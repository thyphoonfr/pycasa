"""
FR : Atelier de création de montages photo pour PyCasa.
Réimplémente fidèlement l'atelier interactif de montage photo (CCollageUI) de Picasa 3.
EN : Picture Collage Maker for PyCasa.
Re-implements Picasa 3's interactive Collage Maker (CCollageUI).

Ref: picasa3.exe @ ID_COLLAGEMAKER (0x0088C3EC)
Ref: picasa3.exe @ CCollageUI, CCollageManager, CollagePanel
Ref: ui/resources/xml/STRINGRES_FR.XML (collage::*, CCollageUI::*)
"""

from __future__ import annotations
import math
import os
import sys
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QRadioButton, QButtonGroup, QSlider, QFrame,
    QColorDialog, QMessageBox, QTabWidget, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage, QTransform
)

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle


class CollageTheme:
    PILE = "pile"                   # Pile d'images (Pêle-mêle éparpillé)
    MOSAIC = "mosaic"               # Mosaïque
    FRAME = "frame"                 # Cadre mosaïque avec centre
    GRID = "grid"                   # Grille régulière
    CONTACT_SHEET = "contact_sheet" # Planche-contact
    MULTI_EXP = "multiexp"          # Exposition multiple


class CollageBorder:
    NONE = 0
    WHITE = 1
    POLAROID = 2


class CollagePhotoItem:
    """
    FR : Représente une photo positionnée sur le plan de montage.
    EN : Represents a photo positioned on the collage canvas.
    """

    def __init__(self, path: str, x: float = 0.5, y: float = 0.5, angle: float = 0.0, scale: float = 0.35):
        self.path = path
        self.x = x          # Coordonnée x normalisée (0.0 à 1.0)
        self.y = y          # Coordonnée y normalisée (0.0 à 1.0)
        self.angle = angle  # Angle en degrés
        self.scale = scale  # Échelle relative
        self.border: int = CollageBorder.WHITE
        self.pixmap: Optional[QPixmap] = None
        self._screen_rect: QRectF = QRectF()


class PicasaCollageCanvas(QWidget):
    """
    FR : Plan de travail interactif du montage photo.
    Affiche la page avec ombres portées et permet le déplacement interactif à la souris.
    EN : Interactive photo collage workspace canvas.
    Displays the page with drop shadows and allows interactive mouse dragging.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(480, 480)
        self.setMouseTracking(True)

        self.theme: str = CollageTheme.PILE
        self.border_mode: int = CollageBorder.WHITE
        self.grid_spacing: int = 4
        self.bg_color: QColor = QColor(255, 255, 255)
        self.aspect_ratio: float = 4.0 / 3.0  # Paysage standard 4:3
        self.is_landscape: bool = True

        self.items: List[CollagePhotoItem] = []
        self._dragged_item: Optional[CollagePhotoItem] = None
        self._drag_start_pos: QPointF = QPointF(0, 0)
        self._drag_start_item_pos: QPointF = QPointF(0, 0)
        self._page_rect: QRectF = QRectF()

    def set_photos(self, paths: List[str]) -> None:
        self.items = []
        max_size = 360 if len(paths) > 12 else 600
        for p in paths:
            if p and os.path.exists(p):
                item = CollagePhotoItem(p)
                self._load_thumbnail(item, max_size=max_size)
                self.items.append(item)
        self.randomize_layout()

    def _load_thumbnail(self, item: CollagePhotoItem, max_size: Optional[int] = None) -> None:
        try:
            from picasa_py.ui.image_processor import PicasaImageProcessor
            target_max = max_size if max_size is not None else (360 if len(self.items) > 12 else 600)
            im = PicasaImageProcessor.load_transformed_image(item.path, max_size=target_max)
            if im is not None:
                item.pixmap = PicasaImageProcessor.pil_to_qpixmap(im)
            else:
                item.pixmap = None
        except Exception:
            item.pixmap = None

    def randomize_layout(self) -> None:
        """
        FR : Réorganise les photos aléatoirement selon le thème actif.
        EN : Randomly rearranges the photos according to the active theme.
        """
        self.apply_layout_theme()

    def apply_layout_theme(self) -> None:
        """
        FR : Calcule et applique la disposition des photos selon le thème actif et l'espacement de grille.
        EN : Computes and applies photo layout according to the active theme and grid spacing.
        """
        n = len(self.items)
        if n == 0:
            self.update()
            return

        spacing_factor = max(0.25, 1.0 - float(self.grid_spacing) / 120.0)

        if self.theme == CollageTheme.PILE:
            # Distribution aléatoire éparpillée avec rotations naturelles
            for item in self.items:
                item.x = random.uniform(0.2, 0.8)
                item.y = random.uniform(0.2, 0.8)
                item.angle = random.uniform(-20.0, 20.0)
                item.scale = random.uniform(0.30, 0.45)
                item.border = self.border_mode

        elif self.theme == CollageTheme.GRID or self.theme == CollageTheme.CONTACT_SHEET:
            cols = max(1, int(math.ceil(math.sqrt(n * self.aspect_ratio))))
            rows = max(1, int(math.ceil(n / float(cols))))
            for i, item in enumerate(self.items):
                r = i // cols
                c = i % cols
                item.x = (c + 0.5) / float(cols)
                item.y = (r + 0.5) / float(rows)
                item.angle = 0.0
                item.scale = (1.0 / max(cols, rows)) * spacing_factor
                item.border = self.border_mode

        elif self.theme == CollageTheme.MOSAIC or self.theme == CollageTheme.FRAME:
            # Mosaïque avec centre prédominant si FRAME
            cols = max(1, int(math.ceil(math.sqrt(n))))
            rows = max(1, int(math.ceil(n / float(cols))))
            for i, item in enumerate(self.items):
                r = i // cols
                c = i % cols
                item.x = (c + 0.5) / float(cols)
                item.y = (r + 0.5) / float(rows)
                item.angle = 0.0
                if self.theme == CollageTheme.FRAME and i == 0:
                    item.x, item.y = 0.5, 0.5
                    item.scale = 0.55 * spacing_factor
                else:
                    item.scale = (1.0 / max(cols, rows)) * spacing_factor
                item.border = self.border_mode

        elif self.theme == CollageTheme.MULTI_EXP:
            for item in self.items:
                item.x = 0.5
                item.y = 0.5
                item.angle = 0.0
                item.scale = 0.85
                item.border = CollageBorder.NONE

        self.update()

    def set_theme(self, theme: str) -> None:
        self.theme = theme
        self.randomize_layout()

    def set_border_mode(self, mode: int) -> None:
        self.border_mode = mode
        for it in self.items:
            it.border = mode
        self.update()

    def set_aspect_ratio(self, ratio: float, is_landscape: bool = True) -> None:
        self.aspect_ratio = ratio if is_landscape else (1.0 / ratio if ratio > 0 else 1.0)
        self.is_landscape = is_landscape
        self.update()

    def set_background_color(self, color: QColor) -> None:
        self.bg_color = color
        self.update()

    def set_grid_spacing(self, spacing: int) -> None:
        self.grid_spacing = int(spacing)
        if self.theme in (CollageTheme.GRID, CollageTheme.MOSAIC, CollageTheme.FRAME, CollageTheme.CONTACT_SHEET):
            self.apply_layout_theme()
        else:
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fond neutre sombre
        painter.fillRect(self.rect(), QColor(0x20, 0x22, 0x26))

        # Calcul de la feuille virtuelle
        vw, vh = float(self.width()), float(self.height())
        margin = 24.0
        avail_w = vw - 2 * margin
        avail_h = vh - 2 * margin

        if avail_w / avail_h > self.aspect_ratio:
            page_h = avail_h
            page_w = page_h * self.aspect_ratio
        else:
            page_w = avail_w
            page_h = page_w / self.aspect_ratio

        px = (vw - page_w) / 2.0
        py = (vh - page_h) / 2.0
        self._page_rect = QRectF(px, py, page_w, page_h)

        # Ombre portée de la page de montage
        painter.fillRect(self._page_rect.translated(6, 6), QColor(0, 0, 0, 110))

        # Page de montage
        painter.fillRect(self._page_rect, self.bg_color)
        painter.setPen(QPen(QColor(160, 160, 160), 1))
        painter.drawRect(self._page_rect)

        # Dessin des photos sur la page
        painter.save()
        painter.setClipRect(self._page_rect)

        if self.theme == CollageTheme.MULTI_EXP:
            alpha = max(30, int(255 / max(1, len(self.items))))
            painter.setOpacity(alpha / 255.0)

        for item in self.items:
            self._draw_collage_item(painter, item, self._page_rect)

        painter.restore()

    def _draw_collage_item(self, painter: QPainter, item: CollagePhotoItem, page_rect: QRectF) -> None:
        if not item.pixmap or item.pixmap.isNull():
            return

        cx = page_rect.x() + item.x * page_rect.width()
        cy = page_rect.y() + item.y * page_rect.height()

        pw = float(item.pixmap.width())
        ph = float(item.pixmap.height())

        # Dimensions de la photo sur la page
        target_w = page_rect.width() * item.scale
        target_h = target_w * (ph / pw) if pw > 0 else target_w

        # Marges de bordure
        b_type = item.border
        pad_top = pad_left = pad_right = 0.0
        pad_bottom = 0.0
        if b_type == CollageBorder.WHITE:
            pad_top = pad_bottom = pad_left = pad_right = max(3.0, target_w * 0.03)
        elif b_type == CollageBorder.POLAROID:
            pad_top = pad_left = pad_right = max(4.0, target_w * 0.04)
            pad_bottom = max(16.0, target_w * 0.16)

        total_w = target_w + pad_left + pad_right
        total_h = target_h + pad_top + pad_bottom

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(item.angle)

        card_rect = QRectF(-total_w / 2.0, -total_h / 2.0, total_w, total_h)
        photo_rect = QRectF(
            card_rect.left() + pad_left,
            card_rect.top() + pad_top,
            target_w,
            target_h
        )

        # Ombre portée de la carte (si pile d'images ou polaroïd)
        if self.theme == CollageTheme.PILE or b_type != CollageBorder.NONE:
            painter.fillRect(card_rect.translated(4, 4), QColor(0, 0, 0, 75))

        # Carte blanche (bordure)
        if b_type != CollageBorder.NONE:
            painter.fillRect(card_rect, QColor(255, 255, 255))
            painter.setPen(QPen(QColor(220, 220, 220), 1))
            painter.drawRect(card_rect)

        # Photo
        painter.drawPixmap(photo_rect, item.pixmap, QRectF(item.pixmap.rect()))
        painter.restore()

        # Enregistrement du rectangle écran approximatif pour le hit-test souris
        item._screen_rect = QRectF(cx - total_w / 2.0, cy - total_h / 2.0, total_w, total_h)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            # Hit-test en partant de la photo du dessus (fin de liste)
            for item in reversed(self.items):
                if item._screen_rect.contains(pos):
                    self._dragged_item = item
                    self._drag_start_pos = pos
                    self._drag_start_item_pos = QPointF(item.x, item.y)
                    # Amener l'élément au premier plan
                    self.items.remove(item)
                    self.items.append(item)
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    self.update()
                    return

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self._dragged_item and not self._page_rect.isEmpty():
            dx_norm = (pos.x() - self._drag_start_pos.x()) / self._page_rect.width()
            dy_norm = (pos.y() - self._drag_start_pos.y()) / self._page_rect.height()
            self._dragged_item.x = max(0.05, min(0.95, self._drag_start_item_pos.x() + dx_norm))
            self._dragged_item.y = max(0.05, min(0.95, self._drag_start_item_pos.y() + dy_norm))
            self.update()
            return

        # Survol
        hit = any(item._screen_rect.contains(pos) for item in self.items)
        self.setCursor(Qt.CursorShape.PointingHandCursor if hit else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragged_item:
            self._dragged_item = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def render_hd(self, width: int = 3840) -> QImage:
        """
        FR : Génère une image haute définition (Ultra HD 4K) du montage pour l'exportation sur disque.
        EN : Generates an Ultra HD 4K image of the collage for disk export.
        Ref: CollageMaker::createprog, saveprog
        """
        height = int(width / self.aspect_ratio)
        img = QImage(width, height, QImage.Format.Format_RGB888)
        img.fill(self.bg_color)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        page_rect = QRectF(0, 0, width, height)

        if self.theme == CollageTheme.MULTI_EXP:
            alpha = max(30, int(255 / max(1, len(self.items))))
            painter.setOpacity(alpha / 255.0)

        saved_screen_rects = [QRectF(it._screen_rect) for it in self.items]
        try:
            for item in self.items:
                # Charger l'image haute définition source avec ses retouches non-destructives
                try:
                    from picasa_py.ui.image_processor import PicasaImageProcessor
                    max_dim = max(width // 2, 1200)
                    full_im = PicasaImageProcessor.load_transformed_image(item.path, max_size=max_dim)
                    if full_im is not None:
                        hd_pixmap = PicasaImageProcessor.pil_to_qpixmap(full_im)
                    else:
                        hd_pixmap = item.pixmap
                except Exception:
                    hd_pixmap = item.pixmap

                orig_pixmap = item.pixmap
                item.pixmap = hd_pixmap
                self._draw_collage_item(painter, item, page_rect)
                item.pixmap = orig_pixmap
        finally:
            for it, sr in zip(self.items, saved_screen_rects):
                it._screen_rect = sr

        painter.end()
        return img


class PicasaCollageDialog(QDialog):
    """
    FR : Atelier complet de création de montages photo (CCollageUI).
    EN : Complete photo collage maker workshop (CCollageUI).
    Ref: picasa3.exe @ 0x0088C3EC (ID_COLLAGEMAKER), collagepanel/*
    """
    collage_created = Signal(str)

    def __init__(
        self,
        photo_paths: List[str],
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        super().__init__(parent)
        self.res_mgr = PicasaResourceManager.get()
        self.style = style or getattr(parent, "style", None) or PicasaStyle.instance()
        self.photo_paths = [p for p in photo_paths if p and os.path.exists(p)]

        self.setWindowTitle(
            self.res_mgr.get_stringres("CCollageUI::title", "Montage photo - Picasa")
        )
        self.resize(1000, 700)
        self.setMinimumSize(840, 560)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Zone droite : Plan de travail (Canvas)
        self.canvas = PicasaCollageCanvas(self)
        self.canvas.set_photos(self.photo_paths)

        # 2. Panneau latéral gauche (CollagePanel)
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.canvas, 1)

        self.apply_style(self.style)

    def _create_sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(290)
        panel.setObjectName("CollageSidebar")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 1. Sélecteur de type de montage
        self.lbl_type = QLabel("Type de montage :")
        self.lbl_type.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.lbl_type)

        self.cb_theme = QComboBox()
        self.cb_theme.addItem("Pile d'images (Pêle-mêle)", CollageTheme.PILE)
        self.cb_theme.addItem("Mosaïque", CollageTheme.MOSAIC)
        self.cb_theme.addItem("Cadre mosaïque", CollageTheme.FRAME)
        self.cb_theme.addItem("Grille régulière", CollageTheme.GRID)
        self.cb_theme.addItem("Planche-contact", CollageTheme.CONTACT_SHEET)
        self.cb_theme.addItem("Exposition multiple", CollageTheme.MULTI_EXP)
        self.cb_theme.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.cb_theme)

        # Bouton Mélanger les photos
        self.btn_shuffle = QPushButton("Mélanger les photos")
        self.btn_shuffle.setObjectName("SecondaryBtn")
        self.btn_shuffle.clicked.connect(self.canvas.randomize_layout)
        layout.addWidget(self.btn_shuffle)

        layout.addSpacing(4)

        # 2. Bordures des photos
        self.lbl_border = QLabel("Bordure des photos :")
        self.lbl_border.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_border)

        self.border_group = QButtonGroup(self)
        self.rb_b0 = QRadioButton("Aucune bordure")
        self.rb_b1 = QRadioButton("Bordure blanche")
        self.rb_b2 = QRadioButton("Appareil instantané (Polaroïd)")
        self.rb_b1.setChecked(True)
        self.border_group.addButton(self.rb_b0, CollageBorder.NONE)
        self.border_group.addButton(self.rb_b1, CollageBorder.WHITE)
        self.border_group.addButton(self.rb_b2, CollageBorder.POLAROID)
        self.border_group.idClicked.connect(self.canvas.set_border_mode)
        layout.addWidget(self.rb_b0)
        layout.addWidget(self.rb_b1)
        layout.addWidget(self.rb_b2)

        layout.addSpacing(4)

        # 3. Format de page et orientation
        self.lbl_fmt = QLabel("Format de page :")
        self.lbl_fmt.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_fmt)

        self.cb_format = QComboBox()
        formats = [
            ("Standard (4:3)", 4.0 / 3.0),
            ("Écran large (16:9)", 16.0 / 9.0),
            ("Feuille A4", 297.0 / 210.0),
            ("Carré (1:1)", 1.0),
            ("Tirage photo (3:2)", 3.0 / 2.0),
        ]
        for name, val in formats:
            self.cb_format.addItem(name, val)
        self.cb_format.currentIndexChanged.connect(self._on_format_changed)
        layout.addWidget(self.cb_format)

        h_orient = QHBoxLayout()
        self.rb_land = QRadioButton("Paysage")
        self.rb_port = QRadioButton("Portrait")
        self.rb_land.setChecked(True)
        self.orient_group = QButtonGroup(self)
        self.orient_group.addButton(self.rb_land, 0)
        self.orient_group.addButton(self.rb_port, 1)
        self.orient_group.idClicked.connect(self._on_format_changed)
        h_orient.addWidget(self.rb_land)
        h_orient.addWidget(self.rb_port)
        layout.addLayout(h_orient)

        layout.addSpacing(4)

        # 4. Couleur d'arrière-plan
        h_bg = QHBoxLayout()
        self.lbl_bg = QLabel("Arrière-plan :")
        self.lbl_bg.setStyleSheet("font-weight: bold;")
        h_bg.addWidget(self.lbl_bg)

        self.btn_bg_color = QPushButton("■ Blanc")
        self.btn_bg_color.setStyleSheet("background-color: #FFFFFF; color: #000000; border: 1px solid #999; padding: 4px 8px; border-radius: 3px;")
        self.btn_bg_color.clicked.connect(self._pick_bg_color)
        h_bg.addWidget(self.btn_bg_color)
        layout.addLayout(h_bg)

        # 4b. Espacement de la grille (collagepanel/gridspacing)
        self.lbl_grid_spacing = QLabel("Espacement de la grille :")
        self.lbl_grid_spacing.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_grid_spacing)

        self.sldr_grid_spacing = QSlider(Qt.Orientation.Horizontal)
        self.sldr_grid_spacing.setRange(0, 24)
        self.sldr_grid_spacing.setValue(self.canvas.grid_spacing)
        self.sldr_grid_spacing.valueChanged.connect(self.canvas.set_grid_spacing)
        layout.addWidget(self.sldr_grid_spacing)

        layout.addStretch(1)

        # 5. Boutons Créer / Fermer
        btns_layout = QVBoxLayout()
        btns_layout.setSpacing(6)

        self.btn_create = QPushButton("Créer le montage")
        self.btn_create.setObjectName("PrimaryBtn")
        self.btn_create.clicked.connect(self.create_collage)
        btns_layout.addWidget(self.btn_create)

        self.btn_close = QPushButton("Fermer")
        self.btn_close.setObjectName("SecondaryBtn")
        self.btn_close.clicked.connect(self.reject)
        btns_layout.addWidget(self.btn_close)

        layout.addLayout(btns_layout)
        return panel

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif à l'atelier de montage.
        EN : Dynamically applies the active Picasa theme to the collage workshop.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        dlg_bg = "#24272E" if is_dark else "#EDEAE4"
        side_bg = "#2A2E37" if is_dark else "#E2DFD6"
        side_border = "#4B5263" if is_dark else "#BFBAB0"
        fg = "#F0F2F5" if is_dark else "#222222"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        inp_border = "#4B5263" if is_dark else "#B0ABA0"
        sec_hover = "#3A3F4B" if is_dark else "#F8F7F4"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {fg};
            }}
            QLabel, QRadioButton {{
                color: {fg};
                font-size: 11px;
            }}
            QPushButton#PrimaryBtn {{
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 7px 16px;
                border: 1px solid #2859A3;
                font-size: 12px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: #4A8BF0;
            }}
            QPushButton#SecondaryBtn {{
                background-color: {inp_bg};
                border: 1px solid {inp_border};
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 11px;
                color: {fg};
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {sec_hover};
                border-color: #888888;
            }}
            QComboBox {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {inp_border};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {inp_bg};
                color: {fg};
                selection-background-color: #3879D9;
                selection-color: #FFFFFF;
                font-size: 9pt;
            }}
        """)
        self.sidebar.setStyleSheet(f"""
            QWidget#CollageSidebar {{
                background-color: {side_bg};
                border-right: 1px solid {side_border};
            }}
        """)

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes selon la langue active.
        EN : Updates texts according to the active language.
        """
        self.setWindowTitle(
            self.res_mgr.get_stringres("CCollageUI::title", "Montage photo - Picasa")
        )
        self.btn_shuffle.setText(
            self.res_mgr.get_xml_string("collagepanel/scramble.title", "Mélanger les photos")
        )
        self.btn_create.setText(
            self.res_mgr.get_xml_string("collagepanel/create.title", "Créer le montage")
        )

    def _on_theme_changed(self) -> None:
        th = self.cb_theme.currentData()
        self.canvas.set_theme(th)

    def _on_format_changed(self, _) -> None:
        ratio = self.cb_format.currentData()
        is_land = self.rb_land.isChecked()
        self.canvas.set_aspect_ratio(ratio, is_land)

    def _pick_bg_color(self) -> None:
        col = QColorDialog.getColor(self.canvas.bg_color, self, "Couleur d'arrière-plan du montage")
        if col.isValid():
            self.canvas.set_background_color(col)
            txt_col = "#000000" if (col.red() * 0.299 + col.green() * 0.587 + col.blue() * 0.114) > 150 else "#FFFFFF"
            self.btn_bg_color.setStyleSheet(f"background-color: {col.name()}; color: {txt_col}; border: 1px solid #666; padding: 4px 8px; border-radius: 3px;")

    def create_collage(self) -> None:
        """
        FR : Rend le montage en haute définition (3840 px) et l'enregistre sur le disque dans 'Montages'.
        EN : Renders the collage in high definition (3840 px) and saves it to disk in 'Montages'.
        Ref: CCollageManager::CollagesFolder, CollageMaker::saveprog
        """
        if not self.canvas.items:
            QMessageBox.information(self, "Montage photo", "Aucune photo à inclure dans le montage.")
            return

        # Répertoire cible : Dossier Images/Picasa/Montages ou dossier parent de la 1ère photo
        out_dir = Path.home() / "Pictures" / "Picasa" / "Montages"
        out_dir.mkdir(parents=True, exist_ok=True)

        import time
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"Montage_{ts}.jpg"
        target_path = out_dir / filename

        # Rendu Ultra HD
        hd_image = self.canvas.render_hd(width=3840)
        hd_image.save(str(target_path), "JPEG", 95)

        self.collage_created.emit(str(target_path))
        reply = QMessageBox.information(
            self,
            "Montage créé avec succès",
            f"Votre montage haute définition a été enregistré dans :\n{target_path}",
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
        )
        if reply == QMessageBox.StandardButton.Open:
            import subprocess
            try:
                if sys.platform == "win32":
                    subprocess.Popen(f'explorer /select,"{target_path}"')
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R", str(target_path)])
                else:
                    subprocess.Popen(["xdg-open", str(target_path.parent)])
            except Exception:
                pass

        self.accept()
