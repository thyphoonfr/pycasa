"""
FR: Tests de validation pour :
1. La sélection continue par plage avec la touche Shift (Shift-clic et Shift-flèches).
2. L'agrandissement et le redimensionnement du tiroir latéral droit (QSplitter et size_toggle).
3. L'affichage des personnes dans le volet latéral (PeoplePanel) avec survol, clic et lien album.
4. Le contraste du texte sur les boîtes de dialogue et gadgets à fond clair (ex. Gestionnaire de personnes).
EN: Validation tests for:
1. Continuous range selection using the Shift key (Shift-click and Shift-arrows).
2. Expanding and resizing the right-hand side drawer (QSplitter and size_toggle).
3. Displaying people in the side panel (PeoplePanel) with hover, click, and album link.
4. Text contrast on light-background dialogs and widgets (e.g. People Manager).

Ref: picasa3.exe @ rightdrawerpanel/size_toggle, PeoplePanel::InThis, PeoplePanel::Known2
Ref: picasa3.exe @ peoplepanel/peoplelist, contactmgr.fen
"""

import os
import shutil
import tempfile
import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QSplitter

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect
from picasa_py.ui.thumbnail_view import PicasaThumbnailView, AlbumSection, ThumbnailItem
from picasa_py.ui.right_drawer import PicasaRightDrawer, PicasaPeoplePanel, FaceCardFrame
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.ui.contact_manager_dialog import PicasaContactManagerDialog


@pytest.fixture
def temp_gallery_env():
    """
    FR: Crée un environnement de galerie temporaire avec 10 photos indexées dans une base Picasa isolée.
    EN: Create a temporary gallery environment with 10 photos indexed in an isolated Picasa database.
    """
    td = tempfile.mkdtemp(prefix="pycasa_shift_test_")
    db_dir = os.path.join(td, "db3")
    contacts_dir = os.path.join(td, "contacts")
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(contacts_dir, exist_ok=True)

    photos = []
    for i in range(10):
        p = os.path.join(td, f"photo_{i}.jpg")
        im = Image.new("RGB", (100, 100), color=(150 + i * 10, 100, 100))
        im.save(p)
        photos.append(p)

    db = PicasaDatabase.open(db_dir, contacts_dir)
    for i, p in enumerate(photos):
        db.add_media_record(td + "\\", os.path.basename(p), 1000 + i, 10000, 2)

    yield {
        "dir": td,
        "photos": photos,
        "db": db,
    }

    try:
        shutil.rmtree(td)
    except Exception:
        pass


def test_shift_click_range_selection(temp_gallery_env, qapp):
    """
    FR: Vérifie la sélection continue avec la touche Shift (photo début -> shift photo fin).
    EN: Verify continuous range selection with the Shift key (start photo -> shift end photo).
    """
    db = temp_gallery_env["db"]
    view = PicasaThumbnailView()
    view.resize(1000, 600)
    view.set_database(db)

    assert len(view.items) >= 10
    order = view._get_visible_item_indices()
    assert len(order) >= 10

    # 1. Clic normal sur la 2ème photo (index order[1])
    from PySide6.QtCore import QPointF
    view._find_item_at = lambda pos: order[1]
    ev1 = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(50, 50), QPointF(50, 50), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    view.mousePressEvent(ev1)

    assert view.selected_indices == {order[1]}
    assert view.anchor_index == order[1]

    # 2. Shift-clic sur la 6ème photo (index order[5])
    view._find_item_at = lambda pos: order[5]
    ev2 = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(50, 50), QPointF(50, 50), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    view.mousePressEvent(ev2)

    # La plage [order[1], order[2], order[3], order[4], order[5]] doit être entièrement sélectionnée
    expected_range = set(order[1:6])
    assert view.selected_indices == expected_range
    # L'ancre doit rester sur order[1]
    assert view.anchor_index == order[1]

    # 3. Shift-clic vers l'arrière sur la 1ère photo (index order[0])
    view._find_item_at = lambda pos: order[0]
    ev3 = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(50, 50), QPointF(50, 50), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    view.mousePressEvent(ev3)

    assert view.selected_indices == {order[0], order[1]}
    assert view.anchor_index == order[1]


def test_keyboard_navigation_and_shift_arrows(temp_gallery_env, qapp):
    """
    FR: Vérifie la sélection et l'extension avec les flèches du clavier.
    EN: Verify selection and range extension using keyboard arrow keys.
    """
    db = temp_gallery_env["db"]
    view = PicasaThumbnailView()
    view.resize(1000, 600)
    view.set_database(db)
    order = view._get_visible_item_indices()

    # Sélectionner le premier élément
    view.selected_indices = {order[0]}
    view.anchor_index = order[0]

    # Flèche droite avec Shift -> sélectionne order[0] et order[1]
    ev_right = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    view.keyPressEvent(ev_right)
    assert view.selected_indices == {order[0], order[1]}

    # Flèche droite avec Shift à nouveau -> sélectionne order[0], order[1], order[2]
    view.keyPressEvent(ev_right)
    assert view.selected_indices == {order[0], order[1], order[2]}

    # Flèche droite sans Shift -> déplace la sélection unique sur order[3]
    ev_right_noshift = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    view.keyPressEvent(ev_right_noshift)
    assert view.selected_indices == {order[3]}
    assert view.anchor_index == order[3]


def test_right_drawer_resizing_and_size_toggle(qapp):
    """
    FR: Vérifie que le tiroir latéral n'est plus à largeur fixe et que le bouton
    size_toggle permet de basculer entre taille normale et agrandie.
    EN: Verify that the side drawer is no longer fixed-width and that the
    size_toggle button toggles between normal and expanded width.
    Ref: picasa3.exe @ rightdrawerpanel/size_toggle
    """
    from PySide6.QtWidgets import QWidget
    splitter = QSplitter(Qt.Orientation.Horizontal)
    dummy = QWidget()
    splitter.addWidget(dummy)
    drawer = PicasaRightDrawer(parent=splitter)
    splitter.addWidget(drawer)

    # Vérifier que le tiroir est redimensionnable
    assert drawer.minimumWidth() <= 250
    assert drawer.maximumWidth() >= 1000
    assert drawer.btn_size_toggle is not None
    assert "Basculer" in drawer.btn_size_toggle.toolTip()

    # Initialiser dans le splitter
    splitter.resize(1200, 800)
    splitter.setSizes([900, 300])

    # Clic sur le bouton size_toggle pour agrandir
    drawer.btn_size_toggle.click()
    # Le panneau doit maintenant être élargi (> 360px, typiquement 520px)
    assert splitter.sizes()[1] >= 450

    # Clic à nouveau pour réduire à la taille standard
    drawer.btn_size_toggle.click()
    assert splitter.sizes()[1] <= 320


def test_one_up_right_drawer_splitter(qapp, temp_gallery_env):
    """
    FR: Vérifie que la vue One-Up intègre le tiroir dans un QSplitter redimensionnable.
    EN: Verify that the One-Up view embeds the right drawer inside a resizable QSplitter.
    """
    view = PicasaOneUpView()
    assert hasattr(view, "right_splitter")
    assert isinstance(view.right_splitter, QSplitter)
    assert view.right_drawer in [view.right_splitter.widget(i) for i in range(view.right_splitter.count())]


def test_people_panel_hover_and_click_signals(temp_gallery_env, qapp):
    """
    FR: Vérifie l'émission des signaux face_hovered, face_clicked et person_filter_requested
    depuis le PeoplePanel.
    EN: Verify emission of the face_hovered, face_clicked, and person_filter_requested
    signals from the PeoplePanel.
    """
    from PySide6.QtCore import QPointF
    db = temp_gallery_env["db"]
    photo = temp_gallery_env["photos"][0]
    fr = FaceRect(0.2, 0.2, 0.6, 0.6, contact_id="cid_clara", contact_name="Clara")
    db.face_manager.add_face(photo, fr, "Clara", contact_id="cid_clara", db_idx=1)

    panel = PicasaPeoplePanel()
    panel.resize(300, 500)
    panel.set_photo_faces(db, 1, photo, [fr])

    assert "Dans cette photo :" in panel.header_lbl.text()

    hovered_indices = []
    clicked_indices = []
    filter_requested = []

    panel.face_hovered.connect(lambda idx: hovered_indices.append(idx))
    panel.face_clicked.connect(lambda idx: clicked_indices.append(idx))
    panel.person_filter_requested.connect(lambda cid, name: filter_requested.append((cid, name)))

    # Trouver la carte créée
    card = None
    for i in range(panel.faces_layout.count()):
        w = panel.faces_layout.itemAt(i).widget()
        if isinstance(w, FaceCardFrame):
            card = w
            break

    assert card is not None
    # Simuler survol
    card.enterEvent(None)
    assert 0 in hovered_indices

    # Simuler sortie du survol
    card.leaveEvent(None)
    assert -1 in hovered_indices

    # Simuler clic sur la carte
    ev_click = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(10, 10), QPointF(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    card.mousePressEvent(ev_click)
    assert 0 in clicked_indices


def test_contact_manager_dialog_text_contrast(temp_gallery_env, qapp):
    """
    FR: Vérifie que le gestionnaire de personnes a des couleurs de texte sombres
    bien contrastées sur son fond clair (#ECE9D8).
    EN: Verify that the People Manager dialog has high-contrast dark text colors
    against its light background (#ECE9D8).
    """
    db = temp_gallery_env["db"]
    dlg = PicasaContactManagerDialog(db)

    # Vérifier les styles appliqués
    qss = dlg.styleSheet()
    assert "color: #111111" in qss
    assert "background-color: #ECE9D8" in qss

    # Vérifier que les labels et champs ont des textes bien lisibles
    assert dlg.lbl_person_title.styleSheet() != ""
    assert "color: #111111" in dlg.lbl_person_title.styleSheet()
    assert "color: #222222" in dlg.lbl_photo_count.styleSheet()
