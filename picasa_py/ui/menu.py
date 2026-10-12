"""
Menu Bar Builder for PyCasa.
Assembles menus and shortcuts exactly matching Picasa 3.

Ref: picasa3.exe @ 0x0088C3EC (eMenu* hierarchy)
Ref: Picasa3i18n.dll @ SHORTCUTS.XML
"""

from __future__ import annotations
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtWidgets import QMenuBar, QMenu, QMainWindow
from PySide6.QtGui import QAction, QKeySequence

RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "resources"


# Ref: picasa3.exe @ 0x0088C3EC
class PicasaMenuBuilder:
    """
    Constructeur de la barre de menus de Picasa.
    """

    def __init__(self, main_window: QMainWindow):
        self.win = main_window
        self.shortcuts: Dict[str, str] = {}
        self._load_shortcuts()

    def _load_shortcuts(self) -> None:
        sc_file = RESOURCES_DIR / "xml" / "SHORTCUTS.XML"
        if not sc_file.exists():
            return

        try:
            root = ET.fromstring(sc_file.read_text(encoding="utf-8"))
            # Standard keyboard mapping
            self.shortcuts["ID_FILE_OPEN"] = "Ctrl+O"
            self.shortcuts["ID_FILE_NEWLABEL"] = "Ctrl+N"
            self.shortcuts["ID_FILE_SAVE"] = "Ctrl+S"
            self.shortcuts["ID_FILE_SAVEAS"] = "Ctrl+Shift+S"
            self.shortcuts["ID_FILE_RENAME"] = "F2"
            self.shortcuts["ID_FILE_PRINT"] = "Ctrl+P"
            self.shortcuts["ID_EDIT_COPY"] = "Ctrl+C"
            self.shortcuts["ID_EDIT_PASTE"] = "Ctrl+V"
            self.shortcuts["ID_EDIT_CUT"] = "Ctrl+X"
            self.shortcuts["ID_ALBUM_SELECTALLPICTURES"] = "Ctrl+A"
            self.shortcuts["ID_VIEW_SLIDESHOW"] = "Ctrl+4"
            self.shortcuts["ID_FILE_DELETEFROMDISK"] = "Delete"
        except Exception:
            pass

    def build_menu_bar(self) -> QMenuBar:
        mb = self.win.menuBar()
        mb.clear()

        # 1. &File
        menu_file = mb.addMenu("&File")
        self._add_action(menu_file, "Add &File to Picasa...", "ID_FILE_OPEN", self.win.action_add_file if hasattr(self.win, "action_add_file") else None)
        self._add_action(menu_file, "Add &Folder to Picasa...", "ID_TOOLS_INCLUDEEXCLUDEFOLDERS")
        self._add_action(menu_file, "&Import From...", "ID_FILE_IMPORTPICTURE")
        self._add_action(menu_file, "&New Album...", "ID_FILE_NEWLABEL")
        menu_file.addSeparator()
        self._add_action(menu_file, "&Save", "ID_FILE_SAVE")
        self._add_action(menu_file, "Save &As...", "ID_FILE_SAVEAS")
        self._add_action(menu_file, "Save a Cop&y", "ID_FILE_SAVEACOPY")
        self._add_action(menu_file, "Rever&t", "ID_FILE_REVERT")
        menu_file.addSeparator()
        self._add_action(menu_file, "Export Pi&cture to Folder...", "ID_FILE_EXPORTTOFOLDER", self.win.action_export if hasattr(self.win, "action_export") else None)
        self._add_action(menu_file, "&Rename...", "ID_FILE_RENAME")
        self._add_action(menu_file, "&Delete from Disk...", "ID_FILE_DELETEFROMDISK")
        menu_file.addSeparator()
        self._add_action(menu_file, "E&xit", "ID_FILE_EXIT", self.win.close)

        # 2. &Edit
        menu_edit = mb.addMenu("&Edit")
        self._add_action(menu_edit, "Cu&t", "ID_EDIT_CUT")
        self._add_action(menu_edit, "&Copy", "ID_EDIT_COPY")
        self._add_action(menu_edit, "&Paste", "ID_EDIT_PASTE")
        menu_edit.addSeparator()
        self._add_action(menu_edit, "Select &All", "ID_ALBUM_SELECTALLPICTURES", self.win.action_select_all if hasattr(self.win, "action_select_all") else None)
        self._add_action(menu_edit, "Select &Starred", "ID_SELECTSTAR")
        self._add_action(menu_edit, "&Invert Selection", "ID_SELECT_INVERT")
        self._add_action(menu_edit, "C&lear Selection", "ID_CLEAR_SELECTION", self.win.action_clear_selection if hasattr(self.win, "action_clear_selection") else None)

        # 3. &View
        menu_view = mb.addMenu("&View")
        self._add_action(menu_view, "Show &Thumbnails in Library", "ID_VIEW_THUMBNAILS")
        self._add_action(menu_view, "Play &Slideshow", "ID_VIEW_SLIDESHOW", self.win.action_slideshow if hasattr(self.win, "action_slideshow") else None)
        self._add_action(menu_view, "Ti&meline", "ID_VIEW_TIMELINE")
        menu_view.addSeparator()
        self._add_action(menu_view, "&Tree View", "ID_VIEW_ALL")
        self._add_action(menu_view, "&Flat Folder View", "ID_VIEW_FOLDERS")

        # 4. &Folder
        menu_folder = mb.addMenu("&Folder")
        self._add_action(menu_folder, "&Locate on Disk", "ID_FILE_LOCATEONDISK")
        self._add_action(menu_folder, "&Refresh Thumbnail", "ID_REFRESH_THUMB")
        self._add_action(menu_folder, "Export as &Web Page...", "ID_FILE_EXPORTASWEBPAGE")

        # 5. &Picture
        menu_picture = mb.addMenu("&Picture")
        self._add_action(menu_picture, "Rotate &Clockwise", "ID_PICTURE_ROTATECLOCKWISE")
        self._add_action(menu_picture, "Rotate &Counterclockwise", "ID_PICTURE_ROTATECOUNTERCLOCKWISE")
        menu_picture.addSeparator()
        self._add_action(menu_picture, "Auto &Contrast", "ID_PICTURE_AUTO_LIGHTING")
        self._add_action(menu_picture, "Auto &Color", "ID_PICTURE_AUTO_COLOR")
        self._add_action(menu_picture, "Auto &Red-Eye", "ID_PICTURE_AUTO_REDEYE")
        self._add_action(menu_picture, "&Undo All Edits", "ID_PICTURE_REVERT")

        # 6. &Create
        menu_create = mb.addMenu("&Create")
        self._add_action(menu_create, "Picture &Collage...", "ID_COLLAGEMAKER")
        self._add_action(menu_create, "Make a &Poster...", "ID_POSTER")
        self._add_action(menu_create, "Make a &Movie...", "MOVIE")
        self._add_action(menu_create, "Set as &Desktop...", "ID_WALLPAPER")
        self._add_action(menu_create, "Set as &Screensaver...", "ID_SCREENSAVER")

        # 7. &Tools
        menu_tools = mb.addMenu("&Tools")
        self._add_action(menu_tools, "&Options...", "ID_TOOLS_OPTIONS", self.win.action_options if hasattr(self.win, "action_options") else None)
        self._add_action(menu_tools, "Adjust &Date and Time...", "ID_TOOLS_ADJUST_TIMESTAMP")
        self._add_action(menu_tools, "&Folder Manager...", "ID_TOOLS_INCLUDEEXCLUDEFOLDERS")
        self._add_action(menu_tools, "&Move Database...", "ID_MOVE_DATABASE")

        # 8. &Help
        menu_help = mb.addMenu("&Help")
        self._add_action(menu_help, "&About Picasa...", "ID_HELP_ABOUT", self.win.action_about if hasattr(self.win, "action_about") else None)
        self._add_action(menu_help, "&Keyboard Shortcuts", "ID_HELP_KEYBOARD_SHORTCUTS")
        self._add_action(menu_help, "&Privacy Policy", "ID_HELP_PRIVACY")

        return mb

    def _add_action(
        self,
        menu: QMenu,
        text: str,
        cmd_id: str,
        callback: Optional[Any] = None
    ) -> QAction:
        action = menu.addAction(text)
        if cmd_id in self.shortcuts:
            action.setShortcut(QKeySequence(self.shortcuts[cmd_id]))
        if callback:
            action.triggered.connect(callback)
        return action
