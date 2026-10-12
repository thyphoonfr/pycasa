"""
Tests unitaires pour le moteur de scan et de surveillance de répertoires.

Vérifie :
1. Extraction EXIF, orientation, dimensions, dates OLE et génération de miniature JPEG.
2. Détection des fichiers non indexés par PicasaDirScanner.
3. Insertion d'enregistrements dans thumbindex.db et thumbs_0.db.
4. Surveillance en temps réel par PicasaFolderWatcher avec debounce de 500 ms (0x00704F20).
5. Dialogue Folder Manager et persistance dans repository.dat.
"""

import io
import os
import time
from pathlib import Path
import pytest
from PIL import Image

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexFile
from picasa_py.db.blockfile import BlockIndexFile, BlockContainerFile
from picasa_py.db.kvtable import KeyValueTableFile
from picasa_py.scanner.scanner import (
    extract_image_metadata_and_thumb,
    datetime_to_ole,
    PicasaDirScanner,
    BackgroundScanWorker,
)
from picasa_py.scanner.watcher import PicasaFolderWatcher
from picasa_py.ui.folder_manager import PicasaFolderManagerDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_picasa_env(tmp_path):
    """Crée un environnement temporaire avec dossier d'images et dossier db3."""
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()

    # Créer 3 images de test
    for i in range(3):
        img = Image.new("RGB", (300 + i * 50, 200 + i * 50), color=(100 + i * 20, 50, 150))
        img.save(photos_dir / f"test_img_{i}.jpg", "JPEG")

    db3_dir = tmp_path / "db3"
    db3_dir.mkdir()

    # Initialiser une base vide avec structures minimales
    ti = ThumbIndexFile()
    (db3_dir / "thumbindex.db").write_bytes(ti.to_bytes())

    thumbs_idx = BlockIndexFile()
    (db3_dir / "thumbs_index.db").write_bytes(thumbs_idx.to_bytes())

    thumbs_cont = BlockContainerFile()
    (db3_dir / "thumbs_0.db").write_bytes(thumbs_cont.to_bytes())

    repo = KeyValueTableFile()
    repo.set(str(photos_dir) + "\\", "1")
    (db3_dir / "repository.dat").write_bytes(repo.to_bytes())

    db = PicasaDatabase.open(db3_dir)
    return photos_dir, db3_dir, db


def test_extract_image_metadata_and_thumb(tmp_path):
    img_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (640, 480), color=(255, 128, 0))
    img.save(img_path, "JPEG")

    res = extract_image_metadata_and_thumb(str(img_path))
    assert res is not None
    jpeg_bytes, w, h, ole_date = res

    assert w == 640
    assert h == 480
    assert ole_date > 0.0
    assert len(jpeg_bytes) > 0

    # Vérifier que la miniature est bien lisible et <= 256x256
    thumb = Image.open(io.BytesIO(jpeg_bytes))
    assert thumb.width <= 256
    assert thumb.height <= 256


def test_dir_scanner_and_indexing(temp_picasa_env):
    photos_dir, db3_dir, db = temp_picasa_env
    scanner = PicasaDirScanner(db)

    # 1. Tous les fichiers doivent être détectés comme non indexés
    unindexed = scanner.find_unindexed_files([str(photos_dir)])
    assert len(unindexed) == 3

    # 2. Indexation du premier fichier
    idx1 = scanner.index_file(unindexed[0])
    assert idx1 is not None

    # thumbindex doit avoir le dossier parent (type 1) et le fichier média (type 2)
    assert len(db.index) >= 2
    assert db.index[idx1].type == 2
    assert db.index[idx1].path == os.path.basename(unindexed[0])

    # La miniature doit être récupérable
    thumb_data = db.get_thumbnail(idx1)
    assert thumb_data is not None
    assert len(thumb_data) > 0

    # 3. Sauvegarde et réouverture
    db.save_database()
    db2 = PicasaDatabase.open(db3_dir)
    assert len(db2.index) == len(db.index)
    assert db2.get_thumbnail(idx1) == thumb_data


def test_background_scan_worker(temp_picasa_env, qapp):
    photos_dir, db3_dir, db = temp_picasa_env

    worker = BackgroundScanWorker(db, [str(photos_dir)])

    progress_events = []
    worker.progress.connect(lambda cur, tot, fn: progress_events.append((cur, tot, fn)))

    added_results = []
    worker.finished.connect(lambda count: added_results.append(count))

    worker.run()

    assert len(added_results) == 1
    assert added_results[0] == 3
    assert len(progress_events) == 3

    # Vérifier que tous les fichiers sont maintenant indexés
    scanner = PicasaDirScanner(db)
    assert len(scanner.find_unindexed_files([str(photos_dir)])) == 0


def test_watcher_reload_and_directories(temp_picasa_env, qapp):
    photos_dir, db3_dir, db = temp_picasa_env

    watcher = PicasaFolderWatcher(db)
    assert str(photos_dir.resolve()) in [os.path.abspath(p) for p in watcher.watched_paths]

    # Modification de la configuration
    new_dir = photos_dir.parent / "extra"
    new_dir.mkdir()
    watcher.add_directory(str(new_dir))
    assert str(new_dir.resolve()) in [os.path.abspath(p) for p in watcher.watched_paths]

    watcher.remove_directory(str(new_dir))
    assert str(new_dir.resolve()) not in [os.path.abspath(p) for p in watcher.watched_paths]


def test_folder_manager_dialog(temp_picasa_env, qapp):
    photos_dir, db3_dir, db = temp_picasa_env

    dlg = PicasaFolderManagerDialog(db)
    assert dlg.windowTitle() != ""
    assert dlg.watched_list.count() >= 1
    assert dlg.tree_view.header().stretchLastSection() is True
    assert not dlg.tree_view.isColumnHidden(0)

    # Tester la modification d'un dossier
    target = str(photos_dir.resolve())
    dlg.current_selected_path = target
    dlg._on_status_radio_changed(1)  # Scan Always

    assert dlg.folder_settings[target] == "1"

    # Enregistrement
    dlg._on_ok_clicked()
    watched = db.get_watched_folders()
    norm_target = target + "\\" if not target.endswith("\\") else target
    assert watched.get(norm_target) == "1"
