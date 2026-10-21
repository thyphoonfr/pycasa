"""FR: Configuration Pytest et fixtures partagées pour les tests PyCasa.
EN: Pytest configuration and shared fixtures for PyCasa tests.
"""

import gc
import pytest
import shiboken6
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView


_SESSION_KEEP_ALIVE = []


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """FR: Fournit une instance partagée de QApplication en mode offscreen pour toute la session Pytest.
    EN: Provides a shared offscreen QApplication instance for the entire Pytest session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    _SESSION_KEEP_ALIVE.append(app)
    yield app
    for widget in list(app.topLevelWidgets()):
        if shiboken6.isValid(widget):
            _SESSION_KEEP_ALIVE.append(widget)
            widget.hide()
    app.processEvents()
