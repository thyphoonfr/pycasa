# Public Test Photos / Photos publiques de test (`tests/fixtures/photos/`)

## 🇬🇧 English

All core unit, round-trip, UI, and face-engine tests in **PyCasa** run **100% out-of-the-box** using the binary fixtures in `tests/fixtures/db/`, `tests/fixtures/ini/`, and dynamically generated synthetic images.

If you wish to add **real public-domain / Creative Commons test photos** (in strict compliance with `AGENTS.md` §9.9 — never commit personal photos), place them in this directory (`tests/fixtures/photos/`):

| Recommended Filename | Purpose |
|---|---|
| `sample_portrait_face.jpg` | Real human face(s) to test end-to-end `Red.dll` / `PurePythonRedEngine` multi-angle detection and 1,044-byte `vqc_Cue` extraction on real photography. |
| `sample_exif_gps.jpg` | Photo containing camera EXIF metadata (`Make`, `Model`, `DateTimeOriginal`, `Orientation`, and `GPSLatitude` / `GPSLongitude`) for EXIF & Places map tests. |
| `sample_landscape.jpg` | High-contrast color photo for visual verification of the 84 non-destructive Picasa / Picnik filters. |

---

## 🇫🇷 Français

Tous les tests unitaires, round-trip binaires, UI et moteur de visages de **PyCasa** fonctionnent **à 100 % de manière autonome** grâce aux fixtures binaires (`tests/fixtures/db/`, `tests/fixtures/ini/`) et aux images synthétiques générées à la volée.

Si vous souhaitez ajouter de **vraies photos publiques** (domaine public / Creative Commons, conformément à `AGENTS.md` §9.9 qui interdit toute photo personnelle sur un dépôt public), placez-les dans ce dossier (`tests/fixtures/photos/`) :

| Nom de fichier recommandé | Utilité |
|---|---|
| `sample_portrait_face.jpg` | Photo avec 1 ou plusieurs visages réels pour tester de bout en bout la détection multi-angles `Red.dll` / `PurePythonRedEngine` et l'extraction de signatures `vqc_Cue` (1 044 octets). |
| `sample_exif_gps.jpg` | Photo contenant des métadonnées EXIF complètes (`Make`, `Model`, `DateTimeOriginal`, `Orientation` et coordonnées `GPS`) pour les tests EXIF et carte « Lieux ». |
| `sample_landscape.jpg` | Photo couleur contrastée pour la validation visuelle des 84 filtres non destructifs Picasa / Picnik. |
