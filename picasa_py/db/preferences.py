"""
FR: Gestionnaire des préférences de Picasa 3 (Software\\Google\\Picasa\\Picasa2\\Preferences).
Centralise la lecture et l'écriture des préférences d'interface et d'application
pour isoler la couche UI conformément à AGENTS.md §4 bis.3.

EN: Picasa 3 preferences manager (Software\\Google\\Picasa\\Picasa2\\Preferences).
Centralizes reading and writing of UI and application preferences
to isolate the UI layer in accordance with AGENTS.md §4 bis.3.

Ref: picasa3.exe @ 0x004060B0 (Local::lang), 0x008b1bf0 (Preferences registry & repository.dat)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any, Optional
from PySide6.QtCore import QSettings


class PicasaPreferences:
    """
    FR: Accès centralisé aux préférences Picasa 3 (HKEY_CURRENT_USER\\Software\\Google\\Picasa\\Picasa2\\Preferences).
    EN: Centralized access to Picasa 3 preferences (HKEY_CURRENT_USER\\Software\\Google\\Picasa\\Picasa2\\Preferences).
    Ref: picasa3.exe @ Software\\Google\\Picasa\\Picasa2\\Preferences
    """

    REGISTRY_ORG = "Google"
    REGISTRY_APP = r"Picasa\Picasa2\Preferences"

    def __init__(self, db3_dir: str | Path | None = None) -> None:
        """
        FR: Initialise l'accès aux préférences persistantes multi-plateformes via QSettings
        et optionnellement au fichier `repository.dat` d'un dossier `db3_dir`.
        EN: Initializes cross-platform persistent preferences access via QSettings
        and optionally to the `repository.dat` file of a `db3_dir` directory.
        """
        from picasa_py.db.kvtable import KeyValueTableFile

        self._settings = QSettings(self.REGISTRY_ORG, self.REGISTRY_APP)
        self.db3_dir: Optional[Path] = None
        self.repository: KeyValueTableFile = KeyValueTableFile()
        if db3_dir is not None:
            p = Path(db3_dir)
            if p.name.lower() == "repository.dat":
                self.db3_dir = p.parent
                repo_file = p
            else:
                self.db3_dir = p
                repo_file = p / "repository.dat"
            if repo_file.exists():
                try:
                    self.repository = KeyValueTableFile.from_bytes(repo_file.read_bytes())
                except Exception:
                    self.repository = KeyValueTableFile()

    @property
    def watched_folders(self) -> list[str]:
        """
        FR: Retourne la liste des dossiers surveillés normalisés (séparateur `\\` avec `\\` final) depuis `repository.dat`.
        EN: Returns the list of normalized watched folders (`\\` separator with trailing `\\`) from `repository.dat`.
        Ref: picasa3.exe @ 0x008B7F90 (foldermgr/watched_folders, repository.dat)
        """
        res: list[str] = []
        for k, v in self.repository.pairs:
            if (":" in k or "\\" in k or "/" in k) and v in ("1", "2"):
                norm = k.replace("/", "\\").rstrip("\\") + "\\"
                if norm not in res:
                    res.append(norm)
        return res

    @watched_folders.setter
    def watched_folders(self, folders: list[str] | dict[str, str]) -> None:
        """
        FR: Définit les dossiers surveillés dans `repository.dat` en normalisant les séparateurs Windows (`\\` final).
        EN: Sets the watched folders in `repository.dat`, normalizing Windows separators (trailing `\\`).
        Ref: picasa3.exe @ 0x008B7F90 (foldermgr/watched_folders, repository.dat)
        """
        existing_non_folders = [
            (k, v)
            for k, v in self.repository.pairs
            if not ((":" in k or "\\" in k or "/" in k) and v in ("0", "1", "2"))
        ]
        self.repository.pairs = list(existing_non_folders)
        if isinstance(folders, dict):
            for k, st in folders.items():
                norm = str(k).replace("/", "\\").rstrip("\\") + "\\"
                self.repository.set(norm, str(st))
        else:
            for k in folders:
                norm = str(k).replace("/", "\\").rstrip("\\") + "\\"
                self.repository.set(norm, "1")

    def save(self, target: str | Path | None = None) -> bool:
        """
        FR: Sauvegarde `repository.dat` au format binaire `KeyValueTableFile` et synchronise `QSettings`.
        EN: Saves `repository.dat` in `KeyValueTableFile` binary format and synchronizes `QSettings`.
        Ref: picasa3.exe @ 0x008b1bf0 (repository.dat)
        """
        self.sync()
        dest = Path(target) if target is not None else self.db3_dir
        if dest is None:
            return False
        repo_file = dest if dest.name.lower() == "repository.dat" else (dest / "repository.dat")
        repo_file.parent.mkdir(parents=True, exist_ok=True)
        repo_file.write_bytes(self.repository.to_bytes())
        return True

    @classmethod
    def load(cls, source: str | Path) -> PicasaPreferences:
        """
        FR: Charge une instance `PicasaPreferences` depuis un dossier `db3` ou un fichier `repository.dat`.
        EN: Loads a `PicasaPreferences` instance from a `db3` directory or a `repository.dat` file.
        Ref: picasa3.exe @ 0x008b1bf0 (repository.dat)
        """
        return cls(db3_dir=source)

    def value(self, key: str, default: Any = None, type: Optional[type] = None) -> Any:
        """
        FR: Lit une valeur de préférence depuis le registre ou fichier de configuration système.
        EN: Reads a preference value from the system registry or configuration file.
        """
        if type is not None:
            return self._settings.value(key, default, type=type)
        return self._settings.value(key, default)

    def setValue(self, key: str, val: Any) -> None:
        """
        FR: Définit une valeur de préférence dans le registre ou fichier de configuration système.
        EN: Sets a preference value in the system registry or configuration file.
        """
        self._settings.setValue(key, val)

    def sync(self) -> None:
        """
        FR: Force la synchronisation des préférences sur le disque ou dans le registre.
        EN: Forces synchronization of preferences to disk or registry.
        """
        self._settings.sync()

    @staticmethod
    def _resolve_repo_config_dir() -> Optional[Path]:
        """
        FR: Résout le répertoire contenant le fichier pointeur repository.dat selon l'OS hôte.
        EN: Resolves the directory containing the repository.dat pointer file according to the host OS.
        """
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            return Path(local_appdata) / "Google" / "Picasa2"
        if sys.platform == "win32":
            return None
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Google" / "Picasa3"
        xdg_data = os.environ.get("XDG_DATA_HOME", "")
        share_root = Path(xdg_data) if xdg_data else (Path.home() / ".local" / "share")
        return share_root / "Google" / "Picasa3"

    @staticmethod
    def get_repository_path() -> Optional[str]:
        """
        FR: Lit l'emplacement personnalisé de la base de données dans repository.dat s'il existe.
        Utilise le format binaire `KeyValueTableFile` (magic `0x3FCCCCCD`) avec repli texte.
        EN: Reads the custom database location from repository.dat if it exists.
        Uses the binary `KeyValueTableFile` format (magic `0x3FCCCCCD`) with plain-text fallback.
        Ref: picasa3.exe @ 0x0041415A, 0x008b1bf0 (repository.dat)
        """
        from picasa_py.db.kvtable import KeyValueTableFile

        repo_dir = PicasaPreferences._resolve_repo_config_dir()
        if repo_dir is None:
            return None
        repo_file = repo_dir / "repository.dat"
        if repo_file.exists():
            try:
                raw = repo_file.read_bytes()
                try:
                    kv = KeyValueTableFile.from_bytes(raw)
                    for key_candidate in ("RepositoryPath", "Path", "repository", "path"):
                        val = kv.get(key_candidate)
                        if val and val.strip():
                            return val.strip()
                    if len(kv.pairs) == 1 and kv.pairs[0][1].strip():
                        return kv.pairs[0][1].strip()
                    return None
                except ValueError:
                    if b"\x00" not in raw:
                        content = raw.decode("utf-8", errors="ignore").strip()
                        if content:
                            return content
            except Exception:
                pass
        return None

    @staticmethod
    def set_repository_path(target_dir: str) -> bool:
        """
        FR: Enregistre le nouvel emplacement de la base de données dans repository.dat au format binaire `KeyValueTableFile`.
        EN: Saves the new custom database location into repository.dat using the binary `KeyValueTableFile` format.
        Ref: picasa3.exe @ 0x0041415A, 0x008b1bf0 (repository.dat)
        """
        from picasa_py.db.kvtable import KeyValueTableFile

        repo_dir = PicasaPreferences._resolve_repo_config_dir()
        if repo_dir is None:
            return False
        try:
            repo_dir.mkdir(parents=True, exist_ok=True)
            repo_file = repo_dir / "repository.dat"
            kv = KeyValueTableFile()
            if repo_file.exists():
                try:
                    kv = KeyValueTableFile.from_bytes(repo_file.read_bytes())
                except Exception:
                    kv = KeyValueTableFile()
            kv.set("RepositoryPath", target_dir.strip())
            repo_file.write_bytes(kv.to_bytes())
            return True
        except Exception:
            return False

    @classmethod
    def get_theme_id(cls) -> str:
        """
        FR: Retourne l'identifiant du thème de couleur actif (par défaut 'original').
        EN: Returns the active color theme identifier (defaults to 'original').
        """
        try:
            prefs = cls()
            val = prefs.value("UITheme", "original", type=str)
            return str(val).strip() if val else "original"
        except Exception:
            return "original"

    @classmethod
    def set_theme_id(cls, theme_id: str) -> None:
        """
        FR: Enregistre l'identifiant du thème de couleur actif.
        EN: Saves the active color theme identifier.
        """
        try:
            prefs = cls()
            prefs.setValue("UITheme", (theme_id or "original").strip())
            prefs.sync()
        except Exception:
            pass

    @classmethod
    def get_face_engine(cls) -> str:
        """
        FR: Retourne le moteur de détection/reconnaissance faciale sélectionné :
        - 'native' (défaut) : exécution native 32 bits de plugins\\Red.dll + plugins\\red.cfg
        - 'python' : exécution Python/NumPy pure du code désassemblé de Red.dll + plugins\\red.cfg
        EN: Returns the selected face detection/recognition engine:
        - 'native' (default): 32-bit native execution of plugins\\Red.dll + plugins\\red.cfg
        - 'python': pure Python/NumPy execution of disassembled Red.dll + plugins\\red.cfg
        """
        try:
            prefs = cls()
            val = str(prefs.value("Faces/Engine", "native", type=str) or "native").strip().lower()
            return "python" if val == "python" else "native"
        except Exception:
            return "native"

    @classmethod
    def set_face_engine(cls, engine: str) -> None:
        """
        FR: Enregistre le moteur de détection/reconnaissance faciale ('native' ou 'python').
        EN: Saves the face detection/recognition engine ('native' or 'python').
        """
        try:
            norm = "python" if str(engine or "").strip().lower() == "python" else "native"
            prefs = cls()
            prefs.setValue("Faces/Engine", norm)
            prefs.sync()
        except Exception:
            pass
