"""
Modèle de données pour les fichiers INI Picasa (.picasa.ini et Picasa.ini).

Traçabilité Ghidra :
- FUN_0068ac80 @ 0x0068AC80 - 0x0068C412 (Écriture sérialisée .picasa.ini)
- FUN_009be730 @ 0x009BE730 - 0x009BE9AE (Moteur de recherche et découpage section/clé)
- FUN_0045c0a0 @ 0x0045C0A0 (Résolution chemin .picasa.ini / Picasa.ini)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterator
import re

# Ref: picasa3.exe @ 0x0068BABA ("faces=%s\r\n")
# Format: rect64(<hex16>),<contact_id_hex>
@dataclass
class FaceItem:
    rect64: str
    contact_id: str

    def to_ini_str(self) -> str:
        # Ref: picasa3.exe @ 0x0068BABA
        return f"rect64({self.rect64}),{self.contact_id}"

    @classmethod
    def from_ini_str(cls, s: str) -> Optional[FaceItem]:
        # Ref: picasa3.exe @ 0x0068BABA, 0x006ADB2E
        m = re.match(r"rect64\(([0-9a-fA-F]+)\),([0-9a-fA-F]+)", s.strip())
        if m:
            return cls(rect64=m.group(1), contact_id=m.group(2))
        return None


# Ref: picasa3.exe @ 0x0068B63D ("crop=rect64(%s)\r\n")
@dataclass
class CropRect:
    rect64: str

    def to_ini_str(self) -> str:
        return f"rect64({self.rect64})"

    @classmethod
    def from_ini_str(cls, s: str) -> Optional[CropRect]:
        m = re.match(r"rect64\(([0-9a-fA-F]+)\)", s.strip())
        if m:
            return cls(rect64=m.group(1))
        return None


# Ref: picasa3.exe @ 0x00CA7810 - 0x00CA78BC (Section Contacts2)
@dataclass
class ContactInfo:
    contact_id: str
    name: str
    email: str = ""
    extra: str = ""

    def to_ini_str(self) -> str:
        # Format Picasa: Nom;email;extra (se termine souvent par ;;)
        return f"{self.name};{self.email};{self.extra}"

    @classmethod
    def from_ini_str(cls, contact_id: str, s: str) -> ContactInfo:
        parts = s.split(";")
        name = parts[0] if len(parts) > 0 else ""
        email = parts[1] if len(parts) > 1 else ""
        extra = ";".join(parts[2:]) if len(parts) > 2 else ""
        return cls(contact_id=contact_id, name=name, email=email, extra=extra)


# Ref: picasa3.exe @ 0x0068AC80 (Élément de section générique)
@dataclass
class IniEntry:
    key: Optional[str] = None
    value: Optional[str] = None
    raw_line: str = ""  # Ligne brute originale (incluant \r\n) pour le round-trip exact

    @property
    def is_key_value(self) -> bool:
        return self.key is not None


@dataclass
class IniSection:
    name: str
    raw_header: str = ""  # Ex: "[Contacts2]\r\n" ou avec espaces/lignes précédentes
    entries: List[IniEntry] = field(default_factory=list)

    def _ci_key(self, k: str) -> str:
        # Ref: picasa3.exe @ 0x009BE7E0 - Insensibilité à la casse ASCII (A-Z -> a-z)
        return k.lower()

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        target = self._ci_key(key)
        for entry in self.entries:
            if entry.key is not None and self._ci_key(entry.key) == target:
                return entry.value
        return default

    def set(self, key: str, value: str) -> None:
        target = self._ci_key(key)
        for entry in self.entries:
            if entry.key is not None and self._ci_key(entry.key) == target:
                entry.value = value
                entry.raw_line = f"{entry.key}={value}\r\n"
                return
        # Nouvelle entrée
        new_entry = IniEntry(key=key, value=value, raw_line=f"{key}={value}\r\n")
        self.entries.append(new_entry)

    def remove(self, key: str) -> bool:
        target = self._ci_key(key)
        for i, entry in enumerate(self.entries):
            if entry.key is not None and self._ci_key(entry.key) == target:
                self.entries.pop(i)
                return True
        return False

    def keys(self) -> Iterator[str]:
        for entry in self.entries:
            if entry.key is not None:
                yield entry.key

    def items(self) -> Iterator[Tuple[str, str]]:
        for entry in self.entries:
            if entry.key is not None and entry.value is not None:
                yield (entry.key, entry.value)
