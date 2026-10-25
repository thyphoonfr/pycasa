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
from typing import List, Optional, Any, Tuple, Set
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QPushButton, QLabel, QSlider, QFrame,
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


_ACTIVE_TRAY_DB: Optional[Any] = None


def _resolve_item_pixmap(item: Any, db: Optional[Any] = None) -> Optional[QPixmap]:
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

    # FR: 1 bis. Essayer depuis la miniature en mémoire de PicasaDatabase (< 0,2 ms)
    # EN: 1 bis. Try from PicasaDatabase in-memory thumbnail (< 0.2 ms)
    eff_db = db or getattr(item, "_db", None) or _ACTIVE_TRAY_DB
    item_idx = getattr(item, "index", -1)
    if eff_db is not None and isinstance(item_idx, int) and item_idx >= 0 and hasattr(eff_db, "get_thumbnail"):
        try:
            from PySide6.QtGui import QImage
            raw_db = eff_db.get_thumbnail(item_idx, size="small") or eff_db.get_thumbnail(item_idx, size="large")
            if raw_db:
                qimg_db = QImage.fromData(raw_db)
                if not qimg_db.isNull():
                    p_db = QPixmap.fromImage(qimg_db)
                    if not p_db.isNull():
                        try:
                            setattr(item, "pixmap", p_db)
                        except Exception:
                            pass
                        return p_db
        except Exception:
            pass

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
    FR: Vignette individuelle miniature au sein du bac à photos (`thumbui/scratch`, `CSelectionNode` @ `0x00714990`).
    Reproduit le comportement exact désassemblé dans `CSelectionNode::HandleMouseAndKeyMessage` (`0x007199B0`) :
    - Clic gauche simple (`WM_LBUTTONDOWN` @ `0x00719C37`) : sélectionne/focalise la miniature dans le bac
      (avec support `Ctrl` et `Shift`) sans jamais supprimer les autres miniatures du bac (`0x00570C62`).
    - Double-clic gauche (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`) : ouvre la photo en mode Édition
      (`thumbui/fullview`) tout en conservant toutes les miniatures dans le bac.
    - Clic droit (`WM_RBUTTONDOWN` @ `0x00719ACE` -> `0x00732EE0`) : ouvre le menu contextuel à 7 entrées du bac.
    EN: Individual miniature thumbnail widget inside the Picture Tray (`thumbui/scratch`, `CSelectionNode` @ `0x00714990`).
    Reproduces the exact disassembled behavior in `CSelectionNode::HandleMouseAndKeyMessage` (`0x007199B0`):
    - Single left-click (`WM_LBUTTONDOWN` @ `0x00719C37`): selects/focuses the thumbnail in the tray
      (with `Ctrl` and `Shift` support) without ever removing other thumbnails from the tray (`0x00570C62`).
    - Double left-click (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`): opens the photo in Edit mode
      (`thumbui/fullview`) while keeping all thumbnails in the tray.
    - Right-click (`WM_RBUTTONDOWN` @ `0x00719ACE` -> `0x00732EE0`): opens the 7-item tray context menu.
    Ref: picasa3.exe @ 0x00714990, 0x007199B0, 0x0071DAC0, 0x0056BFD0, 0x00732EE0
    """
    clicked = Signal(object)
    clicked_with_modifiers = Signal(object, object)
    double_clicked = Signal(object)
    context_menu_requested = Signal(object, QPoint)
    remove_clicked = Signal(object)

    def __init__(
        self,
        item: Any,
        is_held: bool = False,
        is_selected: bool = False,
        is_focused: bool = False,
        cell_size: int = 46,
        parent: Optional[QWidget] = None,
    ):
        """
        FR: Initialise la vignette d'un élément dans le bac à photos.
        EN: Initializes an item thumbnail widget in the photo tray.
        """
        super().__init__(parent)
        self.item = item
        self.is_held: bool = is_held
        self.is_selected: bool = is_selected
        self.is_focused: bool = is_focused
        self.is_hovered: bool = False
        self.cell_size: int = max(16, int(cell_size))

        self.setFixedSize(self.cell_size, self.cell_size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        fname = getattr(item, "filename", "") or os.path.basename(getattr(item, "path", ""))
        self.setToolTip(
            f"{fname}\n(Clic : sélectionner, Double-clic : modifier, Clic droit : menu)"
        )

    def set_cell_size(self, cell_size: int) -> None:
        """
        FR: Met à jour la taille de la cellule selon l'algorithme `LayoutMode9` (`0x0071DAC0`).
        EN: Updates the cell size according to the `LayoutMode9` (`0x0071DAC0`) algorithm.
        """
        new_sz = max(16, int(cell_size))
        if new_sz != self.cell_size:
            self.cell_size = new_sz
            self.setFixedSize(self.cell_size, self.cell_size)
            self.update()

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
        FR: Gère le clic gauche (`WM_LBUTTONDOWN` @ `0x00719C37` : sélection interne au bac sans suppression)
        et le clic droit (`WM_RBUTTONDOWN` @ `0x00719ACE` -> menu contextuel `0x00732EE0`).
        EN: Handles left-click (`WM_LBUTTONDOWN` @ `0x00719C37`: in-tray selection without removal)
        and right-click (`WM_RBUTTONDOWN` @ `0x00719ACE` -> context menu `0x00732EE0`).
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_with_modifiers.emit(self.item, event.modifiers())
            self.clicked.emit(self.item)
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(self.item, event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le double-clic gauche (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`) pour basculer
        en mode Édition (`thumbui/fullview`) tout en conservant toutes les miniatures dans le bac.
        EN: Handles double left-click (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`) to switch
        to Edit mode (`thumbui/fullview`) while keeping all thumbnails in the tray.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine la miniature, son cadre blanc de tirage photo, la bordure de sélection (`#009EFF`)
        et l'indicateur vert de maintien (`Hold` @ `[pItem + 0xBC]`).
        EN: Paints the thumbnail, its white photo-print border, selection border (`#009EFF`),
        and green Hold indicator (`Hold` @ `[pItem + 0xBC]`).
        Ref: picasa3.exe @ 0x00714990, 0x0071DAC0, 0x0088C3EC
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        sz = self.cell_size
        pad = 2 if sz >= 28 else 1
        inner_box = max(8, sz - 2 * pad)
        rect = QRect(pad, pad, inner_box, inner_box)
        painter.fillRect(rect, QColor("#22252A"))

        img_max = max(6, inner_box - (4 if sz >= 28 else 2))
        cache_attr = f"_tray_scaled_{img_max}"
        scaled = getattr(self.item, cache_attr, None)
        if not isinstance(scaled, QPixmap) or scaled.isNull():
            pix = _resolve_item_pixmap(self.item)
            if pix and not pix.isNull():
                scaled = pix.scaled(
                    img_max,
                    img_max,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                try:
                    setattr(self.item, cache_attr, scaled)
                except Exception:
                    pass
        if scaled and not scaled.isNull():
            x_off = pad + (inner_box - scaled.width()) // 2
            y_off = pad + (inner_box - scaled.height()) // 2
            frame_r = QRect(x_off - 1, y_off - 1, scaled.width() + 2, scaled.height() + 2)
            painter.fillRect(frame_r, QColor("#FFFFFF"))
            painter.drawPixmap(x_off, y_off, scaled)
        else:
            painter.setPen(QColor("#777E8C"))
            painter.setFont(QFont("Segoe UI", max(7, sz // 4)))
            is_vid = getattr(self.item, "is_video", False)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎬" if is_vid else "🖼️")

        # FR: 3. Bordure selon état (Sélectionné/Focalisé dans le bac `#009EFF`, Survol `#3D85B3`, Maintenu `#4CAF50`, Normal)
        # EN: 3. Border according to state (Selected/Focused in tray `#009EFF`, Hover `#3D85B3`, Held `#4CAF50`, Normal)
        if self.is_selected or self.is_focused:
            pen = QPen(QColor("#009EFF"), 2.0)
        elif self.is_hovered:
            pen = QPen(QColor("#3D85B3"), 1.6)
        elif self.is_held:
            pen = QPen(QColor("#4CAF50"), 1.6)
        else:
            pen = QPen(QColor("#D0D4DC"), 1.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        # FR: 4. Indicateur d'épingle verte si l'élément est maintenu (`holdCount > 0` @ `[pItem + 0xBC]`)
        # EN: 4. Green pin indicator if item is held (`holdCount > 0` @ `[pItem + 0xBC]`)
        if self.is_held:
            if sz >= 28:
                pin_r = QRect(pad + 1, pad + 1, 10, 10)
                painter.setPen(QColor("#4CAF50"))
                painter.setFont(QFont("Segoe UI Emoji", 7))
                painter.drawText(pin_r, Qt.AlignmentFlag.AlignCenter, "📌")
            else:
                painter.fillRect(QRect(pad + 1, pad + 1, 5, 5), QColor("#4CAF50"))


class PicasaTrayThumbnailStackWidget(QWidget):
    """
    FR: Widget conservé pour compatibilité ascendante des imports éventuels.
    Dans `picasa3.exe` (`CSelectionNode::LayoutMode9` @ `0x0071DAC0`), `thumbui/scratch` utilise
    une grille multi-colonnes / multi-lignes auto-réductrice où chaque miniature reste visible.
    EN: Widget retained for backward import compatibility.
    In `picasa3.exe` (`CSelectionNode::LayoutMode9` @ `0x0071DAC0`), `thumbui/scratch` uses
    an auto-scaling multi-column / multi-row grid where every thumbnail remains individually visible.
    """
    clicked = Signal(object)
    double_clicked = Signal(object)
    remove_clicked = Signal(object)

    def __init__(self, items: List[Any], is_held: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.items = list(items)
        self.is_held = is_held


class PicasaTrayThumbnailStrip(QScrollArea):
    """
    FR: Conteneur de miniatures du bac de sélection (`thumbui/scratch`, `CSelectionNode` @ `0x00714990`),
    avec filigrane « Sélection » (`thumbui/scratchlabel`) lorsqu'il est vide, et mise en page
    en grille adaptative multi-lignes / multi-colonnes fidèle à `CSelectionNode::LayoutMode9` (`0x0071DAC0`).
    Chaque miniature reste individuellement visible, cliquable (sélection dans le bac sans vider les autres),
    double-cliquable (passage en Édition One-Up) et cliquable avec le bouton droit (menu contextuel du bac).
    EN: Selection tray thumbnail container (`thumbui/scratch`, `CSelectionNode` @ `0x00714990`),
    with "Selection" watermark (`thumbui/scratchlabel`) when empty, and adaptive multi-row / multi-column
    grid layout faithful to `CSelectionNode::LayoutMode9` (`0x0071DAC0`).
    Every thumbnail remains individually visible, clickable (in-tray selection without clearing others),
    double-clickable (switches to One-Up Edit mode), and right-clickable (tray context menu).
    Ref: respack.yt @ thumbui/scratch (rect 8, 455, 223, 515), thumbui/scratchlabel (rect 13, 480, 218, 499)
    Ref: picasa3.exe @ 0x00714990, 0x007199B0, 0x0071DAC0, 0x005709A0, 0x0056BFD0, 0x00732EE0
    """
    item_clicked = Signal(object)
    item_double_clicked = Signal(object)
    item_context_menu_requested = Signal(object, QPoint)
    item_remove_requested = Signal(object)
    subselection_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le conteneur de miniatures `thumbui/scratch` et son filigrane « Sélection ».
        EN: Initializes the `thumbui/scratch` thumbnail container and its "Selection" watermark.
        """
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setMinimumWidth(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setStyleSheet("""
            QScrollArea {
                background: #23262C;
                border: 1px solid #17191D;
                border-bottom: 1px solid #3C414B;
                border-right: 1px solid #3C414B;
                border-radius: 3px;
            }
            QScrollBar:horizontal, QScrollBar:vertical {
                height: 4px;
                width: 4px;
                background: #1D2025;
                border: none;
            }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
                background: #555B66;
                border-radius: 2px;
                min-width: 16px;
                min-height: 12px;
            }
        """)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout_h = QHBoxLayout(self.container)
        self.layout_h.setContentsMargins(3, 3, 3, 3)
        self.layout_h.setSpacing(2)

        # FR: Filigrane « Sélection » (thumbui/scratchlabel) affiché quand le bac est vide
        # EN: "Selection" watermark (thumbui/scratchlabel) displayed when the tray is empty
        self.watermark_label = QLabel("Sélection", self.container)
        self.watermark_label.setStyleSheet(
            "color: #555B66; font-size: 13px; font-weight: bold; font-style: italic; padding-left: 8px;"
        )
        self.layout_h.addWidget(self.watermark_label)

        self.grid_host = QWidget(self.container)
        self.grid_host.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(2)
        self.grid_layout.setVerticalSpacing(2)
        self.layout_h.addWidget(self.grid_host)
        self.layout_h.addStretch(1)

        self.setWidget(self.container)
        self.items: List[Any] = []
        self.item_widgets: List[PicasaTrayThumbnailItemWidget] = []
        self.is_held: bool = False
        self.held_paths: Set[str] = set()
        # FR: Sous-sélection interne au bac (`[pItem + 0x5D]` et `focusedItemId` @ `[this + 0x390]`)
        # EN: In-tray sub-selection (`[pItem + 0x5D]` and `focusedItemId` @ `[this + 0x390]`)
        self.selected_paths: Set[str] = set()
        self.focused_path: Optional[str] = None
        self.anchor_idx: int = -1

    @staticmethod
    def _item_key(item: Any) -> str:
        p = getattr(item, "path", None)
        return str(p) if p else f"id:{id(item)}"

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
            QScrollBar:horizontal, QScrollBar:vertical {{
                height: 4px;
                width: 4px;
                background: {strip_bg};
                border: none;
            }}
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {{
                background: {style.topbar_btn_border.name()};
                border-radius: 2px;
                min-width: 16px;
                min-height: 12px;
            }}
        """)
        self.watermark_label.setStyleSheet(
            f"color: {wm_color}; font-size: 13px; font-weight: bold; font-style: italic; padding-left: 8px;"
        )

    def _compute_layout_mode_9(self, n_items: int) -> Tuple[int, int]:
        """
        FR: Calcule `(cell_size, cols)` selon l'algorithme exact `CSelectionNode::LayoutMode9` (`0x0071DAC0`) :
        décrémente la taille de cellule `cell_sz` depuis `46px` jusqu'à ce que toutes les lignes
        `rows = ceil(n_items / cols)` tiennent dans la hauteur du bac (`avail_h`), avec un plancher
        lisible de `18px` pour que chaque miniature reste individuellement visible et cliquable.
        EN: Computes `(cell_size, cols)` following the exact `CSelectionNode::LayoutMode9` (`0x0071DAC0`) algorithm:
        decrements `cell_sz` from `46px` until all rows `rows = ceil(n_items / cols)` fit within the tray
        height (`avail_h`), with a readable floor of `18px` so every thumbnail stays visible and clickable.
        Ref: picasa3.exe @ 0x0071DAC0 (LayoutMode9)
        """
        if n_items <= 0:
            return 46, 1
        avail_w = max(180, (self.viewport().width() if self.viewport() else self.width()) - 8)
        avail_h = max(48, (self.viewport().height() if self.viewport() else self.height()) - 6)
        gap = 2
        for cell_sz in range(46, 17, -1):
            cols = max(1, (avail_w + gap) // (cell_sz + gap))
            rows = (n_items + cols - 1) // cols
            if rows * (cell_sz + gap) - gap <= avail_h:
                return cell_sz, cols
        cell_sz = 18
        cols = max(1, (avail_w + gap) // (cell_sz + gap))
        return cell_sz, cols

    def set_items(
        self,
        items: List[Any],
        is_held: bool = False,
        held_paths: Optional[Set[str]] = None,
    ) -> None:
        """
        FR: Met à jour les éléments affichés dans le bac (`thumbui/scratch`) sous forme de grille
        de vignettes individuelles (`LayoutMode9` @ `0x0071DAC0`).
        EN: Updates the items displayed in the tray (`thumbui/scratch`) as a grid of individual
        thumbnails (`LayoutMode9` @ `0x0071DAC0`).
        """
        self.items = list(items)
        self.is_held = is_held
        if held_paths is not None:
            self.held_paths = set(held_paths)
        elif is_held:
            self.held_paths = {self._item_key(it) for it in self.items}
        else:
            self.held_paths.clear()

        valid_keys = {self._item_key(it) for it in self.items}
        self.selected_paths &= valid_keys
        if self.focused_path not in valid_keys:
            self.focused_path = self._item_key(self.items[0]) if self.items else None

        for w in self.item_widgets:
            self.grid_layout.removeWidget(w)
            w.deleteLater()
        self.item_widgets.clear()

        has_items = len(self.items) > 0
        self.watermark_label.setVisible(not has_items)
        self.grid_host.setVisible(has_items)
        if not has_items:
            return

        cell_sz, cols = self._compute_layout_mode_9(len(self.items))
        for idx, it in enumerate(self.items):
            key = self._item_key(it)
            it_held = self.is_held or (key in self.held_paths)
            it_sel = key in self.selected_paths
            it_foc = (key == self.focused_path) and (len(self.selected_paths) <= 1)
            w = PicasaTrayThumbnailItemWidget(
                it,
                is_held=it_held,
                is_selected=it_sel,
                is_focused=it_foc,
                cell_size=cell_sz,
                parent=self.grid_host,
            )
            w.clicked_with_modifiers.connect(self._on_widget_clicked_with_modifiers)
            w.double_clicked.connect(self._on_widget_double_clicked)
            w.context_menu_requested.connect(self._on_widget_context_menu)
            w.remove_clicked.connect(self.item_remove_requested.emit)
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(w, row, col)
            self.item_widgets.append(w)

    def resizeEvent(self, event: Any) -> None:
        """
        FR: Recalcule la grille `LayoutMode9` (`0x0071DAC0`) lors du redimensionnement du bac.
        EN: Recomputes the `LayoutMode9` (`0x0071DAC0`) grid when the tray is resized.
        """
        super().resizeEvent(event)
        if self.item_widgets and self.items:
            cell_sz, cols = self._compute_layout_mode_9(len(self.items))
            for idx, w in enumerate(self.item_widgets):
                w.set_cell_size(cell_sz)
                self.grid_layout.removeWidget(w)
                self.grid_layout.addWidget(w, idx // cols, idx % cols)

    def _sync_widget_states(self) -> None:
        """
        FR: Rafraîchit les états visuels (`is_selected`, `is_focused`, `is_held`) de chaque miniature du bac.
        EN: Refreshes the visual states (`is_selected`, `is_focused`, `is_held`) of each tray thumbnail.
        """
        for w in self.item_widgets:
            key = self._item_key(w.item)
            w.is_held = self.is_held or (key in self.held_paths)
            w.is_selected = key in self.selected_paths
            w.is_focused = (key == self.focused_path)
            w.update()

    def set_focused_path(self, path: Optional[str], select_only_focused: bool = False) -> None:
        """
        FR: Met en évidence la miniature correspondant à `path` dans le bac (`focusedItemId` @ `[this + 0x390]`).
        EN: Highlights the thumbnail matching `path` in the tray (`focusedItemId` @ `[this + 0x390]`).
        """
        if not path:
            self.focused_path = None
            if select_only_focused:
                self.selected_paths.clear()
            self._sync_widget_states()
            return
        norm_target = os.path.normcase(os.path.normpath(path))
        matched_key: Optional[str] = None
        for idx, it in enumerate(self.items):
            k = self._item_key(it)
            if k == path or os.path.normcase(os.path.normpath(k)) == norm_target:
                matched_key = k
                self.anchor_idx = idx
                break
        if matched_key is not None:
            self.focused_path = matched_key
            if select_only_focused:
                self.selected_paths = {matched_key}
            self._sync_widget_states()

    def _on_widget_clicked_with_modifiers(self, item: Any, modifiers: Any) -> None:
        """
        FR: Gère le clic gauche simple sur une miniature du bac (`WM_LBUTTONDOWN` @ `0x00719C37..0x00719DA2`) :
        - Sans modificateur : sélectionne uniquement cette miniature à l'intérieur du bac (`selected_paths = {key}`)
          sans retirer aucune autre miniature du bac (`0x00570C62`).
        - `Ctrl+Clic` : inverse la sous-sélection de cette miniature dans le bac (`0x00719CC3`).
        - `Shift+Clic` : sélectionne la plage continue depuis `anchor_idx` dans le bac (`0x00719C9C`).
        EN: Handles single left-click on a tray thumbnail (`WM_LBUTTONDOWN` @ `0x00719C37..0x00719DA2`).
        """
        key = self._item_key(item)
        clicked_idx = next((i for i, it in enumerate(self.items) if self._item_key(it) == key), -1)

        if modifiers & Qt.KeyboardModifier.ShiftModifier and 0 <= self.anchor_idx < len(self.items) and clicked_idx >= 0:
            lo = min(self.anchor_idx, clicked_idx)
            hi = max(self.anchor_idx, clicked_idx)
            if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                self.selected_paths.clear()
            for i in range(lo, hi + 1):
                self.selected_paths.add(self._item_key(self.items[i]))
            self.focused_path = key
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            if key in self.selected_paths and len(self.selected_paths) > 1:
                self.selected_paths.remove(key)
            else:
                self.selected_paths.add(key)
            self.focused_path = key
            if clicked_idx >= 0:
                self.anchor_idx = clicked_idx
        else:
            self.selected_paths = {key}
            self.focused_path = key
            if clicked_idx >= 0:
                self.anchor_idx = clicked_idx

        self._sync_widget_states()
        self.subselection_changed.emit()
        self.item_clicked.emit(item)

    def _on_widget_double_clicked(self, item: Any) -> None:
        """
        FR: Gère le double-clic gauche sur une miniature du bac (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`) :
        focalise la miniature et demande le basculement en mode Édition (`thumbui/fullview`).
        EN: Handles double left-click on a tray thumbnail (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`):
        focuses the thumbnail and requests switching to Edit mode (`thumbui/fullview`).
        """
        key = self._item_key(item)
        self.selected_paths = {key}
        self.focused_path = key
        self._sync_widget_states()
        self.subselection_changed.emit()
        self.item_double_clicked.emit(item)

    def _on_widget_context_menu(self, item: Any, global_pos: QPoint) -> None:
        """
        FR: Gère le clic droit sur une miniature du bac (`WM_RBUTTONDOWN` @ `0x00719ACE` -> `0x00732EE0`) :
        si la miniature n'est pas déjà dans la sous-sélection du bac, la sélectionne sans retirer les autres,
        puis ouvre le menu contextuel du bac.
        EN: Handles right-click on a tray thumbnail (`WM_RBUTTONDOWN` @ `0x00719ACE` -> `0x00732EE0`).
        """
        key = self._item_key(item)
        if key not in self.selected_paths:
            self.selected_paths = {key}
            self.focused_path = key
            clicked_idx = next((i for i, it in enumerate(self.items) if self._item_key(it) == key), -1)
            if clicked_idx >= 0:
                self.anchor_idx = clicked_idx
            self._sync_widget_states()
            self.subselection_changed.emit()
            self.item_clicked.emit(item)
        else:
            self.focused_path = key
            self._sync_widget_states()
        self.item_context_menu_requested.emit(item, global_pos)

    def get_subselected_items(self) -> List[Any]:
        """
        FR: Retourne les éléments actuellement sous-sélectionnés dans le bac (ou tous si aucun n'est sous-sélectionné).
        EN: Returns the items currently sub-selected inside the tray (or all items if none is sub-selected).
        """
        if self.selected_paths:
            sub = [it for it in self.items if self._item_key(it) in self.selected_paths]
            if sub:
                return sub
        if self.focused_path:
            foc = [it for it in self.items if self._item_key(it) == self.focused_path]
            if foc:
                return foc
        return list(self.items)


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
    oneup_zoom_changed = Signal(int)
    oneup_fit_requested = Signal()
    oneup_zoom_1to1_requested = Signal()
    oneup_faces_toggled = Signal(bool)
    toggle_left_drawer_requested = Signal()
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
    action_thumbnail_double_clicked = Signal(object)
    tray_context_action_requested = Signal(str, list)
    panel_toggled = Signal(str)
    upload_requested = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise le plateau inférieur PicasaPhotoTray (`thumbui/basecontrolset`) avec sa barre d'en-tête
        (`thumbui/infotext` + `editpanel/toggle_left_drawer`) et ses deux étages de contrôles.
        EN: Initializes the PicasaPhotoTray bottom tray (`thumbui/basecontrolset`) with its header bar
        (`thumbui/infotext` + `editpanel/toggle_left_drawer`) and its two control tiers.
        Ref: picasa3.exe @ 0x0056727B, 0x0057079D, 0x0057BB80..0x0057C3A3
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.is_held: bool = False
        self.held_items: List[Any] = []
        self.active_items: List[Any] = []
        self._db: Optional[Any] = None
        self._is_edit_mode: bool = False
        self._is_video: bool = False
        self._one_up_context: Optional[dict] = None

        # FR: Hauteur authentique de basecontrolset : rect=(0, 429, 800, 534) -> 98-105 px
        # EN: Authentic height of basecontrolset: rect=(0, 429, 800, 534) -> 98-105 px
        self.setFixedHeight(98)
        self.setObjectName("TrayRoot")
        self.apply_style(self.style)

        root_v = QVBoxLayout(self)
        root_v.setContentsMargins(6, 2, 8, 4)
        root_v.setSpacing(2)

        # =====================================================================
        # FR: EN-TÊTE SUPÉRIEUR DE LA BARRE DU BAS (Y = 429..446 dans basecontrolset) :
        #     - Gauche (X=1..16) : editpanel/toggle_left_drawer (visible uniquement en mode Édition 1-Up)
        #     - Centre (X=183..664) : thumbui/infotext (nom de l'image, date, résolution, taille, tags...)
        # EN: TOP HEADER STRIP OF THE BOTTOM BAR (Y = 429..446 in basecontrolset):
        #     - Left (X=1..16): editpanel/toggle_left_drawer (visible only in One-Up Edit mode)
        #     - Center (X=183..664): thumbui/infotext (image filename, date, resolution, file size, tags...)
        # Ref: respack.yt @ editpanel/toggle_left_drawer rect=(1, 430, 16, 446)
        # Ref: respack.yt @ thumbui/infotext rect=(183, 429, 664, 443), picasa3.exe @ 0x0056727B, 0x0057079D
        # =====================================================================
        self.header_bar = QWidget(self)
        self.header_bar.setObjectName("TrayHeaderBar")
        self.header_bar.setFixedHeight(18)
        header_h = QHBoxLayout(self.header_bar)
        header_h.setContentsMargins(0, 0, 0, 0)
        header_h.setSpacing(0)

        # FR: Marge gauche de 20px (XConstraint 0, 0, 20 dans thumbui.tre) hébergeant editpanel/toggle_left_drawer (X=1..16)
        # EN: 20px left margin (XConstraint 0, 0, 20 in thumbui.tre) hosting editpanel/toggle_left_drawer (X=1..16)
        self.header_left_slot = QWidget(self.header_bar)
        self.header_left_slot.setFixedSize(20, 18)
        left_slot_layout = QHBoxLayout(self.header_left_slot)
        left_slot_layout.setContentsMargins(0, 1, 0, 1)
        left_slot_layout.setSpacing(0)

        self.btn_toggle_left_drawer = QPushButton("◀", self.header_left_slot)
        self.btn_toggle_left_drawer.setObjectName("TrayToggleLeftDrawerBtn")
        self.btn_toggle_left_drawer.setFixedSize(20, 16)
        self.btn_toggle_left_drawer.setToolTip("Afficher/masquer le panneau de retouches gauche (editpanel/toggle_left_drawer)")
        self.btn_toggle_left_drawer.clicked.connect(self.toggle_left_drawer_requested.emit)
        self.btn_toggle_left_drawer.hide()
        left_slot_layout.addWidget(self.btn_toggle_left_drawer)
        header_h.addWidget(self.header_left_slot)

        # FR: thumbui/infotext : Property textalign center, XConstraint 0, 0, 20 .. XConstraint 1, 1, -20 (thumbui.tre)
        # EN: thumbui/infotext: Property textalign center, XConstraint 0, 0, 20 .. XConstraint 1, 1, -20 (thumbui.tre)
        self.lbl_selection = QLabel("Aucune sélection", self.header_bar)
        self.lbl_selection.setObjectName("TraySelectionLabel")
        self.lbl_selection.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_infotext = self.lbl_selection
        header_h.addWidget(self.lbl_selection, 1)

        # FR: Marge droite symétrique de 20px (XConstraint 1, 1, -20 dans thumbui.tre)
        # EN: Symmetrical 20px right margin (XConstraint 1, 1, -20 in thumbui.tre)
        header_h.addSpacing(20)

        root_v.addWidget(self.header_bar)

        body_h = QHBoxLayout()
        body_h.setContentsMargins(2, 0, 0, 0)
        body_h.setSpacing(10)

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

        # FR: Cadre enfoncé du bac à photos (thumbui/scratchpadbase)
        # EN: Sunken frame of the photo tray (thumbui/scratchpadbase)
        self.scratchpad_frame = QFrame(left_zone)
        self.scratchpad_frame.setObjectName("ScratchPadBase")
        scratch_h = QHBoxLayout(self.scratchpad_frame)
        scratch_h.setContentsMargins(4, 3, 4, 3)
        scratch_h.setSpacing(4)

        # FR: Bande de miniatures (thumbui/scratch rect=(8, 455, 223, 515))
        # EN: Thumbnail strip (thumbui/scratch rect=(8, 455, 223, 515))
        self.thumb_strip = PicasaTrayThumbnailStrip(self.scratchpad_frame)
        self.thumb_strip.item_clicked.connect(self.action_thumbnail_clicked.emit)
        self.thumb_strip.item_double_clicked.connect(self.action_thumbnail_double_clicked.emit)
        self.thumb_strip.item_context_menu_requested.connect(self._on_strip_context_menu)
        self.thumb_strip.item_remove_requested.connect(self._on_remove_item)
        self.thumb_strip.subselection_changed.connect(self._sync_hold_button_state)
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
        body_h.addWidget(left_zone, 36)

        # =====================================================================
        # FR: ZONE DROITE : 2 étages séparés par thumbui/separator (Y=476..478)
        # EN: RIGHT ZONE: 2 tiers separated by thumbui/separator (Y=476..478)
        # =====================================================================
        right_zone = QWidget(self)
        right_vbox = QVBoxLayout(right_zone)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(3)

        # ---------------------------------------------------------------------
        # FR: ÉTAGE SUPÉRIEUR (Y = 448..475) :
        #     - Mode Bibliothèque : [☆] [↶] [↷] | [🔍 ----o---- 🖼️] | [👤][📍][🏷️][ℹ️]
        #     - Mode Édition 1-Up : [☆] [↶] [↷] | [Ajuster][1:1][🔍 ----o----][Visages] | [👤][📍][🏷️][ℹ️]
        # Ref: picasa3.exe @ 0x0057C260..0x0057C3A3, 0x005678E0..0x005679F8
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

        # 4a. Mode Bibliothèque — thumbui/scale_group : loupe (368..391) + scalecontainer (398..525, 127x27)
        self.icon_small = PicasaZoomIcon(is_large=False)
        upper_strip.addWidget(self.icon_small)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(64, 256)
        self.zoom_slider.setValue(140)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.setToolTip("Ajuster la taille des vignettes (thumbui/scalecontainer)")
        self.zoom_slider.valueChanged.connect(self.zoom_changed.emit)
        upper_strip.addWidget(self.zoom_slider)

        self.icon_large = PicasaZoomIcon(is_large=True)
        upper_strip.addWidget(self.icon_large)

        # 4b. Mode Édition 1-Up — editpanel/zoombuttcontainer (fit, 1to1) + editpanel/zoomup_icon + editpanel/zoomslider_container
        #     (Ref: picasa3.exe @ 0x0057C277..0x0057C38F, 0x005679D5)
        self.btn_fit = QPushButton("Ajuster")
        self.btn_fit.setFixedHeight(24)
        self.btn_fit.setToolTip("Ajuster la photo à la fenêtre (editpanel/fit)")
        self.btn_fit.clicked.connect(self.oneup_fit_requested.emit)
        self.btn_fit.hide()
        upper_strip.addWidget(self.btn_fit)

        self.btn_zoom_1to1 = QPushButton("1:1")
        self.btn_zoom_1to1.setFixedHeight(24)
        self.btn_zoom_1to1.setToolTip("Zoom 1:1 taille réelle 100% (editpanel/1to1)")
        self.btn_zoom_1to1.clicked.connect(self.oneup_zoom_1to1_requested.emit)
        self.btn_zoom_1to1.hide()
        upper_strip.addWidget(self.btn_zoom_1to1)

        self.oneup_zoom_icon = QLabel("🔍")
        self.oneup_zoom_icon.hide()
        upper_strip.addWidget(self.oneup_zoom_icon)

        self.oneup_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.oneup_zoom_slider.setRange(10, 400)
        self.oneup_zoom_slider.setValue(100)
        self.oneup_zoom_slider.setFixedWidth(120)
        self.oneup_zoom_slider.setToolTip("Zoom sur la photo (zoomslider/scaleslider)")
        self.oneup_zoom_slider.valueChanged.connect(self.oneup_zoom_changed.emit)
        self.oneup_zoom_slider.hide()
        upper_strip.addWidget(self.oneup_zoom_slider)

        self.btn_toggle_faces = QPushButton("Visages (On)")
        self.btn_toggle_faces.setFixedHeight(24)
        self.btn_toggle_faces.setCheckable(True)
        self.btn_toggle_faces.setChecked(True)
        self.btn_toggle_faces.toggled.connect(self._on_faces_btn_toggled)
        self.btn_toggle_faces.hide()
        upper_strip.addWidget(self.btn_toggle_faces)

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
        self.btn_upload.setFixedHeight(32)
        self.btn_upload.setToolTip("Partager / Importer vers Google Photos / Web")
        self.btn_upload.clicked.connect(self.upload_requested.emit)
        self.action_buttons_layout.addWidget(self.btn_upload)

        self.btn_email = QPushButton("✉ E-mail")
        self.btn_email.setObjectName("OutputBtn")
        self.btn_email.setFixedHeight(32)
        self.btn_email.setToolTip("Envoyer les photos sélectionnées par e-mail (Ctrl+E)")
        self.btn_email.clicked.connect(self.action_email.emit)
        self.action_buttons_layout.addWidget(self.btn_email)

        self.btn_print = QPushButton("🖨 Imprimer")
        self.btn_print.setObjectName("OutputBtn")
        self.btn_print.setFixedHeight(32)
        self.btn_print.setToolTip("Imprimer les photos sélectionnées (Ctrl+P)")
        self.btn_print.clicked.connect(self.action_print.emit)
        self.action_buttons_layout.addWidget(self.btn_print)

        self.btn_export = QPushButton("📁 Exporter")
        self.btn_export.setObjectName("OutputBtn")
        self.btn_export.setFixedHeight(32)
        self.btn_export.setToolTip("Exporter les photos sélectionnées vers un dossier (Ctrl+Maj+S)")
        self.btn_export.clicked.connect(self.action_export.emit)
        self.action_buttons_layout.addWidget(self.btn_export)

        self.btn_collage = QPushButton("⊞ Montage")
        self.btn_collage.setObjectName("OutputBtn")
        self.btn_collage.setFixedHeight(32)
        self.btn_collage.setToolTip("Créer un montage photo avec la sélection")
        self.btn_collage.clicked.connect(self.action_collage.emit)
        self.action_buttons_layout.addWidget(self.btn_collage)

        self.btn_movie = QPushButton("🎬 Film")
        self.btn_movie.setObjectName("OutputBtn")
        self.btn_movie.setFixedHeight(32)
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
        self.btn_configure_buttons.setFixedSize(28, 32)
        self.btn_configure_buttons.setToolTip("Configurer les boutons (outputlayout/morebutton)...")
        self.btn_configure_buttons.clicked.connect(self.open_button_manager)
        lower_strip.addWidget(self.btn_configure_buttons)

        right_vbox.addLayout(lower_strip)
        body_h.addWidget(right_zone, 64)
        root_v.addLayout(body_h, 1)

        self._is_starred: bool = False
        self.set_selected_count(0)
        self.apply_style(self.style)

    def _on_faces_btn_toggled(self, checked: bool) -> None:
        """
        FR: Met à jour le libellé du bouton Visages et émet le signal vers le canevas 1-Up.
        EN: Updates the Faces button label and emits the signal to the 1-Up canvas.
        """
        self.btn_toggle_faces.setText("Visages (On)" if checked else "Visages (Off)")
        self.oneup_faces_toggled.emit(checked)

    def set_oneup_zoom_from_canvas(self, scale: float, fit_scale: Optional[float] = None) -> None:
        """
        FR: Synchronise le curseur `zoomslider/scaleslider` sans boucle de rétroaction lorsque le canevas 1-Up zoome.
        La borne minimale du curseur est calée sur l'échelle Ajuster (`fit_scale`) afin que la butée gauche
        corresponde toujours à « Ajuster à la fenêtre » et que le glissement vers la droite zoome jusqu'à 400%.
        EN: Synchronizes the `zoomslider/scaleslider` slider without feedback loop when the 1-Up canvas zooms.
        The slider minimum is aligned with `fit_scale` so the left stop always matches "Fit to window".
        Ref: picasa3.exe @ 0x0057C322 (zoomslider/scaleslider), 0x005D1520, 0x00597D10
        """
        self.oneup_zoom_slider.blockSignals(True)
        if fit_scale is not None and fit_scale > 0:
            min_pct = max(5, min(100, int(round(fit_scale * 100))))
            max_pct = max(400, min_pct * 4)
            self.oneup_zoom_slider.setRange(min_pct, max_pct)
        if not self.oneup_zoom_slider.isSliderDown():
            val = int(round(scale * 100))
            val = max(self.oneup_zoom_slider.minimum(), min(self.oneup_zoom_slider.maximum(), val))
            self.oneup_zoom_slider.setValue(val)
        self.oneup_zoom_slider.blockSignals(False)

    def set_edit_mode(self, is_edit_mode: bool, is_video: bool = False) -> None:
        """
        FR: Bascule la visibilité des boutons de `thumbui/basecontrolset` selon le mode actif :
        - Mode Bibliothèque (`is_edit_mode=False`) :
          * Masque `editpanel/toggle_left_drawer`, `editpanel/zoombuttcontainer` (`Ajuster`, `1:1`),
            `editpanel/zoomup_icon`, `editpanel/zoomslider_container` et `btn_toggle_faces`.
          * Affiche `thumbui/scale_group` (`icon_small`, `zoom_slider`, `icon_large`).
        - Mode Édition 1-Up (`is_edit_mode=True`) :
          * Affiche `editpanel/toggle_left_drawer` dans l'en-tête supérieur.
          * Masque `thumbui/scale_group` (`icon_small`, `zoom_slider`, `icon_large`).
          * Affiche `editpanel/zoombuttcontainer` (`Ajuster`, `1:1`), `editpanel/zoomup_icon`,
            `editpanel/zoomslider_container` et `btn_toggle_faces` si `not is_video`
            (les masque si `is_video=True`, conformément à `0x0057C2E6..0x0057C38F` et `0x005679BF`).
        EN: Switches button visibility in `thumbui/basecontrolset` according to the active mode.
        Ref: picasa3.exe @ 0x0057BB80..0x0057C3A3, 0x005678E0..0x005679F8, 0x00572D18..0x00572E18
        """
        self._is_edit_mode = bool(is_edit_mode)
        self._is_video = bool(is_video)

        self.btn_toggle_left_drawer.setVisible(self._is_edit_mode)

        # Mode Bibliothèque : thumbui/scale_group
        show_lib_scale = not self._is_edit_mode
        self.icon_small.setVisible(show_lib_scale)
        self.zoom_slider.setVisible(show_lib_scale)
        self.icon_large.setVisible(show_lib_scale)

        # Mode Édition 1-Up : editpanel/zoombuttcontainer + editpanel/zoomslider_container + editpanel/zoomup_icon
        show_oneup_zoom = self._is_edit_mode and (not self._is_video)
        self.btn_fit.setVisible(show_oneup_zoom)
        self.btn_zoom_1to1.setVisible(show_oneup_zoom)
        self.oneup_zoom_icon.setVisible(show_oneup_zoom)
        self.oneup_zoom_slider.setVisible(show_oneup_zoom)
        self.btn_toggle_faces.setVisible(show_oneup_zoom)

        if self._is_edit_mode:
            # Ref: 0x005678E0..0x00567943 (thumbui/rotateright, thumbui/rotateleft désactivés sur vidéo)
            self.btn_rotate_left.setEnabled(not self._is_video)
            self.btn_rotate_right.setEnabled(not self._is_video)
        else:
            self._one_up_context = None
            self.update_info_text()

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

    @staticmethod
    def _item_key(item: Any) -> str:
        p = getattr(item, "path", None)
        return str(p) if p else f"id:{id(item)}"

    def _get_held_keys(self) -> Set[str]:
        return {self._item_key(it) for it in self.held_items}

    def _sync_hold_button_state(self) -> None:
        """
        FR: Synchronise l'état visuel du bouton Maintenir (`thumbui/scratchhold` @ `0x00577BA0`)
        selon que les éléments ciblés dans le bac sont maintenus (`holdCount > 0` @ `[pItem + 0xBC]`).
        EN: Synchronizes the visual state of the Hold button (`thumbui/scratchhold` @ `0x00577BA0`)
        based on whether the targeted items in the tray are held (`holdCount > 0` @ `[pItem + 0xBC]`).
        """
        held_keys = self._get_held_keys()
        self.is_held = bool(self.held_items)
        targets = self.thumb_strip.get_subselected_items() if hasattr(self, "thumb_strip") else []
        all_targets_held = bool(targets) and all(self._item_key(it) in held_keys for it in targets)
        checked = all_targets_held if targets else self.is_held
        self.btn_hold.blockSignals(True)
        self.btn_hold.setChecked(checked)
        self.btn_hold.blockSignals(False)
        if checked or self.is_held:
            self.btn_hold.setText("📌")
            self.btn_hold.setObjectName("HeldBtn")
            self.btn_hold.setStyleSheet("background-color: #2E5C38; border: 1px solid #4CAF50; color: #FFFFFF;")
        else:
            self.btn_hold.setText("📌")
            self.btn_hold.setObjectName("TrayStackBtn")
            self.btn_hold.setStyleSheet("")

    def _toggle_hold(self) -> None:
        """
        FR: Maintient ou relâche les photos dans le bac (`thumbui/scratchhold` @ `0x00577BA0` / `0x0071A110`).
        Si une sous-sélection existe dans le bac, bascule uniquement ces éléments ; sinon bascule tous les éléments.
        EN: Holds or releases photos in the tray (`thumbui/scratchhold` @ `0x00577BA0` / `0x0071A110`).
        If a sub-selection exists in the tray, toggles only those items; otherwise toggles all items.
        """
        effective = self.get_effective_items()
        sub = (
            [it for it in effective if self._item_key(it) in self.thumb_strip.selected_paths]
            if (self.thumb_strip.selected_paths and len(self.thumb_strip.selected_paths) < len(effective))
            else list(effective)
        )
        if not sub:
            self.is_held = not self.is_held
            if not self.is_held:
                self.held_items.clear()
        else:
            held_keys = self._get_held_keys()
            all_sub_held = all(self._item_key(it) in held_keys for it in sub)
            if all_sub_held:
                remove_keys = {self._item_key(it) for it in sub}
                self.held_items = [it for it in self.held_items if self._item_key(it) not in remove_keys]
            else:
                for it in sub:
                    k = self._item_key(it)
                    if k not in held_keys:
                        self.held_items.append(it)
                        held_keys.add(k)
            self.is_held = bool(self.held_items)

        self._sync_hold_button_state()
        self.thumb_strip.set_items(
            self.get_effective_items(),
            is_held=self.is_held,
            held_paths=self._get_held_keys(),
        )
        self.action_hold.emit(self.is_held)

    def _on_clear_clicked(self) -> None:
        """
        FR: Vide le bac à photos (`thumbui/scratchclear` @ `0x00577FD0`).
        EN: Clears the photo tray (`thumbui/scratchclear` @ `0x00577FD0`).
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
        self.thumb_strip.selected_paths.clear()
        self.thumb_strip.focused_path = None
        self.set_selected_items([])
        self.action_clear.emit()

    def remove_items_from_tray(self, items_to_remove: List[Any]) -> None:
        """
        FR: Retire uniquement les éléments spécifiés du bac à photos (`Tray::ID_REMOVE_SELECTION` @ `0x00733224`).
        EN: Removes only the specified items from the photo tray (`Tray::ID_REMOVE_SELECTION` @ `0x00733224`).
        """
        rem_keys = {self._item_key(it) for it in items_to_remove}
        self.held_items = [it for it in self.held_items if self._item_key(it) not in rem_keys]
        self.active_items = [it for it in self.active_items if self._item_key(it) not in rem_keys]
        self.is_held = bool(self.held_items)
        self.thumb_strip.selected_paths -= rem_keys
        effective = self.get_effective_items()
        self._sync_hold_button_state()
        self.thumb_strip.set_items(effective, is_held=self.is_held, held_paths=self._get_held_keys())
        self.set_selected_count(len(effective))
        paths = [getattr(it, "path", None) for it in items_to_remove if getattr(it, "path", None)]
        if paths:
            self.tray_context_action_requested.emit("remove_selection", paths)

    def _on_remove_item(self, item: Any) -> None:
        """
        FR: Supprime une photo individuelle du bac.
        EN: Removes an individual photo from the tray.
        """
        self.remove_items_from_tray([item])

    def _on_strip_context_menu(self, item: Any, global_pos: QPoint) -> None:
        """
        FR: Ouvre le menu contextuel authentique à 7 entrées du bac de sélection (`TrayContextMenu` @ `0x00732EE0`).
        EN: Opens the authentic 7-item selection tray context menu (`TrayContextMenu` @ `0x00732EE0`).
        Ref: picasa3.exe @ 0x00732EE0, 0x005E7870, 0x005E7D10, MENU_FR.XML (Tray::ID_*)
        """
        sub_items = self.thumb_strip.get_subselected_items()
        if not sub_items:
            sub_items = [item]
        sub_paths = [getattr(it, "path", "") for it in sub_items if getattr(it, "path", "")]
        held_keys = self._get_held_keys()
        any_unheld = any(self._item_key(it) not in held_keys for it in sub_items)

        rm = PicasaResourceManager.get()
        menu = QMenu(self)
        m_bg = "#2D3139" if self.style.is_dark else self.style.window_bgcolor.name()
        m_txt = "#FFFFFF" if self.style.is_dark else self.style.alayout_titleColor.name()
        m_brd = "#4B5260" if self.style.is_dark else self.style.splitter_color.name()
        m_acc = self.style.accent_color.name()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {m_bg};
                color: {m_txt};
                border: 1px solid {m_brd};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 20px 5px 24px;
                font-size: 11px;
            }}
            QMenu::item:selected {{
                background-color: {m_acc};
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {m_brd};
                margin: 4px 8px;
            }}
        """)

        # 1. Afficher et modifier (AlbumPhoto::ID_PICTURE_VIEW, 0x9CA0)
        lbl_view = rm.get_xml_string("AlbumPhoto::ID_PICTURE_VIEW", "Afficher et modifier").replace("&", "")
        act_view = menu.addAction(lbl_view)
        act_view.triggered.connect(lambda: self.action_thumbnail_double_clicked.emit(item))

        # 2. Maintenir la sélection / Relâcher les éléments sélectionnés (Tray::ID_PICTURE_HOLDINPICTURETRAY, 0x9CCA)
        if any_unheld:
            lbl_hold = rm.get_xml_string("Tray::ID_PICTURE_HOLDINPICTURETRAY", "Maintenir la sélection\tH").replace("&", "")
        else:
            lbl_hold = "Relâcher les éléments sélectionnés\tH"
        act_hold = menu.addAction(lbl_hold)
        act_hold.triggered.connect(lambda: self._toggle_hold_for_items(sub_items))

        # 3. Supprimer la sélection (Tray::ID_REMOVE_SELECTION, 0x9CC9)
        lbl_rem = rm.get_xml_string("Tray::ID_REMOVE_SELECTION", "Supprimer la sélection").replace("&", "")
        act_rem = menu.addAction(lbl_rem)
        act_rem.triggered.connect(lambda: self.remove_items_from_tray(sub_items))

        menu.addSeparator()

        # 4. Faire pivoter dans le sens des aiguilles d'une montre (AlbumPhoto::ID_PICTURE_ROTATECLOCKWISE, 0x9CA2)
        lbl_cw = rm.get_xml_string(
            "AlbumPhoto::ID_PICTURE_ROTATECLOCKWISE",
            "Faire pivoter dans le sens des aiguilles d'une montre\tR",
        ).replace("&", "")
        act_cw = menu.addAction(lbl_cw)
        act_cw.triggered.connect(lambda: self.tray_context_action_requested.emit("rotate_cw", sub_paths))

        # 5. Faire pivoter dans le sens inverse des aiguilles d'une montre (AlbumPhoto::ID_PICTURE_ROTATECOUNTERCLOCKWISE, 0x9CA3)
        lbl_ccw = rm.get_xml_string(
            "AlbumPhoto::ID_PICTURE_ROTATECOUNTERCLOCKWISE",
            "Faire pivoter dans le sens inverse des aiguilles d'une montre",
        ).replace("&", "")
        act_ccw = menu.addAction(lbl_ccw)
        act_ccw.triggered.connect(lambda: self.tray_context_action_requested.emit("rotate_ccw", sub_paths))

        menu.addSeparator()

        # 6. Localiser sur le disque (FolderPhotoWin::ID_FILE_LOCATEONDISK, 0x9C99)
        lbl_loc = rm.get_xml_string("FolderPhotoWin::ID_FILE_LOCATEONDISK", "Localiser sur le disque").replace("&", "")
        act_loc = menu.addAction(lbl_loc)
        act_loc.triggered.connect(lambda: self.tray_context_action_requested.emit("locate_on_disk", sub_paths))

        # 7. Propriétés (AlbumPhotoWin::ID_PICTURE_PROPERTIES, 0x9CA8)
        lbl_props = rm.get_xml_string("AlbumPhotoWin::ID_PICTURE_PROPERTIES", "Propriétés").replace("&", "")
        act_props = menu.addAction(lbl_props)
        act_props.triggered.connect(lambda: self.tray_context_action_requested.emit("properties", sub_paths))

        menu.exec(global_pos)

    def _toggle_hold_for_items(self, target_items: List[Any]) -> None:
        """
        FR: Maintient ou relâche spécifiquement les éléments `target_items` dans le bac (`0x00733172`).
        EN: Specifically holds or releases `target_items` in the tray (`0x00733172`).
        """
        held_keys = self._get_held_keys()
        any_unheld = any(self._item_key(it) not in held_keys for it in target_items)
        if any_unheld:
            for it in target_items:
                k = self._item_key(it)
                if k not in held_keys:
                    self.held_items.append(it)
                    held_keys.add(k)
        else:
            rem_keys = {self._item_key(it) for it in target_items}
            self.held_items = [it for it in self.held_items if self._item_key(it) not in rem_keys]
        self.is_held = bool(self.held_items)
        self._sync_hold_button_state()
        self.thumb_strip.set_items(
            self.get_effective_items(),
            is_held=self.is_held,
            held_paths=self._get_held_keys(),
        )
        self.action_hold.emit(self.is_held)

    def set_focused_path(self, path: Optional[str], select_only_focused: bool = False) -> None:
        """
        FR: Met en surbrillance dans le bac la miniature correspondant au chemin `path`.
        EN: Highlights in the tray the thumbnail matching `path`.
        """
        if hasattr(self, "thumb_strip") and self.thumb_strip is not None:
            self.thumb_strip.set_focused_path(path, select_only_focused=select_only_focused)

    def get_effective_items(self) -> List[Any]:
        """
        FR: Renvoie les éléments actifs du bac en évitant les doublons (`held_items` + `active_items`).
        EN: Returns the active items in the tray while avoiding duplicates (`held_items` + `active_items`).
        """
        if self.is_held or self.held_items:
            seen = set()
            combined = []
            for it in self.held_items + self.active_items:
                p = self._item_key(it)
                if p not in seen:
                    seen.add(p)
                    combined.append(it)
            return combined
        return list(self.active_items)

    def set_database(self, db: Optional[Any]) -> None:
        """
        FR: Associe la base de données Picasa au bac à photos pour le chargement instantané des miniatures en RAM.
        EN: Associates the Picasa database with the photo tray for instant in-memory thumbnail loading.
        """
        global _ACTIVE_TRAY_DB
        self._db = db
        _ACTIVE_TRAY_DB = db

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        FR: Formate une taille en octets selon `FormatFileSize` (`0x0098F9F0`) et `STRINGRES_FR.XML` :
        `%.0f octets`, `%.0f ko`, `%.1f Mo`, `%.1f Go`, `%.1f To`.
        EN: Formats a byte size according to `FormatFileSize` (`0x0098F9F0`) and `STRINGRES_FR.XML`:
        `%.0f octets`, `%.0f ko`, `%.1f Mo`, `%.1f Go`, `%.1f To`.
        Ref: picasa3.exe @ 0x0098F9F0..0x0098FB80 (il_FormatBigB/KB/MB/GB/TB)
        """
        b = max(0, int(size_bytes or 0))
        if b < 1024:
            return f"{b} octets"
        kb = b / 1024.0
        if kb < 1024.0:
            return f"{kb:.0f} ko"
        mb = kb / 1024.0
        if mb < 1024.0:
            return f"{mb:.1f} Mo".replace(".", ",")
        gb = mb / 1024.0
        if gb < 1024.0:
            return f"{gb:.1f} Go".replace(".", ",")
        tb = gb / 1024.0
        return f"{tb:.1f} To".replace(".", ",")

    def _get_item_metadata(self, item_or_path: Any) -> Tuple[str, str, Optional[Any], int, int, int, List[str]]:
        """
        FR: Récupère `(filename, folder_name, datetime_obj, width, height, size_bytes, tags)` pour un élément
        depuis la base de données Picasa (`thumbindex.db`, `imagedata_*.pmp`, `.picasa.ini`) ou le système de fichiers.
        EN: Retrieves `(filename, folder_name, datetime_obj, width, height, size_bytes, tags)` for an item
        from the Picasa database (`thumbindex.db`, `imagedata_*.pmp`, `.picasa.ini`) or the filesystem.
        Ref: picasa3.exe @ 0x0056FCE8 (GetRecordInfo), 0x0056FD24 (GetImageDimensions), 0x0056F920 (GetTagInfo)
        """
        from datetime import datetime
        from PySide6.QtGui import QImageReader

        if isinstance(item_or_path, str):
            path = item_or_path
            fname = os.path.basename(path)
            folder_path = os.path.dirname(path)
            folder_name = os.path.basename(folder_path.rstrip("\\/")) if folder_path else ""
            db_idx = -1
            if self._db is not None and hasattr(self._db, "find_media_index_by_path"):
                try:
                    found_idx = self._db.find_media_index_by_path(path)
                    if found_idx is not None:
                        db_idx = int(found_idx)
                except Exception:
                    db_idx = -1
        else:
            path = getattr(item_or_path, "path", "") or ""
            fname = getattr(item_or_path, "filename", "") or (os.path.basename(path) if path else "")
            folder_path = getattr(item_or_path, "folder_path", "") or (os.path.dirname(path) if path else "")
            folder_name = getattr(item_or_path, "folder", "") or (
                os.path.basename(folder_path.rstrip("\\/")) if folder_path else ""
            )
            db_idx = int(getattr(item_or_path, "index", -1) if getattr(item_or_path, "index", None) is not None else -1)

        dt_obj: Optional[datetime] = None
        width = 0
        height = 0
        size_bytes = 0
        tags: List[str] = []

        db = self._db or _ACTIVE_TRAY_DB
        if db is not None and db_idx >= 0:
            try:
                ti = getattr(db, "thumbindex", None)
                if ti is not None and 0 <= db_idx < len(ti.records):
                    rec = ti.records[db_idx]
                    if not fname and rec.path:
                        fname = rec.path
                    if rec.size and rec.size > 0:
                        size_bytes = int(rec.size)
                    ts = rec.to_unix_timestamp()
                    if ts > 0:
                        dt_obj = datetime.fromtimestamp(ts)
            except Exception:
                pass
            try:
                if hasattr(db, "get_property"):
                    ew = int(db.get_property("imagedata_edit_width", db_idx) or 0)
                    eh = int(db.get_property("imagedata_edit_height", db_idx) or 0)
                    w = int(db.get_property("imagedata_width", db_idx) or 0)
                    h = int(db.get_property("imagedata_height", db_idx) or 0)
                    if ew > 0 and eh > 0:
                        width, height = ew, eh
                    elif w > 0 and h > 0:
                        width, height = w, h
                    raw_tags = db.get_property("imagedata_tags", db_idx)
                    if raw_tags and isinstance(raw_tags, str):
                        for t in raw_tags.split(","):
                            ts = t.strip()
                            if ts and ts not in tags:
                                tags.append(ts)
            except Exception:
                pass

        if path and os.path.exists(path):
            try:
                st = os.stat(path)
                if size_bytes <= 0:
                    size_bytes = int(st.st_size)
                if dt_obj is None and st.st_mtime > 0:
                    dt_obj = datetime.fromtimestamp(st.st_mtime)
            except Exception:
                pass
            if width <= 0 or height <= 0:
                try:
                    reader = QImageReader(path)
                    sz = reader.size()
                    if sz.isValid() and sz.width() > 0 and sz.height() > 0:
                        width, height = sz.width(), sz.height()
                except Exception:
                    pass

        if folder_path and fname:
            try:
                ini_p = os.path.join(folder_path, ".picasa.ini")
                doc = None
                if db is not None and hasattr(db, "get_parsed_ini"):
                    doc = db.get_parsed_ini(ini_p)
                    if doc is None:
                        doc = db.get_parsed_ini(os.path.join(folder_path, "Picasa.ini"))
                elif os.path.exists(ini_p):
                    from picasa_py.ini.parser import PicasaIniParser
                    doc = PicasaIniParser.parse_file(ini_p)
                if doc is not None:
                    for kw in doc.get_keywords(fname):
                        kw_s = kw.strip()
                        if kw_s and kw_s not in tags:
                            tags.append(kw_s)
            except Exception:
                pass

        if (width <= 0 or height <= 0) and not isinstance(item_or_path, str):
            pm = getattr(item_or_path, "pixmap", None)
            if isinstance(pm, QPixmap) and not pm.isNull():
                width, height = pm.width(), pm.height()

        return fname, folder_name, dt_obj, width, height, size_bytes, tags

    def _format_tags_suffix(self, items_meta: List[Tuple[str, str, Optional[Any], int, int, int, List[str]]]) -> str:
        """
        FR: Construit le suffixe des tags (`CThumbUI::GetTagInfo` @ `0x0056F920`) :
        `     Tags : tag1, tag2 (3)`.
        EN: Builds the tags suffix (`CThumbUI::GetTagInfo` @ `0x0056F920`):
        `     Tags : tag1, tag2 (3)`.
        Ref: picasa3.exe @ 0x0056F920..0x0056FBB6 (CThumbUI::GetTagInfo::format, "%s (%d)")
        """
        tag_counts: dict[str, int] = {}
        for meta in items_meta:
            seen_in_item: set[str] = set()
            for t in meta[6]:
                if t not in seen_in_item:
                    seen_in_item.add(t)
                    tag_counts[t] = tag_counts.get(t, 0) + 1
        if not tag_counts:
            return ""
        parts = [f"{t} ({cnt})" if cnt > 1 else t for t, cnt in tag_counts.items()]
        return "     Tags : " + ", ".join(parts)

    def update_one_up_info(
        self,
        file_path: str = "",
        folder_name: str = "",
        width: int = 0,
        height: int = 0,
        pos_1based: int = 0,
        total_in_view: int = 0,
        *,
        photo_path: str = "",
        total_in_folder: int = 0,
    ) -> None:
        """
        FR: Met à jour l'en-tête `thumbui/infotext` en mode Édition 1-Up (`BuildEditModeInfoText` @ `0x00566E5A..0x00567285`) :
        `Dossier > Image.jpg     Date Heure     LxH pixels     Taille    (i sur N)     Tags : ...`
        EN: Updates the `thumbui/infotext` header in One-Up Edit mode (`BuildEditModeInfoText` @ `0x00566E5A..0x00567285`).
        Ref: picasa3.exe @ 0x00566E5A..0x00567285 (il_BigView::1, il_BigView::2, CThumbUI::GetTagInfo)
        """
        self._one_up_context = {
            "file_path": file_path or photo_path,
            "folder_name": folder_name,
            "width": width,
            "height": height,
            "pos_1based": pos_1based,
            "total_in_view": total_in_view or total_in_folder,
        }
        self.update_info_text()

    def update_info_text(self, fallback_count: Optional[int] = None) -> None:
        """
        FR: Reproduit fidèlement le texte d'en-tête `thumbui/infotext` de `picasa3.exe` :
        - En mode Édition 1-Up (`0x00566E5A..0x00567285`) :
          `Dossier > Nom.jpg     JJ/MM/AAAA HH:MM     LxH pixels     Taille    (i sur N)     Tags : ...`
        - En mode Bibliothèque (`0x0056FBC0..0x005704CA`) :
          * 0 élément (`il_GetSelectionInfo::1`) : `Aucune sélection`
          * 1 élément (`il_GetSelectionInfo::2`) : `Nom.jpg     JJ/MM/AAAA HH:MM     LxH pixels     Taille     Tags : ...`
          * >1 éléments même date (`il_GetSelectionInfo::3` + `::5`) : `N photos     JJ/MM/AAAA      Taille sur le disque     Tags : ...`
          * >1 éléments dates différentes (`il_GetSelectionInfo::3` + `::4`) : `N photos     DateMin à DateMax     Taille sur le disque     Tags : ...`
        EN: Faithfully reproduces the `thumbui/infotext` header text of `picasa3.exe`.
        Ref: picasa3.exe @ 0x0056FBC0, 0x00566E5A, 0x0056F920, 0x0098F9F0
        """
        if self._is_edit_mode and self._one_up_context and self._one_up_context.get("file_path"):
            ctx = self._one_up_context
            fpath = str(ctx.get("file_path", ""))
            fname, meta_folder, dt_obj, meta_w, meta_h, size_bytes, tags = self._get_item_metadata(fpath)
            folder = str(ctx.get("folder_name") or meta_folder or "").strip()
            w = int(ctx.get("width") or meta_w or 0)
            h = int(ctx.get("height") or meta_h or 0)
            pos_1 = int(ctx.get("pos_1based") or 0)
            tot = int(ctx.get("total_in_view") or 0)

            # Ref: 0x00566EB3 (" > ")
            prefix = f"{folder} > {fname}" if folder else fname
            dt_str = dt_obj.strftime("%d/%m/%Y %H:%M") if dt_obj is not None else ""
            size_str = self.format_file_size(size_bytes)

            # Ref: 0x005670F7 (il_BigView::1 : "%1$s     %2$s     %3$dx%4$d pixels     %5$s")
            parts = [prefix]
            if dt_str:
                parts.append(dt_str)
            if w > 0 and h > 0:
                parts.append(f"{w}x{h} pixels")
            parts.append(size_str)
            text = "     ".join(parts)

            # Ref: 0x00566FAF (il_BigView::2 : "    (%1$d sur %2$d)")
            if tot > 0 and pos_1 > 0:
                text += f"    ({pos_1} sur {tot})"

            # Ref: 0x00567234 (CThumbUI::GetTagInfo)
            text += self._format_tags_suffix([(fname, folder, dt_obj, w, h, size_bytes, tags)])
            self.lbl_selection.setText(text)
            return

        effective = self.get_effective_items()
        count = len(effective) if effective else (fallback_count if fallback_count is not None else 0)

        if count <= 0:
            # Ref: 0x0056FCA0 (il_GetSelectionInfo::1 -> "Aucune sélection")
            self.lbl_selection.setText("Aucune sélection")
            return

        if count == 1 and effective:
            meta = self._get_item_metadata(effective[0])
            fname, folder, dt_obj, w, h, size_bytes, tags = meta
            # Ref: 0x0056FD5E..0x0056FD71 (replace ':' with '/', truncate to 30 chars)
            clean_name = (fname or "").replace(":", "/")
            if len(clean_name) > 30:
                clean_name = clean_name[:27] + "..."
            dt_str = dt_obj.strftime("%d/%m/%Y %H:%M") if dt_obj is not None else ""
            size_str = self.format_file_size(size_bytes)
            # Ref: 0x0056FD76 (il_GetSelectionInfo::2 : "%1$s     %2$s     %3$dx%4$d pixels     %5$s")
            parts = [clean_name]
            if dt_str:
                parts.append(dt_str)
            parts.append(f"{w}x{h} pixels")
            parts.append(size_str)
            text = "     ".join(parts)
            text += self._format_tags_suffix([meta])
            self.lbl_selection.setText(text)
            return

        if count == 1:
            self.lbl_selection.setText("1 photo")
            return

        # Ref: 0x0056FF16..0x0057040E (count > 1 : il_GetSelectionInfo::3 + ::4 / ::5)
        metas = [self._get_item_metadata(it) for it in effective]
        total_bytes = sum(m[5] for m in metas)
        dts = [m[2] for m in metas if m[2] is not None]
        count_str = f"{count:,}".replace(",", " ") if count >= 1000 else str(count)
        size_str = self.format_file_size(total_bytes)

        if dts:
            min_dt = min(dts)
            max_dt = max(dts)
            min_date_str = min_dt.strftime("%d/%m/%Y")
            max_date_str = max_dt.strftime("%d/%m/%Y")
            if min_date_str == max_date_str:
                # Ref: 0x005701BD (il_GetSelectionInfo::5 : "     %1$s      %2$s sur le disque")
                text = f"{count_str} photos     {min_date_str}      {size_str} sur le disque"
            else:
                # Ref: 0x00570271 (il_GetSelectionInfo::4 : "     %1$s à %2$s     %3$s sur le disque")
                text = f"{count_str} photos     {min_date_str} à {max_date_str}     {size_str} sur le disque"
        else:
            text = f"{count_str} photos      {size_str} sur le disque"

        text += self._format_tags_suffix(metas)
        self.lbl_selection.setText(text)

    def set_selected_items(self, items: List[Any]) -> None:
        """
        FR: Met à jour les éléments sélectionnés depuis la grille et affiche leurs miniatures dans le bac.
        EN: Updates the selected items from the grid and displays their thumbnails in the tray.
        """
        self.active_items = list(items)
        effective = self.get_effective_items()
        self._sync_hold_button_state()
        self.thumb_strip.set_items(
            effective,
            is_held=self.is_held,
            held_paths=self._get_held_keys(),
        )
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
        FR: Met à jour l'en-tête `thumbui/infotext` et l'activation des boutons d'action.
        EN: Updates the `thumbui/infotext` header and the enabled state of action buttons.
        Ref: picasa3.exe @ 0x005706B0, 0x0056FBC0
        """
        enabled = count > 0 or self._is_edit_mode
        self.update_info_text(fallback_count=count)

        self.btn_export.setEnabled(enabled)
        self.btn_print.setEnabled(enabled)
        self.btn_email.setEnabled(enabled)
        self.btn_add_to_album.setEnabled(enabled)
        self.btn_collage.setEnabled(enabled)
        self.btn_movie.setEnabled(enabled)
        self.btn_star.setEnabled(enabled)
        rot_enabled = enabled and not (self._is_edit_mode and self._is_video)
        self.btn_rotate_left.setEnabled(rot_enabled)
        self.btn_rotate_right.setEnabled(rot_enabled)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs au plateau inférieur.
        EN: Dynamically applies the color theme to the bottom photo tray.
        """
        if style is None:
            style = PicasaStyle.instance()
        self.style = style
        tray_bg = style.tray_bgcolor.name()
        tray_bg_end = getattr(style, "tray_bgcolor_end", style.tray_bgcolor).name()
        tray_root_bg = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {tray_bg}, stop:1 {tray_bg_end})"
            if tray_bg != tray_bg_end
            else tray_bg
        )
        scratch_bg = style.tray_grad_end.darker(112).name() if style.is_dark else style.tray_grad_end.lighter(104).name()
        btn_start = style.tray_grad_start.name() if style.is_dark else style.topbar_btn_bg_start.name()
        btn_end = style.tray_grad_end.name() if style.is_dark else style.topbar_btn_bg_end.name()
        btn_border = style.topbar_btn_border.name()
        txt_col = style.tray_text_color.name()
        sub_txt = style.alayout_subtitleColor.name()
        dis_txt = style.alayout_subtitleColor.darker(120).name() if style.is_dark else "#8E8E8E"
        dis_bg = style.tray_bgcolor.darker(112).name() if style.is_dark else style.window_bgcolor.darker(104).name()
        dis_border = style.splitter_color.darker(115).name() if style.is_dark else style.splitter_color.name()
        top_border = style.splitter_color.name() if style.is_dark else style.topbar_border_color.name()
        sep_top = style.splitter_color.darker(120).name() if style.is_dark else style.splitter_color.name()
        sep_bot = style.splitter_color.lighter(120).name() if style.is_dark else "#FFFFFF"
        accent = style.accent_color.name()
        accent_end = getattr(style, "accent_grad_end", style.accent_color).name()
        accent_bg = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent_end})"
            if accent != accent_end
            else accent
        )
        has_grad_accent = accent != accent_end
        upload_grad = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent_end})"
            if has_grad_accent
            else "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5CB85C, stop:1 #3D8B3D)"
        )
        upload_hover = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {style.accent_color.lighter(115).name()}, stop:1 {getattr(style, 'accent_grad_end', style.accent_color).lighter(115).name()})"
            if has_grad_accent
            else "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6EC46E, stop:1 #489B48)"
        )
        upload_border = accent_end if has_grad_accent else "#2D672D"

        if hasattr(self, "thumb_strip") and self.thumb_strip:
            self.thumb_strip.apply_style(style)
        if hasattr(self, "btn_star"):
            self.update_star_state(getattr(self, "_is_starred", False))

        self.setStyleSheet(f"""
            QWidget#TrayRoot {{
                background: {tray_root_bg};
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
                background: {accent_bg};
                color: #FFFFFF;
                border-color: {accent};
            }}
            QPushButton:disabled {{
                color: {dis_txt};
                background-color: {dis_bg};
                border-color: {dis_border};
            }}
            QPushButton#GreenUploadBtn {{
                background: {upload_grad};
                border: 1px solid {upload_border};
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 12px;
            }}
            QPushButton#GreenUploadBtn:hover {{
                background: {upload_hover};
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
            QPushButton#OutputBtn:pressed, QPushButton#OutputBtn:checked {{
                background: {accent_bg};
                color: #FFFFFF;
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
