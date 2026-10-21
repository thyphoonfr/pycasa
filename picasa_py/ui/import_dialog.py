"""
FR : Écran d'importation / acquisition de médias pour PyCasa (PicasaImportDialog / AcquirePanel).
EN : Import / Acquire Screen for PyCasa (PicasaImportDialog / AcquirePanel).
Faithful reproduction of Picasa 3 Camera & Media Import screen.

Ref: picasa3.exe @ ACQUIREPANEL_TEXT.XML, ACQUIREPANEL_TEXT_FR.XML
Ref: picasa3.exe @ 0x0088C3EC (ID_FILE_IMPORTPICTURE)
"""

from __future__ import annotations
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QCheckBox, QProgressBar, QMessageBox,
    QFileDialog, QListWidget, QListWidgetItem, QSplitter, QWidget,
    QFrame
)
from PySide6.QtCore import Qt, QSize, Signal, QThread
from PySide6.QtGui import QIcon, QPixmap, QImage

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.database import PicasaDatabase


SUPPORTED_IMPORT_EXTS = {
    ".jpg", ".jpeg", ".jpe", ".png", ".bmp", ".gif", ".webp",
    ".tif", ".tiff", ".tga", ".raw", ".cr2", ".nef", ".arw",
    ".mp4", ".mov", ".avi", ".wmv", ".mkv", ".m4v"
}


class ImportWorker(QThread):
    """
    FR : Thread d'arrière-plan copiant les fichiers sélectionnés vers le dossier de destination.
    EN : Background thread copying selected media files to the destination folder.
    """
    progress = Signal(int, int, str)       # cur, total, current_filename
    finished = Signal(int, int, str)       # success_count, error_count, dest_folder

    def __init__(
        self,
        files_to_copy: List[str],
        destination_dir: str,
        delete_source_after: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.files_to_copy = files_to_copy
        self.destination_dir = destination_dir
        self.delete_source_after = delete_source_after
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        os.makedirs(self.destination_dir, exist_ok=True)
        total = len(self.files_to_copy)
        success = 0
        errors = 0

        for i, src_path in enumerate(self.files_to_copy):
            if self._is_cancelled:
                break
            fname = os.path.basename(src_path)
            self.progress.emit(i + 1, total, fname)
            try:
                dest_path = os.path.join(self.destination_dir, fname)
                if os.path.abspath(src_path) != os.path.abspath(dest_path):
                    shutil.copy2(src_path, dest_path)
                    if self.delete_source_after:
                        try:
                            os.remove(src_path)
                        except Exception:
                            pass
                success += 1
            except Exception:
                errors += 1

        self.finished.emit(success, errors, self.destination_dir)


class PicasaImportDialog(QDialog):
    """
    FR : Écran d'importation de médias depuis une carte mémoire, un appareil ou un dossier.
    EN : Media import screen from a memory card, camera device, or folder.
    Ref: acquirepanel / ACQUIREPANEL_TEXT_FR.XML, IMPORT_FR.XML
    """
    import_completed = Signal(str, int)  # destination_folder, count

    def __init__(
        self,
        db: Optional[PicasaDatabase] = None,
        default_source_dir: Optional[str] = None,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.db = db
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(self.res_mgr.get_xml_string("import/window1.title", "Importer des photos — Picasa"))
        self.resize(780, 560)

        self.discovered_files: List[str] = []
        self._worker: Optional[ImportWorker] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. En-tête : Source et Destination
        self.header_frame = QFrame()
        self.header_frame.setObjectName("ImportHeaderFrame")
        self.header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        h_layout = QVBoxLayout(self.header_frame)
        h_layout.setSpacing(8)

        # Ligne Source
        row_src = QHBoxLayout()
        self.lbl_from = QLabel(self.res_mgr.get_xml_string("acquirepanel/fromtext", "Importer à partir de :"))
        self.lbl_from.setFixedWidth(130)
        self.lbl_from.setStyleSheet("font-weight: bold;")
        row_src.addWidget(self.lbl_from)

        self.combo_source = QComboBox()
        self.combo_source.currentIndexChanged.connect(self._on_source_changed)
        row_src.addWidget(self.combo_source, 1)

        self.btn_browse_source = QPushButton(self.res_mgr.get_xml_string("export/changeloc.title", "Parcourir..."))
        self.btn_browse_source.clicked.connect(self._on_browse_source)
        row_src.addWidget(self.btn_browse_source)
        h_layout.addLayout(row_src)

        # Ligne Destination
        row_dest = QHBoxLayout()
        self.lbl_to = QLabel(self.res_mgr.get_xml_string("acquirepanel/totext", "Importer dans :"))
        self.lbl_to.setFixedWidth(130)
        row_dest.addWidget(self.lbl_to)

        default_pics = os.path.expanduser("~/Pictures")
        if not os.path.exists(default_pics):
            default_pics = os.path.expanduser("~")
        self.edit_dest_dir = QLineEdit(default_pics)
        row_dest.addWidget(self.edit_dest_dir, 1)

        self.btn_browse_dest = QPushButton(self.res_mgr.get_xml_string("export/changeloc.title", "Parcourir..."))
        self.btn_browse_dest.clicked.connect(self._on_browse_dest)
        row_dest.addWidget(self.btn_browse_dest)
        h_layout.addLayout(row_dest)

        # Ligne Sous-dossier & Doublons
        row_sub = QHBoxLayout()
        self.lbl_sub = QLabel(self.res_mgr.get_xml_string("acquirepanel/foldertitletext", "Nom du dossier :"))
        self.lbl_sub.setFixedWidth(130)
        row_sub.addWidget(self.lbl_sub)

        today_name = datetime.now().strftime("%Y-%m-%d")
        self.edit_subfolder = QLineEdit(today_name)
        row_sub.addWidget(self.edit_subfolder, 1)

        self.chk_exclude_dupes = QCheckBox(self.res_mgr.get_xml_string("acquirepanel/dup_checkbox", "Exclure les doublons"))
        self.chk_exclude_dupes.setChecked(True)
        self.chk_exclude_dupes.toggled.connect(self._populate_list)
        row_sub.addWidget(self.chk_exclude_dupes)

        h_layout.addLayout(row_sub)

        # Ligne Après copie
        row_after = QHBoxLayout()
        self.lbl_after = QLabel(self.res_mgr.get_xml_string("acquirepanel/aftercopyinglabel", "Après copie :"))
        self.lbl_after.setFixedWidth(130)
        row_after.addWidget(self.lbl_after)

        self.combo_after = QComboBox()
        self.combo_after.addItem("Laisser les photos sur l'appareil", False)
        self.combo_after.addItem("Supprimer les photos de l'appareil", True)
        row_after.addWidget(self.combo_after, 1)
        h_layout.addLayout(row_after)

        layout.addWidget(self.header_frame)

        # 2. Zone d'aperçu des éléments découverts
        mid_bar = QHBoxLayout()
        self.lbl_status = QLabel("0 photo(s) trouvée(s)")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        mid_bar.addWidget(self.lbl_status)
        mid_bar.addStretch(1)

        self.btn_sel_all = QPushButton(self.res_mgr.get_stringres("SelectAll", "Tout sélectionner"))
        self.btn_sel_all.clicked.connect(self._select_all)
        mid_bar.addWidget(self.btn_sel_all)

        self.btn_desel_all = QPushButton(self.res_mgr.get_stringres("SelectNone", "Tout désélectionner"))
        self.btn_desel_all.clicked.connect(self._deselect_all)
        mid_bar.addWidget(self.btn_desel_all)
        layout.addLayout(mid_bar)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(100, 100))
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setSpacing(8)
        self.list_widget.itemChanged.connect(self._update_counts)
        layout.addWidget(self.list_widget, 1)

        # 3. Barre de progression (masquée par défaut)
        self.prog_bar = QProgressBar()
        self.prog_bar.setVisible(False)
        layout.addWidget(self.prog_bar)

        # 4. Boutons d'action (Ref: acquirepanel/anowbutton, import_selected, acancelbutton)
        btn_bar = QHBoxLayout()
        btn_bar.addStretch(1)

        self.btn_import_all = QPushButton(self.res_mgr.get_xml_string("acquirepanel/anowbutton", "Tout importer"))
        self.btn_import_all.setObjectName("PrimaryBtn")
        self.btn_import_all.clicked.connect(lambda: self._start_import(only_selected=False))
        btn_bar.addWidget(self.btn_import_all)

        self.btn_import_sel = QPushButton(self.res_mgr.get_xml_string("acquirepanel/import_selected", "Importer les éléments sélectionnés"))
        self.btn_import_sel.clicked.connect(lambda: self._start_import(only_selected=True))
        btn_bar.addWidget(self.btn_import_sel)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("acquirepanel/acancelbutton", "Annuler"))
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_bar.addWidget(self.btn_cancel)

        layout.addLayout(btn_bar)

        # Initialisation des sources et application du thème actif
        self._init_sources(default_source_dir)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème PicasaStyle à la boîte de dialogue d'importation.
        EN : Dynamically applies the PicasaStyle theme to the Import dialog.
        """
        self.style = style or PicasaStyle.instance()
        s = self.style
        dlg_bg = s.window_bgcolor.name() if s.is_dark else "#ECE9D8"
        hdr_bg = s.alist_catcolor.name() if s.is_dark else "#F5F3EC"
        txt_col = s.alist_textcolor.name() if s.is_dark else "#111111"
        border_col = s.splitter_color.name() if s.is_dark else "#C0C0C0"
        input_bg = s.thumb_card_bgcolor.name() if s.is_dark else "#FFFFFF"
        input_border = s.topbar_btn_border.name() if s.is_dark else "#7F9DB9"
        btn_bg = s.topbar_btn_bg_start.name() if s.is_dark else "#F0F0F0"
        btn_hover = s.topbar_btn_bg_end.name() if s.is_dark else "#E5E5E5"
        accent = s.accent_color.name()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {txt_col};
            }}
            QFrame#ImportHeaderFrame {{
                background-color: {hdr_bg};
                border: 1px solid {border_col};
                border-radius: 3px;
                padding: 6px;
            }}
            QLabel, QCheckBox {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {txt_col};
                background: transparent;
                border: none;
            }}
            QLineEdit, QComboBox {{
                background-color: {input_bg};
                color: {txt_col};
                border: 1px solid {input_border};
                border-radius: 2px;
                padding: 3px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {txt_col};
                selection-background-color: {accent};
                selection-color: #FFFFFF;
                font-size: 9pt;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {txt_col};
                border: 1px solid {input_border};
                border-radius: 3px;
                padding: 4px 12px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: {accent};
                color: {txt_col};
            }}
            QPushButton#PrimaryBtn {{
                background-color: {accent};
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid {accent};
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {s.accent_color.lighter(115).name()};
                color: #FFFFFF;
            }}
            QListWidget {{
                background-color: #3B3E42;
                border: 1px solid {border_col};
                color: #FFFFFF;
            }}
        """)

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les libellés de la boîte de dialogue d'importation selon la langue active.
        EN : Updates the Import dialog labels according to the active language.
        """
        self.setWindowTitle(self.res_mgr.get_xml_string("import/window1.title", "Importer des photos — Picasa"))
        self.lbl_from.setText(self.res_mgr.get_xml_string("acquirepanel/fromtext", "Importer à partir de :"))
        self.lbl_to.setText(self.res_mgr.get_xml_string("acquirepanel/totext", "Importer dans :"))
        self.lbl_sub.setText(self.res_mgr.get_xml_string("acquirepanel/foldertitletext", "Nom du dossier :"))
        self.chk_exclude_dupes.setText(self.res_mgr.get_xml_string("acquirepanel/dup_checkbox", "Exclure les doublons"))
        self.lbl_after.setText(self.res_mgr.get_xml_string("acquirepanel/aftercopyinglabel", "Après copie :"))
        self.btn_sel_all.setText(self.res_mgr.get_stringres("SelectAll", "Tout sélectionner"))
        self.btn_desel_all.setText(self.res_mgr.get_stringres("SelectNone", "Tout désélectionner"))
        self.btn_import_all.setText(self.res_mgr.get_xml_string("acquirepanel/anowbutton", "Tout importer"))
        self.btn_import_sel.setText(self.res_mgr.get_xml_string("acquirepanel/import_selected", "Importer les éléments sélectionnés"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("acquirepanel/acancelbutton", "Annuler"))


    def _init_sources(self, default_dir: Optional[str] = None) -> None:
        self.combo_source.blockSignals(True)
        self.combo_source.clear()

        if default_dir and os.path.exists(default_dir):
            self.combo_source.insertItem(0, f"Dossier : {default_dir}", default_dir)

        # Disques amovibles / Windows drives
        if sys.platform == "win32":
            import string
            for letter in string.ascii_uppercase:
                drv = f"{letter}:\\"
                if os.path.exists(drv):
                    dcim = os.path.join(drv, "DCIM")
                    if os.path.exists(dcim):
                        self.combo_source.addItem(f"Appareil / Carte mémoire ({letter}:\\DCIM)", dcim)
                    elif letter not in ("C", "D"):
                        self.combo_source.addItem(f"Lecteur amovible ({letter}:)", drv)

        self.combo_source.addItem("Choisir un dossier...", "__BROWSE__")
        self.combo_source.blockSignals(False)

        if self.combo_source.count() > 1:
            self.combo_source.setCurrentIndex(0)
            self._scan_current_source()
        else:
            self.lbl_status.setText("Sélectionnez une source d'importation.")

    def _on_source_changed(self, idx: int) -> None:
        data = self.combo_source.currentData()
        if data == "__BROWSE__":
            self._on_browse_source()
        elif data and os.path.exists(data):
            self._scan_current_source()

    def _on_browse_source(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choisir le dossier source à importer")
        if d:
            self.combo_source.blockSignals(True)
            self.combo_source.insertItem(0, f"Dossier : {d}", d)
            self.combo_source.setCurrentIndex(0)
            self.combo_source.blockSignals(False)
            self._scan_current_source()

    def _on_browse_dest(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination", self.edit_dest_dir.text())
        if d:
            self.edit_dest_dir.setText(d)

    def _scan_current_source(self) -> None:
        data = self.combo_source.currentData()
        if not data or data == "__BROWSE__" or not os.path.exists(data):
            return

        self.discovered_files.clear()
        try:
            for root, _, files in os.walk(data):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_IMPORT_EXTS:
                        self.discovered_files.append(os.path.join(root, f))
        except Exception:
            pass

        self._populate_list()

    def _populate_list(self) -> None:
        self.list_widget.clear()

        existing_names: Set[str] = set()
        if self.db and self.chk_exclude_dupes.isChecked():
            try:
                for entry in self.db.get_all_photos():
                    existing_names.add(os.path.basename(entry.filepath).lower())
            except Exception:
                pass

        for p in self.discovered_files:
            fname = os.path.basename(p)
            is_dupe = fname.lower() in existing_names

            item = QListWidgetItem(fname)
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            if is_dupe and self.chk_exclude_dupes.isChecked():
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setToolTip("Déjà présent dans la photothèque (Doublon)")
            else:
                item.setCheckState(Qt.CheckState.Checked)

            # Charger une miniature rapide pour les premiers fichiers
            if self.list_widget.count() < 60:
                try:
                    pix = QPixmap(p)
                    if not pix.isNull():
                        thumb = pix.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
                        item.setIcon(QIcon(thumb))
                except Exception:
                    pass

            self.list_widget.addItem(item)

        self._update_counts()

    def _select_all(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)
        self._update_counts()

    def _deselect_all(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._update_counts()

    def _update_counts(self) -> None:
        total = self.list_widget.count()
        checked = sum(1 for i in range(total) if self.list_widget.item(i).checkState() == Qt.CheckState.Checked)
        self.lbl_status.setText(f"{checked} sur {total} photo(s) sélectionnée(s)")
        self.btn_import_all.setEnabled(total > 0)
        self.btn_import_sel.setEnabled(checked > 0)

    def _start_import(self, only_selected: bool) -> None:
        target_files: List[str] = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if not only_selected or it.checkState() == Qt.CheckState.Checked:
                p = it.data(Qt.ItemDataRole.UserRole)
                if p:
                    target_files.append(p)

        if not target_files:
            QMessageBox.information(self, "Importer", "Aucune photo sélectionnée pour l'importation.")
            return

        base_dest = self.edit_dest_dir.text().strip()
        sub = self.edit_subfolder.text().strip()
        dest_dir = os.path.join(base_dest, sub) if sub else base_dest

        del_after = self.combo_after.currentData() is True

        self.prog_bar.setMaximum(len(target_files))
        self.prog_bar.setValue(0)
        self.prog_bar.setVisible(True)

        self.btn_import_all.setEnabled(False)
        self.btn_import_sel.setEnabled(False)
        self.btn_cancel.setText("Annuler")

        self._worker = ImportWorker(target_files, dest_dir, delete_source_after=del_after, parent=self)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_progress(self, cur: int, tot: int, fname: str) -> None:
        self.prog_bar.setValue(cur)
        self.lbl_status.setText(f"Importation : {cur}/{tot} — {fname}")

    def _on_worker_finished(self, succ: int, err: int, dest_dir: str) -> None:
        self.prog_bar.setVisible(False)
        self.lbl_status.setText(f"Importation terminée : {succ} photo(s) importée(s).")
        QMessageBox.information(
            self,
            "Importation terminée",
            f"{succ} fichier(s) importé(s) avec succès dans :\n{dest_dir}" + (f"\n({err} erreur(s))" if err else "")
        )
        self.import_completed.emit(dest_dir, succ)
        self.accept()

    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(1500)
        self.reject()
