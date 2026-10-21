"""FR: Tests pour la boîte de dialogue d'options/préférences multi-onglets (PicasaOptionsDialog).
EN: Tests for Multi-tab Options/Preferences Dialog (PicasaOptionsDialog).
Ref: picasa3.exe @ ID_TOOLS_OPTIONS (0x0088C3EC), OPTIONS_FR.XML
"""

from PySide6.QtWidgets import QApplication
from picasa_py.ui.options_dialog import PicasaOptionsDialog
from picasa_py.ui.main_window import PicasaMainWindow


def test_options_dialog_tabs_and_structure(qapp):
    """FR: Vérifie la présence et le libellé des 7 onglets officiels de Picasa.
    EN: Verifies the presence and labels of Picasa's 7 official tabs.
    """
    from picasa_py.ui.resources import PicasaResourceManager
    res = PicasaResourceManager.get()
    prev_lang = res.get_current_language()
    try:
        res.set_language("fr")
        dlg = PicasaOptionsDialog()
        assert dlg.tabs.count() == 7

        tab_titles = [dlg.tabs.tabText(i) for i in range(7)]
        assert "Généralités" in tab_titles[0]
        assert "E-mail" in tab_titles[1]
        assert "Types de fichiers" in tab_titles[2]
        assert "Diaporama" in tab_titles[3]
        assert "Impression" in tab_titles[4]
        assert "Réseau" in tab_titles[5]
        assert "Tags de nom" in tab_titles[6]
    finally:
        res.set_language(prev_lang)


def test_options_dialog_controls_and_save(qapp):
    """FR: Vérifie la modification des réglages et leur sauvegarde dans QSettings.
    EN: Verifies modifying settings and saving them into QSettings.
    """
    from picasa_py.db.preferences import PicasaPreferences
    from picasa_py.ui.resources import PicasaResourceManager
    prefs = PicasaPreferences()
    res = PicasaResourceManager.get()
    keys = [
        "UI/Transitions", "Slideshow/Loop", "Faces/SuggestThreshold",
        "Faces/ClusterThreshold", "Slideshow/MusicPath", "UI/Language",
    ]
    saved_prefs = {k: prefs.value(k, None) for k in keys}
    try:
        dlg = PicasaOptionsDialog()

        # Modifier quelques paramètres
        dlg.chk_transitions.setChecked(False)
        dlg.chk_slideshow_loop.setChecked(True)
        dlg.slider_sugg.setValue(75)
        dlg.slider_cluster.setValue(90)
        dlg.txt_music_path.setText("C:/Musique/Diaporama")

        saved_payload = []
        dlg.settings_saved.connect(lambda s: saved_payload.append(s))

        data = dlg.save_settings()
        assert len(saved_payload) == 1
        assert data["ui_transitions"] is False
        assert data["slideshow_loop"] is True
        assert data["faces_suggest_threshold"] == 75
        assert data["faces_cluster_threshold"] == 90
        assert data["slideshow_music_path"] == "C:/Musique/Diaporama"

        # Vérifier le rechargement
        dlg2 = PicasaOptionsDialog()
        assert dlg2.chk_transitions.isChecked() is False
        assert dlg2.chk_slideshow_loop.isChecked() is True
        assert dlg2.slider_sugg.value() == 75
        assert dlg2.slider_cluster.value() == 90
        assert dlg2.txt_music_path.text() == "C:/Musique/Diaporama"
    finally:
        for k, v in saved_prefs.items():
            if v is None:
                prefs.remove(k)
            else:
                prefs.setValue(k, v)
        prefs.sync()
        res.set_language("system")


def test_main_window_has_options_action(qapp):
    """FR: Vérifie que MainWindow dispose de l'action action_options.
    EN: Verifies that MainWindow provides the action_options method.
    """
    assert hasattr(PicasaMainWindow, "action_options")
    assert callable(PicasaMainWindow.action_options)
