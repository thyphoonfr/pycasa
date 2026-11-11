"""
FR : Composant de la barre d'actions supérieure de PyCasa.
Contient le bouton Importer, la recherche instantanée, les boutons de filtre et les sélecteurs de vue.
EN : Top Action Bar Component for PyCasa.
Contains Import button, Search input, Filter buttons, and View switches.

Ref: picasa3.exe @ HEADERPANELTEXT.XML
Ref: picasa3.exe @ 0x0088C3EC (Search & Filters)
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLineEdit, QLabel, QFrame, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QFont

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaTopBar(QWidget):
    """
    FR : Barre d'outils supérieure fidèle à `thumbui/buttonbarsets` et `searchcontainer.tre`.
    EN : Top toolbar faithful to `thumbui/buttonbarsets` and `searchcontainer.tre`.
    Disposition gauche -> droite (canevas de référence 800x534) :
    - Gauche (au-dessus de l'arbre, X=6..247) :
      * `thumbui/importbutton` (6..117, 111x22) : Importer
      * `thumbui/newalbum` (124..153, 29x22) : Nouvel album
      * `thumbui/hviewtoggle` (160..220, 60x22) : Vue à plat (`flatview`) / Vue arborescente (`folderview`)
      * `thumbui/folderviewpopup` (225..247, 22x22) : Menu déroulant d'options d'affichage des dossiers
    - Centre-Droite (`thumbui/searchcontainer`, X=323..711) :
      * `searchcontainer/filter_label` + `filterbase` : « Filtres » + 4 boutons filtres accolés (★, 👤, 🎬, 📍)
      * `searchcontainer/searchbase` (bordure #7F9DB9, 173x24) : Champ de recherche avec loupe et bouton ✕

    Ref: respack.yt @ thumbui.tre (buttonbarsets, importbutton, newalbum, hviewtoggle, folderviewpopup)
    Ref: respack.yt @ searchcontainer.tre (filterbase, starsearch, facesearch, moviesearch, geotagsearch, searchbase)
    Ref: picasa3.exe @ 0x0088C3EC (Search & Quick Filters)
    """
    import_requested = Signal()
    new_album_requested = Signal()
    search_query_changed = Signal(str)
    filter_starred_toggled = Signal(bool)
    filter_faces_toggled = Signal(bool)
    filter_videos_toggled = Signal(bool)
    filter_geo_toggled = Signal(bool)
    folder_view_mode_changed = Signal(str)  # "flat" (ID_VIEW_FOLDERS) ou "tree" (ID_VIEW_ALL)
    folder_sort_requested = Signal(str)     # "date", "name", "size"
    people_sort_requested = Signal(int)     # 0 (ID_PEOPLEBYNAME), 1 (ID_PEOPLEBYAMOUNT), 2 (ID_PEOPLEBYAMOUNTTOP10)
    slideshow_requested = Signal()

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        # Hauteur authentique : thumbui/buttonbarsets rect=(0, 4, 800, 41) -> 37px
        self.setFixedHeight(38)
        self.setStyleSheet("""
            QWidget#TopBarRoot {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F2F0EC, stop:1 #DFDCD5);
                border-bottom: 1px solid #B5B2AA;
            }
            QPushButton#ListHeaderBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FAF9F6, stop:1 #E2DFD7);
                color: #222222;
                font-weight: bold;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
                border: 1px solid #9E9B93;
            }
            QPushButton#ListHeaderBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #EAE8E1);
                border-color: #6B89A8;
            }
            QPushButton#ListHeaderBtn:pressed, QPushButton#ListHeaderBtn:checked {
                background-color: #C8D8EA;
                border-color: #4A76A8;
            }
            QPushButton#ViewToggleLeft {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FAF9F6, stop:1 #E2DFD7);
                border: 1px solid #9E9B93;
                border-top-left-radius: 3px;
                border-bottom-left-radius: 3px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 2px 4px;
                font-size: 11px;
                color: #222222;
            }
            QPushButton#ViewToggleRight {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FAF9F6, stop:1 #E2DFD7);
                border: 1px solid #9E9B93;
                border-left: none;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                color: #222222;
            }
            QPushButton#ViewToggleLeft:checked, QPushButton#ViewToggleRight:checked {
                background-color: #C5D6E8;
                border-color: #4A76A8;
                font-weight: bold;
            }
            QPushButton#FilterBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FAF9F6, stop:1 #E1DED6);
                border: 1px solid #9E9B93;
                border-radius: 2px;
                padding: 1px 4px;
                font-size: 11px;
                color: #333333;
            }
            QPushButton#FilterBtn:hover {
                background-color: #EDF4FC;
                border-color: #7F9DB9;
            }
            QPushButton#FilterBtn:checked {
                background-color: #C5D8EB;
                border-color: #3879D9;
                font-weight: bold;
            }
            QLineEdit#SearchEdit {
                background-color: #FFFFFF;
                border: 1px solid #7F9DB9;
                border-radius: 2px;
                padding: 2px 8px;
                font-size: 11px;
                color: #222222;
            }
            QLineEdit#SearchEdit:focus {
                border: 1px solid #3879D9;
                background-color: #FFFFFF;
            }
        """)
        self.setObjectName("TopBarRoot")

        # Timer de temporisation pour la frappe instantanée sans freeze
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._on_search_timer_timeout)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 5, 10, 5)
        layout.setSpacing(5)

        # ---------------------------------------------------------------------
        # ZONE GAUCHE : Au-dessus de l'arborescence (X = 6..247 dans thumbui.tre)
        # ---------------------------------------------------------------------
        # 1. thumbui/importbutton : rect=(6, 9, 117, 31) -> 111x22 px
        self.btn_import = QPushButton("📥 Importer...")
        self.btn_import.setObjectName("ListHeaderBtn")
        self.btn_import.setFixedSize(111, 24)
        self.btn_import.setToolTip("Importer des photos depuis un appareil photo ou un dossier (Ctrl+M)")
        self.btn_import.clicked.connect(self.import_requested.emit)
        layout.addWidget(self.btn_import)

        # 2. thumbui/newalbum : rect=(124, 9, 153, 31) -> 29x22 px
        self.btn_new_album = QPushButton("📒+")
        self.btn_new_album.setObjectName("ListHeaderBtn")
        self.btn_new_album.setFixedSize(32, 24)
        self.btn_new_album.setToolTip("Nouvel album (Ctrl+N)")
        self.btn_new_album.clicked.connect(self.new_album_requested.emit)
        layout.addWidget(self.btn_new_album)

        # 3. thumbui/hviewtoggle : flatview (160..190) + folderview (190..220) -> 60x22 px
        toggle_container = QWidget(self)
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(0)

        self.btn_view_flat = QPushButton("📁")
        self.btn_view_flat.setObjectName("ViewToggleLeft")
        self.btn_view_flat.setFixedSize(30, 24)
        self.btn_view_flat.setCheckable(True)
        self.btn_view_flat.setChecked(True)
        self.btn_view_flat.setToolTip("Affichage simple des dossiers (Ctrl+1)")

        self.btn_view_tree = QPushButton("🌳")
        self.btn_view_tree.setObjectName("ViewToggleRight")
        self.btn_view_tree.setFixedSize(30, 24)
        self.btn_view_tree.setCheckable(True)
        self.btn_view_tree.setToolTip("Affichage arborescent des dossiers (Ctrl+2)")

        self.view_mode_group = QButtonGroup(self)
        self.view_mode_group.setExclusive(True)
        self.view_mode_group.addButton(self.btn_view_flat, 0)
        self.view_mode_group.addButton(self.btn_view_tree, 1)
        self.view_mode_group.idClicked.connect(
            lambda btn_id: self.folder_view_mode_changed.emit("tree" if btn_id == 1 else "flat")
        )
        toggle_layout.addWidget(self.btn_view_flat)
        toggle_layout.addWidget(self.btn_view_tree)
        layout.addWidget(toggle_container)

        # 4. thumbui/folderviewpopup : rect=(225, 9, 247, 31) -> 22x22 px
        self.btn_folder_popup = QPushButton("▾")
        self.btn_folder_popup.setObjectName("ListHeaderBtn")
        self.btn_folder_popup.setFixedSize(22, 24)
        self.btn_folder_popup.setToolTip("Options d'affichage et de tri des dossiers")
        self.btn_folder_popup.clicked.connect(self._show_folder_view_popup)
        layout.addWidget(self.btn_folder_popup)

        # Note: thumbui/sbutton est marqué m_hidden dans thumbui.tre (déplacé dans headerpanel/play).
        # On conserve l'attribut caché pour compatibilité des connexions existantes.
        self.btn_slideshow = QPushButton("▶ Diaporama", self)
        self.btn_slideshow.hide()
        self.btn_slideshow.clicked.connect(self.slideshow_requested.emit)

        layout.addStretch(1)

        # ---------------------------------------------------------------------
        # ZONE CENTRE-DROITE : searchcontainer.tre (X = 323..711)
        # Filtres accolés immédiatement à gauche du champ de recherche
        # ---------------------------------------------------------------------
        self.lbl_filters = QLabel("Filtres :")
        self.lbl_filters.setStyleSheet("color: #555555; font-size: 10px; font-weight: bold; margin-right: 2px;")
        layout.addWidget(self.lbl_filters)

        filter_box = QWidget(self)
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(1)

        # searchcontainer/starsearch : rect=(0, 12, 26, 28) -> 26x16 px
        self.btn_star = QPushButton("★")
        self.btn_star.setObjectName("FilterBtn")
        self.btn_star.setFixedSize(26, 22)
        self.btn_star.setCheckable(True)
        self.btn_star.setToolTip("Afficher uniquement les photos favorites marquées d'une étoile")
        self.btn_star.toggled.connect(self.filter_starred_toggled.emit)
        filter_layout.addWidget(self.btn_star)

        # searchcontainer/facesearch : rect=(52, 12, 78, 28) -> 26x16 px
        self.btn_faces = QPushButton("👤")
        self.btn_faces.setObjectName("FilterBtn")
        self.btn_faces.setFixedSize(26, 22)
        self.btn_faces.setCheckable(True)
        self.btn_faces.setToolTip("Afficher uniquement les photos contenant des visages")
        self.btn_faces.toggled.connect(self.filter_faces_toggled.emit)
        filter_layout.addWidget(self.btn_faces)

        # searchcontainer/moviesearch : rect=(78, 12, 104, 28) -> 26x16 px
        self.btn_movies = QPushButton("🎬")
        self.btn_movies.setObjectName("FilterBtn")
        self.btn_movies.setFixedSize(26, 22)
        self.btn_movies.setCheckable(True)
        self.btn_movies.setToolTip("Afficher uniquement les vidéos")
        self.btn_movies.toggled.connect(self.filter_videos_toggled.emit)
        filter_layout.addWidget(self.btn_movies)

        # searchcontainer/geotagsearch : rect=(104, 12, 130, 28) -> 26x16 px
        self.btn_geo = QPushButton("📍")
        self.btn_geo.setObjectName("FilterBtn")
        self.btn_geo.setFixedSize(26, 22)
        self.btn_geo.setCheckable(True)
        self.btn_geo.setToolTip("Afficher uniquement les photos géolocalisées")
        self.btn_geo.toggled.connect(self.filter_geo_toggled.emit)
        filter_layout.addWidget(self.btn_geo)

        layout.addWidget(filter_box)

        layout.addSpacing(4)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("SearchEdit")
        self.search_edit.setPlaceholderText("🔍 Rechercher...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedSize(195, 24)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_edit)

        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème de couleur PicasaStyle à la barre supérieure.
        EN : Dynamically applies the PicasaStyle color theme to the top bar.
        """
        if style is None:
            style = PicasaStyle.instance()
        self.style = style
        g_start = style.topbar_grad_start.name()
        g_mid = style.topbar_grad_mid.name() if getattr(style, "topbar_grad_mid", None) else None
        g_end = style.topbar_grad_end.name()
        b_col = style.topbar_border_color.name()
        txt_col = style.topbar_text_color.name()
        btn_s = style.topbar_btn_bg_start.name()
        btn_e = style.topbar_btn_bg_end.name()
        btn_b = style.topbar_btn_border.name()
        accent = style.accent_color.name()
        accent_end = getattr(style, "accent_grad_end", style.accent_color).name()
        search_bg = "#252932" if style.is_dark else "#FFFFFF"
        search_txt = "#E2E8F0" if style.is_dark else "#222222"
        if g_mid:
            topbar_bg_grad = (
                f"qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {g_start}, stop:0.5 {g_mid}, stop:1 {g_end})"
            )
        else:
            topbar_bg_grad = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {g_start}, stop:1 {g_end})"
        accent_bg_grad = (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent_end})"
            if accent != accent_end
            else accent
        )

        self.setStyleSheet(f"""
            QWidget#TopBarRoot {{
                background: {topbar_bg_grad};
                border-bottom: 1px solid {b_col};
            }}
            QPushButton#ListHeaderBtn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_s}, stop:1 {btn_e});
                color: {txt_col};
                font-weight: bold;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
                border: 1px solid {btn_b};
            }}
            QPushButton#ListHeaderBtn:hover {{
                border-color: {accent};
            }}
            QPushButton#ListHeaderBtn:pressed, QPushButton#ListHeaderBtn:checked {{
                background: {accent_bg_grad};
                color: #FFFFFF;
                border-color: {accent};
            }}
            QPushButton#ViewToggleLeft {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_s}, stop:1 {btn_e});
                border: 1px solid {btn_b};
                border-top-left-radius: 3px;
                border-bottom-left-radius: 3px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 2px 4px;
                font-size: 11px;
                color: {txt_col};
            }}
            QPushButton#ViewToggleRight {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_s}, stop:1 {btn_e});
                border: 1px solid {btn_b};
                border-left: none;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
                color: {txt_col};
            }}
            QPushButton#ViewToggleLeft:checked, QPushButton#ViewToggleRight:checked {{
                background: {accent_bg_grad};
                color: #FFFFFF;
                border-color: {accent};
                font-weight: bold;
            }}
            QPushButton#FilterBtn {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_s}, stop:1 {btn_e});
                border: 1px solid {btn_b};
                border-radius: 2px;
                padding: 1px 4px;
                font-size: 11px;
                color: {txt_col};
            }}
            QPushButton#FilterBtn:hover {{
                border-color: {accent};
            }}
            QPushButton#FilterBtn:checked {{
                background: {accent_bg_grad};
                color: #FFFFFF;
                border-color: {accent};
                font-weight: bold;
            }}
            QLineEdit#SearchEdit {{
                background-color: {search_bg};
                border: 1px solid #7F9DB9;
                border-radius: 2px;
                padding: 2px 8px;
                font-size: 11px;
                color: {search_txt};
            }}
            QLineEdit#SearchEdit:focus {{
                border: 1px solid {accent};
                background-color: {search_bg};
            }}
        """)
        if hasattr(self, "lbl_filters"):
            self.lbl_filters.setStyleSheet(
                f"color: {txt_col}; font-size: 10px; font-weight: bold; margin-right: 2px;"
            )

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes et info-bulles de la barre supérieure selon la langue active.
        EN : Updates the top bar labels and tooltips according to the active language.
        """
        rm = PicasaResourceManager.get()
        imp_lbl = rm.get_xml_string("thumbui/importbutton", "Importer...")
        self.btn_import.setText(f"📥 {imp_lbl}")
        filt_lbl = rm.get_xml_string("searchcontainer/filter_label", "Filtres :")
        self.lbl_filters.setText(filt_lbl)
        search_ph = rm.get_xml_string("searchcontainer/searchbase", "Rechercher...")
        self.search_edit.setPlaceholderText(f"🔍 {search_ph}")

    def _show_folder_view_popup(self) -> None:
        """
        FR : Affiche le menu contextuel d'options de vue/tri des dossiers et personnes (`thumbui/folderviewpopup`, menu 0x86).
        EN : Displays the folder and people view/sort options popup menu (`thumbui/folderviewpopup`, menu 0x86).
        Ref: picasa3.exe @ 0x00733480 - 0x0073399E, 0x005E2070 - 0x005E2270
        Ref: respack.yt @ thumbui/folderviewpopup (rect 225,9,247,31)
        """
        from PySide6.QtWidgets import QMenu
        from picasa_py.db.preferences import PicasaPreferences

        rm = PicasaResourceManager.get()
        menu = QMenu(self)
        act_flat = menu.addAction(rm.get_stringres("Menu::ID_VIEW_FOLDERS", "Affichage simple des dossiers"))
        act_flat.setCheckable(True)
        act_flat.setChecked(self.btn_view_flat.isChecked())
        act_flat.triggered.connect(lambda: self._select_folder_mode("flat"))

        act_tree = menu.addAction(rm.get_stringres("Menu::ID_VIEW_ALL", "Affichage arborescent"))
        act_tree.setCheckable(True)
        act_tree.setChecked(self.btn_view_tree.isChecked())
        act_tree.triggered.connect(lambda: self._select_folder_mode("tree"))

        menu.addSeparator()
        win = self.window()
        lib_tree = getattr(win, "library_tree", None) if win is not None else None
        cur_dsort = (
            int(getattr(lib_tree, "date_sort_mode", 0))
            if lib_tree is not None
            else PicasaPreferences.get_date_sort_mode()
        )
        # FR : Options de tri des Dossiers / Albums (Ref: 0x005E20A1 - 0x005E2112)
        # EN : Folder / Album sort options (Ref: 0x005E20A1 - 0x005E2112)
        act_sort_date = menu.addAction(rm.get_stringres("AlbumList::ID_SORTBYDATE", "Trier les dossiers par date"))
        act_sort_date.setCheckable(True)
        act_sort_date.setChecked(cur_dsort == 0)
        act_sort_date.triggered.connect(lambda: self.folder_sort_requested.emit("date"))

        act_sort_size = menu.addAction(rm.get_stringres("AlbumList::ID_SORTBYSIZE", "Trier les dossiers par taille"))
        act_sort_size.setCheckable(True)
        act_sort_size.setChecked(cur_dsort == 1)
        act_sort_size.triggered.connect(lambda: self.folder_sort_requested.emit("size"))

        act_sort_name = menu.addAction(rm.get_stringres("AlbumList::ID_SORTBYNAME", "Trier les dossiers par nom"))
        act_sort_name.setCheckable(True)
        act_sort_name.setChecked(cur_dsort == 2)
        act_sort_name.triggered.connect(lambda: self.folder_sort_requested.emit("name"))

        # FR : Options de tri de la collection Personnes (Ref: 0x007336F5 - 0x00733772, 0x005E2157 - 0x005E218C)
        # EN : People collection sort options (Ref: 0x007336F5 - 0x00733772, 0x005E2157 - 0x005E218C)
        menu.addSeparator()
        cur_psort = (
            int(getattr(lib_tree, "people_sort_mode", 0))
            if lib_tree is not None
            else PicasaPreferences.get_people_sort_mode()
        )

        act_p_name = menu.addAction(
            rm.get_stringres("AlbumList::ID_PEOPLEBYNAME", "Trier les &personnes par nom")
        )
        act_p_name.setCheckable(True)
        act_p_name.setChecked(cur_psort == 0)
        act_p_name.triggered.connect(lambda: self.people_sort_requested.emit(0))

        act_p_amount = menu.addAction(
            rm.get_stringres("AlbumList::ID_PEOPLEBYAMOUNT", "Trier les personnes par &nombre")
        )
        act_p_amount.setCheckable(True)
        act_p_amount.setChecked(cur_psort == 1)
        act_p_amount.triggered.connect(lambda: self.people_sort_requested.emit(1))

        act_p_top10 = menu.addAction(
            rm.get_stringres(
                "AlbumList::ID_PEOPLEBYAMOUNTTOP10",
                "Trier en fonction des &10premières personnes",
            )
        )
        act_p_top10.setCheckable(True)
        act_p_top10.setChecked(cur_psort == 2)
        act_p_top10.triggered.connect(lambda: self.people_sort_requested.emit(2))

        menu.exec(self.btn_folder_popup.mapToGlobal(self.btn_folder_popup.rect().bottomLeft()))

    def _select_folder_mode(self, mode: str) -> None:
        self.set_folder_view_mode(mode)
        self.folder_view_mode_changed.emit(mode)

    def set_folder_view_mode(self, mode: str) -> None:
        """
        FR : Synchronise l'état des boutons Liste / Arbre sans ré-émettre le signal.
        EN : Synchronizes the Flat / Tree button states without re-emitting the signal.
        """
        self.view_mode_group.blockSignals(True)
        if mode == "tree":
            self.btn_view_tree.setChecked(True)
        else:
            self.btn_view_flat.setChecked(True)
        self.view_mode_group.blockSignals(False)

    def _on_search_text_changed(self, text: str) -> None:
        if not text.strip():
            self._search_timer.stop()
            self.search_query_changed.emit("")
        else:
            self._search_timer.start()

    def _on_search_timer_timeout(self) -> None:
        self.search_query_changed.emit(self.search_edit.text())

    def clear_search(self) -> None:
        self.search_edit.clear()

    def set_search_query(self, text: str) -> None:
        self.search_edit.setText(text)

