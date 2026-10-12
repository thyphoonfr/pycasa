"""
Image processing and filter engine for Picasa 3 editing tools.

Ref: picasa3.exe @ filterdesc.xml
Ref: picasa3.exe @ 0x0088C3EC (eMenuPicture effects)
"""

from __future__ import annotations
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter


# Ref: filterdesc.xml
class PicasaImageProcessor:
    """
    Moteur de traitement d'image exécutant les filtres et retouches de Picasa.
    """

    @staticmethod
    def auto_contrast(img: Image.Image) -> Image.Image:
        """
        Contraste automatique (Ref: ID_PICTURE_AUTO_LIGHTING).
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageOps.autocontrast(img, cutoff=0.5)

    @staticmethod
    def auto_color(img: Image.Image) -> Image.Image:
        """
        Couleur automatique / équilibrage (Ref: ID_PICTURE_AUTO_COLOR).
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageOps.equalize(img)

    @staticmethod
    def black_and_white(img: Image.Image) -> Image.Image:
        """
        Filtre Noir et Blanc (Ref: ID_VIEW_BW, filterdesc: B&W).
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        gray = img.convert("L")
        return gray.convert("RGB")

    @staticmethod
    def sepia(img: Image.Image) -> Image.Image:
        """
        Filtre Sépia classique Picasa (Ref: ID_VIEW_SEPIA, filterdesc: Sepia).
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        # Matrice sépia standard de transformation colorimétrique
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        tr = 0.393 * r + 0.769 * g + 0.189 * b
        tg = 0.349 * r + 0.686 * g + 0.168 * b
        tb = 0.272 * r + 0.534 * g + 0.131 * b
        out = np.stack([np.clip(tr, 0, 255), np.clip(tg, 0, 255), np.clip(tb, 0, 255)], axis=2)
        return Image.fromarray(out.astype(np.uint8))

    @staticmethod
    def warmify(img: Image.Image, intensity: float = 0.2) -> Image.Image:
        """
        Réchauffer les tons (Ref: ID_PICTURE_WARMIFY).
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 + intensity), 0, 255)  # Boost rouge
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 - intensity * 0.5), 0, 255)  # Diminue bleu
        return Image.fromarray(arr.astype(np.uint8))

    @staticmethod
    def fill_light(img: Image.Image, amount: float = 0.3) -> Image.Image:
        """
        Lumière d'appoint (Ref: filterdesc.xml: triple / Fill Light).
        Rehausse les ombres sans brûler les hautes lumières.
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32) / 255.0
        # Courbe de rehaussement d'ombres
        boost = (1.0 - arr) * amount
        out = np.clip((arr + boost) * 255.0, 0, 255)
        return Image.fromarray(out.astype(np.uint8))

    @staticmethod
    def sharpen(img: Image.Image) -> Image.Image:
        """
        Amélioration de netteté (Ref: ID_PICTURE_SHARPEN).
        """
        return img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    @staticmethod
    def film_grain(img: Image.Image, intensity: float = 18.0) -> Image.Image:
        """
        Grain argentique (Ref: ID_PICTURE_FILM_GRAIN).
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, intensity, arr.shape)
        out = np.clip(arr + noise, 0, 255)
        return Image.fromarray(out.astype(np.uint8))
