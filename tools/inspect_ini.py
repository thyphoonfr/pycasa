"""FR: Inspecte l'encodage, les fins de ligne et les en-têtes des fichiers .picasa.ini.
EN: Inspects the encoding, line endings, and headers of .picasa.ini files.
"""

import os
import glob


def inspect_inis() -> None:
    """FR: Parcourt les fichiers .picasa.ini et affiche leurs propriétés de formatage binaire.
    EN: Scans .picasa.ini files and prints their binary formatting properties.
    """
    pictures_dir = os.path.expanduser(r"~\Pictures")
    ini_files = glob.glob(os.path.join(pictures_dir, "**", ".picasa.ini"), recursive=True)
    ini_files += glob.glob(os.path.join(pictures_dir, "**", "Picasa.ini"), recursive=True)
    
    print(f"Found {len(ini_files)} INI files:")
    for path in ini_files:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            raw = f.read()
        
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        has_crlf = b"\r\n" in raw
        has_lf_only = (b"\n" in raw) and (b"\r\n" not in raw)
        
        # Check encoding header
        has_encoding_hdr = b"[encoding]" in raw
        
        print(f"\n--- {path} ({size} bytes) ---")
        print(f"  BOM: {has_bom}, CRLF: {has_crlf}, LF-only: {has_lf_only}, [encoding]: {has_encoding_hdr}")
        print("  First 300 bytes (raw):")
        print(raw[:300])


if __name__ == "__main__":
    inspect_inis()
