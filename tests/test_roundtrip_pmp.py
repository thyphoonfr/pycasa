"""
FR: Tests de validation round-trip binaire strict pour les fichiers .pmp.
Conformément à AGENTS.md §3 et §7 :
"Round-trip : lecture puis réécriture identique au bit près sur tous les fichiers de référence."
EN: Strict binary round-trip validation tests for .pmp files.
In accordance with AGENTS.md §3 and §7:
"Round-trip: reading followed by rewriting is bit-for-bit identical across all reference files."
"""

import os
import glob
import pytest
from picasa_py.db.pmp import PmpFile

FIXTURES_DB_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "db")


def get_db_fixtures():
    """
    FR: Retourne la liste des fichiers .pmp de référence situés dans tests/fixtures/db.
    EN: Return the list of reference .pmp fixture files located in tests/fixtures/db.
    """
    files = glob.glob(os.path.join(FIXTURES_DB_DIR, "*.pmp"))
    assert len(files) > 0, "Aucune fixture .pmp trouvée dans tests/fixtures/db"
    return files


@pytest.mark.parametrize("filepath", get_db_fixtures())
def test_fixtures_pmp_bit_exact_roundtrip(filepath):
    """
    FR: Vérifie qu'un fichier .pmp de fixture relu puis réécrit
    est strictement identique au bit près à l'original.
    EN: Verify that a fixture .pmp file read and rewritten is strictly bit-for-bit identical to the original.
    """
    with open(filepath, "rb") as f:
        original_bytes = f.read()

    pmp = PmpFile.from_bytes(original_bytes)
    serialized_bytes = pmp.to_bytes()

    assert serialized_bytes == original_bytes, (
        f"Différence binaire sur fixture {os.path.basename(filepath)} !\n"
        f"Original : {len(original_bytes)} octets, Produit : {len(serialized_bytes)} octets"
    )


def test_all_system_pmps_roundtrip():
    """
    FR: Teste l'intégralité des fichiers .pmp réels présents dans db3/
    (test en lecture seule).
    EN: Test all real .pmp files present in db3/ (read-only test).
    """
    db3_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3")
    pmp_files = glob.glob(os.path.join(db3_dir, "*.pmp"))
    if not pmp_files:
        pytest.skip("Aucun fichier db3 .pmp disponible sur ce système.")

    tested_count = 0
    for path in pmp_files:
        with open(path, "rb") as f:
            original_bytes = f.read()

        pmp = PmpFile.from_bytes(original_bytes)
        serialized_bytes = pmp.to_bytes()

        assert serialized_bytes == original_bytes, (
            f"Échec roundtrip sur fichier réel : {os.path.basename(path)} "
            f"(Type: {pmp.pmp_type.name}, Taille orig: {len(original_bytes)}, produit: {len(serialized_bytes)})"
        )
        tested_count += 1

    print(f"\n{tested_count} fichiers .pmp réels validés avec succès au bit près.")
