"""
FR : Structures et fonctions de décodage/encodage des coordonnées de visages Picasa (`rect64`).
EN: Structures and functions for decoding/encoding Picasa face coordinates (`rect64`).

Ref: picasa3.exe @ 0x009B9190 (FUN_009b9190 -> decode uint64 to rect coords)
Ref: picasa3.exe @ 0x009B91C0 (FUN_009b91c0 -> encode rect coords to uint64)
Ref: picasa3.exe @ 0x009B9247 (Format string "rect64(%I64x)")
Ref: picasa3.exe @ 0x009B9290 (Coordinate scaling to width & height)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, Union

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap


def decode_rect64_uint64(val: int) -> Tuple[float, float, float, float]:
    """
    FR : Décode un entier 64 bits en coordonnées normalisées `(0.0 .. 1.0)`.
    EN: Decode a 64-bit unsigned integer into normalized coordinates `(0.0 .. 1.0)`.
    Ref: picasa3.exe @ 0x009B9190
    w0 (left_u16)   = (val >> 48) & 0xFFFF
    w1 (top_u16)    = (val >> 32) & 0xFFFF
    w2 (right_u16)  = (val >> 16) & 0xFFFF
    w3 (bottom_u16) = val & 0xFFFF
    """
    w0 = (val >> 48) & 0xFFFF
    w1 = (val >> 32) & 0xFFFF
    w2 = (val >> 16) & 0xFFFF
    w3 = val & 0xFFFF
    return (w0 / 65535.0, w1 / 65535.0, w2 / 65535.0, w3 / 65535.0)


def encode_rect64_uint64(left: float, top: float, right: float, bottom: float) -> int:
    """
    FR : Encode des coordonnées normalisées en entier 64 bits (`uint64`).
    Applique le bornage strict de `FUN_009b9290` :
    - `left, top` dans `[0, 0xFFFE]`
    - `right, bottom` dans `[1, 0xFFFF]`
    - garantit `right > left` (`left = right - 1`) et `bottom > top` (`top = bottom - 1`).
    EN: Encode normalized coordinates into a 64-bit unsigned integer (`uint64`).
    Applies the strict clamping of `FUN_009b9290`:
    - `left, top` in `[0, 0xFFFE]`
    - `right, bottom` in `[1, 0xFFFF]`
    - guarantees `right > left` (`left = right - 1`) and `bottom > top` (`top = bottom - 1`).
    Ref: picasa3.exe @ 0x009B91C0, 0x009B9290 (FUN_009b91c0, FUN_009b9290)
    """
    l_int = max(0, min(0xFFFE, int(round(left * 65535.0))))
    t_int = max(0, min(0xFFFE, int(round(top * 65535.0))))
    r_int = max(1, min(0xFFFF, int(round(right * 65535.0))))
    b_int = max(1, min(0xFFFF, int(round(bottom * 65535.0))))
    if r_int <= l_int:
        l_int = r_int - 1
    if b_int <= t_int:
        t_int = b_int - 1
    return ((l_int & 0xFFFF) << 48) | ((t_int & 0xFFFF) << 32) | ((r_int & 0xFFFF) << 16) | (b_int & 0xFFFF)


def decode_rect64_string(s: str) -> Tuple[float, float, float, float]:
    """
    FR : Décode une chaîne de la forme `rect64(xxxxxxxx)`.
    EN: Decode a `rect64(xxxxxxxx)` formatted string.
    Ref: picasa3.exe @ 0x009B9247
    """
    clean = s.strip()
    if clean.lower().startswith("rect64(") and clean.endswith(")"):
        clean = clean[7:-1]
    val = int(clean, 16)
    return decode_rect64_uint64(val)


def encode_rect64_string(left: float, top: float, right: float, bottom: float) -> str:
    """
    FR : Encode des coordonnées normalisées sous forme de chaîne `rect64(%I64x)` (sans zéros en tête).
    EN: Encode normalized coordinates as a `rect64(%I64x)` string (without leading zeros).
    Ref: picasa3.exe @ 0x009B91C0, 0x009B9247 ("rect64(%I64x)")
    """
    val = encode_rect64_uint64(left, top, right, bottom)
    return f"rect64({val:x})"


decode_rect64 = decode_rect64_uint64
encode_rect64 = encode_rect64_uint64


@dataclass
class FaceRect:
    """
    FR : Rectangle de détection de visage avec coordonnées normalisées `[0.0 .. 1.0]`.
    EN: Face detection bounding rectangle with normalized `[0.0 .. 1.0]` coordinates.
    """

    left: float
    top: float
    right: float
    bottom: float
    contact_id: str = ""
    contact_name: Optional[str] = None
    record_index: Optional[int] = None
    feature_vector: Optional[Any] = field(default=None, compare=False, repr=False)
    template_blob: Optional[bytes] = field(default=None, compare=False, repr=False)

    @classmethod
    def from_rect64(cls, s: str, contact_id: str = "", contact_name: Optional[str] = None) -> FaceRect:
        """
        FR : Construit un `FaceRect` à partir d'une chaîne `rect64(...)`.
        EN: Build a `FaceRect` instance from a `rect64(...)` string.
        """
        l, t, r, b = decode_rect64_string(s)
        return cls(left=l, top=t, right=r, bottom=b, contact_id=contact_id, contact_name=contact_name)

    @classmethod
    def from_uint64(cls, val: int, contact_id: str = "", contact_name: Optional[str] = None) -> FaceRect:
        """
        FR : Construit un `FaceRect` à partir d'un entier 64 bits `rect64`.
        EN: Build a `FaceRect` instance from a 64-bit `rect64` integer.
        """
        l, t, r, b = decode_rect64_uint64(val)
        return cls(left=l, top=t, right=r, bottom=b, contact_id=contact_id, contact_name=contact_name)

    def to_rect64(self) -> str:
        """
        FR : Convertit le rectangle en chaîne `rect64(XXXXXXXXXXXXXXXX)`.
        EN: Convert the rectangle into a `rect64(XXXXXXXXXXXXXXXX)` string.
        """
        return encode_rect64_string(self.left, self.top, self.right, self.bottom)

    def to_rect64_string(self) -> str:
        """
        FR : Alias vers `to_rect64()`.
        EN: Alias for `to_rect64()`.
        """
        return self.to_rect64()

    def to_uint64(self) -> int:
        """
        FR : Convertit le rectangle en entier 64 bits non signé (`uint64`).
        EN: Convert the rectangle into an unsigned 64-bit integer (`uint64`).
        """
        return encode_rect64_uint64(self.left, self.top, self.right, self.bottom)

    @property
    def width(self) -> float:
        """
        FR : Largeur normalisée du rectangle (`right - left`).
        EN: Normalized rectangle width (`right - left`).
        """
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        """
        FR : Hauteur normalisée du rectangle (`bottom - top`).
        EN: Normalized rectangle height (`bottom - top`).
        """
        return max(0.0, self.bottom - self.top)

    def to_pixel_rect(self, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
        """
        FR : Convertit en coordonnées pixels entières `(x, y, w, h)`.
        Garantit des dimensions strictement positives et bornées dans l'image.
        EN: Convert to integer pixel coordinates `(x, y, w, h)`.
        Guarantees strictly positive dimensions bounded within the image.
        Ref: picasa3.exe @ 0x009B93F0 (FUN_009b93f0)
        """
        l = min(self.left, self.right)
        t = min(self.top, self.bottom)
        r = max(self.left, self.right)
        b = max(self.top, self.bottom)
        x = max(0, min(img_width - 1, int(round(l * img_width))))
        y = max(0, min(img_height - 1, int(round(t * img_height))))
        w = max(1, min(img_width - x, int(round((r - l) * img_width))))
        h = max(1, min(img_height - y, int(round((b - t) * img_height))))
        return (x, y, w, h)

    def to_pixel_bbox(self, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
        """
        FR : Convertit en coordonnées pixels entières de boîte englobante `(left, top, right, bottom)`
        adaptées pour `PIL.Image.crop(box)`.
        EN: Convert to integer pixel bounding box coordinates `(left, top, right, bottom)`
        suitable for `PIL.Image.crop(box)`.
        """
        l = min(self.left, self.right)
        t = min(self.top, self.bottom)
        r = max(self.left, self.right)
        b = max(self.top, self.bottom)
        x1 = max(0, min(img_width - 1, int(round(l * img_width))))
        y1 = max(0, min(img_height - 1, int(round(t * img_height))))
        x2 = max(x1 + 1, min(img_width, int(round(r * img_width))))
        y2 = max(y1 + 1, min(img_height, int(round(b * img_height))))
        return (x1, y1, x2, y2)

    def to_cropped_space(self, crop_rect: Tuple[float, float, float, float]) -> Optional[FaceRect]:
        """
        FR : Projette les coordonnées du visage dans l'espace de l'image recadrée `[0.0 .. 1.0]`.
        Retourne `None` si le visage est entièrement en dehors du cadre de recadrage.
        EN: Project the face coordinates into the cropped image space `[0.0 .. 1.0]`.
        Returns `None` if the face lies completely outside the crop rectangle.
        Ref: picasa3.exe @ 0x00456A15, 0x0042A6F9
        """
        cl, ct, cr, cb = crop_rect
        cw = cr - cl
        ch = cb - ct
        if cw <= 1e-6 or ch <= 1e-6:
            return None

        l_prime = (self.left - cl) / cw
        t_prime = (self.top - ct) / ch
        r_prime = (self.right - cl) / cw
        b_prime = (self.bottom - ct) / ch

        # FR : Si le rectangle est entièrement en dehors
        # EN: If the rectangle is completely outside
        if r_prime <= 0.0 or l_prime >= 1.0 or b_prime <= 0.0 or t_prime >= 1.0:
            return None

        # FR : Clamper à l'image recadrée
        # EN: Clamp to cropped image bounds
        nl = max(0.0, min(1.0, min(l_prime, r_prime)))
        nt = max(0.0, min(1.0, min(t_prime, b_prime)))
        nr = max(0.0, min(1.0, max(l_prime, r_prime)))
        nb = max(0.0, min(1.0, max(t_prime, b_prime)))

        if (nr - nl) < 0.005 or (nb - nt) < 0.005:
            return None

        return FaceRect(
            left=nl,
            top=nt,
            right=nr,
            bottom=nb,
            contact_id=self.contact_id,
            contact_name=self.contact_name,
            feature_vector=self.feature_vector,
            template_blob=self.template_blob,
            record_index=self.record_index,
        )

    def from_cropped_space(self, crop_rect: Tuple[float, float, float, float]) -> FaceRect:
        """
        FR : Projette inversement un rectangle tracé sur l'image recadrée vers les coordonnées d'origine `[0.0 .. 1.0]`.
        EN: Inversely project a rectangle drawn on the cropped image back to original coordinates `[0.0 .. 1.0]`.
        Ref: picasa3.exe @ 0x00456A15
        """
        cl, ct, cr, cb = crop_rect
        cw = cr - cl
        ch = cb - ct
        l_orig = cl + self.left * cw
        t_orig = ct + self.top * ch
        r_orig = cl + self.right * cw
        b_orig = ct + self.bottom * ch

        return FaceRect(
            left=max(0.0, min(1.0, min(l_orig, r_orig))),
            top=max(0.0, min(1.0, min(t_orig, b_orig))),
            right=max(0.0, min(1.0, max(l_orig, r_orig))),
            bottom=max(0.0, min(1.0, max(t_orig, b_orig))),
            contact_id=self.contact_id,
            contact_name=self.contact_name,
            feature_vector=self.feature_vector,
            template_blob=self.template_blob,
            record_index=self.record_index,
        )

    def to_rotated_space(self, rotation_steps: int) -> FaceRect:
        """
        FR : Projette les coordonnées lors d'une rotation 90° (`steps=1`), 180° (`steps=2`), 270° (`steps=3`).
        EN: Project coordinates under a 90° (`steps=1`), 180° (`steps=2`), or 270° (`steps=3`) rotation.
        Ref: picasa3.exe @ 0x0042A6F9 ("rotate(-1)")
        """
        rot = rotation_steps % 4
        if rot == 0:
            return FaceRect(
                self.left,
                self.top,
                self.right,
                self.bottom,
                self.contact_id,
                self.contact_name,
                self.feature_vector,
                self.template_blob,
                self.record_index,
            )
        elif rot == 1:  # 90° CW (image rotated 270 deg in PIL)
            nl = 1.0 - self.bottom
            nt = self.left
            nr = 1.0 - self.top
            nb = self.right
        elif rot == 2:  # 180°
            nl = 1.0 - self.right
            nt = 1.0 - self.bottom
            nr = 1.0 - self.left
            nb = 1.0 - self.top
        else:  # rot == 3, 270° CW
            nl = self.top
            nt = 1.0 - self.right
            nr = self.bottom
            nb = 1.0 - self.left

        return FaceRect(
            left=min(nl, nr),
            top=min(nt, nb),
            right=max(nl, nr),
            bottom=max(nt, nb),
            contact_id=self.contact_id,
            contact_name=self.contact_name,
            feature_vector=self.feature_vector,
            template_blob=self.template_blob,
            record_index=self.record_index,
        )

    def from_rotated_space(self, rotation_steps: int) -> FaceRect:
        """
        FR : Inverse de `to_rotated_space`.
        EN: Inverse of `to_rotated_space`.
        """
        rot = rotation_steps % 4
        inv_steps = (4 - rot) % 4
        return self.to_rotated_space(inv_steps)

    def to_tilted_space(self, angle_deg: float, aspect_ratio: float = 1.0) -> Optional[FaceRect]:
        """
        FR : Projette les coordonnées lors d'un redressement (`tilt`) avec cadrage automatique.
        EN: Project coordinates under a straighten (`tilt`) angle with auto-zoom cropping.
        Ref: picasa3.exe @ 0x0042BFA0 (FUN_0042bfa0), 0x009E68F0, 0x009E6490, 0x0090A720
        """
        if abs(angle_deg) < 0.01:
            return FaceRect(
                self.left,
                self.top,
                self.right,
                self.bottom,
                self.contact_id,
                self.contact_name,
                self.feature_vector,
                self.template_blob,
                self.record_index,
            )

        a = math.radians(abs(angle_deg))
        s = math.cos(a) + (math.sin(a) * aspect_ratio) if aspect_ratio >= 1.0 else math.cos(a) + (math.sin(a) / aspect_ratio)
        rad = math.radians(angle_deg)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        cx = (self.left + self.right) / 2.0
        cy = (self.top + self.bottom) / 2.0
        hw = (self.right - self.left) / 2.0
        hh = (self.bottom - self.top) / 2.0

        dx = (cx - 0.5) * aspect_ratio
        dy = cy - 0.5
        # FR : Rotation horaire dans le repère image (x vers la droite, y vers le bas)
        #      conforme à FUN_0042bfa0 (0x0042BFA0) et PIL.Image.rotate(-angle_deg).
        # EN : Clockwise rotation in image coordinates (x right, y down)
        #      matching FUN_0042bfa0 (0x0042BFA0) and PIL.Image.rotate(-angle_deg).
        rx = dx * cos_r - dy * sin_r
        ry = dx * sin_r + dy * cos_r
        ncx = (rx / aspect_ratio) * s + 0.5
        ncy = ry * s + 0.5

        nhw = hw * s
        nhh = hh * s

        nl = ncx - nhw
        nr = ncx + nhw
        nt = ncy - nhh
        nb = ncy + nhh

        if nr <= 0.0 or nl >= 1.0 or nb <= 0.0 or nt >= 1.0:
            return None

        nl = max(0.0, min(1.0, nl))
        nt = max(0.0, min(1.0, nt))
        nr = max(0.0, min(1.0, nr))
        nb = max(0.0, min(1.0, nb))

        if (nr - nl) < 0.005 or (nb - nt) < 0.005:
            return None

        return FaceRect(
            left=nl,
            top=nt,
            right=nr,
            bottom=nb,
            contact_id=self.contact_id,
            contact_name=self.contact_name,
            feature_vector=self.feature_vector,
            template_blob=self.template_blob,
            record_index=self.record_index,
        )

    def from_tilted_space(self, angle_deg: float, aspect_ratio: float = 1.0) -> FaceRect:
        """
        FR : Inverse de `to_tilted_space`.
        EN: Inverse of `to_tilted_space`.
        Ref: picasa3.exe @ 0x0042BFA0 (FUN_0042bfa0), 0x009E6490
        """
        if abs(angle_deg) < 0.01:
            return FaceRect(
                self.left,
                self.top,
                self.right,
                self.bottom,
                self.contact_id,
                self.contact_name,
                self.feature_vector,
                self.template_blob,
                self.record_index,
            )

        a = math.radians(abs(angle_deg))
        s = math.cos(a) + (math.sin(a) * aspect_ratio) if aspect_ratio >= 1.0 else math.cos(a) + (math.sin(a) / aspect_ratio)
        rad = math.radians(angle_deg)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        cx = (self.left + self.right) / 2.0
        cy = (self.top + self.bottom) / 2.0
        hw = (self.right - self.left) / 2.0
        hh = (self.bottom - self.top) / 2.0

        rx = ((cx - 0.5) / s) * aspect_ratio
        ry = (cy - 0.5) / s
        dx = rx * cos_r + ry * sin_r
        dy = -rx * sin_r + ry * cos_r
        orig_cx = (dx / aspect_ratio) + 0.5
        orig_cy = dy + 0.5

        orig_hw = hw / s
        orig_hh = hh / s

        nl = orig_cx - orig_hw
        nr = orig_cx + orig_hw
        nt = orig_cy - orig_hh
        nb = orig_cy + orig_hh

        return FaceRect(
            left=max(0.0, min(1.0, nl)),
            top=max(0.0, min(1.0, nt)),
            right=max(0.0, min(1.0, nr)),
            bottom=max(0.0, min(1.0, nb)),
            contact_id=self.contact_id,
            contact_name=self.contact_name,
            feature_vector=self.feature_vector,
            template_blob=self.template_blob,
            record_index=self.record_index,
        )

    def transform_to_display(
        self,
        crop_rect: Optional[Tuple[float, float, float, float]] = None,
        rotation: int = 0,
        tilt_angle: float = 0.0,
        aspect_ratio: float = 1.0,
    ) -> Optional[FaceRect]:
        """
        FR : Applique la chaîne de transformations non-destructives d'affichage :
        1. Recadrage (`crop`)
        2. Rotation (`rotate`)
        3. Redressement (`tilt`)
        EN: Apply the non-destructive display transformation chain:
        1. Crop
        2. Rotate
        3. Tilt (straighten)
        """
        res: Optional[FaceRect] = self
        if crop_rect:
            res = res.to_cropped_space(crop_rect)
            if res is None:
                return None

        if rotation % 4 != 0:
            res = res.to_rotated_space(rotation)

        if abs(tilt_angle) >= 0.01:
            res = res.to_tilted_space(tilt_angle, aspect_ratio)
            if res is None:
                return None

        return res

    def transform_from_display(
        self,
        crop_rect: Optional[Tuple[float, float, float, float]] = None,
        rotation: int = 0,
        tilt_angle: float = 0.0,
        aspect_ratio: float = 1.0,
    ) -> FaceRect:
        """
        FR : Applique la chaîne inverse des transformations pour recalculer les coordonnées
        d'origine `[0.0 .. 1.0]` avant enregistrement dans `.picasa.ini`.
        EN: Apply the inverse transformation chain to compute original `[0.0 .. 1.0]`
        coordinates before saving to `.picasa.ini`.
        """
        res = self
        if abs(tilt_angle) >= 0.01:
            res = res.from_tilted_space(tilt_angle, aspect_ratio)

        if rotation % 4 != 0:
            res = res.from_rotated_space(rotation)

        if crop_rect:
            res = res.from_cropped_space(crop_rect)

        return res

    @staticmethod
    def to_avatar_pixmap(
        img: Image.Image,
        avatar_size: int = 64,
        circular: bool = True,
    ) -> QPixmap:
        """
        FR : Convertit une image PIL (vignette pré-découpée ou crop) en `QPixmap`
        avec mise à l'échelle fidèle et masque circulaire optionnel.
        EN: Convert a PIL image (pre-cropped thumbnail or face crop) into a `QPixmap`
        with faithful scaling and optional circular mask.
        """
        w, h = img.size
        if w <= 0 or h <= 0:
            return QPixmap()

        if img.mode in ("P", "PA") or (img.mode != "RGBA" and "transparency" in img.info):
            img = img.convert("RGBA")

        if circular:
            side = min(w, h)
            cx, cy = w // 2, h // 2
            cropped = img.crop((cx - side // 2, cy - side // 2, cx + (side + 1) // 2, cy + (side + 1) // 2))
            cropped = cropped.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        else:
            scale = avatar_size / float(max(w, h))
            nw = max(1, int(round(w * scale)))
            nh = max(1, int(round(h * scale)))
            cropped = img.resize((nw, nh), Image.Resampling.LANCZOS)

        if cropped.mode != "RGB":
            cropped = cropped.convert("RGB")

        data = cropped.tobytes("raw", "RGB")
        qimg = QImage(data, cropped.width, cropped.height, cropped.width * 3, QImage.Format.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)

        if not circular:
            return pix

        circular_pix = QPixmap(avatar_size, avatar_size)
        circular_pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(circular_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        path.addEllipse(1, 1, avatar_size - 2, avatar_size - 2)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pix)

        pen = QPen(QColor(220, 220, 220, 180), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, avatar_size - 2, avatar_size - 2)
        painter.end()

        return circular_pix

    def crop_avatar(
        self,
        source_image: Image.Image,
        avatar_size: int = 64,
        margin_ratio: float = 0.0,
        circular: bool = True,
    ) -> QPixmap:
        """
        FR : Découpe un avatar centré sur le visage conformément aux proportions Picasa.
        Dans Picasa 3, `FaceRect` (`rect64`) correspond exactement au cadrage portrait 5:6
        englobant le visage, la chevelure et le menton sans marge superflue.
        EN: Crop a face-centered avatar matching Picasa's proportions.
        In Picasa 3, `FaceRect` (`rect64`) matches the 5:6 portrait framing encompassing
        the face, hair, and chin without excess margin.
        Ref: picasa3.exe @ 0x009B93F0, 0x00456A15, PeopleAlbumUseFaceSrc
        """
        if source_image.mode in ("P", "PA") or (source_image.mode != "RGBA" and "transparency" in source_image.info):
            source_image = source_image.convert("RGBA")
        w, h = source_image.size
        fx, fy, fw, fh = self.to_pixel_rect(w, h)

        # FR : Cadrage centré préservant l'intégralité du visage sans amputation du front ni du menton
        # EN: Centered framing preserving the entire face without clipping forehead or chin
        side = max(fw, fh)
        if margin_ratio > 0.0:
            side = side * (1.0 + 2.0 * margin_ratio)

        cx = fx + fw / 2.0
        cy = fy + fh / 2.0
        x1 = cx - side / 2.0
        y1 = cy - side / 2.0
        x2 = cx + side / 2.0
        y2 = cy + side / 2.0

        if x1 < 0.0:
            shift = -x1
            x1 = 0.0
            x2 = min(float(w), x2 + shift)
        if y1 < 0.0:
            shift = -y1
            y1 = 0.0
            y2 = min(float(h), y2 + shift)
        if x2 > float(w):
            shift = x2 - float(w)
            x2 = float(w)
            x1 = max(0.0, x1 - shift)
        if y2 > float(h):
            shift = y2 - float(h)
            y2 = float(h)
            y1 = max(0.0, y1 - shift)

        ix1 = max(0, min(w - 1, int(round(x1))))
        iy1 = max(0, min(h - 1, int(round(y1))))
        ix2 = max(ix1 + 1, min(w, int(round(x2))))
        iy2 = max(iy1 + 1, min(h, int(round(y2))))

        cropped = source_image.crop((ix1, iy1, ix2, iy2))
        return self.to_avatar_pixmap(cropped, avatar_size=avatar_size, circular=circular)

    def project_for_photo_ini(
        self,
        photo_path: Optional[str],
        aspect_ratio: Optional[float] = None,
        db: Any = None,
    ) -> FaceRect:
        """
        FR : Projette ce rectangle de visage (stocké dans les coordonnées d'origine)
             dans l'espace d'une image déjà transformée par `.picasa.ini` (`crop`, `rotate`, `tilt`).
        EN: Project this face rectangle (stored in original unedited coordinates)
            into the coordinate space of an image already transformed by `.picasa.ini` (`crop`, `rotate`, `tilt`).
        Ref: picasa3.exe @ 0x0042BFA0 (FUN_0042bfa0), 0x00456A15, 0x0042A6F9
        """
        if not photo_path or not os.path.exists(photo_path):
            return self
        parent_dir = os.path.dirname(photo_path)
        ini_path = os.path.join(parent_dir, ".picasa.ini")
        if not os.path.exists(ini_path):
            ini_path = os.path.join(parent_dir, "Picasa.ini")
        if not os.path.exists(ini_path):
            return self
        try:
            from picasa_py.ini.parser import PicasaIniParser
            doc = (
                db.get_parsed_ini(ini_path)
                if (db is not None and hasattr(db, "get_parsed_ini"))
                else PicasaIniParser.parse_file(ini_path)
            )
            if doc is None:
                doc = PicasaIniParser.parse_file(ini_path)
            base_name = os.path.basename(photo_path)
            crop_rect: Optional[Tuple[float, float, float, float]] = None
            crop_hex = doc.get_crop(base_name)
            if crop_hex:
                crop_rect = decode_rect64_string(crop_hex)
            rot = (doc.get_rotate(base_name) or 0) % 4
            tilt = doc.get_tilt(base_name) or 0.0
            if crop_rect is None and rot == 0 and abs(tilt) < 0.01:
                return self

            if aspect_ratio is not None and aspect_ratio > 0.0:
                eff_aspect = float(aspect_ratio)
            else:
                w0, h0 = 0, 0
                try:
                    with Image.open(photo_path) as raw_img:
                        w0, h0 = raw_img.size
                        exif = raw_img.getexif()
                        if exif and int(exif.get(0x0112, 1) or 1) in (5, 6, 7, 8):
                            w0, h0 = h0, w0
                except Exception:
                    w0, h0 = 0, 0
                if (w0 <= 0 or h0 <= 0) and db is not None and hasattr(db, "find_photo_index"):
                    try:
                        p_idx = db.find_photo_index(photo_path)
                        if p_idx is not None and hasattr(db, "pmps"):
                            pmp_w = db.pmps.get("imagedata_width")
                            pmp_h = db.pmps.get("imagedata_height")
                            if pmp_w and pmp_h and p_idx < len(pmp_w.records) and p_idx < len(pmp_h.records):
                                w0 = int(pmp_w.records[p_idx] or 0)
                                h0 = int(pmp_h.records[p_idx] or 0)
                    except Exception:
                        pass
                if w0 > 0 and h0 > 0:
                    w_c = float(w0)
                    h_c = float(h0)
                    if crop_rect is not None:
                        cl, ct, cr, cb = crop_rect
                        w_c *= max(1e-6, cr - cl)
                        h_c *= max(1e-6, cb - ct)
                    if rot in (1, 3):
                        w_c, h_c = h_c, w_c
                    eff_aspect = (w_c / float(h_c)) if h_c > 1e-6 else 1.0
                else:
                    eff_aspect = 1.0

            projected = self.transform_to_display(
                crop_rect=crop_rect,
                rotation=rot,
                tilt_angle=tilt,
                aspect_ratio=eff_aspect,
            )
            return projected if projected is not None else self
        except Exception:
            return self

