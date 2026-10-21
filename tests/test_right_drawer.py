"""
FR: Tests de validation du volet latéral droit (PicasaRightDrawer) et de ses 4 panneaux :
- Personnes (People Panel)
- Lieux (Places Panel avec Leaflet)
- Tags (Mots-clés et synchronisation .picasa.ini)
- Propriétés (Image Properties / EXIF)
EN: Validation tests for the right-hand side drawer (PicasaRightDrawer) and its 4 panels:
- People (People Panel)
- Places (Places Panel with Leaflet)
- Tags (Keywords and .picasa.ini synchronization)
- Properties (Image Properties / EXIF)

Ref: picasa3.exe @ RIGHTDRAWERPANEL_TEXT.XML, IMAGEPROPERTIES.XML, imageproperties.fen
Ref: picasa3.exe @ PEOPLEPANEL_TEXT_FR.XML, GEOPANELTEXT_FR.XML, TAGPANEL_TEXT_FR.XML
"""

import os
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from picasa_py.ui.right_drawer import (
    PicasaRightDrawer, PicasaPeoplePanel, PicasaPlacesPanel,
    PicasaTagsPanel, PicasaPropertiesPanel
)
from picasa_py.ui.exif_reader import (
    format_filesize, format_exposure_time, format_f_number,
    format_focal_length, format_gps_dms, extract_full_metadata
)
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.faces.facerect import FaceRect
from picasa_py.ini.parser import PicasaIniParser


def test_exif_formatters():
    """
    FR: Vérifie les fonctions de conversion et de formatage des données EXIF.
    EN: Verify the conversion and formatting functions for EXIF data.
    """
    # Taille
    assert format_filesize(500) == "500 octets"
    assert "Ko" in format_filesize(150_000)
    assert "Mo" in format_filesize(3_500_000)

    # Temps de pose
    assert format_exposure_time(0.0125) == "1/80 s"
    assert format_exposure_time(0.004) == "1/250 s"
    assert format_exposure_time(2.0) == "2,0 s"

    # Ouverture
    assert format_f_number(2.8) == "f/2.8"
    assert format_f_number(4.0) == "f/4"

    # Focale
    assert format_focal_length(50.0) == "50,0 mm"

    # Coordonnées GPS
    formatted = format_gps_dms(48.8584, 2.2945, 35.0)
    assert "48°" in formatted
    assert "2°" in formatted
    assert "N" in formatted
    assert "E" in formatted
    assert "Alt: 35 m" in formatted


def test_right_drawer_panels_and_toggles(qapp):
    """
    FR: Vérifie l'instanciation, la bascule des onglets et l'escamotage du tiroir.
    EN: Verify instantiation, tab switching, and collapsing of the right drawer.
    """
    drawer = PicasaRightDrawer()
    drawer.resize(300, 600)

    # 1. Vérification des 4 onglets
    assert drawer.stack.count() == 4
    assert isinstance(drawer.panel_people, PicasaPeoplePanel)
    assert isinstance(drawer.panel_places, PicasaPlacesPanel)
    assert isinstance(drawer.panel_tags, PicasaTagsPanel)
    assert isinstance(drawer.panel_properties, PicasaPropertiesPanel)

    # 2. Ouvrir le panneau Personnes
    drawer.show_panel("people")
    assert drawer.isVisible()
    assert drawer.stack.currentIndex() == 0
    assert drawer.current_panel_name == "people"
    assert "Personnes" in drawer.lbl_title.text()

    # 3. Basculer sur Lieux
    drawer.show_panel("places")
    assert drawer.stack.currentIndex() == 1
    assert drawer.current_panel_name == "places"
    assert "Lieux" in drawer.lbl_title.text()

    # 4. Basculer sur Tags
    drawer.show_panel("tags")
    assert drawer.stack.currentIndex() == 2
    assert drawer.current_panel_name == "tags"
    assert "Tags" in drawer.lbl_title.text()

    # 5. Basculer sur Propriétés
    drawer.show_panel("properties")
    assert drawer.stack.currentIndex() == 3
    assert drawer.current_panel_name == "properties"
    assert "Propriétés" in drawer.lbl_title.text()

    # 6. Toggle : même panneau -> fermeture
    drawer.toggle_panel("properties")
    assert not drawer.isVisible()
    assert drawer.is_expanded is False

    # 7. Toggle : volet fermé -> ouverture
    drawer.toggle_panel("people")
    assert drawer.isVisible()
    assert drawer.stack.currentIndex() == 0


def test_tags_panel_persistence(qapp, tmp_path):
    """
    FR: Vérifie l'ajout, la suppression de tags et la persistance dans .picasa.ini.
    EN: Verify adding and removing tags and persistence in .picasa.ini.
    """
    # Créer une image et son dossier
    folder = tmp_path / "AlbumTest"
    folder.mkdir()
    photo_file = folder / "img1.jpg"
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    img.save(str(photo_file))

    panel = PicasaTagsPanel()
    panel.set_photo_path(str(photo_file))
    assert panel.current_tags == []

    # Ajouter un tag
    panel._add_tag_string("Vacances")
    panel._add_tag_string("Plage")
    assert "Vacances" in panel.current_tags
    assert "Plage" in panel.current_tags

    # Vérifier l'écriture dans .picasa.ini
    ini_path = folder / ".picasa.ini"
    assert ini_path.exists()
    with open(ini_path, "rb") as f:
        doc = PicasaIniParser.parse_bytes(f.read())
        saved_tags = doc.get_keywords("img1.jpg")
        assert "Vacances" in saved_tags
        assert "Plage" in saved_tags

    # Supprimer un tag
    panel._remove_tag("Plage")
    assert "Plage" not in panel.current_tags
    with open(ini_path, "rb") as f:
        doc2 = PicasaIniParser.parse_bytes(f.read())
        saved_tags2 = doc2.get_keywords("img1.jpg")
        assert "Vacances" in saved_tags2
        assert "Plage" not in saved_tags2


def test_places_panel_leaflet(qapp):
    """
    FR: Vérifie la génération de la vue cartographique Leaflet.
    EN: Verify generation of the Leaflet map view.
    """
    panel = PicasaPlacesPanel()
    panel.update_map(48.8584, 2.2945, "TourEiffel.jpg")
    assert panel.current_lat == 48.8584
    assert panel.current_lon == 2.2945
    assert "48°" in panel.lbl_coords.text()
    assert "2°" in panel.lbl_coords.text()


def test_one_up_right_drawer_integration(qapp, tmp_path):
    """
    FR: Vérifie l'intégration du volet droit dans le visualiseur One-Up.
    EN: Verify integration of the right drawer inside the One-Up viewer.
    """
    view = PicasaOneUpView()
    view.resize(1100, 700)
    view.show()

    # Par défaut, le volet droit est masqué
    assert view.right_drawer is not None
    assert not view.right_drawer.isVisible()

    # Les 4 boutons de bascule existent sur la barre inférieure
    assert view.btn_panel_people is not None
    assert view.btn_panel_places is not None
    assert view.btn_panel_tags is not None
    assert view.btn_panel_props is not None

    # Clic sur le bouton Lieux (Leaflet)
    view.btn_panel_places.click()
    assert view.right_drawer.isVisible()
    assert view.right_drawer.current_panel_name == "places"
    assert view.btn_panel_places.isChecked()

    # Clic sur le bouton Personnes
    view.btn_panel_people.click()
    assert view.right_drawer.isVisible()
    assert view.right_drawer.current_panel_name == "people"
    assert view.btn_panel_people.isChecked()
    assert not view.btn_panel_places.isChecked()

    # Re-clic sur Personnes -> fermeture
    view.btn_panel_people.click()
    assert not view.right_drawer.isVisible()
    assert not view.btn_panel_people.isChecked()


def test_right_drawer_lazy_updates(qapp, tmp_path):
    """
    FR: Vérifie que la sélection d'une photo lorsque le tiroir droit est masqué n'exécute pas de décodage
        ni de mise à jour des sous-volets tant que l'utilisateur n'ouvre pas le tiroir, et que seul l'onglet
        actif est rafraîchi à l'ouverture.
    EN: Verifies that selecting a photo while the right drawer is hidden does not execute decoding
        or subpanel updates until the user opens the drawer, and that only the active tab is refreshed on open.
    """
    folder = tmp_path / "LazyAlbum"
    folder.mkdir()
    photo_file = folder / "lazy1.jpg"
    img = Image.new("RGB", (120, 90), (80, 120, 160))
    img.save(str(photo_file))

    drawer = PicasaRightDrawer()
    drawer.hide()

    # Tant que le tiroir est masqué, set_current_photo marque les 4 panneaux comme dirty sans peupler la table EXIF
    drawer.set_current_photo(None, 0, str(photo_file))
    assert drawer._dirty_panels == {"people", "places", "tags", "properties"}
    assert drawer.panel_properties.table.rowCount() == 0

    # L'ouverture sur l'onglet "properties" rafraîchit uniquement "properties"
    drawer.show_panel("properties")
    assert "properties" not in drawer._dirty_panels
    assert {"people", "places", "tags"}.issubset(drawer._dirty_panels)
    assert drawer.panel_properties.table.rowCount() > 0

    # Le basculement sur "tags" rafraîchit alors "tags" à la demande
    drawer.show_panel("tags")
    assert "tags" not in drawer._dirty_panels
    assert drawer.panel_tags.photo_path == str(photo_file)


def test_one_up_right_drawer_shows_faces_when_opened(qapp, tmp_path):
    """
    FR: Vérifie que lorsqu'une photo contenant des visages est ouverte en grand (One-Up View),
        le volet latéral droit Personnes affiche bien tous les visages (« Dans cette photo »)
        que le volet soit ouvert après l'ouverture de la photo ou déjà ouvert avant.
    EN: Verifies that when a photo containing faces is opened in One-Up View,
        the People right drawer displays all faces ("In this photo") whether the drawer
        is opened after opening the photo or was already open beforehand.
    Ref: picasa3.exe @ rightdrawerpanel, PeoplePanel::InThisPhoto
    """
    from picasa_py.db.database import PicasaDatabase

    folder = tmp_path / "FacesOneUpAlbum"
    folder.mkdir()
    photo_file = folder / "group_photo.jpg"
    img = Image.new("RGB", (320, 240), (140, 160, 180))
    img.save(str(photo_file))

    db_dir = tmp_path / "db3"
    contacts_dir = tmp_path / "contacts"
    db_dir.mkdir(exist_ok=True)
    contacts_dir.mkdir(exist_ok=True)
    db = PicasaDatabase.open(db_dir, contacts_dir)
    photo_idx = db.add_media_record(str(folder) + "\\", "group_photo.jpg", 1000, 45000.0, 2)

    fm = db.face_manager
    fr1 = FaceRect(left=0.10, top=0.15, right=0.35, bottom=0.45)
    fr2 = FaceRect(left=0.55, top=0.20, right=0.80, bottom=0.50)
    fm.add_face(str(photo_file), fr1, "Alice Martin", db_idx=photo_idx)
    fm.add_face(str(photo_file), fr2, "Bob Dupont", db_idx=photo_idx)

    view = PicasaOneUpView()
    view.resize(1100, 700)

    # Cas 1 : le tiroir droit est fermé au moment de open_photo, puis ouvert par l'utilisateur
    view.open_photo(db, photo_idx, [photo_idx], direct_path=str(photo_file))
    view.toggle_drawer_panel("people")
    assert len(view.right_drawer.panel_people.faces) == 2
    names = {f.contact_name for f in view.right_drawer.panel_people.faces}
    assert names == {"Alice Martin", "Bob Dupont"}
    assert "(2)" in view.right_drawer.panel_people.header_lbl.text()

    # Cas 2 : le tiroir droit reste ouvert lorsqu'on ouvre la photo (y compris depuis un sous-enregistrement 1001)
    child_1001_indices = [
        i for i, r in enumerate(db.index) if r.type == 1001 and r.parent_idx == photo_idx
    ]
    assert len(child_1001_indices) >= 1
    view.open_photo(db, child_1001_indices[0], [child_1001_indices[0]], direct_path=str(photo_file))
    assert len(view.right_drawer.panel_people.faces) == 2


