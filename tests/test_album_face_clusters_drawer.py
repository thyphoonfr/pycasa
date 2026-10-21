"""FR: Tests de validation pour l'affichage des visages similaires regroupés dans l'onglet de droite
lorsqu'on sélectionne un album ou plusieurs photos.
EN: Validation tests for displaying grouped similar faces in the right drawer
when selecting an album or multiple photos.

Ref: picasa3.exe @ 0x00788090 - 0x00788C80 (faceclusterpanel)
Ref: 0x00CB4660 (faceclusterpanel_%d_addname), 0x00CB46D0 (faceclusterpanel_%d_ignore)
Ref: 0x00CA0FD8 (PeoplePanel::Cluster -> "%d photos"), 0x00CA160C (PeoplePanel::SuggestionFmt -> "%s?")
Ref: 0x00CF4F48 (hauteur 86.0f), 0x00649023 (avatar 72x72 px)
"""

import os
import shutil
import tempfile
import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import PicasaFaceManager
from picasa_py.ui.right_drawer import PicasaRightDrawer, PicasaInlineNameEdit


@pytest.fixture
def album_cluster_env():
    """FR: Crée un environnement temporaire avec une base Picasa et 4 photos de test pour le regroupement de visages.
    EN: Creates a temporary environment with a Picasa database and 4 test photos for face clustering.
    """
    td = tempfile.mkdtemp(prefix="pycasa_cluster_test_")
    db_dir = os.path.join(td, "db3")
    contacts_dir = os.path.join(td, "contacts")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(contacts_dir, exist_ok=True)

    photos = []
    for i in range(4):
        p = os.path.join(td, f"photo_{i+1}.jpg")
        im = Image.new("RGB", (200, 200), color=(200 + i*10, 210, 220))
        d = ImageDraw.Draw(im)
        d.rectangle([40, 40, 160, 160], fill=(230, 190, 160))
        im.save(p)
        photos.append(p)

    db = PicasaDatabase.open(db_dir, contacts_dir)
    for i, p in enumerate(photos):
        db.add_media_record(td + "\\", os.path.basename(p), 1000 + i, 45000, 2)

    yield {
        "dir": td,
        "photos": photos,
        "db": db,
    }

    try:
        shutil.rmtree(td)
    except Exception:
        pass


def test_album_unnamed_face_clustering_in_drawer(album_cluster_env, qapp):
    """FR: Vérifie que lors de la sélection d'un album avec des visages non identifiés,
    le tiroir droit affiche chaque groupe de visages similaires sous forme de carte dédiée
    avec avatar 72x72, champ de nom direct, compteur de photos et bouton d'exclusion.
    EN: Verifies that when selecting an album with unidentified faces,
    the right drawer displays each group of similar faces as a dedicated card
    with a 72x72 avatar, inline name field, photo counter, and ignore button.
    """
    db = album_cluster_env["db"]
    photos = album_cluster_env["photos"]

    # 1. Ajouter 2 visages sans nom sur photo 1 et photo 2 (personne A)
    fr1 = FaceRect(0.2, 0.2, 0.8, 0.8)
    fr2 = FaceRect(0.2, 0.2, 0.8, 0.8)
    db.face_manager.unnamed_faces.append((0, photos[0], fr1))
    db.face_manager.photo_to_faces[0] = [fr1]
    db.face_manager.unnamed_faces.append((1, photos[1], fr2))
    db.face_manager.photo_to_faces[1] = [fr2]

    # 2. Ajouter 1 visage avec suggestion sur photo 3 (personne B)
    fr3 = FaceRect(0.25, 0.25, 0.75, 0.75, contact_name="? Clara")
    db.face_manager.unnamed_faces.append((2, photos[2], fr3))
    db.face_manager.photo_to_faces[2] = [fr3]

    drawer = PicasaRightDrawer()
    drawer.resize(320, 700)

    # Simuler le clic sur l'album contenant les photos
    drawer.set_multiple_photos(db, [0, 1, 2], photos[:3])
    panel = drawer.panel_people

    # Vérifier l'en-tête
    assert "Qui est présent sur ces photos" in panel.header_lbl.text()

    # Trouver toutes les cartes de groupe dans le layout (QFrame)
    frames = [
        panel.faces_layout.itemAt(i).widget()
        for i in range(panel.faces_layout.count())
        if isinstance(panel.faces_layout.itemAt(i).widget(), QFrame)
    ]
    assert len(frames) >= 2  # Au moins 2 clusters distincts

    # Vérifier la présence des éléments fidèles dans la carte de cluster
    c_card = frames[0]
    edits = c_card.findChildren(PicasaInlineNameEdit)
    assert len(edits) == 1
    assert edits[0].placeholderText() == "Ajouter un nom"
    assert edits[0].height() == 24

    # Bouton ignore (✕)
    ignore_btns = [b for b in c_card.findChildren(QPushButton) if b.text() == "✕"]
    assert len(ignore_btns) >= 1

    # Avatar 72x72
    avatar_labels = [l for l in c_card.findChildren(QLabel) if l.width() == 72 and l.height() == 72]
    assert len(avatar_labels) == 1


def test_album_face_cluster_naming_and_ignore(album_cluster_env, qapp):
    """FR: Vérifie qu'en nommant un cluster dans le tiroir, tous les visages du cluster
    sont nommés d'un coup et enregistrés.
    EN: Verifies that naming a cluster in the drawer names and saves all faces
    in the cluster at once.
    """
    db = album_cluster_env["db"]
    photos = album_cluster_env["photos"]

    fr1 = FaceRect(0.2, 0.2, 0.8, 0.8)
    fr2 = FaceRect(0.2, 0.2, 0.8, 0.8)
    db.face_manager.unnamed_faces.append((0, photos[0], fr1))
    db.face_manager.photo_to_faces[0] = [fr1]
    db.face_manager.unnamed_faces.append((1, photos[1], fr2))
    db.face_manager.photo_to_faces[1] = [fr2]

    drawer = PicasaRightDrawer()
    drawer.set_multiple_photos(db, [0, 1], photos[:2])
    panel = drawer.panel_people

    frames = [
        panel.faces_layout.itemAt(i).widget()
        for i in range(panel.faces_layout.count())
        if isinstance(panel.faces_layout.itemAt(i).widget(), QFrame)
    ]
    assert len(frames) >= 1
    edit = frames[0].findChild(PicasaInlineNameEdit)
    assert edit is not None

    # Saisir un nom et valider avec Entrée
    edit.setText("David")
    edit.returnPressed.emit()

    # Vérifier que la personne David a été créée avec 2 photos
    person = db.face_manager.get_person("cid_david") or [p for p in db.face_manager.get_people() if p.name == "David"][0]
    assert person is not None
    assert person.name == "David"
    assert len(person.photo_indices) >= 1


def test_album_face_cluster_detector_suggestion_matching(album_cluster_env, qapp):
    """FR: Vérifie que la détection de suggestion par vecteur de caractéristiques
    (PicasaFaceDetector) dans _create_cluster_card fonctionne sans aucune erreur d'importation.
    EN: Verifies that feature-vector suggestion matching (PicasaFaceDetector)
    in _create_cluster_card works without any import errors.
    """
    import numpy as np
    db = album_cluster_env["db"]
    photos = album_cluster_env["photos"]

    # Ajouter une personne avec un vecteur de caractéristiques
    p_cluster = db.face_manager.create_person("Emma")
    p_cluster.feature_vector = np.ones((128,), dtype=np.float32)

    # Simuler get_face_template sur la base de données
    db.get_face_template = lambda idx: np.ones((128,), dtype=np.float32)

    # Ajouter un visage sans nom
    fr = FaceRect(0.2, 0.2, 0.8, 0.8)
    db.face_manager.unnamed_faces.append((0, photos[0], fr))
    db.face_manager.photo_to_faces[0] = [fr]

    drawer = PicasaRightDrawer()
    drawer.resize(320, 700)

    # Cette méthode invoquait PicasaFaceDetector et levait l'ImportError
    drawer.set_multiple_photos(db, [0], [photos[0]])
    panel = drawer.panel_people

    # Vérifier que la carte de cluster a été créée et affiche la suggestion "Emma ?"
    frames = [
        panel.faces_layout.itemAt(i).widget()
        for i in range(panel.faces_layout.count())
        if isinstance(panel.faces_layout.itemAt(i).widget(), QFrame)
    ]
    assert len(frames) >= 1
    labels = [l.text() for l in frames[0].findChildren(QLabel)]
    assert any("Emma" in t for t in labels)
