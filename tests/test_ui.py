"""
Tests for PyCasa UI components in offscreen mode.

Ref: AGENTS.md §4 bis (Fidélité de l'interface)
"""

import os
import sys
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Force offscreen platform for headless test execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.main_window import PicasaMainWindow
from picasa_py.ui.library_tree import PicasaLibraryTree
from picasa_py.ui.thumbnail_view import PicasaThumbnailView
from picasa_py.ui.photo_tray import PicasaPhotoTray
from picasa_py.ui.top_bar import PicasaTopBar
from picasa_py.ui.right_drawer import PicasaRightDrawer
from picasa_py.db.database import PicasaDatabase


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    return app


def test_style_loading():
    style = PicasaStyle.load()
    assert style.alist_height == 22
    assert style.alist_indent == 17
    assert style.alayout_gutter == 24
    assert style.alayout_thumbGutterX == 12
    assert style.alayout_thumbGutterY == 22
    assert style.thumbsel_color1.name().upper() == "#009EFF"
    assert style.thumbsel_color2.name().upper() == "#FFFFFF"


def test_resource_manager(qapp):
    res = PicasaResourceManager.get()
    # Check icons
    ico = res.get_icon(105)
    assert not ico.isNull()
    # Check cursors
    cur = res.get_cursor(1)
    assert cur is not None
    # Check strings
    assert res.get_string(200) == "Albums"
    assert res.get_string(196) == "Folders"


def test_main_window_instantiation(qapp):
    win = PicasaMainWindow()
    assert win.windowTitle() == "Picasa 3"
    assert win.top_bar is not None
    assert win.splitter is not None
    assert win.library_tree is not None
    assert win.thumb_view is not None
    assert win.right_drawer is not None
    assert win.photo_tray is not None
    assert win.menuBar() is not None
    assert win.status_bar is not None

    # Check menu titles
    actions = [m.title() for m in win.menuBar().findChildren(type(win.menuBar().addMenu("")))]
    for expected in ["&File", "&Edit", "&View", "&Folder", "&Picture", "&Create", "&Tools", "&Help"]:
        assert expected in actions

    # Check selection integration
    win.thumb_view.selected_indices = {0, 1}
    win._on_selection_changed([0, 1])
    assert "2 photos sélectionnées" in win.photo_tray.lbl_selection.text()

    # Check clear selection
    win.action_clear_selection()
    assert len(win.thumb_view.selected_indices) == 0
    assert "Aucune photo sélectionnée" in win.photo_tray.lbl_selection.text()

    win.close()
