"""
Module d'extraction et de formatage des métadonnées EXIF et de géolocalisation pour PyCasa.

Ref: picasa3.exe @ IMAGEPROPERTIES.XML, imageproperties.fen
Ref: picasa3.exe @ 0x00889210 (EXIF parsing & display strings)
Ref: AGENTS.md §4 bis (Propriétés de l'image fidèles à l'original)
"""

from __future__ import annotations
import os
from datetime import datetime
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ExifTags

Image.MAX_IMAGE_PIXELS = None


def format_filesize(size_bytes: int) -> str:
    """Formate une taille de fichier en Ko ou Mo selon la convention Picasa."""
    if size_bytes < 1024:
        return f"{size_bytes} octets"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} Ko".replace(".", ",")
    else:
        return f"{size_bytes / (1024 * 1024):.1f} Mo".replace(".", ",")


def format_exposure_time(val: Any) -> str:
    """Formate un temps d'exposition en fraction lisible (ex: 1/125 s)."""
    try:
        f = float(val)
        if f <= 0:
            return str(val)
        if f >= 1.0:
            return f"{f:.1f} s".replace(".", ",")
        # Fraction standard
        frac = Fraction(f).limit_denominator(8000)
        return f"1/{round(1.0 / f)} s"
    except Exception:
        return str(val)


def format_f_number(val: Any) -> str:
    """Formate une valeur d'ouverture f (ex: f/2.8)."""
    try:
        f = float(val)
        return f"f/{f:.1f}" if f != int(f) else f"f/{int(f)}"
    except Exception:
        return str(val)


def format_focal_length(val: Any) -> str:
    """Formate une distance focale (ex: 50,0 mm)."""
    try:
        f = float(val)
        return f"{f:.1f} mm".replace(".", ",")
    except Exception:
        return str(val)


def parse_gps_coordinates(exif: Any) -> Optional[Tuple[float, float, Optional[float]]]:
    """
    Extrait les coordonnées GPS en degrés décimaux depuis les métadonnées EXIF.
    Renvoie (latitude, longitude, altitude_m).
    """
    try:
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        if not gps_ifd:
            return None

        # 1: GPSLatitudeRef, 2: GPSLatitude, 3: GPSLongitudeRef, 4: GPSLongitude, 6: GPSAltitude
        lat_raw = gps_ifd.get(2)
        lat_ref = gps_ifd.get(1, "N")
        lon_raw = gps_ifd.get(4)
        lon_ref = gps_ifd.get(3, "E")
        alt_raw = gps_ifd.get(6)

        if not lat_raw or not lon_raw:
            return None

        def dms_to_dec(dms: Any) -> float:
            d = float(dms[0])
            m = float(dms[1])
            s = float(dms[2])
            return d + (m / 60.0) + (s / 3600.0)

        lat = dms_to_dec(lat_raw)
        if str(lat_ref).upper() == "S":
            lat = -lat

        lon = dms_to_dec(lon_raw)
        if str(lon_ref).upper() == "W":
            lon = -lon

        alt = float(alt_raw) if alt_raw is not None else None
        return (lat, lon, alt)
    except Exception:
        return None


def format_gps_dms(lat: float, lon: float, alt: Optional[float] = None) -> str:
    """Formate les coordonnées en DMS (Degrés Minutes Secondes) pour l'affichage."""
    lat_card = "N" if lat >= 0 else "S"
    lat_abs = abs(lat)
    lat_deg = int(lat_abs)
    lat_min = int((lat_abs - lat_deg) * 60)
    lat_sec = ((lat_abs - lat_deg) * 60 - lat_min) * 60

    lon_card = "E" if lon >= 0 else "W"
    lon_abs = abs(lon)
    lon_deg = int(lon_abs)
    lon_min = int((lon_abs - lon_deg) * 60)
    lon_sec = ((lon_abs - lon_deg) * 60 - lon_min) * 60

    res = f"{lat_deg}° {lat_min}' {lat_sec:.1f}\" {lat_card}, {lon_deg}° {lon_min}' {lon_sec:.1f}\" {lon_card}"
    if alt is not None:
        res += f" • Alt: {alt:.0f} m"
    return res


def extract_full_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extrait l'ensemble des informations de base, propriétés EXIF et GPS d'une photo.
    """
    data: Dict[str, Any] = {
        "filename": os.path.basename(file_path),
        "folder": os.path.dirname(file_path),
        "filesize": "—",
        "date": "—",
        "dimensions": (0, 0),
        "resolution": "—",
        "camera": "—",
        "gps": None,
        "gps_formatted": "—",
        "properties": [],
    }

    if not os.path.exists(file_path):
        return data

    try:
        sz = os.path.getsize(file_path)
        data["filesize"] = format_filesize(sz)
    except Exception:
        pass

    try:
        mtime = os.path.getmtime(file_path)
        dt = datetime.fromtimestamp(mtime)
        data["date"] = dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        pass

    try:
        with Image.open(file_path) as img:
            data["dimensions"] = img.size
            w, h = img.size
            mp = (w * h) / 1_000_000.0
            data["resolution"] = f"{w} × {h} ({mp:.1f} MP)"

            props: List[Tuple[str, str]] = []
            props.append(("Nom du fichier", data["filename"]))
            props.append(("Emplacement", data["folder"]))
            props.append(("Taille du fichier", data["filesize"]))
            props.append(("Dimensions", f"{w} × {h} pixels"))
            props.append(("Mégapixels", f"{mp:.1f} MP"))

            exif = img.getexif()
            if exif:
                # Récupérer les tags EXIF de base
                make = str(exif.get(0x010F, "")).strip()  # Make
                model = str(exif.get(0x0110, "")).strip()  # Model
                if model:
                    data["camera"] = f"{make} {model}".strip() if make and make not in model else model
                    props.append(("Appareil photo", data["camera"]))

                date_taken = exif.get(0x9003) or exif.get(0x0132)
                if date_taken and isinstance(date_taken, str):
                    try:
                        clean_dt = datetime.strptime(date_taken.strip()[:19], "%Y:%m:%d %H:%M:%S")
                        data["date"] = clean_dt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        pass
                props.append(("Date de prise de vue", data["date"]))

                # IFD EXIF étendu
                try:
                    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                except Exception:
                    exif_ifd = {}

                if exif_ifd:
                    # Temps de pose / Vitesse d'obturation
                    exp_time = exif_ifd.get(0x829A)
                    if exp_time is not None:
                        props.append(("Vitesse d'obturation", format_exposure_time(exp_time)))

                    # Ouverture F-Number
                    f_num = exif_ifd.get(0x829D)
                    if f_num is not None:
                        props.append(("Ouverture", format_f_number(f_num)))

                    # Sensibilité ISO
                    iso = exif_ifd.get(0x8827)
                    if iso is not None:
                        props.append(("Sensibilité ISO", f"ISO {iso}"))

                    # Distance focale
                    focal = exif_ifd.get(0x920A)
                    if focal is not None:
                        props.append(("Distance focale", format_focal_length(focal)))

                    # Focale équivalente 35mm
                    focal_35 = exif_ifd.get(0xA405)
                    if focal_35:
                        props.append(("Équivalent 35mm", f"{focal_35} mm"))

                    # Flash
                    flash_val = exif_ifd.get(0x9209)
                    if flash_val is not None:
                        try:
                            fv = int(flash_val)
                            fired = (fv & 1) != 0
                            props.append(("Flash", "Déclenché" if fired else "Non déclenché"))
                        except Exception:
                            pass

                    # Balance des blancs
                    wb = exif_ifd.get(0xA403)
                    if wb is not None:
                        props.append(("Balance des blancs", "Automatique" if wb == 0 else "Manuelle"))

                # Coordonnées GPS
                gps_coords = parse_gps_coordinates(exif)
                if gps_coords:
                    data["gps"] = gps_coords
                    data["gps_formatted"] = format_gps_dms(gps_coords[0], gps_coords[1], gps_coords[2])
                    props.append(("Coordonnées GPS", data["gps_formatted"]))

                # Logiciel
                software = exif.get(0x0131)
                if software:
                    props.append(("Logiciel", str(software).strip()))

            data["properties"] = props

    except Exception:
        pass

    return data
