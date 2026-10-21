"""FR: Analyse par désassemblage les appels suivant chaque référence croisée à `.picasa.ini` dans picasa3.exe.
EN: Analyzes via disassembly the calls following each cross-reference to `.picasa.ini` in picasa3.exe.
"""

import pefile
import capstone

pe = pefile.PE("bin/Picasa3.exe")
image_base = pe.OPTIONAL_HEADER.ImageBase
with open("bin/Picasa3.exe", "rb") as f:
    data = f.read()

# Load xrefs from earlier
xrefs = [
    0x00410FF5, 0x0042A4FD, 0x0043308B, 0x00433D3A, 0x004416AF, 0x00441EF6,
    0x00445B21, 0x004544FA, 0x00454847, 0x004567AB, 0x0045B96A, 0x0045C0CA,
    0x0045C22D, 0x0046328C, 0x0046D968, 0x0046DA5C, 0x0046E09A, 0x0046E3E6,
    0x0046E813, 0x004719DF, 0x00472938, 0x004754E4, 0x0047886C, 0x004788EF,
    0x00479578, 0x004795E7, 0x004849A8, 0x004E6D30, 0x004E6D5A, 0x00501664,
    0x0052A864, 0x0052AB55, 0x0052B26B, 0x0052C3A9, 0x00543383, 0x005434A5,
    0x005A9ABA, 0x005AB433, 0x005CA368, 0x005CA3DC, 0x005E6F34, 0x005ED934,
    0x00603CF7, 0x00603EE3, 0x0068ACBB, 0x0069616B, 0x00697865, 0x006B5506,
    0x00706B3B, 0x007100AF, 0x007101E6, 0x00740296, 0x007403BD, 0x00740F5A,
    0x00740F6C, 0x00740F91, 0x0077FA23, 0x007D9747, 0x007DB04E, 0x007DB0B0,
    0x007DB96A
]

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

print("Scanning xrefs to .picasa.ini:")
for xref in xrefs:
    rva = xref - image_base
    chunk = data[rva - 10 : rva + 40]
    insns = list(md.disasm(chunk, xref - 10))
    for ins in insns:
        if "c80a6c" in ins.op_str.lower() or "0xc80a6c" in ins.op_str.lower():
            # Find next calls
            following_calls = [i for i in insns if i.mnemonic == 'call' and i.address > ins.address]
            call_targets = [i.op_str for i in following_calls[:3]]
            print(f"  0x{ins.address:08X}: {ins.mnemonic:<6} {ins.op_str:<30} -> calls: {call_targets}")
            break
