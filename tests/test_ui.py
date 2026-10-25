"""
FR: Tests des composants d'interface PyCasa en mode hors-écran (offscreen).
EN: Tests for PyCasa UI components in offscreen mode.

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
    """
    FR: Fournit une instance QApplication en mode offscreen pour la session de tests.
    EN: Provide an offscreen QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    return app


def test_style_loading():
    """
    FR: Vérifie que PicasaStyle.load() charge les constantes de mise en page et de couleurs attendues.
    EN: Verify that PicasaStyle.load() loads the expected layout and color constants.
    """
    style = PicasaStyle.load()
    assert style.alist_height == 22
    assert style.alist_indent == 17
    assert style.alayout_gutter == 24
    assert style.alayout_thumbGutterX == 12
    assert style.alayout_thumbGutterY == 22
    assert style.thumbsel_color1.name().upper() == "#009EFF"
    assert style.thumbsel_color2.name().upper() == "#FFFFFF"


def test_resource_manager(qapp):
    """
    FR: Vérifie l'accès aux icônes, curseurs et chaînes via PicasaResourceManager.
    EN: Verify access to icons, cursors, and strings via PicasaResourceManager.
    """
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
    """
    FR: Vérifie l'instanciation de PicasaMainWindow, ses sous-composants, ses menus et la sélection.
    EN: Verify PicasaMainWindow instantiation, subcomponents, menus, and selection handling.
    """
    from picasa_py.version import APP_NAME, APP_VERSION, get_window_title

    win = PicasaMainWindow()
    assert win.windowTitle() == get_window_title()
    assert win.windowTitle() == f"{APP_NAME} {APP_VERSION}"
    assert win.top_bar is not None
    assert win.splitter is not None
    assert win.library_tree is not None
    assert win.thumb_view is not None
    assert win.right_drawer is not None
    assert win.photo_tray is not None
    assert win.menuBar() is not None
    assert win.status_bar is not None

    # Check menu titles (EN or FR localization)
    actions = [m.title() for m in win.menuBar().findChildren(type(win.menuBar().addMenu("")))]
    assert len(actions) >= 8

    # Check selection integration
    win.thumb_view.selected_indices = {0, 1}
    win._on_selection_changed([0, 1])
    assert "2 photo" in win.photo_tray.lbl_selection.text()

    # Check clear selection
    win.action_clear_selection()
    assert len(win.thumb_view.selected_indices) == 0
    assert "0 photo" in win.photo_tray.lbl_selection.text() or "Aucune" in win.photo_tray.lbl_selection.text()
    win.close()

    win.stop_background_tasks()
    win.close()
    qapp.processEvents()


def test_version_and_about_dialog(qapp, monkeypatch):
    """
    FR: Vérifie le format du numéro de version z.y.x.w et le contenu de la boîte de dialogue À propos.
    EN: Verify the z.y.x.w version number format and the contents of the About dialog.
    """
    from PySide6.QtWidgets import QMessageBox
    from picasa_py.version import (
        APP_NAME,
        APP_VERSION,
        VERSION_W,
        VERSION_X,
        VERSION_Y,
        VERSION_Z,
        get_about_dialog_text,
        get_about_dialog_title,
        get_window_title,
    )

    win = PicasaMainWindow()
    assert win.windowTitle() == f"{APP_NAME} {APP_VERSION}"
    assert APP_NAME == "PyCasa"
    assert VERSION_Z == 3
    assert VERSION_Y == 9
    assert VERSION_X >= 145
    assert VERSION_W >= 260
    assert APP_VERSION == f"{VERSION_Z}.{VERSION_Y}.{VERSION_X}.{VERSION_W}"

    captured = {}

    def fake_about(parent, title, text):
        """
        FR: Capture le titre et le texte passés à QMessageBox.about.
        EN: Capture the title and text passed to QMessageBox.about.
        """
        captured["title"] = title
        captured["text"] = text

    monkeypatch.setattr(QMessageBox, "about", fake_about)
    win.action_about()

    assert APP_NAME in captured["title"]
    assert f"{APP_NAME} {APP_VERSION}" in captured["text"]
    assert APP_VERSION in captured["text"]

    win.stop_background_tasks()
    win.close()
    qapp.processEvents()

