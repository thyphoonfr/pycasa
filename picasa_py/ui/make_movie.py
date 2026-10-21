"""
FR: Créateur de films Picasa 3 (CMakeMoviePanel).
Interface dédiée au mode diaporama vidéo (Make Movie) de Picasa 3.
EN: Picasa 3 Movie Maker (CMakeMoviePanel).
Dedicated interface for Picasa 3's video slideshow mode (Make Movie).

Ref: picasa3.exe @ CMakeMoviePanel, MakeMoviePanel, CRenderMovie, ytDSMovieWriter
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import QWidget

from picasa_py.ui.movie_maker import (
    PicasaMovieMakerDialog,
    PicasaMoviePreviewCanvas,
    MovieSlide,
    MovieRenderWorker,
    MOVIE_RESOLUTIONS,
    AUDIO_OPTIONS,
    MOVIE_TRANSITIONS,
    TEXT_STYLES,
)


class PicasaMakeMovieDialog(PicasaMovieMakerDialog):
    """
    FR: Boîte de dialogue de création de films diaporamas (CMakeMoviePanel).
    EN: Slideshow movie creation dialog (CMakeMoviePanel).
    Ref: picasa3.exe @ CMakeMoviePanel, ID_CREATE_SLIDESHOW_MOVIE
    """

    def __init__(self, photo_paths: List[str], parent: Optional[QWidget] = None):
        """
        FR: Initialise la boîte de dialogue de création de film en mode diaporama standard.
        EN: Initializes the movie maker dialog in standard slideshow mode.
        """
        super().__init__(
            photo_paths=photo_paths,
            face_mode=False,
            contact_id=None,
            parent=parent,
        )


__all__ = [
    "PicasaMakeMovieDialog",
    "PicasaMovieMakerDialog",
    "PicasaMoviePreviewCanvas",
    "MovieSlide",
    "MovieRenderWorker",
    "MOVIE_RESOLUTIONS",
    "AUDIO_OPTIONS",
    "MOVIE_TRANSITIONS",
    "TEXT_STYLES",
]
