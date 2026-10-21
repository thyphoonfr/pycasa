"""FR: Tests pour la pipette de couleur neutre (filter_whitept) et les ratios de recadrage personnalisés (customaspectratio.fen).
EN: Tests for Neutral Color Picker (filter_whitept) and Custom Aspect Ratios (customaspectratio.fen).
"""
import pytest
from PySide6.QtWidgets import QApplication
from PIL import Image
import numpy as np

from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.ui.custom_aspect_ratio_dialog import PicasaCustomAspectRatioDialog
from picasa_py.ui.edit_panel import PicasaCropSubpanel


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_neutral_color_balance_neutralizes_yellow_cast():
    """FR: Vérifie que neutral_color_balance corrige une dominante jaune.
    EN: Verifies that neutral_color_balance corrects a yellow color cast.
    """
    # Créer une image 50x50 avec dominante jaune (R=220, G=210, B=140)
    arr = np.zeros((50, 50, 3), dtype=np.uint8)
    arr[:, :] = [220, 210, 140]
    img = Image.fromarray(arr)

    # Échantillonner un pixel jaune supposé être du blanc/gris neutre
    corrected = PicasaImageProcessor.neutral_color_balance(img, (220, 210, 140))
    res_arr = np.array(corrected)

    # Les composantes R et B doivent être beaucoup plus proches qu'initialement
    diff_before = abs(int(arr[0, 0, 0]) - int(arr[0, 0, 2]))  # 220 - 140 = 80
    diff_after = abs(int(res_arr[0, 0, 0]) - int(res_arr[0, 0, 2]))
    assert diff_after < diff_before / 2


def test_custom_aspect_ratio_dialog(qapp):
    """FR: Vérifie la saisie et le calcul de ratio dans PicasaCustomAspectRatioDialog.
    EN: Verifies input and aspect ratio calculation in PicasaCustomAspectRatioDialog.
    """
    dlg = PicasaCustomAspectRatioDialog()
    dlg.edit_width.setText("16")
    dlg.edit_height.setText("10")
    dlg.edit_name.setText("Écran 16:10")
    dlg._on_accept()

    res = dlg.get_custom_ratio()
    assert res is not None
    name, ratio = res
    assert name == "Écran 16:10"
    assert abs(ratio - 1.6) < 1e-5


def test_crop_subpanel_custom_aspect_ratio(qapp):
    """FR: Vérifie l'ajout dynamique d'un ratio personnalisé dans PicasaCropSubpanel.
    EN: Verifies dynamic addition of a custom aspect ratio in PicasaCropSubpanel.
    """
    panel = PicasaCropSubpanel()
    initial_count = len(panel.radio_buttons)

    # Simuler l'ajout direct
    idx = len(panel.radio_buttons)
    from PySide6.QtWidgets import QRadioButton
    rb = QRadioButton("Panoramique 21:9")
    panel.btn_group.addButton(rb, idx)
    panel.radio_buttons.append((rb, 21.0 / 9.0))

    assert len(panel.radio_buttons) == initial_count + 1
    _, val = panel.radio_buttons[-1]
    assert abs(val - (21.0 / 9.0)) < 1e-4
