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
from PySide6.QtGui import QColor, QFont, QPixmap

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


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

        # 3. Curseur de zoom de vignettes
        lbl_small = QLabel("−")
        lbl_small.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(lbl_small)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(64, 256)
        self.zoom_slider.setValue(140)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self.zoom_changed.emit)
        main_layout.addWidget(self.zoom_slider)

        lbl_large = QLabel("+")
        lbl_large.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(lbl_large)

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
