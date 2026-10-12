"""
One-Up & Two-Up View Component for PyCasa (Single & Dual Photo Viewer & Editor).
Assembles the Edit Panel, Image Canvas, Viewer Top Bar, and Transport Controls.

Ref: picasa3.exe @ OneUp, AVOneUpUI, editoneup
Ref: picasa3.exe @ TwoUp, TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
Ref: AGENTS.md §4 bis (Mode visualiseur/retouche fidèle, barre supérieure et comparaison A B|A A|A)
"""

from __future__ import annotations
import os
import io
from pathlib import Path
from typing import List, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider, QFrame,
    QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
from PIL import Image

# Permettre l'ouverture des images gigapixel et panoramiques sans limitation de décompression
Image.MAX_IMAGE_PIXELS = None

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.image_canvas import PicasaImageCanvas
from picasa_py.ui.edit_panel import PicasaEditPanel
from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.ui.right_drawer import PicasaRightDrawer
from picasa_py.db.database import PicasaDatabase


# Ref: picasa3.exe @ OneUp, TwoUp
class PicasaOneUpView(QWidget):
    """
    Vue d'édition d'une image unique (« One-Up View ») ou comparaison (« Two-Up View »)
    avec barre de contrôle supérieure, retouche, comparaison A B|A A|A et navigation.
    """
    back_to_library_requested = Signal()
    photo_modified = Signal(int, dict)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.db: Optional[PicasaDatabase] = None
        self.current_index: int = -1
        self.secondary_index: int = -1
        self.available_indices: List[int] = []

        # Historique de retouche pour Annuler/Rétablir
        self._history: List[Image.Image] = []
        self._history_idx: int = -1
        self._original_pil_img: Optional[Image.Image] = None

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

        # 2. Zone droite (Barre supérieure + Canvas + barre inférieure de transport)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Barre supérieure de navigation et de comparaison (Ref: TwoUp, TwoUpAB, TwoUpAA)
        self.viewer_top_bar = self._create_viewer_top_bar()
        right_layout.addWidget(self.viewer_top_bar)

        self.canvas = PicasaImageCanvas(self.style, self)
        self.canvas.active_pane_changed.connect(self._on_active_pane_changed)
        right_layout.addWidget(self.canvas, 1)

        # 3. Barre inférieure de commandes de transport
        self.transport_bar = self._create_transport_bar()
        right_layout.addWidget(self.transport_bar)

        main_layout.addWidget(right_container, 1)

        # 4. Volet latéral droit escamotable (Personnes, Lieux, Tags, Propriétés)
        self.right_drawer = PicasaRightDrawer(self.style, self)
        self.right_drawer.hide()
        self.right_drawer.drawer_closed.connect(self._on_drawer_closed)
        self.right_drawer.panel_changed.connect(self._on_drawer_panel_changed)
        self.right_drawer.panel_people.face_hovered.connect(self._on_drawer_face_hovered)
        main_layout.addWidget(self.right_drawer)

    def _create_viewer_top_bar(self) -> QWidget:
        """
        Barre supérieure du visualiseur Picasa 3 contenant la navigation d'image
        et le sélecteur de comparaison côte à côte [A] [A | B] [A | A].
        Ref: picasa3.exe @ TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
        """
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet("""
            QWidget {
                background-color: #202226;
                border-bottom: 1px solid #141517;
            }
            QPushButton {
                background-color: #32353B;
                color: #DDDDDD;
                border: 1px solid #43474F;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #40444B;
                color: #FFFFFF;
                border-color: #555B66;
            }
            QPushButton:pressed {
                background-color: #202225;
            }
            QPushButton:checked {
                background-color: #25648B;
                color: #FFFFFF;
                border: 1px solid #3399FF;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # 1. Bouton Retour à la bibliothèque
        self.btn_top_back = QPushButton("◀ Bibliothèque")
        self.btn_top_back.setToolTip("Revenir à la bibliothèque (Échap ou Entrée)")
        self.btn_top_back.clicked.connect(self.back_to_library_requested.emit)
        layout.addWidget(self.btn_top_back)

        layout.addSpacing(6)

        # 2. Boutons de navigation précédente / suivante
        self.btn_top_prev = QPushButton("◀")
        self.btn_top_prev.setFixedWidth(28)
        self.btn_top_prev.setToolTip("Photo précédente (Flèche Gauche)")
        self.btn_top_prev.clicked.connect(self.navigate_previous)
        layout.addWidget(self.btn_top_prev)

        self.btn_top_next = QPushButton("▶")
        self.btn_top_next.setFixedWidth(28)
        self.btn_top_next.setToolTip("Photo suivante (Flèche Droite)")
        self.btn_top_next.clicked.connect(self.navigate_next)
        layout.addWidget(self.btn_top_next)

        # 3. Libellé d'informations de la photo en cours
        self.lbl_top_info = QLabel("")
        self.lbl_top_info.setStyleSheet("color: #E2E2E2; font-weight: bold; padding-left: 6px;")
        layout.addWidget(self.lbl_top_info)

        layout.addStretch(1)

        # 4. Groupe de boutons de comparaison côte à côte (Ref: picasa3.exe @ TwoUp, TwoUpAB, TwoUpAA)
        layout.addWidget(QLabel("Affichage :"))

        self.btn_mode_a = QPushButton("A")
        self.btn_mode_a.setCheckable(True)
        self.btn_mode_a.setChecked(True)
        self.btn_mode_a.setToolTip("Vue unique standard (A)")

        self.btn_mode_ab = QPushButton("A | B")
        self.btn_mode_ab.setCheckable(True)
        self.btn_mode_ab.setToolTip("Comparer deux photos différentes côte à côte (A | B)")

        self.btn_mode_aa = QPushButton("A | A")
        self.btn_mode_aa.setCheckable(True)
        self.btn_mode_aa.setToolTip("Comparer la photo originale et la version retouchée côte à côte (A | A)")

        self.mode_btn_group = QButtonGroup(bar)
        self.mode_btn_group.addButton(self.btn_mode_a, 0)
        self.mode_btn_group.addButton(self.btn_mode_ab, 1)
        self.mode_btn_group.addButton(self.btn_mode_aa, 2)
        self.mode_btn_group.idClicked.connect(self._on_view_mode_changed)

        layout.addWidget(self.btn_mode_a)
        layout.addWidget(self.btn_mode_ab)
        layout.addWidget(self.btn_mode_aa)

        return bar

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
        self.canvas.zoom_changed.connect(self._on_canvas_zoom_changed)
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

        # Séparateur vertical
        sep_drawer = QFrame()
        sep_drawer.setFrameShape(QFrame.Shape.VLine)
        sep_drawer.setStyleSheet("color: #404550;")
        layout.addWidget(sep_drawer)

        # 4 Boutons du panneau latéral droit (Ref: thumbui/people_toggle, places_toggle, tags_toggle, properties_toggle)
        self.btn_panel_people = QPushButton("👤 Personnes")
        self.btn_panel_people.setCheckable(True)
        self.btn_panel_people.setToolTip("Afficher/masquer le panneau des personnes")
        self.btn_panel_people.clicked.connect(lambda: self.toggle_drawer_panel("people"))
        layout.addWidget(self.btn_panel_people)

        self.btn_panel_places = QPushButton("📍 Lieux")
        self.btn_panel_places.setCheckable(True)
        self.btn_panel_places.setToolTip("Afficher/masquer le panneau des lieux (Carte Leaflet)")
        self.btn_panel_places.clicked.connect(lambda: self.toggle_drawer_panel("places"))
        layout.addWidget(self.btn_panel_places)

        self.btn_panel_tags = QPushButton("🏷️ Tags")
        self.btn_panel_tags.setCheckable(True)
        self.btn_panel_tags.setToolTip("Afficher/masquer le panneau des tags")
        self.btn_panel_tags.clicked.connect(lambda: self.toggle_drawer_panel("tags"))
        layout.addWidget(self.btn_panel_tags)

        self.btn_panel_props = QPushButton("ℹ️ Propriétés")
        self.btn_panel_props.setCheckable(True)
        self.btn_panel_props.setToolTip("Afficher/masquer le panneau des propriétés (Données EXIF)")
        self.btn_panel_props.clicked.connect(lambda: self.toggle_drawer_panel("properties"))
        layout.addWidget(self.btn_panel_props)

        return bar

    def toggle_drawer_panel(self, panel_name: str) -> None:
        """
        Bascule l'ouverture/fermeture du volet latéral droit pour le panneau demandé.
        Ref: picasa3.exe @ thumbui/people_toggle, places_toggle, tags_toggle, properties_toggle
        """
        self.right_drawer.toggle_panel(panel_name)
        self._update_drawer_buttons_state()

    def _on_drawer_closed(self) -> None:
        self._update_drawer_buttons_state()

    def _on_drawer_panel_changed(self, panel_name: str) -> None:
        self._update_drawer_buttons_state()

    def _on_drawer_face_hovered(self, face_idx: int) -> None:
        self.canvas.hovered_face_idx = face_idx
        self.canvas.update()

    def _update_drawer_buttons_state(self) -> None:
        is_open = self.right_drawer.isVisible()
        curr = self.right_drawer.current_panel_name if is_open else ""
        self.btn_panel_people.setChecked(is_open and curr == "people")
        self.btn_panel_places.setChecked(is_open and curr == "places")
        self.btn_panel_tags.setChecked(is_open and curr == "tags")
        self.btn_panel_props.setChecked(is_open and curr == "properties")

    def _on_canvas_zoom_changed(self, zoom: float) -> None:
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(zoom * 100))
        self.zoom_slider.blockSignals(False)

    def _on_toggle_face_tags(self, checked: bool) -> None:
        self.btn_toggle_faces.setText("Visages (On)" if checked else "Visages (Off)")
        self.canvas.set_show_face_tags(checked)

    def _on_view_mode_changed(self, mode_id: int) -> None:
        """
        Bascule entre les modes de comparaison :
        0: A (vue simple)
        1: A | B (2 photos côte à côte)
        2: A | A (avant / après retouches)
        Ref: picasa3.exe @ TwoUpAB, TwoUpAA
        """
        if mode_id == 0:
            self.canvas.set_view_mode("A")
        elif mode_id == 1:
            self.canvas.set_view_mode("A_B")
            self._load_secondary_photo()
        elif mode_id == 2:
            self.canvas.set_view_mode("A_A")
            if self._original_pil_img:
                orig_pix = self._pil_to_pixmap(self._original_pil_img)
                self.canvas.set_original_pixmap(orig_pix)

        self._update_top_bar_info()

    def _on_active_pane_changed(self, pane: str) -> None:
        self._update_top_bar_info()

    def _load_pil_image_at_index(self, index: int, direct_path: Optional[str] = None) -> Optional[Image.Image]:
        """Charge une image PIL haute résolution depuis le disque ou le cache."""
        if self.db is None or index < 0 or index >= len(self.db.index):
            return None

        # Priorité au chemin direct connu ou reconstitution depuis thumbindex.db
        full_path = direct_path if (direct_path and os.path.exists(direct_path)) else self.db.get_media_full_path(index)
        pil_img: Optional[Image.Image] = None

        if full_path and os.path.exists(full_path):
            try:
                with Image.open(full_path) as raw_img:
                    # Gérer les palettes avec transparence pour éviter UserWarning de PIL
                    if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                        raw_img = raw_img.convert("RGBA")
                    from PIL import ImageOps
                    try:
                        pil_img = ImageOps.exif_transpose(raw_img)
                    except Exception:
                        pil_img = raw_img
                    if pil_img.mode not in ("RGB", "RGBA"):
                        pil_img = pil_img.convert("RGB")
                    # Forcer le décodage effectif des données en RAM avant de fermer le descripteur de fichier
                    pil_img.load()
            except Exception:
                pass

        if pil_img is None:
            for sz in ("preview", "large", "medium", "small"):
                raw_thumb = self.db.load_thumbnail(index, size=sz)
                if raw_thumb:
                    try:
                        with Image.open(io.BytesIO(raw_thumb)) as thumb_raw:
                            if thumb_raw.mode in ("P", "PA") or "transparency" in thumb_raw.info:
                                thumb_raw = thumb_raw.convert("RGBA")
                            if thumb_raw.mode not in ("RGB", "RGBA"):
                                thumb_raw = thumb_raw.convert("RGB")
                            pil_img = thumb_raw.copy()
                            break
                    except Exception:
                        pass

        return pil_img

    def _pil_to_pixmap(self, img: Image.Image) -> QPixmap:
        """
        Convertit une image PIL en QPixmap de façon directe et ultra-rapide en mémoire.
        Évite le goulot d'étranglement de ré-encodage JPEG et la limite d'allocation Qt.
        """
        if img.mode in ("P", "PA") or "transparency" in img.info:
            img = img.convert("RGBA")

        if img.mode == "RGBA":
            bgra_data = img.tobytes("raw", "BGRA")
            qimg = QImage(bgra_data, img.width, img.height, img.width * 4, QImage.Format.Format_ARGB32).copy()
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            rgb_data = img.tobytes("raw", "RGB")
            qimg = QImage(rgb_data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888).copy()

        return QPixmap.fromImage(qimg)

    def open_photo(
        self,
        db: PicasaDatabase,
        index: int,
        available_indices: List[int],
        direct_path: Optional[str] = None
    ) -> None:
        self.db = db
        self.current_index = index
        self.available_indices = available_indices
        self._history.clear()
        self._history_idx = -1

        faces = db.face_manager.get_faces_for_photo(index)
        self.canvas.set_face_rects(faces)

        if index < 0 or index >= len(db.index):
            return

        pil_img = self._load_pil_image_at_index(index, direct_path=direct_path)
        if pil_img:
            self._original_pil_img = pil_img.copy()
            self._history = [pil_img.copy()]
            self._history_idx = 0
            self._display_current_history()

            orig_pix = self._pil_to_pixmap(self._original_pil_img)
            self.canvas.set_original_pixmap(orig_pix)

        filename = os.path.basename(db.index[index].path)
        self.canvas.main_title = filename

        # Si en mode A|B, charger automatiquement la photo secondaire
        if self.canvas.view_mode == "A_B":
            self._load_secondary_photo()

        # Mettre à jour le volet latéral droit (Personnes, Lieux, Tags, Propriétés)
        full_path = direct_path if (direct_path and os.path.exists(direct_path)) else (self.db.get_media_full_path(index) if self.db else None)
        self.right_drawer.set_current_photo(db, index, full_path or "")

        self._update_top_bar_info()

    def _load_secondary_photo(self) -> None:
        """Charge la photo B pour le mode de comparaison A | B."""
        if not self.available_indices or self.db is None:
            return

        # Par défaut, sélectionner la photo suivante dans la liste
        if (
            self.secondary_index < 0
            or self.secondary_index not in self.available_indices
            or self.secondary_index == self.current_index
        ):
            try:
                curr_pos = self.available_indices.index(self.current_index)
                sec_pos = (curr_pos + 1) % len(self.available_indices)
                self.secondary_index = self.available_indices[sec_pos]
            except ValueError:
                self.secondary_index = self.available_indices[0]

        sec_img = self._load_pil_image_at_index(self.secondary_index)
        if sec_img:
            sec_pix = self._pil_to_pixmap(sec_img)
            sec_filename = os.path.basename(self.db.index[self.secondary_index].path)
            self.canvas.set_secondary_pixmap(sec_pix, sec_filename)
        else:
            self.canvas.set_secondary_pixmap(None, "Aucune")

        self._update_top_bar_info()

    def _update_top_bar_info(self) -> None:
        """Met à jour l'intitulé informatif de la photo dans la barre supérieure."""
        if self.db is None or self.current_index < 0:
            self.lbl_top_info.setText("")
            return

        total = len(self.available_indices)
        curr_pos = -1
        try:
            curr_pos = self.available_indices.index(self.current_index)
        except ValueError:
            pass

        filename = os.path.basename(self.db.index[self.current_index].path) if self.current_index < len(self.db.index) else ""

        if self.canvas.view_mode == "A":
            pos_str = f"Photo {curr_pos + 1} sur {total}" if curr_pos >= 0 else ""
            self.lbl_top_info.setText(f"{pos_str}  •  {filename}")
        elif self.canvas.view_mode == "A_B":
            sec_name = self.canvas.secondary_title
            active_info = " (Active)" if self.canvas.active_pane == "B" else ""
            self.lbl_top_info.setText(f"Comparaison A | B  •  Photo A: {filename}  vs  Photo B: {sec_name}{active_info}")
        elif self.canvas.view_mode == "A_A":
            self.lbl_top_info.setText(f"Comparaison A | A  •  Originale (Avant) vs Retouchée (Après) — {filename}")

    def _display_current_history(self) -> None:
        if self._history_idx < 0 or self._history_idx >= len(self._history):
            return

        img = self._history[self._history_idx]
        pix = self._pil_to_pixmap(img)
        self.canvas.set_pixmap_direct(pix)

        if self._original_pil_img:
            orig_pix = self._pil_to_pixmap(self._original_pil_img)
            self.canvas.set_original_pixmap(orig_pix)

    def _push_history(self, img: Image.Image) -> None:
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

        # En mode A|B, si le volet B est actif, on fait défiler la photo B
        if self.canvas.view_mode == "A_B" and self.canvas.active_pane == "B":
            try:
                curr_pos = self.available_indices.index(self.secondary_index)
                if curr_pos > 0:
                    self.secondary_index = self.available_indices[curr_pos - 1]
                    self._load_secondary_photo()
            except ValueError:
                pass
            return

        # En mode A ou A|A, faire défiler la photo principale
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

        # En mode A|B, si le volet B est actif, on fait défiler la photo B
        if self.canvas.view_mode == "A_B" and self.canvas.active_pane == "B":
            try:
                curr_pos = self.available_indices.index(self.secondary_index)
                if curr_pos < len(self.available_indices) - 1:
                    self.secondary_index = self.available_indices[curr_pos + 1]
                    self._load_secondary_photo()
            except ValueError:
                pass
            return

        # En mode A ou A|A, faire défiler la photo principale
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
        elif event.key() == Qt.Key.Key_A:
            # Raccourci A pour basculer en mode A simple
            self.mode_btn_group.button(0).setChecked(True)
            self._on_view_mode_changed(0)
        elif event.key() == Qt.Key.Key_B:
            # Raccourci B pour basculer en mode A|B
            self.mode_btn_group.button(1).setChecked(True)
            self._on_view_mode_changed(1)
        else:
            super().keyPressEvent(event)
