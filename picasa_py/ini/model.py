"""
FR: Modèle de données pour les fichiers INI Picasa (.picasa.ini et Picasa.ini).
EN: Data model for Picasa INI files (.picasa.ini and Picasa.ini).

Traçabilité Ghidra / Ghidra Traceability:
- FUN_0068ac80 @ 0x0068AC80 - 0x0068C412 (Écriture sérialisée .picasa.ini / Serialized .picasa.ini writer)
- FUN_009be730 @ 0x009BE730 - 0x009BE9AE (Moteur de recherche et découpage section/clé / Section and key lookup/splitting engine)
- FUN_0045c0a0 @ 0x0045C0A0 (Résolution chemin .picasa.ini / Picasa.ini / Path resolution for .picasa.ini and Picasa.ini)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterator
import re


# Ref: picasa3.exe @ 0x0068BABA ("faces=%s\r\n")
# Format: rect64(<hex16>),<contact_id_hex>
@dataclass
class FaceItem:
    """
    FR: Représente une annotation de visage (coordonnées rect64 et identifiant de contact) dans .picasa.ini.
    EN: Represents a face annotation (rect64 coordinates and contact ID) in .picasa.ini.
    """
    rect64: str
    contact_id: str

    def to_ini_str(self) -> str:
        """
        FR: Formate le visage sous la forme 'rect64(<hex>),<contact_id>'.
        EN: Formats the face item as 'rect64(<hex>),<contact_id>'.
        """
        # Ref: picasa3.exe @ 0x0068BABA
        return f"rect64({self.rect64}),{self.contact_id}"

    @classmethod
    def from_ini_str(cls, s: str) -> Optional[FaceItem]:
        """
        FR: Analyse une expression 'rect64(<hex>),<contact_id>' depuis .picasa.ini.
        EN: Parses a 'rect64(<hex>),<contact_id>' expression from .picasa.ini.
        """
        # Ref: picasa3.exe @ 0x0068BABA, 0x006ADB2E
        m = re.match(r"rect64\(([0-9a-fA-F]+)\),([^;,\s]+)", s.strip())
        if m:
            return cls(rect64=m.group(1), contact_id=m.group(2))
        return None


# Ref: picasa3.exe @ 0x0068B63D ("crop=rect64(%s)\r\n"), 0x009B91C0, 0x009B9290
@dataclass
class Rect64:
    """
    FR: Représente un rectangle 64 bits (`rect64`) en coordonnées entières 16 bits `[0, 65535]` avec bornage strict de `FUN_009b9290`.
    EN: Represents a 64-bit rectangle (`rect64`) in 16-bit integer coordinates `[0, 65535]` with strict `FUN_009b9290` clamping.
    Ref: picasa3.exe @ 0x009B9190, 0x009B91C0, 0x009B9247 ("rect64(%I64x)"), 0x009B9290
    """
    left: int
    top: int
    right: int
    bottom: int

    @classmethod
    def from_normalized(cls, left: float, top: float, right: float, bottom: float) -> Rect64:
        """
        FR: Construit un `Rect64` depuis des coordonnées normalisées `[0.0, 1.0]` avec le bornage exact de `FUN_009b9290`.
        EN: Builds a `Rect64` from normalized `[0.0, 1.0]` coordinates with the exact clamping of `FUN_009b9290`.
        Ref: picasa3.exe @ 0x009B9290 (FUN_009b9290)
        """
        l_int = max(0, min(0xFFFE, int(round(left * 65535.0))))
        t_int = max(0, min(0xFFFE, int(round(top * 65535.0))))
        r_int = max(1, min(0xFFFF, int(round(right * 65535.0))))
        b_int = max(1, min(0xFFFF, int(round(bottom * 65535.0))))
        if r_int <= l_int:
            l_int = r_int - 1
        if b_int <= t_int:
            t_int = b_int - 1
        return cls(
            left=l_int,
            top=t_int,
            right=r_int,
            bottom=b_int,
        )

    def to_normalized(self) -> Tuple[float, float, float, float]:
        """
        FR: Convertit les coordonnées 16 bits `[0, 65535]` en coordonnées flottantes normalisées `[0.0, 1.0]`.
        EN: Converts 16-bit `[0, 65535]` coordinates into normalized `[0.0, 1.0]` float coordinates.
        Ref: picasa3.exe @ 0x009B9190 (FUN_009b9190)
        """
        return (
            self.left / 65535.0,
            self.top / 65535.0,
            self.right / 65535.0,
            self.bottom / 65535.0,
        )

    def to_uint64(self) -> int:
        """
        FR: Encode le rectangle en entier non signé 64 bits (`uint64`).
        EN: Encodes the rectangle into a 64-bit unsigned integer (`uint64`).
        Ref: picasa3.exe @ 0x009B91C0, 0x009B9290
        """
        if any(isinstance(v, float) for v in (self.left, self.top, self.right, self.bottom)) and max(self.right, self.bottom) <= 1.0:
            l_int = max(0, min(0xFFFE, int(round(self.left * 65535.0))))
            t_int = max(0, min(0xFFFE, int(round(self.top * 65535.0))))
            r_int = max(1, min(0xFFFF, int(round(self.right * 65535.0))))
            b_int = max(1, min(0xFFFF, int(round(self.bottom * 65535.0))))
        else:
            l_int = max(0, min(0xFFFE, int(self.left)))
            t_int = max(0, min(0xFFFE, int(self.top)))
            r_int = max(1, min(0xFFFF, int(self.right)))
            b_int = max(1, min(0xFFFF, int(self.bottom)))
        if r_int <= l_int:
            l_int = r_int - 1
        if b_int <= t_int:
            t_int = b_int - 1
        return ((l_int & 0xFFFF) << 48) | ((t_int & 0xFFFF) << 32) | ((r_int & 0xFFFF) << 16) | (b_int & 0xFFFF)

    @classmethod
    def from_uint64(cls, val: int) -> Rect64:
        """
        FR: Décode un entier 64 bits `rect64` en `Rect64`.
        EN: Decodes a 64-bit `rect64` integer into `Rect64`.
        Ref: picasa3.exe @ 0x009B9190 (FUN_009b9190)
        """
        l_int = (val >> 48) & 0xFFFF
        t_int = (val >> 32) & 0xFFFF
        r_int = (val >> 16) & 0xFFFF
        b_int = val & 0xFFFF
        return cls(
            left=l_int,
            top=t_int,
            right=r_int,
            bottom=b_int,
        )

    def to_ini_string(self) -> str:
        """
        FR: Sérialise le rectangle sous la forme `rect64(%I64x)` (hexadécimal minuscule sans zéros superflus).
        EN: Serializes the rectangle as `rect64(%I64x)` (lowercase hex without leading zeros).
        Ref: picasa3.exe @ 0x009B91C0, 0x009B9247 ("rect64(%I64x)")
        """
        return f"rect64({self.to_uint64():x})"

    def to_ini_str(self) -> str:
        """
        FR: Alias de `to_ini_string()`.
        EN: Alias for `to_ini_string()`.
        """
        return self.to_ini_string()

    @classmethod
    def from_ini_string(cls, s: str) -> Optional[Rect64]:
        """
        FR: Analyse une chaîne `rect64(<hex>)`, `<hex>` ou `l,t,r,b` depuis `.picasa.ini`.
        EN: Parses a `rect64(<hex>)`, `<hex>`, or `l,t,r,b` string from `.picasa.ini`.
        Ref: picasa3.exe @ 0x009B91E0 (FUN_009b91e0), 0x006ADB2E
        """
        clean = s.strip()
        if not clean:
            return None
        m = re.match(r"^rect64\(([0-9a-fA-F]+)\)$", clean, re.IGNORECASE)
        if m:
            return cls.from_uint64(int(m.group(1), 16))
        if re.match(r"^[0-9a-fA-F]{1,16}$", clean):
            return cls.from_uint64(int(clean, 16))
        parts = [p.strip() for p in clean.split(",")]
        if len(parts) == 4:
            try:
                vals = [float(p) for p in parts]
                if any(v > 1.0 for v in vals):
                    return cls.from_normalized(
                        vals[0] / 65535.0,
                        vals[1] / 65535.0,
                        vals[2] / 65535.0,
                        vals[3] / 65535.0,
                    )
                return cls.from_normalized(vals[0], vals[1], vals[2], vals[3])
            except ValueError:
                return None
        return None

    @classmethod
    def from_ini_str(cls, s: str) -> Optional[Rect64]:
        """
        FR: Alias de `from_ini_string(s)`.
        EN: Alias for `from_ini_string(s)`.
        """
        return cls.from_ini_string(s)


# Ref: picasa3.exe @ 0x0068B63D ("crop=rect64(%s)\r\n")
@dataclass
class CropRect:
    """
    FR: Représente un rectangle de recadrage 64 bits (rect64) dans .picasa.ini.
    EN: Represents a 64-bit crop rectangle (rect64) in .picasa.ini.
    """
    rect64: str

    def to_ini_str(self) -> str:
        """
        FR: Formate le recadrage sous la forme 'rect64(<hex>)'.
        EN: Formats the crop rectangle as 'rect64(<hex>)'.
        """
        return f"rect64({self.rect64})"

    @classmethod
    def from_ini_str(cls, s: str) -> Optional[CropRect]:
        """
        FR: Analyse une expression 'rect64(<hex>)' depuis .picasa.ini.
        EN: Parses a 'rect64(<hex>)' expression from .picasa.ini.
        """
        m = re.match(r"rect64\(([0-9a-fA-F]+)\)", s.strip(), re.IGNORECASE)
        if m:
            return cls(rect64=m.group(1))
        return None


# Ref: picasa3.exe @ 0x00CA7810 - 0x00CA78BC (Section Contacts2)
@dataclass
class ContactInfo:
    """
    FR: Informations d'un contact stockées dans la section [Contacts2] d'un fichier .picasa.ini.
    EN: Contact information stored in the [Contacts2] section of a .picasa.ini file.
    """
    contact_id: str
    name: str
    email: str = ""
    extra: str = ""

    def to_ini_str(self) -> str:
        """
        FR: Sérialise le contact au format 'Nom;email;extra'.
        EN: Serializes the contact in 'Name;email;extra' format.
        """
        # Format Picasa: Nom;email;extra (se termine souvent par ;;)
        return f"{self.name};{self.email};{self.extra}"

    @classmethod
    def from_ini_str(cls, contact_id: str, s: str) -> ContactInfo:
        """
        FR: Construit un ContactInfo depuis une valeur de clé de la section [Contacts2].
        EN: Builds a ContactInfo from a key value in the [Contacts2] section.
        """
        parts = s.split(";")
        name = parts[0] if len(parts) > 0 else ""
        email = parts[1] if len(parts) > 1 else ""
        extra = ";".join(parts[2:]) if len(parts) > 2 else ""
        return cls(contact_id=contact_id, name=name, email=email, extra=extra)


# Ref: picasa3.exe @ 0x0068AC80 (Élément de section générique)
@dataclass
class IniEntry:
    """
    FR: Ligne individuelle dans une section INI (paire clé=valeur ou ligne brute/commentaire).
    EN: Individual line within an INI section (key=value pair or raw/comment line).
    """
    key: Optional[str] = None
    value: Optional[str] = None
    raw_line: str = ""  # FR: Ligne brute originale (incluant \r\n) pour le round-trip exact / EN: Original raw line (with \r\n) for exact round-trip

    @property
    def is_key_value(self) -> bool:
        """
        FR: Indique si l'entrée est une paire clé=valeur valide.
        EN: Indicates whether the entry is a valid key=value pair.
        """
        return self.key is not None


@dataclass
class IniSection:
    """
    FR: Section nommée d'un fichier .picasa.ini (ex: [Picasa], [Contacts2], [IMG_0001.JPG]).
    EN: Named section of a .picasa.ini file (e.g., [Picasa], [Contacts2], [IMG_0001.JPG]).
    """
    name: str
    raw_header: str = ""  # Ex: "[Contacts2]\r\n" ou avec espaces/lignes précédentes
    entries: List[IniEntry] = field(default_factory=list)
    _modified: bool = field(default=False, repr=False, compare=False)

    def _ci_key(self, k: str) -> str:
        """
        FR: Normalisation insensible à la casse ASCII stricte ('A'..'Z' -> +0x20).
        EN: Strict ASCII case-insensitive normalization ('A'..'Z' -> +0x20).
        """
        # Ref: picasa3.exe @ 0x009BE7E0 - Insensibilité à la casse ASCII stricte ('A'..'Z' -> +0x20)
        return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in k)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        FR: Récupère la valeur associée à une clé (insensible à la casse ASCII).
        EN: Retrieves the value associated with a key (ASCII case-insensitive).
        """
        target = self._ci_key(key)
        for entry in self.entries:
            if entry.key is not None and self._ci_key(entry.key) == target:
                return entry.value
        return default

    def set(self, key: str, value: str) -> None:
        """
        FR: Définit ou met à jour la valeur d'une clé en dédupliquant d'éventuels doublons.
        EN: Sets or updates a key's value while deduplicating any duplicate occurrences.
        """
        self._modified = True
        target = self._ci_key(key)
        found_idx: Optional[int] = None
        to_remove: List[int] = []
        for i, entry in enumerate(self.entries):
            if entry.key is not None and self._ci_key(entry.key) == target:
                if found_idx is None:
                    found_idx = i
                    entry.value = value
                    entry.raw_line = f"{entry.key}={value}\r\n"
                else:
                    to_remove.append(i)
        for idx in reversed(to_remove):
            self.entries.pop(idx)
        if found_idx is not None:
            return
        # FR: Nouvelle entrée / EN: New entry
        new_entry = IniEntry(key=key, value=value, raw_line=f"{key}={value}\r\n")
        self.entries.append(new_entry)

    def remove(self, key: str) -> bool:
        """
        FR: Supprime toutes les occurrences d'une clé dans la section.
        EN: Removes all occurrences of a key from the section.
        """
        self._modified = True
        target = self._ci_key(key)
        removed = False
        for i in range(len(self.entries) - 1, -1, -1):
            entry = self.entries[i]
            if entry.key is not None and self._ci_key(entry.key) == target:
                self.entries.pop(i)
                removed = True
        return removed

    def remove_key(self, key: str) -> bool:
        """
        FR: Alias de remove(key) pour supprimer une clé de la section INI.
        EN: Alias of remove(key) to remove a key from the INI section.
        Ref: picasa3.exe @ 0x0068AC80, 0x00C8D849
        """
        return self.remove(key)

    def keys(self) -> Iterator[str]:
        """
        FR: Itère sur les clés de la section.
        EN: Iterates over the keys in the section.
        """
        for entry in self.entries:
            if entry.key is not None:
                yield entry.key

    def items(self) -> Iterator[Tuple[str, str]]:
        """
        FR: Itère sur les couples (clé, valeur) de la section.
        EN: Iterates over the (key, value) pairs in the section.
        """
        for entry in self.entries:
            if entry.key is not None and entry.value is not None:
                yield (entry.key, entry.value)

