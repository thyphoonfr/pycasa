"""
FR: Gestionnaire de ressources pour le chargement des icônes PE extraites, curseurs et chaînes multilingues.
EN: Resource Manager for loading extracted PE icons, cursors and multilingual strings.

Ref: picasa3.exe @ 0x009838D0 (Window icon and cursor initialization)
"""

from __future__ import annotations
import json
import math
import sys
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QIcon, QPixmap, QCursor, QPainter, QColor, QPen, QPolygonF
from PySide6.QtCore import QPoint, QPointF, Qt


def _resolve_res_dir() -> Path:
    """
    FR: Résout le chemin du répertoire des ressources (ui/resources), depuis les sources
    ou depuis un exécutable autonome PyInstaller (sys._MEIPASS) sur Windows, macOS et Linux.
    EN: Resolves the resources directory path (ui/resources), whether running from source
    or from a standalone PyInstaller executable (sys._MEIPASS) on Windows, macOS, and Linux.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        frozen_dir = Path(meipass) / "ui" / "resources"
        if frozen_dir.exists():
            return frozen_dir
    return Path(__file__).resolve().parent.parent.parent / "ui" / "resources"


RES_DIR = _resolve_res_dir()


# Ref: picasa3.exe @ 0x009838D0
class PicasaResourceManager:
    """
    FR: Gestionnaire centralisé des ressources graphiques et textuelles de Picasa 3.
    EN: Centralized manager for Picasa 3 graphical and text resources.
    """
    _instance: Optional[PicasaResourceManager] = None

    def __init__(self, base_dir: Optional[Path] = None):
        """
        FR: Initialise le gestionnaire de ressources et charge les tables de chaînes et langues.
        EN: Initializes the resource manager and loads string tables and languages.
        """
        self.base_dir = base_dir or _resolve_res_dir()
        self._icons: Dict[int, QIcon] = {}
        self._png_icons: Dict[str, QIcon] = {}
        self._cursors: Dict[int, QCursor] = {}
        self._strings: Dict[int, str] = {}
        self._xml_strings: Dict[str, str] = {}
        self._stringres_cache: Dict[str, Dict[str, str]] = {}
        self._available_languages: list[tuple[str, str]] = []
        self._current_lang: str = "enUS"
        self.on_language_changed_callbacks: list = []
        self._load_strings()
        self._load_languages()
        try:
            from picasa_py.db.preferences import PicasaPreferences
            settings = PicasaPreferences()
            saved_lang = str(settings.value("UI/Language", "") or "").strip()
            if saved_lang and saved_lang != "system":
                self._current_lang = saved_lang
            else:
                self._current_lang = self.resolve_system_language()
        except Exception:
            self._current_lang = self.resolve_system_language()

    def resolve_system_language(self) -> str:
        """
        FR: Résout la langue du système d'exploitation vers un code de langue Picasa.
        EN: Resolves the operating system locale to a Picasa language code.
        Ref: picasa3.exe @ 0x004060B0 (Local::lang)
        """
        try:
            from PySide6.QtCore import QLocale
            loc = QLocale.system().name().replace("_", "-")
            loc_lower = loc.lower()
            if loc_lower.startswith("en-gb") or loc_lower.startswith("en-uk") or loc_lower.startswith("en-au"):
                return "enUK"
            if loc_lower.startswith("en"):
                return "enUS"
            if loc_lower.startswith("pt-br"):
                return "pt-BR"
            if loc_lower.startswith("pt"):
                return "pt"
            if loc_lower.startswith("zh-cn") or loc_lower.startswith("zh-hans") or loc_lower.startswith("zh-sg"):
                return "zh-CN"
            if loc_lower.startswith("zh"):
                return "zh-TW"
            if loc_lower.startswith("he") or loc_lower.startswith("iw"):
                return "iw"
            if loc_lower.startswith("nb") or loc_lower.startswith("nn") or loc_lower.startswith("no"):
                return "no"
            if loc_lower.startswith("tl") or loc_lower.startswith("fil"):
                return "fil"
            primary = loc_lower.split("-")[0]
            avail_codes = {code.lower(): code for code, _ in self._available_languages}
            if primary in avail_codes:
                return avail_codes[primary]
            if primary == "fr":
                return "fr"
        except Exception:
            pass
        return "enUS"

    @classmethod
    def get(cls) -> PicasaResourceManager:
        """
        FR: Retourne l'instance singleton du gestionnaire de ressources.
        EN: Returns the singleton instance of the resource manager.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def instance(cls) -> PicasaResourceManager:
        """
        FR: Alias de get() pour récupérer le singleton.
        EN: Alias for get() to retrieve the singleton instance.
        """
        return cls.get()

    def _load_strings(self) -> None:
        """
        FR: Charge la table des chaînes PE extraites depuis strings/strings.json.
        EN: Loads the extracted PE string table from strings/strings.json.
        """
        str_file = self.base_dir / "strings" / "strings.json"
        if str_file.exists():
            data = json.loads(str_file.read_text(encoding="utf-8"))
            self._strings = {int(k): v for k, v in data.items()}

    def _load_languages(self) -> None:
        r"""
        FR: Charge la liste officielle des 41 langues depuis xml/LANGNAMES.XML.
        EN: Loads the official list of 41 languages from xml/LANGNAMES.XML.
        Ref: picasa3.exe @ 0x004055EF, i18n\langnames.xml
        """
        lang_file = self.base_dir / "xml" / "LANGNAMES.XML"
        if not lang_file.exists():
            return

        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(lang_file)
            root = tree.getroot()
            self._available_languages.clear()
            for sres in root.findall(".//stringres"):
                s_id = sres.attrib.get("id", "")
                xmb = sres.find("xmbtext")
                if s_id.startswith("Lang::") and xmb is not None and xmb.text:
                    code = s_id.replace("Lang::", "")
                    self._available_languages.append((code, xmb.text))
        except Exception:
            pass

    def get_available_languages(self) -> list[tuple[str, str]]:
        """
        FR: Retourne la liste des (code_langue, nom_natif) disponibles.
        EN: Returns the list of available (language_code, native_name) tuples.
        """
        return list(self._available_languages)

    def get_current_language(self) -> str:
        """
        FR: Retourne le code de la langue active (ex: 'fr', 'enUS', 'de', 'es').
        EN: Returns the active language code (e.g., 'fr', 'enUS', 'de', 'es').
        """
        return self._current_lang

    def set_language(self, lang_code: str) -> None:
        """
        FR: Définit la langue active et vide le cache des chaînes XML pour rechargement.
        Si lang_code vaut 'system' ou '', résout la langue du système d'exploitation.
        EN: Sets the active language and clears the XML string cache for reloading.
        If lang_code is 'system' or '', resolves the operating system language.
        Ref: picasa3.exe @ 0x004060B0 (Local::lang)
        """
        resolved = self.resolve_system_language() if (not lang_code or lang_code == "system") else lang_code
        if self._current_lang != resolved:
            self._current_lang = resolved
            self._xml_strings.clear()
            self._stringres_cache.clear()
            for cb in self.on_language_changed_callbacks:
                try:
                    cb(resolved)
                except Exception:
                    pass

    def _get_lang_suffix(self, lang_code: Optional[str] = None) -> str:
        """
        FR: Convertit un code de langue en suffixe de fichier de ressource Picasa.
        Ex: 'enUS' -> '', 'enUK' -> '_EN-GB', 'pt' -> '_PT-PT', 'fr' -> '_FR'.
        EN: Converts a language code to a Picasa resource file suffix.
        E.g., 'enUS' -> '', 'enUK' -> '_EN-GB', 'pt' -> '_PT-PT', 'fr' -> '_FR'.
        """
        code = lang_code or self._current_lang
        if not code or code == "system":
            code = self.resolve_system_language()
        if code == "enUS":
            return ""
        if code == "enUK":
            return "_EN-GB"
        if code == "pt":
            return "_PT-PT"
        if code == "pt-BR":
            return "_PT-BR"
        if code in ("zh-CN", "zh-TW"):
            return f"_{code.upper()}"
        return f"_{code.upper()}"

    def get_string(self, str_id: int, default: str = "") -> str:
        """
        FR: Récupère une chaîne par son identifiant numérique PE.
        EN: Retrieves a string by its numeric PE resource ID.
        """
        return self._strings.get(str_id, default)

    def get_png_icon(self, icon_name: str) -> QIcon:
        """
        FR: Charge une icône PNG par son nom depuis `ui/resources/icons/` (avec ou sans extension `.png`).
            Permet de remplacer ou mettre à jour n'importe quelle icône simplement en modifiant le fichier `.png`.
        EN: Loads a PNG icon by name from `ui/resources/icons/` (with or without `.png` extension).
            Allows replacing or updating any icon simply by editing the `.png` file.
        """
        fname = icon_name if icon_name.lower().endswith(".png") else f"{icon_name}.png"
        if fname in self._png_icons:
            return self._png_icons[fname]
        png_path = self.base_dir / "icons" / fname
        icon = QIcon(str(png_path)) if png_path.exists() else QIcon()
        self._png_icons[fname] = icon
        return icon

    def get_icon(self, group_id: int = 105) -> QIcon:
        """
        FR: Charge une icône par son identifiant de groupe PE (ex. 105 = icône principale Picasa).
            Charge en priorité les fichiers `.png` (`group_icon_<id>_<w>x<h>.png` et `group_icon_<id>.png`)
            depuis `ui/resources/icons/`, avec repli sur `group_icon_<id>.ico`.
        EN: Loads an icon by its PE group ID (e.g., 105 = Picasa Main Icon).
            Prioritizes `.png` files (`group_icon_<id>_<w>x<h>.png` and `group_icon_<id>.png`)
            from `ui/resources/icons/`, falling back to `group_icon_<id>.ico`.
        """
        if group_id in self._icons:
            return self._icons[group_id]

        icons_dir = self.base_dir / "icons"
        stem = f"group_icon_{group_id}"
        primary_png = icons_dir / f"{stem}.png"
        sized_pngs = sorted(icons_dir.glob(f"{stem}_*x*.png"))

        if primary_png.exists() or sized_pngs:
            icon = QIcon()
            for sp in sized_pngs:
                icon.addFile(str(sp))
            if primary_png.exists():
                icon.addFile(str(primary_png))
        else:
            ico_file = icons_dir / f"{stem}.ico"
            icon = QIcon(str(ico_file)) if ico_file.exists() else QIcon()

        self._icons[group_id] = icon
        return icon

    def get_star_icon(self, size: int = 20) -> QIcon:
        """
        FR: Charge l'icône d'étoile dorée Picasa depuis `ui/resources/icons/star_icon.png`
            (avec repli vectoriel QPainter si le fichier `.png` est absent).
        EN: Loads the golden Picasa star icon from `ui/resources/icons/star_icon.png`
            (with vector QPainter fallback if the `.png` file is missing).
        Ref: picasa3.exe @ ID_PICTURE_STAR, star=yes
        """
        star_png = self.base_dir / "icons" / "star_icon.png"
        if star_png.exists():
            src_pix = QPixmap(str(star_png))
            if not src_pix.isNull():
                if src_pix.width() != size or src_pix.height() != size:
                    src_pix = src_pix.scaled(
                        size,
                        size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                return QIcon(src_pix)

        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#B8860B"), 1))
        painter.setBrush(QColor("#FFD700"))
        cx, cy = size / 2.0, size / 2.0
        r_out, r_in = (size / 2.0) - 1.5, ((size / 2.0) - 1.5) * 0.42
        pts = []
        for si in range(10):
            angle = si * math.pi / 5.0 - math.pi / 2.0
            r = r_out if si % 2 == 0 else r_in
            pts.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
        painter.drawPolygon(QPolygonF(pts))
        painter.end()
        return QIcon(pix)

    def get_cursor(self, cursor_id: int) -> QCursor:
        """
        FR: Charge un curseur depuis `ui/resources/cursors/cursor_<id>.png` (en priorité)
            ou `cursor_<id>.cur` avec ses coordonnées exactes de point chaud (`cursors.json`).
        EN: Loads a cursor from `ui/resources/cursors/cursor_<id>.png` (prioritized)
            or `cursor_<id>.cur` with its exact hotspot coordinates (`cursors.json`).
        """
        if cursor_id in self._cursors:
            return self._cursors[cursor_id]

        cursors_dir = self.base_dir / "cursors"
        png_file = cursors_dir / f"cursor_{cursor_id}.png"
        cur_file = cursors_dir / f"cursor_{cursor_id}.cur"
        manifest_file = cursors_dir / "cursors.json"
        hx, hy = 0, 0
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            info = manifest.get(str(cursor_id), {})
            hx = info.get("hotspot_x", 0)
            hy = info.get("hotspot_y", 0)
            custom_png = info.get("png_file")
            if custom_png:
                cand_png = cursors_dir / custom_png
                if cand_png.exists():
                    png_file = cand_png

        if png_file.exists():
            pix = QPixmap(str(png_file))
            cursor = QCursor(pix, hx, hy)
        elif cur_file.exists():
            pix = QPixmap(str(cur_file))
            cursor = QCursor(pix, hx, hy)
        else:
            cursor = QCursor()

        self._cursors[cursor_id] = cursor
        return cursor

    def get_stringres(self, res_id: str, default: str = "") -> str:
        r"""
        FR: Récupère une chaîne traduite depuis STRINGRES.XML ou STRINGRES_{LANG}.XML.
        EN: Retrieves a translated string from STRINGRES.XML or STRINGRES_{LANG}.XML.
        Ref: picasa3.exe @ 0x004055D4, i18n\stringres.xml
        """
        suffix = self._get_lang_suffix()
        cache = self._stringres_cache.get(suffix)
        if cache is None:
            cache = {}
            xml_dir = self.base_dir / "xml"
            res_file = xml_dir / f"STRINGRES{suffix}.XML"
            if not res_file.exists() and suffix:
                res_file = xml_dir / "STRINGRES.XML"

            if res_file.exists():
                import xml.etree.ElementTree as ET
                try:
                    tree = ET.parse(res_file)
                    root = tree.getroot()
                    for sres in root.findall(".//stringres"):
                        s_id = sres.attrib.get("id")
                        xmb = sres.find("xmbtext")
                        if s_id and xmb is not None and xmb.text:
                            cache[s_id] = xmb.text
                except Exception:
                    pass
            self._stringres_cache[suffix] = cache

        return cache.get(res_id, default)

    def get_xml_string(self, xml_id: str, default: str = "") -> str:
        """
        FR: Récupère une chaîne depuis les fichiers XML de ressources (ex: options/tab3.title).
        Recherche en priorité dans la version de la langue active, puis dans le fichier de base,
        puis en anglais (_EN-GB), puis en français (_FR). Ne remplace jamais une clé déjà trouvée.
        EN: Retrieves a string from XML resource files (e.g., options/tab3.title).
        Searches first in the active language file, then in the base file, then in English (_EN-GB),
        then in French (_FR). Never overwrites an already cached key.
        """
        if xml_id in self._xml_strings:
            return self._xml_strings[xml_id]

        if "/" in xml_id:
            prefix = xml_id.split("/")[0].upper()
            xml_dir = self.base_dir / "xml"
            suffix = self._get_lang_suffix()
            candidates = [
                xml_dir / f"{prefix}{suffix}.XML",
                xml_dir / f"{prefix}.XML",
                xml_dir / f"{prefix}_EN-GB.XML",
                xml_dir / f"{prefix}_FR.XML",
                xml_dir / f"TOOLTIPS{suffix}.XML",
                xml_dir / "TOOLTIPS.XML",
                xml_dir / "TOOLTIPS_EN-GB.XML",
                xml_dir / "TOOLTIPS_FR.XML",
            ]
            import xml.etree.ElementTree as ET
            seen: set[Path] = set()
            for cand in candidates:
                if cand in seen or not cand.exists():
                    continue
                seen.add(cand)
                try:
                    tree = ET.parse(cand)
                    root = tree.getroot()
                    for sres in root.findall(".//stringres"):
                        s_id = sres.attrib.get("id")
                        xmb = sres.find("xmbtext")
                        if s_id and xmb is not None and xmb.text and s_id not in self._xml_strings:
                            self._xml_strings[s_id] = xmb.text
                    for act in root.findall(".//action"):
                        target = act.attrib.get("target")
                        prop = act.attrib.get("property", "")
                        xmb = act.find("xmbtext")
                        if target and xmb is not None and xmb.text:
                            if prop == "Tooltip":
                                tip_key = f"{target}.tooltip"
                                if tip_key not in self._xml_strings:
                                    self._xml_strings[tip_key] = xmb.text
                                if target not in self._xml_strings:
                                    self._xml_strings[target] = xmb.text
                            elif target not in self._xml_strings:
                                self._xml_strings[target] = xmb.text
                except Exception:
                    pass

        val = self._xml_strings.get(xml_id, default)
        self._xml_strings[xml_id] = val
        return val

    def get_edit_tab_icon(self, tab_index: int) -> QIcon:
        """
        FR: Charge l'icône officielle des 5 onglets du volet d'édition gauche
            (`editpanel/tab1` .. `editpanel/tab5`) extraite de `runtime/respack.yt` :
            - 0 (`editpanel/tab1`, `layer:editpanel/basic_icon` @ 0x0AB2AE, 15x16) : Clé à molette (Retouches courantes)
            - 1 (`editpanel/tab2`, `layer:editpanel/tuning_icon` @ 0x0AAD8A, 17x18) : Soleil mi-ombre (Réglages)
            - 2 (`editpanel/tab3`, `layer:editpanel/tab3_icon` @ 0x0AA9A9, 20x19) : Pinceau (Effets 1)
            - 3 (`editpanel/tab4`, `layer:editpanel/tab4_icon` @ 0x0AA4EE, 25x19) : Pinceau sur paysage vert (Effets 2)
            - 4 (`editpanel/tab5`, `layer:editpanel/tab5_icon` @ 0x0A9FB1, 25x19) : Pinceau sur ciel bleu (Effets 3)
        EN: Loads the official icon for the 5 left editing panel tabs
            (`editpanel/tab1` .. `editpanel/tab5`) extracted from `runtime/respack.yt`.

        Ref: respack.yt @ tre:editpanel (0x0D04BA..0x0D2200), tre:drawer_tab, TOOLTIPS_FR.XML:231-245
        """
        filenames = {
            0: "editpanel_tab1_basic.png",
            1: "editpanel_tab2_tuning.png",
            2: "editpanel_tab3_fx1.png",
            3: "editpanel_tab4_fx2.png",
            4: "editpanel_tab5_fx3.png",
        }
        fname = filenames.get(tab_index)
        if fname:
            png_path = self.base_dir / "icons" / fname
            if png_path.exists():
                return QIcon(str(png_path))
        return QIcon()

    def get_edit_tool_icon(self, tool_id: str) -> QIcon:
        """
        FR: Charge l'icône officielle d'un outil de l'onglet 1 (`editpanel/tabpanel1`) ou de la pipette
            extraite de `runtime/respack.yt` (`crop`, `straighten`, `redeye`, `enhance`,
            `autolighting`, `autocolor`, `retouch`, `text`, `dropper`).
        EN: Loads the official icon for a Tab 1 tool (`editpanel/tabpanel1`) or neutral dropper
            extracted from `runtime/respack.yt`.

        Ref: respack.yt @ layer:editpanel/button(crop..text) (44x30), layer:globalbuttons/dropper_n
        """
        png_path = self.base_dir / "icons" / f"editpanel_tool_{tool_id}.png"
        if png_path.exists():
            return QIcon(str(png_path))
        return QIcon()

    def get_drawer_toggle_icon(self, panel_name: str, size: int = 18) -> QIcon:
        """
        FR: Charge ou génère l'icône des 4 boutons de bascule du panneau latéral droit
            (thumbui/people_toggle, places_toggle, tags_toggle, properties_toggle).
        EN: Loads or generates the icon for the 4 right-side drawer toggle buttons
            (thumbui/people_toggle, places_toggle, tags_toggle, properties_toggle).

        Ref: picasa3.exe @ 0x005D96D4..0x005D9E54, respack.yt @ layer:thumbui/*_icon, TOOLTIPS_FR.XML:858-869
        """
        png_map = {
            "people": "thumbui_people_icon.png",
            "places": "thumbui_places_icon.png",
            "tags": "thumbui_tags_icon.png",
            "properties": "thumbui_properties_icon.png",
        }
        fname = png_map.get(panel_name)
        if fname:
            png_path = self.base_dir / "icons" / fname
            if png_path.exists():
                return QIcon(str(png_path))

        from PySide6.QtGui import QPainterPath, QFont
        from PySide6.QtCore import QRectF
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if panel_name == "people":
            # FR: Silhouette buste et tête (thumbui/people_toggle @ 0x00C964BC)
            # EN: Head and shoulders silhouette (thumbui/people_toggle @ 0x00C964BC)
            painter.setPen(QPen(QColor("#3A6EA5"), 1.2))
            painter.setBrush(QColor("#6FA8DC"))
            painter.drawEllipse(QPointF(size * 0.5, size * 0.32), size * 0.19, size * 0.19)
            path = QPainterPath()
            path.moveTo(size * 0.18, size * 0.86)
            path.quadTo(size * 0.18, size * 0.55, size * 0.50, size * 0.55)
            path.quadTo(size * 0.82, size * 0.55, size * 0.82, size * 0.86)
            path.closeSubpath()
            painter.drawPath(path)
        elif panel_name == "places":
            # FR: Marqueur de carte goutte d'eau rouge/orange (thumbui/places_toggle @ 0x00C964D4)
            # EN: Red/orange map pin teardrop marker (thumbui/places_toggle @ 0x00C964D4)
            painter.setPen(QPen(QColor("#992B15"), 1.2))
            painter.setBrush(QColor("#E04B2B"))
            path = QPainterPath()
            cx = size * 0.5
            r = size * 0.26
            cy = size * 0.36
            path.moveTo(cx, size * 0.88)
            path.quadTo(cx - r * 1.15, cy + r * 0.4, cx - r, cy)
            path.arcTo(QRectF(cx - r, cy - r, r * 2, r * 2), 180, -180)
            path.quadTo(cx + r * 1.15, cy + r * 0.4, cx, size * 0.88)
            path.closeSubpath()
            painter.drawPath(path)
            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), size * 0.09, size * 0.09)
        elif panel_name == "tags":
            # FR: Étiquette de mot-clé inclinée avec œillet (thumbui/tags_toggle @ 0x00C964EC)
            # EN: Angled keyword price/luggage tag with eyelet (thumbui/tags_toggle @ 0x00C964EC)
            painter.setPen(QPen(QColor("#8A6D1B"), 1.2))
            painter.setBrush(QColor("#F1C232"))
            pts = [
                QPointF(size * 0.16, size * 0.50),
                QPointF(size * 0.50, size * 0.16),
                QPointF(size * 0.82, size * 0.18),
                QPointF(size * 0.84, size * 0.50),
                QPointF(size * 0.50, size * 0.84),
            ]
            painter.drawPolygon(QPolygonF(pts))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(size * 0.67, size * 0.33), size * 0.07, size * 0.07)
        else:
            # FR: Badge circulaire bleu « i » d'information EXIF (thumbui/properties_toggle @ 0x00C94F88)
            # EN: Circular blue "i" EXIF info badge (thumbui/properties_toggle @ 0x00C94F88)
            painter.setPen(QPen(QColor("#24527A"), 1.2))
            painter.setBrush(QColor("#3D85C6"))
            painter.drawEllipse(QPointF(size * 0.5, size * 0.5), size * 0.36, size * 0.36)
            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Georgia", max(8, int(size * 0.52)), QFont.Weight.Bold)
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "i")

        painter.end()
        return QIcon(pix)

    def get_2up_button_icon(self, kind: str, size: int = 18) -> QIcon:
        """
        FR: Charge ou génère l'icône des boutons de comparaison 2-Up :
            - 'swap_layout_horiz' / 'swap_layout_vert' (editpanel/swap_2up_layout @ 0x00C8ED18, FUN_00569720)
            - 'swap_focus' (editpanel/swap_2up_focus @ 0x00C8ECFC, FUN_0056A160)
        EN: Loads or generates the icon for the 2-Up comparison buttons:
            - 'swap_layout_horiz' / 'swap_layout_vert' (editpanel/swap_2up_layout @ 0x00C8ED18, FUN_00569720)
            - 'swap_focus' (editpanel/swap_2up_focus @ 0x00C8ECFC, FUN_0056A160)

        Ref: picasa3.exe @ 0x00569620..0x0056A950, respack.yt @ layer:editpanel/swap_2up_*_icon
        """
        png_map = {
            "swap_focus": "editpanel_swap_2up_focus_icon.png",
            "swap_layout_vert": "editpanel_swap_2up_layout_icon.png",
            "swap_layout_horiz": "editpanel_swap_2up_layout_horiz_icon.png",
            "only_1up": "editpanel_only_1up_icon.png",
            "ab_2up": "editpanel_ab_2up_icon.png",
            "aa_2up": "editpanel_aa_2up_icon.png",
        }
        fname = png_map.get(kind)
        if fname:
            png_path = self.base_dir / "icons" / fname
            if png_path.exists():
                return QIcon(str(png_path))

        from PySide6.QtCore import QRectF
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if kind == "swap_layout_vert":
            # FR: Division horizontale haut/bas (pour basculer vers vertical/horizontal)
            # EN: Top/bottom split icon
            painter.setPen(QPen(QColor("#D0D7DE"), 1.2))
            painter.setBrush(QColor("#4A76A8"))
            painter.drawRect(QRectF(2, 2, size - 4, (size - 6) / 2))
            painter.setBrush(QColor("#2F4F75"))
            painter.drawRect(QRectF(2, size / 2 + 1, size - 4, (size - 6) / 2))
        elif kind == "swap_layout_horiz":
            # FR: Division côte à côte gauche/droite
            # EN: Left/right split icon
            painter.setPen(QPen(QColor("#D0D7DE"), 1.2))
            painter.setBrush(QColor("#4A76A8"))
            painter.drawRect(QRectF(2, 2, (size - 6) / 2, size - 4))
            painter.setBrush(QColor("#2F4F75"))
            painter.drawRect(QRectF(size / 2 + 1, 2, (size - 6) / 2, size - 4))
        else:
            # FR: Bascule du focus entre l'image A et l'image B (editpanel/swap_2up_focus)
            # EN: Focus toggle between Pane A and Pane B (editpanel/swap_2up_focus)
            painter.setPen(QPen(QColor("#FFD700"), 1.5))
            painter.setBrush(QColor("#3879D9"))
            painter.drawRect(QRectF(1.5, 3, (size - 5) / 2, size - 6))
            painter.setPen(QPen(QColor("#9EA7B3"), 1.0))
            painter.setBrush(QColor("#3A3F47"))
            painter.drawRect(QRectF(size / 2 + 1, 3, (size - 5) / 2, size - 6))
            # Petite double flèche d'échange
            painter.setPen(QPen(QColor("#FFFFFF"), 1.4))
            painter.drawLine(QPointF(size * 0.32, size * 0.5), QPointF(size * 0.68, size * 0.5))

        painter.end()
        return QIcon(pix)



