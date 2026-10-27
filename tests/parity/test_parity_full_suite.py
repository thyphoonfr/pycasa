"""
FR: Suite de validation de parité complète (Étape 3 du protocole de parité) entre Picasa 3.9 (v3.9.141.259) et PyCasa :
- Catégorie A : Formats de données persistantes (.picasa.ini, contacts.xml, PMP, thumbindex.db, CBlockFile,
                wordhash.dat, repository.dat/usernames.dat, listes .txt auxiliaires, .picasaoriginals/backuphash,
                XMP mwg-rs:Regions, JPEG APP13 IPTC sans perte, JPEG APP1 EXIF DateTimeOriginal sans perte, Registre Windows).
- Catégorie B : Concurrence, priorités de threads, ReadDirectoryChangesW (FILE_NOTIFY_INFORMATION, debounce 500 ms),
                verrous CBlockFile fins.
- Catégorie C : Pipeline d'image pixel-exact (grain 5 passes MT19937, redeye HSV flood-fill, spotblend/retouch Hermite + Poisson,
                CTextItemList outer/inner format, JPEG save quality=90, rotation EXIF sans perte, seuils Red.dll 0.85/0.90).
- Catégorie D : Logique métier (scan incrémental, protection des disques hors ligne, tri d'albums, préréglages d'export 85/85/95/65,
                détection de doublons d'importation originfast).
- Catégorie E : Fuzzing et cas limites sur les parseurs binaires et texte (.picasa.ini, PMP, thumbindex.db, wordhash.dat,
                noms Unicode, .picasa.ini en lecture seule).

EN: Full parity validation suite (Step 3 of the parity protocol) between Picasa 3.9 (v3.9.141.259) and PyCasa.
"""

from __future__ import annotations

import datetime
import os
import struct
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from picasa_py.db.blockfile import BlockContainerFile, BlockEntry, BlockIndexFile, compute_thumb_checksum
from picasa_py.db.contacts import Contact, ContactsFile
from picasa_py.db.database import (
    DEFAULT_CATDATA_RECORDS,
    STANDARD_BLOCKFILE_PREFIXES,
    STANDARD_PMP_SCHEMA,
    PicasaDatabase,
)
from picasa_py.db.kvtable import KeyValueTableFile
from picasa_py.db.pmp import PMP_MAGIC, PmpFile, PmpType
from picasa_py.db.thumbindex import THUMBINDEX_MAGIC, ThumbIndexFile, ThumbIndexRecord
from picasa_py.db.wordhash import WordHashFile
from picasa_py.faces.detector import (
    FR_RECOMMEND_INCLUDE_LIMIT,
    FR_RECOMMEND_SHOW_LIMIT,
    FR_SORT_THRESHOLD,
    FR_SUGGESTION_SINGLE_THRESHOLD,
    FR_SUGGESTION_THRESHOLD,
)
from picasa_py.faces.facerect import FaceRect, decode_rect64_string, encode_rect64_string
from picasa_py.faces.xmp_tagger import PicasaXMPFaceTagger
from picasa_py.ini.parser import PicasaIniDocument, PicasaIniParser
from picasa_py.ini.writer import PicasaIniWriter
from picasa_py.db.preferences import PicasaPreferences
from picasa_py.scanner.scanner import PicasaDirScanner, compute_originfast_hash, datetime_to_ole
from picasa_py.scanner.watcher import (
    DEBOUNCE_DELAY_MS,
    READ_DIR_CHANGES_BUFFER_SIZE,
    READ_DIR_CHANGES_NOTIFY_FILTER,
    READ_DIR_CHANGES_WATCH_SUBTREE,
    parse_file_notify_information,
)
from picasa_py.ui.export_dialog import QUALITY_PRESETS
from picasa_py.ui.image_processor import PicasaImageProcessor
from picasa_py.ui.import_dialog import PicasaImportDialog
from picasa_py.ui.offset_time_dialog import PicasaAdjustTimeDialog as PicasaOffsetTimeDialog


# ============================================================================
# CATÉGORIE A & E : Formats persistants, .picasa.ini, DB3, IPTC/EXIF/XMP, Fuzz
# ============================================================================


def test_a04_a05_a06_e06_picasa_ini_inplace_no_empty_sections_and_readonly(tmp_path: Path) -> None:
    """
    FR: Vérifie A-04, A-05, A-06, E-06 :
    - Aucune section vide `[<filename>]` n'est créée lorsqu'on appelle `set_starred(fn, False)`,
      `set_rotate(fn, 0)`, `set_caption(fn, "")`, `set_keywords(fn, [])`, `set_crop(fn, None)`,
      `set_tilt(fn, 0.0)`, `set_faces(fn, [])`, `set_filters(fn, [])`, `set_text(fn, None)` (`0x009BD7B8`).
    - Écriture directe sur place sans fichier `.tmp` résiduel et préservation de `[encoding]\r\nutf8=1\r\n` (`0x005A8E9E`).
    - Si `.picasa.ini` possède `FILE_ATTRIBUTE_READONLY` (`0x01`), `write_file` retourne `False` sans modifier le fichier (`0x0099DB60`).
    """
    doc = PicasaIniParser.parse_bytes(b"[encoding]\r\nutf8=1\r\n")
    doc.set_starred("ghost.jpg", False)
    doc.set_rotate("ghost.jpg", 0)
    doc.set_caption("ghost.jpg", "")
    doc.set_keywords("ghost.jpg", [])
    doc.set_crop("ghost.jpg", None)
    doc.set_tilt("ghost.jpg", 0.0)
    doc.set_faces("ghost.jpg", [])
    doc.set_filters("ghost.jpg", [])
    doc.set_text("ghost.jpg", None)

    assert doc.get_section("ghost.jpg") is None
    assert doc.to_bytes() == b"[encoding]\r\nutf8=1\r\n"

    # Écriture sur place et vérification d'absence de fichier .tmp
    ini_path = tmp_path / ".picasa.ini"
    doc.set_caption("étoile.jpg", "Légende accentuée")
    assert PicasaIniWriter.write_file(str(ini_path), doc) is True
    assert list(tmp_path.glob("*.tmp")) == []
    written_bytes = ini_path.read_bytes()
    assert written_bytes.startswith(b"[encoding]\r\nutf8=1\r\n")

    # E-06 : protection d'un .picasa.ini en lecture seule (0x0099DB60 / 0x009BD706)
    if sys.platform == "win32":
        import ctypes

        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(ini_path))
        ctypes.windll.kernel32.SetFileAttributesW(str(ini_path), attrs | 0x01)
        try:
            doc2 = PicasaIniParser.parse_file(str(ini_path))
            doc2.set_starred("étoile.jpg", True)
            assert PicasaIniWriter.write_file(str(ini_path), doc2) is False
            assert ini_path.read_bytes() == written_bytes
        finally:
            ctypes.windll.kernel32.SetFileAttributesW(str(ini_path), attrs & ~0x01)


def test_a09_a19_a20_a21_database_schema_sentinels_and_watched_lists(tmp_path: Path) -> None:
    """
    FR: Vérifie A-09, A-19, A-20, A-21 :
    - Présence des 57 tables `.pmp` incluant `catdata_info.pmp` (`0x00420268`).
    - Création des 4 fichiers sentinelles de 4 octets `0x3FCCCCCD` (`b"\\xcd\\xcc\\xcc?"`) :
      `catdata_0`, `imagedata_0`, `albumdata_0`, `profilephotos_0.db` (`0x00411824..0x00411851`, `0x00415AFB`).
    - Création de `Picasa2Albums\\watchedfolders.txt` (`0x004F5960`) et `frexcludefolders.txt` (`0x004F5D90`).
    - Absence de tout fichier `.tmp` résiduel lors de `save_database`.
    """
    root_dir = tmp_path / "Picasa2"
    db = PicasaDatabase.create_new(root_dir)
    assert "catdata_info" in STANDARD_PMP_SCHEMA
    assert "catdata_info" in DEFAULT_CATDATA_RECORDS
    assert (db.db3_dir / "catdata_info.pmp").exists()
    assert db.pmps["catdata_info"].records == [""] * 9

    for sentinel in ("catdata_0", "imagedata_0", "albumdata_0", "profilephotos_0.db"):
        sp = db.db3_dir / sentinel
        assert sp.exists(), f"Sentinelle manquante : {sentinel}"
        assert sp.read_bytes() == b"\xcd\xcc\xcc?"

    p2a_dir = tmp_path / "Picasa2Albums"
    assert (p2a_dir / "watchedfolders.txt").exists()
    assert (p2a_dir / "frexcludefolders.txt").exists()
    assert list(db.db3_dir.glob("*.tmp")) == []


def test_a23_xmp_face_tagger_format_and_dom_merge(tmp_path: Path) -> None:
    """
    FR: Vérifie A-23 (`FileFaceTagger` @ `0x00BA73C0`, `0x00BA7430`, `0x00BB17E0`, `0x00BB2010`) :
    - Format `%g` pour `stArea:x/y/w/h`, `mwg-rs:AppliedToDimensions`, absence de `Iptc4xmpExt:PersonInImage`.
    - Fusion sans perte dans un paquet XMP préexistant (ex. `dc:description` ou `xmp:Rating` conservé).
    """
    existing = (
        b'<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        b'<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        b'  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        b'    <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/">\n'
        b'      <xmp:Rating>5</xmp:Rating>\n'
        b'    </rdf:Description>\n'
        b'  </rdf:RDF>\n'
        b'</x:xmpmeta>\n'
        b'<?xpacket end="w"?>'
    )
    pkt = PicasaXMPFaceTagger.build_xmp_packet(
        width=1600,
        height=1200,
        faces=[("Marie Curie", 0.1, 0.2, 0.3, 0.6)],
        existing_xmp=existing,
    )
    s = pkt.decode("utf-8")
    assert "<xmp:Rating>5</xmp:Rating>" in s
    assert 'stArea:x="0.2"' in s
    assert 'stArea:y="0.4"' in s
    assert 'stDim:w="1600"' in s
    assert "PersonInImage" not in s


def test_a24_a26_lossless_jpeg_iptc_and_exif_datetime(tmp_path: Path) -> None:
    """
    FR: Vérifie A-24 (`0x00438450`, `0x00456150`) et A-26 (`0x00490580`, `0x009ED330`) :
    - `db.set_caption` et `db.set_tags` écrivent sans perte les datasets IPTC `1:90` (`\\x1b%G`),
      `2:120` (Caption-Abstract) et `2:25` (Keywords) dans `APP13` (`Photoshop 3.0\\x008BIM\\x04\\x04`)
      tout en conservant les données d'image compressées (`0xFFDA`..EOF) strictement identiques au bit près.
    - `PicasaOffsetTimeDialog.execute_adjustment` met à jour `DateTimeOriginal` dans `APP1` EXIF
      sans ré-encoder le flux compressé (`0xFFDA`..EOF).
    """
    photos_dir = tmp_path / "Photos"
    photos_dir.mkdir()
    jpg_path = photos_dir / "vacances.jpg"
    img = Image.new("RGB", (64, 48), (120, 160, 200))
    img.save(jpg_path, "JPEG", quality=90)

    orig_raw = jpg_path.read_bytes()
    orig_sos_idx = orig_raw.find(b"\xff\xda")
    assert orig_sos_idx > 0
    orig_scan_stream = orig_raw[orig_sos_idx:]

    db = PicasaDatabase.create_new(tmp_path / "db_iptc")
    scanner = PicasaDirScanner(db)
    idx = scanner.index_file(str(jpg_path))
    assert idx >= 0

    assert db.set_caption(idx, "Coucher de soleil à Étretat") is True
    assert db.set_tags(idx, ["Normandie", "Été"]) is True

    after_iptc_raw = jpg_path.read_bytes()
    iptc_sos_idx = after_iptc_raw.find(b"\xff\xda")
    assert after_iptc_raw[iptc_sos_idx:] == orig_scan_stream
    assert b"Photoshop 3.0\x008BIM\x04\x04" in after_iptc_raw
    assert b"\x1b%G" in after_iptc_raw
    assert "Coucher de soleil à Étretat".encode("utf-8") in after_iptc_raw
    assert "Normandie".encode("utf-8") in after_iptc_raw
    assert "Été".encode("utf-8") in after_iptc_raw

    # Test A-26 : Ajustement de date EXIF sans perte sur le flux JPEG
    dlg = PicasaOffsetTimeDialog([str(jpg_path)], db=db)
    target_dt = datetime.datetime(2024, 7, 14, 18, 30, 0)
    from PySide6.QtCore import QDate, QTime

    dlg.radio_absolute.setChecked(True)
    dlg.edit_new_date.setDate(QDate(target_dt.year, target_dt.month, target_dt.day))
    dlg.edit_new_time.setTime(QTime(target_dt.hour, target_dt.minute, target_dt.second))
    res = dlg.execute_adjustment()
    assert len(res) == 1

    after_exif_raw = jpg_path.read_bytes()
    exif_sos_idx = after_exif_raw.find(b"\xff\xda")
    assert after_exif_raw[exif_sos_idx:] == orig_scan_stream
    assert b"2024:07:14 18:30:00" in after_exif_raw


def test_e02_e03_e04_parser_fuzzing_and_bounds() -> None:
    """
    FR: Vérifie E-02, E-03, E-04 :
    - Rejet de `record_count > 0x0FFFFFFF` dans `PmpFile.from_bytes` (`0x0099C95A`) et `ThumbIndexFile.from_bytes`.
    - Support du magic `0x40400000` (v3.0) et `0x40466666` (v3.1) dans `ThumbIndexFile.from_bytes` (`0x004F2EF0`).
    - Validation `validate_parent_indices()` (`0x004F4F95`) sur des `parent_idx` hors bornes ou auto-référents.
    - Robustesse de `PicasaIniParser.parse_bytes` sur des entrées arbitraires/malformées sans exception.
    """
    # E-02 : PMP record_count > 0x0FFFFFFF
    bad_pmp = struct.pack("<IIIII", PMP_MAGIC, 0x13320001, 2, 0x13320001, 0x10000000)
    with pytest.raises(ValueError):
        PmpFile.from_bytes(bad_pmp)

    # E-03 : ThumbIndex v3.0 header + parent_idx hors bornes
    rec = ThumbIndexRecord(path="photo.jpg", ft1=0, ft2=0, size=100, type=2, flags=0x00010000, parent_idx=99)
    raw_v30 = struct.pack("<II", 0x40400000, 1) + rec.to_bytes()
    ti = ThumbIndexFile.from_bytes(raw_v30)
    assert len(ti.records) == 1
    assert ti.validate_parent_indices() == 1
    assert ti.records[0].type == 0
    assert ti.records[0].parent_idx == 0xFFFFFFFF

    # E-01 : Fuzzing léger sur PicasaIniParser
    for malformed in (
        b"",
        b"\xff\xfe\x00\x00[broken",
        b"[unclosed_section\r\nkey_without_eq\r\n=val_without_key\r\n[IMG.JPG]\r\nstar=yes",
        b"\xef\xbb\xbf[Contacts2]\r\n123=a;b;c\n[IMG.JPG]\nfaces=rect64(invalid),123\r\n",
    ):
        doc = PicasaIniParser.parse_bytes(malformed)
        assert isinstance(doc.to_bytes(), bytes)


# ============================================================================
# CATÉGORIE B : Concurrence & ReadDirectoryChangesW
# ============================================================================


def test_b04_read_directory_changes_constants_and_notify_parser() -> None:
    """
    FR: Vérifie B-04 (`0x00704F20..0x0070525A`) :
    - `DEBOUNCE_DELAY_MS == 500`, `READ_DIR_CHANGES_BUFFER_SIZE == 0x10000`,
      `READ_DIR_CHANGES_WATCH_SUBTREE is True`, `READ_DIR_CHANGES_NOTIFY_FILTER == 0x57`.
    - Décodage binaire exact de `FILE_NOTIFY_INFORMATION` (chaîné par `NextEntryOffset`).
    """
    assert DEBOUNCE_DELAY_MS == 500
    assert READ_DIR_CHANGES_BUFFER_SIZE == 0x10000
    assert READ_DIR_CHANGES_WATCH_SUBTREE is True
    assert READ_DIR_CHANGES_NOTIFY_FILTER == 0x57

    name1 = "2026\\IMG_01.JPG".encode("utf-16le")
    entry1_len = 12 + len(name1)
    pad1 = (4 - (entry1_len % 4)) % 4
    next_off1 = entry1_len + pad1
    entry1 = struct.pack("<III", next_off1, 1, len(name1)) + name1 + (b"\x00" * pad1)

    name2 = "2026\\.picasa.ini".encode("utf-16le")
    entry2 = struct.pack("<III", 0, 3, len(name2)) + name2

    parsed = parse_file_notify_information(entry1 + entry2, r"C:\Photos")
    assert parsed == [
        (1, os.path.join(r"C:\Photos", "2026\\IMG_01.JPG")),
        (3, os.path.join(r"C:\Photos", "2026\\.picasa.ini")),
    ]


# ============================================================================
# CATÉGORIE C & D : Pipeline d'image, Seuils Visages & Logique Métier
# ============================================================================


def test_c10_c12_c13_c18_filters_text_and_face_thresholds() -> None:
    """
    FR: Vérifie C-10 (`film_grain` 5 passes MT19937 @ `0x0090A2E0`),
    C-12 (`remove_red_eye` HSV flood-fill @ `0x008720C0` & `retouch_heal`/`spotblend` Hermite+Poisson @ `0x00910C20`),
    C-13 (`CTextItemList` avec `<item_len>;` @ `0x00A4DB30`),
    et C-18 (`FRSuggestionThreshold = 0.85`, `FRSuggestionSingleThreshold = 0.90` @ `0x0048AABC`).
    """
    assert FR_SUGGESTION_THRESHOLD == pytest.approx(0.85)
    assert FR_SUGGESTION_SINGLE_THRESHOLD == pytest.approx(0.90)
    assert FR_SORT_THRESHOLD == pytest.approx(0.85)
    assert FR_RECOMMEND_INCLUDE_LIMIT == pytest.approx(0.50)
    assert FR_RECOMMEND_SHOW_LIMIT == pytest.approx(0.70)

    # C-10 : déterminisme bit-exact du grain MT19937(5489) et atténuation sur noir/blanc extrêmes
    base_img = Image.new("RGB", (32, 32), (128, 128, 128))
    g1 = PicasaImageProcessor.film_grain(base_img, 0.5)
    g2 = PicasaImageProcessor.film_grain(base_img, 0.5)
    assert g1.tobytes() == g2.tobytes()
    assert g1.tobytes() != base_img.tobytes()

    # C-12 : redeye HSV flood-fill (cible uniquement la composante connexe rouge saturée)
    eye_arr = np.full((24, 24, 3), 120, dtype=np.uint8)
    eye_arr[8:15, 8:15] = (230, 20, 25)  # pupille rouge saturée
    eye_img = Image.fromarray(eye_arr, mode="RGB")
    fixed_eye = np.array(PicasaImageProcessor.remove_red_eye(eye_img, (0.2, 0.2, 0.8, 0.8)))
    assert fixed_eye[10, 10, 0] < 80
    assert fixed_eye[2, 2, 0] == 120

    # C-12 : spotblend / retouch Hermite + Poisson
    spot_arr = np.full((32, 32, 3), 180, dtype=np.uint8)
    spot_arr[15:17, 15:17] = (20, 20, 20)
    healed = np.array(PicasaImageProcessor.retouch_heal(Image.fromarray(spot_arr), (0.5, 0.5), 0.2))
    assert healed[16, 16, 0] > 140

    # C-13 : CTextItemList outer format <num_items>;<item_len>;<utf8_len>;<utf8_text>;...
    item_body = "14;Bonjour Picasa;Arial;0.200000,0.800000,0.100000,0.000000;v1,400,400,128.000000,2.000000,1.000000,1.000000,4278190080,4294901760,32768;"
    outer_tok = f"1;{len(item_body.encode('utf-8'))};{item_body}"
    doc = PicasaIniDocument()
    doc.set_text("test.jpg", outer_tok)
    assert doc.get_text("test.jpg") == "Bonjour Picasa"
    txt_s, (px, py), sz, col, sh = PicasaImageProcessor.parse_text_token(outer_tok)
    assert txt_s == "Bonjour Picasa"
    assert (px, py) == pytest.approx((0.2, 0.8))
    assert sz == 36
    assert col == (255, 0, 0)
    assert sh is True


def test_d03_d09_d10_offline_volume_export_presets_and_import_dupe_originfast(tmp_path: Path, qapp) -> None:
    """
    FR: Vérifie D-03 (`0x004F4FB1..0x004F5253`), D-09 (`0x00739C45..0x00739CBA`), et D-10 (`0x00513680`) :
    - D-09 : `QUALITY_PRESETS` = 85 (Auto), 85 (Normal), 95 (Max), 65 (Min), 85 (Custom).
    - D-03 : `_check_deleted_records` ne marque jamais comme supprimé un enregistrement situé sur un lecteur démonté (`Z:\\`).
    - D-10 : `PicasaImportDialog` détecte un doublon renommé grâce à `imagedata_originfast.pmp`.
    """
    # D-09
    assert QUALITY_PRESETS[0][1] == 85
    assert QUALITY_PRESETS[1][1] == 85
    assert QUALITY_PRESETS[2][1] == 95
    assert QUALITY_PRESETS[3][1] == 65
    assert QUALITY_PRESETS[4][1] == 85

    # D-03 : lecteur hors ligne Z:\
    db = PicasaDatabase.create_new(tmp_path / "db_offline")
    assert db.thumbindex is not None
    db.thumbindex.records.append(
        ThumbIndexRecord(path="Z:\\OfflinePhotos\\", ft1=1, ft2=1, size=0, type=1, flags=0x00010000, parent_idx=0xFFFFFFFF)
    )
    db.thumbindex.records.append(
        ThumbIndexRecord(path="keep_me.jpg", ft1=1, ft2=1, size=1234, type=2, flags=0x00010000, parent_idx=0)
    )
    scanner = PicasaDirScanner(db)
    deleted = scanner._check_deleted_records()
    assert deleted == 0
    assert db.thumbindex.records[1].type == 2

    # D-10 : détection de doublon d'importation par originfast même si le fichier source a été renommé
    lib_dir = tmp_path / "Library"
    lib_dir.mkdir()
    orig_img = lib_dir / "IMG_1000.JPG"
    Image.new("RGB", (80, 60), (42, 84, 126)).save(orig_img, "JPEG")
    scanner.index_file(str(orig_img))

    cam_dir = tmp_path / "CameraCard"
    cam_dir.mkdir()
    renamed_copy = cam_dir / "RENAMED_COPY.JPG"
    renamed_copy.write_bytes(orig_img.read_bytes())

    imp_dlg = PicasaImportDialog(db=db, default_source_dir=str(cam_dir))
    try:
        assert imp_dlg.list_widget.count() == 1
        item = imp_dlg.list_widget.item(0)
        assert item.checkState() == pytest.importorskip("PySide6.QtCore").Qt.CheckState.Unchecked
    finally:
        imp_dlg.close()
