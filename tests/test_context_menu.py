"""FR: Tests unitaires pour les menus contextuels de Picasa 3 (PicasaContextMenuBuilder) et la barre de menus (PicasaMenuBuilder).
EN: Unit tests for Picasa 3 context menus (PicasaContextMenuBuilder) and menu bar (PicasaMenuBuilder).
Ref: picasa3.exe @ 0x0088C3EC (eMenu* hierarchy)
Ref: picasa3.exe @ 0x00CADB44 - 0x00CAE010 (Photo context menus)
Ref: picasa3.exe @ 0x00CAE090 - 0x00CAE2F0 (Folder context menus)
Ref: picasa3.exe @ 0x00CAE3C4 - 0x00CAE460 (Album context menus)
Ref: picasa3.exe @ 0x00CAF1B8 - 0x00CAF354 (People Album photo and album context menus)
"""

import os
from unittest.mock import MagicMock
import pytest
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow

from picasa_py.ui.context_menu import PicasaContextMenuBuilder
from picasa_py.ui.menu import PicasaMenuBuilder
from picasa_py.ui.resources import PicasaResourceManager


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def preserve_language():
    """FR: Sauvegarde et restaure la langue courante de PicasaResourceManager autour de chaque test.
    EN: Saves and restores the current PicasaResourceManager language around each test.
    """
    res = PicasaResourceManager.get()
    orig = res.get_current_language()
    yield
    res.set_language(orig or "fr")


def get_all_action_texts(menu):
    """FR: Récupère récursivement tous les textes d'actions d'un menu et de ses sous-menus.
    EN: Recursively retrieves all action texts from a menu and its submenus.
    """
    texts = []
    for act in menu.actions():
        t = act.text()
        if t:
            texts.append(t)
        if act.menu():
            texts.extend(get_all_action_texts(act.menu()))
    return texts


def test_photo_context_menu_normal_folder(qapp):
    """FR: Teste le menu contextuel d'une photo standard dans un dossier.
    EN: Tests the context menu of a standard photo in a folder.
    """
    # S'assurer d'être en anglais pour tester les libellés stables ou tester les deux
    PicasaResourceManager.get().set_language("enUS")
    widget = QWidget()
    mock_win = MagicMock()

    menu = PicasaContextMenuBuilder.build_photo_context_menu(
        parent=widget,
        photo_paths=["C:/Photos/image1.jpg"],
        is_in_album=False,
        main_win=mock_win,
        contact_id=None
    )
    assert menu is not None
    texts = get_all_action_texts(menu)

    # Doit contenir les actions standard du binaire picasa3.exe
    assert any("&View and Edit" in t for t in texts)
    assert any("&Add to Album" in t for t in texts)
    assert any("&Rotate Clockwise" in t for t in texts)
    assert any("Rotate &Counterclockwise" in t for t in texts)
    assert any("Add/Remove &Star" in t for t in texts)
    assert any("Undo all &Edits" in t for t in texts)
    assert any("&Open File" in t for t in texts)
    assert any("Locate on &Disk" in t for t in texts)
    assert any("Copy Full &Path" in t for t in texts)
    assert any("&Copy" in t for t in texts)
    assert any("Copy All &Effects" in t for t in texts)
    assert any("Paste All E&ffects" in t for t in texts)

    # Spécifique dossier
    assert any("&Move to New Folder..." in t for t in texts)
    assert any("&Split Folder Here..." in t for t in texts)

    assert any("Create &Movie..." in t for t in texts)
    assert any("&Rename..." in t for t in texts)
    assert any("&Delete from Disk..." in t for t in texts)
    assert any("Reset &Faces" in t for t in texts)
    assert any("Set as &Desktop..." in t for t in texts)
    assert any("Propert&ies" in t for t in texts)

    # Ne doit PAS contenir les actions de People Album ni de Virtual Album
    assert not any("&Remove from People Album" in t for t in texts)
    assert not any("&Remove from Album" in t for t in texts)
    assert not any("&Locate in Picasa" in t for t in texts)


def test_photo_context_menu_in_album(qapp):
    """FR: Teste le menu contextuel d'une photo dans un album virtuel.
    EN: Tests the context menu of a photo inside a virtual album.
    """
    PicasaResourceManager.get().set_language("enUS")
    widget = QWidget()
    mock_win = MagicMock()

    menu = PicasaContextMenuBuilder.build_photo_context_menu(
        parent=widget,
        photo_paths=["C:/Photos/image1.jpg"],
        is_in_album=True,
        main_win=mock_win,
        contact_id=None
    )
    assert menu is not None
    texts = get_all_action_texts(menu)

    # Doit contenir &Locate in Picasa et &Remove from Album au lieu de &Delete from Disk...
    assert any("&Locate in Picasa" in t for t in texts)
    assert any("&Remove from Album" in t for t in texts)
    assert not any("&Delete from Disk..." in t for t in texts)


def test_photo_context_menu_in_person_album(qapp):
    """FR: Teste le menu contextuel d'une photo de visage dans un album de personne (PplAlbumPhoto).
    EN: Tests the context menu of a face photo in a person album (PplAlbumPhoto).
    Ref: picasa3.exe @ 0x00CAF1B8, 0x00CAF244, 0x00CAF27C
    """
    PicasaResourceManager.get().set_language("enUS")
    widget = QWidget()
    mock_win = MagicMock()

    # Création d'un mock database avec face_manager
    mock_db = MagicMock()
    mock_person1 = MagicMock()
    mock_person1.contact_id = "p1"
    mock_person1.name = "Alice"
    mock_person2 = MagicMock()
    mock_person2.contact_id = "p2"
    mock_person2.name = "Bob"
    mock_db.face_manager.get_people.return_value = [mock_person1, mock_person2]

    menu = PicasaContextMenuBuilder.build_photo_context_menu(
        parent=widget,
        photo_paths=["C:/Photos/face1.jpg"],
        db=mock_db,
        is_in_album=False,
        main_win=mock_win,
        contact_id="p1"  # Actuellement Alice
    )
    assert menu is not None
    texts = get_all_action_texts(menu)

    # Doit contenir les actions spécifiques aux personnes
    assert any("&Move to People Album" in t for t in texts)
    assert any("Bob" in t for t in texts)  # Bob est dans le sous-menu
    assert any("Move to &New Person..." in t for t in texts)
    assert any("&Set as People Album Thumbnail" in t for t in texts)
    assert any("Create &Face Movie..." in t for t in texts)

    # ID_FILE_DELETEFROMDISK doit être "&Remove from People Album" et NON "&Delete from Disk..."
    assert any("&Remove from People Album" in t for t in texts)
    assert not any("&Delete from Disk..." in t for t in texts)

    # Trouver l'action &Remove from People Album et vérifier qu'elle appelle action_remove_from_person
    for act in menu.actions():
        if "&Remove from People Album" in act.text():
            act.trigger()
            mock_win.action_remove_from_person.assert_called_once()
            break


def test_folder_context_menu(qapp):
    """FR: Teste le menu contextuel d'un dossier.
    EN: Tests the context menu of a folder.
    Ref: picasa3.exe @ 0x007319F0, 0x00CAE090 - 0x00CAE2F0
    """
    PicasaResourceManager.get().set_language("enUS")
    widget = QWidget()
    mock_win = MagicMock()

    menu = PicasaContextMenuBuilder.build_folder_context_menu(
        parent=widget,
        folder_path="C:/Photos/Vacances",
        main_win=mock_win
    )
    texts = get_all_action_texts(menu)

    assert any("Play &Slideshow" in t for t in texts)
    assert any("&Edit Folder Description..." in t for t in texts)
    assert any("&Move Folder..." in t for t in texts)
    assert any("Select &All" in t for t in texts)
    assert any("Clear Selection" in t for t in texts)
    assert any("&Invert Selection" in t for t in texts)
    assert any("S&ort Folder By" in t for t in texts)
    assert any("Name" in t for t in texts)
    assert any("Date" in t for t in texts)
    assert any("Size" in t for t in texts)
    assert any("&Refresh Thumbnail" in t for t in texts)
    assert any("Locate on &Disk" in t for t in texts)
    assert any("&Folder Manager..." in t for t in texts)
    assert any("&Delete Folder..." in t for t in texts)
    assert any("Export as &Web Page..." in t for t in texts)

    # Tester le déclenchement de &Move Folder...
    for act in menu.actions():
        if "&Move Folder..." in act.text():
            act.trigger()
            mock_win.action_move_folder.assert_called_with("C:/Photos/Vacances")
            break


def test_album_context_menu(qapp):
    """FR: Teste le menu contextuel d'un album virtuel.
    EN: Tests the context menu of a virtual album.
    Ref: picasa3.exe @ 0x00732160, 0x00CAE3C4 - 0x00CAE460
    """
    PicasaResourceManager.get().set_language("enUS")
    widget = QWidget()
    mock_win = MagicMock()

    menu = PicasaContextMenuBuilder.build_album_context_menu(
        parent=widget,
        album_name="BestOf2024",
        main_win=mock_win
    )
    texts = get_all_action_texts(menu)

    assert any("Play &Slideshow" in t for t in texts)
    assert any("&Edit Album Description..." in t for t in texts)
    assert any("Select &All" in t for t in texts)
    assert any("Clear Selection" in t for t in texts)
    assert any("&Invert Selection" in t for t in texts)
    assert any("Sort &Album By" in t for t in texts)
    assert any("Name" in t for t in texts)
    assert any("Date" in t for t in texts)
    assert any("Size" in t for t in texts)
    assert any("&Refresh Thumbnail" in t for t in texts)
    assert any("&Delete Album..." in t for t in texts)
    assert any("Export as &Web Page..." in t for t in texts)


def test_person_context_menu(qapp):
    """FR: Teste le menu contextuel d'un contact / personne (PplAlbum).
    EN: Tests the context menu of a contact / person (PplAlbum).
    Ref: picasa3.exe @ 0x007359E0, 0x00CAF334 - 0x00CAF2B8
    """
    PicasaResourceManager.get().set_language("enUS")
    widget = QWidget()
    mock_win = MagicMock()

    menu = PicasaContextMenuBuilder.build_person_context_menu(
        parent=widget,
        contact_id="person_42",
        person_name="Jean Dupont",
        main_win=mock_win
    )
    texts = get_all_action_texts(menu)

    assert any("Play &Slideshow" in t for t in texts)
    assert any("Create &Face Movie..." in t for t in texts)
    assert any("&Edit Person..." in t for t in texts)
    assert any("Select &All" in t for t in texts)
    assert any("Clear Selection" in t for t in texts)
    assert any("&Delete Person..." in t for t in texts)


def test_main_menu_builder_wiring(qapp):
    """FR: Vérifie que la barre de menu principale (PicasaMenuBuilder) câble correctement
    toutes les actions vers la fenêtre principale.
    EN: Verifies that the main menu bar (PicasaMenuBuilder) properly wires
    all actions to the main window.
    """
    win = QMainWindow()
    # Attacher des mocks pour chaque action attendue
    win.action_add_file = MagicMock()
    win.action_folder_manager = MagicMock()
    win.action_import = MagicMock()
    win.action_new_album = MagicMock()
    win.action_save = MagicMock()
    win.action_save_as = MagicMock()
    win.action_save_a_copy = MagicMock()
    win.action_undo_all_edits = MagicMock()
    win.action_print = MagicMock()
    win.action_print_contact_sheet = MagicMock()
    win.action_export = MagicMock()
    win.action_rename = MagicMock()
    win.action_delete_from_disk = MagicMock()
    win.action_cut = MagicMock()
    win.action_copy = MagicMock()
    win.action_copy_all_effects = MagicMock()
    win.action_copy_path = MagicMock()
    win.action_paste = MagicMock()
    win.action_paste_all_effects = MagicMock()
    win.action_select_all = MagicMock()
    win.action_select_starred = MagicMock()
    win.action_invert_selection = MagicMock()
    win.action_clear_selection = MagicMock()
    win._back_to_library = MagicMock()
    win.action_slideshow = MagicMock()
    win.action_view_timeline = MagicMock()
    win.action_view_tree = MagicMock()
    win.action_view_flat_folders = MagicMock()
    win.action_toggle_drawer_panel = MagicMock()
    win.action_locate_on_disk = MagicMock()
    win.action_refresh_thumbnails = MagicMock()
    win.action_export_as_web_page = MagicMock()
    win.action_rotate_clockwise = MagicMock()
    win.action_rotate_counterclockwise = MagicMock()
    win.action_toggle_star = MagicMock()
    win.action_auto_contrast = MagicMock()
    win.action_auto_color = MagicMock()
    win.action_auto_redeye = MagicMock()
    win.action_properties = MagicMock()
    win.action_collage = MagicMock()
    win.action_poster = MagicMock()
    win.action_movie = MagicMock()
    win.action_set_desktop_wallpaper = MagicMock()
    win.action_set_screensaver = MagicMock()
    win.action_options = MagicMock()
    win.action_adjust_time = MagicMock()
    win.action_contact_manager = MagicMock()
    win.action_write_facetags = MagicMock()
    win.action_move_database = MagicMock()
    win.action_compact_database = MagicMock()
    win.action_about = MagicMock()
    win.action_keyboard_shortcuts = MagicMock()
    win.action_privacy_policy = MagicMock()
    win.action_help_contents = MagicMock()

    builder = PicasaMenuBuilder(win)
    mb = builder.build_menu_bar()

    # Vérifier que les 8 menus originaux sont présents
    top_menus = [act.text() for act in mb.actions()]
    assert len(top_menus) == 8

    # Tester le déclenchement de quelques actions clés
    all_actions = []
    for top_act in mb.actions():
        m = top_act.menu()
        if m:
            all_actions.extend(m.actions())

    for act in all_actions:
        if "Ctrl+O" in act.shortcut().toString():
            act.trigger()
            win.action_add_file.assert_called_once()
        elif "Ctrl+N" in act.shortcut().toString():
            act.trigger()
            win.action_new_album.assert_called_once()
        elif "Ctrl+T" in act.shortcut().toString():
            act.trigger()
            win.action_toggle_star.assert_called_once()
        elif "Ctrl+X" in act.shortcut().toString():
            act.trigger()
            win.action_cut.assert_called_once()


def test_context_menu_french_localization(qapp):
    """FR: Vérifie que les menus contextuels (photo, dossier, album, personne) sont bien traduits
    en français avec les libellés officiels de STRINGRES_FR.XML lorsque la langue est 'fr'.
    EN: Verifies that context menus (photo, folder, album, person) are properly localized
    in French using the official STRINGRES_FR.XML labels when language is 'fr'.
    Ref: picasa3.exe @ STRINGRES_FR.XML
    """
    PicasaResourceManager.get().set_language("fr")
    widget = QWidget()
    mock_win = MagicMock()

    # Photo menu
    menu_p = PicasaContextMenuBuilder.build_photo_context_menu(
        parent=widget,
        photo_paths=["C:/Photos/image1.jpg"],
        is_in_album=False,
        main_win=mock_win,
        contact_id=None
    )
    texts_p = get_all_action_texts(menu_p)
    assert any("&Afficher et modifier" in t for t in texts_p)
    assert any("&Ajouter à l'album" in t for t in texts_p)
    assert any("R&otation vers la droite" in t for t in texts_p)
    assert any("A&nnuler toutes les modifications" in t for t in texts_p)
    assert any("Rechercher sur le &disque" in t for t in texts_p)
    assert any("&Supprimer du disque" in t for t in texts_p)

    # Folder menu
    menu_f = PicasaContextMenuBuilder.build_folder_context_menu(
        parent=widget, folder_path="C:/Photos", main_win=mock_win
    )
    texts_f = get_all_action_texts(menu_f)
    assert any("Afficher le &diaporama" in t for t in texts_f)
    assert any("&Modifier la description du dossier..." in t for t in texts_f)
    assert any("&Tout sélectionner" in t for t in texts_f)
    assert any("Actualiser les &vignettes" in t for t in texts_f)
    assert any("Gestionnaire de &dossiers..." in t for t in texts_f)

    # Person menu
    menu_pe = PicasaContextMenuBuilder.build_person_context_menu(
        parent=widget, contact_id="p1", person_name="Marie", main_win=mock_win
    )
    texts_pe = get_all_action_texts(menu_pe)
    assert any("Afficher le &diaporama" in t for t in texts_pe)
    assert any("Créer un &film avec des visages..." in t for t in texts_pe)
    assert any("Modifi&er l'album dédié à la personne..." in t for t in texts_pe)
    assert any("&Supprimer l'album dédié à la personne" in t for t in texts_pe)


def test_move_face_to_person_live_refresh(qapp):
    """FR: Vérifie qu'un visage déplacé vers une autre personne (Move to People Album)
    est immédiatement retiré de l'album de la personne source dans l'interface.
    EN: Verifies that a face moved to another person (Move to People Album)
    is immediately removed from the source person's album in the UI.
    Ref: picasa3.exe @ PplAlbumPhoto::ID_PEOPLEALBUMS (0x00CAF244)
    """
    import tempfile
    import shutil
    from pathlib import Path
    from PIL import Image
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.ui.main_window import PicasaMainWindow

    td = tempfile.mkdtemp(prefix="pycasa_test_move_face_")
    try:
        photo1 = os.path.join(td, "photo1.jpg")
        img1 = Image.new("RGB", (640, 480), color=(100, 150, 200))
        img1.save(photo1)

        db_dir = os.path.join(td, "db3")
        contacts_dir = os.path.join(td, "contacts")
        os.makedirs(db_dir, exist_ok=True)
        os.makedirs(contacts_dir, exist_ok=True)

        win = PicasaMainWindow(db_path=db_dir)
        db = win.db
        db.contacts_dir = Path(contacts_dir)

        # Ajouter la photo dans la base
        db_idx = db.add_media_record(td + "\\", "photo1.jpg", 100, 10000, 2)

        # Créer deux personnes : Alice et Bob
        fm = db.face_manager
        p_alice = fm.create_person("Alice")
        p_bob = fm.create_person("Bob")

        # Assigner un visage à Alice sur photo1
        fr = FaceRect(left=0.1, top=0.1, right=0.4, bottom=0.4, contact_id=p_alice.contact_id)
        fm.add_face(photo1, fr, "Alice", db_idx=db_idx)

        assert photo1 in p_alice.photo_paths
        assert db_idx in p_alice.photo_indices

        # Afficher l'album d'Alice dans la vue
        win.thumb_view.filter_by_person(p_alice.contact_id, "Alice", p_alice.photo_indices)
        assert len(win.thumb_view.visible_sections) == 1
        assert len(win.thumb_view.visible_sections[0].item_indices) == 1

        # Déplacer le visage d'Alice vers Bob via action_move_face_to_person
        win.action_move_face_to_person(
            photo_path=photo1,
            face_rect=fr,
            target_contact_id=p_bob.contact_id,
            target_name="Bob",
            source_contact_id=p_alice.contact_id
        )

        # 1. Le cluster d'Alice ne doit plus contenir photo1
        assert photo1 not in p_alice.photo_paths
        assert db_idx not in p_alice.photo_indices

        # 2. Le cluster de Bob doit maintenant contenir photo1
        assert photo1 in p_bob.photo_paths
        assert db_idx in p_bob.photo_indices

        # 3. L'affichage de l'album d'Alice doit être immédiatement vide
        assert win.thumb_view.current_folder_filter == f"person:{p_alice.contact_id}"
        assert len(win.thumb_view.visible_sections[0].item_indices) == 0

        win.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_menu_album_folder_title_and_hidden_pictures(qapp):
    """
    FR: Vérifie que :
    - Le 5e menu s'appelle « &Photo » en FR (Ref: STRINGRES_FR.XML eMenuPicture) et non « &Image ».
    - Le 4e menu bascule dynamiquement entre « &Album » (vue globale / album / personne) et « &Dossier »
      (lorsqu'un dossier physique est sélectionné) (Ref: picasa3.exe @ 0x00537FB0).
    - Photo > Masquer (`ID_PICTURE_HIDE`), Photo > Afficher (`ID_PICTURE_UNHIDE`) et Affichage > Photos masquées
      (`ID_VIEW_SHOWHIDDEN`) fonctionnent et écrivent `hidden=yes` dans `.picasa.ini`.
    EN: Verifies dynamic Album/Folder 4th menu title, &Photo 5th menu title in FR, and Hide/Unhide/ShowHidden.
    """
    import tempfile
    import shutil
    from PIL import Image
    from picasa_py.ui.main_window import PicasaMainWindow
    from picasa_py.ui.resources import PicasaResourceManager
    from picasa_py.ini.parser import PicasaIniParser

    td = tempfile.mkdtemp(prefix="picasa_hidden_test_")
    rm = PicasaResourceManager.get()
    prev_lang = rm.get_current_language()
    try:
        rm.set_language("fr")
        photo1 = os.path.join(td, "photo1.jpg")
        Image.new("RGB", (120, 90), color=(80, 120, 160)).save(photo1)

        db_dir = os.path.join(td, "db3")
        os.makedirs(db_dir, exist_ok=True)
        win = PicasaMainWindow(db_path=db_dir)
        db = win.db
        db.add_media_record(td + "\\", "photo1.jpg", 100, 10000, 2)
        win.thumb_view.set_database(db)

        # Par défaut (aucun dossier sélectionné), le 4e menu est &Album et le 5e est &Photo
        top_titles = [act.text() for act in win.menuBar().actions()]
        assert top_titles[3] == "&Album"
        assert top_titles[4] == "&Photo"

        # Lorsqu'on sélectionne un dossier physique, le 4e menu passe à &Dossier
        win._on_folder_selected(td, "folder", "TestFolder")
        assert win.menu_builder.menu_folder.title() == "&Dossier"

        # Lorsqu'on sélectionne un album virtuel, le 4e menu repasse à &Album
        win._on_folder_selected("special_starred", "starred", "Photos favorites")
        assert win.menu_builder.menu_folder.title() == "&Album"
        win._on_folder_selected(td, "folder", "TestFolder")

        # Masquer photo1 via action_hide_pictures
        assert len(win.thumb_view.filtered_indices) == 1
        win.action_hide_pictures([photo1])
        ini_doc = PicasaIniParser.parse_file(os.path.join(td, ".picasa.ini"))
        assert ini_doc.get_section("photo1.jpg").get("hidden") == "yes"
        # ShowHidden est False par défaut -> la photo masquée n'est plus affichée
        assert len(win.thumb_view.filtered_indices) == 0

        # Basculer Affichage > Photos masquées (ID_VIEW_SHOWHIDDEN) -> la photo masquée réapparaît
        win.action_toggle_show_hidden(True)
        assert win.show_hidden_pictures is True
        assert win.menu_builder.act_show_hidden.isChecked() is True
        assert len(win.thumb_view.filtered_indices) == 1

        # Réafficher photo1 via action_unhide_pictures
        win.action_unhide_pictures([photo1])
        ini_doc2 = PicasaIniParser.parse_file(os.path.join(td, ".picasa.ini"))
        sec2 = ini_doc2.get_section("photo1.jpg")
        assert sec2 is None or sec2.get("hidden") is None
        win.action_toggle_show_hidden(False)
        assert len(win.thumb_view.filtered_indices) == 1

        # Vérifier l'enregistrement et la lecture du mot de passe de collection dans catdata_info.pmp
        win._set_collection_password_hash("Hidden Folders", "e10adc3949ba59abbe56e057f20f883e")
        assert win._get_collection_password_hash("Hidden Folders") == "e10adc3949ba59abbe56e057f20f883e"
        assert "catdata_info" in win.db.pmps
        assert os.path.exists(os.path.join(db_dir, "catdata_info.pmp"))

        # Vérifier le masquage et le réaffichage d'un dossier entier (Ref: 0x005EE2A0, 0x00446012)
        win.action_hide_folder(td)
        assert td.replace("\\", "/").rstrip("/").lower() in win.db._hidden_folders
        ini_folder_doc = PicasaIniParser.parse_file(os.path.join(td, ".picasa.ini"))
        assert ini_folder_doc.get_section("Picasa").get("P2category") == "Hidden Folders"
        assert len(win.thumb_view.filtered_indices) == 0

        # Basculer Affichage > Photos masquées (0x005C9300) NE demande PAS de mot de passe :
        # "Dossiers masqués" apparaît replié (verrouillé) tant que l'utilisateur ne le déplie pas (0x004AB9A0 -> 0x004AB650)
        win.action_toggle_show_hidden(True)
        assert win.library_tree.cat_hidden_folders.isHidden() is False
        assert win.library_tree.cat_hidden_folders.isExpanded() is False
        assert len(win.thumb_view.filtered_indices) == 0

        # Déverrouiller et déplier "Dossiers masqués" -> les photos du dossier masqué apparaissent
        win._unlocked_collections.add("Hidden Folders")
        win.library_tree.cat_hidden_folders.setExpanded(True)
        win.thumb_view._apply_current_filters(reset_scroll=False)
        assert len(win.thumb_view.filtered_indices) == 1

        # Replier "Dossiers masqués" reverrouille la collection (0x00453AF0)
        win.library_tree.cat_hidden_folders.setExpanded(False)
        assert "Hidden Folders" not in win._unlocked_collections
        assert len(win.thumb_view.filtered_indices) == 0

        win.action_unhide_folder(td)
        assert td.replace("\\", "/").rstrip("/").lower() not in win.db._hidden_folders
        ini_folder_doc2 = PicasaIniParser.parse_file(os.path.join(td, ".picasa.ini"))
        assert ini_folder_doc2.get_section("Picasa").get("P2category") == "Folders on Disk"
        assert len(win.thumb_view.filtered_indices) == 1

        win.stop_background_tasks()
        win.close()
    finally:
        rm.set_language(prev_lang)
        shutil.rmtree(td, ignore_errors=True)

