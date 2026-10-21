"""
FR : Boîte de dialogue de création de poster pour PyCasa (CPosterDialog / poster.fen).
Découpe une photo sur une grille de pages imprimables avec marges de chevauchement.
EN : Poster Maker Dialog for PyCasa (CPosterDialog / poster.fen).
Splits a photo across a grid of printable pages with tile overlapping margins.

Ref: picasa3.exe @ poster.fen, POSTER.XML
Ref: ui/resources/xml/POSTER_FR.XML
"""

from __future__ import annotations
import os
import sys
import math
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QFileDialog, QMessageBox, QFrame,
    QWidget
)
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QImage, QPaintEvent

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PosterPreviewWidget(QWidget):
    """
    FR : Aperçu visuel de la photo découpée en tuiles de poster.
    EN : Visual preview of the photo split into poster tiles.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.pixmap: Optional[QPixmap] = None
        self.grid_size: int = 2
        self.setFixedHeight(180)

    def set_photo(self, photo_path: str, grid_size: int) -> None:
        self.grid_size = grid_size
        if os.path.exists(photo_path):
            from picasa_py.ui.image_processor import PicasaImageProcessor
            img = PicasaImageProcessor.load_transformed_image(photo_path, max_size=800)
            self.pixmap = PicasaImageProcessor.pil_to_qpixmap(img) if img is not None else QPixmap(photo_path)
        else:
            self.pixmap = None
        self.update()

    def set_grid_size(self, grid_size: int) -> None:
        self.grid_size = grid_size
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fond sombre
        painter.fillRect(self.rect(), QColor("#303236"))

        if not self.pixmap or self.pixmap.isNull():
            painter.setPen(QColor("#AAAAAA"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucune image sélectionnée")
            return

        # Cadre centré pour l'image
        target_size = self.pixmap.scaled(
            self.width() - 20, self.height() - 20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        x = (self.width() - target_size.width()) // 2
        y = (self.height() - target_size.height()) // 2
        img_rect = QRect(x, y, target_size.width(), target_size.height())

        painter.drawPixmap(x, y, target_size)

        # Dessin du quadrillage des feuilles
        painter.setPen(QPen(QColor("#00FFCC"), 1.5, Qt.PenStyle.DashLine))
        step_x = img_rect.width() / self.grid_size
        step_y = img_rect.height() / self.grid_size

        for c in range(1, self.grid_size):
            line_x = int(img_rect.left() + c * step_x)
            painter.drawLine(line_x, img_rect.top(), line_x, img_rect.bottom())

        for r in range(1, self.grid_size):
            line_y = int(img_rect.top() + r * step_y)
            painter.drawLine(img_rect.left(), line_y, img_rect.right(), line_y)

        # Cadre extérieur blanc
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawRect(img_rect)


class PicasaPosterDialog(QDialog):
    """
    FR : Dialogue de création de poster géant (poster.fen).
    EN : Giant poster creation dialog (poster.fen).
    """

    def __init__(
        self,
        photo_path: str,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.photo_path = photo_path
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(self.res_mgr.get_xml_string("poster/window1.title", "Paramètres de poster"))
        self.setFixedWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Conseil officiel (Ref: poster/label2.title)
        self.tip_lbl = QLabel(
            f"<b>Conseil :</b> {self.res_mgr.get_xml_string('poster/label2.title', 'si vous ne voulez pas ajuster la photo, recadrez-la au format du papier.')}"
        )
        self.tip_lbl.setWordWrap(True)
        layout.addWidget(self.tip_lbl)

        # 2. Aperçu du quadrillage
        self.preview = PosterPreviewWidget(self)
        self.preview.set_photo(photo_path, 2)
        layout.addWidget(self.preview)

        # 3. Taille de poster (Facteur d'agrandissement)
        self.lbl_factor = QLabel(self.res_mgr.get_xml_string("poster/labelgroup3.title", "Taille de poster :"))
        layout.addWidget(self.lbl_factor)
        self.combo_factor = QComboBox()
        factors = [
            ("200 % (2 × 2 = 4 pages)", 2),
            ("300 % (3 × 3 = 9 pages)", 3),
            ("400 % (4 × 4 = 16 pages)", 4),
            ("500 % (5 × 5 = 25 pages)", 5),
            ("600 % (6 × 6 = 36 pages)", 6),
            ("700 % (7 × 7 = 49 pages)", 7),
            ("800 % (8 × 8 = 64 pages)", 8),
            ("900 % (9 × 9 = 81 pages)", 9),
            ("1000 % (10 × 10 = 100 pages)", 10),
        ]
        for label, grid_sz in factors:
            self.combo_factor.addItem(label, grid_sz)
        self.combo_size = self.combo_factor
        self.combo_factor.currentIndexChanged.connect(self._on_factor_changed)
        layout.addWidget(self.combo_factor)

        # 4. Format du papier
        self.lbl_paper = QLabel(self.res_mgr.get_xml_string("poster/labelgroup14.title", "Format du papier :"))
        layout.addWidget(self.lbl_paper)
        self.combo_paper = QComboBox()
        self.combo_paper.addItems(["A4 (210 × 297 mm)", "Lettre US (8.5 × 11 pouces)", "A3 (297 × 420 mm)"])
        layout.addWidget(self.combo_paper)

        # 5. Chevauchement des mosaïques (Ref: poster/overlap)
        self.chk_overlap = QCheckBox(
            self.res_mgr.get_xml_string(
                "poster/overlap.title",
                "Chevauchement des mosaïques (facilite l'assemblage)",
            )
        )
        self.chk_overlap.setChecked(True)
        layout.addWidget(self.chk_overlap)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 6. Boutons OK / Annuler
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        self.btn_ok = QPushButton("Créer le poster...")
        self.btn_ok.setObjectName("PrimaryBtn")
        self.btn_ok.clicked.connect(self._generate_poster)
        btn_box.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("poster/button19.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue poster.
        EN : Dynamically applies the active Picasa theme to the poster dialog.
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
            QLabel {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
            QComboBox {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 3px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {inp_bg};
                color: {fg};
                selection-background-color: #3879D9;
                selection-color: #FFFFFF;
                font-size: 9pt;
            }}
            QCheckBox {{
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
        self.setWindowTitle(self.res_mgr.get_xml_string("poster/window1.title", "Paramètres de poster"))
        self.lbl_factor.setText(self.res_mgr.get_xml_string("poster/labelgroup3.title", "Taille de poster :"))
        self.lbl_paper.setText(self.res_mgr.get_xml_string("poster/labelgroup14.title", "Format du papier :"))
        self.chk_overlap.setText(
            self.res_mgr.get_xml_string(
                "poster/overlap.title",
                "Chevauchement des mosaïques (facilite l'assemblage)",
            )
        )
        self.btn_cancel.setText(self.res_mgr.get_xml_string("poster/button19.title", "Annuler"))

    def _on_factor_changed(self, idx: int) -> None:
        grid_sz = self.combo_factor.currentData()
        self.preview.set_grid_size(grid_sz)

    def _generate_poster(self) -> None:
        """
        FR : Découpe l'image selon la grille sélectionnée et ouvre le dossier des tuiles générées.
        EN : Splits the image according to the selected grid and opens the generated tiles folder.
        """
        if not os.path.exists(self.photo_path):
            QMessageBox.warning(self, "Erreur", "Le fichier photo source n'existe pas.")
            return

        grid_sz = self.combo_factor.currentData()
        overlap = self.chk_overlap.isChecked()

        src_p = Path(self.photo_path)
        out_dir = src_p.parent / f"Poster_{src_p.stem}_{grid_sz}x{grid_sz}"
        os.makedirs(out_dir, exist_ok=True)

        try:
            from picasa_py.ui.image_processor import PicasaImageProcessor
            img = PicasaImageProcessor.load_transformed_image(self.photo_path)
            if img is not None:
                w, h = img.size
                tile_w = w // grid_sz
                tile_h = h // grid_sz
                margin_x = int(tile_w * 0.03) if overlap else 0
                margin_y = int(tile_h * 0.03) if overlap else 0

                count = 0
                for r in range(grid_sz):
                    for c in range(grid_sz):
                        left = max(0, c * tile_w - margin_x)
                        top = max(0, r * tile_h - margin_y)
                        right = min(w, (c + 1) * tile_w + margin_x)
                        bottom = min(h, (r + 1) * tile_h + margin_y)

                        box = (left, top, right, bottom)
                        tile_img = img.crop(box)
                        tile_name = f"page_{r+1:02d}_{c+1:02d}.jpg"
                        tile_path = out_dir / tile_name
                        if tile_img.mode in ("RGBA", "P"):
                            tile_img = tile_img.convert("RGB")
                        tile_img.save(str(tile_path), "JPEG", quality=95)
                        count += 1
            else:
                count = 0

            QMessageBox.information(
                self,
                "Poster généré",
                f"Le poster a été découpé en {count} pages prêtes à imprimer dans le dossier :\n{out_dir}"
            )
            # Ouvrir le dossier des pages (multi-plateforme : Windows / macOS / Linux)
            import subprocess
            try:
                if sys.platform == "win32":
                    os.startfile(str(out_dir))
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(out_dir)])
                else:
                    subprocess.Popen(["xdg-open", str(out_dir)])
            except Exception:
                pass
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la génération du poster : {e}")
