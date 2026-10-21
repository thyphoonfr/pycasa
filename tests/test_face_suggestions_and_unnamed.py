"""FR: Tests unitaires pour les suggestions de visages, les visages sans nom et les avatars.
EN: Unit tests for face suggestions, unnamed faces, and avatars.
Ref: picasa3.exe @ faceheaderpanel/sug_label, confirmsug, confirmsel, removesel
Ref: picasa3.exe @ unknownfaceheaderpanel/cluster, addname, ignore, CThumbDB::unknownfacealbum
Ref: AGENTS.md §4 bis.1 & §4 bis.2
"""

import os
import shutil
import tempfile
from PIL import Image, ImageDraw
import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import PicasaFaceManager, FaceSuggestion
from picasa_py.ui.thumbnail_view import PicasaThumbnailView
from picasa_py.ui.library_tree import PicasaLibraryTree
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.menu import PicasaMenuBuilder
from picasa_py.ui.main_window import PicasaMainWindow


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pycasa_test", "-platform", "offscreen"])
    return app


@pytest.fixture
def temp_face_env():
    """FR: Crée un environnement temporaire avec deux photos synthétiques et une base PicasaDatabase.
    EN: Creates a temporary environment with two synthetic photos and a PicasaDatabase.
    """
    td = tempfile.mkdtemp(prefix="pycasa_face_test_")
    db_dir = os.path.join(td, "db3")
    contacts_dir = os.path.join(td, "contacts")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(contacts_dir, exist_ok=True)

    # Photo 1 avec un faux visage
    photo1 = os.path.join(td, "photo1.jpg")
    img1 = Image.new("RGB", (400, 400), color=(200, 220, 240))
    d1 = ImageDraw.Draw(img1)
    d1.ellipse([100, 100, 300, 300], fill=(240, 200, 170), outline=(100, 50, 20))
    img1.save(photo1)

    # Photo 2 avec un deuxième visage
    photo2 = os.path.join(td, "photo2.jpg")
    img2 = Image.new("RGB", (400, 400), color=(210, 230, 220))
    d2 = ImageDraw.Draw(img2)
    d2.ellipse([120, 120, 280, 280], fill=(240, 200, 170), outline=(100, 50, 20))
    img2.save(photo2)

    db = PicasaDatabase.open(db_dir, contacts_dir)
    db.add_media_record(td + "\\", "photo1.jpg", 1001, 50000, 2)
    db.add_media_record(td + "\\", "photo2.jpg", 1002, 50000, 2)

    yield {
        "dir": td,
        "photo1": photo1,
        "photo2": photo2,
        "db": db,
    }

    try:
        shutil.rmtree(td)
    except Exception:
        pass


def test_person_avatar_generation(qapp, temp_face_env):
    """FR: Vérifie la génération et mise en cache d'avatar circulaire pour une personne.
    EN: Verifies generation and caching of a circular avatar for a person.
    """
    db = temp_face_env["db"]
    photo1 = temp_face_env["photo1"]

    fr = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    db.face_manager.add_face(photo1, fr, "Alice Test", db_idx=0)
    person = db.face_manager.get_people()[0]

    avatar = db.face_manager.get_person_avatar(person.contact_id, size=64)
    assert avatar is not None
    assert not avatar.isNull()
    assert avatar.width() == 64
    assert avatar.height() == 64

    # L'arborescence doit charger cet avatar comme icône
    tree = PicasaLibraryTree()
    tree.populate_from_database(db)
    assert tree.cat_people.childCount() == 1
    item = tree.cat_people.child(0)
    assert not item.icon(0).isNull()


def test_face_suggestions_lifecycle(qapp, temp_face_env):
    """FR: Vérifie le cycle complet de validation et rejet des suggestions de visages.
    EN: Verifies the complete validation and rejection lifecycle of face suggestions.
    """
    db = temp_face_env["db"]
    photo1 = temp_face_env["photo1"]
    photo2 = temp_face_env["photo2"]

    # Créer une personne
    fr1 = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    db.face_manager.add_face(photo1, fr1, "Bob Dupont", db_idx=0)
    bob = db.face_manager.get_people()[0]

    # Ajouter 2 suggestions pour Bob
    fr2 = FaceRect(left=0.3, top=0.3, right=0.7, bottom=0.7)
    sug1 = FaceSuggestion(
        contact_id=bob.contact_id,
        contact_name=bob.name,
        photo_path=photo2,
        face_rect=fr2,
        similarity=0.85,
        db_idx=1
    )
    fr3 = FaceRect(left=0.2, top=0.2, right=0.6, bottom=0.6)
    sug2 = FaceSuggestion(
        contact_id=bob.contact_id,
        contact_name=bob.name,
        photo_path=photo1,
        face_rect=fr3,
        similarity=0.78,
        db_idx=0
    )
    db.face_manager.suggestions[bob.contact_id] = [sug1, sug2]

    # Vérifier get_suggestions
    sugs = db.face_manager.get_suggestions(bob.contact_id)
    assert len(sugs) == 2

    # Obtenir un avatar de suggestion
    avatar = db.face_manager.get_face_avatar(sug1.photo_path, sug1.face_rect, sug1.db_idx, size=54)
    assert avatar is not None
    assert not avatar.isNull()

    # Valider sug1
    confirmed = db.face_manager.confirm_suggestion(sug1)
    assert confirmed is not None
    assert len(db.face_manager.get_suggestions(bob.contact_id)) == 1

    # Rejeter sug2
    db.face_manager.reject_suggestion(sug2)
    assert len(db.face_manager.get_suggestions(bob.contact_id)) == 0


def test_confirm_all_suggestions(qapp, temp_face_env):
    """FR: Vérifie le bouton 'Tout confirmer' (confirmsug).
    EN: Verifies the 'Confirm All' action (confirmsug).
    """
    db = temp_face_env["db"]
    photo1 = temp_face_env["photo1"]

    fr1 = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    db.face_manager.add_face(photo1, fr1, "Charlie", db_idx=0)
    charlie = db.face_manager.get_people()[0]

    sug1 = FaceSuggestion(charlie.contact_id, charlie.name, photo1, fr1, 0.90, 0)
    sug2 = FaceSuggestion(charlie.contact_id, charlie.name, photo1, fr1, 0.88, 0)
    db.face_manager.suggestions[charlie.contact_id] = [sug1, sug2]

    count = db.face_manager.confirm_all_suggestions(charlie.contact_id)
    assert count == 2
    assert len(db.face_manager.get_suggestions(charlie.contact_id)) == 0


def test_unnamed_faces_filtering_and_clustering(qapp, temp_face_env):
    """FR: Vérifie l'affichage, le clustering et le nommage en masse des visages sans nom.
    EN: Verifies display, clustering, and batch naming of unnamed faces.
    """
    db = temp_face_env["db"]
    photo1 = temp_face_env["photo1"]
    photo2 = temp_face_env["photo2"]

    fr1 = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    fr2 = FaceRect(left=0.30, top=0.30, right=0.70, bottom=0.70)
    db.face_manager.unnamed_faces = [
        (0, photo1, fr1),
        (1, photo2, fr2)
    ]

    thumb_view = PicasaThumbnailView()
    thumb_view.set_database(db)

    # Filtrer par visages sans nom (non groupé)
    thumb_view.filter_by_unnamed_faces(db.face_manager.unnamed_faces, grouped=False)
    assert len(thumb_view.visible_sections) == 1
    sec = thumb_view.visible_sections[0]
    assert sec.is_unnamed is True
    assert len(sec.item_indices) == 2

    # Filtrer par visages sans nom (groupé par similarité)
    thumb_view.filter_by_unnamed_faces(db.face_manager.unnamed_faces, grouped=True)
    assert len(thumb_view.visible_sections) >= 1
    assert all(s.is_unnamed for s in thumb_view.visible_sections)

    # Nommer le premier cluster
    cluster = thumb_view.visible_sections[0].cluster_faces
    if cluster:
        db.face_manager.name_cluster(cluster, "David Nommé")
        # Les visages nommés doivent maintenant faire partie des personnes
        people_names = [p.name for p in db.face_manager.get_people()]
        assert "David Nommé" in people_names


def test_language_switch_and_menu_update(qapp, temp_face_env):
    """FR: Vérifie que le changement de langue bascule immédiatement les menus.
    EN: Verifies that changing the language immediately updates the menus.
    """
    res = PicasaResourceManager.get()
    win = PicasaMainWindow(db_path=os.path.join(temp_face_env["dir"], "db3"))

    # Par défaut enUS
    res.set_language("enUS")
    win.menu_builder.build_menu_bar()
    actions_en = [m.title() for m in win.menuBar().findChildren(type(win.menuBar().addMenu("")))]
    assert "&File" in actions_en
    assert "&Edit" in actions_en

    # Basculer en français
    res.set_language("fr")
    win.menu_builder.build_menu_bar()
    actions_fr = [m.title() for m in win.menuBar().findChildren(type(win.menuBar().addMenu("")))]
    assert "&Fichier" in actions_fr
    assert "&Édition" in actions_fr

    # Rétablir en anglais US
    res.set_language("enUS")
    win.menu_builder.build_menu_bar()

    win.stop_background_tasks()
    win.close()
    qapp.processEvents()


def test_library_tree_refresh_and_category_translations(qapp):
    """FR: Vérifie que PicasaLibraryTree.refresh() fonctionne sans erreur et traduit les catégories.
    EN: Verifies that PicasaLibraryTree.refresh() runs without error and translates categories.
    """
    from picasa_py.ui.library_tree import PicasaLibraryTree
    from picasa_py.ui.style import PicasaStyle

    res = PicasaResourceManager.get()
    tree = PicasaLibraryTree(PicasaStyle())

    # refresh() sans base de données ne doit pas planter
    tree.refresh()

    # En français
    res.set_language("fr")
    tree.refresh()
    assert tree.cat_folders.text(0) == "Dossiers"
    assert tree.cat_albums.text(0) == "Albums"
    assert tree.cat_people.text(0) == "Personnes"

    # En anglais
    res.set_language("enUS")
    tree.refresh()
    assert tree.cat_folders.text(0) == "Folders"
    assert tree.cat_albums.text(0) == "Albums"
    assert tree.cat_people.text(0) == "People"


def test_pmp_unnamed_faces_and_unknownfacealbum(qapp, temp_face_env):
    """FR: Vérifie le chargement fidèle depuis imagedata_facerect, personalbumid et suggestionpersonalbumid.
    EN: Verifies faithful loading from imagedata_facerect, personalbumid, and suggestionpersonalbumid.
    Ref: CThumbDB::unknownfacealbum @ 0x008AAD76
    """
    from picasa_py.db.pmp import PmpFile, PmpType
    from picasa_py.faces.face_manager import PicasaFaceManager
    from picasa_py.faces.facerect import FaceRect

    db = temp_face_env["db"]

    # Simuler albumdata avec Album 0 = Sans nom (cat 8), Album 1 = Jean (cat 8)
    ad_names = PmpFile(PmpType.STRING, ["Sans nom", "Jean"])
    ad_cats = PmpFile(PmpType.UINT32, [8, 8])
    ad_cids = PmpFile(PmpType.UINT64, [0, 0x1234567890ABCDEF])
    db.pmps["albumdata_name"] = ad_names
    db.pmps["albumdata_category"] = ad_cats
    db.pmps["albumdata_albumcontactids"] = ad_cids

    fr_val1 = FaceRect(0.2, 0.2, 0.4, 0.4).to_uint64()
    fr_val2 = FaceRect(0.5, 0.5, 0.7, 0.7).to_uint64()
    fr_val3 = FaceRect(0.1, 0.1, 0.3, 0.3).to_uint64()

    db.pmps["imagedata_facerect"] = PmpFile(PmpType.UINT64, [fr_val1, fr_val2, fr_val3])
    db.pmps["imagedata_personalbumid"] = PmpFile(PmpType.UINT32, [1, 0, 0])
    db.pmps["imagedata_suggestionpersonalbumid"] = PmpFile(PmpType.UINT32, [0, 1, 0])

    fm = PicasaFaceManager(db)

    # Album 0 ("Sans nom") ne doit PAS être dans les PersonCluster
    assert "pers_0000" not in fm.people
    assert "1234567890abcdef" in fm.people

    # Photo 0 est assignée à Jean
    jean = fm.people["1234567890abcdef"]
    assert len(jean.photo_indices) == 1
    assert jean.photo_indices[0] == 0

    # Photo 1 est une suggestion pour Jean
    sugs = fm.get_suggestions("1234567890abcdef")
    assert len(sugs) == 1
    assert sugs[0].db_idx == 1

    # Photo 2 est un visage sans nom
    assert len(fm.unnamed_faces) == 1
    assert fm.unnamed_faces[0][0] == 2


def test_unnamed_faces_button_layout_and_ungrouping(qapp, temp_face_env):
    """FR: Vérifie que les boutons 'Grouper par visage', 'Dissocier' et 'Diaporama'
    ne se chevauchent pas dans la géométrie du header, et que le clic sur 'Dissocier'
    remet la vue en mode non groupé.
    EN: Verifies that the 'Group by face', 'Ungroup', and 'Slideshow' buttons
    do not overlap in the header geometry, and clicking 'Ungroup' returns the view to ungrouped mode.
    Ref: picasa3.exe @ unknownfaceheaderpanel
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt, QEvent

    db = temp_face_env["db"]
    photo1 = temp_face_env["photo1"]
    photo2 = temp_face_env["photo2"]

    fr1 = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    fr2 = FaceRect(left=0.30, top=0.30, right=0.70, bottom=0.70)
    db.face_manager.unnamed_faces = [
        (0, photo1, fr1),
        (1, photo2, fr2)
    ]

    thumb_view = PicasaThumbnailView()
    thumb_view.resize(1000, 600)
    thumb_view.set_database(db)

    # 1. Vérification du non-chevauchement des rectangles
    y = 50
    slideshow_r = thumb_view._get_slideshow_btn_rect(y)
    cluster_r = thumb_view._get_cluster_action_btn_rect(y)
    ungroup_r = thumb_view._get_ungroup_action_btn_rect(y)
    ignore_r = thumb_view._get_ignore_action_btn_rect(y)

    assert not slideshow_r.intersects(cluster_r), "Le bouton Grouper/Nommer ne doit pas chevaucher le bouton Diaporama !"
    assert not cluster_r.intersects(ungroup_r), "Le bouton Développer ne doit pas chevaucher le bouton Nommer !"
    assert not ungroup_r.intersects(ignore_r), "Le bouton Ignorer ne doit pas chevaucher Développer !"
    assert not slideshow_r.intersects(ungroup_r)
    # L'ordre de droite à gauche doit être : Diaporama, Nommer, Développer, Ignorer
    assert ignore_r.right() < ungroup_r.left() < cluster_r.left() < slideshow_r.left()

    # 2. Affichage groupé
    thumb_view.filter_by_unnamed_faces(db.face_manager.unnamed_faces, grouped=True)
    assert len(thumb_view.visible_sections) >= 1
    assert thumb_view.visible_sections[0].cluster_faces is not None

    # 3. Clic sur le bouton 'Développer les groupes' (ungroup)
    from PySide6.QtCore import QPointF
    sec = thumb_view.visible_sections[0]
    sec_top = sec.y_start - thumb_view.scroll_y
    btn_ungroup = thumb_view._get_ungroup_action_btn_rect(sec_top)
    click_pt = QPointF(btn_ungroup.center())
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        click_pt,
        click_pt,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    thumb_view.mousePressEvent(event)

    # Doit être revenu au mode non groupé (1 seule section générale pour les visages sans nom)
    assert len(thumb_view.visible_sections) == 1
    assert thumb_view.visible_sections[0].cluster_faces is None
    assert thumb_view.visible_sections[0].is_unnamed is True
