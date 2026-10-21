"""
FR: Tests pour l'atelier d'impression interactif WYSIWYG de Picasa 3 (CPrintDlg).
EN: Tests for Picasa 3 Interactive WYSIWYG Print Workshop (CPrintDlg).
Ref: picasa3.exe @ 0x008C3380 (reviewprint, CPrintDlg, printpanel/*)
"""

import os
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPaintEvent, QRegion
from PySide6.QtWidgets import QApplication

from picasa_py.ui.print_dialog import (
    PicasaPrintDialog, PicasaPrintPreviewCanvas, PrintLayoutType
)
from picasa_py.ui.main_window import PicasaMainWindow


def test_print_canvas_page_and_cells_calculation(qapp, tmp_path):
    """
    FR: Vérifie le découpage des cellules et le calcul du nombre de pages selon la disposition.
    EN: Verify cell layout partitioning and page count calculation according to the print layout.
    """
    canvas = PicasaPrintPreviewCanvas()
    canvas.resize(600, 800)

    # 5 photos fictives
    paths = []
    for i in range(5):
        p = tmp_path / f"photo_{i}.jpg"
        im = Image.new("RGB", (800, 600), color=(i * 40, 100, 150))
        im.save(p)
        paths.append(str(p))

    # 1. Pleine page (1 par page) -> 5 pages avec copies=1
    canvas.set_data(paths, PrintLayoutType.FULL_PAGE, "crop", copies=1)
    assert canvas.get_photos_per_page() == 1
    assert canvas.get_total_pages() == 5
    assert len(canvas.get_photos_for_page(0)) == 1

    # 2. Format 10 x 15 cm (2 par page) -> ceil(5 / 2) = 3 pages
    canvas.set_data(paths, PrintLayoutType.FORMAT_10x15, "crop", copies=1)
    assert canvas.get_photos_per_page() == 2
    assert canvas.get_total_pages() == 3
    assert len(canvas.get_photos_for_page(0)) == 2
    assert len(canvas.get_photos_for_page(2)) == 1

    # 3. Format 10 x 15 cm avec 2 copies -> 10 tirages -> 5 pages
    canvas.set_data(paths, PrintLayoutType.FORMAT_10x15, "crop", copies=2)
    assert canvas.get_total_prints_count() == 10
    assert canvas.get_total_pages() == 5

    # 4. Petit format / Portefeuille (9 par page) -> 1 page
    canvas.set_data(paths, PrintLayoutType.WALLET, "shrink", copies=1)
    assert canvas.get_photos_per_page() == 9
    assert canvas.get_total_pages() == 1
    assert len(canvas.get_photos_for_page(0)) == 5

    # 5. Planche-contact (35 par page) -> 1 page
    canvas.set_data(paths, PrintLayoutType.CONTACT_SHEET, "shrink", copies=1)
    assert canvas.get_photos_per_page() == 35
    assert canvas.get_total_pages() == 1

    # Vérification des cellules géométriques
    cells_full = canvas._compute_cells(QRectF(0, 0, 500, 700))
    assert len(cells_full) == 35  # car layout_type est CONTACT_SHEET

    canvas.layout_type = PrintLayoutType.FORMAT_10x15
    cells_2 = canvas._compute_cells(QRectF(0, 0, 500, 700))
    assert len(cells_2) == 2


def test_print_canvas_dpi_calculation(qapp, tmp_path):
    """
    FR: Vérifie le calcul des DPI et des paliers de qualité (best / good / bad).
    EN: Verify DPI calculation and quality tier classification (best / good / bad).
    """
    canvas = PicasaPrintPreviewCanvas()

    # Image haute résolution (3000 x 2000)
    p_high = tmp_path / "high_res.jpg"
    Image.new("RGB", (3000, 2000), color=(100, 100, 100)).save(p_high)

    canvas.set_data([str(p_high)], PrintLayoutType.FORMAT_10x15, "crop", 1)
    dpi, qual = canvas.calculate_current_dpi()
    assert dpi >= 280
    assert qual == "best"

    # Image très basse résolution (200 x 150)
    p_low = tmp_path / "low_res.jpg"
    Image.new("RGB", (200, 150), color=(100, 100, 100)).save(p_low)

    canvas.set_data([str(p_low)], PrintLayoutType.FULL_PAGE, "crop", 1)
    dpi_low, qual_low = canvas.calculate_current_dpi()
    assert dpi_low < 150
    assert qual_low == "bad"


def test_print_preview_paint_event(qapp, tmp_path):
    """
    FR: Vérifie que le rendu WYSIWYG s'exécute sans erreur graphique.
    EN: Verify that WYSIWYG preview rendering executes without graphical errors.
    """
    canvas = PicasaPrintPreviewCanvas()
    canvas.resize(500, 650)

    p = tmp_path / "test_img.jpg"
    Image.new("RGB", (400, 300), color=(200, 120, 80)).save(p)

    canvas.set_data([str(p)], PrintLayoutType.FORMAT_10x15, "crop", copies=1)
    canvas.paintEvent(QPaintEvent(QRegion(canvas.rect())))

    canvas.set_data([str(p)], PrintLayoutType.CONTACT_SHEET, "shrink", copies=1)
    canvas.paintEvent(QPaintEvent(QRegion(canvas.rect())))


def test_print_dialog_ui_components(qapp, tmp_path):
    """
    FR: Vérifie l'interaction des contrôles dans la boîte de dialogue d'impression.
    EN: Verify control interactions in the print dialog.
    """
    paths = []
    for i in range(3):
        p = tmp_path / f"img_{i}.jpg"
        Image.new("RGB", (600, 400), color=(100, 200, 50)).save(p)
        paths.append(str(p))

    dlg = PicasaPrintDialog(paths)
    assert dlg.spin_copies.value() == 1
    assert dlg.preview_canvas.get_total_pages() == 2  # 3 photos en 10x15 (2/page) = 2 pages

    # Changer le format à Pleine page (1 par page)
    dlg.radio_layouts[0][0].setChecked(True)
    dlg._on_layout_changed(0)
    assert dlg.preview_canvas.get_total_pages() == 3

    # Passer à la page 2
    dlg._on_next_page()
    assert dlg.preview_canvas.current_page == 1
    assert "Page 2 sur 3" in dlg.lbl_pag_info.text()

    # Revenir à la page 1
    dlg._on_prev_page()
    assert dlg.preview_canvas.current_page == 0

    # Changer les copies à 2
    dlg.spin_copies.setValue(2)
    assert dlg.preview_canvas.get_total_prints_count() == 6
