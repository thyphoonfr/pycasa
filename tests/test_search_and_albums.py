"""
FR: Tests de validation pour le moteur de recherche (wordhash.dat + métadonnées dynamiques)
et la gestion des signaux et du cycle de vie des Albums et Dossiers.
Conforme à AGENTS.md :
- Traçabilité Ghidra (wordhash @ 0x007046E0, albums @ 0x00732160, search UI @ 0x0088C3EC)
- Aucune régression sur le reste de la photothèque.
EN: Validation tests for the search engine (wordhash.dat + dynamic metadata)
and signal and lifecycle management for Albums and Folders.
Complies with AGENTS.md:
- Ghidra traceability (wordhash @ 0x007046E0, albums @ 0x00732160, search UI @ 0x0088C3EC)
- Zero regression on the rest of the photo library.
"""

import os
import shutil
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from picasa_py.db.wordhash import WordHashFile, WordEntry, WORDHASH_MAGIC
from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.ui.thumbnail_view import PicasaThumbnailView, ThumbnailItem
from picasa_py.ui.library_tree import PicasaLibraryTree
from picasa_py.ui.top_bar import PicasaTopBar


@pytest.fixture(scope="session")
def qapp():
    """
    FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provide a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_wordhash_create_and_search():
    """
    FR: Vérifie la création et la recherche multi-termes avec préfixe dans WordHashFile.
    EN: Verify creation and multi-term prefix search in WordHashFile.
    Ref: picasa3.exe @ 0x007046E0, 0x004DB4F0
    """
    index_data = {
        "vacances": [1, 2, 5],
        "plage": [2, 5],
        "soleil": [5, 8],
        "montagne": [10],
    }
    wh = WordHashFile.create_from_dict(index_data)
    assert wh.magic == WORDHASH_MAGIC
    assert len(wh.entries) == 4

    # Recherche mono-mot exact
    assert wh.search("montagne") == [10]

    # Recherche par préfixe (insensible à la casse)
    assert wh.search("vac") == [1, 2, 5]
    assert wh.search("PLA") == [2, 5]

    # Recherche multi-termes (intersection AND)
    # "vacances" [1, 2, 5] AND "plage" [2, 5] -> [2, 5]
    assert wh.search("vacances plage") == [2, 5]

    # "vacances" AND "soleil" -> [5]
    assert wh.search("vacances soleil") == [5]

    # Aucun match commun
    assert wh.search("vacances montagne") == []

    # Vérification du roundtrip binaire
    raw = wh.to_bytes()
    reloaded = WordHashFile.from_bytes(raw)
    assert reloaded.search("vacances soleil") == [5]


def test_database_dynamic_search(tmp_path):
    """
    FR: Vérifie que PicasaDatabase.search effectue une recherche complète
    sur les noms de fichiers, dossiers parents et personnes.
    EN: Verify that PicasaDatabase.search performs a comprehensive search
    across filenames, parent folders, and people.
    Ref: picasa3.exe @ 0x0088C3EC
    """
    db_dir = tmp_path / "db3"
    db_dir.mkdir()
    db = PicasaDatabase(db3_dir=db_dir)

    # Création d'un index synthétique
    # 0: Dossier "Vacances_2023"
    # 1: Image "IMG_001.JPG" dans "Vacances_2023"
    # 2: Image "plage_soleil.jpg" dans "Vacances_2023"
    # 3: Dossier "Famille"
    # 4: Image "portrait.jpg" dans "Famille"
    records = [
        ThumbIndexRecord(path="C:\\Photos\\Vacances_2023\\", ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=0),
        ThumbIndexRecord(path="IMG_001.JPG", ft1=0, ft2=0, size=1000, type=2, flags=0, parent_idx=0),
        ThumbIndexRecord(path="plage_soleil.jpg", ft1=0, ft2=0, size=2000, type=2, flags=0, parent_idx=0),
        ThumbIndexRecord(path="C:\\Photos\\Famille\\", ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=0),
        ThumbIndexRecord(path="portrait.jpg", ft1=0, ft2=0, size=1500, type=2, flags=0, parent_idx=3),
    ]
    db.thumbindex = ThumbIndexFile(records=records)

    # 1. Recherche par nom de fichier
    res = db.search("plage")
    assert 2 in res
    assert 1 not in res

    # 2. Recherche par dossier parent
    res_folder = db.search("Vacances")
    assert 1 in res_folder
    assert 2 in res_folder
    assert 4 not in res_folder

    # 3. Recherche multi-mots
    res_multi = db.search("Vacances plage")
    assert res_multi == [2]


def test_database_albums_lifecycle(tmp_path):
    """
    FR: Vérifie la détection et la suppression des albums virtuels dans .picasa.ini.
    EN: Verify detection and deletion of virtual albums in .picasa.ini.
    Ref: picasa3.exe @ 0x00732160 (ID_ALBUM_DELETE, [.album:<uid>])
    """
    folder = tmp_path / "AlbumFolder"
    folder.mkdir()
    ini_path = folder / ".picasa.ini"

    # Créer un fichier .picasa.ini avec un album et une photo associée
    ini_content = (
        "[.album:album1234]\r\n"
        "name=Mon Bel Album\r\n"
        "token=album1234\r\n"
        "date=2023-08-15\r\n"
        "\r\n"
        "[photo1.jpg]\r\n"
        "albums=album1234\r\n"
    )
    ini_path.write_text(ini_content, encoding="utf-8")

    db_dir = tmp_path / "db3"
    db_dir.mkdir()
    db = PicasaDatabase(db3_dir=db_dir)
    db.set_watched_folder(str(folder), "1")

    # 1. Vérifier la détection de l'album
    albums = db.get_all_albums()
    assert len(albums) == 1
    assert albums[0]["token"] == "album1234"
    assert albums[0]["name"] == "Mon Bel Album"
    assert len(albums[0]["photo_paths"]) == 1
    assert "photo1.jpg" in albums[0]["photo_paths"][0]

    # 2. Vérifier la suppression de l'album
    deleted = db.delete_album("album1234")
    assert deleted is True

    # Après suppression, get_all_albums ne renvoie plus cet album
    albums_after = db.get_all_albums()
    assert len(albums_after) == 0

    # Et la section [photo1.jpg] n'a plus la clé albums
    doc = PicasaIniParser.parse_file(str(ini_path))
    sec = doc.get_section("photo1.jpg")
    assert sec is not None
    assert sec.get("albums") is None


def test_thumbnail_view_album_and_search_filter(qapp):
    """
    FR: Vérifie le filtrage par album et par recherche dans PicasaThumbnailView.
    EN: Verify filtering by album and by search query in PicasaThumbnailView.
    """
    view = PicasaThumbnailView()
    items = [
        ThumbnailItem(index=0, path="C:/photos/img1.jpg", filename="img1.jpg", folder="Vacances", folder_path="C:/photos/"),
        ThumbnailItem(index=1, path="C:/photos/img2.jpg", filename="img2.jpg", folder="Vacances", folder_path="C:/photos/"),
        ThumbnailItem(index=2, path="C:/photos/img3.jpg", filename="img3.jpg", folder="Vacances", folder_path="C:/photos/", starred=True),
    ]
    view.items = items

    # 1. Filtrer par album
    view.filter_by_album("alb1", "Favoris", [0, 2])
    assert len(view.visible_sections) == 1
    assert view.visible_sections[0].is_album is True
    assert view.visible_sections[0].name == "Favoris"
    assert view.filtered_indices == [0, 2]

    # Filtre rapide étoile appliqué sur l'album
    view.apply_quick_filters(filter_starred=True)
    assert view.filtered_indices == [2]

    # 2. Filtrer par recherche
    view.apply_quick_filters(filter_starred=False)
    view.filter_by_search("img2", [1])
    assert len(view.visible_sections) == 1
    assert view.visible_sections[0].is_search is True
    assert view.filtered_indices == [1]


def test_top_bar_search_field(qapp):
    """
    FR: Vérifie le champ de recherche dans PicasaTopBar (clear button, debounce, signaux).
    EN: Verify the search field in PicasaTopBar (clear button, debounce, signals).
    """
    top_bar = PicasaTopBar()
    emitted = []
    top_bar.search_query_changed.connect(lambda q: emitted.append(q))

    # Taper du texte
    top_bar.search_edit.setText("test")
    # Avant expiration du timer, aucun signal émis (debounce)
    assert len(emitted) == 0

    # Forcer l'expiration du timer
    top_bar._search_timer.timeout.emit()
    assert len(emitted) == 1
    assert emitted[-1] == "test"

    # Effacer le texte -> émission instantanée sans attendre le debounce
    top_bar.clear_search()
    assert emitted[-1] == ""


def test_library_tree_live_refresh(qapp, tmp_path):
    """
    FR: Vérifie que refresh_albums() et refresh_folders() mettent à jour l'arborescence sans recharger tout l'arbre.
    EN: Verify that refresh_albums() and refresh_folders() update the library tree without reloading the entire tree.
    """
    folder = tmp_path / "MyPhotos"
    folder.mkdir()
    (folder / ".picasa.ini").write_text(
        "[.album:tok1]\r\nname=Voyage Italie\r\ntoken=tok1\r\n\r\n[pic.jpg]\r\nalbums=tok1\r\n",
        encoding="utf-8"
    )
    db_dir = tmp_path / "db3"
    db_dir.mkdir()
    db = PicasaDatabase(db3_dir=db_dir)
    db.set_watched_folder(str(folder), "1")
    records = [
        ThumbIndexRecord(path=str(folder) + "\\", ft1=0, ft2=0, size=0, type=1, flags=0, parent_idx=0),
        ThumbIndexRecord(path="pic.jpg", ft1=0, ft2=0, size=1234, type=2, flags=0, parent_idx=0),
    ]
    db.thumbindex = ThumbIndexFile(records=records)

    tree = PicasaLibraryTree()
    tree.populate_from_database(db)

    # Vérifier les albums dans cat_albums (Photos favorites épinglé + Voyage Italie)
    assert tree.cat_albums.childCount() == 2
    album_names_init = [tree.cat_albums.child(i).text(0) for i in range(tree.cat_albums.childCount())]
    assert any("Photos favorites" in n for n in album_names_init)
    assert any("Voyage Italie" in n for n in album_names_init)

    # Vérifier le dossier dans cat_folders
    assert tree.cat_folders.childCount() == 1
    assert "MyPhotos" in tree.cat_folders.child(0).text(0)

    # Ajouter un deuxième album dans un autre dossier
    folder2 = tmp_path / "OtherPhotos"
    folder2.mkdir()
    (folder2 / ".picasa.ini").write_text(
        "[.album:tok2]\r\nname=Concert\r\ntoken=tok2\r\n",
        encoding="utf-8"
    )
    db.set_watched_folder(str(folder2), "1")

    # Appeler refresh_albums()
    tree.refresh_albums()
    assert tree.cat_albums.childCount() == 3
    album_names = [tree.cat_albums.child(i).text(0) for i in range(tree.cat_albums.childCount())]
    assert any("Concert" in n for n in album_names)
    assert any("Voyage Italie" in n for n in album_names)


def test_folders_and_albums_parity_with_picasa3(qapp, tmp_path):
    """
    FR: Vérifie la conformité de l'affichage des Dossiers et des Albums avec picasa3.exe :
    - inclusion des PNG (type=14) et BMP/GIF (type=3),
    - exclusion des dossiers cat=6 ("Other Stuff") de Dossiers et de ThumbnailView.sections,
    - exclusion des tokens de dossiers (cat=2, "]album:<folder_uid>") de la liste des Albums (cat=0),
    - inclusion de l'album dynamique système "]updated" ("Récemment mis à jour") lorsqu'il a des photos actives,
    - tri par défaut par date décroissante (Preferences\\datesort = 0) puis par nom.
    EN: Verifies Folders and Albums display parity with picasa3.exe.
    Ref: picasa3.exe @ 0x004A59E9, 0x004A7A18 - 0x004A8054, 0x004AA9F0, 0x004ACA00
    """
    from picasa_py.db.pmp import PmpFile, PmpType
    from picasa_py.db.wordhash import WordHashFile, WordHashEntry

    f_old = tmp_path / "AlphaOld"
    f_new = tmp_path / "BetaNew"
    f_other = tmp_path / "GammaOtherStuff"
    for d in (f_old, f_new, f_other):
        d.mkdir()

    db_dir = tmp_path / "db3"
    db_dir.mkdir()
    db = PicasaDatabase(db3_dir=db_dir)
    records = [
        ThumbIndexRecord(path=str(f_old) + "\\", ft1=0, ft2=0, size=0, type=1, flags=0x0102, parent_idx=0xFFFFFFFF),
        ThumbIndexRecord(path="old_jpg.jpg", ft1=0, ft2=0, size=1000, type=2, flags=0x0100, parent_idx=0),
        ThumbIndexRecord(path=str(f_new) + "\\", ft1=0, ft2=0, size=0, type=1, flags=0x0102, parent_idx=0xFFFFFFFF),
        ThumbIndexRecord(path="screen1.png", ft1=0, ft2=0, size=2000, type=14, flags=0x0100, parent_idx=2),
        ThumbIndexRecord(path="anim.gif", ft1=0, ft2=0, size=1500, type=3, flags=0x0100, parent_idx=2),
        ThumbIndexRecord(path=str(f_other) + "\\", ft1=0, ft2=0, size=0, type=1, flags=0x0102, parent_idx=0xFFFFFFFF),
        ThumbIndexRecord(path="thumb_cache.jpg", ft1=0, ft2=0, size=500, type=2, flags=0x0100, parent_idx=5),
    ]
    db.thumbindex = ThumbIndexFile(records=records)

    db.pmps["albumdata_name"] = PmpFile(
        PmpType.STRING,
        ["Photos favorites", "Récemment mis à jour", "AlphaOld", "BetaNew", "GammaOtherStuff"],
    )
    db.pmps["albumdata_category"] = PmpFile(PmpType.UINT32, [0, 0, 2, 2, 6])
    db.pmps["albumdata_token"] = PmpFile(
        PmpType.STRING,
        ["]star", "]updated", "]album:fold_old", "]album:fold_new", "]album:fold_other"],
    )
    db.pmps["albumdata_uid"] = PmpFile(
        PmpType.STRING,
        ["starred", "updated", "fold_old", "fold_new", "fold_other"],
    )
    db.pmps["albumdata_filename"] = PmpFile(
        PmpType.STRING,
        ["", "", str(f_old) + "\\", str(f_new) + "\\", str(f_other) + "\\"],
    )
    db.pmps["albumdata_date"] = PmpFile(
        PmpType.DOUBLE,
        [0.0, 0.0, 44000.0, 45500.0, 46000.0],
    )

    wh = WordHashFile()
    wh._word_map["]updated"] = WordHashEntry(word="]updated", str_offset=0, image_ids=[3, 4])
    db.wordhash = wh

    tree = PicasaLibraryTree()
    tree.set_date_sort_mode(0, persist=False)
    tree.populate_from_database(db)

    # 1. Dossiers : BetaNew (date 45500, 2 fichiers : PNG type=14 + GIF type=3) avant AlphaOld (date 44000, 1 JPG),
    # et GammaOtherStuff (cat=6) exclu
    folder_labels = [tree.cat_folders.child(i).text(0) for i in range(tree.cat_folders.childCount())]
    assert folder_labels == ["BetaNew (2)", "AlphaOld (1)"]

    # 2. Tri par nom (mode 2) : AlphaOld avant BetaNew
    tree.set_date_sort_mode(2, persist=False)
    folder_labels_by_name = [tree.cat_folders.child(i).text(0) for i in range(tree.cat_folders.childCount())]
    assert folder_labels_by_name == ["AlphaOld (1)", "BetaNew (2)"]

    # 3. Albums : Photos favorites (0) + Récemment mis à jour (2), sans aucun token de dossier "]album:fold_*"
    album_labels = [tree.cat_albums.child(i).text(0) for i in range(tree.cat_albums.childCount())]
    assert album_labels == ["Photos favorites (0)", "Récemment mis à jour (2)"]

    # 4. ThumbnailView : sections contient BetaNew (2) et AlphaOld (1), mais pas GammaOtherStuff (cat=6)
    view = PicasaThumbnailView()
    view.set_database(db)
    sec_names_counts = [(s.name, len(s.item_indices)) for s in view.visible_sections]
    assert sec_names_counts == [("BetaNew", 2), ("AlphaOld", 1)]

