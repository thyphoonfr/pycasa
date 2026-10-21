# tests/test_face_zoom_and_framing.py
"""FR: Tests de validation du cadrage des visages, de la résolution des enregistrements type 1001
et de la bascule Visages / Photos conforme à picasa3.exe.
EN: Validation tests for face framing, type 1001 record resolution,
and Faces / Photos toggle matching picasa3.exe.
Ref: picasa3.exe @ 0x009B93F0, 0x009B9290, 0x0057A4F0, 0x005E5290 (PeopleAlbumUseFaceSrc)
"""
import io
import os
from pathlib import Path
from PIL import Image
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.ui.thumbnail_view import PicasaThumbnailView, ThumbnailItem, AlbumSection


def test_face_record_parent_resolution():
    """FR: Vérifie qu'un enregistrement type 1001 dans thumbindex.db résout correctement
    sa photo parente et son chemin sur disque.
    EN: Verifies that a type 1001 record in thumbindex.db properly resolves
    its parent photo and its on-disk path.
    Ref: picasa3.exe @ 0x009B93F0, 0x0057A4F0
    """
    db = PicasaDatabase.open_default()
    if not db.index:
        pytest.skip("Base de données Picasa locale non disponible")

    face_indices = [i for i, r in enumerate(db.index) if r.type == 1001]
    if not face_indices:
        pytest.skip("Aucun enregistrement visage type 1001 trouvé dans la base")

    f_idx = face_indices[0]
    assert db.is_face_record(f_idx) is True

    parent_idx = db.get_face_parent_photo_idx(f_idx)
    assert parent_idx is not None
    assert 0 <= parent_idx < len(db.index)
    assert db.index[parent_idx].type != 1001

    full_path = db.get_media_full_path(f_idx)
    assert full_path != ""
    assert full_path == db.get_media_full_path(parent_idx)


def test_person_filter_items_count_and_pixmaps(qapp):
    """FR: Vérifie que filter_by_person charge bien tous les visages de la personne
    (pas seulement les photos directes) et que le cadrage visage est préservé.
    EN: Verifies that filter_by_person loads all faces of the person
    (not only direct photo records) and preserves face framing.
    Ref: picasa3.exe @ faceheaderpanel/face_zoom, picture_zoom
    """
    db = PicasaDatabase.open_default()
    if not db.face_manager.people:
        pytest.skip("Aucun contact dans la base Picasa")

    person = list(db.face_manager.people.values())[0]
    total_recs = len(person.photo_indices)

    tv = PicasaThumbnailView()
    tv.set_database(db)

    # Filtrer par cette personne
    tv.filter_by_person(person.contact_id, person.name, person.photo_indices)

    assert len(tv.visible_sections) == 1
    sec = tv.visible_sections[0]
    assert len(sec.item_indices) == total_recs
    assert sec.face_zoom is True

    # Vérifier l'avatar visage (mode Visages)
    first_item_idx = sec.item_indices[0]
    fz_pix = tv._get_face_pixmap(first_item_idx, person.contact_id)
    assert fz_pix is not None and not fz_pix.isNull()
    # Le visage doit avoir une hauteur de thumb_base_size (140) et un ratio proche de 5:6 (117x140)
    assert fz_pix.height() == tv.thumb_base_size
    assert 110 <= fz_pix.width() <= 125

    # Vérifier la bascule en mode Photos
    sec.face_zoom = False
    pz_pix = tv._get_parent_photo_pixmap(first_item_idx)
    assert pz_pix is not None and not pz_pix.isNull()

    # Rebascule en mode Visages
    sec.face_zoom = True
    fz_pix2 = tv._get_face_pixmap(first_item_idx, person.contact_id)
    assert fz_pix2 is not None and not fz_pix2.isNull()
    assert fz_pix2.size() == fz_pix.size()


def test_unnamed_faces_avatar_no_double_crop(qapp):
    """FR: Vérifie que pour les visages sans nom, le thumbnail extrait de thumbs_0.db
    pour un enregistrement type 1001 n'est pas recoupé une 2e fois.
    EN: Verifies that for unnamed faces, the thumbnail extracted from thumbs_0.db
    for a type 1001 record is not cropped a second time.
    Ref: picasa3.exe @ unknownfaceheaderpanel
    """
    db = PicasaDatabase.open_default()
    if not db.face_manager.unnamed_faces:
        pytest.skip("Aucun visage sans nom")

    tv = PicasaThumbnailView()
    tv.set_database(db)
    tv.filter_by_unnamed_faces(db.face_manager.unnamed_faces, grouped=False)

    assert len(tv.visible_sections) == 1
    sec = tv.visible_sections[0]
    assert len(sec.item_indices) == len(db.face_manager.unnamed_faces)

    first_item_idx = sec.item_indices[0]
    pix = tv._get_face_pixmap(first_item_idx, None)
    assert pix is not None and not pix.isNull()
    assert pix.height() == tv.thumb_base_size
    assert 110 <= pix.width() <= tv.thumb_base_size

    # Tester aussi le premier enregistrement type 1001 s'il existe
    f1001_pos = next((i for i, (idx, p, fr) in enumerate(db.face_manager.unnamed_faces) if idx is not None and db.is_face_record(idx)), None)
    if f1001_pos is not None:
        item_1001_idx = sec.item_indices[f1001_pos]
        pix_1001 = tv._get_face_pixmap(item_1001_idx, None)
        assert pix_1001 is not None and not pix_1001.isNull()
        assert pix_1001.height() == tv.thumb_base_size
        assert 110 <= pix_1001.width() <= 125


def test_to_avatar_pixmap_proportions():
    """FR: Vérifie que FaceRect.to_avatar_pixmap conserve les proportions exactes
    et ne déforme pas l'image.
    EN: Verifies that FaceRect.to_avatar_pixmap preserves exact aspect ratios
    and does not distort the image.
    Ref: picasa3.exe @ 0x009B93F0
    """
    # Image 120x144 (vignette Picasa type 1001 native)
    img_120_144 = Image.new("RGB", (120, 144), color=(200, 100, 50))
    pix = FaceRect.to_avatar_pixmap(img_120_144, avatar_size=140, circular=False)
    assert not pix.isNull()
    assert pix.height() == 140
    assert pix.width() == int(round(120 * 140 / 144.0))  # 117

    # Image carrée 200x200
    img_sq = Image.new("RGB", (200, 200), color=(50, 100, 200))
    pix_sq = FaceRect.to_avatar_pixmap(img_sq, avatar_size=64, circular=False)
    assert not pix_sq.isNull()
    assert pix_sq.width() == 64
    assert pix_sq.height() == 64

    # Circulaire
    pix_circ = FaceRect.to_avatar_pixmap(img_sq, avatar_size=64, circular=True)
    assert not pix_circ.isNull()
    assert pix_circ.width() == 64
    assert pix_circ.height() == 64
