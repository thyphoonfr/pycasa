"""
Module de lecture et d'écriture du fichier wordhash.dat (Index de recherche inversé par mot-clé).

Traçabilité Ghidra :
- Magic number : 0x3FCCCCCD (1.6f float32 à l'adresse globale _DAT_00d678e0)
- Écriture globale : picasa3.exe @ 0x004DB4F0 (FUN_004db4f0)
- Lecture globale : picasa3.exe @ 0x004DB720 (FUN_004db720)
- Écriture du pool de chaînes : picasa3.exe @ 0x00A61700 (FUN_00a61700)
- Lecture du pool de chaînes : picasa3.exe @ 0x00A617B0 (FUN_00a617b0)
- Écriture de la table d'index : picasa3.exe @ 0x00704500 (FUN_00704500)
- Lecture de la table d'index : picasa3.exe @ 0x007046E0 (FUN_007046e0)
- Écriture de vecteur colonne : picasa3.exe @ 0x0099C1E0 (FUN_0099c1e0)
"""

from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import Dict, List, Tuple


WORDHASH_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32
HEADER_STRUCT = struct.Struct("<II")
POOL_HEADER_STRUCT = struct.Struct("<III")


@dataclass
class WordEntry:
    word: str
    str_offset: int
    image_ids: List[int]


class WordHashFile:
    """
    Représente le fichier wordhash.dat complet.
    Permet la lecture, la recherche et la ré-écriture bit-exacte.
    """

    def __init__(
        self,
        magic: int = WORDHASH_MAGIC,
        max_doc_id: int = 0,
        chunk_size: int = 65536,
        used_bytes: int | None = None,
        pool_bytes: bytes | None = None,
        entries: List[WordEntry] | None = None,
    ):
        self.magic = magic
        self.max_doc_id = max_doc_id
        self.chunk_size = chunk_size
        self.used_bytes = used_bytes
        self.pool_bytes = pool_bytes if pool_bytes is not None else b""
        self.entries: List[WordEntry] = entries if entries is not None else []

    @classmethod
    # Ref: picasa3.exe @ 0x004DB720 / 0x007046E0
    def from_bytes(cls, data: bytes) -> WordHashFile:
        if len(data) < 20:
            raise ValueError(f"Fichier wordhash.dat trop court : {len(data)} octets (min 20)")

        magic, max_doc_id = HEADER_STRUCT.unpack_from(data, 0)
        if magic != WORDHASH_MAGIC:
            raise ValueError(f"Magic wordhash invalide : 0x{magic:08X} (attendu 0x{WORDHASH_MAGIC:08X})")

        pos = 8
        chunk_count, chunk_size, used_bytes = POOL_HEADER_STRUCT.unpack_from(data, pos)
        pos += 12

        pool_len = chunk_count * chunk_size
        if pos + pool_len > len(data):
            raise ValueError(f"Pool de chaînes wordhash tronqué : {pool_len} octets attendus")

        pool_bytes = data[pos : pos + pool_len]
        pos += pool_len

        if pos + 4 > len(data):
            raise ValueError("Nombre d'entrées wordhash manquant")

        word_count = struct.unpack_from("<I", data, pos)[0]
        pos += 4

        entries: List[WordEntry] = []
        for i in range(word_count):
            if pos + 8 > len(data):
                raise ValueError(f"Entrée wordhash {i} tronquée")
            str_off = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            count = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            if pos + count * 4 > len(data):
                raise ValueError(f"Vecteur d'images de l'entrée {i} tronqué : {count} IDs attendus")
            items = list(struct.unpack_from(f"<{count}I", data, pos))
            pos += count * 4

            null_idx = pool_bytes.find(b"\x00", str_off)
            word = pool_bytes[str_off:null_idx].decode("utf-8", errors="surrogateescape")
            entries.append(WordEntry(word=word, str_offset=str_off, image_ids=items))

        if pos != len(data):
            raise ValueError(f"Octets excédentaires à la fin de wordhash.dat : {len(data) - pos} octets")

        return cls(
            magic=magic,
            max_doc_id=max_doc_id,
            chunk_size=chunk_size,
            used_bytes=used_bytes,
            pool_bytes=pool_bytes,
            entries=entries,
        )

    # Ref: picasa3.exe @ 0x004DB4F0 / 0x00704500
    def to_bytes(self) -> bytes:
        chunk_size = self.chunk_size if self.chunk_size > 0 else 65536
        # Si pool_bytes est fourni, on calcule le nombre de chunks
        pool_len = len(self.pool_bytes)
        chunk_count = (pool_len + chunk_size - 1) // chunk_size if pool_len > 0 else 1
        total_pool_alloc = chunk_count * chunk_size
        padded_pool = self.pool_bytes.ljust(total_pool_alloc, b"\x00")

        # Calcul des used_bytes
        if self.used_bytes is not None:
            used_bytes = self.used_bytes
        else:
            last_null = padded_pool.rfind(b"\x00")
            used_bytes = (last_null + 1) if last_null != -1 else len(self.pool_bytes)

        parts: List[bytes] = [
            HEADER_STRUCT.pack(self.magic, self.max_doc_id),
            POOL_HEADER_STRUCT.pack(chunk_count, chunk_size, used_bytes),
            padded_pool,
            struct.pack("<I", len(self.entries)),
        ]

        for entry in self.entries:
            count = len(entry.image_ids)
            parts.append(struct.pack(f"<II{count}I", entry.str_offset, count, *entry.image_ids))

        return b"".join(parts)
