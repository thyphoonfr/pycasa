"""
FR : Boîte de dialogue des propriétés d'album pour PyCasa (CAlbumDialog / album.fen).
Permet de créer ou modifier un album avec titre, date automatique, piste musicale, lieu et description.
EN : Album Properties Dialog for PyCasa (CAlbumDialog / album.fen).
Allows creating or editing an album with title, auto date, music track, location, and description.

Ref: picasa3.exe @ album.fen
Ref: ui/resources/xml/ALBUM_FR.XML / ALBUM.XML
Ref: .picasa.ini @ [.album:<token>]
"""

from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QTextEdit, QDateEdit, QFileDialog,
    QGroupBox, QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QIcon

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaAlbumDialog(QDialog):
    """
    FR : Dialogue de création et d'édition d'album fidèle à album.fen.
    EN : Album creation and editing dialog faithful to album.fen.
    """

    def __init__(
        self,
        album_name: str = "",
        date_str: str = "",
        music_path: str = "",
        location: str = "",
        description: str = "",
        photo_dates: Optional[List[datetime]] = None,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()
        self.photo_dates = photo_dates or []
        self._is_existing_album = bool(album_name)

        self.setWindowTitle("Propriétés de l'album" if album_name else "Nouvel album")
        self.setFixedWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Nom de l'album (Ref: album/namelabel)
        self.lbl_name = QLabel(self.res_mgr.get_xml_string("album/namelabel.title", "Nom :"))
        layout.addWidget(self.lbl_name)
        self.edit_name = QLineEdit(album_name)
        self.edit_name.setPlaceholderText("Nom du nouvel album")
        layout.addWidget(self.edit_name)

        # 2. Date et Date automatique (Ref: album/labelgroup4, autodate)
        self.lbl_date = QLabel(self.res_mgr.get_xml_string("album/labelgroup4.title", "Date :"))
        layout.addWidget(self.lbl_date)
        date_box = QHBoxLayout()
        date_box.setSpacing(8)
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDisplayFormat("dd/MM/yyyy")

        initial_date = QDate.currentDate()
        if date_str:
            try:
                # Tenter format ISO ou standard
                dt = datetime.fromisoformat(date_str.split("T")[0])
                initial_date = QDate(dt.year, dt.month, dt.day)
            except Exception:
                pass
        elif self.photo_dates:
            min_dt = min(self.photo_dates)
            initial_date = QDate(min_dt.year, min_dt.month, min_dt.day)

        self.date_picker.setDate(initial_date)
        date_box.addWidget(self.date_picker)

        self.btn_auto_date = QPushButton(self.res_mgr.get_xml_string("album/autodate.title", "Date automatique"))
        self.btn_auto_date.setToolTip("Calculer la date d'après les photos sélectionnées")
        self.btn_auto_date.clicked.connect(self._on_auto_date)
        date_box.addWidget(self.btn_auto_date)
        date_box.addStretch(1)
        layout.addLayout(date_box)

        # 3. Musique pour diaporama et film (Ref: album/labelgroup8, usemusic, music)
        self.lbl_music = QLabel(self.res_mgr.get_xml_string("album/labelgroup8.title", "Musique :"))
        layout.addWidget(self.lbl_music)
        self.chk_music = QCheckBox(
            self.res_mgr.get_xml_string(
                "album/usemusic.title",
                "Utiliser de la musique pour la présentation du diaporama et du film :",
            )
        )
        self.chk_music.setChecked(bool(music_path))
        self.chk_music.toggled.connect(self._on_music_toggled)
        layout.addWidget(self.chk_music)

        music_box = QHBoxLayout()
        music_box.setContentsMargins(20, 0, 0, 0)
        self.edit_music = QLineEdit(music_path)
        self.edit_music.setReadOnly(True)
        self.edit_music.setPlaceholderText("Aucun fichier audio sélectionné")
        self.edit_music.setEnabled(bool(music_path))
        music_box.addWidget(self.edit_music)

        self.btn_browse_music = QPushButton(self.res_mgr.get_xml_string("album/music.title", "Parcourir..."))
        self.btn_browse_music.setEnabled(bool(music_path))
        self.btn_browse_music.clicked.connect(self._on_browse_music)
        music_box.addWidget(self.btn_browse_music)
        layout.addLayout(music_box)

        # 4. Lieu de prise de vue (Ref: album/labelgroup14)
        self.lbl_location = QLabel(
            self.res_mgr.get_xml_string("album/labelgroup14.title", "Lieu de prise de vue (facultatif) :")
        )
        layout.addWidget(self.lbl_location)
        self.edit_location = QLineEdit(location)
        self.edit_location.setPlaceholderText("ex: Paris, France")
        layout.addWidget(self.edit_location)

        # 5. Description (Ref: album/labelgroup16)
        self.lbl_caption = QLabel(
            self.res_mgr.get_xml_string("album/labelgroup16.title", "Description (facultative) :")
        )
        layout.addWidget(self.lbl_caption)
        self.edit_caption = QTextEdit()
        self.edit_caption.setPlainText(description)
        self.edit_caption.setFixedHeight(60)
        layout.addWidget(self.edit_caption)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 6. Boutons OK / Annuler (Ref: album/ok, button20)
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        self.btn_ok = QPushButton(self.res_mgr.get_xml_string("album/ok.title", "OK"))
        self.btn_ok.setObjectName("PrimaryBtn")
        self.btn_ok.clicked.connect(self._on_accept)
        btn_box.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("album/button20.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)

        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue.
        EN : Dynamically applies the active Picasa theme to the dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#111111"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        border = "#4B5263" if is_dark else "#7F9DB9"
        btn_bg = "#3A3F4B" if is_dark else "#F0F0F0"
        btn_hover = "#484E5C" if is_dark else "#E5E5E5"
        btn_border = "#555B69" if is_dark else "#707070"
        accent = s.accent_color.name()

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
            QLineEdit, QDateEdit, QTextEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 3px;
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
                border-color: {accent};
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
            QCheckBox {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
        """)
        if hasattr(self, "sep"):
            self.sep.setStyleSheet(f"color: {border};")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les libellés du dialogue selon la langue active.
        EN : Updates the dialog labels according to the active language.
        """
        self.lbl_name.setText(self.res_mgr.get_xml_string("album/namelabel.title", "Nom :"))
        self.lbl_date.setText(self.res_mgr.get_xml_string("album/labelgroup4.title", "Date :"))
        self.btn_auto_date.setText(self.res_mgr.get_xml_string("album/autodate.title", "Date automatique"))
        self.lbl_music.setText(self.res_mgr.get_xml_string("album/labelgroup8.title", "Musique :"))
        self.chk_music.setText(
            self.res_mgr.get_xml_string(
                "album/usemusic.title",
                "Utiliser de la musique pour la présentation du diaporama et du film :",
            )
        )
        self.btn_browse_music.setText(self.res_mgr.get_xml_string("album/music.title", "Parcourir..."))
        self.lbl_location.setText(
            self.res_mgr.get_xml_string("album/labelgroup14.title", "Lieu de prise de vue (facultatif) :")
        )
        self.lbl_caption.setText(
            self.res_mgr.get_xml_string("album/labelgroup16.title", "Description (facultative) :")
        )
        self.btn_ok.setText(self.res_mgr.get_xml_string("album/ok.title", "OK"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("album/button20.title", "Annuler"))

    def _on_auto_date(self) -> None:
        """
        FR : Calcule automatiquement la date d'après la plus ancienne photo de l'album.
        EN : Automatically computes the date from the earliest photo in the album.
        """
        if self.photo_dates:
            earliest = min(self.photo_dates)
            self.date_picker.setDate(QDate(earliest.year, earliest.month, earliest.day))
        else:
            self.date_picker.setDate(QDate.currentDate())

    def _on_music_toggled(self, checked: bool) -> None:
        self.edit_music.setEnabled(checked)
        self.btn_browse_music.setEnabled(checked)
        if not checked:
            self.edit_music.clear()

    def _on_browse_music(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier musical",
            "",
            "Fichiers audio (*.mp3 *.wma *.m4a *.wav *.ogg);;Tous les fichiers (*.*)"
        )
        if path:
            self.edit_music.setText(path)

    def _on_accept(self) -> None:
        name = self.edit_name.text().strip()
        if not name:
            self.edit_name.setFocus()
            return
        self.accept()

    def get_album_data(self) -> Dict[str, str]:
        """
        FR : Retourne les paramètres complets de l'album.
        EN : Returns the complete album parameters.
        """
        qd = self.date_picker.date()
        date_iso = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}T00:00:00"
        return {
            "name": self.edit_name.text().strip(),
            "date": date_iso,
            "music": self.edit_music.text().strip() if self.chk_music.isChecked() else "",
            "location": self.edit_location.text().strip(),
            "description": self.edit_caption.toPlainText().strip(),
        }

