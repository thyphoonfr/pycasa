"""
Photo Tray Component for PyCasa (Bottom Action Tray).
Holds current selections and provides actions (Hold, Clear, Export, Print, Email, Zoom).

Ref: picasa3.exe @ 0x0088C3EC (Tray operations, Hold/Clear, Export)
Ref: runtime/constants.ui [Picasa2]
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPixmap, QPainter, QPen, QBrush, QPaintEvent
from PySide6.QtCore import QRect

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaZoomIcon(QWidget):
    """
    Icône de zoom de vignette (petite grille 2x2 ou grande vignette unique).
    Ref: picasa3.exe @ zoomslider (0x0088E914)
    """

    def __init__(self, is_large: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_large = is_large
        self.setFixedSize(18, 18)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor("#8A92A0")
        painter.setPen(QPen(color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if not self.is_large:
            # Petite grille de 4 carrés (2x2)
            for row in range(2):
                for col in range(2):
                    r = QRect(2 + col * 7, 2 + row * 7, 6, 6)
                    painter.drawRect(r)
        else:
            # Grande vignette unique
            r = QRect(2, 2, 13, 13)
            painter.drawRect(r)


class PicasaPhotoTray(QWidget):
    """
    Barre inférieure caractéristique de Picasa (« Picture Tray »).
    """
    zoom_changed = Signal(int)
    action_export = Signal()
    action_print = Signal()
    action_email = Signal()
    action_hold = Signal()
    action_clear = Signal()
    panel_toggled = Signal(str)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            QWidget#TrayRoot {{
                background-color: {self.style.tray_bgcolor.name()};
                border-top: 1px solid #1E2024;
            }}
            QPushButton {{
                background-color: #3E434B;
                color: #FFFFFF;
                border: 1px solid #555B66;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4C525C;
            }}
            QPushButton:pressed {{
                background-color: #2D3137;
            }}
            QPushButton#PrimaryBtn {{
                background-color: #25648B;
                border: 1px solid #3D85B3;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: #2F78A6;
            }}
            QLabel {{
                color: #DDDDDD;
                font-size: 11px;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: #555B66;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #CCCCCC;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }}
        """)
        self.setObjectName("TrayRoot")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 6)
        main_layout.setSpacing(10)

        # 1. Boutons Hold & Clear
        self.btn_hold = QPushButton("Hold")
        self.btn_hold.setToolTip("Conserver la sélection en cours")
        self.btn_hold.clicked.connect(self.action_hold.emit)
        main_layout.addWidget(self.btn_hold)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setToolTip("Effacer la sélection du bac")
        self.btn_clear.clicked.connect(self.action_clear.emit)
        main_layout.addWidget(self.btn_clear)

        # Séparateur vertical
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #44474E;")
        main_layout.addWidget(sep1)

        # 2. Indicateur de sélection
        self.lbl_selection = QLabel("Aucune photo sélectionnée")
        self.lbl_selection.setMinimumWidth(160)
        main_layout.addWidget(self.lbl_selection)

        main_layout.addStretch(1)

        # 3. Curseur de zoom de vignettes (zoomslider / scaleslider)
        self.icon_small = PicasaZoomIcon(is_large=False)
        main_layout.addWidget(self.icon_small)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(64, 256)
        self.zoom_slider.setValue(140)
        self.zoom_slider.setFixedWidth(110)
        self.zoom_slider.valueChanged.connect(self.zoom_changed.emit)
        main_layout.addWidget(self.zoom_slider)

        self.icon_large = PicasaZoomIcon(is_large=True)
        main_layout.addWidget(self.icon_large)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #44474E;")
        main_layout.addWidget(sep2)

        # 4. Boutons d'action rapides (Upload, Email, Print, Export)
        self.btn_upload = QPushButton("Upload")
        self.btn_upload.setObjectName("PrimaryBtn")
        main_layout.addWidget(self.btn_upload)

        self.btn_email = QPushButton("Email")
        self.btn_email.clicked.connect(self.action_email.emit)
        main_layout.addWidget(self.btn_email)

        self.btn_print = QPushButton("Print")
        self.btn_print.clicked.connect(self.action_print.emit)
        main_layout.addWidget(self.btn_print)

        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.action_export.emit)
        main_layout.addWidget(self.btn_export)

        # 5. Boutons de bascule du panneau latéral droit (Ref: thumbui/*_toggle)
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color: #44474E;")
        main_layout.addWidget(sep3)

        self.btn_panel_people = QPushButton("👤 Personnes")
        self.btn_panel_people.setCheckable(True)
        self.btn_panel_people.setToolTip("Afficher/masquer le panneau des personnes")
        self.btn_panel_people.clicked.connect(lambda: self.panel_toggled.emit("people"))
        main_layout.addWidget(self.btn_panel_people)

        self.btn_panel_places = QPushButton("📍 Lieux")
        self.btn_panel_places.setCheckable(True)
        self.btn_panel_places.setToolTip("Afficher/masquer le panneau des lieux (Carte Leaflet)")
        self.btn_panel_places.clicked.connect(lambda: self.panel_toggled.emit("places"))
        main_layout.addWidget(self.btn_panel_places)

        self.btn_panel_tags = QPushButton("🏷️ Tags")
        self.btn_panel_tags.setCheckable(True)
        self.btn_panel_tags.setToolTip("Afficher/masquer le panneau des tags")
        self.btn_panel_tags.clicked.connect(lambda: self.panel_toggled.emit("tags"))
        main_layout.addWidget(self.btn_panel_tags)

        self.btn_panel_props = QPushButton("ℹ️ Propriétés")
        self.btn_panel_props.setCheckable(True)
        self.btn_panel_props.setToolTip("Afficher/masquer le panneau des propriétés (Données EXIF)")
        self.btn_panel_props.clicked.connect(lambda: self.panel_toggled.emit("properties"))
        main_layout.addWidget(self.btn_panel_props)

    def update_panel_buttons(self, is_open: bool, current_panel: str) -> None:
        self.btn_panel_people.setChecked(is_open and current_panel == "people")
        self.btn_panel_places.setChecked(is_open and current_panel == "places")
        self.btn_panel_tags.setChecked(is_open and current_panel == "tags")
        self.btn_panel_props.setChecked(is_open and current_panel == "properties")

    def set_selected_count(self, count: int) -> None:
        if count == 0:
            self.lbl_selection.setText("Aucune photo sélectionnée")
            self.btn_export.setEnabled(False)
            self.btn_print.setEnabled(False)
            self.btn_email.setEnabled(False)
        elif count == 1:
            self.lbl_selection.setText("1 photo sélectionnée")
            self.btn_export.setEnabled(True)
            self.btn_print.setEnabled(True)
            self.btn_email.setEnabled(True)
        else:
            self.lbl_selection.setText(f"{count} photos sélectionnées")
            self.btn_export.setEnabled(True)
            self.btn_print.setEnabled(True)
            self.btn_email.setEnabled(True)
