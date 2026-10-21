"""
FR: Composant du panneau d'édition pour la vue One-Up de PyCasa (volet latéral gauche d'édition).
Contient les 5 onglets d'outils de retouche et de filtres de Picasa 3.
EN: Edit Panel component for PyCasa One-Up View (Left editing sidebar).
Contains the 5 tabs of Picasa 3 editing tools and filters.

Ref: picasa3.exe @ editoneup, filterdesc.xml
Ref: runtime/constants.ui [Picasa2]
"""

from __future__ import annotations
from typing import Dict, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QToolButton, QLabel,
    QTabWidget, QSlider, QFrame, QScrollArea, QGridLayout,
    QStackedWidget, QRadioButton, QButtonGroup, QLineEdit, QCheckBox,
    QColorDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPen

from PIL import Image
from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.histogram_widget import PicasaHistogramWidget, PicasaCameraInfoCard
from picasa_py.ui.image_processor import PicasaImageProcessor


class PicasaCropSubpanel(QWidget):
    """
    FR: Sous-panneau officiel de recadrage avec sélection de format et boutons d'application.
    EN: Official cropping subpanel with aspect ratio selection and apply/discard buttons.
    Ref: picasa3.exe @ editpanel/crop*, customaspectratio.fen
    """
    ratio_changed = Signal(object)
    apply_clicked = Signal()
    discard_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le sous-panneau de recadrage et ses formats prédéfinis ou personnalisés.
        EN: Initializes the cropping subpanel and its preset or custom aspect ratios.
        """
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. FR: En-tête / EN: Header (Ref: editpanel/crop_label)
        self.lbl_title = QLabel(self.res_mgr.get_xml_string("editpanel/crop_label", "Recadrer la photo"))
        self.lbl_title.setObjectName("SubpanelTitle")
        layout.addWidget(self.lbl_title)

        # 2. FR: Explication / EN: Description (Ref: editpanel/croptext)
        self.lbl_desc = QLabel(self.res_mgr.get_xml_string(
            "editpanel/croptext",
            "Sélectionnez une dimension ci-dessous et faites glisser le pointeur sur l'image pour sélectionner la partie à recadrer."
        ))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setObjectName("SubpanelDesc")
        layout.addWidget(self.lbl_desc)

        # 3. FR: Formats / Ratios prédéfinis / EN: Preset formats / Aspect ratios
        self.btn_group = QButtonGroup(self)
        ratios = [
            ("Manuel (libre)", None),
            ("Carré (1:1)", 1.0),
            ("4:3 (Photo standard / TV)", 4.0 / 3.0),
            ("16:9 (Écran large / HD)", 16.0 / 9.0),
            ("4 x 6 (Tirage petit format)", 6.0 / 4.0),
            ("5 x 7 (Format moyen)", 7.0 / 5.0),
            ("8 x 10 (Grand format)", 10.0 / 8.0),
        ]

        # FR: Charger les formats personnalisés persistés / EN: Load persisted custom aspect ratios (Ref: customaspectratio.fen)
        try:
            from picasa_py.db.preferences import PicasaPreferences
            import json
            settings = PicasaPreferences()
            custom_list = settings.value("CustomAspectRatios", [])
            if isinstance(custom_list, str):
                custom_list = json.loads(custom_list)
            if isinstance(custom_list, list):
                for item in custom_list:
                    if isinstance(item, dict) and "name" in item and "val" in item:
                        ratios.append((item["name"], float(item["val"])))
        except Exception:
            pass

        self.radio_buttons = []
        for i, (name, val) in enumerate(ratios):
            rb = QRadioButton(name)
            rb.setStyleSheet("font-size: 11px; padding: 2px;")
            if i == 0:
                rb.setChecked(True)
            self.btn_group.addButton(rb, i)
            layout.addWidget(rb)
            self.radio_buttons.append((rb, val))

        self.btn_group.idClicked.connect(self._on_ratio_clicked)

        # FR: Bouton d'ajout de format personnalisé / EN: Add custom aspect ratio button (Ref: customaspectratio.fen)
        self.btn_add_custom = QPushButton("+ Ajouter un format personnalisé...")
        self.btn_add_custom.setObjectName("LinkBtn")
        self.btn_add_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_custom.clicked.connect(self._open_custom_aspect_ratio_dialog)
        layout.addWidget(self.btn_add_custom)

        layout.addStretch(1)

        # 4. FR: Boutons d'action : Appliquer, Réinitialiser, Annuler / EN: Action buttons: Apply, Discard, Cancel
        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_apply = QPushButton(self.res_mgr.get_xml_string("editpanel/cropapply", "Appliquer"))
        self.btn_apply.setObjectName("ApplyCropBtn")
        self.btn_apply.setStyleSheet("""
            QPushButton#ApplyCropBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #2859A3;
            }
            QPushButton#ApplyCropBtn:hover {
                background-color: #4A8BF0;
            }
        """)
        self.btn_apply.clicked.connect(self.apply_clicked.emit)
        btns_layout.addWidget(self.btn_apply)

        h_sub_btns = QHBoxLayout()
        self.btn_discard = QPushButton(self.res_mgr.get_xml_string("editpanel/cropdiscard", "Réinitialiser"))
        self.btn_discard.setObjectName("SmallActionBtn")
        self.btn_discard.clicked.connect(self.discard_clicked.emit)
        h_sub_btns.addWidget(self.btn_discard)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("editpanel/cropcancel", "Annuler"))
        self.btn_cancel.setObjectName("SmallActionBtn")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        h_sub_btns.addWidget(self.btn_cancel)
        btns_layout.addLayout(h_sub_btns)

        layout.addLayout(btns_layout)

    def _on_ratio_clicked(self, id_: int) -> None:
        """
        FR: Émet le nouveau ratio de recadrage sélectionné par l'utilisateur.
        EN: Emits the new crop aspect ratio selected by the user.
        """
        if 0 <= id_ < len(self.radio_buttons):
            _, ratio_val = self.radio_buttons[id_]
            self.ratio_changed.emit(ratio_val)

    def reset_to_manual(self) -> None:
        """
        FR: Réinitialise la sélection de format sur le mode « Manuel (libre) ».
        EN: Resets the aspect ratio selection to "Manual (free)" mode.
        """
        if self.radio_buttons:
            self.radio_buttons[0][0].setChecked(True)

    def _open_custom_aspect_ratio_dialog(self) -> None:
        """
        FR: Ouvre le dialogue d'ajout de format de recadrage personnalisé (customaspectratio.fen).
        EN: Opens the custom crop aspect ratio dialog (customaspectratio.fen).
        """
        from picasa_py.ui.custom_aspect_ratio_dialog import PicasaCustomAspectRatioDialog
        dlg = PicasaCustomAspectRatioDialog(parent=self.window())
        if dlg.exec():
            res = dlg.get_custom_ratio()
            if res:
                name, val = res
                idx = len(self.radio_buttons)
                rb = QRadioButton(name)
                rb.setStyleSheet("font-size: 11px; padding: 2px;")
                self.btn_group.addButton(rb, idx)
                self.layout().insertWidget(self.layout().indexOf(self.btn_add_custom), rb)
                self.radio_buttons.append((rb, val))
                rb.setChecked(True)
                self.ratio_changed.emit(val)

                # FR: Persister via PicasaPreferences / EN: Persist via PicasaPreferences
                try:
                    from picasa_py.db.preferences import PicasaPreferences
                    import json
                    settings = PicasaPreferences()
                    custom_raw = settings.value("CustomAspectRatios", [])
                    if isinstance(custom_raw, str):
                        custom_list = json.loads(custom_raw)
                    elif isinstance(custom_raw, list):
                        custom_list = list(custom_raw)
                    else:
                        custom_list = []
                    custom_list.append({"name": name, "val": val})
                    settings.setValue("CustomAspectRatios", json.dumps(custom_list))
                except Exception:
                    pass


class PicasaStraightenSubpanel(QWidget):
    """
    FR: Sous-panneau officiel de redressement avec curseur d'angle et niveau d'alignement.
    EN: Official straightening subpanel with angle slider and alignment level.
    Ref: picasa3.exe @ filter_tilt (0x008814AC), IDS_WARN_CROP_ACCURACY
    """
    angle_changed = Signal(float)
    apply_clicked = Signal()
    reset_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le sous-panneau de redressement et son curseur d'angle (-45° à +45°).
        EN: Initializes the straightening subpanel and its angle slider (-45° to +45°).
        """
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 1. FR: En-tête / EN: Header (Ref: filter_tilt_label0)
        lbl_title = QLabel(self.res_mgr.get_string("filter_tilt_label0", "Redresser la photo"))
        lbl_title.setObjectName("SubpanelTitle")
        layout.addWidget(lbl_title)

        # 2. FR: Explication / EN: Description
        lbl_desc = QLabel("Faites glisser le curseur pour aligner l'horizon. La photo est automatiquement recadrée pour éviter les coins noirs.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("SubpanelDesc")
        layout.addWidget(lbl_desc)

        # 3. FR: Slider d'angle (-45.0° à +45.0°) avec affichage numérique / EN: Angle slider (-45.0° to +45.0°) with numeric display
        slider_box = QVBoxLayout()
        slider_box.setSpacing(4)

        header_slider = QHBoxLayout()
        lbl_angle_name = QLabel("Angle :")
        lbl_angle_name.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.lbl_angle_val = QLabel("0.0°")
        self.lbl_angle_val.setObjectName("SubpanelValue")
        header_slider.addWidget(lbl_angle_name)
        header_slider.addStretch()
        header_slider.addWidget(self.lbl_angle_val)
        slider_box.addLayout(header_slider)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-450, 450)  # FR: Valeur / 10 = degrés / EN: Value / 10 = degrees
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self._on_slider_changed)
        slider_box.addWidget(self.slider)

        # FR: Repères -45°, 0°, +45° / EN: Ticks -45°, 0°, +45°
        ticks_layout = QHBoxLayout()
        lbl_m45 = QLabel("-45°")
        lbl_0 = QLabel("0°")
        lbl_p45 = QLabel("+45°")
        for l in (lbl_m45, lbl_0, lbl_p45):
            l.setObjectName("SubpanelTick")
        ticks_layout.addWidget(lbl_m45)
        ticks_layout.addStretch()
        ticks_layout.addWidget(lbl_0)
        ticks_layout.addStretch()
        ticks_layout.addWidget(lbl_p45)
        slider_box.addLayout(ticks_layout)

        layout.addLayout(slider_box)

        layout.addStretch(1)

        # 4. FR: Boutons d'action : Appliquer, Réinitialiser, Annuler / EN: Action buttons: Apply, Reset, Cancel
        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_apply = QPushButton(self.res_mgr.get_string("editpanel/cropapply", "Appliquer"))
        self.btn_apply.setObjectName("ApplyStraightenBtn")
        self.btn_apply.setStyleSheet("""
            QPushButton#ApplyStraightenBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #2859A3;
            }
            QPushButton#ApplyStraightenBtn:hover {
                background-color: #4A8BF0;
            }
        """)
        self.btn_apply.clicked.connect(self.apply_clicked.emit)
        btns_layout.addWidget(self.btn_apply)

        h_sub = QHBoxLayout()
        self.btn_reset = QPushButton("Réinitialiser")
        self.btn_reset.setObjectName("SmallActionBtn")
        self.btn_reset.clicked.connect(self.reset_angle)
        h_sub.addWidget(self.btn_reset)

        self.btn_cancel = QPushButton(self.res_mgr.get_string("editpanel/cropcancel", "Annuler"))
        self.btn_cancel.setObjectName("SmallActionBtn")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        h_sub.addWidget(self.btn_cancel)
        btns_layout.addLayout(h_sub)

        layout.addLayout(btns_layout)

    def _on_slider_changed(self, val: int) -> None:
        """
        FR: Convertit la position du curseur en degrés et émet le signal `angle_changed`.
        EN: Converts the slider position to degrees and emits the `angle_changed` signal.
        """
        deg = val / 10.0
        self.lbl_angle_val.setText(f"{deg:+.1f}°")
        self.angle_changed.emit(deg)

    def reset_angle(self) -> None:
        """
        FR: Réinitialise l'angle de redressement à 0.0° et émet `reset_clicked`.
        EN: Resets the straightening angle to 0.0° and emits `reset_clicked`.
        """
        self.slider.setValue(0)
        self.lbl_angle_val.setText("0.0°")
        self.reset_clicked.emit()

    def set_angle_from_canvas(self, deg: float) -> None:
        """
        FR: Met à jour le curseur lors d'une rotation interactive sur l'image.
        EN: Updates the slider during interactive rotation on the image canvas.
        """
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(deg * 10.0)))
        self.lbl_angle_val.setText(f"{deg:+.1f}°")
        self.slider.blockSignals(False)


class PicasaTextSubpanel(QWidget):
    """
    FR: Sous-panneau officiel d'ajout de texte sur photo.
    EN: Official text overlay subpanel for photos.
    Ref: picasa3.exe @ editpanel/edittextpanel (0x00658900), EditText::GhostText, editpanel/edittextshadow
    """
    params_changed = Signal(str, int, object, bool)
    apply_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le sous-panneau d'outil texte (champ de saisie, taille, couleur, ombre).
        EN: Initializes the text tool subpanel (input field, font size, color, shadow).
        """
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()
        self.current_color = QColor(255, 255, 255)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. FR: En-tête / EN: Header
        lbl_title = QLabel(self.res_mgr.get_string("ytImageMetadata::Text", "Ajouter du texte"))
        lbl_title.setObjectName("SubpanelTitle")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel("Saisissez votre texte ci-dessous puis déplacez-le sur la photo à l'aide de la souris.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("SubpanelDesc")
        layout.addWidget(lbl_desc)

        # 2. FR: Champ de saisie / EN: Text input field
        self.txt_input = QLineEdit()
        self.txt_input.setObjectName("SubpanelLineEdit")
        self.txt_input.setPlaceholderText(self.res_mgr.get_string("EditText::GhostText", "Cliquez pour ajouter du texte..."))
        self.txt_input.textChanged.connect(self._emit_params)
        layout.addWidget(self.txt_input)

        # 3. FR: Taille de police / EN: Font size
        size_box = QVBoxLayout()
        size_box.setSpacing(4)
        h_size = QHBoxLayout()
        lbl_size = QLabel("Taille de police :")
        lbl_size.setStyleSheet("font-size: 11px;")
        self.lbl_size_val = QLabel("28 pt")
        self.lbl_size_val.setObjectName("SubpanelValue")
        h_size.addWidget(lbl_size)
        h_size.addStretch()
        h_size.addWidget(self.lbl_size_val)
        size_box.addLayout(h_size)

        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(12, 96)
        self.slider_size.setValue(28)
        self.slider_size.valueChanged.connect(self._on_size_changed)
        size_box.addWidget(self.slider_size)
        layout.addLayout(size_box)

        # 4. FR: Couleur et Ombre / EN: Color and Shadow (Ref: editpanel/edittextshadow)
        h_opts = QHBoxLayout()
        self.btn_color = QPushButton("■ Couleur")
        self.btn_color.setStyleSheet("background-color: #FFFFFF; color: #000000; font-weight: bold; border: 1px solid #999; padding: 4px 8px; border-radius: 3px;")
        self.btn_color.clicked.connect(self._pick_color)
        h_opts.addWidget(self.btn_color)

        self.chk_shadow = QCheckBox("Ombre")
        self.chk_shadow.setChecked(True)
        self.chk_shadow.stateChanged.connect(self._emit_params)
        h_opts.addWidget(self.chk_shadow)
        layout.addLayout(h_opts)

        layout.addStretch(1)

        # 5. FR: Boutons d'action / EN: Action buttons
        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_apply = QPushButton(self.res_mgr.get_string("editpanel/cropapply", "Appliquer"))
        self.btn_apply.setObjectName("ApplyTextBtn")
        self.btn_apply.setStyleSheet("""
            QPushButton#ApplyTextBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #2859A3;
            }
            QPushButton#ApplyTextBtn:hover {
                background-color: #4A8BF0;
            }
        """)
        self.btn_apply.clicked.connect(self.apply_clicked.emit)
        btns_layout.addWidget(self.btn_apply)

        self.btn_cancel = QPushButton(self.res_mgr.get_string("editpanel/cropcancel", "Annuler"))
        self.btn_cancel.setObjectName("SmallActionBtn")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        btns_layout.addWidget(self.btn_cancel)

        layout.addLayout(btns_layout)

    def _on_size_changed(self, val: int) -> None:
        """
        FR: Met à jour l'étiquette de taille de police et émet les nouveaux paramètres de texte.
        EN: Updates the font size label and emits the new text parameters.
        """
        self.lbl_size_val.setText(f"{val} pt")
        self._emit_params()

    def _pick_color(self) -> None:
        """
        FR: Ouvre un sélecteur de couleur pour choisir la couleur du texte.
        EN: Opens a color picker dialog to choose the text color.
        """
        col = QColorDialog.getColor(self.current_color, self, "Choisir une couleur de texte")
        if col.isValid():
            self.current_color = col
            txt_col = "#000000" if (col.red() * 0.299 + col.green() * 0.587 + col.blue() * 0.114) > 150 else "#FFFFFF"
            self.btn_color.setStyleSheet(f"background-color: {col.name()}; color: {txt_col}; font-weight: bold; border: 1px solid #666; padding: 4px 8px; border-radius: 3px;")
            self._emit_params()

    def _emit_params(self) -> None:
        """
        FR: Émet le signal `params_changed` avec le texte, la taille, la couleur et l'option d'ombre.
        EN: Emits the `params_changed` signal with text, font size, color, and shadow option.
        """
        self.params_changed.emit(
            self.txt_input.text(),
            self.slider_size.value(),
            self.current_color,
            self.chk_shadow.isChecked()
        )

    def reset_text(self) -> None:
        """
        FR: Réinitialise le champ de texte et ses options aux valeurs par défaut.
        EN: Resets the text input field and its options to their default values.
        """
        self.txt_input.clear()
        self.slider_size.setValue(28)
        self.current_color = QColor(255, 255, 255)
        self.btn_color.setStyleSheet("background-color: #FFFFFF; color: #000000; font-weight: bold; border: 1px solid #999; padding: 4px 8px; border-radius: 3px;")
        self.chk_shadow.setChecked(True)


class PicasaRedEyeSubpanel(QWidget):
    """
    FR: Sous-panneau officiel d'atténuation des yeux rouges.
    EN: Official red-eye reduction subpanel.
    Ref: picasa3.exe @ filterdesc: redeye, eMenuPicture::ID_PICTURE_AUTO_REDEYE
    """
    apply_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le sous-panneau de correction des yeux rouges.
        EN: Initializes the red-eye reduction subpanel.
        """
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        lbl_title = QLabel("Yeux rouges")
        lbl_title.setObjectName("SubpanelTitle")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Picasa atténue automatiquement les reflets rouges des yeux sur les visages détectés, "
            "ou appliquez la correction directement sur l'image."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("SubpanelDesc")
        layout.addWidget(lbl_desc)

        layout.addStretch(1)

        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_apply = QPushButton(self.res_mgr.get_string("editpanel/cropapply", "Appliquer"))
        self.btn_apply.setObjectName("ApplyRedEyeBtn")
        self.btn_apply.setStyleSheet("""
            QPushButton#ApplyRedEyeBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #2859A3;
            }
            QPushButton#ApplyRedEyeBtn:hover {
                background-color: #4A8BF0;
            }
        """)
        self.btn_apply.clicked.connect(self.apply_clicked.emit)
        btns_layout.addWidget(self.btn_apply)

        self.btn_cancel = QPushButton(self.res_mgr.get_string("editpanel/cropcancel", "Annuler"))
        self.btn_cancel.setObjectName("SmallActionBtn")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        btns_layout.addWidget(self.btn_cancel)

        layout.addLayout(btns_layout)


class PicasaRetouchSubpanel(QWidget):
    """
    FR: Sous-panneau officiel de retouche des imperfections (tampon de lissage local).
    EN: Official blemish retouching subpanel (local healing brush/stamp).
    Ref: picasa3.exe @ filterdesc: retouch, 0x0088C3EC
    """
    apply_clicked = Signal(float)  # radius
    cancel_clicked = Signal()
    radius_changed = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le sous-panneau de retouche et son curseur de rayon de pinceau.
        EN: Initializes the retouch subpanel and its brush radius slider.
        """
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        lbl_title = QLabel("Retoucher")
        lbl_title.setObjectName("SubpanelTitle")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Corrigez les imperfections et poussières en appliquant un lissage local "
            "adapté à la texture de la photo."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("SubpanelDesc")
        layout.addWidget(lbl_desc)

        lbl_size = QLabel("Taille du pinceau :")
        layout.addWidget(lbl_size)
        self.slider_radius = QSlider(Qt.Orientation.Horizontal)
        self.slider_radius.setRange(5, 50)
        self.slider_radius.setValue(20)
        self.slider_radius.valueChanged.connect(lambda v: self.radius_changed.emit(v / 500.0))
        layout.addWidget(self.slider_radius)

        layout.addStretch(1)

        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_apply = QPushButton(self.res_mgr.get_string("editpanel/cropapply", "Appliquer"))
        self.btn_apply.setObjectName("ApplyRetouchBtn")
        self.btn_apply.setStyleSheet("""
            QPushButton#ApplyRetouchBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #2859A3;
            }
            QPushButton#ApplyRetouchBtn:hover {
                background-color: #4A8BF0;
            }
        """)
        self.btn_apply.clicked.connect(lambda: self.apply_clicked.emit(self.slider_radius.value() / 500.0))
        btns_layout.addWidget(self.btn_apply)

        self.btn_cancel = QPushButton(self.res_mgr.get_string("editpanel/cropcancel", "Annuler"))
        self.btn_cancel.setObjectName("SmallActionBtn")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        btns_layout.addWidget(self.btn_cancel)

        layout.addLayout(btns_layout)


# =============================================================================
# SPÉCIFICATIONS DES CURSEURS ET PARAMÈTRES DE FILTRES (Ref: filterdesc.xml)
# FR : Définit pour chaque filtre à mode="effect" ses curseurs et sélecteurs de couleur exacts.
# EN : Defines for each mode="effect" filter its exact sliders and color pickers from filterdesc.xml.
# =============================================================================

ONECLICK_EFFECTS = {
    "autocontrast",
    "lucky",
    "autocolor",
    "bw",
    "sepia",
    "warmify",
    "invert",
}

# FR: Filtres exigeant un zoom ajusté à la fenêtre (<zoom forcefit="1"/> dans filterdesc.xml, Ref: 0x005F8730)
# EN: Filters requiring zoom-to-fit on activation (<zoom forcefit="1"/> in filterdesc.xml, Ref: 0x005F8730)
FORCEFIT_EFFECTS = {
    "straighten",
    "soft_focus",
    "focal_bw",
    "graduated_tint",
}

FILTER_SPECS: dict[str, dict] = {
    # --- Tab 3 : Effets 1 (Ref: filterdesc.xml @ unsharp2, grain, tint, sat, radblur, glow2, radsat, dir_tint, ansel) ---
    "sharpen": {
        "title": "🔍 Netteté",
        "title_id": "FilterName_unsharp2",
        "desc": "Ajustez le curseur pour renforcer le piqué et la netteté des contours, puis cliquez sur Appliquer.",
        "sliders": [
            {"key": "amount", "label": "Quantité", "min": 5, "max": 100, "default": 50, "scale": 100.0, "unit": "%"},
        ],
    },
    "grain": {
        "title": "🎞️ Grain photo",
        "title_id": "FilterName_PicnikGrain",
        "desc": "Ajustez l'intensité et l'atténuation du grain argentique.",
        "sliders": [
            {"key": "intensity", "label": "Grain", "min": 2, "max": 50, "default": 18, "scale": 1.0, "unit": ""},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "tint": {
        "title": "🎨 Teinte",
        "title_id": "FilterName_PicnikTint",
        "desc": "Choisissez la couleur de virage et ajustez la préservation de la teinte.",
        "colors": [
            {"key": "color", "label": "Couleur de teinte", "default": (220, 190, 150)},
        ],
        "sliders": [
            {"key": "intensity", "label": "Intensité", "min": 0, "max": 100, "default": 40, "scale": 100.0, "unit": "%"},
        ],
    },
    "saturation": {
        "title": "🧪 Saturation",
        "title_id": "FilterName_sat",
        "desc": "Déplacez le curseur pour désaturer (gauche) ou intensifier les couleurs (droite).",
        "sliders": [
            {"key": "factor", "label": "Quantité", "min": 0, "max": 250, "default": 140, "scale": 100.0, "unit": "%"},
        ],
    },
    "soft_focus": {
        "title": "🌫️ Flou artistique",
        "title_id": "FilterName_radblur",
        "desc": "Réglez la taille de la zone centrale nette et la quantité de flou périphérique.",
        "sliders": [
            {"key": "size", "label": "Taille", "min": 5, "max": 85, "default": 35, "scale": 100.0, "unit": "%"},
            {"key": "amount", "label": "Quantité", "min": 5, "max": 100, "default": 40, "scale": 100.0, "unit": "%"},
        ],
    },
    "glow": {
        "title": "✨ Halo",
        "title_id": "FilterName_glow2",
        "desc": "Ajustez l'intensité lumineuse et le rayon de diffusion du halo.",
        "sliders": [
            {"key": "intensity", "label": "Intensité", "min": 5, "max": 100, "default": 45, "scale": 100.0, "unit": "%"},
            {"key": "radius", "label": "Rayon", "min": 2, "max": 25, "default": 8, "scale": 1.0, "unit": " px"},
        ],
    },
    "focal_bw": {
        "title": "🎯 N&B focalisé",
        "title_id": "FilterName_radsat",
        "desc": "Ajustez la taille et la netteté de la zone centrale conservée en couleur.",
        "sliders": [
            {"key": "size", "label": "Taille", "min": 5, "max": 85, "default": 35, "scale": 100.0, "unit": "%"},
            {"key": "sharpness", "label": "Netteté", "min": 5, "max": 95, "default": 40, "scale": 100.0, "unit": "%"},
        ],
    },
    "graduated_tint": {
        "title": "🌅 Teinte dégradée",
        "title_id": "FilterName_dir_tint",
        "desc": "Choisissez la couleur du filtre dégradé, son estompage et son intensité.",
        "colors": [
            {"key": "color", "label": "Couleur du filtre", "default": (255, 140, 50)},
        ],
        "sliders": [
            {"key": "feather", "label": "Estomper", "min": 10, "max": 100, "default": 50, "scale": 100.0, "unit": "%"},
            {"key": "shade", "label": "Ombre / Intensité", "min": 5, "max": 100, "default": 50, "scale": 100.0, "unit": "%"},
        ],
    },
    "filtered_bw": {
        "title": "⬛ N&B filtré",
        "title_id": "FilterName_ansel",
        "desc": "Sélectionnez la couleur du filtre optique simulé pour la conversion Noir & Blanc.",
        "colors": [
            {"key": "color", "label": "Couleur du filtre optique", "default": (255, 85, 85)},
        ],
        "sliders": [],
    },
    # --- Tab 4 : Effets 2 (Ref: filterdesc.xml @ HDR, Orton, Lomo, Sixties, CrossProcess, IR, Holga, Cinemascope, NightVision, HeatMap, Polaroid, QuantizePalette) ---
    "hdr": {
        "title": "🌌 Simul. HDR",
        "title_id": "FilterName_HDR",
        "desc": "Ajustez le rayon, l'intensité et l'atténuation du simulateur HDR.",
        "sliders": [
            {"key": "radius", "label": "Rayon", "min": 1, "max": 50, "default": 20, "scale": 1.0, "unit": ""},
            {"key": "strength", "label": "Intensité", "min": 0, "max": 60, "default": 30, "scale": 10.0, "unit": ""},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "orton": {
        "title": "📷 Effet Orton",
        "title_id": "FilterName_Orton",
        "desc": "Réglez le flou lumineux (Bloom), la luminosité et l'atténuation de l'effet Orton.",
        "sliders": [
            {"key": "bloom", "label": "Flou lumineux", "min": 0, "max": 50, "default": 25, "scale": 1.0, "unit": ""},
            {"key": "brightness", "label": "Luminosité", "min": 0, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "lomo": {
        "title": "📸 Lomo",
        "title_id": "FilterName_Lomo",
        "desc": "Ajustez le flou périphérique et l'atténuation de l'effet lomographique.",
        "sliders": [
            {"key": "blur", "label": "Flou", "min": 0, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "sixties": {
        "title": "📻 Années 60",
        "title_id": "FilterName_Sixties",
        "desc": "Ajustez l'atténuation du virage rétro Années 60.",
        "sliders": [
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 20, "scale": 1.0, "unit": "%"},
        ],
    },
    "cross_process": {
        "title": "🔀 Trait. croisé",
        "title_id": "FilterName_CrossProcess",
        "desc": "Ajustez l'atténuation du traitement croisé argentique.",
        "sliders": [
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "infrared": {
        "title": "🔮 Infrarouge",
        "title_id": "FilterName_IR",
        "desc": "Ajustez l'atténuation du film infrarouge.",
        "sliders": [
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "holga": {
        "title": "🎞️ Holga",
        "title_id": "FilterName_Holga",
        "desc": "Ajustez le flou optique, le grain et l'atténuation de l'appareil Holga.",
        "sliders": [
            {"key": "blur", "label": "Flou", "min": 0, "max": 100, "default": 70, "scale": 1.0, "unit": "%"},
            {"key": "grain", "label": "Grain", "min": 0, "max": 100, "default": 30, "scale": 1.0, "unit": "%"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "cinemascope": {
        "title": "🎬 Cinémascope",
        "title_id": "FilterName_Cinemascope",
        "desc": "Ajustez l'intensité des couleurs et l'atténuation du rendu Cinémascope.",
        "sliders": [
            {"key": "color_boost", "label": "Intensité couleur", "min": -50, "max": 50, "default": 0, "scale": 1.0, "unit": "%"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "night_vision": {
        "title": "🌙 Vision nuit",
        "title_id": "FilterName_NightVision",
        "desc": "Choisissez la couleur phosphorescente et réglez le grain et l'atténuation.",
        "colors": [
            {"key": "color", "label": "Couleur phosphore", "default": (87, 204, 41)},
        ],
        "sliders": [
            {"key": "grain", "label": "Grain", "min": 0, "max": 100, "default": 20, "scale": 1.0, "unit": "%"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "heat_map": {
        "title": "🌡️ Thermique",
        "title_id": "FilterName_HeatMap",
        "desc": "Ajustez le décalage de teinte du spectre thermique et l'atténuation.",
        "sliders": [
            {"key": "shift", "label": "Décalage teinte", "min": 0, "max": 360, "default": 0, "scale": 1.0, "unit": "°"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "polaroid": {
        "title": "🖼️ Polaroid",
        "title_id": "FilterName_Polaroid",
        "desc": "Ajustez l'angle d'inclinaison du cadre Polaroid.",
        "sliders": [
            {"key": "angle", "label": "Rotation", "min": -30, "max": 30, "default": 5, "scale": 1.0, "unit": "°"},
        ],
    },
    "quantize_palette": {
        "title": "🎨 Postériser",
        "title_id": "FilterName_QuantizePalette",
        "desc": "Ajustez le nombre de niveaux de couleurs (palette quantifiée).",
        "sliders": [
            {"key": "steps", "label": "Nombre de couleurs", "min": 2, "max": 30, "default": 8, "scale": 1.0, "unit": ""},
        ],
    },
    # --- Tab 5 : Effets 3 (Ref: filterdesc.xml @ Boost, Vignette, TwoTone, Pixelate, PicnikFocalPixelate, FocalZoom, Soften, Comicize, Neon, PencilSketch, Border, MuseumMatte, DropShadow, RoundedEdges, LocalContrast) ---
    "boost": {
        "title": "🚀 Boost",
        "title_id": "FilterName_Boost",
        "desc": "Ajustez l'impact d'amplification dynamique des couleurs et du contraste.",
        "sliders": [
            {"key": "impact", "label": "Impact", "min": 0, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
        ],
    },
    "vignette": {
        "title": "🔲 Vignettage",
        "title_id": "FilterName_Vignette",
        "desc": "Choisissez la couleur de vignettage, sa taille et son intensité.",
        "colors": [
            {"key": "color", "label": "Couleur du vignettage", "default": (0, 0, 0)},
        ],
        "sliders": [
            {"key": "size", "label": "Taille", "min": 0, "max": 60, "default": 25, "scale": 100.0, "unit": "%"},
            {"key": "amount", "label": "Intensité", "min": 0, "max": 100, "default": 50, "scale": 100.0, "unit": "%"},
        ],
    },
    "two_tone": {
        "title": "🎭 Bichromie",
        "title_id": "FilterName_TwoTone",
        "desc": "Choisissez les couleurs d'ombres et de hautes lumières et ajustez le contraste.",
        "colors": [
            {"key": "shadow_color", "label": "Couleur des ombres", "default": (0, 68, 136)},
            {"key": "highlight_color", "label": "Couleur des lumières", "default": (255, 255, 0)},
        ],
        "sliders": [
            {"key": "brightness", "label": "Luminosité", "min": -100, "max": 100, "default": 0, "scale": 1.0, "unit": ""},
            {"key": "contrast", "label": "Contraste", "min": -100, "max": 100, "default": 0, "scale": 1.0, "unit": ""},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "pixelate": {
        "title": "🧱 Pixelliser",
        "title_id": "FilterName_Pixelate",
        "desc": "Ajustez la taille des blocs de mosaïque et l'atténuation.",
        "sliders": [
            {"key": "block_size", "label": "Taille des pixels", "min": 2, "max": 60, "default": 14, "scale": 1.0, "unit": " px"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "focal_pixelate": {
        "title": "🎯 Pix. focale",
        "title_id": "FilterName_PicnikFocalPixelate",
        "desc": "Ajustez la taille des pixels, le rayon de la zone centrale nette et la dureté du bord.",
        "sliders": [
            {"key": "block_size", "label": "Taille des pixels", "min": 2, "max": 60, "default": 15, "scale": 1.0, "unit": " px"},
            {"key": "size", "label": "Taille focale", "min": 5, "max": 85, "default": 35, "scale": 100.0, "unit": "%"},
            {"key": "hardness", "label": "Netteté du bord", "min": 0, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
        ],
    },
    "focal_zoom": {
        "title": "🌀 Zoom focal",
        "title_id": "FilterName_FocalZoom",
        "desc": "Ajustez la vitesse de zoom radial, la taille du centre net et la dureté.",
        "sliders": [
            {"key": "zoom_amount", "label": "Zoom", "min": 1, "max": 100, "default": 30, "scale": 1.0, "unit": "%"},
            {"key": "size", "label": "Taille focale", "min": 5, "max": 85, "default": 25, "scale": 100.0, "unit": "%"},
            {"key": "hardness", "label": "Netteté du bord", "min": 0, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
        ],
    },
    "soften": {
        "title": "🌸 Adoucir",
        "title_id": "FilterName_Soften",
        "desc": "Ajustez la douceur du flou portrait et l'atténuation.",
        "sliders": [
            {"key": "impact", "label": "Douceur", "min": 1, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
        ],
    },
    "comic": {
        "title": "💥 BD Comics",
        "title_id": "FilterName_Comicize",
        "desc": "Ajustez la finesse des aplats de couleur et la force de l'encrage.",
        "sliders": [
            {"key": "radius", "label": "Rayon", "min": 0, "max": 100, "default": 40, "scale": 1.0, "unit": ""},
            {"key": "strength", "label": "Intensité encrage", "min": 0, "max": 100, "default": 75, "scale": 1.0, "unit": "%"},
        ],
    },
    "neon": {
        "title": "⚡ Néon",
        "title_id": "FilterName_Neon",
        "desc": "Choisissez la couleur du tube néon et ajustez l'atténuation.",
        "colors": [
            {"key": "color", "label": "Couleur du néon", "default": (255, 0, 0)},
        ],
        "sliders": [
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "pencil_sketch": {
        "title": "✏️ Crayon",
        "title_id": "FilterName_PencilSketch",
        "desc": "Ajustez l'épaisseur du trait de crayon et le contraste du croquis.",
        "sliders": [
            {"key": "radius", "label": "Épaisseur du trait", "min": 1, "max": 20, "default": 2, "scale": 1.0, "unit": ""},
            {"key": "contrast", "label": "Contraste", "min": 20, "max": 120, "default": 100, "scale": 1.0, "unit": ""},
        ],
    },
    "border": {
        "title": "🖼️ Bordure",
        "title_id": "FilterName_Border",
        "desc": "Personnalisez les couleurs et l'épaisseur de la bordure extérieure et intérieure.",
        "colors": [
            {"key": "outer_color", "label": "Couleur extérieure", "default": (26, 26, 26)},
            {"key": "inner_color", "label": "Couleur intérieure", "default": (255, 255, 255)},
        ],
        "sliders": [
            {"key": "outer_thickness", "label": "Épaisseur extérieure", "min": 1, "max": 50, "default": 15, "scale": 1.0, "unit": "%"},
            {"key": "inner_thickness", "label": "Épaisseur intérieure", "min": 0, "max": 30, "default": 3, "scale": 1.0, "unit": "%"},
            {"key": "corner_radius", "label": "Rayon des coins", "min": 0, "max": 50, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
    "museum_matte": {
        "title": "🏛️ Cadre musée",
        "title_id": "FilterName_MuseumMatte",
        "desc": "Ajustez l'épaisseur et les couleurs du passe-partout et du cadre de galerie.",
        "colors": [
            {"key": "inner_color", "label": "Couleur du passe-partout", "default": (240, 234, 228)},
            {"key": "outer_color", "label": "Couleur du cadre", "default": (26, 14, 3)},
        ],
        "sliders": [
            {"key": "inner_thickness", "label": "Épaisseur passe-partout", "min": 0, "max": 50, "default": 12, "scale": 1.0, "unit": "%"},
            {"key": "outer_thickness", "label": "Épaisseur du cadre", "min": 0, "max": 50, "default": 7, "scale": 1.0, "unit": "%"},
        ],
    },
    "drop_shadow": {
        "title": "☁️ Ombre portée",
        "title_id": "FilterName_DropShadow",
        "desc": "Ajustez la distance, l'angle, le flou et la couleur d'arrière-plan de l'ombre portée.",
        "colors": [
            {"key": "bg_color", "label": "Couleur d'arrière-plan", "default": (255, 255, 255)},
        ],
        "sliders": [
            {"key": "distance", "label": "Distance", "min": 0, "max": 40, "default": 6, "scale": 1.0, "unit": " px"},
            {"key": "angle", "label": "Angle", "min": 0, "max": 360, "default": 45, "scale": 1.0, "unit": "°"},
            {"key": "blur", "label": "Flou", "min": 1, "max": 30, "default": 8, "scale": 1.0, "unit": " px"},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 50, "scale": 1.0, "unit": "%"},
        ],
    },
    "rounded_edges": {
        "title": "⬜ Coins arrondis",
        "title_id": "FilterName_RoundedEdges",
        "desc": "Ajustez le rayon d'arrondi des angles et la couleur extérieure.",
        "colors": [
            {"key": "outer_color", "label": "Couleur extérieure", "default": (255, 255, 255)},
        ],
        "sliders": [
            {"key": "corner_radius", "label": "Rayon des coins", "min": 1, "max": 50, "default": 10, "scale": 1.0, "unit": "%"},
        ],
    },
    "local_contrast": {
        "title": "🔆 Contraste loc.",
        "title_id": "FilterName_LocalContrast",
        "desc": "Ajustez le rayon et l'intensité de renforcement des micro-détails.",
        "sliders": [
            {"key": "radius", "label": "Rayon", "min": 1, "max": 50, "default": 15, "scale": 1.0, "unit": ""},
            {"key": "strength", "label": "Intensité", "min": 0, "max": 30, "default": 15, "scale": 10.0, "unit": ""},
            {"key": "fade", "label": "Atténuer", "min": 0, "max": 100, "default": 0, "scale": 1.0, "unit": "%"},
        ],
    },
}


class PicasaEffectTileButton(QPushButton):
    """
    FR: Tuile de filtre dans la grille `editpanel/fxthumbs` (`editpanel/fx1`..`editpanel/fx12`)
        affichant une miniature carrée de la photo ouverte avec l'effet appliqué au-dessus du libellé
        (`editpanel/fx1_label`..`editpanel/fx12_label`).
    EN: Filter tile in the `editpanel/fxthumbs` grid (`editpanel/fx1`..`editpanel/fx12`)
        displaying a square thumbnail of the opened photo with the effect applied above the label
        (`editpanel/fx1_label`..`editpanel/fx12_label`).

    Ref: picasa3.exe @ 0x00568A08..0x00568F45 (FUN_00568A08), 0x005D7C60..0x005D8274,
         editpanel/fxthumbs (0x00C902B8), editpanel/fx%d (0x00C8ECA4), editpanel/fx%d_label (0x00C8ECAC)
    """

    def __init__(self, label: str, action_id: str, tooltip: str = "", parent: Optional[QWidget] = None):
        """
        FR: Initialise la tuile d'effet avec son libellé, son identifiant d'action et sa miniature d'aperçu.
        EN: Initializes the effect tile with its label, action ID, and preview thumbnail.
        """
        super().__init__(label, parent)
        self.action_id: str = action_id
        self.preview_pixmap: Optional[QPixmap] = None
        self._hovered: bool = False
        self.setObjectName("EffectTileBtn")
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(78, 74)
        self.setFixedHeight(76)

    def set_preview_pixmap(self, pix: Optional[QPixmap]) -> None:
        """
        FR: Définit la miniature d'aperçu de l'effet et rafraîchit le rendu de la tuile.
        EN: Sets the effect preview thumbnail pixmap and refreshes the tile rendering.
        """
        self.preview_pixmap = pix
        self.update()

    def enterEvent(self, event: Any) -> None:
        """
        FR: Active l'état de survol visuel de la tuile d'effet.
        EN: Enables the visual hover state of the effect tile.
        """
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        """
        FR: Désactive l'état de survol visuel de la tuile d'effet.
        EN: Disables the visual hover state of the effect tile.
        """
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: Any) -> None:
        """
        FR: Dessine la miniature `editpanel/fx%d` en haut et le libellé `editpanel/fx%d_label` en bas.
        EN: Draws the `editpanel/fx%d` thumbnail at the top and the `editpanel/fx%d_label` at the bottom.
        Ref: picasa3.exe @ 0x00568A08 (FUN_00568A08)
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        style = PicasaStyle.instance()
        w, h = float(self.width()), float(self.height())
        rect = QRectF(1.0, 1.0, w - 2.0, h - 2.0)

        bg_col = style.topbar_btn_bg_end if self._hovered else style.topbar_btn_bg_start
        border_col = style.accent_color if self._hovered else style.topbar_btn_border
        painter.setPen(QPen(border_col, 1.2 if self._hovered else 1.0))
        painter.setBrush(bg_col)
        painter.drawRoundedRect(rect, 4.0, 4.0)

        thumb_size = 46.0
        tx = (w - thumb_size) / 2.0
        ty = 4.0
        thumb_rect = QRectF(tx, ty, thumb_size, thumb_size)

        if self.preview_pixmap is not None and not self.preview_pixmap.isNull():
            painter.save()
            painter.fillRect(thumb_rect.adjusted(-1, -1, 1, 1), QColor(20, 22, 26, 180))
            painter.drawPixmap(thumb_rect.toRect(), self.preview_pixmap)
            painter.setPen(QPen(QColor(255, 255, 255, 70), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(thumb_rect)
            painter.restore()
        else:
            painter.fillRect(thumb_rect, QColor(40, 44, 52, 90))
            painter.setPen(QPen(border_col, 1.0))
            painter.drawRect(thumb_rect)

        # Libellé sous la miniature (sans l'emoji de tête s'il y a une miniature pour gagner de la place)
        raw_text = self.text()
        parts = raw_text.split(" ", 1)
        clean_label = parts[1] if len(parts) == 2 and not parts[0].isalnum() else raw_text

        lbl_rect = QRectF(2.0, ty + thumb_size + 2.0, w - 4.0, h - (ty + thumb_size + 4.0))
        painter.setPen(style.alist_textcolor)
        font = QFont("Tahoma", 8, QFont.Weight.Bold if self._hovered else QFont.Weight.Normal)
        painter.setFont(font)
        fm = painter.fontMetrics()
        elided = fm.elidedText(clean_label, Qt.TextElideMode.ElideRight, int(lbl_rect.width()))
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, elided)
        painter.end()


class PicasaEffectSubpanel(QWidget):
    """
    FR: Sous-panneau générique d'ajustement des filtres paramétrables (`mode="effect"` dans `filterdesc.xml`).
        Construit dynamiquement les curseurs et sélecteurs de couleur du filtre actif, émet un aperçu
        en direct à chaque déplacement de curseur, et ne valide l'effet que sur clic sur « Appliquer »
        (ou restaure l'image de base sur clic sur « Annuler »).
    EN: Generic adjustment subpanel for parameterized filters (`mode="effect"` in `filterdesc.xml`).
        Dynamically builds the sliders and color pickers for the active filter, emits a live preview
        on every slider move, and only commits the effect on clicking "Apply" (or reverts to the
        base image on clicking "Cancel").

    Ref: picasa3.exe @ filterdesc.xml (mode="effect", <sliders>, <HSlider*>, <colorwheel>)
    Ref: TOOLTIPS_FR.XML @ editpanel/ok ("Appliquer"), editpanel/cancel ("Annuler")
    """
    preview_changed = Signal(str, dict)  # (effect_name, params)
    apply_clicked = Signal(str, dict)    # (effect_name, params)
    cancel_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le sous-panneau générique d'ajustement des effets paramétrables.
        EN: Initializes the generic adjustment subpanel for parameterized effects.
        """
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()
        self.effect_name: str = ""
        self._sliders: dict[str, tuple[QSlider, float, QLabel, str]] = {}
        self._colors: dict[str, tuple[int, int, int]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.lbl_title = QLabel("Effet")
        self.lbl_title.setObjectName("SubpanelTitle")
        layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setObjectName("SubpanelDesc")
        layout.addWidget(self.lbl_desc)

        self.controls_container = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_container)
        self.controls_layout.setContentsMargins(0, 4, 0, 4)
        self.controls_layout.setSpacing(10)
        layout.addWidget(self.controls_container)

        layout.addStretch(1)

        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_apply = QPushButton(self.res_mgr.get_string("editpanel/ok", "Appliquer"))
        self.btn_apply.setObjectName("ApplyEffectBtn")
        self.btn_apply.setStyleSheet("""
            QPushButton#ApplyEffectBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #2859A3;
            }
            QPushButton#ApplyEffectBtn:hover {
                background-color: #4A8BF0;
            }
        """)
        self.btn_apply.clicked.connect(self._on_apply)
        btns_layout.addWidget(self.btn_apply)

        self.btn_cancel = QPushButton(self.res_mgr.get_string("editpanel/cancel", "Annuler"))
        self.btn_cancel.setObjectName("SmallActionBtn")
        self.btn_cancel.clicked.connect(self.cancel_clicked.emit)
        btns_layout.addWidget(self.btn_cancel)

        layout.addLayout(btns_layout)

    def configure_effect(self, effect_name: str, spec: dict) -> None:
        """
        FR: Configure les curseurs et boutons de couleur pour le filtre `effect_name`.
        EN: Configures sliders and color buttons for the `effect_name` filter.
        """
        self.effect_name = effect_name
        self._sliders.clear()
        self._colors.clear()

        while self.controls_layout.count():
            item = self.controls_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                sub = item.layout()
                while sub.count():
                    si = sub.takeAt(0)
                    if si.widget():
                        si.widget().deleteLater()

        self.lbl_title.setText(spec.get("title", effect_name))
        self.lbl_desc.setText(spec.get("desc", ""))

        # 1. FR: Sélecteurs de couleur éventuels / EN: Optional color pickers (<colorwheel> / <colorpicker> in filterdesc.xml)
        for cspec in spec.get("colors", []):
            ckey = cspec["key"]
            clabel = cspec.get("label", "Couleur")
            cdef = tuple(cspec.get("default", (255, 255, 255)))
            self._colors[ckey] = cdef

            row = QHBoxLayout()
            lbl = QLabel(f"{clabel} :")
            row.addWidget(lbl)
            row.addStretch(1)

            btn_col = QPushButton("■ Choisir")
            self._style_color_btn(btn_col, cdef)
            btn_col.clicked.connect(lambda _, k=ckey, b=btn_col: self._pick_color(k, b))
            row.addWidget(btn_col)
            self.controls_layout.addLayout(row)

        # 2. FR: Curseurs / EN: Sliders (<sliders> / <HSlider*> in filterdesc.xml)
        for sspec in spec.get("sliders", []):
            skey = sspec["key"]
            slabel = sspec.get("label", skey)
            smin = int(sspec.get("min", 0))
            smax = int(sspec.get("max", 100))
            sdef = int(sspec.get("default", 0))
            scale = float(sspec.get("scale", 1.0))
            unit = str(sspec.get("unit", ""))

            box = QVBoxLayout()
            box.setSpacing(3)
            hdr = QHBoxLayout()
            lbl = QLabel(f"{slabel} :")
            val_lbl = QLabel(self._format_val(sdef, scale, unit))
            val_lbl.setObjectName("SubpanelValue")
            btn_rst = QPushButton("↺")
            btn_rst.setObjectName("HistModeBtn")
            btn_rst.setFixedSize(20, 18)
            btn_rst.setToolTip(f"Réinitialiser ({self._format_val(sdef, scale, unit)})")

            hdr.addWidget(lbl)
            hdr.addStretch(1)
            hdr.addWidget(val_lbl)
            hdr.addWidget(btn_rst)
            box.addLayout(hdr)

            sldr = QSlider(Qt.Orientation.Horizontal)
            sldr.setRange(smin, smax)
            sldr.setValue(sdef)
            self._sliders[skey] = (sldr, scale, val_lbl, unit)

            sldr.valueChanged.connect(lambda _v, k=skey: self._on_slider_changed(k))
            btn_rst.clicked.connect(lambda _, s=sldr, d=sdef: s.setValue(d))
            box.addWidget(sldr)
            self.controls_layout.addLayout(box)

    @staticmethod
    def _format_val(raw_val: int, scale: float, unit: str) -> str:
        """
        FR: Formate la valeur numérique d'un curseur avec son facteur d'échelle et son unité.
        EN: Formats a slider's numeric value with its scale factor and unit.
        """
        if scale == 10.0:
            return f"{raw_val / 10.0:.1f}{unit}"
        return f"{raw_val}{unit}"

    @staticmethod
    def _style_color_btn(btn: QPushButton, rgb: tuple[int, int, int]) -> None:
        """
        FR: Applique la couleur d'arrière-plan et un texte contrasté au bouton de sélection de couleur.
        EN: Applies the background color and contrasting text color to the color picker button.
        """
        r, g, b = rgb
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        fg = "#000000" if luma > 145 else "#FFFFFF"
        btn.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); color: {fg}; font-weight: bold; "
            f"border: 1px solid #777; padding: 3px 10px; border-radius: 3px;"
        )

    def _pick_color(self, key: str, btn: QPushButton) -> None:
        """
        FR: Ouvre un dialogue de choix de couleur pour le paramètre `key` et émet l'aperçu en direct.
        EN: Opens a color picker dialog for parameter `key` and emits the live preview.
        """
        cur = self._colors.get(key, (255, 255, 255))
        col = QColorDialog.getColor(QColor(*cur), self, "Choisir une couleur")
        if col.isValid():
            rgb = (col.red(), col.green(), col.blue())
            self._colors[key] = rgb
            self._style_color_btn(btn, rgb)
            self.preview_changed.emit(self.effect_name, self.get_params())

    def _on_slider_changed(self, key: str) -> None:
        """
        FR: Met à jour l'étiquette du curseur `key` et émet le signal d'aperçu en direct.
        EN: Updates the label for slider `key` and emits the live preview signal.
        """
        if key in self._sliders:
            sldr, scale, val_lbl, unit = self._sliders[key]
            val_lbl.setText(self._format_val(sldr.value(), scale, unit))
        self.preview_changed.emit(self.effect_name, self.get_params())

    def get_params(self) -> dict:
        """
        FR: Collecte et retourne le dictionnaire des paramètres courants (couleurs et curseurs).
        EN: Collects and returns the dictionary of current parameters (colors and sliders).
        """
        params: dict = {}
        for k, rgb in self._colors.items():
            params[k] = rgb
        for k, (sldr, scale, _lbl, _u) in self._sliders.items():
            params[k] = float(sldr.value()) / scale
        return params

    def _on_apply(self) -> None:
        """
        FR: Émet le signal `apply_clicked` avec le nom de l'effet et ses paramètres courants.
        EN: Emits the `apply_clicked` signal with the effect name and its current parameters.
        """
        self.apply_clicked.emit(self.effect_name, self.get_params())


class PicasaEditPanel(QWidget):
    """
    FR: Volet latéral gauche d'édition de photo (Onglets Retouches, Éclairage, Effets).
    EN: Left photo editing sidebar panel (Basic Fixes, Tuning, Effects tabs).
    Ref: picasa3.exe @ editoneup, filterdesc.xml
    """
    back_to_library = Signal()
    apply_effect = Signal(str, dict)  # (effect_name, params)
    neutral_color_picker_toggled = Signal(bool)
    undo_action = Signal()
    redo_action = Signal()
    save_action = Signal()  # Ref: picasa3.exe @ ID_FILE_SAVE (0x008814AC, Ctrl+S)

    # FR: Signaux de recadrage interactif / EN: Interactive cropping signals (Ref: editpanel/crop*)
    crop_requested = Signal()
    crop_ratio_changed = Signal(object)
    crop_apply = Signal()
    crop_discard = Signal()
    crop_cancel = Signal()

    # FR: Signaux de redressement / EN: Straightening signals (Ref: filter_tilt, 0x008814AC)
    straighten_requested = Signal()
    straighten_angle_changed = Signal(float)
    straighten_apply = Signal()
    straighten_cancel = Signal()
    straighten_reset = Signal()

    # FR: Signaux d'outil texte / EN: Text tool signals (Ref: editpanel/edittextpanel, 0x00658900)
    text_tool_requested = Signal()
    text_params_changed = Signal(str, int, object, bool)
    text_apply = Signal()
    text_cancel = Signal()

    # FR: Signaux yeux rouges / EN: Red-eye signals (Ref: filterdesc.xml @ redeye)
    redeye_requested = Signal()
    redeye_apply = Signal()
    redeye_cancel = Signal()

    # FR: Signaux retouche / EN: Retouch signals (Ref: filterdesc.xml @ retouch)
    retouch_requested = Signal()
    retouch_apply = Signal(float)
    retouch_cancel = Signal()
    retouch_radius_changed = Signal(float)

    # FR: Signaux d'aperçu en direct et de validation des filtres à curseurs / EN: Live preview and commit signals for slider filters (Ref: filterdesc.xml @ mode="effect" / mode="soft")
    tuning_preview_changed = Signal(dict)        # {"fill": float, "highlights": float, "shadows": float, "colortemp": float}
    tuning_applied = Signal(dict)                # Valide les réglages d'éclairage dans l'historique et .picasa.ini
    effect_preview_requested = Signal(str, dict) # (effect_name, params) à l'ouverture ou déplacement d'un curseur
    effect_applied = Signal(str, dict)           # (effect_name, params) lors du clic sur Appliquer (editpanel/ok)
    effect_cancelled = Signal()                  # lors du clic sur Annuler (editpanel/cancel)

    # FR: Signal de verrouillage modal de l'interface lors de l'ouverture/fermeture d'un outil ou filtre (Ref: picasa3.exe @ 0x0057BB50, FUN_0057bb50)
    # EN: Modal UI lock signal when entering/exiting an interactive tool or filter subpanel (Ref: picasa3.exe @ 0x0057BB50, FUN_0057bb50)
    modal_tool_lock_changed = Signal(bool, int, str)  # (locked, mode, tool_or_effect_id)


    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise le panneau latéral d'édition avec ses 5 onglets, ses sous-panneaux d'outils et son histogramme.
        EN: Initializes the left editing panel with its 5 tabs, tool subpanels, and histogram.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()
        self._syncing_tuning_sliders: bool = False
        self.is_tool_locked: bool = False
        self.active_tool_mode: int = 0
        self.active_tool_id: str = ""
        # FR: Registre des tuiles d'effets par onglet (2=Effets 1, 3=Effets 2, 4=Effets 3) et cache de miniatures (Ref: editpanel/fxthumbs @ 0x00568A08)
        # EN: Registry of effect tiles by tab index (2=Effects 1, 3=Effects 2, 4=Effects 3) and thumbnail cache (Ref: editpanel/fxthumbs @ 0x00568A08)
        self._effect_tiles_by_tab: dict[int, list[PicasaEffectTileButton]] = {2: [], 3: [], 4: []}
        self._base_fx_thumb: Optional[Image.Image] = None
        self._fx_preview_cache: dict[str, QPixmap] = {}

        self.setFixedWidth(295)
        self.setObjectName("EditPanelRoot")
        self.apply_style(self.style)

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. FR: En-tête haut gauche / EN: Top-left header: editpanel/albumview (rect=(10, 9, 132, 31))
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self.btn_back = QPushButton("◀ Retour à la photothèque")
        self.btn_back.setObjectName("BackBtn")
        self.btn_back.setToolTip("Quitter l'éditeur et revenir à la photothèque (Échap)")
        self.btn_back.clicked.connect(self.back_to_library.emit)
        top_row.addWidget(self.btn_back, 1)
        main_layout.addLayout(top_row)

        # 2. FR: Boîte d'outils principale / EN: Main toolbox: editpanel/edittabbase & editpanel/editcontrols (rect=(3, 40, 279, 391))
        # Ref: respack.yt @ tre:editpanel (editpanel/tab1..tab5, Property button_buttcon 1), TOOLTIPS_FR.XML:231-245
        self.stack = QStackedWidget()

        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(25, 19))
        self.tabs.addTab(self._create_basic_fixes_tab(), self.res_mgr.get_edit_tab_icon(0), "")
        self.tabs.addTab(self._create_tuning_tab(), self.res_mgr.get_edit_tab_icon(1), "")
        self.tabs.addTab(self._create_effects_tab1(), self.res_mgr.get_edit_tab_icon(2), "")
        self.tabs.addTab(self._create_effects_tab2(), self.res_mgr.get_edit_tab_icon(3), "")
        self.tabs.addTab(self._create_effects_tab3(), self.res_mgr.get_edit_tab_icon(4), "")
        self.tabs.setTabToolTip(0, self.res_mgr.get_xml_string("editpanel/tab1.tooltip", "Retouches courantes"))
        self.tabs.setTabToolTip(1, self.res_mgr.get_xml_string("editpanel/tab2.tooltip", "Retouches précises de l'éclairage et des couleurs"))
        self.tabs.setTabToolTip(2, self.res_mgr.get_xml_string("editpanel/tab3.tooltip", "Traitement des images en toute simplicité"))
        self.tabs.setTabToolTip(3, self.res_mgr.get_xml_string("editpanel/tab4.tooltip", "Un traitement des images encore plus simple"))
        self.tabs.setTabToolTip(4, self.res_mgr.get_xml_string("editpanel/tab5.tooltip", "Un traitement des images encore plus simple"))
        self.tabs.currentChanged.connect(self._on_main_tab_changed)
        self.stack.addWidget(self.tabs)  # Page 0

        self.crop_subpanel = PicasaCropSubpanel(self)
        self.crop_subpanel.ratio_changed.connect(self.crop_ratio_changed.emit)
        self.crop_subpanel.apply_clicked.connect(self._on_crop_apply)
        self.crop_subpanel.discard_clicked.connect(self._on_crop_discard)
        self.crop_subpanel.cancel_clicked.connect(self._on_crop_cancel)
        self.stack.addWidget(self.crop_subpanel)  # Page 1

        self.straighten_subpanel = PicasaStraightenSubpanel(self)
        self.straighten_subpanel.angle_changed.connect(self.straighten_angle_changed.emit)
        self.straighten_subpanel.apply_clicked.connect(self._on_straighten_apply)
        self.straighten_subpanel.reset_clicked.connect(self.straighten_reset.emit)
        self.straighten_subpanel.cancel_clicked.connect(self._on_straighten_cancel)
        self.stack.addWidget(self.straighten_subpanel)  # Page 2

        self.text_subpanel = PicasaTextSubpanel(self)
        self.text_subpanel.params_changed.connect(self.text_params_changed.emit)
        self.text_subpanel.apply_clicked.connect(self._on_text_apply)
        self.text_subpanel.cancel_clicked.connect(self._on_text_cancel)
        self.stack.addWidget(self.text_subpanel)  # Page 3

        self.redeye_subpanel = PicasaRedEyeSubpanel(self)
        self.redeye_subpanel.apply_clicked.connect(self._on_redeye_apply)
        self.redeye_subpanel.cancel_clicked.connect(self._on_redeye_cancel)
        self.stack.addWidget(self.redeye_subpanel)  # Page 4

        self.retouch_subpanel = PicasaRetouchSubpanel(self)
        self.retouch_subpanel.apply_clicked.connect(self._on_retouch_apply)
        self.retouch_subpanel.cancel_clicked.connect(self._on_retouch_cancel)
        self.retouch_subpanel.radius_changed.connect(self.retouch_radius_changed.emit)
        self.stack.addWidget(self.retouch_subpanel)  # Page 5

        # FR: Sous-panneau vidéo / EN: Video subpanel (Ref: STRINGRES_FR.XML:640)
        self.video_subpanel = self._create_video_subpanel()
        self.stack.addWidget(self.video_subpanel)  # Page 6

        # FR: Sous-panneau générique des filtres à curseurs / EN: Generic slider filters subpanel (Ref: filterdesc.xml @ mode="effect")
        self.effect_subpanel = PicasaEffectSubpanel(self)
        self.effect_subpanel.preview_changed.connect(self.effect_preview_requested.emit)
        self.effect_subpanel.apply_clicked.connect(self._on_effect_subpanel_apply)
        self.effect_subpanel.cancel_clicked.connect(self._on_effect_subpanel_cancel)
        self.stack.addWidget(self.effect_subpanel)  # Page 7

        main_layout.addWidget(self.stack, 1)

        # 3. FR: Bas de editcontrols / EN: Bottom of editcontrols (YConstraint 1, 1, -4):
        # editpanel/filter_undo (rect=(7, 361, 139, 389)) & editpanel/filter_redo (rect=(144, 361, 276, 389))
        undo_box = QHBoxLayout()
        undo_box.setSpacing(6)
        self.btn_undo = QPushButton("↶ Annuler")
        self.btn_undo.setObjectName("ToolBtn")
        self.btn_undo.setFixedHeight(28)
        self.btn_undo.clicked.connect(self.undo_action.emit)
        undo_box.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↷ Rétablir")
        self.btn_redo.setObjectName("ToolBtn")
        self.btn_redo.setFixedHeight(28)
        self.btn_redo.clicked.connect(self.redo_action.emit)
        undo_box.addWidget(self.btn_redo)
        main_layout.addLayout(undo_box)

        # FR: Bouton Enregistrer sur le disque / EN: Save to disk button (Ref: picasa3.exe @ editpanel/writetodisk, ID_FILE_SAVE, Ctrl+S)
        self.btn_save = QPushButton("💾 Enregistrer sur le disque")
        self.btn_save.setObjectName("SaveBtn")
        self.btn_save.setToolTip("Enregistrer les retouches sur le fichier et sauvegarder l'original dans .picasaoriginals (Ctrl+S)")
        self.btn_save.setStyleSheet("""
            QPushButton#SaveBtn {
                background-color: #2F6DB5;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 11px;
                border: 1px solid #1E4E85;
            }
            QPushButton#SaveBtn:hover {
                background-color: #3879D9;
            }
        """)
        self.btn_save.clicked.connect(self.save_action.emit)
        main_layout.addWidget(self.btn_save)

        # 4. FR: Bas du volet gauche : Histogramme & Fiche Appareil Photo / EN: Bottom of left panel: Histogram & Camera Info Card (Ref: editpanel/nerdview_container YConstraint 1,1,-95)
        self.hist_box = QWidget()
        hist_vbox = QVBoxLayout(self.hist_box)
        hist_vbox.setContentsMargins(0, 2, 0, 2)
        hist_vbox.setSpacing(3)

        hist_header = QHBoxLayout()
        lbl_hist = QLabel("Histogramme & EXIF :")
        lbl_hist.setObjectName("HistHeaderLabel")
        hist_header.addWidget(lbl_hist)
        hist_header.addStretch(1)

        for mode_title, mode_val in [("Tous", "RGB"), ("R", "R"), ("V", "G"), ("B", "B"), ("Lum", "L")]:
            b = QPushButton(mode_title)
            b.setObjectName("HistModeBtn")
            b.setFixedSize(28, 16)
            b.clicked.connect(lambda _, m=mode_val: self.histogram_widget.set_channel_mode(m))
            hist_header.addWidget(b)
        hist_vbox.addLayout(hist_header)

        self.histogram_widget = PicasaHistogramWidget(height=60, parent=self, style=self.style)
        hist_vbox.addWidget(self.histogram_widget)

        self.camera_info_card = PicasaCameraInfoCard(parent=self, style=self.style)
        hist_vbox.addWidget(self.camera_info_card)

        main_layout.addWidget(self.hist_box)
        self.apply_style(self.style)

    def set_modal_tool_lock(self, locked: bool, mode: int = 0, tool_id: str = "", emit_signal: bool = True) -> None:
        """
        FR: Verrouille ou déverrouille les contrôles du panneau d'édition gauche (onglets, Annuler, Rétablir,
            Enregistrer, Histogramme) lorsqu'un outil modal (`mode in (2, 3, 4, 6)`) est actif.
        EN: Locks or unlocks left edit panel controls (tabs, Undo, Redo, Save, Histogram)
            when a modal tool or parameterized filter (`mode in (2, 3, 4, 6)`) is active.
        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50), 0x005F8520 (FUN_005f8520), 0x00900490 (FUN_00900490)
        """
        self.is_tool_locked = bool(locked)
        self.active_tool_mode = int(mode) if locked else 0
        self.active_tool_id = str(tool_id) if locked else ""

        if hasattr(self, "tabs") and self.tabs.tabBar() is not None:
            self.tabs.tabBar().setEnabled(not locked)
        if hasattr(self, "btn_undo"):
            self.btn_undo.setEnabled(not locked)
        if hasattr(self, "btn_redo"):
            self.btn_redo.setEnabled(not locked)
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(not locked)
        if hasattr(self, "hist_box"):
            self.hist_box.setEnabled(not locked)
        if hasattr(self, "btn_back"):
            # Ref: picasa3.exe @ 0x0057BE8B (editpanel/albumview disabled in mode 3)
            self.btn_back.setEnabled(not (locked and mode == 3))

        if emit_signal:
            self.modal_tool_lock_changed.emit(self.is_tool_locked, self.active_tool_mode, self.active_tool_id)

    def cancel_active_subpanel(self) -> None:
        """
        FR: Annule tout sous-panneau d'outil ou d'effet actuellement ouvert et déverrouille l'interface.
        EN: Cancels any currently open tool or effect subpanel and unlocks the UI.
        Ref: picasa3.exe @ 0x005F8160 (FUN_005f8160), 0x005F9230 (FUN_005f9230)
        """
        cur = self.stack.currentWidget() if hasattr(self, "stack") else None
        if cur == self.crop_subpanel:
            self._on_crop_cancel()
        elif cur == self.straighten_subpanel:
            self._on_straighten_cancel()
        elif cur == self.text_subpanel:
            self._on_text_cancel()
        elif cur == self.redeye_subpanel:
            self._on_redeye_cancel()
        elif cur == self.retouch_subpanel:
            self._on_retouch_cancel()
        elif cur == self.effect_subpanel:
            self._on_effect_subpanel_cancel()
        elif self.is_tool_locked:
            self.set_modal_tool_lock(False, 0, "")

    def _open_crop_subpanel(self) -> None:
        """
        FR: Affiche le sous-panneau de recadrage, verrouille l'interface (mode 2) et émet `crop_requested`.
        EN: Displays the cropping subpanel, locks the UI (mode 2), and emits `crop_requested`.
        Ref: picasa3.exe @ 0x005EFE99, 0x0057BB50
        """
        self.crop_subpanel.reset_to_manual()
        self.stack.setCurrentIndex(1)
        self.set_modal_tool_lock(True, 2, "crop")
        self.crop_requested.emit()

    def _on_crop_apply(self) -> None:
        """
        FR: Ferme le sous-panneau de recadrage, déverrouille l'interface et émet `crop_apply`.
        EN: Closes the cropping subpanel, unlocks the UI, and emits `crop_apply`.
        Ref: picasa3.exe @ 0x005EFFCD, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.crop_apply.emit()

    def _on_crop_discard(self) -> None:
        """
        FR: Ferme le sous-panneau de recadrage, déverrouille l'interface et émet `crop_discard` pour réinitialiser le cadrage.
        EN: Closes the cropping subpanel, unlocks the UI, and emits `crop_discard` to reset the crop.
        Ref: picasa3.exe @ 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.crop_discard.emit()

    def _on_crop_cancel(self) -> None:
        """
        FR: Annule le recadrage en cours, déverrouille l'interface et revient aux onglets principaux.
        EN: Cancels the current crop operation, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F0160, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.crop_cancel.emit()

    def _open_straighten_subpanel(self) -> None:
        """
        FR: Affiche le sous-panneau de redressement, verrouille l'interface (mode 6) et émet `straighten_requested`.
        EN: Displays the straightening subpanel, locks the UI (mode 6), and emits `straighten_requested`.
        Ref: picasa3.exe @ 0x005F8775, 0x0057BB50
        """
        self.straighten_subpanel.slider.setValue(0)
        self.stack.setCurrentIndex(2)
        self.set_modal_tool_lock(True, 6, "straighten")
        self.straighten_requested.emit()

    def _on_straighten_apply(self) -> None:
        """
        FR: Valide le redressement, déverrouille l'interface et revient aux onglets principaux.
        EN: Applies the straightening angle, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F88AB, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.straighten_apply.emit()

    def _on_straighten_cancel(self) -> None:
        """
        FR: Annule le redressement en cours, déverrouille l'interface et revient aux onglets principaux.
        EN: Cancels the straightening operation, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F8945, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.straighten_cancel.emit()

    def _open_text_subpanel(self) -> None:
        """
        FR: Affiche le sous-panneau d'outil texte, verrouille l'interface (mode 2) et émet `text_tool_requested`.
        EN: Displays the text tool subpanel, locks the UI (mode 2), and emits `text_tool_requested`.
        Ref: picasa3.exe @ 0x005F63ED, 0x0057BB50
        """
        self.text_subpanel.reset_text()
        self.stack.setCurrentIndex(3)
        self.set_modal_tool_lock(True, 2, "text")
        self.text_tool_requested.emit()

    def _on_text_apply(self) -> None:
        """
        FR: Valide l'ajout de texte, déverrouille l'interface et revient aux onglets principaux.
        EN: Commits the text overlay, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F6789, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.text_apply.emit()

    def _on_text_cancel(self) -> None:
        """
        FR: Annule l'ajout de texte, déverrouille l'interface et revient aux onglets principaux.
        EN: Cancels the text overlay, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F68DA, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.text_cancel.emit()

    def _open_redeye_subpanel(self) -> None:
        """
        FR: Affiche le sous-panneau de correction des yeux rouges, verrouille l'interface (mode 2) et émet `redeye_requested`.
        EN: Displays the red-eye reduction subpanel, locks the UI (mode 2), and emits `redeye_requested`.
        Ref: picasa3.exe @ 0x005F2CCB, 0x0057BB50
        """
        self.stack.setCurrentIndex(4)
        self.set_modal_tool_lock(True, 2, "redeye")
        self.redeye_requested.emit()

    def _on_redeye_apply(self) -> None:
        """
        FR: Valide la correction des yeux rouges, déverrouille l'interface et revient aux onglets principaux.
        EN: Applies red-eye reduction, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F2F3C, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.redeye_apply.emit()

    def _on_redeye_cancel(self) -> None:
        """
        FR: Annule l'outil yeux rouges, déverrouille l'interface et revient aux onglets principaux.
        EN: Cancels the red-eye tool, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F2FE7, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.redeye_cancel.emit()

    def _open_retouch_subpanel(self) -> None:
        """
        FR: Affiche le sous-panneau de retouche locale, verrouille l'interface (mode 2) et émet `retouch_requested`.
        EN: Displays the local retouch subpanel, locks the UI (mode 2), and emits `retouch_requested`.
        Ref: picasa3.exe @ 0x005F374C, 0x0057BB50
        """
        self.stack.setCurrentIndex(5)
        self.set_modal_tool_lock(True, 2, "retouch")
        self.retouch_requested.emit()

    def _on_retouch_apply(self, radius: float) -> None:
        """
        FR: Valide la retouche avec le rayon spécifié, déverrouille l'interface et revient aux onglets principaux.
        EN: Applies retouching with the specified radius, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F39A1, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.retouch_apply.emit(radius)

    def _on_retouch_cancel(self) -> None:
        """
        FR: Annule l'outil de retouche, déverrouille l'interface et revient aux onglets principaux.
        EN: Cancels the retouching tool, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F3A52, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.retouch_cancel.emit()

    def _on_effect_button_clicked(self, action_id: str) -> None:
        """
        FR: Gère le clic sur un filtre dans les onglets d'effets :
            - Si le filtre est à clic unique (`mode="oneclick"` dans `filterdesc.xml`), applique immédiatement sans verrouiller.
            - Si le filtre possède des curseurs/options (`mode="effect"` -> mode 4), ouvre le sous-panneau de réglage,
              verrouille l'interface (`FUN_0057bb50`) et lance l'aperçu en direct sur l'image de base sans valider
              tant que l'utilisateur n'a pas cliqué sur Appliquer.
        EN: Handles clicking a filter in the effect tabs:
            - If the filter is one-click (`mode="oneclick"` in `filterdesc.xml`), applies immediately without locking.
            - If the filter has sliders/options (`mode="effect"` -> mode 4), opens the adjustment subpanel,
              locks the UI (`FUN_0057bb50`), and previews live on the base image without committing
              until the user clicks Apply.

        Ref: picasa3.exe @ 0x005F8520 (FUN_005f8520), 0x0057BB50 (FUN_0057bb50), filterdesc.xml
        """
        if action_id in ONECLICK_EFFECTS or action_id not in FILTER_SPECS:
            self.apply_effect.emit(action_id, {})
            return
        spec = FILTER_SPECS[action_id]
        self.effect_subpanel.configure_effect(action_id, spec)
        self.stack.setCurrentWidget(self.effect_subpanel)
        self.set_modal_tool_lock(True, 4, action_id)
        self.effect_preview_requested.emit(action_id, self.effect_subpanel.get_params())

    def _on_effect_subpanel_apply(self, effect_name: str, params: dict) -> None:
        """
        FR: Valide l'effet paramétrable sélectionné dans le sous-panneau, déverrouille l'interface et revient aux onglets principaux.
        EN: Commits the parameterized effect from the subpanel, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F88AB, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.effect_applied.emit(effect_name, params)

    def _on_effect_subpanel_cancel(self) -> None:
        """
        FR: Annule l'effet paramétrable en cours d'aperçu, déverrouille l'interface et revient aux onglets principaux.
        EN: Cancels the parameterized effect preview, unlocks the UI, and returns to the main tabs.
        Ref: picasa3.exe @ 0x005F8945, 0x0057BB50
        """
        self.stack.setCurrentIndex(0)
        self.set_modal_tool_lock(False, 0, "")
        self.effect_cancelled.emit()

    def get_tuning_params(self) -> dict:
        """
        FR: Retourne l'état courant des 4 curseurs de réglage d'éclairage (Tab 1 / Tab 2).
        EN: Returns the current state of the 4 lighting/tuning sliders (Tab 1 / Tab 2).
        """
        return {
            "fill": self.sldr_fill.value() / 100.0,
            "highlights": self.sldr_highlights.value() / 100.0,
            "shadows": self.sldr_shadows.value() / 100.0,
            "colortemp": float(self.sldr_temp.value()),
        }

    def reset_tuning_controls_silently(self) -> None:
        """
        FR: Remet les curseurs de Lumière d'appoint et Réglages à zéro sans émettre d'événement d'édition.
        EN: Resets the Fill Light and Tuning sliders to zero without emitting edit signals.
        """
        self._syncing_tuning_sliders = True
        try:
            for s in (self.sldr_basic_fill, self.sldr_fill, self.sldr_highlights, self.sldr_shadows, self.sldr_temp):
                s.blockSignals(True)
                s.setValue(0)
                s.blockSignals(False)
            if hasattr(self, "lbl_basic_fill_val"):
                self.lbl_basic_fill_val.setText("0%")
            if hasattr(self, "lbl_fill_val"):
                self.lbl_fill_val.setText("0%")
            if hasattr(self, "lbl_highlights_val"):
                self.lbl_highlights_val.setText("0%")
            if hasattr(self, "lbl_shadows_val"):
                self.lbl_shadows_val.setText("0%")
            if hasattr(self, "lbl_temp_val"):
                self.lbl_temp_val.setText("0")
        finally:
            self._syncing_tuning_sliders = False

    def _on_tuning_slider_value_changed(self, source: str, val: int) -> None:
        """
        FR: Synchronise `sldr_basic_fill` (Tab 1) et `sldr_fill` (Tab 2), met à jour les étiquettes
            et émet `tuning_preview_changed` pour un aperçu en temps réel non-cumulatif depuis l'image de base.
        EN: Synchronizes `sldr_basic_fill` (Tab 1) and `sldr_fill` (Tab 2), updates labels,
            and emits `tuning_preview_changed` for non-cumulative real-time preview from the base image.

        Ref: respack.yt @ editpanel.tre (flightslider1, finetune2)
        """
        if self._syncing_tuning_sliders:
            return
        self._syncing_tuning_sliders = True
        try:
            if source == "basic_fill":
                self.sldr_fill.blockSignals(True)
                self.sldr_fill.setValue(val)
                self.sldr_fill.blockSignals(False)
                self.lbl_basic_fill_val.setText(f"{val}%")
                self.lbl_fill_val.setText(f"{val}%")
            elif source == "fill":
                self.sldr_basic_fill.blockSignals(True)
                self.sldr_basic_fill.setValue(val)
                self.sldr_basic_fill.blockSignals(False)
                self.lbl_basic_fill_val.setText(f"{val}%")
                self.lbl_fill_val.setText(f"{val}%")
            elif source == "highlights":
                self.lbl_highlights_val.setText(f"{val}%")
            elif source == "shadows":
                self.lbl_shadows_val.setText(f"{val}%")
            elif source == "temp":
                self.lbl_temp_val.setText(f"{val:+d}" if val != 0 else "0")
        finally:
            self._syncing_tuning_sliders = False

        self.tuning_preview_changed.emit(self.get_tuning_params())

    def _create_basic_fixes_tab(self) -> QWidget:
        """
        FR: Construit l'onglet 1 « Retouches courantes » (`editpanel/tabpanel1`) selon la disposition de `editpanel.tre`
            (grille de 3 colonnes d'outils + curseur Lumière d'appoint en bas).
        EN: Builds Tab 1 "Basic Fixes" (`editpanel/tabpanel1`) matching the `editpanel.tre` layout
            (3-column tool grid + Fill Light slider at the bottom).
        Ref: respack.yt @ editpanel.tre (tabpanel1, flightslider1, backlight_container)
        """
        w = QWidget()
        w.setObjectName("TabScrollContent")
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(6, 8, 6, 8)
        vbox.setSpacing(8)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)

        self._basic_tool_buttons: dict[str, QToolButton] = {}
        tools = [
            (
                self.res_mgr.get_xml_string("editpanel/crop", "Recadrer"),
                self.res_mgr.get_xml_string("editpanel/crop.tooltip", "Recadrer l'image"),
                "crop",
                "crop",
            ),
            (
                self.res_mgr.get_xml_string("editpanel/horizonadjust", "Redresser"),
                self.res_mgr.get_xml_string("editpanel/horizonadjust.tooltip", "Redresser une photo penchée"),
                "straighten",
                "straighten",
            ),
            (
                self.res_mgr.get_xml_string("editpanel/redeye", "Yeux rouges"),
                self.res_mgr.get_xml_string("editpanel/redeye.tooltip", "Corriger les yeux rouges"),
                "redeye",
                "redeye",
            ),
            (
                self.res_mgr.get_xml_string("editpanel/enhance", "J'ai de la chance"),
                self.res_mgr.get_xml_string("editpanel/enhance.tooltip", "Corriger automatiquement l'éclairage et la couleur"),
                "lucky",
                "enhance",
            ),
            (
                self.res_mgr.get_xml_string("editpanel/autolighting", "Contraste auto"),
                self.res_mgr.get_xml_string("editpanel/autolighting.tooltip", "Corriger l'exposition sans affecter les couleurs"),
                "autocontrast",
                "autolighting",
            ),
            (
                self.res_mgr.get_xml_string("editpanel/autocolor", "Couleur auto"),
                self.res_mgr.get_xml_string("editpanel/autocolor.tooltip", "Supprimer la dominante de couleur tout en préservant l'exposition"),
                "autocolor",
                "autocolor",
            ),
            (
                self.res_mgr.get_xml_string("editpanel/retouch", "Retoucher"),
                self.res_mgr.get_xml_string("editpanel/retouch.tooltip", "Éliminer les imperfections et améliorer la qualité de la photo"),
                "retouch",
                "retouch",
            ),
            (
                self.res_mgr.get_xml_string("editpanel/edittext", "Texte"),
                self.res_mgr.get_xml_string("editpanel/edittext.tooltip", "Superposer du texte sur votre image"),
                "text",
                "text",
            ),
        ]

        for i, (label, tooltip, action_id, icon_key) in enumerate(tools):
            btn = QToolButton()
            btn.setObjectName("ToolBtn")
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setIcon(self.res_mgr.get_edit_tool_icon(icon_key))
            btn.setIconSize(QSize(44, 30))
            btn.setText(label)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(60)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            if action_id == "crop":
                self.btn_crop = btn
                btn.clicked.connect(self._open_crop_subpanel)
            elif action_id == "straighten":
                self.btn_straighten = btn
                btn.clicked.connect(self._open_straighten_subpanel)
            elif action_id == "redeye":
                self.btn_redeye = btn
                btn.clicked.connect(self._open_redeye_subpanel)
            elif action_id == "retouch":
                self.btn_retouch = btn
                btn.clicked.connect(self._open_retouch_subpanel)
            elif action_id == "text":
                self.btn_text = btn
                btn.clicked.connect(self._open_text_subpanel)
            else:
                btn.clicked.connect(lambda _, a=action_id: self.apply_effect.emit(a, {}))
            self._basic_tool_buttons[action_id] = btn
            grid.addWidget(btn, i // 3, i % 3)

        vbox.addLayout(grid)

        # FR: Curseur « Lumière d'appoint » en bas de tabpanel1 / EN: "Fill Light" slider at the bottom of tabpanel1
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("TabSeparator")
        vbox.addWidget(sep)

        fill_row = QHBoxLayout()
        fill_row.setContentsMargins(2, 2, 2, 2)
        fill_row.setSpacing(6)
        lbl_fill_icon = QLabel("💡")
        lbl_fill_icon.setStyleSheet("font-size: 16px;")
        fill_row.addWidget(lbl_fill_icon)

        fill_col = QVBoxLayout()
        fill_col.setContentsMargins(0, 0, 0, 0)
        fill_col.setSpacing(2)

        fill_hdr = QHBoxLayout()
        lbl_fill_txt = QLabel("Lumière d'appoint :")
        lbl_fill_txt.setObjectName("FillLightLabel")
        self.lbl_basic_fill_val = QLabel("0%")
        self.lbl_basic_fill_val.setObjectName("SubpanelValue")
        self.btn_apply_basic_fill = QPushButton("✓")
        self.btn_apply_basic_fill.setObjectName("HistModeBtn")
        self.btn_apply_basic_fill.setFixedSize(20, 18)
        self.btn_apply_basic_fill.setToolTip("Appliquer la lumière d'appoint")
        self.btn_apply_basic_fill.clicked.connect(lambda: self.tuning_applied.emit(self.get_tuning_params()))
        btn_rst_basic_fill = QPushButton("↺")
        btn_rst_basic_fill.setObjectName("HistModeBtn")
        btn_rst_basic_fill.setFixedSize(20, 18)
        btn_rst_basic_fill.setToolTip("Réinitialiser la lumière d'appoint (0%)")
        fill_hdr.addWidget(lbl_fill_txt)
        fill_hdr.addStretch(1)
        fill_hdr.addWidget(self.lbl_basic_fill_val)
        fill_hdr.addWidget(self.btn_apply_basic_fill)
        fill_hdr.addWidget(btn_rst_basic_fill)
        fill_col.addLayout(fill_hdr)

        self.sldr_basic_fill = QSlider(Qt.Orientation.Horizontal)
        self.sldr_basic_fill.setRange(0, 100)
        self.sldr_basic_fill.setValue(0)
        self.sldr_basic_fill.valueChanged.connect(
            lambda v: self._on_tuning_slider_value_changed("basic_fill", v)
        )
        self.sldr_basic_fill.sliderReleased.connect(
            lambda: self.apply_effect.emit("fill_light", {"amount": self.sldr_basic_fill.value() / 100.0})
        )
        btn_rst_basic_fill.clicked.connect(lambda: self._reset_single_tuning_slider("fill"))
        fill_col.addWidget(self.sldr_basic_fill)
        fill_row.addLayout(fill_col, 1)
        vbox.addLayout(fill_row)

        vbox.addStretch(1)
        return w

    def _create_tuning_tab(self) -> QWidget:
        """
        FR: Construit l'onglet 2 « Réglages » (Lumière d'appoint, Hautes lumières, Ombres, Température et Pipette).
        EN: Builds Tab 2 "Tuning" (Fill Light, Highlights, Shadows, Color Temperature, and Neutral Picker).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. FR: Lumière d'appoint / EN: Fill Light
        h_fill = QHBoxLayout()
        h_fill.addWidget(QLabel("💡 Lumière d'appoint :"))
        h_fill.addStretch(1)
        self.lbl_fill_val = QLabel("0%")
        self.lbl_fill_val.setObjectName("SubpanelValue")
        btn_rst_fill = QPushButton("↺")
        btn_rst_fill.setObjectName("HistModeBtn")
        btn_rst_fill.setFixedSize(20, 18)
        btn_rst_fill.setToolTip("Réinitialiser la lumière d'appoint (0%)")
        btn_rst_fill.clicked.connect(lambda: self._reset_single_tuning_slider("fill"))
        h_fill.addWidget(self.lbl_fill_val)
        h_fill.addWidget(btn_rst_fill)
        layout.addLayout(h_fill)

        self.sldr_fill = QSlider(Qt.Orientation.Horizontal)
        self.sldr_fill.setRange(0, 100)
        self.sldr_fill.setValue(0)
        self.sldr_fill.valueChanged.connect(
            lambda v: self._on_tuning_slider_value_changed("fill", v)
        )
        self.sldr_fill.sliderReleased.connect(
            lambda: self.apply_effect.emit("fill_light", {"amount": self.sldr_fill.value() / 100.0})
        )
        layout.addWidget(self.sldr_fill)

        # 2. FR: Hautes lumières / EN: Highlights
        h_hl = QHBoxLayout()
        h_hl.addWidget(QLabel("☀️ Hautes lumières :"))
        h_hl.addStretch(1)
        self.lbl_highlights_val = QLabel("0%")
        self.lbl_highlights_val.setObjectName("SubpanelValue")
        btn_rst_hl = QPushButton("↺")
        btn_rst_hl.setObjectName("HistModeBtn")
        btn_rst_hl.setFixedSize(20, 18)
        btn_rst_hl.setToolTip("Réinitialiser les hautes lumières (0%)")
        btn_rst_hl.clicked.connect(lambda: self._reset_single_tuning_slider("highlights"))
        h_hl.addWidget(self.lbl_highlights_val)
        h_hl.addWidget(btn_rst_hl)
        layout.addLayout(h_hl)

        self.sldr_highlights = QSlider(Qt.Orientation.Horizontal)
        self.sldr_highlights.setRange(0, 100)
        self.sldr_highlights.setValue(0)
        self.sldr_highlights.valueChanged.connect(
            lambda v: self._on_tuning_slider_value_changed("highlights", v)
        )
        self.sldr_highlights.sliderReleased.connect(
            lambda: self.apply_effect.emit("highlights", {"amount": self.sldr_highlights.value() / 100.0})
        )
        layout.addWidget(self.sldr_highlights)

        # 3. FR: Ombres / EN: Shadows
        h_sh = QHBoxLayout()
        h_sh.addWidget(QLabel("🌑 Ombres :"))
        h_sh.addStretch(1)
        self.lbl_shadows_val = QLabel("0%")
        self.lbl_shadows_val.setObjectName("SubpanelValue")
        btn_rst_sh = QPushButton("↺")
        btn_rst_sh.setObjectName("HistModeBtn")
        btn_rst_sh.setFixedSize(20, 18)
        btn_rst_sh.setToolTip("Réinitialiser les ombres (0%)")
        btn_rst_sh.clicked.connect(lambda: self._reset_single_tuning_slider("shadows"))
        h_sh.addWidget(self.lbl_shadows_val)
        h_sh.addWidget(btn_rst_sh)
        layout.addLayout(h_sh)

        self.sldr_shadows = QSlider(Qt.Orientation.Horizontal)
        self.sldr_shadows.setRange(0, 100)
        self.sldr_shadows.setValue(0)
        self.sldr_shadows.valueChanged.connect(
            lambda v: self._on_tuning_slider_value_changed("shadows", v)
        )
        self.sldr_shadows.sliderReleased.connect(
            lambda: self.apply_effect.emit("shadows", {"amount": self.sldr_shadows.value() / 100.0})
        )
        layout.addWidget(self.sldr_shadows)

        # 4. FR: Température de couleur avec Pipette de couleur neutre / EN: Color Temp with Neutral Color Picker (Ref: filter_whitept, CDesaturateFilter::pickcolor)
        h_temp_lbl = QHBoxLayout()
        h_temp_lbl.addWidget(QLabel("🌡️ Température :"))
        h_temp_lbl.addStretch(1)
        self.lbl_temp_val = QLabel("0")
        self.lbl_temp_val.setObjectName("SubpanelValue")
        h_temp_lbl.addWidget(self.lbl_temp_val)

        btn_rst_temp = QPushButton("↺")
        btn_rst_temp.setObjectName("HistModeBtn")
        btn_rst_temp.setFixedSize(20, 18)
        btn_rst_temp.setToolTip("Réinitialiser la température de couleur (0)")
        btn_rst_temp.clicked.connect(lambda: self._reset_single_tuning_slider("temp"))
        h_temp_lbl.addWidget(btn_rst_temp)

        self.btn_neutral_color = QPushButton("🧪 Pipette")
        self.btn_neutral_color.setObjectName("SmallActionBtn")
        self.btn_neutral_color.setCheckable(True)
        self.btn_neutral_color.setToolTip("Pipette couleur neutre : cliquez sur un point blanc ou gris neutre sur la photo pour corriger la balance des blancs (Ref: filter_whitept)")
        self.btn_neutral_color.toggled.connect(self.neutral_color_picker_toggled.emit)
        h_temp_lbl.addWidget(self.btn_neutral_color)
        layout.addLayout(h_temp_lbl)

        self.sldr_temp = QSlider(Qt.Orientation.Horizontal)
        self.sldr_temp.setRange(-50, 50)
        self.sldr_temp.setValue(0)
        self.sldr_temp.valueChanged.connect(
            lambda v: self._on_tuning_slider_value_changed("temp", v)
        )
        self.sldr_temp.sliderReleased.connect(
            lambda: self.apply_effect.emit("color_temp", {"temp": float(self.sldr_temp.value())})
        )
        layout.addWidget(self.sldr_temp)

        # FR: Boutons Valider (Appliquer) / Réinitialiser l'éclairage / EN: Apply / Reset lighting buttons
        self.btn_apply_tuning = QPushButton(self.res_mgr.get_string("editpanel/ok", "Appliquer les réglages"))
        self.btn_apply_tuning.setObjectName("ApplyTuningBtn")
        self.btn_apply_tuning.setStyleSheet("""
            QPushButton#ApplyTuningBtn {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 5px 8px;
                border-radius: 4px;
                border: 1px solid #2859A3;
            }
            QPushButton#ApplyTuningBtn:hover {
                background-color: #4A8BF0;
            }
        """)
        self.btn_apply_tuning.clicked.connect(lambda: self.tuning_applied.emit(self.get_tuning_params()))
        layout.addWidget(self.btn_apply_tuning)

        btn_reset_l = QPushButton("Réinitialiser l'éclairage")
        btn_reset_l.setObjectName("SmallActionBtn")
        btn_reset_l.clicked.connect(self._reset_tuning_sliders)
        layout.addWidget(btn_reset_l)

        layout.addStretch(1)
        return self._wrap_in_scroll(w)

    def _reset_single_tuning_slider(self, which: str) -> None:
        """
        FR: Réinitialise individuellement l'un des curseurs d'éclairage (`fill`, `highlights`, `shadows`, `temp`).
        EN: Individually resets one of the lighting sliders (`fill`, `highlights`, `shadows`, `temp`).
        """
        if which == "fill":
            self.sldr_fill.setValue(0)
        elif which == "highlights":
            self.sldr_highlights.setValue(0)
        elif which == "shadows":
            self.sldr_shadows.setValue(0)
        elif which == "temp":
            self.sldr_temp.setValue(0)

    def _reset_tuning_sliders(self) -> None:
        """
        FR: Réinitialise tous les curseurs d'éclairage à zéro et émet `reset_lighting`.
        EN: Resets all lighting sliders to zero and emits `reset_lighting`.
        """
        self.reset_tuning_controls_silently()
        self.apply_effect.emit("reset_lighting", {})

    def _wrap_in_scroll(self, content_widget: QWidget) -> QScrollArea:
        """
        FR: Enveloppe un widget d'onglet dans une `QScrollArea` stylisée sans bordure.
        EN: Wraps a tab content widget inside a frameless styled `QScrollArea`.
        """
        content_widget.setObjectName("TabScrollContent")
        content_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sa = QScrollArea()
        sa.setObjectName("TabScrollArea")
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setWidget(content_widget)
        sa.viewport().setObjectName("TabScrollViewport")
        return sa

    def _create_effects_tab1(self) -> QWidget:
        """
        FR: Construit l'onglet 3 « Effets 1 » contenant les 12 filtres classiques de Picasa 3
            avec leurs miniatures d'aperçu en direct (`editpanel/fxthumbs`, `editpanel/fx1`..`editpanel/fx12`).
        EN: Builds Tab 3 "Effects 1" containing the 12 classic Picasa 3 filters
            with their live preview thumbnails (`editpanel/fxthumbs`, `editpanel/fx1`..`editpanel/fx12`).
        Ref: picasa3.exe @ 0x00568A08, 0x005D7C60, editpanel/fxthumbs
        """
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(6, 8, 6, 8)
        grid.setSpacing(6)

        effects = [
            ("🔍 Netteté", "sharpen", "Améliore le piqué et les contours (avec curseur de netteté)"),
            ("📜 Sépia", "sepia", "Tons chauds sépia d'époque"),
            ("⬛ N&B", "bw", "Noir et blanc classique argentique"),
            ("🌅 Réchauffer", "warmify", "Rehausse les tons rouges et ambrés"),
            ("🎞️ Grain photo", "grain", "Ajoute un grain argentique fin réglable"),
            ("🎨 Teinte", "tint", "Applique une dominante de couleur personnalisable"),
            ("🧪 Saturation", "saturation", "Ajuste l'intensité des couleurs"),
            ("🌫️ Flou doux", "soft_focus", "Flou artistique portrait autour d'un centre net"),
            ("✨ Halo", "glow", "Éclat lumineux féérique réglable"),
            ("🎯 N&B focalisé", "focal_bw", "Garde le centre en couleur et l'extérieur en N&B"),
            ("🌅 Dégradé", "graduated_tint", "Teinte dégradée crépusculaire réglable"),
            ("⬛ N&B filtré", "filtered_bw", "Noir et blanc avec filtre coloré optique (Ansel)"),
        ]

        self._effect_tiles_by_tab[2] = []
        for i, (label, action_id, tip) in enumerate(effects):
            btn = PicasaEffectTileButton(label, action_id, tip, w)
            btn.clicked.connect(lambda _, a=action_id: self._on_effect_button_clicked(a))
            grid.addWidget(btn, i // 3, i % 3)
            self._effect_tiles_by_tab[2].append(btn)

        return self._wrap_in_scroll(w)

    def _create_effects_tab2(self) -> QWidget:
        """
        FR: Construit l'onglet 4 « Effets 2 » (HDR, Orton, Lomo, Années 60, Traitement croisé, etc.)
            avec leurs miniatures d'aperçu en direct (`editpanel/fxthumbs`).
        EN: Builds Tab 4 "Effects 2" (HDR-ish, Orton, Lomo, 1960s, Cross Process, etc.)
            with their live preview thumbnails (`editpanel/fxthumbs`).
        Ref: picasa3.exe @ 0x00568A08, 0x005D7C60, editpanel/fxthumbs
        """
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(6, 8, 6, 8)
        grid.setSpacing(6)

        effects = [
            ("🌌 Simul. HDR", "hdr", "Simulateur d'imagerie à grande plage dynamique"),
            ("📷 Effet Orton", "orton", "Flou onirique et surexposition lumineuse"),
            ("📸 Lomo", "lomo", "Style lomographie saturé à vignettage"),
            ("📻 Années 60", "sixties", "Rendu rétro chaleureux et décoloré"),
            ("🔀 Trait. croisé", "cross_process", "Virage argentique chimique créatif"),
            ("🔮 Infrarouge", "infrared", "Feuillages blancs éclatants et ciel profond"),
            ("🎞️ Holga", "holga", "Esthétique appareil jouet plastique vintage"),
            ("🎬 Cinémascope", "cinemascope", "Bandes cinématographiques 2.39:1"),
            ("🌙 Vision nuit", "night_vision", "Monochrome vert phosphorescent et bruit"),
            ("🌡️ Thermique", "heat_map", "Spectre de fausses couleurs thermiques"),
            ("🖼️ Polaroid", "polaroid", "Cadre photo instantané Polaroid inclinable"),
            ("🎨 Postériser", "quantize_palette", "Réduction artistique du nombre de couleurs"),
        ]

        self._effect_tiles_by_tab[3] = []
        for i, (label, action_id, tip) in enumerate(effects):
            btn = PicasaEffectTileButton(label, action_id, tip, w)
            btn.clicked.connect(lambda _, a=action_id: self._on_effect_button_clicked(a))
            grid.addWidget(btn, i // 3, i % 3)
            self._effect_tiles_by_tab[3].append(btn)

        return self._wrap_in_scroll(w)

    def _create_effects_tab3(self) -> QWidget:
        """
        FR: Construit l'onglet 5 « Effets 3 » (Boost, Vignettage, Bichromie, Pixelliser, BD, Crayon, Cadres, etc.)
            avec leurs miniatures d'aperçu en direct (`editpanel/fxthumbs`).
        EN: Builds Tab 5 "Effects 3" (Boost, Vignette, Duo-Tone, Pixelate, Comic, Sketch, Borders, etc.)
            with their live preview thumbnails (`editpanel/fxthumbs`).
        Ref: picasa3.exe @ 0x00568A08, 0x005D7C60, editpanel/fxthumbs
        """
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(6, 8, 6, 8)
        grid.setSpacing(6)

        effects = [
            ("🚀 Boost", "boost", "Amplification dynamique de vibrance"),
            ("🔲 Vignettage", "vignette", "Assombrissement artistique des coins"),
            ("🎭 Bichromie", "two_tone", "Virage bicolore d'ombres et lumières"),
            ("🧱 Pixelliser", "pixelate", "Mosaïque géométrique de pixels"),
            ("🎯 Pix. focale", "focal_pixelate", "Pixelliser autour d'une zone centrale nette"),
            ("🔄 Inverser", "invert", "Inversion négative des couleurs"),
            ("🌀 Zoom focal", "focal_zoom", "Effet de vitesse et flou de zoom radial"),
            ("🌸 Adoucir", "soften", "Diffusion douce glamour"),
            ("💥 BD Comics", "comic", "Contours encrés et couleurs stylisées"),
            ("⚡ Néon", "neon", "Tracés lumineux fluorescents sur fond sombre"),
            ("✏️ Crayon", "pencil_sketch", "Croquis réaliste au crayon graphite"),
            ("🖼️ Bordure", "border", "Cadre photo élégant avec liseré intérieur"),
            ("🏛️ Cadre musée", "museum_matte", "Passe-partout de galerie avec biseau"),
            ("☁️ Ombre portée", "drop_shadow", "Ombre portée sur fond clair"),
            ("⬜ Coins arrondis", "rounded_edges", "Angles arrondis doux"),
            ("🔆 Contraste loc.", "local_contrast", "Renforcement des micro-détails"),
        ]

        self._effect_tiles_by_tab[4] = []
        for i, (label, action_id, tip) in enumerate(effects):
            btn = PicasaEffectTileButton(label, action_id, tip, w)
            btn.clicked.connect(lambda _, a=action_id: self._on_effect_button_clicked(a))
            grid.addWidget(btn, i // 3, i % 3)
            self._effect_tiles_by_tab[4].append(btn)

        return self._wrap_in_scroll(w)

    def _apply_effect_on_thumb(self, base_img: Image.Image, action_id: str) -> Image.Image:
        """
        FR: Applique un filtre Picasa 3 avec ses paramètres par défaut sur la miniature carrée 46x46
            pour le rendu de `editpanel/fxthumbs` (`editpanel/fx1`..`editpanel/fx12`).
        EN: Applies a Picasa 3 filter with its default parameters onto the 46x46 square thumbnail
            for rendering `editpanel/fxthumbs` (`editpanel/fx1`..`editpanel/fx12`).
        Ref: picasa3.exe @ 0x00568A08 (FUN_00568A08), 0x00C7E5A0
        """
        p = PicasaImageProcessor
        try:
            if action_id == "sharpen":
                return p.sharpen(base_img, 0.6)
            if action_id == "sepia":
                return p.sepia(base_img)
            if action_id == "bw":
                return p.black_and_white(base_img)
            if action_id == "warmify":
                return p.warmify(base_img)
            if action_id in ("grain", "film_grain"):
                return p.film_grain(base_img, 35.0)
            if action_id == "tint":
                return p.tint(base_img, (70, 130, 180), 0.5)
            if action_id == "saturation":
                return p.saturation(base_img, 1.4)
            if action_id == "soft_focus":
                return p.soft_focus(base_img, 0.35, 0.55)
            if action_id == "glow":
                return p.glow(base_img, 0.5, 4.0)
            if action_id == "focal_bw":
                return p.focal_bw(base_img, 0.35, 0.40)
            if action_id == "graduated_tint":
                return p.graduated_tint(base_img, (255, 140, 50), 0.5, 0.55)
            if action_id == "filtered_bw":
                return p.filtered_bw(base_img, (255, 85, 85))
            if action_id == "hdr":
                return p.hdr_simulator(base_img, 50.0, 50.0, 100.0)
            if action_id == "orton":
                return p.orton(base_img, 50.0, 50.0, 50.0)
            if action_id == "lomo":
                return p.lomo(base_img, 50.0, 0.0)
            if action_id == "sixties":
                return p.sixties(base_img, 20.0)
            if action_id == "cross_process":
                return p.cross_process(base_img, 0.0)
            if action_id == "infrared":
                return p.infrared(base_img, 20.0, 0.0)
            if action_id == "holga":
                return p.holga(base_img, 60.0, 25.0, 0.0)
            if action_id == "cinemascope":
                return p.cinemascope(base_img, 0.0, 0.0)
            if action_id == "night_vision":
                return p.night_vision(base_img, 20.0, 0.0, (87, 204, 41))
            if action_id == "heat_map":
                return p.heat_map(base_img, 0.0, 0.0)
            if action_id == "polaroid":
                return p.polaroid(base_img, 5.0)
            if action_id == "quantize_palette":
                return p.quantize_palette(base_img, 6)
            if action_id == "boost":
                return p.boost(base_img, 100.0)
            if action_id == "vignette":
                return p.vignette(base_img, 0.5, 0.25, (0, 0, 0))
            if action_id == "two_tone":
                return p.two_tone(base_img, 0.0, 20.0, 0.0, (40, 20, 90), (255, 220, 130))
            if action_id == "pixelate":
                return p.pixelate(base_img, 6, 0.0)
            if action_id == "focal_pixelate":
                return p.focal_pixelate(base_img, 6.0, 0.35, 0.5, 0.5)
            if action_id == "invert":
                return p.invert(base_img)
            if action_id == "focal_zoom":
                return p.focal_zoom(base_img, 0.30, 0.35, 0.5, 0.5)
            if action_id == "soften":
                return p.soften(base_img, 60.0, 0.0)
            if action_id == "comic":
                return p.comic(base_img, 50.0, 50.0)
            if action_id == "neon":
                return p.neon(base_img, (0, 240, 255), 0.0)
            if action_id == "pencil_sketch":
                return p.pencil_sketch(base_img, 2.0, 100.0)
            if action_id == "border":
                return p.border(base_img, 10.0, 4.0, 0.0, (0, 0, 0), (255, 255, 255))
            if action_id == "museum_matte":
                return p.museum_matte(base_img, 18.0, 3.0, (255, 255, 255), (30, 30, 30))
            if action_id == "drop_shadow":
                return p.drop_shadow(base_img, 4.0, 90.0, 10.0, 30.0, (255, 255, 255))
            if action_id == "rounded_edges":
                return p.rounded_edges(base_img, 18.0, 0.0, (255, 255, 255))
            if action_id == "local_contrast":
                return p.local_contrast(base_img, 8.0, 2.0, 0.0)
        except Exception:
            pass
        return base_img

    @staticmethod
    def _pil_thumb_to_qpixmap(img: Image.Image) -> QPixmap:
        """
        FR: Convertit une miniature PIL en QPixmap pour l'affichage dans `PicasaEffectTileButton`.
        EN: Converts a PIL thumbnail to QPixmap for display in `PicasaEffectTileButton`.
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        if img.size != (46, 46):
            img = img.resize((46, 46), Image.Resampling.BILINEAR)
        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888).copy()
        return QPixmap.fromImage(qimg)

    def _refresh_effect_tiles_for_tab(self, tab_idx: int) -> None:
        """
        FR: Génère et assigne les miniatures d'effets pour l'onglet actif (2, 3 ou 4) si une photo est ouverte.
        EN: Generates and assigns effect thumbnails for the active tab (2, 3, or 4) when a photo is open.
        Ref: picasa3.exe @ 0x00568A08 (FUN_00568A08, editpanel/fxthumbs)
        """
        tiles = self._effect_tiles_by_tab.get(tab_idx, [])
        if not tiles:
            return
        if self._base_fx_thumb is None:
            for tile in tiles:
                tile.set_preview_pixmap(None)
            return
        for tile in tiles:
            aid = tile.action_id
            pix = self._fx_preview_cache.get(aid)
            if pix is None:
                fx_img = self._apply_effect_on_thumb(self._base_fx_thumb, aid)
                pix = self._pil_thumb_to_qpixmap(fx_img)
                self._fx_preview_cache[aid] = pix
            tile.set_preview_pixmap(pix)

    def _on_main_tab_changed(self, tab_idx: int) -> None:
        """
        FR: Rafraîchit les miniatures d'aperçu d'effets lorsqu'un onglet d'effets (Effets 1/2/3) devient actif.
        EN: Refreshes effect preview thumbnails when an effects tab (Effects 1/2/3) becomes active.
        """
        if tab_idx in (2, 3, 4):
            self._refresh_effect_tiles_for_tab(tab_idx)

    def set_image(self, img: Optional[Image.Image]) -> None:
        """
        FR: Met à jour l'histogramme en direct et les miniatures d'aperçu des effets (`editpanel/fxthumbs`)
            avec l'image actuellement affichée.
        EN: Updates the live histogram and the effect preview thumbnails (`editpanel/fxthumbs`)
            with the currently displayed image.
        Ref: picasa3.exe @ 0x00568A08 (FUN_00568A08), editpanel/fxthumbs
        """
        self.histogram_widget.set_image(img)
        self._fx_preview_cache.clear()
        if img is None:
            self._base_fx_thumb = None
            for tab_idx in (2, 3, 4):
                self._refresh_effect_tiles_for_tab(tab_idx)
            return
        try:
            # Recadrage carré centré 46x46 pour les miniatures d'effets (comme picasa3.exe @ 0x00568A08)
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            sq = img.crop((left, top, left + side, top + side))
            if sq.mode != "RGB":
                sq = sq.convert("RGB")
            self._base_fx_thumb = sq.resize((46, 46), Image.Resampling.BILINEAR)
        except Exception:
            self._base_fx_thumb = None

        # Met à jour immédiatement l'onglet d'effets uniquement s'il est actuellement ouvert
        cur_tab = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        if cur_tab in (2, 3, 4):
            self._refresh_effect_tiles_for_tab(cur_tab)

    def set_photo_metadata(self, file_path: str) -> None:
        """
        FR: Met à jour les informations d'appareil photo et EXIF.
        EN: Updates the camera and EXIF metadata information card.
        """
        self.camera_info_card.set_photo_path(file_path)

    def _create_video_subpanel(self) -> QWidget:
        """
        FR: Construit le sous-panneau affiché lorsqu'une vidéo est ouverte dans la vue One-Up.
        EN: Builds the subpanel displayed when a video is opened in One-Up view.
        Ref: STRINGRES_FR.XML:640
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(14)

        icon_lbl = QLabel("🎬")
        icon_lbl.setStyleSheet("font-size: 32px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel("Lecture Vidéo")
        title_lbl.setObjectName("SubpanelTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        # Ref: STRINGRES_FR.XML:640
        notice_lbl = QLabel(
            "Notez que les effets ne peuvent pas être appliqués aux vidéos."
        )
        notice_lbl.setWordWrap(True)
        notice_lbl.setObjectName("SubpanelDesc")
        notice_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(notice_lbl)

        layout.addStretch(1)
        return w

    def set_video_mode(self, is_video: bool) -> None:
        """
        FR: Adapte le volet d'édition selon que le média actif est une vidéo ou une photo.
        EN: Adapts the editing panel depending on whether the active media is a video or a photo.
        Ref: STRINGRES_FR.XML:640
        """
        self.btn_undo.setVisible(not is_video)
        self.btn_redo.setVisible(not is_video)
        self.btn_save.setVisible(not is_video)
        if is_video:
            self.stack.setCurrentWidget(self.video_subpanel)
        else:
            self.stack.setCurrentIndex(0)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs PicasaStyle au panneau de retouches.
        EN: Dynamically applies the PicasaStyle color theme to the editing panel.
        """
        if style is None:
            style = PicasaStyle.instance()
        self.style = style
        panel_bg = style.alist_catcolor.name() if style.is_dark else style.drawer_bgcolor.name()
        pane_bg = style.alist_bgcolor.name() if style.is_dark else style.window_bgcolor.name()
        tab_bg = style.tray_bgcolor.name() if style.is_dark else style.topbar_grad_end.name()
        border_col = style.splitter_color.name() if style.is_dark else style.topbar_border_color.name()
        btn_bg = style.topbar_btn_bg_start.name()
        btn_hover = style.topbar_btn_bg_end.name()
        btn_border = style.topbar_btn_border.name()
        txt_col = style.alist_textcolor.name()
        sub_col = style.alayout_subtitleColor.name()
        accent = style.accent_color.name()
        input_bg = style.window_bgcolor.name() if style.is_dark else "#FFFFFF"

        self.setStyleSheet(f"""
            QWidget#EditPanelRoot {{
                background-color: {panel_bg};
                border-right: 1px solid {border_col};
            }}
            QScrollArea#TabScrollArea {{
                background-color: {pane_bg};
                border: none;
            }}
            QWidget#TabScrollViewport, QWidget#TabScrollContent {{
                background-color: {pane_bg};
            }}
            QPushButton#BackBtn {{
                background-color: {accent};
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                border: 1px solid {accent};
                text-align: left;
            }}
            QPushButton#BackBtn:hover {{
                background-color: {style.accent_color.lighter(115).name()};
            }}
            QPushButton#ToolBtn, QToolButton#ToolBtn {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 5px 4px;
                font-size: 10px;
                font-weight: bold;
                color: {txt_col};
                text-align: center;
            }}
            QPushButton#ToolBtn:hover, QToolButton#ToolBtn:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
            QPushButton#ToolBtn:pressed, QToolButton#ToolBtn:pressed {{
                background-color: {tab_bg};
            }}
            QPushButton#SmallActionBtn {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                color: {txt_col};
            }}
            QPushButton#SmallActionBtn:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
            QPushButton#SmallActionBtn:checked {{
                background-color: {accent};
                color: #FFFFFF;
                border-color: {accent};
            }}
            QPushButton#HistModeBtn {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 2px;
                font-size: 9px;
                padding: 0;
                color: {txt_col};
            }}
            QPushButton#HistModeBtn:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
            QPushButton#LinkBtn {{
                background-color: transparent;
                color: {accent};
                border: none;
                text-align: left;
                font-size: 11px;
                text-decoration: underline;
                padding: 4px 0;
            }}
            QPushButton#LinkBtn:hover {{
                color: {style.accent_color.lighter(120).name()};
            }}
            QTabWidget::pane {{
                border: 1px solid {border_col};
                background-color: {pane_bg};
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {tab_bg};
                border: 1px solid {border_col};
                min-width: 44px;
                min-height: 23px;
                padding: 3px 4px;
                font-size: 10px;
                font-weight: bold;
                color: {txt_col};
            }}
            QTabBar::tab:selected {{
                background-color: {pane_bg};
                border-bottom-color: {pane_bg};
                color: {txt_col};
            }}
            QLabel {{
                font-size: 11px;
                color: {txt_col};
                background: transparent;
            }}
            QLabel#SubpanelTitle {{
                font-size: 13px;
                font-weight: bold;
                color: {txt_col};
            }}
            QLabel#SubpanelDesc {{
                font-size: 11px;
                color: {sub_col};
            }}
            QLabel#SubpanelValue {{
                font-size: 11px;
                font-weight: bold;
                color: {accent};
            }}
            QLabel#SubpanelTick {{
                font-size: 9px;
                color: {sub_col};
            }}
            QLabel#HistHeaderLabel, QLabel#FillLightLabel {{
                font-size: 10px;
                font-weight: bold;
                color: {sub_col};
            }}
            QFrame#TabSeparator {{
                color: {border_col};
            }}
            QRadioButton, QCheckBox {{
                color: {txt_col};
                background: transparent;
            }}
            QLineEdit#SubpanelLineEdit {{
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 5px 8px;
                background-color: {input_bg};
                color: {txt_col};
                font-size: 12px;
            }}
            QLineEdit#SubpanelLineEdit:focus {{
                border-color: {accent};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: {btn_border};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
        """)
        if hasattr(self, "histogram_widget"):
            self.histogram_widget.apply_style(style)
        if hasattr(self, "camera_info_card"):
            self.camera_info_card.apply_style(style)
        self.update()

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes et info-bulles de l'interface du volet d'édition selon la langue active.
        EN: Updates the editing panel UI strings and tooltips according to the active language.
        """
        rm = PicasaResourceManager.get()
        back_lbl = rm.get_xml_string("editpanel/albumview", "Retour à la photothèque")
        self.btn_back.setText(f"◀ {back_lbl}")
        undo_lbl = rm.get_xml_string("editpanel/filter_undo", "Annuler")
        redo_lbl = rm.get_xml_string("editpanel/filter_redo", "Rétablir")
        self.btn_undo.setText(f"↶ {undo_lbl}")
        self.btn_redo.setText(f"↷ {redo_lbl}")
        save_lbl = rm.get_xml_string("editpanel/writetodisk", "Enregistrer sur le disque")
        self.btn_save.setText(f"💾 {save_lbl}")
        if hasattr(self, "tabs"):
            self.tabs.setTabToolTip(0, rm.get_xml_string("editpanel/tab1.tooltip", "Retouches courantes"))
            self.tabs.setTabToolTip(1, rm.get_xml_string("editpanel/tab2.tooltip", "Retouches précises de l'éclairage et des couleurs"))
            self.tabs.setTabToolTip(2, rm.get_xml_string("editpanel/tab3.tooltip", "Traitement des images en toute simplicité"))
            self.tabs.setTabToolTip(3, rm.get_xml_string("editpanel/tab4.tooltip", "Un traitement des images encore plus simple"))
            self.tabs.setTabToolTip(4, rm.get_xml_string("editpanel/tab5.tooltip", "Un traitement des images encore plus simple"))
        if hasattr(self, "_basic_tool_buttons"):
            xml_tool_keys = {
                "crop": ("editpanel/crop", "Recadrer", "editpanel/crop.tooltip", "Recadrer l'image"),
                "straighten": ("editpanel/horizonadjust", "Redresser", "editpanel/horizonadjust.tooltip", "Redresser une photo penchée"),
                "redeye": ("editpanel/redeye", "Yeux rouges", "editpanel/redeye.tooltip", "Corriger les yeux rouges"),
                "lucky": ("editpanel/enhance", "J'ai de la chance", "editpanel/enhance.tooltip", "Corriger automatiquement l'éclairage et la couleur"),
                "autocontrast": ("editpanel/autolighting", "Contraste auto", "editpanel/autolighting.tooltip", "Corriger l'exposition sans affecter les couleurs"),
                "autocolor": ("editpanel/autocolor", "Couleur auto", "editpanel/autocolor.tooltip", "Supprimer la dominante de couleur tout en préservant l'exposition"),
                "retouch": ("editpanel/retouch", "Retoucher", "editpanel/retouch.tooltip", "Éliminer les imperfections et améliorer la qualité de la photo"),
                "text": ("editpanel/edittext", "Texte", "editpanel/edittext.tooltip", "Superposer du texte sur votre image"),
            }
            for act_id, (lbl_key, lbl_def, tip_key, tip_def) in xml_tool_keys.items():
                btn = self._basic_tool_buttons.get(act_id)
                if btn is not None:
                    btn.setText(rm.get_xml_string(lbl_key, lbl_def))
                    btn.setToolTip(rm.get_xml_string(tip_key, tip_def))
        if hasattr(self, "crop_subpanel"):
            self.crop_subpanel.lbl_title.setText(rm.get_xml_string("editpanel/crop_label", "Recadrer la photo"))
            self.crop_subpanel.lbl_desc.setText(rm.get_xml_string(
                "editpanel/croptext",
                "Sélectionnez une dimension ci-dessous et faites glisser le pointeur sur l'image pour sélectionner la partie à recadrer."
            ))
            self.crop_subpanel.btn_apply.setText(rm.get_xml_string("editpanel/cropapply", "Appliquer"))
            self.crop_subpanel.btn_discard.setText(rm.get_xml_string("editpanel/cropdiscard", "Réinitialiser"))
            self.crop_subpanel.btn_cancel.setText(rm.get_xml_string("editpanel/cropcancel", "Annuler"))

