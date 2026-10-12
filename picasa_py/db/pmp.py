"""
Module de lecture et écriture des fichiers .pmp (Picasa Property Map).

Traçabilité Ghidra :
- Classe : CPropertyMap (.\\thumblab\\CPropertyMap.cpp @ 0x00CA8104)
- Magic number : 0x3FCCCCCD (1.6f)
- Signature type : 0x13320000 | type_enum
- FUN_006a2b60 @ 0x006A2B60 (Ouverture / lecture du fichier .pmp)
- FUN_006d17f0 @ 0x006D17F0 (Dispatch par type)
- FUN_009977a0 @ 0x009977A0 (Sérialisation chaîne type 0x0000)
- FUN_00997f40 @ 0x00997F40 (Sérialisation uint32 type 0x0001 / 0x0007)
- FUN_009981e0 @ 0x009981E0 (Sérialisation double/uint64 type 0x0002 / 0x0004)
- FUN_00998090 @ 0x00998090 (Sérialisation uint8/uint16 type 0x0003 / 0x0005)
"""

from __future__ import annotations
import enum
import struct
from dataclasses import dataclass
from typing import Any, List, Union


# Ref: picasa3.exe @ 0x006D17F0 (Switch type_id)
class PmpType(enum.IntEnum):
    STRING = 0x0000      # Chaînes UTF-8 null-terminated (handle)
    UINT32 = 0x0001      # Entier non signé 32-bit (4 octets)
    DOUBLE = 0x0002      # Flottant double précision IEEE 754 (8 octets)
    UINT8 = 0x0003       # Entier non signé 8-bit (1 octet)
    UINT64 = 0x0004      # Entier non signé 64-bit (8 octets)
    UINT16 = 0x0005      # Entier non signé 16-bit (2 octets)
    STRING_PTR = 0x0006  # Chaînes UTF-8 null-terminated (pointeur direct)
    UINT32_ALT = 0x0007  # Entier non signé 32-bit (4 octets)

    @classmethod
    def from_type_id(cls, type_id: int) -> PmpType:
        # Ref: picasa3.exe @ 0x006D17F0 (param_1[0xc5] == 0x13320000 | type)
        return cls(type_id & 0x0000FFFF)

    def to_type_id(self) -> int:
        return 0x13320000 | int(self.value)


# Ref: picasa3.exe @ 0x006A2B60 (En-tête de 20 octets)
PMP_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32
PMP_SUBVERSION = 0x00000002
HEADER_STRUCT = struct.Struct("<IIIII")


@dataclass
class PmpHeader:
    magic: int = PMP_MAGIC
    type_id: int = 0x13320000
    subversion: int = PMP_SUBVERSION
    type_id_repeat: int = 0x13320000
    record_count: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> PmpHeader:
        if len(data) < 20:
            raise ValueError(f"En-tête PMP trop court : {len(data)} octets (attendu 20)")
        magic, type_id, subversion, type_id_repeat, record_count = HEADER_STRUCT.unpack(data[:20])
        if magic != PMP_MAGIC:
            raise ValueError(f"Magic PMP invalide : 0x{magic:08X} (attendu 0x{PMP_MAGIC:08X})")
        if subversion != PMP_SUBVERSION:
            raise ValueError(f"Version de schéma PMP non supportée : {subversion} (attendu {PMP_SUBVERSION})")
        if type_id != type_id_repeat:
            raise ValueError(f"Incohérence des identifiants de type dans l'en-tête PMP : 0x{type_id:08X} != 0x{type_id_repeat:08X}")
        return cls(
            magic=magic,
            type_id=type_id,
            subversion=subversion,
            type_id_repeat=type_id_repeat,
            record_count=record_count,
        )

    def to_bytes(self) -> bytes:
        return HEADER_STRUCT.pack(
            self.magic,
            self.type_id,
            self.subversion,
            self.type_id_repeat,
            self.record_count,
        )


class PmpFile:
    """
    Représentation d'une colonne PMP de Picasa.
    Permet la lecture, la manipulation et la sérialisation à l'octet près.
    """

    def __init__(self, pmp_type: PmpType, records: List[Any] | None = None):
        self.pmp_type = pmp_type
        self.records: List[Any] = records if records is not None else []

    @classmethod
    def from_bytes(cls, data: bytes) -> PmpFile:
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
                    records.append(payload[idx:].decode("utf-8", errors="replace"))
                    break
                s = payload[idx:end].decode("utf-8", errors="replace")
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
        # Ref: FUN_006a2b60
        with open(path, "rb") as f:
            data = f.read()
        return cls.from_bytes(data)

    def to_bytes(self) -> bytes:
        """
        Sérialise l'objet PMP au format binaire identique à l'original.
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
            body_parts = []
            for s in self.records:
                if s is None:
                    body_parts.append(b"\x00")
                else:
                    body_parts.append(str(s).encode("utf-8") + b"\x00")
            body_bytes = b"".join(body_parts)

        elif self.pmp_type in (PmpType.UINT32, PmpType.UINT32_ALT):
            body_bytes = struct.pack(f"<{count}I", *self.records)

        elif self.pmp_type == PmpType.DOUBLE:
            body_bytes = struct.pack(f"<{count}d", *self.records)

        elif self.pmp_type == PmpType.UINT8:
            body_bytes = bytes(self.records)

        elif self.pmp_type == PmpType.UINT64:
            body_bytes = struct.pack(f"<{count}Q", *self.records)

        elif self.pmp_type == PmpType.UINT16:
            body_bytes = struct.pack(f"<{count}H", *self.records)

        else:
            raise NotImplementedError(f"Type PMP non supporté : {self.pmp_type}")

        return head_bytes + body_bytes

    def write_file(self, path: str) -> None:
        data = self.to_bytes()
        with open(path, "wb") as f:
            f.write(data)
