"""
FR: Tests de validation aller-retour (round-trip) octet pour octet des fichiers .picasa.ini.
Conformément à AGENTS.md §7:
"1. Round-trip : lecture puis réécriture identique au bit près sur tous les fichiers de référence.
Tout écart (même un octet) est un bug."
EN: Byte-for-byte round-trip validation tests for .picasa.ini files.
In accordance with AGENTS.md §7:
"1. Round-trip: reading followed by rewriting must be bit-for-bit identical across all reference files.
Any discrepancy (even a single byte) is a bug."
"""

import os
import glob
import pytest
from picasa_py.ini import PicasaIniParser, PicasaIniWriter, FaceItem, CropRect

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "ini")


def get_fixture_files():
    """
    FR: Retourne la liste des fichiers .ini de référence situés dans tests/fixtures/ini.
    EN: Return the list of reference .ini fixture files located in tests/fixtures/ini.
    """
    files = glob.glob(os.path.join(FIXTURES_DIR, "*.ini"))
    assert len(files) > 0, "Aucun fichier fixture trouvé dans tests/fixtures/ini"
    return files


@pytest.mark.parametrize("filepath", get_fixture_files())
def test_fixtures_bit_exact_roundtrip(filepath):
    """
    FR: Vérifie qu'un fichier de test de référence relu puis réécrit
    est absolument identique au bit près à l'original.
    EN: Verify that a reference test file read and rewritten is bit-for-bit identical to the original.
    """
    with open(filepath, "rb") as f:
        original_bytes = f.read()

    doc = PicasaIniParser.parse_bytes(original_bytes)
    serialized_bytes = PicasaIniWriter.to_bytes(doc)

    assert serialized_bytes == original_bytes, (
        f"Différence binaire détectée sur {os.path.basename(filepath)} !\n"
        f"Taille originale : {len(original_bytes)} octets, générée : {len(serialized_bytes)} octets."
    )


def test_real_system_inis_roundtrip():
    """
    FR: Teste tous les fichiers .picasa.ini réels découverts dans Pictures/
    (test en lecture seule, sans modification des originaux).
    EN: Test all real .picasa.ini files discovered in Pictures/
    (read-only test without modifying the originals).
    """
    pictures_dir = os.path.expanduser(r"~\Pictures")
    ini_files = glob.glob(os.path.join(pictures_dir, "**", ".picasa.ini"), recursive=True)
    ini_files += glob.glob(os.path.join(pictures_dir, "**", "Picasa.ini"), recursive=True)

    tested_count = 0
    for path in ini_files:
        with open(path, "rb") as f:
            original_bytes = f.read()

        doc = PicasaIniParser.parse_bytes(original_bytes)
        serialized_bytes = PicasaIniWriter.to_bytes(doc)

        assert serialized_bytes == original_bytes, f"Échec roundtrip sur fichier réel: {path}"
        tested_count += 1

    print(f"\n{tested_count} fichiers réels validés avec succès au bit près.")


def test_high_level_model_access():
    """
    FR: Vérifie les accesseurs haut niveau sur un document.
    EN: Verify high-level model accessors on a parsed INI document.
    """
    sample = (
        b"[Contacts2]\r\n"
        b"aa28c3a53f34c2f8=User One;user1@test.com;\r\n"
        b"[IMG_0001.JPG]\r\n"
        b"faces=rect64(3a4400008b119b9d),aa28c3a53f34c2f8\r\n"
        b"crop=rect64(1d3a0e46ffffe75e)\r\n"
        b"star=yes\r\n"
        b"backuphash=12345\r\n"
    )

    doc = PicasaIniParser.parse_bytes(sample)

    # 1. Vérification des contacts
    contacts = doc.get_contacts()
    assert "aa28c3a53f34c2f8" in contacts
    assert contacts["aa28c3a53f34c2f8"].name == "User One"
    assert contacts["aa28c3a53f34c2f8"].email == "user1@test.com"

    # 2. Vérification des faces
    faces = doc.get_faces("IMG_0001.JPG")
    assert len(faces) == 1
    assert faces[0].rect64 == "3a4400008b119b9d"
    assert faces[0].contact_id == "aa28c3a53f34c2f8"

    # 3. Vérification du crop
    crop = doc.get_crop("IMG_0001.JPG")
    assert crop == "1d3a0e46ffffe75e"

    # 4. Vérification de l'étoile (star)
    assert doc.is_starred("IMG_0001.JPG") is True
    assert doc.is_starred("UNKNOWN.JPG") is False

    # 5. Case-insensitivity de la recherche (Ref: FUN_009be730)
    sec_lower = doc.get_section("img_0001.jpg")
    assert sec_lower is not None
    assert sec_lower.get("BACKUPHASH") == "12345"


def test_modifications_and_additions():
    """
    FR: Vérifie l'ajout de nouvelles sections et clés selon le format canonique de FUN_0068ac80.
    EN: Verify adding new sections and keys according to the canonical format of FUN_0068ac80.
    """
    doc = PicasaIniParser.parse_bytes(b"[Contacts2]\r\n")

    # Ajout d'une image avec star et faces
    doc.set_starred("new_image.jpg", True)
    doc.set_faces("new_image.jpg", [
        FaceItem(rect64="1111222233334444", contact_id="abcdef0123456789")
    ])
    doc.set_crop("new_image.jpg", "aaaa1111bbbb2222")

    out = doc.to_bytes()
    expected = (
        b"[Contacts2]\r\n"
        b"[new_image.jpg]\r\n"
        b"star=yes\r\n"
        b"faces=rect64(1111222233334444),abcdef0123456789\r\n"
        b"crop=rect64(aaaa1111bbbb2222)\r\n"
    )
    assert out == expected
