"""
Edit Panel component for PyCasa One-Up View (Left editing sidebar).
Contains the 5 tabs of Picasa 3 editing tools and filters.

Ref: picasa3.exe @ editoneup, filterdesc.xml
Ref: runtime/constants.ui [Picasa2]
"""

from __future__ import annotations
from typing import Dict, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QSlider, QFrame, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaEditPanel(QWidget):
    """
    Volet latéral gauche d'édition de photo (Onglets Retouches, Éclairage, Effets).
    """
    back_to_library = Signal()
    apply_effect = Signal(str, dict)  # (effect_name, params)
    undo_action = Signal()
    redo_action = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.setFixedWidth(280)
        self.setStyleSheet("""
            QWidget#EditPanelRoot {
                background-color: #EDEAE4;
                border-right: 1px solid #C0BCB4;
            }
            QPushButton#BackBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                border: 1px solid #2859A3;
                text-align: left;
            }
            QPushButton#BackBtn:hover {
                background-color: #4A8BF0;
            }
            QPushButton#ToolBtn {
                background-color: #F8F7F4;
                border: 1px solid #C5C0B6;
                border-radius: 4px;
                padding: 8px 6px;
                font-size: 11px;
                font-weight: bold;
                color: #333333;
                text-align: center;
            }
            QPushButton#ToolBtn:hover {
                background-color: #FFFFFF;
                border-color: #3879D9;
            }
            QPushButton#ToolBtn:pressed {
                background-color: #E2DFD6;
            }
            QTabWidget::pane {
                border: 1px solid #C0BCB4;
                background-color: #F4F2ED;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #DDD9D0;
                border: 1px solid #C0BCB4;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: bold;
                color: #555555;
            }
            QTabBar::tab:selected {
                background-color: #F4F2ED;
                border-bottom-color: #F4F2ED;
                color: #222222;
            }
            QLabel {
                font-size: 11px;
                color: #444444;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #B5B0A4;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #25648B;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
        """)
        self.setObjectName("EditPanelRoot")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Bouton "Revenir à la bibliothèque"
        self.btn_back = QPushButton("◀ Revenir à la bibliothèque")
        self.btn_back.setObjectName("BackBtn")
        self.btn_back.setToolTip("Quitter l'éditeur et revenir à la vue grille (Échap)")
        self.btn_back.clicked.connect(self.back_to_library.emit)
        main_layout.addWidget(self.btn_back)

        # 2. Boutons Annuler / Rétablir
        undo_box = QHBoxLayout()
        self.btn_undo = QPushButton("↶ Annuler")
        self.btn_undo.setObjectName("ToolBtn")
        self.btn_undo.clicked.connect(self.undo_action.emit)
        undo_box.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↷ Rétablir")
        self.btn_redo.setObjectName("ToolBtn")
        self.btn_redo.clicked.connect(self.redo_action.emit)
        undo_box.addWidget(self.btn_redo)
        main_layout.addLayout(undo_box)

        # 3. Onglets de retouche
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_basic_fixes_tab(), "Retouches")
        self.tabs.addTab(self._create_tuning_tab(), "Lumière")
        self.tabs.addTab(self._create_effects_tab(), "Effets")
        main_layout.addWidget(self.tabs, 1)

    def _create_basic_fixes_tab(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(6, 10, 6, 10)
        grid.setSpacing(6)

        tools = [
            ("Recadrer", "crop"),
            ("Redresser", "straighten"),
            ("Yeux rouges", "redeye"),
            ("J'ai de la chance", "lucky"),
            ("Contraste auto", "autocontrast"),
            ("Couleur auto", "autocolor"),
            ("Retoucher", "retouch"),
            ("Texte", "text"),
        ]

        for i, (label, action_id) in enumerate(tools):
            btn = QPushButton(label)
            btn.setObjectName("ToolBtn")
            btn.clicked.connect(lambda _, a=action_id: self.apply_effect.emit(a, {}))
            grid.addWidget(btn, i // 2, i % 2)

        return w

    def _create_tuning_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Lumière d'appoint
        layout.addWidget(QLabel("Lumière d'appoint (Fill Light) :"))
        self.sldr_fill = QSlider(Qt.Orientation.Horizontal)
        self.sldr_fill.setRange(0, 100)
        self.sldr_fill.setValue(0)
        self.sldr_fill.sliderReleased.connect(
            lambda: self.apply_effect.emit("fill_light", {"amount": self.sldr_fill.value() / 100.0})
        )
        layout.addWidget(self.sldr_fill)

        # Hautes lumières
        layout.addWidget(QLabel("Hautes lumières :"))
        self.sldr_highlights = QSlider(Qt.Orientation.Horizontal)
        self.sldr_highlights.setRange(0, 100)
        self.sldr_highlights.setValue(0)
        layout.addWidget(self.sldr_highlights)

        # Ombres
        layout.addWidget(QLabel("Ombres :"))
        self.sldr_shadows = QSlider(Qt.Orientation.Horizontal)
        self.sldr_shadows.setRange(0, 100)
        self.sldr_shadows.setValue(0)
        layout.addWidget(self.sldr_shadows)

        # Température de couleur
        layout.addWidget(QLabel("Température de couleur :"))
        self.sldr_temp = QSlider(Qt.Orientation.Horizontal)
        self.sldr_temp.setRange(-50, 50)
        self.sldr_temp.setValue(0)
        layout.addWidget(self.sldr_temp)

        layout.addStretch(1)
        return w

    def _create_effects_tab(self) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(6, 10, 6, 10)
        grid.setSpacing(6)

        effects = [
            ("Netteté", "sharpen"),
            ("Sépia", "sepia"),
            ("Noir et blanc", "bw"),
            ("Réchauffer", "warmify"),
            ("Grain photo", "grain"),
            ("Saturation", "saturation"),
        ]

        for i, (label, action_id) in enumerate(effects):
            btn = QPushButton(label)
            btn.setObjectName("ToolBtn")
            btn.clicked.connect(lambda _, a=action_id: self.apply_effect.emit(a, {}))
            grid.addWidget(btn, i // 2, i % 2)

        return w
