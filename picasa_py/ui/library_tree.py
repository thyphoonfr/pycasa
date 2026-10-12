"""
Library Tree component for PyCasa (Left Sidebar).
Displays Albums, People, Folders, and Projects.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2] alist_*
Ref: picasa3.exe @ 0x0088C3EC (eMenuLabelFolder)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from pathlib import Path
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QWidget, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.database import PicasaDatabase


# Ref: constants.ui [Picasa2] alist_*
class PicasaLibraryTree(QWidget):
    """
    Volet latéral gauche de navigation (Albums, Personnes, Dossiers, Projets).
    """
    # Signal émis lors de la sélection d'un dossier ou album (identifiant, type, nom)
    folder_selected = Signal(str, str, str)  # (target_key, target_type, display_name)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(self.style.alist_indent)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.style.alist_bgcolor.name()};
                border: none;
                font-size: {self.style.alist_fontsize_win}px;
                color: #222222;
            }}
            QTreeWidget::item {{
                height: {self.style.alist_height}px;
                padding-left: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {self.style.alist_selcolor_win.name()};
                color: #FFFFFF;
            }}
            QTreeWidget::item:hover:!selected {{
                background-color: {self.style.alist_hicolor_win.name()};
            }}
        """)

        layout.addWidget(self.tree)
        self.tree.itemClicked.connect(self._on_item_clicked)

        # Categories
        self.cat_albums: Optional[QTreeWidgetItem] = None
        self.cat_people: Optional[QTreeWidgetItem] = None
        self.cat_folders: Optional[QTreeWidgetItem] = None
        self.cat_projects: Optional[QTreeWidgetItem] = None

        self._init_categories()

    def _init_categories(self) -> None:
        self.tree.clear()

        def _create_cat(title: str, icon_id: int) -> QTreeWidgetItem:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, title)
            item.setIcon(0, self.res_mgr.get_icon(icon_id))
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setBackground(0, self.style.alist_catcolor)
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "key": title})
            item.setExpanded(True)
            return item

        # Ref: strings.json (200: Albums, 196: Folders, 299: Projects)
        self.cat_albums = _create_cat(self.res_mgr.get_string(200, "Albums"), 152)
        self.cat_people = _create_cat("People", 159)
        self.cat_folders = _create_cat(self.res_mgr.get_string(196, "Folders"), 150)
        self.cat_projects = _create_cat(self.res_mgr.get_string(299, "Projects"), 161)

    def populate_from_database(self, db: PicasaDatabase) -> None:
        """
        Remplit l'arborescence à partir des tables réelles de PicasaDatabase.
        """
        self._init_categories()

        # 1. Regrouper les images par dossier
        folder_counts: Dict[str, int] = {}
        for entry in db.index:
            path_str = entry.path
            folder_name = Path(path_str).parent.name or "Root"
            folder_counts[folder_name] = folder_counts.get(folder_name, 0) + 1

        for folder_name, count in sorted(folder_counts.items()):
            item = QTreeWidgetItem(self.cat_folders)
            item.setText(0, f"{folder_name} ({count})")
            item.setIcon(0, self.res_mgr.get_icon(150))
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "key": folder_name, "name": folder_name})

        # 2. Contacts / People
        if db.contacts:
            for cid, contact in sorted(db.contacts.contacts.items(), key=lambda x: x[1].name):
                item = QTreeWidgetItem(self.cat_people)
                item.setText(0, contact.name)
                item.setIcon(0, self.res_mgr.get_icon(159))
                item.setData(0, Qt.ItemDataRole.UserRole, {"type": "person", "key": cid, "name": contact.name})

        # 3. Virtual Albums
        if db.catdata and "name" in db.catdata:
            cat_names = db.catdata["name"]
            for i in range(cat_names.entry_count):
                album_name = cat_names.get_value(i)
                if album_name:
                    item = QTreeWidgetItem(self.cat_albums)
                    item.setText(0, str(album_name))
                    item.setIcon(0, self.res_mgr.get_icon(152))
                    item.setData(0, Qt.ItemDataRole.UserRole, {"type": "album", "key": str(album_name), "name": str(album_name)})

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") in ("folder", "album", "person"):
            self.folder_selected.emit(data["key"], data["type"], data["name"])
