"""
Main Application Window for PyCasa (faithful reproduction of ytWindow).

Ref: picasa3.exe @ 0x00983940 (ytWindow WndProc)
Ref: picasa3.exe @ 0x0070494B (Magic signature 0x47506332 'GPc2')
Ref: picasa3.exe @ OneUp, editoneup
Ref: AGENTS.md §4 bis (Disposition et fonctionnement identiques)
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QStackedWidget, QStatusBar, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

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
from picasa_py.scanner.watcher import PicasaFolderWatcher
from picasa_py.scanner.scanner import BackgroundScanWorker
from picasa_py.db.database import PicasaDatabase


# Ref: picasa3.exe @ 0x00983940 (ytWindow)
class PicasaMainWindow(QMainWindow):
    """
    Fenêtre principale de l'application reproduisant ytWindow de Picasa 3.
    Gère la bascule entre la vue Bibliothèque (grille) et la vue Édition (One-Up).
    """
    WINDOW_MAGIC = 0x47506332  # 'GPc2'

    def __init__(self, db_path: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()
        self.watcher: Optional[PicasaFolderWatcher] = None
        self.scan_worker: Optional[BackgroundScanWorker] = None

        self.setWindowTitle("Picasa 3")
        self.setWindowIcon(self.res_mgr.get_icon(105))
        self.resize(1200, 780)

        # Central container
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Barre d'outils supérieure
        self.top_bar = PicasaTopBar(self.style, self)
        main_layout.addWidget(self.top_bar)

        # 2. Sélecteur de mode (Bibliothèque / One-Up View)
        self.stack = QStackedWidget(self)

        # Page 0: Bibliothèque (Splitter 3 volets: Arborescence | Grille | Tiroir)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setHandleWidth(4)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #D6D6D6;
            }
        """)

        # Volet gauche (Arborescence)
        self.library_tree = PicasaLibraryTree(self.style, self)
        self.library_tree.setMinimumWidth(180)
        self.splitter.addWidget(self.library_tree)

        # Volet central (Grille de vignettes)
        self.thumb_view = PicasaThumbnailView(self.style, self)
        self.splitter.addWidget(self.thumb_view)

        # Volet droit (Tiroir de métadonnées)
        self.right_drawer = PicasaRightDrawer(self.style, self)
        self.splitter.addWidget(self.right_drawer)

        self.splitter.setSizes([220, 720, 260])
        self.stack.addWidget(self.splitter)

        # Page 1: Vue d'édition One-Up (Ref: picasa3.exe @ OneUp)
        self.one_up_view = PicasaOneUpView(self.style, self)
        self.stack.addWidget(self.one_up_view)

        main_layout.addWidget(self.stack, 1)

        # 3. Bac à photos inférieur (Photo Tray)
        self.photo_tray = PicasaPhotoTray(self.style, self)
        main_layout.addWidget(self.photo_tray)

        # 4. Barre d'état
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("background-color: #E6E6E6; color: #555555; font-size: 11px;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")

        # 5. Construction des menus
        self.menu_builder = PicasaMenuBuilder(self)
        self.menu_builder.build_menu_bar()

        # 6. Connexion des signaux
        self._connect_signals()

        # 7. Chargement de la base de données
        self.db: Optional[PicasaDatabase] = None
        self._init_database(db_path)

    def _connect_signals(self) -> None:
        # Sélection de dossier dans l'arborescence
        self.library_tree.folder_selected.connect(self._on_folder_selected)

        # Sélection d'éléments dans la grille
        self.thumb_view.selection_changed.connect(self._on_selection_changed)

        # Double-clic pour ouvrir la photo en grand (One-Up View)
        self.thumb_view.item_double_clicked.connect(self._open_one_up_view)

        # Retour à la bibliothèque
        self.one_up_view.back_to_library_requested.connect(self._back_to_library)

        # Curseur de zoom du plateau
        self.photo_tray.zoom_changed.connect(self.thumb_view.set_thumb_size)

        # Recherche et filtres
        self.top_bar.search_query_changed.connect(self._on_search_query)

        # Actions du plateau
        self.photo_tray.action_clear.connect(self.action_clear_selection)
        self.photo_tray.action_export.connect(self.action_export)

    def _init_database(self, db_path: Optional[str] = None) -> None:
        try:
            if db_path:
                self.db = PicasaDatabase.open(db_path)
            else:
                self.db = PicasaDatabase.open_default()

            self.library_tree.populate_from_database(self.db)
            self.thumb_view.set_database(self.db)
            count = len(self.db.index)
            self.status_bar.showMessage(f"Base de données chargée : {count} photos indexées")

            # Surveillance en temps réel des répertoires (debounce 500 ms, Ref: 0x00704F20)
            self.watcher = PicasaFolderWatcher(self.db, self)
            self.watcher.scan_requested.connect(self._on_watcher_scan_requested)

            # Analyse initiale en arrière-plan des dossiers surveillés
            watched = [p.rstrip("\\/") for p, st in self.db.get_watched_folders().items() if st in ("1", "2")]
            if watched:
                self._start_background_scan(watched)
        except Exception as e:
            self.status_bar.showMessage(f"Mode sans base active : {e}")

    def _open_one_up_view(self, item_idx: int) -> None:
        """
        Bascule en mode visualiseur/retouche plein écran pour la photo sélectionnée.
        """
        if self.db is None or item_idx >= len(self.thumb_view.items):
            return

        item = self.thumb_view.items[item_idx]
        available_indices = [self.thumb_view.items[i].index for i in self.thumb_view.filtered_indices]
        self.one_up_view.open_photo(self.db, item.index, available_indices)
        self.top_bar.hide()
        self.photo_tray.hide()
        self.stack.setCurrentIndex(1)
        self.one_up_view.setFocus()
        self.status_bar.showMessage(f"Éditeur Picasa : {item.filename}")

    def _back_to_library(self) -> None:
        """
        Revient à la grille de la photothèque.
        """
        self.stack.setCurrentIndex(0)
        self.top_bar.show()
        self.photo_tray.show()
        curr_db_idx = self.one_up_view.current_index
        if curr_db_idx >= 0:
            found = [i for i, it in enumerate(self.thumb_view.items) if it.index == curr_db_idx]
            if found:
                self.thumb_view.selected_indices = {found[0]}
                self.thumb_view.update()
                self._on_selection_changed([found[0]])
        self.thumb_view.setFocus()
        self.status_bar.showMessage("Bibliothèque")

    def _on_folder_selected(self, key: str, target_type: str, display_name: str) -> None:
        if target_type == "folder":
            self.thumb_view.filter_by_folder(key)
            self.status_bar.showMessage(f"Dossier sélectionné : {display_name}")
        elif target_type == "person":
            person = self.db.face_manager.get_person(key) if self.db and self.db.face_manager else None
            indices = person.photo_indices if person else []
            self.thumb_view.filter_by_person(key, display_name, indices)
            self.status_bar.showMessage(f"Personne : {display_name} ({len(indices)} photos)")
        else:
            self.thumb_view.filter_by_folder(None)
            self.status_bar.showMessage(f"Sélection : {display_name}")

    def _on_selection_changed(self, indices: List[int]) -> None:
        count = len(indices)
        self.photo_tray.set_selected_count(count)

        if count == 1 and self.db is not None:
            idx = indices[0]
            if idx < len(self.thumb_view.items):
                item = self.thumb_view.items[idx]
                entry = self.db.index[item.index]
                info = {
                    "filename": item.filename,
                    "date": "—",
                    "size": f"{entry.size // 1024} Ko" if entry.size else "—",
                    "resolution": "—",
                    "camera": "—"
                }
                self.right_drawer.display_item_info(info)
        elif count == 0:
            self.right_drawer.display_item_info(None)
        else:
            info = {
                "filename": f"{count} fichiers sélectionnés",
                "date": "—",
                "size": "—",
                "resolution": "—",
                "camera": "—"
            }
            self.right_drawer.display_item_info(info)

    def _on_search_query(self, query: str) -> None:
        if not self.db or not self.db.search_index:
            return
        query = query.strip()
        if not query:
            self.thumb_view.filter_by_folder(None)
            return

        doc_ids = self.db.search(query)
        self.thumb_view.filtered_indices = [
            i for i in doc_ids if i < len(self.thumb_view.items)
        ]
        self.thumb_view.section_title = f'Recherche : "{query}"'
        self.thumb_view.section_subtitle = f"{len(self.thumb_view.filtered_indices)} résultats"
        self.thumb_view.selected_indices.clear()
        self.thumb_view._recompute_layout()
        self.thumb_view.update()

    # --- Actions des Menus ---

    def action_add_file(self) -> None:
        fn, _ = QFileDialog.getOpenFileName(self, "Ajouter un fichier à Picasa", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if fn:
            self.status_bar.showMessage(f"Fichier sélectionné : {fn}")

    def action_select_all(self) -> None:
        self.thumb_view.selected_indices = set(self.thumb_view.filtered_indices)
        self.thumb_view.selection_changed.emit(list(self.thumb_view.selected_indices))
        self.thumb_view.update()

    def action_clear_selection(self) -> None:
        self.thumb_view.selected_indices.clear()
        self.thumb_view.selection_changed.emit([])
        self.thumb_view.update()

    def action_slideshow(self) -> None:
        QMessageBox.information(self, "Diaporama", "Lancement du diaporama plein écran.")

    def action_options(self) -> None:
        QMessageBox.information(self, "Options", "Préférences de Picasa (options.fen).")

    def action_export(self) -> None:
        sel_count = len(self.thumb_view.selected_indices)
        if sel_count == 0:
            QMessageBox.information(self, "Export", "Veuillez sélectionner au moins une image.")
            return
        dest_dir = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier de destination pour l'export")
        if dest_dir:
            self.status_bar.showMessage(f"Export de {sel_count} images vers {dest_dir}")

    def action_about(self) -> None:
        about_text = self.res_mgr.get_string(298, "Picasa 3 Re-implementation in Python")
        QMessageBox.about(self, "À propos de Picasa", f"Picasa 3 (Python Edition)\n\n{about_text}")

    # --- Gestionnaire de dossiers & Auto-indexation en arrière-plan ---

    def action_folder_manager(self) -> None:
        """Ouvre la boîte de dialogue Folder Manager (foldermgr)."""
        if not self.db:
            QMessageBox.warning(self, "Gestionnaire de dossiers", "Aucune base de données active.")
            return

        dlg = PicasaFolderManagerDialog(self.db, self)
        dlg.folders_updated.connect(self._on_folders_updated)
        dlg.exec()

    def _on_folders_updated(self, newly_watched: List[str]) -> None:
        """Réagit à la mise à jour des dossiers dans Folder Manager."""
        if self.watcher:
            self.watcher.reload_from_database()
        if newly_watched:
            self.status_bar.showMessage(f"Dossiers mis à jour. Lancement de l'indexation de {len(newly_watched)} dossier(s)...")
            self._start_background_scan(newly_watched)

    def _on_watcher_scan_requested(self, paths: List[str]) -> None:
        """Déclenché par le watcher après le debounce de 500 ms."""
        self.status_bar.showMessage(f"Modification détectée dans {len(paths)} dossier(s)...")
        self._start_background_scan(paths)

    def _start_background_scan(self, folder_paths: List[str]) -> None:
        """Lance l'indexation en arrière-plan sans bloquer l'interface."""
        if not self.db or not folder_paths:
            return
        if self.scan_worker and self.scan_worker.isRunning():
            return

        self.scan_worker = BackgroundScanWorker(self.db, folder_paths, self)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _on_scan_progress(self, current: int, total: int, fname: str) -> None:
        self.status_bar.showMessage(f"Indexation en arrière-plan : {current}/{total} — {fname}")

    def _on_scan_finished(self, total_added: int) -> None:
        if total_added > 0 and self.db:
            self.library_tree.populate_from_database(self.db)
            self.thumb_view.set_database(self.db)
            self.status_bar.showMessage(f"Indexation terminée : {total_added} nouvelle(s) photo(s) ajoutée(s)")
        else:
            self.status_bar.showMessage("Indexation terminée : photothèque à jour")

    def closeEvent(self, event) -> None:
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait(1000)
        super().closeEvent(event)

