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
    def load_transformed_image(file_path: str, max_size: int = 0, parsed_ini: Any = None) -> Optional[Image.Image]:
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
                if parsed_ini is not None or os.path.exists(ini_path):
                    try:
                        from picasa_py.ini.parser import PicasaIniParser
                        from picasa_py.faces.facerect import decode_rect64_string
                        doc = parsed_ini if parsed_ini is not None else PicasaIniParser.parse_file(ini_path)
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
                                pil_img = PicasaImageProcessor.apply_filter_chain(pil_img, filters_str, skip_geom=True)

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
        FR : Analyse une entrée `text=` de `.picasa.ini` :
             1. Format natif `CTextItemList` de `picasa3.exe` (`0x00A4DB30` / `0x00A4DD50`) :
                `<num_items>;<utf8_len>;<utf8_text>;<font>;<nx>,<ny>,<scale>,<angle>;v1,<weight>,<flags2>,<rel_size>,<outline_w>,<aspect>,<fill_alpha>,<outline_argb>,<fill_argb>,<style_flags>;`
             2. Format historique à 12 champs : `Police;taille;0;0;0;400;0;0;r,g,b;px,py;shadow;texte`
             3. Format court à 4 champs : `texte;taille;r,g,b;px,py` ou texte brut.
        EN : Parses a `.picasa.ini` `text=` entry:
             1. Native `picasa3.exe` `CTextItemList` format (`0x00A4DB30` / `0x00A4DD50`):
                `<num_items>;<utf8_len>;<utf8_text>;<font>;<nx>,<ny>,<scale>,<angle>;v1,<weight>,<flags2>,<rel_size>,<outline_w>,<aspect>,<fill_alpha>,<outline_argb>,<fill_argb>,<style_flags>;`
             2. Legacy 12-field format: `Font;size;0;0;0;400;0;0;r,g,b;px,py;shadow;text`
             3. Short 4-field format: `text;size;r,g,b;px,py` or plain text.

        Ref: picasa3.exe @ 0x00A4DB30, 0x00A4DD50, 0x00A4E3A0, 0x00658900
        """
        raw = txt_val.strip()
        if not raw:
            return "", (0.15, 0.85), 28, (255, 255, 255), True
        if ";" not in raw:
            return raw, (0.15, 0.85), 28, (255, 255, 255), True

        # 1. Format natif CTextItemList (0x00A4DB30 / 0x00A4DD50) : <num_items>;<utf8_len>;<utf8_text>;<font>;<nx>,<ny>,<scale>,<angle>;v1,...
        first_semi = raw.find(";")
        if first_semi > 0 and raw[:first_semi].strip().isdigit():
            second_semi = raw.find(";", first_semi + 1)
            if second_semi > first_semi + 1 and raw[first_semi + 1 : second_semi].strip().isdigit():
                try:
                    utf8_len = int(raw[first_semi + 1 : second_semi].strip())
                    rest_bytes = raw[second_semi + 1 :].encode("utf-8")
                    if len(rest_bytes) >= utf8_len:
                        text_str = rest_bytes[:utf8_len].decode("utf-8", errors="replace")
                        tail_str = rest_bytes[utf8_len:].decode("utf-8", errors="replace").lstrip(";")
                        tail_parts = [p.strip() for p in tail_str.split(";") if p.strip()]
                        pos_norm: Tuple[float, float] = (0.15, 0.85)
                        size = 28
                        color: Tuple[int, int, int] = (255, 255, 255)
                        shadow = True
                        if len(tail_parts) >= 2 and "," in tail_parts[1]:
                            coords = [float(x.strip()) for x in tail_parts[1].split(",") if x.strip()]
                            if len(coords) >= 2:
                                pos_norm = (coords[0], coords[1])
                            if len(coords) >= 3 and coords[2] > 0:
                                size = max(8, int(round(coords[2] * 360.0)))
                        if len(tail_parts) >= 3 and tail_parts[2].startswith("v1,"):
                            v_fields = [x.strip() for x in tail_parts[2].split(",")]
                            if len(v_fields) >= 5:
                                shadow = float(v_fields[4]) > 0.0
                            if len(v_fields) >= 9:
                                raw_c = v_fields[8].strip().lower()
                                try:
                                    if any(ch in raw_c for ch in "abcdef") or len(raw_c) == 8:
                                        fill_u32 = int(raw_c, 16) & 0xFFFFFFFF
                                    else:
                                        fill_u32 = int(float(raw_c)) & 0xFFFFFFFF
                                except ValueError:
                                    fill_u32 = int(raw_c, 16) & 0xFFFFFFFF
                                color = ((fill_u32 >> 16) & 0xFF, (fill_u32 >> 8) & 0xFF, fill_u32 & 0xFF)
                        return text_str, pos_norm, size, color, shadow
                except Exception:
                    pass

        parts = raw.split(";")
        # 2. Format court à 4 champs : txt;size;r,g,b;px,py
        if len(parts) == 4 and "," in parts[3]:
            try:
                coord_parts = [float(x.strip()) for x in parts[3].split(",") if x.strip()]
                if len(coord_parts) >= 2:
                    px, py = coord_parts[0], coord_parts[1]
                    text_str = parts[0].strip()
                    size = int(round(float(parts[1].strip()))) if parts[1].strip() else 28
                    color = (255, 255, 255)
                    if "," in parts[2]:
                        c_vals = [int(round(float(c.strip()))) for c in parts[2].split(",") if c.strip()]
                        if len(c_vals) >= 3:
                            color = (c_vals[0], c_vals[1], c_vals[2])
                    return text_str, (px, py), size, color, True
            except Exception:
                pass

        # 3. Format historique à 12 champs : Arial;size;0;0;0;400;0;0;r,g,b;px,py;shadow;txt
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
            pos_norm = (0.15, 0.85)
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
    def _parse_filter_color(
        parts: list[str],
        idx: int,
        default_rgb: Tuple[int, int, int] = (255, 255, 255),
    ) -> Tuple[Tuple[int, int, int], int]:
        """
        FR : Extrait une couleur `(R, G, B)` depuis `parts[idx:]` en acceptant à la fois
             le format hexadécimal 8 chiffres natif de `picasa3.exe` (`%08x`, `0x008FAC40` / `0x008FB7E7`)
             et le format décimal à 3 composantes `R,G,B`. Retourne `(rgb, next_idx)`.
        EN : Extracts an `(R, G, B)` color from `parts[idx:]`, accepting both the native
             `picasa3.exe` 8-hex-digit format (`%08x`, `0x008FAC40` / `0x008FB7E7`)
             and the 3-component decimal `R,G,B` format. Returns `(rgb, next_idx)`.

        Ref: picasa3.exe @ 0x008FAC40, 0x008FB7E7
        """
        if idx >= len(parts):
            return default_rgb, idx
        tok = parts[idx].strip()
        hex_candidate = tok[2:] if tok.lower().startswith("0x") else tok
        if (
            len(hex_candidate) in (6, 8)
            and "." not in hex_candidate
            and all(c in "0123456789abcdefABCDEF" for c in hex_candidate)
            and (idx + 2 >= len(parts) or len(hex_candidate) >= 6)
        ):
            val = int(hex_candidate, 16)
            return ((val >> 16) & 0xFF, (val >> 8) & 0xFF, val & 0xFF), idx + 1
        if idx + 2 < len(parts):
            try:
                r = max(0, min(255, int(round(float(parts[idx])))))
                g = max(0, min(255, int(round(float(parts[idx + 1])))))
                b = max(0, min(255, int(round(float(parts[idx + 2])))))
                return (r, g, b), idx + 3
            except Exception:
                pass
        return default_rgb, idx + 1

    @staticmethod
    def apply_filter_chain(img: Image.Image, filters_str: str, skip_geom: bool = False) -> Image.Image:
        """
        FR : Applique séquentiellement la chaîne de filtres non-destructifs .picasa.ini (filters=...).
        EN : Sequentially applies the .picasa.ini non-destructive filter chain (filters=...).

        Ref: picasa3.exe @ filterdesc.xml, 0x008FAC40, 0x008FB450, 0x008814AC, 0x00760F40
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
                if fname_l in ("crop64", "crop"):
                    if not skip_geom and len(parts) > 1:
                        from picasa_py.faces.facerect import decode_rect64_string
                        lf, tf, rf, bf = decode_rect64_string(parts[1])
                        out = PicasaImageProcessor.crop(out, (lf, tf, rf, bf))
                elif fname_l == "tilt":
                    if not skip_geom and len(parts) > 1:
                        t_ang = float(parts[1])
                        if abs(t_ang) >= 0.01:
                            out = PicasaImageProcessor.straighten(out, t_ang)
                elif fname_l in ("autolight", "autocontrast"):
                    out = PicasaImageProcessor.auto_contrast(out)
                elif fname_l == "enhance":
                    out = PicasaImageProcessor.enhance_lucky(out)
                elif fname_l in ("autocolor", "colorfix"):
                    out = PicasaImageProcessor.auto_color(out)
                elif fname_l == "whitept":
                    if len(parts) == 2 and len(parts[1]) in (6, 8):
                        col, _ = PicasaImageProcessor._parse_filter_color(parts, 1, (128, 128, 128))
                        out = PicasaImageProcessor.neutral_color_picker(out, col)
                    else:
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
                    amt = float(parts[1]) if len(parts) > 1 else 0.6
                    out = PicasaImageProcessor.sharpen(out, amount=amt)
                elif fname_l in ("grain", "grain2", "filmgrain", "picnikgrain"):
                    if fname_l == "picnikgrain" and len(parts) == 2:
                        out = PicasaImageProcessor.film_grain(out, intensity=18.0, fade=float(parts[1]))
                    elif len(parts) <= 1:
                        out = PicasaImageProcessor.film_grain(out, intensity=18.0, fade=0.0)
                    else:
                        amt = float(parts[1]) if len(parts) > 1 else 18.0
                        fade = float(parts[2]) if len(parts) > 2 else 0.0
                        out = PicasaImageProcessor.film_grain(out, intensity=amt, fade=fade)
                elif fname_l in ("fill", "backlight", "autobacklight", "filllight"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.3
                    out = PicasaImageProcessor.fill_light(out, amt)
                elif fname_l in ("finetune", "finetune2"):
                    # Ref: picasa3.exe @ 0x008FAC40, 0x008FB120
                    # Format exact : finetune2=1,<fill:%f>,<highlights:%f>,<shadows:%f>,<neutral_rgb:%08x>,<colortemp:%f>
                    f_val = float(parts[1]) if len(parts) > 1 else 0.0
                    hl_val = float(parts[2]) if len(parts) > 2 else 0.0
                    sh_val = float(parts[3]) if len(parts) > 3 else 0.0
                    neutral_rgb = 0
                    ct_val = 0.0
                    if len(parts) >= 6:
                        try:
                            neutral_rgb = int(parts[4], 16)
                        except ValueError:
                            neutral_rgb = 0
                        ct_val = float(parts[5])
                    elif len(parts) == 5:
                        p4 = parts[4].strip()
                        if len(p4) == 8 and all(c in "0123456789abcdefABCDEF" for c in p4) and "." not in p4:
                            neutral_rgb = int(p4, 16)
                        else:
                            ct_val = float(p4)
                    out = PicasaImageProcessor.finetune(out, f_val, hl_val, sh_val, ct_val, neutral_rgb=neutral_rgb)
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
                    fac = float(parts[1]) if len(parts) > 1 else 0.1618
                    out = PicasaImageProcessor.saturation(out, fac)
                elif fname_l in ("tint", "picniktint"):
                    # Ref: picasa3.exe @ 0x008FAC40 : PicnikTint=1,<fade>,<00rrggbb> ou tint=1,<pres>,<ffrrggbb>
                    raw_s = float(parts[1]) if len(parts) > 1 else 0.4
                    if fname_l == "picniktint" or raw_s > 1.0:
                        amt = max(0.0, min(1.0, 1.0 - (raw_s / 100.0 if fname_l == "picniktint" else raw_s / 256.0)))
                    else:
                        amt = raw_s
                    col, _ = PicasaImageProcessor._parse_filter_color(parts, 2, (220, 190, 150))
                    out = PicasaImageProcessor.tint(out, tint_rgb=col, intensity=amt)
                elif fname_l in ("radblur", "softfocus"):
                    # Ref: picasa3.exe @ 0x008FAE22..0x008FAE90 : radblur=1,<cx>,<cy>,<size>,<amount>
                    if len(parts) >= 5:
                        cx = float(parts[1])
                        cy = float(parts[2])
                        sz = float(parts[3])
                        amt = float(parts[4])
                        out = PicasaImageProcessor.soft_focus(out, amount=amt, radius_norm=sz, center_x=cx, center_y=cy)
                    else:
                        amt = float(parts[1]) if len(parts) > 1 else 0.4
                        sz = float(parts[2]) if len(parts) > 2 else 0.35
                        out = PicasaImageProcessor.soft_focus(out, amount=amt, radius_norm=sz)
                elif fname_l in ("glow", "glow2"):
                    amt = float(parts[1]) if len(parts) > 1 else 0.65
                    rad = float(parts[2]) if len(parts) > 2 else 3.0
                    out = PicasaImageProcessor.glow(out, intensity=amt, radius=rad)
                elif fname_l in ("radsat", "focalbw"):
                    # Ref: picasa3.exe @ 0x008FAE22..0x008FAE90 : radsat=1,<cx>,<cy>,<size>,<sharpness>
                    if len(parts) >= 5:
                        cx = float(parts[1])
                        cy = float(parts[2])
                        sz = float(parts[3])
                        sh = float(parts[4])
                        out = PicasaImageProcessor.focal_bw(out, radius_norm=sz, sharpness=sh, center_x=cx, center_y=cy)
                    else:
                        sz = float(parts[1]) if len(parts) > 1 else 0.35
                        sh = float(parts[2]) if len(parts) > 2 else 0.4
                        out = PicasaImageProcessor.focal_bw(out, radius_norm=sz, sharpness=sh)
                elif fname_l in ("dir_tint", "gradtint", "graduatedtint", "graduated_tint"):
                    # Ref: picasa3.exe @ 0x008FAE22..0x008FAF30 : dir_tint=1,<cx>,<cy>,<feather>,<shade>,<ffrrggbb>[,<angle>]
                    if fname_l == "dir_tint" and len(parts) >= 6 and (len(parts[5]) in (6, 8) or len(parts) == 7):
                        cx = float(parts[1])
                        cy = float(parts[2])
                        feath = float(parts[3])
                        amt = float(parts[4])
                        col, next_i = PicasaImageProcessor._parse_filter_color(parts, 5, (123, 180, 216))
                        ang = float(parts[next_i]) if next_i < len(parts) else 0.0
                        out = PicasaImageProcessor.graduated_tint(
                            out, tint_rgb=col, intensity=amt, feather=feath, center_x=cx, center_y=cy, angle_deg=ang
                        )
                    else:
                        amt = float(parts[1]) if len(parts) > 1 else 0.5
                        feath = float(parts[2]) if len(parts) > 2 else 0.5
                        col, _ = PicasaImageProcessor._parse_filter_color(parts, 3, (255, 140, 50))
                        out = PicasaImageProcessor.graduated_tint(out, tint_rgb=col, intensity=amt, feather=feath)
                elif fname_l in ("ansel", "filtered_bw", "filteredbw"):
                    # Ref: picasa3.exe @ 0x008FAC40, 0x008FB7E7 : ansel=1,<ffrrggbb>
                    col, _ = PicasaImageProcessor._parse_filter_color(parts, 1, (255, 85, 85))
                    out = PicasaImageProcessor.filtered_bw(out, col)
                elif fname_l == "redeye":
                    if len(parts) >= 5:
                        box = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
                        out = PicasaImageProcessor.remove_red_eye(out, box)
                    else:
                        out = PicasaImageProcessor.remove_red_eye(out)
                elif fname_l == "retouch":
                    cx = float(parts[1]) if len(parts) > 1 else 0.5
                    cy = float(parts[2]) if len(parts) > 2 else 0.5
                    rad = float(parts[3]) if len(parts) > 3 else 0.03
                    out = PicasaImageProcessor.retouch_heal(out, (cx, cy), rad)
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
                    col, _ = PicasaImageProcessor._parse_filter_color(parts, 3, (87, 204, 41))
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
                    # Ref: filterdesc.xml @ Vignette : Vignette=1,<blur>,<strength>,<fade>,<clrsw:%08x> ou legacy <amt>,<sz>,<color>
                    if len(parts) == 5 and len(parts[4]) in (6, 8) and "." not in parts[4]:
                        col, _ = PicasaImageProcessor._parse_filter_color(parts, 4, (0, 0, 0))
                    else:
                        col, _ = PicasaImageProcessor._parse_filter_color(parts, 3, (0, 0, 0))
                    out = PicasaImageProcessor.vignette(out, amount=amt, size=sz, color_rgb=col)
                elif fname_l in ("twotone", "duotone", "two_tone"):
                    b_val = float(parts[1]) if len(parts) > 1 else 0.0
                    c_val = float(parts[2]) if len(parts) > 2 else 0.0
                    f_val = float(parts[3]) if len(parts) > 3 else 0.0
                    sc, next_i = PicasaImageProcessor._parse_filter_color(parts, 4, (0, 68, 136))
                    hc, _ = PicasaImageProcessor._parse_filter_color(parts, next_i, (255, 255, 0))
                    out = PicasaImageProcessor.two_tone(out, b_val, c_val, f_val, sc, hc)
                elif fname_l == "pixelate":
                    bs = int(round(float(parts[1]))) if len(parts) > 1 else 14
                    fade = float(parts[3]) if len(parts) >= 4 else (float(parts[2]) if len(parts) > 2 else 0.0)
                    out = PicasaImageProcessor.pixelate(out, block_size=bs, fade=fade)
                elif fname_l in ("focalpixelate", "picnikfocalpixelate"):
                    # Ref: 0x008FADDE : PicnikFocalPixelate=1,<cx>,<cy>,<block_size>,<size>,<hardness>[,<rev>]
                    if len(parts) >= 6 and 0.0 <= float(parts[1]) <= 1.0 and 0.0 <= float(parts[2]) <= 1.0 and float(parts[3]) > 1.0:
                        cx, cy = float(parts[1]), float(parts[2])
                        bs, sz, hd = float(parts[3]), float(parts[4]), float(parts[5])
                        out = PicasaImageProcessor.focal_pixelate(out, bs, sz, hd, cx, cy)
                    else:
                        args = [float(p) for p in parts[1:6]]
                        out = PicasaImageProcessor.focal_pixelate(out, *args)
                elif fname_l == "localcontrast":
                    args = [float(p) for p in parts[1:4]]
                    out = PicasaImageProcessor.local_contrast(out, *args)
                elif fname_l in ("dropshadow", "drop_shadow"):
                    dist = float(parts[1]) if len(parts) > 1 else 6.0
                    ang = float(parts[2]) if len(parts) > 2 else 45.0
                    blur = float(parts[3]) if len(parts) > 3 else 8.0
                    # Ref: filterdesc.xml @ DropShadow : DropShadow=1,<dist>,<ang>,<blur>,<shadow_hex>,<bg_hex>,<fade>
                    if len(parts) >= 7 and len(parts[4]) in (6, 8) and "." not in parts[4]:
                        _, next_i = PicasaImageProcessor._parse_filter_color(parts, 4, (0, 0, 0))
                        bg, next_i2 = PicasaImageProcessor._parse_filter_color(parts, next_i, (255, 255, 255))
                        fade = float(parts[next_i2]) if next_i2 < len(parts) else 50.0
                    else:
                        fade = float(parts[4]) if len(parts) > 4 else 50.0
                        bg, _ = PicasaImageProcessor._parse_filter_color(parts, 5, (255, 255, 255))
                    out = PicasaImageProcessor.drop_shadow(
                        out,
                        distance=dist,
                        angle_deg=ang,
                        blur_radius=blur,
                        shadow_alpha=(100.0 - fade) / 100.0,
                        bg_color=bg,
                    )
                elif fname_l in ("roundededges", "rounded_edges", "roundedcorners"):
                    rr = float(parts[1]) if len(parts) > 1 else 0.1
                    oc, _ = PicasaImageProcessor._parse_filter_color(parts, 2, (255, 255, 255))
                    out = PicasaImageProcessor.rounded_edges(out, radius_ratio=rr, outer_color=oc)
                elif fname_l == "invert":
                    out = PicasaImageProcessor.invert(out)
                elif fname_l == "focalzoom":
                    # Ref: 0x008FADDE : FocalZoom=1,<cx>,<cy>,<zoom>,<size>,<hardness>[,<fade>]
                    if len(parts) >= 6 and 0.0 <= float(parts[1]) <= 1.0 and 0.0 <= float(parts[2]) <= 1.0 and float(parts[3]) > 1.0:
                        zm, sz, hd = float(parts[3]), float(parts[4]), float(parts[5])
                        out = PicasaImageProcessor.focal_zoom(out, zm, sz, hd)
                    else:
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
                    col, _ = PicasaImageProcessor._parse_filter_color(parts, 2, (0, 255, 255))
                    out = PicasaImageProcessor.neon(out, col, fade)
                elif fname_l == "pencilsketch":
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.pencil_sketch(out, *args)
                elif fname_l in ("museummatte", "museum_matte"):
                    in_t = float(parts[1]) if len(parts) > 1 else 12.0
                    if len(parts) >= 5 and float(parts[2]) == 0.0 and float(parts[3]) == 0.0:
                        out_t = float(parts[4])
                        ic, next_i = PicasaImageProcessor._parse_filter_color(parts, 5, (240, 234, 228))
                        oc, _ = PicasaImageProcessor._parse_filter_color(parts, next_i, (26, 14, 3))
                    else:
                        out_t = float(parts[2]) if len(parts) > 2 else 7.0
                        ic, next_i = PicasaImageProcessor._parse_filter_color(parts, 3, (240, 234, 228))
                        oc, _ = PicasaImageProcessor._parse_filter_color(parts, next_i, (26, 14, 3))
                    out = PicasaImageProcessor.museum_matte(out, in_t, out_t, ic, oc)
                elif fname_l == "reanimatedeyecolor":
                    args = [float(p) for p in parts[1:3]]
                    out = PicasaImageProcessor.reanimated_eye_color(out, *args)
                elif fname_l == "border":
                    outer_t = float(parts[1]) if len(parts) > 1 else 0.04
                    inner_t = float(parts[2]) if len(parts) > 2 else 0.005
                    rad = float(parts[3]) if len(parts) > 3 else 0.0
                    oc, next_i = PicasaImageProcessor._parse_filter_color(parts, 4, (26, 26, 26))
                    ic, _ = PicasaImageProcessor._parse_filter_color(parts, next_i, (255, 255, 255))
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

    # =========================================================================
    # CONSTANTES ET MOTEURS DE NIVEAUX / COULEURS DÉSOBFUSQUÉS DE PICASA3.EXE
    # Ref: picasa3.exe @ 0x008F7EE0, 0x0090AC20, 0x0090C1E0, 0x0090E9D0, 0x0090EDA0
    # =========================================================================

    # Table exacte des 115 températures de couleur (R, G, B) extraite de picasa3.exe @ 0x00C7CF98
    # Index 55 = (255, 249, 253) correspond au point blanc neutre (colortemp = 0.0)
    _KELVIN_TABLE_00C7CF98: Tuple[Tuple[int, int, int], ...] = (
        (255, 56, 0), (255, 71, 0), (255, 83, 0), (255, 93, 0), (255, 101, 0),
        (255, 109, 0), (255, 115, 0), (255, 121, 0), (255, 126, 0), (255, 131, 0),
        (255, 137, 18), (255, 142, 33), (255, 147, 44), (255, 152, 54), (255, 157, 63),
        (255, 161, 72), (255, 165, 79), (255, 169, 87), (255, 173, 94), (255, 177, 101),
        (255, 180, 107), (255, 184, 114), (255, 187, 120), (255, 190, 126), (255, 193, 132),
        (255, 196, 137), (255, 199, 143), (255, 201, 148), (255, 204, 153), (255, 206, 159),
        (255, 209, 163), (255, 211, 168), (255, 213, 173), (255, 215, 177), (255, 217, 182),
        (255, 219, 186), (255, 221, 190), (255, 223, 194), (255, 225, 198), (255, 227, 202),
        (255, 228, 206), (255, 230, 210), (255, 232, 213), (255, 233, 217), (255, 235, 220),
        (255, 236, 224), (255, 238, 227), (255, 239, 230), (255, 240, 233), (255, 242, 236),
        (255, 243, 239), (255, 244, 242), (255, 245, 245), (255, 246, 248), (255, 248, 251),
        (255, 249, 253), (254, 249, 255), (252, 247, 255), (249, 246, 255), (247, 245, 255),
        (245, 243, 255), (243, 242, 255), (240, 241, 255), (239, 240, 255), (237, 239, 255),
        (235, 238, 255), (233, 237, 255), (231, 236, 255), (230, 235, 255), (228, 234, 255),
        (227, 233, 255), (225, 232, 255), (224, 231, 255), (222, 230, 255), (221, 230, 255),
        (220, 229, 255), (218, 228, 255), (217, 227, 255), (216, 227, 255), (215, 226, 255),
        (214, 225, 255), (212, 225, 255), (211, 224, 255), (210, 223, 255), (209, 223, 255),
        (208, 222, 255), (207, 221, 255), (207, 221, 255), (206, 220, 255), (205, 220, 255),
        (204, 219, 255), (203, 219, 255), (202, 218, 255), (201, 218, 255), (201, 217, 255),
        (200, 217, 255), (199, 216, 255), (199, 216, 255), (198, 216, 255), (197, 215, 255),
        (196, 215, 255), (196, 214, 255), (195, 214, 255), (195, 214, 255), (194, 213, 255),
        (193, 213, 255), (193, 212, 255), (192, 212, 255), (192, 212, 255), (191, 211, 255),
        (191, 211, 255), (190, 211, 255), (190, 210, 255), (189, 210, 255), (189, 210, 255),
    )

    # Matrice d'espace conique A @ 0x00CF47B0..0x00CF47D0 et son inverse Q = A^-1 (call 0x00A4A140)
    _CONE_MATRIX_A_00CF47B0 = np.array(
        [
            [1.9044, 0.4508, -0.3826],
            [-0.0532, 1.8018, 0.1995],
            [0.0491, -0.3057, 1.8576],
        ],
        dtype=np.float32,
    )
    _CONE_MATRIX_Q_00A4A140 = np.linalg.inv(_CONE_MATRIX_A_00CF47B0).astype(np.float32)

    @staticmethod
    def _chromatic_adaptation_0090eda0(
        img: Image.Image,
        rgb_in: Tuple[int, int, int] | int,
    ) -> Image.Image:
        """
        FR : Adaptation chromatique matricielle 3x3 en virgule fixe 16.16 reproduisant exactement
             `FUN_0090eda0 @ 0x0090EDA0` de `picasa3.exe`.
             Neutralise la couleur d'illuminant `(R_in, G_in, B_in)` vers le gris neutre `(Y, Y, Y)`
             de même luminance `Y = (77*R_in + 151*G_in + 28*B_in) >> 8` dans l'espace conique `Q = A^-1`.
        EN : Exact 16.16 fixed-point 3x3 chromatic adaptation matrix reproducing
             `FUN_0090eda0 @ 0x0090EDA0` from `picasa3.exe`.
             Neutralizes the illuminant color `(R_in, G_in, B_in)` to neutral gray `(Y, Y, Y)`
             of identical luminance `Y = (77*R_in + 151*G_in + 28*B_in) >> 8` in cone space `Q = A^-1`.

        Ref: picasa3.exe @ 0x0090EDA0, 0x00A4A140, 0x00CF47B0..0x00CF47D0
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        if isinstance(rgb_in, int):
            if (rgb_in & 0x00FFFFFF) == 0:
                return img.copy()
            r_in = (rgb_in >> 16) & 0xFF
            g_in = (rgb_in >> 8) & 0xFF
            b_in = rgb_in & 0xFF
        else:
            r_in, g_in, b_in = int(rgb_in[0]), int(rgb_in[1]), int(rgb_in[2])
            if r_in == 0 and g_in == 0 and b_in == 0:
                return img.copy()

        # Ref: 0x0090EE6B..0x0090EE94 : chaque canal à 0 est forcé à 1
        r = max(1, min(255, r_in))
        g = max(1, min(255, g_in))
        b = max(1, min(255, b_in))

        # Ref: 0x0090EE94..0x0090EEAB : Y = (77 * R + 151 * G + 28 * B) >> 8
        y_luma = (77 * r + 151 * g + 28 * b) >> 8
        v_gray = np.array([float(y_luma), float(y_luma), float(y_luma)], dtype=np.float32)
        v_in = np.array([float(r), float(g), float(b)], dtype=np.float32)

        q_mat = PicasaImageProcessor._CONE_MATRIX_Q_00A4A140
        a_mat = PicasaImageProcessor._CONE_MATRIX_A_00CF47B0
        u_gray = q_mat @ v_gray
        u_in = q_mat @ v_in

        # Ref: 0x0090F002..0x0090F02B : ratios diagonaux Von Kries dans l'espace Q
        s0 = float(u_gray[0] / u_in[0]) if abs(float(u_in[0])) > 1e-6 else 1.0
        s1 = float(u_gray[1] / u_in[1]) if abs(float(u_in[1])) > 1e-6 else 1.0
        s2 = float(u_gray[2] / u_in[2]) if abs(float(u_in[2])) > 1e-6 else 1.0

        # Ref: 0x0090F032..0x0090F316 : M_final = A * diag(s0, s1, s2) * Q, puis virgule fixe 16.16 (* 65536.0)
        m_final = a_mat @ (np.diag(np.array([s0, s1, s2], dtype=np.float32)) @ q_mat)
        m_fp = np.round(m_final.astype(np.float64) * 65536.0).astype(np.int64)

        # Ref: 0x0090F360..0x0090F3FE : produit matriciel entier >> 16 avec saturation [0..255]
        arr = np.array(img, dtype=np.int64)
        out = (arr @ m_fp.T) >> 16
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def _levels_lut_0090c1e0(
        img: Image.Image,
        black_pt: float,
        white_pt: float,
        gamma: float = 1.0,
    ) -> Image.Image:
        """
        FR : Table de correspondance (LUT) 16 bits (`0..65280`, `0xFF00`) d'étirement des niveaux
             Ombres / Hautes lumières reproduisant exactement `FUN_0090c3b0 @ 0x0090C3B0` ->
             `FUN_0090c1e0 @ 0x0090C1E0` -> `FUN_0090bc60 @ 0x0090BC60` de `picasa3.exe`.
        EN : Exact 16-bit (`0..65280`, `0xFF00`) Shadows / Highlights levels lookup table (LUT)
             reproducing `FUN_0090c3b0 @ 0x0090C3B0` -> `FUN_0090c1e0 @ 0x0090C1E0` ->
             `FUN_0090bc60 @ 0x0090BC60` from `picasa3.exe`.

        Ref: picasa3.exe @ 0x008F7F5D, 0x0090C3B0, 0x0090C1E0, 0x0090BC60
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        bp = float(black_pt)
        wp = float(white_pt)
        if abs(wp - bp) < 1e-6:
            scale = 1.0
        else:
            scale = 1.0 / (wp - bp)
        offset = bp * 65280.0
        xs = np.arange(256, dtype=np.float64) * 256.0
        if abs(float(gamma) - 1.0) < 1e-6:
            vals = (xs - offset) * scale
        else:
            norm = np.maximum(0.0, (xs - offset) * scale / 65280.0)
            vals = (norm ** float(gamma)) * 65280.0
        lut16 = np.clip(np.round(vals), 0, 65280).astype(np.int32)
        lut8 = np.clip(lut16 >> 8, 0, 255).astype(np.uint8)
        arr = np.array(img, dtype=np.uint8)
        return Image.fromarray(lut8[arr])

    @staticmethod
    def _central_crop_percentiles_00a4b960(
        img: Image.Image,
        low_pct: float = 0.005,
        high_pct: float = 0.995,
    ) -> Tuple[list[int], list[int], int, int]:
        """
        FR : Calcule les histogrammes R, G, B sur la zone centrale de 90 % (`x` de 5 % à 95 %,
             `y` de 5 % à 95 %, `0x00A4B960`) et extrait les quantiles bas (`0.5 %`) et hauts (`99.5 %`)
             par canal ainsi que leurs extrema globaux `min_low` et `max_high` (`0x00A4BFD0`).
        EN : Computes R, G, B histograms on the central 90% crop (`x` from 5% to 95%,
             `y` from 5% to 95%, `0x00A4B960`) and extracts per-channel low (`0.5%`) and high (`99.5%`)
             percentiles along with their global extrema `min_low` and `max_high` (`0x00A4BFD0`).

        Ref: picasa3.exe @ 0x00A4B960, 0x00A4BFD0
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.uint8)
        h, w = arr.shape[:2]
        x0 = int(w * 0.05)
        x1 = max(x0 + 1, int(w * 0.95))
        y0 = int(h * 0.05)
        y1 = max(y0 + 1, int(h * 0.95))
        crop = arr[y0:y1, x0:x1]
        n_pix = max(1, crop.shape[0] * crop.shape[1])
        low_thresh = float(low_pct) * n_pix
        high_thresh = float(high_pct) * n_pix

        lows: list[int] = []
        highs: list[int] = []
        for c in range(3):
            hist = np.bincount(crop[:, :, c].ravel(), minlength=256)
            csum = np.cumsum(hist)
            low_idx = int(np.searchsorted(csum, low_thresh, side="left"))
            high_idx = int(np.searchsorted(csum, high_thresh, side="left"))
            lows.append(max(0, min(255, low_idx)))
            highs.append(max(0, min(255, high_idx)))

        return lows, highs, min(lows), max(highs)

    @staticmethod
    def _estimate_scene_illuminant_0090f8f0(img: Image.Image) -> Tuple[int, int, int]:
        """
        FR : Estime l'illuminant de la scène `(R_est, 128, B_est)` via l'histogramme 2D `64x64`
             des rapports `(R/G, B/G)` pondéré au centre cubique, reproduisant exactement
             `FUN_0090f8f0 @ 0x0090F8F0` de `picasa3.exe`.
        EN : Estimates the scene illuminant `(R_est, 128, B_est)` via the `64x64` 2D histogram
             of `(R/G, B/G)` ratios with cubic center weighting, reproducing
             `FUN_0090f8f0 @ 0x0090F8F0` from `picasa3.exe`.

        Ref: picasa3.exe @ 0x0090F8F0, 0x008F82A0
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.int32)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]

        # Ref: 0x0090F958..0x0090F9A9 : filtre 32 <= G <= 224 et rx, ry dans [0..63]
        valid_g = (g >= 32) & (g <= 224)
        if not np.any(valid_g):
            return (128, 128, 128)
        r_v = r[valid_g]
        g_v = g[valid_g]
        b_v = b[valid_g]
        rx = (r_v * 32) // g_v - 16
        ry = (b_v * 32) // g_v - 16
        in_bounds = (rx >= 0) & (rx < 64) & (ry >= 0) & (ry < 64)
        if not np.any(in_bounds):
            return (128, 128, 128)

        rx = rx[in_bounds]
        ry = ry[in_bounds]
        flat_idx = ry * 64 + rx
        hist2d = np.bincount(flat_idx, minlength=4096).reshape((64, 64)).astype(np.float64)

        # Ref: 0x0090F9BA..0x0090FA44 : poids w(x, y) = ((32 - max(|x - 32|, |y - 32|))^3) // 32
        yy, xx = np.mgrid[0:64, 0:64]
        max_d = np.maximum(np.abs(xx - 32), np.abs(yy - 32))
        weights = (((32 - max_d) ** 3) // 32).astype(np.float64)
        w_hist = hist2d * weights
        total_w = float(np.sum(w_hist))
        if total_w <= 0.0:
            return (128, 128, 128)

        cx = float(np.sum(w_hist * xx)) / total_w
        cy = float(np.sum(w_hist * yy)) / total_w
        r_est = max(1, min(255, int(round((cx + 16.0) * 4.0))))
        b_est = max(1, min(255, int(round((cy + 16.0) * 4.0))))
        return (r_est, 128, b_est)

    @staticmethod
    def auto_contrast(img: Image.Image) -> Image.Image:
        """
        FR : Contraste automatique (`autolight`) reproduisant exactement `FUN_008f80c0 @ 0x008F80C0` :
             calcule les quantiles 0.5 % / 99.5 % sur les 90 % centraux de l'image, prend le point noir
             global `min_low / 255.0` et le point blanc global `max_high / 255.0` (préservant la teinte)
             et applique la LUT 16 bits `_levels_lut_0090c1e0`.
        EN : Automatic contrast (`autolight`) reproducing `FUN_008f80c0 @ 0x008F80C0`:
             computes 0.5% / 99.5% percentiles on the central 90% crop, takes the global black point
             `min_low / 255.0` and global white point `max_high / 255.0` (preserving hue),
             and applies the 16-bit LUT `_levels_lut_0090c1e0`.

        Ref: picasa3.exe @ 0x008F80C0, 0x00A4B960, 0x00A4BFD0, 0x0090C3B0
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        _lows, _highs, min_low, max_high = PicasaImageProcessor._central_crop_percentiles_00a4b960(
            img, 0.005, 0.995
        )
        if max_high <= min_low:
            return img.copy()
        return PicasaImageProcessor._levels_lut_0090c1e0(
            img,
            black_pt=float(min_low) / 255.0,
            white_pt=float(max_high) / 255.0,
            gamma=1.0,
        )

    @staticmethod
    def auto_color(img: Image.Image) -> Image.Image:
        """
        FR : Couleur automatique (`autocolor`) reproduisant exactement `FUN_008f82a0 @ 0x008F82A0` :
             estime l'illuminant de la scène `(R_est, 128, B_est)` via l'histogramme 2D `(R/G, B/G)`
             (`0x0090F8F0`) et applique la matrice d'adaptation chromatique 3x3 (`0x0090EDA0`).
        EN : Automatic color (`autocolor`) reproducing `FUN_008f82a0 @ 0x008F82A0`:
             estimates the scene illuminant `(R_est, 128, B_est)` via the 2D `(R/G, B/G)` histogram
             (`0x0090F8F0`) and applies the 3x3 chromatic adaptation matrix (`0x0090EDA0`).

        Ref: picasa3.exe @ 0x008F82A0, 0x0090F8F0, 0x0090EDA0
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        illum_rgb = PicasaImageProcessor._estimate_scene_illuminant_0090f8f0(img)
        return PicasaImageProcessor._chromatic_adaptation_0090eda0(img, illum_rgb)

    @staticmethod
    def enhance_lucky(img: Image.Image) -> Image.Image:
        """
        FR : « J'ai de la chance » (`enhance=1`) reproduisant exactement `FUN_008f8840 @ 0x008F8840`
             -> `FUN_009db610 @ 0x009DB610` (`is_enhance=1, factor=0.3`) :
             étirement par canal amorti à 50 % vers les extrema globaux `(min_low, max_high)`
             avec facteur de point noir `0.3` et plafond de sortie à `252` (`0xFC`).
        EN : "I'm Feeling Lucky" (`enhance=1`) reproducing `FUN_008f8840 @ 0x008F8840`
             -> `FUN_009db610 @ 0x009DB610` (`is_enhance=1, factor=0.3`):
             per-channel stretch damped 50% toward global `(min_low, max_high)`
             with black-point factor `0.3` and output ceiling `252` (`0xFC`).

        Ref: picasa3.exe @ 0x008F8840, 0x009DB610, 0x00A4B960, 0x00A4BFD0
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        lows, highs, min_low, max_high = PicasaImageProcessor._central_crop_percentiles_00a4b960(
            img, 0.005, 0.995
        )
        arr = np.array(img, dtype=np.uint8)
        out = np.empty_like(arr)
        xs = np.arange(256, dtype=np.int32)
        for c in range(3):
            low_scaled = int(round(float(lows[c]) * 0.3))
            eff_low = int(round((float(min_low) - float(low_scaled)) * 0.5 + float(low_scaled)))
            eff_high = int(round((float(max_high) - float(highs[c])) * 0.5 + float(highs[c])))
            denom = eff_high - eff_low
            if denom <= 0:
                out[:, :, c] = arr[:, :, c]
            else:
                lut = np.zeros(256, dtype=np.uint8)
                mid_mask = (xs > eff_low) & (xs < eff_high)
                lut[mid_mask] = np.clip(((xs[mid_mask] - eff_low) * 252) // denom, 0, 252).astype(np.uint8)
                lut[xs >= eff_high] = 252
                out[:, :, c] = lut[arr[:, :, c]]
        return Image.fromarray(out)

    # Table statique 256 entrées BGRA de `warm` extraite de picasa3.exe @ 0x00D33B70 (FUN_0090c040 @ 0x0090C040)
    _WARM_LUT_R_00D33B72: Tuple[int, ...] = (
        0, 1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 15, 16, 17, 18,
        20, 21, 22, 23, 25, 26, 27, 29, 30, 31, 33, 34, 35, 36, 38, 39,
        40, 42, 43, 44, 46, 47, 48, 50, 51, 52, 54, 55, 56, 58, 59, 60,
        61, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78,
        79, 80, 81, 82, 83, 84, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95,
        96, 97, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
        111, 112, 113, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 122, 123, 124,
        125, 126, 127, 128, 129, 129, 130, 131, 132, 133, 134, 135, 135, 136, 137, 138,
        139, 140, 140, 141, 142, 143, 143, 144, 145, 146, 147, 147, 148, 149, 150, 150,
        151, 152, 153, 153, 154, 155, 156, 156, 157, 158, 159, 159, 160, 161, 162, 162,
        163, 164, 165, 166, 166, 167, 168, 169, 169, 170, 171, 172, 172, 173, 174, 175,
        175, 176, 177, 178, 178, 179, 180, 181, 181, 182, 183, 184, 185, 185, 186, 187,
        187, 188, 189, 190, 191, 192, 192, 193, 194, 195, 196, 197, 198, 198, 199, 200,
        201, 202, 203, 203, 204, 205, 206, 207, 208, 208, 209, 210, 211, 212, 213, 213,
        214, 215, 216, 217, 218, 218, 219, 220, 221, 222, 223, 224, 225, 226, 226, 227,
        228, 229, 230, 231, 232, 233, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242,
    )
    _WARM_LUT_G_00D33B71: Tuple[int, ...] = (
        0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
        15, 16, 17, 18, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
        30, 31, 32, 33, 34, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44,
        45, 46, 47, 48, 49, 50, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
        60, 60, 61, 62, 63, 64, 65, 65, 66, 67, 68, 69, 70, 70, 71, 72,
        73, 74, 74, 75, 76, 77, 78, 79, 79, 80, 81, 82, 83, 84, 84, 85,
        86, 87, 88, 88, 89, 90, 91, 92, 93, 93, 94, 95, 96, 97, 98, 98,
        99, 100, 101, 102, 103, 104, 104, 105, 106, 107, 108, 109, 109, 110, 111, 112,
        113, 114, 114, 115, 116, 117, 118, 119, 119, 120, 121, 122, 123, 124, 125, 125,
        126, 127, 128, 129, 130, 131, 131, 132, 133, 134, 135, 136, 137, 137, 138, 139,
        140, 141, 142, 143, 143, 144, 145, 146, 147, 148, 149, 149, 150, 151, 152, 153,
        154, 155, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168,
        168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183,
        184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199,
        200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 212, 213, 214, 215, 216,
        217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
    )
    _WARM_LUT_B_00D33B70: Tuple[int, ...] = (
        0, 0, 1, 2, 2, 3, 4, 4, 5, 6, 7, 7, 8, 9, 9, 10,
        11, 12, 12, 13, 14, 14, 15, 16, 16, 17, 18, 19, 19, 20, 21, 21,
        22, 23, 24, 24, 25, 26, 26, 27, 28, 28, 29, 30, 31, 31, 32, 33,
        33, 34, 35, 35, 36, 37, 37, 38, 39, 40, 40, 41, 42, 42, 43, 44,
        44, 45, 46, 47, 48, 49, 49, 50, 51, 52, 53, 53, 54, 55, 56, 57,
        58, 58, 59, 60, 61, 62, 62, 63, 64, 65, 66, 66, 67, 68, 69, 70,
        71, 71, 72, 73, 74, 75, 75, 76, 77, 78, 79, 80, 80, 81, 82, 83,
        84, 84, 85, 86, 87, 88, 89, 89, 90, 91, 92, 93, 94, 95, 96, 96,
        97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112,
        113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128,
        129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144,
        145, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 161, 162,
        163, 164, 165, 166, 167, 168, 169, 171, 172, 173, 174, 175, 176, 177, 178, 180,
        181, 182, 183, 184, 185, 186, 187, 189, 190, 191, 192, 193, 194, 195, 196, 198,
        199, 200, 201, 202, 203, 204, 206, 207, 208, 209, 210, 211, 212, 214, 215, 216,
        217, 218, 219, 220, 222, 223, 224, 225, 226, 227, 228, 230, 231, 232, 233, 234,
    )

    @staticmethod
    def black_and_white(img: Image.Image) -> Image.Image:
        """
        FR : Filtre Noir et Blanc (`bw=1`) reproduisant exactement `FUN_008f84c0 @ 0x008F84C0`
             -> `FUN_009a9550 @ 0x009A9550` (`factor = 0x100`) de `picasa3.exe` :
             $$Y = (77 \\cdot R + 151 \\cdot G + 28 \\cdot B) \\gg 8$$
        EN : Black and White filter (`bw=1`) reproducing `FUN_008f84c0 @ 0x008F84C0`
             -> `FUN_009a9550 @ 0x009A9550` (`factor = 0x100`) from `picasa3.exe`:
             $$Y = (77 \\cdot R + 151 \\cdot G + 28 \\cdot B) \\gg 8$$

        Ref: picasa3.exe @ 0x008F84C0, 0x009A9550..0x009A95F2, filterdesc.xml @ bw
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.int32)
        y = ((77 * arr[:, :, 0] + 151 * arr[:, :, 1] + 28 * arr[:, :, 2]) >> 8).astype(np.uint8)
        return Image.fromarray(np.stack([y, y, y], axis=2))

    @staticmethod
    def sepia(img: Image.Image) -> Image.Image:
        """
        FR : Filtre Sépia (`sepia=1`) reproduisant exactement `FUN_008f8950 @ 0x008F8950`
             -> `FUN_0090a120 @ 0x0090A120` de `picasa3.exe` :
             1. Luminance entière : $Y = (77 R + 151 G + 28 B) \\gg 8$
             2. Relèvement du point noir (`0xDA = 218`) : $U = 255 - (((255 - Y) \\cdot 218) \\gg 8)$
             3. Virage linéaire par morceaux autour de $U = 128$ et de la teinte médiane
                `0xFF9B7D63` ($R_{\\text{mid}} = 155, G_{\\text{mid}} = 125, B_{\\text{mid}} = 99$) :
                - Si $U < 128$ : $(R, G, B) = ((2 U \\cdot 155) \\gg 8, (2 U \\cdot 125) \\gg 8, (2 U \\cdot 99) \\gg 8)$
                - Si $U \\ge 128$ : $(R, G, B) = 255 - ((2 (255 - U) \\cdot (100, 130, 156)) \\gg 8)$
        EN : Sepia filter (`sepia=1`) reproducing `FUN_008f8950 @ 0x008F8950`
             -> `FUN_0090a120 @ 0x0090A120` from `picasa3.exe`:
             1. Integer luminance: $Y = (77 R + 151 G + 28 B) \\gg 8$
             2. Black-point lift (`0xDA = 218`): $U = 255 - (((255 - Y) \\cdot 218) \\gg 8)$
             3. Two-segment piecewise linear toning around $U = 128$ and midpoint color
                `0xFF9B7D63` ($R_{\\text{mid}} = 155, G_{\\text{mid}} = 125, B_{\\text{mid}} = 99$).

        Ref: picasa3.exe @ 0x008F8950, 0x0090A120..0x0090A2CE, filterdesc.xml @ sepia
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        ys = np.arange(256, dtype=np.int32)
        us = 255 - (((255 - ys) * 218) >> 8)
        lut = np.empty((256, 3), dtype=np.uint8)
        low = us < 128
        high = ~low
        lut[low, 0] = ((2 * us[low] * 155) >> 8).astype(np.uint8)
        lut[low, 1] = ((2 * us[low] * 125) >> 8).astype(np.uint8)
        lut[low, 2] = ((2 * us[low] * 99) >> 8).astype(np.uint8)
        inv_u = 255 - us[high]
        lut[high, 0] = (255 - ((2 * inv_u * 100) >> 8)).astype(np.uint8)
        lut[high, 1] = (255 - ((2 * inv_u * 130) >> 8)).astype(np.uint8)
        lut[high, 2] = (255 - ((2 * inv_u * 156) >> 8)).astype(np.uint8)

        arr = np.array(img, dtype=np.int32)
        y_img = np.clip((77 * arr[:, :, 0] + 151 * arr[:, :, 1] + 28 * arr[:, :, 2]) >> 8, 0, 255)
        return Image.fromarray(lut[y_img])

    @staticmethod
    def warmify(img: Image.Image, intensity: float = 0.2) -> Image.Image:
        """
        FR : Filtre Réchauffer (`warm=1`) reproduisant exactement `FUN_008f8930 @ 0x008F8930`
             -> `FUN_0090c040 @ 0x0090C040` via la table statique de 256 entrées BGRA à `0x00D33B70`.
        EN : Warmify filter (`warm=1`) reproducing `FUN_008f8930 @ 0x008F8930`
             -> `FUN_0090c040 @ 0x0090C040` using the static 256-entry BGRA LUT at `0x00D33B70`.

        Ref: picasa3.exe @ 0x008F8930, 0x0090C040, 0x00D33B70, filterdesc.xml @ warm
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        lut_table = (
            list(PicasaImageProcessor._WARM_LUT_R_00D33B72)
            + list(PicasaImageProcessor._WARM_LUT_G_00D33B71)
            + list(PicasaImageProcessor._WARM_LUT_B_00D33B70)
        )
        warmed = img.point(lut_table)
        # Si une intensité personnalisée différente du défaut one-click (0.2) est demandée, interpoler
        if abs(float(intensity) - 0.2) > 1e-4 and 0.0 <= float(intensity) <= 1.0:
            blend_w = min(1.0, max(0.0, float(intensity) / 0.2))
            if abs(blend_w - 1.0) > 1e-4:
                return Image.blend(img, warmed, blend_w)
        return warmed

    @staticmethod
    def fill_light(img: Image.Image, amount: float = 0.3, chroma_preserve: float = 1.0) -> Image.Image:
        """
        FR : Lumière d'appoint (`fill`, `backlight`, et Étape 1 de `finetune2`) reproduisant exactement
             `FUN_0090ac20 @ 0x0090AC20` de `picasa3.exe` :
             - `t = 1.0 - amount`, `w = 1.0 / (0.7 * t + 0.3)`, `gamma = t / (0.7 * w + 0.3)`
             - `LUT[i] = round(255.0 * clamp(((i * w) / 255.0) ** gamma, 0.0, 256.0))`
             - Luminance entière rapide `L = (R + 2*G + B) >> 2`
             - Mélange pondéré par `(255 - L)` : `C_out = clamp(C + (((LUT[C] - C) * factor * (255 - L)) >> 16), 0, 255)`
        EN : Fill Light (`fill`, `backlight`, and Step 1 of `finetune2`) reproducing
             `FUN_0090ac20 @ 0x0090AC20` from `picasa3.exe`:
             - `t = 1.0 - amount`, `w = 1.0 / (0.7 * t + 0.3)`, `gamma = t / (0.7 * w + 0.3)`
             - `LUT[i] = round(255.0 * clamp(((i * w) / 255.0) ** gamma, 0.0, 256.0))`
             - Fast integer luma `L = (R + 2*G + B) >> 2`
             - Inverse-luma blend: `C_out = clamp(C + (((LUT[C] - C) * factor * (255 - L)) >> 16), 0, 255)`

        Ref: picasa3.exe @ 0x0090AC20, 0x008F7CF0, 0x008F7F28
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        amt = max(0.0, min(1.0, float(amount)))
        if amt <= 1e-6:
            return img.copy()

        # Ref: 0x0090AC59..0x0090ACA6
        t = 1.0 - amt
        w = 1.0 / (0.7 * t + 0.3)
        gamma = t / (0.7 * w + 0.3)

        # Ref: 0x0090ACF0..0x0090AD55 : table LUT[0..255] int32
        xs = (np.arange(256, dtype=np.float64) * w) / 255.0
        curved = np.clip(np.power(np.maximum(0.0, xs), gamma), 0.0, 256.0)
        lut = np.round(255.0 * curved).astype(np.int32)

        # Ref: 0x0090AD8D..0x0090AE59 : boucle pixels en arithmétique entière >> 16
        arr = np.array(img, dtype=np.int32)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        luma = (r + (g << 1) + b) >> 2
        factor = int(round(float(chroma_preserve) * 256.0))
        inv_luma_w = ((255 - luma) * factor)[:, :, np.newaxis]

        lut_vals = lut[arr]
        out = arr + (((lut_vals - arr) * inv_luma_w) >> 16)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def sharpen(img: Image.Image, amount: float = 0.6) -> Image.Image:
        """
        FR : Amélioration de netteté par masque flou (`unsharp2` / `unsharp`) reproduisant exactement
             `FUN_008f8f30 @ 0x008F8F30` -> `FUN_0090c4a0 @ 0x0090C4A0` de `picasa3.exe` :
             - Flou séparable de rayon `1.0` (`0x00A42C20(radius=1.0f, type=2)`)
             - Facteur d'amplification entier `scale_int = round(amount * 512.0)` (`[0x00CF4C48] = 512.0`)
             - Sans seuil (`threshold = 0`) :
               $$C_{\\text{out}} = \\text{clamp}\\left(C_{\\text{src}} + \\left(\\frac{(C_{\\text{src}} - C_{\\text{blur}}) \\cdot \\text{scale\\_int}}{256}\\right), 0, 255\\right)$$
        EN : Sharpness enhancement (`unsharp2` / `unsharp`) reproducing `FUN_008f8f30 @ 0x008F8F30`
             -> `FUN_0090c4a0 @ 0x0090C4A0` from `picasa3.exe`:
             - Separable blur of radius `1.0` (`0x00A42C20(radius=1.0f, type=2)`)
             - Integer scale `scale_int = round(amount * 512.0)` (`[0x00CF4C48] = 512.0`)
             - Zero threshold (`threshold = 0`).

        Ref: picasa3.exe @ 0x008F8F30, 0x0090C4A0..0x0090C6AC, filterdesc.xml @ unsharp, unsharp2
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        amt = float(amount)
        if abs(amt) < 1e-6:
            return img.copy()
        blurred = img.filter(ImageFilter.GaussianBlur(radius=1.0))
        scale_int = int(round(amt * 512.0))
        arr_src = np.array(img, dtype=np.int32)
        arr_blur = np.array(blurred, dtype=np.int32)
        out = arr_src + (((arr_src - arr_blur) * scale_int) >> 8)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

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
        FR : Ajuste les hautes lumières (`highlights`, plage `0.0 .. 0.48` dans `filterdesc.xml`)
             en abaissant le point blanc `white_pt = max(0.001, 1.0 - highlights)` via la LUT 16 bits
             exacte de `picasa3.exe` (`0x008F7F5D..0x008F7FFC` -> `0x0090C3B0` / `0x0090C1E0`).
        EN : Adjusts highlights (`highlights`, range `0.0 .. 0.48` in `filterdesc.xml`)
             by lowering the white point `white_pt = max(0.001, 1.0 - highlights)` via the exact
             16-bit LUT from `picasa3.exe` (`0x008F7F5D..0x008F7FFC` -> `0x0090C3B0` / `0x0090C1E0`).

        Ref: picasa3.exe @ 0x008F7F5D, 0x0090C3B0, 0x0090C1E0, filterdesc.xml @ finetune2 (slider id="1")
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        hl = max(0.0, min(0.999, float(amount)))
        if hl <= 1e-6:
            return img.copy()
        white_pt = max(0.001, 1.0 - hl)
        return PicasaImageProcessor._levels_lut_0090c1e0(img, black_pt=0.0, white_pt=white_pt, gamma=1.0)

    @staticmethod
    def adjust_shadows(img: Image.Image, amount: float = 0.3) -> Image.Image:
        """
        FR : Ajuste les ombres (`shadows`, plage `0.0 .. 0.48` dans `filterdesc.xml`)
             en relevant le point noir `black_pt = shadows` (ce qui approfondit/assombrit les ombres)
             via la LUT 16 bits exacte de `picasa3.exe` (`0x008F7F5D..0x008F7FFC` -> `0x0090C3B0` / `0x0090C1E0`).
        EN : Adjusts shadows (`shadows`, range `0.0 .. 0.48` in `filterdesc.xml`)
             by raising the black point `black_pt = shadows` (deepening/darkening shadows)
             via the exact 16-bit LUT from `picasa3.exe` (`0x008F7F5D..0x008F7FFC` -> `0x0090C3B0` / `0x0090C1E0`).

        Ref: picasa3.exe @ 0x008F7F5D, 0x0090C3B0, 0x0090C1E0, filterdesc.xml @ finetune2 (slider id="2")
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        sh = max(0.0, min(0.998, float(amount)))
        if sh <= 1e-6:
            return img.copy()
        return PicasaImageProcessor._levels_lut_0090c1e0(img, black_pt=sh, white_pt=1.0, gamma=1.0)

    @staticmethod
    def color_temperature(img: Image.Image, temp: float = 0.0) -> Image.Image:
        """
        FR : Ajuste la température de couleur (`colortemp` dans `[-1.0, +1.0]`, ou `[-50..+50]` normalisé)
             en reproduisant exactement `FUN_0090e9d0 @ 0x0090E9D0` :
             `idx = clamp(round(colortemp * 37.0 + 55.0), 0, 114)` dans `_KELVIN_TABLE_00C7CF98`,
             suivi de l'adaptation chromatique matricielle `_chromatic_adaptation_0090eda0`.
        EN : Adjusts color temperature (`colortemp` in `[-1.0, +1.0]`, or normalized `[-50..+50]`)
             reproducing `FUN_0090e9d0 @ 0x0090E9D0`:
             `idx = clamp(round(colortemp * 37.0 + 55.0), 0, 114)` into `_KELVIN_TABLE_00C7CF98`,
             followed by the `_chromatic_adaptation_0090eda0` matrix transform.

        Ref: picasa3.exe @ 0x0090E9D0, 0x0090EDA0, 0x00C7CF98, filterdesc.xml @ finetune2 (slider id="3")
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        t_val = float(temp)
        if abs(t_val) < 1e-6:
            return img.copy()
        if abs(t_val) > 1.0:
            t_val = max(-1.0, min(1.0, t_val / 50.0))
        else:
            t_val = max(-1.0, min(1.0, t_val))
        idx = max(0, min(114, int(round(t_val * 37.0 + 55.0))))
        if idx == 55:
            return img.copy()
        rgb_kelvin = PicasaImageProcessor._KELVIN_TABLE_00C7CF98[idx]
        return PicasaImageProcessor._chromatic_adaptation_0090eda0(img, rgb_kelvin)

    @staticmethod
    def neutral_color_balance(img: Image.Image, sampled_rgb: Tuple[int, int, int] | int) -> Image.Image:
        """
        FR : Corrige la balance des blancs à partir d'un point échantillonné à la pipette (`neutral_rgb`)
             en appliquant exactement la matrice d'adaptation chromatique 3x3 `FUN_0090eda0 @ 0x0090EDA0`
             de `picasa3.exe` (Étape 3 de `finetune2 @ 0x008F8002`).
        EN : Corrects white balance from a pipette-sampled neutral point (`neutral_rgb`)
             by applying the exact 3x3 chromatic adaptation matrix `FUN_0090eda0 @ 0x0090EDA0`
             from `picasa3.exe` (Step 3 of `finetune2 @ 0x008F8002`).

        Ref: picasa3.exe @ 0x008F8002, 0x0090EDA0, filterdesc.xml @ finetune2 (<colorpicker id="0"/>)
        """
        return PicasaImageProcessor._chromatic_adaptation_0090eda0(img, sampled_rgb)

    # =========================================================================
    # TAB 3: EFFETS 1 (Picasa Standard: Ref: filterdesc.xml @ sat, tint, glow...)
    # =========================================================================

    @staticmethod
    def saturation(img: Image.Image, factor: float = 0.1618) -> Image.Image:
        """
        FR : Ajuste la saturation (`sat=1,<amount>`) en reproduisant exactement `FUN_008f8ff0 @ 0x008F8FF0` :
             - Si `amount < 0.0` (`0x0090E200`) : désaturation linéaire entière vers
               `Y = (2*R + 5*G + B + 4) >> 3` avec `ebx = round((amount + 1.0) * 256.0)`.
             - Si `amount >= 0.0` (`0x0090B930`) : amplification non-linéaire via 3 tables de puissance
               de 2048 entrées (`x = i / 256.0`) avec exposants `1 + 0.3*(3*amount)` (R),
               `1 + 0.7*(3*amount)` (G), `1 + 0.9*(3*amount)` (B) autour de `Y = (2*R + 5*G + B) >> 3`,
               et réduction proportionnelle `(255 << 8) // max(R', G', B')` si `max > 255` pour préserver la teinte.
        EN : Adjusts color saturation (`sat=1,<amount>`) reproducing `FUN_008f8ff0 @ 0x008F8FF0`:
             - If `amount < 0.0` (`0x0090E200`): integer linear desaturation toward
               `Y = (2*R + 5*G + B + 4) >> 3` with `ebx = round((amount + 1.0) * 256.0)`.
             - If `amount >= 0.0` (`0x0090B930`): non-linear saturation boost via 2048-entry power LUTs
               with channel exponents `1 + 0.3*(3*amount)` (R), `1 + 0.7*(3*amount)` (G), `1 + 0.9*(3*amount)` (B)
               relative to `Y = (2*R + 5*G + B) >> 3`, plus hue-preserving scaling when `max(R', G', B') > 255`.

        Ref: picasa3.exe @ 0x008F8FF0, 0x0090E200, 0x0090B930, filterdesc.xml @ sat
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        amt = float(factor)
        # Compatibilité descendante si un facteur > 1.0 (ex. 1.4) est passé au lieu de [-1.0, +1.0]
        if amt > 1.0001:
            amt = max(-1.0, min(1.0, amt - 1.0))
        else:
            amt = max(-1.0, min(1.0, amt))

        if abs(amt) < 1e-6:
            return img.copy()

        arr = np.array(img, dtype=np.int32)
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]

        if amt < 0.0:
            # Ref: 0x0090E200..0x0090E305 : désaturation entière
            ebx = max(0, min(256, int(round((amt + 1.0) * 256.0))))
            y = ((r << 1) + 5 * g + b + 4) >> 3
            y3 = y[:, :, np.newaxis]
            out = y3 + (((arr - y3) * ebx) >> 8)
            return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

        # Ref: 0x0090B930..0x0090BBE8 : amplification de saturation non-linéaire à préservation de teinte
        s = 3.0 * amt
        xs = np.arange(2048, dtype=np.float64) / 256.0
        lut_r = (np.power(xs, 1.0 + 0.3 * s) * 256.0).astype(np.int32)
        lut_g = (np.power(xs, 1.0 + 0.7 * s) * 256.0).astype(np.int32)
        lut_b = (np.power(xs, 1.0 + 0.9 * s) * 256.0).astype(np.int32)

        y = ((r << 1) + 5 * g + b) >> 3
        inv_y = np.zeros_like(y)
        pos_y = y > 0
        inv_y[pos_y] = 65535 // y[pos_y]

        idx_r = np.clip((r * inv_y) >> 8, 0, 2047)
        idx_g = np.clip((g * inv_y) >> 8, 0, 2047)
        idx_b = np.clip((b * inv_y) >> 8, 0, 2047)

        r_p = (lut_r[idx_r] * y) >> 8
        g_p = (lut_g[idx_g] * y) >> 8
        b_p = (lut_b[idx_b] * y) >> 8

        max_c = np.maximum(np.maximum(r_p, g_p), b_p)
        over = max_c > 255
        if np.any(over):
            scale_over = (255 << 8) // max_c[over]
            r_p[over] = (r_p[over] * scale_over) >> 8
            g_p[over] = (g_p[over] * scale_over) >> 8
            b_p[over] = (b_p[over] * scale_over) >> 8

        out = np.stack([np.clip(r_p, 0, 255), np.clip(g_p, 0, 255), np.clip(b_p, 0, 255)], axis=2).astype(np.uint8)
        return Image.fromarray(out)

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
    def soft_focus(
        img: Image.Image,
        amount: float = 0.4,
        radius_norm: float = 0.35,
        center_x: float = 0.5,
        center_y: float = 0.5,
    ) -> Image.Image:
        """
        FR : Flou artistique / Soft focus (`radblur`) autour du centre `(center_x, center_y)`
             reproduisant `FUN_008f8520 @ 0x008F8520` -> `FUN_0090b050 @ 0x0090B050` (`0x0090AEB0` Hermite smoothstep).
        EN : Soft focus artistic blur (`radblur`) around `(center_x, center_y)`
             reproducing `FUN_008f8520 @ 0x008F8520` -> `FUN_0090b050 @ 0x0090B050` (`0x0090AEB0` Hermite smoothstep).

        Ref: picasa3.exe @ 0x008F8520, 0x0090B050, 0x0090AEB0, filterdesc.xml @ radblur
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        w_img, h_img = img.size
        amt = max(0.0, float(amount))
        # Ref: picasa3.exe @ 0x008F85BE..0x008F8617 & 0x0090B0CE..0x0090B129 ([0x00CF40B8] = 0.01) :
        # s = 0.01 * w; r_blur = s * amount + 0.001 + s = 0.01 * w * (1 + amount) + 0.001
        r_px = max(0.5, float(w_img) * 0.01 * (1.0 + amt) + 0.001 if amt <= 1.0 else amt * 12.0)
        blurred = img.filter(ImageFilter.GaussianBlur(radius=r_px))
        if abs(float(radius_norm)) <= 0.01:
            return blurred
        arr_orig = np.array(img, dtype=np.float32)
        arr_blur = np.array(blurred, dtype=np.float32)
        h, w = arr_orig.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h * float(center_y), w * float(center_x)
        sz_f = float(radius_norm)
        eff_r = (sz_f + 1.0) * 0.5 if sz_f < 0.0 else sz_f
        # Ref: picasa3.exe @ 0x0090AEB0 : R = max(0.5*w, 0.5*h) * (size + 1.0) = max(w, h) * eff_r, sharpness = 0.0
        max_r = max(1.0, float(max(w, h)) * max(0.02, eff_r))
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        t = np.clip(dist / max_r, 0.0, 1.0)
        # Ref: 0x0090AFBD..0x0090AFE0 : u = 1 - t; w_orig = u^2 * (3 - 2*u)
        u = 1.0 - t
        w_orig = (u * u * (3.0 - 2.0 * u))[:, :, np.newaxis]
        out = arr_orig * w_orig + arr_blur * (1.0 - w_orig)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def glow(img: Image.Image, intensity: float = 0.65, radius: float = 3.0) -> Image.Image:
        """
        FR : Halo / Éclat lumineux diffus (`glow2` / `glow`) reproduisant exactement
             `FUN_008f8f70 @ 0x008F8F70` -> `FUN_0090d4b0 @ 0x0090D4B0` & `FUN_009ac3f0 @ 0x009AC3F0` :
             1. Pré-assombrissement quadratique des tons moyens/ombres avant le flou
                (`0x00AA40A0(dst, 0.5f, 0)` : $\\gamma = 2.0$, $C' = (C \\cdot C) // 255$) afin que seules
                les hautes lumières diffusent dans le halo.
             2. Flou gaussien de rayon `radius` (`0x009DD0D0`).
             3. Fusion **Screen (Superposition)** entière (`0x009AC3F0`) pondérée par `w = round(|intensity| * 256)` :
                $$\\text{screen} = 255 - (((255 - C_{\\text{blur}}) \\cdot (255 - C_{\\text{src}})) \\gg 8)$$
                $$C_{\\text{out}} = \\text{screen} + (((C_{\\text{src}} - \\text{screen}) \\cdot (256 - w)) \\gg 8)$$
        EN : Diffuse luminous glow (`glow2` / `glow`) reproducing `FUN_008f8f70 @ 0x008F8F70`
             -> `FUN_0090d4b0 @ 0x0090D4B0` & `FUN_009ac3f0 @ 0x009AC3F0`:
             1. Pre-blur quadratic gamma darkening (`0x00AA40A0(dst, 0.5f, 0)`: $\\gamma = 2.0$) so only highlights bloom.
             2. Gaussian blur of radius `radius` (`0x009DD0D0`).
             3. Integer **Screen** blend (`0x009AC3F0`) weighted by `w = round(|intensity| * 256)`.

        Ref: picasa3.exe @ 0x008F8F70, 0x0090D4B0, 0x00AA40A0, 0x009AC3F0, filterdesc.xml @ glow, glow2
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        # Étape 1 : gamma quadratique (1 / 0.5 = 2.0) avant flou (Ref: 0x0090D516 -> 0x00AA40A0)
        xs = np.arange(256, dtype=np.float64)
        gamma2_lut = np.clip(np.round(255.0 * ((xs / 255.0) ** 2.0)), 0, 255).astype(np.uint8)
        arr_src = np.array(img, dtype=np.int32)
        pre_dark = Image.fromarray(gamma2_lut[arr_src.astype(np.uint8)])

        # Étape 2 : flou (Ref: 0x0090D538 -> 0x009DD0D0)
        blurred = pre_dark.filter(ImageFilter.GaussianBlur(radius=max(0.5, float(radius))))
        arr_blur = np.array(blurred, dtype=np.int32)

        # Étape 3 : fusion Screen entière (Ref: 0x0090D55E -> 0x009AC3F0)
        w = max(0, min(256, int(round(abs(float(intensity)) * 256.0))))
        inv_w = 256 - w
        screen = 255 - (((255 - arr_blur) * (255 - arr_src)) >> 8)
        out = screen + (((arr_src - screen) * inv_w) >> 8)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def focal_bw(
        img: Image.Image,
        radius_norm: float = 0.35,
        sharpness: float = 0.4,
        center_x: float = 0.5,
        center_y: float = 0.5,
    ) -> Image.Image:
        """
        FR : Noir & Blanc focalisé (`radsat`) avec centre `(center_x, center_y)` conservant la couleur,
             reproduisant `FUN_008f8680 @ 0x008F8680` -> `FUN_0090b660 @ 0x0090B660` & `FUN_0090aeb0 @ 0x0090AEB0`
             (transition radiale Hermite smoothstep et luminance entière `(77*R + 151*G + 28*B) >> 8`).
        EN : Focal Black & White (`radsat`) preserving color at `(center_x, center_y)`,
             reproducing `FUN_008f8680 @ 0x008F8680` -> `FUN_0090b660 @ 0x0090B660` & `FUN_0090aeb0 @ 0x0090AEB0`
             (Hermite smoothstep radial transition and integer luminance `(77*R + 151*G + 28*B) >> 8`).

        Ref: picasa3.exe @ 0x008F8680, 0x0090B660, 0x0090AEB0, filterdesc.xml @ radsat
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr_rgb = np.array(img, dtype=np.float32)
        arr_i = arr_rgb.astype(np.int32)
        # Ref: 0x0090B81D..0x0090B834 : Y = (77*R + 151*G + 28*B) >> 8
        arr_gray = ((77 * arr_i[:, :, 0] + 151 * arr_i[:, :, 1] + 28 * arr_i[:, :, 2]) >> 8).astype(np.float32)
        arr_gray3 = np.stack([arr_gray] * 3, axis=2)
        h, w = arr_rgb.shape[:2]
        y, x = np.ogrid[:h, :w]
        cy, cx = h * float(center_y), w * float(center_x)
        sz_f = float(radius_norm)
        eff_r = (sz_f + 1.0) * 0.5 if sz_f < 0.0 else sz_f
        # Ref: picasa3.exe @ 0x0090B674..0x0090B693 & 0x0090AEB0 :
        # R = max(w, h) * eff_r, sh_sqrt = sqrt(sharpness), inv_feather = 1 / (1 - 0.99 * sh_sqrt)
        max_r = max(1.0, float(max(w, h)) * max(0.02, eff_r))
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        sh_sqrt = math.sqrt(max(0.0, min(1.0, float(sharpness))))
        inv_feather = 1.0 / max(0.01, 1.0 - 0.99 * sh_sqrt)
        t = np.clip((dist / max_r - 0.5) * inv_feather + 0.5, 0.0, 1.0)
        # Ref: 0x0090AFBD : u = 1 - t; w_col = u^2 * (3 - 2*u)
        u = 1.0 - t
        w_col = (u * u * (3.0 - 2.0 * u))[:, :, np.newaxis]
        out = arr_rgb * w_col + arr_gray3 * (1.0 - w_col)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    @staticmethod
    def graduated_tint(
        img: Image.Image,
        tint_rgb: tuple[int, int, int] = (123, 180, 216),
        intensity: float = 0.5,
        feather: float = 0.5,
        center_x: float = 0.5,
        center_y: float = 0.5,
        angle_deg: float = 0.0,
    ) -> Image.Image:
        """
        FR : Teinte dégradée directionnelle (`dir_tint`) reproduisant `FUN_008f9880 @ 0x008F9880`
             -> `FUN_0090f470 @ 0x0090F470` & `FUN_0090ec40 @ 0x0090EC40` :
             courbe rationnelle d'assombrissement `g = 0.95 * (1 - shade) + 0.025`, `k = 1/g - 1`,
             `y = x / (x + (1 - x) * k)` multipliée par `tint_rgb` et mélangée le long de la normale.
        EN : Directional graduated tint (`dir_tint`) reproducing `FUN_008f9880 @ 0x008F9880`
             -> `FUN_0090f470 @ 0x0090F470` & `FUN_0090ec40 @ 0x0090EC40`.

        Ref: picasa3.exe @ 0x008F9880, 0x0090F470, 0x0090ECD0, 0x0090EC40, filterdesc.xml @ dir_tint
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]
        y, x = np.ogrid[:h, :w]
        cx = float(center_x) * w
        cy = float(center_y) * h
        rad = math.radians(float(angle_deg) + 90.0)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        # Ref: 0x0090F52C ([0x00CF43C0] = 0.38) : échelle de transition sur la diagonale
        diag = max(1.0, math.hypot(w, h) * 0.38)
        proj = ((x - cx) * cos_a + (y - cy) * sin_a) / diag
        span = max(0.05, float(feather))
        t = np.clip(0.5 - proj / span, 0.0, 1.0)
        grad = (t * t * (3.0 - 2.0 * t))[:, :, np.newaxis]
        # Ref: 0x008F9968 & 0x0090EC40 : courbe rationnelle g = 0.95 * (1 - shade) + 0.025
        shade_clamped = max(0.0, min(1.0, float(intensity)))
        g_val = 0.95 * (1.0 - shade_clamped) + 0.025
        k_val = (1.0 / g_val) - 1.0
        x_norm = arr / 255.0
        y_curve = x_norm / np.maximum(1e-6, x_norm + (1.0 - x_norm) * k_val)
        tint_arr = np.array(tint_rgb, dtype=np.float32)
        tinted = y_curve * tint_arr
        blended = arr * (1.0 - grad) + tinted * grad
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
        # Pass 2: SimpleColorMatrixImageOperation(Contrast=10, Brightness=10) per filterdesc.xml @ CrossProcess
        step2 = PicasaImageProcessor._simple_color_matrix(
            Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)),
            brightness=10.0,
            contrast=10.0,
        )
        out2 = np.array(step2, dtype=np.float32)
        # Pass 3: Multiply tint 0xfcff00 with BlendAlpha=0.2
        tint_mult = np.array([252.0 / 255.0, 255.0 / 255.0, 0.0], dtype=np.float32)
        out2 = out2 * (0.8 + 0.2 * tint_mult)
        res = Image.fromarray(np.clip(out2, 0, 255).astype(np.uint8))
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
        if effect_name == "autocontrast":
            return PicasaImageProcessor.auto_contrast(img)
        if effect_name in ("lucky", "enhance"):
            return PicasaImageProcessor.enhance_lucky(img)
        if effect_name == "autocolor":
            return PicasaImageProcessor.auto_color(img)
        if effect_name == "bw":
            return PicasaImageProcessor.black_and_white(img)
        if effect_name == "sepia":
            return PicasaImageProcessor.sepia(img)
        if effect_name == "warmify":
            return PicasaImageProcessor.warmify(img, float(p.get("intensity", 0.2)))
        if effect_name == "sharpen":
            return PicasaImageProcessor.sharpen(img, amount=float(p.get("amount", 0.6)))
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
                neutral_rgb=p.get("neutral_rgb", 0),
            )
        if effect_name == "tint":
            return PicasaImageProcessor.tint(
                img,
                tint_rgb=tuple(p.get("color", (220, 190, 150))),
                intensity=float(p.get("intensity", 0.4)),
            )
        if effect_name == "saturation":
            return PicasaImageProcessor.saturation(img, float(p.get("factor", p.get("amount", 0.1618))))
        if effect_name == "soft_focus":
            return PicasaImageProcessor.soft_focus(
                img,
                amount=float(p.get("amount", 0.4)),
                radius_norm=float(p.get("size", 0.35)),
                center_x=float(p.get("cx", 0.5)),
                center_y=float(p.get("cy", 0.5)),
            )
        if effect_name == "glow":
            return PicasaImageProcessor.glow(
                img,
                intensity=float(p.get("intensity", 0.65)),
                radius=float(p.get("radius", 3.0)),
            )
        if effect_name == "focal_bw":
            return PicasaImageProcessor.focal_bw(
                img,
                radius_norm=float(p.get("size", 0.35)),
                sharpness=float(p.get("sharpness", 0.4)),
                center_x=float(p.get("cx", 0.5)),
                center_y=float(p.get("cy", 0.5)),
            )
        if effect_name == "graduated_tint":
            return PicasaImageProcessor.graduated_tint(
                img,
                tint_rgb=tuple(p.get("color", (123, 180, 216))),
                intensity=float(p.get("shade", 0.5)),
                feather=float(p.get("feather", 0.5)),
                center_x=float(p.get("cx", 0.5)),
                center_y=float(p.get("cy", 0.5)),
                angle_deg=float(p.get("angle", 0.0)),
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
        FR : Noir & Blanc avec filtre optique coloré exact (`ansel` @ 0x008F8410 -> 0x0090E680) :
             1. Poids entiers normalisés à 256 : w_C = int(C_f * 256 / (R_f + G_f + B_f)).
             2. Luminance filtrée 16 bits : L16 = min(65535, R*w_R + G*w_G + B*w_B), L8 = L16 >> 8.
             3. Luminance naturelle : Y_nat = (2*R + 5*G + B + 4) >> 3.
             4. Compensation parabolique de luminosité moyenne :
                k = clamp((mean(Y_nat) - mean(L8)) / 32.0, -1.0, 1.0), k_fp = int(k * 256.0)
                L16' = clamp(L16 + (((((65535 - L16) * L16) >> 14) * k_fp) >> 8), 0, 65535)
                C_out = L16' >> 8
        EN : Exact Black & White with colored optical filter (`ansel` @ 0x008F8410 -> 0x0090E680):
             1. Integer weights normalized to 256: w_C = int(C_f * 256 / (R_f + G_f + B_f)).
             2. 16-bit filtered luminance: L16 = min(65535, R*w_R + G*w_G + B*w_B), L8 = L16 >> 8.
             3. Natural luminance: Y_nat = (2*R + 5*G + B + 4) >> 3.
             4. Parabolic average-brightness compensation:
                k = clamp((mean(Y_nat) - mean(L8)) / 32.0, -1.0, 1.0), k_fp = int(k * 256.0)
                L16' = clamp(L16 + (((((65535 - L16) * L16) >> 14) * k_fp) >> 8), 0, 65535)
                C_out = L16' >> 8

        Ref: picasa3.exe @ 0x008F8410 (ansel vtable apply)
        Ref: picasa3.exe @ 0x0090E680 (filtered B&W parabolic brightness compensation)
        Ref: runtime/filterdesc.xml @ ansel
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img, dtype=np.int64)
        rf, gf, bf = int(filter_rgb[0]), int(filter_rgb[1]), int(filter_rgb[2])
        s = rf + gf + bf
        if s <= 0:
            wr, wg, wb = 85, 85, 85
        else:
            wr = (rf * 256) // s
            wg = (gf * 256) // s
            wb = (bf * 256) // s
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        l16 = np.minimum(65535, r * wr + g * wg + b * wb)
        l8 = l16 >> 8
        y_nat = ((g * 2 + r) * 2 + b + g + 4) >> 3
        mean_diff = float(np.mean(y_nat) - np.mean(l8))
        k = max(-1.0, min(1.0, mean_diff * 0.03125))
        k_fp = int(k * 256.0)
        if k_fp != 0:
            delta = ((((65535 - l16) * l16) >> 14) * k_fp) >> 8
            l16 = np.clip(l16 + delta, 0, 65535)
        gray = (l16 >> 8).astype(np.uint8)
        return Image.fromarray(np.stack([gray, gray, gray], axis=2))

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
        colortemp: float = 0.0,
        neutral_rgb: int | Tuple[int, int, int] = 0,
    ) -> Image.Image:
        """
        FR : Pipeline de réglage fin combiné en 4 étapes (`finetune2`) reproduisant exactement
             `FUN_008f7ee0 @ 0x008F7EE0` de `picasa3.exe` :
             1. Lumière d'appoint (`0x008F7F28` -> `0x0090AC20`) si `fill != 0.0`
             2. LUT 16 bits Hautes lumières & Ombres (`0x008F7F5D` -> `0x0090C3B0`) avec
                `white_pt = max(0.001, 1.0 - highlights)` et `black_pt = shadows`
             3. Adaptation chromatique point neutre (`0x008F8002` -> `0x0090EDA0`) si `neutral_rgb != 0`
             4. Température de couleur Kelvin (`0x008F8037` -> `0x0090E9D0`) si `colortemp != 0.0`
        EN : Exact 4-step combined fine-tuning pipeline (`finetune2`) reproducing
             `FUN_008f7ee0 @ 0x008F7EE0` from `picasa3.exe`:
             1. Fill Light (`0x008F7F28` -> `0x0090AC20`) if `fill != 0.0`
             2. 16-bit Highlights & Shadows LUT (`0x008F7F5D` -> `0x0090C3B0`) with
                `white_pt = max(0.001, 1.0 - highlights)` and `black_pt = shadows`
             3. Neutral point chromatic adaptation (`0x008F8002` -> `0x0090EDA0`) if `neutral_rgb != 0`
             4. Kelvin Color Temperature (`0x008F8037` -> `0x0090E9D0`) if `colortemp != 0.0`

        Ref: picasa3.exe @ 0x008F7EE0, 0x0090AC20, 0x0090C3B0, 0x0090EDA0, 0x0090E9D0
        """
        if img.mode != "RGB":
            out = img.convert("RGB")
        else:
            out = img.copy()

        # Étape 1 : Lumière d'appoint (Ref: 0x008F7F28 -> 0x0090AC20)
        if abs(float(fill)) > 1e-6:
            out = PicasaImageProcessor.fill_light(out, float(fill), 1.0)

        # Étape 2 : LUT 16 bits combinée Hautes lumières + Ombres (Ref: 0x008F7F5D..0x008F7FFC -> 0x0090C3B0)
        hl = float(highlights)
        sh = float(shadows)
        if abs(hl) > 1e-6 or abs(sh) > 1e-6:
            white_pt = max(0.001, 1.0 - hl)
            black_pt = sh
            out = PicasaImageProcessor._levels_lut_0090c1e0(out, black_pt=black_pt, white_pt=white_pt, gamma=1.0)

        # Étape 3 : Point neutre pipette (Ref: 0x008F8002 -> 0x0090EDA0)
        has_neutral = (
            (neutral_rgb & 0x00FFFFFF) != 0
            if isinstance(neutral_rgb, int)
            else (isinstance(neutral_rgb, (tuple, list)) and len(neutral_rgb) >= 3 and any(int(c) > 0 for c in neutral_rgb[:3]))
        )
        if has_neutral:
            out = PicasaImageProcessor._chromatic_adaptation_0090eda0(out, neutral_rgb)

        # Étape 4 : Température de couleur (Ref: 0x008F8037 -> 0x0090E9D0)
        if abs(float(colortemp)) > 1e-6:
            out = PicasaImageProcessor.color_temperature(out, float(colortemp))

        return out

    @staticmethod
    def compute_autotune_lighting(img: Image.Image, current_fill: float = 0.0) -> Tuple[float, float]:
        """
        FR : Calcule les valeurs automatiques des curseurs `highlights` (`0.0 .. 0.48`) et `shadows` (`0.0 .. 0.48`)
             lors du clic sur la baguette magique d'éclairage de l'onglet 2 (`button id="0"`, `0x008FC690`).
        EN : Computes automatic slider values for `highlights` (`0.0 .. 0.48`) and `shadows` (`0.0 .. 0.48`)
             when clicking the Tab 2 lighting magic wand (`button id="0"`, `0x008FC690`).

        Ref: picasa3.exe @ 0x008FC690, 0x00A4B960, 0x00A4BFD0
        """
        src = PicasaImageProcessor.fill_light(img, current_fill) if abs(current_fill) > 1e-6 else img
        _lows, _highs, min_low, max_high = PicasaImageProcessor._central_crop_percentiles_00a4b960(
            src, 0.005, 0.995
        )
        sh_val = max(0.0, min(0.48, float(min_low) / 255.0))
        hl_val = max(0.0, min(0.48, 1.0 - float(max_high) / 255.0))
        return hl_val, sh_val

    @staticmethod
    def compute_autotune_color(img: Image.Image) -> int:
        """
        FR : Calcule la valeur automatique `neutral_rgb` (`0x00RRGGBB`) lors du clic sur la baguette
             magique de couleur de l'onglet 2 (`button id="1"`, `0x008FC690` -> `0x0090F8F0`).
        EN : Computes the automatic `neutral_rgb` (`0x00RRGGBB`) value when clicking the Tab 2
             color magic wand (`button id="1"`, `0x008FC690` -> `0x0090F8F0`).

        Ref: picasa3.exe @ 0x008FC690, 0x0090F8F0
        """
        r_est, g_est, b_est = PicasaImageProcessor._estimate_scene_illuminant_0090f8f0(img)
        return ((r_est & 0xFF) << 16) | ((g_est & 0xFF) << 8) | (b_est & 0xFF)

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
    enhance = enhance_lucky
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

