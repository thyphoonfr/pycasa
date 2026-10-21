"""FR: Tests unitaires pour la détection et la gestion des visages (Option 2).
Vérifie :
1. Décodage et encodage bit-exact de rect64 (0x009B9190 / 0x009B91C0).
2. Calcul des coordonnées pixels et découpage d'avatar circulaire.
3. Regroupement par contact (PersonCluster) et synchronisation .picasa.ini / contacts.xml.
4. Affichage dans l'arborescence (PicasaLibraryTree) et filtrage par personne dans PicasaThumbnailView.

EN: Unit tests for face detection and face management (Option 2).
Verifies:
1. Bit-exact decoding and encoding of rect64 (0x009B9190 / 0x009B91C0).
2. Pixel coordinate computation and circular avatar cropping.
3. Contact clustering (PersonCluster) and .picasa.ini / contacts.xml synchronization.
4. Display in the library tree (PicasaLibraryTree) and person filtering in PicasaThumbnailView.

Ref: picasa3.exe @ 0x009B9190, 0x009B91C0, 0x0047A778
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
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _create_temp_face_db(tmp_path: Path) -> PicasaDatabase:
    """FR: Crée une base PicasaDatabase temporaire peuplée avec deux personnes synthétiques (Alice Martin et Bob Dupont).
    EN: Creates a temporary PicasaDatabase populated with two synthetic people (Alice Martin and Bob Dupont).
    """
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    img1_path = photos_dir / "photo1.jpg"
    img2_path = photos_dir / "photo2.jpg"
    Image.new("RGB", (400, 400), color=(200, 180, 160)).save(img1_path, quality=90)
    Image.new("RGB", (400, 400), color=(160, 180, 200)).save(img2_path, quality=90)

    db_dir = tmp_path / "db3"
    db = PicasaDatabase.create_new(db_dir)
    idx1 = db.add_media_record(str(photos_dir), "photo1.jpg", img1_path.stat().st_size)
    idx2 = db.add_media_record(str(photos_dir), "photo2.jpg", img2_path.stat().st_size)

    fm = PicasaFaceManager(db)
    fm.add_face(
        str(img1_path),
        FaceRect(left=0.2, top=0.2, right=0.6, bottom=0.6),
        "Alice Martin",
        db_idx=idx1,
    )
    fm.add_face(
        str(img2_path),
        FaceRect(left=0.3, top=0.3, right=0.7, bottom=0.7),
        "Bob Dupont",
        db_idx=idx2,
    )
    db._face_manager = fm
    return db


def test_rect64_bit_exact_encoding():
    """FR: Vérifie l'encodage et le décodage bit-exact des chaînes rect64.
    EN: Verifies bit-exact encoding and decoding of rect64 strings.
    """
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
    """FR: Vérifie la conversion en coordonnées pixels et le découpage d'avatar circulaire.
    EN: Verifies conversion to pixel coordinates and circular avatar cropping.
    """
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


def test_face_manager_loading(qapp, tmp_path):
    """FR: Vérifie le chargement des personnes et de leurs avatars dans PicasaFaceManager.
    EN: Verifies loading of people and their avatars in PicasaFaceManager.
    """
    db = _create_temp_face_db(tmp_path)
    fm = db.face_manager

    people = fm.get_people()
    assert len(people) >= 2

    # Alice Martin et Bob Dupont doivent être présents
    names = [p.name for p in people]
    assert "Alice Martin" in names
    assert "Bob Dupont" in names

    alice = next(p for p in people if p.name == "Alice Martin")
    assert alice.photo_count > 0
    assert alice.avatar_pixmap is not None
    assert not alice.avatar_pixmap.isNull()


def test_library_tree_people_population(qapp, tmp_path):
    """FR: Vérifie le peuplement de la catégorie Personnes dans l'arborescence PicasaLibraryTree.
    EN: Verifies population of the People category in the PicasaLibraryTree.
    """
    db = _create_temp_face_db(tmp_path)
    tree = PicasaLibraryTree()
    tree.populate_from_database(db)

    # La catégorie People doit contenir des enfants avec avatar et compteur
    people_cat = tree.cat_people
    assert people_cat is not None
    assert people_cat.childCount() >= 2

    first_child = people_cat.child(0)
    assert "(" in first_child.text(0)
    assert not first_child.icon(0).isNull()


def test_thumbnail_view_filter_by_person(qapp, tmp_path):
    """FR: Vérifie le filtrage des vignettes par personne dans PicasaThumbnailView.
    EN: Verifies thumbnail filtering by person in PicasaThumbnailView.
    """
    db = _create_temp_face_db(tmp_path)
    tv = PicasaThumbnailView()
    tv.set_database(db)

    fm = db.face_manager
    alice = next(p for p in fm.get_people() if p.name == "Alice Martin")

    # Filtrer par Alice Martin
    tv.filter_by_person(alice.contact_id, alice.name, alice.photo_indices)

    assert len(tv.visible_sections) == 1
    assert tv.visible_sections[0].name == "Alice Martin"
    assert len(tv.filtered_indices) > 0
    assert len(tv.filtered_indices) == len([i for i, item in enumerate(tv.items) if item.index in alice.photo_indices])


def test_red_cfg_full_deserialization_and_pure_python_engine():
    """FR: Vérifie que `RedCfgModel.load()` désérialise 100 % des 2 281 657 octets de `plugins\\red.cfg`
    (6 objets racines, 0 octet résiduel) et que `PurePythonRedEngine` produit des gabarits
    1044 octets `vqc_Cue` valides et compatibles avec `vqc_Relator::relate`.
    EN: Verifies that `RedCfgModel.load()` deserializes 100% of the 2,281,657 bytes of `plugins\\red.cfg`
    (6 root objects, 0 trailing bytes) and that `PurePythonRedEngine` produces valid 1044-byte
    `vqc_Cue` templates compatible with `vqc_Relator::relate`.
    """
    import numpy as np
    from picasa_py.db.blockfile import verify_face_template_blob
    from picasa_py.faces.red_engine_py import PurePythonRedEngine, RedCfgModel

    cfg_candidates = [
        Path("ui/resources/plugins/red.cfg"),
        Path(r"C:\Program Files (x86)\Google\Picasa3\plugins\red.cfg"),
        Path(r"C:\Program Files\Google\Picasa3\plugins\red.cfg"),
    ]
    cfg_path = next((p for p in cfg_candidates if p.is_file()), None)
    if cfg_path is None:
        pytest.skip("plugins\\red.cfg non installé sur la machine de test")

    model = RedCfgModel.load(cfg_path)
    assert model.total_bytes == 2_281_657
    assert model.fvc0_alt_mats.shape == (180, 16, 32)
    assert model.fvc1_alt_mats.shape == (60, 16, 32)
    assert model.sub_basis_90x3840.shape == (90, 3840)
    assert model.quant_indices_2000.shape == (2000,)
    assert model.quant_thresholds.shape == (2000, 15)
    assert model.relator_weights_2000.shape == (2000,)

    eng = PurePythonRedEngine(cfg_path)
    # Test de la géométrie d'yeux exacte (picasa3.exe @ 0x0047A778..0x0047AE64)
    l_f, t_f, r_f, b_f, adj_conf, roll = eng.compute_picasa_eye_box(
        89.0, 100.0, 111.0, 100.0, pan=0.0, conf=0.80, img_w=200, img_h=200
    )
    assert abs(l_f - 0.30) < 1e-5
    assert abs(r_f - 0.70) < 1e-5
    assert abs(t_f - 0.27) < 1e-5
    assert abs(b_f - 0.75) < 1e-5
    assert abs(adj_conf - 0.80) < 1e-5
    assert abs(roll) < 1e-5

    # Test de l'extraction vqc_Cue 1044 octets et de vqc_Relator::relate
    rng = np.random.default_rng(42)
    gray1 = rng.integers(30, 220, size=(200, 200), dtype=np.uint8)
    blob1, vec1 = eng.extract_vqc_cue_from_eyes(gray1, 80.0, 90.0, 120.0, 90.0)
    assert len(blob1) == 1044
    assert verify_face_template_blob(blob1)
    assert vec1.shape == (2000,)
    assert eng.relate_cues(blob1, blob1) > 0.9999


def test_face_detector_engine_switch():
    """FR: Vérifie le basculement entre le moteur natif ('native') et le moteur Python pur ('python')
    dans `PicasaPreferences` et `PicasaFaceDetector`.
    EN: Verifies switching between the native engine ('native') and the pure Python engine ('python')
    in `PicasaPreferences` and `PicasaFaceDetector`.
    """
    from picasa_py.db.preferences import PicasaPreferences
    from picasa_py.faces.detector import PicasaFaceDetector

    prev = PicasaPreferences.get_face_engine()
    try:
        PicasaPreferences.set_face_engine("python")
        assert PicasaPreferences.get_face_engine() == "python"

        det = PicasaFaceDetector(engine="python")
        assert det.get_engine() == "python"
        crop = Image.new("RGB", (160, 160), color=(140, 130, 120))
        feat = det.compute_face_feature(crop)
        if det._cfg_path:
            assert feat is not None
            assert len(feat) == 2000
            sim = det.compare_face_features(feat, feat)
            assert sim > 0.999

        det.set_engine("native")
        assert det.get_engine() == "native"
    finally:
        PicasaPreferences.set_face_engine(prev)


def test_face_high_res_disk_crop_over_low_res_parent_thumb(qapp, tmp_path):
    """FR: Vérifie que pour une photo complète (type != 1001), `get_face_avatar` découpe le visage
    depuis la photo originale haute résolution sur disque plutôt que depuis la minuscule vignette
    `144x108` de la photo entière dans `thumbs_0.db`.
    EN: Verifies that for a full photo (type != 1001), `get_face_avatar` crops the face from the
    high-resolution original photo on disk rather than from the tiny `144x108` whole-photo
    thumbnail in `thumbs_0.db`.
    """
    photos_dir = tmp_path / "photos_hr"
    photos_dir.mkdir(parents=True, exist_ok=True)
    img_path = photos_dir / "group_hr.jpg"

    # FR: Image haute résolution sur disque avec un visage rouge vif (255, 0, 0)
    # EN: High-resolution image on disk with a bright red face (255, 0, 0)
    hr_img = Image.new("RGB", (2000, 1500), color=(20, 20, 20))
    face_patch = Image.new("RGB", (200, 200), color=(255, 0, 0))
    hr_img.paste(face_patch, (900, 650))
    hr_img.save(img_path, "JPEG", quality=98)

    db_dir = tmp_path / "db3_hr"
    db = PicasaDatabase.create_new(db_dir)
    idx = db.add_media_record(str(photos_dir), "group_hr.jpg", img_path.stat().st_size)

    # FR: Stocker une vignette basse résolution bleue (0, 0, 255) dans thumbs_0.db pour prouver
    # que get_face_avatar privilégie la photo originale haute résolution sur disque
    # EN: Store a low-resolution blue (0, 0, 255) thumbnail in thumbs_0.db to prove that
    # get_face_avatar prioritizes the high-resolution on-disk original photo
    low_thumb = Image.new("RGB", (144, 108), color=(0, 0, 255))
    buf = io.BytesIO()
    low_thumb.save(buf, "JPEG", quality=80)
    db.get_thumbnail = lambda i, size="small": buf.getvalue()

    fr = FaceRect(left=900 / 2000.0, top=650 / 1500.0, right=1100 / 2000.0, bottom=850 / 1500.0)
    fm = PicasaFaceManager(db)
    pix = fm.get_face_avatar(str(img_path), fr, db_idx=idx, size=128, circular=False)
    assert pix is not None and not pix.isNull()
    qimg = pix.toImage()
    center_col = qimg.pixelColor(qimg.width() // 2, qimg.height() // 2)
    assert center_col.red() > 200
    assert center_col.blue() < 50

