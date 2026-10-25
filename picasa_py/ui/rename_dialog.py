"""
FR: Boîte de dialogue de renommage par lot de Picasa.
Reproduit fidèlement RenameDialog et ExampleTransformer@RenameDialog.
EN: Picasa Batch Rename Dialog.
Reproduces RenameDialog and ExampleTransformer@RenameDialog faithfully.

Ref: picasa3.exe @ 0x00936F78 (RenameDialog)
Ref: rename.fen / RENAME_FR.XML
Ref: SHORTCUTS.XML @ ID_FILE_RENAME (F2)
"""

from __future__ import annotations
import os
import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument


class PicasaRenameDialog(QDialog):
    """
    FR: Boîte de dialogue officielle de renommage de fichiers par lot.
    EN: Official Picasa batch file rename dialog.
    Ref: rename.fen, RENAME_FR.XML, RenameDialog
    """

    def __init__(
        self,
        file_paths: List[str],
        style: Optional[PicasaStyle] = None,
        parent: Optional[QWidget] = None
    ):
        """
        FR: Initialise la boîte de dialogue de renommage par lot avec la liste de fichiers sélectionnés.
        EN: Initializes the batch rename dialog with the list of selected files.
        """
        super().__init__(parent)
        self.file_paths = file_paths
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(self.res_mgr.get_xml_string("rename/window1.title", "Renommer les fichiers"))
        self.setFixedWidth(400)

        # FR: Récupération des métadonnées du premier fichier pour l'aperçu d'exemple
        # EN: Retrieve metadata from the first file for the sample preview
        self.first_ext = ".jpg"
        self.first_date_str = ""
        self.first_size_str = ""
        if self.file_paths:
            first_p = Path(self.file_paths[0])
            self.first_ext = first_p.suffix
            self._extract_sample_info(first_p)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # FR: 1. Nombre de fichiers / EN: 1. File count (Ref: rename/label2.title & rename/bind3.format)
        count = len(self.file_paths)
        if count == 1:
            count_text = self.res_mgr.get_xml_string("rename/label2.title", "1 fichier à renommer")
        else:
            fmt = self.res_mgr.get_xml_string("rename/bind3.format", "%s fichier(s) à renommer.")
            count_text = fmt % count
        self.lbl_count = QLabel(count_text)
        layout.addWidget(self.lbl_count)

        # FR: 2. Saisie du nom de base / EN: 2. Base name input (Ref: rename/label5.title)
        self.grp_name = QGroupBox(self.res_mgr.get_xml_string(
            "rename/label5.title",
            "Entrez un nouveau nom pour ces fichiers :"
        ))
        lay_name = QVBoxLayout(self.grp_name)
        initial_name = Path(self.file_paths[0]).stem if self.file_paths else "Photo"
        self.edit_basename = QLineEdit(initial_name)
        self.edit_basename.textChanged.connect(self._update_sample_preview)
        lay_name.addWidget(self.edit_basename)
        layout.addWidget(self.grp_name)

        # FR: 3. Éléments à inclure / EN: 3. Elements to include (Ref: rename/labelgroup8.title)
        self.grp_inc = QGroupBox(self.res_mgr.get_xml_string(
            "rename/labelgroup8.title",
            "Inclure dans les noms de fichiers :"
        ))
        lay_inc = QVBoxLayout(self.grp_inc)
        self.chk_date = QCheckBox(self.res_mgr.get_xml_string("rename/date.title", "Date"))
        self.chk_date.setChecked(False)
        self.chk_date.toggled.connect(self._update_sample_preview)
        lay_inc.addWidget(self.chk_date)

        self.chk_size = QCheckBox(self.res_mgr.get_xml_string("rename/size.title", "Résolution d'image"))
        self.chk_size.setChecked(False)
        self.chk_size.toggled.connect(self._update_sample_preview)
        lay_inc.addWidget(self.chk_size)
        layout.addWidget(self.grp_inc)

        # FR: 4. Exemple en temps réel / EN: 4. Live sample preview (Ref: rename/sample.title, ExampleTransformer)
        self.grp_sample = QGroupBox(self.res_mgr.get_xml_string("rename/sample.title", "Exemple :"))
        lay_sample = QVBoxLayout(self.grp_sample)
        self.lbl_sample = QLabel()
        lay_sample.addWidget(self.lbl_sample)
        layout.addWidget(self.grp_sample)

        # FR: 5. Boutons Renommer / Annuler
        # EN: 5. Rename / Cancel buttons
        lay_btns = QHBoxLayout()
        lay_btns.addStretch(1)

        self.btn_rename = QPushButton(self.res_mgr.get_xml_string("rename/rename.title", "Renommer"))
        self.btn_rename.setObjectName("AcceptBtn")
        self.btn_rename.clicked.connect(self.accept)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("rename/button14.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)

        lay_btns.addWidget(self.btn_rename)
        lay_btns.addWidget(self.btn_cancel)
        layout.addLayout(lay_btns)

        self.apply_style(self.style)
        self._update_sample_preview()

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème Picasa actif au dialogue de renommage.
        EN: Dynamically applies the active Picasa theme to the rename dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#000000"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        border = "#4B5263" if is_dark else "#7F9DB9"
        grp_border = "#4B5263" if is_dark else "#C0BCB4"
        btn_bg = "#3A3F4B" if is_dark else "#F8F7F4"
        btn_hover = "#484E5C" if is_dark else "#EBF2F9"
        sample_fg = "#7FB5FF" if is_dark else "#154273"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
                font-size: 11px;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {grp_border};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                color: {fg};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                color: {fg};
            }}
            QCheckBox {{
                color: {fg};
                font-size: 11px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 4px 14px;
                font-size: 11px;
                min-width: 75px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: #3879D9;
                color: {fg};
            }}
            QPushButton#AcceptBtn {{
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #2859A3;
            }}
            QPushButton#AcceptBtn:hover {{
                background-color: #4A8BF0;
                color: #FFFFFF;
            }}
            QLineEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 3px;
                font-size: 11px;
            }}
        """)
        self.lbl_count.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {fg};")
        self.lbl_sample.setStyleSheet(
            f"font-family: Consolas, monospace; font-size: 11px; color: {sample_fg}; font-weight: bold;"
        )

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes selon la langue active.
        EN: Updates texts according to the active language.
        """
        self.setWindowTitle(self.res_mgr.get_xml_string("rename/window1.title", "Renommer les fichiers"))
        count = len(self.file_paths)
        if count == 1:
            count_text = self.res_mgr.get_xml_string("rename/label2.title", "1 fichier à renommer")
        else:
            fmt = self.res_mgr.get_xml_string("rename/bind3.format", "%s fichier(s) à renommer.")
            count_text = fmt % count
        self.lbl_count.setText(count_text)
        self.grp_name.setTitle(self.res_mgr.get_xml_string(
            "rename/label5.title",
            "Entrez un nouveau nom pour ces fichiers :"
        ))
        self.grp_inc.setTitle(self.res_mgr.get_xml_string(
            "rename/labelgroup8.title",
            "Inclure dans les noms de fichiers :"
        ))
        self.chk_date.setText(self.res_mgr.get_xml_string("rename/date.title", "Date"))
        self.chk_size.setText(self.res_mgr.get_xml_string("rename/size.title", "Résolution d'image"))
        self.grp_sample.setTitle(self.res_mgr.get_xml_string("rename/sample.title", "Exemple :"))
        self.btn_rename.setText(self.res_mgr.get_xml_string("rename/rename.title", "Renommer"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("rename/button14.title", "Annuler"))

    def _extract_sample_info(self, p: Path) -> None:
        """
        FR: Extrait la date et la résolution d'image pour l'aperçu d'exemple interactif.
        EN: Extracts the date and image resolution for the interactive sample preview.
        """
        if not p.exists():
            self.first_date_str = "2024-06-15"
            self.first_size_str = "1920x1080"
            return

        try:
            mtime = os.path.getmtime(p)
            dt = datetime.datetime.fromtimestamp(mtime)
            self.first_date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            self.first_date_str = "2024-06-15"

        try:
            with Image.open(p) as img:
                w, h = img.size
                self.first_size_str = f"{w}x{h}"
        except Exception:
            self.first_size_str = "1920x1080"

    def _format_filename(self, base: str, date_str: str, size_str: str, ext: str, index: int, total: int) -> str:
        """
        FR: Formate le nom de fichier final en intégrant date, base, résolution et compteur ordonné.
        EN: Formats the final filename incorporating date, base name, resolution, and ordered counter.
        Ref: ExampleTransformer@RenameDialog
        """
        parts = []
        if self.chk_date.isChecked() and date_str:
            parts.append(date_str)

        clean_base = base.strip()
        if clean_base:
            parts.append(clean_base)

        if self.chk_size.isChecked() and size_str:
            parts.append(size_str)

        prefix = " - ".join(parts) if parts else "Photo"

        if total > 1:
            digits = max(3, len(str(total)))
            return f"{prefix} - {index:0{digits}d}{ext}"
        else:
            return f"{prefix}{ext}"

    def _update_sample_preview(self) -> None:
        """
        FR: Met à jour l'exemple en direct lorsque l'utilisateur modifie les paramètres.
        EN: Updates the live sample preview when the user modifies settings.
        """
        base = self.edit_basename.text()
        total = len(self.file_paths)
        sample = self._format_filename(
            base=base,
            date_str=self.first_date_str,
            size_str=self.first_size_str,
            ext=self.first_ext,
            index=1,
            total=total
        )
        self.lbl_sample.setText(sample)
        self.btn_rename.setEnabled(bool(base.strip() or self.chk_date.isChecked()))

    def execute_rename(self) -> List[Tuple[str, str]]:
        """
        FR: Exécute le renommage effectif sur le disque et met à jour les fichiers .picasa.ini.
        Retourne la liste des correspondances (ancien_chemin, nouveau_chemin).
        EN: Executes the actual file rename on disk and updates the .picasa.ini files.
        Returns the list of (old_path, new_path) pairs.
        """
        base = self.edit_basename.text().strip()
        total = len(self.file_paths)
        renamed_pairs: List[Tuple[str, str]] = []

        # FR: Cache INI par répertoire pour mettre à jour les clés de sections
        # EN: Per-directory INI cache to update section keys
        ini_docs = {}

        for i, path_str in enumerate(self.file_paths):
            src_p = Path(path_str)
            if not src_p.exists():
                continue

            date_str = ""
            size_str = ""

            if self.chk_date.isChecked():
                try:
                    mtime = os.path.getmtime(src_p)
                    date_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                except Exception:
                    pass

            if self.chk_size.isChecked():
                try:
                    with Image.open(src_p) as img:
                        size_str = f"{img.width}x{img.height}"
                except Exception:
                    pass

            new_name = self._format_filename(
                base=base,
                date_str=date_str,
                size_str=size_str,
                ext=src_p.suffix,
                index=i + 1,
                total=total
            )

            dst_p = src_p.parent / new_name

            # FR: Si le nom est différent, procéder au renommage atomique
            # EN: If the name differs, perform atomic rename
            if src_p != dst_p:
                try:
                    # FR: Éviter d'écraser un fichier existant involontairement
                    # EN: Avoid unintentionally overwriting an existing file
                    if dst_p.exists() and dst_p.resolve() != src_p.resolve():
                        dst_p = src_p.parent / f"{dst_p.stem}_bis{dst_p.suffix}"

                    src_p.rename(dst_p)
                    renamed_pairs.append((str(src_p), str(dst_p)))

                    # FR: Renommer également la copie dans .picasaoriginals si elle existe (Ref: 0x00543642)
                    # EN: Also rename the backup copy in .picasaoriginals if it exists (Ref: 0x00543642)
                    for orig_sub in (".picasaoriginals", "Originals"):
                        orig_src = src_p.parent / orig_sub / src_p.name
                        orig_dst = src_p.parent / orig_sub / dst_p.name
                        if orig_src.exists() and not orig_dst.exists():
                            try:
                                orig_src.rename(orig_dst)
                            except Exception:
                                pass

                    # FR: Mise à jour de la section .picasa.ini correspondante
                    # EN: Update the corresponding .picasa.ini section
                    parent_dir = str(src_p.parent)
                    if parent_dir not in ini_docs:
                        ini_p = Path(parent_dir) / ".picasa.ini"
                        if ini_p.exists():
                            ini_docs[parent_dir] = PicasaIniParser.parse_file(str(ini_p))
                        else:
                            ini_docs[parent_dir] = None

                    doc = ini_docs.get(parent_dir)
                    if doc:
                        sec = doc.get_section(src_p.name)
                        if sec:
                            sec.name = dst_p.name
                            sec.raw_header = f"[{dst_p.name}]\r\n"

                except Exception:
                    pass

        # FR: Sauvegarder les fichiers .picasa.ini modifiés
        # EN: Save modified .picasa.ini files
        for p_dir, doc in ini_docs.items():
            if doc:
                try:
                    ini_p = Path(p_dir) / ".picasa.ini"
                    doc.write_file(str(ini_p))
                except Exception:
                    pass

        return renamed_pairs
