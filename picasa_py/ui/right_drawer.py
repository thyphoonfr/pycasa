"""
Right Drawer Component for PyCasa (Metadata, EXIF, Tags, and Faces).

Ref: picasa3.exe @ RIGHTDRAWERPANEL_TEXT.XML, IMAGEPROPERTIES.XML
Ref: runtime/imageproperties.fen
"""

from __future__ import annotations
from typing import Dict, Optional, Any
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QFormLayout, QLineEdit, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from picasa_py.ui.style import PicasaStyle


class PicasaRightDrawer(QWidget):
    """
    Volet latéral droit escamotable (Propriétés/EXIF, Balises/Tags, Visages).
    """
    drawer_toggled = Signal(bool)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.is_expanded: bool = False

        self.setFixedWidth(260)
        self.setStyleSheet("""
            QWidget#DrawerRoot {{
                background-color: #F6F6F6;
                border-left: 1px solid #CCCCCC;
            }}
            QLabel#DrawerHeader {{
                font-weight: bold;
                font-size: 13px;
                color: #333333;
                padding-bottom: 6px;
                border-bottom: 1px solid #E0E0E0;
            }}
            QLabel {{
                font-size: 11px;
                color: #555555;
            }}
        """)
        self.setObjectName("DrawerRoot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # En-tête
        self.lbl_title = QLabel("Propriétés de l'image")
        self.lbl_title.setObjectName("DrawerHeader")
        layout.addWidget(self.lbl_title)

        # Formulaire des propriétés EXIF
        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form_layout.setContentsMargins(0, 8, 0, 0)
        self.form_layout.setSpacing(6)

        self.lbl_filename = QLabel("—")
        self.lbl_date = QLabel("—")
        self.lbl_size = QLabel("—")
        self.lbl_res = QLabel("—")
        self.lbl_camera = QLabel("—")

        self.form_layout.addRow("Fichier :", self.lbl_filename)
        self.form_layout.addRow("Date :", self.lbl_date)
        self.form_layout.addRow("Taille :", self.lbl_size)
        self.form_layout.addRow("Résolution :", self.lbl_res)
        self.form_layout.addRow("Appareil :", self.lbl_camera)

        layout.addLayout(self.form_layout)
        layout.addStretch(1)

    def display_item_info(self, info: Optional[Dict[str, Any]]) -> None:
        if not info:
            self.lbl_filename.setText("—")
            self.lbl_date.setText("—")
            self.lbl_size.setText("—")
            self.lbl_res.setText("—")
            self.lbl_camera.setText("—")
            return

        self.lbl_filename.setText(str(info.get("filename", "—")))
        self.lbl_date.setText(str(info.get("date", "—")))
        self.lbl_size.setText(str(info.get("size", "—")))
        self.lbl_res.setText(str(info.get("resolution", "—")))
        self.lbl_camera.setText(str(info.get("camera", "—")))
