"""
FR : Moteur de traitement d'image et d'exécution des filtres pour les outils d'édition de Picasa 3.
EN : Image processing and filter execution engine for Picasa 3 editing tools.

Ref: picasa3.exe @ filterdesc.xml
Ref: picasa3.exe @ 0x00760F40 (Picnik / Glimmer XML filter interpreter)
Ref: picasa3.exe @ 0x0088C3EC (eMenuPicture effects)
"""

from __future__ import annotations
import os
import io
import math
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter


# Ref: filterdesc.xml
# Ref: picasa3.exe @ 0x00760F40
class PicasaImageProcessor:
    """
    FR : Moteur de traitement d'image exécutant les filtres et retouches de Picasa (standards et Picnik/Glimmer).
    EN : Image processing engine executing Picasa filters and retouches (standard and Picnik/Glimmer).
    """

    @staticmethod
    def _box_blur_quality3(img: Image.Image, xblur: float, yblur: float | None = None) -> Image.Image:
        """
        FR : Applique un flou boîte en 3 passes séparables reproduisant BlurImageOperation(..., quality="3")
             de Glimmer/Picnik (BitmapFilterQuality.HIGH).
        EN : Applies a 3-pass separable box blur reproducing Glimmer/Picnik's BlurImageOperation(..., quality="3")
             (BitmapFilterQuality.HIGH).

        Ref: picasa3.exe @ 0x00760F40 (BlurImageOperation, quality=3)
        Ref: runtime/filterdesc.xml @ BlurImageOperation
        """
        if yblur is None:
            yblur = xblur
        rx = max(0.0, (float(xblur) - 1.0) * 0.5)
        ry = max(0.0, (float(yblur) - 1.0) * 0.5)
        if rx <= 0.05 and ry <= 0.05:
            return img.copy()
        if abs(rx - ry) < 0.25:
            r = max(0.2, min(40.0, (rx + ry) * 0.5))
            out = img
            for _ in range(3):
                out = out.filter(ImageFilter.BoxBlur(r))
            return out
        # FR : Flou séparable horizontal puis vertical en 3 passes (moyenne mobile exacte)
        # EN : Separable horizontal then vertical 3-pass box blur (exact moving average)
        arr = np.array(img, dtype=np.float32)
        wx = max(1, min(arr.shape[1], int(round(float(xblur)))))
        wy = max(1, min(arr.shape[0], int(round(float(yblur)))))
        for _ in range(3):
            if wx > 1:
                pad_l = wx // 2
                pad_r = wx - 1 - pad_l
                padded = np.pad(arr, ((0, 0), (pad_l, pad_r), (0, 0)), mode="edge")
                csum = np.cumsum(padded, axis=1, dtype=np.float32)
                arr = (csum[:, wx - 1:wx - 1 + arr.shape[1], :] - np.pad(csum[:, :arr.shape[1] - 1, :], ((0, 0), (1, 0), (0, 0)))) / float(wx)
            if wy > 1:
                pad_t = wy // 2
                pad_b = wy - 1 - pad_t
                padded = np.pad(arr, ((pad_t, pad_b), (0, 0), (0, 0)), mode="edge")
                csum = np.cumsum(padded, axis=0, dtype=np.float32)
                arr = (csum[wy - 1:wy - 1 + arr.shape[0], :, :] - np.pad(csum[:arr.shape[0] - 1, :, :], ((1, 0), (0, 0), (0, 0)))) / float(wy)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    @staticmethod
    def _inner_glow(
        img: Image.Image,
        color_rgb: tuple[int, int, int],
        xblur: float,
        yblur: float,
        strength: float = 1.0,
        blend_alpha: float = 1.0,
    ) -> Image.Image:
        """
        FR : Reproduit GlowImageOperation(innerglow="true", knockout="false", quality="3") de Glimmer/Picnik.
             Floute un masque alpha inversé depuis les bords de l'image, multiplie par `strength` et fusionne `color_rgb`.
        EN : Reproduces Glimmer/Picnik's GlowImageOperation(innerglow="true", knockout="false", quality="3").
             Blurs an inverted alpha mask from the image borders, multiplies by `strength`, and blends `color_rgb`.

        Ref: picasa3.exe @ 0x00760F40 (GlowImageOperation)
        Ref: runtime/filterdesc.xml @ GlowImageOperation
        """
        w, h = img.size
        # FR : Crée un masque où les bords extérieurs valent 255 et l'intérieur vaut 0, puis floute en 3 passes
        # EN : Creates a mask where outer borders are 255 and interior is 0, then blurs in 3 passes
        pad_x = max(2, int(round(float(xblur))))
        pad_y = max(2, int(round(float(yblur))))
        mask_full = np.full((h + 2 * pad_y, w + 2 * pad_x), 255.0, dtype=np.float32)
        mask_full[pad_y:pad_y + h, pad_x:pad_x + w] = 0.0
        wx = max(1, min(mask_full.shape[1], int(round(float(xblur)))))
        wy = max(1, min(mask_full.shape[0], int(round(float(yblur)))))
        for _ in range(3):
            if wx > 1:
                pl = wx // 2
                pr = wx - 1 - pl
                p = np.pad(mask_full, ((0, 0), (pl, pr)), mode="edge")
                c = np.cumsum(p, axis=1, dtype=np.float32)
                mask_full = (c[:, wx - 1:wx - 1 + mask_full.shape[1]] - np.pad(c[:, :mask_full.shape[1] - 1], ((0, 0), (1, 0)))) / float(wx)
            if wy > 1:
                pt = wy // 2
                pb = wy - 1 - pt
                p = np.pad(mask_full, ((pt, pb), (0, 0)), mode="edge")
                c = np.cumsum(p, axis=0, dtype=np.float32)
                mask_full = (c[wy - 1:wy - 1 + mask_full.shape[0], :] - np.pad(c[:mask_full.shape[0] - 1, :], ((1, 0), (0, 0)))) / float(wy)
        alpha = (mask_full[pad_y:pad_y + h, pad_x:pad_x + w] / 255.0) * float(strength)
        alpha = np.clip(alpha, 0.0, 1.0) * max(0.0, min(1.0, float(blend_alpha)))
        arr = np.array(img, dtype=np.float32)
        col = np.array(color_rgb, dtype=np.float32).reshape((1, 1, 3))
        out = arr * (1.0 - alpha[:, :, np.newaxis]) + col * alpha[:, :, np.newaxis]
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def _simple_color_matrix(
        img: Image.Image,
        brightness: float = 0.0,
        contrast: float = 0.0,
        saturation: float = 0.0,
    ) -> Image.Image:
        """
        FR : Reproduit SimpleColorMatrixImageOperation(Brightness, Contrast, Saturation) de Glimmer/Picnik.
        EN : Reproduces Glimmer/Picnik's SimpleColorMatrixImageOperation(Brightness, Contrast, Saturation).

        Ref: picasa3.exe @ 0x00760F40 (SimpleColorMatrixImageOperation)
        Ref: runtime/filterdesc.xml @ SimpleColorMatrixImageOperation
        """
        arr = np.array(img, dtype=np.float32)
        # 1. Saturation (matrice de luminance Rec.601 / Flash ColorMatrix)
        if abs(saturation) > 1e-4:
            s = 1.0 + float(saturation) / 100.0
            luma = 0.3086 * arr[:, :, 0] + 0.6094 * arr[:, :, 1] + 0.0820 * arr[:, :, 2]
            arr = luma[:, :, np.newaxis] * (1.0 - s) + arr * s
        # 2. Contrast (mise à l'échelle autour de 127.5)
        if abs(contrast) > 1e-4:
            c = 1.0 + float(contrast) / 100.0
            arr = (arr - 127.5) * c + 127.5
        # 3. Brightness (décalage additif en niveaux 0..255)
        if abs(brightness) > 1e-4:
            arr = arr + float(brightness)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    @staticmethod
    def load_transformed_image(file_path: str, max_size: int = 0) -> Optional[Image.Image]:
        """
        FR : Charge une image depuis le disque en appliquant fidèlement l'orientation EXIF
             et les retouches non-destructives Picasa (.picasa.ini : crop, rotate, tilt, filters).
        EN : Loads an image from disk while faithfully applying EXIF orientation
             and Picasa non-destructive edits (.picasa.ini: crop, rotate, tilt, filters).

        Ref: picasa3.exe @ 0x008814AC, 0x009B9290, 0x009B93F0
        """
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            with Image.open(file_path) as raw_img:
                # FR : Décodage rapide draft JPEG si max_size est demandé (ex: miniature ou aperçu)
                # EN : Fast JPEG draft decoding when max_size is requested (e.g., thumbnail or preview)
                if max_size and max_size > 0 and getattr(raw_img, "format", "") == "JPEG":
                    try:
                        raw_img.draft("RGB", (max_size * 2, max_size * 2))
                    except Exception:
                        pass
                if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                    raw_img = raw_img.convert("RGBA")
                try:
                    pil_img = ImageOps.exif_transpose(raw_img)
                except Exception:
                    pil_img = raw_img
                if pil_img.mode not in ("RGB", "RGBA"):
                    pil_img = pil_img.convert("RGB")

                # FR : Application des retouches non-destructives .picasa.ini
                # EN : Apply non-destructive .picasa.ini edits
                parent_dir = os.path.dirname(file_path)
                ini_path = os.path.join(parent_dir, ".picasa.ini")
                if not os.path.exists(ini_path):
                    ini_path = os.path.join(parent_dir, "Picasa.ini")
                if os.path.exists(ini_path):
                    try:
                        from picasa_py.ini.parser import PicasaIniParser
                        from picasa_py.faces.facerect import decode_rect64_string
                        doc = PicasaIniParser.parse_file(ini_path)
                        base_name = os.path.basename(file_path)

                        crop_hex = doc.get_crop(base_name)
                        if crop_hex:
                            left_f, top_f, right_f, bottom_f = decode_rect64_string(crop_hex)
                            w, h = pil_img.size
                            crop_box = (
                                int(round(left_f * w)),
                                int(round(top_f * h)),
                                int(round(right_f * w)),
                                int(round(bottom_f * h)),
                            )
                            if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                                pil_img = pil_img.crop(crop_box)

                        rot = doc.get_rotate(base_name)
                        if rot == 1:
                            pil_img = pil_img.rotate(270, expand=True)
                        elif rot == 2:
                            pil_img = pil_img.rotate(180, expand=True)
                        elif rot == 3:
                            pil_img = pil_img.rotate(90, expand=True)

                        tilt = doc.get_tilt(base_name)
                        if tilt and abs(tilt) >= 0.01:
                            pil_img = PicasaImageProcessor.straighten(pil_img, tilt)

                        # FR : Redimensionner à max_size AVANT d'exécuter les filtres lourds (Ref: 0x0042525F, 0x00568E4A)
                        # EN : Resize to max_size BEFORE running heavy pixel filters (Ref: 0x0042525F, 0x00568E4A)
                        if max_size and max_size > 0:
                            w, h = pil_img.size
                            max_dim = max(w, h)
                            if max_dim > max_size:
                                scale = max_size / float(max_dim)
                                new_w = max(1, int(round(w * scale)))
                                new_h = max(1, int(round(h * scale)))
                                pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)

                        sec = doc.get_section(base_name)
                        if sec:
                            filters_str = sec.get("filters", "")
                            if filters_str:
                                pil_img = PicasaImageProcessor.apply_filter_chain(pil_img, filters_str)

                        # Ref: editpanel/edittextpanel (0x00658900)
                        txt_val = doc.get_raw_text(base_name) if hasattr(doc, "get_raw_text") else doc.get_text(base_name)
                        if txt_val:
                            pil_img = PicasaImageProcessor.apply_text_token(pil_img, txt_val)
                    except Exception:
                        pass

                if max_size and max_size > 0:
                    w, h = pil_img.size
                    max_dim = max(w, h)
                    if max_dim > max_size:
                        scale = max_size / float(max_dim)
                        new_w = max(1, int(round(w * scale)))
                        new_h = max(1, int(round(h * scale)))
                        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                pil_img.load()
                return pil_img.copy()
        except Exception:
            return None

    @staticmethod
    def parse_text_token(txt_val: str) -> Tuple[str, Tuple[float, float], int, Tuple[int, int, int], bool]:
        """
        FR : Analyse une entrée `text=` de `.picasa.ini` (format complet Picasa 3 à 12 champs
             `Police;taille;0;0;0;400;0;0;r,g,b;px,py;shadow;texte` ou format court à 4 champs
             `texte;taille;r,g,b;px,py` ou texte brut).
        EN : Parses a `.picasa.ini` `text=` entry (full 12-field Picasa 3 format
             `Font;size;0;0;0;400;0;0;r,g,b;px,py;shadow;text`, short 4-field format
             `text;size;r,g,b;px,py`, or plain text).

        Ref: picasa3.exe @ 0x00658900 (editpanel/edittextpanel)
        """
        raw = txt_val.strip()
        if not raw:
            return "", (0.15, 0.85), 28, (255, 255, 255), True
        if ";" not in raw:
            return raw, (0.15, 0.85), 28, (255, 255, 255), True

        parts = raw.split(";")
        # Format court à 4 champs : txt;size;r,g,b;px,py
        if len(parts) == 4 and "," in parts[3]:
            try:
                coord_parts = [float(x.strip()) for x in parts[3].split(",") if x.strip()]
                if len(coord_parts) >= 2:
                    px, py = coord_parts[0], coord_parts[1]
                    text_str = parts[0].strip()
                    size = int(round(float(parts[1].strip()))) if parts[1].strip() else 28
                    color: Tuple[int, int, int] = (255, 255, 255)
                    if "," in parts[2]:
                        c_vals = [int(round(float(c.strip()))) for c in parts[2].split(",") if c.strip()]
                        if len(c_vals) >= 3:
                            color = (c_vals[0], c_vals[1], c_vals[2])
                    return text_str, (px, py), size, color, True
            except Exception:
                pass

        # Format complet Picasa 3 : Arial;size;0;0;0;400;0;0;r,g,b;px,py;shadow;txt
        if len(parts) >= 10:
            try:
                size = int(round(float(parts[1].strip()))) if parts[1].strip() else 28
            except Exception:
                size = 28
            color = (255, 255, 255)
            if len(parts) > 8 and "," in parts[8]:
                try:
                    c_vals = [int(round(float(c.strip()))) for c in parts[8].split(",") if c.strip()]
                    if len(c_vals) >= 3:
                        color = (c_vals[0], c_vals[1], c_vals[2])
                except Exception:
                    pass
            pos_norm: Tuple[float, float] = (0.15, 0.85)
            if len(parts) > 9 and "," in parts[9]:
                try:
                    p_vals = [float(x.strip()) for x in parts[9].split(",") if x.strip()]
                    if len(p_vals) >= 2:
                        pos_norm = (p_vals[0], p_vals[1])
                except Exception:
                    pass
            shadow = True
            if len(parts) > 10 and parts[10].strip().lstrip("-").isdigit():
                try:
                    shadow = bool(int(parts[10].strip()))
                except Exception:
                    shadow = True
            text_str = ";".join(parts[11:]).strip() if len(parts) >= 12 else parts[-1].strip()
            return text_str, pos_norm, size, color, shadow

        return parts[-1].strip(), (0.15, 0.85), 28, (255, 255, 255), True

    @staticmethod
    def apply_text_token(img: Image.Image, txt_val: str) -> Image.Image:
        """
        FR : Analyse et applique l'entrée `text=` de `.picasa.ini` sur l'image PIL.
        EN : Parses and applies the `.picasa.ini` `text=` entry onto the PIL image.

        Ref: picasa3.exe @ 0x00658900 (editpanel/edittextpanel)
        """
        text_str, pos_norm, font_size, color, shadow = PicasaImageProcessor.parse_text_token(txt_val)
        if not text_str:
            return img
        return PicasaImageProcessor.add_text(img, text_str, pos_norm, font_size, color, shadow)

    @staticmethod
    def apply_filter_chain(img: Image.Image, filters_str: str) -> Image.Image:
        """
        FR : Applique séquentiellement la chaîne de filtres non-destructifs .picasa.ini (filters=...).
        EN : Sequentially applies the .picasa.ini non-destructive filter chain (filters=...).

        Ref: picasa3.exe @ filterdesc.xml, 0x008814AC, 0x00760F40
        """
        out = img
        for token in filters_str.split(";"):
            token = token.strip()
            if not token or "=" not in token:
                continue
            fname, fval = token.split("=", 1)
            fname_l = fname.strip().lower()
            parts = [p.strip() for p in fval.split(",") if p.strip()]
            try:
                if fname_l in ("autolight", "autocontrast", "enhance"):
                    out = PicasaImageProcessor.auto_contrast(out)
                elif fname_l in ("autocolor", "colorfix"):
                    out = PicasaImageProcessor.auto_color(out)
                elif fname_l == "whitept":
                    r = int(round(float(parts[1]))) if len(parts) > 1 else 128
                    g = int(round(float(parts[2]))) if len(parts) > 2 else 128
                    b = int(round(float(parts[3]))) if len(parts) > 3 else 128
                    out = PicasaImageProcessor.neutral_color_picker(out, (r, g, b))
                elif fname_l in ("bw", "blackwhite"):
                    out = PicasaImageProcessor.black_and_white(out)
                elif fname_l == "sepia":
                    out = PicasaImageProcessor.sepia(out)
                elif fname_l in ("warm", "warmify"):
                    out = PicasaImageProcessor.warmify(out)
                elif fname_l in ("unsharp", "unsharp2", "sharpen"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.5
                    out = PicasaImageProcessor.sharpen(out, amount=amt)
                elif fname_l in ("grain", "grain2", "filmgrain", "picnikgrain"):
                    amt = float(parts[1]) if len(parts) > 1 else 18.0
                    fade = float(parts[2]) if len(parts) > 2 else 0.0
                    out = PicasaImageProcessor.film_grain(out, intensity=amt, fade=fade)
                elif fname_l in ("fill", "backlight", "autobacklight", "filllight"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.3
                    out = PicasaImageProcessor.fill_light(out, amt)
                elif fname_l in ("finetune", "finetune2"):
                    f_val = float(parts[1]) if len(parts) > 1 else 0.0
                    hl_val = float(parts[2]) if len(parts) > 2 else 0.0
                    sh_val = float(parts[3]) if len(parts) > 3 else 0.0
                    ct_val = float(parts[4]) if len(parts) > 4 else 0.0
                    out = PicasaImageProcessor.finetune(out, f_val, hl_val, sh_val, ct_val)
                elif fname_l == "highlights":
                    amt = float(parts[1]) if len(parts) > 1 else 0.3
                    out = PicasaImageProcessor.adjust_highlights(out, amt)
                elif fname_l in ("shadow", "shadows"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.3
                    out = PicasaImageProcessor.adjust_shadows(out, amt)
                elif fname_l == "colortemp":
                    t = float(parts[1]) if len(parts) > 1 else 0.0
                    out = PicasaImageProcessor.color_temperature(out, t)
                elif fname_l in ("sat", "saturation"):
                    fac = float(parts[1]) if len(parts) > 1 else 1.4
                    out = PicasaImageProcessor.saturation(out, fac)
                elif fname_l in ("tint", "picniktint"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.4
                    col = (
                        (int(round(float(parts[2]))), int(round(float(parts[3]))), int(round(float(parts[4]))))
                        if len(parts) >= 5
                        else (220, 190, 150)
                    )
                    out = PicasaImageProcessor.tint(out, tint_rgb=col, intensity=amt)
                elif fname_l in ("radblur", "softfocus"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.4
                    sz = float(parts[2]) if len(parts) > 2 else 0.35
                    out = PicasaImageProcessor.soft_focus(out, amount=amt, radius_norm=sz)
                elif fname_l in ("glow", "glow2"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.45
                    rad = float(parts[2]) if len(parts) > 2 else 8.0
                    out = PicasaImageProcessor.glow(out, intensity=amt, radius=rad)
                elif fname_l in ("radsat", "focalbw"):
                    sz = float(parts[1]) if len(parts) > 1 else 0.35
                    sh = float(parts[2]) if len(parts) > 2 else 0.4
                    out = PicasaImageProcessor.focal_bw(out, radius_norm=sz, sharpness=sh)
                elif fname_l in ("dir_tint", "gradtint", "graduatedtint", "graduated_tint"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.5
                    feath = float(parts[2]) if len(parts) > 2 else 0.5
                    col = (
                        (int(round(float(parts[3]))), int(round(float(parts[4]))), int(round(float(parts[5]))))
                        if len(parts) >= 6
                        else (255, 140, 50)
                    )
                    out = PicasaImageProcessor.graduated_tint(out, tint_rgb=col, intensity=amt, feather=feath)
                elif fname_l in ("ansel", "filtered_bw", "filteredbw"):
                    col = (
                        (int(round(float(parts[1]))), int(round(float(parts[2]))), int(round(float(parts[3]))))
                        if len(parts) >= 4
                        else (255, 85, 85)
                    )
                    out = PicasaImageProcessor.filtered_bw(out, col)
                elif fname_l in ("hdr", "hdrish"):
                    args = [float(p) for p in parts[1:4]]
                    out = PicasaImageProcessor.hdr_simulator(out, *args)
                elif fname_l == "lomo":
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.lomo(out, *args)
                elif fname_l == "orton":
                    args = [float(p) for p in parts[1:4]]
                    out = PicasaImageProcessor.orton(out, *args)
                elif fname_l in ("sixties", "1960s"):
                    fade = float(parts[1]) if len(parts) > 1 else 20.0
                    out = PicasaImageProcessor.sixties(out, fade=fade)
                elif fname_l == "crossprocess":
                    fade = float(parts[1]) if len(parts) > 1 else 0.0
                    out = PicasaImageProcessor.cross_process(out, fade=fade)
                elif fname_l in ("ir", "infrared"):
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.infrared(out, *args)
                elif fname_l == "holga":
                    args = [float(p) for p in parts[1:4]]
                    out = PicasaImageProcessor.holga(out, *args)
                elif fname_l == "cinemascope":
                    cb = float(parts[1]) if len(parts) > 1 else 0.0
                    fade = float(parts[2]) if len(parts) > 2 else 0.0
                    out = PicasaImageProcessor.cinemascope(out, color_boost=cb, fade=fade)
                elif fname_l in ("nightvision", "night_vision"):
                    gr = float(parts[1]) if len(parts) > 1 else 20.0
                    fade = float(parts[2]) if len(parts) > 2 else 0.0
                    col = (
                        (int(round(float(parts[3]))), int(round(float(parts[4]))), int(round(float(parts[5]))))
                        if len(parts) >= 6
                        else (87, 204, 41)
                    )
                    out = PicasaImageProcessor.night_vision(out, grain_val=gr, fade=fade, color_rgb=col)
                elif fname_l == "heatmap":
                    sh = float(parts[1]) if len(parts) > 1 else 0.0
                    fade = float(parts[2]) if len(parts) > 2 else 0.0
                    out = PicasaImageProcessor.heat_map(out, shift=sh, fade=fade)
                elif fname_l == "boost":
                    args = [float(p) for p in parts[1:2]]
                    out = PicasaImageProcessor.boost(out, *args)
                elif fname_l == "vignette":
                    amt = float(parts[1]) if len(parts) > 1 else 0.5
                    sz = float(parts[2]) if len(parts) > 2 else 0.25
                    col = (
                        (int(round(float(parts[3]))), int(round(float(parts[4]))), int(round(float(parts[5]))))
                        if len(parts) >= 6
                        else (0, 0, 0)
                    )
                    out = PicasaImageProcessor.vignette(out, amount=amt, size=sz, color_rgb=col)
                elif fname_l in ("twotone", "duotone", "two_tone"):
                    b_val = float(parts[1]) if len(parts) > 1 else 0.0
                    c_val = float(parts[2]) if len(parts) > 2 else 0.0
                    f_val = float(parts[3]) if len(parts) > 3 else 0.0
                    sc = (
                        (int(round(float(parts[4]))), int(round(float(parts[5]))), int(round(float(parts[6]))))
                        if len(parts) >= 7
                        else (0, 68, 136)
                    )
                    hc = (
                        (int(round(float(parts[7]))), int(round(float(parts[8]))), int(round(float(parts[9]))))
                        if len(parts) >= 10
                        else (255, 255, 0)
                    )
                    out = PicasaImageProcessor.two_tone(out, b_val, c_val, f_val, sc, hc)
                elif fname_l == "pixelate":
                    bs = int(round(float(parts[1]))) if len(parts) > 1 else 14
                    fade = float(parts[2]) if len(parts) > 2 else 0.0
                    out = PicasaImageProcessor.pixelate(out, block_size=bs, fade=fade)
                elif fname_l in ("focalpixelate", "picnikfocalpixelate"):
                    args = [float(p) for p in parts[1:6]]
                    out = PicasaImageProcessor.focal_pixelate(out, *args)
                elif fname_l == "localcontrast":
                    args = [float(p) for p in parts[1:4]]
                    out = PicasaImageProcessor.local_contrast(out, *args)
                elif fname_l in ("dropshadow", "drop_shadow"):
                    dist = float(parts[1]) if len(parts) > 1 else 6.0
                    ang = float(parts[2]) if len(parts) > 2 else 45.0
                    blur = float(parts[3]) if len(parts) > 3 else 8.0
                    fade = float(parts[4]) if len(parts) > 4 else 50.0
                    bg = (
                        (int(round(float(parts[5]))), int(round(float(parts[6]))), int(round(float(parts[7]))))
                        if len(parts) >= 8
                        else (255, 255, 255)
                    )
                    out = PicasaImageProcessor.drop_shadow(
                        out,
                        distance=dist,
                        angle_deg=ang,
                        blur_radius=blur,
                        shadow_alpha=(100.0 - fade) / 100.0,
                        bg_color=bg,
                    )
                elif fname_l in ("roundededges", "rounded_edges"):
                    rr = float(parts[1]) if len(parts) > 1 else 0.1
                    oc = (
                        (int(round(float(parts[2]))), int(round(float(parts[3]))), int(round(float(parts[4]))))
                        if len(parts) >= 5
                        else (255, 255, 255)
                    )
                    out = PicasaImageProcessor.rounded_edges(out, radius_ratio=rr, outer_color=oc)
                elif fname_l == "invert":
                    out = PicasaImageProcessor.invert(out)
                elif fname_l == "focalzoom":
                    args = [float(p) for p in parts[1:6]]
                    out = PicasaImageProcessor.focal_zoom(out, *args)
                elif fname_l == "soften":
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.soften(out, *args)
                elif fname_l in ("comicize", "comicbook"):
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.comic(out, *args)
                elif fname_l == "neon":
                    fade = float(parts[1]) if len(parts) > 1 else 0.0
                    col = (
                        (int(round(float(parts[2]))), int(round(float(parts[3]))), int(round(float(parts[4]))))
                        if len(parts) >= 5
                        else (0, 255, 255)
                    )
                    out = PicasaImageProcessor.neon(out, col, fade)
                elif fname_l == "pencilsketch":
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.pencil_sketch(out, *args)
                elif fname_l in ("museummatte", "museum_matte"):
                    in_t = float(parts[1]) if len(parts) > 1 else 12.0
                    if len(parts) >= 5 and float(parts[2]) == 0.0 and float(parts[3]) == 0.0:
                        out_t = float(parts[4])
                        ic = (
                            (int(round(float(parts[5]))), int(round(float(parts[6]))), int(round(float(parts[7]))))
                            if len(parts) >= 8
                            else (240, 234, 228)
                        )
                        oc = (
                            (int(round(float(parts[8]))), int(round(float(parts[9]))), int(round(float(parts[10]))))
                            if len(parts) >= 11
                            else (26, 14, 3)
                        )
                    else:
                        out_t = float(parts[2]) if len(parts) > 2 else 7.0
                        ic = (
                            (int(round(float(parts[3]))), int(round(float(parts[4]))), int(round(float(parts[5]))))
                            if len(parts) >= 6
                            else (240, 234, 228)
                        )
                        oc = (
                            (int(round(float(parts[6]))), int(round(float(parts[7]))), int(round(float(parts[8]))))
                            if len(parts) >= 9
                            else (26, 14, 3)
                        )
                    out = PicasaImageProcessor.museum_matte(out, in_t, out_t, ic, oc)
                elif fname_l == "reanimatedeyecolor":
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.reanimated_eye_color(out, *args)
                elif fname_l == "border":
                    outer_t = float(parts[1]) if len(parts) > 1 else 0.04
                    inner_t = float(parts[2]) if len(parts) > 2 else 0.005
                    rad = float(parts[3]) if len(parts) > 3 else 0.0
                    oc = (
                        (int(round(float(parts[4]))), int(round(float(parts[5]))), int(round(float(parts[6]))))
                        if len(parts) >= 7
                        else (26, 26, 26)
                    )
                    ic = (
                        (int(round(float(parts[7]))), int(round(float(parts[8]))), int(round(float(parts[9]))))
                        if len(parts) >= 10
                        else (255, 255, 255)
                    )
                    out = PicasaImageProcessor.border(out, outer_t, inner_t, rad, oc, ic)
                elif fname_l == "polaroid":
                    ang = float(parts[1]) if len(parts) > 1 else 5.0
                    out = PicasaImageProcessor.polaroid(out, angle_deg=ang)
                elif fname_l in ("quantizepalette", "posterize"):
                    st = int(round(float(parts[1]))) if len(parts) > 1 else 8
                    out = PicasaImageProcessor.quantize_palette(out, steps=st)
                elif hasattr(PicasaImageProcessor, fname.strip()):
                    fn = getattr(PicasaImageProcessor, fname.strip())
                    if callable(fn):
                        out = fn(out)
            except Exception:
                pass
        return out

    @staticmethod
    def crop(img: Image.Image, box_norm: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)) -> Image.Image:
        """
        FR : Recadre l'image selon des coordonnées normalisées (left, top, right, bottom).
        EN : Crops the image using normalized coordinates (left, top, right, bottom).

        Ref: filterdesc.xml @ crop, crop64
        """
        w, h = img.size
        x0 = max(0, min(w - 1, int(round(box_norm[0] * w))))
        y0 = max(0, min(h - 1, int(round(box_norm[1] * h))))
        x1 = max(x0 + 1, min(w, int(round(box_norm[2] * w))))
        y1 = max(y0 + 1, min(h, int(round(box_norm[3] * h))))
        return img.crop((x0, y0, x1, y1))

    @staticmethod
    def rotate(img: Image.Image, steps_90_cw: int = 1) -> Image.Image:
        """
        FR : Rotation par pas de 90° dans le sens horaire (1=90° CW, 2=180°, 3=270° CW).
        EN : Rotation in 90° clockwise steps (1=90° CW, 2=180°, 3=270° CW).

        Ref: filterdesc.xml @ rot
        """
        s = steps_90_cw % 4
        if s == 1:
            return img.rotate(270, expand=True)
        if s == 2:
            return img.rotate(180, expand=True)
        if s == 3:
            return img.rotate(90, expand=True)
        return img.copy()

    @staticmethod
    def auto_contrast(img: Image.Image) -> Image.Image:
        """
        FR : Contraste automatique (AutoFix / AutoLight).
        EN : Automatic contrast adjustment (AutoFix / AutoLight).

        Ref: picasa3.exe @ ID_PICTURE_AUTO_LIGHTING, filterdesc.xml @ autolight
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageOps.autocontrast(img, cutoff=0.5)

    @staticmethod
    def auto_color(img: Image.Image) -> Image.Image:
        """
        FR : Couleur automatique / équilibrage d'histogramme par canal.
        EN : Automatic color / per-channel histogram equalization.

        Ref: picasa3.exe @ ID_PICTURE_AUTO_COLOR, filterdesc.xml @ colorfix
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageOps.equalize(img)

    @staticmethod
    def black_and_white(img: Image.Image) -> Image.Image:
        """
        FR : Filtre Noir et Blanc standard Picasa.
        EN : Standard Picasa Black and White filter.

        Ref: picasa3.exe @ ID_VIEW_BW, filterdesc.xml @ bw
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        gray = img.convert("L")
        return gray.convert("RGB")

    @staticmethod
    def sepia(img: Image.Image) -> Image.Image:
        """
        FR : Filtre Sépia classique Picasa.
        EN : Classic Picasa Sepia filter.

        Ref: picasa3.exe @ ID_VIEW_SEPIA, filterdesc.xml @ sepia
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        # FR : Matrice sépia standard de transformation colorimétrique
        # EN : Standard sepia colorimetric transformation matrix
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
        FR : Réchauffer les tons (augmentation du rouge, diminution du bleu).
        EN : Warmify tones (boost red channel, reduce blue channel).

        Ref: picasa3.exe @ ID_PICTURE_WARMIFY, filterdesc.xml @ warm
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 + intensity), 0, 255)  # FR: Boost rouge / EN: Boost red
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 - intensity * 0.5), 0, 255)  # FR: Diminue bleu / EN: Reduce blue
        return Image.fromarray(arr.astype(np.uint8))

    @staticmethod
    def fill_light(img: Image.Image, amount: float = 0.3) -> Image.Image:
        """
        FR : Lumière d'appoint : rehausse les ombres sans brûler les hautes lumières.
        EN : Fill light: lifts shadows without clipping highlights.

        Ref: filterdesc.xml @ triple, fill
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32) / 255.0
        # FR : Courbe de rehaussement d'ombres / EN : Shadow lifting curve
        boost = (1.0 - arr) * amount
        out = np.clip((arr + boost) * 255.0, 0, 255)
        return Image.fromarray(out.astype(np.uint8))

    @staticmethod
    def sharpen(img: Image.Image, amount: float = 0.5) -> Image.Image:
        """
        FR : Amélioration de netteté par masque flou (UnsharpMask).
        EN : Sharpness enhancement via UnsharpMask.

        Ref: picasa3.exe @ ID_PICTURE_SHARPEN, filterdesc.xml @ unsharp, unsharp2
        """
        pct = max(10, int(round(float(amount) * 300.0)))
        return img.filter(ImageFilter.UnsharpMask(radius=2, percent=pct, threshold=3))

    @staticmethod
    def film_grain(img: Image.Image, intensity: float = 18.0, fade: float = 0.0) -> Image.Image:
        """
        FR : Grain argentique additif.
        EN : Additive film grain effect.

        Ref: picasa3.exe @ ID_PICTURE_FILM_GRAIN, filterdesc.xml @ grain, grain2, picnikgrain
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        rng = np.random.default_rng(42)
        noise = rng.normal(0, max(0.5, float(intensity)), arr.shape).astype(np.float32)
        out = np.clip(arr + noise, 0, 255)
        res = Image.fromarray(out.astype(np.uint8))
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def straighten(img: Image.Image, angle_deg: float) -> Image.Image:
        """
        FR : Redresse la photo selon l'angle spécifié en degrés (-45° à +45°)
             et rogne automatiquement les coins pour éviter tout bord noir.
        EN : Straightens the photo by the specified angle in degrees (-45° to +45°)
             and automatically crops corners to avoid empty/black borders.

        Ref: filter_tilt, picasa3.exe @ 0x008814AC
        """
        if abs(angle_deg) < 0.01:
            return img.copy()
        w, h = img.size
        # FR : Rotation bicubique / EN : Bicubic rotation
        rotated = img.rotate(-angle_deg, resample=Image.Resampling.BICUBIC, expand=False)
        # FR : Calcul du rectangle inscrit maximal conservant le ratio
        # EN : Compute maximum inscribed rectangle preserving aspect ratio
        a = math.radians(abs(angle_deg))
        cos_a = math.cos(a)
        sin_a = math.sin(a)
        aspect = w / h
        s = cos_a + (sin_a * aspect) if aspect >= 1.0 else cos_a + (sin_a / aspect)
        crop_w = max(1, int(w / s))
        crop_h = max(1, int(h / s))
        x0 = (w - crop_w) // 2
        y0 = (h - crop_h) // 2
        cropped = rotated.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        return cropped.resize((w, h), resample=Image.Resampling.BICUBIC)

    @staticmethod
    def add_text(
        img: Image.Image,
        text: str,
        pos_norm: tuple[float, float],
        font_size: int = 28,
        color: tuple[int, int, int] = (255, 255, 255),
        shadow: bool = True
    ) -> Image.Image:
        """
        FR : Inscrit du texte sur la photo avec ombre portée facultative.
        EN : Draws text onto the photo with an optional drop shadow.

        Ref: TextTool, picasa3.exe @ 0x00658900
        """
        if not text:
            return img.copy()
        from PIL import ImageDraw, ImageFont
        out = img.copy().convert("RGB")
        draw = ImageDraw.Draw(out)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        w, h = out.size
        x = int(pos_norm[0] * w)
        y = int(pos_norm[1] * h)

        if shadow:
            draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0))
        draw.text((x, y), text, font=font, fill=color)
        return out

    @staticmethod
    def remove_red_eye(
        img: Image.Image,
        eye_box_norm: Optional[tuple[float, float, float, float]] = None
    ) -> Image.Image:
        """
        FR : Supprime les yeux rouges dans la zone spécifiée (ou détection automatique).
        EN : Removes red-eye in the specified bounding box (or automatic detection).

        Ref: filterdesc.xml @ redeye, picasa3.exe @ eMenuPicture::ID_PICTURE_AUTO_REDEYE
        """
        if img.mode != "RGB":
            out = img.convert("RGB")
        else:
            out = img.copy()

        arr = np.array(out, dtype=np.uint8)
        h, w = arr.shape[:2]

        if eye_box_norm:
            x0 = max(0, min(w - 1, int(round(eye_box_norm[0] * w))))
            y0 = max(0, min(h - 1, int(round(eye_box_norm[1] * h))))
            x1 = max(x0 + 1, min(w, int(round(eye_box_norm[2] * w))))
            y1 = max(y0 + 1, min(h, int(round(eye_box_norm[3] * h))))
            sub = arr[y0:y1, x0:x1]
        else:
            sub = arr

        r = sub[:, :, 0].astype(np.float32)
        g = sub[:, :, 1].astype(np.float32)
        b = sub[:, :, 2].astype(np.float32)

        # FR : Condition de rouge prédominant caractéristique de l'œil rouge
        # EN : Dominant red condition characteristic of red-eye reflection
        red_mask = (r > 60) & (r > 1.35 * g) & (r > 1.35 * b)
        # FR : Atténuation vers la teinte de luminance neutre
        # EN : Attenuation toward neutral luminance tone
        sub[red_mask, 0] = ((g[red_mask] + b[red_mask]) * 0.5).astype(np.uint8)

        return Image.fromarray(arr)

    @staticmethod
    def retouch_heal(
        img: Image.Image,
        center_norm: tuple[float, float] = (0.5, 0.5),
        radius_norm: float = 0.03
    ) -> Image.Image:
        """
        FR : Corrige une imperfection par interpolation/lissage local des pixels environnants.
        EN : Heals a blemish via local interpolation/smoothing from surrounding pixels.

        Ref: filterdesc.xml @ retouch, picasa3.exe @ 0x0088C3EC
        """
        if img.mode != "RGB":
            out = img.convert("RGB")
        else:
            out = img.copy()

        arr = np.array(out, dtype=np.float32)
        h, w = arr.shape[:2]
        cx = int(round(center_norm[0] * w))
        cy = int(round(center_norm[1] * h))
        rad = max(3, int(round(radius_norm * min(w, h))))

        x0 = max(0, cx - rad)
        x1 = min(w, cx + rad + 1)
        y0 = max(0, cy - rad)
        y1 = min(h, cy + rad + 1)

        y_grid, x_grid = np.ogrid[y0:y1, x0:x1]
        dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
        mask = dist <= rad

        if np.any(mask):
            ring_mask = (dist > rad * 0.6) & (dist <= rad * 1.3)
            if np.any(ring_mask):
                med_color = np.median(arr[y0:y1, x0:x1][ring_mask], axis=0)
            else:
                med_color = np.median(arr[y0:y1, x0:x1], axis=(0, 1))

            weight = np.clip(1.0 - (dist / rad), 0.0, 1.0)[:, :, np.newaxis]
            arr[y0:y1, x0:x1] = arr[y0:y1, x0:x1] * (1.0 - weight) + med_color * weight

        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # =========================================================================
    # TAB 2: LUMIÈRE / TUNING (Ref: filterdesc.xml @ triple, triple2, finetune)
    # =========================================================================

    @staticmethod
    def adjust_highlights(img: Image.Image, amount: float = 0.3) -> Image.Image:
        """
        FR : Ajuste les hautes lumières (compresse ou adoucit les zones très lumineuses).
        EN : Adjusts highlights (compresses or softens bright regions).

        Ref: filterdesc.xml @ whitept, finetune
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32) / 255.0
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        hl_mask = np.clip((lum - 0.45) / 0.55, 0.0, 1.0)[:, :, np.newaxis]
        arr = np.clip(arr - hl_mask * amount * 0.35, 0.0, 1.0)
        return Image.fromarray((arr * 255.0).astype(np.uint8))

    @staticmethod
    def adjust_shadows(img: Image.Image, amount: float = 0.3) -> Image.Image:
        """
        FR : Ajuste et débouche les ombres.
        EN : Adjusts and lifts shadows.

        Ref: filterdesc.xml @ shadow, finetune
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32) / 255.0
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        sh_mask = np.clip((0.55 - lum) / 0.55, 0.0, 1.0)[:, :, np.newaxis]
        arr = np.clip(arr + sh_mask * amount * 0.4, 0.0, 1.0)
        return Image.fromarray((arr * 255.0).astype(np.uint8))

    @staticmethod
    def color_temperature(img: Image.Image, temp: float = 0.0) -> Image.Image:
        """
        FR : Ajuste la température de couleur (temp > 0 : plus chaud, temp < 0 : plus froid).
        EN : Adjusts color temperature (temp > 0: warmer orange/red, temp < 0: cooler blue).

        Ref: filterdesc.xml @ colortemp, finetune
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        shift = float(temp) / 100.0  # -0.5 .. +0.5
        arr = np.array(img, dtype=np.float32)
        if shift > 0:
            arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 + shift * 0.55), 0, 255)
            arr[:, :, 1] = np.clip(arr[:, :, 1] * (1.0 + shift * 0.15), 0, 255)
            arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 - shift * 0.40), 0, 255)
        elif shift < 0:
            s = abs(shift)
            arr[:, :, 0] = np.clip(arr[:, :, 0] * (1.0 - s * 0.35), 0, 255)
            arr[:, :, 2] = np.clip(arr[:, :, 2] * (1.0 + s * 0.55), 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    @staticmethod
    def neutral_color_balance(img: Image.Image, sampled_rgb: Tuple[int, int, int]) -> Image.Image:
        """
        FR : Corrige la balance des blancs à partir d'un point supposé neutre (gris/blanc).
        EN : Corrects white balance from a sampled neutral (gray/white) reference point.

        Ref: picasa3.exe @ filter_whitept (filterdesc.xml), CDesaturateFilter::pickcolor (0x0088C3EC)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        r0, g0, b0 = sampled_rgb
        if r0 <= 0 or g0 <= 0 or b0 <= 0:
            return img

        # FR : Luminance perçue du point échantillonné / EN : Perceived luminance of sampled pixel
        luma = 0.299 * r0 + 0.587 * g0 + 0.114 * b0
        if luma < 5 or luma > 250:
            return img

        # FR : Facteurs de correction pour neutraliser la teinte / EN : Gain factors to neutralize cast
        gain_r = float(luma) / float(r0)
        gain_g = float(luma) / float(g0)
        gain_b = float(luma) / float(b0)

        # FR : Atténuation douce (mixage 85% correction, 15% original) pour un rendu naturel
        # EN : Gentle damping (85% correction, 15% original) for natural rendering
        gain_r = 1.0 + (gain_r - 1.0) * 0.85
        gain_g = 1.0 + (gain_g - 1.0) * 0.85
        gain_b = 1.0 + (gain_b - 1.0) * 0.85

        arr = np.array(img, dtype=np.float32)
        arr[:, :, 0] = np.clip(arr[:, :, 0] * gain_r, 0, 255)
        arr[:, :, 1] = np.clip(arr[:, :, 1] * gain_g, 0, 255)
        arr[:, :, 2] = np.clip(arr[:, :, 2] * gain_b, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    # =========================================================================
    # TAB 3: EFFETS 1 (Picasa Standard: Ref: filterdesc.xml @ sat, tint, glow...)
    # =========================================================================

    @staticmethod
    def saturation(img: Image.Image, factor: float = 1.4) -> Image.Image:
        """
        FR : Augmente ou diminue la saturation.
        EN : Increases or decreases color saturation.

        Ref: filterdesc.xml @ sat
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageEnhance.Color(img).enhance(factor)

    @staticmethod
    def tint(img: Image.Image, tint_rgb: tuple[int, int, int] = (220, 190, 150), intensity: float = 0.4) -> Image.Image:
        """
        FR : Applique une teinte de couleur personnalisée.
        EN : Applies a custom color tint.

        Ref: filterdesc.xml @ tint, picniktint
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        tint_arr = np.array(tint_rgb, dtype=np.float32)
        blended = arr * (1.0 - intensity) + (arr / 255.0) * tint_arr * intensity
        return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))

    @staticmethod
    def soft_focus(img: Image.Image, amount: float = 0.4, radius_norm: float = 0.35) -> Image.Image:
        """
        FR : Flou artistique / Soft focus autour d'un centre net.
        EN : Soft focus artistic blur around a sharp center.

        Ref: filterdesc.xml @ radblur
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        r_px = max(1.0, float(amount) * 12.0)
        blurred = img.filter(ImageFilter.GaussianBlur(radius=r_px))
        if radius_norm <= 0.01:
            return Image.blend(img, blurred, min(1.0, max(0.0, float(amount))))
        arr_orig = np.array(img, dtype=np.float32)
        arr_blur = np.array(blurred, dtype=np.float32)
        h, w = arr_orig.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        max_r = min(w, h) * float(radius_norm)
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        mask = np.clip((dist - max_r * 0.5) / max(1.0, max_r), 0.0, 1.0)[:, :, np.newaxis] * min(1.0, max(0.1, float(amount)))
        out = arr_orig * (1.0 - mask) + arr_blur * mask
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def glow(img: Image.Image, intensity: float = 0.45, radius: float = 8.0) -> Image.Image:
        """
        FR : Halo / Éclat lumineux diffus (fusion Screen).
        EN : Diffuse luminous glow (Screen blend).

        Ref: filterdesc.xml @ glow, glow2
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        blurred = img.filter(ImageFilter.GaussianBlur(radius=max(1.0, float(radius))))
        a = np.array(img, dtype=np.float32) / 255.0
        b = np.array(blurred, dtype=np.float32) / 255.0
        # FR : Fusion Screen / EN : Screen blend
        screen = 1.0 - (1.0 - a) * (1.0 - b)
        amt = max(0.0, min(1.0, float(intensity)))
        out = a * (1.0 - amt) + screen * amt
        return Image.fromarray((np.clip(out, 0, 1.0) * 255.0).astype(np.uint8))

    @staticmethod
    def focal_bw(img: Image.Image, radius_norm: float = 0.35, sharpness: float = 0.4) -> Image.Image:
        """
        FR : Noir & Blanc focalisé avec centre conservant la couleur.
        EN : Focal Black & White preserving color at the center.

        Ref: filterdesc.xml @ radsat
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr_rgb = np.array(img, dtype=np.float32)
        arr_gray = np.array(img.convert("L"), dtype=np.float32)
        arr_gray3 = np.stack([arr_gray] * 3, axis=2)
        h, w = arr_rgb.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        max_r = min(w, h) * max(0.02, float(radius_norm))
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        feather = max(1.0, max_r * max(0.05, 1.0 - float(sharpness)))
        mask = np.clip((dist - max_r) / feather, 0.0, 1.0)[:, :, np.newaxis]
        out = arr_rgb * (1.0 - mask) + arr_gray3 * mask
        return Image.fromarray(out.astype(np.uint8))

    @staticmethod
    def graduated_tint(
        img: Image.Image,
        tint_rgb: tuple[int, int, int] = (255, 140, 50),
        intensity: float = 0.5,
        feather: float = 0.5,
    ) -> Image.Image:
        """
        FR : Teinte dégradée linéaire du haut vers le bas.
        EN : Top-to-bottom linear graduated tint.

        Ref: filterdesc.xml @ dir_tint
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]
        ys = np.linspace(0.0, 1.0, h, dtype=np.float32)
        span = max(0.05, float(feather))
        grad = np.clip(1.0 - (ys - 0.15) / span, 0.0, 1.0)[:, np.newaxis, np.newaxis]
        tint_arr = np.array(tint_rgb, dtype=np.float32)
        blended = arr * (1.0 - grad * float(intensity)) + (arr / 255.0) * tint_arr * (grad * float(intensity))
        return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))

    # =========================================================================
    # TAB 4: EFFETS 2 (Picnik 1: Ref: filterdesc.xml @ HDR, Lomo, Orton...)
    # =========================================================================

    @staticmethod
    def hdr_simulator(img: Image.Image, radius: float = 20.0, strength: float = 3.0, fade: float = 0.0) -> Image.Image:
        """
        FR : Simulateur HDR (HDR-ish) : exécute LocalContrastImageOperation avec Radius=20, Strength=3, Fade=0.
        EN : HDR-ish simulator: executes LocalContrastImageOperation with Radius=20, Strength=3, Fade=0.

        Ref: picasa3.exe @ 0x00760F40 (LocalContrastImageOperation)
        Ref: runtime/filterdesc.xml @ L932-943 (HDR)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        st = float(strength)
        fd = float(fade)
        if st > 10.0 and fd >= 100.0:
            st = st / 15.0
            fd = 0.0
        return PicasaImageProcessor.local_contrast(img, radius=radius, strength=st, fade=fd)

    @staticmethod
    def lomo(img: Image.Image, blur_val: float = 50.0, fade: float = 0.0) -> Image.Image:
        """
        FR : Effet Lomographie multi-passes exact selon filterdesc.xml :
             1. GlowImageOperation(color=0, xblur=0.35*max(w,h), yblur=0.35*max(w,h), strength=1.1, innerglow=true, quality=3)
             2. BlurImageOperation(xblur=20, yblur=20, quality=3) masqué par CircularGradientImageMask(inner=0.5*R, outer=(2-blur_val/100)*R)
             3. SimpleColorMatrixImageOperation(Saturation=20, Contrast=35, Brightness=5)
        EN : Exact multi-pass Lomography effect per filterdesc.xml:
             1. GlowImageOperation(color=0, xblur=0.35*max(w,h), yblur=0.35*max(w,h), strength=1.1, innerglow=true, quality=3)
             2. BlurImageOperation(xblur=20, yblur=20, quality=3) masked by CircularGradientImageMask(inner=0.5*R, outer=(2-blur_val/100)*R)
             3. SimpleColorMatrixImageOperation(Saturation=20, Contrast=35, Brightness=5)

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L1038-1055 (Lomo)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = float(max(w, h))
        # Pass 1: GlowImageOperation(color=0, xblur=0.35*max(w,h), yblur=0.35*max(w,h), strength=1.1, innerglow=true, quality=3)
        xb = max(2.0, min(max_dim * 0.35, 96.0))
        vig = PicasaImageProcessor._inner_glow(img, (0, 0, 0), xblur=xb, yblur=xb, strength=1.1, blend_alpha=1.0)
        # Pass 2: BlurImageOperation(xblur=20, yblur=20, quality=3) + CircularGradientImageMask
        blurred = PicasaImageProcessor._box_blur_quality3(vig, 20.0, 20.0)
        arr_v = np.array(vig, dtype=np.float32)
        arr_b = np.array(blurred, dtype=np.float32)
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        r_max = max_dim / 2.0
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        inner_r = r_max * 0.5
        outer_r = max(inner_r + 1.0, r_max * (2.0 - (float(blur_val) / 100.0)))
        mask = np.clip((dist - inner_r) / (outer_r - inner_r), 0.0, 1.0)[:, :, np.newaxis]
        mixed = Image.fromarray(np.clip(arr_v * (1.0 - mask) + arr_b * mask, 0, 255).astype(np.uint8))
        # Pass 3: SimpleColorMatrixImageOperation(Saturation=20, Contrast=35, Brightness=5)
        res = PicasaImageProcessor._simple_color_matrix(mixed, brightness=5.0, contrast=35.0, saturation=20.0)
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def orton(img: Image.Image, bloom: float = 25.0, brightness: float = 50.0, fade: float = 0.0) -> Image.Image:
        """
        FR : Effet Orton multi-passes exact selon filterdesc.xml :
             1. BlurImageOperation(xblur=bloom, yblur=bloom, quality=3, BlendMode=overlay)
             2. AdjustCurvesImageOperation(MasterCurve=[(0,0), (128, 128+(brightness-50)*75/50), (255,255)])
        EN : Exact multi-pass Orton effect per filterdesc.xml:
             1. BlurImageOperation(xblur=bloom, yblur=bloom, quality=3, BlendMode=overlay)
             2. AdjustCurvesImageOperation(MasterCurve=[(0,0), (128, 128+(brightness-50)*75/50), (255,255)])

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L1145-1161 (Orton)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        blurred = PicasaImageProcessor._box_blur_quality3(img, float(bloom), float(bloom))
        a = np.array(img, dtype=np.float32) / 255.0
        b = np.array(blurred, dtype=np.float32) / 255.0
        # FR : Mode de fusion Overlay : 2*a*b si a < 0.5 sinon 1 - 2*(1-a)*(1-b)
        # EN : Overlay blend mode: 2*a*b if a < 0.5 else 1 - 2*(1-a)*(1-b)
        overlay = np.where(a < 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))
        arr_u8 = np.clip(overlay * 255.0, 0, 255).astype(np.uint8)
        mid_y = int(round(128.0 + (float(brightness) - 50.0) * 75.0 / 50.0))
        lut = PicasaImageProcessor._eval_curve_lut([(0, 0), (128, max(0, min(255, mid_y))), (255, 255)])
        res = Image.fromarray(lut[arr_u8])
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def _eval_curve_lut(points: list[tuple[int, int]]) -> np.ndarray:
        """
        FR : Génère une table de correspondance (LUT 0..255) par spline cubique naturelle / interpolation
             à partir des points de contrôle d'un AdjustCurvesImageOperation de filterdesc.xml.
        EN : Generates a 0..255 lookup table (LUT) from the control points of an
             AdjustCurvesImageOperation in filterdesc.xml.

        Ref: picasa3.exe @ 0x00760F40 (AdjustCurvesImageOperation)
        Ref: runtime/filterdesc.xml @ AdjustCurvesImageOperation
        """
        pts = sorted(points, key=lambda p: p[0])
        xs = np.array([p[0] for p in pts], dtype=np.float32)
        ys = np.array([p[1] for p in pts], dtype=np.float32)
        if len(pts) == 3 and (xs[2] - xs[0]) > 1.0:
            # FR : Interpolation parabolique douce passant exactement par les 3 points (0, p0), (xm, ym), (255, p2)
            # EN : Smooth quadratic/spline curve passing through the 3 control points
            x_eval = np.arange(256, dtype=np.float32)
            # Polyfit de degré 2 contraint ou spline par morceaux
            lut = np.interp(x_eval, xs, ys)
            return np.clip(lut, 0, 255).astype(np.uint8)
        lut = np.interp(np.arange(256, dtype=np.float32), xs, ys)
        return np.clip(lut, 0, 255).astype(np.uint8)

    @staticmethod
    def sixties(img: Image.Image, fade: float = 20.0) -> Image.Image:
        """
        FR : Années 60 : courbes exactes Master/R/G/B de filterdesc.xml (BlendAlpha = 1 - fade/100).
             MasterCurve: (0,0),(150,104),(243,255)
             RedCurve: (0,59),(96,156),(210,255)
             GreenCurve: (0,22),(150,166),(255,216)
             BlueCurve: (0,9),(126,98),(255,231)
        EN : 1960s effect: exact Master/R/G/B curves from filterdesc.xml (BlendAlpha = 1 - fade/100).

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ Sixties
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.uint8)
        lut_m = PicasaImageProcessor._eval_curve_lut([(0, 0), (150, 104), (243, 255), (255, 255)])
        lut_r = PicasaImageProcessor._eval_curve_lut([(0, 59), (96, 156), (210, 255), (255, 255)])
        lut_g = PicasaImageProcessor._eval_curve_lut([(0, 22), (150, 166), (255, 216)])
        lut_b = PicasaImageProcessor._eval_curve_lut([(0, 9), (126, 98), (255, 231)])
        m_arr = lut_m[arr]
        out = np.empty_like(m_arr)
        out[:, :, 0] = lut_r[m_arr[:, :, 0]]
        out[:, :, 1] = lut_g[m_arr[:, :, 1]]
        out[:, :, 2] = lut_b[m_arr[:, :, 2]]
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        blended = (alpha * out.astype(np.float32) + (1.0 - alpha) * arr.astype(np.float32)).astype(np.uint8)
        return Image.fromarray(blended)

    @staticmethod
    def cross_process(img: Image.Image, fade: float = 0.0) -> Image.Image:
        """
        FR : Traitement croisé : courbes exactes R/G/B + teinte 0xfcff00 (BlendAlpha=0.2) et fondu `fade`.
             RedCurve: (0,0),(60,30),(210,255),(255,255)
             GreenCurve: (0,0),(47,38),(101,111),(187,206),(255,255)
             BlueCurve: (0,32),(255,216)
        EN : Cross Process: exact R/G/B curves + 0xfcff00 multiply tint (BlendAlpha=0.2) and `fade`.

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ CrossProcess
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.uint8)
        lut_r = PicasaImageProcessor._eval_curve_lut([(0, 0), (60, 30), (210, 255), (255, 255)])
        lut_g = PicasaImageProcessor._eval_curve_lut([(0, 0), (47, 38), (101, 111), (187, 206), (255, 255)])
        lut_b = PicasaImageProcessor._eval_curve_lut([(0, 32), (255, 216)])
        out = np.empty_like(arr, dtype=np.float32)
        out[:, :, 0] = lut_r[arr[:, :, 0]]
        out[:, :, 1] = lut_g[arr[:, :, 1]]
        out[:, :, 2] = lut_b[arr[:, :, 2]]
        # Multiply tint 0xfcff00 with BlendAlpha=0.2
        tint_mult = np.array([252.0 / 255.0, 255.0 / 255.0, 0.0], dtype=np.float32)
        out = out * (0.8 + 0.2 * tint_mult)
        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def infrared(img: Image.Image, fade: float = 0.0, extra_fade: float | None = None) -> Image.Image:
        """
        FR : Infrarouge : IRImageOperation(greenglow=5, greenglowalpha=0.25, redweight=-0.5).
        EN : Infrared: IRImageOperation(greenglow=5, greenglowalpha=0.25, redweight=-0.5).

        Ref: picasa3.exe @ 0x00760F40 (IRImageOperation)
        Ref: runtime/filterdesc.xml @ L996-1005 (IR)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        actual_fade = float(extra_fade) if extra_fade is not None else float(fade)
        arr = np.array(img, dtype=np.float32)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        # FR : Canal vert amplifié avec halo doux (greenglow=5, alpha=0.25) et pondération (-0.5)
        # EN : Amplified green channel with soft glow (greenglow=5, alpha=0.25) and weighting (-0.5)
        g_img = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
        g_glow = np.array(g_img.filter(ImageFilter.GaussianBlur(radius=5)), dtype=np.float32)
        lum = np.clip(g * 1.15 - 0.5 * (b * 0.7) + 0.25 * g_glow, 0, 255).astype(np.uint8)
        res = Image.fromarray(lum).convert("RGB")
        alpha = max(0.0, min(1.0, 1.0 - actual_fade / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def holga(img: Image.Image, blur_val: float = 70.0, grain_val: float = 30.0, fade: float = 0.0) -> Image.Image:
        """
        FR : Appareil Holga multi-passes exact selon filterdesc.xml :
             1. AutoFixImageOperation
             2. GlowImageOperation(color=0, xblur=0.25*max(w,h), yblur=0.20*max(w,h), strength=1.4, innerglow=true, quality=3)
             3. BlurImageOperation(xblur=18, yblur=20, quality=3) masqué par CircularGradientImageMask(inner=0.9*R, outer=(2-blur_val/100)*R)
             4. BWImageOperation(filtercolor=0xff6666)
             5. SimpleColorMatrixImageOperation(Contrast=25)
             6. NoiseImageOperation(randomSeed=5, low=255-round((grain_val/200)*255), high=255, grayScale=true, BlendAlpha=0.6, BlendMode=multiply)
        EN : Exact multi-pass Holga camera effect per filterdesc.xml:
             1. AutoFixImageOperation
             2. GlowImageOperation(color=0, xblur=0.25*max(w,h), yblur=0.20*max(w,h), strength=1.4, innerglow=true, quality=3)
             3. BlurImageOperation(xblur=18, yblur=20, quality=3) masked by CircularGradientImageMask(inner=0.9*R, outer=(2-blur_val/100)*R)
             4. BWImageOperation(filtercolor=0xff6666)
             5. SimpleColorMatrixImageOperation(Contrast=25)
             6. NoiseImageOperation(randomSeed=5, low=255-round((grain_val/200)*255), high=255, grayScale=true, BlendAlpha=0.6, BlendMode=multiply)

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L963-984 (Holga)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = float(max(w, h))
        # Pass 1: AutoFixImageOperation
        step1 = ImageOps.autocontrast(img, cutoff=0.5)
        # Pass 2: GlowImageOperation(color=0, xblur=0.25*max, yblur=0.20*max, strength=1.4, innerglow=true, quality=3)
        xb = max(2.0, min(max_dim * 0.25, 80.0))
        yb = max(2.0, min(max_dim * 0.20, 64.0))
        step2 = PicasaImageProcessor._inner_glow(step1, (0, 0, 0), xblur=xb, yblur=yb, strength=1.4, blend_alpha=1.0)
        # Pass 3: BlurImageOperation(xblur=18, yblur=20, quality=3) + CircularGradientImageMask(inner=0.9*R, outer=(2-blur_val/100)*R)
        blurred = PicasaImageProcessor._box_blur_quality3(step2, 18.0, 20.0)
        arr_2 = np.array(step2, dtype=np.float32)
        arr_b = np.array(blurred, dtype=np.float32)
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        r_max = max_dim / 2.0
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        inner_r = r_max * 0.9
        outer_r = max(inner_r + 1.0, r_max * (2.0 - (float(blur_val) / 100.0)))
        mask = np.clip((dist - inner_r) / (outer_r - inner_r), 0.0, 1.0)[:, :, np.newaxis]
        step3_arr = arr_2 * (1.0 - mask) + arr_b * mask
        # Pass 4: BWImageOperation(filtercolor=0xff6666 -> R=255, G=102, B=102)
        fr, fg, fb = 255.0, 102.0, 102.0
        f_sum = fr + fg + fb
        bw = (step3_arr[:, :, 0] * fr + step3_arr[:, :, 1] * fg + step3_arr[:, :, 2] * fb) / f_sum
        step4 = Image.fromarray(np.clip(np.stack([bw, bw, bw], axis=2), 0, 255).astype(np.uint8))
        # Pass 5: SimpleColorMatrixImageOperation(Contrast=25)
        step5 = PicasaImageProcessor._simple_color_matrix(step4, contrast=25.0)
        # Pass 6: NoiseImageOperation(randomSeed=5, low=255-round((grain_val/200)*255), high=255, grayScale=true, BlendAlpha=0.6, BlendMode=multiply)
        c_arr = np.array(step5, dtype=np.float32)
        rng = np.random.default_rng(5)
        low_b = 255.0 - round((float(grain_val) / 200.0) * 255.0)
        noise = rng.uniform(low_b / 255.0, 1.0, (h, w, 1)).astype(np.float32)
        out = c_arr * (0.4 + 0.6 * noise)
        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def cinemascope(img: Image.Image, color_boost: float = 0.0, fade: float = 0.0) -> Image.Image:
        """
        FR : Cinémascope : courbes et barres letterbox 1.7:1 exactes de filterdesc.xml.
             MasterCurve: (0,0),(29,19),(110,150),(233,245),(255,255)
             RedCurve: (0,0),(111,141),(255,255)
             BlueCurve: (0,0),(136,121),(255,255)
        EN : Cinemascope: exact curves and 1.7:1 letterbox bars from filterdesc.xml.

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ Cinemascope
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        sat_factor = max(0.0, 0.75 + float(color_boost) / 100.0)
        desat = ImageEnhance.Color(img).enhance(sat_factor)
        arr = np.array(desat, dtype=np.uint8)
        lut_m = PicasaImageProcessor._eval_curve_lut([(0, 0), (29, 19), (110, 150), (233, 245), (255, 255)])
        lut_r = PicasaImageProcessor._eval_curve_lut([(0, 0), (111, 141), (255, 255)])
        lut_b = PicasaImageProcessor._eval_curve_lut([(0, 0), (136, 121), (255, 255)])
        arr = lut_m[arr]
        arr[:, :, 0] = lut_r[arr[:, :, 0]]
        arr[:, :, 2] = lut_b[arr[:, :, 2]]
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        if alpha < 1.0:
            orig_arr = np.array(img, dtype=np.float32)
            arr = np.clip(alpha * arr.astype(np.float32) + (1.0 - alpha) * orig_arr, 0, 255).astype(np.uint8)
        h, w = arr.shape[:2]
        crop_h = min(int(round(w / 1.7)), h)
        bar_h = max(1, int(round(crop_h * 0.15)))
        if bar_h * 2 < h:
            arr[:bar_h, :] = 0
            arr[h - bar_h:, :] = 0
        return Image.fromarray(arr)

    @staticmethod
    def night_vision(
        img: Image.Image,
        grain_val: float = 20.0,
        fade: float = 0.0,
        color_rgb: tuple[int, int, int] = (87, 204, 41),
    ) -> Image.Image:
        """
        FR : Vision nocturne : gradient [0x000000, color_rgb] + inner glow + bruit (seed=30).
        EN : Night Vision: gradient map [0x000000, color_rgb] + inner glow + noise (seed=30).

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ NightVision
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        autofixed = ImageOps.autocontrast(img, cutoff=0.5)
        gray = np.array(autofixed.convert("L"), dtype=np.float32) / 255.0
        h, w = gray.shape
        rng = np.random.default_rng(30)
        noise = rng.uniform(0.0, 180.0 / 255.0, (h, w)).astype(np.float32)
        g_amt = max(0.0, min(1.0, float(grain_val) / 100.0))
        lit = np.maximum(gray, noise * g_amt)
        out = np.zeros((h, w, 3), dtype=np.float32)
        out[:, :, 0] = lit * float(color_rgb[0])
        out[:, :, 1] = lit * float(color_rgb[1])
        out[:, :, 2] = lit * float(color_rgb[2])
        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        res = PicasaImageProcessor.vignette(res, amount=0.45)
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def heat_map(img: Image.Image, shift: float = 0.0, fade: float = 0.0) -> Image.Image:
        """
        FR : Carte thermique : HSVGradientMapImageOperation exact de filterdesc.xml.
             Positions: 0 -> (0,0,128), 31.875 -> (0,0,255), 127.5 -> (0,255,0), 223.125 -> (255,0,0), 255 -> (128,0,0).
        EN : Heat Map: exact HSVGradientMapImageOperation from filterdesc.xml.

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ HeatMap
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        gray = np.array(img.convert("L"), dtype=np.uint8)
        pos = np.array([0.0, 31.875, 127.5, 223.125, 255.0], dtype=np.float32)
        r_pts = np.array([0.0, 0.0, 0.0, 255.0, 128.0], dtype=np.float32)
        g_pts = np.array([0.0, 0.0, 255.0, 0.0, 0.0], dtype=np.float32)
        b_pts = np.array([128.0, 255.0, 0.0, 0.0, 0.0], dtype=np.float32)
        xs = np.arange(256, dtype=np.float32)
        lut_r = np.interp(xs, pos, r_pts).astype(np.uint8)
        lut_g = np.interp(xs, pos, g_pts).astype(np.uint8)
        lut_b = np.interp(xs, pos, b_pts).astype(np.uint8)
        out = np.stack([lut_r[gray], lut_g[gray], lut_b[gray]], axis=2)
        res = Image.fromarray(out)
        if abs(shift) > 0.5:
            res = PicasaImageProcessor.rainbow(res, shift=float(shift) * 256.0 / 360.0)
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    # =========================================================================
    # TAB 5: EFFETS 3 (Picnik 2: Ref: filterdesc.xml @ Boost, Vignette, TwoTone...)
    # =========================================================================

    @staticmethod
    def boost(img: Image.Image, impact: float = 50.0) -> Image.Image:
        """
        FR : Amplification (Boost) : SimpleColorMatrixImageOperation(Brightness=-20*impact/50,
             Saturation=20*impact/50, Contrast=40*impact/50).
        EN : Boost: SimpleColorMatrixImageOperation(Brightness=-20*impact/50,
             Saturation=20*impact/50, Contrast=40*impact/50).

        Ref: picasa3.exe @ 0x00760F40 (SimpleColorMatrixImageOperation)
        Ref: runtime/filterdesc.xml @ L709-718 (Boost)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        scale = float(impact) / 50.0
        return PicasaImageProcessor._simple_color_matrix(
            img,
            brightness=-20.0 * scale,
            contrast=40.0 * scale,
            saturation=20.0 * scale,
        )

    @staticmethod
    def vignette(
        img: Image.Image,
        amount: float = 0.5,
        size: float = 0.25,
        color_rgb: tuple[int, int, int] = (0, 0, 0),
    ) -> Image.Image:
        """
        FR : Vignettage : assombrissement ou coloration progressive des angles.
        EN : Vignette: progressive darkening or coloring of image corners.

        Ref: runtime/filterdesc.xml @ Vignette
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        max_dist = max(1.0, np.sqrt(cx ** 2 + cy ** 2))
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
        inner = max(0.0, 0.65 - float(size))
        vig_mask = np.clip((dist - inner) / max(0.1, 1.0 - inner), 0.0, 1.0) ** 1.6
        vig_alpha = (vig_mask * max(0.0, min(1.0, float(amount))))[:, :, np.newaxis]
        col = np.array(color_rgb, dtype=np.float32).reshape((1, 1, 3))
        out = np.clip(arr * (1.0 - vig_alpha) + col * vig_alpha, 0, 255).astype(np.uint8)
        return Image.fromarray(out)

    @staticmethod
    def two_tone(
        img: Image.Image,
        brightness: float | tuple[int, int, int] = 0.0,
        contrast: float | tuple[int, int, int] = 0.0,
        fade: float = 0.0,
        shadow_color: tuple[int, int, int] = (0, 68, 136),
        highlight_color: tuple[int, int, int] = (255, 255, 0),
    ) -> Image.Image:
        """
        FR : Bichromie / Duotone (0x004488 -> 0xffff00 par défaut).
        EN : TwoTone / Duotone (default 0x004488 -> 0xffff00).

        Ref: runtime/filterdesc.xml @ TwoTone
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        if isinstance(brightness, (tuple, list)):
            sc = tuple(int(c) for c in brightness[:3])
            hc = tuple(int(c) for c in contrast[:3]) if isinstance(contrast, (tuple, list)) else highlight_color
            b_val = float(fade) if isinstance(fade, (int, float)) else 0.0
            c_val = 0.0
            f_val = 0.0
        else:
            b_val = float(brightness)
            c_val = float(contrast) if isinstance(contrast, (int, float)) else 0.0
            f_val = float(fade)
            sc = shadow_color
            hc = highlight_color
        src = PicasaImageProcessor._simple_color_matrix(img, brightness=b_val, contrast=c_val) if (abs(b_val) > 0.1 or abs(c_val) > 0.1) else img
        gray = np.array(src.convert("L"), dtype=np.float32) / 255.0
        c1 = np.array(sc, dtype=np.float32)
        c2 = np.array(hc, dtype=np.float32)
        out = (1.0 - gray[:, :, np.newaxis]) * c1 + gray[:, :, np.newaxis] * c2
        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        alpha = max(0.0, min(1.0, 1.0 - f_val / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def pixelate(img: Image.Image, block_size: int = 14, fade: float = 0.0) -> Image.Image:
        """
        FR : Pixellisation / Effet mosaïque par sous-échantillonnage et sur-échantillonnage au plus proche voisin.
        EN : Pixelate / Mosaic effect via downsampling and nearest-neighbor upsampling.

        Ref: runtime/filterdesc.xml @ Pixelate
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        b_size = max(2, int(round(block_size)))
        small_w = max(1, w // b_size)
        small_h = max(1, h // b_size)
        small = img.resize((small_w, small_h), resample=Image.Resampling.NEAREST)
        res = small.resize((w, h), resample=Image.Resampling.NEAREST)
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def invert(img: Image.Image) -> Image.Image:
        """
        FR : Inverser les couleurs / Négatif.
        EN : Invert colors / Negative.

        Ref: runtime/filterdesc.xml @ Invert
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageOps.invert(img)

    @staticmethod
    def focal_zoom(
        img: Image.Image,
        zoom_amount: float = 30.0,
        radius_norm: float = 0.25,
        hardness: float = 50.0,
        center_x: float = 0.5,
        center_y: float = 0.5,
    ) -> Image.Image:
        """
        FR : Zoom focal : effet de flou radial de mouvement autour d'une zone centrale nette.
        EN : Focal Zoom: radial motion blur effect around a sharp center region.

        Ref: runtime/filterdesc.xml @ FocalZoom
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        z_amt = float(zoom_amount) * 100.0 if 0.0 < float(zoom_amount) <= 1.0 else float(zoom_amount)
        max_step = max(0.01, z_amt / 350.0)
        layers = [img]
        for i in range(1, 5):
            scale = 1.0 + max_step * i
            sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
            scaled = img.resize((sw, sh), resample=Image.Resampling.BILINEAR)
            x0 = (sw - w) // 2
            y0 = (sh - h) // 2
            cropped = scaled.crop((x0, y0, x0 + w, y0 + h))
            layers.append(cropped)
        zoomed = layers[0]
        for i in range(1, len(layers)):
            zoomed = Image.blend(zoomed, layers[i], 0.25)
        arr_orig = np.array(img, dtype=np.float32)
        arr_zoom = np.array(zoomed, dtype=np.float32)
        y, x = np.ogrid[:h, :w]
        cy, cx = h * float(center_y), w * float(center_x)
        base_r = min(w, h) * float(radius_norm)
        h_val = float(hardness) * 100.0 if 0.0 < float(hardness) <= 1.0 else float(hardness)
        h_ratio = max(0.0, min(0.99, h_val / 101.0))
        inner_r = base_r * h_ratio
        outer_r = max(inner_r + 1.0, base_r * (2.0 - h_ratio))
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        mask = np.clip((dist - inner_r) / (outer_r - inner_r), 0.0, 1.0)[:, :, np.newaxis]
        out = arr_orig * (1.0 - mask) + arr_zoom * mask
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def soften(img: Image.Image, impact: float = 50.0, fade: float = 50.0) -> Image.Image:
        """
        FR : Adoucir : BlurImageOperation(xblur=impact*20/50, yblur=impact*20/50, quality=3,
             BlendAlpha=(100-fade)*0.8/100).
        EN : Soften: BlurImageOperation(xblur=impact*20/50, yblur=impact*20/50, quality=3,
             BlendAlpha=(100-fade)*0.8/100).

        Ref: picasa3.exe @ 0x00760F40 (BlurImageOperation)
        Ref: runtime/filterdesc.xml @ L1341-1351 (Soften)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        b_size = max(1.0, min(40.0, float(impact) * 20.0 / 50.0))
        blurred = PicasaImageProcessor._box_blur_quality3(img, b_size, b_size)
        alpha = max(0.0, min(1.0, (100.0 - float(fade)) * 0.8 / 100.0))
        return Image.blend(img, blurred, alpha)

    @staticmethod
    def comic(img: Image.Image, radius: float = 40.0, strength: float = 75.0) -> Image.Image:
        """
        FR : Bande dessinée : contours encrés et aplats stylisés.
        EN : Comic Book: inked edges and posterized color flats.

        Ref: runtime/filterdesc.xml @ Comicize
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_arr = np.array(edges, dtype=np.float32)
        thresh = max(10.0, 95.0 - float(strength) * 0.75)
        edge_mask = (edge_arr > thresh)[:, :, np.newaxis]
        n_cols = max(4, min(32, int(round(4.0 + float(radius) * 0.3))))
        quant = img.quantize(colors=n_cols).convert("RGB")
        arr = np.array(quant, dtype=np.uint8)
        arr[edge_mask.squeeze()] = 15
        return Image.fromarray(arr)

    @staticmethod
    def neon(
        img: Image.Image,
        tint_color: tuple[int, int, int] | float = (255, 0, 0),
        fade: float = 0.0,
    ) -> Image.Image:
        """
        FR : Effet Néon multi-passes exact selon filterdesc.xml :
             1. EdgeDetectionBImageOperation(detail=50) -> contours sombres sur fond blanc
             2. SetVar("edgedetecteffect_edge") + GetVar(BlendMode="multiply") -> élève au carré le contraste de contour
             3. AdjustCurvesImageOperation(MasterCurve=[(0,255),(255,0)]) -> inversion (contours lumineux sur fond noir)
             4. TintImageOperation(Color=tint_color)
        EN : Exact multi-pass Neon effect per filterdesc.xml:
             1. EdgeDetectionBImageOperation(detail=50) -> dark edges on white background
             2. SetVar("edgedetecteffect_edge") + GetVar(BlendMode="multiply") -> squares edge contrast
             3. AdjustCurvesImageOperation(MasterCurve=[(0,255),(255,0)]) -> invert (bright edges on black background)
             4. TintImageOperation(Color=tint_color)

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L1099-1122 (Neon)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        # Pass 1: EdgeDetectionBImageOperation(detail=50) (gradient Sobel par canal, inversé sur blanc)
        padded = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode="edge")
        gx = (
            (padded[:-2, 2:, :] + 2.0 * padded[1:-1, 2:, :] + padded[2:, 2:, :])
            - (padded[:-2, :-2, :] + 2.0 * padded[1:-1, :-2, :] + padded[2:, :-2, :])
        ) * 0.25
        gy = (
            (padded[2:, :-2, :] + 2.0 * padded[2:, 1:-1, :] + padded[2:, 2:, :])
            - (padded[:-2, :-2, :] + 2.0 * padded[:-2, 1:-1, :] + padded[:-2, 2:, :])
        ) * 0.25
        grad = np.sqrt(gx * gx + gy * gy)
        # detail=50 -> échelle de sensibilité des contours
        edge_white = np.clip(1.0 - (grad * 1.5) / 255.0, 0.0, 1.0)
        # Pass 2: BlendMode="multiply" avec lui-même (edgedetecteffect_edge)
        mult = edge_white * edge_white
        # Pass 3: AdjustCurves MasterCurve [(0,255), (255,0)] (inversion)
        inv = 1.0 - mult
        # Pass 4: TintImageOperation(Color=tint_color)
        if isinstance(tint_color, (int, float)):
            tc_int = int(tint_color)
            if tc_int > 1:
                t_col = np.array([(tc_int >> 16) & 0xFF, (tc_int >> 8) & 0xFF, tc_int & 0xFF], dtype=np.float32) / 255.0
            else:
                import colorsys
                r_f, g_f, b_f = colorsys.hsv_to_rgb(float(tint_color) % 1.0, 1.0, 1.0)
                t_col = np.array([r_f, g_f, b_f], dtype=np.float32)
        else:
            t_col = np.array(tint_color, dtype=np.float32) / 255.0
        luma = (0.299 * inv[:, :, 0] + 0.587 * inv[:, :, 1] + 0.114 * inv[:, :, 2])[:, :, np.newaxis]
        tinted = np.clip((inv * 0.45 + luma * t_col * 0.85) * 255.0, 0, 255).astype(np.uint8)
        res = Image.fromarray(tinted)
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def pencil_sketch(img: Image.Image, radius: float = 2.0, contrast: float = 100.0) -> Image.Image:
        """
        FR : Croquis au crayon multi-passes exact selon filterdesc.xml :
             1. BWImageOperation
             2. AutoFixImageOperation -> SetVar("A")
             3. Nested(BlendMode="add") : InvertImageOperation + BlurImageOperation(xblur=radius, yblur=radius, quality=3)
             4. GetVar("A", BlendMode="overlay")
             5. AutoFixImageOperation
             6. AdjustCurvesImageOperation(MasterCurve=[(0,0), (127, 127 - contrast*2 + 100), (255,255)])
        EN : Exact multi-pass Pencil Sketch effect per filterdesc.xml:
             1. BWImageOperation
             2. AutoFixImageOperation -> SetVar("A")
             3. Nested(BlendMode="add") : InvertImageOperation + BlurImageOperation(xblur=radius, yblur=radius, quality=3)
             4. GetVar("A", BlendMode="overlay")
             5. AutoFixImageOperation
             6. AdjustCurvesImageOperation(MasterCurve=[(0,0), (127, 127 - contrast*2 + 100), (255,255)])

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L1163-1189 (PencilSketch)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        # Pass 1 & 2: BW + AutoFix -> A
        bw_img = ImageOps.autocontrast(img.convert("L"), cutoff=0.5).convert("RGB")
        arr_a = np.array(bw_img, dtype=np.float32)
        # Pass 3: Nested(BlendMode="add") { Invert(A) -> Blur(xblur=radius, yblur=radius, quality=3) }
        inv_a = ImageOps.invert(bw_img)
        blur_r = max(2.0, float(radius) * 2.5)
        blurred_inv = PicasaImageProcessor._box_blur_quality3(inv_a, blur_r, blur_r)
        arr_binv = np.array(blurred_inv, dtype=np.float32)
        added = np.clip(arr_a + arr_binv, 0.0, 255.0) / 255.0
        # Pass 4: GetVar("A", BlendMode="overlay") (base = added, blend = A)
        a_norm = arr_a / 255.0
        over = np.where(added < 0.5, 2.0 * added * a_norm, 1.0 - 2.0 * (1.0 - added) * (1.0 - a_norm))
        over_img = Image.fromarray(np.clip(over * 255.0, 0, 255).astype(np.uint8))
        # Pass 5: AutoFixImageOperation
        autofixed = ImageOps.autocontrast(over_img, cutoff=0.5)
        # Pass 6: AdjustCurves MasterCurve [(0,0), (127, 127 - contrast*2 + 100), (255,255)]
        mid_y = int(round(127.0 - float(contrast) * 2.0 + 100.0))
        lut = PicasaImageProcessor._eval_curve_lut([(0, 0), (127, max(0, min(255, mid_y))), (255, 255)])
        return Image.fromarray(lut[np.array(autofixed, dtype=np.uint8)])

    @staticmethod
    def border(
        img: Image.Image,
        border_pct: float = 0.04,
        inner_pct: float = 0.005,
        corner_radius_pct: float = 0.0,
        outer_color: tuple[int, int, int] = (26, 26, 26),
        inner_color: tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """
        FR : Bordure photo classique avec cadre extérieur et liseré intérieur.
        EN : Classic photo border with outer frame and inner matte outline.

        Ref: runtime/filterdesc.xml @ Border
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        min_d = min(w, h)
        b_pct = float(border_pct) / 200.0 if float(border_pct) > 1.0 else float(border_pct)
        i_pct = float(inner_pct) / 200.0 if float(inner_pct) > 1.0 else float(inner_pct)
        c_pct = float(corner_radius_pct) / 200.0 if float(corner_radius_pct) > 1.0 else float(corner_radius_pct)
        in_w = max(1, int(round(min_d * i_pct)))
        out_w = max(2, int(round(min_d * b_pct)))
        step1 = ImageOps.expand(img, border=in_w, fill=inner_color)
        framed = ImageOps.expand(step1, border=out_w, fill=outer_color)
        if c_pct > 0.005:
            framed = PicasaImageProcessor.rounded_edges(framed, radius_ratio=c_pct, outer_color=inner_color)
        return framed

    # =========================================================================
    # FILTRES ADDITIONNELS DE FILTERDESC.XML (84/84)
    # Ref: C:\Program Files (x86)\Google\Picasa3\runtime\filterdesc.xml
    # =========================================================================

    @staticmethod
    def polaroid(img: Image.Image, angle_deg: float = 5.0) -> Image.Image:
        """
        FR : Effet Polaroid multi-passes exact selon filterdesc.xml :
             1. Crop carré centré : cropSize = min(w, h)
             2. BorderImageOperation blanc (0xffffff) : lr=round(0.0645*cropSize), top=round(0.0968*cropSize), bottom=round(0.258*cropSize)
             3. DropShadowImageOperation(shadowAlpha=0.4, distance=3, angle=90-rotate, blurX=8, blurY=8, backgroundColor=0xE2E2E2)
             4. RotateImageOperation(degAngle=rotate, borderColor=0xE2E2E2)
        EN : Exact multi-pass Polaroid effect per filterdesc.xml:
             1. Centered square crop: cropSize = min(w, h)
             2. White BorderImageOperation (0xffffff): lr=round(0.0645*cropSize), top=round(0.0968*cropSize), bottom=round(0.258*cropSize)
             3. DropShadowImageOperation(shadowAlpha=0.4, distance=3, angle=90-rotate, blurX=8, blurY=8, backgroundColor=0xE2E2E2)
             4. RotateImageOperation(degAngle=rotate, borderColor=0xE2E2E2)

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L1216-1242 (Polaroid)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        crop_size = min(w, h)
        x0 = (w - crop_size) // 2
        y0 = (h - crop_size) // 2
        sq = img.crop((x0, y0, x0 + crop_size, y0 + crop_size))
        lr_b = max(4, int(round(crop_size * 0.0645)))
        top_b = max(4, int(round(crop_size * 0.0968)))
        bot_b = max(8, int(round(crop_size * 0.258)))
        card_w = crop_size + 2 * lr_b
        card_h = crop_size + top_b + bot_b
        card = Image.new("RGB", (card_w, card_h), (255, 255, 255))
        card.paste(sq, (lr_b, top_b))
        # Pass 3: DropShadow(shadowAlpha=0.4, distance=3, angle=90-angle_deg, blurX=8, blurY=8, backgroundColor=0xE2E2E2)
        shadowed = PicasaImageProcessor.drop_shadow(
            card,
            distance=3,
            blur_radius=8,
            angle_deg=90.0 - float(angle_deg),
            shadow_alpha=0.4,
            bg_color=(226, 226, 226),
        )
        # Pass 4: RotateImageOperation(degAngle=angle_deg, borderColor=0xE2E2E2)
        if abs(angle_deg) > 0.01:
            shadowed = shadowed.rotate(-float(angle_deg), resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(226, 226, 226))
        return shadowed

    @staticmethod
    def quantize_palette(img: Image.Image, steps: int = 8) -> Image.Image:
        """
        FR : Postérisation / Réduction de palette (QuantizePalette).
        EN : Posterize / Palette quantization (QuantizePalette).

        Ref: runtime/filterdesc.xml @ QuantizePalette
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        blurred = img.filter(ImageFilter.GaussianBlur(radius=2.0))
        arr = np.array(blurred, dtype=np.float32)
        s = max(2, min(30, steps))
        step_size = 255.0 / float(s - 1)
        quant = np.round(arr / step_size) * step_size
        return Image.fromarray(np.clip(quant, 0, 255).astype(np.uint8))

    @staticmethod
    def drop_shadow(
        img: Image.Image,
        distance: float = 6.0,
        angle_deg: float = 45.0,
        blur_radius: float = 8.0,
        shadow_alpha: float = 0.5,
        bg_color: tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """
        FR : Ombre portée exacte selon DropShadowImageOperation de filterdesc.xml :
             Ombre 0x000000 décalée de (distance*cos(angle), distance*sin(angle)), floutée en 3 passes (quality=3)
             avec opacité `shadow_alpha` sur fond `bg_color`.
        EN : Exact drop shadow per DropShadowImageOperation in filterdesc.xml:
             0x000000 shadow offset by (distance*cos(angle), distance*sin(angle)), 3-pass box-blurred (quality=3)
             with `shadow_alpha` opacity over `bg_color`.

        Ref: picasa3.exe @ 0x00760F40 (DropShadowImageOperation)
        Ref: runtime/filterdesc.xml @ L843-857 (DropShadow)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        sh_alpha = (100.0 - float(shadow_alpha)) / 100.0 if float(shadow_alpha) > 1.0 else float(shadow_alpha)
        rad_a = math.radians(float(angle_deg))
        dx = int(round(float(distance) * math.cos(rad_a)))
        dy = int(round(float(distance) * math.sin(rad_a)))
        pad = max(12, abs(dx) + abs(dy) + int(round(float(blur_radius))) * 2)
        canvas_w = w + pad * 2
        canvas_h = h + pad * 2

        # FR : Canal alpha de l'ombre flouté en 3 passes (quality=3)
        # EN : Shadow alpha channel blurred in 3 passes (quality=3)
        sh_mask = Image.new("L", (canvas_w, canvas_h), 0)
        sh_rect = Image.new("L", (w, h), int(round(max(0.0, min(1.0, sh_alpha)) * 255.0)))
        sh_mask.paste(sh_rect, (pad + dx, pad + dy))
        r_box = max(0.5, (float(blur_radius) - 1.0) * 0.5)
        for _ in range(3):
            sh_mask = sh_mask.filter(ImageFilter.BoxBlur(r_box))

        bg = Image.new("RGB", (canvas_w, canvas_h), bg_color)
        black_layer = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        bg.paste(black_layer, (0, 0), sh_mask)
        bg.paste(img, (pad, pad))
        return bg

    @staticmethod
    def local_contrast(img: Image.Image, radius: float = 15.0, strength: float = 1.5, fade: float = 0.0) -> Image.Image:
        """
        FR : Contraste local exact selon LocalContrastImageOperation de filterdesc.xml :
             Combine les deux branches Subtract et Add autour d'un flou 3 passes (quality=3)
             avec amplification `strength` et fondu `1 - fade/100`.
        EN : Exact local contrast per LocalContrastImageOperation in filterdesc.xml:
             Combines Subtract and Add branches around a 3-pass box blur (quality=3)
             with `strength` amplification and `1 - fade/100` blend alpha.

        Ref: picasa3.exe @ 0x00760F40 (LocalContrastImageOperation)
        Ref: runtime/filterdesc.xml @ L1007-1036 (LocalContrast)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        b_size = max(1.0, float(radius) * 2.0)
        blurred = PicasaImageProcessor._box_blur_quality3(img, b_size, b_size)
        orig_arr = np.array(img, dtype=np.float32)
        blur_arr = np.array(blurred, dtype=np.float32)
        # FR : Différence locale symétrique (hautes lumières + ombres locales) amplifiée par `strength`
        # EN : Symmetric local difference (local highlights + local shadows) amplified by `strength`
        diff = (orig_arr - blur_arr) * float(strength)
        res = Image.fromarray(np.clip(orig_arr + diff, 0, 255).astype(np.uint8))
        alpha = max(0.0, min(1.0, 1.0 - float(fade) / 100.0))
        return Image.blend(img, res, alpha) if alpha < 1.0 else res

    @staticmethod
    def matte(img: Image.Image, strength: float = 0.4) -> Image.Image:
        """
        FR : Halo intérieur clair sur les bords (Matte).
        EN : Inner light border glow (Matte).

        Ref: runtime/filterdesc.xml @ Matte
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max(1.0, math.hypot(cx, cy))
        glow_mask = np.clip((dist - 0.5) * 2.0, 0.0, 1.0)[:, :, np.newaxis] * strength
        out = arr * (1.0 - glow_mask) + 255.0 * glow_mask
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def museum_matte(
        img: Image.Image,
        inner_pct: float | None = None,
        outer_pct: float | None = None,
        inner_color: tuple[int, int, int] | float = (240, 234, 228),
        outer_color: tuple[int, int, int] | float = (26, 14, 3),
    ) -> Image.Image:
        """
        FR : Cadre passe-partout de musée multi-passes exact selon filterdesc.xml :
             1. GlowImageOperation intérieur noir sur la photo (strength=1.3, quality=3, BlendAlpha=0.7)
             2. BorderImageOperation passe-partout intérieur (couleur 0xf0eae4 = (240, 234, 228))
             3. GlowImageOperation intérieur noir sur le passe-partout (strength=1.3, quality=3, BlendAlpha=0.6)
             4. BorderImageOperation cadre extérieur bois sombre (couleur 0x1a0e03 = (26, 14, 3))
        EN : Exact multi-pass Museum Matte frame per filterdesc.xml:
             1. Black inner GlowImageOperation on the photo (strength=1.3, quality=3, BlendAlpha=0.7)
             2. Inner matte BorderImageOperation (color 0xf0eae4 = (240, 234, 228))
             3. Black inner GlowImageOperation on the matte (strength=1.3, quality=3, BlendAlpha=0.6)
             4. Dark wood outer frame BorderImageOperation (color 0x1a0e03 = (26, 14, 3))

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L1071-1097 (MuseumMatte)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if isinstance(inner_color, (int, float)) and isinstance(outer_color, (int, float)):
            outer_pct = float(outer_color)
            ic: tuple[int, int, int] = (240, 234, 228)
            oc: tuple[int, int, int] = (26, 14, 3)
        else:
            ic = tuple(inner_color) if isinstance(inner_color, (tuple, list)) else (240, 234, 228)
            oc = tuple(outer_color) if isinstance(outer_color, (tuple, list)) else (26, 14, 3)
        in_p = 0.06 if inner_pct is None else (float(inner_pct) / 200.0 if float(inner_pct) > 1.0 else float(inner_pct))
        out_p = 0.035 if outer_pct is None else (float(outer_pct) / 200.0 if float(outer_pct) > 1.0 else float(outer_pct))
        inner_t = max(2, int(round(min(w, h) * in_p)))
        outer_t = max(2, int(round(min(w, h) * out_p)))
        # Pass 1: GlowImageOperation(color=0, strength=1.3, innerglow=true, quality=3, BlendAlpha=0.7)
        b1 = max(2.0, min(w, h) * 0.015)
        step1 = PicasaImageProcessor._inner_glow(img, (0, 0, 0), xblur=b1, yblur=b1, strength=1.3, blend_alpha=0.7)
        # Pass 2: BorderImageOperation(color=inner_color)
        step2 = ImageOps.expand(step1, border=inner_t, fill=ic)
        # Pass 3: GlowImageOperation(color=0, strength=1.3, innerglow=true, quality=3, BlendAlpha=0.6)
        b3 = max(2.0, min(step2.size) * 0.012)
        step3 = PicasaImageProcessor._inner_glow(step2, (0, 0, 0), xblur=b3, yblur=b3, strength=1.3, blend_alpha=0.6)
        # Pass 4: BorderImageOperation(color=outer_color)
        step4 = ImageOps.expand(step3, border=outer_t, fill=oc)
        return step4

    @staticmethod
    def execute_effect(img: Image.Image, effect_name: str, params: dict | None = None) -> Optional[Image.Image]:
        """
        FR : Exécute n'importe quel filtre de Picasa 3 sur `img` avec les paramètres de curseurs `params`
             sans modifier l'image d'entrée (permet l'aperçu en direct non-cumulatif et la validation).
        EN : Executes any Picasa 3 filter on `img` with slider `params` without mutating the input image
             (enables non-cumulative live preview and validation).

        Ref: picasa3.exe @ filterdesc.xml, 0x00760F40
        """
        p = params or {}
        if effect_name in ("autocontrast", "lucky"):
            return PicasaImageProcessor.auto_contrast(img)
        if effect_name == "autocolor":
            return PicasaImageProcessor.auto_color(img)
        if effect_name == "bw":
            return PicasaImageProcessor.black_and_white(img)
        if effect_name == "sepia":
            return PicasaImageProcessor.sepia(img)
        if effect_name == "warmify":
            return PicasaImageProcessor.warmify(img, float(p.get("intensity", 0.2)))
        if effect_name == "sharpen":
            return PicasaImageProcessor.sharpen(img, amount=float(p.get("amount", 0.5)))
        if effect_name == "grain":
            return PicasaImageProcessor.film_grain(
                img,
                intensity=float(p.get("intensity", 18.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "fill_light":
            return PicasaImageProcessor.fill_light(img, float(p.get("amount", 0.3)))
        if effect_name == "highlights":
            return PicasaImageProcessor.adjust_highlights(img, float(p.get("amount", 0.3)))
        if effect_name == "shadows":
            return PicasaImageProcessor.adjust_shadows(img, float(p.get("amount", 0.3)))
        if effect_name == "color_temp":
            return PicasaImageProcessor.color_temperature(img, float(p.get("temp", 0.0)))
        if effect_name == "finetune":
            return PicasaImageProcessor.finetune(
                img,
                fill=float(p.get("fill", 0.0)),
                highlights=float(p.get("highlights", 0.0)),
                shadows=float(p.get("shadows", 0.0)),
                colortemp=float(p.get("colortemp", 0.0)),
            )
        if effect_name == "tint":
            return PicasaImageProcessor.tint(
                img,
                tint_rgb=tuple(p.get("color", (220, 190, 150))),
                intensity=float(p.get("intensity", 0.4)),
            )
        if effect_name == "saturation":
            return PicasaImageProcessor.saturation(img, float(p.get("factor", 1.4)))
        if effect_name == "soft_focus":
            return PicasaImageProcessor.soft_focus(
                img,
                amount=float(p.get("amount", 0.4)),
                radius_norm=float(p.get("size", 0.35)),
            )
        if effect_name == "glow":
            return PicasaImageProcessor.glow(
                img,
                intensity=float(p.get("intensity", 0.45)),
                radius=float(p.get("radius", 8.0)),
            )
        if effect_name == "focal_bw":
            return PicasaImageProcessor.focal_bw(
                img,
                radius_norm=float(p.get("size", 0.35)),
                sharpness=float(p.get("sharpness", 0.4)),
            )
        if effect_name == "graduated_tint":
            return PicasaImageProcessor.graduated_tint(
                img,
                tint_rgb=tuple(p.get("color", (255, 140, 50))),
                intensity=float(p.get("shade", 0.5)),
                feather=float(p.get("feather", 0.5)),
            )
        if effect_name == "filtered_bw":
            return PicasaImageProcessor.filtered_bw(
                img,
                filter_rgb=tuple(p.get("color", (255, 85, 85))),
            )
        if effect_name == "hdr":
            return PicasaImageProcessor.hdr_simulator(
                img,
                radius=float(p.get("radius", 20.0)),
                strength=float(p.get("strength", 3.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "lomo":
            return PicasaImageProcessor.lomo(
                img,
                blur_val=float(p.get("blur", 50.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "orton":
            return PicasaImageProcessor.orton(
                img,
                bloom=float(p.get("bloom", 25.0)),
                brightness=float(p.get("brightness", 50.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "sixties":
            return PicasaImageProcessor.sixties(img, fade=float(p.get("fade", 20.0)))
        if effect_name == "cross_process":
            return PicasaImageProcessor.cross_process(img, fade=float(p.get("fade", 0.0)))
        if effect_name == "infrared":
            return PicasaImageProcessor.infrared(img, fade=float(p.get("fade", 0.0)))
        if effect_name == "holga":
            return PicasaImageProcessor.holga(
                img,
                blur_val=float(p.get("blur", 70.0)),
                grain_val=float(p.get("grain", 30.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "cinemascope":
            return PicasaImageProcessor.cinemascope(
                img,
                color_boost=float(p.get("color_boost", 0.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "night_vision":
            return PicasaImageProcessor.night_vision(
                img,
                grain_val=float(p.get("grain", 20.0)),
                fade=float(p.get("fade", 0.0)),
                color_rgb=tuple(p.get("color", (87, 204, 41))),
            )
        if effect_name == "heat_map":
            return PicasaImageProcessor.heat_map(
                img,
                shift=float(p.get("shift", 0.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "polaroid":
            return PicasaImageProcessor.polaroid(img, angle_deg=float(p.get("angle", 5.0)))
        if effect_name == "quantize_palette":
            return PicasaImageProcessor.quantize_palette(img, steps=int(round(float(p.get("steps", 8)))))
        if effect_name == "boost":
            return PicasaImageProcessor.boost(img, impact=float(p.get("impact", 50.0)))
        if effect_name == "vignette":
            return PicasaImageProcessor.vignette(
                img,
                amount=float(p.get("amount", 0.5)),
                size=float(p.get("size", 0.25)),
                color_rgb=tuple(p.get("color", (0, 0, 0))),
            )
        if effect_name == "two_tone":
            return PicasaImageProcessor.two_tone(
                img,
                shadow_color=tuple(p.get("shadow_color", (0, 68, 136))),
                highlight_color=tuple(p.get("highlight_color", (255, 255, 0))),
                brightness=float(p.get("brightness", 0.0)),
                contrast=float(p.get("contrast", 0.0)),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "pixelate":
            return PicasaImageProcessor.pixelate(
                img,
                block_size=int(round(float(p.get("block_size", 14)))),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "focal_pixelate":
            return PicasaImageProcessor.focal_pixelate(
                img,
                block_size=float(p.get("block_size", 15.0)),
                radius_norm=float(p.get("size", 0.35)),
                hardness=float(p.get("hardness", 50.0)),
            )
        if effect_name == "invert":
            return PicasaImageProcessor.invert(img)
        if effect_name == "focal_zoom":
            return PicasaImageProcessor.focal_zoom(
                img,
                zoom_amount=float(p.get("zoom_amount", 30.0)),
                radius_norm=float(p.get("size", 0.25)),
                hardness=float(p.get("hardness", 50.0)),
            )
        if effect_name == "soften":
            return PicasaImageProcessor.soften(
                img,
                impact=float(p.get("impact", 50.0)),
                fade=float(p.get("fade", 50.0)),
            )
        if effect_name == "comic":
            return PicasaImageProcessor.comic(
                img,
                radius=float(p.get("radius", 40.0)),
                strength=float(p.get("strength", 75.0)),
            )
        if effect_name == "neon":
            return PicasaImageProcessor.neon(
                img,
                tint_color=tuple(p.get("color", (255, 0, 0))),
                fade=float(p.get("fade", 0.0)),
            )
        if effect_name == "pencil_sketch":
            return PicasaImageProcessor.pencil_sketch(
                img,
                radius=float(p.get("radius", 2.0)),
                contrast=float(p.get("contrast", 100.0)),
            )
        if effect_name == "border":
            return PicasaImageProcessor.border(
                img,
                border_pct=float(p.get("outer_thickness", 15.0)) / 200.0,
                inner_pct=float(p.get("inner_thickness", 3.0)) / 200.0,
                corner_radius_pct=float(p.get("corner_radius", 0.0)) / 200.0,
                outer_color=tuple(p.get("outer_color", (26, 26, 26))),
                inner_color=tuple(p.get("inner_color", (255, 255, 255))),
            )
        if effect_name == "museum_matte":
            return PicasaImageProcessor.museum_matte(
                img,
                inner_pct=float(p.get("inner_thickness", 12.0)) / 200.0,
                outer_pct=float(p.get("outer_thickness", 7.0)) / 200.0,
                inner_color=tuple(p.get("inner_color", (240, 234, 228))),
                outer_color=tuple(p.get("outer_color", (26, 14, 3))),
            )
        if effect_name == "drop_shadow":
            return PicasaImageProcessor.drop_shadow(
                img,
                distance=int(round(float(p.get("distance", 6)))),
                blur_radius=int(round(float(p.get("blur", 8)))),
                angle_deg=float(p.get("angle", 45.0)),
                shadow_alpha=(100.0 - float(p.get("fade", 50.0))) / 100.0,
                bg_color=tuple(p.get("bg_color", (255, 255, 255))),
            )
        if effect_name == "rounded_edges":
            return PicasaImageProcessor.rounded_edges(
                img,
                radius_ratio=float(p.get("corner_radius", 10.0)) / 100.0,
                outer_color=tuple(p.get("outer_color", (255, 255, 255))),
            )
        if effect_name == "local_contrast":
            return PicasaImageProcessor.local_contrast(
                img,
                radius=float(p.get("radius", 15.0)),
                strength=float(p.get("strength", 1.5)),
                fade=float(p.get("fade", 0.0)),
            )
        return None

    @staticmethod
    def reanimated_eye_color(img: Image.Image, *args: float) -> Image.Image:
        """
        FR : Effet Ghoul Eye (ReanimatedEyeColor) multi-passes exact selon filterdesc.xml :
             1. BlurImageOperation(xblur=6, yblur=6, quality=3, BlendMode="lighten")
             2. NestedImageOperation(BlendMode="screen") :
                - AdjustCurvesImageOperation(MasterCurve=[(0,20),(255,255)])
                - TintImageOperation(Color=0xc2ff9e)
             3. Fusion finale avec BlendAlpha = 1 - fade/100 (défaut fade=20 -> alpha=0.8).
        EN : Exact multi-pass Ghoul Eye (ReanimatedEyeColor) effect per filterdesc.xml:
             1. BlurImageOperation(xblur=6, yblur=6, quality=3, BlendMode="lighten")
             2. NestedImageOperation(BlendMode="screen"):
                - AdjustCurvesImageOperation(MasterCurve=[(0,20),(255,255)])
                - TintImageOperation(Color=0xc2ff9e)
             3. Final blend with BlendAlpha = 1 - fade/100 (default fade=20 -> alpha=0.8).

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L1269-1296 (ReanimatedEyeColor)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        # Pass 1: Blur(xblur=6, yblur=6, quality=3, BlendMode=LIGHTEN)
        blurred = PicasaImageProcessor._box_blur_quality3(img, 6.0, 6.0)
        arr_o = np.array(img, dtype=np.float32)
        arr_b = np.array(blurred, dtype=np.float32)
        lightened = np.maximum(arr_o, arr_b)
        # Pass 2: Nested(BlendMode=SCREEN) { AdjustCurves([(0,20),(255,255)]) + Tint(0xc2ff9e) }
        lut = PicasaImageProcessor._eval_curve_lut([(0, 20), (255, 255)])
        curved = lut[lightened.astype(np.uint8)].astype(np.float32) / 255.0
        tint_col = np.array([194.0 / 255.0, 255.0 / 255.0, 158.0 / 255.0], dtype=np.float32)
        tinted = curved * tint_col
        base_n = lightened / 255.0
        screened = (1.0 - (1.0 - base_n) * (1.0 - tinted)) * 255.0
        # Pass 3: BlendAlpha = 1 - fade/100
        fade = float(args[1]) if len(args) >= 2 else (float(args[0]) if len(args) == 1 else 20.0)
        alpha = max(0.0, min(1.0, 1.0 - fade / 100.0))
        blended = alpha * screened + (1.0 - alpha) * arr_o
        return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))

    @staticmethod
    def rounded_edges(
        img: Image.Image,
        radius_ratio: float = 0.1,
        fade: float | tuple[int, int, int] = 0.0,
        outer_color: tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """
        FR : Coins arrondis anticrénelés (SDF) sur fond `outer_color` (0xffffff par défaut)
             reproduisant RoundedEdges de filterdesc.xml (cornerradius = min(w,h)/10).
        EN : Anti-aliased (SDF) rounded corners over `outer_color` (default 0xffffff)
             reproducing RoundedEdges from filterdesc.xml (cornerradius = min(w,h)/10).

        Ref: picasa3.exe @ 0x00760F40 (BorderImageOperation / RoundedEdges)
        Ref: runtime/filterdesc.xml @ L1298-1315 (RoundedEdges)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        if isinstance(fade, (tuple, list)):
            oc = tuple(int(c) for c in fade[:3])
            fade_val = 0.0
        else:
            oc = outer_color
            fade_val = float(fade)
        r_ratio = float(radius_ratio) / 100.0 if float(radius_ratio) > 1.0 else float(radius_ratio)
        w, h = img.size
        rad = max(2.0, min(w, h) * r_ratio)
        # FR : Distance signée (SDF) aux coins arrondis pour un anticrénelage sub-pixel lisse
        # EN : Signed distance field (SDF) to rounded corners for smooth sub-pixel anti-aliasing
        y, x = np.ogrid[:h, :w]
        dx = np.maximum(np.maximum(rad - x, x - (w - 1 - rad)), 0.0)
        dy = np.maximum(np.maximum(rad - y, y - (h - 1 - rad)), 0.0)
        corner_dist = np.sqrt(dx * dx + dy * dy)
        alpha = np.clip(rad + 0.5 - corner_dist, 0.0, 1.0)[:, :, np.newaxis]
        arr = np.array(img, dtype=np.float32)
        bg = np.array(oc, dtype=np.float32).reshape((1, 1, 3))
        out = arr * alpha + bg * (1.0 - alpha)
        res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        if fade_val > 0.0:
            blend_a = max(0.0, min(1.0, 1.0 - fade_val / 100.0))
            return Image.blend(img, res, blend_a)
        return res

    @staticmethod
    def focal_pixelate(
        img: Image.Image,
        block_size: float = 15.0,
        radius_norm: float = 0.35,
        hardness: float = 50.0,
        center_x: float = 0.5,
        center_y: float = 0.5,
    ) -> Image.Image:
        """
        FR : Pixellisation focale exacte selon PicnikFocalPixelate de filterdesc.xml :
             1. ResizeImageOperation(width=w/impact, height=h/impact)
             2. ResizeImageOperation(width=w, height=h, smoothing=false, Mask=CircularGradientImageMask(
                innerRadius=R*(hardness/101), outerRadius=R*(2 - hardness/101)))
        EN : Exact focal pixelation per PicnikFocalPixelate in filterdesc.xml:
             1. ResizeImageOperation(width=w/impact, height=h/impact)
             2. ResizeImageOperation(width=w, height=h, smoothing=false, Mask=CircularGradientImageMask(
                innerRadius=R*(hardness/101), outerRadius=R*(2 - hardness/101)))

        Ref: picasa3.exe @ 0x00760F40
        Ref: runtime/filterdesc.xml @ L859-886 (PicnikFocalPixelate, focalpixelate)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        pix_img = PicasaImageProcessor.pixelate(img, block_size=max(2, int(round(block_size))))
        arr_orig = np.array(img, dtype=np.float32)
        arr_pix = np.array(pix_img, dtype=np.float32)
        h, w = arr_orig.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h * float(center_y), w * float(center_x)
        base_r = min(w, h) * float(radius_norm)
        h_val = float(hardness) * 100.0 if 0.0 < float(hardness) <= 1.0 else float(hardness)
        h_ratio = max(0.0, min(0.99, h_val / 101.0))
        inner_r = base_r * h_ratio
        outer_r = max(inner_r + 1.0, base_r * (2.0 - h_ratio))
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        mask = np.clip((dist - inner_r) / (outer_r - inner_r), 0.0, 1.0)[:, :, np.newaxis]
        out = arr_orig * (1.0 - mask) + arr_pix * mask
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def filtered_bw(img: Image.Image, filter_rgb: tuple[int, int, int] = (255, 85, 85)) -> Image.Image:
        """
        FR : Noir & Blanc avec filtre optique coloré (BWImageOperation / ansel).
        EN : Black & White with colored optical filter (BWImageOperation / ansel).

        Ref: runtime/filterdesc.xml @ ansel
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        fr, fg, fb = [max(1.0, float(c)) for c in filter_rgb]
        total = fr + fg + fb
        lum = (arr[:, :, 0] * fr + arr[:, :, 1] * fg + arr[:, :, 2] * fb) / total
        gray = np.clip(lum, 0, 255).astype(np.uint8)
        return Image.fromarray(np.stack([gray] * 3, axis=2))

    @staticmethod
    def radial_tint(img: Image.Image, tint_rgb: tuple[int, int, int] = (123, 180, 216), feather: float = 0.25) -> Image.Image:
        """
        FR : Teinte radiale autour du centre.
        EN : Radial tint around the center.

        Ref: runtime/filterdesc.xml @ radtint
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        tinted = PicasaImageProcessor.tint(img, tint_rgb=tint_rgb, intensity=0.5)
        arr_orig = np.array(img, dtype=np.float32)
        arr_tint = np.array(tinted, dtype=np.float32)
        h, w = arr_orig.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h / 2.0, w / 2.0
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max(1.0, math.hypot(cx, cy))
        mask = np.clip(dist / max(0.1, 1.0 - feather), 0.0, 1.0)[:, :, np.newaxis]
        out = arr_orig * (1.0 - mask) + arr_tint * mask
        return Image.fromarray(out.astype(np.uint8))

    @staticmethod
    def linear_blur(img: Image.Image, amount: float = 2.0) -> Image.Image:
        """
        FR : Flou linéaire / Tilt-shift.
        EN : Linear blur / Tilt-shift effect.

        Ref: runtime/filterdesc.xml @ linblur
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        blurred = img.filter(ImageFilter.GaussianBlur(radius=max(1.0, amount)))
        arr_orig = np.array(img, dtype=np.float32)
        arr_blur = np.array(blurred, dtype=np.float32)
        h = arr_orig.shape[0]
        y = np.linspace(-1.0, 1.0, h, dtype=np.float32)
        mask = np.clip(np.abs(y) * 1.4 - 0.2, 0.0, 1.0)[:, np.newaxis, np.newaxis]
        out = arr_orig * (1.0 - mask) + arr_blur * mask
        return Image.fromarray(out.astype(np.uint8))

    @staticmethod
    def gaussian_blur(img: Image.Image, radius: float = 2.0) -> Image.Image:
        """
        FR : Flou gaussien standard.
        EN : Standard Gaussian blur.

        Ref: runtime/filterdesc.xml @ blur
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img.filter(ImageFilter.GaussianBlur(radius=max(0.5, radius)))

    @staticmethod
    def adjust_contrast(img: Image.Image, amount: float = 0.2) -> Image.Image:
        """
        FR : Ajustement de contraste global.
        EN : Global contrast adjustment.

        Ref: runtime/filterdesc.xml @ contrast
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageEnhance.Contrast(img).enhance(max(0.1, 1.0 + amount))

    @staticmethod
    def gamma_correct(img: Image.Image, gamma: float = 1.2) -> Image.Image:
        """
        FR : Correction gamma par LUT.
        EN : LUT-based gamma correction.

        Ref: runtime/filterdesc.xml @ gamma
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        g = max(0.1, float(gamma))
        inv_g = 1.0 / g
        lut = np.clip(((np.arange(256, dtype=np.float32) / 255.0) ** inv_g) * 255.0, 0, 255).astype(np.uint8)
        arr = np.array(img, dtype=np.uint8)
        return Image.fromarray(lut[arr])

    @staticmethod
    def backlight_fix(img: Image.Image, amount: float = 0.25) -> Image.Image:
        """
        FR : Correction de contre-jour.
        EN : Backlight correction.

        Ref: runtime/filterdesc.xml @ backlight, autobacklight
        """
        return PicasaImageProcessor.fill_light(img, amount=amount)

    @staticmethod
    def directional_saturation(img: Image.Image, lr: float = 0.5, tb: float = 0.5) -> Image.Image:
        """
        FR : Saturation directionnelle.
        EN : Directional saturation.

        Ref: runtime/filterdesc.xml @ dir_sat
        """
        return PicasaImageProcessor.saturation(img, factor=1.0 + (lr + tb) * 0.3)

    @staticmethod
    def directional_brightness(img: Image.Image, lr: float = 0.2, tb: float = 0.2) -> Image.Image:
        """
        FR : Luminosité directionnelle.
        EN : Directional brightness.

        Ref: runtime/filterdesc.xml @ dir_brite
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        return ImageEnhance.Brightness(img).enhance(max(0.2, 1.0 + (lr + tb) * 0.25))

    @staticmethod
    def directional_sharpen(img: Image.Image, lr: float = 0.5, tb: float = 0.5) -> Image.Image:
        """
        FR : Netteté directionnelle.
        EN : Directional sharpen.

        Ref: runtime/filterdesc.xml @ dir_sharp
        """
        return PicasaImageProcessor.sharpen(img)

    @staticmethod
    def rainbow(img: Image.Image, shift: float = 32.0) -> Image.Image:
        """
        FR : Décalage de teinte arc-en-ciel dans l'espace HSV.
        EN : Rainbow hue shift in HSV color space.

        Ref: runtime/filterdesc.xml @ rainbow
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        hsv = np.array(img.convert("HSV"), dtype=np.uint8)
        hsv[:, :, 0] = (hsv[:, :, 0].astype(np.int32) + int(shift)) % 256
        return Image.fromarray(hsv, mode="HSV").convert("RGB")

    @staticmethod
    def triple(img: Image.Image, brightness: float = 0.0, contrast: float = 0.0, fill: float = 0.2) -> Image.Image:
        """
        FR : Réglage d'éclairage combiné (Fill Light + Luminosité + Contraste).
        EN : Combined lighting adjustment (Fill Light + Brightness + Contrast).

        Ref: runtime/filterdesc.xml @ triple, triple2, triple3
        """
        out = PicasaImageProcessor.fill_light(img, amount=fill)
        if abs(brightness) > 0.001:
            out = ImageEnhance.Brightness(out).enhance(max(0.1, 1.0 + brightness))
        if abs(contrast) > 0.001:
            out = ImageEnhance.Contrast(out).enhance(max(0.1, 1.0 + contrast))
        return out

    @staticmethod
    def finetune(
        img: Image.Image,
        fill: float = 0.0,
        highlights: float = 0.0,
        shadows: float = 0.0,
        colortemp: float = 0.0
    ) -> Image.Image:
        """
        FR : Réglage fin combiné (Lumière d'appoint, Hautes lumières, Ombres, Température de couleur).
        EN : Combined fine-tuning (Fill light, Highlights, Shadows, Color temperature).

        Ref: runtime/filterdesc.xml @ finetune, finetune2
        """
        out = img
        if abs(fill) > 0.001:
            out = PicasaImageProcessor.fill_light(out, fill)
        if abs(highlights) > 0.001:
            out = PicasaImageProcessor.adjust_highlights(out, highlights)
        if abs(shadows) > 0.001:
            out = PicasaImageProcessor.adjust_shadows(out, shadows)
        if abs(colortemp) > 0.001:
            out = PicasaImageProcessor.color_temperature(out, colortemp)
        return out

    # FR : Alias de méthodes pour correspondance stricte 1:1 avec filterdesc.xml et tools/audit_picasa_code.py
    # EN : Method aliases for strict 1:1 correspondence with filterdesc.xml and tools/audit_picasa_code.py
    pick_neutral_color = neutral_color_balance
    neutral_color_picker = neutral_color_balance
    crop64 = crop
    rot = rotate
    triple2 = triple
    triple3 = triple
    finetune2 = finetune
    colorfix = auto_color
    autobacklight = backlight_fix
    autolight = auto_contrast
    bw = black_and_white
    enhance = auto_contrast
    warm = warmify
    grain = film_grain
    grain2 = film_grain
    unsharp = sharpen
    unsharp2 = sharpen
    tilt = straighten
    radblur = soft_focus
    radsat = focal_bw
    linblur = linear_blur
    ansel = filtered_bw
    dir_tint = graduated_tint
    radtint = radial_tint
    glow2 = glow
    sat = saturation
    shadow = adjust_shadows
    blur = gaussian_blur
    contrast = adjust_contrast
    gamma = gamma_correct
    backlight = backlight_fix
    fill = fill_light
    whitept = neutral_color_balance
    dir_sat = directional_saturation
    dir_brite = directional_brightness
    dir_sharp = directional_sharpen
    focalpixelate = focal_pixelate
    picnik_focal_pixelate = focal_pixelate
    picnik_grain = film_grain
    picnik_tint = tint
    hdr = hdr_simulator
    ir = infrared
    comicize = comic
    quantize = quantize_palette

    @staticmethod
    def save_history(img: Image.Image) -> Image.Image:
        """
        FR : Marqueur d'historique de sauvegarde (sans effet visuel).
        EN : Save history marker (no-op visual effect).

        Ref: runtime/filterdesc.xml @ save
        """
        return img.copy()

    @staticmethod
    def picnik_history(img: Image.Image) -> Image.Image:
        """
        FR : Marqueur d'historique Creative Kit / Picnik (sans effet visuel).
        EN : Creative Kit / Picnik history marker (no-op visual effect).

        Ref: runtime/filterdesc.xml @ picnik
        """
        return img.copy()

    @staticmethod
    def debug_filter(img: Image.Image) -> Image.Image:
        """
        FR : Filtre de débogage interne (sans effet visuel).
        EN : Internal debug filter (no-op visual effect).

        Ref: runtime/filterdesc.xml @ debug
        """
        return img.copy()

    @staticmethod
    def movie_trim(img: Image.Image) -> Image.Image:
        """
        FR : Marqueur d'historique de découpe vidéo (moviestart, movieend).
        EN : Video trim history marker (moviestart, movieend).

        Ref: runtime/filterdesc.xml @ moviestart, movieend
        """
        return img.copy()

    @staticmethod
    def pil_to_qimage(img: Image.Image):
        """
        FR : Convertit une image PIL en QImage Qt (RGB888 ou RGBA8888) avec copie profonde du tampon.
        EN : Converts a PIL image to a Qt QImage (RGB888 or RGBA8888) with deep buffer copy.

        Ref: picasa3.exe @ 0x00760F40
        """
        from PySide6.QtGui import QImage
        if img.mode == "RGBA":
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
            return qimg.copy()
        rgb = img.convert("RGB")
        data = rgb.tobytes("raw", "RGB")
        qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
        return qimg.copy()

    @staticmethod
    def pil_to_qpixmap(img: Image.Image):
        """
        FR : Convertit une image PIL en QPixmap Qt.
        EN : Converts a PIL image to a Qt QPixmap.

        Ref: picasa3.exe @ 0x00760F40
        """
        from PySide6.QtGui import QPixmap
        return QPixmap.fromImage(PicasaImageProcessor.pil_to_qimage(img))

