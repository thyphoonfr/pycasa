"""
FR: Module de compatibilité et d'énumération des dossiers Picasa 3 (AVytDirScannerWindows).
Ré-exporte les classes et fonctions de picasa_py.scanner.scanner avec support multi-OS
(attributs de fichiers cachés sous Windows via ctypes.windll protégé par sys.platform == 'win32',
et conventions de fichiers cachés POSIX '.' sous Linux et macOS).

EN: Compatibility and directory enumeration module for Picasa 3 (AVytDirScannerWindows).
Re-exports classes and functions from picasa_py.scanner.scanner with cross-platform support
(Windows hidden file attributes via ctypes.windll guarded by sys.platform == 'win32',
and POSIX '.' hidden file conventions on Linux and macOS).

Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List, Set

from picasa_py.scanner.scanner import (
    PicasaDirScanner,
    BackgroundScanWorker,
    SUPPORTED_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    EXTENSION_TYPE_MAP,
    DEFAULT_EXCLUDED_DIRS,
    datetime_to_ole,
    extract_image_metadata_and_thumb,
    extract_video_metadata_and_thumb,
    extract_media_metadata_and_thumb,
    load_directory_filters,
)


def is_hidden_or_system_path(path: str | Path) -> bool:
    """
    FR: Vérifie si un fichier ou dossier possède l'attribut caché/système (Windows FILE_ATTRIBUTE_HIDDEN/SYSTEM
    ou nom commençant par '.' sous Linux/macOS).
    EN: Checks whether a file or directory has the hidden/system attribute (Windows FILE_ATTRIBUTE_HIDDEN/SYSTEM
    or a leading '.' filename on Linux/macOS).
    Ref: picasa3.exe @ 0x00415790 (FindFirstFileW / dwFileAttributes)
    """
    p = str(path)
    base = os.path.basename(p.rstrip("\\/"))
    if base.startswith("."):
        return True
    if sys.platform == "win32" and os.path.exists(p):
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(p)
            if attrs != -1 and (attrs & 0x06):  # FILE_ATTRIBUTE_HIDDEN (0x2) | FILE_ATTRIBUTE_SYSTEM (0x4)
                return True
        except Exception:
            pass
    return False


__all__ = [
    "PicasaDirScanner",
    "BackgroundScanWorker",
    "SUPPORTED_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "EXTENSION_TYPE_MAP",
    "DEFAULT_EXCLUDED_DIRS",
    "datetime_to_ole",
    "extract_image_metadata_and_thumb",
    "extract_video_metadata_and_thumb",
    "extract_media_metadata_and_thumb",
    "load_directory_filters",
    "is_hidden_or_system_path",
]
