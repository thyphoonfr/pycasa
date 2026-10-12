"""
Structures et fonctions de décodage/encodage des coordonnées de visages Picasa (rect64).

Ref: picasa3.exe @ 0x009B9190 (FUN_009b9190 -> decode uint64 to rect coords)
Ref: picasa3.exe @ 0x009B91C0 (FUN_009b91c0 -> encode rect coords to uint64)
Ref: picasa3.exe @ 0x009B9247 (Format string "rect64(%I64x)")
Ref: picasa3.exe @ 0x009B9290 (Coordinate scaling to width & height)
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from PySide6.QtGui import QImage, QPixmap, QPainter, QPainterPath, QColor, QPen
from PySide6.QtCore import Qt, QRectF


def decode_rect64_uint64(val: int) -> Tuple[float, float, float, float]:
    """
    Décode un entier 64 bits en coordonnées normalisées (0.0 .. 1.0).
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
    Encode des coordonnées normalisées en entier 64 bits.
    Ref: picasa3.exe @ 0x009B91C0
    """
    w0 = max(0, min(65535, int(round(left * 65535.0))))
    w1 = max(0, min(65535, int(round(top * 65535.0))))
    w2 = max(0, min(65535, int(round(right * 65535.0))))
    w3 = max(0, min(65535, int(round(bottom * 65535.0))))
    return (w0 << 48) | (w1 << 32) | (w2 << 16) | w3


def decode_rect64_string(s: str) -> Tuple[float, float, float, float]:
    """
    Décode une chaîne de la forme rect64(XXXXXXXXXXXXXXXX).
    Ref: picasa3.exe @ 0x009B9247
    """
    clean = s.strip()
    if clean.startswith("rect64(") and clean.endswith(")"):
        clean = clean[7:-1]
    val = int(clean, 16)
    return decode_rect64_uint64(val)


def encode_rect64_string(left: float, top: float, right: float, bottom: float) -> str:
    """
    Encode des coordonnées normalisées sous forme de chaîne rect64(XXXXXXXXXXXXXXXX).
    """
    val = encode_rect64_uint64(left, top, right, bottom)
    return f"rect64({val:016x})"


@dataclass
class FaceRect:
    """
    Rectangle de détection de visage avec coordonnées normalisées [0.0 .. 1.0].
    """
    left: float
    top: float
    right: float
    bottom: float
    contact_id: str = ""
    contact_name: Optional[str] = None

    @classmethod
    def from_rect64(cls, s: str, contact_id: str = "", contact_name: Optional[str] = None) -> FaceRect:
        l, t, r, b = decode_rect64_string(s)
        return cls(left=l, top=t, right=r, bottom=b, contact_id=contact_id, contact_name=contact_name)

    @classmethod
    def from_uint64(cls, val: int, contact_id: str = "", contact_name: Optional[str] = None) -> FaceRect:
        l, t, r, b = decode_rect64_uint64(val)
        return cls(left=l, top=t, right=r, bottom=b, contact_id=contact_id, contact_name=contact_name)

    def to_rect64(self) -> str:
        return encode_rect64_string(self.left, self.top, self.right, self.bottom)

    def to_uint64(self) -> int:
        return encode_rect64_uint64(self.left, self.top, self.right, self.bottom)

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    def to_pixel_rect(self, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
        """Convertit en coordonnées pixels entières (x, y, w, h)."""
        x = int(round(self.left * img_width))
        y = int(round(self.top * img_height))
        w = int(round(self.width * img_width))
        h = int(round(self.height * img_height))
        return (x, y, max(1, w), max(1, h))

    def crop_avatar(
        self,
        source_image: Image.Image,
        avatar_size: int = 64,
        margin_ratio: float = 0.25,
        circular: bool = True
    ) -> QPixmap:
        """
        Découpe un avatar centré sur le visage avec marge esthétique Picasa.
        """
        w, h = source_image.size
        fx, fy, fw, fh = self.to_pixel_rect(w, h)

        # Ajouter une marge autour du visage
        margin_x = fw * margin_ratio
        margin_y = fh * margin_ratio

        x1 = max(0, fx - margin_x)
        y1 = max(0, fy - margin_y)
        x2 = min(w, fx + fw + margin_x)
        y2 = min(h, fy + fh + margin_y)

        # Rendre le recadrage carré
        cw = x2 - x1
        ch = y2 - y1
        if cw > ch:
            diff = (cw - ch) / 2
            x1 = max(0, x1 + diff)
            x2 = min(w, x2 - diff)
        elif ch > cw:
            diff = (ch - cw) / 2
            y1 = max(0, y1 + diff)
            y2 = min(h, y2 - diff)

        cropped = source_image.crop((int(x1), int(y1), int(x2), int(y2)))
        cropped = cropped.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        if cropped.mode in ("P", "PA") or "transparency" in cropped.info:
            cropped = cropped.convert("RGBA")
        if cropped.mode != "RGB":
            cropped = cropped.convert("RGB")

        # Convertir en QImage puis QPixmap
        data = cropped.tobytes("raw", "RGB")
        qimg = QImage(data, avatar_size, avatar_size, avatar_size * 3, QImage.Format.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)

        if not circular:
            return pix

        # Rendu circulaire avec bordure douce
        circular_pix = QPixmap(avatar_size, avatar_size)
        circular_pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(circular_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        path.addEllipse(1, 1, avatar_size - 2, avatar_size - 2)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pix)

        # Bordure discrète
        pen = QPen(QColor(220, 220, 220, 180), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, avatar_size - 2, avatar_size - 2)
        painter.end()

        return circular_pix
