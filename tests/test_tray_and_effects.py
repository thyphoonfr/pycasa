"""
FR: Tests unitaires et d'intégration pour le Photo Tray Picasa, le moteur d'effets, l'histogramme et la fiche appareil photo.
EN: Unit & Integration Tests for Picasa Photo Tray, Effects Engine, Histogram & Camera Info.

Ref: picasa3.exe @ filterdesc.xml, Picture Tray, IMAGEPROPERTIES.XML
Ref: AGENTS.md §7 (Stratégie de validation)
"""

import os
import sys
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from picasa_py.ui.photo_tray import PicasaPhotoTray, PicasaTrayThumbnailStrip
from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.ui.histogram_widget import PicasaHistogramWidget, PicasaCameraInfoCard
from picasa_py.ui.edit_panel import PicasaEditPanel
from picasa_py.ui.thumbnail_view import ThumbnailItem


@pytest.fixture(scope="session")
def qapp():
    """
    FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provide a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_photo_tray_selection_and_strip(qapp):
    """
    FR: Vérifie la sélection d'éléments et l'affichage de la bande de miniatures dans le Photo Tray.
    EN: Verify item selection and thumbnail strip display in the Photo Tray.
    """
    tray = PicasaPhotoTray()

    assert tray.lbl_selection.text() == "Aucune photo sélectionnée"
    assert tray.btn_add_to_album.isEnabled() is False
    assert tray.btn_export.isEnabled() is False

    # Création de faux items
    item1 = ThumbnailItem(index=0, path="C:/photos/photo1.jpg", filename="photo1.jpg", folder="Vacances", folder_path="C:/photos")
    item2 = ThumbnailItem(index=1, path="C:/photos/photo2.jpg", filename="photo2.jpg", folder="Vacances", folder_path="C:/photos")

    # Sélection de 2 éléments
    tray.set_selected_items([item1, item2])
    assert "2 photos sélectionnées" in tray.lbl_selection.text()
    assert tray.btn_add_to_album.isEnabled() is True
    assert tray.btn_export.isEnabled() is True
    assert len(tray.get_effective_items()) == 2
    assert len(tray.thumb_strip.items) == 2


def test_photo_tray_hold_and_clear(qapp):
    """
    FR: Vérifie les actions Conserver (Hold) et Effacer (Clear) du Photo Tray.
    EN: Verify the Hold and Clear actions of the Photo Tray.
    """
    tray = PicasaPhotoTray()
    item1 = ThumbnailItem(index=0, path="C:/photos/photo1.jpg", filename="photo1.jpg", folder="Vacances", folder_path="C:/photos")
    item2 = ThumbnailItem(index=1, path="C:/photos/photo2.jpg", filename="photo2.jpg", folder="Vacances", folder_path="C:/photos")

    tray.set_selected_items([item1])
    assert len(tray.get_effective_items()) == 1

    # Activer Hold
    tray._toggle_hold()
    assert tray.is_held is True
    assert tray.btn_hold.isChecked() is True

    # Nouvelle sélection (autre dossier par exemple)
    tray.set_selected_items([item2])
    # Avec Hold actif, item1 et item2 doivent être conservés
    effective = tray.get_effective_items()
    assert len(effective) == 2
    assert item1 in effective and item2 in effective

    # Clear
    tray._on_clear_clicked()
    assert tray.is_held is False
    assert len(tray.get_effective_items()) == 0
    assert tray.lbl_selection.text() == "Aucune photo sélectionnée"
    assert tray.btn_add_to_album.isEnabled() is False


def test_histogram_widget(qapp):
    """
    FR: Vérifie le calcul des bins RGB/Luminance et les modes de canaux de PicasaHistogramWidget.
    EN: Verify RGB/Luminance bin calculation and channel modes of PicasaHistogramWidget.
    """
    hw = PicasaHistogramWidget(height=70)
    assert hw._has_data is False

    # Image de test
    img = Image.new("RGB", (80, 80), color=(180, 100, 60))
    hw.set_image(img)
    assert hw._has_data is True
    assert len(hw._r_bins) == 256
    assert len(hw._g_bins) == 256
    assert len(hw._b_bins) == 256
    assert len(hw._l_bins) == 256
    assert hw._max_val > 0

    # Modes de canaux
    for mode in ("RGB", "R", "G", "B", "L"):
        hw.set_channel_mode(mode)
        assert hw.channel_mode == mode

    hw.set_image(None)
    assert hw._has_data is False


def test_camera_info_card(qapp):
    """
    FR: Vérifie la mise à jour et l'effacement des badges EXIF de PicasaCameraInfoCard.
    EN: Verify updating and clearing EXIF badges on PicasaCameraInfoCard.
    """
    card = PicasaCameraInfoCard()
    meta = {
        "filename": "test.jpg",
        "folder": "C:/photos",
        "filesize": "2,4 Mo",
        "date": "14/10/2026 10:15:00",
        "resolution": "4000 × 3000 (12.0 MP)",
        "camera": "Canon EOS 80D",
        "properties": [
            ("Appareil photo", "Canon EOS 80D"),
            ("Ouverture", "f/2.8"),
            ("Vitesse d'obturation", "1/250 s"),
            ("Sensibilité ISO", "ISO 400"),
            ("Distance focale", "50.0 mm"),
            ("Flash", "Déclenché"),
        ]
    }
    card.update_with_metadata(meta)
    assert "Canon EOS 80D" in card.lbl_camera.text()
    assert card.badge_aperture.text() == "f/2.8"
    assert card.badge_shutter.text() == "1/250 s"
    assert card.badge_iso.text() == "400"
    assert card.badge_focal.text() == "50.0 mm"
    assert not card.badge_flash.isHidden()

    card.clear_info()
    assert "Aucune photo" in card.lbl_camera.text()
    assert card.badge_aperture.isHidden()


def test_edit_panel_5_tabs_and_wiring(qapp):
    """
    FR: Vérifie la présence des 5 onglets d'édition (icônes sans texte + info-bulles officielles) et le câblage des curseurs de réglages.
    EN: Verify the presence of the 5 editing tabs (icon-only + official tooltips) and wiring of the tuning sliders.
    """
    panel = PicasaEditPanel()
    assert panel.tabs.count() == 5

    # Dans picasa3.exe (respack.yt @ tre:editpanel, tre:drawer_tab), les 5 onglets n'ont pas de texte, uniquement une icône et une info-bulle
    for i in range(5):
        assert panel.tabs.tabText(i) == ""
        assert not panel.tabs.tabIcon(i).isNull()
        assert panel.tabs.tabToolTip(i) != ""

    for btn in panel._basic_tool_buttons.values():
        assert not btn.icon().isNull()

    # Vérification de l'histogramme et de la fiche appareil
    assert hasattr(panel, "histogram_widget")
    assert hasattr(panel, "camera_info_card")

    # Vérification de l'émission des signaux de sliders
    received_effects = []
    panel.apply_effect.connect(lambda eff, params: received_effects.append((eff, params)))

    panel.sldr_fill.setValue(50)
    panel.sldr_fill.sliderReleased.emit()
    assert any(eff == "fill_light" for eff, _ in received_effects)

    panel.sldr_highlights.setValue(40)
    panel.sldr_highlights.sliderReleased.emit()
    assert any(eff == "highlights" for eff, _ in received_effects)

    panel.sldr_shadows.setValue(30)
    panel.sldr_shadows.sliderReleased.emit()
    assert any(eff == "shadows" for eff, _ in received_effects)

    panel.sldr_temp.setValue(15)
    panel.sldr_temp.sliderReleased.emit()
    assert any(eff == "color_temp" for eff, _ in received_effects)


def test_all_image_processor_effects():
    """
    FR: Vérifie que chacun des effets d'image des 5 onglets s'exécute et retourne une image PIL valide.
    EN: Verify that every image effect across the 5 tabs executes and returns a valid PIL Image.
    """
    img = Image.new("RGB", (64, 64), color=(120, 140, 180))

    effects = [
        # Tab 1
        ("auto_contrast", lambda: PicasaImageProcessor.auto_contrast(img)),
        ("auto_color", lambda: PicasaImageProcessor.auto_color(img)),
        ("black_and_white", lambda: PicasaImageProcessor.black_and_white(img)),
        ("sepia", lambda: PicasaImageProcessor.sepia(img)),
        ("warmify", lambda: PicasaImageProcessor.warmify(img)),
        ("sharpen", lambda: PicasaImageProcessor.sharpen(img)),
        ("film_grain", lambda: PicasaImageProcessor.film_grain(img)),
        # Tab 2
        ("fill_light", lambda: PicasaImageProcessor.fill_light(img, 0.4)),
        ("highlights", lambda: PicasaImageProcessor.adjust_highlights(img, 0.4)),
        ("shadows", lambda: PicasaImageProcessor.adjust_shadows(img, 0.4)),
        ("color_temperature", lambda: PicasaImageProcessor.color_temperature(img, 20.0)),
        # Tab 3
        ("saturation", lambda: PicasaImageProcessor.saturation(img, 1.3)),
        ("tint", lambda: PicasaImageProcessor.tint(img)),
        ("soft_focus", lambda: PicasaImageProcessor.soft_focus(img)),
        ("glow", lambda: PicasaImageProcessor.glow(img)),
        ("focal_bw", lambda: PicasaImageProcessor.focal_bw(img)),
        ("graduated_tint", lambda: PicasaImageProcessor.graduated_tint(img)),
        # Tab 4
        ("hdr_simulator", lambda: PicasaImageProcessor.hdr_simulator(img)),
        ("lomo", lambda: PicasaImageProcessor.lomo(img)),
        ("orton", lambda: PicasaImageProcessor.orton(img)),
        ("sixties", lambda: PicasaImageProcessor.sixties(img)),
        ("cross_process", lambda: PicasaImageProcessor.cross_process(img)),
        ("infrared", lambda: PicasaImageProcessor.infrared(img)),
        ("holga", lambda: PicasaImageProcessor.holga(img)),
        ("cinemascope", lambda: PicasaImageProcessor.cinemascope(img)),
        ("night_vision", lambda: PicasaImageProcessor.night_vision(img)),
        ("heat_map", lambda: PicasaImageProcessor.heat_map(img)),
        # Tab 5
        ("boost", lambda: PicasaImageProcessor.boost(img)),
        ("vignette", lambda: PicasaImageProcessor.vignette(img)),
        ("two_tone", lambda: PicasaImageProcessor.two_tone(img)),
        ("pixelate", lambda: PicasaImageProcessor.pixelate(img)),
        ("invert", lambda: PicasaImageProcessor.invert(img)),
        ("focal_zoom", lambda: PicasaImageProcessor.focal_zoom(img)),
        ("soften", lambda: PicasaImageProcessor.soften(img)),
        ("comic", lambda: PicasaImageProcessor.comic(img)),
        ("neon", lambda: PicasaImageProcessor.neon(img)),
        ("pencil_sketch", lambda: PicasaImageProcessor.pencil_sketch(img)),
        ("border", lambda: PicasaImageProcessor.border(img)),
    ]

    for name, fn in effects:
        res = fn()
        assert isinstance(res, Image.Image), f"Effect {name} did not return PIL Image"
        assert res.size[0] > 0 and res.size[1] > 0, f"Effect {name} returned empty image"


def test_non_cumulative_tuning_sliders(qapp, tmp_path):
    """
    FR: Vérifie que bouger le curseur 'Lumière d'appoint' (ou les curseurs de Réglages)
    de 0 -> 60 -> 25 -> 0 ne cumule JAMAIS l'effet sur lui-même et restaure l'image
    exactement à l'identique lorsqu'on revient à 0.
    EN: Verify that moving the 'Fill Light' slider (or Tuning sliders)
    from 0 -> 60 -> 25 -> 0 NEVER compounds the effect on itself and restores the image
    identically when returning to 0.
    Ref: picasa3.exe @ filterdesc.xml (finetune2, flightslider1)
    """
    import numpy as np
    from picasa_py.ui.one_up_view import PicasaOneUpView

    img_path = tmp_path / "slider_test.png"
    base_img = Image.new("RGB", (64, 64), (80, 100, 120))
    base_img.save(str(img_path))

    view = PicasaOneUpView()
    view.open_photo(None, -1, [], direct_path=str(img_path))

    orig_arr = np.array(view._history[view._history_idx]).copy()

    # 1. Déplacer Lumière d'appoint dans l'onglet 1 (sldr_basic_fill) à 60%
    view.edit_panel.sldr_basic_fill.setValue(60)
    view.edit_panel.sldr_basic_fill.sliderReleased.emit()
    # Vérifier la synchronisation avec sldr_fill (Onglet 2)
    assert view.edit_panel.sldr_fill.value() == 60
    arr_60 = np.array(view._history[view._history_idx]).copy()
    assert np.mean(arr_60) > np.mean(orig_arr)

    # 2. Redescendre le curseur à 25% : l'image doit être MOINS lumineuse qu'à 60% (et non 60% + 25% !)
    view.edit_panel.sldr_basic_fill.setValue(25)
    view.edit_panel.sldr_basic_fill.sliderReleased.emit()
    arr_25 = np.array(view._history[view._history_idx]).copy()
    expected_25 = np.array(PicasaImageProcessor.fill_light(base_img, 0.25))
    assert np.mean(arr_25) < np.mean(arr_60)
    assert np.array_equal(arr_25, expected_25)

    # 3. Remettre le curseur à 0% : l'image doit redevenir strictement identique à l'originale
    view.edit_panel.sldr_basic_fill.setValue(0)
    view.edit_panel.sldr_basic_fill.sliderReleased.emit()
    arr_0 = np.array(view._history[view._history_idx]).copy()
    assert np.array_equal(arr_0, orig_arr)


def test_parameterized_effect_subpanel_preview_apply_cancel(qapp, tmp_path):
    """
    FR: Vérifie que cliquer sur un filtre à curseurs (mode='effect' dans filterdesc.xml)
    ouvre le sous-panneau de réglage avec aperçu en direct non-cumulatif, restaure
    l'image originale si on clique sur Annuler, et ne valide dans l'historique et
    .picasa.ini que lorsqu'on clique sur Appliquer.
    EN: Verify that clicking a parameterized filter (mode='effect' in filterdesc.xml)
    opens the parameter subpanel with non-cumulative live preview, restores the original
    image on Cancel, and only commits to history and .picasa.ini on Apply.
    Ref: picasa3.exe @ filterdesc.xml, TOOLTIPS_FR.XML (editpanel/ok, editpanel/cancel)
    """
    import numpy as np
    from picasa_py.ui.one_up_view import PicasaOneUpView
    from picasa_py.ui.edit_panel import FILTER_SPECS

    img_path = tmp_path / "effect_subpanel_test.png"
    # Créer un motif en damier pour que les filtres spatiaux (sharpen, lomo, etc.) aient un effet visible
    arr_init = np.zeros((64, 64, 3), dtype=np.uint8)
    arr_init[:, :, 0] = 100
    arr_init[::2, ::2, 1] = 200
    arr_init[:, :, 2] = 150
    base_img = Image.fromarray(arr_init)
    base_img.save(str(img_path))

    view = PicasaOneUpView()
    view.open_photo(None, -1, [], direct_path=str(img_path))
    assert view._history_idx == 0

    # 1. Ouvrir le filtre 'lomo' (qui a des curseurs blur et fade)
    assert "lomo" in FILTER_SPECS
    view.edit_panel._on_effect_button_clicked("lomo")
    assert view.edit_panel.stack.currentWidget() == view.edit_panel.effect_subpanel
    assert view.edit_panel.effect_subpanel.effect_name == "lomo"
    # L'historique ne doit pas encore avoir été incrémenté (aperçu seulement)
    assert view._history_idx == 0

    # 2. Bouger le curseur 'blur' plusieurs fois : toujours en aperçu
    blur_sldr = view.edit_panel.effect_subpanel._sliders["blur"][0]
    blur_sldr.setValue(80)
    blur_sldr.setValue(30)
    assert view._history_idx == 0

    # 3. Cliquer sur Annuler : retour aux onglets, historique inchangé à 0
    view.edit_panel.effect_subpanel.btn_cancel.click()
    assert view.edit_panel.stack.currentIndex() == 0
    assert view._history_idx == 0
    assert np.array_equal(np.array(view._history[view._history_idx]), arr_init)

    # 4. Rouvrir 'lomo', régler 'blur' à 65 et cliquer sur Appliquer
    view.edit_panel._on_effect_button_clicked("lomo")
    view.edit_panel.effect_subpanel._sliders["blur"][0].setValue(65)
    view.edit_panel.effect_subpanel.btn_apply.click()

    assert view.edit_panel.stack.currentIndex() == 0
    assert view._history_idx == 1
    assert not np.array_equal(np.array(view._history[view._history_idx]), arr_init)

