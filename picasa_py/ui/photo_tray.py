"""
FR: Composant du plateau inférieur de PyCasa (Bac à photos / Picture Tray).
Conserve les sélections actives, affiche le ruban de miniatures, l'ajout aux albums et les actions rapides.
EN: Photo Tray Component for PyCasa (Bottom Action Tray / Picture Tray).
Holds current selections, provides visual thumbnail strip, album assignment, and quick actions.

Ref: picasa3.exe @ 0x0088C3EC (Tray operations, Hold/Clear, Export, AddToAlbum)
Ref: picasa3.exe @ Picture Tray, 0x0088E914 (zoomslider)
Ref: runtime/constants.ui [Picasa2]
Ref: AGENTS.md §4 bis (Disposition et fonctionnement identiques à l'original)
"""

from __future__ import annotations
import os
from typing import List, Optional, Any, Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider, QFrame,
    QScrollArea, QMenu, QSizePolicy, QDialog, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QRect, QSize, QPoint
from PySide6.QtGui import (
    QColor, QFont, QPixmap, QPainter, QPen, QBrush, QPaintEvent, QMouseEvent,
    QAction, QIcon
)

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaButtonManagerDialog(QDialog):
    """
    FR: Dialogue « Configurer les boutons » de la barre inférieure Picasa 3.
    EN: "Configure Buttons" dialog for the Picasa 3 bottom button bar.
    Ref: runtime/BUTTONMGR_TEXT_FR.XML (Boutons disponibles :, Boutons actuels :,
         Ajouter >>, << Supprimer, Monter, Descendre, Rétablir les valeurs par défaut)
    """
    ALL_BUTTONS = [
        ("upload", "Importer (Web)"),
        ("email", "E-mail"),
        ("print", "Imprimer"),
        ("export", "Exporter"),
        ("collage", "Montage"),
        ("movie", "Film"),
    ]

    def __init__(
        self,
        active_keys: List[str],
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        """
        FR: Initialise le dialogue de configuration des boutons avec les clés de boutons actives.
        EN: Initializes the button manager dialog with the active button keys.
        """
        super().__init__(parent)
        self.style = style or getattr(parent, "style", None) or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()
        self.setWindowTitle(self.res_mgr.get_xml_string("buttonmgr", "Configurer les boutons"))
        self.resize(520, 340)
        self._active_keys = list(active_keys)

        root = QVBoxLayout(self)
        self.lbl_desc = QLabel(
            self.res_mgr.get_xml_string(
                "buttonmgr/instructions",
                "Sélectionnez les boutons à afficher dans la barre des boutons Picasa :",
            )
        )
        self.lbl_desc.setWordWrap(True)
        root.addWidget(self.lbl_desc)

        lists_layout = QHBoxLayout()

        # FR: Colonne gauche : Boutons disponibles
        # EN: Left column: Available buttons
        left_col = QVBoxLayout()
        self.lbl_available = QLabel(self.res_mgr.get_xml_string("buttonmgr/available", "Boutons disponibles :"))
        left_col.addWidget(self.lbl_available)
        self.list_available = QListWidget(self)
        left_col.addWidget(self.list_available)
        lists_layout.addLayout(left_col, 1)

        # FR: Colonne centrale : Ajouter >> / << Supprimer
        # EN: Middle column: Add >> / << Remove
        mid_col = QVBoxLayout()
        mid_col.addStretch(1)
        self.btn_add = QPushButton(self.res_mgr.get_xml_string("buttonmgr/add", "Ajouter >>"), self)
        self.btn_add.clicked.connect(self._on_add)
        mid_col.addWidget(self.btn_add)
        self.btn_remove = QPushButton(self.res_mgr.get_xml_string("buttonmgr/remove", "<< Supprimer"), self)
        self.btn_remove.clicked.connect(self._on_remove)
        mid_col.addWidget(self.btn_remove)
        mid_col.addStretch(1)
        lists_layout.addLayout(mid_col)

        # FR: Colonne droite : Boutons actuels + Monter / Descendre
        # EN: Right column: Current buttons + Move Up / Move Down
        right_col = QVBoxLayout()
        self.lbl_current = QLabel(self.res_mgr.get_xml_string("buttonmgr/current", "Boutons actuels :"))
        right_col.addWidget(self.lbl_current)
        self.list_current = QListWidget(self)
        right_col.addWidget(self.list_current)

        up_down = QHBoxLayout()
        self.btn_up = QPushButton(self.res_mgr.get_xml_string("buttonmgr/moveup", "Monter"), self)
        self.btn_up.clicked.connect(self._on_move_up)
        self.btn_down = QPushButton(self.res_mgr.get_xml_string("buttonmgr/movedown", "Descendre"), self)
        self.btn_down.clicked.connect(self._on_move_down)
        up_down.addWidget(self.btn_up)
        up_down.addWidget(self.btn_down)
        right_col.addLayout(up_down)
        lists_layout.addLayout(right_col, 1)

        root.addLayout(lists_layout, 1)

        # FR: Bas de dialogue : Rétablir les valeurs par défaut / OK / Annuler
        # EN: Dialog bottom: Reset to defaults / OK / Cancel
        bottom_row = QHBoxLayout()
        self.btn_reset = QPushButton(self.res_mgr.get_xml_string("buttonmgr/reset", "Rétablir les valeurs par défaut"), self)
        self.btn_reset.clicked.connect(self._on_reset_defaults)
        bottom_row.addWidget(self.btn_reset)
        bottom_row.addStretch(1)
        self.btn_ok = QPushButton(self.res_mgr.get_xml_string("buttonmgr/ok", "OK"), self)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("buttonmgr/cancel", "Annuler"), self)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(self.btn_ok)
        bottom_row.addWidget(self.btn_cancel)
        root.addLayout(bottom_row)

        self._populate_lists()
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs PicasaStyle au dialogue.
        EN: Dynamically applies the PicasaStyle color theme to the dialog.
        """
        if style is None:
            style = PicasaStyle.instance()
        self.style = style
        is_dark = style.is_dark
        bg = style.drawer_bgcolor.name() if is_dark else style.window_bgcolor.name()
        txt = style.alist_textcolor.name()
        list_bg = style.window_bgcolor.darker(115).name() if is_dark else "#FFFFFF"
        border = style.splitter_color.name() if is_dark else style.topbar_border_color.name()
        btn_bg = style.topbar_btn_bg_start.name()
        btn_hover = style.topbar_btn_bg_end.name()
        btn_border = style.topbar_btn_border.name()
        accent = style.accent_color.name()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {txt};
            }}
            QLabel {{
                color: {txt};
                font-size: 11px;
                background: transparent;
            }}
            QListWidget {{
                background-color: {list_bg};
                color: {txt};
                border: 1px solid {border};
                border-radius: 3px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {txt};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
        """)

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes du dialogue de configuration des boutons selon la langue active.
        EN: Updates the button configuration dialog texts according to the active language.
        """
        rm = PicasaResourceManager.get()
        self.setWindowTitle(rm.get_xml_string("buttonmgr", "Configurer les boutons"))
        self.lbl_desc.setText(
            rm.get_xml_string(
                "buttonmgr/instructions",
                "Sélectionnez les boutons à afficher dans la barre des boutons Picasa :",
            )
        )
        self.lbl_available.setText(rm.get_xml_string("buttonmgr/available", "Boutons disponibles :"))
        self.lbl_current.setText(rm.get_xml_string("buttonmgr/current", "Boutons actuels :"))
        self.btn_add.setText(rm.get_xml_string("buttonmgr/add", "Ajouter >>"))
        self.btn_remove.setText(rm.get_xml_string("buttonmgr/remove", "<< Supprimer"))
        self.btn_up.setText(rm.get_xml_string("buttonmgr/moveup", "Monter"))
        self.btn_down.setText(rm.get_xml_string("buttonmgr/movedown", "Descendre"))
        self.btn_reset.setText(rm.get_xml_string("buttonmgr/reset", "Rétablir les valeurs par défaut"))
        self.btn_ok.setText(rm.get_xml_string("buttonmgr/ok", "OK"))
        self.btn_cancel.setText(rm.get_xml_string("buttonmgr/cancel", "Annuler"))

    def _populate_lists(self) -> None:
        """
        FR: Remplit les listes des boutons disponibles et des boutons actuels.
        EN: Populates the available buttons and current buttons lists.
        """
        self.list_available.clear()
        self.list_current.clear()
        label_map = dict(self.ALL_BUTTONS)
        for key in self._active_keys:
            if key in label_map:
                it = QListWidgetItem(label_map[key])
                it.setData(Qt.ItemDataRole.UserRole, key)
                self.list_current.addItem(it)
        for key, label in self.ALL_BUTTONS:
            if key not in self._active_keys:
                it = QListWidgetItem(label)
                it.setData(Qt.ItemDataRole.UserRole, key)
                self.list_available.addItem(it)

    def _on_add(self) -> None:
        """
        FR: Ajoute le bouton sélectionné de la liste disponible vers la liste actuelle.
        EN: Adds the selected button from the available list to the current list.
        """
        it = self.list_available.currentItem()
        if not it:
            return
        key = it.data(Qt.ItemDataRole.UserRole)
        if key and key not in self._active_keys:
            self._active_keys.append(key)
            self._populate_lists()

    def _on_remove(self) -> None:
        """
        FR: Retire le bouton sélectionné de la liste des boutons actuels.
        EN: Removes the selected button from the current buttons list.
        """
        it = self.list_current.currentItem()
        if not it:
            return
        key = it.data(Qt.ItemDataRole.UserRole)
        if key in self._active_keys:
            self._active_keys.remove(key)
            self._populate_lists()

    def _on_move_up(self) -> None:
        """
        FR: Déplace le bouton sélectionné vers le haut dans la liste actuelle.
        EN: Moves the selected button up in the current list.
        """
        row = self.list_current.currentRow()
        if row > 0:
            self._active_keys[row - 1], self._active_keys[row] = (
                self._active_keys[row],
                self._active_keys[row - 1],
            )
            self._populate_lists()
            self.list_current.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        """
        FR: Déplace le bouton sélectionné vers le bas dans la liste actuelle.
        EN: Moves the selected button down in the current list.
        """
        row = self.list_current.currentRow()
        if 0 <= row < len(self._active_keys) - 1:
            self._active_keys[row + 1], self._active_keys[row] = (
                self._active_keys[row],
                self._active_keys[row + 1],
            )
            self._populate_lists()
            self.list_current.setCurrentRow(row + 1)

    def _on_reset_defaults(self) -> None:
        """
        FR: Rétablit l'ensemble et l'ordre par défaut des boutons de la barre.
        EN: Restores the default set and order of bar buttons.
        """
        self._active_keys = [k for k, _ in self.ALL_BUTTONS]
        self._populate_lists()

    def get_active_keys(self) -> List[str]:
        """
        FR: Retourne la liste ordonnée des clés de boutons actifs.
        EN: Returns the ordered list of active button keys.
        """
        return list(self._active_keys)


class PicasaZoomIcon(QWidget):
    """
    FR: Icône de zoom de vignette (petite grille 2x2 ou grande vignette unique).
    EN: Thumbnail zoom icon (small 2x2 grid or single large thumbnail).
    Ref: picasa3.exe @ zoomslider (0x0088E914)
    """

    def __init__(self, is_large: bool = False, parent: Optional[QWidget] = None):
        """
        FR: Initialise l'icône de zoom (petite grille ou grande vignette).
        EN: Initializes the zoom icon (small grid or large thumbnail).
        """
        super().__init__(parent)
        self.is_large = is_large
        self.setFixedSize(18, 18)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine l'icône de grille 2x2 ou de grande vignette unique.
        EN: Paints the 2x2 grid icon or single large thumbnail icon.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor("#8A92A0")
        painter.setPen(QPen(color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if not self.is_large:
            # FR: Petite grille de 4 carrés (2x2)
            # EN: Small grid of 4 squares (2x2)
            for row in range(2):
                for col in range(2):
                    r = QRect(2 + col * 7, 2 + row * 7, 6, 6)
                    painter.drawRect(r)
        else:
            # FR: Grande vignette unique
            # EN: Single large thumbnail
            r = QRect(2, 2, 13, 13)
            painter.drawRect(r)


def _resolve_item_pixmap(item: Any) -> Optional[QPixmap]:
    """
    FR: Récupère ou charge à la volée la miniature `QPixmap` réelle d'un élément sélectionné
    pour l'afficher dans le bac à photos (`thumbui/scratch`), sans jamais se contenter d'une icône générique.
    EN: Retrieves or loads on the fly the actual `QPixmap` thumbnail of a selected item
    for display in the photo tray (`thumbui/scratch`), never falling back to a generic icon alone.
    Ref: picasa3.exe @ 0x0088C3EC (CScratchPad::DrawItem)
    """
    pix = getattr(item, "pixmap", None)
    if isinstance(pix, QPixmap) and not pix.isNull():
        return pix

    # FR: 1. Essayer depuis des octets JPEG en mémoire si présents
    # EN: 1. Try from in-memory JPEG bytes if present
    raw_bytes = getattr(item, "thumbnail_bytes", None) or getattr(item, "jpeg_bytes", None)
    if raw_bytes:
        p = QPixmap()
        if p.loadFromData(raw_bytes) and not p.isNull():
            try:
                setattr(item, "pixmap", p)
            except Exception:
                pass
            return p

    # FR: 2. Charger depuis le chemin disque avec QPixmap / PIL draft rapide
    # EN: 2. Load from disk path using fast QPixmap / PIL draft
    path = getattr(item, "path", None)
    if path and isinstance(path, str) and os.path.isfile(path):
        try:
            from PIL import Image, ImageOps
            from PySide6.QtGui import QImage
            with Image.open(path) as raw_img:
                raw_img.draft("RGB", (160, 160))
                try:
                    img = ImageOps.exif_transpose(raw_img)
                except Exception:
                    img = raw_img
                if img.mode in ("P", "PA") or (img.mode != "RGBA" and "transparency" in img.info):
                    img = img.convert("RGBA")
                img_rgb = img.convert("RGB")
                img_rgb.thumbnail((96, 96), Image.Resampling.BILINEAR)
                data = img_rgb.tobytes("raw", "RGB")
                qimg = QImage(data, img_rgb.width, img_rgb.height, img_rgb.width * 3, QImage.Format.Format_RGB888)
                p = QPixmap.fromImage(qimg.copy())
                if not p.isNull():
                    try:
                        setattr(item, "pixmap", p)
                    except Exception:
                        pass
                    return p
        except Exception:
            p = QPixmap(path)
            if not p.isNull():
                scaled = p.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                try:
                    setattr(item, "pixmap", scaled)
                except Exception:
                    pass
                return scaled
    return None


class PicasaTrayThumbnailItemWidget(QWidget):
    """
    FR: Vignette individuelle miniature au sein du bac à photos (Picture Tray).
    EN: Individual miniature thumbnail widget inside the Picture Tray.
    Ref: picasa3.exe @ Picture Tray, 0x0088C3EC
    """
    clicked = Signal(object)
    remove_clicked = Signal(object)

    def __init__(self, item: Any, is_held: bool = False, parent: Optional[QWidget] = None):
        """
        FR: Initialise la vignette d'un élément dans le bac à photos.
        EN: Initializes an item thumbnail widget in the photo tray.
        """
        super().__init__(parent)
        self.item = item
        self.is_held = is_held
        self.is_hovered: bool = False

        self.setFixedSize(46, 46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        fname = getattr(item, "filename", "") or os.path.basename(getattr(item, "path", ""))
        self.setToolTip(f"{fname}\n(Clic pour afficher, clic-droit pour retirer du bac)")

    def enterEvent(self, event: Any) -> None:
        """
        FR: Active l'état de survol lorsque le curseur entre dans la vignette.
        EN: Enables hover state when the cursor enters the thumbnail.
        """
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        """
        FR: Désactive l'état de survol lorsque le curseur quitte la vignette.
        EN: Disables hover state when the cursor leaves the thumbnail.
        """
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le clic gauche (sélection ou suppression sur le badge) et le clic droit (retrait du bac).
        EN: Handles left-click (selection or removal on badge) and right-click (remove from tray).
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # FR: Vérifier si clic sur la zone de fermeture en haut à droite
            # EN: Check if click is inside the top-right close area
            if self.is_hovered and event.pos().x() >= 30 and event.pos().y() <= 14:
                self.remove_clicked.emit(self.item)
            else:
                self.clicked.emit(self.item)
        elif event.button() == Qt.MouseButton.RightButton:
            self.remove_clicked.emit(self.item)
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine la miniature, son cadre blanc de tirage photo et les badges d'état.
        EN: Paints the thumbnail, its white photo print border, and state badges.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # FR: 1. Cadre de fond type tirage photo (bordure blanche Picasa)
        # EN: 1. Photo-print background frame (Picasa white border)
        rect = QRect(2, 2, 42, 42)
        painter.fillRect(rect, QColor("#22252A"))

        # FR: 2. Image miniature réelle
        # EN: 2. Actual thumbnail image
        pix = _resolve_item_pixmap(self.item)
        if pix and not pix.isNull():
            scaled = pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x_off = 2 + (42 - scaled.width()) // 2
            y_off = 2 + (42 - scaled.height()) // 2
            frame_r = QRect(x_off - 1, y_off - 1, scaled.width() + 2, scaled.height() + 2)
            painter.fillRect(frame_r, QColor("#FFFFFF"))
            painter.drawPixmap(x_off, y_off, scaled)
        else:
            painter.setPen(QColor("#777E8C"))
            painter.setFont(QFont("Segoe UI", 12))
            is_vid = getattr(self.item, "is_video", False)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎬" if is_vid else "🖼️")

        # FR: 3. Bordure selon état (Normal, Survol, Held)
        # EN: 3. Border according to state (Normal, Hover, Held)
        if self.is_held:
            pen = QPen(QColor("#4CAF50"), 1.8)
        elif self.is_hovered:
            pen = QPen(QColor("#3D85B3"), 1.5)
        else:
            pen = QPen(QColor("#D0D4DC"), 1)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        # FR: 4. Petit badge de suppression en survol
        # EN: 4. Small close/remove badge on hover
        if self.is_hovered:
            close_r = QRect(31, 2, 13, 13)
            painter.fillRect(close_r, QColor(0, 0, 0, 190))
            painter.setPen(QColor("#FF5555"))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(close_r, Qt.AlignmentFlag.AlignCenter, "✕")

        # FR: 5. Badge d'épingle si 'Held'
        # EN: 5. Pin badge if 'Held'
        if self.is_held:
            pin_r = QRect(3, 3, 10, 10)
            painter.setPen(QColor("#4CAF50"))
            painter.setFont(QFont("Segoe UI Emoji", 7))
            painter.drawText(pin_r, Qt.AlignmentFlag.AlignCenter, "📌")


class PicasaTrayThumbnailStackWidget(QWidget):
    """
    FR: Affichage regroupé en pile / éventail (`CScratchPad` @ 0x0088C3EC) lorsque de nombreuses
    photos (> 4) sont sélectionnées dans le bac à photos (`thumbui/scratch`).
    Affiche les miniatures chevauchées avec cadre photo blanc, ombre portée et badge du total.
    EN: Stacked / fanned display (`CScratchPad` @ 0x0088C3EC) when many photos (> 4)
    are selected in the photo tray (`thumbui/scratch`).
    Displays overlapping thumbnails with white photo border, drop shadow, and total count badge.
    """
    clicked = Signal(object)
    remove_clicked = Signal(object)

    def __init__(self, items: List[Any], is_held: bool = False, parent: Optional[QWidget] = None):
        """
        FR: Initialise le widget de pile de miniatures avec la liste des éléments sélectionnés.
        EN: Initializes the thumbnail stack widget with the list of selected items.
        """
        super().__init__(parent)
        self.items = list(items)
        self.is_held = is_held
        self.hovered_index: int = -1
        self.setMinimumWidth(190)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{len(self.items)} photos sélectionnées dans le bac\n(Clic pour afficher la photo survolée)")

    def _visible_cards(self) -> List[Tuple[int, Any, QRect]]:
        """
        FR: Calcule les positions chevauchées des cartes de la pile dans la largeur disponible.
        EN: Computes the overlapping card positions of the stack within the available width.
        """
        n = len(self.items)
        if n == 0:
            return []
        max_cards = min(n, 12)
        avail_w = max(160, self.width() - 8)
        card_sz = 42
        if max_cards == 1:
            step = 0
        else:
            step = max(8, min(32, (avail_w - card_sz - 12) // (max_cards - 1)))
        cards: List[Tuple[int, Any, QRect]] = []
        for idx in range(max_cards):
            item = self.items[idx]
            x = 4 + idx * step
            y = 3 + ((idx % 3) - 1)  # FR: léger décalage vertical naturel d'une pile Picasa / EN: natural vertical offset of a Picasa stack
            cards.append((idx, item, QRect(x, y, card_sz, card_sz)))
        return cards

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        FR: Met à jour la carte survolée et l'infobulle lors du déplacement de la souris sur la pile.
        EN: Updates the hovered card and tooltip when moving the mouse over the stack.
        """
        pos = event.pos()
        hit = -1
        for idx, _, r in reversed(self._visible_cards()):
            if r.contains(pos):
                hit = idx
                break
        if hit != self.hovered_index:
            self.hovered_index = hit
            if 0 <= hit < len(self.items):
                it = self.items[hit]
                fname = getattr(it, "filename", "") or os.path.basename(getattr(it, "path", ""))
                self.setToolTip(f"{fname} ({hit + 1}/{len(self.items)} dans la pile)")
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: Any) -> None:
        """
        FR: Réinitialise l'indice de carte survolée lorsque la souris quitte la pile.
        EN: Resets the hovered card index when the mouse leaves the stack.
        """
        self.hovered_index = -1
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Émet le signal de clic ou de retrait pour la carte survolée dans la pile.
        EN: Emits the click or remove signal for the hovered card in the stack.
        """
        if not self.items:
            return
        idx = self.hovered_index if 0 <= self.hovered_index < len(self.items) else (len(self.items) - 1)
        target = self.items[idx]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(target)
        elif event.button() == Qt.MouseButton.RightButton:
            self.remove_clicked.emit(target)
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine les cartes chevauchées de la pile ainsi que le badge du nombre total d'éléments.
        EN: Paints the overlapping cards of the stack as well as the total item count badge.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cards = self._visible_cards()
        for idx, item, rect in cards:
            # FR: Ombre portée sous chaque vignette de la pile
            # EN: Drop shadow under each thumbnail in the stack
            shadow_r = rect.adjusted(2, 2, 2, 2)
            painter.fillRect(shadow_r, QColor(0, 0, 0, 110))

            # FR: Fond blanc de tirage photo
            # EN: White photo-print background
            painter.fillRect(rect, QColor("#F4F5F7"))
            inner_r = rect.adjusted(2, 2, -2, -2)
            painter.fillRect(inner_r, QColor("#22252A"))

            pix = _resolve_item_pixmap(item)
            if pix and not pix.isNull():
                scaled = pix.scaled(
                    inner_r.width(),
                    inner_r.height(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                sx = max(0, (scaled.width() - inner_r.width()) // 2)
                sy = max(0, (scaled.height() - inner_r.height()) // 2)
                painter.drawPixmap(inner_r.topLeft(), scaled, QRect(sx, sy, inner_r.width(), inner_r.height()))

            if idx == self.hovered_index:
                pen = QPen(QColor("#3D85B3"), 2.0)
            elif self.is_held:
                pen = QPen(QColor("#4CAF50"), 1.6)
            else:
                pen = QPen(QColor("#FFFFFF"), 1.2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        # FR: Badge du nombre total de photos empilées en bas à droite de la pile
        # EN: Total stacked photo count badge at the bottom right of the stack
        if cards:
            last_rect = cards[-1][2]
            badge_text = f"×{len(self.items)}"
            badge_w = max(26, 8 + len(badge_text) * 7)
            badge_r = QRect(
                min(self.width() - badge_w - 2, last_rect.right() - badge_w // 2),
                last_rect.bottom() - 15,
                badge_w,
                16,
            )
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            painter.setBrush(QBrush(QColor("#2B6DA8" if not self.is_held else "#2E7D32")))
            painter.drawRoundedRect(badge_r, 7, 7)
            painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold))
            painter.drawText(badge_r, Qt.AlignmentFlag.AlignCenter, badge_text)


class PicasaTrayThumbnailStrip(QScrollArea):
    """
    FR: Ruban horizontal de prévisualisation des miniatures dans le bac à photos (`thumbui/scratch`),
    avec filigrane « Sélection » (`thumbui/scratchlabel`) lorsqu'il est vide, et regroupement
    automatique en pile (`CScratchPad`) lorsque plus de 4 photos sont sélectionnées.
    EN: Horizontal thumbnail preview strip in the photo tray (`thumbui/scratch`),
    with "Selection" watermark (`thumbui/scratchlabel`) when empty, and automatic
    stack grouping (`CScratchPad`) when more than 4 photos are selected.
    Ref: respack.yt @ thumbui/scratch (rect 8, 455, 223, 515), thumbui/scratchlabel (rect 13, 480, 218, 499)
    """
    item_clicked = Signal(object)
    item_remove_requested = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le ruban défilant de miniatures et son filigrane « Sélection ».
        EN: Initializes the scrollable thumbnail strip and its "Selection" watermark.
        """
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setMinimumWidth(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setStyleSheet("""
            QScrollArea {
                background: #23262C;
                border: 1px solid #17191D;
                border-bottom: 1px solid #3C414B;
                border-right: 1px solid #3C414B;
                border-radius: 3px;
            }
            QScrollBar:horizontal {
                height: 4px;
                background: #1D2025;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #555B66;
                border-radius: 2px;
                min-width: 16px;
            }
        """)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout_h = QHBoxLayout(self.container)
        self.layout_h.setContentsMargins(4, 4, 4, 4)
        self.layout_h.setSpacing(4)

        # FR: Filigrane « Sélection » (thumbui/scratchlabel) affiché quand le bac est vide
        # EN: "Selection" watermark (thumbui/scratchlabel) displayed when the tray is empty
        self.watermark_label = QLabel("Sélection", self.container)
        self.watermark_label.setStyleSheet(
            "color: #555B66; font-size: 13px; font-weight: bold; font-style: italic; padding-left: 8px;"
        )
        self.layout_h.addWidget(self.watermark_label)
        self.layout_h.addStretch(1)

        self.setWidget(self.container)
        self.items: List[Any] = []
        self.is_held: bool = False

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique le style de thème PicasaStyle au ruban de miniatures et au filigrane.
        EN: Applies the PicasaStyle theme style to the thumbnail strip and watermark.
        """
        strip_bg = style.tray_grad_end.darker(112).name() if style.is_dark else style.window_bgcolor.name()
        border_top = "#17191D" if style.is_dark else style.topbar_border_color.name()
        border_bot = "#3C414B" if style.is_dark else "#FFFFFF"
        wm_color = "#555B66" if style.is_dark else style.alayout_subtitleColor.name()
        self.setStyleSheet(f"""
            QScrollArea {{
                background: {strip_bg};
                border: 1px solid {border_top};
                border-bottom: 1px solid {border_bot};
                border-right: 1px solid {border_bot};
                border-radius: 3px;
            }}
            QScrollBar:horizontal {{
                height: 4px;
                background: {strip_bg};
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {style.topbar_btn_border.name()};
                border-radius: 2px;
                min-width: 16px;
            }}
        """)
        self.watermark_label.setStyleSheet(
            f"color: {wm_color}; font-size: 13px; font-weight: bold; font-style: italic; padding-left: 8px;"
        )


    def set_items(self, items: List[Any], is_held: bool = False) -> None:
        """
        FR: Met à jour les éléments affichés dans le ruban (vignettes individuelles ou pile chevauchée).
        EN: Updates the items displayed in the strip (individual thumbnails or overlapping stack).
        """
        self.items = list(items)
        self.is_held = is_held

        # FR: Nettoyage des widgets de miniatures existants (en préservant watermark_label et le stretch)
        # EN: Clean up existing thumbnail widgets (preserving watermark_label and stretch)
        for i in reversed(range(self.layout_h.count())):
            w_item = self.layout_h.itemAt(i)
            w = w_item.widget() if w_item else None
            if w and w is not self.watermark_label:
                self.layout_h.takeAt(i)
                w.deleteLater()

        self.watermark_label.setVisible(len(self.items) == 0)

        # Ref: picasa3.exe @ 0x0088C3EC (CScratchPad) :
        # FR: - Jusqu'à 4 photos : affichage côte à côte des miniatures
        # FR: - Plus de 4 photos : regroupement visuel en pile chevauchée (PicasaTrayThumbnailStackWidget)
        # EN: - Up to 4 photos: side-by-side thumbnail display
        # EN: - More than 4 photos: visual grouping in an overlapping stack (PicasaTrayThumbnailStackWidget)
        if len(self.items) > 4:
            stack_w = PicasaTrayThumbnailStackWidget(self.items, is_held=self.is_held, parent=self.container)
            stack_w.clicked.connect(self.item_clicked.emit)
            stack_w.remove_clicked.connect(self.item_remove_requested.emit)
            self.layout_h.insertWidget(self.layout_h.count() - 1, stack_w, 1)
        else:
            for it in self.items:
                w = PicasaTrayThumbnailItemWidget(it, is_held=self.is_held, parent=self.container)
                w.clicked.connect(self.item_clicked.emit)
                w.remove_clicked.connect(self.item_remove_requested.emit)
                self.layout_h.insertWidget(self.layout_h.count() - 1, w)


class PicasaPhotoTray(QWidget):
    """
    FR: Plateau de contrôle inférieur à 2 étages / 3 zones fidèle à `thumbui/basecontrolset` (hauteur 98-105px) :
    - Zone Gauche (`thumbui/scratchback`, ~36.5% de la largeur, X=8..285, Y=449..530) :
      * `thumbui/infotext` (état de la sélection au-dessus du bac)
      * `thumbui/scratch` (bande de miniatures avec filigrane « Sélection »)
      * Colonne verticale de 3 boutons à droite du bac (X=244..278) :
        1. `thumbui/scratchhold` (Maintenir 📌, 34x22, Y=454..476)
        2. `thumbui/scratchclear` (Effacer ✕, 34x20, Y=476..496)
        3. `thumbui/addtobuttcon` (Ajouter à l'album ➕▾, 34x22, Y=503..525)
    - Zone Droite — Étage Supérieur (au-dessus de `thumbui/separator`, Y=448..475) :
      * Gauche (`bcenterright`) : `startoggle` (☆, 36x22), `rotateleft` (↶, 36x22), `rotateright` (↷, 36x22)
      * Centre (`scale_group`) : `loupe` + `scalecontainer` (curseur de zoom des vignettes, 127x27)
      * Droite (`metadata_group`) : 4 boutons bascule du tiroir droit (`people_toggle`, `places_toggle`, `tags_toggle`, `properties_toggle`)
    - Zone Droite — Étage Inférieur (sous `thumbui/separator`, Y=480..528) :
      * `thumbui/webupload` (bouton vert « Importer » / « Partager », 141x35)
      * `thumbui/outputs` (`outputlayout`, cellules 55x36 : E-mail, Imprimer, Exporter, Montage, Film, Plus/⚙)
    EN: 2-tier / 3-zone bottom control tray faithful to `thumbui/basecontrolset` (height 98-105px):
    - Left Zone (`thumbui/scratchback`, ~36.5% width, X=8..285, Y=449..530):
      * `thumbui/infotext` (selection status above the tray)
      * `thumbui/scratch` (thumbnail strip with "Selection" watermark)
      * Vertical column of 3 buttons on the right of the tray (X=244..278):
        1. `thumbui/scratchhold` (Hold 📌, 34x22, Y=454..476)
        2. `thumbui/scratchclear` (Clear ✕, 34x20, Y=476..496)
        3. `thumbui/addtobuttcon` (Add to Album ➕▾, 34x22, Y=503..525)
    - Right Zone — Upper Tier (above `thumbui/separator`, Y=448..475):
      * Left (`bcenterright`): `startoggle` (☆, 36x22), `rotateleft` (↶, 36x22), `rotateright` (↷, 36x22)
      * Center (`scale_group`): `loupe` + `scalecontainer` (thumbnail zoom slider, 127x27)
      * Right (`metadata_group`): 4 right-drawer toggle buttons (`people_toggle`, `places_toggle`, `tags_toggle`, `properties_toggle`)
    - Right Zone — Lower Tier (below `thumbui/separator`, Y=480..528):
      * `thumbui/webupload` (green "Upload" / "Share" button, 141x35)
      * `thumbui/outputs` (`outputlayout`, 55x36 cells: Email, Print, Export, Collage, Movie, More/⚙)

    Ref: respack.yt @ thumbui.tre (basecontrolset, scratchback, bcenterright, scale_group, metadata_group, separator, outputs)
    Ref: respack.yt @ scratch.tre, outputlayout.tre
    Ref: picasa3.exe @ 0x0088C3EC, 0x0088E914
    """
    zoom_changed = Signal(int)
    action_export = Signal()
    action_print = Signal()
    action_email = Signal()
    action_star = Signal()
    action_rotate_left = Signal()
    action_rotate_right = Signal()
    action_collage = Signal()
    action_movie = Signal()
    action_hold = Signal(bool)  # FR: True = actif, False = relâché / EN: True = active, False = released
    action_clear = Signal()
    action_add_to_album = Signal()
    action_thumbnail_clicked = Signal(object)
    panel_toggled = Signal(str)
    upload_requested = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise le plateau inférieur PicasaPhotoTray et ses deux étages de contrôles.
        EN: Initializes the PicasaPhotoTray bottom tray and its two control tiers.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.is_held: bool = False
        self.held_items: List[Any] = []
        self.active_items: List[Any] = []

        # FR: Hauteur authentique de basecontrolset : rect=(0, 429, 800, 534) -> 98-105 px
        # EN: Authentic height of basecontrolset: rect=(0, 429, 800, 534) -> 98-105 px
        self.setFixedHeight(98)
        self.setObjectName("TrayRoot")
        self.apply_style(self.style)

        root_h = QHBoxLayout(self)
        root_h.setContentsMargins(8, 4, 8, 5)
        root_h.setSpacing(10)

        # =====================================================================
        # FR: ZONE GAUCHE : thumbui/scratchback (Picture Tray + 3 boutons empilés)
        # EN: LEFT ZONE: thumbui/scratchback (Picture Tray + 3 stacked buttons)
        # Ref: respack.yt @ thumbui/scratchback rect=(8, 449, 285, 530)
        # =====================================================================
        left_zone = QWidget(self)
        left_zone.setMinimumWidth(260)
        left_zone.setMaximumWidth(340)
        left_vbox = QVBoxLayout(left_zone)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(2)

        # FR: Texte d'état de sélection au sommet (thumbui/infotext rect=(183, 429, 664, 443))
        # EN: Selection status text at the top (thumbui/infotext rect=(183, 429, 664, 443))
        self.lbl_selection = QLabel("Aucune photo sélectionnée")
        self.lbl_selection.setObjectName("TraySelectionLabel")
        left_vbox.addWidget(self.lbl_selection)

        # FR: Cadre enfoncé du bac à photos (thumbui/scratchpadbase)
        # EN: Sunken frame of the photo tray (thumbui/scratchpadbase)
        self.scratchpad_frame = QFrame(left_zone)
        self.scratchpad_frame.setObjectName("ScratchPadBase")
        scratch_h = QHBoxLayout(self.scratchpad_frame)
        scratch_h.setContentsMargins(4, 4, 4, 4)
        scratch_h.setSpacing(4)

        # FR: Bande de miniatures (thumbui/scratch rect=(8, 455, 223, 515))
        # EN: Thumbnail strip (thumbui/scratch rect=(8, 455, 223, 515))
        self.thumb_strip = PicasaTrayThumbnailStrip(self.scratchpad_frame)
        self.thumb_strip.item_clicked.connect(self.action_thumbnail_clicked.emit)
        self.thumb_strip.item_remove_requested.connect(self._on_remove_item)
        scratch_h.addWidget(self.thumb_strip, 1)

        # FR: Colonne verticale des 3 boutons du bac à droite (X=244..278) :
        # EN: Vertical column of the 3 tray buttons on the right (X=244..278):
        # 1. scratchhold (Y=454..476)
        # 2. scratchclear (Y=476..496)
        # 3. addtobuttcon (Y=503..525)
        tray_btns_col = QVBoxLayout()
        tray_btns_col.setContentsMargins(0, 0, 0, 0)
        tray_btns_col.setSpacing(2)

        self.btn_hold = QPushButton("📌")
        self.btn_hold.setObjectName("TrayStackBtn")
        self.btn_hold.setCheckable(True)
        self.btn_hold.setFixedSize(36, 20)
        self.btn_hold.setToolTip("Maintenir les photos sélectionnées dans le bac (Hold)")
        self.btn_hold.clicked.connect(self._toggle_hold)
        tray_btns_col.addWidget(self.btn_hold)

        self.btn_clear = QPushButton("✕")
        self.btn_clear.setObjectName("TrayStackBtn")
        self.btn_clear.setFixedSize(36, 20)
        self.btn_clear.setToolTip("Effacer le bac à photos (Clear)")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        tray_btns_col.addWidget(self.btn_clear)

        self.btn_add_to_album = QPushButton("➕▾")
        self.btn_add_to_album.setObjectName("TrayStackBtn")
        self.btn_add_to_album.setFixedSize(36, 20)
        self.btn_add_to_album.setToolTip("Ajouter les photos sélectionnées à un album...")
        self.btn_add_to_album.clicked.connect(self.action_add_to_album.emit)
        self.btn_add_to_album.setEnabled(False)
        tray_btns_col.addWidget(self.btn_add_to_album)

        scratch_h.addLayout(tray_btns_col)
        left_vbox.addWidget(self.scratchpad_frame, 1)
        root_h.addWidget(left_zone, 36)

        # =====================================================================
        # FR: ZONE DROITE : 2 étages séparés par thumbui/separator (Y=476..478)
        # EN: RIGHT ZONE: 2 tiers separated by thumbui/separator (Y=476..478)
        # =====================================================================
        right_zone = QWidget(self)
        right_vbox = QVBoxLayout(right_zone)
        right_vbox.setContentsMargins(0, 2, 0, 0)
        right_vbox.setSpacing(4)

        # ---------------------------------------------------------------------
        # FR: ÉTAGE SUPÉRIEUR (Y = 448..475) :
        # EN: UPPER TIER (Y = 448..475):
        # [☆] [↶] [↷]   |   [🔍 ----o---- 🖼️]   |   [👤 Personnes][📍 Lieux][🏷️ Tags][ℹ️ Propriétés]
        # ---------------------------------------------------------------------
        upper_strip = QHBoxLayout()
        upper_strip.setContentsMargins(0, 0, 0, 0)
        upper_strip.setSpacing(4)

        # 1. thumbui/startoggle : rect=(289, 449, 325, 471) -> 36x22 px
        self.btn_star = QPushButton("☆")
        self.btn_star.setObjectName("StarBtn")
        self.btn_star.setFixedSize(36, 24)
        self.btn_star.setToolTip("Ajouter/supprimer une étoile de favori (Ctrl+T)")
        self.btn_star.clicked.connect(self.action_star.emit)
        upper_strip.addWidget(self.btn_star)

        # 2. thumbui/rotateleft : rect=(330, 449, 366, 471) -> 36x22 px
        self.btn_rotate_left = QPushButton("↶")
        self.btn_rotate_left.setFixedSize(36, 24)
        self.btn_rotate_left.setToolTip("Faire pivoter vers la gauche (Ctrl+Maj+R)")
        self.btn_rotate_left.clicked.connect(self.action_rotate_left.emit)
        upper_strip.addWidget(self.btn_rotate_left)

        # 3. thumbui/rotateright : rect=(367, 449, 403, 471) -> 36x22 px
        self.btn_rotate_right = QPushButton("↷")
        self.btn_rotate_right.setFixedSize(36, 24)
        self.btn_rotate_right.setToolTip("Faire pivoter vers la droite (Ctrl+R)")
        self.btn_rotate_right.clicked.connect(self.action_rotate_right.emit)
        upper_strip.addWidget(self.btn_rotate_right)

        upper_strip.addSpacing(8)

        # 4. thumbui/scale_group : loupe (368..391) + scalecontainer (398..525, 127x27)
        self.icon_small = PicasaZoomIcon(is_large=False)
        upper_strip.addWidget(self.icon_small)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(64, 256)
        self.zoom_slider.setValue(140)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.setToolTip("Ajuster la taille des vignettes")
        self.zoom_slider.valueChanged.connect(self.zoom_changed.emit)
        upper_strip.addWidget(self.zoom_slider)

        self.icon_large = PicasaZoomIcon(is_large=True)
        upper_strip.addWidget(self.icon_large)

        upper_strip.addStretch(1)

        # FR: 5. thumbui/metadata_group : rect=(545, 448, 785, 472) -> 4 boutons bascule (60x24 chacun)
        # EN: 5. thumbui/metadata_group: rect=(545, 448, 785, 472) -> 4 toggle buttons (60x24 each)
        metadata_box = QWidget(right_zone)
        metadata_layout = QHBoxLayout(metadata_box)
        metadata_layout.setContentsMargins(0, 0, 0, 0)
        metadata_layout.setSpacing(2)

        # FR: 4 boutons d'icônes (sans texte) de la colonne de droite (Ref: picasa3.exe @ 0x005D96D4..0x005D9E54, TOOLTIPS_FR.XML:858-869)
        # EN: 4 icon-only buttons (no text) for the right column (Ref: picasa3.exe @ 0x005D96D4..0x005D9E54, TOOLTIPS_FR.XML:858-869)
        rm = PicasaResourceManager.get()
        from PySide6.QtCore import QSize

        self.btn_panel_people = QPushButton("")
        self.btn_panel_people.setIcon(rm.get_drawer_toggle_icon("people", 18))
        self.btn_panel_people.setIconSize(QSize(18, 18))
        self.btn_panel_people.setCheckable(True)
        self.btn_panel_people.setFixedSize(30, 24)
        self.btn_panel_people.setToolTip(rm.get_xml_string("thumbui/people_toggle.tooltip", "Afficher/masquer le panneau Personnes"))
        self.btn_panel_people.clicked.connect(lambda: self.panel_toggled.emit("people"))
        metadata_layout.addWidget(self.btn_panel_people)

        self.btn_panel_places = QPushButton("")
        self.btn_panel_places.setIcon(rm.get_drawer_toggle_icon("places", 18))
        self.btn_panel_places.setIconSize(QSize(18, 18))
        self.btn_panel_places.setCheckable(True)
        self.btn_panel_places.setFixedSize(30, 24)
        self.btn_panel_places.setToolTip(rm.get_xml_string("thumbui/places_toggle.tooltip", "Afficher/Masquer le panneau Lieux"))
        self.btn_panel_places.clicked.connect(lambda: self.panel_toggled.emit("places"))
        metadata_layout.addWidget(self.btn_panel_places)

        self.btn_panel_tags = QPushButton("")
        self.btn_panel_tags.setIcon(rm.get_drawer_toggle_icon("tags", 18))
        self.btn_panel_tags.setIconSize(QSize(18, 18))
        self.btn_panel_tags.setCheckable(True)
        self.btn_panel_tags.setFixedSize(30, 24)
        self.btn_panel_tags.setToolTip(rm.get_xml_string("thumbui/tags_toggle.tooltip", "Afficher/Masquer le panneau Tags"))
        self.btn_panel_tags.clicked.connect(lambda: self.panel_toggled.emit("tags"))
        metadata_layout.addWidget(self.btn_panel_tags)

        self.btn_panel_props = QPushButton("")
        self.btn_panel_props.setIcon(rm.get_drawer_toggle_icon("properties", 18))
        self.btn_panel_props.setIconSize(QSize(18, 18))
        self.btn_panel_props.setCheckable(True)
        self.btn_panel_props.setFixedSize(30, 24)
        self.btn_panel_props.setToolTip(rm.get_xml_string("thumbui/properties_toggle.tooltip", "Afficher/Masquer le panneau Propriétés"))
        self.btn_panel_props.clicked.connect(lambda: self.panel_toggled.emit("properties"))
        metadata_layout.addWidget(self.btn_panel_props)

        upper_strip.addWidget(metadata_box)
        right_vbox.addLayout(upper_strip)

        # ---------------------------------------------------------------------
        # FR: SÉPARATEUR HORIZONTAL (thumbui/separator : rect=(296, 476, 793, 478))
        # EN: HORIZONTAL SEPARATOR (thumbui/separator: rect=(296, 476, 793, 478))
        # ---------------------------------------------------------------------
        self.sep_horiz = QFrame(right_zone)
        self.sep_horiz.setObjectName("TrayHorizSeparator")
        self.sep_horiz.setFrameShape(QFrame.Shape.HLine)
        self.sep_horiz.setFixedHeight(2)
        right_vbox.addWidget(self.sep_horiz)

        # ---------------------------------------------------------------------
        # FR: ÉTAGE INFÉRIEUR (Y = 480..528) :
        # EN: LOWER TIER (Y = 480..528):
        # [⬆ Importer (Web)]  [✉ E-mail] [🖨 Imprimer] [📁 Exporter] [⊞ Montage] [🎬 Film]  [⚙]
        # Ref: thumbui/webupload (296..437, 141x35) + outputlayout (55x36 cells)
        # ---------------------------------------------------------------------
        lower_strip = QHBoxLayout()
        lower_strip.setContentsMargins(0, 0, 0, 0)
        lower_strip.setSpacing(6)

        self.action_buttons_container = QWidget(right_zone)
        self.action_buttons_layout = QHBoxLayout(self.action_buttons_container)
        self.action_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.action_buttons_layout.setSpacing(6)

        self.btn_upload = QPushButton("⬆ Partager")
        self.btn_upload.setObjectName("GreenUploadBtn")
        self.btn_upload.setFixedHeight(34)
        self.btn_upload.setToolTip("Partager / Importer vers Google Photos / Web")
        self.btn_upload.clicked.connect(self.upload_requested.emit)
        self.action_buttons_layout.addWidget(self.btn_upload)

        self.btn_email = QPushButton("✉ E-mail")
        self.btn_email.setObjectName("OutputBtn")
        self.btn_email.setFixedHeight(34)
        self.btn_email.setToolTip("Envoyer les photos sélectionnées par e-mail (Ctrl+E)")
        self.btn_email.clicked.connect(self.action_email.emit)
        self.action_buttons_layout.addWidget(self.btn_email)

        self.btn_print = QPushButton("🖨 Imprimer")
        self.btn_print.setObjectName("OutputBtn")
        self.btn_print.setFixedHeight(34)
        self.btn_print.setToolTip("Imprimer les photos sélectionnées (Ctrl+P)")
        self.btn_print.clicked.connect(self.action_print.emit)
        self.action_buttons_layout.addWidget(self.btn_print)

        self.btn_export = QPushButton("📁 Exporter")
        self.btn_export.setObjectName("OutputBtn")
        self.btn_export.setFixedHeight(34)
        self.btn_export.setToolTip("Exporter les photos sélectionnées vers un dossier (Ctrl+Maj+S)")
        self.btn_export.clicked.connect(self.action_export.emit)
        self.action_buttons_layout.addWidget(self.btn_export)

        self.btn_collage = QPushButton("⊞ Montage")
        self.btn_collage.setObjectName("OutputBtn")
        self.btn_collage.setFixedHeight(34)
        self.btn_collage.setToolTip("Créer un montage photo avec la sélection")
        self.btn_collage.clicked.connect(self.action_collage.emit)
        self.action_buttons_layout.addWidget(self.btn_collage)

        self.btn_movie = QPushButton("🎬 Film")
        self.btn_movie.setObjectName("OutputBtn")
        self.btn_movie.setFixedHeight(34)
        self.btn_movie.setToolTip("Créer un film vidéo ou diaporama avec la sélection")
        self.btn_movie.clicked.connect(self.action_movie.emit)
        self.action_buttons_layout.addWidget(self.btn_movie)

        self._action_button_map = {
            "upload": self.btn_upload,
            "email": self.btn_email,
            "print": self.btn_print,
            "export": self.btn_export,
            "collage": self.btn_collage,
            "movie": self.btn_movie,
        }
        self._active_button_keys: List[str] = list(self._action_button_map.keys())
        lower_strip.addWidget(self.action_buttons_container)

        lower_strip.addStretch(1)

        self.btn_configure_buttons = QPushButton("⚙")
        self.btn_configure_buttons.setFixedSize(28, 34)
        self.btn_configure_buttons.setToolTip("Configurer les boutons (outputlayout/morebutton)...")
        self.btn_configure_buttons.clicked.connect(self.open_button_manager)
        lower_strip.addWidget(self.btn_configure_buttons)

        right_vbox.addLayout(lower_strip)
        root_h.addWidget(right_zone, 64)

        self._is_starred: bool = False
        self.set_selected_count(0)
        self.apply_style(self.style)

    def apply_button_configuration(self, keys: List[str]) -> None:
        """
        FR: Met à jour la visibilité et l'ordre des boutons d'action du plateau.
        EN: Updates the visibility and order of the tray action buttons.
        Ref: runtime/BUTTONMGR_TEXT_FR.XML
        """
        valid_keys = [k for k in keys if k in self._action_button_map]
        self._active_button_keys = valid_keys
        for btn in self._action_button_map.values():
            self.action_buttons_layout.removeWidget(btn)
            btn.hide()
        for k in valid_keys:
            btn = self._action_button_map[k]
            self.action_buttons_layout.addWidget(btn)
            btn.show()

    def open_button_manager(self) -> None:
        """
        FR: Ouvre le dialogue « Configurer les boutons » (BUTTONMGR_TEXT_FR.XML).
        EN: Opens the "Configure Buttons" dialog (BUTTONMGR_TEXT_FR.XML).
        """
        dlg = PicasaButtonManagerDialog(self._active_button_keys, self.window())
        if dlg.exec():
            self.apply_button_configuration(dlg.get_active_keys())

    def _toggle_hold(self) -> None:
        """
        FR: Active ou désactive le mode 'Hold' (maintien du bac à photos).
        EN: Toggles the 'Hold' mode (retaining items in the photo tray).
        """
        self.is_held = not self.is_held
        self.btn_hold.blockSignals(True)
        self.btn_hold.setChecked(self.is_held)
        self.btn_hold.blockSignals(False)
        if self.is_held:
            self.btn_hold.setText("📌")
            self.btn_hold.setObjectName("HeldBtn")
            self.btn_hold.setStyleSheet("background-color: #2E5C38; border: 1px solid #4CAF50; color: #FFFFFF;")
            self.held_items = list(self.active_items)
        else:
            self.btn_hold.setText("📌")
            self.btn_hold.setObjectName("TrayStackBtn")
            self.btn_hold.setStyleSheet("")
            self.held_items.clear()

        self.thumb_strip.set_items(self.get_effective_items(), is_held=self.is_held)
        self.action_hold.emit(self.is_held)

    def _on_clear_clicked(self) -> None:
        """
        FR: Vide le bac à photos et réinitialise l'état Hold.
        EN: Clears the photo tray and resets the Hold state.
        """
        self.is_held = False
        self.btn_hold.blockSignals(True)
        self.btn_hold.setChecked(False)
        self.btn_hold.blockSignals(False)
        self.btn_hold.setText("📌")
        self.btn_hold.setObjectName("TrayStackBtn")
        self.btn_hold.setStyleSheet("")
        self.held_items.clear()
        self.active_items.clear()
        self.set_selected_items([])
        self.action_clear.emit()

    def _on_remove_item(self, item: Any) -> None:
        """
        FR: Supprime une photo individuelle du bac.
        EN: Removes an individual photo from the tray.
        """
        if item in self.held_items:
            self.held_items.remove(item)
        if item in self.active_items:
            self.active_items.remove(item)
        self.thumb_strip.set_items(self.get_effective_items(), is_held=self.is_held)
        self.set_selected_count(len(self.get_effective_items()))

    def get_effective_items(self) -> List[Any]:
        """
        FR: Renvoie les éléments actifs du bac en évitant les doublons.
        EN: Returns the active items in the tray while avoiding duplicates.
        """
        if self.is_held:
            seen = set()
            combined = []
            for it in self.held_items + self.active_items:
                p = getattr(it, "path", None) or str(it)
                if p not in seen:
                    seen.add(p)
                    combined.append(it)
            return combined
        return list(self.active_items)

    def set_selected_items(self, items: List[Any]) -> None:
        """
        FR: Met à jour les éléments sélectionnés et affiche les miniatures.
        EN: Updates the selected items and displays their thumbnails.
        """
        self.active_items = list(items)
        effective = self.get_effective_items()
        self.thumb_strip.set_items(effective, is_held=self.is_held)
        self.set_selected_count(len(effective))

        # FR: État du bouton favori
        # EN: Star button state
        any_starred = bool(effective) and any(getattr(it, "starred", False) for it in effective)
        self.update_star_state(any_starred)

    def update_star_state(self, is_starred: bool) -> None:
        """
        FR: Met à jour l'apparence du bouton Favori selon l'état des photos et le thème actif.
        EN: Updates the Star button appearance according to the photos' state and active theme.
        """
        self._is_starred = is_starred
        if not hasattr(self, "btn_star"):
            return
        if is_starred:
            self.btn_star.setText("★")
            star_bg = "#3D3520" if self.style.is_dark else "#FFF8E1"
            star_col = "#FFD700" if self.style.is_dark else "#D97706"
            star_hov = "#4D4228" if self.style.is_dark else "#FFECB3"
            self.btn_star.setStyleSheet(f"""
                QPushButton#StarBtn {{
                    background-color: {star_bg};
                    color: {star_col};
                    border: 1px solid #FFC107;
                    font-size: 14px;
                    padding: 2px;
                    border-radius: 3px;
                }}
                QPushButton#StarBtn:hover {{
                    background-color: {star_hov};
                }}
            """)
        else:
            self.btn_star.setText("☆")
            self.btn_star.setStyleSheet("")

    def update_panel_buttons(self, is_open: bool, current_panel: str) -> None:
        """
        FR: Met à jour l'état enfoncé des 4 boutons bascule du tiroir droit.
        EN: Updates the checked state of the 4 right-drawer toggle buttons.
        """
        self.btn_panel_people.setChecked(is_open and current_panel == "people")
        self.btn_panel_places.setChecked(is_open and current_panel == "places")
        self.btn_panel_tags.setChecked(is_open and current_panel == "tags")
        self.btn_panel_props.setChecked(is_open and current_panel == "properties")

    def set_selected_count(self, count: int) -> None:
        """
        FR: Met à jour le compteur de sélection affiché et l'activation des boutons d'action.
        EN: Updates the displayed selection count and the enabled state of action buttons.
        """
        enabled = count > 0
        if count == 0:
            self.lbl_selection.setText("Aucune photo sélectionnée")
        elif count == 1:
            self.lbl_selection.setText("1 photo sélectionnée")
        else:
            self.lbl_selection.setText(f"{count} photos sélectionnées")

        self.btn_export.setEnabled(enabled)
        self.btn_print.setEnabled(enabled)
        self.btn_email.setEnabled(enabled)
        self.btn_add_to_album.setEnabled(enabled)
        self.btn_collage.setEnabled(enabled)
        self.btn_movie.setEnabled(enabled)
        self.btn_star.setEnabled(enabled)
        self.btn_rotate_left.setEnabled(enabled)
        self.btn_rotate_right.setEnabled(enabled)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs au plateau inférieur.
        EN: Dynamically applies the color theme to the bottom photo tray.
        """
        if style is None:
            style = PicasaStyle.instance()
        self.style = style
        tray_bg = style.tray_bgcolor.name()
        scratch_bg = style.tray_grad_end.darker(112).name() if style.is_dark else style.tray_grad_end.lighter(104).name()
        btn_start = style.tray_grad_start.name() if style.is_dark else style.topbar_btn_bg_start.name()
        btn_end = style.tray_grad_end.name() if style.is_dark else style.topbar_btn_bg_end.name()
        btn_border = "#555B66" if style.is_dark else style.topbar_btn_border.name()
        txt_col = style.tray_text_color.name()
        sub_txt = "#B0B8C4" if style.is_dark else style.alayout_subtitleColor.name()
        dis_txt = "#777C85" if style.is_dark else "#8E8E8E"
        dis_bg = "#2E3138" if style.is_dark else style.window_bgcolor.darker(104).name()
        dis_border = "#3E424B" if style.is_dark else style.splitter_color.name()
        top_border = "#1E2024" if style.is_dark else style.topbar_border_color.name()
        sep_top = "#202328" if style.is_dark else style.splitter_color.name()
        sep_bot = "#454A54" if style.is_dark else "#FFFFFF"
        accent = style.accent_color.name()

        if hasattr(self, "thumb_strip") and self.thumb_strip:
            self.thumb_strip.apply_style(style)
        if hasattr(self, "btn_star"):
            self.update_star_state(getattr(self, "_is_starred", False))

        self.setStyleSheet(f"""
            QWidget#TrayRoot {{
                background-color: {tray_bg};
                border-top: 1px solid {top_border};
            }}
            QLabel#TraySelectionLabel {{
                color: {sub_txt};
                font-size: 10px;
                font-weight: bold;
                padding-left: 2px;
            }}
            QFrame#TrayHorizSeparator {{
                background-color: {sep_top};
                border-bottom: 1px solid {sep_bot};
            }}
            QFrame#ScratchPadBase {{
                background-color: {scratch_bg};
                border: 1px solid {top_border};
                border-radius: 4px;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_start}, stop:1 {btn_end});
                color: {txt_col};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {accent};
            }}
            QPushButton:pressed, QPushButton:checked {{
                background-color: {accent};
                color: #FFFFFF;
                border-color: {accent};
            }}
            QPushButton:disabled {{
                color: {dis_txt};
                background-color: {dis_bg};
                border-color: {dis_border};
            }}
            QPushButton#GreenUploadBtn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5CB85C, stop:1 #3D8B3D);
                border: 1px solid #2D672D;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 12px;
            }}
            QPushButton#GreenUploadBtn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6EC46E, stop:1 #489B48);
            }}
            QPushButton#OutputBtn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_start}, stop:1 {btn_end});
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
                color: {txt_col};
            }}
            QPushButton#OutputBtn:hover {{
                border-color: {accent};
            }}
            QPushButton#OutputBtn:disabled {{
                color: {dis_txt};
                background: {dis_bg};
                border-color: {dis_border};
            }}
            QPushButton#TrayStackBtn {{
                padding: 1px 4px;
                font-size: 10px;
                border-radius: 2px;
            }}
            QLabel {{
                color: {txt_col};
                font-size: 11px;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: {btn_border};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }}
        """)
        self.update()

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les libellés du bac à photos selon la langue active.
        EN: Updates the photo tray labels according to the active language.
        """
        rm = PicasaResourceManager.get()
        if hasattr(self, "thumb_strip") and hasattr(self.thumb_strip, "watermark_label"):
            self.thumb_strip.watermark_label.setText(rm.get_xml_string("thumbui/scratchlabel", "Sélection"))
        self.btn_panel_people.setText("")
        self.btn_panel_people.setToolTip(rm.get_xml_string("thumbui/people_toggle.tooltip", "Afficher/masquer le panneau Personnes"))
        self.btn_panel_places.setText("")
        self.btn_panel_places.setToolTip(rm.get_xml_string("thumbui/places_toggle.tooltip", "Afficher/Masquer le panneau Lieux"))
        self.btn_panel_tags.setText("")
        self.btn_panel_tags.setToolTip(rm.get_xml_string("thumbui/tags_toggle.tooltip", "Afficher/Masquer le panneau Tags"))
        self.btn_panel_props.setText("")
        self.btn_panel_props.setToolTip(rm.get_xml_string("thumbui/properties_toggle.tooltip", "Afficher/Masquer le panneau Propriétés"))
        self.btn_email.setText(f"✉ {rm.get_xml_string('outputlayout/email', 'E-mail')}")
        self.btn_print.setText(f"🖨 {rm.get_xml_string('outputlayout/print', 'Imprimer')}")
        self.btn_export.setText(f"📁 {rm.get_xml_string('outputlayout/export', 'Exporter')}")
        self.btn_collage.setText(f"⊞ {rm.get_xml_string('outputlayout/collage', 'Montage')}")
        self.btn_movie.setText(f"🎬 {rm.get_xml_string('outputlayout/movie', 'Film')}")
        self.set_selected_count(len(self.get_effective_items()))
