"""
FR : Module de détection de visages et de gestion des personnes (People) de Picasa 3.
EN: Picasa 3 Face Detection and People Management Module.

# Ref: picasa3.exe @ 0x008AAD76 (FaceSyncer)
# Ref: picasa3.exe @ 0x009B9190 (rect64 decoder)
"""

from picasa_py.faces.facerect import (
    FaceRect,
    decode_rect64_string,
    decode_rect64_uint64,
    encode_rect64_string,
    encode_rect64_uint64,
)
from picasa_py.faces.face_manager import PersonCluster, PicasaFaceManager

__all__ = [
    "FaceRect",
    "decode_rect64_string",
    "encode_rect64_string",
    "decode_rect64_uint64",
    "encode_rect64_uint64",
    "PicasaFaceManager",
    "PersonCluster",
]
