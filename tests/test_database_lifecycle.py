"""FR: Tests du cycle de vie des bases de données Picasa 3 :
- Création d'une nouvelle base de données vierge complète (PicasaDatabase.create_new)
- Ouverture d'une base existante via le dossier parent ou directement db3/ (PicasaDatabase.open)
- Bascule à chaud (hot-switch) dans PicasaMainWindow via Outils > Créer / Ouvrir une base de données.

EN: Picasa 3 database lifecycle tests:
- Creation of a complete blank database (PicasaDatabase.create_new)
- Opening an existing database via the parent folder or directly db3/ (PicasaDatabase.open)
- Hot-switching in PicasaMainWindow via Tools > Create / Open Database.

Ref: picasa3.exe @ 0x004156F0 (CThumbDB::Init), 0x006B6070 (CThumbDB::Open), 0x0088C3EC (eMenuTools)
"""

from __future__ import annotations
from pathlib import Path
from typing import List
from PIL import Image

from picasa_py.db.database import (
    PicasaDatabase,
    STANDARD_PMP_SCHEMA,
    STANDARD_BLOCKFILE_PREFIXES,
    DEFAULT_CATDATA_RECORDS,
)
from picasa_py.scanner.scanner import PicasaDirScanner
from picasa_py.ui.main_window import PicasaMainWindow

# Conserver les références aux fenêtres jusqu'au teardown global de conftest.py (QWebEngineView)
_KEEP_REFS: List[object] = []


def test_create_new_database_full_schema_and_reopen(tmp_path: Path) -> None:
    """FR: Vérifie que PicasaDatabase.create_new initialise sur disque l'intégralité des fichiers
    d'une base Picasa 3 vierge (thumbindex.db, wordhash.dat, repository.dat, usernames.dat,
    contacts/contacts.xml, 56 colonnes .pmp, 6 paires CBlockFile) et que PicasaDatabase.open
    accepte aussi bien le dossier parent que le sous-dossier db3/.
    EN: Verifies that PicasaDatabase.create_new initializes on disk all files of a blank
    Picasa 3 database (thumbindex.db, wordhash.dat, repository.dat, usernames.dat,
    contacts/contacts.xml, 56 .pmp columns, 6 CBlockFile pairs) and that PicasaDatabase.open
    accepts both the parent folder and the db3/ subfolder.
    """
    root_dir = tmp_path / "CustomPicasaDB"
    db = PicasaDatabase.create_new(root_dir)

    assert db.db3_dir == root_dir / "db3"
    assert db.contacts_dir == root_dir / "contacts"
    assert (db.db3_dir / "thumbindex.db").exists()
    assert (db.db3_dir / "wordhash.dat").exists()
    assert (db.db3_dir / "repository.dat").exists()
    assert (db.db3_dir / "usernames.dat").exists()
    assert (db.contacts_dir / "contacts.xml").exists()

    # Vérification des 56 colonnes .pmp et des 9 catégories par défaut
    for stem, expected_type in STANDARD_PMP_SCHEMA.items():
        pmp_path = db.db3_dir / f"{stem}.pmp"
        assert pmp_path.exists(), f"Colonne PMP manquante : {stem}.pmp"
        assert db.pmps[stem].pmp_type == expected_type

    for cat_col, expected_vals in DEFAULT_CATDATA_RECORDS.items():
        assert db.pmps[cat_col].records == expected_vals

    # Vérification des 6 paires CBlockFile (*_index.db et *_0.db)
    for prefix in STANDARD_BLOCKFILE_PREFIXES:
        assert (db.db3_dir / f"{prefix}_index.db").exists()
        assert (db.db3_dir / f"{prefix}_0.db").exists()
        assert prefix in db.block_indices
        assert prefix in db.block_containers

    # Réouverture via le dossier parent (contenant db3/ et contacts/)
    reopened_parent = PicasaDatabase.open(root_dir)
    assert reopened_parent.db3_dir == root_dir / "db3"
    assert reopened_parent.contacts_dir == root_dir / "contacts"
    assert len(reopened_parent.pmps) == len(STANDARD_PMP_SCHEMA)
    assert reopened_parent.pmps["catdata_name"].records == DEFAULT_CATDATA_RECORDS["catdata_name"]

    # Réouverture directement via le dossier db3/
    reopened_db3 = PicasaDatabase.open(root_dir / "db3")
    assert reopened_db3.db3_dir == root_dir / "db3"
    assert len(reopened_db3.pmps) == len(STANDARD_PMP_SCHEMA)


def test_tools_menu_contains_create_and_open_database_actions(qapp, tmp_path: Path) -> None:
    """FR: Vérifie que le menu Outils (&Tools) expose bien les actions ID_CREATE_DATABASE et ID_OPEN_DATABASE
    et que leurs callbacks basculent à chaud entre deux bases de données distinctes dans PicasaMainWindow.
    EN: Verifies that the Tools (&Tools) menu exposes the ID_CREATE_DATABASE and ID_OPEN_DATABASE actions
    and that their callbacks hot-switch between two distinct databases in PicasaMainWindow.
    """
    db_a_root = tmp_path / "db_alpha"
    db_b_root = tmp_path / "db_beta"

    # Préparer db_alpha avec 2 photos indexées
    photos_dir = tmp_path / "photos_alpha"
    photos_dir.mkdir(parents=True, exist_ok=True)
    for i in range(2):
        img = Image.new("RGB", (64, 48), color=(40 * i, 120, 200))
        img.save(photos_dir / f"alpha_{i}.jpg", "JPEG")

    db_a = PicasaDatabase.create_new(db_a_root)
    scanner = PicasaDirScanner(db_a)
    for i in range(2):
        scanner.index_file(str(photos_dir / f"alpha_{i}.jpg"))
    db_a.save_database()
    assert len([r for r in db_a.index if r.type == 2]) == 2

    win = PicasaMainWindow(db_path=str(db_a_root), auto_scan=False)
    _KEEP_REFS.append(win)
    try:
        # 1. Vérifier la présence des actions dans le menu Outils
        mb = win.menuBar()
        action_texts = []
        for menu_act in mb.actions():
            menu = menu_act.menu()
            if menu:
                for act in menu.actions():
                    if act.text():
                        action_texts.append(act.text())

        joined = " | ".join(action_texts).lower().replace("&", "")
        assert any(
            phrase in joined
            for phrase in (
                "créer une nouvelle base",
                "create new database",
                "crear una nueva base",
                "neue datenbank erstellen",
            )
        )
        assert any(
            phrase in joined
            for phrase in (
                "ouvrir une base",
                "open existing database",
                "abrir una base",
                "vorhandene datenbank öffnen",
            )
        )

        # Vérifier que db_alpha est initialement chargée avec ses 2 photos
        assert win.db is not None
        assert win.db.db3_dir == db_a_root / "db3"
        assert len(win.thumb_view.items) == 2

        # 2. Créer une nouvelle base vierge db_beta depuis Outils > Créer une nouvelle base de données
        created_db = win.action_create_database(str(db_b_root))
        qapp.processEvents()
        assert created_db is not None
        assert win.db is created_db
        assert win.db.db3_dir == db_b_root / "db3"
        assert len(win.thumb_view.items) == 0

        # 3. Rouvrir la base existante db_alpha depuis Outils > Ouvrir une base de données existante
        reopened_db = win.action_open_database(str(db_a_root))
        qapp.processEvents()
        assert reopened_db is not None
        assert win.db is reopened_db
        assert win.db.db3_dir == db_a_root / "db3"
        assert len(win.thumb_view.items) == 2
    finally:
        win.stop_background_tasks()
        win.close()
        qapp.processEvents()


def test_database_selector_dialog_and_menu_trigger(qapp, tmp_path: Path, monkeypatch) -> None:
    """FR: Vérifie :
    1. Le dialogue PicasaDatabaseSelectorDialog en mode 'create' et 'open' (arborescence,
       diagnostic en temps réel, bouton Par défaut, validation).
    2. Le déclenchement direct via QAction.trigger() dans le menu Outils (qui passe checked=False)
       ouvre bien PicasaDatabaseSelectorDialog et bascule la base de données.
    EN: Verifies:
    1. PicasaDatabaseSelectorDialog in 'create' and 'open' modes (directory tree,
       real-time diagnostics, Default button, confirmation).
    2. Direct triggering via QAction.trigger() in the Tools menu (which passes checked=False)
       properly opens PicasaDatabaseSelectorDialog and switches the database.
    """
    from PySide6.QtWidgets import QDialog, QMessageBox
    from picasa_py.ui.move_database_dialog import PicasaDatabaseSelectorDialog

    existing_root = tmp_path / "existing_picasa_db"
    new_root = tmp_path / "new_picasa_db"
    db_existing = PicasaDatabase.create_new(existing_root)

    # 1. Test de PicasaDatabaseSelectorDialog en mode "open" sur une base existante
    dlg_open = PicasaDatabaseSelectorDialog(mode="open", current_db=db_existing)
    dlg_open.set_target_directory(str(existing_root))
    qapp.processEvents()
    assert "valide détectée" in dlg_open.lbl_status_box.text()
    dlg_open._on_confirm()
    assert dlg_open.selected_path == str(existing_root.resolve())
    dlg_open.close()

    # 2. Test de PicasaDatabaseSelectorDialog en mode "create" sur un dossier vierge
    dlg_create = PicasaDatabaseSelectorDialog(mode="create", current_db=db_existing)
    dlg_create.set_target_directory(str(new_root))
    qapp.processEvents()
    assert "prêt pour la création" in dlg_create.lbl_status_box.text()
    dlg_create._on_confirm()
    assert dlg_create.selected_path == str(new_root.resolve())
    dlg_create.close()

    # 3. Test du clic réel sur QAction dans le menu Outils (qui émet triggered(False))
    win = PicasaMainWindow(db_path=str(existing_root), auto_scan=False)
    _KEEP_REFS.append(win)
    try:
        monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

        def _fake_exec(self_dlg: PicasaDatabaseSelectorDialog) -> int:
            """FR: Simule la sélection et validation d'un nouveau répertoire dans le dialogue.
            EN: Simulates selecting and confirming a new directory in the dialog.
            """
            self_dlg.set_target_directory(str(new_root))
            self_dlg.chk_default.setChecked(False)
            self_dlg._on_confirm()
            return int(QDialog.DialogCode.Accepted)

        monkeypatch.setattr(PicasaDatabaseSelectorDialog, "exec", _fake_exec)

        # Trouver l'action ID_CREATE_DATABASE dans la barre de menu et appeler .trigger()
        create_action = None
        for menu_act in win.menuBar().actions():
            menu = menu_act.menu()
            if menu:
                for act in menu.actions():
                    txt = act.text().lower().replace("&", "")
                    if (
                        act.objectName() == "ID_CREATE_DATABASE"
                        or "créer une nouvelle base" in txt
                        or "create new database" in txt
                    ):
                        create_action = act
                        break
        assert create_action is not None
        create_action.trigger()
        qapp.processEvents()

        assert win.db is not None
        assert win.db.db3_dir == new_root / "db3"
        assert (new_root / "db3" / "thumbindex.db").exists()
    finally:
        win.stop_background_tasks()
        win.close()
        qapp.processEvents()


def test_clean_picasa_traces_recursive_and_menu_alerts(qapp, tmp_path: Path, monkeypatch) -> None:
    """FR: Vérifie la fonctionnalité Outils > Nettoyer les traces Picasa (.picasa.ini)... :
    1. Présence de l'action ID_CLEAN_PICASA_TRACES dans le menu Outils (&Tools).
    2. Détection récursive des fichiers .picasa.ini (y compris cachés sur Windows) et Picasa.ini.
    3. Alerte de confirmation QMessageBox.warning (annulation avec No, suppression avec Yes)
       et alerte d'information de fin sans toucher aux photos originales.
    EN: Verifies Tools > Clean Picasa Traces (.picasa.ini)...:
    1. Presence of the ID_CLEAN_PICASA_TRACES action in the Tools (&Tools) menu.
    2. Recursive detection of .picasa.ini (including hidden on Windows) and Picasa.ini files.
    3. QMessageBox.warning confirmation dialog (cancel with No, delete with Yes)
       and completion QMessageBox.information dialog while leaving original photos untouched.
    """
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from picasa_py.ini.parser import PicasaIniDocument

    db_root = tmp_path / "db_clean_test"
    db = PicasaDatabase.create_new(db_root)

    # Construire une arborescence de dossiers avec des photos et des .picasa.ini (dont cachés)
    photos_root = tmp_path / "Phototheque"
    sub_a = photos_root / "2025" / "Vacances"
    sub_b = photos_root / "2026" / "Famille"
    sub_a.mkdir(parents=True)
    sub_b.mkdir(parents=True)

    img_a = sub_a / "plage.jpg"
    img_b = sub_b / "portrait.jpg"
    Image.new("RGB", (32, 32), (100, 150, 200)).save(img_a, "JPEG")
    Image.new("RGB", (32, 32), (200, 120, 80)).save(img_b, "JPEG")

    ini_root = photos_root / ".picasa.ini"
    ini_a = sub_a / ".picasa.ini"
    ini_b = sub_b / "Picasa.ini"

    for ini_p in (ini_root, ini_a, ini_b):
        doc = PicasaIniDocument()
        sec = doc.get_or_create_section("Picasa")
        sec.set("name", ini_p.parent.name)
        doc.write_file(str(ini_p))

    found = PicasaDatabase.find_picasa_ini_traces(photos_root)
    assert len(found) == 3

    win = PicasaMainWindow(db_path=str(db_root), auto_scan=False)
    _KEEP_REFS.append(win)
    try:
        # 1. Vérifier que l'action ID_CLEAN_PICASA_TRACES est bien présente dans le menu Outils
        clean_action = None
        for menu_act in win.menuBar().actions():
            menu = menu_act.menu()
            if menu:
                for act in menu.actions():
                    if act.objectName() == "ID_CLEAN_PICASA_TRACES":
                        clean_action = act
                        break
        assert clean_action is not None

        # 2. Simuler un refus (StandardButton.No) dans l'alerte d'avertissement : rien ne doit être supprimé
        warnings_shown: List[str] = []
        infos_shown: List[str] = []

        monkeypatch.setattr(
            QFileDialog,
            "getExistingDirectory",
            lambda *args, **kwargs: str(photos_root),
        )
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda _parent, title, text, *_a, **_kw: (
                warnings_shown.append(f"{title}: {text}"),
                QMessageBox.StandardButton.No,
            )[1],
        )
        monkeypatch.setattr(
            QMessageBox,
            "information",
            lambda _parent, title, text, *_a, **_kw: (
                infos_shown.append(f"{title}: {text}"),
                QMessageBox.StandardButton.Ok,
            )[1],
        )

        deleted_no = win.action_clean_picasa_traces()
        assert deleted_no == 0
        assert len(warnings_shown) == 1
        assert "3 fichier(s)" in warnings_shown[0]
        assert len(PicasaDatabase.find_picasa_ini_traces(photos_root)) == 3

        # 3. Simuler la confirmation (StandardButton.Yes) via le déclenchement du menu
        warnings_shown.clear()
        infos_shown.clear()
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda _parent, title, text, *_a, **_kw: (
                warnings_shown.append(f"{title}: {text}"),
                QMessageBox.StandardButton.Yes,
            )[1],
        )

        clean_action.trigger()
        qapp.processEvents()

        assert len(warnings_shown) == 1
        assert len(infos_shown) == 1
        assert "3 fichier(s) .picasa.ini ont été supprimés" in infos_shown[0]
        assert len(PicasaDatabase.find_picasa_ini_traces(photos_root)) == 0
        # Les photos originales doivent être intactes
        assert img_a.exists() and img_b.exists()

        # 4. Relancer sur le dossier déjà propre : alerte « Aucune trace Picasa détectée »
        infos_shown.clear()
        deleted_empty = win.action_clean_picasa_traces(photos_root, confirm=True)
        assert deleted_empty == 0
        assert len(infos_shown) == 1
        assert "Aucun fichier .picasa.ini" in infos_shown[0]
    finally:
        win.stop_background_tasks()
        win.close()
        qapp.processEvents()


def test_database_root_directory_hierarchy_parity(tmp_path: Path, monkeypatch) -> None:
    """FR: Vérifie la parité stricte de l'arborescence de fichiers et sous-dossiers de la base de données
    avec `picasa3.exe` (Ref: 0x004156F0, 0x004164A7..0x004165FB, 0x00419C30, 0x0041B5D3, 0x0044F390,
    0x004F5960, 0x004F5D90, 0x0066F2B0, 0x0097E366, 0x00980EC0) :
    1. `<root>/db3/` : fichiers binaires et listes `.txt`, aucun sous-dossier (`albums/` interdit),
       et `tags.txt` n'est créé que si au moins un mot-clé existe.
    2. `<root>/contacts/contacts.xml` + copie automatique vers `Picasa2Albums/<db_guid>/backup.xml`.
    3. `<root>/ioqueue/` : `slingshot.ioq`, `filesafe.ioq`, `albumsafe.ioq`.
    4. `<root>/tmp/` : créé à l'initialisation / sauvegarde.
    5. `Picasa2Albums/` : `watchedfolders.txt`, `frexcludefolders.txt` (sans AttributeError sur `repository.pairs`),
       et suppression des `.pal` dans `Picasa2Albums/<db_guid>/` lors de `delete_album()`.
    6. `PicasaPreferences.set_repository_path()` / `get_repository_path()` utilise `AppLocalDataPath`
       sans créer de fichier `repository.dat` parasite à la racine `<root>/`.
    EN: Verifies strict parity of the database file and folder hierarchy with `picasa3.exe`.
    """
    from picasa_py.db.contacts import Contact
    from picasa_py.db.preferences import PicasaPreferences

    # Simuler un dossier racine Picasa2 comme %LOCALAPPDATA%\Google\Picasa2
    google_dir = tmp_path / "Google"
    picasa2_root = google_dir / "Picasa2"
    db = PicasaDatabase.create_new(picasa2_root)

    # 1. Vérifier les sous-dossiers directs sous Picasa2 (db3, contacts, ioqueue, tmp)
    assert db.root_dir == picasa2_root
    assert (picasa2_root / "db3").is_dir()
    assert (picasa2_root / "contacts").is_dir()
    assert (picasa2_root / "ioqueue").is_dir()
    assert (picasa2_root / "tmp").is_dir()
    for ioq_name in ("slingshot.ioq", "filesafe.ioq", "albumsafe.ioq"):
        assert (picasa2_root / "ioqueue" / ioq_name).is_file()

    # Aucun sous-dossier dans db3/ et aucun repository.dat à la racine Picasa2/
    assert not any(p.is_dir() for p in (picasa2_root / "db3").iterdir())
    assert not (picasa2_root / "repository.dat").exists()
    # Sur une base vierge sans mots-clés, tags.txt n'est pas créé tandis que les 4 autres listes .txt existent
    for txt_name in ("scanlist.txt", "starlist.txt", "saverlist.txt", "facetags.txt"):
        assert (picasa2_root / "db3" / txt_name).is_file()
    assert not (picasa2_root / "db3" / "tags.txt").exists()
    for sent_name in ("catdata_0", "imagedata_0", "albumdata_0", "profilephotos_0.db"):
        assert (picasa2_root / "db3" / sent_name).read_bytes() == b"\xcd\xcc\xcc?"

    # 2. Vérifier Picasa2Albums (dossier frère de Picasa2 sous Google/)
    p2a_dir = google_dir / "Picasa2Albums"
    assert db.picasa2albums_dir == p2a_dir
    assert (p2a_dir / "watchedfolders.txt").is_file()
    assert (p2a_dir / "frexcludefolders.txt").is_file()

    # Configurer un dossier surveillé ("1") et un dossier exclu FR ("0") dans repository.dat
    watched_folder = r"C:\Users\Test\Pictures\Vacances"
    excl_fr_folder = r"C:\Users\Test\Pictures\ExcluFR"
    db.set_watched_folder(watched_folder, "1")
    db.repository.set(f"FileManagerFRStatus\\{excl_fr_folder}\\", "0")

    # Créer un sous-dossier <db_guid> dans Picasa2Albums avec un fichier .pal
    guid_dir = p2a_dir / "d3607f57f103d40b8a8be532944fa91d"
    guid_dir.mkdir(parents=True, exist_ok=True)
    pal_file = guid_dir / "my_album_123.pal"
    pal_file.write_text("<picasa2album/>", encoding="utf-8")

    # Ajouter un contact et sauvegarder la base
    db.contacts.add_contact(Contact(id="1234567890abcdef", name="Jean Dupont"))
    db.save_database()

    # Vérifier watchedfolders.txt, frexcludefolders.txt et backup.xml dans Picasa2Albums
    wf_content = (p2a_dir / "watchedfolders.txt").read_text(encoding="utf-8")
    fr_content = (p2a_dir / "frexcludefolders.txt").read_text(encoding="utf-8")
    assert watched_folder + "\\" in wf_content
    assert excl_fr_folder + "\\" in fr_content
    assert (guid_dir / "backup.xml").is_file()
    assert "Jean Dupont" in (guid_dir / "backup.xml").read_text(encoding="utf-8")

    # Vérifier que delete_album supprime le .pal dans Picasa2Albums/<db_guid>/
    assert db.delete_album("my_album_123") is True
    assert not pal_file.exists()

    # 3. Vérifier que set_repository_path / get_repository_path utilise AppLocalDataPath sans créer Picasa2/repository.dat
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    prev_val = PicasaPreferences.get_repository_path()
    try:
        assert PicasaPreferences.set_repository_path(str(picasa2_root / "db3")) is True
        assert PicasaPreferences.get_repository_path() == str(picasa2_root)
        assert not (picasa2_root / "repository.dat").exists()
    finally:
        prefs = PicasaPreferences()
        if prev_val:
            prefs.setValue("AppLocalDataPath", prev_val)
        else:
            prefs._settings.remove("AppLocalDataPath")
        prefs.sync()


def test_open_empty_db3_and_scan_produces_full_picasa3_compatible_schema(tmp_path: Path) -> None:
    """FR: Vérifie que l'ouverture d'un dossier db3/ vide (ou partiellement purgé sans fichiers .pmp ni *_index.db)
    via PicasaDatabase.open() suivie d'un scan PicasaDirScanner et d'un save_database() génère sur disque :
    - les 56 colonnes .pmp avec exactement len(thumbindex.records) lignes pour imagedata_*, >= 1 ligne pour albumdata_*
      (incluant la ligne 0 ]unknownface / "Sans nom" cat=8 @ 0x008AAD76) et 9 lignes pour catdata_* ;
    - les 6 paires CBlockFile (*_0.db + *_index.db) avec les miniatures JPEG effectivement écrites dans thumbs_0.db / thumbs2_0.db ;
    - repository.dat contenant DBID, rawversion="1.1", colorspaceversion="1.1", gpsversion="1.0" (Ref: 0x004199E0, 0x0041F586..0x0041F8C1) ;
    - wordhash.dat, usernames.dat, les 4 sentinelles et les listes .txt requis par CThumbDB::Open (0x0041EE10).
    EN: Verifies that opening an empty or partially purged db3/ folder via PicasaDatabase.open() followed by
    scanning and save_database() writes all 56 .pmp columns, all 6 CBlockFile pairs with thumbnails,
    repository.dat version keys, wordhash.dat, usernames.dat, sentinels, and .txt lists required by CThumbDB::Open.
    """
    empty_root = tmp_path / "Picasa2"
    empty_db3 = empty_root / "db3"
    empty_db3.mkdir(parents=True)

    photos_dir = tmp_path / "Photos" / "1999"
    photos_dir.mkdir(parents=True)
    for i in range(2):
        img = Image.new("RGB", (160, 120), color=(50 + 40 * i, 100, 180))
        img.save(photos_dir / f"img_{i}.jpg", "JPEG")

    # Ouvrir le dossier db3/ vide via PicasaDatabase.open (comme au démarrage sur un dossier db3/ vidé)
    db = PicasaDatabase.open(empty_db3)
    db.set_watched_folder(str(photos_dir), "1")

    scanner = PicasaDirScanner(db)
    for fpath in scanner.find_unindexed_files([str(photos_dir)]):
        scanner.index_file(fpath)
    db.save_database()

    # 1. Toutes les 56 colonnes .pmp doivent exister sur disque et être alignées
    expected_img_rows = len(db.index)
    assert expected_img_rows == 3  # 1 dossier (type=1) + 2 photos (type=2)
    for stem in STANDARD_PMP_SCHEMA:
        pmp_path = empty_db3 / f"{stem}.pmp"
        assert pmp_path.is_file(), f"{stem}.pmp manquant sur disque"
        if stem.startswith("imagedata_"):
            assert len(db.pmps[stem].records) == expected_img_rows
        elif stem.startswith("albumdata_"):
            assert len(db.pmps[stem].records) >= 2  # ligne 0 (]unknownface) + ligne 1 (dossier 1999)
        elif stem.startswith("catdata_"):
            assert len(db.pmps[stem].records) == 9

    assert db.pmps["albumdata_token"].records[0] == "]unknownface"
    assert db.pmps["albumdata_category"].records[0] == 8

    # 2. Les miniatures doivent avoir été enregistrées dans thumbs_0.db et thumbs2_0.db
    for prefix in STANDARD_BLOCKFILE_PREFIXES:
        assert (empty_db3 / f"{prefix}_0.db").is_file()
        assert (empty_db3 / f"{prefix}_index.db").is_file()
    assert (empty_db3 / "thumbs_0.db").stat().st_size > 4
    assert (empty_db3 / "thumbs2_0.db").stat().st_size > 4
    assert db.get_thumbnail(1, "small") is not None
    assert db.get_thumbnail(2, "small") is not None

    # 3. Clés obligatoires de repository.dat (0x004199E0, 0x0041F586..0x0041F8C1)
    assert db.repository is not None
    assert db.repository.get("DBID") is not None and len(db.repository.get("DBID") or "") == 32
    assert db.repository.get("rawversion") == "1.1"
    assert db.repository.get("colorspaceversion") == "1.1"
    assert db.repository.get("gpsversion") == "1.0"
    assert (empty_db3 / "wordhash.dat").is_file()
    assert (empty_db3 / "usernames.dat").is_file()


def test_starred_photos_album_count_matches_thumbnail_view_filter(qapp, tmp_path: Path) -> None:
    """FR: Vérifie que lorsqu'une photo est marquée favorite (`star=yes` dans `.picasa.ini` / `]star` dans `wordhash.dat`),
    le compteur de `db.get_starred_photo_paths()` (« Photos favorites (1) » dans l'arborescence) correspond exactement
    au nombre de vignettes affichées par `PicasaThumbnailView.filter_by_starred()`, même lorsque `set_database(db)`
    est appelé avant `db.get_starred_photo_paths()`.
    EN: Verifies that when a photo is starred (`star=yes` in `.picasa.ini` / `]star` in `wordhash.dat`),
    `db.get_starred_photo_paths()` ("Starred Photos (1)" in the library tree) matches the exact number of thumbnails
    displayed by `PicasaThumbnailView.filter_by_starred()`, even when `set_database(db)` runs before `get_starred_photo_paths()`.
    """
    from picasa_py.ui.thumbnail_view import PicasaThumbnailView

    root = tmp_path / "Picasa2"
    db3 = root / "db3"
    photos_dir = tmp_path / "Photos" / "Vacances"
    photos_dir.mkdir(parents=True)

    img1 = Image.new("RGB", (160, 120), color=(200, 80, 40))
    img1.save(photos_dir / "fav.jpg", "JPEG")
    img2 = Image.new("RGB", (160, 120), color=(40, 80, 200))
    img2.save(photos_dir / "normal.jpg", "JPEG")
    (photos_dir / ".picasa.ini").write_text("[fav.jpg]\r\nstar=yes\r\n", encoding="utf-8")

    db = PicasaDatabase.create_new(db3)
    db.set_watched_folder(str(photos_dir), "1")
    scanner = PicasaDirScanner(db)
    for fpath in scanner.find_unindexed_files([str(photos_dir)]):
        scanner.index_file(fpath)
    db.save_database()

    # Recharger la base comme au démarrage et appeler set_database AVANT get_starred_photo_paths()
    db_reloaded = PicasaDatabase.open(db3)
    tv = PicasaThumbnailView()
    tv.set_database(db_reloaded)

    starred_paths = db_reloaded.get_starred_photo_paths()
    assert len(starred_paths) == 1
    tv.filter_by_starred()
    assert len(tv.filtered_indices) == 1
    assert Path(tv.items[tv.filtered_indices[0]].path).name == "fav.jpg"


def test_ignored_ini_face_materialized_and_zero_face_scan_persisted_to_disk(qapp, tmp_path: Path) -> None:
    """FR: Vérifie que :
    1) Lors de la création d'une nouvelle base à partir d'un dossier dont `.picasa.ini` contient un visage ignoré
       (`faces=rect64(...),ffffffffffffffff`), PyCasa matérialise l'enregistrement enfant `type == 1001` avec le jeton
       `]ignoreface` dans `wordhash.dat` (`picasa3.exe @ 0x004842BA..0x0048431C`) et ne le redétecte pas comme visage sans nom.
    2) Lorsque `BackgroundFaceDetectionWorker.run()` analyse des photos à 0 visage (`total_detected == 0`), il persiste
       `imagedata_facerect = 1` sur disque (`imagedata_facerect.pmp`), de sorte qu'au redémarrage suivant ni Picasa 3
       ni PyCasa ne relancent l'analyse faciale sur ces photos (`get_unscanned_photos() == []`).
    EN: Verifies that:
    1) On new DB creation from a folder whose `.picasa.ini` contains an ignored face (`faces=rect64(...),ffffffffffffffff`),
       PyCasa materializes the `type == 1001` child record with `]ignoreface` in `wordhash.dat` and does not re-detect it.
    2) When `BackgroundFaceDetectionWorker.run()` scans 0-face photos (`total_detected == 0`), it persists
       `imagedata_facerect = 1` to disk (`imagedata_facerect.pmp`) so neither Picasa 3 nor PyCasa rescans them on next launch.
    """
    from picasa_py.faces.face_manager import BackgroundFaceDetectionWorker, FaceRect

    root = tmp_path / "Picasa2"
    db3 = root / "db3"
    photos_dir = tmp_path / "Photos" / "Paysages"
    photos_dir.mkdir(parents=True)

    img1 = Image.new("RGB", (200, 150), color=(30, 140, 60))
    img1.save(photos_dir / "tree.jpg", "JPEG")
    img2 = Image.new("RGB", (200, 150), color=(60, 100, 180))
    img2.save(photos_dir / "sky.jpg", "JPEG")

    ignored_fr = FaceRect(left=0.25, top=0.25, right=0.55, bottom=0.65)
    r64_str = ignored_fr.to_rect64()
    (photos_dir / ".picasa.ini").write_text(
        f"[tree.jpg]\r\nfaces={r64_str},ffffffffffffffff\r\n",
        encoding="utf-8",
    )

    db = PicasaDatabase.create_new(db3)
    db.set_watched_folder(str(photos_dir), "1")
    scanner = PicasaDirScanner(db)
    for fpath in scanner.find_unindexed_files([str(photos_dir)]):
        scanner.index_file(fpath)
    db.face_manager.reload()
    db.save_database()

    # L'entrée ffffffffffffffff doit avoir créé un enfant 1001 marqué ]ignoreface et 0 visage sans nom
    assert len(db.face_manager.unnamed_faces) == 0
    ignore_ids = db.wordhash.search("]ignoreface") if db.wordhash else []
    assert len(ignore_ids) == 1
    child_1001 = ignore_ids[0]
    assert db.index[child_1001].type == 1001

    # Exécuter BackgroundFaceDetectionWorker sur le reste des photos sans visage (sky.jpg -> 0 visage)
    worker = BackgroundFaceDetectionWorker(db)
    worker.run()

    # Recharger depuis le disque : toutes les photos doivent avoir imagedata_facerect != 0 et get_unscanned_photos() == []
    db2 = PicasaDatabase.open(db3)
    assert db2.face_manager.get_unscanned_photos() == []
    for idx, rec in enumerate(db2.index):
        if rec.type == 2:
            assert db2.pmps["imagedata_facerect"].records[idx] != 0


def test_unknown_person_placeholder_albums_created_and_displayed(tmp_path: Path, monkeypatch) -> None:
    """
    FR : Vérifie que les identifiants de contacts orphelins dans `.picasa.ini` (`faces=rect64(...),<cid>`
    absents de `contacts.xml` et `[Contacts2]`) créent des albums de personnes distincts (`cat == 8`)
    intitulés `<Personne inconnue>` (`CThumbDB::UnknownPerson`), ne sont pas fusionnés entre eux,
    et s'affichent dans la section `Personnes` (`PicasaLibraryTree`) comme dans `picasa3.exe`.
    EN: Verifies that orphan contact IDs in `.picasa.ini` (`faces=rect64(...),<cid>` missing from
    `contacts.xml` and `[Contacts2]`) create distinct `cat == 8` person albums named `<Personne inconnue>`
    (`CThumbDB::UnknownPerson`), are never merged together, and appear in `Personnes` (`PicasaLibraryTree`).
    Ref: picasa3.exe @ 0x00484264..0x00484453, 0x00489EC5..0x0048A23D (CThumbDB::UnknownPerson @ 0x00C81BA4)
    """
    import os
    from PIL import Image
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.scanner.scanner import PicasaDirScanner
    from picasa_py.ui.resources import PicasaResourceManager

    res_mgr = PicasaResourceManager.get()
    monkeypatch.setattr(res_mgr, "_current_lang", "fr")

    root = tmp_path / "Picasa2"
    db3 = root / "db3"
    contacts_dir = root / "contacts"
    photos_dir = tmp_path / "Photos" / "Famille"
    photos_dir.mkdir(parents=True)

    Image.new("RGB", (200, 150), color=(120, 80, 60)).save(photos_dir / "group.jpg", "JPEG")

    fr_known = FaceRect(left=0.10, top=0.20, right=0.30, bottom=0.50).to_rect64()
    fr_unk1 = FaceRect(left=0.40, top=0.20, right=0.60, bottom=0.50).to_rect64()
    fr_unk2 = FaceRect(left=0.70, top=0.20, right=0.90, bottom=0.50).to_rect64()

    cid_known = "6e55417b6930726"
    cid_unk1 = "b41b35abd37e9064"
    cid_unk2 = "50b1e94187ba7f02"

    (photos_dir / ".picasa.ini").write_text(
        f"[group.jpg]\r\n"
        f"faces={fr_known},{cid_known};{fr_unk1},{cid_unk1};{fr_unk2},{cid_unk2}\r\n"
        f"[Contacts2]\r\n"
        f"{cid_known}=Elisabeth;;\r\n",
        encoding="utf-8",
    )

    db = PicasaDatabase.create_new(db3, contacts_dir)
    db.set_watched_folder(str(photos_dir), "1")
    scanner = PicasaDirScanner(db)
    for fpath in scanner.find_unindexed_files([str(photos_dir)]):
        scanner.index_file(fpath)
    db.face_manager.reload()
    db.save_database()

    # Les 3 contacts (1 nommé + 2 <Personne inconnue>) doivent exister séparément dans people et albumdata_*
    assert cid_known in db.face_manager.people
    assert cid_unk1 in db.face_manager.people
    assert cid_unk2 in db.face_manager.people
    assert db.face_manager.people[cid_known].name == "Elisabeth"
    assert db.face_manager.people[cid_unk1].name == "<Personne inconnue>"
    assert db.face_manager.people[cid_unk2].name == "<Personne inconnue>"
    assert len(db.face_manager.unnamed_faces) == 0

    # Recharger depuis db3 sur disque et vérifier la persistance dans albumdata_*
    db2 = PicasaDatabase.open(db3, contacts_dir)
    assert cid_unk1 in db2.face_manager.people
    assert cid_unk2 in db2.face_manager.people
    assert db2.face_manager.people[cid_unk1].name == "<Personne inconnue>"
    assert db2.face_manager.people[cid_unk2].name == "<Personne inconnue>"
    assert db2.face_manager.people[cid_unk1].photo_count == 1
    assert db2.face_manager.people[cid_unk2].photo_count == 1

    # Vérifier le tri de ComparePeopleAlbums (0x004A7B9A..0x004A7D80) :
    # les personnes nommées ("Elisabeth") précèdent toujours les "<Personne inconnue>"
    from picasa_py.ui.library_tree import PicasaLibraryTree
    sorted_clusters = PicasaLibraryTree._sort_people_clusters(
        type("DummyTree", (), {"people_sort_mode": 0})(),
        list(db2.face_manager.people.values()),
    )
    assert [p.name for p in sorted_clusters] == [
        "Elisabeth",
        "<Personne inconnue>",
        "<Personne inconnue>",
    ]

    # Renommer uniquement cid_unk1 ne doit pas modifier cid_unk2
    assert db2.face_manager.rename_person(cid_unk1, "Marie-Cécile")
    assert db2.face_manager.people[cid_unk1].name == "Marie-Cécile"
    assert db2.face_manager.people[cid_unk2].name == "<Personne inconnue>"


def test_people_tree_displays_face_thumbnails_after_scan(tmp_path: Path) -> None:
    """FR: Vérifie que la colonne de gauche `Personnes` (`PicasaLibraryTree` / `CAlbumListUI` @ `0x00764AE2..0x00765285`)
    affiche une miniature rectangulaire encadrée du visage de chaque personne (connue ou `<Personne inconnue>`)
    dès la fin de l'indexation (`BackgroundScanWorker`), même lorsque `populate_from_database(db)` a été appelé
    alors que la base venait d'être créée et était encore vide.
    EN: Verifies that the left sidebar `Personnes` (`PicasaLibraryTree` / `CAlbumListUI` @ `0x00764AE2..0x00765285`)
    renders a framed rectangular face thumbnail for each person (known or `<Personne inconnue>`) right after
    `BackgroundScanWorker` completes, even when `populate_from_database(db)` was initially called on an empty newly created DB.
    Ref: picasa3.exe @ 0x00764AE2 - 0x00765285
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from picasa_py.faces.face_manager import FaceRect
    from picasa_py.ui.library_tree import PicasaLibraryTree
    from picasa_py.scanner.scanner import BackgroundScanWorker

    _app = QApplication.instance() or QApplication([])

    google_dir = tmp_path / "Google"
    picasa2_root = google_dir / "Picasa2"
    db3 = picasa2_root / "db3"
    contacts_dir = picasa2_root / "contacts"
    contacts_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = tmp_path / "Photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    cid_known = "1a2b3c4d5e6f7081"
    cid_unk = "482510f7f40b913f"

    # Un fichier contacts.xml existe déjà avant create_new
    (contacts_dir / "contacts.xml").write_text(
        f'<contacts><contact id="{cid_known}" name="Elisabeth" display="Elisabeth"/></contacts>',
        encoding="utf-8",
    )

    img = Image.new("RGB", (400, 300), color=(210, 120, 60))
    img.save(photos_dir / "portrait.jpg", "JPEG")

    fr_known = FaceRect(0.10, 0.15, 0.35, 0.55).to_rect64().replace("rect64(", "").replace(")", "")
    fr_unk = FaceRect(0.55, 0.15, 0.80, 0.55).to_rect64().replace("rect64(", "").replace(")", "")
    (photos_dir / ".picasa.ini").write_text(
        f"[portrait.jpg]\r\n"
        f"faces=rect64({fr_known}),{cid_known};rect64({fr_unk}),{cid_unk}\r\n"
        f"[Contacts2]\r\n"
        f"{cid_known}=Elisabeth;;\r\n",
        encoding="utf-8",
    )

    # 1. Créer la base alors qu'elle est encore vide et peupler l'arbre immédiatement (comme switch_database)
    db = PicasaDatabase.create_new(db3, contacts_dir)
    assert len(db.contacts.contacts) == 1
    db.set_watched_folder(str(photos_dir), "1")

    tree = PicasaLibraryTree()
    tree.populate_from_database(db)

    # 2. Exécuter le worker de scan en arrière-plan, puis rafraîchir Personnes (comme _on_scan_finished)
    worker = BackgroundScanWorker(db, [str(photos_dir)])
    worker.run()
    assert getattr(worker, "_reloaded_face_manager", False) is True

    tree.refresh_people()

    assert tree.cat_people.childCount() == 2
    default_img = tree.res_mgr.get_icon(159).pixmap(16, 16).toImage()
    for i in range(tree.cat_people.childCount()):
        ch = tree.cat_people.child(i)
        ud = ch.data(0, Qt.ItemDataRole.UserRole)
        assert ud is not None
        assert ud.get("has_avatar") is True
        icon_img = ch.icon(0).pixmap(16, 16).toImage()
        assert not icon_img.isNull()
        assert icon_img != default_img


def test_ini_encoding_header_and_hex_cid_resolution_and_wordhash_face_search(tmp_path: Path) -> None:
    """
    FR: Vérifie la parité stricte avec `picasa3.exe` sur :
    1. L'émission de `[encoding]\\r\\nutf8=1\\r\\n` uniquement lorsque `[Picasa]` contient de l'UTF-8
       ou que `[encoding]` était déjà présent (`picasa3.exe @ 0x0068AE31, 0x00CA77F0`).
    2. La résolution symétrique des identifiants `contact_id` 64 bits `%I64x` (15 caractères hex)
       et `%016I64x` (16 caractères avec zéro initial) dans `get_person`, `get_person_avatar`,
       `rename_person` et `delete_person` (`picasa3.exe @ 0x00413630`).
    3. La résolution des sous-enregistrements de visages `type == 1001` vers leur photo parente
       et le filtrage des `doc_id` hors bornes dans `PicasaDatabase.search()`.
    """
    import os
    from PIL import Image
    from picasa_py.faces.face_manager import FaceRect
    from picasa_py.ini.parser import PicasaIniDocument, PicasaIniParser
    from picasa_py.ini.writer import PicasaIniWriter
    from picasa_py.scanner.scanner import BackgroundScanWorker

    # 1. [encoding]\r\nutf8=1\r\n uniquement pour [Picasa] UTF-8 ou [encoding] explicite
    doc_contacts = PicasaIniDocument()
    doc_contacts.get_or_create_section("Contacts2").set("6e55417b6930726", "Hélène PARTIOT;;")
    doc_contacts.set_caption("photo.jpg", "Été en famille")
    raw_contacts = PicasaIniWriter.to_bytes(doc_contacts)
    assert not raw_contacts.startswith(b"[encoding]\r\nutf8=1\r\n")
    assert "Hélène PARTIOT".encode("utf-8") in raw_contacts

    doc_folder = PicasaIniDocument()
    doc_folder.get_or_create_section("Picasa").set("description", "Vacances d'été")
    raw_folder = PicasaIniWriter.to_bytes(doc_folder)
    assert raw_folder.startswith(b"[encoding]\r\nutf8=1\r\n[Picasa]\r\n")

    # 2. Résolution %I64x (15 chars) vs %016I64x (16 chars) et recherche wordhash sur 1001
    google_dir = tmp_path / "Google"
    picasa2_root = google_dir / "Picasa2"
    db3 = picasa2_root / "db3"
    contacts_dir = picasa2_root / "contacts"
    photos_dir = tmp_path / "Photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (320, 240), color=(140, 160, 200))
    img.save(photos_dir / "famille.jpg", "JPEG")

    fr_hex = FaceRect(0.20, 0.20, 0.50, 0.60).to_rect64().replace("rect64(", "").replace(")", "")
    (photos_dir / ".picasa.ini").write_text(
        f"[famille.jpg]\r\n"
        f"faces=rect64({fr_hex}),6e55417b6930726\r\n"
        f"[Contacts2]\r\n"
        f"06e55417b6930726=Hélène PARTIOT;;\r\n",
        encoding="utf-8",
    )

    db = PicasaDatabase.create_new(db3, contacts_dir)
    db.set_watched_folder(str(photos_dir), "1")
    worker = BackgroundScanWorker(db, [str(photos_dir)])
    worker.run()
    db.save_database()

    db2 = PicasaDatabase.open(db3, contacts_dir)
    assert db2.face_manager is not None
    # Accessible aussi bien avec que sans zéro initial
    p_unpadded = db2.face_manager.get_person("6e55417b6930726")
    p_padded = db2.face_manager.get_person("06e55417b6930726")
    assert p_unpadded is not None
    assert p_unpadded is p_padded
    assert p_unpadded.name == "Hélène PARTIOT"

    # 3. Recherche wordhash sur un jeton attaché à l'enregistrement 1001 + doc_id hors bornes
    assert db2.wordhash is not None
    db2.wordhash.add_word("stale_oob_token", 99999)
    assert db2.search("stale_oob_token") == []

    face_1001_indices = [i for i, r in enumerate(db2.thumbindex.records) if r.type == 1001]
    assert len(face_1001_indices) == 1
    photo_indices = [i for i, r in enumerate(db2.thumbindex.records) if r.type == 2]
    assert len(photo_indices) == 1
    db2.wordhash.add_word("token_sur_visage_1001", face_1001_indices[0])
    search_hits = db2.search("token_sur_visage_1001")
    assert search_hits == [photo_indices[0]]

    # Renommage via l'identifiant 16 caractères (avec zéro en tête)
    assert db2.face_manager.rename_person("06e55417b6930726", "Hélène P.") is True
    assert db2.face_manager.get_person("6e55417b6930726").name == "Hélène P."
    doc_after = PicasaIniParser.parse_file(str(photos_dir / ".picasa.ini"))
    c2_sec = doc_after.get_section("Contacts2")
    assert c2_sec is not None
    assert (c2_sec.get("6e55417b6930726") or c2_sec.get("06e55417b6930726")) == "Hélène P.;;"

    # 4. ContactsFile.get() tolérant aux variantes 15 et 16 caractères
    assert db2.contacts is not None
    c_15 = db2.contacts.get("6e55417b6930726")
    c_16 = db2.contacts.get("06e55417b6930726")
    assert c_15 is not None and c_15 is c_16
    assert c_15.name == "Hélène P."

    # 5. ThumbIndexFile.sanitize_records() préserve les enregistrements 1001 actifs (même avec path == "")
    db2.thumbindex.sanitize_records()
    assert db2.thumbindex.records[face_1001_indices[0]].type == 1001

    # 6. _write_auxiliary_txt_lists() vide starlist.txt et tags.txt lorsque la dernière étoile ou le dernier tag est retiré
    p_idx = photo_indices[0]
    db2.set_starred(p_idx, True)
    db2.add_keyword(p_idx, "vacances_test")
    db2.save_database()
    assert "famille.jpg" in (db3 / "starlist.txt").read_text(encoding="utf-8")
    assert "vacances_test" in (db3 / "tags.txt").read_text(encoding="utf-8")

    db2.set_starred(p_idx, False)
    db2.remove_keyword(p_idx, "vacances_test")
    db2.save_database()
    assert (db3 / "starlist.txt").read_text(encoding="utf-8").strip() == ""
    assert (db3 / "tags.txt").read_text(encoding="utf-8").strip() == ""

    # 6 bis. set_person_album_cover persiste la couverture dans contacts.xml et repository.dat
    fr_obj = db2.face_manager.get_faces_for_photo(str(photos_dir / "famille.jpg"))[0]
    assert db2.face_manager.set_person_album_cover("06e55417b6930726", str(photos_dir / "famille.jpg"), fr_obj) is True
    assert db2.contacts.get("6e55417b6930726").extra_attrs.get("cover_rect64") == fr_obj.to_rect64()
    assert db2.repository.get("PeopleCovers/6e55417b6930726/photo_path") == str(photos_dir / "famille.jpg")

    # 7. PicasaFolderWatcher ne doit surveiller aucun sous-dossier si tous les dossiers racines sont en statut '0' ou '2'
    # et save_repository_only() persiste bien thumbindex.db lorsque set_watched_folder(..., '0') l'a rendu dirty
    from picasa_py.scanner.watcher import PicasaFolderWatcher

    sub_dir = photos_dir / "SubFolder"
    sub_dir.mkdir(parents=True, exist_ok=True)
    db2.set_watched_folder(str(photos_dir), "0")
    assert db2.thumbindex.dirty is True
    db2.save_repository_only()
    assert db2.thumbindex.dirty is False
    watcher = PicasaFolderWatcher(db2)
    assert len(watcher.watched_paths) == 0
    watcher.stop()

    # 8. find_photo_index / _index_single_record_into_cache : si un enregistrement supprimé (flags_hi=0)
    # est suivi d'un nouvel enregistrement actif portant le même chemin, le nouvel indice actif prime
    db2.set_watched_folder(str(photos_dir), "1")
    db2.thumbindex.records[p_idx].flags_hi = 0  # soft-delete l'ancien enregistrement
    assert db2.find_photo_index(str(photos_dir / "famille.jpg")) is None
    new_p_idx = db2.add_media_record(str(photos_dir), "famille.jpg", 1234, media_type=2)
    assert db2.find_photo_index(str(photos_dir / "famille.jpg")) == new_p_idx
    assert db2.find_media_index_by_path(str(photos_dir / "famille.jpg")) == new_p_idx


def test_pass6_photo_and_folder_lifecycle_and_scanner(tmp_path: Path):
    """
    FR: Vérifie les corrections de la passe 6 :
    - rename_photo / move_photo synchronisent FaceManager (photo_to_faces, person.photo_paths) et les fichiers .pal ;
    - delete_photo nettoie imagedata_personalbumrecs*, wordhash et FaceManager ;
    - ensure_folder_album_row synchronise albumdata_description depuis [Picasa] description= ;
    - PicasaDirScanner._check_deleted_records marque rec.is_active == False, imagedata_aliasparents == 0 et nettoie wordhash ;
    - move_folder et delete_folder mettent à jour thumbindex.db, albumdata, watched_folders.txt, FaceManager et .pal.
    """
    import os
    import shutil
    import os
    from PIL import Image
    from picasa_py.scanner.scanner import PicasaDirScanner

    db_dir = tmp_path / "db3_pass6"
    contacts_dir = tmp_path / "contacts_pass6"
    src_dir = tmp_path / "PhotosSrc"
    dst_dir = tmp_path / "PhotosDst"
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)

    img1 = src_dir / "portrait.jpg"
    Image.new("RGB", (64, 64), (180, 90, 60)).save(img1, "JPEG")

    ini_path = src_dir / ".picasa.ini"
    ini_path.write_bytes(
        b"[Picasa]\r\nname=Portraits\r\ndescription=Description dossier test\r\n"
        b"[portrait.jpg]\r\nfaces=rect64(3c9116d6a8717be7),6e55417b6930726\r\n"
        b"[Contacts2]\r\n6e55417b6930726=Alice Martin;;\r\n"
    )

    db = PicasaDatabase.create_new(db_dir, contacts_dir)
    db.set_watched_folder(str(src_dir), "1")
    db.set_watched_folder(str(dst_dir), "1")

    scanner = PicasaDirScanner(db)
    scanner.scan_directory(src_dir)
    db.ensure_folder_album_row(str(src_dir))

    # Vérifier la synchronisation de albumdata_description
    desc_col = db.pmps["albumdata_description"]
    uid_col = db.pmps["albumdata_uid"]
    fn_col = db.pmps["albumdata_filename"]
    album_row = next(
        i for i, f in enumerate(fn_col.records)
        if f and os.path.normcase(os.path.normpath(str(f))) == os.path.normcase(os.path.normpath(str(src_dir)))
    )
    assert desc_col.records[album_row] == "Description dossier test"

    # Créer un fichier .pal référençant portrait.jpg
    pal_dir = db.picasa2albums_dir / "mon_guid"
    pal_dir.mkdir(parents=True, exist_ok=True)
    pal_path = pal_dir / "cab1234567890.pal"
    pal_path.write_text(
        f'<picasa2album><files><filename>{str(img1)}</filename></files></picasa2album>',
        encoding="utf-8",
    )

    # Forcer le chargement de FaceManager
    _ = db.face_manager
    person = db.face_manager.people.get("6e55417b6930726")
    assert person is not None
    assert any(os.path.normcase(p) == os.path.normcase(str(img1)) for p in person.photo_paths)

    # 1. Renommer portrait.jpg -> portrait_renomme.jpg
    renamed_img = src_dir / "portrait_renomme.jpg"
    assert db.rename_photo(str(img1), "portrait_renomme.jpg") is True
    assert any(os.path.normcase(p) == os.path.normcase(str(renamed_img)) for p in person.photo_paths)
    assert not any(os.path.normcase(p) == os.path.normcase(str(img1)) for p in person.photo_paths)
    assert str(renamed_img).lower() in pal_path.read_text(encoding="utf-8").lower()

    # 2. Déplacer portrait_renomme.jpg vers dst_dir
    moved_img = dst_dir / "portrait_renomme.jpg"
    assert db.move_photo(str(renamed_img), str(dst_dir)) is True
    assert any(os.path.normcase(p) == os.path.normcase(str(moved_img)) for p in person.photo_paths)
    assert str(moved_img).lower() in pal_path.read_text(encoding="utf-8").lower()

    # 3. Déplacer le dossier dst_dir -> dst_dir_moved (sur disque puis via db.move_folder)
    moved_folder = tmp_path / "PhotosDstMoved"
    shutil.move(str(dst_dir), str(moved_folder))
    moved_img_in_moved_folder = moved_folder / "portrait_renomme.jpg"
    assert db.move_folder(str(dst_dir), str(moved_folder)) is True
    assert db.find_photo_index(str(moved_img_in_moved_folder)) is not None
    assert str(moved_img_in_moved_folder).lower() in pal_path.read_text(encoding="utf-8").lower()

    # 4. Vérifier _check_deleted_records du scanner lorsqu'un fichier disparaît du disque
    img2 = moved_folder / "jetable.jpg"
    Image.new("RGB", (32, 32), (10, 20, 30)).save(img2, "JPEG")
    scanner.scan_directory(moved_folder)
    idx_jetable = db.find_photo_index(str(img2))
    assert idx_jetable is not None
    assert db.thumbindex.records[idx_jetable].is_active is True
    img2.unlink()
    scanner._check_deleted_records(moved_folder)
    assert db.thumbindex.records[idx_jetable].is_active is False
    alias_col = db.pmps["imagedata_aliasparents"]
    assert alias_col.records[idx_jetable] == 0

    # 5. Supprimer portrait_renomme.jpg via delete_photo et vérifier le nettoyage complet
    idx_moved = db.find_photo_index(str(moved_img_in_moved_folder))
    assert idx_moved is not None
    assert db.delete_photo(str(moved_img_in_moved_folder), delete_from_disk=False) is True
    assert db.thumbindex.records[idx_moved].is_active is False
    pa_col = db.pmps["imagedata_personalbumrecs"]
    assert pa_col.records[idx_moved] == 0xFFFFFFFF
    person_after = db.face_manager.people.get("6e55417b6930726")
    assert person_after is None or not any(
        os.path.normcase(p) == os.path.normcase(str(moved_img_in_moved_folder))
        for p in person_after.photo_paths
    )

    # 6. Supprimer le dossier src_dir via db.delete_folder
    assert db.delete_folder(str(src_dir)) is True
    assert not any(
        r.type == 1 and r.is_active and r.path and os.path.normcase(os.path.normpath(r.path)) == os.path.normcase(os.path.normpath(str(src_dir)))
        for r in db.thumbindex.records
    )


def test_pass7_wordhash_remove_doc_export_exif_and_movie_maker(qapp, tmp_path: Path) -> None:
    """
    FR: Vérifie les correctifs de la septième passe de vérification :
    1) `WordHashFile.remove_doc(doc_id)` retire effectivement `doc_id` de toutes les entrées de `wordhash.dat`
       lors de `delete_photo`, `delete_folder` ou `_check_deleted_records`, et `delete_photo` nettoie aussi
       les entrées `<filename>` dans les fichiers `.pal`.
    2) `PicasaExportWorker` copie les vidéos, résout les collisions de noms (`-001`, `-002`) et préserve EXIF/ICC
       avec `Orientation = 1`.
    3) `extract_full_metadata` (`exif_reader.py`) calcule les dimensions effectives (Orientation EXIF + `crop`/`rotate`
       de `.picasa.ini`) et lit le repli `geotag=lat,lon` de `.picasa.ini`.
    4) `PicasaMovieMakerDialog._build_initial_slides` normalise les `contact_id` 15/16-hex et interroge `face_manager`.
    EN: Verifies Pass 7 fixes across WordHashFile.remove_doc, PicasaExportWorker, extract_full_metadata, and MovieMaker.
    """
    from picasa_py.ui.export_dialog import PicasaExportConfig, PicasaExportWorker
    from picasa_py.ui.exif_reader import extract_full_metadata
    from picasa_py.ui.movie_maker import PicasaMovieMakerDialog

    db_root = tmp_path / "Picasa2"
    db = PicasaDatabase.create_new(db_root)

    folder_a = tmp_path / "FolderA"
    folder_b = tmp_path / "FolderB"
    folder_a.mkdir(parents=True, exist_ok=True)
    folder_b.mkdir(parents=True, exist_ok=True)

    # 1. Créer une photo avec EXIF Orientation = 6 (90° CW) et DateTimeOriginal
    img_a = folder_a / "dup.jpg"
    pil_a = Image.new("RGB", (200, 100), (180, 90, 40))
    exif_a = pil_a.getexif()
    exif_a[0x0112] = 6  # Orientation 6 -> dimensions effectives 100x200
    exif_a[0x010F] = "Canon"
    exif_a[0x0110] = "EOS 5D"
    exif_a[0x9003] = "2022:08:15 14:30:00"
    pil_a.save(img_a, "JPEG", exif=exif_a.tobytes())

    # Créer une seconde photo portant le même nom dans FolderB + un fichier vidéo
    img_b = folder_b / "dup.jpg"
    Image.new("RGB", (120, 80), (40, 90, 180)).save(img_b, "JPEG")
    vid_b = folder_b / "clip.mp4"
    vid_b.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")

    (folder_a / ".picasa.ini").write_text(
        "[dup.jpg]\r\n"
        "star=yes\r\n"
        "geotag=48.8584,2.2945\r\n"
        "faces=rect64(3333333366666666),6e55417b6930726\r\n"
        "[Contacts2]\r\n"
        "06e55417b6930726=Alice;;\r\n",
        encoding="utf-8",
    )

    # Tester extract_full_metadata : Orientation 6 transforme 200x100 -> 100x200 et geotag INI est lu
    meta = extract_full_metadata(str(img_a))
    assert meta["dimensions"] == (100, 200)
    assert meta["gps"] is not None
    assert abs(meta["gps"][0] - 48.8584) < 1e-4
    assert abs(meta["gps"][1] - 2.2945) < 1e-4

    # Tester PicasaExportWorker : collisions dup.jpg / dup-001.jpg, copie vidéo clip.mp4 et EXIF Orientation = 1
    export_dest = tmp_path / "ExportOut"
    cfg = PicasaExportConfig(
        dest_path=str(export_dest),
        folder_name="Batch1",
        use_original_size=True,
        quality=90,
        add_numbers=False,
    )
    worker = PicasaExportWorker([str(img_a), str(img_b), str(vid_b)], cfg)
    worker.run()
    out_batch = export_dest / "Batch1"
    assert (out_batch / "dup.jpg").is_file()
    assert (out_batch / "dup-001.jpg").is_file()
    assert (out_batch / "clip.mp4").is_file()
    with Image.open(out_batch / "dup.jpg") as exp_img:
        assert exp_img.size == (100, 200)
        exp_exif = exp_img.getexif()
        assert exp_exif.get(0x0112) == 1
        assert exp_exif.get(0x0110) == "EOS 5D"

    # Tester PicasaMovieMakerDialog._build_initial_slides avec contact_id sur 16 caractères vs 15 dans faces=
    mm_dlg = PicasaMovieMakerDialog([str(img_a)], face_mode=True, contact_id="06e55417b6930726")
    assert len(mm_dlg.slides) == 1
    assert mm_dlg.slides[0].face_rect is not None
    assert mm_dlg.slides[0].date_str == "15/08/2022"
    mm_dlg.close()

    # Tester WordHashFile.remove_doc et nettoyage .pal lors de delete_photo
    scanner = PicasaDirScanner(db)
    scanner.scan_directory(str(folder_a))
    idx_a = db.find_photo_index(str(img_a))
    assert idx_a is not None
    assert db.wordhash is not None
    assert idx_a in db.wordhash.search("]star")

    pal_dir = db.picasa2albums_dir / "guid_test"
    pal_dir.mkdir(parents=True, exist_ok=True)
    pal_file = pal_dir / "alb1.pal"
    pal_file.write_text(
        f"<picasa2album>\r\n <files>\r\n  <filename>{str(img_a)}</filename>\r\n </files>\r\n</picasa2album>\r\n",
        encoding="utf-8",
    )

    assert db.delete_photo(idx_a, delete_from_disk=False) is True
    assert idx_a not in db.wordhash.search("]star")
    assert str(img_a).lower() not in pal_file.read_text(encoding="utf-8").lower()


def test_pass8_adjust_time_type32_video_trim_crop_exif_and_web_export(tmp_path: Path, qapp):
    """
    FR: Vérifie les corrections de la passe 8 :
    1. `PicasaAdjustTimeDialog.execute_adjustment()` sur une photo JPEG `rec.type == 32` :
       met à jour `imagedata_tagdate`, `imagedata_datetime`, `imagedata_originfast`,
       les sommes de contrôle des blockfiles (`thumbs_index.db`) et renvoie `results` non vide.
    2. `ole_to_datetime()` dans `picasa_py/db/thumbindex.py`.
    3. `PicasaVideoPlayer._persist_trim_key()` écrit bien `moviestart` et `movieend` dans `.picasa.ini`
       et `load_video()` les relit.
    4. `extract_full_metadata()` (`exif_reader.py`), `PicasaRenameDialog._get_image_resolution()`
       et `_get_cached_full_metadata()` (`histogram_widget.py`) calculent les dimensions exactes
       d'une photo recadrée (`crop=rect64(3333,3333,cccc,cccc)`) et pivotée (`rotate=rotate(1)`)
       tout en préservant `geotag=`.
    5. `PicasaWebExportDialog._export_gallery()` gère les collisions de noms de fichiers (`-001.jpg`),
       convertit les `.png` en `.jpg` et affiche la légende `caption=` de `.picasa.ini`.
    EN: Verifies Pass 8 fixes.
    """
    from datetime import datetime
    import os
    from PIL import Image
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.db.thumbindex import ole_to_datetime
    from picasa_py.scanner.scanner import PicasaDirScanner, datetime_to_ole
    from picasa_py.ui.offset_time_dialog import PicasaAdjustTimeDialog
    from picasa_py.ui.video_player import PicasaVideoPlayer
    from picasa_py.ui.exif_reader import extract_full_metadata
    from picasa_py.ui.rename_dialog import PicasaRenameDialog
    from picasa_py.ui.histogram_widget import _get_cached_full_metadata
    from picasa_py.ui.web_export_dialog import PicasaWebExportDialog
    from picasa_py.ini.parser import PicasaIniParser

    db_dir = tmp_path / "db3_pass8"
    db = PicasaDatabase.create_new(db_dir)

    folder_a = tmp_path / "PhotosA"
    folder_b = tmp_path / "PhotosB"
    folder_a.mkdir(parents=True, exist_ok=True)
    folder_b.mkdir(parents=True, exist_ok=True)

    # 1. Créer une photo JPEG 200x100 avec EXIF DateTimeOriginal (sera indexée en type=32)
    img_a = folder_a / "photo.jpg"
    im = Image.new("RGB", (200, 100), (80, 120, 200))
    exif = im.getexif()
    exif[0x0132] = "2021:05:10 10:00:00"
    exif[0x9003] = "2021:05:10 10:00:00"
    im.save(img_a, "JPEG", exif=exif.tobytes())

    scanner = PicasaDirScanner(db)
    scanner.scan_directory(str(folder_a))
    idx_a = db.find_photo_index(str(img_a))
    assert idx_a is not None
    db.thumbindex.records[idx_a].type = 32

    # Ajuster la date/heure via PicasaAdjustTimeDialog.execute_adjustment()
    from PySide6.QtCore import QDate, QTime
    target_dt = datetime(2023, 7, 14, 18, 30, 0)
    adj_dlg = PicasaAdjustTimeDialog([str(img_a)], db=db)
    adj_dlg.edit_new_date.setDate(QDate(2023, 7, 14))
    adj_dlg.edit_new_time.setTime(QTime(18, 30, 0))
    results = adj_dlg.execute_adjustment()
    adj_dlg.close()

    assert len(results) == 1
    assert results[0][0] == str(img_a)
    assert results[0][1] == target_dt

    expected_ole = datetime_to_ole(target_dt)
    assert abs(db.pmps["imagedata_tagdate"].records[idx_a] - expected_ole) < 1e-5
    assert abs(db.thumbindex.records[idx_a].to_unix_timestamp() - target_dt.timestamp()) < 2.0

    # Vérifier ole_to_datetime()
    dt_back = ole_to_datetime(expected_ole)
    assert dt_back is not None
    assert abs((dt_back - target_dt).total_seconds()) < 2.0

    # 2. Vérifier PicasaVideoPlayer._persist_trim_key()
    import types
    vid_path = folder_a / "sample.mp4"
    vid_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    edited_signals = []

    class _DummySig:
        def emit(self, p: str) -> None:
            edited_signals.append(p)

    vp_dummy = types.SimpleNamespace(
        current_video_path=str(vid_path),
        photo_edited=_DummySig(),
    )
    PicasaVideoPlayer._persist_trim_key(vp_dummy, "moviestart", "1500")
    PicasaVideoPlayer._persist_trim_key(vp_dummy, "movieend", "4500")
    doc_v = PicasaIniParser.parse_file(str(folder_a / ".picasa.ini"))
    sec_v = doc_v.get_section("sample.mp4")
    assert sec_v is not None
    assert sec_v.get("moviestart") == "1500"
    assert sec_v.get("movieend") == "4500"
    assert len(edited_signals) == 2

    # 3. Vérifier extract_full_metadata, _get_cached_full_metadata et PicasaRenameDialog._get_image_resolution
    #    sur une image 200x100 recadrée à 60% (120x60) puis pivotée de 90° (60x120) avec geotag
    from picasa_py.ini.writer import PicasaIniWriter
    meta_before = _get_cached_full_metadata(str(img_a))
    assert meta_before["dimensions"] == (200, 100)

    ini_a = folder_a / ".picasa.ini"
    doc_a = PicasaIniParser.parse_file(str(ini_a))
    sec_a = doc_a.get_or_create_section("photo.jpg")
    sec_a.set("crop", "rect64(33333333cccccccc)")
    sec_a.set("rotate", "rotate(1)")
    sec_a.set("geotag", "45.7640,4.8357")
    sec_a.set("caption", "Belle vue de Lyon")
    PicasaIniWriter.write_file(str(ini_a), doc_a)
    meta_after = extract_full_metadata(str(img_a))
    assert meta_after["dimensions"] == (60, 120)
    assert meta_after["gps"] is not None
    assert abs(meta_after["gps"][0] - 45.7640) < 1e-4
    assert abs(meta_after["gps"][1] - 4.8357) < 1e-4

    cached_after = _get_cached_full_metadata(str(img_a))
    assert cached_after["dimensions"] == (60, 120)

    ren_dlg = PicasaRenameDialog([str(img_a)])
    _, res_str = ren_dlg._extract_photo_date_and_size(Path(img_a))
    assert res_str == "60x120"
    ren_dlg.close()

    # 4. Vérifier PicasaWebExportDialog._export_gallery() avec doublon de nom et source PNG + caption INI
    img_b_png = folder_b / "photo.png"
    Image.new("RGBA", (80, 60), (255, 0, 0, 255)).save(img_b_png, "PNG")

    web_out = tmp_path / "WebGalleryOut"
    web_dlg = PicasaWebExportDialog([str(img_a), str(img_b_png)])
    web_dlg.edit_location.setText(str(web_out))
    web_dlg.edit_title.setText("Test Galerie")
    web_dlg._export_gallery()
    web_dlg.close()

    assert (web_out / "images" / "photo.jpg").is_file()
    assert (web_out / "images" / "photo-001.jpg").is_file()
    html_text = (web_out / "index.html").read_text(encoding="utf-8")
    assert "Belle vue de Lyon" in html_text


def test_pass9_repository_only_save_ini_get_key_contact_email_and_db_helpers(tmp_path: Path):
    """
    FR : Passe 9 — Vérifie :
    1. `PicasaDatabase.set_folder_face_exclusion()` et `save_repository_only()` :
       écriture atomique de `repository.dat`, `scanlist.txt`, `Picasa2Albums\\watchedfolders.txt`
       et `Picasa2Albums\\frexcludefolders.txt` sans lever d'AttributeError sur `repository.entries`,
       `_frexclude_folders`, `albums_dir` ou `albums_root_dir`.
    2. `PicasaIniDocument.get_key()` / `set_key()` et `PmpFile.values` alias.
    3. `Contact(id=..., name=..., email=...)` et synchronisation `[Contacts2]` dans `.picasa.ini`
       lors de la modification de l'adresse e-mail dans `PicasaContactManagerDialog`.
    4. `PicasaDatabase.get_property()`, `set_property()`, `index_single_file()`, `get_full_path()`,
       `get_albums()`, `thumbs` property, et `PicasaPhotoTray._get_item_metadata()` en mode One-Up (`str`).
    """
    import os
    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from picasa_py.db.contacts import Contact, ContactsFile
    from picasa_py.ini.parser import PicasaIniDocument, PicasaIniParser
    from picasa_py.ini.writer import PicasaIniWriter
    from picasa_py.ui.contact_manager_dialog import PicasaContactManagerDialog
    from picasa_py.ui.photo_tray import PicasaPhotoTray

    app = QApplication.instance() or QApplication([])
    assert app is not None

    root_dir = tmp_path / "PicasaRoot9"
    db = PicasaDatabase.create_new(root_dir)

    photos_dir = tmp_path / "Photos9"
    excl_dir = tmp_path / "ExcludedFaces9"
    photos_dir.mkdir(parents=True)
    excl_dir.mkdir(parents=True)

    # 1. set_watched_folder + set_folder_face_exclusion + save_repository_only
    db.set_watched_folder(str(photos_dir), "1")
    db.set_folder_face_exclusion(str(excl_dir), excluded=True)
    db.save_repository_only()

    assert (db.db3_dir / "repository.dat").is_file()
    assert (db.db3_dir / "scanlist.txt").is_file()
    assert (db.picasa2albums_dir / "watchedfolders.txt").is_file()
    assert (db.picasa2albums_dir / "frexcludefolders.txt").is_file()

    wf_content = (db.picasa2albums_dir / "watchedfolders.txt").read_text(encoding="utf-8")
    frex_content = (db.picasa2albums_dir / "frexcludefolders.txt").read_text(encoding="utf-8")
    assert str(photos_dir).replace("/", "\\") in wf_content
    assert str(excl_dir).replace("/", "\\") in frex_content

    # 2. PicasaIniDocument.get_key / set_key
    ini_doc = PicasaIniDocument()
    ini_doc.set_key("sample.jpg", "filters", "autolight=1;")
    assert ini_doc.get_key("sample.jpg", "filters") == "autolight=1;"
    assert ini_doc.get_value("sample.jpg", "filters") == "autolight=1;"
    ini_doc.set_key("sample.jpg", "filters", None)
    assert ini_doc.get_key("sample.jpg", "filters") is None

    # 3. index_single_file, get_property, set_property, get_full_path, thumbs, PmpFile.values
    img_path = photos_dir / "collage_out.jpg"
    Image.new("RGB", (320, 200), (40, 120, 220)).save(img_path, "JPEG", quality=92)
    idx = db.index_single_file(str(img_path))
    assert idx is not None and idx >= 0
    assert db.get_full_path(idx) is not None
    assert os.path.normcase(db.get_full_path(idx)) == os.path.normcase(str(img_path))
    assert db.get_property("imagedata_width", idx) == 320
    assert db.get_property("imagedata_height", idx) == 200
    db.set_property("imagedata_tags", idx, "vacances,famille")
    assert db.get_property("imagedata_tags", idx) == "vacances,famille"
    assert db.pmps["imagedata_tags"].values[idx] == "vacances,famille"
    assert "thumbs" in db.thumbs

    # PicasaPhotoTray._get_item_metadata en mode One-Up (chemin str) avec db
    tray = PicasaPhotoTray()
    tray.set_database(db)
    fname, folder_name, dt_obj, width, height, size_bytes, tags = tray._get_item_metadata(str(img_path))
    assert width == 320
    assert height == 200
    assert "vacances" in tags
    assert "famille" in tags
    tray.close()

    # 4. Contact(email=...) + PicasaContactManagerDialog._update_contact_in_xml + [Contacts2] sync
    c = Contact(id="a1b2c3d4e5f60718", name="Alice Martin", email="alice@example.com")
    assert c.email == "alice@example.com"
    assert c.extra_attrs.get("email0") == "alice@example.com"

    dlg = PicasaContactManagerDialog(db)
    dlg.current_person = db.face_manager.create_person("Alice Martin")
    cid_alice = dlg.current_person.contact_id
    dlg.current_person.photo_paths = [str(img_path)]

    ini_p = photos_dir / ".picasa.ini"
    p_doc = PicasaIniParser.parse_file(str(ini_p)) if ini_p.exists() else PicasaIniDocument()
    c2_sec = p_doc.get_or_create_section("Contacts2")
    c2_sec.set(cid_alice, "Alice Martin;;")
    PicasaIniWriter.write_file(str(ini_p), p_doc)

    dlg._update_contact_in_xml(cid_alice, "Alice Martin", "alice.new@example.com")
    dlg.close()

    saved_c = db.contacts.get(cid_alice)
    assert saved_c is not None
    assert saved_c.email == "alice.new@example.com"
    reloaded_ini = PicasaIniParser.parse_file(str(ini_p))
    assert reloaded_ini.get_key("Contacts2", cid_alice) == "Alice Martin;alice.new@example.com;"



