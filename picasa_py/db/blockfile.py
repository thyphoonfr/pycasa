"""
Module de lecture et d'écriture des conteneurs CBlockFile (*_0.db) et de leurs index (*_index.db).

Traçabilité Ghidra :
- Source originale : .\\thumblab\\CBlockFile.cpp @ 0x00CA847C, 0x00CA8487
- Magic number : 0x3FCCCCCD (1.6f float32 à l'adresse globale _DAT_00d678e0)
- Écriture d'index : picasa3.exe @ 0x006B7FC0 (FUN_006b7fc0 -> CBlockFile::SaveIndex)
- Lecture d'index : picasa3.exe @ 0x006B82E0 (FUN_006b82e0 -> CBlockFile::ReadIndex)
- Écriture d'entrée : picasa3.exe @ 0x006B75F0 (FUN_006b75f0 -> CBlockFile::WriteEntry)
- Validation des tables : picasa3.exe @ 0x006B8AC0 (FUN_006b8ac0 -> CBlockFile::InitTable)
- Sérialisation d'un vecteur colonne : picasa3.exe @ 0x0099C1E0 (FUN_0099c1e0)
- Sérialisation d'un bloc actif : picasa3.exe @ 0x00996D50 (FUN_00996d50)
- Format CSV de diagnostic : picasa3.exe @ 0x006B5E00 ("Size,Offset,Checksum\\n", "%d,%d,%d\\n")
"""

from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import List, Tuple, Optional


# Ref: picasa3.exe @ _DAT_00d678e0
BLOCKFILE_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32

# En-tête d'index : magic (uint32), active_block (uint32)
INDEX_HEADER_STRUCT = struct.Struct("<II")

# En-tête de container : magic (uint32)
CONTAINER_HEADER_STRUCT = struct.Struct("<I")


@dataclass
class BlockEntry:
    """
    Entrée individuelle pointée par l'index CBlockFile.
    """
    checksum: int = 0
    offset: int = 0
    size: int = 0
    block: int = 0

    @property
    def is_empty(self) -> bool:
        return self.size == 0 and self.offset == 0

    @property
    def raw_size_block(self) -> int:
        return ((self.block & 0xFF) << 24) | (self.size & 0x00FFFFFF)

    @classmethod
    def from_raw(cls, checksum: int, offset: int, raw_size_block: int) -> BlockEntry:
        block = (raw_size_block >> 24) & 0xFF
        size = raw_size_block & 0x00FFFFFF
        return cls(checksum=checksum, offset=offset, size=size, block=block)


class BlockIndexFile:
    """
    Représente un fichier d'index CBlockFile (*_index.db).
    Structure :
      - magic : 0x3FCCCCCD (4 octets)
      - active_block : uint32 (4 octets)
      - Vecteur 1 (Checksums) : count (uint32) + count * uint32
      - Vecteur 2 (Offsets) : count (uint32) + count * uint32
      - Vecteur 3 (Sizes & Blocks) : count (uint32) + count * uint32
    """

    def __init__(
        self,
        magic: int = BLOCKFILE_MAGIC,
        active_block: int = 0,
        checksums: List[int] | None = None,
        offsets: List[int] | None = None,
        sizes_and_blocks: List[int] | None = None,
    ):
        self.magic = magic
        self.active_block = active_block
        self.checksums: List[int] = checksums if checksums is not None else []
        self.offsets: List[int] = offsets if offsets is not None else []
        self.sizes_and_blocks: List[int] = sizes_and_blocks if sizes_and_blocks is not None else []

    @property
    def record_count(self) -> int:
        return len(self.checksums)

    def get_entries(self) -> List[BlockEntry]:
        count = self.record_count
        return [
            BlockEntry.from_raw(self.checksums[i], self.offsets[i], self.sizes_and_blocks[i])
            for i in range(count)
        ]

    @classmethod
    def from_entries(cls, entries: List[BlockEntry], active_block: int = 0) -> BlockIndexFile:
        checksums = [e.checksum for e in entries]
        offsets = [e.offset for e in entries]
        sizes_and_blocks = [e.raw_size_block for e in entries]
        return cls(
            magic=BLOCKFILE_MAGIC,
            active_block=active_block,
            checksums=checksums,
            offsets=offsets,
            sizes_and_blocks=sizes_and_blocks,
        )

    @classmethod
    # Ref: picasa3.exe @ 0x006B82E0 (ReadIndex)
    def from_bytes(cls, data: bytes) -> BlockIndexFile:
        if len(data) < 20:
            raise ValueError(f"Fichier *_index.db trop court : {len(data)} octets (min 20)")

        magic, active_block = INDEX_HEADER_STRUCT.unpack_from(data, 0)
        if magic != BLOCKFILE_MAGIC:
            raise ValueError(f"Magic index blockfile invalide : 0x{magic:08X} (attendu 0x{BLOCKFILE_MAGIC:08X})")

        pos = 8
        # Vecteur 1 : Checksums (Ref: picasa3.exe @ 0x006B81AE)
        c1 = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        if pos + c1 * 4 > len(data):
            raise ValueError(f"Vecteur checksums tronqué : {c1} éléments attendus")
        checksums = list(struct.unpack_from(f"<{c1}I", data, pos))
        pos += c1 * 4

        # Vecteur 2 : Offsets (Ref: picasa3.exe @ 0x006B81C4)
        c2 = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        if pos + c2 * 4 > len(data):
            raise ValueError(f"Vecteur offsets tronqué : {c2} éléments attendus")
        offsets = list(struct.unpack_from(f"<{c2}I", data, pos))
        pos += c2 * 4

        # Vecteur 3 : Sizes & Blocks (Ref: picasa3.exe @ 0x006B81DE)
        c3 = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        if pos + c3 * 4 > len(data):
            raise ValueError(f"Vecteur sizes_and_blocks tronqué : {c3} éléments attendus")
        sizes_and_blocks = list(struct.unpack_from(f"<{c3}I", data, pos))
        pos += c3 * 4

        if pos != len(data):
            raise ValueError(f"Données résiduelles dans *_index.db : {len(data) - pos} octets non consommés")

        if not (c1 == c2 == c3):
            raise ValueError(f"Incohérence du nombre d'éléments entre les vecteurs : c1={c1}, c2={c2}, c3={c3}")

        return cls(
            magic=magic,
            active_block=active_block,
            checksums=checksums,
            offsets=offsets,
            sizes_and_blocks=sizes_and_blocks,
        )

    # Ref: picasa3.exe @ 0x006B7FC0 (SaveIndex)
    def to_bytes(self) -> bytes:
        count = len(self.checksums)
        if len(self.offsets) != count or len(self.sizes_and_blocks) != count:
            raise ValueError("Les 3 vecteurs de BlockIndexFile doivent avoir la même longueur")

        parts: List[bytes] = [
            INDEX_HEADER_STRUCT.pack(self.magic, self.active_block),
            struct.pack(f"<I{count}I", count, *self.checksums),
            struct.pack(f"<I{count}I", count, *self.offsets),
            struct.pack(f"<I{count}I", count, *self.sizes_and_blocks),
        ]
        return b"".join(parts)


class BlockContainerFile:
    """
    Représente un fichier conteneur de données CBlockFile (*_0.db, *_1.db...).
    En-tête de 4 octets : magic 0x3FCCCCCD (1.6f).
    Suivi par les blobs de données brutes (images JPEG, modèles, etc.).
    """

    def __init__(self, magic: int = BLOCKFILE_MAGIC, data: bytes | None = None):
        self.magic = magic
        self.payload: bytearray = bytearray(data) if data is not None else bytearray()

    @classmethod
    # Ref: picasa3.exe @ 0x006B61E0 (OpenBlock)
    def from_bytes(cls, data: bytes) -> BlockContainerFile:
        if len(data) < 4:
            raise ValueError(f"Conteneur blockfile trop court : {len(data)} octets (min 4)")
        magic = struct.unpack_from("<I", data, 0)[0]
        if magic != BLOCKFILE_MAGIC:
            raise ValueError(f"Magic container blockfile invalide : 0x{magic:08X} (attendu 0x{BLOCKFILE_MAGIC:08X})")
        return cls(magic=magic, data=data[4:])

    # Ref: picasa3.exe @ 0x006B7FC0
    def to_bytes(self) -> bytes:
        return CONTAINER_HEADER_STRUCT.pack(self.magic) + bytes(self.payload)

    def get_blob(self, entry: BlockEntry) -> bytes:
        """
        Extrait le blob correspondant à l'entrée demandée.
        L'offset stocké dans l'entrée est relatif au fichier complet (offset >= 4).
        """
        if entry.is_empty:
            return b""
        if entry.offset < 4:
            raise ValueError(f"Offset d'entrée invalide : {entry.offset} (doit être >= 4)")
        rel_offset = entry.offset - 4
        end_offset = rel_offset + entry.size
        if end_offset > len(self.payload):
            raise ValueError(
                f"Entrée hors limites du container : offset={entry.offset}, taille={entry.size}, "
                f"fin={end_offset} > taille utile={len(self.payload)}"
            )
        return bytes(self.payload[rel_offset:end_offset])

    def append_blob(self, blob: bytes, checksum: int = 0, block_idx: int = 0) -> BlockEntry:
        """
        Ajoute un nouveau blob à la fin du conteneur et renvoie la BlockEntry correspondante.
        """
        abs_offset = len(self.payload) + 4
        size = len(blob)
        self.payload.extend(blob)
        return BlockEntry(checksum=checksum, offset=abs_offset, size=size, block=block_idx)
