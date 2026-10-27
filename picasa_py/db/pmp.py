"""
FR: Module de lecture et écriture des fichiers .pmp (Picasa Property Map).
EN: Module for reading and writing .pmp files (Picasa Property Map).

Traçabilité Ghidra / Ghidra Traceability:
- Classe / Class: CPropertyMap (.\\thumblab\\CPropertyMap.cpp @ 0x00CA8104)
- Magic number : 0x3FCCCCCD (1.6f)
- Signature type : 0x13320000 | type_enum
- FUN_006a2b60 @ 0x006A2B60 (Ouverture / lecture du fichier .pmp / Open and read .pmp file)
- FUN_006d17f0 @ 0x006D17F0 (Dispatch par type / Dispatch by column type)
- FUN_009977a0 @ 0x009977A0 (Sérialisation chaîne type 0x0000 / String serialization type 0x0000)
- FUN_00997f40 @ 0x00997F40 (Sérialisation uint32 type 0x0001 / 0x0007 / uint32 serialization)
- FUN_009981e0 @ 0x009981E0 (Sérialisation double/uint64 type 0x0002 / 0x0004 / double & uint64 serialization)
- FUN_00998090 @ 0x00998090 (Sérialisation uint8/uint16 type 0x0003 / 0x0005 / uint8 & uint16 serialization)
"""

from __future__ import annotations
import enum
import os
import struct
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, List, Union


# Ref: picasa3.exe @ 0x006D17F0 (Switch type_id)
class PmpType(enum.IntEnum):
    """
    FR: Types de données des colonnes .pmp de Picasa 3.
    EN: Data types for Picasa 3 .pmp columns.
    """
    STRING = 0x0000      # FR: Chaînes UTF-8 null-terminated (handle) / EN: Null-terminated UTF-8 strings (handle)
    UINT32 = 0x0001      # FR: Entier non signé 32-bit (4 octets) / EN: 32-bit unsigned integer (4 bytes)
    DOUBLE = 0x0002      # FR: Flottant double précision IEEE 754 (8 octets) / EN: IEEE 754 double-precision float (8 bytes)
    UINT8 = 0x0003       # FR: Entier non signé 8-bit (1 octet) / EN: 8-bit unsigned integer (1 byte)
    UINT64 = 0x0004      # FR: Entier non signé 64-bit (8 octets) / EN: 64-bit unsigned integer (8 bytes)
    UINT16 = 0x0005      # FR: Entier non signé 16-bit (2 octets) / EN: 16-bit unsigned integer (2 bytes)
    STRING_PTR = 0x0006  # FR: Chaînes UTF-8 null-terminated (pointeur direct) / EN: Null-terminated UTF-8 strings (direct pointer)
    UINT32_ALT = 0x0007  # FR: Entier non signé 32-bit (4 octets) / EN: 32-bit unsigned integer (4 bytes)

    @classmethod
    def from_type_id(cls, type_id: int) -> PmpType:
        """
        FR: Extrait l'énumération PmpType depuis l'identifiant 32 bits (0x13320000 | type).
        EN: Extracts the PmpType enum from the 32-bit type identifier (0x13320000 | type).
        """
        # Ref: picasa3.exe @ 0x006D17F0 (param_1[0xc5] == 0x13320000 | type)
        return cls(type_id & 0x0000FFFF)

    def to_type_id(self) -> int:
        """
        FR: Convertit l'énumération PmpType en identifiant 32 bits avec préfixe 0x13320000.
        EN: Converts the PmpType enum to a 32-bit type identifier with 0x13320000 prefix.
        """
        return 0x13320000 | int(self.value)


# Ref: picasa3.exe @ 0x006A2B60 (En-tête de 20 octets / 20-byte header)
PMP_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32 / 1.6f in IEEE 754 float32
PMP_SUBVERSION = 0x00000002
HEADER_STRUCT = struct.Struct("<IIIII")


@dataclass
class PmpHeader:
    """
    FR: En-tête binaire de 20 octets d'un fichier .pmp.
    EN: 20-byte binary header of a .pmp file.
    """
    magic: int = PMP_MAGIC
    type_id: int = 0x13320000
    subversion: int = PMP_SUBVERSION
    type_id_repeat: int = 0x13320000
    record_count: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> PmpHeader:
        """
        FR: Désérialise et valide l'en-tête de 20 octets d'un fichier .pmp.
        EN: Deserializes and validates the 20-byte header of a .pmp file.
        """
        if len(data) < 20:
            raise ValueError(f"En-tête PMP trop court : {len(data)} octets (attendu 20)")
        magic, type_id, subversion, type_id_repeat, record_count = HEADER_STRUCT.unpack(data[:20])
        if magic != PMP_MAGIC:
            raise ValueError(f"Magic PMP invalide : 0x{magic:08X} (attendu 0x{PMP_MAGIC:08X})")
        if subversion != PMP_SUBVERSION:
            raise ValueError(f"Version de schéma PMP non supportée : {subversion} (attendu {PMP_SUBVERSION})")
        if type_id != type_id_repeat:
            raise ValueError(f"Incohérence des identifiants de type dans l'en-tête PMP : 0x{type_id:08X} != 0x{type_id_repeat:08X}")
        # Ref: picasa3.exe @ 0x0099C95A (cmp eax, 0x0FFFFFFF; jbe ...)
        if record_count > 0x0FFFFFFF:
            raise ValueError(f"Nombre d'enregistrements PMP invalide (> 0x0FFFFFFF) : 0x{record_count:08X}")
        return cls(
            magic=magic,
            type_id=type_id,
            subversion=subversion,
            type_id_repeat=type_id_repeat,
            record_count=record_count,
        )

    def to_bytes(self) -> bytes:
        """
        FR: Sérialise l'en-tête PMP en 20 octets little-endian.
        EN: Serializes the PMP header into 20 little-endian bytes.
        """
        return HEADER_STRUCT.pack(
            self.magic,
            self.type_id,
            self.subversion,
            self.type_id_repeat,
            self.record_count,
        )


class PmpFile:
    """
    FR: Représentation d'une colonne PMP de Picasa.
    Permet la lecture, la manipulation et la sérialisation à l'octet près.
    EN: Representation of a Picasa PMP column file.
    Supports bit-exact reading, manipulation, and serialization.
    """

    def __init__(self, pmp_type: PmpType, records: List[Any] | None = None, dirty: bool = False):
        """
        FR: Initialise une colonne PMP typée avec sa liste d'enregistrements et son flag d'état modifié (`dirty`).
        EN: Initializes a typed PMP column with its list of records and its modified state flag (`dirty`).
        Ref: picasa3.exe @ 0x006C1920 (CPMTable)
        """
        self.pmp_type = pmp_type
        self.records: List[Any] = records if records is not None else []
        self.dirty: bool = dirty

    @classmethod
    def from_bytes(cls, data: bytes) -> PmpFile:
        """
        FR: Désérialise un fichier .pmp complet depuis un buffer d'octets.
        EN: Deserializes a complete .pmp file from a byte buffer.
        """
        header = PmpHeader.from_bytes(data[:20])
        pmp_type = PmpType.from_type_id(header.type_id)
        payload = data[20:]
        count = header.record_count

        records: List[Any] = []

        # Ref: picasa3.exe @ 0x006D17F0
        if pmp_type in (PmpType.STRING, PmpType.STRING_PTR):
            # Ref: FUN_009977a0 @ 0x009977A0 & FUN_009975d0 @ 0x009975D0
            idx = 0
            for _ in range(count):
                end = payload.find(b"\x00", idx)
                if end == -1:
                    records.append(payload[idx:].decode("utf-8", errors="surrogateescape"))
                    break
                s = payload[idx:end].decode("utf-8", errors="surrogateescape")
                records.append(s)
                idx = end + 1

        elif pmp_type in (PmpType.UINT32, PmpType.UINT32_ALT):
            # Ref: FUN_00997f40 @ 0x00997F40
            expected = count * 4
            if len(payload) < expected:
                raise ValueError(f"Charge utile PMP tronquée : {len(payload)} < {expected}")
            records = list(struct.unpack(f"<{count}I", payload[:expected]))

        elif pmp_type == PmpType.DOUBLE:
            # Ref: FUN_009981e0 @ 0x009981E0
            expected = count * 8
            if len(payload) < expected:
                raise ValueError(f"Charge utile PMP tronquée : {len(payload)} < {expected}")
            records = list(struct.unpack(f"<{count}d", payload[:expected]))

        elif pmp_type == PmpType.UINT8:
            # Ref: FUN_00998090 @ 0x00998090
            expected = count
            if len(payload) < expected:
                raise ValueError(f"Charge utile PMP tronquée : {len(payload)} < {expected}")
            records = list(payload[:expected])

        elif pmp_type == PmpType.UINT64:
            # Ref: FUN_009981e0 @ 0x009981E0
            expected = count * 8
            if len(payload) < expected:
                raise ValueError(f"Charge utile PMP tronquée : {len(payload)} < {expected}")
            records = list(struct.unpack(f"<{count}Q", payload[:expected]))

        elif pmp_type == PmpType.UINT16:
            # Ref: FUN_00998330 @ 0x00998330
            expected = count * 2
            if len(payload) < expected:
                raise ValueError(f"Charge utile PMP tronquée : {len(payload)} < {expected}")
            records = list(struct.unpack(f"<{count}H", payload[:expected]))

        else:
            raise NotImplementedError(f"Type PMP non supporté : {pmp_type}")

        return cls(pmp_type=pmp_type, records=records)

    @classmethod
    def from_file(cls, path: str) -> PmpFile:
        """
        FR: Lit et désérialise un fichier .pmp depuis le disque.
        EN: Reads and deserializes a .pmp file from disk.
        """
        # Ref: FUN_006a2b60
        with open(path, "rb") as f:
            data = f.read()
        return cls.from_bytes(data)

    def default_value(self) -> Any:
        """
        FR: Renvoie la valeur par défaut Picasa pour une nouvelle ligne de ce type PMP.
        EN: Returns the Picasa default value for a new row of this PMP type.
        """
        if self.pmp_type in (PmpType.STRING, PmpType.STRING_PTR):
            return ""
        elif self.pmp_type == PmpType.DOUBLE:
            return 0.0
        return 0

    def to_bytes(self) -> bytes:
        """
        FR: Sérialise l'objet PMP au format binaire identique à l'original.
        EN: Serializes the PMP object into the exact original binary format.
        Ref: FUN_006a2cd0
        """
        type_id = self.pmp_type.to_type_id()
        count = len(self.records)
        header = PmpHeader(
            magic=PMP_MAGIC,
            type_id=type_id,
            subversion=PMP_SUBVERSION,
            type_id_repeat=type_id,
            record_count=count,
        )
        head_bytes = header.to_bytes()

        if self.pmp_type in (PmpType.STRING, PmpType.STRING_PTR):
            body_bytes = b"\x00".join(
                b"" if s is None else (s if isinstance(s, str) else str(s)).encode("utf-8", errors="surrogateescape")
                for s in self.records
            ) + (b"\x00" if count > 0 else b"")

        elif self.pmp_type in (PmpType.UINT32, PmpType.UINT32_ALT):
            try:
                body_bytes = struct.pack(f"<{count}I", *self.records)
            except (struct.error, TypeError):
                body_bytes = struct.pack(f"<{count}I", *(int(x) & 0xFFFFFFFF for x in self.records))

        elif self.pmp_type == PmpType.DOUBLE:
            try:
                body_bytes = struct.pack(f"<{count}d", *self.records)
            except (struct.error, TypeError):
                body_bytes = struct.pack(f"<{count}d", *(float(x) for x in self.records))

        elif self.pmp_type == PmpType.UINT8:
            try:
                body_bytes = bytes(self.records)
            except (ValueError, TypeError):
                body_bytes = bytes(int(x) & 0xFF for x in self.records)

        elif self.pmp_type == PmpType.UINT64:
            try:
                body_bytes = struct.pack(f"<{count}Q", *self.records)
            except (struct.error, TypeError):
                body_bytes = struct.pack(f"<{count}Q", *(int(x) & 0xFFFFFFFFFFFFFFFF for x in self.records))

        elif self.pmp_type == PmpType.UINT16:
            try:
                body_bytes = struct.pack(f"<{count}H", *self.records)
            except (struct.error, TypeError):
                body_bytes = struct.pack(f"<{count}H", *(int(x) & 0xFFFF for x in self.records))

        else:
            raise NotImplementedError(f"Type PMP non supporté : {self.pmp_type}")

        return head_bytes + body_bytes

    def write_file(self, path: str) -> None:
        """
        FR: Écrit directement le fichier .pmp sur disque (`CREATE_ALWAYS` / `"wb"`), conformément à `picasa3.exe`.
        Ref: picasa3.exe @ 0x006A2CD0, 0x00998620
        EN: Writes the .pmp file directly to disk (`CREATE_ALWAYS` / `"wb"`), matching `picasa3.exe`.
        """
        data = self.to_bytes()
        abs_path = os.path.abspath(path)
        dir_name = os.path.dirname(abs_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(data)
        self.dirty = False

