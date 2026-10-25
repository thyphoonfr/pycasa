"""
FR: Fichier central de définition du nom et de la version de l'application PyCasa.
Pour modifier le nom ou la version affichée partout dans l'application (barre de titre
de la fenêtre principale, boîte de dialogue « À propos de PyCasa », écran de démarrage
SplashScreen, métadonnées Qt et exécutables PyInstaller), modifiez uniquement les
constantes `APP_NAME` et `APP_VERSION` ci-dessous.

EN: Central configuration file for the PyCasa application name and version.
To change the name or version displayed everywhere across the application (main window
title bar, "About PyCasa" dialog, SplashScreen, Qt metadata, and PyInstaller builds),
edit only the `APP_NAME` and `APP_VERSION` constants below.

Ref: picasa3.exe PE VS_VERSION_INFO (FileVersion / ProductVersion = 3.9.141.259)
Ref: picasa3.exe @ 0x0087FC90 (SplashThread version display)
Ref: STRINGRES_*.XML (IDS_VERSION, IDS_BUILDNUMBER, IDS_ABOUT1, about/window1.title)
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

# ==============================================================================
# FR: POINT UNIQUE DE MODIFICATION DE LA VERSION POUR LE DÉVELOPPEUR (FORMAT z.y.x.w)
# - z (VERSION_Z) & y (VERSION_Y) : modifiables uniquement par l'utilisateur (3.9).
# - x (VERSION_X) : incrémenté à chaque demande d'ajout de fonctionnalité (initialisé à 145).
# - w (VERSION_W) : incrémenté à chaque changement dans le code.
#
# EN: SINGLE POINT OF TRUTH FOR DEVELOPER VERSIONING (z.y.x.w FORMAT)
# - z (VERSION_Z) & y (VERSION_Y): user-controlled only (3.9).
# - x (VERSION_X): incremented on each new feature request (initialized to 145).
# - w (VERSION_W): incremented on every code change.
# ==============================================================================
APP_NAME: str = "PyCasa"

VERSION_Z: int = 3
VERSION_Y: int = 9
VERSION_X: int = 153
VERSION_W: int = 319

APP_VERSION: str = f"{VERSION_Z}.{VERSION_Y}.{VERSION_X}.{VERSION_W}"

# FR: Titre complet affiché dans la barre de titre de la fenêtre principale
# EN: Full title displayed in the main window title bar
APP_FULL_TITLE: str = f"{APP_NAME} {APP_VERSION}"
__version__: str = APP_VERSION


def get_window_title() -> str:
    """
    FR: Retourne le titre complet de la fenêtre principale (ex: "PyCasa 3.9.145.260").
    EN: Returns the full main window title (e.g. "PyCasa 3.9.145.260").
    """
    return f"{APP_NAME} {APP_VERSION}"


def get_version_parts() -> Tuple[str, str]:
    """
    FR: Sépare `APP_VERSION` en (version_courte, numero_build).
    Exemple : "3.9.141.259" -> ("3.9.141", "259").
    EN: Splits `APP_VERSION` into (short_version, build_number).
    Example: "3.9.141.259" -> ("3.9.141", "259").
    """
    parts = APP_VERSION.split(".")
    if len(parts) >= 4:
        return ".".join(parts[:3]), parts[3]
    return APP_VERSION, ""


def get_about_dialog_title(res_mgr: Optional[Any] = None) -> str:
    """
    FR: Retourne le titre traduit de la fenêtre « À propos de PyCasa ».
    EN: Returns the localized title for the "About PyCasa" dialog.
    Ref: ABOUT_*.XML (about/window1.title)
    """
    raw_title = f"À propos de {APP_NAME}"
    if res_mgr is not None and hasattr(res_mgr, "get_xml_string"):
        try:
            raw_title = res_mgr.get_xml_string("ABOUT", "about/window1.title", raw_title)
        except Exception:
            pass
    return raw_title.replace("Picasa", APP_NAME)


def get_about_dialog_text(res_mgr: Optional[Any] = None) -> str:
    """
    FR: Construit le texte complet de la boîte de dialogue « À propos de PyCasa »
    incluant le nom et la version complète (`PyCasa 3.9.141.259`), le numéro de build
    et les mentions légales traduites de `STRINGRES_*.XML` / `ABOUT_*.XML`.
    EN: Builds the full text for the "About PyCasa" dialog including the application
    name and complete version (`PyCasa 3.9.141.259`), build number, and localized
    notices from `STRINGRES_*.XML` / `ABOUT_*.XML`.
    Ref: STRINGRES_*.XML (IDS_ABOUT1, IDS_BUILDNUMBER), ABOUT_*.XML
    """
    short_ver, build_num = get_version_parts()
    version_display = f"{short_ver} (Build {build_num})" if build_num else APP_VERSION

    raw_about = (
        f"{APP_NAME} {version_display}\n\n"
        "Copyright (c) Google, Inc. 2003-2015. Tous droits réservés.\n\n"
        "Ce logiciel repose en partie sur les travaux de l'IJG (Independent JPEG Group)."
    )
    if res_mgr is not None:
        try:
            if hasattr(res_mgr, "get_stringres"):
                xml_about = res_mgr.get_stringres("IDS_ABOUT1", "")
                if xml_about:
                    raw_about = xml_about.replace("\\n", "\n")
            elif hasattr(res_mgr, "get_string"):
                pe_about = res_mgr.get_string(298, "")
                if pe_about:
                    raw_about = pe_about
        except Exception:
            pass

    if "%s" in raw_about:
        raw_about = raw_about.replace("%s", version_display, 1)
    raw_about = raw_about.replace("Picasa\u00a0", f"{APP_NAME} ").replace("Picasa ", f"{APP_NAME} ", 1)

    header = f"{APP_NAME} {APP_VERSION}"
    if build_num:
        header += f"\nVersion {short_ver} (Build {build_num}) — Version complète : {APP_VERSION}"
    else:
        header += f"\nVersion complète : {APP_VERSION}"

    return f"{header}\n\n{raw_about}"
