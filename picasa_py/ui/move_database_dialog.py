"""
FR : Boîtes de dialogue de déplacement et de sélection de base de données pour PyCasa (move_database.fen).
Permet de déplacer, créer ou ouvrir un répertoire de base de données locale Picasa 3.
EN : Move & Select Database Dialogs for PyCasa (CMoveDatabaseDialog / move_database.fen).
Allows moving, creating, or opening a Picasa 3 local database directory.

Ref: picasa3.exe @ move_database.fen, compacting.fen
Ref: ui/resources/xml/MOVE_DATABASE_FR.XML / MOVE_DATABASE.XML
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.database import PicasaDatabase


class PicasaMoveDatabaseDialog(QDialog):
    """
    FR : Dialogue de déplacement et de migration de la base de données Picasa.
    EN : Picasa database move and migration dialog.
    """

    def __init__(
        self,
        db: PicasaDatabase,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.db = db
        self.new_db_path: Optional[str] = None
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(
            self.res_mgr.get_xml_string("move_database/window1.title", "Déplacer la base de données")
        )
        self.setFixedWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Avertissements officiels de Picasa
        self.warn_lbl = QLabel(
            "<b>Vous devrez redémarrer Picasa pour que les modifications prennent effet.</b><br><br>"
            "<i>Remarque : Il est conseillé de sauvegarder votre base de données avant de tester cette fonctionnalité. "
            "Ne déplacez JAMAIS la base de données vers un lecteur réseau ou amovible afin d'éviter toute perte de données.</i>"
        )
        self.warn_lbl.setWordWrap(True)
        layout.addWidget(self.warn_lbl)

        # 2. Emplacement actuel
        self.lbl_curr = QLabel(
            self.res_mgr.get_xml_string(
                "move_database/labelgroup6.title",
                "Emplacement actuel de la base de données :",
            )
        )
        layout.addWidget(self.lbl_curr)
        curr_loc = str(self.db.db_dir) if (self.db and hasattr(self.db, "db_dir") and self.db.db_dir) else (str(self.db.db3_dir) if (self.db and hasattr(self.db, "db3_dir") and self.db.db3_dir) else "")
        self.edit_curr = QLineEdit(curr_loc)
        self.edit_curr.setReadOnly(True)
        self.edit_current = self.edit_curr
        layout.addWidget(self.edit_curr)

        # 3. Nouvel emplacement
        self.lbl_new = QLabel(
            self.res_mgr.get_xml_string(
                "move_database/labelgroup9.title",
                "Nouvel emplacement de la base de données :",
            )
        )
        layout.addWidget(self.lbl_new)
        new_box = QHBoxLayout()
        self.edit_new = QLineEdit()
        self.edit_new.setPlaceholderText("Sélectionnez le nouveau dossier cible...")
        self.edit_target = self.edit_new
        new_box.addWidget(self.edit_new, 1)

        self.btn_browse = QPushButton(
            self.res_mgr.get_xml_string("move_database/changeloc.title", "Parcourir...")
        )
        self.btn_browse.clicked.connect(self._browse_new_loc)
        new_box.addWidget(self.btn_browse)

        self.btn_default = QPushButton(
            self.res_mgr.get_xml_string("move_database/defaultloc.title", "Par défaut")
        )
        self.btn_default.clicked.connect(self._reset_default)
        new_box.addWidget(self.btn_default)

        layout.addLayout(new_box)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 4. Boutons d'action
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        self.btn_move = QPushButton(
            self.res_mgr.get_xml_string("move_database/move.title", "Déplacer au prochain redémarrage")
        )
        self.btn_move.setObjectName("PrimaryBtn")
        self.btn_move.clicked.connect(self._apply_move)
        btn_box.addWidget(self.btn_move)

        self.btn_cancel = QPushButton(
            self.res_mgr.get_xml_string("move_database/button16.title", "Annuler")
        )
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue.
        EN : Dynamically applies the active Picasa theme to the dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#111111"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        border = "#4B5263" if is_dark else "#7F9DB9"
        btn_bg = "#3A3F4B" if is_dark else "#F0F0F0"
        btn_hover = "#484E5C" if is_dark else "#E5E5E5"
        btn_border = "#555B69" if is_dark else "#707070"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
            QLineEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 4px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 12px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                min-width: 65px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: #3C7FB1;
                color: {fg};
            }}
            QPushButton#PrimaryBtn {{
                background-color: #2F6DB5;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #1E4E85;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: #3879D9;
                color: #FFFFFF;
            }}
        """)
        if hasattr(self, "sep"):
            self.sep.setStyleSheet(f"color: {border};")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes selon la langue active.
        EN : Updates texts according to the active language.
        """
        self.setWindowTitle(
            self.res_mgr.get_xml_string("move_database/window1.title", "Déplacer la base de données")
        )
        self.lbl_curr.setText(
            self.res_mgr.get_xml_string(
                "move_database/labelgroup6.title",
                "Emplacement actuel de la base de données :",
            )
        )
        self.lbl_new.setText(
            self.res_mgr.get_xml_string(
                "move_database/labelgroup9.title",
                "Nouvel emplacement de la base de données :",
            )
        )
        self.btn_browse.setText(self.res_mgr.get_xml_string("move_database/changeloc.title", "Parcourir..."))
        self.btn_default.setText(self.res_mgr.get_xml_string("move_database/defaultloc.title", "Par défaut"))
        self.btn_move.setText(
            self.res_mgr.get_xml_string("move_database/move.title", "Déplacer au prochain redémarrage")
        )
        self.btn_cancel.setText(self.res_mgr.get_xml_string("move_database/button16.title", "Annuler"))

    def _browse_new_loc(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choisir le nouvel emplacement de la base de données",
            str(Path.home())
        )
        if folder:
            self.edit_new.setText(folder)

    def _reset_default(self) -> None:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            default_p = os.path.join(local_appdata, "Google", "Picasa2", "db3")
            self.edit_new.setText(default_p)

    def _apply_move(self) -> None:
        target = self.edit_new.text().strip()
        if not target:
            QMessageBox.warning(self, "Erreur", "Veuillez spécifier un dossier de destination.")
            return

        if os.path.abspath(target).lower() == os.path.abspath(self.edit_curr.text()).lower():
            QMessageBox.information(self, "Information", "L'emplacement sélectionné est déjà l'emplacement actuel.")
            return

        res = QMessageBox.question(
            self,
            "Confirmer le déplacement",
            f"La base de données sera copiée vers :\n{target}\n\nVoulez-vous procéder à la copie maintenant ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            try:
                os.makedirs(target, exist_ok=True)
                src = self.edit_curr.text()
                if os.path.exists(src):
                    for item in os.listdir(src):
                        s = os.path.join(src, item)
                        d = os.path.join(target, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)
                from picasa_py.db.preferences import PicasaPreferences
                PicasaPreferences.set_repository_path(target)
                self.new_db_path = target
                QMessageBox.information(
                    self,
                    "Déplacement terminé",
                    "Les fichiers de la base de données ont été copiés avec succès et la nouvelle base est maintenant active."
                )
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Erreur de copie", f"Impossible de copier les fichiers : {e}")


class PicasaDatabaseSelectorDialog(QDialog):
    """
    FR : Boîte de dialogue dédiée pour « Créer une nouvelle base de données... » (mode="create")
    et « Ouvrir une base de données existante... » (mode="open"), dans l'esprit visuel de
    PicasaMoveDatabaseDialog (move_database.fen) et PicasaFolderManagerDialog (foldermgr).
    EN : Dedicated dialog for "Create a new database..." (mode="create") and "Open an existing
    database..." (mode="open"), matching the visual style of move_database.fen and foldermgr.

    Ref: picasa3.exe @ move_database.fen, foldermgr/foldertree (0x008B7F90)
    Ref: picasa3.exe @ 0x004156F0 (CThumbDB::Init), 0x006B6070 (CThumbDB::Open)
    """

    def __init__(
        self,
        mode: str = "open",
        current_db: Optional[PicasaDatabase] = None,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None,
    ):
        super().__init__(parent)
        from PySide6.QtWidgets import QTreeView, QFileSystemModel, QCheckBox, QGroupBox
        from PySide6.QtCore import QDir, QModelIndex

        self.mode = mode if mode in ("create", "open") else "open"
        self.current_db = current_db
        self.selected_path: Optional[str] = None
        self.persist_as_default: bool = True
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        is_create = self.mode == "create"
        self.setWindowTitle(
            "Créer une nouvelle base de données Picasa"
            if is_create
            else "Ouvrir une base de données Picasa existante"
        )
        self.resize(640, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. En-tête explicatif (style Picasa)
        if is_create:
            intro_text = (
                "<b>Créer une nouvelle base de données Picasa 3</b><br>"
                "Sélectionnez dans l'arborescence ci-dessous le répertoire dans lequel initialiser "
                "une nouvelle base de données vierge (les sous-dossiers <code>db3</code> et <code>contacts</code> "
                "ainsi que toutes les tables binaires <code>.pmp</code> et <code>thumbindex.db</code> y seront créés)."
            )
        else:
            intro_text = (
                "<b>Ouvrir une base de données Picasa 3 existante</b><br>"
                "Sélectionnez dans l'arborescence ci-dessous un dossier contenant une base Picasa "
                "(soit le dossier parent contenant <code>db3/</code> et <code>contacts/</code>, soit directement le dossier <code>db3/</code>)."
            )
        self.lbl_intro = QLabel(intro_text)
        self.lbl_intro.setWordWrap(True)
        layout.addWidget(self.lbl_intro)

        # 2. Emplacement actuel en lecture seule
        curr_row = QHBoxLayout()
        curr_row.addWidget(QLabel("Base actuelle :"))
        curr_loc = (
            str(self.current_db.db3_dir)
            if (self.current_db and getattr(self.current_db, "db3_dir", None))
            else "Aucune base active"
        )
        self.edit_curr = QLineEdit(curr_loc)
        self.edit_curr.setReadOnly(True)
        curr_row.addWidget(self.edit_curr, 1)
        layout.addLayout(curr_row)

        # 3. Arborescence des répertoires (comme dans le Gestionnaire de dossiers)
        self.grp_tree = QGroupBox("Sélectionner un répertoire sur le disque")
        tree_vbox = QVBoxLayout(self.grp_tree)
        tree_vbox.setContentsMargins(8, 8, 8, 8)
        tree_vbox.setSpacing(6)

        self.fs_model = QFileSystemModel(self)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives)
        self.fs_model.setRootPath("")

        self.tree_view = QTreeView(self.grp_tree)
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setHeaderHidden(True)
        for col in range(1, 4):
            self.tree_view.hideColumn(col)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(18)
        self.tree_view.selectionModel().currentChanged.connect(self._on_tree_selection_changed)
        tree_vbox.addWidget(self.tree_view, 1)

        # Barre de chemin + Parcourir + Nouveau dossier + Par défaut
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Dossier choisi :"))
        self.edit_target = QLineEdit()
        self.edit_target.setPlaceholderText("Chemin du dossier cible...")
        self.edit_target.textChanged.connect(self._on_path_text_changed)
        path_row.addWidget(self.edit_target, 1)

        self.btn_browse = QPushButton("Parcourir...")
        self.btn_browse.clicked.connect(self._browse_folder)
        path_row.addWidget(self.btn_browse)

        if is_create:
            self.btn_mkdir = QPushButton("Nouveau dossier...")
            self.btn_mkdir.clicked.connect(self._create_subfolder)
            path_row.addWidget(self.btn_mkdir)

        self.btn_default = QPushButton("Emplacement par défaut")
        self.btn_default.setToolTip("Sélectionner l'emplacement standard de Picasa 3 (%LOCALAPPDATA%\\Google\\Picasa2)")
        self.btn_default.clicked.connect(self._select_default_location)
        path_row.addWidget(self.btn_default)

        tree_vbox.addLayout(path_row)
        layout.addWidget(self.grp_tree, 1)

        # 4. Encadré de diagnostic en temps réel sur le dossier sélectionné
        self.lbl_status_box = QLabel("")
        self.lbl_status_box.setWordWrap(True)
        layout.addWidget(self.lbl_status_box)

        # 5. Case à cocher de persistance
        self.chk_default = QCheckBox("Mémoriser cette base de données par défaut au prochain démarrage de Picasa")
        self.chk_default.setChecked(True)
        layout.addWidget(self.chk_default)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 6. Boutons d'action
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_confirm = QPushButton(
            "Créer et activer la base" if is_create else "Ouvrir cette base de données"
        )
        self.btn_confirm.setObjectName("PrimaryBtn")
        self.btn_confirm.clicked.connect(self._on_confirm)
        btn_row.addWidget(self.btn_confirm)

        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        layout.addLayout(btn_row)

        self.apply_style(self.style)

        # Initialiser sur le parent de la base actuelle ou le dossier utilisateur
        initial_dir = (
            str(self.current_db.db3_dir.parent)
            if (self.current_db and getattr(self.current_db, "db3_dir", None))
            else str(Path.home())
        )
        self.set_target_directory(initial_dir)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au sélecteur de base de données.
        EN : Dynamically applies the active Picasa theme to the database selector dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#111111"
        grp_bg = "#2A2E37" if is_dark else "#F6F4EC"
        grp_title = "#7FB5FF" if is_dark else "#1B4F72"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        ro_bg = "#1A1D22" if is_dark else "#F4F2E8"
        ro_fg = "#9DA5B4" if is_dark else "#555555"
        border = "#4B5263" if is_dark else "#7F9DB9"
        grp_border = "#4B5263" if is_dark else "#B8B4A2"
        btn_bg = "#3A3F4B" if is_dark else "#F0F0F0"
        btn_hover = "#484E5C" if is_dark else "#E5F0FA"
        btn_border = "#555B69" if is_dark else "#707070"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QLabel {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {grp_border};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 10px;
                background-color: {grp_bg};
                color: {fg};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: {grp_title};
            }}
            QLineEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 4px 6px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QTreeView {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                selection-background-color: #3399FF;
                selection-color: #FFFFFF;
                font-size: 11px;
            }}
            QTreeView::item {{
                height: 22px;
                color: {fg};
            }}
            QTreeView::item:selected {{
                background-color: #3399FF;
                color: #FFFFFF;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 5px 12px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                min-width: 75px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: #3C7FB1;
            }}
            QPushButton#PrimaryBtn {{
                background-color: #2F6DB5;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #1E4E85;
                padding: 5px 16px;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: #3879D9;
                color: #FFFFFF;
            }}
            QCheckBox {{
                font-size: 11px;
                color: {fg};
            }}
        """)
        self.edit_curr.setStyleSheet(f"background-color: {ro_bg}; color: {ro_fg};")
        self.lbl_status_box.setStyleSheet(
            f"background-color: {inp_bg}; color: {fg}; border: 1px solid {grp_border}; border-radius: 3px; padding: 6px 8px;"
        )
        if hasattr(self, "sep"):
            self.sep.setStyleSheet(f"color: {border};")

    def set_target_directory(self, folder_path: str) -> None:
        if not folder_path:
            return
        norm = os.path.abspath(folder_path)
        self.edit_target.setText(norm)
        idx = self.fs_model.index(norm)
        if idx.isValid():
            self.tree_view.setCurrentIndex(idx)
            self.tree_view.expand(idx)
            self.tree_view.scrollTo(idx)

    def _on_tree_selection_changed(self, current, _previous) -> None:
        if current.isValid():
            p = self.fs_model.filePath(current)
            if p:
                self.edit_target.setText(os.path.normpath(p))

    def _on_path_text_changed(self, text: str) -> None:
        clean = text.strip()
        if not clean:
            self.lbl_status_box.setText("<span style='color:#666666;'>Aucun répertoire sélectionné.</span>")
            self.btn_confirm.setEnabled(False)
            return

        self.btn_confirm.setEnabled(True)
        try:
            for_create = self.mode == "create"
            p_db3, p_contacts = PicasaDatabase.resolve_database_dirs(clean, for_creation=for_create)
            has_thumbindex = (p_db3 / "thumbindex.db").exists()
            pmp_count = len(list(p_db3.glob("*.pmp"))) if p_db3.exists() else 0
            has_contacts = (p_contacts / "contacts.xml").exists() if p_contacts.exists() else False

            if self.mode == "create":
                if has_thumbindex or pmp_count > 0:
                    self.lbl_status_box.setText(
                        f"<span style='color:#9A6700;'><b>⚠️ Base existante détectée :</b></span> "
                        f"<code>{p_db3}</code> contient déjà <code>thumbindex.db</code> ({pmp_count} fichiers <code>.pmp</code>).<br>"
                        f"Une confirmation vous sera demandée avant de réinitialiser cette base."
                    )
                else:
                    self.lbl_status_box.setText(
                        f"<span style='color:#1E6F3D;'><b>✔ Emplacement prêt pour la création :</b></span><br>"
                        f"• Dossier DB : <code>{p_db3}</code><br>"
                        f"• Dossier Contacts : <code>{p_contacts}</code>"
                    )
            else:
                if has_thumbindex or pmp_count > 0:
                    contacts_txt = "contacts.xml présent" if has_contacts else "aucun fichier contacts.xml"
                    self.lbl_status_box.setText(
                        f"<span style='color:#1E6F3D;'><b>✔ Base de données Picasa 3 valide détectée :</b></span><br>"
                        f"• Dossier DB : <code>{p_db3}</code> ({pmp_count} tables <code>.pmp</code>, <code>thumbindex.db</code>)<br>"
                        f"• Contacts : <code>{p_contacts}</code> ({contacts_txt})"
                    )
                else:
                    self.lbl_status_box.setText(
                        f"<span style='color:#9A6700;'><b>ℹ️ Aucune base existante trouvée dans ce dossier :</b></span><br>"
                        f"<code>{p_db3}</code> ne contient pas encore de fichiers Picasa. "
                        f"Si vous continuez, Picasa vous proposera d'y initialiser une nouvelle base."
                    )
        except Exception as e:
            self.lbl_status_box.setText(f"<span style='color:#B02020;'>Chemin invalide : {e}</span>")

    def _browse_folder(self) -> None:
        start = self.edit_target.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Choisir un répertoire pour la base de données Picasa",
            start,
        )
        if chosen:
            self.set_target_directory(chosen)

    def _create_subfolder(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        base = self.edit_target.text().strip() or str(Path.home())
        if not os.path.isdir(base):
            QMessageBox.warning(self, "Nouveau dossier", "Sélectionnez d'abord un dossier parent existant.")
            return
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du nouveau dossier :")
        if ok and name.strip():
            new_p = os.path.join(base, name.strip())
            try:
                os.makedirs(new_p, exist_ok=True)
                self.set_target_directory(new_p)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de créer le dossier : {e}")

    def _select_default_location(self) -> None:
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            default_root = os.path.join(local_appdata, "Google", "Picasa2")
            self.set_target_directory(default_root)

    def _on_confirm(self) -> None:
        target = self.edit_target.text().strip()
        if not target:
            QMessageBox.warning(self, "Répertoire requis", "Veuillez sélectionner un répertoire.")
            return
        self.selected_path = target
        self.persist_as_default = self.chk_default.isChecked()
        self.accept()

