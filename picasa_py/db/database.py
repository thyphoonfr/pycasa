"""
Gestionnaire unifié de base de données Picasa (db3 et contacts).

Permet l'accès de haut niveau à l'ensemble des données de la photothèque :
- Dossiers et arborescence (thumbindex.db)
- Propriétés colonnes (tables .pmp : imagedata, albumdata, catdata)
- Miniatures et caches d'images (CBlockFile : thumbs, thumbs2, bigthumbs, previews)
- Contacts et visages (contacts.xml, facetemplatesV2)
- Métadonnées du référentiel (repository.dat, usernames.dat)
- Index inversé de recherche (wordhash.dat)
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Optional

from picasa_py.db.pmp import PmpFile
from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord
from picasa_py.db.blockfile import BlockIndexFile, BlockContainerFile
from picasa_py.db.kvtable import KeyValueTableFile
from picasa_py.db.wordhash import WordHashFile
from picasa_py.db.contacts import ContactsFile, Contact


class PicasaDatabase:
    """
    Instance complète d'une base de données Picasa 3.
    """

    def __init__(self, db3_dir: Path, contacts_dir: Path | None = None):
        self.db3_dir = db3_dir
        self.contacts_dir = contacts_dir

        self.thumbindex: Optional[ThumbIndexFile] = None
        self.repository: Optional[KeyValueTableFile] = None
        self.usernames: Optional[KeyValueTableFile] = None
        self.wordhash: Optional[WordHashFile] = None
        self.contacts: Optional[ContactsFile] = None

        self.pmps: Dict[str, PmpFile] = {}
        self.block_indices: Dict[str, BlockIndexFile] = {}
        self.block_containers: Dict[str, BlockContainerFile] = {}

    @classmethod
    def open_default(cls) -> PicasaDatabase:
        localappdata = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2"))
        db3_dir = localappdata / "db3"
        contacts_dir = localappdata / "contacts"
        db = cls(db3_dir=db3_dir, contacts_dir=contacts_dir)
        db.load_all()
        return db

    def load_all(self) -> None:
        """Charge l'ensemble des fichiers disponibles dans le répertoire de base de données."""
        if not self.db3_dir.exists():
            return

        # 1. thumbindex.db
        ti_path = self.db3_dir / "thumbindex.db"
        if ti_path.exists():
            self.thumbindex = ThumbIndexFile.from_bytes(ti_path.read_bytes())

        # 2. repository.dat & usernames.dat
        repo_path = self.db3_dir / "repository.dat"
        if repo_path.exists():
            self.repository = KeyValueTableFile.from_bytes(repo_path.read_bytes())

        un_path = self.db3_dir / "usernames.dat"
        if un_path.exists():
            self.usernames = KeyValueTableFile.from_bytes(un_path.read_bytes())

        # 3. wordhash.dat
        wh_path = self.db3_dir / "wordhash.dat"
        if wh_path.exists():
            self.wordhash = WordHashFile.from_bytes(wh_path.read_bytes())

        # 4. Tables PMP
        for pmp_path in self.db3_dir.glob("*.pmp"):
            self.pmps[pmp_path.stem] = PmpFile.from_bytes(pmp_path.read_bytes())

        # 5. CBlockFile indices & conteneurs
        for idx_path in self.db3_dir.glob("*_index.db"):
            prefix = idx_path.stem.replace("_index", "")
            self.block_indices[prefix] = BlockIndexFile.from_bytes(idx_path.read_bytes())

            container_path = self.db3_dir / f"{prefix}_0.db"
            if container_path.exists():
                self.block_containers[prefix] = BlockContainerFile.from_bytes(container_path.read_bytes())

        # 6. contacts.xml
        if self.contacts_dir and (self.contacts_dir / "contacts.xml").exists():
            self.contacts = ContactsFile.from_xml((self.contacts_dir / "contacts.xml").read_text(encoding="utf-8"))

    @classmethod
    def open(cls, db3_dir: str | Path, contacts_dir: str | Path | None = None) -> PicasaDatabase:
        p_db3 = Path(db3_dir)
        p_cont = Path(contacts_dir) if contacts_dir else p_db3.parent / "contacts"
        db = cls(db3_dir=p_db3, contacts_dir=p_cont)
        db.load_all()
        return db

    @property
    def index(self) -> List[ThumbIndexRecord]:
        return self.thumbindex.records if self.thumbindex else []

    @property
    def catdata(self) -> Dict[str, PmpFile]:
        return {k.replace("catdata_", ""): v for k, v in self.pmps.items() if k.startswith("catdata_")}

    @property
    def search_index(self) -> Optional[WordHashFile]:
        return self.wordhash

    def search(self, word: str) -> List[int]:
        if not self.wordhash:
            return []
        return self.wordhash.search(word)

    def load_thumbnail(self, index: int, size: str = "small") -> Optional[bytes]:
        return self.get_thumbnail(index, size)

    def get_thumbnail(self, index: int, size: str = "small") -> Optional[bytes]:
        """
        Extrait la miniature d'une image à un index donné.
        size: "small" (thumbs), "medium" (thumbs2), "large" (bigthumbs), "preview" (previews).
        """
        prefix_map = {
            "small": "thumbs",
            "medium": "thumbs2",
            "large": "bigthumbs",
            "preview": "previews",
        }
        prefix = prefix_map.get(size, "thumbs")
        idx_file = self.block_indices.get(prefix)
        container = self.block_containers.get(prefix)
        if not idx_file or not container or index >= idx_file.record_count:
            return None

        entry = idx_file.get_entries()[index]
        if entry.is_empty:
            return None
        return container.get_blob(entry)

