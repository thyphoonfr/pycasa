"""
FR: Tests unitaires pour le support vidéo complet dans PyCasa (Picasa 3 Video Parity).
Vérifie la détection des extensions vidéo, l'extraction de métadonnées/vignettes,
l'intégration dans la grille (badge et filtres rapides) et le lecteur One-Up.
EN: Unit tests for full video support in PyCasa (Picasa 3 Video Parity).
Verifies video extension detection, metadata/thumbnail extraction,
grid integration (badge and quick filters), and the One-Up video player.

Ref: picasa3.exe @ 0x0088C3EC, Dev::ID_MOVIESETSTART, Dev::ID_MOVIESETEND
Ref: STRINGRES_FR.XML:640 ("Notez que les effets ne peuvent pas être appliqués aux vidéos")
"""

import os
import tempfile
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from picasa_py.scanner.scanner import (
    VIDEO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    EXTENSION_TYPE_MAP,
    extract_video_metadata_and_thumb,
    extract_media_metadata_and_thumb,
)
from picasa_py.ui.thumbnail_view import ThumbnailItem, PicasaThumbnailView, AlbumSection
from picasa_py.ui.video_player import PicasaVideoPlayer, format_time_ms
from picasa_py.ui.edit_panel import PicasaEditPanel
from picasa_py.ui.one_up_view import PicasaOneUpView
from picasa_py.db.database import PicasaDatabase


@pytest.fixture(scope="session")
def qapp():
    """
    FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provide a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_video_extensions_and_types():
    """
    FR: Vérifie la reconnaissance des extensions vidéo et le type 0x20.
    EN: Verify recognition of video file extensions and the 0x20 binary type.
    """
    assert ".mp4" in VIDEO_EXTENSIONS
    assert ".avi" in VIDEO_EXTENSIONS
    assert ".wmv" in VIDEO_EXTENSIONS
    assert ".mov" in VIDEO_EXTENSIONS
    assert ".mkv" in VIDEO_EXTENSIONS

    for ext in (".mp4", ".avi", ".wmv", ".mov", ".mpg", ".mpeg"):
        assert EXTENSION_TYPE_MAP.get(ext) == 0x20  # Type binaire Picasa Movie


def test_format_time_ms():
    """
    FR: Vérifie le formatage des durées vidéo.
    EN: Verify formatting of video durations in milliseconds.
    """
    assert format_time_ms(0) == "00:00"
    assert format_time_ms(14000) == "00:14"
    assert format_time_ms(75000) == "01:15"
    assert format_time_ms(3665000) == "01:01:05"


def test_video_thumbnail_and_fallback():
    """
    FR: Vérifie l'extraction de vignette de secours pour une vidéo.
    EN: Verify fallback thumbnail extraction for a video file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_video = os.path.join(tmpdir, "vacances_2024.mp4")
        with open(fake_video, "wb") as f:
            f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")

        # Même si le fichier est un mock binaire invalide, le générateur
        # de secours Picasa produit une vignette cinéma 256x256 sans planter
        res = extract_video_metadata_and_thumb(fake_video)
        assert res is not None
        thumb_bytes, w, h, date_ole = res
        assert len(thumb_bytes) > 0
        assert thumb_bytes.startswith(b"\xff\xd8")  # Format JPEG valide


def test_thumbnail_view_video_filter(qapp):
    """
    FR: Vérifie le filtrage rapide des vidéos dans la grille virtuelle.
    EN: Verify quick video filtering in the virtual thumbnail grid.
    """
    view = PicasaThumbnailView()

    # Créer une liste mixte de photos et de vidéos
    item1 = ThumbnailItem(index=0, path="photo1.jpg", filename="photo1.jpg", folder="Dossier", folder_path="C:/Photos", is_video=False)
    item2 = ThumbnailItem(index=1, path="film.mp4", filename="film.mp4", folder="Dossier", folder_path="C:/Photos", is_video=True)
    item3 = ThumbnailItem(index=2, path="photo2.jpg", filename="photo2.jpg", folder="Dossier", folder_path="C:/Photos", is_video=False)
    item4 = ThumbnailItem(index=3, path="clip.avi", filename="clip.avi", folder="Dossier", folder_path="C:/Photos", is_video=True)

    view.items = [item1, item2, item3, item4]
    sec = AlbumSection(name="Dossier", folder_path="C:/Photos", date_str="2024", item_indices=[0, 1, 2, 3])
    view.sections = [sec]
    view.visible_sections = [sec]
    view.filtered_indices = [0, 1, 2, 3]

    # Sans filtre : tous les éléments
    view.apply_quick_filters(filter_videos=False)
    assert len(view.filtered_indices) == 4

    # Filtre vidéo actif : uniquement les 2 vidéos
    view.apply_quick_filters(filter_videos=True)
    assert len(view.filtered_indices) == 2
    assert view.filtered_indices == [1, 3]

    # Désactivation du filtre vidéo
    view.apply_quick_filters(filter_videos=False)
    assert len(view.filtered_indices) == 4


def test_edit_panel_video_mode(qapp):
    """
    FR: Vérifie que le panneau d'édition désactive les effets en mode vidéo.
    EN: Verify that the edit panel disables image effects when in video mode.
    """
    panel = PicasaEditPanel()
    assert not panel.btn_save.isHidden()
    assert not panel.btn_undo.isHidden()

    # Activation du mode vidéo
    panel.set_video_mode(True)
    assert panel.btn_save.isHidden()
    assert panel.btn_undo.isHidden()
    assert panel.stack.currentWidget() == panel.video_subpanel

    # Retour en mode photo
    panel.set_video_mode(False)
    assert not panel.btn_save.isHidden()
    assert not panel.btn_undo.isHidden()


def test_video_player_component(qapp):
    """
    FR: Vérifie l'initialisation et le fonctionnement de PicasaVideoPlayer.
    EN: Verify initialization and operation of PicasaVideoPlayer.
    """
    player = PicasaVideoPlayer()
    assert player.btn_play.text() == "▶"
    assert player.btn_trim_start.text() == "[ Début"
    assert player.btn_trim_end.text() == "Fin ]"
    assert player.btn_snapshot is not None

    # Test Trimming
    player._set_trim_start(12000)
    assert player.trim_start_ms == 12000
    assert "[00:12" in player.btn_trim_start.text()

    player._set_trim_end(45000)
    assert player.trim_end_ms == 45000
    assert "00:45]" in player.btn_trim_end.text()

    # Test Mute
    assert not player.audio_output.isMuted()
    player.toggle_mute()
    assert player.audio_output.isMuted()
    player.toggle_mute()
    assert not player.audio_output.isMuted()


def test_one_up_view_video_integration(qapp):
    """
    FR: Vérifie la bascule automatique entre Canvas photo et VideoPlayer dans One-Up.
    EN: Verify automatic switching between photo Canvas and VideoPlayer in One-Up view.
    """
    one_up = PicasaOneUpView()
    assert one_up.center_stack.currentWidget() == one_up.canvas

    with tempfile.TemporaryDirectory() as tmpdir:
        vid_path = os.path.join(tmpdir, "presentation.mp4")
        with open(vid_path, "wb") as f:
            f.write(b"\x00" * 100)

        # Ouverture de la vidéo
        one_up.open_photo(None, -1, [], direct_path=vid_path)
        assert one_up.center_stack.currentWidget() == one_up.video_player
        assert one_up.transport_bar.isHidden()
        assert not one_up.btn_mode_a.isEnabled()
        assert "🎬" in one_up.lbl_top_info.text()
        one_up.video_player.stop()
