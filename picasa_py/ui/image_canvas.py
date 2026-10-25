"""
FR: Canevas d'image interactif haute résolution pour les vues One-Up et Two-Up de PyCasa.
Supporte le zoom fluide, le déplacement panoramique, la rotation, le navigateur Loupe
et les modes de comparaison côte à côte (A, A|B, A|A).

EN: High-Resolution Interactive Image Canvas for PyCasa One-Up & Two-Up Views.
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
    QPaintEvent, QResizeEvent, QCursor, QPen, QFont, QBrush, QContextMenuEvent
)
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle
from picasa_py.faces.facerect import FaceRect, encode_rect64_string, decode_rect64_string


# Ref: picasa3.exe @ OneUp (0x0094355C), TwoUp (0x0088E588)
class PicasaImageCanvas(QWidget):
    """
    FR: Zone d'affichage haute résolution d'une photo avec zoom continu ancré,
    panoramique (pan) fluide, balises de visages, navigateur Loupe de cadrage,
    et modes de comparaison côte-à-côte (A, A|B, A|A).
    EN: High-resolution photo display canvas with anchored continuous zoom,
    smooth panning, face tags, framing Loupe navigator, and side-by-side comparison modes (A, A|B, A|A).
    """
    zoom_changed = Signal(float)
    navigate_prev = Signal()
    navigate_next = Signal()
    active_pane_changed = Signal(str)  # "A" ou "B"
    face_clicked = Signal(object, int)  # (FaceRect, index)
    manual_face_defined = Signal(object)  # FaceRect
    context_menu_requested = Signal(object)  # QPoint (global pos)

    # FR: Signaux des outils interactifs d'édition / EN: Interactive editing tool signals (Ref: CSmartCrop, filter_tilt, retouch, redeye)
    straighten_interactive_angle_changed = Signal(float)
    retouch_applied = Signal(float, float, float)  # (norm_x, norm_y, radius)
    redeye_applied = Signal(float, float)  # (norm_x, norm_y)
    redeye_box_applied = Signal(object)  # QRectF
    neutral_color_picked = Signal(object)  # Tuple[int, int, int] (r, g, b)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise le canevas d'image, ses curseurs PE authentiques et ses états d'outils interactifs.
        EN: Initializes the image canvas, its authentic PE cursors, and its interactive tool states.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.image_path: Optional[str] = None
        self._raw_pixmap: Optional[QPixmap] = None
        self._display_pixmap: Optional[QPixmap] = None

        # FR: Modes de comparaison côte-à-côte / EN: Side-by-side comparison modes (Ref: picasa3.exe @ TwoUp, TwoUpAB, TwoUpAA)
        self.view_mode: str = "A"  # "A" (vue unique), "A_B" (2 photos), "A_A" (avant/après)
        self._original_pixmap: Optional[QPixmap] = None
        self._secondary_pixmap: Optional[QPixmap] = None
        self.main_title: str = "Photo A"
        self.secondary_title: str = "Photo B"
        self.active_pane: str = "A"  # "A" ou "B"
        # FR: Orientation de la division 2-Up ("horizontal" = gauche/droite, "vertical" = haut/bas)
        # EN: 2-Up split orientation ("horizontal" = left/right, "vertical" = top/bottom)
        # Ref: picasa3.exe @ 0x00569720 (FUN_00569720, editpanel/swap_2up_layout)
        self.split_orientation: str = "horizontal"

        # FR: Paramètres de vue / EN: View parameters
        self.zoom_level: float = 1.0  # 1.0 = 100% échelle 1:1
        self.fit_to_window: bool = True
        self.pan_offset: QPointF = QPointF(0, 0)
        self.rotation_degrees: int = 0  # 0, 90, 180, 270

        # FR: État d'interaction souris (pan/drag principal) / EN: Mouse interaction state (main pan/drag)
        self._is_dragging: bool = False
        self._last_mouse_pos: QPoint = QPoint(0, 0)

        # FR: Navigateur Loupe d'ensemble et bouton fermer [×] / EN: Loupe Overview Navigator and close [×] button
        # Ref: picasa3.exe @ editpanel/nav (0x005D165D), nav/overview (0x0056953D), nav/zoom (0x005736F4 -> 0x00A615C0),
        #      nav/nav (0x0056B338), PanHandler (0x005C46B0 / 0x005C47F0 -> 0x00597D10)
        self._nav_card_rect: QRectF = QRectF()
        self._nav_img_rect: QRectF = QRectF()
        self._vbox_rect: QRectF = QRectF()
        self._nav_close_rect: QRectF = QRectF()
        self._is_hovering_nav_close: bool = False
        self._nav_thumbnail: Optional[QPixmap] = None
        self._is_dragging_nav_box: bool = False
        self._last_nav_drag_pos: QPointF = QPointF(0, 0)
        self.show_loupe_navigator: bool = True

        # FR: Paramètres de transformation d'affichage active (crop, tilt, rotate) / EN: Active display transform parameters (crop, tilt, rotate)
        self._active_crop_rect: Optional[Tuple[float, float, float, float]] = None
        self._active_tilt_angle: float = 0.0
        self._active_rotation_steps: int = 0

        # FR: Balises de visages / EN: Face Tags (Ref: 0x008AAD76)
        self.face_rects: List[Any] = []
        self.show_face_tags: bool = True
        self.hovered_face_idx: int = -1

        # FR: Ajout manuel de visages / EN: Manual face addition (Ref: peoplepanel/manual_add, 0x008A0D0C)
        self.is_manual_face_add: bool = False
        self._manual_face_start: Optional[QPointF] = None
        self._manual_face_current: Optional[QPointF] = None

        # FR: Curseurs authentiques Picasa 3 / EN: Authentic Picasa 3 cursors (Ref: PE resources cursors 1..12)
        self._pan_cursor = self.res_mgr.get_cursor(7)
        self._pan_closed_cursor = self.res_mgr.get_cursor(3)
        self._crop_cursor = self.res_mgr.get_cursor(1)
        self._dropper_cursor = self.res_mgr.get_cursor(2)
        self._face_cursor = self.res_mgr.get_cursor(5)
        self._redeye_cursor = self.res_mgr.get_cursor(8)
        self._retouch_cursor = self.res_mgr.get_cursor(9)
        self._tilt_cursor = self.res_mgr.get_cursor(12)
        self.setCursor(self._pan_cursor)

        # FR: Outil de recadrage interactif / EN: Interactive crop tool (Ref: picasa3.exe @ CSmartCrop, 0x008A786C)
        self.is_cropping: bool = False
        self.crop_target_ratio: Optional[float] = None
        self.crop_rect_norm: QRectF = QRectF(0.1, 0.1, 0.8, 0.8)
        self._crop_drag_handle: Optional[str] = None
        self._crop_drag_start_pos: QPointF = QPointF(0, 0)
        self._crop_drag_start_rect: QRectF = QRectF()
        self._image_target_rect: QRectF = QRectF()

        # FR: Outil Redresser / EN: Straighten tool (Ref: filter_tilt, picasa3.exe @ 0x008814AC)
        self.is_straightening: bool = False
        self.straighten_angle: float = 0.0
        self._straighten_drag_start: Optional[QPointF] = None
        self._straighten_drag_start_angle: float = 0.0

        # FR: Outil Retouche / EN: Retouch tool (Healing Puck, Ref: filterdesc.xml @ retouch, 0x0088C3EC)
        self.is_retouching: bool = False
        self.retouch_radius: float = 0.04
        self._retouch_hover_pos: Optional[QPointF] = None

        # FR: Outil Yeux Rouges / EN: Red-Eye tool (Ref: filterdesc.xml @ redeye, 0x005E7CD7)
        self.is_redeye: bool = False
        self._redeye_start: Optional[QPointF] = None
        self._redeye_current: Optional[QPointF] = None

        # FR: Outil Texte / EN: Text tool (Ref: TextTool, picasa3.exe @ 0x00658900)
        self.is_text_tool_active: bool = False
        self.text_content: str = ""
        self.text_font_size: int = 28
        self.text_shadow: bool = True
        self.text_color: QColor = QColor(255, 255, 255)
        self.text_pos_norm: QPointF = QPointF(0.15, 0.85)
        self._is_dragging_text: bool = False
        self._text_screen_rect: QRectF = QRectF()
        self._text_drag_start_pos: QPointF = QPointF(0, 0)

        # FR: Mode Pipette couleur neutre / EN: Neutral color picker mode (Ref: CDesaturateFilter::pickcolor, filter_whitept)
        self.is_pipette_mode: bool = False

    def set_pipette_mode(self, active: bool) -> None:
        """
        FR: Active ou désactive le mode Pipette de couleur neutre (filter_whitept).
        EN: Enables or disables the neutral color picker mode (filter_whitept).
        """
        self.is_pipette_mode = active
        if active:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(self._pan_cursor)

    def load_image(self, path: str, rotation: int = 0) -> bool:
        """
        FR: Charge une image haute résolution depuis le disque (gère panoramiques, gigapixel, PSD, TIFF, WEBP).
        EN: Loads a high-resolution image from disk (handles panoramic, gigapixel, PSD, TIFF, WEBP).
        """
        self.image_path = path
        self.rotation_degrees = rotation % 360
        self.pan_offset = QPointF(0, 0)
        self.fit_to_window = True

        p = Path(path)
        if p.exists():
            # 1. FR: Tenter via QImageReader avec allocation illimitée / EN: Try via QImageReader with unlimited allocation
            reader = QImageReader(str(p))
            reader.setAutoTransform(True)
            reader.setAllocationLimit(0)
            qimg = reader.read()
            if not qimg.isNull():
                self._raw_pixmap = QPixmap.fromImage(qimg)
                self._update_display_pixmap()
                self.update()
                return True

            # 2. FR: Fallback via PIL pour formats spéciaux ou très grandes résolutions / EN: PIL fallback for special formats or huge resolutions
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

    def set_pixmap_direct(self, pixmap: QPixmap, rotation: int = 0, preserve_view: bool = False) -> None:
        """
        FR: Définit directement le `QPixmap` affiché avec un angle de rotation optionnel,
        en préservant optionnellement le zoom et le déplacement panoramique (`preserve_view=True`).
        EN: Directly sets the displayed `QPixmap` with an optional rotation angle,
        optionally preserving the current zoom and pan offset (`preserve_view=True`).
        Ref: picasa3.exe @ 0x00760F40, OneUpUI (0x0094355C)
        """
        if isinstance(rotation, bool):
            preserve_view = rotation
            rotation = self.rotation_degrees
        self.rotation_degrees = rotation % 360
        prev_pix = (
            self._raw_pixmap
            if (self._raw_pixmap is not None and not self._raw_pixmap.isNull())
            else self._original_pixmap
        )
        self._raw_pixmap = pixmap
        if preserve_view and prev_pix is not None and not prev_pix.isNull():
            if (
                not self.fit_to_window
                and pixmap is not None
                and not pixmap.isNull()
                and pixmap.width() > 0
                and prev_pix.width() != pixmap.width()
            ):
                self.zoom_level *= (prev_pix.width() / float(pixmap.width()))
        else:
            self.pan_offset = QPointF(0, 0)
            self.fit_to_window = True
        self._update_display_pixmap()
        if self.fit_to_window:
            self.zoom_level = self._get_fit_scale()
        self.zoom_changed.emit(self.get_current_scale())
        self.update()

    def set_display_image(self, pil_img: Image.Image) -> None:
        """
        FR: Convertit une image PIL en `QPixmap` et l'affiche directement sur le canevas.
        EN: Converts a PIL image into a `QPixmap` and displays it directly on the canvas.
        """
        if pil_img.mode in ("P", "PA") or "transparency" in pil_img.info:
            pil_img = pil_img.convert("RGBA")
        if pil_img.mode == "RGBA":
            bgra_data = pil_img.tobytes("raw", "BGRA")
            qimg = QImage(bgra_data, pil_img.width, pil_img.height, pil_img.width * 4, QImage.Format.Format_ARGB32).copy()
        else:
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            rgb_data = pil_img.tobytes("raw", "RGB")
            qimg = QImage(rgb_data, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format.Format_RGB888).copy()
        self.set_pixmap_direct(QPixmap.fromImage(qimg), self.rotation_degrees)

    def toggle_two_up(self) -> bool:
        """
        FR: Bascule entre la vue simple (A) et la vue côte à côte Avant/Après (A_A).
        EN: Toggles between single view (A) and side-by-side Before/After view (A_A).
        """
        new_mode = "A" if self.view_mode != "A" else "A_A"
        self.set_view_mode(new_mode)
        return self.view_mode != "A"

    def set_rotation(self, degrees: int) -> None:
        """
        FR: Définit l'angle de rotation en degrés (modulo 360) et rafraîchit l'image affichée.
        EN: Sets the rotation angle in degrees (modulo 360) and refreshes the displayed image.
        """
        self.rotation_degrees = degrees % 360
        self._update_display_pixmap()
        self.update()

    def rotate_clockwise(self) -> None:
        """
        FR: Fait pivoter l'image de 90° dans le sens horaire.
        EN: Rotates the image 90° clockwise.
        """
        self.set_rotation(self.rotation_degrees + 90)

    def rotate_counterclockwise(self) -> None:
        """
        FR: Fait pivoter l'image de 90° dans le sens anti-horaire.
        EN: Rotates the image 90° counterclockwise.
        """
        self.set_rotation(self.rotation_degrees - 90)

    def set_view_mode(self, mode: str) -> None:
        """
        FR: Définit le mode d'affichage ("A" One-Up, "A_B" Two-Up A|B, "A_A" Two-Up A|A).
        EN: Sets the display view mode ("A" One-Up, "A_B" Two-Up A|B, "A_A" Two-Up A|A).
        Ref: picasa3.exe @ TwoUp, TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
        """
        if mode in ("A", "A_B", "A_A"):
            prev_fit_scale = self._get_fit_scale()
            self.view_mode = mode
            new_fit_scale = self._get_fit_scale()
            if self.fit_to_window:
                self.zoom_level = new_fit_scale
                self.pan_offset = QPointF(0, 0)
            elif prev_fit_scale > 0 and new_fit_scale > 0:
                self.zoom_level = max(0.1, min(6.0, self.zoom_level * (new_fit_scale / prev_fit_scale)))
                self._clamp_pan_offset()
            self.zoom_changed.emit(self.get_current_scale())
            self.update()

    def set_split_orientation(self, orientation: str) -> None:
        """
        FR: Définit l'orientation de division en mode 2-Up ("horizontal" côte à côte ou "vertical" haut/bas).
        EN: Sets the split orientation in 2-Up mode ("horizontal" side-by-side or "vertical" top/bottom).
        Ref: picasa3.exe @ 0x00569720 (FUN_00569720, editpanel/swap_2up_layout)
        """
        if orientation in ("horizontal", "vertical"):
            prev_fit_scale = self._get_fit_scale()
            self.split_orientation = orientation
            new_fit_scale = self._get_fit_scale()
            if self.fit_to_window:
                self.zoom_level = new_fit_scale
                self.pan_offset = QPointF(0, 0)
            elif prev_fit_scale > 0 and new_fit_scale > 0:
                self.zoom_level = max(0.1, min(6.0, self.zoom_level * (new_fit_scale / prev_fit_scale)))
                self._clamp_pan_offset()
            self.zoom_changed.emit(self.get_current_scale())
            self.update()

    def toggle_split_orientation(self) -> str:
        """
        FR: Bascule l'orientation de division en mode 2-Up entre horizontal (côte à côte) et vertical (haut/bas).
        EN: Toggles the 2-Up split orientation between horizontal (side-by-side) and vertical (top/bottom).
        Ref: picasa3.exe @ 0x00569650, 0x00569720 (editpanel/swap_2up_layout)
        """
        new_orient = "vertical" if self.split_orientation == "horizontal" else "horizontal"
        self.set_split_orientation(new_orient)
        return self.split_orientation

    def swap_active_pane(self) -> str:
        """
        FR: Bascule la mise au point (sélection active) entre le volet A et le volet B en mode 2-Up.
        EN: Toggles active focus between Pane A and Pane B in 2-Up mode.
        Ref: picasa3.exe @ 0x0056A160, 0x00569AF0 (editpanel/swap_2up_focus, editpanel/selection_label)
        """
        self.active_pane = "B" if self.active_pane == "A" else "A"
        self.active_pane_changed.emit(self.active_pane)
        self.update()
        return self.active_pane

    def set_original_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        """
        FR: Enregistre la photo originale non retouchée pour le mode de comparaison A|A.
        EN: Stores the unedited original photo for the A|A comparison mode.
        """
        self._original_pixmap = pixmap
        if self.view_mode == "A_A":
            if self.fit_to_window:
                self.zoom_level = self._get_fit_scale()
            self.zoom_changed.emit(self.get_current_scale())
            self.update()

    def set_secondary_pixmap(self, pixmap: Optional[QPixmap], title: str = "Photo B") -> None:
        """
        FR: Définit la photo secondaire et son titre pour le mode de comparaison A|B.
        EN: Sets the secondary photo and its title for the A|B comparison mode.
        """
        self._secondary_pixmap = pixmap
        self.secondary_title = title
        if self.view_mode == "A_B":
            if self.fit_to_window:
                self.zoom_level = self._get_fit_scale()
            self.zoom_changed.emit(self.get_current_scale())
            self.update()

    def _update_display_pixmap(self) -> None:
        """
        FR: Applique la rotation éventuelle au pixmap brut et précalcule la miniature de la Loupe.
        EN: Applies any active rotation to the raw pixmap and precomputes the Loupe thumbnail.
        """
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

        # FR: Précalcul de la miniature de cadrage pour la Loupe uniquement si zoomé (> 1.01) / EN: Precompute Loupe framing thumbnail only when zoomed (> 1.01)
        if (
            self._display_pixmap
            and not self._display_pixmap.isNull()
            and not self.fit_to_window
            and self.zoom_level > 1.01
        ):
            self._nav_thumbnail = self._display_pixmap.scaled(
                180, 180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self._nav_thumbnail = None

    def _get_active_pane_rect(self, for_pos: Optional[QPointF] = None) -> QRectF:
        """
        FR: Retourne le rectangle du volet actif (plein canevas en mode "A", demi-volet en mode "A_B" / "A_A").
        EN: Returns the active pane rectangle (full canvas in "A" mode, half-pane in "A_B" / "A_A" mode).
        Ref: picasa3.exe @ 0x005D157D ([ebp + 0x327c] / [ebp + 0x3280])
        """
        w, h = float(max(1, self.width())), float(max(1, self.height()))
        if self.view_mode not in ("A_B", "A_A"):
            return QRectF(0.0, 0.0, w, h)
        if self.split_orientation == "vertical":
            half_h = max(10.0, (h - 2.0) / 2.0)
            first_rect = QRectF(0.0, 0.0, w, half_h)
            second_rect = QRectF(0.0, half_h + 2.0, w, half_h)
        else:
            half_w = max(10.0, (w - 2.0) / 2.0)
            first_rect = QRectF(0.0, 0.0, half_w, h)
            second_rect = QRectF(half_w + 2.0, 0.0, half_w, h)
        if for_pos is not None:
            return second_rect if second_rect.contains(for_pos) else first_rect
        return first_rect if self.active_pane == "A" else second_rect

    def _get_active_pane_pixmap(self) -> Optional[QPixmap]:
        """
        FR: Retourne le `QPixmap` affiché dans le volet actif (A ou B selon `view_mode` et `active_pane`).
        EN: Returns the `QPixmap` displayed in the active pane (A or B depending on `view_mode` and `active_pane`).
        Ref: picasa3.exe @ 0x005D157D
        """
        if self.view_mode == "A_B" and self.active_pane == "B":
            if self._secondary_pixmap is not None and not self._secondary_pixmap.isNull():
                return self._secondary_pixmap
        elif self.view_mode == "A_A" and self.active_pane == "A":
            if self._original_pixmap is not None and not self._original_pixmap.isNull():
                return self._original_pixmap
        return self._display_pixmap

    def get_current_scale(self) -> float:
        """
        FR: Retourne le facteur d'échelle actuel de l'image.
        EN: Returns the current image scale factor.
        """
        if self.fit_to_window:
            return self._get_fit_scale()
        return self.zoom_level

    def is_zoomed_in(self) -> bool:
        """
        FR: Vérifie si l'image est zoomée au-delà de l'ajustement au volet d'affichage (1-Up ou 2-Up A|B / A|A).
        EN: Checks whether the image is zoomed beyond the viewport pane fit (1-Up or 2-Up A|B / A|A).
        Ref: picasa3.exe @ 0x005D1520..0x005D16B6 (editpanel/nav)
        """
        pix = self._get_active_pane_pixmap()
        if pix is None or pix.isNull():
            return False
        if self.fit_to_window:
            return False
        pane_rect = self._get_active_pane_rect()
        scale = self.get_current_scale()
        fit_scale = self._get_fit_scale()
        draw_w = pix.width() * scale
        draw_h = pix.height() * scale
        if (draw_w > pane_rect.width() + 10) or (draw_h > pane_rect.height() + 10):
            return True
        return scale > fit_scale * 1.01

    def set_zoom(self, zoom: float) -> None:
        """
        FR: Définit le niveau de zoom (entre 0.1 et 6.0) centré sur la vue courante et contraint le décalage panoramique.
        EN: Sets the zoom level (clamped between 0.1 and 6.0) centered on the current view and constrains the pan offset.
        Ref: picasa3.exe @ 0x005D1520 (CEditPanel::SetZoom)
        """
        old_scale = self.get_current_scale()
        new_zoom = max(0.1, min(6.0, float(zoom)))
        if old_scale > 0 and not self.fit_to_window:
            self.pan_offset = QPointF(
                self.pan_offset.x() * (new_zoom / old_scale),
                self.pan_offset.y() * (new_zoom / old_scale),
            )
        self.zoom_level = new_zoom
        self.fit_to_window = False
        self._clamp_pan_offset()
        self.zoom_changed.emit(self.zoom_level)
        self.update()

    def set_zoom_from_slider(self, slider_pct: int) -> None:
        """
        FR: Applique le niveau de zoom issu du curseur `zoomslider/scaleslider` (`slider_pct` en %).
        Lorsque le curseur est ramené tout à gauche (au niveau Ajuster `fit_scale`), réactive le mode Ajuster.
        EN: Applies the zoom level from the `zoomslider/scaleslider` slider (`slider_pct` in %).
        When dragged back to the leftmost Fit position (`fit_scale`), re-enables Fit-to-window mode.
        Ref: picasa3.exe @ 0x0057C322, 0x005D1520, 0x00597D10
        """
        target_zoom = float(slider_pct) / 100.0
        fit_scale = self._get_fit_scale()
        if target_zoom <= fit_scale * 1.01:
            self.reset_zoom_to_fit()
            return
        self.set_zoom(target_zoom)

    def reset_zoom_to_fit(self) -> None:
        """
        FR: Réinitialise le zoom pour ajuster l'image entière à la fenêtre et referme la miniature d'aperçu.
        EN: Resets the zoom level to fit the entire image within the viewport and closes the overview miniature.
        Ref: picasa3.exe @ FUN_00597d10 (0x00597D10), FUN_005ee590 (0x005EE590), FUN_005d1520 (0x005D1520)
        """
        self.fit_to_window = True
        self.pan_offset = QPointF(0, 0)
        self._is_dragging_nav_box = False
        self._is_hovering_nav_close = False
        self._nav_card_rect = QRectF()
        self._nav_img_rect = QRectF()
        self._vbox_rect = QRectF()
        self._nav_close_rect = QRectF()
        self.zoom_level = self._get_fit_scale()
        self.zoom_changed.emit(self.zoom_level)
        self.update()

    def _get_fit_scale(self) -> float:
        """
        FR: Calcule le facteur d'échelle permettant de faire tenir l'image dans le volet actif (1-Up ou 2-Up).
        EN: Computes the scale factor required to fit the image inside the active viewport pane (1-Up or 2-Up).
        """
        pix = self._get_active_pane_pixmap()
        if pix is None or pix.isNull():
            return 1.0
        pane_rect = self._get_active_pane_rect()
        img_w = max(1, pix.width())
        img_h = max(1, pix.height())
        view_w = max(10.0, pane_rect.width() - 20.0)
        view_h = max(10.0, pane_rect.height() - 20.0)
        scale_x = view_w / img_w
        scale_y = view_h / img_h
        return min(scale_x, scale_y)

    def _clamp_pan_offset(self) -> None:
        """
        FR: Contraint le panoramique pour maintenir l'image visible et centrée dans le volet actif.
        EN: Constrains the pan offset to keep the image visible and centered inside the active pane.
        Ref: picasa3.exe @ PanHandler 0x0093F3A8
        """
        pix = self._get_active_pane_pixmap()
        if pix is None or pix.isNull():
            self.pan_offset = QPointF(0, 0)
            return

        pane_rect = self._get_active_pane_rect()
        pane_w = pane_rect.width()
        pane_h = pane_rect.height()
        scale = self.get_current_scale()
        draw_w = pix.width() * scale
        draw_h = pix.height() * scale

        # FR: Axe horizontal / EN: Horizontal axis
        if draw_w <= pane_w:
            new_x = 0.0
        else:
            max_delta_x = (draw_w - pane_w) / 2.0
            bound_x = max_delta_x + 40.0
            new_x = max(-bound_x, min(bound_x, self.pan_offset.x()))

        # FR: Axe vertical / EN: Vertical axis
        if draw_h <= pane_h:
            new_y = 0.0
        else:
            max_delta_y = (draw_h - pane_h) / 2.0
            bound_y = max_delta_y + 40.0
            new_y = max(-bound_y, min(bound_y, self.pan_offset.y()))

        self.pan_offset = QPointF(new_x, new_y)

    def set_zoom_anchored(self, new_zoom: float, anchor: QPointF) -> None:
        """
        FR: Zoom ancré au niveau du curseur : le point de la photo sous la souris reste stable (1-Up et 2-Up).
        EN: Cursor-anchored zoom: the point on the photo under the mouse remains stationary (1-Up and 2-Up).
        Ref: picasa3.exe @ CLoupeMaker / OneUpUI 0x0094355C, 0x005D1520
        """
        pix = self._get_active_pane_pixmap()
        if pix is None or pix.isNull():
            return

        pane_rect = self._get_active_pane_rect(for_pos=anchor)
        old_scale = self.get_current_scale()
        clamped_zoom = max(0.1, min(6.0, new_zoom))
        fit_scale = self._get_fit_scale()

        if clamped_zoom <= fit_scale * 0.98:
            self.reset_zoom_to_fit()
            return

        draw_w_old = pix.width() * old_scale
        draw_h_old = pix.height() * old_scale
        cx_old = pane_rect.x() + (pane_rect.width() - draw_w_old) / 2.0 + self.pan_offset.x()
        cy_old = pane_rect.y() + (pane_rect.height() - draw_h_old) / 2.0 + self.pan_offset.y()

        u = (anchor.x() - cx_old) / draw_w_old if draw_w_old > 0 else 0.5
        v = (anchor.y() - cy_old) / draw_h_old if draw_h_old > 0 else 0.5
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))

        draw_w_new = pix.width() * clamped_zoom
        draw_h_new = pix.height() * clamped_zoom

        cx_new = anchor.x() - u * draw_w_new
        cy_new = anchor.y() - v * draw_h_new

        self.pan_offset = QPointF(
            cx_new - (pane_rect.x() + (pane_rect.width() - draw_w_new) / 2.0),
            cy_new - (pane_rect.y() + (pane_rect.height() - draw_h_new) / 2.0)
        )
        self.zoom_level = clamped_zoom
        self.fit_to_window = False
        self._clamp_pan_offset()
        self.zoom_changed.emit(self.zoom_level)
        self.update()

    def _update_loupe_geometry(self) -> None:
        """
        FR: Calcule la géométrie du navigateur Loupe (`editpanel/nav`), de son bouton de fermeture `[×]`
        et du cadre de visée orange (`nav/nav`) en mode 1-Up (`A`) comme en mode 2-Up (`A|B`, `A|A`).
        EN: Computes the geometry of the Loupe overview navigator (`editpanel/nav`), its close `[×]` button,
        and the orange viewfinder frame (`nav/nav`) in both 1-Up (`A`) and 2-Up (`A|B`, `A|A`) modes.
        Ref: picasa3.exe @ editpanel/nav (0x005D165D), nav/overview (0x0056953D), nav/zoom (0x005736F4),
             nav/nav (0x0056B338), PanHandler (0x005C46B0 / 0x005C47F0 -> 0x00597D10)
        """
        pix = self._get_active_pane_pixmap()
        if not self.is_zoomed_in() or pix is None or pix.isNull():
            self._nav_card_rect = QRectF()
            self._nav_img_rect = QRectF()
            self._vbox_rect = QRectF()
            self._nav_close_rect = QRectF()
            self._is_hovering_nav_close = False
            return

        img_w = pix.width()
        img_h = pix.height()
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
        header_h = 18.0
        card_w = max(nw + pad * 2.0, 96.0)
        card_h = header_h + nh + pad * 1.5
        margin_right = 18.0
        margin_bottom = 18.0

        card_x = self.width() - card_w - margin_right
        card_y = self.height() - card_h - margin_bottom

        self._nav_card_rect = QRectF(card_x, card_y, card_w, card_h)
        img_x = card_x + (card_w - nw) / 2.0
        img_y = card_y + header_h + pad * 0.5
        self._nav_img_rect = QRectF(img_x, img_y, nw, nh)

        close_sz = 14.0
        close_x = card_x + card_w - close_sz - 4.0
        close_y = card_y + (header_h - close_sz) / 2.0 + 1.0
        self._nav_close_rect = QRectF(close_x, close_y, close_sz, close_sz)

        pane_rect = self._get_active_pane_rect()
        pane_w = pane_rect.width()
        pane_h = pane_rect.height()
        scale = self.get_current_scale()
        draw_w = img_w * scale
        draw_h = img_h * scale

        cx = (pane_w - draw_w) / 2.0 + self.pan_offset.x()
        cy = (pane_h - draw_h) / 2.0 + self.pan_offset.y()

        u1 = max(0.0, min(1.0, -cx / draw_w)) if draw_w > 0 else 0.0
        u2 = max(0.0, min(1.0, (pane_w - cx) / draw_w)) if draw_w > 0 else 1.0
        v1 = max(0.0, min(1.0, -cy / draw_h)) if draw_h > 0 else 0.0
        v2 = max(0.0, min(1.0, (pane_h - cy) / draw_h)) if draw_h > 0 else 1.0

        if u2 < u1:
            u2 = u1
        if v2 < v1:
            v2 = v1

        vx = self._nav_img_rect.x() + u1 * self._nav_img_rect.width()
        vy = self._nav_img_rect.y() + v1 * self._nav_img_rect.height()
        vw = max(8.0, (u2 - u1) * self._nav_img_rect.width())
        vh = max(8.0, (v2 - v1) * self._nav_img_rect.height())

        self._vbox_rect = QRectF(vx, vy, vw, vh)

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique le style de thème PicasaStyle au canevas et déclenche un rafraîchissement.
        EN: Applies the PicasaStyle theme to the canvas and triggers a repaint.
        """
        self.style = style
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine le fond du canevas ainsi que la vue One-Up ou Two-Up (A|B, A|A).
        EN: Paints the canvas background and either the One-Up or Two-Up (A|B, A|A) view.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # FR: Fond du canevas adapté au thème actif / EN: Canvas background matching active theme (style.grid_bgcolor)
        painter.fillRect(self.rect(), self.style.grid_bgcolor)

        if self.view_mode in ("A_B", "A_A"):
            self._paint_two_up(painter)
        else:
            self._paint_one_up(painter)


    def _paint_one_up(self, painter: QPainter) -> None:
        """
        FR: Rendu standard en vue unique (One-Up) avec ombre, visages, Loupe et outils interactifs.
        EN: Standard single-image (One-Up) rendering with drop shadow, face tags, Loupe, and interactive tools.
        """
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

        # FR: Ombre portée de la photo / EN: Photo drop shadow
        shadow_rect = target_rect.translated(4, 4)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 90))

        # FR: Dessin de l'image haute définition (avec rotation live si outil Redresser actif) / EN: Draw high-res image (with live rotation if Straighten tool is active)
        if self.is_straightening and abs(self.straighten_angle) >= 0.01:
            import math
            painter.save()
            painter.setClipRect(target_rect)
            cx = target_rect.center().x()
            cy = target_rect.center().y()
            painter.translate(cx, cy)
            # FR: En Qt, painter.rotate(angle) tourne dans le sens horaire, ce qui correspond
            #     à PIL.Image.rotate(-angle) et à FUN_0042bfa0 (0x0042BFA0).
            # EN: In Qt, painter.rotate(angle) rotates clockwise, matching PIL.Image.rotate(-angle)
            #     and FUN_0042bfa0 (0x0042BFA0).
            painter.rotate(self.straighten_angle)
            # FR: Calcul du facteur d'agrandissement anti-bords-noirs / EN: Anti-black-corners zoom scale calculation (Ref: Picasa tilt math, 0x008814AC)
            rad = math.radians(abs(self.straighten_angle))
            aspect = (draw_w / draw_h) if draw_h > 0 else 1.0
            scale_crop = math.cos(rad) + (math.sin(rad) * aspect if aspect >= 1.0 else math.sin(rad) / aspect)
            painter.scale(scale_crop, scale_crop)
            painter.drawPixmap(QRectF(-draw_w / 2.0, -draw_h / 2.0, draw_w, draw_h), self._display_pixmap, QRectF(self._display_pixmap.rect()))
            painter.restore()
        else:
            painter.drawPixmap(target_rect, self._display_pixmap, QRectF(self._display_pixmap.rect()))

        # FR: Dessin des balises de visages (y compris pendant le redressement interactif)
        # EN: Draw face tags (including during interactive straightening) (Ref: 0x008AAD76, 0x0042BFA0)
        if self.show_face_tags and self.face_rects and (not self.is_any_tool_active() or self.is_straightening):
            self._draw_face_tags(painter, target_rect)

        # FR: Dessin de l'outil d'ajout manuel de visage / EN: Draw manual face addition overlay (Ref: 0x008A0D0C)
        if self.is_manual_face_add:
            self._draw_manual_face_overlay(painter, target_rect)

        # FR: Dessin du navigateur Loupe d'ensemble / EN: Draw overview Loupe navigator (Ref: 0x00942AE4)
        if not self.is_any_tool_active():
            self._update_loupe_geometry()
            self._draw_overview_navigator(painter)

        # FR: Dessin des outils interactifs / EN: Draw interactive tool overlays
        self._image_target_rect = target_rect
        if self.is_cropping:
            self._draw_crop_overlay(painter, target_rect)
        elif self.is_straightening:
            self._draw_straighten_overlay(painter, target_rect)
        elif self.is_text_tool_active:
            self._draw_text_overlay(painter, target_rect)
        elif self.is_retouching:
            self._draw_retouch_overlay(painter, target_rect)
        elif self.is_redeye:
            self._draw_redeye_overlay(painter, target_rect)

    def _paint_two_up(self, painter: QPainter) -> None:
        """
        FR: Rendu en mode comparaison (Two-Up A|B ou A|A), avec prise en charge de la division
            horizontale (côte à côte gauche/droite) et verticale (haut/bas) et du focus actif.
        EN: Comparison mode rendering (Two-Up A|B or A|A), supporting horizontal (left/right)
            and vertical (top/bottom) splits and active pane focus.
        Ref: picasa3.exe @ TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C), FUN_00569720 (0x00569720),
             FUN_0056A160 (0x0056A160), editpanel/selection_label (0x00C8ED4C)
        """
        w, h = float(self.width()), float(self.height())
        if self.split_orientation == "vertical":
            half_h = (h - 2.0) / 2.0
            first_rect = QRectF(0, 0, w, half_h)
            second_rect = QRectF(0, half_h + 2.0, w, half_h)
            painter.fillRect(QRectF(0, half_h, w, 2), QColor(20, 22, 26))
        else:
            half_w = (w - 2.0) / 2.0
            first_rect = QRectF(0, 0, half_w, h)
            second_rect = QRectF(half_w + 2.0, 0, half_w, h)
            painter.fillRect(QRectF(half_w, 0, 2, h), QColor(20, 22, 26))

        sel_lbl = self.res_mgr.get_xml_string("editpanel/selection_label", "Sélectionné")
        act_first = (self.active_pane == "A")
        act_second = (self.active_pane == "B")

        if self.view_mode == "A_A":
            img_first = self._original_pixmap if self._original_pixmap else self._display_pixmap
            img_second = self._display_pixmap
            badge_first = f"Originale (Avant) — {sel_lbl}" if act_first else "Originale (Avant)"
            badge_second = f"Retouchée (Après) — {sel_lbl}" if act_second else "Retouchée (Après)"
        else:  # "A_B"
            img_first = self._display_pixmap
            img_second = self._secondary_pixmap
            badge_first = f"Photo A : {self.main_title} ({sel_lbl})" if act_first else f"Photo A : {self.main_title}"
            badge_second = f"Photo B : {self.secondary_title} ({sel_lbl})" if act_second else f"Photo B : {self.secondary_title}"

        self._draw_pane_content(painter, first_rect, img_first, badge_first, act_first, False)
        self._draw_pane_content(painter, second_rect, img_second, badge_second, act_second, (self.view_mode == "A_A"))

        # FR: Dessin du navigateur Loupe d'ensemble avec cadre de visée orange en mode A|B et A|A
        # EN: Draw overview Loupe navigator with orange viewfinder frame in A|B and A|A modes
        # Ref: picasa3.exe @ 0x005D1520..0x005D16B6 (editpanel/nav, [ebp + 0x327c] / [ebp + 0x3280])
        if not self.is_any_tool_active():
            self._update_loupe_geometry()
            self._draw_overview_navigator(painter)

    def _draw_pane_content(
        self, painter: QPainter, pane_rect: QRectF,
        pix: Optional[QPixmap], badge_text: str, is_active: bool, is_modified_style: bool
    ) -> None:
        """
        FR: Dessine une photo, son cadre de focus et son étiquette dans un volet de comparaison 2-Up.
        EN: Draws a photo, its focus border, and its badge label inside a 2-Up comparison pane.
        """
        if pix is None or pix.isNull():
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(pane_rect, Qt.AlignmentFlag.AlignCenter, "Aucune photo sélectionnée")
        else:
            # FR: Calcul du ratio adapté au demi-panneau / EN: Compute scale ratio for half-pane
            scale_x = max(10.0, pane_rect.width() - 20.0) / max(1, pix.width())
            scale_y = max(10.0, pane_rect.height() - 20.0) / max(1, pix.height())
            fit_scale = min(scale_x, scale_y)
            if self.fit_to_window:
                scale = fit_scale
            else:
                active_fit = max(0.001, self._get_fit_scale())
                scale = self.zoom_level * (fit_scale / active_fit)

            dw = pix.width() * scale
            dh = pix.height() * scale
            cx = pane_rect.x() + (pane_rect.width() - dw) / 2.0 + self.pan_offset.x()
            cy = pane_rect.y() + (pane_rect.height() - dh) / 2.0 + self.pan_offset.y()
            t_rect = QRectF(cx, cy, dw, dh)

            painter.save()
            painter.setClipRect(pane_rect)

            # FR: Ombre portée / EN: Drop shadow
            painter.fillRect(t_rect.translated(3, 3), QColor(0, 0, 0, 90))
            # FR: Image haute résolution / EN: High-resolution image
            painter.drawPixmap(t_rect, pix, QRectF(pix.rect()))
            if is_active:
                painter.setPen(QPen(QColor(51, 153, 255, 220), 2.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(t_rect.adjusted(-1, -1, 1, 1))
            painter.restore()

        # FR: Badge pill en haut à gauche du volet / EN: Top-left pill badge of the pane
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
        FR: Dessine la miniature flottante de vue d'ensemble (`editpanel/nav`) avec l'en-tête de zoom (`nav/zoom`),
        la petite croix de fermeture `[×]` (`PanHandler @ 0x005C46B0 -> 0x00597D10`) et le cadre de visée orange (`nav/nav`).
        EN: Draws the floating overview thumbnail navigator (`editpanel/nav`) with the zoom header (`nav/zoom`),
        the small close cross `[×]` button (`PanHandler @ 0x005C46B0 -> 0x00597D10`), and the orange viewfinder frame (`nav/nav`).
        Ref: picasa3.exe @ editpanel/nav (0x005D165D), nav/overview (0x0056953D), nav/zoom (0x005736F4 -> 0x00A615C0),
             nav/nav (0x0056B338), PanHandler (0x005C46B0 / 0x005C47F0 -> 0x00597D10)
        """
        if not self.is_zoomed_in() or not self.show_loupe_navigator:
            return
        if self._nav_card_rect.isEmpty() or self._nav_img_rect.isEmpty():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. FR: Ombre portée de la carte Loupe / EN: Loupe card drop shadow
        shadow_rect = self._nav_card_rect.translated(2, 3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 110))
        painter.drawRoundedRect(shadow_rect, 6.0, 6.0)

        # 2. FR: Carte d'arrière-plan semi-transparente sombre / EN: Dark semi-transparent background card
        painter.setBrush(QColor(22, 24, 28, 230))
        painter.setPen(QPen(QColor(70, 75, 85, 220), 1.0))
        painter.drawRoundedRect(self._nav_card_rect, 6.0, 6.0)

        # 2b. FR: En-tête de zoom (nav/zoom @ 0x00A615C0) et bouton croix [×] (PanHandler @ 0x005C46B0 -> 0x00597D10)
        # EN: Zoom header (nav/zoom @ 0x00A615C0) and close cross [×] button (PanHandler @ 0x005C46B0 -> 0x00597D10)
        zoom_pct = int(round(self.get_current_scale() * 100.0))
        lbl_rect = QRectF(
            self._nav_card_rect.left() + 6.0,
            self._nav_card_rect.top() + 1.0,
            max(20.0, self._nav_card_rect.width() - 28.0),
            16.0,
        )
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(210, 215, 225, 230))
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{zoom_pct}%")

        if not self._nav_close_rect.isEmpty():
            if self._is_hovering_nav_close:
                painter.setBrush(QColor(220, 70, 60, 220))
                painter.setPen(QPen(QColor(255, 160, 150, 240), 1.0))
            else:
                painter.setBrush(QColor(55, 60, 70, 190))
                painter.setPen(QPen(QColor(130, 138, 150, 200), 1.0))
            painter.drawRoundedRect(self._nav_close_rect, 3.0, 3.0)

            cross_pen = QPen(
                QColor(255, 255, 255, 255) if self._is_hovering_nav_close else QColor(215, 220, 230, 235),
                1.6,
            )
            cross_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(cross_pen)
            m = 3.8
            cx1 = self._nav_close_rect.left() + m
            cy1 = self._nav_close_rect.top() + m
            cx2 = self._nav_close_rect.right() - m
            cy2 = self._nav_close_rect.bottom() - m
            painter.drawLine(QPointF(cx1, cy1), QPointF(cx2, cy2))
            painter.drawLine(QPointF(cx2, cy1), QPointF(cx1, cy2))

        # 3. FR: Miniature de l'image du volet actif / EN: Active pane image thumbnail
        active_pix = self._get_active_pane_pixmap()
        if active_pix is self._display_pixmap:
            if (self._nav_thumbnail is None or self._nav_thumbnail.isNull()) and active_pix and not active_pix.isNull():
                self._nav_thumbnail = active_pix.scaled(
                    180, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            if self._nav_thumbnail and not self._nav_thumbnail.isNull():
                painter.drawPixmap(self._nav_img_rect, self._nav_thumbnail, QRectF(self._nav_thumbnail.rect()))
            elif active_pix:
                painter.drawPixmap(self._nav_img_rect, active_pix, QRectF(active_pix.rect()))
        elif active_pix and not active_pix.isNull():
            painter.drawPixmap(self._nav_img_rect, active_pix, QRectF(active_pix.rect()))

        # 4. FR: Voile sombre atténuant les zones hors du cadrage actuel / EN: Dark veil dimming areas outside the current framing
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 70))
        painter.drawRect(self._nav_img_rect)

        # 5. FR: Cadre de visée (Orange Picasa #FF9900) / EN: Viewfinder Frame (Picasa Orange #FF9900)
        painter.setBrush(QColor(255, 145, 0, 50))
        painter.setPen(QPen(QColor(255, 155, 0, 240), 1.8))
        painter.drawRect(self._vbox_rect)

        # FR: Coins renforcés caractéristiques de Picasa Loupe / EN: Signature Picasa Loupe corner accents
        c_len = min(6.0, min(self._vbox_rect.width(), self._vbox_rect.height()) / 2.0)
        c_pen = QPen(QColor(255, 220, 130, 255), 2.2)
        painter.setPen(c_pen)
        x1, y1 = self._vbox_rect.left(), self._vbox_rect.top()
        x2, y2 = self._vbox_rect.right(), self._vbox_rect.bottom()

        # FR: Coin Haut-Gauche / EN: Top-Left Corner
        painter.drawLine(QPointF(x1, y1), QPointF(x1 + c_len, y1))
        painter.drawLine(QPointF(x1, y1), QPointF(x1, y1 + c_len))
        # FR: Coin Haut-Droit / EN: Top-Right Corner
        painter.drawLine(QPointF(x2, y1), QPointF(x2 - c_len, y1))
        painter.drawLine(QPointF(x2, y1), QPointF(x2, y1 + c_len))
        # FR: Coin Bas-Gauche / EN: Bottom-Left Corner
        painter.drawLine(QPointF(x1, y2), QPointF(x1 + c_len, y2))
        painter.drawLine(QPointF(x1, y2), QPointF(x1, y2 - c_len))
        # FR: Coin Bas-Droit / EN: Bottom-Right Corner
        painter.drawLine(QPointF(x2, y2), QPointF(x2 - c_len, y2))
        painter.drawLine(QPointF(x2, y2), QPointF(x2, y2 - c_len))

        painter.restore()

    def set_active_transform(
        self,
        crop_rect: Optional[Tuple[float, float, float, float]] = None,
        tilt_angle: float = 0.0,
        rotation_steps: int = 0
    ) -> None:
        """
        FR: Définit les paramètres de transformation non-destructive appliqués à la photo affichée
            pour projeter correctement les balises de visages et les nouvelles annotations.
        EN: Sets the non-destructive transformation parameters applied to the displayed photo
            to accurately project face tags and new annotations.
        Ref: picasa3.exe @ 0x00456A15, 0x0042A6F9, 0x008814AC
        """
        self._active_crop_rect = crop_rect
        self._active_tilt_angle = float(tilt_angle)
        self._active_rotation_steps = int(rotation_steps) % 4
        self.update()

    def is_any_tool_active(self) -> bool:
        """
        FR: Indique si un outil interactif monopolise la souris (empêchant le pan/zoom involontaire).
        EN: Indicates whether an interactive tool currently captures mouse input (preventing unintended pan/zoom).
        """
        return bool(
            self.is_cropping or
            self.is_straightening or
            self.is_manual_face_add or
            self.is_text_tool_active or
            self.is_retouching or
            self.is_redeye
        )

    def set_face_rects(self, rects: List[Any]) -> None:
        """
        FR: Définit la liste des rectangles de visages (`FaceRect`) associés à la photo active.
        EN: Sets the list of face rectangles (`FaceRect`) associated with the active photo.
        """
        self.face_rects = rects
        self.hovered_face_idx = -1
        self.update()

    def set_show_face_tags(self, show: bool) -> None:
        """
        FR: Active ou désactive l'affichage des cadres et étiquettes de visages sur la photo.
        EN: Enables or disables drawing face frames and name badges on the photo.
        """
        self.show_face_tags = show
        self.update()

    def _draw_face_tags(self, painter: QPainter, target_rect: QRectF) -> None:
        """
        FR: Dessine les rectangles de visages projetés et leurs étiquettes de nom sur l'image.
        EN: Draws the projected face rectangles and their contact name badges on the image.
        Ref: picasa3.exe @ 0x008AAD76
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        aspect = 1.0
        if self._display_pixmap and not self._display_pixmap.isNull() and self._display_pixmap.height() > 0:
            aspect = self._display_pixmap.width() / float(self._display_pixmap.height())

        for i, fr in enumerate(self.face_rects):
            # FR: Projeter le visage des coordonnées d'origine vers l'espace affiché / EN: Project face from original coordinates to display space
            disp_fr = fr.transform_to_display(
                crop_rect=self._active_crop_rect,
                rotation=self._active_rotation_steps,
                tilt_angle=self._active_tilt_angle,
                aspect_ratio=aspect
            )
            if disp_fr is not None and self.is_straightening and abs(self.straighten_angle) >= 0.01:
                disp_fr = disp_fr.to_tilted_space(self.straighten_angle, aspect_ratio=aspect)
            if disp_fr is None:
                continue

            fx = target_rect.x() + disp_fr.left * target_rect.width()
            fy = target_rect.y() + disp_fr.top * target_rect.height()
            fw = disp_fr.width * target_rect.width()
            fh = disp_fr.height * target_rect.height()

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

    # --- FR: Outil d'ajout manuel de visage / EN: Manual face addition tool (Ref: picasa3.exe @ 0x008A0D0C, 0x008A1594) ---

    def start_manual_face_add(self) -> None:
        """
        FR: Active le mode d'ajout manuel d'un visage avec curseur croix et cadre interactif.
        EN: Activates manual face addition mode with crosshair cursor and interactive frame.
        """
        self.is_manual_face_add = True
        self._manual_face_start = None
        self._manual_face_current = None
        self.setCursor(self._face_cursor)
        self.update()

    def cancel_manual_face_add(self) -> None:
        """
        FR: Annule l'ajout manuel de visage et rétablit le curseur normal.
        EN: Cancels manual face addition and restores the default pan cursor.
        """
        self.is_manual_face_add = False
        self._manual_face_start = None
        self._manual_face_current = None
        self.setCursor(self._pan_cursor)
        self.update()

    def _draw_manual_face_overlay(self, painter: QPainter, target_rect: QRectF) -> None:
        """
        FR: Dessine le bandeau d'instructions et le rectangle de sélection manuelle du visage.
        EN: Draws the instruction banner and the manual face selection rectangle.
        Ref: picasa3.exe @ manual_add::instructions (0x008A1594), peoplepanel/manual_frame (0x00898ADC)
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. FR: Bandeau supérieur d'instructions Picasa / EN: Picasa top instruction banner
        banner_w = min(560.0, float(self.width() - 30))
        banner_h = 36.0
        banner_x = (float(self.width()) - banner_w) / 2.0
        banner_y = 12.0
        banner_rect = QRectF(banner_x, banner_y, banner_w, banner_h)

        # FR: Fond sombre arrondi avec bordure dorée / EN: Rounded dark background with gold border
        painter.setPen(QPen(QColor(240, 180, 40, 200), 1.2))
        painter.setBrush(QColor(22, 26, 32, 235))
        painter.drawRoundedRect(banner_rect, 6.0, 6.0)

        painter.setPen(QColor("#FFDE66"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(
            banner_rect,
            Qt.AlignmentFlag.AlignCenter,
            "➕ Dessinez un rectangle autour du visage à identifier (Échap pour annuler)"
        )

        # 2. FR: Rectangle de sélection manuelle en cours de tracé / EN: Manual selection rectangle being drawn
        if self._manual_face_start and self._manual_face_current:
            x1 = min(self._manual_face_start.x(), self._manual_face_current.x())
            y1 = min(self._manual_face_start.y(), self._manual_face_current.y())
            x2 = max(self._manual_face_start.x(), self._manual_face_current.x())
            y2 = max(self._manual_face_start.y(), self._manual_face_current.y())

            sx = target_rect.x() + x1 * target_rect.width()
            sy = target_rect.y() + y1 * target_rect.height()
            sw = max(2.0, (x2 - x1) * target_rect.width())
            sh = max(2.0, (y2 - y1) * target_rect.height())
            box = QRectF(sx, sy, sw, sh)

            # FR: Remplissage semi-transparent et contour jaune pointillé / EN: Semi-transparent fill and dashed yellow outline
            painter.setBrush(QColor(255, 215, 60, 45))
            pen = QPen(QColor(255, 220, 80, 240), 2.0, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRoundedRect(box, 3.0, 3.0)

            # FR: Poignées blanches aux 4 coins / EN: White handles at the 4 corners (Ref: peoplepanel/manual_frame)
            hs = 6.0
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(QPen(QColor(20, 20, 20), 1.0))
            for pt in [box.topLeft(), box.topRight(), box.bottomLeft(), box.bottomRight()]:
                painter.drawRect(QRectF(pt.x() - hs / 2.0, pt.y() - hs / 2.0, hs, hs))

            # FR: Étiquette "Nouveau visage" / EN: "New face" label
            lbl_rect = QRectF(box.left(), box.bottom() + 4, max(90.0, box.width()), 20.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(20, 24, 30, 220))
            painter.drawRoundedRect(lbl_rect, 3.0, 3.0)
            painter.setPen(QColor("#FFDE66"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, "Nouveau visage")

        painter.restore()

    # --- FR: Outil de recadrage interactif / EN: Interactive crop tool (Ref: picasa3.exe @ CSmartCrop, 0x008A786C) ---

    def start_crop(self, initial_crop_norm: Optional[QRectF] = None) -> None:
        """
        FR: Active le mode de recadrage interactif avec la grille des tiers.
        EN: Activates the interactive cropping mode with the rule-of-thirds grid.
        """
        self.is_cropping = True
        self.crop_target_ratio = None
        if initial_crop_norm and not initial_crop_norm.isEmpty():
            self.crop_rect_norm = initial_crop_norm
        else:
            self.crop_rect_norm = QRectF(0.1, 0.1, 0.8, 0.8)
        self.setCursor(self._crop_cursor)
        self.update()

    def set_crop_aspect_ratio(self, ratio: Optional[float]) -> None:
        """
        FR: Fixe le ratio de proportion du recadrage (ex: 1.0, 4/3, 16/9, None pour manuel).
        EN: Sets the crop aspect ratio constraint (e.g. 1.0, 4/3, 16/9, or None for free manual).
        """
        self.crop_target_ratio = ratio
        if ratio and self._display_pixmap and not self._display_pixmap.isNull():
            img_w = self._display_pixmap.width()
            img_h = self._display_pixmap.height()
            curr = self.crop_rect_norm
            target_norm_ratio = ratio * (img_h / float(img_w))
            new_w = min(0.9, curr.height() * target_norm_ratio)
            new_h = new_w / target_norm_ratio
            cx, cy = curr.center().x(), curr.center().y()
            new_x = max(0.0, min(1.0 - new_w, cx - new_w / 2.0))
            new_y = max(0.0, min(1.0 - new_h, cy - new_h / 2.0))
            self.crop_rect_norm = QRectF(new_x, new_y, new_w, new_h)
        self.update()

    def cancel_crop(self) -> None:
        """
        FR: Annule le recadrage interactif et rétablit le curseur normal.
        EN: Cancels the interactive crop and restores the default pan cursor.
        """
        self.is_cropping = False
        self._crop_drag_handle = None
        self.setCursor(self._pan_cursor)
        self.update()

    def apply_crop(self) -> str:
        """
        FR: Valide le recadrage, désactive l'outil et retourne `rect64(...)` pour `.picasa.ini`.
        EN: Commits the crop, deactivates the tool, and returns `rect64(...)` for `.picasa.ini`.
        """
        self.is_cropping = False
        self._crop_drag_handle = None
        self.setCursor(self._pan_cursor)
        r = self.crop_rect_norm
        crop_str = encode_rect64_string(r.left(), r.top(), r.right(), r.bottom())
        self.update()
        return crop_str

    def _draw_crop_overlay(self, painter: QPainter, target_rect: QRectF) -> None:
        """
        FR: Rendu interactif du recadrage avec masque sombre, règle des tiers et 8 poignées.
        EN: Interactive crop overlay rendering with dark mask, rule of thirds, and 8 resize handles.
        Ref: picasa3.exe @ CSmartCrop, 0x008A786C
        """
        sx = target_rect.x() + self.crop_rect_norm.x() * target_rect.width()
        sy = target_rect.y() + self.crop_rect_norm.y() * target_rect.height()
        sw = self.crop_rect_norm.width() * target_rect.width()
        sh = self.crop_rect_norm.height() * target_rect.height()
        crop_screen = QRectF(sx, sy, sw, sh)

        # 1. FR: Masque semi-transparent sombre à l'extérieur de la sélection / EN: Dark semi-transparent mask outside selection
        mask_color = QColor(0, 0, 0, 160)
        # FR: Haut / EN: Top
        painter.fillRect(QRectF(target_rect.left(), target_rect.top(), target_rect.width(), max(0.0, sy - target_rect.top())), mask_color)
        # FR: Bas / EN: Bottom
        painter.fillRect(QRectF(target_rect.left(), sy + sh, target_rect.width(), max(0.0, target_rect.bottom() - (sy + sh))), mask_color)
        # FR: Gauche / EN: Left
        painter.fillRect(QRectF(target_rect.left(), sy, max(0.0, sx - target_rect.left()), sh), mask_color)
        # FR: Droite / EN: Right
        painter.fillRect(QRectF(sx + sw, sy, max(0.0, target_rect.right() - (sx + sw)), sh), mask_color)

        # 2. FR: Règle des tiers (Lignes discrètes en pointillés) / EN: Rule of thirds (Subtle dashed lines)
        painter.setPen(QPen(QColor(255, 255, 255, 110), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(sx + sw / 3.0, sy), QPointF(sx + sw / 3.0, sy + sh))
        painter.drawLine(QPointF(sx + 2.0 * sw / 3.0, sy), QPointF(sx + 2.0 * sw / 3.0, sy + sh))
        painter.drawLine(QPointF(sx, sy + sh / 3.0), QPointF(sx + sw, sy + sh / 3.0))
        painter.drawLine(QPointF(sx, sy + 2.0 * sh / 3.0), QPointF(sx + sw, sy + 2.0 * sh / 3.0))

        # 3. FR: Contour du cadre de recadrage / EN: Crop frame border
        painter.setPen(QPen(QColor(255, 255, 255, 240), 1.5, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(crop_screen)

        # 4. FR: Dessin des 8 poignées de redimensionnement / EN: Draw the 8 resize handles
        handle_size = 8.0
        half_h = handle_size / 2.0
        handles = [
            QPointF(sx, sy),                        # tl
            QPointF(sx + sw / 2.0, sy),             # tm
            QPointF(sx + sw, sy),                   # tr
            QPointF(sx + sw, sy + sh / 2.0),        # mr
            QPointF(sx + sw, sy + sh),              # br
            QPointF(sx + sw / 2.0, sy + sh),        # bm
            QPointF(sx, sy + sh),                   # bl
            QPointF(sx, sy + sh / 2.0),             # ml
        ]

        painter.setPen(QPen(QColor(40, 40, 40), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        for hp in handles:
            painter.drawRect(QRectF(hp.x() - half_h, hp.y() - half_h, handle_size, handle_size))

    def _get_crop_handle_at(self, pos: QPointF) -> Optional[str]:
        """
        FR: Identifie la poignée ou la zone de recadrage située sous la position `pos` de la souris.
        EN: Identifies the crop handle or interior zone under the mouse position `pos`.
        """
        if not self.is_cropping or self._image_target_rect.isEmpty():
            return None
        tr = self._image_target_rect
        sx = tr.x() + self.crop_rect_norm.x() * tr.width()
        sy = tr.y() + self.crop_rect_norm.y() * tr.height()
        sw = self.crop_rect_norm.width() * tr.width()
        sh = self.crop_rect_norm.height() * tr.height()

        tol = 9.0
        if abs(pos.x() - sx) <= tol and abs(pos.y() - sy) <= tol: return "tl"
        if abs(pos.x() - (sx + sw)) <= tol and abs(pos.y() - sy) <= tol: return "tr"
        if abs(pos.x() - (sx + sw)) <= tol and abs(pos.y() - (sy + sh)) <= tol: return "br"
        if abs(pos.x() - sx) <= tol and abs(pos.y() - (sy + sh)) <= tol: return "bl"
        if abs(pos.y() - sy) <= tol and sx <= pos.x() <= sx + sw: return "tm"
        if abs(pos.y() - (sy + sh)) <= tol and sx <= pos.x() <= sx + sw: return "bm"
        if abs(pos.x() - sx) <= tol and sy <= pos.y() <= sy + sh: return "ml"
        if abs(pos.x() - (sx + sw)) <= tol and sy <= pos.y() <= sy + sh: return "mr"

        if sx < pos.x() < sx + sw and sy < pos.y() < sy + sh:
            return "inside"
        return None

    def _handle_crop_drag(self, pos: QPointF) -> None:
        """
        FR: Met à jour le rectangle normalisé de recadrage lors du glissement d'une poignée ou du cadre.
        EN: Updates the normalized crop rectangle while dragging a handle or the frame interior.
        """
        if not self._crop_drag_handle or self._image_target_rect.isEmpty():
            return
        tr = self._image_target_rect
        dx_norm = (pos.x() - self._crop_drag_start_pos.x()) / tr.width()
        dy_norm = (pos.y() - self._crop_drag_start_pos.y()) / tr.height()
        r0 = self._crop_drag_start_rect

        left, top, right, bottom = r0.left(), r0.top(), r0.right(), r0.bottom()

        if self._crop_drag_handle == "inside":
            w = r0.width()
            h = r0.height()
            new_left = max(0.0, min(1.0 - w, left + dx_norm))
            new_top = max(0.0, min(1.0 - h, top + dy_norm))
            self.crop_rect_norm = QRectF(new_left, new_top, w, h)
            return

        if "l" in self._crop_drag_handle:
            left = max(0.0, min(right - 0.05, left + dx_norm))
        if "r" in self._crop_drag_handle:
            right = min(1.0, max(left + 0.05, right + dx_norm))
        if "t" in self._crop_drag_handle:
            top = max(0.0, min(bottom - 0.05, top + dy_norm))
        if "b" in self._crop_drag_handle:
            bottom = min(1.0, max(top + 0.05, bottom + dy_norm))

        if self.crop_target_ratio and self._display_pixmap and not self._display_pixmap.isNull():
            img_w = self._display_pixmap.width()
            img_h = self._display_pixmap.height()
            target_norm_ratio = self.crop_target_ratio * (img_h / float(img_w))
            w = right - left
            h = bottom - top
            if self._crop_drag_handle in ("l", "r"):
                new_h = w / target_norm_ratio
                bottom = min(1.0, top + new_h)
            else:
                new_w = h * target_norm_ratio
                right = min(1.0, left + new_w)

        self.crop_rect_norm = QRectF(left, top, max(0.05, right - left), max(0.05, bottom - top))

    # --- FR: Outil Redresser / EN: Straighten tool (Ref: filter_tilt, picasa3.exe @ 0x008814AC) ---

    def start_straighten(self, initial_angle: float = 0.0) -> None:
        """
        FR: Active le mode de redressement interactif avec l'angle initial spécifié.
        EN: Activates interactive straightening mode with the specified initial angle.
        """
        self.is_straightening = True
        self.straighten_angle = float(initial_angle)
        self.setCursor(self._tilt_cursor)
        self.update()

    def set_straighten_angle(self, angle: float) -> None:
        """
        FR: Met à jour l'angle de redressement en degrés et rafraîchit l'aperçu du canevas.
        EN: Updates the straightening angle in degrees and refreshes the canvas preview.
        """
        self.straighten_angle = float(angle)
        self.update()

    def apply_straighten(self) -> float:
        """
        FR: Valide le redressement, désactive l'outil et retourne l'angle final en degrés.
        EN: Commits the straightening operation, deactivates the tool, and returns the final angle in degrees.
        """
        self.is_straightening = False
        self.setCursor(self._pan_cursor)
        angle = self.straighten_angle
        self.update()
        return angle

    def cancel_straighten(self) -> None:
        """
        FR: Annule le redressement en cours et remet l'angle à zéro.
        EN: Cancels the straightening operation and resets the angle to zero.
        """
        self.is_straightening = False
        self.straighten_angle = 0.0
        self.setCursor(self._pan_cursor)
        self.update()

    def _draw_straighten_overlay(self, painter: QPainter, target_rect: QRectF) -> None:
        """
        FR: Dessine la grille d'alignement / niveau à bulle sur la photo pendant le redressement.
        EN: Draws the alignment grid / spirit level over the photo during straightening.
        Ref: picasa3.exe @ filter_tilt, 0x008814AC
        """
        painter.save()
        painter.setClipRect(target_rect)

        # FR: Grille orthogonale en pointillés fins semi-transparents / EN: Semi-transparent fine dashed orthogonal grid
        grid_pen = QPen(QColor(255, 255, 255, 110), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)

        step_x = target_rect.width() / 8.0
        for i in range(1, 8):
            gx = target_rect.left() + i * step_x
            painter.drawLine(QPointF(gx, target_rect.top()), QPointF(gx, target_rect.bottom()))

        step_y = target_rect.height() / 8.0
        for j in range(1, 8):
            gy = target_rect.top() + j * step_y
            painter.drawLine(QPointF(target_rect.left(), gy), QPointF(target_rect.right(), gy))

        # FR: Ligne de niveau centrale renforcée / EN: Highlighted central horizon level line
        center_pen = QPen(QColor(255, 255, 120, 180), 1.5, Qt.PenStyle.SolidLine)
        painter.setPen(center_pen)
        cy = target_rect.center().y()
        painter.drawLine(QPointF(target_rect.left(), cy), QPointF(target_rect.right(), cy))

        # FR: Badge d'angle flottant au centre bas / EN: Floating angle badge at bottom center
        badge_w, badge_h = 90.0, 28.0
        badge_x = target_rect.center().x() - badge_w / 2.0
        badge_y = target_rect.bottom() - badge_h - 14.0
        badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.drawRoundedRect(badge_rect, 5.0, 5.0)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        angle_str = f"{self.straighten_angle:+.1f}°"
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, angle_str)

        painter.restore()

    # --- FR: Outil Texte / EN: Text tool (Ref: editpanel/textgroupnode, 0x0089898A) ---

    def start_text_tool(self, initial_text: str = "") -> None:
        """
        FR: Active l'outil d'ajout de texte interactif sur le canevas.
        EN: Activates the interactive text overlay tool on the canvas.
        """
        self.is_text_tool_active = True
        self.text_content = initial_text
        self.update()

    def set_text_params(self, text: str, font_size: int = 28, color: Optional[QColor] = None, shadow: bool = True) -> None:
        """
        FR: Met à jour le contenu, la taille de police, la couleur et l'ombre de l'outil texte.
        EN: Updates the text content, font size, color, and drop shadow of the text tool.
        """
        self.text_content = text
        self.text_font_size = font_size
        if color is not None:
            self.text_color = color
        self.text_shadow = shadow
        self.update()

    def apply_text_tool(self) -> dict:
        """
        FR: Valide et désactive l'outil texte en retournant un dictionnaire de ses paramètres.
        EN: Commits and deactivates the text tool, returning a dictionary of its parameters.
        """
        self.is_text_tool_active = False
        res = {
            "text": self.text_content,
            "font_size": self.text_font_size,
            "color": (self.text_color.red(), self.text_color.green(), self.text_color.blue()),
            "shadow": self.text_shadow,
            "pos_norm": (self.text_pos_norm.x(), self.text_pos_norm.y())
        }
        self.update()
        return res

    def cancel_text_tool(self) -> None:
        """
        FR: Annule et désactive l'outil d'ajout de texte.
        EN: Cancels and deactivates the text overlay tool.
        """
        self.is_text_tool_active = False
        self.update()

    def _draw_text_overlay(self, painter: QPainter, target_rect: QRectF) -> None:
        """
        FR: Dessine l'éditeur de texte interactif sur la photo avec poignée de déplacement.
        EN: Draws the interactive text editor overlay on the photo with its drag handle.
        Ref: picasa3.exe @ editpanel/textringnode, editpanel/textgroupnode, 0x0089898A
        """
        painter.save()
        px = target_rect.left() + self.text_pos_norm.x() * target_rect.width()
        py = target_rect.top() + self.text_pos_norm.y() * target_rect.height()

        txt = self.text_content.strip()
        is_ghost = not txt
        display_txt = txt if txt else "Cliquez pour ajouter du texte"

        scaled_font_size = max(11, int(self.text_font_size * self.get_current_scale()))
        font = QFont("Segoe UI", scaled_font_size)
        if is_ghost:
            font.setItalic(True)
        painter.setFont(font)
        fm = painter.fontMetrics()
        bounds = fm.boundingRect(display_txt)
        padding = 8.0
        box_rect = QRectF(px - padding, py - bounds.height() - padding, bounds.width() + 2 * padding, bounds.height() + 2 * padding)

        # FR: Cadre de sélection / EN: Selection frame
        ring_pen = QPen(QColor(56, 121, 217, 220), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(ring_pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 80) if is_ghost else QColor(0, 0, 0, 50)))
        painter.drawRoundedRect(box_rect, 4.0, 4.0)

        # FR: Poignée d'ancrage circulaire / EN: Circular anchor handle
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.setBrush(QBrush(QColor(56, 121, 217)))
        painter.drawEllipse(QPointF(box_rect.left(), box_rect.center().y()), 5.0, 5.0)

        # FR: Texte (avec ombre si activée) / EN: Text (with drop shadow if enabled)
        if self.text_shadow and not is_ghost:
            painter.setPen(QColor(0, 0, 0, 220))
            painter.drawText(QPointF(px + 2, py + 2), display_txt)

        text_color = QColor(200, 200, 200, 180) if is_ghost else self.text_color
        painter.setPen(text_color)
        painter.drawText(QPointF(px, py), display_txt)

        self._text_screen_rect = box_rect
        painter.restore()

    # --- FR: Outil Retouche / EN: Retouch tool (Healing Puck, Ref: filterdesc.xml @ retouch, IDC_PUCK (cursor_9.cur), 0x0088C3EC) ---

    def start_retouch(self, radius: float = 0.04) -> None:
        """
        FR: Active le mode de retouche locale par tampon de lissage.
        EN: Activates local blemish retouching mode using the healing brush.
        """
        self.is_retouching = True
        self.retouch_radius = radius
        self._retouch_hover_pos = None
        self.setCursor(self._retouch_cursor)
        self.update()

    def set_retouch_radius(self, radius: float) -> None:
        """
        FR: Met à jour le rayon normalisé du pinceau de retouche.
        EN: Updates the normalized radius of the retouching brush.
        """
        self.retouch_radius = radius
        self.update()

    def cancel_retouch(self) -> None:
        """
        FR: Désactive le mode de retouche locale et rétablit le curseur normal.
        EN: Deactivates local retouching mode and restores the default pan cursor.
        """
        self.is_retouching = False
        self._retouch_hover_pos = None
        self.setCursor(self._pan_cursor)
        self.update()

    def _draw_retouch_overlay(self, painter: QPainter, target_rect: QRectF) -> None:
        """
        FR: Dessine l'anneau de prévisualisation du tampon de retouche (Healing puck).
        EN: Draws the preview ring of the retouching brush (Healing puck).
        Ref: filterdesc.xml @ retouch, IDC_PUCK (cursor_9.cur), 0x0088C3EC
        """
        if not self.is_retouching or not self._retouch_hover_pos:
            return
        if not target_rect.contains(self._retouch_hover_pos):
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rad_px = max(6.0, self.retouch_radius * min(target_rect.width(), target_rect.height()))
        puck_rect = QRectF(
            self._retouch_hover_pos.x() - rad_px,
            self._retouch_hover_pos.y() - rad_px,
            rad_px * 2.0,
            rad_px * 2.0
        )
        painter.setBrush(QColor(255, 230, 80, 30))
        painter.setPen(QPen(QColor(255, 240, 100, 220), 1.2, Qt.PenStyle.DashLine))
        painter.drawEllipse(puck_rect)

        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.0))
        cx = self._retouch_hover_pos.x()
        cy = self._retouch_hover_pos.y()
        painter.drawLine(QPointF(cx - 4, cy), QPointF(cx + 4, cy))
        painter.drawLine(QPointF(cx, cy - 4), QPointF(cx, cy + 4))

        painter.restore()

    # --- FR: Outil Yeux Rouges / EN: Red-Eye tool (Ref: filterdesc.xml @ redeye, IDC_REDEYE (cursor_8.cur), 0x005E7CD7) ---

    def start_redeye(self) -> None:
        """
        FR: Active le mode interactif de correction des yeux rouges.
        EN: Activates the interactive red-eye reduction mode.
        """
        self.is_redeye = True
        self._redeye_start = None
        self._redeye_current = None
        self.setCursor(self._redeye_cursor)
        self.update()

    def cancel_redeye(self) -> None:
        """
        FR: Désactive le mode de correction des yeux rouges et rétablit le curseur normal.
        EN: Deactivates red-eye reduction mode and restores the default pan cursor.
        """
        self.is_redeye = False
        self._redeye_start = None
        self._redeye_current = None
        self.setCursor(self._pan_cursor)
        self.update()

    def _draw_redeye_overlay(self, painter: QPainter, target_rect: QRectF) -> None:
        """
        FR: Dessine le cadre de sélection de suppression des yeux rouges en cours de tracé.
        EN: Draws the red-eye removal selection box currently being dragged.
        Ref: filterdesc.xml @ redeye, IDC_REDEYE (cursor_8.cur), 0x005E7CD7
        """
        if not self.is_redeye or not self._redeye_start or not self._redeye_current:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        x1 = min(self._redeye_start.x(), self._redeye_current.x())
        y1 = min(self._redeye_start.y(), self._redeye_current.y())
        x2 = max(self._redeye_start.x(), self._redeye_current.x())
        y2 = max(self._redeye_start.y(), self._redeye_current.y())

        sx = target_rect.x() + x1 * target_rect.width()
        sy = target_rect.y() + y1 * target_rect.height()
        sw = max(4.0, (x2 - x1) * target_rect.width())
        sh = max(4.0, (y2 - y1) * target_rect.height())
        box = QRectF(sx, sy, sw, sh)

        painter.setBrush(QColor(255, 50, 50, 40))
        painter.setPen(QPen(QColor(255, 80, 80, 240), 1.5, Qt.PenStyle.DashLine))
        painter.drawRect(box)

        painter.restore()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        FR: Gère la molette de la souris pour effectuer un zoom continu ancré sous le curseur.
        EN: Handles mouse wheel events to perform cursor-anchored continuous zooming.
        """
        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 1.18 if delta > 0 else (1.0 / 1.18)
        current_s = self.get_current_scale()
        new_zoom = current_s * factor
        self.set_zoom_anchored(new_zoom, event.position())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le clic de souris selon l'outil actif (pipette, visage, recadrage, redresser, retouche, yeux rouges, texte, Loupe ou pan).
        EN: Handles mouse press events according to the active tool (pipette, face, crop, straighten, retouch, red-eye, text, Loupe, or pan).
        """
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            target_f = QRectF(self._image_target_rect)

            # FR: Mode Pipette couleur neutre / EN: Neutral color picker mode (Ref: CDesaturateFilter::pickcolor, filter_whitept)
            if self.is_pipette_mode:
                if not target_f.isEmpty() and target_f.contains(pos) and self._display_pixmap and not self._display_pixmap.isNull():
                    nx = (pos.x() - target_f.left()) / target_f.width()
                    ny = (pos.y() - target_f.top()) / target_f.height()
                    qimg = self._display_pixmap.toImage()
                    px = int(nx * qimg.width())
                    py = int(ny * qimg.height())
                    px = max(0, min(qimg.width() - 1, px))
                    py = max(0, min(qimg.height() - 1, py))
                    col = qimg.pixelColor(px, py)
                    self.is_pipette_mode = False
                    self.setCursor(self._pan_cursor)
                    self.neutral_color_picked.emit((col.red(), col.green(), col.blue()))
                return

            # FR: Mode d'ajout manuel de visage / EN: Manual face addition mode (Ref: peoplepanel/manual_add, 0x008A0D0C)
            if self.is_manual_face_add:
                if not target_f.isEmpty() and target_f.contains(pos):
                    nx = (pos.x() - target_f.left()) / target_f.width()
                    ny = (pos.y() - target_f.top()) / target_f.height()
                    self._manual_face_start = QPointF(max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
                    self._manual_face_current = QPointF(self._manual_face_start)
                    self.update()
                return

            # FR: Outil Recadrage interactif / EN: Interactive crop tool (Ref: CSmartCrop, 0x008A786C)
            if self.is_cropping:
                handle = self._get_crop_handle_at(pos)
                if handle:
                    self._crop_drag_handle = handle
                    self._crop_drag_start_pos = pos
                    self._crop_drag_start_rect = QRectF(self.crop_rect_norm)
                    return
                elif not target_f.isEmpty() and target_f.contains(pos):
                    nx = (pos.x() - target_f.left()) / target_f.width()
                    ny = (pos.y() - target_f.top()) / target_f.height()
                    self.crop_rect_norm = QRectF(max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)), 0.01, 0.01)
                    self._crop_drag_handle = "br"
                    self._crop_drag_start_pos = pos
                    self._crop_drag_start_rect = QRectF(self.crop_rect_norm)
                    self.update()
                    return
                return

            # FR: Outil Redresser / EN: Straighten tool (Ref: filter_tilt, 0x008814AC)
            if self.is_straightening:
                if not target_f.isEmpty() and target_f.contains(pos):
                    self._straighten_drag_start = pos
                    self._straighten_drag_start_angle = self.straighten_angle
                return

            # FR: Outil Retouche / EN: Retouch tool (Healing Puck, Ref: filterdesc.xml @ retouch, 0x0088C3EC)
            if self.is_retouching:
                if not target_f.isEmpty() and target_f.contains(pos):
                    nx = (pos.x() - target_f.left()) / target_f.width()
                    ny = (pos.y() - target_f.top()) / target_f.height()
                    self.retouch_applied.emit(nx, ny, self.retouch_radius)
                return

            # FR: Outil Yeux Rouges / EN: Red-Eye tool (Ref: filterdesc.xml @ redeye, 0x005E7CD7)
            if self.is_redeye:
                if not target_f.isEmpty() and target_f.contains(pos):
                    nx = (pos.x() - target_f.left()) / target_f.width()
                    ny = (pos.y() - target_f.top()) / target_f.height()
                    self._redeye_start = QPointF(nx, ny)
                    self._redeye_current = QPointF(nx, ny)
                    self.update()
                return

            # FR: Interaction avec l'outil Texte / EN: Text tool interaction (Ref: editpanel/textringnode)
            if self.is_text_tool_active:
                if not self._text_screen_rect.isEmpty() and self._text_screen_rect.contains(pos):
                    self._is_dragging_text = True
                    self._text_drag_start_pos = pos
                    return
                elif not target_f.isEmpty() and target_f.contains(pos):
                    nx = (pos.x() - target_f.left()) / target_f.width()
                    ny = (pos.y() - target_f.top()) / target_f.height()
                    self.text_pos_norm = QPointF(max(0.05, min(0.95, nx)), max(0.05, min(0.95, ny)))
                    self._is_dragging_text = True
                    self._text_drag_start_pos = pos
                    self.update()
                    return
                return

            # FR: Clic sur une balise de visage existante / EN: Click on an existing face tag (Ref: peoplepanel/face_click, 0x008A1034)
            if self.show_face_tags and self.face_rects and not target_f.isEmpty():
                aspect = 1.0
                if self._display_pixmap and not self._display_pixmap.isNull() and self._display_pixmap.height() > 0:
                    aspect = self._display_pixmap.width() / float(self._display_pixmap.height())
                for i, fr in enumerate(self.face_rects):
                    disp_fr = fr.transform_to_display(
                        crop_rect=self._active_crop_rect,
                        rotation=self._active_rotation_steps,
                        tilt_angle=self._active_tilt_angle,
                        aspect_ratio=aspect
                    )
                    if disp_fr is None:
                        continue
                    fx = target_f.x() + disp_fr.left * target_f.width()
                    fy = target_f.y() + disp_fr.top * target_f.height()
                    fw = disp_fr.width * target_f.width()
                    fh = disp_fr.height * target_f.height()
                    face_box = QRectF(fx, fy, fw, fh)
                    badge_rect = QRectF(fx - 10, fy + fh, fw + 20, 26)
                    if face_box.contains(pos) or badge_rect.contains(pos):
                        self.face_clicked.emit(fr, i)
                        return

            # 1. FR: Sélection de volet en mode comparaison A|B ou A|A / EN: Pane selection in A|B or A|A comparison mode
            if self.view_mode in ("A_B", "A_A"):
                if self.split_orientation == "vertical":
                    half_h = (self.height() - 2.0) / 2.0
                    new_pane = "A" if pos.y() < half_h else "B"
                else:
                    half_w = (self.width() - 2.0) / 2.0
                    new_pane = "A" if pos.x() < half_w else "B"
                if self.active_pane != new_pane:
                    self.active_pane = new_pane
                    self.active_pane_changed.emit(new_pane)
                    self.update()

            # 2. FR: Interaction avec la Loupe si active (clic sur la croix [×] ou sur la miniature)
            # EN: Loupe navigator interaction if active (click on close [×] button or thumbnail)
            # Ref: picasa3.exe @ PanHandler (0x005C46B0 -> 0x00597D10), nav/nav (0x0056B338)
            if self.is_zoomed_in() and self.show_loupe_navigator and self._nav_card_rect.contains(pos):
                if not self._nav_close_rect.isEmpty() and self._nav_close_rect.contains(pos):
                    self._is_hovering_nav_close = False
                    self._is_dragging_nav_box = False
                    self.reset_zoom_to_fit()
                    return
                if self._nav_img_rect.contains(pos):
                    if self._vbox_rect.contains(pos):
                        self._is_dragging_nav_box = True
                        self._last_nav_drag_pos = pos
                    else:
                        self._center_on_nav_point(pos)
                        self._is_dragging_nav_box = True
                        self._last_nav_drag_pos = pos
                return

            # 3. FR: Panoramique sur le canvas (uniquement si aucun outil n'est actif) / EN: Canvas panning (only when no tool is active)
            self._is_dragging = True
            self._last_mouse_pos = event.pos()
            self.setCursor(self._pan_closed_cursor)

    def _center_on_nav_point(self, click_pos: QPointF) -> None:
        """
        FR: Recentre la vue principale sur le point cliqué dans la miniature de la Loupe.
        EN: Recenters the main view on the point clicked inside the Loupe thumbnail.
        """
        pix = self._get_active_pane_pixmap()
        if self._nav_img_rect.isEmpty() or pix is None or pix.isNull():
            return
        u = (click_pos.x() - self._nav_img_rect.x()) / self._nav_img_rect.width()
        v = (click_pos.y() - self._nav_img_rect.y()) / self._nav_img_rect.height()
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))

        scale = self.get_current_scale()
        draw_w = pix.width() * scale
        draw_h = pix.height() * scale

        self.pan_offset = QPointF(draw_w * (0.5 - u), draw_h * (0.5 - v))
        self._clamp_pan_offset()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le déplacement de la souris (tracé d'outil interactif, survol de poignées/visages, ou déplacement panoramique).
        EN: Handles mouse move events (interactive tool dragging, handle/face hovering, or canvas panning).
        """
        pos = event.position()

        # FR: Mode d'ajout manuel de visage / EN: Manual face addition mode (Ref: peoplepanel/manual_frame, 0x00898ADC)
        if self.is_manual_face_add:
            target_f = QRectF(self._image_target_rect)
            if self._manual_face_start and not target_f.isEmpty():
                nx = (pos.x() - target_f.left()) / target_f.width()
                ny = (pos.y() - target_f.top()) / target_f.height()
                self._manual_face_current = QPointF(max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
                self.update()
            return

        # 0. FR: Recadrage interactif (déplacement poignée ou survol poignées) / EN: Interactive crop (handle drag or hover)
        if self.is_cropping:
            if self._crop_drag_handle:
                self._handle_crop_drag(pos)
                self.update()
                return
            else:
                handle = self._get_crop_handle_at(pos)
                if handle in ("tl", "br"):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif handle in ("tr", "bl"):
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif handle in ("tm", "bm"):
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif handle in ("ml", "mr"):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif handle == "inside":
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.setCursor(self._crop_cursor)
                return

        # FR: Outil Redresser interactif / EN: Interactive Straighten tool (Ref: filter_tilt, 0x008814AC)
        if self.is_straightening:
            if self._straighten_drag_start:
                dx = pos.x() - self._straighten_drag_start.x()
                new_angle = max(-45.0, min(45.0, self._straighten_drag_start_angle + dx * 0.1))
                self.straighten_angle = round(new_angle, 1)
                self.straighten_interactive_angle_changed.emit(self.straighten_angle)
                self.update()
            else:
                self.setCursor(self._tilt_cursor)
            return

        # FR: Outil Retouche / EN: Retouch tool (Healing puck, Ref: retouch, 0x0088C3EC)
        if self.is_retouching:
            self._retouch_hover_pos = pos
            self.setCursor(self._retouch_cursor)
            self.update()
            return

        # FR: Outil Yeux Rouges / EN: Red-Eye tool (Ref: redeye)
        if self.is_redeye:
            if self._redeye_start and not self._image_target_rect.isEmpty():
                nx = (pos.x() - self._image_target_rect.left()) / self._image_target_rect.width()
                ny = (pos.y() - self._image_target_rect.top()) / self._image_target_rect.height()
                self._redeye_current = QPointF(max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
                self.update()
            else:
                self.setCursor(self._redeye_cursor)
            return

        # FR: Interaction avec l'outil Texte / EN: Text tool interaction (Ref: editpanel/textgroupnode)
        if self.is_text_tool_active:
            if self._is_dragging_text and not self._image_target_rect.isEmpty():
                dx = (pos.x() - self._text_drag_start_pos.x()) / self._image_target_rect.width()
                dy = (pos.y() - self._text_drag_start_pos.y()) / self._image_target_rect.height()
                self._text_drag_start_pos = pos
                nx = max(0.05, min(0.95, self.text_pos_norm.x() + dx))
                ny = max(0.05, min(0.95, self.text_pos_norm.y() + dy))
                self.text_pos_norm = QPointF(nx, ny)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                self.update()
                return
            elif not self._text_screen_rect.isEmpty() and self._text_screen_rect.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
            elif not self._image_target_rect.isEmpty() and self._image_target_rect.contains(pos):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                return

        # 1. FR: Déplacement du cadre de cadrage dans la Loupe / EN: Dragging the viewfinder box inside the Loupe
        if self._is_dragging_nav_box:
            delta = pos - self._last_nav_drag_pos
            self._last_nav_drag_pos = pos

            pix = self._get_active_pane_pixmap()
            if not self._nav_img_rect.isEmpty() and pix is not None and not pix.isNull():
                scale = self.get_current_scale()
                draw_w = pix.width() * scale
                draw_h = pix.height() * scale

                ratio_x = draw_w / self._nav_img_rect.width()
                ratio_y = draw_h / self._nav_img_rect.height()

                self.pan_offset = QPointF(
                    self.pan_offset.x() - delta.x() * ratio_x,
                    self.pan_offset.y() - delta.y() * ratio_y
                )
                self._clamp_pan_offset()
                self.update()
            return

        # 2. FR: Déplacement panoramique (Pan) de la photo / EN: Panning the photo
        if self._is_dragging:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.pan_offset += QPointF(delta.x(), delta.y())
            self.fit_to_window = False
            self._clamp_pan_offset()
            self.update()
            return

        # 3. FR: Adaptation du curseur de survol et état de la croix [×] / EN: Hover cursor adaptation and close [×] state
        # Ref: picasa3.exe @ PanHandler (0x005C47F0)
        prev_hover_close = self._is_hovering_nav_close
        if self.is_zoomed_in() and self.show_loupe_navigator and self._nav_card_rect.contains(pos):
            self._is_hovering_nav_close = (
                not self._nav_close_rect.isEmpty() and self._nav_close_rect.contains(pos)
            )
            if self._is_hovering_nav_close:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif self._vbox_rect.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._is_hovering_nav_close = False
            self.setCursor(self._pan_cursor)
        if self._is_hovering_nav_close != prev_hover_close:
            self.update()

        # 4. FR: Survol des balises de visages / EN: Hovering over face tags
        if self.show_face_tags and self.face_rects and self._display_pixmap:
            scale = self.get_current_scale()
            draw_w = self._display_pixmap.width() * scale
            draw_h = self._display_pixmap.height() * scale
            cx = (self.width() - draw_w) / 2.0 + self.pan_offset.x()
            cy = (self.height() - draw_h) / 2.0 + self.pan_offset.y()
            t_rect = QRectF(cx, cy, draw_w, draw_h)

            prev_hovered = self.hovered_face_idx
            self.hovered_face_idx = -1
            aspect = (draw_w / draw_h) if draw_h > 0 else 1.0
            for i, fr in enumerate(self.face_rects):
                disp_fr = fr.transform_to_display(
                    crop_rect=self._active_crop_rect,
                    rotation=self._active_rotation_steps,
                    tilt_angle=self._active_tilt_angle,
                    aspect_ratio=aspect
                )
                if disp_fr is None:
                    continue
                fx = t_rect.x() + disp_fr.left * t_rect.width()
                fy = t_rect.y() + disp_fr.top * t_rect.height()
                fw = disp_fr.width * t_rect.width()
                fh = disp_fr.height * t_rect.height()
                if QRectF(fx, fy, fw, fh).contains(pos):
                    self.hovered_face_idx = i
                    break
            if prev_hovered != self.hovered_face_idx:
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        FR: Finalise l'action de glisser-déposer ou de sélection d'outil au relâchement du bouton gauche.
        EN: Finalizes drag-and-drop or tool selection upon releasing the left mouse button.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # FR: Finalisation du tracé manuel de visage / EN: Finalize manual face rectangle drawing (Ref: peoplepanel/manual_add)
            if self.is_manual_face_add:
                target_f = QRectF(self._image_target_rect)
                if self._manual_face_start and not target_f.isEmpty():
                    pos = event.position()
                    nx = (pos.x() - target_f.left()) / target_f.width()
                    ny = (pos.y() - target_f.top()) / target_f.height()
                    self._manual_face_current = QPointF(max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))

                if self._manual_face_start and self._manual_face_current:
                    x1 = min(self._manual_face_start.x(), self._manual_face_current.x())
                    y1 = min(self._manual_face_start.y(), self._manual_face_current.y())
                    x2 = max(self._manual_face_start.x(), self._manual_face_current.x())
                    y2 = max(self._manual_face_start.y(), self._manual_face_current.y())
                    w = x2 - x1
                    h = y2 - y1
                    if w >= 0.01 and h >= 0.01:
                        disp_fr = FaceRect(left=x1, top=y1, right=x2, bottom=y2)
                        aspect = 1.0
                        if self._display_pixmap and not self._display_pixmap.isNull() and self._display_pixmap.height() > 0:
                            aspect = self._display_pixmap.width() / float(self._display_pixmap.height())
                        # FR: Transformation inverse vers les coordonnées de la photo originale / EN: Inverse transform to original photo coordinates
                        orig_fr = disp_fr.transform_from_display(
                            crop_rect=self._active_crop_rect,
                            rotation=self._active_rotation_steps,
                            tilt_angle=self._active_tilt_angle,
                            aspect_ratio=aspect
                        )
                        self.is_manual_face_add = False
                        self._manual_face_start = None
                        self._manual_face_current = None
                        self.setCursor(self._pan_cursor)
                        self.update()
                        self.manual_face_defined.emit(orig_fr)
                        return
                self._manual_face_start = None
                self._manual_face_current = None
                self.update()
                return

            if self.is_cropping and self._crop_drag_handle:
                self._crop_drag_handle = None
                return

            if self.is_straightening:
                self._straighten_drag_start = None
                return

            if self.is_redeye:
                if self._redeye_start and self._redeye_current:
                    dx = abs(self._redeye_current.x() - self._redeye_start.x())
                    dy = abs(self._redeye_current.y() - self._redeye_start.y())
                    if dx < 0.01 and dy < 0.01:
                        self.redeye_applied.emit(self._redeye_start.x(), self._redeye_start.y())
                    else:
                        rx = min(self._redeye_start.x(), self._redeye_current.x())
                        ry = min(self._redeye_start.y(), self._redeye_current.y())
                        rw = max(0.01, dx)
                        rh = max(0.01, dy)
                        self.redeye_box_applied.emit(QRectF(rx, ry, rw, rh))
                self._redeye_start = None
                self._redeye_current = None
                self.update()
                return

            if self.is_retouching:
                return

            if self.is_text_tool_active and self._is_dragging_text:
                self._is_dragging_text = False
                return

            self._is_dragging = False
            self._is_dragging_nav_box = False
            self.setCursor(self._pan_cursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        FR: Bascule entre l'ajustement à la fenêtre et un zoom ciblé au double-clic gauche.
        EN: Toggles between fit-to-window and anchored zoom-in on left double-click.
        """
        if self.is_any_tool_active():
            return
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            if self.fit_to_window:
                fit_scale = self._get_fit_scale()
                target_zoom = 1.0 if fit_scale < 0.8 else max(1.5, fit_scale * 2.0)
                self.set_zoom_anchored(target_zoom, pos)
            else:
                self.reset_zoom_to_fit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        FR: Recalcule et contraint le décalage panoramique lors du redimensionnement du widget.
        EN: Recomputes and clamps the pan offset when the canvas widget is resized.
        """
        super().resizeEvent(event)
        if self.fit_to_window:
            self.zoom_level = self._get_fit_scale()
            self.zoom_changed.emit(self.zoom_level)
        self._clamp_pan_offset()

    def keyPressEvent(self, event) -> None:
        """
        FR: Gère la touche Échap pour annuler un outil interactif actif, ou propage les touches de navigation au parent.
        EN: Handles the Escape key to cancel an active interactive tool, or propagates navigation keys to the parent.
        """
        if event.key() == Qt.Key.Key_Escape:
            if self.is_manual_face_add:
                self.cancel_manual_face_add()
                event.accept()
                return
            if self.is_cropping:
                self.cancel_crop()
                event.accept()
                return
            if self.is_straightening:
                self.cancel_straighten()
                event.accept()
                return
            if self.is_retouching:
                self.cancel_retouch()
                event.accept()
                return
            if self.is_redeye:
                self.cancel_redeye()
                event.accept()
                return
            if self.is_text_tool_active:
                self.cancel_text_tool()
                event.accept()
                return
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        FR: Gère le clic droit sur le canevas en mode One-Up / Two-Up (annule l'outil actif ou ouvre le menu contextuel).
        EN: Handles right-click on the canvas in One-Up / Two-Up mode (cancels active tool or opens the context menu).
        Ref: picasa3.exe @ TrackPopupMenu (0x005E7CD7), lb_rightclick (0x005D41F4)
        """
        if self.is_any_tool_active():
            if self.is_manual_face_add:
                self.cancel_manual_face_add()
            elif self.is_cropping:
                self.cancel_crop()
            elif self.is_straightening:
                self.cancel_straighten()
            elif self.is_retouching:
                self.cancel_retouch()
            elif self.is_redeye:
                self.cancel_redeye()
            elif self.is_text_tool_active:
                self.cancel_text_tool()
            event.accept()
            return
        self.context_menu_requested.emit(event.globalPos())
        event.accept()

