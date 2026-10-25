"""
FR: Composant de visualisation et d'édition d'une image unique (« One-Up View ») ou double (« Two-Up View »).
Assemble le panneau d'édition, le canevas d'image, la barre supérieure et les contrôles de transport.

EN: One-Up & Two-Up View Component for PyCasa (Single & Dual Photo Viewer & Editor).
Assembles the Edit Panel, Image Canvas, Viewer Top Bar, and Transport Controls.

Ref: picasa3.exe @ OneUp, AVOneUpUI, editoneup
Ref: picasa3.exe @ TwoUp, TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
Ref: AGENTS.md §4 bis (Mode visualiseur/retouche fidèle, barre supérieure et comparaison A B|A A|A)
"""

from __future__ import annotations
import os
import sys
import io
from pathlib import Path
from typing import Any, List, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider, QFrame,
    QButtonGroup, QStackedWidget, QSplitter, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage
from PIL import Image

# FR: Permettre l'ouverture des images gigapixel et panoramiques sans limitation de décompression
# EN: Allow opening gigapixel and panoramic images without decompression bomb limit
Image.MAX_IMAGE_PIXELS = None

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.image_canvas import PicasaImageCanvas
from picasa_py.ui.edit_panel import PicasaEditPanel
from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.ui.right_drawer import PicasaRightDrawer
from picasa_py.ui.filmstrip import PicasaFilmstrip
from picasa_py.ui.name_face_dialog import PicasaNameFaceDialog
from picasa_py.ui.video_player import PicasaVideoPlayer
from picasa_py.faces.facerect import FaceRect
from picasa_py.db.database import PicasaDatabase
from picasa_py.scanner.scanner import VIDEO_EXTENSIONS


# Ref: picasa3.exe @ OneUp, TwoUp
class PicasaOneUpView(QWidget):
    """
    FR: Vue d'édition d'une image unique (« One-Up View ») ou comparaison (« Two-Up View »)
    avec barre de contrôle supérieure, retouche, comparaison A B|A A|A et navigation.
    EN: Single-image editor view ("One-Up View") or comparison view ("Two-Up View")
    with top control bar, editing tools, A B|A A|A comparison, and navigation.
    """
    back_to_library_requested = Signal()
    photo_modified = Signal(int, dict)
    photo_edited = Signal(str)
    slideshow_requested = Signal()
    people_changed = Signal()
    star_toggled = Signal(str, bool)  # file_path, is_starred (Ref: ID_PICTURE_STAR, star=yes)
    current_photo_changed = Signal(int, str)  # db_index, file_path (Ref: 0x005683A0 RefreshOneUpView)

    @property
    def current_photo_path(self) -> Optional[str]:
        """
        FR: Retourne le chemin complet du fichier média actuellement ouvert dans la vue.
        EN: Returns the full file path of the media item currently open in the view.
        """
        if self._current_photo_path:
            return self._current_photo_path
        if self.db and 0 <= self.current_index < len(self.db.index):
            return self.db.get_media_full_path(self.current_index)
        return None

    @current_photo_path.setter
    def current_photo_path(self, val: Optional[str]) -> None:
        """
        FR: Définit explicitement le chemin complet du fichier média actuellement ouvert.
        EN: Explicitly sets the full file path of the currently open media item.
        """
        self._current_photo_path = val

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise la vue d'édition One-Up/Two-Up, ses barres d'outils, son canevas et ses volets latéraux.
        EN: Initializes the One-Up/Two-Up editor view, its toolbars, image canvas, and side drawers.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.db: Optional[PicasaDatabase] = None
        self.current_index: int = -1
        self.secondary_index: int = -1
        self.available_indices: List[int] = []
        self._current_photo_path: Optional[str] = None

        # FR: Historique de retouche pour Annuler/Rétablir
        # EN: Edit history stack for Undo/Redo
        self._history: List[Image.Image] = []
        self._history_ini_snapshots: List[Optional[str]] = []
        self._history_idx: int = -1
        self._original_pil_img: Optional[Image.Image] = None
        self._raw_unedited_pil_img: Optional[Image.Image] = None
        self._orig_backup_path: Optional[str] = None
        self._orig_backup_loaded: bool = False
        # FR: Images de référence non-cumulatives pour les curseurs de réglage (Tab 1/2) et l'aperçu des filtres (Tab 3/4/5)
        # EN: Non-cumulative reference images for tuning sliders (Tab 1/2) and filter previews (Tab 3/4/5)
        self._tuning_base_img: Optional[Image.Image] = None
        self._tuning_history_slot: int = -1
        self._effect_preview_base_img: Optional[Image.Image] = None
        self._fast_preview_base_source: Optional[Image.Image] = None
        self._fast_preview_base_img: Optional[Image.Image] = None
        self._pending_full_res_preview: Optional[Tuple[str, Any, Any]] = None
        self._original_pixmap_dirty: bool = True
        self._full_res_preview_timer = QTimer(self)
        self._full_res_preview_timer.setSingleShot(True)
        self._full_res_preview_timer.setInterval(75)
        self._full_res_preview_timer.timeout.connect(self._flush_full_res_preview)
        self._pending_thumb_db_sync: Optional[Tuple[int, Image.Image, str]] = None
        self._thumb_db_sync_timer = QTimer(self)
        self._thumb_db_sync_timer.setSingleShot(True)
        self._thumb_db_sync_timer.setInterval(350)
        self._thumb_db_sync_timer.timeout.connect(self._flush_pending_thumb_db_sync)

        # FR: Paramètres de transformation d'affichage active (crop, tilt, rotate)
        # EN: Active display transformation parameters (crop, tilt, rotate)
        self._active_crop_rect: Optional[Tuple[float, float, float, float]] = None
        self._active_tilt: float = 0.0
        self._active_rotate: int = 0
        self._is_tool_locked: bool = False
        self._active_tool_mode: int = 0
        self._use_external_bottom_bar: bool = False

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # FR: 1. Volet gauche d'édition
        # EN: 1. Left editing panel
        self.edit_panel = PicasaEditPanel(self.style, self)
        self.edit_panel.back_to_library.connect(self._on_back_to_library_clicked)
        self.edit_panel.modal_tool_lock_changed.connect(self._set_modal_tool_lock)
        self.edit_panel.apply_effect.connect(self._on_apply_effect)
        self.edit_panel.tuning_preview_changed.connect(self._on_tuning_preview_changed)
        self.edit_panel.tuning_applied.connect(self._on_tuning_applied)
        self.edit_panel.effect_preview_requested.connect(self._on_effect_preview_requested)
        self.edit_panel.effect_applied.connect(self._on_effect_applied)
        self.edit_panel.effect_cancelled.connect(self._on_effect_cancelled)
        self.edit_panel.undo_action.connect(self._on_undo)
        self.edit_panel.redo_action.connect(self._on_redo)
        self.edit_panel.save_action.connect(self.save_current_photo)
        self.edit_panel.crop_requested.connect(self._on_crop_start)
        self.edit_panel.crop_apply.connect(self._on_crop_apply)
        self.edit_panel.crop_discard.connect(self._on_crop_discard)
        self.edit_panel.straighten_requested.connect(self._on_straighten_start)
        self.edit_panel.straighten_apply.connect(self._on_straighten_apply)
        self.edit_panel.text_tool_requested.connect(self._on_text_tool_start)
        self.edit_panel.text_params_changed.connect(self._on_text_params_changed)
        self.edit_panel.text_apply.connect(self._on_text_apply)
        main_layout.addWidget(self.edit_panel)

        # FR: 2. Zone droite (Barre supérieure + Canvas + barre inférieure de transport)
        # EN: 2. Right area (Top bar + Canvas + bottom transport bar)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # FR: Barre supérieure de navigation et de comparaison (Ref: TwoUp, TwoUpAB, TwoUpAA)
        # EN: Top navigation and comparison bar (Ref: TwoUp, TwoUpAB, TwoUpAA)
        self.viewer_top_bar = self._create_viewer_top_bar()
        self.viewer_top_bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.viewer_top_bar)

        # FR: Conteneur central empilé (Canvas pour photos vs Video Player pour vidéos)
        # EN: Central stacked container (Canvas for photos vs Video Player for videos)
        self.center_stack = QStackedWidget(right_container)
        self.center_stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self.canvas = PicasaImageCanvas(self.style, self)
        self.canvas.active_pane_changed.connect(self._on_active_pane_changed)
        self.canvas.context_menu_requested.connect(self._on_canvas_context_menu)
        self.canvas.straighten_interactive_angle_changed.connect(self.edit_panel.straighten_subpanel.set_angle_from_canvas)
        self.canvas.retouch_applied.connect(self._on_canvas_retouch)
        self.canvas.redeye_applied.connect(self._on_canvas_redeye_point)
        self.canvas.redeye_box_applied.connect(self._on_canvas_redeye_box)
        self.edit_panel.crop_ratio_changed.connect(self.canvas.set_crop_aspect_ratio)
        self.edit_panel.crop_cancel.connect(self.canvas.cancel_crop)
        self.edit_panel.straighten_angle_changed.connect(self.canvas.set_straighten_angle)
        self.edit_panel.straighten_cancel.connect(self.canvas.cancel_straighten)
        self.edit_panel.straighten_reset.connect(lambda: self.canvas.set_straighten_angle(0.0))
        self.edit_panel.text_cancel.connect(self.canvas.cancel_text_tool)
        self.edit_panel.redeye_requested.connect(lambda: self.canvas.start_redeye())
        self.edit_panel.redeye_apply.connect(self._on_redeye_apply)
        self.edit_panel.redeye_cancel.connect(self.canvas.cancel_redeye)
        self.edit_panel.retouch_requested.connect(lambda: self.canvas.start_retouch(self.edit_panel.retouch_subpanel.slider_radius.value() / 500.0))
        self.edit_panel.retouch_apply.connect(self._on_retouch_apply)
        self.edit_panel.retouch_cancel.connect(self.canvas.cancel_retouch)
        self.edit_panel.retouch_radius_changed.connect(self.canvas.set_retouch_radius)
        self.edit_panel.neutral_color_picker_toggled.connect(self.canvas.set_pipette_mode)
        self.canvas.neutral_color_picked.connect(self._on_neutral_color_picked)
        self.center_stack.addWidget(self.canvas)

        self.video_player = PicasaVideoPlayer(self.style, self)
        self.video_player.top_bar.hide()
        self.video_player.back_requested.connect(self.back_to_library_requested.emit)
        self.video_player.snapshot_captured.connect(self._on_video_snapshot_captured)
        self.center_stack.addWidget(self.video_player)

        right_layout.addWidget(self.center_stack, 1)

        # FR: 2 bis. Barre de légende éditable en ligne sous l'image (Ref: picasa3.exe @ editpanel/captionbutton)
        # EN: 2 bis. Inline editable caption bar below the image (Ref: picasa3.exe @ editpanel/captionbutton)
        self.caption_bar = self._create_caption_bar()
        self.caption_bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.caption_bar)

        # FR: 3. Barre inférieure de commandes de transport
        # EN: 3. Bottom transport controls bar
        self.transport_bar = self._create_transport_bar()
        self.transport_bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.transport_bar)

        # FR: 4. Volet central + tiroir latéral droit escamotable dans un QSplitter
        # EN: 4. Central pane + collapsible right side drawer inside a QSplitter
        self.right_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.right_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #141517;
            }
        """)
        self.right_splitter.addWidget(right_container)

        self.right_drawer = PicasaRightDrawer(self.style, self)
        self.right_drawer.hide()
        self.right_drawer.drawer_closed.connect(self._on_drawer_closed)
        self.right_drawer.panel_changed.connect(self._on_drawer_panel_changed)
        self.right_drawer.panel_people.face_hovered.connect(self._on_drawer_face_hovered)
        self.right_drawer.panel_people.manual_add_requested.connect(self._on_manual_face_add_start)
        self.right_drawer.panel_people.faces_updated.connect(self.canvas.set_face_rects)
        self.right_drawer.people_changed.connect(self.people_changed)
        self.canvas.manual_face_defined.connect(self._on_manual_face_defined)
        self.canvas.face_clicked.connect(self._on_canvas_face_clicked)

        self.right_splitter.addWidget(self.right_drawer)
        self.right_splitter.setCollapsible(0, False)
        self.right_splitter.setCollapsible(1, True)
        self.right_splitter.setSizes([900, 300])
        main_layout.addWidget(self.right_splitter, 1)
        self.apply_style(self.style)


    def _create_viewer_top_bar(self) -> QWidget:
        """
        FR: Barre supérieure du visualiseur Picasa 3 (`editpanel/oneup_controls`, rect=(280, 0, 800, 37)).
        Disposition gauche -> droite fidèle à `editpanel.tre` :
        - Gauche (X=290..384) : `editpanel/sbutton` (▶ Diaporama)
        - Centre (X=394..682) : `editpanel/filmcontainer` (◀ prev, filmstrip, ▶ next)
        - Droite (X=596..795) : `editpanel/layout_2up_group` (`only_1up_toggle` [A], `ab_2up_toggle` [A|B], `aa_2up_toggle` [A|A])

        EN: Picasa 3 viewer top bar (`editpanel/oneup_controls`, rect=(280, 0, 800, 37)).
        Left-to-right layout faithful to `editpanel.tre`:
        - Left (X=290..384): `editpanel/sbutton` (▶ Slideshow)
        - Center (X=394..682): `editpanel/filmcontainer` (◀ prev, filmstrip, ▶ next)
        - Right (X=596..795): `editpanel/layout_2up_group` (`only_1up_toggle` [A], `ab_2up_toggle` [A|B], `aa_2up_toggle` [A|A])

        Ref: respack.yt @ editpanel.tre (oneup_controls, sbutton, filmcontainer, layout_2up_group)
        Ref: picasa3.exe @ TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
        """
        bar = QWidget()
        bar.setFixedHeight(48)
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
                padding: 3px 8px;
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
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        # FR: Note : Dans editpanel.tre, le bouton "Retour à la photothèque" (editpanel/albumview)
        # est uniquement en haut à gauche du panneau d'édition (X=10..132). On garde btn_top_back caché pour compatibilité.
        # EN: Note: In editpanel.tre, the "Back to Library" button (editpanel/albumview)
        # is only at the top-left of the edit panel (X=10..132). We keep btn_top_back hidden for compatibility.
        self.btn_top_back = QPushButton("◀ Bibliothèque", bar)
        self.btn_top_back.hide()
        self.btn_top_back.clicked.connect(self.back_to_library_requested.emit)

        # FR: 1. editpanel/sbutton : rect=(290, 9, 384, 31) -> 94x22 px (▶ Diaporama à gauche de oneup_controls)
        # EN: 1. editpanel/sbutton: rect=(290, 9, 384, 31) -> 94x22 px (▶ Slideshow on the left of oneup_controls)
        self.btn_top_slideshow = QPushButton("▶ Diaporama")
        self.btn_top_slideshow.setToolTip("Lancer le diaporama plein écran (Ctrl+4)")
        self.btn_top_slideshow.clicked.connect(self.slideshow_requested.emit)
        layout.addWidget(self.btn_top_slideshow)

        layout.addStretch(1)

        # FR: 2. editpanel/filmcontainer : rect=(394, 3, 682, 36) -> prev (399..428) + filmstrip (431..645) + next (651..680)
        #     Centré horizontalement (`m_centerX`) dans `editpanel/oneup_controls` et toujours visible en modes A, A|B et A|A.
        # EN: 2. editpanel/filmcontainer: rect=(394, 3, 682, 36) -> prev (399..428) + filmstrip (431..645) + next (651..680)
        #     Horizontally centered (`m_centerX`) in `editpanel/oneup_controls` and always visible in A, A|B, and A|A modes.
        self.btn_top_prev = QPushButton("◀")
        self.btn_top_prev.setFixedSize(29, 32)
        self.btn_top_prev.setToolTip("Photo précédente (Flèche Gauche)")
        self.btn_top_prev.clicked.connect(self.navigate_previous)
        layout.addWidget(self.btn_top_prev)

        self.filmstrip = PicasaFilmstrip(thumb_size=34, spacing=5, parent=bar)
        self.filmstrip.setMinimumWidth(214)
        self.filmstrip.setMaximumWidth(360)
        self.filmstrip.photo_clicked.connect(self._on_filmstrip_photo_clicked)
        layout.addWidget(self.filmstrip, 2)

        self.btn_top_next = QPushButton("▶")
        self.btn_top_next.setFixedSize(29, 32)
        self.btn_top_next.setToolTip("Photo suivante (Flèche Droite)")
        self.btn_top_next.clicked.connect(self.navigate_next)
        layout.addWidget(self.btn_top_next)

        layout.addStretch(1)

        # FR: Note : Dans picasa3.exe, les informations de la photo sont affichées dans `thumbui/infotext`
        #     (au-dessus de la barre inférieure) et non dans `editpanel/oneup_controls`. On garde `lbl_top_info`
        #     masqué pour la compatibilité des tests sans écraser la pellicule ni les boutons 2-Up.
        # EN: Note: In picasa3.exe, photo info is displayed in `thumbui/infotext` (above the bottom bar)
        #     and not in `editpanel/oneup_controls`. Keep `lbl_top_info` hidden for test compatibility
        #     without crushing the filmstrip or clipping the 2-Up buttons.
        self.lbl_top_info = QLabel("", bar)
        self.lbl_top_info.hide()

        # FR: 4. editpanel/layout_2up_group : rect=(596, 8, 795, 32) -> only_1up_toggle (596..635), ab_2up_toggle (635..674),
        #     aa_2up_toggle (673..712), swap_2up_focus (720..756, 0x00C8ECFC, FUN_0056A160),
        #     swap_2up_layout (759..795, 0x00C8ED18, FUN_00569720)
        # EN: 4. editpanel/layout_2up_group: rect=(596, 8, 795, 32) -> only_1up_toggle (596..635), ab_2up_toggle (635..674),
        #     aa_2up_toggle (673..712), swap_2up_focus (720..756, 0x00C8ECFC, FUN_0056A160),
        #     swap_2up_layout (759..795, 0x00C8ED18, FUN_0056A160)
        from PySide6.QtCore import QSize
        rm = PicasaResourceManager.get()

        self.btn_mode_a = QPushButton("")
        self.btn_mode_a.setObjectName("editpanel/only_1up_toggle")
        self.btn_mode_a.setFixedSize(39, 26)
        self.btn_mode_a.setIcon(rm.get_2up_button_icon("only_1up", 20))
        self.btn_mode_a.setIconSize(QSize(20, 15))
        self.btn_mode_a.setCheckable(True)
        self.btn_mode_a.setChecked(True)
        self.btn_mode_a.setToolTip(rm.get_xml_string("editpanel/only_1up_toggle.tooltip", "Afficher une seule image"))

        self.btn_mode_ab = QPushButton("")
        self.btn_mode_ab.setObjectName("editpanel/ab_2up_toggle")
        self.btn_mode_ab.setFixedSize(39, 26)
        self.btn_mode_ab.setIcon(rm.get_2up_button_icon("ab_2up", 27))
        self.btn_mode_ab.setIconSize(QSize(27, 15))
        self.btn_mode_ab.setCheckable(True)
        self.btn_mode_ab.setToolTip(rm.get_xml_string("editpanel/ab_2up_toggle.tooltip", "Afficher deux images côte à côte"))

        self.btn_mode_aa = QPushButton("")
        self.btn_mode_aa.setObjectName("editpanel/aa_2up_toggle")
        self.btn_mode_aa.setFixedSize(39, 26)
        self.btn_mode_aa.setIcon(rm.get_2up_button_icon("aa_2up", 27))
        self.btn_mode_aa.setIconSize(QSize(27, 15))
        self.btn_mode_aa.setCheckable(True)
        self.btn_mode_aa.setToolTip(rm.get_xml_string("editpanel/aa_2up_toggle.tooltip", "Afficher deux copies de la même image côte à côte"))

        self.btn_swap_2up_focus = QPushButton("")
        self.btn_swap_2up_focus.setObjectName("editpanel/swap_2up_focus")
        self.btn_swap_2up_focus.setFixedSize(36, 26)
        self.btn_swap_2up_focus.setIcon(rm.get_2up_button_icon("swap_focus", 21))
        self.btn_swap_2up_focus.setIconSize(QSize(21, 15))
        self.btn_swap_2up_focus.setToolTip(
            rm.get_xml_string("editpanel/swap_2up_focus.tooltip", "Modifier l'image sur laquelle porte la mise au point")
        )
        self.btn_swap_2up_focus.hide()
        self.btn_swap_2up_focus.clicked.connect(self._on_swap_2up_focus_clicked)

        self.btn_swap_2up_layout = QPushButton("")
        self.btn_swap_2up_layout.setObjectName("editpanel/swap_2up_layout")
        self.btn_swap_2up_layout.setFixedSize(36, 26)
        self.btn_swap_2up_layout.setIcon(rm.get_2up_button_icon("swap_layout_vert", 22))
        self.btn_swap_2up_layout.setIconSize(QSize(22, 17))
        self.btn_swap_2up_layout.setToolTip(
            rm.get_xml_string("editpanel/swap_2up_layout.tooltip", "Basculer entre l'affichage horizontal et l'affichage vertical")
        )
        self.btn_swap_2up_layout.hide()
        self.btn_swap_2up_layout.clicked.connect(self._on_swap_2up_layout_clicked)

        self.mode_btn_group = QButtonGroup(bar)
        self.mode_btn_group.addButton(self.btn_mode_a, 0)
        self.mode_btn_group.addButton(self.btn_mode_ab, 1)
        self.mode_btn_group.addButton(self.btn_mode_aa, 2)
        self.mode_btn_group.idClicked.connect(self._on_view_mode_changed)

        layout.addWidget(self.btn_mode_a)
        layout.addWidget(self.btn_mode_ab)
        layout.addWidget(self.btn_mode_aa)
        layout.addWidget(self.btn_swap_2up_focus)
        layout.addWidget(self.btn_swap_2up_layout)

        return bar

    def _create_caption_bar(self) -> QWidget:
        """
        FR: Barre de légende éditable en ligne affichée sous la photo dans One-Up View.
        EN: Inline editable caption bar displayed below the photo in One-Up View.

        Ref: respack.yt @ editpanel/caption (rect 280, 411, 706, 428), editpanel/captionbutton (rect 479, 414, 498, 429)
        """
        bar = QWidget()
        bar.setFixedHeight(28)
        bar.setStyleSheet("""
            QWidget {
                background-color: #1C1E22;
                border-top: 1px solid #2A2D34;
            }
            QLineEdit {
                background-color: #262930;
                color: #F0F0F0;
                border: 1px solid #3C414C;
                border-radius: 3px;
                padding: 1px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                background-color: #2E323B;
                border: 1px solid #4A90D9;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 2, 24, 2)
        self.caption_edit = QLineEdit(bar)
        self.caption_edit.setPlaceholderText("Saisissez une légende ici...")
        self.caption_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_edit.editingFinished.connect(self._on_caption_committed)
        layout.addWidget(self.caption_edit, 1)
        return bar

    def _on_caption_committed(self) -> None:
        """
        FR: Enregistre la légende saisie dans .picasa.ini, imagedata_caption.pmp et wordhash.dat via PicasaDatabase.
        EN: Saves the entered caption to .picasa.ini, imagedata_caption.pmp, and wordhash.dat via PicasaDatabase.

        Ref: picasa3.exe @ editpanel/captionbutton, 0x0068AC80, AGENTS.md §4 bis.3
        """
        target_path = self.current_photo_path
        if not target_path or not os.path.exists(target_path):
            return
        caption_val = self.caption_edit.text().strip()

        def _apply_caption(doc, fname: str) -> None:
            """
            FR: Met à jour ou supprime la clé `caption` dans la section du fichier `.picasa.ini`.
            EN: Updates or removes the `caption` key in the `.picasa.ini` file section.
            """
            sec = doc.get_or_create_section(fname)
            if caption_val:
                sec.set("caption", caption_val)
            else:
                sec.remove("caption")

        if self.db is not None:
            self.db.update_photo_ini(target_path, _apply_caption)
        else:
            parent_dir = os.path.dirname(target_path)
            ini_path = os.path.join(parent_dir, ".picasa.ini")
            from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
            doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()
            fname = os.path.basename(target_path)
            _apply_caption(doc, fname)
            doc.write_file(ini_path)
        self.photo_edited.emit(target_path)

    def set_use_external_bottom_bar(self, enabled: bool) -> None:
        """
        FR: Indique que la barre inférieure globale `thumbui/basecontrolset` (`PicasaMainWindow.photo_tray`)
        est utilisée et maintient `self.transport_bar` masquée afin d'éviter toute double barre inférieure.
        EN: Indicates that the global bottom bar `thumbui/basecontrolset` (`PicasaMainWindow.photo_tray`)
        is used and keeps `self.transport_bar` hidden to prevent any duplicate bottom bar.

        Ref: picasa3.exe @ 0x0057BB80..0x0057C3A3 (thumbui/basecontrolset)
        """
        self._use_external_bottom_bar = bool(enabled)
        if self._use_external_bottom_bar and hasattr(self, "transport_bar") and self.transport_bar is not None:
            self.transport_bar.hide()

    def _toggle_left_edit_drawer(self) -> None:
        """
        FR: Bascule l'affichage du volet gauche d'édition (`editpanel/toggle_left_drawer`).
        EN: Toggles the visibility of the left editing panel (`editpanel/toggle_left_drawer`).

        Ref: respack.yt @ editpanel/toggle_left_drawer (Handler varbutton LEFTDRAWEROFFSET 0 -279 1)
        """
        visible = not self.edit_panel.isVisible()
        self.edit_panel.setVisible(visible)
        txt = "◀" if visible else "▶"
        self.btn_toggle_left_drawer.setText(txt)
        win = self.window()
        if win is not None and win is not self and hasattr(win, "photo_tray") and win.photo_tray is not None:
            if hasattr(win.photo_tray, "btn_toggle_left_drawer"):
                win.photo_tray.btn_toggle_left_drawer.setText(txt)

    def _create_transport_bar(self) -> QWidget:
        """
        FR: Barre inférieure de One-Up View alignée sur `editpanel.tre` et `thumbui/basecontrolset` :
        - `editpanel/toggle_left_drawer` (escamotage du volet gauche)
        - `thumbui/startoggle` (☆), `rotateleft` (↶), `rotateright` (↷)
        - `editpanel/zoombuttcontainer` (`fit` Ajuster, `1to1` 1:1) + `zoomslider_container` (curseur de zoom)
        - `thumbui/metadata_group` (4 boutons du tiroir droit : Personnes, Lieux, Tags, Propriétés)

        EN: Bottom transport bar of One-Up View aligned with `editpanel.tre` and `thumbui/basecontrolset`:
        - `editpanel/toggle_left_drawer` (collapsing the left edit drawer)
        - `thumbui/startoggle` (☆), `rotateleft` (↶), `rotateright` (↷)
        - `editpanel/zoombuttcontainer` (`fit` Fit, `1to1` 1:1) + `zoomslider_container` (zoom slider)
        - `thumbui/metadata_group` (4 right-drawer buttons: People, Places, Tags, Properties)

        Ref: respack.yt @ editpanel.tre (toggle_left_drawer, zoombuttcontainer, fit, 1to1, zoomslider_container)
        Ref: respack.yt @ thumbui.tre (startoggle, rotateleft, rotateright, metadata_group)
        """
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet("""
            QWidget {
                background-color: #242629;
                border-top: 1px solid #141517;
            }
            QPushButton {
                background-color: #383C42;
                color: #FFFFFF;
                border: 1px solid #4D525A;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #484D55;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #25648B;
                border-color: #4DA3FF;
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
        layout.setContentsMargins(8, 5, 10, 5)
        layout.setSpacing(6)

        # FR: 1. editpanel/toggle_left_drawer : rect=(1, 430, 16, 446) -> bouton d'escamotage du volet gauche
        # EN: 1. editpanel/toggle_left_drawer: rect=(1, 430, 16, 446) -> left drawer collapse toggle button
        self.btn_toggle_left_drawer = QPushButton("◀")
        self.btn_toggle_left_drawer.setFixedSize(22, 24)
        self.btn_toggle_left_drawer.setToolTip("Afficher/masquer le panneau de retouches gauche")
        self.btn_toggle_left_drawer.clicked.connect(self._toggle_left_edit_drawer)
        layout.addWidget(self.btn_toggle_left_drawer)

        # FR: 2. thumbui/startoggle (☆), rotateleft (↶), rotateright (↷)
        # EN: 2. thumbui/startoggle (☆), rotateleft (↶), rotateright (↷)
        self.btn_star = QPushButton("☆ Favori")
        self.btn_star.setToolTip("Ajouter aux photos favorites (Ctrl+T)")
        self.btn_star.clicked.connect(self._toggle_star_current)
        layout.addWidget(self.btn_star)

        self.btn_rot_left = QPushButton("↶")
        self.btn_rot_left.setFixedSize(34, 24)
        self.btn_rot_left.setToolTip("Pivoter vers la gauche (Ctrl+Maj+R)")
        self.btn_rot_left.clicked.connect(self._on_rotate_left)
        layout.addWidget(self.btn_rot_left)

        self.btn_rot_right = QPushButton("↷")
        self.btn_rot_right.setFixedSize(34, 24)
        self.btn_rot_right.setToolTip("Pivoter vers la droite (Ctrl+R)")
        self.btn_rot_right.clicked.connect(self._on_rotate_right)
        layout.addWidget(self.btn_rot_right)

        layout.addSpacing(8)

        # FR: 3. editpanel/zoombuttcontainer : fit (286..323, 37x22) + 1to1 (323..360, 37x22) + zoomslider (399..526, 127x27)
        # EN: 3. editpanel/zoombuttcontainer: fit (286..323, 37x22) + 1to1 (323..360, 37x22) + zoomslider (399..526, 127x27)
        self.btn_fit = QPushButton("Ajuster")
        self.btn_fit.setToolTip("Ajuster la photo à la fenêtre (editpanel/fit)")
        self.btn_fit.clicked.connect(self.canvas.reset_zoom_to_fit)
        layout.addWidget(self.btn_fit)

        self.btn_zoom_1to1 = QPushButton("1:1")
        self.btn_zoom_1to1.setToolTip("Zoom 1:1 taille réelle 100% (editpanel/1to1)")
        self.btn_zoom_1to1.clicked.connect(lambda: self.canvas.set_zoom(1.0))
        layout.addWidget(self.btn_zoom_1to1)

        layout.addWidget(QLabel("🔍"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(125)
        self.zoom_slider.valueChanged.connect(self.canvas.set_zoom_from_slider)
        self.canvas.zoom_changed.connect(self._on_canvas_zoom_changed)
        layout.addWidget(self.zoom_slider)

        # FR: Bouton Affichage des balises de visages (Ref: 0x008AAD76)
        # EN: Face tags display toggle button (Ref: 0x008AAD76)
        self.btn_toggle_faces = QPushButton("Visages (On)")
        self.btn_toggle_faces.setCheckable(True)
        self.btn_toggle_faces.setChecked(True)
        self.btn_toggle_faces.toggled.connect(self._on_toggle_face_tags)
        layout.addWidget(self.btn_toggle_faces)

        # FR: Attributs conservés pour compatibilité des tests/appels existants
        # EN: Attributes kept for backward compatibility with existing tests/calls
        self.btn_prev = QPushButton("◀ Précédente", bar)
        self.btn_prev.hide()
        self.btn_prev.clicked.connect(self.navigate_previous)
        self.btn_next = QPushButton("Suivante ▶", bar)
        self.btn_next.hide()
        self.btn_next.clicked.connect(self.navigate_next)
        self.btn_slideshow = QPushButton("Diaporama", bar)
        self.btn_slideshow.hide()
        self.btn_slideshow.clicked.connect(self.slideshow_requested.emit)

        layout.addStretch(1)

        # FR: Séparateur vertical
        # EN: Vertical separator
        sep_drawer = QFrame()
        sep_drawer.setFrameShape(QFrame.Shape.VLine)
        sep_drawer.setStyleSheet("color: #404550;")
        layout.addWidget(sep_drawer)

        # FR: 4. thumbui/metadata_group (545..785) : 4 boutons d'icônes (sans texte) du panneau latéral droit
        # EN: 4. thumbui/metadata_group (545..785): 4 icon-only right side drawer toggle buttons
        # Ref: picasa3.exe @ 0x005D96D4..0x005D9E54, TOOLTIPS_FR.XML:858-869
        from PySide6.QtCore import QSize
        rm = PicasaResourceManager.get()

        self.btn_panel_people = QPushButton("")
        self.btn_panel_people.setIcon(rm.get_drawer_toggle_icon("people", 18))
        self.btn_panel_people.setIconSize(QSize(18, 18))
        self.btn_panel_people.setFixedSize(32, 26)
        self.btn_panel_people.setCheckable(True)
        self.btn_panel_people.setToolTip(rm.get_xml_string("thumbui/people_toggle.tooltip", "Afficher/masquer le panneau Personnes"))
        self.btn_panel_people.clicked.connect(lambda: self.toggle_drawer_panel("people"))
        layout.addWidget(self.btn_panel_people)

        self.btn_panel_places = QPushButton("")
        self.btn_panel_places.setIcon(rm.get_drawer_toggle_icon("places", 18))
        self.btn_panel_places.setIconSize(QSize(18, 18))
        self.btn_panel_places.setFixedSize(32, 26)
        self.btn_panel_places.setCheckable(True)
        self.btn_panel_places.setToolTip(rm.get_xml_string("thumbui/places_toggle.tooltip", "Afficher/Masquer le panneau Lieux"))
        self.btn_panel_places.clicked.connect(lambda: self.toggle_drawer_panel("places"))
        layout.addWidget(self.btn_panel_places)

        self.btn_panel_tags = QPushButton("")
        self.btn_panel_tags.setIcon(rm.get_drawer_toggle_icon("tags", 18))
        self.btn_panel_tags.setIconSize(QSize(18, 18))
        self.btn_panel_tags.setFixedSize(32, 26)
        self.btn_panel_tags.setCheckable(True)
        self.btn_panel_tags.setToolTip(rm.get_xml_string("thumbui/tags_toggle.tooltip", "Afficher/Masquer le panneau Tags"))
        self.btn_panel_tags.clicked.connect(lambda: self.toggle_drawer_panel("tags"))
        layout.addWidget(self.btn_panel_tags)

        self.btn_panel_props = QPushButton("")
        self.btn_panel_props.setIcon(rm.get_drawer_toggle_icon("properties", 18))
        self.btn_panel_props.setIconSize(QSize(18, 18))
        self.btn_panel_props.setFixedSize(32, 26)
        self.btn_panel_props.setCheckable(True)
        self.btn_panel_props.setToolTip(rm.get_xml_string("thumbui/properties_toggle.tooltip", "Afficher/Masquer le panneau Propriétés"))
        self.btn_panel_props.clicked.connect(lambda: self.toggle_drawer_panel("properties"))
        layout.addWidget(self.btn_panel_props)

        return bar

    def toggle_drawer_panel(self, panel_name: str) -> None:
        """
        FR: Bascule l'ouverture/fermeture du volet latéral droit pour le panneau demandé.
        EN: Toggles opening/closing of the right side drawer for the requested panel.

        Ref: picasa3.exe @ thumbui/people_toggle, places_toggle, tags_toggle, properties_toggle
        """
        self.right_drawer.toggle_panel(panel_name)
        self._update_drawer_buttons_state()

    def update_star_button(self, is_starred: bool) -> None:
        """
        FR: Met à jour le texte et le style du bouton favori selon l'état de l'étoile et le thème actif.
        EN: Updates the favorite button text and style according to the star state and active theme.

        Ref: picasa3.exe @ editpanel/star_icon
        """
        self._is_starred = is_starred
        if not hasattr(self, "btn_star"):
            return
        is_dark = getattr(self.style, "is_dark", True)
        if is_starred:
            self.btn_star.setText("★ Favori")
            star_bg = "#383218" if is_dark else "#FFF8E1"
            star_col = "#FFD700" if is_dark else "#D97706"
            star_hov = "#4D431F" if is_dark else "#FFECB3"
            self.btn_star.setStyleSheet(f"""
                QPushButton {{
                    background-color: {star_bg};
                    color: {star_col};
                    border: 1px solid #FFC107;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {star_hov};
                }}
            """)
            self.btn_star.setToolTip("Retirer des photos favorites (Ctrl+T)")
        else:
            self.btn_star.setText("☆ Favori")
            self.btn_star.setStyleSheet("")
            self.btn_star.setToolTip("Ajouter aux photos favorites (Ctrl+T)")

    def _toggle_star_current(self) -> None:
        """
        FR: Bascule l'étoile sur la photo actuellement ouverte dans One-Up (Ctrl+T)
        en synchronisant `.picasa.ini`, `imagedata_star.pmp` et `wordhash.dat` (`]star`).
        EN: Toggles the star status on the photo currently open in One-Up (Ctrl+T),
        synchronizing `.picasa.ini`, `imagedata_star.pmp`, and `wordhash.dat` (`]star`).

        Ref: picasa3.exe @ ID_PICTURE_STAR, star=yes, 0x00456A15
        """
        target_path = self.current_photo_path
        if not target_path or not os.path.exists(target_path):
            return
        state = {"starred": False}

        def _toggle(doc, fname: str) -> None:
            new_s = not doc.is_starred(fname)
            doc.set_starred(fname, new_s)
            state["starred"] = new_s

        self._update_ini(target_path, _toggle)
        self.update_star_button(state["starred"])
        self.star_toggled.emit(target_path, state["starred"])

    def _on_drawer_closed(self) -> None:
        """
        FR: Synchronise l'état des boutons de la barre inférieure lorsque le tiroir droit est fermé.
        EN: Synchronizes the bottom bar button states when the right drawer is closed.
        """
        self._update_drawer_buttons_state()

    def _on_drawer_panel_changed(self, panel_name: str) -> None:
        """
        FR: Synchronise l'état des boutons de la barre inférieure lorsque le panneau actif du tiroir change.
        EN: Synchronizes the bottom bar button states when the active drawer panel changes.
        """
        self._update_drawer_buttons_state()

    def _on_drawer_face_hovered(self, face_idx: int) -> None:
        """
        FR: Met en surbrillance sur le canevas le rectangle du visage survolé dans le panneau Personnes.
        EN: Highlights on the canvas the face rectangle hovered in the People panel.
        """
        self.canvas.hovered_face_idx = face_idx
        self.canvas.update()

    def _on_back_to_library_clicked(self) -> None:
        """
        FR: Annule tout sous-panneau ou outil modal actif avant de retourner à la photothèque.
        Reproduit `FUN_005f8d80 @ 0x005F8D80` / `FUN_005f92e0 @ 0x005F92E0` (`editpanel/albumview`).
        EN: Cancels any active modal tool or subpanel before returning to the library.
        Reproduces `FUN_005f8d80 @ 0x005F8D80` / `FUN_005f92e0 @ 0x005F92E0` (`editpanel/albumview`).

        Ref: picasa3.exe @ 0x005F8D80, 0x005F92E0, 0x0057BB50
        """
        self._flush_pending_thumb_db_sync()
        if getattr(self, "_is_tool_locked", False) or self.edit_panel.stack.currentIndex() != 0:
            if hasattr(self, "canvas") and self.canvas is not None:
                self.canvas.cancel_manual_face_add()
            self.edit_panel.cancel_active_subpanel()
            self._set_modal_tool_lock(False, 0, "")
        self.back_to_library_requested.emit()

    def _on_manual_face_add_start(self) -> None:
        """
        FR: Démarre l'ajout manuel d'un visage sur le canevas et verrouille les barres d'interface (`mode == 3`).
        EN: Starts manual face addition on the canvas and locks the UI bars (`mode == 3`).

        Ref: picasa3.exe @ 0x0057BB50 (mode == 3)
        """
        self.canvas.start_manual_face_add()
        self._set_modal_tool_lock(True, 3, "manual_face")

    def _set_modal_tool_lock(self, locked: bool, mode: int = 0, tool_id: str = "") -> None:
        """
        FR: Verrouille ou déverrouille la barre supérieure (`viewer_top_bar` / `editpanel/oneup_controls`),
        la barre de légende (`caption_bar` / `editpanel/caption`), la barre inférieure (`transport_bar` /
        `thumbui/basecontrolset`, `thumbui/buttonbarsets`), la colonne de droite (`right_drawer` /
        `rightdrawerpanel/*`) et les contrôles globaux du panneau gauche lorsqu'un outil modal
        (Recadrer, Redresser, Yeux rouges, Retoucher, Texte, Visage manuel) ou un filtre paramétré
        (`mode="effect"`) est ouvert, jusqu'à clic sur « Appliquer » ou « Annuler ».
        Reproduit fidèlement `FUN_0057bb50 @ 0x0057BB50` et `FUN_005f8520 @ 0x005F8520`.
        EN: Locks or unlocks the top bar (`viewer_top_bar` / `editpanel/oneup_controls`),
        caption bar (`caption_bar` / `editpanel/caption`), bottom bar (`transport_bar` /
        `thumbui/basecontrolset`, `thumbui/buttonbarsets`), right column (`right_drawer` /
        `rightdrawerpanel/*`), and left panel global controls when a modal tool (Crop, Straighten,
        Red-eye, Retouch, Text, Manual face) or parameterized filter (`mode="effect"`) is open,
        until the user clicks "Apply" or "Cancel".
        Faithfully reproduces `FUN_0057bb50 @ 0x0057BB50` and `FUN_005f8520 @ 0x005F8520`.

        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50), 0x005F8520 (FUN_005f8520), 0x005F8730 (<zoom forcefit="1"/>)
        """
        self._is_tool_locked = bool(locked)
        self._active_tool_mode = int(mode) if locked else 0
        en = not bool(locked)

        # FR: Synchroniser l'état des contrôles du panneau gauche si l'appel provient directement de PicasaOneUpView
        # EN: Sync left edit panel control state if called directly on PicasaOneUpView
        if hasattr(self, "edit_panel") and self.edit_panel is not None:
            if getattr(self.edit_panel, "is_tool_locked", None) != bool(locked):
                self.edit_panel.set_modal_tool_lock(bool(locked), mode, tool_id, emit_signal=False)

        # FR: 1. Barre du haut (`editpanel/oneup_controls` : `sbutton`, `filmcontainer`, `layout_2up_group`)
        #     Ref: 0x0057BBD3 ([edi + 0x274] = 0 -> navigation pellicule désactivée), 0x0057BCFA
        # EN: 1. Top bar (`editpanel/oneup_controls`: `sbutton`, `filmcontainer`, `layout_2up_group`)
        #     Ref: 0x0057BBD3 ([edi + 0x274] = 0 -> filmstrip navigation disabled), 0x0057BCFA
        if hasattr(self, "viewer_top_bar") and self.viewer_top_bar is not None:
            self.viewer_top_bar.setEnabled(en)
        for attr in (
            "btn_top_slideshow",
            "btn_top_prev",
            "btn_top_next",
            "filmstrip",
            "btn_mode_a",
            "btn_mode_ab",
            "btn_mode_aa",
            "btn_swap_2up_layout",
            "btn_swap_2up_focus",
        ):
            w = getattr(self, attr, None)
            if w is not None:
                w.setEnabled(en)

        # FR: 2. Barre de légende (`editpanel/caption`, `editpanel/captionbutton`) :
        #     masquée pendant un outil/filtre (`0x0057BDF2..0x0057BE47`) et réaffichée au déverrouillage (`0x0057C01C..0x0057C07D`)
        # EN: 2. Caption bar (`editpanel/caption`, `editpanel/captionbutton`):
        #     hidden during a tool/filter (`0x0057BDF2..0x0057BE47`) and restored on unlock (`0x0057C01C..0x0057C07D`)
        if hasattr(self, "caption_bar") and self.caption_bar is not None:
            self.caption_bar.setEnabled(en)
            if hasattr(self, "caption_edit") and self.caption_edit is not None:
                self.caption_edit.setEnabled(en)
            if locked:
                self.caption_bar.hide()
            else:
                is_vid = hasattr(self, "center_stack") and hasattr(self, "video_player") and (
                    self.center_stack.currentWidget() == self.video_player
                )
                if not is_vid:
                    self.caption_bar.show()

        # FR: 3. Barre du bas (`thumbui/basecontrolset` @ 0x0057BD12, `thumbui/buttonbarsets` @ 0x0057BCF6)
        # EN: 3. Bottom transport bar (`thumbui/basecontrolset` @ 0x0057BD12, `thumbui/buttonbarsets` @ 0x0057BCF6)
        if hasattr(self, "transport_bar") and self.transport_bar is not None:
            self.transport_bar.setEnabled(en)
        win = self.window()
        if win is not None and win is not self and hasattr(win, "photo_tray") and win.photo_tray is not None:
            win.photo_tray.setEnabled(en)
        for attr in (
            "zoom_slider",
            "btn_1to1",
            "btn_fit",
            "btn_star",
            "btn_rot_ccw",
            "btn_rot_cw",
            "btn_prev",
            "btn_play",
            "btn_next",
            "btn_toggle_faces",
            "btn_upload_bottom",
            "btn_people_album_bottom",
            "btn_make_collage_bottom",
            "btn_make_movie_bottom",
            "btn_panel_people",
            "btn_panel_places",
            "btn_panel_tags",
            "btn_panel_props",
        ):
            w = getattr(self, attr, None)
            if w is not None:
                w.setEnabled(en)

        # FR: 4. Colonne de droite (`rightdrawerpanel/peoplepanel`, `geopanel`, `tagpanel`, `propertiespanel`)
        #     Ref: 0x0057BD3E..0x0057BD7A
        # EN: 4. Right column (`rightdrawerpanel/peoplepanel`, `geopanel`, `tagpanel`, `propertiespanel`)
        #     Ref: 0x0057BD3E..0x0057BD7A
        if hasattr(self, "right_drawer") and self.right_drawer is not None:
            self.right_drawer.setEnabled(en)
            for p_attr in ("panel_people", "panel_places", "panel_tags", "panel_properties"):
                p_widget = getattr(self.right_drawer, p_attr, None)
                if p_widget is not None:
                    p_widget.setEnabled(en)

        # FR: 5. `<zoom forcefit="1"/>` (`[ebx + 0xd4]` @ 0x005F8730 -> `0x005D1BE0`) :
        #     Redresser (`tilt`) et les filtres à cible (`soft_focus`, `focal_bw`, `graduated_tint`)
        #     forcent le zoom en mode Ajuster à la fenêtre à l'ouverture de l'outil.
        # EN: 5. `<zoom forcefit="1"/>` (`[ebx + 0xd4]` @ 0x005F8730 -> `0x005D1BE0`):
        #     Straighten (`tilt`) and puck-based filters (`soft_focus`, `focal_bw`, `graduated_tint`)
        #     force zoom-to-fit when opening the tool.
        if locked and hasattr(self, "canvas") and self.canvas is not None:
            if mode == 6 or tool_id in ("straighten", "soft_focus", "focal_bw", "graduated_tint"):
                self.canvas.reset_zoom_to_fit()

    def _on_manual_face_defined(self, face_rect: FaceRect) -> None:
        """
        FR: Déclenché quand l'utilisateur termine de tracer un rectangle de visage.
        Ouvre le dialogue modal pour saisir le nom de la personne.
        EN: Triggered when the user finishes drawing a manual face rectangle.
        Opens the modal dialog to enter the person's name.

        Ref: picasa3.exe @ 0x008A1034 (peoplepanel/manual_add_editbox), 0x0057BB50
        """
        self._set_modal_tool_lock(False, 0, "")
        if not self.db:
            return

        target_path = None
        if self.db and 0 <= self.current_index < len(self.db.index):
            target_path = self.db.get_media_full_path(self.current_index)
        if not target_path and self.canvas.image_path:
            target_path = self.canvas.image_path

        if not target_path or not os.path.exists(target_path):
            return

        self.right_drawer.show_panel("people")
        self._update_drawer_buttons_state()

        # FR: Obtenir l'image PIL actuellement affichée pour une fidélité pixel-parfaite
        # EN: Get the currently displayed PIL image for pixel-perfect fidelity
        source_img = None
        if self._history and 0 <= self._history_idx < len(self._history):
            source_img = self._history[self._history_idx]
        if source_img is None:
            source_img = PicasaImageProcessor.load_transformed_image(target_path)

        existing_names = [p.name for p in self.db.face_manager.get_people()]
        dlg = PicasaNameFaceDialog(
            face_rect=face_rect,
            photo_path=target_path,
            existing_names=existing_names,
            is_new_face=True,
            parent=self.window(),
            source_image=source_img,
        )
        if dlg.exec():
            name = dlg.get_contact_name()
            if name:
                db_i = self.current_index if self.current_index >= 0 else None
                self.db.face_manager.add_face(
                    target_path, face_rect, name, db_idx=db_i, source_image=source_img
                )
                updated_faces = self.db.face_manager.get_faces_for_photo(self.current_index) if db_i is not None else [face_rect]
                self.canvas.set_face_rects(updated_faces)
                self.right_drawer.panel_people.set_photo_faces(
                    self.db, self.current_index, target_path, updated_faces, source_img=source_img
                )
                self.people_changed.emit()

    def _on_canvas_face_clicked(self, face_rect: FaceRect, idx: int) -> None:
        """
        FR: Déclenché par un clic direct sur une balise de visage sur l'image.
        Ouvre le tiroir latéral sur le volet des personnes et affiche le dialogue de modification.
        EN: Triggered by a direct click on a face tag on the image.
        Opens the right side drawer on the People panel and displays the face naming dialog.
        """
        self.right_drawer.show_panel("people")
        self._update_drawer_buttons_state()
        source_img = None
        if self._history and 0 <= self._history_idx < len(self._history):
            source_img = self._history[self._history_idx]
        self.right_drawer.panel_people._open_name_dialog(
            face_rect, is_new=not bool(face_rect.contact_name), source_image=source_img
        )

    def _update_drawer_buttons_state(self) -> None:
        """
        FR: Met à jour l'état coché des 4 boutons du tiroir latéral droit selon le panneau visible.
        EN: Updates the checked state of the 4 right side drawer buttons based on the visible panel.
        """
        is_open = self.right_drawer.isVisible() or (
            not getattr(self.right_drawer, "_explicitly_hidden", True) and self.right_drawer.is_expanded
        )
        curr = self.right_drawer.current_panel_name if is_open else ""
        self.btn_panel_people.setChecked(is_open and curr == "people")
        self.btn_panel_places.setChecked(is_open and curr == "places")
        self.btn_panel_tags.setChecked(is_open and curr == "tags")
        self.btn_panel_props.setChecked(is_open and curr == "properties")
        win = self.window()
        if win is not None and win is not self and hasattr(win, "photo_tray") and win.photo_tray is not None:
            if hasattr(win, "stack") and win.stack.currentWidget() == self:
                win.photo_tray.update_panel_buttons(is_open, curr)

    def _on_canvas_zoom_changed(self, zoom: float) -> None:
        """
        FR: Synchronise la position du curseur de zoom lorsque le facteur de zoom du canevas change.
        EN: Synchronizes the zoom slider position when the canvas zoom factor changes.
        """
        self.zoom_slider.blockSignals(True)
        fit_scale = self.canvas._get_fit_scale()
        if fit_scale > 0:
            min_pct = max(5, min(100, int(round(fit_scale * 100))))
            self.zoom_slider.setRange(min_pct, max(400, min_pct * 4))
        if not self.zoom_slider.isSliderDown():
            val = max(self.zoom_slider.minimum(), min(self.zoom_slider.maximum(), int(round(zoom * 100))))
            self.zoom_slider.setValue(val)
        self.zoom_slider.blockSignals(False)

    def _on_toggle_face_tags(self, checked: bool) -> None:
        """
        FR: Active ou désactive l'affichage des cadres de visages sur le canevas.
        EN: Enables or disables the display of face bounding boxes on the canvas.
        """
        self.btn_toggle_faces.setText("Visages (On)" if checked else "Visages (Off)")
        self.canvas.set_show_face_tags(checked)

    def _on_view_mode_changed(self, mode_id: int) -> None:
        """
        FR: Bascule entre les modes de comparaison :
        0: A (vue simple -> masque swap_2up_layout et swap_2up_focus)
        1: A | B (2 photos côte à côte -> affiche swap_2up_layout et swap_2up_focus)
        2: A | A (avant / après retouches -> affiche swap_2up_layout et swap_2up_focus)
        EN: Switches between comparison view modes:
        0: A (single view -> hides swap_2up_layout and swap_2up_focus)
        1: A | B (2 photos side by side -> shows swap_2up_layout and swap_2up_focus)
        2: A | A (before / after edits -> shows swap_2up_layout and swap_2up_focus)

        Ref: picasa3.exe @ TwoUpAB, TwoUpAA, FUN_0056A680 @ 0x0056A8DB..0x0056A8EA, FUN_0056A260 @ 0x0056A5DD..0x0056A5EC
        """
        if mode_id == 0:
            if hasattr(self, "btn_mode_a"):
                self.btn_mode_a.setChecked(True)
            self.canvas.set_view_mode("A")
            if hasattr(self, "btn_swap_2up_layout"):
                self.btn_swap_2up_layout.hide()
            if hasattr(self, "btn_swap_2up_focus"):
                self.btn_swap_2up_focus.hide()
            if hasattr(self, "filmstrip") and self.filmstrip is not None:
                if hasattr(self.filmstrip, "set_secondary_index"):
                    self.filmstrip.set_secondary_index(-1)
                self.filmstrip.set_current_index(self.current_index)
        elif mode_id == 1:
            if hasattr(self, "btn_mode_ab"):
                self.btn_mode_ab.setChecked(True)
            self.canvas.set_view_mode("A_B")
            if hasattr(self, "btn_swap_2up_layout"):
                self.btn_swap_2up_layout.show()
            if hasattr(self, "btn_swap_2up_focus"):
                self.btn_swap_2up_focus.show()
            self._load_secondary_photo()
            if hasattr(self, "filmstrip") and self.filmstrip is not None:
                if hasattr(self.filmstrip, "set_secondary_index"):
                    self.filmstrip.set_secondary_index(self.secondary_index)
                active_idx = self.secondary_index if (self.canvas.active_pane == "B" and self.secondary_index >= 0) else self.current_index
                self.filmstrip.set_current_index(active_idx)
        elif mode_id == 2:
            if hasattr(self, "btn_mode_aa"):
                self.btn_mode_aa.setChecked(True)
            self.canvas.set_view_mode("A_A")
            if hasattr(self, "btn_swap_2up_layout"):
                self.btn_swap_2up_layout.show()
            if hasattr(self, "btn_swap_2up_focus"):
                self.btn_swap_2up_focus.show()
            if hasattr(self, "filmstrip") and self.filmstrip is not None:
                if hasattr(self.filmstrip, "set_secondary_index"):
                    self.filmstrip.set_secondary_index(-1)
                self.filmstrip.set_current_index(self.current_index)
            if getattr(self, "_orig_backup_path", None) and not getattr(self, "_orig_backup_loaded", False):
                try:
                    from PIL import ImageOps
                    with Image.open(str(self._orig_backup_path)) as b_raw:
                        if getattr(b_raw, "format", "") == "JPEG":
                            try:
                                b_raw.draft("RGB", (3200, 3200))
                            except Exception:
                                pass
                        b_img = ImageOps.exif_transpose(b_raw)
                        if b_img.mode not in ("RGB", "RGBA"):
                            b_img = b_img.convert("RGB")
                        b_img.load()
                        uw, uh = b_img.size
                        umax = max(uw, uh)
                        if umax > 1600:
                            usc = 1600.0 / float(umax)
                            b_img = b_img.resize(
                                (max(1, int(round(uw * usc))), max(1, int(round(uh * usc)))),
                                Image.Resampling.BILINEAR,
                            )
                        self._raw_unedited_pil_img = b_img
                        self._original_pil_img = b_img
                        self._orig_backup_loaded = True
                        self._original_pixmap_dirty = True
                except Exception:
                    self._orig_backup_loaded = True
            if self._original_pil_img and (self._original_pixmap_dirty or self.canvas.original_pixmap is None):
                orig_pix = self._pil_to_pixmap(self._original_pil_img)
                self.canvas.set_original_pixmap(orig_pix)
                self._original_pixmap_dirty = False

        self._update_top_bar_info()

    def _on_swap_2up_layout_clicked(self) -> None:
        """
        FR: Bascule la division 2-Up entre l'affichage horizontal (gauche/droite) et vertical (haut/bas).
        EN: Toggles the 2-Up split between horizontal (left/right) and vertical (top/bottom) layout.
        Ref: picasa3.exe @ 0x00569650, 0x00569720 (editpanel/swap_2up_layout)
        """
        new_orient = self.canvas.toggle_split_orientation()
        rm = PicasaResourceManager.get()
        if new_orient == "vertical":
            self.btn_swap_2up_layout.setIcon(rm.get_2up_button_icon("swap_layout_horiz", 22))
        else:
            self.btn_swap_2up_layout.setIcon(rm.get_2up_button_icon("swap_layout_vert", 22))

    def _on_swap_2up_focus_clicked(self) -> None:
        """
        FR: Bascule la sélection active entre l'image A et l'image B dans la vue 2-Up.
        EN: Toggles active selection focus between Image A and Image B in 2-Up view.
        Ref: picasa3.exe @ 0x0056A160, 0x00569AF0 (editpanel/swap_2up_focus, editpanel/selection_label)
        """
        self.canvas.swap_active_pane()

    def _on_active_pane_changed(self, pane: str) -> None:
        """
        FR: Met à jour la pellicule supérieure (`0x005704D0`) et l'en-tête d'informations (`0x005D7B60`)
        lorsque le volet actif (A ou B) change en mode 2-Up.
        EN: Updates the top filmstrip (`0x005704D0`) and the info header (`0x005D7B60`)
        when the active pane (A or B) changes in 2-Up mode.
        Ref: picasa3.exe @ 0x0056A1FB..0x0056A235
        """
        self._update_top_bar_info()
        if self.canvas.view_mode == "A_B":
            target_idx = self.secondary_index if (pane == "B" and self.secondary_index >= 0) else self.current_index
            if hasattr(self, "filmstrip") and self.filmstrip is not None and target_idx >= 0:
                self.filmstrip.set_current_index(target_idx)
            if self.db is not None and 0 <= target_idx < len(self.db.index):
                p_path = self.db.get_media_full_path(target_idx) or ""
                self.current_photo_changed.emit(target_idx, p_path)

    def _on_neutral_color_picked(self, rgb: Tuple[int, int, int]) -> None:
        """
        FR: Enregistre le point neutre échantillonné (`neutral_rgb` `0x00RRGGBB`, `[edi + 0x40]` @ `0x008F8002`)
            et réapplique le pipeline non-cumulatif `finetune2` (`0x008F7EE0` / `0x008FAC40`).
        EN: Stores the sampled neutral point (`neutral_rgb` `0x00RRGGBB`, `[edi + 0x40]` @ `0x008F8002`)
            and reapplies the non-cumulative `finetune2` pipeline (`0x008F7EE0` / `0x008FAC40`).

        Ref: picasa3.exe @ 0x008F8002, 0x0090EDA0, 0x008FAC40
        """
        if not self._history or self._history_idx < 0:
            return
        r, g, b = int(rgb[0]) & 0xFF, int(rgb[1]) & 0xFF, int(rgb[2]) & 0xFF
        neutral_rgb = (r << 16) | (g << 8) | b
        if hasattr(self.edit_panel, "set_tuning_neutral_rgb"):
            self.edit_panel.set_tuning_neutral_rgb(neutral_rgb)
        if hasattr(self.edit_panel, "btn_neutral_color"):
            self.edit_panel.btn_neutral_color.setChecked(False)
        self._on_apply_effect("color_temp", {})

    @staticmethod
    def _resolve_db_photo_index(db: Optional[PicasaDatabase], idx: int) -> int:
        """
        FR: Résout un index de sous-enregistrement de visage (`type == 1001`) vers l'index de sa photo parente.
        EN: Resolves a face sub-record index (`type == 1001`) to its parent photo index.

        Ref: picasa3.exe @ thumbindex.db (type 1001, parent photo index)
        """
        if db is None or idx < 0:
            return idx
        if hasattr(db, "is_face_record") and db.is_face_record(idx):
            if hasattr(db, "get_face_parent_photo_idx"):
                p_idx = db.get_face_parent_photo_idx(idx)
                if p_idx >= 0:
                    return p_idx
        if hasattr(db, "index") and 0 <= idx < len(db.index) and getattr(db.index[idx], "type", 0) == 1001:
            p_idx = getattr(db.index[idx], "parent", -1)
            if 0 <= p_idx < len(db.index):
                return p_idx
        return idx

    def _read_current_ini_snapshot(self, photo_path: Optional[str] = None) -> Optional[str]:
        """
        FR: Capture le contenu texte actuel du fichier `.picasa.ini` du dossier de la photo.
        EN: Captures the current text content of the `.picasa.ini` file in the photo's directory.
        """
        target = photo_path or self.current_photo_path
        if not target:
            return None
        parent_dir = os.path.dirname(target)
        for ini_name in (".picasa.ini", "Picasa.ini"):
            ini_p = os.path.join(parent_dir, ini_name)
            if os.path.exists(ini_p):
                try:
                    return Path(ini_p).read_text(encoding="utf-8", errors="replace")
                except Exception:
                    return None
        return None

    def _sync_current_thumbnails_to_db(
        self,
        pil_img: Optional[Image.Image] = None,
        index_override: Optional[int] = None,
    ) -> None:
        """
        FR: Recalcule les miniatures et aperçus (`thumbs`, `thumbs2`, `bigthumbs`, `previews`)
        dans `PicasaDatabase` à partir de l'image active et invalide le cache de la pellicule (`filmstrip`).
        Reproduit fidèlement `FUN_00579360 @ 0x00579360` -> `FUN_00425210` / `FUN_00425F60` et `0x00579680`.
        EN: Recalculates thumbnails and previews (`thumbs`, `thumbs2`, `bigthumbs`, `previews`)
        in `PicasaDatabase` from the active image and invalidates the filmstrip thumbnail cache.
        Faithfully reproduces `FUN_00579360 @ 0x00579360` -> `FUN_00425210` / `FUN_00425F60` and `0x00579680`.
        Ref: picasa3.exe @ 0x00579360, 0x00425210, 0x00425F60, 0x00579680 (editpanel/filmstrip)
        """
        if index_override is None and self._thumb_db_sync_timer.isActive():
            self._thumb_db_sync_timer.stop()
            self._pending_thumb_db_sync = None
        target_idx = self.current_index if index_override is None else index_override
        img = pil_img
        if img is None and self._history and 0 <= self._history_idx < len(self._history):
            img = self._history[self._history_idx]
        if img is not None and self.db is not None and target_idx >= 0:
            if hasattr(self.db, "update_thumbnails_from_pil"):
                if hasattr(self.db, "schedule_save_thumbnails"):
                    self.db.update_thumbnails_from_pil(target_idx, img, persist_to_disk=False)
                    self.db.schedule_save_thumbnails(1500)
                else:
                    self.db.update_thumbnails_from_pil(target_idx, img, persist_to_disk=True)
        if hasattr(self, "filmstrip") and target_idx >= 0:
            if hasattr(self.filmstrip, "invalidate_thumbnail"):
                self.filmstrip.invalidate_thumbnail(target_idx)
            else:
                self.filmstrip._thumb_cache.pop(target_idx, None)
                self.filmstrip.update()

    def _schedule_thumb_db_sync(self, pil_img: Image.Image, target_path: str) -> None:
        """
        FR: Planifie la mise à jour différée (350 ms) des miniatures de la base de données et l'émission
        du signal `photo_edited` après le relâchement d'un curseur de réglage afin de ne pas bloquer l'interface.
        EN: Schedules a debounced (350 ms) update of database thumbnails and emission of the
        `photo_edited` signal after a tuning slider release so the UI thread stays responsive.
        Ref: picasa3.exe @ 0x00579360, 0x00760F40
        """
        self._pending_thumb_db_sync = (self.current_index, pil_img, target_path)
        self._thumb_db_sync_timer.start()

    def _flush_pending_thumb_db_sync(self) -> None:
        """
        FR: Exécute immédiatement toute synchronisation de miniatures en attente avant un changement de photo ou de vue.
        EN: Immediately flushes any pending thumbnail database synchronization before switching photos or views.
        Ref: picasa3.exe @ 0x00579360
        """
        if self._thumb_db_sync_timer.isActive():
            self._thumb_db_sync_timer.stop()
        pending = self._pending_thumb_db_sync
        self._pending_thumb_db_sync = None
        if pending is None:
            return
        sync_idx, sync_img, sync_path = pending
        self._sync_current_thumbnails_to_db(sync_img, index_override=sync_idx)
        if sync_path:
            self.photo_edited.emit(sync_path)

    def _restore_ini_snapshot(self, snapshot: Optional[str]) -> None:
        """
        FR: Restaure le fichier `.picasa.ini` du dossier de la photo à partir d'un instantané d'historique
            et synchronise la base de données ainsi que les vignettes.
        EN: Restores the photo directory's `.picasa.ini` file from a history snapshot
            and synchronizes the database and thumbnails.
        """
        target = self.current_photo_path
        if not target or not os.path.exists(target):
            return
        parent_dir = Path(target).parent
        ini_path = parent_dir / ".picasa.ini"
        try:
            if snapshot is None:
                if ini_path.exists():
                    if os.name == "nt":
                        try:
                            import ctypes
                            ctypes.windll.kernel32.SetFileAttributesW(str(ini_path), 0x80)
                        except Exception:
                            pass
                    ini_path.unlink()
            else:
                from picasa_py.ini.parser import PicasaIniParser
                doc = PicasaIniParser.parse_bytes(snapshot.encode("utf-8"))
                doc.write_file(str(ini_path))
            if self.db is not None:
                if hasattr(self.db, "_ini_cache") and isinstance(self.db._ini_cache, dict):
                    self.db._ini_cache.clear()
                if hasattr(self.db, "sync_photo_ini_to_db"):
                    self.db.sync_photo_ini_to_db(target)
            self._sync_active_transform_from_ini(target)
            self._sync_current_thumbnails_to_db()
            self.photo_edited.emit(target)
        except Exception:
            pass

    def _sync_active_transform_from_ini(self, target_path: Optional[str] = None) -> None:
        """
        FR: Relit les transformations géométriques actives (`crop`, `rotate`, `tilt`) depuis `.picasa.ini`,
            met à jour le canevas (`set_active_transform`) et rafraîchit les vignettes de visages du tiroir droit.
        EN: Re-reads active geometric transformations (`crop`, `rotate`, `tilt`) from `.picasa.ini`,
            updates the canvas (`set_active_transform`), and refreshes face avatars in the right drawer.
        Ref: picasa3.exe @ 0x0042BFA0, 0x00456A15, 0x0042A6F9
        """
        t_path = target_path or self.current_photo_path
        if not t_path and self.db and 0 <= self.current_index < len(self.db.index):
            t_path = self.db.get_media_full_path(self.current_index)
        self._active_crop_rect = None
        self._active_rotate = 0
        self._active_tilt = 0.0
        if t_path and os.path.exists(t_path):
            parent_dir = os.path.dirname(t_path)
            ini_path = os.path.join(parent_dir, ".picasa.ini")
            try:
                from picasa_py.ini.parser import PicasaIniParser
                from picasa_py.faces.facerect import decode_rect64_string
                doc = None
                if self.db and hasattr(self.db, "get_parsed_ini"):
                    doc = self.db.get_parsed_ini(ini_path)
                    if doc is None:
                        doc = self.db.get_parsed_ini(os.path.join(parent_dir, "Picasa.ini"))
                else:
                    if not os.path.exists(ini_path):
                        ini_path = os.path.join(parent_dir, "Picasa.ini")
                    if os.path.exists(ini_path):
                        doc = PicasaIniParser.parse_file(ini_path)
                if doc is not None:
                    base_name = os.path.basename(t_path)
                    crop_hex = doc.get_crop(base_name)
                    if crop_hex:
                        self._active_crop_rect = decode_rect64_string(crop_hex)
                    self._active_rotate = doc.get_rotate(base_name) or 0
                    self._active_tilt = doc.get_tilt(base_name) or 0.0
            except Exception:
                pass
        self.canvas.set_active_transform(self._active_crop_rect, self._active_tilt, self._active_rotate)
        curr_img = (
            self._history[self._history_idx]
            if (self._history and 0 <= self._history_idx < len(self._history))
            else None
        )
        if t_path:
            self.right_drawer.set_current_photo(self.db, self.current_index, t_path, source_img=curr_img)

    def _load_pil_image_at_index(
        self,
        index: int,
        direct_path: Optional[str] = None,
        max_size: int = 1600,
    ) -> Optional[Image.Image]:
        """
        FR: Charge une image PIL depuis le disque ou le cache d'aperçus (`previews_0.db`),
        en appliquant les transformations non-destructives définies dans `.picasa.ini`.
        Conformément à `picasa3.exe @ 0x0042525F` (`0x640 = 1600px`) et `0x00568E4A`,
        l'image est décodée en mode draft et redimensionnée à `max_size` (1600px par défaut)
        AVANT l'exécution de la chaîne de filtres `filters=`, ce qui garantit une navigation
        instantanée avec la pellicule ou les flèches même sur des photos 24 MP avec effets.
        EN: Loads a PIL image from disk or the preview cache (`previews_0.db`),
        applying non-destructive transformations defined in `.picasa.ini`.
        Following `picasa3.exe @ 0x0042525F` (`0x640 = 1600px`) and `0x00568E4A`,
        the image is draft-decoded and scaled to `max_size` (1600px by default)
        BEFORE running the `filters=` chain, ensuring instant navigation via filmstrip
        or arrow keys even on 24 MP photos with heavy effects.
        Ref: picasa3.exe @ 0x0042525F, 0x0042A800, 0x00568E4A
        """
        full_path = direct_path if (direct_path and os.path.exists(direct_path)) else (
            self.db.get_media_full_path(index) if (self.db and 0 <= index < len(self.db.index)) else None
        )
        if not full_path or not os.path.exists(full_path):
            if self.db is None or index < 0 or index >= len(self.db.index):
                return None

        pil_img: Optional[Image.Image] = None
        self._raw_unedited_pil_img = None

        if full_path and os.path.exists(full_path):
            try:
                # FR: Lecture préalable des transformations non-destructives .picasa.ini (crop, rotate, tilt)
                # pour adapter la cible de sous-échantillonnage JPEG et recadrer en pleine résolution
                # EN: Pre-read non-destructive .picasa.ini transforms (crop, rotate, tilt)
                # to adjust JPEG draft target and crop at full resolution
                self._active_crop_rect = None
                self._active_rotate = 0
                self._active_tilt = 0.0
                doc = None
                base_name = os.path.basename(full_path)
                crop_hex = None
                rot = 0
                tilt = 0.0
                parent_dir = os.path.dirname(full_path)
                ini_path = os.path.join(parent_dir, ".picasa.ini")
                try:
                    from picasa_py.ini.parser import PicasaIniParser
                    from picasa_py.faces.facerect import decode_rect64_string
                    if self.db and hasattr(self.db, "get_parsed_ini"):
                        doc = self.db.get_parsed_ini(ini_path)
                        if doc is None:
                            doc = self.db.get_parsed_ini(os.path.join(parent_dir, "Picasa.ini"))
                    else:
                        if not os.path.exists(ini_path):
                            ini_path = os.path.join(parent_dir, "Picasa.ini")
                        if os.path.exists(ini_path):
                            doc = PicasaIniParser.parse_file(ini_path)
                    if doc is not None:
                        crop_hex = doc.get_crop(base_name)
                        if crop_hex:
                            left_f, top_f, right_f, bottom_f = decode_rect64_string(crop_hex)
                            self._active_crop_rect = (left_f, top_f, right_f, bottom_f)
                        rot = doc.get_rotate(base_name) or 0
                        self._active_rotate = rot
                        tilt = doc.get_tilt(base_name) or 0.0
                        self._active_tilt = tilt
                except Exception:
                    pass

                with Image.open(full_path) as raw_img:
                    if max_size and max_size > 0 and getattr(raw_img, "format", "") == "JPEG":
                        try:
                            draft_target = max_size * 2
                            if self._active_crop_rect is not None:
                                lf, tf, rf, bf = self._active_crop_rect
                                min_frac = max(0.05, min(rf - lf, bf - tf))
                                draft_target = int(round((max_size * 2) / min_frac))
                            raw_img.draft("RGB", (draft_target, draft_target))
                        except Exception:
                            pass
                    # FR: Gérer les palettes avec transparence pour éviter UserWarning de PIL
                    # EN: Handle palettes with transparency to avoid PIL UserWarning
                    if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                        raw_img = raw_img.convert("RGBA")
                    from PIL import ImageOps
                    try:
                        pil_img = ImageOps.exif_transpose(raw_img)
                    except Exception:
                        pil_img = raw_img
                    if pil_img.mode not in ("RGB", "RGBA"):
                        pil_img = pil_img.convert("RGB")

                    # FR: Conserver l'image brute avant retouches .picasa.ini (ou depuis .picasaoriginals/) pour la comparaison A|A
                    # EN: Keep the unedited raw image before .picasa.ini edits (or from .picasaoriginals/) for A|A comparison
                    def _make_unedited_copy(src_img: Image.Image) -> Image.Image:
                        """
                        FR: Copie et redimensionne à `max_size` l'image brute de référence pour le mode A|A.
                        EN: Copies and scales the unedited reference image to `max_size` for A|A mode.
                        """
                        if max_size and max_size > 0:
                            uw, uh = src_img.size
                            umax = max(uw, uh)
                            if umax > max_size:
                                usc = max_size / float(umax)
                                return src_img.resize(
                                    (max(1, int(round(uw * usc))), max(1, int(round(uh * usc)))),
                                    Image.Resampling.BILINEAR,
                                )
                        return src_img.copy()

                    orig_backup = Path(full_path).parent / ".picasaoriginals" / os.path.basename(full_path)
                    self._orig_backup_path = str(orig_backup) if orig_backup.exists() else None
                    self._orig_backup_loaded = False
                    if self._orig_backup_path and self.canvas.view_mode in ("A_A", "A_B"):
                        try:
                            with Image.open(self._orig_backup_path) as b_raw:
                                if max_size and max_size > 0 and getattr(b_raw, "format", "") == "JPEG":
                                    try:
                                        b_raw.draft("RGB", (max_size * 2, max_size * 2))
                                    except Exception:
                                        pass
                                b_img = ImageOps.exif_transpose(b_raw)
                                if b_img.mode not in ("RGB", "RGBA"):
                                    b_img = b_img.convert("RGB")
                                b_img.load()
                                self._raw_unedited_pil_img = _make_unedited_copy(b_img)
                                self._orig_backup_loaded = True
                        except Exception:
                            self._raw_unedited_pil_img = _make_unedited_copy(pil_img)
                    else:
                        self._raw_unedited_pil_img = _make_unedited_copy(pil_img)

                    # FR: Application des transformations géométriques .picasa.ini sur l'image pleine résolution (crop -> rotate -> tilt)
                    # EN: Apply .picasa.ini geometric transforms on full-resolution image (crop -> rotate -> tilt)
                    if self._active_crop_rect is not None:
                        left_f, top_f, right_f, bottom_f = self._active_crop_rect
                        w, h = pil_img.size
                        crop_box = (
                            int(round(left_f * w)),
                            int(round(top_f * h)),
                            int(round(right_f * w)),
                            int(round(bottom_f * h)),
                        )
                        if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                            pil_img = pil_img.crop(crop_box)

                    if rot == 1:
                        pil_img = pil_img.rotate(270, expand=True)
                    elif rot == 2:
                        pil_img = pil_img.rotate(180, expand=True)
                    elif rot == 3:
                        pil_img = pil_img.rotate(90, expand=True)

                    # Ref: filter_tilt (0x008814AC)
                    if tilt and abs(tilt) >= 0.01:
                        pil_img = PicasaImageProcessor.straighten(pil_img, tilt)

                    # FR: Redimensionner à max_size (1600px) APRÈS recadrage/rotation et AVANT les filtres (Ref: 0x0042525F, 0x00568E4A)
                    # EN: Resize to max_size (1600px) AFTER crop/rotate and BEFORE running filters (Ref: 0x0042525F, 0x00568E4A)
                    if max_size and max_size > 0:
                        w0, h0 = pil_img.size
                        max_d0 = max(w0, h0)
                        if max_d0 > max_size:
                            sc0 = max_size / float(max_d0)
                            pil_img = pil_img.resize(
                                (max(1, int(round(w0 * sc0))), max(1, int(round(h0 * sc0)))),
                                Image.Resampling.BILINEAR,
                            )

                    if doc is not None:
                        try:
                            # Ref: filterdesc.xml, 0x008814AC, 0x00760F40
                            sec = doc.get_section(base_name)
                            if sec:
                                filters_str = sec.get("filters", "")
                                if filters_str:
                                    pil_img = PicasaImageProcessor.apply_filter_chain(pil_img, filters_str, skip_geom=True)

                            # Ref: editpanel/edittextpanel (0x00658900)
                            txt_val = doc.get_raw_text(base_name) if hasattr(doc, "get_raw_text") else doc.get_text(base_name)
                            if txt_val:
                                pil_img = PicasaImageProcessor.apply_text_token(pil_img, txt_val)
                        except Exception:
                            pass

                    # FR: Forcer le décodage effectif des données en RAM avant de fermer le descripteur de fichier
                    # EN: Force actual decoding of image data into RAM before closing the file descriptor
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
        FR: Convertit une image PIL en QPixmap de façon directe et ultra-rapide en mémoire.
        Évite le goulot d'étranglement de ré-encodage JPEG et la limite d'allocation Qt.
        EN: Directly and rapidly converts a PIL image into a QPixmap in memory.
        Avoids the JPEG re-encoding bottleneck and Qt allocation limits.
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
        db: Optional[PicasaDatabase],
        index: int,
        available_indices: List[int],
        direct_path: Optional[str] = None
    ) -> None:
        """
        FR: Ouvre un média (photo ou vidéo) dans la vue One-Up, initialise l'historique d'édition,
        charge les visages, les métadonnées `.picasa.ini`, la pellicule et le tiroir latéral droit.
        EN: Opens a media item (photo or video) in One-Up View, initializes edit history,
        loads faces, `.picasa.ini` metadata, the filmstrip, and the right side drawer.
        """
        self._flush_pending_thumb_db_sync()
        if db is not None:
            if index >= 0:
                index = self._resolve_db_photo_index(db, index)
            elif direct_path:
                if hasattr(db, "find_media_index_by_path"):
                    found_idx = db.find_media_index_by_path(direct_path)
                    if found_idx is not None and found_idx >= 0:
                        index = found_idx
                elif hasattr(db, "index"):
                    norm_target = os.path.normcase(os.path.abspath(direct_path))
                    for k in range(len(db.index)):
                        if getattr(db.index[k], "type", 0) in (2, 0x20):
                            mp = db.get_media_full_path(k)
                            if mp and os.path.normcase(os.path.abspath(mp)) == norm_target:
                                index = k
                                break
            if available_indices:
                dedup_avail: List[int] = []
                seen_avail = set()
                for raw_i in available_indices:
                    res_i = self._resolve_db_photo_index(db, raw_i)
                    if res_i >= 0 and res_i not in seen_avail:
                        seen_avail.add(res_i)
                        dedup_avail.append(res_i)
                if index >= 0 and index not in seen_avail:
                    dedup_avail.append(index)
                if dedup_avail:
                    available_indices = dedup_avail
            elif index >= 0:
                available_indices = [index]

        self.db = db
        self.current_index = index
        self.available_indices = available_indices
        self._history.clear()
        self._history_ini_snapshots.clear()
        self._history_idx = -1
        if getattr(self, "_is_tool_locked", False):
            self._set_modal_tool_lock(False, 0, "")

        full_path = direct_path if (direct_path and os.path.exists(direct_path)) else (
            self.db.get_media_full_path(index) if (self.db and 0 <= index < len(self.db.index)) else None
        )
        if not full_path and (self.db is None or index < 0 or index >= len(self.db.index)):
            return

        faces = []
        if db is not None and getattr(db, "face_manager", None):
            faces = db.face_manager.get_faces_for_photo(index, photo_path=full_path or direct_path)

        self._current_photo_path = full_path

        # FR: Vérifier s'il s'agit d'un fichier vidéo (Ref: 0x20, DirEntry.IsMovie)
        # EN: Check whether the file is a video (Ref: 0x20, DirEntry.IsMovie)
        is_video = False
        if full_path:
            ext = Path(full_path).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                is_video = True
        elif db and 0 <= index < len(db.index):
            if db.index[index].type == 0x20 or Path(db.index[index].path).suffix.lower() in VIDEO_EXTENSIONS:
                is_video = True

        if is_video and full_path:
            self.canvas.set_face_rects([])
            self.video_player.load_video(full_path)
            self.center_stack.setCurrentWidget(self.video_player)
            self.transport_bar.hide()
            self.btn_mode_a.setEnabled(False)
            self.btn_mode_ab.setEnabled(False)
            self.btn_mode_aa.setEnabled(False)
            self.edit_panel.set_video_mode(True)

            filename = os.path.basename(full_path)
            self.canvas.main_title = filename
            self._current_photo_path = full_path
            self.canvas.image_path = full_path

            self.right_drawer.set_current_photo(db, index, full_path, source_img=None)
            if db is not None and 0 <= index < len(db.index):
                self.filmstrip.set_items(db, available_indices, index)

            total = len(self.available_indices)
            curr_pos = -1
            try:
                curr_pos = self.available_indices.index(self.current_index)
            except ValueError:
                pass
            pos_str = f"Vidéo {curr_pos + 1} sur {total}" if curr_pos >= 0 else ""
            self.lbl_top_info.setText(f"🎬 {pos_str}  •  {filename}")
            self.current_photo_changed.emit(self.current_index, full_path or "")
            return

        # FR: Photo normale
        # EN: Standard photo
        self.video_player.stop()
        self.center_stack.setCurrentWidget(self.canvas)
        if not self._use_external_bottom_bar:
            self.transport_bar.show()
        self.btn_mode_a.setEnabled(True)
        self.btn_mode_ab.setEnabled(True)
        self.btn_mode_aa.setEnabled(True)
        self.edit_panel.set_video_mode(False)

        pil_img = self._load_pil_image_at_index(index, direct_path=direct_path)
        if pil_img:
            self._original_pil_img = getattr(self, "_raw_unedited_pil_img", None) or pil_img
            self._tuning_base_img = pil_img
            self._tuning_history_slot = -1
            self._effect_preview_base_img = None
            self._history = [pil_img]
            self._history_ini_snapshots = [self._read_current_ini_snapshot(full_path)]
            self._history_idx = 0
            self.edit_panel.reset_tuning_controls_silently()
            self._display_current_history(preserve_view=False)

            self.edit_panel.set_photo_metadata(full_path or "")

        # FR: Transmettre les transformations actives et les visages au canevas
        # EN: Pass active transformations and face rectangles to the canvas
        self.canvas.set_active_transform(self._active_crop_rect, self._active_tilt, self._active_rotate)
        self.canvas.set_face_rects(faces)

        filename = os.path.basename(full_path) if full_path else (
            os.path.basename(db.index[index].path) if (db and 0 <= index < len(db.index)) else ""
        )
        self.canvas.main_title = filename

        # FR: Si en mode A|B, charger automatiquement la photo secondaire
        # EN: If in A|B mode, automatically load the secondary photo
        if self.canvas.view_mode == "A_B":
            self._load_secondary_photo()

        if self.canvas.view_mode in ("A_B", "A_A"):
            if hasattr(self, "btn_swap_2up_layout"):
                self.btn_swap_2up_layout.show()
            if hasattr(self, "btn_swap_2up_focus"):
                self.btn_swap_2up_focus.show()

        # FR: Mettre à jour le volet latéral droit (Personnes, Lieux, Tags, Propriétés)
        # EN: Update the right side drawer (People, Places, Tags, Properties)
        self._current_photo_path = full_path
        self.canvas.image_path = full_path
        self.right_drawer.set_current_photo(db, index, full_path or "", source_img=pil_img)
        if db is not None and 0 <= index < len(db.index):
            self.filmstrip.set_items(db, available_indices, index)
            if self.canvas.view_mode == "A_B" and hasattr(self.filmstrip, "set_secondary_index"):
                self.filmstrip.set_secondary_index(self.secondary_index)

        # FR: Lire le statut favori (star=yes) et la légende (caption=) depuis .picasa.ini / DB
        # EN: Read favorite status (star=yes) and caption (caption=) from .picasa.ini / DB
        is_starred = False
        caption_text = ""
        if full_path:
            parent_dir = os.path.dirname(full_path)
            for ini_name in (".picasa.ini", "Picasa.ini"):
                ini_p = os.path.join(parent_dir, ini_name)
                if os.path.exists(ini_p):
                    try:
                        from picasa_py.ini.parser import PicasaIniParser
                        doc = (
                            self.db.get_parsed_ini(ini_p)
                            if (self.db and hasattr(self.db, "get_parsed_ini"))
                            else PicasaIniParser.parse_file(ini_p)
                        )
                        if doc is None:
                            doc = PicasaIniParser.parse_file(ini_p)
                        fname = os.path.basename(full_path)
                        is_starred = doc.is_starred(fname)
                        sec = doc.get_section(fname)
                        if sec:
                            caption_text = sec.get("caption") or ""
                        break
                    except Exception:
                        pass
        if not caption_text and db is not None and 0 <= index < len(db.index):
            try:
                cap_tbl = db.tables.get("imagedata_caption")
                if cap_tbl and index < len(cap_tbl.values) and cap_tbl.values[index]:
                    caption_text = str(cap_tbl.values[index])
            except Exception:
                pass
        self.update_star_button(is_starred)
        if hasattr(self, "caption_edit"):
            self.caption_edit.blockSignals(True)
            self.caption_edit.setText(caption_text)
            self.caption_edit.blockSignals(False)

        self._update_top_bar_info()
        self.current_photo_changed.emit(self.current_index, full_path or "")

    def _on_canvas_context_menu(self, global_pos: QPoint) -> None:
        """
        FR: Affiche le menu contextuel de la photo en mode One-Up / Two-Up.
        EN: Displays the photo context menu in One-Up / Two-Up mode.

        Ref: picasa3.exe @ TrackPopupMenu (0x005E7CD7), lb_rightclick (0x005D41F4)
        """
        photo_path = getattr(self, "_current_photo_path", None)
        if not photo_path and self.db and 0 <= self.current_index < len(self.db.index):
            photo_path = self.db.get_media_full_path(self.current_index)
        if not photo_path and self.canvas.image_path:
            photo_path = self.canvas.image_path

        if photo_path:
            from picasa_py.ui.context_menu import PicasaContextMenuBuilder
            PicasaContextMenuBuilder.show_photo_context_menu(
                parent=self,
                global_pos=global_pos,
                photo_paths=[photo_path],
                db=self.db,
                is_in_album=False,
                main_win=self.window(),
            )

    def _on_filmstrip_photo_clicked(self, photo_idx: int) -> None:
        """
        FR: Gère le clic direct sur une miniature de la pellicule de navigation supérieure.
        Ignoré lorsqu'un outil ou filtre modal verrouille l'interface (`[edi + 0x274] == 0` dans `FUN_0057bb50`).
        EN: Handles a direct click on a thumbnail in the top navigation filmstrip.
        Ignored when a modal tool or filter locks the UI (`[edi + 0x274] == 0` in `FUN_0057bb50`).

        Ref: picasa3.exe @ editpanel/filmstrip, filmstripdoubleclick, 0x0057BBD3 (FUN_0057bb50)
        """
        if getattr(self, "_is_tool_locked", False):
            return
        if self.canvas.view_mode == "A_B" and self.canvas.active_pane == "B":
            self.secondary_index = photo_idx
            self._load_secondary_photo()
            if self.db is not None and 0 <= photo_idx < len(self.db.index):
                sec_path = self.db.get_media_full_path(photo_idx) or ""
                self.current_photo_changed.emit(photo_idx, sec_path)
        else:
            self.open_photo(self.db, photo_idx, self.available_indices)

    def _load_secondary_photo(self) -> None:
        """
        FR: Charge la photo B pour le mode de comparaison A | B.
        EN: Loads photo B for the A | B comparison mode.
        """
        if not self.available_indices or self.db is None:
            return

        # FR: Par défaut, sélectionner la photo suivante dans la liste
        # EN: By default, select the next photo in the list
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

        if hasattr(self, "filmstrip") and self.filmstrip is not None:
            if hasattr(self.filmstrip, "set_secondary_index"):
                self.filmstrip.set_secondary_index(self.secondary_index)
            if self.canvas.view_mode == "A_B" and self.canvas.active_pane == "B" and self.secondary_index >= 0:
                self.filmstrip.set_current_index(self.secondary_index)

        self._update_top_bar_info()

    def _update_top_bar_info(self) -> None:
        """
        FR: Met à jour l'intitulé informatif de la photo dans la barre supérieure.
        EN: Updates the informational photo title label in the top bar.
        """
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

    def _display_pil_on_canvas(
        self,
        img: Image.Image,
        is_live_preview: bool = False,
        preserve_view: bool = False,
    ) -> None:
        """
        FR: Affiche une image PIL sur le canevas et met à jour l'histogramme sans altérer l'historique.
        EN: Displays a PIL image on the canvas and updates the histogram without altering history.
        Ref: picasa3.exe @ 0x00760F40
        """
        pix = self._pil_to_pixmap(img)
        self.canvas.set_pixmap_direct(pix, preserve_view=(is_live_preview or preserve_view))
        if is_live_preview:
            self.edit_panel.histogram_widget.set_image(img)
        else:
            self.edit_panel.set_image(img)
            if self.right_drawer.isVisible() and hasattr(self.right_drawer.panel_properties, "set_image"):
                self.right_drawer.panel_properties.set_image(img)

    def _display_current_history(self, preserve_view: bool = True) -> None:
        """
        FR: Affiche l'image correspondant à l'indice courant de l'historique d'édition.
        EN: Displays the image corresponding to the current index in the edit history.
        """
        if self._history_idx < 0 or self._history_idx >= len(self._history):
            return

        img = self._history[self._history_idx]
        self._display_pil_on_canvas(img, preserve_view=preserve_view)

        if self._original_pil_img:
            if self.canvas.view_mode == "A_A":
                orig_pix = self._pil_to_pixmap(self._original_pil_img)
                self.canvas.set_original_pixmap(orig_pix)
                self._original_pixmap_dirty = False
            else:
                self._original_pixmap_dirty = True

    def _get_fast_preview_base(self, base_img: Image.Image) -> Image.Image:
        """
        FR: Retourne une copie réduite (max 480px) mise en cache pour le glissement fluide des curseurs à 60 FPS.
        EN: Returns a cached downscaled copy (max 480px) for smooth 60 FPS slider dragging.
        Ref: picasa3.exe @ 0x00760F40
        """
        if self._fast_preview_base_source is base_img and self._fast_preview_base_img is not None:
            return self._fast_preview_base_img
        self._fast_preview_base_source = base_img
        w, h = base_img.size
        max_dim = max(w, h)
        target_max = 480
        if max_dim > target_max:
            sc = float(target_max) / float(max_dim)
            self._fast_preview_base_img = base_img.resize(
                (max(1, int(round(w * sc))), max(1, int(round(h * sc)))),
                Image.Resampling.BILINEAR,
            )
        else:
            self._fast_preview_base_img = base_img
        return self._fast_preview_base_img

    def _flush_full_res_preview(self) -> None:
        """
        FR: Recalcule l'aperçu pleine résolution (1600px) 75 ms après l'arrêt du glissement d'un curseur.
        EN: Recomputes the full-resolution preview (1600px) 75 ms after slider dragging pauses.
        """
        pending = self._pending_full_res_preview
        self._pending_full_res_preview = None
        if pending is None or self._history_idx < 0 or not self._history:
            return
        kind, arg1, arg2 = pending
        if kind == "tuning" and self._tuning_base_img is not None:
            tp = arg1
            preview_img = PicasaImageProcessor.finetune(
                self._tuning_base_img,
                fill=float(tp.get("fill", 0.0)),
                highlights=float(tp.get("highlights", 0.0)),
                shadows=float(tp.get("shadows", 0.0)),
                colortemp=float(tp.get("colortemp", 0.0)),
                neutral_rgb=int(tp.get("neutral_rgb", 0)),
            )
            self._display_pil_on_canvas(preview_img, is_live_preview=True, preserve_view=True)
        elif kind == "effect" and self._effect_preview_base_img is not None:
            preview_img = PicasaImageProcessor.execute_effect(self._effect_preview_base_img, arg1, arg2)
            if preview_img is not None:
                self._display_pil_on_canvas(preview_img, is_live_preview=True, preserve_view=True)

    def _push_history(self, img: Image.Image, preserve_view: bool = True) -> None:
        """
        FR: Empile un nouvel état d'image dans l'historique d'édition et rafraîchit le canevas.
        EN: Pushes a new image state onto the edit history stack and refreshes the canvas.
        """
        self._history = self._history[: self._history_idx + 1]
        self._history_ini_snapshots = self._history_ini_snapshots[: self._history_idx + 1]
        self._history.append(img.copy())
        self._history_ini_snapshots.append(self._read_current_ini_snapshot())
        self._history_idx = len(self._history) - 1
        self._display_current_history(preserve_view=preserve_view)

    def _on_tuning_preview_changed(self, tuning_params: dict) -> None:
        """
        FR: Aperçu en temps réel non-cumulatif des curseurs de Lumière d'appoint / Réglages (`finetune2`).
        Calcule toujours à partir de `self._tuning_base_img` pour que déplacer un curseur de gauche
        à droite ne superpose jamais l'effet sur lui-même, et que revenir à 0 redonne l'image exacte.
        EN: Non-cumulative real-time preview for Fill Light / Tuning sliders (`finetune2`).
        Always computes from `self._tuning_base_img` so moving a slider back and forth never stacks
        the effect onto itself, and returning to 0 restores the exact base image.

        Ref: picasa3.exe @ filterdesc.xml (finetune2, mode="soft", flightslider1), 0x008F7EE0
        """
        if self._history_idx < 0 or not self._history:
            return
        if self._tuning_base_img is None:
            self._tuning_base_img = self._history[self._history_idx].copy()

        src_img = self._get_fast_preview_base(self._tuning_base_img)
        preview_img = PicasaImageProcessor.finetune(
            src_img,
            fill=float(tuning_params.get("fill", 0.0)),
            highlights=float(tuning_params.get("highlights", 0.0)),
            shadows=float(tuning_params.get("shadows", 0.0)),
            colortemp=float(tuning_params.get("colortemp", 0.0)),
            neutral_rgb=int(tuning_params.get("neutral_rgb", 0)),
        )
        self._display_pil_on_canvas(preview_img, is_live_preview=True, preserve_view=True)
        if src_img is not self._tuning_base_img:
            self._pending_full_res_preview = ("tuning", dict(tuning_params), None)
            self._full_res_preview_timer.start()
        else:
            self._full_res_preview_timer.stop()
            self._pending_full_res_preview = None

    def _on_tuning_applied(self, tuning_params: dict) -> None:
        """
        FR: Valide explicitement les réglages d'éclairage (`Appliquer les réglages`) comme nouvelle base
        et remet les curseurs à 0 pour d'éventuelles retouches ultérieures.
        EN: Explicitly commits lighting adjustments ("Apply adjustments") as the new base image
        and resets sliders to 0 for subsequent edits.

        Ref: picasa3.exe @ 0x008FAC40, 0x008F7EE0, filterdesc.xml (finetune2)
        """
        if self._history_idx < 0 or not self._history:
            return
        base_img = self._tuning_base_img if self._tuning_base_img is not None else self._history[self._history_idx]
        fill_v = float(tuning_params.get("fill", 0.0))
        hl_v = float(tuning_params.get("highlights", 0.0))
        sh_v = float(tuning_params.get("shadows", 0.0))
        ct_v = float(tuning_params.get("colortemp", 0.0))
        neutral_rgb = int(tuning_params.get("neutral_rgb", 0)) & 0x00FFFFFF
        if abs(fill_v) < 1e-4 and abs(hl_v) < 1e-4 and abs(sh_v) < 1e-4 and abs(ct_v) < 1e-4 and neutral_rgb == 0:
            return

        new_img = PicasaImageProcessor.finetune(base_img, fill_v, hl_v, sh_v, ct_v, neutral_rgb=neutral_rgb)
        if self._tuning_history_slot == self._history_idx and self._tuning_history_slot > 0:
            self._history[self._history_idx] = new_img.copy()
            self._display_current_history(preserve_view=True)
        else:
            self._push_history(new_img, preserve_view=True)
        self._tuning_base_img = new_img.copy()
        self._tuning_history_slot = -1
        self.edit_panel.reset_tuning_controls_silently()

        target_path = self.current_photo_path
        if target_path and os.path.exists(target_path):
            # Ref: picasa3.exe @ 0x008FAC40 : finetune2=1,<fill:%f>,<highlights:%f>,<shadows:%f>,<neutral_rgb:%08x>,<colortemp:%f>
            token = f"finetune2=1,{fill_v:.6f},{hl_v:.6f},{sh_v:.6f},{neutral_rgb:08x},{ct_v:.6f}"
            self._update_ini_tuning_token(target_path, token)
            self._sync_current_thumbnails_to_db(new_img)
            self.photo_edited.emit(target_path)

    def _update_ini_tuning_token(self, target_path: str, token: Optional[str]) -> None:
        """
        FR: Met à jour les jetons de réglage d'éclairage dans `.picasa.ini` sans empiler de doublons
        lorsque l'utilisateur ajuste un curseur à plusieurs reprises.
        EN: Updates lighting adjustment tokens in `.picasa.ini` without stacking duplicates
        when the user adjusts a slider multiple times.
        """
        tuning_prefixes = ("fill=", "backlight=", "highlights=", "shadows=", "colortemp=", "finetune=", "finetune2=")

        def _replace_tuning(doc, fname: str) -> None:
            """
            FR: Remplace ou supprime les jetons de réglage d'éclairage dans la clé `filters` de `.picasa.ini`.
            EN: Replaces or removes lighting adjustment tokens in the `filters` key of `.picasa.ini`.
            """
            sec = doc.get_or_create_section(fname)
            existing = sec.get("filters", "") or ""
            kept = [
                t.strip()
                for t in existing.split(";")
                if t.strip() and not t.strip().lower().startswith(tuning_prefixes)
            ]
            if token:
                kept.append(token)
            if kept:
                sec.set("filters", ";".join(kept) + ";")
            else:
                sec.remove("filters")

        self._update_ini(target_path, _replace_tuning)

    def _on_effect_preview_requested(self, effect_name: str, params: dict) -> None:
        """
        FR: Affiche en temps réel l'aperçu d'un filtre paramétrable (`mode="effect"`) sur l'image de base
        sans modifier l'historique ni écrire dans `.picasa.ini` tant que l'utilisateur n'a pas validé.
        EN: Displays a live preview of a parameterized filter (`mode="effect"`) on the base image
        without mutating history or writing to `.picasa.ini` until the user clicks Apply.

        Ref: picasa3.exe @ filterdesc.xml (mode="effect"), 0x00760F40
        """
        if self._history_idx < 0 or not self._history:
            return
        if self._effect_preview_base_img is None:
            self._effect_preview_base_img = self._history[self._history_idx].copy()

        src_img = self._get_fast_preview_base(self._effect_preview_base_img)
        preview_img = PicasaImageProcessor.execute_effect(src_img, effect_name, params)
        if preview_img is not None:
            self._display_pil_on_canvas(preview_img, is_live_preview=True, preserve_view=True)
            if src_img is not self._effect_preview_base_img:
                self._pending_full_res_preview = ("effect", effect_name, dict(params))
                self._full_res_preview_timer.start()
            else:
                self._full_res_preview_timer.stop()
                self._pending_full_res_preview = None

    def _on_effect_applied(self, effect_name: str, params: dict) -> None:
        """
        FR: Valide le filtre paramétrable lorsque l'utilisateur clique sur « Appliquer » (`editpanel/ok`).
        EN: Commits the parameterized filter when the user clicks "Apply" (`editpanel/ok`).

        Ref: TOOLTIPS_FR.XML @ editpanel/ok ("Appliquer")
        """
        self._full_res_preview_timer.stop()
        self._pending_full_res_preview = None
        if self._effect_preview_base_img is not None and 0 <= self._history_idx < len(self._history):
            self._history[self._history_idx] = self._effect_preview_base_img.copy()
        self._effect_preview_base_img = None
        self._on_apply_effect(effect_name, params)

    def _on_effect_cancelled(self) -> None:
        """
        FR: Annule l'aperçu du filtre en cours et restaure l'image de base (`editpanel/cancel`).
        EN: Cancels the current filter preview and restores the base image (`editpanel/cancel`).

        Ref: TOOLTIPS_FR.XML @ editpanel/cancel ("Annuler")
        """
        self._full_res_preview_timer.stop()
        self._pending_full_res_preview = None
        if self._effect_preview_base_img is not None:
            self._display_pil_on_canvas(self._effect_preview_base_img, preserve_view=True)
            self._effect_preview_base_img = None
        else:
            self._display_current_history(preserve_view=True)

    def _on_apply_effect(self, effect_name: str, params: dict) -> None:
        """
        FR: Applique un effet ou un réglage sur l'image active, met à jour l'historique et persiste le filtre dans `.picasa.ini`.
        EN: Applies an effect or adjustment to the active image, updates history, and persists the filter in `.picasa.ini`.
        """
        if self._history_idx < 0 or not self._history:
            return
        self._full_res_preview_timer.stop()
        self._pending_full_res_preview = None

        # FR: --- Cas 1 : Curseurs d'éclairage et baguettes magiques (Tab 1 Lumière d'appoint / Tab 2 Réglages) ---
        # Calculés de façon NON-CUMULATIVE depuis `self._tuning_base_img` !
        # EN: --- Case 1: Lighting sliders and magic wands (Tab 1 Fill Light / Tab 2 Tuning) ---
        # Computed NON-CUMULATIVELY from `self._tuning_base_img`!
        if effect_name in ("fill_light", "highlights", "shadows", "color_temp", "autotune_lighting", "autotune_color"):
            if self._tuning_base_img is None:
                self._tuning_base_img = self._history[self._history_idx].copy()

            t_params = self.edit_panel.get_tuning_params()
            if effect_name == "autotune_lighting":
                hl_auto, sh_auto = PicasaImageProcessor.compute_autotune_lighting(
                    self._tuning_base_img, current_fill=float(t_params.get("fill", 0.0))
                )
                if hasattr(self.edit_panel, "set_tuning_sliders_from_params"):
                    self.edit_panel.set_tuning_sliders_from_params(hl_auto, sh_auto)
                t_params["highlights"] = hl_auto
                t_params["shadows"] = sh_auto
            elif effect_name == "autotune_color":
                n_rgb = PicasaImageProcessor.compute_autotune_color(self._tuning_base_img)
                if hasattr(self.edit_panel, "set_tuning_neutral_rgb"):
                    self.edit_panel.set_tuning_neutral_rgb(n_rgb)
                t_params["neutral_rgb"] = n_rgb
            elif effect_name == "fill_light" and "amount" in params:
                t_params["fill"] = float(params["amount"])
            elif effect_name == "highlights" and "amount" in params:
                t_params["highlights"] = float(params["amount"])
            elif effect_name == "shadows" and "amount" in params:
                t_params["shadows"] = float(params["amount"])
            elif effect_name == "color_temp" and "temp" in params:
                t_params["colortemp"] = float(params["temp"])

            neutral_rgb = int(t_params.get("neutral_rgb", 0)) & 0x00FFFFFF
            new_img = PicasaImageProcessor.finetune(
                self._tuning_base_img,
                fill=t_params["fill"],
                highlights=t_params["highlights"],
                shadows=t_params["shadows"],
                colortemp=t_params["colortemp"],
                neutral_rgb=neutral_rgb,
            )
            # FR: Mettre à jour le créneau d'historique de réglage en place au lieu d'empiler à chaque mouvement de curseur
            # EN: Update the tuning history slot in place instead of stacking on every slider movement
            if self._tuning_history_slot == self._history_idx and self._tuning_history_slot > 0:
                self._history[self._history_idx] = new_img.copy()
                self._display_current_history(preserve_view=True)
            else:
                self._push_history(new_img, preserve_view=True)
                self._tuning_history_slot = self._history_idx

            target_path = self.current_photo_path
            if target_path and os.path.exists(target_path):
                fill_v = t_params["fill"]
                hl_v = t_params["highlights"]
                sh_v = t_params["shadows"]
                ct_v = t_params["colortemp"]
                if abs(fill_v) < 1e-4 and abs(hl_v) < 1e-4 and abs(sh_v) < 1e-4 and abs(ct_v) < 1e-4 and neutral_rgb == 0:
                    self._update_ini_tuning_token(target_path, None)
                else:
                    # Ref: picasa3.exe @ 0x008FAC40 : finetune2=1,<fill:%f>,<highlights:%f>,<shadows:%f>,<neutral_rgb:%08x>,<colortemp:%f>
                    self._update_ini_tuning_token(
                        target_path,
                        f"finetune2=1,{fill_v:.6f},{hl_v:.6f},{sh_v:.6f},{neutral_rgb:08x},{ct_v:.6f}",
                    )
                self._schedule_thumb_db_sync(new_img, target_path)
            return

        if effect_name == "reset_lighting":
            base_restored = (
                self._tuning_base_img.copy()
                if self._tuning_base_img is not None
                else (self._original_pil_img.copy() if self._original_pil_img else None)
            )
            if base_restored is not None:
                if self._tuning_history_slot == self._history_idx and self._tuning_history_slot > 0:
                    self._history[self._history_idx] = base_restored.copy()
                    self._display_current_history()
                else:
                    self._push_history(base_restored)
                target_path = self.current_photo_path
                if target_path and os.path.exists(target_path):
                    self._update_ini_tuning_token(target_path, None)
                    self._sync_current_thumbnails_to_db(base_restored)
                    self.photo_edited.emit(target_path)
            return

        # FR: --- Cas 2 : Filtres standards et effets validés (Tab 1, 3, 4, 5) ---
        # EN: --- Case 2: Standard filters and committed effects (Tab 1, 3, 4, 5) ---
        current_img = self._history[self._history_idx]
        new_img = PicasaImageProcessor.execute_effect(current_img, effect_name, params)

        if new_img:
            self._push_history(new_img)
            # FR: La nouvelle image validée devient la nouvelle base pour les curseurs de réglage d'éclairage
            # EN: The newly committed image becomes the new base for lighting adjustment sliders
            self._tuning_base_img = new_img.copy()
            self._tuning_history_slot = -1
            self.edit_panel.reset_tuning_controls_silently()

            target_path = self.current_photo_path
            if target_path and os.path.exists(target_path):
                token = self._effect_to_ini_token(effect_name, params)
                if token:
                    self._append_filter_to_ini(token, target_path)
                self._sync_current_thumbnails_to_db(new_img)
                self.photo_edited.emit(target_path)

    @staticmethod
    def _extract_rgb(col: Any, default: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """
        FR: Extrait un triplet (R, G, B) entier depuis un QColor ou un tuple/liste.
        EN: Extracts an integer (R, G, B) tuple from a QColor or a tuple/list.
        """
        if hasattr(col, "red"):
            return int(col.red()), int(col.green()), int(col.blue())
        if isinstance(col, (tuple, list)) and len(col) >= 3:
            return int(col[0]), int(col[1]), int(col[2])
        return default

    def _effect_to_ini_token(self, effect_name: str, params: Optional[dict] = None) -> Optional[str]:
        """
        FR: Convertit un nom d'effet et ses paramètres de curseurs en jeton `filters=` pour `.picasa.ini`.
        EN: Converts an effect name and its slider parameters into a `filters=` token for `.picasa.ini`.
        Ref: picasa3.exe @ filterdesc.xml, 0x008814AC, 0x00760F40
        """
        p = params or {}
        if effect_name == "autocontrast":
            return "autolight=1"
        if effect_name == "lucky":
            return "enhance=1"
        if effect_name == "autocolor":
            return "autocolor=1"
        if effect_name == "whitept":
            r, g, b = self._extract_rgb(p.get("color", (128, 128, 128)), (128, 128, 128))
            return f"whitept=1,{r},{g},{b}"
        if effect_name == "bw":
            return "bw=1"
        if effect_name == "sepia":
            return "sepia=1"
        if effect_name == "warmify":
            return "warm=1"
        if effect_name == "sharpen":
            return f"unsharp2=1,{float(p.get('amount', 0.6)):.6f}"
        if effect_name in ("grain", "film_grain"):
            return f"PicnikGrain=1,{int(round(float(p.get('intensity', 18.0))))},{int(round(float(p.get('fade', 0.0))))},0"
        if effect_name == "tint":
            r, g, b = self._extract_rgb(p.get("color", (220, 190, 150)), (220, 190, 150))
            fade_pct = max(0.0, min(100.0, (1.0 - float(p.get("intensity", 0.4))) * 100.0))
            return f"PicnikTint=1,{fade_pct:.6f},{(r << 16) | (g << 8) | b:08x}"
        if effect_name == "saturation":
            return f"sat=1,{float(p.get('factor', p.get('amount', 0.1618))):.6f}"
        if effect_name == "soft_focus":
            cx = float(p.get("cx", 0.5))
            cy = float(p.get("cy", 0.5))
            size = float(p.get("size", 0.35))
            amount = float(p.get("amount", 0.4))
            return f"radblur=1,{cx:.6f},{cy:.6f},{size:.6f},{amount:.6f}"
        if effect_name == "glow":
            return f"glow2=1,{float(p.get('intensity', 0.65)):.6f},{float(p.get('radius', 3.0)):.6f}"
        if effect_name == "focal_bw":
            cx = float(p.get("cx", 0.5))
            cy = float(p.get("cy", 0.5))
            size = float(p.get("size", 0.35))
            sharp = float(p.get("sharpness", 0.4))
            return f"radsat=1,{cx:.6f},{cy:.6f},{size:.6f},{sharp:.6f}"
        if effect_name == "graduated_tint":
            r, g, b = self._extract_rgb(p.get("color", (123, 180, 216)), (123, 180, 216))
            cx = float(p.get("cx", 0.5))
            cy = float(p.get("cy", 0.5))
            feather = float(p.get("feather", 0.5))
            shade = float(p.get("shade", 0.5))
            angle = float(p.get("angle", 0.0))
            return f"dir_tint=1,{cx:.6f},{cy:.6f},{feather:.6f},{shade:.6f},{0xFF000000 | (r << 16) | (g << 8) | b:08x},{angle:.6f}"
        if effect_name == "filtered_bw":
            r, g, b = self._extract_rgb(p.get("color", (255, 85, 85)), (255, 85, 85))
            return f"ansel=1,{0xFF000000 | (r << 16) | (g << 8) | b:08x}"
        if effect_name == "hdr":
            return f"HDR=1,{float(p.get('radius', 20.0)):.2f},{float(p.get('strength', 3.0)):.2f},{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "lomo":
            return f"Lomo=1,{float(p.get('blur', 50.0)):.2f},{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "orton":
            return f"Orton=1,{float(p.get('bloom', 25.0)):.2f},{float(p.get('brightness', 50.0)):.2f},{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "sixties":
            return f"Sixties=1,{float(p.get('fade', 20.0)):.2f},00ffffff,1"
        if effect_name == "cross_process":
            return f"CrossProcess=1,{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "infrared":
            return f"IR=1,{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "holga":
            return f"Holga=1,{float(p.get('blur', 70.0)):.2f},{float(p.get('grain', 30.0)):.2f},{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "cinemascope":
            return f"Cinemascope=1,{float(p.get('color_boost', 0.0)):.2f},{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "night_vision":
            r, g, b = self._extract_rgb(p.get("color", (87, 204, 41)), (87, 204, 41))
            return f"NightVision=1,{float(p.get('grain', 20.0)):.2f},{float(p.get('fade', 0.0)):.2f},{(r << 16) | (g << 8) | b:08x}"
        if effect_name == "heat_map":
            return f"HeatMap=1,{float(p.get('shift', 0.0)):.2f},{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "polaroid":
            return f"Polaroid=1,{float(p.get('angle', 5.0)):.2f},00e2e2e2"
        if effect_name == "quantize_palette":
            return f"QuantizePalette=1,{int(round(float(p.get('steps', 8))))},80.00,0.00"
        if effect_name == "boost":
            return f"Boost=1,{float(p.get('impact', 50.0)):.2f}"
        if effect_name == "vignette":
            r, g, b = self._extract_rgb(p.get("color", (0, 0, 0)), (0, 0, 0))
            return f"Vignette=1,{float(p.get('amount', 0.5)):.4f},{float(p.get('size', 0.25)):.4f},{(r << 16) | (g << 8) | b:08x}"
        if effect_name == "two_tone":
            b_val = float(p.get("brightness", 0.0))
            c_val = float(p.get("contrast", 0.0))
            f_val = float(p.get("fade", 0.0))
            sr, sg, sb = self._extract_rgb(p.get("shadow_color", (0, 68, 136)), (0, 68, 136))
            hr, hg, hb = self._extract_rgb(p.get("highlight_color", (255, 255, 0)), (255, 255, 0))
            return f"TwoTone=1,{b_val:.1f},{c_val:.1f},{f_val:.1f},{(sr << 16) | (sg << 8) | sb:08x},{(hr << 16) | (hg << 8) | hb:08x}"
        if effect_name == "pixelate":
            return f"Pixelate=1,{int(round(float(p.get('block_size', 14))))},9.00,{float(p.get('fade', 0.0)):.2f}"
        if effect_name == "focal_pixelate":
            cx = float(p.get("cx", 0.5))
            cy = float(p.get("cy", 0.5))
            return f"PicnikFocalPixelate=1,{cx:.6f},{cy:.6f},{float(p.get('block_size', 15.0)):.2f},{float(p.get('size', 0.35)):.4f},{float(p.get('hardness', 50.0)):.2f},0"
        if effect_name == "invert":
            return "Invert=1"
        if effect_name == "focal_zoom":
            cx = float(p.get("cx", 0.5))
            cy = float(p.get("cy", 0.5))
            return f"FocalZoom=1,{cx:.6f},{cy:.6f},{float(p.get('zoom_amount', 30.0)):.2f},{float(p.get('size', 0.25)):.4f},{float(p.get('hardness', 50.0)):.2f},0.00"
        if effect_name == "soften":
            return f"Soften=1,{float(p.get('impact', 50.0)):.2f},{float(p.get('fade', 50.0)):.2f}"
        if effect_name == "comic":
            return f"Comicize=1,{float(p.get('radius', 40.0)):.2f},{float(p.get('strength', 75.0)):.2f},50.00"
        if effect_name == "neon":
            fade = float(p.get("fade", 0.0))
            r, g, b = self._extract_rgb(p.get("color", (0, 255, 255)), (0, 255, 255))
            return f"Neon=1,{fade:.2f},{(r << 16) | (g << 8) | b:08x}"
        if effect_name == "pencil_sketch":
            return f"PencilSketch=1,{float(p.get('radius', 2.0)):.2f},{float(p.get('contrast', 100.0)):.2f},0.00"
        if effect_name == "border":
            outer_t = float(p.get("outer_thickness", 15.0))
            inner_t = float(p.get("inner_thickness", 3.0))
            rad = float(p.get("corner_radius", 0.0))
            or_, og, ob = self._extract_rgb(p.get("outer_color", (26, 26, 26)), (26, 26, 26))
            ir, ig, ib = self._extract_rgb(p.get("inner_color", (255, 255, 255)), (255, 255, 255))
            return f"Border=1,{outer_t:.1f},{inner_t:.1f},{rad:.1f},{(or_ << 16) | (og << 8) | ob:08x},{(ir << 16) | (ig << 8) | ib:08x},0.00"
        if effect_name == "museum_matte":
            in_t = float(p.get("inner_thickness", 12.0))
            out_t = float(p.get("outer_thickness", 7.0))
            ir, ig, ib = self._extract_rgb(p.get("inner_color", (240, 234, 228)), (240, 234, 228))
            or_, og, ob = self._extract_rgb(p.get("outer_color", (26, 14, 3)), (26, 14, 3))
            return f"MuseumMatte=1,{in_t:.2f},0,0,{out_t:.2f},{(ir << 16) | (ig << 8) | ib:08x},{(or_ << 16) | (og << 8) | ob:08x}"
        if effect_name == "drop_shadow":
            dist = float(p.get("distance", 6.0))
            ang = float(p.get("angle", 45.0))
            blur = float(p.get("blur", 8.0))
            fade = float(p.get("fade", 50.0))
            br, bg_g, bb = self._extract_rgb(p.get("bg_color", (255, 255, 255)), (255, 255, 255))
            return f"DropShadow=1,{dist:.1f},{ang:.1f},{blur:.1f},00000000,{(br << 16) | (bg_g << 8) | bb:08x},{fade:.1f}"
        if effect_name == "rounded_edges":
            rr = float(p.get("corner_radius", 10.0)) / 100.0
            or_, og, ob = self._extract_rgb(p.get("outer_color", (255, 255, 255)), (255, 255, 255))
            return f"RoundedEdges=1,{rr:.4f},{(or_ << 16) | (og << 8) | ob:08x}"
        if effect_name == "local_contrast":
            return f"LocalContrast=1,{float(p.get('radius', 15.0)):.2f},{float(p.get('strength', 1.5)):.2f},{float(p.get('fade', 0.0)):.2f}"
        return None

    def _append_filter_to_ini(self, token: str, target_path: Optional[str] = None) -> None:
        """
        FR: Ajoute un jeton de filtre à la clé `filters=` dans `.picasa.ini`.
        EN: Appends a filter token to the `filters=` key in `.picasa.ini`.
        """
        t_path = target_path or self.current_photo_path
        if not t_path and self.db and 0 <= self.current_index < len(self.db.index):
            t_path = self.db.get_media_full_path(self.current_index)
        if t_path and os.path.exists(t_path):
            clean_tok = token.strip().rstrip(";")
            if clean_tok:
                self._update_ini(t_path, lambda doc, fname: doc.append_filter(fname, clean_tok))

    def _update_ini(self, target_path: str, modify_fn) -> None:
        """
        FR: Met à jour .picasa.ini via PicasaDatabase (si disponible) ou PicasaIniDocument.
        EN: Updates .picasa.ini via PicasaDatabase (if available) or PicasaIniDocument.
        """
        if not target_path or not os.path.exists(target_path):
            return
        if self.db is not None and hasattr(self.db, "update_photo_ini"):
            self.db.update_photo_ini(target_path, modify_fn)
        else:
            p = Path(target_path)
            ini_path = p.parent / ".picasa.ini"
            from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
            doc = PicasaIniParser.parse_file(str(ini_path)) if ini_path.exists() else PicasaIniDocument()
            modify_fn(doc, p.name)
            doc.write_file(str(ini_path))
        if 0 <= self._history_idx < len(self._history_ini_snapshots):
            self._history_ini_snapshots[self._history_idx] = self._read_current_ini_snapshot(target_path)

    def _on_rotate_left(self) -> None:
        """
        FR: Pivote la photo de 90° vers la gauche et enregistre rotate=rotate(n) dans .picasa.ini.
        EN: Rotates the photo 90° counterclockwise and saves rotate=rotate(n) in .picasa.ini.
        """
        self._active_rotate = (self._active_rotate - 1) % 4
        self.canvas.set_active_transform(self._active_crop_rect, self._active_tilt, self._active_rotate)
        if self._history and 0 <= self._history_idx < len(self._history):
            self._history[self._history_idx] = self._history[self._history_idx].rotate(90, expand=True)
            if self._tuning_base_img is not None:
                self._tuning_base_img = self._tuning_base_img.rotate(90, expand=True)
            self._display_current_history(preserve_view=False)
        else:
            self.canvas.rotate_counterclockwise()
        target_path = self.current_photo_path
        if target_path and os.path.exists(target_path):
            self._update_ini(target_path, lambda doc, fname: doc.set_rotate(fname, (doc.get_rotate(fname) - 1) % 4))
            curr_img = self._history[self._history_idx] if (self._history and 0 <= self._history_idx < len(self._history)) else None
            self.right_drawer.set_current_photo(self.db, self.current_index, target_path, source_img=curr_img)
            self._sync_current_thumbnails_to_db()
            self.photo_edited.emit(target_path)

    def _on_rotate_right(self) -> None:
        """
        FR: Pivote la photo de 90° vers la droite et enregistre rotate=rotate(n) dans .picasa.ini.
        EN: Rotates the photo 90° clockwise and saves rotate=rotate(n) in .picasa.ini.
        """
        self._active_rotate = (self._active_rotate + 1) % 4
        self.canvas.set_active_transform(self._active_crop_rect, self._active_tilt, self._active_rotate)
        if self._history and 0 <= self._history_idx < len(self._history):
            self._history[self._history_idx] = self._history[self._history_idx].rotate(270, expand=True)
            if self._tuning_base_img is not None:
                self._tuning_base_img = self._tuning_base_img.rotate(270, expand=True)
            self._display_current_history(preserve_view=False)
        else:
            self.canvas.rotate_clockwise()
        target_path = self.current_photo_path
        if target_path and os.path.exists(target_path):
            self._update_ini(target_path, lambda doc, fname: doc.set_rotate(fname, (doc.get_rotate(fname) + 1) % 4))
            curr_img = self._history[self._history_idx] if (self._history and 0 <= self._history_idx < len(self._history)) else None
            self.right_drawer.set_current_photo(self.db, self.current_index, target_path, source_img=curr_img)
            self._sync_current_thumbnails_to_db()
            self.photo_edited.emit(target_path)

    def _on_undo(self) -> None:
        """
        FR: Annule la dernière opération dans l'historique d'édition et restaure l'état précédent.
        EN: Undoes the last operation in the edit history and restores the previous state.
        """
        if self._history_idx > 0:
            self._history_idx -= 1
            self._tuning_base_img = self._history[self._history_idx].copy()
            self._tuning_history_slot = -1
            self._effect_preview_base_img = None
            self.edit_panel.reset_tuning_controls_silently()
            self._display_current_history()
            if 0 <= self._history_idx < len(self._history_ini_snapshots):
                self._restore_ini_snapshot(self._history_ini_snapshots[self._history_idx])

    def _on_redo(self) -> None:
        """
        FR: Rétablit l'opération suivante dans l'historique d'édition.
        EN: Redoes the next operation in the edit history.
        """
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self._tuning_base_img = self._history[self._history_idx].copy()
            self._tuning_history_slot = -1
            self._effect_preview_base_img = None
            self.edit_panel.reset_tuning_controls_silently()
            self._display_current_history()
            if 0 <= self._history_idx < len(self._history_ini_snapshots):
                self._restore_ini_snapshot(self._history_ini_snapshots[self._history_idx])

    # FR: --- Gestion du recadrage interactif (Ref: editpanel/crop*, CSmartCrop) ---
    # EN: --- Interactive crop management (Ref: editpanel/crop*, CSmartCrop) ---

    def _on_crop_start(self) -> None:
        """
        FR: Démarre le mode recadrage interactif sur le canevas et verrouille les barres d'interface (`mode == 2`).
        EN: Starts interactive cropping mode on the canvas and locks the UI bars (`mode == 2`).

        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50, mode == 2)
        """
        self._set_modal_tool_lock(True, 2, "crop")
        self.canvas.start_crop()

    def _on_crop_apply(self) -> None:
        """
        FR: Applique le recadrage, le persiste dans .picasa.ini, recharge l'image cadrée et déverrouille l'interface.
        EN: Applies the crop, persists it in .picasa.ini, reloads the cropped image, and unlocks the UI.

        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50, locked=0)
        """
        self._set_modal_tool_lock(False, 0, "")
        crop_str = self.canvas.apply_crop()
        if self._active_crop_rect is not None or self._active_rotate != 0:
            try:
                from picasa_py.faces.facerect import decode_rect64_string
                cl, ct, cr, cb = decode_rect64_string(crop_str)
                orig_c = FaceRect(cl, ct, cr, cb)
                if self._active_rotate:
                    orig_c = orig_c.from_rotated_space(self._active_rotate)
                if self._active_crop_rect is not None:
                    orig_c = orig_c.from_cropped_space(self._active_crop_rect)
                crop_str = orig_c.to_rect64()
            except Exception:
                pass
        target_path = self.current_photo_path
        if not target_path and self.db and 0 <= self.current_index < len(self.db.index):
            target_path = self.db.get_media_full_path(self.current_index)

        if not target_path:
            return

        prev_idx = self._history_idx
        prev_snap = (
            self._history_ini_snapshots[prev_idx]
            if 0 <= prev_idx < len(self._history_ini_snapshots)
            else self._read_current_ini_snapshot(target_path)
        )
        def _apply_crop_doc(doc, fname: str) -> None:
            doc.set_crop(fname, crop_str)
            clean_hex = crop_str.strip()
            if clean_hex.lower().startswith("rect64(") and clean_hex.endswith(")"):
                clean_hex = clean_hex[7:-1]
            if clean_hex:
                doc.append_filter(fname, f"crop64=1,{clean_hex}")

        self._update_ini(target_path, _apply_crop_doc)
        if 0 <= prev_idx < len(self._history_ini_snapshots):
            self._history_ini_snapshots[prev_idx] = prev_snap
        if self.db is not None and hasattr(self.db, "_ini_cache") and isinstance(self.db._ini_cache, dict):
            self.db._ini_cache.clear()

        pil_img = self._load_pil_image_at_index(self.current_index, direct_path=target_path)
        if pil_img is not None:
            self._tuning_base_img = pil_img.copy()
            self._tuning_history_slot = -1
            self._effect_preview_base_img = None
            self._push_history(pil_img)
            self.canvas.set_active_transform(self._active_crop_rect, self._active_tilt, self._active_rotate)
            self.right_drawer.set_current_photo(self.db, self.current_index, target_path, source_img=pil_img)
        self._sync_current_thumbnails_to_db(pil_img)
        self.photo_edited.emit(target_path)

    def _on_crop_discard(self) -> None:
        """
        FR: Supprime le recadrage existant dans .picasa.ini, réinitialise l'image et déverrouille l'interface.
        EN: Removes the existing crop from .picasa.ini, resets the image, and unlocks the UI.

        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50, locked=0)
        """
        self._set_modal_tool_lock(False, 0, "")
        self.canvas.cancel_crop()
        target_path = self.current_photo_path
        if not target_path and self.db and 0 <= self.current_index < len(self.db.index):
            target_path = self.db.get_media_full_path(self.current_index)

        if not target_path:
            return

        prev_idx = self._history_idx
        prev_snap = (
            self._history_ini_snapshots[prev_idx]
            if 0 <= prev_idx < len(self._history_ini_snapshots)
            else self._read_current_ini_snapshot(target_path)
        )
        self._update_ini(target_path, lambda doc, fname: doc.set_crop(fname, None))
        if 0 <= prev_idx < len(self._history_ini_snapshots):
            self._history_ini_snapshots[prev_idx] = prev_snap
        if self.db is not None and hasattr(self.db, "_ini_cache") and isinstance(self.db._ini_cache, dict):
            self.db._ini_cache.clear()

        pil_img = self._load_pil_image_at_index(self.current_index, direct_path=target_path)
        if pil_img is not None:
            self._tuning_base_img = pil_img.copy()
            self._tuning_history_slot = -1
            self._effect_preview_base_img = None
            self._push_history(pil_img)
            self.canvas.set_active_transform(self._active_crop_rect, self._active_tilt, self._active_rotate)
            self.right_drawer.set_current_photo(self.db, self.current_index, target_path, source_img=pil_img)
        self._sync_current_thumbnails_to_db(pil_img)
        self.photo_edited.emit(target_path)

    # FR: --- Outil Redresser (Ref: filter_tilt, picasa3.exe @ 0x008814AC) ---
    # EN: --- Straighten tool (Ref: filter_tilt, picasa3.exe @ 0x008814AC) ---

    def _on_straighten_start(self) -> None:
        """
        FR: Démarre l'outil de redressement d'horizon sur le canevas, force le zoom Ajuster (`forcefit="1"`)
        et verrouille les barres d'interface (`mode == 6`).
        EN: Starts the horizon straightening tool on the canvas, forces zoom-to-fit (`forcefit="1"`),
        and locks the UI bars (`mode == 6`).

        Ref: picasa3.exe @ 0x005F8520, 0x005F8730, 0x0057BB50 (mode == 6)
        """
        self._set_modal_tool_lock(True, 6, "straighten")
        self.canvas.start_straighten(0.0)

    def _on_straighten_apply(self) -> None:
        """
        FR: Valide l'angle de redressement, l'enregistre dans `.picasa.ini` (`tilt=1,angle,0.000000`),
        recharge la photo et déverrouille l'interface.
        EN: Commits the straighten angle, saves it in `.picasa.ini` (`tilt=1,angle,0.000000`),
        reloads the photo, and unlocks the UI.

        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50, locked=0)
        """
        self._set_modal_tool_lock(False, 0, "")
        angle = self.canvas.apply_straighten()
        effective_angle = max(-45.0, min(45.0, self._active_tilt + angle)) if abs(angle) >= 0.01 else 0.0
        target_path = self.current_photo_path
        if not target_path and self.db and 0 <= self.current_index < len(self.db.index):
            target_path = self.db.get_media_full_path(self.current_index)

        if not target_path:
            return

        prev_idx = self._history_idx
        prev_snap = (
            self._history_ini_snapshots[prev_idx]
            if 0 <= prev_idx < len(self._history_ini_snapshots)
            else self._read_current_ini_snapshot(target_path)
        )
        self._update_ini(target_path, lambda doc, fname: doc.set_tilt(fname, effective_angle))
        if 0 <= prev_idx < len(self._history_ini_snapshots):
            self._history_ini_snapshots[prev_idx] = prev_snap
        if self.db is not None and hasattr(self.db, "_ini_cache") and isinstance(self.db._ini_cache, dict):
            self.db._ini_cache.clear()

        # FR: Recharger l'image redressée, mettre à jour l'historique, le canevas et les visages du tiroir droit
        # EN: Reload the straightened image, update history, canvas, and right drawer faces
        pil_img = self._load_pil_image_at_index(self.current_index, direct_path=target_path)
        if pil_img is not None:
            self._tuning_base_img = pil_img.copy()
            self._tuning_history_slot = -1
            self._effect_preview_base_img = None
            self._push_history(pil_img)
            self.canvas.set_active_transform(self._active_crop_rect, self._active_tilt, self._active_rotate)
            self.right_drawer.set_current_photo(self.db, self.current_index, target_path, source_img=pil_img)
        self._sync_current_thumbnails_to_db(pil_img)
        self.photo_edited.emit(target_path)

    # FR: --- Outil Texte (Ref: editpanel/edittextpanel, picasa3.exe @ 0x00658900) ---
    # EN: --- Text tool (Ref: editpanel/edittextpanel, picasa3.exe @ 0x00658900) ---

    def _on_text_tool_start(self) -> None:
        """
        FR: Démarre l'outil de superposition de texte sur le canevas et verrouille les barres d'interface (`mode == 2`).
        EN: Starts the text overlay tool on the canvas and locks the UI bars (`mode == 2`).

        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50, mode == 2)
        """
        self._set_modal_tool_lock(True, 2, "text")
        self.canvas.start_text_tool("")

    def _on_text_params_changed(self, text: str, font_size: int, color: Any, shadow: bool) -> None:
        """
        FR: Met à jour en temps réel les paramètres du texte (contenu, taille, couleur, ombre) sur le canevas.
        EN: Updates the text overlay parameters (content, size, color, shadow) in real time on the canvas.
        """
        self.canvas.set_text_params(text, font_size, color, shadow)

    def _on_text_apply(self) -> None:
        """
        FR: Valide la superposition de texte, l'applique à l'historique PIL, persiste le jeton `text=`
        dans `.picasa.ini` et déverrouille l'interface.
        EN: Commits the text overlay, applies it to the PIL history, persists the `text=` token
        in `.picasa.ini`, and unlocks the UI.

        Ref: picasa3.exe @ 0x0057BB50 (FUN_0057bb50, locked=0)
        """
        self._set_modal_tool_lock(False, 0, "")
        params = self.canvas.apply_text_tool()
        txt = params.get("text", "").strip()
        if not txt:
            return

        target_path = self.current_photo_path
        if not target_path and self.db and 0 <= self.current_index < len(self.db.index):
            target_path = self.db.get_media_full_path(self.current_index)

        if not target_path:
            return

        size = int(params.get("font_size", 28))
        r, g, b = self._extract_rgb(params.get("color", (255, 255, 255)), (255, 255, 255))
        pos_norm = params.get("pos_norm", (0.15, 0.85))
        px, py = float(pos_norm[0]), float(pos_norm[1])
        shadow = bool(params.get("shadow", True))

        # FR: Application PIL sur l'historique d'édition
        # EN: Apply text rendering via PIL onto the edit history
        if self._history and 0 <= self._history_idx < len(self._history):
            curr_img = self._history[self._history_idx]
            new_img = PicasaImageProcessor.add_text(
                curr_img,
                txt,
                (px, py),
                size,
                (r, g, b),
                shadow,
            )
            self._push_history(new_img)

        # Ref: picasa3.exe @ 0x00A4DB30, 0x00A4E3A0 (CTextItemList exact format)
        utf8_len = len(txt.encode("utf-8"))
        scale = max(0.02, min(0.5, float(size) / 360.0))
        fill_argb = 0xFF000000 | ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)
        outline_w = 2.0 if shadow else 0.0
        outline_argb = 0xFF000000
        text_token = (
            f"1;{utf8_len};{txt};Arial;{px:.6f},{py:.6f},{scale:.6f},0.000000;"
            f"v1,400,400,128.000000,{outline_w:.6f},1.000000,1.000000,{outline_argb},{fill_argb},32768;"
        )
        self._update_ini(target_path, lambda doc, fname: doc.set_text(fname, text_token))
        self._sync_current_thumbnails_to_db()
        self.photo_edited.emit(target_path)

    # FR: --- Outils Yeux Rouges & Retouche (Ref: filterdesc.xml @ redeye, retouch) ---
    # EN: --- Red-eye & Retouch tools (Ref: filterdesc.xml @ redeye, retouch) ---

    def _on_redeye_apply(self) -> None:
        """
        FR: Applique l'atténuation automatique des yeux rouges, persiste `redeye=1` dans `.picasa.ini` et déverrouille l'interface.
        EN: Applies automatic red-eye reduction, persists `redeye=1` in `.picasa.ini`, and unlocks the UI.

        Ref: picasa3.exe @ 0x008FAC40, filterdesc.xml @ redeye
        """
        self._set_modal_tool_lock(False, 0, "")
        self.canvas.cancel_redeye()
        if self._history_idx < 0 or not self._history:
            return
        curr_img = self._history[self._history_idx]
        new_img = PicasaImageProcessor.remove_red_eye(curr_img)
        self._push_history(new_img)
        self._append_filter_to_ini("redeye=1")
        self._sync_current_thumbnails_to_db(new_img)
        target_path = self.current_photo_path
        if target_path:
            self.photo_edited.emit(target_path)

    def _on_retouch_apply(self, radius: float) -> None:
        """
        FR: Applique le lissage local de retouche d'imperfections, persiste `retouch=1,...` dans `.picasa.ini` et déverrouille l'interface.
        EN: Applies local blemish healing smoothing, persists `retouch=1,...` in `.picasa.ini`, and unlocks the UI.

        Ref: picasa3.exe @ 0x008FAC40, filterdesc.xml @ retouch
        """
        self._set_modal_tool_lock(False, 0, "")
        self.canvas.cancel_retouch()
        if self._history_idx < 0 or not self._history:
            return
        curr_img = self._history[self._history_idx]
        new_img = PicasaImageProcessor.retouch_heal(curr_img, (0.5, 0.5), radius)
        self._push_history(new_img)
        self._append_filter_to_ini(f"retouch=1,0.500000,0.500000,{float(radius):.6f}")
        self._sync_current_thumbnails_to_db(new_img)
        target_path = self.current_photo_path
        if target_path:
            self.photo_edited.emit(target_path)

    def _on_canvas_retouch(self, nx: float, ny: float, radius: float) -> None:
        """
        FR: Applique une retouche locale à la position cliquée sur la photo et la persiste dans `.picasa.ini`.
        EN: Applies a local blemish retouch at the clicked normalized position on the photo and persists it in `.picasa.ini`.

        Ref: picasa3.exe @ 0x008FAC40, filterdesc.xml @ retouch
        """
        if self._history_idx < 0 or not self._history:
            return
        curr_img = self._history[self._history_idx]
        new_img = PicasaImageProcessor.retouch_heal(curr_img, (nx, ny), radius)
        self._push_history(new_img)
        self._append_filter_to_ini(f"retouch=1,{float(nx):.6f},{float(ny):.6f},{float(radius):.6f}")
        self._sync_current_thumbnails_to_db(new_img)
        target_path = self.current_photo_path
        if target_path:
            self.photo_edited.emit(target_path)

    def _on_canvas_redeye_point(self, nx: float, ny: float) -> None:
        """
        FR: Applique la suppression des yeux rouges sur le point cliqué et la persiste dans `.picasa.ini`.
        EN: Applies red-eye removal around the clicked point and persists it in `.picasa.ini`.

        Ref: picasa3.exe @ 0x008FAC40, filterdesc.xml @ redeye
        """
        if self._history_idx < 0 or not self._history:
            return
        curr_img = self._history[self._history_idx]
        box = (max(0.0, nx - 0.025), max(0.0, ny - 0.025), min(1.0, nx + 0.025), min(1.0, ny + 0.025))
        new_img = PicasaImageProcessor.remove_red_eye(curr_img, box)
        self._push_history(new_img)
        self._append_filter_to_ini(f"redeye=1,{box[0]:.6f},{box[1]:.6f},{box[2]:.6f},{box[3]:.6f}")
        self._sync_current_thumbnails_to_db(new_img)
        target_path = self.current_photo_path
        if target_path:
            self.photo_edited.emit(target_path)

    def _on_canvas_redeye_box(self, rect: QRectF) -> None:
        """
        FR: Applique la suppression des yeux rouges sur le rectangle sélectionné et la persiste dans `.picasa.ini`.
        EN: Applies red-eye removal within the selected bounding rectangle and persists it in `.picasa.ini`.

        Ref: picasa3.exe @ 0x008FAC40, filterdesc.xml @ redeye
        """
        if self._history_idx < 0 or not self._history:
            return
        curr_img = self._history[self._history_idx]
        box = (rect.left(), rect.top(), rect.right(), rect.bottom())
        new_img = PicasaImageProcessor.remove_red_eye(curr_img, box)
        self._push_history(new_img)
        self._append_filter_to_ini(f"redeye=1,{box[0]:.6f},{box[1]:.6f},{box[2]:.6f},{box[3]:.6f}")
        self._sync_current_thumbnails_to_db(new_img)
        target_path = self.current_photo_path
        if target_path:
            self.photo_edited.emit(target_path)

    def _on_video_snapshot_captured(self, snapshot_path: str) -> None:
        """
        FR: Notifie l'application lorsqu'une capture d'écran vidéo a été enregistrée.
        EN: Notifies the application when a video frame snapshot has been saved.
        """
        if snapshot_path:
            self.photo_edited.emit(snapshot_path)

    def navigate_previous(self) -> None:
        """
        FR: Navigue vers le média précédent dans la liste disponible (ou dans le volet B en mode A|B).
        Bloqué lorsqu'un outil ou filtre modal verrouille l'interface (`[edi + 0x274] == 0` dans `FUN_0057bb50`).
        EN: Navigates to the previous media item in the available list (or in pane B in A|B mode).
        Blocked when a modal tool or filter locks the UI (`[edi + 0x274] == 0` in `FUN_0057bb50`).

        Ref: picasa3.exe @ 0x0057BBD3 (FUN_0057bb50)
        """
        if getattr(self, "_is_tool_locked", False):
            return
        self._flush_pending_thumb_db_sync()
        if hasattr(self, "video_player"):
            self.video_player.stop()
        if not self.available_indices or self.db is None:
            return

        # FR: En mode A|B, si le volet B est actif, on fait défiler la photo B
        # EN: In A|B mode, if pane B is active, scroll photo B
        if self.canvas.view_mode == "A_B" and self.canvas.active_pane == "B":
            try:
                curr_pos = self.available_indices.index(self.secondary_index)
                if curr_pos > 0:
                    self.secondary_index = self.available_indices[curr_pos - 1]
                    self._load_secondary_photo()
                    self.filmstrip.set_current_index(self.secondary_index)
            except ValueError:
                pass
            return

        # FR: En mode A ou A|A, faire défiler la photo principale
        # EN: In A or A|A mode, scroll the primary photo
        try:
            curr_pos = self.available_indices.index(self.current_index)
            if curr_pos > 0:
                prev_idx = self.available_indices[curr_pos - 1]
                self.open_photo(self.db, prev_idx, self.available_indices)
        except ValueError:
            pass

    def navigate_next(self) -> None:
        """
        FR: Navigue vers le média suivant dans la liste disponible (ou dans le volet B en mode A|B).
        Bloqué lorsqu'un outil ou filtre modal verrouille l'interface (`[edi + 0x274] == 0` dans `FUN_0057bb50`).
        EN: Navigates to the next media item in the available list (or in pane B in A|B mode).
        Blocked when a modal tool or filter locks the UI (`[edi + 0x274] == 0` in `FUN_0057bb50`).

        Ref: picasa3.exe @ 0x0057BBD3 (FUN_0057bb50)
        """
        if getattr(self, "_is_tool_locked", False):
            return
        self._flush_pending_thumb_db_sync()
        if hasattr(self, "video_player"):
            self.video_player.stop()
        if not self.available_indices or self.db is None:
            return

        # FR: En mode A|B, si le volet B est actif, on fait défiler la photo B
        # EN: In A|B mode, if pane B is active, scroll photo B
        if self.canvas.view_mode == "A_B" and self.canvas.active_pane == "B":
            try:
                curr_pos = self.available_indices.index(self.secondary_index)
                if curr_pos < len(self.available_indices) - 1:
                    self.secondary_index = self.available_indices[curr_pos + 1]
                    self._load_secondary_photo()
                    self.filmstrip.set_current_index(self.secondary_index)
            except ValueError:
                pass
            return

        # FR: En mode A ou A|A, faire défiler la photo principale
        # EN: In A or A|A mode, scroll the primary photo
        try:
            curr_pos = self.available_indices.index(self.current_index)
            if curr_pos < len(self.available_indices) - 1:
                next_idx = self.available_indices[curr_pos + 1]
                self.open_photo(self.db, next_idx, self.available_indices)
        except ValueError:
            pass

    def keyPressEvent(self, event) -> None:
        """
        FR: Gère les raccourcis clavier de la vue One-Up (flèches Gauche/Droite, Échap/Entrée, A, B, Ctrl+T).
        Lorsqu'un outil ou filtre modal est ouvert (`_is_tool_locked`), Échap annule l'outil actif
        sans quitter la vue One-Up, et les raccourcis de navigation/comparaison sont bloqués.
        EN: Handles keyboard shortcuts in One-Up View (Left/Right arrows, Escape/Enter, A, B, Ctrl+T).
        When a modal tool or filter is open (`_is_tool_locked`), Escape cancels the active tool
        without leaving One-Up View, and navigation/comparison shortcuts are blocked.

        Ref: picasa3.exe @ 0x0057BB50, 0x005F8160 (editpanel/cancel)
        """
        if getattr(self, "_is_tool_locked", False):
            if event.key() == Qt.Key.Key_Escape:
                if self.edit_panel.stack.currentIndex() != 0:
                    self.edit_panel.cancel_active_subpanel()
                else:
                    self.canvas.cancel_manual_face_add()
                    self._set_modal_tool_lock(False, 0, "")
                return
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Left:
            self.navigate_previous()
        elif event.key() == Qt.Key.Key_Right:
            self.navigate_next()
        elif event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._flush_pending_thumb_db_sync()
            self.back_to_library_requested.emit()
        elif event.key() == Qt.Key.Key_A:
            # FR: Raccourci A pour basculer en mode A simple
            # EN: Shortcut A to switch to single A view mode
            self.mode_btn_group.button(0).setChecked(True)
            self._on_view_mode_changed(0)
        elif event.key() == Qt.Key.Key_B:
            # FR: Raccourci B pour basculer en mode A|B
            # EN: Shortcut B to switch to A|B comparison mode
            self.mode_btn_group.button(1).setChecked(True)
            self._on_view_mode_changed(1)
        elif event.key() == Qt.Key.Key_T and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            # FR: Raccourci Ctrl+T pour basculer le statut favori (Ref: ID_PICTURE_STAR)
            # EN: Shortcut Ctrl+T to toggle favorite status (Ref: ID_PICTURE_STAR)
            self._toggle_star_current()
        else:
            super().keyPressEvent(event)

    def save_current_photo(self) -> bool:
        """
        FR: Enregistre les modifications apportées à la photo active sur le disque en pleine résolution.
        Crée une copie de sauvegarde dans le dossier caché `.picasaoriginals/` exactement comme
        `picasa3.exe`, préserve les métadonnées EXIF/ICC, écrit `backuphash` et nettoie les jetons
        de retouche dans `.picasa.ini`.
        EN: Saves modifications made to the active photo to disk at full resolution.
        Creates a backup copy in the hidden `.picasaoriginals/` directory exactly like
        `picasa3.exe`, preserves EXIF/ICC metadata, writes `backuphash`, and clears baked edit
        tokens from `.picasa.ini`.

        Ref: picasa3.exe @ .picasaoriginals (0x008814AC, 0x009B9290, 0x00456A15)
        """
        self._flush_pending_thumb_db_sync()
        if not self._history or self._history_idx < 0:
            return False

        target_path = getattr(self, "_current_photo_path", None)
        if not target_path and self.db and 0 <= self.current_index < len(self.db.index):
            target_path = self.db.get_media_full_path(self.current_index)
        if not target_path or not os.path.exists(target_path):
            return False

        current_img = self._history[self._history_idx]
        target_p = Path(target_path)
        folder = target_p.parent
        originals_dir = folder / ".picasaoriginals"

        try:
            originals_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ctypes.windll.kernel32.SetFileAttributesW(str(originals_dir), FILE_ATTRIBUTE_HIDDEN)
                except Exception:
                    pass

            backup_file = originals_dir / target_p.name
            if not backup_file.exists():
                import shutil
                shutil.copy2(target_path, str(backup_file))

            # FR: Si l'image disque est plus grande que l'aperçu 1600px et que .picasa.ini contient des retouches,
            #     rendre en pleine résolution (max_size=0) avant d'écraser le fichier.
            # EN: If the disk image is larger than the 1600px preview and .picasa.ini has edits,
            #     render at full resolution (max_size=0) before overwriting the file.
            img_to_save = current_img
            exif_bytes = None
            icc_profile = None
            try:
                with Image.open(target_path) as meta_im:
                    raw_w, raw_h = meta_im.size
                    icc_profile = meta_im.info.get("icc_profile")
                    raw_exif = meta_im.getexif()
                    if raw_exif:
                        if 0x0112 in raw_exif:
                            raw_exif[0x0112] = 1
                        exif_bytes = raw_exif.tobytes()
                if max(raw_w, raw_h) > max(current_img.size):
                    from picasa_py.ini.parser import PicasaIniParser
                    ini_p = folder / ".picasa.ini"
                    if not ini_p.exists():
                        alt_p = folder / "Picasa.ini"
                        if alt_p.exists():
                            ini_p = alt_p
                    if ini_p.exists():
                        doc_check = PicasaIniParser.parse_file(ini_p)
                        sec_check = doc_check.get_section(target_p.name)
                        if sec_check and any(
                            sec_check.get(k)
                            for k in ("filters", "crop", "rotate", "tilt", "text", "autolight", "backlight", "colorfix", "redeye", "retouch")
                        ):
                            full_rendered = PicasaImageProcessor.load_transformed_image(
                                target_path, max_size=0, parsed_ini=doc_check
                            )
                            if full_rendered is not None:
                                img_to_save = full_rendered
            except Exception:
                pass

            save_kwargs: dict = {}
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile

            ext = target_p.suffix.lower()
            if ext in (".jpg", ".jpeg"):
                img_to_save.convert("RGB").save(target_path, format="JPEG", quality=95, **save_kwargs)
            elif ext == ".png":
                img_to_save.save(target_path, format="PNG", **save_kwargs)
            else:
                img_to_save.save(target_path, **save_kwargs)

            # Ref: picasa3.exe @ 0x00429CA0, 0x004548B1, 0x004851C3, 0x0098B6E0 :
            # backuphash est le XOR des quatre mots 16 bits du double IEEE-754 de la date OLE Automation courante
            import struct
            from datetime import datetime
            from picasa_py.scanner.scanner import datetime_to_ole
            try:
                ole_now = datetime_to_ole(datetime.now())
                w0, w1, w2, w3 = struct.unpack("<4H", struct.pack("<d", ole_now))
                b_hash = ((w0 ^ w1 ^ w2 ^ w3) & 0xFFFF) or 1
            except Exception:
                b_hash = 1

            def _clear_baked_edits(doc, fname: str) -> None:
                """
                FR: Nettoie les clés de retouches non-destructives désormais gravées dans les pixels
                    et enregistre `backuphash` comme `picasa3.exe` (`0x00456A15`).
                EN: Clears non-destructive edit keys that have been baked into pixels
                    and records `backuphash` like `picasa3.exe` (`0x00456A15`).
                """
                doc.set_crop(fname, None)
                doc.set_rotate(fname, 0)
                doc.set_tilt(fname, None)
                doc.set_text(fname, None)
                sec = doc.get_or_create_section(fname)
                for k in ("filters", "crop", "rotate", "tilt", "text", "textactive", "backlight", "autolight", "colorfix", "redeye", "retouch"):
                    sec.remove(k)
                sec.set("backuphash", str(b_hash))

            self._update_ini(target_path, _clear_baked_edits)
            self._active_crop_rect = None
            self._active_rotate = 0
            self._active_tilt = 0.0
            self.canvas.set_active_transform(None, 0.0, 0)

            self._orig_backup_path = str(backup_file)
            if self._original_pil_img is None:
                self._original_pil_img = current_img.copy()
            if self.canvas.view_mode == "A_A":
                orig_pix = self._pil_to_pixmap(self._original_pil_img)
                self.canvas.set_original_pixmap(orig_pix)

            # FR : Mettre à jour ft2, file_size, width, height, originfast et revertable dans db3/
            # avant de régénérer les vignettes (pour que compute_thumb_checksum @ 0x006B99F0 soit exact)
            # EN: Update ft2, file_size, width, height, originfast, and revertable in db3/
            # before regenerating thumbnails (so compute_thumb_checksum @ 0x006B99F0 is exact)
            if self.db is not None and os.path.exists(target_path):
                try:
                    from picasa_py.scanner.scanner import file_filetimes, compute_originfast_hash
                    rec_idx = self.db.find_photo_index(target_path) if hasattr(self.db, "find_photo_index") else None
                    if rec_idx is not None and self.db.thumbindex is not None and 0 <= rec_idx < len(self.db.thumbindex.records):
                        _, ft2_new, fsize_new = file_filetimes(Path(target_path))
                        rec = self.db.thumbindex.records[rec_idx]
                        rec.ft2 = ft2_new
                        rec.size = fsize_new
                        rec.file_size = fsize_new
                        self.db.thumbindex.dirty = True
                        for col_n, col_v in (
                            ("imagedata_width", int(current_img.width)),
                            ("imagedata_height", int(current_img.height)),
                            ("imagedata_originfast", compute_originfast_hash(Path(target_path))),
                            ("imagedata_revertable", 1),
                        ):
                            pmp_c = self.db.pmps.get(col_n)
                            if pmp_c is not None and rec_idx < len(pmp_c.records):
                                pmp_c.records[rec_idx] = col_v
                                pmp_c.dirty = True
                except Exception:
                    pass

            self._sync_current_thumbnails_to_db(current_img)
            self.photo_edited.emit(target_path)
            return True
        except Exception:
            return False

    def save_current_photo_as(self, output_path: str) -> bool:
        """
        FR: Enregistre l'image active vers un nouvel emplacement en pleine résolution avec métadonnées EXIF/ICC (ID_FILE_SAVEAS).
        EN: Saves the active image to a new file path at full resolution with EXIF/ICC metadata (ID_FILE_SAVEAS).
        """
        if not self._history or self._history_idx < 0:
            return False
        try:
            current_img = self._history[self._history_idx]
            img_to_save = current_img
            exif_bytes = None
            icc_profile = None
            target_path = getattr(self, "_current_photo_path", None)
            if target_path and os.path.exists(target_path):
                try:
                    with Image.open(target_path) as meta_im:
                        raw_w, raw_h = meta_im.size
                        icc_profile = meta_im.info.get("icc_profile")
                        raw_exif = meta_im.getexif()
                        if raw_exif:
                            if 0x0112 in raw_exif:
                                raw_exif[0x0112] = 1
                            exif_bytes = raw_exif.tobytes()
                    if max(raw_w, raw_h) > max(current_img.size):
                        full_rendered = PicasaImageProcessor.load_transformed_image(target_path, max_size=0)
                        if full_rendered is not None:
                            img_to_save = full_rendered
                except Exception:
                    pass
            save_kwargs: dict = {}
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile
            ext = Path(output_path).suffix.lower()
            if ext in (".jpg", ".jpeg"):
                img_to_save.convert("RGB").save(output_path, format="JPEG", quality=95, **save_kwargs)
            elif ext == ".png":
                img_to_save.save(output_path, format="PNG", **save_kwargs)
            else:
                img_to_save.save(output_path, **save_kwargs)
            return True
        except Exception:
            return False

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs PicasaStyle à toute la vue One-Up / Éditeur.
        EN: Dynamically applies the PicasaStyle color theme to the entire One-Up / Editor view.
        """
        style = style or PicasaStyle.instance()
        self.style = style
        bar_bg = style.tray_bgcolor.name()
        btn_start = style.tray_grad_start.name() if style.is_dark else style.topbar_btn_bg_start.name()
        btn_end = style.tray_grad_end.name() if style.is_dark else style.topbar_btn_bg_end.name()
        btn_border = "#43474F" if style.is_dark else style.topbar_btn_border.name()
        txt_col = style.tray_text_color.name()
        border_col = "#141517" if style.is_dark else style.topbar_border_color.name()
        input_bg = "#262930" if style.is_dark else "#FFFFFF"
        accent = style.accent_color.name()

        if hasattr(self, "edit_panel") and self.edit_panel:
            self.edit_panel.apply_style(style)
        if hasattr(self, "canvas") and self.canvas:
            self.canvas.apply_style(style)
        if hasattr(self, "filmstrip") and self.filmstrip:
            self.filmstrip.apply_style(style)
        if hasattr(self, "right_drawer") and self.right_drawer:
            self.right_drawer.apply_style(style)
        if hasattr(self, "video_player") and self.video_player and hasattr(self.video_player, "apply_style"):
            self.video_player.apply_style(style)
        if hasattr(self, "btn_star"):
            self.update_star_button(getattr(self, "_is_starred", False))
        if hasattr(self, "right_splitter") and self.right_splitter:
            self.right_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {style.splitter_color.name()}; }}")

        if hasattr(self, "viewer_top_bar") and self.viewer_top_bar:
            self.viewer_top_bar.setStyleSheet(f"""
                QWidget {{
                    background-color: {bar_bg};
                    border-bottom: 1px solid {border_col};
                }}
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {btn_start}, stop:1 {btn_end});
                    color: {txt_col};
                    border: 1px solid {btn_border};
                    border-radius: 3px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border-color: {accent};
                }}
                QPushButton:checked {{
                    background-color: {accent};
                    color: #FFFFFF;
                    border: 1px solid {accent};
                }}
                QLabel {{
                    color: {txt_col};
                    font-size: 11px;
                }}
            """)
        if hasattr(self, "lbl_top_info") and self.lbl_top_info:
            self.lbl_top_info.setStyleSheet(f"color: {txt_col}; font-weight: bold; padding-left: 4px; border: none;")

        if hasattr(self, "caption_bar") and self.caption_bar:
            self.caption_bar.setStyleSheet(f"""
                QWidget {{
                    background-color: {bar_bg};
                    border-top: 1px solid {border_col};
                }}
                QLineEdit {{
                    background-color: {input_bg};
                    color: {txt_col};
                    border: 1px solid {btn_border};
                    border-radius: 3px;
                    padding: 1px 10px;
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border: 1px solid {accent};
                }}
            """)

        if hasattr(self, "transport_bar") and self.transport_bar:
            self.transport_bar.setStyleSheet(f"""
                QWidget {{
                    background-color: {bar_bg};
                    border-top: 1px solid {border_col};
                }}
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {btn_start}, stop:1 {btn_end});
                    color: {txt_col};
                    border: 1px solid {btn_border};
                    border-radius: 3px;
                    padding: 3px 8px;
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
        FR: Met à jour les textes traduits de la vue One-Up / Éditeur et de ses sous-panneaux.
        EN: Updates translated texts of the One-Up / Editor view and its subpanels.
        """
        res = PicasaResourceManager.get()
        sbtn = res.get_xml_string("editpanel/sbutton", "Diaporama")
        if hasattr(self, "btn_top_slideshow"):
            self.btn_top_slideshow.setText(f"▶ {sbtn}")
        if hasattr(self, "caption_edit"):
            cap_hint = res.get_xml_string("editpanel/captionbutton", "Créer une légende !")
            self.caption_edit.setPlaceholderText(cap_hint)
        if hasattr(self, "btn_panel_people"):
            self.btn_panel_people.setText("")
            self.btn_panel_people.setToolTip(res.get_xml_string("thumbui/people_toggle.tooltip", "Afficher/masquer le panneau Personnes"))
        if hasattr(self, "btn_panel_places"):
            self.btn_panel_places.setText("")
            self.btn_panel_places.setToolTip(res.get_xml_string("thumbui/places_toggle.tooltip", "Afficher/Masquer le panneau Lieux"))
        if hasattr(self, "btn_panel_tags"):
            self.btn_panel_tags.setText("")
            self.btn_panel_tags.setToolTip(res.get_xml_string("thumbui/tags_toggle.tooltip", "Afficher/Masquer le panneau Tags"))
        if hasattr(self, "btn_panel_props"):
            self.btn_panel_props.setText("")
            self.btn_panel_props.setToolTip(res.get_xml_string("thumbui/properties_toggle.tooltip", "Afficher/Masquer le panneau Propriétés"))
        if hasattr(self, "btn_swap_2up_layout"):
            self.btn_swap_2up_layout.setToolTip(
                res.get_xml_string("editpanel/swap_2up_layout.tooltip", "Basculer entre l'affichage horizontal et l'affichage vertical")
            )
        if hasattr(self, "btn_swap_2up_focus"):
            self.btn_swap_2up_focus.setToolTip(
                res.get_xml_string("editpanel/swap_2up_focus.tooltip", "Modifier l'image sur laquelle porte la mise au point")
            )
        if hasattr(self, "edit_panel") and hasattr(self.edit_panel, "retranslate_ui"):
            self.edit_panel.retranslate_ui()
        if hasattr(self, "right_drawer") and hasattr(self.right_drawer, "retranslate_ui"):
            self.right_drawer.retranslate_ui()
        self._update_top_bar_info()


