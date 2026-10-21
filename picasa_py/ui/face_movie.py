"""
FR : Créateur de films de visages Picasa 3 (CMakeFaceMoviePanel).
Interface dédiée à l'alignement automatique des yeux/nez et au morphing temporel entre photos d'une personne.
EN : Picasa 3 Face Movie Maker (CMakeFaceMoviePanel).
Dedicated interface for automatic eye/nose alignment and temporal morphing across photos of a person.

Ref: picasa3.exe @ CMakeFaceMoviePanel, ID_CREATE_FACEMOVIE
"""

from __future__ import annotations
from typing import List, Optional
from PySide6.QtWidgets import QWidget

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.movie_maker import (
    PicasaMovieMakerDialog,
    PicasaMoviePreviewCanvas,
    MovieSlide,
    MovieRenderWorker,
)


class PicasaFaceMovieDialog(PicasaMovieMakerDialog):
    """
    FR : Boîte de dialogue de création de films de visages (CMakeFaceMoviePanel).
    EN : Face movie creation dialog (CMakeFaceMoviePanel).
    Ref: picasa3.exe @ CMakeFaceMoviePanel, ID_CREATE_FACEMOVIE
    """

    def __init__(
        self,
        photo_paths: List[str],
        contact_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        super().__init__(
            photo_paths=photo_paths,
            face_mode=True,
            contact_id=contact_id,
            parent=parent,
            style=style,
        )


__all__ = [
    "PicasaFaceMovieDialog",
    "PicasaMovieMakerDialog",
    "PicasaMoviePreviewCanvas",
    "MovieSlide",
    "MovieRenderWorker",
]
