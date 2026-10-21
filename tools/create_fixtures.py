"""FR: Utilitaire de création de fixtures .picasa.ini anonymisées à partir d'un dossier source.
EN: Utility for creating anonymized .picasa.ini fixtures from a source directory.

Ref: picasa3.exe @ 0x0085AC90 (Contacts2 & .picasa.ini serialization)
Ref: AGENTS.md §7 & §9.9 (Fixtures de référence anonymisées)
"""

from __future__ import annotations

import os
import re


def create_fixtures(src_dir: str | None = None, out_dir: str = r"tests\fixtures\ini") -> None:
    """FR: Crée les fixtures .picasa.ini anonymisées dans le dossier de sortie spécifié.
    EN: Creates anonymized .picasa.ini fixtures in the specified output directory.
    """
    if src_dir is None:
        src_dir = os.environ.get("PYCASA_FIXTURE_SRC_DIR", os.path.expanduser(r"~\Pictures"))
    os.makedirs(out_dir, exist_ok=True)

    album1_dir = os.environ.get("PYCASA_FIXTURE_ALBUM1", "SampleAlbum1")
    album2_dir = os.environ.get("PYCASA_FIXTURE_ALBUM2", "SampleAlbum2")
    album3_dir = os.environ.get("PYCASA_FIXTURE_ALBUM3", "SampleAlbum3")

    # 1. Sample album 1
    f1 = os.path.join(src_dir, album1_dir, ".picasa.ini")
    if os.path.exists(f1):
        with open(f1, "rb") as f:
            content = f.read()
        with open(os.path.join(out_dir, "fixture_album_troyes.ini"), "wb") as f:
            f.write(content)
        print("Created fixture_album_troyes.ini")

    # 2. Sample album 2 (with crop, multi albums, albums section)
    f2 = os.path.join(src_dir, album2_dir, ".picasa.ini")
    if os.path.exists(f2):
        with open(f2, "rb") as f:
            content = f.read()
        with open(os.path.join(out_dir, "fixture_crop_and_albums.ini"), "wb") as f:
            f.write(content)
        print("Created fixture_crop_and_albums.ini")

    # 3. Anonymized contacts and faces fixture
    f3 = os.path.join(src_dir, album3_dir, ".picasa.ini")
    if os.path.exists(f3):
        with open(f3, "rb") as f:
            content = f.read()
        # Anonymize names in Contacts2
        content = re.sub(rb"=[^;\r\n]+;;", b"=Contact_Person;;", content)
        with open(os.path.join(out_dir, "fixture_faces_contacts.ini"), "wb") as f:
            f.write(content)
        print("Created fixture_faces_contacts.ini")

    # 4. Root pictures ini (larger, multi-faces)
    f4 = os.path.join(src_dir, ".picasa.ini")
    if os.path.exists(f4):
        with open(f4, "rb") as f:
            content = f.read()
        content = re.sub(rb"=[^;\r\n]+;;", b"=Contact_Person;;", content)
        with open(os.path.join(out_dir, "fixture_large_faces.ini"), "wb") as f:
            f.write(content)
        print("Created fixture_large_faces.ini")


if __name__ == "__main__":
    create_fixtures()
