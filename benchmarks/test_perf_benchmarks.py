"""FR: Benchmarks de performance automatisés pour les opérations critiques de PyCasa.
EN: Automated performance benchmarks for PyCasa critical operations.

Ref: AGENTS.md §4 ter (Performances & Benchmarks automatisés)
Ref: docs/perf/targets.md
Ref: picasa3.exe @ 0x004A1F30, 0x0093E780
"""

from __future__ import annotations

import time
from PySide6.QtGui import QImage

from picasa_py.ini.parser import PicasaIniParser
from picasa_py.ini.writer import PicasaIniWriter
from picasa_py.db.pmp import PmpFile, PmpType
from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord, THUMBINDEX_MAGIC
from picasa_py.db.wordhash import WordHashFile
from picasa_py.ui.image_processor import PicasaImageProcessor


def test_perf_ini_roundtrip() -> None:
    """FR: Vérifie que le parsing et la sérialisation d'un fichier .picasa.ini de 25 sections restent sous 10 ms.
    EN: Verify INI parse + serialize stays well below 10ms for a 25-section .picasa.ini.
    """
    lines = ["[Picasa]\r\n", "name=Test Album\r\n", "P2category=Folders on Disk\r\n"]
    for i in range(25):
        lines.append(f"[IMG_{i:04d}.JPG]\r\n")
        lines.append("star=yes\r\n")
        lines.append("filters=enhance=1;finetune2=1,0.200000,0.100000,0.000000,00000000,0.150000;\r\n")
        lines.append("faces=rect64(123456789abcdef0),1a2b3c4d5e6f7890\r\n")
    raw = "".join(lines).encode("utf-8")

    t0 = time.perf_counter()
    for _ in range(20):
        doc = PicasaIniParser.parse_bytes(raw)
        out = PicasaIniWriter.to_bytes(doc)
    elapsed_ms = ((time.perf_counter() - t0) / 20.0) * 1000.0
    assert out == raw
    assert elapsed_ms < 10.0, f"INI round-trip took {elapsed_ms:.2f}ms (budget: 10.0ms)"


def test_perf_pmp_roundtrip() -> None:
    """FR: Vérifie que la lecture et l'écriture d'une colonne PMP de 5 000 enregistrements restent sous 25 ms.
    EN: Verify PMP column read + write for 5,000 records stays below 25ms.
    """
    col = PmpFile(pmp_type=PmpType.UINT64, records=[i * 1000000 for i in range(5000)])
    raw = col.to_bytes()

    t0 = time.perf_counter()
    col2 = PmpFile.from_bytes(raw)
    raw2 = col2.to_bytes()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert raw2 == raw
    assert elapsed_ms < 25.0, f"PMP 5000-record round-trip took {elapsed_ms:.2f}ms (budget: 25.0ms)"


def test_perf_thumbindex_roundtrip() -> None:
    """FR: Vérifie que la lecture et l'écriture de thumbindex.db pour 2 000 enregistrements restent sous 40 ms.
    EN: Verify thumbindex read + write for 2,000 records stays below 40ms.
    """
    entries = [
        ThumbIndexRecord(
            path=f"IMG_{i:04d}.JPG",
            ft1=130000000000000000 + i,
            ft2=130000000000000000 + i,
            size=2048000 + i,
            type=2,
            flags=0x0100,
            parent_idx=0,
        )
        for i in range(2000)
    ]
    table = ThumbIndexFile(magic=THUMBINDEX_MAGIC, records=entries)
    raw = table.to_bytes()

    t0 = time.perf_counter()
    table2 = ThumbIndexFile.from_bytes(raw)
    raw2 = table2.to_bytes()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert raw2 == raw
    assert elapsed_ms < 40.0, f"thumbindex 2000-record round-trip took {elapsed_ms:.2f}ms (budget: 40.0ms)"


def test_perf_wordhash_roundtrip() -> None:
    """FR: Vérifie que la construction, sérialisation et lecture de wordhash pour 1 000 mots restent sous 40 ms.
    EN: Verify wordhash build + serialize + parse for 1,000 words stays below 40ms.
    """
    index_dict = {f"mot_cle_{i}": [i, (i + 1) % 1000] for i in range(1000)}
    wh = WordHashFile.create_from_dict(index_dict, max_doc_id=1000)
    raw = wh.to_bytes()

    t0 = time.perf_counter()
    wh2 = WordHashFile.from_bytes(raw)
    raw2 = wh2.to_bytes()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert raw2 == raw
    assert elapsed_ms < 40.0, f"wordhash 1000-word round-trip took {elapsed_ms:.2f}ms (budget: 40.0ms)"


def test_perf_image_processor_filter_chain() -> None:
    """FR: Vérifie que PicasaImageProcessor.apply_filter_chain sur un aperçu 800x600 reste sous 80 ms.
    EN: Verify PicasaImageProcessor.apply_filter_chain on an 800x600 preview stays below 80ms.
    """
    img = QImage(800, 600, QImage.Format.Format_RGB32)
    img.fill(0xFF6080A0)
    chain = "enhance=1;finetune2=1,0.200000,0.100000,0.150000,00000000,0.100000;warm=1;"

    # Warm-up run
    PicasaImageProcessor.apply_filter_chain(img, chain)

    t0 = time.perf_counter()
    out = PicasaImageProcessor.apply_filter_chain(img, chain)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert not out.isNull()
    assert out.width() == 800 and out.height() == 600
    assert elapsed_ms < 80.0, f"Filter chain on 800x600 took {elapsed_ms:.2f}ms (budget: 80.0ms)"


def test_perf_100k_scale_library() -> None:
    """FR: Vérifie la tenue en charge sur une très grande photothèque de 100 000 entrées (AGENTS.md §4 ter.1).
    EN: Verifies load performance on a very large 100,000-entry photo library (AGENTS.md §4 ter.1).
    """
    from picasa_py.db.blockfile import BlockIndexFile

    n = 100_000
    col = PmpFile(pmp_type=PmpType.UINT32, records=list(range(n)))
    t0 = time.perf_counter()
    raw_pmp = col.to_bytes()
    col2 = PmpFile.from_bytes(raw_pmp)
    pmp_ms = (time.perf_counter() - t0) * 1000.0
    assert len(col2.records) == n
    assert pmp_ms < 150.0, f"100k PMP round-trip took {pmp_ms:.2f}ms (budget: 150.0ms)"

    bidx = BlockIndexFile(
        checksums=list(range(n)),
        offsets=[4 + i * 2048 for i in range(n)],
        sizes_and_blocks=[2048 for _ in range(n)],
    )
    t1 = time.perf_counter()
    raw_idx = bidx.to_bytes()
    bidx2 = BlockIndexFile.from_bytes(raw_idx)
    idx_ms = (time.perf_counter() - t1) * 1000.0
    assert bidx2.record_count == n
    assert idx_ms < 150.0, f"100k BlockIndexFile round-trip took {idx_ms:.2f}ms (budget: 150.0ms)"
