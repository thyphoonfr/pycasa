"""
FR: Lecteur vidéo intégré Picasa 3 (PicasaVideoPlayer / CMoviePlayer).
Fournit la lecture vidéo accélérée, la barre de transport multimédia,
l'instantané photo (Take Snapshot) et le découpage début/fin.

EN: Built-in Picasa 3 Video Player (PicasaVideoPlayer / CMoviePlayer).
Provides hardware-accelerated video playback, media transport bar,
snapshot capture (Take Snapshot), and start/end trimming.

Ref: picasa3.exe @ 0x0088C3EC, Dev::ID_MOVIESETSTART, Dev::ID_MOVIESETEND
Ref: export.fen @ movies (First frame, Full movie)
Ref: STRINGRES_FR.XML:640 ("Notez que les effets ne peuvent pas être appliqués aux vidéos")
"""

from __future__ import annotations
import os
import math
from pathlib import Path
from typing import Optional

os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg*=false")
os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")
os.environ.setdefault("OPENCV_LOG_LEVEL", "OFF")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QFrame, QStyle, QMessageBox
)
from PySide6.QtCore import Qt, QUrl, Signal, QTime
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from picasa_py.ui.style import PicasaStyle


def format_time_ms(ms: int) -> str:
    """
    FR: Formate une durée en millisecondes en 'MM:SS' ou 'HH:MM:SS'.
    EN: Formats a duration in milliseconds as 'MM:SS' or 'HH:MM:SS'.
    """
    total_seconds = max(0, ms // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class PicasaVideoPlayer(QWidget):
    """
    FR: Composant de lecture vidéo One-Up reproduisant l'expérience Picasa 3.
    EN: One-Up video player component reproducing the Picasa 3 experience.
    """
    back_requested = Signal()
    snapshot_captured = Signal(str)  # FR: Émis avec le chemin du fichier JPEG généré / EN: Emitted with generated JPEG file path
    photo_edited = Signal(str)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise le composant de lecture vidéo avec barre supérieure, surface vidéo et barre de transport.
        EN: Initializes the video player widget with top bar, video surface, and transport bar.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.current_video_path: Optional[str] = None
        self._is_slider_dragged = False
        self.trim_start_ms: int = 0
        self.trim_end_ms: int = 0

        self.setStyleSheet("""
            QWidget#VideoPlayerRoot {
                background-color: #0E0F12;
            }
            QWidget#TransportBar {
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
                color: #DDDDDD;
                font-size: 11px;
            }
            QSlider::groove:horizontal {
                height: 5px;
                background: #50545C;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #3879D9;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
        """)
        self.setObjectName("VideoPlayerRoot")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # FR: 1. Barre supérieure d'informations vidéo
        # EN: 1. Top video information bar
        self.top_bar = self._create_top_bar()
        main_layout.addWidget(self.top_bar)

        # FR: 2. Zone d'affichage vidéo centrale
        # EN: 2. Central video display area
        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #000000;")
        main_layout.addWidget(self.video_widget, 1)

        # FR: Moteur multimédia Qt / EN: Qt multimedia engine
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        # FR: 3. Barre de commandes de transport
        # EN: 3. Media transport control bar
        self.transport_bar = self._create_transport_bar()
        main_layout.addWidget(self.transport_bar)
        self.apply_style(self.style)

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique dynamiquement le thème de couleurs PicasaStyle au lecteur vidéo.
        EN: Dynamically applies the PicasaStyle color theme to the video player.
        """
        self.style = style
        bar_bg = style.tray_bgcolor.name()
        btn_start = style.tray_grad_start.name() if style.is_dark else style.topbar_btn_bg_start.name()
        btn_end = style.tray_grad_end.name() if style.is_dark else style.topbar_btn_bg_end.name()
        btn_border = "#4D525A" if style.is_dark else style.topbar_btn_border.name()
        txt_col = style.tray_text_color.name()
        sub_txt = "#888888" if style.is_dark else style.alayout_subtitleColor.name()
        border_col = "#141517" if style.is_dark else style.topbar_border_color.name()
        accent = style.accent_color.name()

        self.setStyleSheet(f"""
            QWidget#VideoPlayerRoot {{
                background-color: #0E0F12;
            }}
            QWidget#TransportBar, QWidget#VideoTopBar {{
                background-color: {bar_bg};
                border-top: 1px solid {border_col};
                border-bottom: 1px solid {border_col};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_start}, stop:1 {btn_end});
                color: {txt_col};
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {accent};
            }}
            QPushButton:pressed {{
                background-color: {accent};
                color: #FFFFFF;
            }}
            QLabel {{
                color: {txt_col};
                font-size: 11px;
            }}
            QSlider::groove:horizontal {{
                height: 5px;
                background: {btn_border};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
        """)
        if hasattr(self, "top_bar") and self.top_bar:
            self.top_bar.setObjectName("VideoTopBar")
            self.top_bar.setStyleSheet("")
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {txt_col};")
        if hasattr(self, "lbl_details") and self.lbl_details:
            self.lbl_details.setStyleSheet(f"color: {sub_txt}; font-size: 11px;")

    def _create_top_bar(self) -> QWidget:
        """
        FR: Construit la barre supérieure affichant le bouton retour, le titre et la taille du fichier vidéo.
        EN: Builds the top bar displaying the back button, video title, and file size.
        """
        bar = QWidget()
        bar.setObjectName("VideoTopBar")
        bar.setFixedHeight(40)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)

        self.btn_back = QPushButton("◀ Revenir à la bibliothèque")
        self.btn_back.clicked.connect(self.back_requested.emit)
        layout.addWidget(self.btn_back)

        layout.addSpacing(16)
        self.lbl_title = QLabel("")
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        self.lbl_details = QLabel("")
        layout.addWidget(self.lbl_details)

        return bar

    def _create_transport_bar(self) -> QWidget:
        """
        FR: Construit la barre inférieure de transport multimédia (lecture, arrêt, curseur, découpage, instantané, volume).
        EN: Builds the bottom media transport bar (play, stop, seek slider, trimming, snapshot, volume).
        """
        bar = QWidget()
        bar.setObjectName("TransportBar")
        bar.setFixedHeight(54)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(10)

        # FR: Bouton Lecture / Pause / EN: Play / Pause button
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.btn_play.setToolTip("Lecture / Pause (Espace)")
        self.btn_play.clicked.connect(self.toggle_play_pause)
        layout.addWidget(self.btn_play)

        # FR: Bouton Stop / EN: Stop button
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedWidth(36)
        self.btn_stop.setToolTip("Arrêter")
        self.btn_stop.clicked.connect(self.stop)
        layout.addWidget(self.btn_stop)

        # FR: Temps écoulé / EN: Elapsed time
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setFixedWidth(90)
        layout.addWidget(self.lbl_time)

        # FR: Curseur de progression temporelle (Seek) / EN: Time seek slider
        self.slider_time = QSlider(Qt.Orientation.Horizontal)
        self.slider_time.setRange(0, 1000)
        self.slider_time.setValue(0)
        self.slider_time.sliderPressed.connect(self._on_slider_pressed)
        self.slider_time.sliderReleased.connect(self._on_slider_released)
        self.slider_time.sliderMoved.connect(self._on_slider_moved)
        layout.addWidget(self.slider_time, 1)

        # FR: Marqueurs de début / fin (Trimming Picasa) / EN: Start / end trim markers
        self.btn_trim_start = QPushButton("[ Début")
        self.btn_trim_start.setToolTip("Définir le début du film (Ref: ID_MOVIESETSTART)")
        self.btn_trim_start.clicked.connect(self._set_trim_start)
        layout.addWidget(self.btn_trim_start)

        self.btn_trim_end = QPushButton("Fin ]")
        self.btn_trim_end.setToolTip("Définir la fin du film (Ref: ID_MOVIESETEND)")
        self.btn_trim_end.clicked.connect(self._set_trim_end)
        layout.addWidget(self.btn_trim_end)

        # FR: Bouton "Prendre un instantané" (Capture de frame) / EN: "Take Snapshot" button (frame capture)
        self.btn_snapshot = QPushButton("📸 Instantané")
        self.btn_snapshot.setToolTip("Enregistrer l'image courante en tant que photo JPEG dans le dossier")
        self.btn_snapshot.setStyleSheet("""
            QPushButton {
                background-color: #2F6DB5;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #1E4E85;
            }
            QPushButton:hover {
                background-color: #3879D9;
            }
        """)
        self.btn_snapshot.clicked.connect(self.take_snapshot)
        layout.addWidget(self.btn_snapshot)

        # FR: Volume / EN: Volume
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedWidth(36)
        self.btn_mute.clicked.connect(self.toggle_mute)
        layout.addWidget(self.btn_mute)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setFixedWidth(70)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self.slider_vol)

        return bar

    def load_video(self, file_path: str) -> bool:
        """
        FR: Charge un fichier vidéo, restaure les marqueurs de découpage .picasa.ini et initialise la lecture.
        EN: Loads a video file, restores .picasa.ini trim markers, and initializes playback.
        """
        if not file_path or not os.path.exists(file_path):
            return False

        self.current_video_path = file_path
        self.trim_start_ms = 0
        self.trim_end_ms = 0
        self.btn_trim_start.setText("[ Début")
        self.btn_trim_end.setText("Fin ]")

        try:
            from picasa_py.ini.parser import PicasaIniParser
            p = Path(file_path)
            ini_p = p.parent / ".picasa.ini"
            if ini_p.exists():
                doc = PicasaIniParser.parse_file(str(ini_p))
                sec = doc.get_section(p.name)
                if sec:
                    ms_start = sec.get("moviestart")
                    if ms_start and ms_start.isdigit():
                        self.trim_start_ms = int(ms_start)
                        self.btn_trim_start.setText(f"[{format_time_ms(self.trim_start_ms)}")
                    ms_end = sec.get("movieend")
                    if ms_end and ms_end.isdigit():
                        self.trim_end_ms = int(ms_end)
                        self.btn_trim_end.setText(f"{format_time_ms(self.trim_end_ms)}]")
        except Exception:
            pass

        filename = os.path.basename(file_path)
        self.lbl_title.setText(f"🎬 {filename}")

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        self.lbl_details.setText(f"{file_size_mb:.1f} Mo")

        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.audio_output.setVolume(self.slider_vol.value() / 100.0)
        if self.trim_start_ms > 0:
            self.player.setPosition(self.trim_start_ms)
        self.player.play()
        return True

    def toggle_play_pause(self) -> None:
        """
        FR: Bascule entre la lecture et la mise en pause de la vidéo.
        EN: Toggles between video playback and pause.
        """
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self) -> None:
        """
        FR: Arrête la lecture vidéo et libère la source multimédia active.
        EN: Stops video playback and releases the active media source.
        """
        self.player.stop()
        self.player.setSource(QUrl())
        self.btn_play.setText("▶")

    def toggle_mute(self) -> None:
        """
        FR: Active ou désactive la sourdine audio et met à jour l'icône du bouton.
        EN: Toggles audio mute state and updates the button icon.
        """
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        self.btn_mute.setText("🔇" if not is_muted else "🔊")

    def _on_volume_changed(self, val: int) -> None:
        """
        FR: Ajuste le volume sonore de la sortie audio selon la position du curseur.
        EN: Adjusts the audio output volume according to the slider position.
        """
        self.audio_output.setVolume(val / 100.0)
        if val == 0:
            self.btn_mute.setText("🔇")
        else:
            self.btn_mute.setText("🔊")

    def _on_position_changed(self, pos_ms: int) -> None:
        """
        FR: Met à jour le curseur temporel et l'affichage du temps écoulé, en respectant la fin de découpage.
        EN: Updates the seek slider and elapsed time label while respecting the end trim point.
        """
        if self.trim_end_ms > 0 and pos_ms >= self.trim_end_ms:
            self.player.pause()
            self.player.setPosition(self.trim_start_ms)
            return
        if not self._is_slider_dragged:
            dur_ms = self.player.duration()
            if dur_ms > 0:
                self.slider_time.setValue(int(pos_ms * 1000 / dur_ms))
            self.lbl_time.setText(f"{format_time_ms(pos_ms)} / {format_time_ms(dur_ms)}")

    def _on_duration_changed(self, dur_ms: int) -> None:
        """
        FR: Met à jour l'étiquette de durée totale lorsque la durée du média est connue.
        EN: Updates the total duration label when the media duration becomes available.
        """
        pos_ms = self.player.position()
        self.lbl_time.setText(f"{format_time_ms(pos_ms)} / {format_time_ms(dur_ms)}")

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """
        FR: Met à jour l'icône du bouton lecture/pause selon l'état du lecteur multimédia.
        EN: Updates the play/pause button icon according to the media player state.
        """
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def _on_slider_pressed(self) -> None:
        """
        FR: Marque le début du glissement manuel du curseur temporel.
        EN: Marks the start of manual dragging on the time seek slider.
        """
        self._is_slider_dragged = True

    def _on_slider_released(self) -> None:
        """
        FR: Applique la nouvelle position de lecture lorsque l'utilisateur relâche le curseur temporel.
        EN: Applies the new playback position when the user releases the time seek slider.
        """
        self._is_slider_dragged = False
        dur_ms = self.player.duration()
        if dur_ms > 0:
            target_ms = int(self.slider_time.value() * dur_ms / 1000)
            self.player.setPosition(target_ms)

    def _on_slider_moved(self, val: int) -> None:
        """
        FR: Met à jour l'aperçu du temps pendant le déplacement du curseur de recherche.
        EN: Updates the time preview while the seek slider is being moved.
        """
        dur_ms = self.player.duration()
        if dur_ms > 0:
            curr_ms = int(val * dur_ms / 1000)
            self.lbl_time.setText(f"{format_time_ms(curr_ms)} / {format_time_ms(dur_ms)}")

    def _persist_trim_key(self, key: str, value: str) -> None:
        """
        FR: Enregistre la clé de découpage vidéo (`moviestart` ou `movieend`) dans `.picasa.ini`.
        EN: Persists the video trim key (`moviestart` or `movieend`) to `.picasa.ini`.
        """
        if not self.current_video_path:
            return
        try:
            from picasa_py.ini.parser import PicasaIniParser
            from picasa_py.ini.writer import PicasaIniWriter
            from picasa_py.ini.model import IniDocument
            p = Path(self.current_video_path)
            ini_p = p.parent / ".picasa.ini"
            doc = PicasaIniParser.parse_file(str(ini_p)) if ini_p.exists() else IniDocument()
            sec = doc.get_or_create_section(p.name)
            sec.set(key, value)
            PicasaIniWriter.write_file(str(ini_p), doc)
            self.photo_edited.emit(self.current_video_path)
        except Exception:
            pass

    def _set_trim_start(self, pos_ms: Optional[int] = None) -> None:
        """
        FR: Définit le point d'entrée (`moviestart`) de la vidéo à la position actuelle ou fournie.
        EN: Sets the video trim start point (`moviestart`) to the current or provided position.
        """
        self.trim_start_ms = pos_ms if isinstance(pos_ms, int) and not isinstance(pos_ms, bool) else self.player.position()
        self.btn_trim_start.setText(f"[{format_time_ms(self.trim_start_ms)}")
        self._persist_trim_key("moviestart", str(self.trim_start_ms))

    def _set_trim_end(self, pos_ms: Optional[int] = None) -> None:
        """
        FR: Définit le point de sortie (`movieend`) de la vidéo à la position actuelle ou fournie.
        EN: Sets the video trim end point (`movieend`) to the current or provided position.
        """
        self.trim_end_ms = pos_ms if isinstance(pos_ms, int) and not isinstance(pos_ms, bool) else self.player.position()
        self.btn_trim_end.setText(f"{format_time_ms(self.trim_end_ms)}]")
        self._persist_trim_key("movieend", str(self.trim_end_ms))

    def take_snapshot(self) -> Optional[str]:
        """
        FR: Capture l'image vidéo à la position actuelle et l'enregistre en JPG.
        EN: Captures the video frame at the current position and saves it as a JPEG file.
        Ref: picasa3.exe @ Take Snapshot
        """
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            return None

        pos_ms = self.player.position()
        p = Path(self.current_video_path)
        folder = p.parent
        counter = 1
        snapshot_name = f"{p.stem}_snapshot_{counter:02d}.jpg"
        while (folder / snapshot_name).exists():
            counter += 1
            snapshot_name = f"{p.stem}_snapshot_{counter:02d}.jpg"
        out_path = str(folder / snapshot_name)

        saved = False
        try:
            import cv2
            from picasa_py.scanner.scanner import _suppress_c_stderr
            with _suppress_c_stderr():
                cap = cv2.VideoCapture(self.current_video_path)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_POS_MSEC, pos_ms)
                    ret, frame = cap.read()
                    if not ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    cap.release()
                else:
                    ret, frame = False, None

            if ret and frame is not None:
                from PIL import Image
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                img.save(out_path, format="JPEG", quality=95)
                saved = True
        except Exception:
            pass

        if saved:
            self.snapshot_captured.emit(out_path)
            self.photo_edited.emit(out_path)
            QMessageBox.information(
                self,
                "Instantané capturé",
                f"L'image vidéo a été enregistrée avec succès sous :\n{snapshot_name}"
            )
            return out_path
        else:
            QMessageBox.warning(self, "Erreur", "Impossible de capturer l'instantané de cette vidéo.")
            return None

    def keyPressEvent(self, event) -> None:
        """
        FR: Gère les raccourcis clavier du lecteur vidéo (Espace, flèches ±5s, Échap/Entrée).
        EN: Handles video player keyboard shortcuts (Space, arrows ±5s, Escape/Enter).
        """
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play_pause()
        elif event.key() == Qt.Key.Key_Left:
            self.player.setPosition(max(0, self.player.position() - 5000))
        elif event.key() == Qt.Key.Key_Right:
            self.player.setPosition(min(self.player.duration(), self.player.position() + 5000))
        elif event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.stop()
            self.back_requested.emit()
        else:
            super().keyPressEvent(event)
