r"""FR: Tests unitaires pour la gestion de l'internationalisation et des 41 langues de Picasa 3.
EN: Unit tests for internationalization and management of Picasa 3's 41 languages.
Ref: AGENTS.md §4 bis.1 (Textes identiques, tables de chaînes et gestion des langues)
Ref: picasa3.exe @ 0x004060B0, 0x004055A0, i18n\langnames.xml, i18n\stringres.xml, options.fen
"""
import pytest
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.options_dialog import PicasaOptionsDialog


def test_langnames_loaded_all_41_languages():
    """FR: Vérifie que les 41 langues officielles de langnames.xml sont chargées dans PicasaResourceManager.
    EN: Verifies that all 41 official languages from langnames.xml are loaded in PicasaResourceManager.
    """
    res = PicasaResourceManager.get()
    langs = res.get_available_languages()
    
    assert len(langs) == 41, f"Expected 41 languages, got {len(langs)}"
    
    lang_dict = dict(langs)
    assert "fr" in lang_dict
    assert lang_dict["fr"] == "Français"
    assert "enUS" in lang_dict
    assert lang_dict["enUS"] == "English (US)"
    assert "de" in lang_dict
    assert lang_dict["de"] == "Deutsch"
    assert "es" in lang_dict
    assert lang_dict["es"] == "Español"
    assert "it" in lang_dict
    assert lang_dict["it"] == "Italiano"
    assert "ja" in lang_dict
    assert lang_dict["ja"] == "日本語"


def test_stringres_multilingual_translations():
    """FR: Vérifie les traductions multilingues des ressources de chaînes (fr, enUS, de, es).
    EN: Verifies multilingual string resource translations (fr, enUS, de, es).
    """
    res = PicasaResourceManager.get()
    
    # 1. Français
    res.set_language("fr")
    assert res.get_current_language() == "fr"
    fr_str = res.get_stringres("IDS_LAST_ALBUM_NOTIFY")
    assert "dernier dossier" in fr_str
    
    # 2. Anglais US
    res.set_language("enUS")
    assert res.get_current_language() == "enUS"
    en_str = res.get_stringres("IDS_LAST_ALBUM_NOTIFY")
    assert en_str == "You are on the last folder"
    
    # 3. Allemand
    res.set_language("de")
    assert res.get_current_language() == "de"
    de_str = res.get_stringres("IDS_LAST_ALBUM_NOTIFY")
    assert "letzten Ordner" in de_str
    
    # 4. Espagnol
    res.set_language("es")
    assert res.get_current_language() == "es"
    es_str = res.get_stringres("IDS_LAST_ALBUM_NOTIFY")
    assert "última carpeta" in es_str

    # Rétablir en français
    res.set_language("fr")


def test_options_dialog_language_dropdown(qapp):
    """FR: Vérifie la liste déroulante de sélection de langue et la persistance dans PicasaOptionsDialog.
    EN: Verifies the language selection dropdown and persistence in PicasaOptionsDialog.
    """
    from picasa_py.db.preferences import PicasaPreferences
    prefs = PicasaPreferences()
    orig_lang = prefs.value("UI/Language", None)
    res = PicasaResourceManager.get()
    try:
        res.set_language("fr")
        dlg = PicasaOptionsDialog()

        # Vérifier que le dropdown combo_language est présent
        assert hasattr(dlg, "combo_language")
        assert dlg.combo_language.count() >= 41

        # Vérifier l'élément par défaut ("system")
        assert dlg.combo_language.itemData(0) == "system"
        assert "Généralités" in dlg.tabs.tabText(0)
        assert dlg.btn_cancel.text() == "Annuler"

        # Sélectionner l'espagnol
        idx_es = dlg.combo_language.findData("es")
        assert idx_es > 0
        dlg.combo_language.setCurrentIndex(idx_es)

        data = dlg.save_settings()
        assert data["ui_language"] == "es"

        # Vérifier que le ResourceManager et la fenêtre Options ont bien basculé en espagnol
        assert res.get_current_language() == "es"
        assert dlg.tabs.tabText(0) == "General"
        assert dlg.btn_cancel.text() == "Cancelar"

        # Recharger dans une nouvelle boîte de dialogue (en espagnol)
        dlg2 = PicasaOptionsDialog()
        assert dlg2.combo_language.currentData() == "es"
        assert dlg2.tabs.tabText(0) == "General"
        assert dlg2.btn_cancel.text() == "Cancelar"

        # Repasser sur "system" ("Par défaut du système") et vérifier la résolution système
        dlg2.combo_language.setCurrentIndex(0)
        data_sys = dlg2.save_settings()
        assert data_sys["ui_language"] == "system"
        assert res.get_current_language() == res.resolve_system_language()
    finally:
        if orig_lang is None or orig_lang == "es":
            prefs.setValue("UI/Language", "system")
        else:
            prefs.setValue("UI/Language", orig_lang)
        prefs.sync()
        res.set_language("system")


def test_drawer_toggle_and_no_font_or_pil_warnings(qapp):
    """FR: Vérifie la bascule du tiroir droit et l'absence d'avertissements QFont ou PIL sur images palette.
    EN: Verifies right drawer toggling and the absence of QFont or PIL warnings on palette images.
    """
    import warnings
    from PIL import Image
    from PySide6.QtCore import qInstallMessageHandler
    from picasa_py.ui.main_window import PicasaMainWindow
    from picasa_py.faces.facerect import FaceRect

    qt_font_warnings = []
    prev_handler = qInstallMessageHandler(
        lambda t, c, m: qt_font_warnings.append(m) if "QFont::setPointSize:" in m else None
    )
    try:
        win = PicasaMainWindow(db_path="__non_existent__", auto_scan=False)
        # Bascule du tiroir droit via menu Affichage -> Tags (vérifie _is_expanded)
        win.action_toggle_drawer_panel("tags")
        assert win.right_drawer._is_expanded is False
        win.right_drawer.toggle_size()
        assert win.right_drawer._is_expanded is True
        win.action_toggle_drawer_panel("people")

        # Vérifie que l'ouverture du menu déroulant de langue n'émet aucun QFont::setPointSize <= 0
        dlg = PicasaOptionsDialog()
        dlg.show()
        dlg.combo_language.showPopup()
        qapp.processEvents()
        dlg.combo_language.hidePopup()
        dlg.close()
        win.close()
    finally:
        qInstallMessageHandler(prev_handler)

    assert qt_font_warnings == [], f"Unexpected QFont warnings: {qt_font_warnings}"

    # Vérifie qu'une image palette ('P') avec transparence en octets n'émet aucun UserWarning PIL
    pal_img = Image.new("P", (120, 120), 0)
    pal_img.putpalette([i % 256 for i in range(768)])
    pal_img.info["transparency"] = b"\x00\xff"
    fr = FaceRect(0.2, 0.2, 0.8, 0.8)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pix1 = FaceRect.to_avatar_pixmap(pal_img, avatar_size=64, circular=False)
        pix2 = fr.crop_avatar(pal_img, avatar_size=64, circular=True)
        assert not pix1.isNull()
        assert not pix2.isNull()
        pil_trans_warnings = [w for w in caught if "Palette images with Transparency" in str(w.message)]
        assert pil_trans_warnings == []
