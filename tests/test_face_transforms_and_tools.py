"""FR: Tests unitaires pour les transformations de coordonnées de visages (crop, tilt, rotate)
et la gestion des outils interactifs sur le canvas (curseurs PE, conflits zoom/pan).
EN: Unit tests for face coordinate transformations (crop, tilt, rotate)
and interactive tool management on the canvas (PE cursors, zoom/pan conflicts).
Ref: AGENTS.md §3, §4 bis, §5
"""
import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QKeyEvent

from picasa_py.faces.facerect import FaceRect
from picasa_py.ui.image_canvas import PicasaImageCanvas


def test_face_crop_transform():
    """FR: Vérifie la projection et la rétroprojection d'un rectangle de visage dans un espace recadré.
    EN: Verifies forward and inverse projection of a face rectangle in a cropped space.
    """
    # Visage centré sur une image normale
    face = FaceRect(left=0.4, top=0.4, right=0.6, bottom=0.6)
    
    # Recadrage au quart supérieur gauche [0.0, 0.0, 0.5, 0.5]
    crop = (0.0, 0.0, 0.5, 0.5)
    transformed = face.to_cropped_space(crop)
    assert transformed is not None
    # Dans le quart sup gauche, [0.4, 0.4, 0.6, 0.6] devient [0.8, 0.8, 1.2, 1.2] clampé à [0.8, 0.8, 1.0, 1.0]
    assert pytest.approx(transformed.left, abs=1e-3) == 0.8
    assert pytest.approx(transformed.top, abs=1e-3) == 0.8

    # Visage complètement hors du crop -> doit retourner None
    face_outside = FaceRect(left=0.6, top=0.6, right=0.8, bottom=0.8)
    assert face_outside.to_cropped_space(crop) is None

    # Test aller-retour (roundtrip) pour un visage entièrement dans le crop
    crop2 = (0.2, 0.2, 0.8, 0.8)
    face_inside = FaceRect(left=0.3, top=0.3, right=0.5, bottom=0.5)
    in_crop = face_inside.to_cropped_space(crop2)
    assert in_crop is not None
    back_to_orig = in_crop.from_cropped_space(crop2)
    assert pytest.approx(back_to_orig.left, abs=1e-6) == face_inside.left
    assert pytest.approx(back_to_orig.top, abs=1e-6) == face_inside.top
    assert pytest.approx(back_to_orig.right, abs=1e-6) == face_inside.right
    assert pytest.approx(back_to_orig.bottom, abs=1e-6) == face_inside.bottom


def test_face_rotate_transform():
    """FR: Vérifie la rotation de 90° et la rotation inverse d'un rectangle de visage.
    EN: Verifies 90-degree rotation and inverse rotation of a face rectangle.
    """
    face = FaceRect(left=0.1, top=0.2, right=0.3, bottom=0.5)
    
    # 90 deg clockwise (1 step)
    r1 = face.to_rotated_space(1)
    # (x, y) -> (1-y, x)
    assert pytest.approx(r1.left, abs=1e-6) == 1.0 - 0.5  # 0.5
    assert pytest.approx(r1.top, abs=1e-6) == 0.1
    assert pytest.approx(r1.right, abs=1e-6) == 1.0 - 0.2  # 0.8
    assert pytest.approx(r1.bottom, abs=1e-6) == 0.3

    # Inverse
    back = r1.from_rotated_space(1)
    assert pytest.approx(back.left, abs=1e-6) == face.left
    assert pytest.approx(back.top, abs=1e-6) == face.top
    assert pytest.approx(back.right, abs=1e-6) == face.right
    assert pytest.approx(back.bottom, abs=1e-6) == face.bottom


def test_face_tilt_transform_roundtrip():
    """FR: Vérifie l'aller-retour de transformation d'inclinaison (redressement) sur un FaceRect.
    EN: Verifies tilt (straighten) transformation round-trip on a FaceRect.
    """
    face = FaceRect(left=0.3, top=0.3, right=0.5, bottom=0.5)
    angle = 5.0  # 5 degrés de redressement
    aspect = 4.0 / 3.0

    tilted = face.to_tilted_space(angle, aspect)
    assert tilted is not None
    restored = tilted.from_tilted_space(angle, aspect)

    assert pytest.approx(restored.left, abs=1e-5) == face.left
    assert pytest.approx(restored.top, abs=1e-5) == face.top
    assert pytest.approx(restored.right, abs=1e-5) == face.right
    assert pytest.approx(restored.bottom, abs=1e-5) == face.bottom


def test_canvas_tool_activation_and_cursors(qapp):
    """FR: Vérifie l'activation/annulation des outils (retouche, yeux rouges, redressement, recadrage) sur le canevas.
    EN: Verifies activation and cancellation of tools (retouch, red-eye, straighten, crop) on the canvas.
    """
    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)
    canvas._image_target_rect = canvas.rect()

    assert not canvas.is_any_tool_active()

    # Retouch
    canvas.start_retouch(25.0)
    assert canvas.is_retouching is True
    assert canvas.is_any_tool_active() is True
    assert canvas.retouch_radius == 25.0
    canvas.set_retouch_radius(40.0)
    assert canvas.retouch_radius == 40.0
    canvas.cancel_retouch()
    assert canvas.is_retouching is False

    # Red Eye
    canvas.start_redeye()
    assert canvas.is_redeye is True
    assert canvas.is_any_tool_active() is True
    canvas.cancel_redeye()
    assert canvas.is_redeye is False

    # Straighten
    canvas.start_straighten(0.0)
    assert canvas.is_straightening is True
    assert canvas.is_any_tool_active() is True
    canvas.cancel_straighten()
    assert canvas.is_straightening is False

    # Crop
    canvas.start_crop()
    assert canvas.is_cropping is True
    assert canvas.is_any_tool_active() is True
    canvas.cancel_crop()
    assert canvas.is_cropping is False


def test_canvas_zoom_pan_conflict_prevention(qapp):
    """FR: Vérifie que le déplacement (pan) et le double-clic zoom sont désactivés lorsqu'un outil d'édition est actif.
    EN: Verifies that pan dragging and double-click zoom are disabled when an editing tool is active.
    """
    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)
    canvas._image_target_rect = canvas.rect()

    # Simuler le début d'un outil retouche
    canvas.start_retouch(30.0)
    assert canvas.is_retouching is True

    # Clic gauche pour appliquer une retouche
    retouch_points = []
    canvas.retouch_applied.connect(lambda x, y, r: retouch_points.append((x, y, r)))

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(400, 300),
        QPointF(400, 300),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press_event)

    # Vérifier que le pan dragging N'A PAS été activé
    assert canvas._is_dragging is False
    assert len(retouch_points) == 1
    assert pytest.approx(retouch_points[0][0], abs=1e-2) == 0.5
    assert pytest.approx(retouch_points[0][1], abs=1e-2) == 0.5
    assert retouch_points[0][2] == 30.0

    # Double clic ne doit PAS modifier le zoom si un outil est actif
    prev_zoom = canvas.zoom_level
    double_click = QMouseEvent(
        QMouseEvent.Type.MouseButtonDblClick,
        QPointF(400, 300),
        QPointF(400, 300),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseDoubleClickEvent(double_click)
    assert canvas.zoom_level == prev_zoom

    # Escape doit annuler l'outil actif
    key_esc = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(key_esc)
    assert canvas.is_retouching is False
    assert not canvas.is_any_tool_active()


def test_canvas_face_manual_add_inverse_transform(qapp):
    """FR: Vérifie que l'ajout manuel d'un visage sur une image recadrée applique la transformation inverse vers l'image originale.
    EN: Verifies that manual face addition on a cropped image applies the inverse transform back to original image coordinates.
    """
    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)
    canvas._image_target_rect = canvas.rect()

    # Image avec un crop actif [0.2, 0.2, 0.8, 0.8]
    crop_rect = (0.2, 0.2, 0.8, 0.8)
    canvas.set_active_transform(crop_rect=crop_rect, tilt_angle=0.0, rotation_steps=0)

    canvas.start_manual_face_add()
    assert canvas.is_manual_face_add is True

    created_faces = []
    canvas.manual_face_defined.connect(lambda f: created_faces.append(f))

    # L'utilisateur trace un cadre au centre de la zone affichée [0.4, 0.4] -> [0.6, 0.6]
    # (en pixels: 320x240 à 480x360)
    p_press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(320, 240),
        QPointF(320, 240),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(p_press)

    p_release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(480, 360),
        QPointF(480, 360),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseReleaseEvent(p_release)

    assert len(created_faces) == 1
    face = created_faces[0]
    # Dans l'espace du crop (0.2..0.8), [0.4..0.6] correspond dans l'image originale à:
    # left = 0.2 + 0.4 * 0.6 = 0.44
    # right = 0.2 + 0.6 * 0.6 = 0.56
    assert pytest.approx(face.left, abs=1e-2) == 0.44
    assert pytest.approx(face.top, abs=1e-2) == 0.44
    assert pytest.approx(face.right, abs=1e-2) == 0.56
    assert pytest.approx(face.bottom, abs=1e-2) == 0.56
