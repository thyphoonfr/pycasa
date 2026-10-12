"""
Parseur dédié pour les fichiers .picasa.ini et Picasa.ini.

Traçabilité Ghidra :
- FUN_009be730 @ 0x009BE730 - 0x009BE9AE (Moteur d'extraction clé/valeur en mémoire)
- FUN_009bd390 / FUN_009bd490 @ 0x009BD390 (Lecture brute et taille du fichier)
"""

from __future__ import annotations
import os
from typing import List, Optional, Tuple
from picasa_py.ini.model import IniEntry, IniSection, FaceItem, CropRect, ContactInfo

# Ref: picasa3.exe @ 0x009BE730
class PicasaIniParser:
    """
    Parseur fidèle du format INI de Picasa.
    Préserve l'ordre, les fins de ligne et les lignes non analysées pour un round-trip octet pour octet.
    """

    @staticmethod
    def parse_bytes(data: bytes) -> PicasaIniDocument:
        # Ref: picasa3.exe @ 0x00CA77F0 (Décodage UTF-8)
        # Note: Picasa écrit de l'UTF-8 sans BOM
        if data.startswith(b"\xef\xbb\xbf"):
            # Enlever le BOM si présent pour le texte, mais le document s'en souvient
            text = data[3:].decode("utf-8", errors="replace")
            has_bom = True
        else:
            text = data.decode("utf-8", errors="replace")
            has_bom = False

        doc = PicasaIniDocument(has_bom=has_bom)

        # Découpage préservant les délimiteurs originaux
        lines = text.splitlines(keepends=True)
        current_section: Optional[IniSection] = None
        pending_raw_prefix: List[str] = []

        for line in lines:
            stripped = line.strip()
            # Ref: picasa3.exe @ 0x009BE730 ligne 79 (Recherche du délimiteur section 0x5b '[')
            if stripped.startswith("[") and stripped.endswith("]"):
                sec_name = stripped[1:-1]
                header_raw = "".join(pending_raw_prefix) + line
                pending_raw_prefix = []
                current_section = IniSection(name=sec_name, raw_header=header_raw)
                doc.sections.append(current_section)
                continue

            # Si aucune section n'a encore été déclarée (préambule)
            if current_section is None:
                if stripped.startswith("[") and "]" in stripped:
                    # Cas où des caractères suivent le ']'
                    end_idx = stripped.find("]")
                    sec_name = stripped[1:end_idx]
                    header_raw = "".join(pending_raw_prefix) + line
                    pending_raw_prefix = []
                    current_section = IniSection(name=sec_name, raw_header=header_raw)
                    doc.sections.append(current_section)
                else:
                    pending_raw_prefix.append(line)
                continue

            # Ref: picasa3.exe @ 0x009BE730 ligne 126 (Séparation par 0x3d '=')
            eq_idx = line.find("=")
            if eq_idx != -1:
                key = line[:eq_idx].strip()
                val_raw = line[eq_idx + 1 :]
                # Découpage de la valeur sans \r\n (Ref: 0x009BE730 l. 127-133: arrêt à 0x0d ou 0x0a)
                val = val_raw.rstrip("\r\n")
                entry = IniEntry(key=key, value=val, raw_line=line)
                current_section.entries.append(entry)
            else:
                # Ligne vide, commentaire ou résidu préservé à l'identique
                entry = IniEntry(raw_line=line)
                current_section.entries.append(entry)

        # Si des lignes préambule n'ont pas été rattachées à une section
        if pending_raw_prefix:
            doc.preamble = "".join(pending_raw_prefix)

        return doc

    @classmethod
    def parse_file(cls, path: str) -> PicasaIniDocument:
        # Ref: picasa3.exe @ 0x009BD490
        with open(path, "rb") as f:
            data = f.read()
        return cls.parse_bytes(data)


class PicasaIniDocument:
    """
    Représente un fichier INI Picasa complet (.picasa.ini ou Picasa.ini).
    Fournit l'API haut niveau et la sérialisation fidèle.
    """

    def __init__(self, has_bom: bool = False, preamble: str = ""):
        self.sections: List[IniSection] = []
        self.has_bom: bool = has_bom
        self.preamble: str = preamble

    def _ci_sec(self, s: str) -> str:
        # Ref: picasa3.exe @ 0x009BE730 - Insensibilité à la casse
        return s.lower()

    def get_section(self, name: str) -> Optional[IniSection]:
        target = self._ci_sec(name)
        for sec in self.sections:
            if self._ci_sec(sec.name) == target:
                return sec
        return None

    def get_or_create_section(self, name: str) -> IniSection:
        sec = self.get_section(name)
        if sec is None:
            # En-tête standard CRLF Ref: picasa3.exe @ 0x0068B37F ("[%s]\r\n")
            sec = IniSection(name=name, raw_header=f"[{name}]\r\n")
            self.sections.append(sec)
        return sec

    def remove_section(self, name: str) -> bool:
        target = self._ci_sec(name)
        for i, sec in enumerate(self.sections):
            if self._ci_sec(sec.name) == target:
                self.sections.pop(i)
                return True
        return False

    # --- Accesseurs haut niveau calqués sur Picasa ---

    # Ref: picasa3.exe @ 0x0068BABA ("faces=%s\r\n")
    def get_faces(self, filename: str) -> List[FaceItem]:
        sec = self.get_section(filename)
        if not sec:
            return []
        val = sec.get("faces")
        if not val:
            return []
        res = []
        for part in val.split(";"):
            part = part.strip()
            if not part:
                continue
            item = FaceItem.from_ini_str(part)
            if item:
                res.append(item)
        return res

    def set_faces(self, filename: str, faces: List[FaceItem]) -> None:
        sec = self.get_or_create_section(filename)
        if not faces:
            sec.remove("faces")
        else:
            val = ";".join(f.to_ini_str() for f in faces)
            sec.set("faces", val)

    # Ref: picasa3.exe @ 0x0068B63D ("crop=rect64(%s)\r\n")
    def get_crop(self, filename: str) -> Optional[str]:
        sec = self.get_section(filename)
        if not sec:
            return None
        val = sec.get("crop")
        if not val:
            return None
        c = CropRect.from_ini_str(val)
        return c.rect64 if c else None

    def set_crop(self, filename: str, rect64: Optional[str]) -> None:
        sec = self.get_or_create_section(filename)
        if not rect64:
            sec.remove("crop")
        else:
            sec.set("crop", f"rect64({rect64})")

    # Ref: picasa3.exe @ 0x0068B800 ("star=yes\r\n")
    def is_starred(self, filename: str) -> bool:
        sec = self.get_section(filename)
        if not sec:
            return False
        return sec.get("star", "").lower() == "yes"

    def set_starred(self, filename: str, starred: bool) -> None:
        sec = self.get_or_create_section(filename)
        if starred:
            sec.set("star", "yes")
        else:
            sec.remove("star")

    # Ref: picasa3.exe @ 0x0068B8D0 ("keywords=%s\r\n")
    def get_keywords(self, filename: str) -> List[str]:
        sec = self.get_section(filename)
        if not sec:
            return []
        val = sec.get("keywords")
        if not val:
            return []
        return [k.strip() for k in val.split(",") if k.strip()]

    def set_keywords(self, filename: str, keywords: List[str]) -> None:
        sec = self.get_or_create_section(filename)
        clean = [k.strip() for k in keywords if k.strip()]
        if not clean:
            sec.remove("keywords")
        else:
            sec.set("keywords", ",".join(clean))

    # Ref: picasa3.exe @ 0x00CA7810 - Contacts2
    def get_contacts(self) -> Dict[str, ContactInfo]:
        sec = self.get_section("Contacts2")
        if not sec:
            return {}
        contacts = {}
        for entry in sec.entries:
            if entry.key and entry.value:
                contacts[entry.key] = ContactInfo.from_ini_str(entry.key, entry.value)
        return contacts

    def to_bytes(self) -> bytes:
        """
        Sérialise le document complet en respectant exactement l'encodage et les séparateurs.
        Ref: FUN_0068ac80
        """
        from picasa_py.ini.writer import PicasaIniWriter
        return PicasaIniWriter.to_bytes(self)

    def write_file(self, path: str) -> None:
        data = self.to_bytes()
        with open(path, "wb") as f:
            f.write(data)
