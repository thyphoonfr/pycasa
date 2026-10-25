"""FR: Tests pour la vue One-Up, le processeur d'image et la navigation dans l'éditeur.
EN: Tests for One-Up View, Image Processor, and editor navigation.

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
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    return app


@pytest.fixture
def sample_image():
    """FR: Crée une image RGB de test 100x100.
    EN: Creates a 100x100 test RGB image.
    """
    # Créer une image de test 100x100 RGB
    img = Image.new("RGB", (100, 100), color=(120, 80, 40))
    return img


def test_image_processor_filters(sample_image):
    """FR: Vérifie les filtres principaux de PicasaImageProcessor (contraste, couleur, N&B, sépia, netteté, grain).
    EN: Verifies core PicasaImageProcessor filters (auto-contrast, auto-color, B&W, sepia, sharpen, grain).
    """
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
    """FR: Vérifie les rotations horaires et antihoraires sur PicasaImageCanvas.
    EN: Verifies clockwise and counterclockwise rotations on PicasaImageCanvas.
    """
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
    """FR: Vérifie l'historique d'annulation (undo) et de rétablissement (redo) dans PicasaOneUpView.
    EN: Verifies the undo and redo history stack in PicasaOneUpView.
    """
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
    """FR: Vérifie le basculement entre la grille de photothèque et la vue One-Up dans PicasaMainWindow.
    EN: Verifies switching between the library grid and One-Up view in PicasaMainWindow.
    """
    win = PicasaMainWindow(auto_scan=True)
    assert "Erreur lors du chargement de la base de données" not in win.status_bar.currentMessage()
    assert "QTimer" not in win.status_bar.currentMessage()
    assert win.stack.currentIndex() == 0  # Grille

    # Simuler double-clic sur photo 0 si base présente
    if win.db and len(win.db.index) > 0:
        win._open_one_up_view(0)
        assert win.stack.currentIndex() == 1  # One-Up
        assert win.top_bar.isHidden()
        assert not win.photo_tray.isHidden()  # Ref: 0x0057BB80 (thumbui/basecontrolset reste visible en Édition)

        # Retour à la bibliothèque en cliquant sur le bouton « Retour à la photothèque » (`btn_back`)
        win.one_up_view.edit_panel.btn_back.click()
        assert win.stack.currentIndex() == 0  # Grille
        assert not win.top_bar.isHidden()
        assert not win.photo_tray.isHidden()

    win.close()


def test_get_media_full_path_resolution():
    """FR: Test que PicasaDatabase.get_media_full_path reconstitue correctement
    le chemin disque absolu parent_path + filename.
    EN: Tests that PicasaDatabase.get_media_full_path properly reconstructs
    the absolute disk path parent_path + filename.
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
    """FR: Test du système de zoom ancré et du navigateur Loupe avec cadre de visée orange.
    EN: Tests the anchored zoom system and Loupe navigator with orange viewport frame.
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


def test_one_up_top_bar_and_comparison_modes(qapp, sample_image):
    """FR: Test de la barre supérieure One-Up / Two-Up et des modes de comparaison
    côte à côte A, A|B, A|A.
    EN: Tests the One-Up / Two-Up top bar and side-by-side comparison modes A, A|B, A|A.
    Ref: picasa3.exe @ TwoUp, TwoUpAB (0x0088E588), TwoUpAA (0x0088E59C)
    """
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord

    db = PicasaDatabase()
    ti = ThumbIndexFile()
    rec_folder = ThumbIndexRecord(path="C:/Photos", ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=-1)
    ti.records.append(rec_folder)
    rec1 = ThumbIndexRecord(path="Photo1.jpg", ft1=0, ft2=0, size=100, type=2, flags=0, parent_idx=0)
    rec2 = ThumbIndexRecord(path="Photo2.jpg", ft1=0, ft2=0, size=100, type=2, flags=0, parent_idx=0)
    rec3 = ThumbIndexRecord(path="Photo3.jpg", ft1=0, ft2=0, size=100, type=2, flags=0, parent_idx=0)
    ti.records.extend([rec1, rec2, rec3])
    db.thumbindex = ti

    view = PicasaOneUpView()
    view.resize(1000, 700)

    # 1. Barre supérieure présente et initialisée
    assert view.viewer_top_bar is not None
    assert view.btn_top_prev is not None
    assert view.btn_top_next is not None
    assert view.btn_mode_a.isChecked()

    # 2. Ouvrir la photo 1
    view._history = [sample_image.copy()]
    view._history_idx = 0
    view._original_pil_img = sample_image.copy()
    view.db = db
    view.current_index = 1
    view.available_indices = [1, 2, 3]
    view._update_top_bar_info()
    assert "Photo 1 sur 3" in view.lbl_top_info.text()

    # 3. Basculer en mode A|B (Comparer 2 photos)
    view.mode_btn_group.button(1).click()
    assert view.canvas.view_mode == "A_B"
    assert "Comparaison A | B" in view.lbl_top_info.text()

    # Navigation en mode A|B sur le volet B
    view.canvas.active_pane = "B"
    view.secondary_index = 2
    view.navigate_next()
    assert view.secondary_index == 3

    # 4. Basculer en mode A|A (Avant / Après)
    view.mode_btn_group.button(2).click()
    assert view.canvas.view_mode == "A_A"
    assert "Comparaison A | A" in view.lbl_top_info.text()

    # 5. Revenir en mode A (Vue simple)
    view.mode_btn_group.button(0).click()
    assert view.canvas.view_mode == "A"
    assert "Photo 1 sur 3" in view.lbl_top_info.text()


def test_palette_transparency_and_huge_image_support(qapp, tmp_path):
    """FR: Vérifie le chargement sans avertissement ni rejet des images en mode palette avec transparence,
    ainsi que les images très haute résolution dépassant les limites par défaut de Qt/PIL.
    EN: Verifies warning-free loading of palette images with transparency,
    as well as very high-resolution images exceeding default Qt/PIL limits.
    """
    import warnings
    from PIL import Image
    from picasa_py.ui.one_up_view import PicasaOneUpView
    from picasa_py.ui.image_canvas import PicasaImageCanvas

    view = PicasaOneUpView()

    # 1. Image en palette (mode P) avec transparence
    pal_img = Image.new("P", (128, 128))
    pal_img.info["transparency"] = b"\x00"

    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        pix = view._pil_to_pixmap(pal_img)
        assert not pix.isNull()
        assert pix.width() == 128
        assert pix.height() == 128
        # Aucun UserWarning émis par PIL concernant la palette
        assert not any("Palette images with Transparency" in str(w.message) for w in recorded_warnings)

    # 2. Image volumineuse (> 100 Mo en mémoire décompressée)
    huge_img = Image.new("RGB", (4000, 3000), (45, 90, 135))
    pix_huge = view._pil_to_pixmap(huge_img)
    assert not pix_huge.isNull()
    assert pix_huge.width() == 4000
    assert pix_huge.height() == 3000

    # 3. Canvas load_image avec image sauvegardée sur disque
    test_path = str(tmp_path / "huge_test.png")
    huge_img.save(test_path)

    canvas = PicasaImageCanvas()
    canvas.resize(800, 600)
    success = canvas.load_image(test_path)
    assert success is True
    assert canvas._raw_pixmap is not None
    assert canvas._raw_pixmap.width() == 4000
    assert canvas._raw_pixmap.height() == 3000


def test_revert_all_edits_and_fx_thumbnails_and_2up_extra_buttons(qapp, tmp_path, sample_image):
    """FR: Vérifie les 4 comportements de Picasa 3 :
    1) Clic droit -> Annuler toutes les modifications (ID_PICTURE_REVERT / action_undo_all_edits) ;
    2) Miniatures d'aperçu d'effets dans la colonne de gauche (editpanel/fxthumbs, editpanel/fx1..fx12) ;
    3) Boutons d'icônes sans texte dans les onglets de la colonne de droite (people/places/tags/properties_toggle) ;
    4) Apparition des 2 boutons supplémentaires (swap_2up_layout et swap_2up_focus) en mode A|B et A|A.
    EN: Verifies the 4 Picasa 3 behaviors:
    1) Right-click -> Undo All Edits (ID_PICTURE_REVERT / action_undo_all_edits);
    2) Live effect preview thumbnails in the left edit panel (editpanel/fxthumbs, editpanel/fx1..fx12);
    3) Icon-only buttons with no text for the right drawer toggles (people/places/tags/properties_toggle);
    4) Visibility and behavior of the 2 extra buttons (swap_2up_layout and swap_2up_focus) in A|B and A|A modes.
    Ref: picasa3.exe @ 0x00C8D849, 0x00568A08, 0x005D96D4, 0x00569720, 0x0056A160
    """
    from picasa_py.ini.parser import PicasaIniParser
    from picasa_py.ui.photo_tray import PicasaPhotoTray
    from picasa_py.ui.edit_panel import PicasaEffectTileButton

    # --- 1. Right-click -> Annuler toutes les modifications (action_undo_all_edits) ---
    photo_file = tmp_path / "test_revert.jpg"
    sample_image.save(str(photo_file), "JPEG")
    ini_file = tmp_path / ".picasa.ini"

    win = PicasaMainWindow()
    win.db = PicasaDatabase(tmp_path / "db3")
    win._update_photo_ini(
        str(photo_file),
        lambda doc, fname: (
            doc.set_rotate(fname, 1),
            doc.set_tilt(fname, 0.25),
            doc.get_or_create_section(fname).set("filters", "sepia=1;bw=1;"),
        ),
    )
    doc_before = PicasaIniParser.parse_file(ini_file)
    assert doc_before.get_rotate("test_revert.jpg") == 1
    assert doc_before.get_section("test_revert.jpg").get("filters") == "sepia=1;bw=1;"

    win.action_undo_all_edits([str(photo_file)])

    doc_after = PicasaIniParser.parse_file(ini_file)
    assert doc_after.get_rotate("test_revert.jpg") == 0
    assert doc_after.get_tilt("test_revert.jpg") is None
    sec_after = doc_after.get_section("test_revert.jpg")
    assert sec_after is None or sec_after.get("filters") is None

    # --- 2. Miniatures d'effets dans la colonne de gauche (editpanel/fxthumbs) ---
    view = win.one_up_view
    view.edit_panel.set_image(sample_image)
    for tab_idx in (2, 3, 4):
        view.edit_panel.tabs.setCurrentIndex(tab_idx)
        tiles = view.edit_panel._effect_tiles_by_tab[tab_idx]
        assert len(tiles) >= 12
        for tile in tiles:
            assert isinstance(tile, PicasaEffectTileButton)
            assert tile.preview_pixmap is not None
            assert not tile.preview_pixmap.isNull()
            assert tile.preview_pixmap.width() == 46
            assert tile.preview_pixmap.height() == 46

    # --- 3. Boutons de la colonne de droite : icônes uniquement et aucun texte ---
    tray = PicasaPhotoTray()
    for btn in (
        tray.btn_panel_people,
        tray.btn_panel_places,
        tray.btn_panel_tags,
        tray.btn_panel_props,
        view.btn_panel_people,
        view.btn_panel_places,
        view.btn_panel_tags,
        view.btn_panel_props,
    ):
        assert btn.text() == ""
        assert not btn.icon().isNull()
        assert len(btn.toolTip()) > 0

    # --- 4. Boutons supplémentaires A|B et A|A : swap_2up_layout et swap_2up_focus ---
    view._on_view_mode_changed(0)  # Mode 1-Up ("A")
    assert not view.btn_swap_2up_layout.isVisibleTo(view.viewer_top_bar)
    assert not view.btn_swap_2up_focus.isVisibleTo(view.viewer_top_bar)

    view._on_view_mode_changed(1)  # Mode A|B
    assert view.btn_swap_2up_layout.isVisibleTo(view.viewer_top_bar)
    assert view.btn_swap_2up_focus.isVisibleTo(view.viewer_top_bar)
    assert view.canvas.split_orientation == "horizontal"
    assert view.canvas.active_pane == "A"

    # Clic sur swap_2up_layout -> bascule horizontal <-> vertical
    view.btn_swap_2up_layout.click()
    assert view.canvas.split_orientation == "vertical"
    view.btn_swap_2up_layout.click()
    assert view.canvas.split_orientation == "horizontal"

    # Clic sur swap_2up_focus -> bascule A <-> B
    view.btn_swap_2up_focus.click()
    assert view.canvas.active_pane == "B"
    view.btn_swap_2up_focus.click()
    assert view.canvas.active_pane == "A"

    # Mode A|A -> les 2 boutons restent visibles
    view._on_view_mode_changed(2)
    assert view.btn_swap_2up_layout.isVisibleTo(view.viewer_top_bar)
    assert view.btn_swap_2up_focus.isVisibleTo(view.viewer_top_bar)

    # Retour en mode 1-Up -> les 2 boutons sont masqués
    view._on_view_mode_changed(0)
    assert not view.btn_swap_2up_layout.isVisibleTo(view.viewer_top_bar)
    assert not view.btn_swap_2up_focus.isVisibleTo(view.viewer_top_bar)

    win.close()


def test_modal_tool_and_effect_ui_locking(qapp, tmp_path, sample_image):
    """FR: Vérifie que cliquer sur Recadrer, Redresser, Texte, Yeux rouges, Retoucher ou un filtre
    paramétré (`mode="effect"`) verrouille la barre du haut (`viewer_top_bar`), masque la barre de
    légende (`caption_bar`), verrouille la barre du bas (`transport_bar`), la colonne de droite
    (`right_drawer`) et les onglets/boutons globaux du panneau gauche jusqu'à Appliquer ou Annuler,
    tandis que les effets instantanés (`mode="oneclick"`) et les curseurs d'éclairage (`mode="soft"`)
    ne verrouillent pas l'interface, conformément à `FUN_0057bb50 @ 0x0057BB50` et `FUN_005f8520 @ 0x005F8520`.
    EN: Verifies that clicking Crop, Straighten, Text, Red-eye, Retouch, or a parameterized filter
    (`mode="effect"`) locks the top bar (`viewer_top_bar`), hides the caption bar (`caption_bar`),
    locks the bottom bar (`transport_bar`), the right drawer (`right_drawer`), and the left panel
    tabs/global buttons until Apply or Cancel, while instant effects (`mode="oneclick"`) and tuning
    sliders (`mode="soft"`) do not lock the UI, matching `FUN_0057bb50 @ 0x0057BB50` and `FUN_005f8520 @ 0x005F8520`.
    Ref: picasa3.exe @ 0x0057BB50, 0x005F8520, 0x005F8730, 0x00900490
    """
    p1 = tmp_path / "lock_test_1.jpg"
    p2 = tmp_path / "lock_test_2.jpg"
    sample_image.save(str(p1), "JPEG")
    sample_image.save(str(p2), "JPEG")

    db = PicasaDatabase()
    from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord
    ti = ThumbIndexFile()
    ti.records.append(ThumbIndexRecord(path=str(tmp_path), ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=-1))
    ti.records.append(ThumbIndexRecord(path="lock_test_1.jpg", ft1=0, ft2=0, size=100, type=2, flags=0, parent_idx=0))
    ti.records.append(ThumbIndexRecord(path="lock_test_2.jpg", ft1=0, ft2=0, size=100, type=2, flags=0, parent_idx=0))
    db.thumbindex = ti

    view = PicasaOneUpView()
    view.resize(1200, 800)
    view.show()
    view.open_photo(db, 1, [1, 2], direct_path=str(p1))
    view.right_drawer.show_panel("people")

    def _assert_locked(expected: bool) -> None:
        """FR: Vérifie l'état de verrouillage de toutes les barres et panneaux.
        EN: Asserts the lock state of all bars and panels.
        """
        assert view._is_tool_locked is expected
        assert view.edit_panel.is_tool_locked is expected
        assert view.viewer_top_bar.isEnabled() is (not expected)
        assert view.transport_bar.isEnabled() is (not expected)
        assert view.right_drawer.isEnabled() is (not expected)
        assert view.edit_panel.tabs.tabBar().isEnabled() is (not expected)
        assert view.edit_panel.btn_undo.isEnabled() is (not expected)
        assert view.edit_panel.btn_redo.isEnabled() is (not expected)
        assert view.edit_panel.btn_save.isEnabled() is (not expected)
        assert view.caption_bar.isHidden() is expected

    _assert_locked(False)

    # 1. Outil Recadrer (mode == 2) : verrouille jusqu'à Annuler ou Appliquer
    view.edit_panel.btn_crop.click()
    _assert_locked(True)
    assert view._active_tool_mode == 2
    # La navigation est bloquée pendant que l'outil est actif
    view.navigate_next()
    assert view.current_index == 1
    # Annuler déverrouille tout
    view.edit_panel.crop_subpanel.btn_cancel.click()
    _assert_locked(False)

    # 2. Outil Redresser (mode == 6 + forcefit="1") : force le zoom Fit et verrouille jusqu'à Appliquer/Annuler
    view.canvas.set_zoom(2.0)
    assert view.canvas.fit_to_window is False
    view.edit_panel.btn_straighten.click()
    _assert_locked(True)
    assert view._active_tool_mode == 6
    assert view.canvas.fit_to_window is True  # <zoom forcefit="1"/> @ 0x005F8730
    view.edit_panel.straighten_subpanel.btn_apply.click()
    _assert_locked(False)

    # 3. Filtre paramétré (mode == 4, ex: "sepia" retiré de ONECLICK ou "tint" / "soft_focus") :
    #    - "sepia", "bw", "warmify", "sharpen", "invert" sont mode="oneclick" (mode == 1) -> pas de verrouillage
    view.edit_panel._on_effect_button_clicked("sepia")
    _assert_locked(False)
    view.edit_panel._on_effect_button_clicked("invert")
    _assert_locked(False)

    #    - "soft_focus" est mode="effect" (mode == 4) avec forcefit="1" -> ouvre sous-panneau et verrouille
    view.canvas.set_zoom(1.8)
    view.edit_panel._on_effect_button_clicked("soft_focus")
    _assert_locked(True)
    assert view._active_tool_mode == 4
    assert view.canvas.fit_to_window is True
    view.edit_panel.effect_subpanel.btn_cancel.click()
    _assert_locked(False)

    # 4. Curseurs d'éclairage (mode == 5, "soft" finetune2) -> aperçu direct sans verrouiller les barres
    view.edit_panel.sldr_fill.setValue(25)
    _assert_locked(False)

    # 5. Clic sur « Retour à la photothèque » (`btn_back`) en mode normal et pendant un outil actif
    back_signals: list[bool] = []
    view.back_to_library_requested.connect(lambda: back_signals.append(True))
    view.edit_panel.btn_back.click()
    assert len(back_signals) == 1

    view.edit_panel.btn_crop.click()
    _assert_locked(True)
    view.edit_panel.btn_back.click()
    _assert_locked(False)
    assert len(back_signals) == 2

    view.close()


def test_single_bottom_bar_mode_buttons_and_infotext_header(qapp, tmp_path, sample_image):
    """
    FR: Vérifie que `PicasaMainWindow` n'affiche qu'UNE SEULE barre inférieure (`self.photo_tray` /
    `thumbui/basecontrolset`, avec `self.one_up_view.transport_bar` masquée), bascule la visibilité
    des boutons selon le mode (Bibliothèque vs Édition 1-Up photo/vidéo, `0x0057BB80..0x0057C3A3`),
    et formate l'en-tête `thumbui/infotext` exactement comme `picasa3.exe` (`0x0056FBC0`, `0x00566E5A`,
    `0x0056F920`).
    EN: Verifies that `PicasaMainWindow` displays ONLY ONE bottom bar (`self.photo_tray` /
    `thumbui/basecontrolset`, with `self.one_up_view.transport_bar` hidden), toggles button visibility
    by mode (Library vs One-Up Edit photo/video, `0x0057BB80..0x0057C3A3`), and formats the
    `thumbui/infotext` header exactly like `picasa3.exe` (`0x0056FBC0`, `0x00566E5A`, `0x0056F920`).
    """
    import time
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord
    from picasa_py.ui.main_window import PicasaMainWindow
    from picasa_py.ui.thumbnail_view import ThumbnailItem

    folder_dir = tmp_path / "Vacances2026"
    folder_dir.mkdir(parents=True, exist_ok=True)
    p1 = folder_dir / "plage_matin.jpg"
    p2 = folder_dir / "plage_soir.jpg"
    sample_image.save(str(p1), "JPEG")
    sample_image.save(str(p2), "JPEG")

    # Définir deux dates différentes et un fichier .picasa.ini avec keywords=mer,soleil
    t1 = 1711968600.0  # 2024-04-01 12:50 local
    t2 = 1712141400.0  # 2024-04-03 12:50 local
    os.utime(str(p1), (t1, t1))
    os.utime(str(p2), (t2, t2))
    ini_file = folder_dir / ".picasa.ini"
    ini_file.write_text("[plage_matin.jpg]\r\nkeywords=mer,soleil\r\n", encoding="utf-8")

    db_dir = tmp_path / "db3"
    db_dir.mkdir(parents=True, exist_ok=True)
    win = PicasaMainWindow(db_path=str(db_dir), auto_scan=False)
    win.resize(1280, 800)

    db = PicasaDatabase()
    ti = ThumbIndexFile()
    ti.records.append(ThumbIndexRecord(path=str(folder_dir), ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=-1))
    ti.records.append(ThumbIndexRecord(path="plage_matin.jpg", ft1=0, ft2=0, size=100, type=2, flags=0, parent_idx=0))
    ti.records.append(ThumbIndexRecord(path="plage_soir.jpg", ft1=0, ft2=0, size=100, type=2, flags=0, parent_idx=0))
    db.thumbindex = ti
    win.db = db

    it1 = ThumbnailItem(
        index=1,
        path=str(p1),
        filename="plage_matin.jpg",
        folder="Vacances2026",
        folder_path=str(folder_dir),
    )
    it2 = ThumbnailItem(
        index=2,
        path=str(p2),
        filename="plage_soir.jpg",
        folder="Vacances2026",
        folder_path=str(folder_dir),
    )
    win.thumb_view.items = [it1, it2]
    win.thumb_view.filtered_indices = [0, 1]

    # 1. En mode Bibliothèque : 0 sélection -> "Aucune sélection"
    win._on_selection_changed([])
    assert win.photo_tray.lbl_selection.text() == "Aucune sélection"
    assert win.one_up_view.transport_bar.isHidden() is True
    assert win.photo_tray.zoom_slider.isHidden() is False
    assert win.photo_tray.btn_toggle_left_drawer.isHidden() is True
    assert win.photo_tray.btn_fit.isHidden() is True
    assert win.photo_tray.btn_zoom_1to1.isHidden() is True
    assert win.photo_tray.oneup_zoom_slider.isHidden() is True
    assert win.photo_tray.btn_toggle_faces.isHidden() is True

    # 2. En mode Bibliothèque : 1 photo sélectionnée -> nom, date, résolution WxH pixels, taille, Tags
    win.thumb_view.selected_indices = {0}
    win._on_selection_changed([0])
    info_single = win.photo_tray.lbl_selection.text()
    assert "plage_matin.jpg" in info_single
    assert f"{sample_image.width}x{sample_image.height} pixels" in info_single
    assert "Tags : mer, soleil" in info_single

    # 3. En mode Bibliothèque : 2 photos sélectionnées avec dates différentes -> "2 photos     ... à ...     ... sur le disque"
    win.thumb_view.selected_indices = {0, 1}
    win._on_selection_changed([0, 1])
    info_multi = win.photo_tray.lbl_selection.text()
    assert info_multi.startswith("2 photos     ")
    assert " à " in info_multi
    assert "sur le disque" in info_multi
    assert "Tags : mer, soleil" in info_multi

    # 4. Double-clic / Ouverture en mode Édition 1-Up :
    #    - UNE SEULE barre du bas (`win.one_up_view.transport_bar` reste masquée !)
    #    - Les contrôles 1-Up (`btn_toggle_left_drawer`, `btn_fit`, `btn_zoom_1to1`, `oneup_zoom_slider`, `btn_toggle_faces`) sont visibles
    #    - Le curseur d'échelle de la grille (`zoom_slider`) est masqué
    #    - L'en-tête `thumbui/infotext` affiche "Vacances2026 > plage_matin.jpg     ...     WxH pixels     ...    (1 sur 2)    Tags : mer, soleil"
    win._open_one_up_view(0)
    assert win.stack.currentWidget() == win.one_up_view
    assert win.one_up_view.transport_bar.isHidden() is True
    assert win.photo_tray.isHidden() is False
    assert win.photo_tray.zoom_slider.isHidden() is True
    assert win.photo_tray.btn_toggle_left_drawer.isHidden() is False
    assert win.photo_tray.btn_fit.isHidden() is False
    assert win.photo_tray.btn_zoom_1to1.isHidden() is False
    assert win.photo_tray.oneup_zoom_slider.isHidden() is False
    assert win.photo_tray.btn_toggle_faces.isHidden() is False

    info_oneup = win.photo_tray.lbl_selection.text()
    assert info_oneup.startswith("Vacances2026 > plage_matin.jpg     ")
    assert f"{sample_image.width}x{sample_image.height} pixels" in info_oneup
    assert "(1 sur 2)" in info_oneup
    assert "Tags : mer, soleil" in info_oneup

    # 5. Clic sur la 2e miniature dans le bac en mode 1-Up : met à jour l'en-tête vers (2 sur 2) et garde 1 seule barre
    from PySide6.QtCore import Qt
    win.photo_tray.thumb_strip._on_widget_clicked_with_modifiers(it2, Qt.KeyboardModifier.NoModifier)
    assert win.one_up_view.transport_bar.isHidden() is True
    info_oneup_2 = win.photo_tray.lbl_selection.text()
    assert info_oneup_2.startswith("Vacances2026 > plage_soir.jpg     ")
    assert "(2 sur 2)" in info_oneup_2

    # 6. En mode vidéo 1-Up : masque les contrôles de zoom et désactive la rotation
    win.photo_tray.set_edit_mode(True, is_video=True)
    assert win.photo_tray.btn_fit.isHidden() is True
    assert win.photo_tray.btn_zoom_1to1.isHidden() is True
    assert win.photo_tray.oneup_zoom_slider.isHidden() is True
    assert win.photo_tray.btn_rotate_left.isEnabled() is False
    assert win.photo_tray.btn_rotate_right.isEnabled() is False

    # 7. Retour à la photothèque : restaure les contrôles de bibliothèque et l'en-tête de sélection
    win._back_to_library()
    assert win.stack.currentWidget() != win.one_up_view
    assert win.photo_tray.zoom_slider.isHidden() is False
    assert win.photo_tray.btn_toggle_left_drawer.isHidden() is True
    assert win.photo_tray.btn_fit.isHidden() is True
    assert win.photo_tray.oneup_zoom_slider.isHidden() is True
    assert win.photo_tray.lbl_selection.text().startswith("2 photos     ")

    win.stop_background_tasks()
    win.close()


def test_oneup_zoom_slider_and_two_up_loupe_navigator(qapp: QApplication, sample_image, tmp_path: Path):
    """Vérifie le curseur de zoom 1-Up (`oneup_zoom_slider`) et la miniature Loupe en modes A, A|B et A|A."""
    from picasa_py.ui.main_window import PicasaMainWindow
    from picasa_py.ui.thumbnail_view import ThumbnailItem
    from PySide6.QtGui import QPixmap

    folder_dir = tmp_path / "PhotosZoom"
    folder_dir.mkdir(parents=True, exist_ok=True)
    p1 = folder_dir / "photo_a.jpg"
    p2 = folder_dir / "photo_b.jpg"
    sample_image.save(str(p1), "JPEG")
    sample_image.save(str(p2), "JPEG")

    db_dir = tmp_path / "db3_zoom"
    db_dir.mkdir(parents=True, exist_ok=True)
    win = PicasaMainWindow(db_path=str(db_dir), auto_scan=False)
    win.resize(1200, 800)

    it1 = ThumbnailItem(
        index=1,
        path=str(p1),
        filename="photo_a.jpg",
        folder="PhotosZoom",
        folder_path=str(folder_dir),
    )
    it2 = ThumbnailItem(
        index=2,
        path=str(p2),
        filename="photo_b.jpg",
        folder="PhotosZoom",
        folder_path=str(folder_dir),
    )
    win.thumb_view.items = [it1, it2]
    win.thumb_view.filtered_indices = [0, 1]

    win._open_one_up_view(0)
    canvas = win.one_up_view.canvas
    canvas.resize(800, 600)
    # Injecter un QPixmap haute résolution (800x600) directement pour un test déterministe
    pm = QPixmap(800, 600)
    pm.fill()
    canvas.set_pixmap_direct(pm)
    canvas.set_secondary_pixmap(pm, "Photo B")

    # 1. Par défaut : ajusté à la fenêtre (fit_to_window = True, pas de Loupe affichée)
    assert canvas.fit_to_window is True
    assert canvas.is_zoomed_in() is False

    # 2. Déplacement du curseur `oneup_zoom_slider` dans la barre du bas (ex: 200% = 2.0x)
    win.photo_tray.oneup_zoom_slider.setValue(200)
    assert canvas.fit_to_window is False
    assert canvas.zoom_level == pytest.approx(2.0, rel=1e-2)
    assert canvas.is_zoomed_in() is True
    canvas._update_loupe_geometry()
    assert not canvas._nav_card_rect.isEmpty()
    assert not canvas._nav_img_rect.isEmpty()
    assert not canvas._vbox_rect.isEmpty()

    # 3. Retour du curseur `oneup_zoom_slider` tout à gauche (minimum = Fit) -> réinitialise `fit_to_window`
    win.photo_tray.oneup_zoom_slider.setValue(win.photo_tray.oneup_zoom_slider.minimum())
    assert canvas.fit_to_window is True
    assert canvas.is_zoomed_in() is False

    # 4. En mode comparaison A|B (`view_mode == "A_B"`) : zoom via le curseur -> miniature Loupe + cadre orange actifs
    win.one_up_view.mode_btn_group.button(1).click()
    assert canvas.view_mode == "A_B"
    canvas.set_secondary_pixmap(pm, "Photo B")
    win.photo_tray.oneup_zoom_slider.setValue(250)
    assert canvas.fit_to_window is False
    assert canvas.zoom_level == pytest.approx(2.5, rel=1e-2)
    assert canvas.is_zoomed_in() is True
    canvas._update_loupe_geometry()
    assert not canvas._nav_card_rect.isEmpty()
    assert not canvas._nav_img_rect.isEmpty()
    assert not canvas._vbox_rect.isEmpty()
    # Vérifie que le rendu A|B avec Loupe s'exécute sans erreur
    grabbed_ab = canvas.grab()
    assert not grabbed_ab.isNull()

    # 5. En mode comparaison A|A (`view_mode == "A_A"`) : miniature Loupe + cadre orange également actifs
    win.one_up_view.mode_btn_group.button(2).click()
    assert canvas.view_mode == "A_A"
    canvas.set_original_pixmap(pm)
    assert canvas.is_zoomed_in() is True
    canvas._update_loupe_geometry()
    assert not canvas._nav_card_rect.isEmpty()
    assert not canvas._nav_img_rect.isEmpty()
    assert not canvas._vbox_rect.isEmpty()
    grabbed_aa = canvas.grab()
    assert not grabbed_aa.isNull()

    # 6. En modes A|B et A|A :
    #    - la pellicule (`filmstrip`) entre `btn_top_prev` et `btn_top_next` conserve sa largeur (>= 214 px)
    #    - les boutons `btn_swap_2up_layout` (horizontal/vertical) et `btn_swap_2up_focus` sont visibles et non rognés
    #    - l'en-tête `thumbui/infotext` (`lbl_selection`) est centré (`Qt.AlignmentFlag.AlignCenter`)
    from PySide6.QtCore import Qt
    assert bool(win.photo_tray.lbl_selection.alignment() & Qt.AlignmentFlag.AlignHCenter)
    assert win.one_up_view.filmstrip.isVisibleTo(win.one_up_view.viewer_top_bar)
    assert win.one_up_view.filmstrip.width() >= 214
    assert win.one_up_view.btn_swap_2up_layout.isVisibleTo(win.one_up_view.viewer_top_bar)
    assert win.one_up_view.btn_swap_2up_focus.isVisibleTo(win.one_up_view.viewer_top_bar)
    assert win.one_up_view.btn_swap_2up_layout.geometry().right() <= win.one_up_view.viewer_top_bar.width()

    win.stop_background_tasks()
    win.close()




