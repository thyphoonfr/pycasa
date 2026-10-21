"""
FR: Widget de pellicule (Filmstrip) Picasa pour la vue One-Up et les boîtes de dialogue.
Affiche un carrousel horizontal de miniatures avec sélection active et navigation fluide.
EN: Picasa Filmstrip Widget for One-Up View & Dialogs.
Displays horizontal thumbnail carousel with active selection and smooth navigation.

Ref: picasa3.exe @ editpanel/filmstrip (0x0088E9C2), il_BigView::1 (0x0088E9A8)
Ref: picasa3.exe @ filmstripmove (0x00893584), filmstripdoubleclick (0x008941D8)
Ref: AGENTS.md §4 bis (Navigation par bande de miniatures fidèle à l'original)
"""

from __future__ import annotations
import io
from typing import List, Dict, Optional
from PIL import Image

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QImage, QWheelEvent, QMouseEvent

from picasa_py.db.database import PicasaDatabase
from picasa_py.ui.style import PicasaStyle


# Ref: picasa3.exe @ editpanel/filmstrip
class PicasaFilmstrip(QWidget):
    """
    FR: Bandeau horizontal de miniatures photos pour la navigation en vue One-Up / Plein écran.
    Permet de visualiser les photos précédentes et suivantes et de basculer d'un clic.
    EN: Horizontal photo thumbnail filmstrip for navigation in One-Up / Fullscreen view.
    Allows viewing previous and next photos and switching between them with a single click.
    """
    photo_clicked = Signal(int)  # FR: Émet l'index de la photo sélectionnée / EN: Emits the selected photo index

    def __init__(
        self,
        thumb_size: int = 42,
        spacing: int = 6,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QWidget] = None
    ):
        """
        FR: Initialise le bandeau de miniatures avec la taille, l'espacement et le style donnés.
        EN: Initializes the thumbnail filmstrip with the given thumbnail size, spacing, and style.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.thumb_size = thumb_size
        self.spacing = spacing
        self.setFixedHeight(thumb_size + 10)
        self.setMouseTracking(True)

        self.db: Optional[PicasaDatabase] = None
        self.indices: List[int] = []
        self.current_index: int = -1
        self.hovered_index: int = -1

        self.scroll_x: int = 0
        self._thumb_cache: Dict[int, QPixmap] = {}

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique dynamiquement le thème PicasaStyle et redessine la pellicule.
        EN: Dynamically applies the PicasaStyle theme and repaints the filmstrip.
        """
        self.style = style
        self.update()

    def set_items(self, db: Optional[PicasaDatabase], indices: List[int], current_index: int) -> None:
        """
        FR: Met à jour les éléments de la pellicule et l'élément actif.
        EN: Updates the filmstrip items and the currently active item.
        """
        if self.db is not db:
            self._thumb_cache.clear()
        self.db = db
        new_indices = list(indices)
        if self.indices == new_indices:
            self.set_current_index(current_index)
            return
        self.indices = new_indices
        self.current_index = current_index
        self._ensure_centered(current_index)
        self.update()

    def set_current_index(self, current_index: int) -> None:
        """
        FR: Change la photo active et centre la vue sur cette miniature.
        EN: Changes the active photo and centers the view on its thumbnail.
        """
        self.current_index = current_index
        self._ensure_centered(current_index)
        self.update()

    def invalidate_thumbnail(self, db_idx: int) -> None:
        """
        FR: Invalide la miniature mise en cache pour l'enregistrement db_idx (ainsi que sa photo parente)
        afin de forcer son rechargement depuis la base de données après l'application d'un effet.
        EN: Invalidates the cached thumbnail for record db_idx (and its parent photo)
        so it is reloaded from the database after an effect or edit is applied.
        Ref: picasa3.exe @ 0x00579680 -> 0x005A6950 (editpanel/filmstrip invalidate)
        """
        self._thumb_cache.pop(db_idx, None)
        if self.db is not None and hasattr(self.db, "is_face_record") and self.db.is_face_record(db_idx):
            p_idx = self.db.get_face_parent_photo_idx(db_idx)
            if p_idx is not None:
                self._thumb_cache.pop(p_idx, None)
        self.update()

    def clear_cache(self) -> None:
        """
        FR: Vide intégralement le cache mémoire des miniatures de la pellicule.
        EN: Clears the entire in-memory thumbnail cache of the filmstrip.
        """
        self._thumb_cache.clear()
        self.update()

    def _get_item_width(self) -> int:
        """
        FR: Renvoie la largeur totale occupée par un élément (miniature + espacement).
        EN: Returns the total width occupied by a single item (thumbnail + spacing).
        """
        return self.thumb_size + self.spacing

    def _get_total_content_width(self) -> int:
        """
        FR: Calcule la largeur totale en pixels de l'ensemble des miniatures de la pellicule.
        EN: Computes the total width in pixels of all thumbnails in the filmstrip.
        """
        if not self.indices:
            return 0
        return len(self.indices) * self._get_item_width() - self.spacing

    def _ensure_centered(self, active_index: int) -> None:
        """
        FR: Centre la miniature active dans la largeur disponible.
        EN: Centers the active thumbnail within the available widget width.
        """
        if active_index not in self.indices:
            return
        pos = self.indices.index(active_index)
        item_w = self._get_item_width()
        item_center = pos * item_w + (self.thumb_size // 2)

        target_x = item_center - (self.width() // 2)
        max_scroll = max(0, self._get_total_content_width() - self.width())
        self.scroll_x = max(0, min(max_scroll, target_x))

    def _load_pixmap(self, db_idx: int) -> Optional[QPixmap]:
        """
        FR: Charge une miniature depuis la base de données ou le cache mémoire.
        EN: Loads a thumbnail from the database or the in-memory pixmap cache.
        """
        if db_idx in self._thumb_cache:
            return self._thumb_cache[db_idx]

        if self.db is None:
            return None

        resolved_idx = db_idx
        if hasattr(self.db, "is_face_record") and self.db.is_face_record(db_idx):
            parent_idx = self.db.get_face_parent_photo_idx(db_idx)
            if parent_idx > 0:
                resolved_idx = parent_idx

        # FR: Charger la miniature 'small' ou 'medium' / EN: Load the 'small' or 'medium' thumbnail
        raw = self.db.load_thumbnail(resolved_idx, size="small")
        if not raw:
            raw = self.db.load_thumbnail(resolved_idx, size="medium")

        if not raw and hasattr(self.db, "get_media_full_path"):
            try:
                full_path = self.db.get_media_full_path(resolved_idx)
                if full_path:
                    from picasa_py.ui.image_processor import PicasaImageProcessor
                    pil_fallback = PicasaImageProcessor.load_transformed_image(full_path, max_size=144)
                    if pil_fallback is not None:
                        if hasattr(self.db, "update_thumbnails_from_pil"):
                            self.db.update_thumbnails_from_pil(resolved_idx, pil_fallback, persist_to_disk=False)
                        raw = self.db.load_thumbnail(resolved_idx, size="small")
            except Exception:
                pass

        pix: Optional[QPixmap] = None
        if raw:
            try:
                with Image.open(io.BytesIO(raw)) as img:
                    if img.mode in ("P", "PA") or "transparency" in img.info:
                        img = img.convert("RGBA")
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGB")
                    # FR: Redimensionner en carré centré / EN: Center-crop and resize to square
                    w, h = img.size
                    side = min(w, h)
                    left = (w - side) // 2
                    top = (h - side) // 2
                    cropped = img.crop((left, top, left + side, top + side))
                    cropped = cropped.resize((self.thumb_size, self.thumb_size), Image.Resampling.BILINEAR)

                    if cropped.mode == "RGBA":
                        bgra_data = cropped.tobytes("raw", "BGRA")
                        qimg = QImage(bgra_data, self.thumb_size, self.thumb_size, self.thumb_size * 4, QImage.Format.Format_ARGB32).copy()
                    else:
                        rgb_data = cropped.tobytes("raw", "RGB")
                        qimg = QImage(rgb_data, self.thumb_size, self.thumb_size, self.thumb_size * 3, QImage.Format.Format_RGB888).copy()
                    pix = QPixmap.fromImage(qimg)
            except Exception:
                pass

        if pix:
            self._thumb_cache[db_idx] = pix
        return pix

    def resizeEvent(self, event) -> None:
        """
        FR: Recentre la miniature active lors du redimensionnement du bandeau.
        EN: Re-centers the active thumbnail when the filmstrip widget is resized.
        """
        super().resizeEvent(event)
        self._ensure_centered(self.current_index)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        FR: Fait défiler horizontalement la pellicule lors d'un mouvement de molette souris.
        EN: Horizontally scrolls the filmstrip upon mouse wheel rotation.
        """
        delta = event.angleDelta().y() or event.angleDelta().x()
        step = 40 if delta > 0 else -40
        max_scroll = max(0, self._get_total_content_width() - self.width())
        self.scroll_x = max(0, min(max_scroll, self.scroll_x - step))
        self.update()

    def _get_item_rect(self, pos: int) -> QRect:
        """
        FR: Renvoie le rectangle d'affichage de la miniature à la position séquentielle pos.
        EN: Returns the bounding rectangle of the thumbnail at sequential position pos.
        """
        x = pos * self._get_item_width() - self.scroll_x
        y = (self.height() - self.thumb_size) // 2
        return QRect(x, y, self.thumb_size, self.thumb_size)

    def _find_item_at(self, point: QPoint) -> Optional[int]:
        """
        FR: Renvoie l'index en base de données de la miniature située au point donné, ou None.
        EN: Returns the database index of the thumbnail located at the given point, or None.
        """
        for pos, idx in enumerate(self.indices):
            r = self._get_item_rect(pos)
            if r.x() > self.width():
                break
            if r.x() + r.width() < 0:
                continue
            if r.contains(point):
                return idx
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Émet le signal photo_clicked lorsqu'une miniature est cliquée avec le bouton gauche.
        EN: Emits the photo_clicked signal when a thumbnail is left-clicked.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._find_item_at(event.position().toPoint())
            if idx is not None:
                self.photo_clicked.emit(idx)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        FR: Met à jour l'indice de la miniature survolée lors du déplacement du curseur.
        EN: Updates the hovered thumbnail index as the mouse cursor moves.
        """
        idx = self._find_item_at(event.position().toPoint())
        if idx != self.hovered_index:
            self.hovered_index = idx if idx is not None else -1
            self.update()

    def leaveEvent(self, event) -> None:
        """
        FR: Efface l'état de survol lorsque le curseur quitte la pellicule.
        EN: Clears the hover state when the mouse cursor leaves the filmstrip.
        """
        if self.hovered_index != -1:
            self.hovered_index = -1
            self.update()

    def paintEvent(self, event) -> None:
        """
        FR: Dessine l'arrière-plan de la pellicule, les miniatures visibles et les cadres de sélection/survol.
        EN: Paints the filmstrip background, visible thumbnails, and active/hover selection borders.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # FR: Fond de la bande adapté au thème actif / EN: Strip background adapted to the active theme
        painter.fillRect(self.rect(), self.style.tray_bgcolor)

        item_w = self._get_item_width()
        y = (self.height() - self.thumb_size) // 2

        for pos, idx in enumerate(self.indices):
            x = pos * item_w - self.scroll_x
            if x + self.thumb_size < 0:
                continue
            if x > self.width():
                break

            r = QRect(x, y, self.thumb_size, self.thumb_size)
            is_active = (idx == self.current_index)
            is_hover = (idx == self.hovered_index)

            # FR: Charger la miniature / EN: Load the thumbnail pixmap
            pix = self._load_pixmap(idx)
            if pix and not pix.isNull():
                painter.drawPixmap(r.x(), r.y(), pix)
            else:
                painter.fillRect(r, QColor(45, 48, 55))

            # FR: Cadre de sélection Picasa 3 / EN: Picasa 3 selection border
            if is_active:
                # FR: Bordure lumineuse bleue / cyan Picasa / EN: Bright Picasa blue / cyan border
                painter.setPen(QPen(QColor(51, 153, 255), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 3, 3)
            elif is_hover:
                # FR: Bordure de survol grise / EN: Gray hover border
                painter.setPen(QPen(QColor(140, 145, 155), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 2, 2)
            else:
                # FR: Bordure neutre très fine / EN: Thin neutral border
                painter.setPen(QPen(QColor(40, 42, 46), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(r, 2, 2)

