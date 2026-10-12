"""
One-Up View Component for PyCasa (Single Photo Viewer & Editor).
Assembles the Edit Panel, Image Canvas, and Transport Controls.

Ref: picasa3.exe @ OneUp, AVOneUpUI, editoneup
Ref: AGENTS.md §4 bis (Mode visualiseur/retouche fidèle)
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
from PIL import Image

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.image_canvas import PicasaImageCanvas
from picasa_py.ui.edit_panel import PicasaEditPanel
from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.db.database import PicasaDatabase


# Ref: picasa3.exe @ OneUp
class PicasaOneUpView(QWidget):
    """
    Vue d'édition d'une image unique (« One-Up View ») avec retouche et navigation.
    """
    back_to_library_requested = Signal()
    photo_modified = Signal(int, dict)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.db: Optional[PicasaDatabase] = None
        self.current_index: int = -1
        self.available_indices: List[int] = []

        # Historique de retouche pour Annuler/Rétablir
        self._history: List[Image.Image] = []
        self._history_idx: int = -1

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Volet gauche d'édition
        self.edit_panel = PicasaEditPanel(self.style, self)
        self.edit_panel.back_to_library.connect(self.back_to_library_requested.emit)
        self.edit_panel.apply_effect.connect(self._on_apply_effect)
        self.edit_panel.undo_action.connect(self._on_undo)
        self.edit_panel.redo_action.connect(self._on_redo)
        main_layout.addWidget(self.edit_panel)

        # 2. Zone droite (Canvas + barre inférieure de transport)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.canvas = PicasaImageCanvas(self.style, self)
        right_layout.addWidget(self.canvas, 1)

        # 3. Barre inférieure de commandes de transport
        self.transport_bar = self._create_transport_bar()
        right_layout.addWidget(self.transport_bar)

        main_layout.addWidget(right_container, 1)

    def _create_transport_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet("""
            QWidget {
                background-color: #242629;
                border-top: 1px solid #141517;
            }
            QPushButton {
                background-color: #383C42;
                color: #FFFFFF;
                border: 1px solid #4D525A;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #484D55;
            }
            QPushButton:pressed {
                background-color: #26292E;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #50545C;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #DDDDDD;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(10)

        # Navigation Précédente / Suivante
        self.btn_prev = QPushButton("◀ Précédente")
        self.btn_prev.clicked.connect(self.navigate_previous)
        layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Suivante ▶")
        self.btn_next.clicked.connect(self.navigate_next)
        layout.addWidget(self.btn_next)

        layout.addSpacing(16)

        # Rotations rapides
        self.btn_rot_left = QPushButton("↶ 90°")
        self.btn_rot_left.setToolTip("Pivoter vers la gauche (Ctrl+Maj+R)")
        self.btn_rot_left.clicked.connect(self.canvas.rotate_counterclockwise)
        layout.addWidget(self.btn_rot_left)

        self.btn_rot_right = QPushButton("↷ 90°")
        self.btn_rot_right.setToolTip("Pivoter vers la droite (Ctrl+R)")
        self.btn_rot_right.clicked.connect(self.canvas.rotate_clockwise)
        layout.addWidget(self.btn_rot_right)

        layout.addStretch(1)

        # Curseur de zoom
        layout.addWidget(QLabel("Zoom :"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(lambda v: self.canvas.set_zoom(v / 100.0))
        layout.addWidget(self.zoom_slider)

        self.btn_fit = QPushButton("Ajuster")
        self.btn_fit.clicked.connect(self.canvas.reset_zoom_to_fit)
        layout.addWidget(self.btn_fit)

        layout.addSpacing(10)

        # Bouton Affichage des balises de visages (Ref: 0x008AAD76)
        self.btn_toggle_faces = QPushButton("Visages (On)")
        self.btn_toggle_faces.setCheckable(True)
        self.btn_toggle_faces.setChecked(True)
        self.btn_toggle_faces.toggled.connect(self._on_toggle_face_tags)
        layout.addWidget(self.btn_toggle_faces)

        return bar

    def _on_toggle_face_tags(self, checked: bool) -> None:
        self.btn_toggle_faces.setText("Visages (On)" if checked else "Visages (Off)")
        self.canvas.set_show_face_tags(checked)

    def open_photo(self, db: PicasaDatabase, index: int, available_indices: List[int]) -> None:
        self.db = db
        self.current_index = index
        self.available_indices = available_indices
        self._history.clear()
        self._history_idx = -1

        # Charger les balises de visages associées à cette photo
        faces = db.face_manager.get_faces_for_photo(index)
        self.canvas.set_face_rects(faces)

        if index < 0 or index >= len(db.index):
            return

        entry = db.index[index]
        path_str = entry.path

        # Vérifier si le fichier existe sur disque
        p = Path(path_str)
        pil_img: Optional[Image.Image] = None
        if p.exists():
            try:
                pil_img = Image.open(str(p)).convert("RGB")
            except Exception:
                pass

        # Si pas sur disque, charger depuis la base thumbs
        if pil_img is None:
            raw_thumb = db.load_thumbnail(index)
            if raw_thumb:
                import io
                try:
                    pil_img = Image.open(io.BytesIO(raw_thumb)).convert("RGB")
                except Exception:
                    pass

        if pil_img:
            self._history = [pil_img.copy()]
            self._history_idx = 0
            self._display_current_history()

    def _display_current_history(self) -> None:
        if self._history_idx < 0 or self._history_idx >= len(self._history):
            return

        img = self._history[self._history_idx]
        # Convertir PIL -> QImage -> QPixmap
        import io
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        qimg = QImage()
        qimg.loadFromData(buf.getvalue(), "JPEG")
        self.canvas.set_pixmap_direct(QPixmap.fromImage(qimg))

    def _push_history(self, img: Image.Image) -> None:
        # Tronquer si on a annulé des actions
        self._history = self._history[: self._history_idx + 1]
        self._history.append(img.copy())
        self._history_idx = len(self._history) - 1
        self._display_current_history()

    def _on_apply_effect(self, effect_name: str, params: dict) -> None:
        if self._history_idx < 0 or not self._history:
            return

        current_img = self._history[self._history_idx]
        new_img: Optional[Image.Image] = None

        if effect_name == "autocontrast" or effect_name == "lucky":
            new_img = PicasaImageProcessor.auto_contrast(current_img)
        elif effect_name == "autocolor":
            new_img = PicasaImageProcessor.auto_color(current_img)
        elif effect_name == "bw":
            new_img = PicasaImageProcessor.black_and_white(current_img)
        elif effect_name == "sepia":
            new_img = PicasaImageProcessor.sepia(current_img)
        elif effect_name == "warmify":
            new_img = PicasaImageProcessor.warmify(current_img)
        elif effect_name == "sharpen":
            new_img = PicasaImageProcessor.sharpen(current_img)
        elif effect_name == "grain":
            new_img = PicasaImageProcessor.film_grain(current_img)
        elif effect_name == "fill_light":
            amt = params.get("amount", 0.3)
            new_img = PicasaImageProcessor.fill_light(current_img, amt)

        if new_img:
            self._push_history(new_img)

    def _on_undo(self) -> None:
        if self._history_idx > 0:
            self._history_idx -= 1
            self._display_current_history()

    def _on_redo(self) -> None:
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self._display_current_history()

    def navigate_previous(self) -> None:
        if not self.available_indices or self.db is None:
            return
        try:
            curr_pos = self.available_indices.index(self.current_index)
            if curr_pos > 0:
                prev_idx = self.available_indices[curr_pos - 1]
                self.open_photo(self.db, prev_idx, self.available_indices)
        except ValueError:
            pass

    def navigate_next(self) -> None:
        if not self.available_indices or self.db is None:
            return
        try:
            curr_pos = self.available_indices.index(self.current_index)
            if curr_pos < len(self.available_indices) - 1:
                next_idx = self.available_indices[curr_pos + 1]
                self.open_photo(self.db, next_idx, self.available_indices)
        except ValueError:
            pass

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Left:
            self.navigate_previous()
        elif event.key() == Qt.Key.Key_Right:
            self.navigate_next()
        elif event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.back_to_library_requested.emit()
        else:
            super().keyPressEvent(event)
