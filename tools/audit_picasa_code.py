"""FR: Script d'audit comparant les fonctionnalités, méthodes, classes et filtres de Picasa 3 original avec l'implémentation PyCasa.
EN: Audit script comparing original Picasa3 features, methods, classes, and filters against the PyCasa implementation.
"""
import sys
sys.path.insert(0, ".")
import re
import os

# 1. Parse filterdesc.xml
xml_path = r"C:\Program Files (x86)\Google\Picasa3\runtime\filterdesc.xml"
filters = []
if os.path.exists(xml_path):
    with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    pattern = re.compile(r'<filter\s+([^>]+)>')
    for m in pattern.finditer(content):
        attrs = dict(re.findall(r'(\w+)=["\']([^"\']*)["\']', m.group(1)))
        filters.append(attrs)

from picasa_py.ui.image_processor import PicasaImageProcessor
ip_methods = set(dir(PicasaImageProcessor))

print("=== 1. FILTERS AUDIT (filterdesc.xml vs PicasaImageProcessor) ===")
print(f"Total filters defined in Picasa 3 runtime: {len(filters)}")

# Mapping from filter ID to expected python method name
filter_map = {
    'save': 'save_history',
    'crop64': 'crop64',
    'crop': 'crop',
    'picnik': 'picnik_history',
    'rot': 'rotate',
    'debug': 'debug_filter',
    'triple': 'triple',
    'triple2': 'triple2',
    'triple3': 'triple3',
    'finetune': 'finetune',
    'finetune2': 'finetune2',
    'colorfix': 'auto_color',
    'autobacklight': 'backlight_fix',
    'autolight': 'auto_contrast',
    'bw': 'black_and_white',
    'enhance': 'auto_contrast',
    'warm': 'warmify',
    'grain': 'film_grain',
    'grain2': 'film_grain',
    'unsharp': 'sharpen',
    'unsharp2': 'sharpen',
    'tilt': 'straighten',
    'rainbow': 'rainbow',
    'radblur': 'soft_focus',
    'radsat': 'focal_bw',
    'linblur': 'linear_blur',
    'ansel': 'filtered_bw',
    'dir_tint': 'graduated_tint',
    'radtint': 'radial_tint',
    'glow2': 'glow',
    'sat': 'saturation',
    'shadow': 'adjust_shadows',
    'blur': 'gaussian_blur',
    'contrast': 'adjust_contrast',
    'gamma': 'gamma_correct',
    'backlight': 'backlight_fix',
    'fill': 'fill_light',
    'whitept': 'neutral_color_balance',
    'dir_sat': 'directional_saturation',
    'dir_brite': 'directional_brightness',
    'dir_sharp': 'directional_sharpen',
    'focalpixelate': 'focal_pixelate',
    'comicize': 'comic',
    'dropshadow': 'drop_shadow',
    'picnikfocalpixelate': 'focal_pixelate',
    'picnikgrain': 'film_grain',
    'hdr': 'hdr_simulator',
    'ir': 'infrared',
    'localcontrast': 'local_contrast',
    'matte': 'matte',
    'museummatte': 'museum_matte',
    'quantizepalette': 'quantize_palette',
    'reanimatedeyecolor': 'reanimated_eye_color',
    'roundededges': 'rounded_edges',
    'sixties': 'sixties',
    'picniktint': 'tint',
    'twotone': 'two_tone',
    'moviestart': 'movie_trim',
    'movieend': 'movie_trim',
    'straighten': 'straighten',
    'redeye': 'remove_red_eye',
    'autocolor': 'auto_color',
    'autocontrast': 'auto_contrast',
    'lucky': 'auto_contrast',
    'filllight': 'fill_light',
    'highlights': 'adjust_highlights',
    'shadows': 'adjust_shadows',
    'colortemp': 'color_temperature',
    'neutralcolor': 'neutral_color_picker',
    'sharpen': 'sharpen',
    'sepia': 'sepia',
    'blackwhite': 'black_and_white',
    'warmify': 'warmify',
    'filmgrain': 'film_grain',
    'tint': 'tint',
    'saturation': 'saturation',
    'softfocus': 'soft_focus',
    'glow': 'glow',
    'focalbw': 'focal_bw',
    'graduatedtint': 'graduated_tint',
    'vignette': 'vignette',
    'infrared': 'infrared',
    'lomo': 'lomo',
    'holga': 'holga',
    'hdrish': 'hdr_simulator',
    'cinemascope': 'cinemascope',
    'orton': 'orton',
    '1960s': 'sixties',
    'invert': 'invert',
    'heatmap': 'heat_map',
    'nightvision': 'night_vision',
    'crossprocess': 'cross_process',
    'posterize': 'quantize_palette',
    'duotone': 'two_tone',
    'boost': 'boost',
    'soften': 'soften',
    'pixelate': 'pixelate',
    'focalzoom': 'focal_zoom',
    'pencilsketch': 'pencil_sketch',
    'neon': 'neon',
    'comicbook': 'comic',
    'border': 'border',
    'polaroid': 'polaroid',
    'text': 'add_text',
    'retouch': 'retouch_heal'
}

missing_filters = []
present_filters = []
for f in filters:
    fid = f.get('id', '')
    cat = f.get('category', '')
    ini = f.get('picasaini', '')
    py_func = filter_map.get(fid.lower())
    if py_func and hasattr(PicasaImageProcessor, py_func):
        present_filters.append((fid, cat, ini, py_func))
    else:
        missing_filters.append((fid, cat, ini, py_func))

print(f"Filters implemented in PyCasa: {len(present_filters)} / {len(filters)}")
print(f"Filters missing in PyCasa: {len(missing_filters)}")
if missing_filters:
    print("\nMissing Filters:")
    for fid, cat, ini, py_func in missing_filters:
        print(f"  - {fid:20} (cat={cat:12}, ini={ini:15}) -> expected: {py_func}")

# 2. Check Dialogs
print("\n=== 2. DIALOGS AUDIT ===")
picasa_py_dialogs = [
    'FolderManagerDialog', 'OptionsDialog', 'ExportDialog', 'WebExportDialog',
    'PosterDialog', 'PrintDialog', 'ContactManagerDialog', 'MoveDatabaseDialog',
    'OffsetTimeDialog', 'RenameDialog', 'ImagePropertiesDialog', 'NameFaceDialog',
    'AlbumDialog', 'EmailDialog', 'ImportDialog'
]
import picasa_py.ui
py_ui_files = os.listdir('picasa_py/ui')
print(f"UI Dialog files in picasa_py/ui: {[f for f in py_ui_files if 'dialog' in f]}")

# 3. Check Menu Actions & Commands
with open("bin/picasa3.exe", "rb") as f:
    exe_data = f.read()

menu_ids = sorted(set(re.findall(rb'ID_[A-Z0-9_]+', exe_data)))
menu_ids = [m.decode('latin1') for m in menu_ids]

with open("picasa_py/ui/menu.py", "r", encoding="utf-8") as f:
    menu_py_text = f.read()
with open("picasa_py/ui/main_window.py", "r", encoding="utf-8") as f:
    mw_py_text = f.read()

print(f"\nTotal command IDs in picasa3.exe: {len(menu_ids)}")

# 4. Check Key Subsystems
print("\n=== 3. KEY SUBSYSTEMS COMPARISON ===")
subsystems = {
    "Two-Up / Side-by-side Before-After": "TwoUpView" in mw_py_text or "two_up" in mw_py_text,
    "Copy / Paste All Effects": "copy_effects" in mw_py_text or "COPYALLEFFECTS" in menu_py_text,
    "Save to Disk (.picasaoriginals backup)": "originals" in mw_py_text.lower(),
    "Neutral Color Picker (Eyedropper)": hasattr(PicasaImageProcessor, "pick_neutral_color"),
    "Make Movie (Ken Burns / Audio sync)": os.path.exists("picasa_py/ui/make_movie.py"),
    "Face Movie (CMakeFaceMoviePanel)": os.path.exists("picasa_py/ui/face_movie.py"),
    "Batch Write Face Tags to XMP": hasattr(picasa_py.ui, "WriteAllFacetagsDialog") or "write_all_facetags" in mw_py_text,
    "Contact Sheet Print": "contact_sheet" in mw_py_text or "CONTACTSHEET" in menu_py_text,
    "Batch Date/Time Adjuster": "offset_time" in mw_py_text,
    "Batch Rename": "rename_dialog" in mw_py_text or "RenameDialog" in mw_py_text,
    "Move Database": "move_database" in mw_py_text,
    "Set Face as Album Cover": "set_album_cover" in mw_py_text or "SETPEOPLEALBUMCOVER" in menu_py_text,
    "Password Protect Collection": "password" in mw_py_text.lower(),
    "Google Earth Geotagging (KML)": "kml" in mw_py_text.lower(),
    "CD/DVD Backup Burn": "burn" in mw_py_text.lower() or "backup" in mw_py_text.lower(),
}

for sub, status in subsystems.items():
    print(f"  [{'PRESENT' if status else 'MISSING':7}] {sub}")
