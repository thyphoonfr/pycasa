"""
FR: Menus contextuels Picasa 3 (clic droit) pour les photos, dossiers, albums et personnes.
EN: Picasa 3 Context Menus (Right-Click Menus) for Photos, Folders, Albums, and People.

Reverse-engineered directly from picasa3.exe binary:
Ref: picasa3.exe @ 0x00CADB44 - 0x00CAE010 (AlbumPhoto / FolderPhoto string table)
Ref: picasa3.exe @ 0x00CAE090 - 0x00CAE2F0 (Folder context menu strings)
Ref: picasa3.exe @ 0x00CAE3C4 - 0x00CAE460 (Album context menu strings)
Ref: picasa3.exe @ 0x00CAF1B8 - 0x00CAF2B8 (PplAlbumPhoto string table)
Ref: picasa3.exe @ 0x00CAF334 - 0x00CAF2B8 (PplAlbum context menu strings)
Ref: picasa3.exe @ 0x005E7C20, 0x005E7CD7 (TrackPopupMenu dispatch)
Ref: picasa3.exe @ 0x007319F0 (Folder context menu builder)
Ref: picasa3.exe @ 0x00732160 (Album context menu builder)
Ref: picasa3.exe @ 0x007359E0 (People Album context menu builder)
Ref: picasa3.exe @ 0x005D41F4 (Listbox right click handler "lb_rightclick")
"""

from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from PySide6.QtWidgets import QMenu, QWidget, QApplication, QMessageBox, QInputDialog
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QImage
from PySide6.QtCore import Qt, QPoint

from picasa_py.db.database import PicasaDatabase


def recycle_or_delete_file(file_path: str) -> bool:
    """
    FR: Supprime un fichier en l'envoyant vers la Corbeille du système (Windows SHFileOperationW,
    macOS ~/.Trash ou Linux FreeDesktop ~/.local/share/Trash) si possible, ou par suppression directe sinon.
    EN: Deletes a file by moving it to the system Trash/Recycle Bin (Windows SHFileOperationW,
    macOS ~/.Trash, or Linux FreeDesktop ~/.local/share/Trash) when possible, or falls back to direct removal.
    Ref: picasa3.exe @ 0x004A0410 (DeleteFile / SHFileOperationW FO_DELETE)
    """
    if not os.path.exists(file_path):
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class SHFILEOPSTRUCTW(ctypes.Structure):
                """
                FR: Structure Win32 SHFILEOPSTRUCTW pour les opérations de fichiers Shell (Corbeille).
                EN: Win32 SHFILEOPSTRUCTW structure for Shell file operations (Recycle Bin).
                """
                _fields_ = [
                    ('hwnd', wintypes.HWND),
                    ('wFunc', wintypes.UINT),
                    ('pFrom', wintypes.LPCWSTR),
                    ('pTo', wintypes.LPCWSTR),
                    ('fFlags', ctypes.c_uint16),
                    ('fAnyOperationsAborted', wintypes.BOOL),
                    ('hNameMappings', wintypes.LPVOID),
                    ('lpszProgressTitle', wintypes.LPCWSTR)
                ]

            FO_DELETE = 3
            FOF_ALLOWUNDO = 0x0040
            FOF_NOCONFIRMATION = 0x0010
            FOF_SILENT = 0x0004

            path_double_null = os.path.abspath(file_path) + "\0\0"
            fileop = SHFILEOPSTRUCTW()
            fileop.hwnd = None
            fileop.wFunc = FO_DELETE
            fileop.pFrom = path_double_null
            fileop.pTo = None
            fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
            fileop.fAnyOperationsAborted = False
            fileop.hNameMappings = None
            fileop.lpszProgressTitle = None

            res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
            if res == 0 and not fileop.fAnyOperationsAborted:
                return True
        except Exception:
            pass

    try:
        import send2trash
        send2trash.send2trash(file_path)
        return True
    except ImportError:
        pass
    except Exception:
        pass

    # FR: Solution de repli multi-OS pour macOS (~/.Trash) et Linux FreeDesktop (~/.local/share/Trash)
    # EN: Multi-OS fallback for macOS (~/.Trash) and Linux FreeDesktop (~/.local/share/Trash)
    if sys.platform == "darwin":
        try:
            import shutil
            trash_dir = Path.home() / ".Trash"
            trash_dir.mkdir(parents=True, exist_ok=True)
            src = Path(file_path)
            dest = trash_dir / src.name
            counter = 1
            while dest.exists():
                dest = trash_dir / f"{src.stem}_{counter}{src.suffix}"
                counter += 1
            shutil.move(str(src), str(dest))
            return True
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            import shutil
            import urllib.parse
            from datetime import datetime
            xdg_data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
            trash_base = Path(xdg_data) / "Trash"
            files_dir = trash_base / "files"
            info_dir = trash_base / "info"
            files_dir.mkdir(parents=True, exist_ok=True)
            info_dir.mkdir(parents=True, exist_ok=True)
            src = Path(file_path).resolve()
            dest_name = src.name
            counter = 1
            while (files_dir / dest_name).exists() or (info_dir / f"{dest_name}.trashinfo").exists():
                dest_name = f"{src.stem}_{counter}{src.suffix}"
                counter += 1
            info_path = info_dir / f"{dest_name}.trashinfo"
            del_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            encoded_path = urllib.parse.quote(str(src), safe="/")
            info_path.write_text(
                f"[Trash Info]\nPath={encoded_path}\nDeletionDate={del_date}\n",
                encoding="utf-8",
            )
            shutil.move(str(src), str(files_dir / dest_name))
            return True
        except Exception:
            pass

    try:
        if os.path.isdir(file_path):
            import shutil
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
        return True
    except Exception:
        return False


def _tr(en: str, fr: str, res_id: Optional[str] = None) -> str:
    """
    FR: Traduction d'un élément de menu contextuel d'après STRINGRES_FR.XML ou la langue active.
    EN: Translates a context menu item using STRINGRES XML or the active language.
    Ref: picasa3.exe @ 0x004055D4, i18n/stringres.xml
    """
    try:
        from picasa_py.ui.resources import PicasaResourceManager
        rm = PicasaResourceManager.get()
        lang = rm.get_current_language().lower()
        if lang.startswith("fr"):
            if res_id:
                val = rm.get_stringres(res_id, "")
                if val:
                    return val
            return fr
        elif res_id and not lang.startswith("en"):
            val = rm.get_stringres(res_id, "")
            if val:
                return val
    except Exception:
        pass
    return en


class PicasaContextMenuBuilder:
    """
    FR: Constructeur des menus contextuels conformes à picasa3.exe.
    EN: Context menu builder matching picasa3.exe.
    """

    @staticmethod
    def build_photo_context_menu(
        parent: QWidget,
        photo_paths: List[str],
        db: Optional[PicasaDatabase] = None,
        is_in_album: bool = False,
        main_win: Optional[Any] = None,
        contact_id: Optional[str] = None,
        face_rect: Optional[Any] = None,
        suggestion: Optional[Any] = None,
    ) -> Optional[QMenu]:
        """
        FR: Construit le menu contextuel photo (AlbumPhoto / FolderPhoto / PplAlbumPhoto).
        EN: Builds the photo context menu (AlbumPhoto / FolderPhoto / PplAlbumPhoto).
        Ref: picasa3.exe @ 0x00CADB44 - 0x00CAE010 (AlbumPhoto/FolderPhoto)
        Ref: picasa3.exe @ 0x00CAF1B8 - 0x00CAF2B8 (PplAlbumPhoto)
        Ref: picasa3.exe @ faceheaderpanel/confirmsel, removesel
        """
        if not photo_paths:
            return None

        single_path = photo_paths[0]
        count = len(photo_paths)
        menu = QMenu(parent)

        # FR: 0. Actions de suggestion si l'élément sélectionné est une suggestion
        # EN: 0. Suggestion actions when the selected item is a face suggestion
        if suggestion and db and getattr(db, "face_manager", None):
            act_sug_yes = menu.addAction(_tr("✔ Confirm this suggestion", "✔ Confirmer cette suggestion"))
            act_sug_yes.triggered.connect(lambda: db.face_manager.confirm_suggestion(suggestion))
            act_sug_no = menu.addAction(_tr("✘ Reject this suggestion", "✘ Rejeter cette suggestion"))
            act_sug_no.triggered.connect(lambda: db.face_manager.reject_suggestion(suggestion))
            menu.addSeparator()

        # 1. &View and Edit (ID_PICTURE_VIEW)
        act_view = menu.addAction(_tr("&View and Edit", "&Afficher et modifier", "AlbumPhoto::ID_PICTURE_VIEW"))
        act_view.setShortcut(QKeySequence("Enter"))
        if main_win and hasattr(main_win, "action_view_and_edit"):
            act_view.triggered.connect(lambda: main_win.action_view_and_edit(single_path))

        # 2. &Add to Album (Submenu: ID_LABELS)
        menu_album = menu.addMenu(_tr("&Add to Album", "&Ajouter à l'album", "AlbumPhoto::ID_LABELS"))
        PicasaContextMenuBuilder._populate_add_to_album_menu(menu_album, photo_paths, db, main_win)

        menu.addSeparator()

        # 3. &Rotate Clockwise (ID_PICTURE_ROTATECLOCKWISE, Ctrl+R / F6)
        act_rot_cw = menu.addAction(_tr("&Rotate Clockwise", "Faire pivoter vers la &droite", "AlbumPhoto::ID_PICTURE_ROTATECLOCKWISE"))
        act_rot_cw.setShortcut(QKeySequence("Ctrl+R"))
        if main_win and hasattr(main_win, "action_rotate_clockwise"):
            act_rot_cw.triggered.connect(lambda: main_win.action_rotate_clockwise(photo_paths))

        # 4. Rotate &Counterclockwise (ID_PICTURE_ROTATECOUNTERCLOCKWISE, Ctrl+Shift+R / F7)
        act_rot_ccw = menu.addAction(_tr("Rotate &Counterclockwise", "Ro&tation vers la gauche", "AlbumPhoto::ID_PICTURE_ROTATECOUNTERCLOCKWISE"))
        act_rot_ccw.setShortcut(QKeySequence("Ctrl+Shift+R"))
        if main_win and hasattr(main_win, "action_rotate_counterclockwise"):
            act_rot_ccw.triggered.connect(lambda: main_win.action_rotate_counterclockwise(photo_paths))

        # 4 bis. Add/Remove Star (ID_PICTURE_STAR, Ctrl+T, Ref: 0x0088F6FC, 0x0068B800)
        act_star = menu.addAction(_tr("Add/Remove &Star", "Ajouter/Supprimer une &étoile"))
        act_star.setShortcut(QKeySequence("Ctrl+T"))
        if main_win and hasattr(main_win, "action_toggle_star"):
            act_star.triggered.connect(lambda: main_win.action_toggle_star(photo_paths))

        # 5. Undo all &Edits (ID_PICTURE_REVERT)
        act_revert = menu.addAction(_tr("Undo all &Edits", "A&nnuler toutes les modifications", "AlbumPhoto::ID_PICTURE_REVERT"))
        if main_win and hasattr(main_win, "action_undo_all_edits"):
            act_revert.triggered.connect(lambda: main_win.action_undo_all_edits(photo_paths))

        menu.addSeparator()

        # 6. &Open File (ID_FILE_OPENINANEDITOR)
        act_open_file = menu.addAction(_tr("&Open File", "Ouvrir le &fichier", "AlbumPhoto::ID_FILE_OPENINANEDITOR"))
        if main_win and hasattr(main_win, "action_open_file"):
            act_open_file.triggered.connect(lambda: main_win.action_open_file(single_path))

        # 7. Locate on &Disk (ID_FILE_LOCATEONDISK)
        act_locate_disk = menu.addAction(_tr("Locate on &Disk", "Rechercher sur le &disque", "AlbumPhotoWin::ID_FILE_LOCATEONDISK"))
        if main_win and hasattr(main_win, "action_locate_on_disk"):
            act_locate_disk.triggered.connect(lambda: main_win.action_locate_on_disk(single_path))

        # FR: Si on est dans un album virtuel : &Locate in Picasa / EN: When inside a virtual album: &Locate in Picasa
        if is_in_album:
            act_locate_pic = menu.addAction(_tr("&Locate in Picasa", "&Rechercher dans Picasa", "AlbumPhoto::ID_FILE_LOCATEINPICASA"))
            if main_win and hasattr(main_win, "action_locate_in_picasa"):
                act_locate_pic.triggered.connect(lambda: main_win.action_locate_in_picasa(single_path))

        # 8. Copy Full &Path (ID_COPY_PATH)
        act_copy_path = menu.addAction(_tr("Copy Full &Path", "Copier le chemin &complet", "AlbumPhoto::ID_COPY_PATH"))
        if main_win and hasattr(main_win, "action_copy_path"):
            act_copy_path.triggered.connect(lambda: main_win.action_copy_path(single_path))

        # 9. &Copy (ID_EDIT_COPY, Ctrl+C)
        act_copy = menu.addAction(_tr("&Copy", "&Copier"))
        act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        if main_win and hasattr(main_win, "action_copy"):
            act_copy.triggered.connect(lambda: main_win.action_copy(single_path))

        # 9 bis. Copy All Effects (ID_EDIT_COPYALLEFFECTS, Ctrl+Shift+C)
        act_copy_eff = menu.addAction(_tr("Copy All &Effects", "Copier tous les &effets"))
        act_copy_eff.setShortcut(QKeySequence("Ctrl+Shift+C"))
        if main_win and hasattr(main_win, "action_copy_all_effects"):
            act_copy_eff.triggered.connect(main_win.action_copy_all_effects)

        # 9 ter. Paste All Effects (ID_EDIT_PASTEALLEFFECTS, Ctrl+Shift+V)
        act_paste_eff = menu.addAction(_tr("Paste All E&ffects", "Coller tous les e&ffets"))
        act_paste_eff.setShortcut(QKeySequence("Ctrl+Shift+V"))
        if main_win and hasattr(main_win, "action_paste_all_effects"):
            act_paste_eff.triggered.connect(lambda: main_win.action_paste_all_effects(photo_paths))

        if contact_id:
            # PplAlbumPhoto::ID_PEOPLEALBUMS (0x00CAF244) -> Move to People Album submenu
            menu_move_person = menu.addMenu(
                _tr("&Move to People Album", "&Ajouter à l'album dédié à la personne", "PplAlbumPhoto::ID_PEOPLEALBUMS")
            )
            PicasaContextMenuBuilder._populate_move_to_person_menu(
                menu_move_person, single_path, face_rect, contact_id, db, main_win
            )

            # PplAlbumPhoto::ID_PEOPLEALBUMSNEW (0x00CAF27C) -> Move to New Person...
            act_new_person = menu.addAction(
                _tr("Move to &New Person...", "Déplacer vers une &nouvelle personne...", "PplAlbumPhoto::ID_PEOPLEALBUMSNEW")
            )
            if main_win and hasattr(main_win, "action_move_face_to_new_person"):
                act_new_person.triggered.connect(
                    lambda: main_win.action_move_face_to_new_person(single_path, face_rect, source_contact_id=contact_id)
                )

            # Set as People Album Thumbnail (Ref: PplAlbumPhoto::ID_SETPEOPLEALBUMCOVER, 0x00CAF214)
            act_cover = menu.addAction(
                _tr("&Set as People Album Thumbnail", "&Définir en tant que vignette de votre album", "PplAlbumPhoto::ID_SETPEOPLEALBUMCOVER")
            )
            if main_win and hasattr(main_win, "action_set_person_album_cover"):
                act_cover.triggered.connect(
                    lambda: main_win.action_set_person_album_cover(contact_id, single_path, face_rect)
                )

            # Create Face Movie (Ref: CMakeFaceMoviePanel, ID_MOVIEFACES)
            act_facemovie = menu.addAction(
                _tr("Create &Face Movie...", "Créer un &film avec des visages...")
            )
            if main_win and hasattr(main_win, "action_movie"):
                act_facemovie.triggered.connect(
                    lambda: main_win.action_movie(face_mode=True, contact_id=contact_id)
                )

        if not is_in_album and not contact_id:
            # FolderPhoto::ID_FILE_MOVETOFOLDER (0x00CADC5C)
            act_mov_f = menu.addAction(_tr("&Move to New Folder...", "&Déplacer vers un nouveau dossier...", "FolderPhoto::ID_ALBUM_NEW"))
            if main_win and hasattr(main_win, "action_move_photos_to_folder"):
                act_mov_f.triggered.connect(lambda: main_win.action_move_photos_to_folder(photo_paths))

            # FolderPhoto::ID_FILE_SPLITFOLDERHERE (0x00CADC90)
            act_split_f = menu.addAction(_tr("&Split Folder Here...", "Diviser le dossier &ici...", "FolderPhoto::ID_PICTURE_SPLITALBUMHERE"))
            if main_win and hasattr(main_win, "action_split_folder_here"):
                act_split_f.triggered.connect(lambda: main_win.action_split_folder_here(single_path))

        # Create Movie (Ref: CMakeMoviePanel, ID_MAKEMOVIE)
        act_movie = menu.addAction(_tr("Create &Movie...", "Créer un &film..."))
        if main_win and hasattr(main_win, "action_movie"):
            act_movie.triggered.connect(lambda: main_win.action_movie(face_mode=False))

        menu.addSeparator()

        # 10. &Rename... (ID_FILE_RENAME, F2)
        act_rename = menu.addAction(_tr("&Rename...", "&Renommer..."))
        act_rename.setShortcut(QKeySequence("F2"))
        if main_win and hasattr(main_win, "action_rename"):
            act_rename.triggered.connect(main_win.action_rename)

        # 11. Adjust &Date and Time... (ID_TOOLS_ADJUST_TIMESTAMP)
        act_date = menu.addAction(_tr("Adjust &Date and Time...", "Ajuster la &date et l'heure..."))
        if main_win and hasattr(main_win, "action_adjust_time"):
            act_date.triggered.connect(main_win.action_adjust_time)

        # 12. &Delete from Disk... ou &Remove from Album / People Album (ID_FILE_DELETEFROMDISK)
        if contact_id:
            # Ref: picasa3.exe @ PplAlbumPhoto::ID_FILE_DELETEFROMDISK (0x00CAF1B8, 0x00CAF1E0)
            act_del = menu.addAction(
                _tr("&Remove from People Album", "&Supprimer de l'album dédié à la personne", "PplAlbumPhoto::ID_FILE_DELETEFROMDISK")
            )
            if main_win and hasattr(main_win, "action_remove_from_person"):
                act_del.triggered.connect(lambda: main_win.action_remove_from_person(contact_id, photo_paths, face_rect))
        elif is_in_album:
            act_del = menu.addAction(
                _tr("&Remove from Album", "&Supprimer de l'album", "AlbumPhoto::ID_FILE_DELETEFROMDISK")
            )
            if main_win and hasattr(main_win, "action_remove_from_album"):
                act_del.triggered.connect(lambda: main_win.action_remove_from_album(photo_paths))
        else:
            act_del = menu.addAction(
                _tr("&Delete from Disk...", "&Supprimer du disque...", "FolderPhoto::ID_FILE_DELETEFROMDISK")
            )
            act_del.setShortcut(QKeySequence.StandardKey.Delete)
            if main_win and hasattr(main_win, "action_delete_from_disk"):
                act_del.triggered.connect(lambda: main_win.action_delete_from_disk(photo_paths))

        # 13. Reset &Faces (ID_PICTURE_RESET_FACES)
        act_reset_faces = menu.addAction(
            _tr("Reset &Faces", "Réinitialiser les &visages", "AlbumPhoto::ID_PICTURE_RESET_FACES")
        )
        if main_win and hasattr(main_win, "action_reset_faces"):
            act_reset_faces.triggered.connect(lambda: main_win.action_reset_faces(photo_paths))

        # 14. Set as &Desktop... (ID_WALLPAPER)
        act_wallpaper = menu.addAction(
            _tr("Set as &Desktop...", "&Définir comme fond d'écran...", "eMenuCreate::ID_WALLPAPER")
        )
        if main_win and hasattr(main_win, "action_set_desktop_wallpaper"):
            act_wallpaper.triggered.connect(lambda: main_win.action_set_desktop_wallpaper(photo_paths))

        # 15. Propert&ies (ID_PICTURE_PROPERTIES, Alt+Enter)
        act_prop = menu.addAction(
            _tr("Propert&ies", "Propr&iétés", "AlbumPhotoWin::ID_PICTURE_PROPERTIES")
        )
        act_prop.setShortcut(QKeySequence("Alt+Enter"))
        if main_win and hasattr(main_win, "action_properties"):
            act_prop.triggered.connect(main_win.action_properties)

        return menu

    @staticmethod
    def show_photo_context_menu(
        parent: QWidget,
        global_pos: QPoint,
        photo_paths: List[str],
        db: Optional[PicasaDatabase] = None,
        is_in_album: bool = False,
        main_win: Optional[Any] = None,
        contact_id: Optional[str] = None,
        face_rect: Optional[Any] = None,
        suggestion: Optional[Any] = None,
    ) -> Optional[QAction]:
        """
        FR: Construit et affiche de manière modale le menu contextuel d'une ou plusieurs photos.
        EN: Builds and modally executes the context menu for one or more photos at global_pos.
        """
        menu = PicasaContextMenuBuilder.build_photo_context_menu(
            parent, photo_paths, db=db, is_in_album=is_in_album, main_win=main_win,
            contact_id=contact_id, face_rect=face_rect, suggestion=suggestion
        )
        return menu.exec(global_pos) if menu else None

    @staticmethod
    def build_folder_context_menu(
        parent: QWidget,
        folder_path: str,
        db: Optional[PicasaDatabase] = None,
        main_win: Optional[Any] = None
    ) -> QMenu:
        """
        FR: Construit le menu contextuel d'un dossier (Folder::*).
        EN: Builds the context menu for a folder (Folder::*).
        Ref: picasa3.exe @ 0x007319F0, 0x00CAE090 - 0x00CAE2F0
        """
        menu = QMenu(parent)

        # 1. Play &Slideshow (ID_VIEW_SLIDESHOW, Ctrl+4)
        act_ss = menu.addAction(_tr("Play &Slideshow", "Afficher le &diaporama", "eMenuLabelFolder::ID_ALBUM_SLIDESHOW"))
        act_ss.setShortcut(QKeySequence("Ctrl+4"))
        if main_win and hasattr(main_win, "action_slideshow_for_folder"):
            act_ss.triggered.connect(lambda: main_win.action_slideshow_for_folder(folder_path))

        menu.addSeparator()

        # 2. &Edit Folder Description... (ID_ALBUM_EDITCAPTIONS)
        act_desc = menu.addAction(_tr("&Edit Folder Description...", "&Modifier la description du dossier...", "Folder::ID_ALBUM_EDITCAPTIONS"))
        if main_win and hasattr(main_win, "action_edit_folder_description"):
            act_desc.triggered.connect(lambda: main_win.action_edit_folder_description(folder_path))

        # Folder::ID_MOVEFOLDER (0x00CAE1F8, 0x00CAE2C4)
        act_mov = menu.addAction(_tr("&Move Folder...", "&Déplacer le dossier...", "Folder::ID_MOVEFOLDER"))
        if main_win and hasattr(main_win, "action_move_folder"):
            act_mov.triggered.connect(lambda: main_win.action_move_folder(folder_path))

        menu.addSeparator()

        # 3. Select &All (ID_ALBUM_SELECTALLPICTURES, Ctrl+A)
        act_sel_all = menu.addAction(_tr("Select &All", "&Tout sélectionner"))
        act_sel_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        if main_win and hasattr(main_win, "action_select_all"):
            act_sel_all.triggered.connect(main_win.action_select_all)

        # 4. Clear Selection (ID_CLEAR_SELECTION)
        act_clear_sel = menu.addAction(_tr("Clear Selection", "&Effacer la sélection", "Folder::ID_CLEAR_SELECTION"))
        if main_win and hasattr(main_win, "action_clear_selection"):
            act_clear_sel.triggered.connect(main_win.action_clear_selection)

        # 5. &Invert Selection (ID_SELECT_INVERT)
        act_inv_sel = menu.addAction(_tr("&Invert Selection", "&Inverser la sélection"))
        if main_win and hasattr(main_win, "action_invert_selection"):
            act_inv_sel.triggered.connect(main_win.action_invert_selection)

        menu.addSeparator()

        # S&ort Folder By (SortFolderBy, 0x00CAE2A8)
        menu_sort = menu.addMenu(_tr("S&ort Folder By", "T&rier le dossier par", "Folder::SortFolderBy"))
        act_sort_name = menu_sort.addAction(_tr("Name", "&Nom", "Sort::ID_NAMESORT"))
        if main_win and hasattr(main_win, "action_sort_folder_by"):
            act_sort_name.triggered.connect(lambda: main_win.action_sort_folder_by("name"))
        act_sort_date = menu_sort.addAction(_tr("Date", "&Date", "Sort::ID_DATESORT"))
        if main_win and hasattr(main_win, "action_sort_folder_by"):
            act_sort_date.triggered.connect(lambda: main_win.action_sort_folder_by("date"))
        act_sort_size = menu_sort.addAction(_tr("Size", "&Taille", "Sort::ID_SIZESORT"))
        if main_win and hasattr(main_win, "action_sort_folder_by"):
            act_sort_size.triggered.connect(lambda: main_win.action_sort_folder_by("size"))

        menu.addSeparator()

        # 6. &Refresh Thumbnail (ID_REFRESH_THUMB)
        act_refresh = menu.addAction(_tr("&Refresh Thumbnail", "Actualiser les &vignettes", "Folder::ID_REFRESH_THUMB"))
        if main_win and hasattr(main_win, "action_refresh_thumbnails"):
            act_refresh.triggered.connect(lambda: main_win.action_refresh_thumbnails(folder_path))

        # 7. Locate on &Disk (ID_ALBUM_LOCATEONDISK)
        act_locate = menu.addAction(_tr("Locate on &Disk", "Rechercher sur le &disque", "AlbumPhotoWin::ID_FILE_LOCATEONDISK"))
        if main_win and hasattr(main_win, "action_locate_on_disk"):
            act_locate.triggered.connect(lambda: main_win.action_locate_on_disk(folder_path))

        # 8. &Folder Manager... (ID_MANAGE_ALBUM)
        act_fm = menu.addAction(_tr("&Folder Manager...", "Gestionnaire de &dossiers..."))
        if main_win and hasattr(main_win, "action_folder_manager"):
            act_fm.triggered.connect(main_win.action_folder_manager)

        # 9. &Delete Folder... (ID_ALBUM_DELETE)
        act_del = menu.addAction(_tr("&Delete Folder...", "&Supprimer le dossier...", "Folder::ID_ALBUM_DELETE"))
        if main_win and hasattr(main_win, "action_delete_folder"):
            act_del.triggered.connect(lambda: main_win.action_delete_folder(folder_path))

        menu.addSeparator()

        # 10. Export as &Web Page... (ID_ALBUM_MAKE_WEB)
        act_web = menu.addAction(_tr("Export as &Web Page...", "E&xporter sous forme de page HTML...", "eMenuLabelFolder::ID_FILE_EXPORTASWEBPAGE"))
        if main_win and hasattr(main_win, "action_export_as_web_page"):
            act_web.triggered.connect(lambda: main_win.action_export_as_web_page(folder_path))

        return menu

    @staticmethod
    def show_folder_context_menu(
        parent: QWidget,
        global_pos: QPoint,
        folder_path: str,
        db: Optional[PicasaDatabase] = None,
        main_win: Optional[Any] = None
    ) -> Optional[QAction]:
        """
        FR: Construit et affiche de manière modale le menu contextuel d'un dossier.
        EN: Builds and modally executes the context menu for a folder at global_pos.
        """
        menu = PicasaContextMenuBuilder.build_folder_context_menu(
            parent, folder_path, db=db, main_win=main_win
        )
        return menu.exec(global_pos) if menu else None

    @staticmethod
    def build_album_context_menu(
        parent: QWidget,
        album_name: str,
        db: Optional[PicasaDatabase] = None,
        main_win: Optional[Any] = None
    ) -> QMenu:
        """
        FR: Construit le menu contextuel d'un album virtuel (Album::*).
        EN: Builds the context menu for a virtual album (Album::*).
        Ref: picasa3.exe @ 0x00732160, 0x00CAE3C4 - 0x00CAE460
        """
        menu = QMenu(parent)

        # 1. Play &Slideshow (ID_VIEW_SLIDESHOW, Ctrl+4)
        act_ss = menu.addAction(_tr("Play &Slideshow", "Afficher le &diaporama", "eMenuLabelFolder::ID_ALBUM_SLIDESHOW"))
        act_ss.setShortcut(QKeySequence("Ctrl+4"))
        if main_win and hasattr(main_win, "action_slideshow_for_album"):
            act_ss.triggered.connect(lambda: main_win.action_slideshow_for_album(album_name))

        menu.addSeparator()

        # 2. &Edit Album Description... (ID_ALBUM_EDITCAPTIONS)
        act_desc = menu.addAction(_tr("&Edit Album Description...", "&Modifier la description de l'album..."))
        if main_win and hasattr(main_win, "action_edit_album_description"):
            act_desc.triggered.connect(lambda: main_win.action_edit_album_description(album_name))

        menu.addSeparator()

        # 3. Select &All (ID_ALBUM_SELECTALLPICTURES, Ctrl+A)
        act_sel_all = menu.addAction(_tr("Select &All", "&Tout sélectionner"))
        act_sel_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        if main_win and hasattr(main_win, "action_select_all"):
            act_sel_all.triggered.connect(main_win.action_select_all)

        # 4. Clear Selection (ID_CLEAR_SELECTION)
        act_clear_sel = menu.addAction(_tr("Clear Selection", "&Effacer la sélection"))
        if main_win and hasattr(main_win, "action_clear_selection"):
            act_clear_sel.triggered.connect(main_win.action_clear_selection)

        # 5. &Invert Selection (ID_SELECT_INVERT)
        act_inv_sel = menu.addAction(_tr("&Invert Selection", "&Inverser la sélection"))
        if main_win and hasattr(main_win, "action_invert_selection"):
            act_inv_sel.triggered.connect(main_win.action_invert_selection)

        menu.addSeparator()

        # Sort &Album By (SortAlbumBy, 0x00CAE418)
        menu_sort = menu.addMenu(_tr("Sort &Album By", "Trier l'&album par", "Album::SortAlbumBy"))
        act_sort_name = menu_sort.addAction(_tr("Name", "&Nom", "Sort::ID_NAMESORT"))
        if main_win and hasattr(main_win, "action_sort_album_by"):
            act_sort_name.triggered.connect(lambda: main_win.action_sort_album_by("name"))
        act_sort_date = menu_sort.addAction(_tr("Date", "&Date", "Sort::ID_DATESORT"))
        if main_win and hasattr(main_win, "action_sort_album_by"):
            act_sort_date.triggered.connect(lambda: main_win.action_sort_album_by("date"))
        act_sort_size = menu_sort.addAction(_tr("Size", "&Taille", "Sort::ID_SIZESORT"))
        if main_win and hasattr(main_win, "action_sort_album_by"):
            act_sort_size.triggered.connect(lambda: main_win.action_sort_album_by("size"))

        menu.addSeparator()

        # 6. &Refresh Thumbnail (ID_REFRESH_THUMB)
        act_refresh = menu.addAction(_tr("&Refresh Thumbnail", "Actualiser les &vignettes"))
        if main_win and hasattr(main_win, "action_refresh_thumbnails"):
            act_refresh.triggered.connect(lambda: main_win.action_refresh_thumbnails(album_name))

        # 7. &Delete Album... (ID_ALBUM_DELETE)
        act_del = menu.addAction(_tr("&Delete Album...", "&Supprimer l'album..."))
        if main_win and hasattr(main_win, "action_delete_album"):
            act_del.triggered.connect(lambda: main_win.action_delete_album(album_name))

        menu.addSeparator()

        # 8. Export as &Web Page... (ID_ALBUM_MAKE_WEB)
        act_web = menu.addAction(_tr("Export as &Web Page...", "E&xporter sous forme de page HTML...", "eMenuLabelFolder::ID_FILE_EXPORTASWEBPAGE"))
        if main_win and hasattr(main_win, "action_export_as_web_page"):
            act_web.triggered.connect(lambda: main_win.action_export_as_web_page(album_name))

        return menu

    @staticmethod
    def show_album_context_menu(
        parent: QWidget,
        global_pos: QPoint,
        album_name: str,
        db: Optional[PicasaDatabase] = None,
        main_win: Optional[Any] = None
    ) -> Optional[QAction]:
        """
        FR: Construit et affiche de manière modale le menu contextuel d'un album virtuel.
        EN: Builds and modally executes the context menu for a virtual album at global_pos.
        """
        menu = PicasaContextMenuBuilder.build_album_context_menu(
            parent, album_name, db=db, main_win=main_win
        )
        return menu.exec(global_pos) if menu else None

    @staticmethod
    def build_person_context_menu(
        parent: QWidget,
        contact_id: str,
        person_name: str,
        db: Optional[PicasaDatabase] = None,
        main_win: Optional[Any] = None
    ) -> QMenu:
        """
        FR: Construit le menu contextuel d'un album de contact / personne (PplAlbum::*).
        EN: Builds the context menu for a contact / person album (PplAlbum::*).
        Ref: picasa3.exe @ 0x007359E0, 0x00CAF334 - 0x00CAF2B8
        """
        menu = QMenu(parent)

        # 1. Play &Slideshow (ID_VIEW_SLIDESHOW, Ctrl+4)
        act_ss = menu.addAction(_tr("Play &Slideshow", "Afficher le &diaporama", "eMenuLabelFolder::ID_ALBUM_SLIDESHOW"))
        act_ss.setShortcut(QKeySequence("Ctrl+4"))
        if main_win and hasattr(main_win, "action_slideshow_for_person"):
            act_ss.triggered.connect(lambda: main_win.action_slideshow_for_person(contact_id))

        # 1 bis. Create &Face Movie... (Ref: CMakeFaceMoviePanel, ID_MOVIEFACES)
        act_fm = menu.addAction(_tr("Create &Face Movie...", "Créer un &film avec des visages..."))
        if main_win and hasattr(main_win, "action_movie"):
            act_fm.triggered.connect(lambda: main_win.action_movie(face_mode=True, contact_id=contact_id))

        menu.addSeparator()

        # 2. &Edit Person... (ID_ALBUM_EDITCAPTIONS)
        act_edit = menu.addAction(_tr("&Edit Person...", "Modifi&er l'album dédié à la personne...", "PplAlbum::ID_ALBUM_EDITCAPTIONS"))
        if main_win and hasattr(main_win, "action_edit_person"):
            act_edit.triggered.connect(lambda: main_win.action_edit_person(contact_id, person_name))

        menu.addSeparator()

        # 3. Select &All (ID_ALBUM_SELECTALLPICTURES, Ctrl+A)
        act_sel_all = menu.addAction(_tr("Select &All", "Tout &sélectionner", "PplAlbum::ID_ALBUM_SELECTALLPICTURES"))
        act_sel_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        if main_win and hasattr(main_win, "action_select_all"):
            act_sel_all.triggered.connect(main_win.action_select_all)

        # 4. Clear Selection (ID_CLEAR_SELECTION)
        act_clear_sel = menu.addAction(_tr("Clear Selection", "&Effacer la sélection", "PplAlbum::ID_CLEAR_SELECTION"))
        if main_win and hasattr(main_win, "action_clear_selection"):
            act_clear_sel.triggered.connect(main_win.action_clear_selection)

        menu.addSeparator()

        # 5. &Delete Person... (ID_ALBUM_DELETE)
        act_del = menu.addAction(_tr("&Delete Person...", "&Supprimer l'album dédié à la personne", "PplAlbum::ID_ALBUM_DELETE"))
        if main_win and hasattr(main_win, "action_delete_person"):
            act_del.triggered.connect(lambda: main_win.action_delete_person(contact_id, person_name))

        return menu

    @staticmethod
    def show_person_context_menu(
        parent: QWidget,
        global_pos: QPoint,
        contact_id: str,
        person_name: str,
        db: Optional[PicasaDatabase] = None,
        main_win: Optional[Any] = None
    ) -> Optional[QAction]:
        """
        FR: Construit et affiche de manière modale le menu contextuel d'une personne.
        EN: Builds and modally executes the context menu for a person album at global_pos.
        """
        menu = PicasaContextMenuBuilder.build_person_context_menu(
            parent, contact_id, person_name, db=db, main_win=main_win
        )
        return menu.exec(global_pos) if menu else None

    @staticmethod
    def _populate_add_to_album_menu(
        menu: QMenu,
        photo_paths: List[str],
        db: Optional[PicasaDatabase],
        main_win: Optional[Any]
    ) -> None:
        """
        FR: Construit le sous-menu "Add to Album" avec les albums existants et "New Album...".
        EN: Populates the "Add to Album" submenu with existing albums and "New Album...".
        """
        # "New Album..."
        act_new = menu.addAction(_tr("&New Album...", "&Nouvel album..."))
        if main_win and hasattr(main_win, "action_new_album_with_photos"):
            act_new.triggered.connect(lambda: main_win.action_new_album_with_photos(photo_paths))

        menu.addSeparator()

        # FR: Récupérer les albums existants (avec leur token et nom d'affichage)
        # EN: Retrieve existing albums (with their token and display name)
        albums = db.get_all_albums() if db and hasattr(db, "get_all_albums") else []
        for alb in sorted(albums, key=lambda x: str(x.get("name", "")).lower()):
            aname = str(alb.get("name") or "Sans titre")
            atoken = str(alb.get("token") or aname)
            act_alb = menu.addAction(aname)
            if main_win and hasattr(main_win, "action_add_photos_to_album"):
                act_alb.triggered.connect(
                    lambda checked=False, tok=atoken: main_win.action_add_photos_to_album(photo_paths, tok)
                )

    @staticmethod
    def _populate_move_to_person_menu(
        menu: QMenu,
        photo_path: str,
        face_rect: Any,
        current_contact_id: str,
        db: Optional[PicasaDatabase],
        main_win: Optional[Any]
    ) -> None:
        """
        FR: Remplit le sous-menu "Move to People Album" avec les personnes existantes.
        EN: Populates the "Move to People Album" submenu with existing people contacts.
        Ref: picasa3.exe @ PplAlbumPhoto::ID_PEOPLEALBUMS (0x00CAF244)
        """
        if not db or not getattr(db, "face_manager", None):
            return
        people = db.face_manager.get_people()
        added = 0
        for p in sorted(people, key=lambda x: str(getattr(x, "name", "") or "").lower()):
            cid = str(getattr(p, "contact_id", "") or "")
            pname = str(getattr(p, "name", "") or "")
            if cid.lower() == current_contact_id.lower():
                continue
            act = menu.addAction(pname)
            if main_win and hasattr(main_win, "action_move_face_to_person"):
                act.triggered.connect(
                    lambda checked=False, target_cid=cid, target_cname=pname: main_win.action_move_face_to_person(
                        photo_path, face_rect, target_cid, target_cname, source_contact_id=current_contact_id
                    )
                )
            added += 1
        if added == 0:
            act_none = menu.addAction(_tr("(No other people)", "(Aucune autre personne)"))
            act_none.setEnabled(False)

