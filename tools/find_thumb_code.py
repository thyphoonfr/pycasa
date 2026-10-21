"""FR: Recherche les chaînes et références croisées liées à CThumbDB, thumbindex.db et aux conteneurs *_index.db.
EN: Searches for strings and cross-references related to CThumbDB, thumbindex.db, and *_index.db containers.
"""

import pefile
import struct

pe = pefile.PE("bin/Picasa3.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase
with open("bin/Picasa3.exe", "rb") as f:
    data = f.read()

targets = [
    b"CThumbDB",
    b"thumbindex.db",
    b"thumbs_index.db",
    b"%s_index.db",
    b"%s_%d.db",
    b"%s_0.db",
    b"thumbs_0.db",
]

for t in targets:
    idx = 0
    while True:
        pos = data.find(t, idx)
        if pos == -1:
            break
        rva = pe.get_rva_from_offset(pos)
        va = image_base + rva if rva else 0
        print(f"Target {t.decode('latin1')} found at VA 0x{va:08X} (offset 0x{pos:08X})")
        # search xrefs to this VA
        va_bytes = struct.pack("<I", va)
        x_idx = 0
        xrefs = []
        while True:
            x_pos = data.find(va_bytes, x_idx)
            if x_pos == -1:
                break
            x_rva = pe.get_rva_from_offset(x_pos)
            x_va = image_base + x_rva if x_rva else 0
            xrefs.append(x_va)
            x_idx = x_pos + 1
        print(f"  -> {len(xrefs)} xrefs found: {[hex(x) for x in xrefs[:5]]}")
        idx = pos + len(t)
