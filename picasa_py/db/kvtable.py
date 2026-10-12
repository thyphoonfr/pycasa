"""
Module de lecture et d'écriture des fichiers de tables clé-valeur (repository.dat, usernames.dat).

Traçabilité Ghidra :
- Magic number : 0x3FCCCCCD (1.6f float32 à l'adresse globale _DAT_00d678e0)
- Références fichier : picasa3.exe @ 0x0041415A (repository.dat), 0x00416652 (usernames.dat)
- Vtable : 0x00C827F8
"""

from __future__ import annotations
import struct
from typing import Dict, List, Tuple


KV_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32
HEADER_STRUCT = struct.Struct("<II")


class KeyValueTableFile:
    """
    Représente un fichier de paires clé-valeur binaire (ex. repository.dat, usernames.dat).
    Préserve strictement l'ordre d'origine des paires pour garantir le round-trip bit-exact.
    """

    def __init__(self, magic: int = KV_MAGIC, pairs: List[Tuple[str, str]] | None = None):
        self.magic = magic
        self.pairs: List[Tuple[str, str]] = pairs if pairs is not None else []

    @property
    def mapping(self) -> Dict[str, str]:
        return dict(self.pairs)

    @classmethod
    def from_bytes(cls, data: bytes, encoding: str = "utf-8") -> KeyValueTableFile:
        if len(data) < 8:
            raise ValueError(f"Fichier de table clé-valeur trop court : {len(data)} octets (min 8)")

        magic, pair_count = HEADER_STRUCT.unpack_from(data, 0)
        if magic != KV_MAGIC:
            raise ValueError(f"Magic clé-valeur invalide : 0x{magic:08X} (attendu 0x{KV_MAGIC:08X})")

        pos = 8
        pairs: List[Tuple[str, str]] = []
        data_len = len(data)

        for i in range(pair_count):
            # Lecture de la clé
            null1 = data.find(b"\x00", pos)
            if null1 == -1:
                raise ValueError(f"Délimiteur null manquant pour la clé à la paire {i} (pos {pos})")
            key = data[pos:null1].decode(encoding, errors="surrogateescape")
            pos = null1 + 1

            # Lecture de la valeur
            null2 = data.find(b"\x00", pos)
            if null2 == -1:
                raise ValueError(f"Délimiteur null manquant pour la valeur à la paire {i} (pos {pos})")
            val = data[pos:null2].decode(encoding, errors="surrogateescape")
            pos = null2 + 1

            pairs.append((key, val))

        if pos != data_len:
            raise ValueError(f"Octets excédentaires à la fin du fichier clé-valeur : {data_len - pos} octets")

        return cls(magic=magic, pairs=pairs)

    def to_bytes(self, encoding: str = "utf-8") -> bytes:
        parts: List[bytes] = [HEADER_STRUCT.pack(self.magic, len(self.pairs))]
        for k, v in self.pairs:
            parts.append(k.encode(encoding, errors="surrogateescape") + b"\x00")
            parts.append(v.encode(encoding, errors="surrogateescape") + b"\x00")
        return b"".join(parts)
