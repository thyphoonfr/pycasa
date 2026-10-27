"""
FR: Boîte de dialogue d'ajustement de la date et de l'heure des photos.
Reproduit fidèlement COffsetDate / AdjustTimeThread et offsettime.fen.
EN: Picasa Adjust Photo Date and Time Dialog.
Reproduces COffsetDate / AdjustTimeThread and offsettime.fen faithfully.

Ref: picasa3.exe @ 0x0077C670 (COffsetDate dialog creation, offsettime.fen)
Ref: picasa3.exe @ 0x0077CF70 (Relative vs absolute delta calculation, 100ns units)
Ref: picasa3.exe @ 0x0077CFD0 (AdjustTimeThread::SettingDates, 0x00CB4134)
Ref: picasa3.exe @ 0x00490580 (Relative timestamp shift across photos)
Ref: picasa3.exe @ 0x00490C10 (Absolute timestamp set across photos)
Ref: offsettime.fen / OFFSETTIME_FR.XML
Ref: STRINGRES_FR.XML @ eMenuTools::ID_TOOLS_ADJUST_TIMESTAMP (0x00CB40AC)
"""

from __future__ import annotations
import os
import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QGroupBox,
    QDateEdit, QTimeEdit, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QDate, QTime, QDateTime
from PySide6.QtGui import QPixmap, QImage

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.database import PicasaDatabase


# FR: Constante de conversion Windows FILETIME (intervalles de 100 ns depuis le 1er janv. 1601)
# EN: Windows FILETIME conversion constant (100-nanosecond intervals since Jan 1, 1601)
# Ref: picasa3.exe @ 0x0077CF70 (0x989680 = 10,000,000, 11644473600 seconds between 1601 and 1970)
WINDOWS_EPOCH_DIFF_SECONDS = 11644473600
FILETIME_TICKS_PER_SECOND = 10_000_000


def unix_to_filetime(timestamp: float) -> int:
    """
    FR: Convertit un horodatage POSIX en FILETIME Windows (uint64).
    EN: Converts a POSIX timestamp to Windows FILETIME (uint64).
    """
    return int((timestamp + WINDOWS_EPOCH_DIFF_SECONDS) * FILETIME_TICKS_PER_SECOND)


def filetime_to_unix(filetime: int) -> float:
    """
    FR: Convertit un FILETIME Windows en horodatage POSIX.
    EN: Converts a Windows FILETIME to a POSIX timestamp.
    """
    return (filetime / FILETIME_TICKS_PER_SECOND) - WINDOWS_EPOCH_DIFF_SECONDS


def get_photo_datetime(path: str) -> datetime.datetime:
    """
    FR: Extrait la date et l'heure réelles de la photo, en privilégiant l'EXIF DateTimeOriginal / DateTime,
    puis le mtime du fichier sur disque.
    EN: Extracts the actual photo date and time, preferring EXIF DateTimeOriginal / DateTime,
    then falling back to disk mtime.
    """
    p = Path(path)
    if p.exists() and p.suffix.lower() in (".jpg", ".jpeg"):
        try:
            with Image.open(p) as img:
                exif = img.getexif()
                # 36867: DateTimeOriginal, 36868: DateTimeDigitized, 306: DateTime
                for tag in (36867, 36868, 306):
                    val = exif.get(tag)
                    if val and isinstance(val, str):
                        try:
                            return datetime.datetime.strptime(val.strip(), "%Y:%m:%d %H:%M:%S")
                        except Exception:
                            pass
        except Exception:
            pass

    if p.exists():
        try:
            mtime = os.path.getmtime(p)
            return datetime.datetime.fromtimestamp(mtime)
        except Exception:
            pass

    return datetime.datetime.now()


class PicasaAdjustTimeDialog(QDialog):
    """
    FR: Boîte de dialogue officielle d'ajustement de la date et de l'heure des photos.
    EN: Official Picasa photo date and time adjustment dialog.
    Ref: offsettime.fen, OFFSETTIME_FR.XML, COffsetDate @ 0x0077C670
    """

    def __init__(
        self,
        file_paths: List[str],
        db: Optional[PicasaDatabase] = None,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QWidget] = None
    ):
        """
        FR: Initialise la boîte de dialogue d'ajustement de date et heure pour les fichiers sélectionnés.
        EN: Initializes the date and time adjustment dialog for the selected files.
        """
        super().__init__(parent)
        self.file_paths = file_paths
        self.db = db
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        # FR: Titre dynamique selon le nombre d'éléments / EN: Dynamic title based on item count (Ref: picasa3.exe @ 0x00CB40AC)
        base_title = self.res_mgr.get_xml_string("offsettime/window1.title", "Ajuster la date de la photo")
        if len(self.file_paths) > 1:
            self.setWindowTitle(f"{base_title} - {len(self.file_paths)} éléments")
        else:
            self.setWindowTitle(base_title)

        self.setFixedWidth(440)

        # FR: Récupération de la date de la première photo de référence
        # EN: Retrieve the date of the first reference photo
        self.reference_path = self.file_paths[0] if self.file_paths else ""
        self.original_dt = get_photo_datetime(self.reference_path) if self.reference_path else datetime.datetime.now()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 14, 14, 14)

        # FR: 1. Rangée supérieure : Vignette à gauche + Éditeurs de date à droite
        # EN: 1. Top row: Thumbnail on the left + Date editors on the right
        # Ref: <group layout="row"> <printpreview name="thumb"/> ... </group>
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # FR: Vignette de la photo / EN: Photo thumbnail (Ref: printpreview name="thumb")
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(120, 120)
        self.lbl_thumb.setFrameShape(QFrame.Shape.Box)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_thumbnail()
        top_row.addWidget(self.lbl_thumb)

        # FR: Colonne de droite avec les deux groupes de date
        # EN: Right column with the two date groups
        date_col = QVBoxLayout()
        date_col.setSpacing(8)

        # FR: Groupe 1 : Date actuelle de la photo / EN: Group 1: Current photo date (Ref: offsettime/labelgroup5.title)
        self.grp_current = QGroupBox(self.res_mgr.get_xml_string(
            "offsettime/labelgroup5.title",
            "Date de la photo affichée : "
        ))
        lay_current = QHBoxLayout(self.grp_current)
        lay_current.setSpacing(6)
        lay_current.setContentsMargins(8, 8, 8, 8)

        self.edit_curr_date = QDateEdit()
        self.edit_curr_date.setDisplayFormat("dd/MM/yyyy")
        self.edit_curr_date.setDate(QDate(self.original_dt.year, self.original_dt.month, self.original_dt.day))
        self.edit_curr_date.setEnabled(False)

        self.edit_curr_time = QTimeEdit()
        self.edit_curr_time.setDisplayFormat("HH:mm:ss")
        self.edit_curr_time.setTime(QTime(self.original_dt.hour, self.original_dt.minute, self.original_dt.second))
        self.edit_curr_time.setEnabled(False)

        lay_current.addWidget(self.edit_curr_date)
        lay_current.addWidget(self.edit_curr_time)
        date_col.addWidget(self.grp_current)

        # FR: Groupe 2 : Nouvelle date de la photo / EN: Group 2: New photo date (Ref: offsettime/labelgroup9.title)
        self.grp_new = QGroupBox(self.res_mgr.get_xml_string(
            "offsettime/labelgroup9.title",
            "Date de la nouvelle photo : "
        ))
        lay_new = QHBoxLayout(self.grp_new)
        lay_new.setSpacing(6)
        lay_new.setContentsMargins(8, 8, 8, 8)

        self.edit_new_date = QDateEdit()
        self.edit_new_date.setCalendarPopup(True)
        self.edit_new_date.setDisplayFormat("dd/MM/yyyy")
        self.edit_new_date.setDate(QDate(self.original_dt.year, self.original_dt.month, self.original_dt.day))

        self.edit_new_time = QTimeEdit()
        self.edit_new_time.setDisplayFormat("HH:mm:ss")
        self.edit_new_time.setTime(QTime(self.original_dt.hour, self.original_dt.minute, self.original_dt.second))

        lay_new.addWidget(self.edit_new_date)
        lay_new.addWidget(self.edit_new_time)
        date_col.addWidget(self.grp_new)

        top_row.addLayout(date_col)
        layout.addLayout(top_row)

        # FR: 2. Options d'ajustement / EN: 2. Adjustment options (Ref: radiogroup name="adjust_type")
        self.grp_adjust = QGroupBox()
        lay_adjust = QVBoxLayout(self.grp_adjust)
        lay_adjust.setSpacing(6)
        lay_adjust.setContentsMargins(10, 8, 10, 8)

        # Radio relative (Ref: offsettime/relative.title)
        self.radio_relative = QRadioButton(self.res_mgr.get_xml_string(
            "offsettime/relative.title",
            "Ajuster la date des photos en fonction de la quantité"
        ))
        self.radio_relative.setChecked(True)
        lay_adjust.addWidget(self.radio_relative)

        # Radio absolute (Ref: offsettime/absolute.title)
        self.radio_absolute = QRadioButton(self.res_mgr.get_xml_string(
            "offsettime/absolute.title",
            "Définir la même date et la même heure pour toutes les photos"
        ))
        lay_adjust.addWidget(self.radio_absolute)

        layout.addWidget(self.grp_adjust)

        # FR: 3. Boutons d'action (OK / Annuler) / EN: 3. Action buttons (OK / Cancel) (Ref: buttongroup)
        lay_btns = QHBoxLayout()
        lay_btns.addStretch()

        self.btn_ok = QPushButton(self.res_mgr.get_xml_string("offsettime/ok.title", "OK"))
        self.btn_ok.setObjectName("PrimaryAction")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)
        lay_btns.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("offsettime/button18.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)
        lay_btns.addWidget(self.btn_cancel)

        layout.addLayout(lay_btns)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique dynamiquement le thème Picasa actif au dialogue.
        EN: Dynamically applies the active Picasa theme to the dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#000000"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        dis_bg = "#282C34" if is_dark else "#E8E7E3"
        dis_fg = "#808694" if is_dark else "#555555"
        border = "#4B5263" if is_dark else "#7F9DB9"
        grp_border = "#4B5263" if is_dark else "#C0BCB4"
        btn_bg = "#3A3F4B" if is_dark else "#F8F7F4"
        btn_hover = "#484E5C" if is_dark else "#EBF2F9"

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
                font-size: 11px;
                color: {fg};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                color: {fg};
            }}
            QDateEdit, QTimeEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 2px 4px;
                font-size: 11px;
            }}
            QDateEdit:disabled, QTimeEdit:disabled {{
                background-color: {dis_bg};
                color: {dis_fg};
            }}
            QRadioButton {{
                font-size: 11px;
                color: {fg};
                spacing: 6px;
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
            QPushButton#PrimaryAction {{
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #2859A3;
            }}
            QPushButton#PrimaryAction:hover {{
                background-color: #4A8BF0;
                color: #FFFFFF;
            }}
        """)
        self.lbl_thumb.setStyleSheet(f"background-color: {inp_bg}; border: 1px solid {border}; color: {fg};")

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les textes selon la langue active.
        EN: Updates texts according to the active language.
        """
        base_title = self.res_mgr.get_xml_string("offsettime/window1.title", "Ajuster la date de la photo")
        if len(self.file_paths) > 1:
            self.setWindowTitle(f"{base_title} - {len(self.file_paths)} éléments")
        else:
            self.setWindowTitle(base_title)
        self.grp_current.setTitle(self.res_mgr.get_xml_string("offsettime/labelgroup5.title", "Date de la photo affichée : "))
        self.grp_new.setTitle(self.res_mgr.get_xml_string("offsettime/labelgroup9.title", "Date de la nouvelle photo : "))
        self.radio_relative.setText(self.res_mgr.get_xml_string(
            "offsettime/relative.title",
            "Ajuster la date des photos en fonction de la quantité"
        ))
        self.radio_absolute.setText(self.res_mgr.get_xml_string(
            "offsettime/absolute.title",
            "Définir la même date et la même heure pour toutes les photos"
        ))
        self.btn_ok.setText(self.res_mgr.get_xml_string("offsettime/ok.title", "OK"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("offsettime/button18.title", "Annuler"))

    def _load_thumbnail(self) -> None:
        """
        FR: Charge et affiche l'aperçu de la photo de référence.
        EN: Loads and displays the preview of the reference photo.
        """
        if not self.reference_path or not os.path.exists(self.reference_path):
            self.lbl_thumb.setText("Aperçu")
            return

        try:
            pix = QPixmap(self.reference_path)
            if not pix.isNull():
                scaled = pix.scaled(114, 114, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.lbl_thumb.setPixmap(scaled)
            else:
                self.lbl_thumb.setText("Aperçu")
        except Exception:
            self.lbl_thumb.setText("Aperçu")

    def get_target_datetime(self) -> datetime.datetime:
        """
        FR: Renvoie le nouvel objet datetime sélectionné par l'utilisateur.
        EN: Returns the new datetime object selected by the user.
        """
        d = self.edit_new_date.date()
        t = self.edit_new_time.time()
        return datetime.datetime(d.year(), d.month(), d.day(), t.hour(), t.minute(), t.second())

    def is_relative(self) -> bool:
        """
        FR: Indique si le mode de décalage relatif est sélectionné.
        EN: Indicates whether the relative offset mode is selected.
        """
        return self.radio_relative.isChecked()

    def execute_adjustment(self) -> List[Tuple[str, datetime.datetime]]:
        """
        FR: Applique l'ajustement de date/heure aux fichiers sélectionnés.
        Met à jour le mtime du fichier sur disque, les métadonnées EXIF JPEG et thumbindex.db.
        EN: Applies the date/time adjustment to the selected files.
        Updates the file mtime on disk, JPEG EXIF metadata, and thumbindex.db records.
        Ref: AdjustTimeThread @ 0x0077CFD0
        """
        new_target_dt = self.get_target_datetime()
        is_rel = self.is_relative()
        delta = new_target_dt - self.original_dt

        results: List[Tuple[str, datetime.datetime]] = []

        for p_str in self.file_paths:
            p = Path(p_str)
            if not p.exists():
                continue

            try:
                # FR: 1. Calcul de la nouvelle date pour cette photo
                # EN: 1. Compute the new date for this photo
                if is_rel:
                    orig_dt = get_photo_datetime(str(p))
                    final_dt = orig_dt + delta
                else:
                    final_dt = new_target_dt

                new_ts = final_dt.timestamp()

                # FR: 2. Mise à jour EXIF sans perte si JPEG (avant os.utime pour ne pas écraser st_mtime)
                # EN: 2. Lossless EXIF APP1 update if JPEG (before os.utime so st_mtime is not overwritten)
                # Ref: picasa3.exe @ 0x00490580, 0x00490C10, 0x009ED330, 0x00992780
                if p.suffix.lower() in (".jpg", ".jpeg"):
                    try:
                        import struct
                        exif_str = final_dt.strftime("%Y:%m:%d %H:%M:%S")
                        with Image.open(p) as img:
                            exif = img.getexif()
                            exif[306] = exif_str    # DateTime (0x0132)
                            exif[36867] = exif_str  # DateTimeOriginal (0x9003)
                            exif[36868] = exif_str  # DateTimeDigitized (0x9004)
                            try:
                                exif_ifd = exif.get_ifd(0x8769)
                                exif_ifd[36867] = exif_str
                                exif_ifd[36868] = exif_str
                            except Exception:
                                pass
                            exif_payload = exif.tobytes()
                        raw_jpg = p.read_bytes()
                        if len(raw_jpg) >= 4 and raw_jpg[:2] == b"\xff\xd8" and len(exif_payload) + 2 <= 65535:
                            new_app1 = b"\xff\xe1" + struct.pack(">H", len(exif_payload) + 2) + exif_payload
                            pos = 2
                            n_jpg = len(raw_jpg)
                            out_chunks = [b"\xff\xd8"]
                            replaced = False
                            while pos + 4 <= n_jpg:
                                if raw_jpg[pos] != 0xFF:
                                    break
                                marker = raw_jpg[pos : pos + 2]
                                if marker in (b"\xff\xda", b"\xff\xd9"):
                                    break
                                if marker == b"\xff\x00":
                                    pos += 1
                                    continue
                                seg_len = struct.unpack_from(">H", raw_jpg, pos + 2)[0]
                                if seg_len < 2 or pos + 2 + seg_len > n_jpg:
                                    break
                                seg_bytes = raw_jpg[pos : pos + 2 + seg_len]
                                if marker == b"\xff\xe1" and seg_bytes[4:10] == b"Exif\x00\x00":
                                    if not replaced:
                                        out_chunks.append(new_app1)
                                        replaced = True
                                else:
                                    out_chunks.append(seg_bytes)
                                pos += 2 + seg_len
                            if not replaced:
                                if len(out_chunks) > 1 and out_chunks[1].startswith(b"\xff\xe0"):
                                    out_chunks.insert(2, new_app1)
                                else:
                                    out_chunks.insert(1, new_app1)
                            out_chunks.append(raw_jpg[pos:])
                            p.write_bytes(b"".join(out_chunks))
                    except Exception:
                        pass

                # FR: 3. Mise à jour de l'horodatage sur disque
                # EN: 3. Update timestamp on disk
                os.utime(str(p), (new_ts, new_ts))

                # FR: 4. Mise à jour de la base de données si active (thumbindex.db, imagedata_originfast, thumbs_index.db)
                # EN: 4. Update database if active (thumbindex.db, imagedata_originfast, thumbs_index.db)
                if self.db and self.db.thumbindex:
                    from picasa_py.scanner.scanner import file_filetimes, compute_originfast_hash
                    from picasa_py.db.blockfile import compute_thumb_checksum
                    ft = unix_to_filetime(new_ts)
                    _, ft2_disk, fsize_disk = file_filetimes(p)
                    idx = self.db.find_photo_index(str(p)) if hasattr(self.db, "find_photo_index") else None
                    if idx is None:
                        norm_path = os.path.abspath(str(p)).lower()
                        for r_i, r_cand in enumerate(self.db.thumbindex.records):
                            full = self.db.get_media_full_path(r_i)
                            if full and os.path.abspath(full).lower() == norm_path:
                                idx = r_i
                                break
                    if idx is not None and 0 <= idx < len(self.db.thumbindex.records):
                        rec = self.db.thumbindex.records[idx]
                        rec.ft1 = ft
                        rec.ft2 = ft2_disk or ft
                        rec.size = fsize_disk
                        rec.file_size = fsize_disk
                        self.db.thumbindex.dirty = True
                        pmp_of = self.db.pmps.get("imagedata_originfast") if hasattr(self.db, "pmps") else None
                        if pmp_of is not None and idx < len(pmp_of.records):
                            pmp_of.records[idx] = compute_originfast_hash(p)
                            pmp_of.dirty = True
                        folder_p = ""
                        if 0 <= rec.parent_idx < len(self.db.thumbindex.records):
                            folder_p = self.db.thumbindex.records[rec.parent_idx].path
                        new_cs = compute_thumb_checksum(folder_p, rec.path, rec.ft2, rec.size)
                        indices_to_update = [idx]
                        if hasattr(self.db, "_get_face_children"):
                            indices_to_update.extend(self.db._get_face_children(idx))
                        for stem in ("thumbs", "thumbs2", "bigthumbs", "previews"):
                            b_idx = getattr(self.db, "block_indices", {}).get(stem)
                            if b_idx is not None:
                                for u_idx in indices_to_update:
                                    b_ent = b_idx.get_entry(u_idx) if hasattr(b_idx, "get_entry") else None
                                    if b_ent is not None and not b_ent.is_empty:
                                        if stem in ("thumbs", "thumbs2"):
                                            b_idx.checksums[u_idx] = new_cs
                                        elif hasattr(self.db, "compute_entry_checksum"):
                                            b_idx.checksums[u_idx] = self.db.compute_entry_checksum(u_idx, stem)
                                        b_idx.dirty = True

                results.append((str(p), final_dt))

            except Exception:
                continue

        # FR: Sauvegarde de la base via PicasaDatabase
        # EN: Save database via PicasaDatabase
        if self.db and hasattr(self.db, "save_database"):
            try:
                self.db.save_database()
            except Exception:
                pass
        elif self.db and hasattr(self.db, "save_all"):
            try:
                self.db.save_all()
            except Exception:
                pass
        elif self.db and self.db.thumbindex and self.db.db3_dir and self.db.db3_dir.exists():
            try:
                self.db.thumbindex.save(str(self.db.db3_dir / "thumbindex.db"))
            except Exception:
                pass

        return results
