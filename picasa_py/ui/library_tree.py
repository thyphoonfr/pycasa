"""
FR: Composant de l'arborescence de la photothèque de PyCasa (volet latéral gauche).
Affiche les Albums, Personnes, Dossiers et Projets.
EN: Library Tree component for PyCasa (Left Sidebar).
Displays Albums, People, Folders, and Projects.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2] alist_*
Ref: picasa3.exe @ albumdata_category.pmp (cat=2 Folders, cat=0 Albums, cat=8 People)
"""

from __future__ import annotations
import os
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QWidget, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt, Signal, QSize, QMimeData, QTimer, QSignalBlocker
from PySide6.QtGui import QColor, QFont, QIcon, QContextMenuEvent, QDragEnterEvent, QDragMoveEvent, QDropEvent, QWheelEvent, QMouseEvent

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.context_menu import PicasaContextMenuBuilder
from picasa_py.db.database import PicasaDatabase
from picasa_py.scanner.scanner import BackgroundScanWorker


def _norm(path: str) -> str:
    """
    FR: Normalise un chemin de fichier en minuscules avec des barres obliques '/' sans barre finale.
    EN: Normalizes a file path to lowercase with forward slashes '/' and no trailing slash.
    """
    return path.replace("\\", "/").rstrip("/").lower()


def _extract_photo_paths_from_mime(mime: QMimeData) -> List[str]:
    """
    FR: Extrait la liste des chemins de photos depuis les données MIME d'un glisser-déposer.
    EN: Extracts the list of photo file paths from drag-and-drop QMimeData.
    """
    if mime.hasFormat("application/x-picasa-photo-paths"):
        raw = bytes(mime.data("application/x-picasa-photo-paths")).decode("utf-8", errors="ignore")
        return [p.strip() for p in raw.splitlines() if p.strip()]
    if mime.hasUrls():
        return [u.toLocalFile() for u in mime.urls() if u.isLocalFile() and u.toLocalFile()]
    return []


class _PicasaDropTreeWidget(QTreeWidget):
    """
    FR: QTreeWidget acceptant le glisser-déposer de vignettes vers un album ou un dossier.
    EN: QTreeWidget accepting drag-and-drop of thumbnails onto an album or folder.
    Ref: picasa3.exe @ constants.ui [Picasa2] alist_dragcolor=#82A6BD
    """
    def __init__(self, owner: "PicasaLibraryTree", parent: Optional[QWidget] = None):
        """
        FR: Initialise l'arbre supportant le dépôt de fichiers et référence son conteneur PicasaLibraryTree.
        EN: Initializes the drop-enabled tree widget and stores a reference to its PicasaLibraryTree owner.
        """
        super().__init__(parent)
        self.owner = owner
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        FR: Accepte l'entrée du glisser-déposer si les données MIME contiennent des chemins de photos.
        EN: Accepts the drag enter event if the MIME data contains valid photo paths.
        """
        paths = _extract_photo_paths_from_mime(event.mimeData())
        if paths:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """
        FR: Autorise le survol de dépôt uniquement sur les éléments de type album, dossier ou favoris.
        EN: Allows drag move drop target highlighting only over album, folder, or starred items.
        """
        paths = _extract_photo_paths_from_mime(event.mimeData())
        if not paths:
            event.ignore()
            return
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item:
            ud = item.data(0, Qt.ItemDataRole.UserRole)
            if ud and ud.get("type") in ("album", "folder", "starred"):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        FR: Délègue le dépôt des photos sur l'élément ciblé au PicasaLibraryTree propriétaire.
        EN: Delegates the photo drop action on the target item to the owning PicasaLibraryTree.
        """
        paths = _extract_photo_paths_from_mime(event.mimeData())
        if not paths:
            event.ignore()
            return
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item and self.owner.handle_drop_on_item(item, paths):
            event.acceptProposedAction()
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        FR: Signale l'activité de défilement de l'arborescence afin de suspendre les rafraîchissements de scan concurrents.
        EN: Signals library tree wheel scrolling activity to defer concurrent background scan UI refreshes.
        Ref: picasa3.exe @ 0x005D41F4 (CAlbumListUI::UpdateCategory)
        """
        BackgroundScanWorker.notify_gui_activity()
        super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Signale l'interaction souris dans l'arborescence pour éviter toute interruption par un scan en arrière-plan.
        EN: Signals mouse press interaction in the library tree to avoid interruption by background scanning.
        Ref: picasa3.exe @ 0x005D41F4 (CAlbumListUI::UpdateCategory)
        """
        BackgroundScanWorker.notify_gui_activity()
        super().mousePressEvent(event)


# Ref: constants.ui [Picasa2] alist_*
class PicasaLibraryTree(QWidget):
    """
    FR: Volet latéral gauche de navigation fidèle aux dossiers et albums de Picasa.
    EN: Left navigation sidebar faithful to Picasa folders, albums, and people categories.
    """
    folder_selected = Signal(str, str, str)  # (target_key, target_type, display_name)
    photos_dropped_on_album = Signal(str, list)  # (album_token, photo_paths)
    photos_dropped_on_folder = Signal(str, list)  # (folder_path, photo_paths)
    photos_dropped_on_starred = Signal(list)  # (photo_paths)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise le composant d'arborescence de la photothèque et ses catégories racines.
        EN: Initializes the library tree component and its top-level categories.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        from PySide6.QtWidgets import QAbstractItemView
        self.tree = _PicasaDropTreeWidget(self, self)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(self.style.alist_indent)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.verticalScrollBar().setSingleStep(self.style.alist_height)
        self.tree.verticalScrollBar().valueChanged.connect(lambda _: BackgroundScanWorker.notify_gui_activity())
        self.tree.verticalScrollBar().sliderPressed.connect(BackgroundScanWorker.notify_gui_activity)
        header = self.tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.tree)
        self.tree.setIconSize(QSize(22, 22))
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemCollapsed.connect(self._on_item_collapsed)

        self.db: Optional[PicasaDatabase] = None
        self.folder_view_mode: str = "flat"  # FR: "flat" (ID_VIEW_FOLDERS) ou "tree" (ID_VIEW_ALL) / EN: "flat" or "tree"
        self.show_hidden: bool = False  # Ref: picasa3.exe @ 0x00748185, 0x00748610 (ShowHidden reveals Hidden Folders)
        self._cached_hidden_folder_items: List[Tuple[str, int, str, str]] = []
        self._updating_hidden_cat: bool = False
        self.cat_albums: Optional[QTreeWidgetItem] = None
        self.cat_people: Optional[QTreeWidgetItem] = None
        self.cat_folders: Optional[QTreeWidgetItem] = None
        self.cat_hidden_folders: Optional[QTreeWidgetItem] = None
        self.cat_projects: Optional[QTreeWidgetItem] = None
        self._pending_tree_avatars: List[Tuple[QTreeWidgetItem, str]] = []
        self._avatar_timer = QTimer(self)
        self._avatar_timer.setInterval(12)
        self._avatar_timer.timeout.connect(self._load_next_tree_avatars)

        self.apply_style(self.style)
        self._init_categories()

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleur PicasaStyle à l'arborescence et à ses barres de défilement.
        EN: Dynamically applies the PicasaStyle color theme to the library tree and its scrollbars.
        """
        if style is None:
            style = PicasaStyle.instance()
        self.style = style
        self.tree.setIndentation(self.style.alist_indent)
        self.tree.verticalScrollBar().setSingleStep(self.style.alist_height)
        txt_col = getattr(self.style, "alist_textcolor", QColor("#222222")).name()
        bg_col = self.style.alist_bgcolor.name()
        bg_end = getattr(self.style, "alist_bgcolor_end", self.style.alist_bgcolor).name()
        sel_col = self.style.alist_selcolor_win.name()
        sel_end = getattr(self.style, "accent_grad_end", self.style.alist_selcolor_win).name()
        tree_bg = (
            f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {bg_col}, stop:1 {bg_end})"
            if bg_col != bg_end
            else bg_col
        )
        sel_bg = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {sel_col}, stop:1 {sel_end})"
            if sel_col != sel_end
            else sel_col
        )
        is_dark = getattr(self.style, "is_dark", False)
        sb_track = self.style.alist_catcolor.name() if not is_dark else self.style.window_bgcolor.name()
        sb_border = self.style.topbar_border_color.name()
        sb_handle = (
            self.style.topbar_btn_border.darker(115).name()
            if not is_dark
            else self.style.topbar_btn_border.lighter(130).name()
        )
        sb_hover = self.style.alist_selcolor_win.name()
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {tree_bg};
                border: none;
                font-size: {self.style.alist_fontsize_win}px;
                color: {txt_col};
            }}
            QTreeWidget::item {{
                height: {self.style.alist_height}px;
                padding-left: 4px;
            }}
            QTreeWidget::item:selected {{
                background: {sel_bg};
                color: #FFFFFF;
            }}
            QTreeWidget::item:hover:!selected {{
                background-color: {self.style.alist_hicolor_win.name()};
            }}
            QScrollBar:vertical {{
                background: {sb_track};
                width: 14px;
                margin: 0px;
                border-left: 1px solid {sb_border};
            }}
            QScrollBar::handle:vertical {{
                background: {sb_handle};
                min-height: 28px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:vertical:pressed {{
                background: {sb_hover};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background: {sb_track};
                height: 12px;
                margin: 0px;
                border-top: 1px solid {sb_border};
            }}
            QScrollBar::handle:horizontal {{
                background: {sb_handle};
                min-width: 28px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover,
            QScrollBar::handle:horizontal:pressed {{
                background: {sb_hover};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: none;
            }}
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """)
        for cat in (self.cat_albums, self.cat_people, self.cat_folders, self.cat_hidden_folders, self.cat_projects):
            if cat is not None:
                cat.setBackground(0, self.style.alist_catcolor)
                cat.setForeground(0, QColor(txt_col))
                for i in range(cat.childCount()):
                    child = cat.child(i)
                    if child is None:
                        continue
                    ud = child.data(0, Qt.ItemDataRole.UserRole)
                    if isinstance(ud, dict) and ud.get("type") in ("starred", "unnamed_faces"):
                        child.setBackground(0, self.style.alist_stickycolor)
                        child.setForeground(0, QColor(txt_col))
                    else:
                        child.setForeground(0, QColor(txt_col))

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les titres des catégories de l'arborescence selon la langue active.
        EN: Updates the library tree category titles according to the active language.
        """
        self.refresh()

    def handle_drop_on_item(self, item: QTreeWidgetItem, paths: List[str]) -> bool:
        """
        FR: Traite le dépôt de photos sur un élément de l'arborescence (album, dossier ou favoris).
        EN: Handles dropping photos onto a tree item (album, folder, or starred photos).
        Ref: picasa3.exe @ CAlbumList::dragcolor, Drag & Drop
        """
        if not item or not paths:
            return False
        ud = item.data(0, Qt.ItemDataRole.UserRole)
        if not ud:
            return False
        t = ud.get("type")
        if t == "album":
            token = ud.get("token") or ud.get("key") or ""
            if token:
                self.photos_dropped_on_album.emit(token, paths)
                return True
        elif t == "folder":
            fpath = ud.get("key") or ""
            if fpath:
                self.photos_dropped_on_folder.emit(fpath, paths)
                return True
        elif t == "starred":
            self.photos_dropped_on_starred.emit(paths)
            return True
        return False

    def set_folder_view_mode(self, mode: str) -> None:
        """
        FR: Bascule entre la vue à plat ('flat', ID_VIEW_FOLDERS) et l'arborescence ('tree', ID_VIEW_ALL).
        EN: Switches between flat view ('flat', ID_VIEW_FOLDERS) and hierarchical tree view ('tree', ID_VIEW_ALL).
        """
        if mode in ("flat", "tree") and mode != self.folder_view_mode:
            self.folder_view_mode = mode
            self.refresh_folders()

    def _init_categories(self) -> None:
        """
        FR: Crée les nœuds racines de catégories (Albums, Personnes, Dossiers, Projets) dans l'arbre.
        EN: Creates the top-level category nodes (Albums, People, Folders, Projects) in the tree.
        """
        self.tree.clear()

        def _create_cat(title: str, icon_id: int) -> QTreeWidgetItem:
            """
            FR: Construit et configure un élément de catégorie racine avec son icône et sa couleur d'en-tête.
            EN: Builds and configures a root category tree item with its icon and header background color.
            """
            item = QTreeWidgetItem(self.tree)
            item.setText(0, title)
            item.setIcon(0, self.res_mgr.get_icon(icon_id))
            font = item.font(0)
            if font.pointSize() <= 0:
                font.setPointSize(8)
            font.setBold(True)
            item.setFont(0, font)
            item.setBackground(0, self.style.alist_catcolor)
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "key": title})
            item.setExpanded(True)
            return item

        self.cat_albums = _create_cat(self.res_mgr.get_stringres("CAlbumList::liststicky5", self.res_mgr.get_string(200, "Albums")), 152)
        self.cat_people = _create_cat(self.res_mgr.get_stringres("Category::people", "Personnes"), 159)
        # Ref: picasa3.exe @ 0x004A2314, 0x004A2DF2 ("Hidden Folders" / IDS_HIDDEN = "Dossiers masqués", cat=7)
        # Placé juste au-dessus de "Dossiers" dans le QTreeWidget afin qu'il soit immédiatement visible sans défiler 700+ dossiers
        hidden_title = self.res_mgr.get_stringres("IDS_HIDDEN", self.res_mgr.get_string(240, "Dossiers masqués"))
        self.cat_hidden_folders = _create_cat(hidden_title, 150)
        self.cat_hidden_folders.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "key": "Hidden Folders"})
        self.cat_hidden_folders.setHidden(True)
        self.cat_folders = _create_cat(self.res_mgr.get_stringres("CAlbumList::liststicky2", self.res_mgr.get_string(196, "Folders")), 150)
        self.cat_projects = _create_cat(self.res_mgr.get_stringres("CAlbumList::liststicky8", self.res_mgr.get_string(299, "Projects")), 161)

    def refresh(self) -> None:
        """
        FR: Rafraîchit l'intégralité de l'arborescence (catégories, dossiers, albums, personnes).
        EN: Refreshes the entire library tree (categories, folders, albums, people).
        Ref: picasa3.exe @ 0x005D41F4 (CAlbumListUI::Refresh)
        """
        self._init_categories()
        if not getattr(self, "db", None):
            return
        self.refresh_folders()
        self.refresh_albums()
        self.refresh_people()

    def populate_from_database(self, db: PicasaDatabase) -> None:
        """
        FR: Remplit l'arborescence avec les dossiers, albums et personnes.
        EN: Populates the library tree with folders, albums, and people.
        Ref: picasa3.exe @ 0x005D41F4 (CAlbumListUI::Populate)
        """
        self.db = db
        self.refresh()

    def set_show_hidden(self, show: bool) -> None:
        """
        FR: Met à jour uniquement l'état de visibilité de la collection « Dossiers masqués » (`cat=7`)
        sans reconstruire les 700+ dossiers normaux (`cat=2`), conformément à `FUN_005C9300` & `FUN_004A8B10`.
        EN: Updates only the visibility state of the "Hidden Folders" collection (`cat=7`)
        without rebuilding all normal folders (`cat=2`), matching `FUN_005C9300` & `FUN_004A8B10`.
        Ref: picasa3.exe @ 0x005C9300, 0x004A8B10, 0x004B2060
        """
        self.show_hidden = bool(show)
        self._update_hidden_folders_category()

    def _is_hidden_folders_password_locked(self) -> bool:
        """
        FR: Indique si la collection « Dossiers masqués » est actuellement protégée par mot de passe et non déverrouillée.
        EN: Returns whether the "Hidden Folders" collection is currently password-protected and locked.
        Ref: picasa3.exe @ 0x004AB650, 0x005EE522 (catdata_state[7] == 0 tant que le mot de passe n'a pas été saisi)
        """
        main_win = self.window()
        if main_win is not None and hasattr(main_win, "_get_collection_password_hash"):
            pwd_hash = main_win._get_collection_password_hash("Hidden Folders")
            if pwd_hash:
                unlocked = getattr(main_win, "_unlocked_collections", set())
                return "Hidden Folders" not in unlocked
        return False

    def _update_hidden_folders_category(self) -> None:
        """
        FR: Met à jour le nœud `cat_hidden_folders` (« Dossiers masqués », `cat=7`) en O(H) :
        - Masqué si `not self.show_hidden` ou s'il n'y a aucun dossier masqué (`0x004A8B10`, `0x004B2060`).
        - Replié (`setExpanded(False)`) sans sous-dossiers affichés tant que la collection est verrouillée par mot de passe (`0x005EE522`, `0x004AB650`).
        - Déplié avec ses dossiers masqués si pas de mot de passe ou déjà déverrouillé.
        EN: Updates the `cat_hidden_folders` node ("Hidden Folders", `cat=7`) in O(H).
        Ref: picasa3.exe @ 0x004A8B10, 0x004B2060, 0x004AB650, 0x005EE522
        """
        if self.cat_hidden_folders is None:
            return
        self._updating_hidden_cat = True
        self.tree.setUpdatesEnabled(False)
        try:
            self.cat_hidden_folders.setExpanded(False)
            self.cat_hidden_folders.takeChildren()
            if not self.show_hidden or not self._cached_hidden_folder_items:
                self.cat_hidden_folders.setHidden(True)
                return

            self.cat_hidden_folders.setHidden(False)
            is_locked = self._is_hidden_folders_password_locked()
            children_to_add: List[QTreeWidgetItem] = []
            folder_icon = self.res_mgr.get_icon(150)
            for name, count, fpath, norm_k in sorted(self._cached_hidden_folder_items, key=lambda x: x[0].lower()):
                h_item = QTreeWidgetItem()
                h_item.setText(0, f"{name} ({count})")
                h_item.setIcon(0, folder_icon)
                h_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "folder",
                    "key": fpath,
                    "name": name,
                    "is_hidden_folder": True,
                })
                children_to_add.append(h_item)
            if children_to_add:
                self.cat_hidden_folders.addChildren(children_to_add)
            # Ref: picasa3.exe @ 0x005EE522, 0x004AB650 : replié (state=0) si protégé par mot de passe non saisi
            self.cat_hidden_folders.setExpanded(not is_locked)
        finally:
            self.tree.setUpdatesEnabled(True)
            self._updating_hidden_cat = False

    def refresh_folders(self) -> None:
        """
        FR: Met à jour dynamiquement la section Dossiers (Folders) dans l'arborescence.
        Supporte la vue à plat (flat) et la vue arborescente hiérarchique (tree).
        Préserve l'expansion, la sélection et la position de la barre de défilement verticale
        (mise à jour sur place lorsque la liste des dossiers n'a pas changé de structure).
        EN: Dynamically updates the Folders section in the library tree.
        Supports both flat list mode (flat) and hierarchical folder tree mode (tree).
        Preserves expansion, selection, and vertical scrollbar position (in-place update when structure matches).
        Ref: picasa3.exe @ 0x005D41F4 (CAlbumListUI::UpdateCategory Folders)
        """
        if not self.cat_folders or not self.db:
            return

        vbar = self.tree.verticalScrollBar()
        saved_scroll = vbar.value() if vbar is not None else 0
        was_expanded = self.cat_folders.isExpanded()
        self.tree.setUpdatesEnabled(False)
        try:
            with QSignalBlocker(self.tree):
                selected_key = None
                curr = self.tree.currentItem()
                if curr:
                    ud = curr.data(0, Qt.ItemDataRole.UserRole)
                    if ud and ud.get("type") == "folder":
                        selected_key = ud.get("key")

                # Compter par parent_idx entier d'abord O(N), puis normaliser uniquement par dossier unique O(F)
                ti_folders: Dict[int, str] = {}
                idx_media_count: Dict[int, int] = {}
                for i, r in enumerate(self.db.index):
                    rt = r.type
                    if rt == 1:
                        ti_folders[i] = r.path
                    elif rt in (2, 6, 7, 13, 18, 31, 32):
                        p_idx = r.parent_idx
                        idx_media_count[p_idx] = idx_media_count.get(p_idx, 0) + 1

                folder_media_count: Dict[str, int] = {}
                norm_by_idx: Dict[int, str] = {}
                for idx, fpath in ti_folders.items():
                    if fpath:
                        k = _norm(fpath)
                        norm_by_idx[idx] = k
                        c = idx_media_count.get(idx, 0)
                        if c > 0:
                            folder_media_count[k] = folder_media_count.get(k, 0) + c

                ad_names = self.db.pmps.get("albumdata_name")
                ad_cats = self.db.pmps.get("albumdata_category")
                ad_files = self.db.pmps.get("albumdata_filename")

                folder_items: List[Tuple[str, int, str, str]] = []
                hidden_folder_items: List[Tuple[str, int, str, str]] = []
                added_norm_paths: Set[str] = set()
                hidden_norm_paths: Set[str] = set()
                db_hidden_folders = getattr(self.db, "_hidden_folders", None)
                if db_hidden_folders:
                    for hp in db_hidden_folders:
                        hidden_norm_paths.add(_norm(hp))

                if ad_names and ad_cats and ad_files:
                    names = ad_names.records
                    cats = ad_cats.records
                    files = ad_files.records
                    for i in range(len(names)):
                        fpath = files[i] if i < len(files) else ""
                        if not fpath:
                            continue
                        norm_k = _norm(fpath)
                        cat_val = cats[i] if i < len(cats) else 2
                        if cat_val == 7 or norm_k in hidden_norm_paths:
                            hidden_norm_paths.add(norm_k)
                            count = folder_media_count.get(norm_k, 0)
                            if count > 0 and norm_k not in added_norm_paths:
                                hidden_folder_items.append((names[i] or os.path.basename(fpath.rstrip("\\/")), count, fpath, norm_k))
                                added_norm_paths.add(norm_k)
                        elif cat_val == 2:  # FR: Dossier réel visible dans Picasa / EN: Real folder visible in Picasa
                            count = folder_media_count.get(norm_k, 0)
                            if count > 0 and norm_k not in added_norm_paths:
                                folder_items.append((names[i] or os.path.basename(fpath.rstrip("\\/")), count, fpath, norm_k))
                                added_norm_paths.add(norm_k)

                # FR: Dossiers trouvés dans thumbindex / EN: Folders found in thumbindex
                for idx, fpath in ti_folders.items():
                    norm_k = norm_by_idx.get(idx) or _norm(fpath)
                    if norm_k not in added_norm_paths:
                        count = folder_media_count.get(norm_k, 0)
                        if count > 0:
                            dname = os.path.basename(fpath.rstrip("\\/")) or fpath
                            if norm_k in hidden_norm_paths:
                                hidden_folder_items.append((dname, count, fpath, norm_k))
                            else:
                                folder_items.append((dname, count, fpath, norm_k))
                            added_norm_paths.add(norm_k)

                # Synchroniser self.db._hidden_folders avec l'ensemble des dossiers cat==7 détectés
                if hidden_norm_paths:
                    if not hasattr(self.db, "_hidden_folders") or not isinstance(self.db._hidden_folders, set):
                        self.db._hidden_folders = set()
                    self.db._hidden_folders.update(hidden_norm_paths)

                self._cached_hidden_folder_items = hidden_folder_items
                self._update_hidden_folders_category()

                sorted_flat = sorted(folder_items, key=lambda x: x[0].lower())
                # Mise à jour sur place O(F) en mode flat si la liste des dossiers est identique (ex. incrément de compteur pendant le scan)
                if self.folder_view_mode != "tree" and self.cat_folders.childCount() == len(sorted_flat) and len(sorted_flat) > 0:
                    same_keys = True
                    for i, (_, _, _, norm_k) in enumerate(sorted_flat):
                        ch = self.cat_folders.child(i)
                        ud = ch.data(0, Qt.ItemDataRole.UserRole) if ch else None
                        if not ud or _norm(ud.get("key", "")) != norm_k:
                            same_keys = False
                            break
                    if same_keys:
                        for i, (name, count, fpath, _) in enumerate(sorted_flat):
                            ch = self.cat_folders.child(i)
                            lbl = f"{name} ({count})"
                            if ch.text(0) != lbl:
                                ch.setText(0, lbl)
                        return

                if selected_key:
                    self.tree.setCurrentItem(None)
                # Détacher tous les enfants d'un seul bloc O(1)
                self.cat_folders.setExpanded(False)
                self.cat_folders.takeChildren()

                folder_icon = self.res_mgr.get_icon(150)
                norm_selected_key = _norm(selected_key) if selected_key else None
                item_to_reselect = None
                if self.folder_view_mode == "tree":
                    # FR: Mode arborescent (ID_VIEW_ALL) : hiérarchie parent -> sous-dossier
                    # EN: Hierarchical tree mode (ID_VIEW_ALL): parent -> subfolder hierarchy
                    nodes_by_norm: Dict[str, QTreeWidgetItem] = {}
                    sorted_by_depth = sorted(folder_items, key=lambda x: (x[3].count("/"), x[0].lower()))
                    for name, count, fpath, norm_k in sorted_by_depth:
                        parent_node = self.cat_folders
                        parent_dir = _norm(os.path.dirname(fpath.rstrip("\\/")))
                        while parent_dir and "/" in parent_dir:
                            if parent_dir in nodes_by_norm:
                                parent_node = nodes_by_norm[parent_dir]
                                break
                            next_p = _norm(os.path.dirname(parent_dir))
                            if next_p == parent_dir:
                                break
                            parent_dir = next_p
                        item = QTreeWidgetItem(parent_node)
                        item.setText(0, f"{name} ({count})")
                        item.setIcon(0, folder_icon)
                        item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "folder",
                            "key": fpath,
                            "name": name,
                        })
                        item.setExpanded(True)
                        nodes_by_norm[norm_k] = item
                        if norm_selected_key and norm_k == norm_selected_key:
                            item_to_reselect = item
                else:
                    # FR: Mode à plat (ID_VIEW_FOLDERS) — insertion groupée addChildren / EN: Flat list mode
                    flat_items: List[QTreeWidgetItem] = []
                    for name, count, fpath, norm_k in sorted_flat:
                        item = QTreeWidgetItem()
                        item.setText(0, f"{name} ({count})")
                        item.setIcon(0, folder_icon)
                        item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "folder",
                            "key": fpath,
                            "name": name,
                        })
                        flat_items.append(item)
                        if norm_selected_key and norm_k == norm_selected_key:
                            item_to_reselect = item
                    if flat_items:
                        self.cat_folders.addChildren(flat_items)

                self.cat_folders.setExpanded(was_expanded or bool(folder_items))
                if item_to_reselect:
                    item_to_reselect.setSelected(True)
                if vbar is not None and saved_scroll > 0:
                    vbar.setValue(saved_scroll)
        finally:
            self.tree.setUpdatesEnabled(True)
            if vbar is not None and saved_scroll > 0:
                vbar.setValue(saved_scroll)

    def refresh_albums(self) -> None:
        """
        FR: Met à jour dynamiquement la section Albums dans l'arborescence.
        EN: Dynamically updates the Albums section in the library tree.
        Ref: picasa3.exe @ 0x005D41F4, 0x008AAD76 (CAlbumListUI::UpdateCategory Albums)
        """
        if not self.cat_albums or not self.db:
            return

        vbar = self.tree.verticalScrollBar()
        saved_scroll = vbar.value() if vbar is not None else 0
        was_expanded = self.cat_albums.isExpanded()
        self.tree.setUpdatesEnabled(False)
        try:
            with QSignalBlocker(self.tree):
                selected_key = None
                curr = self.tree.currentItem()
                if curr:
                    ud = curr.data(0, Qt.ItemDataRole.UserRole)
                    if ud and ud.get("type") in ("album", "starred"):
                        selected_key = ud.get("key")
                        self.tree.setCurrentItem(None)

                self.cat_albums.setExpanded(False)
                self.cat_albums.takeChildren()

                # FR: Album virtuel épinglé "Photos favorites" / EN: Sticky virtual album "Starred Photos"
                # (Ref: picasa3.exe @ CThumbDB::starredphotos, 0x0088F6FC, alist_stickycolor)
                starred_paths = self.db.get_starred_photo_paths() if hasattr(self.db, "get_starred_photo_paths") else []
                starred_count = len(starred_paths)
                count_str = f" ({starred_count})" if starred_count > 0 else " (0)"
                item_starred = QTreeWidgetItem()
                item_starred.setText(0, f"Photos favorites{count_str}")
                item_starred.setIcon(0, self.res_mgr.get_star_icon(18))
                item_starred.setBackground(0, self.style.alist_stickycolor)
                item_starred.setForeground(0, self.style.alist_textcolor)
                item_starred.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "starred",
                    "key": "special_starred",
                    "name": "Photos favorites",
                    "token": "starred",
                    "photo_paths": starred_paths,
                })
                album_children: List[QTreeWidgetItem] = [item_starred]
                item_to_reselect = None
                if selected_key == "special_starred":
                    item_to_reselect = item_starred

                albums = self.db.get_all_albums()
                album_icon = self.res_mgr.get_icon(152)

                for alb in sorted(albums, key=lambda a: a["name"].lower()):
                    count = len(alb.get("photo_paths", []))
                    count_str = f" ({count})" if count > 0 else ""
                    item = QTreeWidgetItem()
                    item.setText(0, f"{alb['name']}{count_str}")
                    item.setIcon(0, album_icon)
                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "album",
                        "key": alb["token"],
                        "name": alb["name"],
                        "token": alb["token"],
                        "photo_paths": alb.get("photo_paths", []),
                    })
                    album_children.append(item)
                    if selected_key and (alb["token"] == selected_key or alb["name"] == selected_key):
                        item_to_reselect = item

                self.cat_albums.addChildren(album_children)
                self.cat_albums.setExpanded(was_expanded or True)
                if item_to_reselect:
                    item_to_reselect.setSelected(True)
                if vbar is not None and saved_scroll > 0:
                    vbar.setValue(saved_scroll)
        finally:
            self.tree.setUpdatesEnabled(True)
            if vbar is not None and saved_scroll > 0:
                vbar.setValue(saved_scroll)

    def refresh_people(self) -> None:
        """
        FR: Met à jour dynamiquement la section Personnes (People) dans l'arborescence.
        Préserve les nœuds existants sur place lorsque l'ordre des personnes n'a pas changé
        afin d'éviter tout saut de défilement ou perte de clic pendant la détection de visages.
        EN: Dynamically updates the People section in the library tree.
        Preserves existing nodes in-place when the person list order is unchanged
        to avoid any scroll jump or lost click during background face detection.
        Ref: picasa3.exe @ 0x008AAD76, 0x005D41F4 (CAlbumListUI::UpdateCategory People)
        """
        if not self.cat_people or not self.db or not getattr(self.db, "face_manager", None):
            return

        vbar = self.tree.verticalScrollBar()
        saved_scroll = vbar.value() if vbar is not None else 0
        was_expanded = self.cat_people.isExpanded()
        self.tree.setUpdatesEnabled(False)
        try:
            with QSignalBlocker(self.tree):
                selected_key = None
                curr = self.tree.currentItem()
                if curr:
                    ud = curr.data(0, Qt.ItemDataRole.UserRole)
                    if ud and ud.get("type") in ("person", "unnamed_faces"):
                        selected_key = ud.get("key")

                people = list(self.db.face_manager.get_people())
                known_ids = {p.contact_id.lower() for p in people}

                # FR: Inclure également les personnes enregistrées dans contacts.xml même sans photo
                # EN: Also include people registered in contacts.xml even if they have 0 photos
                if getattr(self.db, "contacts", None) and hasattr(self.db.contacts, "contacts"):
                    from picasa_py.faces.face_manager import PersonCluster
                    c_data = self.db.contacts.contacts
                    c_list = c_data.values() if isinstance(c_data, dict) else c_data
                    for c in c_list:
                        cid = (getattr(c, "id", None) or "").strip().lower()
                        if cid and cid not in known_ids:
                            cluster = PersonCluster(contact_id=cid, name=getattr(c, "name", "") or cid)
                            self.db.face_manager.people[cid] = cluster
                            people.append(cluster)
                            known_ids.add(cid)

                # FR: Trier : d'abord ceux qui ont des photos (par photo_count décroissant), puis par ordre alphabétique
                # EN: Sort: first by descending photo_count, then alphabetically by name
                people_sorted = sorted(people, key=lambda p: (-p.photo_count, p.name.lower()))

                unnamed_list = self.db.face_manager.unnamed_faces if hasattr(self.db.face_manager, "unnamed_faces") else []
                unnamed_count = len(unnamed_list)
                unnamed_title = self.res_mgr.get_stringres("CThumbDB::unknownfacealbum", "Sans nom")

                expected_keys: List[str] = []
                if unnamed_count > 0:
                    expected_keys.append("unnamed")
                expected_keys.extend(p.contact_id.lower() for p in people_sorted)

                # Mise à jour sur place O(P) si la liste des nœuds enfants est identique
                if self.cat_people.childCount() == len(expected_keys) and len(expected_keys) > 0:
                    same_people_keys = True
                    for i, exp_k in enumerate(expected_keys):
                        ch = self.cat_people.child(i)
                        ud = ch.data(0, Qt.ItemDataRole.UserRole) if ch else None
                        if not ud or str(ud.get("key", "")).lower() != exp_k:
                            same_people_keys = False
                            break
                    if same_people_keys:
                        offset = 0
                        if unnamed_count > 0:
                            ch_u = self.cat_people.child(0)
                            u_lbl = f"{unnamed_title} ({unnamed_count})"
                            if ch_u.text(0) != u_lbl:
                                ch_u.setText(0, u_lbl)
                            offset = 1
                        for j, person in enumerate(people_sorted):
                            ch_p = self.cat_people.child(offset + j)
                            p_lbl = f"{person.name} ({person.photo_count})"
                            if ch_p.text(0) != p_lbl:
                                ch_p.setText(0, p_lbl)
                        return

                self._avatar_timer.stop()
                self._pending_tree_avatars.clear()
                if selected_key:
                    self.tree.setCurrentItem(None)

                # FR: Détacher tous les enfants en O(1) / EN: Detach all children in O(1)
                self.cat_people.setExpanded(False)
                self.cat_people.takeChildren()

                item_to_reselect = None
                people_children: List[QTreeWidgetItem] = []

                # FR: Section spéciale épinglée "Sans nom" / EN: Sticky special section "Unnamed"
                # (Ref: CThumbDB::unknownfacealbum, 0x008AAD76, alist_stickycolor)
                if unnamed_count > 0:
                    item_unnamed = QTreeWidgetItem()
                    item_unnamed.setText(0, f"{unnamed_title} ({unnamed_count})")
                    item_unnamed.setIcon(0, self.res_mgr.get_icon(159))
                    item_unnamed.setBackground(0, self.style.alist_stickycolor)
                    item_unnamed.setForeground(0, self.style.alist_textcolor)
                    font_u = item_unnamed.font(0)
                    if font_u.pointSize() <= 0:
                        font_u.setPointSize(8)
                    font_u.setItalic(True)
                    item_unnamed.setFont(0, font_u)
                    item_unnamed.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "unnamed_faces",
                        "key": "unnamed",
                        "name": unnamed_title,
                    })
                    people_children.append(item_unnamed)
                    if selected_key == "unnamed":
                        item_to_reselect = item_unnamed

                fm = self.db.face_manager
                avatar_cache = getattr(fm, "_avatar_cache", {})
                default_person_icon = self.res_mgr.get_icon(159)
                sync_avatar_decodes = 0

                for person in people_sorted:
                    item = QTreeWidgetItem()
                    item.setText(0, f"{person.name} ({person.photo_count})")
                    cid_low = person.contact_id.lower()
                    cached_av = avatar_cache.get((cid_low, 48, True)) or getattr(person, "_avatar_pixmap", None)
                    if cached_av is not None and not isinstance(cached_av, property) and not cached_av.isNull():
                        item.setIcon(0, QIcon(cached_av))
                    elif sync_avatar_decodes < 6:
                        sync_avatar_decodes += 1
                        avatar = fm.get_person_avatar(
                            person.contact_id, size=48, allow_disk_fallback=False
                        )
                        if avatar and not avatar.isNull():
                            item.setIcon(0, QIcon(avatar))
                        else:
                            item.setIcon(0, default_person_icon)
                    else:
                        item.setIcon(0, default_person_icon)
                        if person.photo_count > 0:
                            self._pending_tree_avatars.append((item, person.contact_id))

                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "person",
                        "key": person.contact_id,
                        "name": person.name,
                    })
                    people_children.append(item)
                    if selected_key and cid_low == selected_key.lower():
                        item_to_reselect = item

                if people_children:
                    self.cat_people.addChildren(people_children)
                self.cat_people.setExpanded(was_expanded or bool(people_children))
                if item_to_reselect:
                    item_to_reselect.setSelected(True)
                if vbar is not None and saved_scroll > 0:
                    vbar.setValue(saved_scroll)
        finally:
            self.tree.setUpdatesEnabled(True)
            if vbar is not None and saved_scroll > 0:
                vbar.setValue(saved_scroll)

        if self._pending_tree_avatars:
            self._avatar_timer.start()

    def _load_next_tree_avatars(self) -> None:
        """
        FR: Charge progressivement par petits lots les avatars restants des personnes dans l'arborescence.
        EN: Progressively loads remaining people avatars in small batches in the library tree.
        """
        if not self._pending_tree_avatars or not self.db or not getattr(self.db, "face_manager", None):
            self._pending_tree_avatars.clear()
            self._avatar_timer.stop()
            return
        batch = self._pending_tree_avatars[:6]
        del self._pending_tree_avatars[:6]
        fm = self.db.face_manager
        for item, cid in batch:
            try:
                if item.treeWidget() is None:
                    continue
                av = fm.get_person_avatar(cid, size=48, allow_disk_fallback=False)
                if av and not av.isNull():
                    item.setIcon(0, QIcon(av))
            except Exception:
                pass
        if not self._pending_tree_avatars:
            self._avatar_timer.stop()

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """
        FR: Gère le dépliage d'une catégorie dans l'arborescence (`CAlbumState::passprompt` @ `0x004AB650`).
        Si la catégorie « Dossiers masqués » (`cat=7`) est protégée par mot de passe et non déverrouillée,
        demande le mot de passe avant d'autoriser son ouverture ; en cas de refus ou d'erreur, la replie.
        EN: Handles category expansion in the library tree (`CAlbumState::passprompt` @ `0x004AB650`).
        Ref: picasa3.exe @ 0x004AB9A0 - 0x004ABB69, 0x004AB650 - 0x004AB8F1
        """
        if self._updating_hidden_cat or item is not self.cat_hidden_folders:
            return
        if self._is_hidden_folders_password_locked():
            main_win = self.window()
            if main_win is not None and hasattr(main_win, "_verify_collection_password_prompt"):
                if not main_win._verify_collection_password_prompt("Hidden Folders"):
                    self._updating_hidden_cat = True
                    try:
                        item.setExpanded(False)
                    finally:
                        self._updating_hidden_cat = False
                    return
                if hasattr(main_win, "thumb_view"):
                    main_win.thumb_view._apply_current_filters(reset_scroll=False)

    def _on_item_collapsed(self, item: QTreeWidgetItem) -> None:
        """
        FR: Gère le repliage d'une catégorie dans l'arborescence (`0x00453AF0`).
        Replier « Dossiers masqués » reverrouille la collection si elle est protégée par mot de passe (`catdata_state[7] = 0`).
        EN: Handles category collapse in the library tree (`0x00453AF0`).
        Collapsing "Hidden Folders" re-locks the collection if password-protected (`catdata_state[7] = 0`).
        Ref: picasa3.exe @ 0x00453AF0, 0x004AB9A0
        """
        if self._updating_hidden_cat or item is not self.cat_hidden_folders:
            return
        main_win = self.window()
        if main_win is not None and hasattr(main_win, "_get_collection_password_hash"):
            if main_win._get_collection_password_hash("Hidden Folders"):
                unlocked = getattr(main_win, "_unlocked_collections", None)
                if isinstance(unlocked, set):
                    unlocked.discard("Hidden Folders")
                if hasattr(main_win, "thumb_view"):
                    main_win.thumb_view._apply_current_filters(reset_scroll=False)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        FR: Émet le signal folder_selected correspondant à l'élément ou la catégorie cliquée.
        Pour la catégorie « Dossiers masqués » (`cat=7`), bascule son état déplié/replié avec vérification
        du mot de passe conformément à `0x004AB9A0 -> 0x004AB650`.
        EN: Emits the folder_selected signal matching the clicked item or category.
        Ref: picasa3.exe @ 0x004AB9A0 - 0x004ABB69, 0x004AB650
        """
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") in ("folder", "album", "person", "unnamed_faces", "starred"):
            self.folder_selected.emit(data["key"], data["type"], data["name"])
        elif data and data.get("type") == "category":
            if item is self.cat_hidden_folders:
                if not item.isExpanded():
                    item.setExpanded(True)
                    if item.isExpanded() and item.childCount() > 0:
                        first_child = item.child(0)
                        c_data = first_child.data(0, Qt.ItemDataRole.UserRole)
                        if c_data and c_data.get("key"):
                            self.folder_selected.emit(c_data["key"], "folder", c_data.get("name", ""))
                else:
                    item.setExpanded(False)
                return
            # FR: Cliquer sur la catégorie "Folders" ou "Albums" réinitialise la vue à toutes les photos
            # EN: Clicking on the "Folders" or "Albums" category resets the view to all photos
            self.folder_selected.emit("", "all", "Toutes les photos")

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        FR: Gestion du clic droit dans l'arborescence (Ref: 0x005D41F4, "lb_rightclick").
        Si l'utilisateur fait un clic droit sur une catégorie repliée et protégée par mot de passe,
        demande d'abord le mot de passe (`0x005D4407 -> 0x005D4494 -> 0x005EC440`).
        EN: Right-click context menu handler in the library tree (Ref: 0x005D41F4, "lb_rightclick").
        Ref: picasa3.exe @ 0x005D41F4, 0x005D4407 - 0x005D44AF, 0x005EC440
        """
        item = self.tree.itemAt(event.pos())
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        t = data.get("type")
        main_win = self.window()

        if t == "folder":
            fpath = data.get("key", "")
            if fpath:
                PicasaContextMenuBuilder.show_folder_context_menu(
                    self, event.globalPos(), fpath, db=self.db, main_win=main_win
                )
        elif t == "album":
            aname = data.get("name", "")
            if aname:
                PicasaContextMenuBuilder.show_album_context_menu(
                    self, event.globalPos(), aname, db=self.db, main_win=main_win
                )
        elif t == "person":
            cid = data.get("key", "")
            pname = data.get("name", "")
            PicasaContextMenuBuilder.show_person_context_menu(
                self, event.globalPos(), cid, pname, db=self.db, main_win=main_win
            )
        elif t == "category":
            ckey = data.get("key", "")
            if item is self.cat_hidden_folders and not item.isExpanded() and self._is_hidden_folders_password_locked():
                if main_win is not None and hasattr(main_win, "_verify_collection_password_prompt"):
                    if not main_win._verify_collection_password_prompt("Hidden Folders"):
                        return
                    item.setExpanded(True)
            PicasaContextMenuBuilder.show_collection_context_menu(
                self, event.globalPos(), ckey, db=self.db, main_win=main_win
            )


