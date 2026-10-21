"""
FR: Tests de validation pour :
1. Le filtre de suggestions de personnes (faceheaderpanel/sug_filter, confirmsug).
2. L'affichage multi-sélection dans le volet des personnes (PeoplePanel::Known2, Who).
3. Le câblage complet de gestion des visages (détection, suggestions, validation, rejet).
EN: Validation tests for:
1. Person suggestion filter (faceheaderpanel/sug_filter, confirmsug).
2. Multi-selection display in the People panel (PeoplePanel::Known2, Who).
3. Complete face management wiring (detection, suggestions, confirmation, rejection).
Ref: picasa3.exe @ FACEHEADERPANELTEXT_FR.XML, PEOPLEPANEL_TEXT_FR.XML, 0x005E16EA, 0x0074B9D6, 0x00CA1264
"""

import os
import shutil
import tempfile
import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.faces.face_manager import PicasaFaceManager, FaceSuggestion
from picasa_py.ui.thumbnail_view import PicasaThumbnailView, AlbumSection, ThumbnailItem
from picasa_py.ui.right_drawer import PicasaRightDrawer, PicasaPeoplePanel


@pytest.fixture
def temp_face_test_env():
    """
    FR: Crée un environnement de test temporaire avec 3 photos et une base Picasa isolée.
    EN: Create a temporary test environment with 3 photos and an isolated Picasa database.
    """
    td = tempfile.mkdtemp(prefix="pycasa_sug_test_")
    db_dir = os.path.join(td, "db3")
    contacts_dir = os.path.join(td, "contacts")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(contacts_dir, exist_ok=True)

    photo1 = os.path.join(td, "photo1.jpg")
    photo2 = os.path.join(td, "photo2.jpg")
    photo3 = os.path.join(td, "photo3.jpg")

    for p in (photo1, photo2, photo3):
        im = Image.new("RGB", (200, 200), color=(220, 210, 200))
        d = ImageDraw.Draw(im)
        d.ellipse([50, 50, 150, 150], fill=(240, 200, 170))
        im.save(p)

    db = PicasaDatabase.open(db_dir, contacts_dir)
    db.add_media_record(td + "\\", "photo1.jpg", 1001, 50000, 2)
    db.add_media_record(td + "\\", "photo2.jpg", 1002, 50000, 2)
    db.add_media_record(td + "\\", "photo3.jpg", 1003, 50000, 2)

    yield {
        "dir": td,
        "photo1": photo1,
        "photo2": photo2,
        "photo3": photo3,
        "db": db,
    }

    try:
        shutil.rmtree(td)
    except Exception:
        pass


def test_person_sug_filter_toggle(temp_face_test_env, qapp):
    """
    FR: Vérifie le fonctionnement du bouton 'Afficher uniquement les suggestions' (sug_filter)
    et de sa bascule entre photos confirmées et suggestions.
    EN: Verify the 'Show suggestions only' button (sug_filter) and its toggle between confirmed photos and suggestions.
    Ref: picasa3.exe @ faceheaderpanel/sug_filter (0x005E16EA, 0x0074B9D6)
    """
    db = temp_face_test_env["db"]
    photo1 = temp_face_test_env["photo1"]
    photo2 = temp_face_test_env["photo2"]
    photo3 = temp_face_test_env["photo3"]

    # Ajouter 2 visages confirmés pour Alice
    fr1 = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    fr2 = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    db.face_manager.add_face(photo1, fr1, "Alice", contact_id="cid_alice", db_idx=1)
    db.face_manager.add_face(photo2, fr2, "Alice", contact_id="cid_alice", db_idx=2)

    # Ajouter 1 suggestion pour Alice
    fr_sug = FaceRect(left=0.25, top=0.25, right=0.75, bottom=0.75)
    sug = FaceSuggestion(
        contact_id="cid_alice",
        contact_name="Alice",
        photo_path=photo3,
        face_rect=fr_sug,
        similarity=0.88,
        db_idx=3
    )
    db.face_manager.suggestions["cid_alice"] = [sug]

    view = PicasaThumbnailView()
    view.resize(1000, 600)
    view.set_database(db)

    # Filtrer par Alice
    cluster = db.face_manager.get_person("cid_alice")
    view.filter_by_person("cid_alice", "Alice", cluster.photo_indices)

    sec = view.visible_sections[0]
    assert sec.is_person is True
    assert len(sec.suggestions) == 1
    assert sec.only_suggestions is False
    assert len(sec.item_indices) == 2  # 2 photos confirmées initialement

    # 1. Vérifier la présence des boutons de suggestions dans l'en-tête
    rect_sug = view._get_sug_filter_btn_rect(0)
    rect_confirm = view._get_confirm_sug_btn_rect(0)
    assert rect_sug.width() > 0
    assert rect_confirm.width() > 0
    assert rect_confirm.right() < rect_sug.left()  # Confirm button sits to the left of sug filter

    # 2. Clic sur le bouton de filtre des suggestions (sug_filter)
    view._toggle_suggestions_only(sec)
    assert sec.only_suggestions is True
    assert len(sec.item_indices) == 1  # Affiche uniquement la suggestion
    assert view.items[sec.item_indices[0]].is_synthetic_suggestion is True

    # 3. Clic à nouveau pour désactiver le filtre et revenir aux photos confirmées
    view._toggle_suggestions_only(sec)
    assert sec.only_suggestions is False
    assert len(sec.item_indices) == 2  # Reviens aux 2 photos confirmées


def test_person_confirm_all_suggestions(temp_face_test_env, qapp):
    """
    FR: Vérifie la validation groupée de toutes les suggestions d'une personne (confirmsug).
    EN: Verify bulk confirmation of all suggestions for a person (confirmsug).
    Ref: picasa3.exe @ faceheaderpanel/confirmsug (0x00896F74)
    """
    db = temp_face_test_env["db"]
    photo1 = temp_face_test_env["photo1"]
    photo2 = temp_face_test_env["photo2"]

    db.face_manager.add_face(photo1, FaceRect(0.25, 0.25, 0.75, 0.75), "Bob", contact_id="cid_bob", db_idx=1)

    sug = FaceSuggestion(
        contact_id="cid_bob",
        contact_name="Bob",
        photo_path=photo2,
        face_rect=FaceRect(0.25, 0.25, 0.75, 0.75),
        similarity=0.91,
        db_idx=2
    )
    db.face_manager.suggestions["cid_bob"] = [sug]

    view = PicasaThumbnailView()
    view.resize(1000, 600)
    view.set_database(db)
    view.filter_by_person("cid_bob", "Bob", [1])

    sec = view.visible_sections[0]
    assert len(sec.suggestions) == 1

    # Valider toutes les suggestions
    count = db.face_manager.confirm_all_suggestions("cid_bob")
    assert count == 1
    assert len(db.face_manager.get_suggestions("cid_bob")) == 0

    # Vérifier que Bob a maintenant 2 photos
    cluster = db.face_manager.get_person("cid_bob")
    assert 2 in cluster.photo_indices


def test_right_drawer_multi_selection(temp_face_test_env, qapp):
    """
    FR: Vérifie l'affichage du volet des personnes lors de sélections multiples.
    EN: Verify the People panel display during multiple selections.
    Ref: picasa3.exe @ PeoplePanel::Known2 ("People in these photos:"), PeoplePanel::Who
    """
    db = temp_face_test_env["db"]
    photo1 = temp_face_test_env["photo1"]
    photo2 = temp_face_test_env["photo2"]
    photo3 = temp_face_test_env["photo3"]

    # Alice apparaît sur photo1 et photo2
    db.face_manager.add_face(photo1, FaceRect(0.25, 0.25, 0.75, 0.75), "Alice", contact_id="cid_alice", db_idx=1)
    db.face_manager.add_face(photo2, FaceRect(0.25, 0.25, 0.75, 0.75), "Alice", contact_id="cid_alice", db_idx=2)

    # Bob apparaît sur photo2
    db.face_manager.add_face(photo2, FaceRect(0.1, 0.1, 0.3, 0.3), "Bob", contact_id="cid_bob", db_idx=2)

    # Un visage sans nom sur photo3
    db.face_manager.unnamed_faces.append((3, photo3, FaceRect(0.2, 0.2, 0.4, 0.4)))
    db.face_manager.photo_to_faces[3] = [FaceRect(0.2, 0.2, 0.4, 0.4, contact_name=None)]

    drawer = PicasaRightDrawer()
    drawer.resize(300, 600)

    # Sélection de photo1 et photo2 (contient Alice et Bob)
    drawer.set_multiple_photos(db, [1, 2], [photo1, photo2])
    panel_p = drawer.panel_people
    assert "Personnes figurant sur ces photos" in panel_p.header_lbl.text()
    assert "(2)" in panel_p.header_lbl.text()  # Alice et Bob

    # Sélection de photo3 (contient un visage non identifié)
    drawer.set_multiple_photos(db, [3], [photo3])
    assert "Qui est présent sur ces photos" in panel_p.header_lbl.text()

    # Sélection sans aucun visage
    drawer.set_multiple_photos(db, [], [])
    assert "Personnes" in panel_p.header_lbl.text()


def test_right_drawer_person_filter_signal(temp_face_test_env, qapp):
    """
    FR: Vérifie l'émission du signal person_filter_requested depuis le tiroir.
    EN: Verify emission of the person_filter_requested signal from the right drawer.
    """
    db = temp_face_test_env["db"]
    photo1 = temp_face_test_env["photo1"]

    db.face_manager.add_face(photo1, FaceRect(0.25, 0.25, 0.75, 0.75), "Alice", contact_id="cid_alice", db_idx=1)

    drawer = PicasaRightDrawer()
    drawer.resize(300, 600)
    drawer.set_multiple_photos(db, [1], [photo1])

    received = []
    drawer.person_filter_requested.connect(lambda cid, name: received.append((cid, name)))

    # Émettre le signal depuis le panel interne
    drawer.panel_people.person_filter_requested.emit("cid_alice", "Alice")
    assert received == [("cid_alice", "Alice")]


def test_context_menu_suggestion_actions(temp_face_test_env, qapp):
    """
    FR: Vérifie la présence et le déclenchement des actions de suggestion
    dans le menu contextuel clic droit.
    EN: Verify the presence and triggering of suggestion actions in the right-click context menu.
    Ref: picasa3.exe @ faceheaderpanel/confirmsel, removesel
    """
    from picasa_py.ui.context_menu import PicasaContextMenuBuilder

    db = temp_face_test_env["db"]
    photo1 = temp_face_test_env["photo1"]

    sug = FaceSuggestion(
        contact_id="cid_charlie",
        contact_name="Charlie",
        photo_path=photo1,
        face_rect=FaceRect(0.2, 0.2, 0.5, 0.5),
        similarity=0.89,
        db_idx=1
    )
    db.face_manager.suggestions["cid_charlie"] = [sug]

    # Construire le menu avec la suggestion
    menu = PicasaContextMenuBuilder.build_photo_context_menu(
        None, [photo1], db=db, contact_id="cid_charlie", suggestion=sug
    )
    assert menu is not None
    action_texts = [a.text() for a in menu.actions()]
    assert any("Confirmer cette suggestion" in t or "Confirm this suggestion" in t for t in action_texts)
    assert any("Rejeter cette suggestion" in t or "Reject this suggestion" in t for t in action_texts)

    # Déclencher la validation depuis le menu
    act_confirm = next(a for a in menu.actions() if "Confirmer cette suggestion" in a.text() or "Confirm this suggestion" in a.text())
    act_confirm.trigger()

    # Vérifier que la suggestion a été confirmée et qu'elle n'est plus en attente
    assert len(db.face_manager.get_suggestions("cid_charlie")) == 0
    assert db.face_manager.get_person("cid_charlie") is not None


def test_suggestion_individual_confirm_and_reject_buttons(temp_face_test_env, qapp):
    """
    FR: Vérifie les boutons d'action individuels sur chaque vignette de suggestion :
    ✓ (arrows/checkyes, 0x00761E33) et ✕ (arrows/checkno, 0x00761E47).
    EN: Verify the individual action buttons on each suggestion thumbnail:
    ✓ (arrows/checkyes, 0x00761E33) and ✕ (arrows/checkno, 0x00761E47).
    """
    db = temp_face_test_env["db"]
    photo1 = temp_face_test_env["photo1"]
    photo2 = temp_face_test_env["photo2"]
    photo3 = temp_face_test_env["photo3"]

    db.face_manager.add_face(photo1, FaceRect(0.2, 0.2, 0.8, 0.8), "David", contact_id="cid_david", db_idx=1)

    sug1 = FaceSuggestion(
        contact_id="cid_david",
        contact_name="David",
        photo_path=photo2,
        face_rect=FaceRect(0.2, 0.2, 0.8, 0.8),
        similarity=0.92,
        db_idx=2,
    )
    sug2 = FaceSuggestion(
        contact_id="cid_david",
        contact_name="David",
        photo_path=photo3,
        face_rect=FaceRect(0.2, 0.2, 0.8, 0.8),
        similarity=0.85,
        db_idx=3,
    )
    db.face_manager.suggestions["cid_david"] = [sug1, sug2]

    view = PicasaThumbnailView()
    view.resize(1000, 600)
    view.set_database(db)

    # Filtrer par David en affichant les suggestions
    view.filter_by_person("cid_david", "David", [1], only_suggestions=True)

    sec = view.visible_sections[0]
    assert sec.only_suggestions is True
    assert len(sec.item_indices) == 2

    # 1. Clic sur le bouton Valider (✓) de la première suggestion
    item_idx_0 = sec.item_indices[0]
    rect_0 = view._get_item_rect(sec, 0)
    btn_ok_0, btn_no_0 = view._get_suggestion_item_buttons(rect_0)

    from PySide6.QtCore import QPointF
    click_ok = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(btn_ok_0.center()),
        QPointF(btn_ok_0.center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(click_ok)

    # Vérifier que sug1 a été validé
    assert 2 in db.face_manager.get_person("cid_david").photo_indices
    remaining_sugs = db.face_manager.get_suggestions("cid_david")
    assert len(remaining_sugs) == 1
    assert remaining_sugs[0].photo_path == photo3

    # 2. Clic sur le bouton Rejeter (✕) de la suggestion restante
    sec_after = view.visible_sections[0]
    assert len(sec_after.item_indices) == 1
    rect_rem = view._get_item_rect(sec_after, 0)
    btn_ok_rem, btn_no_rem = view._get_suggestion_item_buttons(rect_rem)

    click_no = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(btn_no_rem.center()),
        QPointF(btn_no_rem.center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(click_no)

    # Vérifier que sug2 a été rejeté
    assert len(db.face_manager.get_suggestions("cid_david")) == 0


def test_suggestion_selected_header_confirm_and_remove(temp_face_test_env, qapp):
    """
    FR: Vérifie les boutons d'en-tête pour les suggestions sélectionnées :
    faceheaderpanel/confirmsel (0x005E1610) et faceheaderpanel/removesel (0x005E177C).
    EN: Verify the header buttons for selected suggestions:
    faceheaderpanel/confirmsel (0x005E1610) and faceheaderpanel/removesel (0x005E177C).
    """
    from PySide6.QtCore import QPointF
    db = temp_face_test_env["db"]
    photo1 = temp_face_test_env["photo1"]
    photo2 = temp_face_test_env["photo2"]
    photo3 = temp_face_test_env["photo3"]

    db.face_manager.add_face(photo1, FaceRect(0.2, 0.2, 0.8, 0.8), "Emma", contact_id="cid_emma", db_idx=1)

    sug = FaceSuggestion(
        contact_id="cid_emma",
        contact_name="Emma",
        photo_path=photo2,
        face_rect=FaceRect(0.2, 0.2, 0.8, 0.8),
        similarity=0.90,
        db_idx=2,
    )
    db.face_manager.suggestions["cid_emma"] = [sug]

    view = PicasaThumbnailView()
    view.resize(1000, 600)
    view.set_database(db)

    view.filter_by_person("cid_emma", "Emma", [1], only_suggestions=True)
    sec = view.visible_sections[0]

    # Sélectionner la suggestion
    view.selected_indices = {sec.item_indices[0]}

    # Vérifier que les boutons de sélection sont disponibles
    sec_top = sec.y_start - view.scroll_y
    rect_csel = view._get_confirm_sel_btn_rect(sec_top)
    rect_rsel = view._get_remove_sel_btn_rect(sec_top)
    assert rect_csel.width() > 0
    assert rect_rsel.width() > 0

    # Clic sur Confirmer la sélection
    click_csel = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(rect_csel.center()),
        QPointF(rect_csel.center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(click_csel)

    # Vérifier que la suggestion a été confirmée
    assert len(db.face_manager.get_suggestions("cid_emma")) == 0
    assert 2 in db.face_manager.get_person("cid_emma").photo_indices

    # Tester maintenant la suppression (rejet) via le bouton d'en-tête Supprimer
    sug_rem = FaceSuggestion(
        contact_id="cid_emma",
        contact_name="Emma",
        photo_path=photo3,
        face_rect=FaceRect(0.1, 0.1, 0.7, 0.7),
        similarity=0.88,
        db_idx=3,
    )
    db.face_manager.suggestions["cid_emma"] = [sug_rem]
    view.filter_by_person("cid_emma", "Emma", [1, 2], only_suggestions=True)
    sec2 = view.visible_sections[0]
    view.selected_indices = {sec2.item_indices[0]}
    sec2_top = sec2.y_start - view.scroll_y
    rect_rsel2 = view._get_remove_sel_btn_rect(sec2_top)

    click_rsel = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(rect_rsel2.center()),
        QPointF(rect_rsel2.center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(click_rsel)

    # Vérifier que la suggestion a été rejetée
    assert len(db.face_manager.get_suggestions("cid_emma")) == 0

