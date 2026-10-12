"""
Library Tree component for PyCasa (Left Sidebar).
Displays Albums, People, Folders, and Projects.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2] alist_*
Ref: picasa3.exe @ albumdata_category.pmp (cat=2 Folders, cat=0 Albums, cat=8 People)
"""

from __future__ import annotations
import os
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QWidget, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.database import PicasaDatabase


def _norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


# Ref: constants.ui [Picasa2] alist_*
class PicasaLibraryTree(QWidget):
    """
    Volet latéral gauche de navigation fidèle aux dossiers et albums de Picasa.
    """
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

        self.cat_albums = _create_cat(self.res_mgr.get_string(200, "Albums"), 152)
        self.cat_people = _create_cat("People", 159)
        self.cat_folders = _create_cat(self.res_mgr.get_string(196, "Folders"), 150)
        self.cat_projects = _create_cat(self.res_mgr.get_string(299, "Projects"), 161)

    def populate_from_database(self, db: PicasaDatabase) -> None:
        """
        Remplit l'arborescence en utilisant la table albumdata (cat=2 pour les dossiers réels).
        """
        self._init_categories()

        # 1. Cartographier les répertoires et compter les photos par dossier
        ti_folders = {i: r.path for i, r in enumerate(db.index) if r.type == 1}

        folder_media_count: Dict[str, int] = {}
        for r in db.index:
            if r.type in (2, 6, 7, 13, 18, 31):
                fpath = ti_folders.get(r.parent_idx, "")
                if fpath:
                    k = _norm(fpath)
                    folder_media_count[k] = folder_media_count.get(k, 0) + 1

        # 2. Dossiers configurés dans albumdata (cat == 2)
        ad_names = db.pmps.get("albumdata_name")
        ad_cats = db.pmps.get("albumdata_category")
        ad_files = db.pmps.get("albumdata_filename")

        added_norm_paths: Set[str] = set()

        if ad_names and ad_cats and ad_files:
            names = ad_names.records
            cats = ad_cats.records
            files = ad_files.records
            folder_items = []
            for i in range(len(names)):
                if cats[i] == 2:  # Dossier réel visible dans Picasa
                    fpath = files[i] if i < len(files) else ""
                    norm_k = _norm(fpath)
                    count = folder_media_count.get(norm_k, 0)
                    if count > 0:
                        folder_items.append((names[i], count, fpath, norm_k))

            # Trier les dossiers par nom alphabétique
            for name, count, fpath, norm_k in sorted(folder_items, key=lambda x: x[0].lower()):
                item = QTreeWidgetItem(self.cat_folders)
                item.setText(0, f"{name} ({count})")
                item.setIcon(0, self.res_mgr.get_icon(150))
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "folder",
                    "key": fpath,
                    "name": name,
                })
                added_norm_paths.add(norm_k)

        # 3. Albums virtuels (cat == 0 dans albumdata)
        if ad_names and ad_cats:
            names = ad_names.records
            cats = ad_cats.records
            for i in range(len(names)):
                if cats[i] == 0:
                    name = names[i]
                    item = QTreeWidgetItem(self.cat_albums)
                    item.setText(0, name)
                    item.setIcon(0, self.res_mgr.get_icon(152))
                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "album",
                        "key": name,
                        "name": name,
                    })

        # 4. Contacts / Visages (cat == 8 dans albumdata ou contacts.xml)
        if ad_names and ad_cats:
            names = ad_names.records
            cats = ad_cats.records
            for i in range(len(names)):
                if cats[i] == 8:
                    name = names[i]
                    item = QTreeWidgetItem(self.cat_people)
                    item.setText(0, name)
                    item.setIcon(0, self.res_mgr.get_icon(159))
                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "person",
                        "key": name,
                        "name": name,
                    })
        elif db.contacts:
            for cid, contact in sorted(db.contacts.contacts.items(), key=lambda x: x[1].name):
                item = QTreeWidgetItem(self.cat_people)
                item.setText(0, contact.name)
                item.setIcon(0, self.res_mgr.get_icon(159))
                item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "person",
                    "key": cid,
                    "name": contact.name,
                })

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") in ("folder", "album", "person"):
            self.folder_selected.emit(data["key"], data["type"], data["name"])
        elif data and data.get("type") == "category":
            # Cliquer sur la catégorie "Folders" ou "Albums" réinitialise la vue à toutes les photos
            self.folder_selected.emit("", "all", "Toutes les photos")
