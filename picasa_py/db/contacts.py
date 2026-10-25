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


@dataclass
class Contact:
    """
    FR: Représente un contact individuel (personne identifiée) dans contacts.xml.
    EN: Represents an individual contact (identified person) in contacts.xml.
    """
    id: str
    name: str
    modified_time: str = ""
    local_contact: str = "1"
    extra_attrs: Dict[str, str] = field(default_factory=dict)

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

    @property
    def by_id(self) -> Dict[str, Contact]:
        """
        FR: Retourne un dictionnaire indexé par identifiant hexadécimal de contact.
        EN: Returns a dictionary indexed by hexadecimal contact ID.
        """
        return {c.id: c for c in self.contacts}

    def get(self, contact_id: str, default: Optional[Contact] = None) -> Optional[Contact]:
        """
        FR: Récupère un contact par son identifiant hexadécimal.
        EN: Retrieves a contact by its hexadecimal identifier.
        """
        return self.by_id.get(contact_id, default)

    def add_contact(self, contact: Contact) -> None:
        """
        FR: Ajoute ou met à jour un contact dans la liste.
        EN: Adds or updates a contact in the list.
        """
        for i, existing in enumerate(self.contacts):
            if existing.id == contact.id:
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
        known_keys = {"id", "name", "display", "modified_time", "local_contact"}
        for elem in root.findall("contact"):
            extra = {k: v for k, v in elem.attrib.items() if k not in known_keys}
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
        FR: Sauvegarde atomique de contacts.xml sur disque.
        EN: Atomically saves contacts.xml to disk.
        """
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        tmp_path = abs_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.to_xml())
        os.replace(tmp_path, abs_path)

