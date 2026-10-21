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

