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
        FR: Lit l'emplacement personnalisé de la racine de base de données Picasa 3 :
        1. En priorité via la clé de préférence `AppLocalDataPath` dans
           `HKCU\\Software\\Google\\Picasa\\Picasa2\\Preferences` (exactement comme `picasa3.exe`
           à `0x004073A5`, `0x0097E366` et `CFilePath::Resolve` à `0x00980EC0`).
        2. En repli de rétrocompatibilité (lecture seule) depuis un éventuel ancien fichier
           `repository.dat` (`RepositoryPath`).
        EN: Reads the custom Picasa 3 database root location:
        1. Primarily via the `AppLocalDataPath` preference key in
           `HKCU\\Software\\Google\\Picasa\\Picasa2\\Preferences` (matching `picasa3.exe`
           at `0x004073A5`, `0x0097E366`, and `CFilePath::Resolve` at `0x00980EC0`).
        2. Read-only backward compatibility fallback to any legacy `repository.dat` (`RepositoryPath`).
        Ref: picasa3.exe @ 0x00407385..0x004073AD, 0x0097E366 (AppLocalDataPath), 0x00980EC0 (CFilePath::Resolve)
        """
        try:
            prefs = PicasaPreferences()
            app_local_data = prefs.value("AppLocalDataPath", "", type=str)
            if app_local_data and str(app_local_data).strip():
                raw_val = str(app_local_data).strip()
                p_val = Path(raw_val.rstrip("\\/"))
                # Ref: picasa3.exe @ 0x0098104F..0x009810B4 (CFilePath::Resolve) :
                # picasa3.exe exécute _splitpath(AppLocalDataPath) puis AppendDir("Google\\Picasa2").
                # - Si AppLocalDataPath se termine par '\\' (ex. "C:\\Users\\...\\AppData\\Local\\"),
                #   picasa3.exe résout "<AppLocalDataPath>Google\\Picasa2".
                # - Si une ancienne valeur pointait sur "<base>\\Google\\Picasa2" sans '\\' final,
                #   on la corrige dans le registre en "<base>\\" pour que picasa3.exe ouvre la même base.
                if p_val.name.lower() == "picasa2" and p_val.parent.name.lower() == "google":
                    base_with_slash = str(p_val.parent.parent).rstrip("\\/") + "\\"
                    if raw_val != base_with_slash:
                        try:
                            prefs.setValue("AppLocalDataPath", base_with_slash)
                            prefs.sync()
                        except Exception:
                            pass
                    return str(p_val)
                if raw_val.endswith(("\\", "/")) or (p_val / "Google" / "Picasa2").exists():
                    cand = p_val / "Google" / "Picasa2"
                    if cand.exists() or not (p_val / "db3").exists():
                        return str(cand)
                return raw_val
        except Exception:
            pass

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
                    for key_candidate in ("RepositoryPath", "AppLocalDataPath", "Path", "repository", "path"):
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
        FR: Enregistre le nouvel emplacement racine de la base de données dans la clé `AppLocalDataPath`
        de `HKCU\\Software\\Google\\Picasa\\Picasa2\\Preferences` (comme `picasa3.exe` à `0x004073A5` et `0x0097E366`).
        Si `target_dir` pointe sur le sous-dossier `db3`, normalise vers son dossier racine parent (`<Picasa2_Root>`)
        afin que `#db3\\`, `#contacts\\`, `#tmp\\` et `ioqueue\\` soient résolus sous la même racine.
        Ne crée aucun fichier `repository.dat` à la racine `<Picasa2_Root>` (dans `picasa3.exe`, `repository.dat`
        existe uniquement dans `db3\\repository.dat`, Ref: `0x0041415A`).
        EN: Saves the new database root path into the `AppLocalDataPath` key of
        `HKCU\\Software\\Google\\Picasa\\Picasa2\\Preferences` (matching `picasa3.exe` at `0x004073A5` and `0x0097E366`).
        If `target_dir` points to the `db3` subfolder, normalizes to its parent root folder (`<Picasa2_Root>`)
        so `#db3\\`, `#contacts\\`, `#tmp\\`, and `ioqueue\\` resolve under the same root.
        Does not create a `repository.dat` file in `<Picasa2_Root>` (in `picasa3.exe`, `repository.dat`
        only exists at `db3\\repository.dat`, Ref: `0x0041415A`).
        Ref: picasa3.exe @ 0x00407385..0x004073AD, 0x0097E366 (AppLocalDataPath), 0x0041415A (db3\\repository.dat)
        """
        clean = (target_dir or "").strip()
        if not clean:
            return False
        try:
            p = Path(clean)
            if p.name.lower() == "db3":
                root_p = p.parent
            else:
                root_p = p
            # Ref: picasa3.exe @ 0x0098104F..0x009810B4 (CFilePath::Resolve) :
            # Lorsque la racine est "<base>\\Google\\Picasa2", AppLocalDataPath dans le registre
            # doit valoir "<base>\\" (avec '\\' final) afin que _splitpath + AppendDir("Google\\Picasa2")
            # de picasa3.exe résolve exactement "<base>\\Google\\Picasa2\\db3".
            if root_p.name.lower() == "picasa2" and root_p.parent.name.lower() == "google":
                reg_val = str(root_p.parent.parent).rstrip("\\/") + "\\"
            else:
                reg_val = str(root_p)
            prefs = PicasaPreferences()
            prefs.setValue("AppLocalDataPath", reg_val)
            prefs.sync()
            # Nettoyer un éventuel ancien fichier pointeur non-standard <Picasa2_Root>/repository.dat
            repo_dir = PicasaPreferences._resolve_repo_config_dir()
            if repo_dir is not None:
                legacy_ptr = repo_dir / "repository.dat"
                if legacy_ptr.exists():
                    try:
                        legacy_ptr.unlink()
                    except Exception:
                        pass
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

    @classmethod
    def get_people_sort_mode(cls) -> int:
        """
        FR: Retourne le mode de tri de la collection Personnes (`Preferences\\peoplesort`) :
        - 0 (défaut) : Trier les personnes par nom (`AlbumList::ID_PEOPLEBYNAME`, 0x9E18)
        - 1 : Trier les personnes par nombre (`AlbumList::ID_PEOPLEBYAMOUNT`, 0x9E19)
        - 2 : Trier en fonction des 10 premières personnes (`AlbumList::ID_PEOPLEBYAMOUNTTOP10`, 0x9E38)
        EN: Returns the People collection sort mode (`Preferences\\peoplesort`):
        - 0 (default): Sort People by Name (`AlbumList::ID_PEOPLEBYNAME`, 0x9E18)
        - 1: Sort People by Amount (`AlbumList::ID_PEOPLEBYAMOUNT`, 0x9E19)
        - 2: Sort People by Top 10 (`AlbumList::ID_PEOPLEBYAMOUNTTOP10`, 0x9E38)
        Ref: picasa3.exe @ 0x004A198C, 0x004A37E8, 0x004A7A18
        """
        try:
            prefs = cls()
            val = prefs.value("peoplesort", 0, type=int)
            mode = int(val) if val is not None else 0
            return mode if mode in (0, 1, 2) else 0
        except Exception:
            return 0

    @classmethod
    def set_people_sort_mode(cls, mode: int) -> None:
        """
        FR: Enregistre le mode de tri de la collection Personnes (`Preferences\\peoplesort` : 0, 1 ou 2).
        EN: Saves the People collection sort mode (`Preferences\\peoplesort`: 0, 1, or 2).
        Ref: picasa3.exe @ 0x004A37E8, 0x005D31B9 - 0x005D3205
        """
        try:
            norm = int(mode) if int(mode) in (0, 1, 2) else 0
            prefs = cls()
            prefs.setValue("peoplesort", norm)
            prefs.sync()
        except Exception:
            pass

    @classmethod
    def get_date_sort_mode(cls) -> int:
        """
        FR: Retourne le mode de tri des dossiers et albums (`Preferences\\datesort`) :
        - 0 (défaut) : Trier par date (`AlbumList::ID_SORTBYDATE`, 0x9C8B)
        - 1 : Trier par taille (`AlbumList::ID_SORTBYSIZE`, 0x9CBD)
        - 2 : Trier par nom (`AlbumList::ID_SORTBYNAME`, 0x9C8C)
        - 4 / 5 : Trier par modifications les plus récentes (`AlbumList::ID_SORTBYMOST_RECENT_PHOTO`, 0x9DC8)
        EN: Returns the Folders and Albums sort mode (`Preferences\\datesort`):
        - 0 (default): Sort by Date (`AlbumList::ID_SORTBYDATE`, 0x9C8B)
        - 1: Sort by Size (`AlbumList::ID_SORTBYSIZE`, 0x9CBD)
        - 2: Sort by Name (`AlbumList::ID_SORTBYNAME`, 0x9C8C)
        - 4 / 5: Sort by Most Recent Photo (`AlbumList::ID_SORTBYMOST_RECENT_PHOTO`, 0x9DC8)
        Ref: picasa3.exe @ 0x004A195F, 0x004A37AF, 0x004A7D7F, 0x005E20A1
        """
        try:
            prefs = cls()
            val = prefs.value("datesort", 0, type=int)
            mode = int(val) if val is not None else 0
            return mode if mode in (0, 1, 2, 4, 5) else 0
        except Exception:
            return 0

    @classmethod
    def set_date_sort_mode(cls, mode: int) -> None:
        """
        FR: Enregistre le mode de tri des dossiers et albums (`Preferences\\datesort` : 0, 1, 2, 4 ou 5).
        EN: Saves the Folders and Albums sort mode (`Preferences\\datesort`: 0, 1, 2, 4, or 5).
        Ref: picasa3.exe @ 0x004A37AF, 0x004B07C0, 0x005D30F0
        """
        try:
            norm = int(mode) if int(mode) in (0, 1, 2, 4, 5) else 0
            prefs = cls()
            prefs.setValue("datesort", norm)
            prefs.sync()
        except Exception:
            pass

    @classmethod
    def get_album_list_flip(cls) -> bool:
        """
        FR: Retourne l'état d'inversion de l'ordre de tri des dossiers et albums (`Preferences\\albumlistflip`, défaut False).
        EN: Returns the reverse sort flag for folders and albums (`Preferences\\albumlistflip`, default False).
        Ref: picasa3.exe @ 0x004A19B1, 0x004A383C, 0x004A7DF7, 0x005E211A
        """
        try:
            prefs = cls()
            val = prefs.value("albumlistflip", 0, type=int)
            return bool(int(val)) if val is not None else False
        except Exception:
            return False

    @classmethod
    def set_album_list_flip(cls, flip: bool) -> None:
        """
        FR: Enregistre l'état d'inversion de l'ordre de tri des dossiers et albums (`Preferences\\albumlistflip`).
        EN: Saves the reverse sort flag for folders and albums (`Preferences\\albumlistflip`).
        Ref: picasa3.exe @ 0x004A383C, 0x004B07C0
        """
        try:
            prefs = cls()
            prefs.setValue("albumlistflip", 1 if flip else 0)
            prefs.sync()
        except Exception:
            pass


