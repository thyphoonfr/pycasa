"""FR: Recherche les chaînes ASCII et UTF-16LE liées aux fichiers .picasa.ini dans picasa3.exe.
EN: Searches for ASCII and UTF-16LE strings related to .picasa.ini files in picasa3.exe.
"""

import pefile


def scan_strings() -> None:
    """FR: Parcourt picasa3.exe pour trouver les chaînes cibles en ASCII et UTF-16LE et affiche leurs VA.
    EN: Scans picasa3.exe to find target strings in ASCII and UTF-16LE and prints their VAs.
    """
    pe = pefile.PE("bin/Picasa3.exe")
    image_base = pe.OPTIONAL_HEADER.ImageBase
    print(f"Image Base: 0x{image_base:08X}")
    
    with open("bin/Picasa3.exe", "rb") as f:
        data = f.read()

    targets = [
        ".picasa.ini",
        "Picasa.ini",
        "picasa.ini",
        "[Picasa]",
        "[encoding]",
        "[contacts2]",
        "[albums]",
        "[faces]",
        "crop64",
        "filters=",
        "backuphash=",
        "faces=",
        "caption=",
        "star=",
        "albums=",
    ]

    for target in targets:
        # Search ASCII
        target_bytes = target.encode("ascii")
        idx = 0
        while True:
            pos = data.find(target_bytes, idx)
            if pos == -1:
                break
            rva = pe.get_rva_from_offset(pos)
            va = image_base + rva if rva is not None else 0
            # get surrounding null-terminated string
            s = pos
            while s > 0 and data[s-1] != 0:
                s -= 1
            e = pos
            while e < len(data) and data[e] != 0:
                e += 1
            s_decoded = data[s:e].decode("latin1", errors="replace")
            print(f"[ASCII] {target} @ file 0x{pos:08X}, VA 0x{va:08X}: {repr(s_decoded)}")
            idx = pos + 1

        # Search UTF-16LE
        target_u16 = target.encode("utf-16le")
        idx = 0
        while True:
            pos = data.find(target_u16, idx)
            if pos == -1:
                break
            rva = pe.get_rva_from_offset(pos)
            va = image_base + rva if rva is not None else 0
            s = pos
            while s >= 2 and data[s-2:s] != b"\x00\x00":
                s -= 2
            e = pos
            while e + 2 <= len(data) and data[e:e+2] != b"\x00\x00":
                e += 2
            u_decoded = data[s:e].decode("utf-16le", errors="replace")
            print(f"[UTF16] {target} @ file 0x{pos:08X}, VA 0x{va:08X}: {repr(u_decoded)}")
            idx = pos + 2


if __name__ == "__main__":
    scan_strings()
