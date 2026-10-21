"""FR: Tests de validation pour la saisie et modification directe en ligne des noms de visages (People Panel).
EN: Validation tests for inline direct input and editing of face names (People Panel).
Ref: picasa3.exe @ peoplepanel/editbox, peoplepanel/peopleautocomplete
Ref: picasa3.exe @ peoplepanel/suggestion_yes, peoplepanel/suggestion_no, peoplepanel/addname
Ref: picasa3.exe @ 0x00646B48, 0x00646CAA (SendMessageW EM_SETSEL)
"""

import os
import shutil
import tempfile
import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QLineEdit, QPushButton, QStackedWidget

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import FaceSuggestion
from picasa_py.ui.right_drawer import PicasaPeoplePanel, PicasaInlineNameEdit, FaceCardFrame


@pytest.fixture
def temp_inline_edit_env():
    """FR: Crée un environnement temporaire avec une photo et une base PicasaDatabase pour l'édition en ligne.
    EN: Creates a temporary environment with a photo and a PicasaDatabase for inline editing.
    """
    td = tempfile.mkdtemp(prefix="pycasa_inline_face_test_")
    db_dir = os.path.join(td, "db3")
    contacts_dir = os.path.join(td, "contacts")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(contacts_dir, exist_ok=True)

    photo_path = os.path.join(td, "test_people.jpg")
    im = Image.new("RGB", (200, 200), color=(200, 200, 200))
    im.save(photo_path)

    db = PicasaDatabase.open(db_dir, contacts_dir)
    db.add_media_record(td + "\\", "test_people.jpg", 1001, 10000, 2)

    yield {
        "dir": td,
        "photo": photo_path,
        "db": db,
    }

    try:
        shutil.rmtree(td)
    except Exception:
        pass


def test_suggestion_inline_direct_text_editing(temp_inline_edit_env, qapp):
    """FR: Vérifie que pour une suggestion de visage, le volet présente directement un QLineEdit
    éditable en ligne permettant de modifier le texte et de le valider avec Entrée ou le bouton ✔.
    EN: Verifies that for a face suggestion, the panel directly presents an inline editable
    QLineEdit allowing text modification and confirmation via Enter or the ✔ button.
    Ref: picasa3.exe @ peoplepanel/editbox, peoplepanel/suggestion_yes
    """
    db = temp_inline_edit_env["db"]
    photo = temp_inline_edit_env["photo"]

    fr = FaceRect(0.2, 0.2, 0.5, 0.5, contact_name="? Alice")
    panel = PicasaPeoplePanel()
    panel.resize(320, 600)
    panel.set_photo_faces(db, 1, photo, [fr])

    # Trouver la carte
    card = panel.faces_layout.itemAt(0).widget()
    assert isinstance(card, FaceCardFrame)

    # Trouver le champ QLineEdit d'édition directe
    name_edit = card.findChild(QLineEdit)
    assert name_edit is not None
    assert isinstance(name_edit, PicasaInlineNameEdit)
    assert name_edit.text() == "Alice"

    # Trouver les boutons de validation et rejet
    buttons = card.findChildren(QPushButton)
    btn_yes = next((b for b in buttons if b.text() == "✔"), None)
    btn_no = next((b for b in buttons if b.text() == "✘"), None)
    assert btn_yes is not None
    assert btn_no is not None

    # Modifier directement le texte dans le champ (ex: "Alice Martin")
    name_edit.setText("Alice Martin")

    # Simuler appui sur Entrée
    name_edit.returnPressed.emit()

    # Vérifier que le visage est maintenant confirmé sous "Alice Martin"
    faces = db.face_manager.get_faces_for_photo(1)
    assert len(faces) == 1
    assert faces[0].contact_name == "Alice Martin"
    assert faces[0].contact_id != ""


def test_unnamed_face_inline_text_editing(temp_inline_edit_env, qapp):
    """FR: Vérifie qu'un visage non identifié propose directement un champ de saisie en ligne
    pour taper le nom et valider avec Entrée sans passer obligatoirement par un dialogue modal.
    EN: Verifies that an unidentified face directly offers an inline input field
    to type the name and confirm via Enter without requiring a modal dialog.
    Ref: picasa3.exe @ peoplepanel/addname:%d, peoplepanel/editbox
    """
    db = temp_inline_edit_env["db"]
    photo = temp_inline_edit_env["photo"]

    fr_unnamed = FaceRect(0.3, 0.3, 0.6, 0.6, contact_name="")
    panel = PicasaPeoplePanel()
    panel.resize(320, 600)
    panel.set_photo_faces(db, 1, photo, [fr_unnamed])

    card = panel.faces_layout.itemAt(0).widget()
    assert isinstance(card, FaceCardFrame)

    name_edit = card.findChild(QLineEdit)
    assert name_edit is not None
    assert "Ajouter un nom" in name_edit.placeholderText()

    # Saisir un nom
    name_edit.setText("Julien")
    name_edit.returnPressed.emit()

    faces = db.face_manager.get_faces_for_photo(1)
    assert len(faces) == 1
    assert faces[0].contact_name == "Julien"


def test_identified_face_inline_renaming(temp_inline_edit_env, qapp):
    """FR: Vérifie qu'une personne identifiée peut être renommée directement en ligne
    en cliquant sur le bouton Modifier.
    EN: Verifies that an identified person can be renamed directly inline
    by clicking the Edit button.
    Ref: picasa3.exe @ 0x00646B48, 0x00646CAA
    """
    db = temp_inline_edit_env["db"]
    photo = temp_inline_edit_env["photo"]

    fr = FaceRect(0.2, 0.2, 0.5, 0.5)
    db.face_manager.add_face(photo, fr, "Marc", db_idx=1)

    panel = PicasaPeoplePanel()
    panel.resize(320, 600)
    faces = db.face_manager.get_faces_for_photo(1)
    panel.set_photo_faces(db, 1, photo, faces)

    card = panel.faces_layout.itemAt(0).widget()
    stack = card.findChild(QStackedWidget)
    assert stack is not None
    assert stack.currentIndex() == 0  # Mode vue

    # Cliquer sur "Modifier"
    btn_edit = next(b for b in card.findChildren(QPushButton) if b.text() == "Modifier")
    btn_edit.click()

    # La pile doit être passée en mode édition
    assert stack.currentIndex() == 1
    inline_edit = card.findChild(QLineEdit)
    assert inline_edit is not None
    assert inline_edit.text() == "Marc"

    # Modifier le nom
    inline_edit.setText("Marcus")
    inline_edit.returnPressed.emit()

    # Le visage doit avoir été réassigné
    updated_faces = db.face_manager.get_faces_for_photo(1)
    assert updated_faces[0].contact_name == "Marcus"
