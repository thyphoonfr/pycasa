"""FR: Utilitaire de désassemblage rapide d'une plage d'adresses virtuelles dans picasa3.exe via Capstone.
EN: Quick disassembly utility for a virtual address range in picasa3.exe using Capstone.
"""

import sys
import capstone
import pefile


def disasm_range(start_va: int, count: int = 100) -> None:
    """FR: Désassemble et affiche `count` instructions x86 32 bits à partir de `start_va`.
    EN: Disassembles and prints `count` 32-bit x86 instructions starting at `start_va`.
    """
    pe = pefile.PE("bin/Picasa3.exe")
    image_base = pe.OPTIONAL_HEADER.ImageBase
    with open("bin/Picasa3.exe", "rb") as f:
        data = f.read()

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    start_rva = start_va - image_base
    chunk = data[start_rva:start_rva + 4096]

    for i, insn in enumerate(md.disasm(chunk, start_va)):
        if i >= count:
            break
        print(f"0x{insn.address:08X}:  {insn.bytes.hex():<16}  {insn.mnemonic:<8} {insn.op_str}")


if __name__ == "__main__":
    start = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x0068B7A0
    cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    disasm_range(start, cnt)
