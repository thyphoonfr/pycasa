"""
Picasa Folder Manager Dialog (CFolderMgrDialog / foldermgr).

Reproduit fidèlement la boîte de dialogue de gestion des dossiers de Picasa 3 :
- Arborescence des dossiers du système (foldermgr/foldertree)
- Options de surveillance par dossier (Toujours analyser / Analyser une fois / Supprimer)
- Détection des visages par dossier (foldermgr/frexclude)
- Liste des dossiers actuellement surveillés (foldermgr/watched_folders)
- Avertissement pour les disques entiers
- Enregistrement dans repository.dat

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


RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "resources"


def _load_foldermgr_strings() -> Dict[str, str]:
    """Charge les libellés officiels de Picasa depuis FOLDERMGR_TEXT_FR.XML (ou EN)."""
    strings = {
        "folder_list": "Liste de dossiers",
        "instructions": (
            "Vous pouvez définir les dossiers que Picasa doit explorer pour rechercher des images. "
            "Vous pouvez également sélectionner des dossiers pour découvrir de nouvelles images."
        ),
        "status_label": "Pour le dossier actuel :",
        "scan_always": "Toujours analyser",
        "scan_once": "Analyser une seule fois",
        "remove": "Supprimer de Picasa",
        "watched_label": "Dossiers surveillés",
        "face_detection": "Détection des visages activée",
        "ok": "OK",
        "cancel": "Annuler",
        "help": "Aide",
        "title": "Gestionnaire de dossiers",
        "drive_warning": (
            "Watching an entire drive can slow down the system. It would be better to "
            "select several sub-folders. Are you sure you want to do this?"
        ),
    }

    # Tentative de lecture du fichier XML français ou anglais
    for xml_name in ["FOLDERMGR_TEXT_FR.XML", "FOLDERMGR_TEXT.XML"]:
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
    Boîte de dialogue Folder Manager de Picasa 3.
    Ref: picasa3.exe @ 0x008B7F90
    """
    folders_updated = Signal(list)  # Émet la liste des dossiers modifiés

    def __init__(self, db: PicasaDatabase, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.strings = _load_foldermgr_strings()

        # Copie locale de l'état actuel des dossiers pour permettre Annuler
        # Format : {norm_path: "0" | "1" | "2"}
        self.folder_settings: Dict[str, str] = {}
        for p, st in self.db.get_watched_folders().items():
            norm = os.path.abspath(p)
            self.folder_settings[norm] = st

        self.current_selected_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(self.strings["title"])
        self.resize(760, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #EBEBEB;
                color: #222222;
                font-family: 'Segoe UI', Tahoma, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #F8F8F8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #333333;
            }
            QTreeView {
                background-color: #FFFFFF;
                color: #111111;
                border: 1px solid #B0B0B0;
                selection-background-color: #3399FF;
                selection-color: #FFFFFF;
                font-size: 12px;
            }
            QTreeView::item {
                color: #111111;
                height: 22px;
            }
            QTreeView::item:selected {
                background-color: #3399FF;
                color: #FFFFFF;
            }
            QListWidget {
                background-color: #FFFFFF;
                color: #111111;
                border: 1px solid #B0B0B0;
                selection-background-color: #3399FF;
                selection-color: #FFFFFF;
                font-size: 11px;
            }
            QListWidget::item {
                color: #111111;
                padding: 4px 6px;
            }
            QListWidget::item:selected {
                background-color: #3399FF;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F5F5F5, stop:1 #E0E0E0);
                border: 1px solid #707070;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 75px;
                min-height: 22px;
                color: #111111;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #EAEAEA);
                border-color: #3C7FB1;
            }
            QPushButton:pressed {
                background-color: #D5D5D5;
            }
            QRadioButton {
                spacing: 8px;
                font-weight: normal;
                color: #222222;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Splitter horizontal (Gauche: Arborescence, Droite: Actions & Dossiers surveillés)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # --- Panneau Gauche : Arborescence des dossiers ---
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        left_label = QLabel(self.strings["folder_list"], left_widget)
        left_label.setStyleSheet("font-weight: bold; color: #333333;")
        left_layout.addWidget(left_label)

        self.fs_model = QFileSystemModel(self)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)
        self.fs_model.setRootPath("")

        self.tree_view = QTreeView(left_widget)
        self.tree_view.setModel(self.fs_model)
        # N'afficher que la colonne du nom de dossier avec étirement complet
        for col in range(1, 4):
            self.tree_view.hideColumn(col)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.clicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self.tree_view)

        splitter.addWidget(left_widget)

        # --- Panneau Droit : Explications, Paramètres du dossier, Liste surveillée ---
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Instructions du haut
        instr_label = QLabel(self.strings["instructions"], right_widget)
        instr_label.setWordWrap(True)
        instr_label.setStyleSheet("color: #444444; font-size: 11px;")
        right_layout.addWidget(instr_label)

        # Groupe : Pour le dossier actuel
        self.status_group = QGroupBox(self.strings["status_label"], right_widget)
        group_layout = QVBoxLayout(self.status_group)
        group_layout.setSpacing(8)

        self.current_folder_label = QLabel("Aucun dossier sélectionné", self.status_group)
        self.current_folder_label.setStyleSheet("font-style: italic; color: #555555;")
        self.current_folder_label.setWordWrap(True)
        group_layout.addWidget(self.current_folder_label)

        self.btn_group = QButtonGroup(self.status_group)

        # Radio 1 : Toujours analyser
        self.radio_watch = QRadioButton(f"● {self.strings['scan_always']}", self.status_group)
        self.radio_watch.setStyleSheet("QRadioButton { color: #0066CC; font-weight: bold; }")
        self.btn_group.addButton(self.radio_watch, 1)
        group_layout.addWidget(self.radio_watch)

        # Radio 2 : Analyser une seule fois
        self.radio_scan_once = QRadioButton(f"▶ {self.strings['scan_once']}", self.status_group)
        self.radio_scan_once.setStyleSheet("QRadioButton { color: #008800; }")
        self.btn_group.addButton(self.radio_scan_once, 2)
        group_layout.addWidget(self.radio_scan_once)

        # Radio 3 : Supprimer de Picasa
        self.radio_remove = QRadioButton(f"✕ {self.strings['remove']}", self.status_group)
        self.radio_remove.setStyleSheet("QRadioButton { color: #AA0000; }")
        self.btn_group.addButton(self.radio_remove, 0)
        group_layout.addWidget(self.radio_remove)

        # Checkbox Détection des visages
        self.chk_face_detect = QCheckBox(self.strings["face_detection"], self.status_group)
        self.chk_face_detect.setChecked(True)
        group_layout.addWidget(self.chk_face_detect)

        self.btn_group.idClicked.connect(self._on_status_radio_changed)

        right_layout.addWidget(self.status_group)

        # Groupe : Dossiers surveillés (Watched Folders)
        watched_group = QGroupBox(self.strings["watched_label"], right_widget)
        watched_layout = QVBoxLayout(watched_group)
        watched_layout.setContentsMargins(6, 6, 6, 6)

        self.watched_list = QListWidget(watched_group)
        self.watched_list.itemClicked.connect(self._on_watched_list_item_clicked)
        watched_layout.addWidget(self.watched_list)

        right_layout.addWidget(watched_group)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter, 1)

        # --- Boutons du bas (Aide, OK, Annuler) ---
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

        # Initialisation de la liste des dossiers surveillés
        self._refresh_watched_list()
        self._update_radio_states()
        self._auto_expand_initial_paths()

    def _auto_expand_initial_paths(self) -> None:
        """Déplie automatiquement les dossiers pertinents (Images, Documents, dossiers surveillés)."""
        from PySide6.QtCore import QTimer

        def _do_expand():
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
        """Met à jour la liste des dossiers surveillés affichés à droite."""
        self.watched_list.clear()
        for folder_path, status in sorted(self.folder_settings.items()):
            if status == "1":
                self.watched_list.addItem(f"● [Toujours] {folder_path}")
            elif status == "2":
                self.watched_list.addItem(f"▶ [1 fois] {folder_path}")

    def _on_tree_item_clicked(self, index: QModelIndex) -> None:
        path = self.fs_model.filePath(index)
        if not path:
            return
        norm_path = os.path.abspath(path)
        self.current_selected_path = norm_path
        self.current_folder_label.setText(norm_path)
        self._update_radio_states()

    def _update_radio_states(self) -> None:
        """Met à jour l'état des boutons radio selon le dossier actuellement sélectionné."""
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

        status = self.folder_settings.get(self.current_selected_path, None)

        self.btn_group.setExclusive(False)
        self.radio_watch.setChecked(status == "1")
        self.radio_scan_once.setChecked(status == "2")
        self.radio_remove.setChecked(status == "0")
        self.btn_group.setExclusive(True)

    def _on_status_radio_changed(self, button_id: int) -> None:
        if not self.current_selected_path:
            return

        # Avertissement si l'utilisateur choisit d'analyser un disque entier (ex: C:\)
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
        item = self.watched_list.currentItem()
        if not item:
            return
        text = item.text()
        # Extraction du chemin après le préfixe
        if "] " in text:
            path = text.split("] ", 1)[1]
            idx = self.fs_model.index(path)
            if idx.isValid():
                self.tree_view.setCurrentIndex(idx)
                self.tree_view.scrollTo(idx)
                self._on_tree_item_clicked(idx)

    def _on_help_clicked(self) -> None:
        QMessageBox.information(
            self,
            "Picasa",
            "Pour surveiller vos photos :\n"
            "- Choisissez un dossier dans l'arborescence\n"
            "- Sélectionnez 'Toujours analyser' pour surveiller automatiquement les nouveaux clichés\n"
            "- Cliquez sur OK pour valider."
        )

    def _on_ok_clicked(self) -> None:
        """Enregistre les modifications dans la base Picasa et ferme le dialogue."""
        changed_folders: List[str] = []
        newly_watched: List[str] = []

        for path, status in self.folder_settings.items():
            self.db.set_watched_folder(path, status)
            changed_folders.append(path)
            if status in ("1", "2"):
                newly_watched.append(path)

        # Sauvegarde atomique du fichier repository.dat
        try:
            self.db.save_database()
        except Exception:
            pass

        self.folders_updated.emit(newly_watched)
        self.accept()
