# PyCasa — Google Picasa 3.9 Reborn in Python (Windows, macOS, Linux)

> [!CAUTION]
> **🇫🇷 AVERTISSEMENT IMPORTANT — UTILISATION À VOS RISQUES ET PÉRILS :**
> Bien que **PyCasa** ait fait l'objet de nombreux tests de non-régression, d'aller-retour binaire au bit près (*round-trip*) et d'interopérabilité croisée avec `picasa3.exe`, ce logiciel est fourni **« TEL QUEL » (*AS IS*), sans aucune garantie d'aucune sorte**, expresse ou implicite. L'utilisation de ce logiciel sur vos photothèques se fait **sous votre entière responsabilité et à vos propres risques et périls**.
> **Précaution indispensable avant toute utilisation :** effectuez **toujours une sauvegarde complète** de vos dossiers de photos, de vos fichiers `.picasa.ini` et de votre base de données Picasa (`%LOCALAPPDATA%\Google\Picasa2\db3` et `contacts\contacts.xml`) avant d'utiliser PyCasa.
>
> **🇬🇧 IMPORTANT DISCLAIMER — USE AT YOUR OWN RISK:**
> Although **PyCasa** has undergone extensive unit, byte-for-byte round-trip, and cross-interoperability testing against `picasa3.exe`, this software is provided **"AS IS", without warranty of any kind**, express or implied. Using this software on your photo library is **strictly at your own risk**.
> **Essential precaution before use:** **always make a full backup** of your photo folders, `.picasa.ini` files, and Picasa database (`%LOCALAPPDATA%\Google\Picasa2\db3` and `contacts\contacts.xml`) before running PyCasa.

> **EN:** A faithful, cross-platform Python & PySide6 re-implementation of **Google Picasa 3** with **100% byte-for-byte database, `.picasa.ini`, and neural face recognition compatibility**, built through clean-room reverse engineering of `picasa3.exe` and `Red.dll` in Ghidra.
>
> **FR :** Une réimplémentation Python & PySide6 multi-plateforme (**Windows, macOS, Linux**) fidèle au bit près et au pixel près de **Google Picasa 3**, offrant **100 % de compatibilité binaire avec la base de données, les fichiers `.picasa.ini` et le moteur neuronal de reconnaissance faciale**, réalisée par rétro-ingénierie sous Ghidra de `picasa3.exe` et `Red.dll`.

---

## 🌍 Table of Contents / Sommaire

- [🇬🇧 English Documentation](#-english-documentation)
  - [Overview](#overview)
  - [Key Features](#key-features)
  - [Architecture & Repository Layout](#architecture--repository-layout)
  - [Installation & Running from Source](#installation--running-from-source)
  - [Building Standalone Executables (Windows, macOS, Linux)](#building-standalone-executables-windows-macos-linux)
  - [Testing & Public Test Photos](#testing--public-test-photos)
  - [Versioning Policy (`z.y.x.w`)](#versioning-policy-zyxw)
- [🇫🇷 Documentation Française](#-documentation-française)
  - [Présentation](#présentation)
  - [Fonctionnalités principales](#fonctionnalités-principales)
  - [Architecture et organisation du dépôt](#architecture-et-organisation-du-dépôt)
  - [Installation et lancement depuis les sources](#installation-et-lancement-depuis-les-sources)
  - [Génération des exécutables autonomes (Windows, macOS, Linux)](#génération-des-exécutables-autonomes-windows-macos-linux)
  - [Tests et photos publiques de test](#tests-et-photos-publiques-de-test)
  - [Politique de versionnage (`z.y.x.w`)](#politique-de-versionnage-zyxw)

---

# 🇬🇧 English Documentation

## Overview

**PyCasa** (`v3.9.145.x`) is an open-source, cross-platform (**Windows, macOS, Linux**) Python re-implementation of **Google Picasa 3.9 (`picasa3.exe`)**. Every data structure, binary format, UI layout, non-destructive filter, and face recognition algorithm is traced directly to its disassembled routine in `picasa3.exe` and `Red.dll` (see [`AGENTS.md`](AGENTS.md) and [`docs/`](docs/)).

Because **PyCasa** reads and writes the exact binary formats of Picasa 3, you can run `picasa3.exe` and **PyCasa** alternately on the same photo library and database without data loss, corruption, or forced re-indexing.

## Key Features

1. **100% Byte-for-Byte Database Compatibility (`db3/`)**
   - Full read/write support for `thumbindex.db` (`CThumbIndex`, magic `0x40466666`, 32-byte records, media & `1001` face sub-records).
   - All 56 `.pmp` columnar property tables (`CPropertyMap`, magic `0x3FCCCCCD`, types `0x0..0x7` across `imagedata_*`, `catdata_*`, `albumdata_*`).
   - All 6 `CBlockFile` index/container pairs (`thumbs`, `thumbs2`, `bigthumbs`, `previews`, `albums`, `facetemplatesV2`) with exact header/entry checksums.
   - `wordhash.dat` search dictionary, `repository.dat`, `usernames.dat`, `.pal` XML album definitions, and `contacts.xml`.

2. **100% Exact `.picasa.ini` Parser & Writer**
   - Dedicated parser (`FUN_009be730`) and atomic writer (`FUN_0068ac80`) preserving section/key order, CRLF line endings, UTF-8/ANSI fallback, `faces=rect64(...)`, `filters=...`, `crop64=...`, `tilt=1,angle,scale`, `star=yes`, `backuphash`, `[Contacts2]`, and `[.album:...]`.

3. **Bit-Exact Neural Face Detection & Recognition (`Red.dll` + `red.cfg`)**
   - **Native 32-bit Mode (Windows)**: Drives the original `plugins\Red.dll` + `plugins\red.cfg` via a persistent 32-bit bridge process ([`red_bridge_x86.exe`](picasa_py/faces/red_bridge.cs)).
   - **Pure Python/NumPy Mode (Windows, macOS, Linux)**: [`PurePythonRedEngine`](picasa_py/faces/red_engine_py.py) deserializes 100% of the 2,281,657 bytes of [`ui/resources/plugins/red.cfg`](ui/resources/plugins/red.cfg) and executes the exact 23-stage `faco` cascade, `faci` eye localizers, 90×3840 subspace projection, 4-bit quantization, and `vqc_Relator` matching — producing **bit-identical 1,044-byte `vqc_Cue` face templates (`max_diff = 0`)**.

4. **Faithful UI, 84 Non-Destructive Filters & 41 Languages**
   - **Library View**: Virtualized 60 FPS thumbnail grid, sticky album headers, `AVCScrollThrottle` speed-sensitive scrollbar with timeline tooltip, continuous multi-album scroll, Folder/Album/People tree, and top filter bar (Stars, Faces, Movies, Geotagged, Search, Timeline slider).
   - **One-Up & Side-by-Side (Two-Up) Editor**: Top navigation filmstrip, 5-tab editing panel (*Commonly Needed Fixes*, *Tuning*, *Effects 1*, *Effects 2*, *Effects 3*), live non-cumulative adjustment sliders, interactive subpanels (`PicasaEffectSubpanel`) with live preview and Apply/Cancel for all 32 parameterized filters, plus 52 one-click filters (84 total from `runtime/filterdesc.xml`).
   - **Right Drawer & Studios**: Collapsible Right Drawer (*People*, *Places* with interactive OpenStreetMap/Leaflet geotagging, *Tags* with 10 Quick Tags `Alt+1..0`, *EXIF Properties*), Photo Tray with stacking, Collage Studio, Movie Maker, Face Movie, Slideshow, Print / Contact Sheet, and 5 dynamic themes (*Original*, *Dark*, *Ocean*, *Emerald Forest*, *Sepia Warm*).
   - **41 Official Languages**: Loaded dynamically from `ui/resources/xml/` with live UI retranslation.

## Architecture & Repository Layout

```text
.
├── AGENTS.md                  # Clean-room engineering rules & Ghidra traceability standards
├── main.py                    # Application entry point
├── pycasa.spec                # PyInstaller cross-platform specification (with OS icons)
├── pyproject.toml             # Python package configuration & metadata
├── requirements.txt           # Runtime & test dependencies
├── docs/
│   ├── analysis/              # Decompiled C functions from picasa3.exe & Red.dll
│   ├── formats/               # Binary format specifications (DB, PMP, CBlockFile, INI)
│   ├── perf/                  # Performance targets & benchmarks documentation
│   ├── ui/                    # UI layout & toolkit documentation
│   ├── open-questions.md      # Documented edge cases & resolved binary questions
│   └── packaging_executables.md # Guide for building Windows/macOS/Linux executables
├── ghidra/
│   └── scripts/               # Ghidra Java extraction & decompilation scripts
├── picasa_py/
│   ├── version.py             # Centralized version definition (z.y.x.w)
│   ├── db/                    # Binary database readers/writers (db3/, PMP, CBlockFile, contacts)
│   ├── ini/                   # Dedicated .picasa.ini parser, model, and writer
│   ├── faces/                 # Face detection & recognition (Red.dll bridge + PurePythonRedEngine)
│   ├── scanner/               # Background filesystem scanner & live watcher
│   └── ui/                    # PySide6 GUI, 84 image filters, dialogs, and creative studios
├── ui/
│   └── resources/             # Extracted PE resources (icons, cursors, 41 XML locales, red.cfg)
├── tests/
│   ├── fixtures/              # Read-only reference fixtures (db/, ini/, photos/)
│   └── test_*.py              # 50+ unit, round-trip, interoperability, and UI test modules
├── benchmarks/                # Automated performance benchmarks (pytest-benchmark)
└── tools/                     # Binary inspection, PE extraction, and PyInstaller build scripts
```

## Installation & Running from Source

### Prerequisites
- **Python 3.11+** (tested up to Python 3.14)
- **OS**: Windows, macOS, or Linux

```bash
# Install dependencies
pip install -r requirements.txt

# Launch PyCasa (automatically detects the default OS Picasa db3 directory)
python main.py

# Or launch with a specific db3 database directory
python main.py "path/to/db3"
```

## Building Standalone Executables (Windows, macOS, Linux)

PyCasa includes an automated cross-platform build script ([`tools/build_executable.py`](tools/build_executable.py)) and a GitHub Actions workflow ([`.github/workflows/build_executables.yml`](.github/workflows/build_executables.yml)) that package PyCasa with its official Picasa 3 icon (`ui/resources/icons/group_icon_105.ico`, auto-converted to `.icns` on macOS and `.png` + `.desktop` on Linux):

```bash
pip install pyinstaller
python tools/build_executable.py
```

- **Windows**: `dist/PyCasa/PyCasa.exe` (`PyCasa-<version>-Windows-x64.zip`)
- **macOS**: `dist/PyCasa.app` (`PyCasa-<version>-macOS.zip`)
- **Linux**: `dist/PyCasa/PyCasa` + `dist/PyCasa/PyCasa.desktop` (`PyCasa-<version>-Linux-x64.tar.gz`)

Pre-built standalone releases for **Windows (64-bit)**, **macOS**, and **Linux (x86_64)** are available directly on the **[GitHub Releases page](https://github.com/thyphoonfr/pycasa/releases)**. Pushing a `v*` tag (`git tag v3.9.150.x && git push origin v3.9.150.x`) automatically builds and publishes all three OS packages to GitHub Releases.

See **[`docs/packaging_executables.md`](docs/packaging_executables.md)** for full details.

## Testing & Public Test Photos

Run the full test suite with `pytest`:

```bash
pytest
```

- All unit, byte-for-byte round-trip (`tests/test_roundtrip_*.py`), interoperability (`tests/test_interop_*.py`), face recognition (`tests/test_faces.py`), and UI tests run **100% out-of-the-box** without requiring a pre-existing personal photo library.
- If you want to add **public-domain / Creative Commons test photos** for additional real-photo testing, place them in **[`tests/fixtures/photos/`](tests/fixtures/photos/README.md)**.

## Versioning Policy (`z.y.x.w`)

The application version is managed centrally in [`picasa_py/version.py`](picasa_py/version.py) following the **`z.y.x.w`** scheme (`AGENTS.md` §9.10):
- **`z.y`** (`3.9`): Reserved exclusively for the project owner.
- **`x`** (initialized at `145`): Incremented on every new feature request.
- **`w`**: Incremented on every code modification, bug fix, or refactoring.

---

# 🇫🇷 Documentation Française

## Présentation

**PyCasa** (`v3.9.145.x`) est une réimplémentation open-source et multi-plateforme (**Windows, macOS, Linux**) en Python & PySide6 de **Google Picasa 3.9 (`picasa3.exe`)**. Chaque structure binaire, algorithme de base de données, mise en page d'interface, filtre non destructif et réseau neuronal de détection de visages est relié directement à son adresse dans le désassemblage Ghidra de `picasa3.exe` et `Red.dll` (voir [`AGENTS.md`](AGENTS.md) et [`docs/`](docs/)).

Grâce à sa compatibilité binaire au bit près, `picasa3.exe` et **PyCasa** peuvent travailler **alternativement sur la même photothèque** sans perte, corruption ni ré-indexation forcée.

## Fonctionnalités principales

1. **Compatibilité binaire 100 % avec la base de données Picasa 3 (`db3/`)**
   - Lecture et écriture bit-à-bit de `thumbindex.db` (`CThumbIndex`, magic `0x40466666`, enregistrements de 32 octets, photos et sous-enregistrements visages `type 1001`).
   - Prise en charge des 56 tables colonnes `.pmp` (`CPropertyMap`, magic `0x3FCCCCCD`, types `0x0..0x7` sur `imagedata_*`, `catdata_*`, `albumdata_*`).
   - Prise en charge des 6 paires de conteneurs `CBlockFile` (`thumbs`, `thumbs2`, `bigthumbs`, `previews`, `albums`, `facetemplatesV2`) avec calcul exact des checksums.
   - Dictionnaire de recherche `wordhash.dat`, `repository.dat`, `usernames.dat`, albums `.pal` et `contacts.xml`.

2. **Compatibilité 100 % avec les fichiers `.picasa.ini`**
   - Parseur (`FUN_009be730`) et writer atomique (`FUN_0068ac80`) dédiés préservant l'ordre des sections et des clés, les fins de ligne CRLF, l'encodage UTF-8/ANSI, `faces=rect64(...)`, `filters=...`, `crop64=...`, `tilt=1,angle,scale`, `star=yes`, `backuphash`, `[Contacts2]` et `[.album:...]`.

3. **Reconnaissance faciale neuronale exacte au bit près (`Red.dll` + `red.cfg`)**
   - **Mode Natif 32 bits (Windows)** : exécute `plugins\Red.dll` + `plugins\red.cfg` via le pont [`red_bridge_x86.exe`](picasa_py/faces/red_bridge.cs).
   - **Mode Python/NumPy pur désassemblé (Windows, macOS, Linux)** : [`PurePythonRedEngine`](picasa_py/faces/red_engine_py.py) désérialise 100 % des 2 281 657 octets de [`ui/resources/plugins/red.cfg`](ui/resources/plugins/red.cfg) et reproduit au bit près la cascade `faco` à 23 étages, les localisateurs d'yeux `faci`, la projection sous-espace 90×3840, la quantification 4 bits et le comparateur `vqc_Relator` (signatures `vqc_Cue` de 1 044 octets avec **`max_diff = 0`**).

4. **Interface fidèle, 84 filtres non destructifs et 41 langues**
   - **Vue Photothèque** : grille de vignettes virtualisée à 60 FPS, en-têtes d'albums épinglés (*sticky headers*), barre de défilement `AVCScrollThrottle` à vitesse variable avec bulle chronologique, défilement continu multi-albums, arborescence Dossiers/Albums/Personnes et barre supérieure de filtres.
   - **Éditeur One-Up et Comparaison Côte-à-côte (Two-Up)** : pellicule supérieure (*filmstrip*), panneau d'édition à 5 onglets (*Retouches courantes*, *Réglages*, *Effets 1*, *Effets 2*, *Effets 3*), curseurs d'exposition non cumulatifs en temps réel, sous-panneaux de réglage (`PicasaEffectSubpanel`) avec aperçu en direct et boutons Appliquer/Annuler pour les 32 filtres paramétrables, et 84 filtres au total issus de `runtime/filterdesc.xml`.
   - **Tiroir droit et ateliers créatifs** : Tiroir droit repliable (*Personnes*, *Lieux* avec carte interactive OpenStreetMap/Leaflet, *Tags* + 10 Tags Rapides `Alt+1..0`, *Propriétés EXIF*), Bac à photos avec empilement, Créateur de montages (*Collage*), Créateur de films (*Movie Maker*), Film de visages (*Face Movie*), Diaporama, Impression / Planche-contact, 5 thèmes dynamiques et **41 langues officielles** (`ui/resources/xml/`).

## Installation et lancement depuis les sources

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer PyCasa (détecte automatiquement le dossier db3 de l'OS)
python main.py

# Ou spécifier un dossier db3 personnalisé
python main.py "chemin/vers/db3"
```

## Génération des exécutables autonomes (Windows, macOS, Linux)

Le script [`tools/build_executable.py`](tools/build_executable.py) génère un exécutable autonome avec l'icône officielle de Picasa 3 (`ui/resources/icons/group_icon_105.ico`, convertie automatiquement en `.icns` sous macOS et `.png` + `.desktop` sous Linux) :

```bash
pip install pyinstaller
python tools/build_executable.py
```

Consultez **[`docs/packaging_executables.md`](docs/packaging_executables.md)** pour la documentation complète par système d'exploitation.

Les exécutables pré-compilés pour **Windows (64 bits)**, **macOS** et **Linux (x86_64)** sont téléchargeables directement sur la page **[GitHub Releases](https://github.com/thyphoonfr/pycasa/releases)**. Tout tag `v*` poussé sur GitHub (`git tag v3.9.150.x && git push origin v3.9.150.x`) compile et publie automatiquement les 3 versions dans GitHub Releases.

## Tests et photos publiques de test

Pour lancer l'ensemble de la suite de tests :

```bash
pytest
```

- Tous les tests unitaires, round-trip binaires (`tests/test_roundtrip_*.py`), d'interopérabilité (`tests/test_interop_*.py`), de visages (`tests/test_faces.py`) et d'interface s'exécutent **à 100 % sans nécessiter de photothèque personnelle locale**.
- Si vous souhaitez ajouter des **photos publiques de test** (domaine public / Creative Commons, sans données personnelles conformément à `AGENTS.md` §9.9), placez-les dans **[`tests/fixtures/photos/`](tests/fixtures/photos/README.md)**.

## Politique de versionnage (`z.y.x.w`)

Le numéro de version est centralisé dans [`picasa_py/version.py`](picasa_py/version.py) au format **`z.y.x.w`** (`AGENTS.md` §9.10) :
- **`z.y`** (`3.9`) : réservés exclusivement à l'utilisateur.
- **`x`** (initialisé à `145`) : incrémenté à chaque demande d'ajout de fonctionnalité.
- **`w`** : incrémenté à chaque modification du code (correction, ajustement, refactoring).
