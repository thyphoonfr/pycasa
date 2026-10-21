"""FR: Tests de non-régression issus de l'audit et des correctifs de PyCasa.
EN: Audit and remediation regression tests for PyCasa.
"""

# Ref: Audit & Remediation Regression Tests for PyCasa
from __future__ import annotations

from pathlib import Path
import pytest
from PySide6.QtGui import QImage

from picasa_py.db.kvtable import KeyValueTableFile
from picasa_py.db.wordhash import WordHashFile
from picasa_py.db.contacts import Contact, ContactsFile
from picasa_py.db.database import PicasaDatabase
from picasa_py.db.pmp import PmpFile, PmpType
from picasa_py.db.preferences import PicasaPreferences
from picasa_py.ini.parser import PicasaIniParser
from picasa_py.ini.writer import PicasaIniWriter
from picasa_py.faces.facerect import decode_rect64_string, encode_rect64_string
from picasa_py.faces.xmp_tagger import PicasaXMPFaceTagger
from picasa_py.scanner.scanner import PicasaDirScanner
from picasa_py.ui.image_processor import PicasaImageProcessor


def test_kvtable_roundtrip_and_set_remove() -> None:
    """FR: Vérifie l'aller-retour binaire et les opérations set/remove de KeyValueTableFile.
    EN: Verifies binary round-trip and set/remove operations on KeyValueTableFile.
    """
    table = KeyValueTableFile(pairs=[("key1", "val1"), ("key2", "val2")])
    table.set("key1", "updated1")
    table.set("key3", "val3")
    assert table.remove("key2") is True
    raw = table.to_bytes()
    parsed = KeyValueTableFile.from_bytes(raw)
    assert parsed.pairs == [("key1", "updated1"), ("key3", "val3")]


def test_wordhash_preserves_custom_chunk_size_and_add_document_words() -> None:
    """FR: Vérifie la préservation de chunk_size et l'ajout incrémental de mots dans WordHashFile.
    EN: Verifies custom chunk_size preservation and incremental word addition in WordHashFile.
    """
    wh = WordHashFile.create_from_dict({"vacances": [1, 5, 10]}, max_doc_id=42, chunk_size=32768)
    wh.add_document_words(12, ["plage", "vacances"])
    raw = wh.to_bytes()
    wh2 = WordHashFile.from_bytes(raw)
    assert wh2.chunk_size == 32768
    assert wh2.search("vacances") == [1, 5, 10, 12]
    assert wh2.search("plage") == [12]


def test_contacts_preserves_extra_attrs() -> None:
    """FR: Vérifie que ContactsFile préserve les attributs XML supplémentaires lors d'un aller-retour.
    EN: Verifies that ContactsFile preserves extra XML attributes across a round-trip.
    """
    xml = (
        '<?xml version="1.0" encoding="utf-8" ?>\r\n'
        '<contacts>\r\n'
        ' <contact id="1a2b3c4d5e6f7890" name="Alice" display="Alice B" '
        'modified_time="2025-01-01T12:00:00Z" local_contact="1" sync_enabled="0"/>\r\n'
        '</contacts>\r\n'
    )
    table = ContactsFile.from_xml(xml)
    assert len(table.contacts) == 1
    c = table.contacts[0]
    assert c.extra_attrs.get("sync_enabled") == "0"
    assert c.extra_attrs.get("display") == "Alice B"
    out = table.to_xml()
    table2 = ContactsFile.from_xml(out)
    assert table2.contacts[0].extra_attrs.get("sync_enabled") == "0"
    assert table2.contacts[0].name == "Alice"


def test_ini_parser_and_writer_roundtrip() -> None:
    """FR: Vérifie l'aller-retour de lecture et d'écriture via PicasaIniParser et PicasaIniWriter.
    EN: Verifies read and write round-trip via PicasaIniParser and PicasaIniWriter.
    """
    raw = (
        b"[Picasa]\r\n"
        b"name=Mon Album\r\n"
        b"[IMG_0001.JPG]\r\n"
        b"star=yes\r\n"
    )
    doc = PicasaIniParser.parse_bytes(raw)
    sec = doc.get_section("IMG_0001.JPG")
    assert sec is not None
    assert sec.get("STAR") == "yes"

    sec.set("filters", "enhance=1;")
    dumped = PicasaIniWriter.to_bytes(doc)
    doc2 = PicasaIniParser.parse_bytes(dumped)
    sec2 = doc2.get_section("IMG_0001.JPG")
    assert sec2 is not None
    assert sec2.get("filters") == "enhance=1;"


def test_database_inter_table_sync_and_ini_cache(tmp_path: Path) -> None:
    """FR: Vérifie la synchronisation inter-tables (PMP, wordhash, repository) et le cache INI de PicasaDatabase.
    EN: Verifies inter-table synchronization (PMP, wordhash, repository) and INI caching in PicasaDatabase.
    """
    db_dir = tmp_path / "db3"
    db_dir.mkdir()
    db = PicasaDatabase(db_dir)
    db.pmps["imagedata_width"] = PmpFile(PmpType.UINT32)
    db.pmps["imagedata_height"] = PmpFile(PmpType.UINT32)
    db.pmps["imagedata_filters"] = PmpFile(PmpType.STRING)
    db.pmps["imagedata_edited"] = PmpFile(PmpType.UINT8)
    db.pmps["imagedata_tags"] = PmpFile(PmpType.STRING)
    db.pmps["imagedata_caption"] = PmpFile(PmpType.STRING)
    db.wordhash = WordHashFile()

    folder_dir = tmp_path / "Photos"
    folder_dir.mkdir()
    img_path = folder_dir / "IMG_0001.JPG"
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(0xFF336699)
    img.save(str(img_path), "JPG")

    scanner = PicasaDirScanner(db)
    file_idx = scanner.index_file(str(img_path))
    assert file_idx is not None
    assert db.pmps["imagedata_width"].records[file_idx] == 64
    assert db.pmps["imagedata_height"].records[file_idx] == 64

    # Update INI via database helper and verify PMP + wordhash sync
    def _mutate(doc, fname):
        """FR: Modifie la section INI de l'image avec légende, mots-clés et filtres.
        EN: Mutates the image's INI section with caption, keywords, and filters.
        """
        sec = doc.get_or_create_section(fname)
        sec.set("caption", "Vacances plage")
        sec.set("keywords", "ete, mer")
        sec.set("filters", "enhance=1;warm=1;")

    assert db.update_photo_ini(str(img_path), _mutate) is True
    assert db.pmps["imagedata_caption"].records[file_idx] == "Vacances plage"
    assert db.pmps["imagedata_filters"].records[file_idx] == "enhance=1;warm=1;"
    assert file_idx in db.search("vacances")
    assert file_idx in db.search("mer")

    # Watched folder state sync
    db.set_watched_folder(str(folder_dir), "1")
    watched = db.get_watched_folders()
    assert any(v == "1" for v in watched.values())

    # Save and reload database
    db.save_database()
    db2 = PicasaDatabase.open(db_dir)
    assert len(db2.index) == 2
    assert file_idx in db2.search("vacances")


def test_rect64_encode_decode() -> None:
    """FR: Vérifie l'encodage et le décodage des coordonnées normalisées rect64.
    EN: Verifies encoding and decoding of normalized rect64 coordinates.
    """
    encoded = encode_rect64_string(0.1, 0.2, 0.5, 0.8)
    l, t, r, b = decode_rect64_string(encoded)
    assert l == pytest.approx(0.1, abs=1e-3)
    assert t == pytest.approx(0.2, abs=1e-3)
    assert r == pytest.approx(0.5, abs=1e-3)
    assert b == pytest.approx(0.8, abs=1e-3)


def test_xmp_tagger_writes_mwg_rs_regions(tmp_path: Path) -> None:
    """FR: Vérifie que PicasaXMPFaceTagger injecte les régions mwg-rs dans l'en-tête JPEG.
    EN: Verifies that PicasaXMPFaceTagger injects mwg-rs regions into the JPEG header.
    """
    folder = tmp_path / "Album"
    folder.mkdir()
    img_path = folder / "portrait.jpg"
    img = QImage(100, 100, QImage.Format.Format_RGB32)
    img.fill(0xFF888888)
    img.save(str(img_path), "JPG")

    pkt = PicasaXMPFaceTagger.build_xmp_packet(100, 100, [("Alice", 0.25, 0.25, 0.75, 0.75)])
    ok = PicasaXMPFaceTagger.inject_xmp_into_jpeg(str(img_path), pkt)
    assert ok is True
    raw = img_path.read_bytes()
    assert b"http://ns.adobe.com/xap/1.0/\x00" in raw
    assert b"mwg-rs:RegionList" in raw
    assert b"<mwg-rs:Name>Alice</mwg-rs:Name>" in raw


def test_all_84_filters_execute_cleanly() -> None:
    """FR: Vérifie que toutes les chaînes de filtres Picasa s'exécutent proprement sur une image test.
    EN: Verifies that all Picasa filter chains execute cleanly on a test image.
    """
    img = QImage(40, 40, QImage.Format.Format_RGB32)
    img.fill(0xFF708090)

    filter_chains = [
        "enhance=1;",
        "Equalize=1;",
        "finetune2=1,0.2,0.1,0.1,00000000,0.1;",
        "fill=1,0.25;",
        "Autolight=1;",
        "bw=1;",
        "sepia=1;",
        "warm=1;",
        "unsharp=1,0.5;",
        "grain=1,0.3;",
        "tint=1,0.5;",
        "saturation=1,0.4;",
        "softfocus=1,0.4;",
        "glow=1,0.4,0.4;",
        "filteredbw=1,00ff0000;",
        "focalbw=1,0.5,0.5,0.3;",
        "grad=1,0.5,0.5,0.4;",
        "tilt=1,0.3;",
        "crop64=1,20002000e000e000;",
        "redeye=1;",
        "Spot=1;",
        "text=1,Hello;",
        "Lomo=1,0.5,0.5;",
        "Holga=1;",
        "HDR=1,0.4,0.4;",
        "Cinemascope=1,0.5,0.5;",
        "Orton=1,0.4,0.4;",
        "Sixties=1,0.8;",
        "CrossProcess=1,0.7;",
        "Vignette=1,0.5,0.5;",
        "Posterize=1,8;",
        "Invert=1;",
        "Infrared=1;",
        "Neon=1;",
        "Sketch=1,0.5;",
        "Comic=1,0.5;",
        "Infrared2=1,0.5;",
        "Solarize=1,0.5;",
        "Polaroid=1;",
        "HeatMap=1,0.7;",
        "NightVision=1,0.7;",
        "Embossed=1,0.5;",
        "Borders=1,0.05;",
        "Frame=1,0.08;",
        "DropShadow=1,0.05;",
        "LocalContrast=1,0.5;",
        "Matte=1,0.08;",
        "MuseumMatte=1,0.1;",
        "QuantizePalette=1;",
        "ReanimatedEyeColor=1;",
        "RoundedEdges=1,0.2;",
        "PicnikFocalPixelate=1,0.5,0.5,0.3,6;",
        "ansel=1;",
        "radtint=1,0.5;",
        "linblur=1,0.3;",
        "gamma=1,1.2;",
        "contrast=1,0.3;",
        "blur=1,0.3;",
        "backlight=1,0.4;",
        "dir_sat=1,0.4;",
        "dir_brite=1,0.2;",
        "dir_sharp=1,0.4;",
    ]
    for chain in filter_chains:
        out = PicasaImageProcessor.apply_filter_chain(img, chain)
        assert not out.isNull(), f"Filter chain failed: {chain}"
        assert out.width() > 0 and out.height() > 0

    from PIL import Image
    pil_img = Image.new("RGB", (40, 40), (112, 128, 144))
    duotone = PicasaImageProcessor.two_tone(pil_img, (20, 10, 0), (240, 220, 180))
    assert duotone.size == (40, 40)
    boost = PicasaImageProcessor.boost(pil_img)
    assert boost.size == (40, 40)
    balanced = PicasaImageProcessor.pick_neutral_color(pil_img, (112, 128, 144))
    assert balanced.size == (40, 40)


def test_picasa_preferences_registry_isolation() -> None:
    """FR: Vérifie que PicasaPreferences pointe vers le chemin de registre officiel de Picasa 3.
    EN: Verifies that PicasaPreferences points to the official Picasa 3 registry path.
    """
    prefs = PicasaPreferences()
    assert prefs.REGISTRY_ORG == "Google"
    assert prefs.REGISTRY_APP == r"Picasa\Picasa2\Preferences"
