"""
Tests de round-trip pour contacts.xml.
"""

import os
from pathlib import Path
import pytest
from picasa_py.db.contacts import ContactsFile, Contact


def test_synthetic_contacts_roundtrip():
    contacts = [
        Contact(id="aa28c3a53f34c2f8", name="Alice", modified_time="2026-02-16T05:32:52+01:00", local_contact="1"),
        Contact(id="d58a057b4464a07a", name="Bob", modified_time="2026-08-26T15:52:06+02:00", local_contact="1"),
    ]
    cf = ContactsFile(contacts=contacts)
    xml_str = cf.to_xml()

    parsed = ContactsFile.from_xml(xml_str)
    assert len(parsed.contacts) == 2
    assert parsed.by_id["aa28c3a53f34c2f8"].name == "Alice"
    assert parsed.to_xml() == xml_str


def test_real_contacts_roundtrip():
    contacts_path = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\contacts\contacts.xml"))
    if not contacts_path.exists():
        pytest.skip("contacts.xml introuvable")

    original_text = contacts_path.read_text(encoding="utf-8")
    cf = ContactsFile.from_xml(original_text)
    assert len(cf.contacts) > 0
    reconstructed = cf.to_xml()
    # Formatage identique (avec saut de ligne)
    assert reconstructed.strip() == original_text.strip()
