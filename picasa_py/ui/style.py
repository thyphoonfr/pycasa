"""
UI Styling, metrics and color constants for PyCasa.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2]
Ref: picasa3.exe @ 0x009BE730 (INI parsing engine)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from PySide6.QtGui import QColor, QFont
from picasa_py.ini.parser import PicasaIniParser

STYLE_FILE = Path(__file__).resolve().parent.parent.parent / "ui" / "resources" / "style" / "constants.ui"


def _parse_color(c_str: str, default: str = "#000000") -> QColor:
    c_str = (c_str or default).strip()
    if c_str.startswith("0x") or c_str.startswith("0X"):
        val = int(c_str, 16)
        a = (val >> 24) & 0xFF
        r = (val >> 16) & 0xFF
        g = (val >> 8) & 0xFF
        b = val & 0xFF
        return QColor(r, g, b, a)
    elif c_str.startswith("#"):
        return QColor(c_str)
    return QColor(default)


# Ref: constants.ui [Picasa2]
@dataclass
class PicasaStyle:
    # --- Album List (Left panel) ---
    # Ref: constants.ui: alist_*
    alist_height: int = 22
    alist_fontsize_win: int = 14
    alist_indent: int = 17
    alist_bgcolor: QColor = field(default_factory=lambda: QColor(0xF3, 0xF3, 0xF3))
    alist_hicolor_win: QColor = field(default_factory=lambda: QColor(0x83, 0xA7, 0xBD))
    alist_hicolor2_win: QColor = field(default_factory=lambda: QColor(0xE5, 0xE2, 0xDA))
    alist_selcolor_win: QColor = field(default_factory=lambda: QColor(0x25, 0x64, 0x8B))
    alist_catcolor: QColor = field(default_factory=lambda: QColor(0xED, 0xEA, 0xE4))
    alist_scatcolor: QColor = field(default_factory=lambda: QColor(0x25, 0x64, 0x8B))
    alist_dotcolor: QColor = field(default_factory=lambda: QColor(0xBE, 0xBE, 0xBE))
    alist_stickycolor: QColor = field(default_factory=lambda: QColor(0xEA, 0xE7, 0xDC))

    # --- Album Label / Header ---
    # Ref: constants.ui: alabel_*
    alabel_hicol: QColor = field(default_factory=lambda: QColor("#f2f2f2"))
    alabel_fldrcol: QColor = field(default_factory=lambda: QColor("#e2e2e2"))
    alabel_fldrhicol: QColor = field(default_factory=lambda: QColor("#f2f2f2"))
    alabel_albumcol: QColor = field(default_factory=lambda: QColor("#e2e2e2"))
    alabel_albumhicol: QColor = field(default_factory=lambda: QColor("#f2f2f2"))
    alabel_buttfont_win: str = "Segoe UI"
    alabel_buttfontSize_win: int = 12
    alabel_lighttext: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    alabel_darktext: QColor = field(default_factory=lambda: QColor("#000000"))
    alabel_iconoffsetx: int = 12
    alabel_iconoffsety: int = 8
    alabel_subhead: int = 20

    # --- Thumbnail Layout & Grid ---
    # Ref: constants.ui: alayout_*
    alayout_gutter: int = 24
    alayout_thumbGutterX: int = 12
    alayout_thumbGutterY: int = 22
    alayout_titleFont: str = "Georgia"
    alayout_titleSize: int = 20
    alayout_titleColor: QColor = field(default_factory=lambda: QColor("#634B45"))
    alayout_titleOffsetX: int = 28
    alayout_bodyFont: str = "Georgia"
    alayout_bodySize: int = 14
    alayout_bodyOffset: int = 0

    # --- Thumbnail Selection ---
    # Ref: constants.ui: thumbsel_*
    thumbsel_color1: QColor = field(default_factory=lambda: QColor("#009EFF"))
    thumbsel_color2: QColor = field(default_factory=lambda: QColor("#FFFFFF"))

    # --- Background & UI Chrome ---
    window_bgcolor: QColor = field(default_factory=lambda: QColor(0xF0, 0xF0, 0xF0))
    grid_bgcolor: QColor = field(default_factory=lambda: QColor(0xE0, 0xE0, 0xE0))
    tray_bgcolor: QColor = field(default_factory=lambda: QColor(0x2E, 0x31, 0x36))
    tray_text_color: QColor = field(default_factory=lambda: QColor(0xEE, 0xEE, 0xEE))

    @classmethod
    def load(cls, path: Optional[Path] = None) -> PicasaStyle:
        target = path or STYLE_FILE
        if not target.exists():
            return cls()

        doc = PicasaIniParser.parse_file(str(target))
        sec = doc.get_section("Picasa2")
        if not sec:
            return cls()

        def _int(k: str, default: int) -> int:
            val = sec.get(k)
            try:
                return int(val) if val is not None else default
            except ValueError:
                return default

        def _col(k: str, default_hex: str) -> QColor:
            val = sec.get(k)
            return _parse_color(val, default_hex) if val is not None else QColor(default_hex)

        return cls(
            alist_height=_int("alist_height", 22),
            alist_fontsize_win=_int("alist_fontsize_win", 14),
            alist_indent=_int("alist_indent", 17),
            alist_bgcolor=_col("alist_bgcolor", "#F3F3F3"),
            alist_hicolor_win=_col("alist_hicolor_win", "#83A7BD"),
            alist_hicolor2_win=_col("alist_hicolor2_win", "#E5E2DA"),
            alist_selcolor_win=_col("alist_selcolor_win", "#25648B"),
            alist_catcolor=_col("alist_catcolor", "#EDEAE4"),
            alist_scatcolor=_col("alist_scatcolor", "#25648B"),
            alist_dotcolor=_col("alist_dotcolor", "#BEBEBE"),
            alist_stickycolor=_col("alist_stickycolor", "#EAE7DC"),
            alabel_hicol=_col("alabel_hicol", "#f2f2f2"),
            alabel_fldrcol=_col("alabel_fldrcol", "#e2e2e2"),
            alabel_fldrhicol=_col("alabel_fldrhicol", "#f2f2f2"),
            alabel_albumcol=_col("alabel_albumcol", "#e2e2e2"),
            alabel_albumhicol=_col("alabel_albumhicol", "#f2f2f2"),
            alabel_buttfont_win=sec.get("alabel_buttfont_win", "Segoe UI"),
            alabel_buttfontSize_win=_int("alabel_buttfontSize_win", 12),
            alabel_lighttext=_col("alabel_lighttext", "#FFFFFF"),
            alabel_darktext=_col("alabel_darktext", "#000000"),
            alabel_iconoffsetx=_int("alabel_iconoffsetx", 12),
            alabel_iconoffsety=_int("alabel_iconoffsety", 8),
            alabel_subhead=_int("alabel_subhead", 20),
            alayout_gutter=_int("alayout_gutter", 24),
            alayout_thumbGutterX=_int("alayout_thumbGutterX", 12),
            alayout_thumbGutterY=_int("alayout_thumbGutterY", 22),
            alayout_titleFont=sec.get("alayout_titleFont", "Georgia"),
            alayout_titleSize=_int("alayout_titleSize", 20),
            alayout_titleColor=_col("alayout_titleColor", "#634B45"),
            alayout_titleOffsetX=_int("alayout_titleOffsetX", 28),
            alayout_bodyFont=sec.get("alayout_bodyFont", "Georgia"),
            alayout_bodySize=_int("alayout_bodySize", 14),
            alayout_bodyOffset=_int("alayout_bodyOffset", 0),
            thumbsel_color1=_col("thumbsel_color1", "#009EFF"),
            thumbsel_color2=_col("thumbsel_color2", "#FFFFFF"),
        )
