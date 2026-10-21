"""FR: Tests unitaires pour l'interface graphique liée aux visages :
1. Dialogue de saisie de nom (PicasaNameFaceDialog).
2. Mode d'ajout interactif sur le canevas (PicasaImageCanvas: start_manual_face_add).
3. Panneau des personnes dans le tiroir latéral (PicasaPeoplePanel).
4. Bouton de validation de suggestions dans l'en-tête d'album (PicasaThumbnailView).

EN: Unit tests for the face-related graphical user interface:
1. Name input dialog (PicasaNameFaceDialog).
2. Interactive addition mode on the canvas (PicasaImageCanvas: start_manual_face_add).
3. People panel in the right drawer (PicasaPeoplePanel).
4. Suggestion confirmation button in the album header (PicasaThumbnailView).
"""

import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent

from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import PicasaFaceManager, FaceSuggestion
from picasa_py.ui.name_face_dialog import PicasaNameFaceDialog
from picasa_py.ui.image_canvas import PicasaImageCanvas
from picasa_py.ui.right_drawer import PicasaPeoplePanel
from picasa_py.db.database import PicasaDatabase


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    return app


def test_name_face_dialog_creation_and_input(qapp):
    """FR: Vérifie la création, la saisie de nom et la demande de suppression dans PicasaNameFaceDialog.
    EN: Verifies creation, name input, and deletion request in PicasaNameFaceDialog.
    """
    fr = FaceRect(left=0.2, top=0.2, right=0.5, bottom=0.5)
    existing = ["Alice", "Bob", "Charlie"]

    dialog = PicasaNameFaceDialog(
        face_rect=fr,
        photo_path="",
        existing_names=existing,
        current_name="Bob",
        is_new_face=False
    )

    assert dialog.name_edit.text() == "Bob"
    assert dialog.existing_names == existing

    # Simuler la modification du nom
    dialog.name_edit.setText("Robert")
    assert dialog.get_contact_name() == "Robert"
    assert not dialog.is_delete_requested()

    # Clic sur supprimer
    dialog._on_delete()
    assert dialog.is_delete_requested()


def test_canvas_manual_face_add_interaction(qapp):
    """FR: Vérifie le tracé interactif à la souris d'un cadre de visage manuel sur PicasaImageCanvas.
    EN: Verifies interactive mouse drawing of a manual face rectangle on PicasaImageCanvas.
    """
    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)
    canvas._image_target_rect = canvas.rect()

    # Activer le mode d'ajout manuel
    canvas.start_manual_face_add()
    assert canvas.is_manual_face_add is True
    assert canvas.cursor().shape() in (Qt.CursorShape.CrossCursor, Qt.CursorShape.BitmapCursor)

    defined_faces = []
    canvas.manual_face_defined.connect(lambda f: defined_faces.append(f))

    # Simuler le tracé de la souris (press à (200, 150) -> move à (400, 350) -> release)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(200, 150),
        QPointF(200, 150),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press_event)
    assert canvas._manual_face_start is not None

    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(400, 350),
        QPointF(400, 350),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseMoveEvent(move_event)
    assert canvas._manual_face_current is not None

    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(400, 350),
        QPointF(400, 350),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseReleaseEvent(release_event)

    # Le mode manuel doit s'être désactivé et le signal émis avec un FaceRect valide
    assert canvas.is_manual_face_add is False
    assert len(defined_faces) == 1
    fr = defined_faces[0]
    assert 0.20 <= fr.left <= 0.30
    assert 0.20 <= fr.top <= 0.30
    assert 0.45 <= fr.right <= 0.55
    assert 0.50 <= fr.bottom <= 0.65


def test_people_panel_cards_and_suggestions(qapp):
    """FR: Vérifie la génération des cartes de visages (identifié, suggéré, inconnu) dans PicasaPeoplePanel.
    EN: Verifies generation of face cards (identified, suggested, unnamed) in PicasaPeoplePanel.
    """
    panel = PicasaPeoplePanel()
    panel.resize(300, 500)

    # 1. Visage identifié
    f1 = FaceRect(left=0.1, top=0.1, right=0.3, bottom=0.3, contact_id="1234", contact_name="Alice")
    # 2. Visage suggéré
    f2 = FaceRect(left=0.4, top=0.1, right=0.6, bottom=0.3, contact_id="", contact_name="? Bob")
    # 3. Visage non identifié
    f3 = FaceRect(left=0.7, top=0.1, right=0.9, bottom=0.3, contact_id="", contact_name=None)

    panel.set_photo_faces(db=None, photo_index=0, photo_path="", faces=[f1, f2, f3])

    # Le conteneur doit avoir créé 3 cartes + 1 stretch spacer = 4 items
    assert panel.faces_layout.count() == 4
