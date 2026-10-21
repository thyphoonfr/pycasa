"""
FR : Boîte de dialogue de format de recadrage personnalisé pour PyCasa.
Réimplémente fidèlement le dialogue customaspectratio.fen (CustomAspectRatioDlg) de Picasa 3.
EN : Custom Aspect Ratio Dialog for PyCasa.
Re-implements Picasa 3's customaspectratio.fen dialog (CustomAspectRatioDlg).

Ref: picasa3.exe @ CustomAspectRatioDlg, CustomAspectRatios (0x0088C3EC)
Ref: runtime/customaspectratio.fen
"""

from __future__ import annotations
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle


class PicasaCustomAspectRatioDialog(QDialog):
    """
    FR : Dialogue d'ajout d'un format de recadrage personnalisé.
    EN : Dialog for adding a custom crop aspect ratio.
    Ref: customaspectratio.fen
    """

    def __init__(self, parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()
        self.style = style or getattr(parent, "style", None) or PicasaStyle.instance()
        self.setWindowTitle(
            self.res_mgr.get_xml_string("customaspectratio/window1.title", "Ajouter un format personnalisé")
        )
        self.setFixedSize(320, 210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Dimensions (Ref: labelgroup title="Dimensions:" width x height)
        self.lbl_dim = QLabel(
            f"<b>{self.res_mgr.get_xml_string('customaspectratio/labelgroup2.title', 'Dimensions :')}</b>"
        )
        layout.addWidget(self.lbl_dim)

        h_dim = QHBoxLayout()
        h_dim.setSpacing(8)
        self.edit_width = QLineEdit("16")
        self.edit_width.setFixedWidth(50)
        self.edit_width.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_dim.addWidget(self.edit_width)

        lbl_x = QLabel("x")
        lbl_x.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_dim.addWidget(lbl_x)

        self.edit_height = QLineEdit("10")
        self.edit_height.setFixedWidth(50)
        self.edit_height.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_dim.addWidget(self.edit_height)
        h_dim.addStretch(1)
        layout.addLayout(h_dim)

        # 2. Nom (Ref: labelgroup title="Name:" edit name="title")
        self.lbl_name = QLabel(
            f"<b>{self.res_mgr.get_xml_string('customaspectratio/labelgroup8.title', 'Nom du format :')}</b>"
        )
        layout.addWidget(self.lbl_name)

        self.edit_name = QLineEdit("Écran large 16:10")
        layout.addWidget(self.edit_name)

        # 3. Exemple (Ref: labelgroup title="Example:" label title=" 4 x 6 Small print")
        self.lbl_ex = QLabel("Exemple :  4 x 6   Tirage petit format")
        layout.addWidget(self.lbl_ex)

        layout.addStretch(1)

        # 4. Boutons OK / Annuler (Ref: buttongroup type="accept", type="cancel")
        h_btns = QHBoxLayout()
        h_btns.addStretch(1)

        self.btn_ok = QPushButton(self.res_mgr.get_xml_string("customaspectratio/button15.title", "OK"))
        self.btn_ok.setObjectName("OkBtn")
        self.btn_ok.clicked.connect(self._on_accept)
        h_btns.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("customaspectratio/button16.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)
        h_btns.addWidget(self.btn_cancel)

        layout.addLayout(h_btns)

        self.result_ratio: Optional[float] = None
        self.result_name: Optional[str] = None
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
        bg = "#24272E" if is_dark else "#EBE8E1"
        fg = "#F0F2F5" if is_dark else "#111111"
        sub_fg = "#9DA5B4" if is_dark else "#666666"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        border = "#4B5263" if is_dark else "#7F9DB9"
        btn_bg = "#3A3F4B" if is_dark else "#ECE9D8"
        btn_hover = "#484E5C" if is_dark else "#E2DFCE"
        btn_border = "#555B69" if is_dark else "#707070"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                color: {fg};
                font-size: 11px;
            }}
            QLineEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 3px 6px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: #3879D9;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 16px;
                font-size: 11px;
                min-width: 65px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: {fg};
            }}
            QPushButton#OkBtn {{
                font-weight: bold;
                background-color: #3879D9;
                color: #FFFFFF;
                border: 1px solid #2859A3;
            }}
            QPushButton#OkBtn:hover {{
                background-color: #4A8BF0;
                color: #FFFFFF;
            }}
        """)
        self.lbl_ex.setStyleSheet(f"color: {sub_fg}; font-size: 10px; font-style: italic;")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes selon la langue active.
        EN : Updates the texts according to the active language.
        """
        self.setWindowTitle(
            self.res_mgr.get_xml_string("customaspectratio/window1.title", "Ajouter un format personnalisé")
        )
        self.lbl_dim.setText(
            f"<b>{self.res_mgr.get_xml_string('customaspectratio/labelgroup2.title', 'Dimensions :')}</b>"
        )
        self.lbl_name.setText(
            f"<b>{self.res_mgr.get_xml_string('customaspectratio/labelgroup8.title', 'Nom du format :')}</b>"
        )
        self.btn_ok.setText(self.res_mgr.get_xml_string("customaspectratio/button15.title", "OK"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("customaspectratio/button16.title", "Annuler"))

    def _on_accept(self) -> None:
        try:
            w_str = self.edit_width.text().strip().replace(",", ".")
            h_str = self.edit_height.text().strip().replace(",", ".")
            w = float(w_str)
            h = float(h_str)
            if w <= 0 or h <= 0:
                raise ValueError("Les dimensions doivent être strictement positives.")
        except Exception:
            QMessageBox.warning(self, "Erreur", "Veuillez saisir des nombres valides pour la largeur et la hauteur.")
            return

        name = self.edit_name.text().strip()
        if not name:
            name = f"{w_str} x {h_str}"

        self.result_ratio = w / h
        self.result_name = name
        self.accept()

    def get_custom_ratio(self) -> Optional[Tuple[str, float]]:
        """
        FR : Retourne (nom, ratio) si accepté, ou None.
        EN : Returns (name, ratio) if accepted, or None.
        """
        if self.result_ratio is not None and self.result_name is not None:
            return (self.result_name, self.result_ratio)
        return None
