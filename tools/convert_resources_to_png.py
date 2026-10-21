#!/usr/bin/env python3
"""
FR: Convertit et extrait toutes les ressources graphiques de PyCasa (`.ico`, `.cur`, `.gif`,
    ainsi que les icônes d'étoile et de bascule 2-Up de `respack.yt`) en fichiers `.png` RGBA 32 bits
    dans `ui/resources/icons/`, `ui/resources/cursors/` et `ui/resources/geotag/`.
    Les fichiers `.ico` et `.cur` originaux sont préservés conformément à `AGENTS.md §4 bis.2`,
    tandis que `PicasaResourceManager` charge désormais prioritairement les fichiers `.png`,
    permettant de modifier ou remplacer n'importe quelle icône avec un simple éditeur d'image.

EN: Converts and extracts all PyCasa graphical resources (`.ico`, `.cur`, `.gif`,
    as well as star and 2-Up toggle icons from `respack.yt`) into 32-bit RGBA `.png` files
    under `ui/resources/icons/`, `ui/resources/cursors/`, and `ui/resources/geotag/`.
    Original `.ico` and `.cur` files are preserved per `AGENTS.md §4 bis.2`,
    while `PicasaResourceManager` loads `.png` files first so any icon can be updated
    with a standard image editor.

Ref: picasa3.exe @ 0x009838D0 (PE Icons & Cursors), runtime/respack.yt (PNG layers)
"""

from __future__ import annotations

import io
import json
import math
import struct
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RES_DIR = PROJECT_ROOT / "ui" / "resources"
ICONS_DIR = RES_DIR / "icons"
CURSORS_DIR = RES_DIR / "cursors"
GEOTAG_DIR = RES_DIR / "geotag"


def _decode_ico_or_cur_entry_to_rgba(raw_bytes: bytes, offset: int, size: int, width: int, height: int) -> Image.Image:
    """
    FR: Décode une entrée d'image issue d'un conteneur `.ico` ou `.cur` (PNG embarqué ou DIB BITMAPINFOHEADER
        avec masque XOR + masque AND 1-bit) en image PIL RGBA 32 bits.
    EN: Decodes an image entry from an `.ico` or `.cur` container (embedded PNG or BITMAPINFOHEADER DIB
        with XOR + 1-bit AND mask) into a 32-bit RGBA PIL Image.
    """
    blob = raw_bytes[offset : offset + size]
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return Image.open(io.BytesIO(blob)).convert("RGBA")

    # Lecture de l'en-tête BITMAPINFOHEADER (40 octets)
    if len(blob) < 40:
        raise ValueError("Invalid DIB header size")
    bi_size, bi_w, bi_h, bi_planes, bi_bitcount, bi_comp, bi_size_img = struct.unpack_from("<IiiHHII", blob, 0)
    w = width if width > 0 else bi_w
    h = height if height > 0 else abs(bi_h) // 2

    if bi_bitcount == 32:
        pixel_offset = bi_size
        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            src_y = (h - 1 - y) if bi_h > 0 else y
            row_off = pixel_offset + src_y * w * 4
            for x in range(w):
                b, g, r, a = struct.unpack_from("<BBBB", blob, row_off + x * 4)
                px[x, y] = (r, g, b, a)
        return img

    if bi_bitcount in (1, 4, 8):
        num_colors = 1 << bi_bitcount
        palette: List[Tuple[int, int, int]] = []
        pal_off = bi_size
        for c in range(num_colors):
            b, g, r, _ = struct.unpack_from("<BBBB", blob, pal_off + c * 4)
            palette.append((r, g, b))

        xor_off = pal_off + num_colors * 4
        xor_stride = ((w * bi_bitcount + 31) // 32) * 4
        and_off = xor_off + xor_stride * h
        and_stride = ((w + 31) // 32) * 4

        img = Image.new("RGBA", (w, h))
        px = img.load()
        for y in range(h):
            src_y = (h - 1 - y) if bi_h > 0 else y
            x_row = blob[xor_off + src_y * xor_stride : xor_off + (src_y + 1) * xor_stride]
            a_row = blob[and_off + src_y * and_stride : and_off + (src_y + 1) * and_stride]
            for x in range(w):
                if bi_bitcount == 1:
                    c_idx = (x_row[x // 8] >> (7 - (x % 8))) & 1
                elif bi_bitcount == 4:
                    byte_val = x_row[x // 2]
                    c_idx = (byte_val >> 4) & 0x0F if (x % 2 == 0) else (byte_val & 0x0F)
                else:
                    c_idx = x_row[x]
                and_bit = (a_row[x // 8] >> (7 - (x % 8))) & 1 if len(a_row) > (x // 8) else 0
                r, g, b = palette[c_idx] if c_idx < len(palette) else (0, 0, 0)
                if and_bit == 1 and c_idx == 0:
                    # Transparent
                    px[x, y] = (0, 0, 0, 0)
                elif and_bit == 1 and c_idx != 0:
                    # Pixel inversé (XOR cursor) -> rendu blanc avec contour visible
                    px[x, y] = (255, 255, 255, 255)
                else:
                    px[x, y] = (r, g, b, 255)
        return img

    # Repli via Pillow
    return Image.open(io.BytesIO(raw_bytes)).convert("RGBA")


def convert_all_ico_files() -> Dict[str, dict]:
    """
    FR: Convertit tous les fichiers `group_icon_*.ico` de `ui/resources/icons/` en `.png`.
        Pour chaque groupe d'icônes, extrait la meilleure profondeur de couleur (bpp) par taille
        sous `group_icon_<id>_<w>x<h>.png` ainsi que l'image principale `group_icon_<id>.png`.
    EN: Converts all `group_icon_*.ico` files in `ui/resources/icons/` to `.png`.
        For each icon group, extracts the highest bit-depth (bpp) per size as
        `group_icon_<id>_<w>x<h>.png` as well as the primary image `group_icon_<id>.png`.
    """
    manifest_icons: Dict[str, dict] = {}
    for ico_path in sorted(ICONS_DIR.glob("group_icon_*.ico")):
        raw = ico_path.read_bytes()
        if len(raw) < 6:
            continue
        _reserved, _type, count = struct.unpack_from("<HHH", raw, 0)
        best_by_size: Dict[Tuple[int, int], Tuple[int, Image.Image]] = {}
        for i in range(count):
            b_w, b_h, b_colors, _res, planes, bpp, bytes_in_res, img_off = struct.unpack_from(
                "<BBBBHHII", raw, 6 + i * 16
            )
            w = 256 if b_w == 0 else b_w
            h = 256 if b_h == 0 else b_h
            # Si le bloc est un PNG, il est en 32 bpp
            if raw[img_off : img_off + 8] == b"\x89PNG\r\n\x1a\n":
                eff_bpp = 32
            elif bpp > 0:
                eff_bpp = bpp
            elif len(raw) >= img_off + 16:
                eff_bpp = struct.unpack_from("<H", raw, img_off + 14)[0]
            else:
                eff_bpp = 8

            rgba = _decode_ico_or_cur_entry_to_rgba(raw, img_off, bytes_in_res, w, h)
            prev = best_by_size.get((w, h))
            if prev is None or eff_bpp >= prev[0]:
                best_by_size[(w, h)] = (eff_bpp, rgba)

        if not best_by_size:
            continue

        stem = ico_path.stem  # ex: group_icon_105
        gid = stem.replace("group_icon_", "")
        size_files: Dict[str, str] = {}
        # Sauvegarder chaque taille et choisir la plus grande comme `group_icon_<id>.png`
        sorted_sizes = sorted(best_by_size.keys(), key=lambda wh: (wh[0] * wh[1]))
        for (w, h) in sorted_sizes:
            _, img_rgba = best_by_size[(w, h)]
            if len(sorted_sizes) > 1:
                sz_name = f"{stem}_{w}x{h}.png"
                img_rgba.save(ICONS_DIR / sz_name, format="PNG")
                size_files[f"{w}x{h}"] = sz_name

        largest_wh = sorted_sizes[-1]
        primary_img = best_by_size[largest_wh][1]
        primary_name = f"{stem}.png"
        primary_img.save(ICONS_DIR / primary_name, format="PNG")
        size_files[f"{largest_wh[0]}x{largest_wh[1]}"] = size_files.get(
            f"{largest_wh[0]}x{largest_wh[1]}", primary_name
        )

        manifest_icons[gid] = {
            "png_file": primary_name,
            "ico_file": ico_path.name,
            "sizes": size_files,
        }
    return manifest_icons


def convert_all_cur_files() -> Dict[str, dict]:
    """
    FR: Convertit tous les curseurs `cursor_*.cur` de `ui/resources/cursors/` en `cursor_*.png` RGBA
        et met à jour `cursors.json` avec la clé `"png_file"`.
    EN: Converts all `cursor_*.cur` files in `ui/resources/cursors/` to RGBA `cursor_*.png`
        and updates `cursors.json` with the `"png_file"` key.
    """
    manifest_path = CURSORS_DIR / "cursors.json"
    manifest: Dict[str, dict] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for cur_path in sorted(CURSORS_DIR.glob("cursor_*.cur")):
        raw = cur_path.read_bytes()
        if len(raw) < 22:
            continue
        _reserved, _type, count = struct.unpack_from("<HHH", raw, 0)
        if count < 1:
            continue
        b_w, b_h, _b_colors, _res, hx, hy, bytes_in_res, img_off = struct.unpack_from("<BBBBHHII", raw, 6)
        w = 256 if b_w == 0 else b_w
        h = 256 if b_h == 0 else b_h
        rgba = _decode_ico_or_cur_entry_to_rgba(raw, img_off, bytes_in_res, w, h)
        png_name = f"{cur_path.stem}.png"
        rgba.save(CURSORS_DIR / png_name, format="PNG")

        cid = cur_path.stem.replace("cursor_", "")
        entry = manifest.get(cid, {})
        entry["file"] = cur_path.name
        entry["png_file"] = png_name
        entry.setdefault("hotspot_x", hx)
        entry.setdefault("hotspot_y", hy)
        entry["width"] = w
        entry["height"] = h
        manifest[cid] = entry

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def ensure_special_ui_pngs() -> None:
    """
    FR: Génère les fichiers `.png` pour les icônes qui étaient encore dessinées en code Python
        (`star_icon.png`, `editpanel_swap_2up_layout_horiz_icon.png`) et convertit `geotag/close.gif`
        en `geotag/close.png`.
    EN: Generates `.png` files for icons that were previously drawn procedurally in Python
        (`star_icon.png`, `editpanel_swap_2up_layout_horiz_icon.png`) and converts `geotag/close.gif`
        to `geotag/close.png`.
    """
    # 1. Étoile dorée Picasa (`star_icon.png` en 64x64 haute définition)
    star_png = ICONS_DIR / "star_icon.png"
    if not star_png.exists():
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size / 2.0, size / 2.0
        r_out = (size / 2.0) - 4.0
        r_in = r_out * 0.42
        pts = []
        for si in range(10):
            angle = si * math.pi / 5.0 - math.pi / 2.0
            r = r_out if si % 2 == 0 else r_in
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(pts, fill=(255, 215, 0, 255), outline=(184, 134, 11, 255), width=2)
        img.save(star_png, format="PNG")

    # 2. Icône de division horizontale 2-Up (`editpanel_swap_2up_layout_horiz_icon.png`)
    #    obtenue par rotation 90° de l'icône officielle `editpanel_swap_2up_layout_icon.png`
    vert_png = ICONS_DIR / "editpanel_swap_2up_layout_icon.png"
    horiz_png = ICONS_DIR / "editpanel_swap_2up_layout_horiz_icon.png"
    if vert_png.exists() and not horiz_png.exists():
        with Image.open(vert_png) as v_im:
            h_im = v_im.convert("RGBA").transpose(Image.Transpose.ROTATE_90)
            h_im.save(horiz_png, format="PNG")

    # 3. Conversion de `ui/resources/geotag/close.gif` en `close.png`
    close_gif = GEOTAG_DIR / "close.gif"
    close_png = GEOTAG_DIR / "close.png"
    if close_gif.exists() and not close_png.exists():
        with Image.open(close_gif) as g_im:
            g_im.convert("RGBA").save(close_png, format="PNG")


def main() -> int:
    """
    FR: Exécute la conversion complète de toutes les ressources en `.png` et met à jour les manifestes JSON.
    EN: Runs the full conversion of all resources into `.png` and updates JSON manifests.
    """
    ico_manifest = convert_all_ico_files()
    cur_manifest = convert_all_cur_files()
    ensure_special_ui_pngs()

    all_pngs = sorted(p.name for p in ICONS_DIR.glob("*.png"))
    manifest_out = {
        "group_icons": ico_manifest,
        "ui_icons_png": all_pngs,
    }
    (ICONS_DIR / "icons_png_manifest.json").write_text(
        json.dumps(manifest_out, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] Converted {len(ico_manifest)} icon groups and {len(cur_manifest)} cursors to PNG.")
    print(f"[OK] Total PNG icons in ui/resources/icons/: {len(all_pngs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
