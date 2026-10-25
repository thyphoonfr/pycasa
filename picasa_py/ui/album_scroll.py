"""
FR: Composant de barre de défilement à rappel central par vitesse (AVCScrollThrottle / AVAlbumScroll).
Reproduit fidèlement la barre de défilement temporelle emblématique de Picasa 3 :
- Curseur de commande au repos au centre vertical de la piste.
- Glisser vers le HAUT remonte dans le temps ; glisser vers le BAS avance dans le temps.
- La vitesse augmente de manière non linéaire avec la distance au centre (contrôle fin près du centre, balayage rapide aux extrémités).
- Rappel par ressort : au relâchement de la souris, le curseur revient au cran central.
- Badge flottant de date et d'album (PicasaScrollTooltip) suivant le curseur.
- Indicateur de tension directionnel reliant le cran central au curseur.
- Boutons de pas (throttle/albumscrolltop, throttle/albumscrollbottom).
- Boutons de saut d'album (throttle/prevalbum, throttle/nextalbum).

EN: Custom Album Scroll Throttle Component for PyCasa (AVCScrollThrottle / AVAlbumScroll).
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
    FR: Badge flottant chronologique affichant l'Album et la Date en regard du curseur throttle.
    EN: Floating timeline badge displaying the Album and Date beside the throttle handle.
    Ref: picasa3.exe @ 0x005DE8E0 (AVytToolTip indicator)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le badge flottant transparent aux événements souris.
        EN: Initializes the floating badge transparent to mouse events.
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

        self.title_text: str = ""
        self.subtitle_text: str = ""
        self.pointer_size: int = 6

    def set_content(self, title: str, subtitle: str) -> None:
        """
        FR: Définit le titre (album/dossier) et le sous-titre (date/décompte) du badge et redessine.
        EN: Sets the badge title (album/folder) and subtitle (date/count) and triggers a repaint.
        """
        self.title_text = title
        self.subtitle_text = subtitle
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine le badge flottant arrondi avec son pointeur triangulaire et ses textes.
        EN: Paints the rounded floating badge with its triangular pointer and text labels.
        """
        if not self.title_text and not self.subtitle_text:
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w = self.width() - self.pointer_size - 1
            h = self.height() - 2

            # FR: 1. Tracé du corps arrondi avec pointeur triangulaire à droite vers le curseur
            # EN: 1. Rounded body path with right-side triangular pointer toward the handle
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

            # FR: 2. Fond semi-transparent sombre et liseré
            # EN: 2. Dark semi-transparent background and border outline
            painter.fillPath(path, QColor(24, 26, 30, 238))
            painter.setPen(QPen(QColor(85, 91, 102, 220), 1))
            painter.drawPath(path)

            # FR: 3. Titre de l'album / dossier en cours
            # EN: 3. Current album / folder title
            painter.setFont(QFont("Tahoma", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            title_rect = QRect(10, 6, w - 16, 16)
            elided_title = painter.fontMetrics().elidedText(self.title_text, Qt.TextElideMode.ElideRight, w - 16)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_title)

            # FR: 4. Date et décompte de photos
            # EN: 4. Date and photo count subtitle
            painter.setFont(QFont("Tahoma", 8))
            painter.setPen(QColor("#9CA3AF"))
            sub_rect = QRect(10, 22, w - 16, 14)
            elided_sub = painter.fontMetrics().elidedText(self.subtitle_text, Qt.TextElideMode.ElideRight, w - 16)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_sub)
        finally:
            painter.end()


class PicasaAlbumScroll(QWidget):
    """
    FR: Système de défilement par manette des gaz / jog-shuttle (AVCScrollThrottle).
    Le curseur reste centré au repos. Glisser vers le haut/bas fait défiler le contenu
    à une vitesse proportionnelle à l'écartement. Au relâchement, le curseur revient au centre.
    EN: Spring-loaded center throttle / jog-shuttle scrollbar (AVCScrollThrottle).
    The handle rests at the center; dragging up/down scrolls at a speed proportional
    to the displacement and snaps back to center on release.
    """
    value_changed = Signal(int)
    jump_prev_album = Signal()
    jump_next_album = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise la barre de défilement throttle, ses dimensions, minuteries et badge flottant.
        EN: Initializes the throttle scrollbar, its dimensions, timers, and floating tooltip badge.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.setMouseTracking(True)
        self.setFixedWidth(20)

        # FR: Plage de défilement du contenu / EN: Content scroll range
        self.min_val: int = 0
        self.max_val: int = 0
        self.cur_val: float = 0.0
        self.page_step: int = 100

        # FR: Boutons de navigation (haut et bas) / EN: Navigation buttons (top and bottom)
        self.btn_size: int = 16
        self.album_btn_size: int = 14

        # FR: Dimensions du curseur throttle (capsule) / EN: Throttle handle (capsule) dimensions
        self.thumb_width: int = 14
        self.thumb_height: int = 28

        # FR: Position verticale actuelle du curseur (en pixels) / EN: Current vertical handle position (in pixels)
        self._thumb_y: float = 0.0

        # FR: États interactifs / EN: Interactive states
        self._hover_thumb: bool = False
        self._is_throttling: bool = False
        self._throttle_speed: float = 0.0  # FR: pixels par seconde / EN: pixels per second
        self._last_tick_time: float = 0.0

        # FR: Callback externe pour obtenir les métadonnées (album, date) pour un scroll_y donné
        # EN: External callback providing metadata (album, date) for a given scroll_y
        self.info_provider: Optional[Callable[[int], Tuple[str, str]]] = None

        # FR: Badge flottant (géré sur le parent) / EN: Floating badge (managed on the parent widget)
        self.tooltip = PicasaScrollTooltip(self.parentWidget())

        # FR: Timer de défilement continu pendant le throttle (60 FPS / 16ms)
        # EN: Continuous scroll timer during active throttling (60 FPS / 16ms)
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setInterval(16)
        self._throttle_timer.timeout.connect(self._on_throttle_tick)

        # FR: Timer d'animation de retour élastique (spring-back) vers le centre
        # EN: Spring-back animation timer returning the handle to the center
        self._spring_timer = QTimer(self)
        self._spring_timer.setInterval(16)
        self._spring_timer.timeout.connect(self._on_spring_tick)

        # FR: Timer pour masquer le badge après inactivité
        # EN: Single-shot timer to hide the tooltip badge after inactivity
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(700)
        self._hide_timer.timeout.connect(self._on_hide_tooltip)

    # -------------------------------------------------------------------------
    # FR: Géométrie & Repères / EN: Geometry & Landmarks
    # -------------------------------------------------------------------------
    @property
    def track_top(self) -> int:
        """
        FR: Ordonnée supérieure de la piste de déplacement du curseur.
        EN: Top Y coordinate of the throttle handle track.
        """
        return self.btn_size + self.album_btn_size + 4

    @property
    def track_bottom(self) -> int:
        """
        FR: Ordonnée inférieure de la piste de déplacement du curseur.
        EN: Bottom Y coordinate of the throttle handle track.
        """
        return self.height() - (self.btn_size + self.album_btn_size + 4)

    @property
    def track_height(self) -> int:
        """
        FR: Hauteur utile de la piste de défilement.
        EN: Usable height of the scroll track.
        """
        return max(40, self.track_bottom - self.track_top)

    @property
    def center_y(self) -> int:
        """
        FR: Position Y du point mort central (neutre).
        EN: Y coordinate of the central neutral dead-zone notch.
        """
        return self.track_top + self.track_height // 2

    @property
    def rest_thumb_y(self) -> float:
        """
        FR: Position Y du curseur au repos (centré).
        EN: Y coordinate of the handle at rest (centered).
        """
        return float(self.center_y - self.thumb_height // 2)

    @property
    def max_deflection(self) -> float:
        """
        FR: Déviation maximale du curseur vers le haut ou vers le bas.
        EN: Maximum deflection of the handle upward or downward from center.
        """
        return max(20.0, (self.track_height / 2.0) - (self.thumb_height / 2.0) - 2.0)

    def _get_thumb_rect(self) -> QRect:
        """
        FR: Calcule le rectangle géométrique actuel de la capsule du curseur.
        EN: Computes the current bounding rectangle of the throttle handle capsule.
        """
        x = (self.width() - self.thumb_width) // 2
        if self._is_throttling or self._spring_timer.isActive():
            y = int(self._thumb_y)
        else:
            y = int(self.rest_thumb_y)
        return QRect(x, y, self.thumb_width, self.thumb_height)

    # -------------------------------------------------------------------------
    # FR: API Publique / EN: Public API
    # -------------------------------------------------------------------------
    def set_range(self, min_val: int, max_val: int, page_step: int = 100) -> None:
        """
        FR: Définit les bornes minimale et maximale ainsi que le pas de page du défilement.
        EN: Sets the minimum and maximum scroll bounds and page step size.
        """
        self.min_val = min_val
        self.max_val = max(min_val, max_val)
        self.page_step = max(1, page_step)
        self.cur_val = max(float(self.min_val), min(float(self.max_val), self.cur_val))
        if not self._is_throttling and not self._spring_timer.isActive():
            self._thumb_y = self.rest_thumb_y
        self.update()

    def set_value(self, val: int) -> None:
        """
        FR: Met à jour la position actuelle du défilement en la bornant à l'intervalle valide.
        EN: Updates the current scroll position clamped within the valid range.
        """
        clamped = max(float(self.min_val), min(float(self.max_val), float(val)))
        if clamped != self.cur_val:
            self.cur_val = clamped
            self.update()

    def value(self) -> int:
        """
        FR: Renvoie la valeur entière actuelle du défilement.
        EN: Returns the current integer scroll value.
        """
        return int(self.cur_val)

    def set_info_provider(self, provider: Callable[[int], Tuple[str, str]]) -> None:
        """
        FR: Enregistre la fonction de rappel fournissant le titre et la date pour une position donnée.
        EN: Registers the callback function providing the title and date for a given scroll position.
        """
        self.info_provider = provider

    # -------------------------------------------------------------------------
    # FR: Physique du Throttle & Animation Ressort (AVCScrollThrottle)
    # EN: Throttle Physics & Spring-Back Animation (AVCScrollThrottle)
    # -------------------------------------------------------------------------
    def _update_throttle_from_mouse_y(self, mouse_y: float) -> None:
        """
        FR: Calcule la déviation du curseur par rapport au centre et la vitesse associée.
        EN: Computes the handle deflection from the center and the corresponding scroll speed.
        Ref: picasa3.exe @ 0x0072E330, 0x005CE090
        """
        self._is_throttling = True
        raw_delta = mouse_y - float(self.center_y)
        max_d = self.max_deflection

        # FR: Déviation bornée / EN: Clamped deflection
        clamped_d = max(-max_d, min(max_d, raw_delta))
        self._thumb_y = float(self.center_y) + clamped_d - (self.thumb_height / 2.0)

        # FR: Zone morte centrale (3 pixels) pour éviter toute dérive au point mort
        # EN: Central dead zone (3 pixels) to prevent drift at neutral position
        dead_zone = 3.0
        abs_d = abs(clamped_d)
        if abs_d <= dead_zone:
            self._throttle_speed = 0.0
        else:
            # FR: Facteur normalisé entre 0.0 et 1.0 / EN: Normalized factor between 0.0 and 1.0
            u = (abs_d - dead_zone) / (max_d - dead_zone)
            direction = 1.0 if clamped_d > 0 else -1.0

            # FR: Courbe de vitesse progressive non-linéaire : vitesse douce au départ, accélération rapide en bout de course
            # EN: Non-linear progressive speed curve: gentle speed near center, rapid acceleration at extremes
            base_v = u * 120.0             # FR: Contrôle fin / EN: Fine control
            quad_v = (u ** 2) * 600.0      # FR: Balayage fluide / EN: Smooth scrubbing
            cubic_v = (u ** 3) * 2200.0    # FR: Défilement ultra-rapide / EN: Ultra-fast scrolling
            self._throttle_speed = direction * (base_v + quad_v + cubic_v)

        self._update_tooltip_position()
        self.update()

    def _on_throttle_tick(self) -> None:
        """
        FR: Horloge 60 FPS du défilement continu proportionnel.
        EN: 60 FPS timer tick for continuous proportional scrolling.
        """
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
        """
        FR: Animation de retour élastique vers le centre au relâchement de la souris.
        EN: Spring-back animation returning the handle to the center upon mouse release.
        """
        target_y = self.rest_thumb_y
        diff = target_y - self._thumb_y

        if abs(diff) < 0.8:
            self._thumb_y = target_y
            self._spring_timer.stop()
        else:
            # FR: Interpolation élastique progressive (facteur 0.30)
            # EN: Progressive elastic interpolation (0.30 damping factor)
            self._thumb_y += diff * 0.30

        self.update()

    # -------------------------------------------------------------------------
    # FR: Gestion du Badge Flottant Chronologique / EN: Floating Timeline Badge Management
    # -------------------------------------------------------------------------
    def _show_tooltip_for_val(self, val: int, thumb_center_y: int) -> None:
        """
        FR: Positionne et affiche le badge flottant en regard du curseur pour la valeur donnée.
        EN: Positions and displays the floating tooltip badge beside the handle for the given scroll value.
        """
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
        """
        FR: Met à jour la position et le contenu du badge flottant si le curseur est actif ou survolé.
        EN: Updates the floating tooltip position and content when the handle is active or hovered.
        """
        if self._is_throttling or self._hover_thumb:
            thumb_r = self._get_thumb_rect()
            self._show_tooltip_for_val(int(self.cur_val), thumb_r.center().y())

    def _on_hide_tooltip(self) -> None:
        """
        FR: Masque le badge flottant lorsque le défilement throttle est terminé.
        EN: Hides the floating tooltip badge when throttling is inactive.
        """
        if not self._is_throttling:
            self.tooltip.hide()

    # -------------------------------------------------------------------------
    # FR: Événements Souris / EN: Mouse Events
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le clic gauche sur les boutons de pas, de saut d'album ou sur la piste throttle.
        EN: Handles left mouse clicks on step buttons, album jump buttons, or the throttle track.
        """
        if event.button() != Qt.MouseButton.LeftButton:
            return

        y = event.position().y()

        # FR: 1. Bouton Haut (step up) / EN: 1. Top button (step up)
        if y < self.btn_size:
            self.set_value(int(self.cur_val) - 60)
            self.value_changed.emit(int(self.cur_val))
            return

        # FR: 2. Bouton Saut Album Précédent (prevalbum) / EN: 2. Previous Album Jump button (prevalbum)
        if y < self.btn_size + self.album_btn_size:
            self.jump_prev_album.emit()
            return

        # FR: 3. Bouton Saut Album Suivant (nextalbum) / EN: 3. Next Album Jump button (nextalbum)
        if y > self.height() - (self.btn_size + self.album_btn_size) and y < self.height() - self.btn_size:
            self.jump_next_album.emit()
            return

        # FR: 4. Bouton Bas (step down) / EN: 4. Bottom button (step down)
        if y >= self.height() - self.btn_size:
            self.set_value(int(self.cur_val) + 60)
            self.value_changed.emit(int(self.cur_val))
            return

        # FR: 5. Zone de glisse Throttle / EN: 5. Throttle drag track area
        if self.track_top <= y <= self.track_bottom:
            self._spring_timer.stop()
            self._is_throttling = True
            self._last_tick_time = time.time()
            self._update_throttle_from_mouse_y(y)
            self._throttle_timer.start()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        FR: Met à jour le throttle pendant le glissement ou l'état de survol du curseur.
        EN: Updates throttling during mouse drag or updates the handle hover state.
        """
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
        """
        FR: Arrête le défilement au relâchement du clic gauche et lance le rappel élastique au centre.
        EN: Stops throttling on left button release and starts the spring-back return to center.
        """
        if event.button() == Qt.MouseButton.LeftButton and self._is_throttling:
            self._is_throttling = False
            self._throttle_speed = 0.0
            self._throttle_timer.stop()
            # FR: Déclencher le retour élastique au centre / EN: Trigger elastic spring-back to center
            self._spring_timer.start()
            self._hide_timer.start()
            self.update()

    def leaveEvent(self, event) -> None:
        """
        FR: Réinitialise le survol et programme le masquage du badge lorsque la souris quitte le widget.
        EN: Resets hover state and schedules tooltip hiding when the mouse leaves the widget.
        """
        super().leaveEvent(event)
        self._hover_thumb = False
        self.update()
        if not self._is_throttling:
            self._hide_timer.start()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        FR: Fait défiler la vue par pas lors de l'utilisation de la molette sur la barre.
        EN: Scrolls the view by step increments when turning the mouse wheel over the scrollbar.
        """
        delta = event.angleDelta().y()
        step = 60 if delta > 0 else -60
        self.set_value(int(self.cur_val) - step)
        self.value_changed.emit(int(self.cur_val))

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique le thème graphique PicasaStyle et redessine la barre de défilement.
        EN: Applies the PicasaStyle visual theme and repaints the scrollbar.
        """
        self.style = style
        self.update()

    # -------------------------------------------------------------------------
    # FR: Rendu Graphique (QPainter) / EN: Custom Painting (QPainter)
    # -------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine la piste, les boutons fléchés, le repère central, le ruban de tension et la capsule.
        EN: Paints the track, arrow buttons, center notch, tension ribbon, and throttle thumb capsule.
        """
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # FR: 1. Piste de défilement (thumbui/albumscroll) adaptée au thème (uni ou dégradé)
            # EN: 1. Scroll track (thumbui/albumscroll) adapted to the active theme (solid or gradient)
            track_bg = self.style.tray_bgcolor if self.style.is_dark else self.style.topbar_grad_end
            track_end = getattr(self.style, "tray_bgcolor_end", track_bg) if self.style.is_dark else track_bg
            border_col = self.style.splitter_color
            if track_bg != track_end:
                tr_grad = QLinearGradient(0.0, 0.0, 0.0, float(self.height()))
                tr_grad.setColorAt(0.0, track_bg)
                tr_grad.setColorAt(1.0, track_end)
                painter.fillRect(self.rect(), QBrush(tr_grad))
            else:
                painter.fillRect(self.rect(), track_bg)
            painter.setPen(border_col)
            painter.drawLine(0, 0, 0, self.height())

            # FR: 2. Boutons de navigation Haut / EN: 2. Top navigation buttons
            self._draw_arrow_button(painter, 0, 0, self.width(), self.btn_size, up=True, double=False)
            self._draw_arrow_button(painter, 0, self.btn_size, self.width(), self.album_btn_size, up=True, double=True)

            # FR: 3. Marque neutre centrale (Point mort de repos du throttle)
            # EN: 3. Central neutral notch (resting dead-zone mark of the throttle)
            cx = self.width() // 2
            cy = self.center_y
            painter.setPen(QPen(self.style.topbar_btn_border, 1))
            painter.drawLine(cx - 5, cy, cx + 5, cy)
            painter.setPen(QPen(border_col, 1))
            painter.drawLine(cx - 5, cy + 1, cx + 5, cy + 1)

            # FR: 4. Ruban de tension / vitesse lors de l'écartement
            # EN: 4. Tension / speed ribbon indicator during handle deflection
            thumb_r = self._get_thumb_rect()
            thumb_cy = thumb_r.center().y()
            if abs(thumb_cy - cy) > 2:
                self._draw_tension_indicator(painter, cx, cy, thumb_cy)

            # FR: 5. Curseur Throttle (Capsule avec rainures Picasa)
            # EN: 5. Throttle handle (Capsule with Picasa grip grooves)
            self._draw_throttle_thumb(painter, thumb_r)

            # FR: 6. Boutons de navigation Bas / EN: 6. Bottom navigation buttons
            next_album_y = self.height() - (self.btn_size + self.album_btn_size)
            self._draw_arrow_button(painter, 0, next_album_y, self.width(), self.album_btn_size, up=False, double=True)
            self._draw_arrow_button(painter, 0, self.height() - self.btn_size, self.width(), self.btn_size, up=False, double=False)
        finally:
            painter.end()

    def _draw_tension_indicator(self, painter: QPainter, cx: int, cy: int, thumb_cy: int) -> None:
        """
        FR: Trace le ruban indicateur reliant le centre au curseur pour matérialiser la poussée.
        EN: Draws the tension ribbon connecting the center notch to the handle to visualize thrust.
        """
        top_y = min(cy, thumb_cy)
        bottom_y = max(cy, thumb_cy)
        h = bottom_y - top_y

        glow_rect = QRect(cx - 3, top_y, 6, h)
        gradient = QLinearGradient(0, top_y, 0, bottom_y)
        if thumb_cy < cy:
            # FR: Vers le haut : défilement arrière / EN: Upward: backward scrolling
            gradient.setColorAt(0.0, QColor(62, 130, 184, 180))
            gradient.setColorAt(1.0, QColor(62, 130, 184, 40))
        else:
            # FR: Vers le bas : défilement avant / EN: Downward: forward scrolling
            gradient.setColorAt(0.0, QColor(62, 130, 184, 40))
            gradient.setColorAt(1.0, QColor(62, 130, 184, 180))

        painter.fillRect(glow_rect, gradient)

    def _draw_throttle_thumb(self, painter: QPainter, rect: QRect) -> None:
        """
        FR: Dessine la capsule du curseur throttle avec reflets et rainures.
        EN: Draws the throttle handle capsule with metallic highlights and grip grooves.
        """
        painter.save()
        radius = 5.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # FR: Dégradé métallique ou thème selon l'état / EN: State-dependent metallic or theme gradient
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        btn_s = self.style.topbar_btn_bg_start
        btn_e = self.style.topbar_btn_bg_end
        acc = getattr(self.style, "accent_color", QColor("#6B7382"))
        if self._is_throttling:
            gradient.setColorAt(0.0, btn_s.lighter(130))
            gradient.setColorAt(0.5, btn_s.lighter(115))
            gradient.setColorAt(1.0, btn_e.lighter(115))
            border_color = acc.lighter(120)
        elif self._hover_thumb:
            gradient.setColorAt(0.0, btn_s.lighter(115))
            gradient.setColorAt(0.5, btn_s)
            gradient.setColorAt(1.0, btn_e)
            border_color = acc
        else:
            gradient.setColorAt(0.0, btn_s)
            gradient.setColorAt(0.5, btn_e)
            gradient.setColorAt(1.0, btn_e.darker(110))
            border_color = self.style.topbar_btn_border

        painter.fillPath(path, gradient)
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

        # FR: Rainures centrales de préhension (3 stries caractéristiques de Picasa)
        # EN: Central grip grooves (Picasa's 3 signature ridges)
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
        """
        FR: Dessine un bouton fléché simple (pas) ou double (saut d'album) en haut ou en bas de la piste.
        EN: Draws a single (step) or double (album jump) arrow button at the top or bottom of the track.
        """
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

