"""
Module de lecture et d'écriture du fichier thumbindex.db (Picasa File & Folder Index).

Traçabilité Ghidra :
- Fonction d'écriture : picasa3.exe @ 0x004F54B0 (FUN_004f54b0 -> SaveThumbIndex)
- Fonction de lecture : picasa3.exe @ 0x004F25F0 (FUN_004f25f0 -> ReadThumbIndex)
- Magic number : 0x40466666 (flottant 3.1f stocké à 0x00CF4F4C)
- Sérialisation chaîne : picasa3.exe @ 0x00996DB0 (FUN_00996db0 -> WriteNullTerminatedString)
- Sérialisation métadonnées : picasa3.exe @ 0x004F571B (fwrite 30 octets fixes)
"""

from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import List, Union


# Ref: picasa3.exe @ 0x00CF4F4C
THUMBINDEX_MAGIC = 0x40466666  # 3.1f en IEEE 754 float32

# En-tête : magic (uint32), record_count (uint32)
HEADER_STRUCT = struct.Struct("<II")

# Métadonnées d'un enregistrement : 30 octets fixes
# ft1 (uint64), ft2 (uint64), size (uint32), type (uint32), flags (uint16), parent_idx (uint32)
META_STRUCT = struct.Struct("<QQIIHI")
META_SIZE = 30


@dataclass
class ThumbIndexRecord:
    """
    Enregistrement individuel dans thumbindex.db.
    """
    path: str
    ft1: int
    ft2: int
    size: int
    type: int
    flags: int
    parent_idx: int

    @property
    def file_size(self) -> int:
        return self.size

    # Ref: picasa3.exe @ 0x004F571B
    def to_bytes(self, encoding: str = "utf-8") -> bytes:
        encoded_path = self.path.encode(encoding) + b"\x00"
        meta_bytes = META_STRUCT.pack(
            self.ft1,
            self.ft2,
            self.size,
            self.type,
            self.flags,
            self.parent_idx,
        )
        return encoded_path + meta_bytes


class ThumbIndexFile:
    """
    Représente le fichier thumbindex.db complet.
    Garantit une sérialisation/désérialisation bit-exacte.
    """

    def __init__(self, magic: int = THUMBINDEX_MAGIC, records: List[ThumbIndexRecord] | None = None):
        self.magic = magic
        self.records: List[ThumbIndexRecord] = records if records is not None else []

    @classmethod
    # Ref: picasa3.exe @ 0x004F25F0
    def from_bytes(cls, data: bytes, encoding: str = "utf-8") -> ThumbIndexFile:
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

            records.append(ThumbIndexRecord(
                path=path,
                ft1=ft1,
                ft2=ft2,
                size=size,
                type=ftype,
                flags=flags,
                parent_idx=parent_idx,
            ))

        if pos != data_len:
            raise ValueError(f"Octets excédentaires à la fin de thumbindex.db : {data_len - pos} octets non consommés")

        return cls(magic=magic, records=records)

    # Ref: picasa3.exe @ 0x004F54B0
    def to_bytes(self, encoding: str = "utf-8") -> bytes:
        parts: List[bytes] = [HEADER_STRUCT.pack(self.magic, len(self.records))]
        for rec in self.records:
            parts.append(rec.to_bytes(encoding=encoding))
        return b"".join(parts)
