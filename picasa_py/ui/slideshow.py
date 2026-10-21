"""
FR: Composant de diaporama plein écran pour PyCasa.
Reproduction fidèle du lecteur de diaporama de Picasa 3.

EN: Fullscreen Slideshow Component for PyCasa.
Faithful reproduction of Picasa 3 Slideshow player.

Ref: picasa3.exe @ 0x00620AB7 (Slideshow entry)
Ref: picasa3.exe @ 0x0074E843 (SlideshowBaseHandler)
Ref: picasa3.exe @ SlideShowHideTimer (HUD auto-hide after 3s)
Ref: TOOLTIPS_FR.XML @ "Visionner un diaporama de ces photos"
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGraphicsOpacityEffect, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QUrl
from PySide6.QtGui import (
    QKeyEvent, QMouseEvent, QPainter, QPixmap, QColor, QFont,
    QPen, QBrush, QImage
)
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False


from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.faces.facerect import decode_rect64_string


class PicasaSlideshowHUD(QFrame):
    """
    FR: Barre de commandes flottante semi-transparente du diaporama.
    EN: Semi-transparent floating control bar for the slideshow.
    Ref: SlideShowHideTimer (Masquage automatique au bout de 3 secondes sans mouvement)
    """
    play_pause_toggled = Signal(bool)  # is_playing
    prev_clicked = Signal()
    next_clicked = Signal()
    interval_changed = Signal(int)     # millisecondes
    rotate_cw_clicked = Signal()
    star_clicked = Signal()
    exit_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise la barre de commandes flottante du diaporama et ses boutons d'action.
        EN: Initializes the floating slideshow HUD control bar and its action buttons.
        """
        super().__init__(parent)
        self.setFixedSize(500, 52)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 30, 34, 210);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 26px;
            }
            QPushButton {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                font-size: 15px;
                padding: 4px;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 45);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 25);
            }
            QLabel {
                color: #DDDDDD;
                font-size: 11px;
                background-color: transparent;
                border: none;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 60);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(10)

        # FR: 1. Précédent (◀◀) / EN: 1. Previous (◀◀)
        self.btn_prev = QPushButton("◀◀")
        self.btn_prev.setToolTip("Photo précédente (Flèche gauche)")
        self.btn_prev.clicked.connect(self.prev_clicked.emit)
        layout.addWidget(self.btn_prev)

        # FR: 2. Lecture / Pause (⏸ / ▶) / EN: 2. Play / Pause (⏸ / ▶)
        self.is_playing = True
        self.btn_play_pause = QPushButton("⏸")
        self.btn_play_pause.setToolTip("Pause / Lecture (Espace)")
        self.btn_play_pause.clicked.connect(self._toggle_play_pause)
        layout.addWidget(self.btn_play_pause)

        # FR: 3. Suivant (▶▶) / EN: 3. Next (▶▶)
        self.btn_next = QPushButton("▶▶")
        self.btn_next.setToolTip("Photo suivante (Flèche droite)")
        self.btn_next.clicked.connect(self.next_clicked.emit)
        layout.addWidget(self.btn_next)

        # FR: Séparateur / EN: Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: rgba(255,255,255,40);")
        layout.addWidget(sep1)

        # FR: 4. Curseur de vitesse / délai (1s à 10s)
        # EN: 4. Speed / delay slider (1s to 10s)
        lbl_speed = QLabel("⏱")
        layout.addWidget(lbl_speed)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(1, 10)
        self.slider_speed.setValue(3)  # 3 secondes par défaut
        self.slider_speed.setFixedWidth(80)
        self.slider_speed.setToolTip("Délai d'affichage par photo (secondes)")
        self.slider_speed.valueChanged.connect(lambda v: self.interval_changed.emit(v * 1000))
        layout.addWidget(self.slider_speed)

        self.lbl_speed_val = QLabel("3s")
        self.slider_speed.valueChanged.connect(lambda v: self.lbl_speed_val.setText(f"{v}s"))
        layout.addWidget(self.lbl_speed_val)

        # FR: Séparateur / EN: Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: rgba(255,255,255,40);")
        layout.addWidget(sep2)

        # FR: 5. Rotation horaire (↻) / EN: 5. Clockwise rotation (↻)
        self.btn_rot = QPushButton("↻")
        self.btn_rot.setToolTip("Faire pivoter de 90° dans le sens horaire (Ctrl+R)")
        self.btn_rot.clicked.connect(self.rotate_cw_clicked.emit)
        layout.addWidget(self.btn_rot)

        # FR: 6. Étoiler (⭐) / EN: 6. Star (⭐)
        self.btn_star = QPushButton("☆")
        self.btn_star.setToolTip("Ajouter / Supprimer des favoris (Ctrl+S)")
        self.btn_star.clicked.connect(self.star_clicked.emit)
        layout.addWidget(self.btn_star)

        # FR: 7. Quitter (✕) / EN: 7. Exit (✕)
        self.btn_exit = QPushButton("✕")
        self.btn_exit.setToolTip("Quitter le diaporama (Échap)")
        self.btn_exit.clicked.connect(self.exit_clicked.emit)
        layout.addWidget(self.btn_exit)

    def _toggle_play_pause(self) -> None:
        """
        FR: Bascule l'état lecture/pause du diaporama et émet le signal correspondant.
        EN: Toggles the slideshow play/pause state and emits the corresponding signal.
        """
        self.is_playing = not self.is_playing
        self.btn_play_pause.setText("⏸" if self.is_playing else "▶")
        self.play_pause_toggled.emit(self.is_playing)

    def set_playing(self, playing: bool) -> None:
        """
        FR: Définit explicitement l'état de lecture du bouton lecture/pause.
        EN: Explicitly sets the playback state of the play/pause button.
        """
        self.is_playing = playing
        self.btn_play_pause.setText("⏸" if playing else "▶")

    def set_starred(self, starred: bool) -> None:
        """
        FR: Met à jour l'icône et la couleur du bouton favori selon l'état étoilé de la photo.
        EN: Updates the star button icon and color according to the photo's starred state.
        """
        self.btn_star.setText("★" if starred else "☆")
        self.btn_star.setStyleSheet("color: #FFCC00;" if starred else "color: #FFFFFF;")


class PicasaSlideshowWindow(QWidget):
    """
    FR: Lecteur Diaporama Plein Écran de Picasa 3.
    EN: Picasa 3 Fullscreen Slideshow Player.
    Ref: SlideshowBaseHandler, CDXSlideshowFilter
    """
    photo_changed = Signal(int)  # index courant

    def __init__(
        self,
        photo_paths: List[str],
        start_index: int = 0,
        audio_path: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        """
        FR: Initialise la fenêtre plein écran du diaporama avec la liste de photos et l'audio optionnel.
        EN: Initializes the fullscreen slideshow window with the photo list and optional audio.
        """
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.photo_paths = photo_paths
        self.current_idx = max(0, min(start_index, len(photo_paths) - 1)) if photo_paths else 0
        self.audio_path = audio_path

        self.setStyleSheet("background-color: #000000;")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMouseTracking(True)

        # FR: Pixmaps pour transition de fondu (Crossfade)
        # EN: Pixmaps for crossfade transition
        self._curr_pixmap: Optional[QPixmap] = None
        self._prev_pixmap: Optional[QPixmap] = None
        self._transition_opacity: float = 1.0  # 1.0 = transition terminée

        # FR: Minuteur d'avance automatique
        # EN: Auto-advance timer
        self.advance_timer = QTimer(self)
        self.advance_timer.setInterval(3000)
        self.advance_timer.timeout.connect(self.next_photo)

        # FR: Minuteur de transition progressive (Crossfade 60Hz)
        # EN: Progressive crossfade transition timer (60Hz)
        self.fade_timer = QTimer(self)
        self.fade_timer.setInterval(16)
        self.fade_timer.timeout.connect(self._step_fade)

        # FR: Minuteur d'auto-masquage du HUD (3 secondes)
        # EN: HUD auto-hide timer (3 seconds)
        self.hud_hide_timer = QTimer(self)
        self.hud_hide_timer.setInterval(3000)
        self.hud_hide_timer.timeout.connect(self._hide_hud)

        # FR: HUD flottant / EN: Floating HUD
        self.hud = PicasaSlideshowHUD(self)
        self.hud.prev_clicked.connect(self.prev_photo)
        self.hud.next_clicked.connect(self.next_photo)
        self.hud.play_pause_toggled.connect(self._on_play_pause_toggled)
        self.hud.interval_changed.connect(self._on_interval_changed)
        self.hud.rotate_cw_clicked.connect(self.rotate_current_cw)
        self.hud.star_clicked.connect(self.toggle_star_current)
        self.hud.exit_clicked.connect(self.close)

        # FR: Cache INI pour éviter relectures disque
        # EN: INI cache to avoid redundant disk reads
        self._ini_cache = {}

        # FR: Musique de fond / EN: Background music (Ref: album.fen / usemusic)
        self.media_player: Optional[QMediaPlayer] = None
        self.audio_output: Optional[QAudioOutput] = None
        if self.audio_path and os.path.exists(self.audio_path) and HAS_MULTIMEDIA:
            try:
                self.audio_output = QAudioOutput(self)
                self.media_player = QMediaPlayer(self)
                self.media_player.setAudioOutput(self.audio_output)
                self.media_player.setSource(QUrl.fromLocalFile(self.audio_path))
                self.media_player.play()
            except Exception:
                self.media_player = None

        if self.photo_paths:
            self._load_current_photo(animate=False)
            self.advance_timer.start()

    def showEvent(self, event) -> None:
        """
        FR: Gère l'affichage de la fenêtre, repositionne le HUD et démarre son minuteur de masquage.
        EN: Handles window show event, repositions the HUD, and starts its auto-hide timer.
        """
        super().showEvent(event)
        self._reposition_hud()
        self.hud_hide_timer.start()

    def resizeEvent(self, event) -> None:
        """
        FR: Repositionne le HUD flottant lors du redimensionnement de la fenêtre.
        EN: Repositions the floating HUD when the window is resized.
        """
        super().resizeEvent(event)
        self._reposition_hud()

    def _reposition_hud(self) -> None:
        """
        FR: Centre horizontalement la barre HUD en bas de l'écran.
        EN: Horizontally centers the HUD bar at the bottom of the screen.
        """
        x = (self.width() - self.hud.width()) // 2
        y = self.height() - self.hud.height() - 36
        self.hud.move(x, y)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        FR: Réaffiche le curseur et le HUD lors d'un mouvement de souris et relance le délai de 3s.
        EN: Restores the cursor and HUD on mouse movement and restarts the 3s auto-hide timer.
        """
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if not self.hud.isVisible():
            self.hud.show()
        self.hud_hide_timer.start(3000)
        super().mouseMoveEvent(event)

    def _hide_hud(self) -> None:
        """
        FR: Masque le HUD et le curseur de souris après 3 secondes d'inactivité.
        EN: Hides the HUD and mouse cursor after 3 seconds of inactivity.
        """
        if self.hud.isVisible():
            self.hud.hide()
        self.setCursor(Qt.CursorShape.BlankCursor)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        FR: Gère les raccourcis clavier du diaporama (navigation, lecture/pause, quitter).
        EN: Handles slideshow keyboard shortcuts (navigation, play/pause, exit).
        """
        k = event.key()
        if k in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
        elif k in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_PageDown):
            self.next_photo()
        elif k in (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_PageUp):
            self.prev_photo()
        elif k == Qt.Key.Key_Space:
            self.hud._toggle_play_pause()
        elif k == Qt.Key.Key_Home:
            self.current_idx = 0
            self._load_current_photo(animate=True)
        elif k == Qt.Key.Key_End:
            self.current_idx = len(self.photo_paths) - 1
            self._load_current_photo(animate=True)
        super().keyPressEvent(event)

    def _on_play_pause_toggled(self, is_playing: bool) -> None:
        """
        FR: Démarre ou met en pause le minuteur d'avance automatique et la piste audio.
        EN: Starts or pauses the auto-advance timer and audio track.
        """
        if is_playing:
            self.advance_timer.start()
            if self.media_player:
                self.media_player.play()
        else:
            self.advance_timer.stop()
            if self.media_player:
                self.media_player.pause()

    def _on_interval_changed(self, ms: int) -> None:
        """
        FR: Met à jour l'intervalle d'affichage entre deux diapositives en millisecondes.
        EN: Updates the display interval between slides in milliseconds.
        """
        self.advance_timer.setInterval(ms)

    def next_photo(self) -> None:
        """
        FR: Passe à la photo suivante de la liste en bouclant au début.
        EN: Advances to the next photo in the list, looping back to the start.
        """
        if not self.photo_paths:
            return
        self.current_idx = (self.current_idx + 1) % len(self.photo_paths)
        self._load_current_photo(animate=True)
        if self.hud.is_playing:
            self.advance_timer.start()

    def prev_photo(self) -> None:
        """
        FR: Revient à la photo précédente de la liste en bouclant à la fin.
        EN: Returns to the previous photo in the list, looping to the end.
        """
        if not self.photo_paths:
            return
        self.current_idx = (self.current_idx - 1 + len(self.photo_paths)) % len(self.photo_paths)
        self._load_current_photo(animate=True)
        if self.hud.is_playing:
            self.advance_timer.start()

    def _load_current_photo(self, animate: bool = True) -> None:
        """
        FR: Charge la photo courante en appliquant l'orientation EXIF, les transformations
        non-destructives (.picasa.ini : crop, rotate, tilt, filters) et le repli imagedata_rotate,
        puis lance le fondu-enchaîné.
        EN: Loads the current photo applying EXIF orientation, non-destructive transforms
        (.picasa.ini: crop, rotate, tilt, filters), and imagedata_rotate fallback,
        then starts the crossfade transition.
        Ref: picasa3.exe @ 0x00620AB7, 0x0074E843, 0x008814AC, 0x0042A6F9
        """
        if not self.photo_paths or self.current_idx >= len(self.photo_paths):
            return

        path_str = self.photo_paths[self.current_idx]
        src = Path(path_str)

        # FR: Charger les métadonnées .picasa.ini
        # EN: Load .picasa.ini metadata
        parent_dir = str(src.parent)
        if parent_dir not in self._ini_cache:
            ini_p = Path(parent_dir) / ".picasa.ini"
            if not ini_p.exists():
                ini_p = Path(parent_dir) / "Picasa.ini"
            if ini_p.exists():
                try:
                    self._ini_cache[parent_dir] = PicasaIniParser.parse_file(str(ini_p))
                except Exception:
                    self._ini_cache[parent_dir] = None
            else:
                self._ini_cache[parent_dir] = None

        doc = self._ini_cache.get(parent_dir)
        rot = 0
        has_ini_rot = False
        crop_hex = None
        tilt = 0.0
        filters_str = ""
        starred = False
        if doc:
            sec = doc.get_section(src.name)
            if sec and sec.get("rotate") is not None:
                has_ini_rot = True
            rot = doc.get_rotate(src.name)
            crop_hex = doc.get_crop(src.name)
            tilt = doc.get_tilt(src.name) or 0.0
            if sec:
                filters_str = sec.get("filters", "") or ""
            starred = doc.is_starred(src.name)

        self.hud.set_starred(starred)

        # FR: Décodage de l'image avec orientation EXIF + transformations non-destructives Picasa
        # EN: Decode image with EXIF orientation + Picasa non-destructive transformations
        try:
            from PIL import ImageOps
            from picasa_py.ui.image_processor import PicasaImageProcessor

            with Image.open(src) as raw_img:
                exif_orient = 1
                try:
                    exif = raw_img.getexif()
                    if exif:
                        exif_orient = int(exif.get(0x0112, 1) or 1)
                except Exception:
                    exif_orient = 1

                if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                    raw_img = raw_img.convert("RGBA")
                try:
                    img = ImageOps.exif_transpose(raw_img)
                except Exception:
                    img = raw_img
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                else:
                    img = img.copy()

            # FR: Si aucune rotation .picasa.ini ni orientation EXIF (>1) n'est présente,
            # vérifier imagedata_rotate.pmp dans la base de données parente (Ref: 0x0068B5E0)
            # EN: When neither .picasa.ini rotate nor EXIF orientation (>1) is set,
            # check imagedata_rotate.pmp in the parent database (Ref: 0x0068B5E0)
            if not has_ini_rot and exif_orient <= 1:
                parent_win = self.parentWidget()
                db = getattr(parent_win, "db", None) if parent_win else None
                if db is not None and hasattr(db, "find_media_index_by_path") and hasattr(db, "get_rotate"):
                    try:
                        db_idx = db.find_media_index_by_path(path_str)
                        if db_idx is not None and db_idx >= 0:
                            rot = db.get_rotate(db_idx)
                    except Exception:
                        pass

            if crop_hex:
                try:
                    left_f, top_f, right_f, bottom_f = decode_rect64_string(crop_hex)
                    w, h = img.size
                    crop_box = (
                        int(round(left_f * w)),
                        int(round(top_f * h)),
                        int(round(right_f * w)),
                        int(round(bottom_f * h)),
                    )
                    if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                        img = img.crop(crop_box)
                except Exception:
                    pass

            if rot == 1:
                img = img.rotate(270, expand=True)
            elif rot == 2:
                img = img.rotate(180, expand=True)
            elif rot == 3:
                img = img.rotate(90, expand=True)

            if tilt and abs(tilt) >= 0.01:
                try:
                    img = PicasaImageProcessor.straighten(img, tilt)
                except Exception:
                    pass

            if filters_str:
                try:
                    img = PicasaImageProcessor.apply_filter_chain(img, filters_str)
                except Exception:
                    pass

            if img.mode != "RGB":
                img = img.convert("RGB")
            data = img.tobytes("raw", "RGB")
            qim = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888).copy()
            new_pixmap = QPixmap.fromImage(qim)
        except Exception:
            new_pixmap = QPixmap()

        if animate and self._curr_pixmap is not None:
            self._prev_pixmap = self._curr_pixmap
            self._curr_pixmap = new_pixmap
            self._transition_opacity = 0.0
            self.fade_timer.start()
        else:
            self._curr_pixmap = new_pixmap
            self._prev_pixmap = None
            self._transition_opacity = 1.0
            self.update()

        self.photo_changed.emit(self.current_idx)

    def _step_fade(self) -> None:
        """
        FR: Avance d'un pas l'opacité de la transition en fondu-enchaîné.
        EN: Advances the crossfade transition opacity by one step.
        """
        self._transition_opacity += 0.06
        if self._transition_opacity >= 1.0:
            self._transition_opacity = 1.0
            self.fade_timer.stop()
            self._prev_pixmap = None
        self.update()

    def rotate_current_cw(self) -> None:
        """
        FR: Pivote la photo courante de 90° dans le sens horaire et persiste dans .picasa.ini (et la base si présente).
        EN: Rotates the current photo 90° clockwise and persists the change to .picasa.ini (and database if present).
        """
        if not self.photo_paths:
            return
        path_str = self.photo_paths[self.current_idx]
        src = Path(path_str)
        parent_dir = str(src.parent)
        ini_p = Path(parent_dir) / ".picasa.ini"

        doc = self._ini_cache.get(parent_dir)
        if not doc:
            doc = PicasaIniParser.parse_file(str(ini_p)) if ini_p.exists() else PicasaIniDocument()
            self._ini_cache[parent_dir] = doc

        current_rot = doc.get_rotate(src.name)
        new_rot = (current_rot + 1) % 4
        doc.set_rotate(src.name, new_rot)
        doc.write_file(str(ini_p))

        # FR: Synchroniser avec la base de données et la vue de vignettes si disponibles
        # EN: Synchronize with the database and thumbnail view when available
        parent_win = self.parentWidget()
        db = getattr(parent_win, "db", None) if parent_win else None
        if db is not None and hasattr(db, "find_media_index_by_path") and hasattr(db, "set_rotate"):
            try:
                db_idx = db.find_media_index_by_path(path_str)
                if db_idx is not None and db_idx >= 0:
                    db.set_rotate(db_idx, new_rot)
            except Exception:
                pass

        self._load_current_photo(animate=False)

    def toggle_star_current(self) -> None:
        """
        FR: Bascule l'étoile/favori de la photo courante et persiste dans .picasa.ini.
        EN: Toggles the star/favorite status of the current photo and persists it to .picasa.ini.
        """
        if not self.photo_paths:
            return
        path_str = self.photo_paths[self.current_idx]
        src = Path(path_str)
        parent_dir = str(src.parent)
        ini_p = Path(parent_dir) / ".picasa.ini"

        doc = self._ini_cache.get(parent_dir)
        if not doc:
            doc = PicasaIniParser.parse_file(str(ini_p)) if ini_p.exists() else PicasaIniDocument()
            self._ini_cache[parent_dir] = doc

        is_star = doc.is_starred(src.name)
        doc.set_starred(src.name, not is_star)
        doc.write_file(str(ini_p))

        self.hud.set_starred(not is_star)

    def paintEvent(self, event) -> None:
        """
        FR: Dessine la photo courante (et la précédente en fondu) centrée sur fond noir avec légende.
        EN: Draws the current photo (and previous one during crossfade) centered on a black background with caption.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        vw, vh = self.width(), self.height()

        def draw_scaled(pm: QPixmap, opacity: float) -> None:
            """
            FR: Dessine un QPixmap redimensionné proportionnellement et centré avec l'opacité donnée.
            EN: Draws a proportionally scaled and centered QPixmap with the given opacity.
            """
            if pm.isNull() or opacity <= 0.0:
                return
            pw, ph = pm.width(), pm.height()
            scale = min(vw / float(pw), vh / float(ph))
            target_w = int(pw * scale)
            target_h = int(ph * scale)
            x = (vw - target_w) // 2
            y = (vh - target_h) // 2

            painter.setOpacity(opacity)
            painter.drawPixmap(x, y, target_w, target_h, pm)

        if self._prev_pixmap and self._transition_opacity < 1.0:
            draw_scaled(self._prev_pixmap, 1.0 - self._transition_opacity)

        if self._curr_pixmap:
            draw_scaled(self._curr_pixmap, self._transition_opacity)

        # FR: Légende du fichier en bas à gauche
        # EN: File caption at the bottom-left
        if self.photo_paths and self.current_idx < len(self.photo_paths):
            painter.setOpacity(0.7)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 10))
            name_text = Path(self.photo_paths[self.current_idx]).name
            counter_text = f"({self.current_idx + 1} / {len(self.photo_paths)})"
            painter.drawText(24, vh - 24, f"{name_text}  {counter_text}")

        painter.end()

    def closeEvent(self, event) -> None:
        """
        FR: Arrête la lecture audio éventuelle à la fermeture du diaporama.
        EN: Stops any active audio playback when closing the slideshow.
        """
        if hasattr(self, "media_player") and self.media_player:
            self.media_player.stop()
            self.media_player.setSource(QUrl())
        super().closeEvent(event)
