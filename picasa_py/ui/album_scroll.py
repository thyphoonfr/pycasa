"""
Custom Album Scroll Throttle Component for PyCasa (AVCScrollThrottle / AVAlbumScroll).

Faithfully reproduces Picasa 3's iconic spring-loaded center throttle scrollbar:
- Throttle handle resting at the vertical center of the track.
- Dragging UP scrolls back in time; dragging DOWN scrolls forward in time.
- Speed increases non-linearly with distance from center (fine control near center, rapid scrub at extremes).
- Spring-loaded return: on mouse release, the handle snaps back to the center notch.
- Floating Date & Album Tooltip Badge (PicasaScrollTooltip) following the throttle handle.
- Directional tension indicator connecting center notch to the handle.
- Step buttons (throttle/albumscrolltop, throttle/albumscrollbottom).
- Album jump buttons (throttle/prevalbum, throttle/nextalbum).

Ref: picasa3.exe @ 0x0072E6E6, 0x00CAD944 (AVCScrollThrottle constructor & vtable)
Ref: picasa3.exe @ 0x0072E330 (AVCScrollThrottle bounds & range calculation)
Ref: picasa3.exe @ 0x005DE8E0 (scrollstart, scrolling, scrollstop handlers)
Ref: picasa3.exe @ 0x005CE090 (scrolling physics update)
Ref: picasa3.exe @ 0x00C96818 (throttle/albumscrolltop)
Ref: picasa3.exe @ 0x00C96830 (throttle/albumscrollbottom)
"""

from __future__ import annotations
import math
import time
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
    Badge flottant chronologique affichant l'Album et la Date en regard du curseur throttle.
    Ref: picasa3.exe @ 0x005DE8E0 (AVytToolTip indicator)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

        self.title_text: str = ""
        self.subtitle_text: str = ""
        self.pointer_size: int = 6

    def set_content(self, title: str, subtitle: str) -> None:
        self.title_text = title
        self.subtitle_text = subtitle
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.title_text and not self.subtitle_text:
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width() - self.pointer_size - 1
            h = self.height() - 2

            # 1. Tracé du corps arrondi avec pointeur triangulaire à droite vers le curseur
            path = QPainterPath()
            rect = QRect(1, 1, w, h)
            path.addRoundedRect(rect, 5.0, 5.0)

            cy = h // 2 + 1
            pointer = QPolygon([
                QPoint(w, cy - self.pointer_size),
                QPoint(w + self.pointer_size, cy),
                QPoint(w, cy + self.pointer_size),
            ])
            path.addPolygon(pointer)

            # 2. Fond semi-transparent sombre et liseré
            painter.fillPath(path, QColor(24, 26, 30, 238))
            painter.setPen(QPen(QColor(85, 91, 102, 220), 1))
            painter.drawPath(path)

            # 3. Titre de l'album / dossier en cours
            painter.setFont(QFont("Tahoma", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            title_rect = QRect(10, 6, w - 16, 16)
            elided_title = painter.fontMetrics().elidedText(self.title_text, Qt.TextElideMode.ElideRight, w - 16)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_title)

            # 4. Date et décompte de photos
            painter.setFont(QFont("Tahoma", 8))
            painter.setPen(QColor("#9CA3AF"))
            sub_rect = QRect(10, 22, w - 16, 14)
            elided_sub = painter.fontMetrics().elidedText(self.subtitle_text, Qt.TextElideMode.ElideRight, w - 16)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_sub)
        finally:
            painter.end()


class PicasaAlbumScroll(QWidget):
    """
    Système de défilement par manette des gaz / jog-shuttle (AVCScrollThrottle).
    Le curseur reste centré au repos. Glisser vers le haut/bas fait défiler le contenu
    à une vitesse proportionnelle à l'écartement. Au relâchement, le curseur revient au centre.
    """
    value_changed = Signal(int)
    jump_prev_album = Signal()
    jump_next_album = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.setMouseTracking(True)
        self.setFixedWidth(20)

        # Plage de défilement du contenu
        self.min_val: int = 0
        self.max_val: int = 0
        self.cur_val: float = 0.0
        self.page_step: int = 100

        # Boutons de navigation (haut et bas)
        self.btn_size: int = 16
        self.album_btn_size: int = 14

        # Dimensions du curseur throttle (capsule)
        self.thumb_width: int = 14
        self.thumb_height: int = 28

        # Position verticale actuelle du curseur (en pixels)
        self._thumb_y: float = 0.0

        # États interactifs
        self._hover_thumb: bool = False
        self._is_throttling: bool = False
        self._throttle_speed: float = 0.0  # pixels par seconde
        self._last_tick_time: float = 0.0

        # Callback externe pour obtenir les métadonnées (album, date) pour un scroll_y donné
        self.info_provider: Optional[Callable[[int], Tuple[str, str]]] = None

        # Badge flottant (géré sur le parent)
        self.tooltip = PicasaScrollTooltip(self.parentWidget())

        # Timer de défilement continu pendant le throttle (60 FPS / 16ms)
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setInterval(16)
        self._throttle_timer.timeout.connect(self._on_throttle_tick)

        # Timer d'animation de retour élastique (spring-back) vers le centre
        self._spring_timer = QTimer(self)
        self._spring_timer.setInterval(16)
        self._spring_timer.timeout.connect(self._on_spring_tick)

        # Timer pour masquer le badge après inactivité
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(700)
        self._hide_timer.timeout.connect(self._on_hide_tooltip)

    # -------------------------------------------------------------------------
    # Géométrie & Repères
    # -------------------------------------------------------------------------
    @property
    def track_top(self) -> int:
        return self.btn_size + self.album_btn_size + 4

    @property
    def track_bottom(self) -> int:
        return self.height() - (self.btn_size + self.album_btn_size + 4)

    @property
    def track_height(self) -> int:
        return max(40, self.track_bottom - self.track_top)

    @property
    def center_y(self) -> int:
        """Position Y du point mort central (neutre)."""
        return self.track_top + self.track_height // 2

    @property
    def rest_thumb_y(self) -> float:
        """Position Y du curseur au repos (centré)."""
        return float(self.center_y - self.thumb_height // 2)

    @property
    def max_deflection(self) -> float:
        """Déviation maximale du curseur vers le haut ou vers le bas."""
        return max(20.0, (self.track_height / 2.0) - (self.thumb_height / 2.0) - 2.0)

    def _get_thumb_rect(self) -> QRect:
        x = (self.width() - self.thumb_width) // 2
        if self._is_throttling or self._spring_timer.isActive():
            y = int(self._thumb_y)
        else:
            y = int(self.rest_thumb_y)
        return QRect(x, y, self.thumb_width, self.thumb_height)

    # -------------------------------------------------------------------------
    # API Publique
    # -------------------------------------------------------------------------
    def set_range(self, min_val: int, max_val: int, page_step: int = 100) -> None:
        self.min_val = min_val
        self.max_val = max(min_val, max_val)
        self.page_step = max(1, page_step)
        self.cur_val = max(float(self.min_val), min(float(self.max_val), self.cur_val))
        if not self._is_throttling and not self._spring_timer.isActive():
            self._thumb_y = self.rest_thumb_y
        self.update()

    def set_value(self, val: int) -> None:
        clamped = max(float(self.min_val), min(float(self.max_val), float(val)))
        if clamped != self.cur_val:
            self.cur_val = clamped
            self.update()

    def value(self) -> int:
        return int(self.cur_val)

    def set_info_provider(self, provider: Callable[[int], Tuple[str, str]]) -> None:
        self.info_provider = provider

    # -------------------------------------------------------------------------
    # Physique du Throttle & Animation Ressort (AVCScrollThrottle)
    # -------------------------------------------------------------------------
    def _update_throttle_from_mouse_y(self, mouse_y: float) -> None:
        """
        Calcule la déviation du curseur par rapport au centre et la vitesse associée.
        Ref: picasa3.exe @ 0x0072E330, 0x005CE090
        """
        self._is_throttling = True
        raw_delta = mouse_y - float(self.center_y)
        max_d = self.max_deflection

        # Déviation bornée
        clamped_d = max(-max_d, min(max_d, raw_delta))
        self._thumb_y = float(self.center_y) + clamped_d - (self.thumb_height / 2.0)

        # Zone morte centrale (3 pixels) pour éviter toute dérive au point mort
        dead_zone = 3.0
        abs_d = abs(clamped_d)
        if abs_d <= dead_zone:
            self._throttle_speed = 0.0
        else:
            # Facteur normalisé entre 0.0 et 1.0
            u = (abs_d - dead_zone) / (max_d - dead_zone)
            direction = 1.0 if clamped_d > 0 else -1.0

            # Courbe de vitesse progressive non-linéaire :
            # vitesse douce au départ, accélération rapide en bout de course
            base_v = u * 120.0             # Contrôle fin
            quad_v = (u ** 2) * 600.0      # Balayage fluide
            cubic_v = (u ** 3) * 2200.0    # Défilement ultra-rapide
            self._throttle_speed = direction * (base_v + quad_v + cubic_v)

        self._update_tooltip_position()
        self.update()

    def _on_throttle_tick(self) -> None:
        """Horloge 60 FPS du défilement continu proportionnel."""
        now = time.time()
        if self._last_tick_time == 0.0:
            dt = 0.016
        else:
            dt = max(0.001, min(0.050, now - self._last_tick_time))
        self._last_tick_time = now

        if self._throttle_speed != 0.0 and self.max_val > self.min_val:
            delta_px = self._throttle_speed * dt
            new_val = max(float(self.min_val), min(float(self.max_val), self.cur_val + delta_px))
            if new_val != self.cur_val:
                self.cur_val = new_val
                self.value_changed.emit(int(self.cur_val))
                self._update_tooltip_position()

    def _on_spring_tick(self) -> None:
        """Animation de retour élastique vers le centre au relâchement de la souris."""
        target_y = self.rest_thumb_y
        diff = target_y - self._thumb_y

        if abs(diff) < 0.8:
            self._thumb_y = target_y
            self._spring_timer.stop()
        else:
            # Interpolation élastique progressive (facteur 0.30)
            self._thumb_y += diff * 0.30

        self.update()

    # -------------------------------------------------------------------------
    # Gestion du Badge Flottant Chronologique
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

        tip_w = 200
        tip_h = 42
        self.tooltip.resize(tip_w, tip_h)

        pos_in_parent = self.mapTo(self.parentWidget(), QPoint(0, thumb_center_y))
        tip_x = max(10, pos_in_parent.x() - tip_w - 4)
        tip_y = max(10, min(self.parentWidget().height() - tip_h - 10, pos_in_parent.y() - tip_h // 2))

        self.tooltip.move(tip_x, tip_y)
        self.tooltip.show()
        self.tooltip.raise_()

    def _update_tooltip_position(self) -> None:
        if self._is_throttling or self._hover_thumb:
            thumb_r = self._get_thumb_rect()
            self._show_tooltip_for_val(int(self.cur_val), thumb_r.center().y())

    def _on_hide_tooltip(self) -> None:
        if not self._is_throttling:
            self.tooltip.hide()

    # -------------------------------------------------------------------------
    # Événements Souris
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        y = event.position().y()

        # 1. Bouton Haut (step up)
        if y < self.btn_size:
            self.set_value(int(self.cur_val) - 60)
            self.value_changed.emit(int(self.cur_val))
            return

        # 2. Bouton Saut Album Précédent (prevalbum)
        if y < self.btn_size + self.album_btn_size:
            self.jump_prev_album.emit()
            return

        # 3. Bouton Saut Album Suivant (nextalbum)
        if y > self.height() - (self.btn_size + self.album_btn_size) and y < self.height() - self.btn_size:
            self.jump_next_album.emit()
            return

        # 4. Bouton Bas (step down)
        if y >= self.height() - self.btn_size:
            self.set_value(int(self.cur_val) + 60)
            self.value_changed.emit(int(self.cur_val))
            return

        # 5. Zone de glisse Throttle
        if self.track_top <= y <= self.track_bottom:
            self._spring_timer.stop()
            self._is_throttling = True
            self._last_tick_time = time.time()
            self._update_throttle_from_mouse_y(y)
            self._throttle_timer.start()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        y = event.position().y()
        thumb_r = self._get_thumb_rect()

        if self._is_throttling:
            self._update_throttle_from_mouse_y(y)
            return

        is_hover = thumb_r.contains(event.position().toPoint())
        if is_hover != self._hover_thumb:
            self._hover_thumb = is_hover
            self.update()

        if is_hover:
            self._update_tooltip_position()
        else:
            self._hide_timer.start()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_throttling:
            self._is_throttling = False
            self._throttle_speed = 0.0
            self._throttle_timer.stop()
            # Déclencher le retour élastique au centre
            self._spring_timer.start()
            self._hide_timer.start()
            self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hover_thumb = False
        self.update()
        if not self._is_throttling:
            self._hide_timer.start()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        step = 60 if delta > 0 else -60
        self.set_value(int(self.cur_val) - step)
        self.value_changed.emit(int(self.cur_val))

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

            # 3. Marque neutre centrale (Point mort de repos du throttle)
            cx = self.width() // 2
            cy = self.center_y
            painter.setPen(QPen(QColor("#454C57"), 1))
            painter.drawLine(cx - 5, cy, cx + 5, cy)
            painter.setPen(QPen(QColor("#1E2024"), 1))
            painter.drawLine(cx - 5, cy + 1, cx + 5, cy + 1)

            # 4. Ruban de tension / vitesse lors de l'écartement
            thumb_r = self._get_thumb_rect()
            thumb_cy = thumb_r.center().y()
            if abs(thumb_cy - cy) > 2:
                self._draw_tension_indicator(painter, cx, cy, thumb_cy)

            # 5. Curseur Throttle (Capsule avec rainures Picasa)
            self._draw_throttle_thumb(painter, thumb_r)

            # 6. Boutons de navigation Bas
            next_album_y = self.height() - (self.btn_size + self.album_btn_size)
            self._draw_arrow_button(painter, 0, next_album_y, self.width(), self.album_btn_size, up=False, double=True)
            self._draw_arrow_button(painter, 0, self.height() - self.btn_size, self.width(), self.btn_size, up=False, double=False)
        finally:
            painter.end()

    def _draw_tension_indicator(self, painter: QPainter, cx: int, cy: int, thumb_cy: int) -> None:
        """Trace le ruban indicateur reliant le centre au curseur pour matérialiser la poussée."""
        top_y = min(cy, thumb_cy)
        bottom_y = max(cy, thumb_cy)
        h = bottom_y - top_y

        glow_rect = QRect(cx - 3, top_y, 6, h)
        gradient = QLinearGradient(0, top_y, 0, bottom_y)
        if thumb_cy < cy:
            # Vers le haut : défilement arrière
            gradient.setColorAt(0.0, QColor(62, 130, 184, 180))
            gradient.setColorAt(1.0, QColor(62, 130, 184, 40))
        else:
            # Vers le bas : défilement avant
            gradient.setColorAt(0.0, QColor(62, 130, 184, 40))
            gradient.setColorAt(1.0, QColor(62, 130, 184, 180))

        painter.fillRect(glow_rect, gradient)

    def _draw_throttle_thumb(self, painter: QPainter, rect: QRect) -> None:
        """Dessine la capsule du curseur throttle avec reflets et rainures."""
        painter.save()
        radius = 5.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # Dégradé métallique selon l'état
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        if self._is_throttling:
            gradient.setColorAt(0.0, QColor("#858D9C"))
            gradient.setColorAt(0.5, QColor("#757D8C"))
            gradient.setColorAt(1.0, QColor("#636B7A"))
            border_color = QColor("#A0A8B8")
        elif self._hover_thumb:
            gradient.setColorAt(0.0, QColor("#707886"))
            gradient.setColorAt(0.5, QColor("#626A78"))
            gradient.setColorAt(1.0, QColor("#545B67"))
            border_color = QColor("#8A93A3")
        else:
            gradient.setColorAt(0.0, QColor("#5A616E"))
            gradient.setColorAt(0.5, QColor("#4E5562"))
            gradient.setColorAt(1.0, QColor("#404651"))
            border_color = QColor("#6B7382")

        painter.fillPath(path, gradient)
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

        # Rainures centrales de préhension (3 stries caractéristiques de Picasa)
        cy = rect.center().y()
        cx = rect.center().x()
        groove_pen = QPen(QColor(0, 0, 0, 80), 1)
        groove_light = QPen(QColor(255, 255, 255, 60), 1)
        for offset in (-4, 0, 4):
            painter.setPen(groove_pen)
            painter.drawLine(cx - 4, cy + offset, cx + 4, cy + offset)
            painter.setPen(groove_light)
            painter.drawLine(cx - 4, cy + offset + 1, cx + 4, cy + offset + 1)

        painter.restore()

    def _draw_arrow_button(
        self, painter: QPainter, x: int, y: int, w: int, h: int, up: bool, double: bool
    ) -> None:
        painter.save()
        cx = x + w // 2
        cy = y + h // 2
        arrow_color = QColor("#8A92A0")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(arrow_color)

        if not double:
            if up:
                pts = [QPoint(cx, cy - 3), QPoint(cx - 4, cy + 2), QPoint(cx + 4, cy + 2)]
            else:
                pts = [QPoint(cx, cy + 3), QPoint(cx - 4, cy - 2), QPoint(cx + 4, cy - 2)]
            painter.drawPolygon(QPolygon(pts))
        else:
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
