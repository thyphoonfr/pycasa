# -*- mode: python ; coding: utf-8 -*-
"""
FR: Spécification PyInstaller multi-OS (Windows, macOS, Linux) pour l'exécutable autonome PyCasa.
Embarque l'icône officielle Picasa 3 (group_icon_105.ico extraite des ressources PE de picasa3.exe),
l'ensemble du répertoire ui/resources/ (icônes, bitmaps, dialogues, tables de chaînes, plugins/red.cfg,
plugins/Red.dll) ainsi que le pont de reconnaissance faciale 32-bit picasa_py/faces/red_bridge_x86.exe.

EN: Multi-OS PyInstaller specification (Windows, macOS, Linux) for the standalone PyCasa executable.
Embeds the official Picasa 3 icon (group_icon_105.ico extracted from picasa3.exe PE resources),
the entire ui/resources/ directory (icons, bitmaps, dialogs, string tables, plugins/red.cfg,
plugins/Red.dll) as well as the 32-bit facial recognition bridge picasa_py/faces/red_bridge_x86.exe.

Ref: picasa3.exe PE Resource Group Icon ID 105 (ui/resources/icons/group_icon_105.ico)
Ref: picasa3.exe @ 0x004D5CA0 (WinMain / Application Entry Point)
"""

import os
import sys
from pathlib import Path

block_cipher = None

# FR: Répertoire racine du projet PyCasa
# EN: Root directory of the PyCasa project
PROJECT_ROOT = Path(SPECPATH).resolve()

# FR: Données et binaires embarqués dans l'archive PyInstaller (_MEIPASS)
# EN: Data files and binaries bundled inside the PyInstaller archive (_MEIPASS)
datas = []
binaries = []

res_dir = PROJECT_ROOT / "ui" / "resources"
if res_dir.is_dir():
    datas.append((str(res_dir), os.path.join("ui", "resources")))

red_bridge = PROJECT_ROOT / "picasa_py" / "faces" / "red_bridge_x86.exe"
if red_bridge.is_file():
    datas.append((str(red_bridge), os.path.join("picasa_py", "faces")))

# FR: Sélection de l'icône officielle selon le système d'exploitation cible
# EN: Official icon selection according to the target operating system
ico_path = res_dir / "icons" / "group_icon_105.ico"
icns_path = res_dir / "icons" / "group_icon_105.icns"

if sys.platform == "darwin" and icns_path.is_file():
    app_icon = str(icns_path)
elif ico_path.is_file():
    app_icon = str(ico_path)
else:
    app_icon = None

# FR: Modules cachés requis par PySide6, Pillow, numpy et les sous-systèmes PyCasa
# EN: Hidden imports required by PySide6, Pillow, numpy, and PyCasa subsystems
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtSvg",
    "PySide6.QtPrintSupport",
    "PIL",
    "PIL.Image",
    "PIL.ImageOps",
    "PIL.ImageEnhance",
    "PIL.ImageFilter",
    "PIL.ExifTags",
    "PIL.IcoImagePlugin",
    "numpy",
]

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# FR: Sur Windows et Linux, construction d'un exécutable autonome unique (onefile)
# Sur macOS, construction d'un bundle .app standard en plus du binaire
# EN: On Windows and Linux, build a single-file standalone executable (onefile)
# On macOS, build a standard .app bundle in addition to the binary
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PyCasa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=(sys.platform == "darwin"),
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from picasa_py.version import APP_NAME, APP_VERSION

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=app_icon,
        bundle_identifier="com.google.picasa3.pycasa",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": f"{APP_NAME} {APP_VERSION}",
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "NSHighResolutionCapable": True,
        },
    )
