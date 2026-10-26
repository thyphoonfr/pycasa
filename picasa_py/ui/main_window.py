"""
FR: Fenêtre principale de l'application PyCasa (reproduction fidèle de ytWindow).
EN: Main Application Window for PyCasa (faithful reproduction of ytWindow).

Ref: picasa3.exe @ 0x00983940 (ytWindow WndProc)
Ref: picasa3.exe @ 0x0070494B (Magic signature 0x47506332 'GPc2')
Ref: picasa3.exe @ OneUp, editoneup
Ref: AGENTS.md §4 bis (Disposition et fonctionnement identiques)
"""

from __future__ import annotations
import os
import sys
import time
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStackedWidget, QStatusBar, QMessageBox, QFileDialog, QDialog, QProgressDialog,
    QApplication, QInputDialog, QMenu
)
from PySide6.QtCore import Qt, QSize, QPoint, Signal, QTimer, QThread, QObject, QEvent
from PySide6.QtGui import QIcon, QImage, QImageReader, QPixmap, QPalette

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.menu import PicasaMenuBuilder
from picasa_py.ui.top_bar import PicasaTopBar
from picasa_py.ui.library_tree import PicasaLibraryTree
from picasa_py.ui.thumbnail_view import PicasaThumbnailView
from picasa_py.ui.photo_tray import PicasaPhotoTray
from picasa_py.ui.right_drawer import PicasaRightDrawer
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.ui.folder_manager import PicasaFolderManagerDialog
from picasa_py.ui.export_dialog import PicasaExportDialog, PicasaExportWorker
from picasa_py.ui.slideshow import PicasaSlideshowWindow
from picasa_py.ui.rename_dialog import PicasaRenameDialog
from picasa_py.ui.offset_time_dialog import PicasaAdjustTimeDialog
from picasa_py.ui.album_dialog import PicasaAlbumDialog
from picasa_py.ui.image_properties_dialog import PicasaImagePropertiesDialog
from picasa_py.ui.contact_manager_dialog import PicasaContactManagerDialog
from picasa_py.ui.email_dialog import PicasaEmailDialog
from picasa_py.ui.move_database_dialog import PicasaMoveDatabaseDialog, PicasaDatabaseSelectorDialog
from picasa_py.ui.poster_dialog import PicasaPosterDialog
from picasa_py.ui.web_export_dialog import PicasaWebExportDialog
from picasa_py.ui.import_dialog import PicasaImportDialog
from picasa_py.ui.notifier_popup import PicasaNotifierPopup
from picasa_py.ui.context_menu import PicasaContextMenuBuilder, recycle_or_delete_file
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.scanner.watcher import PicasaFolderWatcher
from picasa_py.scanner.scanner import BackgroundScanWorker
from picasa_py.faces.face_manager import BackgroundFaceDetectionWorker
from picasa_py.db.database import PicasaDatabase
from picasa_py.version import (
    get_about_dialog_text,
    get_about_dialog_title,
    get_window_title,
)




class _GuiActivityEventFilter(QObject):
    """
    FR: Moniteur global d'activité utilisateur (souris, molette, clavier) suspendant
    immédiatement les workers d'arrière-plan pendant toute interaction de l'utilisateur.
    EN: Global user activity monitor (mouse, wheel, keyboard) that immediately suspends
    background workers during any user interaction.
    Ref: picasa3.exe @ 0x005E4AC0, 0x005E4F6E (CSlowTaskManager User Activity Throttle)
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """
        FR: Intercepte les événements d'entrée utilisateur et notifie `BackgroundScanWorker`.
        EN: Intercepts user input events and notifies `BackgroundScanWorker`.
        """
        etype = event.type()
        if etype in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.Wheel,
            QEvent.Type.KeyPress,
        ):
            BackgroundScanWorker.notify_gui_activity()
        elif etype == QEvent.Type.MouseMove:
            try:
                if getattr(event, "buttons", lambda: Qt.MouseButton.NoButton)() != Qt.MouseButton.NoButton:
                    BackgroundScanWorker.notify_gui_activity()
            except Exception:
                pass
        return False


# Ref: picasa3.exe @ 0x00983940 (ytWindow)
class PicasaMainWindow(QMainWindow):
    """
    FR: Fenêtre principale de l'application reproduisant ytWindow de Picasa 3.
    Gère la bascule entre la vue Bibliothèque (grille) et la vue Édition (One-Up).
    EN: Main application window reproducing Picasa 3's ytWindow.
    Manages switching between the Library view (grid) and the Editor view (One-Up).
    """
    WINDOW_MAGIC = 0x47506332  # 'GPc2'
    albums_changed = Signal()
    folders_changed = Signal()

    def __init__(self, db_path: Optional[str] = None, auto_scan: bool = True, parent: Optional[QWidget] = None):
        """
        FR: Initialise la fenêtre principale, ses panneaux, ses menus et la base de données.
        EN: Initializes the main window, its panels, menus, and database.
        """
        super().__init__(parent)
        QImageReader.setAllocationLimit(0)
        self.auto_scan = auto_scan
        try:
            from picasa_py.db.preferences import PicasaPreferences
            saved_tid = PicasaPreferences.get_theme_id()
            self.style = PicasaStyle.load_theme(saved_tid)
        except Exception:
            self.style = PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()
        self.watcher: Optional[PicasaFolderWatcher] = None
        self.scan_worker: Optional[BackgroundScanWorker] = None
        self.face_worker: Optional[BackgroundFaceDetectionWorker] = None
        self._pending_scan_folders: Set[str] = set()
        self._pending_scan_notify: bool = False
        self._active_scan_notify: bool = True
        self._gui_activity_filter = _GuiActivityEventFilter(self)
        app_inst = QApplication.instance()
        if app_inst is not None:
            app_inst.installEventFilter(self._gui_activity_filter)
        else:
            self.installEventFilter(self._gui_activity_filter)

        # Fenêtre surgissante de notification Picasa (Ref: picasa3.exe @ 0x0040C339 [ebp+0x30f0], CNotifierPopup @ 0x00656FE0)
        self.notifier_popup = PicasaNotifierPopup(self.style, self)
        self.notifier_popup.notification_clicked.connect(self._on_notifier_popup_clicked)

        self.setWindowTitle(get_window_title())
        self.setWindowIcon(self.res_mgr.get_icon(105))
        self.resize(1200, 780)

        # Central container
        central_widget = QWidget(self)
        central_widget.setObjectName("MainWindowCentral")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Barre d'outils supérieure / Top toolbar
        from PySide6.QtWidgets import QSizePolicy
        self.top_bar = PicasaTopBar(self.style, self)
        self.top_bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.top_bar)

        # 2. Sélecteur de mode (Bibliothèque / One-Up View) / Mode switcher (Library / One-Up View)
        self.stack = QStackedWidget(self)
        self.stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        # Page 0: Bibliothèque (Splitter 3 volets: Arborescence | Grille | Tiroir)
        # Page 0: Library (3-pane Splitter: Tree | Grid | Drawer)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setHandleWidth(4)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #D6D6D6;
            }
        """)

        # Volet gauche (Arborescence) / Left pane (Library tree)
        self.library_tree = PicasaLibraryTree(self.style, self)
        self.library_tree.setMinimumWidth(180)
        self.splitter.addWidget(self.library_tree)

        # Volet central (Grille de vignettes) / Center pane (Thumbnail grid)
        self.thumb_view = PicasaThumbnailView(self.style, self)
        self.splitter.addWidget(self.thumb_view)

        # Volet droit (Tiroir de métadonnées) / Right pane (Metadata drawer)
        self.right_drawer = PicasaRightDrawer(self.style, self)
        self.right_drawer.hide()
        self.splitter.addWidget(self.right_drawer)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, True)

        self.splitter.setSizes([220, 980, 0])
        self.stack.addWidget(self.splitter)

        # Page 1: Vue d'édition One-Up (Ref: picasa3.exe @ OneUp) / One-Up Editor view
        self.one_up_view = PicasaOneUpView(self.style, self)
        self.one_up_view.set_use_external_bottom_bar(True)
        self.stack.addWidget(self.one_up_view)

        main_layout.addWidget(self.stack, 1)

        # 3. Bac à photos inférieur (Photo Tray) / Bottom Photo Tray
        self.photo_tray = PicasaPhotoTray(self.style, self)
        self.photo_tray.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.photo_tray)

        # 4. Barre d'état / Status bar
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("background-color: #E6E6E6; color: #555555; font-size: 11px;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")

        # 5. Construction des menus / Menu bar construction
        self.show_hidden_pictures: bool = False  # Ref: picasa3.exe @ 0x00564ED4 ([ebp + 0x3188] Preferences/ShowHidden)
        self._unlocked_collections: Set[str] = set()  # Ref: picasa3.exe @ 0x004AB650, 0x005EC440
        self.menu_builder = PicasaMenuBuilder(self)
        self.menu_builder.build_menu_bar()

        # 6. Connexion des signaux / Signal connections
        self._connect_signals()
        if hasattr(self.res_mgr, "on_language_changed_callbacks"):
            if self._on_language_changed not in self.res_mgr.on_language_changed_callbacks:
                self.res_mgr.on_language_changed_callbacks.append(self._on_language_changed)

        # 7. Application systématique du thème initial et chargement de la base de données
        # 7. Systematic application of initial theme and database loading
        self.apply_theme(self.style.theme_id, persist=False)
        self.db: Optional[PicasaDatabase] = None
        self._effects_clipboard: Optional[Dict[str, str]] = None
        self._init_database(db_path)

    def apply_theme(self, theme_id: str, persist: bool = True) -> None:
        """
        FR: Charge et applique à chaud un thème de couleurs (`ui/resources/themes/<theme_id>.ini`)
        à la fenêtre principale, à sa palette Qt, à la barre de menus et à tous les panneaux.
        EN: Hot-loads and applies a color theme (`ui/resources/themes/<theme_id>.ini`)
        to the main window, its Qt palette, the menu bar, and all child panels.
        """
        new_style = PicasaStyle.load_theme(theme_id)
        self.style = new_style

        win_bg = new_style.window_bgcolor.name()
        grid_bg = new_style.grid_bgcolor.name()
        txt_col = new_style.topbar_text_color.name()
        menu_bg = new_style.topbar_grad_start.name()
        menu_bg_end = new_style.topbar_grad_end.name()
        menu_border = new_style.topbar_border_color.name()
        accent = new_style.accent_color.name()
        accent_end = getattr(new_style, "accent_grad_end", new_style.accent_color).name()
        split_col = new_style.splitter_color.name()
        sb_bg = new_style.statusbar_bgcolor.name()
        sb_bg_end = getattr(new_style, "statusbar_bgcolor_end", new_style.statusbar_bgcolor).name()
        sb_fg = new_style.statusbar_text_color.name()
        accent_css = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent_end})"
            if accent != accent_end
            else accent
        )
        menubar_css = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {menu_bg}, stop:1 {menu_bg_end})"
            if accent != accent_end
            else menu_bg
        )
        sb_css = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {sb_bg}, stop:1 {sb_bg_end})"
            if sb_bg != sb_bg_end
            else sb_bg
        )

        # Mettre à jour la QPalette de la fenêtre pour éviter tout fond sombre hérité de l'OS (Windows Dark Mode)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, new_style.window_bgcolor)
        pal.setColor(QPalette.ColorRole.WindowText, new_style.topbar_text_color)
        pal.setColor(QPalette.ColorRole.Base, new_style.alist_bgcolor)
        pal.setColor(QPalette.ColorRole.AlternateBase, new_style.grid_bgcolor)
        pal.setColor(QPalette.ColorRole.Text, new_style.alist_textcolor)
        pal.setColor(QPalette.ColorRole.Button, new_style.topbar_btn_bg_start)
        pal.setColor(QPalette.ColorRole.ButtonText, new_style.topbar_text_color)
        pal.setColor(QPalette.ColorRole.Highlight, new_style.accent_color)
        pal.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        self.setPalette(pal)
        if self.centralWidget():
            self.centralWidget().setPalette(pal)
            self.centralWidget().setAutoFillBackground(True)

        self.setStyleSheet(f"""
            QMainWindow, QWidget#MainWindowCentral {{
                background-color: {win_bg};
                color: {txt_col};
            }}
            QStackedWidget {{
                background-color: {grid_bg};
            }}
            QMenuBar {{
                background: {menubar_css};
                color: {txt_col};
                border-bottom: 1px solid {menu_border};
            }}
            QMenuBar::item {{
                background: transparent;
                color: {txt_col};
                padding: 4px 8px;
            }}
            QMenuBar::item:selected {{
                background: {accent_css};
                color: #FFFFFF;
            }}
            QMenu {{
                background-color: {win_bg};
                color: {txt_col};
                border: 1px solid {menu_border};
                padding: 2px;
            }}
            QMenu::item {{
                padding: 5px 24px 5px 20px;
                color: {txt_col};
            }}
            QMenu::item:selected {{
                background: {accent_css};
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {menu_border};
                margin: 3px 6px;
            }}
        """)

        if hasattr(self, "top_bar") and hasattr(self.top_bar, "apply_style"):
            self.top_bar.apply_style(new_style)
        if hasattr(self, "library_tree") and hasattr(self.library_tree, "apply_style"):
            self.library_tree.apply_style(new_style)
        if hasattr(self, "thumb_view") and hasattr(self.thumb_view, "apply_style"):
            self.thumb_view.apply_style(new_style)
        if hasattr(self, "right_drawer") and hasattr(self.right_drawer, "apply_style"):
            self.right_drawer.apply_style(new_style)
        if hasattr(self, "photo_tray") and hasattr(self.photo_tray, "apply_style"):
            self.photo_tray.apply_style(new_style)
        if hasattr(self, "one_up_view") and hasattr(self.one_up_view, "apply_style"):
            self.one_up_view.apply_style(new_style)
        if hasattr(self, "notifier_popup") and hasattr(self.notifier_popup, "apply_style"):
            self.notifier_popup.apply_style(new_style)

        self.splitter.setStyleSheet(
            f"QSplitter {{ background-color: {win_bg}; }} "
            f"QSplitter::handle {{ background-color: {split_col}; }}"
        )

        self.status_bar.setStyleSheet(f"background: {sb_css}; color: {sb_fg}; font-size: 11px;")

        if hasattr(self, "menu_builder") and getattr(self.menu_builder, "theme_actions", None):
            act = self.menu_builder.theme_actions.get(new_style.theme_id)
            if act:
                act.setChecked(True)

        if persist:
            try:
                from picasa_py.db.preferences import PicasaPreferences
                PicasaPreferences.set_theme_id(new_style.theme_id)
            except Exception:
                pass

        self.status_bar.showMessage(f"Thème de couleurs appliqué : {new_style.theme_name}")
        self.update()


    def _connect_signals(self) -> None:
        """
        FR: Connecte l'ensemble des signaux entre l'arborescence, la grille, le bac, le tiroir et l'éditeur.
        EN: Connects all signals between the library tree, thumbnail grid, photo tray, drawer, and editor.
        """
        # Sélection de dossier dans l'arborescence et glisser-déposer (Drag & Drop)
        self.library_tree.folder_selected.connect(self._on_folder_selected)
        self.library_tree.photos_dropped_on_album.connect(self._on_photos_dropped_on_album)
        self.library_tree.photos_dropped_on_folder.connect(self._on_photos_dropped_on_folder)
        self.library_tree.photos_dropped_on_starred.connect(self._on_photos_dropped_on_starred)

        # Sélection d'éléments dans la grille
        self.thumb_view.selection_changed.connect(self._on_selection_changed)

        # Double-clic pour ouvrir la photo en grand (One-Up View) et actions d'en-tête de section
        self.thumb_view.item_double_clicked.connect(self._open_one_up_view)
        self.thumb_view.slideshow_requested.connect(self._on_album_slideshow)
        self.thumb_view.collage_section_requested.connect(self._on_section_collage_requested)
        self.thumb_view.movie_section_requested.connect(self._on_section_movie_requested)
        self.thumb_view.save_section_requested.connect(self._on_section_save_requested)
        self.thumb_view.active_folder_changed.connect(self._on_active_folder_scrolled)

        # Retour à la bibliothèque & Diaporama
        self.one_up_view.back_to_library_requested.connect(self._back_to_library)
        self.one_up_view.slideshow_requested.connect(self.action_slideshow)
        self.one_up_view.photo_edited.connect(self._on_photo_edited)
        self.one_up_view.current_photo_changed.connect(self._on_one_up_photo_changed)

        # Curseur de zoom du plateau (Bibliothèque : thumbui/scale_group ; 1-Up : editpanel/zoombuttcontainer & zoomslider)
        self.photo_tray.zoom_changed.connect(self.thumb_view.set_thumb_size)
        self.photo_tray.toggle_left_drawer_requested.connect(self.one_up_view._toggle_left_edit_drawer)
        self.photo_tray.oneup_fit_requested.connect(self.one_up_view.canvas.reset_zoom_to_fit)
        self.photo_tray.oneup_zoom_1to1_requested.connect(lambda: self.one_up_view.canvas.set_zoom(1.0))
        self.photo_tray.oneup_zoom_changed.connect(self.one_up_view.canvas.set_zoom_from_slider)
        self.photo_tray.oneup_faces_toggled.connect(self.one_up_view._on_toggle_face_tags)
        self.one_up_view.canvas.zoom_changed.connect(
            lambda scale: self.photo_tray.set_oneup_zoom_from_canvas(scale, self.one_up_view.canvas._get_fit_scale())
        )

        # Recherche, mode d'affichage des dossiers et filtres rapides
        self.top_bar.folder_view_mode_changed.connect(self._on_top_bar_folder_view_mode_changed)
        self.top_bar.folder_sort_requested.connect(self.action_sort_folder_by)
        self.top_bar.new_album_requested.connect(self.action_new_album)
        self.top_bar.search_query_changed.connect(self._on_search_query)
        self.top_bar.filter_starred_toggled.connect(lambda v: self.thumb_view.apply_quick_filters(filter_starred=v))
        self.top_bar.filter_faces_toggled.connect(lambda v: self.thumb_view.apply_quick_filters(filter_faces=v))
        self.top_bar.filter_videos_toggled.connect(lambda v: self.thumb_view.apply_quick_filters(filter_videos=v))
        self.top_bar.filter_geo_toggled.connect(lambda v: self.thumb_view.apply_quick_filters(filter_geo=v))

        # Actions du plateau (Ref: thumbui/startoggle, rotate_ccw, rotate_cw, il_CollageButton, il_MakeMovieButton)
        self.photo_tray.action_hold.connect(self._on_tray_hold)
        self.photo_tray.action_clear.connect(self.action_clear_selection)
        self.photo_tray.action_star.connect(self.action_toggle_star)
        self.photo_tray.action_rotate_left.connect(lambda: self.action_rotate_counterclockwise())
        self.photo_tray.action_rotate_right.connect(lambda: self.action_rotate_clockwise())
        self.photo_tray.action_print.connect(self.action_print)
        self.photo_tray.action_export.connect(self.action_export)
        self.photo_tray.action_collage.connect(self.action_collage)
        self.photo_tray.action_movie.connect(lambda: self.action_movie(face_mode=False))
        self.photo_tray.action_email.connect(self.action_email)
        self.photo_tray.upload_requested.connect(self.action_web_export)
        self.photo_tray.action_add_to_album.connect(self._on_tray_add_to_album)
        self.photo_tray.action_thumbnail_clicked.connect(self._on_tray_thumbnail_clicked)
        self.photo_tray.action_thumbnail_double_clicked.connect(self._on_tray_thumbnail_double_clicked)
        self.photo_tray.tray_context_action_requested.connect(self._on_tray_context_action_requested)

        # Synchronisation de l'étoile / favori entre vues
        self.thumb_view.star_toggled.connect(self._on_thumb_star_toggled)
        self.one_up_view.star_toggled.connect(self._on_one_up_star_toggled)

        # Importation & Diaporama depuis la barre supérieure
        self.top_bar.import_requested.connect(self.action_import)
        self.top_bar.slideshow_requested.connect(self.action_slideshow)

        # Volet latéral droit dans la bibliothèque (Ref: thumbui/*_toggle)
        self.photo_tray.panel_toggled.connect(self._on_tray_panel_toggled)
        self.right_drawer.drawer_closed.connect(self._on_drawer_state_changed)
        self.right_drawer.panel_changed.connect(self._on_drawer_state_changed)
        self.right_drawer.people_changed.connect(self._on_people_changed)
        self.right_drawer.person_filter_requested.connect(self._on_person_filter_requested)
        self.right_drawer.cluster_filter_requested.connect(self._on_cluster_filter_requested)
        if hasattr(self.one_up_view, "right_drawer"):
            self.one_up_view.right_drawer.person_filter_requested.connect(self._on_person_filter_requested)
            self.one_up_view.right_drawer.cluster_filter_requested.connect(self._on_cluster_filter_requested)
        self.one_up_view.people_changed.connect(self._on_people_changed)
        self.albums_changed.connect(self._on_albums_changed)
        self.folders_changed.connect(self._on_folders_changed)

    def _init_database(self, db_path: Optional[str] = None) -> None:
        """
        FR: Ouvre la base de données Picasa initiale (spécifiée, personnalisée ou par défaut).
        EN: Opens the initial Picasa database (specified, custom repository, or default).
        """
        try:
            target_path = db_path
            if not target_path:
                from picasa_py.db.preferences import PicasaPreferences
                custom_repo = PicasaPreferences.get_repository_path()
                if custom_repo and os.path.exists(custom_repo):
                    target_path = custom_repo

            if target_path:
                db = PicasaDatabase.open(target_path)
            else:
                db = PicasaDatabase.open_default()

            self.switch_database(db, persist_preference=False)
        except Exception as e:
            self.status_bar.showMessage(f"Mode sans base active : {e}")

    def switch_database(self, new_db_or_path: Any, persist_preference: bool = False) -> bool:
        """
        FR: Bascule à chaud vers une autre base de données Picasa (nouvellement créée ou existante)
        sans redémarrer l'application : arrête les tâches d'arrière-plan et le watcher,
        déconnecte les callbacks de l'ancienne base, charge la nouvelle base et rafraîchit toutes les vues.
        EN: Hot-switches to another Picasa database (newly created or existing)
        without restarting the application: stops background tasks and watcher,
        disconnects old database callbacks, loads the new database, and refreshes all views.
        """
        try:
            self.stop_background_tasks()

            if self.watcher is not None:
                try:
                    if hasattr(self.watcher, "stop"):
                        self.watcher.stop()
                    else:
                        self.watcher.debounce_timer.stop()
                        self.watcher.pending_changed_paths.clear()
                        self.watcher.set_watched_directories([])
                    try:
                        self.watcher.scan_requested.disconnect(self._on_watcher_scan_requested)
                    except Exception:
                        pass
                    self.watcher.deleteLater()
                except Exception:
                    pass
                self.watcher = None

            if hasattr(self, "notifier_popup") and self.notifier_popup:
                try:
                    self.notifier_popup.clear_notifications()
                    self.notifier_popup.hide()
                except Exception:
                    pass

            if hasattr(self, "_unlocked_collections") and isinstance(self._unlocked_collections, set):
                self._unlocked_collections.clear()

            if self.db is not None and getattr(self.db, "_face_manager", None) is not None:
                try:
                    if self._on_people_changed in self.db.face_manager.on_people_changed_callbacks:
                        self.db.face_manager.on_people_changed_callbacks.remove(self._on_people_changed)
                except Exception:
                    pass

            if self.stack.currentWidget() == self.one_up_view:
                self._back_to_library()

            if hasattr(self, "one_up_view") and self.one_up_view is not None:
                try:
                    if hasattr(self.one_up_view, "_full_res_preview_timer"):
                        self.one_up_view._full_res_preview_timer.stop()
                    if hasattr(self.one_up_view, "_ flush_pending_thumb_db_sync"):
                        self.one_up_view._flush_pending_thumb_db_sync()
                    elif hasattr(self.one_up_view, "_flush_pending_thumb_db_sync"):
                        self.one_up_view._flush_pending_thumb_db_sync()
                    if hasattr(self.one_up_view, "_thumb_db_sync_timer"):
                        self.one_up_view._thumb_db_sync_timer.stop()
                except Exception:
                    pass

            # FR: Annuler tout timer d'écriture différée sur l'ancienne base avant de basculer
            # EN: Cancel any deferred save timer on the old database before switching
            if self.db is not None and self.db is not new_db_or_path:
                try:
                    t_timer = getattr(self.db, "_thumb_save_timer", None)
                    if t_timer is not None:
                        t_timer.cancel()
                        self.db._thumb_save_timer = None
                except Exception:
                    pass

            if isinstance(new_db_or_path, PicasaDatabase):
                self.db = new_db_or_path
            else:
                self.db = PicasaDatabase.open(str(new_db_or_path))

            if hasattr(self, "one_up_view") and self.one_up_view is not None:
                self.one_up_view.db = self.db
                self.one_up_view.current_index = -1
                self.one_up_view.available_indices = []

            if persist_preference and self.db:
                from picasa_py.db.preferences import PicasaPreferences
                PicasaPreferences.set_repository_path(str(self.db.db3_dir))

            self.photo_tray.set_database(self.db)
            self.photo_tray.held_items = []
            self.photo_tray.set_selected_items([])
            self.thumb_view.set_database(self.db)
            self.library_tree.populate_from_database(self.db)
            if hasattr(self, "right_drawer") and self.right_drawer is not None:
                self.right_drawer.set_current_photo(self.db, -1, "")

            if self.db and getattr(self.db, "face_manager", None):
                if self._on_people_changed not in self.db.face_manager.on_people_changed_callbacks:
                    self.db.face_manager.on_people_changed_callbacks.append(self._on_people_changed)

            count = len(self.db.index)
            self.status_bar.showMessage(f"Base de données chargée ({self.db.db3_dir}) : {count} photos indexées")

            self.watcher = PicasaFolderWatcher(self.db, self)
            self.watcher.scan_requested.connect(self._on_watcher_scan_requested)

            if self.auto_scan:
                QTimer.singleShot(500, self._launch_deferred_startup_scan)
            return True

        except Exception as e:
            self.status_bar.showMessage(f"Erreur lors du chargement de la base de données : {e}")
            return False

    def _launch_deferred_startup_scan(self) -> None:
        """
        FR: Lance le balayage en arrière-plan différé après l'affichage initial de la fenêtre principale
            afin de ne pas bloquer les premiers clics de l'utilisateur au démarrage.
            Reproduit le lancement asynchrone de `CDirectoryScanner` (`0x00797AF0`) après l'initialisation
            de `ytWindow` (`0x00983940`).
        EN: Launches the deferred background scan after the initial main window display
            so the user's first clicks at startup are never blocked.
            Reproduces the asynchronous launch of `CDirectoryScanner` (`0x00797AF0`) after
            `ytWindow` (`0x00983940`) initialization.

        Ref: picasa3.exe @ 0x00797AF0 (CDirectoryScanner), 0x00983940 (ytWindow), AGENTS.md §4 ter.1
        """
        if getattr(self, "_is_closing", False) or not self.auto_scan or self.db is None:
            return
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return
        if self.face_worker is not None and self.face_worker.isRunning():
            return
        indexed_dirs_lower: Set[str] = set()
        if self.db.thumbindex:
            for r in self.db.thumbindex.records:
                if r.type == 1 and r.is_active and r.path:
                    indexed_dirs_lower.add(r.path.replace("/", "\\").rstrip("\\").lower())
        watched: List[str] = []
        for p, st in self.db.get_watched_folders().items():
            clean_p = p.rstrip("\\/")
            if st == "1":
                watched.append(clean_p)
            elif st == "2":
                # Ref: picasa3.exe @ 0x004F6380 — un dossier "Scan Once" (+) n'est balayé au démarrage
                # que s'il ne possède encore aucun dossier indexé dans thumbindex.db.
                norm_p = clean_p.replace("/", "\\").lower()
                prefix_p = norm_p + "\\"
                if not any(d == norm_p or d.startswith(prefix_p) for d in indexed_dirs_lower):
                    watched.append(clean_p)
        if watched:
            self._start_background_scan(watched)
        elif len(self.db.index) > 0:
            self._start_background_face_detection()

    def _open_one_up_view(self, item_idx: int) -> None:
        """
        FR: Bascule en mode visualiseur/retouche plein écran pour la photo sélectionnée.
        EN: Switches to full-pane viewer/editor mode (One-Up View) for the selected photo.
        """
        BackgroundScanWorker.notify_gui_activity()
        if self.db is None or item_idx >= len(self.thumb_view.items):
            return

        lib_drawer_was_open = (
            self.right_drawer.isVisible()
            or (not getattr(self.right_drawer, "_explicitly_hidden", True) and self.right_drawer.is_expanded)
        )
        lib_panel_name = self.right_drawer.current_panel_name or "people"
        lib_expanded_width = getattr(self.right_drawer, "_is_expanded", False)

        item = self.thumb_view.items[item_idx]
        f_indices = self.thumb_view.filtered_indices if self.thumb_view.filtered_indices is not None else range(len(self.thumb_view.items))
        available_indices = [self.thumb_view.items[i].index for i in f_indices if i < len(self.thumb_view.items)]

        # FR: Conserver le bac de sélection (`thumbui/basecontrolset` / `thumbui/scratch`) visible en mode Édition 1-Up
        #     (Ref: picasa3.exe @ 0x0057BB80..0x0057C228 CThumbUI::SetEditModeVisibility)
        # EN: Keep the selection tray (`thumbui/basecontrolset` / `thumbui/scratch`) visible in One-Up Edit mode
        #     (Ref: picasa3.exe @ 0x0057BB80..0x0057C228 CThumbUI::SetEditModeVisibility)
        if not self.photo_tray.get_effective_items():
            if self.db is not None and hasattr(self.photo_tray, "set_database"):
                self.photo_tray.set_database(self.db)
            self.photo_tray.set_selected_items([item])
        self.photo_tray.set_focused_path(item.path, select_only_focused=True)

        # FR: Étape 1 (Ref: picasa3.exe @ 0x00568E4A) : basculer immédiatement vers la vue 1-Up et afficher
        #     l'aperçu déjà en mémoire (previews/bigthumbs CBlockFile ou vignette de la grille) avant le décodage HD.
        # EN: Step 1 (Ref: picasa3.exe @ 0x00568E4A): switch to the One-Up view immediately and show the
        #     in-memory preview (previews/bigthumbs CBlockFile or grid thumbnail) before the HD decode.
        try:
            preview_pix: Optional[QPixmap] = None
            if item.index >= 0 and not item.has_edits:
                for sz in ("preview", "large"):
                    raw_prev = self.db.get_thumbnail(item.index, size=sz)
                    if raw_prev:
                        qimg_prev = QImage.fromData(raw_prev)
                        if not qimg_prev.isNull():
                            preview_pix = QPixmap.fromImage(qimg_prev)
                            break
            if preview_pix is None:
                preview_pix = self.thumb_view._pixmap_cache.get(item_idx)
            self.top_bar.hide()
            self.photo_tray.show()
            self.stack.setCurrentIndex(1)
            if preview_pix is not None and not preview_pix.isNull() and hasattr(self.one_up_view, "canvas"):
                self.one_up_view.canvas.set_pixmap_direct(preview_pix)
                if self.isVisible():
                    self.one_up_view.repaint()
        except Exception:
            pass

        # FR: Étape 2 : décodage 1600px + filtres .picasa.ini (l'état final reste identique)
        # EN: Step 2: 1600px decode + .picasa.ini filters (final state unchanged)
        self.one_up_view.open_photo(self.db, item.index, available_indices, direct_path=item.path)

        if lib_drawer_was_open and hasattr(self.one_up_view, "right_drawer"):
            self.one_up_view.right_drawer._is_expanded = lib_expanded_width
            self.one_up_view.right_drawer.show_panel(lib_panel_name)
            self.one_up_view._update_drawer_buttons_state()

        self.top_bar.hide()
        self.photo_tray.show()
        self.photo_tray.set_focused_path(item.path, select_only_focused=True)
        self._sync_one_up_info_bar()
        self.stack.setCurrentIndex(1)
        self.one_up_view.setFocus()
        self.status_bar.showMessage(f"Éditeur Picasa : {item.filename}")

    def _sync_one_up_info_bar(self) -> None:
        """
        FR: Synchronise la visibilité des boutons de la barre inférieure (`thumbui/basecontrolset`)
        et le texte d'en-tête (`thumbui/infotext` @ `0x00566E5A..0x00567285`) avec le média
        actuellement ouvert dans `self.one_up_view`.
        EN: Synchronizes the bottom bar button visibility (`thumbui/basecontrolset`) and
        header info text (`thumbui/infotext` @ `0x00566E5A..0x00567285`) with the media item
        currently open in `self.one_up_view`.

        Ref: picasa3.exe @ 0x0057BB80..0x0057C3A3, 0x00566E5A..0x00567285, 0x005678E0..0x005679F8
        """
        if not hasattr(self, "photo_tray") or self.photo_tray is None:
            return
        if self.db is not None:
            self.photo_tray.set_database(self.db)
        is_video = bool(
            hasattr(self.one_up_view, "center_stack")
            and hasattr(self.one_up_view, "video_player")
            and self.one_up_view.center_stack.currentWidget() == self.one_up_view.video_player
        )
        self.photo_tray.set_edit_mode(True, is_video=is_video)
        if hasattr(self.one_up_view, "edit_panel") and hasattr(self.photo_tray, "btn_toggle_left_drawer"):
            self.photo_tray.btn_toggle_left_drawer.setText(
                "◀" if not self.one_up_view.edit_panel.isHidden() else "▶"
            )
        if hasattr(self.one_up_view, "canvas") and hasattr(self.photo_tray, "set_oneup_zoom_from_canvas"):
            self.photo_tray.set_oneup_zoom_from_canvas(
                self.one_up_view.canvas.get_current_scale(),
                self.one_up_view.canvas._get_fit_scale(),
            )

        photo_path = self.one_up_view.current_photo_path or ""
        avail = list(getattr(self.one_up_view, "available_indices", []) or [])
        curr_idx = getattr(self.one_up_view, "current_index", -1)
        pos_1based = 0
        total_count = len(avail)
        if curr_idx >= 0 and curr_idx in avail:
            pos_1based = avail.index(curr_idx) + 1
        elif total_count > 0:
            pos_1based = 1
        self.photo_tray.update_one_up_info(
            photo_path=photo_path,
            pos_1based=pos_1based,
            total_in_folder=total_count,
        )

    def _back_to_library(self) -> None:
        """
        FR: Revient à la grille de la photothèque en invalidant le cache de vignette de la photo éditée
        tout en préservant la sélection multiple active dans le bac et la grille (`thumbui/scratch`).
        EN: Returns to the library grid while invalidating the edited photo's thumbnail cache
        and preserving any active multi-selection in the tray and grid (`thumbui/scratch`).
        """
        BackgroundScanWorker.notify_gui_activity()
        oneup_drawer_open = False
        oneup_panel_name = "people"
        oneup_expanded_width = False
        if hasattr(self.one_up_view, "right_drawer"):
            rd = self.one_up_view.right_drawer
            oneup_drawer_open = (
                rd.isVisible()
                or (not getattr(rd, "_explicitly_hidden", True) and rd.is_expanded)
            )
            oneup_panel_name = rd.current_panel_name or "people"
            oneup_expanded_width = getattr(rd, "_is_expanded", False)

        self.stack.setCurrentIndex(0)
        self.top_bar.show()
        self.photo_tray.show()
        self.photo_tray.setEnabled(True)
        self.photo_tray.set_edit_mode(False)
        if hasattr(self.one_up_view, "video_player"):
            self.one_up_view.video_player.stop()
        if self.one_up_view.current_photo_path:
            self.thumb_view.invalidate_item(self.one_up_view.current_photo_path)

        if oneup_drawer_open:
            self.right_drawer._is_expanded = oneup_expanded_width
            self.right_drawer.show_panel(oneup_panel_name)
        elif not getattr(self.right_drawer, "_explicitly_hidden", True):
            self.right_drawer.hide_drawer()

        curr_db_idx = self.one_up_view.current_index
        if curr_db_idx >= 0:
            found = [i for i, it in enumerate(self.thumb_view.items) if it.index == curr_db_idx]
            if found:
                foc_idx = found[0]
                if len(self.thumb_view.selected_indices) > 1 or len(self.photo_tray.get_effective_items()) > 1:
                    self.thumb_view.focus_index = foc_idx
                    self.thumb_view.update()
                    self.photo_tray.set_focused_path(self.thumb_view.items[foc_idx].path, select_only_focused=True)
                else:
                    self.thumb_view.selected_indices = {foc_idx}
                    self.thumb_view.focus_index = foc_idx
                    self.thumb_view.update()
                    self._on_selection_changed([foc_idx])
        self._on_drawer_state_changed()
        self.thumb_view.setFocus()
        self.library_tree.refresh_people()
        self.status_bar.showMessage("Bibliothèque")

    def _on_people_changed(self) -> None:
        """
        FR: Appelé dès qu'une personne ou un visage est ajouté, renommé, réassigné ou supprimé.
        Préserve la sélection et tout champ de saisie de nom actif dans le volet Personnes
        lorsque la mise à jour provient du thread de détection en arrière-plan (`BackgroundFaceDetectionWorker`).
        EN: Called whenever a person or face is added, renamed, reassigned, or deleted.
        Preserves selection and any active name input box in the People panel
        when the update originates from the background detection worker (`BackgroundFaceDetectionWorker`).
        Ref: picasa3.exe @ 0x008AAD76 (NOTIFY_PEOPLE_CHANGED, CAlbumListUI::UpdateCategory People)
        Ref: picasa3.exe @ 0x00789C00 - 0x00789D50 (faceclusterpanel::UpdateClusters)
        """
        sender = self.sender()
        is_bg_face_worker = sender is not None and sender is getattr(self, "face_worker", None)
        user_editing_name = (
            hasattr(self, "right_drawer")
            and self.right_drawer is not None
            and hasattr(self.right_drawer, "is_user_editing_name")
            and self.right_drawer.is_user_editing_name()
        )

        if self.library_tree:
            self.library_tree.refresh_people()
        if (
            self.stack.currentWidget() == self.one_up_view
            and self.db is not None
            and getattr(self.db, "face_manager", None) is not None
            and self.one_up_view.current_index >= 0
        ):
            faces = self.db.face_manager.get_faces_for_photo(
                self.one_up_view.current_index,
                photo_path=self.one_up_view.current_photo_path,
            )
            self.one_up_view.canvas.set_face_rects(faces)
            if hasattr(self.one_up_view, "right_drawer"):
                one_up_editing = (
                    hasattr(self.one_up_view.right_drawer, "is_user_editing_name")
                    and self.one_up_view.right_drawer.is_user_editing_name()
                )
                if not (is_bg_face_worker and one_up_editing):
                    self.one_up_view.right_drawer._dirty_panels.add("people")
                    if not getattr(self.one_up_view.right_drawer, "_explicitly_hidden", True):
                        self.one_up_view.right_drawer._sync_active_panel()
        if (
            self.thumb_view
            and self.thumb_view.current_folder_filter
            and self.thumb_view.current_folder_filter.startswith("person:")
        ):
            if is_bg_face_worker and (user_editing_name or bool(self.thumb_view.selected_indices)):
                return
            cid = self.thumb_view.current_folder_filter[7:]
            person = self.db.face_manager.get_person(cid) if self.db and self.db.face_manager else None
            if person:
                only_sug = False
                if self.thumb_view.visible_sections and self.thumb_view.visible_sections[0].only_suggestions:
                    only_sug = True
                saved_scroll = self.thumb_view.scroll_y
                self.thumb_view.filter_by_person(cid, person.name, person.photo_indices, only_suggestions=only_sug)
                if saved_scroll > 0:
                    max_scroll = max(0, self.thumb_view.total_content_height - self.thumb_view.height())
                    clamped_scroll = min(saved_scroll, max_scroll)
                    self.thumb_view.scroll_y = clamped_scroll
                    self.thumb_view.scrollbar.set_value(clamped_scroll)
                    self.thumb_view.update()
        elif (
            self.thumb_view
            and self.thumb_view.current_folder_filter == "unnamed_faces"
        ):
            if self.db and getattr(self.db, "face_manager", None):
                self.thumb_view.sync_unnamed_faces_incremental(self.db.face_manager.unnamed_faces)

    def _on_person_filter_requested(self, contact_id: str, name: str) -> None:
        """
        FR: Filtre la vue vignettes sur l'album de la personne demandée depuis le volet latéral.
        EN: Filters the thumbnail view to the person's album requested from the side drawer.
        """
        if self.stack.currentWidget() == self.one_up_view:
            self._back_to_library()
        person = self.db.face_manager.get_person(contact_id) if self.db and self.db.face_manager else None
        indices = person.photo_indices if person else []
        self.thumb_view.filter_by_person(contact_id, name, indices)

    def _on_albums_changed(self) -> None:
        """
        FR: Déclenché lors de la création, modification ou suppression d'un album.
        EN: Triggered when an album is created, modified, or deleted.
        Ref: picasa3.exe @ 0x005D41F4, 0x008AAD76 (NOTIFY_ALBUM_CHANGED)
        """
        if self.library_tree:
            self.library_tree.refresh_albums()
        if (
            self.thumb_view
            and self.thumb_view.current_folder_filter
            and self.thumb_view.current_folder_filter.startswith("album:")
        ):
            alb_token = self.thumb_view.current_folder_filter[6:]
            indices = self._get_album_item_indices(alb_token, "")
            aname = self.thumb_view.visible_sections[0].name if self.thumb_view.visible_sections else alb_token
            self.thumb_view.filter_by_album(alb_token, aname, indices)

    def _on_folders_changed(self) -> None:
        """
        FR: Déclenché lors de l'ajout, renommage, suppression ou scan d'un dossier.
        EN: Triggered when a folder is added, renamed, deleted, or scanned.
        Ref: picasa3.exe @ 0x005D41F4 (NOTIFY_FOLDERS_CHANGED)
        """
        if self.library_tree:
            self.library_tree.refresh_folders()

    def notify_albums_changed(self) -> None:
        """
        FR: Émet le signal de notification de changement des albums.
        EN: Emits the albums changed notification signal.
        """
        self.albums_changed.emit()

    def notify_folders_changed(self) -> None:
        """
        FR: Émet le signal de notification de changement des dossiers.
        EN: Emits the folders changed notification signal.
        """
        self.folders_changed.emit()

    def _get_album_item_indices(self, album_token: str, album_name: str = "") -> List[int]:
        """
        FR: Retrouve les indices des photos associées à un album dans self.thumb_view.items.
        EN: Finds the indices of photos associated with an album in self.thumb_view.items.
        Ref: picasa3.exe @ 0x00732160
        """
        if not self.db:
            return []

        albums = self.db.get_all_albums()
        target_album = None
        for a in albums:
            if a["token"] == album_token or (album_name and a["name"].lower() == album_name.lower()):
                target_album = a
                break

        paths_set = set()
        if target_album:
            paths_set = {p.replace("\\", "/").lower() for p in target_album.get("photo_paths", [])}

        matching = []
        folder_ini_cache: dict = {}
        for i, item in enumerate(self.thumb_view.items):
            norm_item_p = item.path.replace("\\", "/").lower()
            if norm_item_p in paths_set:
                matching.append(i)
                continue

            fp = item.folder_path
            if fp not in folder_ini_cache:
                doc = None
                if fp:
                    ini_p = os.path.join(fp, ".picasa.ini")
                    if self.db is not None and hasattr(self.db, "get_parsed_ini"):
                        doc = self.db.get_parsed_ini(ini_p)
                        if doc is None:
                            doc = self.db.get_parsed_ini(os.path.join(fp, "Picasa.ini"))
                    elif os.path.exists(ini_p):
                        try:
                            from picasa_py.ini.parser import PicasaIniParser
                            doc = PicasaIniParser.parse_file(ini_p)
                        except Exception:
                            doc = None
                folder_ini_cache[fp] = doc
            doc = folder_ini_cache[fp]
            if doc:
                try:
                    sec = doc.get_section(item.filename)
                    if sec:
                        albs = sec.get("albums")
                        if albs:
                            toks = [t.strip() for t in albs.split(",") if t.strip()]
                            if album_token in toks or (target_album and target_album["token"] in toks):
                                matching.append(i)
                except Exception:
                    pass

        return matching

    def _on_photo_edited(self, photo_path: str) -> None:
        """
        FR: Déclenché lorsqu'une photo est éditée ou recadrée.
        EN: Triggered when a photo is edited or cropped.
        """
        if photo_path:
            if hasattr(self, "one_up_view") and hasattr(self.one_up_view, "filmstrip"):
                if self.db is not None and hasattr(self.db, "find_media_index_by_path"):
                    db_idx = self.db.find_media_index_by_path(photo_path)
                    if db_idx is not None and db_idx >= 0:
                        self.one_up_view.filmstrip.invalidate_thumbnail(db_idx)
            self.thumb_view.invalidate_item(photo_path)
            self.thumb_view.update()
            if self.stack.currentWidget() == self.one_up_view:
                self._sync_one_up_info_bar()
            else:
                self.photo_tray.update_info_text()

    def _on_folder_selected(self, key: str, target_type: str, display_name: str) -> None:
        """
        FR: Réagit à la sélection d'un dossier, d'un album ou d'une personne dans l'arborescence.
        EN: Handles selection of a folder, album, or person in the library tree.
        """
        BackgroundScanWorker.notify_gui_activity()
        # Ref: picasa3.exe @ 0x00537FB0 - 0x005380EA (ThumbUIOutput::FolderMenu vs AlbumMenu)
        if hasattr(self, "menu_builder") and self.menu_builder is not None:
            self.menu_builder.update_folder_album_menu_title(target_type == "folder")
        if target_type == "folder":
            self.thumb_view.scroll_to_folder(key)
            # FR: Indices du dossier via sa section (O(sections)) au lieu de parcourir tous les items
            # EN: Folder indices via its section (O(sections)) instead of scanning every item
            norm_key = os.path.normcase(os.path.normpath(key)) if key else key
            indices = []
            for sec in self.thumb_view.sections:
                sp = getattr(sec, "folder_path", "") or ""
                if sp == key or (sp and os.path.normcase(os.path.normpath(sp)) == norm_key):
                    indices = list(sec.item_indices)
                    break
            if not indices:
                indices = [i for i, it in enumerate(self.thumb_view.items) if it.folder_path == key]
            paths = [self.thumb_view.items[i].path for i in indices if i < len(self.thumb_view.items)]
            if self.db:
                self.right_drawer.set_album_paths(self.db, paths, scope_label="l'album")
                if not self.thumb_view.selected_indices:
                    self.right_drawer.set_current_photo(self.db, -1, "")
            self.status_bar.showMessage(f"Dossier sélectionné : {display_name}")
        elif target_type == "person":
            person = self.db.face_manager.get_person(key) if self.db and self.db.face_manager else None
            indices = person.photo_indices if person else []
            self.thumb_view.filter_by_person(key, display_name, indices)
            paths = [self.thumb_view.items[i].path for i in self.thumb_view.filtered_indices if i < len(self.thumb_view.items)]
            if self.db:
                self.right_drawer.set_album_paths(self.db, paths, scope_label="l'album")
                if not self.thumb_view.selected_indices:
                    self.right_drawer.set_current_photo(self.db, -1, "")
            self.status_bar.showMessage(f"Personne : {display_name} ({len(indices)} photos)")
        elif target_type == "album":
            indices = self._get_album_item_indices(key, display_name)
            self.thumb_view.filter_by_album(key, display_name, indices)
            paths = [self.thumb_view.items[i].path for i in indices if i < len(self.thumb_view.items)]
            if self.db:
                self.right_drawer.set_album_paths(self.db, paths, scope_label="l'album")
                if not self.thumb_view.selected_indices:
                    self.right_drawer.set_current_photo(self.db, -1, "")
            self.status_bar.showMessage(f"Album : {display_name} ({len(indices)} photos)")
        elif target_type == "starred":
            self.thumb_view.filter_by_starred()
            count = len(self.thumb_view.filtered_indices)
            paths = [self.thumb_view.items[i].path for i in self.thumb_view.filtered_indices if i < len(self.thumb_view.items)]
            if self.db:
                self.right_drawer.set_album_paths(self.db, paths, scope_label="l'album")
                if not self.thumb_view.selected_indices:
                    self.right_drawer.set_current_photo(self.db, -1, "")
            self.status_bar.showMessage(f"Photos favorites : {count} photo(s)")
        elif target_type == "unnamed_faces":
            # Ref: picasa3.exe @ 0x0074AE80 - 0x0074AF79 (unknownfaceheaderpanel) & 0x00647F79 (PeoplePanel selection state)
            if self.db and getattr(self.db, "face_manager", None):
                unnamed = self.db.face_manager.unnamed_faces
                # Réinitialiser le contexte d'album du tiroir droit AVANT filter_by_unnamed_faces
                # afin que selection_changed([]) n'invoque jamais set_multiple_photos sur 33 000+ visages
                self.right_drawer.set_album_paths(self.db, [], scope_label="l'album")
                self.thumb_view.filter_by_unnamed_faces(unnamed)
                self.status_bar.showMessage(f"Visages sans nom : {len(unnamed)} visages à identifier")
            else:
                self.status_bar.showMessage("Aucun visage sans nom détecté.")
        else:
            self.thumb_view.filter_by_folder(None)
            self.status_bar.showMessage(f"Sélection : {display_name}")

    def _on_active_folder_scrolled(self, folder_path: str) -> None:
        """
        FR: Met à jour la barre d'état lors du défilement multi-albums continu.
        EN: Updates the status bar during continuous multi-album scrolling.
        """
        if not self.thumb_view.current_folder_filter:
            folder_name = os.path.basename(folder_path.rstrip("\\/"))
            if folder_name:
                self.status_bar.showMessage(f"Dossier : {folder_name}")

    def _on_cluster_filter_requested(self, paths: List[str]) -> None:
        """
        FR: Sélectionne et fait défiler jusqu'aux photos du groupe de visages sélectionné.
        EN: Selects and scrolls to the photos of the selected face cluster.
        """
        if not paths:
            return
        if self.stack.currentWidget() == self.one_up_view:
            self._back_to_library()
        indices = [i for i, it in enumerate(self.thumb_view.items) if it.path in paths]
        if indices:
            self.thumb_view.set_selected_indices(indices)
            self.thumb_view.scroll_to_index(indices[0])
            self.status_bar.showMessage(f"Groupe de visages : {len(indices)} photo(s) sélectionnée(s)")

    def _on_selection_changed(self, indices: List[int]) -> None:
        """
        FR: Met à jour le bac à photos et le tiroir latéral droit lorsque la sélection de vignettes change.
        EN: Updates the photo tray and right drawer when the thumbnail selection changes.
        """
        count = len(indices)
        selected_items = []
        sync_decoded = 0
        for i in indices:
            if i < len(self.thumb_view.items):
                item = self.thumb_view.items[i]
                cur_pm = getattr(item, "pixmap", None)
                if cur_pm is None or (hasattr(cur_pm, "isNull") and cur_pm.isNull()):
                    cached_pm = self.thumb_view._pixmap_cache.get(i) or self.thumb_view._db_pixmap_cache.get(
                        getattr(item, "index", -1)
                    )
                    if cached_pm is not None and not cached_pm.isNull():
                        item.pixmap = cached_pm
                    elif sync_decoded < 12 and self.db is not None and getattr(item, "index", -1) >= 0:
                        sync_decoded += 1
                        try:
                            raw = self.db.get_thumbnail(item.index)
                            if raw:
                                qimg = QImage.fromData(raw)
                                if not qimg.isNull():
                                    item.pixmap = QPixmap.fromImage(qimg)
                        except Exception:
                            pass
                selected_items.append(item)

        if self.db is not None and hasattr(self.photo_tray, "set_database"):
            self.photo_tray.set_database(self.db)
        self.photo_tray.set_selected_items(selected_items)
        if not selected_items and count > 0:
            self.photo_tray.set_selected_count(count)

        if self.db is None:
            return

        self._sync_right_drawer_from_selection(indices)

        if self.right_drawer.isVisible():
            self.right_drawer._ensure_splitter_width(520 if self.right_drawer._is_expanded else 280)

    def _sync_right_drawer_from_selection(self, indices: List[int]) -> None:
        """
        FR: Synchronise le tiroir latéral droit (`PicasaRightDrawer`) selon les éléments actuellement sélectionnés :
        - En vue "Visages sans nom" (`unnamed_faces` / `faceclusterpanel` @ `0x0064C4C4 - 0x0064CD8D`),
          affiche uniquement les visages ou grappes sélectionnés (`explicit_clusters`), sans extraire les autres
          personnes figurant sur la même photo parente et sans jamais dupliquer la photo.
          Si 0 élément est sélectionné (`0x00647F79`), affiche l'invite vide ("Sélectionner des photos...").
        - Dans les autres vues, résout les index de base de données (`item.index`) et déduplique par photo parente.
        EN: Synchronizes the right side drawer (`PicasaRightDrawer`) based on the currently selected items.
        Ref: picasa3.exe @ 0x0064C4C4 - 0x0064CD8D, 0x00647F79, 0x0078A6C0 (faceclusterpanel::GetSelectedFaces)
        """
        if self.db is None:
            return
        count = len(indices)
        is_unnamed_view = getattr(self.thumb_view, "current_folder_filter", None) == "unnamed_faces"

        if count == 0:
            # Ref: picasa3.exe @ 0x00647F79 (PeoplePanel: 0 photo sélectionnée -> état vide "Sélectionner des photos...")
            self.right_drawer.set_current_photo(self.db, -1, "")
            return

        if is_unnamed_view:
            explicit_clusters: List[List[Tuple[Optional[int], str, Any]]] = []
            selected_db_indices: List[int] = []
            selected_paths: List[str] = []
            for i in indices:
                if 0 <= i < len(self.thumb_view.items):
                    it = self.thumb_view.items[i]
                    c_faces = getattr(it, "cluster_faces", None)
                    if c_faces:
                        explicit_clusters.append(list(c_faces))
                        for db_idx, ppath, _ in c_faces:
                            if ppath:
                                selected_db_indices.append(db_idx if db_idx is not None else -1)
                                selected_paths.append(ppath)
                    elif getattr(it, "face_rect", None) is not None and it.path:
                        explicit_clusters.append([(it.index if it.index >= 0 else None, it.path, it.face_rect)])
                        selected_db_indices.append(it.index)
                        selected_paths.append(it.path)
            if explicit_clusters:
                self.right_drawer.set_multiple_photos(
                    self.db,
                    selected_db_indices,
                    selected_paths,
                    explicit_clusters=explicit_clusters,
                )
                return

        if count == 1:
            idx = indices[0]
            if 0 <= idx < len(self.thumb_view.items):
                item = self.thumb_view.items[idx]
                c_faces = getattr(item, "cluster_faces", None)
                if c_faces and len(c_faces) > 1:
                    # Ref: picasa3.exe @ 0x0078A6C0 (faceclusterpanel::GetSelectedFaces étend la grappe au tiroir PeoplePanel)
                    c_db_indices = [db_idx if db_idx is not None else -1 for db_idx, _, _ in c_faces]
                    c_paths = [ppath for _, ppath, _ in c_faces if ppath]
                    self.right_drawer.set_multiple_photos(
                        self.db,
                        c_db_indices,
                        c_paths,
                        explicit_clusters=[list(c_faces)],
                    )
                else:
                    self.right_drawer.set_current_photo(self.db, item.index, item.path)
        elif count > 1:
            selected_db_indices = []
            selected_paths = []
            for i in indices:
                if 0 <= i < len(self.thumb_view.items):
                    it = self.thumb_view.items[i]
                    c_faces = getattr(it, "cluster_faces", None)
                    if c_faces and len(c_faces) > 1:
                        for db_idx, ppath, _ in c_faces:
                            if ppath:
                                selected_db_indices.append(db_idx if db_idx is not None else -1)
                                selected_paths.append(ppath)
                    elif it.path:
                        selected_db_indices.append(it.index)
                        selected_paths.append(it.path)
            self.right_drawer.set_multiple_photos(self.db, selected_db_indices, selected_paths)

    def _on_tray_add_to_album(self) -> None:
        """
        FR: Ouvre le menu d'ajout des photos du bac à un album virtuel.
        EN: Opens the menu to add photo tray items to a virtual album.
        Ref: picasa3.exe @ ID_LABELS, ID_FILE_NEWLABEL
        """
        tray_items = self.photo_tray.get_effective_items()
        paths = [it.path for it in tray_items if getattr(it, "path", None)]
        if not paths:
            paths = self._get_active_photo_paths()
        if not paths:
            return

        menu = QMenu(self)
        m_bg = "#2D3139" if self.style.is_dark else self.style.window_bgcolor.name()
        m_txt = "#FFFFFF" if self.style.is_dark else self.style.alayout_titleColor.name()
        m_brd = "#4B5260" if self.style.is_dark else self.style.splitter_color.name()
        m_acc = self.style.accent_color.name()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {m_bg};
                color: {m_txt};
                border: 1px solid {m_brd};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 20px 5px 24px;
                font-size: 11px;
            }}
            QMenu::item:selected {{
                background-color: {m_acc};
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {m_brd};
                margin: 4px 8px;
            }}
        """)

        act_new = menu.addAction("➕ Nouvel album...")
        act_new.triggered.connect(lambda: self.action_new_album_with_photos(paths))

        if self.db:
            albums = self.db.get_all_albums()
            if albums:
                menu.addSeparator()
                for alb in albums:
                    tok = alb.get("token", "")
                    name = alb.get("name", "Sans titre")
                    act = menu.addAction(f"📁 {name}")
                    act.triggered.connect(lambda _, t=tok: self.action_add_photos_to_album(paths, t))

        btn = self.photo_tray.btn_add_to_album
        menu.exec(btn.mapToGlobal(QPoint(0, -menu.sizeHint().height())))

    def _on_tray_hold(self) -> None:
        """
        FR: Conserve les éléments sélectionnés dans le bac à photos (Ref: thumbui/hold).
        EN: Holds the selected items in the photo tray (Ref: thumbui/hold).
        """
        held = len(getattr(self.photo_tray, "held_items", []))
        self.status_bar.showMessage(f"{held} photo(s) conservée(s) dans le bac à photos.")

    def _on_tray_thumbnail_clicked(self, item: Any) -> None:
        """
        FR: Gère le clic gauche simple sur une miniature du bac à photos (`thumbui/scratch`) :
        - Ne supprime JAMAIS les autres miniatures du bac ni la sélection multiple de la grille
          (`CThumbUI::OnSelectionChanged` @ `0x00570C62 -> je 0x00570D58`, `PruneUnheldItems` ignoré).
        - En mode Bibliothèque : focalise et fait défiler jusqu'à cette photo dans la grille et met à jour
          le tiroir droit (`SetCurrentItem` @ `0x0056B6F0`).
        - En mode Édition 1-Up (`0x00570DC9 -> 0x005683A0` `RefreshOneUpView`) : affiche immédiatement
          la photo cliquée dans l'éditeur tout en conservant toutes les miniatures dans le bac.
        EN: Handles single left-click on a thumbnail in the photo tray (`thumbui/scratch`):
        - NEVER removes other thumbnails from the tray or clears the grid's multi-selection
          (`CThumbUI::OnSelectionChanged` @ `0x00570C62 -> je 0x00570D58`, skips `PruneUnheldItems`).
        - In Library mode: focuses and scrolls to that photo in the grid and updates the right drawer.
        - In One-Up Edit mode (`0x00570DC9 -> 0x005683A0` `RefreshOneUpView`): immediately loads and
          displays the clicked photo in the editor while keeping all thumbnails in the tray.
        Ref: picasa3.exe @ 0x00719C37, 0x005709A0..0x00570E10, 0x005683A0
        """
        target_path = getattr(item, "path", "")
        if not target_path:
            return
        norm_target = os.path.normcase(os.path.normpath(target_path))
        matched_idx: Optional[int] = None
        for idx, it in enumerate(self.thumb_view.items):
            if it.path == target_path or (it.path and os.path.normcase(os.path.normpath(it.path)) == norm_target):
                matched_idx = idx
                break

        if matched_idx is not None:
            self.thumb_view.focus_index = matched_idx
            self.thumb_view.scroll_to_index(matched_idx)
            self.thumb_view.update()
            grid_item = self.thumb_view.items[matched_idx]
            self.photo_tray.update_star_state(bool(getattr(grid_item, "starred", False)))
            if self.db is not None:
                self.right_drawer.set_current_photo(self.db, grid_item.index, grid_item.path)

        if self.stack.currentWidget() == self.one_up_view:
            if not getattr(self.one_up_view, "_is_tool_locked", False) and self.db is not None:
                db_idx = getattr(item, "index", -1)
                if (db_idx is None or db_idx < 0) and matched_idx is not None:
                    db_idx = self.thumb_view.items[matched_idx].index
                avail = list(self.one_up_view.available_indices) if self.one_up_view.available_indices else []
                if db_idx is not None and db_idx >= 0 and db_idx not in avail:
                    avail.append(db_idx)
                self.one_up_view.open_photo(self.db, db_idx if db_idx is not None else -1, avail, direct_path=target_path)
                self.photo_tray.set_focused_path(target_path)

    def _on_tray_thumbnail_double_clicked(self, item: Any) -> None:
        """
        FR: Gère le double-clic gauche sur une miniature du bac (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`) :
        bascule en mode Édition 1-Up (`thumbui/fullview` @ `0x0056C0D4`) sur cette photo tout en conservant
        intégralement le contenu du bac de sélection.
        EN: Handles double left-click on a tray thumbnail (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`):
        switches to One-Up Edit mode (`thumbui/fullview` @ `0x0056C0D4`) on that photo while preserving
        all items in the selection tray.
        Ref: picasa3.exe @ 0x00719A44, 0x0056BFD0, 0x0056C0D4
        """
        target_path = getattr(item, "path", "")
        if not target_path:
            return
        norm_target = os.path.normcase(os.path.normpath(target_path))
        for idx, it in enumerate(self.thumb_view.items):
            if it.path == target_path or (it.path and os.path.normcase(os.path.normpath(it.path)) == norm_target):
                self.thumb_view.focus_index = idx
                self._open_one_up_view(idx)
                return

    def _on_one_up_photo_changed(self, db_idx: int, file_path: str) -> None:
        """
        FR: Synchronise la miniature focalisée et l'état d'étoile dans le bac de sélection lorsque
        l'utilisateur change de photo dans l'éditeur 1-Up (flèches Gauche/Droite, pellicule ou clic bac).
        EN: Synchronizes the focused thumbnail and star state in the selection tray when the user
        switches photos in the One-Up editor (Left/Right arrows, filmstrip, or tray click).
        Ref: picasa3.exe @ 0x005683A0 (RefreshOneUpView), 0x00570DC9
        """
        if file_path and hasattr(self, "photo_tray") and self.photo_tray is not None:
            self.photo_tray.set_focused_path(file_path, select_only_focused=True)
            if hasattr(self.one_up_view, "_is_starred"):
                self.photo_tray.update_star_state(bool(getattr(self.one_up_view, "_is_starred", False)))
            if self.stack.currentWidget() == self.one_up_view:
                self._sync_one_up_info_bar()

    def _on_tray_context_action_requested(self, action_id: str, paths: List[str]) -> None:
        """
        FR: Exécute les commandes du menu contextuel à 7 entrées du bac de sélection (`TrayContextMenu` @ `0x00732EE0`).
        EN: Executes commands from the 7-item selection tray context menu (`TrayContextMenu` @ `0x00732EE0`).
        Ref: picasa3.exe @ 0x00732EE0..0x007332AD
        """
        if action_id == "remove_selection":
            if paths:
                norm_rem = {os.path.normcase(os.path.normpath(p)) for p in paths if p}
                kept_indices = [
                    idx
                    for idx in sorted(self.thumb_view.selected_indices)
                    if idx < len(self.thumb_view.items)
                    and os.path.normcase(os.path.normpath(self.thumb_view.items[idx].path)) not in norm_rem
                ]
                self.thumb_view.selected_indices = set(kept_indices)
                self.thumb_view.update()
            return
        if not paths:
            return
        if action_id == "rotate_cw":
            self.action_rotate_clockwise(paths)
        elif action_id == "rotate_ccw":
            self.action_rotate_counterclockwise(paths)
        elif action_id == "locate_on_disk":
            self.action_locate_on_disk(paths[0])
        elif action_id == "properties":
            self._on_tray_panel_toggled("properties")

    def _on_tray_panel_toggled(self, panel_name: str) -> None:
        """
        FR: Bascule l'ouverture du tiroir latéral droit pour le panneau demandé depuis le bac à photos.
        EN: Toggles the right side drawer for the requested panel from the photo tray.
        """
        if self.stack.currentWidget() == self.one_up_view and hasattr(self.one_up_view, "right_drawer"):
            self.one_up_view.right_drawer.toggle_panel(panel_name)
            is_open = self.one_up_view.right_drawer.isVisible()
            curr = self.one_up_view.right_drawer.current_panel_name if is_open else ""
            self.photo_tray.update_panel_buttons(is_open, curr)
            return
        self.right_drawer.toggle_panel(panel_name)
        self._on_drawer_state_changed()

    def _on_drawer_state_changed(self) -> None:
        """
        FR: Synchronise l'état des boutons du bac à photos et le contenu du tiroir latéral droit.
        EN: Synchronizes the photo tray button states and the content of the right side drawer.
        """
        is_open = self.right_drawer.isVisible()
        curr = self.right_drawer.current_panel_name if is_open else ""
        self.photo_tray.update_panel_buttons(is_open, curr)
        if is_open:
            self.right_drawer._ensure_splitter_width(520 if self.right_drawer._is_expanded else 280)
        if is_open and self.db is not None:
            selected_indices = sorted(self.thumb_view.selected_indices)
            if selected_indices or getattr(self.thumb_view, "current_folder_filter", None) == "unnamed_faces":
                self._sync_right_drawer_from_selection(selected_indices)
            elif self.thumb_view.current_folder_filter:
                disp_indices = self.thumb_view.filtered_indices if self.thumb_view.filtered_indices is not None else []
                if disp_indices and len(disp_indices) <= 200:
                    db_indices = [
                        self.thumb_view.items[i].index
                        for i in disp_indices
                        if 0 <= i < len(self.thumb_view.items) and self.thumb_view.items[i].path
                    ]
                    paths = [
                        self.thumb_view.items[i].path
                        for i in disp_indices
                        if 0 <= i < len(self.thumb_view.items) and self.thumb_view.items[i].path
                    ]
                    self.right_drawer.set_multiple_photos(self.db, db_indices, paths)
                else:
                    self.right_drawer.set_current_photo(self.db, -1, "")
            elif self.right_drawer._album_paths:
                self.right_drawer.set_multiple_photos(self.db, [], self.right_drawer._album_paths)
            else:
                self.right_drawer.set_current_photo(self.db, -1, "")

    def _on_search_query(self, query: str) -> None:
        """
        FR: Recherche instantanée avec support multi-mots et préfixe (WordHash + live metadata).
        EN: Instant search with multi-word and prefix support (WordHash + live metadata).
        Ref: picasa3.exe @ 0x007046E0, 0x0088C3EC
        """
        query_stripped = query.strip()
        if not query_stripped:
            self.thumb_view.filter_by_folder(None)
            self.status_bar.showMessage("Photothèque")
            return

        if not self.db:
            return

        idx_to_item = {it.index: i for i, it in enumerate(self.thumb_view.items) if it.index >= 0}
        matched_doc_ids = self.db.search(query_stripped)
        seen_items = set()
        matching_indices: List[int] = []
        for doc_id in matched_doc_ids:
            item_pos = idx_to_item.get(doc_id)
            if item_pos is not None and item_pos not in seen_items:
                seen_items.add(item_pos)
                matching_indices.append(item_pos)

        if not matching_indices and len(self.thumb_view.items) <= 500:
            tokens = [t.lower() for t in query_stripped.split() if t]
            for i, item in enumerate(self.thumb_view.items):
                fn = item.filename.lower()
                fo = item.folder.lower()
                combined = f"{fn} {fo}"
                if all(t in combined for t in tokens):
                    matching_indices.append(i)

        matching_indices.sort()
        self.thumb_view.filter_by_search(query_stripped, matching_indices)
        self.status_bar.showMessage(f"Recherche : {len(matching_indices)} résultat(s) pour « {query_stripped} »")

    # --- FR: Actions des Menus & Menus Contextuels / EN: Menu & Context Menu Actions (Ref: picasa3.exe @ eMenu* & 0x00CADB44) ---

    def _get_active_photo_paths(self) -> List[str]:
        """
        FR: Retourne la liste des chemins de photos actives (vue One-Up, sélection grille ou bac à photos).
        EN: Returns the list of active photo paths (One-Up view, grid selection, or photo tray).
        """
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            return [self.one_up_view.current_photo_path]
        if self.thumb_view.selected_indices:
            return [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
        if hasattr(self, "photo_tray") and self.photo_tray.held_items:
            return [it.path for it in self.photo_tray.held_items if getattr(it, "path", None)]
        return []

    def action_view_and_edit(self, file_path: Optional[str] = None) -> None:
        """
        FR: Ouvre l'image en grand dans One-Up (ID_PICTURE_VIEW).
        EN: Opens the image in the One-Up viewer/editor (ID_PICTURE_VIEW).
        Ref: picasa3.exe @ 0x00CADB44
        """
        if not file_path:
            paths = self._get_active_photo_paths()
            if paths:
                file_path = paths[0]
        if not file_path:
            return

        for idx, item in enumerate(self.thumb_view.items):
            if item.path == file_path:
                self._open_one_up_view(idx)
                return

    def action_locate_on_disk(self, target_path: Optional[str] = None) -> None:
        """
        FR: Révèle le fichier ou le dossier dans l'Explorateur Windows (ID_FILE_LOCATEONDISK).
        EN: Reveals the file or folder in the system file explorer (ID_FILE_LOCATEONDISK).
        Ref: picasa3.exe @ 0x00C8C50A, 0x00CADF8C
        """
        if not target_path:
            paths = self._get_active_photo_paths()
            target_path = paths[0] if paths else self.thumb_view.current_folder_filter

        if not target_path:
            return

        norm = os.path.normpath(target_path)
        import sys
        if sys.platform == "win32":
            if os.path.isfile(norm):
                subprocess.Popen(f'explorer.exe /select,"{norm}"')
            elif os.path.isdir(norm):
                subprocess.Popen(f'explorer.exe "{norm}"')
        elif sys.platform == "darwin":
            if os.path.isfile(norm):
                subprocess.Popen(["open", "-R", norm])
            else:
                subprocess.Popen(["open", norm])
        else:
            folder = os.path.dirname(norm) if os.path.isfile(norm) else norm
            subprocess.Popen(["xdg-open", folder])

    def action_locate_in_picasa(self, file_path: str) -> None:
        """
        FR: Fait défiler la bibliothèque jusqu'à l'image et la sélectionne (ID_FILE_LOCATEINPICASA).
        EN: Scrolls the library to the image and selects it (ID_FILE_LOCATEINPICASA).
        Ref: picasa3.exe @ 0x00CADFC0, 0x005FA020
        """
        if self.stack.currentWidget() == self.one_up_view:
            self._back_to_library()

        norm_target = os.path.normcase(os.path.normpath(file_path)) if file_path else ""
        for idx, item in enumerate(self.thumb_view.items):
            if item.path == file_path or (item.path and os.path.normcase(os.path.normpath(item.path)) == norm_target):
                self.thumb_view.selected_indices = {idx}
                self.thumb_view.update()
                self._on_selection_changed([idx])
                item_rects = getattr(self.thumb_view, "_item_rects", None)
                if isinstance(item_rects, dict) and idx in item_rects:
                    r = item_rects[idx]
                    self.thumb_view.scrollbar.set_value(max(0, int(r.top() - 50)))
                else:
                    scrolled = False
                    for sec in getattr(self.thumb_view, "visible_sections", []):
                        if idx in sec.item_indices:
                            slot = sec.item_indices.index(idx)
                            r = self.thumb_view._get_item_rect(sec, slot)
                            target_y = max(0, int(r.top() - 50))
                            self.thumb_view.scrollbar.set_value(target_y)
                            self.thumb_view.scroll_y = target_y
                            self.thumb_view.update()
                            scrolled = True
                            break
                    if not scrolled and item.folder_path and hasattr(self.thumb_view, "scroll_to_folder"):
                        self.thumb_view.scroll_to_folder(item.folder_path)
                return

    def action_copy_path(self, target_path: Optional[str] = None) -> None:
        """
        FR: Copie le chemin absolu de l'élément dans le presse-papiers (ID_COPY_PATH).
        EN: Copies the absolute path of the item to the clipboard (ID_COPY_PATH).
        Ref: picasa3.exe @ 0x00CADDBC
        """
        if not target_path:
            paths = self._get_active_photo_paths()
            target_path = paths[0] if paths else ""
        if target_path:
            QApplication.clipboard().setText(os.path.normpath(target_path))
            self.status_bar.showMessage(f"Chemin copié : {os.path.normpath(target_path)}")

    def action_copy(self, target_path: Optional[str] = None) -> None:
        """
        FR: Copie l'image dans le presse-papiers (ID_EDIT_COPY, Ctrl+C).
        EN: Copies the image to the clipboard (ID_EDIT_COPY, Ctrl+C).
        Ref: picasa3.exe @ 0x0088C3EC
        """
        if not target_path:
            paths = self._get_active_photo_paths()
            target_path = paths[0] if paths else ""
        if target_path and os.path.exists(target_path):
            from picasa_py.ui.image_processor import PicasaImageProcessor
            pil_img = PicasaImageProcessor.load_transformed_image(target_path)
            pix = PicasaImageProcessor.pil_to_qpixmap(pil_img) if pil_img is not None else QPixmap(target_path)
            if not pix.isNull():
                QApplication.clipboard().setPixmap(pix)
                self.status_bar.showMessage(f"Photo copiée : {os.path.basename(target_path)}")

    def action_copy_all_effects(self) -> None:
        """
        FR: Copie l'ensemble des effets et retouches de la photo active dans le presse-papiers (ID_EDIT_COPYALLEFFECTS, Ctrl+Shift+C).
        EN: Copies all effects and edits of the active photo to the clipboard (ID_EDIT_COPYALLEFFECTS, Ctrl+Shift+C).
        Ref: picasa3.exe @ 0x0088C3EC (ID_EDIT_COPYALLEFFECTS), CFilterStack::CopyEffects
        """
        target_path: Optional[str] = None
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            target_path = self.one_up_view.current_photo_path
        else:
            paths = self._get_active_photo_paths()
            if paths:
                target_path = paths[0]

        if not target_path or not os.path.exists(target_path):
            self.status_bar.showMessage("Aucune photo sélectionnée pour copier les effets.")
            return

        parent_dir = os.path.dirname(target_path)
        ini_path = os.path.join(parent_dir, ".picasa.ini")
        if not os.path.exists(ini_path):
            alt = os.path.join(parent_dir, "Picasa.ini")
            if os.path.exists(alt):
                ini_path = alt

        effects: Dict[str, str] = {}
        if os.path.exists(ini_path):
            try:
                doc = PicasaIniParser.parse_file(ini_path)
                fname = os.path.basename(target_path)
                sec = doc.get_section(fname)
                if sec:
                    effect_keys = [
                        "crop", "rotate", "tilt", "text", "textactive",
                        "filters", "backlight", "autolight", "colorfix",
                        "redeye", "retouch", "star"
                    ]
                    for k in effect_keys:
                        val = sec.get(k)
                        if val is not None and val != "":
                            effects[k] = val
            except Exception:
                pass

        # Si l'utilisateur est en cours d'édition dans one_up_view, récupérer également les retouches actives non encore enregistrées
        if self.stack.currentWidget() == self.one_up_view:
            if getattr(self.one_up_view, "_active_crop_rect", None):
                r = self.one_up_view._active_crop_rect
                effects["crop"] = f"rect64({int(r[0]*65535):04x}{int(r[1]*65535):04x}{int(r[2]*65535):04x}{int(r[3]*65535):04x})"
            if getattr(self.one_up_view, "_active_tilt", 0.0) != 0.0:
                effects["tilt"] = f"tilt({self.one_up_view._active_tilt:.6f},0.000000)"
            if getattr(self.one_up_view, "_active_rotate", 0) != 0:
                effects["rotate"] = f"rotate({self.one_up_view._active_rotate})"

        if not effects:
            self.status_bar.showMessage("Aucune retouche ou effet à copier sur cette photo.")
            return

        self._effects_clipboard = effects
        self.status_bar.showMessage(f"Effets copiés ({len(effects)} paramètre(s)) dans le presse-papiers (Ctrl+Shift+C).")

    def action_paste_all_effects(self, paths: Optional[List[str]] = None) -> None:
        """
        FR: Applique l'ensemble des effets copiés aux photos sélectionnées (ID_EDIT_PASTEALLEFFECTS, Ctrl+Shift+V).
        EN: Applies all copied effects to the selected photos (ID_EDIT_PASTEALLEFFECTS, Ctrl+Shift+V).
        Ref: picasa3.exe @ 0x0088C3EC (ID_EDIT_PASTEALLEFFECTS), CFilterStack::PasteEffects
        """
        if not self._effects_clipboard:
            self.status_bar.showMessage("Aucun effet dans le presse-papiers. Utilisez Ctrl+Shift+C d'abord.")
            return

        if paths is None:
            if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
                paths = [self.one_up_view.current_photo_path]
            else:
                paths = self._get_active_photo_paths()

        if not paths:
            self.status_bar.showMessage("Sélectionnez au moins une photo pour coller les effets.")
            return

        def _apply_effects(doc: PicasaIniDocument, fname: str) -> None:
            """
            FR: Copie les clés d'effets du presse-papiers dans la section INI de la photo.
            EN: Copies the clipboard effect keys into the photo's INI section.
            """
            sec = doc.get_or_create_section(fname)
            for k, v in self._effects_clipboard.items():
                sec.set(k, v)

        for p in paths:
            self._update_photo_ini(p, _apply_effects)
            if self.db is not None and hasattr(self.db, "update_photo_thumbnails_from_disk"):
                try:
                    self.db.update_photo_thumbnails_from_disk(p, persist_to_disk=False)
                except Exception:
                    pass
            self.thumb_view.invalidate_item(p)
        if self.db is not None and hasattr(self.db, "schedule_save_thumbnails"):
            self.db.schedule_save_thumbnails(1500)

        # Si l'image ouverte dans one_up_view est modifiée, rafraîchir son affichage
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path in paths:
            self.one_up_view.open_photo(
                self.db,
                self.one_up_view.current_index,
                self.one_up_view.available_indices,
                direct_path=self.one_up_view.current_photo_path
            )

        self.thumb_view.update()
        self.status_bar.showMessage(f"Effets appliqués à {len(paths)} photo(s) (Ctrl+Shift+V).")

    def action_set_person_album_cover(self, contact_id: str, photo_path: str, face_rect: Optional[Any] = None) -> None:
        """
        FR: Définit la photo/visage sélectionné comme miniature de l'album de personne (ID_SETPEOPLEALBUMCOVER).
        EN: Sets the selected photo/face as the person album cover thumbnail (ID_SETPEOPLEALBUMCOVER).
        Ref: picasa3.exe @ PplAlbumPhoto::ID_SETPEOPLEALBUMCOVER (0x008AF20B), CThumbUI::UpdateAlbumCover
        """
        if not self.db or not getattr(self.db, "face_manager", None):
            return

        fm = self.db.face_manager
        if not face_rect:
            faces = fm.photo_to_faces.get(photo_path, [])
            for fr in faces:
                if fr.contact_id.lower() == contact_id.lower():
                    face_rect = fr
                    break
            if not face_rect and faces:
                face_rect = faces[0]

        if not face_rect:
            from picasa_py.faces.facerect import FaceRect
            face_rect = FaceRect(left=0.15, top=0.15, right=0.85, bottom=0.85, contact_id=contact_id)

        fm.set_person_album_cover(contact_id, photo_path, face_rect)
        self.thumb_view._pixmap_cache.clear()
        self.thumb_view.update()
        if hasattr(self, "library_tree"):
            self.library_tree.refresh()
        self.status_bar.showMessage("Miniature de l'album de personne mise à jour.")

    action_set_album_cover = action_set_person_album_cover

    def action_print_contact_sheet(self) -> None:
        """
        FR: Imprime directement une planche-contact des photos sélectionnées (ID_FILE_PRINTCONTACTSHEET).
        EN: Directly prints a contact sheet of the selected photos (ID_FILE_PRINTCONTACTSHEET).
        Ref: picasa3.exe @ 0x008C3380 (ID_FILE_PRINTCONTACTSHEET)
        """
        paths = self._get_active_photo_paths()
        if not paths and self.thumb_view.items:
            paths = [it.path for it in self.thumb_view.items if it.path]
        if not paths:
            QMessageBox.information(self, "Planche-contact", "Aucune photo sélectionnée.")
            return

        from picasa_py.ui.print_dialog import PicasaPrintDialog, PrintLayoutType
        dlg = PicasaPrintDialog(paths, parent=self)
        for rb, l_type in getattr(dlg, "radio_layouts", []):
            if l_type == PrintLayoutType.CONTACT_SHEET:
                rb.setChecked(True)
                break
        if hasattr(dlg, "preview_canvas"):
            dlg.preview_canvas.set_layout_mode(PrintLayoutType.CONTACT_SHEET)
        if hasattr(dlg, "_refresh_preview"):
            dlg._refresh_preview()
        dlg.exec()

    def action_open_file(self, target_path: Optional[str] = None) -> None:
        """
        FR: Ouvre le fichier avec l'application par défaut du système (ID_FILE_OPENINANEDITOR).
        EN: Opens the file with the system default application (ID_FILE_OPENINANEDITOR).
        Ref: picasa3.exe @ 0x00CADCD0
        """
        if not target_path:
            paths = self._get_active_photo_paths()
            target_path = paths[0] if paths else ""
        if target_path and os.path.exists(target_path):
            import sys
            if sys.platform == "win32":
                os.startfile(target_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target_path])
            else:
                subprocess.Popen(["xdg-open", target_path])

    def action_delete_from_disk(self, paths: Optional[List[str]] = None) -> None:
        """
        FR: Supprime les photos du disque vers la Corbeille (ID_FILE_DELETEFROMDISK, Suppr).
        EN: Deletes the photos from disk to the Recycle Bin (ID_FILE_DELETEFROMDISK, Del).
        Ref: picasa3.exe @ 0x00CADD98, 0x004A0410
        """
        if paths is None:
            paths = self._get_active_photo_paths()
        if not paths:
            QMessageBox.information(self, "Supprimer", "Aucun élément sélectionné.")
            return

        cnt = len(paths)
        msg = "Voulez-vous vraiment placer ce fichier dans la Corbeille ?" if cnt == 1 else f"Voulez-vous vraiment placer ces {cnt} fichiers dans la Corbeille ?"
        rep = QMessageBox.question(
            self,
            "Supprimer du disque",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if rep != QMessageBox.StandardButton.Yes:
            return

        deleted_paths = set()
        for p in paths:
            if recycle_or_delete_file(p):
                deleted_paths.add(p)
                if self.db is not None and hasattr(self.db, "delete_photo"):
                    try:
                        self.db.delete_photo(p)
                    except Exception:
                        pass

        if deleted_paths:
            self.thumb_view.items = [it for it in self.thumb_view.items if it.path not in deleted_paths]
            self.thumb_view.selected_indices.clear()
            self.thumb_view.filter_by_folder(self.thumb_view.current_folder_filter)
            if self.stack.currentWidget() == self.one_up_view:
                self._back_to_library()
            self.status_bar.showMessage(f"{len(deleted_paths)} fichier(s) placé(s) dans la Corbeille.")

    def action_remove_from_album(self, paths: Optional[List[str]] = None, album_token: Optional[str] = None) -> None:
        """
        FR: Retire la photo de l'album virtuel sans la supprimer du disque.
        EN: Removes the photo from the virtual album without deleting it from disk.
        Ref: picasa3.exe @ 0x00CADFF8 (AlbumPhoto::ID_FILE_DELETEFROMDISK)
        """
        if paths is None:
            paths = self._get_active_photo_paths()
        if not paths:
            return

        if not album_token and self.thumb_view.current_folder_filter and self.thumb_view.current_folder_filter.startswith("album:"):
            album_token = self.thumb_view.current_folder_filter[6:]

        for p in paths:
            def _rem_alb(doc: PicasaIniDocument, fname: str) -> None:
                """
                FR: Retire le jeton d'album de la clé albums dans la section INI de la photo.
                EN: Removes the album token from the albums key in the photo's INI section.
                """
                sec = doc.get_section(fname)
                if not sec:
                    return
                cur = sec.get("albums", "")
                if not cur:
                    return
                parts = [x.strip() for x in cur.split(",") if x.strip()]
                if album_token:
                    new_parts = [x for x in parts if x.lower() != album_token.lower()]
                else:
                    new_parts = []
                if new_parts:
                    sec.set("albums", ",".join(new_parts))
                else:
                    sec.remove("albums")
            self._update_photo_ini(p, _rem_alb)

        self.notify_albums_changed()
        self.status_bar.showMessage(f"{len(paths)} photo(s) retirée(s) de l'album.")

    def action_rotate_clockwise(self, paths: Optional[List[str]] = None) -> None:
        """
        FR: Pivote la sélection de 90° dans le sens horaire (ID_PICTURE_ROTATECLOCKWISE, Ctrl+R).
        EN: Rotates the selection 90° clockwise (ID_PICTURE_ROTATECLOCKWISE, Ctrl+R).
        Ref: picasa3.exe @ 0x00C8D79D, 0x0068B5E0
        """
        if self.stack.currentWidget() == self.one_up_view:
            if (
                not paths
                or isinstance(paths, bool)
                or (
                    len(paths) == 1
                    and self.one_up_view.current_photo_path
                    and os.path.normcase(os.path.normpath(paths[0]))
                    == os.path.normcase(os.path.normpath(self.one_up_view.current_photo_path))
                )
            ):
                self.one_up_view._on_rotate_right()
                if hasattr(self, "photo_tray") and hasattr(self.photo_tray, "thumb_strip"):
                    self.photo_tray.thumb_strip.update()
                self.status_bar.showMessage("Rotation horaire : 1 photo(s).")
                return

        if not paths or isinstance(paths, bool):
            paths = self._get_active_photo_paths()
        if not paths:
            return

        for p in paths:
            self._update_photo_ini(p, lambda doc, fname: doc.set_rotate(fname, (doc.get_rotate(fname) + 1) % 4))
            if self.db is not None and hasattr(self.db, "update_photo_thumbnails_from_disk"):
                self.db.update_photo_thumbnails_from_disk(p, persist_to_disk=False)
            self.thumb_view.invalidate_item(p)
        if self.db is not None:
            if hasattr(self.db, "schedule_save_thumbnails"):
                self.db.schedule_save_thumbnails(1500)
            elif hasattr(self.db, "save_thumbnails_only"):
                self.db.save_thumbnails_only()
        if hasattr(self, "one_up_view") and hasattr(self.one_up_view, "filmstrip"):
            self.one_up_view.filmstrip.clear_cache()

        self.thumb_view.update()
        if self.right_drawer.isVisible():
            self._on_selection_changed(list(self.thumb_view.selected_indices))
        if hasattr(self, "photo_tray") and hasattr(self.photo_tray, "thumb_strip"):
            self.photo_tray.thumb_strip.update()
        self.status_bar.showMessage(f"Rotation horaire : {len(paths)} photo(s).")

    def action_rotate_counterclockwise(self, paths: Optional[List[str]] = None) -> None:
        """
        FR: Pivote la sélection de 90° dans le sens anti-horaire (ID_PICTURE_ROTATECOUNTERCLOCKWISE, Ctrl+Shift+R).
        EN: Rotates the selection 90° counterclockwise (ID_PICTURE_ROTATECOUNTERCLOCKWISE, Ctrl+Shift+R).
        Ref: picasa3.exe @ 0x00C8D74D, 0x0068B5E0
        """
        if self.stack.currentWidget() == self.one_up_view:
            if (
                not paths
                or isinstance(paths, bool)
                or (
                    len(paths) == 1
                    and self.one_up_view.current_photo_path
                    and os.path.normcase(os.path.normpath(paths[0]))
                    == os.path.normcase(os.path.normpath(self.one_up_view.current_photo_path))
                )
            ):
                self.one_up_view._on_rotate_left()
                if hasattr(self, "photo_tray") and hasattr(self.photo_tray, "thumb_strip"):
                    self.photo_tray.thumb_strip.update()
                self.status_bar.showMessage("Rotation anti-horaire : 1 photo(s).")
                return

        if not paths or isinstance(paths, bool):
            paths = self._get_active_photo_paths()
        if not paths:
            return

        for p in paths:
            self._update_photo_ini(p, lambda doc, fname: doc.set_rotate(fname, (doc.get_rotate(fname) - 1) % 4))
            if self.db is not None and hasattr(self.db, "update_photo_thumbnails_from_disk"):
                self.db.update_photo_thumbnails_from_disk(p, persist_to_disk=False)
            self.thumb_view.invalidate_item(p)
        if self.db is not None:
            if hasattr(self.db, "schedule_save_thumbnails"):
                self.db.schedule_save_thumbnails(1500)
            elif hasattr(self.db, "save_thumbnails_only"):
                self.db.save_thumbnails_only()
        if hasattr(self, "one_up_view") and hasattr(self.one_up_view, "filmstrip"):
            self.one_up_view.filmstrip.clear_cache()

        self.thumb_view.update()
        if self.right_drawer.isVisible():
            self._on_selection_changed(list(self.thumb_view.selected_indices))
        if hasattr(self, "photo_tray") and hasattr(self.photo_tray, "thumb_strip"):
            self.photo_tray.thumb_strip.update()
        self.status_bar.showMessage(f"Rotation anti-horaire : {len(paths)} photo(s).")

    def action_undo_all_edits(self, paths: Optional[List[str]] = None) -> None:
        """
        FR: Annule toutes les retouches non-destructives Picasa (ID_PICTURE_REVERT).
        EN: Reverts all non-destructive Picasa edits (ID_PICTURE_REVERT).
        Ref: picasa3.exe @ 0x00C8D849, 0x00CADBF0
        """
        if not paths or isinstance(paths, bool):
            paths = self._get_active_photo_paths()
        if not paths:
            return

        def _reset_doc(doc: PicasaIniDocument, fname: str) -> None:
            """
            FR: Réinitialise le recadrage, la rotation, le redressement, les filtres et le texte dans la section INI.
            EN: Resets crop, rotation, tilt, filters, and text in the INI section.
            """
            doc.set_crop(fname, None)
            doc.set_rotate(fname, 0)
            doc.set_tilt(fname, None)
            doc.set_text(fname, None)
            sec = doc.get_section(fname)
            if sec is not None:
                for k in (
                    "filters",
                    "crop",
                    "rotate",
                    "tilt",
                    "text",
                    "textactive",
                    "backlight",
                    "autolight",
                    "colorfix",
                    "redeye",
                    "retouch",
                    "backuphash",
                ):
                    sec.remove(k)

        norm_targets = {os.path.normcase(os.path.normpath(p)) for p in paths}
        for p in paths:
            try:
                p_obj = Path(p)
                orig_backup = p_obj.parent / ".picasaoriginals" / p_obj.name
                if orig_backup.exists():
                    import shutil
                    shutil.copy2(str(orig_backup), str(p_obj))
                    try:
                        orig_backup.unlink()
                        if not any(orig_backup.parent.iterdir()):
                            orig_backup.parent.rmdir()
                    except Exception:
                        pass
                    if self.db is not None and self.db.thumbindex is not None:
                        try:
                            from picasa_py.scanner.scanner import file_filetimes, compute_originfast_hash
                            from PIL import Image
                            rec_idx = self.db.find_photo_index(p) if hasattr(self.db, "find_photo_index") else None
                            if rec_idx is not None and 0 <= rec_idx < len(self.db.thumbindex.records):
                                _, ft2_rest, fsize_rest = file_filetimes(p_obj)
                                rec = self.db.thumbindex.records[rec_idx]
                                rec.ft2 = ft2_rest
                                rec.size = fsize_rest
                                rec.file_size = fsize_rest
                                self.db.thumbindex.dirty = True
                                with Image.open(p_obj) as r_img:
                                    rw, rh = r_img.size
                                for col_n, col_v in (
                                    ("imagedata_width", int(rw)),
                                    ("imagedata_height", int(rh)),
                                    ("imagedata_originfast", compute_originfast_hash(p_obj)),
                                    ("imagedata_revertable", 0),
                                ):
                                    pmp_c = self.db.pmps.get(col_n)
                                    if pmp_c is not None and rec_idx < len(pmp_c.records):
                                        pmp_c.records[rec_idx] = col_v
                                        pmp_c.dirty = True
                        except Exception:
                            pass
            except Exception:
                pass
            self._update_photo_ini(p, _reset_doc)
            if self.db is not None and hasattr(self.db, "sync_photo_ini_to_db"):
                try:
                    self.db.sync_photo_ini_to_db(p)
                except Exception:
                    pass
            if self.db is not None and hasattr(self.db, "update_photo_thumbnails_from_disk"):
                self.db.update_photo_thumbnails_from_disk(p, persist_to_disk=False)
            self.thumb_view.invalidate_item(p)
        if self.db is not None:
            if hasattr(self.db, "schedule_save_thumbnails"):
                self.db.schedule_save_thumbnails(1500)
            elif hasattr(self.db, "save_thumbnails_only"):
                self.db.save_thumbnails_only()
        if hasattr(self, "one_up_view") and hasattr(self.one_up_view, "filmstrip"):
            self.one_up_view.filmstrip.clear_cache()

        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            cur_norm = os.path.normcase(os.path.normpath(self.one_up_view.current_photo_path))
            if cur_norm in norm_targets:
                canvas = self.one_up_view.canvas
                canvas.cancel_crop()
                canvas.cancel_straighten()
                canvas.cancel_text_tool()
                canvas.cancel_redeye()
                canvas.cancel_retouch()
                canvas.cancel_manual_face_add()
                if hasattr(self.one_up_view, "edit_panel") and hasattr(self.one_up_view.edit_panel, "main_stack"):
                    self.one_up_view.edit_panel.main_stack.setCurrentIndex(0)
                self.one_up_view.open_photo(
                    self.db,
                    self.one_up_view.current_index,
                    self.one_up_view.available_indices,
                    direct_path=self.one_up_view.current_photo_path
                )
        elif self.right_drawer.isVisible():
            self._on_selection_changed(list(self.thumb_view.selected_indices))

        self.thumb_view.update()
        if hasattr(self, "photo_tray") and hasattr(self.photo_tray, "thumb_strip"):
            self.photo_tray.thumb_strip.update()
        self.status_bar.showMessage(f"Retouches annulées pour {len(paths)} photo(s).")

    def action_toggle_star(self, paths: Optional[List[str]] = None) -> None:
        """
        FR: Bascule le statut favori / étoilé (ID_PICTURE_STAR).
        EN: Toggles the starred / favorite status (ID_PICTURE_STAR).
        Ref: picasa3.exe @ 0x0068B800 ("star=yes")
        """
        if not paths or isinstance(paths, bool):
            paths = self._get_active_photo_paths()
        if not paths:
            return

        target_set = set(paths)
        for p in paths:
            def _toggle(doc: PicasaIniDocument, fname: str) -> None:
                """
                FR: Inverse l'état étoilé dans le document .picasa.ini.
                EN: Inverts the starred state in the .picasa.ini document.
                """
                st = doc.is_starred(fname)
                doc.set_starred(fname, not st)
            self._update_photo_ini(p, _toggle)

        for it in self.thumb_view.items:
            if it.path in target_set:
                it.starred = not it.starred

        self.thumb_view.update()

        # Mettre à jour l'état de l'étoile dans One-Up view si active
        if self.stack.currentWidget() == self.one_up_view:
            curr_p = self.one_up_view.current_photo_path
            if curr_p and curr_p in target_set:
                new_st = any(it.starred for it in self.thumb_view.items if it.path == curr_p)
                self.one_up_view.update_star_button(new_st)

        # Mettre à jour le photo tray
        sel_items = [it for it in self.thumb_view.items if it.path in target_set]
        if sel_items:
            any_starred = any(it.starred for it in sel_items)
            self.photo_tray.update_star_state(any_starred)

        # Actualiser la catégorie Albums dans l'arborescence (compteur de favoris)
        if hasattr(self, "library_tree"):
            self.library_tree.refresh_albums()

        self.status_bar.showMessage(f"Étoile basculée pour {len(paths)} photo(s).")

    def _on_thumb_star_toggled(self, file_path: str, is_starred: bool) -> None:
        """
        FR: Déclenché lors du clic direct sur l'étoile d'une miniature dans la grille.
        EN: Triggered when clicking directly on a thumbnail's star badge in the grid.
        Ref: picasa3.exe @ thumbui/startoggle, ID_PICTURE_STAR
        """
        def _update(doc: PicasaIniDocument, fname: str) -> None:
            """
            FR: Définit l'état étoilé dans le document .picasa.ini.
            EN: Sets the starred state in the .picasa.ini document.
            """
            doc.set_starred(fname, is_starred)
        self._update_photo_ini(file_path, _update)

        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path == file_path:
            self.one_up_view.update_star_button(is_starred)

        for it in self.thumb_view.items:
            if it.path == file_path:
                it.starred = is_starred
                break

        eff = self.photo_tray.get_effective_items()
        if any(getattr(it, "path", None) == file_path for it in eff):
            self.photo_tray.update_star_state(is_starred)

        if hasattr(self, "library_tree"):
            self.library_tree.refresh_albums()

    def _on_one_up_star_toggled(self, file_path: str, is_starred: bool) -> None:
        """
        FR: Déclenché lors du basculement d'étoile depuis One-Up View (bouton ou Ctrl+T).
        EN: Triggered when toggling the star from One-Up View (button or Ctrl+T).
        """
        for it in self.thumb_view.items:
            if it.path == file_path:
                it.starred = is_starred
                break
        self.thumb_view.update()

        eff = self.photo_tray.get_effective_items()
        if any(getattr(it, "path", None) == file_path for it in eff):
            self.photo_tray.update_star_state(is_starred)

        if hasattr(self, "library_tree"):
            self.library_tree.refresh_albums()

    def action_select_all(self) -> None:
        """
        FR: Sélectionne toutes les photos visibles (ID_ALBUM_SELECTALLPICTURES, Ctrl+A).
        EN: Selects all visible photos (ID_ALBUM_SELECTALLPICTURES, Ctrl+A).
        """
        self.thumb_view.selected_indices = set(self.thumb_view.filtered_indices)
        self.thumb_view.selection_changed.emit(list(self.thumb_view.selected_indices))
        self.thumb_view.update()
        self.status_bar.showMessage(f"{len(self.thumb_view.selected_indices)} photo(s) sélectionnée(s).")

    def action_clear_selection(self) -> None:
        """
        FR: Désélectionne toutes les photos (ID_CLEAR_SELECTION).
        EN: Clears the current photo selection (ID_CLEAR_SELECTION).
        """
        self.thumb_view.selected_indices.clear()
        self.thumb_view.selection_changed.emit([])
        self.thumb_view.update()
        self.status_bar.showMessage("Sélection annulée.")

    def action_select_starred(self) -> None:
        """
        FR: Sélectionne toutes les photos étoilées (ID_SELECTSTAR).
        EN: Selects all starred photos (ID_SELECTSTAR).
        """
        starred_indices = {i for i, it in enumerate(self.thumb_view.items) if it.starred}
        self.thumb_view.selected_indices = starred_indices
        self.thumb_view.selection_changed.emit(list(starred_indices))
        self.thumb_view.update()
        self.status_bar.showMessage(f"{len(starred_indices)} photo(s) étoilée(s) sélectionnée(s).")

    def action_invert_selection(self) -> None:
        """
        FR: Inverse la sélection courante (ID_SELECT_INVERT).
        EN: Inverts the current selection (ID_SELECT_INVERT).
        """
        all_vis = set(self.thumb_view.filtered_indices)
        self.thumb_view.selected_indices = all_vis - self.thumb_view.selected_indices
        self.thumb_view.selection_changed.emit(list(self.thumb_view.selected_indices))
        self.thumb_view.update()

    def action_properties(self) -> None:
        """
        FR: Affiche les propriétés détaillées de l'image (ID_PICTURE_PROPERTIES, Alt+Enter / imageproperties.fen).
        EN: Displays the detailed image properties (ID_PICTURE_PROPERTIES, Alt+Enter / imageproperties.fen).
        """
        paths = self._get_active_photo_paths()
        if not paths and self.thumb_view.items:
            paths = [it.path for it in self.thumb_view.items if it.path]
        if paths:
            dlg = PicasaImagePropertiesDialog(paths, current_index=0, parent=self)
            dlg.exec()
        else:
            self._on_tray_panel_toggled("properties")

    def _bake_photo_edits_on_disk(self, target_path: str) -> bool:
        """
        FR: Grave les retouches non-destructives `.picasa.ini` en pleine résolution sur le disque,
        sauvegarde l'original dans `.picasaoriginals/`, préserve EXIF/ICC et écrit `backuphash`.
        EN: Bakes non-destructive `.picasa.ini` edits at full resolution to disk,
        backs up the original in `.picasaoriginals/`, preserves EXIF/ICC, and writes `backuphash`.

        Ref: picasa3.exe @ 0x008814AC, 0x009B9290, 0x00456A15
        """
        if not target_path or not os.path.exists(target_path):
            return False
        target_p = Path(target_path)
        folder = target_p.parent
        ini_p = folder / ".picasa.ini"
        if not ini_p.exists():
            alt_p = folder / "Picasa.ini"
            if alt_p.exists():
                ini_p = alt_p
        if not ini_p.exists():
            return False
        try:
            doc_check = PicasaIniParser.parse_file(ini_p)
            sec_check = doc_check.get_section(target_p.name)
            if not sec_check or not any(
                sec_check.get(k)
                for k in ("filters", "crop", "rotate", "tilt", "text", "autolight", "backlight", "colorfix", "redeye", "retouch")
            ):
                return False
            full_rendered = PicasaImageProcessor.load_transformed_image(
                target_path, max_size=0, parsed_ini=doc_check
            )
            if full_rendered is None:
                return False

            originals_dir = folder / ".picasaoriginals"
            originals_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(str(originals_dir), 0x02)
                except Exception:
                    pass
            backup_file = originals_dir / target_p.name
            if not backup_file.exists():
                import shutil
                shutil.copy2(target_path, str(backup_file))

            exif_bytes = None
            icc_profile = None
            try:
                from PIL import Image
                with Image.open(target_path) as meta_im:
                    icc_profile = meta_im.info.get("icc_profile")
                    raw_exif = meta_im.getexif()
                    if raw_exif:
                        if 0x0112 in raw_exif:
                            raw_exif[0x0112] = 1
                        exif_bytes = raw_exif.tobytes()
            except Exception:
                pass
            save_kwargs: dict = {}
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile
            ext = target_p.suffix.lower()
            if ext in (".jpg", ".jpeg"):
                full_rendered.convert("RGB").save(target_path, format="JPEG", quality=95, **save_kwargs)
            elif ext == ".png":
                full_rendered.save(target_path, format="PNG", **save_kwargs)
            else:
                full_rendered.save(target_path, **save_kwargs)

            import zlib
            try:
                b_hash = (zlib.crc32(backup_file.read_bytes()) & 0xFFFF) or 1
            except Exception:
                b_hash = 1

            def _clear_baked(doc: PicasaIniDocument, fname: str) -> None:
                doc.set_crop(fname, None)
                doc.set_rotate(fname, 0)
                doc.set_tilt(fname, None)
                doc.set_text(fname, None)
                sec = doc.get_or_create_section(fname)
                for k in ("filters", "crop", "rotate", "tilt", "text", "textactive", "backlight", "autolight", "colorfix", "redeye", "retouch"):
                    sec.remove(k)
                sec.set("backuphash", str(b_hash))

            self._update_photo_ini(target_path, _clear_baked)
            if self.db is not None and hasattr(self.db, "update_photo_thumbnails_from_disk"):
                self.db.update_photo_thumbnails_from_disk(target_path, persist_to_disk=False)
            self.thumb_view.invalidate_item(target_path)
            return True
        except Exception:
            return False

    def action_save(self) -> None:
        """
        FR: Enregistre les retouches de la photo active ou des photos sélectionnées (ID_FILE_SAVE, Ctrl+S).
        EN: Saves the edits of the active photo or selected photos (ID_FILE_SAVE, Ctrl+S).
        """
        if self.stack.currentWidget() == self.one_up_view:
            ok = self.one_up_view.save_current_photo()
            if ok:
                if self.one_up_view.current_photo_path:
                    self.thumb_view.invalidate_item(self.one_up_view.current_photo_path)
                self.thumb_view.update()
                self.status_bar.showMessage("Modifications enregistrées (.picasaoriginals sauvegardé).")
            else:
                self.status_bar.showMessage("Impossible d'enregistrer la photo.")
        else:
            paths = self._get_active_photo_paths()
            saved = 0
            for p in paths:
                if self._bake_photo_edits_on_disk(p):
                    saved += 1
            if saved > 0:
                if self.db is not None and hasattr(self.db, "schedule_save_thumbnails"):
                    self.db.schedule_save_thumbnails(1500)
                self.thumb_view.update()
                self.status_bar.showMessage(f"Modifications enregistrées pour {saved} photo(s) (.picasaoriginals sauvegardé).")
            else:
                self.status_bar.showMessage("Aucune modification en attente à enregistrer.")

    def action_save_as(self) -> None:
        """
        FR: Enregistre sous un nouveau nom (ID_FILE_SAVEAS, Ctrl+Shift+S).
        EN: Saves the photo under a new filename (ID_FILE_SAVEAS, Ctrl+Shift+S).
        """
        paths = self._get_active_photo_paths()
        if not paths:
            return
        orig_path = paths[0]
        ext = os.path.splitext(orig_path)[1]
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            orig_path,
            f"Image files (*{ext} *{'*.jpg' if ext != '.jpg' else ''});;All Files (*.*)"
        )
        if save_path:
            if self.stack.currentWidget() == self.one_up_view:
                self.one_up_view.save_current_photo_as(save_path)
            else:
                from picasa_py.ui.image_processor import PicasaImageProcessor
                pil_img = PicasaImageProcessor.load_transformed_image(orig_path)
                if pil_img is not None:
                    pil_img.save(save_path, quality=95)
                else:
                    import shutil
                    shutil.copy2(orig_path, save_path)
            self.status_bar.showMessage(f"Fichier enregistré sous : {os.path.basename(save_path)}")

    def action_save_a_copy(self) -> None:
        """
        FR: Enregistre une copie de la photo (ID_FILE_SAVEACOPY).
        EN: Saves a copy of the photo (ID_FILE_SAVEACOPY).
        """
        paths = self._get_active_photo_paths()
        if not paths:
            return
        orig_path = paths[0]
        p = Path(orig_path)
        copy_name = f"{p.stem}-1{p.suffix}"
        counter = 1
        while (p.parent / copy_name).exists():
            counter += 1
            copy_name = f"{p.stem}-{counter}{p.suffix}"
        copy_path = str(p.parent / copy_name)

        if self.stack.currentWidget() == self.one_up_view:
            self.one_up_view.save_current_photo_as(copy_path)
        else:
            from picasa_py.ui.image_processor import PicasaImageProcessor
            pil_img = PicasaImageProcessor.load_transformed_image(orig_path)
            if pil_img is not None:
                pil_img.save(copy_path, quality=95)
            else:
                import shutil
                shutil.copy2(orig_path, copy_path)
        self.status_bar.showMessage(f"Copie créée : {copy_name}")

    def action_set_desktop_wallpaper(self, paths: Optional[List[str]] = None) -> None:
        """
        FR: Définit la photo sélectionnée comme fond d'écran Windows (ID_WALLPAPER).
        EN: Sets the selected photo as the desktop wallpaper (ID_WALLPAPER).
        Ref: picasa3.exe @ ID_WALLPAPER, SystemParametersInfoW SPI_SETDESKWALLPAPER
        """
        if paths is None:
            paths = self._get_active_photo_paths()
        if not paths:
            return
        target_path = paths[0]
        if not os.path.exists(target_path):
            return

        from picasa_py.ui.image_processor import PicasaImageProcessor
        wallpaper_path = os.path.abspath(target_path)
        pil_img = PicasaImageProcessor.load_transformed_image(target_path)
        if pil_img is not None:
            try:
                wp_dir = Path.home() / "Pictures" / "Picasa"
                wp_dir.mkdir(parents=True, exist_ok=True)
                wp_file = wp_dir / "Picasa_Background.bmp"
                pil_img.save(str(wp_file))
                wallpaper_path = str(wp_file.resolve())
            except Exception:
                wallpaper_path = os.path.abspath(target_path)

        if sys.platform == "win32":
            try:
                import ctypes
                SPI_SETDESKWALLPAPER = 20
                SPIF_UPDATEINIFILE = 0x01
                SPIF_SENDCHANGE = 0x02
                res = ctypes.windll.user32.SystemParametersInfoW(
                    SPI_SETDESKWALLPAPER,
                    0,
                    wallpaper_path,
                    SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
                )
                if res:
                    self.status_bar.showMessage(f"Fond d'écran appliqué : {os.path.basename(target_path)}")
                    return
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                script = f'tell application "Finder" to set desktop picture to POSIX file "{wallpaper_path}"'
                subprocess.run(["osascript", "-e", script], check=True)
                self.status_bar.showMessage(f"Fond d'écran appliqué : {os.path.basename(target_path)}")
                return
            except Exception:
                pass
        else:
            try:
                uri = Path(wallpaper_path).resolve().as_uri()
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], check=True)
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], check=False)
                self.status_bar.showMessage(f"Fond d'écran appliqué : {os.path.basename(target_path)}")
                return
            except Exception:
                pass
        self.status_bar.showMessage("Impossible de définir le fond d'écran sur ce système.")

    def action_auto_contrast(self) -> None:
        """
        FR: Applique le contraste automatique (ID_PICTURE_AUTO_LIGHTING).
        EN: Applies automatic contrast (ID_PICTURE_AUTO_LIGHTING).
        """
        if self.stack.currentWidget() == self.one_up_view:
            self.one_up_view._on_apply_effect("autocontrast", {})
            self.status_bar.showMessage("Contraste automatique appliqué.")
        else:
            paths = self._get_active_photo_paths()
            if paths:
                self.action_view_and_edit(paths[0])
                self.one_up_view._on_apply_effect("autocontrast", {})

    def action_auto_color(self) -> None:
        """
        FR: Applique la couleur automatique (ID_PICTURE_AUTO_COLOR).
        EN: Applies automatic color adjustment (ID_PICTURE_AUTO_COLOR).
        """
        if self.stack.currentWidget() == self.one_up_view:
            self.one_up_view._on_apply_effect("autocolor", {})
            self.status_bar.showMessage("Couleur automatique appliquée.")
        else:
            paths = self._get_active_photo_paths()
            if paths:
                self.action_view_and_edit(paths[0])
                self.one_up_view._on_apply_effect("autocolor", {})

    def action_refresh_thumbnails(self, folder_or_album: Optional[str] = None) -> None:
        """
        FR: Actualise les miniatures de la photothèque (ID_REFRESH_THUMB).
        EN: Refreshes the photo library thumbnails (ID_REFRESH_THUMB).
        """
        self.thumb_view._pixmap_cache.clear()
        self.thumb_view.update()
        self.status_bar.showMessage("Miniatures actualisées.")

    def action_slideshow_for_folder(self, folder_path: str) -> None:
        """
        FR: Lance le diaporama pour un dossier cliqué.
        EN: Starts the slideshow for a clicked folder.
        """
        norm_target = folder_path.replace("\\", "/").rstrip("/").lower()
        paths = [
            it.path for it in self.thumb_view.items
            if it.folder_path.replace("\\", "/").rstrip("/").lower() == norm_target and it.path
        ]
        self._on_album_slideshow(paths)

    def _get_album_music(self, album_name: str) -> Optional[str]:
        """
        FR: Recherche le chemin de la musique associée à un album dans les fichiers .picasa.ini.
        EN: Searches for the music track path associated with an album in .picasa.ini files.
        """
        if not self.db:
            return None
        watched = [p.rstrip("\\/") for p, st in self.db.get_watched_folders().items() if st in ("1", "2")]
        for w in watched:
            ini_p = os.path.join(w, ".picasa.ini")
            if os.path.exists(ini_p):
                try:
                    doc = PicasaIniParser.parse_file(ini_p)
                    for sec in doc.sections:
                        if sec.name.startswith(".album:"):
                            if sec.get("name", "").strip().lower() == album_name.strip().lower() or sec.name[7:].strip() == album_name.strip():
                                m = sec.get("music", "").strip()
                                if m and os.path.exists(m):
                                    return m
                except Exception:
                    pass
        return None

    def action_slideshow_for_album(self, album_name: str) -> None:
        """
        FR: Lance le diaporama pour un album virtuel avec sa musique de présentation.
        EN: Starts the slideshow for a virtual album with its background music track.
        """
        if album_name:
            indices = self._get_album_item_indices("", album_name)
            if not indices:
                indices = self._get_album_item_indices(album_name, album_name)
            paths = [
                self.thumb_view.items[i].path
                for i in indices
                if 0 <= i < len(self.thumb_view.items) and self.thumb_view.items[i].path
            ]
        else:
            paths = [it.path for it in self.thumb_view.items if it.path]
        music_path = self._get_album_music(album_name)
        self._on_album_slideshow(paths, music_path=music_path)

    def action_slideshow_for_person(self, contact_id: str) -> None:
        """
        FR: Lance le diaporama pour une personne.
        EN: Starts the slideshow for a person.
        """
        if not self.db or not self.db.face_manager:
            return
        person = self.db.face_manager.get_person(contact_id)
        if person:
            paths = [
                self.thumb_view.items[idx].path
                for idx in person.photo_indices
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
            self._on_album_slideshow(paths)

    def action_new_album(self) -> None:
        """
        FR: Création d'un nouvel album virtuel (ID_FILE_NEWLABEL, Ctrl+N / album.fen).
        EN: Creates a new virtual album (ID_FILE_NEWLABEL, Ctrl+N / album.fen).
        """
        selected = self._get_active_photo_paths()
        self.action_new_album_with_photos(selected)

    def action_new_album_with_photos(self, photo_paths: Optional[List[str]] = None) -> None:
        """
        FR: Ouvre le dialogue complet de création d'album (album.fen) et associe les photos.
        EN: Opens the full album creation dialog (album.fen) and links the photos.
        """
        photos = photo_paths or []
        photo_dates = []
        for p in photos:
            try:
                mtime = os.path.getmtime(p)
                photo_dates.append(datetime.fromtimestamp(mtime))
            except Exception:
                pass

        dlg = PicasaAlbumDialog(photo_dates=photo_dates, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        album_data = dlg.get_album_data()
        album_name = album_data["name"]
        if not album_name:
            return

        import uuid
        album_uid = uuid.uuid4().hex[:16]

        # Enregistrer la section [.album:<uid>] dans le dossier de la première photo,
        # ou dans le premier dossier surveillé, ou dans le dossier utilisateur
        target_dir = None
        if photos and os.path.exists(photos[0]):
            target_dir = os.path.dirname(photos[0])
        elif self.db:
            watched = [p.rstrip("\\/") for p, st in self.db.get_watched_folders().items() if st in ("1", "2")]
            if watched:
                target_dir = watched[0]

        if target_dir and os.path.exists(target_dir):
            ini_path = os.path.join(target_dir, ".picasa.ini")
            doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()
            sec = doc.get_or_create_section(f".album:{album_uid}")
            sec.set("name", album_name)
            sec.set("token", album_uid)
            if album_data.get("date"):
                sec.set("date", album_data["date"])
            if album_data.get("music"):
                sec.set("music", album_data["music"])
            if album_data.get("location"):
                sec.set("location", album_data["location"])
            if album_data.get("description"):
                sec.set("description", album_data["description"])
                sec.set("caption", album_data["description"])
            doc.write_file(ini_path)
            if self.db and hasattr(self.db, "_sync_album_sections_from_ini_doc"):
                try:
                    self.db._sync_album_sections_from_ini_doc(doc)
                except Exception:
                    pass
            if self.db and hasattr(self.db, "invalidate_ini_cache"):
                self.db.invalidate_ini_cache(ini_path)
            elif self.db and hasattr(self.db, "_ini_cache"):
                self.db._ini_cache.pop(os.path.normcase(os.path.abspath(ini_path)), None)

        # Lier les photos à l'album
        if photos:
            self.action_add_photos_to_album(photos, album_uid)

        self.notify_albums_changed()
        self.status_bar.showMessage(f"Album créé : « {album_name} » ({len(photos)} photo(s)).")

    def action_add_photos_to_album(self, photo_paths: List[str], album_token: str) -> None:
        """
        FR: Ajoute une liste de photos à un album virtuel identifié par son jeton.
        EN: Adds a list of photos to a virtual album identified by its token.
        """
        if not photo_paths:
            return
        for p in photo_paths:
            def _add_alb(doc: PicasaIniDocument, fname: str) -> None:
                """
                FR: Ajoute le jeton d'album à la clé albums de la section INI de la photo.
                EN: Appends the album token to the albums key of the photo's INI section.
                """
                sec = doc.get_or_create_section(fname)
                cur = sec.get("albums", "")
                parts = [x.strip() for x in cur.split(",") if x.strip()]
                if album_token not in parts:
                    parts.append(album_token)
                    sec.set("albums", ",".join(parts))
            self._update_photo_ini(p, _add_alb)
        self.notify_albums_changed()
        self.status_bar.showMessage(f"{len(photo_paths)} photo(s) ajoutée(s) à l'album.")

    def action_reset_faces(self, photo_paths: List[str]) -> None:
        """
        FR: Réinitialise les visages détectés pour les photos (ID_PICTURE_RESET_FACES).
        EN: Resets detected faces for the specified photos (ID_PICTURE_RESET_FACES).
        """
        for p in photo_paths:
            self._update_photo_ini(p, lambda doc, fname: doc.get_or_create_section(fname).remove("faces"))
        self.status_bar.showMessage(f"Visages réinitialisés pour {len(photo_paths)} photo(s).")

    def action_edit_folder_description(self, folder_path: str) -> None:
        """
        FR: Modifie le nom / la description d'un dossier dans la section [Picasa] de .picasa.ini.
        EN: Edits a folder's name / description in the [Picasa] section of .picasa.ini.
        Ref: picasa3.exe @ Folder::ID_ALBUM_EDITDESCRIPTION (0x00CAE244)
        """
        if not folder_path or not os.path.isdir(folder_path):
            return
        ini_path = os.path.join(folder_path, ".picasa.ini")
        if not os.path.exists(ini_path):
            alt = os.path.join(folder_path, "Picasa.ini")
            if os.path.exists(alt):
                ini_path = alt
        doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()
        picasa_sec = doc.get_section("Picasa")
        current_desc = (picasa_sec.get("description") or picasa_sec.get("name") or os.path.basename(folder_path.rstrip("\\/"))) if picasa_sec else os.path.basename(folder_path.rstrip("\\/"))

        new_desc, ok = QInputDialog.getText(self, "Description du dossier", "Nom ou description :", text=current_desc)
        if ok and new_desc.strip():
            sec = doc.get_or_create_section("Picasa")
            sec.set("name", new_desc.strip())
            sec.set("description", new_desc.strip())
            doc.write_file(ini_path)
            if self.db and hasattr(self.db, "_ini_cache"):
                self.db._ini_cache.pop(os.path.normcase(os.path.abspath(ini_path)), None)
            self.notify_folders_changed()
            self.status_bar.showMessage(f"Description du dossier enregistrée : {new_desc.strip()}")

    def action_edit_album_description(self, album_name: str) -> None:
        """
        FR: Édition des propriétés complètes de l'album (album.fen).
        EN: Edits the complete properties of the album (album.fen).
        """
        music_path = self._get_album_music(album_name) or ""
        dlg = PicasaAlbumDialog(album_name=album_name, music_path=music_path, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_album_data()
            new_name = data.get("name", album_name)
            if self.db:
                watched = [p.rstrip("\\/") for p, st in self.db.get_watched_folders().items() if st in ("1", "2")]
                for w in watched:
                    ini_p = os.path.join(w, ".picasa.ini")
                    if os.path.exists(ini_p):
                        try:
                            from picasa_py.ini.parser import PicasaIniParser
                            doc = PicasaIniParser.parse_file(ini_p)
                            mod = False
                            for sec in doc.sections:
                                if sec.name.startswith(".album:") and (sec.get("name") == album_name or sec.name[7:] == album_name):
                                    if new_name:
                                        sec.set("name", new_name)
                                    if data.get("date"):
                                        sec.set("date", data["date"])
                                    if data.get("music"):
                                        sec.set("music", data["music"])
                                    if data.get("location"):
                                        sec.set("location", data["location"])
                                    if data.get("description"):
                                        sec.set("description", data["description"])
                                        sec.set("caption", data["description"])
                                    mod = True
                            if mod:
                                doc.write_file(ini_p)
                                if self.db and hasattr(self.db, "_sync_album_sections_from_ini_doc"):
                                    try:
                                        self.db._sync_album_sections_from_ini_doc(doc)
                                    except Exception:
                                        pass
                                if self.db and hasattr(self.db, "invalidate_ini_cache"):
                                    self.db.invalidate_ini_cache(ini_p)
                                elif self.db and hasattr(self.db, "_ini_cache"):
                                    self.db._ini_cache.pop(os.path.normcase(os.path.abspath(ini_p)), None)
                        except Exception:
                            pass
            self.notify_albums_changed()
            self.status_bar.showMessage(f"Propriétés de l'album « {new_name} » mises à jour.")

    def action_edit_person(self, contact_id: str, person_name: str) -> None:
        """
        FR: Ouvre une boîte de dialogue pour renommer une personne existante.
        EN: Opens a dialog to rename an existing person.
        """
        new_name, ok = QInputDialog.getText(self, "Modifier la personne", "Nom de la personne :", text=person_name)
        if ok and new_name.strip() and self.db and self.db.face_manager:
            self.db.face_manager.rename_person(contact_id, new_name.strip())
            self.library_tree.populate_from_database(self.db)
            self.status_bar.showMessage(f"Personne renommée : {new_name.strip()}")

    def action_delete_folder(self, folder_path: str) -> None:
        """
        FR: Supprime un dossier et ses photos vers la Corbeille après confirmation.
        EN: Deletes a folder and its photos to the Recycle Bin after confirmation.
        """
        rep = QMessageBox.question(self, "Supprimer le dossier", f"Voulez-vous supprimer le dossier « {os.path.basename(folder_path)} » et ses photos vers la Corbeille ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if rep == QMessageBox.StandardButton.Yes:
            recycle_or_delete_file(folder_path)
            self.thumb_view.filter_by_folder(None)
            self.notify_folders_changed()
            self.status_bar.showMessage("Dossier placé dans la Corbeille.")

    def action_delete_album(self, album_name: str) -> None:
        """
        FR: Supprime un album virtuel après confirmation sans supprimer les photos originales.
        EN: Deletes a virtual album after confirmation without deleting the original photos.
        """
        rep = QMessageBox.question(self, "Supprimer l'album", f"Voulez-vous supprimer l'album « {album_name} » ?\n(Les photos originales ne seront pas supprimées)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if rep == QMessageBox.StandardButton.Yes:
            if self.db:
                self.db.delete_album(album_name)
            self.notify_albums_changed()
            if self.thumb_view.current_folder_filter and self.thumb_view.current_folder_filter.startswith("album:"):
                self.thumb_view.filter_by_folder(None)
            self.status_bar.showMessage(f"Album « {album_name} » supprimé.")

    def action_delete_person(self, contact_id: str, person_name: str) -> None:
        """
        FR: Retire une personne de Picasa après confirmation sans supprimer les photos originales.
        EN: Removes a person from Picasa after confirmation without deleting the original photos.
        """
        rep = QMessageBox.question(self, "Supprimer la personne", f"Voulez-vous retirer « {person_name} » de Picasa ?\n(Les photos originales ne seront pas supprimées)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if rep == QMessageBox.StandardButton.Yes and self.db and self.db.face_manager:
            self.db.face_manager.delete_person(contact_id)
            self.library_tree.populate_from_database(self.db)
            self.status_bar.showMessage(f"« {person_name} » retiré de Picasa.")

    def action_poster(self) -> None:
        """
        FR: Ouvre l'atelier de création de poster multi-pages (poster.fen).
        EN: Opens the multi-page poster creation workshop (poster.fen).
        """
        paths = self._get_active_photo_paths()
        if not paths:
            QMessageBox.information(self, "Créer un poster", "Sélectionnez une photo pour créer un poster.")
            return
        dlg = PicasaPosterDialog(paths[0], parent=self)
        dlg.exec()

    def action_email(self) -> None:
        """
        FR: Envoie les photos sélectionnées par courrier électronique (CHOOSE_MAIL_TEXT.XML).
        EN: Sends the selected photos via email (CHOOSE_MAIL_TEXT.XML).
        """
        paths = self._get_active_photo_paths()
        if not paths:
            QMessageBox.information(self, "E-mail", "Sélectionnez au moins une photo à envoyer par e-mail.")
            return
        dlg = PicasaEmailDialog(paths, parent=self)
        dlg.exec()

    def action_contact_manager(self) -> None:
        """
        FR: Ouvre le gestionnaire de personnes et de contacts (contactmgr.fen).
        EN: Opens the people and contact manager dialog (contactmgr.fen).
        """
        if not self.db:
            QMessageBox.warning(self, "Gestionnaire de personnes", "Aucune base de données active.")
            return
        dlg = PicasaContactManagerDialog(self.db, parent=self)
        dlg.exec()
        self.library_tree.refresh_people()
        self.status_bar.showMessage("Personnes et contacts mis à jour.")

    def action_create_database(self, target_dir: Optional[str] = None) -> Optional[PicasaDatabase]:
        """
        FR: Crée une nouvelle base de données Picasa 3 complète et vierge dans un dossier choisi
        et bascule immédiatement l'application sur cette nouvelle base (ID_CREATE_DATABASE).
        EN: Creates a new complete and empty Picasa 3 database in a chosen directory
        and immediately switches the application to this new database (ID_CREATE_DATABASE).
        Ref: picasa3.exe @ 0x004156F0 (CThumbDB::Init)
        """
        if isinstance(target_dir, bool):
            target_dir = None
        interactive = target_dir is None
        persist_pref = interactive
        if target_dir is None:
            dlg = PicasaDatabaseSelectorDialog(
                mode="create",
                current_db=self.db,
                style=self.style,
                parent=self,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.selected_path:
                return None
            target_dir = dlg.selected_path
            persist_pref = dlg.persist_as_default

        try:
            p_db3, _ = PicasaDatabase.resolve_database_dirs(target_dir, for_creation=True)
            if interactive and (p_db3 / "thumbindex.db").exists():
                rep = QMessageBox.question(
                    self,
                    "Base de données existante détectée",
                    f"Une base de données Picasa existe déjà dans :\n{p_db3}\n\n"
                    "Voulez-vous la réinitialiser avec une nouvelle base vierge ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if rep != QMessageBox.StandardButton.Yes:
                    return None

            # FR: Arrêter impérativement tout scan/watcher de l'ancienne base AVANT d'écrire la nouvelle base sur disque
            # EN: Strictly stop any active scan/watcher on the old database BEFORE writing the new database to disk
            self.stop_background_tasks()
            if self.watcher is not None and hasattr(self.watcher, "stop"):
                self.watcher.stop()

            new_db = PicasaDatabase.create_new(target_dir)
            self.switch_database(new_db, persist_preference=persist_pref)
            self.status_bar.showMessage(f"Nouvelle base de données créée et activée : {new_db.db3_dir}")
            if interactive:
                QMessageBox.information(
                    self,
                    "Nouvelle base de données créée",
                    f"La nouvelle base de données Picasa a été initialisée avec succès dans :\n{new_db.db3_dir}\n\n"
                    "Vous pouvez maintenant ajouter des dossiers via Fichier > Ajouter un dossier à Picasa...",
                )
            return new_db
        except Exception as e:
            if interactive:
                QMessageBox.critical(self, "Erreur de création", f"Impossible de créer la base de données : {e}")
            self.status_bar.showMessage(f"Erreur de création de base : {e}")
            return None

    def action_open_database(self, target_dir: Optional[str] = None) -> Optional[PicasaDatabase]:
        """
        FR: Ouvre une base de données Picasa 3 existante depuis un dossier choisi (db3/ ou dossier parent)
        et bascule à chaud l'application sur cette base (ID_OPEN_DATABASE).
        EN: Opens an existing Picasa 3 database from a chosen folder (db3/ or parent directory)
        and hot-switches the application to this database (ID_OPEN_DATABASE).
        Ref: picasa3.exe @ 0x006B6070 (CThumbDB::Open), 0x008b1bf0 (repository.dat)
        """
        if isinstance(target_dir, bool):
            target_dir = None
        interactive = target_dir is None
        persist_pref = interactive
        if target_dir is None:
            dlg = PicasaDatabaseSelectorDialog(
                mode="open",
                current_db=self.db,
                style=self.style,
                parent=self,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.selected_path:
                return None
            target_dir = dlg.selected_path
            persist_pref = dlg.persist_as_default

        try:
            p_db3, _ = PicasaDatabase.resolve_database_dirs(target_dir, for_creation=False)
            has_db_files = (
                (p_db3 / "thumbindex.db").exists()
                or any(p_db3.glob("*.pmp"))
                or any(p_db3.glob("*_index.db"))
            )
            if not has_db_files:
                if interactive:
                    rep = QMessageBox.question(
                        self,
                        "Aucune base détectée",
                        f"Aucune base Picasa existante n'a été trouvée dans :\n{target_dir}\n\n"
                        "Voulez-vous initialiser une nouvelle base de données dans ce dossier ?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes,
                    )
                    if rep == QMessageBox.StandardButton.Yes:
                        return self.action_create_database(target_dir)
                    return None

            # FR: Arrêter impérativement tout scan/watcher de l'ancienne base AVANT d'ouvrir la nouvelle base
            # EN: Strictly stop any active scan/watcher on the old database BEFORE opening the new database
            self.stop_background_tasks()
            if self.watcher is not None and hasattr(self.watcher, "stop"):
                self.watcher.stop()

            opened_db = PicasaDatabase.open(target_dir)
            self.switch_database(opened_db, persist_preference=persist_pref)
            count = len(opened_db.index)
            self.status_bar.showMessage(f"Base de données ouverte ({opened_db.db3_dir}) : {count} entrées indexées")
            if interactive:
                QMessageBox.information(
                    self,
                    "Base de données ouverte",
                    f"La base de données Picasa a été chargée avec succès :\n{opened_db.db3_dir}\n\n"
                    f"Entrées indexées : {count}",
                )
            return opened_db
        except Exception as e:
            if interactive:
                QMessageBox.critical(self, "Erreur d'ouverture", f"Impossible d'ouvrir la base de données : {e}")
            self.status_bar.showMessage(f"Erreur d'ouverture de base : {e}")
            return None

    def action_move_database(self) -> None:
        """
        FR: Déplacement de la base de données Picasa vers un autre emplacement (move_database.fen).
        EN: Moves the Picasa database to another location (move_database.fen).
        """
        if not self.db:
            QMessageBox.warning(self, "Déplacer la base", "Aucune base de données active.")
            return
        dlg = PicasaMoveDatabaseDialog(self.db, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.new_db_path:
            self.switch_database(dlg.new_db_path, persist_preference=True)

    def action_compact_database(self) -> None:
        """
        FR: Compactage et défragmentation de la base de données (compacting.fen).
        EN: Compacts and defragments the database (compacting.fen).
        """
        if not self.db:
            QMessageBox.warning(self, "Compacter la base", "Aucune base de données active.")
            return
        try:
            self.status_bar.showMessage("Compactage de la base de données en cours...")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            compact_res = self.db.compact()
            QApplication.restoreOverrideCursor()
            if isinstance(compact_res, tuple) and len(compact_res) == 2:
                saved_bytes = max(0, int(compact_res[0]) - int(compact_res[1]))
            else:
                saved_bytes = max(0, int(compact_res))
            reclaimed_kb = max(0, saved_bytes // 1024)
            self.status_bar.showMessage(f"Compactage terminé. Espace récupéré : {reclaimed_kb} Ko.")
            QMessageBox.information(
                self,
                "Compactage terminé",
                f"La base de données a été compactée avec succès.\nEspace récupéré : {reclaimed_kb} Ko."
            )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Erreur de compactage", f"Impossible de compacter la base : {e}")

    def action_clean_picasa_traces(
        self,
        target_dir: Optional[str | Path] = None,
        confirm: bool = True,
    ) -> int:
        """
        FR: Permet de choisir un répertoire et de supprimer récursivement tous les fichiers
        `.picasa.ini` (ainsi que `Picasa.ini`) qu'il contient, avec alertes de pré-vérification,
        d'avertissement détaillé avant suppression et de bilan final (`ID_CLEAN_PICASA_TRACES`).
        Retourne le nombre de fichiers `.picasa.ini` supprimés.
        EN: Lets the user choose a directory and recursively delete all `.picasa.ini` (and
        `Picasa.ini`) files under it, with pre-check, detailed warning confirmation, and
        completion summary alerts (`ID_CLEAN_PICASA_TRACES`).
        Returns the number of deleted `.picasa.ini` files.
        Ref: picasa3.exe @ 0x0068AC80 (.picasa.ini), AGENTS.md §4 bis.3
        """
        if isinstance(target_dir, bool):
            target_dir = None

        interactive = target_dir is None
        if target_dir is None:
            default_dir = str(Path.home())
            cur_filter = getattr(self.thumb_view, "current_folder_filter", None)
            if cur_filter and not str(cur_filter).startswith(("album:", "person:", "starred")) and os.path.isdir(str(cur_filter)):
                default_dir = str(cur_filter)
            chosen = QFileDialog.getExistingDirectory(
                self,
                "Choisir le répertoire dont supprimer récursivement les traces Picasa (.picasa.ini)",
                default_dir,
            )
            if not chosen:
                return 0
            target_dir = chosen

        root_path = Path(target_dir)
        if not root_path.exists() or not root_path.is_dir():
            if interactive or confirm:
                QMessageBox.warning(
                    self,
                    "Nettoyer les traces Picasa",
                    f"Le répertoire sélectionné est introuvable ou invalide :\n{root_path}",
                )
            return 0

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            traces = PicasaDatabase.find_picasa_ini_traces(root_path)
        finally:
            QApplication.restoreOverrideCursor()

        if not traces:
            self.status_bar.showMessage(f"Aucune trace .picasa.ini trouvée dans {root_path}")
            if interactive or confirm:
                QMessageBox.information(
                    self,
                    "Aucune trace Picasa détectée",
                    f"Aucun fichier .picasa.ini n'a été trouvé dans le répertoire :\n{root_path}\n"
                    "ni dans ses sous-dossiers.",
                )
            return 0

        if confirm:
            preview_lines: List[str] = []
            for p in traces[:8]:
                try:
                    preview_lines.append(f"  • {p.relative_to(root_path)}")
                except Exception:
                    preview_lines.append(f"  • {p}")
            if len(traces) > 8:
                preview_lines.append(f"  • ... et {len(traces) - 8} autre(s) fichier(s)")
            preview_block = "\n".join(preview_lines)

            warn_msg = (
                f"Attention : vous êtes sur le point de supprimer définitivement "
                f"{len(traces)} fichier(s) « .picasa.ini » dans :\n{root_path}\n"
                f"(ainsi que tous ses sous-dossiers).\n\n"
                f"Fichiers détectés :\n{preview_block}\n\n"
                "Conséquences de cette suppression :\n"
                "• Vos fichiers photos et vidéos originaux NE SERONT PAS touchés ni supprimés.\n"
                "• En revanche, les métadonnées locales Picasa stockées uniquement dans ces fichiers "
                ".picasa.ini (retouches non enregistrées sur le disque, étoiles/favoris, albums virtuels, "
                "descriptions de dossiers et tags de visages non écrits en XMP) seront effacées.\n\n"
                "Voulez-vous vraiment supprimer tous ces fichiers .picasa.ini ?"
            )
            rep = QMessageBox.warning(
                self,
                "Confirmation — Nettoyer les traces Picasa (.picasa.ini)",
                warn_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if rep != QMessageBox.StandardButton.Yes:
                self.status_bar.showMessage("Nettoyage des traces Picasa annulé.")
                return 0

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.db is not None:
                deleted, failed = self.db.clean_picasa_ini_traces(root_path)
            else:
                temp_db = PicasaDatabase()
                deleted, failed = temp_db.clean_picasa_ini_traces(root_path)
        finally:
            QApplication.restoreOverrideCursor()

        if deleted:
            self.notify_folders_changed()
            self.notify_albums_changed()
            self.thumb_view.update()

        del_count = len(deleted)
        fail_count = len(failed)
        self.status_bar.showMessage(
            f"Nettoyage Picasa terminé : {del_count} fichier(s) .picasa.ini supprimé(s) dans {root_path}."
        )

        if interactive or confirm:
            if fail_count == 0:
                QMessageBox.information(
                    self,
                    "Nettoyage Picasa terminé",
                    f"Nettoyage terminé avec succès !\n\n"
                    f"{del_count} fichier(s) .picasa.ini ont été supprimés récursivement dans :\n{root_path}",
                )
            else:
                err_preview = "\n".join(f"• {p} : {err}" for p, err in failed[:5])
                QMessageBox.warning(
                    self,
                    "Nettoyage Picasa partiel",
                    f"{del_count} fichier(s) .picasa.ini supprimé(s), mais {fail_count} fichier(s) "
                    f"n'ont pas pu être supprimés :\n\n{err_preview}",
                )

        return del_count

    def action_import(self) -> None:
        """
        FR: Ouvre l'écran d'importation depuis une carte mémoire, un appareil ou un dossier (ACQUIREPANEL_TEXT_FR.XML).
        EN: Opens the import dialog from a memory card, device, or folder (ACQUIREPANEL_TEXT_FR.XML).
        """
        dlg = PicasaImportDialog(db=self.db, parent=self)
        def on_imported(dest_dir: str, count: int) -> None:
            """
            FR: Lance le scan d'arrière-plan sur le dossier de destination après l'importation.
            EN: Starts the background scan on the destination folder after import completion.
            """
            if count > 0:
                self.status_bar.showMessage(f"{count} photos importées dans {dest_dir}. Lancement de l'indexation...")
                self._start_background_scan([dest_dir])
        dlg.import_completed.connect(on_imported)
        dlg.exec()

    def action_export_as_web_page(self, folder_or_album: Optional[str] = None) -> None:
        """
        FR: Génère une galerie web HTML5 responsive avec lightbox (webexport.fen).
        EN: Generates a responsive HTML5 web gallery with lightbox (webexport.fen).
        """
        paths: List[str] = []
        if folder_or_album and self.thumb_view.items:
            norm_target = folder_or_album.replace("\\", "/").rstrip("/").lower()
            paths = [
                it.path for it in self.thumb_view.items
                if it.folder_path.replace("\\", "/").rstrip("/").lower() == norm_target and it.path
            ]
        if not paths:
            paths = self._get_active_photo_paths()
        if not paths and self.thumb_view.items:
            paths = [it.path for it in self.thumb_view.items if it.path]

        if not paths:
            QMessageBox.information(self, "Page Web", "Aucune photo sélectionnée pour l'exportation.")
            return

        title = folder_or_album or "Galerie Picasa"
        dlg = PicasaWebExportDialog(paths, default_title=title, parent=self)
        dlg.exec()

    action_web_export = action_export_as_web_page


    def _update_photo_ini(self, file_path: str, modify_fn) -> None:
        """
        FR: Modifie et enregistre fidèlement le fichier .picasa.ini associé à une photo,
        et synchronise les tables de la base de données (AGENTS.md §4 bis.3).
        EN: Faithfully modifies and saves the .picasa.ini file associated with a photo,
        and synchronizes the database tables (AGENTS.md §4 bis.3).
        """
        if not file_path or not os.path.exists(file_path):
            return
        if self.db is not None and hasattr(self.db, "update_photo_ini"):
            self.db.update_photo_ini(file_path, modify_fn)
            return
        parent_dir = os.path.dirname(file_path)
        ini_path = os.path.join(parent_dir, ".picasa.ini")
        if not os.path.exists(ini_path):
            alt = os.path.join(parent_dir, "Picasa.ini")
            if os.path.exists(alt):
                ini_path = alt
        doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()
        fname = os.path.basename(file_path)
        modify_fn(doc, fname)
        doc.write_file(ini_path)

    def action_add_file(self) -> None:
        """
        FR: Ajoute un fichier image ou vidéo à la base Picasa et l'affiche (ID_FILE_ADDFILE, Ctrl+O).
        EN: Adds an image or video file to the Picasa database and displays it (ID_FILE_ADDFILE, Ctrl+O).
        Ref: picasa3.exe @ eMenuFile::ID_FILE_ADDFILE (0x0088C3EC)
        """
        fn, _ = QFileDialog.getOpenFileName(
            self,
            "Ajouter un fichier à Picasa",
            "",
            "Médias (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp *.avi *.mp4 *.mov *.wmv *.mpg *.mpeg *.mkv *.m4v)"
        )
        if not fn or not os.path.exists(fn):
            return
        if self.db:
            from picasa_py.scanner.scanner import PicasaDirScanner
            scanner = PicasaDirScanner(self.db)
            added = scanner.index_file(fn)
            if added is not None:
                self.db.save_database()
                self.thumb_view.set_database(self.db)
                self.library_tree.populate_from_database(self.db)
                if hasattr(self, "notifier_popup") and self.notifier_popup:
                    self.notifier_popup.notify_photo_indexed(
                        os.path.dirname(fn),
                        os.path.basename(fn),
                        fn,
                        db_idx=added,
                        show_popup=self.isVisible() or self.isMinimized(),
                    )
        self.action_locate_in_picasa(fn)
        self.status_bar.showMessage(f"Fichier ajouté à Picasa : {os.path.basename(fn)}")

    def action_cut(self) -> None:
        """
        FR: Couper la sélection active (ID_EDIT_CUT).
        EN: Cuts the active selection (ID_EDIT_CUT).
        """
        fw = QApplication.focusWidget()
        if fw and hasattr(fw, "cut"):
            fw.cut()
        elif self.thumb_view.current_folder_filter and self.thumb_view.current_folder_filter.startswith("album:"):
            self.action_remove_from_album()

    def action_paste(self) -> None:
        """
        FR: Coller la sélection ou les effets (ID_EDIT_PASTE).
        EN: Pastes the selection or effects (ID_EDIT_PASTE).
        """
        fw = QApplication.focusWidget()
        if fw and hasattr(fw, "paste"):
            fw.paste()
        elif getattr(self, "_effects_clipboard", None):
            self.action_paste_all_effects()

    def action_view_timeline(self) -> None:
        """
        FR: Bascule le tri chronologique par date et fait défiler vers le haut (ID_VIEW_TIMELINE).
        EN: Switches to chronological date sorting and scrolls to the top (ID_VIEW_TIMELINE).
        """
        self.action_sort_folder_by("date")
        self.thumb_view.scrollbar.set_value(0)
        self.status_bar.showMessage("Vue chronologique activée (tri par date).")

    def action_view_tree(self) -> None:
        """
        FR: Affiche la vue arborescente hiérarchique des dossiers (ID_VIEW_ALL).
        EN: Displays the hierarchical tree view of folders (ID_VIEW_ALL).
        """
        if hasattr(self, "top_bar") and hasattr(self.top_bar, "set_folder_view_mode"):
            self.top_bar.set_folder_view_mode("tree")
        if hasattr(self, "library_tree"):
            if hasattr(self.library_tree, "set_folder_view_mode"):
                self.library_tree.set_folder_view_mode("tree")
            self.library_tree.cat_folders.setExpanded(True)
            self.library_tree.cat_albums.setExpanded(True)
            self.library_tree.cat_people.setExpanded(True)
            self.status_bar.showMessage("Affichage arborescent des dossiers activé.")

    def action_view_flat_folders(self) -> None:
        """
        FR: Affiche la vue à plat des dossiers dans l'arborescence (ID_VIEW_FOLDERS).
        EN: Displays the flat list view of folders in the library tree (ID_VIEW_FOLDERS).
        """
        if hasattr(self, "top_bar") and hasattr(self.top_bar, "set_folder_view_mode"):
            self.top_bar.set_folder_view_mode("flat")
        if hasattr(self, "library_tree"):
            if hasattr(self.library_tree, "set_folder_view_mode"):
                self.library_tree.set_folder_view_mode("flat")
            self.library_tree.cat_folders.setExpanded(True)
            self.status_bar.showMessage("Affichage à plat des dossiers activé.")

    def _on_top_bar_folder_view_mode_changed(self, mode: str) -> None:
        """
        FR: Bascule le mode d'affichage des dossiers depuis la barre supérieure (Liste à plat vs Arbre).
        EN: Switches the folder view mode from the top bar (Flat list vs Tree).
        """
        if mode == "tree":
            self.action_view_tree()
        else:
            self.action_view_flat_folders()

    def _on_section_collage_requested(self, paths: List[str]) -> None:
        """
        FR: Ouvre l'atelier de montage photo pour les photos d'une section (albumheader/create_collage).
        EN: Opens the photo collage workshop for a section's photos (albumheader/create_collage).
        """
        if not paths:
            return
        from picasa_py.ui.collage import PicasaCollageDialog
        dlg = PicasaCollageDialog(paths, parent=self)
        dlg.collage_created.connect(self._on_collage_created)
        dlg.exec()

    def _on_section_movie_requested(self, paths: List[str]) -> None:
        """
        FR: Ouvre le créateur de films pour les photos d'une section (albumheader/create_movie).
        EN: Opens the movie maker for a section's photos (albumheader/create_movie).
        """
        if not paths:
            return
        from picasa_py.ui.movie_maker import PicasaMovieMakerDialog
        dlg = PicasaMovieMakerDialog(paths, face_mode=False, parent=self)
        dlg.movie_created.connect(self._on_movie_created)
        dlg.exec()

    def _on_section_save_requested(self, folder_path: str) -> None:
        """
        FR: Enregistre les retouches en attente du dossier sur le disque (albumheader/save_edits, HEADERPANELTEXT_FR.XML).
        EN: Saves pending edits for the folder to disk (albumheader/save_edits, HEADERPANELTEXT_FR.XML).
        """
        if not folder_path or not os.path.isdir(folder_path):
            return
        norm_folder = os.path.normcase(os.path.normpath(folder_path))
        saved_count = 0
        for it in self.thumb_view.items:
            if it.path:
                it_dir = os.path.normcase(os.path.normpath(os.path.dirname(it.path)))
                if it_dir == norm_folder:
                    try:
                        if self._bake_photo_edits_on_disk(it.path):
                            saved_count += 1
                        elif self.db is not None and hasattr(self.db, "sync_photo_ini_to_db"):
                            self.db.sync_photo_ini_to_db(it.path)
                    except Exception:
                        pass
        if self.db is not None and hasattr(self.db, "schedule_save_thumbnails"):
            self.db.schedule_save_thumbnails(1500)
        self.thumb_view._pixmap_cache.clear()
        self.thumb_view.update()
        folder_name = os.path.basename(folder_path.rstrip(chr(92) + "/"))
        self.status_bar.showMessage(f"Modifications enregistrées pour le dossier : {folder_name}")

    def _on_photos_dropped_on_album(self, album_token: str, photo_paths: List[str]) -> None:
        """
        FR: Associe les photos déposées par glisser-déposer à l'album cible.
        EN: Associates photos dropped via drag-and-drop with the target album.
        """
        if not album_token or not photo_paths:
            return
        self.action_add_photos_to_album(photo_paths, album_token)

    def _on_photos_dropped_on_folder(self, dest_folder: str, photo_paths: List[str]) -> None:
        """
        FR: Déplace les photos déposées par glisser-déposer vers le dossier cible en migrant
        leurs sections `.picasa.ini`, `.picasaoriginals/` et `thumbindex.db`.
        EN: Moves photos dropped via drag-and-drop to the target folder, migrating their
        `.picasa.ini` sections, `.picasaoriginals/`, and `thumbindex.db`.
        Ref: picasa3.exe @ 0x0068AC80
        """
        if not dest_folder or not os.path.isdir(dest_folder) or not photo_paths:
            return
        import shutil
        moved = 0
        for p in photo_paths:
            if not p or not os.path.exists(p):
                continue
            if os.path.normcase(os.path.abspath(os.path.dirname(p))) == os.path.normcase(os.path.abspath(dest_folder)):
                continue
            try:
                dest_p = os.path.join(dest_folder, os.path.basename(p))
                if not os.path.exists(dest_p):
                    if self.db is not None and hasattr(self.db, "move_photo"):
                        self.db.move_photo(p, dest_folder)
                    else:
                        shutil.move(p, dest_p)
                    for it in self.thumb_view.items:
                        if it.path == p:
                            it.path = dest_p
                            it.folder_path = dest_folder
                    moved += 1
            except Exception:
                pass
        if moved > 0:
            self.notify_folders_changed()
            self.status_bar.showMessage(f"{moved} photo(s) déplacée(s) vers {os.path.basename(dest_folder.rstrip(chr(92) + '/'))}.")

    def _on_photos_dropped_on_starred(self, photo_paths: List[str]) -> None:
        """
        FR: Ajoute une étoile aux photos déposées sur « Photos favorites ».
        EN: Adds a star to photos dropped onto "Starred Photos".
        """
        if not photo_paths:
            return
        target_set = set(photo_paths)
        for p in photo_paths:
            self._update_photo_ini(p, lambda doc, fname: doc.set_starred(fname, True))
        for it in self.thumb_view.items:
            if it.path in target_set:
                it.starred = True
        self.thumb_view.update()
        if hasattr(self, "library_tree"):
            self.library_tree.refresh_albums()
        self.status_bar.showMessage(f"{len(photo_paths)} photo(s) ajoutée(s) aux favoris.")

    def action_toggle_two_up(self) -> None:
        """
        FR: Bascule l'affichage côte à côte Avant/Après dans l'éditeur (TwoUpView / two_up).
        EN: Toggles the side-by-side Before/After comparison view in the editor (TwoUpView / two_up).
        Ref: picasa3.exe @ editoneup::TwoUpView (0x0088C3EC)
        """
        if self.stack.currentWidget() != self.one_up_view:
            paths = self._get_active_photo_paths()
            if paths:
                self.action_view_and_edit(paths[0])
        if hasattr(self.one_up_view, "canvas"):
            active = self.one_up_view.canvas.toggle_two_up()
            state_lbl = "activé" if active else "désactivé"
            self.status_bar.showMessage(f"Affichage côte à côte A/B (TwoUpView) {state_lbl}.")

    def action_export_kml(self) -> None:
        """
        FR: Exporte les photos géolocalisées vers un fichier Google Earth (.kml) (ID_GEOTAG_EXPORT_KML).
        EN: Exports geotagged photos to a Google Earth (.kml) file (ID_GEOTAG_EXPORT_KML).
        Ref: picasa3.exe @ 0x0088C3EC (ID_GEOTAG_EXPORT_KML, Google Earth Geotagging)
        """
        paths = self._get_active_photo_paths()
        if not paths and self.thumb_view.items:
            paths = [it.path for it in self.thumb_view.items if it.path]
        if not paths:
            QMessageBox.information(self, "Google Earth (KML)", "Aucune photo sélectionnée.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter vers un fichier Google Earth (.kml)",
            "PicasaGeotags.kml",
            "Fichier Google Earth KML (*.kml)"
        )
        if not save_path:
            return

        placemarks: List[str] = []
        for p in paths:
            if not p or not os.path.exists(p):
                continue
            ini_p = os.path.join(os.path.dirname(p), ".picasa.ini")
            lat, lon = None, None
            if os.path.exists(ini_p):
                try:
                    doc = self.db.get_parsed_ini(ini_p) if self.db else PicasaIniParser.parse_file(ini_p)
                    if doc:
                        sec = doc.get_section(os.path.basename(p))
                        if sec and sec.get("geotag"):
                            parts = [x.strip() for x in sec.get("geotag", "").split(",")]
                            if len(parts) >= 2:
                                lat, lon = float(parts[0]), float(parts[1])
                except Exception:
                    pass
            if lat is not None and lon is not None:
                fname = os.path.basename(p).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                placemarks.append(
                    f"    <Placemark>\n"
                    f"      <name>{fname}</name>\n"
                    f"      <Point><coordinates>{lon:.6f},{lat:.6f},0</coordinates></Point>\n"
                    f"    </Placemark>"
                )

        kml_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
            '  <Document>\n'
            '    <name>Photos Picasa</name>\n'
            + "\n".join(placemarks) + "\n"
            '  </Document>\n'
            '</kml>\n'
        )
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(kml_content)
            self.status_bar.showMessage(f"Fichier KML exporté ({len(placemarks)} géolocalisation(s)) : {os.path.basename(save_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur KML", f"Impossible d'écrire le fichier KML : {e}")

    def _get_collection_password_hash(self, collection_name: str = "Hidden Folders") -> str:
        """
        FR: Récupère le hachage MD5 du mot de passe d'une collection depuis `catdata_info.pmp`
        (ou `.picasa.ini` `[Picasa] password=` si `collection_name` est un chemin de dossier).
        EN: Retrieves the MD5 password hash of a collection from `catdata_info.pmp`
        (or `.picasa.ini` `[Picasa] password=` if `collection_name` is a folder path).
        Ref: picasa3.exe @ 0x004AB69D, 0x005EB989, 0x005EC44A (catdata_info 'info')
        """
        if collection_name and os.path.isdir(collection_name):
            ini_p = os.path.join(collection_name, ".picasa.ini")
            if os.path.exists(ini_p):
                try:
                    doc = PicasaIniParser.parse_file(ini_p)
                    sec = doc.get_section("Picasa")
                    if sec and sec.get("password"):
                        return sec.get("password", "").strip()
                except Exception:
                    pass
        if self.db is not None and hasattr(self.db, "pmps"):
            cat_names = self.db.pmps.get("catdata_name")
            cat_infos = self.db.pmps.get("catdata_info")
            if cat_names and cat_infos:
                target_low = (collection_name or "Hidden Folders").strip().lower()
                if target_low in ("dossiers masqués", "hidden folders"):
                    target_low = "hidden folders"
                for idx, cname in enumerate(cat_names.records):
                    if str(cname or "").strip().lower() == target_low and idx < len(cat_infos.records):
                        return str(cat_infos.records[idx] or "").strip()
            pwd_map = getattr(self.db, "_collection_passwords", None)
            if isinstance(pwd_map, dict):
                return str(pwd_map.get(collection_name, "") or pwd_map.get("Hidden Folders", "")).strip()
        return ""

    def _set_collection_password_hash(self, collection_name: str, pwd_hash: str) -> None:
        """
        FR: Enregistre ou efface le hachage MD5 du mot de passe d'une collection dans `catdata_info.pmp`
        et `.picasa.ini` si un dossier est ciblé.
        EN: Stores or clears a collection's MD5 password hash in `catdata_info.pmp`
        and `.picasa.ini` if a folder path is targeted.
        Ref: picasa3.exe @ 0x005EBA5E, 0x005EBC52 (SetCatData 'info')
        """
        if collection_name and os.path.isdir(collection_name):
            ini_p = os.path.join(collection_name, ".picasa.ini")
            doc = PicasaIniParser.parse_file(ini_p) if os.path.exists(ini_p) else PicasaIniDocument()
            sec = doc.get_or_create_section("Picasa")
            if pwd_hash:
                sec.set("password", pwd_hash)
            else:
                sec.remove("password")
            doc.write_file(ini_p)
        if self.db is not None:
            if not hasattr(self.db, "_collection_passwords") or not isinstance(self.db._collection_passwords, dict):
                self.db._collection_passwords = {}
            norm_col = "Hidden Folders" if (collection_name or "").strip().lower() in ("", "dossiers masqués", "hidden folders") else collection_name
            if pwd_hash:
                self.db._collection_passwords[norm_col] = pwd_hash
            else:
                self.db._collection_passwords.pop(norm_col, None)
            if hasattr(self.db, "pmps"):
                from picasa_py.db.pmp import PmpFile, PmpType
                from picasa_py.db.database import DEFAULT_CATDATA_RECORDS
                cat_names = self.db.pmps.get("catdata_name")
                if cat_names is None:
                    cat_names = PmpFile(
                        pmp_type=PmpType.STRING,
                        records=list(DEFAULT_CATDATA_RECORDS["catdata_name"]),
                        dirty=True,
                    )
                    self.db.pmps["catdata_name"] = cat_names
                if "catdata_info" not in self.db.pmps:
                    self.db.pmps["catdata_info"] = PmpFile(
                        pmp_type=PmpType.STRING,
                        records=["" for _ in range(len(cat_names.records))],
                        dirty=True,
                    )
                cat_infos = self.db.pmps["catdata_info"]
                while len(cat_infos.records) < len(cat_names.records):
                    cat_infos.records.append("")
                for idx, cname in enumerate(cat_names.records):
                    if str(cname or "").strip().lower() == norm_col.lower():
                        cat_infos.records[idx] = pwd_hash
                        cat_infos.dirty = True
                        break
                db3_dir = getattr(self.db, "db3_dir", None)
                if db3_dir and os.path.isdir(str(db3_dir)):
                    for stem_c in ("catdata_name", "catdata_info", "catdata_state"):
                        pmp_c = self.db.pmps.get(stem_c)
                        if pmp_c is not None and getattr(pmp_c, "dirty", False):
                            try:
                                (Path(db3_dir) / f"{stem_c}.pmp").write_bytes(pmp_c.to_bytes())
                                pmp_c.dirty = False
                            except Exception:
                                pass

    def _verify_collection_password_prompt(self, collection_name: str = "Hidden Folders") -> bool:
        """
        FR: Vérifie le mot de passe d'une collection protégée avant de l'ouvrir (`CAlbumState::passprompt` / `CThumbUI::PassEntryPrompt`).
        EN: Verifies a protected collection's password before opening it (`CAlbumState::passprompt` / `CThumbUI::PassEntryPrompt`).
        Ref: picasa3.exe @ 0x004AB650 - 0x004AB8F1, 0x005EC440 - 0x005EC80E
        """
        norm_col = (
            "Hidden Folders"
            if (collection_name or "").strip().lower() in ("", "dossiers masqués", "hidden folders")
            else collection_name
        )
        expected_hash = self._get_collection_password_hash(norm_col)
        if not expected_hash or norm_col in self._unlocked_collections:
            return True
        from PySide6.QtWidgets import QLineEdit
        prompt_txt = self.res_mgr.get_stringres(
            "CThumbUI::PassEntryPrompt",
            "Entrez un mot de passe pour ouvrir cette collection.",
        )
        title_txt = self.res_mgr.get_stringres("CThumbUI::PassEntryTitle", "Saisie du mot de passe")
        pwd, ok = QInputDialog.getText(self, title_txt, prompt_txt, QLineEdit.EchoMode.Password)
        if not ok:
            return False
        import hashlib
        entered_hash = hashlib.md5(pwd.strip().encode("utf-8")).hexdigest()
        if entered_hash.lower() == expected_hash.lower():
            self._unlocked_collections.add(norm_col)
            return True
        QMessageBox.warning(self, title_txt, "Mot de passe incorrect.")
        return False

    def action_password_protect_collection(self, folder_path: Optional[str] = None) -> None:
        """
        FR: Définit, modifie ou retire la protection par mot de passe d'une collection (`Collection::ID_COL_PASSWORD` 0x9D56 -> `FUN_005EB910`).
        Demande le mot de passe (`CThumbUI::PassEntryOpenPrompt`) puis sa confirmation (`CThumbUI::PassVerifyPrompt`),
        ou supprime le mot de passe s'il est laissé vide (`CThumbUI::PassEntryNoPass`).
        EN: Sets, changes, or removes password protection for a collection (`Collection::ID_COL_PASSWORD` 0x9D56 -> `FUN_005EB910`).
        Prompts for the password (`CThumbUI::PassEntryOpenPrompt`) and confirmation (`CThumbUI::PassVerifyPrompt`),
        or removes the password if left blank (`CThumbUI::PassEntryNoPass`).
        Ref: picasa3.exe @ 0x005EB910 - 0x005EBC99, 0x00732715 (Collection::ID_COL_PASSWORD)
        """
        raw_target = folder_path if isinstance(folder_path, str) and folder_path else (self.thumb_view.current_folder_filter or "Hidden Folders")
        target = (
            "Hidden Folders"
            if (raw_target or "").strip().lower() in ("", "dossiers masqués", "hidden folders")
            else raw_target
        )
        if not self._verify_collection_password_prompt(target):
            return
        from PySide6.QtWidgets import QLineEdit
        open_prompt = self.res_mgr.get_stringres(
            "CThumbUI::PassEntryOpenPrompt",
            "Entrez le mot de passe à utiliser pour cette collection.",
        )
        title_txt = self.res_mgr.get_stringres("CThumbUI::PassEntryTitle", "Saisie du mot de passe")
        pwd, ok = QInputDialog.getText(self, title_txt, open_prompt, QLineEdit.EchoMode.Password)
        if not ok:
            return
        if not pwd.strip():
            # Ref: picasa3.exe @ 0x005EBA54 - 0x005EBAAE (CThumbUI::PassEntryNoPass)
            self._set_collection_password_hash(target, "")
            self.library_tree._update_hidden_folders_category()
            self.thumb_view._apply_current_filters(reset_scroll=False)
            no_pass_msg = self.res_mgr.get_stringres("CThumbUI::PassEntryNoPass", "Aucun mot de passe n'est défini.")
            self.status_bar.showMessage(no_pass_msg)
            return

        # Ref: picasa3.exe @ 0x005EBABF - 0x005EBC05 (CThumbUI::PassVerifyPrompt & PassVerifyWrong)
        verify_prompt = self.res_mgr.get_stringres("CThumbUI::PassVerifyPrompt", "Veuillez confirmer votre mot de passe.")
        verify_title = self.res_mgr.get_stringres("CThumbUI::PassVerifyTitle", "Vérification du mot de passe")
        pwd2, ok2 = QInputDialog.getText(self, verify_title, verify_prompt, QLineEdit.EchoMode.Password)
        if not ok2:
            return
        if pwd.strip() != pwd2.strip():
            wrong_msg = self.res_mgr.get_stringres("CThumbUI::PassVerifyWrong", "Les mots de passe ne correspondent pas.")
            QMessageBox.warning(self, verify_title, wrong_msg)
            return

        import hashlib
        digest = hashlib.md5(pwd.strip().encode("utf-8")).hexdigest()
        self._set_collection_password_hash(target, digest)
        self._unlocked_collections.add(target)
        self.library_tree._update_hidden_folders_category()
        self.thumb_view._apply_current_filters(reset_scroll=False)
        self.status_bar.showMessage("Collection protégée par mot de passe.")

    def action_toggle_show_hidden(self, checked: Optional[bool] = None) -> None:
        """
        FR: Bascule l'affichage des photos masquées et de la collection « Dossiers masqués »
        (`eMenuView::ID_VIEW_SHOWHIDDEN`, cmd `0x9C9E` -> `FUN_005C9300` & `FUN_005C90F0`).
        Dans `picasa3.exe @ 0x005C9300`, le clic sur `Affichage > Photos masquées` ne demande
        jamais de mot de passe : il affiche immédiatement les photos `]hidden` et rend visible
        l'en-tête « Dossiers masqués » (replié s'il est protégé par mot de passe). Le mot de passe
        n'est demandé que lorsque l'utilisateur déplie ou clique sur « Dossiers masqués » (`0x004AB9A0 -> 0x004AB650`).
        EN: Toggles display of hidden pictures and the "Hidden Folders" collection
        (`eMenuView::ID_VIEW_SHOWHIDDEN`, cmd `0x9C9E` -> `FUN_005C9300` & `FUN_005C90F0`).
        Ref: picasa3.exe @ 0x005C9300 - 0x005C93C1, 0x005C90F0 - 0x005C9155, 0x00660C80, 0x004AB9A0
        """
        new_state = (not self.show_hidden_pictures) if checked is None else bool(checked)
        self.show_hidden_pictures = new_state
        if not self.show_hidden_pictures:
            self._unlocked_collections.discard("Hidden Folders")
        if hasattr(self, "menu_builder") and self.menu_builder.act_show_hidden is not None:
            self.menu_builder.act_show_hidden.blockSignals(True)
            self.menu_builder.act_show_hidden.setChecked(self.show_hidden_pictures)
            self.menu_builder.act_show_hidden.blockSignals(False)
        self.thumb_view.show_hidden = self.show_hidden_pictures
        self.library_tree.set_show_hidden(self.show_hidden_pictures)
        self.thumb_view._apply_current_filters(reset_scroll=False)
        self.status_bar.showMessage(
            "Photos masquées affichées." if self.show_hidden_pictures else "Photos masquées masquées."
        )

    def _set_pictures_hidden_state(self, hide: bool, photo_paths: Optional[List[str]] = None) -> None:
        """
        FR: Masque (`hide=True`, cmd `0x9CA4`) ou réaffiche (`hide=False`, cmd `0x9CA5`) les photos sélectionnées
        en écrivant `hidden=yes` dans `.picasa.ini`, en mettant à jour `imagedata_hidden.pmp` et le jeton `]hidden`
        dans `wordhash.dat` (`FUN_005E7D90`).
        EN: Hides (`hide=True`, cmd `0x9CA4`) or unhides (`hide=False`, cmd `0x9CA5`) selected photos
        by writing `hidden=yes` in `.picasa.ini`, updating `imagedata_hidden.pmp`, and indexing `]hidden`
        in `wordhash.dat` (`FUN_005E7D90`).
        Ref: picasa3.exe @ 0x005E7D90 - 0x005E8060, 0x00458D50, 0x0078CCFE
        """
        paths = photo_paths if isinstance(photo_paths, list) and photo_paths else self._get_active_photo_paths()
        if not paths:
            return
        norm_targets = {p.replace("\\", "/").lower() for p in paths if p}
        docs_by_ini: Dict[str, PicasaIniDocument] = {}
        updated_count = 0

        for p in paths:
            if not p:
                continue
            folder_dir = os.path.dirname(p)
            fname = os.path.basename(p)
            if folder_dir and os.path.isdir(folder_dir):
                ini_p = os.path.join(folder_dir, ".picasa.ini")
                if ini_p not in docs_by_ini:
                    docs_by_ini[ini_p] = PicasaIniParser.parse_file(ini_p) if os.path.exists(ini_p) else PicasaIniDocument()
                doc = docs_by_ini[ini_p]
                if hide:
                    sec = doc.get_or_create_section(fname)
                    sec.set("hidden", "yes")
                else:
                    sec = doc.get_section(fname)
                    if sec is not None:
                        sec.remove("hidden")
            updated_count += 1

        for ini_p, doc in docs_by_ini.items():
            try:
                doc.write_file(ini_p)
            except Exception:
                pass

        for it in self.thumb_view.items:
            if it.path and it.path.replace("\\", "/").lower() in norm_targets:
                it.hidden = hide
                if self.db is not None and it.index >= 0:
                    if "imagedata_hidden" in self.db.pmps and it.index < len(self.db.pmps["imagedata_hidden"].records):
                        self.db.pmps["imagedata_hidden"].records[it.index] = 1 if hide else 0
                        self.db.pmps["imagedata_hidden"].dirty = True
                    if getattr(self.db, "wordhash", None) is not None:
                        if hide:
                            self.db.wordhash.add_word("]hidden", it.index)
                        elif hasattr(self.db.wordhash, "remove_word"):
                            self.db.wordhash.remove_word("]hidden", it.index)

        self.thumb_view._apply_current_filters(reset_scroll=False)
        self.status_bar.showMessage(
            f"{updated_count} photo(s) masquée(s)." if hide else f"{updated_count} photo(s) affichée(s)."
        )

    def action_hide_pictures(self, photo_paths: Optional[List[str]] = None) -> None:
        """
        FR: Masque les photos sélectionnées (`eMenuPicture::ID_PICTURE_HIDE`, cmd `0x9CA4` -> `FUN_005E7D90(1)`).
        EN: Hides the selected pictures (`eMenuPicture::ID_PICTURE_HIDE`, cmd `0x9CA4` -> `FUN_005E7D90(1)`).
        Ref: picasa3.exe @ 0x005CBD52, 0x005E7D90
        """
        self._set_pictures_hidden_state(True, photo_paths)

    def action_unhide_pictures(self, photo_paths: Optional[List[str]] = None) -> None:
        """
        FR: Réaffiche les photos masquées sélectionnées (`eMenuPicture::ID_PICTURE_UNHIDE`, cmd `0x9CA5` -> `FUN_005E7D90(0)`).
        EN: Unhides the selected hidden pictures (`eMenuPicture::ID_PICTURE_UNHIDE`, cmd `0x9CA5` -> `FUN_005E7D90(0)`).
        Ref: picasa3.exe @ 0x005CBD5F, 0x005E7D90
        """
        self._set_pictures_hidden_state(False, photo_paths)

    def _set_folder_hidden_state(self, hide: bool, folder_path: Optional[str] = None) -> None:
        """
        FR: Déplace un dossier vers la collection « Dossiers masqués » (`hide=True`, cmd `0x9C72`, `cat=7`)
        ou vers « Dossiers sur le disque » (`hide=False`, cmd `0x9CD0`, `cat=2`) conformément à `FUN_005EE2A0` & `FUN_00445B80`.
        Écrit également `P2category=Hidden Folders` (ou `P2category=Folders on Disk`) dans `[Picasa]` du `.picasa.ini` (`0x00446012`).
        Si `hide=True` et que « Dossiers masqués » n'a pas encore de mot de passe, propose d'en ajouter un
        (`IDS_PROMPT_HIDDEN_PWD_MESSAGE` @ `0x005EE444`).
        EN: Moves a folder into the "Hidden Folders" collection (`hide=True`, cmd `0x9C72`, `cat=7`)
        or back to "Folders on Disk" (`hide=False`, cmd `0x9CD0`, `cat=2`) per `FUN_005EE2A0` & `FUN_00445B80`.
        Ref: picasa3.exe @ 0x005EE2A0 - 0x005EE57F, 0x00445B80 - 0x00446050
        """
        target = folder_path if isinstance(folder_path, str) and folder_path else self.thumb_view.current_folder_filter
        if not target or not os.path.isdir(target):
            return
        norm_target = target.replace("\\", "/").rstrip("/").lower()

        # Ref: picasa3.exe @ 0x00446012 (Écrit P2category dans [Picasa] de .picasa.ini)
        try:
            ini_p = os.path.join(target, ".picasa.ini")
            doc = PicasaIniParser.parse_file(ini_p) if os.path.exists(ini_p) else PicasaIniDocument()
            sec = doc.get_or_create_section("Picasa")
            sec.set("P2category", "Hidden Folders" if hide else "Folders on Disk")
            doc.write_file(ini_p)
        except Exception:
            pass

        if self.db is not None:
            if not hasattr(self.db, "_hidden_folders") or not isinstance(self.db._hidden_folders, set):
                self.db._hidden_folders = set()
            if hide:
                self.db._hidden_folders.add(norm_target)
            else:
                self.db._hidden_folders.discard(norm_target)

            if hasattr(self.db, "invalidate_ini_cache"):
                self.db.invalidate_ini_cache(os.path.join(target, ".picasa.ini"))
            if hasattr(self.db, "ensure_folder_album_row"):
                self.db.ensure_folder_album_row(target)
            ad_cats = self.db.pmps.get("albumdata_category")
            ad_files = self.db.pmps.get("albumdata_filename")
            if ad_cats and ad_files:
                for i, fp in enumerate(ad_files.records):
                    if str(fp or "").replace("\\", "/").rstrip("/").lower() == norm_target and i < len(ad_cats.records):
                        ad_cats.records[i] = 7 if hide else 2
                        ad_cats.dirty = True
            db3_dir = getattr(self.db, "db3_dir", None)
            if db3_dir and os.path.isdir(str(db3_dir)):
                for stem_a, pmp_a in self.db.pmps.items():
                    if stem_a.startswith("albumdata_") and getattr(pmp_a, "dirty", False):
                        try:
                            (Path(db3_dir) / f"{stem_a}.pmp").write_bytes(pmp_a.to_bytes())
                            pmp_a.dirty = False
                        except Exception:
                            pass

        # Ref: picasa3.exe @ 0x005EE373 - 0x005EE4E6 (IDS_PROMPT_HIDDEN_PWD_MESSAGE -> call 0x005EB910)
        if hide and not self._get_collection_password_hash("Hidden Folders") and not getattr(self, "_do_not_confirm_hidden_pwd", False):
            msg = self.res_mgr.get_stringres(
                "IDS_WARN_NO_HIDDEN_PWD",
                'Actuellement, la collection "Dossiers masqués" n\'est pas protégée par un mot de passe. Voulez-vous ajouter un mot de passe maintenant ?',
            )
            title = self.res_mgr.get_stringres("IDS_HIDDEN", "Dossiers masqués")
            ans = QMessageBox.question(
                self,
                title,
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                self.action_password_protect_collection("Hidden Folders")

        # Ref: picasa3.exe @ 0x005EE522 (Si un mot de passe existe sur Hidden Folders, replie la catégorie state=0)
        if hide and self._get_collection_password_hash("Hidden Folders"):
            self._unlocked_collections.discard("Hidden Folders")
            if self.db is not None and hasattr(self.db, "pmps") and "catdata_state" in self.db.pmps:
                cat_states = self.db.pmps["catdata_state"]
                if len(cat_states.records) > 7:
                    cat_states.records[7] = 0
                    cat_states.dirty = True

        self.library_tree.refresh_folders()
        self.thumb_view._apply_current_filters(reset_scroll=False)
        self.status_bar.showMessage(
            f"Dossier déplacé vers « Dossiers masqués » : {os.path.basename(target.rstrip(chr(92) + '/'))}"
            if hide
            else f"Dossier rétabli dans « Dossiers sur le disque » : {os.path.basename(target.rstrip(chr(92) + '/'))}"
        )

    def action_hide_folder(self, folder_path: Optional[str] = None) -> None:
        """
        FR: Masque le dossier entier en le déplaçant dans « Dossiers masqués » (`Folder::ID_HIDEENTIREALBUM`, cmd `0x9C72`).
        EN: Hides the entire folder by moving it to "Hidden Folders" (`Folder::ID_HIDEENTIREALBUM`, cmd `0x9C72`).
        Ref: picasa3.exe @ 0x005CC054, 0x005EE2A0
        """
        self._set_folder_hidden_state(True, folder_path)

    def action_unhide_folder(self, folder_path: Optional[str] = None) -> None:
        """
        FR: Réaffiche le dossier masqué dans « Dossiers sur le disque » (`Folder::ID_UNHIDEENTIREALBUM`, cmd `0x9CD0`).
        EN: Unhides the hidden folder back to "Folders on Disk" (`Folder::ID_UNHIDEENTIREALBUM`, cmd `0x9CD0`).
        Ref: picasa3.exe @ 0x005CC069, 0x005EE2A0
        """
        self._set_folder_hidden_state(False, folder_path)

    def action_backup(self) -> None:
        """
        FR: Sauvegarde les photos et fichiers .picasa.ini sélectionnés vers un dossier ou support de sauvegarde (ID_TOOLS_BACKUP).
        EN: Backs up selected photos and .picasa.ini files to a destination folder or backup medium (ID_TOOLS_BACKUP).
        Ref: picasa3.exe @ 0x0088C3EC (ID_TOOLS_BACKUP, backup.fen / CD/DVD Backup Burn)
        """
        dest_dir = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination pour la sauvegarde PicasaBackup")
        if not dest_dir:
            return
        paths = self._get_active_photo_paths()
        if not paths and self.thumb_view.items:
            paths = [it.path for it in self.thumb_view.items if it.path]
        if not paths:
            QMessageBox.information(self, "Sauvegarde", "Aucune photo à sauvegarder.")
            return

        import shutil
        backup_root = os.path.join(dest_dir, "PicasaBackup")
        os.makedirs(backup_root, exist_ok=True)
        copied = 0
        copied_inis: Set[str] = set()
        for p in paths:
            if not p or not os.path.exists(p):
                continue
            try:
                folder_name = os.path.basename(os.path.dirname(p)) or "Photos"
                target_sub = os.path.join(backup_root, folder_name)
                os.makedirs(target_sub, exist_ok=True)
                shutil.copy2(p, os.path.join(target_sub, os.path.basename(p)))
                copied += 1
                ini_src = os.path.join(os.path.dirname(p), ".picasa.ini")
                if os.path.exists(ini_src) and ini_src not in copied_inis:
                    shutil.copy2(ini_src, os.path.join(target_sub, ".picasa.ini"))
                    copied_inis.add(ini_src)
            except Exception:
                pass
        self.status_bar.showMessage(f"Sauvegarde terminée : {copied} fichier(s) copié(s) dans {backup_root}")
        QMessageBox.information(
            self,
            "Sauvegarde Picasa terminée",
            f"{copied} photo(s) et leurs métadonnées .picasa.ini ont été sauvegardées dans :\n{backup_root}"
        )

    def action_toggle_drawer_panel(self, panel_name: str) -> None:
        """
        FR: Bascule l'affichage d'un des volets du panneau droit (people, places, tags, properties).
        EN: Toggles the display of one of the right drawer panels (people, places, tags, properties).
        """
        self._on_tray_panel_toggled(panel_name)

    def action_auto_redeye(self) -> None:
        """
        FR: Détection et correction automatique des yeux rouges (ID_PICTURE_AUTO_REDEYE).
        EN: Automatic red-eye detection and correction (ID_PICTURE_AUTO_REDEYE).
        """
        if self.stack.currentWidget() == self.one_up_view:
            self.one_up_view._on_apply_effect("redeye", {})
            self.status_bar.showMessage("Correction automatique des yeux rouges appliquée.")
        else:
            paths = self._get_active_photo_paths()
            if paths:
                self.action_view_and_edit(paths[0])
                self.one_up_view._on_apply_effect("redeye", {})

    def action_move_folder(self, folder_path: str) -> None:
        """
        FR: Déplace un dossier vers un nouvel emplacement sur le disque (ID_MOVEFOLDER).
        EN: Moves a folder to a new location on disk (ID_MOVEFOLDER).
        Ref: picasa3.exe @ Folder::ID_MOVEFOLDER (0x00CAE2C4)
        """
        if not os.path.exists(folder_path):
            return
        dest_parent = QFileDialog.getExistingDirectory(
            self, "Choisir le dossier de destination pour déplacer ce dossier", os.path.dirname(folder_path)
        )
        if dest_parent:
            import shutil
            fname = os.path.basename(folder_path.rstrip("\\/"))
            new_path = os.path.join(dest_parent, fname)
            if os.path.exists(new_path):
                QMessageBox.warning(self, "Déplacer le dossier", f"Un dossier nommé « {fname} » existe déjà dans la destination.")
                return
            try:
                shutil.move(folder_path, new_path)
                self.notify_folders_changed()
                self.thumb_view.filter_by_folder(new_path)
                self.status_bar.showMessage(f"Dossier déplacé vers {new_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur de déplacement", f"Impossible de déplacer le dossier : {e}")

    def action_move_photos_to_folder(self, photo_paths: Optional[List[str]] = None) -> None:
        """
        FR: Déplace les photos sélectionnées vers un nouveau dossier (FolderPhoto::ID_ALBUM_NEW)
        en migrant leurs sections `.picasa.ini`, `.picasaoriginals/` et `thumbindex.db`.
        EN: Moves the selected photos to a new folder (FolderPhoto::ID_ALBUM_NEW), migrating their
        `.picasa.ini` sections, `.picasaoriginals/`, and `thumbindex.db`.
        Ref: picasa3.exe @ 0x00CADC5C, 0x00CADC74, 0x0068AC80
        """
        if not photo_paths:
            photo_paths = self._get_active_photo_paths()
        if not photo_paths:
            return
        dest_dir = QFileDialog.getExistingDirectory(
            self, "Sélectionnez le dossier de destination", os.path.dirname(photo_paths[0])
        )
        if dest_dir:
            import shutil
            moved = 0
            for p in photo_paths:
                try:
                    dest_p = os.path.join(dest_dir, os.path.basename(p))
                    if self.db is not None and hasattr(self.db, "move_photo"):
                        self.db.move_photo(p, dest_dir)
                    else:
                        shutil.move(p, dest_p)
                    for it in self.thumb_view.items:
                        if it.path == p:
                            it.path = dest_p
                            it.folder_path = dest_dir
                    moved += 1
                except Exception:
                    pass
            self.notify_folders_changed()
            self.thumb_view.filter_by_folder(dest_dir)
            self.status_bar.showMessage(f"{moved} photo(s) déplacée(s) vers {dest_dir}")

    def action_split_folder_here(self, photo_path: str) -> None:
        """
        FR: Scinde le dossier en deux à partir de cette photo (FolderPhoto::ID_PICTURE_SPLITALBUMHERE)
        en migrant les sections `.picasa.ini`, `.picasaoriginals/` et `thumbindex.db`.
        EN: Splits the folder into two starting from this photo (FolderPhoto::ID_PICTURE_SPLITALBUMHERE),
        migrating `.picasa.ini` sections, `.picasaoriginals/`, and `thumbindex.db`.
        Ref: picasa3.exe @ 0x00CADC90, 0x00CADCA8, 0x0068AC80
        """
        if not photo_path or not os.path.exists(photo_path):
            return
        parent_dir = os.path.dirname(photo_path)
        cur_folder_name = os.path.basename(parent_dir)
        new_name, ok = QInputDialog.getText(
            self, "Scinder le dossier",
            f"Nom du nouveau dossier pour les photos à partir de {os.path.basename(photo_path)} :",
            text=f"{cur_folder_name} (suite)"
        )
        if ok and new_name.strip():
            new_dir = os.path.join(os.path.dirname(parent_dir), new_name.strip())
            os.makedirs(new_dir, exist_ok=True)
            found = False
            to_move = []
            for it in self.thumb_view.items:
                if it.path == photo_path:
                    found = True
                if found and it.folder_path == parent_dir and it.path:
                    to_move.append(it.path)
            import shutil
            for p in to_move:
                try:
                    dest_p = os.path.join(new_dir, os.path.basename(p))
                    if self.db is not None and hasattr(self.db, "move_photo"):
                        self.db.move_photo(p, new_dir)
                    else:
                        shutil.move(p, dest_p)
                    for it in self.thumb_view.items:
                        if it.path == p:
                            it.path = dest_p
                            it.folder_path = new_dir
                except Exception:
                    pass
            self.notify_folders_changed()
            self.thumb_view.filter_by_folder(new_dir)
            self.status_bar.showMessage(f"Dossier scindé : {len(to_move)} photo(s) déplacée(s) dans « {new_name.strip()} ».")

    def action_remove_from_person(self, contact_id: str, photo_paths: List[str], face_rect: Optional[Any] = None) -> None:
        """
        FR: Retire le visage de l'album de la personne sans supprimer la photo du disque.
        EN: Removes the face from the person's album without deleting the photo from disk.
        Ref: picasa3.exe @ PplAlbumPhoto::ID_FILE_DELETEFROMDISK (0x00CAF1B8, 0x00CAF1E0)
        """
        if not self.db or not self.db.face_manager:
            return
        from picasa_py.faces.face_manager import _face_overlap
        fm = self.db.face_manager
        person = fm.get_person(contact_id)
        pname = person.name if person else "cette personne"

        rep = QMessageBox.question(
            self,
            "Supprimer de l'album de la personne",
            f"Voulez-vous retirer ce visage de « {pname} » ?\n(La photo originale sur le disque ne sera pas supprimée)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if rep != QMessageBox.StandardButton.Yes:
            return

        for p in photo_paths:
            faces = fm.photo_to_faces.get(p, [])
            for fr in list(faces):
                if fr.contact_id.lower() == contact_id.lower():
                    def _remove_face(doc: PicasaIniDocument, fname: str) -> None:
                        """
                        FR: Retire les entrées de visage associées au contact dans la section INI.
                        EN: Removes the face entries associated with the contact in the INI section.
                        """
                        f_list = doc.get_faces(fname)
                        f_list = [f for f in f_list if f.contact_id.lower() != contact_id.lower()]
                        doc.set_faces(fname, f_list)
                    self._update_photo_ini(p, _remove_face)

                    if contact_id.lower() in fm.people:
                        cl = fm.people[contact_id.lower()]
                        cl.photo_paths = [pth for pth in cl.photo_paths if pth != p]
                        for idx_k in list(cl.face_rects_by_photo.keys()):
                            cl.face_rects_by_photo[idx_k] = [
                                f for f in cl.face_rects_by_photo[idx_k] if _face_overlap(f, fr) < 0.5
                            ]
                    fr.contact_id = ""
                    fr.contact_name = None
                    fm.unnamed_faces.append((None, p, fr))

        fm.notify_people_changed()
        if hasattr(self, "library_tree"):
            self.library_tree.refresh_people()
        if person:
            self.thumb_view.filter_by_person(contact_id, person.name, person.photo_indices)
        self.status_bar.showMessage(f"Visage retiré de « {pname} ».")

    def action_move_face_to_person(
        self,
        photo_path: str,
        face_rect: Any,
        target_contact_id: str,
        target_name: str,
        source_contact_id: Optional[str] = None
    ) -> None:
        """
        FR: Déplace / réassigne le visage à une autre personne existante.
        EN: Moves / reassigns the face to another existing person.
        Ref: picasa3.exe @ PplAlbumPhoto::ID_PEOPLEALBUMS (0x00CAF244)
        """
        if not self.db or not self.db.face_manager:
            return
        fm = self.db.face_manager

        if not source_contact_id:
            if self.thumb_view.current_folder_filter and self.thumb_view.current_folder_filter.startswith("person:"):
                source_contact_id = self.thumb_view.current_folder_filter.split("person:")[1]

        old_fr = face_rect
        if not old_fr and source_contact_id:
            for f in fm.get_faces_for_photo(photo_path):
                if f.contact_id.lower() == source_contact_id.lower():
                    old_fr = f
                    break
        if not old_fr:
            faces = fm.photo_to_faces.get(photo_path, [])
            if faces:
                old_fr = faces[0]

        if old_fr:
            if source_contact_id and not old_fr.contact_id:
                old_fr.contact_id = source_contact_id

            fm.reassign_face(
                photo_path,
                old_fr,
                target_name,
                new_contact_id=target_contact_id,
                source_contact_id=source_contact_id
            )

            # Rafraîchir l'album de la personne source pour que le visage disparaisse immédiatement
            if source_contact_id and self.thumb_view.current_folder_filter == f"person:{source_contact_id}":
                src_person = fm.get_person(source_contact_id)
                if src_person:
                    self.thumb_view.filter_by_person(source_contact_id, src_person.name, src_person.photo_indices)
                else:
                    self.thumb_view.filter_by_person(source_contact_id, "", [])
            elif self.thumb_view.current_folder_filter == f"person:{target_contact_id}":
                target_person = fm.get_person(target_contact_id)
                if target_person:
                    self.thumb_view.filter_by_person(target_contact_id, target_person.name, target_person.photo_indices)
            elif self.thumb_view.current_folder_filter == "unnamed_faces":
                self.thumb_view.filter_by_unnamed_faces(fm.unnamed_faces)

            self.thumb_view._pixmap_cache.clear()
            self.thumb_view._recompute_layout()
            self.thumb_view.update()
            if hasattr(self, "library_tree"):
                self.library_tree.refresh_people()
            if hasattr(self, "right_drawer") and self.right_drawer.isVisible():
                self._on_selection_changed(list(self.thumb_view.selected_indices))
            self.status_bar.showMessage(f"Visage déplacé vers « {target_name} ».")

    def action_move_face_to_new_person(
        self,
        photo_path: str,
        face_rect: Any,
        source_contact_id: Optional[str] = None
    ) -> None:
        """
        FR: Crée une nouvelle personne et lui attribue le visage sélectionné.
        EN: Creates a new person and assigns the selected face to them.
        Ref: picasa3.exe @ PplAlbumPhoto::ID_PEOPLEALBUMSNEW (0x00CAF27C)
        """
        if not self.db or not self.db.face_manager:
            return
        name, ok = QInputDialog.getText(self, "Nouvelle personne", "Nom de la nouvelle personne :")
        if ok and name.strip():
            clean_name = name.strip()
            fm = self.db.face_manager
            cl = fm.create_person(clean_name)
            self.action_move_face_to_person(
                photo_path, face_rect, cl.contact_id, clean_name, source_contact_id=source_contact_id
            )

    def action_sort_folder_by(self, criterion: str, target_folder: Optional[str] = None) -> None:
        """
        FR: Trie le dossier courant par nom, date ou taille (Sort::ID_NAMESORT, DATESORT, SIZESORT)
            en triant `sec.item_indices` au sein des sections cibles sans invalider les indices globaux.
        EN: Sorts the current folder by name, date, or size (Sort::ID_NAMESORT, DATESORT, SIZESORT)
            by sorting `sec.item_indices` within the target sections without invalidating global indices.
        Ref: picasa3.exe @ Folder::SortFolderBy (0x00CAE204)
        """
        if not self.thumb_view.items:
            return

        if criterion == "name":
            def _sort_key(idx: int):
                if 0 <= idx < len(self.thumb_view.items):
                    return self.thumb_view.items[idx].filename.lower()
                return ""
        elif criterion == "date":
            pmp_dates = (
                self.db.pmps.get("imagedata_date").values
                if (self.db is not None and hasattr(self.db, "pmps") and "imagedata_date" in self.db.pmps)
                else None
            )
            def _sort_key(idx: int):
                if 0 <= idx < len(self.thumb_view.items):
                    it = self.thumb_view.items[idx]
                    if pmp_dates is not None and 0 <= it.index < len(pmp_dates) and pmp_dates[it.index]:
                        try:
                            return float(pmp_dates[it.index])
                        except Exception:
                            pass
                    try:
                        return os.path.getmtime(it.path) if it.path else 0
                    except Exception:
                        return 0
                return 0
        elif criterion == "size":
            pmp_sizes = (
                self.db.pmps.get("imagedata_filesize").values
                if (self.db is not None and hasattr(self.db, "pmps") and "imagedata_filesize" in self.db.pmps)
                else None
            )
            def _sort_key(idx: int):
                if 0 <= idx < len(self.thumb_view.items):
                    it = self.thumb_view.items[idx]
                    if pmp_sizes is not None and 0 <= it.index < len(pmp_sizes) and pmp_sizes[it.index]:
                        try:
                            return int(pmp_sizes[it.index])
                        except Exception:
                            pass
                    try:
                        return os.path.getsize(it.path) if it.path else 0
                    except Exception:
                        return 0
                return 0
        else:
            return

        norm_target = target_folder.replace("\\", "/").rstrip("/").lower() if target_folder else None
        for sec_list in (getattr(self.thumb_view, "visible_sections", []), getattr(self.thumb_view, "sections", [])):
            for sec in sec_list:
                if norm_target:
                    sec_fp = getattr(sec, "folder_path", "").replace("\\", "/").rstrip("/").lower()
                    sec_nm = getattr(sec, "name", "").lower()
                    if sec_fp != norm_target and sec_nm != norm_target:
                        continue
                sec.item_indices.sort(key=_sort_key)

        if hasattr(self.thumb_view, "_recalculate_layout"):
            self.thumb_view._recalculate_layout()
        elif hasattr(self.thumb_view, "_recompute_layout"):
            self.thumb_view._recompute_layout()
        if hasattr(self.thumb_view, "viewport") and callable(getattr(self.thumb_view, "viewport", None)):
            vp = self.thumb_view.viewport()
            if vp is not None:
                vp.update()
        self.thumb_view.update()
        labels = {"name": "nom", "date": "date", "size": "taille"}
        self.status_bar.showMessage(f"Photothèque triée par {labels.get(criterion, criterion)}.")

    def action_sort_album_by(self, criterion: str, target_album: Optional[str] = None) -> None:
        """
        FR: Trie l'album courant par nom, date ou taille (Album::SortAlbumBy).
        EN: Sorts the current album by name, date, or size (Album::SortAlbumBy).
        Ref: picasa3.exe @ Album::SortAlbumBy (0x00CAE43C)
        """
        self.action_sort_folder_by(criterion, target_folder=target_album)

    def action_keyboard_shortcuts(self) -> None:
        """
        FR: Affiche la liste des raccourcis clavier de Picasa (ID_HELP_KEYBOARD_SHORTCUTS).
        EN: Displays the list of Picasa keyboard shortcuts (ID_HELP_KEYBOARD_SHORTCUTS).
        Ref: picasa3.exe @ 0x0088C3EC, SHORTCUTS.XML
        """
        shortcuts_text = (
            "<b>Raccourcis clavier Picasa 3 :</b><br><br>"
            "<table>"
            "<tr><td><b>Ctrl+O</b></td><td>Ajouter un fichier à Picasa...</td></tr>"
            "<tr><td><b>Ctrl+N</b></td><td>Nouvel album...</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Enregistrer les retouches</td></tr>"
            "<tr><td><b>Ctrl+Shift+S</b></td><td>Enregistrer sous...</td></tr>"
            "<tr><td><b>F2</b></td><td>Renommer la sélection...</td></tr>"
            "<tr><td><b>Suppr</b></td><td>Supprimer du disque...</td></tr>"
            "<tr><td><b>Ctrl+R</b></td><td>Faire pivoter vers la droite</td></tr>"
            "<tr><td><b>Ctrl+Shift+R</b></td><td>Faire pivoter vers la gauche</td></tr>"
            "<tr><td><b>Ctrl+T</b></td><td>Ajouter / Supprimer une étoile</td></tr>"
            "<tr><td><b>Ctrl+C</b></td><td>Copier la photo</td></tr>"
            "<tr><td><b>Ctrl+Shift+C</b></td><td>Copier tous les effets</td></tr>"
            "<tr><td><b>Ctrl+Shift+V</b></td><td>Coller tous les effets</td></tr>"
            "<tr><td><b>Ctrl+Shift+Y</b></td><td>Copier le chemin complet</td></tr>"
            "<tr><td><b>Ctrl+A</b></td><td>Tout sélectionner</td></tr>"
            "<tr><td><b>Ctrl+4</b></td><td>Lancer le diaporama</td></tr>"
            "<tr><td><b>Alt+Entrée</b></td><td>Propriétés de l'image</td></tr>"
            "<tr><td><b>Ctrl+P</b></td><td>Imprimer</td></tr>"
            "<tr><td><b>Ctrl+Shift+P</b></td><td>Imprimer la planche-contact</td></tr>"
            "</table>"
        )
        QMessageBox.information(self, "Raccourcis clavier Picasa", shortcuts_text)

    def action_privacy_policy(self) -> None:
        """
        FR: Affiche la politique de confidentialité (ID_HELP_PRIVACY).
        EN: Displays the privacy policy (ID_HELP_PRIVACY).
        Ref: picasa3.exe @ 0x0088C3EC
        """
        msg = (
            "<b>Règles de confidentialité de Picasa :</b><br><br>"
            "Picasa fonctionne exclusivement en local sur votre poste de travail.<br><br>"
            "• Aucune de vos photos, vidéos, bases de données ou métadonnées n'est transmise à des tiers.<br>"
            "• La détection et la reconnaissance des visages s'exécutent entièrement en local.<br>"
            "• Les modifications sont non-destructives et préservées dans les fichiers .picasa.ini locaux."
        )
        QMessageBox.information(self, "Règles de confidentialité", msg)

    def action_set_screensaver(self) -> None:
        """
        FR: Définit les photos sélectionnées comme économiseur d'écran (ID_SCREENSAVER).
        EN: Sets the selected photos as the screensaver album (ID_SCREENSAVER).
        Ref: picasa3.exe @ eMenuCreate::ID_SCREENSAVER, DazzleCollection::PicasaScreensaverAlbum
        """
        paths = self._get_active_photo_paths()
        if not paths:
            QMessageBox.information(self, "Économiseur d'écran", "Sélectionnez au moins une photo pour l'économiseur d'écran.")
            return
        self.action_add_photos_to_album(paths, "screensaver")
        self.status_bar.showMessage(f"{len(paths)} photo(s) configurée(s) pour l'économiseur d'écran Picasa.")

    def action_help_contents(self) -> None:
        """
        FR: Affiche l'aide et les informations de Picasa (ID_HELP_DEFAULT, F1).
        EN: Displays Picasa help and information (ID_HELP_DEFAULT, F1).
        Ref: picasa3.exe @ eMenuHelp::ID_HELP_DEFAULT
        """
        self.action_keyboard_shortcuts()

    def action_slideshow(self) -> None:
        """
        FR: Lance le lecteur de diaporama plein écran (SlideshowBaseHandler).
        EN: Starts the fullscreen slideshow player (SlideshowBaseHandler).
        Ref: picasa3.exe @ 0x00620AB7, 0x0074E843, ID_VIEW_SLIDESHOW (Ctrl+4)
        """
        paths: List[str] = []
        start_idx = 0

        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            paths = [item.path for item in self.thumb_view.items if item.path]
            try:
                start_idx = paths.index(self.one_up_view.current_photo_path)
            except ValueError:
                start_idx = 0
        elif self.thumb_view.selected_indices:
            selected_set = sorted(self.thumb_view.selected_indices)
            paths = [self.thumb_view.items[i].path for i in selected_set if self.thumb_view.items[i].path]
            start_idx = 0
        elif self.thumb_view.items:
            paths = [item.path for item in self.thumb_view.items if item.path]
            start_idx = 0

        if not paths:
            QMessageBox.information(self, "Diaporama", "Aucune photo à afficher dans le diaporama.")
            return

        self._slideshow_win = PicasaSlideshowWindow(paths, start_index=start_idx, parent=self)
        self._slideshow_win.showFullScreen()

    def _on_album_slideshow(self, paths: List[str], music_path: Optional[str] = None) -> None:
        """
        FR: Lance directement le diaporama pour l'album dont l'en-tête a été cliqué.
        EN: Directly starts the slideshow for the album whose header was clicked.
        """
        if not paths:
            return
        self._slideshow_win = PicasaSlideshowWindow(paths, start_index=0, audio_path=music_path, parent=self)
        self._slideshow_win.showFullScreen()

    def action_rename(self) -> None:
        """
        FR: Ouvre la boîte de dialogue de renommage par lot (RenameDialog, F2).
        EN: Opens the batch rename dialog (RenameDialog, F2).
        Ref: picasa3.exe @ 0x00936F78, rename.fen, RENAME_FR.XML
        """
        selected_paths: List[str] = []
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            selected_paths = [self.one_up_view.current_photo_path]
        elif self.thumb_view.selected_indices:
            selected_paths = [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
        elif self.thumb_view.items:
            selected_paths = [item.path for item in self.thumb_view.items if item.path]

        if not selected_paths:
            QMessageBox.information(self, "Renommer", "Aucune photo sélectionnée.")
            return

        dlg = PicasaRenameDialog(selected_paths, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pairs = dlg.execute_rename()
            if pairs:
                for old_p, new_p in pairs:
                    if self.db is not None and hasattr(self.db, "rename_photo"):
                        self.db.rename_photo(old_p, new_p)
                    else:
                        # Migrer [old_fname] -> [new_fname] dans .picasa.ini et .picasaoriginals/
                        parent_dir = os.path.dirname(old_p)
                        old_fn = os.path.basename(old_p)
                        new_fn = os.path.basename(new_p)
                        orig_old = os.path.join(parent_dir, ".picasaoriginals", old_fn)
                        orig_new = os.path.join(parent_dir, ".picasaoriginals", new_fn)
                        if os.path.exists(orig_old) and not os.path.exists(orig_new):
                            try:
                                os.rename(orig_old, orig_new)
                            except Exception:
                                pass
                        ini_p = os.path.join(parent_dir, ".picasa.ini")
                        if os.path.exists(ini_p):
                            try:
                                doc = PicasaIniParser.parse_file(ini_p)
                                sec = doc.get_section(old_fn)
                                if sec is not None:
                                    new_sec = doc.get_or_create_section(new_fn)
                                    for k, v in sec.items():
                                        new_sec.set(k, v)
                                    doc.remove_section(old_fn)
                                    doc.write_file(ini_p)
                            except Exception:
                                pass
                    for item in self.thumb_view.items:
                        if item.path == old_p:
                            item.path = new_p
                            item.filename = os.path.basename(new_p)
                self.thumb_view.update()
                self.status_bar.showMessage(f"{len(pairs)} fichier(s) renommé(s) avec succès.")
                # Mettre à jour One-Up si affiché
                if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
                    for old_p, new_p in pairs:
                        if old_p == self.one_up_view.current_photo_path:
                            self.one_up_view.open_photo(
                                self.db,
                                self.one_up_view.current_index,
                                self.one_up_view.available_indices,
                                direct_path=new_p
                            )
                            break

    def action_print(self) -> None:
        """
        FR: Ouvre l'atelier d'impression interactif WYSIWYG (CPrintDlg).
        EN: Opens the interactive WYSIWYG print workshop (CPrintDlg).
        Ref: picasa3.exe @ 0x008C3380, reviewprint, ID_FILE_PRINT (Ctrl+P)
        """
        from picasa_py.ui.print_dialog import PicasaPrintDialog

        photos_to_print: List[str] = []
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            photos_to_print = [self.one_up_view.current_photo_path]
        elif self.thumb_view.selected_indices:
            photos_to_print = [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
        elif self.thumb_view.items:
            photos_to_print = [item.path for item in self.thumb_view.items if item.path]

        if not photos_to_print:
            QMessageBox.information(self, "Imprimer", "Aucune photo sélectionnée à imprimer.")
            return

        dlg = PicasaPrintDialog(photos_to_print, parent=self)
        dlg.exec()

    def action_export(self) -> None:
        """
        FR: Ouvre la boîte de dialogue d'exportation vers un dossier (CExportPrefsDialog).
        EN: Opens the export to folder dialog (CExportPrefsDialog).
        Ref: picasa3.exe @ 0x00738D00, export.fen, EXPORT_FR.XML
        """
        items_to_export: List[str] = []

        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            items_to_export = [self.one_up_view.current_photo_path]
        elif self.thumb_view.selected_indices:
            items_to_export = [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
        elif self.thumb_view.items:
            items_to_export = [item.path for item in self.thumb_view.items if item.path]

        if not items_to_export:
            QMessageBox.information(self, "Export", "Aucune photo à exporter.")
            return

        default_name = "Export"
        if items_to_export:
            parent_name = Path(items_to_export[0]).parent.name
            if parent_name:
                default_name = parent_name

        dlg = PicasaExportDialog(items_to_export, default_folder_name=default_name, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        config = dlg.get_config()

        # Boîte de progression officielle (CImageOutput::exportprog)
        prog = QProgressDialog("Préparation de l'exportation...", "Annuler", 0, len(items_to_export), self)
        prog.setWindowTitle("Exportation vers le dossier")
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.setMinimumDuration(200)

        self._export_worker = PicasaExportWorker(items_to_export, config, self)

        def on_prog(cur: int, tot: int, name: str) -> None:
            """
            FR: Met à jour la barre de progression de l'exportation.
            EN: Updates the export progress dialog bar and label.
            """
            prog.setValue(cur)
            prog.setLabelText(f"Exportation de : {name} ({cur}/{tot})")

        def on_finished(succ: int, err: int, out_dir: str) -> None:
            """
            FR: Affiche le récapitulatif de fin d'exportation et propose d'ouvrir le dossier.
            EN: Displays the export completion summary and offers to open the output folder.
            """
            prog.close()
            self.status_bar.showMessage(f"Export terminé : {succ} photo(s) exportée(s) vers {out_dir}")
            msg = f"Exportation terminée avec succès !\n\n{succ} fichier(s) exporté(s) dans :\n{out_dir}"
            if err > 0:
                msg += f"\n\n({err} erreur(s) rencontrée(s))"
            reply = QMessageBox.information(
                self,
                "Exportation terminée",
                msg,
                QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
            )
            if reply == QMessageBox.StandardButton.Open:
                import subprocess
                if sys.platform == "win32":
                    subprocess.Popen(f'explorer "{out_dir}"')
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", out_dir])
                else:
                    subprocess.Popen(["xdg-open", out_dir])

        prog.canceled.connect(self._export_worker.cancel)
        self._export_worker.progress.connect(on_prog)
        self._export_worker.finished.connect(on_finished)
        self._export_worker.start()

    def action_adjust_time(self) -> None:
        """
        FR: Ouvre la boîte de dialogue d'ajustement de date et d'heure (COffsetDate).
        EN: Opens the date and time adjustment dialog (COffsetDate).
        Ref: picasa3.exe @ 0x0077C670, offsettime.fen, OFFSETTIME_FR.XML
        """
        selected_paths: List[str] = []
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            selected_paths = [self.one_up_view.current_photo_path]
        elif self.thumb_view.selected_indices:
            selected_paths = [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
        elif self.thumb_view.items:
            selected_paths = [item.path for item in self.thumb_view.items if item.path]

        if not selected_paths:
            QMessageBox.information(self, "Ajuster la date", "Aucune photo sélectionnée.")
            return

        dlg = PicasaAdjustTimeDialog(selected_paths, db=self.db, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            results = dlg.execute_adjustment()
            if results:
                self.status_bar.showMessage(f"Date ajustée pour {len(results)} photo(s).")
                if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
                    self.one_up_view.open_photo(
                        self.db,
                        self.one_up_view.current_index,
                        self.one_up_view.available_indices,
                        direct_path=self.one_up_view.current_photo_path
                    )
                self.thumb_view.update()

    def action_write_facetags(self) -> None:
        """
        FR: Ouvre la boîte de dialogue d'écriture des tags de visages dans les fichiers JPEG XMP.
        EN: Opens the dialog to write face tags into JPEG XMP metadata.
        Ref: FileFaceTagger @ 0x00C29F00, write_all_facetags.fen, WRITE_ALL_FACETAGS_FR.XML
        """
        from picasa_py.faces.xmp_tagger import PicasaWriteFaceTagsDialog

        selected_paths: List[str] = []
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            selected_paths = [self.one_up_view.current_photo_path]
        elif self.thumb_view.selected_indices:
            selected_paths = [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]

        dlg = PicasaWriteFaceTagsDialog(selected_paths=selected_paths, db=self.db, parent=self)
        dlg.exec()

    action_write_all_facetags = action_write_facetags

    def action_about(self) -> None:
        """
        FR: Affiche la boîte de dialogue « À propos de PyCasa » avec la version complète.
        EN: Displays the "About PyCasa" dialog with the complete version number.
        Ref: picasa3.exe @ ID_HELP_ABOUT, ABOUT_*.XML, STRINGRES_*.XML (IDS_ABOUT1)
        """
        title = get_about_dialog_title(self.res_mgr)
        text = get_about_dialog_text(self.res_mgr)
        QMessageBox.about(self, title, text)

    def action_options(self) -> None:
        """
        FR: Ouvre la boîte de dialogue Préférences / Options à 7 onglets (options.fen).
        EN: Opens the 7-tab Preferences / Options dialog (options.fen).
        Ref: picasa3.exe @ ID_TOOLS_OPTIONS (0x0088C3EC), OPTIONS_FR.XML
        """
        from picasa_py.ui.options_dialog import PicasaOptionsDialog

        dlg = PicasaOptionsDialog(parent=self)
        dlg.settings_saved.connect(self._on_options_saved)
        dlg.exec()

    def _on_language_changed(self, lang: str = "") -> None:
        """
        FR: Met à jour dynamiquement tous les composants de l'interface lors d'un changement de langue.
        EN: Dynamically retranslates all UI components when the active language changes.
        """
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """
        FR: Retraduit la barre de menus, la barre supérieure, l'arborescence, la grille, le bac à photos,
        le tiroir latéral droit et l'éditeur One-Up selon la langue active.
        EN: Retranslates the menu bar, top bar, library tree, thumbnail grid, photo tray,
        right drawer, and One-Up editor according to the active language.
        """
        self.setWindowTitle(get_window_title())
        if hasattr(self, "menu_builder") and self.menu_builder:
            if hasattr(self.menu_builder, "retranslate_ui"):
                self.menu_builder.retranslate_ui()
            else:
                self.menu_builder.build_menu_bar()
        if hasattr(self, "top_bar") and hasattr(self.top_bar, "retranslate_ui"):
            self.top_bar.retranslate_ui()
        if hasattr(self, "library_tree") and hasattr(self.library_tree, "retranslate_ui"):
            self.library_tree.retranslate_ui()
        if hasattr(self, "photo_tray") and hasattr(self.photo_tray, "retranslate_ui"):
            self.photo_tray.retranslate_ui()
        if hasattr(self, "right_drawer") and hasattr(self.right_drawer, "retranslate_ui"):
            self.right_drawer.retranslate_ui()
        if hasattr(self, "one_up_view") and hasattr(self.one_up_view, "retranslate_ui"):
            self.one_up_view.retranslate_ui()
        if hasattr(self, "thumb_view") and hasattr(self.thumb_view, "retranslate_ui"):
            self.thumb_view.retranslate_ui()
        if hasattr(self, "notifier_popup") and hasattr(self.notifier_popup, "retranslate_ui"):
            self.notifier_popup.retranslate_ui()

    def _on_options_saved(self, settings: dict) -> None:
        """
        FR: Applique les paramètres modifiés depuis la boîte de dialogue Options (moteur de visages, langue).
        EN: Applies modified settings from the Options dialog (face detection engine, language).
        """
        if "faces_engine" in settings:
            try:
                from picasa_py.faces.detector import PicasaFaceDetector
                PicasaFaceDetector.get().set_engine(str(settings["faces_engine"]))
            except Exception:
                pass
        self._on_language_changed()

        from picasa_py.ui.resources import PicasaResourceManager
        curr_lang = PicasaResourceManager.get().get_current_language()
        lang_names = dict(PicasaResourceManager.get().get_available_languages())
        lang_label = lang_names.get(curr_lang, curr_lang.upper())
        eng_label = "Python pur (red.cfg)" if settings.get("faces_engine") == "python" else "Natif (Red.dll + red.cfg)"
        self.status_bar.showMessage(f"Préférences appliquées — Langue : {lang_label} — Moteur visages : {eng_label}")

    def action_collage(self) -> None:
        """
        FR: Ouvre l'atelier de création de montages photo (CCollageUI).
        EN: Opens the photo collage creation workshop (CCollageUI).
        Ref: picasa3.exe @ ID_COLLAGEMAKER (0x0088C3EC), CCollageUI
        """
        from picasa_py.ui.collage import PicasaCollageDialog

        photos_for_collage: List[str] = []
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            photos_for_collage = [self.one_up_view.current_photo_path]
        elif self.thumb_view.selected_indices:
            photos_for_collage = [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
        elif self.thumb_view.items:
            photos_for_collage = [item.path for item in self.thumb_view.items if item.path]

        if not photos_for_collage:
            QMessageBox.information(self, "Montage photo", "Sélectionnez au moins une photo pour créer un montage.")
            return

        dlg = PicasaCollageDialog(photos_for_collage, parent=self)
        dlg.collage_created.connect(self._on_collage_created)
        dlg.exec()

    def _on_collage_created(self, saved_path: str) -> None:
        """
        FR: Lance l'indexation du dossier parent après la création d'un montage photo.
        EN: Triggers background indexing of the parent folder after a photo collage is created.
        """
        self.status_bar.showMessage(f"Nouveau montage photo créé : {Path(saved_path).name}")
        parent_dir = str(Path(saved_path).parent)
        self._start_background_scan([parent_dir])

    def action_movie(self, face_mode: bool = False, contact_id: Optional[str] = None) -> None:
        """
        FR: Ouvre le créateur de films / diaporama vidéo (CMakeMoviePanel) ou Film de visages (CMakeFaceMoviePanel).
        EN: Opens the Movie Maker / video slideshow creator (CMakeMoviePanel) or Face Movie creator (CMakeFaceMoviePanel).
        Ref: picasa3.exe @ MakeMoviePanel, CMakeMoviePanel, CMakeFaceMoviePanel, ID_MAKEMOVIE, ID_MOVIEFACES
        """
        from picasa_py.ui.movie_maker import PicasaMovieMakerDialog

        photos_for_movie: List[str] = []
        if self.stack.currentWidget() == self.one_up_view and self.one_up_view.current_photo_path:
            photos_for_movie = [self.one_up_view.current_photo_path]
        elif self.thumb_view.selected_indices:
            photos_for_movie = [
                self.thumb_view.items[idx].path
                for idx in sorted(self.thumb_view.selected_indices)
                if idx < len(self.thumb_view.items) and self.thumb_view.items[idx].path
            ]
        elif self.thumb_view.items:
            photos_for_movie = [item.path for item in self.thumb_view.items if item.path]

        if not photos_for_movie:
            QMessageBox.information(self, "Créateur de films", "Sélectionnez au moins une photo pour créer un film.")
            return

        dlg = PicasaMovieMakerDialog(photos_for_movie, face_mode=face_mode, contact_id=contact_id, parent=self)
        dlg.movie_created.connect(self._on_movie_created)
        dlg.exec()

    def _on_movie_created(self, saved_path: str) -> None:
        """
        FR: Lance l'indexation du dossier parent après la création d'un film vidéo.
        EN: Triggers background indexing of the parent folder after a video movie is created.
        """
        self.status_bar.showMessage(f"Nouveau film vidéo créé : {Path(saved_path).name}")
        parent_dir = str(Path(saved_path).parent)
        self._start_background_scan([parent_dir])

    # --- FR: Gestionnaire de dossiers & Auto-indexation en arrière-plan / EN: Folder Manager & Background Auto-Indexing ---

    def action_folder_manager(self) -> None:
        """
        FR: Ouvre la boîte de dialogue Gestionnaire de dossiers (foldermgr).
        EN: Opens the Folder Manager dialog (foldermgr).
        """
        if not self.db:
            QMessageBox.warning(self, "Gestionnaire de dossiers", "Aucune base de données active.")
            return

        dlg = PicasaFolderManagerDialog(self.db, self)
        dlg.folders_updated.connect(self._on_folders_updated)
        dlg.exec()

    def _on_folders_updated(self, newly_watched: List[str]) -> None:
        """
        FR: Réagit à la mise à jour des dossiers dans le Gestionnaire de dossiers.
        EN: Handles folder watch status updates from the Folder Manager.
        """
        if self.watcher:
            self.watcher.reload_from_database()
        self.notify_folders_changed()
        if newly_watched:
            self.status_bar.showMessage(f"Dossiers mis à jour. Lancement de l'indexation de {len(newly_watched)} dossier(s)...")
            self._start_background_scan(newly_watched)

    def _on_watcher_scan_requested(self, paths: List[str]) -> None:
        """
        FR: Déclenché par le watcher après le délai de stabilisation de 500 ms.
        Ignore toute demande si la base active ne possède aucun dossier surveillé ni indexé.
        EN: Triggered by the folder watcher after the 500 ms debounce delay.
        Ignores any request if the active database has no watched or indexed folders.
        Ref: picasa3.exe @ 0x00704F20 (ReadDirectoryChangesW debounce 500 ms)
        """
        if not self.db or not paths:
            return
        if self.sender() is not None and self.sender() is not self.watcher:
            return
        watched = [p for p, st in self.db.get_watched_folders().items() if st in ("1", "2")]
        if not watched and not self.db.index:
            return
        self.status_bar.showMessage(f"Modification détectée dans {len(paths)} dossier(s)...")
        self._start_background_scan(paths, notify_popup=True)

    def _start_background_scan(self, folder_paths: List[str], notify_popup: bool = True) -> None:
        """
        FR: Lance l'indexation en arrière-plan sans bloquer l'interface. Si un scan est déjà
        en cours, place les dossiers modifiés en file d'attente pour les traiter dès la fin du scan.
        EN: Starts background folder indexing without blocking the UI. If a scan is already
        running, queues the modified folders so they are scanned immediately when the active scan finishes.
        Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows), 0x004E1700 (ytDirScannerChangeListWindows)
        """
        if getattr(self, "_is_closing", False) or not self.db or not folder_paths:
            return
        if self.scan_worker and self.scan_worker.isRunning():
            for p in folder_paths:
                if p:
                    self._pending_scan_folders.add(p)
            if notify_popup:
                self._pending_scan_notify = True
            return

        self._active_scan_notify = notify_popup
        self._last_incremental_ui_sync = time.monotonic()
        self.scan_worker = BackgroundScanWorker(self.db, folder_paths, self)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.batch_indexed.connect(self._on_scan_batch_indexed)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.start(QThread.Priority.LowPriority)

    def _on_scan_batch_indexed(self, folder_path: str, filename: str, db_idx: int, batch_count: int) -> None:
        """
        FR: Appelé par lots régulés (ou par fichier sur les petits dossiers) depuis `BackgroundScanWorker`.
        Met à jour la fenêtre surgissante `PicasaNotifierPopup` en lisant directement la miniature
        précalculée dans `CThumbDB` (`thumbs_0.db`) sans jamais décoder l'image haute résolution sur le thread GUI.
        EN: Called in throttled batches (or per file on small folders) from `BackgroundScanWorker`.
        Updates the `PicasaNotifierPopup` window by reading the precomputed thumbnail directly from
        `CThumbDB` (`thumbs_0.db`) without ever decoding the full-resolution image on the GUI thread.
        Ref: picasa3.exe @ 0x00571850 (CThumbUI::NotifyPhotoAddedOrUpdated -> CNotifierPopup @ 0x00659340)
        """
        if getattr(self, "_is_closing", False) or not self.db:
            return
        sender = self.sender()
        if sender is not None and (sender is not self.scan_worker or getattr(sender, "db", None) is not self.db):
            return
        full_path = os.path.join(folder_path, filename) if folder_path and filename else ""
        if getattr(self, "_active_scan_notify", True) and hasattr(self, "notifier_popup") and self.notifier_popup:
            self.notifier_popup.db = self.db
            self.notifier_popup.notify_photo_indexed(
                folder_path=folder_path,
                filename=filename,
                file_path=full_path,
                db_idx=db_idx,
                show_popup=self.isVisible() or self.isMinimized(),
                increment=max(1, int(batch_count)),
                db=self.db,
            )

        now = time.monotonic()
        last_sync = getattr(self, "_last_incremental_ui_sync", 0.0)
        if (
            self.db is not None
            and (now - last_sync) >= 1.5
            and (now - BackgroundScanWorker._last_gui_activity_ts) >= 0.4
        ):
            self._last_incremental_ui_sync = now
            try:
                self.library_tree.refresh_folders()
                if self.stack.currentWidget() != self.one_up_view:
                    self.thumb_view.sync_from_database_incremental(self.db)
            except Exception:
                pass

    def _on_scan_file_indexed(self, folder_path: str, filename: str) -> None:
        """
        FR: Appelé pour un fichier nouvellement indexé ou mis à jour par BackgroundScanWorker.
        Affiche et met à jour la fenêtre surgissante Picasa Notifier en bas à droite de l'écran.
        EN: Called for a newly indexed or updated file by BackgroundScanWorker.
        Displays and updates the Picasa Notifier popup window at the bottom-right of the screen.
        Ref: picasa3.exe @ 0x00571850 (CThumbUI::NotifyPhotoAddedOrUpdated -> CNotifierPopup @ 0x00659340)
        """
        self._on_scan_batch_indexed(folder_path, filename, -1, 1)

    def _on_notifier_popup_clicked(self, file_path: str, folder_path: str) -> None:
        """
        FR: Réagit au clic sur une cellule de la fenêtre surgissante Picasa Notifier :
        restaure la fenêtre principale au premier plan et sélectionne la photo dans la bibliothèque.
        EN: Handles clicking a cell in the Picasa Notifier popup window:
        restores the main window to the foreground and selects the photo in the library.
        Ref: picasa3.exe @ 0x005E4D30 (handler for WM_USER + 0xFF = 0x4FF posted by 0x00658056)
        """
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        if file_path and os.path.exists(file_path):
            self.action_locate_in_picasa(file_path)
        elif folder_path and hasattr(self, "thumb_view") and hasattr(self.thumb_view, "scroll_to_folder"):
            self.thumb_view.scroll_to_folder(folder_path)

    def _on_scan_progress(self, current: int, total: int, fname: str) -> None:
        """
        FR: Affiche la progression de l'indexation en arrière-plan dans la barre d'état.
        EN: Displays background indexing progress in the status bar.
        """
        self.status_bar.showMessage(f"Indexation en arrière-plan : {current}/{total} — {fname}")

    def _on_scan_finished(self, total_added: int) -> None:
        """
        FR: Rafraîchit la bibliothèque à la fin de l'indexation, traite les éventuels dossiers
        en file d'attente et enchaîne avec la détection des visages.
        EN: Refreshes the library when indexing finishes, drains any queued folders,
        and chains into background face detection.
        """
        if getattr(self, "_is_closing", False) or not self.db:
            return
        sender = self.sender()
        if sender is not None and (sender is not self.scan_worker or getattr(sender, "db", None) is not self.db):
            return
        if total_added > 0 and self.db:
            self.library_tree.refresh_folders()
            self.library_tree.refresh_albums()
            if getattr(self.db, "_face_manager", None) is not None:
                self.library_tree.refresh_people()
            if not self.thumb_view.sync_from_database_incremental(self.db):
                self.thumb_view.set_database(self.db, preserve_view_state=True)
            self.status_bar.showMessage(f"Indexation terminée : {total_added} photo(s) indexée(s)")
        else:
            self.status_bar.showMessage("Indexation terminée : photothèque à jour")

        scanned_folders = getattr(self.scan_worker, "folder_paths", None) if self.scan_worker else None

        # Si des modifications ont été détectées par le watcher pendant que ce scan tournait, les lancer immédiatement
        if self._pending_scan_folders and not getattr(self, "_is_closing", False):
            queued = list(self._pending_scan_folders)
            notify_next = self._pending_scan_notify
            self._pending_scan_folders.clear()
            self._pending_scan_notify = False
            self._start_background_scan(queued, notify_popup=notify_next)
            return

        # Enchaîner avec la détection des visages en arrière-plan (Ref: BgFaceDetectThread @ 0x0087ECD6)
        if self.auto_scan and self.db and not getattr(self, "_is_closing", False):
            self._start_background_face_detection(scanned_folders)

    def _start_background_face_detection(self, folder_paths: Optional[List[str]] = None) -> None:
        """
        FR: Lance le thread de détection et de reconnaissance des visages en arrière-plan (`BgFaceDetectThread`).
        EN: Starts the background face detection and recognition thread (`BgFaceDetectThread`).
        Ref: picasa3.exe @ 0x0087ECD6 (BgFaceDetectThread), 0x0093B9CE (CFaceDetector), 0x008C1F34 (FaceSyncer)
        """
        if getattr(self, "_is_closing", False) or not self.db or not getattr(self.db, "face_manager", None):
            return
        if self.face_worker and self.face_worker.isRunning():
            return


        self.face_worker = BackgroundFaceDetectionWorker(
            self.db,
            folder_paths=folder_paths,
            persist_ini=False,
            parent=self,
        )
        self.face_worker.progress.connect(self._on_face_detect_progress)
        self.face_worker.people_updated.connect(self._on_people_changed)
        self.face_worker.finished.connect(self._on_face_detect_finished)
        self.face_worker.start(QThread.Priority.LowestPriority)

    def _on_face_detect_progress(self, current: int, total: int, fname: str) -> None:
        """
        FR: Affiche la progression de la détection des visages dans la barre d'état.
        EN: Displays background face detection progress in the status bar.
        """
        self.status_bar.showMessage(f"Détection des visages en arrière-plan : {current}/{total} — {fname}")

    def _on_face_detect_finished(self, total_faces: int) -> None:
        """
        FR: Met à jour les personnes et la barre d'état à la fin de la détection des visages.
        EN: Updates people and the status bar when background face detection finishes.
        """
        if total_faces > 0:
            self._on_people_changed()
            self.status_bar.showMessage(f"Détection des visages terminée : {total_faces} nouveau(x) visage(s) détecté(s)")
        else:
            self.status_bar.showMessage("Prêt")

    def stop_background_tasks(self) -> None:
        """
        FR: Interrompt, déconnecte et attend la fin de tous les threads d'arrière-plan
        afin qu'aucun signal en file d'attente de l'ancienne base ne pollue la nouvelle base.
        EN: Cancels, disconnects, and waits for all background threads to finish so no
        queued signal from the previous database can pollute the new database.
        """
        self._pending_scan_folders.clear()
        self._pending_scan_notify = False
        if self.scan_worker:
            sw = self.scan_worker
            self.scan_worker = None
            sw.cancel()
            for sig, slot in (
                (sw.progress, self._on_scan_progress),
                (sw.batch_indexed, self._on_scan_batch_indexed),
                (sw.finished, self._on_scan_finished),
            ):
                try:
                    sig.disconnect(slot)
                except Exception:
                    pass
            if sw.isRunning():
                sw.wait(5000)
        if self.face_worker:
            fw = self.face_worker
            self.face_worker = None
            fw.cancel()
            for sig, slot in (
                (fw.progress, self._on_face_detect_progress),
                (fw.people_updated, self._on_people_changed),
                (fw.finished, self._on_face_detect_finished),
            ):
                try:
                    sig.disconnect(slot)
                except Exception:
                    pass
            if fw.isRunning():
                fw.wait(5000)
        if hasattr(self, "thumb_view") and getattr(self.thumb_view, "_cluster_worker", None):
            cw = self.thumb_view._cluster_worker
            self.thumb_view._cluster_worker = None
            if cw and cw.isRunning():
                cw.wait(5000)



    def closeEvent(self, event) -> None:
        """
        FR: Ferme proprement la fenêtre, masque la notification surgissante, interrompt les threads d'arrière-plan
        et sauvegarde sur disque toutes les tables modifiées de la base de données (db3/).
        EN: Cleanly closes the window, hides the notification popup, stops background threads,
        and flushes all dirty database tables (db3/) to disk.
        """
        self._is_closing = True
        if hasattr(self, "notifier_popup") and self.notifier_popup:
            self.notifier_popup.clear_notifications()
            self.notifier_popup.close()
        if hasattr(self, "one_up_view") and hasattr(self.one_up_view, "_flush_pending_thumb_db_sync"):
            try:
                self.one_up_view._flush_pending_thumb_db_sync()
            except Exception:
                pass
        self.stop_background_tasks()
        if getattr(self, "db", None) is not None and hasattr(self.db, "save_database"):
            try:
                t_timer = getattr(self.db, "_thumb_save_timer", None)
                if t_timer is not None:
                    t_timer.cancel()
                    self.db._thumb_save_timer = None
                self.db.save_database()
            except Exception:
                pass
        super().closeEvent(event)


    def __del__(self) -> None:
        """
        FR: Arrête les tâches d'arrière-plan lors de la destruction de l'instance.
        EN: Stops background tasks upon instance destruction.
        """
        try:
            self.stop_background_tasks()
        except Exception:
            pass

