"""
FR : Boîte de dialogue des propriétés de l'image pour PyCasa (CImagePropertiesDialog / imageproperties.fen).
Affiche l'ensemble des métadonnées EXIF/IPTC de l'appareil et de l'image sur 2 colonnes avec navigation.
EN : Image Properties Dialog for PyCasa (CImagePropertiesDialog / imageproperties.fen).
Displays complete EXIF/IPTC camera and image metadata in a 2-column list with photo navigation.

Ref: picasa3.exe @ imageproperties.fen
Ref: ui/resources/xml/IMAGEPROPERTIES_FR.XML / IMAGEPROPERTIES.XML
Ref: AGENTS.md §4 bis (Propriétés de l'image fidèles à l'original)
"""

from __future__ import annotations
import os
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.exif_reader import extract_photo_metadata


class PicasaImagePropertiesDialog(QDialog):
    """
    FR : Dialogue modal détaillé des propriétés de l'image (Alt+Entrée).
    EN : Detailed modal dialog for image properties (Alt+Enter).
    """

    def __init__(
        self,
        photo_paths: List[str],
        current_index: int = 0,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()
        self.photo_paths = [p for p in photo_paths if os.path.exists(p)]
        self.current_index = max(0, min(current_index, len(self.photo_paths) - 1)) if self.photo_paths else 0

        self.setWindowTitle("Propriétés")
        self.resize(520, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. En-tête des informations de fichier (Ref: imageproperties/name, path, size, date)
        grid_layout = QVBoxLayout()
        grid_layout.setSpacing(6)

        # Nom
        row_name = QHBoxLayout()
        self.lbl_n = QLabel(self.res_mgr.get_xml_string("imageproperties/labelgroup2.title", "Nom du fichier :"))
        self.lbl_n.setFixedWidth(100)
        row_name.addWidget(self.lbl_n)
        self.val_name = QLabel("")
        self.val_name.setObjectName("TitleLabel")
        row_name.addWidget(self.val_name, 1)
        grid_layout.addLayout(row_name)

        # Emplacement
        row_path = QHBoxLayout()
        self.lbl_p = QLabel(self.res_mgr.get_xml_string("imageproperties/labelgroup4.title", "Emplacement :"))
        self.lbl_p.setFixedWidth(100)
        row_path.addWidget(self.lbl_p)
        self.val_path = QLineEdit("")
        self.val_path.setReadOnly(True)
        row_path.addWidget(self.val_path, 1)
        grid_layout.addLayout(row_path)

        # Taille et Date
        row_meta = QHBoxLayout()
        self.lbl_s = QLabel(self.res_mgr.get_xml_string("imageproperties/labelgroup6.title", "Taille :"))
        self.lbl_s.setFixedWidth(100)
        row_meta.addWidget(self.lbl_s)
        self.val_size = QLabel("")
        self.val_size.setFixedWidth(120)
        row_meta.addWidget(self.val_size)

        self.lbl_d = QLabel(self.res_mgr.get_xml_string("imageproperties/label9.title", "Date :"))
        self.lbl_d.setFixedWidth(40)
        row_meta.addWidget(self.lbl_d)
        self.val_date = QLabel("")
        row_meta.addWidget(self.val_date, 1)
        grid_layout.addLayout(row_meta)

        layout.addLayout(grid_layout)

        # 2. Tableau des propriétés EXIF / IPTC (Ref: imageproperties/list, column12, column13)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([
            self.res_mgr.get_xml_string("imageproperties/column12.title", "Propriété"),
            self.res_mgr.get_xml_string("imageproperties/column13.title", "Valeur"),
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        # 3. Barre de navigation Précédente / Suivante (Ref: imageproperties/nav, prev, next, navlabel)
        nav_box = QHBoxLayout()
        prev_txt = self.res_mgr.get_xml_string("imageproperties/prev.title", "Préc.")
        self.btn_prev = QPushButton(f"◀ {prev_txt}")
        self.btn_prev.clicked.connect(self._navigate_prev)
        nav_box.addWidget(self.btn_prev)

        self.lbl_nav = QLabel("0 sur 0 fichiers")
        self.lbl_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_box.addWidget(self.lbl_nav, 1)

        next_txt = self.res_mgr.get_xml_string("imageproperties/next.title", "Suivant")
        self.btn_next = QPushButton(f"{next_txt} ▶")
        self.btn_next.clicked.connect(self._navigate_next)
        nav_box.addWidget(self.btn_next)

        layout.addLayout(nav_box)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 4. Bouton Fermer / OK
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        self.btn_ok = QPushButton("Fermer")
        self.btn_ok.setObjectName("PrimaryBtn")
        self.btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_ok)
        layout.addLayout(btn_box)

        # Raccourcis clavier (Flèches gauche et droite pour naviguer)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._navigate_prev)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._navigate_next)

        self.apply_style(self.style)
        self._load_current_photo()

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue des propriétés.
        EN : Dynamically applies the active Picasa theme to the image properties dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#111111"
        inp_bg = "#1E2127" if is_dark else "#F8F8F8"
        tbl_bg = "#1E2127" if is_dark else "#FFFFFF"
        tbl_alt = "#282C34" if is_dark else "#F5F5F5"
        grid_col = "#3A3F4B" if is_dark else "#E0E0E0"
        border = "#4B5263" if is_dark else "#7F9DB9"
        hdr_border = "#4B5263" if is_dark else "#ACA899"
        btn_bg = "#3A3F4B" if is_dark else "#F0F0F0"
        btn_hover = "#484E5C" if is_dark else "#E5E5E5"
        btn_border = "#555B69" if is_dark else "#707070"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
            QLabel#TitleLabel {{
                font-weight: bold;
                font-size: 12px;
                color: {fg};
            }}
            QLineEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 2px 4px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QTableWidget {{
                background-color: {tbl_bg};
                color: {fg};
                alternate-background-color: {tbl_alt};
                border: 1px solid {border};
                gridline-color: {grid_col};
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {hdr_border};
                padding: 3px;
                font-weight: bold;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 12px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                min-width: 65px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: #3C7FB1;
                color: {fg};
            }}
            QPushButton#PrimaryBtn {{
                background-color: #2F6DB5;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #1E4E85;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: #3879D9;
                color: #FFFFFF;
            }}
        """)
        if hasattr(self, "sep"):
            self.sep.setStyleSheet(f"color: {border};")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes selon la langue active.
        EN : Updates texts according to the active language.
        """
        self.lbl_n.setText(self.res_mgr.get_xml_string("imageproperties/labelgroup2.title", "Nom du fichier :"))
        self.lbl_p.setText(self.res_mgr.get_xml_string("imageproperties/labelgroup4.title", "Emplacement :"))
        self.lbl_s.setText(self.res_mgr.get_xml_string("imageproperties/labelgroup6.title", "Taille :"))
        self.lbl_d.setText(self.res_mgr.get_xml_string("imageproperties/label9.title", "Date :"))
        self.table.setHorizontalHeaderLabels([
            self.res_mgr.get_xml_string("imageproperties/column12.title", "Propriété"),
            self.res_mgr.get_xml_string("imageproperties/column13.title", "Valeur"),
        ])
        prev_txt = self.res_mgr.get_xml_string("imageproperties/prev.title", "Préc.")
        next_txt = self.res_mgr.get_xml_string("imageproperties/next.title", "Suivant")
        self.btn_prev.setText(f"◀ {prev_txt}")
        self.btn_next.setText(f"{next_txt} ▶")

    def _load_current_photo(self) -> None:
        """
        FR : Charge et affiche les métadonnées EXIF/IPTC de la photo courante.
        EN : Loads and displays EXIF/IPTC metadata for the current photo.
        """
        if not self.photo_paths or self.current_index < 0 or self.current_index >= len(self.photo_paths):
            self.val_name.setText("Aucun fichier")
            self.val_path.setText("")
            self.val_size.setText("")
            self.val_date.setText("")
            self.lbl_nav.setText("0 sur 0 fichiers")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.table.setRowCount(0)
            return

        file_path = self.photo_paths[self.current_index]
        data = extract_photo_metadata(file_path)

        self.val_name.setText(data.get("filename", os.path.basename(file_path)))
        self.val_path.setText(data.get("folder", os.path.dirname(file_path)))
        self.val_size.setText(data.get("filesize", ""))
        self.val_date.setText(data.get("date", ""))

        total = len(self.photo_paths)
        self.lbl_nav.setText(f"{self.current_index + 1} sur {total} fichiers")
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < total - 1)

        props = data.get("properties", [])
        self.table.setRowCount(len(props))
        for row, (prop_name, prop_val) in enumerate(props):
            item_prop = QTableWidgetItem(str(prop_name))
            item_val = QTableWidgetItem(str(prop_val))
            self.table.setItem(row, 0, item_prop)
            self.table.setItem(row, 1, item_val)

    def _navigate_prev(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self._load_current_photo()

    def _navigate_next(self) -> None:
        if self.current_index < len(self.photo_paths) - 1:
            self.current_index += 1
            self._load_current_photo()
