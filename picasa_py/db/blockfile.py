"""
FR: Module de lecture et d'écriture des conteneurs CBlockFile (*_0.db) et de leurs index (*_index.db).
EN: Module for reading and writing CBlockFile containers (*_0.db) and their index files (*_index.db).

Traçabilité Ghidra / Ghidra Traceability:
- Source originale / Original source : .\\thumblab\\CBlockFile.cpp @ 0x00CA847C, 0x00CA8487
- Magic number : 0x3FCCCCCD (1.6f float32 à l'adresse globale _DAT_00d678e0)
- Écriture d'index / Index write : picasa3.exe @ 0x006B7FC0 (FUN_006b7fc0 -> CBlockFile::SaveIndex)
- Lecture d'index / Index read : picasa3.exe @ 0x006B82E0 (FUN_006b82e0 -> CBlockFile::ReadIndex)
- Écriture d'entrée / Entry write : picasa3.exe @ 0x006B75F0 (FUN_006b75f0 -> CBlockFile::WriteEntry)
- Validation des tables / Table validation : picasa3.exe @ 0x006B8AC0 (FUN_006b8ac0 -> CBlockFile::InitTable)
- Sérialisation d'un vecteur colonne / Column vector serialization : picasa3.exe @ 0x0099C1E0 (FUN_0099c1e0)
- Sérialisation d'un bloc actif / Active block serialization : picasa3.exe @ 0x00996D50 (FUN_00996d50)
- Format CSV de diagnostic / Diagnostic CSV format : picasa3.exe @ 0x006B5E00 ("Size,Offset,Checksum\\n", "%d,%d,%d\\n")
"""

from __future__ import annotations
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union


# Ref: picasa3.exe @ _DAT_00d678e0
BLOCKFILE_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32 / 1.6f in IEEE 754 float32
BLOCK_CONTAINER_MAGIC = BLOCKFILE_MAGIC

# FR: En-tête d'index : magic (uint32), active_block (uint32) / EN: Index header: magic (uint32), active_block (uint32)
INDEX_HEADER_STRUCT = struct.Struct("<II")

# FR: En-tête de container : magic (uint32) / EN: Container header: magic (uint32)
CONTAINER_HEADER_STRUCT = struct.Struct("<I")

# Ref: picasa3.exe @ 0x0048050B, 0x00482399 (facetemplatesV2_index.db checksum = 1)
FACETEMPLATE_BLOCK_CHECKSUM = 1
FACETEMPLATE_BLOB_SIZE = 1044
VQC_CUE_CLASS_ID = 0x00423002
VQC_CUE_FORMAT_ID = 0x0044DD4D


def _rol32(val: int, shift: int) -> int:
    """
    FR: Rotation circulaire 32 bits vers la gauche (instruction x86 ROL).
    EN: 32-bit circular rotate left (x86 ROL instruction).
    """
    val &= 0xFFFFFFFF
    shift &= 31
    return ((val << shift) | (val >> (32 - shift))) & 0xFFFFFFFF


# Ref: picasa3.exe @ 0x006B99F0 (FUN_006b99f0, full_hash=1) & 0x004E3AB0 (FUN_004e3ab0)
# Ghidra project: ghidra/picasa3.gpr
def compute_thumb_checksum(folder_path: str, filename: str, ft2: int, file_size: int) -> int:
    """
    FR: Calcule le checksum 32 bits exact stocké dans thumbs_index.db et thumbs2_index.db.
    Reproduit à l'identique la boucle de hachage insensible à la casse ASCII de FUN_006b99f0
    (seed 0x12345678, modulo 0xF4327 = 1000231) combinée par XOR avec les rotations de ft2 et size.
    EN: Computes the exact 32-bit checksum stored in thumbs_index.db and thumbs2_index.db.
    Faithfully reproduces the ASCII case-insensitive hash loop of FUN_006b99f0
    (seed 0x12345678, modulo 0xF4327 = 1000231) XOR-combined with bit rotations of ft2 and size.
    """
    h = 0x12345678
    for text in (folder_path, filename):
        raw = text.encode("utf-8", errors="surrogateescape")
        for b in raw:
            if b == 0:
                break
            if 0x41 <= b <= 0x5A:
                c = b + 0x20
            elif b >= 0x80:
                c = b - 256
            else:
                c = b
            term = ((h << 5) + c + (h >> 2)) & 0xFFFFFFFF
            h = (h ^ term) & 0xFFFFFFFF

    h = h % 0xF4327
    ft2_lo = ft2 & 0xFFFFFFFF
    ft2_hi = (ft2 >> 32) & 0xFFFFFFFF
    sz = file_size & 0xFFFFFFFF
    edx = _rol32(ft2_hi, 0x11) ^ _rol32(sz, 0x12) ^ _rol32(ft2_lo, 0x0D)
    return (h ^ edx) & 0xFFFFFFFF


# Ref: picasa3.exe @ 0x006B9B26 (FUN_006b99f0, full_hash=0) & 0x0042AD1E (FUN_0042a800)
# Ghidra project: ghidra/picasa3.gpr
def compute_preview_checksum(ft2: int, rotate_step: int = 0, flip: int = 0) -> int:
    """
    FR: Calcule le checksum 32 bits exact stocké dans bigthumbs_index.db et previews_index.db.
    Arrondit le FILETIME ft2 à la seconde la plus proche ((ft2 + 5_000_000) // 10_000_000),
    applique les rotations ROL 13 et ROL 17, puis applique le masque d'orientation (((flip * 4) ^ rotate_step) << 4).
    EN: Computes the exact 32-bit checksum stored in bigthumbs_index.db and previews_index.db.
    Rounds FILETIME ft2 to the nearest second ((ft2 + 5_000_000) // 10_000_000),
    applies ROL 13 and ROL 17 rotations, then XORs the orientation mask (((flip * 4) ^ rotate_step) << 4).
    """
    q = ((ft2 & 0xFFFFFFFFFFFFFFFF) + 0x4C4B40) // 0x989680
    q_lo = q & 0xFFFFFFFF
    q_hi = (q >> 32) & 0xFFFFFFFF
    base = (_rol32(q_lo, 0x0D) ^ _rol32(q_hi, 0x11)) & 0xFFFFFFFF
    orient_mask = ((((1 if flip else 0) * 4) ^ (rotate_step & 3)) << 4) & 0xFFFFFFFF
    return (base ^ orient_mask) & 0xFFFFFFFF


# Ref: Red.dll @ 0x1003E510 (template consistency check) & 0x10102020 (vqc_Cue::exportArr)
def verify_face_template_blob(blob: bytes) -> bool:
    """
    FR: Vérifie l'intégrité binaire d'un gabarit facial vqc_Cue de 1044 octets dans facetemplatesV2_0.db :
    - u[0] == 1044 (0x0414), u[1] == 0x00423002 (vqc_Cue), u[3] == 0x0044DD4D (format ID)
    - Somme modulo 2^32 des 261 uint32 égale à 0xFFFFFFFF (-1), équilibrée par u[10] à +0x28.
    EN: Verifies the binary integrity of a 1044-byte vqc_Cue face template in facetemplatesV2_0.db:
    - u[0] == 1044 (0x0414), u[1] == 0x00423002 (vqc_Cue), u[3] == 0x0044DD4D (format ID)
    - Modulo 2^32 sum of all 261 uint32 words equals 0xFFFFFFFF (-1), balanced by u[10] at +0x28.
    """
    if len(blob) < FACETEMPLATE_BLOB_SIZE:
        return False
    byte_len = struct.unpack_from("<I", blob, 0)[0]
    if byte_len != FACETEMPLATE_BLOB_SIZE or (byte_len >> 2) > 0xFFFF:
        return False
    n_words = byte_len >> 2
    words = struct.unpack_from(f"<{n_words}I", blob, 0)
    if words[1] != VQC_CUE_CLASS_ID or words[3] != VQC_CUE_FORMAT_ID:
        return False
    return (sum(words) & 0xFFFFFFFF) == 0xFFFFFFFF


# Ref: Red.dll @ 0x10102020 (vqc_Cue::exportArr) & 0x10102100 (vqc_Cue::importArr)
def encode_face_template_blob(
    nibbles: List[int] | bytes | bytearray,
    inv_norm: float,
    image_stamp: int = 0,
) -> bytes:
    """
    FR: Encode un gabarit facial vqc_Cue en bloc binaire exact de 1044 octets pour facetemplatesV2_0.db.
    - nibbles : séquence de 2000 valeurs entières 4 bits non signées (0..15) ou 1000 octets déjà packés.
    - inv_norm : facteur de normalisation float32 (1.0 / sqrt(rawSim(cue, cue))).
    - image_stamp : horodatage/identifiant d'image uint32 (+0x20).
    Calcule le mot d'équilibrage u[10] (+0x28) tel que sum(u[0..260]) & 0xFFFFFFFF == 0xFFFFFFFF.
    EN: Encodes a vqc_Cue facial template into an exact 1044-byte binary block for facetemplatesV2_0.db.
    - nibbles: sequence of 2000 unsigned 4-bit integers (0..15) or 1000 pre-packed bytes.
    - inv_norm: float32 normalization factor (1.0 / sqrt(rawSim(cue, cue))).
    - image_stamp: uint32 image timestamp/identifier (+0x20).
    Computes balancing word u[10] (+0x28) such that sum(u[0..260]) & 0xFFFFFFFF == 0xFFFFFFFF.
    """
    if isinstance(nibbles, (bytes, bytearray)) and len(nibbles) == 1000:
        packed_bytes = bytes(nibbles)
    else:
        q_list = list(nibbles)
        if len(q_list) != 2000:
            raise ValueError(f"vqc_Cue requires 2000 4-bit nibbles, got {len(q_list)}")
        buf = bytearray(1000)
        for i in range(1000):
            q_lo = max(0, min(15, int(q_list[2 * i])))
            q_hi = max(0, min(15, int(q_list[2 * i + 1])))
            buf[i] = (q_lo & 0x0F) | ((q_hi & 0x0F) << 4)
        packed_bytes = bytes(buf)

    inv_norm_u32 = struct.unpack("<I", struct.pack("<f", float(inv_norm)))[0]
    header_9 = (
        FACETEMPLATE_BLOB_SIZE,  # u[0] = 1044 (0x0414)
        VQC_CUE_CLASS_ID,        # u[1] = 0x00423002 (vqc_Cue)
        0,                       # u[2] = 0 (version)
        VQC_CUE_FORMAT_ID,       # u[3] = 0x0044DD4D (cue_format_id)
        2000,                    # u[4] = 2000 (size)
        4,                       # u[5] = 4 (bits)
        8,                       # u[6] = 8 (pack_size)
        inv_norm_u32,            # u[7] = inv_norm (float32 bits)
        image_stamp & 0xFFFFFFFF,# u[8] = image_stamp (uint32)
        250,                     # u[9] = 250 (uint32 data words)
    )
    data_words = struct.unpack("<250I", packed_bytes)
    partial_sum = (sum(header_9) + sum(data_words)) & 0xFFFFFFFF
    checksum_u10 = (0xFFFFFFFF - partial_sum) & 0xFFFFFFFF
    return struct.pack("<11I", *header_9, checksum_u10) + packed_bytes


def decode_face_template_blob(blob: bytes) -> Optional[tuple[bytes, float, int]]:
    """
    FR: Décode un bloc binaire vqc_Cue de 1044 octets en (packed_1000_bytes, inv_norm, image_stamp).
    Retourne None si le bloc est invalide.
    EN: Decodes a 1044-byte vqc_Cue binary block into (packed_1000_bytes, inv_norm, image_stamp).
    Returns None if the block is invalid.
    Ref: Red.dll @ 0x10102100 (vqc_Cue::importArr)
    """
    if not verify_face_template_blob(blob):
        return None
    inv_norm = float(struct.unpack_from("<f", blob, 0x1C)[0])
    image_stamp = int(struct.unpack_from("<I", blob, 0x20)[0])
    return blob[0x2C:0x414], inv_norm, image_stamp


@dataclass
class BlockEntry:
    """
    FR: Entrée individuelle pointée par l'index CBlockFile.
    EN: Individual entry pointed to by a CBlockFile index.
    """
    checksum: int = 0
    offset: int = 0
    size: int = 0
    block: int = 0

    @property
    def is_empty(self) -> bool:
        """
        FR: Indique si l'entrée est vide (taille et offset nuls).
        EN: Indicates whether the entry is empty (zero size and offset).
        """
        return self.size == 0 and self.offset == 0

    @property
    def raw_size_block(self) -> int:
        """
        FR: Combine l'indice de bloc (8 bits hauts) et la taille (24 bits bas).
        EN: Packs the block index (upper 8 bits) and blob size (lower 24 bits).
        """
        if self.size > 0x00FFFFFF:
            raise ValueError(f"Taille de blob CBlockFile supérieure à 24 bits (max 16 Mo) : {self.size}")
        return ((self.block & 0xFF) << 24) | (self.size & 0x00FFFFFF)

    @classmethod
    def from_raw(cls, checksum: int, offset: int, raw_size_block: int) -> BlockEntry:
        """
        FR: Construit une BlockEntry depuis les valeurs brutes des 3 vecteurs parallèles.
        EN: Constructs a BlockEntry from raw values of the 3 parallel vectors.
        """
        block = (raw_size_block >> 24) & 0xFF
        size = raw_size_block & 0x00FFFFFF
        return cls(checksum=checksum, offset=offset, size=size, block=block)

    def __int__(self) -> int:
        return self.offset

    def __index__(self) -> int:
        return self.offset

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BlockEntry):
            return (
                self.checksum == other.checksum
                and self.offset == other.offset
                and self.size == other.size
                and self.block == other.block
            )
        if isinstance(other, int):
            return self.offset == other
        return NotImplemented

    def __add__(self, other: int) -> int:
        if isinstance(other, int):
            return self.offset + other
        return NotImplemented

    def __radd__(self, other: int) -> int:
        if isinstance(other, int):
            return other + self.offset
        return NotImplemented

    def __sub__(self, other: int) -> int:
        if isinstance(other, int):
            return self.offset - other
        return NotImplemented

    def __ge__(self, other: int) -> bool:
        if isinstance(other, int):
            return self.offset >= other
        return NotImplemented

    def __gt__(self, other: int) -> bool:
        if isinstance(other, int):
            return self.offset > other
        return NotImplemented

    def __le__(self, other: int) -> bool:
        if isinstance(other, int):
            return self.offset <= other
        return NotImplemented

    def __lt__(self, other: int) -> bool:
        if isinstance(other, int):
            return self.offset < other
        return NotImplemented


class BlockIndexFile:
    """
    FR: Représente un fichier d'index CBlockFile (*_index.db).
    Structure :
      - magic : 0x3FCCCCCD (4 octets)
      - active_block : uint32 (4 octets)
      - Vecteur 1 (Checksums) : count (uint32) + count * uint32
      - Vecteur 2 (Offsets) : count (uint32) + count * uint32
      - Vecteur 3 (Sizes & Blocks) : count (uint32) + count * uint32
    EN: Represents a CBlockFile index file (*_index.db).
    Structure:
      - magic: 0x3FCCCCCD (4 bytes)
      - active_block: uint32 (4 bytes)
      - Vector 1 (Checksums): count (uint32) + count * uint32
      - Vector 2 (Offsets): count (uint32) + count * uint32
      - Vector 3 (Sizes & Blocks): count (uint32) + count * uint32
    """

    def __init__(
        self,
        magic: int = BLOCKFILE_MAGIC,
        active_block: int = 0,
        checksums: List[int] | None = None,
        offsets: List[int] | None = None,
        sizes_and_blocks: List[int] | None = None,
        dirty: bool = False,
    ):
        """
        FR: Initialise l'index CBlockFile avec ses 3 vecteurs parallèles et son flag d'état modifié (`dirty`).
        EN: Initializes the CBlockFile index with its 3 parallel vectors and its modified state flag (`dirty`).
        Ref: picasa3.exe @ 0x006B7FC0 (CBlockFile::SaveIndex)
        """
        self.magic = magic
        self.active_block = active_block
        self.checksums: List[int] = checksums if checksums is not None else []
        self.offsets: List[int] = offsets if offsets is not None else []
        self.sizes_and_blocks: List[int] = sizes_and_blocks if sizes_and_blocks is not None else []
        self.dirty: bool = dirty

    @property
    def record_count(self) -> int:
        """
        FR: Retourne le nombre total d'entrées dans l'index.
        EN: Returns the total number of entries in the index.
        """
        return len(self.checksums)

    def get_entry(self, index: int) -> Optional[BlockEntry]:
        """
        FR: Accès direct en O(1) sans allouer la liste complète des enregistrements.
        EN: Direct O(1) entry lookup without allocating the full list of records.
        """
        if 0 <= index < len(self.checksums):
            return BlockEntry.from_raw(self.checksums[index], self.offsets[index], self.sizes_and_blocks[index])
        return None

    def get_entries(self) -> List[BlockEntry]:
        """
        FR: Retourne la liste complète des entrées BlockEntry.
        EN: Returns the full list of BlockEntry objects.
        """
        count = self.record_count
        return [
            BlockEntry.from_raw(self.checksums[i], self.offsets[i], self.sizes_and_blocks[i])
            for i in range(count)
        ]

    def set_entry(self, index: int, entry: BlockEntry) -> None:
        """
        FR: Définit ou remplace l'entrée d'index à la position `index` et marque l'index comme modifié (`dirty`).
        EN: Sets or replaces the index entry at position `index` and marks the index as modified (`dirty`).
        Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry), 0x006B7FC0 (CBlockFile::SaveIndex)
        """
        while len(self.checksums) <= index:
            self.checksums.append(0)
            self.offsets.append(0)
            self.sizes_and_blocks.append(0)
        self.checksums[index] = entry.checksum
        self.offsets[index] = entry.offset
        self.sizes_and_blocks[index] = entry.raw_size_block
        self.dirty = True

    def append_entry(self, entry: BlockEntry) -> None:
        """
        FR: Ajoute une nouvelle entrée d'index dans les 3 vecteurs et marque l'index comme modifié (`dirty`).
        EN: Appends a new index entry across the 3 parallel vectors and marks the index as modified (`dirty`).
        """
        self.checksums.append(entry.checksum)
        self.offsets.append(entry.offset)
        self.sizes_and_blocks.append(entry.raw_size_block)
        self.dirty = True

    @classmethod
    def from_entries(cls, entries: List[BlockEntry], active_block: int = 0) -> BlockIndexFile:
        """
        FR: Crée un BlockIndexFile à partir d'une liste d'objets BlockEntry.
        EN: Creates a BlockIndexFile from a list of BlockEntry objects.
        """
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
        """
        FR: Désérialise un fichier *_index.db depuis un buffer d'octets.
        EN: Deserializes a *_index.db file from a byte buffer.
        """
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
        """
        FR: Sérialise le fichier *_index.db en octets little-endian.
        EN: Serializes the *_index.db file into little-endian bytes.
        """
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
    FR: Représente un fichier conteneur de données CBlockFile (*_0.db, *_1.db...).
    En-tête de 4 octets : magic 0x3FCCCCCD (1.6f).
    Suivi par les blobs de données brutes (images JPEG, modèles, etc.).
    Supporte un mode paresseux adossé au disque (`from_file`) afin de ne pas charger
    des centaines de Mo en RAM au démarrage.
    EN: Represents a CBlockFile data container file (*_0.db, *_1.db...).
    4-byte header: magic 0x3FCCCCCD (1.6f).
    Followed by raw data blobs (JPEG images, face templates, etc.).
    Supports a lazy disk-backed mode (`from_file`) to avoid loading hundreds of MB
    into RAM at startup.
    Ref: picasa3.exe @ 0x006B6AF0, 0x006B7390
    """

    def __init__(self, magic: int = BLOCKFILE_MAGIC, data: bytes | None = None):
        """
        FR: Initialise le conteneur CBlockFile avec son magic number et sa charge utile.
        EN: Initializes the CBlockFile container with its magic number and payload.
        """
        self.magic = magic
        self._backing_path: Optional[Path] = None
        self._disk_payload_len: int = 0
        self._payload: Optional[bytearray] = bytearray(data) if data is not None else bytearray()
        self._append_buf: bytearray = bytearray()
        self._patch_map: Dict[int, bytes] = {}
        self._dirty_ranges: List[Tuple[int, int]] = []
        self._fully_dirty: bool = False

    @property
    def payload(self) -> bytearray:
        """
        FR: Retourne la charge utile complète en mémoire, en la matérialisant paresseusement
        depuis `_backing_path` uniquement si un appelant accède directement à `container.payload`
        ou appelle `to_bytes()`.
        EN: Returns the full in-memory payload, lazily materializing it from `_backing_path`
        only if a caller accesses `container.payload` directly or calls `to_bytes()`.
        """
        if self._payload is None:
            buf = bytearray()
            if self._backing_path is not None and self._backing_path.exists() and self._disk_payload_len > 0:
                with open(self._backing_path, "rb") as f:
                    f.seek(4)
                    buf.extend(f.read(self._disk_payload_len))
            if len(buf) < self._disk_payload_len:
                buf.extend(b"\x00" * (self._disk_payload_len - len(buf)))
            if self._append_buf:
                buf.extend(self._append_buf)
            if self._patch_map:
                for p_off, p_bytes in self._patch_map.items():
                    rel = p_off - 4
                    end_rel = rel + len(p_bytes)
                    if end_rel > len(buf):
                        buf.extend(b"\x00" * (end_rel - len(buf)))
                    buf[rel:end_rel] = p_bytes
            self._payload = buf
            self._append_buf.clear()
            self._patch_map.clear()
        return self._payload

    @payload.setter
    def payload(self, value: bytearray | bytes) -> None:
        self._payload = value if isinstance(value, bytearray) else bytearray(value)
        self._append_buf = bytearray()
        self._patch_map = {}

    def byte_size(self) -> int:
        """
        FR: Retourne la taille totale en octets du conteneur (en-tête 4 octets inclus)
        sans allouer ni matérialiser le fichier complet en mémoire.
        EN: Returns the total byte size of the container (including the 4-byte header)
        without allocating or materializing the full file in memory.
        Ref: picasa3.exe @ 0x006B6AF0, 0x006B7390
        """
        return 4 + (
            len(self._payload)
            if self._payload is not None
            else self._disk_payload_len + len(self._append_buf)
        )

    @classmethod
    # Ref: picasa3.exe @ 0x006B6AF0, 0x006B7390 (CBlockFile::OpenBlock)
    def from_file(cls, path: Union[str, Path]) -> BlockContainerFile:
        """
        FR: Ouvre un fichier conteneur *_0.db en mode paresseux adossé au disque :
        lit uniquement les 4 premiers octets (`magic`), vérifie `magic == BLOCK_CONTAINER_MAGIC`,
        et conserve la référence `_backing_path` sans charger le reste du fichier en RAM.
        EN: Opens a *_0.db container file in lazy disk-backed mode:
        reads only the first 4 bytes (`magic`), verifies `magic == BLOCK_CONTAINER_MAGIC`,
        and stores `_backing_path` without reading the rest of the file into RAM.
        """
        p = Path(path)
        with open(p, "rb") as f:
            hdr = f.read(4)
            if len(hdr) < 4:
                raise ValueError(f"Conteneur blockfile trop court : {len(hdr)} octets (min 4)")
            magic = struct.unpack_from("<I", hdr, 0)[0]
            if magic != BLOCK_CONTAINER_MAGIC:
                raise ValueError(
                    f"Magic container blockfile invalide : 0x{magic:08X} (attendu 0x{BLOCK_CONTAINER_MAGIC:08X})"
                )
            f.seek(0, os.SEEK_END)
            st_size = f.tell()

        inst = cls.__new__(cls)
        inst.magic = magic
        inst._backing_path = p
        inst._disk_payload_len = max(0, st_size - 4)
        inst._payload = None
        inst._append_buf = bytearray()
        inst._patch_map = {}
        inst._dirty_ranges = []
        inst._fully_dirty = False
        return inst

    @classmethod
    # Ref: picasa3.exe @ 0x006B61E0 (OpenBlock)
    def from_bytes(cls, data: bytes) -> BlockContainerFile:
        """
        FR: Désérialise un fichier conteneur *_0.db depuis un buffer binaire.
        EN: Deserializes a *_0.db container file from a binary byte buffer.
        """
        if len(data) < 4:
            raise ValueError(f"Conteneur blockfile trop court : {len(data)} octets (min 4)")
        magic = struct.unpack_from("<I", data, 0)[0]
        if magic != BLOCKFILE_MAGIC:
            raise ValueError(f"Magic container blockfile invalide : 0x{magic:08X} (attendu 0x{BLOCKFILE_MAGIC:08X})")
        return cls(magic=magic, data=data[4:])

    # Ref: picasa3.exe @ 0x006B7FC0
    def to_bytes(self) -> bytes:
        """
        FR: Sérialise le conteneur CBlockFile en octets.
        EN: Serializes the CBlockFile container into bytes.
        """
        return CONTAINER_HEADER_STRUCT.pack(self.magic) + bytes(self.payload)

    # Ref: picasa3.exe @ 0x006B7390 (CBlockFile::ReadEntry)
    def get_blob(self, entry_or_offset: BlockEntry | int, size: Optional[int] = None) -> bytes:
        """
        FR: Extrait le blob correspondant à l'entrée (`BlockEntry`) ou au couple `(file_offset, size)`.
        L'offset est relatif au fichier complet (`file_offset >= 4`).
        En mode paresseux (`_payload is None`), lit depuis `_append_buf`, `_patch_map` ou directement
        via `seek(file_offset)` + `read(size)` sur `_backing_path` sans charger tout le fichier.
        EN: Extracts the blob corresponding to the requested `BlockEntry` or `(file_offset, size)` pair.
        The offset is relative to the complete file (`file_offset >= 4`).
        In lazy mode (`_payload is None`), reads from `_append_buf`, `_patch_map`, or directly
        via `seek(file_offset)` + `read(size)` on `_backing_path` without loading the entire file.
        """
        if isinstance(entry_or_offset, BlockEntry) and size is None:
            if entry_or_offset.is_empty:
                return b""
            file_offset = entry_or_offset.offset
            blob_size = entry_or_offset.size
        else:
            file_offset = int(entry_or_offset)
            blob_size = int(size or 0)
            if blob_size == 0 and file_offset == 0:
                return b""

        if blob_size == 0:
            if file_offset < 4:
                raise ValueError(f"Offset d'entrée invalide : {file_offset} (doit être >= 4)")
            return b""
        if file_offset < 4:
            raise ValueError(f"Offset d'entrée invalide : {file_offset} (doit être >= 4)")

        rel_offset = file_offset - 4
        end_offset = rel_offset + blob_size
        total_payload_len = (
            len(self._payload)
            if self._payload is not None
            else self._disk_payload_len + len(self._append_buf)
        )
        if end_offset > total_payload_len:
            raise ValueError(
                f"Entrée hors limites du container : offset={file_offset}, taille={blob_size}, "
                f"fin={end_offset} > taille utile={total_payload_len}"
            )

        if self._payload is not None:
            return bytes(self._payload[rel_offset:end_offset])

        if file_offset in self._patch_map and len(self._patch_map[file_offset]) == blob_size:
            return self._patch_map[file_offset]

        if rel_offset >= self._disk_payload_len:
            app_start = rel_offset - self._disk_payload_len
            data = bytearray(self._append_buf[app_start : app_start + blob_size])
        elif end_offset <= self._disk_payload_len:
            assert self._backing_path is not None
            with open(self._backing_path, "rb") as f:
                f.seek(file_offset)
                data = bytearray(f.read(blob_size))
        else:
            assert self._backing_path is not None
            disk_part_len = self._disk_payload_len - rel_offset
            with open(self._backing_path, "rb") as f:
                f.seek(file_offset)
                data = bytearray(f.read(disk_part_len))
            data.extend(self._append_buf[: blob_size - disk_part_len])

        if self._patch_map:
            req_start = file_offset
            req_end = file_offset + blob_size
            for p_off, p_bytes in self._patch_map.items():
                p_end = p_off + len(p_bytes)
                ov_start = max(req_start, p_off)
                ov_end = min(req_end, p_end)
                if ov_end > ov_start:
                    data[ov_start - req_start : ov_end - req_start] = p_bytes[ov_start - p_off : ov_end - p_off]

        return bytes(data)

    # Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry)
    def write_blob_at(self, file_offset: int, blob: bytes) -> None:
        """
        FR: Écrit un blob à l'offset fichier spécifié (`file_offset >= 4`) sans matérialiser
        le fichier disque lorsque l'instance est en mode paresseux (`_payload is None`).
        EN: Writes a blob at the specified file offset (`file_offset >= 4`) without materializing
        the on-disk file when the instance is in lazy mode (`_payload is None`).
        Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry)
        """
        if file_offset < 4:
            raise ValueError(f"Offset d'entrée invalide : {file_offset} (doit être >= 4)")
        size = len(blob)
        if self._payload is None:
            curr_end = 4 + self._disk_payload_len + len(self._append_buf)
            if file_offset == curr_end:
                self._append_buf.extend(blob)
                if size > 0:
                    self._dirty_ranges.append((file_offset, file_offset + size))
                return
            if file_offset >= 4 + self._disk_payload_len and file_offset + size <= curr_end:
                app_off = file_offset - (4 + self._disk_payload_len)
                self._append_buf[app_off : app_off + size] = blob
                if size > 0:
                    self._dirty_ranges.append((file_offset, file_offset + size))
                return
            if file_offset + size <= 4 + self._disk_payload_len:
                self._patch_map[file_offset] = bytes(blob)
                if size > 0:
                    self._dirty_ranges.append((file_offset, file_offset + size))
                return

        rel_offset = file_offset - 4
        payload_buf = self.payload
        if rel_offset + size > len(payload_buf):
            payload_buf.extend(b"\x00" * (rel_offset + size - len(payload_buf)))
        payload_buf[rel_offset : rel_offset + size] = blob
        if size > 0:
            self._dirty_ranges.append((file_offset, file_offset + size))

    # Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry)
    def write_entry(self, offset: int, payload: bytes) -> None:
        """
        FR: Écrit directement une charge utile à l'offset fichier spécifié (>= 4) et enregistre la plage modifiée.
        EN: Directly writes a payload at the specified file offset (>= 4) and records the dirty range.
        Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry)
        """
        self.write_blob_at(offset, payload)

    def append_blob(self, blob: bytes, checksum: int = 0, block_idx: int = 0) -> BlockEntry:
        """
        FR: Ajoute un nouveau blob à la fin du conteneur et renvoie la BlockEntry correspondante
        (compatible avec un entier via `__int__` / `__eq__`).
        En mode paresseux (`_payload is None`), ajoute à `_append_buf` sans matérialiser le fichier disque.
        EN: Appends a new blob to the end of the container and returns the corresponding BlockEntry
        (also int-compatible via `__int__` / `__eq__`).
        In lazy mode (`_payload is None`), appends to `_append_buf` without materializing the on-disk file.
        Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry)
        """
        size = len(blob)
        if size == 0:
            return BlockEntry(checksum=0, offset=0, size=0, block=0)
        if size > 0x00FFFFFF:
            raise ValueError(f"Taille de blob supérieure à 24 bits (max 16 Mo) : {size}")
        if self._payload is None:
            abs_offset = 4 + self._disk_payload_len + len(self._append_buf)
            self._append_buf.extend(blob)
        else:
            abs_offset = 4 + len(self._payload)
            self._payload.extend(blob)
        if size > 0:
            self._dirty_ranges.append((abs_offset, abs_offset + size))
        return BlockEntry(checksum=checksum, offset=abs_offset, size=size, block=block_idx)

    def write_blob(
        self,
        blob: bytes,
        existing_entry: Optional[BlockEntry] = None,
        checksum: int = 0,
        block_idx: int = 0,
    ) -> BlockEntry:
        """
        FR: Écrit un blob dans le conteneur conformément à CBlockFile::WriteEntry (FUN_006b75f0 @ 0x006B75F0) :
        - Si len(blob) == 0, retourne une entrée vide BlockEntry(0, 0, 0, 0) (Ref: 0x006B7732).
        - Si existing_entry est dans le même bloc et a une taille >= len(blob), réécrit sur place.
        - Sinon, ajoute en fin de conteneur.
        EN: Writes a blob into the container in accordance with CBlockFile::WriteEntry (FUN_006b75f0 @ 0x006B75F0):
        - If len(blob) == 0, returns an empty BlockEntry(0, 0, 0, 0) (Ref: 0x006B7732).
        - If existing_entry is in the same block and has size >= len(blob), overwrites in place.
        - Otherwise, appends at the end of the container.
        """
        size = len(blob)
        if size == 0:
            return BlockEntry(checksum=0, offset=0, size=0, block=0)
        if size > 0x00FFFFFF:
            raise ValueError(f"Taille de blob supérieure à 24 bits (max 16 Mo) : {size}")
        if (
            existing_entry is not None
            and not existing_entry.is_empty
            and existing_entry.block == block_idx
            and existing_entry.size >= size
            and existing_entry.offset >= 4
            and existing_entry.offset + size <= self.byte_size()
        ):
            self.write_blob_at(existing_entry.offset, blob)
            return BlockEntry(
                checksum=checksum,
                offset=existing_entry.offset,
                size=size,
                block=block_idx,
            )
        return self.append_blob(blob, checksum=checksum, block_idx=block_idx)

    # Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry), 0x006B7FC0 (CBlockFile::SaveIndex)
    def flush_to_file(self, path: Path | str) -> None:
        """
        FR: Synchronise le conteneur CBlockFile sur disque :
        - En mode paresseux (`_payload is None`) vers `_backing_path`, ouvre le fichier en `r+b`,
          applique les patches `_patch_map` et ajoute `_append_buf` à la fin sans jamais charger le fichier.
        - Si le fichier n'existe pas, est marqué entièrement modifié (`_fully_dirty`) ou a rétréci,
          écrit le fichier complet de manière atomique (.tmp + os.replace).
        - Si aucune plage n'a été modifiée (`_dirty_ranges` vide) et que la taille sur disque correspond,
          ne fait aucune écriture disque.
        - Sinon, écrit uniquement sur place (`r+b`, `seek` + `write`) les plages d'octets modifiées ou ajoutées.
        EN: Flushes the CBlockFile container to disk:
        - In lazy mode (`_payload is None`) targeting `_backing_path`, opens the file in `r+b`,
          writes `_patch_map` patches and appends `_append_buf` at the end without loading the file.
        - If the file does not exist, is marked `_fully_dirty`, or shrank, writes the full file atomically.
        - If no range was modified (`_dirty_ranges` empty) and the on-disk size matches, performs no disk I/O.
        - Otherwise, writes only the modified or appended byte ranges in-place (`r+b`, `seek` + `write`).
        Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry)
        """
        target = Path(path)

        if (
            self._payload is None
            and self._backing_path is not None
            and not self._fully_dirty
            and target.exists()
            and os.path.normcase(os.path.abspath(str(target)))
            == os.path.normcase(os.path.abspath(str(self._backing_path)))
        ):
            if not self._patch_map and not self._append_buf and not self._dirty_ranges:
                return
            try:
                with open(target, "r+b") as f:
                    for p_off, p_bytes in self._patch_map.items():
                        if p_bytes:
                            f.seek(p_off)
                            f.write(p_bytes)
                    if self._append_buf:
                        f.seek(4 + self._disk_payload_len)
                        f.write(self._append_buf)
                        self._disk_payload_len += len(self._append_buf)
                self._append_buf.clear()
                self._patch_map.clear()
                self._dirty_ranges.clear()
                self._fully_dirty = False
                return
            except OSError:
                pass

        total_size = self.byte_size()

        def _full_atomic_write() -> None:
            raw = self.to_bytes()
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(raw)
            try:
                os.replace(str(tmp), str(target))
            except PermissionError:
                try:
                    target.write_bytes(raw)
                finally:
                    tmp.unlink(missing_ok=True)
            self._backing_path = target
            self._disk_payload_len = len(raw) - 4
            self._dirty_ranges.clear()
            self._fully_dirty = False

        if not target.exists() or self._fully_dirty:
            _full_atomic_write()
            return

        try:
            disk_size = target.stat().st_size
        except OSError:
            _full_atomic_write()
            return

        if disk_size > total_size or disk_size < 4:
            _full_atomic_write()
            return

        if not self._dirty_ranges:
            if disk_size == total_size:
                return
            _full_atomic_write()
            return

        payload_buf = self.payload
        try:
            with open(target, "r+b") as f:
                for start, end in self._dirty_ranges:
                    s = max(4, int(start))
                    e = min(total_size, int(end))
                    if e > s:
                        f.seek(s)
                        f.write(payload_buf[s - 4 : e - 4])
            self._dirty_ranges.clear()
            self._fully_dirty = False
        except OSError:
            _full_atomic_write()

