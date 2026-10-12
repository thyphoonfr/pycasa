"""
High-Performance Virtual Thumbnail Grid Component for PyCasa.
Uses custom QPainter with lazy thumbnail loading to ensure 60fps scrolling.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2] alayout_*, thumbsel_*
Ref: AGENTS.md §4 ter (Fluidité de défilement, UI thread non bloqué)
"""

from __future__ import annotations
import math
import os
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtWidgets import QWidget, QScrollBar
from PySide6.QtCore import Qt, QRect, QSize, Signal, QPoint
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage, QMouseEvent,
    QWheelEvent, QPaintEvent, QResizeEvent
)

from picasa_py.ui.style import PicasaStyle
from picasa_py.db.database import PicasaDatabase


@dataclass
class ThumbnailItem:
    index: int           # Index dans thumbindex.db et thumbs_0.db
    path: str            # Chemin absolu du fichier image sur disque
    filename: str        # Nom du fichier (ex. IMG_001.jpg)
    folder: str          # Nom du dossier (ex. Vacances)
    folder_path: str     # Chemin complet du dossier (ex. C:\Photos\Vacances\)
    starred: bool = False
    pixmap: Optional[QPixmap] = None
    loading: bool = False


# Ref: constants.ui [Picasa2] alayout_*, thumbsel_*
class PicasaThumbnailView(QWidget):
    """
    Grille virtuelle de vignettes haute performance avec rendu QPainter.
    Ne dessine et ne charge que les éléments visibles dans la fenêtre.
    """
    selection_changed = Signal(list)
    item_double_clicked = Signal(int)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.db: Optional[PicasaDatabase] = None
        self.items: List[ThumbnailItem] = []
        self.filtered_indices: List[int] = []  # Indices dans self.items actuellement affichés
        self.selected_indices: Set[int] = set()

        # Dimensions dynamiques des vignettes
        self.thumb_base_size: int = 140
        self.scroll_y: int = 0
        self.total_content_height: int = 0

        # Cache de vignettes en mémoire
        self._pixmap_cache: Dict[int, QPixmap] = {}
        self._cache_limit: int = 1000

        # En-tête de section
        self.section_title: str = "Toutes les photos"
        self.section_subtitle: str = ""

        # Barre de défilement verticale
        self.scrollbar = QScrollBar(Qt.Orientation.Vertical, self)
        self.scrollbar.valueChanged.connect(self._on_scroll)

    def set_database(self, db: PicasaDatabase) -> None:
        self.db = db
        self.items.clear()
        self.selected_indices.clear()
        self._pixmap_cache.clear()

        # 1. Cartographier les répertoires depuis thumbindex.db (type == 1)
        folders = {i: r.path for i, r in enumerate(db.index) if r.type == 1}

        # 2. Filtrer UNIQUEMENT les fichiers média réels (JPG, BMP, PSD, TIFF, RAW, WEBP)
        for i, entry in enumerate(db.index):
            if entry.type not in (2, 6, 7, 13, 18, 31):
                continue

            folder_path = folders.get(entry.parent_idx, "")
            folder_name = folder_path.replace("\\", "/").rstrip("/").split("/")[-1] if folder_path else "Photos"
            full_path = os.path.join(folder_path, entry.path) if folder_path else entry.path

            item = ThumbnailItem(
                index=i,
                path=full_path,
                filename=entry.path,
                folder=folder_name,
                folder_path=folder_path,
                starred=False,
            )
            self.items.append(item)

        self.filter_by_folder(None)

    def filter_by_folder(self, folder_path: Optional[str]) -> None:
        """
        Filtre les vignettes par chemin de dossier (ou affiche tout si None).
        """
        if not folder_path:
            self.filtered_indices = list(range(len(self.items)))
            self.section_title = "Toutes les photos"
            self.section_subtitle = f"{len(self.filtered_indices)} photos"
        else:
            norm_target = folder_path.replace("\\", "/").rstrip("/").lower()
            self.filtered_indices = [
                i for i, it in enumerate(self.items)
                if it.folder_path.replace("\\", "/").rstrip("/").lower() == norm_target
            ]
            folder_name = folder_path.replace("\\", "/").rstrip("/").split("/")[-1] or "Dossier"
            self.section_title = folder_name
            self.section_subtitle = f"{len(self.filtered_indices)} photos"

        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.setValue(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def set_thumb_size(self, size: int) -> None:
        self.thumb_base_size = max(64, min(320, size))
        self._recompute_layout()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        sb_width = self.scrollbar.sizeHint().width()
        self.scrollbar.setGeometry(self.width() - sb_width, 0, sb_width, self.height())
        self._recompute_layout()

    def _recompute_layout(self) -> None:
        available_width = self.width() - self.scrollbar.width() - (self.style.alayout_gutter * 2)
        if available_width <= 0:
            return

        slot_width = self.thumb_base_size + self.style.alayout_thumbGutterX
        cols = max(1, available_width // slot_width)
        rows = math.ceil(len(self.filtered_indices) / cols) if self.filtered_indices else 0

        header_height = 60
        # Hauteur totale avec espace pour le nom du fichier sous la miniature
        slot_height = self.thumb_base_size + self.style.alayout_thumbGutterY + 16
        self.total_content_height = header_height + (rows * slot_height) + 40

        max_scroll = max(0, self.total_content_height - self.height())
        self.scrollbar.setRange(0, max_scroll)
        self.scrollbar.setPageStep(self.height())

    def _on_scroll(self, val: int) -> None:
        self.scroll_y = val
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        self.scrollbar.setValue(self.scrollbar.value() - delta // 2)

    def _get_item_rect(self, slot_idx: int) -> QRect:
        available_width = self.width() - self.scrollbar.width() - (self.style.alayout_gutter * 2)
        slot_width = self.thumb_base_size + self.style.alayout_thumbGutterX
        cols = max(1, available_width // slot_width)

        col = slot_idx % cols
        row = slot_idx // cols

        header_height = 60
        slot_height = self.thumb_base_size + self.style.alayout_thumbGutterY + 16
        x = self.style.alayout_gutter + col * slot_width
        y = header_height + row * slot_height - self.scroll_y
        return QRect(x, y, self.thumb_base_size, self.thumb_base_size)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fond de la photothèque
        painter.fillRect(self.rect(), self.style.grid_bgcolor)

        # 1. En-tête de section (Album / Dossier en cours)
        header_y = 30 - self.scroll_y
        if header_y > -40 and header_y < self.height():
            title_font = QFont(self.style.alayout_titleFont, self.style.alayout_titleSize, QFont.Weight.Bold)
            painter.setFont(title_font)
            painter.setPen(self.style.alayout_titleColor)
            painter.drawText(self.style.alayout_titleOffsetX, header_y, self.section_title)

            sub_font = QFont(self.style.alayout_bodyFont, self.style.alayout_bodySize)
            painter.setFont(sub_font)
            painter.setPen(QColor("#777777"))
            painter.drawText(self.style.alayout_titleOffsetX, header_y + 22, self.section_subtitle)

        # 2. Dessin des vignettes visibles
        visible_rect = self.rect()
        for slot_idx, item_idx in enumerate(self.filtered_indices):
            r = self._get_item_rect(slot_idx)
            if r.bottom() < -20:
                continue
            if r.top() > visible_rect.height():
                break

            self._draw_thumbnail(painter, r, item_idx)

    def _draw_thumbnail(self, painter: QPainter, rect: QRect, item_idx: int) -> None:
        item = self.items[item_idx]
        is_selected = item_idx in self.selected_indices

        # Ombre portée
        shadow_rect = rect.adjusted(3, 3, 3, 3)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 35))

        # Cadre blanc de la photo
        painter.fillRect(rect, QColor("#FFFFFF"))

        # Image de vignette
        pix = self._get_thumbnail_pixmap(item_idx)
        if pix and not pix.isNull():
            target_rect = rect.adjusted(4, 4, -4, -4)
            scaled = pix.scaled(
                target_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            draw_x = target_rect.x() + (target_rect.width() - scaled.width()) // 2
            draw_y = target_rect.y() + (target_rect.height() - scaled.height()) // 2
            painter.drawPixmap(draw_x, draw_y, scaled)
        else:
            painter.fillRect(rect.adjusted(4, 4, -4, -4), QColor("#D0D0D0"))

        # Bordures de sélection Picasa (Bleu externe, Blanc interne)
        if is_selected:
            pen_blue = QPen(self.style.thumbsel_color1, 2)
            painter.setPen(pen_blue)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(-2, -2, 2, 2))

            pen_white = QPen(self.style.thumbsel_color2, 1)
            painter.setPen(pen_white)
            painter.drawRect(rect)

        # Légende sous la miniature (Nom du fichier)
        caption_rect = QRect(rect.x() - 4, rect.bottom() + 2, rect.width() + 8, 14)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#444444"))
        elided = painter.fontMetrics().elidedText(item.filename, Qt.TextElideMode.ElideMiddle, caption_rect.width())
        painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, elided)

    def _get_thumbnail_pixmap(self, item_idx: int) -> Optional[QPixmap]:
        item = self.items[item_idx]
        db_index = item.index

        if db_index in self._pixmap_cache:
            return self._pixmap_cache[db_index]

        # 1. Charger depuis le conteneur binaire thumbs_0.db
        if self.db is not None:
            jpeg_data = self.db.load_thumbnail(db_index)
            if jpeg_data:
                qimg = QImage()
                if qimg.loadFromData(jpeg_data, "JPEG"):
                    pix = QPixmap.fromImage(qimg)
                    self._cache_pixmap(db_index, pix)
                    return pix

        # 2. Secours : charger directement depuis le fichier sur le disque
        if item.path and os.path.exists(item.path):
            pix = QPixmap(item.path)
            if not pix.isNull():
                self._cache_pixmap(db_index, pix)
                return pix

        return None

    def _cache_pixmap(self, db_index: int, pix: QPixmap) -> None:
        if len(self._pixmap_cache) > self._cache_limit:
            # Retirer 100 entrées les plus anciennes
            for k in list(self._pixmap_cache.keys())[:100]:
                del self._pixmap_cache[k]
        self._pixmap_cache[db_index] = pix

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()
        clicked_idx: Optional[int] = None

        for slot_idx, item_idx in enumerate(self.filtered_indices):
            r = self._get_item_rect(slot_idx)
            # Prendre en compte la légende sous la vignette
            click_rect = r.adjusted(0, 0, 0, 16)
            if click_rect.contains(pos):
                clicked_idx = item_idx
                break

        if clicked_idx is not None:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if clicked_idx in self.selected_indices:
                    self.selected_indices.remove(clicked_idx)
                else:
                    self.selected_indices.add(clicked_idx)
            else:
                self.selected_indices = {clicked_idx}

            self.selection_changed.emit(list(self.selected_indices))
            self.update()
        else:
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.selected_indices.clear()
                self.selection_changed.emit([])
                self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()
        for slot_idx, item_idx in enumerate(self.filtered_indices):
            r = self._get_item_rect(slot_idx)
            click_rect = r.adjusted(0, 0, 0, 16)
            if click_rect.contains(pos):
                self.item_double_clicked.emit(item_idx)
                break
