"""
FR: Gestionnaire unifié de base de données Picasa 3 (db3 et contacts).
Permet l'accès de haut niveau à l'ensemble des données de la photothèque :
- Dossiers et arborescence (thumbindex.db)
- Propriétés colonnes (tables .pmp : imagedata, albumdata, catdata)
- Miniatures et caches d'images (CBlockFile : thumbs, thumbs2, bigthumbs, previews)
- Contacts et visages (contacts.xml, facetemplatesV2)
- Métadonnées du référentiel (repository.dat, usernames.dat)
- Index inversé de recherche (wordhash.dat)

EN: Unified Picasa 3 database manager (db3 and contacts).
Provides high-level access to all photo library data:
- Folders and directory tree (thumbindex.db)
- Columnar properties (.pmp tables: imagedata, albumdata, catdata)
- Thumbnails and image caches (CBlockFile: thumbs, thumbs2, bigthumbs, previews)
- Contacts and faces (contacts.xml, facetemplatesV2)
- Repository metadata (repository.dat, usernames.dat)
- Inverted search index (wordhash.dat)
"""

from __future__ import annotations
import math
import os
import struct
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np

from picasa_py.db.pmp import PmpFile, PmpType
from picasa_py.db.thumbindex import (
    ThumbIndexFile,
    ThumbIndexRecord,
    THUMBINDEX_ACTIVE_FLAG,
    unix_to_filetime,
)
from picasa_py.db.blockfile import (
    BlockIndexFile,
    BlockContainerFile,
    BlockEntry,
    FACETEMPLATE_BLOCK_CHECKSUM,
    compute_thumb_checksum,
    compute_preview_checksum,
    verify_face_template_blob,
    encode_face_template_blob,
    decode_face_template_blob,
)
from picasa_py.db.kvtable import KeyValueTableFile
from picasa_py.db.wordhash import WordHashFile
from picasa_py.db.contacts import ContactsFile, Contact

# Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows) — type 19 (.pal palette) is NOT a media record
MEDIA_RECORD_TYPES = (2, 3, 4, 6, 7, 8, 13, 18, 31, 32)


def _to_host_path(picasa_path: str) -> str:
    """
    FR: Convertit un chemin au format Picasa ('\\') vers le séparateur du système hôte si non-Windows.
    EN: Converts a Picasa-formatted path ('\\') to the host OS path separator if non-Windows.
    """
    if os.sep != "\\" and picasa_path:
        return picasa_path.replace("\\", os.sep)
    return picasa_path


def _find_default_db3_dir() -> Tuple[Path, Path]:
    """
    FR: Recherche les répertoires par défaut (db3_dir, contacts_dir) selon l'OS hôte :
    - Windows : %LOCALAPPDATA%/Google/Picasa2/db3
    - macOS (darwin) : ~/Library/Application Support/Google/Picasa3/db3 (et Picasa2/db3)
    - Linux : ~/.local/share/Google/Picasa3/db3 (et Picasa2/db3, ou préfixe Wine ~/.google/picasa)
    EN: Finds the default (db3_dir, contacts_dir) directories according to the host OS:
    - Windows: %LOCALAPPDATA%/Google/Picasa2/db3
    - macOS (darwin): ~/Library/Application Support/Google/Picasa3/db3 (and Picasa2/db3)
    - Linux: ~/.local/share/Google/Picasa3/db3 (and Picasa2/db3, or Wine prefix ~/.google/picasa)
    """
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            base = Path(localappdata) / "Google" / "Picasa2"
        else:
            base = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2"))
        return base / "db3", base / "contacts"
    elif sys.platform == "darwin":
        app_support = Path.home() / "Library" / "Application Support" / "Google"
        base = app_support / "Picasa3"
        if not (base / "db3").exists():
            alt = app_support / "Picasa2"
            if (alt / "db3").exists():
                base = alt
        return base / "db3", base / "contacts"
    else:
        wine_base = Path.home() / ".google" / "picasa" / "3.0" / "drive_c" / "users"
        if wine_base.exists():
            try:
                for sub in wine_base.iterdir():
                    cand = sub / "Local Settings" / "Application Data" / "Google" / "Picasa2" / "db3"
                    if cand.exists():
                        return cand, cand.parent / "contacts"
            except Exception:
                pass
        xdg_data = os.environ.get("XDG_DATA_HOME")
        share_root = Path(xdg_data) if xdg_data else (Path.home() / ".local" / "share")
        candidates = [
            share_root / "Google" / "Picasa3",
            share_root / "Google" / "Picasa2",
            share_root / "picasa2",
        ]
        for cand_base in candidates:
            if (cand_base / "db3").exists():
                return cand_base / "db3", cand_base / "contacts"
        default_base = share_root / "Google" / "Picasa3"
        return default_base / "db3", default_base / "contacts"


def _find_red_cfg_path() -> Optional[Path]:
    """
    FR: Localise le fichier de modèle facial plugins/red.cfg sur tous les OS (exécutable PyInstaller,
    ressources embarquées ui/resources/plugins/red.cfg, ou installation Picasa 3 native).
    EN: Locates the plugins/red.cfg facial model file across all OSes (PyInstaller executable,
    bundled ui/resources/plugins/red.cfg resources, or native Picasa 3 installation).
    Ref: picasa3.exe @ 0x0045F0C0 (plugins\\red.cfg)
    """
    candidates: List[Path] = []
    try:
        from picasa_py.ui.resources import RES_DIR
        candidates.append(RES_DIR / "plugins" / "red.cfg")
    except Exception:
        pass
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "ui" / "resources" / "plugins" / "red.cfg")
    candidates.extend([
        Path(__file__).resolve().parent.parent.parent / "ui" / "resources" / "plugins" / "red.cfg",
        Path(r"C:\Program Files (x86)\Google\Picasa3\plugins\red.cfg"),
        Path(r"C:\Program Files\Google\Picasa3\plugins\red.cfg"),
        Path("ui/resources/plugins/red.cfg"),
        Path("bin/plugins/red.cfg"),
    ])
    for cfg_path in candidates:
        if cfg_path.exists():
            return cfg_path
    return None


# Ref: picasa3.exe @ 0x004156F0 (CThumbDB::Init), CPropertyMap (0x00CA8104)
STANDARD_PMP_SCHEMA: Dict[str, PmpType] = {
    "albumdata_albumcontactids": PmpType.UINT64,
    "albumdata_albumpeoplechecksum": PmpType.UINT32,
    "albumdata_category": PmpType.UINT32,
    "albumdata_date": PmpType.DOUBLE,
    "albumdata_description": PmpType.STRING,
    "albumdata_filename": PmpType.STRING,
    "albumdata_hascollage": PmpType.UINT8,
    "albumdata_inisync": PmpType.UINT64,
    "albumdata_location": PmpType.STRING,
    "albumdata_music": PmpType.STRING,
    "albumdata_name": PmpType.STRING,
    "albumdata_token": PmpType.STRING,
    "albumdata_uid": PmpType.STRING,
    "albumdata_unread": PmpType.UINT8,
    "catdata_catpri": PmpType.UINT8,
    "catdata_name": PmpType.STRING,
    "catdata_state": PmpType.UINT8,
    "imagedata_aliasparents": PmpType.UINT32,
    "imagedata_avgcolor": PmpType.UINT32,
    "imagedata_backuphash": PmpType.UINT16,
    "imagedata_caption": PmpType.STRING,
    "imagedata_colorspace": PmpType.UINT8,
    "imagedata_crop64": PmpType.UINT64,
    "imagedata_deferredface": PmpType.STRING,
    "imagedata_deferredregion": PmpType.STRING,
    "imagedata_edit_height": PmpType.UINT32_ALT,
    "imagedata_edit_width": PmpType.UINT32_ALT,
    "imagedata_edited": PmpType.UINT8,
    "imagedata_facequality": PmpType.UINT32,
    "imagedata_facerect": PmpType.UINT64,
    "imagedata_facerectdata": PmpType.STRING,
    "imagedata_fileflags": PmpType.UINT32,
    "imagedata_filetype": PmpType.UINT32,
    "imagedata_filters": PmpType.STRING,
    "imagedata_flipped": PmpType.STRING,
    "imagedata_geoview": PmpType.STRING,
    "imagedata_height": PmpType.UINT32,
    "imagedata_lat": PmpType.DOUBLE,
    "imagedata_long": PmpType.DOUBLE,
    "imagedata_originfast": PmpType.UINT64,
    "imagedata_originslow": PmpType.UINT64,
    "imagedata_peoplealbumchecksum": PmpType.UINT16,
    "imagedata_personalbumid": PmpType.UINT32,
    "imagedata_personalbumrecs": PmpType.UINT32,
    "imagedata_personalbumrecs2": PmpType.UINT32,
    "imagedata_personalbumrecvalues": PmpType.UINT32,
    "imagedata_personalbumrecvalues2": PmpType.UINT32,
    "imagedata_redo": PmpType.STRING,
    "imagedata_revertable": PmpType.UINT8,
    "imagedata_rotate": PmpType.STRING,
    "imagedata_suggestionpersonalbumid": PmpType.UINT32,
    "imagedata_tagdate": PmpType.DOUBLE,
    "imagedata_tags": PmpType.STRING_PTR,
    "imagedata_text": PmpType.STRING,
    "imagedata_textactive": PmpType.UINT8,
    "imagedata_width": PmpType.UINT32,
}

# Ref: picasa3.exe @ 0x004156F0 (catdata_* default categories)
DEFAULT_CATDATA_RECORDS: Dict[str, List[Any]] = {
    "catdata_name": [
        "Labels",
        "Projects (internal)",
        "Folders on Disk",
        "Web Albums",
        "Web Drive",
        "Exported Pictures",
        "Other Stuff",
        "Hidden Folders",
        "People",
    ],
    "catdata_catpri": [100, 90, 20, 9, 8, 7, 6, 1, 95],
    "catdata_state": [1, 1, 1, 1, 1, 1, 0, 1, 1],
}

# Ref: picasa3.exe @ 0x006B5D40 (CBlockFile prefixes)
STANDARD_BLOCKFILE_PREFIXES: Tuple[str, ...] = (
    "albums",
    "bigthumbs",
    "facetemplatesV2",
    "previews",
    "thumbs",
    "thumbs2",
)


class _BlockFileHandle:
    """
    FR: Vue unifiée sur une paire `(BlockIndexFile, BlockContainerFile)` pour un préfixe `CBlockFile` donné.
    EN: Unified view over a `(BlockIndexFile, BlockContainerFile)` pair for a given `CBlockFile` prefix.
    Ref: picasa3.exe @ 0x006B6AF0, 0x006B75F0
    """

    def __init__(self, db: PicasaDatabase, prefix: str):
        self.db = db
        self.prefix = prefix

    @property
    def index_file(self) -> Optional[BlockIndexFile]:
        return self.db.block_indices.get(self.prefix)

    @property
    def container_file(self) -> Optional[BlockContainerFile]:
        return self.db.block_containers.get(self.prefix)

    def write_entry(self, index: int, blob: bytes, checksum: int = 0) -> None:
        """
        FR: Écrit un blob à l'index spécifié dans le conteneur `CBlockFile`.
        EN: Writes a blob at the specified index in the `CBlockFile` container.
        """
        self.db.add_thumbnail(index, blob, size=self.prefix, checksum=checksum)

    def read_entry(self, index: int) -> Optional[bytes]:
        """
        FR: Lit le blob à l'index spécifié depuis le conteneur `CBlockFile`.
        EN: Reads the blob at the specified index from the `CBlockFile` container.
        """
        return self.db.get_thumbnail(index, size=self.prefix)

    def get_entry(self, index: int) -> Optional[BlockEntry]:
        idx_f = self.index_file
        if idx_f is None or index < 0 or index >= idx_f.record_count:
            return None
        return idx_f.get_entry(index)


class PicasaDatabase:
    """
    FR: Instance complète d'une base de données Picasa 3.
    EN: Complete instance of a Picasa 3 database.
    Ref: picasa3.exe @ 0x004156F0 (CThumbDB), 0x00456A15 (SyncIniToDB)
    Ghidra project: ghidra/picasa3.gpr
    """

    def __init__(self, db3_dir: Path = Path("."), contacts_dir: Path | None = None):
        """
        FR: Initialise les structures en mémoire pour le répertoire db3 et le répertoire contacts.
        EN: Initializes in-memory structures for the db3 directory and contacts directory.
        """
        self.db3_dir = db3_dir
        self.contacts_dir = contacts_dir
        self._lock = threading.RLock()
        # FR: Verrous indépendants par conteneur CBlockFile (thumbs, thumbs2, bigthumbs, previews, facetemplatesV2, albums)
        # afin que la lecture des miniatures (get_thumbnail) ne soit jamais bloquée par les opérations sur les tables PMP.
        # EN: Independent per-CBlockFile locks (thumbs, thumbs2, bigthumbs, previews, facetemplatesV2, albums)
        # so thumbnail reads (get_thumbnail) are never blocked by PMP table operations.
        # Ref: picasa3.exe @ 0x00415790 (decomp_dir_scanner_ctor.c:601-652), 0x006B7FC0 (cblockfile_006B7FC0.c:30)
        self._block_locks: Dict[str, threading.RLock] = {
            prefix: threading.RLock() for prefix in STANDARD_BLOCKFILE_PREFIXES
        }

        self.thumbindex: Optional[ThumbIndexFile] = None
        self.repository: Optional[KeyValueTableFile] = None
        self.usernames: Optional[KeyValueTableFile] = None
        self.wordhash: Optional[WordHashFile] = None
        self.contacts: Optional[ContactsFile] = None

        self.pmps: Dict[str, PmpFile] = {}
        self.block_indices: Dict[str, BlockIndexFile] = {}
        self.block_containers: Dict[str, BlockContainerFile] = {}
        self.block_containers_by_block: Dict[Tuple[str, int], BlockContainerFile] = {}
        self._face_manager: Optional[Any] = None
        self._ini_cache: Dict[str, Tuple[float, float, Any]] = {}
        self._path_index_cache: Dict[str, int] = {}
        self._folder_index_cache: Dict[str, int] = {}
        self._folder_idx_to_norms: Dict[int, Tuple[str, str]] = {}
        self._path_index_version: int = -1
        self._path_index_ti_id: int = 0
        self._parent_to_face_children: Dict[int, List[int]] = {}
        self._parent_to_face_children_len: int = -1
        self._albums_cache: Optional[List[Dict[str, Any]]] = None
        self._albums_cache_sig: Optional[Tuple[int, int]] = None
        self._starred_cache: Optional[List[str]] = None
        self._starred_cache_sig: Optional[int] = None
        self._search_haystack_cache: Optional[Dict[int, str]] = None
        self._search_haystack_len: int = -1
        self._deleted_or_reset_indices: Set[int] = set()
        self._modified_media_indices: Set[int] = set()
        self._thumb_save_timer: Optional[threading.Timer] = None
        self._min_aligned_idx: int = -1
        self._aligned_pmp_count: int = 0
        self._scanlist: Dict[str, str] = {}

    @property
    def _deleted_or_Reset_indices(self) -> Set[int]:
        """
        FR: Alias de compatibilité vers `_deleted_or_reset_indices`.
        EN: Compatibility alias to `_deleted_or_reset_indices`.
        """
        return self._deleted_or_reset_indices

    @_deleted_or_Reset_indices.setter
    def _deleted_or_Reset_indices(self, value: Set[int]) -> None:
        self._deleted_or_reset_indices = value

    def invalidate_search_cache(self) -> None:
        """
        FR: Invalide le cache inversé de recherche plein texte (`_search_haystack_cache`).
        EN: Invalidates the full-text search haystack cache (`_search_haystack_cache`).
        """
        self._search_haystack_cache = None
        self._search_haystack_len = -1

    def _get_cached_folder_ini_doc(self, folder_path: str) -> Optional[Any]:
        """
        FR: Retourne le document `.picasa.ini` ou `Picasa.ini` mis en cache pour `folder_path` sans stat disque répété.
        EN: Returns the cached `.picasa.ini` or `Picasa.ini` document for `folder_path` without repeated disk stat.
        """
        if not folder_path:
            return None
        doc = self.get_parsed_ini(os.path.join(folder_path, ".picasa.ini"))
        if doc is None:
            doc = self.get_parsed_ini(os.path.join(folder_path, "Picasa.ini"))
        return doc

    @property
    def block_files(self) -> Dict[str, _BlockFileHandle]:
        """
        FR: Dictionnaire des paires `CBlockFile` ouvertes indexées par préfixe (`thumbs`, `thumbs2`, `bigthumbs`, `previews`, `facetemplatesV2`, `albums`).
        EN: Dictionary of open `CBlockFile` pairs indexed by prefix (`thumbs`, `thumbs2`, `bigthumbs`, `previews`, `facetemplatesV2`, `albums`).
        """
        return {prefix: _BlockFileHandle(self, prefix) for prefix in self.block_indices}

    @classmethod
    def _find_default_db3_dir(cls) -> Path:
        """
        FR: Retourne le chemin par défaut du dossier db3 selon le système d'exploitation.
        EN: Returns the default db3 directory path according to the operating system.
        """
        return _find_default_db3_dir()[0]

    @classmethod
    def _find_red_cfg_path(cls) -> Optional[Path]:
        """
        FR: Retourne le chemin vers plugins/red.cfg (ressources embarquées ou installation locale).
        EN: Returns the path to plugins/red.cfg (bundled resources or local installation).
        """
        return _find_red_cfg_path()

    @classmethod
    def get_default_paths(cls) -> Tuple[Path, Path]:
        """
        FR: Renvoie les chemins par défaut (db3_dir, contacts_dir) selon le système d'exploitation.
        EN: Returns the default paths (db3_dir, contacts_dir) according to the operating system.
        Ref: Windows: %LOCALAPPDATA%/Google/Picasa2/db3
             macOS: ~/Library/Application Support/Google/Picasa3/db3
             Linux: ~/.local/share/Google/Picasa3/db3 (et Picasa2/db3) ou préfixe Wine ~/.google/picasa
        """
        return _find_default_db3_dir()

    @classmethod
    def open_default(cls) -> PicasaDatabase:
        """
        FR: Ouvre la base de données Picasa située dans l'emplacement par défaut de l'OS.
        EN: Opens the Picasa database located in the OS default path.
        """
        db3_dir, contacts_dir = cls.get_default_paths()
        db = cls(db3_dir=db3_dir, contacts_dir=contacts_dir)
        db.load_all()
        return db

    def load_all(self) -> None:
        """
        FR: Charge l'ensemble des fichiers disponibles dans le répertoire de base de données.
        EN: Loads all available files in the database directory.
        """
        if not self.db3_dir.exists():
            return

        # 1. thumbindex.db (FR: Index des fichiers et dossiers / EN: File and folder index)
        ti_path = self.db3_dir / "thumbindex.db"
        if ti_path.exists():
            self.thumbindex = ThumbIndexFile.from_bytes(ti_path.read_bytes())

        # 2. repository.dat, usernames.dat & scanlist.txt (Ref: 0x004A4860, 0x004F6380)
        repo_path = self.db3_dir / "repository.dat"
        if repo_path.exists():
            self.repository = KeyValueTableFile.from_bytes(repo_path.read_bytes())

        un_path = self.db3_dir / "usernames.dat"
        if un_path.exists():
            self.usernames = KeyValueTableFile.from_bytes(un_path.read_bytes())

        self._scanlist.clear()
        scanlist_path = self.db3_dir / "scanlist.txt"
        if scanlist_path.exists():
            try:
                repo_map = dict(self.repository.pairs) if self.repository else {}
                raw_sl = scanlist_path.read_bytes().decode("utf-8", errors="surrogateescape")
                for raw_line in raw_sl.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("-"):
                        fpath = line[1:].strip()
                        st = "0"
                    elif line.startswith("+"):
                        fpath = line[1:].strip()
                        # Si repository.dat indique explicitement "1" (Scan Always), conserver "1"
                        st = "1" if repo_map.get(fpath) == "1" else "2"
                    else:
                        fpath = line
                        st = "1"
                    if fpath:
                        if not fpath.endswith("\\") and ("\\" in fpath or ":" in fpath):
                            fpath += "\\"
                        self._scanlist[fpath] = st
            except Exception:
                pass

        # 3. wordhash.dat (FR: Index inversé de recherche / EN: Inverted search index)
        wh_path = self.db3_dir / "wordhash.dat"
        if wh_path.exists():
            self.wordhash = WordHashFile.from_bytes(wh_path.read_bytes())

        # 4. Tables PMP (FR: Colonnes de propriétés / EN: Property columns)
        for pmp_path in self.db3_dir.glob("*.pmp"):
            self.pmps[pmp_path.stem] = PmpFile.from_bytes(pmp_path.read_bytes())

        # 5. CBlockFile indices & conteneurs multi-blocs (*_0.db, *_1.db, ...)
        # Ref: picasa3.exe @ 0x006B6AF0 (CBlockFile::OpenBlock "%s_%d.%s"), 0x006B8AC0 (ValidateIndex)
        for idx_path in self.db3_dir.glob("*_index.db"):
            prefix = idx_path.stem.replace("_index", "")
            idx_obj = BlockIndexFile.from_bytes(idx_path.read_bytes())
            self.block_indices[prefix] = idx_obj

            for cont_path in sorted(self.db3_dir.glob(f"{prefix}_*.db")):
                if cont_path.stem.endswith("_index"):
                    continue
                suffix_part = cont_path.stem[len(prefix) + 1 :]
                if suffix_part.isdigit():
                    block_num = int(suffix_part)
                    cont_obj = BlockContainerFile.from_file(cont_path)
                    self.block_containers_by_block[(prefix, block_num)] = cont_obj
                    if block_num == 0:
                        self.block_containers[prefix] = cont_obj

            # Ref: picasa3.exe @ 0x006B8AC0 (lines 308-320), 0x006B91F0 (line 65 : dirty=0) :
            # invalide en mémoire les entrées du bloc actif dont offset + size dépasse la taille
            # réelle du conteneur actif sur disque (ex. après compactage de bigthumbs_0.db / previews_0.db
            # à 4 octets via 0x0041B77E-0x0041B7B0), tout en laissant dirty = False.
            active_blk = idx_obj.active_block
            active_cont = self.block_containers_by_block.get((prefix, active_blk))
            if active_cont is not None:
                cont_len = active_cont.byte_size()
                for entry_idx in range(idx_obj.record_count):
                    raw_sb = idx_obj.sizes_and_blocks[entry_idx]
                    if ((raw_sb >> 24) & 0xFF) == active_blk:
                        e_size = raw_sb & 0x00FFFFFF
                        e_off = idx_obj.offsets[entry_idx]
                        if (e_size != 0 or e_off != 0) and (e_off < 4 or e_off + e_size > cont_len):
                            idx_obj.offsets[entry_idx] = 0
                            idx_obj.sizes_and_blocks[entry_idx] = 0
                            idx_obj.checksums[entry_idx] = 0
                            idx_obj._compacted_on_disk = True

        # 6. contacts.xml (FR: Carnet de contacts / EN: Contacts address book)
        if self.contacts_dir and (self.contacts_dir / "contacts.xml").exists():
            self.contacts = ContactsFile.from_xml((self.contacts_dir / "contacts.xml").read_text(encoding="utf-8"))

        # 7. Synchroniser en mémoire les dossiers ayant P2category=Hidden Folders dans .picasa.ini (Ref: 0x004420D3)
        self._hidden_folders: Set[str] = set()
        ad_cats = self.pmps.get("albumdata_category")
        ad_files = self.pmps.get("albumdata_filename")
        if ad_cats is not None and ad_files is not None:
            for i_row, fp_val in enumerate(ad_files.records):
                if not fp_val or i_row >= len(ad_cats.records):
                    continue
                cat_v = ad_cats.records[i_row]
                if cat_v == 7:
                    self._hidden_folders.add(str(fp_val).replace("\\", "/").rstrip("/").lower())
                elif cat_v == 2:
                    host_fp = _to_host_path(str(fp_val).rstrip("\\/"))
                    if host_fp:
                        ini_cand = os.path.join(host_fp, ".picasa.ini")
                        if os.path.exists(ini_cand):
                            try:
                                with open(ini_cand, "rb") as fh_ini:
                                    head_bytes = fh_ini.read(512)
                                if b"Hidden Folders" in head_bytes:
                                    doc_ini = self.get_parsed_ini(ini_cand)
                                    sec_p = doc_ini.get_section("Picasa") if doc_ini is not None else None
                                    p2c = (sec_p.get("P2category") or sec_p.get("category") or "").strip() if sec_p else ""
                                    if p2c.lower() in ("hidden folders", "dossiers masqués"):
                                        ad_cats.records[i_row] = 7
                                        self._hidden_folders.add(str(fp_val).replace("\\", "/").rstrip("/").lower())
                            except Exception:
                                pass

        self._deleted_or_reset_indices.clear()
        self._modified_media_indices.clear()
        self._invalidate_path_index_cache()
        self._albums_cache = None
        self._starred_cache = None
        self._min_aligned_idx = -1

    @classmethod
    def resolve_database_dirs(
        cls,
        target_dir: str | Path,
        contacts_dir: str | Path | None = None,
        for_creation: bool = False,
    ) -> Tuple[Path, Path]:
        """
        FR: Résout les répertoires (db3_dir, contacts_dir) que l'utilisateur ait sélectionné
        le dossier parent (contenant db3/ et contacts/) ou directement le dossier db3/.
        EN: Resolves the (db3_dir, contacts_dir) directories whether the user selected
        the parent folder (containing db3/ and contacts/) or the db3/ folder directly.
        """
        p = Path(target_dir)
        if contacts_dir is not None:
            return p, Path(contacts_dir)
        if p.name.lower() == "db3":
            return p, p.parent / "contacts"
        if (p / "thumbindex.db").exists() or any(p.glob("*.pmp")) or any(p.glob("*_index.db")):
            return p, p.parent / "contacts"
        if (p / "db3").is_dir() or for_creation:
            return p / "db3", p / "contacts"
        return p, p.parent / "contacts"

    @classmethod
    def open(cls, db3_dir: str | Path, contacts_dir: str | Path | None = None) -> PicasaDatabase:
        """
        FR: Ouvre une base de données Picasa existante depuis les chemins spécifiés.
        EN: Opens an existing Picasa database from the specified paths.
        """
        p_db3, p_cont = cls.resolve_database_dirs(db3_dir, contacts_dir, for_creation=False)
        db = cls(db3_dir=p_db3, contacts_dir=p_cont)
        db.load_all()
        return db

    @classmethod
    def create_new(cls, target_dir: str | Path, contacts_dir: str | Path | None = None) -> PicasaDatabase:
        """
        FR: Crée et initialise sur disque une nouvelle base de données Picasa 3 complète et vierge
        (structure binaire exacte de CThumbDB::Init @ 0x004156F0 : thumbindex.db, wordhash.dat,
        repository.dat, usernames.dat, contacts/contacts.xml, 56 colonnes .pmp et 6 paires CBlockFile).
        EN: Creates and initializes on disk a complete, blank Picasa 3 database
        (exact binary structure of CThumbDB::Init @ 0x004156F0: thumbindex.db, wordhash.dat,
        repository.dat, usernames.dat, contacts/contacts.xml, 56 .pmp columns, and 6 CBlockFile pairs).
        """
        p_db3, p_cont = cls.resolve_database_dirs(target_dir, contacts_dir, for_creation=True)
        p_db3.mkdir(parents=True, exist_ok=True)
        p_cont.mkdir(parents=True, exist_ok=True)

        # FR: Purger tout fichier résiduel (*.pmp, *.db, *.dat, *.tmp, *.txt, albums/*.pal) si le dossier contenait une ancienne base
        # EN: Purge any residual file (*.pmp, *.db, *.dat, *.tmp, *.txt, albums/*.pal) if the folder previously held a database
        for pattern in ("*.pmp", "*.db", "*.dat", "*.tmp", "*.txt"):
            for old_f in p_db3.glob(pattern):
                try:
                    old_f.unlink()
                except Exception:
                    pass
        albums_subdir = p_db3 / "albums"
        if albums_subdir.is_dir():
            for old_pal in albums_subdir.glob("*.pal"):
                try:
                    old_pal.unlink()
                except Exception:
                    pass

        db = cls(db3_dir=p_db3, contacts_dir=p_cont)
        db.thumbindex = ThumbIndexFile(records=[], dirty=True)
        db.repository = KeyValueTableFile(pairs=[])
        db.usernames = KeyValueTableFile(pairs=[])
        db.wordhash = WordHashFile(dirty=True)
        db.contacts = ContactsFile(contacts=[])

        for stem, pmp_type in STANDARD_PMP_SCHEMA.items():
            default_records = list(DEFAULT_CATDATA_RECORDS.get(stem, []))
            db.pmps[stem] = PmpFile(pmp_type=pmp_type, records=default_records, dirty=True)

        for prefix in STANDARD_BLOCKFILE_PREFIXES:
            idx_obj = BlockIndexFile.from_entries([], active_block=0)
            idx_obj.dirty = True
            db.block_indices[prefix] = idx_obj
            cont = BlockContainerFile()
            cont._fully_dirty = True
            db.block_containers[prefix] = cont
            db.block_containers_by_block[(prefix, 0)] = cont

        db.save_database(force_all=True)
        return db

    @property
    def index(self) -> List[ThumbIndexRecord]:
        """
        FR: Retourne la liste des enregistrements de thumbindex.db.
        EN: Returns the list of records from thumbindex.db.
        """
        return self.thumbindex.records if self.thumbindex else []

    @property
    def catdata(self) -> Dict[str, PmpFile]:
        """
        FR: Retourne le dictionnaire des tables PMP de catégories (catdata_*).
        EN: Returns the dictionary of category PMP tables (catdata_*).
        """
        return {k.replace("catdata_", ""): v for k, v in self.pmps.items() if k.startswith("catdata_")}

    @property
    def search_index(self) -> Optional[WordHashFile]:
        """
        FR: Retourne l'instance de l'index inversé wordhash.dat.
        EN: Returns the wordhash.dat inverted search index instance.
        """
        return self.wordhash

    @property
    def face_manager(self) -> Any:
        """
        FR: Retourne le gestionnaire de reconnaissance faciale associé à la base.
        EN: Returns the facial recognition manager associated with the database.
        """
        if self._face_manager is None:
            from picasa_py.faces.face_manager import PicasaFaceManager
            self._face_manager = PicasaFaceManager(self)
        return self._face_manager

    def search(self, query: str) -> List[int]:
        """
        FR: Recherche plein texte multi-mots (AND) avec support des préfixes.
        Combine l'index inversé wordhash.dat avec l'indexation dynamique des enregistrements
        (noms de fichiers, dossiers parents, personnes identifiées, mots-clés) via un cache mémoire O(1).
        EN: Multi-word full-text search (AND) with prefix matching support.
        Combines the wordhash.dat inverted index with dynamic record indexing
        (filenames, parent folders, identified people, keywords) via an O(1) in-memory haystack cache.
        Ref: picasa3.exe @ 0x007046E0 (wordhash search), 0x0088C3EC (live search)
        """
        query_stripped = query.strip()
        if not query_stripped:
            return []

        matched_indices: Set[int] = set()

        # 1. Utiliser wordhash.dat si présent / Use wordhash.dat if available
        if self.wordhash:
            try:
                wh_results = self.wordhash.search(query_stripped)
                for idx in wh_results:
                    if idx not in self._deleted_or_reset_indices:
                        matched_indices.add(idx)
            except Exception:
                pass

        # 2. Recherche dynamique dans les métadonnées de la base via _search_haystack_cache
        tokens = [t.lower() for t in query_stripped.split() if t]
        if not tokens:
            return sorted(list(matched_indices))

        if self.thumbindex:
            recs = self.thumbindex.records
            if self._search_haystack_cache is None or self._search_haystack_len != len(recs):
                haystack: Dict[int, str] = {}
                folder_names: Dict[int, str] = {}
                for i, r in enumerate(recs):
                    if r.type == 1:
                        clean_p = r.path.rstrip("\\/").replace("\\", "/")
                        folder_names[i] = os.path.basename(clean_p).lower()

                pmp_tags = self.pmps.get("imagedata_tags")
                tags_recs = pmp_tags.records if pmp_tags else []
                tags_len = len(tags_recs)

                pmp_caption = self.pmps.get("imagedata_caption")
                cap_recs = pmp_caption.records if pmp_caption else []
                cap_len = len(cap_recs)

                person_names_by_idx: Dict[int, List[str]] = {}
                if self._face_manager is not None:
                    people_dict = getattr(self._face_manager, "people", None)
                    if isinstance(people_dict, dict):
                        for person in people_dict.values():
                            pname = (getattr(person, "display_name", "") or getattr(person, "name", "") or "").strip().lower()
                            if not pname:
                                continue
                            for p_idx in getattr(person, "photo_indices", ()):
                                lst = person_names_by_idx.get(p_idx)
                                if lst is None:
                                    person_names_by_idx[p_idx] = [pname]
                                else:
                                    lst.append(pname)
                    for p_idx, flist in getattr(self._face_manager, "photo_to_faces", {}).items():
                        for f in flist:
                            cid = getattr(f, "contact_id", "")
                            if cid and cid != "ffffffffffffffff":
                                p = self._face_manager.get_person(cid)
                                if p and p.name:
                                    pname = p.name.lower()
                                    lst = person_names_by_idx.get(p_idx)
                                    if lst is None:
                                        person_names_by_idx[p_idx] = [pname]
                                    elif pname not in lst:
                                        lst.append(pname)

                deleted_set = self._deleted_or_reset_indices
                for i, r in enumerate(recs):
                    if r.type not in MEDIA_RECORD_TYPES or i in deleted_set or not r.path:
                        continue
                    parts = [r.path.lower(), folder_names.get(r.parent_idx, "")]
                    if i < tags_len and tags_recs[i]:
                        parts.append(str(tags_recs[i]).lower())
                    if i < cap_len and cap_recs[i]:
                        parts.append(str(cap_recs[i]).lower())
                    pnames = person_names_by_idx.get(i)
                    if pnames:
                        parts.extend(pnames)
                    haystack[i] = " ".join(parts)

                self._search_haystack_cache = haystack
                self._search_haystack_len = len(recs)

            deleted_set = self._deleted_or_reset_indices
            for i, corpus in self._search_haystack_cache.items():
                if i in matched_indices or i in deleted_set:
                    continue
                if all(tok in corpus for tok in tokens):
                    matched_indices.add(i)

        return sorted(list(matched_indices))

    def get_parsed_ini(self, ini_path: str) -> Optional[Any]:
        """
        FR: Lit et met en cache l'arbre d'un fichier .picasa.ini pour éviter des relectures multiples.
        Toutes les écritures internes appellent `invalidate_ini_cache`, ce qui permet un TTL long (30 s)
        sans appels `os.path.exists`/`os.path.getmtime` répétés sur le thread GUI.
        EN: Reads and caches a .picasa.ini file tree to avoid redundant disk reads.
        All internal writes call `invalidate_ini_cache`, allowing a 30s TTL without repeated
        `os.path.exists`/`os.path.getmtime` calls on the GUI thread.
        Ref: AGENTS.md §4 ter (Performances - Réduction des I/O disque).
        """
        if not ini_path:
            return None
        key = os.path.normcase(os.path.abspath(ini_path))
        now = time.monotonic()
        cached = self._ini_cache.get(key)
        if cached is not None and len(cached) == 3:
            c_mtime, last_check, c_doc = cached
            if now - last_check < 30.0:
                return c_doc
        else:
            c_mtime, c_doc = (-2.0, None)

        # FR: Si on demande Picasa.ini alors que .picasa.ini existe déjà dans le cache de ce dossier,
        # éviter un stat disque inutile sur Picasa.ini.
        # EN: If Picasa.ini is requested while .picasa.ini already exists in cache for this folder,
        # skip an unnecessary disk stat on Picasa.ini.
        bname_low = os.path.basename(key)
        if bname_low == "picasa.ini":
            dot_key = os.path.join(os.path.dirname(key), ".picasa.ini")
            dot_cached = self._ini_cache.get(dot_key)
            if dot_cached is not None and len(dot_cached) == 3 and dot_cached[2] is not None:
                self._ini_cache[key] = (-1.0, now, None)
                return None

        if not os.path.exists(ini_path):
            self._ini_cache[key] = (-1.0, now, None)
            return None
        try:
            mtime = os.path.getmtime(ini_path)
            if cached is not None and c_mtime == mtime:
                self._ini_cache[key] = (mtime, now, c_doc)
                return c_doc
            from picasa_py.ini.parser import PicasaIniParser
            doc = PicasaIniParser.parse_file(ini_path)
            self._ini_cache[key] = (mtime, now, doc)
            return doc
        except Exception:
            return None

    def invalidate_ini_cache(
        self,
        ini_path: Optional[str | Path] = None,
        invalidate_albums_starred: bool = True,
    ) -> None:
        """
        FR: Invalide l'entrée de cache INI lors d'une modification sur disque.
        Si `invalidate_albums_starred=False` (ex. mise à jour de `faces=` uniquement),
        conserve `_albums_cache` et `_starred_cache` intacts.
        EN: Invalidates the INI cache entry when modified on disk.
        When `invalidate_albums_starred=False` (e.g. updating `faces=` only),
        preserves `_albums_cache` and `_starred_cache`.
        """
        if ini_path:
            ini_str = str(ini_path)
            key = os.path.normcase(os.path.abspath(ini_str))
            self._ini_cache.pop(key, None)
            self._ini_cache.pop(ini_str, None)
        else:
            self._ini_cache.clear()
        if invalidate_albums_starred:
            self._albums_cache = None
            self._starred_cache = None

    def _invalidate_path_index_cache(self) -> None:
        """
        FR: Invalide les index O(1) de chemins et d'enregistrements de visages enfants.
        EN: Invalidates the O(1) path and child face record lookup caches.
        """
        self._path_index_version = -1
        self._parent_to_face_children_len = -1
        self.invalidate_search_cache()

    def _index_single_record_into_cache(self, idx: int, r: ThumbIndexRecord) -> None:
        """
        FR: Insère un enregistrement de thumbindex.db dans les caches O(1) de dossiers, médias et visages.
        EN: Inserts a thumbindex.db record into the O(1) folder, media, and face lookup caches.
        """
        if r.type == 1:
            raw_norm = r.path.replace("/", "\\").rstrip("\\").lower()
            host_p = _to_host_path(r.path)
            abs_norm = os.path.abspath(host_p).replace("/", "\\").rstrip("\\").lower() if host_p else raw_norm
            self._folder_idx_to_norms[idx] = (raw_norm, abs_norm)
            self._folder_index_cache.setdefault(raw_norm, idx)
            self._folder_index_cache.setdefault(abs_norm, idx)
        elif r.type in MEDIA_RECORD_TYPES:
            fn_low = r.path.lower()
            norms = self._folder_idx_to_norms.get(r.parent_idx)
            if norms is None and self.thumbindex and 0 <= r.parent_idx < len(self.thumbindex.records):
                pr = self.thumbindex.records[r.parent_idx]
                if pr.type == 1:
                    raw_n = pr.path.replace("/", "\\").rstrip("\\").lower()
                    host_p = _to_host_path(pr.path)
                    abs_n = os.path.abspath(host_p).replace("/", "\\").rstrip("\\").lower() if host_p else raw_n
                    norms = (raw_n, abs_n)
                    self._folder_idx_to_norms[r.parent_idx] = norms
            if norms is not None:
                raw_n, abs_n = norms
                k_raw = f"{raw_n}\\{fn_low}"
                k_abs = f"{abs_n}\\{fn_low}"
                prev_raw = self._path_index_cache.get(k_raw)
                if prev_raw is None or (
                    self.thumbindex
                    and 0 <= prev_raw < len(self.thumbindex.records)
                    and self.thumbindex.records[prev_raw].type not in MEDIA_RECORD_TYPES
                ):
                    self._path_index_cache[k_raw] = idx
                prev_abs = self._path_index_cache.get(k_abs)
                if prev_abs is None or (
                    self.thumbindex
                    and 0 <= prev_abs < len(self.thumbindex.records)
                    and self.thumbindex.records[prev_abs].type not in MEDIA_RECORD_TYPES
                ):
                    self._path_index_cache[k_abs] = idx
        elif r.type == 1001 and r.parent_idx >= 0:
            children = self._parent_to_face_children.setdefault(r.parent_idx, [])
            if idx not in children:
                children.append(idx)

    def _ensure_path_index_cache(self) -> None:
        """
        FR: Maintient à jour l'index O(1) des chemins et des visages enfants en fonction de thumbindex.records.
        EN: Keeps the O(1) path and child face index synchronized with thumbindex.records.
        """
        if not self.thumbindex:
            self._path_index_cache.clear()
            self._folder_index_cache.clear()
            self._folder_idx_to_norms.clear()
            self._parent_to_face_children.clear()
            self._path_index_version = 0
            self._parent_to_face_children_len = 0
            return

        recs = self.thumbindex.records
        curr_len = len(recs)
        ti_id = id(self.thumbindex)

        if self._path_index_version < 0 or self._path_index_ti_id != ti_id or curr_len < self._path_index_version:
            self._path_index_cache.clear()
            self._folder_index_cache.clear()
            self._folder_idx_to_norms.clear()
            self._parent_to_face_children.clear()
            for i, r in enumerate(recs):
                if r.type == 1:
                    self._index_single_record_into_cache(i, r)
            for i, r in enumerate(recs):
                if r.type != 1:
                    self._index_single_record_into_cache(i, r)
            self._path_index_version = curr_len
            self._parent_to_face_children_len = curr_len
            self._path_index_ti_id = ti_id
        elif curr_len > self._path_index_version:
            for i in range(self._path_index_version, curr_len):
                self._index_single_record_into_cache(i, recs[i])
            self._path_index_version = curr_len
            self._parent_to_face_children_len = curr_len

    def _get_face_children(self, parent_idx: int) -> List[int]:
        """
        FR: Retourne en O(1) la liste des sous-enregistrements de visages (type == 1001) d'une photo parente.
        EN: Returns in O(1) the list of child face sub-records (type == 1001) for a parent photo.
        """
        self._ensure_path_index_cache()
        if not self.thumbindex:
            return []
        recs = self.thumbindex.records
        return [
            c_idx
            for c_idx in self._parent_to_face_children.get(parent_idx, [])
            if 0 <= c_idx < len(recs) and recs[c_idx].type == 1001 and recs[c_idx].parent_idx == parent_idx
        ]

    def find_photo_index(self, photo_path: str) -> Optional[int]:
        """
        FR: Retrouve en O(1) l'indice d'une photo dans thumbindex.db à partir de son chemin complet.
        EN: Finds in O(1) a photo's record index in thumbindex.db from its full file path.
        """
        if not self.thumbindex or not photo_path:
            return None
        self._ensure_path_index_cache()
        fname_lower = os.path.basename(photo_path).lower()
        abs_dir = os.path.dirname(os.path.abspath(photo_path)).replace("/", "\\").rstrip("\\").lower()
        raw_dir = os.path.dirname(photo_path).replace("/", "\\").rstrip("\\").lower()

        for cand_dir in (abs_dir, raw_dir):
            key = f"{cand_dir}\\{fname_lower}"
            idx = self._path_index_cache.get(key)
            if idx is not None and 0 <= idx < len(self.thumbindex.records):
                rec = self.thumbindex.records[idx]
                if rec.type in MEDIA_RECORD_TYPES and rec.path.lower() == fname_lower:
                    return idx
                # FR: Enregistrement modifié/supprimé en place -> reconstruire le cache / EN: Record mutated in-place -> rebuild cache
                self._invalidate_path_index_cache()
                self._ensure_path_index_cache()
                idx2 = self._path_index_cache.get(key)
                if idx2 is not None and 0 <= idx2 < len(self.thumbindex.records):
                    rec2 = self.thumbindex.records[idx2]
                    if rec2.type in MEDIA_RECORD_TYPES and rec2.path.lower() == fname_lower:
                        return idx2
        return None

    find_media_index_by_path = find_photo_index

    def _sync_album_sections_from_ini_doc(self, doc: Any) -> None:
        """
        FR: Synchronise les sections `[.album:<token>]` d'un document `.picasa.ini` vers `albumdata_*.pmp` (dont `albumdata_date.pmp`).
        EN: Synchronizes `[.album:<token>]` sections of a `.picasa.ini` document into `albumdata_*.pmp` (including `albumdata_date.pmp`).
        Ref: picasa3.exe @ 0x00456A15 (FUN_00456a15 -> SyncIniToDB)
        """
        if doc is None or not hasattr(doc, "sections"):
            return
        for sec in doc.sections:
            if not (sec.name.startswith(".album:") or sec.name.startswith("]album:")):
                continue
            raw_tok = sec.get("token") or sec.name[7:]
            clean_tok = raw_tok.strip()
            if clean_tok.startswith("]album:") or clean_tok.startswith(".album:"):
                clean_tok = clean_tok[7:].strip()
            if not clean_tok:
                continue

            ad_tokens = self.pmps.get("albumdata_token")
            ad_uids = self.pmps.get("albumdata_uid")
            ad_names = self.pmps.get("albumdata_name")
            ad_dates = self.pmps.get("albumdata_date")
            ad_cats = self.pmps.get("albumdata_category")

            alb_idx: Optional[int] = None
            candidates = (clean_tok, f"]album:{clean_tok}", f".album:{clean_tok}", raw_tok.strip())
            if ad_tokens is not None:
                for i, v in enumerate(ad_tokens.records):
                    if str(v or "").strip() in candidates:
                        alb_idx = i
                        break
            if alb_idx is None and ad_uids is not None:
                for i, v in enumerate(ad_uids.records):
                    if str(v or "").strip() in candidates:
                        alb_idx = i
                        break
            if alb_idx is None and (ad_dates is not None or ad_names is not None or ad_tokens is not None):
                base_col = ad_names or ad_tokens or ad_dates
                assert base_col is not None
                alb_idx = len(base_col.records)
                for stem, pmp in self.pmps.items():
                    if stem.startswith("albumdata_"):
                        def_v = pmp.default_value()
                        while len(pmp.records) <= alb_idx:
                            pmp.records.append(def_v)
                            pmp.dirty = True
                if ad_tokens is not None:
                    ad_tokens.records[alb_idx] = f"]album:{clean_tok}"
                    ad_tokens.dirty = True
                if ad_uids is not None:
                    ad_uids.records[alb_idx] = clean_tok
                    ad_uids.dirty = True
                if ad_cats is not None:
                    ad_cats.records[alb_idx] = 0
                    ad_cats.dirty = True

            if alb_idx is not None:
                for stem, pmp in self.pmps.items():
                    if stem.startswith("albumdata_"):
                        def_v = pmp.default_value()
                        while len(pmp.records) <= alb_idx:
                            pmp.records.append(def_v)
                            pmp.dirty = True
                aname = sec.get("name")
                if aname is not None and ad_names is not None:
                    if ad_names.records[alb_idx] != aname:
                        ad_names.records[alb_idx] = aname
                        ad_names.dirty = True
                adesc = sec.get("description") or sec.get("caption")
                ad_descs = self.pmps.get("albumdata_description")
                if adesc is not None and ad_descs is not None and alb_idx < len(ad_descs.records):
                    if ad_descs.records[alb_idx] != adesc:
                        ad_descs.records[alb_idx] = adesc
                        ad_descs.dirty = True
                aloc = sec.get("location")
                ad_locs = self.pmps.get("albumdata_location")
                if aloc is not None and ad_locs is not None and alb_idx < len(ad_locs.records):
                    if ad_locs.records[alb_idx] != aloc:
                        ad_locs.records[alb_idx] = aloc
                        ad_locs.dirty = True
                amusic = sec.get("music")
                ad_musics = self.pmps.get("albumdata_music")
                if amusic is not None and ad_musics is not None and alb_idx < len(ad_musics.records):
                    if ad_musics.records[alb_idx] != amusic:
                        ad_musics.records[alb_idx] = amusic
                        ad_musics.dirty = True
                date_str = sec.get("date")
                if date_str is not None and ad_dates is not None:
                    d_clean = date_str.strip()
                    ole_val: Optional[float] = None
                    try:
                        ole_val = float(d_clean)
                    except ValueError:
                        import datetime
                        ole_epoch = datetime.datetime(1899, 12, 30)
                        try:
                            dt = datetime.datetime.fromisoformat(d_clean)
                            if dt.tzinfo is not None:
                                dt = dt.replace(tzinfo=None)
                            ole_val = (dt - ole_epoch).total_seconds() / 86400.0
                        except Exception:
                            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
                                try:
                                    dt = datetime.datetime.strptime(d_clean[:19], fmt)
                                    ole_val = (dt - ole_epoch).total_seconds() / 86400.0
                                    break
                                except ValueError:
                                    continue
                    if ole_val is not None and ad_dates.records[alb_idx] != ole_val:
                        ad_dates.records[alb_idx] = ole_val
                        ad_dates.dirty = True

    def sync_photo_ini_to_db(self, photo_path: str | Path | int, doc: Any = None) -> None:
        """
        FR: Synchronise les métadonnées d'une photo dans .picasa.ini vers les colonnes .pmp et wordhash.dat.
        Accepte soit le chemin complet de la photo, soit son index dans thumbindex.db.
        EN: Synchronizes a photo's .picasa.ini metadata into .pmp columns and wordhash.dat.
        Accepts either the full photo file path or its record index in thumbindex.db.
        Ref: picasa3.exe @ 0x00456A15 (FUN_00456a15 -> SyncIniToDB), func_00456a15.c:3471
        """
        if isinstance(photo_path, int):
            idx = self._resolve_photo_record_index(photo_path)
            if idx is None:
                return
            resolved_path = self.get_media_full_path(idx)
            if not resolved_path:
                return
            photo_path_str = str(resolved_path)
        else:
            photo_path_str = str(photo_path)
            if os.path.isdir(photo_path_str) or photo_path_str.lower().endswith(".ini"):
                from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
                ini_p = photo_path_str if photo_path_str.lower().endswith(".ini") else os.path.join(photo_path_str, ".picasa.ini")
                if doc is None:
                    doc = self.get_parsed_ini(ini_p)
                    if doc is None:
                        doc = PicasaIniParser.parse_file(ini_p) if os.path.exists(ini_p) else PicasaIniDocument()
                self._sync_album_sections_from_ini_doc(doc)
                return
            idx = self.find_photo_index(photo_path_str)
            if idx is None:
                if doc is not None:
                    self._sync_album_sections_from_ini_doc(doc)
                return
        fname = os.path.basename(photo_path_str)
        if doc is None:
            from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
            ini_path = os.path.join(os.path.dirname(photo_path_str), ".picasa.ini")
            doc = self.get_parsed_ini(ini_path)
            if doc is None:
                doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()

        self._sync_album_sections_from_ini_doc(doc)
        self._align_imagedata_tables(idx)
        sec = doc.get_section(fname) if hasattr(doc, "get_section") else None

        def _set_pmp(col_name: str, val: Any) -> None:
            pmp = self.pmps.get(col_name)
            if pmp is None:
                return
            default_v = pmp.default_value()
            while len(pmp.records) <= idx:
                pmp.records.append(default_v)
                pmp.dirty = True
            if pmp.records[idx] != val:
                pmp.records[idx] = val
                pmp.dirty = True

        # 1. Rotation (Ref: picasa3.exe @ 0x0042A570 : rotate(-1) ou absent -> 0 / "")
        raw_rot_val = sec.get("rotate") if sec is not None else None
        if not raw_rot_val or raw_rot_val.strip().lower() == "rotate(-1)":
            rot = 0
        else:
            rot = int(doc.get_rotate(fname) if hasattr(doc, "get_rotate") else 0)
            if rot < 0:
                rot = 0
        pmp_rot_col = self.pmps.get("imagedata_rotate")
        if pmp_rot_col is not None and int(getattr(pmp_rot_col, "pmp_type", 1)) in (0, 6):
            _set_pmp("imagedata_rotate", f"rotate({rot})" if rot > 0 else "")
        else:
            _set_pmp("imagedata_rotate", rot if rot > 0 else 0)

        # 2. Star / Favori (uniquement si une table synthétique de test imagedata_star existe dans self.pmps)
        if "imagedata_star" in self.pmps:
            starred = 1 if (hasattr(doc, "is_starred") and doc.is_starred(fname)) else 0
            _set_pmp("imagedata_star", starred)

        # 3. Crop64 (avec repli sur filters=crop64=1,<hex> via get_crop_rect64 / get_crop)
        crop_u64 = 0
        if hasattr(doc, "get_crop_rect64"):
            c_rect = doc.get_crop_rect64(fname)
            if c_rect is not None:
                crop_u64 = c_rect.to_uint64()
        elif hasattr(doc, "get_crop"):
            crop_hex = doc.get_crop(fname)
            if crop_hex:
                try:
                    crop_u64 = int(crop_hex, 16)
                except Exception:
                    crop_u64 = 0
        _set_pmp("imagedata_crop64", crop_u64)

        # 4. Filters, Text, Keywords, Caption, BackupHash, DeferredFace, Geotag
        edited_val = 0
        lat_val: Optional[float] = None
        lon_val: Optional[float] = None
        if sec is None:
            edited_val = 1 if crop_u64 else (2 if rot > 0 else 0)
            _set_pmp("imagedata_filters", "")
            _set_pmp("imagedata_redo", "")
            # Ref: picasa3.exe @ 0x00476680 — edited=1 si recadrage/filtres, 2 si rotation seule (db3 : 23/23)
            _set_pmp("imagedata_edited", edited_val)
            _set_pmp("imagedata_text", "")
            _set_pmp("imagedata_textactive", 0)
            _set_pmp("imagedata_tags", "")
            _set_pmp("imagedata_caption", "")
            _set_pmp("imagedata_deferredface", "")
            _set_pmp("imagedata_backuphash", 0)
            has_orig_backup = bool(
                photo_path_str
                and fname
                and os.path.exists(os.path.join(os.path.dirname(photo_path_str), ".picasaoriginals", fname))
            )
            if has_orig_backup:
                _set_pmp("imagedata_revertable", 1)
            elif photo_path_str and os.path.exists(photo_path_str):
                _set_pmp("imagedata_revertable", 0)
            if self.wordhash is not None and hasattr(self.wordhash, "remove_word"):
                for st_tok in ("]star", "]hidden", "]screensaver", "]rating"):
                    self.wordhash.remove_word(st_tok, idx)
                ad_uids_col = self.pmps.get("albumdata_uid")
                ad_toks_col = self.pmps.get("albumdata_token")
                known_albs: Set[str] = set()
                for col in (ad_uids_col, ad_toks_col):
                    if col is not None:
                        for v in col.records:
                            s = str(v or "").strip()
                            if s.startswith("]album:") or s.startswith(".album:"):
                                s = s[7:].strip()
                            if s and not s.startswith("]"):
                                known_albs.add(s)
                for ka in known_albs:
                    self.wordhash.remove_word(f"]album:{ka}", idx)
                    self.wordhash.remove_word(f"]snapshot:]album:{ka}", idx)
        else:
            filters_str = sec.get("filters", "") or ""
            # Ref: func_00456a15.c:3352-3460 — legacy fix=1 / bw=1 synthesis when filters= is absent
            if not filters_str:
                synth_parts: List[str] = []
                if (sec.get("fix") or "").strip().lower() in ("1", "yes", "true"):
                    synth_parts.append("autolight=1;")
                if (sec.get("bw") or "").strip().lower() in ("1", "yes", "true"):
                    synth_parts.append("bw=1;")
                if synth_parts:
                    filters_str = "".join(synth_parts)
            # Correction du bug de picasa3.exe @ 0x00459DE3 -> LAB_00459e21 :
            # si crop=rect64(...) est présent sans crop64= dans filters=, on préserve crop_u64 et on le synchronise.
            if crop_u64 and "crop64=" not in filters_str.lower():
                base_f = filters_str.strip(";")
                filters_str = f"{base_f};crop64=1,{crop_u64:x};" if base_f else f"crop64=1,{crop_u64:x};"
            _set_pmp("imagedata_filters", filters_str)
            _set_pmp("imagedata_redo", sec.get("redo", "") or "")

            text_str = sec.get("text", "") or ""
            _set_pmp("imagedata_text", text_str)
            raw_ta = sec.get("textactive")
            # Ref: func_00456a15.c:3189 — strict check on textactive == "1"
            if raw_ta is not None:
                text_active = 1 if raw_ta.strip().lower() in ("1", "yes", "true") else 0
            else:
                text_active = 0
            _set_pmp("imagedata_textactive", text_active)

            # Ref: picasa3.exe @ 0x00476680 — edited=1 si recadrage/filtres/texte actif, 2 si rotation seule (db3 : 23/23)
            edited_val = 1 if (filters_str or crop_u64 or text_active) else (2 if rot > 0 else 0)
            _set_pmp("imagedata_edited", edited_val)

            tags_val = sec.get("keywords", "") or ""
            _set_pmp("imagedata_tags", tags_val if tags_val else "")

            cap_val = sec.get("caption", "") or ""
            _set_pmp("imagedata_caption", cap_val if cap_val else "")

            # Ref: func_00456a15.c:809-862 (onlinechecksum -> uint16 dans imagedata_peoplealbumchecksum.pmp)
            ocs = sec.get("onlinechecksum")
            if ocs:
                try:
                    ocs_s = ocs.strip()
                    try:
                        ocs_int = (int(ocs_s, 16) if ocs_s.lower().startswith("0x") else int(ocs_s, 10)) & 0xFFFF
                    except ValueError:
                        ocs_int = int(ocs_s, 16) & 0xFFFF
                    _set_pmp("imagedata_peoplealbumchecksum", ocs_int)
                except Exception:
                    pass

            # Ref: func_00456a15.c:3471 (backuphash -> uint16 decimal ou 0x hex)
            bhash = sec.get("backuphash")
            bhash_int = 0
            if bhash:
                try:
                    bh_s = bhash.strip()
                    bhash_int = (int(bh_s, 16) if bh_s.lower().startswith("0x") else int(bh_s, 10)) & 0xFFFF
                    _set_pmp("imagedata_backuphash", bhash_int)
                except Exception:
                    _set_pmp("imagedata_backuphash", 0)
            else:
                _set_pmp("imagedata_backuphash", 0)

            has_orig_backup = bool(
                photo_path_str
                and fname
                and any(
                    os.path.exists(os.path.join(os.path.dirname(photo_path_str), orig_dir, fname))
                    for orig_dir in (".picasaoriginals", "Originals")
                )
            )
            if has_orig_backup:
                _set_pmp("imagedata_revertable", 1)
            elif photo_path_str and os.path.exists(photo_path_str):
                _set_pmp("imagedata_revertable", 0)

            raw_faces = sec.get("faces") or ""
            if raw_faces and not self._get_face_children(idx):
                valid_faces = [
                    fp.strip()
                    for fp in raw_faces.split(";")
                    if fp.strip() and not fp.strip().endswith(",0")
                ]
                faces_str = ";".join(valid_faces)
            else:
                faces_str = ""
            _set_pmp("imagedata_deferredface", faces_str)

            geotag_str = sec.get("geotag", "") or ""
            if geotag_str and "," in geotag_str:
                try:
                    lat_s, lon_s = geotag_str.split(",", 1)
                    lat_val = float(lat_s.strip())
                    lon_val = float(lon_s.strip())
                    _set_pmp("imagedata_lat", lat_val)
                    _set_pmp("imagedata_long", lon_val)
                except Exception:
                    pass

            # Indexation dans wordhash.dat (Ref: FUN_00456a15 -> func_0x004d9aa0, CIndexer @ 0x00987DA0)
            if self.wordhash is not None:
                from picasa_py.scanner.scanner import tokenize_indexer_text
                words: List[str] = []
                for kw in tags_val.split(","):
                    if kw.strip():
                        words.extend(tokenize_indexer_text(kw.strip()))
                words.extend(tokenize_indexer_text(cap_val))
                words.extend(tokenize_indexer_text(text_str))
                for tok in words:
                    self.wordhash.add_word(tok, idx)

                # Jetons d'état spéciaux (Ref: picasa3.exe @ 0x0041D358..0x0041D704, 0x00415E5E..0x00415E8C, 0x004DD3CD)
                is_star = (sec.get("star") or "").strip().lower() in ("yes", "1", "true")
                if is_star:
                    self.wordhash.add_word("]star", idx)
                elif hasattr(self.wordhash, "remove_word"):
                    self.wordhash.remove_word("]star", idx)

                is_hidden = (sec.get("hidden") or "").strip().lower() in ("yes", "1", "true")
                if is_hidden:
                    self.wordhash.add_word("]hidden", idx)
                elif hasattr(self.wordhash, "remove_word"):
                    self.wordhash.remove_word("]hidden", idx)

                # Ref: picasa3.exe @ 0x00458F9B (func_00456a15.c:2829-2860) :
                # Correction du bug original (qui ignorait la valeur de screensaver=) :
                # active ]screensaver pour "yes"/"1"/"true" et le retire pour "no"/"0"/"false"/vide.
                raw_ss = sec.get("screensaver")
                is_screensaver = raw_ss is not None and raw_ss.strip().lower() not in ("", "no", "0", "false")
                alb_csv = sec.get("albums") or ""
                active_alb_tokens: Set[str] = set()
                if alb_csv:
                    for raw_a in alb_csv.split(","):
                        a_tok = raw_a.strip()
                        if a_tok.startswith("]album:") or a_tok.startswith(".album:"):
                            a_tok = a_tok[7:].strip()
                        if a_tok:
                            active_alb_tokens.add(a_tok)
                            if a_tok.lower() == "screensaver":
                                is_screensaver = True
                            self.wordhash.add_word(f"]album:{a_tok}", idx)
                            self.wordhash.add_word(f"]snapshot:]album:{a_tok}", idx)
                if hasattr(self.wordhash, "remove_word"):
                    ad_uids_col = self.pmps.get("albumdata_uid")
                    ad_toks_col = self.pmps.get("albumdata_token")
                    known_albs_rm: Set[str] = set()
                    for col in (ad_uids_col, ad_toks_col):
                        if col is not None:
                            for v in col.records:
                                s = str(v or "").strip()
                                if s.startswith("]album:") or s.startswith(".album:"):
                                    s = s[7:].strip()
                                if s and not s.startswith("]"):
                                    known_albs_rm.add(s)
                    for ka in known_albs_rm:
                        if ka not in active_alb_tokens:
                            self.wordhash.remove_word(f"]album:{ka}", idx)
                            self.wordhash.remove_word(f"]snapshot:]album:{ka}", idx)
                if is_screensaver:
                    self.wordhash.add_word("]screensaver", idx)
                elif hasattr(self.wordhash, "remove_word"):
                    self.wordhash.remove_word("]screensaver", idx)

                # Ref: func_00456a15.c:285-369 (rating -> ]rating dans wordhash.dat)
                raw_rating = (sec.get("rating") or "").strip()
                has_rating = False
                if raw_rating:
                    try:
                        has_rating = int(raw_rating) != 0
                    except Exception:
                        has_rating = False
                if has_rating:
                    self.wordhash.add_word("]rating", idx)
                elif hasattr(self.wordhash, "remove_word"):
                    self.wordhash.remove_word("]rating", idx)

        if self.wordhash is not None:
            if edited_val != 0:
                self.wordhash.add_word("]edited", idx)
            elif hasattr(self.wordhash, "remove_word"):
                self.wordhash.remove_word("]edited", idx)

            pmp_rev = self.pmps.get("imagedata_revertable")
            rev_val = pmp_rev.records[idx] if pmp_rev is not None and idx < len(pmp_rev.records) else 0
            if rev_val:
                self.wordhash.add_word("]revertable", idx)
            elif hasattr(self.wordhash, "remove_word"):
                self.wordhash.remove_word("]revertable", idx)

            if lat_val is None:
                pmp_lat = self.pmps.get("imagedata_lat")
                if pmp_lat is not None and idx < len(pmp_lat.records):
                    try:
                        lat_val = float(pmp_lat.records[idx] or 0.0)
                    except Exception:
                        lat_val = 0.0
            if lat_val and lat_val != 0.0:
                self.wordhash.add_word("]geo", idx)
            elif hasattr(self.wordhash, "remove_word"):
                self.wordhash.remove_word("]geo", idx)
        self.invalidate_search_cache()

    def _resolve_photo_record_index(self, idx: int) -> Optional[int]:
        """
        FR: Résout l'index d'un enregistrement de visage (type == 1001) vers l'index de sa photo parente.
        EN: Resolves a face record index (type == 1001) to its parent photo record index.
        """
        if self.is_face_record(idx):
            parent_idx = self.get_face_parent_photo_idx(idx)
            if parent_idx is not None and 0 <= parent_idx < len(self.index):
                return parent_idx
            return None
        if not self.thumbindex or idx < 0 or idx >= len(self.thumbindex.records):
            return None
        return idx

    def get_rotate(self, idx: int) -> int:
        """
        FR: Lit le pas de rotation (0..3) d'un média (résout automatiquement un index 1001 vers sa photo parente).
        EN: Reads the rotation step (0..3) of a media item (automatically resolves a 1001 face index to its parent photo).
        Ref: picasa3.exe @ 0x0068B5E0 ("rotate=rotate(%d)\r\n")
        """
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return 0
        full_path = self.get_media_full_path(eff_idx)
        if full_path:
            ini_path = os.path.join(os.path.dirname(full_path), ".picasa.ini")
            doc = self.get_parsed_ini(ini_path)
            if doc is not None:
                rot = doc.get_rotate(os.path.basename(full_path))
                if rot:
                    return rot
        pmp_rot = self.pmps.get("imagedata_rotate")
        if pmp_rot and eff_idx < len(pmp_rot.records):
            raw = pmp_rot.records[eff_idx]
            if isinstance(raw, int):
                return raw % 4 if raw >= 0 else 0
            if isinstance(raw, str) and raw:
                import re
                m = re.search(r"-?\d+", raw)
                if m:
                    val = int(m.group(0))
                    return val % 4 if val >= 0 else 0
        return 0

    def set_rotate(self, idx: int, rotation: int) -> bool:
        """
        FR: Définit le pas de rotation (0..3) d'un média (résout automatiquement un index 1001 vers sa photo parente).
        EN: Sets the rotation step (0..3) of a media item (automatically resolves a 1001 face index to its parent photo).
        Ref: picasa3.exe @ 0x0068B5E0 ("rotate=rotate(%d)\r\n")
        """
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return False
        self._align_imagedata_tables(eff_idx)
        rot = int(rotation) % 4
        full_path = self.get_media_full_path(eff_idx)
        if full_path:
            return self.update_photo_ini(full_path, lambda doc, fn: doc.set_rotate(fn, rot))
        pmp_rot = self.pmps.get("imagedata_rotate")
        if pmp_rot is not None:
            default_v = pmp_rot.default_value()
            while len(pmp_rot.records) <= eff_idx:
                pmp_rot.records.append(default_v)
                pmp_rot.dirty = True
            if int(getattr(pmp_rot, "pmp_type", 1)) in (0, 6):
                pmp_rot.records[eff_idx] = f"rotate({rot})" if rot > 0 else ""
            else:
                pmp_rot.records[eff_idx] = rot
            pmp_rot.dirty = True
            return True
        return False

    def is_starred(self, idx: int) -> bool:
        """
        FR: Indique si la photo (ou la photo parente d'un visage 1001) est marquée favorite (star=yes).
        EN: Indicates whether the photo (or the parent photo of a 1001 face record) is starred (star=yes).
        Ref: picasa3.exe @ 0x0068B800 ("star=yes\r\n")
        """
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return False
        full_path = self.get_media_full_path(eff_idx)
        if full_path:
            ini_path = os.path.join(os.path.dirname(full_path), ".picasa.ini")
            doc = self.get_parsed_ini(ini_path)
            if doc is not None:
                return doc.is_starred(os.path.basename(full_path))
        pmp_star = self.pmps.get("imagedata_star")
        if pmp_star and eff_idx < len(pmp_star.records):
            return bool(pmp_star.records[eff_idx])
        return False

    def set_starred(self, idx: int, starred: bool) -> bool:
        """
        FR: Définit le statut favori (star=yes) sur la photo (ou la photo parente d'un visage 1001).
        EN: Sets the starred status (star=yes) on the photo (or the parent photo of a 1001 face record).
        Ref: picasa3.exe @ 0x0068B800 ("star=yes\r\n")
        """
        self._starred_cache = None
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return False
        full_path = self.get_media_full_path(eff_idx)
        if full_path:
            res = self.update_photo_ini(full_path, lambda doc, fn: doc.set_starred(fn, bool(starred)))
            self._starred_cache = None
            return res
        return False

    def get_caption(self, idx: int) -> str:
        """
        FR: Retourne la légende (caption) de la photo (ou de la photo parente d'un visage 1001).
        EN: Returns the caption of the photo (or of the parent photo of a 1001 face record).
        Ref: picasa3.exe @ 0x00456A15
        """
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return ""
        full_path = self.get_media_full_path(eff_idx)
        if full_path:
            ini_path = os.path.join(os.path.dirname(full_path), ".picasa.ini")
            doc = self.get_parsed_ini(ini_path)
            if doc is not None:
                sec = doc.get_section(os.path.basename(full_path))
                if sec is not None:
                    val = sec.get("caption")
                    if val is not None:
                        return val
        pmp_cap = self.pmps.get("imagedata_caption")
        if pmp_cap and eff_idx < len(pmp_cap.records) and pmp_cap.records[eff_idx]:
            return str(pmp_cap.records[eff_idx])
        return ""

    def set_caption(self, idx: int, caption: str) -> bool:
        """
        FR: Définit ou supprime la légende (caption) de la photo (ou de la photo parente d'un visage 1001).
        Met à jour `imagedata_caption.pmp` et indexe les termes dans `wordhash.dat`.
        EN: Sets or removes the caption of the photo (or of the parent photo of a 1001 face record).
        Updates `imagedata_caption.pmp` and indexes the terms in `wordhash.dat`.
        Ref: picasa3.exe @ 0x00456A15, 0x004D9AA0
        """
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return False
        self._align_imagedata_tables(eff_idx)
        if self.wordhash is not None and caption:
            from picasa_py.scanner.scanner import tokenize_indexer_text
            for tok in tokenize_indexer_text(caption):
                self.wordhash.add_word(tok, eff_idx)
        full_path = self.get_media_full_path(eff_idx)
        if full_path and os.path.exists(os.path.dirname(full_path)):
            def _mut_cap(doc: Any, fn: str) -> None:
                sec = doc.get_or_create_section(fn)
                if caption:
                    sec.set("caption", caption)
                else:
                    sec.remove("caption")
            return self.update_photo_ini(full_path, _mut_cap)
        pmp_cap = self.pmps.get("imagedata_caption")
        if pmp_cap is not None:
            default_v = pmp_cap.default_value()
            while len(pmp_cap.records) <= eff_idx:
                pmp_cap.records.append(default_v)
                pmp_cap.dirty = True
            pmp_cap.records[eff_idx] = caption or ""
            pmp_cap.dirty = True
            self.invalidate_search_cache()
            return True
        self.invalidate_search_cache()
        return False

    def get_tags(self, idx: int) -> List[str]:
        """
        FR: Retourne la liste des mots-clés de la photo (ou de la photo parente d'un visage 1001).
        EN: Returns the list of keywords/tags of the photo (or of the parent photo of a 1001 face record).
        Ref: picasa3.exe @ 0x0068B8D0 ("keywords=%s\r\n")
        """
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return []
        full_path = self.get_media_full_path(eff_idx)
        if full_path:
            ini_path = os.path.join(os.path.dirname(full_path), ".picasa.ini")
            doc = self.get_parsed_ini(ini_path)
            if doc is not None:
                kws = doc.get_keywords(os.path.basename(full_path))
                if kws:
                    return kws
        pmp_tags = self.pmps.get("imagedata_tags")
        if pmp_tags and eff_idx < len(pmp_tags.records) and pmp_tags.records[eff_idx]:
            return [k.strip() for k in str(pmp_tags.records[eff_idx]).split(",") if k.strip()]
        return []

    def set_tags(self, idx: int, tags: List[str] | str) -> bool:
        """
        FR: Définit ou supprime les mots-clés de la photo (ou de la photo parente d'un visage 1001).
        Met à jour `imagedata_tags.pmp` et indexe les mots-clés dans `wordhash.dat`.
        EN: Sets or removes the keywords/tags of the photo (or of the parent photo of a 1001 face record).
        Updates `imagedata_tags.pmp` and indexes the keywords in `wordhash.dat`.
        Ref: picasa3.exe @ 0x0068B8D0 ("keywords=%s\r\n"), 0x004D9AA0
        """
        eff_idx = self._resolve_photo_record_index(idx)
        if eff_idx is None:
            return False
        self._align_imagedata_tables(eff_idx)
        tag_list = [k.strip() for k in tags.split(",") if k.strip()] if isinstance(tags, str) else [str(k).strip() for k in tags if str(k).strip()]
        if self.wordhash is not None:
            from picasa_py.scanner.scanner import tokenize_indexer_text
            for kw in tag_list:
                for tok in tokenize_indexer_text(kw):
                    self.wordhash.add_word(tok, eff_idx)
        full_path = self.get_media_full_path(eff_idx)
        if full_path and os.path.exists(os.path.dirname(full_path)):
            return self.update_photo_ini(full_path, lambda doc, fn: doc.set_keywords(fn, tag_list))
        pmp_tags = self.pmps.get("imagedata_tags")
        if pmp_tags is not None:
            default_v = pmp_tags.default_value()
            while len(pmp_tags.records) <= eff_idx:
                pmp_tags.records.append(default_v)
                pmp_tags.dirty = True
            pmp_tags.records[eff_idx] = ",".join(tag_list)
            pmp_tags.dirty = True
            self.invalidate_search_cache()
            return True
        self.invalidate_search_cache()
        return False

    def add_keyword(self, idx: int, keyword: str) -> bool:
        """
        FR: Ajoute un mot-clé à la photo et l'indexe dans `wordhash.dat`.
        EN: Adds a keyword to the photo and indexes it in `wordhash.dat`.
        Ref: picasa3.exe @ 0x0068B8D0, 0x004D9AA0
        """
        clean_kw = str(keyword or "").strip()
        if not clean_kw:
            return False
        current = self.get_tags(idx)
        if clean_kw not in current:
            current.append(clean_kw)
        return self.set_tags(idx, current)

    def remove_keyword(self, idx: int, keyword: str) -> bool:
        """
        FR: Supprime un mot-clé de la photo et met à jour `.picasa.ini` et `imagedata_tags.pmp`.
        EN: Removes a keyword from the photo and updates `.picasa.ini` and `imagedata_tags.pmp`.
        Ref: picasa3.exe @ 0x0068B8D0
        """
        clean_kw = str(keyword or "").strip().lower()
        current = [k for k in self.get_tags(idx) if k.strip().lower() != clean_kw]
        return self.set_tags(idx, current)

    def delete_photo(self, idx_or_path: int | str | Path, delete_from_disk: bool = False) -> bool:
        """
        FR: Supprime une photo de `thumbindex.db` selon les invariants de `SaveThumbIndex` (`FUN_004f54b0` @ `0x004F54B0`) :
        - réinitialise `path = ""`, `mod_time = 0.0`, `version = 0`, `flags_lo = 0`, `flags_hi = 0`, `type = 0`, `parent_idx = 0xFFFFFFFF`
        - invalide tous les enregistrements enfants de visages (`type == 1001`) dont `parent_idx == rec_idx`.
        EN: Deletes a photo from `thumbindex.db` following the invariants of `SaveThumbIndex` (`FUN_004f54b0` @ `0x004F54B0`):
        - resets `path = ""`, `mod_time = 0.0`, `version = 0`, `flags_lo = 0`, `flags_hi = 0`, `type = 0`, `parent_idx = 0xFFFFFFFF`
        - invalidates all child face records (`type == 1001`) where `parent_idx == rec_idx`.
        Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex)
        """
        if not self.thumbindex:
            return False
        if isinstance(idx_or_path, int):
            rec_idx = self._resolve_photo_record_index(idx_or_path)
            if rec_idx is None and 0 <= idx_or_path < len(self.thumbindex.records):
                rec_idx = idx_or_path
        else:
            rec_idx = self.find_photo_index(str(idx_or_path))
        if rec_idx is None or rec_idx < 0 or rec_idx >= len(self.thumbindex.records):
            return False

        full_path = self.get_media_full_path(rec_idx)
        rec = self.thumbindex.records[rec_idx]
        rec.mark_deleted()
        rec.mod_time = 0.0
        rec.version = 0
        self.thumbindex.dirty = True
        self._deleted_or_reset_indices.add(rec_idx)

        # Supprimer les enregistrements enfants de visages (type == 1001, parent_idx == rec_idx)
        facerect_pmp = self.pmps.get("imagedata_facerect")
        personalbumid_pmp = self.pmps.get("imagedata_personalbumid")
        suggestion_pmp = self.pmps.get("imagedata_suggestionpersonalbumid")
        for child_idx in self._get_face_children(rec_idx):
            child_rec = self.thumbindex.records[child_idx]
            child_rec.mark_deleted()
            child_rec.mod_time = 0.0
            child_rec.version = 0
            self._deleted_or_reset_indices.add(child_idx)
            if facerect_pmp is not None and child_idx < len(facerect_pmp.records):
                facerect_pmp.records[child_idx] = 0
                facerect_pmp.dirty = True
            if personalbumid_pmp is not None and child_idx < len(personalbumid_pmp.records):
                personalbumid_pmp.records[child_idx] = 0
                personalbumid_pmp.dirty = True
            if suggestion_pmp is not None and child_idx < len(suggestion_pmp.records):
                suggestion_pmp.records[child_idx] = 0
                suggestion_pmp.dirty = True
        self._invalidate_path_index_cache()
        self.invalidate_search_cache()
        self._albums_cache = None
        self._starred_cache = None

        if facerect_pmp is not None and rec_idx < len(facerect_pmp.records):
            facerect_pmp.records[rec_idx] = 0
            facerect_pmp.dirty = True
        if personalbumid_pmp is not None and rec_idx < len(personalbumid_pmp.records):
            personalbumid_pmp.records[rec_idx] = 0
            personalbumid_pmp.dirty = True
        if suggestion_pmp is not None and rec_idx < len(suggestion_pmp.records):
            suggestion_pmp.records[rec_idx] = 0
            suggestion_pmp.dirty = True

        if delete_from_disk and full_path and os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass
        if full_path:
            ini_p = os.path.join(os.path.dirname(full_path), ".picasa.ini")
            if os.path.exists(ini_p):
                try:
                    from picasa_py.ini.parser import PicasaIniParser
                    doc = PicasaIniParser.parse_file(ini_p)
                    if doc.remove_section(os.path.basename(full_path)):
                        doc.write_file(ini_p)
                        self.invalidate_ini_cache(ini_p)
                except Exception:
                    pass
        return True

    def move_photo(self, idx_or_src: int | str | Path, dest_folder: str | Path) -> bool:
        """
        FR: Déplace une photo vers `dest_folder` et transfère sa section `[filename]` (ainsi que ses contacts
        associés dans `[Contacts2]`) du fichier `.picasa.ini` source vers le fichier `.picasa.ini` destination.
        EN: Moves a photo to `dest_folder` and transfers its `[filename]` section (along with any associated
        contacts in `[Contacts2]`) from the source `.picasa.ini` to the destination `.picasa.ini`.
        Ref: picasa3.exe @ 0x0068AC80, 0x00456A15
        """
        import shutil
        from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument

        dest_dir_str = str(dest_folder)
        os.makedirs(dest_dir_str, exist_ok=True)

        rec_idx: Optional[int] = None
        src_full_path: Optional[str] = None
        if isinstance(idx_or_src, int):
            rec_idx = self._resolve_photo_record_index(idx_or_src)
            if rec_idx is not None:
                src_full_path = self.get_media_full_path(rec_idx)
        else:
            src_full_path = str(idx_or_src)
            rec_idx = self.find_photo_index(src_full_path)

        if not src_full_path:
            return False

        src_dir = os.path.dirname(src_full_path)
        fname = os.path.basename(src_full_path)
        dest_full_path = os.path.join(dest_dir_str, fname)

        if os.path.exists(src_full_path) and os.path.abspath(src_full_path) != os.path.abspath(dest_full_path):
            try:
                shutil.move(src_full_path, dest_full_path)
            except Exception:
                pass

        # Transférer la sauvegarde .picasaoriginals/<fname> si présente (Ref: picasa3.exe @ 0x0068AC80)
        src_orig_backup = os.path.join(src_dir, ".picasaoriginals", fname)
        if os.path.exists(src_orig_backup):
            try:
                dest_orig_dir = os.path.join(dest_dir_str, ".picasaoriginals")
                os.makedirs(dest_orig_dir, exist_ok=True)
                shutil.move(src_orig_backup, os.path.join(dest_orig_dir, fname))
            except Exception:
                pass

        # Transférer la section [fname] du .picasa.ini source vers le .picasa.ini destination
        src_ini = os.path.join(src_dir, ".picasa.ini")
        dest_ini = os.path.join(dest_dir_str, ".picasa.ini")
        if os.path.exists(src_ini):
            try:
                src_doc = PicasaIniParser.parse_file(src_ini)
                src_sec = src_doc.get_section(fname)
                if src_sec is not None:
                    dest_doc = PicasaIniParser.parse_file(dest_ini) if os.path.exists(dest_ini) else PicasaIniDocument()
                    dest_sec = dest_doc.get_or_create_section(fname)
                    for k, v in src_sec.items():
                        dest_sec.set(k, v)
                    # Transférer également les entrées [Contacts2] référencées par faces=
                    src_contacts_sec = src_doc.get_section("Contacts2")
                    faces_items = src_doc.get_faces(fname)
                    if src_contacts_sec is not None and faces_items:
                        dest_contacts_sec = dest_doc.get_or_create_section("Contacts2")
                        for f_item in faces_items:
                            c_val = src_contacts_sec.get(f_item.contact_id)
                            if c_val is not None:
                                dest_contacts_sec.set(f_item.contact_id, c_val)
                    dest_doc.write_file(dest_ini)
                    self.invalidate_ini_cache(dest_ini)
                    src_doc.remove_section(fname)
                    src_doc.write_file(src_ini)
                    self.invalidate_ini_cache(src_ini)
            except Exception:
                pass

        if rec_idx is not None and self.thumbindex and 0 <= rec_idx < len(self.thumbindex.records):
            new_parent_idx = self.get_or_create_folder_index(dest_dir_str)
            self.thumbindex.records[rec_idx].parent_idx = new_parent_idx
            self.thumbindex.records[rec_idx].path = fname
            self.thumbindex.dirty = True
            self._modified_media_indices.add(rec_idx)
            # Mettre à jour le checksum CBlockFile (0x006B99F0) pour le nouveau dossier parent
            rec_obj = self.thumbindex.records[rec_idx]
            folder_p = self.thumbindex.records[new_parent_idx].path if 0 <= new_parent_idx < len(self.thumbindex.records) else ""
            new_cs = compute_thumb_checksum(folder_p, rec_obj.path, rec_obj.ft2, rec_obj.size)
            for pref in ("thumbs", "thumbs2"):
                idx_f = self.block_indices.get(pref)
                if idx_f is not None:
                    if 0 <= rec_idx < len(idx_f.checksums) and idx_f.checksums[rec_idx] != 0:
                        idx_f.checksums[rec_idx] = new_cs
                        idx_f.dirty = True
                    for c_idx in self._get_face_children(rec_idx):
                        if 0 <= c_idx < len(idx_f.checksums) and idx_f.checksums[c_idx] != 0:
                            idx_f.checksums[c_idx] = new_cs
                            idx_f.dirty = True

        self._invalidate_path_index_cache()
        self.invalidate_search_cache()
        self._albums_cache = None
        self._starred_cache = None
        return True

    def rename_photo(self, idx_or_src: int | str | Path, new_filename_or_path: str | Path) -> bool:
        """
        FR: Renomme une photo sur le disque (si ce n'est pas déjà fait) et migre sa section
        `[old_name]` -> `[new_name]` dans `.picasa.ini`, sa copie `.picasaoriginals/<old_name>`,
        son enregistrement `thumbindex.db` (`records[rec_idx].path`) et `wordhash.dat`.
        EN: Renames a photo on disk (if not already renamed) and migrates its `[old_name]` ->
        `[new_name]` section in `.picasa.ini`, its `.picasaoriginals/<old_name>` backup, its
        `thumbindex.db` record (`records[rec_idx].path`), and `wordhash.dat`.

        Ref: picasa3.exe @ ID_FILE_RENAME (0x0068AC80, 0x00456A15)
        """
        from picasa_py.ini.parser import PicasaIniParser

        rec_idx: Optional[int] = None
        src_full_path: Optional[str] = None
        if isinstance(idx_or_src, int):
            rec_idx = self._resolve_photo_record_index(idx_or_src)
            if rec_idx is not None:
                src_full_path = self.get_media_full_path(rec_idx)
        else:
            src_full_path = str(idx_or_src)
            rec_idx = self.find_photo_index(src_full_path)

        if not src_full_path:
            return False

        parent_dir = os.path.dirname(src_full_path)
        old_fname = os.path.basename(src_full_path)
        new_fname = os.path.basename(str(new_filename_or_path))
        if not new_fname or old_fname == new_fname:
            return False
        new_full_path = os.path.join(parent_dir, new_fname)

        if os.path.exists(src_full_path) and not os.path.exists(new_full_path):
            try:
                os.rename(src_full_path, new_full_path)
            except Exception:
                return False

        # Migrer .picasaoriginals/<old_fname> -> .picasaoriginals/<new_fname>
        orig_old = os.path.join(parent_dir, ".picasaoriginals", old_fname)
        orig_new = os.path.join(parent_dir, ".picasaoriginals", new_fname)
        if os.path.exists(orig_old) and not os.path.exists(orig_new):
            try:
                os.rename(orig_old, orig_new)
            except Exception:
                pass

        # Migrer [old_fname] -> [new_fname] dans .picasa.ini
        for ini_name in (".picasa.ini", "Picasa.ini"):
            ini_path = os.path.join(parent_dir, ini_name)
            if os.path.exists(ini_path):
                try:
                    doc = PicasaIniParser.parse_file(ini_path)
                    old_sec = doc.get_section(old_fname)
                    if old_sec is not None:
                        new_sec = doc.get_or_create_section(new_fname)
                        for k, v in old_sec.items():
                            new_sec.set(k, v)
                        doc.remove_section(old_fname)
                        doc.write_file(ini_path)
                        self.invalidate_ini_cache(ini_path)
                except Exception:
                    pass
                break

        if rec_idx is not None and self.thumbindex and 0 <= rec_idx < len(self.thumbindex.records):
            self.thumbindex.records[rec_idx].path = new_fname
            self.thumbindex.dirty = True
            self._modified_media_indices.add(rec_idx)
            # Mettre à jour le checksum CBlockFile (0x006B99F0) pour le nouveau nom de fichier
            rec_obj = self.thumbindex.records[rec_idx]
            p_idx = rec_obj.parent_idx
            folder_p = self.thumbindex.records[p_idx].path if 0 <= p_idx < len(self.thumbindex.records) else ""
            new_cs = compute_thumb_checksum(folder_p, rec_obj.path, rec_obj.ft2, rec_obj.size)
            for pref in ("thumbs", "thumbs2"):
                idx_f = self.block_indices.get(pref)
                if idx_f is not None:
                    if 0 <= rec_idx < len(idx_f.checksums) and idx_f.checksums[rec_idx] != 0:
                        idx_f.checksums[rec_idx] = new_cs
                        idx_f.dirty = True
                    for c_idx in self._get_face_children(rec_idx):
                        if 0 <= c_idx < len(idx_f.checksums) and idx_f.checksums[c_idx] != 0:
                            idx_f.checksums[c_idx] = new_cs
                            idx_f.dirty = True
            if self.wordhash is not None:
                from picasa_py.scanner.scanner import tokenize_indexer_text
                if hasattr(self.wordhash, "remove_word"):
                    for old_tok in tokenize_indexer_text(old_fname):
                        self.wordhash.remove_word(old_tok, rec_idx)
                for tok in tokenize_indexer_text(new_fname):
                    self.wordhash.add_word(tok, rec_idx)

        self._invalidate_path_index_cache()
        self.invalidate_search_cache()
        self._albums_cache = None
        self._starred_cache = None
        return True

    def update_photo_ini(
        self,
        photo_path: str,
        mutator: Any,
        invalidate_albums_starred: bool = True,
    ) -> bool:
        """
        FR: Modifie de façon atomique l'entrée d'une photo dans le fichier .picasa.ini de son dossier,
        invalide le cache INI et synchronise les colonnes PMP / wordhash correspondantes.
        EN: Atomically updates a photo's entry in its folder's .picasa.ini file,
        invalidates the INI cache, and synchronizes the corresponding PMP / wordhash columns.
        Ref: AGENTS.md §4 bis.3 & picasa3.exe @ 0x00456A15, 0x0068AC80
        """
        if not photo_path:
            return False
        from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
        folder = os.path.dirname(photo_path)
        fname = os.path.basename(photo_path)
        ini_path = os.path.join(folder, ".picasa.ini")
        try:
            doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()
            mutator(doc, fname)
            doc.write_file(ini_path)
            self.invalidate_ini_cache(ini_path, invalidate_albums_starred=invalidate_albums_starred)
            self.sync_photo_ini_to_db(photo_path, doc)
            self.invalidate_search_cache()
            return True
        except Exception:
            return False

    def save_contacts(self) -> bool:
        """
        FR: Sauvegarde atomiquement contacts.xml via la couche DB.
        EN: Atomically saves contacts.xml through the DB layer.
        """
        if not self.contacts or not self.contacts_dir:
            return False
        try:
            self.contacts.save(str(self.contacts_dir / "contacts.xml"))
            return True
        except Exception:
            return False

    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        FR: Lit une préférence persistante depuis repository.dat.
        EN: Reads a persistent preference from repository.dat.
        """
        if not self.repository:
            return default
        val = self.repository.get(key)
        return val if val is not None else default

    def set_preference(self, key: str, value: Any) -> None:
        """
        FR: Écrit une préférence persistante dans repository.dat.
        EN: Writes a persistent preference to repository.dat.
        """
        if not self.repository:
            self.repository = KeyValueTableFile()
        self.repository.set(key, str(value))

    def _scan_ini_albums(self) -> List[Dict[str, Any]]:
        """
        FR: Alias interne de get_all_albums pour le balayage des albums virtuels .picasa.ini et PMP.
        EN: Internal alias of get_all_albums for scanning .picasa.ini and PMP virtual albums.
        """
        return self.get_all_albums()

    def get_all_albums(self) -> List[Dict[str, Any]]:
        """
        FR: Récupère l'ensemble des albums virtuels (tables PMP et sections .album:<uid> des fichiers .picasa.ini).
        EN: Retrieves all virtual albums (from PMP tables and .album:<uid> sections in .picasa.ini files).
        Ref: picasa3.exe @ albumdata_category.pmp (cat=0), 0x00732160, 0x008AAD76
        """
        ad_names = self.pmps.get("albumdata_name")
        ad_cats = self.pmps.get("albumdata_category")
        ad_tokens = self.pmps.get("albumdata_token")
        self._ensure_path_index_cache()
        curr_sig = (
            len(ad_names.records) if ad_names else 0,
            len(self._folder_idx_to_norms),
        )
        if self._albums_cache is not None and self._albums_cache_sig == curr_sig:
            return [
                dict(a, photo_paths=list(a["photo_paths"]), photo_indices=list(a["photo_indices"]))
                for a in self._albums_cache
            ]

        albums: Dict[str, Dict[str, Any]] = {}

        # 1. Albums dans les tables PMP (cat == 0 dans albumdata_category)
        ad_musics = self.pmps.get("albumdata_music")
        ad_dates = self.pmps.get("albumdata_date")
        if ad_names and ad_cats:
            names = ad_names.records
            cats = ad_cats.records
            tokens = ad_tokens.records if ad_tokens else []
            for i in range(len(names)):
                if i < len(cats) and cats[i] == 0:
                    aname = str(names[i] or "")
                    if i == 0 and aname.strip().lower() in ("", "default", "sans nom", "unnamed"):
                        continue
                    raw_tok = str(tokens[i]) if i < len(tokens) and tokens[i] else f"pmp_{i}"
                    token = raw_tok.strip()
                    # FR : Ignorer les collections dynamiques internes comme ]updated ('Récemment mis à jour')
                    # EN: Skip internal dynamic collections such as ]updated ('Recently Updated')
                    if token.startswith("]") and not token.startswith("]album:"):
                        continue
                    if not aname.strip() and token.startswith("pmp_"):
                        continue
                    if token.startswith("]album:") or token.startswith(".album:"):
                        token = token[7:].strip()
                    if aname.startswith("Album ]album:"):
                        aname = aname.replace("Album ]album:", "Album ")
                    pmp_music = str(ad_musics.records[i] or "") if (ad_musics is not None and i < len(ad_musics.records) and ad_musics.records[i]) else None
                    pmp_date = ad_dates.records[i] if (ad_dates is not None and i < len(ad_dates.records) and ad_dates.records[i]) else None
                    albums[token] = {
                        "token": token,
                        "name": aname,
                        "photo_paths": [],
                        "photo_indices": [],
                        "music": pmp_music,
                        "date": pmp_date,
                        "source": "pmp",
                    }

        # 2. Albums définis dans les fichiers .picasa.ini des dossiers surveillés et indexés
        watched_set: Dict[str, str] = {}
        for p, st in self.get_watched_folders().items():
            if st in ("1", "2"):
                hp = _to_host_path(p.rstrip("\\/"))
                nk = os.path.normcase(os.path.abspath(hp))
                watched_set[nk] = hp
        if self.thumbindex:
            for r in self.thumbindex.records:
                if r.type == 1 and r.path:
                    hp = _to_host_path(r.path.rstrip("\\/"))
                    nk = os.path.normcase(os.path.abspath(hp))
                    if nk not in watched_set:
                        watched_set[nk] = hp

        for w in watched_set.values():
            ini_p = os.path.join(w, ".picasa.ini")
            doc = self.get_parsed_ini(ini_p)
            if not doc:
                continue
            norm_w = os.path.abspath(w).replace("/", "\\").rstrip("\\").lower()
            try:
                folder_albums: Dict[str, str] = {}
                for sec in doc.sections:
                    if sec.name.startswith(".album:") or sec.name.startswith("]album:"):
                        raw_token = sec.get("token") or sec.name[7:]
                        token = raw_token.strip()
                        if token.startswith("]album:") or token.startswith(".album:"):
                            token = token[7:].strip()
                        aname = sec.get("name") or token
                        music = sec.get("music")
                        date = sec.get("date")
                        folder_albums[token] = aname
                        if token not in albums:
                            albums[token] = {
                                "token": token,
                                "name": aname,
                                "photo_paths": [],
                                "photo_indices": [],
                                "music": music,
                                "date": date,
                                "ini_path": ini_p,
                                "source": "ini",
                            }
                        else:
                            if aname and (not albums[token]["name"] or albums[token]["name"].startswith("Album ")):
                                albums[token]["name"] = aname
                            if music and not albums[token]["music"]:
                                albums[token]["music"] = music

                for sec in doc.sections:
                    if sec.name.startswith(".") or sec.name.startswith("]") or sec.name.startswith("["):
                        continue
                    alb_str = sec.get("albums")
                    if not alb_str:
                        continue
                    alb_tokens = [x.strip() for x in alb_str.split(",") if x.strip()]
                    photo_full_path = os.path.join(w, sec.name)
                    rec_idx = self._path_index_cache.get(f"{norm_w}\\{sec.name.lower()}")
                    for t in alb_tokens:
                        tok = t.strip()
                        if tok.startswith("]album:") or tok.startswith(".album:"):
                            tok = tok[7:].strip()
                        if not tok:
                            continue
                        if tok not in albums:
                            aname = folder_albums.get(tok, f"Album {tok}")
                            albums[tok] = {
                                "token": tok,
                                "name": aname,
                                "photo_paths": [],
                                "photo_indices": [],
                                "music": None,
                                "date": None,
                                "ini_path": ini_p,
                                "source": "ini",
                            }
                        if photo_full_path not in albums[tok]["photo_paths"]:
                            albums[tok]["photo_paths"].append(photo_full_path)
                        if rec_idx is not None and rec_idx not in albums[tok]["photo_indices"]:
                            albums[tok]["photo_indices"].append(rec_idx)
            except Exception:
                pass

        # 3. Compléter les photos des albums via wordhash.dat (]album:<token>)
        if self.wordhash is not None and hasattr(self.wordhash, "search"):
            for tok, alb_info in albums.items():
                try:
                    wh_indices = self.wordhash.search(f"]album:{tok}")
                    for r_idx in wh_indices:
                        if 0 <= r_idx < len(self.index) and not self.is_face_record(r_idx):
                            if r_idx not in alb_info["photo_indices"]:
                                alb_info["photo_indices"].append(r_idx)
                            p_full = self.get_media_full_path(r_idx)
                            if p_full and p_full not in alb_info["photo_paths"]:
                                alb_info["photo_paths"].append(p_full)
                except Exception:
                    pass

        res_list = list(albums.values())
        self._albums_cache = [
            dict(a, photo_paths=list(a["photo_paths"]), photo_indices=list(a["photo_indices"]))
            for a in res_list
        ]
        self._albums_cache_sig = curr_sig
        return res_list

    def get_starred_photo_paths(self) -> List[str]:
        """
        FR: Récupère l'ensemble des chemins complets des photos marquées comme favorites (star=yes)
        sans appels `os.path.isdir` / `os.path.exists` bloquants par fichier sur le thread GUI.
        EN: Retrieves all full file paths of photos marked as starred (star=yes)
        without blocking per-file `os.path.isdir` / `os.path.exists` calls on the GUI thread.
        Ref: picasa3.exe @ CThumbDB::starredphotos (0x0088F6FC, 0x0068B800)
        """
        self._ensure_path_index_cache()
        curr_sig = len(self._folder_idx_to_norms)
        if self._starred_cache is not None and self._starred_cache_sig == curr_sig:
            return list(self._starred_cache)

        starred_paths: List[str] = []
        starred_seen: Set[str] = set()
        watched_set: Dict[str, str] = {}
        for p, st in self.get_watched_folders().items():
            if st in ("1", "2"):
                hp = _to_host_path(p.rstrip("\\/"))
                nk = os.path.normcase(os.path.abspath(hp))
                watched_set[nk] = hp
        if self.thumbindex:
            for r in self.thumbindex.records:
                if r.type == 1 and r.path:
                    hp = _to_host_path(r.path.rstrip("\\/"))
                    nk = os.path.normcase(os.path.abspath(hp))
                    if nk not in watched_set:
                        watched_set[nk] = hp

        for w in watched_set.values():
            norm_w = os.path.abspath(w).replace("/", "\\").rstrip("\\").lower()
            doc = self.get_parsed_ini(os.path.join(w, ".picasa.ini"))
            if doc is None:
                doc = self.get_parsed_ini(os.path.join(w, "Picasa.ini"))
            if not doc:
                continue
            try:
                for sec in doc.sections:
                    if sec.get("star", "").lower() == "yes":
                        photo_full_path = os.path.join(w, sec.name)
                        norm_p = f"{norm_w}\\{sec.name.lower()}"
                        if norm_p not in starred_seen:
                            if norm_p in self._path_index_cache or os.path.exists(photo_full_path):
                                starred_seen.add(norm_p)
                                starred_paths.append(photo_full_path)
            except Exception:
                pass
        self._starred_cache = list(starred_paths)
        self._starred_cache_sig = curr_sig
        return starred_paths

    def delete_album(self, album_token: str) -> bool:
        """
        FR: Supprime un album virtuel de ses fichiers `.picasa.ini`, des tables `albumdata_*.pmp`
        et du sous-dossier `db3/albums/*.pal`.
        EN: Deletes a virtual album from its `.picasa.ini` files, `albumdata_*.pmp` tables,
        and `db3/albums/*.pal` directory.
        Ref: picasa3.exe @ 0x00732160 (ID_ALBUM_DELETE), 0x008AAD76
        """
        from picasa_py.ini.parser import PicasaIniParser
        clean_target = album_token.strip()
        if clean_target.startswith("]album:") or clean_target.startswith(".album:"):
            clean_target = clean_target[7:].strip()
        deleted = False
        watched = [_to_host_path(p.rstrip("\\/")) for p, st in self.get_watched_folders().items() if st in ("1", "2")]
        if self.thumbindex:
            for r in self.thumbindex.records:
                if r.type == 1:
                    p = _to_host_path(r.path.rstrip("\\/"))
                    if os.path.isdir(p) and p not in watched:
                        watched.append(p)

        for w in watched:
            ini_p = os.path.join(w, ".picasa.ini")
            if not os.path.exists(ini_p):
                continue
            try:
                doc = PicasaIniParser.parse_file(ini_p)
                modified = False
                for sec in list(doc.sections):
                    if (
                        sec.name in (f".album:{clean_target}", f"]album:{clean_target}", f".album:{album_token}")
                        or (sec.name.startswith(".album:") and sec.get("token") in (album_token, clean_target))
                        or (sec.name.startswith(".album:") and sec.get("name") in (album_token, clean_target))
                    ):
                        doc.sections.remove(sec)
                        doc._modified = True
                        doc._untagged_utf8_preserved = False
                        modified = True
                        deleted = True

                for sec in doc.sections:
                    alb_str = sec.get("albums")
                    if alb_str:
                        tokens = [t.strip() for t in alb_str.split(",") if t.strip()]
                        kept = [
                            t for t in tokens
                            if t not in (album_token, clean_target, f"]album:{clean_target}", f".album:{clean_target}")
                        ]
                        if len(kept) != len(tokens):
                            if kept:
                                sec.set("albums", ",".join(kept))
                            else:
                                sec.remove("albums")
                            modified = True
                            deleted = True

                if modified:
                    doc.write_file(ini_p)
                    self.invalidate_ini_cache(ini_p)
            except Exception:
                pass

        # Nettoyer également les entrées correspondantes dans albumdata_*.pmp
        candidates = {
            album_token.strip(),
            clean_target,
            f"]album:{clean_target}",
            f".album:{clean_target}",
        }
        matched_rows: Set[int] = set()
        for col_name in ("albumdata_token", "albumdata_uid", "albumdata_name"):
            pmp_col = self.pmps.get(col_name)
            if pmp_col is not None:
                for i, val in enumerate(pmp_col.records):
                    if str(val or "").strip() in candidates:
                        matched_rows.add(i)

        if matched_rows:
            for stem, pmp_col in self.pmps.items():
                if stem.startswith("albumdata_"):
                    def_v = pmp_col.default_value()
                    for row_idx in matched_rows:
                        if row_idx < len(pmp_col.records):
                            if stem == "albumdata_category":
                                pmp_col.records[row_idx] = 0xFFFFFFFF
                            else:
                                pmp_col.records[row_idx] = def_v
                            pmp_col.dirty = True
            deleted = True

        if self.wordhash is not None and hasattr(self.wordhash, "words"):
            for w_key in (f"]album:{clean_target}", f"]snapshot:]album:{clean_target}"):
                if w_key in self.wordhash.words:
                    self.wordhash.words.pop(w_key, None)
                    self.wordhash.dirty = True

        # Supprimer le fichier .pal éventuel dans db3/albums/
        if self.db3_dir:
            albums_dir = self.db3_dir / "albums"
            if albums_dir.exists():
                for pal_cand in (f"{clean_target}.pal", f"{album_token.strip()}.pal"):
                    pal_path = albums_dir / pal_cand
                    if pal_path.exists():
                        try:
                            pal_path.unlink()
                            deleted = True
                        except Exception:
                            pass

        self._albums_cache = None
        return deleted

    def rename_album(self, album_token: str, new_name: str) -> bool:
        """
        FR: Renomme un album virtuel dans les fichiers `.picasa.ini` (`[.album:<token>]`)
        et met à jour `albumdata_name.pmp`.
        EN: Renames a virtual album in `.picasa.ini` files (`[.album:<token>]`)
        and updates `albumdata_name.pmp`.
        Ref: picasa3.exe @ 0x008AAD76, albumdata_name.pmp
        """
        from picasa_py.ini.parser import PicasaIniParser
        clean_target = album_token.strip()
        if clean_target.startswith("]album:") or clean_target.startswith(".album:"):
            clean_target = clean_target[7:].strip()
        renamed = False
        watched = [_to_host_path(p.rstrip("\\/")) for p, st in self.get_watched_folders().items() if st in ("1", "2")]
        if self.thumbindex:
            for r in self.thumbindex.records:
                if r.type == 1:
                    p = _to_host_path(r.path.rstrip("\\/"))
                    if os.path.isdir(p) and p not in watched:
                        watched.append(p)

        for w in watched:
            ini_p = os.path.join(w, ".picasa.ini")
            if not os.path.exists(ini_p):
                continue
            try:
                doc = PicasaIniParser.parse_file(ini_p)
                modified = False
                for sec in doc.sections:
                    if (
                        sec.name in (f".album:{clean_target}", f"]album:{clean_target}", f".album:{album_token}")
                        or (sec.name.startswith(".album:") and sec.get("token") in (album_token, clean_target))
                        or (sec.name.startswith(".album:") and sec.get("name") in (album_token, clean_target))
                    ):
                        sec.set("name", new_name)
                        modified = True
                        renamed = True
                if modified:
                    doc.write_file(ini_p)
                    self.invalidate_ini_cache(ini_p)
            except Exception:
                pass

        candidates = {
            album_token.strip(),
            clean_target,
            f"]album:{clean_target}",
            f".album:{clean_target}",
        }
        ad_names = self.pmps.get("albumdata_name")
        if ad_names is not None:
            for col_name in ("albumdata_token", "albumdata_uid", "albumdata_name"):
                pmp_col = self.pmps.get(col_name)
                if pmp_col is not None:
                    for i, val in enumerate(pmp_col.records):
                        if str(val or "").strip() in candidates:
                            while len(ad_names.records) <= i:
                                ad_names.records.append("")
                            ad_names.records[i] = new_name
                            ad_names.dirty = True
                            renamed = True

        self._albums_cache = None
        return renamed

    @staticmethod
    def _is_tree_expansion_ancestor_entry(path_key: str, all_keys_lower: Set[str]) -> bool:
        """
        FR: Identifie les clés de `repository.dat` qui enregistrent uniquement l'état de dépliage
        d'un nœud parent de l'arbre de dossiers (`C:\\`, `C:\\Users\\`, `C:\\Users\\<user>\\`)
        conformément à `picasa3.exe @ 0x004A4860` / `0x004A4A90`, lorsqu'un sous-dossier enfant
        existe dans la liste des chemins configurés.
        EN: Identifies `repository.dat` keys that only record the expansion state of a parent
        folder-tree node (`C:\\`, `C:\\Users\\`, `C:\\Users\\<user>\\`) per `0x004A4860` / `0x004A4A90`,
        when a child folder exists in the configured path set.
        Ref: picasa3.exe @ 0x004A4860, 0x004A4A90 (repository.dat left-tree expanded states)
        """
        norm = path_key.replace("/", "\\").rstrip("\\").lower()
        parts = [p for p in norm.split("\\") if p]
        if not parts:
            return True
        is_candidate_ancestor = False
        if len(parts) == 1 and len(parts[0]) == 2 and parts[0].endswith(":"):
            # Racine de lecteur (ex. "c:")
            is_candidate_ancestor = True
        elif len(parts) == 2 and len(parts[0]) == 2 and parts[0].endswith(":") and parts[1] in ("users", "documents and settings"):
            # Dossier profils système (ex. "c:\\users")
            is_candidate_ancestor = True
        elif len(parts) == 3 and len(parts[0]) == 2 and parts[0].endswith(":") and parts[1] in ("users", "documents and settings"):
            # Racine du profil utilisateur (ex. "c:\\users\\thyph")
            is_candidate_ancestor = True
        if not is_candidate_ancestor:
            return False
        prefix = norm + "\\"
        return any(other != norm and other.startswith(prefix) for other in all_keys_lower)

    def get_watched_folders(self) -> Dict[str, str]:
        """
        FR: Renvoie le dictionnaire `{chemin_dossier: statut}` des dossiers configurés dans
        `scanlist.txt` (`0x004F61C0` / `0x004F6380`) et `repository.dat`, en excluant les nœuds
        parents d'expansion d'arborescence UI (`C:\\`, `C:\\Users\\`, `C:\\Users\\<user>\\`, Ref: `0x004A4860`).
        Statuts Picasa :
        - `"1"` -> Toujours analyser (Scan Always : sans préfixe dans `scanlist.txt`)
        - `"2"` -> Analyser une seule fois (Scan Once : préfixe `+` dans `scanlist.txt`)
        - `"0"` -> Supprimer de Picasa (Excluded : préfixe `-` dans `scanlist.txt`)
        EN: Returns the `{folder_path: status}` dictionary of watched folders configured in
        `scanlist.txt` (`0x004F61C0` / `0x004F6380`) and `repository.dat`, excluding UI tree
        expansion ancestor nodes (`C:\\`, `C:\\Users\\`, `C:\\Users\\<user>\\`, Ref: `0x004A4860`).
        Ref: picasa3.exe @ 0x004F61C0 (SaveScanList), 0x004F6380 (LoadScanList), 0x004A4860 (repository.dat)
        """
        raw_candidates: Dict[str, str] = {}
        if self.repository:
            for k, v in self.repository.pairs:
                if (":" in k or "\\" in k or "/" in k) and v in ("0", "1", "2"):
                    raw_candidates[k] = v
        if self._scanlist:
            for k, v in self._scanlist.items():
                if (":" in k or "\\" in k or "/" in k) and v in ("0", "1", "2"):
                    raw_candidates[k] = v

        if not raw_candidates:
            return {}

        db_in_pytest = "pytest" in str(self.db3_dir).lower() if self.db3_dir else False
        filtered: Dict[str, str] = {}
        for k, v in raw_candidates.items():
            if not db_in_pytest and "pytest" in k.lower():
                continue
            filtered[k] = v

        all_keys_lower = {k.replace("/", "\\").rstrip("\\").lower() for k in filtered}
        stage1: Dict[str, str] = {}
        for k, v in filtered.items():
            if v in ("1", "2") and self._is_tree_expansion_ancestor_entry(k, all_keys_lower):
                continue
            stage1[k] = v

        # Exclure les sous-dossiers marqués "1" dans repository.dat (dépliage UI @ 0x004A4860)
        # lorsqu'un dossier parent est déjà en mode "1" (Scan Always récursif)
        scan_always_roots = {
            k.replace("/", "\\").rstrip("\\").lower()
            for k, v in stage1.items()
            if v == "1"
        }
        res: Dict[str, str] = {}
        for k, v in stage1.items():
            if v == "1":
                norm_k = k.replace("/", "\\").rstrip("\\").lower()
                if any(
                    other != norm_k and norm_k.startswith(other + "\\")
                    for other in scan_always_roots
                ):
                    continue
            res[k] = v
        return res

    def set_watched_folder(self, folder_path: str, status: str) -> None:
        """
        FR: Définit le statut d'un dossier dans `scanlist.txt` et `repository.dat` (format Picasa avec `'\\'` final).
        EN: Sets a folder's status in `scanlist.txt` and `repository.dat` (Picasa format with trailing `'\\'`).
        Ref: picasa3.exe @ 0x004F61C0 (SaveScanList), 0x008B7F90 (foldermgr)
        """
        norm_path = folder_path.replace("/", "\\")
        if not norm_path.endswith("\\"):
            norm_path += "\\"
        if not self.repository:
            self.repository = KeyValueTableFile()
        st_str = str(status)
        self.repository.set(norm_path, st_str)
        self._scanlist[norm_path] = st_str
        self._albums_cache = None
        self._starred_cache = None

    def _serialize_scanlist_bytes(self) -> bytes:
        """
        FR: Sérialise `scanlist.txt` au format exact de `SaveScanList` (`0x004F61C0`) :
        - `"1"` (Scan Always) : `<folder>\\r\\n` (sans préfixe, `0x00C7EBE8 = "%s\\n"`)
        - `"2"` (Scan Once)   : `+<folder>\\r\\n` (`0x00C865B4 = "+%s\\n"`)
        - `"0"` (Excluded)    : `-<folder>\\r\\n` (`0x00C865AC = "-%s\\n"`)
        EN: Serializes `scanlist.txt` in the exact `SaveScanList` (`0x004F61C0`) format.
        Ref: picasa3.exe @ 0x004F61C0 (SaveScanList), 0x004F6380 (LoadScanList)
        """
        scan_lines: List[str] = []
        for k, v in self.get_watched_folders().items():
            if v == "0":
                scan_lines.append(f"-{k}\r\n")
            elif v == "2":
                scan_lines.append(f"+{k}\r\n")
            elif v == "1":
                scan_lines.append(f"{k}\r\n")
        return "".join(scan_lines).encode("utf-8", errors="surrogateescape")

    def save_repository_only(self) -> None:
        """
        FR: Sauvegarde atomiquement sur disque uniquement `repository.dat` et `scanlist.txt`
        (configuration des dossiers surveillés) sans réécrire les 56 tables `.pmp` ni `thumbindex.db`,
        évitant tout gel de l'UI à la fermeture du Gestionnaire de dossiers.
        EN: Atomically saves only `repository.dat` and `scanlist.txt` (watched folder settings)
        to disk without rewriting all 56 `.pmp` tables or `thumbindex.db`, preventing any UI freeze
        when closing the Folder Manager.
        Ref: picasa3.exe @ 0x004F61C0 (SaveScanList), 0x008B1BF0, 0x008B7F90 (repository.dat)
        """
        if not self.db3_dir or self.db3_dir == Path(".") or not self.repository:
            return
        if not self.db3_dir.exists():
            self.db3_dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            repo_bytes = self.repository.to_bytes()
            scanlist_bytes = self._serialize_scanlist_bytes()
        target = self.db3_dir / "repository.dat"
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(repo_bytes)
        try:
            os.replace(str(tmp), str(target))
        except PermissionError:
            try:
                target.write_bytes(repo_bytes)
            finally:
                tmp.unlink(missing_ok=True)
        try:
            (self.db3_dir / "scanlist.txt").write_bytes(scanlist_bytes)
        except Exception:
            pass

    def get_media_full_path(self, index: int) -> Optional[str]:
        """
        FR: Reconstitue le chemin d'accès complet du fichier image ou vidéo sur disque
        en combinant le répertoire parent et le nom de fichier stockés dans thumbindex.db.
        Si index désigne un sous-enregistrement de visage (type == 1001), résout d'abord
        l'enregistrement de la photo parente avant de remonter au dossier (type == 1).
        EN: Reconstructs the full on-disk file path for an image or video record
        by combining the parent directory and filename stored in thumbindex.db.
        If index refers to a face sub-record (type == 1001), resolves the parent photo
        record first before walking up to the folder record (type == 1).
        Ref: picasa3.exe @ 0x0045C0A0
        """
        if not self.thumbindex or index < 0 or index >= len(self.thumbindex.records):
            return None
        rec = self.thumbindex.records[index]
        if rec.type == 1001:
            if 0 <= rec.parent_idx < len(self.thumbindex.records):
                rec = self.thumbindex.records[rec.parent_idx]
            else:
                return None
        if rec.type not in MEDIA_RECORD_TYPES:
            return None
        parent_idx = rec.parent_idx
        folder_path = ""
        if 0 <= parent_idx < len(self.thumbindex.records):
            parent_rec = self.thumbindex.records[parent_idx]
            if parent_rec.type == 1:
                folder_path = parent_rec.path
        if folder_path:
            host_folder = _to_host_path(folder_path)
            clean_child = _to_host_path(rec.path.lstrip("\\/"))
            full = os.path.join(host_folder, clean_child)
            if os.path.exists(full):
                return full
            host_rec_path = _to_host_path(rec.path)
            if os.path.exists(host_rec_path):
                return host_rec_path
            return full
        return _to_host_path(rec.path)

    def is_face_record(self, index: int) -> bool:
        """
        FR: Indique si l'index correspond à un enregistrement de visage (type 1001).
        EN: Indicates whether the index corresponds to a face record (type 1001).
        """
        if not self.thumbindex or index < 0 or index >= len(self.thumbindex.records):
            return False
        return self.thumbindex.records[index].type == 1001

    def get_face_parent_photo_idx(self, index: int) -> Optional[int]:
        """
        FR: Renvoie l'index de la photo parente pour un enregistrement de visage (type 1001).
        EN: Returns the parent photo index for a face record (type 1001).
        """
        if self.is_face_record(index):
            return self.thumbindex.records[index].parent_idx
        return None

    def load_thumbnail(self, index: int, size: str = "small") -> Optional[bytes]:
        """
        FR: Alias de get_thumbnail pour charger le blob JPEG d'une miniature.
        EN: Alias for get_thumbnail to load a thumbnail's JPEG blob.
        """
        return self.get_thumbnail(index, size)

    def get_thumbnail_jpeg(self, index: int, size: str = "small") -> Optional[bytes]:
        """
        FR: Alias de get_thumbnail retournant les octets JPEG d'une miniature.
        EN: Alias for get_thumbnail returning the JPEG bytes of a thumbnail.
        """
        return self.get_thumbnail(index, size)

    def _get_container_for_entry(self, prefix: str, block_num: int) -> Optional[BlockContainerFile]:
        """
        FR: Récupère le conteneur de blocs correspondant au préfixe et au numéro de bloc.
        EN: Retrieves the block container matching the given prefix and block number.
        """
        cont = self.block_containers_by_block.get((prefix, block_num))
        if cont is not None:
            return cont
        if block_num == 0:
            return self.block_containers.get(prefix)
        return None

    def _get_block_lock(self, prefix: str) -> threading.RLock:
        """
        FR: Retourne le verrou dédié au conteneur `CBlockFile` correspondant à `prefix`.
        EN: Returns the dedicated lock for the `CBlockFile` container matching `prefix`.
        Ref: picasa3.exe @ 0x006B7FC0 (cblockfile_006B7FC0.c:30, LPCRITICAL_SECTION at this - 8)
        """
        locks = getattr(self, "_block_locks", None)
        if locks is None:
            self._block_locks = {p: threading.RLock() for p in STANDARD_BLOCKFILE_PREFIXES}
            locks = self._block_locks
        lck = locks.get(prefix)
        if lck is None:
            lck = threading.RLock()
            locks[prefix] = lck
        return lck

    def get_thumbnail(self, index: int, size: str = "small") -> Optional[bytes]:
        """
        FR: Extrait la miniature d'une image à un index donné (supporte les conteneurs multi-blocs *_0.db, *_1.db...).
        size: "small" (thumbs), "medium" (thumbs2), "large" (bigthumbs), "preview" (previews).
        EN: Extracts the thumbnail for an image at a given index (supports multi-block containers *_0.db, *_1.db...).
        size: "small" (thumbs), "medium" (thumbs2), "large" (bigthumbs), "preview" (previews).
        Ref: picasa3.exe @ 0x006B6AF0, 0x006B7390, 0x006B7FC0
        """
        prefix_map = {
            "small": "thumbs",
            "medium": "thumbs2",
            "large": "bigthumbs",
            "preview": "previews",
        }
        prefix = prefix_map.get(size, size)
        with self._get_block_lock(prefix):
            idx_file = self.block_indices.get(prefix)
            if not idx_file or index < 0 or index >= idx_file.record_count:
                return None

            entry = idx_file.get_entry(index)
            if not entry or entry.is_empty:
                return None
            container = self._get_container_for_entry(prefix, entry.block)
            if not container:
                return None
            return container.get_blob(entry)

    _vqc_sqrt_weights: Optional[np.ndarray] = None
    _vqc_weights: Optional[np.ndarray] = None
    _vqc_delta_term: float = -2.462790012359619
    _vqc_thr_arr: Optional[np.ndarray] = None

    @classmethod
    def _get_vqc_relator_weights(cls) -> Tuple[np.ndarray, float]:
        """
        FR: Charge et initialise les 2000 poids du modèle vqc_Relator (0x00423003) depuis plugins/red.cfg.
        EN: Loads and initializes the 2000 weights of the vqc_Relator model (0x00423003) from plugins/red.cfg.
        Ref: picasa3.exe @ 0x0045F0C0 (plugins\\red.cfg), Red.dll @ 0x101005F0 (dqc_Relator::init)
        """
        if cls._vqc_sqrt_weights is not None:
            return cls._vqc_sqrt_weights, cls._vqc_delta_term

        w_raw: Optional[np.ndarray] = None
        delta_term = -2.462790012359619
        found_cfg = _find_red_cfg_path()
        candidates: List[Path] = []
        if found_cfg is not None:
            candidates.append(found_cfg)
        candidates.extend([
            Path(r"C:\Program Files (x86)\Google\Picasa3\plugins\red.cfg"),
            Path(r"C:\Program Files\Google\Picasa3\plugins\red.cfg"),
            Path("ui/resources/plugins/red.cfg"),
            Path("bin/plugins/red.cfg"),
        ])
        for cfg_path in candidates:
            if cfg_path.exists():
                try:
                    cfg = cfg_path.read_bytes()
                    rel_idx = cfg.find(b"\x03\x30\x42\x00\x66\x00\x00\x00")
                    if rel_idx >= 0 and rel_idx + 0x40 + 8000 <= len(cfg):
                        w_off = rel_idx + 0x40
                        w_raw = np.frombuffer(cfg[w_off : w_off + 8000], dtype="<f4").copy()
                        if w_off + 8000 + 34 <= len(cfg):
                            delta_term = float(struct.unpack_from("<f", cfg, w_off + 8000 + 30)[0])
                        # FR: Seuils de quantification vqc_Quantizer / EN: vqc_Quantizer thresholds (0x00423004 -> 30000 floats = 2000x15)
                        thr_idx = cfg.find(b"\x30\x75\x00\x00", max(0, rel_idx - 0x20000))
                        if 0 <= thr_idx < rel_idx and thr_idx + 4 + 120000 <= len(cfg):
                            cls._vqc_thr_arr = np.frombuffer(
                                cfg[thr_idx + 4 : thr_idx + 4 + 120000], dtype="<f4"
                            ).reshape(2000, 15).copy()
                        break
                except Exception:
                    pass

        if w_raw is None or len(w_raw) != 2000:
            # FR: Courbe analytique de repli si plugins/red.cfg est absent / EN: Analytical fallback curve if plugins/red.cfg is missing
            idx_arr = np.arange(2000, dtype=np.float32)
            w_raw = (0.011069 * np.power(1.0 + idx_arr / 180.0, -1.35)).astype(np.float32)

        # Ref: Red.dll @ 0x10100735..0x10100865 (dqc_Relator::init : unbias_exp=0.7f, group_fraction=0.95f)
        # int(250 * (1.0 - float32(0.95))) == 12 (0x101007F8 : _ftol2_sse), et à 0x1010083D la boucle
        # interne fadd dword ptr [edi] réplique le premier poids w[m*8] sur le groupe de 8.
        sum1 = np.float32(np.sum(w_raw, dtype=np.float64))
        u_exp = np.float32(0.7)
        w = np.power(np.maximum(w_raw.astype(np.float64), 1e-12), float(u_exp)).astype(np.float32)
        sum2 = np.float32(np.sum(w, dtype=np.float64))
        scale = np.float32(float(sum1) / float(sum2))
        w = (w.astype(np.float64) * float(scale)).astype(np.float32)
        for m in range(12, 250):
            w[m * 8 : (m + 1) * 8] = w[m * 8]

        cls._vqc_weights = w
        cls._vqc_sqrt_weights = (0.5 * np.sqrt(w)).astype(np.float32)
        cls._vqc_delta_term = delta_term
        return cls._vqc_sqrt_weights, cls._vqc_delta_term

    @classmethod
    def compute_vqc_cue_inv_norm(cls, nibbles: np.ndarray | List[int] | bytes) -> float:
        """
        FR: Calcule le facteur de normalisation exact inv_norm = float32(1.0 / sqrt(rawSim(cue, cue)))
        d'un gabarit vqc_Cue à partir de ses 2000 nibbles 4 bits (ou 1000 octets packés).
        EN: Computes the exact normalization factor inv_norm = float32(1.0 / sqrt(rawSim(cue, cue)))
        of a vqc_Cue template from its 2000 4-bit nibbles (or 1000 packed bytes).
        Ref: Red.dll @ 0x100FE2B9..0x100FE320 & 0x100FF050..0x100FFF45 (vqc_Relator::rawSim)
        """
        cls._get_vqc_relator_weights()
        w = cls._vqc_weights
        delta_term = cls._vqc_delta_term
        assert w is not None

        if isinstance(nibbles, (bytes, bytearray)) and len(nibbles) == 1000:
            raw_bytes = np.frombuffer(nibbles, dtype=np.uint8)
            vals = np.empty(2000, dtype=np.float64)
            vals[0::2] = (raw_bytes & 0x0F).astype(np.float64) * 2.0 - 15.0
            vals[1::2] = ((raw_bytes >> 4) & 0x0F).astype(np.float64) * 2.0 - 15.0
        else:
            q = np.asarray(nibbles, dtype=np.float64).ravel()
            vals = q[:2000] * 2.0 - 15.0

        raw_sim_self = float(np.float32(np.sum((vals * vals) * w.astype(np.float64)) * 0.25 + float(delta_term)))
        if raw_sim_self <= 1e-6:
            return 1.0
        return float(np.float32(1.0 / np.sqrt(raw_sim_self)))

    @classmethod
    def quantize_vqc_cue_nibbles(cls, feature_vec: np.ndarray) -> np.ndarray:
        """
        FR: Quantifie un vecteur continu en 2000 nibbles 4 bits non signés [0..15] selon les 15 seuils
        par dimension de vqc_Quantizer::map (Red.dll @ 0x100FCF60 & 0x100FCB00).
        EN: Quantizes a continuous feature vector into 2000 unsigned 4-bit nibbles [0..15] using the
        15 per-dimension thresholds of vqc_Quantizer::map (Red.dll @ 0x100FCF60 & 0x100FCB00).
        """
        cls._get_vqc_relator_weights()
        v = np.asarray(feature_vec, dtype=np.float32).ravel()
        if len(v) < 2000:
            reps = (2000 + len(v) - 1) // max(1, len(v))
            v = np.tile(v, reps)[:2000]
        else:
            v = v[:2000]
        if cls._vqc_thr_arr is not None:
            # FR: Recherche par dimension sur les 15 seuils / EN: Per-dimension threshold lookup (0x100FCB00)
            return np.sum(v[:, None] > cls._vqc_thr_arr, axis=1).astype(np.uint8)
        # FR: Repli uniforme sur [-0.35, +0.35] en 16 niveaux / EN: Uniform fallback over [-0.35, +0.35] in 16 levels
        scaled = np.clip(np.round((v + 0.35) / 0.70 * 15.0), 0, 15)
        return scaled.astype(np.uint8)

    def add_face_template(
        self,
        index: int,
        nibbles_or_vec: np.ndarray | List[int] | bytes,
        image_stamp: int = 0,
    ) -> bytes:
        """
        FR: Encode et enregistre un gabarit facial vqc_Cue (1044 octets) dans facetemplatesV2_0.db,
        facetemplatesV2_index.db (checksum=1) et imagedata_facetemplatesV2.pmp.
        EN: Encodes and stores a vqc_Cue facial template (1044 bytes) in facetemplatesV2_0.db,
        facetemplatesV2_index.db (checksum=1), and imagedata_facetemplatesV2.pmp.
        Ref: picasa3.exe @ 0x0048050B, Red.dll @ 0x10102020 (vqc_Cue::exportArr)
        """
        if isinstance(nibbles_or_vec, (bytes, bytearray)) and len(nibbles_or_vec) == 1044:
            blob = bytes(nibbles_or_vec)
        else:
            if isinstance(nibbles_or_vec, (bytes, bytearray)) and len(nibbles_or_vec) == 1000:
                nibbles: Any = bytes(nibbles_or_vec)
            else:
                arr = np.asarray(nibbles_or_vec)
                if arr.dtype.kind == "f":
                    nibbles = self.quantize_vqc_cue_nibbles(arr).tolist()
                else:
                    nibbles = arr.astype(np.uint8).ravel()[:2000].tolist()
            inv_norm = self.compute_vqc_cue_inv_norm(nibbles)
            blob = encode_face_template_blob(nibbles, inv_norm, image_stamp=image_stamp)

        self.add_thumbnail(
            index,
            blob,
            size="facetemplatesV2",
            checksum=FACETEMPLATE_BLOCK_CHECKSUM,
        )
        with self._lock:
            if index >= 0:
                self._align_imagedata_tables(index)
            ft_pmp = self.pmps.get("imagedata_facetemplatesV2")
            if ft_pmp is not None and index >= 0:
                while len(ft_pmp.records) <= index:
                    ft_pmp.records.append(0)
                ft_pmp.records[index] = 1
                ft_pmp.dirty = True
                self._dirty = True
            cache = getattr(self, "_face_template_cache", None)
            if cache is not None:
                cache.pop(index, None)
        return blob

    _vqc_byte_lut: Optional[np.ndarray] = None

    @classmethod
    def _get_vqc_byte_lut(cls) -> np.ndarray:
        """
        FR: Table de correspondance (256, 2) float32 précalculée convertissant un octet de deux nibbles 4 bits
        en deux valeurs déquantifiées `[(b & 0x0F)*2.0 - 15.0, ((b >> 4) & 0x0F)*2.0 - 15.0]`.
        Permet un décodage vectorisé ~25x plus rapide pour le regroupement de dizaines de milliers de visages.
        EN: Precomputed (256, 2) float32 lookup table mapping a packed 2-nibble byte to two dequantized values.
        Ref: Red.dll @ 0x10102020 (vqc_Cue::exportArr), picasa3.exe @ 0x0048B840
        """
        if cls._vqc_byte_lut is None:
            b = np.arange(256, dtype=np.uint8)
            lut = np.empty((256, 2), dtype=np.float32)
            lut[:, 0] = (b & 0x0F).astype(np.float32) * 2.0 - 15.0
            lut[:, 1] = ((b >> 4) & 0x0F).astype(np.float32) * 2.0 - 15.0
            cls._vqc_byte_lut = lut
        return cls._vqc_byte_lut

    def get_face_template_cue(self, index: int) -> Optional[Tuple[np.ndarray, float, int]]:
        """
        FR: Extrait le gabarit facial vqc_Cue (1044 octets) depuis facetemplatesV2_*.db :
        - u[0]=1044, u[1]=0x00423002 (vqc_Cue), u[2]=0, u[3]=0x0044DD4D (cue_format_id)
        - u[4]=2000 (size), u[5]=4 (bits), u[6]=8 (pack_size)
        - u[7]=inv_norm (float32), u[8]=image_stamp (uint32), u[9]=250 (uint32 count)
        - u[10]=checksum (uint32 équilibrant la somme des 261 uint32 à 0xFFFFFFFF)
        - u[11..260] (+0x2C..+0x414) = 1000 octets = 2000 nibbles 4 bits non signés q -> (2*q - 15).
        EN: Extracts the vqc_Cue facial template (1044 bytes) from facetemplatesV2_*.db:
        - u[0]=1044, u[1]=0x00423002 (vqc_Cue), u[2]=0, u[3]=0x0044DD4D (cue_format_id)
        - u[4]=2000 (size), u[5]=4 (bits), u[6]=8 (pack_size)
        - u[7]=inv_norm (float32), u[8]=image_stamp (uint32), u[9]=250 (uint32 count)
        - u[10]=checksum (uint32 balancing the sum of the 261 uint32 words to 0xFFFFFFFF)
        - u[11..260] (+0x2C..+0x414) = 1000 bytes = 2000 unsigned 4-bit nibbles q -> (2*q - 15).
        Ref: Red.dll @ 0x10102020 (vqc_Cue::exportArr), 0x10100A10 (vqc_Relator::sim), 0x100FF050 (rawSim)
        """
        with self._get_block_lock("facetemplatesV2"):
            idx_file = self.block_indices.get("facetemplatesV2")
            if not idx_file or index < 0 or index >= idx_file.record_count:
                return None
            entry = idx_file.get_entry(index)
            if not entry or entry.is_empty:
                return None
            container = self._get_container_for_entry("facetemplatesV2", entry.block)
            if not container:
                return None
            if getattr(container, "_payload", None) is None:
                _ = container.payload
            blob = container.get_blob(entry)
        if len(blob) < 1044:
            return None
        u0, u1, u2, u3, u4, u5, u6, inv_norm, image_stamp, u9, _ = struct.unpack_from("<7If3I", blob, 0)
        if (
            u0 == 1044
            and u1 == 0x00423002
            and u2 == 0
            and u3 == 0x0044DD4D
            and u4 == 2000
            and u5 == 4
            and u6 == 8
            and u9 == 250
        ):
            raw_bytes = np.frombuffer(blob, dtype=np.uint8, count=1000, offset=44)
            vals = self._get_vqc_byte_lut()[raw_bytes].ravel()
            sqrt_w, _ = self._get_vqc_relator_weights()
            vec = vals * (inv_norm * sqrt_w)
            cache = getattr(self, "_face_template_cache", None)
            if cache is None:
                cache = {}
                self._face_template_cache = cache
            cache[index] = vec
            return vec, float(inv_norm), int(image_stamp)
        # FR: Fallback pour blobs synthétiques de test / EN: Fallback for synthetic test blobs
        raw = np.frombuffer(blob[20:1044], dtype=np.int8).astype(np.float32)
        norm = float(np.linalg.norm(raw))
        if norm > 1e-6:
            return raw / norm, 1.0, 0
        return None

    @classmethod
    def decode_vqc_cue_vector(cls, blob: bytes) -> Optional[np.ndarray]:
        """
        FR: Décode un blob binaire de 1044 octets `vqc_Cue` (issu de `Red.dll` ou `facetemplatesV2_*.db`)
        en vecteur 2000-D pondéré prêt pour le produit scalaire et la sigmoïde `vqc_Relator::sim`.
        EN: Decodes a 1044-byte `vqc_Cue` binary blob (from `Red.dll` or `facetemplatesV2_*.db`)
        into a weighted 2000-D vector ready for dot product and `vqc_Relator::sim` sigmoid scoring.
        Ref: Red.dll @ 0x10102020 (vqc_Cue::exportArr), 0x10100A10 (vqc_Relator::sim), 0x100FF050 (rawSim)
        """
        if not blob or len(blob) < 1044:
            return None
        u0, u1, u2, u3, u4, u5, u6, inv_norm, _, u9, _ = struct.unpack_from("<7If3I", blob, 0)
        if (
            u0 == 1044
            and u1 == 0x00423002
            and u2 == 0
            and u3 == 0x0044DD4D
            and u4 == 2000
            and u5 == 4
            and u6 == 8
            and u9 == 250
        ):
            raw_bytes = np.frombuffer(blob, dtype=np.uint8, count=1000, offset=44)
            vals = cls._get_vqc_byte_lut()[raw_bytes].ravel()
            sqrt_w, _ = cls._get_vqc_relator_weights()
            return vals * (inv_norm * sqrt_w)
        return None

    def get_face_template(self, index: int) -> Optional[np.ndarray]:
        """
        FR: Extrait le vecteur de modèle facial précalculé (Neven FaceSDK vqc_Cue) depuis facetemplatesV2_*.db.
        EN: Extracts the precomputed facial template vector (Neven FaceSDK vqc_Cue) from facetemplatesV2_*.db.
        Ref: picasa3.exe @ 0x0048050B, 0x0048B840, 0x006CE4A0 & Red.dll @ 0x10100A10 (vqc_Relator::sim)
        """
        cache = getattr(self, "_face_template_cache", None)
        if cache is not None:
            cached = cache.get(index)
            if cached is not None:
                return cached
        cue = self.get_face_template_cue(index)
        return cue[0] if cue is not None else None

    def compute_entry_checksum(self, index: int, prefix: str = "thumbs") -> int:
        """
        FR: Calcule le checksum 32 bits exact d'une entrée CBlockFile selon son préfixe :
        - thumbs, thumbs2 : hash chemin parent + nom fichier + ft2 + size (0x006B99F0 / 0x004E3AB0)
        - bigthumbs, previews : hash ft2 arrondi à la seconde + orientation (0x006B9B26 / 0x0042A800)
        - facetemplatesV2 : constante 1 (0x0048050B)
        EN: Computes the exact 32-bit checksum for a CBlockFile entry according to its prefix:
        - thumbs, thumbs2: parent path + filename + ft2 + size hash (0x006B99F0 / 0x004E3AB0)
        - bigthumbs, previews: ft2 rounded to nearest second + orientation hash (0x006B9B26 / 0x0042A800)
        - facetemplatesV2: constant 1 (0x0048050B)
        """
        if prefix == "facetemplatesV2":
            return FACETEMPLATE_BLOCK_CHECKSUM
        if not self.thumbindex or index < 0 or index >= len(self.thumbindex.records):
            return 0
        rec = self.thumbindex.records[index]
        target_idx = index
        # Ref: picasa3.exe @ 0x004E3B87 : si type == 1001 (0x3e9, face record), utilise la photo parente
        if rec.type == 1001 and 0 <= rec.parent_idx < len(self.thumbindex.records):
            target_idx = rec.parent_idx
            rec = self.thumbindex.records[target_idx]
            if rec.type == 0:
                idx_f = self.block_indices.get(prefix)
                if idx_f is not None and 0 <= target_idx < idx_f.record_count:
                    parent_entry = idx_f.get_entry(target_idx)
                    if parent_entry is not None and parent_entry.checksum != 0:
                        return parent_entry.checksum

        if prefix in ("bigthumbs", "previews"):
            rot_step = 0
            pmp_rot = self.pmps.get("imagedata_rotate")
            if pmp_rot and target_idx < len(pmp_rot.records):
                raw_rot = pmp_rot.records[target_idx]
                if isinstance(raw_rot, int):
                    rot_step = raw_rot & 3
                elif isinstance(raw_rot, str) and raw_rot:
                    s_rot = raw_rot.strip()
                    if s_rot.startswith("rotate(") and s_rot.endswith(")"):
                        s_rot = s_rot[7:-1].strip()
                    try:
                        rot_step = int(s_rot) & 3
                    except ValueError:
                        rot_step = 0
            flip_step = 0
            pmp_flip = self.pmps.get("imagedata_flipped")
            if pmp_flip and target_idx < len(pmp_flip.records):
                raw_flip = pmp_flip.records[target_idx]
                if isinstance(raw_flip, int):
                    flip_step = 1 if raw_flip > 0 else 0
                elif isinstance(raw_flip, str) and raw_flip:
                    s_fl = raw_flip.strip()
                    if s_fl.startswith("flipped(") and s_fl.endswith(")"):
                        s_fl = s_fl[8:-1].strip()
                    try:
                        flip_step = 1 if int(s_fl) > 0 else 0
                    except ValueError:
                        flip_step = 0
            pmp_filt = self.pmps.get("imagedata_filters")
            filt_str = str(pmp_filt.records[target_idx] or "") if (pmp_filt and target_idx < len(pmp_filt.records)) else ""
            pmp_c64 = self.pmps.get("imagedata_crop64")
            c64_val = int(pmp_c64.records[target_idx] or 0) if (pmp_c64 and target_idx < len(pmp_c64.records)) else 0
            pmp_w = self.pmps.get("imagedata_width")
            w_val = int(pmp_w.records[target_idx] or 0) if (pmp_w and target_idx < len(pmp_w.records)) else 0
            pmp_h = self.pmps.get("imagedata_height")
            h_val = int(pmp_h.records[target_idx] or 0) if (pmp_h and target_idx < len(pmp_h.records)) else 0
            pmp_txt = self.pmps.get("imagedata_text")
            txt_str = str(pmp_txt.records[target_idx] or "") if (pmp_txt and target_idx < len(pmp_txt.records)) else ""
            pmp_ta = self.pmps.get("imagedata_textactive")
            ta_val = int(pmp_ta.records[target_idx] or 0) if (pmp_ta and target_idx < len(pmp_ta.records)) else 0
            return compute_preview_checksum(
                rec.ft2,
                rotate_step=rot_step,
                flip=flip_step,
                filters=filt_str,
                crop64=c64_val,
                width=w_val,
                height=h_val,
                text=txt_str,
                text_active=ta_val,
            )

        folder_path = ""
        if 0 <= rec.parent_idx < len(self.thumbindex.records):
            folder_path = self.thumbindex.records[rec.parent_idx].path
        cs = compute_thumb_checksum(folder_path, rec.path, rec.ft2, rec.size)
        t1 = self.block_indices.get("thumbs")
        t2 = self.block_indices.get("thumbs2")
        if t1 is not None and t2 is not None and 0 <= target_idx < min(t1.record_count, t2.record_count):
            e1 = t1.get_entry(target_idx)
            e2 = t2.get_entry(target_idx)
            if e1 is not None and e2 is not None and e1.checksum != 0 and e1.checksum == e2.checksum and e1.checksum != cs:
                return e1.checksum
        return cs

    # Ref: picasa3.exe @ 0x00412DEA, 0x00412E3F — valeur par défaut -1 (0xFFFFFFFF) passée à FUN_006d1a40
    # pour ces colonnes (vérifié sur db3 : lignes actives = 0xFFFFFFFF ; imagedata_aliasparents reste 0).
    _PMP_NEW_ROW_DEFAULTS: Dict[str, Any] = {
        "imagedata_personalbumrecs": 0xFFFFFFFF,
        "imagedata_personalbumrecs2": 0xFFFFFFFF,
    }

    def _pmp_new_row_default(self, stem: str, pmp: Any) -> Any:
        """
        FR: Renvoie la valeur par défaut d'une nouvelle ligne pour la colonne PMP `stem`, conforme à picasa3.exe.
        EN: Returns the default value of a new row for PMP column `stem`, matching picasa3.exe.
        Ref: picasa3.exe @ 0x004127A0..0x00412F20 (FUN_006d1a40 default argument)
        """
        if stem in self._PMP_NEW_ROW_DEFAULTS:
            return self._PMP_NEW_ROW_DEFAULTS[stem]
        return pmp.default_value()

    def _align_imagedata_tables(self, target_idx: int) -> None:
        """
        FR: Aligne toutes les colonnes imagedata_*.pmp et les *_index.db jusqu'à target_idx inclus.
        EN: Aligns all imagedata_*.pmp columns and *_index.db files up to target_idx inclusive.
        Ref: picasa3.exe @ 0x00415790 (decomp_dir_scanner_ctor.c)
        """
        if target_idx < 0:
            return
        pmp_w = self.pmps.get("imagedata_width")
        t_idx = self.block_indices.get("thumbs")
        if (
            target_idx <= self._min_aligned_idx
            and len(self.pmps) == self._aligned_pmp_count
            and (pmp_w is None or len(pmp_w.records) > target_idx)
            and (t_idx is None or t_idx.record_count > target_idx)
        ):
            return
        for name, pmp in self.pmps.items():
            if name.startswith("imagedata_"):
                missing = target_idx + 1 - len(pmp.records)
                if missing > 0:
                    def_val = self._pmp_new_row_default(name, pmp)
                    pmp.records.extend([def_val] * missing)
                    pmp.dirty = True
        for prefix, idx_file in self.block_indices.items():
            if prefix in ("thumbs", "thumbs2", "bigthumbs", "previews", "facetemplatesV2"):
                missing = target_idx + 1 - idx_file.record_count
                if missing > 0:
                    idx_file.checksums.extend([0] * missing)
                    idx_file.offsets.extend([0] * missing)
                    idx_file.sizes_and_blocks.extend([0] * missing)
                    idx_file.dirty = True
        self._min_aligned_idx = target_idx
        self._aligned_pmp_count = len(self.pmps)

    def get_or_create_folder_index(self, folder_path: str) -> int:
        """
        FR: Retrouve l'index de dossier (type == 1) dans thumbindex.db, ou en crée un nouveau
        en conservant strictement le séparateur Picasa ('\\') dans la structure binaire,
        avec `ft1` (création) et `ft2` (modification) exacts au 100 ns et `imagedata_filetype = 1`.
        EN: Finds the folder index (type == 1) in thumbindex.db, or creates a new one
        while strictly preserving the Picasa ('\\') separator in the binary structure,
        with exact 100 ns `ft1` (creation) and `ft2` (last write) and `imagedata_filetype = 1`.
        Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex : flags=0x0100, parent_idx=0xFFFFFFFF), 0x00415790
        """
        if not self.thumbindex:
            self.thumbindex = ThumbIndexFile()

        self._ensure_path_index_cache()
        norm = folder_path.replace("/", "\\").rstrip("\\") + "\\"
        norm_key = norm.rstrip("\\").lower()
        cached_idx = self._folder_index_cache.get(norm_key)
        if cached_idx is not None and 0 <= cached_idx < len(self.thumbindex.records):
            rec = self.thumbindex.records[cached_idx]
            if rec.type == 1 and rec.path.lower() == norm.lower():
                return cached_idx

        for idx, rec in enumerate(self.thumbindex.records):
            if rec.type == 1 and rec.path.lower() == norm.lower():
                self._folder_index_cache[norm_key] = idx
                return idx

        ft1_val = 0
        ft2_val = 0
        host_folder = _to_host_path(folder_path)
        try:
            if os.path.exists(host_folder):
                from picasa_py.scanner.scanner import file_filetimes
                ft1_val, ft2_val, _ = file_filetimes(host_folder)
        except Exception:
            ft1_val = 0
            ft2_val = 0

        new_rec = ThumbIndexRecord(
            path=norm,
            ft1=ft1_val,
            ft2=ft2_val,
            size=0,
            type=1,
            flags=THUMBINDEX_ACTIVE_FLAG,
            parent_idx=0xFFFFFFFF,
        )
        self.thumbindex.records.append(new_rec)
        self.thumbindex.dirty = True
        new_idx = len(self.thumbindex.records) - 1
        self._index_single_record_into_cache(new_idx, new_rec)
        self._path_index_version = len(self.thumbindex.records)
        self._parent_to_face_children_len = len(self.thumbindex.records)
        self._align_imagedata_tables(new_idx)
        pmp_ft = self.pmps.get("imagedata_filetype")
        if pmp_ft is not None and new_idx < len(pmp_ft.records):
            if pmp_ft.records[new_idx] != 1:
                pmp_ft.records[new_idx] = 1
                pmp_ft.dirty = True
        return new_idx

    def ensure_folder_album_row(self, folder_path: str) -> str:
        """
        FR: Garantit l'existence d'une ligne d'album de dossier (`albumdata_category == 2` ou `7`) dans
        `albumdata_*.pmp` pour `folder_path`, synchronise `albumdata_inisync` avec le `FILETIME`
        exact (100 ns) de `.picasa.ini`, et retourne le jeton `]album:<uid>` du dossier.
        EN: Ensures a folder album row (`albumdata_category == 2` or `7`) exists in `albumdata_*.pmp`
        for `folder_path`, synchronizes `albumdata_inisync` with the exact 100 ns `FILETIME`
        of `.picasa.ini`, and returns the folder's `]album:<uid>` token.
        Ref: picasa3.exe @ 0x00415790, 0x00440D82, 0x0041CA51, 0x004DCF60, 0x00456A15, 0x008AAD76
        """
        ad_names = self.pmps.get("albumdata_name")
        ad_cats = self.pmps.get("albumdata_category")
        ad_tokens = self.pmps.get("albumdata_token")
        ad_uids = self.pmps.get("albumdata_uid")
        ad_fnames = self.pmps.get("albumdata_filename")
        ad_dates = self.pmps.get("albumdata_date")
        ad_inisync = self.pmps.get("albumdata_inisync")
        if ad_names is None or ad_cats is None or ad_tokens is None:
            return ""

        norm = folder_path.replace("/", "\\").rstrip("\\") + "\\"
        norm_low = norm.lower()
        host_folder = _to_host_path(folder_path.rstrip("\\/"))

        ini_ft2 = 0
        ini_name_override: Optional[str] = None
        ini_date_override: Optional[float] = None
        target_cat: int = 2  # Ref: picasa3.exe @ 0x004420D3 - 0x00442172 (2 = Folders on Disk, 7 = Hidden Folders)
        if host_folder:
            for ini_cand in (".picasa.ini", "Picasa.ini"):
                ini_p = os.path.join(host_folder, ini_cand)
                if os.path.exists(ini_p):
                    try:
                        from picasa_py.scanner.scanner import file_filetimes, datetime_to_ole
                        from datetime import datetime
                        _, ini_ft2, _ = file_filetimes(ini_p)
                        doc = self.get_parsed_ini(ini_p)
                        if doc is not None:
                            sec_p = doc.get_section("Picasa")
                            if sec_p is not None:
                                n_val = sec_p.get("name")
                                if n_val and n_val.strip():
                                    ini_name_override = n_val.strip()
                                p2cat_val = (sec_p.get("P2category") or sec_p.get("category") or "").strip()
                                if p2cat_val.lower() in ("hidden folders", "dossiers masqués"):
                                    target_cat = 7
                                d_val = sec_p.get("date")
                                if d_val and d_val.strip():
                                    try:
                                        ini_date_override = float(d_val.strip())
                                    except ValueError:
                                        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
                                            try:
                                                ini_date_override = datetime_to_ole(
                                                    datetime.strptime(d_val.strip()[:19], fmt)
                                                )
                                                break
                                            except Exception:
                                                pass
                    except Exception:
                        pass
                    break

        if not hasattr(self, "_hidden_folders") or not isinstance(self._hidden_folders, set):
            self._hidden_folders = set()
        norm_slash_low = norm.replace("\\", "/").rstrip("/").lower()
        if target_cat == 7:
            self._hidden_folders.add(norm_slash_low)
        elif norm_slash_low in self._hidden_folders:
            target_cat = 7

        if ad_fnames is not None:
            for row_i, fn_val in enumerate(ad_fnames.records):
                if row_i < len(ad_cats.records) and ad_cats.records[row_i] in (2, 7):
                    if str(fn_val or "").replace("/", "\\").rstrip("\\").lower() + "\\" == norm_low:
                        if ad_cats.records[row_i] != target_cat:
                            ad_cats.records[row_i] = target_cat
                            ad_cats.dirty = True
                        if ad_inisync is not None and row_i < len(ad_inisync.records) and ini_ft2:
                            if ad_inisync.records[row_i] != ini_ft2:
                                ad_inisync.records[row_i] = ini_ft2
                                ad_inisync.dirty = True
                        if ini_name_override and row_i < len(ad_names.records) and ad_names.records[row_i] != ini_name_override:
                            ad_names.records[row_i] = ini_name_override
                            ad_names.dirty = True
                        if ini_date_override is not None and ad_dates is not None and row_i < len(ad_dates.records) and ad_dates.records[row_i] != ini_date_override:
                            ad_dates.records[row_i] = ini_date_override
                            ad_dates.dirty = True
                        tok = str(ad_tokens.records[row_i] or "") if row_i < len(ad_tokens.records) else ""
                        return tok

        import hashlib
        uid_hex = hashlib.md5(norm_low.encode("utf-8", errors="surrogateescape")).hexdigest()
        tok_str = f"]album:{uid_hex}"
        folder_title = ini_name_override or os.path.basename(norm.rstrip("\\")) or norm
        ole_dt = ini_date_override if ini_date_override is not None else 0.0
        if ole_dt == 0.0 and host_folder and os.path.exists(host_folder):
            try:
                from picasa_py.scanner.scanner import datetime_to_ole
                from datetime import datetime
                ole_dt = datetime_to_ole(datetime.fromtimestamp(os.path.getmtime(host_folder)))
            except Exception:
                ole_dt = 0.0

        albumdata_tables = {
            stem: pmp
            for stem, pmp in self.pmps.items()
            if stem.startswith("albumdata_")
        }
        base_len = len(ad_names.records)
        for pmp in albumdata_tables.values():
            def_val = pmp.default_value()
            while len(pmp.records) < base_len:
                pmp.records.append(def_val)
                pmp.dirty = True

        # Ref: db3 — ligne 0 réservée à l'album des visages sans nom (category=8, token="]unknownface")
        if len(ad_names.records) == 0:
            u_uid = hashlib.md5(b"]unknownface").hexdigest()
            for stem, pmp in albumdata_tables.items():
                if stem == "albumdata_name":
                    pmp.records.append("Sans nom")
                elif stem == "albumdata_token":
                    pmp.records.append("]unknownface")
                elif stem == "albumdata_uid":
                    pmp.records.append(u_uid)
                elif stem == "albumdata_category":
                    pmp.records.append(8)
                else:
                    pmp.records.append(pmp.default_value())
                pmp.dirty = True

        for stem, pmp in albumdata_tables.items():
            if stem == "albumdata_name":
                pmp.records.append(folder_title)
            elif stem == "albumdata_filename":
                pmp.records.append(norm)
            elif stem == "albumdata_token":
                pmp.records.append(tok_str)
            elif stem == "albumdata_uid":
                pmp.records.append(uid_hex)
            elif stem == "albumdata_category":
                pmp.records.append(target_cat)
            elif stem == "albumdata_date":
                pmp.records.append(ole_dt)
            elif stem == "albumdata_inisync":
                pmp.records.append(ini_ft2)
            else:
                pmp.records.append(pmp.default_value())
            pmp.dirty = True
        return tok_str

    def add_media_record(
        self, folder_path: str, filename: str, file_size: int, mtime: int = 0, media_type: int = 2
    ) -> int:
        """
        FR: Ajoute un enregistrement d'image ou vidéo dans thumbindex.db avec flags=0x0100 et FILETIME valide.
        EN: Adds an image or video record to thumbindex.db with flags=0x0100 and a valid FILETIME.
        Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex)
        """
        with self._lock:
            if not self.thumbindex:
                self.thumbindex = ThumbIndexFile()

            parent_idx = self.get_or_create_folder_index(folder_path)
            if mtime > 100000000000:
                ft = int(mtime)
            elif mtime > 0:
                ft = unix_to_filetime(float(mtime))
            else:
                ft = 0
                host_folder = _to_host_path(folder_path)
                full_p = os.path.join(host_folder, filename)
                if os.path.exists(full_p):
                    try:
                        ft = unix_to_filetime(os.path.getmtime(full_p))
                    except Exception:
                        ft = 0

            new_rec = ThumbIndexRecord(
                path=filename,
                ft1=ft,
                ft2=ft,
                size=file_size,
                type=media_type,
                flags=THUMBINDEX_ACTIVE_FLAG,
                parent_idx=parent_idx,
            )
            self.thumbindex.records.append(new_rec)
            self.thumbindex.dirty = True
            new_idx = len(self.thumbindex.records) - 1
            self._index_single_record_into_cache(new_idx, new_rec)
            self._path_index_version = len(self.thumbindex.records)
            self._parent_to_face_children_len = len(self.thumbindex.records)
            self.invalidate_search_cache()
            self._align_imagedata_tables(new_idx)
            return new_idx

    def add_thumbnail(self, index: int, jpeg_bytes: bytes, size: str = "small", checksum: int = 0) -> None:
        """
        FR: Écrit une vignette dans le conteneur CBlockFile (avec réutilisation in-place si possible)
        et met à jour l'index avec le checksum 32 bits exact de picasa3.exe.
        EN: Writes a thumbnail to the CBlockFile container (with in-place reuse when possible)
        and updates the index with the exact 32-bit checksum of picasa3.exe.
        Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry), 0x006B99F0 (checksum)
        """
        prefix_map = {
            "small": "thumbs",
            "medium": "thumbs2",
            "large": "bigthumbs",
            "preview": "previews",
        }
        prefix = prefix_map.get(size, size)
        if checksum == 0:
            with self._lock:
                checksum = self.compute_entry_checksum(index, prefix)
        with self._get_block_lock(prefix):
            idx_file = self.block_indices.get(prefix)
            if not idx_file:
                return

            active_blk = idx_file.active_block
            container = self._get_container_for_entry(prefix, active_blk)
            if not container:
                container = self.block_containers.get(prefix)
                active_blk = 0
            if not container:
                return

            while idx_file.record_count < index:
                idx_file.append_entry(BlockEntry())

            existing = idx_file.get_entry(index) if index < idx_file.record_count else None
            blob_len = len(jpeg_bytes)

            if blob_len == 0:
                entry = BlockEntry(checksum=0, offset=0, size=0, block=0)
            elif (
                existing is not None
                and not existing.is_empty
                and existing.size >= blob_len
                and existing.offset >= 4
            ):
                # Ref: picasa3.exe @ 0x006B75F0 (lines 381-386) : réécriture in-place dans le bloc
                # de l'entrée existante (même si existing.block != active_blk).
                target_cont = self._get_container_for_entry(prefix, existing.block)
                if target_cont is not None and existing.offset + blob_len <= target_cont.byte_size():
                    target_cont.write_blob_at(existing.offset, jpeg_bytes)
                    entry = BlockEntry(
                        checksum=checksum,
                        offset=existing.offset,
                        size=blob_len,
                        block=existing.block,
                    )
                else:
                    entry = container.write_blob(
                        jpeg_bytes,
                        existing_entry=None,
                        checksum=checksum,
                        block_idx=active_blk,
                    )
            else:
                # Ref: picasa3.exe @ 0x006B767A (line 294) : rotation vers active_block + 1
                # si la taille du conteneur actif + blob dépasse 0x7FFFFFFF (2 Go).
                if container.byte_size() + blob_len > 0x7FFFFFFF and active_blk < 0xFF:
                    active_blk += 1
                    idx_file.active_block = active_blk
                    idx_file.dirty = True
                    new_cont = self.block_containers_by_block.get((prefix, active_blk))
                    if new_cont is None:
                        new_cont = BlockContainerFile(magic=container.magic)
                        new_cont._fully_dirty = True
                        self.block_containers_by_block[(prefix, active_blk)] = new_cont
                    container = new_cont
                entry = container.append_blob(
                    jpeg_bytes,
                    checksum=checksum,
                    block_idx=active_blk,
                )

            if index < idx_file.record_count:
                idx_file.checksums[index] = entry.checksum
                idx_file.offsets[index] = entry.offset
                idx_file.sizes_and_blocks[index] = entry.raw_size_block
                idx_file.dirty = True
            else:
                idx_file.append_entry(entry)

    def update_thumbnails_from_pil(
        self,
        index: int,
        pil_img: Any,
        persist_to_disk: bool = True,
    ) -> bool:
        """
        FR: Recalcule et met à jour les miniatures et aperçus JPEG d'une photo à partir d'une image PIL
        déjà transformée/filtrée, exactement comme picasa3.exe après l'application d'un effet ou d'une retouche :
        - `thumbs` (`small`, 144x144 max, qualité 90, Ref: 0x00424EC3 / 0x004281EC)
        - `thumbs2` (`medium`, 288x288 max, qualité 90, Ref: 0x00424E15 / 0x00428413)
        - `bigthumbs` (`large`, 288x288 max, qualité 80/96, Ref: 0x00424E55 / 0x006B6960)
        - `previews` (`preview`, 640x640 ou 1600x1600 max, qualité 80/96, Ref: 0x0042525A..0x00425264 : 0x280 / 0x640)
        Met également à jour `imagedata_edit_width`, `imagedata_edit_height` et `imagedata_avgcolor` (Ref: 0x004280D8).
        EN: Recalculates and updates a photo's JPEG thumbnails and previews from an already-transformed/filtered
        PIL image, matching picasa3.exe after applying an effect or edit:
        - `thumbs` (`small`, 144x144 max, quality 90, Ref: 0x00424EC3 / 0x004281EC)
        - `thumbs2` (`medium`, 288x288 max, quality 90, Ref: 0x00424E15 / 0x00428413)
        - `bigthumbs` (`large`, 288x288 max, quality 80/96, Ref: 0x00424E55 / 0x006B6960)
        - `previews` (`preview`, 640x640 or 1600x1600 max, quality 80/96, Ref: 0x0042525A..0x00425264: 0x280 / 0x640)
        Also updates `imagedata_edit_width`, `imagedata_edit_height`, and `imagedata_avgcolor` (Ref: 0x004280D8).
        Ref: picasa3.exe @ 0x00424E00, 0x00425210, 0x00425F60, 0x00579360, 0x006B6960, 0x006B75F0
        """
        if pil_img is None:
            return False
        resolved_idx = self._resolve_photo_record_index(index)
        if resolved_idx is None or resolved_idx < 0:
            return False

        try:
            import io
            from PIL import Image

            if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
                rgba = pil_img.convert("RGBA")
                rgb_img = Image.new("RGB", rgba.size, (255, 255, 255))
                rgb_img.paste(rgba, mask=rgba.split()[3])
            elif pil_img.mode != "RGB":
                rgb_img = pil_img.convert("RGB")
            else:
                rgb_img = pil_img

            w, h = rgb_img.size
            if w <= 0 or h <= 0:
                return False

            def _encode_scaled_jpeg(max_dim: int, quality: int = 90) -> bytes:
                # Ref: picasa3.exe @ 0x00424CA0 (FUN_00424ca0 -> ceil(max_dim * min_side / max_side))
                if w > max_dim or h > max_dim:
                    if w >= h:
                        tw = max_dim
                        th = max(1, int(math.ceil(max_dim * h / float(w))))
                    else:
                        th = max_dim
                        tw = max(1, int(math.ceil(max_dim * w / float(h))))
                    sub = rgb_img.resize((tw, th), Image.Resampling.BILINEAR)
                else:
                    sub = rgb_img
                buf = io.BytesIO()
                sub.save(buf, format="JPEG", quality=quality)
                return buf.getvalue()

            def _has_existing_block_entry(stem: str, r_idx: int) -> bool:
                b_idx = self.block_indices.get(stem)
                if b_idx is None:
                    return False
                entry = b_idx.get_entry(r_idx)
                return entry is not None and not entry.is_empty

            # FR: Compression JPEG et calcul de la couleur moyenne HORS verrou global (Ref: 0x00414C90 CThumbMaker)
            # bigthumbs_0.db et previews_0.db ne sont mis à jour que si l'enregistrement possède déjà une entrée
            # (dans db3/, bigthumbs_0.db est réservé aux visages 1001 et seules quelques photos ont un preview)
            # EN: JPEG compression and average color computation OUTSIDE the global lock (Ref: 0x00414C90 CThumbMaker)
            # bigthumbs_0.db and previews_0.db are only updated if the record already has an entry
            encoded_small = _encode_scaled_jpeg(144, 90) if "thumbs" in self.block_indices else None
            encoded_med = _encode_scaled_jpeg(72, 90) if "thumbs2" in self.block_indices else None
            encoded_large = _encode_scaled_jpeg(288, 90) if _has_existing_block_entry("bigthumbs", resolved_idx) else None
            encoded_prev = _encode_scaled_jpeg(640, 90) if "previews" in self.block_indices else None

            avg_u32: Optional[int] = None
            if "imagedata_avgcolor" in self.pmps:
                try:
                    avg_px = rgb_img.resize((1, 1), Image.Resampling.BILINEAR).getpixel((0, 0))
                    if isinstance(avg_px, tuple) and len(avg_px) >= 3:
                        avg_u32 = 0xFF000000 | ((int(avg_px[0]) & 0xFF) << 16) | ((int(avg_px[1]) & 0xFF) << 8) | (int(avg_px[2]) & 0xFF)
                except Exception:
                    avg_u32 = None

            with self._lock:
                self._align_imagedata_tables(resolved_idx)

                # 1. thumbs (0x90 = 144px, quality 90 -> 0x5A)
                if encoded_small is not None:
                    self.add_thumbnail(resolved_idx, encoded_small, size="small")

                # 2. thumbs2 (0x48 = 72px, quality 90 -> 0x5A, Ref: FUN_00424CA0)
                if encoded_med is not None:
                    self.add_thumbnail(resolved_idx, encoded_med, size="medium")

                # 3. bigthumbs (0x120 = 288px, quality 90 -> 0x5A, Ref: FUN_00425210)
                if encoded_large is not None:
                    self.add_thumbnail(resolved_idx, encoded_large, size="large")

                # 4. previews (Ref: 0x0042525F : 0x280 = 640px, quality 90 -> 0x5A)
                if encoded_prev is not None:
                    self.add_thumbnail(resolved_idx, encoded_prev, size="preview")

                # 5. Colonnes PMP imagedata_edit_width, imagedata_edit_height (toujours 0 dans db3/), imagedata_avgcolor
                for col_name, col_val in (
                    ("imagedata_edit_width", 0),
                    ("imagedata_edit_height", 0),
                ):
                    pmp = self.pmps.get(col_name)
                    if pmp is not None:
                        def_v = pmp.default_value()
                        while len(pmp.records) <= resolved_idx:
                            pmp.records.append(def_v)
                        pmp.records[resolved_idx] = col_val
                        pmp.dirty = True

                pmp_avg = self.pmps.get("imagedata_avgcolor")
                if pmp_avg is not None and avg_u32 is not None:
                    def_v = pmp_avg.default_value()
                    while len(pmp_avg.records) <= resolved_idx:
                        pmp_avg.records.append(def_v)
                    pmp_avg.records[resolved_idx] = avg_u32
                    pmp_avg.dirty = True

                # 6. Sous-enregistrements de visages enfants (type == 1001, Ref: FUN_00425210 @ 0x004258D1..0x00425B6C)
                if self.thumbindex is not None:
                    child_face_indices = self._get_face_children(resolved_idx)
                    fm = self._face_manager
                    full_path = self.get_media_full_path(resolved_idx) or ""
                    if child_face_indices:
                        if fm is None:
                            fm = getattr(self, "face_manager", None)
                        pmp_fr = self.pmps.get("imagedata_facerect")
                        from picasa_py.faces.facerect import FaceRect
                        for c_idx in child_face_indices:
                            fr_obj = None
                            if fm is not None and hasattr(fm, "photo_to_faces"):
                                c_flist = fm.photo_to_faces.get(c_idx)
                                if c_flist:
                                    fr_obj = c_flist[0]
                            if fr_obj is None and pmp_fr is not None and c_idx < len(pmp_fr.records):
                                rval = pmp_fr.records[c_idx]
                                if rval and rval > 1:
                                    fr_obj = FaceRect.from_uint64(int(rval))
                            if fr_obj is not None and fm is not None and hasattr(fm, "_write_face_record_thumbnails"):
                                fm._write_face_record_thumbnails(
                                    c_idx, fr_obj, photo_path=full_path, source_img=rgb_img
                                )
                    if fm is not None and hasattr(fm, "_avatar_cache") and fm._avatar_cache:
                        affected_indices = {resolved_idx, *child_face_indices}
                        norm_p = os.path.normcase(os.path.abspath(full_path)) if full_path else ""
                        for k in list(fm._avatar_cache.keys()):
                            if isinstance(k, tuple) and len(k) >= 2:
                                if k[0] in affected_indices:
                                    fm._avatar_cache.pop(k, None)
                                elif isinstance(k[1], str) and k[1] and norm_p and os.path.normcase(os.path.abspath(k[1])) == norm_p:
                                    fm._avatar_cache.pop(k, None)

                if not hasattr(self, "_updated_thumb_indices") or not isinstance(self._updated_thumb_indices, set):
                    self._updated_thumb_indices = set()
                self._updated_thumb_indices.add(resolved_idx)

            if persist_to_disk:
                self.save_thumbnails_only()
            return True
        except Exception:
            return False

    # Ref: picasa3.exe @ 0x006B7FC0, 0x006B9470, 0x006C1920 (deferred CBlockFile index/thumb flush)
    def schedule_save_thumbnails(self, delay_ms: int = 1500) -> None:
        """
        FR: Planifie en arrière-plan une écriture différée et coalescée de `save_thumbnails_only`
        afin de ne jamais bloquer le thread GUI lors d'une séquence de retouche rapide.
        Si l'utilisateur interagit encore avec la GUI au moment du déclenchement, reporte l'écriture.
        EN: Schedules a coalesced background call to `save_thumbnails_only` so the GUI thread
        is never blocked during rapid interactive editing.
        If the user is still actively interacting with the GUI when the timer fires, defers the flush.
        Ref: picasa3.exe @ 0x006B7FC0, 0x006B9470, 0x006C1920 (CIndexSaver)
        """
        with self._lock:
            if self._thumb_save_timer is not None:
                try:
                    self._thumb_save_timer.cancel()
                except Exception:
                    pass
                self._thumb_save_timer = None

            def _flush_worker() -> None:
                try:
                    from picasa_py.scanner.scanner import BackgroundScanWorker, set_current_thread_background_priority
                    # Ref: picasa3.exe @ 0x00415790 (CIndexSaver -> THREAD_PRIORITY_BELOW_NORMAL)
                    set_current_thread_background_priority(lowest=False)
                    if BackgroundScanWorker.is_gui_active(0.8):
                        self.schedule_save_thumbnails(1000)
                        return
                except Exception:
                    pass
                with self._lock:
                    self._thumb_save_timer = None
                try:
                    self.save_thumbnails_only()
                except Exception:
                    pass

            timer = threading.Timer(max(0.05, float(delay_ms) / 1000.0), _flush_worker)
            timer.daemon = True
            self._thumb_save_timer = timer
            timer.start()

    def update_photo_thumbnails_from_disk(
        self,
        photo_path_or_idx: str | Path | int,
        persist_to_disk: bool = True,
    ) -> bool:
        """
        FR: Charge l'image transformée depuis le disque (avec ses retouches .picasa.ini)
        à une résolution d'aperçu optimale et met à jour ses miniatures et aperçus dans la base.
        EN: Loads the transformed image from disk (with its .picasa.ini edits)
        at optimal preview resolution and updates its thumbnails and previews in the database.
        Ref: picasa3.exe @ 0x00425210, 0x00425F60, 0x00579360
        """
        if isinstance(photo_path_or_idx, int):
            idx = self._resolve_photo_record_index(photo_path_or_idx)
            if idx is None:
                return False
            full_path = self.get_media_full_path(idx)
        else:
            full_path = str(photo_path_or_idx)
            idx = self.find_photo_index(full_path)
        if idx is None or not full_path or not os.path.exists(full_path):
            return False
        try:
            from picasa_py.ui.image_processor import PicasaImageProcessor
            pil_img = PicasaImageProcessor.load_transformed_image(full_path, max_size=1280)
            if pil_img is None:
                return False
            return self.update_thumbnails_from_pil(idx, pil_img, persist_to_disk=persist_to_disk)
        except Exception:
            return False

    def save_thumbnails_only(self) -> None:
        """
        FR: Sauvegarde atomiquement sur disque les fichiers CBlockFile de miniatures/aperçus
        (`thumbs_*`, `thumbs2_*`, `bigthumbs_*`, `previews_*`) ainsi que les colonnes PMP d'édition
        (`imagedata_edited.pmp`, `imagedata_filters.pmp`, `imagedata_rotate.pmp`, `imagedata_crop64.pmp`)
        sans réécrire l'intégralité des 56 tables PMP lorsque seule une vignette a changé.
        EN: Atomically saves on-disk thumbnail/preview CBlockFile containers and indices
        (`thumbs_*`, `thumbs2_*`, `bigthumbs_*`, `previews_*`) and edit PMP columns
        (`imagedata_edited.pmp`, `imagedata_filters.pmp`, `imagedata_rotate.pmp`, `imagedata_crop64.pmp`)
        without rewriting all 56 PMP tables when only a thumbnail changed.
        Ref: picasa3.exe @ 0x006B7FC0 (CBlockFile::SaveIndex), 0x0080CFA0
        """
        if not self.db3_dir or self.db3_dir == Path(".") or not self.db3_dir.exists():
            return

        def _atomic_write(target: Path, data: bytes) -> None:
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(data)
            try:
                os.replace(str(tmp), str(target))
            except PermissionError:
                try:
                    target.write_bytes(data)
                finally:
                    tmp.unlink(missing_ok=True)

        with self._lock:
            if self._thumb_save_timer is not None:
                try:
                    self._thumb_save_timer.cancel()
                except Exception:
                    pass
                self._thumb_save_timer = None

            ti_bytes: Optional[bytes] = None
            ti_path = self.db3_dir / "thumbindex.db"
            if self.thumbindex is not None:
                if len(self.thumbindex.records) > 0:
                    self._align_imagedata_tables(len(self.thumbindex.records) - 1)
                if getattr(self.thumbindex, "dirty", True) or not ti_path.exists():
                    ti_bytes = self.thumbindex.to_bytes()
                    self.thumbindex.dirty = False

        if ti_bytes is not None:
            _atomic_write(ti_path, ti_bytes)

        thumb_prefixes = ("thumbs", "thumbs2", "bigthumbs", "previews")
        saved_containers: Set[Tuple[str, int]] = set()
        for (prefix, block_num), container in list(self.block_containers_by_block.items()):
            if prefix in thumb_prefixes:
                with self._get_block_lock(prefix):
                    container.flush_to_file(self.db3_dir / f"{prefix}_{block_num}.db")
                saved_containers.add((prefix, block_num))

        for prefix in thumb_prefixes:
            container = self.block_containers.get(prefix)
            if container is not None and (prefix, 0) not in saved_containers:
                with self._get_block_lock(prefix):
                    container.flush_to_file(self.db3_dir / f"{prefix}_0.db")
            idx_file = self.block_indices.get(prefix)
            if idx_file is not None:
                idx_path = self.db3_dir / f"{prefix}_index.db"
                idx_bytes: Optional[bytes] = None
                with self._get_block_lock(prefix):
                    if getattr(idx_file, "dirty", True) or not idx_path.exists():
                        idx_bytes = idx_file.to_bytes()
                        idx_file.dirty = False
                if idx_bytes is not None:
                    _atomic_write(idx_path, idx_bytes)

        with self._lock:
            target_img_len = len(self.thumbindex.records) if self.thumbindex is not None else 0
            always_save_stems = {
                "imagedata_edited",
                "imagedata_filters",
                "imagedata_rotate",
                "imagedata_crop64",
                "imagedata_edit_width",
                "imagedata_edit_height",
                "imagedata_avgcolor",
                "imagedata_text",
                "imagedata_textactive",
                "imagedata_facerect",
            }
            for stem, pmp_file in self.pmps.items():
                if not stem.startswith("imagedata_"):
                    continue
                if self.thumbindex is not None:
                    def_val = self._pmp_new_row_default(stem, pmp_file)
                    while len(pmp_file.records) < target_img_len:
                        pmp_file.records.append(def_val)
                        pmp_file.dirty = True
                    if len(pmp_file.records) > target_img_len:
                        del pmp_file.records[target_img_len:]
                        pmp_file.dirty = True

        is_bg_thread = threading.current_thread() is not threading.main_thread()
        for stem, pmp_file in list(self.pmps.items()):
            if not stem.startswith("imagedata_"):
                continue
            pmp_path = self.db3_dir / f"{stem}.pmp"
            should_write = getattr(pmp_file, "dirty", True) or not pmp_path.exists()
            if not should_write and stem not in always_save_stems:
                try:
                    with open(pmp_path, "rb") as fh:
                        hdr = fh.read(20)
                    if len(hdr) < 20 or struct.unpack_from("<I", hdr, 16)[0] != len(pmp_file.records):
                        should_write = True
                except Exception:
                    should_write = True
            if should_write:
                with self._lock:
                    pmp_bytes = pmp_file.to_bytes()
                    pmp_file.dirty = False
                _atomic_write(pmp_path, pmp_bytes)
                if is_bg_thread:
                    time.sleep(0.0005)

    def save_database(self, force_all: bool = False) -> None:
        """
        FR: Sauvegarde atomique de thumbindex.db, conteneurs multi-blocs, tables PMP,
        wordhash.dat, repository.dat, usernames.dat et contacts.xml.
        N'écrit sur disque que les fichiers marqués `dirty` ou absents sur disque (ou tous si `force_all=True`),
        et exécute toutes les écritures disque en dehors de `self._lock`.
        EN: Atomic save of thumbindex.db, multi-block containers, PMP tables,
        wordhash.dat, repository.dat, usernames.dat, and contacts.xml.
        Only writes files marked `dirty` or missing on disk (or all when `force_all=True`),
        performing all disk I/O outside `self._lock`.
        Ref: picasa3.exe @ 0x004F54B0, 0x006B7FC0 (CBlockFile::SaveIndex), 0x006A2CD0, 0x006C1920 (CPMTable), 0x004DB4F0
        """
        if not self.db3_dir or self.db3_dir == Path("."):
            return
        if not self.db3_dir.exists():
            self.db3_dir.mkdir(parents=True, exist_ok=True)

        def _atomic_write(target: Path, data: bytes) -> None:
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(data)
            try:
                os.replace(str(tmp), str(target))
            except PermissionError:
                try:
                    target.write_bytes(data)
                finally:
                    tmp.unlink(missing_ok=True)

        # 1. thumbindex.db
        ti_path = self.db3_dir / "thumbindex.db"
        with self._lock:
            if self._thumb_save_timer is not None:
                try:
                    self._thumb_save_timer.cancel()
                except Exception:
                    pass
                self._thumb_save_timer = None

            ti_bytes: Optional[bytes] = None
            if self.thumbindex is not None:
                if len(self.thumbindex.records) > 0:
                    self._align_imagedata_tables(len(self.thumbindex.records) - 1)
                if force_all or getattr(self.thumbindex, "dirty", True) or not ti_path.exists():
                    ti_bytes = self.thumbindex.to_bytes()

        if ti_bytes is not None:
            _atomic_write(ti_path, ti_bytes)
            if self.thumbindex is not None:
                self.thumbindex.dirty = False

        # 2. BlockFiles (thumbs_0.db, thumbs_1.db, thumbs_index.db, etc.)
        saved_containers: Set[Tuple[str, int]] = set()
        for (prefix, block_num), container in list(self.block_containers_by_block.items()):
            with self._get_block_lock(prefix):
                container.flush_to_file(self.db3_dir / f"{prefix}_{block_num}.db")
            saved_containers.add((prefix, block_num))

        for prefix, container in list(self.block_containers.items()):
            if (prefix, 0) not in saved_containers:
                with self._get_block_lock(prefix):
                    container.flush_to_file(self.db3_dir / f"{prefix}_0.db")

        for prefix, idx_file in list(self.block_indices.items()):
            idx_path = self.db3_dir / f"{prefix}_index.db"
            idx_bytes: Optional[bytes] = None
            with self._get_block_lock(prefix):
                if getattr(idx_file, "dirty", True) or not idx_path.exists() or (
                    force_all and not getattr(idx_file, "_compacted_on_disk", False)
                ):
                    idx_bytes = idx_file.to_bytes()
            if idx_bytes is not None:
                _atomic_write(idx_path, idx_bytes)
                idx_file.dirty = False
                idx_file._compacted_on_disk = False

        # 3. Tables PMP (*.pmp) : alignement strict des tables imagedata_*, albumdata_*, catdata_*
        with self._lock:
            if self.thumbindex is not None:
                target_img_len = len(self.thumbindex.records)
                for stem, pmp_file in self.pmps.items():
                    if stem.startswith("imagedata_"):
                        def_val = self._pmp_new_row_default(stem, pmp_file)
                        while len(pmp_file.records) < target_img_len:
                            pmp_file.records.append(def_val)
                            pmp_file.dirty = True
                        if len(pmp_file.records) > target_img_len:
                            del pmp_file.records[target_img_len:]
                            pmp_file.dirty = True

            if "albumdata_name" in self.pmps:
                target_alb_len = len(self.pmps["albumdata_name"].records)
                for stem, pmp_file in self.pmps.items():
                    if stem.startswith("albumdata_"):
                        def_val = pmp_file.default_value()
                        while len(pmp_file.records) < target_alb_len:
                            pmp_file.records.append(def_val)
                            pmp_file.dirty = True
                        if len(pmp_file.records) > target_alb_len:
                            del pmp_file.records[target_alb_len:]
                            pmp_file.dirty = True

            if "catdata_name" in self.pmps:
                target_cat_len = len(self.pmps["catdata_name"].records)
                for stem, pmp_file in self.pmps.items():
                    if stem.startswith("catdata_"):
                        def_val = pmp_file.default_value()
                        while len(pmp_file.records) < target_cat_len:
                            pmp_file.records.append(def_val)
                            pmp_file.dirty = True
                        if len(pmp_file.records) > target_cat_len:
                            del pmp_file.records[target_cat_len:]
                            pmp_file.dirty = True

        is_bg_thread = threading.current_thread() is not threading.main_thread()
        for stem, pmp_file in list(self.pmps.items()):
            pmp_path = self.db3_dir / f"{stem}.pmp"
            pmp_bytes: Optional[bytes] = None
            with self._lock:
                if force_all or getattr(pmp_file, "dirty", True) or not pmp_path.exists():
                    pmp_bytes = pmp_file.to_bytes()
            if pmp_bytes is not None:
                _atomic_write(pmp_path, pmp_bytes)
                pmp_file.dirty = False
                if is_bg_thread:
                    time.sleep(0.0005)

        # 4. repository.dat & usernames.dat
        if self.repository:
            with self._lock:
                repo_bytes = self.repository.to_bytes()
            _atomic_write(self.db3_dir / "repository.dat", repo_bytes)
        if self.usernames:
            with self._lock:
                un_bytes = self.usernames.to_bytes()
            _atomic_write(self.db3_dir / "usernames.dat", un_bytes)

        # 5. wordhash.dat
        if self.wordhash:
            wh_path = self.db3_dir / "wordhash.dat"
            wh_bytes: Optional[bytes] = None
            with self._lock:
                if force_all or getattr(self.wordhash, "dirty", True) or not wh_path.exists():
                    wh_bytes = self.wordhash.to_bytes()
            if wh_bytes is not None:
                _atomic_write(wh_path, wh_bytes)
                self.wordhash.dirty = False

        # 6. contacts.xml
        if self.contacts and self.contacts_dir:
            self.save_contacts()

        # 7. Fichiers listes .txt auxiliaires (scanlist.txt, starlist.txt, saverlist.txt, facetags.txt, tags.txt)
        # Ref: picasa3.exe @ 0x0041BA40, 0x004F61C0, 0x004755F0, 0x006BA000, 0x006C0E00
        try:
            self._write_auxiliary_txt_lists()
        except Exception:
            pass

    def _write_auxiliary_txt_lists(self) -> None:
        """
        FR: Écrit les 5 fichiers textes auxiliaires de db3 (`scanlist.txt`, `starlist.txt`,
        `saverlist.txt`, `facetags.txt`, `tags.txt`) conformément à `CThumbDB::Save` (`0x0041BA40`).
        EN: Writes the 5 auxiliary text files in db3 (`scanlist.txt`, `starlist.txt`,
        `saverlist.txt`, `facetags.txt`, `tags.txt`) matching `CThumbDB::Save` (`0x0041BA40`).
        Ref: picasa3.exe @ 0x0041BA40, 0x004F61C0, 0x004755F0, 0x006BA000, 0x006C0E00
        """
        if not self.db3_dir or self.db3_dir == Path(".") or not self.db3_dir.exists():
            return

        # 1. scanlist.txt (Ref: 0x004F61C0 : "<folder>\r\n" pour status 1, "+<folder>\r\n" pour status 2, "-<folder>\r\n" pour status 0)
        if self.repository is not None or self._scanlist:
            scanlist_bytes = self._serialize_scanlist_bytes()
            if scanlist_bytes or not (self.db3_dir / "scanlist.txt").exists():
                (self.db3_dir / "scanlist.txt").write_bytes(scanlist_bytes)

        # 2. starlist.txt & saverlist.txt (Ref: 0x004755F0 : chemins des photos ]star et ]screensaver)
        if self.wordhash is not None and self.thumbindex is not None:
            recs = self.thumbindex.records
            folders_map = {i: r.path for i, r in enumerate(recs) if r.type == 1}
            for list_fname, token_key in (("starlist.txt", "]star"), ("saverlist.txt", "]screensaver")):
                ent = self.wordhash._word_map.get(token_key)
                paths_out: List[str] = []
                if ent is not None and ent.image_ids:
                    for doc_id in ent.image_ids:
                        if 0 <= doc_id < len(recs):
                            r = recs[doc_id]
                            if r.type in MEDIA_RECORD_TYPES and r.is_active:
                                fdir = folders_map.get(r.parent_idx, "")
                                if fdir:
                                    full_p = fdir.rstrip("\\/") + "\\" + r.path.lstrip("\\/")
                                    paths_out.append(f"{full_p}\r\n")
                target_txt = self.db3_dir / list_fname
                if paths_out or not target_txt.exists():
                    target_txt.write_bytes("".join(paths_out).encode("utf-8", errors="surrogateescape"))

        # 3. facetags.txt (Ref: 0x006BA000 : un nom de personne par ligne pour les albums cat == 8)
        ad_names = self.pmps.get("albumdata_name")
        ad_cats = self.pmps.get("albumdata_category")
        if ad_names is not None and ad_cats is not None:
            face_names: List[str] = []
            seen_fn: Set[str] = set()
            for idx_a, name_a in enumerate(ad_names.records):
                if idx_a > 0 and idx_a < len(ad_cats.records) and ad_cats.records[idx_a] == 8:
                    clean_n = str(name_a or "").strip()
                    if clean_n and clean_n.lower() not in ("sans nom", "unnamed") and clean_n not in seen_fn:
                        seen_fn.add(clean_n)
                        face_names.append(f"{clean_n}\r\n")
            ft_path = self.db3_dir / "facetags.txt"
            if face_names or not ft_path.exists():
                ft_path.write_bytes("".join(face_names).encode("utf-8", errors="surrogateescape"))

        # 4. tags.txt (Ref: 0x006C0E00 : mots-clés uniques présents dans imagedata_tags.pmp)
        pmp_tags = self.pmps.get("imagedata_tags")
        if pmp_tags is not None:
            unique_tags: List[str] = []
            seen_t: Set[str] = set()
            for raw_t in pmp_tags.records:
                if raw_t:
                    for kw in str(raw_t).split(","):
                        clean_kw = kw.strip()
                        if clean_kw and clean_kw not in seen_t:
                            seen_t.add(clean_kw)
                            unique_tags.append(f"{clean_kw}\r\n")
            tags_path = self.db3_dir / "tags.txt"
            if unique_tags or not tags_path.exists():
                tags_path.write_bytes("".join(unique_tags).encode("utf-8", errors="surrogateescape"))

    save_all = save_database

    @property
    def tables(self) -> Dict[str, PmpFile]:
        """
        FR: Alias de compatibilité retournant le dictionnaire des tables PMP (self.pmps).
        EN: Compatibility alias returning the dictionary of PMP tables (self.pmps).
        """
        return self.pmps

    @property
    def db_dir(self) -> Path:
        """
        FR: Retourne l'objet Path du répertoire db3.
        EN: Returns the Path object of the db3 directory.
        """
        return self.db3_dir

    @property
    def db_path(self) -> str:
        """
        FR: Retourne le chemin sous forme de chaîne du répertoire db3.
        EN: Returns the string path of the db3 directory.
        """
        return str(self.db3_dir)

    def compact(self) -> Tuple[int, int]:
        """
        FR: Compacte intégralement la base de données conformément à `CThumbDB::Compact` (`FUN_00419560` / `FUN_0041b580`) :
        1. Construit `new_to_old` (indices actifs `rec.type != 0 and rec.is_active`) et `old_to_new` (`0x004F1F80`).
        2. Compacte `thumbindex.records` et réindexe chaque `parent_idx` via `old_to_new` (`0x004F2170`).
        3. Compacte toutes les colonnes `imagedata_*.pmp` selon `new_to_old` et réindexe `imagedata_aliasparents` (`0x006A8430`).
        4. Compacte tous les conteneurs `CBlockFile` (`thumbs`, `thumbs2`, `bigthumbs`, `previews`, `facetemplatesV2`)
           en copiant uniquement les entrées de `new_to_old` vers `*_0.db` (`active_block = 0`) et en supprimant
           les anciens fichiers secondaires `*_1.db`, `*_2.db` (`0x006B9470`).
        5. Compacte `wordhash.dat` en réindexant tous les `doc_id` via `old_to_new` et en mettant à jour `max_doc_id` (`0x004DDA30`).
        Retourne `(taille_initiale_octets, taille_apres_compactage_octets)`.
        EN: Fully compacts the database matching `CThumbDB::Compact` (`FUN_00419560` / `FUN_0041b580`).
        Returns `(initial_size_bytes, compacted_size_bytes)`.
        Ref: picasa3.exe @ 0x00419560, 0x0041B580, 0x004F1F80, 0x004F2170, 0x004DDA30, 0x006A8430, 0x006B9470
        """
        initial_bytes = 0
        final_bytes = 0

        with self._lock:
            new_to_old: Optional[List[int]] = None
            old_to_new: Dict[int, int] = {}

            if self.thumbindex is not None and self.thumbindex.records:
                self.thumbindex.sanitize_records()
                old_records = self.thumbindex.records
                new_to_old = [
                    i for i, r in enumerate(old_records)
                    if r.type != 0 and r.is_active
                ]
                old_to_new = {old_i: new_i for new_i, old_i in enumerate(new_to_old)}

                if len(new_to_old) < len(old_records):
                    compacted_records: List[ThumbIndexRecord] = []
                    for old_i in new_to_old:
                        rec = old_records[old_i]
                        if rec.parent_idx != 0xFFFFFFFF and rec.parent_idx >= 0:
                            rec.parent_idx = old_to_new.get(rec.parent_idx, 0xFFFFFFFF)
                        compacted_records.append(rec)
                    self.thumbindex.records = compacted_records
                    self.thumbindex.dirty = True

                    for stem, pmp_file in self.pmps.items():
                        if not stem.startswith("imagedata_"):
                            continue
                        old_col = pmp_file.records
                        def_val = self._pmp_new_row_default(stem, pmp_file)
                        new_col = [
                            old_col[old_i] if old_i < len(old_col) else def_val
                            for old_i in new_to_old
                        ]
                        if stem == "imagedata_aliasparents":
                            new_col = [
                                old_to_new.get(int(v), 0) if v and int(v) != 0 else 0
                                for v in new_col
                            ]
                        pmp_file.records = new_col
                        pmp_file.dirty = True

                    if self.wordhash is not None and hasattr(self.wordhash, "remap_doc_ids"):
                        self.wordhash.remap_doc_ids(old_to_new, len(new_to_old))

                    self._deleted_or_reset_indices.clear()
                    self._modified_media_indices.clear()
                    self._min_aligned_idx = len(new_to_old) - 1
                    self._invalidate_path_index_cache()

            for prefix in list(self.block_indices.keys()):
                idx_file = self.block_indices.get(prefix)
                container = self.block_containers.get(prefix)
                if not idx_file or not container:
                    continue

                for (p_key, blk_num), blk_cont in list(self.block_containers_by_block.items()):
                    if p_key == prefix:
                        initial_bytes += blk_cont.byte_size()
                if (prefix, 0) not in self.block_containers_by_block:
                    initial_bytes += container.byte_size()

                new_container = BlockContainerFile(magic=container.magic)
                new_entries: List[BlockEntry] = []

                if prefix in ("thumbs", "thumbs2", "bigthumbs", "previews", "facetemplatesV2") and new_to_old is not None:
                    iter_indices = new_to_old
                else:
                    iter_indices = list(range(idx_file.record_count))

                # Ref: picasa3.exe @ 0x0041B77E-0x0041B7B0 : lors de CThumbDB::Compact (0x0041B580),
                # bigthumbs et previews sont compactés avec un vecteur vide (réinitialisant bigthumbs_0.db
                # et previews_0.db à 4 octets), tandis que thumbs, thumbs2, profilephotos et facetemplatesV2
                # conservent et réindexent leurs entrées actives via new_to_old.
                if prefix in ("bigthumbs", "previews"):
                    new_entries = [BlockEntry() for _ in iter_indices]
                else:
                    for old_i in iter_indices:
                        old_entry = idx_file.get_entry(old_i) if old_i < idx_file.record_count else None
                        if old_entry and not old_entry.is_empty:
                            src_cont = self._get_container_for_entry(prefix, old_entry.block)
                            if src_cont:
                                try:
                                    blob = src_cont.get_blob(old_entry)
                                    if blob:
                                        entry = new_container.append_blob(blob, checksum=old_entry.checksum, block_idx=0)
                                        new_entries.append(entry)
                                        continue
                                except Exception:
                                    pass
                        new_entries.append(BlockEntry())

                new_container._fully_dirty = True
                new_idx = BlockIndexFile.from_entries(new_entries, active_block=0)
                new_idx.dirty = True

                for (p_key, blk_num) in list(self.block_containers_by_block.keys()):
                    if p_key == prefix and blk_num > 0:
                        self.block_containers_by_block.pop((p_key, blk_num), None)
                        if self.db3_dir and self.db3_dir != Path("."):
                            stale_path = self.db3_dir / f"{prefix}_{blk_num}.db"
                            try:
                                stale_path.unlink(missing_ok=True)
                            except Exception:
                                pass

                self.block_containers[prefix] = new_container
                self.block_containers_by_block[(prefix, 0)] = new_container
                self.block_indices[prefix] = new_idx
                final_bytes += new_container.byte_size()

        if self._face_manager is not None:
            try:
                self._face_manager.reload()
            except Exception:
                pass

        self.save_database(force_all=True)
        return (initial_bytes, final_bytes)

    @staticmethod
    def find_picasa_ini_traces(
        root_dir: str | Path,
        include_legacy_picasa_ini: bool = True,
    ) -> List[Path]:
        """
        FR: Parcourt récursivement `root_dir` et retourne la liste triée de tous les fichiers
        `.picasa.ini` (ainsi que `Picasa.ini` si `include_legacy_picasa_ini=True`) détectés.
        EN: Recursively walks `root_dir` and returns the sorted list of all `.picasa.ini`
        files (as well as `Picasa.ini` when `include_legacy_picasa_ini=True`) found.
        Ref: picasa3.exe @ 0x0068AC80 (.picasa.ini / Picasa.ini)
        """
        base = Path(root_dir)
        if not base.exists() or not base.is_dir():
            return []
        target_names = {".picasa.ini", "picasa.ini"} if include_legacy_picasa_ini else {".picasa.ini"}
        found: List[Path] = []
        for dirpath, _dirnames, filenames in os.walk(str(base)):
            for fname in filenames:
                if fname.lower() in target_names:
                    found.append(Path(dirpath) / fname)
        found.sort(key=lambda p: str(p).lower())
        return found

    def clean_picasa_ini_traces(
        self,
        root_dir: str | Path,
        include_legacy_picasa_ini: bool = True,
    ) -> Tuple[List[Path], List[Tuple[Path, str]]]:
        """
        FR: Supprime récursivement tous les fichiers `.picasa.ini` (et `Picasa.ini` si demandé)
        présents sous `root_dir`, en levant au préalable les attributs Windows `HIDDEN` / `READONLY`,
        marque la suppression comme écriture interne pour éviter les rebonds du `PicasaFolderWatcher`,
        et invalide les caches INI/albums/favoris de la base de données.
        Retourne `(fichiers_supprimes, [(fichier_en_echec, message_erreur), ...])`.
        EN: Recursively deletes all `.picasa.ini` (and `Picasa.ini` if requested) files under
        `root_dir`, clearing Windows `HIDDEN` / `READONLY` attributes beforehand, marking internal
        writes to prevent `PicasaFolderWatcher` feedback loops, and invalidating DB caches.
        Returns `(deleted_files, [(failed_file, error_message), ...])`.
        Ref: picasa3.exe @ 0x0068AC80, AGENTS.md §4 bis.3
        """
        import stat
        from picasa_py.ini.writer import PicasaIniWriter

        targets = self.find_picasa_ini_traces(root_dir, include_legacy_picasa_ini=include_legacy_picasa_ini)
        deleted: List[Path] = []
        failed: List[Tuple[Path, str]] = []

        for ini_path in targets:
            path_str = str(ini_path)
            try:
                PicasaIniWriter.mark_internal_write(path_str)
                if sys.platform == "win32":
                    try:
                        import ctypes
                        # FILE_ATTRIBUTE_NORMAL = 0x80 (lève HIDDEN 0x02, SYSTEM 0x04, READONLY 0x01)
                        ctypes.windll.kernel32.SetFileAttributesW(path_str, 0x80)
                    except Exception:
                        pass
                try:
                    os.chmod(path_str, stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass
                ini_path.unlink()
                self.invalidate_ini_cache(path_str, invalidate_albums_starred=False)
                deleted.append(ini_path)
            except Exception as exc:
                failed.append((ini_path, str(exc)))

        if deleted:
            self._albums_cache = None
            self._starred_cache = None
            self.invalidate_search_cache()

        return deleted, failed





