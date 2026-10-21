"""FR: Tests pour :
1. PicasaFilmstrip (carrousel de vignettes en haut de la vue One-Up)
2. Défilement continu multi-albums (MultiAlbumScroll)
3. Vue Reconnaissance faciale : Zoom Visage vs Photo entière

EN: Tests for:
1. PicasaFilmstrip (One-Up top navigation filmstrip carousel)
   Ref: picasa3.exe @ editpanel/filmstrip, il_BigView::1
2. Continuous Multi-Album Scroll (MultiAlbumScroll)
   Ref: picasa3.exe @ MultiAlbumScroll, UseMultiAlbumScrollFix, CAlbumList::liststicky
3. Face Recognition view: Face Zoom vs Picture Zoom
   Ref: picasa3.exe @ faceheaderpanel/face_zoom, picture_zoom (0x00896F00)
"""

import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QPixmap, QMouseEvent

from picasa_py.db.database import PicasaDatabase
from picasa_py.ui.filmstrip import PicasaFilmstrip
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.ui.thumbnail_view import PicasaThumbnailView, AlbumSection, ThumbnailItem


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(["picasa_test", "-platform", "offscreen"])
    return app


# =============================================================================
# 1. Tests Filmstrip One-Up
# =============================================================================

def test_filmstrip_creation_and_centering(qapp):
    """FR: Vérifie la création et le centrage automatique de l'élément actif dans PicasaFilmstrip.
    EN: Verifies creation and automatic centering of the active item in PicasaFilmstrip.
    """
    filmstrip = PicasaFilmstrip(thumb_size=40, spacing=6)
    filmstrip.resize(400, 50)

    indices = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    filmstrip.set_items(db=None, indices=indices, current_index=50)

    assert filmstrip.current_index == 50
    assert len(filmstrip.indices) == 10

    # L'élément 50 est au milieu -> scroll_x > 0
    assert filmstrip.scroll_x > 0

    # Changer pour l'élément 10 (premier élément) -> scroll_x doit valoir 0
    filmstrip.set_current_index(10)
    assert filmstrip.current_index == 10
    assert filmstrip.scroll_x == 0


def test_filmstrip_click_and_signal(qapp):
    """FR: Vérifie qu'un clic sur une miniature du filmstrip émet le signal photo_clicked avec le bon index.
    EN: Verifies that clicking a filmstrip thumbnail emits the photo_clicked signal with the right index.
    """
    filmstrip = PicasaFilmstrip(thumb_size=40, spacing=6)
    filmstrip.resize(400, 50)

    indices = [10, 20, 30, 40]
    filmstrip.set_items(db=None, indices=indices, current_index=10)

    clicked_indices = []
    filmstrip.photo_clicked.connect(lambda idx: clicked_indices.append(idx))

    # Clic sur le 2e élément (index 20)
    r = filmstrip._get_item_rect(1)
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(r.center()),
        QPointF(r.center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    filmstrip.mousePressEvent(event)

    assert len(clicked_indices) == 1
    assert clicked_indices[0] == 20


def test_one_up_filmstrip_integration(qapp):
    """FR: Vérifie l'intégration du filmstrip avec PicasaOneUpView lors de l'ouverture et de la navigation.
    EN: Verifies filmstrip integration with PicasaOneUpView during photo opening and navigation.
    """
    db = PicasaDatabase.open_default()
    one_up = PicasaOneUpView()
    one_up.resize(1000, 700)

    available = list(range(min(5, len(db.index))))
    if available:
        one_up.open_photo(db, available[0], available)

        # Vérifier que la pellicule a bien reçu les éléments
        assert one_up.filmstrip is not None
        assert one_up.filmstrip.current_index == available[0]
        assert one_up.filmstrip.indices == available

        # Navigation suivante
        if len(available) > 1:
            one_up.navigate_next()
            assert one_up.current_index == available[1]
            assert one_up.filmstrip.current_index == available[1]


# =============================================================================
# 2. Tests Défilement Continu Multi-Albums (MultiAlbumScroll)
# =============================================================================

def test_multi_album_scroll_to_folder(qapp):
    """FR: Vérifie que scroll_to_folder défile jusqu'à la section cible tout en conservant toutes les sections visibles.
    EN: Verifies that scroll_to_folder scrolls to the target section while keeping all sections visible.
    """
    view = PicasaThumbnailView()
    view.resize(800, 150)

    sec0 = AlbumSection(
        name="Vacances 2023",
        folder_path="C:/Photos/2023_Vacances",
        date_str="Juillet 2023",
        item_indices=[0, 1],
        y_start=12,
        height=300
    )
    sec1 = AlbumSection(
        name="Noël 2023",
        folder_path="C:/Photos/2023_Noel",
        date_str="Décembre 2023",
        item_indices=[2, 3],
        y_start=312,
        height=350
    )
    sec2 = AlbumSection(
        name="Voyage 2024",
        folder_path="C:/Photos/2024_Voyage",
        date_str="Mai 2024",
        item_indices=[4, 5],
        y_start=662,
        height=400
    )

    view.items = [
        ThumbnailItem(0, "C:/Photos/2023_Vacances/1.jpg", "1.jpg", "2023_Vacances", "C:/Photos/2023_Vacances"),
        ThumbnailItem(1, "C:/Photos/2023_Vacances/2.jpg", "2.jpg", "2023_Vacances", "C:/Photos/2023_Vacances"),
        ThumbnailItem(2, "C:/Photos/2023_Noel/3.jpg", "3.jpg", "2023_Noel", "C:/Photos/2023_Noel"),
        ThumbnailItem(3, "C:/Photos/2023_Noel/4.jpg", "4.jpg", "2023_Noel", "C:/Photos/2023_Noel"),
        ThumbnailItem(4, "C:/Photos/2024_Voyage/5.jpg", "5.jpg", "2024_Voyage", "C:/Photos/2024_Voyage"),
        ThumbnailItem(5, "C:/Photos/2024_Voyage/6.jpg", "6.jpg", "2024_Voyage", "C:/Photos/2024_Voyage"),
    ]
    view.sections = [sec0, sec1, sec2]
    view.visible_sections = list(view.sections)
    view._recompute_layout()

    # Défilement vers Noël 2023 sans masquer les autres sections
    view.scroll_to_folder("C:/Photos/2023_Noel")
    assert view.scroll_y == sec1.y_start
    assert len(view.visible_sections) == 3  # Toutes les sections restent enchaînées !

    # Défilement vers Voyage 2024
    view.scroll_to_folder("C:/Photos/2024_Voyage")
    assert view.scroll_y == sec2.y_start
    assert len(view.visible_sections) == 3


def test_active_folder_changed_signal(qapp):
    """FR: Vérifie que le signal active_folder_changed est émis lors du défilement vers une autre section.
    EN: Verifies that the active_folder_changed signal is emitted when scrolling into another section.
    """
    view = PicasaThumbnailView()
    view.resize(800, 600)

    sec0 = AlbumSection(name="Dossier A", folder_path="C:/Photos/A", date_str="", item_indices=[0], y_start=12, height=300)
    sec1 = AlbumSection(name="Dossier B", folder_path="C:/Photos/B", date_str="", item_indices=[1], y_start=312, height=400)

    view.items = [
        ThumbnailItem(0, "C:/Photos/A/1.jpg", "1.jpg", "A", "C:/Photos/A"),
        ThumbnailItem(1, "C:/Photos/B/2.jpg", "2.jpg", "B", "C:/Photos/B"),
    ]
    view.sections = [sec0, sec1]
    view.visible_sections = list(view.sections)
    view._recompute_layout()

    scrolled_folders = []
    view.active_folder_changed.connect(lambda f: scrolled_folders.append(f))

    # Scroll au niveau du dossier B
    view._on_scroll(320)
    assert len(scrolled_folders) > 0
    assert "C:/Photos/B" in scrolled_folders[-1]


# =============================================================================
# 3. Tests Reconnaissance Faciale : Zoom Visage vs Image Entière
# =============================================================================

def test_person_album_face_zoom_toggle(qapp):
    """FR: Vérifie la bascule entre le mode Zoom Visage et le mode Photo entière dans l'en-tête d'album de personne.
    EN: Verifies toggling between Face Zoom mode and Full Picture mode in a person album header.
    """
    view = PicasaThumbnailView()
    view.resize(800, 600)

    # Filtrer par personne -> crée une section is_person=True avec face_zoom=True par défaut
    view.items = [
        ThumbnailItem(0, "C:/Photos/Famille/1.jpg", "1.jpg", "Famille", "C:/Photos/Famille"),
        ThumbnailItem(1, "C:/Photos/Famille/2.jpg", "2.jpg", "Famille", "C:/Photos/Famille"),
    ]
    view.filter_by_person("contact_alice", "Alice Dupont", [0, 1])

    assert len(view.visible_sections) == 1
    sec = view.visible_sections[0]
    assert sec.is_person is True
    assert sec.face_zoom is True  # Mode zoom visage actif par défaut (Ref: faceheaderpanel/face_zoom)
    assert sec.contact_id == "contact_alice"

    sec_top = sec.y_start - view.scroll_y

    # Vérifier les zones cliquables des deux boutons
    fz_rect = view._get_face_zoom_btn_rect(sec_top)
    pz_rect = view._get_picture_zoom_btn_rect(sec_top)
    assert fz_rect.isValid()
    assert pz_rect.isValid()
    assert fz_rect.x() < pz_rect.x()  # Visages à gauche de Photos

    # Simuler le clic sur le bouton [Photo entière]
    click_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(pz_rect.center()),
        QPointF(pz_rect.center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    view.mousePressEvent(click_event)
    assert sec.face_zoom is False  # Basculé en mode photo entière !

    # Simuler le clic sur le bouton [Zoom visage]
    click_event_fz = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(fz_rect.center()),
        QPointF(fz_rect.center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    view.mousePressEvent(click_event_fz)
    assert sec.face_zoom is True  # Revenu en mode zoom visage !
