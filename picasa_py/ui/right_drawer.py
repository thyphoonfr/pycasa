"""
Right Drawer Component for PyCasa (Tiroir latéral droit escamotable).
Contient les 4 volets caractéristiques de Picasa 3 :
1. Personnes (People Panel, détection de visages, identification et ajout manuel)
2. Lieux (Places Panel avec carte interactive Leaflet / OpenStreetMap)
3. Tags (Tag Panel, mots-clés, tags rapides et persistance .picasa.ini)
4. Propriétés (Image Properties / Données EXIF complètes)

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
    QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QThread
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush, QPen
from PySide6.QtWebEngineWidgets import QWebEngineView
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.exif_reader import extract_full_metadata, format_gps_dms
from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument


# =============================================================================
# 1. VOLET DES PERSONNES (People Panel)
# =============================================================================
class PicasaPeoplePanel(QWidget):
    """
    Volet d'identification des visages et personnes sur la photo sélectionnée.
    Ref: picasa3.exe @ PEOPLEPANEL_TEXT_FR.XML, 0x008AAD76
    """
    face_hovered = Signal(int)
    face_clicked = Signal(int)
    manual_add_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db: Optional[PicasaDatabase] = None
        self.photo_index: int = -1
        self.photo_path: str = ""
        self.faces: List[FaceRect] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # En-tête du volet
        header_lbl = QLabel("Personnes sur cette photo")
        header_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #FFFFFF;")
        layout.addWidget(header_lbl)

        # Zone défilante des visages
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #1C1E22;
            }
            QScrollBar::handle:vertical {
                background: #444852;
                border-radius: 4px;
            }
        """)

        self.faces_container = QWidget()
        self.faces_layout = QVBoxLayout(self.faces_container)
        self.faces_layout.setContentsMargins(0, 0, 0, 0)
        self.faces_layout.setSpacing(8)
        self.faces_layout.addStretch(1)

        self.scroll.setWidget(self.faces_container)
        layout.addWidget(self.scroll, 1)

        # Bouton d'ajout manuel (Ref: peoplepanel/manual_add)
        self.btn_manual_add = QPushButton("➕  Ajouter une personne manuellement")
        self.btn_manual_add.setStyleSheet("""
            QPushButton {
                background-color: #32363E;
                color: #DDDDDD;
                border: 1px solid #484E59;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3E434D;
                color: #FFFFFF;
            }
        """)
        self.btn_manual_add.clicked.connect(self.manual_add_requested.emit)
        layout.addWidget(self.btn_manual_add)

    def set_photo_faces(
        self,
        db: Optional[PicasaDatabase],
        photo_index: int,
        photo_path: str,
        faces: List[FaceRect]
    ) -> None:
        self.db = db
        self.photo_index = photo_index
        self.photo_path = photo_path
        self.faces = faces

        # Vider la liste précédente
        while self.faces_layout.count() > 1:
            item = self.faces_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not faces:
            empty_lbl = QLabel("Aucun visage détecté sur cette photo.")
            empty_lbl.setStyleSheet("color: #888888; font-size: 11px; padding: 20px 0;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.faces_layout.insertWidget(0, empty_lbl)
            return

        # Charger l'image source pour découper les avatars
        source_img: Optional[Image.Image] = None
        if photo_path and os.path.exists(photo_path):
            try:
                source_img = Image.open(photo_path)
            except Exception:
                pass

        for i, fr in enumerate(faces):
            card = self._create_face_card(i, fr, source_img)
            self.faces_layout.insertWidget(i, card)

    def _create_face_card(self, idx: int, fr: FaceRect, source_img: Optional[Image.Image]) -> QWidget:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #282C34;
                border: 1px solid #3A3F4B;
                border-radius: 6px;
                padding: 6px;
            }
            QFrame:hover {
                background-color: #30353F;
                border-color: #25648B;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # Avatar circulaire
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(48, 48)
        if source_img:
            try:
                pix = fr.crop_avatar(source_img, avatar_size=48, circular=True)
                avatar_lbl.setPixmap(pix)
            except Exception:
                avatar_lbl.setText("👤")
        else:
            avatar_lbl.setText("👤")
        layout.addWidget(avatar_lbl)

        # Nom de la personne
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name = fr.contact_name or "Sans nom"
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 12px;")
        info_layout.addWidget(name_lbl)

        action_lbl = QLabel("Ajouter un nom" if not fr.contact_name else "Modifier")
        action_lbl.setStyleSheet("color: #4AA3DF; font-size: 11px; text-decoration: underline;")
        action_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        info_layout.addWidget(action_lbl)

        layout.addLayout(info_layout, 1)

        # Bouton Ignorer / Supprimer (Ref: peoplepanel/ignore)
        btn_ignore = QPushButton("✕")
        btn_ignore.setToolTip("Ignorer ce visage")
        btn_ignore.setFixedSize(22, 22)
        btn_ignore.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FF5555;
            }
        """)
        layout.addWidget(btn_ignore)

        return card


# =============================================================================
# 2. VOLET DES LIEUX (Places Panel - Carte Interactive Leaflet)
# =============================================================================
class GeocodeWorker(QThread):
    result_ready = Signal(float, float, str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(self.query)}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "PyCasa/3.9"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    display_name = data[0].get("display_name", self.query)
                    self.result_ready.emit(lat, lon, display_name)
        except Exception:
            pass


class PicasaPlacesPanel(QWidget):
    """
    Volet cartographique interactif basé sur Leaflet et OpenStreetMap.
    Remplace l'affichage original Google Map selon l'instruction du projet.
    Ref: picasa3.exe @ GEOPANELTEXT_FR.XML, thumbui/places_toggle
    """
    location_changed = Signal(float, float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_lat: Optional[float] = None
        self.current_lon: Optional[float] = None
        self.current_filename: str = ""
        self.geocode_worker: Optional[GeocodeWorker] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Barre de recherche d'adresse (Ref: geopanel/search_label)
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Rechercher une adresse...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #1E2024;
                color: #FFFFFF;
                border: 1px solid #3A3E47;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #25648B;
            }
        """)
        self.txt_search.returnPressed.connect(self._on_search_address)
        search_layout.addWidget(self.txt_search, 1)

        self.btn_search = QPushButton("🔍")
        self.btn_search.setToolTip("Rechercher l'adresse")
        self.btn_search.setFixedSize(28, 26)
        self.btn_search.setStyleSheet("""
            QPushButton {
                background-color: #32363E;
                color: #FFFFFF;
                border: 1px solid #484E59;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #404550;
            }
        """)
        self.btn_search.clicked.connect(self._on_search_address)
        search_layout.addWidget(self.btn_search)

        layout.addLayout(search_layout)

        # 2. Vue cartographique Leaflet (QWebEngineView)
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background-color: #E5E3DF; border-radius: 4px;")
        layout.addWidget(self.web_view, 1)

        # 3. Informations de coordonnées GPS
        self.lbl_coords = QLabel("Aucune coordonnée GPS")
        self.lbl_coords.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        self.lbl_coords.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_coords)

        # Initialiser avec une vue par défaut
        self.update_map(None, None, "Photo")

    def update_map(self, lat: Optional[float], lon: Optional[float], filename: str = "") -> None:
        self.current_lat = lat
        self.current_lon = lon
        self.current_filename = filename

        if lat is not None and lon is not None:
            self.lbl_coords.setText(format_gps_dms(lat, lon))
            zoom = 15
            has_marker = True
            m_lat, m_lon = lat, lon
        else:
            self.lbl_coords.setText("Cette photo n'a pas de géolocalisation.")
            zoom = 4
            has_marker = False
            m_lat, m_lon = 46.603354, 1.888334  # Centre de la France

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
    var map = L.map('map', {{ zoomControl: true }}).setView([{m_lat}, {m_lon}], {zoom});
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    }}).addTo(map);

    var marker = null;
    {f"marker = L.marker([{m_lat}, {m_lon}]).addTo(map).bindPopup('<b>{filename}</b><br>{m_lat:.4f}, {m_lon:.4f}').openPopup();" if has_marker else ""}

    map.on('click', function(e) {{
      if (marker) {{
        marker.setLatLng(e.latlng);
      }} else {{
        marker = L.marker(e.latlng).addTo(map);
      }}
      marker.bindPopup('<b>Emplacement défini</b><br>' + e.latlng.lat.toFixed(4) + ', ' + e.latlng.lng.toFixed(4)).openPopup();
    }});
  </script>
</body>
</html>"""
        self.web_view.setHtml(html)

    def _on_search_address(self) -> None:
        query = self.txt_search.text().strip()
        if not query:
            return
        self.geocode_worker = GeocodeWorker(query)
        self.geocode_worker.result_ready.connect(self._on_geocode_success)
        self.geocode_worker.start()

    def _on_geocode_success(self, lat: float, lon: float, display_name: str) -> None:
        self.update_map(lat, lon, self.current_filename or display_name)
        self.location_changed.emit(lat, lon)


# =============================================================================
# 3. VOLET DES TAGS (Tag Panel - Mots-clés & Tags rapides)
# =============================================================================
class PicasaTagsPanel(QWidget):
    """
    Volet de gestion des mots-clés (tags) de la photo sélectionnée.
    Sauvegarde directement dans le fichier .picasa.ini du dossier sous [photo.jpg] keywords=...
    Ref: picasa3.exe @ TAGPANEL_TEXT_FR.XML, KEYWORDSTEXT_FR.XML
    """
    tags_changed = Signal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.photo_path: str = ""
        self.current_tags: List[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Champ d'ajout de tag (Ref: tagpanel/add_tag_label, keywords/addkeywords_label)
        add_lbl = QLabel("Entrez un tag à ajouter :")
        add_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold;")
        layout.addWidget(add_lbl)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)

        self.txt_tag = QLineEdit()
        self.txt_tag.setPlaceholderText("Nouveau tag...")
        self.txt_tag.setStyleSheet("""
            QLineEdit {
                background-color: #1E2024;
                color: #FFFFFF;
                border: 1px solid #3A3E47;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #25648B;
            }
        """)
        self.txt_tag.returnPressed.connect(self._on_add_tag)
        input_layout.addWidget(self.txt_tag, 1)

        self.btn_add = QPushButton("Ajouter")
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #25648B;
                color: #FFFFFF;
                border: 1px solid #3D85B3;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2F78A6;
            }
        """)
        self.btn_add.clicked.connect(self._on_add_tag)
        input_layout.addWidget(self.btn_add)

        layout.addLayout(input_layout)

        # 2. Tags rapides (Ref: tagpanel/quick_label)
        quick_lbl = QLabel("Tags rapides :")
        quick_lbl.setStyleSheet("color: #AAAAAA; font-size: 11px; margin-top: 4px;")
        layout.addWidget(quick_lbl)

        quick_tags_layout = QHBoxLayout()
        quick_tags_layout.setSpacing(4)
        for qtag in ("Vacances", "Famille", "Voyage", "Nature", "Favoris"):
            btn_q = QPushButton(qtag)
            btn_q.setStyleSheet("""
                QPushButton {
                    background-color: #2E323A;
                    color: #CCCCCC;
                    border: 1px solid #434854;
                    border-radius: 10px;
                    padding: 2px 8px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #3B414B;
                    color: #FFFFFF;
                }
            """)
            btn_q.clicked.connect(lambda _, t=qtag: self._add_tag_string(t))
            quick_tags_layout.addWidget(btn_q)

        layout.addLayout(quick_tags_layout)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #353840;")
        layout.addWidget(sep)

        # 3. Liste des tags actuels
        current_lbl = QLabel("Tags associés :")
        current_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold;")
        layout.addWidget(current_lbl)

        self.scroll_tags = QScrollArea()
        self.scroll_tags.setWidgetResizable(True)
        self.scroll_tags.setStyleSheet("background: transparent; border: none;")

        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.addStretch(1)

        self.scroll_tags.setWidget(self.tags_container)
        layout.addWidget(self.scroll_tags, 1)

    def set_photo_path(self, photo_path: str) -> None:
        self.photo_path = photo_path
        self.current_tags = []
        if not photo_path or not os.path.exists(photo_path):
            self._update_tags_display()
            return

        # Lire les tags depuis le fichier .picasa.ini du répertoire
        folder = os.path.dirname(photo_path)
        filename = os.path.basename(photo_path)
        ini_path = os.path.join(folder, ".picasa.ini")
        if os.path.exists(ini_path):
            try:
                with open(ini_path, "rb") as f:
                    doc = PicasaIniParser.parse_bytes(f.read())
                    self.current_tags = doc.get_keywords(filename)
            except Exception:
                pass

        self._update_tags_display()

    def _update_tags_display(self) -> None:
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.current_tags:
            empty_lbl = QLabel("Aucun tag pour cette photo.")
            empty_lbl.setStyleSheet("color: #888888; font-size: 11px; padding: 15px 0;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_layout.insertWidget(0, empty_lbl)
            return

        for idx, tag in enumerate(self.current_tags):
            chip = self._create_tag_chip(tag)
            self.tags_layout.insertWidget(idx, chip)

    def _create_tag_chip(self, tag: str) -> QWidget:
        chip = QFrame()
        chip.setStyleSheet("""
            QFrame {
                background-color: #252830;
                border: 1px solid #383D48;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        tag_lbl = QLabel(f"🏷️  {tag}")
        tag_lbl.setStyleSheet("color: #FFFFFF; font-size: 11px;")
        layout.addWidget(tag_lbl, 1)

        btn_del = QPushButton("✕")
        btn_del.setToolTip(f"Supprimer le tag {tag}")
        btn_del.setFixedSize(18, 18)
        btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888888;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #FF5555;
            }
        """)
        btn_del.clicked.connect(lambda _, t=tag: self._remove_tag(t))
        layout.addWidget(btn_del)

        return chip

    def _on_add_tag(self) -> None:
        tag = self.txt_tag.text().strip()
        if tag:
            self._add_tag_string(tag)
            self.txt_tag.clear()

    def _add_tag_string(self, tag: str) -> None:
        clean_tag = tag.strip()
        if not clean_tag or clean_tag in self.current_tags:
            return
        self.current_tags.append(clean_tag)
        self._save_tags()
        self._update_tags_display()
        self.tags_changed.emit(self.current_tags)

    def _remove_tag(self, tag: str) -> None:
        if tag in self.current_tags:
            self.current_tags.remove(tag)
            self._save_tags()
            self._update_tags_display()
            self.tags_changed.emit(self.current_tags)

    def _save_tags(self) -> None:
        """Sauvegarde les tags dans le fichier .picasa.ini du dossier parent."""
        if not self.photo_path:
            return
        folder = os.path.dirname(self.photo_path)
        filename = os.path.basename(self.photo_path)
        ini_path = os.path.join(folder, ".picasa.ini")

        doc = PicasaIniDocument()
        if os.path.exists(ini_path):
            try:
                with open(ini_path, "rb") as f:
                    doc = PicasaIniParser.parse_bytes(f.read())
            except Exception:
                pass

        doc.set_keywords(filename, self.current_tags)
        try:
            doc.write_file(ini_path)
        except Exception:
            pass


# =============================================================================
# 4. VOLET DES PROPRIÉTÉS & EXIF (Image Properties)
# =============================================================================
class PicasaPropertiesPanel(QWidget):
    """
    Volet d'affichage des propriétés EXIF complètes de l'image.
    Ref: picasa3.exe @ imageproperties.fen, IMAGEPROPERTIES.XML
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # En-tête résumé (Filename, Location, Size, Date)
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #24272E;
                border: 1px solid #373B46;
                border-radius: 6px;
                padding: 8px;
            }
            QLabel {
                font-size: 11px;
                color: #CCCCCC;
            }
        """)
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(4)

        self.lbl_filename = QLabel("—")
        self.lbl_filename.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 12px;")
        h_layout.addWidget(self.lbl_filename)

        self.lbl_path = QLabel("—")
        self.lbl_path.setStyleSheet("color: #8A92A0; font-size: 10px;")
        self.lbl_path.setWordWrap(True)
        h_layout.addWidget(self.lbl_path)

        self.lbl_size_date = QLabel("—")
        h_layout.addWidget(self.lbl_size_date)

        layout.addWidget(header_frame)

        # Tableau des propriétés EXIF (Ref: imageproperties/column12, column13)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Propriété", "Valeur"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1E2024;
                color: #DDDDDD;
                border: 1px solid #32353D;
                border-radius: 4px;
                gridline-color: #2A2D35;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #2A2D35;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                padding: 4px 8px;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 4px 6px;
            }
            QTableWidget::item:selected {
                background-color: #25648B;
            }
        """)
        layout.addWidget(self.table, 1)

    def set_photo_metadata(self, file_path: str) -> None:
        meta = extract_full_metadata(file_path)
        self.lbl_filename.setText(meta["filename"])
        self.lbl_path.setText(meta["folder"])
        self.lbl_size_date.setText(f"{meta['filesize']}  •  {meta['date']}")

        props = meta.get("properties", [])
        self.table.setRowCount(len(props))

        for row, (k, v) in enumerate(props):
            item_k = QTableWidgetItem(k)
            item_k.setFlags(item_k.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_k.setForeground(QColor("#A0A8B4"))

            item_v = QTableWidgetItem(str(v))
            item_v.setFlags(item_v.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_v.setForeground(QColor("#FFFFFF"))

            self.table.setItem(row, 0, item_k)
            self.table.setItem(row, 1, item_v)


# =============================================================================
# 5. CONTENEUR GLOBAL DU TIROIR LATÉRAL (PicasaRightDrawer)
# =============================================================================
class PicasaRightDrawer(QWidget):
    """
    Volet latéral droit de Picasa 3 avec barre d'onglets supérieure escamotable.
    Permet de basculer instantanément entre Personnes, Lieux, Tags et Propriétés.
    Ref: picasa3.exe @ RIGHTDRAWERPANEL_TEXT.XML, 0x0088F9C4
    """
    drawer_closed = Signal()
    panel_changed = Signal(str)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.is_expanded: bool = False
        self.current_panel_name: str = "properties"

        self.setFixedWidth(300)
        self.setStyleSheet("""
            QWidget#RightDrawerRoot {
                background-color: #202226;
                border-left: 1px solid #141517;
            }
        """)
        self.setObjectName("RightDrawerRoot")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Barre d'en-tête supérieure avec sélecteur d'onglets et bouton fermer
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        # 2. Pile des 4 volets
        self.stack = QStackedWidget()

        self.panel_people = PicasaPeoplePanel(self)
        self.panel_places = PicasaPlacesPanel(self)
        self.panel_tags = PicasaTagsPanel(self)
        self.panel_properties = PicasaPropertiesPanel(self)

        self.stack.addWidget(self.panel_people)      # Index 0
        self.stack.addWidget(self.panel_places)      # Index 1
        self.stack.addWidget(self.panel_tags)        # Index 2
        self.stack.addWidget(self.panel_properties)  # Index 3

        main_layout.addWidget(self.stack, 1)

    def _create_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet("""
            QWidget {
                background-color: #282A2E;
                border-bottom: 1px solid #18191B;
            }
            QPushButton {
                background-color: #34373E;
                color: #CCCCCC;
                border: 1px solid #434750;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #42464F;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: #25648B;
                border-color: #3D85B3;
                color: #FFFFFF;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Boutons d'onglets segmentés
        self.btn_people = QPushButton("👤")
        self.btn_people.setToolTip("Personnes (Visages)")
        self.btn_people.setCheckable(True)

        self.btn_places = QPushButton("📍")
        self.btn_places.setToolTip("Lieux (Carte Leaflet)")
        self.btn_places.setCheckable(True)

        self.btn_tags = QPushButton("🏷️")
        self.btn_tags.setToolTip("Tags (Mots-clés)")
        self.btn_tags.setCheckable(True)

        self.btn_props = QPushButton("ℹ️")
        self.btn_props.setToolTip("Propriétés (Données EXIF)")
        self.btn_props.setCheckable(True)
        self.btn_props.setChecked(True)

        self.tab_group = QButtonGroup(bar)
        self.tab_group.addButton(self.btn_people, 0)
        self.tab_group.addButton(self.btn_places, 1)
        self.tab_group.addButton(self.btn_tags, 2)
        self.tab_group.addButton(self.btn_props, 3)
        self.tab_group.idClicked.connect(self._on_tab_clicked)

        layout.addWidget(self.btn_people)
        layout.addWidget(self.btn_places)
        layout.addWidget(self.btn_tags)
        layout.addWidget(self.btn_props)

        # Titre du panneau actif
        self.lbl_title = QLabel("Propriétés")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #FFFFFF; margin-left: 6px;")
        layout.addWidget(self.lbl_title, 1)

        # Bouton Fermer (Ref: rightdrawerpanel/close)
        btn_close = QPushButton("✕")
        btn_close.setToolTip("Fermer ce panneau latéral")
        btn_close.setFixedSize(22, 22)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #888888;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: #44474E;
            }
        """)
        btn_close.clicked.connect(self.hide_drawer)
        layout.addWidget(btn_close)

        return bar

    def _on_tab_clicked(self, tab_id: int) -> None:
        self.stack.setCurrentIndex(tab_id)
        names = {0: "people", 1: "places", 2: "tags", 3: "properties"}
        titles = {0: "Personnes", 1: "Lieux", 2: "Tags", 3: "Propriétés"}
        self.current_panel_name = names.get(tab_id, "properties")
        self.lbl_title.setText(titles.get(tab_id, "Propriétés"))
        self.panel_changed.emit(self.current_panel_name)

    def show_panel(self, panel_name: str) -> None:
        """
        Affiche le panneau spécifié ("people", "places", "tags", "properties")
        et ouvre le tiroir s'il était fermé.
        """
        mapping = {"people": 0, "places": 1, "tags": 2, "properties": 3}
        tab_id = mapping.get(panel_name.lower(), 3)
        btn = self.tab_group.button(tab_id)
        if btn:
            btn.setChecked(True)
        self._on_tab_clicked(tab_id)
        self.show()
        self.is_expanded = True

    def toggle_panel(self, panel_name: str) -> None:
        """
        Bascule l'affichage du panneau (comportement d'origine Picasa 3) :
        - Si le volet est fermé : l'ouvre sur ce panneau.
        - Si le volet est ouvert sur ce même panneau : le ferme.
        - Si le volet est ouvert sur un autre panneau : bascule sur le nouveau panneau.
        """
        if self.isVisible() and self.current_panel_name == panel_name.lower():
            self.hide_drawer()
        else:
            self.show_panel(panel_name)

    def hide_drawer(self) -> None:
        self.hide()
        self.is_expanded = False
        self.drawer_closed.emit()

    def set_current_photo(
        self,
        db: Optional[PicasaDatabase],
        photo_index: int,
        photo_path: str
    ) -> None:
        """
        Met à jour simultanément l'ensemble des 4 volets avec les données de la photo.
        """
        # 1. Volet des personnes
        faces: List[FaceRect] = []
        if db and photo_index >= 0:
            faces = db.face_manager.get_faces_for_photo(photo_index)
        self.panel_people.set_photo_faces(db, photo_index, photo_path, faces)

        # 2. Volet des propriétés EXIF
        self.panel_properties.set_photo_metadata(photo_path)

        # 3. Volet des lieux (Leaflet)
        meta = extract_full_metadata(photo_path)
        lat, lon = None, None
        if meta.get("gps"):
            lat, lon, _ = meta["gps"]
        self.panel_places.update_map(lat, lon, os.path.basename(photo_path))

        # 4. Volet des tags
        self.panel_tags.set_photo_path(photo_path)
