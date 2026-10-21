"""
FR: Tests de round-trip bit-exact pour CBlockFile (*_0.db et *_index.db).
Vérifie l'exigence non négociable 1 d'AGENTS.md :
Lecture puis réécriture identique au bit près sur le format binaire.
EN: Bit-exact round-trip tests for CBlockFile (*_0.db and *_index.db).
Verifies non-negotiable requirement 1 of AGENTS.md:
Reading followed by writing produces bit-for-bit identical binary output.
"""

import glob
import os
from pathlib import Path
import pytest
from picasa_py.db.blockfile import (
    BlockEntry,
    BlockIndexFile,
    BlockContainerFile,
    BLOCKFILE_MAGIC,
)


def test_synthetic_blockfile_roundtrip():
    """
    FR: Vérifie le round-trip binaire sur un conteneur CBlockFile et son fichier d'index synthétiques.
    EN: Verify binary round-trip on a synthetic CBlockFile container and its index file.
    """
    # 1. Création d'un container avec 2 blobs
    container = BlockContainerFile()
    blob1 = b"\xff\xd8\xff\xe0" + b"TEST_JPEG_1" + b"\xff\xd9"
    blob2 = b"\xff\xd8\xff\xe0" + b"TEST_JPEG_2_LONGER" + b"\xff\xd9"

    entry0 = BlockEntry(checksum=0, offset=0, size=0, block=0)
    entry1 = container.append_blob(blob1, checksum=0x12345678, block_idx=0)
    entry2 = container.append_blob(blob2, checksum=0x9ABCDEF0, block_idx=0)

    assert entry1.offset == 4
    assert entry1.size == len(blob1)
    assert entry2.offset == 4 + len(blob1)
    assert entry2.size == len(blob2)

    # Vérification extraction de blobs
    assert container.get_blob(entry0) == b""
    assert container.get_blob(entry1) == blob1
    assert container.get_blob(entry2) == blob2

    # 2. Test round-trip du container
    c_bytes = container.to_bytes()
    assert len(c_bytes) == 4 + len(blob1) + len(blob2)
    c_parsed = BlockContainerFile.from_bytes(c_bytes)
    assert c_parsed.magic == BLOCKFILE_MAGIC
    assert c_parsed.get_blob(entry1) == blob1
    assert c_parsed.get_blob(entry2) == blob2
    assert c_parsed.to_bytes() == c_bytes

    # 3. Test round-trip de l'index
    index = BlockIndexFile.from_entries([entry0, entry1, entry2], active_block=0)
    idx_bytes = index.to_bytes()
    assert len(idx_bytes) == 20 + 3 * 12

    idx_parsed = BlockIndexFile.from_bytes(idx_bytes)
    assert idx_parsed.magic == BLOCKFILE_MAGIC
    assert idx_parsed.active_block == 0
    assert idx_parsed.record_count == 3
    parsed_entries = idx_parsed.get_entries()
    assert parsed_entries[1].offset == entry1.offset
    assert parsed_entries[1].size == entry1.size
    assert parsed_entries[1].checksum == 0x12345678
    assert idx_parsed.to_bytes() == idx_bytes


def test_fixtures_blockfile_roundtrip():
    """
    FR: Vérifie le round-trip bit-exact sur les fichiers CBlockFile de référence dans tests/fixtures/db/.
    EN: Verify bit-exact round-trip on the reference CBlockFile fixtures in tests/fixtures/db/.
    """
    idx_path = Path("tests/fixtures/db/thumbs_sample_index.db")
    c_path = Path("tests/fixtures/db/thumbs_sample_0.db")

    idx = BlockIndexFile.from_bytes(idx_path.read_bytes())
    assert idx.magic == BLOCKFILE_MAGIC
    assert idx.record_count == 3
    assert idx.to_bytes() == idx_path.read_bytes()

    container = BlockContainerFile.from_bytes(c_path.read_bytes())
    assert container.magic == BLOCKFILE_MAGIC
    assert container.to_bytes() == c_path.read_bytes()

    entries = idx.get_entries()
    blob1 = container.get_blob(entries[1])
    assert blob1[:2] == b"\xff\xd8"
    assert blob1[-2:] == b"\xff\xd9"


def test_all_real_index_files_roundtrip():
    """
    FR: Vérifie le round-trip bit-exact sur tous les fichiers *_index.db réels du dossier db3 local.
    EN: Verify bit-exact round-trip on all real *_index.db files in the local db3 directory.
    """
    db_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3"))
    if not db_dir.exists():
        pytest.skip(f"Répertoire de référence non trouvé : {db_dir}")

    index_files = list(db_dir.glob("*_index.db"))
    assert len(index_files) >= 5, f"Moins de 5 fichiers d'index trouvés : {index_files}"

    for idx_path in index_files:
        original_data = idx_path.read_bytes()
        idx = BlockIndexFile.from_bytes(original_data)
        assert idx.magic == BLOCKFILE_MAGIC

        reconstructed_data = idx.to_bytes()
        assert reconstructed_data == original_data, (
            f"Différence binaire sur {idx_path.name} ! "
            f"Original: {len(original_data)}, Reconstruit: {len(reconstructed_data)}"
        )


def test_real_thumbs_container_and_index():
    """
    FR: Vérifie l'extraction de miniatures JPEG et le round-trip bit-exact sur thumbs_index.db et thumbs_0.db réels.
    EN: Verify JPEG thumbnail extraction and bit-exact round-trip on real thumbs_index.db and thumbs_0.db.
    """
    db_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3"))
    if not db_dir.exists():
        pytest.skip(f"Répertoire de référence non trouvé : {db_dir}")

    idx_path = db_dir / "thumbs_index.db"
    container_path = db_dir / "thumbs_0.db"
    if not idx_path.exists() or not container_path.exists():
        pytest.skip("thumbs_index.db ou thumbs_0.db absent")

    idx = BlockIndexFile.from_bytes(idx_path.read_bytes())
    entries = idx.get_entries()

    with open(container_path, "rb") as f:
        container_bytes = f.read()

    container = BlockContainerFile.from_bytes(container_bytes)
    assert container.magic == BLOCKFILE_MAGIC

    # Vérification de l'extraction sur les entrées valides
    valid_count = 0
    for entry in entries:
        if not entry.is_empty and entry.block == 0:
            blob = container.get_blob(entry)
            assert len(blob) == entry.size
            # Vérifier l'en-tête JPEG (SOI: FF D8) et fin (EOI: FF D9)
            assert blob[:2] == b"\xff\xd8", f"En-tête JPEG invalide à l'offset {entry.offset}"
            assert blob[-2:] == b"\xff\xd9", f"Fin JPEG invalide à l'offset {entry.offset}"
            valid_count += 1
            if valid_count >= 10:
                break

    assert valid_count > 0, "Aucune miniature trouvée dans le conteneur"

    # Vérification round-trip bit-exact sur le conteneur complet
    assert container.to_bytes() == container_bytes
