import os
import re

def create_fixtures():
    src_dir = os.path.expanduser(r"~\Pictures")
    out_dir = r"tests\fixtures\ini"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Troyes album
    f1 = os.path.join(src_dir, "6H de Troyes", ".picasa.ini")
    if os.path.exists(f1):
        with open(f1, "rb") as f:
            content = f.read()
        with open(os.path.join(out_dir, "fixture_album_troyes.ini"), "wb") as f:
            f.write(content)
        print("Created fixture_album_troyes.ini")

    # 2. Marriage album (with crop, multi albums, albums section)
    f2 = os.path.join(src_dir, "Image pour le mariage", ".picasa.ini")
    if os.path.exists(f2):
        with open(f2, "rb") as f:
            content = f.read()
        with open(os.path.join(out_dir, "fixture_crop_and_albums.ini"), "wb") as f:
            f.write(content)
        print("Created fixture_crop_and_albums.ini")

    # 3. Anonymized contacts and faces fixture
    f3 = os.path.join(src_dir, "Max et Egone", ".picasa.ini")
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
