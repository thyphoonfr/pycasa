"""
FR: Composant de grille virtuelle de vignettes haute performance pour PyCasa.
Utilise un rendu QPainter personnalisé avec disposition multi-albums et barre de défilement Picasa 3.

EN: High-Performance Virtual Thumbnail Grid Component for PyCasa.
Uses custom QPainter with multi-album section layouts and Picasa 3 custom scrollbar.

Ref: picasa3.exe @ runtime/constants.ui [Picasa2] alayout_*, thumbsel_*
Ref: picasa3.exe @ 0x00573767 (thumbui/albumscroll)
Ref: picasa3.exe @ 0x005DE8E0 (scrolling, scrollstart, scrollstop)
Ref: picasa3.exe @ 0x00C968A0 (albumheader)
Ref: AGENTS.md §4 ter (Fluidité de défilement, UI thread non bloqué)
"""

from __future__ import annotations
from collections import deque
import io
import math
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Deque, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image, ImageOps
Image.MAX_IMAGE_PIXELS = None
from PySide6.QtWidgets import QWidget, QMessageBox, QApplication
from PySide6.QtCore import Qt, QRect, QSize, Signal, QPoint, QThread, QObject, QMimeData, QUrl, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage, QImageReader,
    QMouseEvent, QWheelEvent, QPaintEvent, QResizeEvent, QPolygon, QContextMenuEvent,
    QKeyEvent, QDrag, QLinearGradient
)

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.album_scroll import PicasaAlbumScroll
from picasa_py.ui.context_menu import PicasaContextMenuBuilder
from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.face_manager import _face_overlap
from picasa_py.scanner.scanner import VIDEO_EXTENSIONS



def format_ole_date(ole_days: float) -> str:
    """
    FR: Convertit une date OLE Automation (jours depuis le 30/12/1899)
    en texte français lisible (ex. 'Juin 2024').
    EN: Converts an OLE Automation date (days since 1899-12-30)
    into a readable month/year string.
    Ref: picasa3.exe @ albumdata_date.pmp
    """
    if ole_days <= 0:
        return ""
    try:
        base = datetime(1899, 12, 30)
        dt = base + timedelta(days=ole_days)
        months_fr = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]
        return f"{months_fr[dt.month - 1].capitalize()} {dt.year}"
    except Exception:
        return ""


@dataclass
class ThumbnailItem:
    """
    FR: Représente un élément de vignette individuel dans la grille virtuelle (photo, vidéo ou visage).
    EN: Represents an individual thumbnail item in the virtual grid (photo, video, or face).
    """
    index: int           # Index dans thumbindex.db et thumbs_0.db
    path: str            # Chemin absolu du fichier image sur disque
    filename: str        # Nom du fichier (ex. IMG_001.jpg)
    folder: str          # Nom du dossier (ex. Vacances)
    folder_path: str     # Chemin complet du dossier (ex. C:\\Photos\\Vacances\\)
    starred: bool = False
    has_edits: bool = False
    has_backup: bool = False
    is_video: bool = False
    pixmap: Optional[QPixmap] = None
    face_pixmap: Optional[QPixmap] = None  # Cache de vignette recadrée sur le visage en mode face_zoom
    loading: bool = False
    face_rect: Optional[Any] = None        # Visage sans nom ou spécifique
    is_synthetic_unnamed: bool = False
    is_synthetic_suggestion: bool = False
    is_person_item: bool = False
    suggestion: Optional[Any] = None


@dataclass
class AlbumSection:
    """
    FR: Section d'album / dossier dans le flux de défilement continu.
    EN: Album / folder section in the continuous scrolling stream.
    Ref: picasa3.exe @ albumheader (album_title, folderbutton)
    Ref: picasa3.exe @ faceheaderpanel/face_zoom, picture_zoom, sug_filter, confirmsug
    """
    name: str
    folder_path: str
    date_str: str
    item_indices: List[int] = field(default_factory=list)  # Indices dans self.items
    y_start: int = 0
    height: int = 0
    is_person: bool = False
    is_album: bool = False
    is_search: bool = False
    is_unnamed: bool = False
    face_zoom: bool = True  # True: cadrage centré sur le visage, False: photo entière
    contact_id: Optional[str] = None
    album_token: Optional[str] = None
    suggestions: List[Any] = field(default_factory=list)
    unnamed_faces: List[Any] = field(default_factory=list)
    cluster_faces: Optional[List[Any]] = None
    only_suggestions: bool = False
    all_person_indices: List[int] = field(default_factory=list)
    suggestion_item_indices: List[int] = field(default_factory=list)


class ViewportThumbWorker:
    """
    FR: Worker d'arrière-plan régénérant les miniatures haute qualité des photos retouchées
    visibles dans le viewport selon une file LIFO bornée, sans jamais bloquer `paintEvent`.
    EN: Background worker regenerating high-quality thumbnails for edited photos visible in
    the viewport using a bounded LIFO queue, without ever blocking `paintEvent`.
    Ref: picasa3.exe @ 0x007301F0, 0x00730320 (CThumbCache & Viewport Throttle)
    """
    def __init__(self, max_pending: int = 96) -> None:
        """
        FR: Initialise la file LIFO bornée aux éléments visibles et le thread démon d'arrière-plan.
        EN: Initializes the viewport-bounded LIFO queue and the background daemon thread.
        """
        self.max_pending = max_pending
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._pending_lifo: List[Tuple[int, int, str, bool, Any, bool, Any, Optional[str], int]] = []
        self._in_flight: Set[int] = set()
        self._failed_items: Set[int] = set()
        self.completed: Deque[Tuple[int, int, QImage, Any]] = deque()
        self._thread: Optional[threading.Thread] = None

    def schedule(
        self,
        item_idx: int,
        db_idx: int,
        path: str,
        is_backup_only: bool = False,
        db: Optional[Any] = None,
        db_fast: bool = False,
        is_face: bool = False,
        face_rect: Optional[Any] = None,
        contact_id: Optional[str] = None,
        avatar_size: int = 140,
    ) -> None:
        """
        FR: Planifie la régénération asynchrone d'une vignette ou d'un avatar de visage visible en tête de la pile LIFO.
        EN: Schedules asynchronous regeneration of a visible thumbnail or face avatar at the top of the LIFO stack.
        Ref: picasa3.exe @ 0x00414C90 (CThumbMaker LIFO Queue), 0x007301F0
        """
        if not path and db_idx < 0:
            return
        queue_key = (-item_idx - 1) if is_face else item_idx
        with self._cond:
            if queue_key in self._in_flight or queue_key in self._failed_items:
                return
            self._pending_lifo = [t for t in self._pending_lifo if t[0] != queue_key]
            self._pending_lifo.append(
                (queue_key, db_idx, path, is_backup_only, db, db_fast, face_rect, contact_id, avatar_size)
            )
            if len(self._pending_lifo) > self.max_pending:
                self._pending_lifo = self._pending_lifo[-self.max_pending :]
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run_loop, name="ViewportThumbWorker", daemon=True)
                self._thread.start()
            self._cond.notify()

    def pop_completed(self) -> List[Tuple[int, int, QImage, Any]]:
        """
        FR: Extrait et retourne de manière atomique toutes les miniatures terminées en attente d'intégration UI.
        EN: Atomically pops and returns all completed thumbnails awaiting UI integration.
        """
        with self._cond:
            if not self.completed:
                return []
            res = list(self.completed)
            self.completed.clear()
            return res

    def has_pending(self) -> bool:
        """
        FR: Indique s'il reste des miniatures en cours de calcul ou en attente d'intégration.
        EN: Indicates whether any thumbnails are still being processed or awaiting integration.
        """
        with self._cond:
            return bool(self._pending_lifo or self._in_flight or self.completed)

    def clear(self) -> None:
        """
        FR: Vide la file d'attente et les résultats en attente lors d'un rechargement de base.
        EN: Clears the pending queue and completed results when reloading the database.
        """
        with self._cond:
            self._pending_lifo.clear()
            self._in_flight.clear()
            self._failed_items.clear()
            self.completed.clear()

    def _run_loop(self) -> None:
        """
        FR: Boucle de traitement d'arrière-plan qui décode les miniatures DB, recadre les avatars de visages
        ou applique les filtres PIL hors du thread GUI avec priorité OS réduite.
        EN: Background processing loop that decodes DB thumbnails, crops face avatars,
        or applies PIL filters off the GUI thread at lowered OS thread priority.
        Ref: picasa3.exe @ 0x00414C90 (CThumbMaker), 0x00415790 (SetThreadPriority), 0x007301F0
        """
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), -1)
            except Exception:
                pass

        while True:
            with self._cond:
                if not self._pending_lifo:
                    self._cond.wait(timeout=2.0)
                    if not self._pending_lifo:
                        return
                queue_key, db_idx, path, is_backup_only, db_ref, db_fast, face_rect, contact_id, avatar_size = self._pending_lifo.pop()
                self._in_flight.add(queue_key)

            pil_img = None
            qimg: Optional[QImage] = None
            try:
                if queue_key < 0:
                    # Décodage et recadrage d'un avatar de visage (Personnes / Visages sans nom) hors thread GUI
                    if db_ref is not None and db_idx >= 0 and db_ref.is_face_record(db_idx):
                        raw_thumb = (
                            db_ref.get_thumbnail(db_idx, size="large")
                            or db_ref.get_thumbnail(db_idx, size="small")
                        )
                        if raw_thumb:
                            img = QImage.fromData(raw_thumb)
                            if not img.isNull():
                                qimg = img.copy()

                    if qimg is None:
                        target_fr = face_rect
                        if target_fr is None and db_ref is not None and getattr(db_ref, "face_manager", None) is not None and db_idx >= 0:
                            faces = db_ref.face_manager.get_faces_for_photo(db_idx)
                            if faces:
                                if contact_id:
                                    for f in faces:
                                        if f.contact_id == contact_id:
                                            target_fr = f
                                            break
                                if target_fr is None:
                                    target_fr = faces[0]

                        if target_fr is not None:
                            src_pil: Optional[Image.Image] = None
                            if db_ref is not None and db_idx >= 0:
                                raw_b = (
                                    db_ref.get_thumbnail(db_idx, size="preview")
                                    or db_ref.get_thumbnail(db_idx, size="large")
                                )
                                if raw_b:
                                    try:
                                        with Image.open(io.BytesIO(raw_b)) as im:
                                            src_pil = im.convert("RGB")
                                    except Exception:
                                        src_pil = None
                            if src_pil is None and path and os.path.exists(path):
                                from picasa_py.ui.image_processor import PicasaImageProcessor
                                src_pil = PicasaImageProcessor.load_transformed_image(path, max_size=800)

                            if src_pil is not None:
                                w, h = src_pil.size
                                fx, fy, fw, fh = target_fr.to_pixel_rect(w, h)
                                side = max(fw, fh)
                                cx, cy = fx + fw / 2.0, fy + fh / 2.0
                                x1, y1, x2, y2 = cx - side / 2.0, cy - side / 2.0, cx + side / 2.0, cy + side / 2.0
                                if x1 < 0.0:
                                    x2 = min(float(w), x2 - x1)
                                    x1 = 0.0
                                if y1 < 0.0:
                                    y2 = min(float(h), y2 - y1)
                                    y1 = 0.0
                                if x2 > float(w):
                                    x1 = max(0.0, x1 - (x2 - float(w)))
                                    x2 = float(w)
                                if y2 > float(h):
                                    y1 = max(0.0, y1 - (y2 - float(h)))
                                    y2 = float(h)
                                ix1 = max(0, int(round(x1)))
                                iy1 = max(0, int(round(y1)))
                                ix2 = max(ix1 + 1, min(w, int(round(x2))))
                                iy2 = max(iy1 + 1, min(h, int(round(y2))))
                                av_sz = max(64, int(avatar_size))
                                crop_im = src_pil.crop((ix1, iy1, ix2, iy2)).resize((av_sz, av_sz), Image.Resampling.BILINEAR).convert("RGB")
                                raw = crop_im.tobytes("raw", "RGB")
                                qimg = QImage(raw, av_sz, av_sz, av_sz * 3, QImage.Format.Format_RGB888).copy()
                else:
                    # 1. Décodage rapide depuis le conteneur CBlockFile en mémoire si demandé (hors thread GUI)
                    if db_fast and db_ref is not None and db_idx >= 0 and not is_backup_only:
                        raw_bytes = db_ref.get_thumbnail(db_idx)
                        if raw_bytes:
                            img = QImage.fromData(raw_bytes)
                            if not img.isNull():
                                qimg = img.copy()

                    # 2. Repli ou application des retouches sur le fichier disque
                    if qimg is None and path and os.path.exists(path):
                        if is_backup_only or db_fast:
                            reader = QImageReader(path)
                            reader.setAutoTransform(True)
                            orig_sz = reader.size()
                            if orig_sz.isValid() and orig_sz.width() > 0 and orig_sz.height() > 0:
                                scale = min(256.0 / orig_sz.width(), 256.0 / orig_sz.height(), 1.0)
                                target_sz = QSize(max(1, int(orig_sz.width() * scale)), max(1, int(orig_sz.height() * scale)))
                                reader.setScaledSize(target_sz)
                            img = reader.read()
                            if not img.isNull():
                                qimg = img
                        else:
                            from picasa_py.ui.image_processor import PicasaImageProcessor
                            pil_img = PicasaImageProcessor.load_transformed_image(path, max_size=288)
                            if pil_img is not None:
                                rgb_im = pil_img.convert("RGB")
                                w, h = rgb_im.size
                                raw = rgb_im.tobytes("raw", "RGB")
                                qimg = QImage(raw, w, h, w * 3, QImage.Format.Format_RGB888).copy()
                            else:
                                reader = QImageReader(path)
                                reader.setAutoTransform(True)
                                orig_sz = reader.size()
                                if orig_sz.isValid() and orig_sz.width() > 0 and orig_sz.height() > 0:
                                    scale = min(256.0 / orig_sz.width(), 256.0 / orig_sz.height(), 1.0)
                                    target_sz = QSize(max(1, int(orig_sz.width() * scale)), max(1, int(orig_sz.height() * scale)))
                                    reader.setScaledSize(target_sz)
                                img = reader.read()
                                if not img.isNull():
                                    qimg = img
            except Exception:
                qimg = None

            with self._cond:
                self._in_flight.discard(queue_key)
                if qimg is not None and not qimg.isNull():
                    self.completed.append((queue_key, db_idx, qimg, pil_img))
                else:
                    self._failed_items.add(queue_key)
            time.sleep(0.0005)


class FaceClusterWorker(QThread):
    """
    FR: Worker d'arrière-plan calculant les regroupements de visages sans bloquer l'UI.
    EN: Background worker computing face clusters without blocking the UI thread.
    Ref: picasa3.exe @ CAlbumLabel::LoadingGrouped (0x00881CC0), 0x00415790, 0x005E4AC0, AGENTS.md §4 ter
    """
    progress = Signal(int, int)
    finished = Signal(list)

    def __init__(self, face_manager, threshold: float = 0.65, parent: Optional[QObject] = None):
        """
        FR: Initialise le worker de regroupement des visages avec le seuil de similarité.
        EN: Initializes the face clustering worker with the similarity threshold.
        """
        super().__init__(parent)
        self.face_manager = face_manager
        self.threshold = threshold

    def run(self) -> None:
        """
        FR: Exécute l'algorithme de regroupement des visages sans nom à priorité OS réduite et émet la progression.
        EN: Runs the unnamed face clustering algorithm at lowered OS thread priority and emits progress updates.
        Ref: picasa3.exe @ 0x00415790, 0x005E4AC0
        """
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), -1)
            except Exception:
                pass
        try:
            def on_prog(cur, total):
                """
                FR: Relaye l'avancement du regroupement vers le signal progress.
                EN: Relays clustering progress to the progress signal.
                """
                self.progress.emit(cur, total)

            clusters = self.face_manager.cluster_unnamed_faces(
                threshold=self.threshold, progress_callback=on_prog
            )
            self.finished.emit(clusters)
        except Exception:
            self.finished.emit([])


class PicasaThumbnailView(QWidget):
    """
    FR: Grille virtuelle de vignettes multi-dossiers haute performance avec rendu QPainter
    et barre de défilement temporelle personnalisée (AVAlbumScroll).
    EN: High-performance multi-folder virtual thumbnail grid with custom QPainter rendering
    and custom timeline scrollbar (AVAlbumScroll).
    Ref: picasa3.exe @ MultiAlbumScroll, UseMultiAlbumScrollFix
    """
    selection_changed = Signal(list)
    item_double_clicked = Signal(int)
    slideshow_requested = Signal(list)  # Liste des chemins de photos
    collage_section_requested = Signal(list)  # Liste des chemins de photos pour Montage (headerpanel/create_collage)
    movie_section_requested = Signal(list)  # Liste des chemins de photos pour Film (headerpanel/create_movie)
    save_section_requested = Signal(str)  # Chemin du dossier pour Enregistrer (headerpanel/save_edits)
    active_folder_changed = Signal(str)  # Émis lors du défilement multi-albums pour synchroniser l'arborescence
    star_toggled = Signal(str, bool)  # file_path, is_starred (Ref: ID_PICTURE_STAR, star=yes)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise la grille virtuelle de vignettes, le cache d'images et la barre de défilement Picasa.
        EN: Initializes the virtual thumbnail grid, image cache, and Picasa custom scrollbar.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.db: Optional[PicasaDatabase] = None
        self.items: List[ThumbnailItem] = []
        self.sections: List[AlbumSection] = []
        self.visible_sections: List[AlbumSection] = []
        self.filtered_indices: List[int] = []  # Tous les éléments actuellement filtrés
        self.selected_indices: Set[int] = set()
        self.anchor_index: Optional[int] = None
        self.focus_index: Optional[int] = None

        # État de survol des en-têtes (sticky ou normal) et des vignettes
        self._hovered_header_btn: Optional[Tuple[str, int]] = None  # ("slideshow" | "collage" | "movie" | "star" | "header", sec_idx)
        self._hovered_item_idx: Optional[int] = None
        self._hovered_sug_btn: Optional[Tuple[int, str]] = None  # (item_idx, "ok" | "no")

        # Sélection rectangle élastique (Rubber-band marquee) et glisser-déposer (Drag & Drop)
        self._rubber_band_origin: Optional[QPoint] = None
        self._rubber_band_rect: Optional[QRect] = None
        self._rubber_band_base_selection: Set[int] = set()
        self._drag_start_pos: Optional[QPoint] = None
        self._dragging_item_idx: Optional[int] = None
        self._deferred_single_select_idx: Optional[int] = None

        # Régulation (35 ms) de selection_changed pendant le rectangle élastique
        # Ref: picasa3.exe @ 0x007301F0 (Viewport & Selection Throttle)
        self._pending_selection_emit: bool = False
        self._selection_emit_timer = QTimer(self)
        self._selection_emit_timer.setSingleShot(True)
        self._selection_emit_timer.setInterval(35)
        self._selection_emit_timer.timeout.connect(self._emit_throttled_selection)

        # Dimensions dynamiques des vignettes
        self.thumb_base_size: int = 140
        self.scroll_y: int = 0
        self.total_content_height: int = 0

        # Cache de vignettes en mémoire et cache de QPixmap déjà redimensionnées au viewport
        # Ref: picasa3.exe @ 0x007301F0, 0x00730320 (CThumbCache & Viewport Throttle)
        self._pixmap_cache: Dict[int, QPixmap] = {}
        self._db_pixmap_cache: Dict[int, QPixmap] = {}
        self._scaled_pixmap_cache: Dict[Tuple[int, int, int], QPixmap] = {}
        self._folder_backups_cache: Dict[str, Set[str]] = {}
        self._synced_db_len: int = 0
        self._cache_limit: int = 1000
        self._in_paint_event: bool = False
        self._paint_start_ts: float = 0.0
        self._paint_sync_decodes: int = 0

        # Worker asynchrone de régénération des vignettes retouchées visibles
        self._thumb_worker = ViewportThumbWorker(max_pending=96)
        self._thumb_flush_timer = QTimer(self)
        self._thumb_flush_timer.setInterval(16)
        self._thumb_flush_timer.timeout.connect(self._flush_async_thumbnails)

        # En-tête globale / filtre actif
        self.current_folder_filter: Optional[str] = None
        self._unfiltered_special_sections: List[AlbumSection] = []
        self.quick_filter_starred: bool = False
        self.quick_filter_faces: bool = False
        self.quick_filter_videos: bool = False
        self.quick_filter_geo: bool = False

        # Zoom fluide des vignettes (rendu direct GPU pendant le glissement, SmoothTransformation au repos)
        self._is_zooming_thumbs: bool = False
        self._zoom_settle_timer = QTimer(self)
        self._zoom_settle_timer.setSingleShot(True)
        self._zoom_settle_timer.setInterval(120)
        self._zoom_settle_timer.timeout.connect(self._on_zoom_settled)

        # Barre de défilement personnalisée Picasa 3 (AVAlbumScroll)
        self.scrollbar = PicasaAlbumScroll(style=self.style, parent=self)
        self.scrollbar.set_info_provider(self.get_album_info_at_scroll)
        self.scrollbar.value_changed.connect(self._on_scroll)
        self.scrollbar.jump_prev_album.connect(self._on_jump_prev_album)
        self.scrollbar.jump_next_album.connect(self._on_jump_next_album)

    def _emit_throttled_selection(self) -> None:
        """
        FR: Émet le signal `selection_changed` régulé pendant le tracé d'un rectangle élastique.
        EN: Emits the throttled `selection_changed` signal during rubber-band marquee selection.
        Ref: picasa3.exe @ 0x007301F0 (Viewport & Selection Throttle)
        """
        if self._pending_selection_emit:
            self._pending_selection_emit = False
            self.selection_changed.emit(sorted(self.selected_indices))

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs à la grille de vignettes et à la barre de défilement.
        EN: Dynamically applies the color theme to the thumbnail grid and custom scrollbar.
        """
        style = style or PicasaStyle.instance()
        self.style = style
        if hasattr(self, "scrollbar") and self.scrollbar:
            self.scrollbar.style = style
            self.scrollbar.update()
        self.update()

    def retranslate_ui(self) -> None:
        """
        FR: Force le redessin des en-têtes d'albums et de personnes lors d'un changement de langue.
        EN: Forces repainting of album and person headers when the active language changes.
        """
        self.update()

    def _extract_album_meta_map(self, db: PicasaDatabase) -> Dict[str, Tuple[str, str]]:
        """
        FR: Construit le dictionnaire `norm_folder_path -> (nom_album, date_str)` depuis les tables `albumdata_*`.
        EN: Builds the `norm_folder_path -> (album_name, date_str)` dictionary from `albumdata_*` tables.
        """
        album_meta: Dict[str, Tuple[str, str]] = {}
        if "albumdata_filename" in db.pmps and "albumdata_name" in db.pmps:
            fn_pmp = db.pmps["albumdata_filename"].records
            name_pmp = db.pmps["albumdata_name"].records
            date_pmp = db.pmps.get("albumdata_date", None)
            cat_pmp = db.pmps.get("albumdata_category", None)

            for idx, fn in enumerate(fn_pmp):
                if cat_pmp and idx < len(cat_pmp.records) and cat_pmp.records[idx] == 6:
                    continue
                norm = fn.replace("\\", "/").rstrip("/").lower()
                name = name_pmp[idx] if idx < len(name_pmp) and name_pmp[idx] else ""
                ole_d = date_pmp.records[idx] if date_pmp and idx < len(date_pmp.records) else 0.0
                date_str = format_ole_date(ole_d)
                album_meta[norm] = (name, date_str)
        return album_meta

    def _get_folder_ini_meta_dict(
        self,
        db: PicasaDatabase,
        fp: str,
        folder_ini_meta_cache: Dict[str, Tuple[Set[str], Set[str], Set[str]]],
    ) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        FR: Récupère en une seule passe par dossier les ensembles de fichiers favoris (star=yes),
        retouchés (rotate/tilt/crop/filters/text) et sauvegardés (.picasaoriginals / backuphash),
        en réutilisant le cache `_folder_backups_cache` pour éviter les appels `os.listdir` répétés.
        EN: Retrieves in a single pass per folder the sets of starred (star=yes),
        edited (rotate/tilt/crop/filters/text), and backed-up (.picasaoriginals / backuphash) files,
        reusing `_folder_backups_cache` to avoid repeated `os.listdir` calls.
        """
        norm_k = fp.replace("\\", "/").rstrip("/").lower()
        if norm_k not in folder_ini_meta_cache:
            starred_set: Set[str] = set()
            edited_set: Set[str] = set()
            backup_set: Set[str] = set()
            ini_p = os.path.join(fp, ".picasa.ini")
            doc = db.get_parsed_ini(ini_p) if hasattr(db, "get_parsed_ini") else None
            if not doc:
                alt = os.path.join(fp, "Picasa.ini")
                doc = db.get_parsed_ini(alt) if hasattr(db, "get_parsed_ini") else None
            if doc:
                for sec in doc.sections:
                    sec_low = sec.name.lower()
                    if sec.get("star", "").lower() == "yes":
                        starred_set.add(sec_low)
                    if (
                        sec.get("rotate", "")
                        or sec.get("tilt", "")
                        or sec.get("crop", "")
                        or sec.get("filters", "")
                        or sec.get("text", "")
                    ):
                        edited_set.add(sec_low)
                    if sec.get("backuphash", ""):
                        backup_set.add(sec_low)
            if norm_k in self._folder_backups_cache:
                backup_set.update(self._folder_backups_cache[norm_k])
            else:
                orig_dir = os.path.join(fp, ".picasaoriginals")
                if os.path.isdir(orig_dir):
                    try:
                        orig_files = {fn.lower() for fn in os.listdir(orig_dir)}
                        backup_set.update(orig_files)
                        self._folder_backups_cache[norm_k] = orig_files
                    except Exception:
                        self._folder_backups_cache[norm_k] = set()
                else:
                    self._folder_backups_cache[norm_k] = set()
            folder_ini_meta_cache[norm_k] = (starred_set, edited_set, backup_set)
        return folder_ini_meta_cache[norm_k]

    def set_database(self, db: PicasaDatabase, preserve_view_state: bool = False) -> None:
        """
        FR: Charge les entrées de la base de données Picasa et construit les sections d'albums,
        tout en préservant les `QPixmap` déjà décodées en mémoire (`_db_pixmap_cache`) afin d'éviter
        tout re-décodage synchrone des vignettes sur le thread GUI.
        EN: Loads Picasa database entries and builds continuous album sections while preserving
        already-decoded `QPixmap` objects in memory (`_db_pixmap_cache`) to avoid synchronous
        thumbnail re-decoding on the GUI thread.
        """
        same_db = (self.db is db)
        if same_db and self.items and self._pixmap_cache:
            for it_idx, pm in list(self._pixmap_cache.items()):
                if 0 <= it_idx < len(self.items) and pm and not pm.isNull():
                    db_i = self.items[it_idx].index
                    if db_i >= 0:
                        self._db_pixmap_cache[db_i] = pm
        elif not same_db:
            self._db_pixmap_cache.clear()
            self._folder_backups_cache.clear()

        saved_scroll = self.scroll_y if preserve_view_state else 0
        saved_filter = self.current_folder_filter if preserve_view_state else None
        saved_sel_db = (
            {self.items[idx].index for idx in self.selected_indices if 0 <= idx < len(self.items)}
            if preserve_view_state
            else set()
        )

        self.db = db
        self.items.clear()
        self.sections.clear()
        self.selected_indices.clear()
        self.anchor_index = None
        self._pixmap_cache.clear()
        self._scaled_pixmap_cache.clear()
        if not same_db:
            self._thumb_worker.clear()

        # 1. Cartographier les répertoires depuis thumbindex.db (type == 1)
        folders = {i: r.path for i, r in enumerate(db.index) if r.type == 1}

        # 2. Cartographier les métadonnées d'albums (albumdata_name, albumdata_date, albumdata_filename)
        album_meta = self._extract_album_meta_map(db)

        # 3. Filtrer UNIQUEMENT les fichiers média réels (JPG, BMP, PSD, TIFF, RAW, WEBP)
        # Lecture purement en RAM depuis les colonnes .pmp (Ref: picasa3.exe @ 0x004F6470, 0x0071D260)
        folder_items_map: Dict[str, List[int]] = {}
        folder_ini_meta_cache: Dict[str, Tuple[Set[str], Set[str], Set[str]]] = {}

        edited_recs = db.pmps["imagedata_edited"].records if "imagedata_edited" in db.pmps else None
        filters_recs = db.pmps["imagedata_filters"].records if "imagedata_filters" in db.pmps else None
        crop64_recs = db.pmps["imagedata_crop64"].records if "imagedata_crop64" in db.pmps else None
        rotate_recs = db.pmps["imagedata_rotate"].records if "imagedata_rotate" in db.pmps else None
        tilt_recs = db.pmps["imagedata_tilt"].records if "imagedata_tilt" in db.pmps else None
        text_recs = db.pmps["imagedata_textactive"].records if "imagedata_textactive" in db.pmps else None
        backup_recs = db.pmps["imagedata_backuphash"].records if "imagedata_backuphash" in db.pmps else None
        star_recs = db.pmps["imagedata_star"].records if "imagedata_star" in db.pmps else None
        has_pmp_meta = any(
            r is not None
            for r in (edited_recs, filters_recs, crop64_recs, rotate_recs, tilt_recs, text_recs, backup_recs)
        )
        starred_cache_raw = getattr(db, "_starred_cache", None)
        starred_norm_set: Set[str] = (
            {os.path.normcase(os.path.normpath(p)) for p in starred_cache_raw}
            if starred_cache_raw
            else set()
        )
        allow_disk_ini_fallback = (not has_pmp_meta) and len(db.index) <= 64

        for i, entry in enumerate(db.index):
            is_vid = (entry.type == 0x20) or (Path(entry.path).suffix.lower() in VIDEO_EXTENSIONS)
            if entry.type not in (2, 6, 7, 13, 18, 31, 0x20) and not is_vid:
                continue

            folder_path = folders.get(entry.parent_idx, "")
            folder_name = folder_path.replace("\\", "/").rstrip("/").split("/")[-1] if folder_path else "Photos"
            full_path = os.path.join(folder_path, entry.path) if folder_path else entry.path

            is_st = bool(star_recs and i < len(star_recs) and star_recs[i])
            if not is_st and starred_norm_set and full_path:
                is_st = os.path.normcase(os.path.normpath(full_path)) in starred_norm_set

            has_ed = bool(
                (edited_recs and i < len(edited_recs) and edited_recs[i])
                or (filters_recs and i < len(filters_recs) and filters_recs[i])
                or (crop64_recs and i < len(crop64_recs) and crop64_recs[i] not in (0, 0xFFFFFFFFFFFFFFFF))
                or (rotate_recs and i < len(rotate_recs) and rotate_recs[i])
                or (tilt_recs and i < len(tilt_recs) and abs(float(tilt_recs[i])) >= 0.01)
                or (text_recs and i < len(text_recs) and text_recs[i])
            )
            has_bk = bool(backup_recs and i < len(backup_recs) and backup_recs[i])

            if allow_disk_ini_fallback and folder_path:
                st_set, ed_set, bk_set = self._get_folder_ini_meta_dict(db, folder_path, folder_ini_meta_cache)
                fn_low = entry.path.lower()
                is_st = is_st or (fn_low in st_set)
                has_ed = has_ed or (fn_low in ed_set)
                has_bk = has_bk or (fn_low in bk_set)

            item = ThumbnailItem(
                index=i,
                path=full_path,
                filename=entry.path,
                folder=folder_name,
                folder_path=folder_path,
                starred=is_st,
                has_edits=has_ed,
                has_backup=has_bk,
                is_video=is_vid,
            )
            item_list_idx = len(self.items)
            self.items.append(item)
            if i in self._db_pixmap_cache:
                self._pixmap_cache[item_list_idx] = self._db_pixmap_cache[i]
            if preserve_view_state and i in saved_sel_db:
                self.selected_indices.add(item_list_idx)

            norm_fp = folder_path.replace("\\", "/").rstrip("/").lower()
            if norm_fp not in folder_items_map:
                folder_items_map[norm_fp] = []
            folder_items_map[norm_fp].append(item_list_idx)

        # 4. Construire les sections d'albums pour le défilement continu
        for norm_fp, item_indices in folder_items_map.items():
            first_item = self.items[item_indices[0]]
            meta = album_meta.get(norm_fp, ("", ""))
            sec_name = meta[0] if meta[0] else first_item.folder
            sec_date = meta[1]

            sec = AlbumSection(
                name=sec_name,
                folder_path=first_item.folder_path,
                date_str=sec_date,
                item_indices=item_indices,
            )
            self.sections.append(sec)

        self._synced_db_len = len(db.index)
        self.filter_by_folder(saved_filter)
        if preserve_view_state:
            if saved_sel_db:
                self.selection_changed.emit(sorted(self.selected_indices))
            if saved_scroll > 0:
                max_scroll = max(0, self.total_content_height - self.height())
                clamped_scroll = min(saved_scroll, max_scroll)
                self.scroll_y = clamped_scroll
                self.scrollbar.set_value(clamped_scroll)
                self.update()

    def sync_from_database_incremental(self, db: PicasaDatabase) -> bool:
        """
        FR: Ajoute de manière incrémentale les nouveaux enregistrements `db.index[self._synced_db_len:]`
        sans vider les caches de vignettes (`_pixmap_cache`, `_scaled_pixmap_cache`) ni réinitialiser
        le défilement ou la sélection active pendant un scan en arrière-plan.
        EN: Incrementally appends new `db.index[self._synced_db_len:]` records without clearing
        thumbnail caches (`_pixmap_cache`, `_scaled_pixmap_cache`) or resetting scroll/selection
        state during a background scan.
        Ref: picasa3.exe @ 0x00571850 (CThumbUI::NotifyPhotoAddedOrUpdated)
        """
        new_len = len(db.index)
        deleted_set = getattr(db, "_deleted_or_reset_indices", None)
        has_deleted_in_place = bool(deleted_set)
        if not has_deleted_in_place and self.db is db and self.items:
            for it in self.items:
                if (
                    not getattr(it, "is_synthetic_unnamed", False)
                    and not getattr(it, "is_person_item", False)
                    and 0 <= it.index < new_len
                ):
                    rec = db.index[it.index]
                    if rec.type == 0 or not rec.path:
                        has_deleted_in_place = True
                        break
        if has_deleted_in_place or self.db is not db or self._synced_db_len <= 0 or new_len < self._synced_db_len:
            if deleted_set is not None and hasattr(deleted_set, "clear"):
                deleted_set.clear()
            self.set_database(db, preserve_view_state=True)
            return True

        modified_set = getattr(db, "_modified_media_indices", None)
        if modified_set:
            mod_indices = set(modified_set)
            if hasattr(modified_set, "clear"):
                modified_set.clear()
            for item_list_idx, it in enumerate(self.items):
                if it.index in mod_indices:
                    self.invalidate_item(item_list_idx)

        if new_len == self._synced_db_len:
            return True

        # Si l'utilisateur est sur une vue synthétique (personne / sans nom / recherche / album),
        # mettre simplement à jour les sections de base en arrière-plan.
        album_meta = self._extract_album_meta_map(db)
        edited_recs = db.pmps["imagedata_edited"].records if "imagedata_edited" in db.pmps else None
        filters_recs = db.pmps["imagedata_filters"].records if "imagedata_filters" in db.pmps else None
        crop64_recs = db.pmps["imagedata_crop64"].records if "imagedata_crop64" in db.pmps else None
        rotate_recs = db.pmps["imagedata_rotate"].records if "imagedata_rotate" in db.pmps else None
        tilt_recs = db.pmps["imagedata_tilt"].records if "imagedata_tilt" in db.pmps else None
        text_recs = db.pmps["imagedata_textactive"].records if "imagedata_textactive" in db.pmps else None
        backup_recs = db.pmps["imagedata_backuphash"].records if "imagedata_backuphash" in db.pmps else None
        star_recs = db.pmps["imagedata_star"].records if "imagedata_star" in db.pmps else None
        starred_cache_raw = getattr(db, "_starred_cache", None)
        starred_norm_set: Set[str] = (
            {os.path.normcase(os.path.normpath(p)) for p in starred_cache_raw}
            if starred_cache_raw
            else set()
        )

        sec_by_norm_fp: Dict[str, AlbumSection] = {}
        for sec in self.sections:
            if not sec.is_person and not sec.is_album and not sec.is_search and not sec.is_unnamed:
                norm_fp = sec.folder_path.replace("\\", "/").rstrip("/").lower()
                sec_by_norm_fp[norm_fp] = sec

        added_any = False
        for i in range(self._synced_db_len, new_len):
            entry = db.index[i]
            is_vid = (entry.type == 0x20) or (Path(entry.path).suffix.lower() in VIDEO_EXTENSIONS)
            if entry.type not in (2, 6, 7, 13, 18, 31, 0x20) and not is_vid:
                continue

            parent_idx = entry.parent_idx
            folder_path = (
                db.index[parent_idx].path
                if (0 <= parent_idx < new_len and db.index[parent_idx].type == 1)
                else ""
            )
            folder_name = folder_path.replace("\\", "/").rstrip("/").split("/")[-1] if folder_path else "Photos"
            full_path = os.path.join(folder_path, entry.path) if folder_path else entry.path

            is_st = bool(star_recs and i < len(star_recs) and star_recs[i])
            if not is_st and starred_norm_set and full_path:
                is_st = os.path.normcase(os.path.normpath(full_path)) in starred_norm_set

            has_ed = bool(
                (edited_recs and i < len(edited_recs) and edited_recs[i])
                or (filters_recs and i < len(filters_recs) and filters_recs[i])
                or (crop64_recs and i < len(crop64_recs) and crop64_recs[i] not in (0, 0xFFFFFFFFFFFFFFFF))
                or (rotate_recs and i < len(rotate_recs) and rotate_recs[i])
                or (tilt_recs and i < len(tilt_recs) and abs(float(tilt_recs[i])) >= 0.01)
                or (text_recs and i < len(text_recs) and text_recs[i])
            )
            has_bk = bool(backup_recs and i < len(backup_recs) and backup_recs[i])

            item = ThumbnailItem(
                index=i,
                path=full_path,
                filename=entry.path,
                folder=folder_name,
                folder_path=folder_path,
                starred=is_st,
                has_edits=has_ed,
                has_backup=has_bk,
                is_video=is_vid,
            )
            item_list_idx = len(self.items)
            self.items.append(item)
            added_any = True

            norm_fp = folder_path.replace("\\", "/").rstrip("/").lower()
            sec = sec_by_norm_fp.get(norm_fp)
            if sec is None:
                meta = album_meta.get(norm_fp, ("", ""))
                sec_name = meta[0] if meta[0] else folder_name
                sec_date = meta[1]
                sec = AlbumSection(
                    name=sec_name,
                    folder_path=folder_path,
                    date_str=sec_date,
                    item_indices=[item_list_idx],
                )
                self.sections.append(sec)
                sec_by_norm_fp[norm_fp] = sec
            else:
                sec.item_indices.append(item_list_idx)

        self._synced_db_len = new_len
        if not added_any:
            return True

        # Rafraîchir visible_sections sans perdre scroll_y ni selected_indices
        if self.current_folder_filter is None or (
            not self.current_folder_filter.startswith("person:")
            and self.current_folder_filter != "unnamed_faces"
            and not self.current_folder_filter.startswith("album:")
            and not self.current_folder_filter.startswith("search:")
        ):
            self._apply_current_filters(reset_scroll=False)
        return True

    def filter_by_folder(self, folder_path: Optional[str]) -> None:
        """
        FR: Filtre les vignettes par dossier spécifique, ou affiche l'ensemble
        des albums en flux continu si None (comportement d'origine Picasa 3).
        EN: Filters thumbnails by a specific folder, or displays all albums in a
        continuous scrolling stream if None (authentic Picasa 3 behavior).
        """
        if folder_path is None or (not folder_path.startswith("person:") and folder_path != "unnamed_faces"):
            self.items = [it for it in self.items if not getattr(it, "is_synthetic_unnamed", False) and not getattr(it, "is_person_item", False)]
        self.current_folder_filter = folder_path
        self._apply_current_filters()

    def apply_quick_filters(
        self,
        filter_starred: Optional[bool] = None,
        filter_faces: Optional[bool] = None,
        filter_videos: Optional[bool] = None,
        filter_geo: Optional[bool] = None,
    ) -> None:
        """
        FR: Applique les filtres rapides de la barre supérieure (étoiles, visages, vidéos, lieux).
        EN: Applies top bar quick filters (starred, faces, videos, geotagged places).
        Ref: picasa3.exe @ 0x0088C3EC (Search & Filters)
        """
        if filter_starred is not None:
            self.quick_filter_starred = filter_starred
        if filter_faces is not None:
            self.quick_filter_faces = filter_faces
        if filter_videos is not None:
            self.quick_filter_videos = filter_videos
        if filter_geo is not None:
            self.quick_filter_geo = filter_geo
        self._apply_current_filters()

    def _is_item_geotagged(self, item: ThumbnailItem) -> bool:
        """
        FR: Vérifie si une photo possède des coordonnées GPS (dans imagedata_lat/long ou .picasa.ini geotag=).
        EN: Checks whether a photo has GPS coordinates (in imagedata_lat/long or .picasa.ini geotag=).
        Ref: picasa3.exe @ imagedata_lat.pmp, imagedata_long.pmp, GEOPANELTEXT_FR.XML
        """
        if self.db and item.index >= 0:
            lat_pmp = self.db.pmps.get("imagedata_lat")
            lon_pmp = self.db.pmps.get("imagedata_long")
            if lat_pmp and lon_pmp and item.index < len(lat_pmp.records) and item.index < len(lon_pmp.records):
                try:
                    lat_v = float(lat_pmp.records[item.index])
                    lon_v = float(lon_pmp.records[item.index])
                    if (lat_v != 0.0 or lon_v != 0.0) and abs(lat_v) <= 90.0 and abs(lon_v) <= 180.0:
                        return True
                except Exception:
                    pass
        if item.folder_path and item.filename:
            ini_p = os.path.join(item.folder_path, ".picasa.ini")
            doc = self.db.get_parsed_ini(ini_p) if (self.db and hasattr(self.db, "get_parsed_ini")) else None
            if doc:
                sec = doc.get_section(item.filename)
                if sec and sec.get("geotag", "").strip():
                    return True
        return False

    @staticmethod
    def _clone_special_sections(sections: List[AlbumSection]) -> List[AlbumSection]:
        """
        FR: Retourne une copie indépendante d'une liste de sections spéciales (recherche, album, personne, sans nom).
        EN: Returns an independent copy of a list of special sections (search, album, person, unnamed).
        """
        cloned: List[AlbumSection] = []
        for sec in sections:
            cloned.append(
                AlbumSection(
                    name=sec.name,
                    folder_path=sec.folder_path,
                    date_str=sec.date_str,
                    item_indices=list(sec.item_indices),
                    is_person=sec.is_person,
                    is_album=sec.is_album,
                    is_search=sec.is_search,
                    is_unnamed=sec.is_unnamed,
                    face_zoom=sec.face_zoom,
                    contact_id=sec.contact_id,
                    album_token=sec.album_token,
                    suggestions=sec.suggestions,
                    only_suggestions=sec.only_suggestions,
                    all_person_indices=list(sec.all_person_indices),
                    suggestion_item_indices=list(sec.suggestion_item_indices),
                    unnamed_faces=sec.unnamed_faces,
                    cluster_faces=sec.cluster_faces,
                )
            )
        return cloned

    def _apply_current_filters(self, reset_scroll: bool = True) -> None:
        """
        FR: Applique le filtre de dossier et les filtres rapides actifs (étoiles, visages, vidéos, géolocalisation).
        EN: Applies the active folder filter and quick filters (starred, faces, videos, geotagging).
        """
        if self.current_folder_filter and self.current_folder_filter.startswith("person:"):
            src_secs = (
                self._clone_special_sections(self._unfiltered_special_sections)
                if self._unfiltered_special_sections
                else self.visible_sections
            )
            base_sections = [sec for sec in src_secs if sec.is_person]
            if not base_sections and self.sections:
                base_sections = list(self.sections)
        elif self.current_folder_filter and self.current_folder_filter == "unnamed_faces":
            src_secs = (
                self._clone_special_sections(self._unfiltered_special_sections)
                if self._unfiltered_special_sections
                else self.visible_sections
            )
            base_sections = [sec for sec in src_secs if sec.is_unnamed]
        elif self.current_folder_filter and (
            self.current_folder_filter.startswith("album:")
            or self.current_folder_filter == "special:starred"
        ):
            src_secs = (
                self._clone_special_sections(self._unfiltered_special_sections)
                if self._unfiltered_special_sections
                else self.visible_sections
            )
            base_sections = [sec for sec in src_secs if sec.is_album]
        elif self.current_folder_filter and self.current_folder_filter.startswith("search:"):
            src_secs = (
                self._clone_special_sections(self._unfiltered_special_sections)
                if self._unfiltered_special_sections
                else self.visible_sections
            )
            base_sections = [sec for sec in src_secs if sec.is_search]
        elif self.current_folder_filter:
            norm_target = self.current_folder_filter.replace("\\", "/").rstrip("/").lower()
            base_sections = [
                sec for sec in self.sections
                if sec.folder_path.replace("\\", "/").rstrip("/").lower() == norm_target
            ]
        else:
            base_sections = list(self.sections)

        has_quick = (
            self.quick_filter_starred
            or self.quick_filter_faces
            or self.quick_filter_videos
            or self.quick_filter_geo
        )
        new_visible_sections = []
        self.filtered_indices = []

        for sec in base_sections:
            filtered_sec_indices = []
            for idx in sec.item_indices:
                item = self.items[idx]
                if self.quick_filter_starred and not item.starred:
                    continue
                if self.quick_filter_videos and not item.is_video:
                    continue
                if self.quick_filter_geo and not self._is_item_geotagged(item):
                    continue
                if self.quick_filter_faces:
                    if not self.db or not getattr(self.db, "face_manager", None):
                        continue
                    faces = self.db.face_manager.get_faces_for_photo(item.index)
                    if not faces:
                        continue
                    filtered_sec_indices.append(idx)
                else:
                    filtered_sec_indices.append(idx)

            if filtered_sec_indices or not has_quick:
                display_sec = AlbumSection(
                    name=sec.name,
                    folder_path=sec.folder_path,
                    date_str=sec.date_str,
                    item_indices=filtered_sec_indices,
                    is_person=sec.is_person,
                    is_album=sec.is_album,
                    is_search=sec.is_search,
                    is_unnamed=sec.is_unnamed,
                    face_zoom=sec.face_zoom,
                    contact_id=sec.contact_id,
                    album_token=sec.album_token,
                    suggestions=sec.suggestions,
                    only_suggestions=sec.only_suggestions,
                    all_person_indices=list(sec.all_person_indices),
                    suggestion_item_indices=list(sec.suggestion_item_indices),
                    unnamed_faces=sec.unnamed_faces,
                    cluster_faces=sec.cluster_faces,
                )
                new_visible_sections.append(display_sec)
                self.filtered_indices.extend(filtered_sec_indices)

        self.visible_sections = new_visible_sections
        if reset_scroll:
            self.selected_indices.clear()
            self.scroll_y = 0
            self.scrollbar.set_value(0)
        self._recompute_layout()
        if not reset_scroll and self.scroll_y > 0:
            max_scroll = max(0, self.total_content_height - self.height())
            clamped_scroll = min(self.scroll_y, max_scroll)
            self.scroll_y = clamped_scroll
            self.scrollbar.set_value(clamped_scroll)
        self.update()
        if reset_scroll:
            self.selection_changed.emit(list(self.selected_indices))

    def scroll_to_folder(self, folder_path: str) -> None:
        """
        FR: Défilement continu vers un dossier / album sans masquer les autres sections.
        L'ensemble des dossiers reste enchaîné de façon fluide au scroll vertical.
        EN: Smoothly scrolls to a folder / album without hiding other sections.
        All folders remain chained in a continuous vertical scrolling stream.
        Ref: picasa3.exe @ MultiAlbumScroll, CAlbumList::liststicky, CThumbUI::ShowAlbumSlice
        """
        if not folder_path:
            return

        # Rétablir l'ensemble des sections pour le flux continu si nécessaire
        if len(self.visible_sections) != len(self.sections) or self.current_folder_filter is not None:
            self.items = [it for it in self.items if not getattr(it, "is_synthetic_unnamed", False) and not getattr(it, "is_person_item", False)]
            self.current_folder_filter = None
            self._unfiltered_special_sections.clear()
            self.visible_sections = list(self.sections)
            self.filtered_indices = list(range(len(self.items)))
            self._recompute_layout()

        norm_target = folder_path.replace("\\", "/").rstrip("/").lower()
        target_y = None
        for sec in self.visible_sections:
            sec_norm = sec.folder_path.replace("\\", "/").rstrip("/").lower()
            if sec_norm == norm_target or sec_norm.endswith("/" + norm_target) or norm_target.endswith("/" + sec_norm):
                target_y = sec.y_start
                break

        if target_y is not None:
            new_scroll = max(0, min(self.scrollbar.max_val, target_y))
            self.scrollbar.set_value(new_scroll)
            self.scroll_y = new_scroll
            self.update()

    def filter_by_person(
        self,
        contact_id: str,
        person_name: str,
        db_indices: List[int],
        only_suggestions: bool = False
    ) -> None:
        """
        FR: Affiche les photos et visages associés à une personne avec support du mode zoom visage
        ou photo complète, volet de suggestions et filtrage exclusif des suggestions.
        EN: Displays photos and faces associated with a person, supporting face zoom or full picture mode,
        suggestion items, and suggestions-only filtering.
        Ref: picasa3.exe @ faceheaderpanel/face_zoom, picture_zoom, sug_filter, confirmsug, sug_label
        """
        self.current_folder_filter = f"person:{contact_id}"

        # Nettoyer les items spécifiques précédents (personne, suggestions ou sans nom synthétiques)
        self.items = [it for it in self.items if not getattr(it, "is_synthetic_unnamed", False) and not getattr(it, "is_person_item", False)]

        # 1. Récupérer / créer un item pour chaque enregistrement confirmé associé à cette personne
        person_item_indices: List[int] = []
        existing_map = {it.index: i for i, it in enumerate(self.items)}
        for db_idx in db_indices:
            # Vérifier si cet index correspond déjà à un item existant (O(1))
            existing_pos = existing_map.get(db_idx)
            if existing_pos is not None:
                person_item_indices.append(existing_pos)
                continue

            # Créer un ThumbnailItem pour ce visage / cette photo
            is_face_rec = self.db.is_face_record(db_idx) if self.db else False
            ppath = self.db.get_media_full_path(db_idx) if self.db else ""
            fname = os.path.basename(ppath) if ppath else (person_name or f"Visage {db_idx}")
            fdir = os.path.dirname(ppath) if ppath else ""
            fol_name = os.path.basename(fdir) if fdir else "Personnes"

            fr: Optional[FaceRect] = None
            if self.db and getattr(self.db, "face_manager", None):
                faces = self.db.face_manager.get_faces_for_photo(db_idx)
                for f in faces:
                    if f.contact_id == contact_id:
                        fr = f
                        break
                if fr is None and faces:
                    fr = faces[0]

            item = ThumbnailItem(
                index=db_idx,
                path=ppath,
                filename=fname,
                folder=fol_name,
                folder_path=fdir,
                face_rect=fr,
                is_person_item=True,
            )
            self.items.append(item)
            person_item_indices.append(len(self.items) - 1)

        # 2. Suggestions en attente pour cette personne (Ref: FRSuggestionThreshold ~0.60)
        suggestions = []
        if self.db and getattr(self.db, "face_manager", None):
            suggestions = self.db.face_manager.get_suggestions(contact_id)

        # 3. Créer des ThumbnailItems synthétiques pour les suggestions
        suggestion_item_indices: List[int] = []
        for sug in suggestions:
            s_fname = os.path.basename(sug.photo_path) if sug.photo_path else "Suggestion"
            s_fdir = os.path.dirname(sug.photo_path) if sug.photo_path else ""
            s_fol = os.path.basename(s_fdir) if s_fdir else person_name
            sug_item = ThumbnailItem(
                index=sug.db_idx if sug.db_idx is not None else -1,
                path=sug.photo_path,
                filename=s_fname,
                folder=s_fol,
                folder_path=s_fdir,
                face_rect=sug.face_rect,
                is_person_item=True,
                is_synthetic_suggestion=True,
                suggestion=sug,
            )
            self.items.append(sug_item)
            suggestion_item_indices.append(len(self.items) - 1)

        # Si l'utilisateur a demandé d'afficher uniquement les suggestions mais qu'il n'y en a pas
        if only_suggestions and not suggestions:
            only_suggestions = False

        active_indices = suggestion_item_indices if only_suggestions else person_item_indices
        date_str = f"{len(suggestions)} suggestion(s)" if only_suggestions else "Personnes"

        person_sec = AlbumSection(
            name=person_name,
            folder_path=f"person:{contact_id}",
            date_str=date_str,
            item_indices=list(active_indices),
            is_person=True,
            face_zoom=True,
            contact_id=contact_id,
            suggestions=suggestions,
            only_suggestions=only_suggestions,
            all_person_indices=list(person_item_indices),
            suggestion_item_indices=list(suggestion_item_indices),
        )

        self.visible_sections = [person_sec]
        self._unfiltered_special_sections = self._clone_special_sections(self.visible_sections)
        self.filtered_indices = list(active_indices)
        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.set_value(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def _toggle_suggestions_only(self, sec: AlbumSection) -> None:
        """
        FR: Bascule entre l'affichage de l'ensemble des photos de la personne et
        l'affichage exclusif des suggestions en attente de validation.
        EN: Toggles between displaying all photos of the person and displaying
        only pending face suggestions.
        Ref: picasa3.exe @ faceheaderpanel/sug_filter (0x005E16EA, 0x0074B9D6)
        """
        if not sec.suggestions and not sec.only_suggestions:
            return

        sec.only_suggestions = not sec.only_suggestions
        if sec.only_suggestions:
            sec.item_indices = list(sec.suggestion_item_indices)
            s_count = len(sec.suggestions)
            sec.date_str = "1 suggestion" if s_count == 1 else f"{s_count} suggestions"
        else:
            sec.item_indices = list(sec.all_person_indices)
            sec.date_str = "Personnes"

        self._unfiltered_special_sections = self._clone_special_sections(self.visible_sections)
        self.filtered_indices = list(sec.item_indices)
        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.set_value(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def filter_by_unnamed_faces(
        self,
        unnamed_faces: List[Tuple[Optional[int], str, Any]],
        grouped: bool = False
    ) -> None:
        """
        FR: Affiche les visages détectés sans nom d'après l'album officiel Picasa 3.
        Permet le groupement automatique par similarité faciale ou la nomination directe.
        EN: Displays detected unnamed faces following Picasa 3's official unnamed album.
        Supports automatic facial similarity clustering or direct naming.
        Ref: picasa3.exe @ unknownfaceheaderpanel (cluster, addname, ignore), CThumbDB::unknownfacealbum
        """
        self.current_folder_filter = "unnamed_faces"

        # Retirer les items synthétiques précédents
        self.items = [it for it in self.items if not getattr(it, "is_synthetic_unnamed", False)]

        unnamed_items: List[ThumbnailItem] = []
        for db_idx, ppath, fr in unnamed_faces:
            item = ThumbnailItem(
                index=db_idx if db_idx is not None else -1,
                path=ppath,
                filename=os.path.basename(ppath) if ppath else "Sans nom",
                folder="Sans nom",
                folder_path="unnamed_faces",
                face_rect=fr,
                is_synthetic_unnamed=True,
            )
            self.items.append(item)
            unnamed_items.append(item)

        if not grouped:
            item_indices = [len(self.items) - len(unnamed_items) + i for i in range(len(unnamed_items))]
            sec = AlbumSection(
                name="Visages sans nom",
                folder_path="unnamed_faces",
                date_str=f"{len(item_indices)} visage(s) à identifier",
                item_indices=list(item_indices),
                is_person=True,
                is_unnamed=True,
                face_zoom=True,
                unnamed_faces=unnamed_faces,
            )
            self.visible_sections = [sec]
            self._unfiltered_special_sections = self._clone_special_sections(self.visible_sections)
            self.filtered_indices = list(item_indices)
            self.selected_indices.clear()
            self.scroll_y = 0
            self.scrollbar.set_value(0)
            self._recompute_layout()
            self.update()
            self.selection_changed.emit(list(self.selected_indices))
        else:
            clusters = self.db.face_manager.cluster_unnamed_faces() if (self.db and getattr(self.db, "face_manager", None)) else [[f] for f in unnamed_faces]
            self._apply_unnamed_clusters(clusters)

    def _start_cluster_worker(self) -> None:
        """
        FR: Lance le groupement des visages en arrière-plan (QThread) pour préserver
        une réactivité parfaite de l'interface graphique.
        EN: Starts background face clustering (QThread) to preserve UI responsiveness.
        Ref: picasa3.exe @ CAlbumLabel::LoadingGrouped (0x00881CC0), AGENTS.md §4 ter
        """
        if not self.db or not getattr(self.db, "face_manager", None):
            return

        # Protection essentielle contre les clics répétés (destruction accidentelle du QThread en cours)
        if getattr(self, "_cluster_worker", None) is not None:
            if self._cluster_worker.isRunning():
                return

        main_win = self.window()
        if hasattr(main_win, "status_bar"):
            main_win.status_bar.showMessage("Regroupement des visages. Merci de patienter...")

        self.setCursor(Qt.CursorShape.WaitCursor)
        worker = FaceClusterWorker(self.db.face_manager, parent=None)
        self._cluster_worker = worker

        def _on_prog(cur, total):
            """
            FR: Affiche la progression du regroupement des visages dans la barre d'état.
            EN: Displays face clustering progress in the status bar.
            """
            if hasattr(main_win, "status_bar"):
                main_win.status_bar.showMessage(f"Regroupement des visages en cours : {cur}/{total}...")

        def _on_done(clusters):
            """
            FR: Applique les groupes de visages calculés et restaure le curseur à la fin du thread.
            EN: Applies computed face clusters and restores the cursor when the worker finishes.
            """
            self.unsetCursor()
            self._apply_unnamed_clusters(clusters)
            multi_cnt = sum(1 for c in clusters if len(c) > 1)
            if hasattr(main_win, "status_bar"):
                main_win.status_bar.showMessage(
                    f"Regroupement terminé : {multi_cnt} groupe(s) de visages identifié(s).", 4000
                )
            worker.wait()
            if getattr(self, "_cluster_worker", None) is worker:
                self._cluster_worker = None

        worker.progress.connect(_on_prog)
        worker.finished.connect(_on_done)
        worker.start(QThread.Priority.LowPriority)

    def _apply_unnamed_clusters(self, clusters: List[List[Tuple[Optional[int], str, Any]]]) -> None:
        """
        FR: Applique les clusters de visages sans nom dans la vue.
        Regroupe les visages similaires dans des sections de groupe et réunit les visages
        isolés non groupés dans une section finale unique.
        EN: Applies unnamed face clusters to the view.
        Groups similar faces into cluster sections and gathers isolated faces into a single trailing section.
        Ref: picasa3.exe @ 0x00CA1278 ("Unnamed people in these groups:"), 0x00CA12A5 (PeoplePanel::UnnamedCluster)
        """
        self.current_folder_filter = "unnamed_faces"
        self.items = [it for it in self.items if not getattr(it, "is_synthetic_unnamed", False)]

        all_cluster_faces = []
        for c in clusters:
            all_cluster_faces.extend(c)

        unnamed_items: List[ThumbnailItem] = []
        for db_idx, ppath, fr in all_cluster_faces:
            item = ThumbnailItem(
                index=db_idx if db_idx is not None else -1,
                path=ppath,
                filename=os.path.basename(ppath) if ppath else "Sans nom",
                folder="Sans nom",
                folder_path="unnamed_faces",
                face_rect=fr,
                is_synthetic_unnamed=True,
            )
            self.items.append(item)
            unnamed_items.append(item)

        self.visible_sections = []
        self.filtered_indices = []

        unnamed_map: Dict[Tuple[str, float, float], int] = {}
        start_idx = len(self.items) - len(unnamed_items)
        for i, it in enumerate(unnamed_items):
            if it.face_rect:
                unnamed_map[(it.path, round(it.face_rect.left, 4), round(it.face_rect.top, 4))] = start_idx + i

        multi_clusters = [c for c in clusters if len(c) > 1]
        single_faces = [c[0] for c in clusters if len(c) == 1]

        # 1. Sections pour chaque groupe de visages similaires
        for c_idx, cluster in enumerate(multi_clusters):
            c_indices = []
            for db_idx, ppath, fr in cluster:
                k = (ppath, round(fr.left, 4), round(fr.top, 4))
                if k in unnamed_map:
                    c_indices.append(unnamed_map[k])

            sec = AlbumSection(
                name=f"Groupe de visages similaires #{c_idx + 1}",
                folder_path=f"unnamed_cluster:{c_idx}",
                date_str=f"{len(c_indices)} visage(s)",
                item_indices=list(c_indices),
                is_person=True,
                is_unnamed=True,
                face_zoom=True,
                cluster_faces=cluster,
                unnamed_faces=cluster,
            )
            self.visible_sections.append(sec)
            self.filtered_indices.extend(c_indices)

        # 2. Section unifiée pour tous les visages isolés (non groupés)
        if single_faces:
            s_indices = []
            for db_idx, ppath, fr in single_faces:
                k = (ppath, round(fr.left, 4), round(fr.top, 4))
                if k in unnamed_map:
                    s_indices.append(unnamed_map[k])

            sec_single = AlbumSection(
                name="Autres visages (isolés)",
                folder_path="unnamed_cluster:singles",
                date_str=f"{len(s_indices)} visage(s)",
                item_indices=list(s_indices),
                is_person=True,
                is_unnamed=True,
                face_zoom=True,
                cluster_faces=single_faces,
                unnamed_faces=single_faces,
            )
            self.visible_sections.append(sec_single)
            self.filtered_indices.extend(s_indices)

        self._unfiltered_special_sections = self._clone_special_sections(self.visible_sections)
        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.set_value(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def filter_by_album(self, album_token: str, album_name: str, item_indices: List[int]) -> None:
        """
        FR: Affiche les photos associées à un album virtuel.
        EN: Displays photos associated with a virtual album.
        Ref: picasa3.exe @ 0x00732160 (Album display & slice)
        """
        self.current_folder_filter = f"album:{album_token}"
        album_sec = AlbumSection(
            name=album_name,
            folder_path=f"album:{album_token}",
            date_str="Album",
            item_indices=list(item_indices),
            is_album=True,
            album_token=album_token,
        )
        self.visible_sections = [album_sec]
        self._unfiltered_special_sections = self._clone_special_sections(self.visible_sections)
        self.filtered_indices = list(item_indices)
        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.set_value(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def filter_by_starred(self) -> None:
        """
        FR: Affiche l'album virtuel des photos favorites (marquées d'une étoile).
        EN: Displays the virtual album of starred (favorite) photos.
        Ref: picasa3.exe @ CThumbDB::starredphotos (0x0088F6FC, 0x0068B800)
        """
        self.current_folder_filter = "special:starred"
        starred_indices = [i for i, it in enumerate(self.items) if it.starred]
        starred_sec = AlbumSection(
            name="Photos favorites",
            folder_path="special:starred",
            date_str="Favoris",
            item_indices=list(starred_indices),
            is_album=True,
            album_token="starred",
        )
        self.visible_sections = [starred_sec]
        self._unfiltered_special_sections = self._clone_special_sections(self.visible_sections)
        self.filtered_indices = list(starred_indices)
        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.set_value(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def filter_by_search(self, query: str, item_indices: List[int]) -> None:
        """
        FR: Affiche les photos correspondant aux critères de recherche.
        EN: Displays photos matching the search query criteria.
        Ref: picasa3.exe @ 0x0088C3EC (Search & Filters)
        """
        self.current_folder_filter = f"search:{query}"
        search_sec = AlbumSection(
            name=f'Recherche : "{query}"',
            folder_path=f"search:{query}",
            date_str=f"{len(item_indices)} résultat(s)",
            item_indices=list(item_indices),
            is_search=True,
        )
        self.visible_sections = [search_sec]
        self._unfiltered_special_sections = self._clone_special_sections(self.visible_sections)
        self.filtered_indices = list(item_indices)
        self.selected_indices.clear()
        self.scroll_y = 0
        self.scrollbar.set_value(0)
        self._recompute_layout()
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def _on_zoom_settled(self) -> None:
        """
        FR: Désactive le mode de zoom rapide et redessine les vignettes avec `SmoothTransformation` une fois le curseur stabilisé.
        EN: Disables fast zoom mode and repaints thumbnails with `SmoothTransformation` once the zoom slider settles.
        """
        self._is_zooming_thumbs = False
        self._scaled_pixmap_cache.clear()
        self.update()

    def set_thumb_size(self, size: int) -> None:
        """
        FR: Définit la taille de base des vignettes (entre 64 et 320 pixels) et recalcule la grille.
        EN: Sets the base thumbnail size (clamped between 64 and 320 pixels) and recomputes the grid layout.
        """
        new_size = max(64, min(320, size))
        if new_size != self.thumb_base_size:
            self.thumb_base_size = new_size
            self._is_zooming_thumbs = True
            self._zoom_settle_timer.start()
        self._recompute_layout()
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        FR: Repositionne la barre de défilement et recalcule la disposition lors du redimensionnement.
        EN: Repositions the custom scrollbar and recomputes the grid layout on widget resize.
        """
        super().resizeEvent(event)
        sb_width = self.scrollbar.width()
        self.scrollbar.setGeometry(self.width() - sb_width, 0, sb_width, self.height())
        self._recompute_layout()

    def _recompute_layout(self) -> None:
        """
        FR: Calcule les coordonnées exactes (Y) de chaque section et vignette.
        EN: Computes the exact vertical (Y) coordinates for each section and thumbnail.
        Ref: picasa3.exe @ 0x0072E330 (AVCScrollBox bounds calculation)
        """
        available_width = self.width() - self.scrollbar.width() - (self.style.alayout_gutter * 2)
        if available_width <= 0:
            return

        slot_width = self.thumb_base_size + self.style.alayout_thumbGutterX
        cols = max(1, available_width // slot_width)
        slot_height = self.thumb_base_size + self.style.alayout_thumbGutterY + 16

        current_y = 12
        header_height = 42

        for sec in self.visible_sections:
            sec.y_start = current_y
            rows = math.ceil(len(sec.item_indices) / cols) if sec.item_indices else 0
            grid_h = rows * slot_height
            sec.height = header_height + grid_h + 20
            current_y += sec.height

        self.total_content_height = current_y + 40
        max_scroll = max(0, self.total_content_height - self.height())
        self.scrollbar.set_range(0, max_scroll, page_step=self.height())

    def get_album_info_at_scroll(self, scroll_y: int) -> Tuple[str, str]:
        """
        FR: Fournit l'album et la date correspondant à une position de défilement.
        Alimente le badge flottant PicasaScrollTooltip en temps réel.
        EN: Returns the album name and date subtitle at a given scroll position.
        Feeds the floating PicasaScrollTooltip badge in real time.
        Ref: picasa3.exe @ 0x005DE8E0
        """
        if not self.visible_sections:
            return ("", "")

        target_y = scroll_y + 60
        matched_sec = self.visible_sections[0]

        for sec in self.visible_sections:
            if sec.y_start <= target_y:
                matched_sec = sec
            else:
                break

        count_str = f"{len(matched_sec.item_indices)} photos"
        sub = f"{matched_sec.date_str} • {count_str}" if matched_sec.date_str else count_str
        return (matched_sec.name, sub)

    def _on_scroll(self, val: int) -> None:
        """
        FR: Met à jour le décalage vertical de défilement, signale l'activité GUI aux workers
        d'arrière-plan pour leur faire céder le CPU, et émet le dossier actif au sommet.
        EN: Updates the vertical scroll offset, signals GUI activity to background workers
        so they yield CPU bandwidth, and emits the active top folder.
        """
        try:
            from picasa_py.scanner.scanner import BackgroundScanWorker
            BackgroundScanWorker.notify_gui_activity()
        except Exception:
            pass
        self.scroll_y = val
        self.update()
        # Notifier du changement d'album actif au sommet (Ref: MultiAlbumScroll)
        if self.visible_sections:
            sticky_idx, _ = self._get_sticky_header_info()
            if sticky_idx is not None and 0 <= sticky_idx < len(self.visible_sections):
                self.active_folder_changed.emit(self.visible_sections[sticky_idx].folder_path)
            elif self.visible_sections:
                self.active_folder_changed.emit(self.visible_sections[0].folder_path)

    def _on_jump_prev_album(self) -> None:
        """
        FR: Saut direct vers l'en-tête de l'album précédent (prevalbum).
        EN: Jumps directly to the previous album header (prevalbum).
        """
        curr = self.scroll_y
        target = 0
        for sec in reversed(self.visible_sections):
            if sec.y_start < curr - 20:
                target = sec.y_start
                break
        self.scrollbar.set_value(target)
        self.scroll_y = target
        self.update()

    def _on_jump_next_album(self) -> None:
        """
        FR: Saut direct vers l'en-tête de l'album suivant (nextalbum).
        EN: Jumps directly to the next album header (nextalbum).
        """
        curr = self.scroll_y
        target = self.scrollbar.max_val
        for sec in self.visible_sections:
            if sec.y_start > curr + 20:
                target = sec.y_start
                break
        self.scrollbar.set_value(target)
        self.scroll_y = target
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        FR: Gère le défilement vertical de la grille à la molette de la souris.
        EN: Handles vertical scrolling of the thumbnail grid via the mouse wheel.
        """
        try:
            from picasa_py.scanner.scanner import BackgroundScanWorker
            BackgroundScanWorker.notify_gui_activity()
        except Exception:
            pass
        delta = event.angleDelta().y()
        step = 60 if delta > 0 else -60
        new_val = max(0, min(self.scrollbar.max_val, self.scrollbar.value() - step))
        self.scrollbar.set_value(new_val)
        self.scroll_y = new_val
        self.update()

    # -------------------------------------------------------------------------
    # FR: Géométrie & Détection des Clics / EN: Geometry & Hit Testing
    # -------------------------------------------------------------------------
    def _get_grid_metrics(self) -> Tuple[int, int, int, int]:
        """
        FR: Retourne les métriques de la grille de vignettes (colonnes, largeur de cellule, hauteur de cellule, marge X).
        EN: Returns the thumbnail grid metrics (columns, cell width, cell height, X margin).
        """
        available_width = self.width() - self.scrollbar.width() - (self.style.alayout_gutter * 2)
        slot_width = max(1, self.thumb_base_size + self.style.alayout_thumbGutterX)
        cols = max(1, available_width // slot_width)
        slot_height = max(1, self.thumb_base_size + self.style.alayout_thumbGutterY + 16)
        return cols, slot_width, slot_height, self.style.alayout_gutter

    def _get_item_rect(self, sec: AlbumSection, slot_in_sec: int) -> QRect:
        """
        FR: Calcule le rectangle d'affichage d'une vignette dans sa section.
        EN: Computes the display rectangle of a thumbnail within its section.
        """
        cols, slot_width, slot_height, margin_x = self._get_grid_metrics()

        col = slot_in_sec % cols
        row = slot_in_sec // cols

        header_height = 42

        x = margin_x + col * slot_width
        y = sec.y_start + header_height + row * slot_height - self.scroll_y
        return QRect(x, y, self.thumb_base_size, self.thumb_base_size)

    def _find_item_at(self, point: QPoint) -> Optional[int]:
        """
        FR: Recherche en O(1) l'index de la vignette située aux coordonnées données du pointeur.
        EN: Finds in O(1) the thumbnail item index located at the given pointer coordinates.
        Ref: picasa3.exe @ 0x0072E330 (AVCScrollBox bounds & hit-test)
        """
        cols, _, slot_height, _ = self._get_grid_metrics()
        header_height = 42
        vh = self.height()
        py = point.y()
        for sec in self.visible_sections:
            sec_top = sec.y_start - self.scroll_y
            if sec_top > vh:
                break
            sec_bottom = sec_top + sec.height
            if sec_bottom < 0:
                continue
            if not (sec_top <= py <= sec_bottom):
                continue

            rel_y = py - (sec_top + header_height)
            approx_row = rel_y // slot_height
            first_row = max(0, approx_row - 1)
            last_row = approx_row + 1
            start_slot = first_row * cols
            end_slot = min(len(sec.item_indices), (last_row + 1) * cols)
            for slot_idx in range(start_slot, end_slot):
                r = self._get_item_rect(sec, slot_idx)
                if r.adjusted(-4, -4, 4, 20).contains(point):
                    return sec.item_indices[slot_idx]
        return None

    def _get_sticky_header_info(self) -> Tuple[Optional[int], int]:
        """
        FR: Détermine la section d'album actuellement épinglée en haut de l'écran
        et sa coordonnée Y (effet 'sticky header' de Picasa avec poussée par l'album suivant).
        EN: Determines the album section currently pinned at the top of the viewport
        and its Y coordinate (Picasa sticky header effect pushed by the next album).
        Ref: picasa3.exe @ albumheader
        """
        header_h = 38
        for i, sec in enumerate(self.visible_sections):
            sec_top = sec.y_start - self.scroll_y
            sec_bottom = sec_top + sec.height
            if sec_top <= 0 and sec_bottom > 0:
                sticky_y = 0
                if i + 1 < len(self.visible_sections):
                    next_top = self.visible_sections[i + 1].y_start - self.scroll_y
                    if next_top < header_h:
                        sticky_y = next_top - header_h
                return (i, sticky_y)
        return (None, 0)

    def _get_header_rect(self, y: int) -> QRect:
        """
        FR: Retourne le rectangle complet d'un en-tête de section à la position verticale y.
        EN: Returns the bounding rectangle of a section header at vertical position y.
        """
        header_w = self.width() - self.scrollbar.width()
        return QRect(0, y, header_w, 38)

    def _get_slideshow_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Diaporama' (headerpanel/play) dans l'en-tête d'album/dossier.
        EN: Bounding rectangle of the 'Play Slideshow' (headerpanel/play) button in the section header.
        Ref: picasa3.exe @ headerpanel.tre, HEADERPANELTEXT_FR.XML (headerpanel/play)
        """
        header_w = self.width() - self.scrollbar.width()
        btn_w = 95
        btn_x = header_w - btn_w - 14
        return QRect(btn_x, y + 7, btn_w, 24)

    def _get_collage_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Montage' (headerpanel/create_collage) dans l'en-tête d'album/dossier.
        EN: Bounding rectangle of the 'Create Collage' (headerpanel/create_collage) button in the section header.
        Ref: picasa3.exe @ HEADERPANELTEXT_FR.XML (headerpanel/create_collage)
        """
        slide_r = self._get_slideshow_btn_rect(y)
        btn_w = 78
        return QRect(slide_r.x() - btn_w - 6, y + 7, btn_w, 24)

    def _get_movie_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Film' (headerpanel/create_movie) dans l'en-tête d'album/dossier.
        EN: Bounding rectangle of the 'Create Movie' (headerpanel/create_movie) button in the section header.
        Ref: picasa3.exe @ HEADERPANELTEXT_FR.XML (headerpanel/create_movie)
        """
        collage_r = self._get_collage_btn_rect(y)
        btn_w = 64
        return QRect(collage_r.x() - btn_w - 6, y + 7, btn_w, 24)

    def _get_select_star_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Sélectionner les photos favorites' (headerpanel/select_star) dans l'en-tête.
        EN: Bounding rectangle of the 'Select Starred Photos' (headerpanel/select_star) button in the header.
        Ref: picasa3.exe @ HEADERPANELTEXT_FR.XML (headerpanel/select_star)
        """
        movie_r = self._get_movie_btn_rect(y)
        btn_w = 28
        return QRect(movie_r.x() - btn_w - 6, y + 7, btn_w, 24)

    def _get_save_edits_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Enregistrer les photos retouchées sur un disque' (headerpanel/save_edits).
        EN: Bounding rectangle of the 'Save Edited Photos to Disk' (headerpanel/save_edits) button.
        Ref: picasa3.exe @ HEADERPANELTEXT_FR.XML (headerpanel/save_edits)
        """
        star_r = self._get_select_star_btn_rect(y)
        btn_w = 28
        return QRect(star_r.x() - btn_w - 6, y + 7, btn_w, 24)

    def _get_face_zoom_btn_rect(self, y: int) -> QRect:
        """
        FR: Retourne le rectangle du bouton de bascule 'Visages' (face_zoom) dans l'en-tête de personne.
        EN: Returns the rectangle for the 'Faces' zoom toggle button (face_zoom) in the person header.
        """
        header_w = self.width() - self.scrollbar.width()
        btn_slideshow_w = 95
        btn_slideshow_x = header_w - btn_slideshow_w - 14
        btn_pic_x = btn_slideshow_x - 72 - 6
        btn_face_x = btn_pic_x - 76 - 6
        return QRect(btn_face_x, y + 7, 76, 24)

    def _get_picture_zoom_btn_rect(self, y: int) -> QRect:
        """
        FR: Retourne le rectangle du bouton de bascule 'Photos' (picture_zoom) dans l'en-tête de personne.
        EN: Returns the rectangle for the 'Pictures' zoom toggle button (picture_zoom) in the person header.
        """
        header_w = self.width() - self.scrollbar.width()
        btn_slideshow_w = 95
        btn_slideshow_x = header_w - btn_slideshow_w - 14
        btn_pic_x = btn_slideshow_x - 72 - 6
        return QRect(btn_pic_x, y + 7, 72, 24)

    def _get_sug_filter_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Afficher uniquement les suggestions' dans l'en-tête.
        EN: Bounding rectangle of the 'Show Only Suggestions' filter button in the person header.
        Ref: picasa3.exe @ faceheaderpanel/sug_filter (0x005E16EA, 0x0074B9D6)
        """
        header_w = self.width() - self.scrollbar.width()
        btn_slideshow_w = 95
        btn_slideshow_x = header_w - btn_slideshow_w - 14
        btn_pic_x = btn_slideshow_x - 72 - 6
        btn_face_x = btn_pic_x - 76 - 6
        btn_sug_w = 135
        btn_sug_x = btn_face_x - btn_sug_w - 6
        return QRect(btn_sug_x, y + 7, btn_sug_w, 24)

    def _get_confirm_sug_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Tout valider' dans l'en-tête de la personne.
        EN: Bounding rectangle of the 'Confirm All' suggestions button in the person header.
        Ref: picasa3.exe @ faceheaderpanel/confirmsug (0x00896F74)
        """
        sug_btn_rect = self._get_sug_filter_btn_rect(y)
        btn_confirm_w = 115
        btn_confirm_x = sug_btn_rect.x() - btn_confirm_w - 6
        return QRect(btn_confirm_x, y + 7, btn_confirm_w, 24)

    def _get_confirm_sel_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Confirmer' pour les suggestions sélectionnées.
        EN: Bounding rectangle of the 'Confirm Selected' suggestions button.
        Ref: picasa3.exe @ faceheaderpanel/confirmsel (0x005E1610, 0x0074B78E, 0x00896F80)
        """
        confirm_all_rect = self._get_confirm_sug_btn_rect(y)
        btn_w = 90
        btn_x = confirm_all_rect.x() - btn_w - 6
        return QRect(btn_x, y + 7, btn_w, 24)

    def _get_remove_sel_btn_rect(self, y: int) -> QRect:
        """
        FR: Position du bouton 'Supprimer' (ignorer) pour les suggestions sélectionnées.
        EN: Bounding rectangle of the 'Remove Selected' (ignore) suggestions button.
        Ref: picasa3.exe @ faceheaderpanel/removesel (0x005E177C, 0x0074B8C7, 0x00896FA8)
        """
        confirm_sel_rect = self._get_confirm_sel_btn_rect(y)
        btn_w = 90
        btn_x = confirm_sel_rect.x() - btn_w - 6
        return QRect(btn_x, y + 7, btn_w, 24)

    def _get_suggestion_item_buttons(self, rect: QRect) -> Tuple[QRect, QRect]:
        """
        FR: Retourne les rectangles des boutons Valider (✓) et Ignorer (✗)
        dessinés sur la vignette d'une suggestion de visage.
        EN: Returns the bounding rectangles for the Confirm (✓) and Reject (✗) buttons
        drawn on a face suggestion thumbnail.
        Ref: picasa3.exe @ adorners/suggestionfaceadorner (0x00714707, 0x00782DF6)
        Ref: picasa3.exe @ arrows/checkyes (0x00761E33), arrows/checkno (0x00761E47)
        """
        btn_w = 28
        btn_h = 22
        btn_y = rect.bottom() - 25
        btn_ok = QRect(rect.left() + 6, btn_y, btn_w, btn_h)
        btn_no = QRect(rect.right() - btn_w - 6, btn_y, btn_w, btn_h)
        return (btn_ok, btn_no)

    def _get_cluster_action_btn_rect(self, y: int) -> QRect:
        """
        FR: Retourne le rectangle du bouton d'action principal de regroupement ou de nommage de groupe.
        EN: Returns the rectangle for the primary cluster or add-name action button in the unnamed header.
        """
        header_w = self.width() - self.scrollbar.width()
        btn_slideshow_w = 95
        btn_slideshow_x = header_w - btn_slideshow_w - 14
        btn_w = 155
        btn_x = btn_slideshow_x - btn_w - 8
        return QRect(btn_x, y + 7, btn_w, 24)

    def _get_ungroup_action_btn_rect(self, y: int) -> QRect:
        """
        FR: Retourne le rectangle du bouton 'Développer les groupes' dans l'en-tête des visages sans nom.
        EN: Returns the rectangle for the 'Expand Groups' button in the unnamed faces header.
        """
        header_w = self.width() - self.scrollbar.width()
        btn_slideshow_w = 95
        btn_slideshow_x = header_w - btn_slideshow_w - 14
        btn_cluster_w = 155
        btn_cluster_x = btn_slideshow_x - btn_cluster_w - 8
        btn_ungroup_w = 170
        btn_x = btn_cluster_x - btn_ungroup_w - 8
        return QRect(btn_x, y + 7, btn_ungroup_w, 24)

    def _get_ignore_action_btn_rect(self, y: int) -> QRect:
        """
        FR: Retourne le rectangle du bouton 'Ignorer' pour un groupe de visages sans nom.
        EN: Returns the rectangle for the 'Ignore' button on an unnamed face cluster header.
        """
        header_w = self.width() - self.scrollbar.width()
        btn_slideshow_w = 95
        btn_slideshow_x = header_w - btn_slideshow_w - 14
        btn_cluster_w = 155
        btn_cluster_x = btn_slideshow_x - btn_cluster_w - 8
        btn_ungroup_w = 170
        btn_ungroup_x = btn_cluster_x - btn_ungroup_w - 8
        btn_ign_w = 80
        btn_x = btn_ungroup_x - btn_ign_w - 8
        return QRect(btn_x, y + 7, btn_ign_w, 24)

    def _handle_unnamed_cluster_action(self, sec: AlbumSection) -> None:
        """
        FR: Déclenche l'action de groupement ou de nommage en masse pour les visages sans nom.
        EN: Triggers the clustering or batch-naming action for unnamed faces.
        Ref: picasa3.exe @ unknownfaceheaderpanel/cluster, addname
        """
        if sec.cluster_faces is not None:
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(
                self, "Nommer le groupe de visages",
                f"Nom de la personne correspondant à ce groupe ({len(sec.cluster_faces)} visages) :"
            )
            if ok and name.strip() and self.db and getattr(self.db, "face_manager", None):
                self.db.face_manager.name_cluster(sec.cluster_faces, name.strip())
                self._start_cluster_worker()
        else:
            self._start_cluster_worker()

    def _handle_ignore_cluster_action(self, sec: AlbumSection) -> None:
        """
        FR: Ignore tous les visages de ce groupe en les retirant des visages sans nom.
        EN: Ignores all faces in this cluster by removing them from unnamed faces.
        Ref: picasa3.exe @ unknownfaceheaderpanel/ignore, CThumbDB::ignorefacealbum (0x00c833d2)
        """
        if not sec.cluster_faces or not self.db or not getattr(self.db, "face_manager", None):
            return
        to_ignore = set()
        for db_idx, ppath, fr in sec.cluster_faces:
            to_ignore.add((ppath, round(fr.left, 4), round(fr.top, 4)))

        self.db.face_manager.unnamed_faces = [
            (i, p, f) for (i, p, f) in self.db.face_manager.unnamed_faces
            if (p, round(f.left, 4), round(f.top, 4)) not in to_ignore
        ]
        self._start_cluster_worker()

    def _confirm_single_suggestion(self, sec: AlbumSection, item: ThumbnailItem) -> None:
        """
        FR: Valide une suggestion individuelle (clic sur la coche verte ✓).
        EN: Confirms an individual face suggestion (click on the green checkmark ✓).
        Ref: picasa3.exe @ arrows/checkyes (0x00761E33), confirmsel (0x00896F80)
        """
        sug = getattr(item, "suggestion", None)
        if sug is None and self.db and getattr(self.db, "face_manager", None):
            for s in self.db.face_manager.get_all_suggestions():
                if s.photo_path == item.path and (item.face_rect is None or _face_overlap(s.face_rect, item.face_rect) >= 0.5):
                    sug = s
                    break
        if sug and self.db and getattr(self.db, "face_manager", None):
            self.db.face_manager.confirm_suggestion(sug)
            cluster = self.db.face_manager.get_person(sec.contact_id)
            if cluster:
                still_sugs = bool(self.db.face_manager.get_suggestions(sec.contact_id))
                self.filter_by_person(
                    sec.contact_id,
                    cluster.name,
                    cluster.photo_indices,
                    only_suggestions=sec.only_suggestions and still_sugs
                )

    def _reject_single_suggestion(self, sec: AlbumSection, item: ThumbnailItem) -> None:
        """
        FR: Rejette/ignore une suggestion individuelle (clic sur la croix rouge ✕).
        EN: Rejects/ignores an individual face suggestion (click on the red cross ✕).
        Ref: picasa3.exe @ arrows/checkno (0x00761E47), removesel (0x00896FA8)
        """
        sug = getattr(item, "suggestion", None)
        if sug is None and self.db and getattr(self.db, "face_manager", None):
            for s in self.db.face_manager.get_all_suggestions():
                if s.photo_path == item.path and (item.face_rect is None or _face_overlap(s.face_rect, item.face_rect) >= 0.5):
                    sug = s
                    break
        if sug and self.db and getattr(self.db, "face_manager", None):
            self.db.face_manager.reject_suggestion(sug)
            cluster = self.db.face_manager.get_person(sec.contact_id)
            if cluster:
                still_sugs = bool(self.db.face_manager.get_suggestions(sec.contact_id))
                self.filter_by_person(
                    sec.contact_id,
                    cluster.name,
                    cluster.photo_indices,
                    only_suggestions=sec.only_suggestions and still_sugs
                )

    def _confirm_selected_suggestions(self, sec: AlbumSection) -> None:
        """
        FR: Valide l'ensemble des suggestions sélectionnées dans la grille.
        EN: Confirms all currently selected face suggestions in the grid.
        Ref: picasa3.exe @ faceheaderpanel/confirmsel (0x005E1610, 0x00896F80)
        """
        if not self.db or not getattr(self.db, "face_manager", None):
            return
        selected_sugs = []
        for idx in self.selected_indices:
            if idx < len(self.items):
                it = self.items[idx]
                sug = getattr(it, "suggestion", None)
                if sug:
                    selected_sugs.append(sug)
        for s in selected_sugs:
            self.db.face_manager.confirm_suggestion(s)
        cluster = self.db.face_manager.get_person(sec.contact_id)
        if cluster:
            still_sugs = bool(self.db.face_manager.get_suggestions(sec.contact_id))
            self.filter_by_person(
                sec.contact_id,
                cluster.name,
                cluster.photo_indices,
                only_suggestions=sec.only_suggestions and still_sugs
            )

    def _reject_selected_suggestions(self, sec: AlbumSection) -> None:
        """
        FR: Rejette/ignore l'ensemble des suggestions sélectionnées dans la grille.
        EN: Rejects/ignores all currently selected face suggestions in the grid.
        Ref: picasa3.exe @ faceheaderpanel/removesel (0x005E177C, 0x00896FA8)
        """
        if not self.db or not getattr(self.db, "face_manager", None):
            return
        selected_sugs = []
        for idx in self.selected_indices:
            if idx < len(self.items):
                it = self.items[idx]
                sug = getattr(it, "suggestion", None)
                if sug:
                    selected_sugs.append(sug)
        for s in selected_sugs:
            self.db.face_manager.reject_suggestion(s)
        cluster = self.db.face_manager.get_person(sec.contact_id)
        if cluster:
            still_sugs = bool(self.db.face_manager.get_suggestions(sec.contact_id))
            self.filter_by_person(
                sec.contact_id,
                cluster.name,
                cluster.photo_indices,
                only_suggestions=sec.only_suggestions and still_sugs
            )

    def _handle_header_click(self, sec: AlbumSection, hdr_y: int, pos: QPoint) -> bool:
        """
        FR: Traite un clic gauche dans un en-tête de section (sticky ou naturel).
        EN: Handles a left mouse click inside a section header (sticky or inline).
        Ref: picasa3.exe @ HEADERPANELTEXT_FR.XML, FACEHEADERPANELTEXT_FR.XML
        """
        if sec.is_unnamed:
            if sec.cluster_faces is not None:
                if self._get_ungroup_action_btn_rect(hdr_y).contains(pos):
                    unnamed = self.db.face_manager.unnamed_faces if (self.db and getattr(self.db, "face_manager", None)) else []
                    self.filter_by_unnamed_faces(unnamed, grouped=False)
                    return True
                if self._get_ignore_action_btn_rect(hdr_y).contains(pos):
                    self._handle_ignore_cluster_action(sec)
                    return True
                if self._get_cluster_action_btn_rect(hdr_y).contains(pos):
                    self._handle_unnamed_cluster_action(sec)
                    return True
            else:
                if self._get_cluster_action_btn_rect(hdr_y).contains(pos):
                    self._handle_unnamed_cluster_action(sec)
                    return True

        elif sec.is_person and not sec.is_unnamed:
            if sec.suggestions:
                if self._get_sug_filter_btn_rect(hdr_y).contains(pos):
                    self._toggle_suggestions_only(sec)
                    return True
                if self._get_confirm_sug_btn_rect(hdr_y).contains(pos):
                    if self.db and getattr(self.db, "face_manager", None) and sec.contact_id:
                        self.db.face_manager.confirm_all_suggestions(sec.contact_id)
                        cluster = self.db.face_manager.get_person(sec.contact_id)
                        if cluster:
                            self.filter_by_person(sec.contact_id, cluster.name, cluster.photo_indices, only_suggestions=False)
                    self.update()
                    return True
                has_sel_sug = any(getattr(self.items[i], "is_synthetic_suggestion", False) for i in self.selected_indices if i < len(self.items))
                if has_sel_sug:
                    if self._get_confirm_sel_btn_rect(hdr_y).contains(pos):
                        self._confirm_selected_suggestions(sec)
                        return True
                    if self._get_remove_sel_btn_rect(hdr_y).contains(pos):
                        self._reject_selected_suggestions(sec)
                        return True

            if self._get_face_zoom_btn_rect(hdr_y).contains(pos):
                sec.face_zoom = True
                self.update()
                return True
            if self._get_picture_zoom_btn_rect(hdr_y).contains(pos):
                sec.face_zoom = False
                self.update()
                return True

        else:
            # Boutons d'en-tête d'album/dossier (Ref: HEADERPANELTEXT_FR.XML)
            paths = [self.items[idx].path for idx in sec.item_indices if idx < len(self.items) and self.items[idx].path]
            if self._get_collage_btn_rect(hdr_y).contains(pos):
                self.collage_section_requested.emit(paths)
                return True
            if self._get_movie_btn_rect(hdr_y).contains(pos):
                self.movie_section_requested.emit(paths)
                return True
            if self._get_select_star_btn_rect(hdr_y).contains(pos):
                starred_in_sec = {idx for idx in sec.item_indices if idx < len(self.items) and self.items[idx].starred}
                self.selected_indices = starred_in_sec
                if starred_in_sec:
                    self.anchor_index = min(starred_in_sec)
                    self.focus_index = self.anchor_index
                self.update()
                self.selection_changed.emit(sorted(self.selected_indices))
                return True
            if self._get_save_edits_btn_rect(hdr_y).contains(pos):
                if sec.folder_path:
                    self.save_section_requested.emit(sec.folder_path)
                return True

        btn_rect = self._get_slideshow_btn_rect(hdr_y)
        if btn_rect.contains(pos):
            paths = [self.items[idx].path for idx in sec.item_indices if idx < len(self.items) and self.items[idx].path]
            self.slideshow_requested.emit(paths)
        else:
            self.selected_indices = set(sec.item_indices)
            if sec.item_indices:
                self.anchor_index = sec.item_indices[0]
                self.focus_index = sec.item_indices[0]
            self.update()
            self.selection_changed.emit(list(self.selected_indices))
        return True

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère les clics de souris sur les boutons d'action, en-têtes, étoiles, vignettes ou la sélection élastique.
        EN: Handles mouse press events on action buttons, headers, stars, thumbnails, or rubber-band selection.
        """
        try:
            from picasa_py.scanner.scanner import BackgroundScanWorker
            BackgroundScanWorker.notify_gui_activity()
        except Exception:
            pass
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self._deferred_single_select_idx = None

            # 1. Vérifier les clics directs sur les boutons d'action de suggestion (✓ ou ✕) sur les vignettes
            # Ref: picasa3.exe @ adorners/suggestionfaceadorner (0x00714707, 0x00782DF6)
            cols, _, slot_height, _ = self._get_grid_metrics()
            header_height = 42
            for sec in self.visible_sections:
                sec_top = sec.y_start - self.scroll_y
                if sec_top > self.height():
                    break
                sec_bottom = sec_top + sec.height
                if sec_bottom < 0:
                    continue
                if (sec.is_person or sec.is_unnamed or sec.suggestions) and (sec_top <= pos.y() <= sec_bottom):
                    rel_y = pos.y() - (sec_top + header_height)
                    approx_row = rel_y // slot_height
                    first_row = max(0, approx_row - 1)
                    last_row = approx_row + 1
                    start_slot = first_row * cols
                    end_slot = min(len(sec.item_indices), (last_row + 1) * cols)
                    for slot_idx in range(start_slot, end_slot):
                        it_idx = sec.item_indices[slot_idx]
                        if it_idx < len(self.items):
                            it = self.items[it_idx]
                            if getattr(it, "is_synthetic_suggestion", False):
                                r = self._get_item_rect(sec, slot_idx)
                                btn_ok, btn_no = self._get_suggestion_item_buttons(r)
                                if btn_ok.contains(pos):
                                    self._confirm_single_suggestion(sec, it)
                                    return
                                elif btn_no.contains(pos):
                                    self._reject_single_suggestion(sec, it)
                                    return
                            elif getattr(it, "is_synthetic_unnamed", False):
                                r = self._get_item_rect(sec, slot_idx)
                                caption_rect = QRect(r.x() - 4, r.bottom() + 1, r.width() + 8, 18)
                                if caption_rect.contains(pos):
                                    self._open_name_unnamed_face_dialog(it)
                                    return

            # 2. Vérifier d'abord le clic sur l'en-tête épinglé en haut (Sticky Header)
            sticky_idx, sticky_y = self._get_sticky_header_info()
            if sticky_idx is not None:
                sticky_hdr_rect = self._get_header_rect(sticky_y)
                if sticky_hdr_rect.contains(pos):
                    sec = self.visible_sections[sticky_idx]
                    self._handle_header_click(sec, sticky_y, pos)
                    return

            # 3. Vérifier le clic sur les en-têtes visibles naturels
            for i, sec in enumerate(self.visible_sections):
                if i == sticky_idx:
                    continue
                sec_top = sec.y_start - self.scroll_y
                if 0 <= sec_top <= self.height():
                    hdr_rect = self._get_header_rect(sec_top)
                    if hdr_rect.contains(pos):
                        self._handle_header_click(sec, sec_top, pos)
                        return

            # 4. Vérifier d'abord le clic direct sur l'étoile d'une vignette (Ref: star=yes, thumbui/startoggle)
            for sec in self.visible_sections:
                sec_top = sec.y_start - self.scroll_y
                if sec_top > self.height():
                    break
                sec_bottom = sec_top + sec.height
                if sec_bottom < 0:
                    continue
                if sec_top <= pos.y() <= sec_bottom:
                    rel_y = pos.y() - (sec_top + header_height)
                    approx_row = rel_y // slot_height
                    first_row = max(0, approx_row - 1)
                    last_row = approx_row + 1
                    start_slot = first_row * cols
                    end_slot = min(len(sec.item_indices), (last_row + 1) * cols)
                    for slot_idx in range(start_slot, end_slot):
                        it_idx = sec.item_indices[slot_idx]
                        r = self._get_item_rect(sec, slot_idx)
                        star_box = QRect(r.right() - 24, r.bottom() - 24, 24, 24)
                        if star_box.contains(pos) and it_idx < len(self.items):
                            target_it = self.items[it_idx]
                            if target_it.path:
                                target_it.starred = not target_it.starred
                                self.star_toggled.emit(target_it.path, target_it.starred)
                                self.update()
                                return

            # 5. Vérifier le clic sur une vignette individuelle ou le début d'un glisser-déposer / rectangle élastique
            item_idx = self._find_item_at(pos)
            modifiers = event.modifiers()
            if item_idx is not None:
                self._drag_start_pos = pos
                self._dragging_item_idx = item_idx
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    if item_idx in self.selected_indices:
                        self.selected_indices.remove(item_idx)
                    else:
                        self.selected_indices.add(item_idx)
                    self.anchor_index = item_idx
                    self.focus_index = item_idx
                elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                    self.focus_index = item_idx
                    self._select_range(item_idx)
                else:
                    if item_idx in self.selected_indices and len(self.selected_indices) > 1:
                        # Préserver la sélection multiple pour un éventuel glisser-déposer ou double-clic,
                        # et réduire à 1 élément au relâchement si aucun glisser n'a eu lieu.
                        import time as _time
                        self._pre_release_multi_selection = (set(self.selected_indices), item_idx, _time.monotonic())
                        self._deferred_single_select_idx = item_idx
                        self.focus_index = item_idx
                    else:
                        self._pre_release_multi_selection = None
                        self.selected_indices = {item_idx}
                        self.anchor_index = item_idx
                        self.focus_index = item_idx

                self.update()
                self.selection_changed.emit(list(self.selected_indices))
            else:
                # Clic dans le vide -> Démarrer la sélection par rectangle élastique (Rubber-band marquee)
                self._rubber_band_origin = pos
                self._rubber_band_rect = QRect(pos, QSize())
                if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                    self._rubber_band_base_selection = set(self.selected_indices)
                else:
                    self._rubber_band_base_selection = set()
                    self.selected_indices.clear()
                    self.anchor_index = None
                    self.focus_index = None
                    self.update()
                    self.selection_changed.emit([])

    def _start_thumbnail_drag(self) -> None:
        """
        FR: Démarre une opération de glisser-déposer (QDrag) avec les chemins des photos sélectionnées.
        EN: Starts a drag-and-drop operation (QDrag) with the file paths of selected photos.
        Ref: picasa3.exe @ CAlbumList::dragcolor, Drag & Drop vers Albums/Dossiers
        """
        if not self.selected_indices:
            return
        paths = [
            self.items[idx].path
            for idx in sorted(self.selected_indices)
            if 0 <= idx < len(self.items) and self.items[idx].path
        ]
        if not paths:
            return

        drag = QDrag(self)
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(p) for p in paths]
        mime.setUrls(urls)
        mime.setData("application/x-picasa-photo-paths", "\n".join(paths).encode("utf-8"))
        drag.setMimeData(mime)

        # Vignette miniature sous le curseur pendant le glisser
        first_idx = min(self.selected_indices)
        pix = self._get_thumbnail_pixmap(first_idx)
        if pix and not pix.isNull():
            drag_pix = pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            drag.setPixmap(drag_pix)
            drag.setHotSpot(QPoint(drag_pix.width() // 2, drag_pix.height() // 2))

        self._drag_start_pos = None
        self._dragging_item_idx = None
        self._deferred_single_select_idx = None
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le survol des vignettes et en-têtes, la sélection par rectangle élastique et le glisser-déposer.
        EN: Handles hover states on thumbnails and headers, rubber-band marquee selection, and drag initiation.
        """
        pos = event.position().toPoint()

        # 1. Sélection par rectangle élastique (Rubber-band marquee) en cours
        if self._rubber_band_origin is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self._rubber_band_rect = QRect(self._rubber_band_origin, pos).normalized()
            marquee_sel = set(self._rubber_band_base_selection)
            for sec in self.visible_sections:
                if sec.y_start - self.scroll_y > self.height() + 100:
                    break
                if sec.y_start + sec.height - self.scroll_y < -100:
                    continue
                for slot_idx, it_idx in enumerate(sec.item_indices):
                    r = self._get_item_rect(sec, slot_idx)
                    if self._rubber_band_rect.intersects(r):
                        marquee_sel.add(it_idx)
            if marquee_sel != self.selected_indices:
                self.selected_indices = marquee_sel
                if self.selected_indices:
                    self.anchor_index = min(self.selected_indices)
                    self.focus_index = max(self.selected_indices)
                self._pending_selection_emit = True
                if not self._selection_emit_timer.isActive():
                    self._selection_emit_timer.start()
            self.update()
            return

        # 2. Glisser-déposer d'une ou plusieurs vignettes sélectionnées
        if (
            self._drag_start_pos is not None
            and (event.buttons() & Qt.MouseButton.LeftButton)
            and (pos - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance()
        ):
            self._start_thumbnail_drag()
            return

        hovered = None

        def _check_hdr_hover(hdr_y: int, sec_idx: int, sec: AlbumSection) -> Optional[Tuple[str, int]]:
            """
            FR: Détermine quel bouton d'en-tête de section est survolé par le curseur.
            EN: Determines which section header button is currently hovered by the cursor.
            """
            if self._get_slideshow_btn_rect(hdr_y).contains(pos):
                return ("slideshow", sec_idx)
            if not sec.is_person and not sec.is_unnamed:
                if self._get_collage_btn_rect(hdr_y).contains(pos):
                    return ("collage", sec_idx)
                if self._get_movie_btn_rect(hdr_y).contains(pos):
                    return ("movie", sec_idx)
                if self._get_select_star_btn_rect(hdr_y).contains(pos):
                    return ("star", sec_idx)
                if self._get_save_edits_btn_rect(hdr_y).contains(pos):
                    return ("save", sec_idx)
            if self._get_header_rect(hdr_y).contains(pos):
                return ("header", sec_idx)
            return None

        sticky_idx, sticky_y = self._get_sticky_header_info()
        if sticky_idx is not None:
            hovered = _check_hdr_hover(sticky_y, sticky_idx, self.visible_sections[sticky_idx])

        if not hovered:
            for i, sec in enumerate(self.visible_sections):
                if i == sticky_idx:
                    continue
                sec_top = sec.y_start - self.scroll_y
                if 0 <= sec_top <= self.height():
                    hovered = _check_hdr_hover(sec_top, i, sec)
                    if hovered:
                        break

        if hovered != self._hovered_header_btn:
            self._hovered_header_btn = hovered
            self.update()

        # Suivi du survol des boutons ✓ et ✕ sur les vignettes de suggestions
        hovered_sug_btn = None
        cols, _, slot_height, _ = self._get_grid_metrics()
        header_height = 42
        for sec in self.visible_sections:
            sec_top = sec.y_start - self.scroll_y
            if sec_top > self.height():
                break
            sec_bottom = sec_top + sec.height
            if sec_bottom < 0:
                continue
            if getattr(self, "_person_selection_mode", False) or sec.is_person or sec.suggestions:
                if not (sec_top <= pos.y() <= sec_bottom):
                    continue
                rel_y = pos.y() - (sec_top + header_height)
                approx_row = rel_y // slot_height
                first_row = max(0, approx_row - 1)
                last_row = approx_row + 1
                start_slot = first_row * cols
                end_slot = min(len(sec.item_indices), (last_row + 1) * cols)
                for slot_idx in range(start_slot, end_slot):
                    it_idx = sec.item_indices[slot_idx]
                    if it_idx < len(self.items) and getattr(self.items[it_idx], "is_synthetic_suggestion", False):
                        r = self._get_item_rect(sec, slot_idx)
                        btn_ok, btn_no = self._get_suggestion_item_buttons(r)
                        if btn_ok.contains(pos):
                            hovered_sug_btn = (it_idx, "ok")
                            break
                        elif btn_no.contains(pos):
                            hovered_sug_btn = (it_idx, "no")
                            break
            if hovered_sug_btn:
                break

        if hovered_sug_btn != self._hovered_sug_btn:
            self._hovered_sug_btn = hovered_sug_btn
            self.update()

        if (hovered and hovered[0] in ("slideshow", "collage", "movie", "star", "save", "header")) or hovered_sug_btn:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        # Suivi du survol d'une vignette pour l'étoile et les retours visuels
        item_hovered = self._find_item_at(pos)
        if item_hovered != self._hovered_item_idx:
            self._hovered_item_idx = item_hovered
            self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        FR: Finalise la sélection simple différée ou termine le rectangle élastique au relâchement du bouton.
        EN: Finalizes deferred single selection or ends rubber-band marquee selection on mouse release.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if self._deferred_single_select_idx is not None:
                idx = self._deferred_single_select_idx
                self._deferred_single_select_idx = None
                self.selected_indices = {idx}
                self.anchor_index = idx
                self.focus_index = idx
                self.selection_changed.emit(list(self.selected_indices))
                self.update()
            if self._rubber_band_origin is not None or self._rubber_band_rect is not None:
                self._rubber_band_origin = None
                self._rubber_band_rect = None
                self._rubber_band_base_selection.clear()
                if self._pending_selection_emit or self._selection_emit_timer.isActive():
                    self._selection_emit_timer.stop()
                    self._pending_selection_emit = False
                    self.selection_changed.emit(sorted(self.selected_indices))
                self.update()
            self._drag_start_pos = None
            self._dragging_item_idx = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        """
        FR: Réinitialise les états de survol lorsque le curseur quitte la grille de vignettes.
        EN: Resets hover states when the mouse cursor leaves the thumbnail grid.
        """
        need_update = False
        if self._hovered_header_btn is not None:
            self._hovered_header_btn = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            need_update = True
        if self._hovered_item_idx is not None:
            self._hovered_item_idx = None
            need_update = True
        if self._hovered_sug_btn is not None:
            self._hovered_sug_btn = None
            need_update = True
        if need_update:
            self.update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le double-clic sur une vignette pour ouvrir l'éditeur One-Up, valider une suggestion ou nommer un visage.
        Préserve la sélection multiple active si le double-clic porte sur l'une des vignettes sélectionnées
        (Ref: picasa3.exe @ 0x00719A44 -> 0x0056BFD0, `thumbui/scratch` conserve toutes les photos sélectionnées).
        EN: Handles double-clicking a thumbnail to open the One-Up editor, confirm a suggestion, or name a face.
        Preserves the active multi-selection when double-clicking one of the selected thumbnails
        (Ref: picasa3.exe @ 0x00719A44 -> 0x0056BFD0, `thumbui/scratch` retains all selected photos).
        """
        if event.button() == Qt.MouseButton.LeftButton:
            item_idx = self._find_item_at(event.position().toPoint())
            if item_idx is not None and 0 <= item_idx < len(self.items):
                self._deferred_single_select_idx = None
                pre_multi = getattr(self, "_pre_release_multi_selection", None)
                if pre_multi is not None:
                    import time as _time
                    saved_sel, saved_idx, saved_t = pre_multi
                    self._pre_release_multi_selection = None
                    if saved_idx == item_idx and (_time.monotonic() - saved_t) <= 0.75 and len(saved_sel) > 1:
                        self.selected_indices = set(saved_sel)
                        self.focus_index = item_idx
                        self.selection_changed.emit(sorted(self.selected_indices))
                        self.update()
                item = self.items[item_idx]
                if getattr(item, "is_synthetic_suggestion", False):
                    sec = self.visible_sections[0] if self.visible_sections else None
                    if sec:
                        self._confirm_single_suggestion(sec, item)
                    return
                self.item_double_clicked.emit(item_idx)

    def _get_visible_item_indices(self) -> List[int]:
        """
        FR: Retourne la liste ordonnée de tous les index d'éléments actuellement affichés.
        EN: Returns the ordered list of all currently displayed item indices.
        """
        order: List[int] = []
        for sec in self.visible_sections:
            order.extend(sec.item_indices)
        return order

    def _select_range(self, target_idx: int) -> None:
        """
        FR: Sélectionne une plage continue d'éléments entre anchor_index et target_idx
        selon l'ordre visuel des sections affichées (Shift-clic).
        EN: Selects a contiguous range of items between anchor_index and target_idx
        following the visual order of displayed sections (Shift-click).
        """
        order = self._get_visible_item_indices()
        if not order or target_idx not in order:
            self.selected_indices = {target_idx}
            self.anchor_index = target_idx
            return

        if self.anchor_index is None or self.anchor_index not in order:
            self.anchor_index = target_idx
            self.selected_indices = {target_idx}
            return

        idx_start = order.index(self.anchor_index)
        idx_end = order.index(target_idx)
        low = min(idx_start, idx_end)
        high = max(idx_start, idx_end)

        self.selected_indices = set(order[low : high + 1])

    def set_selected_indices(self, indices) -> None:
        """
        FR: Définit l'ensemble des indices sélectionnés et émet selection_changed.
        EN: Sets the selected item indices and emits selection_changed.
        """
        self.selected_indices = {int(i) for i in indices if 0 <= int(i) < len(self.items)}
        if self.selected_indices:
            self.anchor_index = min(self.selected_indices)
            self.focus_index = self.anchor_index
        else:
            self.anchor_index = None
            self.focus_index = None
        self.update()
        self.selection_changed.emit(sorted(self.selected_indices))

    def scroll_to_index(self, item_idx: int) -> None:
        """
        FR: Alias de ensure_visible pour faire défiler jusqu'à un index.
        EN: Alias for ensure_visible to scroll the view to a specific item index.
        """
        self.ensure_visible(item_idx)

    def select_all(self) -> None:
        """
        FR: Sélectionne toutes les vignettes actuellement visibles (Ctrl+A).
        EN: Selects all currently visible thumbnails (Ctrl+A).
        """
        order = self._get_visible_item_indices()
        self.selected_indices = set(order)
        if order:
            self.anchor_index = order[0]
            self.focus_index = order[-1]
        self.update()
        self.selection_changed.emit(sorted(self.selected_indices))

    def ensure_visible(self, item_idx: int) -> None:
        """
        FR: Fait défiler la vue pour que l'élément soit entièrement visible.
        EN: Scrolls the viewport so that the specified item is fully visible.
        """
        for sec in self.visible_sections:
            if item_idx in sec.item_indices:
                slot_idx = sec.item_indices.index(item_idx)
                r = self._get_item_rect(sec, slot_idx)
                if r.top() < 40:
                    delta = r.top() - 40
                    new_val = max(0, min(self.scrollbar.max_val, self.scroll_y + delta))
                    self.scrollbar.set_value(new_val)
                    self.scroll_y = new_val
                elif r.bottom() > self.height() - 20:
                    delta = r.bottom() - (self.height() - 20)
                    new_val = max(0, min(self.scrollbar.max_val, self.scroll_y + delta))
                    self.scrollbar.set_value(new_val)
                    self.scroll_y = new_val
                break

    def _get_column_count(self) -> int:
        """
        FR: Calcule le nombre de colonnes de vignettes visibles.
        EN: Computes the number of visible thumbnail columns.
        """
        available_width = max(100, self.width() - self.scrollbar.width() - (self.style.alayout_gutter * 2))
        slot_width = self.thumb_base_size + self.style.alayout_thumbGutterX
        return max(1, available_width // max(1, slot_width))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        FR: Gère les raccourcis clavier de navigation et de sélection (flèches, Ctrl+A, Échap, Entrée).
        EN: Handles keyboard navigation and selection shortcuts (arrow keys, Ctrl+A, Escape, Enter).
        """
        key = event.key()
        modifiers = event.modifiers()
        order = self._get_visible_item_indices()

        if not order:
            super().keyPressEvent(event)
            return

        # Ctrl+A : Tout sélectionner
        if key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.select_all()
            return

        # Escape : Désélectionner
        if key == Qt.Key.Key_Escape:
            self.selected_indices.clear()
            self.anchor_index = None
            self.focus_index = None
            self.update()
            self.selection_changed.emit([])
            return

        # Enter / Return : Ouvrir la photo sélectionnée
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.selected_indices:
                first_idx = next(iter(sorted(self.selected_indices)))
                if 0 <= first_idx < len(self.items):
                    self.item_double_clicked.emit(first_idx)
            return

        # Déplacement avec les touches fléchées
        curr_idx: Optional[int] = None
        if self.focus_index is not None and self.focus_index in order:
            curr_idx = self.focus_index
        elif self.anchor_index is not None and self.anchor_index in order:
            curr_idx = self.anchor_index
        elif self.selected_indices:
            curr_idx = next(iter(sorted(self.selected_indices)))
        elif order:
            curr_idx = order[0]

        if curr_idx is None or curr_idx not in order:
            super().keyPressEvent(event)
            return

        pos_in_order = order.index(curr_idx)
        cols = self._get_column_count()
        new_pos = pos_in_order

        if key == Qt.Key.Key_Right:
            new_pos = min(len(order) - 1, pos_in_order + 1)
        elif key == Qt.Key.Key_Left:
            new_pos = max(0, pos_in_order - 1)
        elif key == Qt.Key.Key_Down:
            new_pos = min(len(order) - 1, pos_in_order + cols)
        elif key == Qt.Key.Key_Up:
            new_pos = max(0, pos_in_order - cols)
        elif key == Qt.Key.Key_Home:
            new_pos = 0
        elif key == Qt.Key.Key_End:
            new_pos = len(order) - 1
        else:
            super().keyPressEvent(event)
            return

        target_item = order[new_pos]
        self.focus_index = target_item
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            if self.anchor_index is None:
                self.anchor_index = curr_idx
            self._select_range(target_item)
        else:
            self.selected_indices = {target_item}
            self.anchor_index = target_item

        self.ensure_visible(target_item)
        self.update()
        self.selection_changed.emit(list(self.selected_indices))

    def _open_suggestion_dialog(self, item: ThumbnailItem) -> None:
        """
        FR: Ouvre un dialogue de confirmation / rejet pour une suggestion de visage.
        EN: Opens a confirmation / rejection dialog for a face suggestion.
        Ref: picasa3.exe @ faceheaderpanel/confirmsel, removesel
        """
        if not self.db or not getattr(self.db, "face_manager", None):
            return

        sug_found = None
        for s in self.db.face_manager.get_all_suggestions():
            if s.photo_path == item.path and (item.face_rect is None or _face_overlap(s.face_rect, item.face_rect) >= 0.5):
                sug_found = s
                break

        contact_name = sug_found.contact_name if sug_found else (self.visible_sections[0].name if self.visible_sections else "cette personne")
        box = QMessageBox(self)
        box.setWindowTitle("Confirmer la suggestion de visage")
        box.setText(f"Confirmer que ce visage correspond bien à {contact_name} ?")
        btn_yes = box.addButton("✔ Valider", QMessageBox.ButtonRole.AcceptRole)
        btn_no = box.addButton("✘ Rejeter", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = box.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked == btn_yes and sug_found:
            self.db.face_manager.confirm_suggestion(sug_found)
            if self.visible_sections and self.visible_sections[0].contact_id:
                cid = self.visible_sections[0].contact_id
                cluster = self.db.face_manager.get_person(cid)
                if cluster:
                    self.filter_by_person(cid, cluster.name, cluster.photo_indices, only_suggestions=self.visible_sections[0].only_suggestions)
        elif clicked == btn_no and sug_found:
            self.db.face_manager.reject_suggestion(sug_found)
            if self.visible_sections and self.visible_sections[0].contact_id:
                cid = self.visible_sections[0].contact_id
                cluster = self.db.face_manager.get_person(cid)
                if cluster:
                    self.filter_by_person(cid, cluster.name, cluster.photo_indices, only_suggestions=self.visible_sections[0].only_suggestions)

    def _open_name_unnamed_face_dialog(self, item: ThumbnailItem) -> None:
        """
        FR: Ouvre le dialogue pour nommer, réassigner ou supprimer un visage sans nom.
        EN: Opens the dialog to name, reassign, or delete an unnamed face.
        Ref: picasa3.exe @ unknownfaceheaderpanel/addname (0x008A13B8), ignore
        """
        if not item.face_rect or not self.db or not getattr(self.db, "face_manager", None):
            return
        from picasa_py.ui.name_face_dialog import PicasaNameFaceDialog
        existing_names = [p.name for p in self.db.face_manager.get_people()]
        dlg = PicasaNameFaceDialog(
            face_rect=item.face_rect,
            photo_path=item.path,
            existing_names=existing_names,
            current_name="",
            is_new_face=True,
            parent=self.window(),
        )
        if dlg.exec():
            if dlg.is_delete_requested():
                self.db.face_manager.remove_face(
                    item.path, item.face_rect, db_idx=item.index if item.index >= 0 else None
                )
            else:
                cname = dlg.get_contact_name()
                if cname:
                    self.db.face_manager.add_face(
                        item.path, item.face_rect, cname, db_idx=item.index if item.index >= 0 else None
                    )
            unnamed = self.db.face_manager.unnamed_faces
            self.filter_by_unnamed_faces(unnamed)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        FR: Gestion du clic droit fidèle à picasa3.exe (Ref: 0x005D41F4, "lb_rightclick").
        EN: Right-click context menu handler faithful to picasa3.exe (Ref: 0x005D41F4, "lb_rightclick").
        """
        pos = event.pos()

        # 1. Clic sur l'en-tête collant (sticky)
        sticky_idx, sticky_y = self._get_sticky_header_info()
        if sticky_idx is not None:
            sec = self.visible_sections[sticky_idx]
            if self._get_header_rect(sticky_y).contains(pos):
                self._show_section_context_menu(sec, event.globalPos())
                return

        # 2. Clic sur un en-tête naturel
        for i, sec in enumerate(self.visible_sections):
            if i == sticky_idx:
                continue
            sec_top = sec.y_start - self.scroll_y
            if 0 <= sec_top <= self.height():
                if self._get_header_rect(sec_top).contains(pos):
                    self._show_section_context_menu(sec, event.globalPos())
                    return

        # 3. Clic sur une vignette individuelle
        item_idx = self._find_item_at(pos)
        if item_idx is not None:
            if item_idx not in self.selected_indices:
                self.selected_indices = {item_idx}
                self.update()
                self.selection_changed.emit(list(self.selected_indices))

            selected_paths = [
                self.items[i].path for i in sorted(self.selected_indices)
                if i < len(self.items) and self.items[i].path
            ]
            if selected_paths:
                is_alb = bool(self.current_folder_filter and not os.path.exists(self.current_folder_filter))
                # Vérifier si l'élément cliqué appartient à une section de personne
                sec_contact_id = None
                item_face_rect = self.items[item_idx].face_rect if item_idx < len(self.items) else None
                for sec in self.visible_sections:
                    if item_idx in sec.item_indices and sec.is_person:
                        sec_contact_id = sec.contact_id
                        break
                if not sec_contact_id and getattr(self, "current_person_id", None):
                    sec_contact_id = self.current_person_id

                is_sug_item = getattr(self.items[item_idx], "is_synthetic_suggestion", False) if item_idx < len(self.items) else False
                sug_obj = None
                if is_sug_item and self.db and getattr(self.db, "face_manager", None):
                    for s in self.db.face_manager.get_all_suggestions():
                        if s.photo_path == self.items[item_idx].path:
                            sug_obj = s
                            break

                PicasaContextMenuBuilder.show_photo_context_menu(
                    self,
                    event.globalPos(),
                    selected_paths,
                    db=self.db,
                    is_in_album=is_alb,
                    main_win=self.window(),
                    contact_id=sec_contact_id,
                    face_rect=item_face_rect,
                    suggestion=sug_obj,
                )
            return

        # 4. Clic dans le vide de la grille -> Menu du dossier actuel si filtré
        if self.current_folder_filter and os.path.isdir(self.current_folder_filter):
            PicasaContextMenuBuilder.show_folder_context_menu(
                self, event.globalPos(), self.current_folder_filter, db=self.db, main_win=self.window()
            )

    def _show_section_context_menu(self, sec: AlbumSection, global_pos: QPoint) -> None:
        """
        FR: Affiche le menu contextuel correspondant à une section d'album/dossier/personne.
        EN: Displays the context menu corresponding to an album, folder, or person section.
        """
        main_win = self.window()
        if sec.is_person:
            PicasaContextMenuBuilder.show_person_context_menu(
                self, global_pos, sec.contact_id or "", sec.name, db=self.db, main_win=main_win
            )
        elif not os.path.exists(sec.folder_path):
            PicasaContextMenuBuilder.show_album_context_menu(
                self, global_pos, sec.name, db=self.db, main_win=main_win
            )
        else:
            PicasaContextMenuBuilder.show_folder_context_menu(
                self, global_pos, sec.folder_path, db=self.db, main_win=main_win
            )

    # -------------------------------------------------------------------------
    # FR: Rendu Graphique (QPainter) / EN: Custom QPainter Rendering
    # -------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine le fond de la photothèque, les en-têtes (naturels et épinglés), les vignettes visibles et le rectangle élastique.
        EN: Paints the library background, section headers (inline and sticky), visible thumbnails, and rubber-band marquee.
        """
        painter = QPainter(self)
        self._in_paint_event = True
        self._paint_start_ts = time.perf_counter()
        self._paint_sync_decodes = 0
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Fond de la photothèque (uni ou dégradé diagonal)
            grid_start = self.style.grid_bgcolor
            grid_end = getattr(self.style, "grid_bgcolor_end", grid_start)
            if grid_start != grid_end:
                bg_grad = QLinearGradient(0.0, 0.0, float(self.width()), float(self.height()))
                bg_grad.setColorAt(0.0, grid_start)
                bg_grad.setColorAt(1.0, grid_end)
                painter.fillRect(self.rect(), QBrush(bg_grad))
            else:
                painter.fillRect(self.rect(), grid_start)

            viewport_h = self.height()
            sticky_idx, sticky_y = self._get_sticky_header_info()
            cols, _, slot_height, _ = self._get_grid_metrics()
            header_height = 42

            # 1. Rendu des en-têtes naturels et de l'ensemble des vignettes
            for i, sec in enumerate(self.visible_sections):
                sec_top = sec.y_start - self.scroll_y
                sec_bottom = sec_top + sec.height

                if sec_bottom < -10:
                    continue
                if sec_top > viewport_h + 10:
                    break

                # Dessiner l'en-tête naturel si ce n'est pas la section actuellement épinglée
                if i != sticky_idx and sec_top > -45 and sec_top < viewport_h:
                    self._draw_section_header(painter, sec, sec_top, is_sticky=False, sec_idx=i)

                # Dessiner uniquement la tranche de lignes visible dans le viewport (calcul direct O(1))
                rel_top = -20 - (sec_top + header_height)
                rel_bottom = (viewport_h + 20) - (sec_top + header_height)
                first_row = max(0, rel_top // slot_height - 1)
                last_row = max(0, rel_bottom // slot_height + 1)
                start_slot = first_row * cols
                end_slot = min(len(sec.item_indices), (last_row + 1) * cols)
                for slot_idx in range(start_slot, end_slot):
                    item_idx = sec.item_indices[slot_idx]
                    r = self._get_item_rect(sec, slot_idx)
                    if r.bottom() < -20:
                        continue
                    if r.top() > viewport_h + 20:
                        break

                    self._draw_thumbnail(painter, r, item_idx, sec)

            # 2. Rendu de l'en-tête épinglé (Sticky Header) AU-DESSUS des vignettes
            if sticky_idx is not None:
                sticky_sec = self.visible_sections[sticky_idx]
                self._draw_section_header(painter, sticky_sec, sticky_y, is_sticky=True, sec_idx=sticky_idx)

            # 3. Rendu du rectangle élastique de sélection (Rubber-band marquee, Ref: thumbsel_color1)
            if self._rubber_band_rect is not None and not self._rubber_band_rect.isNull():
                rb_col = self.style.thumbsel_color1
                fill_col = QColor(rb_col.red(), rb_col.green(), rb_col.blue(), 45)
                painter.setPen(QPen(rb_col, 1))
                painter.setBrush(fill_col)
                painter.drawRect(self._rubber_band_rect)

        finally:
            self._in_paint_event = False
            painter.end()

    def _draw_section_header(
        self, painter: QPainter, sec: AlbumSection, y: int, is_sticky: bool = False, sec_idx: int = -1
    ) -> None:
        """
        FR: Dessine l'en-tête d'album emblématique de Picasa (icône dossier/personne, titre, date, boutons d'action).
        Utilise la palette officielle de constants.ui (alabel_fldrcol=#e2e2e2, alabel_fldrhicol=#f2f2f2,
        alist_stickycolor=#EAE7DC, alayout_titleFont=Georgia, alayout_titleColor=#634B45).
        EN: Draws Picasa's iconic section header (folder/person icon, title, date, action buttons).
        Uses the official constants.ui palette (alabel_fldrcol=#e2e2e2, alabel_fldrhicol=#f2f2f2,
        alist_stickycolor=#EAE7DC, alayout_titleFont=Georgia, alayout_titleColor=#634B45).
        Ref: picasa3.exe @ albumheader (0x00C968A0), runtime/constants.ui [Picasa2]
        Ref: picasa3.exe @ HEADERPANELTEXT_FR.XML (play, create_collage, create_movie, select_star, save_edits)
        Ref: picasa3.exe @ faceheaderpanel/face_zoom, picture_zoom
        Ref: picasa3.exe @ unknownfaceheaderpanel/cluster, addname
        """
        header_w = self.width() - self.scrollbar.width()
        is_hdr_hovered = self._hovered_header_btn is not None and self._hovered_header_btn[1] == sec_idx

        is_dark = getattr(self.style, "is_dark", False)
        sep_col = self.style.splitter_color if is_dark else QColor("#BFB9A8" if is_sticky else "#C8C8C8")

        if is_sticky:
            # Fond beige/crème épinglé authentique de constants.ui (alist_stickycolor=#EAE7DC) ou dégradé
            st_start = self.style.alist_stickycolor
            st_end = getattr(self.style, "alist_stickycolor_end", st_start)
            sticky_rect = QRect(0, y, header_w, 38)
            if st_start != st_end:
                st_grad = QLinearGradient(0.0, float(y), float(header_w), float(y))
                st_grad.setColorAt(0.0, st_start)
                st_grad.setColorAt(1.0, st_end)
                painter.fillRect(sticky_rect, QBrush(st_grad))
            else:
                painter.fillRect(sticky_rect, st_start)
            painter.setPen(sep_col)
            painter.drawLine(0, y + 37, header_w, y + 37)
            # Ombre portée douce sous l'en-tête flottant
            painter.fillRect(QRect(0, y + 38, header_w, 3), QColor(0, 0, 0, 45))
            painter.fillRect(QRect(0, y + 41, header_w, 2), QColor(0, 0, 0, 20))
        else:
            # Fond d'en-tête clair authentique (alabel_fldrcol=#e2e2e2, alabel_fldrhicol=#f2f2f2) ou dégradé
            bg_col = self.style.alabel_fldrhicol if is_hdr_hovered else self.style.alabel_fldrcol
            bg_end = (
                getattr(self.style, "alabel_fldrhicol_end", bg_col)
                if is_hdr_hovered
                else getattr(self.style, "alabel_fldrcol_end", bg_col)
            )
            header_rect = QRect(6, y + 1, header_w - 12, 36)
            if bg_col != bg_end:
                hdr_grad = QLinearGradient(6.0, float(y + 1), float(header_w - 6), float(y + 1))
                hdr_grad.setColorAt(0.0, bg_col)
                hdr_grad.setColorAt(1.0, bg_end)
                painter.fillRect(header_rect, QBrush(hdr_grad))
            else:
                painter.fillRect(header_rect, bg_col)
            painter.setPen(sep_col)
            painter.drawLine(6, y, header_w - 6, y)
            painter.drawLine(6, y + 37, header_w - 6, y + 37)

        icon_x = 18
        icon_y = y + 11
        painter.setPen(Qt.PenStyle.NoPen)
        if sec.is_unnamed:
            # Icône point d'interrogation / visage sans nom
            painter.setBrush(QColor("#D35400"))
            painter.drawEllipse(QRect(icon_x + 3, icon_y, 10, 10))
            painter.drawRoundedRect(QRect(icon_x, icon_y + 8, 16, 9), 3, 3)
            painter.setFont(QFont("Tahoma", 7, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRect(icon_x + 3, icon_y, 10, 10), Qt.AlignmentFlag.AlignCenter, "?")
        elif sec.is_person:
            # Avatar circulaire de la personne si disponible, sinon icône personne stylisée
            avatar_drawn = False
            if sec.contact_id and self.db and getattr(self.db, "face_manager", None):
                av = self.db.face_manager.get_person_avatar(
                    sec.contact_id, size=22, allow_disk_fallback=not self._in_paint_event
                )
                if av and not av.isNull():
                    painter.drawPixmap(icon_x - 2, icon_y - 2, 22, 22, av)
                    avatar_drawn = True

            if not avatar_drawn:
                painter.setBrush(QColor("#E67E22"))
                painter.drawEllipse(QRect(icon_x + 3, icon_y, 10, 10))
                painter.drawRoundedRect(QRect(icon_x, icon_y + 8, 16, 9), 3, 3)
        elif sec.is_album:
            # Icône album virtuel Picasa
            painter.setBrush(QColor("#4A7EBB"))
            painter.drawRoundedRect(QRect(icon_x, icon_y + 1, 16, 14), 2, 2)
            painter.setBrush(QColor("#8EB4E3"))
            painter.drawRect(QRect(icon_x + 3, icon_y + 3, 3, 10))
        elif sec.is_search:
            # Icône loupe recherche
            painter.setPen(QPen(QColor("#3879D9"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRect(icon_x + 1, icon_y + 1, 9, 9))
            painter.drawLine(icon_x + 8, icon_y + 8, icon_x + 15, icon_y + 15)
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            # Icône de dossier Picasa (pictogramme stylisé)
            painter.setBrush(QColor("#3E82B8"))
            painter.drawRoundedRect(QRect(icon_x, icon_y + 3, 16, 12), 2, 2)
            painter.drawRoundedRect(QRect(icon_x + 1, icon_y, 7, 5), 1, 1)

        # Titre de l'album / dossier (Georgia gras #634B45, Ref: constants.ui alayout_titleFont / alayout_titleColor)
        title_x = icon_x + 24
        painter.setFont(QFont(self.style.alayout_titleFont, 11, QFont.Weight.Bold))
        painter.setPen(self.style.alayout_titleColor)
        painter.drawText(title_x, y + 24, sec.name)

        # Métadonnées : Date et nombre de photos (Georgia, Ref: constants.ui alayout_bodyFont)
        metrics = painter.fontMetrics()
        title_width = metrics.horizontalAdvance(sec.name)

        date_x = title_x + title_width + 14
        count_str = f"{len(sec.item_indices)} photos"
        meta_str = f"—   {sec.date_str}   •   {count_str}" if sec.date_str else f"—   {count_str}"

        painter.setFont(QFont(self.style.alayout_bodyFont, 9))
        painter.setPen(getattr(self.style, "alayout_subtitleColor", QColor("#5C534E")))
        painter.drawText(date_x, y + 24, meta_str)

        btn_s = self.style.topbar_btn_bg_start
        btn_e = self.style.topbar_btn_bg_end
        btn_txt_norm = self.style.topbar_text_color
        btn_brd_norm = self.style.topbar_btn_border
        accent_col = getattr(self.style, "accent_color", QColor("#3879D9"))
        accent_end = getattr(self.style, "accent_grad_end", accent_col)

        def _make_btn_brush(r: QRect, hovered: bool = False, is_accent: bool = False) -> QBrush:
            if is_accent:
                if accent_col != accent_end:
                    g = QLinearGradient(float(r.left()), float(r.top()), float(r.right()), float(r.bottom()))
                    g.setColorAt(0.0, accent_col.lighter(112) if hovered else accent_col)
                    g.setColorAt(1.0, accent_end.lighter(112) if hovered else accent_end)
                    return QBrush(g)
                return QBrush(accent_col.lighter(112) if hovered else accent_col)
            c1 = btn_s.lighter(115) if hovered else btn_s
            c2 = btn_e.lighter(115) if hovered else btn_e
            if c1 != c2:
                g = QLinearGradient(float(r.left()), float(r.top()), float(r.left()), float(r.bottom()))
                g.setColorAt(0.0, c1)
                g.setColorAt(1.0, c2)
                return QBrush(g)
            return QBrush(c1)

        if sec.is_unnamed:
            if sec.cluster_faces is not None:
                # 1. Bouton "Développer les groupes" (Ref: unknownfaceheaderpanel/showall)
                btn_ungroup = self._get_ungroup_action_btn_rect(y)
                painter.setPen(QPen(btn_brd_norm, 1))
                painter.setBrush(_make_btn_brush(btn_ungroup))
                painter.drawRoundedRect(btn_ungroup, 3, 3)
                painter.setFont(QFont("Tahoma", 8, QFont.Weight.Normal))
                painter.setPen(btn_txt_norm)
                painter.drawText(btn_ungroup, Qt.AlignmentFlag.AlignCenter, "⊞ Développer les groupes")

                # 2. Bouton "Ajouter un nom" pour ce groupe (Ref: unknownfaceheaderpanel/addname)
                btn_cluster = self._get_cluster_action_btn_rect(y)
                painter.setPen(QPen(accent_col.darker(120), 1))
                painter.setBrush(_make_btn_brush(btn_cluster, is_accent=True))
                painter.drawRoundedRect(btn_cluster, 3, 3)
                painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(btn_cluster, Qt.AlignmentFlag.AlignCenter, "➕ Ajouter un nom")

                # 3. Bouton "Ignorer" pour ce groupe (Ref: unknownfaceheaderpanel/ignore)
                btn_ign = self._get_ignore_action_btn_rect(y)
                painter.setPen(QPen(QColor("#8A4040") if is_dark else QColor("#B08080"), 1))
                painter.setBrush(QColor("#4A262A") if is_dark else QColor("#FCE8E8"))
                painter.drawRoundedRect(btn_ign, 3, 3)
                painter.setFont(QFont("Tahoma", 8, QFont.Weight.Normal))
                painter.setPen(QColor("#FF9999") if is_dark else QColor("#902020"))
                painter.drawText(btn_ign, Qt.AlignmentFlag.AlignCenter, "✖ Ignorer")
            else:
                # Mode non groupé : Bouton "Grouper par visage" (Ref: unknownfaceheaderpanel/cluster)
                btn_cluster = self._get_cluster_action_btn_rect(y)
                is_working = getattr(self, "_cluster_worker", None) is not None and self._cluster_worker.isRunning()
                if is_working:
                    painter.setPen(QPen(btn_brd_norm, 1))
                    painter.setBrush(_make_btn_brush(btn_cluster))
                    painter.drawRoundedRect(btn_cluster, 3, 3)
                    painter.setFont(QFont("Tahoma", 8, QFont.Weight.Normal))
                    painter.setPen(btn_txt_norm)
                    painter.drawText(btn_cluster, Qt.AlignmentFlag.AlignCenter, "⏳ Regroupement...")
                else:
                    painter.setPen(QPen(accent_col.darker(120), 1))
                    painter.setBrush(_make_btn_brush(btn_cluster, is_accent=True))
                    painter.drawRoundedRect(btn_cluster, 3, 3)
                    painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold))
                    painter.setPen(QColor("#FFFFFF"))
                    painter.drawText(btn_cluster, Qt.AlignmentFlag.AlignCenter, "👥 Grouper par visage")
        elif sec.is_person:
            btn_fz = self._get_face_zoom_btn_rect(y)
            btn_pz = self._get_picture_zoom_btn_rect(y)

            # Bouton Zoom visage
            if sec.face_zoom:
                painter.setPen(QPen(accent_col.darker(120), 1))
                painter.setBrush(_make_btn_brush(btn_fz, is_accent=True))
            else:
                painter.setPen(QPen(btn_brd_norm, 1))
                painter.setBrush(_make_btn_brush(btn_fz))
            painter.drawRoundedRect(btn_fz, 3, 3)
            painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold if sec.face_zoom else QFont.Weight.Normal))
            painter.setPen(QColor("#FFFFFF") if sec.face_zoom else btn_txt_norm)
            painter.drawText(btn_fz, Qt.AlignmentFlag.AlignCenter, "👤 Visages")

            # Bouton Photo entière
            if not sec.face_zoom:
                painter.setPen(QPen(accent_col.darker(120), 1))
                painter.setBrush(_make_btn_brush(btn_pz, is_accent=True))
            else:
                painter.setPen(QPen(btn_brd_norm, 1))
                painter.setBrush(_make_btn_brush(btn_pz))
            painter.drawRoundedRect(btn_pz, 3, 3)
            painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold if not sec.face_zoom else QFont.Weight.Normal))
            painter.setPen(QColor("#FFFFFF") if not sec.face_zoom else btn_txt_norm)
            painter.drawText(btn_pz, Qt.AlignmentFlag.AlignCenter, "🖼️ Photos")

            # Boutons pour les suggestions : Filtre suggestions + Tout valider
            if sec.suggestions:
                btn_sf = self._get_sug_filter_btn_rect(y)
                if sec.only_suggestions:
                    painter.setPen(QPen(QColor("#D97706"), 1))
                    painter.setBrush(QColor("#F59E0B"))
                    painter.drawRoundedRect(btn_sf, 3, 3)
                    painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold))
                    painter.setPen(QColor("#FFFFFF"))
                    painter.drawText(btn_sf, Qt.AlignmentFlag.AlignCenter, f"💡 Suggestions ({len(sec.suggestions)}) ✓")
                else:
                    painter.setPen(QPen(QColor("#8A6D3B") if is_dark else QColor("#C09853"), 1))
                    painter.setBrush(QColor("#3E3524") if is_dark else QColor("#FCF8E3"))
                    painter.drawRoundedRect(btn_sf, 3, 3)
                    painter.setFont(QFont("Tahoma", 8, QFont.Weight.Normal))
                    painter.setPen(QColor("#FCD34D") if is_dark else QColor("#8A6D3B"))
                    painter.drawText(btn_sf, Qt.AlignmentFlag.AlignCenter, f"💡 Suggestions ({len(sec.suggestions)})")

                btn_cs = self._get_confirm_sug_btn_rect(y)
                painter.setPen(QPen(QColor("#2B8A4B"), 1))
                painter.setBrush(QColor("#2E7D32"))
                painter.drawRoundedRect(btn_cs, 3, 3)
                painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold))
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(btn_cs, Qt.AlignmentFlag.AlignCenter, "✔ Tout confirmer")

                has_sel_sug = any(getattr(self.items[i], "is_synthetic_suggestion", False) for i in self.selected_indices if i < len(self.items))
                if has_sel_sug:
                    btn_csel = self._get_confirm_sel_btn_rect(y)
                    painter.setPen(QPen(QColor("#2B8A4B"), 1))
                    painter.setBrush(QColor("#2E7D32"))
                    painter.drawRoundedRect(btn_csel, 3, 3)
                    painter.setFont(QFont("Tahoma", 8, QFont.Weight.Bold))
                    painter.setPen(QColor("#FFFFFF"))
                    painter.drawText(btn_csel, Qt.AlignmentFlag.AlignCenter, "✔ Confirmer")

                    btn_rsel = self._get_remove_sel_btn_rect(y)
                    painter.setPen(QPen(QColor("#8A2B2B"), 1))
                    painter.setBrush(QColor("#C62828"))
                    painter.drawRoundedRect(btn_rsel, 3, 3)
                    painter.setFont(QFont("Tahoma", 8, QFont.Weight.Normal))
                    painter.setPen(QColor("#FFFFFF"))
                    painter.drawText(btn_rsel, Qt.AlignmentFlag.AlignCenter, "✖ Supprimer")
        else:
            # Boutons d'action d'en-tête d'album/dossier (Ref: HEADERPANELTEXT_FR.XML)
            def _draw_hdr_action_btn(rect: QRect, label: str, btn_key: str) -> None:
                """
                FR: Dessine un bouton d'action standard (Enregistrer, Favoris, Film, Montage) dans l'en-tête.
                EN: Draws a standard action button (Save, Starred, Movie, Collage) inside the section header.
                """
                hov = (self._hovered_header_btn == (btn_key, sec_idx))
                painter.setPen(QPen(accent_col if hov else btn_brd_norm, 1))
                painter.setBrush(_make_btn_brush(rect, hovered=hov))
                painter.drawRoundedRect(rect, 3, 3)
                painter.setFont(QFont(self.style.alabel_buttfont_win, 8, QFont.Weight.Bold if hov else QFont.Weight.Normal))
                painter.setPen(btn_txt_norm)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

            _draw_hdr_action_btn(self._get_save_edits_btn_rect(y), "💾", "save")
            _draw_hdr_action_btn(self._get_select_star_btn_rect(y), "★", "star")
            _draw_hdr_action_btn(self._get_movie_btn_rect(y), "🎬 Film", "movie")
            _draw_hdr_action_btn(self._get_collage_btn_rect(y), "⊞ Montage", "collage")

        # Bouton Diaporama / Lecture à droite (Ref: headerpanel/play)
        btn_rect = self._get_slideshow_btn_rect(y)
        is_hovered = (self._hovered_header_btn == ("slideshow", sec_idx))
        painter.setPen(QPen(accent_col if is_hovered else btn_brd_norm, 1))
        painter.setBrush(_make_btn_brush(btn_rect, hovered=is_hovered))
        painter.drawRoundedRect(btn_rect, 3, 3)

        # Triangle lecture vert Picasa
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4CAF50") if is_hovered else QColor("#5CB85C"))
        play_poly = QPolygon([
            QPoint(btn_rect.x() + 10, y + 13),
            QPoint(btn_rect.x() + 18, y + 19),
            QPoint(btn_rect.x() + 10, y + 25),
        ])
        painter.drawPolygon(play_poly)

        painter.setFont(QFont(self.style.alabel_buttfont_win, 8, QFont.Weight.Bold))
        painter.setPen(btn_txt_norm)
        painter.drawText(btn_rect.x() + 24, y + 23, "Diaporama")

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique dynamiquement le thème de couleur PicasaStyle à la grille de vignettes.
        EN: Dynamically applies the PicasaStyle color theme to the thumbnail grid.
        """
        self.style = style
        if hasattr(self, "scrollbar") and self.scrollbar:
            self.scrollbar.apply_style(style)
        self.update()


    def _draw_thumbnail(
        self, painter: QPainter, rect: QRect, item_idx: int, sec: Optional[AlbumSection] = None
    ) -> None:
        """
        FR: Dessine une carte de vignette complète (ombre, image, cadre de sélection, étoile, badge vidéo et légende).
        EN: Draws a complete thumbnail card (drop shadow, image, selection border, star, video badge, and caption).
        """
        item = self.items[item_idx]
        is_selected = item_idx in self.selected_indices
        is_hovered = (self._hovered_item_idx == item_idx)

        # Ombre portée
        shadow_rect = rect.adjusted(3, 3, 3, 3)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 55 if getattr(self.style, "is_dark", False) else 35))

        # Cadre de la photo
        painter.fillRect(rect, getattr(self.style, "thumb_card_bgcolor", QColor("#FFFFFF")))

        # Image de vignette (cadrage visage ou photo complète)
        is_face_mode = bool(sec and sec.is_person and sec.face_zoom)
        is_person_parent = bool(sec and sec.is_person and not sec.face_zoom)
        if is_face_mode and sec is not None:
            pix = self._get_face_pixmap(item_idx, sec.contact_id)
        elif is_person_parent:
            pix = self._get_parent_photo_pixmap(item_idx)
        else:
            pix = self._get_thumbnail_pixmap(item_idx)

        if pix and not pix.isNull():
            target_rect = rect.adjusted(4, 4, -4, -4)
            tw, th = target_rect.width(), target_rect.height()
            if self._is_zooming_thumbs:
                fit_sz = pix.size().scaled(target_rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
                draw_x = target_rect.x() + (tw - fit_sz.width()) // 2
                draw_y = target_rect.y() + (th - fit_sz.height()) // 2
                painter.drawPixmap(QRect(draw_x, draw_y, fit_sz.width(), fit_sz.height()), pix)
            else:
                if not is_face_mode:
                    cache_idx = item.parent_item_idx if is_person_parent else item_idx
                    scale_key = (cache_idx, tw, th)
                else:
                    scale_key = (-item_idx - 1, tw, th)
                scaled = self._scaled_pixmap_cache.get(scale_key)
                if scaled is None:
                    scaled = pix.scaled(
                        target_rect.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    if len(self._scaled_pixmap_cache) >= 1500:
                        self._scaled_pixmap_cache.clear()
                    self._scaled_pixmap_cache[scale_key] = scaled
                draw_x = target_rect.x() + (tw - scaled.width()) // 2
                draw_y = target_rect.y() + (th - scaled.height()) // 2
                painter.drawPixmap(draw_x, draw_y, scaled)
        else:
            painter.fillRect(rect.adjusted(4, 4, -4, -4), QColor("#D0D0D0"))

        # Bordures de sélection Picasa (Bleu externe ou dégradé, Blanc interne)
        if is_selected:
            sel_c1 = self.style.thumbsel_color1
            sel_end = getattr(self.style, "accent_grad_end", sel_c1)
            if sel_c1 != sel_end and getattr(self.style, "accent_color", sel_c1) != sel_end:
                sel_grad = QLinearGradient(float(rect.left()), float(rect.top()), float(rect.right()), float(rect.bottom()))
                sel_grad.setColorAt(0.0, sel_c1)
                sel_grad.setColorAt(1.0, sel_end)
                pen_blue = QPen(QBrush(sel_grad), 2)
            else:
                pen_blue = QPen(sel_c1, 2)
            painter.setPen(pen_blue)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(-2, -2, 2, 2))

            pen_white = QPen(self.style.thumbsel_color2, 1)
            painter.setPen(pen_white)
            painter.drawRect(rect)

        # Étoile dorée Picasa si la photo est favorite (Ref: star=yes, ID_PICTURE_STAR)
        if item.starred or is_hovered:
            star_box = QRect(rect.right() - 20, rect.bottom() - 20, 18, 18)
            cx, cy = star_box.center().x(), star_box.center().y()
            r_out, r_in = 7.5, 3.2
            pts = []
            for si in range(10):
                angle = si * math.pi / 5.0 - math.pi / 2.0
                r = r_out if si % 2 == 0 else r_in
                pts.append(QPoint(int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))))

            if item.starred:
                painter.setPen(QPen(QColor("#B8860B"), 1))
                painter.setBrush(QColor("#FFD700"))
                painter.drawPolygon(QPolygon(pts))
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
                painter.setBrush(QColor(0, 0, 0, 70))
                painter.drawPolygon(QPolygon(pts))

        # Badge vidéo Picasa (Ref: picasa3.exe @ movie badge / DirEntry.IsMovie)
        if item.is_video:
            badge_rect = QRect(rect.left() + 6, rect.bottom() - 20, 22, 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRoundedRect(badge_rect, 3, 3)

            painter.setBrush(QColor("#FFFFFF"))
            cam_body = QRect(badge_rect.x() + 4, badge_rect.y() + 4, 8, 8)
            painter.drawRoundedRect(cam_body, 1, 1)
            cam_lens = QPolygon([
                QPoint(badge_rect.x() + 12, badge_rect.y() + 6),
                QPoint(badge_rect.x() + 17, badge_rect.y() + 4),
                QPoint(badge_rect.x() + 17, badge_rect.y() + 12),
                QPoint(badge_rect.x() + 12, badge_rect.y() + 10),
            ])
            painter.drawPolygon(cam_lens)

        # Boutons d'action de suggestion (Valider / Ignorer)
        # Ref: picasa3.exe @ adorners/suggestionfaceadorner (0x00714707, 0x00782DF6)
        # Ref: picasa3.exe @ arrows/checkyes (0x00761E33), arrows/checkno (0x00761E47)
        if getattr(item, "is_synthetic_suggestion", False):
            btn_ok, btn_no = self._get_suggestion_item_buttons(rect)
            # Bandeau d'assombrissement subtil pour le contraste des boutons
            scrim = QRect(rect.left() + 4, rect.bottom() - 28, rect.width() - 8, 25)
            painter.fillRect(scrim, QColor(0, 0, 0, 130))

            # Bouton Valider (✓ vert)
            is_ok_hovered = (self._hovered_sug_btn == (item_idx, "ok"))
            painter.setPen(QPen(QColor("#81C784") if is_ok_hovered else QColor("#4CAF50"), 1))
            painter.setBrush(QColor("#388E3C") if is_ok_hovered else QColor("#2E7D32"))
            painter.drawRoundedRect(btn_ok, 3, 3)
            painter.setFont(QFont("Tahoma", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(btn_ok, Qt.AlignmentFlag.AlignCenter, "✓")

            # Bouton Ignorer (✕ rouge)
            is_no_hovered = (self._hovered_sug_btn == (item_idx, "no"))
            painter.setPen(QPen(QColor("#E57373") if is_no_hovered else QColor("#EF5350"), 1))
            painter.setBrush(QColor("#D32F2F") if is_no_hovered else QColor("#C62828"))
            painter.drawRoundedRect(btn_no, 3, 3)
            painter.setFont(QFont("Tahoma", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(btn_no, Qt.AlignmentFlag.AlignCenter, "✕")

        # Légende sous la miniature (Nom du fichier, "Ajouter un nom", ou suggestion "? Nom")
        caption_rect = QRect(rect.x() - 4, rect.bottom() + 2, rect.width() + 8, 14)
        painter.setFont(QFont(self.style.alayout_titleFont, 8, QFont.Weight.Bold if is_selected else QFont.Weight.Normal))
        if getattr(item, "is_synthetic_unnamed", False):
            painter.setPen(QColor("#63B3ED") if getattr(self.style, "is_dark", False) else QColor("#1F65A6"))
            painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, "➕ Ajouter un nom")
        elif getattr(item, "is_synthetic_suggestion", False):
            # Ref: picasa3.exe @ PeoplePanel::SuggestionFmt (0x00CA160C) -> "%s?"
            sug_name = sec.name if (sec and sec.name) else "Suggestion"
            painter.setPen(QColor("#F6AD55") if getattr(self.style, "is_dark", False) else (QColor("#B45309") if not is_selected else QColor("#92400E")))
            elided_sug = painter.fontMetrics().elidedText(f"? {sug_name}", Qt.TextElideMode.ElideMiddle, caption_rect.width())
            painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, elided_sug)
        else:
            lbl_col = self.style.thumbsel_color1 if is_selected else getattr(self.style, "thumb_label_color", QColor("#333333"))
            painter.setPen(lbl_col)
            elided_name = painter.fontMetrics().elidedText(item.filename, Qt.TextElideMode.ElideMiddle, caption_rect.width())
            painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, elided_name)

    def _get_face_pixmap(self, item_idx: int, contact_id: Optional[str]) -> Optional[QPixmap]:
        """
        FR: Découpe et met en cache l'avatar haute résolution centré sur le visage de la personne demandée.
        EN: Crops and caches the high-resolution avatar centered on the requested person's face.
        Ref: picasa3.exe @ faceheaderpanel/face_zoom, 0x009B93F0, 0x0057A4F0
        """
        if item_idx >= len(self.items):
            return None
        item = self.items[item_idx]
        if item.face_pixmap and not item.face_pixmap.isNull():
            return item.face_pixmap

        if self._in_paint_event:
            if self._paint_sync_decodes >= 6 or (time.perf_counter() - self._paint_start_ts) > 0.0035:
                if not self._thumb_flush_timer.isActive():
                    self._thumb_flush_timer.start()
                return None

        # FR: 1. Si c'est un enregistrement de visage dans bigthumbs_0.db / thumbs_0.db (type 1001),
        # la vignette stockée par Picasa est DÉJÀ un avatar cadré exactement sur la tête (240x288 dans bigthumbs_0.db).
        # EN: 1. If this is a face sub-record in bigthumbs_0.db / thumbs_0.db (type 1001),
        # the thumbnail stored by Picasa is ALREADY a head-framed avatar (240x288 in bigthumbs_0.db).
        if self.db and self.db.is_face_record(item.index):
            raw_thumb = (
                self.db.get_thumbnail(item.index, size="large")
                or self.db.get_thumbnail(item.index, size="small")
            )
            if raw_thumb:
                if self._in_paint_event:
                    self._paint_sync_decodes += 1
                qimg = QImage.fromData(raw_thumb)
                if not qimg.isNull():
                    # FR: Mise à la hauteur de la grille (thumb_base_size) une seule fois, puis cache
                    # EN: Scale once to the grid height (thumb_base_size), then cache
                    if qimg.height() != self.thumb_base_size and qimg.height() > 0:
                        qimg = qimg.scaledToHeight(self.thumb_base_size, Qt.TransformationMode.SmoothTransformation)
                    pix = QPixmap.fromImage(qimg)
                    if not pix.isNull():
                        item.face_pixmap = pix
                        return pix
                try:
                    with Image.open(io.BytesIO(raw_thumb)) as thumb_raw:
                        pix = FaceRect.to_avatar_pixmap(thumb_raw, avatar_size=self.thumb_base_size, circular=False)
                        if pix and not pix.isNull():
                            item.face_pixmap = pix
                            return pix
                except Exception:
                    pass

        # FR: 2. Si un FaceRect est associé à l'item (visage sans nom, cluster ou suggestion)
        # EN: 2. When a FaceRect is attached to the item (unnamed face, cluster, or suggestion)
        if item.face_rect is not None:
            if self.db and getattr(self.db, "face_manager", None):
                if self._in_paint_event:
                    self._paint_sync_decodes += 1
                pix = self.db.face_manager.get_face_avatar(
                    item.path,
                    item.face_rect,
                    item.index if item.index >= 0 else None,
                    size=self.thumb_base_size,
                    circular=False,
                    allow_disk_fallback=not self._in_paint_event,
                )
                if pix and not pix.isNull():
                    item.face_pixmap = pix
                    return pix

        if self.db is None:
            return self._get_thumbnail_pixmap(item_idx)

        # FR: 3. Chercher le visage pour ce contact dans cette photo et déléguer à get_face_avatar
        # EN: 3. Find the face for this contact in this photo and delegate to get_face_avatar
        faces = self.db.face_manager.get_faces_for_photo(item.index)
        target_face = None
        if faces:
            if contact_id:
                for f in faces:
                    if f.contact_id == contact_id:
                        target_face = f
                        break
            if target_face is None:
                target_face = faces[0]

        if target_face and getattr(self.db, "face_manager", None):
            if self._in_paint_event:
                self._paint_sync_decodes += 1
            pix = self.db.face_manager.get_face_avatar(
                item.path,
                target_face,
                db_idx=item.index if item.index >= 0 else None,
                size=self.thumb_base_size,
                circular=False,
                allow_disk_fallback=not self._in_paint_event,
            )
            if pix and not pix.isNull():
                item.face_pixmap = pix
                return pix

        return self._get_thumbnail_pixmap(item_idx)

    def _get_parent_photo_pixmap(self, item_idx: int) -> Optional[QPixmap]:
        """
        FR: Récupère la vignette de la photo entière pour un élément d'album de personne (mode Photos).
        EN: Retrieves the full-photo thumbnail for a person album item (Pictures mode).
        Ref: picasa3.exe @ faceheaderpanel/picture_zoom, PeopleAlbumUseFaceSrc
        """
        if self.db is None or item_idx >= len(self.items):
            return None
        item = self.items[item_idx]

        if item.pixmap and not item.pixmap.isNull():
            return item.pixmap

        if self.db.is_face_record(item.index):
            parent_idx = self.db.get_face_parent_photo_idx(item.index)
            if parent_idx is not None and parent_idx >= 0:
                if parent_idx in self._db_pixmap_cache:
                    pix = self._db_pixmap_cache[parent_idx]
                    item.pixmap = pix
                    return pix
                if self._in_paint_event:
                    if self._paint_sync_decodes >= 6 or (time.perf_counter() - self._paint_start_ts) > 0.0035:
                        if not self._thumb_flush_timer.isActive():
                            self._thumb_flush_timer.start()
                        return None
                raw_bytes = (
                    self.db.get_thumbnail(parent_idx, size="large")
                    or self.db.get_thumbnail(parent_idx, size="small")
                )
                if raw_bytes:
                    if self._in_paint_event:
                        self._paint_sync_decodes += 1
                    qimg = QImage.fromData(raw_bytes)
                    if not qimg.isNull():
                        pix = QPixmap.fromImage(qimg)
                        self._db_pixmap_cache[parent_idx] = pix
                        item.pixmap = pix
                        return pix

        return self._get_thumbnail_pixmap(item_idx)

    def invalidate_item(self, item_idx_or_path: Union[int, str]) -> None:
        """
        FR: Invalide le cache d'une miniature modifiée pour forcer son rafraîchissement visuel.
        EN: Invalidates the cached pixmap of a modified thumbnail to force a visual refresh.
        """
        self._folder_backups_cache.clear()
        if isinstance(item_idx_or_path, int):
            self._thumb_worker._failed_items.discard(item_idx_or_path)
            self._pixmap_cache.pop(item_idx_or_path, None)
            for k in [k for k in self._scaled_pixmap_cache if k[0] in (item_idx_or_path, -item_idx_or_path - 1)]:
                self._scaled_pixmap_cache.pop(k, None)
            if 0 <= item_idx_or_path < len(self.items):
                it = self.items[item_idx_or_path]
                self._db_pixmap_cache.pop(it.index, None)
                it.pixmap = None
                it.face_pixmap = None
                if it.path:
                    p = Path(it.path)
                    it.has_backup = (p.parent / ".picasaoriginals" / p.name).exists()
                    it.has_edits = True
        else:
            norm_target = os.path.normcase(os.path.normpath(item_idx_or_path))
            for idx, it in enumerate(self.items):
                if it.path == item_idx_or_path or (it.path and os.path.normcase(os.path.normpath(it.path)) == norm_target):
                    self._thumb_worker._failed_items.discard(idx)
                    self._pixmap_cache.pop(idx, None)
                    self._db_pixmap_cache.pop(it.index, None)
                    for k in [k for k in self._scaled_pixmap_cache if k[0] in (idx, -idx - 1)]:
                        self._scaled_pixmap_cache.pop(k, None)
                    it.pixmap = None
                    it.face_pixmap = None
                    p = Path(it.path)
                    it.has_backup = (p.parent / ".picasaoriginals" / p.name).exists()
                    it.has_edits = True
        self.update()

    def _flush_async_thumbnails(self) -> None:
        """
        FR: Intègre sur le thread GUI les miniatures recalculées en arrière-plan par ViewportThumbWorker.
        EN: Integrates on the GUI thread thumbnails recalculated in background by ViewportThumbWorker.
        Ref: picasa3.exe @ 0x007301F0 (CThumbCache::OnWorkerReady)
        """
        completed = self._thumb_worker.pop_completed()
        if not completed:
            has_unloaded_visible_faces = False
            for sec in self.visible_sections:
                if sec.is_person or sec.is_unnamed:
                    sec_top = sec.y_start - self.scroll_y
                    sec_bottom = sec_top + sec.height
                    if sec_bottom < -20 or sec_top > self.height() + 20:
                        continue
                    for idx in sec.item_indices:
                        if 0 <= idx < len(self.items):
                            it = self.items[idx]
                            if (sec.face_zoom and it.face_pixmap is None) or (
                                not sec.face_zoom and it.pixmap is None and idx not in self._pixmap_cache
                            ):
                                has_unloaded_visible_faces = True
                                break
                if has_unloaded_visible_faces:
                    break
            if has_unloaded_visible_faces:
                self.update()
                return
            if not self._thumb_worker.has_pending():
                self._thumb_flush_timer.stop()
            return
        any_updated = False
        for item_idx, db_idx, qimg, pil_img in completed:
            if 0 <= item_idx < len(self.items):
                pix = QPixmap.fromImage(qimg)
                if not pix.isNull():
                    self._pixmap_cache[item_idx] = pix
                    if db_idx >= 0:
                        self._db_pixmap_cache[db_idx] = pix
                    for k in [k for k in self._scaled_pixmap_cache if k[0] == item_idx]:
                        self._scaled_pixmap_cache.pop(k, None)
                    any_updated = True
                if self.db is not None and db_idx >= 0 and pil_img is not None and hasattr(self.db, "update_thumbnails_from_pil"):
                    try:
                        self.db.update_thumbnails_from_pil(db_idx, pil_img, persist_to_disk=False)
                    except Exception:
                        pass
        if any_updated:
            self.update()

    def _get_thumbnail_pixmap(self, item_idx: int) -> Optional[QPixmap]:
        """
        FR: Récupération de la vignette avec mise en cache mémoire et application
        des retouches non-destructives .picasa.ini (crop, rotate, tilt) ou
        chargement direct depuis l'image modifiée si enregistrée sur le disque.
        EN: Retrieves the thumbnail with in-memory caching and applies non-destructive
        .picasa.ini edits (crop, rotate, tilt) or loads directly from disk if saved.
        Ref: picasa3.exe @ 0x008814AC, 0x009B9290
        """
        if item_idx in self._pixmap_cache:
            return self._pixmap_cache[item_idx]

        if self.db is None or item_idx >= len(self.items):
            return None

        item = self.items[item_idx]
        if item.index >= 0 and not item.has_edits and not item.has_backup and item.index in self._db_pixmap_cache:
            cached_db_pix = self._db_pixmap_cache[item.index]
            if cached_db_pix and not cached_db_pix.isNull():
                self._pixmap_cache[item_idx] = cached_db_pix
                return cached_db_pix

        pix: Optional[QPixmap] = None

        # 1. Si la photo a été enregistrée sur le disque, .picasaoriginals/ existe et le fichier sur le disque a priorité
        has_backup = item.has_backup
        if not has_backup and not self._in_paint_event and item.path:
            p = Path(item.path)
            orig_backup = p.parent / ".picasaoriginals" / p.name
            if orig_backup.exists():
                has_backup = True
                item.has_backup = True

        # Budget de temps strict par frame (< 3.5 ms / max 6 décodages synchrones dans paintEvent)
        # Ref: picasa3.exe @ 0x00414C90 (CThumbMaker), 0x007301F0 (CThumbCache Frame Budget)
        if self._in_paint_event:
            if self._paint_sync_decodes >= 6 or (time.perf_counter() - self._paint_start_ts) > 0.0035:
                self._thumb_worker.schedule(
                    item_idx,
                    item.index,
                    item.path,
                    is_backup_only=has_backup,
                    db=self.db,
                    db_fast=(not has_backup and not item.has_edits),
                )
                if not self._thumb_flush_timer.isActive():
                    self._thumb_flush_timer.start()
                return None

        if not has_backup:
            raw_bytes = self.db.get_thumbnail(item.index)
            if raw_bytes:
                if self._in_paint_event:
                    self._paint_sync_decodes += 1
                img = QImage.fromData(raw_bytes)
                if not img.isNull():
                    pix = QPixmap.fromImage(img)

        # 2. Fallback ou lecture directe si sauvegarde sur disque
        if pix is None and item.path:
            if self._in_paint_event:
                self._thumb_worker.schedule(item_idx, item.index, item.path, is_backup_only=has_backup)
                if not self._thumb_flush_timer.isActive():
                    self._thumb_flush_timer.start()
                return None
            if os.path.exists(item.path):
                reader = QImageReader(item.path)
                reader.setAutoTransform(True)
                orig_sz = reader.size()
                if orig_sz.isValid() and orig_sz.width() > 0 and orig_sz.height() > 0:
                    scale = min(256.0 / orig_sz.width(), 256.0 / orig_sz.height(), 1.0)
                    target_sz = QSize(max(1, int(orig_sz.width() * scale)), max(1, int(orig_sz.height() * scale)))
                    reader.setScaledSize(target_sz)
                img = reader.read()
                if not img.isNull():
                    pix = QPixmap.fromImage(img)

        # 3. Application des transformations non-destructives .picasa.ini si pas encore écrites dans la miniature DB
        updated_db_thumbs = getattr(self.db, "_updated_thumb_indices", set()) if self.db is not None else set()
        should_check_ini = (
            item.path
            and not has_backup
            and (pix is None or item.index not in updated_db_thumbs)
            and (item.has_edits or not self._in_paint_event)
        )
        if should_check_ini:
            p = Path(item.path)
            try:
                from picasa_py.ini.parser import PicasaIniParser
                from picasa_py.faces.facerect import decode_rect64_string
                from PySide6.QtGui import QTransform
                doc = None
                if self.db and hasattr(self.db, "get_parsed_ini"):
                    doc = self.db.get_parsed_ini(str(p.parent / ".picasa.ini"))
                    if doc is None:
                        doc = self.db.get_parsed_ini(str(p.parent / "Picasa.ini"))
                else:
                    ini_path = p.parent / ".picasa.ini"
                    if not ini_path.exists():
                        ini_path = p.parent / "Picasa.ini"
                    if ini_path.exists():
                        doc = PicasaIniParser.parse_file(str(ini_path))
                if doc:
                    rot = doc.get_rotate(p.name)
                    tilt = doc.get_tilt(p.name)
                    crop_hex = doc.get_crop(p.name)
                    filters_str = doc.get_key(p.name, "filters")
                    text_str = doc.get_text(p.name)
                    has_ini_edits = bool(
                        rot
                        or (tilt and abs(tilt) >= 0.01)
                        or crop_hex
                        or (filters_str and filters_str.strip())
                        or (text_str and text_str.strip())
                    )
                    if has_ini_edits:
                        if not self._in_paint_event and os.path.exists(item.path):
                            from picasa_py.ui.image_processor import PicasaImageProcessor
                            pil_img = PicasaImageProcessor.load_transformed_image(item.path, max_size=288)
                            if pil_img is not None:
                                pix = PicasaImageProcessor.pil_to_qpixmap(pil_img)
                                if self.db is not None and item.index >= 0 and hasattr(self.db, "update_thumbnails_from_pil"):
                                    self.db.update_thumbnails_from_pil(item.index, pil_img, persist_to_disk=False)
                        elif pix and not pix.isNull():
                            # Fast geometric preview on DB thumb + schedule background full filter render if needed
                            if crop_hex:
                                left_f, top_f, right_f, bottom_f = decode_rect64_string(crop_hex)
                                pw, ph = pix.width(), pix.height()
                                cx = int(round(left_f * pw))
                                cy = int(round(top_f * ph))
                                cw = int(round((right_f - left_f) * pw))
                                ch = int(round((bottom_f - top_f) * ph))
                                if cw > 0 and ch > 0:
                                    pix = pix.copy(cx, cy, cw, ch)
                            if rot:
                                pix = pix.transformed(QTransform().rotate(rot * 90), Qt.TransformationMode.SmoothTransformation)
                            if tilt and abs(tilt) >= 0.01:
                                pix = pix.transformed(QTransform().rotate(tilt), Qt.TransformationMode.SmoothTransformation)
                            if (filters_str and filters_str.strip()) or (text_str and text_str.strip()):
                                self._thumb_worker.schedule(item_idx, item.index, item.path, is_backup_only=False)
                                if not self._thumb_flush_timer.isActive():
                                    self._thumb_flush_timer.start()
            except Exception:
                pass

        if pix and not pix.isNull():
            if len(self._pixmap_cache) >= self._cache_limit:
                # Evict oldest entry (FIFO / dict insertion order)
                oldest_key = next(iter(self._pixmap_cache), None)
                if oldest_key is not None:
                    self._pixmap_cache.pop(oldest_key, None)
            self._pixmap_cache[item_idx] = pix
            if item.index >= 0:
                if len(self._db_pixmap_cache) >= self._cache_limit * 2:
                    oldest_db_k = next(iter(self._db_pixmap_cache), None)
                    if oldest_db_k is not None:
                        self._db_pixmap_cache.pop(oldest_db_k, None)
                self._db_pixmap_cache[item.index] = pix
            return pix

        return None

