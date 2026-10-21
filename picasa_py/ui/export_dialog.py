"""
FR : Boîte de dialogue et moteur d'exportation d'images de Picasa 3.
EN : Picasa Export Dialog and Processing Engine.
Reproduces CExportPrefsDialog and CImageOutput faithfully.

Ref: picasa3.exe @ 0x00738D00 (CExportPrefsDialog)
Ref: picasa3.exe @ 0x008AF994 (CExportPrefsDialog strings and settings)
Ref: picasa3.exe @ 0x008B02E6 (CImageOutput::exportprog "Exporting to folder")
Ref: export.fen / EXPORT_FR.XML
"""

from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QRadioButton, QButtonGroup,
    QComboBox, QSlider, QFileDialog, QProgressDialog, QMessageBox,
    QGroupBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread, QStandardPaths

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ini.parser import PicasaIniParser
from picasa_py.faces.facerect import decode_rect64_string


# Ref: export.fen <bind source="size" attr="title" list="320|480|640|800|1024|1200|1600"/>
EXPORT_SIZE_STEPS = [320, 480, 640, 800, 1024, 1200, 1600]

# Ref: export.fen <popup name="quality"> & EXPORT_FR.XML
QUALITY_PRESETS = {
    0: ("Automatique", 90, "Préserve la qualité d'origine de l'image."),
    1: ("Normal", 82, "Équilibre satisfaisant entre la qualité et la taille"),
    2: ("Maximum", 95, "Fichiers très volumineux, conservant la précision des détails"),
    3: ("Minimum", 65, "Fichier de taille minimale, perte de qualité"),
    4: ("Personnalisé", 80, "Qualité personnalisée")
}


@dataclass
class PicasaExportConfig:
    """
    FR : Configuration complète pour une tâche d'exportation.
    EN : Complete configuration for an image export task.
    """
    dest_path: str
    folder_name: str
    add_numbers: bool
    use_original_size: bool
    target_size: int
    quality: int
    use_watermark: bool
    watermark_text: str


class PicasaExportWorker(QThread):
    """
    FR : Moteur d'exportation d'images en arrière-plan (Ref: CImageOutput::exportprog).
    Applique les transformations non-destructives (.picasa.ini), le redimensionnement et le filigrane.
    EN : Background image export worker (Ref: CImageOutput::exportprog).
    Applies non-destructive edits (.picasa.ini), resizing, and watermarking.
    """
    progress = Signal(int, int, str)  # (current_idx, total_count, filename)
    finished = Signal(int, int, str)  # (success_count, error_count, output_dir)

    def __init__(self, items: List[str], config: PicasaExportConfig, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.items = items
        self.config = config
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        output_dir = Path(self.config.dest_path) / self.config.folder_name
        output_dir.mkdir(parents=True, exist_ok=True)

        total = len(self.items)
        success_count = 0
        error_count = 0

        # FR : Cache des parsers d'ini par dossier source
        # EN : Cache of INI parsers per source directory
        ini_cache = {}

        digits = max(2, len(str(total)))

        for i, src_path in enumerate(self.items):
            if self._is_cancelled:
                break

            src = Path(src_path)
            self.progress.emit(i + 1, total, src.name)

            try:
                from picasa_py.ui.image_processor import PicasaImageProcessor
                max_sz = (
                    self.config.target_size
                    if (not self.config.use_original_size and self.config.target_size > 0)
                    else 0
                )
                img = PicasaImageProcessor.load_transformed_image(str(src), max_size=max_sz)
                if img is None:
                    error_count += 1
                    continue

                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Filigrane (Watermark)
                if self.config.use_watermark and self.config.watermark_text.strip():
                    self._apply_watermark(img, self.config.watermark_text.strip())

                # Nom de fichier de destination
                if self.config.add_numbers:
                    prefix = f"{i + 1:0{digits}d}-"
                    dst_name = prefix + src.stem + ".jpg"
                else:
                    dst_name = src.stem + ".jpg"

                dst_path = output_dir / dst_name
                img.save(dst_path, "JPEG", quality=self.config.quality, optimize=True)
                success_count += 1

            except Exception:
                error_count += 1

        self.finished.emit(success_count, error_count, str(output_dir))

    def _apply_watermark(self, img: Image.Image, text: str) -> None:
        """
        FR : Appose le texte de filigrane en bas à droite avec ombre portée.
        EN : Draws the watermark text in the bottom-right corner with a drop shadow.
        """
        draw = ImageDraw.Draw(img)
        w, h = img.size

        font_size = max(12, int(h * 0.035))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        margin = max(10, int(font_size * 0.6))
        x = w - text_w - margin
        y = h - text_h - margin

        draw.text((x + 1, y + 1), text, fill=(0, 0, 0, 160), font=font)
        draw.text((x, y), text, fill=(240, 240, 240, 220), font=font)


class PicasaExportDialog(QDialog):
    """
    FR : Boîte de dialogue officielle d'exportation vers un dossier.
    EN : Official Picasa 3 Export to Folder dialog.
    Ref: export.fen, EXPORT_FR.XML, CExportPrefsDialog
    """

    def __init__(
        self,
        item_paths: List[str],
        default_folder_name: str = "Exported",
        style: Optional[PicasaStyle] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.item_paths = item_paths
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(self.res_mgr.get_xml_string("export/window1.title", "Exporter vers le dossier"))
        self.setFixedWidth(460)

        # FR : Récupération du dossier "Mes Images/Picasa/Exports" par défaut
        # EN : Retrieve default "Pictures/Picasa/Exports" folder
        pictures_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        default_export_base = os.path.join(pictures_dir, "Picasa", "Exports")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # 1. Emplacement d'exportation (Ref: export/labelgroup2.title)
        self.grp_loc = QGroupBox(self.res_mgr.get_xml_string("export/labelgroup2.title", "Emplacement d'exportation :"))
        lay_loc = QHBoxLayout(self.grp_loc)
        self.edit_loc = QLineEdit(default_export_base)
        self.btn_browse = QPushButton(self.res_mgr.get_xml_string("export/changeloc.title", "Parcourir..."))
        self.btn_browse.clicked.connect(self._browse_location)
        lay_loc.addWidget(self.edit_loc)
        lay_loc.addWidget(self.btn_browse)
        main_layout.addWidget(self.grp_loc)

        # 2. Nom du dossier exporté (Ref: export/labelgroup6.title)
        self.grp_name = QGroupBox(self.res_mgr.get_xml_string("export/labelgroup6.title", "Nom du dossier exporté :"))
        lay_name = QVBoxLayout(self.grp_name)
        self.edit_name = QLineEdit(default_folder_name)
        self.chk_numbers = QCheckBox(self.res_mgr.get_xml_string("export/addnumbers.title", "Insérez des chiffres dans le nom des fichiers pour conserver l'ordre."))
        self.chk_numbers.setChecked(False)
        lay_name.addWidget(self.edit_name)
        lay_name.addWidget(self.chk_numbers)
        main_layout.addWidget(self.grp_name)

        # 3. Taille de l'image (Ref: export/labelgroup9.title)
        self.grp_size = QGroupBox(self.res_mgr.get_xml_string("export/labelgroup9.title", "Taille de l'image :"))
        lay_size = QVBoxLayout(self.grp_size)

        self.radio_orig = QRadioButton(self.res_mgr.get_xml_string("export/radio11.title", "Utiliser la taille d'origine"))
        self.radio_resize = QRadioButton(self.res_mgr.get_xml_string("export/radio12.title", "Redimensionner au format :"))
        self.radio_resize.setChecked(True)

        size_btn_grp = QButtonGroup(self)
        size_btn_grp.addButton(self.radio_orig)
        size_btn_grp.addButton(self.radio_resize)

        lay_size.addWidget(self.radio_orig)
        lay_size.addWidget(self.radio_resize)

        size_ctrl_lay = QHBoxLayout()
        size_ctrl_lay.setContentsMargins(20, 0, 0, 0)
        self.edit_size = QLineEdit("800")
        self.edit_size.setFixedWidth(50)
        self.lbl_px = QLabel(self.res_mgr.get_xml_string("export/label18.title", "pixels"))
        self.lbl_px.setFixedWidth(40)

        # Slider avec 7 crans (Ref: <slider min="0" max="6" ticks="7" name="size"/>)
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(0, len(EXPORT_SIZE_STEPS) - 1)
        self.slider_size.setValue(3)  # 800 px
        self.slider_size.valueChanged.connect(self._on_slider_size_changed)
        self.edit_size.textChanged.connect(self._on_edit_size_changed)

        size_ctrl_lay.addWidget(self.edit_size)
        size_ctrl_lay.addWidget(self.lbl_px)
        size_ctrl_lay.addWidget(self.slider_size)
        lay_size.addLayout(size_ctrl_lay)

        self.radio_orig.toggled.connect(self._update_size_enabled)
        self.radio_resize.toggled.connect(self._update_size_enabled)
        main_layout.addWidget(self.grp_size)

        # 4. Qualité d'image (Ref: export/labelgroup20.title)
        self.grp_qual = QGroupBox(self.res_mgr.get_xml_string("export/labelgroup20.title", "Qualité d'image :"))
        lay_qual = QVBoxLayout(self.grp_qual)

        top_qual_lay = QHBoxLayout()
        self.combo_qual = QComboBox()
        for i in range(5):
            title, _, _ = QUALITY_PRESETS[i]
            xml_title = self.res_mgr.get_xml_string(f"export/item{23+i}.title", title)
            self.combo_qual.addItem(xml_title)
        self.combo_qual.setCurrentIndex(1)  # Normal par défaut

        self.lbl_qual_desc = QLabel(QUALITY_PRESETS[1][2])

        top_qual_lay.addWidget(self.combo_qual)
        top_qual_lay.addWidget(self.lbl_qual_desc, 1)
        lay_qual.addLayout(top_qual_lay)

        # Slider de qualité pour le mode Personnalisé (Ref: qualslider)
        self.slider_qual = QSlider(Qt.Orientation.Horizontal)
        self.slider_qual.setRange(20, 100)
        self.slider_qual.setValue(80)
        self.slider_qual.setVisible(False)
        lay_qual.addWidget(self.slider_qual)

        self.combo_qual.currentIndexChanged.connect(self._on_quality_changed)
        main_layout.addWidget(self.grp_qual)

        # 5. Filigrane (Ref: export/labelgroup39.title)
        self.grp_wm = QGroupBox(self.res_mgr.get_xml_string("export/labelgroup39.title", "Filigrane :"))
        lay_wm = QVBoxLayout(self.grp_wm)
        self.chk_watermark = QCheckBox(self.res_mgr.get_xml_string("export/usewatermark.title", "Ajouter un filigrane"))
        self.chk_watermark.setChecked(False)

        self.edit_watermark = QLineEdit()
        self.edit_watermark.setEnabled(False)
        self.edit_watermark.setPlaceholderText("Ex: © Mon Nom")

        self.lbl_wm_desc = QLabel(self.res_mgr.get_xml_string(
            "export/label44.title",
            "Apposez votre nom, un domaine Web ou un copyright sur vos photos."
        ))

        self.chk_watermark.toggled.connect(self.edit_watermark.setEnabled)

        lay_wm.addWidget(self.chk_watermark)
        lay_wm.addWidget(self.edit_watermark)
        lay_wm.addWidget(self.lbl_wm_desc)
        main_layout.addWidget(self.grp_wm)

        # 6. Boutons Accepter / Annuler (Ref: buttongroup)
        lay_btns = QHBoxLayout()
        lay_btns.addStretch(1)

        self.btn_export = QPushButton(self.res_mgr.get_xml_string("export/export.title", "Exporter"))
        self.btn_export.setObjectName("AcceptBtn")
        self.btn_export.clicked.connect(self.accept)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("export/button47.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)

        lay_btns.addWidget(self.btn_export)
        lay_btns.addWidget(self.btn_cancel)
        main_layout.addLayout(lay_btns)

        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème PicasaStyle à la boîte de dialogue d'exportation.
        EN : Dynamically applies the PicasaStyle theme to the Export dialog.
        """
        self.style = style or PicasaStyle.instance()
        s = self.style
        dlg_bg = s.window_bgcolor.name() if s.is_dark else "#ECE9D8"
        txt_col = s.alist_textcolor.name() if s.is_dark else "#000000"
        sub_col = s.alayout_subtitleColor.name() if s.is_dark else "#555555"
        border_col = s.splitter_color.name() if s.is_dark else "#C0BCB4"
        input_bg = s.thumb_card_bgcolor.name() if s.is_dark else "#FFFFFF"
        input_border = s.topbar_btn_border.name() if s.is_dark else "#7F9DB9"
        btn_bg = s.topbar_btn_bg_start.name() if s.is_dark else "#F8F7F4"
        btn_hover = s.topbar_btn_bg_end.name() if s.is_dark else "#EBF2F9"
        accent = s.accent_color.name()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {txt_col};
                font-size: 11px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {border_col};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                color: {txt_col};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                color: {txt_col};
            }}
            QLabel, QCheckBox, QRadioButton {{
                color: {txt_col};
                font-size: 11px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {txt_col};
                border: 1px solid {input_border};
                border-radius: 3px;
                padding: 4px 14px;
                font-size: 11px;
                min-width: 75px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: {accent};
                color: {txt_col};
            }}
            QPushButton#AcceptBtn {{
                background-color: {accent};
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid {accent};
            }}
            QPushButton#AcceptBtn:hover {{
                background-color: {s.accent_color.lighter(115).name()};
                color: #FFFFFF;
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {txt_col};
                border: 1px solid {input_border};
                padding: 3px;
                font-size: 11px;
            }}
            QComboBox {{
                background-color: {input_bg};
                color: {txt_col};
                border: 1px solid {input_border};
                padding: 2px 4px;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {txt_col};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                font-size: 9pt;
            }}
        """)
        if hasattr(self, "lbl_qual_desc"):
            self.lbl_qual_desc.setStyleSheet(f"color: {sub_col}; font-style: italic;")
        if hasattr(self, "lbl_wm_desc"):
            self.lbl_wm_desc.setStyleSheet(f"color: {sub_col}; font-size: 10px;")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les libellés de la boîte de dialogue d'exportation selon la langue active.
        EN : Updates the Export dialog labels according to the active language.
        """
        self.setWindowTitle(self.res_mgr.get_xml_string("export/window1.title", "Exporter vers le dossier"))
        self.grp_loc.setTitle(self.res_mgr.get_xml_string("export/labelgroup2.title", "Emplacement d'exportation :"))
        self.btn_browse.setText(self.res_mgr.get_xml_string("export/changeloc.title", "Parcourir..."))
        self.grp_name.setTitle(self.res_mgr.get_xml_string("export/labelgroup6.title", "Nom du dossier exporté :"))
        self.chk_numbers.setText(self.res_mgr.get_xml_string("export/addnumbers.title", "Insérez des chiffres dans le nom des fichiers pour conserver l'ordre."))
        self.grp_size.setTitle(self.res_mgr.get_xml_string("export/labelgroup9.title", "Taille de l'image :"))
        self.radio_orig.setText(self.res_mgr.get_xml_string("export/radio11.title", "Utiliser la taille d'origine"))
        self.radio_resize.setText(self.res_mgr.get_xml_string("export/radio12.title", "Redimensionner au format :"))
        self.lbl_px.setText(self.res_mgr.get_xml_string("export/label18.title", "pixels"))
        self.grp_qual.setTitle(self.res_mgr.get_xml_string("export/labelgroup20.title", "Qualité d'image :"))
        for i in range(min(5, self.combo_qual.count())):
            title, _, _ = QUALITY_PRESETS[i]
            self.combo_qual.setItemText(i, self.res_mgr.get_xml_string(f"export/item{23+i}.title", title))
        self._on_quality_changed(self.combo_qual.currentIndex())
        self.grp_wm.setTitle(self.res_mgr.get_xml_string("export/labelgroup39.title", "Filigrane :"))
        self.chk_watermark.setText(self.res_mgr.get_xml_string("export/usewatermark.title", "Ajouter un filigrane"))
        self.lbl_wm_desc.setText(self.res_mgr.get_xml_string(
            "export/label44.title",
            "Apposez votre nom, un domaine Web ou un copyright sur vos photos."
        ))
        self.btn_export.setText(self.res_mgr.get_xml_string("export/export.title", "Exporter"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("export/button47.title", "Annuler"))

    def _browse_location(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination", self.edit_loc.text())
        if path:
            self.edit_loc.setText(path)

    def _on_slider_size_changed(self, idx: int) -> None:
        if 0 <= idx < len(EXPORT_SIZE_STEPS):
            self.edit_size.setText(str(EXPORT_SIZE_STEPS[idx]))

    def _on_edit_size_changed(self, text: str) -> None:
        try:
            val = int(text)
            if val in EXPORT_SIZE_STEPS:
                self.slider_size.setValue(EXPORT_SIZE_STEPS.index(val))
        except ValueError:
            pass

    def _update_size_enabled(self) -> None:
        enabled = self.radio_resize.isChecked()
        self.edit_size.setEnabled(enabled)
        self.slider_size.setEnabled(enabled)

    def _on_quality_changed(self, idx: int) -> None:
        preset = QUALITY_PRESETS.get(idx, QUALITY_PRESETS[1])
        xml_desc = self.res_mgr.get_xml_string(f"export/label{30+idx}.title", preset[2])
        self.lbl_qual_desc.setText(xml_desc)
        self.slider_qual.setVisible(idx == 4)

    def get_config(self) -> PicasaExportConfig:
        """
        FR : Retourne la configuration validée pour l'exportation.
        EN : Returns the validated export configuration.
        """
        use_orig = self.radio_orig.isChecked()
        try:
            size_val = int(self.edit_size.text())
        except ValueError:
            size_val = 800

        q_idx = self.combo_qual.currentIndex()
        if q_idx == 4:
            qual_val = self.slider_qual.value()
        else:
            qual_val = QUALITY_PRESETS.get(q_idx, (None, 82, None))[1]

        return PicasaExportConfig(
            dest_path=self.edit_loc.text().strip(),
            folder_name=self.edit_name.text().strip() or "Exported",
            add_numbers=self.chk_numbers.isChecked(),
            use_original_size=use_orig,
            target_size=size_val,
            quality=qual_val,
            use_watermark=self.chk_watermark.isChecked(),
            watermark_text=self.edit_watermark.text().strip()
        )

