"""
Tests for One-Up View, Image Processor, and editor navigation.

Ref: AGENTS.md §4 bis (Mode visualiseur/retouche fidèle)
"""

import os
import io
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QImage

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.ui.image_canvas import PicasaImageCanvas
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.ui.main_window import PicasaMainWindow
from picasa_py.db.database import PicasaDatabase


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    return app


@pytest.fixture
def sample_image():
    # Créer une image de test 100x100 RGB
    img = Image.new("RGB", (100, 100), color=(120, 80, 40))
    return img


def test_image_processor_filters(sample_image):
    proc = PicasaImageProcessor

    # Auto contrast
    ac = proc.auto_contrast(sample_image)
    assert ac.size == sample_image.size
    assert ac.mode == "RGB"

    # Auto color
    acol = proc.auto_color(sample_image)
    assert acol.size == sample_image.size

    # Black & White
    bw = proc.black_and_white(sample_image)
    assert bw.size == sample_image.size
    r, g, b = bw.getpixel((50, 50))
    assert r == g == b

    # Sepia
    sep = proc.sepia(sample_image)
    assert sep.size == sample_image.size

    # Warmify
    warm = proc.warmify(sample_image)
    assert warm.size == sample_image.size

    # Fill light
    fl = proc.fill_light(sample_image, amount=0.4)
    assert fl.size == sample_image.size

    # Sharpen
    sh = proc.sharpen(sample_image)
    assert sh.size == sample_image.size

    # Film grain
    fg = proc.film_grain(sample_image, intensity=10.0)
    assert fg.size == sample_image.size


def test_image_canvas_rotations(qapp, sample_image):
    canvas = PicasaImageCanvas()
    buf = io.BytesIO()
    sample_image.save(buf, format="JPEG")
    qimg = QImage()
    qimg.loadFromData(buf.getvalue(), "JPEG")
    canvas.set_pixmap_direct(QPixmap.fromImage(qimg))

    assert canvas.rotation_degrees == 0
    canvas.rotate_clockwise()
    assert canvas.rotation_degrees == 90
    canvas.rotate_clockwise()
    assert canvas.rotation_degrees == 180
    canvas.rotate_counterclockwise()
    assert canvas.rotation_degrees == 90
    canvas.set_rotation(0)
    assert canvas.rotation_degrees == 0


def test_one_up_undo_redo(qapp, sample_image):
    view = PicasaOneUpView()
    view._history = [sample_image.copy()]
    view._history_idx = 0

    # Appliquer sepia
    view._on_apply_effect("sepia", {})
    assert len(view._history) == 2
    assert view._history_idx == 1

    # Annuler (undo)
    view._on_undo()
    assert view._history_idx == 0

    # Rétablir (redo)
    view._on_redo()
    assert view._history_idx == 1


def test_main_window_one_up_switching(qapp):
    win = PicasaMainWindow()
    assert win.stack.currentIndex() == 0  # Grille

    # Simuler double-clic sur photo 0 si base présente
    if win.db and len(win.db.index) > 0:
        win._open_one_up_view(0)
        assert win.stack.currentIndex() == 1  # One-Up
        assert win.top_bar.isHidden()
        assert win.photo_tray.isHidden()

        # Retour à la bibliothèque
        win._back_to_library()
        assert win.stack.currentIndex() == 0  # Grille
        assert not win.top_bar.isHidden()
        assert not win.photo_tray.isHidden()

    win.close()
