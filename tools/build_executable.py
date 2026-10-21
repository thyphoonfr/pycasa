#!/usr/bin/env python3
"""
FR: Script de construction multi-plateforme (Windows, macOS, Linux) de l'exécutable autonome PyCasa.
Prépare les ressources d'icônes spécifiques à l'OS à partir de l'icône officielle Picasa 3
(`ui/resources/icons/group_icon_105.ico`) :
- Windows : utilise directement `group_icon_105.ico` pour `PyCasa.exe`
- macOS   : convertit `group_icon_105.ico` en `group_icon_105.icns` via Pillow pour `PyCasa.app`
- Linux   : extrait `PyCasa.png` (256x256) et génère le lanceur XDG `PyCasa.desktop` dans `dist/`
Puis invoque PyInstaller avec `pycasa.spec`.

EN: Cross-platform build script (Windows, macOS, Linux) for the standalone PyCasa executable.
Prepares OS-specific icon assets from the official Picasa 3 icon
(`ui/resources/icons/group_icon_105.ico`):
- Windows : directly uses `group_icon_105.ico` for `PyCasa.exe`
- macOS   : converts `group_icon_105.ico` to `group_icon_105.icns` via Pillow for `PyCasa.app`
- Linux   : extracts `PyCasa.png` (256x256) and generates the XDG launcher `PyCasa.desktop` in `dist/`
Then invokes PyInstaller with `pycasa.spec`.

Ref: picasa3.exe PE Resource Group Icon ID 105 (ui/resources/icons/group_icon_105.ico)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = PROJECT_ROOT / "pycasa.spec"
ICO_PATH = PROJECT_ROOT / "ui" / "resources" / "icons" / "group_icon_105.ico"
ICNS_PATH = PROJECT_ROOT / "ui" / "resources" / "icons" / "group_icon_105.icns"
DIST_DIR = PROJECT_ROOT / "dist"


def ensure_macos_icns(ico_path: Path = ICO_PATH, icns_path: Path = ICNS_PATH) -> Optional[Path]:
    """
    FR: Convertit l'icône .ico de Picasa 3 en fichier .icns pour macOS à l'aide de Pillow.
    EN: Converts the Picasa 3 .ico icon into a macOS .icns file using Pillow.
    """
    if not ico_path.is_file():
        print(f"[WARN] Icon file not found / Fichier icône introuvable: {ico_path}")
        return None
    try:
        from PIL import Image

        with Image.open(ico_path) as img:
            rgba_img = img.convert("RGBA")
            icns_path.parent.mkdir(parents=True, exist_ok=True)
            rgba_img.save(icns_path, format="ICNS")
        print(f"[OK] Generated macOS icon / Icône macOS générée: {icns_path}")
        return icns_path
    except Exception as exc:
        print(f"[WARN] Could not generate .icns via Pillow ({exc}); falling back to .ico")
        return None


def generate_linux_desktop_assets(ico_path: Path = ICO_PATH, dist_dir: Path = DIST_DIR) -> Optional[Path]:
    """
    FR: Extrait l'icône PNG haute résolution et génère un fichier .desktop conforme XDG pour Linux.
    EN: Extracts the high-resolution PNG icon and generates an XDG-compliant .desktop file for Linux.
    """
    dist_dir.mkdir(parents=True, exist_ok=True)
    png_path = dist_dir / "PyCasa.png"
    desktop_path = dist_dir / "PyCasa.desktop"

    if ico_path.is_file():
        try:
            from PIL import Image

            with Image.open(ico_path) as img:
                rgba_img = img.convert("RGBA")
                rgba_img.save(png_path, format="PNG")
            print(f"[OK] Extracted Linux PNG icon / Icône PNG Linux extraite: {png_path}")
        except Exception as exc:
            print(f"[WARN] Could not extract PNG icon ({exc})")

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from picasa_py.version import APP_NAME, APP_VERSION

    desktop_content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME} {APP_VERSION}\n"
        "GenericName=Photo Organizer and Viewer\n"
        f"Comment=1:1 Python Port of Picasa {APP_VERSION}\n"
        f"Comment[fr]=Portage Python fidèle 1:1 de Picasa {APP_VERSION}\n"
        "Exec=PyCasa %F\n"
        "Icon=PyCasa\n"
        "Terminal=false\n"
        "Categories=Graphics;Photography;Viewer;\n"
        "MimeType=image/jpeg;image/png;image/bmp;image/gif;image/tiff;image/webp;\n"
        "StartupWMClass=PyCasa\n"
    )
    desktop_path.write_text(desktop_content, encoding="utf-8")
    print(f"[OK] Generated Linux .desktop launcher / Lanceur .desktop Linux généré: {desktop_path}")
    return desktop_path


def verify_required_assets() -> List[str]:
    """
    FR: Vérifie la présence des fichiers critiques avant la compilation PyInstaller.
    EN: Verifies that critical files exist prior to running the PyInstaller build.
    """
    missing: List[str] = []
    required_paths = [
        PROJECT_ROOT / "main.py",
        SPEC_PATH,
        ICO_PATH,
        PROJECT_ROOT / "ui" / "resources" / "plugins" / "red.cfg",
    ]
    for path in required_paths:
        if not path.exists():
            missing.append(str(path))
    return missing


def create_windows_distribution_zip(dist_dir: Path = DIST_DIR) -> Optional[Path]:
    """
    FR: Crée une archive ZIP de distribution Windows (`dist/PyCasa-<version>-Windows-x64.zip`)
        prête à être déployée, contenant :
        - `PyCasa/PyCasa.exe` (exécutable autonome avec icône Picasa 3, ressources, 41 langues, `red.cfg`, `Red.dll`, `red_bridge_x86.exe`)
        - `PyCasa/PyCasa.ico` (icône officielle Picasa 3 `group_icon_105.ico`)
        - `PyCasa/LISEZMOI.txt` (instructions de lancement et de compatibilité Picasa 3)
    EN: Creates a ready-to-deploy Windows distribution ZIP archive (`dist/PyCasa-<version>-Windows-x64.zip`)
        containing:
        - `PyCasa/PyCasa.exe` (standalone executable with Picasa 3 icon, resources, 41 languages, `red.cfg`, `Red.dll`, `red_bridge_x86.exe`)
        - `PyCasa/PyCasa.ico` (official Picasa 3 icon `group_icon_105.ico`)
        - `PyCasa/LISEZMOI.txt` (launch and Picasa 3 compatibility instructions)
    """
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from picasa_py.version import APP_NAME, APP_VERSION

    exe_path = dist_dir / "PyCasa.exe"
    if not exe_path.is_file():
        print(f"[WARN] PyCasa.exe not found at / PyCasa.exe introuvable dans: {exe_path}")
        return None

    zip_name = f"{APP_NAME}-{APP_VERSION}-Windows-x64.zip"
    zip_path = dist_dir / zip_name
    readme_text = (
        f"======================================================================\r\n"
        f"  {APP_NAME} {APP_VERSION} — Distribution Windows (64 bits)\r\n"
        f"======================================================================\r\n\r\n"
        f"AVERTISSEMENT / PRÉCAUTION D'USAGE (À VOS RISQUES ET PÉRILS) :\r\n"
        f"   Bien que PyCasa ait fait l'objet de nombreux tests de fidélité binaire\r\n"
        f"   avec picasa3.exe, ce logiciel est fourni « TEL QUEL » (AS IS), sans\r\n"
        f"   aucune garantie. Son utilisation se fait à vos risques et périls.\r\n"
        f"   Effectuez TOUJOURS une sauvegarde de vos photos, de vos fichiers\r\n"
        f"   `.picasa.ini` et du dossier `%LOCALAPPDATA%\\Google\\Picasa2\\db3`\r\n"
        f"   avant utilisation.\r\n\r\n"
        f"1. LANCEMENT :\r\n"
        f"   Double-cliquez sur `PyCasa.exe`. Aucune installation de Python\r\n"
        f"   ni de Picasa 3 n'est requise : toutes les ressources, les 41 langues,\r\n"
        f"   les filtres, le modèle neuronal `red.cfg` et le pont 32 bits\r\n"
        f"   `red_bridge_x86.exe` sont intégrés dans `PyCasa.exe`.\r\n\r\n"
        f"2. COMPATIBILITÉ 100 % AVEC PICASA 3 :\r\n"
        f"   - Base de données : `%LOCALAPPDATA%\\Google\\Picasa2\\db3`\r\n"
        f"   - Fichiers de dossier : `.picasa.ini` et `.picasaoriginals`\r\n"
        f"   - Contacts : `%LOCALAPPDATA%\\Google\\Picasa2\\contacts\\contacts.xml`\r\n"
        f"   Vous pouvez utiliser alternativement `picasa3.exe` et `PyCasa.exe`\r\n"
        f"   sur la même photothèque sans aucune perte ni ré-indexation.\r\n"
    )

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.write(exe_path, arcname=f"{APP_NAME}/PyCasa.exe")
        if ICO_PATH.is_file():
            zf.write(ICO_PATH, arcname=f"{APP_NAME}/PyCasa.ico")
        zf.writestr(f"{APP_NAME}/LISEZMOI.txt", readme_text.encode("utf-8"))

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Windows distribution archive created / Archive Windows créée: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def run_build(dry_run: bool = False, extra_args: Optional[List[str]] = None) -> int:
    """
    FR: Exécute les étapes de préparation des icônes puis lance PyInstaller sur pycasa.spec.
    EN: Runs the icon preparation steps and then invokes PyInstaller on pycasa.spec.
    """
    missing = verify_required_assets()
    if missing:
        print("[ERROR] Missing required build assets / Ressources requises manquantes:")
        for item in missing:
            print(f"  - {item}")
        return 1

    if sys.platform == "darwin":
        ensure_macos_icns()
    elif sys.platform.startswith("linux"):
        generate_linux_desktop_assets()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_PATH),
    ]
    if extra_args:
        cmd.extend(extra_args)

    print(f"[INFO] Platform / Plateforme: {sys.platform}")
    print(f"[INFO] Icon / Icône: {ICO_PATH}")
    print(f"[INFO] Command / Commande: {' '.join(cmd)}")

    if dry_run:
        print("[OK] Dry-run verification succeeded / Vérification à blanc réussie.")
        return 0

    if shutil.which("pyinstaller") is None:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print(
                "[ERROR] PyInstaller is not installed. Run: pip install pyinstaller\n"
                "[ERREUR] PyInstaller n'est pas installé. Exécutez : pip install pyinstaller"
            )
            return 2

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        return result.returncode

    if sys.platform.startswith("linux"):
        generate_linux_desktop_assets()
    elif sys.platform == "win32":
        create_windows_distribution_zip(DIST_DIR)

    print(f"[OK] Standalone executable built in / Exécutable autonome généré dans: {DIST_DIR}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """
    FR: Point d'entrée CLI pour la construction de l'exécutable autonome PyCasa.
    EN: CLI entry point for building the standalone PyCasa executable.
    """
    parser = argparse.ArgumentParser(
        description="Build standalone PyCasa executable with Picasa 3 icon (Windows / macOS / Linux)."
    )
    parser.add_argument(
        "--dry-run",
        "--check",
        action="store_true",
        dest="dry_run",
        help="Validate spec, icon, and bundled resources without running PyInstaller.",
    )
    args, unknown = parser.parse_known_args(argv)
    return run_build(dry_run=args.dry_run, extra_args=unknown)


if __name__ == "__main__":
    raise SystemExit(main())
