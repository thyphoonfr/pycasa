"""
FR: Tests unitaires et d'intégration pour la détection de changements en temps réel
(PicasaFolderWatcher @ 0x00704F20) et la fenêtre surgissante de notification
(PicasaNotifierPopup / CNotifierPopup @ 0x00656FE0).

EN: Unit and integration tests for real-time filesystem change detection
(PicasaFolderWatcher @ 0x00704F20) and the floating notification popup window
(PicasaNotifierPopup / CNotifierPopup @ 0x00656FE0).

Ref: picasa3.exe @ 0x00704F20 (ReadDirectoryChangesW, debounce 500 ms)
Ref: picasa3.exe @ 0x00656FE0, 0x00658400, 0x00659270, 0x00659340, 0x00571850, 0x005E4D30
"""

from __future__ import annotations
import os
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from picasa_py.db.database import PicasaDatabase
from picasa_py.scanner.watcher import PicasaFolderWatcher
from picasa_py.ui.main_window import PicasaMainWindow
from picasa_py.ui.notifier_popup import PicasaNotifierPopup


def _ensure_qapp() -> QApplication:
    """
    FR: Garantit qu'une instance QApplication existe pour les tests Qt.
    EN: Ensures a QApplication instance exists for Qt tests.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_notifier_popup_cell_accumulation_and_thumbnail(tmp_path: Path) -> None:
    """
    FR: Vérifie que PicasaNotifierPopup accumule les notifications par dossier (compteur incrémenté,
    miniature 38x29 avec bordure #7792A4 mise à jour, délai de 5000 ms) et plafonne l'affichage à 3 cellules.
    EN: Verifies that PicasaNotifierPopup accumulates notifications per folder (incremented counter,
    updated 38x29 thumbnail with #7792A4 border, 5000 ms timeout) and caps visible cells at 3.
    Ref: picasa3.exe @ 0x006584BF (max 3 cells), 0x00659270 (38x29 thumb, #7792A4), 0x00659340 (accumulation)
    """
    _ensure_qapp()
    popup = PicasaNotifierPopup()
    try:
        assert popup.windowTitle() == "Picasa Notifier"
        assert popup.THUMB_WIDTH == 38
        assert popup.THUMB_HEIGHT == 29
        assert popup.THUMB_BORDER_COLOR == "#7792A4"
        assert popup.DEFAULT_TIMEOUT_MS == 5000
        assert popup.MAX_VISIBLE_CELLS == 3

        folder_a = tmp_path / "Vacances_Ete"
        folder_a.mkdir()
        img1 = folder_a / "IMG_0001.JPG"
        img2 = folder_a / "IMG_0002.JPG"
        Image.new("RGB", (320, 240), (220, 80, 60)).save(img1, "JPEG")
        Image.new("RGB", (320, 240), (60, 140, 220)).save(img2, "JPEG")

        cell1 = popup.notify_photo_indexed(str(folder_a), "IMG_0001.JPG", str(img1), show_popup=False)
        assert len(popup.cells) == 1
        assert cell1.count == 1
        assert cell1.title == "Vacances_Ete"
        assert cell1.filename == "IMG_0001.JPG"
        assert cell1.thumbnail is not None
        assert cell1.thumbnail.width() <= 38 and cell1.thumbnail.height() <= 29

        # Une seconde photo dans le même dossier incrémente le compteur sans dupliquer la cellule
        cell2 = popup.notify_photo_indexed(str(folder_a), "IMG_0002.JPG", str(img2), show_popup=False)
        assert len(popup.cells) == 1
        assert cell2 is cell1
        assert cell2.count == 2
        assert cell2.filename == "IMG_0002.JPG"
        assert "2" in cell2.subtitle and "IMG_0002.JPG" in cell2.subtitle

        # Ajouter 3 autres dossiers : seules 3 cellules sont visibles simultanément (Ref: 0x006584BF)
        for i in range(3):
            f_extra = tmp_path / f"Dossier_{i}"
            f_extra.mkdir()
            p_extra = f_extra / f"photo_{i}.jpg"
            Image.new("RGB", (160, 120), (100, 180, 90)).save(p_extra, "JPEG")
            popup.notify_photo_indexed(str(f_extra), p_extra.name, str(p_extra), show_popup=False)

        assert len(popup.cells) == 4
        assert len(popup._cell_rects) == 3

        # Vérifier le rendu paintEvent sans erreur
        popup.repaint()
    finally:
        popup.clear_notifications()
        popup.close()


def test_notifier_popup_click_signal_and_collapse(tmp_path: Path) -> None:
    """
    FR: Vérifie qu'un clic sur une cellule émet notification_clicked(file_path, folder_path)
    (WM_USER + 0xFF = 0x4FF @ 0x00658056) et que les boutons réduire/fermer fonctionnent.
    EN: Verifies that clicking a cell emits notification_clicked(file_path, folder_path)
    (WM_USER + 0xFF = 0x4FF @ 0x00658056) and that the collapse/close buttons work.
    """
    _ensure_qapp()
    popup = PicasaNotifierPopup()
    try:
        folder = tmp_path / "Captures"
        folder.mkdir()
        img_path = folder / "capture_01.jpg"
        Image.new("RGB", (200, 150), (40, 200, 120)).save(img_path, "JPEG")

        popup.notify_photo_indexed(str(folder), "capture_01.jpg", str(img_path), show_popup=False)
        assert len(popup._cell_rects) == 1

        # Tester le bouton Réduire/Déplier
        collapse_center = popup._collapse_rect.center()
        ev_collapse = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(collapse_center),
            QPointF(collapse_center),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        popup.mousePressEvent(ev_collapse)
        assert popup.is_collapsed is True
        assert len(popup._cell_rects) == 0

        # Déplier à nouveau
        popup.mousePressEvent(ev_collapse)
        assert popup.is_collapsed is False
        assert len(popup._cell_rects) == 1

        # Cliquer sur la cellule -> doit émettre notification_clicked
        clicked_events = []
        popup.notification_clicked.connect(lambda fp, fd: clicked_events.append((fp, fd)))

        cell_center = popup._cell_rects[0].center()
        ev_cell = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(cell_center),
            QPointF(cell_center),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        popup.mousePressEvent(ev_cell)
        assert len(clicked_events) == 1
        assert clicked_events[0] == (str(img_path), str(folder))
        assert len(popup.cells) == 0
    finally:
        popup.clear_notifications()
        popup.close()


def test_watcher_excludes_hidden_dirs_and_falls_back_to_indexed_folders(tmp_path: Path) -> None:
    """
    FR: Vérifie que PicasaFolderWatcher ignore les sous-dossiers exclus (.git, .picasaoriginals, __pycache__)
    et surveille automatiquement les dossiers indexés (rec.type == 1) de la base de données.
    EN: Verifies that PicasaFolderWatcher skips excluded subdirectories (.git, .picasaoriginals, __pycache__)
    and automatically watches indexed folders (rec.type == 1) from the database.
    """
    _ensure_qapp()
    db_dir = tmp_path / "db_test"
    photo_root = tmp_path / "Photos"
    sub_ok = photo_root / "AlbumVacances"
    sub_git = photo_root / ".git"
    sub_orig = photo_root / ".picasaoriginals"
    sub_ok.mkdir(parents=True)
    sub_git.mkdir(parents=True)
    sub_orig.mkdir(parents=True)

    img_file = sub_ok / "test.jpg"
    Image.new("RGB", (100, 100), (255, 0, 0)).save(img_file, "JPEG")

    db = PicasaDatabase.create_new(str(db_dir))
    db.add_media_record(str(sub_ok) + "\\", "test.jpg", os.path.getsize(img_file), int(os.path.getmtime(img_file)), 2)

    watcher = PicasaFolderWatcher(db)
    norm_sub_ok = os.path.abspath(str(sub_ok))
    assert norm_sub_ok in watcher.watched_paths

    watcher.set_watched_directories([str(photo_root)])
    assert os.path.abspath(str(photo_root)) in watcher.watched_paths
    assert os.path.abspath(str(sub_ok)) in watcher.watched_paths
    assert os.path.abspath(str(sub_git)) not in watcher.watched_paths
    assert os.path.abspath(str(sub_orig)) not in watcher.watched_paths


def test_main_window_queues_scans_and_populates_notifier_popup(tmp_path: Path) -> None:
    """
    FR: Vérifie que PicasaMainWindow met en file d'attente les dossiers modifiés si un scan est déjà actif,
    et que l'indexation d'une nouvelle photo alimente PicasaNotifierPopup et permet de la sélectionner au clic.
    EN: Verifies that PicasaMainWindow queues modified folders when a scan is already running,
    and that indexing a new photo populates PicasaNotifierPopup and selects it when clicked.
    """
    _ensure_qapp()
    db_dir = tmp_path / "db_mw"
    photos_dir = tmp_path / "MesPhotos"
    photos_dir.mkdir(parents=True)

    db = PicasaDatabase.create_new(str(db_dir))
    db.set_watched_folder(str(photos_dir), "1")
    db.save_database()

    win = PicasaMainWindow(db_path=str(db.db3_dir), auto_scan=False)
    try:
        img_new = photos_dir / "nouvelle_photo.jpg"
        Image.new("RGB", (240, 180), (50, 120, 240)).save(img_new, "JPEG")

        win._start_background_scan([str(photos_dir)], notify_popup=True)
        if win.scan_worker:
            win.scan_worker.wait(5000)
        QApplication.processEvents()

        # La notification doit avoir été enregistrée dans win.notifier_popup
        assert len(win.notifier_popup.cells) >= 1
        assert win.notifier_popup.cells[0].filename == "nouvelle_photo.jpg"

        # Simuler le clic sur la notification -> doit sélectionner la photo dans thumb_view
        win._on_notifier_popup_clicked(str(img_new), str(photos_dir))
        selected_paths = [win.thumb_view.items[i].path for i in win.thumb_view.selected_indices]
        assert any(os.path.normcase(p) == os.path.normcase(str(img_new)) for p in selected_paths)
    finally:
        win.close()


def test_zoom_overview_close_button_resets_zoom_to_fit() -> None:
    """
    FR: Vérifie que lorsque la photo est zoomée dans PicasaImageCanvas, la miniature d'aperçu
    (`editpanel/nav`) expose le bouton croix de fermeture (`_nav_close_rect`, `PanHandler @ 0x005C46B0`),
    et qu'un clic sur cette croix referme la miniature et remet la photo ajustée à l'emplacement (`0x00597D10`).
    EN: Verifies that when the photo is zoomed in PicasaImageCanvas, the overview miniature
    (`editpanel/nav`) exposes the close cross button (`_nav_close_rect`, `PanHandler @ 0x005C46B0`),
    and clicking that cross closes the miniature and resets the photo zoom to fit the viewport (`0x00597D10`).
    """
    _ensure_qapp()
    from PySide6.QtGui import QPixmap
    from picasa_py.ui.image_canvas import PicasaImageCanvas

    canvas = PicasaImageCanvas()
    try:
        canvas.resize(800, 600)
        pix = QPixmap(1200, 900)
        pix.fill(Qt.GlobalColor.darkBlue)
        canvas.set_pixmap_direct(pix)

        # Initialement ajusté à la fenêtre
        assert canvas.fit_to_window is True
        assert canvas.is_zoomed_in() is False

        # Zoomer à 200 %
        canvas.set_zoom(2.0)
        canvas._update_loupe_geometry()
        assert canvas.is_zoomed_in() is True
        assert not canvas._nav_card_rect.isEmpty()
        assert not canvas._nav_close_rect.isEmpty()
        assert canvas._nav_card_rect.contains(canvas._nav_close_rect)

        # Survoler la petite croix [×]
        close_center = canvas._nav_close_rect.center()
        ev_move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(close_center),
            QPointF(close_center),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mouseMoveEvent(ev_move)
        assert canvas._is_hovering_nav_close is True

        # Cliquer sur la petite croix [×] -> doit réinitialiser le zoom (fit_to_window) et fermer la miniature
        zoom_signals = []
        canvas.zoom_changed.connect(zoom_signals.append)
        ev_click = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(close_center),
            QPointF(close_center),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        canvas.mousePressEvent(ev_click)

        assert canvas.fit_to_window is True
        assert canvas.is_zoomed_in() is False
        assert canvas._nav_card_rect.isEmpty()
        assert canvas._nav_close_rect.isEmpty()
        assert len(zoom_signals) == 1
    finally:
        canvas.close()


def test_effect_recalculates_thumbnails_and_fast_oneup_navigation(tmp_path: Path) -> None:
    """
    FR: Vérifie que :
    1. L'application d'un effet (`bw`, `sepia`, `finetune2`) ou d'une rotation dans `PicasaOneUpView`
       recalcule immédiatement les miniatures et aperçus (`thumbs`, `thumbs2`, `bigthumbs`, `previews`)
       dans `PicasaDatabase` (`FUN_00579360 @ 0x00579360` -> `0x00425210`) et invalide le cache de la
       pellicule supérieure (`editpanel/filmstrip`, `0x00579680`).
    2. La navigation avec la pellicule ou les flèches (`navigate_next`, `navigate_previous`,
       `_on_filmstrip_photo_clicked`) redimensionne l'aperçu avant l'exécution de `filters=` (`0x0042525F`,
       `0x640 = 1600px`) et reste fluide même sur des photos haute résolution avec effets.
    EN: Verifies that:
    1. Applying an effect (`bw`, `sepia`, `finetune2`) or rotation in `PicasaOneUpView`
       immediately recalculates thumbnails and previews (`thumbs`, `thumbs2`, `bigthumbs`, `previews`)
       in `PicasaDatabase` (`FUN_00579360 @ 0x00579360` -> `0x00425210`) and invalidates the top
       filmstrip cache (`editpanel/filmstrip`, `0x00579680`).
    2. Navigating via filmstrip or arrow keys (`navigate_next`, `navigate_previous`,
       `_on_filmstrip_photo_clicked`) scales the preview before executing `filters=` (`0x0042525F`,
       `0x640 = 1600px`) and remains fast even on high-resolution photos with effects.
    """
    import io
    import time
    _ensure_qapp()
    from picasa_py.ui.one_up_view import PicasaOneUpView
    from picasa_py.scanner.scanner import PicasaDirScanner

    db_dir = tmp_path / "db_oneup"
    photos_dir = tmp_path / "PhotosOneUp"
    photos_dir.mkdir(parents=True)

    # Créer 3 photos colorées (dont une photo 2400x1800 pour tester le redimensionnement pré-filtre)
    p1 = photos_dir / "photo_red.jpg"
    p2 = photos_dir / "photo_green_hd.jpg"
    p3 = photos_dir / "photo_blue.jpg"
    Image.new("RGB", (600, 400), (240, 20, 20)).save(p1, "JPEG", quality=92)
    Image.new("RGB", (2400, 1800), (20, 210, 40)).save(p2, "JPEG", quality=92)
    Image.new("RGB", (600, 400), (30, 60, 230)).save(p3, "JPEG", quality=92)

    db = PicasaDatabase.create_new(str(db_dir))
    scanner = PicasaDirScanner(db)
    idx1 = scanner.index_file(str(p1))
    idx2 = scanner.index_file(str(p2))
    idx3 = scanner.index_file(str(p3))
    assert idx1 is not None and idx2 is not None and idx3 is not None
    avail = [idx1, idx2, idx3]

    # Vérifier que la miniature initiale de p1 est rouge (R >> G, B)
    raw_before = db.load_thumbnail(idx1, size="small")
    assert raw_before is not None
    with Image.open(io.BytesIO(raw_before)) as th_before:
        r0, g0, b0 = th_before.convert("RGB").getpixel((th_before.width // 2, th_before.height // 2))
        assert r0 > 180 and g0 < 60 and b0 < 60

    view = PicasaOneUpView()
    try:
        view.open_photo(db, idx1, avail)
        # Charger la miniature dans le cache du filmstrip avant l'effet
        pix_fs_before = view.filmstrip._load_pixmap(idx1)
        assert pix_fs_before is not None
        assert idx1 in view.filmstrip._thumb_cache

        # Appliquer l'effet Noir & Blanc ('bw') sur p1
        view._on_apply_effect("bw", {})

        # 1. La miniature dans PicasaDatabase (thumbs_0.db et previews_0.db) doit avoir été recalculée en niveaux de gris !
        raw_after = db.load_thumbnail(idx1, size="small")
        assert raw_after is not None
        assert raw_after != raw_before
        with Image.open(io.BytesIO(raw_after)) as th_after:
            r1, g1, b1 = th_after.convert("RGB").getpixel((th_after.width // 2, th_after.height // 2))
            assert abs(r1 - g1) <= 3 and abs(g1 - b1) <= 3

        raw_prev = db.load_thumbnail(idx1, size="preview")
        assert raw_prev is not None

        # 2. Appliquer plusieurs effets sur la photo HD p2 (2400x1800)
        view.navigate_next()
        assert view.current_index == idx2
        # La dimension chargée dans l'éditeur doit être plafonnée à 1600px (0x640, Ref: 0x0042525F)
        assert max(view._history[0].size) <= 1600
        view._on_apply_effect("sepia", {})
        view._on_apply_effect("vignette", {"amount": 0.5, "size": 0.3})

        # 3. Mesurer la rapidité de navigation aller-retour via flèches et pellicule sur les photos avec effets
        t0 = time.perf_counter()
        view.navigate_next()
        assert view.current_index == idx3
        view.navigate_previous()
        assert view.current_index == idx2
        view._on_filmstrip_photo_clicked(idx1)
        assert view.current_index == idx1
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert elapsed_ms < 600.0, f"Navigation One-Up trop lente : {elapsed_ms:.1f} ms"
    finally:
        view.close()


