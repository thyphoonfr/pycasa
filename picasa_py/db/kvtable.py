"""
FR: Module de lecture et d'écriture des fichiers de tables clé-valeur (repository.dat, usernames.dat).
EN: Module for reading and writing binary key-value table files (repository.dat, usernames.dat).

Traçabilité Ghidra / Ghidra Traceability:
- Magic number : 0x3FCCCCCD (1.6f float32 à l'adresse globale _DAT_00d678e0)
- Références fichier / File references : picasa3.exe @ 0x0041415A (repository.dat), 0x00416652 (usernames.dat)
- Vtable : 0x00C827F8
"""

from __future__ import annotations
import struct
from typing import Dict, List, Optional, Tuple


KV_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32 / 1.6f in IEEE 754 float32
HEADER_STRUCT = struct.Struct("<II")


class KeyValueTableFile:
    """
    FR: Représente un fichier de paires clé-valeur binaire (ex. repository.dat, usernames.dat).
    Préserve strictement l'ordre d'origine des paires pour garantir le round-trip bit-exact.
    EN: Represents a binary key-value pair file (e.g., repository.dat, usernames.dat).
    Strictly preserves the original pair order to guarantee bit-exact round-trip serialization.
    """

    def __init__(self, magic: int = KV_MAGIC, pairs: List[Tuple[str, str]] | None = None):
        """
        FR: Initialise la table clé-valeur avec son magic number et sa liste ordonnée de paires.
        EN: Initializes the key-value table with its magic number and ordered list of pairs.
        """
        self.magic = magic
        self.pairs: List[Tuple[str, str]] = pairs if pairs is not None else []

    @property
    def mapping(self) -> Dict[str, str]:
        """
        FR: Retourne les paires sous forme de dictionnaire Python.
        EN: Returns the key-value pairs as a Python dictionary.
        """
        return dict(self.pairs)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        FR: Recherche la valeur associée à une clé ou retourne default.
        EN: Looks up the value associated with a key or returns default.
        """
        for k, v in self.pairs:
            if k == key:
                return v
        return default

    def set(self, key: str, value: str) -> None:
        """
        FR: Met à jour la valeur d'une clé existante sur place, ou l'ajoute en fin de table.
        EN: Updates the value of an existing key in place, or appends it at the end of the table.
        """
        for i, (k, _) in enumerate(self.pairs):
            if k == key:
                self.pairs[i] = (key, str(value))
                return
        self.pairs.append((key, str(value)))

    def remove(self, key: str) -> bool:
        """
        FR: Supprime une clé de la table si elle existe.
        EN: Removes a key from the table if it exists.
        """
        for i, (k, _) in enumerate(self.pairs):
            if k == key:
                del self.pairs[i]
                return True
        return False

    @classmethod
    def from_bytes(cls, data: bytes, encoding: str = "utf-8") -> KeyValueTableFile:
        """
        FR: Désérialise une table clé-valeur binaire depuis un buffer d'octets.
        EN: Deserializes a binary key-value table from a byte buffer.
        """
        if len(data) < 8:
            raise ValueError(f"Fichier de table clé-valeur trop court : {len(data)} octets (min 8)")

        magic, pair_count = HEADER_STRUCT.unpack_from(data, 0)
        if magic != KV_MAGIC:
            raise ValueError(f"Magic clé-valeur invalide : 0x{magic:08X} (attendu 0x{KV_MAGIC:08X})")

        pos = 8
        pairs: List[Tuple[str, str]] = []
        data_len = len(data)

        for i in range(pair_count):
            # FR: Lecture de la clé / EN: Read key string
            null1 = data.find(b"\x00", pos)
            if null1 == -1:
                raise ValueError(f"Délimiteur null manquant pour la clé à la paire {i} (pos {pos})")
            key = data[pos:null1].decode(encoding, errors="surrogateescape")
            pos = null1 + 1

            # FR: Lecture de la valeur / EN: Read value string
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
        """
        FR: Sérialise la table clé-valeur au format binaire exact de Picasa 3.
        EN: Serializes the key-value table into the exact Picasa 3 binary format.
        """
        parts: List[bytes] = [HEADER_STRUCT.pack(self.magic, len(self.pairs))]
        for k, v in self.pairs:
            parts.append(k.encode(encoding, errors="surrogateescape") + b"\x00")
            parts.append(v.encode(encoding, errors="surrogateescape") + b"\x00")
        return b"".join(parts)

