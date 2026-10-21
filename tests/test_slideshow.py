"""
FR: Tests pour le composant de diaporama plein écran (PicasaSlideshowWindow et PicasaSlideshowHUD).
EN: Tests for Fullscreen Slideshow Component (PicasaSlideshowWindow and PicasaSlideshowHUD).
"""

from pathlib import Path
from PIL import Image

import pytest
from PySide6.QtCore import Qt

from picasa_py.ui.slideshow import PicasaSlideshowWindow, PicasaSlideshowHUD
from picasa_py.ini.parser import PicasaIniParser


@pytest.fixture
def temp_slideshow_photos(tmp_path):
    """
    FR: Crée 4 photos JPEG temporaires pour tester le diaporama.
    EN: Create 4 temporary JPEG photos to test the slideshow.
    """
    img_paths = []
    for i in range(4):
        p = tmp_path / f"slide_photo_{i}.jpg"
        img = Image.new("RGB", (600, 400), color=(50 * i, 100, 150))
        img.save(p, "JPEG")
        img_paths.append(str(p))
    return img_paths


def test_slideshow_hud_controls(qapp):
    """
    FR: Vérifie les contrôles du bandeau HUD du diaporama (lecture/pause et étoile).
    EN: Verify the slideshow HUD controls (play/pause toggle and star state).
    """
    hud = PicasaSlideshowHUD()
    assert hud.is_playing is True
    assert hud.btn_play_pause.text() == "⏸"

    # Bascule play/pause
    hud._toggle_play_pause()
    assert hud.is_playing is False
    assert hud.btn_play_pause.text() == "▶"

    # Vérification étoile
    hud.set_starred(True)
    assert hud.btn_star.text() == "★"
    hud.set_starred(False)
    assert hud.btn_star.text() == "☆"


def test_slideshow_window_navigation_and_features(qapp, temp_slideshow_photos):
    """
    FR: Vérifie la navigation entre photos, l'ajout d'étoile et la rotation dans la fenêtre de diaporama.
    EN: Verify photo navigation, starring, and rotation in the slideshow window.
    """
    win = PicasaSlideshowWindow(temp_slideshow_photos, start_index=1)
    assert win.current_idx == 1
    assert win._curr_pixmap is not None
    assert not win._curr_pixmap.isNull()

    # Avancer à la photo suivante
    win.next_photo()
    assert win.current_idx == 2

    # Reculer
    win.prev_photo()
    assert win.current_idx == 1

    # Étoiler la photo 1
    win.toggle_star_current()
    p1 = Path(temp_slideshow_photos[1])
    ini_path = p1.parent / ".picasa.ini"
    assert ini_path.exists()
    doc = PicasaIniParser.parse_file(str(ini_path))
    assert doc.is_starred(p1.name) is True

    # Dé-étoiler
    win.toggle_star_current()
    doc = PicasaIniParser.parse_file(str(ini_path))
    assert doc.is_starred(p1.name) is False

    # Pivoter de 90° CW
    win.rotate_current_cw()
    doc = PicasaIniParser.parse_file(str(ini_path))
    assert doc.get_rotate(p1.name) == 1
    assert win._curr_pixmap.width() == 400
    assert win._curr_pixmap.height() == 600

    win.close()


def test_slideshow_exif_and_ini_rotation(qapp, tmp_path):
    """
    FR: Vérifie que le diaporama respecte l'orientation EXIF (ex: Orientation=6 -> 90° CW)
    ainsi que rotate=rotate(-1) -> 0 dans .picasa.ini.
    EN: Verify that the slideshow honors EXIF orientation (e.g. Orientation=6 -> 90° CW)
    as well as rotate=rotate(-1) -> 0 in .picasa.ini.
    """
    p_exif = tmp_path / "exif_portrait.jpg"
    img = Image.new("RGB", (600, 400), color=(180, 90, 40))
    exif = img.getexif()
    exif[0x0112] = 6  # 90° CW -> 400x600
    img.save(p_exif, "JPEG", exif=exif.tobytes())

    ini_path = tmp_path / ".picasa.ini"
    ini_path.write_text("[exif_portrait.jpg]\r\nrotate=rotate(-1)\r\n", encoding="utf-8")

    doc = PicasaIniParser.parse_file(str(ini_path))
    assert doc.get_rotate("exif_portrait.jpg") == 0

    win = PicasaSlideshowWindow([str(p_exif)], start_index=0)
    assert win._curr_pixmap is not None
    assert not win._curr_pixmap.isNull()
    assert win._curr_pixmap.width() == 400
    assert win._curr_pixmap.height() == 600
    win.close()

