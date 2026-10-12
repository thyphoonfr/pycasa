"""
Tests de validation du volet latéral droit (PicasaRightDrawer) et de ses 4 panneaux :
- Personnes (People Panel)
- Lieux (Places Panel avec Leaflet)
- Tags (Mots-clés et synchronisation .picasa.ini)
- Propriétés (Image Properties / EXIF)

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
    """Vérifie les fonctions de conversion et de formatage des données EXIF."""
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
    """Vérifie l'instanciation, la bascule des onglets et l'escamotage du tiroir."""
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
    """Vérifie l'ajout, la suppression de tags et la persistance dans .picasa.ini."""
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
    """Vérifie la génération de la vue cartographique Leaflet."""
    panel = PicasaPlacesPanel()
    panel.update_map(48.8584, 2.2945, "TourEiffel.jpg")
    assert panel.current_lat == 48.8584
    assert panel.current_lon == 2.2945
    assert "48°" in panel.lbl_coords.text()
    assert "2°" in panel.lbl_coords.text()


def test_one_up_right_drawer_integration(qapp, tmp_path):
    """Vérifie l'intégration du volet droit dans le visualiseur One-Up."""
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
