"""FR: Tests unitaires et d'intégration pour Movie Maker (CMakeMoviePanel) et le Film de visages (CMakeFaceMoviePanel).
EN: Unit and integration tests for Movie Maker (CMakeMoviePanel) and Face Movie (CMakeFaceMoviePanel).
Ref: picasa3.exe @ MakeMoviePanel, CMakeMoviePanel, CMakeFaceMoviePanel, ID_MAKEMOVIE, ID_MOVIEFACES
"""

import os
import tempfile
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QImage, QColor

from picasa_py.faces.facerect import FaceRect
from picasa_py.ui.movie_maker import (
    MovieSlide, PicasaMoviePreviewCanvas, PicasaMovieMakerDialog,
    MovieRenderWorker, MOVIE_RESOLUTIONS, MOVIE_TRANSITIONS, TEXT_STYLES
)
from picasa_py.ui.context_menu import PicasaContextMenuBuilder


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def sample_images(tmp_path):
    """FR: Crée 3 images RGB synthétiques dans un répertoire temporaire pour les tests de film.
    EN: Creates 3 synthetic RGB images in a temporary directory for movie tests.
    """
    paths = []
    for i in range(3):
        p = tmp_path / f"movie_test_{i}.jpg"
        im = Image.new("RGB", (200, 150), (40 * (i + 1), 60 * (i + 1), 80))
        im.save(str(p))
        paths.append(str(p))
    return paths


def test_movie_slide_creation_and_thumbnails(qapp, sample_images):
    """FR: Vérifie la création des diapositives photos et textes et la génération des miniatures.
    EN: Verifies creation of photo and text slides and thumbnail generation.
    """
    # 1. Diapositive photo
    fr = FaceRect(left=0.2, top=0.1, right=0.6, bottom=0.7)
    slide_photo = MovieSlide(path=sample_images[0], is_text=False, duration=4.0, face_rect=fr, date_str="15/10/2026")
    assert not slide_photo.is_text
    assert slide_photo.duration == 4.0
    assert slide_photo.face_rect == fr
    assert slide_photo.date_str == "15/10/2026"

    thumb_p = slide_photo.get_thumbnail(size=64)
    assert thumb_p is not None
    assert not thumb_p.isNull()

    # 2. Diapositive texte
    slide_text = MovieSlide(is_text=True, text="Mon Beau Voyage", duration=3.0)
    assert slide_text.is_text
    assert slide_text.text == "Mon Beau Voyage"
    thumb_t = slide_text.get_thumbnail(size=64)
    assert thumb_t is not None
    assert not thumb_t.isNull()


def test_movie_preview_canvas_timing_and_modes(qapp, sample_images):
    """FR: Vérifie le canevas de prévisualisation, le calcul des durées, et les modes Ken Burns / Face Movie.
    EN: Verifies the preview canvas, duration calculations, and Ken Burns / Face Movie modes.
    """
    canvas = PicasaMoviePreviewCanvas()
    slides = [
        MovieSlide(path=sample_images[0], duration=3.0, face_rect=FaceRect(0.3, 0.2, 0.7, 0.8)),
        MovieSlide(path=sample_images[1], duration=3.0, face_rect=FaceRect(0.2, 0.1, 0.6, 0.7)),
        MovieSlide(is_text=True, text="Fin", duration=2.0)
    ]
    canvas.set_slides(slides)
    canvas.overlap_ratio = 0.25  # 25% superposition

    # Durée totale = 3.0 + (3.0 - 0.75) + (2.0 - 0.5) = 3.0 + 2.25 + 1.5 = 6.75s
    assert abs(canvas.total_duration_s - 6.75) < 0.01

    # Navigation dans le temps
    canvas.set_playback_time(0.0)
    assert canvas.get_current_slide_index() == 0

    canvas.set_playback_time(2.5)
    assert canvas.get_current_slide_index() == 0

    canvas.set_playback_time(3.5)
    assert canvas.get_current_slide_index() == 1

    canvas.set_playback_time(6.0)
    assert canvas.get_current_slide_index() == 2

    # Transport controls
    canvas.play()
    assert canvas.is_playing is True
    canvas.pause()
    assert canvas.is_playing is False
    canvas.rewind()
    assert canvas.current_time_s == 0.0

    # Face Movie mode toggle
    canvas.face_movie_mode = True
    assert canvas.face_movie_mode is True

    # Rendu sans crash
    test_img = QImage(320, 240, QImage.Format.Format_RGB888)
    painter = QPainter(test_img)
    canvas._render_frame(painter, QRectF(0, 0, 320, 240))
    painter.end()


def test_movie_maker_dialog_workflow(qapp, sample_images):
    """FR: Vérifie les interactions avec l'atelier complet Movie Maker (onglets, timeline, actions).
    EN: Verifies interactions with the full Movie Maker workshop (tabs, timeline, actions).
    """
    dlg = PicasaMovieMakerDialog(sample_images, face_mode=False)
    assert len(dlg.slides) == 3
    assert dlg.selected_slide_index == 0
    assert dlg.canvas is not None

    # 1. Insertion d'une diapositive de texte
    dlg._on_insert_text_slide()
    assert len(dlg.slides) == 4
    assert dlg.slides[1].is_text is True

    # 2. Déplacement de diapositive (move_right / move_left)
    dlg.selected_slide_index = 1
    dlg._on_move_right()
    assert dlg.selected_slide_index == 2
    assert dlg.slides[2].is_text is True

    dlg._on_move_left()
    assert dlg.selected_slide_index == 1
    assert dlg.slides[1].is_text is True

    # 3. Édition du texte
    dlg.edit_slide_text.setPlainText("Super Vacances 2026")
    dlg._on_slide_text_edited()
    assert dlg.slides[1].text == "Super Vacances 2026"

    # 4. Suppression de diapositive
    dlg._on_delete_selected_slide()
    assert len(dlg.slides) == 3

    # 5. Changement de transition et de résolution
    dlg.cb_transitions.setCurrentIndex(1)  # Dissolve
    dlg._on_transition_changed()
    assert dlg.canvas.transition_type == "dissolve"

    dlg.cb_resolution.setCurrentIndex(1)  # 640x480
    dlg._on_resolution_changed()
    assert dlg.canvas.resolution == (640, 480)

    # 6. Mode Face Movie
    dlg.chk_face_movie.setChecked(True)
    assert dlg.canvas.face_movie_mode is True

    dlg.close()


def test_movie_render_worker_export(qapp, sample_images, tmp_path):
    """FR: Vérifie l'exportation vidéo MP4 via MovieRenderWorker.
    EN: Verifies MP4 video export via MovieRenderWorker.
    """
    out_mp4 = str(tmp_path / "test_render.mp4")
    slides = [
        MovieSlide(path=sample_images[0], duration=0.2),
        MovieSlide(path=sample_images[1], duration=0.2),
    ]

    worker = MovieRenderWorker(
        slides=slides,
        output_path=out_mp4,
        resolution=(320, 240),
        transition_type="cut",
        overlap_ratio=0.1,
        fps=10
    )

    # Exécuter de manière synchrone via run()
    worker.run()

    # Vérifier que le fichier MP4 a bien été généré sur disque
    assert os.path.exists(out_mp4)
    assert os.path.getsize(out_mp4) > 100


def test_context_menu_movie_actions(qapp, sample_images):
    """FR: Vérifie la présence des commandes Créer un film et Film de visages dans les menus contextuels.
    EN: Verifies the presence of Create Movie and Face Movie commands in context menus.
    """
    class MockWin:
        """FR: Simulacre de fenêtre principale pour intercepter les appels à action_movie.
        EN: Mock main window for intercepting calls to action_movie.
        """
        def __init__(self):
            """FR: Initialise les indicateurs d'appel de film.
            EN: Initializes movie call flags.
            """
            self.movie_called = False
            self.face_mode_called = False
            self.target_contact_id = None

        def action_movie(self, face_mode=False, contact_id=None):
            """FR: Enregistre l'appel à action_movie et ses paramètres.
            EN: Records the call to action_movie and its parameters.
            """
            self.movie_called = True
            self.face_mode_called = face_mode
            self.target_contact_id = contact_id

    win = MockWin()

    # 1. Menu photo standard
    menu_photo = PicasaContextMenuBuilder.build_photo_context_menu(
        parent=None,
        photo_paths=sample_images,
        main_win=win
    )
    assert menu_photo is not None
    actions = [a.text() for a in menu_photo.actions()]
    assert any(t in actions for t in ("Create &Movie...", "Créer un &film..."))

    # 2. Menu photo de personne (avec contact_id)
    menu_person_photo = PicasaContextMenuBuilder.build_photo_context_menu(
        parent=None,
        photo_paths=[sample_images[0]],
        contact_id="person_42",
        main_win=win
    )
    assert menu_person_photo is not None
    actions_p = [a.text() for a in menu_person_photo.actions()]
    assert any(t in actions_p for t in ("Create &Face Movie...", "Créer un &film avec des visages..."))
    assert any(t in actions_p for t in ("Create &Movie...", "Créer un &film..."))

    # Déclencher Create Face Movie
    for a in menu_person_photo.actions():
        if a.text() in ("Create &Face Movie...", "Créer un &film avec des visages..."):
            a.trigger()
            break
    assert win.movie_called is True
    assert win.face_mode_called is True
    assert win.target_contact_id == "person_42"

    # 3. Menu album de personne (build_person_context_menu)
    menu_person_album = PicasaContextMenuBuilder.build_person_context_menu(
        parent=None,
        contact_id="person_99",
        person_name="Claire",
        main_win=win
    )
    assert menu_person_album is not None
    actions_album = [a.text() for a in menu_person_album.actions()]
    assert any(t in actions_album for t in ("Create &Face Movie...", "Créer un &film avec des visages..."))
