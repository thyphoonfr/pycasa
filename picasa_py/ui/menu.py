"""
FR : Constructeur de la barre de menus pour PyCasa.
Assemble les menus et les raccourcis clavier exactement comme Picasa 3.

EN : Menu Bar Builder for PyCasa.
Assembles menus and shortcuts exactly matching Picasa 3.

Ref: picasa3.exe @ 0x0088C3EC (eMenu* hierarchy)
Ref: Picasa3i18n.dll @ SHORTCUTS.XML
"""

from __future__ import annotations
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import QMenuBar, QMenu, QMainWindow
from PySide6.QtGui import QAction, QActionGroup, QKeySequence

RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "resources"


MENU_I18N = {
    "fr": {
        "menu_file": "&Fichier",
        "menu_edit": "&Édition",
        "menu_view": "&Affichage",
        "menu_folder": "&Dossier",
        "menu_picture": "&Image",
        "menu_create": "&Création",
        "menu_tools": "&Outils",
        "menu_help": "&Aide",
        "ID_FILE_OPEN": "Ajouter un &fichier à Picasa...",
        "ID_TOOLS_INCLUDEEXCLUDEFOLDERS": "Ajouter un &dossier à Picasa...",
        "ID_FILE_IMPORTPICTURE": "&Importer depuis...",
        "ID_FILE_NEWLABEL": "&Nouvel album...",
        "ID_FILE_SAVE": "&Enregistrer",
        "ID_FILE_SAVEAS": "Enregistrer &sous...",
        "ID_FILE_SAVEACOPY": "Enregistrer une &copie",
        "ID_FILE_REVERT": "&Rétablir",
        "ID_FILE_PRINT": "&Imprimer...",
        "ID_FILE_PRINTCONTACTSHEET": "Imprimer la &planche-contact...",
        "ID_FILE_EXPORTTOFOLDER": "E&xporter l'image vers le dossier...",
        "ID_FILE_RENAME": "&Renommer...",
        "ID_FILE_DELETEFROMDISK": "&Supprimer du disque...",
        "ID_FILE_EXIT": "&Quitter",
        "ID_EDIT_CUT": "C&ouper",
        "ID_EDIT_COPY": "&Copier",
        "ID_EDIT_COPYALLEFFECTS": "Copier tous les &effets",
        "ID_COPY_PATH": "Copier le &chemin complet",
        "ID_EDIT_PASTE": "C&oller",
        "ID_EDIT_PASTEALLEFFECTS": "Coller tous les e&ffets",
        "ID_SETPEOPLEALBUMCOVER": "Définir en tant que &vignette de l'album",
        "ID_ALBUM_SELECTALLPICTURES": "&Tout sélectionner",
        "ID_SELECTSTAR": "Sélectionner les &favoris",
        "ID_SELECT_INVERT": "&Inverser la sélection",
        "ID_CLEAR_SELECTION": "Annuler la &sélection",
        "ID_VIEW_THUMBNAILS": "Afficher les miniatures dans la &bibliothèque",
        "ID_VIEW_SLIDESHOW": "Lancer le &diaporama",
        "ID_VIEW_TIMELINE": "&Chronologie",
        "ID_VIEW_ALL": "&Affichage arborescent",
        "ID_VIEW_FOLDERS": "Affichage &plat des dossiers",
        "ID_FILE_LOCATEONDISK": "&Rechercher sur le disque",
        "ID_REFRESH_THUMB": "&Actualiser la miniature",
        "ID_FILE_EXPORTASWEBPAGE": "Exporter en page &Web...",
        "ID_PICTURE_ROTATECLOCKWISE": "Faire pivoter vers la &droite",
        "ID_PICTURE_ROTATECOUNTERCLOCKWISE": "Faire pivoter vers la &gauche",
        "ID_PICTURE_STAR": "Ajouter/Supprimer une &étoile",
        "ID_PICTURE_AUTO_LIGHTING": "Contraste &automatique",
        "ID_PICTURE_AUTO_COLOR": "Couleur auto&matique",
        "ID_PICTURE_AUTO_REDEYE": "&Yeux rouges automatiques",
        "ID_PICTURE_REVERT": "Annuler &toutes les retouches",
        "ID_PICTURE_PROPERTIES": "&Propriétés",
        "ID_COLLAGEMAKER": "&Montage photo...",
        "ID_POSTER": "Créer un &poster...",
        "MOVIE": "Créer un &film...",
        "ID_WALLPAPER": "Définir comme &fond d'écran...",
        "ID_SCREENSAVER": "Définir comme &économiseur d'écran...",
        "ID_TOOLS_OPTIONS": "&Options...",
        "ID_TOOLS_ADJUST_TIMESTAMP": "Ajuster la &date et l'heure...",
        "ID_TOOLS_PEOPLE_MGR": "Gestionnaire de &personnes...",
        "ID_TOOLS_WRITE_FACETAGS": "Écrire les tags de visage dans &XMP...",
        "ID_MOVE_DATABASE": "&Déplacer la base de données...",
        "ID_COMPACT_DATABASE": "&Compacter la base de données...",
        "ID_CLEAN_PICASA_TRACES": "&Nettoyer les traces Picasa (.picasa.ini)...",
        "ID_CREATE_DATABASE": "&Créer une nouvelle base de données...",
        "ID_OPEN_DATABASE": "&Ouvrir une base de données existante...",
        "ID_HELP_DEFAULT": "&Rubriques d'aide et index",
        "ID_HELP_ABOUT": "À &propos de PyCasa...",
        "ID_HELP_KEYBOARD_SHORTCUTS": "Raccourcis &clavier",
        "ID_HELP_PRIVACY": "Règles de &confidentialité",
        "ID_ALBUM_EDITCAPTIONS": "&Modifier la description du dossier...",
        "ID_MOVEFOLDER": "&Déplacer le dossier...",
        "ID_ALBUM_DELETE": "&Supprimer le dossier...",
        "ID_PICTURE_RESET_FACES": "&Réinitialiser les visages",
        "ID_VIEW_PEOPLE": "&Personnes",
        "ID_VIEW_PLACES": "&Lieux",
        "ID_VIEW_TAGS": "&Balises",
        "ID_VIEW_DRAWER_PROPERTIES": "&Propriétés du panneau",
        "ID_VIEW_COLOR_THEME": "&Thème de couleurs",
        "eMenuCreate::Movies": "&Film",
        "eMenuCreateMovie::MOVIE": "À partir de la &sélection...",
        "eMenuCreateMovie::ID_FACES": "À partir des &visages de la sélection (Face Movie)...",
        "ID_TOOLS_FOLDER_MGR": "Gestionnaire de &dossiers...",
    },
    "es": {
        "menu_file": "&Archivo",
        "menu_edit": "&Editar",
        "menu_view": "&Ver",
        "menu_folder": "&Carpeta",
        "menu_picture": "&Imagen",
        "menu_create": "&Crear",
        "menu_tools": "&Herramientas",
        "menu_help": "&Ayuda",
        "ID_FILE_OPEN": "Añadir &archivo a Picasa...",
        "ID_TOOLS_INCLUDEEXCLUDEFOLDERS": "Añadir &carpeta a Picasa...",
        "ID_FILE_NEWLABEL": "&Nuevo álbum...",
        "ID_FILE_SAVE": "&Guardar",
        "ID_FILE_PRINT": "&Imprimir...",
        "ID_FILE_EXIT": "&Salir",
        "ID_TOOLS_OPTIONS": "&Opciones...",
        "ID_CREATE_DATABASE": "&Crear una nueva base de datos...",
        "ID_OPEN_DATABASE": "&Abrir una base de datos existente...",
        "ID_CLEAN_PICASA_TRACES": "&Limpiar rastros de Picasa (.picasa.ini)...",
        "ID_VIEW_COLOR_THEME": "&Tema de color",
        "ID_HELP_ABOUT": "&Acerca de PyCasa...",
    },
    "de": {
        "menu_file": "&Datei",
        "menu_edit": "&Bearbeiten",
        "menu_view": "&Ansicht",
        "menu_folder": "&Ordner",
        "menu_picture": "&Bild",
        "menu_create": "&Erstellen",
        "menu_tools": "&Tools",
        "menu_help": "&Hilfe",
        "ID_FILE_OPEN": "&Datei zu Picasa hinzufügen...",
        "ID_TOOLS_INCLUDEEXCLUDEFOLDERS": "&Ordner zu Picasa hinzufügen...",
        "ID_FILE_NEWLABEL": "&Neues Album...",
        "ID_FILE_SAVE": "&Speichern",
        "ID_FILE_PRINT": "&Drucken...",
        "ID_FILE_EXIT": "&Beenden",
        "ID_TOOLS_OPTIONS": "&Optionen...",
        "ID_CREATE_DATABASE": "&Neue Datenbank erstellen...",
        "ID_OPEN_DATABASE": "&Vorhandene Datenbank öffnen...",
        "ID_CLEAN_PICASA_TRACES": "&Picasa-Spuren bereinigen (.picasa.ini)...",
        "ID_VIEW_COLOR_THEME": "&Farbschema",
        "ID_HELP_ABOUT": "Über &PyCasa...",
    },
}


# Ref: picasa3.exe @ 0x0088C3EC
class PicasaMenuBuilder:
    """
    FR : Constructeur de la barre de menus de Picasa avec support multilingue.
    EN : Picasa menu bar builder with multilingual support.
    """

    def __init__(self, main_window: QMainWindow):
        self.win = main_window
        self.shortcuts: Dict[str, str] = {}
        self.theme_actions: Dict[str, QAction] = {}
        self.menu_themes: Optional[QMenu] = None
        self._load_shortcuts()

    def retranslate_ui(self) -> None:
        """
        FR : Reconstruit la barre de menus avec les traductions de la langue active.
        EN : Rebuilds the menu bar with translations for the active language.
        """
        self.build_menu_bar()

    def _tr(self, key: str, default: str) -> str:
        from picasa_py.version import APP_NAME
        res_text = default
        try:
            from picasa_py.ui.resources import PicasaResourceManager
            rm = PicasaResourceManager.get()
            lang = rm.get_current_language().lower()
            for lk in (lang, lang[:2]):
                if lk in MENU_I18N and key in MENU_I18N[lk]:
                    res_text = MENU_I18N[lk][key]
                    break
            else:
                if key == "ID_HELP_ABOUT":
                    res_text = rm.get_stringres("eMenuHelp::ID_HELP_ABOUT", default)
        except Exception:
            pass
        if key == "ID_HELP_ABOUT":
            res_text = res_text.replace("Picasa", APP_NAME)
        return res_text

    def _load_shortcuts(self) -> None:
        sc_file = RESOURCES_DIR / "xml" / "SHORTCUTS.XML"
        if not sc_file.exists():
            return

        try:
            root = ET.fromstring(sc_file.read_text(encoding="utf-8"))
            # Standard keyboard mapping
            self.shortcuts["ID_FILE_OPEN"] = "Ctrl+O"
            self.shortcuts["ID_FILE_NEWLABEL"] = "Ctrl+N"
            self.shortcuts["ID_FILE_SAVE"] = "Ctrl+S"
            self.shortcuts["ID_FILE_SAVEAS"] = "Ctrl+Shift+S"
            self.shortcuts["ID_FILE_RENAME"] = "F2"
            self.shortcuts["ID_FILE_PRINT"] = "Ctrl+P"
            self.shortcuts["ID_FILE_PRINTCONTACTSHEET"] = "Ctrl+Shift+P"
            self.shortcuts["ID_EDIT_COPY"] = "Ctrl+C"
            self.shortcuts["ID_EDIT_COPYALLEFFECTS"] = "Ctrl+Shift+C"
            self.shortcuts["ID_EDIT_PASTE"] = "Ctrl+V"
            self.shortcuts["ID_EDIT_PASTEALLEFFECTS"] = "Ctrl+Shift+V"
            self.shortcuts["ID_EDIT_CUT"] = "Ctrl+X"
            self.shortcuts["ID_ALBUM_SELECTALLPICTURES"] = "Ctrl+A"
            self.shortcuts["ID_VIEW_SLIDESHOW"] = "Ctrl+4"
            self.shortcuts["ID_FILE_DELETEFROMDISK"] = "Delete"
            self.shortcuts["ID_PICTURE_ROTATECLOCKWISE"] = "Ctrl+R"
            self.shortcuts["ID_PICTURE_ROTATECOUNTERCLOCKWISE"] = "Ctrl+Shift+R"
            self.shortcuts["ID_PICTURE_STAR"] = "Ctrl+T"
            self.shortcuts["ID_COPY_PATH"] = "Ctrl+Shift+Y"
            self.shortcuts["ID_PICTURE_PROPERTIES"] = "Alt+Enter"
            self.shortcuts["ID_VIEW_TAGS"] = "Ctrl+K"
        except Exception:
            pass

    def build_menu_bar(self) -> QMenuBar:
        mb = self.win.menuBar()
        mb.clear()

        # 1. &File
        menu_file = mb.addMenu(self._tr("menu_file", "&File"))
        self._add_action(menu_file, self._tr("ID_FILE_OPEN", "Add &File to Picasa..."), "ID_FILE_OPEN", self.win.action_add_file if hasattr(self.win, "action_add_file") else None)
        self._add_action(menu_file, self._tr("ID_TOOLS_INCLUDEEXCLUDEFOLDERS", "Add &Folder to Picasa..."), "ID_TOOLS_INCLUDEEXCLUDEFOLDERS", self.win.action_folder_manager if hasattr(self.win, "action_folder_manager") else None)
        self._add_action(menu_file, self._tr("ID_FILE_IMPORTPICTURE", "&Import From..."), "ID_FILE_IMPORTPICTURE", self.win.action_import if hasattr(self.win, "action_import") else None)
        self._add_action(menu_file, self._tr("ID_FILE_NEWLABEL", "&New Album..."), "ID_FILE_NEWLABEL", self.win.action_new_album if hasattr(self.win, "action_new_album") else None)
        menu_file.addSeparator()
        self._add_action(menu_file, self._tr("ID_FILE_SAVE", "&Save"), "ID_FILE_SAVE", self.win.action_save if hasattr(self.win, "action_save") else None)
        self._add_action(menu_file, self._tr("ID_FILE_SAVEAS", "Save &As..."), "ID_FILE_SAVEAS", self.win.action_save_as if hasattr(self.win, "action_save_as") else None)
        self._add_action(menu_file, self._tr("ID_FILE_SAVEACOPY", "Save a Cop&y"), "ID_FILE_SAVEACOPY", self.win.action_save_a_copy if hasattr(self.win, "action_save_a_copy") else None)
        self._add_action(menu_file, self._tr("ID_FILE_REVERT", "Rever&t"), "ID_FILE_REVERT", self.win.action_undo_all_edits if hasattr(self.win, "action_undo_all_edits") else None)
        menu_file.addSeparator()
        self._add_action(menu_file, self._tr("ID_FILE_PRINT", "&Print..."), "ID_FILE_PRINT", self.win.action_print if hasattr(self.win, "action_print") else None)
        self._add_action(menu_file, self._tr("ID_FILE_PRINTCONTACTSHEET", "Print &Contact Sheet..."), "ID_FILE_PRINTCONTACTSHEET", self.win.action_print_contact_sheet if hasattr(self.win, "action_print_contact_sheet") else None)
        self._add_action(menu_file, self._tr("ID_FILE_EXPORTTOFOLDER", "Export Pi&cture to Folder..."), "ID_FILE_EXPORTTOFOLDER", self.win.action_export if hasattr(self.win, "action_export") else None)
        self._add_action(menu_file, self._tr("ID_FILE_RENAME", "&Rename..."), "ID_FILE_RENAME", self.win.action_rename if hasattr(self.win, "action_rename") else None)
        self._add_action(menu_file, self._tr("ID_FILE_DELETEFROMDISK", "&Delete from Disk..."), "ID_FILE_DELETEFROMDISK", self.win.action_delete_from_disk if hasattr(self.win, "action_delete_from_disk") else None)
        menu_file.addSeparator()
        self._add_action(menu_file, self._tr("ID_FILE_EXIT", "E&xit"), "ID_FILE_EXIT", self.win.close)

        # 2. &Edit
        menu_edit = mb.addMenu(self._tr("menu_edit", "&Edit"))
        self._add_action(menu_edit, self._tr("ID_EDIT_CUT", "Cu&t"), "ID_EDIT_CUT", self.win.action_cut if hasattr(self.win, "action_cut") else None)
        self._add_action(menu_edit, self._tr("ID_EDIT_COPY", "&Copy"), "ID_EDIT_COPY", self.win.action_copy if hasattr(self.win, "action_copy") else None)
        self._add_action(menu_edit, self._tr("ID_EDIT_COPYALLEFFECTS", "Copy All &Effects"), "ID_EDIT_COPYALLEFFECTS", self.win.action_copy_all_effects if hasattr(self.win, "action_copy_all_effects") else None)
        self._add_action(menu_edit, self._tr("ID_COPY_PATH", "Copy Full &Path"), "ID_COPY_PATH", self.win.action_copy_path if hasattr(self.win, "action_copy_path") else None)
        self._add_action(menu_edit, self._tr("ID_EDIT_PASTE", "&Paste"), "ID_EDIT_PASTE", self.win.action_paste if hasattr(self.win, "action_paste") else None)
        self._add_action(menu_edit, self._tr("ID_EDIT_PASTEALLEFFECTS", "Paste All E&ffects"), "ID_EDIT_PASTEALLEFFECTS", self.win.action_paste_all_effects if hasattr(self.win, "action_paste_all_effects") else None)
        menu_edit.addSeparator()
        self._add_action(menu_edit, self._tr("ID_ALBUM_SELECTALLPICTURES", "Select &All"), "ID_ALBUM_SELECTALLPICTURES", self.win.action_select_all if hasattr(self.win, "action_select_all") else None)
        self._add_action(menu_edit, self._tr("ID_SELECTSTAR", "Select &Starred"), "ID_SELECTSTAR", self.win.action_select_starred if hasattr(self.win, "action_select_starred") else None)
        self._add_action(menu_edit, self._tr("ID_SELECT_INVERT", "&Invert Selection"), "ID_SELECT_INVERT", self.win.action_invert_selection if hasattr(self.win, "action_invert_selection") else None)
        self._add_action(menu_edit, self._tr("ID_CLEAR_SELECTION", "C&lear Selection"), "ID_CLEAR_SELECTION", self.win.action_clear_selection if hasattr(self.win, "action_clear_selection") else None)

        # 3. &View
        menu_view = mb.addMenu(self._tr("menu_view", "&View"))
        self._add_action(menu_view, self._tr("ID_VIEW_THUMBNAILS", "Show &Thumbnails in Library"), "ID_VIEW_THUMBNAILS", self.win._back_to_library if hasattr(self.win, "_back_to_library") else None)
        self._add_action(menu_view, self._tr("ID_VIEW_TWOUP", "Side-by-Side &Comparison (Two-Up)"), "ID_VIEW_TWOUP", self.win.action_toggle_two_up if hasattr(self.win, "action_toggle_two_up") else None)
        self._add_action(menu_view, self._tr("ID_VIEW_SLIDESHOW", "Play &Slideshow"), "ID_VIEW_SLIDESHOW", self.win.action_slideshow if hasattr(self.win, "action_slideshow") else None)
        self._add_action(menu_view, self._tr("ID_VIEW_TIMELINE", "Ti&meline"), "ID_VIEW_TIMELINE", self.win.action_view_timeline if hasattr(self.win, "action_view_timeline") else None)
        menu_view.addSeparator()
        self._add_action(menu_view, self._tr("ID_VIEW_ALL", "&Tree View"), "ID_VIEW_ALL", self.win.action_view_tree if hasattr(self.win, "action_view_tree") else None)
        self._add_action(menu_view, self._tr("ID_VIEW_FOLDERS", "&Flat Folder View"), "ID_VIEW_FOLDERS", self.win.action_view_flat_folders if hasattr(self.win, "action_view_flat_folders") else None)
        menu_view.addSeparator()
        self._add_action(menu_view, self._tr("ID_VIEW_PEOPLE", "&People"), "ID_VIEW_PEOPLE", lambda: self.win.action_toggle_drawer_panel("people") if hasattr(self.win, "action_toggle_drawer_panel") else None)
        self._add_action(menu_view, self._tr("ID_VIEW_PLACES", "&Places"), "ID_VIEW_PLACES", lambda: self.win.action_toggle_drawer_panel("places") if hasattr(self.win, "action_toggle_drawer_panel") else None)
        self._add_action(menu_view, self._tr("ID_VIEW_TAGS", "&Tags"), "ID_VIEW_TAGS", lambda: self.win.action_toggle_drawer_panel("tags") if hasattr(self.win, "action_toggle_drawer_panel") else None)
        self._add_action(menu_view, self._tr("ID_VIEW_DRAWER_PROPERTIES", "Properties"), "ID_VIEW_PROPERTIES", lambda: self.win.action_toggle_drawer_panel("properties") if hasattr(self.win, "action_toggle_drawer_panel") else None)
        menu_view.addSeparator()

        # Sous-menu Thème de couleurs (ui/resources/themes/*.ini)
        from picasa_py.ui.style import PicasaStyle
        self.menu_themes = menu_view.addMenu(self._tr("ID_VIEW_COLOR_THEME", "&Color Theme"))
        self.theme_actions.clear()
        theme_group = QActionGroup(self.menu_themes)
        theme_group.setExclusive(True)
        current_tid = getattr(getattr(self.win, "style", None), "theme_id", "original")
        for tinfo in PicasaStyle.list_available_themes():
            if isinstance(tinfo, dict):
                tid = tinfo["id"]
                tname = tinfo["name"]
            else:
                tid, tname, _ = tinfo
            act = QAction(tname, self.menu_themes)
            act.setCheckable(True)
            act.setChecked(tid == current_tid)
            act.triggered.connect(
                lambda _checked=False, target_id=tid: self.win.apply_theme(target_id)
                if hasattr(self.win, "apply_theme")
                else None
            )
            theme_group.addAction(act)
            self.menu_themes.addAction(act)
            self.theme_actions[tid] = act

        # 4. &Folder
        menu_folder = mb.addMenu(self._tr("menu_folder", "&Folder"))
        self._add_action(menu_folder, self._tr("ID_FILE_LOCATEONDISK", "&Locate on Disk"), "ID_FILE_LOCATEONDISK", self.win.action_locate_on_disk if hasattr(self.win, "action_locate_on_disk") else None)
        self._add_action(menu_folder, self._tr("ID_REFRESH_THUMB", "&Refresh Thumbnail"), "ID_REFRESH_THUMB", self.win.action_refresh_thumbnails if hasattr(self.win, "action_refresh_thumbnails") else None)
        self._add_action(menu_folder, self._tr("ID_FILE_EXPORTASWEBPAGE", "Export as &Web Page..."), "ID_FILE_EXPORTASWEBPAGE", self.win.action_export_as_web_page if hasattr(self.win, "action_export_as_web_page") else None)
        menu_folder.addSeparator()
        self._add_action(menu_folder, self._tr("ID_ALBUM_EDITCAPTIONS", "&Edit Folder Description..."), "ID_ALBUM_EDITCAPTIONS", lambda: self.win.action_edit_folder_description(self.win.thumb_view.current_folder_filter or "") if hasattr(self.win, "action_edit_folder_description") else None)
        self._add_action(menu_folder, self._tr("ID_SAFE_ADD", "&Password Protect Collection..."), "ID_SAFE_ADD", self.win.action_password_protect_collection if hasattr(self.win, "action_password_protect_collection") else None)
        self._add_action(menu_folder, self._tr("ID_MOVEFOLDER", "&Move Folder..."), "ID_MOVEFOLDER", lambda: self.win.action_move_folder(self.win.thumb_view.current_folder_filter or "") if hasattr(self.win, "action_move_folder") else None)
        self._add_action(menu_folder, self._tr("ID_ALBUM_DELETE", "&Delete Folder..."), "ID_ALBUM_DELETE", lambda: self.win.action_delete_folder(self.win.thumb_view.current_folder_filter or "") if hasattr(self.win, "action_delete_folder") else None)

        # 5. &Picture
        menu_picture = mb.addMenu(self._tr("menu_picture", "&Picture"))
        self._add_action(menu_picture, self._tr("ID_PICTURE_ROTATECLOCKWISE", "Rotate &Clockwise"), "ID_PICTURE_ROTATECLOCKWISE", self.win.action_rotate_clockwise if hasattr(self.win, "action_rotate_clockwise") else None)
        self._add_action(menu_picture, self._tr("ID_PICTURE_ROTATECOUNTERCLOCKWISE", "Rotate &Counterclockwise"), "ID_PICTURE_ROTATECOUNTERCLOCKWISE", self.win.action_rotate_counterclockwise if hasattr(self.win, "action_rotate_counterclockwise") else None)
        self._add_action(menu_picture, self._tr("ID_PICTURE_STAR", "Toggle &Star"), "ID_PICTURE_STAR", self.win.action_toggle_star if hasattr(self.win, "action_toggle_star") else None)
        menu_picture.addSeparator()
        self._add_action(menu_picture, self._tr("ID_PICTURE_AUTO_LIGHTING", "Auto &Contrast"), "ID_PICTURE_AUTO_LIGHTING", self.win.action_auto_contrast if hasattr(self.win, "action_auto_contrast") else None)
        self._add_action(menu_picture, self._tr("ID_PICTURE_AUTO_COLOR", "Auto &Color"), "ID_PICTURE_AUTO_COLOR", self.win.action_auto_color if hasattr(self.win, "action_auto_color") else None)
        self._add_action(menu_picture, self._tr("ID_PICTURE_AUTO_REDEYE", "Auto &Red-Eye"), "ID_PICTURE_AUTO_REDEYE", self.win.action_auto_redeye if hasattr(self.win, "action_auto_redeye") else None)
        self._add_action(menu_picture, self._tr("ID_PICTURE_RESET_FACES", "Reset &Faces"), "ID_PICTURE_RESET_FACES", lambda: self.win.action_reset_faces(self.win._get_active_photo_paths()) if hasattr(self.win, "action_reset_faces") else None)
        self._add_action(menu_picture, self._tr("ID_PICTURE_REVERT", "&Undo All Edits"), "ID_PICTURE_REVERT", self.win.action_undo_all_edits if hasattr(self.win, "action_undo_all_edits") else None)
        menu_picture.addSeparator()
        self._add_action(menu_picture, self._tr("ID_PICTURE_PROPERTIES", "Propert&ies"), "ID_PICTURE_PROPERTIES", self.win.action_properties if hasattr(self.win, "action_properties") else None)

        # 6. &Create
        menu_create = mb.addMenu(self._tr("menu_create", "&Create"))
        self._add_action(menu_create, self._tr("ID_COLLAGEMAKER", "Picture &Collage..."), "ID_COLLAGEMAKER", self.win.action_collage if hasattr(self.win, "action_collage") else None)
        self._add_action(menu_create, self._tr("ID_POSTER", "Make a &Poster..."), "ID_POSTER", self.win.action_poster if hasattr(self.win, "action_poster") else None)

        # Movie submenu matching Picasa 3 (Ref: eMenuCreate::Movies, eMenuCreateMovie::MOVIE, eMenuCreateMovie::ID_FACES)
        menu_movie = menu_create.addMenu(self._tr("eMenuCreate::Movies", "&Movie"))
        self._add_action(menu_movie, self._tr("eMenuCreateMovie::MOVIE", "From &selection..."), "MOVIE", lambda: self.win.action_movie(face_mode=False) if hasattr(self.win, "action_movie") else None)
        self._add_action(menu_movie, self._tr("eMenuCreateMovie::ID_FACES", "From &faces in selection (Face Movie)..."), "ID_MOVIEFACES", lambda: self.win.action_movie(face_mode=True) if hasattr(self.win, "action_movie") else None)

        self._add_action(menu_create, self._tr("ID_WALLPAPER", "Set as &Desktop..."), "ID_WALLPAPER", self.win.action_set_desktop_wallpaper if hasattr(self.win, "action_set_desktop_wallpaper") else None)
        self._add_action(menu_create, self._tr("ID_SCREENSAVER", "Set as &Screensaver..."), "ID_SCREENSAVER", self.win.action_set_screensaver if hasattr(self.win, "action_set_screensaver") else None)

        # 7. &Tools
        menu_tools = mb.addMenu(self._tr("menu_tools", "&Tools"))
        self._add_action(menu_tools, self._tr("ID_TOOLS_OPTIONS", "&Options..."), "ID_TOOLS_OPTIONS", self.win.action_options if hasattr(self.win, "action_options") else None)
        self._add_action(menu_tools, self._tr("ID_TOOLS_ADJUST_TIMESTAMP", "Adjust &Date and Time..."), "ID_TOOLS_ADJUST_TIMESTAMP", self.win.action_adjust_time if hasattr(self.win, "action_adjust_time") else None)
        self._add_action(menu_tools, self._tr("ID_TOOLS_INCLUDEEXCLUDEFOLDERS", "&Folder Manager..."), "ID_TOOLS_INCLUDEEXCLUDEFOLDERS", self.win.action_folder_manager if hasattr(self.win, "action_folder_manager") else None)
        self._add_action(menu_tools, self._tr("ID_TOOLS_PEOPLE_MGR", "&People Manager..."), "ID_TOOLS_PEOPLE_MGR", self.win.action_contact_manager if hasattr(self.win, "action_contact_manager") else None)
        self._add_action(menu_tools, self._tr("ID_TOOLS_WRITE_FACETAGS", "Write &Face Tags to XMP..."), "ID_TOOLS_WRITE_FACETAGS", self.win.action_write_facetags if hasattr(self.win, "action_write_facetags") else None)
        self._add_action(menu_tools, self._tr("ID_GEOTAG_EXPORT_KML", "Export &Google Earth File (KML)..."), "ID_GEOTAG_EXPORT_KML", self.win.action_export_kml if hasattr(self.win, "action_export_kml") else None)
        self._add_action(menu_tools, self._tr("ID_TOOLS_BACKUP", "&Back Up Pictures..."), "ID_TOOLS_BACKUP", self.win.action_backup if hasattr(self.win, "action_backup") else None)
        menu_tools.addSeparator()
        self._add_action(menu_tools, self._tr("ID_CREATE_DATABASE", "Create &New Database..."), "ID_CREATE_DATABASE", (lambda _checked=False: self.win.action_create_database()) if hasattr(self.win, "action_create_database") else None)
        self._add_action(menu_tools, self._tr("ID_OPEN_DATABASE", "&Open Existing Database..."), "ID_OPEN_DATABASE", (lambda _checked=False: self.win.action_open_database()) if hasattr(self.win, "action_open_database") else None)
        self._add_action(menu_tools, self._tr("ID_MOVE_DATABASE", "&Move Database..."), "ID_MOVE_DATABASE", (lambda _checked=False: self.win.action_move_database()) if hasattr(self.win, "action_move_database") else None)
        self._add_action(menu_tools, self._tr("ID_COMPACT_DATABASE", "&Compact Database..."), "ID_COMPACT_DATABASE", (lambda _checked=False: self.win.action_compact_database()) if hasattr(self.win, "action_compact_database") else None)
        menu_tools.addSeparator()
        self._add_action(menu_tools, self._tr("ID_CLEAN_PICASA_TRACES", "Clean &Picasa Traces (.picasa.ini)..."), "ID_CLEAN_PICASA_TRACES", (lambda _checked=False: self.win.action_clean_picasa_traces()) if hasattr(self.win, "action_clean_picasa_traces") else None)

        # 8. &Help
        menu_help = mb.addMenu(self._tr("menu_help", "&Help"))
        self._add_action(menu_help, self._tr("ID_HELP_DEFAULT", "&Help Contents and Index"), "ID_HELP_DEFAULT", self.win.action_help_contents if hasattr(self.win, "action_help_contents") else None)
        self._add_action(menu_help, self._tr("ID_HELP_ABOUT", "&About Picasa..."), "ID_HELP_ABOUT", self.win.action_about if hasattr(self.win, "action_about") else None)
        self._add_action(menu_help, self._tr("ID_HELP_KEYBOARD_SHORTCUTS", "&Keyboard Shortcuts"), "ID_HELP_KEYBOARD_SHORTCUTS", self.win.action_keyboard_shortcuts if hasattr(self.win, "action_keyboard_shortcuts") else None)
        self._add_action(menu_help, self._tr("ID_HELP_PRIVACY", "&Privacy Policy"), "ID_HELP_PRIVACY", self.win.action_privacy_policy if hasattr(self.win, "action_privacy_policy") else None)

        return mb

    def _add_action(
        self,
        menu: QMenu,
        text: str,
        cmd_id: str,
        callback: Optional[Any] = None
    ) -> QAction:
        action = menu.addAction(text)
        action.setObjectName(cmd_id)
        action.setData(cmd_id)
        if cmd_id in self.shortcuts:
            action.setShortcut(QKeySequence(self.shortcuts[cmd_id]))
        if callback:
            action.triggered.connect(callback)
        return action
