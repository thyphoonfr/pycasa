"""FR: Extraction de toutes les ressources PE, fichiers XML d'internationalisation, définitions de mise en page FEN,
et tables de menus/raccourcis depuis les binaires et répertoires runtime de Picasa 3.
EN: Extraction of all PE resources, XML internationalization, FEN layout definitions,
and menu/shortcut tables from Picasa3 binaries and runtime directories.

Ref: picasa3.exe @ PE Resource Directory
Ref: Picasa3i18n.dll @ PE Resource Directory (Type: XMLF)
Ref: runtime/*.fen, runtime/constants.ui
"""

import os
import sys
import json
import struct
import io
import re
from pathlib import Path
import pefile

BASE_DIR = Path(__file__).resolve().parent.parent
EXE_PATH = BASE_DIR / "bin" / "Picasa3.exe"
PICASA_INSTALL = Path(r"C:\Program Files (x86)\Google\Picasa3")
I18N_DLL_PATH = PICASA_INSTALL / "Picasa3i18n.dll"
RUNTIME_DIR = PICASA_INSTALL / "runtime"
OUT_DIR = BASE_DIR / "ui" / "resources"


def extract_icons(pe: pefile.PE, out_dir: Path):
    """FR: Extrait les groupes d'icônes (RT_GROUP_ICON / RT_ICON) du binaire PE vers des fichiers .ico.
    EN: Extracts icon groups (RT_GROUP_ICON / RT_ICON) from the PE binary into .ico files.
    """
    icon_dir = out_dir / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    
    group_icons = {}
    raw_icons = {}
    
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id == pefile.RESOURCE_TYPE["RT_GROUP_ICON"]:
            for sub in entry.directory.entries:
                data_rva = sub.directory.entries[0].data.struct.OffsetToData
                size = sub.directory.entries[0].data.struct.Size
                group_icons[sub.id] = pe.get_data(data_rva, size)
        elif entry.id == pefile.RESOURCE_TYPE["RT_ICON"]:
            for sub in entry.directory.entries:
                data_rva = sub.directory.entries[0].data.struct.OffsetToData
                size = sub.directory.entries[0].data.struct.Size
                raw_icons[sub.id] = pe.get_data(data_rva, size)
                
    manifest = {}
    for gid, gdata in group_icons.items():
        idReserved, idType, idCount = struct.unpack_from("<HHH", gdata, 0)
        ico = bytearray()
        ico += struct.pack("<HHH", idReserved, idType, idCount)
        offset = 6 + 16 * idCount
        images = []
        entries_info = []
        for i in range(idCount):
            w, h, c, res, planes, bpp, size, nid = struct.unpack_from("<BBBBHHIH", gdata, 6 + i * 14)
            ico += struct.pack("<BBBBHHII", w, h, c, res, planes, bpp, size, offset)
            raw_img = raw_icons.get(nid, b"")
            images.append(raw_img)
            offset += size
            entries_info.append({"width": w or 256, "height": h or 256, "bpp": bpp, "res_id": nid})
        
        for img in images:
            ico += img
            
        ico_file = icon_dir / f"group_icon_{gid}.ico"
        ico_file.write_bytes(ico)
        manifest[gid] = {"file": ico_file.name, "image_count": idCount, "frames": entries_info}
        
    (icon_dir / "icons.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Extracted {len(group_icons)} ICO groups into {icon_dir}")


def extract_cursors(pe: pefile.PE, out_dir: Path):
    """FR: Extrait les curseurs (RT_CURSOR) du binaire PE vers des fichiers .cur.
    EN: Extracts cursors (RT_CURSOR) from the PE binary into .cur files.
    """
    cur_dir = out_dir / "cursors"
    cur_dir.mkdir(parents=True, exist_ok=True)
    
    raw_cursors = {}
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id == pefile.RESOURCE_TYPE["RT_CURSOR"]:
            for sub in entry.directory.entries:
                data_rva = sub.directory.entries[0].data.struct.OffsetToData
                size = sub.directory.entries[0].data.struct.Size
                raw_cursors[sub.id] = pe.get_data(data_rva, size)
                
    manifest = {}
    for cid, raw in raw_cursors.items():
        hx, hy = struct.unpack_from("<HH", raw, 0)
        cur_img = raw[4:]
        
        cur = bytearray()
        cur += struct.pack("<HHH", 0, 2, 1)  # 2 = CURSOR
        cur += struct.pack("<BBBBHHII", 32, 32, 0, 0, hx, hy, len(cur_img), 22)
        cur += cur_img
        
        cur_file = cur_dir / f"cursor_{cid}.cur"
        cur_file.write_bytes(cur)
        manifest[cid] = {"file": cur_file.name, "hotspot_x": hx, "hotspot_y": hy, "size_bytes": len(cur)}
        
    (cur_dir / "cursors.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Extracted {len(raw_cursors)} CUR files into {cur_dir}")


def extract_strings(pe: pefile.PE, out_dir: Path):
    """FR: Extrait les tables de chaînes (RT_STRING) du binaire PE vers strings.json.
    EN: Extracts string tables (RT_STRING) from the PE binary into strings.json.
    """
    str_dir = out_dir / "strings"
    str_dir.mkdir(parents=True, exist_ok=True)
    
    strings = {}
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id == pefile.RESOURCE_TYPE["RT_STRING"]:
            for block in entry.directory.entries:
                block_id = block.id
                data_rva = block.directory.entries[0].data.struct.OffsetToData
                size = block.directory.entries[0].data.struct.Size
                raw = pe.get_data(data_rva, size)
                
                offset = 0
                for i in range(16):
                    str_id = (block_id - 1) * 16 + i
                    if offset + 2 > len(raw):
                        break
                    length = struct.unpack_from("<H", raw, offset)[0]
                    offset += 2
                    if length > 0:
                        s = raw[offset:offset + length * 2].decode("utf-16le", errors="replace")
                        offset += length * 2
                        strings[str_id] = s
                        
    (str_dir / "strings.json").write_text(json.dumps(strings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Extracted {len(strings)} strings into {str_dir / 'strings.json'}")


def extract_dialogs(pe: pefile.PE, out_dir: Path):
    """FR: Extrait les modèles de boîtes de dialogue (RT_DIALOG) du binaire PE.
    EN: Extracts dialog templates (RT_DIALOG) from the PE binary.
    """
    dlg_dir = out_dir / "dialogs"
    dlg_dir.mkdir(parents=True, exist_ok=True)
    
    dialogs = {}
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id == pefile.RESOURCE_TYPE["RT_DIALOG"]:
            for sub in entry.directory.entries:
                data_rva = sub.directory.entries[0].data.struct.OffsetToData
                size = sub.directory.entries[0].data.struct.Size
                raw = pe.get_data(data_rva, size)
                bin_file = dlg_dir / f"dialog_{sub.id}.bin"
                bin_file.write_bytes(raw)
                dialogs[sub.id] = {"file": bin_file.name, "size": size}
                
    (dlg_dir / "dialogs.json").write_text(json.dumps(dialogs, indent=2), encoding="utf-8")
    print(f"Extracted {len(dialogs)} dialogs into {dlg_dir}")


def extract_manifest(pe: pefile.PE, out_dir: Path):
    """FR: Extrait le manifeste côte-à-côte (RT_MANIFEST) du binaire PE.
    EN: Extracts the side-by-side manifest (RT_MANIFEST) from the PE binary.
    """
    mf_dir = out_dir / "manifest"
    mf_dir.mkdir(parents=True, exist_ok=True)
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id == pefile.RESOURCE_TYPE["RT_MANIFEST"]:
            for sub in entry.directory.entries:
                data_rva = sub.directory.entries[0].data.struct.OffsetToData
                size = sub.directory.entries[0].data.struct.Size
                raw = pe.get_data(data_rva, size)
                (mf_dir / "picasa.manifest").write_bytes(raw)
                print(f"Extracted manifest into {mf_dir / 'picasa.manifest'}")


def extract_fen_and_runtime(out_dir: Path):
    """FR: Copie les fichiers de mise en page .fen et les fichiers de configuration du répertoire runtime.
    EN: Copies .fen layout files and configuration files from the runtime directory.
    """
    fen_dir = out_dir / "fen"
    fen_dir.mkdir(parents=True, exist_ok=True)
    style_dir = out_dir / "style"
    style_dir.mkdir(parents=True, exist_ok=True)
    
    fen_count = 0
    if RUNTIME_DIR.exists():
        for fen_file in RUNTIME_DIR.glob("*.fen"):
            content = fen_file.read_bytes()
            (fen_dir / fen_file.name).write_bytes(content)
            fen_count += 1
            
        for fn in ["constants.ui", "defaults.ini", "filterdesc.xml", "properties.xml", "filters.txt", "bezier.txt", "fliprtl.txt", "geotag.kml"]:
            src = RUNTIME_DIR / fn
            if src.exists():
                (style_dir / fn).write_bytes(src.read_bytes())
                
    print(f"Extracted {fen_count} .fen layout files into {fen_dir}")
    print(f"Extracted runtime style/config files into {style_dir}")


def extract_i18n_xml(out_dir: Path):
    """FR: Extrait les fichiers XML de traduction (ressource XMLF) depuis Picasa3i18n.dll.
    EN: Extracts translation XML files (XMLF resource) from Picasa3i18n.dll.
    """
    xml_dir = out_dir / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    
    if not I18N_DLL_PATH.exists():
        print(f"Warning: {I18N_DLL_PATH} not found!")
        return
        
    pe = pefile.PE(str(I18N_DLL_PATH))
    extracted = 0
    manifest = {}
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if str(entry.name) == "XMLF":
            for sub in entry.directory.entries:
                name = str(sub.name) if sub.name else str(sub.id)
                data_rva = sub.directory.entries[0].data.struct.OffsetToData
                size = sub.directory.entries[0].data.struct.Size
                raw = pe.get_data(data_rva, size)
                target = xml_dir / name
                target.write_bytes(raw)
                manifest[name] = size
                extracted += 1
                
    (xml_dir / "index.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Extracted {extracted} XML internationalization files into {xml_dir}")


def extract_menus_and_shortcuts(out_dir: Path):
    """FR: Extrait la table des menus et raccourcis clavier depuis la section de données de picasa3.exe.
    EN: Extracts the menu and keyboard shortcut table from the data section of picasa3.exe.
    """
    menu_dir = out_dir / "menus"
    menu_dir.mkdir(parents=True, exist_ok=True)
    
    # Read binary to extract menu strings table
    with open(EXE_PATH, "rb") as f:
        f.seek(0x88C000)
        data = f.read(20000)
        
    strings = []
    cur = bytearray()
    for b in data:
        if 32 <= b <= 126:
            cur.append(b)
        elif b == 0:
            if len(cur) > 0:
                strings.append(cur.decode("ascii"))
                cur = bytearray()
        else:
            cur = bytearray()
            
    menus = {
        "File": [],
        "Edit": [],
        "View": [],
        "Folder": [],
        "Picture": [],
        "Create": [],
        "Tools": [],
        "Help": [],
    }
    
    current_menu = None
    i = 0
    items = []
    while i < len(strings):
        s = strings[i]
        if s.startswith("eMenu"):
            # Format is typically ID, Label, and maybe Shortcut or next item
            item_id = s
            label = strings[i+1] if i + 1 < len(strings) and not strings[i+1].startswith("eMenu") else ""
            accel = ""
            offset = 2
            if i + 2 < len(strings) and not strings[i+2].startswith("eMenu"):
                accel = strings[i+2]
                offset = 3
            items.append({"id": item_id, "label": label, "accel": accel})
            i += offset
        else:
            i += 1
            
    (menu_dir / "menu_table_raw.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    print(f"Extracted {len(items)} menu items into {menu_dir / 'menu_table_raw.json'}")


def main():
    """FR: Point d'entrée principal pour l'extraction complète des ressources PE et runtime.
    EN: Main entry point for full PE and runtime resource extraction.
    """
    print(f"Opening {EXE_PATH}...")
    pe = pefile.PE(str(EXE_PATH))
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    extract_icons(pe, OUT_DIR)
    extract_cursors(pe, OUT_DIR)
    extract_strings(pe, OUT_DIR)
    extract_dialogs(pe, OUT_DIR)
    extract_manifest(pe, OUT_DIR)
    extract_fen_and_runtime(OUT_DIR)
    extract_i18n_xml(OUT_DIR)
    extract_menus_and_shortcuts(OUT_DIR)
    print("Done extracting all resources!")


if __name__ == "__main__":
    main()
