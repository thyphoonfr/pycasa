"""
FR : Lanceur de l'application graphique PyCasa.
EN : PyCasa UI Application Launcher.

Ref: picasa3.exe @ 0x0070494B (Picasa Startup and main message loop)
Ref: picasa3.exe @ 0x0087FC90 (SplashThread, runtime\\splashbk.jpg, /nosplash)
"""

import argparse
import os
import sys
from typing import Optional

os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg*=false")
os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")
os.environ.setdefault("OPENCV_LOG_LEVEL", "OFF")

from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QLoggingCategory
from PySide6.QtGui import QImageReader
from picasa_py.db.database import PicasaDatabase
from picasa_py.ui.main_window import PicasaMainWindow
from picasa_py.ui.splash_screen import PicasaSplashScreen
from picasa_py.version import APP_NAME, APP_VERSION, get_window_title

# Désactiver les limites de décompression pour permettre l'ouverture des photos panoramiques / ultra haute résolution
Image.MAX_IMAGE_PIXELS = None


def run_picasa(
    db_path: Optional[str] = None,
    create_new: bool = False,
    show_splash: bool = True,
) -> int:
    """
    FR : Lance l'application graphique PyCasa avec son écran de démarrage authentique.
    EN : Launches the PyCasa GUI application with its authentic splash screen.
    Ref: picasa3.exe @ 0x0070494B, 0x0087FC90 (SplashThread)
    """
    # Désactiver la limite d'allocation de 256 Mo de Qt pour autoriser les images volumineuses
    QImageReader.setAllocationLimit(0)
    QLoggingCategory.setFilterRules("qt.multimedia.ffmpeg*=false")

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName(get_window_title())
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Google")

    splash: Optional[PicasaSplashScreen] = None
    if show_splash:
        splash = PicasaSplashScreen()
        splash.show()
        splash.set_status(f"Initialisation de {APP_NAME} {APP_VERSION}...")

    if create_new and db_path:
        if splash is not None:
            splash.set_status("Création de la nouvelle base de données...")
        db = PicasaDatabase.create_new(db_path)
        db_path = str(db.db3_dir)

    if splash is not None:
        splash.set_status("Chargement de la photothèque et des préférences...")

    window = PicasaMainWindow(db_path=db_path)

    if splash is not None:
        splash.set_status(f"Ouverture de l'interface {APP_NAME} {APP_VERSION}...")
        window.show()
        QTimer.singleShot(350, lambda: splash.finish(window))
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyCasa — Picasa 3 Python Edition")
    parser.add_argument(
        "--dbpath",
        "-dbpath",
        dest="db_path",
        default=None,
        help="Chemin d'une base de données Picasa (dossier db3 ou dossier parent)",
    )
    parser.add_argument(
        "--new-db",
        dest="new_db",
        default=None,
        help="Crée et initialise une nouvelle base de données Picasa dans ce dossier au démarrage",
    )
    parser.add_argument(
        "--nosplash",
        "-nosplash",
        action="store_true",
        dest="no_splash",
        help="Désactive l'écran de démarrage (SplashScreen)",
    )
    args, unknown = parser.parse_known_args()
    no_splash = args.no_splash or ("/nosplash" in unknown)
    if args.new_db:
        sys.exit(run_picasa(db_path=args.new_db, create_new=True, show_splash=not no_splash))
    sys.exit(run_picasa(db_path=args.db_path, show_splash=not no_splash))
