"""
FR: Tests de round-trip bit-exact pour les tables clé-valeur (repository.dat, usernames.dat).
Vérifie l'exigence non négociable 1 d'AGENTS.md :
Lecture puis réécriture identique au bit près sur le format binaire.
EN: Bit-exact round-trip tests for key-value tables (repository.dat, usernames.dat).
Verifies non-negotiable requirement 1 of AGENTS.md:
Reading followed by rewriting is bit-for-bit identical on the binary format.
"""

import os
from pathlib import Path
import pytest
from picasa_py.db.kvtable import KeyValueTableFile, KV_MAGIC


def test_synthetic_kvtable_roundtrip():
    """
    FR: Vérifie le round-trip binaire sur une table clé-valeur synthétique.
    EN: Verify binary round-trip on a synthetic key-value table.
    """
    pairs = [
        ("DBID", "81a8e549932f5031577db0e4d3be7269"),
        ("Folders", "1"),
        ("frversion", "1.5"),
    ]
    kv = KeyValueTableFile(pairs=pairs)
    data = kv.to_bytes()

    parsed = KeyValueTableFile.from_bytes(data)
    assert parsed.magic == KV_MAGIC
    assert parsed.pairs == pairs
    assert parsed.mapping["DBID"] == "81a8e549932f5031577db0e4d3be7269"
    assert parsed.to_bytes() == data


def test_fixtures_kvtable_roundtrip():
    """
    FR: Vérifie le round-trip bit-exact sur les fixtures repository_sample.dat et usernames_sample.dat.
    EN: Verify bit-exact round-trip on the repository_sample.dat and usernames_sample.dat fixtures.
    """
    for name in ["repository_sample.dat", "usernames_sample.dat"]:
        p = Path(f"tests/fixtures/db/{name}")
        assert p.exists()
        data = p.read_bytes()
        kv = KeyValueTableFile.from_bytes(data)
        assert kv.magic == KV_MAGIC
        assert kv.to_bytes() == data


def test_real_kvtable_roundtrip():
    """
    FR: Vérifie le round-trip bit-exact sur les fichiers repository.dat et usernames.dat réels s'ils existent.
    EN: Verify bit-exact round-trip on real repository.dat and usernames.dat files if they exist.
    """
    db_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3"))
    if not db_dir.exists():
        pytest.skip(f"Répertoire de référence non trouvé : {db_dir}")

    for name in ["repository.dat", "usernames.dat"]:
        path = db_dir / name
        if not path.exists():
            continue
        original_data = path.read_bytes()
        kv = KeyValueTableFile.from_bytes(original_data)
        assert kv.magic == KV_MAGIC
        reconstructed = kv.to_bytes()
        assert reconstructed == original_data, (
            f"Différence binaire sur {name} ! "
            f"Original: {len(original_data)}, Reconstruit: {len(reconstructed)}"
        )
