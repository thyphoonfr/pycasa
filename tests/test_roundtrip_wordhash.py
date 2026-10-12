"""
Tests de round-trip bit-exact pour wordhash.dat (Index de recherche textuelle).

Vérifie l'exigence non négociable 1 d'AGENTS.md :
Lecture puis réécriture identique au bit près sur le format binaire.
"""

import os
from pathlib import Path
import pytest
from picasa_py.db.wordhash import WordHashFile, WordEntry, WORDHASH_MAGIC


def test_synthetic_wordhash_roundtrip():
    pool = b"vacances\x00plage\x00soleil\x00"
    entries = [
        WordEntry("vacances", 0, [1, 2, 5]),
        WordEntry("plage", 9, [2, 5]),
        WordEntry("soleil", 15, [5]),
    ]
    wh = WordHashFile(max_doc_id=6, chunk_size=64, pool_bytes=pool, entries=entries)
    data = wh.to_bytes()

    parsed = WordHashFile.from_bytes(data)
    assert parsed.magic == WORDHASH_MAGIC
    assert parsed.max_doc_id == 6
    assert len(parsed.entries) == 3
    assert parsed.entries[0].word == "vacances"
    assert parsed.entries[0].image_ids == [1, 2, 5]
    assert parsed.to_bytes() == data


def test_fixture_wordhash_roundtrip():
    fixture_path = Path("tests/fixtures/db/wordhash_sample.dat")
    assert fixture_path.exists()
    data = fixture_path.read_bytes()
    wh = WordHashFile.from_bytes(data)
    assert wh.magic == WORDHASH_MAGIC
    assert len(wh.entries) == 3
    assert wh.to_bytes() == data


def test_real_wordhash_roundtrip():
    db_path = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3\wordhash.dat"))
    if not db_path.exists():
        pytest.skip(f"Fichier de référence non trouvé : {db_path}")

    original_data = db_path.read_bytes()
    wh = WordHashFile.from_bytes(original_data)
    assert wh.magic == WORDHASH_MAGIC
    assert len(wh.entries) > 0

    reconstructed_data = wh.to_bytes()
    assert reconstructed_data == original_data, (
        f"Différence binaire sur wordhash.dat ! "
        f"Original: {len(original_data)}, Reconstruit: {len(reconstructed_data)}"
    )
