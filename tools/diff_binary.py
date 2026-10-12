"""
Outil de comparaison binaire stricte (diff octet par octet).
Utilisé pour valider la conformité stricte bit-à-bit imposée par AGENTS.md.
"""

import sys

def diff_files(file1: str, file2: str, max_diffs: int = 10) -> bool:
    with open(file1, "rb") as f1, open(file2, "rb") as f2:
        b1 = f1.read()
        b2 = f2.read()

    if b1 == b2:
        print(f"[OK] Identique au bit près ({len(b1)} octets) : {file1} == {file2}")
        return True

    print(f"[FAIL] Différence détectée : {file1} ({len(b1)} octets) != {file2} ({len(b2)} octets)")
    min_len = min(len(b1), len(b2))
    diff_count = 0
    for i in range(min_len):
        if b1[i] != b2[i]:
            print(f"  Offset 0x{i:08X} ({i}): 0x{b1[i]:02X} != 0x{b2[i]:02X}")
            diff_count += 1
            if diff_count >= max_diffs:
                print(f"  ... et d'autres différences (limité à {max_diffs})")
                break
    if len(b1) != len(b2):
        print(f"  Différence de taille : taille 1 = {len(b1)}, taille 2 = {len(b2)}")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: py tools/diff_binary.py <file1> <file2>")
        sys.exit(1)
    equal = diff_files(sys.argv[1], sys.argv[2])
    sys.exit(0 if equal else 1)
