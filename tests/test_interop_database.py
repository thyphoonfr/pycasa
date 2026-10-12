"""
Tests d'intégration de haut niveau pour PicasaDatabase.
"""

import os
from pathlib import Path
import pytest
from picasa_py.db.database import PicasaDatabase


def test_open_default_database():
    db_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3"))
    if not db_dir.exists():
        pytest.skip(f"Répertoire Picasa non trouvé : {db_dir}")

    db = PicasaDatabase.open_default()

    # Vérification thumbindex
    assert db.thumbindex is not None
    assert len(db.thumbindex.records) > 0

    # Vérification repository
    assert db.repository is not None
    assert "DBID" in db.repository.mapping

    # Vérification PMP
    assert len(db.pmps) > 0

    # Vérification CBlockFile
    assert "thumbs" in db.block_indices
    assert "thumbs" in db.block_containers

    # Test extraction de miniature réelle
    # Trouver le premier index non vide
    entries = db.block_indices["thumbs"].get_entries()
    first_valid_idx = next(i for i, e in enumerate(entries) if not e.is_empty)

    thumb_data = db.get_thumbnail(first_valid_idx, size="small")
    assert thumb_data is not None
    assert thumb_data[:2] == b"\xff\xd8"
    assert thumb_data[-2:] == b"\xff\xd9"
