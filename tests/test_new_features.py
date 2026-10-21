"""FR: Tests unitaires et d'intégration pour les nouvelles fonctionnalités de Picasa 3 :
- PicasaAlbumDialog (album.fen)
- PicasaImagePropertiesDialog (imageproperties.fen)
- PicasaContactManagerDialog (contactmgr.fen)
- PicasaEmailDialog (CHOOSE_MAIL_TEXT.XML)
- PicasaMoveDatabaseDialog (move_database.fen)
- PicasaPosterDialog (poster.fen)
- PicasaWebExportDialog (webexport.fen)
- PicasaImportDialog (ACQUIREPANEL_TEXT_FR.XML)
- PicasaDatabase.compact() (compacting.fen)

EN: Unit and integration tests for Picasa 3 features:
- PicasaAlbumDialog (album.fen)
- PicasaImagePropertiesDialog (imageproperties.fen)
- PicasaContactManagerDialog (contactmgr.fen)
- PicasaEmailDialog (CHOOSE_MAIL_TEXT.XML)
- PicasaMoveDatabaseDialog (move_database.fen)
- PicasaPosterDialog (poster.fen)
- PicasaWebExportDialog (webexport.fen)
- PicasaImportDialog (ACQUIREPANEL_TEXT_FR.XML)
- PicasaDatabase.compact() (compacting.fen)
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from PIL import Image

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.contacts import Contact, ContactsFile
from picasa_py.ui.album_dialog import PicasaAlbumDialog
from picasa_py.ui.image_properties_dialog import PicasaImagePropertiesDialog
from picasa_py.ui.contact_manager_dialog import PicasaContactManagerDialog
from picasa_py.ui.email_dialog import PicasaEmailDialog
from picasa_py.ui.move_database_dialog import PicasaMoveDatabaseDialog
from picasa_py.ui.poster_dialog import PicasaPosterDialog
from picasa_py.ui.web_export_dialog import PicasaWebExportDialog
from picasa_py.ui.import_dialog import PicasaImportDialog


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_env():
    """FR: Crée un environnement temporaire avec deux photos de test et une base PicasaDatabase.
    EN: Creates a temporary environment with two test photos and a PicasaDatabase.
    """
    td = tempfile.mkdtemp(prefix="pycasa_test_new_")
    # Créer quelques fausses photos
    photo1 = os.path.join(td, "photo1.jpg")
    img1 = Image.new("RGB", (800, 600), color=(255, 0, 0))
    img1.save(photo1)

    photo2 = os.path.join(td, "photo2.jpg")
    img2 = Image.new("RGB", (1024, 768), color=(0, 255, 0))
    img2.save(photo2)

    db_dir = os.path.join(td, "db")
    db = PicasaDatabase.open(db_dir)

    yield {
        "dir": td,
        "photo1": photo1,
        "photo2": photo2,
        "db": db,
    }

    try:
        shutil.rmtree(td)
    except Exception:
        pass


def test_album_dialog(qapp, temp_env):
    """FR: Vérifie le dialogue des propriétés de l'album (album.fen).
    EN: Verifies the album properties dialog (album.fen).
    """
    photo_dates = [datetime(2023, 5, 10, 14, 30), datetime(2023, 5, 12, 18, 0)]
    dlg = PicasaAlbumDialog(
        album_name="Vacances Été",
        date_str="2023-05-10",
        music_path="C:/music/track.mp3",
        location="Nice",
        description="Super séjour au soleil",
        photo_dates=photo_dates
    )
    assert dlg.edit_name.text() == "Vacances Été"
    assert dlg.chk_music.isChecked() is True
    assert dlg.edit_music.text() == "C:/music/track.mp3"
    assert dlg.edit_location.text() == "Nice"
    assert dlg.edit_caption.toPlainText() == "Super séjour au soleil"

    # Test auto date
    dlg._on_auto_date()
    qd = dlg.date_picker.date()
    assert qd.year() == 2023
    assert qd.month() == 5
    assert qd.day() == 10

    data = dlg.get_album_data()
    assert data["name"] == "Vacances Été"
    assert "2023-05-10" in data["date"]
    assert data["music"] == "C:/music/track.mp3"
    assert data["location"] == "Nice"
    assert data["description"] == "Super séjour au soleil"
    dlg.close()


def test_image_properties_dialog(qapp, temp_env):
    """FR: Vérifie le dialogue d'inspection des métadonnées détaillées (imageproperties.fen).
    EN: Verifies the detailed metadata inspection dialog (imageproperties.fen).
    """
    paths = [temp_env["photo1"], temp_env["photo2"]]
    dlg = PicasaImagePropertiesDialog(paths, current_index=0)

    assert dlg.val_name.text() == "photo1.jpg"
    assert "photo1.jpg" in dlg.val_name.text()
    assert dlg.table.rowCount() > 0

    # Navigation suivante
    dlg._navigate_next()
    assert dlg.current_index == 1
    assert dlg.val_name.text() == "photo2.jpg"

    # Navigation précédente
    dlg._navigate_prev()
    assert dlg.current_index == 0
    assert dlg.val_name.text() == "photo1.jpg"
    dlg.close()


def test_contact_manager_dialog(qapp, temp_env):
    """FR: Vérifie le gestionnaire de contacts et personnes (contactmgr.fen).
    EN: Verifies the contact and people manager dialog (contactmgr.fen).
    """
    db = temp_env["db"]
    # Ajouter des contacts dans db.contacts
    if db.contacts is None:
        db.contacts = ContactsFile()
    c1 = Contact(id="c1_test", name="Alice Martin")
    c2 = Contact(id="c2_test", name="Bob Dupont")
    db.contacts.add_contact(c1)
    db.contacts.add_contact(c2)

    dlg = PicasaContactManagerDialog(db)
    assert dlg.list_contacts.count() >= 2

    # Test filtrage recherche
    dlg.search_edit.setText("Alice")
    dlg._filter_contacts("Alice")
    # Seul Alice doit être visible
    visible_count = sum(1 for i in range(dlg.list_contacts.count()) if not dlg.list_contacts.item(i).isHidden())
    assert visible_count == 1

    dlg.search_edit.setText("")
    dlg._filter_contacts("")
    visible_count_all = sum(1 for i in range(dlg.list_contacts.count()) if not dlg.list_contacts.item(i).isHidden())
    assert visible_count_all >= 2
    dlg.close()


def test_email_dialog(qapp, temp_env):
    """FR: Vérifie le dialogue d'envoi par e-mail (CHOOSE_MAIL_TEXT.XML).
    EN: Verifies the email sending dialog (CHOOSE_MAIL_TEXT.XML).
    """
    paths = [temp_env["photo1"], temp_env["photo2"]]
    dlg = PicasaEmailDialog(paths)
    assert len(dlg.photo_paths) == 2
    assert "2" in dlg.lbl_count.text()
    assert dlg.btn_group.checkedId() == 1024 or dlg.btn_group.checkedId() == 800
    dlg.close()


def test_move_database_dialog(qapp, temp_env):
    """FR: Vérifie le dialogue de déplacement de base (move_database.fen).
    EN: Verifies the move database dialog (move_database.fen).
    """
    db = temp_env["db"]
    dlg = PicasaMoveDatabaseDialog(db)
    assert dlg.edit_current.text() == db.db_path
    new_loc = os.path.join(temp_env["dir"], "new_db_location")
    dlg.edit_target.setText(new_loc)
    assert os.path.isabs(dlg.edit_target.text())
    dlg.close()


def test_poster_dialog(qapp, temp_env):
    """FR: Vérifie la découpe multi-pages pour poster (poster.fen).
    EN: Verifies multi-page poster tiling (poster.fen).
    """
    photo_p = temp_env["photo1"]
    dlg = PicasaPosterDialog(photo_p)
    assert dlg.combo_size.currentIndex() == 0  # 200% = 2x2 = 4 pages
    assert "4 pages" in dlg.combo_factor.currentText()

    # Changement d'échelle à 300% (3x3 = 9 pages)
    dlg.combo_factor.setCurrentIndex(1)
    assert "9 pages" in dlg.combo_factor.currentText()
    assert dlg.preview.grid_size == 3
    dlg.close()


def test_web_export_dialog(qapp, temp_env):
    """FR: Vérifie la génération de galerie web HTML5 responsive (webexport.fen).
    EN: Verifies responsive HTML5 web gallery generation (webexport.fen).
    """
    paths = [temp_env["photo1"], temp_env["photo2"]]
    dlg = PicasaWebExportDialog(paths, default_title="Ma Galerie Web")

    out_folder = os.path.join(temp_env["dir"], "web_out")
    dlg.edit_dest.setText(out_folder)
    dlg.edit_title.setText("Super Galerie")

    # Génération
    dlg._generate_web_gallery()

    index_html = os.path.join(out_folder, "index.html")
    assert os.path.exists(index_html)
    content = open(index_html, encoding="utf-8").read()
    assert "Super Galerie" in content
    assert "photo1.jpg" in content
    assert "photo2.jpg" in content

    # Vérifier présence des miniatures exportées
    assert os.path.exists(os.path.join(out_folder, "images", "photo1.jpg"))
    assert os.path.exists(os.path.join(out_folder, "thumbnails", "photo1.jpg"))
    dlg.close()


def test_import_dialog(qapp, temp_env):
    """FR: Vérifie l'écran d'importation de médias (ACQUIREPANEL_TEXT_FR.XML).
    EN: Verifies the media import screen (ACQUIREPANEL_TEXT_FR.XML).
    """
    db = temp_env["db"]
    src_dir = os.path.join(temp_env["dir"], "camera_card")
    os.makedirs(src_dir, exist_ok=True)
    f1 = os.path.join(src_dir, "IMG_0001.JPG")
    f2 = os.path.join(src_dir, "IMG_0002.JPG")
    Image.new("RGB", (100, 100)).save(f1)
    Image.new("RGB", (100, 100)).save(f2)

    dlg = PicasaImportDialog(db=db, default_source_dir=src_dir)
    assert len(dlg.discovered_files) == 2
    assert dlg.list_widget.count() == 2

    # Sélection/Désélection
    dlg._deselect_all()
    assert sum(1 for i in range(dlg.list_widget.count()) if dlg.list_widget.item(i).checkState() == Qt.CheckState.Checked) == 0

    dlg._select_all()
    assert sum(1 for i in range(dlg.list_widget.count()) if dlg.list_widget.item(i).checkState() == Qt.CheckState.Checked) == 2
    dlg.close()


def test_database_compact(temp_env):
    """FR: Vérifie que la méthode compact() de PicasaDatabase s'exécute sans erreur.
    EN: Verifies that PicasaDatabase.compact() executes without error.
    """
    from picasa_py.db.blockfile import BlockContainerFile, BlockIndexFile, BlockEntry
    db = temp_env["db"]

    container = BlockContainerFile()
    blob1 = b"\xff\xd8\xff\xe0" + b"TEST_THUMB_1" + b"\xff\xd9"
    entry0 = BlockEntry(checksum=0, offset=0, size=0, block=0)
    entry1 = container.append_blob(blob1, checksum=0x1234, block_idx=0)
    idx_file = BlockIndexFile.from_entries([entry0, entry1], active_block=0)

    db.block_containers["thumbs"] = container
    db.block_indices["thumbs"] = idx_file

    res = db.compact()
    assert isinstance(res, tuple)
    assert res[0] >= res[1]

    # Vérifier que la miniature est toujours accessible après compactage
    cached = db.get_thumbnail(1, size="small")
    assert cached == blob1
