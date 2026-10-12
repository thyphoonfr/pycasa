"""
Module de lecture et d'écriture de contacts.xml (Picasa Contacts).
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Contact:
    id: str
    name: str
    modified_time: str = ""
    local_contact: str = "1"


class ContactsFile:
    """
    Gestion du fichier contacts.xml de Picasa.
    """

    def __init__(self, contacts: List[Contact] | None = None):
        self.contacts: List[Contact] = contacts if contacts is not None else []

    @property
    def by_id(self) -> Dict[str, Contact]:
        return {c.id: c for c in self.contacts}

    @classmethod
    def from_xml(cls, xml_text: str) -> ContactsFile:
        root = ET.fromstring(xml_text.strip())
        contacts: List[Contact] = []
        for elem in root.findall("contact"):
            contacts.append(Contact(
                id=elem.get("id", ""),
                name=elem.get("name", ""),
                modified_time=elem.get("modified_time", ""),
                local_contact=elem.get("local_contact", "1"),
            ))
        return cls(contacts=contacts)

    def to_xml(self) -> str:
        lines: List[str] = ["<contacts>"]
        for c in self.contacts:
            lines.append(
                f' <contact id="{c.id}" name="{c.name}" modified_time="{c.modified_time}" local_contact="{c.local_contact}"/>'
            )
        lines.append("</contacts>\n")
        return "\n".join(lines)
