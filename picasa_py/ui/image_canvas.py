"""
High-Resolution Interactive Image Canvas for PyCasa One-Up & Two-Up Views.
Supports smooth zooming, panning, rotation, and non-destructive preview.
Includes Picasa's signature Loupe Navigator with interactive orange viewfinder frame,
and Side-by-Side Dual Comparison Modes (A, A|B, A|A).

Ref: picasa3.exe @ OneUp, AVOneUpUI (0x0094355C)
Ref: picasa3.exe @ TwoUp, TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
Ref: picasa3.exe @ CLoupeNode (0x00942AE4), CLoupeMaker (0x00942AC8)
Ref: picasa3.exe @ PanHandler (0x0093F3A8)
Ref: picasa3.exe @ thumbui/loupe (0x0088F9C4)
Ref: AGENTS.md §4 bis (Fonctionnement identique: zoom, pan, molette, comparaison A B|A A|A)
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Optional, Tuple, List, Any
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPixmap, QImage, QImageReader, QMouseEvent, QWheelEvent,
    QPaintEvent, QResizeEvent, QCursor, QPen, QFont
)
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle


# Ref: picasa3.exe @ OneUp (0x0094355C), TwoUp (0x0088E588)
class PicasaImageCanvas(QWidget):
    """
    Zone d'affichage haute résolution d'une photo avec zoom continu ancré,
    panoramique (pan) fluide, balises de visages, navigateur Loupe de cadrage,
    et modes de comparaison côte-à-côte (A, A|B, A|A).
    """
    zoom_changed = Signal(float)
    navigate_prev = Signal()
    navigate_next = Signal()
    active_pane_changed = Signal(str)  # "A" ou "B"

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.image_path: Optional[str] = None
        self._raw_pixmap: Optional[QPixmap] = None
        self._display_pixmap: Optional[QPixmap] = None

        # Modes de comparaison côte-à-côte (Ref: picasa3.exe @ TwoUp, TwoUpAB, TwoUpAA)
        self.view_mode: str = "A"  # "A" (vue unique), "A_B" (2 photos), "A_A" (avant/après)
        self._original_pixmap: Optional[QPixmap] = None
        self._secondary_pixmap: Optional[QPixmap] = None
        self.main_title: str = "Photo A"
        self.secondary_title: str = "Photo B"
        self.active_pane: str = "A"  # "A" ou "B"

        # Paramètres de vue
        self.zoom_level: float = 1.0  # 1.0 = 100% échelle 1:1
        self.fit_to_window: bool = True
        self.pan_offset: QPointF = QPointF(0, 0)
        self.rotation_degrees: int = 0  # 0, 90, 180, 270

        # État d'interaction souris (pan/drag principal)
        self._is_dragging: bool = False
        self._last_mouse_pos: QPoint = QPoint(0, 0)

        # Loupe Overview Navigator (Ref: picasa3.exe @ CLoupeNode, 0x00942AE4)
        self._nav_card_rect: QRectF = QRectF()
        self._nav_img_rect: QRectF = QRectF()
        self._vbox_rect: QRectF = QRectF()
        self._nav_thumbnail: Optional[QPixmap] = None
        self._is_dragging_nav_box: bool = False
        self._last_nav_drag_pos: QPointF = QPointF(0, 0)
        self.show_loupe_navigator: bool = True

        # Balises de visages (Face Tags, Ref: 0x008AAD76)
        self.face_rects: List[Any] = []
        self.show_face_tags: bool = True
        self.hovered_face_idx: int = -1

        # Curseur Main (Hand tool: cursor_7.cur)
        self._pan_cursor = self.res_mgr.get_cursor(7)
        self.setCursor(self._pan_cursor)

    def load_image(self, path: str, rotation: int = 0) -> bool:
        """
        Charge une image haute résolution depuis le disque.
        Gère les images panoramiques, gigapixel, et formats spéciaux (PSD, TIFF, WEBP).
        """
        self.image_path = path
        self.rotation_degrees = rotation % 360
        self.pan_offset = QPointF(0, 0)
        self.fit_to_window = True

        p = Path(path)
        if p.exists():
            # 1. Tenter via QImageReader avec allocation illimitée
            reader = QImageReader(str(p))
            reader.setAutoTransform(True)
            reader.setAllocationLimit(0)
            qimg = reader.read()
            if not qimg.isNull():
                self._raw_pixmap = QPixmap.fromImage(qimg)
                self._update_display_pixmap()
                self.update()
                return True

            # 2. Fallback via PIL pour formats spéciaux ou très grandes résolutions
            try:
                from PIL import ImageOps
                with Image.open(str(p)) as raw_img:
                    if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                        raw_img = raw_img.convert("RGBA")
                    try:
                        pil_img = ImageOps.exif_transpose(raw_img)
                    except Exception:
                        pil_img = raw_img
                    if pil_img.mode not in ("RGB", "RGBA"):
                        pil_img = pil_img.convert("RGB")
                    pil_img.load()
                    if pil_img.mode == "RGBA":
                        data = pil_img.tobytes("raw", "BGRA")
                        qimg = QImage(data, pil_img.width, pil_img.height, pil_img.width * 4, QImage.Format.Format_ARGB32).copy()
                    else:
                        data = pil_img.tobytes("raw", "RGB")
                        qimg = QImage(data, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format.Format_RGB888).copy()
                    if not qimg.isNull():
                        self._raw_pixmap = QPixmap.fromImage(qimg)
                        self._update_display_pixmap()
                        self.update()
                        return True
            except Exception:
                pass

        self._raw_pixmap = None
        self._display_pixmap = None
        self._nav_thumbnail = None
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

    def set_view_mode(self, mode: str) -> None:
        """
        Définit le mode d'affichage :
        - "A" : Vue unique normale (One-Up)
        - "A_B" : Comparaison de deux photos différentes côte à côte (Two-Up A|B)
        - "A_A" : Comparaison avant/après de la même photo côte à côte (Two-Up A|A)
        Ref: picasa3.exe @ TwoUp, TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
        """
        if mode in ("A", "A_B", "A_A"):
            self.view_mode = mode
            self.update()

    def set_original_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        """Enregistre la photo originale non retouchée pour le mode A|A."""
        self._original_pixmap = pixmap
        if self.view_mode == "A_A":
            self.update()

    def set_secondary_pixmap(self, pixmap: Optional[QPixmap], title: str = "Photo B") -> None:
        """Définit la photo secondaire pour le mode de comparaison A|B."""
        self._secondary_pixmap = pixmap
        self.secondary_title = title
        if self.view_mode == "A_B":
            self.update()

    def _update_display_pixmap(self) -> None:
        if self._raw_pixmap is None or self._raw_pixmap.isNull():
            self._display_pixmap = None
            self._nav_thumbnail = None
            return

        if self.rotation_degrees != 0:
            from PySide6.QtGui import QTransform
            transform = QTransform().rotate(self.rotation_degrees)
            self._display_pixmap = self._raw_pixmap.transformed(
                transform, Qt.TransformationMode.SmoothTransformation
            )
        else:
            self._display_pixmap = self._raw_pixmap

        # Précalcul de la miniature de cadrage pour la Loupe (60 FPS garanti)
        if self._display_pixmap and not self._display_pixmap.isNull():
            self._nav_thumbnail = self._display_pixmap.scaled(
                180, 180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self._nav_thumbnail = None

    def get_current_scale(self) -> float:
        """Retourne le facteur d'échelle actuel de l'image."""
        if self.fit_to_window:
            return self._get_fit_scale()
        return self.zoom_level

    def is_zoomed_in(self) -> bool:
        """Vérifie si l'image dépasse les dimensions de la fenêtre."""
        if self._display_pixmap is None or self._display_pixmap.isNull():
            return False
        scale = self.get_current_scale()
        draw_w = self._display_pixmap.width() * scale
        draw_h = self._display_pixmap.height() * scale
        return (draw_w > self.width() + 10) or (draw_h > self.height() + 10)

    def set_zoom(self, zoom: float) -> None:
        self.zoom_level = max(0.1, min(6.0, zoom))
        self.fit_to_window = False
        self._clamp_pan_offset()
        self.zoom_changed.emit(self.zoom_level)
        self.update()

    def reset_zoom_to_fit(self) -> None:
        self.fit_to_window = True
        self.pan_offset = QPointF(0, 0)
        self.zoom_level = self._get_fit_scale()
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

    def _clamp_pan_offset(self) -> None:
        """
        Contraint le panoramique pour maintenir l'image visible et centrée.
        Ref: picasa3.exe @ PanHandler 0x0093F3A8
        """
        if self._display_pixmap is None or self._display_pixmap.isNull():
            self.pan_offset = QPointF(0, 0)
            return

        scale = self.get_current_scale()
        draw_w = self._display_pixmap.width() * scale
        draw_h = self._display_pixmap.height() * scale

        # Axe horizontal
        if draw_w <= self.width():
            new_x = 0.0
        else:
            max_delta_x = (draw_w - self.width()) / 2.0
            bound_x = max_delta_x + 40.0
            new_x = max(-bound_x, min(bound_x, self.pan_offset.x()))

        # Axe vertical
        if draw_h <= self.height():
            new_y = 0.0
        else:
            max_delta_y = (draw_h - self.height()) / 2.0
            bound_y = max_delta_y + 40.0
            new_y = max(-bound_y, min(bound_y, self.pan_offset.y()))

        self.pan_offset = QPointF(new_x, new_y)

    def set_zoom_anchored(self, new_zoom: float, anchor: QPointF) -> None:
        """
        Zoom ancré au niveau du curseur : le point de la photo sous la souris reste stable.
        Ref: picasa3.exe @ CLoupeMaker / OneUpUI 0x0094355C
        """
        if self._display_pixmap is None or self._display_pixmap.isNull():
            return

        old_scale = self.get_current_scale()
        clamped_zoom = max(0.1, min(6.0, new_zoom))
        fit_scale = self._get_fit_scale()

        if clamped_zoom <= fit_scale * 0.98:
            self.reset_zoom_to_fit()
            return

        draw_w_old = self._display_pixmap.width() * old_scale
        draw_h_old = self._display_pixmap.height() * old_scale
        cx_old = (self.width() - draw_w_old) / 2.0 + self.pan_offset.x()
        cy_old = (self.height() - draw_h_old) / 2.0 + self.pan_offset.y()

        u = (anchor.x() - cx_old) / draw_w_old if draw_w_old > 0 else 0.5
        v = (anchor.y() - cy_old) / draw_h_old if draw_h_old > 0 else 0.5
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))

        draw_w_new = self._display_pixmap.width() * clamped_zoom
        draw_h_new = self._display_pixmap.height() * clamped_zoom

        cx_new = anchor.x() - u * draw_w_new
        cy_new = anchor.y() - v * draw_h_new

        self.pan_offset = QPointF(
            cx_new - (self.width() - draw_w_new) / 2.0,
            cy_new - (self.height() - draw_h_new) / 2.0
        )
        self.zoom_level = clamped_zoom
        self.fit_to_window = False
        self._clamp_pan_offset()
        self.zoom_changed.emit(self.zoom_level)
        self.update()

    def _update_loupe_geometry(self) -> None:
        """
        Calcule la géométrie du navigateur Loupe et du cadre de visée orange.
        Ref: picasa3.exe @ CLoupeNode (0x00942AE4)
        """
        if not self.is_zoomed_in() or self._display_pixmap is None:
            self._nav_card_rect = QRectF()
            self._nav_img_rect = QRectF()
            self._vbox_rect = QRectF()
            return

        img_w = self._display_pixmap.width()
        img_h = self._display_pixmap.height()
        if img_w <= 0 or img_h <= 0:
            return

        aspect = img_w / img_h
        max_w, max_h = 160.0, 120.0
        if aspect >= (max_w / max_h):
            nw = max_w
            nh = max(24.0, max_w / aspect)
        else:
            nh = max_h
            nw = max(24.0, max_h * aspect)

        pad = 6.0
        card_w = nw + pad * 2.0
        card_h = nh + pad * 2.0
        margin_right = 18.0
        margin_bottom = 18.0

        card_x = self.width() - card_w - margin_right
        card_y = self.height() - card_h - margin_bottom

        self._nav_card_rect = QRectF(card_x, card_y, card_w, card_h)
        self._nav_img_rect = QRectF(card_x + pad, card_y + pad, nw, nh)

        scale = self.get_current_scale()
        draw_w = img_w * scale
        draw_h = img_h * scale

        cx = (self.width() - draw_w) / 2.0 + self.pan_offset.x()
        cy = (self.height() - draw_h) / 2.0 + self.pan_offset.y()

        u1 = max(0.0, min(1.0, -cx / draw_w))
        u2 = max(0.0, min(1.0, (self.width() - cx) / draw_w))
        v1 = max(0.0, min(1.0, -cy / draw_h))
        v2 = max(0.0, min(1.0, (self.height() - cy) / draw_h))

        if u2 < u1:
            u2 = u1
        if v2 < v1:
            v2 = v1

        vx = self._nav_img_rect.x() + u1 * self._nav_img_rect.width()
        vy = self._nav_img_rect.y() + v1 * self._nav_img_rect.height()
        vw = max(8.0, (u2 - u1) * self._nav_img_rect.width())
        vh = max(8.0, (v2 - v1) * self._nav_img_rect.height())

        self._vbox_rect = QRectF(vx, vy, vw, vh)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fond neutre sombre Picasa (#1A1A1A)
        painter.fillRect(self.rect(), QColor(0x1A, 0x1A, 0x1A))

        if self.view_mode in ("A_B", "A_A"):
            self._paint_two_up(painter)
        else:
            self._paint_one_up(painter)

    def _paint_one_up(self, painter: QPainter) -> None:
        """Rendu standard en vue unique (One-Up)."""
        if self._display_pixmap is None or self._display_pixmap.isNull():
            painter.setPen(QColor("#888888"))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Impossible de charger l'image")
            return

        scale = self.get_current_scale()
        draw_w = self._display_pixmap.width() * scale
        draw_h = self._display_pixmap.height() * scale

        center_x = (self.width() - draw_w) / 2.0 + self.pan_offset.x()
        center_y = (self.height() - draw_h) / 2.0 + self.pan_offset.y()

        target_rect = QRectF(center_x, center_y, draw_w, draw_h)

        # Ombre portée de la photo
        shadow_rect = target_rect.translated(4, 4)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 90))

        # Dessin de l'image haute définition
        painter.drawPixmap(target_rect, self._display_pixmap, QRectF(self._display_pixmap.rect()))

        # Dessin des balises de visages (Face Tags, Ref: 0x008AAD76)
        if self.show_face_tags and self.face_rects:
            self._draw_face_tags(painter, target_rect)

        # Dessin du navigateur Loupe d'ensemble (Ref: 0x00942AE4)
        self._update_loupe_geometry()
        self._draw_overview_navigator(painter)

    def _paint_two_up(self, painter: QPainter) -> None:
        """
        Rendu en mode comparaison côte à côte (Two-Up A|B ou A|A).
        Ref: picasa3.exe @ TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
        """
        w, h = float(self.width()), float(self.height())
        half_w = (w - 2.0) / 2.0
        left_rect = QRectF(0, 0, half_w, h)
        right_rect = QRectF(half_w + 2.0, 0, half_w, h)

        # Séparateur vertical central
        painter.fillRect(QRectF(half_w, 0, 2, h), QColor(20, 22, 26))

        if self.view_mode == "A_A":
            img_left = self._original_pixmap if self._original_pixmap else self._display_pixmap
            img_right = self._display_pixmap
            badge_left = "Originale (Avant)"
            badge_right = "Retouchée (Après)"
            act_left = False
            act_right = False
        else:  # "A_B"
            img_left = self._display_pixmap
            img_right = self._secondary_pixmap
            badge_left = f"Photo A : {self.main_title}"
            badge_right = f"Photo B : {self.secondary_title}"
            act_left = (self.active_pane == "A")
            act_right = (self.active_pane == "B")

        self._draw_pane_content(painter, left_rect, img_left, badge_left, act_left, False)
        self._draw_pane_content(painter, right_rect, img_right, badge_right, act_right, (self.view_mode == "A_A"))

    def _draw_pane_content(
        self, painter: QPainter, pane_rect: QRectF,
        pix: Optional[QPixmap], badge_text: str, is_active: bool, is_modified_style: bool
    ) -> None:
        """Dessine une photo et son étiquette dans un volet de comparaison."""
        if pix is None or pix.isNull():
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(pane_rect, Qt.AlignmentFlag.AlignCenter, "Aucune photo sélectionnée")
        else:
            # Calcul du ratio adapté au demi-panneau
            scale_x = (pane_rect.width() - 20.0) / pix.width()
            scale_y = (pane_rect.height() - 20.0) / pix.height()
            fit_scale = min(scale_x, scale_y)
            scale = fit_scale if self.fit_to_window else (self.zoom_level * fit_scale)

            dw = pix.width() * scale
            dh = pix.height() * scale
            cx = pane_rect.x() + (pane_rect.width() - dw) / 2.0 + self.pan_offset.x()
            cy = pane_rect.y() + (pane_rect.height() - dh) / 2.0 + self.pan_offset.y()
            t_rect = QRectF(cx, cy, dw, dh)

            painter.save()
            painter.setClipRect(pane_rect)

            # Ombre portée
            painter.fillRect(t_rect.translated(3, 3), QColor(0, 0, 0, 90))
            # Image haute résolution
            painter.drawPixmap(t_rect, pix, QRectF(pix.rect()))
            painter.restore()

        # Badge pill en haut à gauche du volet
        painter.save()
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(badge_text)
        b_rect = QRectF(pane_rect.x() + 14, pane_rect.y() + 14, tw + 20, 24)

        if is_active:
            painter.setBrush(QColor(37, 100, 139, 235))
            painter.setPen(QPen(QColor(51, 153, 255, 230), 1.5))
        elif is_modified_style:
            painter.setBrush(QColor(230, 115, 0, 230))
            painter.setPen(QPen(QColor(255, 160, 40, 230), 1.2))
        else:
            painter.setBrush(QColor(24, 26, 30, 210))
            painter.setPen(QPen(QColor(65, 70, 80, 190), 1.0))

        painter.drawRoundedRect(b_rect, 4.0, 4.0)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(b_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
        painter.restore()

    def _draw_overview_navigator(self, painter: QPainter) -> None:
        """
        Dessine la miniature flottante de vue d'ensemble avec le cadre de visée orange.
        Ref: picasa3.exe @ CLoupeNode 0x00942AE4
        """
        if not self.is_zoomed_in() or not self.show_loupe_navigator:
            return
        if self._nav_card_rect.isEmpty() or self._nav_img_rect.isEmpty():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Ombre portée de la carte Loupe
        shadow_rect = self._nav_card_rect.translated(2, 3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 110))
        painter.drawRoundedRect(shadow_rect, 6.0, 6.0)

        # 2. Carte d'arrière-plan semi-transparente sombre
        painter.setBrush(QColor(22, 24, 28, 230))
        painter.setPen(QPen(QColor(70, 75, 85, 220), 1.0))
        painter.drawRoundedRect(self._nav_card_rect, 6.0, 6.0)

        # 3. Miniature de l'image
        if self._nav_thumbnail and not self._nav_thumbnail.isNull():
            painter.drawPixmap(self._nav_img_rect, self._nav_thumbnail, QRectF(self._nav_thumbnail.rect()))
        elif self._display_pixmap:
            painter.drawPixmap(self._nav_img_rect, self._display_pixmap, QRectF(self._display_pixmap.rect()))

        # 4. Voile sombre atténuant les zones hors du cadrage actuel
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 70))
        painter.drawRect(self._nav_img_rect)

        # 5. Cadre de visée (Viewfinder Frame - Orange Picasa #FF9900)
        painter.setBrush(QColor(255, 145, 0, 50))
        painter.setPen(QPen(QColor(255, 155, 0, 240), 1.8))
        painter.drawRect(self._vbox_rect)

        # Coins renforcés (corner accents) caractéristiques de Picasa Loupe
        c_len = min(6.0, min(self._vbox_rect.width(), self._vbox_rect.height()) / 2.0)
        c_pen = QPen(QColor(255, 220, 130, 255), 2.2)
        painter.setPen(c_pen)
        x1, y1 = self._vbox_rect.left(), self._vbox_rect.top()
        x2, y2 = self._vbox_rect.right(), self._vbox_rect.bottom()

        # Coin Haut-Gauche
        painter.drawLine(QPointF(x1, y1), QPointF(x1 + c_len, y1))
        painter.drawLine(QPointF(x1, y1), QPointF(x1, y1 + c_len))
        # Coin Haut-Droit
        painter.drawLine(QPointF(x2, y1), QPointF(x2 - c_len, y1))
        painter.drawLine(QPointF(x2, y1), QPointF(x2, y1 + c_len))
        # Coin Bas-Gauche
        painter.drawLine(QPointF(x1, y2), QPointF(x1 + c_len, y2))
        painter.drawLine(QPointF(x1, y2), QPointF(x1, y2 - c_len))
        # Coin Bas-Droit
        painter.drawLine(QPointF(x2, y2), QPointF(x2 - c_len, y2))
        painter.drawLine(QPointF(x2, y2), QPointF(x2, y2 - c_len))

        painter.restore()

    def set_face_rects(self, rects: List[Any]) -> None:
        self.face_rects = rects
        self.hovered_face_idx = -1
        self.update()

    def set_show_face_tags(self, show: bool) -> None:
        self.show_face_tags = show
        self.update()

    def _draw_face_tags(self, painter: QPainter, target_rect: QRectF) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i, fr in enumerate(self.face_rects):
            fx = target_rect.x() + fr.left * target_rect.width()
            fy = target_rect.y() + fr.top * target_rect.height()
            fw = fr.width * target_rect.width()
            fh = fr.height * target_rect.height()

            rect_box = QRectF(fx, fy, fw, fh)
            is_hovered = (i == self.hovered_face_idx)

            pen_color = QColor(0, 200, 255, 230) if is_hovered else QColor(255, 255, 255, 200)
            pen = QPen(pen_color, 2.0 if is_hovered else 1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect_box, 3, 3)

            name_text = fr.contact_name or "Personne"
            painter.setFont(QFont("Tahoma", 9, QFont.Weight.Bold))
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(name_text)
            badge_w = tw + 16
            badge_h = 22
            badge_x = fx + (fw - badge_w) / 2.0
            badge_y = fy + fh + 4

            badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(20, 24, 30, 210))
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, name_text)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 1.18 if delta > 0 else (1.0 / 1.18)
        current_s = self.get_current_scale()
        new_zoom = current_s * factor
        self.set_zoom_anchored(new_zoom, event.position())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()

            # 1. Sélection de volet en mode comparaison A|B
            if self.view_mode == "A_B":
                half_w = (self.width() - 2.0) / 2.0
                new_pane = "A" if pos.x() < half_w else "B"
                if self.active_pane != new_pane:
                    self.active_pane = new_pane
                    self.active_pane_changed.emit(new_pane)
                    self.update()

            # 2. Interaction avec la Loupe si active
            if self.is_zoomed_in() and self.show_loupe_navigator and self._nav_card_rect.contains(pos):
                if self._nav_img_rect.contains(pos):
                    if self._vbox_rect.contains(pos):
                        self._is_dragging_nav_box = True
                        self._last_nav_drag_pos = pos
                    else:
                        self._center_on_nav_point(pos)
                        self._is_dragging_nav_box = True
                        self._last_nav_drag_pos = pos
                return

            # 3. Panoramique sur le canvas
            self._is_dragging = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _center_on_nav_point(self, click_pos: QPointF) -> None:
        """Recentrer la vue principale sur le point cliqué dans la Loupe."""
        if self._nav_img_rect.isEmpty() or self._display_pixmap is None:
            return
        u = (click_pos.x() - self._nav_img_rect.x()) / self._nav_img_rect.width()
        v = (click_pos.y() - self._nav_img_rect.y()) / self._nav_img_rect.height()
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))

        scale = self.get_current_scale()
        draw_w = self._display_pixmap.width() * scale
        draw_h = self._display_pixmap.height() * scale

        self.pan_offset = QPointF(draw_w * (0.5 - u), draw_h * (0.5 - v))
        self._clamp_pan_offset()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()

        # 1. Déplacement du cadre de cadrage dans la Loupe
        if self._is_dragging_nav_box:
            delta = pos - self._last_nav_drag_pos
            self._last_nav_drag_pos = pos

            if not self._nav_img_rect.isEmpty() and self._display_pixmap:
                scale = self.get_current_scale()
                draw_w = self._display_pixmap.width() * scale
                draw_h = self._display_pixmap.height() * scale

                ratio_x = draw_w / self._nav_img_rect.width()
                ratio_y = draw_h / self._nav_img_rect.height()

                self.pan_offset = QPointF(
                    self.pan_offset.x() - delta.x() * ratio_x,
                    self.pan_offset.y() - delta.y() * ratio_y
                )
                self._clamp_pan_offset()
                self.update()
            return

        # 2. Déplacement panoramique (Pan) de la photo
        if self._is_dragging:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.pan_offset += QPointF(delta.x(), delta.y())
            self.fit_to_window = False
            self._clamp_pan_offset()
            self.update()
            return

        # 3. Adaptation du curseur de survol
        if self.is_zoomed_in() and self.show_loupe_navigator and self._nav_card_rect.contains(pos):
            if self._vbox_rect.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(self._pan_cursor)

        # 4. Survol des balises de visages
        if self.show_face_tags and self.face_rects and self._display_pixmap:
            scale = self.get_current_scale()
            draw_w = self._display_pixmap.width() * scale
            draw_h = self._display_pixmap.height() * scale
            cx = (self.width() - draw_w) / 2.0 + self.pan_offset.x()
            cy = (self.height() - draw_h) / 2.0 + self.pan_offset.y()
            t_rect = QRectF(cx, cy, draw_w, draw_h)

            prev_hovered = self.hovered_face_idx
            self.hovered_face_idx = -1
            for i, fr in enumerate(self.face_rects):
                fx = t_rect.x() + fr.left * t_rect.width()
                fy = t_rect.y() + fr.top * t_rect.height()
                fw = fr.width * t_rect.width()
                fh = fr.height * t_rect.height()
                if QRectF(fx, fy, fw, fh).contains(pos):
                    self.hovered_face_idx = i
                    break
            if prev_hovered != self.hovered_face_idx:
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._is_dragging_nav_box = False
            self.setCursor(self._pan_cursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if self.fit_to_window:
                fit_scale = self._get_fit_scale()
                target_zoom = 1.0 if fit_scale < 0.8 else max(1.5, fit_scale * 2.0)
                self.set_zoom_anchored(target_zoom, pos)
            else:
                self.reset_zoom_to_fit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._clamp_pan_offset()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)
