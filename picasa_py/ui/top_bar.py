"""
Top Action Bar Component for PyCasa.
Contains Import button, Search input, Filter buttons, and View switches.

Ref: picasa3.exe @ HEADERPANELTEXT.XML
Ref: picasa3.exe @ 0x0088C3EC (Search & Filters)
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLineEdit, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaTopBar(QWidget):
    """
    Barre d'outils supérieure (Importation, Recherche, Filtres rapides).
    """
    import_requested = Signal()
    search_query_changed = Signal(str)
    filter_starred_toggled = Signal(bool)
    filter_faces_toggled = Signal(bool)
    filter_videos_toggled = Signal(bool)
    slideshow_requested = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            QWidget#TopBarRoot {{
                background-color: #EAEAEA;
                border-bottom: 1px solid #C0C0C0;
            }}
            QPushButton#ImportBtn {{
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 12px;
                border: 1px solid #2859A3;
            }}
            QPushButton#ImportBtn:hover {{
                background-color: #4A8BF0;
            }}
            QPushButton#ImportBtn:pressed {{
                background-color: #215096;
            }}
            QPushButton#FilterBtn {{
                background-color: #F8F8F8;
                border: 1px solid #BBBBBB;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton#FilterBtn:checked {{
                background-color: #D0E4F5;
                border-color: #3879D9;
            }}
            QLineEdit#SearchEdit {{
                background-color: #FFFFFF;
                border: 1px solid #AAAAAA;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 12px;
            }}
        """)
        self.setObjectName("TopBarRoot")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # 1. Bouton Import
        self.btn_import = QPushButton("Import")
        self.btn_import.setObjectName("ImportBtn")
        self.btn_import.setToolTip("Importer des photos depuis un appareil photo ou un dossier")
        self.btn_import.clicked.connect(self.import_requested.emit)
        layout.addWidget(self.btn_import)

        layout.addSpacing(10)

        # 2. Bouton Diaporama (Slideshow)
        self.btn_slideshow = QPushButton("▶ Diaporama")
        self.btn_slideshow.setObjectName("FilterBtn")
        self.btn_slideshow.setToolTip("Lancer le diaporama plein écran (Ctrl+4)")
        self.btn_slideshow.clicked.connect(self.slideshow_requested.emit)
        layout.addWidget(self.btn_slideshow)

        layout.addStretch(1)

        # 3. Boutons filtres rapides (Starred, People, Video)
        self.btn_star = QPushButton("★")
        self.btn_star.setObjectName("FilterBtn")
        self.btn_star.setCheckable(True)
        self.btn_star.setToolTip("Afficher uniquement les photos marquées d'une étoile")
        self.btn_star.toggled.connect(self.filter_starred_toggled.emit)
        layout.addWidget(self.btn_star)

        self.btn_faces = QPushButton("👤")
        self.btn_faces.setObjectName("FilterBtn")
        self.btn_faces.setCheckable(True)
        self.btn_faces.setToolTip("Afficher uniquement les photos contenant des visages")
        self.btn_faces.toggled.connect(self.filter_faces_toggled.emit)
        layout.addWidget(self.btn_faces)

        self.btn_movies = QPushButton("🎬")
        self.btn_movies.setObjectName("FilterBtn")
        self.btn_movies.setCheckable(True)
        self.btn_movies.setToolTip("Afficher uniquement les vidéos")
        self.btn_movies.toggled.connect(self.filter_videos_toggled.emit)
        layout.addWidget(self.btn_movies)

        # 4. Champ de recherche
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("SearchEdit")
        self.search_edit.setPlaceholderText("Recherche...")
        self.search_edit.setFixedWidth(180)
        self.search_edit.textChanged.connect(self.search_query_changed.emit)
        layout.addWidget(self.search_edit)
