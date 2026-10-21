"""FR: Tests pour l'outil de création de montages photo (CCollageUI).
EN: Tests for Picture Collage Maker (CCollageUI).
Ref: picasa3.exe @ ID_COLLAGEMAKER (0x0088C3EC), CCollageUI, CollagePanel
"""

import os
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPaintEvent, QRegion, QColor, QImage
from PySide6.QtWidgets import QApplication

from picasa_py.ui.collage import (
    PicasaCollageCanvas, PicasaCollageDialog, CollageTheme, CollageBorder
)
from picasa_py.ui.main_window import PicasaMainWindow


def test_collage_canvas_themes_and_layout(qapp, tmp_path):
    """FR: Vérifie le positionnement des photos et l'application des différents thèmes de montage.
    EN: Verifies photo positioning and application of the various collage themes.
    """
    canvas = PicasaCollageCanvas()
    canvas.resize(800, 600)

    # 4 photos de test
    paths = []
    for i in range(4):
        p = tmp_path / f"img_col_{i}.jpg"
        Image.new("RGB", (600, 400), color=(i * 50, 120, 200)).save(p)
        paths.append(str(p))

    canvas.set_photos(paths)
    assert len(canvas.items) == 4

    # 1. Thème Pile d'images (Picture Pile / Pêle-mêle)
    canvas.set_theme(CollageTheme.PILE)
    assert canvas.theme == CollageTheme.PILE
    for it in canvas.items:
        assert 0.05 <= it.x <= 0.95
        assert 0.05 <= it.y <= 0.95

    # 2. Thème Grille
    canvas.set_theme(CollageTheme.GRID)
    assert canvas.theme == CollageTheme.GRID
    assert canvas.items[0].angle == 0.0

    # 3. Thème Mosaïque et Cadre
    canvas.set_theme(CollageTheme.FRAME)
    assert canvas.theme == CollageTheme.FRAME
    assert canvas.items[0].scale > canvas.items[1].scale  # Photo centrale mise en avant

    # 4. Thème Exposition multiple
    canvas.set_theme(CollageTheme.MULTI_EXP)
    assert canvas.theme == CollageTheme.MULTI_EXP
    assert canvas.items[0].x == 0.5 and canvas.items[0].y == 0.5


def test_collage_canvas_borders_and_colors(qapp, tmp_path):
    """FR: Vérifie les modes de bordure et la couleur de fond.
    EN: Verifies border modes and background color.
    """
    canvas = PicasaCollageCanvas()
    p = tmp_path / "single.jpg"
    Image.new("RGB", (400, 400), color=(100, 100, 100)).save(p)
    canvas.set_photos([str(p)])

    canvas.set_border_mode(CollageBorder.POLAROID)
    assert canvas.border_mode == CollageBorder.POLAROID
    assert canvas.items[0].border == CollageBorder.POLAROID

    canvas.set_background_color(QColor(0, 0, 0))
    assert canvas.bg_color == QColor(0, 0, 0)


def test_collage_canvas_interactive_drag_and_paint(qapp, tmp_path):
    """FR: Vérifie l'interaction souris de déplacement des photos et le rendu graphique.
    EN: Verifies mouse drag interaction for moving photos and graphical rendering.
    """
    canvas = PicasaCollageCanvas()
    canvas.resize(600, 600)
    p = tmp_path / "drag_test.jpg"
    Image.new("RGB", (300, 300), color=(150, 80, 40)).save(p)
    canvas.set_photos([str(p)])

    # Rendu graphique
    canvas.paintEvent(QPaintEvent(QRegion(canvas.rect())))

    # Déplacement interactif
    item = canvas.items[0]
    initial_x = item.x
    item._screen_rect = QRectF(250, 250, 100, 100)

    class FakeMouseEvent:
        """FR: Simule un événement souris Qt avec position et bouton.
        EN: Simulates a Qt mouse event with position and button.
        """
        def __init__(self, pos, btn=Qt.MouseButton.LeftButton):
            """FR: Initialise la position et le bouton simulés.
            EN: Initializes the simulated position and button.
            """
            self._pos = pos
            self._btn = btn
        def button(self):
            """FR: Retourne le bouton de souris simulé.
            EN: Returns the simulated mouse button.
            """
            return self._btn
        def position(self):
            """FR: Retourne la position de souris simulée.
            EN: Returns the simulated mouse position.
            """
            return self._pos

    canvas.mousePressEvent(FakeMouseEvent(QPointF(260, 260)))
    assert canvas._dragged_item == item

    canvas.mouseMoveEvent(FakeMouseEvent(QPointF(310, 260)))
    canvas.mouseReleaseEvent(FakeMouseEvent(QPointF(310, 260)))
    assert canvas._dragged_item is None


def test_collage_render_hd(qapp, tmp_path):
    """FR: Vérifie la génération d'un montage Ultra HD exportable en JPEG.
    EN: Verifies generation of an Ultra HD collage exportable to JPEG.
    """
    canvas = PicasaCollageCanvas()
    p = tmp_path / "hd_src.jpg"
    Image.new("RGB", (1200, 800), color=(100, 180, 90)).save(p)
    canvas.set_photos([str(p)])

    hd_img = canvas.render_hd(width=1600)
    assert isinstance(hd_img, QImage)
    assert hd_img.width() == 1600
    assert hd_img.height() == int(1600 / canvas.aspect_ratio)

    out_file = tmp_path / "out_montage.jpg"
    hd_img.save(str(out_file), "JPEG")
    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_collage_dialog_and_main_window_action(qapp):
    """FR: Vérifie l'instanciation de PicasaCollageDialog et l'action action_collage.
    EN: Verifies PicasaCollageDialog instantiation and the action_collage method.
    """
    dlg = PicasaCollageDialog([])
    assert dlg.canvas is not None
    assert dlg.cb_theme.count() == 6

    assert hasattr(PicasaMainWindow, "action_collage")
    assert callable(PicasaMainWindow.action_collage)
