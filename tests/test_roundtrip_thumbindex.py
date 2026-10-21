"""
FR: Tests de round-trip bit-exact pour thumbindex.db (Picasa File & Folder Index).
Vérifie l'exigence non négociable 1 d'AGENTS.md :
Lecture puis réécriture identique au bit près sur le format binaire.
EN: Bit-exact round-trip tests for thumbindex.db (Picasa File & Folder Index).
Verifies non-negotiable requirement 1 of AGENTS.md:
Reading followed by rewriting is bit-for-bit identical on the binary format.
"""

import os
from pathlib import Path
import pytest
from picasa_py.db.thumbindex import (
    ThumbIndexFile,
    ThumbIndexRecord,
    THUMBINDEX_MAGIC,
)


def test_synthetic_thumbindex_roundtrip():
    """
    FR: Vérifie le round-trip binaire sur un index thumbindex.db synthétique.
    EN: Verify binary round-trip on a synthetic thumbindex.db index.
    """
    records = [
        ThumbIndexRecord(
            path="C:\\Photos\\Vacances\\",
            ft1=132500000000000000,
            ft2=132500000000000000,
            size=0,
            type=1,
            flags=256,
            parent_idx=0xFFFFFFFF,
        ),
        ThumbIndexRecord(
            path="C:\\Photos\\Vacances\\image001.jpg",
            ft1=132511111111111111,
            ft2=132522222222222222,
            size=2048500,
            type=2,
            flags=0,
            parent_idx=0,
        ),
    ]

    tf = ThumbIndexFile(magic=THUMBINDEX_MAGIC, records=records)
    data = tf.to_bytes()

    tf_parsed = ThumbIndexFile.from_bytes(data)
    assert tf_parsed.magic == THUMBINDEX_MAGIC
    assert len(tf_parsed.records) == 2
    assert tf_parsed.records[0].path == "C:\\Photos\\Vacances\\"
    assert tf_parsed.records[1].size == 2048500
    assert tf_parsed.records[1].parent_idx == 0

    assert tf_parsed.to_bytes() == data


def test_fixture_thumbindex_roundtrip():
    """
    FR: Vérifie le round-trip bit-exact sur le fichier de référence thumbindex_sample.db.
    EN: Verify bit-exact round-trip on the reference thumbindex_sample.db fixture file.
    """
    fixture_path = Path("tests/fixtures/db/thumbindex_sample.db")
    assert fixture_path.exists()
    data = fixture_path.read_bytes()
    tf = ThumbIndexFile.from_bytes(data)
    assert tf.magic == THUMBINDEX_MAGIC
    assert len(tf.records) == 2
    assert tf.to_bytes() == data


def test_real_thumbindex_roundtrip():
    """
    FR: Vérifie le round-trip bit-exact sur le fichier thumbindex.db réel de Picasa 3 s'il existe.
    EN: Verify bit-exact round-trip on the real Picasa 3 thumbindex.db file if it exists.
    """
    db_path = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3\thumbindex.db"))
    if not db_path.exists():
        pytest.skip(f"Fichier de référence non trouvé : {db_path}")

    with open(db_path, "rb") as f:
        original_data = f.read()

    # Lecture sans modification
    tf = ThumbIndexFile.from_bytes(original_data)
    assert tf.magic == THUMBINDEX_MAGIC
    assert len(tf.records) > 0

    # Ré-écriture
    reconstructed_data = tf.to_bytes()

    # Exigence AGENTS.md : 100% identique au bit près
    assert reconstructed_data == original_data, (
        f"Différence binaire détectée ! "
        f"Original: {len(original_data)} octets, "
        f"Reconstruit: {len(reconstructed_data)} octets"
    )
