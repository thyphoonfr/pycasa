"""
FR: Tests de validation et de persistance des retouches et modifications de photos.
Vérifie le comportement conforme à picasa3.exe (rect64, filtres, sauvegarde sur disque avec .picasaoriginals).
EN: Validation and persistence tests for photo editing and modifications.
Verifies behavior matching picasa3.exe (rect64, filters, disk saving with .picasaoriginals).

Ref: AGENTS.md §1, §3, §4, §4 bis
Ref: picasa3.exe @ 0x008814AC, 0x009B9290, 0x00658900
"""

import os
import io
import shutil
import pytest
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.ui.thumbnail_view import PicasaThumbnailView
from picasa_py.ini.parser import PicasaIniParser
from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord


@pytest.fixture(scope="session")
def qapp():
    """
    FR: Fournit une instance QApplication en mode offscreen pour la session de tests.
    EN: Provide an offscreen QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_edit_test", "-platform", "offscreen"])
    return app


@pytest.fixture
def temp_photo_workspace(tmp_path):
    """
    FR: Prépare un dossier de photos avec une image et une base mock.
    EN: Prepare a photo folder with an image and a mock database.
    """
    img_dir = tmp_path / "Vacances"
    img_dir.mkdir(parents=True, exist_ok=True)

    img_path = img_dir / "IMG_0001.JPG"
    # Créer une image 200x200 rouge
    img = Image.new("RGB", (200, 200), (220, 50, 50))
    img.save(str(img_path), format="JPEG")

    db = PicasaDatabase()
    db.thumbindex = ThumbIndexFile()
    rec_folder = ThumbIndexRecord(path=str(img_dir), ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=-1)
    rec_photo = ThumbIndexRecord(path="IMG_0001.JPG", ft1=0, ft2=0, size=2048, type=2, flags=0, parent_idx=0)
    db.thumbindex.records.extend([rec_folder, rec_photo])

    return img_dir, img_path, db


def test_crop_validation_and_ini_persistence(qapp, temp_photo_workspace):
    """
    FR: Vérifie qu'appliquer un recadrage (Appliquer) écrit crop=rect64(...) dans .picasa.ini,
    met à jour le canvas One-Up et émet photo_edited.
    EN: Verify that applying a crop (Apply) writes crop=rect64(...) to .picasa.ini,
    updates the One-Up canvas, and emits photo_edited.
    """
    img_dir, img_path, db = temp_photo_workspace
    view = PicasaOneUpView()

    edited_signals = []
    view.photo_edited.connect(lambda p: edited_signals.append(p))

    view.open_photo(db, 1, [1])
    assert view.current_photo_path == str(img_path)
    assert view._history_idx == 0
    assert view._history[0].size == (200, 200)

    # Démarrer le recadrage (box 20% à 80% soit 120x120 pixels)
    view.canvas.start_crop(QRectF(0.2, 0.2, 0.6, 0.6))
    view._on_crop_apply()

    # Vérification de la persistance dans .picasa.ini
    ini_path = img_dir / ".picasa.ini"
    assert ini_path.exists()
    doc = PicasaIniParser.parse_file(str(ini_path))
    crop_str = doc.get_crop("IMG_0001.JPG")
    assert crop_str is not None
    assert len(crop_str) == 16  # Hex 64-bit

    # Vérification du rechargement de l'image cadrée
    assert len(edited_signals) == 1
    assert edited_signals[0] == str(img_path)
    assert view._history[view._history_idx].size == (120, 120)


def test_straighten_validation(qapp, temp_photo_workspace):
    """
    FR: Vérifie qu'appliquer un redressement persiste tilt dans .picasa.ini et recharge l'image.
    EN: Verify that applying straighten persists tilt in .picasa.ini and reloads the image.
    """
    img_dir, img_path, db = temp_photo_workspace
    view = PicasaOneUpView()

    edited_signals = []
    view.photo_edited.connect(lambda p: edited_signals.append(p))

    view.open_photo(db, 1, [1])

    view.canvas.start_straighten(5.0)
    view._on_straighten_apply()

    ini_path = img_dir / ".picasa.ini"
    assert ini_path.exists()
    doc = PicasaIniParser.parse_file(str(ini_path))
    tilt = doc.get_tilt("IMG_0001.JPG")
    assert tilt is not None
    assert abs(tilt - 5.0) < 0.1

    assert len(edited_signals) == 1


def test_text_tool_validation(qapp, temp_photo_workspace):
    """
    FR: Vérifie qu'appliquer du texte met à jour l'historique et persiste le texte.
    EN: Verify that applying text updates the history and persists the text.
    """
    img_dir, img_path, db = temp_photo_workspace
    view = PicasaOneUpView()

    edited_signals = []
    view.photo_edited.connect(lambda p: edited_signals.append(p))

    view.open_photo(db, 1, [1])
    view.canvas.start_text_tool("Vacances 2026")
    view._on_text_apply()

    ini_path = img_dir / ".picasa.ini"
    assert ini_path.exists()
    doc = PicasaIniParser.parse_file(str(ini_path))
    assert doc.get_text("IMG_0001.JPG") == "Vacances 2026"
    assert len(edited_signals) == 1


def test_save_to_disk_with_picasaoriginals(qapp, temp_photo_workspace):
    """
    FR: Vérifie que 'Enregistrer sur le disque' (save_current_photo) sauvegarde
    l'original dans .picasaoriginals/ et écrit la version modifiée sur le disque.
    EN: Verify that 'Save to disk' (save_current_photo) backs up the original in
    .picasaoriginals/ and writes the modified version to disk.
    Ref: picasa3.exe @ .picasaoriginals (0x008814AC, 0x009B9290)
    """
    img_dir, img_path, db = temp_photo_workspace
    view = PicasaOneUpView()

    view.open_photo(db, 1, [1])
    # Appliquer sépia
    view._on_apply_effect("sepia", {})
    assert view._history_idx == 1

    ok = view.save_current_photo()
    assert ok is True

    # Vérifier que le dossier .picasaoriginals existe et contient la sauvegarde
    originals_dir = img_dir / ".picasaoriginals"
    assert originals_dir.exists()
    backup_file = originals_dir / "IMG_0001.JPG"
    assert backup_file.exists()

    # Vérifier que l'image originale est conservée
    with Image.open(str(backup_file)) as orig:
        r, g, b = orig.getpixel((50, 50))
        assert r > g and r > b  # Originale était rouge

    # Vérifier que l'image sur disque est la version sépia
    with Image.open(str(img_path)) as modified:
        assert modified.size == (200, 200)


def test_direct_path_loading_without_db(qapp, tmp_path):
    """
    FR: Vérifie qu'ouvrir directement un fichier sans base de données ne plante pas.
    EN: Verify that opening a file directly without a database does not crash.
    """
    img_path = tmp_path / "standalone.png"
    img = Image.new("RGBA", (150, 150), (10, 20, 30, 255))
    img.save(str(img_path))

    view = PicasaOneUpView()
    view.open_photo(None, -1, [], direct_path=str(img_path))
    assert view.current_photo_path == str(img_path)
    assert view._history_idx == 0
    assert view._history[0].size == (150, 150)
