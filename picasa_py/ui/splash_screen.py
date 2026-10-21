"""
FR: Composant d'écran de démarrage pour PyCasa (reproduction fidèle de SplashThread).
Affiche l'image officielle 640x235 `runtime/splashbk.jpg` avec le logo Picasa 3,
le titre, la version et l'état de chargement avant l'ouverture de la fenêtre principale.

EN: Splash Screen Component for PyCasa (faithful reproduction of SplashThread).
Displays the authentic 640x235 `runtime/splashbk.jpg` background with the Picasa 3
aperture logo, application title, version information, and loading status before
opening the main application window.

Ref: picasa3.exe @ 0x0087FC90 (SplashThread, runtime\\splashbk.jpg, nosplash)
Ref: runtime/splashbk.jpg (640x235 JPEG)
Ref: AGENTS.md §4 bis (Fidélité de l'interface)
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QSplashScreen, QApplication, QWidget
from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen, QPaintEvent
)

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.version import APP_NAME, APP_VERSION

RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "resources"
SPLASH_BG_PATH = RESOURCES_DIR / "splashbk.jpg"


class PicasaSplashScreen(QSplashScreen):
    """
    FR: Écran de démarrage authentique de Picasa 3 (640x235 px).
    Utilise l'image officielle `runtime/splashbk.jpg` extraite du binaire original,
    avec le logo Picasa 3, le titre de l'application, la version et l'état de chargement.
    EN: Authentic Picasa 3 splash screen (640x235 px).
    Uses the official `runtime/splashbk.jpg` extracted from the binary, with the
    Picasa 3 logo, application title, version, and loading status.

    Ref: picasa3.exe @ 0x0087FC90 (SplashThread, runtime\\splashbk.jpg)
    """
    SPLASH_WIDTH = 640
    SPLASH_HEIGHT = 235

    def __init__(self, parent: Optional[QWidget] = None):
        """
        FR: Initialise l'écran de démarrage 640x235 px et le centre à l'écran.
        EN: Initializes the 640x235 px splash screen and centers it on screen.
        """
        self.status_text: str = f"Chargement de {APP_NAME} {APP_VERSION}..."
        self.app_title: str = APP_NAME
        self.app_version: str = f"Version {APP_VERSION}"
        self.app_copyright: str = "© Google Inc."

        base_pixmap = self._build_composite_pixmap()
        super().__init__(
            base_pixmap,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setFixedSize(self.SPLASH_WIDTH, self.SPLASH_HEIGHT)
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        """
        FR: Centre l'écran de démarrage sur l'écran principal disponible.
        EN: Centers the splash screen on the primary available screen.
        """
        app = QApplication.instance()
        if app is not None:
            screen = app.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                x = geo.x() + (geo.width() - self.SPLASH_WIDTH) // 2
                y = geo.y() + (geo.height() - self.SPLASH_HEIGHT) // 2
                self.move(x, y)

    def _build_composite_pixmap(self) -> QPixmap:
        """
        FR: Construit l'image 640x235 combinant `splashbk.jpg`, le logo Picasa et le titre.
        EN: Builds the 640x235 composite pixmap combining `splashbk.jpg`, the Picasa logo, and title.
        """
        canvas = QPixmap(self.SPLASH_WIDTH, self.SPLASH_HEIGHT)
        canvas.fill(QColor("#20242B"))

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # FR: 1. Image d'arrière-plan officielle runtime/splashbk.jpg (640x235)
        # EN: 1. Official background image runtime/splashbk.jpg (640x235)
        bg_loaded = False
        if SPLASH_BG_PATH.exists():
            bg_pix = QPixmap(str(SPLASH_BG_PATH))
            if not bg_pix.isNull():
                scaled_bg = bg_pix.scaled(
                    self.SPLASH_WIDTH,
                    self.SPLASH_HEIGHT,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(0, 0, scaled_bg)
                bg_loaded = True

        if not bg_loaded:
            grad = QLinearGradient(0, 0, self.SPLASH_WIDTH, self.SPLASH_HEIGHT)
            grad.setColorAt(0.0, QColor("#2D333D"))
            grad.setColorAt(1.0, QColor("#181B20"))
            painter.fillRect(0, 0, self.SPLASH_WIDTH, self.SPLASH_HEIGHT, grad)

        # FR: 2. Icône officielle Picasa 3 (diaphragme coloré ID 105)
        # EN: 2. Official Picasa 3 icon (colored aperture ID 105)
        try:
            res_mgr = PicasaResourceManager.get()
            icon = res_mgr.get_icon(105)
            icon_pix = icon.pixmap(64, 64)
            if not icon_pix.isNull():
                painter.drawPixmap(36, 56, icon_pix)
        except Exception:
            pass

        # FR: 3. Titre principal "Picasa 3" avec ombre portée douce
        # EN: 3. Main title "Picasa 3" with soft drop shadow
        title_font = QFont("Segoe UI", 30, QFont.Weight.Bold)
        painter.setFont(title_font)

        # FR: Ombre du titre / EN: Title shadow
        painter.setPen(QColor(0, 0, 0, 90))
        painter.drawText(QRect(115, 51, 480, 52), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.app_title)

        # FR: Texte principal du titre / EN: Main title text
        painter.setPen(QColor("#2B3038"))
        painter.drawText(QRect(114, 50, 480, 52), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.app_title)

        # FR: 4. Sous-titre et numéro de version
        # EN: 4. Subtitle and version number
        sub_font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        painter.setFont(sub_font)
        painter.setPen(QColor("#545B66"))
        painter.drawText(
            QRect(116, 102, 480, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.app_version,
        )

        # FR: 5. Bandeau inférieur de statut
        # EN: 5. Bottom status banner
        footer_rect = QRect(0, self.SPLASH_HEIGHT - 34, self.SPLASH_WIDTH, 34)
        painter.fillRect(footer_rect, QColor(28, 31, 36, 215))

        # FR: Ligne d'accentuation colorée (couleurs du logo Picasa)
        # EN: Colored accent stripe (Picasa logo colors)
        stripe_w = self.SPLASH_WIDTH // 5
        picasa_colors = [
            QColor("#E53935"),  # Rouge / Red
            QColor("#FB8C00"),  # Orange
            QColor("#FDD835"),  # Jaune / Yellow
            QColor("#43A047"),  # Vert / Green
            QColor("#1E88E5"),  # Bleu / Blue
        ]
        for idx, col in enumerate(picasa_colors):
            x0 = idx * stripe_w
            w = stripe_w if idx < 4 else (self.SPLASH_WIDTH - x0)
            painter.fillRect(QRect(x0, self.SPLASH_HEIGHT - 36, w, 2), col)

        # FR: Bordure extérieure fine / EN: Thin outer border
        painter.setPen(QPen(QColor("#3A3F47"), 1))
        painter.drawRect(0, 0, self.SPLASH_WIDTH - 1, self.SPLASH_HEIGHT - 1)

        painter.end()
        return canvas

    def set_status(self, message: str) -> None:
        """
        FR: Met à jour le texte d'état affiché en bas de l'écran de démarrage et rafraîchit l'affichage.
        EN: Updates the status text displayed at the bottom of the splash screen and refreshes the display.
        """
        self.status_text = message
        self.showMessage(
            message,
            int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft),
            QColor("#E8EAED"),
        )
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def drawContents(self, painter: Optional[QPainter]) -> None:
        """
        FR: Dessine le message d'état et le copyright dans le bandeau inférieur.
        EN: Draws the status message and copyright in the bottom banner.
        """
        if painter is None:
            return
        painter.save()
        status_font = QFont("Segoe UI", 9, QFont.Weight.Normal)
        painter.setFont(status_font)
        painter.setPen(QColor("#E8EAED"))
        painter.drawText(
            QRect(16, self.SPLASH_HEIGHT - 32, 440, 30),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.status_text,
        )

        painter.setPen(QColor("#9AA0A6"))
        painter.drawText(
            QRect(460, self.SPLASH_HEIGHT - 32, 164, 30),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self.app_copyright,
        )
        painter.restore()
