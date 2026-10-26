"""FR: Tests pour PicasaAlbumScroll (AVCScrollThrottle), PicasaScrollTooltip et le défilement continu multi-albums.
EN: Tests for PicasaAlbumScroll (AVCScrollThrottle), PicasaScrollTooltip and Multi-Album Continuous Scrolling.
Ref: picasa3.exe @ 0x0072E6E6, 0x00CAD944, 0x005DE8E0, 0x005CE090
"""

import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint

from picasa_py.ui.album_scroll import PicasaAlbumScroll, PicasaScrollTooltip
from picasa_py.ui.thumbnail_view import PicasaThumbnailView, format_ole_date
from picasa_py.db.database import PicasaDatabase


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_format_ole_date():
    """FR: Vérifie le formatage des dates OLE Automation en chaîne mois/année.
    EN: Verifies formatting of OLE Automation dates into month/year strings.
    """
    # 45459.4 -> 2024-06-16 -> "Juin 2024"
    res = format_ole_date(45459.4)
    assert "Juin" in res
    assert "2024" in res

    # 0 or negative
    assert format_ole_date(0.0) == ""
    assert format_ole_date(-5.0) == ""


def test_album_scroll_throttle_centered_and_deflection(qapp):
    """FR: Vérifie le centrage du curseur throttle au repos et sa vitesse non linéaire selon la déflexion.
    EN: Verifies throttle thumb centering at rest and its non-linear speed upon deflection.
    """
    scroll = PicasaAlbumScroll()
    scroll.resize(20, 500)
    scroll.set_range(0, 1000, page_step=200)

    # Au repos, le curseur doit être exactement centré verticalement sur le point mort
    thumb_r = scroll._get_thumb_rect()
    assert abs(thumb_r.center().y() - scroll.center_y) <= 1
    assert thumb_r.width() == scroll.thumb_width
    assert thumb_r.height() == scroll.thumb_height

    # Glisser vers le bas (mouse_y > center_y) -> vitesse positive (scroll down)
    center_y = scroll.center_y
    scroll._update_throttle_from_mouse_y(center_y + 30)
    assert scroll._throttle_speed > 0
    thumb_down = scroll._get_thumb_rect()
    assert thumb_down.center().y() > center_y

    speed_small = scroll._throttle_speed

    # Plus on s'éloigne du centre, plus la vitesse augmente (non-linéarité)
    scroll._update_throttle_from_mouse_y(center_y + 80)
    assert scroll._throttle_speed > speed_small * 2

    # Glisser vers le haut (mouse_y < center_y) -> vitesse négative (scroll up)
    scroll._update_throttle_from_mouse_y(center_y - 40)
    assert scroll._throttle_speed < 0
    thumb_up = scroll._get_thumb_rect()
    assert thumb_up.center().y() < center_y

    # Zone morte au centre (écarts <= 3px donnent vitesse 0)
    scroll._update_throttle_from_mouse_y(center_y + 2)
    assert scroll._throttle_speed == 0.0


def test_album_scroll_tooltip_provider(qapp):
    """FR: Vérifie le fournisseur d'info-bulle de défilement d'album.
    EN: Verifies the album scroll tooltip information provider.
    """
    scroll = PicasaAlbumScroll()
    scroll.resize(20, 500)
    scroll.set_range(0, 1000, page_step=200)

    # Setup provider
    def info_cb(val: int):
        """FR: Retourne les informations d'album pour une position de défilement donnée.
        EN: Returns album information for a given scroll position.
        """
        if val < 500:
            return ("Vacances 2023", "Août 2023 • 32 photos")
        else:
            return ("Sortie 2024", "Juin 2024 • 15 photos")

    scroll.set_info_provider(info_cb)

    title, sub = scroll.info_provider(200)
    assert title == "Vacances 2023"
    assert "Août 2023" in sub

    title2, sub2 = scroll.info_provider(800)
    assert title2 == "Sortie 2024"
    assert "Juin 2024" in sub2


def test_thumbnail_view_multi_album_sections(qapp):
    """FR: Vérifie la mise en page multi-albums et la navigation inter-sections dans PicasaThumbnailView.
    EN: Verifies multi-album layout and inter-section navigation in PicasaThumbnailView.
    """
    from picasa_py.ui.thumbnail_view import AlbumSection, ThumbnailItem

    db = PicasaDatabase.open_default()
    view = PicasaThumbnailView()
    view.resize(800, 600)
    view.set_database(db)

    if len(view.sections) < 2:
        items = []
        sec0_indices = []
        sec1_indices = []
        for i in range(40):
            items.append(ThumbnailItem(i, f"C:/Photos/Album1/img_{i}.jpg", f"img_{i}.jpg", "Album 1", "C:/Photos/Album1"))
            sec0_indices.append(i)
        for i in range(40, 80):
            items.append(ThumbnailItem(i, f"C:/Photos/Album2/img_{i}.jpg", f"img_{i}.jpg", "Album 2", "C:/Photos/Album2"))
            sec1_indices.append(i)
        sec0 = AlbumSection(name="Album 1", folder_path="C:/Photos/Album1", date_str="Mai 2024", item_indices=sec0_indices)
        sec1 = AlbumSection(name="Album 2", folder_path="C:/Photos/Album2", date_str="Juin 2024", item_indices=sec1_indices)
        view.items = items
        view.sections = [sec0, sec1]
        view.visible_sections = [sec0, sec1]
        view._recompute_layout()

    # Check sections created
    assert len(view.sections) > 0
    hidden_folders = getattr(db, "_hidden_folders", set()) or set()
    expected_visible_count = sum(
        1 for s in view.sections
        if s.folder_path.replace("\\", "/").rstrip("/").lower() not in hidden_folders
    )
    assert len(view.visible_sections) == expected_visible_count
    assert len(view.items) > 0

    # Layout recomputed
    assert view.total_content_height > 600
    assert view.scrollbar.max_val > 0

    # Test timeline query at top
    title, sub = view.get_album_info_at_scroll(0)
    assert title != ""
    assert "photos" in sub

    # Test timeline query further down
    title_mid, sub_mid = view.get_album_info_at_scroll(1000)
    assert title_mid != ""
    assert "photos" in sub_mid

    # Test jump prev / next album
    first_y = view.visible_sections[0].y_start
    second_y = view.visible_sections[1].y_start if len(view.visible_sections) > 1 else 0
    assert second_y > first_y

    view._on_jump_next_album()
    assert view.scroll_y == second_y
    view._on_jump_prev_album()
    assert view.scroll_y == first_y


def test_sticky_album_header_pin_and_push(qapp):
    """FR: Vérifie l'effet 'sticky header' de Picasa :
    1. L'en-tête reste épinglé à y=0 tant qu'on défile dans l'album.
    2. Quand l'en-tête de l'album suivant arrive, il le pousse vers le haut (sticky_y < 0).
    3. Dès que l'album suivant atteint le haut, il devient le nouvel en-tête épinglé.
    4. Clic sur le bouton Diaporama et sélection complète du dossier.

    EN: Verifies Picasa's 'sticky header' behavior:
    1. Header remains pinned at y=0 while scrolling within the album.
    2. When the next album header arrives, it pushes the current header upward (sticky_y < 0).
    3. Once the next album reaches the top, it becomes the new pinned header.
    4. Clicking the Slideshow button and full folder selection.
    """
    from picasa_py.ui.thumbnail_view import AlbumSection, ThumbnailItem
    from PySide6.QtGui import QPixmap, QMouseEvent
    from PySide6.QtCore import QPointF

    view = PicasaThumbnailView()
    view.resize(800, 600)

    # Créer 2 sections artificielles
    sec0 = AlbumSection(
        name="Dossier 1",
        folder_path="C:/Photos/Dossier1",
        date_str="Mai 2024",
        item_indices=[0, 1],
        y_start=12,
        height=300
    )
    sec1 = AlbumSection(
        name="Dossier 2",
        folder_path="C:/Photos/Dossier2",
        date_str="Juin 2024",
        item_indices=[2, 3],
        y_start=312,
        height=400
    )
    view.items = [
        ThumbnailItem(0, "C:/Photos/Dossier1/1.jpg", "1.jpg", "Dossier1", "C:/Photos/Dossier1"),
        ThumbnailItem(1, "C:/Photos/Dossier1/2.jpg", "2.jpg", "Dossier1", "C:/Photos/Dossier1"),
        ThumbnailItem(2, "C:/Photos/Dossier2/3.jpg", "3.jpg", "Dossier2", "C:/Photos/Dossier2"),
        ThumbnailItem(3, "C:/Photos/Dossier2/4.jpg", "4.jpg", "Dossier2", "C:/Photos/Dossier2"),
    ]
    view.visible_sections = [sec0, sec1]

    # 1. Au sommet (scroll_y = 0) : Dossier 1 démarre à y=12 > 0 -> pas d'en-tête épinglé
    view.scroll_y = 0
    idx, sy = view._get_sticky_header_info()
    assert idx is None

    # 2. Défilement dans Dossier 1 (scroll_y = 100) : Dossier 1 épinglé à y=0
    view.scroll_y = 100
    idx, sy = view._get_sticky_header_info()
    assert idx == 0
    assert sy == 0  # Collé en haut à y=0

    # 3. Arrivée de Dossier 2 qui pousse l'en-tête (sec1 top = 312 - 300 = 12 < 38)
    view.scroll_y = 300
    idx, sy = view._get_sticky_header_info()
    assert idx == 0
    assert sy == 12 - 38  # Poussé vers le haut à -26 px

    # 4. Entrée complète dans Dossier 2 (scroll_y = 330) : Dossier 2 devient épinglé à y=0
    view.scroll_y = 330
    idx, sy = view._get_sticky_header_info()
    assert idx == 1
    assert sy == 0

    # 5. Rendu graphique complet avec paintEvent
    pix = QPixmap(800, 600)
    view.render(pix)
    assert not pix.isNull()

    # 6. Test du clic sur le bouton Diaporama de l'en-tête épinglé
    slideshow_paths = []
    view.slideshow_requested.connect(lambda p: slideshow_paths.extend(p))

    # Clic sur le bouton Diaporama de sec1
    btn_rect = view._get_slideshow_btn_rect(0)
    click_pos = btn_rect.center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(click_pos),
        QPointF(click_pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    view.mousePressEvent(event)
    assert len(slideshow_paths) == 2
    assert "3.jpg" in slideshow_paths[0]
    assert "4.jpg" in slideshow_paths[1]


def test_library_tree_scrollbar_visibility_and_contrast(qapp):
    """FR: Vérifie que la barre de défilement de l'arborescence de gauche (PicasaLibraryTree)
    apparaît bien avec un défilement fluide au pixel et un curseur contrasté lorsqu'il y a
    beaucoup de personnes, d'albums ou de dossiers.
    EN: Verifies that the left library tree (PicasaLibraryTree) scrollbar appears with smooth
    pixel scrolling and a contrasted thumb when there are many people, albums, or folders.
    """
    from PySide6.QtWidgets import QTreeWidgetItem, QAbstractItemView
    from picasa_py.ui.library_tree import PicasaLibraryTree

    lt = PicasaLibraryTree()
    lt.resize(220, 300)
    for i in range(40):
        it = QTreeWidgetItem(lt.cat_people)
        it.setText(0, f"Personne {i} (12)")
    lt.show()
    qapp.processEvents()

    vsb = lt.tree.verticalScrollBar()
    assert lt.tree.verticalScrollMode() == QAbstractItemView.ScrollMode.ScrollPerPixel
    assert vsb.isVisible()
    assert vsb.maximum() > 0
    assert vsb.width() >= 12
    assert "QScrollBar:vertical" in lt.tree.styleSheet()
    assert "QScrollBar::handle:vertical" in lt.tree.styleSheet()

