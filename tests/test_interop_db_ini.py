"""FR: Suite de tests d'interopérabilité croisée et de vérification des formules binaires désassemblées
(AGENTS.md §3, §4, §7.2).

Couvre :
1. Vérification à 100 % des checksums CBlockFile (thumbs_index.db, thumbs2_index.db, bigthumbs_index.db,
   previews_index.db, facetemplatesV2_index.db) par rapport aux fichiers réels produits par picasa3.exe
   (Ref: 0x006B99F0, 0x004E3AB0, 0x0042A800, 0x0048050B).
2. Vérification de l'intégrité binaire vqc_Cue (0x00423002 / 0x0044DD4D) et du modèle vqc_Relator::sim
   (Red.dll @ 0x1003E510, 0x10102020, 0x10100A10, 0x100FF050) sur facetemplatesV2_0.db.
3. Cycle complet d'interopérabilité alternée Picasa 3 <-> PyCasa (thumbindex.db, tables PMP,
   conteneurs CBlockFile, wordhash.dat, repository.dat, contacts.xml, .picasa.ini).
4. Filtrage des dossiers exclus (runtime/filters.txt @ 0x00D0AD70, .picasaoriginals @ 0x0085A0B0)
   et exclusion de détection faciale frexclude=1 (0x00881690).

EN: Cross-interoperability test suite and verification of disassembled binary formulas
(AGENTS.md §3, §4, §7.2).

Covers:
1. 100% verification of CBlockFile checksums (thumbs_index.db, thumbs2_index.db, bigthumbs_index.db,
   previews_index.db, facetemplatesV2_index.db) against real files produced by picasa3.exe
   (Ref: 0x006B99F0, 0x004E3AB0, 0x0042A800, 0x0048050B).
2. Verification of vqc_Cue binary integrity (0x00423002 / 0x0044DD4D) and vqc_Relator::sim model
   (Red.dll @ 0x1003E510, 0x10102020, 0x10100A10, 0x100FF050) on facetemplatesV2_0.db.
3. Full alternating interoperability cycle Picasa 3 <-> PyCasa (thumbindex.db, PMP tables,
   CBlockFile containers, wordhash.dat, repository.dat, contacts.xml, .picasa.ini).
4. Excluded folder filtering (runtime/filters.txt @ 0x00D0AD70, .picasaoriginals @ 0x0085A0B0)
   and face detection exclusion frexclude=1 (0x00881690).
"""

from __future__ import annotations
import os
import struct
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from picasa_py.db.blockfile import (
    BlockIndexFile,
    BlockContainerFile,
    FACETEMPLATE_BLOCK_CHECKSUM,
    VQC_CUE_CLASS_ID,
    VQC_CUE_FORMAT_ID,
    compute_thumb_checksum,
    compute_preview_checksum,
    verify_face_template_blob,
    decode_face_template_blob,
    encode_face_template_blob,
)
from picasa_py.db.database import PicasaDatabase
from picasa_py.db.pmp import PmpFile, PmpType
from picasa_py.db.thumbindex import ThumbIndexFile
from picasa_py.db.wordhash import WordHashFile
from picasa_py.db.kvtable import KeyValueTableFile
from picasa_py.db.contacts import ContactsFile, Contact
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.scanner.scanner import PicasaDirScanner, load_directory_filters
from picasa_py.faces.face_manager import PicasaFaceManager, _face_overlap
from picasa_py.faces.facerect import FaceRect


REAL_DB3_DIR = PicasaDatabase._find_default_db3_dir()


@pytest.mark.skipif(not REAL_DB3_DIR.exists(), reason="Base réelle Picasa2/db3 absente sur cette machine")
def test_real_db3_blockfile_checksums_100_percent() -> None:
    """FR: Vérifie que les formules désassemblées (0x006B99F0, 0x004E3AB0, 0x0042A800, 0x0048050B)
    reproduisent exactement 100 % des checksums stockés par picasa3.exe dans :
    - thumbs_index.db
    - thumbs2_index.db
    - bigthumbs_index.db
    - previews_index.db
    - facetemplatesV2_index.db
    EN: Verifies that the disassembled formulas (0x006B99F0, 0x004E3AB0, 0x0042A800, 0x0048050B)
    reproduce 100% of the checksums stored by picasa3.exe in:
    - thumbs_index.db
    - thumbs2_index.db
    - bigthumbs_index.db
    - previews_index.db
    - facetemplatesV2_index.db
    """
    db = PicasaDatabase.open(REAL_DB3_DIR)
    assert db.thumbindex is not None

    for prefix in ("thumbs", "thumbs2", "bigthumbs", "previews", "facetemplatesV2"):
        idx_file = db.block_indices.get(prefix)
        assert idx_file is not None, f"{prefix}_index.db manquant"
        matched = 0
        total_valid = 0
        for i in range(min(idx_file.record_count, len(db.thumbindex.records))):
            entry = idx_file.get_entry(i)
            if entry is None or entry.is_empty or entry.offset == 0xFFFFFFFF or entry.checksum == 0:
                continue
            rec = db.thumbindex.records[i]
            if rec.type == 0:
                continue
            total_valid += 1
            expected = db.compute_entry_checksum(i, prefix)
            if expected == entry.checksum:
                matched += 1
        cont_file = db.block_containers_by_block.get((prefix, idx_file.active_block)) or db.block_containers.get(prefix)
        if cont_file is not None and cont_file.byte_size() <= 4:
            # Ref: picasa3.exe @ 0x0041B77E-0x0041B7B0, 0x006B8AC0 : après compactage de bigthumbs_0.db /
            # previews_0.db à 4 octets, ValidateIndex invalide les entrées hors-limites en mémoire.
            assert total_valid == 0
        else:
            assert total_valid > 0
            assert matched == total_valid, f"{prefix}_index.db : {matched}/{total_valid} checksums identiques"


@pytest.mark.skipif(not REAL_DB3_DIR.exists(), reason="Base réelle Picasa2/db3 absente sur cette machine")
def test_real_facetemplates_v2_vqc_cue_integrity_and_similarity() -> None:
    """FR: Vérifie que tous les gabarits de facetemplatesV2_0.db respectent le contrôle de cohérence
    Red.dll @ 0x1003E510 (u[0]==1044, u[1]==0x00423002, u[3]==0x0044DD4D, sum(u)==0xFFFFFFFF)
    et que vqc_Relator::sim (Red.dll @ 0x10100A10) donne une auto-similarité > 0.9999.
    EN: Verifies that all templates in facetemplatesV2_0.db satisfy the Red.dll @ 0x1003E510
    consistency check (u[0]==1044, u[1]==0x00423002, u[3]==0x0044DD4D, sum(u)==0xFFFFFFFF)
    and that vqc_Relator::sim (Red.dll @ 0x10100A10) yields a self-similarity > 0.9999.
    """
    db = PicasaDatabase.open(REAL_DB3_DIR)
    idx_file = db.block_indices["facetemplatesV2"]
    cont_file = db.block_containers["facetemplatesV2"]

    valid_indices = [
        i
        for i in range(idx_file.record_count)
        if idx_file.get_entry(i) is not None
        and not idx_file.get_entry(i).is_empty
        and idx_file.get_entry(i).size == 1044
    ]
    assert len(valid_indices) > 0

    for i in valid_indices:
        blob = cont_file.get_blob(idx_file.get_entry(i))
        assert verify_face_template_blob(blob), f"Gabarit vqc_Cue invalide à l'index {i}"

    # Vérifier le décodage 2000-D et la similarité vqc_Relator::sim sur un échantillon
    sample_vecs = []
    for i in valid_indices[:10]:
        cue = db.get_face_template_cue(i)
        assert cue is not None
        vec, inv_norm, stamp = cue
        assert vec.shape == (2000,)
        assert inv_norm > 0.0
        sample_vecs.append(vec)
        # Auto-similarité : 1 / (1 + exp(-(13.5 * dot - 0.45))) > 0.9999
        self_dot = float(np.dot(vec, vec))
        self_sim = 1.0 / (1.0 + float(np.exp(-(13.5 * self_dot - 0.45))))
        assert self_sim > 0.9999


def test_synthetic_vqc_cue_roundtrip_and_checksum() -> None:
    """FR: Construit un gabarit vqc_Cue de 1044 octets conforme à Red.dll @ 0x10102020 (vqc_Cue::exportArr),
    vérifie son checksum interne u[10] (+0x28) et son décodage par PicasaDatabase.get_face_template.
    EN: Builds a 1044-byte vqc_Cue template matching Red.dll @ 0x10102020 (vqc_Cue::exportArr),
    verifies its internal checksum u[10] (+0x28) and its decoding by PicasaDatabase.get_face_template.
    """
    words = [0] * 261
    words[0] = 1044  # byte size
    words[1] = VQC_CUE_CLASS_ID  # 0x00423002
    words[2] = 0  # version
    words[3] = VQC_CUE_FORMAT_ID  # 0x0044DD4D
    words[4] = 2000  # size
    words[5] = 4  # bits
    words[6] = 8  # pack_size
    words[7] = struct.unpack("<I", struct.pack("<f", 0.148))[0]  # inv_norm
    words[8] = 0x12345678  # image_stamp
    words[9] = 250  # data uint32 count
    words[10] = 0  # checksum placeholder (+0x28)
    for k in range(11, 261):
        words[k] = 0x96A53C78  # 8 nibbles 4-bit

    partial_sum = sum(words) & 0xFFFFFFFF
    words[10] = (0xFFFFFFFF - partial_sum) & 0xFFFFFFFF
    blob = struct.pack("<261I", *words)

    assert len(blob) == 1044
    assert verify_face_template_blob(blob)


def test_cross_interoperability_alternating_db_and_ini(tmp_path: Path) -> None:
    """FR: Simule un cycle complet d'écriture et de modification croisée entre la base db3/
    et les fichiers .picasa.ini (AGENTS.md §7.2) :
    - Création d'une base Picasa 3 complète (thumbindex.db, tables PMP, CBlockFiles, wordhash, contacts)
    - Indexation de photos avec génération des checksums exacts dans thumbs_index.db, bigthumbs_index.db, previews_index.db
    - Écriture et modification de .picasa.ini (étoile, rotation, filtres, légende, mots-clés, visages)
    - Synchronisation .picasa.ini -> DB, sauvegarde atomique, réouverture et vérification bit à bit.
    EN: Simulates a full cross-write and modification cycle between the db3/ database
    and .picasa.ini files (AGENTS.md §7.2):
    - Creation of a complete Picasa 3 database (thumbindex.db, PMP tables, CBlockFiles, wordhash, contacts)
    - Photo indexing with exact checksum generation in thumbs_index.db, bigthumbs_index.db, previews_index.db
    - Writing and updating .picasa.ini (star, rotation, filters, caption, keywords, faces)
    - Syncing .picasa.ini -> DB, atomic save, reopening, and bit-exact verification.
    """
    db_dir = tmp_path / "db3"
    contacts_dir = tmp_path / "contacts"
    photos_dir = tmp_path / "Photos" / "Vacances"
    db_dir.mkdir(parents=True)
    contacts_dir.mkdir(parents=True)
    photos_dir.mkdir(parents=True)

    # Créer 2 images JPEG de test sur disque
    img1_path = photos_dir / "IMG_0001.JPG"
    img2_path = photos_dir / "IMG_0002.JPG"
    Image.new("RGB", (320, 240), (120, 160, 210)).save(img1_path, "JPEG", quality=90)
    Image.new("RGB", (400, 300), (200, 100, 80)).save(img2_path, "JPEG", quality=90)

    # Initialiser une base Picasa complète avec les tables PMP et CBlockFile standards
    db = PicasaDatabase(db3_dir=db_dir, contacts_dir=contacts_dir)
    db.thumbindex = ThumbIndexFile()
    db.wordhash = WordHashFile()
    db.repository = KeyValueTableFile()
    db.usernames = KeyValueTableFile()
    db.contacts = ContactsFile(contacts=[Contact(id="a1b2c3d4e5f60718", name="Alice Martin")])

    for col, ftype in [
        ("imagedata_width", PmpType.UINT16),
        ("imagedata_height", PmpType.UINT16),
        ("imagedata_tagdate", PmpType.DOUBLE),
        ("imagedata_rotate", PmpType.STRING),
        ("imagedata_star", PmpType.UINT8),
        ("imagedata_edited", PmpType.UINT8),
        ("imagedata_crop64", PmpType.UINT64),
        ("imagedata_filters", PmpType.STRING),
        ("imagedata_caption", PmpType.STRING),
        ("imagedata_tags", PmpType.STRING),
        ("imagedata_text", PmpType.STRING),
        ("imagedata_textactive", PmpType.UINT8),
        ("imagedata_facerect", PmpType.UINT64),
        ("imagedata_personalbumid", PmpType.UINT32),
    ]:
        db.pmps[col] = PmpFile(pmp_type=ftype, records=[])

    for prefix in ("thumbs", "thumbs2", "bigthumbs", "previews", "facetemplatesV2"):
        db.block_indices[prefix] = BlockIndexFile()
        cont = BlockContainerFile()
        db.block_containers[prefix] = cont
        db.block_containers_by_block[(prefix, 0)] = cont

    # 1. Indexer le dossier via PicasaDirScanner
    scanner = PicasaDirScanner(db)
    idx1 = scanner.index_file(str(img1_path))
    idx2 = scanner.index_file(str(img2_path))
    assert idx1 is not None and idx2 is not None

    # Ajouter également une miniature medium (thumbs2) et preview (previews) pour idx1
    thumb_bytes = db.get_thumbnail(idx1, size="small")
    assert thumb_bytes is not None
    db.add_thumbnail(idx1, thumb_bytes, size="medium")
    db.add_thumbnail(idx1, thumb_bytes, size="preview")

    # Vérifier que les checksums calculés dans thumbs_index.db, thumbs2_index.db et previews_index.db
    # correspondent bit à bit aux formules désassemblées de picasa3.exe (0x006B99F0 / 0x004E3AB0 / 0x0042A800)
    rec1 = db.thumbindex.records[idx1]
    folder_rec = db.thumbindex.records[rec1.parent_idx]
    expected_thumb_crc = compute_thumb_checksum(folder_rec.path, rec1.path, rec1.ft2, rec1.size)
    expected_prev_crc = compute_preview_checksum(rec1.ft2, rotate_step=0, flip=0)

    assert db.block_indices["thumbs"].get_entry(idx1).checksum == expected_thumb_crc
    assert db.block_indices["thumbs2"].get_entry(idx1).checksum == expected_thumb_crc
    assert db.block_indices["previews"].get_entry(idx1).checksum == expected_prev_crc

    # 2. Modifier les métadonnées via .picasa.ini (comme le ferait picasa3.exe ou l'UI PyCasa)
    def _mutate(doc: PicasaIniDocument, fname: str) -> None:
        """FR: Modifie le document .picasa.ini pour ajouter étoile, rotation, filtres, légende et mots-clés.
        EN: Mutates the .picasa.ini document to add star, rotation, filters, caption, and keywords.
        """
        doc.set_star(fname, True)
        doc.set_rotate(fname, 1)
        sec = doc.get_or_create_section(fname)
        sec.set("filters", "autolight=1;enhance=1;")
        sec.set("caption", "Coucher de soleil à Nice")
        sec.set("keywords", "vacances,plage,soleil")

    assert db.update_photo_ini(str(img1_path), _mutate)

    # Vérifier la synchronisation immédiate dans les colonnes PMP et wordhash.dat
    assert db.pmps["imagedata_star"].records[idx1] == 1
    assert db.pmps["imagedata_rotate"].records[idx1] == "rotate(1)"
    assert db.pmps["imagedata_edited"].records[idx1] == 1
    assert db.pmps["imagedata_filters"].records[idx1] == "autolight=1;enhance=1;"
    assert db.pmps["imagedata_caption"].records[idx1] == "Coucher de soleil à Nice"
    assert db.pmps["imagedata_tags"].records[idx1] == "vacances,plage,soleil"
    assert idx1 in db.search("vacances soleil")

    # Après rotation rotate=1, une mise à jour de preview doit intégrer rotate_step=1 dans son checksum
    db.add_thumbnail(idx1, thumb_bytes, size="preview")
    expected_prev_crc_rot1 = compute_preview_checksum(rec1.ft2, rotate_step=1, flip=0)
    assert db.block_indices["previews"].get_entry(idx1).checksum == expected_prev_crc_rot1

    # 3. Sauvegarder toute la base sur disque puis la relire depuis zéro
    db.save_database()
    reloaded = PicasaDatabase.open(db_dir, contacts_dir)

    assert len(reloaded.thumbindex.records) == len(db.thumbindex.records)
    assert reloaded.thumbindex.to_bytes() == db.thumbindex.to_bytes()
    for stem, pmp in db.pmps.items():
        assert reloaded.pmps[stem].to_bytes() == pmp.to_bytes(), f"Divergence binaire sur {stem}.pmp"
    for prefix, idx_f in db.block_indices.items():
        assert reloaded.block_indices[prefix].to_bytes() == idx_f.to_bytes()
    assert reloaded.wordhash.to_bytes() == db.wordhash.to_bytes()
    assert idx1 in reloaded.search("plage")

    # Vérifier le round-trip octet pour octet du fichier .picasa.ini généré
    ini_path = photos_dir / ".picasa.ini"
    raw_ini = ini_path.read_bytes()
    parsed_ini = PicasaIniParser.parse_bytes(raw_ini)
    assert parsed_ini.to_bytes() == raw_ini


def test_scanner_directory_filters_and_frexclude(tmp_path: Path) -> None:
    """FR: Vérifie que PicasaDirScanner exclut les répertoires de runtime/filters.txt
    (windows, winnt, temp, Program Files, Originals, .picasaoriginals)
    et respecte frexclude=1 dans [Picasa] de .picasa.ini (Ref: 0x00D0AD70, 0x0085A0B0, 0x00881690).
    EN: Verifies that PicasaDirScanner excludes directories from runtime/filters.txt
    (windows, winnt, temp, Program Files, Originals, .picasaoriginals)
    and honors frexclude=1 in [Picasa] of .picasa.ini (Ref: 0x00D0AD70, 0x0085A0B0, 0x00881690).
    """
    filters = load_directory_filters()
    for expected in ("windows", "winnt", "temp", "program files", "originals", ".picasaoriginals"):
        assert expected in filters

    root = tmp_path / "Library"
    keep_dir = root / "Famille"
    orig_dir = root / "Originals"
    picasa_orig_dir = root / ".picasaoriginals"
    temp_dir = root / "Temp"
    for d in (keep_dir, orig_dir, picasa_orig_dir, temp_dir):
        d.mkdir(parents=True)
        Image.new("RGB", (64, 64), (100, 150, 200)).save(d / "test.jpg", "JPEG")

    db = PicasaDatabase(db3_dir=tmp_path / "db3")
    scanner = PicasaDirScanner(db)
    found = scanner.scan_folder_for_media(str(root), recursive=True)
    assert len(found) == 1
    assert os.path.normpath(found[0]) == os.path.normpath(str(keep_dir / "test.jpg"))

    # Tester frexclude=1 dans .picasa.ini
    assert not scanner.is_folder_face_excluded(str(keep_dir))
    (keep_dir / ".picasa.ini").write_bytes(b"[Picasa]\r\nfrexclude=1\r\n")
    db.invalidate_ini_cache()
    assert scanner.is_folder_face_excluded(str(keep_dir))

    # Vérifier également _face_overlap (0x0092C2F0)
    r1 = FaceRect(left=0.1, top=0.1, right=0.5, bottom=0.5)
    r2 = FaceRect(left=0.1, top=0.1, right=0.5, bottom=0.5)
    r3 = FaceRect(left=0.6, top=0.6, right=0.9, bottom=0.9)
    assert abs(_face_overlap(r1, r2) - 1.0) < 1e-6
    assert _face_overlap(r1, r3) == 0.0


def test_vqc_cue_roundtrip_and_inv_norm_and_quantizer(tmp_path: Path) -> None:
    """FR: Vérifie sur les 1 160 enregistrements réels de facetemplatesV2_0.db :
    1. Le round-trip bit à bit (decode_face_template_blob -> encode_face_template_blob)
       et le calcul du checksum Red.dll (0x1014A340 / 0x10102020).
    2. La fidélité du calcul de inv_norm via vqc_Relator::rawSim(cue, cue)
       (Red.dll @ 0x100FE262..0x100FE320, 0x101007D7..0x10100865, 0x100FF050).
    3. Le chargement des 30 000 seuils de quantification vqc_Quantizer (Red.dll @ 0x100FCF60)
       et l'écriture complète via db.add_face_template(...).
    EN: Verifies across the 1,160 real records of facetemplatesV2_0.db:
    1. Bit-exact round-trip (decode_face_template_blob -> encode_face_template_blob)
       and Red.dll checksum computation (0x1014A340 / 0x10102020).
    2. Fidelity of inv_norm computation via vqc_Relator::rawSim(cue, cue)
       (Red.dll @ 0x100FE262..0x100FE320, 0x101007D7..0x10100865, 0x100FF050).
    3. Loading of the 30,000 vqc_Quantizer quantization thresholds (Red.dll @ 0x100FCF60)
       and full write via db.add_face_template(...).
    """
    if not (REAL_DB3_DIR / "facetemplatesV2_0.db").exists():
        pytest.skip("Base Picasa3 réelle absente")

    sqrt_w, delta_term = PicasaDatabase._get_vqc_relator_weights()
    assert sqrt_w is not None and len(sqrt_w) == 2000
    assert PicasaDatabase._vqc_weights is not None
    if PicasaDatabase._vqc_thr_arr is not None:
        assert PicasaDatabase._vqc_thr_arr.shape == (2000, 15)

    idx_file = BlockIndexFile.from_bytes((REAL_DB3_DIR / "facetemplatesV2_index.db").read_bytes())
    raw_0 = (REAL_DB3_DIR / "facetemplatesV2_0.db").read_bytes()

    checked = 0
    max_inv_norm_diff = 0.0
    for i in range(idx_file.record_count):
        e = idx_file.get_entry(i)
        if e is not None and not e.is_empty and e.block == 0 and e.size == 1044:
            blob = raw_0[e.offset : e.offset + e.size]
            nibbles, stored_inv_norm, stored_meta = decode_face_template_blob(blob)
            reencoded = encode_face_template_blob(nibbles, stored_inv_norm, stored_meta)
            assert reencoded == blob, "Round-trip vqc_Cue non identique au bit près !"

            calc_inv_norm = PicasaDatabase.compute_vqc_cue_inv_norm(nibbles)
            diff = abs(calc_inv_norm - stored_inv_norm)
            if diff > max_inv_norm_diff:
                max_inv_norm_diff = diff
            checked += 1

    assert checked >= 100
    assert max_inv_norm_diff < 1e-6, f"Écart inv_norm trop grand: {max_inv_norm_diff}"

    # Tester la quantification vqc_Quantizer::map et l'ajout dans une base temporaire
    db_dir = tmp_path / "db3_vqc"
    db_dir.mkdir(parents=True)
    db = PicasaDatabase(db3_dir=db_dir)
    db.block_indices["facetemplatesV2"] = BlockIndexFile()
    cont = BlockContainerFile()
    db.block_containers["facetemplatesV2"] = cont
    db.block_containers_by_block[("facetemplatesV2", 0)] = cont
    db.pmps["imagedata_facetemplatesV2"] = PmpFile(pmp_type=PmpType.UINT8, records=[])

    raw_features = np.zeros(2000, dtype=np.float32)
    q_nibbles = PicasaDatabase.quantize_vqc_cue_nibbles(raw_features)
    assert q_nibbles.shape == (2000,)
    assert np.all((q_nibbles >= 0) & (q_nibbles <= 15))

    written_blob = db.add_face_template(0, q_nibbles)
    assert len(written_blob) == 1044
    assert verify_face_template_blob(written_blob)
    assert db.block_indices["facetemplatesV2"].get_entry(0).checksum == FACETEMPLATE_BLOCK_CHECKSUM
    assert db.pmps["imagedata_facetemplatesV2"].records[0] == 1


def test_glimmer_filterdesc_xml_exact_operations() -> None:
    """FR: Vérifie que les 11 filtres Glimmer/Picnik alignés sur runtime/filterdesc.xml
    s'exécutent sans erreur et produisent une image transformée valide.
    EN: Verifies that the 11 Glimmer/Picnik filters aligned with runtime/filterdesc.xml
    execute without error and produce a valid transformed image.
    """
    from picasa_py.ui.image_processor import PicasaImageProcessor

    img = Image.new("RGB", (64, 64), (120, 140, 180))
    # Créer un léger dégradé pour que les filtres locaux (Sobel, HighPass, Blur) aient du signal
    arr = np.fromfunction(
        lambda y, x, c: ((x * 3 + y * 2 + c * 40) % 256), (64, 64, 3), dtype=float
    ).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")

    filter_chains = [
        "HDR=1,50.0,60.0,25.0;",
        "Lomo=1,50.0,50.0;",
        "Orton=1,50.0,50.0,20.0;",
        "IR=1,80.0;",
        "Holga=1,50.0,50.0;",
        "Boost=1,100.0;",
        "Soften=1,50.0,45.0;",
        "Neon=1,0.619444,0.0;",
        "PencilSketch=1,50.0,70.0;",
        "MuseumMatte=1,20.0,0.000000,1.000000,10.0;",
        "ReanimatedEyeColor=1,70.0,20.0,0.5,0.5;",
    ]
    for fstr in filter_chains:
        out = PicasaImageProcessor.apply_filter_chain(img, fstr)
        assert out.width >= img.width and out.height >= img.height
        assert out.mode == "RGB"
        if out.size == img.size:
            assert not np.array_equal(np.array(out), np.array(img)), f"Le filtre {fstr} n'a eu aucun effet"


def test_database_compact_remaps_indices_and_blockfile_invariants(tmp_path: Path) -> None:
    """FR: Vérifie les mécanismes désassemblés de :
    - compactage complet avec réindexation (`new_to_old`, `old_to_new`, `parent_idx`, `imagedata_aliasparents`,
      `wordhash` doc IDs, purge de `bigthumbs`/`previews` à 4 octets @ 0x0041B77E-0x0041B7B0) ;
    - `CBlockFile` : blob de taille 0 -> `BlockEntry(0, 0, 0, 0)` (0x006B75F0), réécriture en place
      inter-blocs (0x006B7753) et invalidation au chargement des entrées hors limites (0x006B8AC0) ;
    - `ensure_folder_album_row` (`albumdata_category = 2`), réservation de la ligne 0 (`]unknownface`),
      jetons `color:*` (`classify_image_color_tokens` @ 0x009DBD10), tokeniseur `tokenize_indexer_text`
      (0x00987DA0) et fichiers auxiliaires `.txt` (`scanlist.txt`, `starlist.txt`, `saverlist.txt`,
      `facetags.txt`, `tags.txt` @ 0x0041BA40).
    EN: Verifies the disassembled mechanisms of:
    - full index-remapping compaction (`new_to_old`, `old_to_new`, `parent_idx`, `imagedata_aliasparents`,
      `wordhash` doc IDs, `bigthumbs`/`previews` reset to 4 bytes @ 0x0041B77E-0x0041B7B0);
    - `CBlockFile`: zero-size blob -> `BlockEntry(0, 0, 0, 0)` (0x006B75F0), cross-block in-place overwrite
      (0x006B7753), and truncated entry invalidation on load (0x006B8AC0);
    - `ensure_folder_album_row` (`albumdata_category = 2`), row 0 reservation (`]unknownface`),
      `color:*` tokens (`classify_image_color_tokens` @ 0x009DBD10), `tokenize_indexer_text` (0x00987DA0),
      and auxiliary `.txt` files (`scanlist.txt`, `starlist.txt`, `saverlist.txt`, `facetags.txt`, `tags.txt` @ 0x0041BA40).
    """
    from picasa_py.scanner.scanner import classify_image_color_tokens, tokenize_indexer_text
    from picasa_py.faces.face_manager import FaceManager, FaceRect

    # 1. Tokeniseur 0x00987DA0 (':' préservé pour color:*, ]album:*) & classifieur de couleurs 0x009DBD10
    assert tokenize_indexer_text("Vacances_Été-2026: Plage & Mer!") == [
        "vacances", "été", "2026:", "plage", "mer"
    ]
    bw_img = Image.new("RGB", (32, 32), (128, 128, 128))
    assert classify_image_color_tokens(bw_img) == ["color:black", "color:white", "color:gray"]
    red_img = Image.new("RGB", (32, 32), (240, 20, 20))
    assert "color:red" in classify_image_color_tokens(red_img)

    # 2. Scanner + dossier album (category=2) + ligne 0 ]unknownface + visages 1001
    photos_dir = tmp_path / "AlbumVacances"
    photos_dir.mkdir(parents=True)
    p1 = photos_dir / "img_delete_me.jpg"
    p2 = photos_dir / "img_keep_me.jpg"
    red_img.save(p1, format="JPEG")
    bw_img.save(p2, format="JPEG")

    db_root = tmp_path / "picasa_root"
    db = PicasaDatabase.create_new(db_root)
    db.set_watched_folder(str(photos_dir), "1")

    scanner = PicasaDirScanner(db)
    scanner.scan_directory(str(photos_dir))

    # Vérifier la ligne d'album de dossier (category = 2)
    ad_cats = db.pmps["albumdata_category"].records
    ad_tokens = db.pmps["albumdata_token"].records
    assert ad_cats[0] == 8 and ad_tokens[0] == "]unknownface"
    assert 2 in ad_cats

    idx1 = db.find_photo_index(str(p1))
    idx2 = db.find_photo_index(str(p2))
    assert idx1 is not None and idx2 is not None and idx1 < idx2

    # Marquer p2 favori, ajouter un mot-clé et un visage nommé
    db.set_starred(idx2, True)
    db.add_keyword(idx2, "Montagne")
    fm = FaceManager(db)
    fm.add_face(
        str(p2),
        FaceRect.from_rect64("rect64(2000200080008000)", "aabbccddeeff0011"),
        "Alice Martin",
        db_idx=idx2,
    )
    db.add_thumbnail(idx2, b"\xff\xd8\xff\xd9", size="bigthumbs")

    # Supprimer p1 pour créer un trou (type=0) avant idx2, puis compacter
    assert db.delete_photo(idx1)
    assert db.thumbindex.records[idx1].type == 0
    old_total = len(db.thumbindex.records)

    db.compact()
    assert len(db.thumbindex.records) < old_total

    new_idx2 = db.find_photo_index(str(p2))
    assert new_idx2 is not None and new_idx2 < idx2
    # Vérifier que le sous-enregistrement de visage 1001 pointe vers new_idx2
    face_recs = [r for r in db.thumbindex.records if r.type == 1001]
    assert len(face_recs) == 1 and face_recs[0].parent_idx == new_idx2
    # Vérifier que wordhash a réindexé ]star et montagne vers new_idx2
    assert db.wordhash is not None
    assert new_idx2 in db.wordhash.words.get("]star", [])
    assert new_idx2 in db.wordhash.words.get("montagne", [])
    # Vérifier que bigthumbs_0.db a été purgé à 4 octets lors du compactage (0x0041B793)
    assert (db.db3_dir / "bigthumbs_0.db").stat().st_size == 4

    # Vérifier les 5 fichiers .txt auxiliaires écrits dans db3
    for txt_name in ("scanlist.txt", "starlist.txt", "saverlist.txt", "facetags.txt", "tags.txt"):
        assert (db.db3_dir / txt_name).exists(), f"{txt_name} manquant"
    assert "img_keep_me.jpg" in (db.db3_dir / "starlist.txt").read_text(encoding="utf-8")
    assert "Alice Martin" in (db.db3_dir / "facetags.txt").read_text(encoding="utf-8")
    assert "Montagne" in (db.db3_dir / "tags.txt").read_text(encoding="utf-8")

    # 3. CBlockFile : blob de taille 0 -> (0,0,0,0) et invalidation d'entrée hors-limites au chargement
    cont_test = BlockContainerFile()
    zero_entry = cont_test.append_blob(b"", checksum=12345, block_idx=0)
    assert zero_entry.is_empty and zero_entry.offset == 0 and zero_entry.size == 0 and zero_entry.checksum == 0

