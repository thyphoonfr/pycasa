"""FR: Tests pour Copier/Coller tous les effets (ID_EDIT_COPYALLEFFECTS / ID_EDIT_PASTEALLEFFECTS)
et Définir comme miniature d'album de personne (ID_SETPEOPLEALBUMCOVER).
EN: Tests for Copy/Paste All Effects (ID_EDIT_COPYALLEFFECTS / ID_EDIT_PASTEALLEFFECTS)
and Set People Album Thumbnail (ID_SETPEOPLEALBUMCOVER).
"""
import os
import tempfile
import pytest
from PySide6.QtWidgets import QApplication
from PIL import Image

from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import PicasaFaceManager, PersonCluster
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.ui.main_window import PicasaMainWindow


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_copy_and_paste_all_effects(qapp, tmp_path):
    """FR: Vérifie la copie de la pile d'effets .picasa.ini et son application à d'autres photos.
    EN: Verifies copying the .picasa.ini effects stack and pasting it onto other photos.
    """
    # Créer 3 images factices
    img1 = tmp_path / "photo1.jpg"
    img2 = tmp_path / "photo2.jpg"
    img3 = tmp_path / "photo3.jpg"
    for img_p in (img1, img2, img3):
        im = Image.new("RGB", (100, 100), (200, 200, 200))
        im.save(str(img_p))

    # Écrire des effets sur photo1 dans .picasa.ini
    ini_path = tmp_path / ".picasa.ini"
    doc = PicasaIniDocument()
    sec1 = doc.get_or_create_section("photo1.jpg")
    sec1.set("filters", "sepia=1;warmify=40;")
    sec1.set("rotate", "rotate(1)")
    sec1.set("crop", "rect64(1000200080009000)")
    doc.write_file(str(ini_path))

    # Fenêtre principale
    win = PicasaMainWindow()
    win._get_active_photo_paths = lambda: [str(img1)]

    # 1. Copier tous les effets
    win.action_copy_all_effects()
    assert win._effects_clipboard is not None
    assert win._effects_clipboard.get("filters") == "sepia=1;warmify=40;"
    assert win._effects_clipboard.get("rotate") == "rotate(1)"
    assert win._effects_clipboard.get("crop") == "rect64(1000200080009000)"

    # 2. Coller tous les effets sur photo2 et photo3
    win.action_paste_all_effects([str(img2), str(img3)])

    # Relire le .picasa.ini
    doc2 = PicasaIniParser.parse_file(str(ini_path))
    sec2 = doc2.get_section("photo2.jpg")
    sec3 = doc2.get_section("photo3.jpg")
    assert sec2 is not None
    assert sec2.get("filters") == "sepia=1;warmify=40;"
    assert sec2.get("rotate") == "rotate(1)"
    assert sec2.get("crop") == "rect64(1000200080009000)"
    assert sec3 is not None
    assert sec3.get("filters") == "sepia=1;warmify=40;"
    win.close()


def test_set_person_album_cover(qapp, tmp_path):
    """FR: Vérifie le choix d'un visage comme miniature d'album de personne (ID_SETPEOPLEALBUMCOVER).
    EN: Verifies setting a face as the person album cover thumbnail (ID_SETPEOPLEALBUMCOVER).
    """
    img_path = tmp_path / "portrait.jpg"
    im = Image.new("RGB", (200, 200), (120, 150, 180))
    im.save(str(img_path))

    # Mock PicasaDatabase
    class MockDB:
        """FR: Simulacre léger de PicasaDatabase pour tester PicasaFaceManager.
        EN: Lightweight PicasaDatabase mock for testing PicasaFaceManager.
        """
        def __init__(self):
            """FR: Initialise les attributs vides de la base factice.
            EN: Initializes empty attributes for the mock database.
            """
            self.contacts = None
            self.pmps = {}
            self.index = []
        def get_thumbnail(self, idx):
            """FR: Retourne None comme miniature factice.
            EN: Returns None as a dummy thumbnail.
            """
            return None

    db = MockDB()
    fm = PicasaFaceManager(db)
    cluster = PersonCluster(contact_id="pers_001", name="Jean Dupont", photo_paths=[str(img_path)])
    fm.people["pers_001"] = cluster

    fr = FaceRect(left=0.2, top=0.2, right=0.6, bottom=0.6, contact_id="pers_001", contact_name="Jean Dupont")

    # Définir comme couverture
    ok = fm.set_person_album_cover("pers_001", str(img_path), fr)
    assert ok is True
    assert cluster.primary_face_rect == fr
    assert cluster.cover_photo_path == str(img_path)
    assert cluster.avatar_pixmap is not None
    assert not cluster.avatar_pixmap.isNull()

    # Vérifier que get_person_avatar retourne le nouvel avatar
    av = fm.get_person_avatar("pers_001", size=64)
    assert av is not None
    assert not av.isNull()
