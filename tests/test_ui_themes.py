"""
FR: Tests unitaires de propagation dynamique des thèmes (PicasaStyle) sur tous les composants GUI :
- Onglets d'édition (Retouches, Réglages, Effets 1, Effets 2, Effets 3) et sous-panneaux
- Carte d'informations de l'appareil photo (PicasaCameraInfoCard) et Histogramme (PicasaHistogramWidget)
- Tiroir latéral droit (PicasaRightDrawer : Personnes/Suggestions, Lieux, Tags/Tags rapides, Propriétés)
- Plateau inférieur (PicasaPhotoTray, bande de miniatures, bouton favori)
- Vue One-Up (PicasaOneUpView, lecteur vidéo PicasaVideoPlayer)
- En-têtes de sections de la grille (PicasaThumbnailView)
EN: Unit tests for dynamic theme propagation (PicasaStyle) across all GUI components:
- Editing tabs (Basic Fixes, Tuning, Effects 1, Effects 2, Effects 3) and subpanels
- Camera Info Card (PicasaCameraInfoCard) and Histogram (PicasaHistogramWidget)
- Right-hand side drawer (PicasaRightDrawer: People/Suggestions, Places, Tags/Quick Tags, Properties)
- Bottom Photo Tray (PicasaPhotoTray, thumbnail strip, star button)
- One-Up View (PicasaOneUpView, video player PicasaVideoPlayer)
- Grid section headers (PicasaThumbnailView)
"""

from __future__ import annotations
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QScrollArea

from picasa_py.faces.facerect import FaceRect
from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.edit_panel import PicasaEditPanel
from picasa_py.ui.right_drawer import PicasaRightDrawer
from picasa_py.ui.photo_tray import PicasaPhotoTray
from picasa_py.ui.one_up_view import PicasaOneUpView


THEMES = ["original", "dark", "ocean", "sepia_warm", "emerald_forest"]


@pytest.fixture(scope="module")
def qapp():
    """
    FR: Fournit une instance partagée de QApplication pour le module de tests.
    EN: Provide a shared QApplication instance for the test module.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_edit_panel_tabs_and_camera_card_follow_all_themes(qapp):
    """
    FR: Vérifie que Réglages, Effets 1/2/3, Retouches, l'histogramme et les infos appareil suivent chaque thème.
    EN: Verify that Tuning, Effects 1/2/3, Basic Fixes, the histogram, and camera info follow every theme.
    """
    panel = PicasaEditPanel()

    # Vérifier que les QScrollArea de Réglages et Effets 1/2/3 ont bien les objectNames attendus
    scroll_areas = panel.tabs.findChildren(QScrollArea, "TabScrollArea")
    assert len(scroll_areas) == 4  # Réglages, Effets 1, Effets 2, Effets 3
    scroll_contents = panel.tabs.findChildren(QWidget, "TabScrollContent")
    assert len(scroll_contents) >= 4
    for sc in scroll_contents:
        assert sc.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    for theme_id in THEMES:
        style = PicasaStyle.load_theme(theme_id)
        panel.apply_style(style)

        expected_pane_bg = style.alist_bgcolor.name() if style.is_dark else style.window_bgcolor.name()
        assert f"background-color: {expected_pane_bg}" in panel.styleSheet()
        assert "QWidget#TabScrollContent" in panel.styleSheet()

        # Carte d'informations de l'appareil photo
        assert panel.camera_info_card.style.theme_id == theme_id
        card_ss = panel.camera_info_card.styleSheet().lower()
        assert style.alist_textcolor.name().lower() in card_ss
        assert style.splitter_color.name().lower() in card_ss

        # Histogramme
        assert panel.histogram_widget.style.theme_id == theme_id
        assert panel.histogram_widget.style.is_dark == style.is_dark


def test_right_drawer_panels_and_face_suggestions_follow_all_themes(qapp):
    """
    FR: Vérifie que Personnes (suggestions/visages), Lieux, Tags et Propriétés suivent chaque thème.
    EN: Verify that People (suggestions/faces), Places, Tags, and Properties follow every theme.
    """
    drawer = PicasaRightDrawer()

    # Injecter des données de test dans le panneau Personnes (visages nommés, inconnu, suggestion)
    f_named = FaceRect(0.1, 0.1, 0.3, 0.3, contact_id="c1", contact_name="Alice")
    f_sug = FaceRect(0.4, 0.1, 0.6, 0.3)
    f_sug.suggested_contact_id = "c1"
    f_sug.suggested_contact_name = "Alice"
    f_unnamed = FaceRect(0.7, 0.1, 0.9, 0.3)

    drawer.panel_people.set_photo_faces(None, 0, "", [f_named, f_sug, f_unnamed])

    for theme_id in THEMES:
        style = PicasaStyle.load_theme(theme_id)
        drawer.apply_style(style)

        assert drawer.panel_people.style.theme_id == theme_id
        assert drawer.panel_places.style.theme_id == theme_id
        assert drawer.panel_tags.style.theme_id == theme_id
        assert drawer.panel_properties.style.theme_id == theme_id
        assert drawer.panel_properties.histogram_widget.style.theme_id == theme_id

        colors = drawer.panel_people._theme_colors()
        assert colors["btn_bg"].lower() == style.topbar_btn_bg_start.name().lower()
        assert style.drawer_bgcolor.name().lower() in drawer.panel_people.scroll.styleSheet().lower()


def test_photo_tray_and_one_up_view_follow_all_themes(qapp):
    """
    FR: Vérifie que PicasaPhotoTray et PicasaOneUpView propagent tous les thèmes.
    EN: Verify that PicasaPhotoTray and PicasaOneUpView propagate all themes.
    """
    tray = PicasaPhotoTray()
    one_up = PicasaOneUpView()

    for theme_id in THEMES:
        style = PicasaStyle.load_theme(theme_id)
        tray.apply_style(style)
        one_up.apply_style(style)

        assert tray.style.theme_id == theme_id
        assert one_up.style.theme_id == theme_id
        assert one_up.edit_panel.style.theme_id == theme_id
        assert one_up.right_drawer.style.theme_id == theme_id
        assert one_up.video_player.style.theme_id == theme_id
