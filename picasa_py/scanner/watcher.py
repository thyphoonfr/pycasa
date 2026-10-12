"""
Picasa Real-time Directory Watcher (CWatcher / ReadDirectoryChangesW).

Surveille en temps réel les dossiers configurés en mode 'Toujours analyser' (Scan Always)
dans repository.dat.
Regroupe les événements avec un délai anti-rebond (debounce) de 500 ms conformément
au binaire original.

Ref: picasa3.exe @ 0x00704F20 (FUN_00704f20 -> ReadDirectoryChangesW, buffer 0x10000, debounce 500 ms)
Ref: picasa3.exe @ 0x008B7F90 (foldermgr/watched_folders)
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer, Signal

from picasa_py.db.database import PicasaDatabase


class PicasaFolderWatcher(QObject):
    """
    Surveillance en temps réel des dossiers de la bibliothèque Picasa.
    Ref: picasa3.exe @ 0x00704F20 (debounce: 500 ms)
    """

    directory_changed = Signal(str)
    scan_requested = Signal(list)  # Liste des répertoires modifiés à analyser

    def __init__(self, db: Optional[PicasaDatabase] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.db = db
        self.watcher = QFileSystemWatcher(self)
        self.watched_paths: Set[str] = set()
        self.pending_changed_paths: Set[str] = set()

        # Minuterie de debounce (500 ms conformément à 0x00704F20)
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(500)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)

        self.watcher.directoryChanged.connect(self._on_directory_changed)
        self.watcher.fileChanged.connect(self._on_file_changed)

        if self.db:
            self.reload_from_database()

    def reload_from_database(self) -> None:
        """Charge les dossiers à surveiller (statut == '1') depuis la base de données."""
        if not self.db:
            return

        watched_dict = self.db.get_watched_folders()
        paths_to_watch: Set[str] = set()
        for folder_path, status in watched_dict.items():
            if status == "1":
                clean_path = folder_path.rstrip("\\/")
                if os.path.isdir(clean_path):
                    paths_to_watch.add(clean_path)

        self.set_watched_directories(list(paths_to_watch))

    def set_watched_directories(self, paths: List[str]) -> None:
        """Remplace l'ensemble des répertoires surveillés."""
        current_dirs = set(self.watcher.directories())
        new_dirs: Set[str] = set()

        for p in paths:
            norm = os.path.abspath(p)
            if os.path.isdir(norm):
                new_dirs.add(norm)
                # Ajouter également les sous-dossiers immédiats pour une réactivité optimale
                try:
                    for entry in os.scandir(norm):
                        if entry.is_dir():
                            new_dirs.add(os.path.abspath(entry.path))
                except Exception:
                    pass

        to_remove = current_dirs - new_dirs
        if to_remove:
            self.watcher.removePaths(list(to_remove))

        to_add = new_dirs - current_dirs
        if to_add:
            self.watcher.addPaths(list(to_add))

        self.watched_paths = new_dirs

    def add_directory(self, path: str) -> None:
        """Ajoute un répertoire à la surveillance."""
        norm = os.path.abspath(path)
        if os.path.isdir(norm) and norm not in self.watched_paths:
            self.watcher.addPath(norm)
            self.watched_paths.add(norm)

    def remove_directory(self, path: str) -> None:
        """Retire un répertoire de la surveillance."""
        norm = os.path.abspath(path)
        if norm in self.watched_paths:
            self.watcher.removePath(norm)
            self.watched_paths.discard(norm)

    def _on_directory_changed(self, path: str) -> None:
        self.pending_changed_paths.add(path)
        self.directory_changed.emit(path)
        # Relance le timer debounce de 500 ms
        self.debounce_timer.start()

    def _on_file_changed(self, path: str) -> None:
        parent_dir = os.path.dirname(path)
        if parent_dir:
            self.pending_changed_paths.add(parent_dir)
        self.debounce_timer.start()

    def _on_debounce_timeout(self) -> None:
        if not self.pending_changed_paths:
            return
        paths_to_scan = list(self.pending_changed_paths)
        self.pending_changed_paths.clear()
        self.scan_requested.emit(paths_to_scan)
