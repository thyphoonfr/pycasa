import pefile
import struct
import capstone

pe = pefile.PE("bin/Picasa3.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase
with open("bin/Picasa3.exe", "rb") as f:
    data = f.read()

# Search for 0x3FCCCCCD
magic_bytes = b"\xCD\xCC\xCC\x3F"
idx = 0
matches = []
while True:
    pos = data.find(magic_bytes, idx)
    if pos == -1:
        break
    rva = pe.get_rva_from_offset(pos)
    va = image_base + rva if rva else 0
    matches.append((va, pos))
    idx = pos + 1

print(f"Occurrences of 0x3FCCCCCD: {len(matches)}")
for va, pos in matches:
    print(f"  VA 0x{va:08X} (offset 0x{pos:08X})")

# Also search for 0x1332 (4914) as 16-bit or 32-bit immediate
# push 0x1332 -> 68 32 13 00 00
# cmp ..., 0x1332 -> ...
pat_1332 = b"\x32\x13"
idx = 0
matches_1332 = []
while True:
    pos = data.find(b"\x68\x32\x13\x00\x00", idx)
    if pos == -1:
        break
    rva = pe.get_rva_from_offset(pos)
    va = image_base + rva if rva else 0
    matches_1332.append((va, pos))
    idx = pos + 1

print(f"Occurrences of push 0x1332: {len(matches_1332)}")
for va, pos in matches_1332:
    print(f"  VA 0x{va:08X} (offset 0x{pos:08X})")
