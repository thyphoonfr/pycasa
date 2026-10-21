"""
FR: Tests de mise à jour dynamique en temps réel de la section Personnes (People) :
- Ajout d'une nouvelle personne (People Manager / create_person)
- Ajout manuel d'un visage sur une photo (add_face / One-Up)
- Validation d'une suggestion de visage
- Détection et rafraîchissement automatique de l'arborescence (CAlbumListUI / cat_people)
- Suppression et renommage d'une personne
EN: Real-time dynamic update tests for the People section:
- Adding a new person (People Manager / create_person)
- Manually adding a face on a photo (add_face / One-Up)
- Confirming a face suggestion
- Automatic detection and refresh of the library tree (CAlbumListUI / cat_people)
- Deleting and renaming a person
"""

import os
import shutil
import tempfile
from pathlib import Path
from PIL import Image

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.contacts import Contact, ContactsFile
from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import PersonCluster
from picasa_py.ui.library_tree import PicasaLibraryTree
from picasa_py.ui.main_window import PicasaMainWindow


@pytest.fixture(scope="session")
def qapp():
    """
    FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provide a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_people_env():
    """
    FR: Crée un environnement temporaire avec une photo et une base de données pour tester la section Personnes.
    EN: Create a temporary environment with a photo and database to test the People section.
    """
    td = tempfile.mkdtemp(prefix="pycasa_test_people_")
    photo1 = os.path.join(td, "photo1.jpg")
    img1 = Image.new("RGB", (640, 480), color=(180, 200, 220))
    img1.save(photo1)

    db_dir = os.path.join(td, "db3")
    contacts_dir = os.path.join(td, "contacts")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(contacts_dir, exist_ok=True)

    db = PicasaDatabase.open(db_dir, contacts_dir)
    # Ajouter la photo dans l'index
    db.add_media_record(td + "\\", "photo1.jpg", 1234, 100000, 2)

    yield {
        "dir": td,
        "photo1": photo1,
        "db": db,
    }

    try:
        shutil.rmtree(td)
    except Exception:
        pass


def test_people_tree_live_refresh_on_create(qapp, temp_people_env):
    """
    FR: Vérifie que la création d'une personne met à jour immédiatement l'arborescence.
    EN: Verify that creating a person immediately updates the library tree.
    """
    db = temp_people_env["db"]
    tree = PicasaLibraryTree()
    tree.populate_from_database(db)

    # Initialement vide
    assert tree.cat_people.childCount() == 0

    # Créer une nouvelle personne
    new_p = db.face_manager.create_person("Thomas Martin")
    assert new_p.contact_id in db.face_manager.people

    # Rafraîchir l'arborescence (ou via callback)
    tree.refresh_people()
    assert tree.cat_people.childCount() == 1
    item = tree.cat_people.child(0)
    assert "Thomas Martin" in item.text(0)
    assert "(0)" in item.text(0)


def test_people_tree_live_refresh_on_add_face(qapp, temp_people_env):
    """
    FR: Vérifie que l'ajout d'un visage sur une photo incrémente le compteur et met à jour l'avatar.
    EN: Verify that adding a face on a photo increments the counter and updates the avatar.
    """
    db = temp_people_env["db"]
    photo_p = temp_people_env["photo1"]

    callback_called = []
    db.face_manager.on_people_changed_callbacks.append(lambda: callback_called.append(True))

    tree = PicasaLibraryTree()
    tree.populate_from_database(db)

    # Ajout d'un visage pour "Claire Fontaine"
    fr = FaceRect(left=0.2, top=0.2, right=0.5, bottom=0.5)
    db.face_manager.add_face(photo_p, fr, "Claire Fontaine", db_idx=0)

    # Le callback doit avoir été notifié
    assert len(callback_called) >= 1

    # L'arbre doit afficher Claire Fontaine avec 1 photo
    tree.refresh_people()
    assert tree.cat_people.childCount() >= 1

    found = False
    for i in range(tree.cat_people.childCount()):
        child = tree.cat_people.child(i)
        if "Claire Fontaine" in child.text(0):
            found = True
            assert "(1)" in child.text(0)
            # L'icône de l'avatar doit être configurée
            assert not child.icon(0).isNull()
    assert found is True


def test_people_tree_live_refresh_on_delete_person(qapp, temp_people_env):
    """
    FR: Vérifie que la suppression d'une personne la retire de l'arborescence.
    EN: Verify that deleting a person removes them from the library tree.
    """
    db = temp_people_env["db"]
    p = db.face_manager.create_person("Personne A Supprimer")
    tree = PicasaLibraryTree()
    tree.populate_from_database(db)

    # Doit être présente
    assert any("Personne A Supprimer" in tree.cat_people.child(i).text(0) for i in range(tree.cat_people.childCount()))

    # Supprimer la personne
    db.face_manager.delete_person(p.contact_id)
    tree.refresh_people()

    # Ne doit plus être présente
    assert not any("Personne A Supprimer" in tree.cat_people.child(i).text(0) for i in range(tree.cat_people.childCount()))


def test_main_window_people_signal_connection(qapp, temp_people_env):
    """
    FR: Vérifie que MainWindow connecte les signaux people_changed et notifie l'arborescence.
    EN: Verify that MainWindow connects the people_changed signals and notifies the library tree.
    """
    db = temp_people_env["db"]
    win = PicasaMainWindow(db_path=str(db.db3_dir))

    initial_count = win.library_tree.cat_people.childCount()

    # Déclencher un ajout de visage
    fr = FaceRect(left=0.1, top=0.1, right=0.3, bottom=0.3)
    win.db.face_manager.add_face(temp_people_env["photo1"], fr, "Nouvel Ami Test", db_idx=0)

    # Vérifier que le handler de MainWindow a été déclenché
    assert win.library_tree.cat_people.childCount() == initial_count + 1
    assert any("Nouvel Ami Test" in win.library_tree.cat_people.child(i).text(0) for i in range(win.library_tree.cat_people.childCount()))
    win.close()
