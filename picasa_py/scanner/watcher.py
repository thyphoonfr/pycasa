"""
FR: Surveillance en temps réel des répertoires Picasa (CWatcher / ReadDirectoryChangesW).
Surveille en temps réel les dossiers configurés en mode 'Toujours analyser' (Scan Always)
dans repository.dat. Regroupe les événements avec un délai anti-rebond (debounce) de 500 ms
conformément au binaire original.

EN: Picasa Real-time Directory Watcher (CWatcher / ReadDirectoryChangesW).
Monitors in real time the directories configured in 'Scan Always' mode in repository.dat.
Batches filesystem events with a 500 ms debounce delay in accordance with the original binary.

Ref: picasa3.exe @ 0x00704F20 (FUN_00704f20 -> ReadDirectoryChangesW, buffer 0x10000, debounce 500 ms)
Ref: picasa3.exe @ 0x008B7F90 (foldermgr/watched_folders)
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer, Signal

from picasa_py.db.database import PicasaDatabase
from picasa_py.ini.writer import PicasaIniWriter


class PicasaFolderWatcher(QObject):
    """
    FR: Surveillance en temps réel des dossiers de la bibliothèque Picasa (multi-OS via QFileSystemWatcher).
    EN: Real-time monitoring of Picasa library folders (cross-platform via QFileSystemWatcher).
    Ref: picasa3.exe @ 0x00704F20 (debounce: 500 ms)
    """

    directory_changed = Signal(str)
    scan_requested = Signal(list)  # FR: Liste des répertoires modifiés à analyser / EN: List of modified directories to scan

    def __init__(self, db: Optional[PicasaDatabase] = None, parent: Optional[QObject] = None):
        """
        FR: Initialise le surveillant de dossiers et le minuteur anti-rebond de 500 ms.
        EN: Initializes the folder watcher and the 500 ms debounce timer.
        """
        super().__init__(parent)
        self.db = db
        self.watcher = QFileSystemWatcher(self)
        self.watched_paths: Set[str] = set()
        self.pending_changed_paths: Set[str] = set()

        # FR: Minuterie de debounce (500 ms conformément à 0x00704F20)
        # EN: Debounce timer (500 ms in accordance with 0x00704F20)
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(500)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)

        self.watcher.directoryChanged.connect(self._on_directory_changed)
        self.watcher.fileChanged.connect(self._on_file_changed)

        # FR: File d'attente de découverte incrémentale des sous-dossiers pour ne jamais bloquer le thread GUI
        # EN: Incremental subdirectory discovery queue so the GUI thread is never blocked on large folder trees
        self._pending_walk_roots: List[str] = []
        self._walk_chunk_timer = QTimer(self)
        self._walk_chunk_timer.setInterval(8)
        self._walk_chunk_timer.timeout.connect(self._process_next_walk_chunk)

        if self.db:
            self.reload_from_database()

    def _is_excluded_dir_name(self, name: str) -> bool:
        """
        FR: Indique si un nom de sous-dossier doit être ignoré par la surveillance (ex: .git, .picasaoriginals).
        EN: Indicates whether a subdirectory name should be ignored by the watcher (e.g. .git, .picasaoriginals).
        Ref: picasa3.exe @ 0x00415790, 0x0085A0B0 (.picasaoriginals), runtime/filters.txt
        """
        clean = name.strip().lower()
        if not clean or clean.startswith("."):
            return True
        if clean in {
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
            "originals",
            "$recycle.bin",
            "system volume information",
        }:
            return True
        return False

    def reload_from_database(self) -> None:
        """
        FR: Charge les dossiers à surveiller (statut == '1') depuis la base de données,
        avec repli sur les dossiers indexés existants (rec.type == 1) non exclus.
        EN: Loads the folders to watch (status == '1') from the database,
        falling back to existing non-excluded indexed folders (rec.type == 1).
        Ref: picasa3.exe @ 0x00704F20, 0x008B7F90 (foldermgr/watched_folders)
        """
        if not self.db:
            return

        watched_dict = self.db.get_watched_folders()
        excluded_norm: Set[str] = set()
        paths_to_watch: Set[str] = set()
        for folder_path, status in watched_dict.items():
            clean_path = folder_path.rstrip("\\/")
            if os.sep != "\\":
                clean_path = clean_path.replace("\\", os.sep)
            norm_key = os.path.normcase(os.path.abspath(clean_path))
            if status in ("0", "2"):
                excluded_norm.add(norm_key)
            elif status == "1" and os.path.isdir(clean_path):
                paths_to_watch.add(clean_path)

        # Si aucun dossier n'est explicitement en statut '1' dans repository.dat mais que la base
        # contient déjà des dossiers indexés (rec.type == 1) non exclus, les surveiller également.
        if not paths_to_watch and getattr(self.db, "index", None):
            for rec in self.db.index:
                if getattr(rec, "type", 0) == 1 and getattr(rec, "path", ""):
                    clean_p = rec.path.rstrip("\\/")
                    if os.sep != "\\":
                        clean_p = clean_p.replace("\\", os.sep)
                    norm_p = os.path.normcase(os.path.abspath(clean_p))
                    if norm_p not in excluded_norm and os.path.isdir(clean_p):
                        paths_to_watch.add(clean_p)

        self.set_watched_directories(list(paths_to_watch))

    def set_watched_directories(self, paths: List[str]) -> None:
        """
        FR: Remplace l'ensemble des répertoires surveillés. Ajoute immédiatement les répertoires racines
        sans bloquer le thread GUI, puis découvre et ajoute les sous-dossiers par petits lots via
        `_walk_chunk_timer` si l'arborescence est vaste.
        EN: Replaces the set of watched directories. Immediately adds root directories without blocking
        the GUI thread, then discovers and registers subdirectories in small batches via `_walk_chunk_timer`
        if the directory tree is large.
        Ref: picasa3.exe @ 0x00704F20 (ReadDirectoryChangesW avec bWatchSubtree = TRUE)
        """
        self._walk_chunk_timer.stop()
        self._pending_walk_roots.clear()

        current_dirs = set(self.watcher.directories())
        new_dirs: Set[str] = set()
        deferred_roots: List[str] = []
        sync_budget = 40

        for p in paths:
            host_p = p.replace("\\", os.sep) if os.sep != "\\" else p
            norm = os.path.abspath(host_p)
            if os.path.isdir(norm):
                new_dirs.add(norm)
                try:
                    with os.scandir(norm) as it:
                        for entry in it:
                            if entry.is_dir(follow_symlinks=False) and not self._is_excluded_dir_name(entry.name):
                                sub_abs = os.path.abspath(entry.path)
                                new_dirs.add(sub_abs)
                                if sync_budget > 0:
                                    sync_budget -= 1
                                    try:
                                        with os.scandir(sub_abs) as sub_it:
                                            for sub_e in sub_it:
                                                if sub_e.is_dir(follow_symlinks=False) and not self._is_excluded_dir_name(sub_e.name):
                                                    new_dirs.add(os.path.abspath(sub_e.path))
                                                    deferred_roots.append(os.path.abspath(sub_e.path))
                                    except Exception:
                                        pass
                                else:
                                    deferred_roots.append(sub_abs)
                except Exception:
                    pass

        to_remove = current_dirs - new_dirs
        if to_remove:
            self.watcher.removePaths(list(to_remove))

        to_add = new_dirs - current_dirs
        if to_add:
            self.watcher.addPaths(list(to_add))

        self.watched_paths = new_dirs
        if deferred_roots:
            self._pending_walk_roots.extend(deferred_roots)
            self._walk_chunk_timer.start()

    def _process_next_walk_chunk(self) -> None:
        """
        FR: Parcourt un petit lot de sous-dossiers par tick d'horloge (max 25 répertoires)
        afin d'enregistrer les sous-arborescences profondes sans aucun gel de l'interface.
        EN: Processes a small batch of subdirectories per timer tick (max 25 directories)
        to register deep directory trees without any UI freeze.
        """
        if not self._pending_walk_roots:
            self._walk_chunk_timer.stop()
            return

        batch_added: List[str] = []
        processed = 0
        while self._pending_walk_roots and processed < 25:
            curr = self._pending_walk_roots.pop(0)
            processed += 1
            if not os.path.isdir(curr):
                continue
            if curr not in self.watched_paths:
                self.watched_paths.add(curr)
                batch_added.append(curr)
            try:
                with os.scandir(curr) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False) and not self._is_excluded_dir_name(entry.name):
                            sub_abs = os.path.abspath(entry.path)
                            if sub_abs not in self.watched_paths:
                                self.watched_paths.add(sub_abs)
                                batch_added.append(sub_abs)
                            self._pending_walk_roots.append(sub_abs)
            except Exception:
                pass

        if batch_added:
            try:
                self.watcher.addPaths(batch_added)
            except Exception:
                pass

        if not self._pending_walk_roots:
            self._walk_chunk_timer.stop()

    def add_directory(self, path: str) -> None:
        """
        FR: Ajoute un répertoire à la surveillance.
        EN: Adds a directory to the active watch set.
        """
        host_p = path.replace("\\", os.sep) if os.sep != "\\" else path
        norm = os.path.abspath(host_p)
        if os.path.isdir(norm) and norm not in self.watched_paths:
            self.watcher.addPath(norm)
            self.watched_paths.add(norm)

    def remove_directory(self, path: str) -> None:
        """
        FR: Retire un répertoire de la surveillance.
        EN: Removes a directory from the active watch set.
        """
        host_p = path.replace("\\", os.sep) if os.sep != "\\" else path
        norm = os.path.abspath(host_p)
        if norm in self.watched_paths:
            self.watcher.removePath(norm)
            self.watched_paths.discard(norm)

    def _on_directory_changed(self, path: str) -> None:
        """
        FR: Gère la notification de modification d'un dossier et enregistre les nouveaux sous-dossiers directs.
        Ignore immédiatement les notifications provoquées par une écriture `.picasa.ini` interne récente.
        EN: Handles a directory change notification and registers any newly created direct subdirectories.
        Immediately ignores notifications triggered by a recent internal `.picasa.ini` write.
        Ref: picasa3.exe @ 0x00456A15, 0x0068BABA, 0x00704F20
        """
        if PicasaIniWriter.is_recent_internal_write(path, 2.0):
            return
        self.pending_changed_paths.add(path)
        if os.path.isdir(path):
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False) and not self._is_excluded_dir_name(entry.name):
                            norm_sub = os.path.abspath(entry.path)
                            if norm_sub not in self.watched_paths:
                                self.add_directory(norm_sub)
                                self.pending_changed_paths.add(norm_sub)
                                self._pending_walk_roots.append(norm_sub)
                if self._pending_walk_roots and not self._walk_chunk_timer.isActive():
                    self._walk_chunk_timer.start()
            except Exception:
                pass
        self.directory_changed.emit(path)
        # FR: Relance le timer debounce de 500 ms / EN: Restart the 500 ms debounce timer
        self.debounce_timer.start()

    def _on_file_changed(self, path: str) -> None:
        """
        FR: Gère la notification de modification d'un fichier surveillé.
        EN: Handles a file change notification.
        """
        if PicasaIniWriter.is_recent_internal_write(path, 2.0):
            return
        parent_dir = os.path.dirname(path)
        if parent_dir:
            self.pending_changed_paths.add(parent_dir)
        self.debounce_timer.start()

    def _on_debounce_timeout(self) -> None:
        """
        FR: Émet le signal scan_requested avec la liste des dossiers modifiés après expiration du délai de 500 ms.
        EN: Emits the scan_requested signal with the list of modified folders after the 500 ms debounce expires.
        """
        if not self.pending_changed_paths:
            return
        paths_to_scan = list(self.pending_changed_paths)
        self.pending_changed_paths.clear()
        self.scan_requested.emit(paths_to_scan)

