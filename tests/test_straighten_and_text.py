"""
FR: Tests pour les outils d'édition interactifs de Picasa 3 :
- Redresser (Straighten / filter_tilt, Ref: picasa3.exe @ 0x008814AC)
- Texte sur photo (Text Tool, Ref: picasa3.exe @ editpanel/textgroupnode, 0x0089898A)
EN: Tests for Picasa 3 interactive editing tools:
- Redresser (Straighten / filter_tilt, Ref: picasa3.exe @ 0x008814AC)
- Texte sur photo (Text Tool, Ref: picasa3.exe @ editpanel/textgroupnode, 0x0089898A)
"""

import os
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPaintEvent, QRegion, QMouseEvent
from PySide6.QtWidgets import QApplication

from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.ui.image_canvas import PicasaImageCanvas
from picasa_py.ui.edit_panel import PicasaStraightenSubpanel, PicasaTextSubpanel, PicasaEditPanel
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument


def test_straighten_processor():
    """
    FR: Vérifie le traitement d'image de redressement avec auto-crop anti-bords-noirs.
    EN: Verify the straighten image processing with anti-black-border auto-cropping.
    """
    img = Image.new("RGB", (400, 300), color=(100, 150, 200))
    # 0 degrés
    s0 = PicasaImageProcessor.straighten(img, 0.0)
    assert s0.size == (400, 300)

    # 15 degrés
    s15 = PicasaImageProcessor.straighten(img, 15.0)
    assert s15.size == (400, 300)

    # -10 degrés
    sm10 = PicasaImageProcessor.straighten(img, -10.0)
    assert sm10.size == (400, 300)


def test_add_text_processor():
    """
    FR: Vérifie l'inscription de texte sur photo.
    EN: Verify rendering text onto a photo.
    """
    img = Image.new("RGB", (300, 200), color=(50, 50, 50))
    res = PicasaImageProcessor.add_text(img, "Vacances 2026", (0.1, 0.8), font_size=20, color=(255, 255, 0), shadow=True)
    assert res.size == (300, 200)
    # L'image a été modifiée par le texte
    assert res.tobytes() != img.tobytes()


def test_ini_tilt_and_text_roundtrip(tmp_path):
    """
    FR: Vérifie la persistance bit-exact et round-trip de filters=tilt=... et text=... dans .picasa.ini.
    EN: Verify bit-exact persistence and round-trip of filters=tilt=... and text=... in .picasa.ini.
    """
    doc = PicasaIniDocument()
    filename = "IMG_0042.JPG"

    # Vérifier que tilt absent renvoie None
    assert doc.get_tilt(filename) is None
    assert doc.get_text(filename) is None

    # Fixer un tilt
    doc.set_tilt(filename, 3.4567)
    assert abs(doc.get_tilt(filename) - 3.4567) < 0.0001
    sec = doc.get_section(filename)
    assert "tilt=1,3.456700,0.000000;" in sec.get("filters")

    # Fixer du texte
    doc.set_text(filename, "Souvenir d'été")
    assert doc.get_text(filename) == "Souvenir d'été"

    # Écriture et relecture
    ini_file = tmp_path / ".picasa.ini"
    doc.write_file(str(ini_file))

    doc2 = PicasaIniParser.parse_file(str(ini_file))
    assert abs(doc2.get_tilt(filename) - 3.4567) < 0.0001
    assert doc2.get_text(filename) == "Souvenir d'été"

    # Supprimer tilt (angle = 0)
    doc2.set_tilt(filename, 0.0)
    assert doc2.get_tilt(filename) is None

    # Supprimer texte
    doc2.set_text(filename, None)
    assert doc2.get_text(filename) is None


def test_straighten_subpanel(qapp):
    """
    FR: Vérifie le fonctionnement du sous-panneau Redresser et ses signaux.
    EN: Verify operation of the Straighten subpanel and its signals.
    """
    panel = PicasaStraightenSubpanel()
    assert panel.slider.value() == 0
    assert panel.lbl_angle_val.text() == "0.0°"

    received_angles = []
    panel.angle_changed.connect(lambda a: received_angles.append(a))

    # Changer l'angle à +5.2° (slider = 52)
    panel.slider.setValue(52)
    assert panel.lbl_angle_val.text() == "+5.2°"
    assert len(received_angles) > 0
    assert abs(received_angles[-1] - 5.2) < 0.01

    # Réinitialiser
    panel.reset_angle()
    assert panel.slider.value() == 0
    assert panel.lbl_angle_val.text() == "0.0°"


def test_text_subpanel(qapp):
    """
    FR: Vérifie le fonctionnement du sous-panneau Texte et ses signaux.
    EN: Verify operation of the Text subpanel and its signals.
    """
    panel = PicasaTextSubpanel()
    assert panel.slider_size.value() == 28
    assert panel.chk_shadow.isChecked() is True

    received_params = []
    panel.params_changed.connect(lambda t, s, c, sh: received_params.append((t, s, c, sh)))

    panel.txt_input.setText("PyCasa Test")
    panel.slider_size.setValue(36)
    assert len(received_params) > 0
    assert received_params[-1][0] == "PyCasa Test"
    assert received_params[-1][1] == 36

    panel.reset_text()
    assert panel.txt_input.text() == ""
    assert panel.slider_size.value() == 28


def test_canvas_straighten_and_text_overlay(qapp, tmp_path):
    """
    FR: Vérifie l'affichage et l'interaction des overlays Straighten et Text sur le canvas.
    EN: Verify display and interaction of the Straighten and Text overlays on the image canvas.
    """
    # Créer une image de test
    img_path = tmp_path / "canvas_test.jpg"
    img = Image.new("RGB", (600, 400), color=(180, 200, 220))
    img.save(img_path)

    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)
    canvas.load_image(str(img_path))

    # 1. Test Redresser
    canvas.start_straighten(2.5)
    assert canvas.is_straightening is True
    assert canvas.straighten_angle == 2.5
    # Rendu paintEvent avec overlay de redressement (grille + badge)
    canvas.paintEvent(QPaintEvent(QRegion(canvas.rect())))

    applied_angle = canvas.apply_straighten()
    assert applied_angle == 2.5
    assert canvas.is_straightening is False

    # 2. Test Texte
    canvas.start_text_tool("Photo de famille")
    assert canvas.is_text_tool_active is True
    canvas.set_text_params("Photo de famille", 32, QColor(255, 255, 0), True)
    # Rendu paintEvent avec overlay de texte
    canvas.paintEvent(QPaintEvent(QRegion(canvas.rect())))

    applied_data = canvas.apply_text_tool()
    assert applied_data["text"] == "Photo de famille"
    assert applied_data["font_size"] == 32
    assert applied_data["shadow"] is True
    assert canvas.is_text_tool_active is False


def test_straighten_face_tracking_and_avatar_crop(qapp, tmp_path):
    """
    FR: Vérifie que lors de l'utilisation de l'outil Redresser (`tilt`), les rectangles de visages
        (`FaceRect.to_tilted_space` / `from_tilted_space`, `PicasaImageCanvas` et `PicasaPeoplePanel`)
        suivent exactement la rotation horaire et le zoom anti-bords-noirs de l'image (`FUN_0042bfa0`).
    EN: Verify that when using the Straighten tool (`tilt`), face rectangles
        (`FaceRect.to_tilted_space` / `from_tilted_space`, `PicasaImageCanvas`, and `PicasaPeoplePanel`)
        accurately track the clockwise rotation and anti-black-border zoom of the image (`FUN_0042bfa0`).
    Ref: picasa3.exe @ 0x0042BFA0 (FUN_0042bfa0), 0x009E68F0, 0x009E6490, 0x0090A720
    """
    import numpy as np
    from PIL import ImageDraw
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.db.database import PicasaDatabase

    w, h = 400, 300
    aspect = w / float(h)
    img = Image.new("RGB", (w, h), (15, 20, 25))
    draw = ImageDraw.Draw(img)
    # Dessiner une cible lumineuse (visage synthétique) centrée en (u=0.75, v=0.25) -> (300, 75)
    draw.rectangle([292, 67, 308, 83], fill=(250, 220, 180))

    photo_path = tmp_path / "tilted_face_test.png"
    img.save(photo_path)

    fr = FaceRect(
        left=0.75 - 0.04,
        top=0.25 - 0.05,
        right=0.75 + 0.04,
        bottom=0.25 + 0.05,
        contact_id="0000000000000001",
        contact_name="Alice Martin",
    )

    for angle_deg in (10.0, -8.5):
        straightened = PicasaImageProcessor.straighten(img, angle_deg)
        arr = np.array(straightened)
        ys, xs = np.where(arr[:, :, 0] > 180)
        actual_u = float(xs.mean()) / w
        actual_v = float(ys.mean()) / h

        projected = fr.to_tilted_space(angle_deg, aspect_ratio=aspect)
        assert projected is not None
        proj_u = (projected.left + projected.right) / 2.0
        proj_v = (projected.top + projected.bottom) / 2.0
        assert abs(proj_u - actual_u) < 0.005
        assert abs(proj_v - actual_v) < 0.005

        # Vérifier l'inversion exacte (from_tilted_space)
        restored = projected.from_tilted_space(angle_deg, aspect_ratio=aspect)
        assert abs(restored.left - fr.left) < 1e-4
        assert abs(restored.top - fr.top) < 1e-4
        assert abs(restored.right - fr.right) < 1e-4
        assert abs(restored.bottom - fr.bottom) < 1e-4

    # Vérifier l'intégration complète dans PicasaOneUpView (application, Undo/Redo et tiroir droit)
    db_dir = tmp_path / "db3"
    db_dir.mkdir(parents=True, exist_ok=True)
    db = PicasaDatabase(db_dir)
    db.face_manager.add_face(
        photo_path=str(photo_path),
        face_rect=fr,
        contact_name="Alice Martin",
        contact_id="0000000000000001",
    )

    one_up = PicasaOneUpView()
    one_up.open_photo(db, -1, [], direct_path=str(photo_path))
    assert abs(one_up.canvas._active_tilt_angle - 0.0) < 1e-4

    # Démarrer l'outil Redresser, régler à +10.0° et appliquer
    one_up._on_straighten_start()
    one_up.canvas.set_straighten_angle(10.0)
    one_up._on_straighten_apply()

    assert abs(one_up._active_tilt - 10.0) < 1e-4
    assert abs(one_up.canvas._active_tilt_angle - 10.0) < 1e-4

    # Vérifier que Undo remet l'inclinaison active à 0° et Redo la remet à +10°
    one_up._on_undo()
    assert abs(one_up.canvas._active_tilt_angle - 0.0) < 1e-4
    one_up._on_redo()
    assert abs(one_up.canvas._active_tilt_angle - 10.0) < 1e-4

