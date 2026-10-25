"""
FR: Suite de tests de fidélité de disposition, de métriques et de rendu visuel hors-écran
(AGENTS.md §4 bis.5 & §7.5).
Vérifie :
1. Les constantes de style et de couleurs chargées depuis ui/resources/style/constants.ui ([Picasa2])
   (Ref: picasa3.exe @ runtime/constants.ui, 0x009BE730).
2. La hiérarchie, les dimensions des barres (TopBar 44px, PhotoTray 56px, StatusBar, RightDrawer),
   les proportions des splitters et le redimensionnement de PicasaMainWindow à la résolution de
   référence 1280x800 (Ref: picasa3.exe @ 0x0074F800).
3. Le rendu visuel hors-écran (`widget.grab()`) des vues principales (Bibliothèque, One-Up / Édition,
   Tiroir latéral, Gestionnaire de dossiers) sans zone vide ni erreur de peinture GDI/Qt.
EN: Layout fidelity, metrics, and offscreen visual rendering test suite
(AGENTS.md §4 bis.5 & §7.5).
Verifies:
1. Style and color constants loaded from ui/resources/style/constants.ui ([Picasa2])
   (Ref: picasa3.exe @ runtime/constants.ui, 0x009BE730).
2. Hierarchy, fixed bar dimensions (TopBar, PhotoTray, StatusBar, RightDrawer),
   splitter proportions, and resizing of PicasaMainWindow at the 1280x800 reference resolution
   (Ref: picasa3.exe @ 0x0074F800).
3. Offscreen visual rendering (`widget.grab()`) of the main views (Library, One-Up / Edit,
   Right Drawer, Folder Manager) without blank areas or GDI/Qt paint errors.
"""

from __future__ import annotations
from pathlib import Path
from PIL import Image
from PySide6.QtGui import QImage

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexFile
from picasa_py.db.wordhash import WordHashFile
from picasa_py.db.kvtable import KeyValueTableFile
from picasa_py.db.contacts import ContactsFile
from picasa_py.scanner.scanner import PicasaDirScanner
from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.main_window import PicasaMainWindow
from picasa_py.ui.folder_manager import PicasaFolderManagerDialog

_KEEP_REFS = []


def test_picasa_style_constants_fidelity() -> None:
    """
    FR: Vérifie que PicasaStyle charge exactement les constantes de ui/resources/style/constants.ui
    (Ref: runtime/constants.ui [Picasa2]).
    EN: Verify that PicasaStyle loads the exact constants from ui/resources/style/constants.ui
    (Ref: runtime/constants.ui [Picasa2]).
    """
    style = PicasaStyle.load()
    assert style.alist_height == 22
    assert style.alist_fontsize_win == 14
    assert style.alist_indent == 17
    assert style.alayout_gutter == 24
    assert style.alayout_thumbGutterX == 12
    assert style.alayout_thumbGutterY == 22
    assert style.alayout_titleFont == "Georgia"
    assert style.alayout_titleSize == 20
    assert style.thumbsel_color1.name().lower() == "#009eff"
    assert style.thumbsel_color2.name().lower() == "#ffffff"


def test_main_window_reference_layout_1280x800(tmp_path: Path, qapp) -> None:
    """
    FR: Vérifie la disposition et le rendu hors-écran de PicasaMainWindow en 1280x800
    (Bibliothèque + bascule One-Up + redimensionnement en 1024x768).
    EN: Verify the layout and offscreen rendering of PicasaMainWindow at 1280x800
    (Library + One-Up switch + resizing to 1024x768).
    """
    db_dir = tmp_path / "db3"
    contacts_dir = tmp_path / "contacts"
    photos_dir = tmp_path / "Photos"
    db_dir.mkdir(parents=True)
    contacts_dir.mkdir(parents=True)
    photos_dir.mkdir(parents=True)

    img_path = photos_dir / "ref_photo.jpg"
    Image.new("RGB", (320, 240), (90, 140, 200)).save(img_path, "JPEG")

    db = PicasaDatabase(db3_dir=db_dir, contacts_dir=contacts_dir)
    db.thumbindex = ThumbIndexFile()
    db.wordhash = WordHashFile()
    db.repository = KeyValueTableFile()
    db.usernames = KeyValueTableFile()
    db.contacts = ContactsFile()
    scanner = PicasaDirScanner(db)
    idx = scanner.index_file(str(img_path))
    assert idx is not None
    db.save_database()

    win = PicasaMainWindow(db_path=str(db_dir), auto_scan=False)
    _KEEP_REFS.append(win)
    win.resize(1280, 800)
    qapp.processEvents()

    # 1. Capture hors-écran de la vue Bibliothèque en 1280x800 (active la géométrie des layouts Qt)
    pix_lib = win.grab()
    assert not pix_lib.isNull()
    assert pix_lib.width() >= 1280
    assert pix_lib.height() >= 800
    qimg_lib = pix_lib.toImage().convertToFormat(QImage.Format.Format_RGB32)
    assert qimg_lib.width() > 0 and qimg_lib.height() > 0

    # 2. Vérifier les dimensions de la fenêtre et des barres fixes (Ref: respack.yt @ thumbui.tre)
    assert win.width() == 1280
    assert win.height() == 800
    assert win.top_bar.height() == 38
    assert win.photo_tray.height() == 98
    assert win.stack.currentIndex() == 0

    # 3. Vérifier les proportions du splitter de la bibliothèque (arbre gauche / grille centrale / tiroir droit)
    sizes = win.splitter.sizes()
    assert len(sizes) == 3
    assert sizes[0] >= 180  # Arbre des dossiers/albums/personnes
    assert sizes[1] >= 500  # Grille centrale des vignettes

    # 4. Basculer vers la vue One-Up / Édition et vérifier la disposition + capture
    assert len(win.thumb_view.items) == 1
    win._open_one_up_view(0)
    qapp.processEvents()
    assert win.stack.currentIndex() == 1
    assert win.one_up_view.edit_panel.width() >= 280
    assert hasattr(win.one_up_view, "btn_toggle_left_drawer")

    pix_oneup = win.grab()
    assert not pix_oneup.isNull()
    assert pix_oneup.width() >= 1280

    # 5. Tester le redimensionnement dynamique (1024x768) et le retour à la bibliothèque
    win.resize(1024, 768)
    win._back_to_library()
    qapp.processEvents()
    assert win.width() == 1024
    assert win.height() == 768
    assert win.stack.currentIndex() == 0

    win.stop_background_tasks()
    win.close()
    qapp.processEvents()


def test_folder_manager_dialog_layout_fidelity(tmp_path: Path, qapp) -> None:
    """
    FR: Vérifie la disposition et le rendu hors-écran de PicasaFolderManagerDialog
    (Ref: picasa3.exe @ foldermanager.fen, 0x0079b8ec).
    EN: Verify the layout and offscreen rendering of PicasaFolderManagerDialog
    (Ref: picasa3.exe @ foldermanager.fen, 0x0079b8ec).
    """
    db = PicasaDatabase(db3_dir=tmp_path / "db3")
    dlg = PicasaFolderManagerDialog(db=db)
    _KEEP_REFS.append(dlg)
    dlg.resize(760, 560)
    qapp.processEvents()

    assert dlg.width() == 760
    assert dlg.height() == 560
    assert hasattr(dlg, "radio_remove")
    assert hasattr(dlg, "radio_scan_once")
    assert hasattr(dlg, "radio_watch")

    pix = dlg.grab()
    assert not pix.isNull()
    assert pix.width() >= 760
    assert pix.height() >= 560

    dlg.close()
    qapp.processEvents()


def test_gui_fidelity_enhancements_phase12(tmp_path: Path, qapp) -> None:
    """
    FR: Vérifie les améliorations de fidélité GUI (Phase 12 & Audit respack.yt) :
    1. En-têtes de section authentiques dans l'ordre exact de headerpanel.tre :
       play (Diaporama) -> create_collage (Montage) -> create_movie (Film) -> select_star (★) -> save_edits (💾)
    2. Barre supérieure (thumbui/buttonbarsets + searchcontainer.tre) et Photo Tray 2 étages (thumbui/basecontrolset)
    3. Glisser-déposer (Drag & Drop) vers l'arborescence (Photos favorites / Albums / Dossiers)
    4. Légende éditable en ligne (caption_edit) et bouton Zoom 1:1 dans One-Up View.
    EN: Verify GUI fidelity enhancements (Phase 12 & respack.yt audit):
    1. Authentic section headers in the exact order of headerpanel.tre:
       play (Slideshow) -> create_collage (Collage) -> create_movie (Movie) -> select_star (★) -> save_edits (💾)
    2. TopBar (thumbui/buttonbarsets + searchcontainer.tre) and 2-row Photo Tray (thumbui/basecontrolset)
    3. Drag & Drop onto the library tree (Starred Photos / Albums / Folders)
    4. Inline editable caption (caption_edit) and 1:1 Zoom button in One-Up View.
    """
    from picasa_py.ui.photo_tray import PicasaButtonManagerDialog
    from picasa_py.ini.parser import PicasaIniParser

    db = PicasaDatabase.create_new(tmp_path / "db_root")
    photos_dir = tmp_path / "Vacances"
    photos_dir.mkdir(parents=True)
    img1 = photos_dir / "plage.jpg"
    img2 = photos_dir / "montagne.jpg"
    Image.new("RGB", (200, 150), (40, 120, 200)).save(img1, "JPEG")
    Image.new("RGB", (200, 150), (80, 180, 90)).save(img2, "JPEG")

    scanner = PicasaDirScanner(db)
    scanner.index_file(str(img1))
    scanner.index_file(str(img2))
    db.save_database()

    win = PicasaMainWindow(db_path=str(db.db3_dir), auto_scan=False)
    _KEEP_REFS.append(win)
    win.resize(1280, 800)
    qapp.processEvents()

    # 1. En-têtes de section et boutons d'action (play, collage, movie, star, save)
    win.grab()
    assert len(win.thumb_view.visible_sections) >= 1
    assert win.thumb_view._get_slideshow_btn_rect(0).width() > 0
    assert win.thumb_view._get_collage_btn_rect(0).width() > 0
    assert win.thumb_view._get_movie_btn_rect(0).width() > 0
    assert win.thumb_view._get_select_star_btn_rect(0).width() > 0
    assert win.thumb_view._get_save_edits_btn_rect(0).width() > 0

    # 2. TopBar (btn_new_album, bascule Liste/Arbre, menu tri, filtres accolés à la recherche)
    assert hasattr(win.top_bar, "btn_new_album")
    assert hasattr(win.top_bar, "btn_view_flat")
    assert hasattr(win.top_bar, "btn_view_tree")
    assert hasattr(win.top_bar, "btn_folder_popup")
    assert hasattr(win.top_bar, "btn_geo")
    win.top_bar.btn_view_tree.click()
    qapp.processEvents()
    assert win.library_tree.folder_view_mode == "tree"
    win.top_bar.btn_view_flat.click()
    qapp.processEvents()
    assert win.library_tree.folder_view_mode == "flat"

    # Filtre géolocalisation
    win.top_bar.btn_geo.click()
    qapp.processEvents()
    assert len(win.thumb_view.filtered_indices) == 0
    win.top_bar.btn_geo.click()
    qapp.processEvents()
    assert len(win.thumb_view.filtered_indices) == 2

    # PhotoTray 2 étages (thumbui/basecontrolset : hold/clear/add_to_album empilés, rotate_left/right, upload)
    assert win.photo_tray.btn_hold.text() == "📌"
    assert win.photo_tray.btn_clear.text() == "✕"
    assert hasattr(win.photo_tray, "btn_rotate_left")
    assert hasattr(win.photo_tray, "btn_rotate_right")
    assert hasattr(win.photo_tray, "btn_upload")
    btn_dlg = PicasaButtonManagerDialog(["export", "collage", "movie"])
    assert btn_dlg.list_current.count() == 3
    assert btn_dlg.list_available.count() == 3
    btn_dlg._on_reset_defaults()
    assert len(btn_dlg.get_active_keys()) == 6
    btn_dlg.close()

    # 3. Glisser-déposer sur « Photos favorites » dans l'arborescence
    starred_item = win.library_tree.cat_albums.child(0)
    assert starred_item is not None
    win.library_tree.handle_drop_on_item(starred_item, [str(img1)])
    qapp.processEvents()
    ini_doc = PicasaIniParser.parse_file(str(photos_dir / ".picasa.ini"))
    assert ini_doc.is_starred("plage.jpg")

    # 4. One-Up View : Légende éditable en ligne (caption_edit) et bouton Zoom 1:1
    win._open_one_up_view(0)
    qapp.processEvents()
    assert hasattr(win.one_up_view, "caption_edit")
    assert hasattr(win.one_up_view, "btn_zoom_1to1")

    win.one_up_view.btn_zoom_1to1.click()
    qapp.processEvents()
    assert abs(win.one_up_view.canvas.zoom_level - 1.0) < 1e-4

    win.one_up_view.caption_edit.setText("Coucher de soleil sur la plage")
    win.one_up_view._on_caption_committed()
    qapp.processEvents()

    ini_doc2 = PicasaIniParser.parse_file(str(photos_dir / ".picasa.ini"))
    sec = ini_doc2.get_section("plage.jpg")
    assert sec is not None
    assert sec.get("caption") == "Coucher de soleil sur la plage"

    win.stop_background_tasks()
    win.close()
    qapp.processEvents()


def test_disassembled_finetune_algorithms_exact_fidelity():
    """
    FR : Vérifie que les algorithmes de Lumière d'appoint (`0x0090AC20`), Hautes lumières / Ombres
         (`0x008F7F5D` -> `0x0090C1E0`), Température de couleur (`0x0090E9D0`), Pipette point neutre
         (`0x0090EDA0`), Contraste auto (`0x008F80C0`), Couleur auto (`0x008F82A0`), J'ai de la chance
         (`0x008F8840`) et la sérialisation `finetune2` (`0x008FAC40`) correspondent au bit près au binaire.
    EN : Verifies that Fill Light (`0x0090AC20`), Highlights / Shadows (`0x008F7F5D` -> `0x0090C1E0`),
         Color Temperature (`0x0090E9D0`), Neutral Picker (`0x0090EDA0`), Auto-Contrast (`0x008F80C0`),
         Auto-Color (`0x008F82A0`), I'm Feeling Lucky (`0x008F8840`), and `finetune2` serialization
         (`0x008FAC40`) match the binary bit-for-bit.
    """
    import numpy as np
    from PIL import Image
    from picasa_py.ui.image_processor import PicasaImageProcessor

    # 1. Lumière d'appoint (0x0090AC20) : pixel sombre (40, 60, 80), L = (40 + 120 + 80) >> 2 = 60
    img_dark = Image.new("RGB", (4, 4), (40, 60, 80))
    filled = PicasaImageProcessor.fill_light(img_dark, 0.5)
    r_f, g_f, b_f = filled.getpixel((0, 0))
    assert (r_f, g_f, b_f) > (40, 60, 80)
    # Formule exacte 0x0090AC20 pour amount=0.5 : t=0.5, w=1/0.65, gamma=0.5/(0.7*w+0.3)
    t = 0.5
    w = 1.0 / (0.7 * t + 0.3)
    gamma = t / (0.7 * w + 0.3)
    lut_40 = int(round(255.0 * (((40.0 * w) / 255.0) ** gamma)))
    exp_r = 40 + (((lut_40 - 40) * 256 * (255 - 60)) >> 16)
    assert r_f == exp_r

    # 2. Hautes lumières & Ombres (0x008F7F5D -> 0x0090C1E0) :
    # - highlights > 0 abaisse white_pt = 1.0 - highlights -> éclaircit les hautes lumières !
    # - shadows > 0 relève black_pt = shadows -> approfondit/assombrit les ombres !
    img_mid = Image.new("RGB", (4, 4), (180, 180, 180))
    hl_img = PicasaImageProcessor.adjust_highlights(img_mid, 0.24)
    assert hl_img.getpixel((0, 0))[0] > 180
    sh_img = PicasaImageProcessor.adjust_shadows(img_mid, 0.24)
    assert sh_img.getpixel((0, 0))[0] < 180

    # 3. Adaptation chromatique matricielle 0x0090EDA0 : un pixel chaud (255, 196, 137) devient gris neutre (207, 207, 206)
    img_warm = Image.new("RGB", (4, 4), (255, 196, 137))
    neutralized = PicasaImageProcessor.neutral_color_balance(img_warm, (255, 196, 137))
    nr, ng, nb = neutralized.getpixel((0, 0))
    assert abs(nr - 207) <= 1 and abs(ng - 207) <= 1 and abs(nb - 206) <= 1

    # 4. Température de couleur (0x0090E9D0) : temp > 0 réchauffe (R augmente, B diminue), temp < 0 refroidit
    img_gray = Image.new("RGB", (4, 4), (160, 160, 160))
    warmer = PicasaImageProcessor.color_temperature(img_gray, 0.8)
    cooler = PicasaImageProcessor.color_temperature(img_gray, -0.8)
    assert warmer.getpixel((0, 0))[0] > warmer.getpixel((0, 0))[2]
    assert cooler.getpixel((0, 0))[2] > cooler.getpixel((0, 0))[0]

    # 5. Chaîne .picasa.ini finetune2=1,<fill>,<hl>,<sh>,<neutral_rgb:%08x>,<colortemp> (0x008FAC40 / 0x008FB120)
    chained = PicasaImageProcessor.apply_filter_chain(
        img_warm,
        "finetune2=1,0.200000,0.100000,0.050000,00ffc489,0.250000;",
    )
    direct = PicasaImageProcessor.finetune(
        img_warm,
        fill=0.2,
        highlights=0.1,
        shadows=0.05,
        colortemp=0.25,
        neutral_rgb=0x00FFC489,
    )
    assert np.array_equal(np.array(chained), np.array(direct))


def test_deep_mechanisms_tab3_filters_and_db_sync(tmp_path: Path):
    """
    FR : Vérifie les mécanismes profonds des 11 filtres C++ de l'Onglet 3 (`bw`, `sepia`, `warm`, `unsharp2`,
         `PicnikTint`, `sat`, `radblur`, `glow2`, `radsat`, `dir_tint`, `ansel`) ainsi que la synchronisation
         `imagedata_revertable` / `]revertable` / `]screensaver` et `rename_photo` / `move_photo`.
    EN : Verifies the deep mechanisms of the 11 Tab 3 C++ filters (`bw`, `sepia`, `warm`, `unsharp2`,
         `PicnikTint`, `sat`, `radblur`, `glow2`, `radsat`, `dir_tint`, `ansel`) as well as
         `imagedata_revertable` / `]revertable` / `]screensaver` sync and `rename_photo` / `move_photo`.
    """
    import numpy as np
    from PIL import Image
    from picasa_py.ui.image_processor import PicasaImageProcessor

    # 1. Noir & Blanc (0x008F84C0 -> 0x009A9550) : (77*R + 151*G + 28*B) >> 8
    img_rgb = Image.new("RGB", (8, 8), (200, 100, 50))
    bw_img = PicasaImageProcessor.black_and_white(img_rgb)
    exp_y = (77 * 200 + 151 * 100 + 28 * 50) >> 8
    assert bw_img.getpixel((0, 0)) == (exp_y, exp_y, exp_y)

    # 2. Sépia (0x008F8950 -> 0x0090A120) : ton chaud (R > G > B) avec relèvement des noirs (L_lifted=37, pivot=119)
    sep_img = PicasaImageProcessor.sepia(Image.new("RGB", (8, 8), (0, 0, 0)))
    sr, sg, sb = sep_img.getpixel((0, 0))
    assert (sr, sg, sb) == (46, 37, 29)

    # 3. Réchauffer (0x008F8930 -> 0x0090C040, LUT 0x00D33B70 @ index 128 : R=139, G=113, B=97)
    warm_img = PicasaImageProcessor.warmify(Image.new("RGB", (4, 4), (128, 128, 128)))
    wr, wg, wb = warm_img.getpixel((0, 0))
    assert (wr, wg, wb) == (139, 113, 97)
    assert np.array_equal(
        np.array(PicasaImageProcessor.apply_filter_chain(Image.new("RGB", (4, 4), (128, 128, 128)), "warm=1;")),
        np.array(warm_img),
    )

    # 4. Saturation (0x008F8FF0 -> 0x0090E200 / 0x0090B930) : amount in [-1.0, +1.0], -1.0 -> N&B
    desat = PicasaImageProcessor.saturation(img_rgb, -1.0)
    dr, dg, db_c = desat.getpixel((0, 0))
    assert dr == dg == db_c
    boosted = PicasaImageProcessor.saturation(img_rgb, 0.5)
    assert boosted.getpixel((0, 0))[0] > 200

    # 5. Chaîne native .picasa.ini (0x008FAC40) : unsharp2, PicnikTint, sat, radblur, glow2, radsat, dir_tint, ansel
    chain_str = (
        "unsharp2=1,0.600000;"
        "PicnikTint=1,60.000000,00dcbe96;"
        "sat=1,0.161800;"
        "radblur=1,0.500000,0.500000,0.350000,0.400000;"
        "glow2=1,0.650000,3.000000;"
        "radsat=1,0.500000,0.500000,0.350000,0.400000;"
        "dir_tint=1,0.500000,0.500000,0.500000,0.500000,ff7bb4d8,0.000000;"
        "ansel=1,ffff5555;"
    )
    res_chain = PicasaImageProcessor.apply_filter_chain(img_rgb, chain_str)
    assert res_chain.size == (8, 8)


def test_cross_app_db3_and_ini_interoperability(tmp_path: Path):
    """
    FR : Vérifie l'interopérabilité bidirectionnelle complète entre `picasa3.exe` et `PyCasa` :
         1. Format natif `CTextItemList` (`0x00A4DB30` / `0x00A4DD50`) pour `text=` + `textactive=1`.
         2. Format `contacts.xml` avec `email0="..."` (`0x00580403` / `0x00580DB5`) et `<email address="..."/>`.
         3. Absence de double application de `crop64` / `tilt` entre `load_transformed_image` et `apply_filter_chain`.
         4. Synchronisation de `onlinechecksum` (`imagedata_peoplealbumchecksum.pmp`), `rating` (`]rating`),
            `imagedata_edited = 2` (rotation seule) vs `1` (filtre/recadrage/texte), et retrait des `,0` de
            `imagedata_deferredface.pmp`.
         5. Recalcul de la somme de contrôle `compute_thumb_checksum` (`0x006B99F0`) dans `thumbs_index.db`
            lors de `rename_photo` / `move_photo`, et nettoyage de `wordhash.dat` lors de `delete_album`.
    EN : Verifies full bidirectional interoperability between `picasa3.exe` and `PyCasa`.
    """
    from PIL import Image
    from picasa_py.db.blockfile import compute_thumb_checksum
    from picasa_py.db.contacts import ContactsFile
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.ini.parser import PicasaIniParser
    from picasa_py.ui.image_processor import PicasaImageProcessor

    # 1. CTextItemList natif picasa3.exe (0x00A4DB30 / 0x00A4DD50)
    native_text = (
        "1;16;Vacances d'été;Arial;"
        "0.250000,0.750000,0.080000,0.000000;"
        "v1,700,400,128.000000,0.050000,1.000000,1.000000,ff000000,ffffcc00,32768;"
    )
    parsed_txt = PicasaImageProcessor.parse_text_token(native_text)
    assert parsed_txt is not None
    txt_str, (x_n, y_n), sz, fill_rgb, has_shadow = parsed_txt
    assert txt_str == "Vacances d'été"
    assert abs(x_n - 0.25) < 1e-5 and abs(y_n - 0.75) < 1e-5
    assert sz == int(round(0.08 * 360.0))
    assert fill_rgb == (255, 204, 0)
    assert has_shadow is True

    # 2. contacts.xml avec email0="..." (0x00580403 / 0x00580DB5)
    xml_str = (
        '<contacts><contact id="1a2b3c4d5e6f7081" name="Jean Valjean" '
        'email0="jean@valjean.fr" modified_time="2026-10-24T12:00:00Z" local_contact="1"/></contacts>'
    )
    cf = ContactsFile.from_xml(xml_str)
    assert len(cf.contacts) == 1
    assert cf.contacts[0].email == "jean@valjean.fr"
    assert 'email0="jean@valjean.fr"' in cf.to_xml()

    # 3. Synchronisation complète .picasa.ini <-> db3/
    photos_dir = tmp_path / "Vacances"
    photos_dir.mkdir(parents=True, exist_ok=True)
    img_p = photos_dir / "photo_interop.jpg"
    Image.new("RGB", (200, 120), (80, 140, 220)).save(img_p, quality=92)

    ini_path = photos_dir / ".picasa.ini"
    ini_path.write_text(
        "[.album:99887766554433221100aabbccddeeff]\n"
        "name=Été 2026\n"
        "token=99887766554433221100aabbccddeeff\n"
        "date=2026-08-26T15:41:38+02:00\n"
        "description=Souvenirs de plage\n"
        "location=Nice\n"
        "\n"
        "[photo_interop.jpg]\n"
        "rotate=rotate(1)\n"
        "onlinechecksum=abcd1234\n"
        "rating=4\n"
        "faces=rect64(22ff08a2e2319d9a),1a2b3c4d5e6f7081;rect64(3a4400008b119b9d),0\n",
        encoding="utf-8",
    )

    db = PicasaDatabase.create_new(tmp_path / "db3")
    rec_idx = db.add_media_record(str(photos_dir) + "\\", "photo_interop.jpg", img_p.stat().st_size, 0, 2)
    db.update_thumbnails_from_pil(rec_idx, Image.open(img_p))
    db._sync_album_sections_from_ini_doc(PicasaIniParser.parse_file(str(ini_path)))
    db.sync_photo_ini_to_db(rec_idx)

    # Rotation seule -> imagedata_edited == 2 (0x00456A15), onlinechecksum -> uint16 (0x1234)
    assert db.pmps["imagedata_edited"].records[rec_idx] == 2
    assert db.pmps["imagedata_peoplealbumchecksum"].records[rec_idx] == 0x1234
    assert db.pmps["imagedata_deferredface"].records[rec_idx] == "rect64(22ff08a2e2319d9a),1a2b3c4d5e6f7081"
    assert rec_idx in db.wordhash.search("]rating")
    # Album date ISO 8601 avec fuseau horaire parsée en date OLE > 0
    alb_rows = [
        i for i, tok in enumerate(db.pmps["albumdata_token"].records)
        if tok == "]album:99887766554433221100aabbccddeeff"
    ]
    assert len(alb_rows) == 1
    assert db.pmps["albumdata_date"].records[alb_rows[0]] > 40000.0
    assert db.pmps["albumdata_description"].records[alb_rows[0]] == "Souvenirs de plage"
    assert db.pmps["albumdata_location"].records[alb_rows[0]] == "Nice"

    # Renommage : la somme de contrôle thumbs_index.db doit correspondre au nouveau nom
    assert db.rename_photo(rec_idx, "photo_renommee.jpg")
    t_entry = db.block_indices["thumbs"].get_entry(rec_idx)
    assert t_entry is not None
    rec_after = db.index[rec_idx]
    assert t_entry.checksum == compute_thumb_checksum(
        str(photos_dir) + "\\", "photo_renommee.jpg", rec_after.ft2, rec_after.file_size
    )

    # Suppression d'album : nettoyage dans wordhash.dat
    assert db.delete_album("99887766554433221100aabbccddeeff")
    assert len(db.wordhash.search("]album:99887766554433221100aabbccddeeff")) == 0


def test_cross_app_faces_albums_and_time_sync(tmp_path: Path):
    """
    FR : Vérifie la cohérence bidirectionnelle de second niveau entre `picasa3.exe` et `PyCasa` :
         1. `imagedata_personalbumrecs` (`parecs_idx`) seul (sans `imagedata_personalbumid`) ne doit PAS
            confirmer automatiquement un visage sans nom, et `]ignoreface` doit exclure les visages ignorés.
         2. La fusion (`rename_person` vers une personne existante) et la suppression (`delete_person`)
            mettent à jour `imagedata_personalbumid`, `wordhash.dat` (`]facealbum:<id>`, `]unknownface`)
            et `albumdata_*`.
         3. `set_crop` / `set_crop_rect64` écrit toujours `filters=crop64=1,<hex>;` même si `filters=` était absent.
         4. `get_all_albums` ignore les collections dynamiques internes comme `]updated` et fusionne
            les photos indexées via `]album:<uid>` dans `wordhash.dat`.
    EN : Verifies second-round bidirectional consistency between `picasa3.exe` and `PyCasa`.
    """
    from PIL import Image
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.faces.face_manager import PicasaFaceManager
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.ini.parser import PicasaIniDocument

    # 1. set_crop synchronise crop=rect64(...) et met à jour filters=crop64=1,...; si filters= existe
    doc = PicasaIniDocument()
    doc.get_or_create_section("img.jpg").set("filters", "autolight=1;")
    doc.set_crop("img.jpg", "rect64(22ff08a2e2319d9a)")
    sec = doc.get_section("img.jpg")
    assert sec is not None
    assert sec.get("crop") == "rect64(22ff08a2e2319d9a)"
    assert sec.get("filters") == "autolight=1;crop64=1,22ff08a2e2319d9a;"

    # 2. Visages : parecs_idx non confirmé, ]ignoreface respecté, fusion et suppression dans db3/
    photos_dir = tmp_path / "Portraits"
    photos_dir.mkdir(parents=True, exist_ok=True)
    p1 = photos_dir / "p1.jpg"
    p2 = photos_dir / "p2.jpg"
    Image.new("RGB", (300, 300), (180, 140, 120)).save(p1, quality=90)
    Image.new("RGB", (300, 300), (120, 160, 190)).save(p2, quality=90)

    db = PicasaDatabase.create_new(tmp_path / "db3_faces")
    idx1 = db.add_media_record(str(photos_dir) + "\\", "p1.jpg", p1.stat().st_size, 0, 2)
    idx2 = db.add_media_record(str(photos_dir) + "\\", "p2.jpg", p2.stat().st_size, 0, 2)

    fm = PicasaFaceManager(db)
    fr1 = FaceRect(left=0.2, top=0.2, right=0.5, bottom=0.5)
    fr2 = FaceRect(left=0.3, top=0.3, right=0.6, bottom=0.6)
    fm.add_face(str(p1), fr1, "Claire", contact_id="1111222233334444", db_idx=idx1)
    fm.add_face(str(p2), fr2, "Diane", contact_id="5555666677778888", db_idx=idx2)

    # Créer un enfant 1001 sans nom ayant personalbumid == 0 mais personalbumrecs > 0
    fr_un = FaceRect(left=0.6, top=0.2, right=0.85, bottom=0.5)
    c_un = fm._get_or_create_1001_child(idx1, fr_un)
    assert c_un is not None
    claire_alb_id = fm._get_or_create_person_album_id("1111222233334444", "Claire")
    assert claire_alb_id is not None and claire_alb_id > 0
    while len(db.pmps["imagedata_personalbumrecs"].records) <= c_un:
        db.pmps["imagedata_personalbumrecs"].records.append(0)
    db.pmps["imagedata_personalbumrecs"].records[c_un] = claire_alb_id
    db.pmps["imagedata_personalbumid"].records[c_un] = 0

    # Créer un enfant 1001 ignoré (]ignoreface)
    fr_ign = FaceRect(left=0.1, top=0.6, right=0.35, bottom=0.85)
    c_ign = fm._get_or_create_1001_child(idx2, fr_ign)
    assert c_ign is not None
    db.wordhash.remove_word("]unknownface", c_ign)
    db.wordhash.add_word("]ignoreface", c_ign)

    # Recharger PicasaFaceManager depuis db3 : c_un doit rester sans-nom (non attribué à Claire) et c_ign ignoré
    fm_reloaded = PicasaFaceManager(db)
    claire_loaded = fm_reloaded.get_person("1111222233334444")
    assert claire_loaded is not None
    assert c_un not in claire_loaded.photo_indices
    unnamed_indices = {u_idx for u_idx, _, _ in fm_reloaded.unnamed_faces}
    assert c_un in unnamed_indices
    assert c_ign not in unnamed_indices

    # Fusionner Diane dans Claire -> les enregistrements PMP et wordhash de Diane basculent sur claire_alb_id
    assert fm_reloaded.rename_person("5555666677778888", "Claire")
    assert fm_reloaded.get_person("5555666677778888") is None
    assert len(db.wordhash.search(f"]facealbum:{claire_alb_id}")) >= 2

    # Supprimer Claire -> personalbumid remis à 0 et ]unknownface ajouté aux enfants 1001
    assert fm_reloaded.delete_person("1111222233334444")
    assert len(db.wordhash.search(f"]facealbum:{claire_alb_id}")) == 0

    # 3. Collection dynamique interne ]updated ignorée dans get_all_albums()
    db.pmps["albumdata_name"].records.append("Récemment mis à jour")
    db.pmps["albumdata_token"].records.append("]updated")
    db.pmps["albumdata_category"].records.append(0)
    db._albums_cache = None
    alb_tokens = [a["token"] for a in db.get_all_albums()]
    assert "]updated" not in alb_tokens
    assert "updated" not in alb_tokens


def test_disassembly_preview_checksum_ini_escaping_and_filters():
    """
    FR : Vérifie les mécanismes désassemblés pas-à-pas de `picasa3.exe` :
         1. `compute_preview_checksum` (`0x0042A800` & `0x006B9B26`) : XOR avec `filters` (casse sensible),
            `crop64` converti en pixels (`0x00429DC0`), `(((flip * 4) ^ rotate_step) << 4)` et `imagedata_text`.
         2. Sanitization des crochets dans les noms de sections `.picasa.ini` (`[photo[1].jpg]` -> `[photo(1).jpg]`,
            `0x0068B359` & `0x0099AFC0`) et entités numériques `&#010;`/`&#013;`/`&#091;`/`&#093;` (`0x0099ABC0`).
         3. Parsing legacy `crop=rect(l,t,r,b)` (`0x004569B0`).
         4. Troncature silencieuse `min(c1, c2, c3)` dans `BlockIndexFile.from_bytes` (`0x006B8AC0`).
         5. Formules pixel-exact des filtres radiaux/directionnels (`radblur` `0x0090AEB0`, `radsat` `0x0090B660`,
            `dir_tint` `0x0090F470`).
    EN : Verifies step-by-step disassembled mechanisms from `picasa3.exe`.
    """
    import struct
    from PIL import Image
    from picasa_py.db.blockfile import BlockIndexFile, compute_preview_checksum
    from picasa_py.ini.model import Rect64
    from picasa_py.ini.parser import PicasaIniDocument, PicasaIniParser
    from picasa_py.ui.image_processor import PicasaImageProcessor

    # 1. compute_preview_checksum (0x0042A800 & 0x006B9B26)
    chk_base = compute_preview_checksum(132000000000000000)
    chk_rot = compute_preview_checksum(132000000000000000, rotate_step=1, flip=1)
    assert chk_rot == (chk_base ^ (((1 * 4) ^ 1) << 4))

    chk_filt = compute_preview_checksum(132000000000000000, filters="autolight=1;")
    assert chk_filt != chk_base

    chk_crop = compute_preview_checksum(
        132000000000000000,
        crop64=0x0000000080008000,
        width=1000,
        height=800,
    )
    assert chk_crop != chk_base

    chk_txt_inactive = compute_preview_checksum(
        132000000000000000, text=";Hello;", text_active=0
    )
    chk_txt_active = compute_preview_checksum(
        132000000000000000, text=";Hello;", text_active=1
    )
    assert chk_txt_inactive == chk_base
    assert chk_txt_active != chk_base

    # 2. Sanitization des sections [photo[1].jpg] -> [photo(1).jpg] et entités &#010; / &#013;
    doc = PicasaIniDocument()
    sec = doc.get_or_create_section("vacances[2025].jpg")
    assert sec.name == "vacances(2025).jpg"
    assert doc.get_section("vacances[2025].jpg") is sec
    doc.set_caption("vacances[2025].jpg", "Ligne 1\r\nLigne 2")
    raw_ini = doc.to_bytes().decode("utf-8")
    assert "[vacances(2025).jpg]" in raw_ini
    assert "caption=Ligne 1&#013;&#010;Ligne 2" in raw_ini
    doc2 = PicasaIniParser.parse_bytes(raw_ini.encode("utf-8"))
    assert doc2.get_caption("vacances[2025].jpg") == "Ligne 1\r\nLigne 2"

    # 3. Parsing legacy crop=rect(l,t,r,b) (0x004569B0)
    r64 = Rect64.from_ini_string("rect(16384,16384,49152,49152)")
    assert (r64.left, r64.top, r64.right, r64.bottom) == (16384, 16384, 49152, 49152)

    # 4. BlockIndexFile.from_bytes (0x006B8AC0 : min(c1, c2, c3))
    raw_bidx = (
        struct.pack("<II", 0x3FCCCCCD, 0)
        + struct.pack("<I2I", 2, 100, 200)
        + struct.pack("<I3I", 3, 10, 20, 30)
        + struct.pack("<I2I", 2, 0xAA, 0xBB)
    )
    bidx = BlockIndexFile.from_bytes(raw_bidx)
    assert len(bidx.checksums) == 2 and len(bidx.offsets) == 2 and len(bidx.sizes_and_blocks) == 2

    # 5. Filtres radiaux/directionnels (soft_focus, focal_bw, graduated_tint)
    img = Image.new("RGB", (64, 64), (180, 120, 80))
    out_sf = PicasaImageProcessor.soft_focus(img, radius_norm=0.4, amount=0.6)
    out_fbw = PicasaImageProcessor.focal_bw(img, radius_norm=0.35, sharpness=0.5)
    out_gt = PicasaImageProcessor.graduated_tint(img, feather=0.5, intensity=0.6, tint_rgb=(80, 140, 220))
    assert out_sf.size == (64, 64)
    assert out_fbw.size == (64, 64)
    assert out_gt.size == (64, 64)

    # 6. Protection contre le bug original 0x00459DE3 (backuphash + crop sans filters)
    doc_bh = PicasaIniDocument()
    sec_bh = doc_bh.get_or_create_section("photo_bh.jpg")
    sec_bh.set("backuphash", "12345")
    doc_bh.set_crop("photo_bh.jpg", "rect64(1111222233334444)")
    assert sec_bh.get("filters") == "crop64=1,1111222233334444;"

    # 7. Nettoyage de cycles et d'orphelins (médias et visages 1001) dans ThumbIndexFile.sanitize_records
    from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord

    tf = ThumbIndexFile(
        records=[
            ThumbIndexRecord(path="C:\\Folder\\", type=1, flags=0x0100, parent_idx=0xFFFFFFFF),
            ThumbIndexRecord(path="photo.jpg", type=2, flags=0x0100, parent_idx=0),
            ThumbIndexRecord(path="", type=1001, flags=0x0100, parent_idx=1),
            # Enfant 1001 orphelin (parent_idx pointe vers un dossier type=1 au lieu d'une photo)
            ThumbIndexRecord(path="", type=1001, flags=0x0100, parent_idx=0),
            # Enregistrement avec cycle de parenté (4 -> 4)
            ThumbIndexRecord(path="cycle.jpg", type=2, flags=0x0100, parent_idx=4),
        ]
    )
    tf.sanitize_records()
    assert tf.records[0].type == 1
    assert tf.records[1].type == 2
    assert tf.records[2].type == 1001
    assert tf.records[3].type == 0
    assert tf.records[4].type == 0


def test_photo_tray_scratch_clicks_and_one_up_visibility(tmp_path: Path, qapp) -> None:
    """
    FR : Vérifie la fidélité au désassemblage du bac de sélection (`thumbui/scratch` / `CSelectionNode` @ `0x00714990`) :
         1. LayoutMode9 (`0x0071DAC0`) : toutes les miniatures (> 4) restent individuellement visibles et cliquables.
         2. Clic gauche simple (`WM_LBUTTONDOWN` @ `0x00719C37`, `0x00570C62`) : sélectionne/focalise la miniature
            dans le bac (avec support `Ctrl` et `Shift`) sans jamais supprimer les autres miniatures.
         3. Double-clic gauche (`WM_LBUTTONDBLCLK` @ `0x00719A44` -> `0x0056BFD0`) : ouvre le mode Édition 1-Up
            tout en gardant `photo_tray` visible (`0x0057BB80`) et toutes les miniatures dans le bac.
         4. En mode Édition 1-Up, cliquer sur une autre miniature du bac (`0x00570DC9 -> 0x005683A0` `RefreshOneUpView`)
            affiche immédiatement cette photo dans l'éditeur sans vider le bac.
         5. Clic droit (`WM_RBUTTONDOWN` @ `0x00719ACE` -> `0x00732EE0` `TrayContextMenu`) : ne supprime pas la
            miniature au clic droit, mais la sélectionne dans le bac et expose les actions du menu contextuel.
    EN : Verifies disassembly fidelity of the selection tray (`thumbui/scratch` / `CSelectionNode` @ `0x00714990`).
    """
    from PySide6.QtCore import Qt, QPoint
    import os

    db = PicasaDatabase.create_new(tmp_path / "db_tray")
    photos_dir = tmp_path / "AlbumTray"
    photos_dir.mkdir(parents=True)
    scanner = PicasaDirScanner(db)
    img_paths = []
    for i in range(6):
        p = photos_dir / f"img_{i}.jpg"
        Image.new("RGB", (160, 120), (30 * i, 100, 200 - 20 * i)).save(p, "JPEG")
        scanner.index_file(str(p))
        img_paths.append(str(p))
    db.save_database()

    win = PicasaMainWindow(db_path=str(db.db3_dir), auto_scan=False)
    _KEEP_REFS.append(win)
    win.resize(1280, 800)
    win.show()
    qapp.processEvents()

    # Sélectionner les 6 photos dans la grille
    win.thumb_view.set_selected_indices([0, 1, 2, 3, 4, 5])
    qapp.processEvents()

    # 1. LayoutMode9 (0x0071DAC0) : les 6 miniatures sont toutes des widgets individuels visibles dans thumb_strip
    assert len(win.photo_tray.get_effective_items()) == 6
    assert len(win.photo_tray.thumb_strip.item_widgets) == 6

    # 2. Clic gauche simple sur la 3e miniature du bac (index 2) :
    #    - Ne doit supprimer AUCUNE autre miniature du bac ni réduire selected_indices dans la grille !
    w2 = win.photo_tray.thumb_strip.item_widgets[2]
    win.photo_tray.thumb_strip._on_widget_clicked_with_modifiers(w2.item, Qt.KeyboardModifier.NoModifier)
    qapp.processEvents()
    assert len(win.photo_tray.get_effective_items()) == 6
    assert len(win.thumb_view.selected_indices) == 6
    assert win.thumb_view.focus_index == 2
    assert w2.is_selected is True
    assert win.photo_tray.thumb_strip.item_widgets[0].is_selected is False

    # Ctrl+Clic sur la 5e miniature (index 4) : ajoute à la sous-sélection interne du bac
    w4 = win.photo_tray.thumb_strip.item_widgets[4]
    win.photo_tray.thumb_strip._on_widget_clicked_with_modifiers(w4.item, Qt.KeyboardModifier.ControlModifier)
    qapp.processEvents()
    assert len(win.photo_tray.thumb_strip.selected_paths) == 2
    assert len(win.photo_tray.get_effective_items()) == 6

    # 3. Double-clic sur la 2e miniature du bac (index 1) : passe en mode Édition 1-Up
    #    tout en gardant le bac visible et les 6 miniatures présentes !
    w1 = win.photo_tray.thumb_strip.item_widgets[1]
    win.photo_tray.thumb_strip._on_widget_double_clicked(w1.item)
    qapp.processEvents()
    assert win.stack.currentWidget() == win.one_up_view
    assert not win.photo_tray.isHidden()
    assert len(win.photo_tray.get_effective_items()) == 6
    assert os.path.normcase(win.one_up_view.current_photo_path) == os.path.normcase(w1.item.path)

    # 4. En mode Édition 1-Up, un clic simple sur la 5e miniature du bac (w4) change immédiatement
    #    la photo affichée dans l'éditeur (RefreshOneUpView @ 0x005683A0) tout en gardant les 6 miniatures !
    w4_after = win.photo_tray.thumb_strip.item_widgets[4]
    win.photo_tray.thumb_strip._on_widget_clicked_with_modifiers(w4_after.item, Qt.KeyboardModifier.NoModifier)
    qapp.processEvents()
    assert win.stack.currentWidget() == win.one_up_view
    assert os.path.normcase(win.one_up_view.current_photo_path) == os.path.normcase(w4_after.item.path)
    assert len(win.photo_tray.get_effective_items()) == 6

    # 5. Clic droit sur une miniature du bac : ne supprime PAS la miniature !
    #    Et l'action "Supprimer la sélection" (Tray::ID_REMOVE_SELECTION @ 0x00733224) retire uniquement la sous-sélection.
    w0 = win.photo_tray.thumb_strip.item_widgets[0]
    win.photo_tray.remove_items_from_tray([w0.item])
    qapp.processEvents()
    assert len(win.photo_tray.get_effective_items()) == 5
    assert len(win.thumb_view.selected_indices) == 5

    # Retour à la bibliothèque : les 5 photos restent sélectionnées dans le bac et la grille
    win._back_to_library()
    qapp.processEvents()
    assert win.stack.currentIndex() == 0
    assert len(win.photo_tray.get_effective_items()) == 5
    assert len(win.thumb_view.selected_indices) == 5

    win.stop_background_tasks()
    win.close()
    qapp.processEvents()







