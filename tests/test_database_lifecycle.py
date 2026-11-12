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


def test_pass10_xml_resources_tooltips_preferences_remove_and_session_albums(tmp_path: Path):
    """
    FR: Vérifie les corrections de la passe 10 :
    1. `PicasaResourceManager.get_xml_string()` :
       - supporte les appels à 3 arguments (`get_xml_string("ABOUT", "about/window1.title", default)` dans `version.py:78`),
       - lit `type="Tooltip"` dans `TOOLTIPS*.XML` et `*TEXT*.XML` sans écraser les libellés `type="Label"`/`type="Text"`,
       - charge automatiquement les fichiers `*_TEXT_*.XML` et `*TEXT_*.XML` (`COLLAGEPANELTEXT`, `MAKEMOVIEPANELTEXT`, `PEOPLEPANEL_TEXT`, etc.),
       - résout les clés de `STRINGRES_*.XML` et les alias (`_XML_ID_ALIASES`).
    2. `PicasaPreferences.remove()` et `contains()` : permettent de nettoyer une clé de préférence.
    3. `PicasaThumbnailView.current_person_filter` : synchronisé lors de `filter_by_person()` et réinitialisé lors du retour aux dossiers/albums/favoris.
    4. Albums vides créés durant la session (`_session_created_albums`) : conservés dans `get_all_albums()` jusqu'à leur suppression par `delete_album()`.
    5. `PicasaDatabase._is_dummy_db_dir()` : ne crée aucun dossier parasite lorsque `db3_dir` contient `"__non_existent__"`.
    """
    from PySide6.QtWidgets import QApplication
    from PIL import Image
    from picasa_py.ui.resources import PicasaResourceManager
    from picasa_py.version import get_about_dialog_title, APP_NAME
    from picasa_py.db.preferences import PicasaPreferences
    from picasa_py.ui.thumbnail_view import PicasaThumbnailView
    from picasa_py.ini.parser import PicasaIniDocument

    _app = QApplication.instance() or QApplication([])

    # 1. XML resources & tooltips
    res_mgr = PicasaResourceManager()
    res_mgr.set_language("fr")
    about_title_fr = get_about_dialog_title(res_mgr)
    assert APP_NAME in about_title_fr and "propos" in about_title_fr.lower()

    res_mgr.set_language("en")
    about_title_en = get_about_dialog_title(res_mgr)
    assert APP_NAME in about_title_en and "about" in about_title_en.lower()

    res_mgr.set_language("fr")
    assert res_mgr.get_xml_string("editpanel/tab1.tooltip", "") != ""
    assert res_mgr.get_xml_string("editpanel/crop.tooltip", "") != ""
    assert res_mgr.get_xml_string("collagepanel/scramble.title", "") != ""
    assert res_mgr.get_xml_string("makemoviepanel/create.title", "") != ""
    assert res_mgr.get_xml_string("peoplepanel/add_person", "") != ""
    assert res_mgr.get_xml_string("AlbumPhoto::ID_PICTURE_VIEW", "") != ""
    assert res_mgr.get_xml_string("STRINGRES", "IDS_LISTUPDATED", "") != ""

    # 2. PicasaPreferences.remove() & contains()
    prefs = PicasaPreferences(db3_dir=tmp_path / "db3_prefs10")
    test_key = "Pass10TestTempKey"
    prefs.setValue(test_key, 42)
    assert prefs.contains(test_key) is True
    prefs.remove(test_key)
    assert prefs.contains(test_key) is False

    # 3. PicasaThumbnailView.current_person_filter
    tv = PicasaThumbnailView()
    assert tv.current_person_filter is None
    tv.filter_by_person("06e55417b6930726", "Alice", [])
    assert tv.current_person_filter == "06e55417b6930726"
    tv.filter_by_starred()
    assert tv.current_person_filter is None
    tv.close()
    tv.deleteLater()
    _app.processEvents()

    # 4. Session-created empty album visibility & deletion
    db = PicasaDatabase.create_new(tmp_path / "PicasaRoot10")
    photos_dir = tmp_path / "Photos10"
    photos_dir.mkdir(parents=True)
    img_p = photos_dir / "photo10.jpg"
    Image.new("RGB", (64, 64), (100, 150, 200)).save(img_p, "JPEG")
    db.set_watched_folder(str(photos_dir), "1")
    db.index_single_file(str(img_p))

    doc = PicasaIniDocument()
    sec = doc.get_or_create_section(".album:deadbeef12345678")
    sec.set("name", "Mon Album Vide")
    sec.set("token", "deadbeef12345678")
    db._sync_album_sections_from_ini_doc(doc)

    albs = db.get_all_albums()
    tokens = {a["token"] for a in albs}
    assert "deadbeef12345678" in tokens

    db.delete_album("deadbeef12345678")
    albs_after = db.get_all_albums()
    assert "deadbeef12345678" not in {a["token"] for a in albs_after}

    # 5. Dummy db_dir guard
    dummy_db = PicasaDatabase(db3_dir=tmp_path / "__non_existent__")
    dummy_db.save_database()
    assert not (tmp_path / "__non_existent__").exists()


def test_pass11_file_stat_checksums_and_contacts_backup_sync(tmp_path: Path) -> None:
    """
    FR: Vérifie les corrections de la onzième passe d'audit Ghidra vs PyCasa :
    1. `sync_file_stat_and_checksums()` met à jour `ft2`, `size`, `imagedata_filesize.pmp` et les checksums
       32 bits de `thumbs_index.db`, `thumbs2_index.db`, `bigthumbs_index.db` et `previews_index.db`
       (y compris les visages enfants `1001`) lors de l'injection IPTC (`set_caption` / `set_keywords`)
       et de l'injection XMP (`PicasaXMPFaceTagger` / `PicasaWriteFaceTagsWorker`).
    2. `update_thumbnails_from_pil()` utilise `_fit_long_side` (`0x009B4AA0`) avec la cascade `288 -> 144 -> 72`,
       calcule `imagedata_avgcolor` via `compute_thumbnail_avgcolor(thumb_144)` (`0x009AC640`) et met à jour
       les jetons `]color:...` dans `wordhash.dat` (`0x007BC810`).
    3. `PicasaFaceManager` (`create_person`, `rename_person`, `delete_person`) appelle `db.save_contacts()`
       pour synchroniser à la fois `contacts/contacts.xml` et `Picasa2Albums/<db_guid>/backup.xml` (`0x0066F2B0`).
    """
    from PIL import Image
    from picasa_py.db.blockfile import compute_thumb_checksum
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.faces.xmp_tagger import PicasaXMPFaceTagger
    from picasa_py.scanner.scanner import _scale_box_dimensions, compute_thumbnail_avgcolor

    db = PicasaDatabase.create_new(tmp_path / "PicasaRoot11")
    photos_dir = tmp_path / "Photos11"
    photos_dir.mkdir(parents=True)
    img_p = photos_dir / "photo11.jpg"
    Image.new("RGB", (400, 300), (220, 40, 40)).save(img_p, "JPEG", quality=92)

    db.set_watched_folder(str(photos_dir), "1")
    idx = db.index_single_file(str(img_p))
    assert idx is not None and idx >= 0

    # Ajouter un visage sur la photo pour créer un sous-enregistrement 1001 et synchroniser contacts/backup.xml
    fm = db.face_manager
    fr = FaceRect(left=0.2, top=0.2, right=0.6, bottom=0.6)
    fm.add_face(str(img_p), fr, "Clara", db_idx=idx)
    child_1001 = db._get_face_children(idx)
    assert len(child_1001) == 1
    c_idx = child_1001[0]

    # 1. Vérifier que set_caption (qui injecte IPTC APP13 dans le JPEG) met à jour ft2, size, imagedata_filesize
    # et les checksums de thumbs_index.db / thumbs2_index.db pour la photo et son enfant 1001
    assert db.set_caption(idx, "Légende IPTC Pass 11") is True
    rec = db.thumbindex.records[idx]
    folder_path = db.thumbindex.records[rec.parent_idx].path
    expected_cs = compute_thumb_checksum(folder_path, rec.path, rec.ft2, rec.size)
    assert rec.size == img_p.stat().st_size
    assert db.block_indices["thumbs"].checksums[idx] == expected_cs
    assert db.block_indices["thumbs2"].checksums[idx] == expected_cs
    assert db.block_indices["thumbs"].checksums[c_idx] == expected_cs

    # Tester aussi après injection XMP + sync_file_stat_and_checksums
    xmp_bytes = PicasaXMPFaceTagger.build_xmp_packet(400, 300, [("Clara", 0.2, 0.2, 0.6, 0.6)])
    assert PicasaXMPFaceTagger.inject_xmp_into_jpeg(str(img_p), xmp_bytes) is True
    assert db.sync_file_stat_and_checksums(str(img_p)) is True
    rec_after_xmp = db.thumbindex.records[idx]
    expected_cs_xmp = compute_thumb_checksum(folder_path, rec_after_xmp.path, rec_after_xmp.ft2, rec_after_xmp.size)
    assert db.block_indices["thumbs"].checksums[idx] == expected_cs_xmp
    assert db.block_indices["thumbs"].checksums[c_idx] == expected_cs_xmp

    # 2. Vérifier update_thumbnails_from_pil : _scale_box_dimensions, compute_thumbnail_avgcolor et color:gray
    bw_img = Image.new("RGB", (500, 333), (128, 128, 128))
    assert db.update_thumbnails_from_pil(idx, bw_img, persist_to_disk=False) is True
    tw288, th288 = _scale_box_dimensions(500, 333, 288)
    tw144, th144 = _scale_box_dimensions(tw288, th288, 144)
    expected_avg = compute_thumbnail_avgcolor(
        bw_img.resize((tw288, th288), Image.Resampling.BILINEAR).resize((tw144, th144), Image.Resampling.BILINEAR)
    )
    assert db.pmps["imagedata_avgcolor"].records[idx] == expected_avg
    assert idx in db.search("color:gray")
    assert idx not in db.search("color:red")

    # 3. Vérifier que rename_person et delete_person synchronisent Picasa2Albums/<db_guid>/backup.xml
    guid_dir = db.picasa2albums_dir / "11223344556677889900aabbccddeeff"
    guid_dir.mkdir(parents=True, exist_ok=True)
    clara_clusters = [p for p in fm.people.values() if p.name == "Clara"]
    assert len(clara_clusters) == 1
    cid = clara_clusters[0].contact_id
    assert fm.rename_person(cid, "Clara Renommée") is True
    backup_xmls = list(db.picasa2albums_dir.rglob("backup.xml"))
    assert len(backup_xmls) == 1
    assert "Clara Renommée" in backup_xmls[0].read_text(encoding="utf-8")

    assert fm.delete_person(cid) is True
    assert "Clara Renommée" not in backup_xmls[0].read_text(encoding="utf-8")


def test_pass12_redo_stack_revert_move_and_originals_parity(tmp_path: Path):
    """
    FR: Vérifie les corrections de la passe 12 :
    1. Pile `redo=` dans `PicasaIniDocument` (`get_redo`, `set_redo`, `undo_last_filter` @ `0x006AD860`,
       `redo_next_filter` @ `0x006AE280`, exclusion `redeye`/`retouch`/`picnik` @ `0x00846900`, et
       vidage automatique de `redo=` lors d'un nouveau filtre / recadrage / redressement @ `0x0045FF60`),
       et synchronisation avec `imagedata_redo.pmp`.
    2. Fallback legacy `Originals/` aux côtés de `.picasaoriginals/` (`0x00462BA0`) pour `imagedata_revertable`,
       `move_photo`, `rename_photo` et `delete_photo(delete_from_disk=True)` (suppression du backup orphelin).
    3. `move_photo` et `move_folder` : mise à jour des checksums `CBlockFile` sur les 4 index (`thumbs`,
       `thumbs2`, `bigthumbs`, `previews`) et mise à jour des jetons de dossier dans `wordhash.db`.
    """
    from PIL import Image
    from picasa_py.ini.parser import PicasaIniDocument
    from picasa_py.scanner.scanner import PicasaDirScanner
    from picasa_py.db.blockfile import compute_thumb_checksum

    # 1. Test unitaire de la pile filters= <-> redo= dans PicasaIniDocument
    doc = PicasaIniDocument()
    doc.append_filter("photo.jpg", "autolight=1")
    doc.append_filter("photo.jpg", "sepia=1")
    doc.append_filter("photo.jpg", "crop64=1,20002000e000e000")
    doc.set_crop("photo.jpg", "20002000e000e000")
    doc.append_filter("photo.jpg", "redeye=1,1234")
    assert doc.get_filters("photo.jpg") == [
        "autolight=1",
        "sepia=1",
        "crop64=1,20002000e000e000",
        "redeye=1,1234",
    ]
    # Annuler redeye : retiré de filters=, mais PAS ajouté à redo= (0x00846900)
    assert doc.undo_last_filter("photo.jpg") == "redeye=1,1234"
    assert doc.get_redo("photo.jpg") == []
    # Annuler crop64 : retiré de filters=, crop= supprimé, et ajouté à redo= (0x006AD860)
    assert doc.undo_last_filter("photo.jpg") == "crop64=1,20002000e000e000"
    assert doc.get_crop("photo.jpg") is None
    assert doc.get_redo("photo.jpg") == ["crop64=1,20002000e000e000"]
    # Annuler sepia=1 : empilé à la fin de redo=
    assert doc.undo_last_filter("photo.jpg") == "sepia=1"
    assert doc.get_redo("photo.jpg") == ["crop64=1,20002000e000e000", "sepia=1"]
    # Rétablir : dépile sepia=1 puis crop64 (et restaure crop=rect64(...)) (0x006AE280)
    assert doc.redo_next_filter("photo.jpg") == "sepia=1"
    assert doc.get_filters("photo.jpg") == ["autolight=1", "sepia=1"]
    assert doc.redo_next_filter("photo.jpg") == "crop64=1,20002000e000e000"
    assert doc.get_crop("photo.jpg") == "20002000e000e000"
    assert doc.get_redo("photo.jpg") == []
    # Un nouveau filtre vide redo= (0x0045FF60)
    doc.undo_last_filter("photo.jpg")
    assert len(doc.get_redo("photo.jpg")) == 1
    doc.append_filter("photo.jpg", "bw=1")
    assert doc.get_redo("photo.jpg") == []

    # 2 & 3. Test base de données : imagedata_redo, legacy Originals/, move_photo, move_folder et delete_photo
    db_dir = tmp_path / "db3_pass12"
    contacts_dir = tmp_path / "contacts_pass12"
    folder_a = tmp_path / "DossierAlphaUnique"
    folder_b = tmp_path / "DossierBetaUnique"
    folder_c = tmp_path / "DossierGammaUnique"
    folder_a.mkdir(parents=True, exist_ok=True)
    folder_b.mkdir(parents=True, exist_ok=True)

    img_p = folder_a / "vacances.jpg"
    Image.new("RGB", (320, 240), (60, 120, 200)).save(img_p, "JPEG")
    # Créer une sauvegarde dans le dossier legacy Originals/ (0x00462BA0)
    legacy_orig_dir = folder_a / "Originals"
    legacy_orig_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (320, 240), (50, 100, 180)).save(legacy_orig_dir / "vacances.jpg", "JPEG")

    db = PicasaDatabase.create_new(db_dir, contacts_dir)
    db.set_watched_folder(str(folder_a), "1")
    db.set_watched_folder(str(folder_b), "1")
    scanner = PicasaDirScanner(db)
    scanner.scan_directory(folder_a)

    idx = db.find_photo_index(str(img_p))
    assert idx is not None and idx >= 0
    # Sans section INI mais avec Originals/vacances.jpg, imagedata_revertable doit valoir 1
    db.sync_photo_ini_to_db(str(img_p))
    assert db.pmps["imagedata_revertable"].records[idx] == 1

    # Appliquer deux filtres puis annuler le dernier via update_photo_ini -> imagedata_redo synchronisé
    db.update_photo_ini(str(img_p), lambda d, fn: (d.append_filter(fn, "autolight=1"), d.append_filter(fn, "sepia=1")))
    assert db.pmps["imagedata_filters"].records[idx] == "autolight=1;sepia=1;"
    assert db.pmps["imagedata_redo"].records[idx] == ""
    db.update_photo_ini(str(img_p), lambda d, fn: d.undo_last_filter(fn))
    assert db.pmps["imagedata_filters"].records[idx] == "autolight=1;"
    assert db.pmps["imagedata_redo"].records[idx] == "sepia=1;"

    # Simuler des checksums non nuls dans bigthumbs et previews en plus de thumbs/thumbs2
    for pref in ("thumbs", "thumbs2", "bigthumbs", "previews"):
        if pref in db.block_indices and idx < len(db.block_indices[pref].checksums):
            db.block_indices[pref].checksums[idx] = 0x12345678

    # Déplacer la photo de folder_a vers folder_b : Originals/vacances.jpg est déplacé,
    # les 4 checksums CBlockFile et wordhash sont mis à jour
    assert idx in db.search("dossieralphaunique")
    assert db.move_photo(idx, folder_b) is True
    moved_p = folder_b / "vacances.jpg"
    assert moved_p.exists()
    assert (folder_b / "Originals" / "vacances.jpg").exists()
    assert not (folder_a / "Originals" / "vacances.jpg").exists()
    assert idx not in db.search("dossieralphaunique")
    assert idx in db.search("dossierbetaunique")

    rec = db.thumbindex.records[idx]
    folder_b_win = db.thumbindex.records[rec.parent_idx].path
    expected_cs_b = compute_thumb_checksum(folder_b_win, rec.path, rec.ft2, rec.size)
    for pref in ("thumbs", "thumbs2", "bigthumbs", "previews"):
        if pref in db.block_indices and idx < len(db.block_indices[pref].checksums):
            assert db.block_indices[pref].checksums[idx] == expected_cs_b

    # Déplacer le dossier folder_b -> folder_c : wordhash et les 4 checksums sont mis à jour
    folder_b.rename(folder_c)
    assert db.move_folder(str(folder_b), str(folder_c)) is True
    assert idx not in db.search("dossierbetaunique")
    assert idx in db.search("dossiergammaunique")
    rec = db.thumbindex.records[idx]
    folder_c_win = db.thumbindex.records[rec.parent_idx].path
    expected_cs_c = compute_thumb_checksum(folder_c_win, rec.path, rec.ft2, rec.size)
    for pref in ("thumbs", "thumbs2", "bigthumbs", "previews"):
        if pref in db.block_indices and idx < len(db.block_indices[pref].checksums):
            assert db.block_indices[pref].checksums[idx] == expected_cs_c

    # Supprimer la photo du disque : supprime aussi la sauvegarde Originals/vacances.jpg
    assert db.delete_photo(idx, delete_from_disk=True) is True
    assert not (folder_c / "vacances.jpg").exists()
    assert not (folder_c / "Originals" / "vacances.jpg").exists()


def test_pass13_wordhash_token_removal_filters_and_album_pal_parity(tmp_path: Path) -> None:
    """
    FR: Vérifie les corrections de la 13e passe d'audit picasa3.exe vs PyCasa :
    1. Suppression effective des anciens jetons dans `wordhash.db` lorsque des mots-clés (`remove_keyword`),
       une légende (`set_caption("")`) ou un texte actif (`textactive=0`) sont modifiés ou retirés (`0x004D9AA0`).
    2. Indexation du texte décodé de `CTextItemList` sans polluer `wordhash.db` avec la police (`Arial`) ou `v1`.
    3. Rendu des clés historiques `fix=1` et `bw=1` dans `PicasaImageProcessor.load_transformed_image` (`0x00456A15`)
       et désactivation du rendu de `text=` lorsque `textactive=0`.
    4. Prise en compte des coordonnées `(cx, cy)` dans `focal_pixelate` et `focal_zoom` (`0x008FADDE`)
       et mise à l'échelle exacte de `border` pour `inner_pct=1.0` et `0.0`.
    5. Mise à jour du fichier `.pal` dans `Picasa2Albums/<db_guid>/<uid>.pal` lors de `db.rename_album` (`0x008AAD76`).
    """
    from PIL import Image
    import numpy as np
    from picasa_py.ui.image_processor import PicasaImageProcessor
    from picasa_py.ini.parser import PicasaIniParser

    db3_dir = tmp_path / "db3_pass13"
    contacts_dir = tmp_path / "contacts_pass13"
    folder = tmp_path / "PhotosPass13"
    folder.mkdir(parents=True, exist_ok=True)

    photo_p = folder / "color_test.jpg"
    img = Image.new("RGB", (60, 60), (220, 40, 90))
    img.save(photo_p, format="JPEG", quality=95)

    db = PicasaDatabase.create_new(db3_dir, contacts_dir)
    db.set_watched_folder(str(folder), "1")
    PicasaDirScanner(db).scan_directory(folder)
    idx = db.find_photo_index(str(photo_p))
    assert idx is not None

    # 1. Ajout puis suppression de mots-clés et de légende : les anciens jetons doivent disparaître de wordhash.db
    assert db.add_keyword(idx, "montagneunique") is True
    assert db.add_keyword(idx, " glacierunique ") is True
    assert idx in db.search("montagneunique")
    assert idx in db.search("glacierunique")

    assert db.remove_keyword(idx, "montagneunique") is True
    assert idx not in db.search("montagneunique")
    assert idx in db.search("glacierunique")

    assert db.set_caption(idx, "legendeephemere") is True
    assert idx in db.search("legendeephemere")
    assert db.set_caption(idx, "") is True
    assert idx not in db.search("legendeephemere")

    # 2. Texte CTextItemList : seul le texte décodé actif est indexé dans wordhash.db
    ini_path = folder / ".picasa.ini"
    doc = PicasaIniParser.parse_file(str(ini_path))
    sec = doc.get_or_create_section("color_test.jpg")
    sec.set("text", "1;11;Bonjourtous;Arial;0.150000,0.850000,0.080000,0.000000;v1,400,0,128.000000,0.100000,1.000000,1.000000,ff000000,ffffffff,1;")
    sec.set("textactive", "1")
    doc.write_file(str(ini_path))
    db.invalidate_ini_cache(str(ini_path))
    db.sync_photo_ini_to_db(str(photo_p))

    assert idx in db.search("bonjourtous")
    assert idx not in db.search("arial")

    # Désactivation via textactive=0 : le jeton de texte est retiré de wordhash.db
    doc = PicasaIniParser.parse_file(str(ini_path))
    doc.get_or_create_section("color_test.jpg").set("textactive", "0")
    doc.write_file(str(ini_path))
    db.invalidate_ini_cache(str(ini_path))
    db.sync_photo_ini_to_db(str(photo_p))
    assert idx not in db.search("bonjourtous")

    # 3. Legacy bw=1 dans .picasa.ini sans filters= -> rendu en niveaux de gris par load_transformed_image
    doc = PicasaIniParser.parse_file(str(ini_path))
    sec = doc.get_or_create_section("color_test.jpg")
    sec.set("bw", "1")
    doc.write_file(str(ini_path))
    rendered_bw = PicasaImageProcessor.load_transformed_image(str(photo_p))
    assert rendered_bw is not None
    arr_bw = np.array(rendered_bw)
    assert np.allclose(arr_bw[:, :, 0], arr_bw[:, :, 1], atol=2)
    assert np.allclose(arr_bw[:, :, 1], arr_bw[:, :, 2], atol=2)

    # 4. Vérifier focal_zoom avec cx/cy décentrés et border avec inner_pct=1.0 / 0.0
    grad_arr = np.zeros((80, 80, 3), dtype=np.uint8)
    grad_arr[:40, :40] = (255, 0, 0)
    grad_arr[:40, 40:] = (0, 255, 0)
    grad_arr[40:, :40] = (0, 0, 255)
    grad_arr[40:, 40:] = (255, 255, 0)
    grad_img = Image.fromarray(grad_arr)

    fz_tl = PicasaImageProcessor.apply_filter_chain(grad_img, "FocalZoom=1,0.1,0.1,50.0,0.2,50.0;")
    fz_br = PicasaImageProcessor.apply_filter_chain(grad_img, "FocalZoom=1,0.9,0.9,50.0,0.2,50.0;")
    assert not np.array_equal(np.array(fz_tl), np.array(fz_br))

    fp_tl = PicasaImageProcessor.execute_effect(grad_img, "focal_pixelate", {"block_size": 16, "size": 0.25, "hardness": 80, "cx": 0.15, "cy": 0.15})
    fp_br = PicasaImageProcessor.execute_effect(grad_img, "focal_pixelate", {"block_size": 16, "size": 0.25, "hardness": 80, "cx": 0.85, "cy": 0.85})
    assert not np.array_equal(np.array(fp_tl), np.array(fp_br))

    b_img = PicasaImageProcessor.apply_filter_chain(grad_img, "Border=1,10.0,1.0,0.0,001a1a1a,00ffffff;")
    # 10.0 / 200.0 * 80 = 4 px outer, 1.0 / 200.0 * 80 = 1 px inner -> 80 + 2*(4+1) = 90
    assert b_img.size == (90, 90)
    b_zero_in = PicasaImageProcessor.apply_filter_chain(grad_img, "Border=1,10.0,0.0,0.0,001a1a1a,00ffffff;")
    assert b_zero_in.size == (88, 88)

    # 5. Renommage d'album met aussi à jour le fichier .pal dans Picasa2Albums/<db_guid>/<uid>.pal
    alb_tok = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    doc = PicasaIniParser.parse_file(str(ini_path))
    alb_sec = doc.get_or_create_section(f".album:{alb_tok}")
    alb_sec.set("name", "Ancien Nom")
    alb_sec.set("token", alb_tok)
    doc.write_file(str(ini_path))
    db.invalidate_ini_cache(str(ini_path))
    db.sync_photo_ini_to_db(str(photo_p))

    guid_dir = db.picasa2albums_dir / "test_guid"
    guid_dir.mkdir(parents=True, exist_ok=True)
    pal_file = guid_dir / f"{alb_tok}.pal"
    pal_file.write_text(
        '<picasa2album>\n  <property name="name" type="string" value="Ancien Nom"/>\n  <name>Ancien Nom</name>\n</picasa2album>\n',
        encoding="utf-8",
    )

    assert db.rename_album(alb_tok, "Nouveau Nom Pass13") is True
    updated_pal = pal_file.read_text(encoding="utf-8")
    assert 'value="Nouveau Nom Pass13"' in updated_pal
    assert "<name>Nouveau Nom Pass13</name>" in updated_pal


def test_pass14_edited_scan_thumbnails_legacy_ini_and_clean_traces_parity(tmp_path):
    """
    FR: Vérifie les corrections de la 14e passe d'audit picasa3.exe vs PyCasa :
    1. Une photo indexée par `PicasaDirScanner` dans un dossier dont `.picasa.ini` ou `Picasa.ini`
       contient déjà des retouches (`imagedata_edited != 0`, ex. `filters= Invert=1;`) génère ses
       miniatures (`thumbs_0.db`, `thumbs2_0.db`), `imagedata_avgcolor` et ses jetons `color:*`
       dans `wordhash.db` à partir de l'image transformée (`0x00456A15` -> `0x00425210`).
    2. Les méthodes `sync_photo_ini_to_db`, `get_rotate`, `is_starred`, `get_caption`, `get_tags`,
       `get_starred_photo_paths` et `get_all_albums` basculent sur `Picasa.ini` lorsque `.picasa.ini`
       est absent (`0x0068AC80`), incluent `description`/`location`/`uid` dans `get_all_albums`,
       fusionnent les métadonnées `[.album:<tok>]` multi-dossiers sans écraser les champs non vides,
       et excluent les photos masquées (`hidden=yes|1|true`) des albums.
    3. `clean_picasa_ini_traces` resynchronise toutes les colonnes `imagedata_*` et les jetons
       `wordhash.db` (`]star`, `]edited`, mots-clés, légendes) après suppression des `.picasa.ini` / `Picasa.ini`.
    """
    import io
    import numpy as np
    from PIL import Image
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.scanner.scanner import PicasaDirScanner

    db_dir = tmp_path / "db3_pass14"
    contacts_dir = tmp_path / "contacts_pass14"
    db = PicasaDatabase.create_new(db_dir, contacts_dir)

    folder1 = tmp_path / "PhotosPass14_A"
    folder1.mkdir(parents=True, exist_ok=True)
    folder2 = tmp_path / "PhotosPass14_B"
    folder2.mkdir(parents=True, exist_ok=True)

    # 1. Créer une photo rouge pur (255, 0, 0) mais pré-configurée avec Invert=1; dans Picasa.ini (sans .picasa.ini)
    # L'image inversée est cyan (0, 255, 255).
    red_photo = folder1 / "edited_red.jpg"
    Image.new("RGB", (64, 64), (255, 0, 0)).save(str(red_photo), format="JPEG", quality=95)

    hidden_photo = folder1 / "hidden_pic.jpg"
    Image.new("RGB", (64, 64), (0, 255, 0)).save(str(hidden_photo), format="JPEG", quality=95)

    alb_tok = "f1e2d3c4b5a69788796a5b4c3d2e1f00"
    legacy_ini = folder1 / "Picasa.ini"
    legacy_ini.write_text(
        f"[.album:{alb_tok}]\r\n"
        f"name=Album Multi Dossier\r\n"
        f"token={alb_tok}\r\n"
        f"description=Description dossier A\r\n"
        f"location=Paris\r\n"
        f"[edited_red.jpg]\r\n"
        f"rotate=rotate(1)\r\n"
        f"star=1\r\n"
        f"caption=LegendeLegacyIni\r\n"
        f"keywords=TagLegacyUn,TagLegacyDeux\r\n"
        f"filters=Invert=1;\r\n"
        f"albums={alb_tok}\r\n"
        f"[hidden_pic.jpg]\r\n"
        f"hidden=true\r\n"
        f"star=yes\r\n"
        f"albums={alb_tok}\r\n",
        encoding="utf-8",
    )

    # Second dossier référençant le même album mais avec une section [.album:<tok>] minimaliste sans description/location
    photo_b = folder2 / "second.jpg"
    Image.new("RGB", (64, 64), (0, 0, 255)).save(str(photo_b), format="JPEG", quality=95)
    (folder2 / ".picasa.ini").write_text(
        f"[.album:{alb_tok}]\r\n"
        f"token={alb_tok}\r\n"
        f"[second.jpg]\r\n"
        f"albums={alb_tok}\r\n",
        encoding="utf-8",
    )

    scanner = PicasaDirScanner(db)
    scanner.scan_directory(folder1)
    scanner.scan_directory(folder2)

    idx_red = db.find_photo_index(str(red_photo))
    idx_hid = db.find_photo_index(str(hidden_photo))
    assert idx_red is not None
    assert idx_hid is not None

    # Vérifier la lecture depuis Picasa.ini (sans .picasa.ini)
    assert db.get_rotate(idx_red) == 1
    assert db.is_starred(idx_red) is True
    assert db.get_caption(idx_red) == "LegendeLegacyIni"
    assert db.get_tags(idx_red) == ["TagLegacyUn", "TagLegacyDeux"]
    assert idx_red in db.search("legendelegacyini")
    assert idx_red in db.search("taglegacyun")
    assert idx_red in db.search("]star")
    assert idx_red in db.search("]edited")

    # Vérifier que la miniature stockée dans thumbs_0.db reflète bien l'image inversée (cyan : R < 30, G > 200, B > 200)
    thumb_bytes = db.get_thumbnail(idx_red, size="small")
    assert thumb_bytes is not None
    with Image.open(io.BytesIO(thumb_bytes)) as t_img:
        arr = np.array(t_img.convert("RGB"))
        assert float(arr[:, :, 0].mean()) < 30.0
        assert float(arr[:, :, 1].mean()) > 200.0
        assert float(arr[:, :, 2].mean()) > 200.0

    # Vérifier que get_all_albums préserve le nom, la description et le lieu de l'album multi-dossiers
    # et exclut la photo masquée (hidden=true)
    all_albs = {a["token"]: a for a in db.get_all_albums()}
    assert alb_tok in all_albs
    alb_entry = all_albs[alb_tok]
    assert alb_entry["name"] == "Album Multi Dossier"
    assert alb_entry["description"] == "Description dossier A"
    assert alb_entry["location"] == "Paris"
    assert idx_red in alb_entry["photo_indices"]
    assert idx_hid not in alb_entry["photo_indices"]

    # Vérifier que get_starred_photo_paths inclut edited_red.jpg (star=1) et exclut hidden_pic.jpg (hidden=true)
    starred_norms = {p.lower() for p in db.get_starred_photo_paths()}
    assert str(red_photo).lower() in starred_norms
    assert str(hidden_photo).lower() not in starred_norms

    # 3. Nettoyage des traces INI : doit purger imagedata_* et wordhash.db pour les dossiers nettoyés
    deleted, failed = db.clean_picasa_ini_traces(folder1, include_legacy_picasa_ini=True)
    assert len(deleted) == 1
    assert not failed
    assert db.is_starred(idx_red) is False
    assert db.get_rotate(idx_red) == 0
    assert db.get_caption(idx_red) == ""
    assert db.get_tags(idx_red) == []
    assert idx_red not in db.search("]star")
    assert idx_red not in db.search("]edited")
    assert idx_red not in db.search("legendelegacyini")
    assert idx_red not in db.search("taglegacyun")


def test_pass15_move_rename_photo_folder_legacy_ini_and_thumb_save_parity(tmp_path):
    """
    FR: Vérifie les corrections de la 15e passe d'audit picasa3.exe vs PyCasa :
    1. `update_photo_ini` préserve les sections existantes d'un fichier historique `Picasa.ini`
       lorsqu'il écrit `.picasa.ini` (`0x0068AC80`).
    2. `move_photo` transfère également les définitions `[.album:<tok>]` référencées par `albums=`,
       bascule le jeton d'album de dossier `]album:<folder_uid>` dans `wordhash.db`, préserve les
       termes partagés (légende/tags/nom) et maintient `compute_preview_checksum` (`0x006B9B26`)
       sur `bigthumbs` / `previews`.
    3. `rename_photo` et `move_folder` préservent les jetons de légende/tags dans `wordhash.db`,
       maintiennent `compute_preview_checksum` sur `bigthumbs` / `previews`, et `move_folder`
       met à jour `albumdata_name` lorsque le titre du dossier correspondait à l'ancien basename.
    4. `save_thumbnails_only` persiste `wordhash.dat` sur disque après mise à jour des jetons
       `color:*` par `update_thumbnails_from_pil`.
    """
    from PIL import Image
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.ini.parser import PicasaIniParser
    from picasa_py.scanner.scanner import PicasaDirScanner
    from picasa_py.db.wordhash import WordHashFile

    db_dir = tmp_path / "db3_pass15"
    contacts_dir = tmp_path / "contacts_pass15"
    db = PicasaDatabase.create_new(db_dir, contacts_dir)

    src_folder = tmp_path / "DossierSource"
    src_folder.mkdir(parents=True, exist_ok=True)
    dest_folder = tmp_path / "DossierDest"
    dest_folder.mkdir(parents=True, exist_ok=True)

    p1 = src_folder / "vacances_soleil.jpg"
    p2 = src_folder / "autre_photo.jpg"
    Image.new("RGB", (64, 64), (255, 0, 0)).save(str(p1), format="JPEG", quality=95)
    Image.new("RGB", (64, 64), (0, 255, 0)).save(str(p2), format="JPEG", quality=95)

    alb_tok = "11223344556677889900aabbccddeeff"
    legacy_ini = src_folder / "Picasa.ini"
    legacy_ini.write_text(
        f"[.album:{alb_tok}]\r\n"
        f"name=Album Soleil\r\n"
        f"token={alb_tok}\r\n"
        f"[vacances_soleil.jpg]\r\n"
        f"albums={alb_tok}\r\n"
        f"caption= dossiersource vacances\r\n"
        f"[autre_photo.jpg]\r\n"
        f"star=yes\r\n",
        encoding="utf-8",
    )

    scanner = PicasaDirScanner(db)
    scanner.scan_directory(src_folder)

    idx1 = db.find_photo_index(str(p1))
    idx2 = db.find_photo_index(str(p2))
    assert idx1 is not None
    assert idx2 is not None

    # 1. update_photo_ini sur un dossier ayant uniquement Picasa.ini doit préserver [autre_photo.jpg] et [.album:...]
    assert db.set_tags(idx1, ["Plage", "Soleil"]) is True
    dot_ini = src_folder / ".picasa.ini"
    assert dot_ini.exists()
    parsed_dot = PicasaIniParser.parse_file(str(dot_ini))
    assert parsed_dot.is_starred("autre_photo.jpg") is True
    assert parsed_dot.get_section(f".album:{alb_tok}") is not None

    # 2. move_photo vers dest_folder transfère [.album:<tok>], met à jour ]album:<folder_uid> et conserve le mot 'dossiersource' de la légende
    src_folder_tok = db.ensure_folder_album_row(str(src_folder))
    assert idx1 in db.search(src_folder_tok)
    assert db.move_photo(idx1, dest_folder) is True

    dest_dot_ini = dest_folder / ".picasa.ini"
    assert dest_dot_ini.exists()
    dest_doc = PicasaIniParser.parse_file(str(dest_dot_ini))
    dest_alb_sec = dest_doc.get_section(f".album:{alb_tok}")
    assert dest_alb_sec is not None
    assert dest_alb_sec.get("name") == "Album Soleil"

    dest_folder_tok = db.ensure_folder_album_row(str(dest_folder))
    assert idx1 not in db.search(src_folder_tok)
    assert idx1 in db.search(dest_folder_tok)
    # Le mot 'dossiersource' est dans la légende de idx1 : il ne doit pas avoir été supprimé de wordhash !
    assert idx1 in db.search("dossiersource")

    # Simuler un checksum non nul dans previews_index.db et vérifier que rename_photo maintient compute_entry_checksum("previews")
    prev_idx_f = db.block_indices.get("previews")
    if prev_idx_f is not None and idx1 < len(prev_idx_f.checksums):
        prev_idx_f.checksums[idx1] = 123456

    # 3. rename_photo préserve le mot 'soleil' (présent dans les tags) et met à jour le checksum CBlockFile
    assert db.rename_photo(idx1, "plage_ete.jpg") is True
    assert idx1 in db.search("soleil")
    assert idx1 in db.search("plage")
    if prev_idx_f is not None and idx1 < len(prev_idx_f.checksums):
        assert prev_idx_f.checksums[idx1] == db.compute_entry_checksum(idx1, "thumbs")

    # Déplacer physiquement dest_folder -> renamed_folder et appeler move_folder
    renamed_folder = tmp_path / "DossierRenomme"
    dest_folder.rename(renamed_folder)
    assert db.move_folder(str(dest_folder), str(renamed_folder)) is True
    ad_names = db.pmps.get("albumdata_name")
    assert ad_names is not None
    assert "DossierRenomme" in ad_names.records

    # 4. update_thumbnails_from_pil(..., persist_to_disk=True) sauvegarde aussi wordhash.dat sur disque via save_thumbnails_only
    blue_img = Image.new("RGB", (64, 64), (0, 0, 255))
    assert db.update_thumbnails_from_pil(idx1, blue_img, persist_to_disk=True) is True
    wh_on_disk = WordHashFile.from_bytes((db_dir / "wordhash.dat").read_bytes())
    assert idx1 in wh_on_disk.words.get("color:blue", set())


def test_pass16_face_avatar_geo_invalidation_person_search_and_geotag_lifecycle(tmp_path):
    """
    FR : Test de régression de la 16e passe d'audit `picasa3.exe` vs `PyCasa` :
    1. `PicasaFaceManager.add_face` / `rename_person` / `remove_face` sur un dossier ayant
       uniquement `Picasa.ini` préserve toutes les sections héritées lors de l'écriture de `.picasa.ini`.
    2. `PicasaDatabase.search()` résout les enregistrements enfants `type == 1001` vers leur photo
       parente et est invalidé par `notify_people_changed()` lors d'un renommage de personne.
    3. `sync_photo_ini_to_db` propage `imagedata_rotate` aux enfants `1001` et invalide `_avatar_cache`
       (`("face_1001", ...)` et `("person_avatar", ...)`) ainsi que `_updated_thumb_indices` ;
       `update_thumbnails_from_pil` évince également ces clés du cache d'avatars.
    4. `set_geotag`, `get_geotag` et `clear_geotag` synchronisent `.picasa.ini`, `imagedata_lat` /
       `imagedata_long` et le jeton `]geo` dans `wordhash.dat`.
    """
    from PIL import Image
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.faces.face_manager import FaceRect, PicasaFaceManager
    from picasa_py.ini.parser import PicasaIniParser
    from picasa_py.scanner.scanner import PicasaDirScanner

    db_dir = tmp_path / "db3_pass16"
    contacts_dir = tmp_path / "contacts_pass16"
    db = PicasaDatabase.create_new(db_dir, contacts_dir)

    folder = tmp_path / "PhotosPass16"
    folder.mkdir(parents=True, exist_ok=True)
    photo_path = folder / "portrait_famille.jpg"
    other_path = folder / "paysage.jpg"
    Image.new("RGB", (120, 120), (220, 100, 60)).save(str(photo_path), format="JPEG", quality=95)
    Image.new("RGB", (120, 120), (40, 140, 220)).save(str(other_path), format="JPEG", quality=95)

    # Dossier avec un fichier Picasa.ini hérité uniquement
    legacy_ini = folder / "Picasa.ini"
    legacy_ini.write_text(
        "[paysage.jpg]\r\n"
        "star=yes\r\n"
        "caption=Belle montagne\r\n",
        encoding="utf-8",
    )

    scanner = PicasaDirScanner(db)
    scanner.scan_directory(folder)

    p_idx = db.find_photo_index(str(photo_path))
    assert p_idx is not None

    fm = PicasaFaceManager(db)
    frect = FaceRect(0.2, 0.2, 0.6, 0.6)
    added_fr = fm.add_face(str(photo_path), frect, "Alice Martin", db_idx=p_idx)
    cid = added_fr.contact_id
    assert cid

    # 1. Picasa.ini a été migré sans perte vers .picasa.ini lors de add_face
    dot_ini = folder / ".picasa.ini"
    assert dot_ini.exists()
    doc = PicasaIniParser.parse_file(str(dot_ini))
    assert doc.is_starred("paysage.jpg") is True
    assert doc.get_caption("paysage.jpg") == "Belle montagne"

    # 2. Recherche par nom de personne via les enregistrements enfants 1001 + invalidation au renommage
    assert p_idx in db.search("alice")
    assert fm.rename_person(cid, "Alicia Dupont") is True
    assert p_idx in db.search("alicia")
    assert p_idx not in db.search("alice")

    # 3. Propagation de imagedata_rotate aux enfants 1001 et invalidation de _avatar_cache ("face_1001" / "person_avatar")
    child_1001_list = db._get_face_children(p_idx)
    assert len(child_1001_list) == 1
    c_idx = child_1001_list[0]

    fm._avatar_cache[("face_1001", c_idx, 68, False)] = "cached_1001"
    fm._avatar_cache[("person_avatar", cid, 68, False)] = "cached_person"
    assert db.rotate_photo(p_idx, 1) is True
    pmp_rot = db.pmps.get("imagedata_rotate")
    assert pmp_rot is not None
    assert pmp_rot.records[c_idx] == pmp_rot.records[p_idx]
    assert ("face_1001", c_idx, 68, False) not in fm._avatar_cache
    assert ("person_avatar", cid, 68, False) not in fm._avatar_cache

    fm._avatar_cache[("face_1001", c_idx, 68, False)] = "cached_1001_v2"
    fm._avatar_cache[("person_avatar", cid, 68, False)] = "cached_person_v2"
    assert db.update_thumbnails_from_pil(
        p_idx, Image.new("RGB", (120, 120), (10, 200, 50)), persist_to_disk=False
    ) is True
    assert ("face_1001", c_idx, 68, False) not in fm._avatar_cache
    assert ("person_avatar", cid, 68, False) not in fm._avatar_cache
    assert c_idx in db._updated_thumb_indices

    # 4. Cycle complet set_geotag -> get_geotag -> search("]geo") -> clear_geotag
    assert db.get_geotag(p_idx) is None
    assert db.set_geotag(p_idx, 48.858370, 2.294481) is True
    gt = db.get_geotag(p_idx)
    assert gt is not None
    assert abs(gt[0] - 48.858370) < 1e-5
    assert abs(gt[1] - 2.294481) < 1e-5
    assert p_idx in db.search("]geo")

    assert db.clear_geotag(p_idx) is True
    assert db.get_geotag(p_idx) is None
    assert p_idx not in db.search("]geo")


def test_pass17_picasaoriginals_ini_face_remap_and_rotate_thumb_parity(tmp_path: Path) -> None:
    """
    FR: Vérifie les corrections de la 17e passe d'audit picasa3.exe vs PyCasa :
    1. Lors de la gravure de retouches sur le disque (`record_picasaoriginals_bake` / `_bake_photo_edits_on_disk`),
       création fidèle de `.picasaoriginals/.picasa.ini` avec `rotate=`, `crop=`, `filters=`, `moddate=<16-hex-le-filetime>`,
       `width=`, `height=`, `textactive=` et sauvegarde des coordonnées `faces=` originales (`0x00463523`, `0x0046D9A7`,
       `0x0068B539..0x0068B794`).
    2. Projection automatique des rectangles `faces=` et des sous-enregistrements `1001` (`imagedata_facerect`,
       `imagedata_crop64`, `imagedata_width`, `imagedata_height`) vers le repère de l'image gravée, puis restauration
       intégrale et nettoyage de `.picasaoriginals/.picasa.ini` lors de l'annulation (`cleanup_picasaoriginals_entry`).
    3. Migration/nettoyage de `.picasaoriginals/.picasa.ini` lors de `rename_photo`, `move_photo` et `delete_photo`.
    4. Régénération immédiate des vignettes en mémoire lors de `db.set_rotate(idx, rot)` lorsque le fichier existe sur disque.
    """
    import shutil
    import struct
    from PIL import Image
    from picasa_py.ini.parser import PicasaIniParser
    from picasa_py.faces.face_manager import PicasaFaceManager
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.scanner.scanner import file_filetimes

    db = PicasaDatabase.create_new(tmp_path / "db_root_p17")
    folder_a = tmp_path / "PhotosP17A"
    folder_b = tmp_path / "PhotosP17B"
    folder_a.mkdir(parents=True, exist_ok=True)
    folder_b.mkdir(parents=True, exist_ok=True)

    photo_path = folder_a / "vacances_p17.jpg"
    # Image rectangulaire 200x100 avec moitié gauche rouge et moitié droite bleue
    img = Image.new("RGB", (200, 100), (220, 30, 30))
    for x in range(100, 200):
        for y in range(100):
            img.putpixel((x, y), (30, 60, 220))
    img.save(str(photo_path), format="JPEG", quality=95)

    PicasaDirScanner(db).scan_directory(folder_a)
    p_idx = db.find_photo_index(str(photo_path))
    assert p_idx is not None

    fm = PicasaFaceManager(db)
    orig_fr = FaceRect(0.10, 0.20, 0.30, 0.60)
    added_fr = fm.add_face(str(photo_path), orig_fr, "Jean Valjean", db_idx=p_idx)
    orig_u64 = added_fr.to_uint64()
    children = db._get_face_children(p_idx)
    assert len(children) == 1
    c_idx = children[0]
    assert db.pmps["imagedata_facerect"].records[c_idx] == orig_u64

    # 1. set_rotate régénère immédiatement les vignettes en mémoire lorsque le fichier existe sur disque
    thumb_before = db.get_thumbnail(p_idx, "thumbs")
    assert db.set_rotate(p_idx, 1) is True
    thumb_after = db.get_thumbnail(p_idx, "thumbs")
    assert thumb_before is not None and thumb_after is not None
    assert thumb_before != thumb_after

    # Ajouter un filtre en plus de rotate(1) dans .picasa.ini
    db.update_photo_ini(str(photo_path), lambda d, fn: d.append_filter(fn, "autolight=1"))

    # 2. Simuler la gravure sur disque (.picasaoriginals/vacances_p17.jpg + .picasaoriginals/.picasa.ini)
    originals_dir = folder_a / ".picasaoriginals"
    originals_dir.mkdir(parents=True, exist_ok=True)
    backup_file = originals_dir / "vacances_p17.jpg"
    shutil.copy2(str(photo_path), str(backup_file))

    doc_pre = PicasaIniParser.parse_file(str(folder_a / ".picasa.ini"))
    old_faces, tr_faces = PicasaDatabase.record_picasaoriginals_bake(
        photo_path, backup_file, doc_pre, 200, 100
    )
    assert len(old_faces) == 1
    assert len(tr_faces) == 1
    # Après rotation 90° horaire (rotate(1)) : new_left = 1 - bottom = 0.40, new_top = left = 0.10, new_right = 1 - top = 0.80, new_bottom = right = 0.30
    assert abs(tr_faces[0].left - 0.40) < 1e-3
    assert abs(tr_faces[0].top - 0.10) < 1e-3
    assert abs(tr_faces[0].right - 0.80) < 1e-3
    assert abs(tr_faces[0].bottom - 0.30) < 1e-3

    orig_ini_p = originals_dir / ".picasa.ini"
    assert orig_ini_p.exists()
    orig_ini_doc = PicasaIniParser.parse_file(str(orig_ini_p))
    orig_sec = orig_ini_doc.get_section("vacances_p17.jpg")
    assert orig_sec is not None
    assert orig_sec.get("rotate") == "rotate(1)"
    assert orig_sec.get("filters") == "autolight=1;"
    assert orig_sec.get("width") == "200"
    assert orig_sec.get("height") == "100"
    assert orig_sec.get("textactive") == "0"
    _, ft2_bak, _ = file_filetimes(backup_file)
    expected_moddate = struct.pack("<Q", int(ft2_bak) & 0xFFFFFFFFFFFFFFFF).hex()
    assert orig_sec.get("moddate") == expected_moddate
    assert orig_sec.get("faces") is not None

    # Mettre à jour les sous-enregistrements 1001 vers le repère gravé (100x200)
    db.remap_photo_faces_after_geometry_change(p_idx, str(photo_path), tr_faces, 100, 200)
    assert db.pmps["imagedata_facerect"].records[c_idx] == tr_faces[0].to_uint64()
    assert db.pmps["imagedata_width"].records[c_idx] == 100
    assert db.pmps["imagedata_height"].records[c_idx] == 200

    # 3. Migration de .picasaoriginals/.picasa.ini lors de rename_photo et move_photo
    assert db.rename_photo(p_idx, "vacances_renomme.jpg") is True
    orig_ini_after_ren = PicasaIniParser.parse_file(str(originals_dir / ".picasa.ini"))
    assert orig_ini_after_ren.get_section("vacances_renomme.jpg") is not None
    assert orig_ini_after_ren.get_section("vacances_p17.jpg") is None

    assert db.move_photo(p_idx, folder_b) is True
    assert not (folder_a / ".picasaoriginals").exists()
    moved_orig_ini = folder_b / ".picasaoriginals" / ".picasa.ini"
    assert moved_orig_ini.exists()
    moved_orig_doc = PicasaIniParser.parse_file(str(moved_orig_ini))
    assert moved_orig_doc.get_section("vacances_renomme.jpg") is not None

    # 4. Restauration depuis .picasaoriginals : cleanup_picasaoriginals_entry restitue faces= et supprime .picasa.ini vide
    moved_backup_file = folder_b / ".picasaoriginals" / "vacances_renomme.jpg"
    restored_faces_str = PicasaDatabase.cleanup_picasaoriginals_entry(moved_backup_file)
    assert restored_faces_str is not None
    assert not moved_orig_ini.exists()
    restored_list = FaceRect.parse_ini_faces(restored_faces_str)
    assert len(restored_list) == 1
    db.remap_photo_faces_after_geometry_change(
        p_idx, str(folder_b / "vacances_renomme.jpg"), restored_list, 200, 100
    )
    assert db.pmps["imagedata_facerect"].records[c_idx] == orig_u64
    assert db.pmps["imagedata_width"].records[c_idx] == 200
    assert db.pmps["imagedata_height"].records[c_idx] == 100


def test_pass18_exif_gps_restore_iptc_scan_wordhash_color_eye_coords_and_album_sort_parity(tmp_path: Path) -> None:
    """
    FR: Vérifie les corrections de la 18e passe d'audit picasa3.exe vs PyCasa :
    1. `_restore_exif_gps_or_zero` dans `sync_photo_ini_to_db` (`clear_geotag`) restaure les coordonnées
       GPS EXIF d'origine de l'image lorsque `geotag=` est retiré de `.picasa.ini` (`_extract_exif_gps(_im, _ex)`).
    2. `extract_jpeg_iptc_metadata` extrait sans perte la légende (`IPTC 2:120`) et les mots-clés (`IPTC 2:25`)
       du segment `APP13` (`0xFFED`) lors du scan ou de la resynchronisation d'un JPEG sans `.picasa.ini`,
       en peuplant `imagedata_caption.pmp`, `imagedata_tags.pmp` et `wordhash.dat` (`0x00438450`, `0x00456150`, `0x00AB06D0`).
    3. `PicasaDirScanner.update_indexed_file` retire les anciens jetons `color:*` et `]geo` de `wordhash.dat`
       lorsqu'une image existante est modifiée sur le disque.
    4. `_get_or_create_1001_child` persiste les coordonnées oculaires (`leye` / `reye`) non nulles dans
       `imagedata_facerectdata.pmp` pour les visages issus de `PicasaFaceDetector` (`0x00414584`, `0x00C80C90`).
    5. `get_all_albums` calcule `ole_date`, `max_photo_date` et `total_size`, et `_sort_album_entries`
       trie fidèlement les albums par date (`mode=0`), taille (`mode=1`), nom (`mode=2`) et photo la plus récente (`mode=4`).
    """
    from PIL import Image
    from picasa_py.faces.face_manager import PicasaFaceManager
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.scanner.scanner import _extract_exif_gps

    db = PicasaDatabase.create_new(tmp_path / "db_root_p18")
    folder = tmp_path / "PhotosP18"
    folder.mkdir(parents=True, exist_ok=True)

    # 1. Créer une image JPEG avec GPS EXIF (43.2965 N, 5.3698 E — Marseille)
    gps_photo = folder / "marseille_gps.jpg"
    im_red = Image.new("RGB", (80, 80), (240, 20, 20))
    exif = im_red.getexif()
    exif[0x8825] = {
        1: "N",
        2: (43.0, 17.0, 47.40),
        3: "E",
        4: (5.0, 22.0, 11.28),
    }
    im_red.save(str(gps_photo), format="JPEG", quality=95, exif=exif.tobytes())

    # Vérifier la résilience de _extract_exif_gps aux deux ordres d'arguments
    with Image.open(str(gps_photo)) as chk_im:
        chk_ex = chk_im.getexif()
        lat_a, lon_a = _extract_exif_gps(chk_im, chk_ex)
        lat_b, lon_b = _extract_exif_gps(chk_ex, chk_im)
        assert lat_a is not None and lon_a is not None
        assert abs(lat_a - 43.2965) < 1e-3
        assert abs(lon_a - 5.3698) < 1e-3
        assert lat_a == lat_b and lon_a == lon_b

    scanner = PicasaDirScanner(db)
    scanner.scan_directory(folder)
    idx_gps = db.find_photo_index(str(gps_photo))
    assert idx_gps is not None
    assert abs(float(db.pmps["imagedata_lat"].records[idx_gps]) - 43.2965) < 1e-3

    # Surcharger via set_geotag (Paris : 48.8566, 2.3522), puis clear_geotag -> doit restaurer Marseille (43.2965, 5.3698) !
    assert db.set_geotag(idx_gps, 48.8566, 2.3522) is True
    assert abs(float(db.pmps["imagedata_lat"].records[idx_gps]) - 48.8566) < 1e-3
    assert db.clear_geotag(idx_gps) is True
    assert abs(float(db.pmps["imagedata_lat"].records[idx_gps]) - 43.2965) < 1e-3
    assert abs(float(db.pmps["imagedata_long"].records[idx_gps]) - 5.3698) < 1e-3
    assert idx_gps in db.search("]geo")

    # 2. Créer un JPEG contenant des métadonnées IPTC APP13 (2:120 Caption + 2:25 Keywords) mais SANS .picasa.ini
    iptc_photo = folder / "iptc_externe.jpg"
    Image.new("RGB", (80, 80), (20, 200, 40)).save(str(iptc_photo), format="JPEG", quality=95)
    db._update_jpeg_iptc_metadata(
        str(iptc_photo),
        -1,
        caption="Coucher de soleil breton",
        keywords=["Bretagne", "Océan"],
    )
    cap_ext, kws_ext = PicasaDatabase.extract_jpeg_iptc_metadata(iptc_photo)
    assert cap_ext == "Coucher de soleil breton"
    assert kws_ext == ["Bretagne", "Océan"]

    idx_iptc = scanner.index_file(iptc_photo)
    assert idx_iptc >= 0
    assert db.pmps["imagedata_caption"].records[idx_iptc] == "Coucher de soleil breton"
    assert db.pmps["imagedata_tags"].records[idx_iptc] == "Bretagne,Océan"
    assert idx_iptc in db.search("breton")
    assert idx_iptc in db.search("bretagne")

    # 3. update_indexed_file : remplacer l'image rouge avec GPS par une image bleue sans GPS sur disque
    assert idx_gps in db.search("color:red")
    Image.new("RGB", (80, 80), (20, 40, 240)).save(str(gps_photo), format="JPEG", quality=95)
    assert scanner.update_indexed_file(idx_gps, gps_photo) is True
    assert idx_gps in db.search("color:blue")
    assert idx_gps not in db.search("color:red")
    assert idx_gps not in db.search("]geo")
    assert float(db.pmps["imagedata_lat"].records[idx_gps]) == 0.0

    # 4. Coordonnées oculaires leye / reye persistées dans imagedata_facerectdata.pmp via _get_or_create_1001_child
    fm = PicasaFaceManager(db)
    det_fr = FaceRect(0.20, 0.20, 0.60, 0.60)
    det_fr.confidence = 0.925  # type: ignore[attr-defined]
    det_fr.pan = 0.120  # type: ignore[attr-defined]
    det_fr.leye = (0.345, 0.392)  # type: ignore[attr-defined]
    det_fr.reye = (0.455, 0.392)  # type: ignore[attr-defined]
    det_fr.mouth = (0.400, 0.500)  # type: ignore[attr-defined]
    c_1001 = fm._get_or_create_1001_child(idx_iptc, det_fr, "contact_test_18")
    assert c_1001 is not None
    fr_data_str = db.pmps["imagedata_facerectdata"].records[c_1001]
    assert "leye(0.345,0.392)" in fr_data_str
    assert "reye(0.455,0.392)" in fr_data_str
    assert "mouth(0.400,0.500)" in fr_data_str

    # 5. Tri des albums (get_all_albums + _sort_album_entries) par date, taille, nom et photo la plus récente
    db.pmps["imagedata_tagdate"].records[idx_gps] = 44000.0
    db.pmps["imagedata_tagdate"].records[idx_iptc] = 45500.0
    db.thumbindex.records[idx_gps].size = 10000
    db.thumbindex.records[idx_iptc].size = 90000

    from picasa_py.ini.parser import PicasaIniParser
    tok_a = "aaaa1111222233334444555566667777"
    tok_b = "bbbb1111222233334444555566667777"
    doc_p18 = PicasaIniParser.parse_bytes(
        (
            f"[.album:{tok_a}]\r\n"
            f"name=Zeta Album\r\n"
            f"token={tok_a}\r\n"
            f"date=45000.0\r\n"
            f"[.album:{tok_b}]\r\n"
            f"name=Alpha Album\r\n"
            f"token={tok_b}\r\n"
            f"date=43000.0\r\n"
            f"[marseille_gps.jpg]\r\n"
            f"albums={tok_a}\r\n"
            f"[iptc_externe.jpg]\r\n"
            f"albums={tok_b}\r\n"
        ).encode("utf-8")
    )
    doc_p18.write_file(str(folder / ".picasa.ini"))
    db.invalidate_ini_cache(str(folder / ".picasa.ini"))
    db.sync_photo_ini_to_db(idx_gps)
    db.sync_photo_ini_to_db(idx_iptc)
    db._albums_cache = None

    albs = [a for a in db.get_all_albums() if a["token"] in (tok_a, tok_b)]
    assert len(albs) == 2
    by_tok = {a["token"]: a for a in albs}
    assert by_tok[tok_a]["ole_date"] == 45000.0
    assert by_tok[tok_a]["max_photo_date"] == 45000.0
    assert by_tok[tok_b]["ole_date"] == 43000.0
    assert by_tok[tok_b]["max_photo_date"] == 45500.0
    assert by_tok[tok_b]["total_size"] > by_tok[tok_a]["total_size"]

    from picasa_py.ui.library_tree import PicasaLibraryTree
    dummy_tree = PicasaLibraryTree.__new__(PicasaLibraryTree)
    dummy_tree.album_list_flip = False

    # Mode 0 (par date d'album décroissante) : tok_a (45000.0) avant tok_b (43000.0)
    dummy_tree.date_sort_mode = 0
    assert [a["token"] for a in dummy_tree._sort_album_entries(albs)] == [tok_a, tok_b]

    # Mode 4 (par photo la plus récente) : tok_b (max_photo_date=45500.0) avant tok_a (45000.0)
    dummy_tree.date_sort_mode = 4
    assert [a["token"] for a in dummy_tree._sort_album_entries(albs)] == [tok_b, tok_a]

    # Mode 1 (par taille décroissante) : tok_b (90000 octets) avant tok_a (10000 octets)
    dummy_tree.date_sort_mode = 1
    assert [a["token"] for a in dummy_tree._sort_album_entries(albs)] == [tok_b, tok_a]

    # Mode 2 (par nom) : Alpha Album (tok_b) avant Zeta Album (tok_a)
    dummy_tree.date_sort_mode = 2
    assert [a["token"] for a in dummy_tree._sort_album_entries(albs)] == [tok_b, tok_a]


def test_pass19_effects_copy_paste_offset_time_and_geotag_priority(tmp_path: Path):
    """
    FR: Vérifie les correctifs de la 19e passe d'audit Ghidra :
    1. Menu Outils (`ID_TOOLS_FOLDER_MGR` -> "Gestionnaire de &dossiers...", `ID_VIEW_TWOUP`, `ID_GEOTAG_EXPORT_KML`, `ID_TOOLS_BACKUP`).
    2. `get_photo_datetime` (`offset_time_dialog.py`) lit `DateTimeOriginal` (36867) dans le sous-IFD Exif (0x8769)
       et `PicasaAdjustTimeDialog.execute_adjustment` synchronise `imagedata_filesize` et `rec.dirty`.
    3. `extract_full_metadata` (`exif_reader.py`) donne la priorité à `.picasa.ini` `geotag=` sur l'EXIF GPS brut (`0x00456A15`).
    4. `action_copy_all_effects` / `action_paste_all_effects` ne copie jamais `star=yes` et nettoie les anciennes
       clés de retouche (`crop`, `tilt`, `filters`) absentes de la pile copiée (`0x0088C3EC`).
    EN: Verifies the 19th-pass Ghidra audit fixes.
    """
    import datetime as dt_mod
    from PIL import Image
    from picasa_py.db.database import PicasaDatabase
    from picasa_py.scanner.scanner import PicasaDirScanner
    from picasa_py.ini.parser import PicasaIniParser
    from picasa_py.ui.menu import MENU_I18N
    from picasa_py.ui.offset_time_dialog import get_photo_datetime, PicasaAdjustTimeDialog
    from picasa_py.ui.exif_reader import extract_full_metadata

    # 1. Traductions françaises de la barre de menus (STRINGRES_FR.XML)
    fr_map = MENU_I18N["fr"]
    assert fr_map["ID_TOOLS_FOLDER_MGR"] == "Gestionnaire de &dossiers..."
    assert fr_map["ID_TOOLS_INCLUDEEXCLUDEFOLDERS"] == "Ajouter un &dossier à Picasa..."
    assert "ID_VIEW_TWOUP" in fr_map
    assert "ID_GEOTAG_EXPORT_KML" in fr_map
    assert "ID_TOOLS_BACKUP" in fr_map

    db = PicasaDatabase.create_new(tmp_path / "db_root_p19")
    folder = tmp_path / "PhotosPass19"
    folder.mkdir(parents=True, exist_ok=True)
    scanner = PicasaDirScanner(db)

    # 2. Créer un JPEG avec DateTimeOriginal uniquement dans le sous-IFD Exif (0x8769) et un GPS EXIF initial
    photo1 = folder / "subifd_date.jpg"
    im1 = Image.new("RGB", (100, 80), (180, 90, 40))
    exif1 = im1.getexif()
    exif1[0x8769] = {
        36867: "2021:06:15 14:30:00",
        36868: "2021:06:15 14:30:00",
    }
    exif1[0x8825] = {
        1: "N",
        2: (48.0, 51.0, 24.0),
        3: "E",
        4: (2.0, 21.0, 7.0),
    }
    im1.save(str(photo1), format="JPEG", quality=92, exif=exif1.tobytes())

    idx1 = scanner.index_file(photo1)
    assert idx1 >= 0

    # get_photo_datetime doit lire DateTimeOriginal (2021-06-15 14:30:00) dans le sous-IFD 0x8769
    parsed_dt = get_photo_datetime(str(photo1))
    assert parsed_dt == dt_mod.datetime(2021, 6, 15, 14, 30, 0)

    # Tester execute_adjustment sans ouvrir d'interface graphique bloquante
    adj = PicasaAdjustTimeDialog.__new__(PicasaAdjustTimeDialog)
    adj.file_paths = [str(photo1)]
    adj.db = db
    adj.original_dt = parsed_dt
    adj.get_target_datetime = lambda: dt_mod.datetime(2022, 8, 20, 10, 15, 0)  # type: ignore[method-assign]
    adj.is_relative = lambda: False  # type: ignore[method-assign]
    res_adj = adj.execute_adjustment()
    assert len(res_adj) == 1
    assert get_photo_datetime(str(photo1)) == dt_mod.datetime(2022, 8, 20, 10, 15, 0)
    assert db.thumbindex.records[idx1].dirty is True
    assert db.thumbindex.records[idx1].size == photo1.stat().st_size

    # 3. Priorité de .picasa.ini geotag= sur l'EXIF GPS brut dans extract_full_metadata
    doc_geo = PicasaIniParser.parse_bytes(
        b"[subifd_date.jpg]\r\n"
        b"geotag=45.764043,4.835659\r\n"
        b"star=yes\r\n"
        b"filters=bw=1;\r\n"
    )
    doc_geo.write_file(str(folder / ".picasa.ini"))
    meta1 = extract_full_metadata(str(photo1))
    assert meta1["gps"] is not None
    assert abs(meta1["gps"][0] - 45.764043) < 1e-4
    assert abs(meta1["gps"][1] - 4.835659) < 1e-4

    # 4. Copier/Coller tous les effets : ne copie pas star=yes et nettoie les anciens effets de la cible
    photo2 = folder / "target_effects.jpg"
    Image.new("RGB", (100, 80), (40, 120, 200)).save(str(photo2), format="JPEG", quality=92)
    idx2 = scanner.index_file(photo2)
    assert idx2 >= 0

    doc_init = PicasaIniParser.parse_bytes(
        b"[subifd_date.jpg]\r\n"
        b"star=yes\r\n"
        b"filters=sepia=1;\r\n"
        b"[target_effects.jpg]\r\n"
        b"crop=rect64(1000100080008000)\r\n"
        b"tilt=tilt(5.000000,0.000000)\r\n"
        b"filters=crop64=1,1000100080008000;invert=1;\r\n"
    )
    doc_init.write_file(str(folder / ".picasa.ini"))
    db.invalidate_ini_cache(str(folder / ".picasa.ini"))

    from picasa_py.ui.main_window import PicasaMainWindow
    dummy_win = PicasaMainWindow.__new__(PicasaMainWindow)
    dummy_win.db = db
    dummy_win._effects_clipboard = {}
    dummy_win.stack = type("_S", (), {"currentWidget": lambda self: None})()  # type: ignore[assignment]
    dummy_win.one_up_view = type("_O", (), {"current_photo_path": None})()  # type: ignore[assignment]
    dummy_win.status_bar = type("_B", (), {"showMessage": lambda self, msg: None})()  # type: ignore[assignment]
    dummy_win.thumb_view = type("_T", (), {"invalidate_item": lambda self, p: None, "update": lambda self: None})()  # type: ignore[assignment]
    dummy_win._get_active_photo_paths = lambda: [str(photo1)]  # type: ignore[method-assign]
    dummy_win._update_photo_ini = lambda p, fn: db.update_photo_ini(p, fn)  # type: ignore[method-assign]

    dummy_win.action_copy_all_effects()
    assert "star" not in dummy_win._effects_clipboard
    assert dummy_win._effects_clipboard.get("filters") == "sepia=1;"

    dummy_win.action_paste_all_effects([str(photo2)])
    doc_after = PicasaIniParser.parse_file(str(folder / ".picasa.ini"))
    sec2 = doc_after.get_section("target_effects.jpg")
    assert sec2 is not None
    assert sec2.get("star") is None
    assert sec2.get("crop") is None
    assert sec2.get("tilt") is None
    assert sec2.get("filters") == "sepia=1;"


def test_pass20_canvas_tool_cancel_and_graduated_tint_and_save_as_parity(tmp_path: Path) -> None:
    """
    FR: Vérifie les correctifs de la Passe 20 :
    1. L'annulation d'un outil interactif depuis `PicasaImageCanvas` (touche Échap ou clic droit)
       émet `tool_cancelled`, referme le sous-panneau actif de `PicasaEditPanel` et déverrouille
       toutes les barres d'interface de `PicasaOneUpView` (`_is_tool_locked == False`).
    2. `FILTER_SPECS["graduated_tint"]` (`dir_tint` dans `filterdesc.xml`) expose le curseur `angle`
       (-180°..+180°) et le transmet à `PicasaOneUpView._effect_to_ini_token` / `PicasaImageProcessor`.
    3. `PicasaOneUpView.save_current_photo_as` applique `ImageOps.exif_transpose` pour comparer la taille
       réelle, sauvegarde en JPEG `quality=90, subsampling="keep"` et émet `photo_edited`.
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtGui import QKeyEvent, QContextMenuEvent
    from picasa_py.ui.edit_panel import FILTER_SPECS
    from picasa_py.ui.one_up_view import PicasaOneUpView

    app = QApplication.instance() or QApplication([])

    # 1. Vérifier que graduated_tint possède bien le curseur angle (-180..180)
    gt_sliders = FILTER_SPECS["graduated_tint"]["sliders"]
    gt_keys = [s["key"] for s in gt_sliders]
    assert "angle" in gt_keys

    # 2. Créer une photo de test et l'ouvrir dans PicasaOneUpView
    db = PicasaDatabase.create_new(tmp_path / "db_pass20")
    scanner = PicasaDirScanner(db)
    folder = tmp_path / "photos_p20"
    folder.mkdir()
    photo_p = folder / "sample_p20.jpg"
    Image.new("RGB", (320, 240), (90, 140, 210)).save(str(photo_p), format="JPEG", quality=92)
    idx = scanner.index_file(photo_p)
    assert idx >= 0

    view = PicasaOneUpView()
    view.open_photo(db, idx, [idx])

    # Activer l'outil Recadrer : le sous-panneau s'ouvre et l'interface est verrouillée
    view.edit_panel._open_crop_subpanel()
    assert view.edit_panel.stack.currentIndex() == 1
    assert view._is_tool_locked is True
    assert view.canvas.is_cropping is True

    # Simuler Échap directement sur PicasaImageCanvas
    esc_ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    view.canvas.keyPressEvent(esc_ev)
    assert view.canvas.is_cropping is False
    assert view.edit_panel.stack.currentIndex() == 0
    assert view._is_tool_locked is False

    # Activer l'ajout manuel de visage et annuler par clic droit (contextMenuEvent) sur le canevas
    view._on_manual_face_add_start()
    assert view.canvas.is_manual_face_add is True
    assert view._is_tool_locked is True
    ctx_ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(50, 50), QPoint(50, 50))
    view.canvas.contextMenuEvent(ctx_ev)
    assert view.canvas.is_manual_face_add is False
    assert view._is_tool_locked is False

    # 3. Vérifier save_current_photo_as et l'émission du signal photo_edited
    edited_signals: list[str] = []
    view.photo_edited.connect(lambda p: edited_signals.append(p))
    out_p = folder / "saved_as_p20.jpg"
    ok = view.save_current_photo_as(str(out_p))
    assert ok is True
    assert out_p.exists()
    assert str(out_p) in edited_signals












