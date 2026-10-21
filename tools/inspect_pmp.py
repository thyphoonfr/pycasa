"""FR: Inspecte les en-têtes binaires des fichiers .pmp dans le répertoire db3 de Picasa.
EN: Inspects the binary headers of .pmp files in the Picasa db3 directory.
"""

import os
import glob
import struct


def inspect_pmps() -> None:
    """FR: Lit et affiche la taille, les octets d'en-tête en hexadécimal et les entiers 32 bits des fichiers .pmp.
    EN: Reads and prints the size, hex header bytes, and 32-bit integers of .pmp files.
    """
    db3_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3")
    pmp_files = glob.glob(os.path.join(db3_dir, "*.pmp"))
    print(f"Found {len(pmp_files)} .pmp files in {db3_dir}")
    
    print(f"{'Filename':<35} {'Size':>8} {'Magic/Head Hex':<30} {'Header Ints'}")
    print("-" * 90)
    for p in sorted(pmp_files)[:25]:
        name = os.path.basename(p)
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            head = f.read(32)
        head_hex = head[:16].hex()
        # Parse potential 32-bit ints
        ints = [struct.unpack("<I", head[i:i+4])[0] for i in range(0, min(len(head), 24), 4)]
        print(f"{name:<35} {size:>8} {head_hex:<30} {ints}")


if __name__ == "__main__":
    inspect_pmps()
