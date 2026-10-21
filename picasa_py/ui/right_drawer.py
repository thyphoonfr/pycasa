"""
FR: Composant de tiroir latéral droit escamotable pour PyCasa.
Contient les 4 volets caractéristiques de Picasa 3 :
1. Personnes (People Panel, détection de visages, identification et ajout manuel)
2. Lieux (Places Panel avec carte interactive Leaflet / OpenStreetMap)
3. Tags (Tag Panel, mots-clés, tags rapides et persistance .picasa.ini)
4. Propriétés (Image Properties / Données EXIF complètes)

EN: Collapsible Right Drawer Component for PyCasa.
Contains the 4 characteristic Picasa 3 panels:
1. People (People Panel, face detection, identification, and manual addition)
2. Places (Places Panel with interactive Leaflet / OpenStreetMap map)
3. Tags (Tag Panel, keywords, quick tags, and .picasa.ini persistence)
4. Properties (Image Properties / Full EXIF metadata)

Ref: picasa3.exe @ RIGHTDRAWERPANEL_TEXT.XML, IMAGEPROPERTIES.XML, imageproperties.fen
Ref: picasa3.exe @ PEOPLEPANEL_TEXT_FR.XML, GEOPANELTEXT_FR.XML, TAGPANEL_TEXT_FR.XML
Ref: picasa3.exe @ thumbui/people_toggle, places_toggle, tags_toggle, properties_toggle
Ref: AGENTS.md §4 bis (Disposition et fonctionnement identiques à l'original)
"""

from __future__ import annotations
import os
import io
import json
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QLineEdit, QScrollArea, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QButtonGroup,
    QSizePolicy, QMessageBox, QCompleter
)
from PySide6.QtCore import Qt, Signal, QSize, QThread
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush, QPen, QKeyEvent, QPainterPath
from PySide6.QtWebEngineWidgets import QWebEngineView
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.exif_reader import extract_full_metadata, format_gps_dms
from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import _face_overlap
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.ui.name_face_dialog import PicasaNameFaceDialog
from picasa_py.ui.histogram_widget import PicasaHistogramWidget

_EXIF_META_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _get_cached_full_metadata(file_path: str) -> Dict[str, Any]:
    """
    FR: Récupère les métadonnées EXIF complètes avec mise en cache par (chemin, mtime).
    EN: Retrieves full EXIF metadata cached by (path, mtime).
    """
    if not file_path or not os.path.exists(file_path):
        return extract_full_metadata(file_path)
    try:
        mtime = os.path.getmtime(file_path)
        cached = _EXIF_META_CACHE.get(file_path)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        meta = extract_full_metadata(file_path)
        if len(_EXIF_META_CACHE) >= 512:
            _EXIF_META_CACHE.clear()
        _EXIF_META_CACHE[file_path] = (mtime, meta)
        return meta
    except Exception:
        return extract_full_metadata(file_path)


# =============================================================================
# 1. VOLET DES PERSONNES / PEOPLE PANEL
# =============================================================================
class FaceCardFrame(QFrame):
    """
    FR: Cadre de carte de visage supportant le survol et le clic pour mettre en valeur
    le cadre correspondant sur l'image ou naviguer vers l'album.
    EN: Face card frame supporting hover and click to highlight the corresponding
    face box on the image or navigate to the person album.
    Ref: picasa3.exe @ peoplepanel/peoplelist
    """
    def __init__(self, idx: int, on_hover=None, on_leave=None, on_click=None, parent: Optional[QWidget] = None):
        """
        FR: Initialise la carte de visage avec son index et ses callbacks d'interaction.
        EN: Initializes the face card with its index and interaction callbacks.
        """
        super().__init__(parent)
        self.idx = idx
        self.on_hover = on_hover
        self.on_leave = on_leave
        self.on_click = on_click

    def enterEvent(self, event):
        """
        FR: Déclenche le callback de survol lorsque le curseur entre dans la carte.
        EN: Triggers the hover callback when the cursor enters the card.
        """
        super().enterEvent(event)
        if self.on_hover:
            self.on_hover(self.idx)

    def leaveEvent(self, event):
        """
        FR: Déclenche le callback de sortie lorsque le curseur quitte la carte.
        EN: Triggers the leave callback when the cursor leaves the card.
        """
        super().leaveEvent(event)
        if self.on_leave:
            self.on_leave(self.idx)

    def mousePressEvent(self, event):
        """
        FR: Déclenche le callback de clic lors d'un appui souris sur la carte.
        EN: Triggers the click callback when the mouse is pressed on the card.
        """
        super().mousePressEvent(event)
        if self.on_click:
            self.on_click(self.idx)


class PicasaInlineNameEdit(QLineEdit):
    """
    FR: Champ de saisie en ligne de nom de personne pour le volet latéral.
    Supporte la complétion automatique des contacts, la validation par Entrée et l'annulation par Échap.
    EN: Inline person name input field for the side panel.
    Supports contact autocompletion, Enter confirmation, and Escape cancellation.
    Ref: picasa3.exe @ peoplepanel/editbox, peoplepanel/peopleautocomplete
    Ref: picasa3.exe @ 0x00646B48, 0x00646CAA (SendMessageW EM_SETSEL)
    """
    escape_pressed = Signal()

    def __init__(
        self,
        text: str = "",
        placeholder: str = "",
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        """
        FR: Initialise le champ de saisie en ligne avec texte, espace réservé et style.
        EN: Initializes the inline input field with text, placeholder, and style.
        """
        super().__init__(text, parent)
        self.style = style or PicasaStyle()
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.apply_style(self.style)

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique la feuille de style Picasa 3 au champ de saisie en ligne.
        EN: Applies the Picasa 3 stylesheet to the inline input field.
        """
        self.style = style
        is_dark = style.is_dark
        bg = style.window_bgcolor.darker(115).name() if is_dark else "#FFFFFF"
        focus_bg = style.window_bgcolor.darker(130).name() if is_dark else "#FFFFFF"
        txt = style.alist_textcolor.name()
        border = style.topbar_btn_border.name()
        accent = style.accent_color.name()
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg};
                color: {txt};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 11px;
                selection-background-color: {accent};
            }}
            QLineEdit:focus {{
                background-color: {focus_bg};
                border: 1px solid {accent};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent):
        """
        FR: Intercepte la touche Échap pour émettre le signal d'annulation.
        EN: Intercepts the Escape key to emit the cancellation signal.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


def _setup_inline_completer(
    edit: QLineEdit,
    names: List[str],
    style: Optional[PicasaStyle] = None,
) -> None:
    """
    FR: Configure l'autocomplétion des noms de contacts (Ref: peoplepanel/peopleautocomplete).
    EN: Configures contact name autocompletion (Ref: peoplepanel/peopleautocomplete).
    """
    if not names:
        return
    st = style or getattr(edit, "style", None) or PicasaStyle()
    is_dark = st.is_dark
    bg = st.window_bgcolor.name() if is_dark else "#FFFFFF"
    txt = st.alist_textcolor.name()
    border = st.topbar_btn_border.name()
    accent = st.accent_color.name()
    hover_bg = st.topbar_btn_bg_end.name()
    completer = QCompleter(sorted(list(set(names))), edit)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    popup = completer.popup()
    if popup:
        popup.setStyleSheet(f"""
            QListView {{
                background-color: {bg};
                color: {txt};
                border: 1px solid {border};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                font-size: 11px;
                padding: 2px;
            }}
            QListView::item {{
                padding: 4px 6px;
            }}
            QListView::item:hover {{
                background-color: {hover_bg};
            }}
        """)
    edit.setCompleter(completer)


def make_rounded_avatar(pixmap: QPixmap, size: int = 72, radius: int = 4) -> QPixmap:
    """
    FR: Arrondit les coins d'une vignette de visage selon les proportions authentiques de Picasa 3.
    EN: Rounds the corners of a face thumbnail according to authentic Picasa 3 proportions.
    Ref: picasa3.exe @ 0x00649023 (0x48 = 72px)
    """
    if pixmap.isNull():
        return pixmap
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(0.5, 0.5, size - 1, size - 1, radius, radius)
    painter.setClipPath(path)
    if pixmap.size() != QSize(size, size):
        scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        dx = (scaled.width() - size) // 2
        dy = (scaled.height() - size) // 2
        painter.drawPixmap(0, 0, scaled, dx, dy, size, size)
    else:
        painter.drawPixmap(0, 0, pixmap)
    # Bordure subtile grise (Ref: Picasa 3 face border)
    pen = QPen(QColor(60, 66, 78, 220), 1.0)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(0.5, 0.5, size - 1, size - 1, radius, radius)
    painter.end()
    return out


class PicasaPeoplePanel(QWidget):
    """
    FR: Volet d'identification des visages et personnes sur la photo sélectionnée.
    EN: Panel for face and people identification on the selected photo.
    Ref: picasa3.exe @ PEOPLEPANEL_TEXT_FR.XML, 0x008AAD76
    Ref: picasa3.exe @ 0x008A1034 (peoplepanel/manual_add_editbox)
    Ref: picasa3.exe @ 0x008A13B8 (peoplepanel/suggestion_yes, suggestion_no)
    Ref: picasa3.exe @ 0x00896F74 (confirmsug, removesel)
    """
    face_hovered = Signal(int)
    face_clicked = Signal(int)
    manual_add_requested = Signal()
    faces_updated = Signal(list)
    people_changed = Signal()
    person_filter_requested = Signal(str, str)  # contact_id, name
    cluster_filter_requested = Signal(list)  # list of photo paths in cluster

    def __init__(self, parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        """
        FR: Initialise le volet Personnes avec son en-tête, sa zone défilante et le bouton d'ajout manuel.
        EN: Initializes the People panel with its header, scrollable area, and manual add button.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle()
        self.db: Optional[PicasaDatabase] = None
        self.photo_index: int = -1
        self.photo_path: str = ""
        self.faces: List[FaceRect] = []
        self.multi_indices: List[int] = []
        self.multi_paths: List[str] = []
        self._last_mode: str = "single"  # "single" or "multi"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # En-tête du volet avec titre et compteur (Ref: PeoplePanel::InThis, PeoplePanel::Known2)
        header_row = QHBoxLayout()
        self.header_lbl = QLabel("Dans cette photo :")
        header_row.addWidget(self.header_lbl, 1)

        self.btn_detect = QPushButton("🔍")
        self.btn_detect.setToolTip("Détecter automatiquement les visages (CFaceDetector)")
        self.btn_detect.setFixedSize(26, 24)
        self.btn_detect.clicked.connect(self._run_face_detection)
        header_row.addWidget(self.btn_detect)
        layout.addLayout(header_row)

        # Zone défilante des visages
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.faces_container = QWidget()
        self.faces_layout = QVBoxLayout(self.faces_container)
        self.faces_layout.setContentsMargins(0, 0, 0, 0)
        self.faces_layout.setSpacing(6)
        self.faces_layout.addStretch(1)

        self.scroll.setWidget(self.faces_container)
        layout.addWidget(self.scroll, 1)

        # Bouton d'ajout manuel (Ref: peoplepanel/manual_add)
        self.btn_manual_add = QPushButton("➕  Ajouter une personne manuellement")
        self.btn_manual_add.clicked.connect(self.manual_add_requested.emit)
        layout.addWidget(self.btn_manual_add)
        self.apply_style(self.style)

    def _theme_colors(self) -> Dict[str, str]:
        """
        FR: Retourne le dictionnaire des couleurs adaptées au thème actif (clair ou sombre).
        EN: Returns the dictionary of colors adapted to the active theme (light or dark).
        """
        s = self.style
        is_dark = s.is_dark
        if is_dark:
            card_bg = s.window_bgcolor.darker(108).name()
            card_hover = s.window_bgcolor.lighter(115).name()
            card_border = s.splitter_color.name()
            avatar_bg = s.window_bgcolor.darker(125).name()
            sug_title_col = "#FFDE66"
            sug_name_col = "#E2E8F0"
            link_col = "#4AA3DF"
            link_hover = "#72BEF0"
        else:
            card_bg = s.window_bgcolor.name()
            card_hover = s.alist_bgcolor.darker(104).name()
            card_border = s.topbar_border_color.name()
            avatar_bg = s.alist_bgcolor.darker(110).name()
            sug_title_col = "#B75D00"
            sug_name_col = s.alist_textcolor.name()
            link_col = s.accent_color.name()
            link_hover = s.accent_color.darker(115).name()
        return {
            "txt": s.alist_textcolor.name(),
            "sub": s.alayout_subtitleColor.name(),
            "accent": s.accent_color.name(),
            "card_bg": card_bg,
            "card_hover": card_hover,
            "card_border": card_border,
            "avatar_bg": avatar_bg,
            "btn_bg": s.topbar_btn_bg_start.name(),
            "btn_hover": s.topbar_btn_bg_end.name(),
            "btn_border": s.topbar_btn_border.name(),
            "sug_title": sug_title_col,
            "sug_name": sug_name_col,
            "link": link_col,
            "link_hover": link_hover,
        }

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique le style visuel Picasa 3 au volet Personnes et reconstruit les cartes actives.
        EN: Applies the Picasa 3 visual style to the People panel and rebuilds active cards.
        """
        self.style = style
        c = self._theme_colors()
        scroll_bg = style.drawer_bgcolor.name()
        self.header_lbl.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {c['txt']}; background: transparent;")
        self.btn_detect.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['btn_bg']};
                color: {c['txt']};
                border: 1px solid {c['btn_border']};
                border-radius: 3px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
                border-color: {c['accent']};
            }}
        """)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: {scroll_bg};
            }}
            QScrollBar::handle:vertical {{
                background: {c['btn_border']};
                border-radius: 4px;
            }}
        """)
        self.faces_container.setStyleSheet("background: transparent;")
        self.btn_manual_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['btn_bg']};
                color: {c['txt']};
                border: 1px solid {c['btn_border']};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c['btn_hover']};
                border-color: {c['accent']};
            }}
        """)
        # Re-construire les cartes actives avec les nouvelles couleurs du thème
        if self._last_mode == "multi" and (self.multi_paths or self.db is not None):
            self.set_multiple_photos(self.db, self.multi_indices, self.multi_paths)
        elif self.photo_path or self.faces:
            self.set_photo_faces(
                self.db,
                self.photo_index,
                self.photo_path,
                self.faces,
                source_img=getattr(self, "cached_source_img", None),
            )

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes traduits du volet Personnes selon la langue active.
        EN: Updates translated texts of the People panel according to the active language.
        """
        res = PicasaResourceManager.get()
        in_this = res.get_xml_string("peoplepanel/inthis", "Dans cette photo :")
        count_str = f" ({len(self.faces)})" if self.faces else ""
        self.header_lbl.setText(f"{in_this}{count_str}")
        add_person = res.get_xml_string("peoplepanel/add_person", "Ajouter une personne manuellement")
        self.btn_manual_add.setText(f"➕  {add_person}")

    def set_photo_faces(
        self,
        db: Optional[PicasaDatabase],
        photo_index: int,
        photo_path: str,
        faces: List[FaceRect],
        source_img: Optional[Image.Image] = None,
    ) -> None:
        """
        FR: Affiche les cartes des visages détectés pour une photo unique sélectionnée.
        EN: Displays the detected face cards for a single selected photo.
        """
        self._last_mode = "single"
        self.db = db
        self.photo_index = photo_index
        self.photo_path = photo_path
        self.faces = faces
        self.cached_source_img = source_img
        c = self._theme_colors()

        # Vider la liste précédente
        while self.faces_layout.count() > 1:
            item = self.faces_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        count_str = f" ({len(faces)})" if faces else ""
        self.header_lbl.setText(f"Dans cette photo :{count_str}")

        if not faces:
            empty_widget = QWidget()
            empty_widget.setStyleSheet("background: transparent;")
            elay = QVBoxLayout(empty_widget)
            elay.setContentsMargins(0, 20, 0, 20)
            elay.setSpacing(10)

            empty_lbl = QLabel("Aucun visage identifié sur cette photo.")
            empty_lbl.setStyleSheet(f"color: {c['sub']}; font-size: 11px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elay.addWidget(empty_lbl)

            btn_scan = QPushButton("🔍  Détecter les visages")
            btn_scan.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['btn_bg']};
                    color: {c['accent']};
                    border: 1px solid {c['accent']};
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {c['accent']};
                    color: #FFFFFF;
                }}
            """)
            btn_scan.clicked.connect(self._run_face_detection)
            elay.addWidget(btn_scan, alignment=Qt.AlignmentFlag.AlignCenter)

            self.faces_layout.insertWidget(0, empty_widget)
            return

        # Charger l'image source avec orientation et retouches pour découper les avatars
        if source_img is None and photo_path and os.path.exists(photo_path):
            try:
                from picasa_py.ui.image_processor import PicasaImageProcessor
                source_img = PicasaImageProcessor.load_transformed_image(photo_path)
                self.cached_source_img = source_img
            except Exception:
                pass

        for i, fr in enumerate(faces):
            card = self._create_face_card(i, fr, source_img)
            self.faces_layout.insertWidget(i, card)

    def set_multiple_photos(
        self,
        db: Optional[PicasaDatabase],
        photo_indices: List[int],
        photo_paths: List[str],
    ) -> None:
        """
        FR: Présente les personnes détectées et les grappes sans nom sur l'ensemble des photos sélectionnées.
        EN: Presents detected people and unnamed face clusters across all selected photos.
        Ref: picasa3.exe @ 0x00CA1264 ("People in these photos:"), 0x00CA11A0 ("Who is in these photos?")
        Ref: picasa3.exe @ PEOPLEPANEL_TEXT_FR.XML, Text5(peoplepanel/instructions)
        """
        self._last_mode = "multi"
        self.db = db
        self.multi_indices = list(photo_indices)
        self.multi_paths = list(photo_paths)
        self.photo_index = -1
        self.photo_path = ""
        self.faces = []
        self.cached_source_img = None
        c = self._theme_colors()

        # Vider la liste précédente
        while self.faces_layout.count() > 1:
            item = self.faces_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not photo_paths:
            self.header_lbl.setText("Personnes")
            empty_widget = QWidget()
            empty_widget.setStyleSheet("background: transparent;")
            elay = QVBoxLayout(empty_widget)
            elay.setContentsMargins(0, 20, 0, 20)
            empty_lbl = QLabel("Sélectionner des photos pour afficher les personnes.")
            empty_lbl.setStyleSheet(f"color: {c['sub']}; font-size: 11px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elay.addWidget(empty_lbl)
            self.faces_layout.insertWidget(0, empty_widget)
            return

        # Agréger les personnes et visages sur l'ensemble de la sélection
        known_people: Dict[str, Dict[str, Any]] = {}
        unnamed_faces_list: List[Tuple[Optional[int], str, FaceRect]] = []

        for p_idx, p_path in zip(photo_indices, photo_paths):
            photo_faces: List[FaceRect] = []
            if db and p_idx >= 0:
                photo_faces = db.face_manager.get_faces_for_photo(p_idx)
            for fr in photo_faces:
                name_str = fr.contact_name or ""
                if fr.contact_id and name_str and not name_str.startswith("? ") and name_str != "Sans nom":
                    cid = fr.contact_id.lower()
                    if cid not in known_people:
                        known_people[cid] = {
                            "name": name_str,
                            "photos": set(),
                            "sample_face": fr,
                            "sample_path": p_path,
                            "sample_idx": p_idx,
                        }
                    known_people[cid]["photos"].add(p_path or str(p_idx))
                else:
                    unnamed_faces_list.append((p_idx, p_path, fr))

        # Regrouper les visages similaires non nommés en grappes (face clustering)
        # Ref: picasa3.exe @ 0x0064AE90, 0x00788090 (faceclusterpanel), FRSortThreshold (0x00881CC2)
        clusters: List[List[Tuple[Optional[int], str, FaceRect]]] = []
        if unnamed_faces_list and db and getattr(db, "face_manager", None):
            try:
                clusters = db.face_manager.cluster_unnamed_faces(unnamed_subset=unnamed_faces_list)
            except Exception:
                clusters = [[f] for f in unnamed_faces_list]
        elif unnamed_faces_list:
            clusters = [[f] for f in unnamed_faces_list]

        # Mettre à jour l'en-tête selon picasa3.exe (PeoplePanel::Known2 vs PeoplePanel::Who vs PeoplePanel::Unnamed)
        if known_people:
            self.header_lbl.setText(f"Personnes figurant sur ces photos ({len(known_people)})")
        elif clusters:
            self.header_lbl.setText("Qui est présent sur ces photos ?")
        else:
            self.header_lbl.setText("Qui figure sur ces photos ?")

        card_idx = 0

        # 1. Cartes des personnes identifiées
        for cid, info in sorted(known_people.items(), key=lambda kv: len(kv[1]["photos"]), reverse=True):
            card = self._create_multi_person_card(cid, info["name"], len(info["photos"]), info["sample_face"], info["sample_path"])
            self.faces_layout.insertWidget(card_idx, card)
            card_idx += 1

        # 2. Section des visages similaires regroupés (Face Clusters)
        if clusters:
            if known_people:
                # Séparateur / en-tête de section (Ref: PeoplePanel::Unnamed, 0x00CA12D0)
                sec_header = QLabel(f"Groupes de personnes sans nom ({len(clusters)}) :")
                sec_header.setStyleSheet(f"""
                    QLabel {{
                        color: {c['sub']};
                        font-size: 11px;
                        font-weight: bold;
                        padding-top: 8px;
                        padding-bottom: 4px;
                        border-bottom: 1px solid {c['card_border']};
                        background: transparent;
                    }}
                """)
                self.faces_layout.insertWidget(card_idx, sec_header)
                card_idx += 1

            MAX_VISIBLE_CLUSTERS = 30
            rendered_clusters = clusters[:MAX_VISIBLE_CLUSTERS]
            remaining_clusters = clusters[MAX_VISIBLE_CLUSTERS:]

            for c_i, cluster in enumerate(rendered_clusters):
                card = self._create_cluster_card(c_i, cluster)
                self.faces_layout.insertWidget(card_idx, card)
                card_idx += 1

            if remaining_clusters:
                more_widget = QWidget()
                more_widget.setStyleSheet("background: transparent;")
                mlay = QVBoxLayout(more_widget)
                mlay.setContentsMargins(0, 4, 0, 8)
                btn_more = QPushButton(f"+ Afficher les {len(remaining_clusters)} autres groupes...")
                btn_more.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c['btn_bg']};
                        color: {c['accent']};
                        border: 1px solid {c['accent']};
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {c['accent']};
                        color: #FFFFFF;
                    }}
                """)
                def on_show_more():
                    """
                    FR: Affiche les grappes de visages restantes au-delà de la limite initiale.
                    EN: Displays the remaining face clusters beyond the initial limit.
                    """
                    btn_more.setVisible(False)
                    for r_i, r_cluster in enumerate(remaining_clusters):
                        r_card = self._create_cluster_card(MAX_VISIBLE_CLUSTERS + r_i, r_cluster)
                        self.faces_layout.insertWidget(self.faces_layout.count() - 1, r_card)
                btn_more.clicked.connect(on_show_more)
                mlay.addWidget(btn_more, alignment=Qt.AlignmentFlag.AlignCenter)
                self.faces_layout.insertWidget(card_idx, more_widget)
                card_idx += 1

        # Si aucun visage trouvé sur les photos sélectionnées
        if card_idx == 0:
            empty_widget = QWidget()
            empty_widget.setStyleSheet("background: transparent;")
            elay = QVBoxLayout(empty_widget)
            elay.setContentsMargins(0, 20, 0, 20)
            elay.setSpacing(10)

            empty_lbl = QLabel(f"Aucun visage identifié dans la sélection ({len(photo_paths)} photos).")
            empty_lbl.setStyleSheet(f"color: {c['sub']}; font-size: 11px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elay.addWidget(empty_lbl)

            btn_scan = QPushButton("🔍  Détecter les visages sur la sélection")
            btn_scan.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['btn_bg']};
                    color: {c['accent']};
                    border: 1px solid {c['accent']};
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {c['accent']};
                    color: #FFFFFF;
                }}
            """)
            btn_scan.clicked.connect(self._run_multi_face_detection)
            elay.addWidget(btn_scan, alignment=Qt.AlignmentFlag.AlignCenter)

            self.faces_layout.insertWidget(0, empty_widget)

    def _create_cluster_card(
        self,
        cluster_idx: int,
        cluster: List[Tuple[Optional[int], str, FaceRect]],
    ) -> QWidget:
        """
        FR: Crée une carte pour un groupe de visages similaires sans nom (Face Cluster).
        EN: Creates a card for a group of similar unnamed faces (Face Cluster).
        Ref: picasa3.exe @ 0x00788090 - 0x00788C80 (faceclusterpanel)
        Ref: 0x00CB4660 (faceclusterpanel_%d_addname), 0x00CB46D0 (faceclusterpanel_%d_ignore)
        Ref: 0x00CA0FD8 (PeoplePanel::Cluster -> "%d photos"), 0x00CA160C (PeoplePanel::SuggestionFmt -> "%s?")
        Ref: 0x00CF4F48 (hauteur 86.0f), 0x00649023 (avatar 72x72 px)
        """
        c = self._theme_colors()
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 5px;
            }}
            QFrame:hover {{
                background-color: {c['card_hover']};
                border-color: {c['accent']};
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # 1. Échantillon représentatif du cluster
        sample_idx, sample_path, sample_fr = cluster[0]
        unique_paths = list(dict.fromkeys(ppath for _, ppath, _ in cluster if ppath))
        photo_count = len(unique_paths) or len(cluster)

        # 2. Avatar 72x72 avec bords adoucis (Ref: 0x00649023)
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(72, 72)
        avatar_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {c['avatar_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 4px;
            }}
        """)
        avatar_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        avatar_lbl.setToolTip(f"Cliquer pour afficher les {photo_count} photo(s) de ce groupe")

        pix: Optional[QPixmap] = None
        if self.db and getattr(self.db, "face_manager", None):
            pix = self.db.face_manager.get_face_avatar(
                sample_path, sample_fr, db_idx=sample_idx, size=72, circular=False
            )
        if not pix or pix.isNull():
            if sample_idx is not None and self.db:
                try:
                    raw_thumb = self.db.get_thumbnail(sample_idx, size="small")
                    if raw_thumb:
                        with Image.open(io.BytesIO(raw_thumb)) as t_img:
                            pix = sample_fr.crop_avatar(t_img, avatar_size=72, circular=False)
                except Exception:
                    pass

        if pix and not pix.isNull():
            avatar_lbl.setPixmap(make_rounded_avatar(pix, size=72, radius=4))
        else:
            avatar_lbl.setText("👤")
            avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Clic sur l'avatar filtre / sélectionne les photos de ce groupe
        avatar_lbl.mousePressEvent = lambda ev: self.cluster_filter_requested.emit(unique_paths)
        layout.addWidget(avatar_lbl)

        # 3. Colonne d'informations et d'actions (Ref: 0x00788605, 0x00788BA9)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        # Détecter si une suggestion existe pour ce cluster
        suggested_name: Optional[str] = None
        for _, _, fr in cluster:
            if fr.contact_name and fr.contact_name.startswith("? "):
                suggested_name = fr.contact_name[2:].strip()
                break
        if not suggested_name and self.db and getattr(self.db, "face_manager", None):
            feat = None
            if sample_idx is not None and hasattr(self.db, "get_face_template"):
                try:
                    feat = self.db.get_face_template(sample_idx)
                except Exception:
                    feat = None
            if feat is not None:
                best_sim = -1.0
                best_person = None
                try:
                    from picasa_py.faces.detector import (
                        PicasaFaceDetector,
                        FR_SUGGESTION_THRESHOLD,
                        FR_SUGGESTION_SINGLE_THRESHOLD,
                    )
                    detector = PicasaFaceDetector.get()
                    for p in self.db.face_manager.get_people():
                        ref_vecs = p.feature_vectors if getattr(p, "feature_vectors", None) else (
                            [p.feature_vector] if p.feature_vector is not None else []
                        )
                        if not ref_vecs:
                            continue
                        p_sim = max(detector.compare_face_features(feat, rv) for rv in ref_vecs)
                        req_t = FR_SUGGESTION_SINGLE_THRESHOLD if p.photo_count <= 1 else FR_SUGGESTION_THRESHOLD
                        if p_sim >= req_t and p_sim > best_sim:
                            best_sim = p_sim
                            best_person = p
                    if best_person is not None:
                        suggested_name = best_person.name
                except Exception:
                    pass

        # Ligne supérieure : Saisie du nom + Bouton d'exclusion (✕)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        name_edit = PicasaInlineNameEdit(placeholder="Ajouter un nom", style=self.style)
        name_edit.setFixedHeight(24)

        # Autocomplétion avec tous les contacts connus (Ref: peopleautocomplete @ 0x008A1090)
        all_contacts = []
        if self.db and getattr(self.db, "face_manager", None):
            all_contacts = [p.name for p in self.db.face_manager.get_people() if p.name]
        _setup_inline_completer(name_edit, all_contacts, style=self.style)

        def on_apply_cluster():
            """
            FR: Attribue le nom saisi à l'ensemble des visages de la grappe.
            EN: Assigns the entered name to all faces in the cluster.
            """
            new_name = name_edit.text().strip()
            if new_name and self.db and getattr(self.db, "face_manager", None):
                self.db.face_manager.name_cluster(cluster, new_name)
                self.people_changed.emit()
                self.set_multiple_photos(self.db, self.multi_indices, self.multi_paths)

        name_edit.returnPressed.connect(on_apply_cluster)
        top_row.addWidget(name_edit, 1)

        # Bouton d'exclusion / suppression (Ref: faceclusterpanel_%d_ignore @ 0x00CB46D0, 0x00CA1330)
        btn_ignore = QPushButton("✕")
        btn_ignore.setFixedSize(18, 18)
        btn_ignore.setToolTip("Ignorer ce groupe de personnes (PeoplePanel::ConfirmRemoveTitle)")
        btn_ignore.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['sub']};
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                color: #E74C3C;
            }}
        """)
        btn_ignore.setCursor(Qt.CursorShape.PointingHandCursor)

        def on_ignore_cluster():
            """
            FR: Supprime ou ignore tous les visages appartenant à cette grappe.
            EN: Removes or ignores all faces belonging to this cluster.
            """
            if self.db and getattr(self.db, "face_manager", None):
                for c_idx, c_path, c_fr in cluster:
                    self.db.face_manager.remove_face(c_path, c_fr, db_idx=c_idx)
                self.people_changed.emit()
                self.set_multiple_photos(self.db, self.multi_indices, self.multi_paths)

        btn_ignore.clicked.connect(on_ignore_cluster)
        top_row.addWidget(btn_ignore, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        info_layout.addLayout(top_row)

        # Ligne intermédiaire : Compteur de photos (Ref: PeoplePanel::Cluster -> "%d photos" @ 0x00CA0FD8)
        mid_row = QHBoxLayout()
        mid_row.setContentsMargins(0, 0, 0, 0)
        mid_row.setSpacing(6)

        count_text = f"{photo_count} photo{'s' if photo_count > 1 else ''}"
        count_lbl = QLabel(count_text)
        count_lbl.setStyleSheet(f"color: {c['sub']}; font-size: 10px; background: transparent; border: none;")
        mid_row.addWidget(count_lbl)

        btn_filter = QPushButton("Afficher")
        btn_filter.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['link']};
                border: none;
                font-size: 10px;
                text-decoration: underline;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {c['link_hover']};
            }}
        """)
        btn_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_filter.clicked.connect(lambda: self.cluster_filter_requested.emit(unique_paths))
        mid_row.addWidget(btn_filter)
        mid_row.addStretch()
        info_layout.addLayout(mid_row)

        # Ligne de suggestion si présente (Ref: PeoplePanel::SuggestionFmt -> "%s?", 0x00CA160C)
        if suggested_name:
            sug_row = QHBoxLayout()
            sug_row.setContentsMargins(0, 2, 0, 0)
            sug_row.setSpacing(4)

            sug_lbl = QLabel(f"{suggested_name} ?")
            sug_lbl.setStyleSheet(f"color: {c['sug_name']}; font-size: 11px; font-weight: bold; background: transparent; border: none;")
            sug_row.addWidget(sug_lbl, 1)

            # Bouton Oui (Ref: 0x00CB45A8, ConfirmYesButton_b, suggestion_yes @ 0x00CA13CC)
            btn_yes = QPushButton("✓")
            btn_yes.setFixedSize(22, 22)
            btn_yes.setToolTip(f"Confirmer la correspondance avec {suggested_name}")
            btn_yes.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2ECC71;
                }
            """)
            btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)

            def on_confirm_sug():
                """
                FR: Valide la suggestion de nom proposée pour la grappe de visages.
                EN: Confirms the suggested name for the face cluster.
                """
                if self.db and getattr(self.db, "face_manager", None):
                    self.db.face_manager.name_cluster(cluster, suggested_name)
                    self.people_changed.emit()
                    self.set_multiple_photos(self.db, self.multi_indices, self.multi_paths)

            btn_yes.clicked.connect(on_confirm_sug)
            sug_row.addWidget(btn_yes)

            # Bouton Non (Ref: 0x00CB45BC, ConfirmNoButton_b, suggestion_no @ 0x00CA1408)
            btn_no = QPushButton("✕")
            btn_no.setFixedSize(22, 22)
            btn_no.setToolTip("Rejeter cette suggestion")
            btn_no.setStyleSheet("""
                QPushButton {
                    background-color: #C0392B;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #E74C3C;
                }
            """)
            btn_no.setCursor(Qt.CursorShape.PointingHandCursor)

            def on_reject_sug():
                """
                FR: Rejette la suggestion de nom sur la grappe de visages.
                EN: Rejects the name suggestion on the face cluster.
                """
                for _, _, fr in cluster:
                    if fr.contact_name and fr.contact_name.startswith("? "):
                        fr.contact_name = ""
                self.set_multiple_photos(self.db, self.multi_indices, self.multi_paths)

            btn_no.clicked.connect(on_reject_sug)
            sug_row.addWidget(btn_no)

            info_layout.addLayout(sug_row)

        layout.addLayout(info_layout, 1)
        return card

    def _create_multi_person_card(
        self, cid: str, name: str, count: int, sample_fr: FaceRect, sample_path: str
    ) -> QWidget:
        """
        FR: Crée une carte pour une personne identifiée présente sur plusieurs photos sélectionnées.
        EN: Creates a card for an identified person present across multiple selected photos.
        """
        c = self._theme_colors()
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 5px;
            }}
            QFrame:hover {{
                background-color: {c['card_hover']};
                border-color: {c['accent']};
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Avatar de la personne (72x72 pixels, Ref: picasa3.exe @ 0x00649023)
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(72, 72)
        avatar_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {c['avatar_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 4px;
            }}
        """)
        pix: Optional[QPixmap] = None
        if self.db and getattr(self.db, "face_manager", None):
            pix = self.db.face_manager.get_person_avatar(cid, size=72, circular=False)
            if not pix or pix.isNull():
                pix = self.db.face_manager.get_face_avatar(sample_path, sample_fr, size=72, circular=False)
        if pix and not pix.isNull():
            pix = make_rounded_avatar(pix, size=72, radius=4)
            avatar_lbl.setPixmap(pix)
        else:
            avatar_lbl.setText("👤")
            avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar_lbl)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {c['txt']}; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        info_layout.addWidget(name_lbl)

        count_lbl = QLabel(f"Présent(e) dans {count} photo(s)")
        count_lbl.setStyleSheet(f"color: {c['sub']}; font-size: 10px; background: transparent; border: none;")
        info_layout.addWidget(count_lbl)

        btn_view = QPushButton("Afficher l'album")
        btn_view.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['link']};
                border: none;
                text-align: left;
                font-size: 11px;
                text-decoration: underline;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {c['link_hover']};
            }}
        """)
        btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view.clicked.connect(lambda: self.person_filter_requested.emit(cid, name))
        info_layout.addWidget(btn_view)

        layout.addLayout(info_layout, 1)
        return card

    def _run_multi_face_detection(self) -> None:
        """
        FR: Détecte les visages sur toutes les photos actuellement sélectionnées.
        EN: Detects faces across all currently selected photos.
        """
        if not self.db or not getattr(self, "multi_paths", None):
            return
        for p_idx, p_path in zip(self.multi_indices, self.multi_paths):
            if p_path and os.path.exists(p_path):
                self.db.face_manager.detect_faces_for_photo(
                    p_path, db_idx=p_idx if p_idx >= 0 else None, auto_suggest=True
                )
        self.set_multiple_photos(self.db, self.multi_indices, self.multi_paths)
        self.people_changed.emit()

    def _create_face_card(self, idx: int, fr: FaceRect, source_img: Optional[Image.Image]) -> QWidget:
        """
        FR: Crée une carte interactive pour un visage individuel (identifié, suggéré ou sans nom).
        EN: Creates an interactive card for an individual face (identified, suggested, or unnamed).
        """
        name_str = fr.contact_name or ""
        c = self._theme_colors()
        card = FaceCardFrame(
            idx,
            on_hover=lambda i: self.face_hovered.emit(i),
            on_leave=lambda i: self.face_hovered.emit(-1),
            on_click=lambda i: self.face_clicked.emit(i),
        )
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 5px;
            }}
            QFrame:hover {{
                background-color: {c['card_hover']};
                border-color: {c['accent']};
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Avatar de visage agrandi à 72x72 pixels (Ref: picasa3.exe @ 0x00649023, 0x48 = 72px)
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(72, 72)
        avatar_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {c['avatar_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 4px;
            }}
        """)
        if source_img:
            try:
                w_src, h_src = source_img.size
                aspect_src = (w_src / float(h_src)) if h_src > 0 else 1.0
                disp_fr = (
                    fr.project_for_photo_ini(self.photo_path, aspect_ratio=aspect_src, db=self.db)
                    if hasattr(fr, "project_for_photo_ini")
                    else fr
                )
                pix = disp_fr.crop_avatar(source_img, avatar_size=72, circular=False)
                if not pix.isNull():
                    pix = make_rounded_avatar(pix, size=72, radius=4)
                    avatar_lbl.setPixmap(pix)
                else:
                    avatar_lbl.setText("👤")
                    avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception:
                avatar_lbl.setText("👤")
                avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            avatar_lbl.setText("👤")
            avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if fr.contact_id and name_str and not name_str.startswith("? ") and name_str != "Sans nom":
            avatar_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            avatar_lbl.setToolTip(f"Afficher l'album de {name_str}")
            avatar_lbl.mousePressEvent = lambda e, cid=fr.contact_id, n=name_str: self.person_filter_requested.emit(cid, n)

        layout.addWidget(avatar_lbl)

        # Bouton Ignorer / Supprimer le visage (Ref: peoplepanel/ignore, globalbuttons/square_close_h)
        btn_ignore = QPushButton("✕")
        btn_ignore.setToolTip("Ignorer ou supprimer ce visage")
        btn_ignore.setFixedSize(18, 18)
        btn_ignore.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['sub']};
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                color: #E74C3C;
            }}
        """)
        btn_ignore.clicked.connect(lambda: self._delete_face(fr))

        # Liste des contacts existants pour l'autocomplétion (Ref: peoplepanel/peopleautocomplete)
        existing_names: List[str] = []
        if self.db and getattr(self.db, "face_manager", None):
            existing_names = [p.name for p in self.db.face_manager.get_people() if p.name]
            if getattr(self.db, "contacts", None):
                c_list = getattr(self.db.contacts, "contacts", []) if hasattr(self.db.contacts, "contacts") else (
                    list(self.db.contacts.values()) if isinstance(self.db.contacts, dict) else []
                )
                for c_item in c_list:
                    if getattr(c_item, "name", None) and c_item.name not in existing_names:
                        existing_names.append(c_item.name)
        existing_names = sorted(list(set(existing_names)))

        # Analyse de l'état du visage (Suggestion, Sans nom, ou Identifié)
        is_suggestion = name_str.startswith("? ")
        is_unnamed = (not name_str) or (name_str == "Sans nom")

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        if is_suggestion:
            sug_name = name_str[2:].strip()

            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.setSpacing(4)
            sug_title = QLabel("💡 Suggestion :")
            sug_title.setStyleSheet(f"color: {c['sug_title']}; font-size: 10px; font-weight: bold; background: transparent; border: none;")
            top_row.addWidget(sug_title, 1)
            top_row.addWidget(btn_ignore, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            info_layout.addLayout(top_row)

            # Saisie directe en ligne (Ref: peoplepanel/editbox, peoplepanel/suggestion_yes, suggestion_no)
            edit_row = QHBoxLayout()
            edit_row.setContentsMargins(0, 0, 0, 0)
            edit_row.setSpacing(4)

            name_edit = PicasaInlineNameEdit(sug_name, placeholder="Saisir un nom...", style=self.style)
            name_edit.setToolTip("Modifiez directement la proposition si besoin, puis appuyez sur Entrée")
            if existing_names:
                _setup_inline_completer(name_edit, existing_names, style=self.style)

            btn_yes = QPushButton("✔")
            btn_yes.setToolTip("Valider ce nom (Entrée)")
            btn_yes.setFixedSize(26, 24)
            btn_yes.setStyleSheet("""
                QPushButton {
                    background-color: #1F6A38;
                    color: #FFFFFF;
                    border: 1px solid #2B8A4B;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #278546;
                }
            """)

            btn_no = QPushButton("✘")
            btn_no.setToolTip("Rejeter la suggestion (Échap)")
            btn_no.setFixedSize(24, 24)
            btn_no.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['btn_bg']};
                    color: {c['txt']};
                    border: 1px solid {c['btn_border']};
                    border-radius: 3px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {c['btn_hover']};
                    border-color: {c['accent']};
                }}
            """)

            def on_confirm_inline():
                """
                FR: Valide la suggestion ou le nom modifié en ligne pour ce visage.
                EN: Confirms the suggestion or inline-edited name for this face.
                """
                entered = name_edit.text().strip()
                self._apply_inline_suggestion(fr, entered, sug_name)

            name_edit.returnPressed.connect(on_confirm_inline)
            name_edit.escape_pressed.connect(lambda: name_edit.setText(sug_name))
            btn_yes.clicked.connect(on_confirm_inline)
            btn_no.clicked.connect(lambda: self._reject_suggestion(fr))

            edit_row.addWidget(name_edit, 1)
            edit_row.addWidget(btn_yes)
            edit_row.addWidget(btn_no)
            info_layout.addLayout(edit_row)

        elif is_unnamed:
            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.setSpacing(4)
            name_lbl = QLabel("Visage non identifié")
            name_lbl.setStyleSheet(f"color: {c['sub']}; font-style: italic; font-size: 10px; background: transparent; border: none;")
            top_row.addWidget(name_lbl, 1)
            top_row.addWidget(btn_ignore, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            info_layout.addLayout(top_row)

            edit_row = QHBoxLayout()
            edit_row.setContentsMargins(0, 0, 0, 0)
            edit_row.setSpacing(4)

            name_edit = PicasaInlineNameEdit("", placeholder="Ajouter un nom...", style=self.style)
            name_edit.setToolTip("Saisissez directement un nom pour cette personne (Entrée pour valider)")
            if existing_names:
                _setup_inline_completer(name_edit, existing_names, style=self.style)

            btn_apply = QPushButton("✔")
            btn_apply.setToolTip("Attribuer ce nom (Entrée)")
            btn_apply.setFixedSize(26, 24)
            btn_apply.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent']};
                    color: #FFFFFF;
                    border: 1px solid {c['accent']};
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.style.accent_color.lighter(115).name()};
                }}
            """)

            def on_apply_unnamed():
                """
                FR: Attribue le nom saisi au visage non identifié.
                EN: Assigns the entered name to the unidentified face.
                """
                entered = name_edit.text().strip()
                if entered:
                    self._apply_inline_name(fr, entered)

            name_edit.returnPressed.connect(on_apply_unnamed)
            name_edit.escape_pressed.connect(lambda: name_edit.clear())
            btn_apply.clicked.connect(on_apply_unnamed)

            edit_row.addWidget(name_edit, 1)
            edit_row.addWidget(btn_apply)
            info_layout.addLayout(edit_row)

        else:
            # Widget à pile (QStackedWidget) : bascule entre affichage classique et édition en ligne
            name_stack = QStackedWidget()
            name_stack.setStyleSheet("background: transparent; border: none;")

            # Page 0 : Affichage classique
            view_page = QWidget()
            view_page.setStyleSheet("background: transparent; border: none;")
            v_layout = QVBoxLayout(view_page)
            v_layout.setContentsMargins(0, 0, 0, 0)
            v_layout.setSpacing(2)

            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.setSpacing(4)

            name_lbl = QLabel(name_str)
            name_lbl.setStyleSheet(f"color: {c['txt']}; font-weight: bold; font-size: 13px; background: transparent; border: none;")
            if fr.contact_id:
                name_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                name_lbl.setToolTip(f"Afficher l'album de {name_str}")
                name_lbl.mousePressEvent = lambda e, cid=fr.contact_id, n=name_str: self.person_filter_requested.emit(cid, n)
            top_row.addWidget(name_lbl, 1)
            top_row.addWidget(btn_ignore, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            v_layout.addLayout(top_row)

            act_row = QHBoxLayout()
            act_row.setContentsMargins(0, 0, 0, 0)
            act_row.setSpacing(8)

            if fr.contact_id:
                btn_album = QPushButton("Album")
                btn_album.setToolTip(f"Afficher l'album de {name_str}")
                btn_album.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {c['link']};
                        border: none;
                        text-align: left;
                        font-size: 11px;
                        text-decoration: underline;
                        padding: 0;
                    }}
                    QPushButton:hover {{
                        color: {c['link_hover']};
                    }}
                """)
                btn_album.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_album.clicked.connect(lambda _, cid=fr.contact_id, n=name_str: self.person_filter_requested.emit(cid, n))
                act_row.addWidget(btn_album)

            btn_edit = QPushButton("Modifier")
            btn_edit.setToolTip("Modifier directement le nom en ligne")
            btn_edit.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c['sub']};
                    border: none;
                    text-align: left;
                    font-size: 11px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    color: {c['txt']};
                    text-decoration: underline;
                }}
            """)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            act_row.addWidget(btn_edit)

            btn_cover = QPushButton("📌 Vignette")
            btn_cover.setToolTip("Définir comme miniature de l'album de cette personne (ID_SETPEOPLEALBUMCOVER)")
            btn_cover.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c['sub']};
                    border: none;
                    text-align: left;
                    font-size: 10px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    color: {c['txt']};
                    text-decoration: underline;
                }}
            """)
            btn_cover.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cover.clicked.connect(lambda _, f=fr: self._set_as_album_cover(f))
            act_row.addWidget(btn_cover)
            act_row.addStretch(1)

            v_layout.addLayout(act_row)
            name_stack.addWidget(view_page)

            # Page 1 : Édition directe en ligne (Ref: peoplepanel/editbox)
            edit_page = QWidget()
            edit_page.setStyleSheet("background: transparent; border: none;")
            e_layout = QHBoxLayout(edit_page)
            e_layout.setContentsMargins(0, 0, 0, 0)
            e_layout.setSpacing(4)

            inline_rename = PicasaInlineNameEdit(name_str, placeholder="Nouveau nom...", style=self.style)
            if existing_names:
                _setup_inline_completer(inline_rename, existing_names, style=self.style)

            btn_save = QPushButton("✔")
            btn_save.setToolTip("Valider la modification (Entrée)")
            btn_save.setFixedSize(26, 24)
            btn_save.setStyleSheet("""
                QPushButton {
                    background-color: #1F6A38;
                    color: #FFFFFF;
                    border: 1px solid #2B8A4B;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #278546;
                }
            """)

            btn_cancel_edit = QPushButton("✘")
            btn_cancel_edit.setToolTip("Annuler (Échap)")
            btn_cancel_edit.setFixedSize(24, 24)
            btn_cancel_edit.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['btn_bg']};
                    color: {c['txt']};
                    border: 1px solid {c['btn_border']};
                    border-radius: 3px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {c['btn_hover']};
                    border-color: {c['accent']};
                }}
            """)

            def on_reassign_inline():
                """
                FR: Réassigne ce visage au nouveau nom saisi en ligne.
                EN: Reassigns this face to the new inline-entered name.
                """
                new_n = inline_rename.text().strip()
                if new_n and new_n != name_str:
                    db_i = self.photo_index if self.photo_index >= 0 else None
                    self.db.face_manager.reassign_face(
                        self.photo_path, fr, new_n, db_idx=db_i, source_image=getattr(self, "cached_source_img", None)
                    )
                    updated_faces = self.db.face_manager.get_faces_for_photo(self.photo_index) if self.photo_index >= 0 else []
                    self.set_photo_faces(self.db, self.photo_index, self.photo_path, updated_faces, source_img=getattr(self, "cached_source_img", None))
                    self.faces_updated.emit(updated_faces)
                    self.people_changed.emit()
                else:
                    name_stack.setCurrentIndex(0)

            def activate_edit():
                """
                FR: Bascule la carte vers le mode d'édition en ligne du nom.
                EN: Switches the card to inline name editing mode.
                """
                name_stack.setCurrentIndex(1)
                inline_rename.setText(name_str)
                inline_rename.selectAll()
                inline_rename.setFocus()

            def cancel_edit():
                """
                FR: Annule l'édition en ligne et revient à l'affichage standard.
                EN: Cancels inline editing and returns to the standard display.
                """
                inline_rename.setText(name_str)
                name_stack.setCurrentIndex(0)

            btn_edit.clicked.connect(activate_edit)
            name_lbl.mouseDoubleClickEvent = lambda e: activate_edit()

            inline_rename.returnPressed.connect(on_reassign_inline)
            inline_rename.escape_pressed.connect(cancel_edit)
            btn_save.clicked.connect(on_reassign_inline)
            btn_cancel_edit.clicked.connect(cancel_edit)

            e_layout.addWidget(inline_rename, 1)
            e_layout.addWidget(btn_save)
            e_layout.addWidget(btn_cancel_edit)
            name_stack.addWidget(edit_page)

            info_layout.addWidget(name_stack)

        layout.addLayout(info_layout, 1)
        return card

    def _set_as_album_cover(self, fr: FaceRect) -> None:
        """
        FR: Définit ce visage comme avatar officiel pour cette personne (ID_SETPEOPLEALBUMCOVER).
        EN: Sets this face as the official avatar for this person (ID_SETPEOPLEALBUMCOVER).
        """
        if not fr.contact_id or not self.db or not getattr(self.db, "face_manager", None):
            return
        self.db.face_manager.set_person_album_cover(fr.contact_id, self.photo_path, fr)
        self.people_changed.emit()

    def _run_face_detection(self) -> None:
        """
        FR: Déclenche la détection automatique locale des visages sur la photo active.
        EN: Triggers local automatic face detection on the active photo.
        """
        if not self.db or not self.photo_path:
            return
        faces = self.db.face_manager.detect_faces_for_photo(
            self.photo_path,
            db_idx=self.photo_index if self.photo_index >= 0 else None,
            auto_suggest=True
        )
        self.set_photo_faces(self.db, self.photo_index, self.photo_path, faces)
        self.faces_updated.emit(faces)

    def _open_name_dialog(
        self,
        fr: FaceRect,
        is_new: bool = False,
        source_image: Optional[Image.Image] = None,
    ) -> None:
        """
        FR: Ouvre le dialogue modal pour nommer, réassigner ou supprimer le visage.
        EN: Opens the modal dialog to name, reassign, or delete the face.
        """
        if not self.db:
            return

        existing_names = [p.name for p in self.db.face_manager.get_people()]
        curr_name = fr.contact_name if (fr.contact_name and not fr.contact_name.startswith("? ")) else ""
        src_img = source_image if source_image is not None else getattr(self, "cached_source_img", None)

        dlg = PicasaNameFaceDialog(
            face_rect=fr,
            photo_path=self.photo_path,
            existing_names=existing_names,
            current_name=curr_name,
            is_new_face=is_new or not curr_name,
            parent=self.window(),
            source_image=src_img,
        )
        if dlg.exec():
            if dlg.is_delete_requested():
                self._delete_face(fr)
            else:
                new_name = dlg.get_contact_name()
                if new_name:
                    db_i = self.photo_index if self.photo_index >= 0 else None
                    if is_new or not fr.contact_id:
                        self.db.face_manager.add_face(
                            self.photo_path, fr, new_name, db_idx=db_i, source_image=src_img
                        )
                    else:
                        self.db.face_manager.reassign_face(
                            self.photo_path, fr, new_name, db_idx=db_i, source_image=src_img
                        )

                    updated_faces = self.db.face_manager.get_faces_for_photo(self.photo_index) if self.photo_index >= 0 else []
                    self.set_photo_faces(self.db, self.photo_index, self.photo_path, updated_faces, source_img=src_img)
                    self.faces_updated.emit(updated_faces)
                    self.people_changed.emit()

    def _apply_inline_suggestion(self, fr: FaceRect, entered_name: str, original_sug_name: str) -> None:
        """
        FR: Applique directement le nom saisi en ligne au visage suggéré.
        Si le nom saisi correspond à la suggestion initiale, la valide.
        Si l'utilisateur a modifié ou saisi un nouveau nom, attribue ce nouveau nom.
        EN: Directly applies the inline-entered name to the suggested face.
        If the entered name matches the initial suggestion, confirms it.
        If the user modified or entered a new name, assigns that new name.
        Ref: picasa3.exe @ peoplepanel/editbox, peoplepanel/suggestion_yes
        """
        if not self.db:
            return
        name_to_apply = entered_name if entered_name else original_sug_name
        if not name_to_apply:
            return

        if name_to_apply.lower() == original_sug_name.lower():
            self._confirm_suggestion(fr, original_sug_name)
        else:
            # Rejeter l'ancienne suggestion et attribuer le nouveau nom
            for sugs in self.db.face_manager.suggestions.values():
                for s in list(sugs):
                    if s.photo_path == self.photo_path and _face_overlap(s.face_rect, fr) >= 0.5:
                        self.db.face_manager.reject_suggestion(s)

            db_i = self.photo_index if self.photo_index >= 0 else None
            self.db.face_manager.add_face(
                self.photo_path, fr, name_to_apply, db_idx=db_i, source_image=getattr(self, "cached_source_img", None)
            )
            updated_faces = self.db.face_manager.get_faces_for_photo(self.photo_index) if self.photo_index >= 0 else []
            self.set_photo_faces(self.db, self.photo_index, self.photo_path, updated_faces, source_img=getattr(self, "cached_source_img", None))
            self.faces_updated.emit(updated_faces)
            self.people_changed.emit()

    def _apply_inline_name(self, fr: FaceRect, new_name: str) -> None:
        """
        FR: Attribue directement un nom saisi en ligne à un visage non identifié.
        EN: Directly assigns an inline-entered name to an unidentified face.
        Ref: picasa3.exe @ peoplepanel/addname:%d, peoplepanel/editbox
        """
        if not self.db or not new_name:
            return
        db_i = self.photo_index if self.photo_index >= 0 else None
        self.db.face_manager.add_face(
            self.photo_path, fr, new_name, db_idx=db_i, source_image=getattr(self, "cached_source_img", None)
        )
        updated_faces = self.db.face_manager.get_faces_for_photo(self.photo_index) if self.photo_index >= 0 else []
        self.set_photo_faces(self.db, self.photo_index, self.photo_path, updated_faces, source_img=getattr(self, "cached_source_img", None))
        self.faces_updated.emit(updated_faces)
        self.people_changed.emit()

    def _confirm_suggestion(self, fr: FaceRect, person_name: str) -> None:
        """
        FR: Valide la suggestion de visage et l'enregistre dans la base et `.picasa.ini`.
        EN: Confirms the face suggestion and saves it to the database and `.picasa.ini`.
        """
        if not self.db:
            return

        db_i = self.photo_index if self.photo_index >= 0 else None
        # Trouver la suggestion dans face_manager si elle existe
        sug_obj = None
        for sugs in self.db.face_manager.suggestions.values():
            for s in sugs:
                if s.photo_path == self.photo_path and s.contact_name.lower() == person_name.lower():
                    sug_obj = s
                    break
            if sug_obj:
                break

        if sug_obj:
            self.db.face_manager.confirm_suggestion(sug_obj)
        else:
            self.db.face_manager.add_face(self.photo_path, fr, person_name, db_idx=db_i)

        updated_faces = self.db.face_manager.get_faces_for_photo(self.photo_index) if self.photo_index >= 0 else []
        self.set_photo_faces(self.db, self.photo_index, self.photo_path, updated_faces, source_img=getattr(self, "cached_source_img", None))
        self.faces_updated.emit(updated_faces)
        self.people_changed.emit()

    def _reject_suggestion(self, fr: FaceRect) -> None:
        """
        FR: Rejette la suggestion de visage et réinitialise le visage en non identifié.
        EN: Rejects the face suggestion and resets the face to unidentified.
        """
        if not self.db:
            return

        for sugs in self.db.face_manager.suggestions.values():
            for s in list(sugs):
                if s.photo_path == self.photo_path and _face_overlap(s.face_rect, fr) >= 0.5:
                    self.db.face_manager.reject_suggestion(s)

        fr.contact_name = None
        fr.contact_id = ""
        updated_faces = self.db.face_manager.get_faces_for_photo(self.photo_index) if self.photo_index >= 0 else []
        self.set_photo_faces(self.db, self.photo_index, self.photo_path, updated_faces, source_img=getattr(self, "cached_source_img", None))
        self.faces_updated.emit(updated_faces)

    def _delete_face(self, fr: FaceRect) -> None:
        """
        FR: Supprime le visage de la photo et du fichier `.picasa.ini`.
        EN: Removes the face from the photo and from the `.picasa.ini` file.
        """
        if not self.db:
            return
        db_i = self.photo_index if self.photo_index >= 0 else None
        self.db.face_manager.remove_face(self.photo_path, fr, db_idx=db_i)
        updated_faces = self.db.face_manager.get_faces_for_photo(self.photo_index) if self.photo_index >= 0 else []
        self.set_photo_faces(self.db, self.photo_index, self.photo_path, updated_faces, source_img=getattr(self, "cached_source_img", None))
        self.faces_updated.emit(updated_faces)
        self.people_changed.emit()



# =============================================================================
# 2. VOLET DES LIEUX / PLACES PANEL (Carte Interactive Leaflet)
# =============================================================================

# Base de données hors-ligne de villes et monuments de référence pour une résolution
# instantanée et un fonctionnement garanti même sans connexion Internet ou sous pare-feu.
OFFLINE_PLACES_GAZETTEER: Dict[str, Tuple[float, float, str]] = {
    "paris": (48.856614, 2.352222, "Paris, Île-de-France, France"),
    "tour eiffel": (48.858370, 2.294481, "Tour Eiffel, Paris, France"),
    "musée du louvre": (48.860611, 2.337644, "Musée du Louvre, Paris, France"),
    "louvre": (48.860611, 2.337644, "Musée du Louvre, Paris, France"),
    "notre-dame de paris": (48.852968, 2.349902, "Cathédrale Notre-Dame de Paris, France"),
    "arc de triomphe": (48.873792, 2.295028, "Arc de Triomphe, Paris, France"),
    "montmartre": (48.886705, 2.343104, "Montmartre, Paris, France"),
    "versailles": (48.804865, 2.120355, "Versailles, Yvelines, France"),
    "lyon": (45.764043, 4.835659, "Lyon, Auvergne-Rhône-Alpes, France"),
    "marseille": (43.296482, 5.369780, "Marseille, Provence-Alpes-Côte d'Azur, France"),
    "bordeaux": (44.837789, -0.579180, "Bordeaux, Nouvelle-Aquitaine, France"),
    "toulouse": (43.604652, 1.444209, "Toulouse, Occitanie, France"),
    "nice": (43.710173, 7.261953, "Nice, Provence-Alpes-Côte d'Azur, France"),
    "nantes": (47.218371, -1.553621, "Nantes, Pays de la Loire, France"),
    "strasbourg": (48.573405, 7.752111, "Strasbourg, Grand Est, France"),
    "lille": (50.629250, 3.057256, "Lille, Hauts-de-France, France"),
    "rennes": (48.117266, -1.677793, "Rennes, Bretagne, France"),
    "montpellier": (43.610769, 3.876716, "Montpellier, Occitanie, France"),
    "grenoble": (45.188529, 5.724524, "Grenoble, Auvergne-Rhône-Alpes, France"),
    "dijon": (47.322047, 5.041480, "Dijon, Bourgogne-Franche-Comté, France"),
    "angers": (47.478419, -0.563166, "Angers, Pays de la Loire, France"),
    "nîmes": (43.836699, 4.360054, "Nîmes, Occitanie, France"),
    "nimes": (43.836699, 4.360054, "Nîmes, Occitanie, France"),
    "aix-en-provence": (43.529742, 5.447427, "Aix-en-Provence, France"),
    "brest": (48.390394, -4.486076, "Brest, Bretagne, France"),
    "tours": (47.394144, 0.684840, "Tours, Centre-Val de Loire, France"),
    "annecy": (45.899247, 6.129384, "Annecy, Haute-Savoie, France"),
    "chamonix": (45.923697, 6.869433, "Chamonix-Mont-Blanc, France"),
    "mont-saint-michel": (48.636063, -1.511457, "Le Mont-Saint-Michel, Normandie, France"),
    "mont saint michel": (48.636063, -1.511457, "Le Mont-Saint-Michel, Normandie, France"),
    "avignon": (43.949317, 4.805528, "Avignon, Vaucluse, France"),
    "cannes": (43.552847, 7.017369, "Cannes, Alpes-Maritimes, France"),
    "biarritz": (43.483152, -1.558626, "Biarritz, Pyrénées-Atlantiques, France"),
    "la rochelle": (46.160329, -1.151139, "La Rochelle, Charente-Maritime, France"),
    "saint-malo": (48.649337, -2.025674, "Saint-Malo, Ille-et-Vilaine, France"),
    "londres": (51.507351, -0.127758, "Londres, Royaume-Uni"),
    "london": (51.507351, -0.127758, "London, United Kingdom"),
    "new york": (40.712776, -74.005974, "New York, NY, États-Unis"),
    "tokyo": (35.676192, 139.650311, "Tokyo, Japon"),
    "rome": (41.902782, 12.496366, "Rome, Italie"),
    "roma": (41.902782, 12.496366, "Rome, Italie"),
    "madrid": (40.416775, -3.703790, "Madrid, Espagne"),
    "barcelone": (41.385064, 2.173404, "Barcelone, Catalogne, Espagne"),
    "barcelona": (41.385064, 2.173404, "Barcelone, Catalogne, Espagne"),
    "berlin": (52.520007, 13.404954, "Berlin, Allemagne"),
    "bruxelles": (50.850340, 4.351710, "Bruxelles, Belgique"),
    "brussels": (50.850340, 4.351710, "Bruxelles, Belgique"),
    "genève": (46.204391, 6.143158, "Genève, Suisse"),
    "geneve": (46.204391, 6.143158, "Genève, Suisse"),
    "geneva": (46.204391, 6.143158, "Genève, Suisse"),
    "montréal": (45.501689, -73.567256, "Montréal, Québec, Canada"),
    "montreal": (45.501689, -73.567256, "Montréal, Québec, Canada"),
    "sydney": (-33.868820, 151.209296, "Sydney, Australie"),
    "san francisco": (37.774929, -122.419416, "San Francisco, CA, États-Unis"),
    "los angeles": (34.052234, -118.243685, "Los Angeles, CA, États-Unis"),
    "rio de janeiro": (-22.906847, -43.172896, "Rio de Janeiro, Brésil"),
    "amsterdam": (52.367573, 4.904139, "Amsterdam, Pays-Bas"),
    "lisbonne": (38.722252, -9.139337, "Lisbonne, Portugal"),
    "lisbon": (38.722252, -9.139337, "Lisbonne, Portugal"),
    "vienne": (48.208174, 16.373819, "Vienne, Autriche"),
    "vienna": (48.208174, 16.373819, "Vienne, Autriche"),
    "prague": (50.075538, 14.437800, "Prague, République tchèque"),
    "venise": (45.440847, 12.315515, "Venise, Italie"),
    "florence": (43.769560, 11.255814, "Florence, Italie"),
    "athènes": (37.983810, 23.727539, "Athènes, Grèce"),
    "athenes": (37.983810, 23.727539, "Athènes, Grèce"),
    "dublin": (53.349805, -6.260310, "Dublin, Irlande"),
}


def parse_gps_coordinates_query(query: str) -> Optional[Tuple[float, float, str]]:
    """
    FR: Analyse une saisie directe de coordonnées GPS décimales (ex: '48.8584, 2.2945' ou '48.8584 2.2945').
    EN: Parses a direct decimal GPS coordinates input (e.g., '48.8584, 2.2945' or '48.8584 2.2945').
    """
    import re
    q = query.strip()
    m = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*[,;\s]\s*([+-]?\d+(?:\.\d+)?)$", q)
    if m:
        try:
            lat = float(m.group(1))
            lon = float(m.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return (lat, lon, f"{lat:.5f}, {lon:.5f}")
        except ValueError:
            pass
    return None


def lookup_offline_gazetteer(query: str) -> Optional[Tuple[float, float, str]]:
    """
    FR: Recherche une correspondance exacte ou partielle dans le dictionnaire géographique embarqué.
    EN: Searches for an exact or partial match in the embedded offline geographical gazetteer.
    """
    norm = query.strip().lower()
    if not norm:
        return None
    if norm in OFFLINE_PLACES_GAZETTEER:
        return OFFLINE_PLACES_GAZETTEER[norm]
    # Correspondance sur le premier segment avant une virgule (ex: "Paris, France")
    first_part = norm.split(",")[0].strip()
    if first_part in OFFLINE_PLACES_GAZETTEER:
        return OFFLINE_PLACES_GAZETTEER[first_part]
    for key, val in OFFLINE_PLACES_GAZETTEER.items():
        if key in norm or norm in key:
            return val
    return None


class GeocodeWorker(QThread):
    """
    FR: Thread de géocodage multi-sources (Coordonnées directes, Nominatim OSM, Photon Komoot,
    Open-Meteo Geocoding et dictionnaire hors-ligne de secours).
    EN: Multi-source geocoding worker thread (direct coordinates, Nominatim OSM, Photon Komoot,
    Open-Meteo Geocoding, and fallback offline gazetteer).
    Ref: picasa3.exe @ 0x008A9A00 (GeoPanel search, geo::search_err)
    """
    result_ready = Signal(float, float, str)
    search_failed = Signal(str)

    def __init__(self, query: str):
        """
        FR: Initialise le thread de géocodage avec la requête de recherche.
        EN: Initializes the geocoding thread with the search query.
        """
        super().__init__()
        self.query = query.strip()

    @staticmethod
    def geocode_sync(query: str, timeout: float = 3.5) -> Optional[Tuple[float, float, str]]:
        """
        FR: Résout une adresse ou des coordonnées GPS en `(lat, lon, display_name)`.
        EN: Resolves an address or GPS coordinates into `(lat, lon, display_name)`.
        """
        import ssl
        q = query.strip()
        if not q:
            return None

        # 1. Coordonnées GPS directes
        coords = parse_gps_coordinates_query(q)
        if coords:
            return coords

        # 2. Correspondance exacte dans le dictionnaire de référence (instantané)
        norm = q.lower()
        if norm in OFFLINE_PLACES_GAZETTEER:
            return OFFLINE_PLACES_GAZETTEER[norm]
        first_seg = norm.split(",")[0].strip()
        if first_seg in OFFLINE_PLACES_GAZETTEER and len(norm.split(",")) <= 2:
            return OFFLINE_PLACES_GAZETTEER[first_seg]

        # Contextes SSL (standard puis sans vérification si certificats Windows absents)
        ssl_contexts = [None]
        try:
            ssl_contexts.append(ssl._create_unverified_context())
        except Exception:
            pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PyCasa/3.9 PicasaGeoPanel/1.0",
            "Accept": "application/json",
            "Accept-Language": "fr,en;q=0.8",
        }

        # 3. Nominatim OpenStreetMap
        nom_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=1"
        for ctx in ssl_contexts:
            try:
                req = urllib.request.Request(nom_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data and len(data) > 0:
                        return (
                            float(data[0]["lat"]),
                            float(data[0]["lon"]),
                            str(data[0].get("display_name", q)),
                        )
            except Exception:
                continue

        # 4. Photon Komoot (OSM)
        photon_url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(q)}&limit=1&lang=fr"
        for ctx in ssl_contexts:
            try:
                req = urllib.request.Request(photon_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    feats = data.get("features", [])
                    if feats:
                        geom = feats[0].get("geometry", {})
                        coords_list = geom.get("coordinates", [])
                        props = feats[0].get("properties", {})
                        if len(coords_list) >= 2:
                            lon, lat = float(coords_list[0]), float(coords_list[1])
                            parts = [props.get("name"), props.get("city"), props.get("country")]
                            disp = ", ".join(p for p in parts if p) or q
                            return (lat, lon, disp)
            except Exception:
                continue

        # 5. Open-Meteo Geocoding API
        meteo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(q)}&count=1&language=fr&format=json"
        for ctx in ssl_contexts:
            try:
                req = urllib.request.Request(meteo_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results", [])
                    if results:
                        r0 = results[0]
                        lat = float(r0["latitude"])
                        lon = float(r0["longitude"])
                        parts = [r0.get("name"), r0.get("admin1"), r0.get("country")]
                        disp = ", ".join(p for p in parts if p) or q
                        return (lat, lon, disp)
            except Exception:
                continue

        # 6. Secours hors-ligne partiel
        return lookup_offline_gazetteer(q)

    def run(self) -> None:
        """
        FR: Exécute la requête de géocodage en arrière-plan et émet le résultat ou l'échec.
        EN: Executes the geocoding request in the background and emits the result or failure.
        """
        res = self.geocode_sync(self.query)
        if res is not None:
            lat, lon, display_name = res
            self.result_ready.emit(lat, lon, display_name)
        else:
            self.search_failed.emit(self.query)


class PicasaPlacesPanel(QWidget):
    """
    FR: Volet cartographique interactif basé sur Leaflet et OpenStreetMap.
    Reproduit fidèlement la disposition et le comportement de `geopanel.tre` :
    - Barre supérieure (`geopanel/top_bar`) : compteur de lieux dans l'album (`geopanel/geo_info`,
      `GeoPanel::geo_info_format` = "%d %s dans %s") + sélecteur de carte (`geopanel/map_menu` : Plan, Relief, Satellite)
    - Carte interactive centrale (`geopanel/map`) : affiche tous les marqueurs géolocalisés de l'album
      ainsi que le marqueur actif / recherché.
    - Barre d'actions GPS : bouton « Placer ici » (`GeoPanel::infowindowhtml`) et bouton
      « Effacer la géolocalisation » (`geopanel/cleargeotag`).
    - Barre inférieure de recherche (`geopanel/search_label` + `geopanel/search_group`) :
      champ d'adresse avec autocomplétion + bouton Rechercher + affichage DMS/adresse.

    EN: Interactive map panel based on Leaflet and OpenStreetMap.
    Faithfully reproduces the layout and behavior of `geopanel.tre`:
    - Top bar (`geopanel/top_bar`): place counter in the album (`geopanel/geo_info`,
      `GeoPanel::geo_info_format` = "%d %s in %s") + map type selector (`geopanel/map_menu`: Plan, Relief, Satellite)
    - Central interactive map (`geopanel/map`): displays all geotagged markers of the album
      along with the active/searched marker.
    - GPS action bar: "Place here" button (`GeoPanel::infowindowhtml`) and
      "Clear geotag" button (`geopanel/cleargeotag`).
    - Bottom search bar (`geopanel/search_label` + `geopanel/search_group`):
      address input with autocompletion + Search button + DMS/address display.

    Ref: picasa3.exe @ 0x008A9A00 (GeoPanel::geo_info_format, GeoPanel::infowindowhtml, GeotagPanel::clearbutton)
    Ref: respack.yt @ geopanel.tre (top_bar, geo_info, map_menu, map, cleargeotag, search_label, search_group)
    """
    location_changed = Signal(float, float)
    location_cleared = Signal()

    def __init__(self, parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        """
        FR: Initialise le volet Lieux avec sa carte WebEngine, sa barre de recherche et ses contrôles GPS.
        EN: Initializes the Places panel with its WebEngine map, search bar, and GPS controls.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle()
        self.current_lat: Optional[float] = None
        self.current_lon: Optional[float] = None
        self.current_filename: str = ""
        self.current_place_label: str = ""
        self.current_map_layer: str = "Plan"
        self.album_markers: List[Dict[str, Any]] = []
        self.album_scope_label: str = "l'album"
        self.geocode_worker: Optional[GeocodeWorker] = None

        from PySide6.QtWidgets import QComboBox
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)

        # ---------------------------------------------------------------------
        # 1. Barre supérieure : geopanel/top_bar (height=28px)
        #    Gauche : geopanel/geo_info ("X lieux dans l'album" / "Aucun lieu trouvé.")
        #    Droite : geopanel/map_menu (Plan / Relief / Satellite)
        # ---------------------------------------------------------------------
        self.top_bar = QFrame(self)
        self.top_bar.setFixedHeight(28)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(6, 2, 4, 2)
        top_layout.setSpacing(4)

        self.lbl_geo_info = QLabel("Aucun lieu trouvé.")
        top_layout.addWidget(self.lbl_geo_info, 1)

        self.combo_map_type = QComboBox(self.top_bar)
        self.combo_map_type.addItems(["Plan", "Relief", "Satellite"])
        self.combo_map_type.setFixedWidth(78)
        self.combo_map_type.setToolTip("Type de carte (geopanel/map_menu)")
        self.combo_map_type.currentTextChanged.connect(self._on_map_type_changed)
        top_layout.addWidget(self.combo_map_type)

        layout.addWidget(self.top_bar)

        # ---------------------------------------------------------------------
        # 2. Vue cartographique Leaflet (QWebEngineView - geopanel/map)
        # ---------------------------------------------------------------------
        self.web_view = QWebEngineView(self)
        self.web_view.titleChanged.connect(self._on_webview_title_changed)
        layout.addWidget(self.web_view, 1)

        # ---------------------------------------------------------------------
        # 3. Barre d'actions de géolocalisation (Placer ici / Effacer la géolocalisation)
        #    Ref: GeoPanel::infowindowhtml ("Place %d photos here"), geopanel/cleargeotag
        # ---------------------------------------------------------------------
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(4)

        self.btn_place_here = QPushButton("📍 Placer ici")
        self.btn_place_here.setToolTip("Enregistrer cet emplacement GPS sur la ou les photos sélectionnées")
        self.btn_place_here.setFixedHeight(24)
        self.btn_place_here.clicked.connect(self._on_place_here_clicked)
        self.btn_place_here.setEnabled(False)
        action_row.addWidget(self.btn_place_here, 1)

        self.btn_clear_geotag = QPushButton("🗑 Effacer")
        self.btn_clear_geotag.setToolTip("Effacer la géolocalisation de la sélection (geopanel/cleargeotag)")
        self.btn_clear_geotag.setFixedHeight(24)
        self.btn_clear_geotag.clicked.connect(self._on_clear_geotag_clicked)
        self.btn_clear_geotag.setEnabled(False)
        action_row.addWidget(self.btn_clear_geotag)

        layout.addLayout(action_row)

        # ---------------------------------------------------------------------
        # 4. Barre inférieure : geopanel/search_label + geopanel/search_group
        # ---------------------------------------------------------------------
        self.lbl_search_title = QLabel("Rechercher une adresse :")
        layout.addWidget(self.lbl_search_title)

        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)

        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("Ville, adresse ou coordonnées GPS (ex: Paris, 48.85, 2.35)...")
        # Autocomplétion sur les grandes villes et monuments
        completer_items = [val[2] for val in OFFLINE_PLACES_GAZETTEER.values()]
        seen_c = set()
        unique_completer = []
        for item in completer_items:
            if item not in seen_c:
                seen_c.add(item)
                unique_completer.append(item)
        completer = QCompleter(unique_completer, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.txt_search.setCompleter(completer)
        self.txt_search.returnPressed.connect(self._on_search_address)
        search_layout.addWidget(self.txt_search, 1)

        self.btn_search = QPushButton("🔍")
        self.btn_search.setToolTip("Rechercher ce lieu sur la carte")
        self.btn_search.setFixedSize(30, 26)
        self.btn_search.clicked.connect(self._on_search_address)
        search_layout.addWidget(self.btn_search)

        layout.addLayout(search_layout)

        # 5. Informations de coordonnées GPS / résultat de recherche
        self.lbl_coords = QLabel("Aucune coordonnée GPS")
        self.lbl_coords.setWordWrap(True)
        self.lbl_coords.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_coords)

        self.apply_style(self.style)
        # Initialiser avec une vue par défaut
        self.update_map(None, None, "Photo")

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique le style visuel Picasa 3 au volet Lieux.
        EN: Applies the Picasa 3 visual style to the Places panel.
        """
        style = style or PicasaStyle.instance()
        self.style = style
        is_dark = style.is_dark
        txt = style.alist_textcolor.name()
        sub = style.alayout_subtitleColor.name()
        accent = style.accent_color.name()
        border = style.splitter_color.name() if is_dark else style.topbar_border_color.name()
        bar_bg = style.window_bgcolor.darker(108).name() if is_dark else style.window_bgcolor.name()
        btn_bg = style.topbar_btn_bg_start.name()
        btn_hover = style.topbar_btn_bg_end.name()
        btn_border = style.topbar_btn_border.name()
        input_bg = style.window_bgcolor.darker(115).name() if is_dark else "#FFFFFF"
        dis_bg = style.drawer_bgcolor.darker(105).name()

        self.top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {bar_bg};
                border: 1px solid {border};
                border-radius: 3px;
            }}
        """)
        self.lbl_geo_info.setStyleSheet(
            f"color: {txt}; font-size: 11px; font-weight: bold; border: none; background: transparent;"
        )
        self.combo_map_type.setStyleSheet(f"""
            QComboBox {{
                background-color: {btn_bg};
                color: {txt};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 1px 4px;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bar_bg};
                color: {txt};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                font-size: 9pt;
            }}
        """)
        self.web_view.setStyleSheet(f"background-color: #E5E3DF; border: 1px solid {border}; border-radius: 4px;")
        self.btn_place_here.setStyleSheet(f"""
            QPushButton {{
                background-color: #2D6A3E;
                color: #FFFFFF;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #367F4A;
            }}
            QPushButton:disabled {{
                background-color: {dis_bg};
                color: {sub};
                border-color: {border};
            }}
        """)
        self.btn_clear_geotag.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {txt};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: #C94A4A;
                border-color: #C94A4A;
                color: #FFFFFF;
            }}
            QPushButton:disabled {{
                background-color: {dis_bg};
                color: {sub};
                border-color: {border};
            }}
        """)
        self.lbl_search_title.setStyleSheet(
            f"color: {sub}; font-size: 10px; font-weight: bold; background: transparent;"
        )
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {txt};
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
        """)
        self.btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #FFFFFF;
                border: 1px solid {accent};
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {style.accent_color.lighter(115).name()};
            }}
        """)
        has_active_coords = self.current_lat is not None and self.current_lon is not None
        coord_col = accent if (has_active_coords and not is_dark) else ("#B8D4E8" if has_active_coords else sub)
        self.lbl_coords.setStyleSheet(f"color: {coord_col}; font-size: 10px; background: transparent;")

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes traduits du volet Lieux selon la langue active.
        EN: Updates translated texts of the Places panel according to the active language.
        """
        res = PicasaResourceManager.get()
        place_txt = res.get_xml_string("geopanel/place_button", "Placer la photo")
        self.btn_place_here.setText(f"📍 {place_txt}")
        clear_txt = res.get_xml_string("geopanel/cleargeotag", "Effacer")
        self.btn_clear_geotag.setText(f"🗑 {clear_txt}")
        search_lbl = res.get_xml_string("geopanel/search_label", "Rechercher une adresse :")
        self.lbl_search_title.setText(search_lbl)
        self._update_geo_info_header()

    def _on_map_type_changed(self, layer_name: str) -> None:
        """
        FR: Change le fond de carte actif (Plan, Relief, Satellite) et recharge la vue Leaflet.
        EN: Changes the active map layer (Plan, Relief, Satellite) and reloads the Leaflet view.
        """
        self.current_map_layer = layer_name
        self._render_leaflet_html()

    def set_album_context(
        self,
        album_markers: List[Dict[str, Any]],
        scope_label: str = "l'album",
    ) -> None:
        """
        FR: Définit la liste des photos géolocalisées de l'album/dossier actif et met à jour
        le compteur `geopanel/geo_info` (« X lieu(x) dans l'album ») ainsi que les marqueurs.
        EN: Sets the list of geotagged photos for the active album/folder and updates
        the `geopanel/geo_info` counter ("X place(s) in the album") and map markers.
        Ref: picasa3.exe @ 0x008A9A00 (GeoPanel::geo_info_format = "%d %s in %s")
        """
        self.album_markers = list(album_markers)
        self.album_scope_label = scope_label
        self._update_geo_info_header()
        self._render_leaflet_html()

    def _update_geo_info_header(self) -> None:
        """
        FR: Calcule et affiche le nombre d'emplacements distincts dans l'album ou la sélection.
        EN: Computes and displays the number of distinct locations in the album or selection.
        Ref: picasa3.exe @ 0x008A9A00 (GeoPanel::geo_info_no_selection, geo_info_single, geo_info_format)
        """
        unique_coords = {
            (round(float(m["lat"]), 3), round(float(m["lon"]), 3))
            for m in self.album_markers
            if m.get("lat") is not None and m.get("lon") is not None
        }
        if self.current_lat is not None and self.current_lon is not None:
            unique_coords.add((round(self.current_lat, 3), round(self.current_lon, 3)))

        n_places = len(unique_coords)
        n_photos = len(self.album_markers)

        if n_places > 0:
            lieu_str = "lieu" if n_places == 1 else "lieux"
            if n_photos > n_places:
                self.lbl_geo_info.setText(f"{n_places} {lieu_str} dans {self.album_scope_label} ({n_photos} photos)")
            else:
                self.lbl_geo_info.setText(f"{n_places} {lieu_str} dans {self.album_scope_label}")
        elif self.current_lat is not None and self.current_lon is not None:
            self.lbl_geo_info.setText("Emplacement de la photo")
        else:
            self.lbl_geo_info.setText("Aucun lieu trouvé.")

    def update_map(
        self,
        lat: Optional[float],
        lon: Optional[float],
        filename: str = "",
        place_label: str = "",
        album_markers: Optional[List[Dict[str, Any]]] = None,
        scope_label: Optional[str] = None,
    ) -> None:
        """
        FR: Met à jour la position active, les marqueurs de l'album et rafraîchit la carte Leaflet.
        EN: Updates the active position, album markers, and refreshes the Leaflet map.
        """
        self.current_lat = lat
        self.current_lon = lon
        self.current_filename = filename
        self.current_place_label = place_label
        if album_markers is not None:
            self.album_markers = list(album_markers)
        if scope_label is not None:
            self.album_scope_label = scope_label

        has_active_coords = lat is not None and lon is not None
        self.btn_place_here.setEnabled(has_active_coords)
        self.btn_clear_geotag.setEnabled(has_active_coords)

        sub = self.style.alayout_subtitleColor.name()
        active_col = "#B8D4E8" if self.style.is_dark else self.style.accent_color.name()

        if has_active_coords and lat is not None and lon is not None:
            dms = format_gps_dms(lat, lon)
            if place_label:
                self.lbl_coords.setText(f"📍 {place_label}\n({dms})")
            else:
                self.lbl_coords.setText(dms)
            self.lbl_coords.setStyleSheet(f"color: {active_col}; font-size: 10px; background: transparent;")
        else:
            if self.album_markers:
                self.lbl_coords.setText(
                    f"Cette photo n'a pas de géolocalisation ({len(self.album_markers)} photo(s) géolocalisée(s) dans {self.album_scope_label})."
                )
            else:
                self.lbl_coords.setText("Cette photo n'a pas de géolocalisation.")
            self.lbl_coords.setStyleSheet(f"color: {sub}; font-size: 10px; background: transparent;")

        self._update_geo_info_header()
        self._render_leaflet_html()

    def _render_leaflet_html(self) -> None:
        """
        FR: Génère et injecte la page HTML/JavaScript Leaflet dans le QWebEngineView.
        EN: Generates and injects the Leaflet HTML/JavaScript page into the QWebEngineView.
        """
        lat = self.current_lat
        lon = self.current_lon
        filename = (self.current_filename or "Emplacement").replace("'", "\\'").replace('"', "&quot;")
        place_sub = (self.current_place_label or "").replace("'", "\\'").replace('"', "&quot;")

        if lat is not None and lon is not None:
            zoom = 14
            has_marker = True
            m_lat, m_lon = float(lat), float(lon)
        elif self.album_markers:
            # Centrer sur le barycentre des marqueurs de l'album
            lats = [float(m["lat"]) for m in self.album_markers if m.get("lat") is not None]
            lons = [float(m["lon"]) for m in self.album_markers if m.get("lon") is not None]
            m_lat = sum(lats) / len(lats) if lats else 46.603354
            m_lon = sum(lons) / len(lons) if lons else 1.888334
            zoom = 11 if len(lats) == 1 else 6
            has_marker = False
        else:
            zoom = 5
            has_marker = False
            m_lat, m_lon = 46.603354, 1.888334  # Centre de la France

        # Choix de la couche de tuiles selon combo_map_type (Plan / Relief / Satellite)
        if self.current_map_layer == "Relief":
            tile_url = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            tile_attr = "© OpenTopoMap (CC-BY-SA)"
        elif self.current_map_layer == "Satellite":
            tile_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            tile_attr = "© Esri World Imagery"
        else:
            tile_url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            tile_attr = "© OpenStreetMap"

        # Regroupement des marqueurs de l'album par emplacement proche
        grouped_album: Dict[Tuple[float, float], List[str]] = {}
        for m in self.album_markers:
            mlat = m.get("lat")
            mlon = m.get("lon")
            if mlat is None or mlon is None:
                continue
            key = (round(float(mlat), 4), round(float(mlon), 4))
            grouped_album.setdefault(key, []).append(str(m.get("filename", "Photo")))

        album_markers_js_list = []
        for (glat, glon), names in grouped_album.items():
            # Éviter de superposer exactement au marqueur vert actif
            if has_marker and abs(glat - m_lat) < 1e-4 and abs(glon - m_lon) < 1e-4:
                continue
            count = len(names)
            sample = ", ".join(names[:3]).replace("'", "\\'").replace('"', "&quot;")
            if count > 3:
                sample += f" (+{count - 3})"
            label_popup = f"<b>{count} photo{'s' if count > 1 else ''} ici</b><br>{sample}<br><span style=\"color:#666\">{glat:.4f}, {glon:.4f}</span>"
            album_markers_js_list.append(
                f"L.circleMarker([{glat}, {glon}], {{radius: 7, fillColor: '#E53935', color: '#FFFFFF', weight: 2, fillOpacity: 0.9}}).addTo(map).bindPopup('{label_popup}');"
            )
        album_markers_js = "\n    ".join(album_markers_js_list)

        active_popup = f"<b>{filename}</b>"
        if place_sub and place_sub != filename:
            active_popup += f"<br>{place_sub}"
        active_popup += f"<br>{m_lat:.5f}, {m_lon:.5f}"

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html, #map {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #E5E3DF; }}
    .leaflet-popup-content {{ font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 11px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    if (typeof L !== 'undefined') {{
      var map = L.map('map', {{ zoomControl: true }}).setView([{m_lat}, {m_lon}], {zoom});
      L.tileLayer('{tile_url}', {{
        maxZoom: 19,
        attribution: '{tile_attr}'
      }}).addTo(map);

      {album_markers_js}

      var marker = null;
      {f"marker = L.marker([{m_lat}, {m_lon}], {{draggable: true}}).addTo(map).bindPopup('{active_popup}').openPopup();" if has_marker else ""}

      map.on('click', function(e) {{
        if (marker) {{
          marker.setLatLng(e.latlng);
        }} else {{
          marker = L.marker(e.latlng, {{draggable: true}}).addTo(map);
        }}
        marker.bindPopup('<b>Emplacement sélectionné</b><br>' + e.latlng.lat.toFixed(5) + ', ' + e.latlng.lng.toFixed(5)).openPopup();
        document.title = 'GEO:' + e.latlng.lat.toFixed(6) + ',' + e.latlng.lng.toFixed(6);
      }});

      if (marker) {{
        marker.on('dragend', function(e) {{
          var pos = marker.getLatLng();
          marker.bindPopup('<b>Emplacement déplacé</b><br>' + pos.lat.toFixed(5) + ', ' + pos.lng.toFixed(5)).openPopup();
          document.title = 'GEO:' + pos.lat.toFixed(6) + ',' + pos.lng.toFixed(6);
        }});
      }}
    }}
  </script>
</body>
</html>"""
        self.web_view.setHtml(html)

    def _on_webview_title_changed(self, title: str) -> None:
        """
        FR: Récupère les coordonnées cliquées ou déplacées à la souris dans la carte Leaflet.
        EN: Retrieves coordinates clicked or dragged with the mouse in the Leaflet map.
        """
        if title and title.startswith("GEO:"):
            try:
                parts = title[4:].split(",")
                if len(parts) == 2:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    self.current_lat = lat
                    self.current_lon = lon
                    self.btn_place_here.setEnabled(True)
                    self.btn_clear_geotag.setEnabled(True)
                    ok_col = "#81C784" if self.style.is_dark else "#2E7D32"
                    self.lbl_coords.setText(f"📍 Sélection carte : {format_gps_dms(lat, lon)}")
                    self.lbl_coords.setStyleSheet(f"color: {ok_col}; font-size: 10px; background: transparent;")
                    self._update_geo_info_header()
                    self.location_changed.emit(lat, lon)
            except Exception:
                pass

    def _on_place_here_clicked(self) -> None:
        """
        FR: Valide et enregistre les coordonnées actuelles sur la ou les photos sélectionnées.
        EN: Confirms and saves the current coordinates onto the selected photo(s).
        """
        if self.current_lat is not None and self.current_lon is not None:
            self.location_changed.emit(self.current_lat, self.current_lon)
            ok_col = "#81C784" if self.style.is_dark else "#2E7D32"
            self.lbl_coords.setText(
                f"✓ Emplacement enregistré : {self.current_place_label or format_gps_dms(self.current_lat, self.current_lon)}"
            )
            self.lbl_coords.setStyleSheet(f"color: {ok_col}; font-size: 10px; font-weight: bold; background: transparent;")
            self._update_geo_info_header()

    def _on_clear_geotag_clicked(self) -> None:
        """
        FR: Efface la géolocalisation de la photo ou sélection active (Ref: geopanel/cleargeotag).
        EN: Clears the geotag of the active photo or selection (Ref: geopanel/cleargeotag).
        """
        self.current_lat = None
        self.current_lon = None
        self.current_place_label = ""
        self.btn_place_here.setEnabled(False)
        self.btn_clear_geotag.setEnabled(False)
        self.location_cleared.emit()
        self.update_map(None, None, self.current_filename)

    def _on_search_address(self) -> None:
        """
        FR: Lance la recherche géographique synchrone ou asynchrone pour l'adresse saisie.
        EN: Starts synchronous or asynchronous geographical search for the entered address.
        """
        query = self.txt_search.text().strip()
        if not query:
            return

        # 1. Résolution synchrone rapide si coordonnées GPS ou ville connue du gazetteer
        coords = parse_gps_coordinates_query(query)
        if coords is not None:
            self._on_geocode_success(*coords)
            return

        norm = query.lower()
        if norm in OFFLINE_PLACES_GAZETTEER:
            self._on_geocode_success(*OFFLINE_PLACES_GAZETTEER[norm])
            return
        first_seg = norm.split(",")[0].strip()
        if first_seg in OFFLINE_PLACES_GAZETTEER and len(norm.split(",")) <= 2:
            self._on_geocode_success(*OFFLINE_PLACES_GAZETTEER[first_seg])
            return

        # 2. Recherche asynchrone multi-fournisseurs (Nominatim / Photon / Open-Meteo + fallback)
        warn_col = "#FFD54F" if self.style.is_dark else "#B75D00"
        self.lbl_coords.setText(f"Recherche de « {query} » en cours...")
        self.lbl_coords.setStyleSheet(f"color: {warn_col}; font-size: 10px; background: transparent;")
        self.btn_search.setEnabled(False)

        self.geocode_worker = GeocodeWorker(query)
        self.geocode_worker.result_ready.connect(self._on_geocode_success)
        self.geocode_worker.search_failed.connect(self._on_geocode_failed)
        self.geocode_worker.finished.connect(lambda: self.btn_search.setEnabled(True))
        self.geocode_worker.start()

    def _on_geocode_success(self, lat: float, lon: float, display_name: str) -> None:
        """
        FR: Met à jour la carte et émet les nouvelles coordonnées après un géocodage réussi.
        EN: Updates the map and emits the new coordinates after a successful geocoding.
        """
        self.btn_search.setEnabled(True)
        self.update_map(
            lat,
            lon,
            self.current_filename or display_name,
            place_label=display_name,
        )
        self.location_changed.emit(lat, lon)

    def _on_geocode_failed(self, query: str) -> None:
        """
        FR: Affiche un message d'erreur lorsque la recherche d'adresse n'aboutit pas.
        EN: Displays an error message when the address search yields no result.
        """
        self.btn_search.setEnabled(True)
        err_col = "#FF8A80" if self.style.is_dark else "#C62828"
        self.lbl_coords.setText(f"Aucun résultat trouvé pour « {query} ».")
        self.lbl_coords.setStyleSheet(f"color: {err_col}; font-size: 10px; background: transparent;")



# =============================================================================
# 3. VOLET DES TAGS / TAG PANEL (Mots-clés & Tags rapides)
# =============================================================================
class PicasaQuickTagConfigDialog(QWidget):
    """
    FR: Boîte de dialogue « Configuration des tags rapides » (`QuickTagConfigDlg`).
    EN: "Quick Tag Configuration" dialog (`QuickTagConfigDlg`).
    Ref: picasa3.exe @ runtime/QUICKTAGCONFIG_TEXT_FR.XML (quicktagconfig/instructions,
         quicktagconfig/label_1..10, quicktagconfig/reserve_recent, quicktagconfig/fill_frequent)
    """

    def __init__(
        self,
        slots: List[str],
        reserve_recent: bool,
        frequent_tags: List[str],
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        """
        FR: Initialise la boîte de dialogue de configuration des 10 emplacements de tags rapides.
        EN: Initializes the configuration dialog for the 10 quick tag slots.
        """
        from PySide6.QtWidgets import QDialog, QGridLayout, QCheckBox
        super().__init__(parent)
        self.style = style or getattr(parent, "style", None) or PicasaStyle()
        self._dlg = QDialog(parent)
        self._dlg.setWindowTitle("Configuration des tags rapides")
        self._dlg.setMinimumWidth(420)
        self._frequent_tags = list(frequent_tags)

        is_dark = self.style.is_dark
        bg = self.style.drawer_bgcolor.name()
        txt = self.style.alist_textcolor.name()
        input_bg = self.style.window_bgcolor.darker(115).name() if is_dark else "#FFFFFF"
        btn_bg = self.style.topbar_btn_bg_start.name()
        btn_hover = self.style.topbar_btn_bg_end.name()
        btn_border = self.style.topbar_btn_border.name()
        accent = self.style.accent_color.name()
        self._dlg.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {txt};
            }}
            QLabel, QCheckBox {{
                color: {txt};
                font-size: 11px;
                background: transparent;
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {txt};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 3px 6px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {txt};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
        """)

        root = QVBoxLayout(self._dlg)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        lbl_inst = QLabel("Saisissez les tags que vous souhaitez associer aux boutons de tags rapides :")
        lbl_inst.setWordWrap(True)
        root.addWidget(lbl_inst)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        self.edits: List[QLineEdit] = []
        padded_slots = (list(slots) + [""] * 10)[:10]

        for i in range(10):
            key_num = (i + 1) % 10
            lbl = QLabel(f"Alt + {key_num}")
            ed = QLineEdit(padded_slots[i])
            if frequent_tags:
                _setup_inline_completer(ed, frequent_tags, style=self.style)
            self.edits.append(ed)
            row = i % 5
            col_base = 0 if i < 5 else 2
            grid.addWidget(lbl, row, col_base)
            grid.addWidget(ed, row, col_base + 1)

        root.addLayout(grid)

        self.chk_reserve_recent = QCheckBox(
            "Réserver les deux premiers boutons aux tags utilisés récemment"
        )
        self.chk_reserve_recent.setChecked(bool(reserve_recent))
        self.chk_reserve_recent.toggled.connect(self._on_reserve_toggled)
        root.addWidget(self.chk_reserve_recent)

        self.btn_fill_frequent = QPushButton(
            "Remplir les champs vides ci-dessus avec les tags fréquemment utilisés"
        )
        self.btn_fill_frequent.clicked.connect(self._on_fill_frequent)
        root.addWidget(self.btn_fill_frequent)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._dlg.accept)
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self._dlg.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

        self._on_reserve_toggled(self.chk_reserve_recent.isChecked())

    def _on_reserve_toggled(self, checked: bool) -> None:
        """
        FR: Active ou désactive les deux premiers champs lorsque la réservation aux tags récents change.
        EN: Enables or disables the first two fields when recent tag reservation is toggled.
        """
        for i in range(2):
            self.edits[i].setEnabled(not checked)
            if checked:
                self.edits[i].setPlaceholderText("(Tag récent)")
            else:
                self.edits[i].setPlaceholderText("")

    def _on_fill_frequent(self) -> None:
        """
        FR: Remplit automatiquement les emplacements vides avec les mots-clés les plus fréquents.
        EN: Automatically fills empty slots with the most frequently used keywords.
        """
        used = {ed.text().strip().lower() for ed in self.edits if ed.text().strip()}
        candidates = [t for t in self._frequent_tags if t.strip() and t.strip().lower() not in used]
        start_idx = 2 if self.chk_reserve_recent.isChecked() else 0
        c_idx = 0
        for i in range(start_idx, 10):
            if not self.edits[i].text().strip() and c_idx < len(candidates):
                self.edits[i].setText(candidates[c_idx])
                used.add(candidates[c_idx].strip().lower())
                c_idx += 1

    def exec(self) -> bool:
        """
        FR: Exécute la boîte de dialogue modale et retourne True si validée.
        EN: Executes the modal dialog and returns True if accepted.
        """
        return bool(self._dlg.exec())

    def get_config(self) -> Tuple[List[str], bool]:
        """
        FR: Retourne la liste des 10 tags rapides configurés et l'état de l'option des tags récents.
        EN: Returns the list of 10 configured quick tags and the state of the recent tags option.
        """
        return [ed.text().strip() for ed in self.edits], self.chk_reserve_recent.isChecked()


class PicasaTagsPanel(QWidget):
    """
    FR: Volet de gestion des mots-clés (tags) et des 10 Tags rapides (`Alt+1`..`Alt+0`) de la sélection.
    Sauvegarde directement dans le fichier `.picasa.ini` du dossier sous `[photo.jpg] keywords=...`.
    EN: Panel for managing keywords (tags) and the 10 Quick Tags (`Alt+1`..`Alt+0`) for the selection.
    Saves directly into the folder's `.picasa.ini` file under `[photo.jpg] keywords=...`.
    Ref: picasa3.exe @ runtime/TAGPANEL_TEXT_FR.XML, runtime/QUICKTAGCONFIG_TEXT_FR.XML, KEYWORDSTEXT_FR.XML
    """
    tags_changed = Signal(list)

    DEFAULT_QUICK_SLOTS: List[str] = [
        "Vacances",
        "Famille",
        "Voyage",
        "Nature",
        "Favoris",
        "Anniversaire",
        "Portrait",
        "Paysage",
        "Soirée",
        "Architecture",
    ]

    def __init__(self, parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        """
        FR: Initialise le volet Tags avec son champ de saisie, ses 10 boutons de tags rapides et sa liste.
        EN: Initializes the Tags panel with its input field, 10 quick tag buttons, and tag list.
        """
        from PySide6.QtWidgets import QGridLayout
        from PySide6.QtGui import QShortcut, QKeySequence
        super().__init__(parent)
        self.style = style or PicasaStyle()
        self.db: Optional[PicasaDatabase] = None
        self.photo_path: str = ""
        self.photo_paths: List[str] = []
        self.current_tags: List[str] = []
        self.selected_tag: Optional[str] = None

        self.quick_slots: List[str] = list(self.DEFAULT_QUICK_SLOTS)
        self.reserve_recent: bool = True
        self.recent_tags: List[str] = []
        self._config_loaded_from_db: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Champ d'ajout de tag (Ref: tagpanel/add_tag_label, tagpanel/add_button)
        self.add_lbl = QLabel("Entrez un tag à ajouter :")
        layout.addWidget(self.add_lbl)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)

        self.txt_tag = QLineEdit()
        self.txt_tag.setPlaceholderText("Nouveau tag...")
        self.txt_tag.returnPressed.connect(self._on_add_tag)
        input_layout.addWidget(self.txt_tag, 1)

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedWidth(30)
        self.btn_add.setToolTip("Ajouter le tag aux photos sélectionnées")
        self.btn_add.clicked.connect(self._on_add_tag)
        input_layout.addWidget(self.btn_add)

        layout.addLayout(input_layout)

        # 2. En-tête Tags rapides + bouton de configuration (Ref: tagpanel/quick_label, tagpanel/quick_config)
        quick_hdr = QHBoxLayout()
        quick_hdr.setContentsMargins(0, 2, 0, 0)
        self.quick_lbl = QLabel("Tags rapides :")
        quick_hdr.addWidget(self.quick_lbl)
        quick_hdr.addStretch(1)

        self.btn_quick_config = QPushButton("⚙")
        self.btn_quick_config.setFixedSize(24, 22)
        self.btn_quick_config.setToolTip("Configuration des tags rapides (Alt+1..Alt+0)...")
        self.btn_quick_config.clicked.connect(self.open_quick_tag_config_dialog)
        quick_hdr.addWidget(self.btn_quick_config)
        layout.addLayout(quick_hdr)

        # Grille des 10 boutons de Tags rapides (Alt+1 .. Alt+0)
        self.quick_grid_widget = QWidget(self)
        self.quick_grid = QGridLayout(self.quick_grid_widget)
        self.quick_grid.setContentsMargins(0, 0, 0, 0)
        self.quick_grid.setHorizontalSpacing(4)
        self.quick_grid.setVerticalSpacing(4)
        self.quick_buttons: List[QPushButton] = []
        self._quick_shortcuts: List[Any] = []

        for i in range(10):
            key_num = (i + 1) % 10
            btn_q = QPushButton()
            btn_q.setFixedHeight(24)
            btn_q.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_q.clicked.connect(lambda _, slot_idx=i: self._trigger_quick_tag_slot(slot_idx))
            self.quick_buttons.append(btn_q)
            self.quick_grid.addWidget(btn_q, i % 5, 0 if i < 5 else 1)

            sc = QShortcut(QKeySequence(f"Alt+{key_num}"), self)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(lambda slot_idx=i: self._trigger_quick_tag_slot(slot_idx))
            self._quick_shortcuts.append(sc)

        layout.addWidget(self.quick_grid_widget)
        self._refresh_quick_tag_buttons()

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 3. Liste des tags actuels + bouton Supprimer le tag (Ref: tagpanel/remove_button)
        current_hdr = QHBoxLayout()
        self.current_lbl = QLabel("Tags associés :")
        current_hdr.addWidget(self.current_lbl)
        current_hdr.addStretch(1)

        self.btn_remove_selected = QPushButton("Supprimer le tag")
        self.btn_remove_selected.setToolTip("Supprimer le tag sélectionné des photos (Suppr)")
        self.btn_remove_selected.setEnabled(False)
        self.btn_remove_selected.clicked.connect(self._on_remove_selected_tag)
        current_hdr.addWidget(self.btn_remove_selected)
        layout.addLayout(current_hdr)

        self.scroll_tags = QScrollArea()
        self.scroll_tags.setWidgetResizable(True)

        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.addStretch(1)

        self.scroll_tags.setWidget(self.tags_container)
        layout.addWidget(self.scroll_tags, 1)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique le style visuel Picasa 3 au volet Tags.
        EN: Applies the Picasa 3 visual style to the Tags panel.
        """
        style = style or PicasaStyle.instance()
        self.style = style
        is_dark = style.is_dark
        txt = style.alist_textcolor.name()
        sub = style.alayout_subtitleColor.name()
        accent = style.accent_color.name()
        border = style.splitter_color.name() if is_dark else style.topbar_border_color.name()
        input_bg = style.window_bgcolor.darker(115).name() if is_dark else "#FFFFFF"
        btn_border = style.topbar_btn_border.name()

        self.add_lbl.setStyleSheet(f"color: {txt}; font-size: 11px; font-weight: bold; background: transparent;")
        self.txt_tag.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {txt};
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
        """)
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #FFFFFF;
                border: 1px solid {accent};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {style.accent_color.lighter(115).name()};
            }}
        """)
        self.quick_lbl.setStyleSheet(f"color: {sub}; font-size: 11px; font-weight: bold; background: transparent;")
        self.sep.setStyleSheet(f"color: {border};")
        self.current_lbl.setStyleSheet(f"color: {txt}; font-size: 11px; font-weight: bold; background: transparent;")
        self.scroll_tags.setStyleSheet("background: transparent; border: none;")
        self.tags_container.setStyleSheet("background: transparent;")
        self._update_tags_display()

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes traduits du volet Tags selon la langue active.
        EN: Updates translated texts of the Tags panel according to the active language.
        """
        res = PicasaResourceManager.get()
        self.add_lbl.setText(res.get_xml_string("tagpanel/add_tag_label", "Entrez un tag à ajouter :"))
        self.quick_lbl.setText(res.get_xml_string("tagpanel/quick_label", "Tags rapides :"))
        self.btn_remove_selected.setText(res.get_xml_string("tagpanel/remove_button", "Supprimer le tag"))
        self._refresh_quick_tag_buttons()
        self._update_tags_display()

    def _get_effective_quick_slots(self) -> List[str]:
        """
        FR: Retourne la liste effective des 10 tags rapides en tenant compte des 2 tags récents.
        EN: Returns the effective list of 10 quick tags taking into account the 2 recent tags.
        """
        slots = (list(self.quick_slots) + [""] * 10)[:10]
        if self.reserve_recent:
            slots[0] = self.recent_tags[0] if len(self.recent_tags) >= 1 else slots[0]
            slots[1] = self.recent_tags[1] if len(self.recent_tags) >= 2 else slots[1]
        return slots

    def _refresh_quick_tag_buttons(self) -> None:
        """
        FR: Met à jour les libellés et info-bulles des 10 boutons de tags rapides.
        EN: Updates the labels and tooltips of the 10 quick tag buttons.
        """
        eff_slots = self._get_effective_quick_slots()
        for i, btn in enumerate(self.quick_buttons):
            key_num = (i + 1) % 10
            tag_text = eff_slots[i].strip() if i < len(eff_slots) else ""
            if tag_text:
                label = tag_text if len(tag_text) <= 14 else (tag_text[:13] + "…")
                btn.setText(f"{key_num}. {label}")
                btn.setToolTip(f"Ajouter le tag rapide « {tag_text} » (Alt+{key_num})")
                btn.setEnabled(True)
            else:
                btn.setText(f"{key_num}. —")
                btn.setToolTip(f"Aucun tag rapide configuré sur Alt+{key_num} (cliquer sur ⚙ pour configurer)")
                btn.setEnabled(False)

    def _trigger_quick_tag_slot(self, slot_idx: int) -> None:
        """
        FR: Déclenche l'ajout du tag rapide associé à l'emplacement `slot_idx`.
        EN: Triggers adding the quick tag associated with slot `slot_idx`.
        """
        eff_slots = self._get_effective_quick_slots()
        if 0 <= slot_idx < len(eff_slots):
            tag = eff_slots[slot_idx].strip()
            if tag:
                self._add_tag_string(tag)

    def _collect_frequent_tags(self) -> List[str]:
        """
        FR: Collecte tous les mots-clés connus de la base classés par fréquence décroissante.
        EN: Collects all known keywords from the database sorted by decreasing frequency.
        """
        cached = getattr(self, "_cached_frequent_tags", None)
        if cached is not None and getattr(self, "_cached_freq_db_id", None) == id(self.db):
            return list(cached)
        counts: Dict[str, int] = {}
        for t in self.recent_tags:
            if t:
                counts[t] = counts.get(t, 0) + 2
        if self.db is not None:
            pmp_kw = self.db.pmps.get("imagedata_keywords")
            if pmp_kw is not None:
                for raw in pmp_kw.records:
                    if not raw or not isinstance(raw, str):
                        continue
                    for kw in raw.replace(";", ",").split(","):
                        k = kw.strip()
                        if k:
                            counts[k] = counts.get(k, 0) + 1
        for d in self.DEFAULT_QUICK_SLOTS:
            counts.setdefault(d, 0)
        result = [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))]
        self._cached_frequent_tags = result
        self._cached_freq_db_id = id(self.db)
        return list(result)

    def _load_quick_tags_from_db(self) -> None:
        """
        FR: Charge la configuration des tags rapides depuis le dépôt de la base de données.
        EN: Loads the quick tag configuration from the database repository.
        """
        if self._config_loaded_from_db or self.db is None:
            return
        repo = getattr(self.db, "repository", None)
        if repo is not None:
            try:
                raw_slots = repo.get("QuickTags/slots")
                if raw_slots:
                    parsed = json.loads(str(raw_slots))
                    if isinstance(parsed, list) and len(parsed) == 10:
                        self.quick_slots = [str(x) for x in parsed]
                raw_res = repo.get("QuickTags/reserve_recent")
                if raw_res is not None:
                    self.reserve_recent = str(raw_res).strip().lower() not in ("0", "false", "no")
                raw_rec = repo.get("QuickTags/recent_tags")
                if raw_rec:
                    parsed_rec = json.loads(str(raw_rec))
                    if isinstance(parsed_rec, list):
                        self.recent_tags = [str(x) for x in parsed_rec if str(x).strip()][:2]
                self._config_loaded_from_db = True
            except Exception:
                pass
        self._refresh_quick_tag_buttons()

    def _save_quick_tags_to_db(self) -> None:
        """
        FR: Sauvegarde la configuration des tags rapides dans le dépôt de la base de données.
        EN: Saves the quick tag configuration to the database repository.
        """
        if self.db is None:
            return
        repo = getattr(self.db, "repository", None)
        if repo is not None:
            try:
                repo.set("QuickTags/slots", json.dumps(self.quick_slots, ensure_ascii=False))
                repo.set("QuickTags/reserve_recent", "1" if self.reserve_recent else "0")
                repo.set("QuickTags/recent_tags", json.dumps(self.recent_tags[:2], ensure_ascii=False))
            except Exception:
                pass

    def open_quick_tag_config_dialog(self) -> None:
        """
        FR: Ouvre le dialogue « Configuration des tags rapides » (`QuickTagConfigDlg`).
        EN: Opens the "Quick Tag Configuration" dialog (`QuickTagConfigDlg`).
        """
        freq = self._collect_frequent_tags()
        dlg = PicasaQuickTagConfigDialog(
            slots=self.quick_slots,
            reserve_recent=self.reserve_recent,
            frequent_tags=freq,
            parent=self.window(),
            style=self.style,
        )
        if dlg.exec():
            new_slots, new_res = dlg.get_config()
            self.quick_slots = new_slots
            self.reserve_recent = new_res
            self._save_quick_tags_to_db()
            self._refresh_quick_tag_buttons()

    def set_photo_path(self, photo_path: str, db: Optional[PicasaDatabase] = None) -> None:
        """
        FR: Charge et affiche les mots-clés associés à une seule photo.
        EN: Loads and displays the keywords associated with a single photo.
        """
        self.set_photo_paths([photo_path] if photo_path else [], db=db)

    def set_photo_paths(self, photo_paths: List[str], db: Optional[PicasaDatabase] = None) -> None:
        """
        FR: Charge et affiche les mots-clés associés à une ou plusieurs photos sélectionnées.
        EN: Loads and displays the keywords associated with one or more selected photos.
        """
        if db is not None:
            db_changed = (self.db is not db)
            self.db = db
            self._load_quick_tags_from_db()
            if db_changed or not getattr(self, "_completer_initialized", False):
                freq = self._collect_frequent_tags()
                if freq:
                    _setup_inline_completer(self.txt_tag, freq, style=self.style)
                    self._completer_initialized = True
        self.photo_paths = [p for p in photo_paths if p]
        self.photo_path = self.photo_paths[0] if self.photo_paths else ""
        self.current_tags = []
        self.selected_tag = None
        if not self.photo_paths:
            self._update_tags_display()
            return

        seen_tags: List[str] = []
        for p in self.photo_paths:
            if not os.path.exists(p):
                continue
            folder = os.path.dirname(p)
            filename = os.path.basename(p)
            ini_path = os.path.join(folder, ".picasa.ini")
            if os.path.exists(ini_path):
                try:
                    doc = self.db.get_parsed_ini(ini_path) if (self.db and hasattr(self.db, "get_parsed_ini")) else PicasaIniParser.parse_file(ini_path)
                    if doc:
                        for kw in doc.get_keywords(filename):
                            if kw not in seen_tags:
                                seen_tags.append(kw)
                except Exception:
                    pass
        self.current_tags = seen_tags
        self._update_tags_display()

    def _update_tags_display(self) -> None:
        """
        FR: Reconstruit la liste visuelle des étiquettes de tags associées à la sélection.
        EN: Rebuilds the visual list of tag chips associated with the selection.
        """
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if self.selected_tag not in self.current_tags:
            self.selected_tag = self.current_tags[0] if self.current_tags else None
        self.btn_remove_selected.setEnabled(bool(self.selected_tag))

        if not self.current_tags:
            sub = self.style.alayout_subtitleColor.name()
            empty_lbl = QLabel("Aucun tag pour cette photo.")
            empty_lbl.setStyleSheet(f"color: {sub}; font-size: 11px; padding: 15px 0; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_layout.insertWidget(0, empty_lbl)
            return

        for idx, tag in enumerate(self.current_tags):
            chip = self._create_tag_chip(tag)
            self.tags_layout.insertWidget(idx, chip)

    def _select_tag(self, tag: str) -> None:
        """
        FR: Sélectionne un tag dans la liste active et rafraîchit l'affichage.
        EN: Selects a tag in the active list and refreshes the display.
        """
        self.selected_tag = tag
        self._update_tags_display()

    def _on_remove_selected_tag(self) -> None:
        """
        FR: Supprime le tag actuellement sélectionné dans la liste.
        EN: Removes the currently selected tag from the list.
        """
        if self.selected_tag:
            self._remove_tag(self.selected_tag)

    def _create_tag_chip(self, tag: str) -> QWidget:
        """
        FR: Crée un widget d'étiquette (chip) avec bouton de suppression pour un mot-clé donné.
        EN: Creates a tag chip widget with a delete button for a given keyword.
        """
        chip = QFrame()
        is_sel = (tag == self.selected_tag)
        s = self.style
        is_dark = s.is_dark
        txt = s.alist_textcolor.name()
        sub = s.alayout_subtitleColor.name()
        accent = s.accent_color.name()
        if is_dark:
            border_col = accent if is_sel else s.splitter_color.name()
            bg_col = s.window_bgcolor.lighter(125).name() if is_sel else s.window_bgcolor.darker(108).name()
        else:
            border_col = accent if is_sel else s.topbar_border_color.name()
            bg_col = s.alist_bgcolor.darker(108).name() if is_sel else s.window_bgcolor.name()

        chip.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)
        chip.mousePressEvent = lambda ev, t=tag: self._select_tag(t)
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        tag_lbl = QLabel(f"🏷️  {tag}")
        tag_lbl.setStyleSheet(f"color: {txt}; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(tag_lbl, 1)

        btn_del = QPushButton("✕")
        btn_del.setToolTip(f"Supprimer le tag {tag}")
        btn_del.setFixedSize(18, 18)
        btn_del.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {sub};
                border: none;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                color: #E53935;
            }}
        """)
        btn_del.clicked.connect(lambda _, t=tag: self._remove_tag(t))
        layout.addWidget(btn_del)

        return chip

    def _on_add_tag(self) -> None:
        """
        FR: Ajoute le mot-clé saisi dans le champ de texte à la sélection.
        EN: Adds the keyword entered in the text field to the selection.
        """
        tag = self.txt_tag.text().strip()
        if tag:
            self._add_tag_string(tag)
            self.txt_tag.clear()

    def _add_tag_string(self, tag: str) -> None:
        """
        FR: Ajoute une chaîne de tag aux photos sélectionnées et met à jour les tags récents.
        EN: Adds a tag string to the selected photos and updates recent tags.
        """
        clean_tag = tag.strip()
        if not clean_tag:
            return
        if clean_tag not in self.current_tags:
            self.current_tags.append(clean_tag)
        self.selected_tag = clean_tag
        self._cached_frequent_tags = None
        self._completer_initialized = False

        # Mettre à jour la liste des 2 tags récemment utilisés (Ref: quicktagconfig/reserve_recent)
        self.recent_tags = [clean_tag] + [t for t in self.recent_tags if t.lower() != clean_tag.lower()]
        self.recent_tags = self.recent_tags[:2]
        self._save_quick_tags_to_db()
        self._refresh_quick_tag_buttons()

        self._apply_tag_change(add_tag=clean_tag)
        self._update_tags_display()
        self.tags_changed.emit(self.current_tags)

    def _remove_tag(self, tag: str) -> None:
        """
        FR: Retire un mot-clé des photos sélectionnées et met à jour l'interface.
        EN: Removes a keyword from the selected photos and updates the UI.
        """
        if tag in self.current_tags:
            self.current_tags.remove(tag)
            if self.selected_tag == tag:
                self.selected_tag = self.current_tags[0] if self.current_tags else None
            self._cached_frequent_tags = None
            self._completer_initialized = False
            self._apply_tag_change(remove_tag=tag)
            self._update_tags_display()
            self.tags_changed.emit(self.current_tags)

    def _apply_tag_change(self, add_tag: Optional[str] = None, remove_tag: Optional[str] = None) -> None:
        """
        FR: Applique l'ajout ou la suppression de tag sur toutes les photos sélectionnées dans `.picasa.ini`.
        EN: Applies tag addition or removal across all selected photos in `.picasa.ini`.
        """
        targets = self.photo_paths if self.photo_paths else ([self.photo_path] if self.photo_path else [])
        for p in targets:
            if not p or not os.path.exists(p):
                continue
            def _mod(doc: PicasaIniDocument, fname: str) -> None:
                """
                FR: Modifie la liste des mots-clés (`keywords`) de l'entrée photo dans le document INI.
                EN: Modifies the keyword list (`keywords`) of the photo entry in the INI document.
                """
                kws = list(doc.get_keywords(fname))
                if add_tag and add_tag not in kws:
                    kws.append(add_tag)
                if remove_tag and remove_tag in kws:
                    kws.remove(remove_tag)
                doc.set_keywords(fname, kws)

            if self.db is not None and hasattr(self.db, "update_photo_ini"):
                self.db.update_photo_ini(p, _mod)
            else:
                folder = os.path.dirname(p)
                filename = os.path.basename(p)
                ini_path = os.path.join(folder, ".picasa.ini")
                doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()
                _mod(doc, filename)
                try:
                    doc.write_file(ini_path)
                except Exception:
                    pass


# =============================================================================
# 4. VOLET DES PROPRIÉTÉS & EXIF / IMAGE PROPERTIES PANEL
# =============================================================================
class PicasaPropertiesPanel(QWidget):
    """
    FR: Volet d'affichage des propriétés EXIF complètes de l'image.
    EN: Panel displaying full EXIF image properties and real-time histogram.
    Ref: picasa3.exe @ imageproperties.fen, IMAGEPROPERTIES.XML
    """

    def __init__(self, parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        """
        FR: Initialise le volet Propriétés avec l'en-tête résumé, l'histogramme et le tableau EXIF.
        EN: Initializes the Properties panel with the summary header, histogram, and EXIF table.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # En-tête résumé (Filename, Location, Size, Date)
        self.header_frame = QFrame()
        h_layout = QVBoxLayout(self.header_frame)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(4)

        self.lbl_filename = QLabel("—")
        h_layout.addWidget(self.lbl_filename)

        self.lbl_path = QLabel("—")
        self.lbl_path.setWordWrap(True)
        h_layout.addWidget(self.lbl_path)

        self.lbl_size_date = QLabel("—")
        h_layout.addWidget(self.lbl_size_date)

        layout.addWidget(self.header_frame)

        # Histogramme en temps réel
        hist_box = QWidget()
        hist_vbox = QVBoxLayout(hist_box)
        hist_vbox.setContentsMargins(0, 0, 0, 0)
        hist_vbox.setSpacing(2)

        h_top = QHBoxLayout()
        self.lbl_h = QLabel("Histogramme")
        h_top.addWidget(self.lbl_h)
        h_top.addStretch(1)

        self.hist_buttons: List[QPushButton] = []
        for name, mode in [("Tous", "RGB"), ("R", "R"), ("V", "G"), ("B", "B"), ("Lum", "L")]:
            btn = QPushButton(name)
            btn.setFixedSize(26, 16)
            btn.clicked.connect(lambda _, m=mode: self.histogram_widget.set_channel_mode(m))
            h_top.addWidget(btn)
            self.hist_buttons.append(btn)
        hist_vbox.addLayout(h_top)

        self.histogram_widget = PicasaHistogramWidget(height=65, parent=self, style=self.style)
        hist_vbox.addWidget(self.histogram_widget)
        layout.addWidget(hist_box)

        # Tableau des propriétés EXIF (Ref: imageproperties/column12, column13)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Propriété", "Valeur"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique le style visuel Picasa 3 au volet Propriétés et à son tableau EXIF.
        EN: Applies the Picasa 3 visual style to the Properties panel and its EXIF table.
        """
        style = style or PicasaStyle.instance()
        self.style = style
        is_dark = style.is_dark
        txt = style.alist_textcolor.name()
        sub = style.alayout_subtitleColor.name()
        accent = style.accent_color.name()
        border = style.splitter_color.name() if is_dark else style.topbar_border_color.name()
        card_bg = style.window_bgcolor.darker(108).name() if is_dark else style.window_bgcolor.name()
        hdr_bg = style.window_bgcolor.lighter(115).name() if is_dark else style.topbar_grad_end.name()
        btn_bg = style.topbar_btn_bg_start.name()
        btn_hover = style.topbar_btn_bg_end.name()
        btn_border = style.topbar_btn_border.name()

        self.header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px;
            }}
            QLabel {{
                font-size: 11px;
                color: {txt};
                background: transparent;
                border: none;
            }}
        """)
        self.lbl_filename.setStyleSheet(
            f"color: {txt}; font-weight: bold; font-size: 12px; background: transparent; border: none;"
        )
        self.lbl_path.setStyleSheet(f"color: {sub}; font-size: 10px; background: transparent; border: none;")
        self.lbl_size_date.setStyleSheet(f"color: {txt}; font-size: 11px; background: transparent; border: none;")
        self.lbl_h.setStyleSheet(
            f"color: {sub}; font-size: 10px; font-weight: bold; background: transparent;"
        )
        for btn in self.hist_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: {txt};
                    border: 1px solid {btn_border};
                    border-radius: 2px;
                    font-size: 9px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                    border-color: {accent};
                }}
            """)
        self.histogram_widget.apply_style(style)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {card_bg};
                color: {txt};
                border: 1px solid {border};
                border-radius: 4px;
                gridline-color: {border};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {hdr_bg};
                color: {txt};
                font-weight: bold;
                border: none;
                border-bottom: 1px solid {border};
                padding: 4px 8px;
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 4px 6px;
            }}
            QTableWidget::item:selected {{
                background-color: {accent};
                color: #FFFFFF;
            }}
        """)
        # Mettre à jour les couleurs des lignes existantes du tableau
        key_col = QColor(sub)
        val_col = QColor(txt)
        for r in range(self.table.rowCount()):
            ik = self.table.item(r, 0)
            iv = self.table.item(r, 1)
            if ik is not None:
                ik.setForeground(key_col)
            if iv is not None:
                iv.setForeground(val_col)

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les en-têtes du volet Propriétés selon la langue active.
        EN: Updates headers of the Properties panel according to the active language.
        """
        res = PicasaResourceManager.get()
        col1 = res.get_xml_string("imageproperties/column12", "Propriété")
        col2 = res.get_xml_string("imageproperties/column13", "Valeur")
        self.table.setHorizontalHeaderLabels([col1, col2])

    def set_image(self, img: Optional[Image.Image]) -> None:
        """
        FR: Met à jour l'histogramme avec une image en mémoire.
        EN: Updates the histogram with an in-memory image.
        """
        self.histogram_widget.set_image(img)

    def set_photo_metadata(
        self,
        file_path: str,
        source_img: Optional[Image.Image] = None,
        db: Optional[Any] = None,
        db_index: int = -1,
    ) -> None:
        """
        FR: Extrait et affiche les métadonnées EXIF et l'histogramme de la photo spécifiée.
        EN: Extracts and displays the EXIF metadata and histogram of the specified photo.
        """
        meta = _get_cached_full_metadata(file_path)
        self.lbl_filename.setText(meta["filename"])
        self.lbl_path.setText(meta["folder"])
        self.lbl_size_date.setText(f"{meta['filesize']}  •  {meta['date']}")

        if source_img is not None:
            self.histogram_widget.set_image(source_img)
        else:
            hist_img: Optional[Image.Image] = None
            if db is not None and db_index >= 0 and hasattr(db, "get_thumbnail"):
                try:
                    raw = db.get_thumbnail(db_index, "large") or db.get_thumbnail(db_index, "small")
                    if raw:
                        with Image.open(io.BytesIO(raw)) as im_thumb:
                            hist_img = im_thumb.convert("RGB")
                except Exception:
                    hist_img = None
            if hist_img is None and file_path and os.path.exists(file_path):
                try:
                    from picasa_py.ui.image_processor import PicasaImageProcessor
                    hist_img = PicasaImageProcessor.load_transformed_image(file_path, max_size=512)
                except Exception:
                    hist_img = None
            self.histogram_widget.set_image(hist_img)

        props = meta.get("properties", [])
        self.table.setRowCount(len(props))
        key_col = QColor(self.style.alayout_subtitleColor)
        val_col = QColor(self.style.alist_textcolor)

        for row, (k, v) in enumerate(props):
            item_k = QTableWidgetItem(k)
            item_k.setFlags(item_k.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_k.setForeground(key_col)

            item_v = QTableWidgetItem(str(v))
            item_v.setFlags(item_v.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_v.setForeground(val_col)

            self.table.setItem(row, 0, item_k)
            self.table.setItem(row, 1, item_v)

    def set_multiple_photos(self, photo_paths: List[str]) -> None:
        """
        FR: Affiche un résumé des propriétés pour plusieurs photos sélectionnées.
        EN: Displays a summary of properties for multiple selected photos.
        """
        valid_paths = [p for p in photo_paths if p and os.path.exists(p)]
        self.lbl_filename.setText(f"{len(photo_paths)} élément(s) sélectionné(s)")

        total_size = sum(os.path.getsize(p) for p in valid_paths)
        if total_size >= 1024 * 1024 * 1024:
            size_str = f"{total_size / (1024*1024*1024):.2f} Go"
        elif total_size >= 1024 * 1024:
            size_str = f"{total_size / (1024*1024):.1f} Mo"
        else:
            size_str = f"{total_size / 1024:.0f} Ko"

        self.lbl_size_date.setText(f"Taille totale : {size_str}")
        self.lbl_path.setText(os.path.dirname(valid_paths[0]) if valid_paths else "")
        self.histogram_widget.set_image(None)

        self.table.setRowCount(0)
        items = [
            ("Sélection", f"{len(photo_paths)} photos"),
            ("Taille cumulée", size_str),
        ]
        if valid_paths:
            dirs = list(set(os.path.dirname(p) for p in valid_paths))
            items.append(("Dossiers", f"{len(dirs)} dossier(s)"))
        key_col = QColor(self.style.alayout_subtitleColor)
        val_col = QColor(self.style.alist_textcolor)
        for label, val in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_k = QTableWidgetItem(label)
            item_k.setFlags(item_k.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_k.setForeground(key_col)
            item_v = QTableWidgetItem(val)
            item_v.setFlags(item_v.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_v.setForeground(val_col)
            self.table.setItem(row, 0, item_k)
            self.table.setItem(row, 1, item_v)


# =============================================================================
# 5. CONTENEUR GLOBAL DU TIROIR LATÉRAL / RIGHT DRAWER CONTAINER (PicasaRightDrawer)
# =============================================================================
class PicasaRightDrawer(QWidget):
    """
    FR: Volet latéral droit de Picasa 3 avec barre d'onglets supérieure escamotable.
    Permet de basculer instantanément entre Personnes, Lieux, Tags et Propriétés.
    EN: Picasa 3 collapsible right drawer with top tab bar.
    Allows switching between People, Places, Tags, and Properties panels.
    Ref: picasa3.exe @ RIGHTDRAWERPANEL_TEXT.XML, 0x0088F9C4
    """
    drawer_closed = Signal()
    panel_changed = Signal(str)
    people_changed = Signal()
    person_filter_requested = Signal(str, str)  # contact_id, name
    cluster_filter_requested = Signal(list)  # list of photo paths in cluster

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise le tiroir latéral droit et ses 4 sous-volets (Personnes, Lieux, Tags, Propriétés).
        EN: Initializes the right drawer and its 4 subpanels (People, Places, Tags, Properties).
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.is_expanded: bool = False
        self._is_expanded: bool = False
        self._explicitly_hidden: bool = False
        self.current_panel_name: str = "properties"
        self._album_paths: List[str] = []
        self._album_scope_label: str = "l'album"
        self._dirty_panels: Set[str] = set()
        self._selection_mode: str = "single"
        self._current_photo_index: int = -1
        self._current_photo_path: str = ""
        self._current_source_img: Optional[Image.Image] = None
        self._current_multi_indices: List[int] = []
        self._current_multi_paths: List[str] = []
        self._album_context_only_dirty: bool = False

        self.setMinimumWidth(240)
        self.setMaximumWidth(1200)
        self.setObjectName("RightDrawerRoot")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Barre d'en-tête supérieure avec sélecteur d'onglets et bouton fermer
        self.top_bar_widget = self._create_top_bar()
        main_layout.addWidget(self.top_bar_widget)

        # 2. Pile des 4 volets
        self.stack = QStackedWidget()

        self.panel_people = PicasaPeoplePanel(self, style=self.style)
        self.panel_people.people_changed.connect(self.people_changed)
        self.panel_people.person_filter_requested.connect(self.person_filter_requested.emit)
        self.panel_people.cluster_filter_requested.connect(self.cluster_filter_requested.emit)
        self.panel_places = PicasaPlacesPanel(self, style=self.style)
        self.panel_places.location_changed.connect(self._on_places_location_changed)
        self.panel_places.location_cleared.connect(self._on_places_location_cleared)
        self.panel_tags = PicasaTagsPanel(self, style=self.style)
        self.panel_properties = PicasaPropertiesPanel(self, style=self.style)
        self._active_db: Optional[PicasaDatabase] = None
        self._active_paths: List[str] = []

        self.stack.addWidget(self.panel_people)      # Index 0
        self.stack.addWidget(self.panel_places)      # Index 1
        self.stack.addWidget(self.panel_tags)        # Index 2
        self.stack.addWidget(self.panel_properties)  # Index 3

        main_layout.addWidget(self.stack, 1)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs au tiroir latéral droit et à ses sous-volets.
        EN: Dynamically applies the color theme to the right drawer and its subpanels.
        """
        style = style or PicasaStyle.instance()
        self.style = style
        bg = style.drawer_bgcolor.name()
        hs = style.drawer_header_start.name()
        he = style.drawer_header_end.name()
        txt_col = style.tray_text_color.name()
        sub_txt = "#A0AEC0" if style.is_dark else style.alayout_subtitleColor.name()
        border_col = "#141517" if style.is_dark else style.topbar_border_color.name()
        card_bg = style.tray_grad_end.name() if style.is_dark else style.window_bgcolor.name()
        input_bg = "#1E2024" if style.is_dark else "#FFFFFF"
        btn_start = style.tray_grad_start.name() if style.is_dark else style.topbar_btn_bg_start.name()
        btn_end = style.tray_grad_end.name() if style.is_dark else style.topbar_btn_bg_end.name()
        btn_border = "#484D56" if style.is_dark else style.topbar_btn_border.name()
        accent = style.accent_color.name()
        sb_bg = "#1B1D21" if style.is_dark else style.alist_catcolor.name()
        sb_handle = (
            style.topbar_btn_border.lighter(130).name()
            if style.is_dark
            else style.topbar_btn_border.darker(115).name()
        )
        sb_hover = style.alist_selcolor_win.name()

        self.setStyleSheet(f"""
            QWidget#RightDrawerRoot {{
                background-color: {bg};
                border-left: 1px solid {border_col};
            }}
            QWidget#RightDrawerRoot QWidget {{
                background-color: {bg};
                color: {txt_col};
            }}
            QWidget#RightDrawerRoot QLabel {{
                background-color: transparent;
                color: {txt_col};
            }}
            QWidget#RightDrawerRoot QLineEdit {{
                background-color: {input_bg};
                color: {txt_col};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 3px 6px;
            }}
            QWidget#RightDrawerRoot QListWidget,
            QWidget#RightDrawerRoot QTableWidget,
            QWidget#RightDrawerRoot QScrollArea {{
                background-color: {card_bg};
                color: {txt_col};
                border: 1px solid {border_col};
                border-radius: 3px;
            }}
            QWidget#RightDrawerRoot QHeaderView::section {{
                background-color: {he};
                color: {txt_col};
                border: 1px solid {border_col};
                padding: 3px;
            }}
            QWidget#RightDrawerRoot QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_start}, stop:1 {btn_end});
                color: {txt_col};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 3px 6px;
            }}
            QWidget#RightDrawerRoot QPushButton:hover {{
                border-color: {accent};
            }}
            QWidget#RightDrawerRoot QPushButton:checked {{
                background-color: {accent};
                color: #FFFFFF;
                border-color: {accent};
            }}
            QWidget#RightDrawerRoot QScrollBar:vertical {{
                background: {sb_bg};
                width: 10px;
                margin: 0px;
                border-left: 1px solid {border_col};
            }}
            QWidget#RightDrawerRoot QScrollBar::handle:vertical {{
                background: {sb_handle};
                min-height: 24px;
                border-radius: 4px;
                margin: 1px;
            }}
            QWidget#RightDrawerRoot QScrollBar::handle:vertical:hover,
            QWidget#RightDrawerRoot QScrollBar::handle:vertical:pressed {{
                background: {sb_hover};
            }}
            QWidget#RightDrawerRoot QScrollBar::add-line:vertical,
            QWidget#RightDrawerRoot QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QWidget#RightDrawerRoot QScrollBar::add-page:vertical,
            QWidget#RightDrawerRoot QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QWidget#RightDrawerRoot QScrollBar:horizontal {{
                background: {sb_bg};
                height: 10px;
                margin: 0px;
                border-top: 1px solid {border_col};
            }}
            QWidget#RightDrawerRoot QScrollBar::handle:horizontal {{
                background: {sb_handle};
                min-width: 24px;
                border-radius: 4px;
                margin: 1px;
            }}
            QWidget#RightDrawerRoot QScrollBar::handle:horizontal:hover,
            QWidget#RightDrawerRoot QScrollBar::handle:horizontal:pressed {{
                background: {sb_hover};
            }}
            QWidget#RightDrawerRoot QScrollBar::add-line:horizontal,
            QWidget#RightDrawerRoot QScrollBar::sub-line:horizontal {{
                width: 0px;
                background: none;
            }}
            QWidget#RightDrawerRoot QScrollBar::add-page:horizontal,
            QWidget#RightDrawerRoot QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """)
        if hasattr(self, "top_bar_widget") and self.top_bar_widget is not None:
            self.top_bar_widget.setStyleSheet(f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {hs}, stop:1 {he});
                    border-bottom: 1px solid {border_col};
                }}
            """)
        if hasattr(self, "lbl_title") and self.lbl_title is not None:
            self.lbl_title.setStyleSheet(
                f"color: {txt_col}; font-weight: bold; font-size: 12px; background: transparent; border: none;"
            )
        if hasattr(self, "btn_size_toggle") and self.btn_size_toggle is not None:
            self.btn_size_toggle.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {sub_txt}; font-weight: bold; font-size: 10px; }}"
                f"QPushButton:hover {{ color: {txt_col}; }}"
            )
        if hasattr(self, "btn_close") and self.btn_close is not None:
            self.btn_close.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {sub_txt}; font-weight: bold; font-size: 12px; }}"
                f"QPushButton:hover {{ color: #E53E3E; }}"
            )
        if hasattr(self, "panel_people"):
            self.panel_people.apply_style(style)
        if hasattr(self, "panel_places"):
            self.panel_places.apply_style(style)
        if hasattr(self, "panel_tags"):
            self.panel_tags.apply_style(style)
        if hasattr(self, "panel_properties"):
            self.panel_properties.apply_style(style)
        self.update()

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les titres et libellés du tiroir latéral droit et de ses 4 volets selon la langue active.
        EN: Updates titles and labels of the right drawer and its 4 subpanels according to the active language.
        """
        res = PicasaResourceManager.get()
        titles = {
            "people": res.get_xml_string("rightdrawerpanel/tab1", "Personnes"),
            "places": res.get_xml_string("rightdrawerpanel/tab2", "Lieux"),
            "tags": res.get_xml_string("rightdrawerpanel/tab3", "Tags"),
            "properties": res.get_xml_string("rightdrawerpanel/tab4", "Propriétés"),
        }
        self.lbl_title.setText(titles.get(self.current_panel_name, titles["properties"]))
        if hasattr(self.panel_people, "retranslate_ui"):
            self.panel_people.retranslate_ui()
        if hasattr(self.panel_places, "retranslate_ui"):
            self.panel_places.retranslate_ui()
        if hasattr(self.panel_tags, "retranslate_ui"):
            self.panel_tags.retranslate_ui()
        if hasattr(self.panel_properties, "retranslate_ui"):
            self.panel_properties.retranslate_ui()

    def _create_top_bar(self) -> QWidget:
        """
        FR: Crée l'en-tête supérieur du tiroir latéral droit fidèle à `rightdrawerpanel.tre` :
        - Gauche (X=8..22, Y=10..24) : `rightdrawerpanel/size_toggle` (◀◀ / ▶▶)
        - Centre (X=29..247, Y=5..24) : `rightdrawerpanel/title_text` (centré, `Property textalign center`)
        - Droite (X=255..269, Y=10..24) : `rightdrawerpanel/close` (✕)
        (Les 4 boutons de sélection de volet se trouvent en bas dans `thumbui/metadata_group`).

        EN: Creates the top header of the right drawer faithful to `rightdrawerpanel.tre`:
        - Left (X=8..22, Y=10..24): `rightdrawerpanel/size_toggle` (◀◀ / ▶▶)
        - Center (X=29..247, Y=5..24): `rightdrawerpanel/title_text` (centered, `Property textalign center`)
        - Right (X=255..269, Y=10..24): `rightdrawerpanel/close` (✕)
        (The 4 panel selection buttons are located at the bottom in `thumbui/metadata_group`).

        Ref: respack.yt @ rightdrawerpanel.tre (size_toggle, title_text, close, header)
        """
        bar = QWidget()
        bar.setFixedHeight(31)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(6)

        # 1. Gauche : rightdrawerpanel/size_toggle (rect=(8, 10, 22, 24))
        self.btn_size_toggle = QPushButton("◀◀")
        self.btn_size_toggle.setToolTip("Basculer entre l'affichage étroit (276px) ou large (520px) du panneau latéral")
        self.btn_size_toggle.setFixedSize(24, 20)
        self.btn_size_toggle.clicked.connect(self.toggle_size)
        layout.addWidget(self.btn_size_toggle)

        # 2. Centre : rightdrawerpanel/title_text (rect=(29, 5, 247, 24), Property textalign center)
        self.lbl_title = QLabel("Propriétés")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_title, 1)

        # 3. Droite : rightdrawerpanel/close (rect=(255, 10, 269, 24))
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Fermer ce panneau latéral")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.clicked.connect(self.hide_drawer)
        layout.addWidget(self.btn_close)

        # Attributs conservés (icônes sans texte, comme #tab1..#tab4 dans rightdrawerpanel.tre / thumbui/*_toggle @ 0x005D96D4..0x005D9E54)
        rm = PicasaResourceManager.get()
        self.btn_people = QPushButton("", bar)
        self.btn_people.setIcon(rm.get_drawer_toggle_icon("people", 18))
        self.btn_people.setToolTip(rm.get_xml_string("thumbui/people_toggle.tooltip", "Afficher/masquer le panneau Personnes"))
        self.btn_people.setCheckable(True)
        self.btn_people.hide()
        self.btn_places = QPushButton("", bar)
        self.btn_places.setIcon(rm.get_drawer_toggle_icon("places", 18))
        self.btn_places.setToolTip(rm.get_xml_string("thumbui/places_toggle.tooltip", "Afficher/Masquer le panneau Lieux"))
        self.btn_places.setCheckable(True)
        self.btn_places.hide()
        self.btn_tags = QPushButton("", bar)
        self.btn_tags.setIcon(rm.get_drawer_toggle_icon("tags", 18))
        self.btn_tags.setToolTip(rm.get_xml_string("thumbui/tags_toggle.tooltip", "Afficher/Masquer le panneau Tags"))
        self.btn_tags.setCheckable(True)
        self.btn_tags.hide()
        self.btn_props = QPushButton("", bar)
        self.btn_props.setIcon(rm.get_drawer_toggle_icon("properties", 18))
        self.btn_props.setToolTip(rm.get_xml_string("thumbui/properties_toggle.tooltip", "Afficher/Masquer le panneau Propriétés"))
        self.btn_props.setCheckable(True)
        self.btn_props.setChecked(True)
        self.btn_props.hide()

        self.tab_group = QButtonGroup(bar)
        self.tab_group.addButton(self.btn_people, 0)
        self.tab_group.addButton(self.btn_places, 1)
        self.tab_group.addButton(self.btn_tags, 2)
        self.tab_group.addButton(self.btn_props, 3)
        self.tab_group.idClicked.connect(self._on_tab_clicked)

        return bar

    def _ensure_splitter_width(self, target_w: int) -> None:
        """
        FR: Ajuste les tailles du `QSplitter` parent pour garantir la largeur cible du tiroir.
        EN: Adjusts the parent `QSplitter` sizes to ensure the target drawer width.
        """
        from PySide6.QtWidgets import QSplitter
        parent = self.parentWidget()
        if isinstance(parent, QSplitter):
            idx = parent.indexOf(self)
            sizes = parent.sizes()
            if 0 <= idx < len(sizes):
                total = sum(sizes)
                if total <= 0:
                    total = max(1000, parent.width())
                    if len(sizes) == 3:
                        sizes = [220, max(200, total - 220 - target_w), target_w]
                        parent.setSizes(sizes)
                        return
                diff = target_w - sizes[idx]
                adj_idx = idx - 1 if idx > 0 else (idx + 1 if idx + 1 < len(sizes) else -1)
                if 0 <= adj_idx < len(sizes):
                    sizes[adj_idx] = max(120, sizes[adj_idx] - diff)
                    sizes[idx] = target_w
                    parent.setSizes(sizes)
                    return

    def toggle_size(self) -> None:
        """
        FR: Bascule entre la largeur standard (~280px) et large (~520px) du panneau latéral.
        EN: Toggles between standard (~280px) and wide (~520px) side panel width.
        Ref: picasa3.exe @ rightdrawerpanel/size_toggle
        """
        self._is_expanded = not self._is_expanded if self.width() <= 0 else (self.width() <= 360)
        target_w = 520 if self._is_expanded else 280
        self.btn_size_toggle.setText("▶▶" if target_w > 360 else "◀◀")
        self._ensure_splitter_width(target_w)
        self.resize(target_w, self.height())

    def _on_tab_clicked(self, tab_id: int) -> None:
        """
        FR: Active l'onglet correspondant à `tab_id`, synchronise ses données si nécessaire et met à jour le titre.
        EN: Activates the tab corresponding to `tab_id`, syncs its data if needed, and updates the title.
        """
        self.stack.setCurrentIndex(tab_id)
        names = {0: "people", 1: "places", 2: "tags", 3: "properties"}
        res = PicasaResourceManager.get()
        titles = {
            0: res.get_xml_string("rightdrawerpanel/tab1", "Personnes"),
            1: res.get_xml_string("rightdrawerpanel/tab2", "Lieux"),
            2: res.get_xml_string("rightdrawerpanel/tab3", "Tags"),
            3: res.get_xml_string("rightdrawerpanel/tab4", "Propriétés"),
        }
        self.current_panel_name = names.get(tab_id, "properties")
        self.lbl_title.setText(titles.get(tab_id, titles[3]))
        if not self._explicitly_hidden:
            self._sync_active_panel()
        self.panel_changed.emit(self.current_panel_name)

    def show_panel(self, panel_name: str) -> None:
        """
        FR: Affiche le panneau spécifié ("people", "places", "tags", "properties")
        et ouvre le tiroir s'il était fermé en lui allouant sa largeur dans le QSplitter parent.
        EN: Displays the specified panel ("people", "places", "tags", "properties")
        and opens the drawer if closed by allocating its width in the parent QSplitter.
        """
        mapping = {"people": 0, "places": 1, "tags": 2, "properties": 3}
        tab_id = mapping.get(panel_name.lower(), 3)
        self.current_panel_name = panel_name.lower()
        btn = self.tab_group.button(tab_id)
        if btn:
            btn.setChecked(True)
        self.is_expanded = True
        self.show()
        self._on_tab_clicked(tab_id)

        from PySide6.QtWidgets import QSplitter
        parent = self.parentWidget()
        if isinstance(parent, QSplitter):
            idx = parent.indexOf(self)
            sizes = parent.sizes()
            if 0 <= idx < len(sizes) and sizes[idx] < 180:
                self._ensure_splitter_width(280)

    def toggle_panel(self, panel_name: str) -> None:
        """
        FR: Bascule l'affichage du panneau (comportement d'origine Picasa 3) :
        - Si le volet est fermé : l'ouvre sur ce panneau.
        - Si le volet est ouvert sur ce même panneau : le ferme.
        - Si le volet est ouvert sur un autre panneau : bascule sur le nouveau panneau.
        EN: Toggles panel display (original Picasa 3 behavior):
        - If the drawer is closed: opens it on this panel.
        - If the drawer is open on this same panel: closes it.
        - If the drawer is open on another panel: switches to the new panel.
        """
        is_currently_open = self.isVisible() or (not self._explicitly_hidden and self.is_expanded)
        if is_currently_open and self.current_panel_name == panel_name.lower():
            self.hide_drawer()
        else:
            self.show_panel(panel_name)

    def hide_drawer(self) -> None:
        """
        FR: Masque le tiroir latéral droit et restitue son espace au panneau central dans le `QSplitter`.
        EN: Hides the right drawer and returns its space to the central panel in the `QSplitter`.
        """
        from PySide6.QtWidgets import QSplitter
        parent = self.parentWidget()
        if isinstance(parent, QSplitter):
            idx = parent.indexOf(self)
            sizes = parent.sizes()
            if 0 <= idx < len(sizes) and sizes[idx] > 0:
                adj_idx = idx - 1 if idx > 0 else (idx + 1 if idx + 1 < len(sizes) else -1)
                if 0 <= adj_idx < len(sizes):
                    sizes[adj_idx] += sizes[idx]
                sizes[idx] = 0
                parent.setSizes(sizes)
        self.hide()
        self.is_expanded = False
        self.drawer_closed.emit()

    @staticmethod
    def _extract_photo_geotag(
        db: Optional[PicasaDatabase],
        photo_path: str,
        check_exif: bool = True,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        FR: Extrait les coordonnées GPS d'une photo à partir de `.picasa.ini` (`geotag=lat,lon`)
        ou des métadonnées EXIF GPS.
        EN: Extracts GPS coordinates of a photo from `.picasa.ini` (`geotag=lat,lon`)
        or from EXIF GPS metadata.
        """
        if not photo_path or not os.path.exists(photo_path):
            return None, None

        # 1. Priorité au tag geotag= de .picasa.ini (rapide et reflète les modifications Picasa)
        ini_p = os.path.join(os.path.dirname(photo_path), ".picasa.ini")
        if os.path.exists(ini_p):
            try:
                doc = (
                    db.get_parsed_ini(ini_p)
                    if (db and hasattr(db, "get_parsed_ini"))
                    else PicasaIniParser.parse_file(ini_p)
                )
                if doc:
                    sec = doc.get_section(os.path.basename(photo_path))
                    if sec and sec.get("geotag"):
                        parts = [x.strip() for x in sec.get("geotag", "").split(",")]
                        if len(parts) >= 2:
                            return float(parts[0]), float(parts[1])
            except Exception:
                pass

        # 2. Métadonnées EXIF GPS
        if check_exif:
            try:
                meta = _get_cached_full_metadata(photo_path)
                if meta.get("gps"):
                    lat, lon, _ = meta["gps"]
                    return float(lat), float(lon)
            except Exception:
                pass

        return None, None

    def _collect_album_markers(
        self,
        db: Optional[PicasaDatabase],
        candidate_paths: List[str],
    ) -> List[Dict[str, Any]]:
        """
        FR: Collecte l'ensemble des marqueurs GPS de l'album ou du dossier courant.
        EN: Collects all GPS markers from the current album or folder.
        Ref: picasa3.exe @ 0x008A9A00 (GeoPanel::geo_info_format)
        """
        markers: List[Dict[str, Any]] = []
        seen_paths = set()

        for p in candidate_paths[:250]:
            if not p or p in seen_paths:
                continue
            seen_paths.add(p)
            lat, lon = self._extract_photo_geotag(db, p, check_exif=False)
            if lat is not None and lon is not None:
                markers.append({
                    "lat": lat,
                    "lon": lon,
                    "filename": os.path.basename(p),
                    "path": p,
                })
        return markers

    def _get_sibling_album_paths(self, photo_path: str) -> List[str]:
        """
        FR: Récupère les photos du même dossier/album pour calculer le nombre d'emplacements dans l'album.
        EN: Retrieves photos from the same folder/album to compute the number of locations in the album.
        """
        if self._album_paths and photo_path in self._album_paths:
            return self._album_paths
        if not photo_path or not os.path.exists(photo_path):
            return []
        folder = os.path.dirname(photo_path)
        cached_folder = getattr(self, "_cached_sibling_folder", None)
        if cached_folder == folder and getattr(self, "_cached_sibling_paths", None):
            return self._cached_sibling_paths
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
        try:
            paths = [
                os.path.join(folder, fn)
                for fn in sorted(os.listdir(folder))
                if os.path.splitext(fn)[1].lower() in exts
            ]
            self._cached_sibling_folder = folder
            self._cached_sibling_paths = paths
            return paths
        except Exception:
            return [photo_path]

    def _sync_active_panel(self) -> None:
        """
        FR: Rafraîchit uniquement le sous-volet actuellement affiché s'il est marqué comme modifié (`_dirty_panels`).
            Évite toute lecture disque, décodage EXIF/image ou rendu `QWebEngineView` lorsque le tiroir est fermé
            ou sur les 3 onglets masqués.
        EN: Refreshes only the currently active subpanel if it is marked dirty (`_dirty_panels`).
            Avoids any disk I/O, EXIF/image decoding, or `QWebEngineView` rendering when the drawer is closed
            or on the 3 hidden tabs.
        """
        panel = self.current_panel_name
        if panel not in self._dirty_panels:
            return
        self._dirty_panels.discard(panel)
        db = self._active_db

        if self._selection_mode == "multiple":
            indices = self._current_multi_indices
            paths = self._current_multi_paths
            scope_label = self._album_scope_label
            if panel == "people":
                self.panel_people.set_multiple_photos(db, indices, paths)
            elif panel == "properties":
                self.panel_properties.set_multiple_photos(paths)
            elif panel == "tags":
                self.panel_tags.set_photo_paths(paths, db=db)
            elif panel == "places":
                album_markers = self._collect_album_markers(db, paths)
                self._cached_album_markers = album_markers
                active_lat: Optional[float] = None
                active_lon: Optional[float] = None
                active_title = f"{len(paths)} photo(s)"
                if len(album_markers) == 1:
                    active_lat = float(album_markers[0]["lat"])
                    active_lon = float(album_markers[0]["lon"])
                    active_title = str(album_markers[0].get("filename", active_title))
                self.panel_places.update_map(
                    active_lat,
                    active_lon,
                    active_title,
                    album_markers=album_markers,
                    scope_label=scope_label,
                )
        else:
            photo_index = self._current_photo_index
            photo_path = self._current_photo_path
            source_img = self._current_source_img
            if panel == "people":
                faces: List[FaceRect] = []
                if db and getattr(db, "face_manager", None):
                    faces = db.face_manager.get_faces_for_photo(photo_index, photo_path=photo_path)
                self.panel_people.set_photo_faces(db, photo_index, photo_path, faces, source_img=source_img)
            elif panel == "properties":
                self.panel_properties.set_photo_metadata(photo_path, source_img=source_img, db=db, db_index=photo_index)
            elif panel == "tags":
                self.panel_tags.set_photo_path(photo_path, db=db)
            elif panel == "places":
                if self._album_context_only_dirty and not photo_path:
                    markers = self._collect_album_markers(db, self._album_paths)
                    self._cached_album_markers = markers
                    self.panel_places.set_album_context(markers, scope_label=self._album_scope_label)
                else:
                    lat, lon = self._extract_photo_geotag(db, photo_path, check_exif=True)
                    folder_key = os.path.dirname(photo_path) if photo_path else ""
                    if (
                        getattr(self, "_cached_marker_folder", None) == folder_key
                        and getattr(self, "_cached_album_markers", None) is not None
                    ):
                        album_markers = self._cached_album_markers
                    else:
                        sibling_paths = self._get_sibling_album_paths(photo_path)
                        album_markers = self._collect_album_markers(db, sibling_paths)
                        self._cached_marker_folder = folder_key
                        self._cached_album_markers = album_markers
                    self.panel_places.update_map(
                        lat,
                        lon,
                        os.path.basename(photo_path) if photo_path else "",
                        album_markers=album_markers,
                        scope_label=self._album_scope_label,
                    )
                self._album_context_only_dirty = False

    def hide(self) -> None:
        """
        FR: Masque le tiroir latéral droit et marque son état comme explicitement masqué.
        EN: Hides the right drawer and marks its state as explicitly hidden.
        """
        self._explicitly_hidden = True
        super().hide()

    def show(self) -> None:
        """
        FR: Affiche le tiroir latéral droit et synchronise le volet actif.
        EN: Shows the right drawer and synchronizes the active panel.
        """
        self._explicitly_hidden = False
        super().show()
        self._sync_active_panel()

    def set_album_paths(
        self,
        db: Optional[PicasaDatabase],
        photo_paths: List[str],
        scope_label: str = "l'album",
    ) -> None:
        """
        FR: Définit les photos de l'album/dossier courant pour le calcul du compteur de lieux.
        EN: Sets the current album/folder photos for computing the place counter.
        """
        self._active_db = db
        self._album_paths = list(photo_paths)
        self._album_scope_label = scope_label
        self._cached_marker_folder = None
        self._cached_album_markers = None
        self._album_context_only_dirty = True
        self._dirty_panels.add("places")
        if not self._explicitly_hidden and self.current_panel_name == "places":
            self._sync_active_panel()

    def set_current_photo(
        self,
        db: Optional[PicasaDatabase],
        photo_index: int,
        photo_path: str,
        source_img: Optional[Image.Image] = None,
    ) -> None:
        """
        FR: Enregistre la photo active et met à jour le volet ouvert (les volets masqués sont rafraîchis à la demande).
        EN: Stores the active photo and updates the open panel (hidden panels are refreshed on demand).
        """
        self._active_db = db
        self._active_paths = [photo_path] if photo_path else []
        self._selection_mode = "single"
        self._current_photo_index = photo_index
        self._current_photo_path = photo_path
        self._current_source_img = source_img
        self._album_context_only_dirty = False
        self._dirty_panels = {"people", "places", "tags", "properties"}
        if not self._explicitly_hidden:
            self._sync_active_panel()

    def set_multiple_photos(
        self,
        db: Optional[PicasaDatabase],
        photo_indices: List[int],
        photo_paths: List[str],
        scope_label: str = "l'album",
    ) -> None:
        """
        FR: Enregistre la sélection multiple et met à jour le volet ouvert (les volets masqués sont rafraîchis à la demande).
        EN: Stores the multiple selection and updates the open panel (hidden panels are refreshed on demand).
        Ref: picasa3.exe @ 0x00CA1264 ("People in these photos:"), 0x008A9A00 (GeoPanel::geo_info_format)
        """
        self._active_db = db
        self._active_paths = list(photo_paths)
        self._album_paths = list(photo_paths)
        self._album_scope_label = scope_label
        self._selection_mode = "multiple"
        self._current_multi_indices = list(photo_indices)
        self._current_multi_paths = list(photo_paths)
        self._album_context_only_dirty = False
        self._dirty_panels = {"people", "places", "tags", "properties"}
        if not self._explicitly_hidden:
            self._sync_active_panel()
            if self.parentWidget() is None and "people" in self._dirty_panels:
                self._dirty_panels.discard("people")
                self.panel_people.set_multiple_photos(db, self._current_multi_indices, self._current_multi_paths)

    def _on_places_location_changed(self, lat: float, lon: float) -> None:
        """
        FR: Persiste les coordonnées GPS (`geotag=lat,lon`) dans `.picasa.ini` pour les photos sélectionnées
        et met à jour le compteur de lieux dans l'album.
        EN: Persists GPS coordinates (`geotag=lat,lon`) into `.picasa.ini` for selected photos
        and updates the album place counter.
        Ref: picasa3.exe @ GEOPANELTEXT_FR.XML, geotag=
        """
        for p in self._active_paths:
            if not p or not os.path.exists(p):
                continue
            def _set_geo(doc: PicasaIniDocument, fname: str) -> None:
                """
                FR: Enregistre l'attribut `geotag` pour la photo dans la section INI correspondante.
                EN: Sets the `geotag` attribute for the photo in the corresponding INI section.
                """
                sec = doc.get_or_create_section(fname)
                sec.set("geotag", f"{lat:.6f},{lon:.6f}")

            if self._active_db is not None and hasattr(self._active_db, "update_photo_ini"):
                self._active_db.update_photo_ini(p, _set_geo)
            else:
                ini_p = os.path.join(os.path.dirname(p), ".picasa.ini")
                doc = PicasaIniParser.parse_file(ini_p) if os.path.exists(ini_p) else PicasaIniDocument()
                _set_geo(doc, os.path.basename(p))
                try:
                    doc.write_file(ini_p)
                except Exception:
                    pass

        # Rafraîchir les marqueurs de l'album après modification
        self._cached_marker_folder = None
        self._cached_album_markers = None
        ref_path = self._active_paths[0] if self._active_paths else ""
        sibling_paths = self._get_sibling_album_paths(ref_path) if ref_path else self._album_paths
        if sibling_paths:
            self.panel_places.album_markers = self._collect_album_markers(self._active_db, sibling_paths)
            self.panel_places._update_geo_info_header()

    def _on_places_location_cleared(self) -> None:
        """
        FR: Supprime l'entrée `geotag` dans `.picasa.ini` pour les photos sélectionnées.
        EN: Removes the `geotag` entry in `.picasa.ini` for the selected photos.
        Ref: picasa3.exe @ geopanel/cleargeotag (GeotagPanel::clearbutton)
        """
        for p in self._active_paths:
            if not p or not os.path.exists(p):
                continue
            def _clear_geo(doc: PicasaIniDocument, fname: str) -> None:
                """
                FR: Supprime la clé `geotag` de la section INI associée à la photo.
                EN: Removes the `geotag` key from the INI section associated with the photo.
                """
                sec = doc.get_section(fname)
                if sec:
                    sec.remove("geotag")

            if self._active_db is not None and hasattr(self._active_db, "update_photo_ini"):
                self._active_db.update_photo_ini(p, _clear_geo)
            else:
                ini_p = os.path.join(os.path.dirname(p), ".picasa.ini")
                if os.path.exists(ini_p):
                    try:
                        doc = PicasaIniParser.parse_file(ini_p)
                        _clear_geo(doc, os.path.basename(p))
                        doc.write_file(ini_p)
                    except Exception:
                        pass

        self._cached_marker_folder = None
        self._cached_album_markers = None
        ref_path = self._active_paths[0] if self._active_paths else ""
        sibling_paths = self._get_sibling_album_paths(ref_path) if ref_path else self._album_paths
        self.panel_places.album_markers = self._collect_album_markers(self._active_db, sibling_paths)
        self.panel_places._update_geo_info_header()
        self.panel_places._render_leaflet_html()

