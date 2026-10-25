"""
FR: Tests pour :
1. Le volet des Lieux (`PicasaPlacesPanel` & `PicasaRightDrawer`) :
   - Recherche d'adresse (villes, monuments, coordonnées GPS, `GeocodeWorker`)
   - Affichage du nombre d'emplacements dans un album (`geopanel/geo_info`, `GeoPanel::geo_info_format`)
   - Persistance `geotag=lat,lon` et effacement (`geopanel/cleargeotag`) dans `.picasa.ini`
2. Le système de thèmes de couleurs (`ui/resources/themes/*.ini` & menu `Affichage > Thème de couleurs`)
3. L'écran de démarrage authentique (`PicasaSplashScreen` & `ui/resources/splashbk.jpg`)
EN: Tests for:
1. The Places panel (`PicasaPlacesPanel` & `PicasaRightDrawer`):
   - Address search (cities, landmarks, GPS coordinates, `GeocodeWorker`)
   - Album location count display (`geopanel/geo_info`, `GeoPanel::geo_info_format`)
   - Persistence of `geotag=lat,lon` and clearing (`geopanel/cleargeotag`) in `.picasa.ini`
2. Color theme system (`ui/resources/themes/*.ini` & `View > Color Theme` menu)
3. Authentic splash screen (`PicasaSplashScreen` & `ui/resources/splashbk.jpg`)
"""

import os
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.preferences import PicasaPreferences
from picasa_py.ini.parser import PicasaIniParser
from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.right_drawer import (
    PicasaRightDrawer,
    PicasaPlacesPanel,
    GeocodeWorker,
    parse_gps_coordinates_query,
)
from picasa_py.ui.splash_screen import PicasaSplashScreen, SPLASH_BG_PATH
from picasa_py.ui.main_window import PicasaMainWindow


def _ensure_qapp() -> QApplication:
    """
    FR: Garantit qu'une instance de QApplication est initialisée.
    EN: Ensure that a QApplication instance is initialized.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_places_address_search_and_persistence(tmp_path: Path):
    """
    FR: Vérifie que la recherche d'une adresse ou de coordonnées GPS dans `PicasaPlacesPanel`
    met à jour la carte, affiche le nom du lieu + DMS, et persiste `geotag=` dans `.picasa.ini`,
    et que le bouton Effacer (`geopanel/cleargeotag`) supprime bien la géolocalisation.
    EN: Verify that searching for an address or GPS coordinates in `PicasaPlacesPanel`
    updates the map, displays the location name + DMS, persists `geotag=` in `.picasa.ini`,
    and that the Clear button (`geopanel/cleargeotag`) removes the geotag.
    """
    _ensure_qapp()

    db = PicasaDatabase.create_new(tmp_path / "db_places")
    album_dir = tmp_path / "Vacances"
    album_dir.mkdir()
    img1 = album_dir / "photo1.jpg"
    Image.new("RGB", (64, 64), (100, 150, 200)).save(img1)

    drawer = PicasaRightDrawer()
    drawer.set_current_photo(db, 0, str(img1))

    # Au départ : aucune géolocalisation
    assert drawer.panel_places.lbl_geo_info.text() == "Aucun lieu trouvé."
    assert not drawer.panel_places.btn_clear_geotag.isEnabled()

    # 1. Recherche d'une ville ("Paris")
    drawer.panel_places.txt_search.setText("Paris")
    drawer.panel_places._on_search_address()

    assert drawer.panel_places.current_lat is not None
    assert drawer.panel_places.current_lon is not None
    assert abs(drawer.panel_places.current_lat - 48.8566) < 0.05
    assert abs(drawer.panel_places.current_lon - 2.3522) < 0.05
    assert "Paris" in drawer.panel_places.lbl_coords.text()
    assert drawer.panel_places.lbl_geo_info.text() == "1 lieu dans l'album"
    assert drawer.panel_places.btn_clear_geotag.isEnabled()

    # Vérifier la persistance dans .picasa.ini
    ini_file = album_dir / ".picasa.ini"
    assert ini_file.exists()
    doc = PicasaIniParser.parse_file(str(ini_file))
    sec = doc.get_section("photo1.jpg")
    assert sec is not None
    assert sec.get("geotag") is not None
    lat_str, lon_str = sec.get("geotag").split(",")
    assert abs(float(lat_str) - 48.8566) < 0.05
    assert abs(float(lon_str) - 2.3522) < 0.05

    # 2. Recherche par coordonnées GPS directes
    drawer.panel_places.txt_search.setText("45.7640, 4.8357")
    drawer.panel_places._on_search_address()
    assert abs(drawer.panel_places.current_lat - 45.7640) < 0.01
    assert abs(drawer.panel_places.current_lon - 4.8357) < 0.01

    # 3. Effacement de la géolocalisation (geopanel/cleargeotag)
    drawer.panel_places.btn_clear_geotag.click()
    assert drawer.panel_places.current_lat is None
    assert drawer.panel_places.lbl_geo_info.text() == "Aucun lieu trouvé."
    doc_after = PicasaIniParser.parse_file(str(ini_file))
    sec_after = doc_after.get_section("photo1.jpg")
    assert sec_after is None or sec_after.get("geotag") is None


def test_places_album_location_counter(tmp_path: Path):
    """
    FR: Vérifie que `PicasaPlacesPanel` affiche fidèlement le nombre d'emplacements dans un album
    (`GeoPanel::geo_info_format` : "X lieu(x) dans l'album").
    EN: Verify that `PicasaPlacesPanel` accurately displays the number of locations in an album
    (`GeoPanel::geo_info_format`: "X location(s) in album").
    """
    _ensure_qapp()

    db = PicasaDatabase.create_new(tmp_path / "db_counter")
    album_dir = tmp_path / "Roadtrip"
    album_dir.mkdir()

    paths = []
    for i in range(3):
        p = album_dir / f"img_{i}.jpg"
        Image.new("RGB", (64, 64), (120, 80, 90)).save(p)
        paths.append(str(p))

    drawer = PicasaRightDrawer()

    # Géolocaliser img_0 à Paris, img_1 à Paris (même lieu), et img_2 à Lyon (2e lieu)
    drawer.set_current_photo(db, 0, paths[0])
    drawer.panel_places.txt_search.setText("Paris")
    drawer.panel_places._on_search_address()

    drawer.set_current_photo(db, 1, paths[1])
    drawer.panel_places.txt_search.setText("Paris")
    drawer.panel_places._on_search_address()

    drawer.set_current_photo(db, 2, paths[2])
    drawer.panel_places.txt_search.setText("Lyon")
    drawer.panel_places._on_search_address()

    # On a 3 photos géolocalisées réparties sur 2 lieux distincts (Paris et Lyon)
    assert "2 lieux dans l'album" in drawer.panel_places.lbl_geo_info.text()
    assert "3 photos" in drawer.panel_places.lbl_geo_info.text()

    # Sélection de l'album complet via set_multiple_photos
    drawer.set_multiple_photos(db, [0, 1, 2], paths)
    assert "2 lieux dans l'album" in drawer.panel_places.lbl_geo_info.text()
    assert len(drawer.panel_places.album_markers) == 3


def test_color_themes_loading_and_switching(tmp_path: Path, monkeypatch):
    """
    FR: Vérifie que les 5 thèmes de couleurs (`ui/resources/themes/*.ini`) sont découverts,
    chargés correctement, présents dans le menu `Affichage > Thème de couleurs`,
    et applicables à chaud sur `PicasaMainWindow`.
    EN: Verify that the 5 color themes (`ui/resources/themes/*.ini`) are discovered,
    loaded properly, present in the `View > Color Theme` menu, and hot-applicable on `PicasaMainWindow`.
    """
    _ensure_qapp()
    monkeypatch.setattr(PicasaPreferences, "REGISTRY_APP", r"Picasa\Picasa2\Preferences_Pytest")

    themes = PicasaStyle.list_available_themes()
    theme_ids = {t[0] if isinstance(t, tuple) else t["id"] for t in themes}
    assert {"original", "dark", "aurora_gradient", "sunset_gradient", "ocean", "sepia_warm", "emerald_forest"}.issubset(theme_ids)

    db = PicasaDatabase.create_new(tmp_path / "db_themes")
    win = PicasaMainWindow(db_path=str(db.db3_dir), auto_scan=False)
    try:
        # Vérifier la présence des actions dans Affichage > Thème de couleurs
        assert win.menu_builder.menu_themes is not None
        assert len(win.menu_builder.theme_actions) >= 7

        # Basculer sur le thème Sunset Dégradé ("sunset_gradient")
        win.apply_theme("sunset_gradient")
        assert win.style.theme_id == "sunset_gradient"
        assert win.style.is_dark is True
        assert win.menu_builder.theme_actions["sunset_gradient"].isChecked()
        assert PicasaPreferences.get_theme_id() == "sunset_gradient"
        assert win.style.grid_bgcolor.name().lower() == "#140c14"
        assert win.style.grid_bgcolor_end.name().lower() == "#2d122b"
        assert win.style.accent_color.name().lower() == "#e11d48"
        assert win.style.accent_grad_end.name().lower() == "#f59e0b"

        # Basculer sur le nouveau thème moderne dégradé ("aurora_gradient")
        win.apply_theme("aurora_gradient")
        assert win.style.theme_id == "aurora_gradient"
        assert win.style.is_dark is True
        assert win.menu_builder.theme_actions["aurora_gradient"].isChecked()
        assert PicasaPreferences.get_theme_id() == "aurora_gradient"
        assert win.style.grid_bgcolor.name().lower() == "#0b1120"
        assert win.style.grid_bgcolor_end.name().lower() == "#1e1b4b"
        assert win.style.topbar_grad_mid is not None
        assert win.style.topbar_grad_mid.name().lower() == "#172554"
        assert win.style.accent_color.name().lower() == "#6366f1"
        assert win.style.accent_grad_end.name().lower() == "#06b6d4"
        assert "qlineargradient" in win.top_bar.styleSheet()
        assert "qlineargradient" in win.library_tree.tree.styleSheet()
        assert "qlineargradient" in win.photo_tray.styleSheet()

        # Vérifier que "Photos favorites (0)" dans l'arborescence prend bien alist_stickycolor à chaud
        if win.library_tree.cat_albums and win.library_tree.cat_albums.childCount() > 0:
            starred_item = win.library_tree.cat_albums.child(0)
            assert starred_item.background(0).color().name().lower() == "#1e1b4b"
            assert starred_item.foreground(0).color().name().lower() == "#f1f5f9"

        # Basculer sur le thème Sombre ("dark")
        win.apply_theme("dark")
        assert win.style.theme_id == "dark"
        assert win.style.is_dark is True
        assert win.menu_builder.theme_actions["dark"].isChecked()
        assert PicasaPreferences.get_theme_id() == "dark"
        assert win.palette().color(win.palette().ColorRole.Window).name().lower() == "#181a1f"
        assert win.one_up_view.canvas.style.grid_bgcolor.name().lower() == "#14161a"

        # Basculer via l'action du menu sur "ocean"
        win.menu_builder.theme_actions["ocean"].trigger()
        assert win.style.theme_id == "ocean"
        assert win.style.is_dark is False
        assert PicasaPreferences.get_theme_id() == "ocean"
        assert win.palette().color(win.palette().ColorRole.Window).name().lower() == "#e3eef6"
        assert win.photo_tray.style.tray_bgcolor.name().lower() == "#d4e6f1"
        assert win.right_drawer.style.drawer_bgcolor.name().lower() == "#e3eef6"
        assert win.one_up_view.canvas.style.grid_bgcolor.name().lower() == "#d8e6f2"

        # Basculer sur "sepia_warm" et "emerald_forest"
        win.apply_theme("sepia_warm")
        assert win.style.theme_id == "sepia_warm"
        assert win.palette().color(win.palette().ColorRole.Window).name().lower() == "#efe7da"
        assert win.photo_tray.style.tray_bgcolor.name().lower() == "#e5dac9"

        win.apply_theme("emerald_forest")
        assert win.style.theme_id == "emerald_forest"
        assert win.style.is_dark is False
        assert win.palette().color(win.palette().ColorRole.Window).name().lower() == "#e6f0ea"
        assert win.photo_tray.style.tray_bgcolor.name().lower() == "#d8e8df"

        # Revenir au thème original Picasa 3
        win.apply_theme("original")
        assert win.style.theme_id == "original"
        assert win.style.is_dark is False
        assert PicasaPreferences.get_theme_id() == "original"
        assert win.palette().color(win.palette().ColorRole.Window).name().lower() == "#f0f0f0"
        assert win.photo_tray.style.tray_bgcolor.name().lower() == "#e4e1d8"
        assert win.right_drawer.style.drawer_bgcolor.name().lower() == "#edeae4"
    finally:
        win.close()


def test_splash_screen_rendering():
    """
    FR: Vérifie que `PicasaSplashScreen` charge l'image officielle `ui/resources/splashbk.jpg`
    (640x235 px), affiche le titre de l'application et met à jour son statut.
    EN: Verify that `PicasaSplashScreen` loads the official `ui/resources/splashbk.jpg` image
    (640x235 px), displays the application title, and updates its status.
    """
    _ensure_qapp()
    assert SPLASH_BG_PATH.exists()

    splash = PicasaSplashScreen()
    assert splash.width() == 640
    assert splash.height() == 235
    assert splash.pixmap().width() == 640
    assert splash.pixmap().height() == 235

    splash.show()
    splash.set_status("Chargement des albums...")
    assert splash.status_text == "Chargement des albums..."
    splash.close()


def test_background_face_detection_and_scanner_workers(tmp_path: Path, monkeypatch):
    """
    FR: Vérifie le fonctionnement coordonné des workers d'arrière-plan de Picasa 3 :
    - `BackgroundScanWorker` (`AVytDirScannerWindows` @ 0x00415790) : indexation des nouveaux fichiers
      et ré-indexation des fichiers modifiés.
    - `BackgroundFaceDetectionWorker` (`BgFaceDetectThread` @ 0x0087ECD6) : détection automatique des
      visages sur les photos indexées non encore analysées, respect de `frexclude=1` (`0x00881690`),
      et persistance dans `.picasa.ini`.
    EN: Verify the coordinated operation of Picasa 3 background workers:
    - `BackgroundScanWorker` (`AVytDirScannerWindows` @ 0x00415790): indexing new files and re-indexing modified files.
    - `BackgroundFaceDetectionWorker` (`BgFaceDetectThread` @ 0x0087ECD6): automatic face detection on
      unscanned indexed photos, honoring `frexclude=1` (`0x00881690`), and persistence in `.picasa.ini`.
    """
    _ensure_qapp()
    from picasa_py.faces.face_manager import BackgroundFaceDetectionWorker
    from picasa_py.faces.detector import PicasaFaceDetector
    from picasa_py.faces.facerect import FaceRect
    from picasa_py.scanner.scanner import BackgroundScanWorker

    db = PicasaDatabase.create_new(tmp_path / "db_workers")
    watched_dir = tmp_path / "Portraits"
    watched_dir.mkdir()
    excluded_dir = tmp_path / "ExcludedFolder"
    excluded_dir.mkdir()

    # Marquer ExcludedFolder avec frexclude=1 dans [Picasa]
    (excluded_dir / ".picasa.ini").write_text("[Picasa]\r\nfrexclude=1\r\n", encoding="utf-8")

    img1 = watched_dir / "person1.jpg"
    img2 = excluded_dir / "ignored.jpg"
    Image.new("RGB", (120, 120), (210, 175, 150)).save(img1)
    Image.new("RGB", (120, 120), (210, 175, 150)).save(img2)

    # 1. Exécuter BackgroundScanWorker pour indexer les 2 dossiers
    scan_worker = BackgroundScanWorker(db, [str(watched_dir), str(excluded_dir)])
    scan_worker.run()
    assert len(db.index) == 4  # 2 dossiers + 2 images

    # 2. Simuler la détection d'un visage par PicasaFaceDetector
    monkeypatch.setattr(
        PicasaFaceDetector.get(),
        "detect_faces_in_file",
        lambda path: [FaceRect(0.25, 0.20, 0.75, 0.80)],
    )

    unscanned = db.face_manager.get_unscanned_photos()
    # Seul person1.jpg doit être candidat (ignored.jpg est dans un dossier frexclude=1)
    assert len(unscanned) == 1
    assert Path(unscanned[0][1]).name == "person1.jpg"

    # 3. Exécuter BackgroundFaceDetectionWorker (BgFaceDetectThread)
    face_worker = BackgroundFaceDetectionWorker(db, persist_ini=True)
    detected_events = []
    face_worker.faces_detected.connect(lambda idx, p, cnt: detected_events.append((idx, p, cnt)))
    face_worker.run()

    assert len(detected_events) == 1
    assert detected_events[0][2] == 1
    assert len(db.face_manager.unnamed_faces) == 1

    # Vérifier que person1.jpg n'est plus considéré comme "unscanned" au second passage
    assert len(db.face_manager.get_unscanned_photos()) == 0

    # Vérifier que le visage détecté a été persisté dans .picasa.ini
    ini_path = watched_dir / ".picasa.ini"
    assert ini_path.exists()
    doc = PicasaIniParser.parse_file(str(ini_path))
    sec = doc.get_section("person1.jpg")
    assert sec is not None
    assert "rect64(" in (sec.get("faces") or "")

