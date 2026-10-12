"""
Tests for PicasaAlbumScroll (AVCScrollThrottle), PicasaScrollTooltip and Multi-Album Continuous Scrolling.
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
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_format_ole_date():
    # 45459.4 -> 2024-06-16 -> "Juin 2024"
    res = format_ole_date(45459.4)
    assert "Juin" in res
    assert "2024" in res

    # 0 or negative
    assert format_ole_date(0.0) == ""
    assert format_ole_date(-5.0) == ""


def test_album_scroll_throttle_centered_and_deflection(qapp):
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
    scroll = PicasaAlbumScroll()
    scroll.resize(20, 500)
    scroll.set_range(0, 1000, page_step=200)

    # Setup provider
    def info_cb(val: int):
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
    db = PicasaDatabase.open_default()
    view = PicasaThumbnailView()
    view.resize(800, 600)
    view.set_database(db)

    # Check sections created
    assert len(view.sections) > 0
    assert len(view.visible_sections) == len(view.sections)
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
