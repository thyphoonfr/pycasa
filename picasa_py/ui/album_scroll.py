"""
Custom Album Scrollbar Component for PyCasa (AVAlbumScroll / AVCScrollBox / AVCScrollThrottle).

Reproduces Picasa 3's iconic smooth vertical timeline scrollbar:
- Custom dark sleek track (thumbui/albumscroll)
- Capsule thumb handle with subtle gradients (AVCScrollBox)
- Floating Date & Album Tooltip Badge (AVytToolTip) tracking the thumb
- Step buttons (albumscrolltop, albumscrollbottom)
- Fast album jump buttons (prevalbum, nextalbum)
- Smooth throttling physics (AVCScrollThrottle)

Ref: picasa3.exe @ 0x00573767 (thumbui/albumscroll init)
Ref: picasa3.exe @ 0x005DE8E0 (scrollstart, scrolling, scrollstop handlers)
Ref: picasa3.exe @ 0x0072E520 (AVCScrollBox constructor)
Ref: picasa3.exe @ 0x0072E330 (AVCScrollBox layout & range calculation)
Ref: picasa3.exe @ 0x00C96818 (throttle/albumscrolltop)
Ref: picasa3.exe @ 0x00C96830 (throttle/albumscrollbottom)
"""

from __future__ import annotations
import math
from typing import Callable, Optional, Tuple
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QLinearGradient,
    QPainterPath, QPolygon, QMouseEvent, QWheelEvent, QPaintEvent
)

from picasa_py.ui.style import PicasaStyle


class PicasaScrollTooltip(QWidget):
    """
    Badge flottant affichant l'Album et la Date en regard du curseur de défilement.
    Ref: picasa3.exe @ 0x005DE8E0 (AVytToolTip / AVCScrollBox indicator)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

        self.title_text: str = ""
        self.subtitle_text: str = ""
        self.fixed_height: int = 42
        self.min_width: int = 150
        self.pointer_size: int = 6  # Taille de la flèche pointant vers le curseur

    def set_content(self, title: str, subtitle: str) -> None:
        self.title_text = title
        self.subtitle_text = subtitle
        # Calcul de la largeur optimale
        font_title = QFont("Tahoma", 10, QFont.Weight.Bold)
        font_sub = QFont("Tahoma", 8)
        self.adjustSize()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.title_text and not self.subtitle_text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width() - self.pointer_size - 1
        h = self.height() - 2

        # 1. Tracé du corps avec pointeur à droite
        path = QPainterPath()
        rect = QRect(1, 1, w, h)
        path.addRoundedRect(rect, 5.0, 5.0)

        # Flèche pointant vers le thumb à droite
        cy = h // 2 + 1
        pointer = QPolygon([
            QPoint(w, cy - self.pointer_size),
            QPoint(w + self.pointer_size, cy),
            QPoint(w, cy + self.pointer_size),
        ])
        path.addPolygon(pointer)

        # 2. Ombre et Fond
        painter.fillPath(path, QColor(24, 26, 30, 235))
        painter.setPen(QPen(QColor(85, 91, 102, 220), 1))
        painter.drawPath(path)

        # 3. Titre (Nom du dossier / Album)
        painter.setFont(QFont("Tahoma", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF"))
        title_rect = QRect(10, 6, w - 16, 16)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            painter.fontMetrics().elidedText(self.title_text, Qt.TextElideMode.ElideRight, w - 16)
        )

        # 4. Sous-titre (Date & Compte de photos)
        painter.setFont(QFont("Tahoma", 8))
        painter.setPen(QColor("#9CA3AF"))
        sub_rect = QRect(10, 22, w - 16, 14)
        painter.drawText(
            sub_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            painter.fontMetrics().elidedText(self.subtitle_text, Qt.TextElideMode.ElideRight, w - 16)
        )


class PicasaAlbumScroll(QWidget):
    """
    Barre de défilement verticale personnalisée de Picasa 3 (AVAlbumScroll).
    Gère le curseur capsule, les boutons de saut d'album et le badge flottant temporel.
    """
    value_changed = Signal(int)
    jump_prev_album = Signal()
    jump_next_album = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.setMouseTracking(True)
        self.setFixedWidth(18)

        # Plage de défilement
        self.min_val: int = 0
        self.max_val: int = 0
        self.cur_val: int = 0
        self.page_step: int = 100

        # États interactifs
        self._hover_thumb: bool = False
        self._dragging_thumb: bool = False
        self._drag_start_y: int = 0
        self._drag_start_val: int = 0

        # Boutons de navigation (hauteurs en pixels)
        self.btn_size: int = 16
        self.album_btn_size: int = 14

        # Callback externe pour obtenir les métadonnées (album, date) pour un scroll_y donné
        self.info_provider: Optional[Callable[[int], Tuple[str, str]]] = None

        # Badge flottant (géré sur le parent)
        self.tooltip = PicasaScrollTooltip(self.parentWidget())

        # Timer pour masquer le badge après inactivité
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(700)
        self._hide_timer.timeout.connect(self._on_hide_tooltip)

    # -------------------------------------------------------------------------
    # Géométrie & Tailles
    # -------------------------------------------------------------------------
    @property
    def track_top(self) -> int:
        """Début de la zone de glisse (sous les boutons du haut)."""
        return self.btn_size + self.album_btn_size + 4

    @property
    def track_bottom(self) -> int:
        """Fin de la zone de glisse (au-dessus des boutons du bas)."""
        return self.height() - (self.btn_size + self.album_btn_size + 4)

    @property
    def track_height(self) -> int:
        return max(20, self.track_bottom - self.track_top)

    def _get_thumb_rect(self) -> QRect:
        """Calcule le rectangle du curseur (thumb) proportionnel au contenu."""
        if self.max_val <= self.min_val or self.track_height <= 0:
            return QRect(2, self.track_top, self.width() - 4, self.track_height)

        total_range = (self.max_val - self.min_val) + self.page_step
        proportion = self.page_step / max(1, total_range)
        thumb_h = max(24, int(self.track_height * proportion))
        thumb_h = min(self.track_height, thumb_h)

        usable_track = self.track_height - thumb_h
        val_range = self.max_val - self.min_val
        ratio = (self.cur_val - self.min_val) / max(1, val_range)
        thumb_y = self.track_top + int(usable_track * ratio)

        return QRect(3, thumb_y, self.width() - 6, thumb_h)

    # -------------------------------------------------------------------------
    # API Publique
    # -------------------------------------------------------------------------
    def set_range(self, min_val: int, max_val: int, page_step: int = 100) -> None:
        self.min_val = min_val
        self.max_val = max(min_val, max_val)
        self.page_step = max(1, page_step)
        self.cur_val = max(self.min_val, min(self.max_val, self.cur_val))
        self.update()

    def set_value(self, val: int) -> None:
        val = max(self.min_val, min(self.max_val, val))
        if val != self.cur_val:
            self.cur_val = val
            self.update()
            self._update_tooltip_position()

    def value(self) -> int:
        return self.cur_val

    def set_info_provider(self, provider: Callable[[int], Tuple[str, str]]) -> None:
        self.info_provider = provider

    # -------------------------------------------------------------------------
    # Gestion du Badge Flottant
    # -------------------------------------------------------------------------
    def _show_tooltip_for_val(self, val: int, thumb_center_y: int) -> None:
        if not self.info_provider or self.parentWidget() is None:
            return

        title, subtitle = self.info_provider(val)
        if not title and not subtitle:
            self.tooltip.hide()
            return

        self._hide_timer.stop()
        self.tooltip.set_content(title, subtitle)

        # Calcul de la position globale par rapport au parent
        tip_w = 200
        tip_h = 42
        self.tooltip.resize(tip_w, tip_h)

        # Aligné à gauche de la scrollbar, centré verticalement sur thumb_center_y
        pos_in_parent = self.mapTo(self.parentWidget(), QPoint(0, thumb_center_y))
        tip_x = max(10, pos_in_parent.x() - tip_w - 4)
        tip_y = max(10, min(self.parentWidget().height() - tip_h - 10, pos_in_parent.y() - tip_h // 2))

        self.tooltip.move(tip_x, tip_y)
        self.tooltip.show()
        self.tooltip.raise_()

    def _update_tooltip_position(self) -> None:
        if self._dragging_thumb or self._hover_thumb:
            thumb_r = self._get_thumb_rect()
            self._show_tooltip_for_val(self.cur_val, thumb_r.center().y())

    def _on_hide_tooltip(self) -> None:
        if not self._dragging_thumb:
            self.tooltip.hide()

    # -------------------------------------------------------------------------
    # Événements Souris & Défilement
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        y = event.position().y()
        thumb_r = self._get_thumb_rect()

        # 1. Clic sur le bouton Haut (step up)
        if y < self.btn_size:
            self.set_value(self.cur_val - 40)
            self.value_changed.emit(self.cur_val)
            return

        # 2. Clic sur Saut Dossier Précédent (prevalbum)
        if y < self.btn_size + self.album_btn_size:
            self.jump_prev_album.emit()
            return

        # 3. Clic sur Saut Dossier Suivant (nextalbum)
        if y > self.height() - (self.btn_size + self.album_btn_size) and y < self.height() - self.btn_size:
            self.jump_next_album.emit()
            return

        # 4. Clic sur le bouton Bas (step down)
        if y >= self.height() - self.btn_size:
            self.set_value(self.cur_val + 40)
            self.value_changed.emit(self.cur_val)
            return

        # 5. Clic sur le curseur (Thumb) -> début du drag
        if thumb_r.contains(event.position().toPoint()):
            self._dragging_thumb = True
            self._drag_start_y = y
            self._drag_start_val = self.cur_val
            self._update_tooltip_position()
            self.update()
            return

        # 6. Clic dans la piste hors du thumb -> saut proportionnel ou page
        if self.track_top <= y <= self.track_bottom:
            usable = self.track_height - thumb_r.height()
            if usable > 0:
                rel_y = max(0, min(usable, (y - self.track_top - thumb_r.height() / 2)))
                new_val = int(self.min_val + (rel_y / usable) * (self.max_val - self.min_val))
                self.set_value(new_val)
                self.value_changed.emit(self.cur_val)
                self._update_tooltip_position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        y = event.position().y()
        thumb_r = self._get_thumb_rect()

        if self._dragging_thumb:
            usable = self.track_height - thumb_r.height()
            if usable > 0:
                delta_y = y - self._drag_start_y
                delta_val = int((delta_y / usable) * (self.max_val - self.min_val))
                new_val = max(self.min_val, min(self.max_val, self._drag_start_val + delta_val))
                self.set_value(new_val)
                self.value_changed.emit(self.cur_val)
            return

        # Survol du thumb ou de la piste
        is_hover = thumb_r.contains(event.position().toPoint())
        if is_hover != self._hover_thumb:
            self._hover_thumb = is_hover
            self.update()

        # Si survol de la piste, prévisualiser la date/album à cette position
        if self.track_top <= y <= self.track_bottom:
            usable = self.track_height - thumb_r.height()
            if usable > 0:
                rel_y = max(0, min(usable, (y - self.track_top - thumb_r.height() / 2)))
                hover_val = int(self.min_val + (rel_y / usable) * (self.max_val - self.min_val))
                self._show_tooltip_for_val(hover_val, int(y))
        else:
            self._hide_timer.start()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging_thumb = False
            self.update()
            self._hide_timer.start()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hover_thumb = False
        self.update()
        if not self._dragging_thumb:
            self._hide_timer.start()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        step = 40 if delta > 0 else -40
        self.set_value(self.cur_val - step)
        self.value_changed.emit(self.cur_val)

    # -------------------------------------------------------------------------
    # Rendu Graphique (QPainter)
    # -------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 1. Piste de défilement (thumbui/albumscroll)
            painter.fillRect(self.rect(), QColor("#282B30"))
            painter.setPen(QColor("#1E2024"))
            painter.drawLine(0, 0, 0, self.height())

            # 2. Boutons de navigation Haut
            self._draw_arrow_button(painter, 0, 0, self.width(), self.btn_size, up=True, double=False)
            self._draw_arrow_button(painter, 0, self.btn_size, self.width(), self.album_btn_size, up=True, double=True)

            # 3. Curseur (Thumb - AVCScrollBox)
            thumb_r = self._get_thumb_rect()
            if self.max_val > self.min_val:
                self._draw_thumb(painter, thumb_r)

            # 4. Boutons de navigation Bas
            next_album_y = self.height() - (self.btn_size + self.album_btn_size)
            self._draw_arrow_button(painter, 0, next_album_y, self.width(), self.album_btn_size, up=False, double=True)
            self._draw_arrow_button(painter, 0, self.height() - self.btn_size, self.width(), self.btn_size, up=False, double=False)
        finally:
            painter.end()

    def _draw_thumb(self, painter: QPainter, rect: QRect) -> None:
        """Dessine la capsule du curseur avec reflets et états."""
        painter.save()
        radius = 4.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # Gradient vertical selon l'état
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        if self._dragging_thumb:
            gradient.setColorAt(0.0, QColor("#858D9C"))
            gradient.setColorAt(1.0, QColor("#6B7382"))
            border_color = QColor("#A0A8B8")
        elif self._hover_thumb:
            gradient.setColorAt(0.0, QColor("#707886"))
            gradient.setColorAt(1.0, QColor("#5A626F"))
            border_color = QColor("#8A93A3")
        else:
            gradient.setColorAt(0.0, QColor("#5A616E"))
            gradient.setColorAt(1.0, QColor("#464C57"))
            border_color = QColor("#6B7382")

        painter.fillPath(path, gradient)
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

        # Petites rainures centrales décoratives de Picasa
        cy = rect.center().y()
        cx = rect.center().x()
        groove_pen = QPen(QColor(0, 0, 0, 70), 1)
        groove_light = QPen(QColor(255, 255, 255, 50), 1)
        for offset in (-3, 0, 3):
            painter.setPen(groove_pen)
            painter.drawLine(cx - 3, cy + offset, cx + 3, cy + offset)
            painter.setPen(groove_light)
            painter.drawLine(cx - 3, cy + offset + 1, cx + 3, cy + offset + 1)

        painter.restore()

    def _draw_arrow_button(
        self, painter: QPainter, x: int, y: int, w: int, h: int, up: bool, double: bool
    ) -> None:
        """Dessine les flèches de navigation simples ou doubles (album)."""
        painter.save()
        cx = x + w // 2
        cy = y + h // 2
        arrow_color = QColor("#8A92A0")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(arrow_color)

        if not double:
            # Flèche simple (scrolltop / scrollbottom)
            if up:
                pts = [QPoint(cx, cy - 3), QPoint(cx - 4, cy + 2), QPoint(cx + 4, cy + 2)]
            else:
                pts = [QPoint(cx, cy + 3), QPoint(cx - 4, cy - 2), QPoint(cx + 4, cy - 2)]
            painter.drawPolygon(QPolygon(pts))
        else:
            # Double chevron (prevalbum / nextalbum)
            pen = QPen(arrow_color, 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if up:
                painter.drawLine(cx - 3, cy - 1, cx, cy - 4)
                painter.drawLine(cx, cy - 4, cx + 3, cy - 1)
                painter.drawLine(cx - 3, cy + 3, cx, cy)
                painter.drawLine(cx, cy, cx + 3, cy + 3)
            else:
                painter.drawLine(cx - 3, cy - 3, cx, cy)
                painter.drawLine(cx, cy, cx + 3, cy - 3)
                painter.drawLine(cx - 3, cy + 1, cx, cy + 4)
                painter.drawLine(cx, cy + 4, cx + 3, cy + 1)

        painter.restore()
