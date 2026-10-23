"""
FR: Composant de création de films et films de visages pour PyCasa.
Reproduction fidèle de l'atelier de création de films (CMakeMoviePanel) et de films de visages (CMakeFaceMoviePanel) de Picasa 3.
EN: Movie Maker and Face Movie Component for PyCasa.
Faithful reproduction of Picasa 3's Movie Maker (CMakeMoviePanel) and Face Movie (CMakeFaceMoviePanel).

Ref: picasa3.exe @ MakeMoviePanel, CMakeMoviePanel, CMakeFaceMoviePanel
Ref: picasa3.exe @ CRenderMovie, ytDSMovieWriter, MoviePreviewHandler
Ref: picasa3.exe @ ID_MAKEMOVIE_INSERT, ID_MAKEMOVIE_REMOVE, ID_MAKEMOVIE_VIEWEDIT
Ref: ui/resources/xml/STRINGRES_FR.XML (CMakeMoviePanel::*, CMakeFaceMoviePanel::*, CTransitions::*)
"""

from __future__ import annotations
import math
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from PIL import Image
Image.MAX_IMAGE_PIXELS = None

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QCheckBox, QSlider, QFrame, QColorDialog, QMessageBox,
    QTabWidget, QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
    QFontComboBox, QSpinBox, QFileDialog, QProgressDialog, QSplitter,
    QApplication, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer, QUrl, QThread, QSize
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, QImage, QTransform,
    QPainterPath, QLinearGradient, QIcon
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle
from picasa_py.faces.facerect import FaceRect, decode_rect64_string
from picasa_py.ini.parser import PicasaIniParser


# FR: Résolutions prédéfinies / EN: Predefined resolutions (Ref: CMakeMoviePanel::size0 to size6)
MOVIE_RESOLUTIONS: List[Tuple[int, int, str, str]] = [
    (320, 240, "CMakeMoviePanel::size0", "320 x 240"),
    (640, 480, "CMakeMoviePanel::size1", "640 x 480"),
    (800, 600, "CMakeMoviePanel::size2", "800 x 600"),
    (1024, 768, "CMakeMoviePanel::size3", "1024 x 768"),
    (1600, 1200, "CMakeMoviePanel::size4", "1600 x 1200"),
    (1280, 720, "CMakeMoviePanel::size5", "1280 x 720 (720p)"),
    (1920, 1080, "CMakeMoviePanel::size6", "1920 x 1080 (1080p)"),
]

# FR: Options d'ajustement audio / EN: Audio fit options (Ref: CMakeMoviePanel::audiooption0 to audiooption2)
AUDIO_OPTIONS: List[Tuple[int, str, str]] = [
    (0, "CMakeMoviePanel::audiooption0", "Tronquer la piste audio"),
    (1, "CMakeMoviePanel::audiooption1", "Ajuster les photos à l'audio"),
    (2, "CMakeMoviePanel::audiooption2", "Faire défiler en boucle pour correspondre à l'audio"),
]

# FR: Transitions de film / EN: Movie transitions (Ref: CTransitions::*)
MOVIE_TRANSITIONS: List[Tuple[str, str, str]] = [
    ("kenburns", "CTransitions::kenburns", "Panoramique et zoom (Ken Burns)"),
    ("dissolve", "CTransitions::dissolve", "Fondu-enchaîné"),
    ("dissolveblack", "CTransitions::dissolveblack", "Fondu au noir"),
    ("dissolvewhite", "CTransitions::dissolvewhite", "Fondu au blanc"),
    ("wipe", "CTransitions::wiperight", "Volet"),
    ("circle", "CTransitions::circleout", "Cercle"),
    ("push", "CTransitions::pushleft", "Pousser"),
    ("cut", "CTransitions::cut", "Coupure"),
    ("timelapse", "CTransitions::timelapse", "Accéléré (Time Lapse)"),
]

# FR: Modèles de diapositives de texte / EN: Text slide templates (Ref: CMakeMoviePanel::textstyle0 to textstyle11)
TEXT_STYLES: List[Tuple[str, str, str]] = [
    ("centered", "CMakeMoviePanel::textstyle0", "Centré"),
    ("feeling_lucky", "CMakeMoviePanel::textstyle1", "J'ai de la chance"),
    ("caption", "CMakeMoviePanel::textstyle2", "Légende"),
    ("caption_classic", "CMakeMoviePanel::textstyle3", "Légende - Classique"),
    ("gradient_black", "CMakeMoviePanel::textstyle4", "Dégradé - Noir"),
    ("gradient_white", "CMakeMoviePanel::textstyle5", "Dégradé - Blanc"),
    ("transparent_black", "CMakeMoviePanel::textstyle6", "Transparent - Noir"),
    ("transparent_white", "CMakeMoviePanel::textstyle7", "Transparent - Blanc"),
    ("credits", "CMakeMoviePanel::textstyle8", "Générique défilant"),
    ("typewriter", "CMakeMoviePanel::textstyle11", "Machine à écrire"),
]


class MovieSlide:
    """
    FR: Représente une diapositive de la timeline du créateur de film.
    Peut être une photo ou une diapositive de texte insérée.
    EN: Represents a slide in the movie maker timeline.
    Can be a photo or an inserted text slide.
    Ref: MMFilm::ID_MAKEMOVIE_INSERT, CMakeMoviePanel::sampletext
    """
    def __init__(
        self,
        path: Optional[str] = None,
        is_text: bool = False,
        text: str = "",
        duration: float = 3.0,
        face_rect: Optional[FaceRect] = None,
        date_str: str = ""
    ):
        """
        FR: Initialise une diapositive (photo ou texte) avec sa durée et ses métadonnées de visage/date.
        EN: Initializes a slide (photo or text) with its duration and face/date metadata.
        """
        self.path: Optional[str] = path
        self.is_text: bool = is_text
        self.text: str = text or ("Texte" if is_text else "")
        self.duration: float = duration
        self.face_rect: Optional[FaceRect] = face_rect
        self.date_str: str = date_str

        # FR: Styles pour les diapositives de texte
        # EN: Styles for text slides
        self.text_style: str = "centered"
        self.font_family: str = "Arial"
        self.font_size: int = 28
        self.bold: bool = False
        self.italic: bool = False
        self.bg_color: QColor = QColor(24, 24, 26)
        self.text_color: QColor = QColor(255, 255, 255)

        # FR: Cache d'image
        # EN: Image cache
        self._cached_qimage: Optional[QImage] = None
        self._cached_thumb: Optional[QPixmap] = None

    def get_thumbnail(self, size: int = 80) -> QPixmap:
        """
        FR: Génère ou renvoie une miniature pour la timeline.
        EN: Generates or returns a thumbnail for the timeline.
        """
        if self._cached_thumb is not None:
            return self._cached_thumb

        if self.is_text:
            pix = QPixmap(size, int(size * 0.75))
            pix.fill(self.bg_color)
            painter = QPainter(pix)
            painter.setPen(self.text_color)
            f = QFont(self.font_family, 8)
            painter.setFont(f)
            painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.text[:20])
            painter.end()
            self._cached_thumb = pix
            return pix

        if self.path and os.path.exists(self.path):
            try:
                from picasa_py.ui.image_processor import PicasaImageProcessor
                img = PicasaImageProcessor.load_transformed_image(self.path, max_size=size)
                if img is not None:
                    self._cached_thumb = PicasaImageProcessor.pil_to_qpixmap(img)
                    return self._cached_thumb
            except Exception:
                pass

        pix = QPixmap(size, int(size * 0.75))
        pix.fill(QColor(60, 60, 60))
        self._cached_thumb = pix
        return pix


class PicasaMoviePreviewCanvas(QWidget):
    """
    FR: Canevas central de prévisualisation en temps réel du film.
    Gère la lecture fluide (30/60 Hz), les transitions Ken Burns, les fondus,
    l'alignement des visages (Face Movie) et le rendu des titres.
    EN: Central real-time movie preview canvas.
    Handles smooth playback (30/60 Hz), Ken Burns transitions, dissolves,
    face alignment (Face Movie), and title rendering.
    Ref: picasa3.exe @ MoviePreviewHandler, CRenderMovie, CMakeFaceMoviePanel
    """
    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise le canevas de prévisualisation et son minuteur de lecture à 30 Hz.
        EN: Initializes the preview canvas and its 30 Hz playback timer.
        """
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setStyleSheet("background-color: #121316;")

        self.slides: List[MovieSlide] = []
        self.transition_type: str = "kenburns"
        self._overlap_ratio: float = 0.35  # FR: Superposition (0.0 à 1.0) / EN: Overlap (0.0 to 1.0)
        self.crop_to_fit: bool = False
        self.show_captions: bool = False
        self.face_movie_mode: bool = False
        self.show_dates: bool = False
        self.resolution: Tuple[int, int] = (1280, 720)

        # FR: État de lecture
        # EN: Playback state
        self.is_playing: bool = False
        self.current_time_s: float = 0.0
        self.total_duration_s: float = 0.0

        # FR: Minuteur de rendu 30 Hz pour prévisualisation fluide
        # EN: 30 Hz render timer for smooth preview
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(33)  # ~30 FPS
        self.playback_timer.timeout.connect(self._on_tick)
        self._last_tick_time = time.time()

    @property
    def overlap_ratio(self) -> float:
        """
        FR: Retourne le ratio de superposition entre deux diapositives.
        EN: Returns the overlap ratio between two slides.
        """
        return self._overlap_ratio

    @overlap_ratio.setter
    def overlap_ratio(self, val: float) -> None:
        """
        FR: Définit le ratio de superposition (0.0 à 0.9) et recalcule la durée totale.
        EN: Sets the overlap ratio (0.0 to 0.9) and recomputes total duration.
        """
        self._overlap_ratio = max(0.0, min(0.9, val))
        self._recompute_total_duration()

    def set_slides(self, slides: List[MovieSlide]) -> None:
        """
        FR: Met à jour la liste des diapositives du film et recalcule la durée totale.
        EN: Updates the movie slide list and recomputes the total duration.
        """
        self.slides = slides
        self._recompute_total_duration()
        self.update()

    def _recompute_total_duration(self) -> None:
        """
        FR: Recalcule la durée totale du film en tenant compte de la superposition des transitions.
        EN: Recomputes total movie duration taking transition overlap into account.
        """
        if not self.slides:
            self.total_duration_s = 0.0
            return
        total = 0.0
        for i, s in enumerate(self.slides):
            overlap = (s.duration * self.overlap_ratio) if i > 0 else 0.0
            total += (s.duration - overlap)
        self.total_duration_s = max(0.1, total)

    def set_playback_time(self, t: float) -> None:
        """
        FR: Positionne la tête de lecture au temps `t` (en secondes) et rafraîchit le canevas.
        EN: Seeks the playhead to time `t` (in seconds) and refreshes the canvas.
        """
        self.current_time_s = max(0.0, min(self.total_duration_s, t))
        self.update()

    def play(self) -> None:
        """
        FR: Démarre la lecture de la prévisualisation du film.
        EN: Starts movie preview playback.
        """
        self.is_playing = True
        self._last_tick_time = time.time()
        self.playback_timer.start()

    def pause(self) -> None:
        """
        FR: Met en pause la lecture de la prévisualisation du film.
        EN: Pauses movie preview playback.
        """
        self.is_playing = False
        self.playback_timer.stop()
        self.update()

    def rewind(self) -> None:
        """
        FR: Rembobine la prévisualisation au début du film (t = 0.0 s).
        EN: Rewinds the preview to the beginning of the movie (t = 0.0 s).
        """
        self.current_time_s = 0.0
        self.update()

    def _on_tick(self) -> None:
        """
        FR: Avance le temps de lecture à chaque tick du minuteur et boucle en fin de film.
        EN: Advances playback time on each timer tick and loops at the end of the movie.
        """
        now = time.time()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        self.current_time_s += dt
        if self.current_time_s >= self.total_duration_s:
            self.current_time_s = 0.0  # FR: Boucler la prévisualisation / EN: Loop preview
        self.update()

    def get_current_slide_index(self) -> int:
        """
        FR: Trouve l'index de la diapositive principale active au temps t.
        EN: Finds the index of the active primary slide at time t.
        """
        if not self.slides:
            return 0
        t_accum = 0.0
        for i, s in enumerate(self.slides):
            overlap = (s.duration * self.overlap_ratio) if i > 0 else 0.0
            t_accum += (s.duration - overlap)
            if self.current_time_s <= t_accum:
                return i
        return len(self.slides) - 1

    def paintEvent(self, event) -> None:
        """
        FR: Dessine l'écran de prévisualisation du film avec bandes noires et informations d'état.
        EN: Paints the movie preview screen with letterbox bars and status overlay.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # FR: Fond noir profond de salle de projection
        # EN: Deep black projection room background
        painter.fillRect(self.rect(), QColor(14, 15, 18))

        if not self.slides:
            painter.setPen(QColor(160, 160, 160))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucune photo sélectionnée pour le film")
            painter.end()
            return

        # FR: Calculer le rectangle d'affichage 16:9 ou 4:3 avec bandes noires cinéma
        # EN: Compute the 16:9 or 4:3 display rectangle with cinema letterbox bars
        target_w, target_h = self.resolution
        target_aspect = target_w / float(target_h)

        avail_w = self.width() - 32
        avail_h = self.height() - 32
        avail_aspect = avail_w / float(max(1, avail_h))

        if avail_aspect > target_aspect:
            frame_h = avail_h
            frame_w = int(frame_h * target_aspect)
        else:
            frame_w = avail_w
            frame_h = int(frame_w / target_aspect)

        frame_x = (self.width() - frame_w) // 2
        frame_y = (self.height() - frame_h) // 2
        frame_rect = QRectF(frame_x, frame_y, frame_w, frame_h)

        # FR: Découpe cinéma
        # EN: Cinema clip frame
        painter.save()
        painter.setClipRect(frame_rect)
        painter.fillRect(frame_rect, QColor(0, 0, 0))

        # FR: Rendre la diapositive ou transition
        # EN: Render the slide or transition
        self._render_frame(painter, frame_rect)
        painter.restore()

        # FR: Bordure écran cinéma
        # EN: Cinema screen border
        pen = QPen(QColor(55, 60, 70), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(frame_rect)

        # FR: Incrustation informations / EN: Info overlay (Ref: CMakeMoviePanel::info1, CMakeMoviePanel::info3)
        curr_idx = self.get_current_slide_index()
        total_slides = len(self.slides)
        slide = self.slides[curr_idx]

        info_left = f"{Path(slide.path).name if slide.path else 'Titre'}   {target_w}x{target_h} pixels"
        info_right = f"({curr_idx + 1} sur {total_slides})"

        painter.setPen(QColor(180, 185, 195))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(int(frame_rect.left()), int(frame_rect.bottom() + 18), info_left)
        painter.drawText(
            QRectF(frame_rect.right() - 150, frame_rect.bottom() + 4, 150, 20),
            Qt.AlignmentFlag.AlignRight,
            info_right
        )

        painter.end()

    def _render_frame(self, painter: QPainter, rect: QRectF) -> None:
        """
        FR: Calcule l'état d'interpolation entre diapositives et effectue le rendu.
        EN: Computes the interpolation state between slides and performs rendering.
        """
        if not self.slides:
            return

        # FR: Déterminer les deux diapositives en transition ou la diapositive unique
        # EN: Determine the two transitioning slides or the single active slide
        t_accum = 0.0
        slide_a_idx = 0
        slide_b_idx = 0
        alpha = 0.0  # FR: 0.0 = A pur, 1.0 = B pur / EN: 0.0 = pure A, 1.0 = pure B

        for i, s in enumerate(self.slides):
            overlap = (s.duration * self.overlap_ratio) if i > 0 else 0.0
            slide_start = t_accum
            slide_end = slide_start + s.duration
            next_start = slide_end - overlap

            if i < len(self.slides) - 1 and self.current_time_s >= next_start:
                # FR: En transition avec la diapositive suivante
                # EN: Transitioning to the next slide
                slide_a_idx = i
                slide_b_idx = i + 1
                trans_len = max(0.01, overlap)
                alpha = min(1.0, max(0.0, (self.current_time_s - next_start) / trans_len))
                break
            elif self.current_time_s < slide_end or i == len(self.slides) - 1:
                slide_a_idx = i
                slide_b_idx = i
                alpha = 0.0
                break
            t_accum += (s.duration - overlap)

        # FR: Progrès interne de la diapositive pour Ken Burns (0.0 .. 1.0)
        # EN: Internal slide progress for Ken Burns (0.0 .. 1.0)
        dur = self.slides[slide_a_idx].duration
        prog_a = min(1.0, max(0.0, (self.current_time_s - t_accum) / max(0.1, dur)))

        if slide_a_idx == slide_b_idx or alpha <= 0.001:
            self._draw_slide(painter, rect, self.slides[slide_a_idx], prog_a, opacity=1.0)
        else:
            # FR: Rendu avec transition
            # EN: Render with transition
            self._render_transition(painter, rect, self.slides[slide_a_idx], self.slides[slide_b_idx], prog_a, alpha)

    def _render_transition(
        self,
        painter: QPainter,
        rect: QRectF,
        slide_a: MovieSlide,
        slide_b: MovieSlide,
        prog_a: float,
        alpha: float
    ) -> None:
        """
        FR: Applique la transition sélectionnée entre slide_a et slide_b.
        EN: Applies the selected transition between slide_a and slide_b.
        """
        t_type = "dissolve" if self.face_movie_mode else self.transition_type

        if t_type == "cut":
            chosen = slide_a if alpha < 0.5 else slide_b
            self._draw_slide(painter, rect, chosen, prog_a, opacity=1.0)
        elif t_type == "dissolveblack":
            if alpha < 0.5:
                sub_a = alpha * 2.0
                self._draw_slide(painter, rect, slide_a, prog_a, opacity=1.0 - sub_a)
            else:
                sub_b = (alpha - 0.5) * 2.0
                self._draw_slide(painter, rect, slide_b, 0.0, opacity=sub_b)
        elif t_type == "dissolvewhite":
            if alpha < 0.5:
                sub_a = alpha * 2.0
                self._draw_slide(painter, rect, slide_a, prog_a, opacity=1.0 - sub_a)
                painter.fillRect(rect, QColor(255, 255, 255, int(sub_a * 255)))
            else:
                sub_b = (alpha - 0.5) * 2.0
                self._draw_slide(painter, rect, slide_b, 0.0, opacity=sub_b)
                painter.fillRect(rect, QColor(255, 255, 255, int((1.0 - sub_b) * 255)))
        elif t_type == "wipe":
            # FR: Volet horizontal
            # EN: Horizontal wipe
            split_x = rect.left() + rect.width() * alpha
            # FR: Dessiner A / EN: Draw A
            self._draw_slide(painter, rect, slide_a, prog_a, opacity=1.0)
            # FR: Clip B sur la partie droite / EN: Clip B on the right side
            painter.save()
            painter.setClipRect(QRectF(rect.left(), rect.top(), split_x - rect.left(), rect.height()))
            self._draw_slide(painter, rect, slide_b, 0.0, opacity=1.0)
            painter.restore()
        elif t_type == "circle":
            # FR: Iris circulaire
            # EN: Circular iris
            max_radius = math.hypot(rect.width() / 2, rect.height() / 2)
            cur_radius = max_radius * alpha
            self._draw_slide(painter, rect, slide_a, prog_a, opacity=1.0)
            painter.save()
            path = QPainterPath()
            path.addEllipse(rect.center(), cur_radius, cur_radius)
            painter.setClipPath(path)
            self._draw_slide(painter, rect, slide_b, 0.0, opacity=1.0)
            painter.restore()
        elif t_type == "push":
            # FR: Pousser vers la gauche
            # EN: Push left
            shift = rect.width() * alpha
            painter.save()
            painter.translate(-shift, 0)
            self._draw_slide(painter, rect, slide_a, prog_a, opacity=1.0)
            painter.translate(rect.width(), 0)
            self._draw_slide(painter, rect, slide_b, 0.0, opacity=1.0)
            painter.restore()
        else:
            # FR: Fondu-enchaîné classique (Dissolve) ou Face Movie morph
            # EN: Classic cross-dissolve or Face Movie morph
            self._draw_slide(painter, rect, slide_a, prog_a, opacity=1.0)
            self._draw_slide(painter, rect, slide_b, 0.0, opacity=alpha)

    def _draw_slide(
        self,
        painter: QPainter,
        rect: QRectF,
        slide: MovieSlide,
        prog: float,
        opacity: float = 1.0
    ) -> None:
        """
        FR: Dessine une diapositive (photo avec Ken Burns/Face Movie ou diapositive de titre).
        EN: Draws a slide (photo with Ken Burns/Face Movie or title slide).
        """
        if opacity <= 0.001:
            return

        painter.save()
        if opacity < 0.999:
            painter.setOpacity(opacity)

        if slide.is_text:
            self._draw_text_slide(painter, rect, slide, prog)
        else:
            self._draw_photo_slide(painter, rect, slide, prog)

        # FR: Affichage légende si activé / EN: Display caption if enabled (Ref: CMakeMoviePanel::show_captions_label)
        if self.show_captions and not slide.is_text:
            cap_text = slide.text or (Path(slide.path).stem if slide.path else "")
            if cap_text:
                bar_h = 34.0
                bar_rect = QRectF(rect.left(), rect.bottom() - bar_h, rect.width(), bar_h)
                painter.fillRect(bar_rect, QColor(0, 0, 0, 160))
                painter.setPen(QColor(255, 255, 255, 240))
                painter.setFont(QFont("Segoe UI", 11))
                painter.drawText(bar_rect.adjusted(16, 0, -16, 0), Qt.AlignmentFlag.AlignCenter, cap_text)

        # FR: Affichage date EXIF si activé / EN: Display EXIF date if enabled (Ref: CMakeMoviePanel::show_dates_label)
        if self.show_dates and slide.date_str:
            painter.setPen(QColor(240, 240, 240, 220))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            date_rect = QRectF(rect.left() + 20, rect.bottom() - 36, rect.width() - 40, 24)
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignRight, slide.date_str)

        painter.restore()

    def _draw_photo_slide(
        self,
        painter: QPainter,
        rect: QRectF,
        slide: MovieSlide,
        prog: float
    ) -> None:
        """
        FR: Dessine une photo avec calcul exact du centrage visage (Face Movie) ou de l'effet Ken Burns.
        EN: Draws a photo with exact face centering calculation (Face Movie) or Ken Burns effect.
        """
        if not slide.path or not os.path.exists(slide.path):
            return

        # FR: Charger l'image si besoin (sous-échantillonnée à 960px pour prévisualisation 30 FPS)
        # EN: Load image if needed (sub-sampled to 960px for 30 FPS preview)
        if slide._cached_qimage is None:
            try:
                from picasa_py.ui.image_processor import PicasaImageProcessor
                im = PicasaImageProcessor.load_transformed_image(slide.path, max_size=960)
                if im is not None:
                    slide._cached_qimage = PicasaImageProcessor.pil_to_qimage(im)
                else:
                    return
            except Exception:
                return

        qimg = slide._cached_qimage
        if not qimg or qimg.isNull():
            return

        iw = float(qimg.width())
        ih = float(qimg.height())

        # FR: 1. Mode Film de visages (Face Movie)
        # EN: 1. Face Movie mode
        # Ref: CMakeFaceMoviePanel, alignement yeux/nez sur l'ancre fixe (0.50, 0.42)
        if self.face_movie_mode and slide.face_rect:
            fr = slide.face_rect
            # FR: Coordonnées du centre et hauteur du visage
            # EN: Center coordinates and face height
            fcx = (fr.left + fr.right) * 0.5 * iw
            fcy = (fr.top + fr.bottom) * 0.5 * ih
            fh = max(10.0, (fr.bottom - fr.top) * ih)

            # FR: Échelle désirée : la hauteur du visage doit occuper ~38% de la hauteur du cadre
            # EN: Desired scale: face height should occupy ~38% of the frame height
            target_fh = rect.height() * 0.38
            scale = target_fh / fh

            # FR: Point d'ancrage écran fixe : centre horizontal (50%), hauteur yeux (42%)
            # EN: Fixed screen anchor point: horizontal center (50%), eye level (42%)
            anchor_x = rect.left() + rect.width() * 0.50
            anchor_y = rect.top() + rect.height() * 0.42

            dest_x = anchor_x - fcx * scale
            dest_y = anchor_y - fcy * scale
            dest_w = iw * scale
            dest_h = ih * scale

            painter.drawImage(QRectF(dest_x, dest_y, dest_w, dest_h), qimg)
            return

        # FR: 2. Mode Ken Burns (Panoramique et zoom progressif fluide)
        # EN: 2. Ken Burns mode (Smooth progressive pan and zoom)
        # Ref: CTransitions::kenburns
        if self.transition_type == "kenburns":
            # FR: Lissage ease-in-out / EN: Ease-in-out smoothing
            ease_prog = 0.5 - 0.5 * math.cos(math.pi * prog)
            # FR: Déterminer la trajectoire selon l'indice du slide
            # EN: Determine trajectory based on slide index
            slide_idx = self.slides.index(slide) if slide in self.slides else 0
            is_zoom_in = (slide_idx % 2 == 0)

            scale_start = 1.05 if is_zoom_in else 1.25
            scale_end = 1.25 if is_zoom_in else 1.05
            scale_now = scale_start + (scale_end - scale_start) * ease_prog

            # FR: Ajustement de base (fill ou fit)
            # EN: Base fit adjustment (fill or fit)
            base_scale = max(rect.width() / iw, rect.height() / ih) if self.crop_to_fit else min(rect.width() / iw, rect.height() / ih)
            final_scale = base_scale * scale_now

            # FR: Déplacement panoramique lent
            # EN: Slow panning offset
            pan_dx = (rect.width() * 0.04) * (ease_prog - 0.5) if (slide_idx % 3 == 0) else (-rect.width() * 0.04) * (ease_prog - 0.5)
            pan_dy = (rect.height() * 0.03) * (ease_prog - 0.5)

            dw = iw * final_scale
            dh = ih * final_scale
            dx = rect.left() + (rect.width() - dw) / 2.0 + pan_dx
            dy = rect.top() + (rect.height() - dh) / 2.0 + pan_dy

            painter.drawImage(QRectF(dx, dy, dw, dh), qimg)
            return

        # FR: 3. Mode Standard (Fit ou Crop to fit)
        # EN: 3. Standard Mode (Fit or Crop to fit)
        if self.crop_to_fit:
            scale = max(rect.width() / iw, rect.height() / ih)
        else:
            scale = min(rect.width() / iw, rect.height() / ih)

        dw = iw * scale
        dh = ih * scale
        dx = rect.left() + (rect.width() - dw) / 2.0
        dy = rect.top() + (rect.height() - dh) / 2.0

        painter.drawImage(QRectF(dx, dy, dw, dh), qimg)

    def _draw_text_slide(
        self,
        painter: QPainter,
        rect: QRectF,
        slide: MovieSlide,
        prog: float
    ) -> None:
        """
        FR: Dessine une diapositive de texte selon le modèle choisi (Ref: CMakeMoviePanel::textstyle*).
        EN: Draws a text slide according to the selected template (Ref: CMakeMoviePanel::textstyle*).
        """
        st = slide.text_style

        # FR: Fond selon le modèle
        # EN: Background according to template
        if st in ("gradient_black", "textstyle4"):
            grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
            grad.setColorAt(0.0, QColor(45, 45, 50))
            grad.setColorAt(1.0, QColor(10, 10, 12))
            painter.fillRect(rect, grad)
        elif st in ("gradient_white", "textstyle5"):
            grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
            grad.setColorAt(0.0, QColor(250, 250, 252))
            grad.setColorAt(1.0, QColor(200, 205, 215))
            painter.fillRect(rect, grad)
        else:
            painter.fillRect(rect, slide.bg_color)

        # FR: Style de police
        # EN: Font style
        f = QFont(slide.font_family, slide.font_size)
        f.setBold(slide.bold)
        f.setItalic(slide.italic)
        painter.setFont(f)

        txt_col = slide.text_color
        if st in ("gradient_white", "textstyle5"):
            txt_col = QColor(25, 25, 30)
        painter.setPen(txt_col)

        # FR: Disposition du texte
        # EN: Text layout
        if st in ("caption", "caption_classic", "textstyle2", "textstyle3"):
            # FR: Bandeau inférieur semi-transparent
            # EN: Semi-transparent bottom banner
            bar_h = rect.height() * 0.22
            bar_rect = QRectF(rect.left(), rect.bottom() - bar_h, rect.width(), bar_h)
            painter.fillRect(bar_rect, QColor(0, 0, 0, 180))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(bar_rect.adjusted(24, 0, -24, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, slide.text)
        elif st in ("credits", "textstyle8"):
            # FR: Générique défilant du bas vers le haut
            # EN: Scrolling credits from bottom to top
            scroll_y = rect.bottom() - (rect.height() + 200) * prog
            cred_rect = QRectF(rect.left() + 40, scroll_y, rect.width() - 80, 400)
            painter.drawText(cred_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, slide.text)
        elif st in ("typewriter", "textstyle11"):
            # FR: Machine à écrire avec curseur clignotant
            # EN: Typewriter with blinking cursor
            chars_to_show = max(1, int(len(slide.text) * min(1.0, prog * 1.5)))
            visible_text = slide.text[:chars_to_show]
            if (int(prog * 10) % 2) == 0:
                visible_text += "▌"
            f_mono = QFont("Courier New", slide.font_size)
            painter.setFont(f_mono)
            painter.drawText(rect.adjusted(60, 40, -60, -40), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, visible_text)
        else:
            # FR: Centré par défaut
            # EN: Centered by default
            painter.drawText(rect.adjusted(40, 40, -40, -40), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, slide.text)


class PicasaTimelineThumbnail(QFrame):
    """
    FR: Vignette cliquable d'une diapositive dans le ruban inférieur.
    EN: Clickable thumbnail of a slide in the bottom timeline strip.
    """
    clicked = Signal(int)

    def __init__(self, index: int, slide: MovieSlide, parent: Optional[QWidget] = None):
        """
        FR: Initialise la vignette de la diapositive `index` dans la timeline.
        EN: Initializes the thumbnail of slide `index` in the timeline.
        """
        super().__init__(parent)
        self.index = index
        self.slide = slide
        self.is_selected: bool = False
        self.setFixedSize(76, 58)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_selected(self, val: bool) -> None:
        """
        FR: Définit l'état de sélection visuelle de la vignette et déclenche un redessin.
        EN: Sets the visual selection state of the thumbnail and triggers a repaint.
        """
        self.is_selected = val
        self.update()

    def mousePressEvent(self, event) -> None:
        """
        FR: Émet l'indice de la diapositive lors d'un clic gauche.
        EN: Emits the slide index on left-click.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        """
        FR: Dessine l'aperçu de la diapositive, le badge [T] éventuel, le numéro et la bordure de sélection.
        EN: Paints the slide preview, optional [T] badge, slide number, and selection border.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # FR: Dessin vignette
        # EN: Draw thumbnail
        thumb = self.slide.get_thumbnail(size=72)
        if thumb and not thumb.isNull():
            tx = (self.width() - thumb.width()) // 2
            ty = (self.height() - thumb.height()) // 2
            painter.drawPixmap(tx, ty, thumb)

        # FR: Indicateur diapositive texte [T]
        # EN: Text slide indicator [T]
        if self.slide.is_text:
            painter.fillRect(QRectF(4, 4, 16, 14), QColor(0, 0, 0, 160))
            painter.setPen(QColor(255, 215, 0))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(4, 4, 16, 14), Qt.AlignmentFlag.AlignCenter, "T")

        # FR: Numéro de diapositive
        # EN: Slide number
        num_str = str(self.index + 1)
        painter.fillRect(QRectF(self.width() - 20, self.height() - 16, 18, 14), QColor(0, 0, 0, 180))
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(self.width() - 20, self.height() - 16, 18, 14), Qt.AlignmentFlag.AlignCenter, num_str)

        # FR: Bordure de sélection bleue Picasa
        # EN: Picasa blue selection border
        if self.is_selected:
            painter.setPen(QPen(QColor(61, 133, 179), 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        else:
            painter.setPen(QPen(QColor(80, 85, 95), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        painter.end()


class MovieRenderWorker(QThread):
    """
    FR: Worker d'exportation vidéo en arrière-plan (CRenderMovie / ytDSMovieWriter).
    Génère un fichier vidéo .mp4 haute fidélité sans bloquer l'interface.
    EN: Background video export worker (CRenderMovie / ytDSMovieWriter).
    Generates a high-fidelity .mp4 video file without blocking the UI.
    """
    progress = Signal(int, int)  # current_frame, total_frames
    finished_success = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        slides: List[MovieSlide],
        output_path: str,
        resolution: Tuple[int, int] = (1280, 720),
        transition_type: str = "kenburns",
        overlap_ratio: float = 0.35,
        fps: int = 25,
        crop_to_fit: bool = False,
        face_movie_mode: bool = False,
        show_dates: bool = False,
        show_captions: bool = False
    ):
        """
        FR: Initialise le thread de rendu vidéo avec les diapositives et les paramètres d'encodage.
        EN: Initializes the video rendering thread with slides and encoding parameters.
        """
        super().__init__()
        self.slides = slides
        self.output_path = output_path
        self.resolution = resolution
        self.transition_type = transition_type
        self.overlap_ratio = overlap_ratio
        self.fps = fps
        self.crop_to_fit = crop_to_fit
        self.face_movie_mode = face_movie_mode
        self.show_dates = show_dates
        self.show_captions = show_captions
        self._is_cancelled = False

        # FR: Instanciation sur le thread principal GUI pour éviter toute violation QWidget dans QThread.run()
        # EN: Instantiate on the main GUI thread to avoid any QWidget thread violation inside QThread.run()
        self._render_canvas = PicasaMoviePreviewCanvas()
        self._render_canvas.set_slides(self.slides)
        self._render_canvas.resolution = self.resolution
        self._render_canvas.transition_type = self.transition_type
        self._render_canvas.overlap_ratio = self.overlap_ratio
        self._render_canvas.crop_to_fit = self.crop_to_fit
        self._render_canvas.face_movie_mode = self.face_movie_mode
        self._render_canvas.show_dates = self.show_dates
        self._render_canvas.show_captions = self.show_captions
        self._render_canvas._recompute_total_duration()

    def cancel(self) -> None:
        """
        FR: Demande l'annulation immédiate du rendu vidéo en cours.
        EN: Requests immediate cancellation of the ongoing video render.
        """
        self._is_cancelled = True

    def run(self) -> None:
        """
        FR: Exécute la boucle d'encodage image par image vers le fichier MP4.
        EN: Executes the frame-by-frame encoding loop to the MP4 file.
        """
        if not HAS_OPENCV:
            self.failed.emit("Bibliothèque OpenCV non disponible pour l'encodage vidéo.")
            return

        target_w, target_h = self.resolution
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(self.output_path, fourcc, float(self.fps), (target_w, target_h))

        if not writer.isOpened():
            self.failed.emit("Impossible d'initialiser l'enregistreur vidéo MP4.")
            return

        # FR: Calculer la durée totale
        # EN: Compute total duration
        total_time_s = 0.0
        for i, s in enumerate(self.slides):
            overlap = (s.duration * self.overlap_ratio) if i > 0 else 0.0
            total_time_s += (s.duration - overlap)

        total_frames = max(1, int(round(total_time_s * self.fps)))
        dt = 1.0 / float(self.fps)

        temp_canvas = self._render_canvas
        temp_canvas.resolution = self.resolution
        temp_canvas.transition_type = self.transition_type
        temp_canvas.overlap_ratio = self.overlap_ratio
        temp_canvas.crop_to_fit = self.crop_to_fit
        temp_canvas.face_movie_mode = self.face_movie_mode
        temp_canvas.show_dates = self.show_dates
        temp_canvas.show_captions = self.show_captions

        qimage = QImage(target_w, target_h, QImage.Format.Format_RGB888)

        for frame_idx in range(total_frames):
            if self._is_cancelled:
                writer.release()
                if os.path.exists(self.output_path):
                    try:
                        os.remove(self.output_path)
                    except Exception:
                        pass
                return

            t = frame_idx * dt
            temp_canvas.current_time_s = max(0.0, min(temp_canvas.total_duration_s, t))

            # FR: Rendu direct dans QImage
            # EN: Direct render into QImage
            qimage.fill(QColor(0, 0, 0))
            painter = QPainter(qimage)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            temp_canvas._render_frame(painter, QRectF(0, 0, target_w, target_h))
            painter.end()

            # FR: Conversion QImage vers NumPy BGR pour cv2
            # EN: Convert QImage to NumPy BGR for cv2
            ptr = qimage.bits()
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape((target_h, target_w, 3))
            bgr_frame = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            writer.write(bgr_frame)

            self.progress.emit(frame_idx + 1, total_frames)

        writer.release()
        self.finished_success.emit(self.output_path)


class PicasaMovieMakerDialog(QDialog):
    """
    FR: Atelier complet de création de films et diaporamas vidéo (CMakeMoviePanel).
    Prend en charge le mode diaporama classique et le mode Film de visages (CMakeFaceMoviePanel).
    EN: Complete Movie Maker and video slideshow workshop (CMakeMoviePanel).
    Supports classic slideshow mode and Face Movie mode (CMakeFaceMoviePanel).
    Ref: picasa3.exe @ MakeMoviePanel, CMakeMoviePanel, CMakeFaceMoviePanel
    """
    movie_created = Signal(str)

    def __init__(
        self,
        photo_paths: List[str],
        face_mode: bool = False,
        contact_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        """
        FR: Initialise l'atelier de création de films avec la sélection de photos et le mode (standard ou visages).
        EN: Initializes the Movie Maker workshop with the selected photos and mode (standard or Face Movie).
        """
        super().__init__(parent)
        self.face_mode = face_mode
        self.setWindowTitle("Créateur de films Picasa" if not face_mode else "Film de visages Picasa")
        self.resize(1120, 720)
        self.res_mgr = PicasaResourceManager.get()
        self.style = style or getattr(parent, "style", None) or PicasaStyle.instance()

        self.audio_path: Optional[str] = None
        self.media_player: Optional[QMediaPlayer] = None
        self.audio_output: Optional[QAudioOutput] = None
        self.selected_slide_index: int = 0

        # FR: Initialiser les diapositives
        # EN: Initialize slides
        self.slides: List[MovieSlide] = self._build_initial_slides(photo_paths, face_mode, contact_id)
        self._all_unfiltered_slides: List[MovieSlide] = list(self.slides)

        # FR: Configuration de l'interface
        # EN: Setup interface
        self._init_ui(face_mode)
        self._connect_signals()
        self.apply_style(self.style)

        # FR: Charger le premier slide
        # EN: Load the first slide
        self.canvas.set_slides(self.slides)
        self._update_timeline_strip()
        self._update_labels()

    def _build_initial_slides(
        self,
        paths: List[str],
        face_mode: bool,
        contact_id: Optional[str]
    ) -> List[MovieSlide]:
        """
        FR: Construit la liste initiale de `MovieSlide` en lisant les métadonnées `.picasa.ini` (visages, dates, légendes).
        EN: Builds the initial list of `MovieSlide` by reading `.picasa.ini` metadata (faces, dates, captions).
        """
        slides: List[MovieSlide] = []
        ini_cache: Dict[str, Any] = {}

        for p in paths:
            if not p or not os.path.exists(p):
                continue

            # FR: Trouver date et FaceRect éventuels depuis .picasa.ini
            # EN: Find optional date and FaceRect from .picasa.ini
            parent_dir = str(Path(p).parent)
            if parent_dir not in ini_cache:
                ini_p = Path(parent_dir) / ".picasa.ini"
                if ini_p.exists():
                    try:
                        ini_cache[parent_dir] = PicasaIniParser.parse_file(str(ini_p))
                    except Exception:
                        ini_cache[parent_dir] = None
                else:
                    ini_cache[parent_dir] = None

            doc = ini_cache.get(parent_dir)
            f_rect: Optional[FaceRect] = None
            date_str = ""
            caption_str = ""

            if doc:
                sec = doc.get_section(Path(p).name)
                if sec:
                    # FR: Visages / EN: Faces
                    faces_val = sec.get("faces")
                    if faces_val:
                        parts = faces_val.split(";")
                        for part in parts:
                            if "=" in part:
                                r_str, cid = part.split("=", 1)
                                if not contact_id or cid == contact_id:
                                    try:
                                        l, t, r, b = decode_rect64_string(r_str)
                                        f_rect = FaceRect(l, t, r, b, contact_id=cid)
                                        break
                                    except Exception:
                                        pass
                    # FR: Date & Légende / EN: Date & Caption
                    date_str = sec.get("date", "")
                    caption_str = sec.get("caption", "")

            # FR: Si date absente dans l'INI, tenter mtime
            # EN: If date is missing from INI, fall back to mtime
            if not date_str:
                try:
                    mtime = os.path.getmtime(p)
                    date_str = time.strftime("%d/%m/%Y", time.localtime(mtime))
                except Exception:
                    date_str = ""

            slides.append(MovieSlide(path=p, is_text=False, text=caption_str, duration=3.0, face_rect=f_rect, date_str=date_str))

        return slides

    def _init_ui(self, face_mode: bool) -> None:
        """
        FR: Construit la disposition principale (onglets de réglages, visualiseur central et timeline inférieure).
        EN: Builds the main layout (settings tabs, central previewer, and bottom timeline).
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # FR: 1. Zone supérieure divisée : Volet de réglages à gauche | Visualiseur à droite
        # EN: 1. Split top area: Settings pane on the left | Previewer on the right
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # FR: Onglets de réglages gauche / EN: Left settings tabs (Ref: makemoviepanel/tab1, tab2, tab3)
        self.tabs = QTabWidget()
        self.tabs.setFixedWidth(330)

        # Tab 1: Film (Movie settings)
        tab_movie = self._build_tab_movie()
        self.tabs.addTab(tab_movie, self.res_mgr.get_xml_string("makemoviepanel/tab1.title", "Film"))

        # Tab 2: Diapositive (Slide / Text settings)
        tab_slide = self._build_tab_slide()
        self.tabs.addTab(tab_slide, self.res_mgr.get_xml_string("makemoviepanel/tab2.title", "Diapositive"))

        # Tab 3: Options / Visages (Face Movie options)
        tab_options = self._build_tab_options(face_mode)
        self.tabs.addTab(tab_options, "Options")

        splitter.addWidget(self.tabs)

        # FR: Visualiseur central / EN: Central previewer
        preview_container = QWidget()
        v_prev = QVBoxLayout(preview_container)
        v_prev.setContentsMargins(0, 0, 0, 0)
        v_prev.setSpacing(6)

        self.canvas = PicasaMoviePreviewCanvas(self)
        self.canvas.face_movie_mode = face_mode
        v_prev.addWidget(self.canvas, 1)

        splitter.addWidget(preview_container)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, 1)

        # FR: 2. Ruban inférieur (Timeline / Clips strip)
        # EN: 2. Bottom strip (Timeline / Clips strip)
        # Ref: makemoviepanel/filmstrip, MMFilm::ID_MAKEMOVIE_*
        timeline_box = self._build_timeline_box()
        main_layout.addWidget(timeline_box)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème Picasa actif à l'atelier de création de films.
        EN: Dynamically applies the active Picasa theme to the movie maker workshop.
        """
        if style is not None:
            self.style = style
        self.setStyleSheet("""
            QDialog {
                background-color: #2D3035;
                color: #FFFFFF;
            }
            QTabWidget::pane {
                border: 1px solid #44474E;
                background-color: #26282C;
            }
            QTabBar::tab {
                background-color: #35383E;
                color: #BBBBBB;
                padding: 6px 14px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #26282C;
                color: #FFFFFF;
                border-bottom: 2px solid #3D85B3;
            }
            QPushButton {
                background-color: #3E434B;
                color: #FFFFFF;
                border: 1px solid #555B66;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4C525C;
            }
            QPushButton:pressed {
                background-color: #2D3137;
            }
            QPushButton#PrimaryBtn {
                background-color: #25648B;
                border: 1px solid #3D85B3;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #2F78A6;
            }
            QLabel, QCheckBox {
                color: #E0E0E0;
                font-size: 11px;
            }
            QComboBox, QSpinBox, QFontComboBox, QLineEdit, QTextEdit {
                background-color: #1E2024;
                color: #FFFFFF;
                border: 1px solid #484D56;
                border-radius: 3px;
                padding: 4px 6px;
                font-size: 9pt;
            }
            QComboBox QAbstractItemView {
                background-color: #1E2024;
                color: #FFFFFF;
                selection-background-color: #3D85B3;
                selection-color: #FFFFFF;
                font-size: 9pt;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #555B66;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #CCCCCC;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }
        """)

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes selon la langue active.
        EN: Updates texts according to the active language.
        """
        self.setWindowTitle("Créateur de films Picasa" if not self.face_mode else "Film de visages Picasa")
        self.tabs.setTabText(0, self.res_mgr.get_xml_string("makemoviepanel/tab1.title", "Film"))
        self.tabs.setTabText(1, self.res_mgr.get_xml_string("makemoviepanel/tab2.title", "Diapositive"))
        self.btn_create_movie.setText(self.res_mgr.get_xml_string("makemoviepanel/create.title", "Créer un film"))

    def _build_tab_movie(self) -> QWidget:
        """
        FR: Construit l'onglet « Film » (piste audio, style de transition, durée, superposition, dimensions).
        EN: Builds the "Movie" tab (audio track, transition style, duration, overlap, dimensions).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # FR: Piste audio / EN: Audio track (Ref: makemoviepanel/add_audio, remove_audio)
        lbl_audio = QLabel("Piste audio :")
        lbl_audio.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_audio)

        h_audio = QHBoxLayout()
        self.btn_load_audio = QPushButton("Charger...")
        self.btn_load_audio.clicked.connect(self._on_load_audio)
        self.btn_remove_audio = QPushButton("Supprimer")
        self.btn_remove_audio.clicked.connect(self._on_remove_audio)
        self.btn_remove_audio.setEnabled(False)
        h_audio.addWidget(self.btn_load_audio)
        h_audio.addWidget(self.btn_remove_audio)
        layout.addLayout(h_audio)

        self.lbl_audio_name = QLabel("Aucun morceau sélectionné")
        self.lbl_audio_name.setStyleSheet("color: #999999; font-size: 10px;")
        layout.addWidget(self.lbl_audio_name)

        # FR: Options audio / EN: Audio options (Ref: CMakeMoviePanel::audiooption*)
        self.cb_audio_opts = QComboBox()
        for idx, key, label in AUDIO_OPTIONS:
            self.cb_audio_opts.addItem(label, idx)
        self.cb_audio_opts.currentIndexChanged.connect(self._on_audio_option_changed)
        layout.addWidget(self.cb_audio_opts)

        layout.addSpacing(6)

        # FR: Style de transition / EN: Transition style (Ref: CTransitions::*)
        lbl_trans = QLabel("Style de transition :")
        lbl_trans.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_trans)

        self.cb_transitions = QComboBox()
        for code, key, label in MOVIE_TRANSITIONS:
            self.cb_transitions.addItem(label, code)
        self.cb_transitions.currentIndexChanged.connect(self._on_transition_changed)
        layout.addWidget(self.cb_transitions)

        # FR: Curseur de durée de chaque diapositive / EN: Slide duration slider (Ref: CMakeMoviePanel::slideduration)
        self.lbl_slide_dur = QLabel("Durée de chaque diapositive : 3.0 s")
        layout.addWidget(self.lbl_slide_dur)

        self.slider_slide_dur = QSlider(Qt.Orientation.Horizontal)
        self.slider_slide_dur.setRange(10, 100)  # FR: 1.0s à 10.0s (dixièmes de seconde) / EN: 1.0s to 10.0s (tenths of a second)
        self.slider_slide_dur.setValue(30)
        self.slider_slide_dur.valueChanged.connect(self._on_slide_duration_changed)
        layout.addWidget(self.slider_slide_dur)

        # FR: Curseur de superposition / fondu / EN: Overlap / cross-fade slider (Ref: CMakeMoviePanel::transitionsspeed)
        self.lbl_overlap = QLabel("Superposition : 35%")
        layout.addWidget(self.lbl_overlap)

        self.slider_overlap = QSlider(Qt.Orientation.Horizontal)
        self.slider_overlap.setRange(0, 80)  # 0% à 80%
        self.slider_overlap.setValue(35)
        self.slider_overlap.valueChanged.connect(self._on_overlap_changed)
        layout.addWidget(self.slider_overlap)

        layout.addSpacing(6)

        # FR: Dimensions du film / EN: Movie dimensions (Ref: CMakeMoviePanel::size*)
        lbl_dims = QLabel("Dimensions du film :")
        lbl_dims.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_dims)

        self.cb_resolution = QComboBox()
        for w_res, h_res, key, label in MOVIE_RESOLUTIONS:
            self.cb_resolution.addItem(label, (w_res, h_res))
        self.cb_resolution.setCurrentIndex(5)  # FR: 720p par défaut / EN: 720p by default
        self.cb_resolution.currentIndexChanged.connect(self._on_resolution_changed)
        layout.addWidget(self.cb_resolution)

        # FR: Cases à cocher options / EN: Option checkboxes
        self.chk_crop_fit = QCheckBox("Recadrer pour ajuster (plein cadre)")
        self.chk_crop_fit.toggled.connect(self._on_crop_fit_toggled)
        layout.addWidget(self.chk_crop_fit)

        self.chk_show_captions = QCheckBox("Afficher les légendes")
        self.chk_show_captions.toggled.connect(self._on_show_captions_toggled)
        layout.addWidget(self.chk_show_captions)

        layout.addStretch(1)

        # FR: Boutons d'exportation / EN: Export buttons
        self.btn_create_movie = QPushButton("Créer un film")
        self.btn_create_movie.setObjectName("PrimaryBtn")
        self.btn_create_movie.clicked.connect(self.export_movie)
        layout.addWidget(self.btn_create_movie)

        return w

    def _build_tab_slide(self) -> QWidget:
        """
        FR: Construit l'onglet « Diapositive » (texte de diapositive, style de modèle, police, taille, couleur).
        EN: Builds the "Slide" tab (slide text, template style, font, size, color).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_edit = QLabel("Texte de la diapositive :")
        lbl_edit.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_edit)

        self.edit_slide_text = QTextEdit()
        self.edit_slide_text.setPlaceholderText("Saisissez le texte du titre ou de la diapositive...")
        self.edit_slide_text.setFixedHeight(80)
        self.edit_slide_text.textChanged.connect(self._on_slide_text_edited)
        layout.addWidget(self.edit_slide_text)

        # FR: Modèles de style / EN: Style templates (Ref: CMakeMoviePanel::textstyle0 to textstyle11)
        lbl_tmpl = QLabel("Style de modèle :")
        lbl_tmpl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_tmpl)

        self.cb_text_style = QComboBox()
        for code, key, label in TEXT_STYLES:
            self.cb_text_style.addItem(label, code)
        self.cb_text_style.currentIndexChanged.connect(self._on_text_style_changed)
        layout.addWidget(self.cb_text_style)

        # FR: Police et taille / EN: Font and size
        h_font = QHBoxLayout()
        self.font_picker = QFontComboBox()
        self.font_picker.setCurrentFont(QFont("Arial", 10))
        self.font_picker.currentFontChanged.connect(self._on_font_changed)
        h_font.addWidget(self.font_picker)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(12, 96)
        self.spin_font_size.setValue(28)
        self.spin_font_size.valueChanged.connect(self._on_font_size_changed)
        h_font.addWidget(self.spin_font_size)
        layout.addLayout(h_font)

        # FR: Boutons Gras / Italique / Couleur / EN: Bold / Italic / Color buttons
        h_style = QHBoxLayout()
        self.btn_bold = QPushButton("Gras")
        self.btn_bold.setCheckable(True)
        self.btn_bold.clicked.connect(self._on_bold_toggled)
        h_style.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("Italique")
        self.btn_italic.setCheckable(True)
        self.btn_italic.clicked.connect(self._on_italic_toggled)
        h_style.addWidget(self.btn_italic)

        self.btn_color = QPushButton("■ Couleur fond")
        self.btn_color.clicked.connect(self._on_pick_bg_color)
        h_style.addWidget(self.btn_color)
        layout.addLayout(h_style)

        layout.addStretch(1)
        return w

    def _build_tab_options(self, initial_face_mode: bool) -> QWidget:
        """
        FR: Construit l'onglet « Options » (centrage Face Movie, filtrage temporel des rafales, affichage des dates).
        EN: Builds the "Options" tab (Face Movie centering, burst time filtering, date display).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # FR: Film de visages (Face Movie) / EN: Face Movie (Ref: CMakeFaceMoviePanel)
        lbl_face = QLabel("Film de visages (Face Movie) :")
        lbl_face.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_face)

        self.chk_face_movie = QCheckBox("Activer le centrage automatique des visages")
        self.chk_face_movie.setChecked(initial_face_mode)
        self.chk_face_movie.toggled.connect(self._on_face_movie_toggled)
        layout.addWidget(self.chk_face_movie)

        lbl_desc = QLabel(
            "Aligne parfaitement les yeux et le nez de chaque photo sur une position fixe "
            "pour un morphing fluide entre les âges et les expressions."
        )
        lbl_desc.setStyleSheet("color: #A0A8B4; font-size: 10px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        layout.addSpacing(10)

        # FR: Filtre de rafale / EN: Burst filter (Ref: CMakeMoviePanel::movieburst)
        lbl_burst = QLabel("Filtrage temporel :")
        lbl_burst.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_burst)

        self.cb_burst = QComboBox()
        self.cb_burst.addItem("Ne pas filtrer selon le temps passé (tout garder)", 0)
        self.cb_burst.addItem("Supprimer les photos prises dans un intervalle de 1 seconde", 1)
        self.cb_burst.addItem("Supprimer les photos prises dans un intervalle de 5 secondes", 5)
        self.cb_burst.addItem("Supprimer les photos prises dans un intervalle de 1 minute", 60)
        self.cb_burst.currentIndexChanged.connect(self._on_burst_filter_changed)
        layout.addWidget(self.cb_burst)

        layout.addSpacing(10)

        # FR: Affichage dates / EN: Date display (Ref: CMakeMoviePanel::show_dates_label)
        self.chk_show_dates = QCheckBox("Afficher les dates des photos à l'écran")
        self.chk_show_dates.toggled.connect(self._on_show_dates_toggled)
        layout.addWidget(self.chk_show_dates)

        layout.addStretch(1)
        return w

    def _build_timeline_box(self) -> QWidget:
        """
        FR: Construit le bandeau inférieur de la timeline avec les commandes d'édition et de lecture.
        EN: Builds the bottom timeline panel with editing and playback transport controls.
        """
        panel = QFrame()
        panel.setFixedHeight(115)
        panel.setStyleSheet("background-color: #202226; border-top: 1px solid #3A3D44;")

        v_layout = QVBoxLayout(panel)
        v_layout.setContentsMargins(10, 6, 10, 6)
        v_layout.setSpacing(4)

        # FR: Barre d'actions timeline / EN: Timeline action bar
        h_tools = QHBoxLayout()
        self.lbl_clips_count = QLabel("Clips (0)")
        self.lbl_clips_count.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        h_tools.addWidget(self.lbl_clips_count)

        h_tools.addSpacing(14)

        self.btn_insert_text = QPushButton("➕ Insérer une diapositive (texte)")
        self.btn_insert_text.clicked.connect(self._on_insert_text_slide)
        h_tools.addWidget(self.btn_insert_text)

        self.btn_delete_slide = QPushButton("✖ Supprimer")
        self.btn_delete_slide.clicked.connect(self._on_delete_selected_slide)
        h_tools.addWidget(self.btn_delete_slide)

        self.btn_move_left = QPushButton("◀")
        self.btn_move_left.setToolTip("Déplacer la diapositive vers la gauche")
        self.btn_move_left.clicked.connect(self._on_move_left)
        h_tools.addWidget(self.btn_move_left)

        self.btn_move_right = QPushButton("▶")
        self.btn_move_right.setToolTip("Déplacer la diapositive vers la droite")
        self.btn_move_right.clicked.connect(self._on_move_right)
        h_tools.addWidget(self.btn_move_right)

        h_tools.addStretch(1)

        # FR: Commandes de lecture (Transport) / EN: Playback transport controls
        self.btn_rewind = QPushButton("⏮")
        self.btn_rewind.setToolTip("Retour au début")
        self.btn_rewind.clicked.connect(self._on_rewind)
        h_tools.addWidget(self.btn_rewind)

        self.btn_play_pause = QPushButton("▶")
        self.btn_play_pause.setToolTip("Lecture / Pause")
        self.btn_play_pause.clicked.connect(self._on_play_pause_toggled)
        h_tools.addWidget(self.btn_play_pause)

        self.lbl_time_pos = QLabel("00:00 / 00:00")
        self.lbl_time_pos.setStyleSheet("color: #A0A8B4; font-size: 11px;")
        h_tools.addWidget(self.lbl_time_pos)

        v_layout.addLayout(h_tools)

        # FR: Ruban horizontal des vignettes scrollable / EN: Scrollable horizontal thumbnail strip
        self.scroll_timeline = QScrollArea()
        self.scroll_timeline.setFixedHeight(70)
        self.scroll_timeline.setWidgetResizable(True)
        self.scroll_timeline.setStyleSheet("background-color: transparent; border: none;")

        self.timeline_container = QWidget()
        self.timeline_layout = QHBoxLayout(self.timeline_container)
        self.timeline_layout.setContentsMargins(4, 2, 4, 2)
        self.timeline_layout.setSpacing(6)
        self.timeline_layout.addStretch(1)

        self.scroll_timeline.setWidget(self.timeline_container)
        v_layout.addWidget(self.scroll_timeline)

        return panel

    def _connect_signals(self) -> None:
        """
        FR: Connecte le minuteur de lecture du canevas à la mise à jour de l'indicateur temporel.
        EN: Connects the canvas playback timer to the time indicator label update.
        """
        self.canvas.playback_timer.timeout.connect(self._update_time_label)

    def _update_labels(self) -> None:
        """
        FR: Met à jour le nombre de clips et l'état d'activation des boutons d'organisation de la timeline.
        EN: Updates the clip count and the enabled state of timeline reordering buttons.
        """
        count = len(self.slides)
        self.lbl_clips_count.setText(f"Clips ({count})")
        self.btn_delete_slide.setEnabled(count > 0)
        self.btn_move_left.setEnabled(count > 1 and self.selected_slide_index > 0)
        self.btn_move_right.setEnabled(count > 1 and self.selected_slide_index < count - 1)
        self._update_time_label()

    def _update_time_label(self) -> None:
        """
        FR: Met à jour l'affichage MM:SS de la position actuelle et de la durée totale.
        EN: Updates the MM:SS display of the current playback position and total duration.
        """
        cur_m = int(self.canvas.current_time_s) // 60
        cur_s = int(self.canvas.current_time_s) % 60
        tot_m = int(self.canvas.total_duration_s) // 60
        tot_s = int(self.canvas.total_duration_s) % 60
        self.lbl_time_pos.setText(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}")

    def _update_timeline_strip(self) -> None:
        """
        FR: Reconstruit la bande de vignettes de la timeline à partir de la liste actuelle des diapositives.
        EN: Rebuilds the timeline thumbnail strip from the current list of slides.
        """
        # FR: Vider les widgets existants sauf le stretch
        # EN: Clear existing widgets except the stretch
        while self.timeline_layout.count() > 1:
            item = self.timeline_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for idx, slide in enumerate(self.slides):
            thumb_w = PicasaTimelineThumbnail(idx, slide, parent=self.timeline_container)
            thumb_w.set_selected(idx == self.selected_slide_index)
            thumb_w.clicked.connect(self._on_timeline_thumb_clicked)
            self.timeline_layout.insertWidget(idx, thumb_w)

        self._update_labels()

    def _on_timeline_thumb_clicked(self, idx: int) -> None:
        """
        FR: Sélectionne la diapositive `idx` dans la timeline et positionne l'aperçu au début de celle-ci.
        EN: Selects slide `idx` in the timeline and seeks the preview to its start.
        """
        if idx < 0 or idx >= len(self.slides):
            return
        self.selected_slide_index = idx

        # FR: Mettre à jour la sélection visuelle
        # EN: Update visual selection
        for i in range(self.timeline_layout.count() - 1):
            w = self.timeline_layout.itemAt(i).widget()
            if isinstance(w, PicasaTimelineThumbnail):
                w.set_selected(w.index == idx)

        slide = self.slides[idx]
        if slide.is_text:
            self.tabs.setCurrentIndex(1)  # FR: Ouvrir l'onglet Diapositive / EN: Open Slide tab
            self.edit_slide_text.blockSignals(True)
            self.edit_slide_text.setPlainText(slide.text)
            self.edit_slide_text.blockSignals(False)

        # FR: Positionner le canevas au début de cette diapositive
        # EN: Position the canvas at the beginning of this slide
        t_pos = 0.0
        for i in range(idx):
            overlap = (self.slides[i].duration * self.canvas.overlap_ratio) if i > 0 else 0.0
            t_pos += (self.slides[i].duration - overlap)

        self.canvas.set_playback_time(t_pos)
        self._update_labels()

    def _on_play_pause_toggled(self) -> None:
        """
        FR: Bascule entre la lecture et la pause de la prévisualisation vidéo et audio.
        EN: Toggles between play and pause for video and audio preview.
        """
        if self.canvas.is_playing:
            self.canvas.pause()
            self.btn_play_pause.setText("▶")
            if self.media_player:
                self.media_player.pause()
        else:
            self.canvas.play()
            self.btn_play_pause.setText("❚❚")
            if self.media_player:
                self.media_player.play()

    def _on_rewind(self) -> None:
        """
        FR: Rembobine la vidéo et la piste audio au début.
        EN: Rewinds video and audio track to the beginning.
        """
        self.canvas.rewind()
        if self.media_player:
            self.media_player.setPosition(0)
        self._update_time_label()

    def _on_transition_changed(self) -> None:
        """
        FR: Applique le nouveau style de transition sélectionné dans la liste déroulante.
        EN: Applies the newly selected transition style from the combo box.
        """
        self.canvas.transition_type = self.cb_transitions.currentData()
        self.canvas.update()

    def _on_slide_duration_changed(self, val: int) -> None:
        """
        FR: Met à jour la durée individuelle des diapositives selon la position du curseur.
        EN: Updates individual slide duration according to the slider value.
        """
        dur = val / 10.0
        self.lbl_slide_dur.setText(f"Durée de chaque diapositive : {dur:.1f} s")
        for s in self.slides:
            s.duration = dur
        self.canvas._recompute_total_duration()
        self._update_time_label()
        self.canvas.update()

    def _on_overlap_changed(self, val: int) -> None:
        """
        FR: Met à jour le pourcentage de superposition entre les diapositives.
        EN: Updates the overlap percentage between slides.
        """
        ratio = val / 100.0
        self.lbl_overlap.setText(f"Superposition : {val}%")
        self.canvas.overlap_ratio = ratio
        self.canvas._recompute_total_duration()
        self._update_time_label()
        self.canvas.update()

    def _on_resolution_changed(self) -> None:
        """
        FR: Met à jour la résolution cible du film (ex. 720p, 1080p).
        EN: Updates the target movie resolution (e.g., 720p, 1080p).
        """
        self.canvas.resolution = self.cb_resolution.currentData()
        self.canvas.update()

    def _on_crop_fit_toggled(self, checked: bool) -> None:
        """
        FR: Active ou désactive le recadrage plein cadre des photos.
        EN: Enables or disables full-frame crop-to-fit for photos.
        """
        self.canvas.crop_to_fit = checked
        self.canvas.update()

    def _on_show_captions_toggled(self, checked: bool) -> None:
        """
        FR: Active ou désactive l'affichage des légendes sur les photos.
        EN: Enables or disables displaying captions over photos.
        """
        self.canvas.show_captions = checked
        self.canvas.update()

    def _on_face_movie_toggled(self, checked: bool) -> None:
        """
        FR: Active ou désactive le mode d'alignement automatique des visages (Face Movie).
        EN: Enables or disables automatic face alignment mode (Face Movie).
        """
        self.canvas.face_movie_mode = checked
        self.canvas.update()

    def _on_burst_filter_changed(self) -> None:
        """
        FR: Filtre les photos prises en rafale selon l'intervalle temporel minimal choisi.
        EN: Filters burst photos according to the selected minimum time interval.
        """
        if not hasattr(self, "_all_unfiltered_slides") or not self._all_unfiltered_slides:
            self._all_unfiltered_slides = list(self.slides)

        interval_s = self.cb_burst.currentData()
        if interval_s is None or interval_s <= 0:
            self.slides = list(self._all_unfiltered_slides)
            self.selected_slide_index = max(0, min(self.selected_slide_index, max(0, len(self.slides) - 1)))
            self.canvas.set_slides(self.slides)
            self._update_timeline_strip()
            return
        # FR: Filtrer les photos prises trop rapprochées à partir de la liste complète non filtrée
        # EN: Filter out photos taken too close together in time from the full unfiltered list
        filtered: List[MovieSlide] = []
        last_t = 0.0
        for s in self._all_unfiltered_slides:
            if s.is_text or not s.path:
                filtered.append(s)
                continue
            try:
                mt = os.path.getmtime(s.path)
                if abs(mt - last_t) >= interval_s:
                    filtered.append(s)
                    last_t = mt
            except Exception:
                filtered.append(s)
        self.slides = filtered
        self.selected_slide_index = max(0, min(self.selected_slide_index, max(0, len(self.slides) - 1)))
        self.canvas.set_slides(self.slides)
        self._update_timeline_strip()

    def _on_show_dates_toggled(self, checked: bool) -> None:
        """
        FR: Active ou désactive l'incrustation des dates des photos à l'écran.
        EN: Enables or disables overlaying photo dates on screen.
        """
        self.canvas.show_dates = checked
        self.canvas.update()

    def _on_insert_text_slide(self) -> None:
        """
        FR: Insère une nouvelle diapositive de texte après la diapositive sélectionnée.
        EN: Inserts a new text slide after the currently selected slide.
        """
        ts = MovieSlide(is_text=True, text="Titre du film", duration=3.5)
        insert_idx = self.selected_slide_index + 1 if self.slides else 0
        self.slides.insert(insert_idx, ts)
        if hasattr(self, "_all_unfiltered_slides"):
            self._all_unfiltered_slides.insert(min(insert_idx, len(self._all_unfiltered_slides)), ts)
        self.canvas.set_slides(self.slides)
        self.selected_slide_index = insert_idx
        self._update_timeline_strip()
        self._on_timeline_thumb_clicked(insert_idx)

    def _on_delete_selected_slide(self) -> None:
        """
        FR: Supprime la diapositive actuellement sélectionnée dans la timeline.
        EN: Deletes the currently selected slide from the timeline.
        """
        if not self.slides or self.selected_slide_index >= len(self.slides):
            return
        removed_slide = self.slides.pop(self.selected_slide_index)
        if hasattr(self, "_all_unfiltered_slides") and removed_slide in self._all_unfiltered_slides:
            self._all_unfiltered_slides.remove(removed_slide)
        self.selected_slide_index = max(0, min(self.selected_slide_index, len(self.slides) - 1))
        self.canvas.set_slides(self.slides)
        self._update_timeline_strip()
        if self.slides:
            self._on_timeline_thumb_clicked(self.selected_slide_index)

    def _on_move_left(self) -> None:
        """
        FR: Déplace la diapositive sélectionnée d'un cran vers la gauche dans la timeline.
        EN: Moves the selected slide one position to the left in the timeline.
        """
        idx = self.selected_slide_index
        if idx > 0 and idx < len(self.slides):
            self.slides[idx], self.slides[idx - 1] = self.slides[idx - 1], self.slides[idx]
            self.selected_slide_index = idx - 1
            self.canvas.set_slides(self.slides)
            self._update_timeline_strip()
            self._on_timeline_thumb_clicked(self.selected_slide_index)

    def _on_move_right(self) -> None:
        """
        FR: Déplace la diapositive sélectionnée d'un cran vers la droite dans la timeline.
        EN: Moves the selected slide one position to the right in the timeline.
        """
        idx = self.selected_slide_index
        if idx >= 0 and idx < len(self.slides) - 1:
            self.slides[idx], self.slides[idx + 1] = self.slides[idx + 1], self.slides[idx]
            self.selected_slide_index = idx + 1
            self.canvas.set_slides(self.slides)
            self._update_timeline_strip()
            self._on_timeline_thumb_clicked(self.selected_slide_index)

    def _on_slide_text_edited(self) -> None:
        """
        FR: Met à jour le texte de la diapositive sélectionnée lors de la saisie.
        EN: Updates the text of the selected slide when edited.
        """
        if self.slides and self.selected_slide_index < len(self.slides):
            s = self.slides[self.selected_slide_index]
            s.text = self.edit_slide_text.toPlainText()
            s._cached_thumb = None
            self.canvas.update()
            self._update_timeline_strip()

    def _on_text_style_changed(self) -> None:
        """
        FR: Applique le modèle de présentation de texte choisi à la diapositive sélectionnée.
        EN: Applies the selected text layout template to the current slide.
        """
        if self.slides and self.selected_slide_index < len(self.slides):
            s = self.slides[self.selected_slide_index]
            s.text_style = self.cb_text_style.currentData()
            s._cached_thumb = None
            self.canvas.update()

    def _on_font_changed(self, font: QFont) -> None:
        """
        FR: Change la famille de police de la diapositive sélectionnée.
        EN: Changes the font family of the selected slide.
        """
        if self.slides and self.selected_slide_index < len(self.slides):
            s = self.slides[self.selected_slide_index]
            s.font_family = font.family()
            self.canvas.update()

    def _on_font_size_changed(self, size: int) -> None:
        """
        FR: Change la taille de police de la diapositive sélectionnée.
        EN: Changes the font size of the selected slide.
        """
        if self.slides and self.selected_slide_index < len(self.slides):
            s = self.slides[self.selected_slide_index]
            s.font_size = size
            self.canvas.update()

    def _on_bold_toggled(self, checked: bool) -> None:
        """
        FR: Active ou désactive le style gras sur le texte de la diapositive sélectionnée.
        EN: Toggles bold style on the selected slide's text.
        """
        if self.slides and self.selected_slide_index < len(self.slides):
            s = self.slides[self.selected_slide_index]
            s.bold = checked
            self.canvas.update()

    def _on_italic_toggled(self, checked: bool) -> None:
        """
        FR: Active ou désactive le style italique sur le texte de la diapositive sélectionnée.
        EN: Toggles italic style on the selected slide's text.
        """
        if self.slides and self.selected_slide_index < len(self.slides):
            s = self.slides[self.selected_slide_index]
            s.italic = checked
            self.canvas.update()

    def _on_pick_bg_color(self) -> None:
        """
        FR: Ouvre un sélecteur de couleur pour modifier l'arrière-plan de la diapositive de titre.
        EN: Opens a color picker to change the title slide background color.
        """
        if self.slides and self.selected_slide_index < len(self.slides):
            s = self.slides[self.selected_slide_index]
            col = QColorDialog.getColor(s.bg_color, self, "Couleur d'arrière-plan du titre")
            if col.isValid():
                s.bg_color = col
                s._cached_thumb = None
                self.canvas.update()
                self._update_timeline_strip()

    def _on_load_audio(self) -> None:
        """
        FR: Ouvre une boîte de dialogue pour sélectionner et charger un fichier musical d'accompagnement.
        EN: Opens a file dialog to select and load a background audio track.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un morceau audio pour le film",
            "",
            "Fichiers audio (*.mp3 *.wma *.m4a *.wav *.ogg)"
        )
        if file_path and os.path.exists(file_path):
            self.audio_path = file_path
            self.lbl_audio_name.setText(Path(file_path).name)
            self.btn_remove_audio.setEnabled(True)

            if HAS_MULTIMEDIA:
                try:
                    if self.media_player is None:
                        self.audio_output = QAudioOutput(self)
                        self.media_player = QMediaPlayer(self)
                        self.media_player.setAudioOutput(self.audio_output)
                        self.media_player.durationChanged.connect(lambda _d: self._on_audio_option_changed())
                    self.media_player.setSource(QUrl.fromLocalFile(file_path))
                except Exception:
                    self.media_player = None
            self._on_audio_option_changed()

    def _on_remove_audio(self) -> None:
        """
        FR: Supprime la piste audio associée au film et arrête la lecture.
        EN: Removes the audio track associated with the movie and stops playback.
        """
        self.audio_path = None
        self.lbl_audio_name.setText("Aucun morceau sélectionné")
        self.btn_remove_audio.setEnabled(False)
        if self.media_player:
            self.media_player.stop()

    def _on_audio_option_changed(self) -> None:
        """
        FR: Adapte les durées des diapositives selon le mode de synchronisation audio choisi.
        EN: Adapts slide durations according to the selected audio synchronization mode.
        Ref: picasa3.exe @ CMakeMoviePanel::audiooption0..2
        """
        opt = self.cb_audio_opts.currentData()
        if opt == 1 and self.slides:
            # FR: Ajuster les photos à l'audio / EN: Fit photos to audio
            audio_dur_s = 0.0
            if self.media_player and self.media_player.duration() > 0:
                audio_dur_s = self.media_player.duration() / 1000.0
            if audio_dur_s > 0.5:
                n = len(self.slides)
                ov = self.canvas.overlap_ratio
                # total_duration = n * d - (n - 1) * d * ov = d * (n - (n - 1) * ov)
                denom = max(0.1, n - (n - 1) * ov)
                per_slide = max(1.0, min(15.0, audio_dur_s / denom))
                for s in self.slides:
                    s.duration = per_slide
                self.slider_slide_dur.blockSignals(True)
                self.slider_slide_dur.setValue(int(round(per_slide * 10)))
                self.slider_slide_dur.blockSignals(False)
                self.lbl_slide_dur.setText(f"Durée de chaque diapositive : {per_slide:.1f} s")
                self.canvas._recompute_total_duration()
                self._update_time_label()
                self.canvas.update()

    def export_movie(self) -> None:
        """
        FR: Rend le film sous forme de vidéo MP4 et l'enregistre dans le dossier Films de Picasa.
        EN: Renders the movie as an MP4 video and saves it to Picasa's Movies folder.
        Ref: CMakeMoviePanel::SlideshowFolder, CRenderMovie, ytDSMovieWriter
        """
        if not self.slides:
            QMessageBox.information(self, "Créateur de films", "Aucune photo à inclure dans le film.")
            return

        out_dir = Path.home() / "Pictures" / "Picasa" / "Films"
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        prefix = "FilmVisages" if self.canvas.face_movie_mode else "FilmDiaporama"
        default_file = out_dir / f"{prefix}_{ts}.mp4"

        target_file, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le film sous",
            str(default_file),
            "Vidéo MP4 (*.mp4);;Tous les fichiers (*.*)"
        )
        if not target_file:
            return

        # FR: Boîte de progression avec bouton d'annulation
        # EN: Progress dialog with cancel button
        prog_dlg = QProgressDialog("Génération du film en cours...", "Annuler", 0, 100, self)
        prog_dlg.setWindowTitle("Rendu vidéo Picasa")
        prog_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        prog_dlg.setMinimumDuration(0)
        prog_dlg.setValue(0)

        # FR: Thread de rendu en arrière-plan / EN: Background worker thread
        worker = MovieRenderWorker(
            slides=self.slides,
            output_path=target_file,
            resolution=self.canvas.resolution,
            transition_type=self.canvas.transition_type,
            overlap_ratio=self.canvas.overlap_ratio,
            fps=25,
            crop_to_fit=self.canvas.crop_to_fit,
            face_movie_mode=self.canvas.face_movie_mode,
            show_dates=self.canvas.show_dates,
            show_captions=self.canvas.show_captions
        )

        def _on_prog(cur: int, tot: int) -> None:
            """
            FR: Met à jour la barre de progression lors de l'encodage de chaque image.
            EN: Updates the progress bar as each frame is encoded.
            """
            pct = int((cur / max(1, tot)) * 100)
            prog_dlg.setValue(pct)
            prog_dlg.setLabelText(f"Rendu image {cur}/{tot} ({pct}%)")

        def _on_done(saved_path: str) -> None:
            """
            FR: Gère la fin réussie du rendu vidéo et propose d'ouvrir le dossier de sortie.
            EN: Handles successful completion of video rendering and offers to open the output folder.
            """
            prog_dlg.close()
            self.movie_created.emit(saved_path)
            reply = QMessageBox.information(
                self,
                "Film créé avec succès",
                f"Votre film haute définition a été enregistré dans :\n{saved_path}",
                QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
            )
            if reply == QMessageBox.StandardButton.Open:
                import subprocess
                try:
                    if sys.platform == "win32":
                        subprocess.Popen(f'explorer /select,"{saved_path}"')
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", "-R", str(saved_path)])
                    else:
                        subprocess.Popen(["xdg-open", str(Path(saved_path).parent)])
                except Exception:
                    pass

        def _on_fail(err_msg: str) -> None:
            """
            FR: Affiche un message d'erreur critique si le rendu vidéo échoue.
            EN: Displays a critical error message if video rendering fails.
            """
            prog_dlg.close()
            QMessageBox.critical(self, "Erreur de création du film", err_msg)

        prog_dlg.canceled.connect(worker.cancel)
        worker.progress.connect(_on_prog)
        worker.finished_success.connect(_on_done)
        worker.failed.connect(_on_fail)

        worker.start()
        prog_dlg.exec()

    def closeEvent(self, event) -> None:
        """
        FR: Arrête le minuteur de prévisualisation et le lecteur audio à la fermeture de la fenêtre.
        EN: Stops the preview timer and audio player when closing the dialog.
        """
        self.canvas.pause()
        if self.media_player:
            self.media_player.stop()
        super().closeEvent(event)
