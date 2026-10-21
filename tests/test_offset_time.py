"""FR: Tests pour la boîte de dialogue d'ajustement de la date et de l'heure des photos (Option 6).
EN: Tests for Adjust Photo Date and Time Dialog (Option 6).
Ref: picasa3.exe @ 0x0077C670 (COffsetDate), 0x0077CFD0 (AdjustTimeThread), offsettime.fen, OFFSETTIME_FR.XML
"""

from __future__ import annotations
import os
import datetime
from pathlib import Path
from PIL import Image

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate, QTime

from picasa_py.ui.offset_time_dialog import (
    PicasaAdjustTimeDialog,
    unix_to_filetime,
    filetime_to_unix,
    get_photo_datetime,
)
from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexFile, ThumbIndexRecord


@pytest.fixture(scope="session")
def qapp():
    """FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provides a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_filetime_conversions():
    """FR: Vérifie la conversion bidirectionnelle exacte entre horodatage Unix et FILETIME Windows.
    EN: Verifies exact bidirectional conversion between Unix timestamp and Windows FILETIME.
    """
    # Test à l'époque Unix (1970-01-01 00:00:00 UTC)
    ft_epoch = unix_to_filetime(0.0)
    assert ft_epoch == 11644473600 * 10_000_000

    # Test round-trip avec horodatage arbitraire
    test_ts = 1715688000.0  # 2024-05-14 12:00:00 UTC
    ft = unix_to_filetime(test_ts)
    recovered_ts = filetime_to_unix(ft)
    assert recovered_ts == test_ts


def test_get_photo_datetime(tmp_path):
    """FR: Vérifie la lecture correcte de la date depuis l'EXIF ou le mtime.
    EN: Verifies accurate date reading from EXIF or file mtime.
    """
    img_path = tmp_path / "exif_photo.jpg"
    img = Image.new("RGB", (50, 50), color="blue")

    exif = img.getexif()
    exif[36867] = "2023:08:14 15:30:45"  # DateTimeOriginal
    img.save(str(img_path), format="JPEG", exif=exif)

    dt = get_photo_datetime(str(img_path))
    assert dt == datetime.datetime(2023, 8, 14, 15, 30, 45)

    # Sans EXIF -> repli sur le mtime
    no_exif_path = tmp_path / "no_exif.png"
    img.save(str(no_exif_path), format="PNG")
    mtime_target = datetime.datetime(2022, 1, 10, 12, 0, 0)
    os.utime(str(no_exif_path), (mtime_target.timestamp(), mtime_target.timestamp()))

    dt_no_exif = get_photo_datetime(str(no_exif_path))
    assert dt_no_exif.year == 2022
    assert dt_no_exif.month == 1
    assert dt_no_exif.day == 10


def test_adjust_time_dialog_ui(qapp, tmp_path):
    """FR: Vérifie les titres, éléments graphiques et initialisations de la boîte de dialogue.
    EN: Verifies dialog titles, UI widgets, and initializations.
    """
    p1 = tmp_path / "photo1.jpg"
    p2 = tmp_path / "photo2.jpg"
    for p in (p1, p2):
        img = Image.new("RGB", (40, 40), color="red")
        img.save(str(p), format="JPEG")

    # 1. Dialogue avec 1 seule photo
    dlg1 = PicasaAdjustTimeDialog([str(p1)])
    assert dlg1.windowTitle() == "Ajuster la date de la photo"
    assert dlg1.radio_relative.isChecked() is True

    # 2. Dialogue avec plusieurs photos
    dlg2 = PicasaAdjustTimeDialog([str(p1), str(p2)])
    assert "2 éléments" in dlg2.windowTitle()
    assert dlg2.lbl_thumb is not None
    assert dlg2.edit_curr_date.isEnabled() is False
    assert dlg2.edit_curr_time.isEnabled() is False
    assert dlg2.edit_new_date.isEnabled() is True
    assert dlg2.edit_new_time.isEnabled() is True


def test_adjust_time_execution_relative_and_absolute(qapp, tmp_path):
    """FR: Vérifie l'exécution du décalage relatif et absolu sur fichiers et base de données.
    EN: Verifies relative and absolute time adjustment execution on files and database.
    """
    p1 = tmp_path / "photo1.jpg"
    p2 = tmp_path / "photo2.jpg"

    dt1 = datetime.datetime(2023, 1, 1, 10, 0, 0)
    dt2 = datetime.datetime(2023, 1, 1, 12, 0, 0)

    for p, dt in ((p1, dt1), (p2, dt2)):
        img = Image.new("RGB", (30, 30), color="white")
        exif = img.getexif()
        exif[36867] = dt.strftime("%Y:%m:%d %H:%M:%S")
        img.save(str(p), format="JPEG", exif=exif)
        os.utime(str(p), (dt.timestamp(), dt.timestamp()))

    # Créer une base de données de test
    db = PicasaDatabase(db3_dir=tmp_path)
    db.thumbindex = ThumbIndexFile()
    rec1 = ThumbIndexRecord(path=str(p1), ft1=unix_to_filetime(dt1.timestamp()), ft2=0, size=100, type=2, flags=0, parent_idx=0)
    rec2 = ThumbIndexRecord(path=str(p2), ft1=unix_to_filetime(dt2.timestamp()), ft2=0, size=100, type=2, flags=0, parent_idx=0)
    db.thumbindex.records = [rec1, rec2]

    # --- Test 1 : Décalage Relatif de +2 heures (+7200s) ---
    dlg = PicasaAdjustTimeDialog([str(p1), str(p2)], db=db)
    dlg.radio_relative.setChecked(True)
    # Définir nouvelle date de référence : 10:00:00 -> 12:00:00
    dlg.edit_new_date.setDate(QDate(2023, 1, 1))
    dlg.edit_new_time.setTime(QTime(12, 0, 0))

    results = dlg.execute_adjustment()
    assert len(results) == 2

    # Photo 1 décalée de +2h (10h -> 12h)
    new_dt1 = get_photo_datetime(str(p1))
    assert new_dt1 == datetime.datetime(2023, 1, 1, 12, 0, 0)

    # Photo 2 décalée de +2h (12h -> 14h)
    new_dt2 = get_photo_datetime(str(p2))
    assert new_dt2 == datetime.datetime(2023, 1, 1, 14, 0, 0)

    # Vérification mise à jour EXIF
    with Image.open(p1) as img1:
        assert img1.getexif().get(36867) == "2023:01:01 12:00:00"
    with Image.open(p2) as img2:
        assert img2.getexif().get(36867) == "2023:01:01 14:00:00"

    # --- Test 2 : Définition Absolue (même date pour tous) ---
    dlg_abs = PicasaAdjustTimeDialog([str(p1), str(p2)], db=db)
    dlg_abs.radio_absolute.setChecked(True)
    dlg_abs.edit_new_date.setDate(QDate(2025, 6, 20))
    dlg_abs.edit_new_time.setTime(QTime(18, 45, 0))

    results_abs = dlg_abs.execute_adjustment()
    assert len(results_abs) == 2

    assert get_photo_datetime(str(p1)) == datetime.datetime(2025, 6, 20, 18, 45, 0)
    assert get_photo_datetime(str(p2)) == datetime.datetime(2025, 6, 20, 18, 45, 0)
