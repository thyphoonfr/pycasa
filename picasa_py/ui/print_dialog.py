"""
FR: Atelier d'impression interactif WYSIWYG pour PyCasa.
EN: Interactive WYSIWYG Print Workshop for PyCasa.
Re-implements Picasa 3's print panel and review dialog.

Ref: picasa3.exe @ 0x008C3380 (reviewprint, CPrintDlg)
Ref: picasa3.exe @ 0x00943FC4 (.?AVCPrintDlg@@, .?AVCPrintOptionsDialog@@)
Ref: printpanel/* (3x5button, 4x6button, 5x7button, 8x10button, walletbutton, photoindexbutton, croptoggle, fittoggle)
Ref: STRINGRES_FR.XML (ytPrintSizes::*, CPrintDlg::*)
"""

from __future__ import annotations
import math
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QRadioButton, QButtonGroup, QSpinBox, QFrame,
    QScrollArea, QMessageBox, QFileDialog, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QRectF, QPointF, QSizeF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage, QPainterPath
)
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog, QPageSetupDialog

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PrintLayoutType:
    """
    FR: Types de mise en page d'impression disponibles dans Picasa 3.
    EN: Available print layout types in Picasa 3.
    """
    FULL_PAGE = "full"          # 1 par page (Pleine page)
    FORMAT_10x15 = "4x6"        # 2 par page (10 x 15 cm / 4 x 6)
    FORMAT_13x18 = "5x7"        # 2 par page (13 x 18 cm / 5 x 7)
    FORMAT_20x25 = "8x10"       # 1 par page (20 x 25 cm / 8 x 10)
    WALLET = "wallet"           # 9 par page (Petit format / Portefeuille)
    CONTACT_SHEET = "contact"   # 35 par page (Planche-contact 5x7)


class PicasaPrintPreviewCanvas(QWidget):
    """
    FR: Canvas de prévisualisation WYSIWYG de la page d'impression.
    Affiche la feuille de papier à l'échelle avec ombrage et disposition des cellules.
    EN: WYSIWYG print page preview canvas.
    Displays the scaled paper sheet with drop shadow and cell layout.
    Ref: picasa3.exe @ printpanel/preview, CPrintDlg
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le canevas de prévisualisation de la feuille d'impression.
        EN: Initializes the print sheet preview canvas.
        """
        super().__init__(parent)
        self.setMinimumSize(420, 520)
        self.image_paths: List[str] = []
        self.layout_type: str = PrintLayoutType.FORMAT_10x15
        self.framing_mode: str = "crop"  # "crop" ou "shrink"
        self.copies_per_photo: int = 1
        self.current_page: int = 0
        self._pixmap_cache: Dict[str, QPixmap] = {}
        self._pixmap_max_size: int = 0
        self._dim_cache: dict[str, tuple[int, int]] = {}
        self._ini_doc_cache: dict[str, object] = {}

    def set_data(
        self,
        paths: List[str],
        layout_type: str,
        framing_mode: str,
        copies: int,
        page: int = 0
    ) -> None:
        """
        FR: Met à jour les paramètres d'impression (photos, format, cadrage, copies, page) et rafraîchit le canevas.
        EN: Updates print parameters (photos, layout, framing, copies, page) and refreshes the canvas.
        """
        self.image_paths = paths
        self.layout_type = layout_type
        self.framing_mode = framing_mode
        self.copies_per_photo = max(1, copies)
        self.current_page = max(0, min(page, self.get_total_pages() - 1))
        self.update()

    def get_photos_per_page(self) -> int:
        """
        FR: Renvoie le nombre de cellules photos par page selon le format d'impression sélectionné.
        EN: Returns the number of photo cells per page according to the selected print layout.
        """
        if self.layout_type == PrintLayoutType.FULL_PAGE:
            return 1
        elif self.layout_type in (PrintLayoutType.FORMAT_10x15, PrintLayoutType.FORMAT_13x18):
            return 2
        elif self.layout_type == PrintLayoutType.FORMAT_20x25:
            return 1
        elif self.layout_type == PrintLayoutType.WALLET:
            return 9
        elif self.layout_type == PrintLayoutType.CONTACT_SHEET:
            return 35
        return 1

    def get_total_prints_count(self) -> int:
        """
        FR: Calcule le nombre total de tirages (nombre de photos × nombre d'exemplaires).
        EN: Computes the total print count (number of photos × copies per photo).
        """
        return len(self.image_paths) * self.copies_per_photo

    def get_total_pages(self) -> int:
        """
        FR: Calcule le nombre total de pages nécessaires pour imprimer tous les tirages.
        EN: Computes the total number of pages required to print all items.
        """
        total_items = self.get_total_prints_count()
        if total_items <= 0:
            return 1
        return max(1, math.ceil(total_items / self.get_photos_per_page()))

    def get_photos_for_page(self, page_idx: int) -> List[str]:
        """
        FR: Retourne la liste ordonnée des chemins d'images à imprimer sur la page donnée.
        EN: Returns the ordered list of image paths to print on the given page.
        """
        expanded: List[str] = []
        for p in self.image_paths:
            for _ in range(self.copies_per_photo):
                expanded.append(p)

        per_page = self.get_photos_per_page()
        start = page_idx * per_page
        end = start + per_page
        return expanded[start:end]

    def set_layout_mode(self, layout_type: str) -> None:
        """
        FR: Définit le mode de disposition d'impression et rafraîchit l'aperçu.
        EN: Sets the print layout mode and refreshes the preview.
        """
        self.layout_type = layout_type
        self.current_page = max(0, min(self.current_page, self.get_total_pages() - 1))
        self.update()

    def _get_or_load_pixmap(self, path: str) -> Optional[QPixmap]:
        """
        FR: Charge ou récupère en cache le QPixmap d'une photo à imprimer.
        EN: Loads or retrieves from cache the QPixmap for a photo to print.
        """
        if not path or not os.path.exists(path):
            return None
        max_size = 288 if self.get_photos_per_page() > 4 else 640
        if max_size > self._pixmap_max_size:
            self._pixmap_cache.clear()
            self._pixmap_max_size = max_size
        if path in self._pixmap_cache:
            return self._pixmap_cache[path]
        try:
            from picasa_py.ui.image_processor import PicasaImageProcessor
            im = PicasaImageProcessor.load_transformed_image(path, max_size=max_size)
            if im is not None:
                pix = PicasaImageProcessor.pil_to_qpixmap(im)
                self._pixmap_cache[path] = pix
                return pix
            return None
        except Exception:
            return None

    def calculate_current_dpi(self) -> Tuple[int, str]:
        """
        FR: Calcule la résolution effective (DPI) pour l'impression.
        EN: Computes the effective resolution (DPI) for printing.
        Ref: CPrintDlg::bestqual, goodqual, badqual
        """
        if not self.image_paths:
            return 300, "ready"

        page_photos = self.get_photos_for_page(self.current_page)
        if not page_photos:
            return 300, "ready"

        min_dpi = 600
        cell_dims = {
            PrintLayoutType.FULL_PAGE: (8.0, 10.5),
            PrintLayoutType.FORMAT_10x15: (4.0, 6.0),
            PrintLayoutType.FORMAT_13x18: (5.0, 7.0),
            PrintLayoutType.FORMAT_20x25: (8.0, 10.0),
            PrintLayoutType.WALLET: (2.5, 3.2),
            PrintLayoutType.CONTACT_SHEET: (1.5, 1.4),
        }
        cw_in, ch_in = cell_dims.get(self.layout_type, (4.0, 6.0))

        for p in page_photos:
            try:
                if p in self._dim_cache:
                    w, h = self._dim_cache[p]
                else:
                    from PIL import Image
                    with Image.open(p) as im:
                        img_w, img_h = im.size
                    parent_dir = os.path.dirname(p)
                    ini_path = os.path.join(parent_dir, ".picasa.ini")
                    if not os.path.exists(ini_path):
                        ini_path = os.path.join(parent_dir, "Picasa.ini")
                    if os.path.exists(ini_path):
                        try:
                            from picasa_py.ini.parser import PicasaIniParser
                            from picasa_py.faces.facerect import decode_rect64_string
                            if ini_path in self._ini_doc_cache:
                                doc = self._ini_doc_cache[ini_path]
                            else:
                                doc = PicasaIniParser.parse_file(ini_path)
                                self._ini_doc_cache[ini_path] = doc
                            if doc is not None:
                                base_name = os.path.basename(p)
                                crop_hex = doc.get_crop(base_name)
                                if crop_hex:
                                    left_f, top_f, right_f, bottom_f = decode_rect64_string(crop_hex)
                                    if right_f > left_f and bottom_f > top_f:
                                        img_w = max(1, int(round(img_w * (right_f - left_f))))
                                        img_h = max(1, int(round(img_h * (bottom_f - top_f))))
                                rot = doc.get_rotate(base_name)
                                if rot in (1, 3):
                                    img_w, img_h = img_h, img_w
                        except Exception:
                            self._ini_doc_cache[ini_path] = None
                    w, h = img_w, img_h
                    self._dim_cache[p] = (w, h)
                dpi_w = w / max(0.1, cw_in)
                dpi_h = h / max(0.1, ch_in)
                photo_dpi = int(min(dpi_w, dpi_h))
                if photo_dpi < min_dpi:
                    min_dpi = photo_dpi
            except Exception:
                pass

        if min_dpi >= 280:
            return min_dpi, "best"
        elif min_dpi >= 150:
            return min_dpi, "good"
        else:
            return min_dpi, "bad"

    def paintEvent(self, event) -> None:
        """
        FR: Dessine l'aperçu WYSIWYG de la page A4 avec ombre portée, marges et cellules photos.
        EN: Draws the WYSIWYG A4 page preview with drop shadow, margins, and photo cells.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        painter.fillRect(self.rect(), QColor(0x20, 0x22, 0x26))

        vw, vh = float(self.width()), float(self.height())
        margin_view = 20.0
        avail_w = vw - 2 * margin_view
        avail_h = vh - 2 * margin_view

        aspect_paper = 210.0 / 297.0  # Portrait A4
        if avail_w / avail_h > aspect_paper:
            paper_h = avail_h
            paper_w = paper_h * aspect_paper
        else:
            paper_w = avail_w
            paper_h = paper_w / aspect_paper

        paper_x = (vw - paper_w) / 2.0
        paper_y = (vh - paper_h) / 2.0
        paper_rect = QRectF(paper_x, paper_y, paper_w, paper_h)

        shadow_rect = paper_rect.translated(5, 5)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 110))

        painter.fillRect(paper_rect, QColor(255, 255, 255))
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.drawRect(paper_rect)

        margin_pct = 0.04
        print_rect = paper_rect.adjusted(
            paper_w * margin_pct, paper_h * margin_pct,
            -paper_w * margin_pct, -paper_h * margin_pct
        )

        painter.setPen(QPen(QColor(220, 220, 220), 1, Qt.PenStyle.DashLine))
        painter.drawRect(print_rect)

        cells = self._compute_cells(print_rect)
        page_photos = self.get_photos_for_page(self.current_page)

        for i, cell in enumerate(cells):
            painter.setPen(QPen(QColor(235, 235, 235), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(cell)

            if i < len(page_photos):
                photo_path = page_photos[i]
                pix = self._get_or_load_pixmap(photo_path)
                if pix and not pix.isNull():
                    self._draw_photo_in_cell(painter, pix, cell, photo_path)

    def _compute_cells(self, area: QRectF) -> List[QRectF]:
        """
        FR: Calcule les rectangles des cellules selon le format choisi.
        EN: Computes cell rectangles according to the selected layout format.
        """
        cells: List[QRectF] = []
        ax, ay, aw, ah = area.x(), area.y(), area.width(), area.height()

        if self.layout_type == PrintLayoutType.FULL_PAGE or self.layout_type == PrintLayoutType.FORMAT_20x25:
            cells.append(area)

        elif self.layout_type in (PrintLayoutType.FORMAT_10x15, PrintLayoutType.FORMAT_13x18):
            gap = 8.0
            cell_h = (ah - gap) / 2.0
            cells.append(QRectF(ax, ay, aw, cell_h))
            cells.append(QRectF(ax, ay + cell_h + gap, aw, cell_h))

        elif self.layout_type == PrintLayoutType.WALLET:
            gap = 6.0
            cw = (aw - 2 * gap) / 3.0
            ch = (ah - 2 * gap) / 3.0
            for r in range(3):
                for c in range(3):
                    cells.append(QRectF(ax + c * (cw + gap), ay + r * (ch + gap), cw, ch))

        elif self.layout_type == PrintLayoutType.CONTACT_SHEET:
            cols, rows = 5, 7
            gap_x = 4.0
            gap_y = 6.0
            cw = (aw - (cols - 1) * gap_x) / cols
            ch = (ah - (rows - 1) * gap_y) / rows
            for r in range(rows):
                for c in range(cols):
                    cells.append(QRectF(ax + c * (cw + gap_x), ay + r * (ch + gap_y), cw, ch))

        return cells

    def _draw_photo_in_cell(self, painter: QPainter, pix: QPixmap, cell: QRectF, path: str) -> None:
        """
        FR: Dessine une photo dans sa cellule selon le cadrage recadrer ou rétrécir.
        EN: Draws a photo in its cell according to crop-to-fit or shrink-to-fit framing.
        """
        pw = float(pix.width())
        ph = float(pix.height())
        if pw <= 0 or ph <= 0:
            return

        is_contact = self.layout_type == PrintLayoutType.CONTACT_SHEET
        photo_cell = cell.adjusted(1, 1, -1, -12 if is_contact else -1)

        scale_fit = min(photo_cell.width() / pw, photo_cell.height() / ph)
        scale_crop = max(photo_cell.width() / pw, photo_cell.height() / ph)

        painter.save()
        painter.setClipRect(photo_cell)

        if self.framing_mode == "crop" and not is_contact:
            draw_w = pw * scale_crop
            draw_h = ph * scale_crop
            dx = photo_cell.x() + (photo_cell.width() - draw_w) / 2.0
            dy = photo_cell.y() + (photo_cell.height() - draw_h) / 2.0
            painter.drawPixmap(QRectF(dx, dy, draw_w, draw_h), pix, QRectF(pix.rect()))
        else:
            draw_w = pw * scale_fit
            draw_h = ph * scale_fit
            dx = photo_cell.x() + (photo_cell.width() - draw_w) / 2.0
            dy = photo_cell.y() + (photo_cell.height() - draw_h) / 2.0
            painter.drawPixmap(QRectF(dx, dy, draw_w, draw_h), pix, QRectF(pix.rect()))

        painter.restore()

        if is_contact:
            painter.setPen(QColor(70, 70, 70))
            painter.setFont(QFont("Segoe UI", 6))
            txt_rect = QRectF(cell.left(), cell.bottom() - 11, cell.width(), 10)
            painter.drawText(txt_rect, Qt.AlignmentFlag.AlignCenter, Path(path).stem[:12])


class PicasaPrintDialog(QDialog):
    """
    FR: Atelier d'impression complet WYSIWYG de Picasa 3.
    EN: Picasa 3 full WYSIWYG Print Workshop dialog.
    Ref: picasa3.exe @ reviewprint, CPrintDlg (0x008C3380), PRINT_FR.XML
    """

    def __init__(self, photo_paths: List[str], parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        """
        FR: Initialise la boîte de dialogue d'impression WYSIWYG avec les photos sélectionnées.
        EN: Initializes the WYSIWYG print dialog with the selected photos.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()
        self.photo_paths = [p for p in photo_paths if p and os.path.exists(p)]

        self.setWindowTitle(self.res_mgr.get_xml_string("print/window1.title", "Imprimer - Picasa"))
        self.resize(980, 680)
        self.setMinimumSize(820, 560)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # FR: 1. Panneau latéral gauche de commande d'impression (printpanel)
        # EN: 1. Left print control sidebar (printpanel)
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)

        # FR: 2. Zone droite de prévisualisation WYSIWYG
        # EN: 2. Right WYSIWYG preview area
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        self.lbl_page_info = QLabel()
        right_layout.addWidget(self.lbl_page_info)

        self.preview_canvas = PicasaPrintPreviewCanvas(self)
        right_layout.addWidget(self.preview_canvas, 1)

        pag_bar = self._create_pagination_bar()
        right_layout.addWidget(pag_bar)

        main_layout.addWidget(right_container, 1)

        self._update_preview()
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème PicasaStyle à l'atelier d'impression.
        EN: Dynamically applies the PicasaStyle theme to the Print Workshop dialog.
        """
        self.style = style or PicasaStyle.instance()
        s = self.style
        dlg_bg = s.window_bgcolor.name() if s.is_dark else "#EDEAE4"
        side_bg = s.alist_catcolor.name() if s.is_dark else "#E2DFD6"
        txt_col = s.alist_textcolor.name() if s.is_dark else "#222222"
        sub_col = s.alayout_subtitleColor.name() if s.is_dark else "#444444"
        border_col = s.splitter_color.name() if s.is_dark else "#BFBAB0"
        input_bg = s.thumb_card_bgcolor.name() if s.is_dark else "#FFFFFF"
        btn_bg = s.topbar_btn_bg_start.name() if s.is_dark else "#FFFFFF"
        btn_hover = s.topbar_btn_bg_end.name() if s.is_dark else "#F8F7F4"
        accent = s.accent_color.name()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {txt_col};
            }}
            QWidget#SidebarRoot {{
                background-color: {side_bg};
                border-right: 1px solid {border_col};
            }}
            QLabel {{
                color: {txt_col};
                font-size: 11px;
                background: transparent;
            }}
            QPushButton#PrimaryBtn {{
                background-color: {accent};
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 7px 16px;
                border: 1px solid {accent};
                font-size: 12px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {s.accent_color.lighter(115).name()};
            }}
            QPushButton#SecondaryBtn {{
                background-color: {btn_bg};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 11px;
                color: {txt_col};
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
            QComboBox, QSpinBox {{
                background-color: {input_bg};
                color: {txt_col};
                border: 1px solid {border_col};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {txt_col};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                font-size: 9pt;
            }}
            QRadioButton {{
                font-size: 11px;
                padding: 2px;
                color: {txt_col};
            }}
        """)
        if hasattr(self, "lbl_page_info"):
            self.lbl_page_info.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {txt_col};")
        if hasattr(self, "lbl_pag_info"):
            self.lbl_pag_info.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {sub_col};")

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les libellés de l'atelier d'impression selon la langue active.
        EN: Updates the Print Workshop labels according to the active language.
        """
        self.setWindowTitle(self.res_mgr.get_xml_string("print/window1.title", "Imprimer - Picasa"))
        self.lbl_prt_title.setText(self.res_mgr.get_xml_string("printpanel/printer_title", "Imprimante"))
        self.btn_setup.setText(self.res_mgr.get_xml_string("printpanel/printersetupbutton", "Configuration de la page..."))
        self.lbl_layout_title.setText(self.res_mgr.get_xml_string("printpanel/layout_title", "Format d'impression"))
        self.lbl_frame_title.setText(self.res_mgr.get_xml_string("printpanel/fitoptions_title", "Cadrage de l'image"))
        self.rb_crop.setText(self.res_mgr.get_xml_string("printpanel/croptoggle", "Recadrer pour adapter"))
        self.rb_shrink.setText(self.res_mgr.get_xml_string("printpanel/fittoggle", "Rétrécir pour adapter"))
        self.lbl_copies.setText(self.res_mgr.get_xml_string("printpanel/copieslabel", "Exemplaires :"))
        self.btn_print.setText(self.res_mgr.get_xml_string("printpanel/printbutton", "Imprimer"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("printpanel/cancelbutton", "Annuler"))
        self._update_preview()

    def _create_sidebar(self) -> QWidget:
        """
        FR: Construit le panneau latéral gauche regroupant le choix d'imprimante, le format, le cadrage et les copies.
        EN: Builds the left sidebar containing printer selection, layout format, framing, and copy count.
        """
        panel = QWidget()
        panel.setFixedWidth(290)
        panel.setObjectName("SidebarRoot")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # FR: 1. Section Imprimante / EN: 1. Printer section
        self.lbl_prt_title = QLabel(self.res_mgr.get_xml_string("printpanel/printer_title", "Imprimante"))
        self.lbl_prt_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.lbl_prt_title)

        self.cb_printers = QComboBox()
        available = QPrinterInfo.availablePrinterNames()
        if available:
            for p in available:
                self.cb_printers.addItem(p)
            default = QPrinterInfo.defaultPrinterName()
            if default:
                self.cb_printers.setCurrentText(default)
        else:
            self.cb_printers.addItem("Microsoft Print to PDF")
        layout.addWidget(self.cb_printers)

        self.btn_setup = QPushButton(self.res_mgr.get_xml_string("printpanel/printersetupbutton", "Configuration de la page..."))
        self.btn_setup.setObjectName("SecondaryBtn")
        self.btn_setup.clicked.connect(self._on_page_setup)
        layout.addWidget(self.btn_setup)

        layout.addSpacing(4)

        # FR: 2. Section Disposition d'impression / EN: 2. Print layout section
        self.lbl_layout_title = QLabel(self.res_mgr.get_xml_string("printpanel/layout_title", "Format d'impression"))
        self.lbl_layout_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.lbl_layout_title)

        self.layout_group = QButtonGroup(self)
        layouts = [
            ("Pleine page (1 par page)", PrintLayoutType.FULL_PAGE),
            ("10 x 15 cm (2 par page)", PrintLayoutType.FORMAT_10x15),
            ("13 x 18 cm (2 par page)", PrintLayoutType.FORMAT_13x18),
            ("20 x 25 cm (1 par page)", PrintLayoutType.FORMAT_20x25),
            ("Format portefeuille (9 par page)", PrintLayoutType.WALLET),
            ("Planche-contact (35 par page)", PrintLayoutType.CONTACT_SHEET),
        ]

        self.radio_layouts = []
        for i, (label, l_type) in enumerate(layouts):
            rb = QRadioButton(label)
            if l_type == PrintLayoutType.FORMAT_10x15:
                rb.setChecked(True)
            self.layout_group.addButton(rb, i)
            self.radio_layouts.append((rb, l_type))
            layout.addWidget(rb)

        self.layout_group.idClicked.connect(self._on_layout_changed)

        layout.addSpacing(4)

        # FR: 3. Section Cadrage / EN: 3. Framing section (Crop to fit vs Shrink to fit)
        self.lbl_frame_title = QLabel(self.res_mgr.get_xml_string("printpanel/fitoptions_title", "Cadrage de l'image"))
        self.lbl_frame_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.lbl_frame_title)

        self.frame_group = QButtonGroup(self)
        self.rb_crop = QRadioButton(self.res_mgr.get_xml_string("printpanel/croptoggle", "Recadrer pour adapter"))
        self.rb_crop.setToolTip("Remplit la cellule sans bandes blanches en rognant légèrement")
        self.rb_crop.setChecked(True)
        self.frame_group.addButton(self.rb_crop, 0)
        layout.addWidget(self.rb_crop)

        self.rb_shrink = QRadioButton(self.res_mgr.get_xml_string("printpanel/fittoggle", "Rétrécir pour adapter"))
        self.rb_shrink.setToolTip("Affiche la photo entière avec d'éventuelles marges blanches")
        self.frame_group.addButton(self.rb_shrink, 1)
        layout.addWidget(self.rb_shrink)

        self.frame_group.idClicked.connect(self._on_framing_changed)

        layout.addSpacing(4)

        # FR: 4. Section Nombre d'exemplaires / EN: 4. Number of copies section
        h_copies = QHBoxLayout()
        self.lbl_copies = QLabel(self.res_mgr.get_xml_string("printpanel/copieslabel", "Exemplaires :"))
        self.lbl_copies.setStyleSheet("font-weight: bold;")
        h_copies.addWidget(self.lbl_copies)

        self.spin_copies = QSpinBox()
        self.spin_copies.setRange(1, 99)
        self.spin_copies.setValue(1)
        self.spin_copies.valueChanged.connect(self._on_copies_changed)
        h_copies.addWidget(self.spin_copies)
        h_copies.addStretch()
        layout.addLayout(h_copies)

        # FR: 5. Indicateur de qualité d'impression (DPI badge) / EN: 5. Print quality indicator (DPI badge)
        self.badge_quality = QLabel()
        self.badge_quality.setWordWrap(True)
        self.badge_quality.setStyleSheet("""
            padding: 6px 10px;
            border-radius: 4px;
            background-color: #E2F0D9;
            border: 1px solid #A9D18E;
            color: #385723;
            font-size: 11px;
            font-weight: bold;
        """)
        layout.addWidget(self.badge_quality)

        layout.addStretch(1)

        # FR: 6. Boutons d'action (Imprimer / Annuler) / EN: 6. Action buttons (Print / Cancel)
        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_print = QPushButton(self.res_mgr.get_xml_string("printpanel/printbutton", "Imprimer"))
        self.btn_print.setObjectName("PrimaryBtn")
        self.btn_print.clicked.connect(self.execute_print)
        btns_layout.addWidget(self.btn_print)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("printpanel/cancelbutton", "Annuler"))
        self.btn_cancel.setObjectName("SecondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btns_layout.addWidget(self.btn_cancel)

        layout.addLayout(btns_layout)
        return panel

    def _create_pagination_bar(self) -> QWidget:
        """
        FR: Construit la barre inférieure de pagination permettant de naviguer entre les pages d'impression.
        EN: Builds the bottom pagination bar for navigating between print preview pages.
        """
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.btn_prev = QPushButton("◀ Précédente")
        self.btn_prev.setObjectName("SecondaryBtn")
        self.btn_prev.clicked.connect(self._on_prev_page)
        layout.addWidget(self.btn_prev)

        self.lbl_pag_info = QLabel("Page 1 sur 1")
        layout.addWidget(self.lbl_pag_info)

        self.btn_next = QPushButton("Suivante ▶")
        self.btn_next.setObjectName("SecondaryBtn")
        self.btn_next.clicked.connect(self._on_next_page)
        layout.addWidget(self.btn_next)

        layout.addStretch(1)
        return bar

    def _get_active_layout_type(self) -> str:
        """
        FR: Renvoie l'identifiant du format de mise en page actuellement coché.
        EN: Returns the identifier of the currently checked print layout format.
        """
        idx = self.layout_group.checkedId()
        if 0 <= idx < len(self.radio_layouts):
            return self.radio_layouts[idx][1]
        return PrintLayoutType.FORMAT_10x15

    def _on_layout_changed(self, _) -> None:
        """
        FR: Réinitialise la page courante et met à jour l'aperçu lors d'un changement de format.
        EN: Resets the current page and updates the preview when the layout format changes.
        """
        self.preview_canvas.current_page = 0
        self._update_preview()

    def _on_framing_changed(self, _) -> None:
        """
        FR: Met à jour l'aperçu lorsque le mode de cadrage (recadrer ou rétrécir) change.
        EN: Updates the preview when the framing mode (crop or shrink) changes.
        """
        self._update_preview()

    def _on_copies_changed(self, _) -> None:
        """
        FR: Met à jour l'aperçu lorsque le nombre d'exemplaires par photo change.
        EN: Updates the preview when the number of copies per photo changes.
        """
        self._update_preview()

    def _on_prev_page(self) -> None:
        """
        FR: Passe à la page précédente dans le canevas de prévisualisation.
        EN: Navigates to the previous page in the preview canvas.
        """
        if self.preview_canvas.current_page > 0:
            self.preview_canvas.current_page -= 1
            self._update_preview()


    def _on_next_page(self) -> None:
        """
        FR: Passe à la page suivante dans le canevas de prévisualisation.
        EN: Navigates to the next page in the preview canvas.
        """
        if self.preview_canvas.current_page < self.preview_canvas.get_total_pages() - 1:
            self.preview_canvas.current_page += 1
            self._update_preview()

    def _on_page_setup(self) -> None:
        """
        FR: Ouvre la boîte de dialogue système de configuration de la page d'impression.
        EN: Opens the system page setup dialog for the selected printer.
        """
        printer = QPrinter()
        if self.cb_printers.currentText():
            printer.setPrinterName(self.cb_printers.currentText())
        dlg = QPageSetupDialog(printer, self)
        dlg.exec()

    def _update_preview(self) -> None:
        """
        FR: Synchronise l'état des contrôles avec le canevas d'aperçu, la pagination et le badge DPI.
        EN: Synchronizes control states with the preview canvas, pagination bar, and DPI badge.
        """
        l_type = self._get_active_layout_type()
        framing = "crop" if self.rb_crop.isChecked() else "shrink"
        copies = self.spin_copies.value()

        self.preview_canvas.set_data(
            self.photo_paths,
            l_type,
            framing,
            copies,
            page=self.preview_canvas.current_page
        )

        tot_pages = self.preview_canvas.get_total_pages()
        curr_page = self.preview_canvas.current_page + 1

        self.btn_prev.setEnabled(curr_page > 1)
        self.btn_next.setEnabled(curr_page < tot_pages)
        self.lbl_pag_info.setText(f"Page {curr_page} sur {tot_pages}")

        tot_prints = self.preview_canvas.get_total_prints_count()
        photo_label = "photo" if len(self.photo_paths) <= 1 else "photos"
        self.lbl_page_info.setText(
            f"Impression de {len(self.photo_paths)} {photo_label} ({tot_prints} tirages) sur {tot_pages} page(s)"
        )

        # FR: Qualité DPI / EN: DPI quality
        dpi, qual_type = self.preview_canvas.calculate_current_dpi()
        if qual_type == "best":
            self.badge_quality.setText(f"✓ Qualité optimale ({dpi} ppp)")
            self.badge_quality.setStyleSheet("padding: 6px 10px; border-radius: 4px; background-color: #E2F0D9; border: 1px solid #A9D18E; color: #385723; font-weight: bold;")
        elif qual_type == "good":
            self.badge_quality.setText(f"✓ Qualité satisfaisante ({dpi} ppp)")
            self.badge_quality.setStyleSheet("padding: 6px 10px; border-radius: 4px; background-color: #D9E1F2; border: 1px solid #8EA9DB; color: #203764; font-weight: bold;")
        else:
            self.badge_quality.setText(f"⚠ Qualité médiocre ({dpi} ppp)")
            self.badge_quality.setStyleSheet("padding: 6px 10px; border-radius: 4px; background-color: #FCE4D6; border: 1px solid #F4B084; color: #C65911; font-weight: bold;")

    def execute_print(self) -> None:
        """
        FR: Lance l'impression effective des pages vers l'imprimante sélectionnée.
        EN: Executes actual page printing to the selected printer.
        Ref: ytPrinter, CPrintDlg
        """
        if not self.photo_paths:
            QMessageBox.information(self, "Impression", "Aucune photo à imprimer.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        prt_name = self.cb_printers.currentText()
        if prt_name:
            printer.setPrinterName(prt_name)

        # FR: Si l'utilisateur clique sur Imprimer, ouvrir QPrintDialog pour confirmer la destination
        # EN: When the user clicks Print, open QPrintDialog to confirm the destination
        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle("Imprimer les photos")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        tot_pages = self.preview_canvas.get_total_pages()
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
        printable_rect = QRectF(0, 0, page_rect.width(), page_rect.height())

        for p_idx in range(tot_pages):
            if p_idx > 0:
                printer.newPage()

            # FR: Dessin des cellules de la page / EN: Draw page cells
            cells = self.preview_canvas._compute_cells(printable_rect)
            photos = self.preview_canvas.get_photos_for_page(p_idx)

            for c_idx, cell in enumerate(cells):
                if c_idx < len(photos):
                    pix = self.preview_canvas._get_or_load_pixmap(photos[c_idx])
                    if pix and not pix.isNull():
                        self.preview_canvas._draw_photo_in_cell(painter, pix, cell, photos[c_idx])

        painter.end()
        QMessageBox.information(
            self,
            "Impression terminée",
            f"L'impression de {len(self.photo_paths)} photo(s) s'est terminée avec succès."
        )
        self.accept()
