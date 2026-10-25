"""
FR: Parseur dédié pour les fichiers .picasa.ini et Picasa.ini.
EN: Dedicated parser for .picasa.ini and Picasa.ini files.

Traçabilité Ghidra / Ghidra Traceability:
- FUN_009be730 @ 0x009BE730 - 0x009BE9AE (Moteur d'extraction clé/valeur en mémoire / In-memory key/value extraction engine)
- FUN_009bd390 / FUN_009bd490 @ 0x009BD390 (Lecture brute et taille du fichier / Raw file reading and size check)
"""

from __future__ import annotations
import os
import re
from typing import List, Optional, Tuple, Dict, Union
from picasa_py.ini.model import (
    IniEntry,
    IniSection,
    FaceItem,
    CropRect,
    Rect64,
    ContactInfo,
    unescape_ini_value,
)


# Ref: picasa3.exe @ 0x009BE730
class PicasaIniParser:
    """
    FR: Parseur fidèle du format INI de Picasa 3.
    Préserve l'ordre, les fins de ligne et les lignes non analysées pour un round-trip octet pour octet.
    EN: Faithful parser for the Picasa 3 INI format.
    Preserves section/key order, line endings, and unparsed lines for byte-for-byte round-trip fidelity.
    """

    @staticmethod
    def parse_bytes(data: bytes) -> PicasaIniDocument:
        """
        FR: Analyse un buffer d'octets bruts (.picasa.ini) et construit un PicasaIniDocument.
        Détecte l'en-tête `[encoding]\\r\\nutf8=1` (ou BOM UTF-8) pour décoder en UTF-8,
        sinon replie sur ANSI/CP1252 conformement à `FUN_0068ac80` / `FUN_009be730`.
        EN: Parses a raw byte buffer (.picasa.ini) and builds a PicasaIniDocument.
        Detects the `[encoding]\\r\\nutf8=1` header (or UTF-8 BOM) to decode as UTF-8,
        otherwise falls back to ANSI/CP1252 in accordance with `FUN_0068ac80` / `FUN_009be730`.
        """
        # Ref: picasa3.exe @ 0x00CA77F0, 0x0068AD5A (Décodage UTF-8 si [encoding] utf8=1 / ANSI sinon)
        if data.startswith(b"\xef\xbb\xbf"):
            raw_payload = data[3:]
            has_bom = True
        else:
            raw_payload = data
            has_bom = False

        has_utf8_header = bool(
            re.search(
                rb"\[\s*encoding\s*\](?:(?!\r?\n\s*\[).)*?\butf8\s*=\s*1\b",
                raw_payload,
                re.IGNORECASE | re.DOTALL,
            )
        )

        untagged_utf8_preserved = False
        if has_bom or has_utf8_header:
            text = raw_payload.decode("utf-8", errors="replace")
            detected_encoding = "utf-8"
        elif any(b >= 0x80 for b in raw_payload):
            try:
                text = raw_payload.decode("utf-8")
                detected_encoding = "cp1252"
                untagged_utf8_preserved = True
            except UnicodeDecodeError:
                text = raw_payload.decode("cp1252", errors="replace")
                detected_encoding = "cp1252"
        else:
            text = raw_payload.decode("ascii")
            detected_encoding = "cp1252"

        doc = PicasaIniDocument(has_bom=has_bom, encoding=detected_encoding)
        doc._encoding_explicit = False
        doc._untagged_utf8_preserved = untagged_utf8_preserved

        # FR: Découpage uniquement sur \r\n, \r ou \n / EN: Split strictly on \r\n, \r, or \n
        # (Ref: picasa3.exe @ 0x009BE730 : 0x0d / 0x0a)
        lines = [m.group(0) for m in re.finditer(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+", text)]
        current_section: Optional[IniSection] = None
        pending_raw_prefix: List[str] = []

        for line in lines:
            stripped = line.strip("\r\n \t")
            # Ref: picasa3.exe @ 0x009BE730 ligne 79 (Recherche du délimiteur section 0x5b '[')
            if stripped.startswith("[") and stripped.endswith("]"):
                sec_name = stripped[1:-1]
                header_raw = "".join(pending_raw_prefix) + line
                pending_raw_prefix = []
                current_section = IniSection(name=sec_name, raw_header=header_raw)
                doc.sections.append(current_section)
                continue

            # FR: Si aucune section n'a encore été déclarée (préambule)
            # EN: If no section has been declared yet (preamble)
            if current_section is None:
                if stripped.startswith("[") and "]" in stripped:
                    # FR: Cas où des caractères suivent le ']' / EN: Case where characters follow ']'
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
                # FR: Découpage de la valeur sans \r\n et déséchappement &#010;/&#013;/&#091;/&#093; (0x0099ABC0)
                # EN: Strip trailing \r\n from value and unescape &#010;/&#013;/&#091;/&#093; (0x0099ABC0)
                val = unescape_ini_value(val_raw.rstrip("\r\n"))
                entry = IniEntry(key=key, value=val, raw_line=line)
                current_section.entries.append(entry)
            else:
                # FR: Ligne vide, commentaire ou résidu préservé à l'identique
                # EN: Blank line, comment, or unparsed line preserved verbatim
                entry = IniEntry(raw_line=line)
                current_section.entries.append(entry)

        # FR: Si des lignes préambule n'ont pas été rattachées à une section
        # EN: Attach any remaining preamble lines to the document
        if pending_raw_prefix:
            doc.preamble = "".join(pending_raw_prefix)

        for sec in doc.sections:
            sec._modified = False
        doc._modified = False

        return doc

    @classmethod
    def parse_file(cls, path: str) -> PicasaIniDocument:
        """
        FR: Lit et analyse un fichier .picasa.ini ou Picasa.ini depuis le disque.
        EN: Reads and parses a .picasa.ini or Picasa.ini file from disk.
        """
        # Ref: picasa3.exe @ 0x009BD490
        with open(path, "rb") as f:
            data = f.read()
        return cls.parse_bytes(data)


class PicasaIniDocument:
    """
    FR: Représente un fichier INI Picasa complet (.picasa.ini ou Picasa.ini).
    Fournit l'API haut niveau et la sérialisation fidèle.
    EN: Represents a complete Picasa INI file (.picasa.ini or Picasa.ini).
    Provides high-level accessors and byte-exact serialization.
    """

    def __init__(self, has_bom: bool = False, preamble: str = "", encoding: str = "utf-8"):
        """
        FR: Initialise un document INI Picasa vide ou avec préambule.
        EN: Initializes an empty or preamble-prefixed Picasa INI document.
        """
        self.sections: List[IniSection] = []
        self.has_bom: bool = has_bom
        self.preamble: str = preamble
        self._encoding: str = encoding
        self._encoding_explicit: bool = False
        self._modified: bool = False
        self._untagged_utf8_preserved: bool = False

    @property
    def encoding(self) -> str:
        """
        FR: Encodage détecté ou configuré du document INI (`"utf-8"` ou `"cp1252"`).
        EN: Detected or configured encoding of the INI document (`"utf-8"` or `"cp1252"`).
        """
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        """
        FR: Définit explicitement l'encodage cible du document INI.
        EN: Explicitly sets the target encoding of the INI document.
        """
        self._encoding = value
        self._encoding_explicit = True
        self._modified = True
        self._untagged_utf8_preserved = False

    def is_modified(self) -> bool:
        """
        FR: Indique si le document ou l'une de ses sections a été modifié depuis l'analyse.
        EN: Indicates whether the document or any of its sections has been modified since parsing.
        """
        return self._modified or any(sec._modified for sec in self.sections)

    def _ci_sec(self, s: str) -> str:
        """
        FR: Normalisation insensible à la casse ASCII stricte ('A'..'Z' -> +0x20).
        EN: Strict ASCII case-insensitive normalization ('A'..'Z' -> +0x20).
        """
        # Ref: picasa3.exe @ 0x009BE730 - Insensibilité à la casse ASCII stricte ('A'..'Z' -> +0x20)
        return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)

    def _sanitize_sec_name(self, name: str) -> str:
        """
        FR: Remplace '[' par '(' et ']' par ')' dans les noms de sections de fichiers conformément à `0x0068B359` et `0x0099AFC0`.
        EN: Replaces '[' with '(' and ']' with ')' in file section names matching `0x0068B359` and `0x0099AFC0`.
        """
        if "[" in name or "]" in name:
            return name.replace("[", "(").replace("]", ")")
        return name

    def get_section(self, name: str) -> Optional[IniSection]:
        """
        FR: Recherche une section par son nom (insensible à la casse ASCII, avec correspondance '['->'(' et ']'->')').
        EN: Finds a section by name (ASCII case-insensitive, matching '['->'(' and ']'->')').
        Ref: picasa3.exe @ 0x0099AFC0..0x0099AFD5
        """
        target = self._ci_sec(name)
        target_san = self._ci_sec(self._sanitize_sec_name(name))
        for sec in self.sections:
            sec_ci = self._ci_sec(sec.name)
            if sec_ci == target or sec_ci == target_san:
                return sec
        return None

    def get_or_create_section(self, name: str) -> IniSection:
        """
        FR: Récupère une section existante ou la crée à la position canonique de Picasa 3.
        EN: Retrieves an existing section or creates it at Picasa 3's canonical position.
        """
        sec = self.get_section(name)
        if sec is None:
            self._modified = True
            self._untagged_utf8_preserved = False
            clean_name = self._sanitize_sec_name(name)
            # En-tête standard CRLF Ref: picasa3.exe @ 0x0068B359..0x0068B37F ("[%s]\r\n" avec '['->'(' et ']'->')')
            sec = IniSection(name=clean_name, raw_header=f"[{clean_name}]\r\n")
            ci_name = self._ci_sec(clean_name)
            # Ref: FUN_0068ac80 : les sections globales ([encoding], [Picasa], [Contacts2], [.album:...])
            # précèdent les sections de fichiers médias.
            if ci_name == "encoding":
                self.sections.insert(0, sec)
            elif ci_name in ("picasa", "contacts2") or ci_name.startswith(".album:"):
                insert_idx = 0
                for i, existing in enumerate(self.sections):
                    ex_ci = self._ci_sec(existing.name)
                    if ex_ci in ("encoding", "picasa", "contacts2") or ex_ci.startswith(".album:"):
                        insert_idx = i + 1
                    else:
                        break
                self.sections.insert(insert_idx, sec)
            else:
                self.sections.append(sec)
        return sec

    def remove_section(self, name: str) -> bool:
        """
        FR: Supprime une section par son nom si elle existe.
        EN: Removes a section by name if it exists.
        """
        target = self._ci_sec(name)
        target_san = self._ci_sec(self._sanitize_sec_name(name))
        for i, sec in enumerate(self.sections):
            sec_ci = self._ci_sec(sec.name)
            if sec_ci == target or sec_ci == target_san:
                self.sections.pop(i)
                self._modified = True
                self._untagged_utf8_preserved = False
                return True
        return False

    # --- FR: Accesseurs haut niveau calqués sur Picasa / EN: High-level Picasa accessors ---

    # Ref: picasa3.exe @ 0x0068BABA ("faces=%s\r\n")
    def get_faces(self, filename: str) -> List[FaceItem]:
        """
        FR: Retourne la liste des visages (FaceItem) associés à un fichier image.
        EN: Returns the list of faces (FaceItem) associated with an image file.
        """
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
        """
        FR: Définit ou supprime l'entrée faces= pour un fichier image.
        EN: Sets or removes the faces= entry for an image file.
        """
        sec = self.get_or_create_section(filename)
        if not faces:
            sec.remove("faces")
        else:
            val = ";".join(f.to_ini_str() for f in faces)
            sec.set("faces", val)

    # Ref: picasa3.exe @ 0x0068B63D ("crop=rect64(%s)\r\n"), 0x006ADB2E ("crop64=1,%s")
    def get_crop_rect64(self, filename: str) -> Optional[Rect64]:
        """
        FR: Retourne l'objet `Rect64` de recadrage d'une image depuis `crop=` ou en repli depuis `filters=crop64=1,<hex>`.
        EN: Returns the `Rect64` crop object of an image from `crop=` or as fallback from `filters=crop64=1,<hex>`.
        Ref: picasa3.exe @ 0x0068B63D, 0x006ADB2E (FUN_006adb2e)
        """
        sec = self.get_section(filename)
        if not sec:
            return None
        val = sec.get("crop")
        if val:
            r = Rect64.from_ini_string(val)
            if r is not None:
                return r
        filters_val = sec.get("filters")
        if filters_val:
            m = re.search(r"crop64=1,([0-9a-fA-F]+)", filters_val, re.IGNORECASE)
            if m:
                return Rect64.from_uint64(int(m.group(1), 16))
            m2 = re.search(r"crop64=1,rect64\(([0-9a-fA-F]+)\)", filters_val, re.IGNORECASE)
            if m2:
                return Rect64.from_uint64(int(m2.group(1), 16))
        return None

    def set_crop_rect64(self, filename: str, rect: Optional[Union[Rect64, str]]) -> None:
        """
        FR: Définit ou supprime le rectangle de recadrage `crop=rect64(<hex>)` et synchronise `crop64=1,<hex>;` dans `filters=`.
        EN: Sets or removes the `crop=rect64(<hex>)` crop rectangle and synchronizes `crop64=1,<hex>;` in `filters=`.
        Ref: picasa3.exe @ 0x0068B63D, 0x00456A15 (FUN_00456a15)
        """
        sec = self.get_or_create_section(filename)
        if rect is None or (isinstance(rect, str) and not rect.strip()):
            sec.remove("crop")
            filters_val = sec.get("filters")
            if filters_val is not None:
                cleaned = re.sub(r"crop64=[^;]*;?", "", filters_val).strip(";")
                if cleaned:
                    sec.set("filters", cleaned + ";")
                else:
                    sec.remove("filters")
            return

        if isinstance(rect, Rect64):
            hex_str = f"{rect.to_uint64():x}"
        else:
            parsed = Rect64.from_ini_string(rect)
            if parsed is not None:
                hex_str = f"{parsed.to_uint64():x}"
            else:
                clean = rect.strip()
                if clean.lower().startswith("rect64(") and clean.endswith(")"):
                    clean = clean[7:-1]
                hex_str = clean

        sec.set("crop", f"rect64({hex_str})")
        filters_val = sec.get("filters")
        # Protection contre le bug de picasa3.exe @ 0x00459DE3 -> LAB_00459e21 :
        # si backuphash= est présent sans filters=, picasa3.exe écrase imagedata_crop64 = 0.
        if filters_val is not None or sec.get("backuphash") is not None:
            f_str = filters_val or ""
            if re.search(r"crop64=[^;]*", f_str, re.IGNORECASE):
                updated = re.sub(
                    r"crop64=[^;]*;?",
                    f"crop64=1,{hex_str};",
                    f_str,
                    flags=re.IGNORECASE,
                )
                sec.set("filters", updated.strip(";") + ";")
            else:
                base = f_str.strip(";")
                sec.set("filters", (f"{base};crop64=1,{hex_str};" if base else f"crop64=1,{hex_str};"))

    def get_crop(self, filename: str) -> Optional[str]:
        """
        FR: Retourne la chaîne hexadécimale rect64 de recadrage d'une image, ou None.
        EN: Returns the rect64 hexadecimal crop string for an image, or None.
        """
        sec = self.get_section(filename)
        if not sec:
            return None
        val = sec.get("crop")
        if val:
            c = CropRect.from_ini_str(val)
            if c:
                return c.rect64
            r = Rect64.from_ini_string(val)
            if r:
                return f"{r.to_uint64():x}"
        filters_val = sec.get("filters")
        if filters_val:
            m = re.search(r"crop64=1,([0-9a-fA-F]+)", filters_val, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def set_crop(self, filename: str, rect64: Optional[Union[str, Rect64]]) -> None:
        """
        FR: Définit ou supprime le rectangle de recadrage crop=rect64(...) d'une image.
        EN: Sets or removes the crop=rect64(...) rectangle for an image.
        """
        if isinstance(rect64, Rect64) or not rect64:
            self.set_crop_rect64(filename, rect64)
            return
        sec = self.get_or_create_section(filename)
        clean = rect64.strip()
        if clean.lower().startswith("rect64(") and clean.endswith(")"):
            clean = clean[7:-1]
        sec.set("crop", f"rect64({clean})")
        filters_val = sec.get("filters")
        if filters_val is not None or sec.get("backuphash") is not None:
            f_str = filters_val or ""
            if re.search(r"crop64=[^;]*", f_str, re.IGNORECASE):
                updated = re.sub(
                    r"crop64=[^;]*;?",
                    f"crop64=1,{clean};",
                    f_str,
                    flags=re.IGNORECASE,
                )
                sec.set("filters", updated.strip(";") + ";")
            else:
                base = f_str.strip(";")
                sec.set("filters", (f"{base};crop64=1,{clean};" if base else f"crop64=1,{clean};"))

    # Ref: picasa3.exe @ 0x008814AC ("tilt", "filters=%s")
    def get_tilt(self, filename: str) -> Optional[float]:
        """
        FR: Extrait l'angle de redressement (tilt) depuis la clé filters= d'une image.
        EN: Extracts the straightening angle (tilt) from an image's filters= key.
        """
        sec = self.get_section(filename)
        if not sec:
            return None
        val = sec.get("filters")
        if not val:
            return None
        m = re.search(r"tilt=([^;]+)", val)
        if m:
            raw_tilt = m.group(1).strip()
            parts = [p.strip() for p in raw_tilt.split(",") if p.strip()]
            try:
                if len(parts) >= 2 and parts[0] in ("0", "1"):
                    return float(parts[1])
                if parts:
                    return float(parts[0])
            except ValueError:
                return None
        return None

    def set_tilt(self, filename: str, angle_deg: Optional[float]) -> None:
        """
        FR: Définit ou supprime le filtre `tilt=1,<angle>,0.000000;` dans la clé `filters=` d'une image.
        EN: Sets or removes the `tilt=1,<angle>,0.000000;` filter in an image's `filters=` key.
        Ref: picasa3.exe @ 0x008814AC, 0x00456A15 (FUN_00456a15)
        """
        sec = self.get_or_create_section(filename)
        val = sec.get("filters", "")
        # FR: Supprimer tout tilt existant / EN: Remove any existing tilt entry
        val = re.sub(r"tilt=[^;]*;?", "", val).strip(";")
        if angle_deg is not None and abs(angle_deg) >= 0.01:
            tilt_part = f"tilt=1,{angle_deg:.6f},0.000000;"
            val = (val + ";" + tilt_part if val else tilt_part).strip(";") + ";"
        if val:
            sec.set("filters", val)
        else:
            sec.remove("filters")

    # Ref: picasa3.exe @ 0x0068B6B0 ("filters=%s\r\n")
    def get_filters(self, filename: str) -> List[str]:
        """
        FR: Renvoie la liste ordonnée des expressions de filtres non-destructifs (hors vide).
        EN: Returns the ordered list of non-destructive filter expressions (excluding empty items).
        """
        sec = self.get_section(filename)
        if not sec:
            return []
        val = sec.get("filters", "")
        if not val:
            return []
        return [part.strip() for part in val.split(";") if part.strip()]

    def set_filters(self, filename: str, filters: List[str]) -> None:
        """
        FR: Définit la chaîne filters= d'une photo.
        EN: Sets the filters= string of a photo.
        """
        sec = self.get_or_create_section(filename)
        clean = [f.strip().rstrip(";") for f in filters if f.strip().rstrip(";")]
        if not clean:
            sec.remove("filters")
        else:
            sec.set("filters", ";".join(clean) + ";")

    def append_filter(self, filename: str, filter_expr: str) -> None:
        """
        FR: Ajoute ou remplace un filtre dans la clé filters= d'une photo.
        EN: Appends or replaces a filter in a photo's filters= key.
        """
        clean_expr = filter_expr.strip().rstrip(";")
        if not clean_expr:
            return
        current = self.get_filters(filename)
        prefix = clean_expr.split("=")[0].split("(")[0].strip().lower()
        # FR: Remplacer les filtres uniques / EN: Replace singleton filters (finetune2, autolight, colorfix, tilt, crop64)
        singleton_prefixes = {"finetune2", "finetune", "autolight", "colorfix", "tilt", "crop64"}
        if prefix in singleton_prefixes:
            current = [
                f for f in current
                if f.split("=")[0].split("(")[0].strip().lower() != prefix
            ]
        current.append(clean_expr)
        self.set_filters(filename, current)

    # Ref: picasa3.exe @ 0x00658900 (ytImageMetadata::Text, editpanel/edittextpanel)
    def get_raw_text(self, filename: str) -> Optional[str]:
        """
        FR: Retourne l'entrée brute `text=` d'une photo (incluant les paramètres de police/couleur/position), ou None.
        EN: Returns the raw `text=` entry of a photo (including font/color/position parameters), or None.
        """
        sec = self.get_section(filename)
        if not sec:
            return None
        return sec.get("text")

    def get_text(self, filename: str) -> Optional[str]:
        """
        FR: Retourne l'annotation textuelle (outil Texte) d'une photo, ou None.
        Supporte le format natif `CTextItemList` de `picasa3.exe` (`<num_items>;<utf8_len>;<texte>;<police>;...`,
        Ref: `0x00A4DB30` / `0x00A4DD50`), le format à 12 champs (`Police;taille;...;texte`) et le texte brut.
        EN: Returns the text overlay annotation (Text tool) of a photo, or None.
        Supports the native `picasa3.exe` `CTextItemList` format (`<num_items>;<utf8_len>;<text>;<font>;...`,
        Ref: `0x00A4DB30` / `0x00A4DD50`), the 12-field format (`Font;size;...;text`), and plain text.
        """
        sec = self.get_section(filename)
        if not sec:
            return None
        val = sec.get("text")
        if not val:
            return val
        # Format natif CTextItemList (0x00A4DB30 / 0x00A4DD50) : <num_items>;<utf8_len>;<utf8_text>;<font>;...
        first_semi = val.find(";")
        if first_semi > 0 and val[:first_semi].strip().isdigit():
            second_semi = val.find(";", first_semi + 1)
            if second_semi > first_semi + 1 and val[first_semi + 1 : second_semi].strip().isdigit():
                try:
                    utf8_len = int(val[first_semi + 1 : second_semi].strip())
                    rest_bytes = val[second_semi + 1 :].encode("utf-8")
                    if len(rest_bytes) >= utf8_len:
                        return rest_bytes[:utf8_len].decode("utf-8", errors="replace")
                except Exception:
                    pass
        parts = val.split(";", 11)
        if len(parts) == 12 and "," in parts[8] and "," in parts[9]:
            return parts[11]
        return val

    def set_text(self, filename: str, text: Optional[str]) -> None:
        """
        FR: Définit ou supprime l'annotation textuelle (text= et textactive=) d'une photo.
        EN: Sets or removes the text overlay annotation (text= and textactive=) of a photo.
        Ref: picasa3.exe @ 0x00456A15, func_00456a15.c:3189
        """
        sec = self.get_or_create_section(filename)
        if not text:
            sec.remove("text")
            sec.remove("textactive")
        else:
            sec.set("text", text)
            sec.set("textactive", "1")

    # Ref: picasa3.exe @ 0x0068B800 ("star=yes\r\n")
    def is_starred(self, filename: str) -> bool:
        """
        FR: Indique si la photo possède le statut favori (star=yes).
        EN: Indicates whether the photo is marked as starred (star=yes).
        """
        sec = self.get_section(filename)
        if not sec:
            return False
        return sec.get("star", "").lower() == "yes"

    def set_starred(self, filename: str, starred: bool) -> None:
        """
        FR: Active ou désactive l'étoile (star=yes) sur une photo.
        EN: Enables or disables the star flag (star=yes) on a photo.
        """
        sec = self.get_or_create_section(filename)
        if starred:
            sec.set("star", "yes")
        else:
            sec.remove("star")

    set_star = set_starred

    # Ref: picasa3.exe @ 0x0068B5E0 ("rotate=rotate(%d)\r\n"), 0x0042A6F9 ("rotate(-1)" -> 0)
    def get_rotate(self, filename: str) -> int:
        """
        FR: Retourne le pas de rotation (0..3) d'une photo (rotate(-1) signifie 0).
        EN: Returns the rotation step (0..3) of a photo (rotate(-1) means 0).
        """
        sec = self.get_section(filename)
        if not sec:
            return 0
        val = sec.get("rotate")
        if not val:
            return 0
        m = re.search(r"-?\d+", val)
        if not m:
            return 0
        num = int(m.group(0))
        if num < 0:
            return 0
        return num % 4

    def set_rotate(self, filename: str, rotation: int) -> None:
        """
        FR: Définit ou supprime le pas de rotation rotate=rotate(N) d'une photo.
        EN: Sets or removes the rotation step rotate=rotate(N) of a photo.
        """
        sec = self.get_or_create_section(filename)
        rot = rotation % 4
        if rot == 0:
            sec.remove("rotate")
        else:
            sec.set("rotate", f"rotate({rot})")

    get_rotation = get_rotate
    set_rotation = set_rotate

    # Ref: picasa3.exe @ 0x0068B8D0 ("keywords=%s\r\n")
    def get_keywords(self, filename: str) -> List[str]:
        """
        FR: Retourne la liste des mots-clés associés à une photo.
        EN: Returns the list of keywords associated with a photo.
        """
        sec = self.get_section(filename)
        if not sec:
            return []
        val = sec.get("keywords")
        if not val:
            return []
        return [k.strip() for k in val.split(",") if k.strip()]

    def set_keywords(self, filename: str, keywords: Union[List[str], str]) -> None:
        """
        FR: Définit ou supprime la liste des mots-clés (keywords=) d'une photo.
        EN: Sets or removes the keywords list (keywords=) of a photo.
        """
        sec = self.get_or_create_section(filename)
        if isinstance(keywords, str):
            clean = [k.strip() for k in keywords.split(",") if k.strip()]
        else:
            clean = [str(k).strip() for k in keywords if str(k).strip()]
        if not clean:
            sec.remove("keywords")
        else:
            sec.set("keywords", ",".join(clean))

    # Ref: picasa3.exe @ 0x0068B870 ("caption=%s\r\n")
    def get_caption(self, filename: str) -> str:
        """
        FR: Retourne la légende (`caption=`) d'une photo, ou une chaîne vide.
        EN: Returns the caption (`caption=`) of a photo, or an empty string.
        """
        sec = self.get_section(filename)
        if not sec:
            return ""
        return sec.get("caption") or ""

    def set_caption(self, filename: str, caption: Optional[str]) -> None:
        """
        FR: Définit ou supprime la légende (`caption=`) d'une photo.
        EN: Sets or removes the caption (`caption=`) of a photo.
        """
        sec = self.get_or_create_section(filename)
        if not caption:
            sec.remove("caption")
        else:
            sec.set("caption", caption)

    # Ref: picasa3.exe @ 0x00CA7810 - Contacts2
    def get_contacts(self) -> Dict[str, ContactInfo]:
        """
        FR: Extrait le dictionnaire des contacts définis dans la section [Contacts2].
        EN: Extracts the dictionary of contacts defined in the [Contacts2] section.
        """
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
        FR: Sérialise le document complet en respectant exactement l'encodage et les séparateurs.
        EN: Serializes the full document while strictly preserving encoding and line separators.
        Ref: FUN_0068ac80
        """
        from picasa_py.ini.writer import PicasaIniWriter
        return PicasaIniWriter.to_bytes(self)

    def write_file(self, path: str) -> None:
        """
        FR: Enregistre le document INI de manière atomique et sûre sur disque.
        EN: Atomically and safely writes the INI document to disk.
        Ref: FUN_0068ac80
        """
        from picasa_py.ini.writer import PicasaIniWriter
        PicasaIniWriter.write_atomic(path, self)

