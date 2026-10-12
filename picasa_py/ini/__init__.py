"""
Module de gestion des fichiers INI Picasa (.picasa.ini, Picasa.ini).
"""

from picasa_py.ini.model import IniEntry, IniSection, FaceItem, CropRect, ContactInfo
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.ini.writer import PicasaIniWriter

__all__ = [
    "IniEntry",
    "IniSection",
    "FaceItem",
    "CropRect",
    "ContactInfo",
    "PicasaIniParser",
    "PicasaIniDocument",
    "PicasaIniWriter",
]
