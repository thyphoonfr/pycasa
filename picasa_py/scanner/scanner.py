"""
Picasa Directory Scanner & Auto-Indexing Engine (AVytDirScannerWindows / CScanner).

Scans watched directories, detects new or modified media files, extracts EXIF
dates & dimensions, generates high-quality JPEG thumbnails (256x256), and appends
records to thumbindex.db and thumbs_0.db.

Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows)
Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex / add_media_record)
Ref: picasa3.exe @ 0x006B75F0 (CBlockFile::WriteEntry / add_thumbnail)
Ref: picasa3.exe @ albumdata_date.pmp (OLE Automation Date)
"""

from __future__ import annotations
import io
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image, ImageOps, ExifTags
from PySide6.QtCore import QThread, Signal

Image.MAX_IMAGE_PIXELS = None

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexRecord


SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".png", ".bmp", ".gif",
    ".tif", ".tiff", ".webp", ".psd"
}

EXTENSION_TYPE_MAP = {
    ".jpg": 2,
    ".jpeg": 2,
    ".jpe": 2,
    ".bmp": 6,
    ".psd": 7,
    ".tif": 13,
    ".tiff": 13,
    ".webp": 31,
    ".png": 31,
    ".gif": 31,
}

OLE_BASE_DATETIME = datetime(1899, 12, 30)


def datetime_to_ole(dt: datetime) -> float:
    """Convertit un objet datetime en date OLE Automation (jours depuis le 30/12/1899)."""
    delta = dt - OLE_BASE_DATETIME
    return delta.days + (delta.seconds + delta.microseconds / 1e6) / 86400.0


def extract_image_metadata_and_thumb(
    file_path: str, max_thumb_size: int = 256
) -> Optional[Tuple[bytes, int, int, float]]:
    """
    Ouvre l'image, oriente selon l'EXIF, extrait les dimensions,
    calcule la date OLE, et génère le buffer JPEG de la vignette.
    """
    try:
        with Image.open(file_path) as raw_img:
            # 1. Orientation automatique selon les balises EXIF et conversion propre de la transparence
            if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                raw_img = raw_img.convert("RGBA")
            try:
                img = ImageOps.exif_transpose(raw_img)
            except Exception:
                img = raw_img

            orig_w, orig_h = img.size

            # 2. Extraction de la date (EXIF DateTimeOriginal ou date fichier)
            ole_date = 0.0
            exif_data = img.getexif()
            date_found = False

            if exif_data:
                # 0x9003 = DateTimeOriginal, 0x0132 = DateTime
                for tag_id in (0x9003, 0x0132):
                    date_str = exif_data.get(tag_id)
                    if date_str and isinstance(date_str, str):
                        try:
                            # Format standard EXIF : 'YYYY:MM:DD HH:MM:SS'
                            dt = datetime.strptime(date_str.strip()[:19], "%Y:%m:%d %H:%M:%S")
                            ole_date = datetime_to_ole(dt)
                            date_found = True
                            break
                        except Exception:
                            pass

            if not date_found:
                try:
                    mtime = os.path.getmtime(file_path)
                    dt = datetime.fromtimestamp(mtime)
                    ole_date = datetime_to_ole(dt)
                except Exception:
                    ole_date = 0.0

            # 3. Génération de la miniature (JPEG 256x256 conservant le ratio)
            thumb_img = img.copy()
            thumb_img.thumbnail((max_thumb_size, max_thumb_size), Image.Resampling.LANCZOS)
            if thumb_img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", thumb_img.size, (255, 255, 255))
                bg.paste(thumb_img, mask=thumb_img.split()[3])
                thumb_img = bg
            elif thumb_img.mode != "RGB":
                thumb_img = thumb_img.convert("RGB")

            buf = io.BytesIO()
            thumb_img.save(buf, format="JPEG", quality=85, optimize=True)
            jpeg_bytes = buf.getvalue()

            return (jpeg_bytes, orig_w, orig_h, ole_date)
    except Exception:
        return None


class PicasaDirScanner:
    """
    Scrutateur de dossiers analysant les répertoires et synchronisant
    la base de données Picasa avec les fichiers réels du disque.
    """

    def __init__(self, db: PicasaDatabase):
        self.db = db

    def scan_folder_for_media(self, folder_path: str, recursive: bool = True) -> List[str]:
        """Énumère l'ensemble des fichiers média d'un répertoire."""
        results: List[str] = []
        p = Path(folder_path)
        if not p.exists() or not p.is_dir():
            return results

        pattern = "**/*" if recursive else "*"
        try:
            for item in p.glob(pattern):
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                    results.append(str(item.resolve()))
        except Exception:
            pass

        return results

    def find_unindexed_files(self, folder_paths: List[str]) -> List[str]:
        """
        Compare les fichiers du disque avec ceux déjà enregistrés dans thumbindex.db
        et renvoie la liste des nouveaux fichiers à indexer.
        """
        # Cartographier l'existant : (folder_norm, filename_lower)
        indexed: Set[Tuple[str, str]] = set()
        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}

        for r in self.db.index:
            if r.type != 1:
                fpath = folders_map.get(r.parent_idx, "")
                norm_f = fpath.replace("/", "\\").rstrip("\\").lower()
                indexed.add((norm_f, r.path.lower()))

        unindexed: List[str] = []
        for folder in folder_paths:
            found_files = self.scan_folder_for_media(folder, recursive=True)
            for file_path in found_files:
                parent_dir = os.path.dirname(file_path).replace("/", "\\").rstrip("\\").lower()
                fname = os.path.basename(file_path).lower()
                if (parent_dir, fname) not in indexed:
                    unindexed.append(file_path)

        return unindexed

    def index_file(self, file_path: str) -> Optional[int]:
        """
        Génère la vignette et insère l'enregistrement dans la base Picasa.
        """
        ext = os.path.splitext(file_path)[1].lower()
        media_type = EXTENSION_TYPE_MAP.get(ext, 2)
        folder_path = os.path.dirname(file_path) + "\\"
        filename = os.path.basename(file_path)

        meta = extract_image_metadata_and_thumb(file_path)
        if not meta:
            return None

        jpeg_bytes, w, h, ole_date = meta
        file_size = os.path.getsize(file_path)
        mtime = int(os.path.getmtime(file_path))

        # 1. Enregistrement thumbindex.db
        record_idx = self.db.add_media_record(
            folder_path=folder_path,
            filename=filename,
            file_size=file_size,
            mtime=mtime,
            media_type=media_type,
        )

        # 2. Miniature thumbs_0.db et thumbs_index.db
        self.db.add_thumbnail(record_idx, jpeg_bytes, size="small")

        # 3. Colonnes PMP (imagedata_width, imagedata_height, imagedata_tagdate)
        if "imagedata_width" in self.db.pmps:
            while len(self.db.pmps["imagedata_width"].records) <= record_idx:
                self.db.pmps["imagedata_width"].records.append(0)
            self.db.pmps["imagedata_width"].records[record_idx] = w

        if "imagedata_height" in self.db.pmps:
            while len(self.db.pmps["imagedata_height"].records) <= record_idx:
                self.db.pmps["imagedata_height"].records.append(0)
            self.db.pmps["imagedata_height"].records[record_idx] = h

        if "imagedata_tagdate" in self.db.pmps and ole_date > 0.0:
            while len(self.db.pmps["imagedata_tagdate"].records) <= record_idx:
                self.db.pmps["imagedata_tagdate"].records.append(0.0)
            self.db.pmps["imagedata_tagdate"].records[record_idx] = ole_date

        return record_idx


class BackgroundScanWorker(QThread):
    """
    Thread de travail en arrière-plan pour l'auto-indexation et
    la génération de miniatures sans bloquer l'interface graphique.
    """
    progress = Signal(int, int, str)  # (current, total, filename)
    file_indexed = Signal(str, str)   # (folder_path, filename)
    finished = Signal(int)            # (total_added)

    def __init__(self, db: PicasaDatabase, folder_paths: List[str], parent=None):
        super().__init__(parent)
        self.db = db
        self.folder_paths = folder_paths
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        scanner = PicasaDirScanner(self.db)
        to_index = scanner.find_unindexed_files(self.folder_paths)

        total = len(to_index)
        added = 0

        for i, fpath in enumerate(to_index):
            if self._is_cancelled:
                break

            fname = os.path.basename(fpath)
            self.progress.emit(i + 1, total, fname)

            idx = scanner.index_file(fpath)
            if idx is not None:
                added += 1
                self.file_indexed.emit(os.path.dirname(fpath), fname)

        # Sauvegarder les modifications atomiquement sur disque
        if added > 0:
            try:
                self.db.save_database()
            except Exception:
                pass

        self.finished.emit(added)
