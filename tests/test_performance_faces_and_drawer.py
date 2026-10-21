"""
FR: Tests de non-régression de performance pour l'ouverture, l'affichage des visages sans nom,
la navigation dans les personnes et le tiroir latéral.
EN: Performance non-regression tests for opening, displaying unnamed faces,
browsing people, and the right-hand side drawer.
Ref: AGENTS.md §4 ter (Performances comparables à l'original)
"""

import os
import tempfile
import time
import pytest
from PIL import Image
from PySide6.QtCore import Qt

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.ui.main_window import PicasaMainWindow
from picasa_py.ui.thumbnail_view import PicasaThumbnailView
from picasa_py.ui.right_drawer import PicasaRightDrawer


@pytest.fixture
def perf_env():
    """
    FR: Prépare un environnement de test avec 50 photos, 150 visages sans nom et une personne avec 40 visages.
    EN: Prepare a test environment with 50 photos, 150 unnamed faces, and a person with 40 faces.
    """
    td = tempfile.mkdtemp(prefix="pycasa_perf_test_")
    db_dir = os.path.join(td, "db3")
    contacts_dir = os.path.join(td, "contacts")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(contacts_dir, exist_ok=True)

    # Créer 50 photos de test
    photos = []
    for i in range(50):
        p = os.path.join(td, f"img_{i:03d}.jpg")
        im = Image.new("RGB", (100, 100), color=(100, 120, 140))
        im.save(p)
        photos.append(p)

    db = PicasaDatabase.open(db_dir, contacts_dir)
    for i, p in enumerate(photos):
        db.add_media_record(td + "\\", os.path.basename(p), 1000 + i, 45000, 2)

    # Ajouter 150 visages sans nom
    for i in range(150):
        p_idx = i % len(photos)
        fr = FaceRect(0.1, 0.1, 0.9, 0.9)
        db.face_manager.unnamed_faces.append((p_idx, photos[p_idx], fr))
        db.face_manager.photo_to_faces.setdefault(p_idx, []).append(fr)

    # Ajouter une personne avec 40 visages
    person = db.face_manager.create_person("Alice")
    for i in range(40):
        p_idx = i % len(photos)
        fr_p = FaceRect(0.2, 0.2, 0.8, 0.8, contact_id=person.contact_id, contact_name="Alice")
        person.photo_indices.append(p_idx)
        person.photo_paths.append(photos[p_idx])
        db.face_manager.photo_to_faces.setdefault(p_idx, []).append(fr_p)

    yield {"dir": td, "db": db, "photos": photos, "person": person}


def test_unnamed_faces_selection_performance(perf_env, qapp):
    """
    FR: Vérifie que la sélection de Sans nom avec 150 visages s'exécute en moins de 300 ms.
    EN: Verify that selecting Unnamed faces with 150 faces executes in under 300 ms.
    """
    db = perf_env["db"]
    tv = PicasaThumbnailView()
    tv.set_database(db)

    t0 = time.perf_counter()
    tv.filter_by_unnamed_faces(db.face_manager.unnamed_faces)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.3, f"filter_by_unnamed_faces trop lent : {elapsed:.3f}s"
    assert len(tv.visible_sections) >= 1
    assert len(tv.visible_sections[0].item_indices) == 150


def test_person_selection_performance(perf_env, qapp):
    """
    FR: Vérifie que la sélection d'une personne avec de nombreux visages s'exécute en moins de 100 ms.
    EN: Verify that selecting a person with many faces executes in under 100 ms.
    """
    db = perf_env["db"]
    person = perf_env["person"]
    tv = PicasaThumbnailView()
    tv.set_database(db)

    t0 = time.perf_counter()
    tv.filter_by_person(person.contact_id, person.name, person.photo_indices)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.1, f"filter_by_person trop lent : {elapsed:.3f}s"
    assert len(tv.visible_sections) >= 1
    assert len(tv.visible_sections[0].item_indices) == 40


def test_drawer_multiple_photos_performance(perf_env, qapp):
    """
    FR: Vérifie que set_multiple_photos dans le tiroir droit pour 150 visages sans nom reste sous 500 ms.
    EN: Verify that set_multiple_photos in the right drawer for 150 unnamed faces stays under 500 ms.
    """
    db = perf_env["db"]
    drawer = PicasaRightDrawer()
    drawer.resize(320, 700)

    indices = [u[0] for u in db.face_manager.unnamed_faces if u[0] is not None]
    paths = [u[1] for u in db.face_manager.unnamed_faces]

    t0 = time.perf_counter()
    drawer.set_multiple_photos(db, indices, paths)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.5, f"drawer.set_multiple_photos trop lent : {elapsed:.3f}s"
    # Vérifier que le panneau a bien créé les widgets
    assert drawer.panel_people.faces_layout.count() > 0
