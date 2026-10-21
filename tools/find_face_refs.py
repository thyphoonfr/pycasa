"""FR: Recherche les chaînes et références liées à la détection et gestion des visages dans picasa3.exe.
EN: Searches for strings and references related to face detection and management in picasa3.exe.
"""

import pefile

pe = pefile.PE("bin/Picasa3.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase

with open("bin/Picasa3.exe", "rb") as f:
    data = f.read()

targets = [
    b"manual_add",
    b"manual_cancel",
    b"manual_add_editbox",
    b"peoplepanel",
    b"confirmsug",
    b"removesel",
    b"sug_label",
    b"suggestion",
    b"unknownface",
    b"CFaceDetector",
    b"BgFaceDetect",
    b"facetemplates",
    b"FRSuggestionThreshold",
    b"Add a Person",
    b"Ajouter une personne",
    b"Sans nom",
    b"Unnamed",
]

for t in targets:
    pos = 0
    found = 0
    while True:
        pos = data.find(t, pos)
        if pos == -1:
            break
        rva = pe.get_rva_from_offset(pos)
        va = image_base + rva if rva is not None else 0
        s = pos
        while s > 0 and data[s-1] not in (0, 10, 13):
            s -= 1
        e = pos
        while e < len(data) and data[e] not in (0, 10, 13):
            e += 1
        print(f"[{t.decode('latin1', errors='replace')}] file 0x{pos:08X}, VA 0x{va:08X}: {repr(data[s:e].decode('latin1', errors='replace'))}")
        pos += 1
        found += 1
        if found >= 5:
            break
