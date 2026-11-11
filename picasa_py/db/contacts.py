"""
FR: Module de lecture et d'écriture de contacts.xml (Picasa Contacts).
EN: Module for reading and writing contacts.xml (Picasa Contacts).

Traçabilité Ghidra / Ghidra Traceability:
- Ref: picasa3.exe @ 0x00881CC0 (CContactManager / contacts.xml)
- Ref: picasa3.exe @ 0x00CA7810 (Contacts2 / synchronisation contacts.xml)
- Ghidra project: ghidra/picasa3.gpr
"""

from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _escape_xml_attr(val: str) -> str:
    """
    FR: Échappe les caractères spéciaux XML pour un attribut de balise <contact>.
    EN: Escapes special XML characters for a <contact> tag attribute.
    """
    return (
        val.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class Contact:
    """
    FR: Représente un contact individuel (personne identifiée) dans contacts.xml.
    EN: Represents an individual contact (identified person) in contacts.xml.
    """
    id: str
    name: str
    modified_time: str
    local_contact: str
    extra_attrs: Dict[str, str]

    def __init__(
        self,
        id: str,
        name: str,
        modified_time: str = "",
        local_contact: str = "1",
        extra_attrs: Optional[Dict[str, str]] = None,
        email: str = "",
    ) -> None:
        self.id = id
        self.name = name
        self.modified_time = modified_time
        self.local_contact = local_contact
        self.extra_attrs = dict(extra_attrs) if extra_attrs else {}
        if email:
            self.extra_attrs["email0"] = email

    def __repr__(self) -> str:
        return (
            f"Contact(id={self.id!r}, name={self.name!r}, "
            f"modified_time={self.modified_time!r}, local_contact={self.local_contact!r}, "
            f"extra_attrs={self.extra_attrs!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Contact):
            return NotImplemented
        return (
            self.id == other.id
            and self.name == other.name
            and self.modified_time == other.modified_time
            and self.local_contact == other.local_contact
            and self.extra_attrs == other.extra_attrs
        )

    @property
    def email(self) -> str:
        """
        FR: Retourne l'adresse courriel principale (`email0` ou `email`) du contact.
        EN: Returns the contact's primary email address (`email0` or `email`).
        Ref: picasa3.exe @ 0x00580403, 0x00580DB5
        """
        return self.extra_attrs.get("email0") or self.extra_attrs.get("email") or ""

    @email.setter
    def email(self, value: str) -> None:
        if value:
            self.extra_attrs["email0"] = value
        else:
            self.extra_attrs.pop("email0", None)
            self.extra_attrs.pop("email", None)


class ContactsFile:
    """
    FR: Gestion du fichier contacts.xml de Picasa 3.
    EN: Management of the Picasa 3 contacts.xml file.
    Ref: picasa3.exe @ 0x00881CC0
    """

    def __init__(self, contacts: List[Contact] | None = None):
        """
        FR: Initialise la collection de contacts Picasa.
        EN: Initializes the Picasa contacts collection.
        """
        self.contacts: List[Contact] = contacts if contacts is not None else []

    @staticmethod
    def _cid_variants(contact_id: str) -> List[str]:
        """
        FR: Retourne les variantes 15 et 16 caractères d'un identifiant hexadécimal 64 bits.
        Ref: picasa3.exe @ 0x008A2F76 ("%I64x") vs 0x0065DF80 ("%016I64x")
        EN: Returns the 15-char and 16-char variants of a 64-bit hexadecimal contact ID.
        """
        cid = (contact_id or "").strip().lower()
        if not cid:
            return []
        res = [cid]
        if all(c in "0123456789abcdef" for c in cid) and len(cid) <= 16:
            stripped = cid.lstrip("0") or "0"
            padded = cid.zfill(16)
            if stripped not in res:
                res.append(stripped)
            if padded not in res:
                res.append(padded)
        return res

    @property
    def by_id(self) -> Dict[str, Contact]:
        """
        FR: Retourne un dictionnaire indexé par identifiant hexadécimal de contact.
        EN: Returns a dictionary indexed by hexadecimal contact ID.
        """
        return {c.id: c for c in self.contacts}

    def get(self, contact_id: str, default: Optional[Contact] = None) -> Optional[Contact]:
        """
        FR: Récupère un contact par son identifiant hexadécimal (insensible à la casse et au zéro initial 15/16 car.).
        Ref: picasa3.exe @ 0x008A2F76 ("%I64x") vs 0x0065DF80 ("%016I64x")
        EN: Retrieves a contact by its hexadecimal identifier (case-insensitive and 15/16-char zero-padding tolerant).
        """
        direct = self.by_id.get(contact_id)
        if direct is not None:
            return direct
        variants = set(self._cid_variants(contact_id))
        if variants:
            for c in self.contacts:
                if c.id.strip().lower() in variants or set(self._cid_variants(c.id)) & variants:
                    return c
        return default

    def add_contact(self, contact: Contact) -> None:
        """
        FR: Ajoute ou met à jour un contact dans la liste (en unifiant les variantes 15/16 caractères).
        EN: Adds or updates a contact in the list (unifying 15/16-char variants).
        """
        variants = set(self._cid_variants(contact.id))
        for i, existing in enumerate(self.contacts):
            if existing.id == contact.id or (variants and existing.id.strip().lower() in variants):
                self.contacts[i] = contact
                return
        self.contacts.append(contact)

    @classmethod
    def from_xml(cls, xml_text: str) -> ContactsFile:
        """
        FR: Analyse le contenu XML de contacts.xml et construit une instance ContactsFile.
        EN: Parses the XML content of contacts.xml and builds a ContactsFile instance.
        """
        root = ET.fromstring(xml_text.strip())
        contacts: List[Contact] = []
        known_keys = {"id", "name", "modified_time", "local_contact"}
        for elem in root.findall("contact"):
            extra = {k: v for k, v in elem.attrib.items() if k not in known_keys}
            if "name" not in elem.attrib and "display" in extra:
                extra.pop("display", None)
            # Ref: picasa3.exe @ 0x00580403 (email0="..."), 0x00580DB5 (email%d / email)
            if "email" in extra and "email0" not in extra:
                extra["email0"] = extra.pop("email")
            for child_idx, email_child in enumerate(elem.findall("email")):
                addr = email_child.get("address") or email_child.text or ""
                if addr.strip() and f"email{child_idx}" not in extra:
                    extra[f"email{child_idx}"] = addr.strip()
            contacts.append(Contact(
                id=elem.get("id", ""),
                name=elem.get("name") or elem.get("display", ""),
                modified_time=elem.get("modified_time", ""),
                local_contact=elem.get("local_contact", "1"),
                extra_attrs=extra,
            ))
        return cls(contacts=contacts)

    def to_xml(self) -> str:
        """
        FR: Sérialise les contacts au format XML exact produit par Picasa 3.
        EN: Serializes the contacts into the exact XML format produced by Picasa 3.
        """
        lines: List[str] = ["<contacts>"]
        for c in self.contacts:
            attrs = [
                f'id="{_escape_xml_attr(c.id)}"',
                f'name="{_escape_xml_attr(c.name)}"',
                f'modified_time="{_escape_xml_attr(c.modified_time)}"',
                f'local_contact="{_escape_xml_attr(c.local_contact)}"',
            ]
            for k, v in c.extra_attrs.items():
                attrs.append(f'{k}="{_escape_xml_attr(v)}"')
            lines.append(f" <contact {' '.join(attrs)}/>")
        lines.append("</contacts>\n")
        return "\n".join(lines)

    def save(self, path: str) -> None:
        """
        FR: Sauvegarde directe de contacts.xml sur disque (`0x00586BD0` / `0x005868D0`).
        EN: Directly saves contacts.xml to disk (`0x00586BD0` / `0x005868D0`).
        """
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.to_xml())

