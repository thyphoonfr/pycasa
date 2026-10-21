"""
FR: Tests pour la fonctionnalité Étoile / Favoris de Picasa 3 et les actions du Photo Tray.
EN: Tests for Picasa 3 Star / Favorites functionality and Photo Tray actions.

Ref: picasa3.exe @ 0x0088F6FC (thumbui/startoggle), 0x0068B800 ("star=yes")
Ref: picasa3.exe @ editpanel/star_icon, CThumbDB::starredphotos, ID_PICTURE_STAR
Ref: picasa3.exe @ il_CollageButton, il_MakeMovieButton
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QMouseEvent, QPointingDevice

from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.db.database import PicasaDatabase
from picasa_py.ui.photo_tray import PicasaPhotoTray
from picasa_py.ui.thumbnail_view import PicasaThumbnailView, ThumbnailItem
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.ui.library_tree import PicasaLibraryTree


@pytest.fixture(scope="session")
def qapp():
    """
    FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provide a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_ini_star_property(tmp_path):
    """
    FR: Vérifie la sérialisation exacte et la lecture de star=yes dans .picasa.ini.
    EN: Verify exact serialization and parsing of star=yes in .picasa.ini.
    """
    ini_path = tmp_path / ".picasa.ini"
    doc = PicasaIniDocument()
    doc.set_starred("sample.jpg", True)
    doc.write_file(ini_path)

    # Vérification binaire / textuelle
    content = ini_path.read_text(encoding="utf-8")
    assert "[sample.jpg]" in content
    assert "star=yes" in content

    # Relecture
    parsed = PicasaIniParser.parse_file(str(ini_path))
    assert parsed.is_starred("sample.jpg") is True
    assert parsed.is_starred("other.jpg") is False

    # Retrait de l'étoile
    parsed.set_starred("sample.jpg", False)
    parsed.write_file(str(ini_path))
    reparsed = PicasaIniParser.parse_file(str(ini_path))
    assert reparsed.is_starred("sample.jpg") is False


def test_database_get_starred_photo_paths(tmp_path):
    """
    FR: Vérifie que PicasaDatabase.get_starred_photo_paths retrouve correctement les photos étoilées.
    EN: Verify that PicasaDatabase.get_starred_photo_paths properly retrieves starred photos.
    """
    folder = tmp_path / "MyPhotos"
    folder.mkdir()
    p1 = folder / "img1.jpg"
    p2 = folder / "img2.jpg"
    p1.write_bytes(b"dummy1")
    p2.write_bytes(b"dummy2")

    ini = folder / ".picasa.ini"
    doc = PicasaIniDocument()
    doc.set_starred("img1.jpg", True)
    doc.set_starred("img2.jpg", False)
    doc.write_file(ini)

    db = PicasaDatabase(db3_dir=tmp_path / "db3")
    db.set_watched_folder(str(folder), "1")  # Scan Always

    starred = db.get_starred_photo_paths()
    assert str(p1) in starred
    assert str(p2) not in starred


def test_photo_tray_star_and_buttons(qapp):
    """
    FR: Vérifie les boutons Star, Montage et Film sur le Photo Tray.
    EN: Verify the Star, Collage, and Movie buttons on the Photo Tray.
    """
    tray = PicasaPhotoTray()

    assert hasattr(tray, "btn_star")
    assert hasattr(tray, "btn_collage")
    assert hasattr(tray, "btn_movie")

    # Boutons activés lorsqu'une sélection est présente
    tray.set_selected_count(1)
    assert tray.btn_star.isEnabled()

    assert tray.btn_star.text() == "☆"

    # Mise à jour de l'état
    tray.update_star_state(True)
    assert tray.btn_star.text() == "★"

    tray.update_star_state(False)
    assert tray.btn_star.text() == "☆"

    # Vérification des signaux
    star_called = []
    collage_called = []
    movie_called = []
    tray.action_star.connect(lambda: star_called.append(True))
    tray.action_collage.connect(lambda: collage_called.append(True))
    tray.action_movie.connect(lambda: movie_called.append(True))

    tray.btn_star.click()
    tray.btn_collage.click()
    tray.btn_movie.click()

    assert len(star_called) == 1
    assert len(collage_called) == 1
    assert len(movie_called) == 1


def test_one_up_view_star_button_and_shortcut(qapp, tmp_path):
    """
    FR: Vérifie le bouton Favori et son raccourci dans One-Up View.
    EN: Verify the Favorite star button and its shortcut in the One-Up View.
    """
    photo_file = tmp_path / "test.jpg"
    photo_file.write_bytes(b"dummy")

    view = PicasaOneUpView()
    assert hasattr(view, "btn_star")
    assert view.btn_star.text() == "☆ Favori"

    # Ouvrir la photo
    view._current_photo_path = str(photo_file)
    view.update_star_button(False)
    assert view.btn_star.text() == "☆ Favori"

    star_events = []
    view.star_toggled.connect(lambda p, st: star_events.append((p, st)))

    # Clic sur le bouton favori
    view.btn_star.click()
    assert view.btn_star.text() == "★ Favori"
    assert len(star_events) == 1
    assert star_events[-1] == (str(photo_file), True)

    # Deuxième clic pour retirer le favori
    view.btn_star.click()
    assert view.btn_star.text() == "☆ Favori"
    assert len(star_events) == 2
    assert star_events[-1] == (str(photo_file), False)


def test_thumbnail_view_filter_by_starred(qapp):
    """
    FR: Vérifie le filtrage de la grille par photos favorites.
    EN: Verify filtering the thumbnail grid by starred photos.
    """
    view = PicasaThumbnailView()
    view.items = [
        ThumbnailItem(index=0, path="pic1.jpg", filename="pic1.jpg", folder="test", folder_path="", starred=True),
        ThumbnailItem(index=1, path="pic2.jpg", filename="pic2.jpg", folder="test", folder_path="", starred=False),
        ThumbnailItem(index=2, path="pic3.jpg", filename="pic3.jpg", folder="test", folder_path="", starred=True),
    ]

    view.filter_by_starred()
    assert view.filtered_indices == [0, 2]
    assert len(view.visible_sections) == 1
    assert view.visible_sections[0].name == "Photos favorites"
    assert view.visible_sections[0].item_indices == [0, 2]


def test_library_tree_starred_album(qapp, tmp_path):
    """
    FR: Vérifie la présence de l'album virtuel épinglé 'Photos favorites' dans l'arborescence.
    EN: Verify the presence of the pinned 'Starred Photos' virtual album in the library tree.
    """
    folder = tmp_path / "Photos"
    folder.mkdir()
    p1 = folder / "star1.jpg"
    p1.write_bytes(b"dummy")

    ini = folder / ".picasa.ini"
    doc = PicasaIniDocument()
    doc.set_starred("star1.jpg", True)
    doc.write_file(ini)

    db = PicasaDatabase(db3_dir=tmp_path / "db3")
    db.set_watched_folder(str(folder), "1")

    tree = PicasaLibraryTree()
    tree.db = db
    tree.refresh_albums()

    assert tree.cat_albums is not None
    assert tree.cat_albums.childCount() >= 1

    first_item = tree.cat_albums.child(0)
    data = first_item.data(0, Qt.ItemDataRole.UserRole)
    assert data["type"] == "starred"
    assert "Photos favorites" in first_item.text(0)
    assert "(1)" in first_item.text(0)


def test_context_menu_star_action(qapp, tmp_path):
    """
    FR: Vérifie que le menu contextuel d'une photo propose bien 'Add/Remove Star' avec le raccourci Ctrl+T.
    EN: Verify that a photo's context menu offers 'Add/Remove Star' with the Ctrl+T shortcut.
    """
    from picasa_py.ui.context_menu import PicasaContextMenuBuilder

    photo_path = str(tmp_path / "photo.jpg")
    Path(photo_path).write_bytes(b"dummy")

    mock_main = MagicMock()
    menu = PicasaContextMenuBuilder.build_photo_context_menu(
        parent=None,
        photo_paths=[photo_path],
        db=None,
        is_in_album=False,
        main_win=mock_main,
    )
    assert menu is not None

    star_actions = [act for act in menu.actions() if "Star" in act.text() or "étoile" in act.text().lower()]
    assert len(star_actions) >= 1
    star_act = star_actions[0]
    assert star_act.shortcut().toString() == "Ctrl+T"

    star_act.trigger()
    assert mock_main.action_toggle_star.called
