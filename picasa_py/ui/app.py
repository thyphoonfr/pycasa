"""
PyCasa UI Application Launcher.

Ref: picasa3.exe @ 0x0070494B (Picasa Startup and main message loop)
"""

import sys
from typing import Optional
from PySide6.QtWidgets import QApplication
from picasa_py.ui.main_window import PicasaMainWindow


def run_picasa(db_path: Optional[str] = None) -> int:
    """
    Lance l'application graphique Picasa 3.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("Picasa 3")
    app.setOrganizationName("Google")

    window = PicasaMainWindow(db_path=db_path)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_picasa())
