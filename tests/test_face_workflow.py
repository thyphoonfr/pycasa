"""FR: Tests unitaires et d'intégration pour le flux complet de gestion des visages :
1. Détection automatique de visages (CFaceDetector / BgFaceDetectThread).
2. Ajout manuel d'une personne (peoplepanel/manual_add, PicasaNameFaceDialog).
3. Gestion et validation des suggestions de visages (confirmsug, suggestion_yes/no).
4. Modification et réassignation de la personne liée à un visage, et suppression.

EN: Unit and integration tests for the complete face management workflow:
1. Automatic face detection (CFaceDetector / BgFaceDetectThread).
2. Manual person addition (peoplepanel/manual_add, PicasaNameFaceDialog).
3. Management and validation of face suggestions (confirmsug, suggestion_yes/no).
4. Editing, reassigning a person linked to a face, and deletion.

Ref: picasa3.exe @ 0x0087ECD6 (BgFaceDetectThread)
Ref: picasa3.exe @ 0x008A1034 (peoplepanel/manual_add_editbox)
Ref: picasa3.exe @ 0x008A13B8 (peoplepanel/suggestion_yes, suggestion_no)
Ref: picasa3.exe @ 0x00896F74 (confirmsug, removesel)
Ref: AGENTS.md §3 & §4 (Compatibilité bit-exacte des fichiers .picasa.ini)
"""

import os
from pathlib import Path
import shutil
import tempfile
import pytest
from PIL import Image, ImageDraw

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect, decode_rect64_string, encode_rect64_string
from picasa_py.faces.detector import PicasaFaceDetector
from picasa_py.faces.face_manager import PicasaFaceManager, FaceSuggestion
from picasa_py.ini.parser import PicasaIniParser


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    return app


@pytest.fixture
def temp_photo_dir():
    """FR: Crée un répertoire temporaire avec des images de test.
    EN: Creates a temporary directory with test images.
    """
    temp_dir = tempfile.mkdtemp(prefix="pycasa_face_test_")
    
    # Créer une image 800x600 avec un ovale simulant une tête/visage
    img_path = os.path.join(temp_dir, "portrait.jpg")
    img = Image.new("RGB", (800, 600), color=(220, 220, 220))
    draw = ImageDraw.Draw(img)
    # Tête ovale
    draw.ellipse([300, 150, 500, 420], fill=(235, 195, 165), outline=(100, 60, 40), width=3)
    # Yeux
    draw.ellipse([345, 230, 375, 255], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
    draw.ellipse([355, 238, 368, 250], fill=(30, 80, 150))
    draw.ellipse([425, 230, 455, 255], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
    draw.ellipse([435, 238, 448, 250], fill=(30, 80, 150))
    # Bouche
    draw.arc([360, 320, 440, 370], start=0, end=180, fill=(180, 50, 50), width=3)
    img.save(img_path, quality=95)

    yield temp_dir, img_path

    # Nettoyage
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


def test_face_detector_direct_detection(temp_photo_dir):
    """FR: Vérifie l'exécution directe du détecteur de visages sur un fichier image.
    EN: Verifies direct execution of the face detector on an image file.
    """
    _, img_path = temp_photo_dir
    detector = PicasaFaceDetector.get()
    faces = detector.detect_faces_in_file(img_path)

    # Le détecteur OpenCV Haar cascade doit pouvoir s'exécuter sans erreur
    assert isinstance(faces, list)
    for f in faces:
        assert 0.0 <= f.left < f.right <= 1.0
        assert 0.0 <= f.top < f.bottom <= 1.0


def test_manual_face_addition_and_ini_persistence(qapp, temp_photo_dir):
    """FR: Vérifie l'ajout manuel d'un visage et sa persistance dans .picasa.ini.
    EN: Verifies manual face addition and its persistence in .picasa.ini.
    """
    temp_dir, img_path = temp_photo_dir
    db = PicasaDatabase.create_new(Path(temp_dir) / "db3")
    fm = PicasaFaceManager(db)

    # 1. Ajout manuel d'un visage
    manual_rect = FaceRect(left=0.35, top=0.20, right=0.65, bottom=0.60)
    added_face = fm.add_face(
        photo_path=img_path,
        face_rect=manual_rect,
        contact_name="Alice Dupont",
        db_idx=None
    )

    assert added_face.contact_name == "Alice Dupont"
    assert len(added_face.contact_id) == 16  # 16-hex characters Picasa format
    cid = added_face.contact_id

    # 2. Vérification de la création du fichier .picasa.ini
    ini_path = os.path.join(temp_dir, ".picasa.ini")
    assert os.path.exists(ini_path)

    doc = PicasaIniParser.parse_file(ini_path)
    # Doit contenir [Contacts2] avec cid=Alice Dupont;;
    sec_c2 = doc.get_section("Contacts2")
    assert sec_c2 is not None
    assert sec_c2.get(cid) == "Alice Dupont;;"

    # Doit contenir [portrait.jpg] avec faces=rect64(...),cid
    faces_items = doc.get_faces("portrait.jpg")
    assert len(faces_items) == 1
    assert faces_items[0].contact_id == cid
    assert faces_items[0].rect64 == manual_rect.to_rect64()[7:-1]

    # 3. Vérification du cluster en mémoire
    cluster = fm.get_person(cid)
    assert cluster is not None
    assert cluster.name == "Alice Dupont"
    assert img_path in cluster.photo_paths


def test_reassign_face_to_different_contact(qapp, temp_photo_dir):
    """FR: Vérifie la réassignation d'un visage à un autre contact et la mise à jour de .picasa.ini.
    EN: Verifies reassigning a face to a different contact and updating .picasa.ini.
    """
    temp_dir, img_path = temp_photo_dir
    db = PicasaDatabase.create_new(Path(temp_dir) / "db3")
    fm = PicasaFaceManager(db)

    # Ajouter initialement le visage pour Alice
    face1 = FaceRect(left=0.30, top=0.20, right=0.70, bottom=0.60)
    fm.add_face(img_path, face1, "Alice")
    alice_cid = face1.contact_id

    # Réassigner le visage à Bob
    face2 = fm.reassign_face(
        photo_path=img_path,
        old_face_rect=face1,
        new_contact_name="Bob Martin",
        db_idx=None
    )

    assert face2.contact_name == "Bob Martin"
    assert face2.contact_id != alice_cid
    bob_cid = face2.contact_id

    # Vérification dans le fichier .picasa.ini
    ini_path = os.path.join(temp_dir, ".picasa.ini")
    doc = PicasaIniParser.parse_file(ini_path)

    faces_items = doc.get_faces("portrait.jpg")
    assert len(faces_items) == 1
    assert faces_items[0].contact_id == bob_cid

    # Vérification que Bob est dans [Contacts2]
    sec_c2 = doc.get_section("Contacts2")
    assert sec_c2.get(bob_cid) == "Bob Martin;;"


def test_remove_face(qapp, temp_photo_dir):
    """FR: Vérifie la suppression d'un visage et le retrait de l'entrée dans .picasa.ini.
    EN: Verifies face removal and deletion of the entry in .picasa.ini.
    """
    temp_dir, img_path = temp_photo_dir
    db = PicasaDatabase.create_new(Path(temp_dir) / "db3")
    fm = PicasaFaceManager(db)

    face = FaceRect(left=0.25, top=0.25, right=0.60, bottom=0.60)
    fm.add_face(img_path, face, "Claire")

    # Vérifier que le visage est présent dans le .picasa.ini
    ini_path = os.path.join(temp_dir, ".picasa.ini")
    doc = PicasaIniParser.parse_file(ini_path)
    assert len(doc.get_faces("portrait.jpg")) == 1

    # Supprimer le visage
    fm.remove_face(img_path, face)

    # Vérifier que le .picasa.ini ne contient plus de balise faces pour cette photo
    doc2 = PicasaIniParser.parse_file(ini_path)
    assert len(doc2.get_faces("portrait.jpg")) == 0


def test_face_suggestions_validation_flow(qapp, temp_photo_dir):
    """FR: Vérifie le flux de validation des suggestions de visages (confirmsug).
    EN: Verifies the face suggestion validation workflow (confirmsug).
    """
    temp_dir, img_path = temp_photo_dir
    db = PicasaDatabase.create_new(Path(temp_dir) / "db3")
    fm = PicasaFaceManager(db)

    # Créer un contact connu "David"
    ref_face = FaceRect(left=0.1, top=0.1, right=0.4, bottom=0.4)
    fm.add_face(img_path, ref_face, "David")
    david_cid = ref_face.contact_id

    # Simuler une suggestion pour David
    sug_face = FaceRect(left=0.5, top=0.5, right=0.8, bottom=0.8)
    sug = FaceSuggestion(
        contact_id=david_cid,
        contact_name="David",
        photo_path=img_path,
        face_rect=sug_face,
        similarity=0.82,
        db_idx=None
    )
    fm.suggestions.setdefault(david_cid, []).append(sug)

    # Récupérer les suggestions pour David
    david_sugs = fm.get_suggestions(david_cid)
    assert len(david_sugs) == 1
    assert david_sugs[0].similarity == 0.82

    # Valider la suggestion
    confirmed_face = fm.confirm_suggestion(sug)
    assert confirmed_face.contact_id == david_cid
    assert confirmed_face.contact_name == "David"

    # Vérifier que la suggestion a été retirée de la liste
    assert len(fm.get_suggestions(david_cid)) == 0

    # Vérifier que les deux visages sont maintenant enregistrés dans le .picasa.ini
    ini_path = os.path.join(temp_dir, ".picasa.ini")
    doc = PicasaIniParser.parse_file(ini_path)
    faces = doc.get_faces("portrait.jpg")
    assert len(faces) == 2
    assert all(f.contact_id == david_cid for f in faces)


def test_avatar_crop_preserves_face_bounds(qapp):
    """FR: Vérifie que crop_avatar n'ampute pas le haut du front ni le bas du menton
    quand le visage est plus haut que large (ratio humain standard).
    EN: Verifies that crop_avatar does not clip the top of the forehead or bottom of the chin
    when the face is taller than wide (standard human aspect ratio).
    Ref: picasa3.exe @ 0x00456A15, 0x009B93F0
    """
    # Image 1000x1000 avec fond blanc
    img = Image.new("RGB", (1000, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Visage vertical entre y=200 et y=600 (hauteur 400), x=400 et x=600 (largeur 200)
    # Marqueur rouge au sommet du front (y=210)
    draw.rectangle([480, 205, 520, 220], fill=(255, 0, 0))
    # Marqueur bleu à la pointe du menton (y=590)
    draw.rectangle([480, 580, 520, 595], fill=(0, 0, 255))

    fr = FaceRect(left=0.4, top=0.2, right=0.6, bottom=0.6)
    avatar_pix = fr.crop_avatar(img, avatar_size=64, circular=False)

    assert not avatar_pix.isNull()
    assert avatar_pix.width() == 64
    assert avatar_pix.height() == 64

    # Convertir en QImage pour inspecter les pixels
    qimg = avatar_pix.toImage()
    # Le haut de l'avatar doit contenir du rouge (front) et le bas du bleu (menton)
    has_red = False
    has_blue = False
    for y in range(qimg.height()):
        for x in range(qimg.width()):
            col = qimg.pixelColor(x, y)
            if col.red() > 200 and col.green() < 50 and col.blue() < 50:
                has_red = True
            if col.blue() > 200 and col.red() < 50 and col.green() < 50:
                has_blue = True

    assert has_red, "Le front rouge a été amputé par le recadrage !"
    assert has_blue, "Le menton bleu a été amputé par le recadrage !"


def test_manual_face_avatar_with_exif_orientation(qapp, temp_photo_dir):
    """FR: Vérifie qu'une photo avec orientation EXIF produit un avatar exactement centré
    sur la zone sélectionnée à l'écran, sans décalage ni inversion 90°/270°.
    EN: Verifies that a photo with EXIF orientation produces an avatar accurately centered
    on the screen-selected region, without offset or 90°/270° inversion.
    """
    temp_dir, _ = temp_photo_dir
    exif_img_path = os.path.join(temp_dir, "exif_rotated.jpg")

    # Créer une image 600x400 (paysage) avec un visage rouge dans le coin haut-gauche
    raw_img = Image.new("RGB", (600, 400), color=(240, 240, 240))
    raw_draw = ImageDraw.Draw(raw_img)
    # Marqueur rouge spécifique
    raw_draw.rectangle([50, 50, 150, 150], fill=(255, 0, 0))

    # Ajouter tag EXIF Orientation 6 (rotation 90° horaire à l'affichage)
    exif = raw_img.getexif()
    exif[0x0112] = 6  # Orientation 6
    raw_img.save(exif_img_path, quality=95, exif=exif)

    # Charger l'image avec PicasaImageProcessor (orientation appliquée -> 400x600 portrait)
    from picasa_py.ui.image_processor import PicasaImageProcessor
    transformed = PicasaImageProcessor.load_transformed_image(exif_img_path)
    assert transformed is not None
    assert transformed.size == (400, 600)  # La largeur et hauteur sont inversées par EXIF 6

    # Dans l'image orientée, trouver la position du marqueur rouge
    # Coordonnées normalisées du marqueur rouge à l'écran
    # Par rotation 90° CW de (50, 50) dans 600x400: nouveau X = 400 - 150 = 250..350, Y = 50..150
    # Cherchons le rectangle du rouge dans l'image orientée
    red_coords = []
    for y in range(transformed.height):
        for x in range(transformed.width):
            r, g, b = transformed.getpixel((x, y))[:3]
            if r > 200 and g < 50 and b < 50:
                red_coords.append((x, y))

    assert len(red_coords) > 0
    min_x = min(c[0] for c in red_coords) / transformed.width
    min_y = min(c[1] for c in red_coords) / transformed.height
    max_x = max(c[0] for c in red_coords) / transformed.width
    max_y = max(c[1] for c in red_coords) / transformed.height

    # L'utilisateur sélectionne ce visage rouge sur l'écran
    selected_fr = FaceRect(left=min_x, top=min_y, right=max_x, bottom=max_y)

    # 1. Dialogue avec source_image = transformed
    from picasa_py.ui.name_face_dialog import PicasaNameFaceDialog
    dlg = PicasaNameFaceDialog(
        face_rect=selected_fr,
        photo_path=exif_img_path,
        existing_names=[],
        source_image=transformed
    )
    dlg_pix = dlg.avatar_lbl.pixmap()
    assert dlg_pix is not None and not dlg_pix.isNull()

    # Vérifier que l'avatar du dialogue contient le rouge
    dlg_qimg = dlg_pix.toImage()
    dlg_has_red = any(
        dlg_qimg.pixelColor(x, y).red() > 200 and dlg_qimg.pixelColor(x, y).green() < 50
        for y in range(dlg_qimg.height()) for x in range(dlg_qimg.width())
    )
    assert dlg_has_red, "L'avatar du dialogue doit contenir le visage sélectionné !"

    # 2. Ajout dans FaceManager avec source_image
    db = PicasaDatabase.create_new(Path(temp_dir) / "db3_exif")
    fm = PicasaFaceManager(db)
    added = fm.add_face(exif_img_path, selected_fr, "Élise", source_image=transformed)
    cluster = fm.get_person(added.contact_id)
    assert cluster is not None
    assert cluster.avatar_pixmap is not None

    cluster_qimg = cluster.avatar_pixmap.toImage()
    cluster_has_red = any(
        cluster_qimg.pixelColor(x, y).red() > 200 and cluster_qimg.pixelColor(x, y).green() < 50
        for y in range(cluster_qimg.height()) for x in range(cluster_qimg.width())
    )
    assert cluster_has_red, "L'avatar de la personne dans FaceManager doit contenir le visage sélectionné !"
