"""
FR: Boîte de dialogue du Gestionnaire de dossiers de Picasa 3 (CFolderMgrDialog / foldermgr).
Reproduit fidèlement la boîte de dialogue de gestion des dossiers de Picasa 3 :
- Arborescence des dossiers du système (foldermgr/foldertree)
- Options de surveillance par dossier (Toujours analyser / Analyser une fois / Supprimer)
- Détection des visages par dossier (foldermgr/frexclude)
- Liste des dossiers actuellement surveillés (foldermgr/watched_folders)
- Avertissement pour les disques entiers
- Enregistrement dans repository.dat

EN: Picasa Folder Manager Dialog (CFolderMgrDialog / foldermgr).
Faithfully reproduces Picasa 3's Folder Manager dialog:
- System folder tree view (foldermgr/foldertree)
- Per-folder watch options (Scan Always / Scan Once / Remove from Picasa)
- Per-folder face detection toggle (foldermgr/frexclude)
- Currently watched folders list (foldermgr/watched_folders)
- Whole-drive watching warning
- Persistence into repository.dat

Ref: picasa3.exe @ 0x008B7F90 (foldermgr, CFolderMgrDialog)
Ref: picasa3.exe @ 0x00704F20 (debounce 500 ms)
Ref: ui/resources/xml/FOLDERMGR_TEXT_FR.XML / FOLDERMGR_TEXT.XML
"""

from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set

from PySide6.QtCore import Qt, Signal, QModelIndex, QDir
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QFileSystemModel, QRadioButton, QButtonGroup,
    QCheckBox, QListWidget, QGroupBox, QSplitter, QMessageBox,
    QWidget, QHeaderView
)
from PySide6.QtGui import QFont, QColor, QStandardItemModel, QStandardItem

from picasa_py.db.database import PicasaDatabase
from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "resources"


def _load_foldermgr_strings() -> Dict[str, str]:
    """
    FR: Charge les libellés officiels de Picasa depuis FOLDERMGR_TEXT_*.XML selon la langue active.
    EN: Loads official Picasa labels from FOLDERMGR_TEXT_*.XML according to the active language.
    """
    res = PicasaResourceManager.get()
    strings = {
        "folder_list": res.get_xml_string("foldermgr/folder_list_label", "Liste de dossiers"),
        "instructions": res.get_xml_string(
            "foldermgr/instructions_text",
            "Vous pouvez définir les dossiers que Picasa doit explorer pour rechercher des images. "
            "Vous pouvez également sélectionner des dossiers pour découvrir de nouvelles images."
        ),
        "status_label": res.get_xml_string("foldermgr/status_label", "Pour le dossier actuel :"),
        "scan_always": res.get_xml_string("foldermgr/watch_label", "Toujours analyser"),
        "scan_once": res.get_xml_string("foldermgr/scan_once_label", "Analyser une seule fois"),
        "remove": res.get_xml_string("foldermgr/remove_label", "Supprimer de Picasa"),
        "watched_label": res.get_xml_string("foldermgr/watched_label", "Dossiers surveillés"),
        "face_detection": res.get_xml_string("foldermgr/frexclude", "Détection des visages activée"),
        "ok": res.get_xml_string("foldermgr/ok-label", "OK"),
        "cancel": res.get_xml_string("foldermgr/cancel-label", "Annuler"),
        "help": res.get_xml_string("foldermgr/help-label", "Aide"),
        "title": res.get_stringres("CFolderMgrDialog::title", "Gestionnaire de dossiers"),
        "drive_warning": (
            "Watching an entire drive can slow down the system. It would be better to "
            "select several sub-folders. Are you sure you want to do this?"
        ),
    }

    lang = (res.get_current_language() or "fr").upper()
    candidates = [f"FOLDERMGR_TEXT_{lang}.XML", "FOLDERMGR_TEXT_FR.XML", "FOLDERMGR_TEXT.XML"]
    for xml_name in candidates:
        xml_path = RESOURCES_DIR / "xml" / xml_name
        if xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for action in root.findall("action"):
                    target = action.get("target", "")
                    text_elem = action.find("xmbtext")
                    if text_elem is not None and text_elem.text:
                        val = text_elem.text.strip()
                        if target == "foldermgr/folder_list_label":
                            strings["folder_list"] = val
                        elif target == "foldermgr/instructions_text":
                            strings["instructions"] = val
                        elif target == "foldermgr/status_label":
                            strings["status_label"] = val
                        elif target == "foldermgr/watch_label":
                            strings["scan_always"] = val
                        elif target == "foldermgr/scan_once_label":
                            strings["scan_once"] = val
                        elif target == "foldermgr/remove_label":
                            strings["remove"] = val
                        elif target == "foldermgr/watched_label":
                            strings["watched_label"] = val
                        elif target == "foldermgr/ok-label":
                            strings["ok"] = val
                        elif target == "foldermgr/cancel-label":
                            strings["cancel"] = val
                        elif target == "foldermgr/help-label":
                            strings["help"] = val
                break
            except Exception:
                pass

    return strings


class PicasaFolderManagerDialog(QDialog):
    """
    FR: Boîte de dialogue Gestionnaire de dossiers (Folder Manager) de Picasa 3.
    EN: Picasa 3 Folder Manager dialog.
    Ref: picasa3.exe @ 0x008B7F90
    """
    folders_updated = Signal(list)  # FR: Émet la liste des dossiers modifiés / EN: Emits the list of updated folders

    def __init__(self, db: PicasaDatabase, parent: Optional[QWidget] = None, style: Optional[PicasaStyle] = None):
        """
        FR: Initialise le dialogue Gestionnaire de dossiers avec l'état actuel de la base de données.
        EN: Initializes the Folder Manager dialog with the current database watched folders state.
        """
        super().__init__(parent)
        self.db = db
        self.style = style or PicasaStyle.instance()
        self.strings = _load_foldermgr_strings()

        # FR: Copie locale de l'état actuel des dossiers pour permettre Annuler
        # EN: Local copy of current folder states to support Cancel
        # Format : {norm_path: "0" | "1" | "2"}
        self.folder_settings: Dict[str, str] = {}
        for p, st in self.db.get_watched_folders().items():
            norm = os.path.abspath(p)
            self.folder_settings[norm] = st

        self.current_selected_path: Optional[str] = None
        self._init_ui()
        self.apply_style(self.style)

    def _init_ui(self) -> None:
        """
        FR: Construit la disposition graphique complète (arborescence, options radio, liste surveillée et boutons).
        EN: Builds the complete dialog UI layout (folder tree, radio options, watched list, and buttons).
        """
        self.setWindowTitle(self.strings["title"])
        self.resize(760, 560)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # --- FR: Panneau Gauche : Arborescence des dossiers / EN: Left Panel: Folder Tree ---
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.left_label = QLabel(self.strings["folder_list"], left_widget)
        left_layout.addWidget(self.left_label)

        self.fs_model = QFileSystemModel(self)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)
        self.fs_model.setRootPath("")

        self.tree_view = QTreeView(left_widget)
        self.tree_view.setModel(self.fs_model)
        for col in range(1, 4):
            self.tree_view.hideColumn(col)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.clicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self.tree_view)

        splitter.addWidget(left_widget)

        # --- FR: Panneau Droit : Explications, Paramètres du dossier, Liste surveillée / EN: Right Panel ---
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.instr_label = QLabel(self.strings["instructions"], right_widget)
        self.instr_label.setWordWrap(True)
        right_layout.addWidget(self.instr_label)

        self.status_group = QGroupBox(self.strings["status_label"], right_widget)
        group_layout = QVBoxLayout(self.status_group)
        group_layout.setSpacing(8)

        self.current_folder_label = QLabel("Aucun dossier sélectionné", self.status_group)
        self.current_folder_label.setWordWrap(True)
        group_layout.addWidget(self.current_folder_label)

        self.btn_group = QButtonGroup(self.status_group)

        # FR: Radio 1 : Toujours analyser / EN: Radio 1: Scan Always
        self.radio_watch = QRadioButton(f"● {self.strings['scan_always']}", self.status_group)
        self.btn_group.addButton(self.radio_watch, 1)
        group_layout.addWidget(self.radio_watch)

        # FR: Radio 2 : Analyser une seule fois / EN: Radio 2: Scan Once
        self.radio_scan_once = QRadioButton(f"▶ {self.strings['scan_once']}", self.status_group)
        self.btn_group.addButton(self.radio_scan_once, 2)
        group_layout.addWidget(self.radio_scan_once)

        # FR: Radio 3 : Supprimer de Picasa / EN: Radio 3: Remove from Picasa
        self.radio_remove = QRadioButton(f"✕ {self.strings['remove']}", self.status_group)
        self.btn_group.addButton(self.radio_remove, 0)
        group_layout.addWidget(self.radio_remove)

        # FR: Checkbox Détection des visages / EN: Face Detection checkbox (Ref: foldermgr/frexclude, [Picasa] frexclude=1)
        self.face_detect_settings: Dict[str, bool] = {}
        self.chk_face_detect = QCheckBox(self.strings["face_detection"], self.status_group)
        self.chk_face_detect.setChecked(True)
        self.chk_face_detect.toggled.connect(self._on_face_detect_toggled)
        group_layout.addWidget(self.chk_face_detect)

        self.btn_group.idClicked.connect(self._on_status_radio_changed)

        right_layout.addWidget(self.status_group)

        # FR: Groupe : Dossiers surveillés / EN: Group: Watched Folders
        self.watched_group = QGroupBox(self.strings["watched_label"], right_widget)
        watched_layout = QVBoxLayout(self.watched_group)
        watched_layout.setContentsMargins(6, 6, 6, 6)

        self.watched_list = QListWidget(self.watched_group)
        self.watched_list.itemClicked.connect(self._on_watched_list_item_clicked)
        watched_layout.addWidget(self.watched_list)

        right_layout.addWidget(self.watched_group)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter, 1)

        # --- FR: Boutons du bas (Aide, OK, Annuler) / EN: Bottom buttons (Help, OK, Cancel) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.btn_help = QPushButton(self.strings["help"], self)
        self.btn_help.clicked.connect(self._on_help_clicked)
        bottom_layout.addWidget(self.btn_help)

        bottom_layout.addStretch(1)

        self.btn_ok = QPushButton(self.strings["ok"], self)
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        bottom_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(self.strings["cancel"], self)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(bottom_layout)

        self._refresh_watched_list()
        self._update_radio_states()
        self._auto_expand_initial_paths()

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème PicasaStyle au gestionnaire de dossiers.
        EN: Dynamically applies the PicasaStyle theme to the Folder Manager dialog.
        """
        self.style = style or PicasaStyle.instance()
        s = self.style
        dlg_bg = s.window_bgcolor.name() if s.is_dark else "#EBEBEB"
        grp_bg = s.alist_bgcolor.name() if s.is_dark else "#F8F8F8"
        txt_col = s.alist_textcolor.name() if s.is_dark else "#222222"
        border_col = s.splitter_color.name() if s.is_dark else "#CCCCCC"
        view_bg = s.thumb_card_bgcolor.name() if s.is_dark else "#FFFFFF"
        btn_start = s.topbar_btn_bg_start.name() if s.is_dark else "#F5F5F5"
        btn_end = s.topbar_btn_bg_end.name() if s.is_dark else "#E0E0E0"
        accent = s.accent_color.name()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {txt_col};
                font-family: 'Segoe UI', Tahoma, sans-serif;
                font-size: 12px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {border_col};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {grp_bg};
                color: {txt_col};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {txt_col};
            }}
            QLabel, QCheckBox {{
                color: {txt_col};
            }}
            QTreeView {{
                background-color: {view_bg};
                color: {txt_col};
                border: 1px solid {border_col};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                font-size: 12px;
            }}
            QTreeView::item {{
                color: {txt_col};
                height: 22px;
            }}
            QTreeView::item:selected {{
                background-color: {accent};
                color: #FFFFFF;
            }}
            QListWidget {{
                background-color: {view_bg};
                color: {txt_col};
                border: 1px solid {border_col};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                font-size: 11px;
            }}
            QListWidget::item {{
                color: {txt_col};
                padding: 4px 6px;
            }}
            QListWidget::item:selected {{
                background-color: {accent};
                color: #FFFFFF;
            }}
            QPushButton {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {btn_start}, stop:1 {btn_end});
                border: 1px solid {border_col};
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 75px;
                min-height: 22px;
                color: {txt_col};
            }}
            QPushButton:hover {{
                border-color: {accent};
            }}
            QRadioButton {{
                spacing: 8px;
                font-weight: normal;
                color: {txt_col};
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
            }}
        """)
        if hasattr(self, "left_label"):
            self.left_label.setStyleSheet(f"font-weight: bold; color: {txt_col};")
        if hasattr(self, "instr_label"):
            self.instr_label.setStyleSheet(f"color: {txt_col}; font-size: 11px;")
        if hasattr(self, "current_folder_label"):
            self.current_folder_label.setStyleSheet(f"font-style: italic; color: {txt_col}; font-weight: bold;")
        if hasattr(self, "radio_watch"):
            w_col = "#4DA3FF" if s.is_dark else "#0066CC"
            self.radio_watch.setStyleSheet(f"QRadioButton {{ color: {w_col}; font-weight: bold; }}")
        if hasattr(self, "radio_scan_once"):
            o_col = "#4CD964" if s.is_dark else "#008800"
            self.radio_scan_once.setStyleSheet(f"QRadioButton {{ color: {o_col}; }}")
        if hasattr(self, "radio_remove"):
            r_col = "#FF6B6B" if s.is_dark else "#AA0000"
            self.radio_remove.setStyleSheet(f"QRadioButton {{ color: {r_col}; }}")

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les libellés du gestionnaire de dossiers selon la langue active.
        EN: Updates the Folder Manager labels according to the active language.
        """
        self.strings = _load_foldermgr_strings()
        self.setWindowTitle(self.strings["title"])
        self.left_label.setText(self.strings["folder_list"])
        self.instr_label.setText(self.strings["instructions"])
        self.status_group.setTitle(self.strings["status_label"])
        self.radio_watch.setText(f"● {self.strings['scan_always']}")
        self.radio_scan_once.setText(f"▶ {self.strings['scan_once']}")
        self.radio_remove.setText(f"✕ {self.strings['remove']}")
        self.chk_face_detect.setText(self.strings["face_detection"])
        self.watched_group.setTitle(self.strings["watched_label"])
        self.btn_help.setText(self.strings["help"])
        self.btn_ok.setText(self.strings["ok"])
        self.btn_cancel.setText(self.strings["cancel"])

    def _auto_expand_initial_paths(self) -> None:
        """
        FR: Déplie automatiquement les dossiers pertinents (Images, Documents, dossiers surveillés).
        EN: Automatically expands relevant initial folders (Pictures, Documents, watched folders).
        """
        from PySide6.QtCore import QTimer

        def _do_expand():
            """
            FR: Exécute le dépliement différé des chemins cibles dans le QTreeView.
            EN: Performs the deferred expansion of target paths in the QTreeView.
            """
            targets = []
            for p in list(self.folder_settings.keys()):
                if os.path.exists(p):
                    targets.append(p)
            user_pic = os.path.expanduser("~/Pictures")
            if os.path.exists(user_pic):
                targets.append(user_pic)
            user_doc = os.path.expanduser("~/Documents")
            if os.path.exists(user_doc):
                targets.append(user_doc)

            for target in targets:
                idx = self.fs_model.index(target)
                if idx.isValid():
                    p_idx = idx
                    while p_idx.isValid():
                        self.tree_view.expand(p_idx)
                        p_idx = p_idx.parent()

            if targets:
                first_idx = self.fs_model.index(targets[0])
                if first_idx.isValid():
                    self.tree_view.setCurrentIndex(first_idx)
                    self.tree_view.scrollTo(first_idx)
                    self._on_tree_item_clicked(first_idx)

        QTimer.singleShot(200, _do_expand)

    def _refresh_watched_list(self) -> None:
        """
        FR: Met à jour la liste des dossiers surveillés affichés à droite.
        EN: Refreshes the list of watched folders displayed in the right panel.
        """
        self.watched_list.clear()
        for folder_path, status in sorted(self.folder_settings.items()):
            if status == "1":
                self.watched_list.addItem(f"● [Toujours] {folder_path}")
            elif status == "2":
                self.watched_list.addItem(f"▶ [1 fois] {folder_path}")

    def _on_tree_item_clicked(self, index: QModelIndex) -> None:
        """
        FR: Sélectionne le dossier cliqué dans l'arborescence et met à jour les contrôles d'état.
        EN: Selects the clicked folder in the tree view and updates the status controls.
        """
        path = self.fs_model.filePath(index)
        if not path:
            return
        norm_path = os.path.abspath(path)
        self.current_selected_path = norm_path
        self.current_folder_label.setText(norm_path)
        self._update_radio_states()

    def _get_folder_face_detect_enabled(self, folder_path: str) -> bool:
        """
        FR: Vérifie si la détection des visages est activée pour ce dossier (absence de frexclude=1 dans .picasa.ini).
        EN: Checks whether face detection is enabled for this folder (absence of frexclude=1 in .picasa.ini).
        """
        if folder_path in self.face_detect_settings:
            return self.face_detect_settings[folder_path]
        ini_p = os.path.join(folder_path, ".picasa.ini")
        if os.path.exists(ini_p):
            try:
                from picasa_py.ini.parser import PicasaIniParser
                doc = PicasaIniParser.parse_file(ini_p)
                sec = doc.get_section("Picasa")
                if sec and sec.get("frexclude") in ("1", "yes", "true"):
                    return False
            except Exception:
                pass
        return True

    def _on_face_detect_toggled(self, checked: bool) -> None:
        """
        FR: Mémorise le changement de l'option de détection des visages pour le dossier sélectionné.
        EN: Records the face detection checkbox state change for the currently selected folder.
        """
        if self.current_selected_path:
            self.face_detect_settings[self.current_selected_path] = checked

    def _update_radio_states(self) -> None:
        """
        FR: Met à jour l'état des boutons radio selon le dossier actuellement sélectionné.
        EN: Updates the radio button states according to the currently selected folder.
        """
        if not self.current_selected_path:
            self.radio_watch.setEnabled(False)
            self.radio_scan_once.setEnabled(False)
            self.radio_remove.setEnabled(False)
            self.chk_face_detect.setEnabled(False)
            self.btn_group.setExclusive(False)
            self.radio_watch.setChecked(False)
            self.radio_scan_once.setChecked(False)
            self.radio_remove.setChecked(False)
            self.btn_group.setExclusive(True)
            return

        self.radio_watch.setEnabled(True)
        self.radio_scan_once.setEnabled(True)
        self.radio_remove.setEnabled(True)
        self.chk_face_detect.setEnabled(True)

        self.chk_face_detect.blockSignals(True)
        self.chk_face_detect.setChecked(self._get_folder_face_detect_enabled(self.current_selected_path))
        self.chk_face_detect.blockSignals(False)

        status = self.folder_settings.get(self.current_selected_path, None)

        self.btn_group.setExclusive(False)
        self.radio_watch.setChecked(status == "1")
        self.radio_scan_once.setChecked(status == "2")
        self.radio_remove.setChecked(status == "0")
        self.btn_group.setExclusive(True)

    def _on_status_radio_changed(self, button_id: int) -> None:
        """
        FR: Met à jour le mode de surveillance du dossier sélectionné lorsque l'utilisateur change de bouton radio.
        EN: Updates the watch mode of the selected folder when the user clicks a status radio button.
        """
        if not self.current_selected_path:
            return

        # FR: Avertissement si l'utilisateur choisit d'analyser un disque entier (ex: C:\)
        # EN: Warning if the user chooses to watch an entire drive root (e.g., C:\)
        # Ref: picasa3.exe @ 0x008B7FC4
        is_drive_root = (
            len(self.current_selected_path) <= 3 and
            self.current_selected_path[1:2] == ":"
        )
        if is_drive_root and button_id in (1, 2):
            resp = QMessageBox.warning(
                self,
                "Picasa",
                self.strings["drive_warning"],
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                self._update_radio_states()
                return

        status_str = str(button_id)
        self.folder_settings[self.current_selected_path] = status_str
        self._refresh_watched_list()

    def _on_watched_list_item_clicked(self) -> None:
        """
        FR: Navigue vers le dossier correspondant dans l'arborescence lors d'un clic dans la liste surveillée.
        EN: Navigates to the corresponding folder in the tree view when clicked in the watched list.
        """
        item = self.watched_list.currentItem()
        if not item:
            return
        text = item.text()
        # FR: Extraction du chemin après le préfixe / EN: Extract folder path after status prefix
        if "] " in text:
            path = text.split("] ", 1)[1]
            idx = self.fs_model.index(path)
            if idx.isValid():
                self.tree_view.setCurrentIndex(idx)
                self.tree_view.scrollTo(idx)
                self._on_tree_item_clicked(idx)

    def _on_help_clicked(self) -> None:
        """
        FR: Affiche la boîte de dialogue d'aide du Gestionnaire de dossiers.
        EN: Displays the Folder Manager help message box.
        """
        QMessageBox.information(
            self,
            "Picasa",
            "Pour surveiller vos photos :\n"
            "- Choisissez un dossier dans l'arborescence\n"
            "- Sélectionnez 'Toujours analyser' pour surveiller automatiquement les nouveaux clichés\n"
            "- Cliquez sur OK pour valider."
        )

    def _on_ok_clicked(self) -> None:
        """
        FR: Enregistre les modifications dans la base Picasa et ferme le dialogue.
        EN: Saves folder watch settings to the Picasa database and closes the dialog.
        """
        changed_folders: List[str] = []
        newly_watched: List[str] = []

        for path, status in self.folder_settings.items():
            self.db.set_watched_folder(path, status)
            changed_folders.append(path)
            if status in ("1", "2"):
                newly_watched.append(path)

        # FR: Persister l'option de détection des visages (frexclude=1 dans [Picasa] de .picasa.ini)
        # EN: Persist the face detection option (frexclude=1 in [Picasa] section of .picasa.ini)
        from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
        for folder_path, enabled in self.face_detect_settings.items():
            if not os.path.isdir(folder_path):
                continue
            ini_p = os.path.join(folder_path, ".picasa.ini")
            try:
                doc = PicasaIniParser.parse_file(ini_p) if os.path.exists(ini_p) else PicasaIniDocument()
                sec = doc.get_or_create_section("Picasa")
                if not enabled:
                    sec.set("frexclude", "1")
                else:
                    sec.remove("frexclude")
                doc.write_file(ini_p)
            except Exception:
                pass

        # FR: Sauvegarde atomique du fichier repository.dat / EN: Atomic save of repository.dat
        try:
            self.db.save_database()
        except Exception:
            pass

        self.folders_updated.emit(newly_watched)
        self.accept()

