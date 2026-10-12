"""
Resource Manager for loading extracted PE icons, cursors and strings.

Ref: picasa3.exe @ 0x009838D0 (Window icon and cursor initialization)
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QIcon, QPixmap, QCursor
from PySide6.QtCore import QPoint

RES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "resources"


# Ref: picasa3.exe @ 0x009838D0
class PicasaResourceManager:
    """
    Gestionnaire centralisé des ressources graphiques de Picasa.
    """
    _instance: Optional[PicasaResourceManager] = None

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or RES_DIR
        self._icons: Dict[int, QIcon] = {}
        self._cursors: Dict[int, QCursor] = {}
        self._strings: Dict[int, str] = {}
        self._load_strings()

    @classmethod
    def get(cls) -> PicasaResourceManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_strings(self) -> None:
        str_file = self.base_dir / "strings" / "strings.json"
        if str_file.exists():
            data = json.loads(str_file.read_text(encoding="utf-8"))
            self._strings = {int(k): v for k, v in data.items()}

    def get_string(self, str_id: int, default: str = "") -> str:
        return self._strings.get(str_id, default)

    def get_icon(self, group_id: int = 105) -> QIcon:
        """
        Charge une icône PE extraite (ex. 105 = Picasa Main Icon).
        """
        if group_id in self._icons:
            return self._icons[group_id]

        ico_file = self.base_dir / "icons" / f"group_icon_{group_id}.ico"
        if ico_file.exists():
            icon = QIcon(str(ico_file))
        else:
            icon = QIcon()

        self._icons[group_id] = icon
        return icon

    def get_cursor(self, cursor_id: int) -> QCursor:
        """
        Charge un curseur Windows (.cur) extrait avec son point chaud exact.
        """
        if cursor_id in self._cursors:
            return self._cursors[cursor_id]

        cur_file = self.base_dir / "cursors" / f"cursor_{cursor_id}.cur"
        manifest_file = self.base_dir / "cursors" / "cursors.json"
        hx, hy = 0, 0
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            info = manifest.get(str(cursor_id), {})
            hx = info.get("hotspot_x", 0)
            hy = info.get("hotspot_y", 0)

        if cur_file.exists():
            pix = QPixmap(str(cur_file))
            cursor = QCursor(pix, hx, hy)
        else:
            cursor = QCursor()

        self._cursors[cursor_id] = cursor
        return cursor
