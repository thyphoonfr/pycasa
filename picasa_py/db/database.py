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
from picasa_py.db.blockfile import BlockIndexFile, BlockContainerFile, BlockEntry
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

    def get_watched_folders(self) -> Dict[str, str]:
        """
        Renvoie le dictionnaire {chemin_dossier: statut} des dossiers configurés dans repository.dat.
        Statuts Picasa :
        "1" -> Toujours analyser (Scan Always)
        "2" -> Analyser une seule fois (Scan Once)
        "0" -> Supprimer de Picasa (Remove)
        Ref: picasa3.exe @ 0x008B7F90 (foldermgr/watched_folders, repository.dat)
        """
        if not self.repository:
            return {}
        res: Dict[str, str] = {}
        for k, v in self.repository.pairs:
            if (":" in k or "\\" in k or "/" in k) and v in ("0", "1", "2"):
                res[k] = v
        return res

    def set_watched_folder(self, folder_path: str, status: str) -> None:
        """
        Définit le statut d'un dossier dans repository.dat.
        """
        norm_path = folder_path.replace("/", "\\")
        if not norm_path.endswith("\\"):
            norm_path += "\\"
        if not self.repository:
            self.repository = KeyValueTableFile()
        self.repository.set(norm_path, str(status))

    def load_thumbnail(self, index: int, size: str = "small") -> Optional[bytes]:

        return self.get_thumbnail(index, size)

    def get_thumbnail_jpeg(self, index: int, size: str = "small") -> Optional[bytes]:
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

    def get_or_create_folder_index(self, folder_path: str) -> int:
        """
        Retrouve l'index de dossier (type == 1) dans thumbindex.db, ou en crée un nouveau.
        Ref: picasa3.exe @ 0x004F25F0
        """
        if not self.thumbindex:
            self.thumbindex = ThumbIndexFile()

        norm = folder_path.replace("/", "\\").rstrip("\\") + "\\"
        for idx, rec in enumerate(self.thumbindex.records):
            if rec.type == 1 and rec.path.lower() == norm.lower():
                return idx

        # Nouveau dossier à indexer
        new_rec = ThumbIndexRecord(
            path=norm,
            ft1=0,
            ft2=0,
            size=0,
            type=1,
            flags=0,
            parent_idx=0,
        )
        self.thumbindex.records.append(new_rec)
        return len(self.thumbindex.records) - 1

    def add_media_record(
        self, folder_path: str, filename: str, file_size: int, mtime: int = 0, media_type: int = 2
    ) -> int:
        """
        Ajoute un enregistrement d'image ou vidéo dans thumbindex.db.
        Ref: picasa3.exe @ 0x004F54B0
        """
        if not self.thumbindex:
            self.thumbindex = ThumbIndexFile()

        parent_idx = self.get_or_create_folder_index(folder_path)
        new_rec = ThumbIndexRecord(
            path=filename,
            ft1=0,
            ft2=0,
            size=file_size,
            type=media_type,
            flags=0,
            parent_idx=parent_idx,
        )
        self.thumbindex.records.append(new_rec)
        return len(self.thumbindex.records) - 1

    def add_thumbnail(self, index: int, jpeg_bytes: bytes, size: str = "small") -> None:
        """
        Écrit une vignette dans le conteneur CBlockFile et met à jour l'index.
        Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry)
        """
        prefix = "thumbs" if size == "small" else size
        idx_file = self.block_indices.get(prefix)
        container = self.block_containers.get(prefix)

        if not idx_file or not container:
            return

        entry = container.append_blob(jpeg_bytes)

        # Si l'index saute des positions, insérer des entrées vides de remplissage
        while idx_file.record_count < index:
            idx_file.append_entry(BlockEntry())

        if index < idx_file.record_count:
            idx_file.checksums[index] = entry.checksum
            idx_file.offsets[index] = entry.offset
            idx_file.sizes_and_blocks[index] = entry.raw_size_block
        else:
            idx_file.append_entry(entry)

    def save_database(self) -> None:
        """
        Sauvegarde atomique de thumbindex.db, conteneurs de vignettes et tables de référentiel.
        Ref: picasa3.exe @ 0x004F54B0, 0x006B7FC0
        """
        if not self.db3_dir.exists():
            self.db3_dir.mkdir(parents=True, exist_ok=True)

        # 1. thumbindex.db
        if self.thumbindex:
            ti_path = self.db3_dir / "thumbindex.db"
            tmp_ti = self.db3_dir / "thumbindex.db.tmp"
            tmp_ti.write_bytes(self.thumbindex.to_bytes())
            if ti_path.exists():
                ti_path.unlink()
            tmp_ti.rename(ti_path)

        # 2. BlockFiles (thumbs_0.db, thumbs_index.db, etc.)
        for prefix, container in self.block_containers.items():
            cont_path = self.db3_dir / f"{prefix}_0.db"
            tmp_cont = self.db3_dir / f"{prefix}_0.db.tmp"
            tmp_cont.write_bytes(container.to_bytes())
            if cont_path.exists():
                cont_path.unlink()
            tmp_cont.rename(cont_path)

        for prefix, idx_file in self.block_indices.items():
            idx_path = self.db3_dir / f"{prefix}_index.db"
            tmp_idx = self.db3_dir / f"{prefix}_index.db.tmp"
            tmp_idx.write_bytes(idx_file.to_bytes())
            if idx_path.exists():
                idx_path.unlink()
            tmp_idx.rename(idx_path)

        # 3. repository.dat
        if self.repository:
            rep_path = self.db3_dir / "repository.dat"
            tmp_rep = self.db3_dir / "repository.dat.tmp"
            tmp_rep.write_bytes(self.repository.to_bytes())
            if rep_path.exists():
                rep_path.unlink()
            tmp_rep.rename(rep_path)


