"""
FR : Système de thèmes, métriques et constantes de couleurs d'interface pour PyCasa.
EN : UI Styling, metrics, color constants and Theme System for PyCasa.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2]
Ref: picasa3.exe @ 0x009BE730 (INI parsing engine)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Tuple
from PySide6.QtGui import QColor
from picasa_py.ini.parser import PicasaIniParser

RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "resources"
STYLE_FILE = RESOURCES_DIR / "style" / "constants.ui"
THEMES_DIR = RESOURCES_DIR / "themes"


def _parse_color(c_str: str, default: str = "#000000") -> QColor:
    """
    FR : Convertit une chaîne de couleur hexadécimale ('#RRGGBB' ou '0xAARRGGBB') en QColor.
    EN : Parses a hexadecimal color string ('#RRGGBB' or '0xAARRGGBB') into a QColor.
    """
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
    """
    FR : Constantes exactes de couleurs, polices et dimensions extraites de `runtime/constants.ui`
    avec prise en charge des thèmes dynamiques (`original`, `dark`, `ocean`, `sepia_warm`, `emerald_forest`).
    EN : Exact color, font, and dimension constants extracted from `runtime/constants.ui`
    with support for dynamic themes (`original`, `dark`, `ocean`, `sepia_warm`, `emerald_forest`).
    """
    _instance: ClassVar[Optional["PicasaStyle"]] = None

    theme_id: str = "original"
    theme_name: str = "Picasa 3 Original (Clair)"
    is_dark: bool = False

    # --- Album List (Panneau latéral gauche / Left panel) ---
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
    alist_textcolor: QColor = field(default_factory=lambda: QColor("#222222"))

    # --- Album Label / Header (En-têtes d'albums et dossiers / Album & Folder headers) ---
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

    # --- Thumbnail Layout & Grid (Disposition et grille des vignettes) ---
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
    alayout_subtitleColor: QColor = field(default_factory=lambda: QColor("#5C534E"))

    # --- Thumbnail Selection & Cards (Sélection et cartes de vignettes) ---
    # Ref: constants.ui: thumbsel_*
    thumbsel_color1: QColor = field(default_factory=lambda: QColor("#009EFF"))
    thumbsel_color2: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    thumb_card_bgcolor: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    thumb_label_color: QColor = field(default_factory=lambda: QColor("#222222"))

    # --- Background & UI Chrome (Arrière-plan et habillage général) ---
    window_bgcolor: QColor = field(default_factory=lambda: QColor(0xF0, 0xF0, 0xF0))
    grid_bgcolor: QColor = field(default_factory=lambda: QColor(0xE0, 0xE0, 0xE0))
    topbar_grad_start: QColor = field(default_factory=lambda: QColor("#F7F7F7"))
    topbar_grad_end: QColor = field(default_factory=lambda: QColor("#E1E1E1"))
    topbar_border_color: QColor = field(default_factory=lambda: QColor("#B6B6B6"))
    topbar_text_color: QColor = field(default_factory=lambda: QColor("#222222"))
    topbar_btn_bg_start: QColor = field(default_factory=lambda: QColor("#FDFDFD"))
    topbar_btn_bg_end: QColor = field(default_factory=lambda: QColor("#DCDCDC"))
    topbar_btn_border: QColor = field(default_factory=lambda: QColor("#9A9A9A"))
    splitter_color: QColor = field(default_factory=lambda: QColor("#D6D6D6"))
    statusbar_bgcolor: QColor = field(default_factory=lambda: QColor("#E6E6E6"))
    statusbar_text_color: QColor = field(default_factory=lambda: QColor("#555555"))

    tray_bgcolor: QColor = field(default_factory=lambda: QColor("#E4E1D8"))
    tray_grad_start: QColor = field(default_factory=lambda: QColor("#F3F1EB"))
    tray_grad_end: QColor = field(default_factory=lambda: QColor("#DCD8CD"))
    tray_text_color: QColor = field(default_factory=lambda: QColor("#222222"))
    drawer_bgcolor: QColor = field(default_factory=lambda: QColor("#EDEAE4"))
    drawer_header_start: QColor = field(default_factory=lambda: QColor("#F7F5F0"))
    drawer_header_end: QColor = field(default_factory=lambda: QColor("#DFDCD4"))
    accent_color: QColor = field(default_factory=lambda: QColor("#25648B"))

    @classmethod
    def instance(cls) -> "PicasaStyle":
        """
        FR : Retourne l'instance singleton du thème PicasaStyle actif (la charge depuis les préférences si nécessaire).
        EN : Returns the singleton instance of the active PicasaStyle theme (loading it from preferences if needed).
        """
        if cls._instance is None:
            try:
                from picasa_py.db.preferences import PicasaPreferences
                prefs = PicasaPreferences()
                saved_theme = str(prefs.value("UI/Theme", "original") or "original")
            except Exception:
                saved_theme = "original"
            cls._instance = cls.load_theme(saved_theme)
        return cls._instance

    @classmethod
    def list_available_themes(cls) -> List[Tuple[str, str, Path]]:
        """
        FR : Retourne la liste des thèmes disponibles dans `ui/resources/themes/`
        sous la forme `[(theme_id, theme_name, path), ...]`, avec 'original' en premier.
        EN : Returns the list of available themes in `ui/resources/themes/`
        as `[(theme_id, theme_name, path), ...]`, with 'original' first.
        """
        themes: List[Tuple[str, str, Path]] = []
        if THEMES_DIR.exists():
            for ini_file in sorted(THEMES_DIR.glob("*.ini")):
                try:
                    doc = PicasaIniParser.parse_file(str(ini_file))
                    sec = doc.get_section("Picasa2")
                    t_id = (sec.get("theme_id") if sec else None) or ini_file.stem
                    t_name = (sec.get("theme_name") if sec else None) or ini_file.stem.replace("_", " ").title()
                    themes.append((t_id.strip(), t_name.strip(), ini_file))
                except Exception:
                    continue

        # FR : Placer 'original' en tête, puis 'dark', puis le reste par ordre alphabétique
        # EN : Place 'original' first, then 'dark', then the rest alphabetically
        order_priority = {"original": 0, "dark": 1, "ocean": 2, "sepia_warm": 3, "emerald_forest": 4}
        themes.sort(key=lambda item: (order_priority.get(item[0], 99), item[1].lower()))
        if not themes:
            themes.append(("original", "Picasa 3 Original (Clair)", STYLE_FILE))
        return themes

    @classmethod
    def load_theme(cls, theme_id: str = "original") -> "PicasaStyle":
        """
        FR : Charge un thème par son identifiant (`original`, `dark`, `ocean`, `sepia_warm`, `emerald_forest`,
        ou tout fichier `<theme_id>.ini` présent dans `ui/resources/themes/`) et met à jour l'instance active.
        EN : Loads a theme by its identifier (`original`, `dark`, `ocean`, `sepia_warm`, `emerald_forest`,
        or any `<theme_id>.ini` file in `ui/resources/themes/`) and updates the active singleton instance.
        """
        clean_id = (theme_id or "original").strip()
        if clean_id == "original" and not (THEMES_DIR / "original.ini").exists():
            style = cls.load(STYLE_FILE)
            cls._instance = style
            return style

        candidate = THEMES_DIR / f"{clean_id}.ini"
        if candidate.exists():
            style = cls.load(candidate)
            cls._instance = style
            return style

        for t_id, _t_name, t_path in cls.list_available_themes():
            if t_id.lower() == clean_id.lower():
                style = cls.load(t_path)
                cls._instance = style
                return style

        style = cls.load(STYLE_FILE)
        cls._instance = style
        return style

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PicasaStyle":
        """
        FR : Charge et interprète `constants.ui` ou un fichier `.ini` de thème Picasa 3.
        EN : Loads and parses `constants.ui` or a Picasa 3 theme `.ini` file.
        """
        target = path or STYLE_FILE
        if not target.exists():
            style = cls()
            if cls._instance is None:
                cls._instance = style
            return style

        # FR : Charger d'abord les valeurs de base depuis constants.ui si on charge un thème personnalisé
        # EN : Load base values from constants.ui first when loading a custom theme
        base_sec = None
        if target != STYLE_FILE and STYLE_FILE.exists():
            try:
                base_doc = PicasaIniParser.parse_file(str(STYLE_FILE))
                base_sec = base_doc.get_section("Picasa2")
            except Exception:
                base_sec = None

        doc = PicasaIniParser.parse_file(str(target))
        sec = doc.get_section("Picasa2")
        if not sec:
            style = cls()
            if cls._instance is None:
                cls._instance = style
            return style

        def _get_raw(k: str) -> Optional[str]:
            v = sec.get(k)
            if v is not None:
                return v
            if base_sec is not None:
                return base_sec.get(k)
            return None

        def _int(k: str, default: int) -> int:
            val = _get_raw(k)
            try:
                return int(val) if val is not None else default
            except ValueError:
                return default

        def _col(k: str, default_hex: str) -> QColor:
            val = _get_raw(k)
            return _parse_color(val, default_hex) if val is not None else QColor(default_hex)

        def _str(k: str, default_str: str) -> str:
            val = _get_raw(k)
            return val.strip() if val is not None else default_str

        is_dark_flag = _int("is_dark", 0) != 0

        style = cls(
            theme_id=_str("theme_id", "original"),
            theme_name=_str("theme_name", "Picasa 3 Original (Clair)"),
            is_dark=is_dark_flag,
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
            alist_textcolor=_col("alist_textcolor", "#222222"),
            alabel_hicol=_col("alabel_hicol", "#f2f2f2"),
            alabel_fldrcol=_col("alabel_fldrcol", "#e2e2e2"),
            alabel_fldrhicol=_col("alabel_fldrhicol", "#f2f2f2"),
            alabel_albumcol=_col("alabel_albumcol", "#e2e2e2"),
            alabel_albumhicol=_col("alabel_albumhicol", "#f2f2f2"),
            alabel_buttfont_win=_str("alabel_buttfont_win", "Segoe UI"),
            alabel_buttfontSize_win=_int("alabel_buttfontSize_win", 12),
            alabel_lighttext=_col("alabel_lighttext", "#FFFFFF"),
            alabel_darktext=_col("alabel_darktext", "#000000"),
            alabel_iconoffsetx=_int("alabel_iconoffsetx", 12),
            alabel_iconoffsety=_int("alabel_iconoffsety", 8),
            alabel_subhead=_int("alabel_subhead", 20),
            alayout_gutter=_int("alayout_gutter", 24),
            alayout_thumbGutterX=_int("alayout_thumbGutterX", 12),
            alayout_thumbGutterY=_int("alayout_thumbGutterY", 22),
            alayout_titleFont=_str("alayout_titleFont", "Georgia"),
            alayout_titleSize=_int("alayout_titleSize", 20),
            alayout_titleColor=_col("alayout_titleColor", "#634B45"),
            alayout_titleOffsetX=_int("alayout_titleOffsetX", 28),
            alayout_bodyFont=_str("alayout_bodyFont", "Georgia"),
            alayout_bodySize=_int("alayout_bodySize", 14),
            alayout_bodyOffset=_int("alayout_bodyOffset", 0),
            alayout_subtitleColor=_col("alayout_subtitleColor", "#5C534E"),
            thumbsel_color1=_col("thumbsel_color1", "#009EFF"),
            thumbsel_color2=_col("thumbsel_color2", "#FFFFFF"),
            thumb_card_bgcolor=_col("thumb_card_bgcolor", "#FFFFFF"),
            thumb_label_color=_col("thumb_label_color", "#222222"),
            window_bgcolor=_col("window_bgcolor", "#F0F0F0"),
            grid_bgcolor=_col("grid_bgcolor", "#E0E0E0"),
            topbar_grad_start=_col("topbar_grad_start", "#F7F7F7"),
            topbar_grad_end=_col("topbar_grad_end", "#E1E1E1"),
            topbar_border_color=_col("topbar_border_color", "#B6B6B6"),
            topbar_text_color=_col("topbar_text_color", "#222222"),
            topbar_btn_bg_start=_col("topbar_btn_bg_start", "#FDFDFD"),
            topbar_btn_bg_end=_col("topbar_btn_bg_end", "#DCDCDC"),
            topbar_btn_border=_col("topbar_btn_border", "#9A9A9A"),
            splitter_color=_col("splitter_color", "#D6D6D6"),
            statusbar_bgcolor=_col("statusbar_bgcolor", "#E6E6E6"),
            statusbar_text_color=_col("statusbar_text_color", "#555555"),
            tray_bgcolor=_col("tray_bgcolor", "#2E3136"),
            tray_grad_start=_col("tray_grad_start", "#3E424A"),
            tray_grad_end=_col("tray_grad_end", "#282B31"),
            tray_text_color=_col("tray_text_color", "#EEEEEE"),
            drawer_bgcolor=_col("drawer_bgcolor", "#24272D"),
            drawer_header_start=_col("drawer_header_start", "#383C45"),
            drawer_header_end=_col("drawer_header_end", "#282B31"),
            accent_color=_col("accent_color", "#25648B"),
        )
        cls._instance = style
        return style

