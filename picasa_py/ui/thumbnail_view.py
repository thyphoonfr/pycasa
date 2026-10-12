"""
High-Performance Virtual Thumbnail Grid Component for PyCasa.
Uses custom QPainter with multi-album section layouts and Picasa 3 custom scrollbar.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2] alayout_*, thumbsel_*
Ref: picasa3.exe @ 0x00573767 (thumbui/albumscroll)
Ref: picasa3.exe @ 0x005DE8E0 (scrolling, scrollstart, scrollstop)
Ref: picasa3.exe @ 0x00C968A0 (albumheader)
Ref: AGENTS.md §4 ter (Fluidité de défilement, UI thread non bloqué)
"""

from __future__ import annotations
import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QSize, Signal, QPoint
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage, QMouseEvent,
    QWheelEvent, QPaintEvent, QResizeEvent, QPolygon
)

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.album_scroll import PicasaAlbumScroll
from picasa_py.db.database import PicasaDatabase


def format_ole_date(ole_days: float) -> str:
    """
    Convertit une date OLE Automation (jours depuis le 30/12/1899)
    en texte français lisible (ex. 'Juin 2024').
    Ref: picasa3.exe @ albumdata_date.pmp
    """
    if ole_days <= 0:
        return ""
    try:
        base = datetime(1899, 12, 30)
        dt = base + timedelta(days=ole_days)
        months_fr = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]
        return f"{months_fr[dt.month - 1].capitalize()} {dt.year}"
    except Exception:
        return ""


@dataclass
class ThumbnailItem:
    index: int           # Index dans thumbindex.db et thumbs_0.db
    path: str            # Chemin absolu du fichier image sur disque
    filename: str        # Nom du fichier (ex. IMG_001.jpg)
    folder: str          # Nom du dossier (ex. Vacances)
    folder_path: str     # Chemin complet du dossier (ex. C:\\Photos\\Vacances\\)
    starred: bool = False
    pixmap: Optional[QPixmap] = None
    loading: bool = False


@dataclass
class AlbumSection:
    """
    Section d'album / dossier dans le flux de défilement continu.
    Ref: picasa3.exe @ albumheader (album_title, folderbutton)
    """
    name: str
    folder_path: str
    date_str: str
    item_indices: List[int] = field(default_factory=list)  # Indices dans self.items
    y_start: int = 0
    height: int = 0


class PicasaThumbnailView(QWidget):
    """
    Grille virtuelle de vignettes multi-dossiers haute performance avec rendu QPainter
    et barre de défilement temporelle personnalisée (AVAlbumScroll).
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
        self.sections: List[AlbumSection] = []
        self.visible_sections: List[AlbumSection] = []
        self.filtered_indices: List[int] = []  # Tous les éléments actuellement filtrés
        self.selected_indices: Set[int] = set()

        # Dimensions dynamiques des vignettes
        self.thumb_base_size: int = 140
        self.scroll_y: int = 0
        self.total_content_height: int = 0

        # Cache de vignettes en mémoire
        self._pixmap_cache: Dict[int, QPixmap] = {}
        self._cache_limit: int = 1000

        # En-tête globale / filtre actif
        self.current_folder_filter: Optional[str] = None

        # Barre de défilement personnalisée Picasa 3 (AVAlbumScroll)
        self.scrollbar = PicasaAlbumScroll(style=self.style, parent=self)
        self.scrollbar.set_info_provider(self.get_album_info_at_scroll)
        self.scrollbar.value_changed.connect(self._on_scroll)
        self.scrollbar.jump_prev_album.connect(self._on_jump_prev_album)
        self.scrollbar.jump_next_album.connect(self._on_jump_next_album)

    def set_database(self, db: PicasaDatabase) -> None:
        self.db = db
        self.items.clear()
        self.sections.clear()
        self.selected_indices.clear()
        self._pixmap_cache.clear()

        # 1. Cartographier les répertoires depuis thumbindex.db (type == 1)
        folders = {i: r.path for i, r in enumerate(db.index) if r.type == 1}

        # 2. Cartographier les métadonnées d'albums (albumdata_name, albumdata_date, albumdata_filename)
        album_meta: Dict[str, Tuple[str, str]] = {}  # norm_path -> (name, date_str)
        if "albumdata_filename" in db.pmps and "albumdata_name" in db.pmps:
            fn_pmp = db.pmps["albumdata_filename"].records
            name_pmp = db.pmps["albumdata_name"].records
            date_pmp = db.pmps.get("albumdata_date", None)
            cat_pmp = db.pmps.get("albumdata_category", None)

            for idx, fn in enumerate(fn_pmp):
                if cat_pmp and idx < len(cat_pmp.records) and cat_pmp.records[idx] == 6:
                    continue  # Ignorer les dossiers système de vignettes
                norm = fn.replace("\\", "/").rstrip("/").lower()
                name = name_pmp[idx] if idx < len(name_pmp) and name_pmp[idx] else ""
                ole_d = date_pmp.records[idx] if date_pmp and idx < len(date_pmp.records) else 0.0
                date_str = format_ole_date(ole_d)
                album_meta[norm] = (name, date_str)

        # 3. Filtrer UNIQUEMENT les fichiers média réels (JPG, BMP, PSD, TIFF, RAW, WEBP)
        folder_items_map: Dict[str, List[int]] = {}

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
            item_list_idx = len(self.items)
            self.items.append(item)

            norm_fp = folder_path.replace("\\", "/").rstrip("/").lower()
            if norm_fp not in folder_items_map:
                folder_items_map[norm_fp] = []
            folder_items_map[norm_fp].append(item_list_idx)

        # 4. Construire les sections d'albums pour le défilement continu
        for norm_fp, item_indices in folder_items_map.items():
            first_item = self.items[item_indices[0]]
            # Nom et date depuis albumdata ou dossier
            meta = album_meta.get(norm_fp, ("", ""))
            sec_name = meta[0] if meta[0] else first_item.folder
            sec_date = meta[1]

            sec = AlbumSection(
                name=sec_name,
                folder_path=first_item.folder_path,
                date_str=sec_date,
                item_indices=item_indices,
            )
            self.sections.append(sec)

        self.filter_by_folder(None)

    def filter_by_folder(self, folder_path: Optional[str]) -> None:
        """
        Filtre les vignettes par dossier spécifique, ou affiche l'ensemble
        des albums en flux continu si None (comportement d'origine Picasa 3).
        """
        self.current_folder_filter = folder_path

        if not folder_path:
            self.visible_sections = list(self.sections)
            self.filtered_indices = list(range(len(self.items)))
        else:
            norm_target = folder_path.replace("\\", "/").rstrip("/").lower()
            self.visible_sections = [
                sec for sec in self.sections
                if sec.folder_path.replace("\\", "/").rstrip("/").lower() == norm_target
            ]
            self.filtered_indices = []
            for sec in self.visible_sections:
                self.filtered_indices.extend(sec.item_indices)

        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.set_value(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def set_thumb_size(self, size: int) -> None:
        self.thumb_base_size = max(64, min(320, size))
        self._recompute_layout()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        sb_width = self.scrollbar.width()
        self.scrollbar.setGeometry(self.width() - sb_width, 0, sb_width, self.height())
        self._recompute_layout()

    def _recompute_layout(self) -> None:
        """
        Calcule les coordonnées exactes (Y) de chaque section et vignette.
        Ref: picasa3.exe @ 0x0072E330 (AVCScrollBox bounds calculation)
        """
        available_width = self.width() - self.scrollbar.width() - (self.style.alayout_gutter * 2)
        if available_width <= 0:
            return

        slot_width = self.thumb_base_size + self.style.alayout_thumbGutterX
        cols = max(1, available_width // slot_width)
        slot_height = self.thumb_base_size + self.style.alayout_thumbGutterY + 16

        current_y = 12
        header_height = 42

        for sec in self.visible_sections:
            sec.y_start = current_y
            rows = math.ceil(len(sec.item_indices) / cols) if sec.item_indices else 0
            grid_h = rows * slot_height
            sec.height = header_height + grid_h + 20
            current_y += sec.height

        self.total_content_height = current_y + 40
        max_scroll = max(0, self.total_content_height - self.height())
        self.scrollbar.set_range(0, max_scroll, page_step=self.height())

    def get_album_info_at_scroll(self, scroll_y: int) -> Tuple[str, str]:
        """
        Fournit l'album et la date correspondant à une position de défilement.
        Alimente le badge flottant PicasaScrollTooltip en temps réel.
        Ref: picasa3.exe @ 0x005DE8E0
        """
        if not self.visible_sections:
            return ("", "")

        target_y = scroll_y + 60
        matched_sec = self.visible_sections[0]

        for sec in self.visible_sections:
            if sec.y_start <= target_y:
                matched_sec = sec
            else:
                break

        count_str = f"{len(matched_sec.item_indices)} photos"
        sub = f"{matched_sec.date_str} • {count_str}" if matched_sec.date_str else count_str
        return (matched_sec.name, sub)

    def _on_scroll(self, val: int) -> None:
        self.scroll_y = val
        self.update()

    def _on_jump_prev_album(self) -> None:
        """Saut direct vers l'en-tête de l'album précédent (prevalbum)."""
        curr = self.scroll_y
        target = 0
        for sec in reversed(self.visible_sections):
            if sec.y_start < curr - 20:
                target = sec.y_start
                break
        self.scrollbar.set_value(target)
        self.scroll_y = target
        self.update()

    def _on_jump_next_album(self) -> None:
        """Saut direct vers l'en-tête de l'album suivant (nextalbum)."""
        curr = self.scroll_y
        target = self.scrollbar.max_val
        for sec in self.visible_sections:
            if sec.y_start > curr + 20:
                target = sec.y_start
                break
        self.scrollbar.set_value(target)
        self.scroll_y = target
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        step = 60 if delta > 0 else -60
        new_val = max(0, min(self.scrollbar.max_val, self.scrollbar.value() - step))
        self.scrollbar.set_value(new_val)
        self.scroll_y = new_val
        self.update()

    # -------------------------------------------------------------------------
    # Géométrie & Détection des Clics
    # -------------------------------------------------------------------------
    def _get_item_rect(self, sec: AlbumSection, slot_in_sec: int) -> QRect:
        available_width = self.width() - self.scrollbar.width() - (self.style.alayout_gutter * 2)
        slot_width = self.thumb_base_size + self.style.alayout_thumbGutterX
        cols = max(1, available_width // slot_width)

        col = slot_in_sec % cols
        row = slot_in_sec // cols

        header_height = 42
        slot_height = self.thumb_base_size + self.style.alayout_thumbGutterY + 16

        x = self.style.alayout_gutter + col * slot_width
        y = sec.y_start + header_height + row * slot_height - self.scroll_y
        return QRect(x, y, self.thumb_base_size, self.thumb_base_size)

    def _find_item_at(self, point: QPoint) -> Optional[int]:
        for sec in self.visible_sections:
            if sec.y_start - self.scroll_y > self.height():
                break
            if sec.y_start + sec.height - self.scroll_y < 0:
                continue

            for slot_idx, item_idx in enumerate(sec.item_indices):
                r = self._get_item_rect(sec, slot_idx)
                if r.adjusted(-4, -4, 4, 20).contains(point):
                    return item_idx
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item_idx = self._find_item_at(event.position().toPoint())
            if item_idx is not None:
                modifiers = event.modifiers()
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    if item_idx in self.selected_indices:
                        self.selected_indices.remove(item_idx)
                    else:
                        self.selected_indices.add(item_idx)
                elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                    self.selected_indices.add(item_idx)
                else:
                    self.selected_indices = {item_idx}

                self.update()
                self.selection_changed.emit(list(self.selected_indices))
            else:
                self.selected_indices.clear()
                self.update()
                self.selection_changed.emit([])

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item_idx = self._find_item_at(event.position().toPoint())
            if item_idx is not None:
                self.item_double_clicked.emit(item_idx)

    # -------------------------------------------------------------------------
    # Rendu Graphique (QPainter)
    # -------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Fond de la photothèque
            painter.fillRect(self.rect(), self.style.grid_bgcolor)

            viewport_h = self.height()

            for sec in self.visible_sections:
                sec_top = sec.y_start - self.scroll_y
                sec_bottom = sec_top + sec.height

                # Ne dessiner que les sections recoupant l'écran
                if sec_bottom < -10:
                    continue
                if sec_top > viewport_h + 10:
                    break

                # 1. Dessiner l'en-tête de section (Album Header)
                if sec_top > -45 and sec_top < viewport_h:
                    self._draw_section_header(painter, sec, sec_top)

                # 2. Dessiner les vignettes de la section
                for slot_idx, item_idx in enumerate(sec.item_indices):
                    r = self._get_item_rect(sec, slot_idx)
                    if r.bottom() < -20:
                        continue
                    if r.top() > viewport_h + 20:
                        break

                    self._draw_thumbnail(painter, r, item_idx)
        finally:
            painter.end()

    def _draw_section_header(self, painter: QPainter, sec: AlbumSection, y: int) -> None:
        """
        Dessine l'en-tête d'album emblématique de Picasa (icône dossier, titre, date, diaporama).
        Ref: picasa3.exe @ albumheader (0x00C968A0)
        """
        header_w = self.width() - self.scrollbar.width() - 20
        header_rect = QRect(10, y + 2, header_w, 36)

        # Ligne de séparation supérieure discrète
        painter.setPen(QColor("#24272D"))
        painter.drawLine(10, y, 10 + header_w, y)

        # Fond subtil d'en-tête
        painter.fillRect(header_rect, QColor(36, 39, 45, 140))

        # Icône de dossier Picasa (pictogramme stylisé)
        icon_x = 18
        icon_y = y + 10
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#3E82B8"))
        painter.drawRoundedRect(QRect(icon_x, icon_y + 3, 16, 12), 2, 2)
        painter.drawRoundedRect(QRect(icon_x + 1, icon_y, 7, 5), 1, 1)

        # Titre de l'album / dossier (en gras)
        title_x = icon_x + 24
        painter.setFont(QFont("Tahoma", 10, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(title_x, y + 22, sec.name)

        # Métadonnées : Date et nombre de photos
        metrics = painter.fontMetrics()
        title_width = metrics.horizontalAdvance(sec.name)

        date_x = title_x + title_width + 14
        count_str = f"{len(sec.item_indices)} photos"
        meta_str = f"—   {sec.date_str}   •   {count_str}" if sec.date_str else f"—   {count_str}"

        painter.setFont(QFont("Tahoma", 9))
        painter.setPen(QColor("#8E96A4"))
        painter.drawText(date_x, y + 22, meta_str)

        # Bouton Diaporama / Lecture à droite
        btn_w = 90
        btn_x = header_w - btn_w
        btn_rect = QRect(btn_x, y + 7, btn_w, 24)
        painter.setPen(QPen(QColor("#454C57"), 1))
        painter.setBrush(QColor("#2C3038"))
        painter.drawRoundedRect(btn_rect, 3, 3)

        # Triangle lecture vert Picasa
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#5CB85C"))
        play_poly = QPolygon([
            QPoint(btn_x + 10, y + 13),
            QPoint(btn_x + 18, y + 19),
            QPoint(btn_x + 10, y + 25),
        ])
        painter.drawPolygon(play_poly)

        painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#CCCCCC"))
        painter.drawText(btn_x + 24, y + 23, "Diaporama")

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
        painter.setFont(QFont(self.style.alayout_titleFont, 8))
        painter.setPen(QColor("#DDDDDD") if is_selected else QColor("#999999"))
        elided_name = painter.fontMetrics().elidedText(item.filename, Qt.TextElideMode.ElideMiddle, caption_rect.width())
        painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, elided_name)

    def _get_thumbnail_pixmap(self, item_idx: int) -> Optional[QPixmap]:
        """Récupération de la vignette avec mise en cache mémoire."""
        if item_idx in self._pixmap_cache:
            return self._pixmap_cache[item_idx]

        if self.db is None:
            return None

        item = self.items[item_idx]
        raw_bytes = self.db.get_thumbnail(item.index)

        if raw_bytes:
            img = QImage.fromData(raw_bytes)
            if not img.isNull():
                pix = QPixmap.fromImage(img)
                if len(self._pixmap_cache) < self._cache_limit:
                    self._pixmap_cache[item_idx] = pix
                return pix

        # Fallback si absent du cache binaire Picasa
        if os.path.exists(item.path):
            img = QImage(item.path)
            if not img.isNull():
                pix = QPixmap.fromImage(img.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio))
                if len(self._pixmap_cache) < self._cache_limit:
                    self._pixmap_cache[item_idx] = pix
                return pix

        return None
