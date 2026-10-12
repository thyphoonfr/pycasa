"""
Tests unitaires pour la détection et la gestion des visages (Option 2).

Vérifie :
1. Décodage et encodage bit-exact de rect64 (0x009B9190 / 0x009B91C0).
2. Calcul des coordonnées pixels et découpage d'avatar circulaire.
3. Regroupement par contact (PersonCluster) et synchronisation .picasa.ini / contacts.xml.
4. Affichage dans l'arborescence (PicasaLibraryTree) et filtrage par personne dans PicasaThumbnailView.
"""

import io
from pathlib import Path
import pytest
from PIL import Image

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import (
    FaceRect,
    decode_rect64_string,
    encode_rect64_string,
    decode_rect64_uint64,
    encode_rect64_uint64,
)
from picasa_py.faces.face_manager import PicasaFaceManager, PersonCluster
from picasa_py.ui.library_tree import PicasaLibraryTree
from picasa_py.ui.thumbnail_view import PicasaThumbnailView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_rect64_bit_exact_encoding():
    # Coordonnées réelles issues de .picasa.ini
    samples = [
        "rect64(22ff08a2e2319d9a)",
        "rect64(3a4400008b119b9d)",
        "rect64(804c464ba47a87d1)",
        "rect64(ac4f3264da8c85a8)",
        "rect64(668d27db902c72ef)",
    ]

    for sample in samples:
        l, t, r, b = decode_rect64_string(sample)
        # Vérifier la cohérence géométrique (left < right et top < bottom)
        assert 0.0 <= l < r <= 1.0
        assert 0.0 <= t < b <= 1.0

        # Ré-encodage bit-exact
        encoded = encode_rect64_string(l, t, r, b)
        assert encoded == sample


def test_facerect_pixel_and_avatar(qapp):
    # Créer une image 800x600 avec un "visage" dessiné au centre
    img = Image.new("RGB", (800, 600), color=(200, 200, 200))
    # Visage normalisé: L=0.3, T=0.2, R=0.7, B=0.6
    fr = FaceRect(left=0.3, top=0.2, right=0.7, bottom=0.6, contact_id="test1234", contact_name="Alice")

    px, py, pw, ph = fr.to_pixel_rect(800, 600)
    assert px == 240
    assert py == 120
    assert pw == 320
    assert ph == 240

    # Découpage de l'avatar circulaire
    avatar_pix = fr.crop_avatar(img, avatar_size=64, circular=True)
    assert not avatar_pix.isNull()
    assert avatar_pix.width() == 64
    assert avatar_pix.height() == 64


def test_face_manager_loading():
    db = PicasaDatabase.open_default()
    fm = PicasaFaceManager(db)

    people = fm.get_people()
    assert len(people) >= 2

    # Yann Lebrun et Egone Lebrun doivent être présents
    names = [p.name for p in people]
    assert "Yann Lebrun" in names
    assert "Egone Lebrun" in names

    yann = next(p for p in people if p.name == "Yann Lebrun")
    assert yann.photo_count > 0
    assert yann.avatar_pixmap is not None
    assert not yann.avatar_pixmap.isNull()


def test_library_tree_people_population(qapp):
    db = PicasaDatabase.open_default()
    tree = PicasaLibraryTree()
    tree.populate_from_database(db)

    # La catégorie People doit contenir des enfants avec avatar et compteur
    people_cat = tree.cat_people
    assert people_cat is not None
    assert people_cat.childCount() >= 2

    first_child = people_cat.child(0)
    assert "(" in first_child.text(0)
    assert not first_child.icon(0).isNull()


def test_thumbnail_view_filter_by_person(qapp):
    db = PicasaDatabase.open_default()
    tv = PicasaThumbnailView()
    tv.set_database(db)

    fm = db.face_manager
    yann = next(p for p in fm.get_people() if p.name == "Yann Lebrun")

    # Filtrer par Yann Lebrun
    tv.filter_by_person(yann.contact_id, yann.name, yann.photo_indices)

    assert len(tv.visible_sections) == 1
    assert tv.visible_sections[0].name == "Yann Lebrun"
    assert len(tv.filtered_indices) > 0
    assert len(tv.filtered_indices) == len([i for i, item in enumerate(tv.items) if item.index in yann.photo_indices])
