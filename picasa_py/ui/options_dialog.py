"""
FR: Boîte de dialogue Préférences / Options multi-onglets pour PyCasa.
EN: Multi-tab Options / Preferences Dialog for PyCasa.
Re-implements Picasa 3's options dialog matching exact strings and tab structure.

Ref: picasa3.exe @ ID_TOOLS_OPTIONS (0x0088C3EC)
Ref: ui/resources/xml/OPTIONS_FR.XML, OPTIONS.XML
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QCheckBox, QRadioButton, QButtonGroup, QSlider,
    QLineEdit, QFileDialog, QGroupBox, QGridLayout, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.preferences import PicasaPreferences


class PicasaOptionsDialog(QDialog):
    """
    FR: Boîte de dialogue Préférences / Options à 7 onglets de Picasa 3.
    EN: Picasa 3 7-tab Preferences / Options dialog.
    Ref: options.fen, OPTIONS_FR.XML
    """
    settings_saved = Signal(dict)

    def _tr(self, xml_id: str, default: str = "") -> str:
        """
        FR: Récupère une chaîne traduite depuis les fichiers XML officiels.
        EN: Retrieves a translated string from the official XML files.
        """
        return self.res_mgr.get_xml_string(xml_id, default)

    def __init__(self, parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        """
        FR: Initialise la boîte de dialogue d'options à 7 onglets et charge les préférences enregistrées.
        EN: Initializes the 7-tab options dialog and loads saved preferences.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()
        self.settings = PicasaPreferences()

        self.setWindowTitle(self._tr("options/window1.win_title", "Options"))
        self.resize(560, 480)
        self.setMinimumSize(500, 420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._create_general_tab(), self._tr("options/tab3.title", "Généralités"))
        self.tabs.addTab(self._create_email_tab(), self._tr("options/tab36.title", "E-mail"))
        self.tabs.addTab(self._create_filetypes_tab(), self._tr("options/tab59.title", "Types de fichiers"))
        self.tabs.addTab(self._create_slideshow_tab(), self._tr("options/tab97.title", "Diaporama"))
        self.tabs.addTab(self._create_printing_tab(), self._tr("options/tab106.title", "Impression"))
        self.tabs.addTab(self._create_network_tab(), self._tr("options/tab128.title", "Réseau"))
        self.tabs.addTab(self._create_nametags_tab(), self._tr("options/tab169.title", "Tags de nom"))

        main_layout.addWidget(self.tabs, 1)

        # FR: Boutons OK / Annuler / Appliquer
        # EN: OK / Cancel / Apply buttons
        btns_layout = QHBoxLayout()
        btns_layout.addStretch(1)

        self.btn_ok = QPushButton(self._tr("options/button189.title", "OK"))
        self.btn_ok.setObjectName("PrimaryBtn")
        self.btn_ok.clicked.connect(self._on_ok)
        btns_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(self._tr("options/button190.title", "Annuler"))
        self.btn_cancel.setObjectName("SecondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btns_layout.addWidget(self.btn_cancel)

        self.btn_apply = QPushButton(self.res_mgr.get_stringres("Apply", "Appliquer"))
        self.btn_apply.setObjectName("SecondaryBtn")
        self.btn_apply.clicked.connect(self.save_settings)
        btns_layout.addWidget(self.btn_apply)

        main_layout.addLayout(btns_layout)

        # FR: Chargement des réglages enregistrés et application du thème actif
        # EN: Load saved settings and apply active theme
        self.load_settings()
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème PicasaStyle à la boîte de dialogue Options.
        EN: Dynamically applies the PicasaStyle theme to the Options dialog.
        """
        self.style = style or PicasaStyle.instance()
        s = self.style
        dlg_bg = s.window_bgcolor.name() if s.is_dark else "#EDEAE4"
        pane_bg = s.alist_bgcolor.name() if s.is_dark else "#F8F7F4"
        tab_bg = s.alist_catcolor.name() if s.is_dark else "#DDD9D0"
        border_col = s.splitter_color.name() if s.is_dark else "#BFBAB0"
        txt_col = s.alist_textcolor.name() if s.is_dark else "#111111"
        input_bg = s.thumb_card_bgcolor.name() if s.is_dark else "#FFFFFF"
        btn_bg = s.topbar_btn_bg_start.name() if s.is_dark else "#FFFFFF"
        btn_hover = s.topbar_btn_bg_end.name() if s.is_dark else "#F0EEE9"
        accent = s.accent_color.name()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {txt_col};
            }}
            QTabWidget::pane {{
                border: 1px solid {border_col};
                background-color: {pane_bg};
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {tab_bg};
                border: 1px solid {border_col};
                padding: 6px 10px;
                font-size: 11px;
                color: {txt_col};
            }}
            QTabBar::tab:selected {{
                background-color: {pane_bg};
                border-bottom-color: {pane_bg};
                color: {txt_col};
                font-weight: bold;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {border_col};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 12px;
                font-size: 11px;
                color: {txt_col};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: {txt_col};
            }}
            QCheckBox, QRadioButton, QLabel {{
                font-size: 11px;
                color: {txt_col};
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {txt_col};
                border: 1px solid {border_col};
                border-radius: 3px;
                padding: 4px;
                font-size: 11px;
            }}
            QComboBox {{
                background-color: {input_bg};
                border: 1px solid {border_col};
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
                color: {txt_col};
                min-height: 24px;
            }}
            QComboBox:hover {{
                border-color: {accent};
            }}
            QComboBox:focus {{
                border: 2px solid {accent};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid {border_col};
                background-color: {tab_bg};
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }}
            QComboBox::down-arrow {{
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {txt_col};
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                border: 1px solid {border_col};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                color: {txt_col};
                font-size: 9pt;
                padding: 2px;
            }}
            QPushButton#PrimaryBtn {{
                background-color: {accent};
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 16px;
                border: 1px solid {accent};
                font-size: 11px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {s.accent_color.lighter(115).name()};
            }}
            QPushButton#SecondaryBtn {{
                background-color: {btn_bg};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11px;
                color: {txt_col};
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {btn_hover};
                color: {txt_col};
            }}
        """)


    def _create_general_tab(self) -> QWidget:
        """
        FR: Construit l'onglet « Généralités » (interface utilisateur, fichiers, mises à jour, langue).
        EN: Builds the "General" tab (user interface, files, automatic updates, language).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # FR: 1. Interface utilisateur / EN: 1. User interface
        self.grp_ui = QGroupBox(self._tr("options/labelgroup4.title", "Interface utilisateur :"))
        ui_layout = QVBoxLayout(self.grp_ui)
        self.chk_transitions = QCheckBox(self._tr("options/UITransitions.title", "Utiliser des effets spéciaux"))
        self.chk_tooltips = QCheckBox(self._tr("options/ShowTooltips.title", "Afficher les info-bulles"))
        self.chk_single_click = QCheckBox(self._tr("options/SingleClickExit.title", "Cliquer une seule fois pour quitter le centre de retouches"))
        ui_layout.addWidget(self.chk_transitions)
        ui_layout.addWidget(self.chk_tooltips)
        ui_layout.addWidget(self.chk_single_click)
        layout.addWidget(self.grp_ui)

        # FR: 2. Fichiers / EN: 2. Files
        self.grp_files = QGroupBox(self._tr("options/labelgroup10.title", "Fichiers :"))
        files_layout = QVBoxLayout(self.grp_files)
        self.chk_autoexclude = QCheckBox(self._tr("options/autoexclude.title", "Détection de doublons lors de l'importation"))
        self.chk_no_confirm_del = QCheckBox(self._tr("options/DoNotConfirmDeleteFromDisk.title", "Supprimer du disque sans confirmation"))
        self.chk_no_confirm_album = QCheckBox(self._tr("options/DoNotConfirmRemoveFromAlbum.title", "Supprimer de l'album sans confirmation"))
        files_layout.addWidget(self.chk_autoexclude)
        files_layout.addWidget(self.chk_no_confirm_del)
        files_layout.addWidget(self.chk_no_confirm_album)
        layout.addWidget(self.grp_files)

        # FR: 3. Mises à jour automatiques / EN: 3. Automatic updates
        self.grp_updates = QGroupBox(self._tr("options/labelgroup20.title", "Mises à jour automatiques :"))
        up_layout = QVBoxLayout(self.grp_updates)
        self.rb_update_auto = QRadioButton(self._tr("options/item22.title", "Mettre à jour automatiquement"))
        self.rb_update_ask = QRadioButton(self._tr("options/item23.title", "Demander confirmation avant le téléchargement des mises à jour"))
        self.rb_update_never = QRadioButton(self._tr("options/item24.title", "Ne pas rechercher les mises à jour"))
        self.update_group = QButtonGroup(self)
        self.update_group.addButton(self.rb_update_auto, 0)
        self.update_group.addButton(self.rb_update_ask, 1)
        self.update_group.addButton(self.rb_update_never, 2)
        up_layout.addWidget(self.rb_update_auto)
        up_layout.addWidget(self.rb_update_ask)
        up_layout.addWidget(self.rb_update_never)
        layout.addWidget(self.grp_updates)

        # FR: 4. Langue de l'interface / EN: 4. UI Language (Ref: options.fen line 32, 0x004060B0, Local::lang)
        self.grp_lang = QGroupBox(self._tr("options/labelgroup25.title", "Langue :"))
        lang_layout = QVBoxLayout(self.grp_lang)
        self.combo_language = QComboBox()
        sys_lang = self.res_mgr.resolve_system_language()
        sys_label = self._tr("options/item27.title", "Par défaut du système")
        if "(en-US)" in sys_label:
            sys_label = sys_label.replace("(en-US)", f"({sys_lang})")
        self.combo_language.addItem(sys_label, "system")
        for code, name in self.res_mgr.get_available_languages():
            self.combo_language.addItem(f"{name} ({code})", code)
        lang_layout.addWidget(self.combo_language)
        layout.addWidget(self.grp_lang)

        layout.addStretch(1)
        return w

    def _create_email_tab(self) -> QWidget:
        """
        FR: Construit l'onglet « E-mail » (programme de messagerie et taille des pièces jointes).
        EN: Builds the "E-mail" tab (mail client selection and attachment image size).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.grp_mailer = QGroupBox(self._tr("options/labelgroup38.title", "Programme de messagerie :"))
        m_layout = QVBoxLayout(self.grp_mailer)
        self.rb_mail_ask = QRadioButton(self._tr("options/radio40.title", "Choisir à chaque envoi de photos"))
        self.rb_mail_default = QRadioButton(self._tr("options/defaultmail.title", "Utiliser le programme de messagerie par défaut de mon ordinateur"))
        self.rb_mail_google = QRadioButton(self._tr("options/radio42.title", "Utiliser mon compte Google"))
        self.mail_group = QButtonGroup(self)
        self.mail_group.addButton(self.rb_mail_ask, 0)
        self.mail_group.addButton(self.rb_mail_default, 1)
        self.mail_group.addButton(self.rb_mail_google, 2)
        m_layout.addWidget(self.rb_mail_ask)
        m_layout.addWidget(self.rb_mail_default)
        m_layout.addWidget(self.rb_mail_google)
        layout.addWidget(self.grp_mailer)

        self.grp_mail_size = QGroupBox(self._tr("options/labelgroup43.title", "Taille pour plusieurs photos :"))
        s_layout = QVBoxLayout(self.grp_mail_size)
        self.cb_mail_size = QComboBox()
        orig_lbl = self._tr("options/radio52.title", "Taille d'origine")
        rec_lbl = self._tr("options/label153.title", "(recommandé)")
        px_fmt = self._tr("options/bind47.format", "%s pixels")
        self.cb_mail_size.addItems([
            px_fmt.replace("%s", "640"),
            px_fmt.replace("%s", "800"),
            f"{px_fmt.replace('%s', '1024')} {rec_lbl}",
            px_fmt.replace("%s", "1600"),
            orig_lbl,
        ])
        s_layout.addWidget(self.cb_mail_size)
        layout.addWidget(self.grp_mail_size)

        layout.addStretch(1)
        return w

    def _create_filetypes_tab(self) -> QWidget:
        """
        FR: Construit l'onglet « Types de fichiers » permettant de cocher les extensions prises en charge.
        EN: Builds the "File Types" tab allowing selection of supported media file extensions.
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.lbl_ft_desc = QLabel(self._tr("options/label61.title", "Afficher les fichiers JPEG et :"))
        self.lbl_ft_desc.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_ft_desc)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.ft_checkboxes: Dict[str, QCheckBox] = {}
        formats = [
            ("bmp", self._tr("options/SupportBMP.title", ".BMP")),
            ("gif", self._tr("options/SupportGIF.title", ".GIF")),
            ("png", self._tr("options/SupportPNG.title", ".PNG")),
            ("tga", self._tr("options/SupportTGA.title", ".TGA")),
            ("tiff", self._tr("options/SupportTIF.title", ".TIF, .TIFF")),
            ("webp", self._tr("options/SupportWEBP.title", ".WEBP")),
            ("psd", self._tr("options/SupportPSD.title", ".PSD (Photoshop)")),
            ("raw", self._tr("options/SupportRAW.title", "Formats RAW")),
            ("movies", self._tr("options/SupportMovies.title", "Vidéos (.AVI, .MPG, .ASF, .WMV)")),
        ]

        for i, (ext_id, label) in enumerate(formats):
            chk = QCheckBox(label)
            chk.setChecked(True)
            self.ft_checkboxes[ext_id] = chk
            grid.addWidget(chk, i // 2, i % 2)

        layout.addLayout(grid)

        # FR: Boutons Tout cocher / Décocher
        # EN: Select All / Select None buttons
        h_sel = QHBoxLayout()
        self.btn_ft_all = QPushButton(self.res_mgr.get_stringres("SelectAll", "Tout sélectionner"))
        self.btn_ft_all.setObjectName("SecondaryBtn")
        self.btn_ft_all.clicked.connect(lambda: [c.setChecked(True) for c in self.ft_checkboxes.values()])
        h_sel.addWidget(self.btn_ft_all)

        self.btn_ft_none = QPushButton(self.res_mgr.get_stringres("SelectNone", "Tout désélectionner"))
        self.btn_ft_none.setObjectName("SecondaryBtn")
        self.btn_ft_none.clicked.connect(lambda: [c.setChecked(False) for c in self.ft_checkboxes.values()])
        h_sel.addWidget(self.btn_ft_none)
        h_sel.addStretch(1)
        layout.addLayout(h_sel)

        layout.addStretch(1)
        return w

    def _create_slideshow_tab(self) -> QWidget:
        """
        FR: Construit l'onglet « Diaporama » (lecture en boucle, musique de fond et dossier MP3).
        EN: Builds the "Slideshow" tab (looping playback, background music, and MP3 folder path).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.chk_slideshow_loop = QCheckBox(self._tr("options/LoopSlideshow.title", "Diaporama en boucle"))
        layout.addWidget(self.chk_slideshow_loop)

        self.chk_slideshow_music = QCheckBox(self._tr("options/PlayMP3Tracks.title", "Jouer de la musique pendant le diaporama"))
        layout.addWidget(self.chk_slideshow_music)

        self.grp_music = QGroupBox(self._tr("options/label104.title", "Sélectionner un dossier de pistes musicales :"))
        m_layout = QHBoxLayout(self.grp_music)
        self.txt_music_path = QLineEdit()
        m_layout.addWidget(self.txt_music_path)

        self.btn_browse_music = QPushButton(self._tr("options/MP3SlideshowPath.title", "Parcourir..."))
        self.btn_browse_music.setObjectName("SecondaryBtn")
        self.btn_browse_music.clicked.connect(self._on_browse_music)
        m_layout.addWidget(self.btn_browse_music)
        layout.addWidget(self.grp_music)

        layout.addStretch(1)
        return w

    def _create_printing_tab(self) -> QWidget:
        """
        FR: Construit l'onglet « Impression » (aperçus, qualité d'impression et filtre Lanczos).
        EN: Builds the "Printing" tab (previews, print resolution quality, and Lanczos resampling).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.grp_prev = QGroupBox(self._tr("options/labelgroup118.title", "Aperçus :"))
        p_layout = QVBoxLayout(self.grp_prev)
        self.chk_high_res_preview = QCheckBox(self._tr("options/PrintProxyPreview.title", "Utiliser des aperçus haute qualité (plus lent)"))
        p_layout.addWidget(self.chk_high_res_preview)
        layout.addWidget(self.grp_prev)

        self.grp_qual = QGroupBox(self._tr("options/labelgroup120.title", "Qualité d'impression :"))
        q_layout = QVBoxLayout(self.grp_qual)
        self.rb_print_high = QRadioButton(self._tr("options/radio123.title", "Haute qualité (résolution maximale)"))
        self.rb_print_compat = QRadioButton(self._tr("options/radio122.title", "Compatible (résolution deux fois inférieure)"))
        self.print_qual_group = QButtonGroup(self)
        self.print_qual_group.addButton(self.rb_print_high, 0)
        self.print_qual_group.addButton(self.rb_print_compat, 1)
        q_layout.addWidget(self.rb_print_high)
        q_layout.addWidget(self.rb_print_compat)
        layout.addWidget(self.grp_qual)

        self.grp_resample = QGroupBox(self._tr("options/labelgroup124.title", "Qualité de rééchantillonnage à l'impression :"))
        r_layout = QVBoxLayout(self.grp_resample)
        self.rb_resample_std = QRadioButton(self._tr("options/radio126.title", "Général (Lanczos-3)"))
        self.rb_resample_sharp = QRadioButton(self._tr("options/radio127.title", "Extra netteté (Lanczos-8)"))
        self.resample_group = QButtonGroup(self)
        self.resample_group.addButton(self.rb_resample_std, 0)
        self.resample_group.addButton(self.rb_resample_sharp, 1)
        r_layout.addWidget(self.rb_resample_std)
        r_layout.addWidget(self.rb_resample_sharp)
        layout.addWidget(self.grp_resample)

        layout.addStretch(1)
        return w

    def _create_network_tab(self) -> QWidget:
        """
        FR: Construit l'onglet « Réseau » (détection automatique du proxy et niveau de journalisation).
        EN: Builds the "Network" tab (automatic proxy detection and network logging level).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.chk_autoproxy = QCheckBox(self._tr("options/autoproxy.title", "Détecter automatiquement les paramètres réseau"))
        layout.addWidget(self.chk_autoproxy)

        self.grp_log = QGroupBox(self._tr("options/labelgroup135.title", "Niveau journal réseau :"))
        l_layout = QVBoxLayout(self.grp_log)
        self.cb_net_log = QComboBox()
        self.cb_net_log.addItems([
            self._tr("options/item137.title", "Désactiver la consignation dans le journal"),
            self._tr("options/item138.title", "Consigner uniquement les erreurs"),
            self._tr("options/item139.title", "Informations de journal minimales"),
            self._tr("options/item140.title", "Informations de journal détaillées"),
            self._tr("options/item141.title", "Consigner toutes les informations réseau"),
        ])
        l_layout.addWidget(self.cb_net_log)
        layout.addWidget(self.grp_log)

        layout.addStretch(1)
        return w

    def _create_nametags_tab(self) -> QWidget:
        """
        FR: Construit l'onglet « Tags de nom » (détection des visages, seuils de suggestion/cluster, XMP et moteur Red.dll).
        EN: Builds the "Name Tags" tab (face detection, suggestion/cluster thresholds, XMP persistence, and Red.dll engine).
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.chk_facedetect = QCheckBox(self._tr("options/enablefacedetection.title", "Activer la détection des visages"))
        self.chk_facesuggest = QCheckBox(self._tr("options/enablefacesuggestions.title", "Activer les suggestions :"))
        layout.addWidget(self.chk_facedetect)
        layout.addWidget(self.chk_facesuggest)

        # FR: Seuil de suggestion / EN: Suggestion threshold
        self.grp_thresh = QGroupBox(self._tr("options/tab169.title", "Tags de nom"))
        t_layout = QVBoxLayout(self.grp_thresh)

        h_sugg = QHBoxLayout()
        self.lbl_sugg_title = QLabel(self._tr("options/labelgroup176.title", "Seuil de la suggestion :"))
        h_sugg.addWidget(self.lbl_sugg_title)
        self.lbl_sugg_val = QLabel("70 %")
        self.lbl_sugg_val.setStyleSheet("font-weight: bold; color: #25648B;")
        h_sugg.addStretch()
        h_sugg.addWidget(self.lbl_sugg_val)
        t_layout.addLayout(h_sugg)

        self.slider_sugg = QSlider(Qt.Orientation.Horizontal)
        self.slider_sugg.setRange(50, 95)
        self.slider_sugg.setValue(70)
        self.slider_sugg.valueChanged.connect(lambda v: self.lbl_sugg_val.setText(f"{v} %"))
        t_layout.addWidget(self.slider_sugg)

        h_cluster = QHBoxLayout()
        self.lbl_cluster_title = QLabel(self._tr("options/labelgroup181.title", "Seuil du cluster :"))
        h_cluster.addWidget(self.lbl_cluster_title)
        self.lbl_cluster_val = QLabel("85 %")
        self.lbl_cluster_val.setStyleSheet("font-weight: bold; color: #25648B;")
        h_cluster.addStretch()
        h_cluster.addWidget(self.lbl_cluster_val)
        t_layout.addLayout(h_cluster)

        self.slider_cluster = QSlider(Qt.Orientation.Horizontal)
        self.slider_cluster.setRange(50, 95)
        self.slider_cluster.setValue(85)
        self.slider_cluster.valueChanged.connect(lambda v: self.lbl_cluster_val.setText(f"{v} %"))
        t_layout.addWidget(self.slider_cluster)

        layout.addWidget(self.grp_thresh)

        self.chk_persist_xmp = QCheckBox(self._tr("options/persistfacetofile.title", "Enregistrer les tags associés à un nom de la photo"))
        layout.addWidget(self.chk_persist_xmp)

        # FR: Sélection du moteur d'exécution Red.dll / red.cfg (Natif 32 bits vs Python pur désassemblé)
        # EN: Red.dll / red.cfg execution engine selection (Native 32-bit vs pure disassembled Python)
        self.grp_engine = QGroupBox("Moteur d'exécution de reconnaissance faciale (Red.dll / red.cfg) :")
        eng_layout = QVBoxLayout(self.grp_engine)
        self.cb_face_engine = QComboBox()
        self.cb_face_engine.addItem(
            "Moteur original natif 32 bits (plugins\\Red.dll + plugins\\red.cfg)",
            "native",
        )
        self.cb_face_engine.addItem(
            "Moteur Red.dll désassemblé en Python/NumPy pur (plugins\\red.cfg)",
            "python",
        )
        eng_layout.addWidget(self.cb_face_engine)
        layout.addWidget(self.grp_engine)

        layout.addStretch(1)
        return w

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour dynamiquement tous les libellés de la boîte de dialogue selon la langue active.
        EN: Dynamically updates all dialog labels according to the active language.
        """
        self.setWindowTitle(self._tr("options/window1.win_title", "Options"))
        self.tabs.setTabText(0, self._tr("options/tab3.title", "Généralités"))
        self.tabs.setTabText(1, self._tr("options/tab36.title", "E-mail"))
        self.tabs.setTabText(2, self._tr("options/tab59.title", "Types de fichiers"))
        self.tabs.setTabText(3, self._tr("options/tab97.title", "Diaporama"))
        self.tabs.setTabText(4, self._tr("options/tab106.title", "Impression"))
        self.tabs.setTabText(5, self._tr("options/tab128.title", "Réseau"))
        self.tabs.setTabText(6, self._tr("options/tab169.title", "Tags de nom"))

        self.btn_ok.setText(self._tr("options/button189.title", "OK"))
        self.btn_cancel.setText(self._tr("options/button190.title", "Annuler"))
        self.btn_apply.setText(self.res_mgr.get_stringres("Apply", "Appliquer"))

        self.grp_ui.setTitle(self._tr("options/labelgroup4.title", "Interface utilisateur :"))
        self.chk_transitions.setText(self._tr("options/UITransitions.title", "Utiliser des effets spéciaux"))
        self.chk_tooltips.setText(self._tr("options/ShowTooltips.title", "Afficher les info-bulles"))
        self.chk_single_click.setText(self._tr("options/SingleClickExit.title", "Cliquer une seule fois pour quitter le centre de retouches"))

        self.grp_files.setTitle(self._tr("options/labelgroup10.title", "Fichiers :"))
        self.chk_autoexclude.setText(self._tr("options/autoexclude.title", "Détection de doublons lors de l'importation"))
        self.chk_no_confirm_del.setText(self._tr("options/DoNotConfirmDeleteFromDisk.title", "Supprimer du disque sans confirmation"))
        self.chk_no_confirm_album.setText(self._tr("options/DoNotConfirmRemoveFromAlbum.title", "Supprimer de l'album sans confirmation"))

        self.grp_updates.setTitle(self._tr("options/labelgroup20.title", "Mises à jour automatiques :"))
        self.rb_update_auto.setText(self._tr("options/item22.title", "Mettre à jour automatiquement"))
        self.rb_update_ask.setText(self._tr("options/item23.title", "Demander confirmation avant le téléchargement des mises à jour"))
        self.rb_update_never.setText(self._tr("options/item24.title", "Ne pas rechercher les mises à jour"))

        self.grp_lang.setTitle(self._tr("options/labelgroup25.title", "Langue :"))
        sys_lang = self.res_mgr.resolve_system_language()
        sys_label = self._tr("options/item27.title", "Par défaut du système")
        if "(en-US)" in sys_label:
            sys_label = sys_label.replace("(en-US)", f"({sys_lang})")
        if self.combo_language.count() > 0:
            self.combo_language.setItemText(0, sys_label)

        self.grp_mailer.setTitle(self._tr("options/labelgroup38.title", "Programme de messagerie :"))
        self.rb_mail_ask.setText(self._tr("options/radio40.title", "Choisir à chaque envoi de photos"))
        self.rb_mail_default.setText(self._tr("options/defaultmail.title", "Utiliser le programme de messagerie par défaut de mon ordinateur"))
        self.rb_mail_google.setText(self._tr("options/radio42.title", "Utiliser mon compte Google"))
        self.grp_mail_size.setTitle(self._tr("options/labelgroup43.title", "Taille pour plusieurs photos :"))

        self.lbl_ft_desc.setText(self._tr("options/label61.title", "Afficher les fichiers JPEG et :"))
        self.chk_slideshow_loop.setText(self._tr("options/LoopSlideshow.title", "Diaporama en boucle"))
        self.chk_slideshow_music.setText(self._tr("options/PlayMP3Tracks.title", "Jouer de la musique pendant le diaporama"))
        self.grp_music.setTitle(self._tr("options/label104.title", "Sélectionner un dossier de pistes musicales :"))
        self.btn_browse_music.setText(self._tr("options/MP3SlideshowPath.title", "Parcourir..."))

        self.grp_prev.setTitle(self._tr("options/labelgroup118.title", "Aperçus :"))
        self.chk_high_res_preview.setText(self._tr("options/PrintProxyPreview.title", "Utiliser des aperçus haute qualité (plus lent)"))
        self.grp_qual.setTitle(self._tr("options/labelgroup120.title", "Qualité d'impression :"))
        self.rb_print_high.setText(self._tr("options/radio123.title", "Haute qualité (résolution maximale)"))
        self.rb_print_compat.setText(self._tr("options/radio122.title", "Compatible (résolution deux fois inférieure)"))
        self.grp_resample.setTitle(self._tr("options/labelgroup124.title", "Qualité de rééchantillonnage à l'impression :"))
        self.rb_resample_std.setText(self._tr("options/radio126.title", "Général (Lanczos-3)"))
        self.rb_resample_sharp.setText(self._tr("options/radio127.title", "Extra netteté (Lanczos-8)"))

        self.chk_autoproxy.setText(self._tr("options/autoproxy.title", "Détecter automatiquement les paramètres réseau"))
        self.grp_log.setTitle(self._tr("options/labelgroup135.title", "Niveau journal réseau :"))

        self.chk_facedetect.setText(self._tr("options/enablefacedetection.title", "Activer la détection des visages"))
        self.chk_facesuggest.setText(self._tr("options/enablefacesuggestions.title", "Activer les suggestions :"))
        self.grp_thresh.setTitle(self._tr("options/tab169.title", "Tags de nom"))
        self.lbl_sugg_title.setText(self._tr("options/labelgroup176.title", "Seuil de la suggestion :"))
        self.lbl_cluster_title.setText(self._tr("options/labelgroup181.title", "Seuil du cluster :"))
        self.chk_persist_xmp.setText(self._tr("options/persistfacetofile.title", "Enregistrer les tags associés à un nom de la photo"))

    def _on_browse_music(self) -> None:
        """
        FR: Ouvre un sélecteur de répertoire pour choisir le dossier de musique du diaporama.
        EN: Opens a directory picker dialog to select the slideshow music folder.
        """
        folder = QFileDialog.getExistingDirectory(self, self._tr("options/label104.title", "Sélectionner le dossier de musique"))
        if folder:
            self.txt_music_path.setText(folder)

    def load_settings(self) -> None:
        """
        FR: Charge les préférences depuis PicasaPreferences avec les valeurs par défaut de Picasa 3.
        EN: Loads preferences from PicasaPreferences using Picasa 3 default values.
        """
        # FR: Général / EN: General
        self.chk_transitions.setChecked(self.settings.value("UI/Transitions", True, type=bool))
        self.chk_tooltips.setChecked(self.settings.value("UI/Tooltips", True, type=bool))
        self.chk_single_click.setChecked(self.settings.value("UI/SingleClickExit", False, type=bool))
        self.chk_autoexclude.setChecked(self.settings.value("Files/AutoExcludeDuplicates", True, type=bool))
        self.chk_no_confirm_del.setChecked(self.settings.value("Files/NoConfirmDelete", False, type=bool))
        self.chk_no_confirm_album.setChecked(self.settings.value("Files/NoConfirmRemoveAlbum", False, type=bool))

        up_mode = self.settings.value("Updates/Mode", 0, type=int)
        if self.update_group.button(up_mode):
            self.update_group.button(up_mode).setChecked(True)

        # FR: Langue / EN: Language (Ref: Local::lang, 0x004060B0)
        cur_lang = self.settings.value("UI/Language", "system", type=str) or "system"
        idx = self.combo_language.findData(cur_lang)
        if idx >= 0:
            self.combo_language.setCurrentIndex(idx)

        # FR: E-mail / EN: Email
        mail_mode = self.settings.value("Email/Mailer", 0, type=int)
        if self.mail_group.button(mail_mode):
            self.mail_group.button(mail_mode).setChecked(True)
        self.cb_mail_size.setCurrentIndex(self.settings.value("Email/SizeIdx", 2, type=int))

        # FR: Types de fichiers (valeurs par défaut exactes de picasa3.exe @ 0x004E04A0..0x004E0780)
        # EN: File types (exact defaults from picasa3.exe @ 0x004E04A0..0x004E0780)
        default_ft = {
            "bmp": True,
            "gif": False,
            "png": False,
            "tga": False,
            "tiff": True,
            "webp": True,
            "psd": True,
            "raw": True,
            "movies": True,
        }
        pref_key_map = {
            "bmp": "SupportBMP",
            "gif": "SupportGIF",
            "png": "SupportPNG",
            "tga": "SupportTGA",
            "tiff": "SupportTIF",
            "webp": "SupportWEBP",
            "psd": "SupportPSD",
            "raw": "SupportRAW",
            "movies": "SupportMovies",
        }
        for ext_id, chk in self.ft_checkboxes.items():
            def_val = default_ft.get(ext_id, True)
            raw_ft = self.settings.value(f"FileTypes/{ext_id}", None)
            if raw_ft is None:
                pk = pref_key_map.get(ext_id)
                raw_ft = self.settings.value(pk, None) if pk else None
            if raw_ft is None:
                chk.setChecked(def_val)
            else:
                chk.setChecked(self.settings.value(f"FileTypes/{ext_id}", def_val, type=bool))

        # FR: Diaporama / EN: Slideshow
        self.chk_slideshow_loop.setChecked(self.settings.value("Slideshow/Loop", False, type=bool))
        self.chk_slideshow_music.setChecked(self.settings.value("Slideshow/PlayMusic", False, type=bool))
        self.txt_music_path.setText(self.settings.value("Slideshow/MusicPath", "", type=str))

        # FR: Impression / EN: Printing
        self.chk_high_res_preview.setChecked(self.settings.value("Printing/HighResPreview", True, type=bool))
        self.rb_print_high.setChecked(self.settings.value("Printing/HighQuality", True, type=bool))
        self.rb_print_compat.setChecked(not self.rb_print_high.isChecked())
        self.rb_resample_std.setChecked(self.settings.value("Printing/ResampleStandard", True, type=bool))
        self.rb_resample_sharp.setChecked(not self.rb_resample_std.isChecked())

        # FR: Réseau / EN: Network
        self.chk_autoproxy.setChecked(self.settings.value("Network/AutoProxy", True, type=bool))
        self.cb_net_log.setCurrentIndex(self.settings.value("Network/LogLevel", 0, type=int))

        # FR: Tags de nom / EN: Name tags
        self.chk_facedetect.setChecked(self.settings.value("Faces/DetectionEnabled", True, type=bool))
        self.chk_facesuggest.setChecked(self.settings.value("Faces/SuggestionsEnabled", True, type=bool))
        s_val = self.settings.value("Faces/SuggestThreshold", 70, type=int)
        c_val = self.settings.value("Faces/ClusterThreshold", 85, type=int)
        self.slider_sugg.setValue(s_val)
        self.slider_cluster.setValue(c_val)
        self.lbl_sugg_val.setText(f"{s_val} %")
        self.lbl_cluster_val.setText(f"{c_val} %")
        self.chk_persist_xmp.setChecked(self.settings.value("Faces/PersistXMP", True, type=bool))
        cur_eng = PicasaPreferences.get_face_engine()
        eng_idx = self.cb_face_engine.findData(cur_eng)
        if eng_idx >= 0:
            self.cb_face_engine.setCurrentIndex(eng_idx)

    def save_settings(self) -> dict:
        """
        FR: Sauvegarde les préférences dans PicasaPreferences et émet le dictionnaire de configuration.
        EN: Saves preferences to PicasaPreferences and emits the configuration dictionary.
        """
        face_engine = str(self.cb_face_engine.currentData() or "native")
        data = {
            "ui_transitions": self.chk_transitions.isChecked(),
            "ui_tooltips": self.chk_tooltips.isChecked(),
            "ui_single_click_exit": self.chk_single_click.isChecked(),
            "ui_language": self.combo_language.currentData() or "system",
            "files_autoexclude": self.chk_autoexclude.isChecked(),
            "files_no_confirm_del": self.chk_no_confirm_del.isChecked(),
            "files_no_confirm_album": self.chk_no_confirm_album.isChecked(),
            "updates_mode": self.update_group.checkedId(),
            "email_mailer": self.mail_group.checkedId(),
            "email_size_idx": self.cb_mail_size.currentIndex(),
            "file_types": {ext_id: chk.isChecked() for ext_id, chk in self.ft_checkboxes.items()},
            "slideshow_loop": self.chk_slideshow_loop.isChecked(),
            "slideshow_music": self.chk_slideshow_music.isChecked(),
            "slideshow_music_path": self.txt_music_path.text(),
            "printing_high_res_prev": self.chk_high_res_preview.isChecked(),
            "printing_high_quality": self.rb_print_high.isChecked(),
            "printing_resample_std": self.rb_resample_std.isChecked(),
            "network_autoproxy": self.chk_autoproxy.isChecked(),
            "network_log_level": self.cb_net_log.currentIndex(),
            "faces_detection": self.chk_facedetect.isChecked(),
            "faces_suggestions": self.chk_facesuggest.isChecked(),
            "faces_suggest_threshold": self.slider_sugg.value(),
            "faces_cluster_threshold": self.slider_cluster.value(),
            "faces_persist_xmp": self.chk_persist_xmp.isChecked(),
            "faces_engine": face_engine,
        }

        self.settings.setValue("UI/Transitions", data["ui_transitions"])
        self.settings.setValue("UI/Tooltips", data["ui_tooltips"])
        self.settings.setValue("UI/SingleClickExit", data["ui_single_click_exit"])
        self.settings.setValue("UI/Language", data["ui_language"])
        self.res_mgr.set_language(data["ui_language"])
        self.retranslate_ui()

        self.settings.setValue("Files/AutoExcludeDuplicates", data["files_autoexclude"])
        self.settings.setValue("Files/NoConfirmDelete", data["files_no_confirm_del"])
        self.settings.setValue("Files/NoConfirmRemoveAlbum", data["files_no_confirm_album"])
        self.settings.setValue("Updates/Mode", data["updates_mode"])
        self.settings.setValue("Email/Mailer", data["email_mailer"])
        self.settings.setValue("Email/SizeIdx", data["email_size_idx"])

        pref_key_map = {
            "bmp": "SupportBMP",
            "gif": "SupportGIF",
            "png": "SupportPNG",
            "tga": "SupportTGA",
            "tiff": "SupportTIF",
            "webp": "SupportWEBP",
            "psd": "SupportPSD",
            "raw": "SupportRAW",
            "movies": "SupportMovies",
        }
        for ext_id, checked in data["file_types"].items():
            self.settings.setValue(f"FileTypes/{ext_id}", checked)
            pk = pref_key_map.get(ext_id)
            if pk:
                self.settings.setValue(pk, 1 if checked else 0)

        self.settings.setValue("Slideshow/Loop", data["slideshow_loop"])
        self.settings.setValue("Slideshow/PlayMusic", data["slideshow_music"])
        self.settings.setValue("Slideshow/MusicPath", data["slideshow_music_path"])
        self.settings.setValue("Printing/HighResPreview", data["printing_high_res_prev"])
        self.settings.setValue("Printing/HighQuality", data["printing_high_quality"])
        self.settings.setValue("Printing/ResampleStandard", data["printing_resample_std"])
        self.settings.setValue("Network/AutoProxy", data["network_autoproxy"])
        self.settings.setValue("Network/LogLevel", data["network_log_level"])
        self.settings.setValue("Faces/DetectionEnabled", data["faces_detection"])
        self.settings.setValue("Faces/SuggestionsEnabled", data["faces_suggestions"])
        self.settings.setValue("Faces/SuggestThreshold", data["faces_suggest_threshold"])
        self.settings.setValue("Faces/ClusterThreshold", data["faces_cluster_threshold"])
        self.settings.setValue("Faces/PersistXMP", data["faces_persist_xmp"])
        PicasaPreferences.set_face_engine(face_engine)

        self.settings.sync()
        self.settings_saved.emit(data)
        return data

    def _on_ok(self) -> None:
        """
        FR: Sauvegarde les préférences et ferme la boîte de dialogue avec acceptation.
        EN: Saves preferences and closes the dialog with acceptance.
        """
        self.save_settings()
        self.accept()
