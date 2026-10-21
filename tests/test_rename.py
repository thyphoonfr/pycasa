"""
FR: Tests pour la boîte de dialogue de renommage par lot Picasa (RenameDialog / ExampleTransformer).
EN: Tests for Picasa Batch Rename Dialog (RenameDialog / ExampleTransformer).
"""

import os
from pathlib import Path
from PIL import Image

import pytest

from picasa_py.ui.rename_dialog import PicasaRenameDialog
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument


@pytest.fixture
def temp_rename_files(tmp_path):
    """
    FR: Crée un dossier temporaire contenant 2 images JPEG et un fichier .picasa.ini associé.
    EN: Create a temporary directory containing 2 JPEG images and an associated .picasa.ini file.
    """
    img_paths = []
    for i in range(2):
        p = tmp_path / f"orig_photo_{i}.jpg"
        img = Image.new("RGB", (800, 600), color=(100, 100, 100))
        img.save(p, "JPEG")
        img_paths.append(str(p))

    # Créer un .picasa.ini avec des métadonnées
    doc = PicasaIniDocument()
    doc.set_starred("orig_photo_0.jpg", True)
    doc.write_file(str(tmp_path / ".picasa.ini"))

    return {
        "dir": tmp_path,
        "img_paths": img_paths
    }


def test_rename_dialog_preview(qapp, temp_rename_files):
    """
    FR: Vérifie l'aperçu du nom de fichier généré dynamiquement (nom de base, date, résolution).
    EN: Verify the dynamically generated filename preview (base name, date, image resolution).
    """
    dlg = PicasaRenameDialog(temp_rename_files["img_paths"])
    assert "2" in dlg.lbl_count.text() and "fichier(s)" in dlg.lbl_count.text()

    # Saisie d'un nouveau nom de base
    dlg.edit_basename.setText("Corse")
    sample1 = dlg.lbl_sample.text()
    assert "Corse - 001.jpg" in sample1

    # Activer la date
    dlg.chk_date.setChecked(True)
    sample2 = dlg.lbl_sample.text()
    assert "Corse" in sample2
    assert "001.jpg" in sample2

    # Activer la résolution
    dlg.chk_size.setChecked(True)
    sample3 = dlg.lbl_sample.text()
    assert "800x600" in sample3


def test_rename_execution_and_ini_update(qapp, temp_rename_files):
    """
    FR: Vérifie que le renommage par lot renomme les fichiers sur disque et met à jour les sections dans .picasa.ini.
    EN: Verify that batch renaming renames the files on disk and updates the corresponding sections in .picasa.ini.
    """
    dlg = PicasaRenameDialog(temp_rename_files["img_paths"])
    dlg.edit_basename.setText("Voyage")
    dlg.chk_date.setChecked(False)
    dlg.chk_size.setChecked(False)

    pairs = dlg.execute_rename()
    assert len(pairs) == 2

    # Vérifier que les anciens fichiers n'existent plus
    for old_p, _ in pairs:
        assert not os.path.exists(old_p)

    # Vérifier que les nouveaux fichiers existent
    for _, new_p in pairs:
        assert os.path.exists(new_p)

    # Vérifier que le fichier .picasa.ini a été mis à jour avec le nouveau nom de fichier
    ini_path = temp_rename_files["dir"] / ".picasa.ini"
    assert ini_path.exists()
    doc = PicasaIniParser.parse_file(str(ini_path))
    new_name_0 = Path(pairs[0][1]).name
    assert doc.is_starred(new_name_0) is True
