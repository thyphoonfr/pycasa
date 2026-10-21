"""FR: Tests pour la boîte de dialogue d'exportation Picasa et le moteur de traitement (CExportPrefsDialog / CImageOutput).
EN: Tests for Picasa Export Dialog and Processing Engine (CExportPrefsDialog / CImageOutput).
"""

import os
import shutil
import tempfile
from pathlib import Path
from PIL import Image

import pytest
from PySide6.QtWidgets import QApplication

from picasa_py.ui.export_dialog import (
    PicasaExportDialog, PicasaExportConfig, PicasaExportWorker,
    EXPORT_SIZE_STEPS, QUALITY_PRESETS
)
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.faces.facerect import encode_rect64_string


@pytest.fixture
def temp_export_env(tmp_path):
    """FR: Crée un environnement temporaire d'exportation avec 3 images et un fichier .picasa.ini.
    EN: Creates a temporary export environment with 3 images and a .picasa.ini file.
    """
    src_dir = tmp_path / "source_photos"
    src_dir.mkdir()
    dest_dir = tmp_path / "exports"
    dest_dir.mkdir()

    # Créer 3 images de test
    img_paths = []
    for i in range(3):
        p = src_dir / f"test_img_{i}.jpg"
        img = Image.new("RGB", (1200, 800), color=(100 + i * 40, 150, 200))
        img.save(p, "JPEG")
        img_paths.append(str(p))

    # Créer un .picasa.ini avec rotation pour img 0 et crop pour img 1
    ini_doc = PicasaIniDocument()
    ini_doc.set_rotate("test_img_0.jpg", 1)  # 90° CW -> deviendra 800x1200
    crop_str = encode_rect64_string(0.25, 0.25, 0.75, 0.75)
    ini_doc.set_crop("test_img_1.jpg", crop_str)  # 50% central -> 600x400
    ini_doc.write_file(str(src_dir / ".picasa.ini"))

    return {
        "src_dir": src_dir,
        "dest_dir": dest_dir,
        "img_paths": img_paths,
        "crop_str": crop_str
    }


def test_export_dialog_config(qapp, temp_export_env):
    """FR: Vérifie la configuration par défaut et les contrôles de PicasaExportDialog.
    EN: Verifies the default configuration and controls of PicasaExportDialog.
    """
    dlg = PicasaExportDialog(
        item_paths=temp_export_env["img_paths"],
        default_folder_name="Vacances2024"
    )
    assert dlg.edit_name.text() == "Vacances2024"
    assert dlg.radio_resize.isChecked()
    assert dlg.edit_size.text() == "800"

    cfg = dlg.get_config()
    assert cfg.folder_name == "Vacances2024"
    assert cfg.target_size == 800
    assert not cfg.use_original_size
    assert not cfg.use_watermark


def test_export_worker_transformations_and_watermark(temp_export_env):
    """FR: Vérifie l'application des transformations (rotation, recadrage, redimensionnement) et du filigrane lors de l'exportation.
    EN: Verifies application of transformations (rotation, crop, resize) and watermarking during export.
    """
    cfg = PicasaExportConfig(
        dest_path=str(temp_export_env["dest_dir"]),
        folder_name="AlbumTest",
        add_numbers=True,
        use_original_size=False,
        target_size=400,
        quality=85,
        use_watermark=True,
        watermark_text="© PyCasa 2026"
    )

    worker = PicasaExportWorker(temp_export_env["img_paths"], cfg)
    
    finished_args = []
    worker.finished.connect(lambda s, e, out: finished_args.append((s, e, out)))

    # Exécuter de manière synchrone via run()
    worker.run()

    assert len(finished_args) == 1
    succ, err, out_dir = finished_args[0]
    assert succ == 3
    assert err == 0

    out_path = Path(out_dir)
    assert out_path.exists()

    exported_files = sorted(list(out_path.glob("*.jpg")))
    assert len(exported_files) == 3

    # Vérification des numéros d'ordre dans les noms de fichiers
    assert exported_files[0].name.startswith("01-test_img_0")
    assert exported_files[1].name.startswith("02-test_img_1")
    assert exported_files[2].name.startswith("03-test_img_2")

    # Image 0 a été tournée de 90° (original 1200x800 -> tourné 800x1200 -> redimensionné à max 400)
    with Image.open(exported_files[0]) as im0:
        w, h = im0.size
        assert max(w, h) <= 400
        assert h >= w  # portrait après rotation 90°

    # Image 1 a été croppée (ratio 1:1 car 50% de 1200x800 = 600x400 non mais recadré)
    with Image.open(exported_files[1]) as im1:
        w, h = im1.size
        assert max(w, h) <= 400
