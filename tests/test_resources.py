"""
Validation tests for extracted PE resources, style definitions, and XML configs.

Ref: AGENTS.md §4 bis.2 (PE Resources verification)
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
import pytest

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "ui" / "resources"


def test_extracted_icons_validity():
    icon_dir = RESOURCES_DIR / "icons"
    assert icon_dir.exists(), "icons directory must exist"
    
    manifest_file = icon_dir / "icons.json"
    assert manifest_file.exists(), "icons.json manifest must exist"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    
    assert len(manifest) == 11, f"Expected 11 group icons, found {len(manifest)}"
    
    # Check main app icon (group 105)
    app_icon_path = icon_dir / "group_icon_105.ico"
    assert app_icon_path.exists(), "Main application icon 105 must exist"
    with Image.open(app_icon_path) as img:
        assert img.format == "ICO"
        assert img.size == (256, 256) or img.size[0] >= 16


def test_extracted_cursors_validity():
    cur_dir = RESOURCES_DIR / "cursors"
    assert cur_dir.exists(), "cursors directory must exist"
    
    manifest_file = cur_dir / "cursors.json"
    assert manifest_file.exists(), "cursors.json manifest must exist"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    
    assert len(manifest) == 12, f"Expected 12 cursors, found {len(manifest)}"
    
    for cid in range(1, 13):
        cur_file = cur_dir / f"cursor_{cid}.cur"
        assert cur_file.exists(), f"cursor_{cid}.cur must exist"
        data = cur_file.read_bytes()
        assert len(data) > 22
        # Check cursor type magic = 2
        assert data[2:4] == b"\x02\x00"


def test_extracted_strings_table():
    str_file = RESOURCES_DIR / "strings" / "strings.json"
    assert str_file.exists(), "strings.json must exist"
    strings = json.loads(str_file.read_text(encoding="utf-8"))
    
    assert len(strings) >= 200
    assert strings.get("195") == "Favorites"
    assert strings.get("196") == "Folders"
    assert strings.get("200") == "Albums"
    assert strings.get("242") == "Red Eye"


def test_constants_ui_parsing():
    from picasa_py.ini.parser import PicasaIniParser
    
    const_file = RESOURCES_DIR / "style" / "constants.ui"
    assert const_file.exists(), "constants.ui must exist"
    
    doc = PicasaIniParser.parse_file(str(const_file))
    sec = doc.get_section("Picasa2")
    assert sec is not None
    assert sec.get("alist_height") == "22"
    assert sec.get("alist_indent") == "17"
    assert sec.get("alayout_gutter") == "24"
    assert sec.get("alayout_thumbGutterX") == "12"
    assert sec.get("alayout_thumbGutterY") == "22"
    assert sec.get("thumbsel_color1") == "#009EFF"
    assert sec.get("thumbsel_color2") == "#FFFFFF"


def test_shortcuts_xml_validity():
    sc_file = RESOURCES_DIR / "xml" / "SHORTCUTS.XML"
    assert sc_file.exists(), "SHORTCUTS.XML must exist"
    
    root = ET.fromstring(sc_file.read_text(encoding="utf-8"))
    assert root.tag == "shortcuts"
    keymaps = root.findall("keymap")
    assert len(keymaps) > 0


def test_fen_layout_files_validity():
    fen_dir = RESOURCES_DIR / "fen"
    assert fen_dir.exists(), "fen directory must exist"
    fen_files = list(fen_dir.glob("*.fen"))
    assert len(fen_files) >= 40
    
    for f in fen_files:
        content = f.read_text(encoding="utf-8")
        # Every .fen file is an XML document with a root element like <window> or similar
        root = ET.fromstring(content)
        assert root.tag in ("window", "dialog", "panel", "wizard", "group")
