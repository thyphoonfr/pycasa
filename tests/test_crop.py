"""FR: Tests pour l'outil de recadrage interactif avec règle des tiers et ratios prédéfinis (CSmartCrop / crop=rect64).
EN: Tests for Interactive Crop Tool with Rule of Thirds and Ratio Presets (CSmartCrop / crop=rect64).
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QImage

from picasa_py.ui.image_canvas import PicasaImageCanvas
from picasa_py.ui.edit_panel import PicasaCropSubpanel, PicasaEditPanel
from picasa_py.faces.facerect import decode_rect64_string, encode_rect64_string


def test_crop_subpanel_ratios(qapp):
    """FR: Vérifie les boutons radio de ratios prédéfinis dans PicasaCropSubpanel.
    EN: Verifies preset aspect ratio radio buttons in PicasaCropSubpanel.
    """
    panel = PicasaCropSubpanel()
    assert len(panel.radio_buttons) >= 6

    received_ratios = []
    panel.ratio_changed.connect(lambda r: received_ratios.append(r))

    # Clic sur le ratio Carré (index 1 -> 1.0)
    panel.btn_group.button(1).click()
    assert len(received_ratios) == 1
    assert received_ratios[0] == 1.0

    # Clic sur 16:9 (index 3 -> 16/9)
    panel.btn_group.button(3).click()
    assert len(received_ratios) == 2
    assert abs(received_ratios[1] - (16.0 / 9.0)) < 1e-4


def test_image_canvas_crop_interaction(qapp):
    """FR: Vérifie le cycle complet d'interaction de recadrage sur PicasaImageCanvas et l'encodage rect64.
    EN: Verifies the full crop interaction cycle on PicasaImageCanvas and rect64 encoding.
    """
    canvas = PicasaImageCanvas()

    # Créer une fausse pixmap 800x600
    img = QImage(800, 600, QImage.Format.Format_RGB888)
    img.fill(Qt.GlobalColor.blue)
    canvas.set_pixmap_direct(QPixmap.fromImage(img))

    # 1. Démarrer le recadrage
    canvas.start_crop(QRectF(0.2, 0.2, 0.6, 0.6))
    assert canvas.is_cropping is True
    assert canvas.crop_rect_norm == QRectF(0.2, 0.2, 0.6, 0.6)

    # 2. Fixer un ratio 1:1 (carré)
    canvas.set_crop_aspect_ratio(1.0)
    assert canvas.crop_target_ratio == 1.0
    r = canvas.crop_rect_norm
    # (w * 800) / (h * 600) doit valoir 1.0 -> w / h = 600 / 800 = 0.75
    ratio_calc = (r.width() * 800) / (r.height() * 600)
    assert abs(ratio_calc - 1.0) < 0.05

    # 3. Valider le recadrage
    crop_str = canvas.apply_crop()
    assert canvas.is_cropping is False
    assert crop_str.startswith("rect64(") and crop_str.endswith(")")

    # 4. Décoder la chaîne hexadécimale produite
    left, top, right, bottom = decode_rect64_string(crop_str)
    assert 0.0 <= left < right <= 1.0
    assert 0.0 <= top < bottom <= 1.0


def test_edit_panel_switching_to_crop(qapp):
    """FR: Vérifie le basculement du panneau d'édition vers le sous-panneau de recadrage et son annulation.
    EN: Verifies switching the edit panel to the crop subpanel and cancelling it.
    """
    panel = PicasaEditPanel()
    assert panel.stack.currentIndex() == 0  # Onglets normaux

    crop_started = []
    panel.crop_requested.connect(lambda: crop_started.append(True))

    panel._open_crop_subpanel()
    assert panel.stack.currentIndex() == 1  # Sous-panneau de recadrage
    assert len(crop_started) == 1

    panel._on_crop_cancel()
    assert panel.stack.currentIndex() == 0  # Retour aux onglets


def test_image_canvas_crop_paint_event(qapp):
    """FR: Vérifie que paintEvent s'exécute sans erreur lors du mode recadrage avec toutes les poignées.
    EN: Verifies that paintEvent executes without error during crop mode with all handles.
    """
    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)

    img = QImage(800, 600, QImage.Format.Format_RGB888)
    img.fill(Qt.GlobalColor.blue)
    canvas.set_pixmap_direct(QPixmap.fromImage(img))

    # Démarrer le recadrage
    canvas.start_crop(QRectF(0.1, 0.1, 0.8, 0.8))
    assert canvas.is_cropping is True

    # Rendu graphique complet (déclenche paintEvent et _draw_crop_overlay)
    target_pix = QPixmap(800, 600)
    canvas.render(target_pix)
    assert not target_pix.isNull()
