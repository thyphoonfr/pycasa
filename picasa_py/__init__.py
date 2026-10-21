"""
FR: PyCasa — Portage Python fidèle et multi-OS de Picasa 3.9.141.259.
Basé exclusivement sur le désassemblage Ghidra de picasa3.exe.
Pour modifier la version de l'application, éditez `picasa_py/version.py`.

EN: PyCasa — Faithful cross-platform Python port of Picasa 3.9.141.259.
Based exclusively on the Ghidra disassembly of picasa3.exe.
To change the application version, edit `picasa_py/version.py`.
"""

from picasa_py.version import (
    APP_FULL_TITLE,
    APP_NAME,
    APP_VERSION,
    VERSION_W,
    VERSION_X,
    VERSION_Y,
    VERSION_Z,
    __version__,
    get_about_dialog_text,
    get_about_dialog_title,
    get_version_parts,
    get_window_title,
)

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "APP_FULL_TITLE",
    "VERSION_Z",
    "VERSION_Y",
    "VERSION_X",
    "VERSION_W",
    "__version__",
    "get_window_title",
    "get_version_parts",
    "get_about_dialog_title",
    "get_about_dialog_text",
]
