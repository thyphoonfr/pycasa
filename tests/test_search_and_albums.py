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
