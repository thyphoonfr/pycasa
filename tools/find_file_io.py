"""FR: Localise les entrées IAT et appels indirects à CreateFileA, CreateFileW et ReadFile dans picasa3.exe.
EN: Locates IAT entries and indirect calls to CreateFileA, CreateFileW, and ReadFile in picasa3.exe.
"""

import pefile
import capstone
import struct

pe = pefile.PE("bin/Picasa3.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase

create_file_iat = []
read_file_iat = []

for entry in pe.DIRECTORY_ENTRY_IMPORT:
    dll = entry.dll.decode('latin1', 'ignore').lower()
    if 'kernel32' in dll:
        for imp in entry.imports:
            if imp.name:
                name = imp.name.decode('latin1', 'ignore')
                if name == 'CreateFileA':
                    create_file_iat.append((name, imp.address))
                elif name == 'CreateFileW':
                    create_file_iat.append((name, imp.address))
                elif name == 'ReadFile':
                    read_file_iat.append((name, imp.address))

print("IAT entries:")
for n, a in create_file_iat + read_file_iat:
    print(f"  {n}: 0x{a:08X}")

with open("bin/Picasa3.exe", "rb") as f:
    data = f.read()

# Search for calls to ReadFile IAT: call dword ptr [0xXXXXXXXX] -> ff 15 xx xx xx xx
for name, iat_va in read_file_iat:
    pat = b"\xFF\x15" + struct.pack("<I", iat_va)
    idx = 0
    matches = []
    while True:
        pos = data.find(pat, idx)
        if pos == -1:
            break
        rva = pe.get_rva_from_offset(pos)
        va = image_base + rva if rva else 0
        matches.append((va, pos))
        idx = pos + 1
    print(f"Calls to {name} (IAT 0x{iat_va:08X}): {len(matches)} occurrences")
    for va, pos in matches:
        print(f"  -> call at VA 0x{va:08X}")
