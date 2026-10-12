"""
High-Resolution Interactive Image Canvas for PyCasa One-Up View.
Supports smooth zooming, panning, rotation, and non-destructive preview.

Ref: picasa3.exe @ OneUp, AVOneUpUI
Ref: AGENTS.md §4 bis (Fonctionnement identique: zoom, pan, molette)
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPixmap, QImage, QMouseEvent, QWheelEvent,
    QPaintEvent, QResizeEvent, QCursor, QPen
)
from PIL import Image

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle


# Ref: picasa3.exe @ OneUp
class PicasaImageCanvas(QWidget):
    """
    Zone d'affichage haute résolution d'une photo avec zoom, panoramique (pan),
    et affichage temps réel des retouches.
    """
    zoom_changed = Signal(float)
    navigate_prev = Signal()
    navigate_next = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.image_path: Optional[str] = None
        self._raw_pixmap: Optional[QPixmap] = None
        self._display_pixmap: Optional[QPixmap] = None

        # Paramètres de vue
        self.zoom_level: float = 1.0  # 1.0 = Fit to window
        self.fit_to_window: bool = True
        self.pan_offset: QPointF = QPointF(0, 0)
        self.rotation_degrees: int = 0  # 0, 90, 180, 270

        # État d'interaction souris (pan/drag)
        self._is_dragging: bool = False
        self._last_mouse_pos: QPoint = QPoint(0, 0)

        # Curseur Main (Hand tool: cursor_7.cur)
        self._pan_cursor = self.res_mgr.get_cursor(7)
        self.setCursor(self._pan_cursor)

    def load_image(self, path: str, rotation: int = 0) -> bool:
        """
        Charge une image haute résolution depuis le disque ou le conteneur.
        """
        self.image_path = path
        self.rotation_degrees = rotation % 360
        self.pan_offset = QPointF(0, 0)
        self.fit_to_window = True

        p = Path(path)
        if p.exists():
            pix = QPixmap(str(p))
            if not pix.isNull():
                self._raw_pixmap = pix
                self._update_display_pixmap()
                self.update()
                return True

        self._raw_pixmap = None
        self._display_pixmap = None
        self.update()
        return False

    def set_pixmap_direct(self, pixmap: QPixmap, rotation: int = 0) -> None:
        self.rotation_degrees = rotation % 360
        self._raw_pixmap = pixmap
        self.pan_offset = QPointF(0, 0)
        self.fit_to_window = True
        self._update_display_pixmap()
        self.update()

    def set_rotation(self, degrees: int) -> None:
        self.rotation_degrees = degrees % 360
        self._update_display_pixmap()
        self.update()

    def rotate_clockwise(self) -> None:
        self.set_rotation(self.rotation_degrees + 90)

    def rotate_counterclockwise(self) -> None:
        self.set_rotation(self.rotation_degrees - 90)

    def _update_display_pixmap(self) -> None:
        if self._raw_pixmap is None or self._raw_pixmap.isNull():
            self._display_pixmap = None
            return

        if self.rotation_degrees != 0:
            from PySide6.QtGui import QTransform
            transform = QTransform().rotate(self.rotation_degrees)
            self._display_pixmap = self._raw_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        else:
            self._display_pixmap = self._raw_pixmap

    def set_zoom(self, zoom: float) -> None:
        self.zoom_level = max(0.1, min(5.0, zoom))
        self.fit_to_window = False
        self.zoom_changed.emit(self.zoom_level)
        self.update()

    def reset_zoom_to_fit(self) -> None:
        self.fit_to_window = True
        self.pan_offset = QPointF(0, 0)
        self.zoom_level = 1.0
        self.zoom_changed.emit(self.zoom_level)
        self.update()

    def _get_fit_scale(self) -> float:
        if self._display_pixmap is None or self._display_pixmap.isNull():
            return 1.0
        img_w = self._display_pixmap.width()
        img_h = self._display_pixmap.height()
        view_w = max(10, self.width() - 20)
        view_h = max(10, self.height() - 20)
        scale_x = view_w / img_w
        scale_y = view_h / img_h
        return min(scale_x, scale_y)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fond neutre sombre (Picasa One-Up utilise un fond gris foncé/noir #1A1A1A)
        painter.fillRect(self.rect(), QColor(0x1A, 0x1A, 0x1A))

        if self._display_pixmap is None or self._display_pixmap.isNull():
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Impossible de charger l'image")
            return

        scale = self._get_fit_scale() if self.fit_to_window else self.zoom_level
        draw_w = self._display_pixmap.width() * scale
        draw_h = self._display_pixmap.height() * scale

        center_x = (self.width() - draw_w) / 2.0 + self.pan_offset.x()
        center_y = (self.height() - draw_h) / 2.0 + self.pan_offset.y()

        target_rect = QRectF(center_x, center_y, draw_w, draw_h)

        # Ombre portée de la photo
        shadow_rect = target_rect.translated(4, 4)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 90))

        # Dessin de l'image
        painter.drawPixmap(target_rect, self._display_pixmap, QRectF(self._display_pixmap.rect()))

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            new_zoom = (self._get_fit_scale() if self.fit_to_window else self.zoom_level) * 1.15
            self.set_zoom(new_zoom)
        elif delta < 0:
            new_zoom = (self._get_fit_scale() if self.fit_to_window else self.zoom_level) / 1.15
            self.set_zoom(new_zoom)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.pan_offset += QPointF(delta.x(), delta.y())
            self.fit_to_window = False
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.fit_to_window:
            self.set_zoom(1.0)
        else:
            self.reset_zoom_to_fit()
