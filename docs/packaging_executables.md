# Guide de Génération des Exécutables & Gestion des Icônes Multi-OS (FR / EN)
# Cross-Platform Executable Packaging & OS Icon Guide (FR / EN)

> **Références Ghidra / Ghidra References** :
> - `picasa3.exe @ 0x009838D0` (`RegisterMainWindowClass` — Chargement de l'icône principale `RT_GROUP_ICON #105`)
> - `picasa3.exe @ 0x004D5CA0` (`WinMain` — Point d'entrée de l'application)
> - Ressource extraite / Extracted PE resource : [`ui/resources/icons/group_icon_105.ico`](../ui/resources/icons/group_icon_105.ico)

---

## 🇫🇷 Version Française

### 1. Vue d'ensemble

PyCasa peut être compilé en un **exécutable autonome** sans console pour **Windows**, **macOS** et **Linux** à l'aide de **PyInstaller**, du fichier de configuration [`pycasa.spec`](../pycasa.spec) et du script d'automatisation [`tools/build_executable.py`](../tools/build_executable.py).

L'exécutable généré embarque automatiquement dans son archive interne (`sys._MEIPASS`) :
- L'intégralité du dossier [`ui/resources/`](../ui/resources) :
  - les **11 groupes d'icônes PE** extraits de `picasa3.exe` (dont l'icône officielle multi-résolution `group_icon_105.ico` jusqu'en 256×256),
  - les **12 curseurs natifs** (`.cur`) avec leurs points chauds exacts,
  - les **3 084 fichiers XML de traduction** couvrant les **41 langues** de Picasa 3 (`OPTIONS_*.XML`, `STRINGRES_*.XML`, `LANGNAMES.XML`, `SHORTCUTS.XML`, etc.),
  - les définitions de filtres et de styles (`style/filterdesc.xml`, `style/constants.ui`),
  - le modèle de réseau de neurones et de quantification de reconnaissance faciale [`ui/resources/plugins/red.cfg`](../ui/resources/plugins/red.cfg) (ainsi que `Red.dll` et [`red_bridge_x86.exe`](../picasa_py/faces/red_bridge_x86.exe) pour Windows).

Au démarrage, [`_resolve_res_dir()`](../picasa_py/ui/resources.py#L22-L35) dans `picasa_py/ui/resources.py` et [`_get_candidate_plugin_dirs()`](../picasa_py/faces/detector.py#L60-L81) dans `picasa_py/faces/detector.py` détectent automatiquement `getattr(sys, "_MEIPASS", None)` afin de charger toutes les ressources depuis l'exécutable congelé.

---

### 2. Fonctionnement de l'icône officielle pour chaque OS

L'icône source unique est la ressource PE originale **`RT_GROUP_ICON #105`** extraite de `picasa3.exe` : [`ui/resources/icons/group_icon_105.ico`](../ui/resources/icons/group_icon_105.ico). Chaque système d'exploitation gère les icônes d'exécutables différemment :

| Système d'exploitation | Fichier généré dans `dist/` | Format d'icône requis par l'OS | Comment [`tools/build_executable.py`](../tools/build_executable.py) et [`pycasa.spec`](../pycasa.spec) l'appliquent |
| :--- | :--- | :--- | :--- |
| **Windows** (`win32`) | `dist\PyCasa.exe` | **`.ico`** intégré dans l'en-tête PE (`RT_GROUP_ICON`) | 1. **Explorateur Windows & Raccourcis** : `pycasa.spec` passe `icon="ui/resources/icons/group_icon_105.ico"` à `EXE(...)`, ce qui injecte directement l'icône multi-résolution (16×16 à 256×256) dans les ressources PE de `PyCasa.exe`.<br>2. **Barre de titre & Barre des tâches** : Au lancement, `PicasaMainWindow` et `QApplication` chargent `res_mgr.get_icon(105)` via `setWindowIcon()`. |
| **macOS** (`darwin`) | `dist/PyCasa.app` | **`.icns`** (Apple Icon Image) dans `Contents/Resources/` + déclaration `CFBundleIconFile` dans `Info.plist` | 1. **Conversion automatique `.ico` -> `.icns`** : Avant d'appeler PyInstaller, `ensure_macos_icns()` dans `tools/build_executable.py` convertit `group_icon_105.ico` en `ui/resources/icons/group_icon_105.icns` via Pillow (`img.save(..., format="ICNS")`).<br>2. **Finder & Dock macOS** : `pycasa.spec` crée un bundle `BUNDLE(..., name="PyCasa.app", icon=icns_path, bundle_identifier="com.google.picasa3.pycasa")` avec `NSHighResolutionCapable=True` (support Retina). |
| **Linux** (`linux`) | `dist/PyCasa` + `dist/PyCasa.png` + `dist/PyCasa.desktop` | **`.png` (256×256)** + lanceur **`.desktop`** (standard FreeDesktop / XDG) | Contrairement à Windows (PE) et macOS (`.app`), le format binaire **ELF** sous Linux ne stocke pas d'icône dans l'en-tête de l'exécutable : les environnements de bureau (GNOME, KDE Plasma, XFCE, Cinnamon) associent l'icône via un fichier `.desktop` et `StartupWMClass`.<br>1. **Menu d'applications & Bureau** : `generate_linux_desktop_assets()` dans `tools/build_executable.py` extrait `dist/PyCasa.png` (256×256 RGBA) depuis `group_icon_105.ico` et génère `dist/PyCasa.desktop` (`Icon=PyCasa`, `StartupWMClass=PyCasa`).<br>2. **Barre des tâches / Dock X11 & Wayland** : Au lancement, Qt applique `setWindowIcon(res_mgr.get_icon(105))` à la fenêtre principale. |

---

### 3. Commandes de génération locale (Windows, macOS, Linux)

#### Prérequis
```bash
pip install pyinstaller pillow PySide6 numpy opencv-python
```

#### Vérification à blanc (Dry-Run sans lancer la compilation)
```bash
python tools/build_executable.py --dry-run
```
Cette commande vérifie la présence de `main.py`, `pycasa.spec`, `ui/resources/icons/group_icon_105.ico` et `ui/resources/plugins/red.cfg`.

#### Compilation de l'exécutable pour l'OS courant
```bash
python tools/build_executable.py
```

- **Sous Windows** : produit `dist\PyCasa.exe` (double-cliquable directement, avec l'icône Picasa 3).
- **Sous macOS** : génère `ui/resources/icons/group_icon_105.icns` puis produit `dist/PyCasa.app` (glissable dans `/Applications`).
- **Sous Linux** : produit `dist/PyCasa`, `dist/PyCasa.png` et `dist/PyCasa.desktop`. Pour installer l'icône et le lanceur dans le menu d'applications de l'utilisateur sous Linux :
  ```bash
  mkdir -p ~/.local/share/icons/hicolor/256x256/apps ~/.local/share/applications ~/bin
  cp dist/PyCasa ~/bin/PyCasa
  cp dist/PyCasa.png ~/.local/share/icons/hicolor/256x256/apps/PyCasa.png
  sed "s|Exec=PyCasa|Exec=$HOME/bin/PyCasa|" dist/PyCasa.desktop > ~/.local/share/applications/PyCasa.desktop
  ```

---

### 4. Compilation multi-OS automatisée via GitHub Actions

Un workflow CI complet est fourni dans [`.github/workflows/build_executables.yml`](../.github/workflows/build_executables.yml). Il compile simultanément sur les 3 systèmes d'exploitation (`windows-latest`, `macos-latest`, `ubuntu-latest`) et publie les 3 artefacts prêts à l'emploi :
- `PyCasa-Windows-x64` (`PyCasa.exe`)
- `PyCasa-macOS-App` (`PyCasa.app.zip`)
- `PyCasa-Linux-x64` (`PyCasa`, `PyCasa.png`, `PyCasa.desktop`)

---
---

## 🇬🇧 English Version

### 1. Overview

PyCasa can be packaged into a **standalone GUI executable** (no console window) on **Windows**, **macOS**, and **Linux** using **PyInstaller**, the [`pycasa.spec`](../pycasa.spec) specification file, and the [`tools/build_executable.py`](../tools/build_executable.py) build helper script.

The generated executable automatically bundles into its internal archive (`sys._MEIPASS`):
- The entire [`ui/resources/`](../ui/resources) directory:
  - all **11 PE icon groups** extracted from `picasa3.exe` (including the official multi-resolution `group_icon_105.ico` up to 256×256),
  - all **12 native cursors** (`.cur`) with their exact hotspots,
  - all **3,084 localization XML files** covering all **41 languages** of Picasa 3 (`OPTIONS_*.XML`, `STRINGRES_*.XML`, `LANGNAMES.XML`, `SHORTCUTS.XML`, etc.),
  - filter and style definitions (`style/filterdesc.xml`, `style/constants.ui`),
  - the neural network and quantizer weights for facial recognition [`ui/resources/plugins/red.cfg`](../ui/resources/plugins/red.cfg) (as well as `Red.dll` and [`red_bridge_x86.exe`](../picasa_py/faces/red_bridge_x86.exe) for Windows).

At startup, [`_resolve_res_dir()`](../picasa_py/ui/resources.py#L22-L35) in `picasa_py/ui/resources.py` and [`_get_candidate_plugin_dirs()`](../picasa_py/faces/detector.py#L60-L81) in `picasa_py/faces/detector.py` automatically detect `getattr(sys, "_MEIPASS", None)` to load all assets from the frozen executable.

---

### 2. How the Official Icon Works on Each OS

The single source of truth for the icon is the original PE resource **`RT_GROUP_ICON #105`** extracted from `picasa3.exe`: [`ui/resources/icons/group_icon_105.ico`](../ui/resources/icons/group_icon_105.ico). Each operating system handles executable icons differently:

| Operating System | Output in `dist/` | OS Icon Format | How [`tools/build_executable.py`](../tools/build_executable.py) and [`pycasa.spec`](../pycasa.spec) Apply It |
| :--- | :--- | :--- | :--- |
| **Windows** (`win32`) | `dist\PyCasa.exe` | **`.ico`** embedded in PE header (`RT_GROUP_ICON`) | 1. **Windows Explorer & Shortcuts**: `pycasa.spec` passes `icon="ui/resources/icons/group_icon_105.ico"` to `EXE(...)`, embedding the multi-resolution icon (16×16 to 256×256) directly into the PE resources of `PyCasa.exe`.<br>2. **Title Bar & Taskbar**: At runtime, `PicasaMainWindow` and `QApplication` load `res_mgr.get_icon(105)` via `setWindowIcon()`. |
| **macOS** (`darwin`) | `dist/PyCasa.app` | **`.icns`** (Apple Icon Image) inside `Contents/Resources/` + `CFBundleIconFile` in `Info.plist` | 1. **Automatic `.ico` -> `.icns` conversion**: Before invoking PyInstaller, `ensure_macos_icns()` in `tools/build_executable.py` converts `group_icon_105.ico` into `ui/resources/icons/group_icon_105.icns` via Pillow (`img.save(..., format="ICNS")`).<br>2. **macOS Finder & Dock**: `pycasa.spec` builds a macOS application bundle `BUNDLE(..., name="PyCasa.app", icon=icns_path, bundle_identifier="com.google.picasa3.pycasa")` with `NSHighResolutionCapable=True` (Retina support). |
| **Linux** (`linux`) | `dist/PyCasa` + `dist/PyCasa.png` + `dist/PyCasa.desktop` | **`.png` (256×256)** + **`.desktop`** launcher (FreeDesktop / XDG standard) | Unlike Windows (PE) and macOS (`.app`), the Linux **ELF** binary format does not embed icons inside the executable header; desktop environments (GNOME, KDE Plasma, XFCE, Cinnamon) associate the icon through a `.desktop` entry and `StartupWMClass`.<br>1. **App Menu & Desktop**: `generate_linux_desktop_assets()` in `tools/build_executable.py` extracts `dist/PyCasa.png` (256×256 RGBA) from `group_icon_105.ico` and generates `dist/PyCasa.desktop` (`Icon=PyCasa`, `StartupWMClass=PyCasa`).<br>2. **X11 & Wayland Taskbar / Dock**: At runtime, Qt applies `setWindowIcon(res_mgr.get_icon(105))` to the main window. |

---

### 3. Local Build Commands (Windows, macOS, Linux)

#### Prerequisites
```bash
pip install pyinstaller pillow PySide6 numpy opencv-python
```

#### Dry-Run Check (Validate Assets Without Building)
```bash
python tools/build_executable.py --dry-run
```

#### Build the Standalone Executable for the Current OS
```bash
python tools/build_executable.py
```

- **On Windows**: produces `dist\PyCasa.exe` (ready to launch with the embedded Picasa 3 icon).
- **On macOS**: generates `ui/resources/icons/group_icon_105.icns` and produces `dist/PyCasa.app` (can be dragged into `/Applications`).
- **On Linux**: produces `dist/PyCasa`, `dist/PyCasa.png`, and `dist/PyCasa.desktop`. To install the icon and desktop launcher in the user's application menu on Linux:
  ```bash
  mkdir -p ~/.local/share/icons/hicolor/256x256/apps ~/.local/share/applications ~/bin
  cp dist/PyCasa ~/bin/PyCasa
  cp dist/PyCasa.png ~/.local/share/icons/hicolor/256x256/apps/PyCasa.png
  sed "s|Exec=PyCasa|Exec=$HOME/bin/PyCasa|" dist/PyCasa.desktop > ~/.local/share/applications/PyCasa.desktop
  ```

---

### 4. Automated Cross-Platform Builds via GitHub Actions

A multi-OS GitHub Actions workflow is provided in [`.github/workflows/build_executables.yml`](../.github/workflows/build_executables.yml). It builds on `windows-latest`, `macos-latest`, and `ubuntu-latest` in parallel and uploads three ready-to-run artifacts:
- `PyCasa-Windows-x64` (`PyCasa.exe`)
- `PyCasa-macOS-App` (`PyCasa.app.zip`)
- `PyCasa-Linux-x64` (`PyCasa`, `PyCasa.png`, `PyCasa.desktop`)
