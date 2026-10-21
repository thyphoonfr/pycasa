"""
FR : Boîte de dialogue d'envoi de photos par e-mail pour PyCasa (CHOOSE_MAIL_TEXT.XML / COMPOSE_MAIL_TEXT.XML).
Prépare les photos sélectionnées, les redimensionne et lance le client de messagerie par défaut.
EN : Email Photos Dialog for PyCasa (CHOOSE_MAIL_TEXT.XML / COMPOSE_MAIL_TEXT.XML).
Prepares selected photos for emailing, resizes them, and launches the default mail client.

Ref: picasa3.exe @ CHOOSE_MAIL_TEXT.XML, COMPOSE_MAIL_TEXT.XML
Ref: runtime/constants.ui [Picasa2]
"""

from __future__ import annotations
import os
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QTextEdit,
    QProgressBar, QMessageBox, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtCore import QUrl

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaEmailDialog(QDialog):
    """
    FR : Dialogue de préparation et d'envoi de photos par courrier électronique.
    EN : Photo preparation and email sending dialog.
    """

    def __init__(
        self,
        photo_paths: List[str],
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.photo_paths = [p for p in photo_paths if os.path.exists(p)]
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle("Envoyer des photos par e-mail")
        self.setFixedWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. En-tête : nombre de photos
        self.lbl_count = QLabel(f"<b>{len(self.photo_paths)}</b> photo(s) sélectionnée(s) pour l'envoi")
        layout.addWidget(self.lbl_count)

        # 2. Groupe de redimensionnement pour l'envoi
        self.grp_size = QGroupBox("Taille des images :")
        grp_size_layout = QVBoxLayout(self.grp_size)
        grp_size_layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.rb_1024 = QRadioButton("1024 × 768 pixels (recommandé pour e-mail)")
        self.rb_800 = QRadioButton("800 × 600 pixels (pour écrans plus petits)")
        self.rb_640 = QRadioButton("640 × 480 pixels (taille compacte)")
        self.rb_orig = QRadioButton("Taille originale (fichiers volumineux)")

        self.rb_1024.setChecked(True)
        self.btn_group.addButton(self.rb_1024, 1024)
        self.btn_group.addButton(self.rb_800, 800)
        self.btn_group.addButton(self.rb_640, 640)
        self.btn_group.addButton(self.rb_orig, 0)

        grp_size_layout.addWidget(self.rb_1024)
        grp_size_layout.addWidget(self.rb_800)
        grp_size_layout.addWidget(self.rb_640)
        grp_size_layout.addWidget(self.rb_orig)
        layout.addWidget(self.grp_size)

        # 3. Champs Destinataire et Objet
        meta_box = QVBoxLayout()
        meta_box.setSpacing(6)

        self.lbl_to = QLabel(self.res_mgr.get_xml_string("compose_mail_text/to.title", "À (Destinataire) :"))
        meta_box.addWidget(self.lbl_to)
        self.edit_to = QLineEdit()
        self.edit_to.setPlaceholderText("destinataire@example.com")
        meta_box.addWidget(self.edit_to)

        self.lbl_subject = QLabel(self.res_mgr.get_xml_string("compose_mail_text/subject.title", "Objet :"))
        meta_box.addWidget(self.lbl_subject)
        self.edit_subject = QLineEdit(f"Photos partagées ({len(self.photo_paths)} images)")
        meta_box.addWidget(self.edit_subject)

        self.lbl_body = QLabel(self.res_mgr.get_xml_string("compose_mail_text/message.title", "Message :"))
        meta_box.addWidget(self.lbl_body)
        self.edit_body = QTextEdit()
        self.edit_body.setPlainText("Bonjour,\n\nVoici des photos partagées depuis Picasa.")
        self.edit_body.setFixedHeight(60)
        meta_box.addWidget(self.edit_body)

        layout.addLayout(meta_box)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 4. Boutons d'action
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        self.btn_send = QPushButton("Créer le message")
        self.btn_send.setObjectName("PrimaryBtn")
        self.btn_send.clicked.connect(self._prepare_and_send)
        btn_box.addWidget(self.btn_send)

        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue e-mail.
        EN : Dynamically applies the active Picasa theme to the email dialog.
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

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel, QGroupBox {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
            QLineEdit, QTextEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 3px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QRadioButton {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
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
        self.lbl_to.setText(self.res_mgr.get_xml_string("compose_mail_text/to.title", "À (Destinataire) :"))
        self.lbl_subject.setText(self.res_mgr.get_xml_string("compose_mail_text/subject.title", "Objet :"))
        self.lbl_body.setText(self.res_mgr.get_xml_string("compose_mail_text/message.title", "Message :"))

    def _prepare_and_send(self) -> None:
        """
        FR : Redimensionne les photos dans un dossier temporaire et ouvre le client mail système.
        EN : Resizes photos into a temporary folder and opens the system mail client.
        """
        target_size = self.btn_group.checkedId()
        out_dir = tempfile.mkdtemp(prefix="picasa_mail_")
        exported_files: List[str] = []

        for p in self.photo_paths:
            try:
                dest_path = os.path.join(out_dir, os.path.basename(p))
                from picasa_py.ui.image_processor import PicasaImageProcessor
                img_copy = PicasaImageProcessor.load_transformed_image(
                    p, max_size=target_size if target_size > 0 else 0
                )
                if img_copy is not None:
                    if img_copy.mode in ("RGBA", "P"):
                        img_copy = img_copy.convert("RGB")
                    img_copy.save(dest_path, "JPEG", quality=85 if target_size > 0 else 95)
                    exported_files.append(dest_path)
            except Exception:
                pass

        # Lancer le client mail système via mailto ou explorer le dossier
        subject = urllib.parse.quote(self.edit_subject.text())
        body = urllib.parse.quote(self.edit_body.toPlainText() + f"\n\n({len(exported_files)} photo(s) préparée(s))")
        to = urllib.parse.quote(self.edit_to.text().strip())

        mailto_uri = f"mailto:{to}?subject={subject}&body={body}"
        QDesktopServices.openUrl(QUrl(mailto_uri))

        # Ouvrir le dossier temporaire contenant les images redimensionnées prêtes à glisser-déposer (Windows/macOS/Linux)
        if exported_files:
            import subprocess
            try:
                if sys.platform == "win32":
                    os.startfile(out_dir)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", out_dir])
                else:
                    subprocess.Popen(["xdg-open", out_dir])
            except Exception:
                pass

        self.accept()
