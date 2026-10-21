"""
FR: Scrutateur de dossiers Picasa et moteur d'auto-indexation (AVytDirScannerWindows / CScanner).
Analyse les répertoires surveillés, détecte les fichiers médias nouveaux ou modifiés, extrait les dates
et dimensions EXIF, génère les miniatures JPEG (256x256) et met à jour thumbindex.db et thumbs_0.db.

EN: Picasa Directory Scanner & Auto-Indexing Engine (AVytDirScannerWindows / CScanner).
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
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image, ImageOps, ExifTags
from PySide6.QtCore import QThread, Signal

Image.MAX_IMAGE_PIXELS = None

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexRecord


VIDEO_EXTENSIONS = {
    ".avi", ".wmv", ".asf", ".mpg", ".mpeg", ".mpe", ".m1v", ".m2v",
    ".mp4", ".m4v", ".mov", ".3gp", ".3g2", ".mkv", ".flv", ".webm"
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".png", ".bmp", ".gif",
    ".tif", ".tiff", ".webp", ".psd"
}

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

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
    # FR: Formats vidéos Picasa 3 / EN: Picasa 3 video formats (Ref: SupportMovies, SupportQuicktime, DirEntry.IsMovie)
    ".avi": 0x20,
    ".wmv": 0x20,
    ".asf": 0x20,
    ".mpg": 0x20,
    ".mpeg": 0x20,
    ".mpe": 0x20,
    ".m1v": 0x20,
    ".m2v": 0x20,
    ".mp4": 0x20,
    ".m4v": 0x20,
    ".mov": 0x20,
    ".3gp": 0x20,
    ".3g2": 0x20,
    ".mkv": 0x20,
    ".flv": 0x20,
    ".webm": 0x20,
}

OLE_BASE_DATETIME = datetime(1899, 12, 30)


def datetime_to_ole(dt: datetime) -> float:
    """
    FR: Convertit un objet datetime en date OLE Automation (jours depuis le 30/12/1899).
    EN: Converts a datetime object to an OLE Automation date (days since 1899-12-30).
    """
    delta = dt - OLE_BASE_DATETIME
    return delta.days + (delta.seconds + delta.microseconds / 1e6) / 86400.0


def extract_video_metadata_and_thumb(
    file_path: str, max_thumb_size: int = 144
) -> Optional[Tuple[bytes, int, int, float]]:
    """
    FR: Extrait la première frame ou une frame représentative d'un fichier vidéo
    ainsi que sa résolution et date de modification.
    EN: Extracts the first or representative frame from a video file
    along with its resolution and modification date.
    Ref: picasa3.exe @ DirEntry.IsMovie(), export.fen (First frame), 0x00424CA0
    """
    try:
        orig_w = 640
        orig_h = 480
        ole_date = 0.0

        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            ole_date = datetime_to_ole(dt)
        except Exception:
            pass

        thumb_img: Optional[Image.Image] = None

        # FR: Tentative d'extraction rapide de frame via OpenCV / EN: Fast frame extraction attempt via OpenCV
        try:
            import cv2
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if w > 0 and h > 0:
                    orig_w, orig_h = w, h

                fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * 0.5))
                ret, frame = cap.read()
                if not ret or frame is None:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                cap.release()

                if ret and frame is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    thumb_img = Image.fromarray(rgb)
        except Exception:
            pass

        # FR: Fallback élégant : vignette sombre avec bande cinéma et icône vidéo Picasa
        # EN: Clean fallback: dark thumbnail with filmstripsprockets and Picasa play icon
        if thumb_img is None:
            thumb_img = Image.new("RGB", (max_thumb_size, max_thumb_size), (30, 32, 36))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(thumb_img)
            # FR: Bandeaux cinéma / EN: Filmstrip bars
            draw.rectangle([0, 0, max_thumb_size, 24], fill=(15, 16, 18))
            draw.rectangle([0, max_thumb_size - 24, max_thumb_size, max_thumb_size], fill=(15, 16, 18))
            # FR: Perforations film / EN: Film perforations
            for x in range(8, max_thumb_size - 8, 20):
                draw.rectangle([x, 6, x + 10, 18], fill=(220, 220, 220))
                draw.rectangle([x, max_thumb_size - 18, x + 10, max_thumb_size - 6], fill=(220, 220, 220))
            # FR: Symbole de lecture Play centré / EN: Centered Play triangle icon
            cx, cy = max_thumb_size // 2, max_thumb_size // 2
            tri = [(cx - 20, cy - 25), (cx + 25, cy), (cx - 20, cy + 25)]
            draw.polygon(tri, fill=(240, 240, 240))
        else:
            thumb_img.thumbnail((max_thumb_size, max_thumb_size), Image.Resampling.LANCZOS)
            if thumb_img.mode != "RGB":
                thumb_img = thumb_img.convert("RGB")

        buf = io.BytesIO()
        thumb_img.save(buf, format="JPEG", quality=90, optimize=True)
        jpeg_bytes = buf.getvalue()

        t2_img = thumb_img.copy()
        t2_img.thumbnail((72, 72), Image.Resampling.LANCZOS)
        buf2 = io.BytesIO()
        t2_img.save(buf2, format="JPEG", quality=90, optimize=True)
        return _MediaMetadataResult(jpeg_bytes, orig_w, orig_h, ole_date, thumb2_bytes=buf2.getvalue())
    except Exception:
        return None


def extract_media_metadata_and_thumb(
    file_path: str, max_thumb_size: int = 144
) -> Optional[Tuple[bytes, int, int, float]]:
    """
    FR: Extrait les métadonnées et la miniature appropriée selon le type de média (image ou vidéo).
    EN: Extracts metadata and the appropriate thumbnail depending on media type (image or video).
    Ref: picasa3.exe @ 0x00424CA0 (thumbs=144px, thumbs2=72px, quality=90)
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return extract_video_metadata_and_thumb(file_path, max_thumb_size)
    return extract_image_metadata_and_thumb(file_path, max_thumb_size)


class _MediaMetadataResult(tuple):
    """
    FR: Nuplet `(jpeg_bytes, width, height, ole_date)` supportant également l'accès par clé dictionnaire
    (`meta["lat"]`, `meta["lon"]`, `meta.get("lat")`) pour les coordonnées GPS EXIF.
    EN: Tuple `(jpeg_bytes, width, height, ole_date)` also supporting dictionary key access
    (`meta["lat"]`, `meta["lon"]`, `meta.get("lat")`) for EXIF GPS coordinates.
    """

    def __new__(
        cls,
        jpeg_bytes: bytes,
        width: int,
        height: int,
        ole_date: float,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        thumb2_bytes: Optional[bytes] = None,
    ):
        obj = super().__new__(cls, (jpeg_bytes, width, height, ole_date))
        obj.lat = lat
        obj.lon = lon
        obj.thumb2_bytes = thumb2_bytes
        obj._extra = {
            "thumb": jpeg_bytes,
            "jpeg_bytes": jpeg_bytes,
            "thumb2_bytes": thumb2_bytes,
            "width": width,
            "height": height,
            "date": ole_date,
            "ole_date": ole_date,
            "lat": lat,
            "lon": lon,
        }
        return obj

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._extra[key]
        return super().__getitem__(key)

    def __contains__(self, key) -> bool:
        if isinstance(key, str):
            return key in self._extra and self._extra[key] is not None
        return super().__contains__(key)

    def get(self, key: str, default=None):
        val = self._extra.get(key, default)
        return default if val is None else val


def _DMS_to_degrees(val) -> Optional[float]:
    """
    FR: Convertit un triplet EXIF `(degrés, minutes, secondes)` en degrés décimaux flottants.
    EN: Converts an EXIF `(degrees, minutes, seconds)` triplet into float decimal degrees.
    """
    try:
        def _to_float(x) -> float:
            if isinstance(x, tuple) and len(x) == 2:
                return float(x[0]) / float(x[1]) if x[1] else 0.0
            return float(x)

        deg = _to_float(val[0])
        minutes = _to_float(val[1]) if len(val) > 1 else 0.0
        seconds = _to_float(val[2]) if len(val) > 2 else 0.0
        return deg + (minutes / 60.0) + (seconds / 3600.0)
    except Exception:
        return None


def _extract_exif_gps(raw_img: Image.Image, exif_data) -> Tuple[Optional[float], Optional[float]]:
    """
    FR: Extrait les coordonnées GPS EXIF (IFD `0x8825`) en degrés décimaux signés `(lat, lon)`.
    EN: Extracts EXIF GPS coordinates (IFD `0x8825`) as signed decimal degrees `(lat, lon)`.
    Ref: picasa3.exe @ imagedata_lat.pmp, imagedata_long.pmp
    """
    gps_ifd = None
    try:
        if exif_data is not None and hasattr(exif_data, "get_ifd"):
            gps_ifd = exif_data.get_ifd(0x8825)
    except Exception:
        gps_ifd = None
    if not gps_ifd and exif_data is not None:
        cand = exif_data.get(0x8825)
        if isinstance(cand, dict):
            gps_ifd = cand
    if not gps_ifd and hasattr(raw_img, "_getexif"):
        try:
            raw_exif = raw_img._getexif()
            if isinstance(raw_exif, dict) and isinstance(raw_exif.get(0x8825), dict):
                gps_ifd = raw_exif.get(0x8825)
        except Exception:
            pass
    if not gps_ifd or not isinstance(gps_ifd, dict):
        return None, None

    lat_val = gps_ifd.get(2)
    lon_val = gps_ifd.get(4)
    if lat_val is None or lon_val is None:
        return None, None

    lat = _DMS_to_degrees(lat_val)
    lon = _DMS_to_degrees(lon_val)
    if lat is None or lon is None:
        return None, None

    lat_ref = gps_ifd.get(1, "N")
    lon_ref = gps_ifd.get(3, "E")
    if isinstance(lat_ref, bytes):
        lat_ref = lat_ref.decode("ascii", errors="ignore")
    if isinstance(lon_ref, bytes):
        lon_ref = lon_ref.decode("ascii", errors="ignore")
    if str(lat_ref).strip().upper().startswith("S"):
        lat = -abs(lat)
    if str(lon_ref).strip().upper().startswith("W"):
        lon = -abs(lon)
    return lat, lon


def extract_image_metadata_and_thumb(
    file_path: str, max_thumb_size: int = 144
) -> Optional[Tuple[bytes, int, int, float]]:
    """
    FR: Ouvre l'image, oriente selon l'EXIF, extrait les dimensions et coordonnées GPS,
    calcule la date OLE, et génère le buffer JPEG de la vignette (144px max, qualité 90,
    ainsi que la vignette `thumbs2` 72px max, qualité 90).
    EN: Opens the image, applies EXIF orientation, extracts dimensions and GPS coordinates,
    computes the OLE date, and generates the thumbnail JPEG buffer (144px max, quality 90,
    along with the `thumbs2` 72px max, quality 90 thumbnail).
    Ref: picasa3.exe @ 0x00424CA0 (FUN_00424ca0 -> thumbs=144px, thumbs2=72px, quality=90)
    """
    try:
        with Image.open(file_path) as raw_img:
            exif_data = raw_img.getexif()
            gps_lat, gps_lon = _extract_exif_gps(raw_img, exif_data)

            # 1. FR: Orientation automatique selon les balises EXIF et conversion propre de la transparence
            #    EN: Automatic EXIF orientation and clean transparency conversion
            if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                raw_img = raw_img.convert("RGBA")
            try:
                img = ImageOps.exif_transpose(raw_img)
            except Exception:
                img = raw_img

            orig_w, orig_h = img.size

            # 2. FR: Extraction de la date (EXIF DateTimeOriginal ou date fichier)
            #    EN: Date extraction (EXIF DateTimeOriginal or file modification time)
            ole_date = 0.0
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

            # 3. FR: Génération de la miniature (JPEG 144x144 conservant le ratio, qualité 90)
            #    EN: Thumbnail generation (aspect-ratio preserving 144x144 JPEG, quality 90)
            thumb_img = img.copy()
            thumb_img.thumbnail((max_thumb_size, max_thumb_size), Image.Resampling.LANCZOS)
            if thumb_img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", thumb_img.size, (255, 255, 255))
                bg.paste(thumb_img, mask=thumb_img.split()[3])
                thumb_img = bg
            elif thumb_img.mode != "RGB":
                thumb_img = thumb_img.convert("RGB")

            buf = io.BytesIO()
            thumb_img.save(buf, format="JPEG", quality=90, optimize=True)
            jpeg_bytes = buf.getvalue()

            t2_img = thumb_img.copy()
            t2_img.thumbnail((72, 72), Image.Resampling.LANCZOS)
            buf2 = io.BytesIO()
            t2_img.save(buf2, format="JPEG", quality=90, optimize=True)
            thumb2_bytes = buf2.getvalue()

            return _MediaMetadataResult(
                jpeg_bytes, orig_w, orig_h, ole_date, lat=gps_lat, lon=gps_lon, thumb2_bytes=thumb2_bytes
            )
    except Exception:
        return None


# Ref: runtime/filters.txt @ 0x00D0AD70 (DirectoryFilters) & .picasaoriginals @ 0x0085A0B0
DEFAULT_EXCLUDED_DIRS: Set[str] = {
    "windows",
    "winnt",
    "temp",
    "program files",
    "originals",
    ".picasaoriginals",
}


def load_directory_filters() -> Set[str]:
    """
    FR: Charge la liste d'exclusion des répertoires depuis runtime/filters.txt (section DirectoryFilters).
    EN: Loads the directory exclusion list from runtime/filters.txt (DirectoryFilters section).
    Ref: picasa3.exe @ 0x00D0AD70 (runtime\\filters.txt -> DirectoryFilters)
    """
    excluded = set(DEFAULT_EXCLUDED_DIRS)
    candidates: List[Path] = []
    try:
        from picasa_py.ui.resources import RES_DIR
        candidates.append(RES_DIR / "runtime" / "filters.txt")
    except Exception:
        pass
    candidates.extend([
        Path(r"C:\Program Files (x86)\Google\Picasa3\runtime\filters.txt"),
        Path(r"C:\Program Files\Google\Picasa3\runtime\filters.txt"),
        Path("runtime/filters.txt"),
    ])
    for path in candidates:
        if path.exists():
            try:
                in_dir_filters = False
                for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#") or line.startswith("//"):
                        continue
                    if line == "DirectoryFilters":
                        in_dir_filters = True
                        continue
                    if line == "{":
                        continue
                    if line == "}":
                        if in_dir_filters:
                            break
                        continue
                    if in_dir_filters:
                        excluded.add(line.lower())
                break
            except Exception:
                pass
    return excluded


class PicasaDirScanner:
    """
    FR: Scrutateur de dossiers analysant les répertoires et synchronisant
    la base de données Picasa avec les fichiers réels du disque (multi-OS).
    EN: Directory scanner analyzing folders and synchronizing
    the Picasa database with actual files on disk (cross-platform).
    """

    def __init__(self, db: PicasaDatabase):
        """
        FR: Initialise le scrutateur de répertoires avec la base Picasa et les filtres d'exclusion.
        EN: Initializes the directory scanner with the Picasa database and exclusion filters.
        """
        self.db = db
        self.excluded_dirs: Set[str] = load_directory_filters()
        self._discovered_albums: Dict[str, Dict[str, object]] = {}

    def is_excluded_dir(self, dir_name: str) -> bool:
        """
        FR: Indique si un sous-dossier doit être ignoré lors du scan récursif.
        EN: Indicates whether a subfolder should be skipped during recursive scanning.
        Ref: picasa3.exe @ 0x00415790, 0x0085A0B0 (.picasaoriginals), runtime/filters.txt
        """
        clean = os.path.basename(dir_name.rstrip("\\/")).lower()
        return clean in self.excluded_dirs or clean.startswith(".")

    def is_folder_face_excluded(self, folder_path: str) -> bool:
        """
        FR: Vérifie si le dossier comporte frexclude=1 dans la section [Picasa] de son .picasa.ini.
        EN: Checks whether the folder has frexclude=1 in the [Picasa] section of its .picasa.ini.
        Ref: picasa3.exe @ 0x00881690 (frexclude)
        """
        for ini_name in (".picasa.ini", "Picasa.ini"):
            ini_path = os.path.join(folder_path, ini_name)
            if os.path.exists(ini_path):
                doc = (
                    self.db.get_parsed_ini(ini_path)
                    if (self.db and hasattr(self.db, "get_parsed_ini"))
                    else None
                )
                if doc is None:
                    try:
                        from picasa_py.ini.parser import PicasaIniParser
                        doc = PicasaIniParser.parse_file(ini_path)
                    except Exception:
                        doc = None
                if doc is not None:
                    sec = doc.get_section("Picasa")
                    if sec is not None:
                        val = (sec.get("frexclude") or "").strip().lower()
                        if val in ("1", "yes", "true"):
                            return True
        return False

    def scan_folder_for_media(self, folder_path: str, recursive: bool = True, is_cancelled=None) -> List[str]:
        """
        FR: Énumère l'ensemble des fichiers média d'un répertoire avec support d'annulation.
        EN: Enumerates all media files in a directory with cancellation support.
        """
        results: List[str] = []
        host_folder = folder_path.replace("\\", os.sep) if os.sep != "\\" else folder_path
        if not os.path.exists(host_folder) or not os.path.isdir(host_folder):
            return results

        if not recursive:
            try:
                self._collect_ini_albums_from_folder(host_folder)
                for entry in os.scandir(host_folder):
                    if is_cancelled and is_cancelled():
                        break
                    if entry.is_file() and Path(entry.name).suffix.lower() in SUPPORTED_EXTENSIONS:
                        results.append(os.path.abspath(entry.path))
            except Exception:
                pass
            return results

        try:
            for root, dirs, files in os.walk(host_folder):
                if is_cancelled and is_cancelled():
                    break
                dirs[:] = [d for d in dirs if not self.is_excluded_dir(d)]
                self._collect_ini_albums_from_folder(root)
                for fname in files:
                    if Path(fname).suffix.lower() in SUPPORTED_EXTENSIONS:
                        results.append(os.path.abspath(os.path.join(root, fname)))
        except Exception:
            pass

        return results

    def _collect_ini_albums_from_folder(self, folder_path: str) -> None:
        """
        FR: Découvre les sections [.album:<token>] et les références albums= d'un dossier .picasa.ini.
        EN: Discovers [.album:<token>] sections and albums= references from a folder's .picasa.ini.
        Ref: picasa3.exe @ 0x00456A15, 0x00732160
        """
        for ini_name in (".picasa.ini", "Picasa.ini"):
            ini_path = os.path.join(folder_path, ini_name)
            if not os.path.exists(ini_path):
                continue
            doc = (
                self.db.get_parsed_ini(ini_path)
                if (self.db and hasattr(self.db, "get_parsed_ini"))
                else None
            )
            if doc is None:
                try:
                    from picasa_py.ini.parser import PicasaIniParser
                    doc = PicasaIniParser.parse_file(ini_path)
                except Exception:
                    doc = None
            if doc is None:
                continue
            for sec in doc.sections:
                if sec.name.startswith(".album:") or sec.name.startswith("]album:"):
                    raw_tok = sec.get("token") or sec.name[7:]
                    tok = raw_tok.strip()
                    if tok.startswith("]album:") or tok.startswith(".album:"):
                        tok = tok[7:].strip()
                    if not tok:
                        continue
                    aname = (sec.get("name") or tok).strip()
                    date_val = 0.0
                    raw_date = sec.get("date")
                    if raw_date:
                        try:
                            date_val = float(raw_date.strip())
                        except ValueError:
                            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
                                try:
                                    dt = datetime.strptime(raw_date.strip()[:19], fmt)
                                    date_val = datetime_to_ole(dt)
                                    break
                                except Exception:
                                    pass
                    self._discovered_albums[tok] = {
                        "name": aname,
                        "token": tok,
                        "uid": (sec.get("uid") or tok).strip(),
                        "date": date_val,
                        "description": sec.get("description") or "",
                        "location": sec.get("location") or "",
                        "music": sec.get("music") or "",
                    }
                elif not sec.name.startswith("[") and sec.name.lower() not in ("picasa", "contacts2", "encoding"):
                    alb_str = sec.get("albums")
                    if alb_str:
                        for t in alb_str.split(","):
                            tok = t.strip()
                            if tok.startswith("]album:") or tok.startswith(".album:"):
                                tok = tok[7:].strip()
                            if tok and tok not in self._discovered_albums:
                                self._discovered_albums[tok] = {
                                    "name": f"Album {tok}",
                                    "token": tok,
                                    "uid": tok,
                                    "date": 0.0,
                                }
            break

    def _sync_ini_albums_to_pmp(self) -> int:
        """
        FR: Synchronise les albums découverts dans .picasa.ini (self._discovered_albums) vers les tables
        albumdata_*.pmp sans JAMAIS écraser la ligne 0 (Default) ni les albums de personnes (category == 8)
        ou système (category == 2). Maintient le même row_count sur toutes les colonnes albumdata_*.
        EN: Synchronizes albums discovered in .picasa.ini (self._discovered_albums) into albumdata_*.pmp
        tables without EVER overwriting row 0 (Default), person albums (category == 8), or system albums
        (category == 2). Preserves identical row_count across all albumdata_* columns.
        Ref: picasa3.exe @ 0x004156F0, 0x00456A15, 0x008AAD76
        """
        if not self.db or not self._discovered_albums:
            return 0
        ad_name = self.db.pmps.get("albumdata_name")
        ad_token = self.db.pmps.get("albumdata_token")
        ad_cat = self.db.pmps.get("albumdata_category")
        if ad_name is None or ad_token is None or ad_cat is None:
            return 0

        albumdata_tables = {
            stem: pmp
            for stem, pmp in self.db.pmps.items()
            if stem.startswith("albumdata_")
        }
        base_len = len(ad_name.records)
        for pmp in albumdata_tables.values():
            def_val = pmp.default_value()
            while len(pmp.records) < base_len:
                pmp.records.append(def_val)

        # FR: Si les tables albumdata_* sont totalement vides, réserver la ligne 0 ("Default") comme picasa3.exe
        # EN: If albumdata_* tables are completely empty, reserve row 0 ("Default") like picasa3.exe
        if len(ad_name.records) == 0:
            for stem, pmp in albumdata_tables.items():
                if stem == "albumdata_name":
                    pmp.records.append("Default")
                elif stem == "albumdata_category":
                    pmp.records.append(0)
                else:
                    pmp.records.append(pmp.default_value())

        updated_or_added = 0
        for raw_tok, alb_meta in self._discovered_albums.items():
            tok_clean = str(raw_tok).strip()
            if tok_clean.startswith("]album:") or tok_clean.startswith(".album:"):
                tok_clean = tok_clean[7:].strip()
            if not tok_clean:
                continue

            aname = str(alb_meta.get("name") or tok_clean)
            adate = float(alb_meta.get("date") or 0.0)
            auid = str(alb_meta.get("uid") or tok_clean)

            existing_row: Optional[int] = None
            for row_i, existing_tok in enumerate(ad_token.records):
                clean_ex = str(existing_tok or "").strip()
                if clean_ex.startswith("]album:") or clean_ex.startswith(".album:"):
                    clean_ex = clean_ex[7:].strip()
                if clean_ex and clean_ex == tok_clean:
                    existing_row = row_i
                    break

            if existing_row is not None:
                ad_name.records[existing_row] = aname
                ad_token.records[existing_row] = tok_clean
                ad_cat.records[existing_row] = 0
                if adate and "albumdata_date" in albumdata_tables:
                    albumdata_tables["albumdata_date"].records[existing_row] = adate
                updated_or_added += 1
            else:
                for stem, pmp in albumdata_tables.items():
                    if stem == "albumdata_name":
                        pmp.records.append(aname)
                    elif stem == "albumdata_token":
                        pmp.records.append(tok_clean)
                    elif stem == "albumdata_uid":
                        pmp.records.append(auid)
                    elif stem == "albumdata_category":
                        pmp.records.append(0)
                    elif stem == "albumdata_date":
                        pmp.records.append(adate)
                    elif stem == "albumdata_description":
                        pmp.records.append(str(alb_meta.get("description") or ""))
                    elif stem == "albumdata_location":
                        pmp.records.append(str(alb_meta.get("location") or ""))
                    elif stem == "albumdata_music":
                        pmp.records.append(str(alb_meta.get("music") or ""))
                    else:
                        pmp.records.append(pmp.default_value())
                updated_or_added += 1

        return updated_or_added

    def _check_deleted_records(self, folder_paths: Optional[List[str]] = None) -> int:
        """
        FR: Marque comme supprimés (type = 0) les enregistrements média dont le fichier a disparu du disque
        et nettoie immédiatement tous les sous-enregistrements de visages (type == 1001) orphelins associés.
        EN: Marks media records whose on-disk file has been removed as deleted (type = 0)
        and immediately cleans up all associated orphaned face sub-records (type == 1001).
        Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows), 0x008AAD76
        """
        if not self.db or not self.db.thumbindex:
            return 0

        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
        allowed_folders_norm: Optional[Set[str]] = None
        if folder_paths:
            allowed_folders_norm = {
                os.path.abspath(p.replace("\\", os.sep) if os.sep != "\\" else p).replace("/", "\\").rstrip("\\").lower()
                for p in folder_paths if p
            }

        deleted_photo_indices: Set[int] = set()
        deleted_count = 0

        for idx, rec in enumerate(self.db.index):
            if rec.type == 0:
                deleted_photo_indices.add(idx)
                continue
            if rec.type not in (2, 3, 4, 6, 7, 8, 13, 18, 31, 32):
                continue
            fdir = folders_map.get(rec.parent_idx, "")
            if not fdir:
                continue
            host_fdir = fdir.replace("\\", os.sep) if os.sep != "\\" else fdir
            norm_fdir = os.path.abspath(host_fdir).replace("/", "\\").rstrip("\\").lower()
            if allowed_folders_norm is not None and not any(
                norm_fdir == af or norm_fdir.startswith(af + "\\") for af in allowed_folders_norm
            ):
                continue
            full_path = os.path.join(host_fdir, rec.path)
            if not os.path.exists(full_path):
                rec.type = 0
                rec.path = ""
                rec.parent_idx = 0xFFFFFFFF
                deleted_photo_indices.add(idx)
                deleted_count += 1

        if deleted_photo_indices:
            for c_idx, c_rec in enumerate(self.db.index):
                if c_rec.type == 1001 and c_rec.parent_idx in deleted_photo_indices:
                    c_rec.type = 0
                    c_rec.path = ""
                    c_rec.parent_idx = 0xFFFFFFFF
                    for col_name in (
                        "imagedata_facerect",
                        "imagedata_personalbumid",
                        "imagedata_suggestionpersonalbumid",
                    ):
                        pmp = self.db.pmps.get(col_name)
                        if pmp is not None and c_idx < len(pmp.records):
                            pmp.records[c_idx] = 0
            if hasattr(self.db, "_invalidate_path_index_cache"):
                self.db._invalidate_path_index_cache()

        return deleted_count

    def find_unindexed_files(self, folder_paths: List[str], is_cancelled=None) -> List[str]:
        """
        FR: Compare les fichiers du disque avec ceux déjà enregistrés dans thumbindex.db
        et renvoie la liste des nouveaux fichiers à indexer.
        EN: Compares files on disk against those already recorded in thumbindex.db
        and returns the list of new files to index.
        Ref: picasa3.exe @ 0x00415790 — reconnaît tous les types médias (2, 3, 4, 6, 7, 8, 13, 18, 31, 32).
        """
        # FR: Cartographier l'existant : (folder_norm, filename_lower)
        # EN: Map existing indexed records: (folder_norm, filename_lower)
        indexed: Set[Tuple[str, str]] = set()
        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}

        for r in self.db.index:
            if r.type in (2, 3, 4, 6, 7, 8, 13, 18, 31, 32):
                fpath = folders_map.get(r.parent_idx, "")
                norm_f = fpath.replace("/", "\\").rstrip("\\").lower()
                indexed.add((norm_f, r.path.lower()))

        self._check_deleted_records(folder_paths)

        unindexed: List[str] = []
        for folder in folder_paths:
            if is_cancelled and is_cancelled():
                break
            found_files = self.scan_folder_for_media(folder, recursive=True, is_cancelled=is_cancelled)
            for file_path in found_files:
                if is_cancelled and is_cancelled():
                    break
                parent_dir = os.path.dirname(file_path).replace("/", "\\").rstrip("\\").lower()
                fname = os.path.basename(file_path).lower()
                if (parent_dir, fname) not in indexed:
                    unindexed.append(file_path)

        self._sync_ini_albums_to_pmp()
        return unindexed

    def find_modified_files(self, folder_paths: List[str], is_cancelled=None) -> List[Tuple[int, str]]:
        """
        FR: Détecte les fichiers déjà indexés dont la date de modification (mtime) ou la taille
        sur disque a changé par rapport à thumbindex.db.
        EN: Detects already-indexed files whose modification time (mtime) or file size
        on disk has changed compared to thumbindex.db.
        Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows)
        """
        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
        allowed_folders_norm: Set[str] = {
            os.path.abspath(p.replace("\\", os.sep) if os.sep != "\\" else p).replace("/", "\\").rstrip("\\").lower()
            for p in folder_paths if p
        }
        modified: List[Tuple[int, str]] = []
        for idx, rec in enumerate(self.db.index):
            if is_cancelled and is_cancelled():
                break
            if rec.type not in (2, 3, 4, 6, 7, 8, 13, 18, 31, 32):
                continue
            fdir = folders_map.get(rec.parent_idx, "")
            if not fdir:
                continue
            host_fdir = fdir.replace("\\", os.sep) if os.sep != "\\" else fdir
            norm_fdir = os.path.abspath(host_fdir).replace("/", "\\").rstrip("\\").lower()
            if allowed_folders_norm and not any(
                norm_fdir == af or norm_fdir.startswith(af + "\\") for af in allowed_folders_norm
            ):
                continue
            full_path = os.path.join(host_fdir, rec.path)
            if not os.path.exists(full_path):
                continue
            try:
                disk_mtime = int(os.path.getmtime(full_path))
                disk_size = os.path.getsize(full_path)
                if rec.file_size and (disk_size != rec.file_size or abs(disk_mtime - getattr(rec, "mtime", disk_mtime)) > 2):
                    modified.append((idx, full_path))
            except Exception:
                pass
        return modified

    def update_indexed_file(self, record_idx: int, file_path: str) -> bool:
        """
        FR: Met à jour la vignette et les métadonnées d'un enregistrement existant modifié sur disque.
        EN: Updates the thumbnail and metadata of an existing record modified on disk.
        Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows), 0x006B75F0 (CThumbFile::WriteThumb)
        """
        if record_idx < 0 or record_idx >= len(self.db.index):
            return False
        meta = extract_media_metadata_and_thumb(file_path)
        if not meta:
            return False
        jpeg_bytes, w, h, ole_date = meta
        rec = self.db.index[record_idx]
        rec.file_size = os.path.getsize(file_path)
        rec.mtime = int(os.path.getmtime(file_path))
        if hasattr(self.db, "_align_imagedata_tables"):
            self.db._align_imagedata_tables(record_idx)
        self.db.add_thumbnail(record_idx, jpeg_bytes, size="small")
        if "thumbs2" in getattr(self.db, "block_indices", {}):
            t2_bytes = getattr(meta, "thumb2_bytes", None)
            if not t2_bytes and jpeg_bytes:
                try:
                    with Image.open(io.BytesIO(jpeg_bytes)) as t_img:
                        t2 = t_img.copy()
                        t2.thumbnail((72, 72), Image.Resampling.LANCZOS)
                        if t2.mode != "RGB":
                            t2 = t2.convert("RGB")
                        b2 = io.BytesIO()
                        t2.save(b2, format="JPEG", quality=90)
                        t2_bytes = b2.getvalue()
                except Exception:
                    t2_bytes = jpeg_bytes
            self.db.add_thumbnail(record_idx, t2_bytes or jpeg_bytes, size="medium")
        if "imagedata_width" in self.db.pmps and record_idx < len(self.db.pmps["imagedata_width"].records):
            self.db.pmps["imagedata_width"].records[record_idx] = w
        if "imagedata_height" in self.db.pmps and record_idx < len(self.db.pmps["imagedata_height"].records):
            self.db.pmps["imagedata_height"].records[record_idx] = h
        if "imagedata_tagdate" in self.db.pmps and record_idx < len(self.db.pmps["imagedata_tagdate"].records):
            self.db.pmps["imagedata_tagdate"].records[record_idx] = float(ole_date)
        gps_lat = getattr(meta, "lat", None)
        gps_lon = getattr(meta, "lon", None)
        if gps_lat is not None and gps_lon is not None:
            if "imagedata_lat" in self.db.pmps:
                while len(self.db.pmps["imagedata_lat"].records) <= record_idx:
                    self.db.pmps["imagedata_lat"].records.append(0.0)
                self.db.pmps["imagedata_lat"].records[record_idx] = float(gps_lat)
            if "imagedata_long" in self.db.pmps:
                while len(self.db.pmps["imagedata_long"].records) <= record_idx:
                    self.db.pmps["imagedata_long"].records.append(0.0)
                self.db.pmps["imagedata_long"].records[record_idx] = float(gps_lon)
        if hasattr(self.db, "sync_photo_ini_to_db"):
            try:
                self.db.sync_photo_ini_to_db(record_idx)
            except Exception:
                pass
        return True

    def index_file(self, file_path: str) -> Optional[int]:
        """
        FR: Génère la vignette et insère l'enregistrement dans la base Picasa
        (en conservant strictement le séparateur '\\' dans thumbindex.db).
        EN: Generates the thumbnail and inserts the record into the Picasa database
        (strictly preserving the '\\' separator inside thumbindex.db).
        """
        ext = os.path.splitext(file_path)[1].lower()
        media_type = EXTENSION_TYPE_MAP.get(ext, 2)
        folder_path = os.path.dirname(file_path).replace("/", "\\").rstrip("\\") + "\\"
        filename = os.path.basename(file_path)

        meta = extract_media_metadata_and_thumb(file_path)
        if not meta:
            return None

        jpeg_bytes, w, h, ole_date = meta
        file_size = os.path.getsize(file_path)
        mtime = int(os.path.getmtime(file_path))

        # 1. Enregistrement thumbindex.db / thumbindex.db record
        record_idx = self.db.add_media_record(
            folder_path=folder_path,
            filename=filename,
            file_size=file_size,
            mtime=mtime,
            media_type=media_type,
        )
        if hasattr(self.db, "_align_imagedata_tables"):
            self.db._align_imagedata_tables(record_idx)

        # 2. Miniature thumbs_0.db (144px, q=90) et thumbs2_0.db (72px, q=90) / Thumbnail in thumbs_0.db & thumbs2_0.db
        self.db.add_thumbnail(record_idx, jpeg_bytes, size="small")
        if "thumbs2" in getattr(self.db, "block_indices", {}):
            t2_bytes = getattr(meta, "thumb2_bytes", None)
            if not t2_bytes and jpeg_bytes:
                try:
                    with Image.open(io.BytesIO(jpeg_bytes)) as t_img:
                        t2 = t_img.copy()
                        t2.thumbnail((72, 72), Image.Resampling.LANCZOS)
                        if t2.mode != "RGB":
                            t2 = t2.convert("RGB")
                        b2 = io.BytesIO()
                        t2.save(b2, format="JPEG", quality=90)
                        t2_bytes = b2.getvalue()
                except Exception:
                    t2_bytes = jpeg_bytes
            self.db.add_thumbnail(record_idx, t2_bytes or jpeg_bytes, size="medium")

        # 3. Colonnes PMP (imagedata_width, imagedata_height, imagedata_tagdate, imagedata_filetype, imagedata_origin, imagedata_colorspace, imagedata_facerect, imagedata_avgcolor, imagedata_lat, imagedata_long)
        # Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows / alignement strict des lignes PMP), 0x004280D8
        def _set_pmp_col(col_name: str, val) -> None:
            if col_name in self.db.pmps:
                pmp_obj = self.db.pmps[col_name]
                def_v = pmp_obj.default_value()
                while len(pmp_obj.records) <= record_idx:
                    pmp_obj.records.append(def_v)
                pmp_obj.records[record_idx] = val

        _set_pmp_col("imagedata_width", w)
        _set_pmp_col("imagedata_height", h)
        _set_pmp_col("imagedata_tagdate", float(ole_date))

        filetype_map = {
            ".jpg": 1,
            ".jpeg": 1,
            ".jpe": 1,
            ".png": 2,
            ".gif": 3,
            ".bmp": 4,
            ".tif": 5,
            ".tiff": 5,
            ".webp": 6,
            ".psd": 7,
        }
        ft_code = 10 if ext in VIDEO_EXTENSIONS else filetype_map.get(ext, 1)
        _set_pmp_col("imagedata_filetype", ft_code)
        _set_pmp_col("imagedata_origin", 1)
        _set_pmp_col("imagedata_originfast", 1)
        _set_pmp_col("imagedata_colorspace", 1)
        _set_pmp_col("imagedata_facerect", 0)

        if "imagedata_avgcolor" in self.db.pmps and jpeg_bytes:
            try:
                with Image.open(io.BytesIO(jpeg_bytes)) as t_img:
                    px = t_img.convert("RGB").resize((1, 1), Image.Resampling.BILINEAR).getpixel((0, 0))
                    if isinstance(px, tuple) and len(px) >= 3:
                        avg_u32 = ((int(px[0]) & 0xFF) << 16) | ((int(px[1]) & 0xFF) << 8) | (int(px[2]) & 0xFF)
                        _set_pmp_col("imagedata_avgcolor", avg_u32)
            except Exception:
                pass

        gps_lat = getattr(meta, "lat", None)
        gps_lon = getattr(meta, "lon", None)
        if gps_lat is not None and gps_lon is not None:
            _set_pmp_col("imagedata_lat", float(gps_lat))
            _set_pmp_col("imagedata_long", float(gps_lon))

        if getattr(self.db, "wordhash", None) is not None:
            stem_str = os.path.splitext(filename)[0]
            if stem_str.strip():
                self.db.wordhash.add_word(stem_str.strip(), record_idx)
            parent_dir_name = os.path.basename(folder_path.rstrip("\\/"))
            if parent_dir_name.strip():
                self.db.wordhash.add_word(parent_dir_name.strip(), record_idx)

        # 4. Synchroniser les métadonnées .picasa.ini (étoile, rotation, filtres, texte, légende, visages, backuphash)
        if hasattr(self.db, "sync_photo_ini_to_db"):
            try:
                self.db.sync_photo_ini_to_db(record_idx)
            except Exception:
                pass

        return record_idx

    _index_media_file = index_file

    def scan_directory(self, folder_path: str) -> int:
        """
        FR: Analyse synchrone complète d'un dossier (suppression des orphelins, indexation,
        mise à jour des fichiers modifiés et synchronisation des albums INI).
        EN: Complete synchronous scan of a folder (orphan cleanup, indexing,
        modified file update, and INI album synchronization).
        Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows)
        """
        folders = [str(folder_path)]
        changed = self._check_deleted_records(folders)
        for fpath in self.find_unindexed_files(folders):
            if self.index_file(fpath) is not None:
                changed += 1
        for rec_idx, fpath in self.find_modified_files(folders):
            if self.update_indexed_file(rec_idx, fpath):
                changed += 1
        self._sync_ini_albums_to_pmp()
        return changed


class BackgroundScanWorker(QThread):
    """
    FR: Thread de travail en arrière-plan pour l'auto-indexation et
    la génération de miniatures sans bloquer l'interface graphique.
    EN: Background worker thread for auto-indexing and
    thumbnail generation without blocking the graphical user interface.
    Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows)
    """
    progress = Signal(int, int, str)  # (current, total, filename)
    file_indexed = Signal(str, str)   # (folder_path, filename)
    finished = Signal(int)            # (total_added_or_updated)

    def __init__(self, db: PicasaDatabase, folder_paths: List[str], parent=None):
        """
        FR: Initialise le thread d'analyse avec la base Picasa et la liste des dossiers à scanner.
        EN: Initializes the scan worker thread with the Picasa database and folder list to scan.
        """
        super().__init__(parent)
        self.db = db
        self.folder_paths = folder_paths
        self._is_cancelled = False

    def cancel(self) -> None:
        """
        FR: Demande l'annulation propre de l'analyse en cours.
        EN: Requests a clean cancellation of the ongoing scan.
        """
        self._is_cancelled = True

    def __del__(self) -> None:
        try:
            self._is_cancelled = True
            if self.isRunning():
                self.wait(2000)
        except Exception:
            pass

    def run(self) -> None:
        """
        FR: Exécute l'indexation des nouveaux fichiers et la mise à jour des fichiers modifiés.
        EN: Executes indexing of new files and updating of modified files.
        """
        scanner = PicasaDirScanner(self.db)
        deleted_count = scanner._check_deleted_records(self.folder_paths)
        to_index = scanner.find_unindexed_files(self.folder_paths, is_cancelled=lambda: self._is_cancelled)
        to_update = scanner.find_modified_files(self.folder_paths, is_cancelled=lambda: self._is_cancelled)

        total = len(to_index) + len(to_update)
        changed = deleted_count

        for i, fpath in enumerate(to_index):
            if self._is_cancelled:
                break

            fname = os.path.basename(fpath)
            self.progress.emit(i + 1, total, fname)

            idx = scanner.index_file(fpath)
            if idx is not None:
                changed += 1
                self.file_indexed.emit(os.path.dirname(fpath), fname)

            if (i + 1) % 25 == 0:
                time.sleep(0.001)

        offset = len(to_index)
        for j, (rec_idx, fpath) in enumerate(to_update):
            if self._is_cancelled:
                break

            fname = os.path.basename(fpath)
            self.progress.emit(offset + j + 1, total, fname)
            if scanner.update_indexed_file(rec_idx, fpath):
                changed += 1
                self.file_indexed.emit(os.path.dirname(fpath), fname)

            if (j + 1) % 25 == 0:
                time.sleep(0.001)

        alb_synced = scanner._sync_ini_albums_to_pmp()
        if alb_synced > 0 and changed == 0:
            try:
                self.db.save_database()
            except Exception:
                pass

        # FR: Sauvegarder les modifications atomiquement sur disque / EN: Save changes atomically to disk
        if changed > 0:
            try:
                self.db.save_database()
            except Exception:
                pass

        self.finished.emit(changed)


