"""
FR : Boîte de dialogue d'attribution et de modification d'un visage à une personne.
Inclut l'aperçu de l'avatar recadré, l'autocomplétion des contacts connus et la suppression.
EN : Face Naming and Reassignment Dialog for PyCasa.
Includes cropped avatar preview, known contacts autocompletion, and face deletion.

Ref: picasa3.exe @ 0x008A1034 (peoplepanel/manual_add_editbox)
Ref: picasa3.exe @ 0x008A15D0 (peoplepanel/manual_add_autocomplete)
Ref: picasa3.exe @ 0x008A13B8 (peoplepanel/addname)
Ref: picasa3.exe @ 0x00896FA8 (removesel / ignore)
"""

from __future__ import annotations
import os
from typing import List, Optional
from PIL import Image

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCompleter,
    QFrame,
    QWidget,
)
from PySide6.QtCore import Qt, Signal, QStringListModel
from PySide6.QtGui import QPixmap, QFont, QIcon

from picasa_py.faces.facerect import FaceRect
from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaNameFaceDialog(QDialog):
    """
    FR : Dialogue modal permettant de nommer, réassigner ou supprimer un visage.
    EN : Modal dialog for naming, reassigning, or deleting a face.
    """

    def __init__(
        self,
        face_rect: FaceRect,
        photo_path: str,
        existing_names: List[str],
        current_name: Optional[str] = None,
        is_new_face: bool = False,
        parent: Optional[QWidget] = None,
        source_image: Optional[Image.Image] = None,
        style: Optional[PicasaStyle] = None,
    ):
        super().__init__(parent)
        self.face_rect = face_rect
        self.photo_path = photo_path
        self.existing_names = sorted(list(set(existing_names)))
        self.current_name = current_name or ""
        self.is_new_face = is_new_face
        self.delete_requested = False
        self.source_image = source_image
        self.res_mgr = PicasaResourceManager.get()
        self.style = style or getattr(parent, "style", None) or PicasaStyle.instance()

        self.setWindowTitle(
            self.res_mgr.get_xml_string("peoplepanel/addname.title", "Ajouter un nom")
            if is_new_face
            else "Modifier la personne"
        )
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # En-tête avec avatar découpé et prompt
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(64, 64)
        self._load_avatar()
        header_layout.addWidget(self.avatar_lbl)

        prompt_layout = QVBoxLayout()
        prompt_layout.setSpacing(4)
        title_text = "Qui est cette personne ?" if is_new_face else "Nom de la personne :"
        self.title_lbl = QLabel(title_text)
        prompt_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("Saisissez un nouveau nom ou choisissez dans la liste.")
        self.sub_lbl.setWordWrap(True)
        prompt_layout.addWidget(self.sub_lbl)

        header_layout.addLayout(prompt_layout, 1)
        layout.addLayout(header_layout)

        # Champ de texte avec autocomplétion (Ref: peoplepanel/manual_add_autocomplete)
        self.name_edit = QLineEdit(self.current_name)
        self.name_edit.setPlaceholderText("Nom et prénom...")
        self.name_edit.returnPressed.connect(self._on_accept)

        if self.existing_names:
            completer = QCompleter(self.existing_names, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.name_edit.setCompleter(completer)

        layout.addWidget(self.name_edit)

        # Barre des boutons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        if not is_new_face:
            self.btn_delete = QPushButton("Supprimer le visage")
            self.btn_delete.setObjectName("btnDelete")
            self.btn_delete.clicked.connect(self._on_delete)
            btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch(1)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("peoplepanel/cancel.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton(self.res_mgr.get_xml_string("peoplepanel/ok.title", "OK"))
        self.btn_ok.setObjectName("btnOk")
        self.btn_ok.clicked.connect(self._on_accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

        self.apply_style(self.style)

        self.name_edit.selectAll()
        self.name_edit.setFocus()

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue.
        EN : Dynamically applies the active Picasa theme to the dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        dlg_bg = s.window_bgcolor.name() if not is_dark else "#24272E"
        txt_col = s.alayout_titleColor.name() if not is_dark else "#FFFFFF"
        sub_col = s.alayout_subtitleColor.name() if not is_dark else "#9DA5B4"
        inp_bg = "#FFFFFF" if not is_dark else "#1E2127"
        brd_col = s.splitter_color.name() if not is_dark else "#4B5263"
        btn_bg = s.topbar_btn_bg_start.name() if not is_dark else "#3A3F4B"
        accent = s.accent_color.name()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {txt_col};
                border: 1px solid {brd_col};
                border-radius: 8px;
            }}
            QLabel {{
                color: {txt_col};
                font-family: "Segoe UI", Tahoma, sans-serif;
            }}
            QLineEdit {{
                background-color: {inp_bg};
                color: {txt_col};
                border: 1px solid {brd_col};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: {accent};
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {txt_col};
                border: 1px solid {brd_col};
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {accent};
            }}
            QPushButton#btnOk {{
                background-color: {accent};
                color: #FFFFFF;
                border-color: {accent};
            }}
            QPushButton#btnDelete {{
                background-color: transparent;
                color: #C62828;
                border: 1px solid #C62828;
            }}
        """)
        self.title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {txt_col};")
        self.sub_lbl.setStyleSheet(f"font-size: 11px; color: {sub_col};")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes selon la langue active.
        EN : Updates texts according to the active language.
        """
        self.setWindowTitle(
            self.res_mgr.get_xml_string("peoplepanel/addname.title", "Ajouter un nom")
            if self.is_new_face
            else "Modifier la personne"
        )
        self.btn_cancel.setText(self.res_mgr.get_xml_string("peoplepanel/cancel.title", "Annuler"))
        self.btn_ok.setText(self.res_mgr.get_xml_string("peoplepanel/ok.title", "OK"))

    def _load_avatar(self) -> None:
        """
        FR : Découpe un aperçu circulaire du visage avec orientation et retouches fidèles.
        EN : Crops a circular preview of the face with faithful orientation and edits.
        """
        img = self.source_image
        if img is None and self.photo_path and os.path.exists(self.photo_path):
            from picasa_py.ui.image_processor import PicasaImageProcessor
            img = PicasaImageProcessor.load_transformed_image(self.photo_path)
        if img is not None:
            try:
                w_img, h_img = img.size
                aspect_img = (w_img / float(h_img)) if h_img > 0 else 1.0
                disp_fr = (
                    self.face_rect.project_for_photo_ini(self.photo_path, aspect_ratio=aspect_img)
                    if hasattr(self.face_rect, "project_for_photo_ini")
                    else self.face_rect
                )
                pix = disp_fr.crop_avatar(img, avatar_size=64, circular=True)
                if not pix.isNull():
                    self.avatar_lbl.setPixmap(pix)
                    return
            except Exception:
                pass
        self.avatar_lbl.setText("👤")
        self.avatar_lbl.setStyleSheet("font-size: 32px; background: #1C1E22; border-radius: 32px;")
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _on_accept(self) -> None:
        if self.get_contact_name():
            self.accept()

    def _on_delete(self) -> None:
        self.delete_requested = True
        self.accept()

    def get_contact_name(self) -> str:
        return self.name_edit.text().strip()

    def is_delete_requested(self) -> bool:
        return self.delete_requested
