"""
FR: Gestionnaire de vérification et d'installation des mises à jour de PyCasa depuis GitHub Releases
pour Windows (`PyCasa.exe`), macOS (`PyCasa-macOS.zip` / `PyCasa.app`) et Linux (`PyCasa-Linux-x64.tar.gz` / `PyCasa`).
EN: PyCasa GitHub Releases update checker and self-updater for Windows (`PyCasa.exe`),
macOS (`PyCasa-macOS.zip` / `PyCasa.app`), and Linux (`PyCasa-Linux-x64.tar.gz` / `PyCasa`).

Ref: picasa3.exe @ 0x0088C3EC (ID_HELP_CHECKFORUPDATES / options.fen item22..item24)
Ref: ui/resources/xml/OPTIONS_FR.XML (options/labelgroup20.title, item22.title, item23.title, item24.title)
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

from picasa_py.version import APP_NAME, APP_VERSION

GITHUB_REPO = "thyphoonfr/pycasa"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_HTML_URL = f"https://github.com/{GITHUB_REPO}/releases"


def parse_version_tuple(version_str: str) -> Tuple[int, ...]:
    """
    FR: Convertit une chaîne de version (ex. 'v3.9.174.423' ou '3.9.174.423') en tuple d'entiers `(3, 9, 174, 423)`.
    EN: Parses a version string (e.g. 'v3.9.174.423' or '3.9.174.423') into an integer tuple `(3, 9, 174, 423)`.
    """
    cleaned = (version_str or "").strip().lstrip("vV")
    parts: List[int] = []
    for token in cleaned.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            parts.append(int(digits))
        else:
            parts.append(0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def is_newer_version(remote_version: str, local_version: str = APP_VERSION) -> bool:
    """
    FR: Retourne True si `remote_version` est strictement plus récente que `local_version`.
    EN: Returns True if `remote_version` is strictly newer than `local_version`.
    """
    return parse_version_tuple(remote_version) > parse_version_tuple(local_version)


def select_asset_for_platform(
    assets: List[Dict[str, Any]],
    platform_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    FR: Sélectionne l'asset de la Release GitHub correspondant au système d'exploitation courant :
        - Windows (`win32`) : `PyCasa.exe` (prioritaire) ou `PyCasa-*-Windows-x64.zip`
        - macOS (`darwin`)  : `PyCasa-macOS.zip`
        - Linux (`linux*`)  : `PyCasa-Linux-x64.tar.gz` (prioritaire) ou `PyCasa`
    EN: Selects the GitHub Release asset matching the current operating system:
        - Windows (`win32`) : `PyCasa.exe` (preferred) or `PyCasa-*-Windows-x64.zip`
        - macOS (`darwin`)  : `PyCasa-macOS.zip`
        - Linux (`linux*`)  : `PyCasa-Linux-x64.tar.gz` (preferred) or `PyCasa`
    """
    plat = (platform_name or sys.platform).lower()
    if not assets:
        return None

    if plat == "win32":
        for a in assets:
            if str(a.get("name", "")).lower() == "pycasa.exe":
                return a
        for a in assets:
            name_l = str(a.get("name", "")).lower()
            if "windows" in name_l and name_l.endswith(".zip"):
                return a
    elif plat == "darwin":
        for a in assets:
            name_l = str(a.get("name", "")).lower()
            if "macos" in name_l and name_l.endswith(".zip"):
                return a
    elif plat.startswith("linux"):
        for a in assets:
            name_l = str(a.get("name", "")).lower()
            if "linux" in name_l and (name_l.endswith(".tar.gz") or name_l.endswith(".tgz")):
                return a
        for a in assets:
            if str(a.get("name", "")) == "PyCasa":
                return a

    return None


def fetch_latest_release_info(api_url: str = GITHUB_LATEST_RELEASE_API, timeout: float = 8.0) -> Dict[str, Any]:
    """
    FR: Interroge l'API GitHub Releases et retourne les métadonnées de la dernière release publiée.
    EN: Queries the GitHub Releases API and returns metadata for the latest published release.
    """
    req = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_NAME}/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)
    tag_name = str(data.get("tag_name") or data.get("name") or "").strip()
    remote_ver = tag_name.lstrip("vV")
    assets = data.get("assets") if isinstance(data.get("assets"), list) else []
    matched_asset = select_asset_for_platform(assets)
    return {
        "tag_name": tag_name,
        "version": remote_ver,
        "name": str(data.get("name") or tag_name),
        "body": str(data.get("body") or ""),
        "html_url": str(data.get("html_url") or GITHUB_RELEASES_HTML_URL),
        "assets": assets,
        "asset": matched_asset,
    }


class UpdateCheckWorker(QThread):
    """
    FR: Thread d'arrière-plan vérifiant sans bloquer l'interface si une nouvelle Release GitHub est disponible.
    EN: Non-blocking background thread checking whether a newer GitHub Release is available.
    """

    update_available = Signal(dict)
    up_to_date = Signal(str)
    check_failed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None, local_version: str = APP_VERSION):
        super().__init__(parent)
        self.local_version = local_version

    def run(self) -> None:
        try:
            info = fetch_latest_release_info()
            remote_ver = info.get("version", "")
            if remote_ver and is_newer_version(remote_ver, self.local_version):
                self.update_available.emit(info)
            else:
                self.up_to_date.emit(remote_ver or self.local_version)
        except Exception as exc:
            self.check_failed.emit(str(exc))


class UpdateDownloadWorker(QThread):
    """
    FR: Thread de téléchargement de l'exécutable ou de l'archive de mise à jour depuis GitHub Releases.
    EN: Background thread downloading the executable or update archive from GitHub Releases.
    """

    progress = Signal(int, int)
    download_finished = Signal(str)
    download_failed = Signal(str)

    def __init__(self, download_url: str, dest_path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.download_url = download_url
        self.dest_path = dest_path
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                downloaded = 0
                chunk_size = 64 * 1024
                os.makedirs(os.path.dirname(os.path.abspath(self.dest_path)), exist_ok=True)
                with open(self.dest_path, "wb") as out_f:
                    while True:
                        if self._cancelled:
                            break
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)
            if self._cancelled:
                try:
                    if os.path.exists(self.dest_path):
                        os.remove(self.dest_path)
                except Exception:
                    pass
                return
            self.download_finished.emit(self.dest_path)
        except Exception as exc:
            try:
                if os.path.exists(self.dest_path):
                    os.remove(self.dest_path)
            except Exception:
                pass
            self.download_failed.emit(str(exc))


def apply_downloaded_update(
    downloaded_file: str,
    target_executable: Optional[str] = None,
    platform_name: Optional[str] = None,
    relaunch: bool = True,
) -> Tuple[bool, str]:
    """
    FR: Applique la mise à jour téléchargée pour l'exécutable autonome sur Windows, macOS ou Linux :
        - Windows (`win32`) : extrait `PyCasa.exe` si archive `.zip`, écrit `<target>.new`, génère et lance
          un script `.cmd` détaché qui remplace `PyCasa.exe` après fermeture du processus et le relance.
        - Linux (`linux*`)  : extrait `PyCasa` depuis `PyCasa-Linux-x64.tar.gz`, applique `chmod 0755`,
          remplace atomiquement l'exécutable (`os.replace`) et relance la nouvelle version.
        - macOS (`darwin`)  : extrait `PyCasa.app` depuis `PyCasa-macOS.zip`, génère et lance un script `.sh`
          détaché qui remplace le bundle `PyCasa.app` et exécute `open -n "PyCasa.app"`.
    EN: Applies the downloaded update for the standalone executable on Windows, macOS, or Linux.
    """
    plat = (platform_name or sys.platform).lower()
    exe_path = Path(target_executable or sys.executable).resolve()
    dl_path = Path(downloaded_file).resolve()

    if not dl_path.exists():
        return False, f"Fichier téléchargé introuvable : {dl_path}"

    # 1. WINDOWS (PyCasa.exe ou PyCasa-*-Windows-x64.zip)
    if plat == "win32":
        staged_exe = exe_path.with_name(f"{exe_path.name}.new")
        if dl_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(dl_path, "r") as zf:
                exe_members = [m for m in zf.namelist() if m.lower().endswith("pycasa.exe")]
                if not exe_members:
                    return False, "Aucun fichier PyCasa.exe trouvé dans l'archive ZIP."
                with zf.open(exe_members[0]) as src, open(staged_exe, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            try:
                dl_path.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            if dl_path != staged_exe:
                shutil.move(str(dl_path), str(staged_exe))

        cmd_script = Path(tempfile.gettempdir()) / f"pycasa_update_{os.getpid()}.cmd"
        relaunch_line = f'start "" "{exe_path}"\r\n' if relaunch else ""
        script_content = (
            "@echo off\r\n"
            "setlocal\r\n"
            "set RETRIES=0\r\n"
            ":waitloop\r\n"
            "ping 127.0.0.1 -n 2 > nul\r\n"
            f'move /Y "{staged_exe}" "{exe_path}" > nul 2>&1\r\n'
            "if errorlevel 1 (\r\n"
            "    set /A RETRIES+=1\r\n"
            "    if %RETRIES% LSS 15 goto waitloop\r\n"
            "    exit /b 1\r\n"
            ")\r\n"
            f"{relaunch_line}"
            'del "%~f0"\r\n'
        )
        cmd_script.write_text(script_content, encoding="utf-8")
        if relaunch:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            subprocess.Popen(
                ["cmd.exe", "/c", str(cmd_script)],
                creationflags=creationflags,
                close_fds=True,
            )
        return True, str(staged_exe)

    # 2. LINUX (PyCasa-Linux-x64.tar.gz ou binaire PyCasa)
    if plat.startswith("linux"):
        staged_bin = exe_path.with_name(f"{exe_path.name}.new")
        name_l = dl_path.name.lower()
        if name_l.endswith(".tar.gz") or name_l.endswith(".tgz"):
            with tarfile.open(dl_path, "r:gz") as tf:
                bin_member = None
                for m in tf.getmembers():
                    if m.isfile() and os.path.basename(m.name) == "PyCasa":
                        bin_member = m
                        break
                if bin_member is None:
                    return False, "Aucun binaire PyCasa trouvé dans l'archive .tar.gz."
                extracted = tf.extractfile(bin_member)
                if extracted is None:
                    return False, "Impossible d'extraire le binaire PyCasa."
                with extracted, open(staged_bin, "wb") as dst:
                    shutil.copyfileobj(extracted, dst)
                # Extraire aussi PyCasa.png et PyCasa.desktop à côté si présents
                for m in tf.getmembers():
                    base_m = os.path.basename(m.name)
                    if m.isfile() and base_m in ("PyCasa.png", "PyCasa.desktop"):
                        ext_asset = tf.extractfile(m)
                        if ext_asset is not None:
                            with ext_asset, open(exe_path.parent / base_m, "wb") as adst:
                                shutil.copyfileobj(ext_asset, adst)
            try:
                dl_path.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            if dl_path != staged_bin:
                shutil.move(str(dl_path), str(staged_bin))

        os.chmod(staged_bin, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        os.replace(str(staged_bin), str(exe_path))
        if relaunch:
            subprocess.Popen([str(exe_path)], close_fds=True)
        return True, str(exe_path)

    # 3. MACOS (PyCasa-macOS.zip contenant PyCasa.app)
    if plat == "darwin":
        staging_dir = Path(tempfile.mkdtemp(prefix="pycasa_macos_update_"))
        if sys.platform == "darwin" and shutil.which("ditto"):
            subprocess.run(["ditto", "-x", "-k", str(dl_path), str(staging_dir)], check=True)
        else:
            with zipfile.ZipFile(dl_path, "r") as zf:
                zf.extractall(staging_dir)

        new_app = staging_dir / "PyCasa.app"
        if not new_app.exists():
            candidates = list(staging_dir.rglob("*.app"))
            if not candidates:
                return False, "Aucun bundle PyCasa.app trouvé dans l'archive macOS."
            new_app = candidates[0]

        # Localiser le bundle .app en cours d'exécution (ex: /Applications/PyCasa.app/Contents/MacOS/PyCasa)
        target_app: Optional[Path] = None
        for parent in [exe_path] + list(exe_path.parents):
            if parent.name.lower().endswith(".app"):
                target_app = parent
                break
        if target_app is None:
            target_app = exe_path.parent / "PyCasa.app"

        # Assurer les permissions d'exécution sur Contents/MacOS/PyCasa
        macos_bin = new_app / "Contents" / "MacOS" / "PyCasa"
        if macos_bin.exists():
            os.chmod(macos_bin, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        sh_script = staging_dir / "apply_macos_update.sh"
        relaunch_cmd = f'open -n "{target_app}"\n' if relaunch else ""
        sh_content = (
            "#!/bin/sh\n"
            "sleep 1\n"
            f'rm -rf "{target_app}"\n'
            f'mv "{new_app}" "{target_app}"\n'
            f"{relaunch_cmd}"
            f'rm -rf "{staging_dir}"\n'
        )
        sh_script.write_text(sh_content, encoding="utf-8")
        os.chmod(sh_script, stat.S_IRWXU)
        try:
            dl_path.unlink(missing_ok=True)
        except Exception:
            pass
        if relaunch:
            subprocess.Popen(["/bin/sh", str(sh_script)], close_fds=True)
        return True, str(target_app)

    return False, f"Plateforme non prise en charge pour la mise à jour automatique : {plat}"


class PicasaUpdateController:
    """
    FR: Contrôleur d'interface gérant la vérification, la boîte de dialogue de confirmation,
        la barre de progression de téléchargement et l'application de la mise à jour.
    EN: UI controller managing update checks, confirmation dialogs, download progress,
        and applying the update.
    """

    def __init__(self, parent_window: QWidget):
        self.parent_window = parent_window
        self._check_worker: Optional[UpdateCheckWorker] = None
        self._download_worker: Optional[UpdateDownloadWorker] = None

    def check_for_updates(self, manual: bool = True) -> None:
        """
        FR: Lance une vérification des mises à jour en arrière-plan.
            Si `manual=False`, respecte le réglage `Updates/Mode` des Options de Picasa 3 :
            - 0 : Mettre à jour automatiquement
            - 1 : Demander confirmation avant le téléchargement des mises à jour
            - 2 : Ne pas rechercher les mises à jour
        EN: Starts a background update check, respecting `Updates/Mode` when `manual=False`.
        """
        from picasa_py.db.preferences import PicasaPreferences

        prefs = PicasaPreferences()
        update_mode = int(prefs.value("Updates/Mode", 0, type=int) or 0)
        if not manual and update_mode == 2:
            return

        if self._check_worker is not None and self._check_worker.isRunning():
            return

        self._check_worker = UpdateCheckWorker(self.parent_window)
        self._check_worker.update_available.connect(
            lambda info: self._on_update_available(info, manual=manual, update_mode=update_mode)
        )
        self._check_worker.up_to_date.connect(
            lambda ver: self._on_up_to_date(ver, manual=manual)
        )
        self._check_worker.check_failed.connect(
            lambda err: self._on_check_failed(err, manual=manual)
        )
        self._check_worker.start()

    def _on_up_to_date(self, remote_ver: str, manual: bool) -> None:
        if manual:
            QMessageBox.information(
                self.parent_window,
                f"Mises à jour {APP_NAME}",
                f"Vous utilisez déjà la dernière version disponible ({APP_NAME} {APP_VERSION}).",
            )

    def _on_check_failed(self, err_msg: str, manual: bool) -> None:
        if manual:
            QMessageBox.warning(
                self.parent_window,
                f"Mises à jour {APP_NAME}",
                f"Impossible de vérifier les mises à jour sur GitHub :\n{err_msg}",
            )

    def _on_update_available(self, info: Dict[str, Any], manual: bool, update_mode: int) -> None:
        remote_ver = info.get("version") or info.get("tag_name") or ""
        html_url = info.get("html_url") or GITHUB_RELEASES_HTML_URL
        asset = info.get("asset")
        is_frozen = bool(getattr(sys, "frozen", False))

        # Si mode automatique (0) au démarrage et exécutable autonome disponible : lancer directement
        if not manual and update_mode == 0 and is_frozen and asset and asset.get("browser_download_url"):
            self._start_download_and_install(asset, remote_ver)
            return

        if is_frozen and asset and asset.get("browser_download_url"):
            msg = (
                f"<b>Une nouvelle version de {APP_NAME} est disponible !</b><br><br>"
                f"• Version actuelle : <b>{APP_VERSION}</b><br>"
                f"• Nouvelle version : <b>{remote_ver}</b><br><br>"
                f"Voulez-vous télécharger et installer automatiquement cette mise à jour maintenant ?"
            )
            ans = QMessageBox.question(
                self.parent_window,
                f"Mise à jour {APP_NAME} disponible",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if ans == QMessageBox.StandardButton.Yes:
                self._start_download_and_install(asset, remote_ver)
        else:
            msg = (
                f"<b>Une nouvelle version de {APP_NAME} est disponible sur GitHub !</b><br><br>"
                f"• Version actuelle : <b>{APP_VERSION}</b><br>"
                f"• Nouvelle version : <b>{remote_ver}</b><br><br>"
                f"Voulez-vous ouvrir la page de téléchargement de la Release GitHub ?"
            )
            ans = QMessageBox.question(
                self.parent_window,
                f"Mise à jour {APP_NAME} disponible",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if ans == QMessageBox.StandardButton.Yes:
                webbrowser.open(html_url)

    def _start_download_and_install(self, asset: Dict[str, Any], remote_ver: str) -> None:
        download_url = str(asset.get("browser_download_url") or "")
        asset_name = str(asset.get("name") or f"PyCasa-{remote_ver}")
        if not download_url:
            return

        exe_dir = Path(sys.executable).resolve().parent
        dest_dir = exe_dir if os.access(str(exe_dir), os.W_OK) else Path(tempfile.gettempdir())
        dest_file = dest_dir / f"{asset_name}.download"

        prog = QProgressDialog(
            f"Téléchargement de {APP_NAME} {remote_ver} ({asset_name})...",
            "Annuler",
            0,
            100,
            self.parent_window,
        )
        prog.setWindowTitle(f"Mise à jour {APP_NAME}")
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)

        worker = UpdateDownloadWorker(download_url, str(dest_file), self.parent_window)
        self._download_worker = worker

        def _on_prog(received: int, total: int) -> None:
            if total > 0:
                pct = min(99, int((received * 100) / total))
                prog.setValue(pct)
                mb_done = received / (1024 * 1024)
                mb_tot = total / (1024 * 1024)
                prog.setLabelText(
                    f"Téléchargement de {APP_NAME} {remote_ver} ({mb_done:.1f} / {mb_tot:.1f} Mo)..."
                )

        def _on_done(downloaded_path: str) -> None:
            prog.setValue(100)
            prog.close()
            ok, detail = apply_downloaded_update(downloaded_path, relaunch=True)
            if ok:
                QMessageBox.information(
                    self.parent_window,
                    f"Mise à jour {APP_NAME}",
                    f"La mise à jour vers {APP_NAME} {remote_ver} est prête.\n"
                    f"L'application va maintenant redémarrer sur la nouvelle version.",
                )
                app = QApplication.instance()
                if app is not None:
                    app.quit()
            else:
                QMessageBox.critical(
                    self.parent_window,
                    f"Erreur de mise à jour {APP_NAME}",
                    f"Impossible d'appliquer la mise à jour :\n{detail}",
                )

        def _on_err(err_msg: str) -> None:
            prog.close()
            QMessageBox.critical(
                self.parent_window,
                f"Erreur de téléchargement {APP_NAME}",
                f"Le téléchargement de la mise à jour a échoué :\n{err_msg}",
            )

        prog.canceled.connect(worker.cancel)
        worker.progress.connect(_on_prog)
        worker.download_finished.connect(_on_done)
        worker.download_failed.connect(_on_err)
        worker.start()
