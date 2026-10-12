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


def test_get_media_full_path_resolution():
    """
    Test que PicasaDatabase.get_media_full_path reconstitue correctement
    le chemin disque absolu parent_path + filename.
    Ref: picasa3.exe @ 0x0045C0A0
    """
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord

    db = PicasaDatabase()
    ti = ThumbIndexFile()
    # Dossier (type 1)
    rec_folder = ThumbIndexRecord(
        path=r"C:\Photos\Vacances",
        ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=-1
    )
    ti.records.append(rec_folder)

    # Photo (type 2) rattachée au dossier 0
    rec_photo = ThumbIndexRecord(
        path="DSC_0001.JPG",
        ft1=0, ft2=0, size=1024, type=2, flags=0, parent_idx=0
    )
    ti.records.append(rec_photo)

    db.thumbindex = ti

    full_path = db.get_media_full_path(1)
    assert full_path is not None
    assert full_path == os.path.join(r"C:\Photos\Vacances", "DSC_0001.JPG")

    # Index invalide ou record type 1 (dossier)
    assert db.get_media_full_path(-1) is None
    assert db.get_media_full_path(0) is None
    assert db.get_media_full_path(999) is None


def test_image_canvas_loupe_and_anchored_zoom(qapp):
    """
    Test du système de zoom ancré et du navigateur Loupe avec cadre de visée orange.
    Ref: picasa3.exe @ CLoupeNode (0x00942AE4), OneUpUI (0x0094355C)
    """
    from PySide6.QtCore import QPointF, QSize
    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)

    # Image haute résolution 4000x3000
    pix = QPixmap(4000, 3000)
    canvas.set_pixmap_direct(pix)

    # 1. État initial : mode Ajuster (Fit)
    assert canvas.fit_to_window is True
    fit_scale = canvas._get_fit_scale()
    assert fit_scale > 0
    # En mode ajuster, l'image n'est pas zoomée au-delà de la fenêtre
    assert canvas.is_zoomed_in() is False

    # 2. Zoom à 100% (1:1) : l'image dépasse l'écran (4000x3000 > 800x600)
    canvas.set_zoom(1.0)
    assert canvas.fit_to_window is False
    assert canvas.is_zoomed_in() is True

    # 3. Calcul de la géométrie de la Loupe
    canvas._update_loupe_geometry()
    assert not canvas._nav_card_rect.isEmpty()
    assert not canvas._nav_img_rect.isEmpty()
    assert not canvas._vbox_rect.isEmpty()

    # Le cadre de visée _vbox_rect doit être contenu dans la miniature _nav_img_rect
    assert canvas._nav_img_rect.contains(canvas._vbox_rect.center())
    assert canvas._vbox_rect.width() <= canvas._nav_img_rect.width()
    assert canvas._vbox_rect.height() <= canvas._nav_img_rect.height()

    # 4. Zoom ancré au curseur (400, 300)
    canvas.set_zoom_anchored(1.5, QPointF(400, 300))
    assert canvas.zoom_level == 1.5

    # 5. Recentrage via clic sur la Loupe
    nav_pt = canvas._nav_img_rect.topLeft() + QPointF(10, 10)
    canvas._center_on_nav_point(nav_pt)
    canvas._update_loupe_geometry()
    # Le cadre s'est déplacé vers le haut-gauche
    assert canvas._vbox_rect.left() >= canvas._nav_img_rect.left() - 1.0

    # 6. Réinitialisation au Fit
    canvas.reset_zoom_to_fit()
    assert canvas.fit_to_window is True
    assert canvas.pan_offset == QPointF(0, 0)
    assert canvas.is_zoomed_in() is False

