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

