"""
FR: Module de lecture et d'écriture du fichier thumbindex.db (Picasa File & Folder Index).
EN: Module for reading and writing the thumbindex.db file (Picasa File & Folder Index).

Traçabilité Ghidra / Ghidra Traceability:
- Fonction d'écriture / Write function : picasa3.exe @ 0x004F54B0 (FUN_004f54b0 -> SaveThumbIndex)
- Fonction de lecture / Read function : picasa3.exe @ 0x004F25F0 (FUN_004f25f0 -> ReadThumbIndex)
- Magic number : 0x40466666 (flottant 3.1f stocké à 0x00CF4F4C / float 3.1f stored at 0x00CF4F4C)
- Sérialisation chaîne / String serialization : picasa3.exe @ 0x00996DB0 (FUN_00996db0 -> WriteNullTerminatedString)
- Sérialisation métadonnées / Metadata serialization : picasa3.exe @ 0x004F571B (fwrite 30 octets fixes / 30 fixed bytes)
"""

from __future__ import annotations
import os
from pathlib import Path
import struct
from dataclasses import dataclass
from typing import Iterator, List, Optional, Union


# Ref: picasa3.exe @ 0x00CF4F4C
THUMBINDEX_MAGIC = 0x40466666  # 3.1f en IEEE 754 float32 / 3.1f in IEEE 754 float32
THUMBINDEX_ACTIVE_FLAG = 0x0100  # Ref: picasa3.exe @ 0x004F54B0 (*(char *)(entry + 0x1d) != 0)
EPOCH_AS_FILETIME = 116444736000000000  # 1er janvier 1970 en intervalles de 100 ns depuis 1601 / Jan 1, 1970 in 100-ns intervals since 1601
HUNDREDS_OF_NANOSECONDS = 10000000

# FR: En-tête : magic (uint32), record_count (uint32) / EN: Header: magic (uint32), record_count (uint32)
HEADER_STRUCT = struct.Struct("<II")

# FR: Métadonnées d'un enregistrement : 30 octets fixes / EN: Record metadata: 30 fixed bytes
# ft1 (uint64), ft2 (uint64), size (uint32), type (uint32), flags (uint16), parent_idx (uint32)
META_STRUCT = struct.Struct("<QQIIHI")
META_SIZE = 30


def unix_to_filetime(ts: float) -> int:
    """
    FR: Convertit un timestamp Unix (secondes) en FILETIME Windows 64 bits.
    EN: Converts a Unix timestamp (seconds) into a 64-bit Windows FILETIME.
    """
    if ts <= 0:
        return 0
    return int(ts * HUNDREDS_OF_NANOSECONDS) + EPOCH_AS_FILETIME


def filetime_to_unix(ft: int) -> float:
    """
    FR: Convertit un FILETIME Windows 64 bits en timestamp Unix (secondes).
    EN: Converts a 64-bit Windows FILETIME into a Unix timestamp (seconds).
    """
    if ft <= EPOCH_AS_FILETIME:
        return 0.0
    return (ft - EPOCH_AS_FILETIME) / float(HUNDREDS_OF_NANOSECONDS)


@dataclass(init=False)
class ThumbIndexRecord:
    """
    FR: Enregistrement individuel dans thumbindex.db (dossier, fichier média ou visage).
    EN: Individual record in thumbindex.db (folder, media file, or face).
    """
    path: str
    ft1: int
    ft2: int
    size: int
    type: int
    flags: int
    parent_idx: int

    def __init__(
        self,
        path: str = "",
        ft1: int = 0,
        ft2: int = 0,
        size: int = 0,
        type: int = 0,
        flags: int = 0,
        parent_idx: int = 0xFFFFFFFF,
        *,
        mod_time: Optional[float] = None,
        version: Optional[int] = None,
        flags_lo: Optional[int] = None,
        flags_hi: Optional[int] = None,
    ):
        """
        FR: Initialise un enregistrement de thumbindex.db.
        EN: Initializes a thumbindex.db record.
        """
        self.path = path
        self.ft1 = int(ft1)
        self.ft2 = int(ft2)
        self.size = int(version) if version is not None else int(size)
        self.type = int(type)
        self.flags = int(flags)
        self.parent_idx = int(parent_idx)
        self._flags_hi_modified = False
        self._flags_hi_explicit = flags_hi is not None

        if mod_time is not None:
            self.mod_time = float(mod_time)
        if flags_lo is not None:
            self.flags_lo = int(flags_lo)
        if flags_hi is not None:
            self.flags = (self.flags & 0x00FF) | ((int(flags_hi) & 0xFF) << 8)

    @property
    def flags_lo(self) -> int:
        """
        FR: Octet de poids faible du champ `flags` (`+0x1c`).
        EN: Low byte of the `flags` field (`+0x1c`).
        Ref: picasa3.exe @ 0x004F54B0
        """
        return self.flags & 0xFF

    @flags_lo.setter
    def flags_lo(self, value: int) -> None:
        """
        FR: Modifie l'octet de poids faible du champ `flags` (`+0x1c`).
        EN: Sets the low byte of the `flags` field (`+0x1c`).
        """
        self.flags = (self.flags & 0xFF00) | (int(value) & 0xFF)

    @property
    def flags_hi(self) -> int:
        """
        FR: Octet de poids fort du champ `flags` (`+0x1d`, indicateur d'entrée active).
        EN: High byte of the `flags` field (`+0x1d`, active entry indicator).
        Ref: picasa3.exe @ 0x004F54B0
        """
        return (self.flags >> 8) & 0xFF

    @flags_hi.setter
    def flags_hi(self, value: int) -> None:
        """
        FR: Modifie l'octet de poids fort du champ `flags` (`+0x1d`).
        EN: Sets the high byte of the `flags` field (`+0x1d`).
        """
        self.flags = (self.flags & 0x00FF) | ((int(value) & 0xFF) << 8)
        self._flags_hi_modified = True

    @property
    def mod_time(self) -> float:
        """
        FR: Horodatage de modification Unix (secondes flottantes) converti depuis `ft1` / `ft2`.
        EN: Unix modification timestamp (float seconds) converted from `ft1` / `ft2`.
        """
        if self.ft1:
            return filetime_to_unix(self.ft1)
        if self.ft2:
            return filetime_to_unix(self.ft2)
        return 0.0

    @mod_time.setter
    def mod_time(self, value: float) -> None:
        """
        FR: Met à jour `ft1` et `ft2` à partir d'un horodatage Unix (secondes flottantes).
        EN: Updates `ft1` and `ft2` from a Unix timestamp (float seconds).
        """
        ft = unix_to_filetime(float(value)) if value and value > 0 else 0
        self.ft1 = ft
        self.ft2 = ft

    @property
    def version(self) -> int:
        """
        FR: Champ taille/version 32 bits (`size`) de l'enregistrement.
        EN: 32-bit size/version field (`size`) of the record.
        """
        return self.size

    @version.setter
    def version(self, value: int) -> None:
        """
        FR: Modifie le champ taille/version 32 bits (`size`) de l'enregistrement.
        EN: Sets the 32-bit size/version field (`size`) of the record.
        """
        self.size = int(value)

    @property
    def file_size(self) -> int:
        """
        FR: Retourne la taille du fichier en octets.
        EN: Returns the file size in bytes.
        """
        return self.size

    @file_size.setter
    def file_size(self, value: int) -> None:
        """
        FR: Modifie la taille du fichier en octets.
        EN: Sets the file size in bytes.
        """
        self.size = int(value)

    @property
    def mtime(self) -> int:
        """
        FR: Retourne l'horodatage de modification Unix (secondes) à partir de ft2.
        EN: Returns the Unix modification timestamp (seconds) from ft2.
        """
        return int(filetime_to_unix(self.ft2)) if self.ft2 else 0

    @mtime.setter
    def mtime(self, value: int) -> None:
        """
        FR: Met à jour ft2 à partir d'un horodatage Unix (secondes).
        EN: Updates ft2 from a Unix timestamp (seconds).
        """
        self.ft2 = unix_to_filetime(float(value)) if value else 0

    @property
    def is_active(self) -> bool:
        """
        FR: Indique si l'entrée a le bit d'activité positionné dans l'octet haut de flags (+0x1d).
        EN: Indicates whether the entry has the active flag set in the high byte of flags (+0x1d).
        Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex)
        """
        return (self.flags & 0xFF00) != 0

    def mark_deleted(self) -> None:
        """
        FR: Invalide l'enregistrement exactement comme SaveThumbIndex (FUN_004f54b0 @ 0x004F54B0).
        EN: Invalidates the record exactly like SaveThumbIndex (FUN_004f54b0 @ 0x004F54B0).
        """
        self.path = ""
        self.ft1 = 0
        self.ft2 = 0
        self.size = 0
        self.type = 0
        self.flags = 0
        self.parent_idx = 0xFFFFFFFF

    # Ref: picasa3.exe @ 0x004F571B
    def to_bytes(self, encoding: str = "utf-8") -> bytes:
        """
        FR: Sérialise l'enregistrement (chaîne terminée par zéro + 30 octets de métadonnées).
        EN: Serializes the record (null-terminated string + 30 bytes of metadata).
        """
        encoded_path = self.path.encode(encoding, errors="surrogateescape") + b"\x00"
        meta_bytes = META_STRUCT.pack(
            self.ft1 & 0xFFFFFFFFFFFFFFFF,
            self.ft2 & 0xFFFFFFFFFFFFFFFF,
            self.size & 0xFFFFFFFF,
            self.type & 0xFFFFFFFF,
            self.flags & 0xFFFF,
            self.parent_idx & 0xFFFFFFFF,
        )
        return encoded_path + meta_bytes


class ThumbIndexFile:
    """
    FR: Représente le fichier thumbindex.db complet.
    Garantit une sérialisation/désérialisation bit-exacte.
    EN: Represents the complete thumbindex.db file.
    Guarantees bit-exact serialization and deserialization.
    """

    def __init__(self, magic: int = THUMBINDEX_MAGIC, records: List[ThumbIndexRecord] | None = None, dirty: bool = False):
        """
        FR: Initialise une instance de ThumbIndexFile avec son magic number, ses enregistrements et son flag `dirty`.
        EN: Initializes a ThumbIndexFile instance with its magic number, records, and `dirty` flag.
        Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex)
        """
        self.magic = magic
        self.records: List[ThumbIndexRecord] = records if records is not None else []
        self.dirty: bool = dirty

    def __len__(self) -> int:
        return len(self.records)

    def __bool__(self) -> bool:
        return True

    def __iter__(self) -> Iterator[ThumbIndexRecord]:
        return iter(self.records)

    def __getitem__(self, idx: int) -> ThumbIndexRecord:
        return self.records[idx]

    @classmethod
    # Ref: picasa3.exe @ 0x004F46B0 (ReadThumbIndex), 0x004F25F0 (DumpThumbIndex)
    def from_bytes(cls, data: bytes, encoding: str = "utf-8") -> ThumbIndexFile:
        """
        FR: Désérialise thumbindex.db depuis un buffer binaire.
        EN: Deserializes thumbindex.db from a binary byte buffer.
        """
        if len(data) < 8:
            raise ValueError(f"Fichier thumbindex.db trop court : {len(data)} octets (min 8)")

        magic, record_count = HEADER_STRUCT.unpack_from(data, 0)
        if magic != THUMBINDEX_MAGIC:
            raise ValueError(f"Magic thumbindex invalide : 0x{magic:08X} (attendu 0x{THUMBINDEX_MAGIC:08X})")

        pos = 8
        records: List[ThumbIndexRecord] = []
        data_len = len(data)

        for i in range(record_count):
            null_pos = data.find(b"\x00", pos)
            if null_pos == -1:
                raise ValueError(f"Délimiteur null manquant pour le chemin à l'entrée {i} (pos {pos})")

            raw_path = data[pos:null_pos]
            path = raw_path.decode(encoding, errors="surrogateescape")
            pos = null_pos + 1

            if pos + META_SIZE > data_len:
                raise ValueError(f"Données tronquées pour les métadonnées de l'entrée {i} (attendu {META_SIZE} octets à pos {pos})")

            ft1, ft2, size, ftype, flags, parent_idx = META_STRUCT.unpack_from(data, pos)
            pos += META_SIZE

            rec = ThumbIndexRecord(
                path=path,
                ft1=ft1,
                ft2=ft2,
                size=size,
                type=ftype,
                flags=flags,
                parent_idx=parent_idx,
            )
            rec._flags_hi_modified = False
            rec._flags_hi_explicit = False
            records.append(rec)

        if pos != data_len:
            raise ValueError(f"Octets excédentaires à la fin de thumbindex.db : {data_len - pos} octets non consommés")

        return cls(magic=magic, records=records)

    def sanitize_records(self) -> None:
        """
        FR: Nettoie les entrées inactives (`flags_hi == 0` ou `type == 0`) ou orphelines conformément à SaveThumbIndex (`FUN_004f54b0` @ `0x004F54B0`).
        EN: Sanitizes inactive (`flags_hi == 0` or `type == 0`) or orphaned entries in accordance with SaveThumbIndex (`FUN_004f54b0` @ `0x004F54B0`).
        """
        count = len(self.records)
        for rec in self.records:
            if rec.type == 0 or rec.flags_hi == 0:
                rec.mark_deleted()
            elif rec.type == 4 and (rec.parent_idx < 0 or rec.parent_idx >= count or rec.parent_idx == 0xFFFFFFFF):
                rec.mark_deleted()

    # Ref: picasa3.exe @ 0x004F54B0
    def to_bytes(self, encoding: str = "utf-8", sanitize: bool = False) -> bytes:
        """
        FR: Sérialise l'intégralité de thumbindex.db en octets.
        EN: Serializes the entire thumbindex.db into bytes.
        """
        if sanitize:
            self.sanitize_records()
        else:
            count = len(self.records)
            for rec in self.records:
                if rec.type == 0 or (
                    rec.flags_hi == 0
                    and (getattr(rec, "_flags_hi_modified", False) or getattr(rec, "_flags_hi_explicit", False) or rec.path == "")
                ):
                    rec.mark_deleted()
                elif rec.type == 4 and (rec.parent_idx < 0 or rec.parent_idx >= count or rec.parent_idx == 0xFFFFFFFF):
                    rec.mark_deleted()
        parts: List[bytes] = [HEADER_STRUCT.pack(self.magic, len(self.records))]
        for rec in self.records:
            parts.append(rec.to_bytes(encoding=encoding))
        return b"".join(parts)

    def write(self, path: Union[str, Path], encoding: str = "utf-8") -> None:
        """
        FR: Écrit `thumbindex.db` sur disque en appliquant le nettoyage des enregistrements supprimés/inactifs (`FUN_004f54b0`).
        EN: Writes `thumbindex.db` to disk while sanitizing deleted/inactive records (`FUN_004f54b0`).
        Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex)
        """
        data = self.to_bytes(encoding=encoding, sanitize=True)
        abs_path = os.path.abspath(str(path))
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        tmp_path = abs_path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(data)
        os.replace(tmp_path, abs_path)
        self.dirty = False

    @classmethod
    def read(cls, path: Union[str, Path], encoding: str = "utf-8") -> ThumbIndexFile:
        """
        FR: Lit et désérialise `thumbindex.db` depuis le disque (`FUN_004f46b0`).
        EN: Reads and deserializes `thumbindex.db` from disk (`FUN_004f46b0`).
        Ref: picasa3.exe @ 0x004F46B0 (ReadThumbIndex)
        """
        return cls.from_bytes(Path(path).read_bytes(), encoding=encoding)

    def save(self, path: Union[str, Path], encoding: str = "utf-8") -> None:
        """
        FR: Sauvegarde atomique de thumbindex.db sur disque.
        EN: Atomically saves thumbindex.db to disk.
        """
        self.write(path, encoding=encoding)


ThumbIndex = ThumbIndexFile

