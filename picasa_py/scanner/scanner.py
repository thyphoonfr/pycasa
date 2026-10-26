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
import ctypes
import hashlib
import io
import math
import os
import re
import struct
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg*=false")
os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")
os.environ.setdefault("OPENCV_LOG_LEVEL", "OFF")

from PIL import Image, ImageOps, ExifTags
from PySide6.QtCore import QThread, Signal

Image.MAX_IMAGE_PIXELS = None

from picasa_py.db.database import PicasaDatabase
from picasa_py.db.thumbindex import ThumbIndexRecord


def set_current_thread_background_priority(lowest: bool = False) -> None:
    """
    FR: Abaisse la priorité d'ordonnancement OS du thread courant (`THREAD_PRIORITY_BELOW_NORMAL = -1`
    ou `THREAD_PRIORITY_LOWEST = -2` sous Windows, `os.nice` sous POSIX) afin que les workers
    d'arrière-plan ne préemptent jamais le thread GUI principal.
    EN: Lowers the OS scheduling priority of the current thread (`THREAD_PRIORITY_BELOW_NORMAL = -1`
    or `THREAD_PRIORITY_LOWEST = -2` on Windows, `os.nice` on POSIX) so background workers never
    preempt the main GUI thread.
    Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows), 0x0087ECD6 (BgFaceDetectThread)
    """
    try:
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadPriority(
                ctypes.windll.kernel32.GetCurrentThread(),
                -2 if lowest else -1,
            )
        elif sys.platform.startswith("linux") and hasattr(os, "setpriority"):
            # FR: Sous Linux, la priorité « nice » est propre à chaque thread (TID) ; valeur absolue (non cumulative).
            #     Sous macOS, os.nice/setpriority affecterait tout le processus (GUI incluse) : on s'abstient.
            # EN: On Linux, the nice value is per-thread (TID); absolute value (not cumulative).
            #     On macOS, os.nice/setpriority would affect the whole process (GUI included): skip.
            os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), 10 if lowest else 5)
    except Exception:
        pass


def compute_originfast_hash(file_path: Union[str, Path]) -> int:
    """
    FR: Calcule l'empreinte rapide 64 bits `imagedata_originfast` conformément à `FUN_00a4d210` :
    1. Si une copie originale existe dans `.picasaoriginals/<filename>` ou `Originals/<filename>`
       du même dossier, calcule le hash sur cette copie originale ; sinon sur `file_path`.
    2. Lit la taille `sz`, les `min(sz, 0x41C2)` premiers octets (`head`) et les `min(sz - len(head), 0x41C2)`
       derniers octets (`tail`).
    3. Calcule `MD5(pack("<I", sz & 0xFFFFFFFF) + head + tail)` et retourne les 8 premiers octets en `uint64` LE.
    EN: Computes the 64-bit fast origin hash `imagedata_originfast` matching `FUN_00a4d210`:
    1. If an original copy exists in `.picasaoriginals/<filename>` or `Originals/<filename>` in the
       same folder, hashes that original copy; otherwise hashes `file_path`.
    2. Reads file size `sz`, up to `0x41C2` (`16834`) head bytes, and up to `0x41C2` tail bytes.
    3. Computes `MD5(pack("<I", sz & 0xFFFFFFFF) + head + tail)` and returns the first 8 bytes as LE `uint64`.
    Ref: picasa3.exe @ 0x00A4D210 (FUN_00a4d210), 0x004350A4, 0x00462BA0
    """
    try:
        p = Path(file_path)
        parent = p.parent
        fname = p.name
        target_path = p
        for orig_dir in (".picasaoriginals", "Originals"):
            cand = parent / orig_dir / fname
            if cand.is_file():
                target_path = cand
                break
        with open(target_path, "rb") as f:
            sz = os.fstat(f.fileno()).st_size
            head = f.read(min(sz, 0x41C2))
            rem = sz - len(head)
            if rem > 0:
                tail_len = min(rem, 0x41C2)
                f.seek(sz - tail_len)
                tail = f.read(tail_len)
            else:
                tail = b""
        digest = hashlib.md5(struct.pack("<I", sz & 0xFFFFFFFF) + head + tail).digest()
        return int(struct.unpack_from("<Q", digest, 0)[0])
    except Exception:
        return 0


# Ref: picasa3.exe @ 0x00D33418 (table d'extensions LookupExtensionType @ 0x00A4C140, type 18 = 0x12)
RAW_EXTENSIONS = {
    ".raw", ".crw", ".cr2", ".nef", ".orf", ".dcr", ".mrw", ".pef", ".raf",
    ".srf", ".dng", ".kdc", ".sr2", ".arw", ".3fr", ".rw2", ".nrw", ".rdc",
    ".mos", ".erf", ".qtk", ".mdc", ".mef", ".k25", ".dc2", ".x3f", ".srw",
}

VIDEO_EXTENSIONS = {
    ".avi", ".wmv", ".asf", ".mpg", ".mpeg", ".mpe", ".m1v", ".m2v",
    ".mp4", ".m4v", ".mov", ".3gp", ".3g2", ".mkv", ".flv", ".webm"
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".png", ".bmp", ".gif",
    ".tif", ".tiff", ".webp", ".psd",
} | RAW_EXTENSIONS

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# Ref: picasa3.exe @ 0x00D33418 (LookupExtensionType @ 0x00A4C140, RegisterExtensions @ 0x004FADB0)
EXTENSION_TYPE_MAP = {
    ".jpg": 2,
    ".jpeg": 2,
    ".jpe": 2,
    ".bmp": 6,
    ".psd": 7,
    ".tif": 13,
    ".tiff": 13,
    # FR: Formats RAW appareil photo / EN: Camera RAW formats (type 18 = 0x12, Ref: 0x00D33418, 0x00412826, 0x00434FB0)
    **{ext: 18 for ext in RAW_EXTENSIONS},
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


_FILETIME_EPOCH_OFFSET = 116444736000000000


def file_filetimes(file_path: Union[str, Path]) -> Tuple[int, int, int]:
    """
    FR: Retourne (ft1 = création, ft2 = dernière écriture, taille) au format FILETIME Windows exact
    (précision 100 ns, sans troncature à la seconde). Vérifié sur db3 : ft2 identique au 100 ns près
    sur 362/800 fichiers inchangés depuis l'indexation.
    EN: Returns (ft1 = creation, ft2 = last write, size) as exact Windows FILETIME values
    (100 ns precision, no truncation to seconds). Verified on db3: ft2 identical to the 100 ns
    on 362/800 files unchanged since indexing.
    Ref: picasa3.exe @ 0x004F25F0 (« Name,Creation Time,Access Time,Size,... »), 0x004F54B0
    """
    st = os.stat(file_path)
    birth_ns = getattr(st, "st_birthtime_ns", None)
    if birth_ns is None:
        birth_ns = st.st_ctime_ns
    ft1 = birth_ns // 100 + _FILETIME_EPOCH_OFFSET
    ft2 = st.st_mtime_ns // 100 + _FILETIME_EPOCH_OFFSET
    return ft1, ft2, st.st_size


_WORDHASH_SPLIT_RE = re.compile(r"[\x00-\x2f\x3a-\x40\x5b-\x60\x7b-\x7f]+")
# Ref: picasa3.exe @ 0x00987DA0 (bitmap 0xD30BD0 : ':' 0x3A est conservé comme caractère de mot)
_INDEXER_TEXT_SPLIT_RE = re.compile(r"[\x00-\x2f\x3b-\x40\x5b-\x60\x7b-\x7f]+")


def tokenize_indexer_text(text: str) -> List[str]:
    """
    FR: Découpe un texte (légende, texte sur image, mot-clé) selon la table de caractères exacte
    de `CIndexer::Tokenize` (`FUN_00987da0` @ `0x00987DA0`, bitmap `0xD30BD0`) :
    conserve `'0'-'9'`, `'a'-'z'`, `':'` (`0x3A`) et tous les octets UTF-8 `>= 0x80` en minuscules.
    EN: Splits text (caption, photo text, keyword) using the exact character bitmap of
    `CIndexer::Tokenize` (`FUN_00987da0` @ `0x00987DA0`, bitmap `0xD30BD0`):
    keeps `'0'-'9'`, `'a'-'z'`, `':'` (`0x3A`), and all UTF-8 bytes `>= 0x80` in lowercase.
    Ref: picasa3.exe @ 0x00987DA0, 0x00D30BD0
    """
    if not text:
        return []
    return [tok for tok in _INDEXER_TEXT_SPLIT_RE.split(text.lower()) if tok]


_COLOR_BUCKET_TOKENS: Tuple[str, ...] = (
    "color:red",
    "color:orange",
    "color:yellow",
    "color:green",
    "color:blue",
    "color:purple",
    "color:pink",
)


def classify_image_color_tokens(img_or_bytes: Union[Image.Image, bytes]) -> List[str]:
    """
    FR: Classifie la couleur dominante d'une miniature en jetons `color:*` pour `wordhash.dat`
    conformément à `FUN_00428566` -> `FUN_00424c20` -> `FUN_009dbd10` :
    - Pour chaque pixel `(R, G, B)` de la vignette :
      - `V = max(R, G, B)`, `m = min(R, G, B)`, `delta = V - m`
      - Si `V > 0`, `S = (delta * 255) // V`
      - Si `S > 50` (`0x32`) et `delta > 0` :
        - Calcule la teinte `hue_255` sur `[0..255]` (`h_raw // 6`), puis `b24 = hue_255 // 10`
        - Associe `b24` au seau `0..6` (`red`, `orange`, `yellow`, `green`, `blue`, `purple`, `pink`)
        - Accumule `hist[bucket] += S`
    - Retourne le jeton du seau ayant le score maximal (`> 0`), ou les 3 jetons
      `["color:black", "color:white", "color:gray"]` si aucun pixel saturé ne domine.
    EN: Classifies a thumbnail's dominant color into `color:*` tokens for `wordhash.dat`
    matching `FUN_00428566` -> `FUN_00424c20` -> `FUN_009dbd10`.
    Ref: picasa3.exe @ 0x00428566, 0x00424C20, 0x009DBD10, 0x00C85220
    """
    try:
        if isinstance(img_or_bytes, (bytes, bytearray)):
            with Image.open(io.BytesIO(img_or_bytes)) as opened:
                rgb = opened.convert("RGB")
                raw = rgb.tobytes()
        elif isinstance(img_or_bytes, Image.Image):
            rgb = img_or_bytes if img_or_bytes.mode == "RGB" else img_or_bytes.convert("RGB")
            raw = rgb.tobytes()
        else:
            return []
        if not raw:
            return []
        hist = [0, 0, 0, 0, 0, 0, 0]
        # Échantillonnage rapide (pas de 3 octets = 1 pixel ; pas de 12 octets si très grande image)
        step = 3 if len(raw) <= 144 * 144 * 3 else 12
        for off in range(0, len(raw) - 2, step):
            r = raw[off]
            g = raw[off + 1]
            b = raw[off + 2]
            v = r if r >= g else g
            if b > v:
                v = b
            if v == 0:
                continue
            m = r if r <= g else g
            if b < m:
                m = b
            delta = v - m
            if delta == 0:
                continue
            s = (delta * 255) // v
            if s <= 50:
                continue
            if r == v:
                h_raw = ((g - b) * 255) // delta
            elif g == v:
                h_raw = 510 + ((b - r) * 255) // delta
            else:
                h_raw = 1020 + ((r - g) * 255) // delta
            if h_raw < 0:
                h_raw += 1530
            hue_255 = h_raw // 6
            b24 = hue_255 // 10
            if b24 == 0 or b24 >= 24:
                bucket = 0
            elif b24 <= 3:
                bucket = 1
            elif b24 == 4:
                bucket = 2
            elif b24 <= 11:
                bucket = 3
            elif b24 <= 17:
                bucket = 4
            elif b24 <= 21:
                bucket = 5
            else:
                bucket = 6
            hist[bucket] += s
        best_bucket = -1
        best_val = 0
        for idx_b, val in enumerate(hist):
            if val > best_val:
                best_val = val
                best_bucket = idx_b
        if best_bucket >= 0 and best_val > 0:
            return [_COLOR_BUCKET_TOKENS[best_bucket]]
        return ["color:black", "color:white", "color:gray"]
    except Exception:
        return []


def wordhash_tokens_for_media(
    filename: str,
    width: int,
    height: int,
    media_type: int = 2,
    folder_album_token: str = "",
    color_tokens: Optional[List[str]] = None,
) -> List[str]:
    """
    FR: Mots indexés dans wordhash.dat à l'indexation d'un média : jetons du nom de fichier complet
    (extension comprise) en minuscules, découpés sur les caractères ASCII non alphanumériques, puis
    largeur et hauteur (pour les JPEG), le jeton d'album du dossier parent (`]album:<uid>`) et
    les jetons de couleur (`color:<teinte>`). Le nom du dossier n'est PAS indexé directement.
    Vérifié sur db3 : jetons du nom 800/800, largeur/hauteur 2093/2093 JPEG, `]album:<uid>` 2931/2931 images.
    EN: Words indexed in wordhash.dat when indexing a media file: lowercase tokens of the full file name
    (extension included), split on ASCII non-alphanumeric characters, then width and height (for JPEGs),
    parent folder album token (`]album:<uid>`), and dominant color tokens (`color:<hue>`).
    Ref: picasa3.exe @ 0x00987DA0, 0x00428566, 0x00424C20, 0x009DBD10
    """
    out: List[str] = []
    seen: Set[str] = set()
    for tok in _WORDHASH_SPLIT_RE.split(filename.lower()):
        if tok and tok not in seen:
            seen.add(tok)
            out.append(tok)
    # Ref: db3 — largeur/hauteur indexées pour les JPEG uniquement (type 2 : 2093/2093 ; autres types : 2/1037)
    if media_type == 2:
        for dim in (width, height):
            if dim and dim > 0:
                s = str(int(dim))
                if s not in seen:
                    seen.add(s)
                    out.append(s)
    if media_type != 32:
        if folder_album_token:
            ftok = folder_album_token.strip().lower()
            if ftok and ftok not in seen:
                seen.add(ftok)
                out.append(ftok)
        if color_tokens:
            for ctok in color_tokens:
                c_low = ctok.strip().lower()
                if c_low and c_low not in seen:
                    seen.add(c_low)
                    out.append(c_low)
    return out


def compute_thumbnail_avgcolor(img_or_bytes: Union[Image.Image, bytes]) -> Optional[int]:
    """
    FR: Calcule la couleur moyenne ARGB 32 bits (`imagedata_avgcolor`) sur tous les pixels
    `N = width * height` de la miniature 144 px par division entière non signée (`sum_c // N`),
    conformément à `FUN_009ac640` (`0x009AC640`) appelée en `0x004280C9` :
    `0xFF000000 | ((sum_R // N) << 16) | ((sum_G // N) << 8) | (sum_B // N)`.
    EN: Computes the 32-bit ARGB average color (`imagedata_avgcolor`) across all `N = width * height`
    pixels of the 144 px thumbnail using unsigned integer floor division (`sum_c // N`),
    matching `FUN_009ac640` (`0x009AC640`) called at `0x004280C9`.
    Ref: picasa3.exe @ 0x009AC640 (div ecx @ 0x009AC70B..0x009AC72E), 0x004280C9 ("avgcolor" @ 0x00C813F0)
    """
    try:
        if isinstance(img_or_bytes, (bytes, bytearray)):
            with Image.open(io.BytesIO(img_or_bytes)) as opened:
                rgb = opened.convert("RGB")
                raw = rgb.tobytes()
            has_alpha = False
        elif isinstance(img_or_bytes, Image.Image):
            if img_or_bytes.mode == "RGBA":
                raw = img_or_bytes.tobytes()
                has_alpha = True
            else:
                rgb = img_or_bytes if img_or_bytes.mode == "RGB" else img_or_bytes.convert("RGB")
                raw = rgb.tobytes()
                has_alpha = False
        else:
            return None
        if has_alpha:
            n_pixels = len(raw) // 4
            if n_pixels <= 0:
                return None
            avg_r = sum(raw[0::4]) // n_pixels
            avg_g = sum(raw[1::4]) // n_pixels
            avg_b = sum(raw[2::4]) // n_pixels
            avg_a = sum(raw[3::4]) // n_pixels
            return (
                ((avg_a & 0xFF) << 24)
                | ((avg_r & 0xFF) << 16)
                | ((avg_g & 0xFF) << 8)
                | (avg_b & 0xFF)
            )
        n_pixels = len(raw) // 3
        if n_pixels <= 0:
            return None
        avg_r = sum(raw[0::3]) // n_pixels
        avg_g = sum(raw[1::3]) // n_pixels
        avg_b = sum(raw[2::3]) // n_pixels
        return (
            0xFF000000
            | ((avg_r & 0xFF) << 16)
            | ((avg_g & 0xFF) << 8)
            | (avg_b & 0xFF)
        )
    except Exception:
        return None


def detect_media_type(file_path: Union[str, Path]) -> int:
    """
    FR: Détermine le code `type` de `thumbindex.db` conformément à `LookupExtensionType` (`0x00A4C140`,
    table `0x00D33418`) et `DetectSignatureType` (`0x00A4C600`, appelée par `0x005B1460` / `0x005B1570`).
    Dans `0x00A4C600`, les en-têtes TIFF (`II*\\0`, `MM\\0*`, `IIN1`) retournent `0` afin que les fichiers
    TIFF (`13`) et RAW basés sur TIFF (`18`) conservent le code de leur extension ; pour les autres formats
    (`JPEG -> 2`, `BMP -> 6`, `PNG/GIF/WEBP -> 31`), la signature prime sur l'extension.
    EN: Determines the `thumbindex.db` `type` code matching `LookupExtensionType` (`0x00A4C140`,
    table `0x00D33418`) and `DetectSignatureType` (`0x00A4C600`, called by `0x005B1460` / `0x005B1570`).
    Ref: picasa3.exe @ 0x00A4C600, 0x00A4C140, 0x005B1460, 0x005B1570, 0x004FADB0, 0x00D33418
    """
    ext = os.path.splitext(str(file_path))[1].lower()
    ext_type = EXTENSION_TYPE_MAP.get(ext, 2)
    if ext_type in (18, 32) or ext in VIDEO_EXTENSIONS:
        return ext_type
    try:
        with open(file_path, "rb") as f:
            head = f.read(12)
    except OSError:
        return ext_type
    if head[:3] == b"\xff\xd8\xff":
        return 2
    if head[:8] == b"\x89PNG\r\n\x1a\n" or head[:6] in (b"GIF87a", b"GIF89a") or (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
        return 31
    if head[:2] == b"BM":
        return 6
    if head[:4] == b"8BPS":
        return 7
    if head[:4] in (b"II*\x00", b"MM\x00*", b"IIN1"):
        return ext_type if ext_type in (13, 18) else 13
    return ext_type


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
            os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")
            os.environ.setdefault("OPENCV_LOG_LEVEL", "OFF")
            import cv2
            try:
                if hasattr(cv2, "setLogLevel"):
                    cv2.setLogLevel(0)
            except Exception:
                pass
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
            try:
                with open(file_path, "rb") as fh_vid:
                    head_vid = fh_vid.read(64)
                if len(head_vid) >= 32 and all(b in (9, 10, 13) or 32 <= b <= 126 for b in head_vid):
                    # Fichier texte pur portant une extension vidéo (ex. LICENSES/COPYING.MKV)
                    return None
            except Exception:
                pass
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
            bt_bytes_vid: Optional[bytes] = None
        else:
            if thumb_img.mode != "RGB":
                thumb_img = thumb_img.convert("RGB")
            bt_vid_img = thumb_img.copy()
            bt_vid_img.thumbnail((288, 288), Image.Resampling.BILINEAR)
            buf_bt = io.BytesIO()
            bt_vid_img.save(buf_bt, format="JPEG", quality=90)
            bt_bytes_vid = buf_bt.getvalue()
            thumb_img.thumbnail((max_thumb_size, max_thumb_size), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        thumb_img.save(buf, format="JPEG", quality=90, optimize=True)
        jpeg_bytes = buf.getvalue()
        if bt_bytes_vid is None:
            bt_bytes_vid = jpeg_bytes

        t2_img = thumb_img.copy()
        t2_img.thumbnail((72, 72), Image.Resampling.LANCZOS)
        buf2 = io.BytesIO()
        t2_img.save(buf2, format="JPEG", quality=90, optimize=True)
        return _MediaMetadataResult(
            jpeg_bytes,
            orig_w,
            orig_h,
            ole_date,
            thumb2_bytes=buf2.getvalue(),
            bigthumb_bytes=bt_bytes_vid,
        )
    except Exception:
        return None


def extract_media_metadata_and_thumb(
    file_path: str, max_thumb_size: int = 144
) -> Optional[Tuple[bytes, int, int, float]]:
    """
    FR: Extrait les métadonnées et la miniature appropriée selon le type de média (image ou vidéo).
    EN: Extracts metadata and the appropriate thumbnail depending on media type (image or video).
    Ref: picasa3.exe @ 0x00424CA0 (thumbs=144px, thumbs2=72px, bigthumbs=288px, quality=90)
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return extract_video_metadata_and_thumb(file_path, max_thumb_size)
    return extract_image_metadata_and_thumb(file_path, max_thumb_size)


class _MediaMetadataResult(tuple):
    """
    FR: Nuplet `(jpeg_bytes, width, height, ole_date)` supportant également l'accès par clé dictionnaire
    (`meta["lat"]`, `meta["lon"]`, `meta.get("lat")`) pour les coordonnées GPS EXIF et `bigthumb_bytes`.
    EN: Tuple `(jpeg_bytes, width, height, ole_date)` also supporting dictionary key access
    (`meta["lat"]`, `meta["lon"]`, `meta.get("lat")`) for EXIF GPS coordinates and `bigthumb_bytes`.
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
        bigthumb_bytes: Optional[bytes] = None,
    ):
        obj = super().__new__(cls, (jpeg_bytes, width, height, ole_date))
        obj.lat = lat
        obj.lon = lon
        obj.thumb2_bytes = thumb2_bytes
        obj.bigthumb_bytes = bigthumb_bytes
        obj._extra = {
            "thumb": jpeg_bytes,
            "jpeg_bytes": jpeg_bytes,
            "thumb2_bytes": thumb2_bytes,
            "bigthumb_bytes": bigthumb_bytes,
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


def _scale_box_dimensions(sw: int, sh: int, target: int) -> Tuple[int, int]:
    """
    FR: Calcule les dimensions `(nw, nh)` d'une boîte englobante `target x target` selon la formule
    FPU exacte de `FUN_009b4aa0` (`0x009B4AA0`, appelée par `0x00A405A0` en `0x00A4060A` et par
    `0x00425210` en `0x004257B7` lors de `0x00424CA0`) :
      1. `scale = min((target + 0.499) / sw, (target + 0.499) / sh)` (constante `0.499` @ `0x00CF4160`)
      2. Conversion `float32` de `sw * scale + 1e-5` et `sh * scale + 1e-5` (constante `1e-5` @ `0x00CF41E0`,
         `fstp dword ptr` + `fld dword ptr` en `0x009B4B19..0x009B4B37`)
      3. Arrondi FPU au plus proche (`fistp dword ptr`, round-to-even).
    Vérifié sur `db3` : `99.98 %` (`4391 / 4392`) de correspondance exacte sur `thumbs2`.
    EN: Computes bounding-box dimensions `(nw, nh)` inside `target x target` using the exact FPU
    formula of `FUN_009b4aa0` (`0x009B4AA0`).
    Ref: picasa3.exe @ 0x009B4AA0, 0x00A405A0, 0x00424CA0, 0x00425210 (0x00CF4160 = 0.499, 0x00CF41E0 = 1e-5)
    """
    if sw <= 0 or sh <= 0 or target <= 0:
        return max(1, sw), max(1, sh)
    t_bias = float(target) + 0.499
    scale = min(t_bias / float(sw), t_bias / float(sh))
    fw = struct.unpack("<f", struct.pack("<f", float(sw) * scale + 1e-5))[0]
    fh = struct.unpack("<f", struct.pack("<f", float(sh) * scale + 1e-5))[0]
    return max(1, int(round(fw))), max(1, int(round(fh)))


def _fit_long_side(img: Image.Image, target: int, src_size: Optional[Tuple[int, int]] = None) -> Image.Image:
    """
    FR: Redimensionne l'image dans une boîte `target x target` selon `FUN_009b4aa0` (`0x009B4AA0`)
    appelée par `0x00A405A0` dans `0x00424CA0` (`288 -> 144 -> 72`).
    EN: Resizes the image into a `target x target` bounding box matching `FUN_009b4aa0` (`0x009B4AA0`)
    called by `0x00A405A0` in `0x00424CA0` (`288 -> 144 -> 72`).
    Ref: picasa3.exe @ 0x009B4AA0, 0x00A405A0, 0x00424CA0, 0x00425210
    """
    w, h = img.size
    if w <= 0 or h <= 0:
        return img.copy()
    sw, sh = src_size if (src_size and src_size[0] > 0 and src_size[1] > 0) else (w, h)
    nw, nh = _scale_box_dimensions(sw, sh, target)
    if (nw, nh) == (w, h):
        return img.copy()
    return img.resize((nw, nh), Image.Resampling.BILINEAR)


def _extract_tiff_raw_metadata_and_preview(
    file_path: Union[str, Path]
) -> Optional[Tuple[int, int, int, float, Optional[bytes]]]:
    """
    FR: Analyse binaire directe des en-têtes TIFF / SubIFD / ExifIFD des fichiers RAW (`.pef`, `.cr2`,
    `.nef`, `.arw`, `.dng`, `.orf`, `.rw2`, `.sr2`, etc.) conformément à `dcraw::parse_tiff_ifd`
    (`0x008BD740`) et `dcraw::identify` (`0x008C925E..0x008C93C8`) :
    - Parcourt `IFD0`, `SubIFDs` (`0x014A`), `ExifIFD` (`0x8769`) et la chaîne `NextIFD`
    - Identifie les dimensions du capteur RAW (`Compression` != 6 et != 7, ou plus grand IFD) et applique
      les ajustements de largeur/hauteur active Pentax de `0x008C928E..0x008C93B7` (`K-x`/`K-r` : `4352 -> 4309`,
      `K-5` : `>=4960 -> 4950, h-10`, `K-7` : `4736 -> 4684x3122`, `(2624,3936) -> (2616,3896)`,
      `(3136,4864) -> (3124,4688)`)
    - Extrait l'orientation EXIF (`0x0112`), la date de prise de vue (`0x9003` / `0x0132`) et le plus grand
      aperçu JPEG intégré (`0x0201` + `0x0202`, ou `0x0111` + `0x0117` si flux `0xFF 0xD8 0xFF`).
    EN: Direct binary TIFF / SubIFD / ExifIFD parser for RAW files matching `dcraw::parse_tiff_ifd`
    (`0x008BD740`) and `dcraw::identify` (`0x008C925E..0x008C93C8`).
    Ref: picasa3.exe @ 0x008BD740, 0x008C925E..0x008C93C8
    """
    try:
        with open(file_path, "rb") as f:
            head = f.read(8)
            if len(head) < 8:
                return None
            endian_tag = head[:2]
            if endian_tag == b"II":
                bo = "<"
            elif endian_tag == b"MM":
                bo = ">"
            else:
                return None
            magic, ifd0_off = struct.unpack(bo + "HI", head[2:8])
            if magic not in (42, 0x4F52, 0x5352, 0x0055):
                return None

            f.seek(0, os.SEEK_END)
            file_len = f.tell()

            type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}

            def _read_tag_values(ttype: int, count: int, val_bytes: bytes):
                sz = type_sizes.get(ttype, 1) * count
                if sz <= 0 or count <= 0:
                    return []
                if sz <= 4:
                    raw_b = val_bytes[:sz]
                else:
                    off = struct.unpack(bo + "I", val_bytes)[0]
                    if off <= 0 or off + sz > file_len:
                        return []
                    pos = f.tell()
                    f.seek(off)
                    raw_b = f.read(sz)
                    f.seek(pos)
                if ttype == 2:
                    return [raw_b.rstrip(b"\x00").decode("latin-1", errors="ignore")]
                if ttype in (1, 6, 7):
                    return list(raw_b)
                if ttype == 3:
                    return list(struct.unpack(bo + f"{len(raw_b) // 2}H", raw_b))
                if ttype == 4:
                    return list(struct.unpack(bo + f"{len(raw_b) // 4}I", raw_b))
                if ttype == 8:
                    return list(struct.unpack(bo + f"{len(raw_b) // 2}h", raw_b))
                if ttype == 9:
                    return list(struct.unpack(bo + f"{len(raw_b) // 4}i", raw_b))
                return []

            visited: Set[int] = set()
            queue: List[int] = [ifd0_off]
            raw_candidates: List[Tuple[int, int, int]] = []
            all_dims: List[Tuple[int, int]] = []
            jpeg_spans: List[Tuple[int, int]] = []
            orient = 1
            model_str = ""
            date_strs: List[Tuple[int, str]] = []

            while queue:
                ifd_off = queue.pop(0)
                if ifd_off <= 0 or ifd_off in visited or ifd_off + 2 > file_len or len(visited) > 32:
                    continue
                visited.add(ifd_off)
                f.seek(ifd_off)
                cnt_b = f.read(2)
                if len(cnt_b) < 2:
                    continue
                n_entries = struct.unpack(bo + "H", cnt_b)[0]
                if n_entries <= 0 or n_entries > 512:
                    continue
                entries_b = f.read(n_entries * 12)
                if len(entries_b) < n_entries * 12:
                    continue
                nxt_b = f.read(4)
                if len(nxt_b) == 4:
                    nxt_off = struct.unpack(bo + "I", nxt_b)[0]
                    if nxt_off > 0 and nxt_off not in visited:
                        queue.append(nxt_off)

                ifd_w = 0
                ifd_h = 0
                ifd_comp = 0
                jpg_off = 0
                jpg_len = 0
                strip_off = 0
                strip_len = 0

                for i in range(n_entries):
                    eb = entries_b[i * 12 : (i + 1) * 12]
                    tag, ttype, count = struct.unpack(bo + "HHI", eb[:8])
                    val_b = eb[8:12]
                    if tag in (
                        0x0100, 0x0101, 0x0103, 0x0110, 0x0111, 0x0112, 0x0117,
                        0x0132, 0x014A, 0x0201, 0x0202, 0x8769, 0x9003, 0xA002, 0xA003,
                    ):
                        vals = _read_tag_values(ttype, count, val_b)
                        if not vals:
                            continue
                        if tag in (0x0100, 0xA002):
                            ifd_w = max(ifd_w, int(vals[0]))
                        elif tag in (0x0101, 0xA003):
                            ifd_h = max(ifd_h, int(vals[0]))
                        elif tag == 0x0103:
                            ifd_comp = int(vals[0])
                        elif tag == 0x0110 and isinstance(vals[0], str):
                            model_str = vals[0].strip()
                        elif tag == 0x0112 and orient == 1:
                            orient = int(vals[0])
                        elif tag in (0x9003, 0x0132) and isinstance(vals[0], str):
                            date_strs.append((0 if tag == 0x9003 else 1, vals[0].strip()))
                        elif tag in (0x014A, 0x8769):
                            for sub_off in vals:
                                if isinstance(sub_off, int) and sub_off > 0 and sub_off not in visited:
                                    queue.append(sub_off)
                        elif tag == 0x0201:
                            jpg_off = int(vals[0])
                        elif tag == 0x0202:
                            jpg_len = int(vals[0])
                        elif tag == 0x0111 and len(vals) == 1:
                            strip_off = int(vals[0])
                        elif tag == 0x0117 and len(vals) == 1:
                            strip_len = int(vals[0])

                if ifd_w > 0 and ifd_h > 0:
                    all_dims.append((ifd_w, ifd_h))
                    if ifd_comp not in (6, 7):
                        raw_candidates.append((ifd_w, ifd_h, ifd_comp))
                if jpg_off > 0 and jpg_len > 0 and jpg_off + jpg_len <= file_len:
                    jpeg_spans.append((jpg_len, jpg_off))
                elif strip_off > 0 and strip_len > 0 and strip_off + strip_len <= file_len and ifd_comp in (6, 7):
                    jpeg_spans.append((strip_len, strip_off))

            if raw_candidates:
                raw_w, raw_h, _ = max(raw_candidates, key=lambda item: item[0] * item[1])
            elif all_dims:
                raw_w, raw_h = max(all_dims, key=lambda item: item[0] * item[1])
            else:
                return None

            # Ref: picasa3.exe @ 0x008C928E..0x008C93B7 (dcraw::identify — dimensions actives capteur Pentax)
            if (raw_h, raw_w) == (2624, 3936):
                raw_h, raw_w = 2616, 3896
            elif (raw_h, raw_w) == (3136, 4864):
                raw_h, raw_w = 3124, 4688
            if model_str:
                m_up = model_str.upper()
                if raw_w == 4352 and ("K-R" in m_up or "K-X" in m_up):
                    raw_w = 4309
                elif raw_w >= 4960 and "K-5" in m_up:
                    raw_w = 4950
                    raw_h = max(1, raw_h - 10)
                elif raw_w == 4736 and "K-7" in m_up:
                    raw_w = 4684
                    raw_h = 3122

            ole_date = 0.0
            date_strs.sort(key=lambda item: item[0])
            for _, d_str in date_strs:
                try:
                    dt = datetime.strptime(d_str[:19], "%Y:%m:%d %H:%M:%S")
                    ole_date = datetime_to_ole(dt)
                    break
                except Exception:
                    pass
            if ole_date == 0.0:
                try:
                    ole_date = datetime_to_ole(datetime.fromtimestamp(os.path.getmtime(file_path)))
                except Exception:
                    ole_date = 0.0

            preview_bytes: Optional[bytes] = None
            if jpeg_spans:
                jpeg_spans.sort(reverse=True)
                for j_len, j_off in jpeg_spans:
                    f.seek(j_off)
                    cand_b = f.read(j_len)
                    if cand_b[:3] == b"\xff\xd8\xff":
                        preview_bytes = cand_b
                        break

            return raw_w, raw_h, orient, ole_date, preview_bytes
    except Exception:
        return None


def extract_image_metadata_and_thumb(
    file_path: str, max_thumb_size: int = 144
) -> Optional[Tuple[bytes, int, int, float]]:
    """
    FR: Ouvre l'image, oriente selon l'EXIF, extrait les dimensions et coordonnées GPS,
    calcule la date OLE, et génère le buffer JPEG de la vignette (144px max, qualité 90,
    ainsi que la vignette `thumbs2` 72px max, qualité 90).
    Pour les fichiers RAW (`.pef`, `.cr2`, `.nef`, `.arw`, `.dng`, etc.), extrait les dimensions
    capteur exactes et l'aperçu JPEG intégré conformément à `dcraw::parse_tiff_ifd` (`0x008BD740`)
    et `dcraw::identify` (`0x008C925E..0x008C93C8`).
    EN: Opens the image, applies EXIF orientation, extracts dimensions and GPS coordinates,
    computes the OLE date, and generates the thumbnail JPEG buffer (144px max, quality 90,
    along with the `thumbs2` 72px max, quality 90 thumbnail).
    Ref: picasa3.exe @ 0x00424CA0 (thumbs=144px, thumbs2=72px, quality=90), 0x009B4AA0, 0x008BD740, 0x008C92E8
    """
    ext_low = os.path.splitext(file_path)[1].lower()
    raw_info = _extract_tiff_raw_metadata_and_preview(file_path) if ext_low in RAW_EXTENSIONS else None

    try:
        if raw_info is not None and raw_info[4] is not None:
            raw_w, raw_h, exif_orient, ole_date, preview_bytes = raw_info
            gps_lat, gps_lon = None, None
            with Image.open(io.BytesIO(preview_bytes)) as prev_img:
                prev_img.load()
                if exif_orient in (5, 6, 7, 8):
                    orig_w, orig_h = raw_h, raw_w
                else:
                    orig_w, orig_h = raw_w, raw_h

                # Ref: libtiff @ picasa3.exe — rejette les TIFF malformés dépourvus de StripByteCounts (279) et TileByteCounts (325)
                if raw_info is None and getattr(raw_img, "format", None) == "TIFF":
                    tag_v2 = getattr(raw_img, "tag_v2", None)
                    if tag_v2 is not None and 279 not in tag_v2 and 325 not in tag_v2:
                        return None

                # Ref: PSD loader @ picasa3.exe — rejette les fichiers PSD dépassant 8192 px de côté
                if ext_low == ".psd" and (orig_w > 8192 or orig_h > 8192):
                    return None

                # Ref: picasa3.exe @ 0x009B4AA0, 0x00424CA0 — rejette les images dégénérées dont la miniature 72px a une dimension nulle (<= 0)
                if orig_w <= 0 or orig_h <= 0 or int((min(orig_w, orig_h) * 72.0) / max(orig_w, orig_h) + 0.499) <= 0:
                    return None
                img = prev_img.copy()
                if exif_orient != 1 and img.width >= img.height and orig_w < orig_h:
                    if exif_orient == 6:
                        img = img.transpose(Image.Transpose.ROTATE_270)
                    elif exif_orient == 8:
                        img = img.transpose(Image.Transpose.ROTATE_90)
                elif exif_orient == 3:
                    img = img.transpose(Image.Transpose.ROTATE_180)
        else:
            with Image.open(file_path) as raw_img:
                exif_data = raw_img.getexif()
                gps_lat, gps_lon = _extract_exif_gps(raw_img, exif_data)

                # 1. FR: Dimensions réelles (avec orientation EXIF 0x0112) extraites avant tout draft()
                #    EN: True pixel dimensions (accounting for EXIF Orientation 0x0112) extracted before draft()
                if raw_info is not None:
                    raw_w, raw_h, exif_orient, ole_date, _ = raw_info
                else:
                    raw_w, raw_h = raw_img.size
                    exif_orient = exif_data.get(0x0112, 1) if exif_data else 1
                if exif_orient in (5, 6, 7, 8):
                    orig_w, orig_h = raw_h, raw_w
                else:
                    orig_w, orig_h = raw_w, raw_h

                # Ref: libtiff @ picasa3.exe — rejette les TIFF malformés dépourvus de StripByteCounts (279) et TileByteCounts (325)
                if raw_info is None and getattr(raw_img, "format", None) == "TIFF":
                    tag_v2 = getattr(raw_img, "tag_v2", None)
                    if tag_v2 is not None and 279 not in tag_v2 and 325 not in tag_v2:
                        return None

                # Ref: PSD loader @ picasa3.exe — rejette les fichiers PSD dépassant 8192 px de côté
                if ext_low == ".psd" and (orig_w > 8192 or orig_h > 8192):
                    return None

                # Ref: picasa3.exe @ 0x009B4AA0, 0x00424CA0 — rejette les images dégénérées dont la miniature 72px a une dimension nulle (<= 0)
                if orig_w <= 0 or orig_h <= 0 or int((min(orig_w, orig_h) * 72.0) / max(orig_w, orig_h) + 0.499) <= 0:
                    return None

                # 2. FR: Extraction de la date (EXIF DateTimeOriginal ou date fichier)
                #    EN: Date extraction (EXIF DateTimeOriginal or file modification time)
                if raw_info is None:
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

                # 3. FR: Décodage DCT sous-échantillonné (libjpeg draft 1/2, 1/4, 1/8) pour les grands JPEG
                #    EN: Subsampled DCT decoding (libjpeg draft 1/2, 1/4, 1/8) for large JPEGs
                draft_target = max(max_thumb_size * 2, 288)
                if getattr(raw_img, "format", None) == "JPEG" and (raw_w > draft_target * 2 or raw_h > draft_target * 2):
                    try:
                        raw_img.draft("RGB", (draft_target, draft_target))
                    except Exception:
                        pass

                # 4. FR: Orientation automatique selon les balises EXIF et conversion propre de la transparence
                #    EN: Automatic EXIF orientation and clean transparency conversion
                if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                    raw_img = raw_img.convert("RGBA")
                try:
                    img = ImageOps.exif_transpose(raw_img)
                except Exception:
                    img = raw_img.copy()
                if img is raw_img:
                    img = raw_img.copy()

        # 5. FR: Cascade de miniatures conforme à 0x00424CA0 -> 0x00A405A0 -> 0x009B4AA0 :
        #        bigthumbs (288px max, q=90) -> thumbs (144px, q=90) -> thumbs2 (72px, q=90)
        #    EN: Thumbnail cascade matching 0x00424CA0 -> 0x00A405A0 -> 0x009B4AA0:
        #        bigthumbs (288px max, q=90) -> thumbs (144px, q=90) -> thumbs2 (72px, q=90)
        bt_max = max(288, max_thumb_size)
        if max(orig_w, orig_h) > bt_max:
            bt_img = _fit_long_side(img, bt_max, (orig_w, orig_h))
        else:
            bt_img = img.copy()
        if bt_img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", bt_img.size, (255, 255, 255))
            bg.paste(bt_img, mask=bt_img.split()[3])
            bt_img = bg
        elif bt_img.mode != "RGB":
            bt_img = bt_img.convert("RGB")

        buf_bt = io.BytesIO()
        bt_img.save(buf_bt, format="JPEG", quality=90)
        bigthumb_bytes = buf_bt.getvalue()

        thumb_img = _fit_long_side(bt_img, max_thumb_size, bt_img.size)
        buf = io.BytesIO()
        thumb_img.save(buf, format="JPEG", quality=90)
        jpeg_bytes = buf.getvalue()

        t2_img = _fit_long_side(thumb_img, 72, thumb_img.size)
        buf2 = io.BytesIO()
        t2_img.save(buf2, format="JPEG", quality=90)
        thumb2_bytes = buf2.getvalue()

        return _MediaMetadataResult(
            jpeg_bytes,
            orig_w,
            orig_h,
            ole_date,
            lat=gps_lat,
            lon=gps_lon,
            thumb2_bytes=thumb2_bytes,
            bigthumb_bytes=bigthumb_bytes,
        )
    except Exception:
        if ext_low in RAW_EXTENSIONS and os.path.exists(file_path):
            try:
                if raw_info is not None:
                    fb_w, fb_h, fb_orient, ole_date, _ = raw_info
                    if fb_orient in (5, 6, 7, 8):
                        fb_w, fb_h = fb_h, fb_w
                elif ext_low == ".raw":
                    # FR: Un fichier binaire .raw générique sans en-tête TIFF/RAW valide n'est pas une photo RAW
                    # EN: A generic .raw binary file without a valid TIFF/RAW header is not a camera RAW photo
                    return None
                else:
                    fb_w, fb_h = 640, 480
                    mtime = os.path.getmtime(file_path)
                    ole_date = datetime_to_ole(datetime.fromtimestamp(mtime))
                t1_w, t1_h = _scale_box_dimensions(fb_w, fb_h, max_thumb_size)
                raw_fallback = Image.new("RGB", (t1_w, t1_h), (48, 50, 54))
                b_sm = io.BytesIO()
                raw_fallback.save(b_sm, format="JPEG", quality=90)
                sm_bytes = b_sm.getvalue()
                t2_fb = _fit_long_side(raw_fallback, 72, (t1_w, t1_h))
                b_t2 = io.BytesIO()
                t2_fb.save(b_t2, format="JPEG", quality=90)
                return _MediaMetadataResult(
                    sm_bytes,
                    fb_w,
                    fb_h,
                    ole_date,
                    thumb2_bytes=b_t2.getvalue(),
                    bigthumb_bytes=sm_bytes,
                )
            except Exception:
                return None
        return None


# Ref: style/filters.txt @ 0x004FBFF0 (DirectoryFilters), 0x004FBBFE..0x004FBCFA (thumbs, RECYCLER, Originals, .picasaoriginals)
DEFAULT_EXCLUDED_DIRS: Set[str] = {
    "windows",
    "winnt",
    "temp",
    "program files",
    "program files (x86)",
    "programdata",
    "appdata",
    "application data",
    "local settings",
    "originals",
    ".picasaoriginals",
    "thumbs",
    "recycler",
    "$recycle.bin",
    "system volume information",
    "pytest_tmp",
}


def load_directory_filters() -> Set[str]:
    """
    FR: Charge la liste d'exclusion des répertoires depuis style/filters.txt ou runtime/filters.txt (section DirectoryFilters).
    EN: Loads the directory exclusion list from style/filters.txt or runtime/filters.txt (DirectoryFilters section).
    Ref: picasa3.exe @ 0x004FBFF0, 0x00D0AD70 (filters.txt -> DirectoryFilters)
    """
    excluded = set(DEFAULT_EXCLUDED_DIRS)
    candidates: List[Path] = []
    try:
        from picasa_py.ui.resources import RES_DIR
        candidates.append(RES_DIR / "style" / "filters.txt")
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

    def is_excluded_dir(self, dir_name: str, full_path: Optional[str] = None) -> bool:
        """
        FR: Indique si un sous-dossier doit être ignoré lors du scan récursif
        (filtres DirectoryFilters, dossiers système/AppData/Temp et répertoire de base db3).
        EN: Indicates whether a subfolder should be skipped during recursive scanning
        (DirectoryFilters, Windows system/AppData/Temp folders, and the db3 database directory).
        Ref: picasa3.exe @ 0x00415790, 0x004FBB90..0x004FC050, 0x0085A0B0 (.picasaoriginals), style/filters.txt
        """
        clean = os.path.basename(dir_name.rstrip("\\/")).lower()
        if clean in self.excluded_dirs or clean.startswith(".") or clean.startswith("$"):
            return True
        if full_path and self.db and getattr(self.db, "db3_dir", None):
            try:
                if os.path.normcase(os.path.abspath(full_path)) == os.path.normcase(os.path.abspath(str(self.db.db3_dir))):
                    return True
            except Exception:
                pass
        return False

    def is_folder_face_excluded(self, folder_path: str) -> bool:
        """
        FR: Vérifie si le dossier comporte frexclude=1 dans la section [Picasa] de son .picasa.ini.
        EN: Checks whether the folder has frexclude=1 in the [Picasa] section of its .picasa.ini.
        Ref: picasa3.exe @ 0x00881690 (frexclude)
        """
        has_db_cache = bool(self.db and hasattr(self.db, "get_parsed_ini"))
        for ini_name in (".picasa.ini", "Picasa.ini"):
            ini_path = os.path.join(folder_path, ini_name)
            doc = self.db.get_parsed_ini(ini_path) if has_db_cache else None
            if doc is None and not has_db_cache and os.path.exists(ini_path):
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

    def get_enabled_extensions(self) -> Set[str]:
        """
        FR: Retourne l'ensemble des extensions de fichiers activées selon les préférences Picasa 3
        (`SupportBMP`, `SupportGIF`, `SupportPNG`, `SupportTGA`, `SupportTIF`, `SupportWEBP`,
        `SupportPSD`, `SupportRAW`, `SupportMovies`).
        Conformément à `picasa3.exe @ 0x004E04A0..0x004E0780`, `.gif`, `.png` et `.tga` sont
        désactivés par défaut (`0`), tandis que `.jpg`, `.bmp`, `.tif`, `.webp`, `.psd`, RAW et vidéos
        sont activés par défaut (`1`).
        EN: Returns the set of enabled file extensions according to Picasa 3 preferences.
        Per `picasa3.exe @ 0x004E04A0..0x004E0780`, `.gif`, `.png`, and `.tga` are disabled by
        default (`0`), while `.jpg`, `.bmp`, `.tif`, `.webp`, `.psd`, RAW, and videos are enabled (`1`).
        Ref: picasa3.exe @ 0x004E04A0..0x004E0985, 0x004FADB0, 0x004FB948
        """
        exts: Set[str] = {".jpg", ".jpeg", ".jpe"}
        try:
            from picasa_py.db.preferences import PicasaPreferences
            prefs = PicasaPreferences()

            def _is_enabled(support_key: str, default: bool) -> bool:
                raw = prefs.value(support_key, None)
                if raw is None:
                    return default
                if isinstance(raw, bool):
                    return raw
                s = str(raw).strip().lower()
                if s in ("1", "true", "yes"):
                    return True
                if s in ("0", "false", "no"):
                    return False
                return default

            if _is_enabled("SupportBMP", True):
                exts.add(".bmp")
            if _is_enabled("SupportGIF", False):
                exts.add(".gif")
            if _is_enabled("SupportPNG", False):
                exts.add(".png")
            if _is_enabled("SupportTGA", False):
                exts.add(".tga")
            if _is_enabled("SupportTIF", True):
                exts.update({".tif", ".tiff"})
            if _is_enabled("SupportWEBP", True):
                exts.add(".webp")
            if _is_enabled("SupportPSD", True):
                exts.add(".psd")
            if _is_enabled("SupportRAW", True):
                exts.update(RAW_EXTENSIONS)
            if _is_enabled("SupportMovies", True):
                exts.update(VIDEO_EXTENSIONS)
        except Exception:
            exts.update({".bmp", ".tif", ".tiff", ".webp", ".psd"} | RAW_EXTENSIONS | VIDEO_EXTENSIONS)
        return exts

    def scan_folder_for_media(self, folder_path: str, recursive: bool = True, is_cancelled=None) -> List[str]:
        """
        FR: Énumère l'ensemble des fichiers média d'un répertoire avec support d'annulation,
        filtrage des extensions activées (`0x004E04A0`) et exclusion des sous-dossiers retirés (`-` dans `scanlist.txt`).
        EN: Enumerates all media files in a directory with cancellation support,
        enabled extension filtering (`0x004E04A0`), and exclusion of removed subfolders (`-` in `scanlist.txt`).
        Ref: picasa3.exe @ 0x00415790, 0x004E04A0, 0x004F6380
        """
        results: List[str] = []
        host_folder = folder_path.replace("\\", os.sep) if os.sep != "\\" else folder_path
        if not os.path.exists(host_folder) or not os.path.isdir(host_folder):
            return results
        if self.is_excluded_dir(os.path.basename(host_folder.rstrip("\\/")), host_folder):
            return results

        enabled_exts = self.get_enabled_extensions()
        excluded_watched_dirs: Set[str] = set()
        if self.db and hasattr(self.db, "get_watched_folders"):
            try:
                for wp, st in self.db.get_watched_folders().items():
                    if st == "0":
                        excluded_watched_dirs.add(
                            os.path.normcase(os.path.abspath(wp.replace("\\", os.sep).rstrip("\\/")))
                        )
            except Exception:
                pass

        if not recursive:
            try:
                self._collect_ini_albums_from_folder(host_folder)
                for entry in os.scandir(host_folder):
                    if is_cancelled and is_cancelled():
                        break
                    if entry.is_file() and not entry.name.startswith("."):
                        ext_l = Path(entry.name).suffix.lower()
                        if ext_l in enabled_exts:
                            try:
                                if entry.stat().st_size <= 0:
                                    continue
                            except Exception:
                                continue
                            if ext_l == ".raw" and _extract_tiff_raw_metadata_and_preview(entry.path) is None:
                                continue
                            results.append(os.path.abspath(entry.path))
            except Exception:
                pass
            return results

        try:
            dir_counter = 0
            for root, dirs, files in os.walk(host_folder):
                if is_cancelled and is_cancelled():
                    break
                dirs[:] = [
                    d for d in dirs
                    if not self.is_excluded_dir(d, os.path.join(root, d))
                    and os.path.normcase(os.path.abspath(os.path.join(root, d))) not in excluded_watched_dirs
                ]
                self._collect_ini_albums_from_folder(root)
                for fname in files:
                    if fname.startswith("."):
                        continue
                    ext_l = Path(fname).suffix.lower()
                    if ext_l in enabled_exts:
                        full_p = os.path.abspath(os.path.join(root, fname))
                        try:
                            if os.path.getsize(full_p) <= 0:
                                continue
                        except Exception:
                            continue
                        if ext_l == ".raw" and _extract_tiff_raw_metadata_and_preview(full_p) is None:
                            continue
                        results.append(full_p)
                dir_counter += 1
                if dir_counter % 10 == 0:
                    time.sleep(0.001)
        except Exception:
            pass

        return results

    def _collect_ini_albums_from_folder(self, folder_path: str) -> None:
        """
        FR: Découvre les sections [.album:<token>] et les références albums= d'un dossier .picasa.ini.
        EN: Discovers [.album:<token>] sections and albums= references from a folder's .picasa.ini.
        Ref: picasa3.exe @ 0x00456A15, 0x00732160
        """
        has_db_cache = bool(self.db and hasattr(self.db, "get_parsed_ini"))
        for ini_name in (".picasa.ini", "Picasa.ini"):
            ini_path = os.path.join(folder_path, ini_name)
            doc = self.db.get_parsed_ini(ini_path) if has_db_cache else None
            if doc is None and not has_db_cache:
                if not os.path.exists(ini_path):
                    continue
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
                            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
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
                pmp.dirty = True

        # FR: Si les tables albumdata_* sont totalement vides, réserver la ligne 0 ("]unknownface" / "Sans nom") comme picasa3.exe (0x008AAD76)
        # EN: If albumdata_* tables are completely empty, reserve row 0 ("]unknownface" / "Sans nom") like picasa3.exe (0x008AAD76)
        if len(ad_name.records) == 0:
            for stem, pmp in albumdata_tables.items():
                if stem == "albumdata_name":
                    pmp.records.append("Sans nom")
                elif stem == "albumdata_token":
                    pmp.records.append("]unknownface")
                elif stem == "albumdata_uid":
                    pmp.records.append("dd27de9b1f1abf38b41e1a769380f405")
                elif stem == "albumdata_category":
                    pmp.records.append(8)
                else:
                    pmp.records.append(pmp.default_value())
                pmp.dirty = True

        existing_token_to_row: Dict[str, int] = {
            str(tok): i for i, tok in enumerate(ad_token.records) if tok
        }
        for row_i, existing_tok in enumerate(ad_token.records):
            clean_ex = str(existing_tok or "").strip()
            if clean_ex.startswith("]album:") or clean_ex.startswith(".album:"):
                clean_ex = clean_ex[7:].strip()
            if clean_ex and clean_ex not in existing_token_to_row:
                existing_token_to_row[clean_ex] = row_i

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

            existing_row = existing_token_to_row.get(tok_clean)
            if existing_row is None:
                existing_row = existing_token_to_row.get(f"]album:{tok_clean}")

            # Ref: db3/albumdata_token.pmp — les albums utilisateur (catégorie 0) sont stockés « ]album:<uid> »
            canonical_tok = f"]album:{tok_clean}"
            if existing_row is not None:
                if ad_name.records[existing_row] != aname:
                    ad_name.records[existing_row] = aname
                    ad_name.dirty = True
                if ad_token.records[existing_row] != canonical_tok:
                    ad_token.records[existing_row] = canonical_tok
                    ad_token.dirty = True
                if ad_cat.records[existing_row] != 0:
                    ad_cat.records[existing_row] = 0
                    ad_cat.dirty = True
                if adate and "albumdata_date" in albumdata_tables:
                    ad_date = albumdata_tables["albumdata_date"]
                    if ad_date.records[existing_row] != adate:
                        ad_date.records[existing_row] = adate
                        ad_date.dirty = True
                for meta_key, col_stem in (
                    ("description", "albumdata_description"),
                    ("location", "albumdata_location"),
                    ("music", "albumdata_music"),
                ):
                    meta_val = str(alb_meta.get(meta_key) or "")
                    if meta_val and col_stem in albumdata_tables:
                        ad_col = albumdata_tables[col_stem]
                        if ad_col.records[existing_row] != meta_val:
                            ad_col.records[existing_row] = meta_val
                            ad_col.dirty = True
                updated_or_added += 1
            else:
                for stem, pmp in albumdata_tables.items():
                    if stem == "albumdata_name":
                        pmp.records.append(aname)
                    elif stem == "albumdata_token":
                        pmp.records.append(canonical_tok)
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
                    pmp.dirty = True
                existing_token_to_row[tok_clean] = len(ad_name.records) - 1
                updated_or_added += 1

        return updated_or_added

    def index_folder(self, folder_path: str) -> int:
        """
        FR: Indexe ou récupère un enregistrement de dossier (type == 1) dans thumbindex.db
        et positionne imagedata_filetype = 1 conformément à picasa3.exe.
        EN: Indexes or retrieves a folder record (type == 1) in thumbindex.db
        and sets imagedata_filetype = 1 matching picasa3.exe.
        Ref: picasa3.exe @ 0x004F54B0 (SaveThumbIndex), 0x00415790 (AVytDirScannerWindows)
        """
        with self.db._lock:
            folder_idx = self.db.get_or_create_folder_index(folder_path)
            if hasattr(self.db, "_align_imagedata_tables"):
                self.db._align_imagedata_tables(folder_idx)
            if "imagedata_filetype" in self.db.pmps:
                pmp_ft = self.db.pmps["imagedata_filetype"]
                while len(pmp_ft.records) <= folder_idx:
                    pmp_ft.records.append(pmp_ft.default_value())
                if pmp_ft.records[folder_idx] != 1:
                    pmp_ft.records[folder_idx] = 1
                    pmp_ft.dirty = True
            return folder_idx

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

        with self.db._lock:
            raw_records = [
                (i, r.type, r.path, r.parent_idx)
                for i, r in enumerate(self.db.index)
            ]
        folders_map = {i: path for i, rtype, path, _ in raw_records if rtype == 1}
        allowed_folders_norm: Optional[Set[str]] = None
        if folder_paths:
            allowed_folders_norm = {
                os.path.abspath(p.replace("\\", os.sep) if os.sep != "\\" else p).replace("/", "\\").rstrip("\\").lower()
                for p in folder_paths if p
            }

        deleted_photo_indices: Set[int] = set()
        newly_deleted_indices: List[int] = []
        deleted_count = 0
        is_bg_thread = threading.current_thread() is not threading.main_thread()

        for idx, rtype, rpath, rparent in raw_records:
            if is_bg_thread and idx > 0 and (idx % 64) == 0:
                BackgroundScanWorker.yield_for_gui(0.001)
            if rtype == 0:
                deleted_photo_indices.add(idx)
                continue
            if rtype not in (2, 3, 4, 6, 7, 8, 13, 18, 31, 32):
                continue
            fdir = folders_map.get(rparent, "")
            if not fdir:
                continue
            host_fdir = fdir.replace("\\", os.sep) if os.sep != "\\" else fdir
            norm_fdir = os.path.abspath(host_fdir).replace("/", "\\").rstrip("\\").lower()
            if allowed_folders_norm is not None and not any(
                norm_fdir == af or norm_fdir.startswith(af + "\\") for af in allowed_folders_norm
            ):
                continue
            full_path = os.path.join(host_fdir, rpath)
            if not os.path.exists(full_path):
                newly_deleted_indices.append(idx)
                deleted_photo_indices.add(idx)
                deleted_count += 1

        if newly_deleted_indices:
            with self.db._lock:
                del_set = getattr(self.db, "_deleted_or_reset_indices", None)
                for idx in newly_deleted_indices:
                    if 0 <= idx < len(self.db.index):
                        rec = self.db.index[idx]
                        rec.type = 0
                        rec.path = ""
                        rec.parent_idx = 0xFFFFFFFF
                        self.db.thumbindex.dirty = True
                        if isinstance(del_set, set):
                            del_set.add(idx)
                        for col_name in (
                            "imagedata_personalbumrecs",
                            "imagedata_personalbumrecs2",
                            "imagedata_aliasparents",
                        ):
                            pmp = self.db.pmps.get(col_name)
                            if pmp is not None and idx < len(pmp.records) and pmp.records[idx] != 0:
                                pmp.records[idx] = 0
                                pmp.dirty = True
                for c_idx, c_rec in enumerate(self.db.index):
                    if c_rec.type == 1001 and c_rec.parent_idx in deleted_photo_indices:
                        c_rec.type = 0
                        c_rec.path = ""
                        c_rec.parent_idx = 0xFFFFFFFF
                        self.db.thumbindex.dirty = True
                        if isinstance(del_set, set):
                            del_set.add(c_idx)
                        for col_name in (
                            "imagedata_facerect",
                            "imagedata_personalbumid",
                            "imagedata_suggestionpersonalbumid",
                            "imagedata_personalbumrecs",
                            "imagedata_personalbumrecs2",
                            "imagedata_aliasparents",
                        ):
                            pmp = self.db.pmps.get(col_name)
                            if pmp is not None and c_idx < len(pmp.records):
                                pmp.records[c_idx] = 0
                                pmp.dirty = True
                if hasattr(self.db, "_invalidate_path_index_cache"):
                    self.db._invalidate_path_index_cache()
                if hasattr(self.db, "invalidate_search_cache"):
                    self.db.invalidate_search_cache()

        self._last_deleted_count = deleted_count
        return deleted_count

    def find_unindexed_files(self, folder_paths: List[str], is_cancelled=None) -> List[str]:
        """
        FR: Compare les fichiers du disque avec ceux déjà enregistrés dans thumbindex.db
        et renvoie la liste des nouveaux fichiers à indexer.
        EN: Compares files on disk against those already recorded in thumbindex.db
        and returns the list of new files to index.
        Ref: picasa3.exe @ 0x00415790 — reconnaît tous les types médias (2, 3, 4, 6, 7, 8, 13, 18, 31, 32).
        """
        # FR: Cartographier l'existant : (folder_norm, filename_lower) hors verrou global
        # EN: Map existing indexed records: (folder_norm, filename_lower) outside global lock
        with self.db._lock:
            raw_records = [
                (i, r.type, r.path, r.parent_idx, getattr(r, "ft2", 0))
                for i, r in enumerate(self.db.index)
            ]
        indexed: Set[Tuple[str, str]] = set()
        folders_map = {i: path for i, rtype, path, _, _ in raw_records if rtype == 1}
        folder_ft2_by_norm = {
            path.replace("/", "\\").rstrip("\\").lower(): ft2
            for _, rtype, path, _, ft2 in raw_records
            if rtype == 1 and path
        }

        for _, rtype, rpath, rparent, _ in raw_records:
            if rtype in (2, 3, 4, 6, 7, 8, 13, 18, 31, 32):
                fpath = folders_map.get(rparent, "")
                norm_f = fpath.replace("/", "\\").rstrip("\\").lower()
                indexed.add((norm_f, rpath.lower()))

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
                    f_ft2 = folder_ft2_by_norm.get(parent_dir, 0)
                    if f_ft2 > 0:
                        try:
                            file_ft1, file_ft2, _ = file_filetimes(file_path)
                            if (file_ft2 <= f_ft2 + 600_000_000 or file_ft1 <= f_ft2) and extract_media_metadata_and_thumb(file_path) is None:
                                continue
                        except Exception:
                            pass
                    unindexed.append(file_path)

        with self.db._lock:
            self._last_synced_albums_count = self._sync_ini_albums_to_pmp()
        return unindexed

    def find_modified_files(self, folder_paths: List[str], is_cancelled=None) -> List[Tuple[int, str]]:
        """
        FR: Détecte les fichiers déjà indexés dont la date de modification (mtime) ou la taille
        sur disque a changé par rapport à thumbindex.db.
        Copie les tuples bruts sous `with self.db._lock:` en < 1 ms, puis effectue la normalisation
        des chemins et les appels disque hors verrou.
        EN: Detects already-indexed files whose modification time (mtime) or file size
        on disk has changed compared to thumbindex.db.
        Copies raw tuples under `with self.db._lock:` in < 1 ms, then performs path normalization
        and disk stat calls outside the lock.
        Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows)
        """
        with self.db._lock:
            raw_records = [
                (i, rec.type, rec.path, rec.parent_idx, rec.mod_time, rec.file_size, getattr(rec, "mtime", 0))
                for i, rec in enumerate(self.db.index)
            ]
        folders_map: Dict[int, str] = {}
        folders_norm_map: Dict[int, Tuple[str, str]] = {}
        for i, rtype, rpath, _, _, _, _ in raw_records:
            if rtype == 1:
                folders_map[i] = rpath
                host_fdir = rpath.replace("\\", os.sep) if os.sep != "\\" else rpath
                norm_fdir = os.path.normcase(os.path.normpath(os.path.abspath(host_fdir))).replace("/", "\\").rstrip("\\").lower()
                folders_norm_map[i] = (host_fdir, norm_fdir)

        allowed_folders_norm: Set[str] = {
            os.path.normcase(os.path.normpath(os.path.abspath(p.replace("\\", os.sep) if os.sep != "\\" else p))).replace("/", "\\").rstrip("\\").lower()
            for p in folder_paths if p
        }
        modified: List[Tuple[int, str]] = []
        is_bg_thread = threading.current_thread() is not threading.main_thread()
        for idx, rtype, rpath, rparent, _, r_fsize, r_mtime in raw_records:
            if is_cancelled and is_cancelled():
                break
            if is_bg_thread and idx > 0 and (idx % 64) == 0:
                BackgroundScanWorker.yield_for_gui(0.001)
            if rtype not in (2, 3, 4, 6, 7, 8, 13, 18, 31, 32):
                continue
            fnorm_pair = folders_norm_map.get(rparent)
            if not fnorm_pair:
                continue
            host_fdir, norm_fdir = fnorm_pair
            if allowed_folders_norm and not any(
                norm_fdir == af or norm_fdir.startswith(af + "\\") for af in allowed_folders_norm
            ):
                continue
            full_path = os.path.join(host_fdir, rpath)
            if not os.path.exists(full_path):
                continue
            try:
                disk_mtime = int(os.path.getmtime(full_path))
                disk_size = os.path.getsize(full_path) & 0xFFFFFFFF
                if r_fsize and (disk_size != (r_fsize & 0xFFFFFFFF) or abs(disk_mtime - (r_mtime or disk_mtime)) > 2):
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
        ft1_val, ft2_val, fsize = file_filetimes(file_path)
        is_video_rec = int(self.db.index[record_idx].type) == 32 or os.path.splitext(file_path)[1].lower() in VIDEO_EXTENSIONS
        # Ref: picasa3.exe @ 0x00513741..0x0051374A — préserve imagedata_originfast s'il est déjà non nul ; 0 pour les vidéos
        existing_ofast = 0
        if not is_video_rec and "imagedata_originfast" in self.db.pmps:
            ofast_recs = self.db.pmps["imagedata_originfast"].records
            if record_idx < len(ofast_recs):
                existing_ofast = int(ofast_recs[record_idx] or 0)
        originfast_val = 0 if is_video_rec else (existing_ofast if existing_ofast != 0 else compute_originfast_hash(file_path))

        t2_bytes: Optional[bytes] = getattr(meta, "thumb2_bytes", None)
        if not t2_bytes and jpeg_bytes and "thumbs2" in getattr(self.db, "block_indices", {}):
            try:
                with Image.open(io.BytesIO(jpeg_bytes)) as t_img:
                    t2 = _fit_long_side(t_img.convert("RGB"), 72, t_img.size)
                    b2 = io.BytesIO()
                    t2.save(b2, format="JPEG", quality=90)
                    t2_bytes = b2.getvalue()
            except Exception:
                t2_bytes = jpeg_bytes

        bigthumb_bytes: Optional[bytes] = getattr(meta, "bigthumb_bytes", None)

        avg_u32: Optional[int] = 0 if is_video_rec else None
        color_toks: List[str] = []
        if jpeg_bytes and not is_video_rec:
            try:
                with Image.open(io.BytesIO(jpeg_bytes)) as t_img:
                    rgb_t = t_img.convert("RGB")
                    if "imagedata_avgcolor" in self.db.pmps:
                        avg_u32 = compute_thumbnail_avgcolor(rgb_t)
                    color_toks = classify_image_color_tokens(rgb_t)
            except Exception:
                avg_u32 = None

        with self.db._lock:
            rec = self.db.index[record_idx]
            rec.file_size = fsize
            rec.ft1 = ft1_val
            rec.ft2 = ft2_val
            rec_type = int(rec.type)
            if self.db.thumbindex is not None:
                self.db.thumbindex.dirty = True
            if hasattr(self.db, "_align_imagedata_tables"):
                self.db._align_imagedata_tables(record_idx)

            def _set_pmp_col(col_name: str, val) -> None:
                if col_name in self.db.pmps:
                    pmp_obj = self.db.pmps[col_name]
                    def_v = pmp_obj.default_value()
                    while len(pmp_obj.records) <= record_idx:
                        pmp_obj.records.append(def_v)
                    pmp_obj.records[record_idx] = val
                    pmp_obj.dirty = True

            _set_pmp_col("imagedata_width", w)
            _set_pmp_col("imagedata_height", h)
            # Ref: db3 — imagedata_tagdate = 0 pour les images au scan (2931/2931), date de modification
            # en heure locale pour les vidéos (199/199)
            _set_pmp_col("imagedata_tagdate", float(ole_date) if is_video_rec else 0.0)
            _set_pmp_col("imagedata_filetype", rec_type)
            _set_pmp_col("imagedata_fileflags", 1 if rec_type == 18 else 0)
            _set_pmp_col("imagedata_originfast", originfast_val)
            _set_pmp_col("imagedata_colorspace", 0)
            # Ref: db3 — les vidéos (type 32) gardent 0 dans personalbumrecs/recs2 (les images : 0xFFFFFFFF)
            _rec_default = 0 if rec_type == 32 else 0xFFFFFFFF
            _set_pmp_col("imagedata_personalbumrecs", _rec_default)
            _set_pmp_col("imagedata_personalbumrecs2", _rec_default)
            if avg_u32 is not None:
                _set_pmp_col("imagedata_avgcolor", avg_u32)

            gps_lat = getattr(meta, "lat", None)
            gps_lon = getattr(meta, "lon", None)
            if gps_lat is not None and gps_lon is not None:
                _set_pmp_col("imagedata_lat", float(gps_lat))
                _set_pmp_col("imagedata_long", float(gps_lon))

            if getattr(self.db, "wordhash", None) is not None:
                folder_p = os.path.dirname(file_path).replace("/", "\\").rstrip("\\") + "\\"
                folder_alb_tok = (
                    self.db.ensure_folder_album_row(folder_p)
                    if hasattr(self.db, "ensure_folder_album_row") and not is_video_rec
                    else ""
                )
                for tok in wordhash_tokens_for_media(
                    os.path.basename(file_path), w, h, rec_type, folder_alb_tok, color_toks
                ):
                    self.db.wordhash.add_word(tok, record_idx)
                if gps_lat is not None and gps_lon is not None and (float(gps_lat) != 0.0 or float(gps_lon) != 0.0):
                    self.db.wordhash.add_word("]geo", record_idx)

        # FR: Écritures de miniatures HORS de `with self.db._lock:` (protégées par `_get_block_lock(prefix)`)
        # EN: Thumbnail writes OUTSIDE `with self.db._lock:` (protected by `_get_block_lock(prefix)`)
        self.db.add_thumbnail(record_idx, jpeg_bytes, size="small")
        # Ref: db3 — pas de thumbs2 pour les vidéos (199/199 absents)
        if "thumbs2" in getattr(self.db, "block_indices", {}) and not is_video_rec:
            self.db.add_thumbnail(record_idx, t2_bytes or jpeg_bytes, size="medium")
        # Ref: db3 — bigthumbs/previews ne sont créés qu'à la demande (476/3130) : on ne rafraîchit
        # qu'une entrée bigthumbs déjà existante.
        bt_idx = getattr(self.db, "block_indices", {}).get("bigthumbs")
        if bt_idx is not None and record_idx < bt_idx.record_count and bigthumb_bytes:
            bt_entry = bt_idx.get_entry(record_idx)
            if bt_entry is not None and bt_entry.offset:
                self.db.add_thumbnail(record_idx, bigthumb_bytes, size="large")

        if hasattr(self.db, "sync_photo_ini_to_db"):
            try:
                self.db.sync_photo_ini_to_db(record_idx)
            except Exception:
                pass
        mod_set = getattr(self.db, "_modified_media_indices", None)
        if isinstance(mod_set, set):
            mod_set.add(record_idx)
        if hasattr(self.db, "invalidate_search_cache"):
            self.db.invalidate_search_cache()
        return True

    def index_file(self, file_path: str) -> Optional[int]:
        """
        FR: Génère la vignette et insère l'enregistrement dans la base Picasa
        (en conservant strictement le séparateur '\\' dans thumbindex.db).
        Les écritures de miniatures dans CBlockFile sont effectuées en dehors de `self.db._lock`.
        EN: Generates the thumbnail and inserts the record into the Picasa database
        (strictly preserving the '\\' separator inside thumbindex.db).
        Thumbnail writes into CBlockFile are performed outside `self.db._lock`.
        """
        ext = os.path.splitext(file_path)[1].lower()
        media_type = detect_media_type(file_path)
        folder_path = os.path.dirname(file_path).replace("/", "\\").rstrip("\\") + "\\"
        filename = os.path.basename(file_path)

        meta = extract_media_metadata_and_thumb(file_path)
        if not meta:
            return None

        jpeg_bytes, w, h, ole_date = meta
        ft1_val, ft2_val, file_size = file_filetimes(file_path)
        is_video_rec = media_type == 32
        # Ref: db3 — originfast = 0 pour les vidéos (199/199)
        originfast_val = 0 if is_video_rec else compute_originfast_hash(file_path)

        t2_bytes: Optional[bytes] = getattr(meta, "thumb2_bytes", None)
        if not t2_bytes and jpeg_bytes and "thumbs2" in getattr(self.db, "block_indices", {}):
            try:
                with Image.open(io.BytesIO(jpeg_bytes)) as t_img:
                    t2 = _fit_long_side(t_img.convert("RGB"), 72, t_img.size)
                    b2 = io.BytesIO()
                    t2.save(b2, format="JPEG", quality=90)
                    t2_bytes = b2.getvalue()
            except Exception:
                t2_bytes = jpeg_bytes

        bigthumb_bytes: Optional[bytes] = getattr(meta, "bigthumb_bytes", None)

        avg_u32: Optional[int] = 0 if is_video_rec else None
        color_toks: List[str] = []
        if jpeg_bytes and not is_video_rec:
            try:
                with Image.open(io.BytesIO(jpeg_bytes)) as t_img:
                    rgb_t = t_img.convert("RGB")
                    if "imagedata_avgcolor" in self.db.pmps:
                        avg_u32 = compute_thumbnail_avgcolor(rgb_t)
                    color_toks = classify_image_color_tokens(rgb_t)
            except Exception:
                avg_u32 = None

        # 1. Enregistrement thumbindex.db et colonnes PMP sous verrou DB / thumbindex.db record and PMP columns under DB lock
        with self.db._lock:
            record_idx = self.db.add_media_record(
                folder_path=folder_path,
                filename=filename,
                file_size=file_size,
                mtime=ft2_val,
                media_type=media_type,
            )
            # FR: ft1 = date de création exacte (FILETIME), ft2 = dernière écriture exacte
            # EN: ft1 = exact creation time (FILETIME), ft2 = exact last write time
            new_rec = self.db.index[record_idx]
            new_rec.ft1 = ft1_val
            new_rec.ft2 = ft2_val
            if hasattr(self.db, "_align_imagedata_tables"):
                self.db._align_imagedata_tables(record_idx)

            # 2. Colonnes PMP (imagedata_width, imagedata_height, imagedata_tagdate, imagedata_filetype, imagedata_fileflags, imagedata_originfast, imagedata_colorspace, imagedata_facerect, imagedata_avgcolor, imagedata_lat, imagedata_long)
            # Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows / alignement strict des lignes PMP), 0x004280D8, 0x00A4D210
            def _set_pmp_col(col_name: str, val) -> None:
                if col_name in self.db.pmps:
                    pmp_obj = self.db.pmps[col_name]
                    def_v = pmp_obj.default_value()
                    while len(pmp_obj.records) <= record_idx:
                        pmp_obj.records.append(def_v)
                    pmp_obj.records[record_idx] = val
                    pmp_obj.dirty = True

            _set_pmp_col("imagedata_width", w)
            _set_pmp_col("imagedata_height", h)
            # Ref: db3 — imagedata_tagdate = 0 pour les images au scan (2931/2931), date de modification
            # en heure locale pour les vidéos (199/199)
            _set_pmp_col("imagedata_tagdate", float(ole_date) if is_video_rec else 0.0)
            _set_pmp_col("imagedata_filetype", media_type)
            _set_pmp_col("imagedata_fileflags", 0)
            _set_pmp_col("imagedata_originfast", originfast_val)
            _set_pmp_col("imagedata_colorspace", 0)
            _set_pmp_col("imagedata_facerect", 0)
            # Ref: db3 — les vidéos (type 32) gardent 0 dans personalbumrecs/recs2 (les images : 0xFFFFFFFF)
            _rec_default = 0 if is_video_rec else 0xFFFFFFFF
            _set_pmp_col("imagedata_personalbumrecs", _rec_default)
            _set_pmp_col("imagedata_personalbumrecs2", _rec_default)

            if avg_u32 is not None:
                _set_pmp_col("imagedata_avgcolor", avg_u32)

            gps_lat = getattr(meta, "lat", None)
            gps_lon = getattr(meta, "lon", None)
            if gps_lat is not None and gps_lon is not None:
                _set_pmp_col("imagedata_lat", float(gps_lat))
                _set_pmp_col("imagedata_long", float(gps_lon))

            folder_alb_tok = (
                self.db.ensure_folder_album_row(folder_path)
                if hasattr(self.db, "ensure_folder_album_row") and not is_video_rec
                else ""
            )
            if getattr(self.db, "wordhash", None) is not None:
                for tok in wordhash_tokens_for_media(
                    filename, w, h, media_type, folder_alb_tok, color_toks
                ):
                    self.db.wordhash.add_word(tok, record_idx)
                if gps_lat is not None and gps_lon is not None and (float(gps_lat) != 0.0 or float(gps_lon) != 0.0):
                    self.db.wordhash.add_word("]geo", record_idx)

        # 3. Miniatures thumbs_0.db (144px, q=90) et thumbs2_0.db (72px, q=90), HORS de `with self.db._lock:`
        #    Ref: db3 — pas de thumbs2 pour les vidéos ; bigthumbs/previews créés à la demande seulement (476/3130)
        #    EN: thumbs_0.db (144px) and thumbs2_0.db (72px) thumbnails OUTSIDE `with self.db._lock:`;
        #    no thumbs2 for videos, bigthumbs/previews created on demand only.
        self.db.add_thumbnail(record_idx, jpeg_bytes, size="small")
        if "thumbs2" in getattr(self.db, "block_indices", {}) and not is_video_rec:
            self.db.add_thumbnail(record_idx, t2_bytes or jpeg_bytes, size="medium")

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
        for fpath in self.find_unindexed_files(folders):
            if self.index_file(fpath) is not None:
                pass
        changed = getattr(self, "_last_deleted_count", 0)
        # Recompute total changed count from indexed + modified
        # Note: find_unindexed_files already called _check_deleted_records and _sync_ini_albums_to_pmp
        return changed


class BackgroundScanWorker(QThread):
    """
    FR: Thread de travail en arrière-plan à basse priorité (`QThread.Priority.LowPriority`)
    pour l'auto-indexation et la génération de miniatures sans jamais bloquer l'interface graphique.
    Cède systématiquement le GIL après chaque photo et met en pause son activité dès que
    l'utilisateur interagit avec l'interface (défilement, sélection, édition).
    EN: Low-priority background worker thread (`QThread.Priority.LowPriority`)
    for auto-indexing and thumbnail generation without ever blocking the GUI thread.
    Yields the GIL after every photo and automatically throttles/pauses whenever
    the user is actively interacting with the GUI (scrolling, selecting, editing).
    Ref: picasa3.exe @ 0x00415790 (AVytDirScannerWindows), 0x00797AF0 (CDirectoryScanner)
    """
    progress = Signal(int, int, str)       # (current, total, filename)
    file_indexed = Signal(str, str)        # (folder_path, filename)
    batch_indexed = Signal(str, str, int, int)  # (folder_path, filename, db_idx, batch_count)
    finished = Signal(int)                 # (total_added_or_updated)

    # FR: Horodatage monotone de la dernière activité GUI pour donner priorité absolue à l'UI
    # EN: Monotonic timestamp of the latest GUI interaction to give absolute priority to the UI
    # Ref: picasa3.exe @ 0x005E4F6E (QueryPerformanceCounter stored at *(double *)(db + 0x2da8))
    _last_gui_activity_ts: float = 0.0

    @classmethod
    def notify_gui_activity(cls) -> None:
        """
        FR: Signale une interaction utilisateur (défilement, clic, clavier, édition) afin que tous les
        workers d'arrière-plan cèdent immédiatement le CPU, le GIL et le disque au thread GUI.
        EN: Signals a user interaction (scroll, click, key press, edit) so all background workers
        immediately yield CPU, GIL, and disk bandwidth to the GUI thread.
        Ref: picasa3.exe @ 0x005E4AC0, 0x005E4F6E (decompiled_5e5290.c:176-202)
        """
        cls._last_gui_activity_ts = time.monotonic()

    @classmethod
    def is_gui_active(cls, window_s: float = 0.35) -> bool:
        """
        FR: Indique si l'utilisateur a interagi avec l'interface au cours des `window_s` dernières secondes.
        EN: Returns whether the user has interacted with the GUI within the last `window_s` seconds.
        Ref: picasa3.exe @ 0x005E4F6E (*(double *)(db + 0x2da8))
        """
        return (time.monotonic() - cls._last_gui_activity_ts) < window_s

    @classmethod
    def yield_for_gui(cls, base_sleep_s: float = 0.002) -> None:
        """
        FR: Cède le GIL après chaque unité de travail et met en pause le worker tant que l'utilisateur
        interagit activement avec la GUI (fenêtre de 350 ms après tout événement souris/clavier/scroll).
        EN: Yields the GIL after each work unit and pauses the worker while the user is actively
        interacting with the GUI (350 ms window after any mouse/keyboard/scroll event).
        Ref: picasa3.exe @ 0x005E4F6E, 0x00415790 (decomp_dir_scanner_ctor.c:486)
        """
        now = time.monotonic()
        elapsed = now - cls._last_gui_activity_ts
        if elapsed < 0.35:
            wait_end = now + min(0.15, 0.35 - elapsed)
            while time.monotonic() < wait_end and (time.monotonic() - cls._last_gui_activity_ts) < 0.35:
                time.sleep(0.025)
        elif base_sleep_s > 0.0:
            time.sleep(base_sleep_s)

    def __init__(self, db: PicasaDatabase, folder_paths: List[str], parent=None):
        """
        FR: Initialise le thread d'analyse avec la base Picasa et la liste des dossiers à scanner.
        EN: Initializes the scan worker thread with the Picasa database and folder list to scan.
        """
        super().__init__(parent)
        self.db = db
        self.folder_paths = folder_paths
        self._is_cancelled = False

    def start(self, priority: QThread.Priority = QThread.Priority.LowPriority) -> None:
        """
        FR: Démarre le thread avec une priorité OS basse (`LowPriority`) pour ne jamais
        préempter le thread GUI principal.
        EN: Starts the thread with `LowPriority` OS scheduling so it never preempts
        the main GUI thread.
        """
        super().start(priority)

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
        FR: Exécute l'indexation des nouveaux fichiers et la mise à jour des fichiers modifiés
        en cédant le GIL à chaque fichier et en régulant les signaux UI pour les grands dossiers.
        EN: Executes indexing of new files and updating of modified files while yielding
        the GIL on every file and throttling UI signals for large folders.
        Ref: picasa3.exe @ 0x00415790 (CDirScanner -> SetThreadPriority(THREAD_PRIORITY_BELOW_NORMAL))
        """
        if self.isRunning():
            set_current_thread_background_priority(lowest=False)
        scanner = PicasaDirScanner(self.db)
        to_index = scanner.find_unindexed_files(self.folder_paths, is_cancelled=lambda: self._is_cancelled)
        to_update = scanner.find_modified_files(self.folder_paths, is_cancelled=lambda: self._is_cancelled)

        total = len(to_index) + len(to_update)
        changed = getattr(scanner, "_last_deleted_count", 0)
        is_running_thread = self.isRunning()
        throttle_signals = is_running_thread and total > 20
        last_progress_emit = 0.0
        pending_by_folder: Dict[str, Tuple[str, int, int]] = {}  # folder -> (last_fname, last_idx, count)

        def _flush_pending_batches(force: bool = False) -> None:
            nonlocal last_progress_emit
            now = time.monotonic()
            if not force and (now - last_progress_emit) < 0.15:
                return
            last_progress_emit = now
            for fdir, (l_fname, l_idx, b_cnt) in list(pending_by_folder.items()):
                self.batch_indexed.emit(fdir, l_fname, l_idx, b_cnt)
                if not throttle_signals:
                    self.file_indexed.emit(fdir, l_fname)
            pending_by_folder.clear()

        for i, fpath in enumerate(to_index):
            if self._is_cancelled:
                break

            if is_running_thread:
                self.yield_for_gui(0.002)

            fname = os.path.basename(fpath)
            now = time.monotonic()
            if not throttle_signals or i == 0 or (i + 1) == total or (now - last_progress_emit) >= 0.12:
                self.progress.emit(i + 1, total, fname)

            idx = scanner.index_file(fpath)
            if idx is not None:
                changed += 1
                fdir = os.path.dirname(fpath)
                if not throttle_signals:
                    self.file_indexed.emit(fdir, fname)
                    self.batch_indexed.emit(fdir, fname, idx, 1)
                else:
                    prev = pending_by_folder.get(fdir)
                    prev_cnt = prev[2] if prev is not None else 0
                    pending_by_folder[fdir] = (fname, idx, prev_cnt + 1)
                    if (now - last_progress_emit) >= 0.15 or (i + 1) == len(to_index):
                        _flush_pending_batches(force=True)

        offset = len(to_index)
        for j, (rec_idx, fpath) in enumerate(to_update):
            if self._is_cancelled:
                break

            if is_running_thread:
                self.yield_for_gui(0.002)

            fname = os.path.basename(fpath)
            now = time.monotonic()
            if not throttle_signals or j == 0 or (offset + j + 1) == total or (now - last_progress_emit) >= 0.12:
                self.progress.emit(offset + j + 1, total, fname)
            if scanner.update_indexed_file(rec_idx, fpath):
                changed += 1
                fdir = os.path.dirname(fpath)
                if not throttle_signals:
                    self.file_indexed.emit(fdir, fname)
                    self.batch_indexed.emit(fdir, fname, rec_idx, 1)
                else:
                    prev = pending_by_folder.get(fdir)
                    prev_cnt = prev[2] if prev is not None else 0
                    pending_by_folder[fdir] = (fname, rec_idx, prev_cnt + 1)
                    if (now - last_progress_emit) >= 0.15 or (j + 1) == len(to_update):
                        _flush_pending_batches(force=True)

        if self._is_cancelled:
            return

        if pending_by_folder:
            _flush_pending_batches(force=True)

        with self.db._lock:
            alb_synced = scanner._sync_ini_albums_to_pmp()
        if alb_synced > 0 and changed == 0 and not self._is_cancelled:
            try:
                self.db.save_database()
            except Exception:
                pass

        # FR: Sauvegarder les modifications atomiquement sur disque / EN: Save changes atomically to disk
        if changed > 0 and not self._is_cancelled:
            try:
                self.db.save_database()
            except Exception:
                pass

        if not self._is_cancelled:
            self.finished.emit(changed)


