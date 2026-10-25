# Points non résolus et questions ouvertes

Ce document consigne toutes les questions, hypothèses et points de doute conformément au §8 de `AGENTS.md`.

---

## 1. Format INI (`.picasa.ini` / `Picasa.ini`)
*Statut : Résolu & validé par tests round-trip bit-exact.*

- [x] Localisation exacte des fonctions de parsing et de sérialisation INI dans `Picasa3.exe` :
  - Writer : `FUN_0068ac80` @ `0x0068AC80` - `0x0068C412`.
  - Reader/Parser : `FUN_009be730` @ `0x009BE730`, `FUN_009bd390` @ `0x009BD390`.
- [x] Encodage exact : UTF-8 sans BOM, fins de ligne strictly CRLF (`\r\n`).
- [x] Comportement en lecture : recherche de section délimitée par `[` et `]`, recherche de clé suivie de `=`, comparaison insensible à la casse ASCII (+0x20).
- [x] Préservation intégrale des lignes inconnues, commentaires et espacements lors du round-trip.

---

## 2. Format PMP (`.pmp` - Base de données colonne)
*Statut : Résolu & validé par tests round-trip bit-exact.*

- [x] Localisation dans le binaire : `CPropertyMap` (`.\thumblab\CPropertyMap.cpp` @ `0x00CA8104`), `FUN_006a2b60`, `FUN_006d17f0`.
- [x] Structure de l'en-tête (20 octets) :
  - `magic` = `0x3FCCCCCD` (float 1.6f).
  - `type_id` = `0x13320000 | type_enum`.
  - `subversion` = `0x00000002`.
  - `type_id_repeat` = `type_id`.
  - `record_count` = nombre de lignes.
- [x] Types de données identifiés et validés (0x0000 à 0x0007).
- [x] Validé à 100% sur l'intégralité des 56 fichiers réels de `AppData/Local/Google/Picasa2/db3`.

---

## 3. Format `thumbindex.db` (Arborescence et fichiers surveillés)
*Statut : Résolu & validé par tests round-trip bit-exact.*

- [x] Localisation dans le binaire :
  - Writer : `picasa3.exe @ 0x004F54B0` (`FUN_004f54b0`).
  - Reader : `picasa3.exe @ 0x004F25F0` (`FUN_004f25f0`).
  - Magic : `0x40466666` (float 3.1f stocké à `0x00CF4F4C`).
- [x] Structure de l'en-tête (8 octets) : `magic (uint32)`, `record_count (uint32)`.
- [x] Structure d'un enregistrement : `path\0` + 30 octets fixes (`ft1:uint64`, `ft2:uint64`, `size:uint32`, `type:uint32`, `flags:uint16`, `parent_idx:uint32`).
- [x] Validé à 100% sur le fichier réel `thumbindex.db` (274 542 octets, 4 670 enregistrements).

---

## 4. Format `CBlockFile` (`*_0.db` et `*_index.db` - Conteneurs et index de miniatures)
*Statut : Résolu & validé par tests round-trip bit-exact.*

- [x] Localisation dans le binaire :
  - Source C++ : `.\thumblab\CBlockFile.cpp` @ `0x00CA847C`, `0x00CA8487`.
  - SaveIndex : `picasa3.exe @ 0x006B7FC0`.
  - ReadIndex : `picasa3.exe @ 0x006B82E0`.
  - WriteEntry : `picasa3.exe @ 0x006B75F0`.
  - Magic : `0x3FCCCCCD` (float 1.6f).
- [x] Structure de l'index (`*_index.db`) :
  - En-tête (8 octets) : `magic (uint32)`, `active_block (uint32)`.
  - 3 vecteurs colonnes séquentiels de taille identique :
    1. Checksums : `count (uint32)` + `count * uint32`.
    2. Offsets : `count (uint32)` + `count * uint32`.
    3. Sizes & Blocks : `count (uint32)` + `count * uint32` (bits 0..23 = taille, bits 24..31 = n° bloc).
- [x] Structure des conteneurs (`*_0.db`) : en-tête 4 octets `0x3FCCCCCD`, puis concaténation des blobs (images JPEG authentiques vérifiées de `0xFFD8` à `0xFFD9`).
- [x] Validé à 100% sur l'ensemble des 6 bases d'index et sur `thumbs_0.db` (20 Mo).

---

## 5. Format Key-Value Table (`repository.dat`, `usernames.dat`)
*Statut : Résolu & validé par tests round-trip bit-exact.*

- [x] Localisation dans le binaire : `picasa3.exe @ 0x0041415A`, `0x00416652`, vtable `0x00C827F8`.
- [x] Structure : `magic (uint32 = 0x3FCCCCCD)`, `pair_count (uint32)`, suivi de `pair_count` paires de chaînes `key\0` et `value\0`.
- [x] Validé à 100% sur les fichiers réels.

---

## 6. Format `wordhash.dat` (Index inversé de recherche plein texte)
*Statut : Résolu & validé par tests round-trip bit-exact.*

- [x] Localisation dans le binaire : `picasa3.exe @ 0x004DB4F0`, `0x004DB720`, `0x00704500`, `0x007046E0`, `0x00A61700`.
- [x] Structure :
  - En-tête : `magic (0x3FCCCCCD)`, `max_doc_id (uint32)`.
  - String pool : `chunk_count`, `chunk_size`, `used_bytes`, puis les blocs du pool.
  - Table inversée : `word_count`, puis pour chaque mot : `str_offset: uint32`, `count: uint32`, `items: count * uint32`.
- [x] Validé à 100% sur le fichier réel `wordhash.dat` (226 860 octets, 4 263 entrées).

---

## 7. Format `contacts.xml` (Annuaire et visages)
*Statut : Résolu & validé par tests round-trip.*

- [x] XML UTF-8 sous `<contacts>` avec éléments `<contact id="..." name="..." modified_time="..." local_contact="1"/>`.
- [x] Les IDs correspondent exactement aux IDs référencés dans `picasa.ini` (`faces=rect64(...),<contact_id>`).

---

---

## 8. Ressources PE et Définition d'Interface (`Picasa3.exe`, `Picasa3i18n.dll`, `runtime/`)
*Statut : Résolu & validé par tests unitaires.*

- [x] Extraction de l'intégralité des ressources PE via `pefile` :
  - 11 groupes d'icônes (`RT_GROUP_ICON` / `RT_ICON`) exportés en fichiers `.ico` valides, dont l'icône principale `group_icon_105.ico` (256x256).
  - 12 curseurs (`RT_GROUP_CURSOR` / `RT_CURSOR`) exportés en `.cur` avec leurs points chauds originaux respectés (loupe, crop, pipette, yeux rouges, etc.).
  - 265 chaînes extraites de `RT_STRING` vers `strings.json`.
  - 13 dialogues bruts `RT_DIALOG`.
  - Manifeste d'application `picasa.manifest`.
- [x] Extraction des ressources d'internationalisation :
  - 3 084 fichiers XML extraits de `Picasa3i18n.dll` (type `XMLF`), dont `SHORTCUTS.XML`.
- [x] Définitions de gabarits d'interface :
  - 47 fichiers `.fen` (XML de mise en page Picasa).
  - Métriques et styles `constants.ui` (`alist_*`, `alabel_*`, `alayout_*`, `thumbsel_*`).
- [x] Structure de menu interne :
  - Table binaire `eMenu*` mappée à `0x0088C3EC` (167 entrées structurées avec libellés et raccourcis).

---

## 9. Fenêtre Principale et Architecture UI (`ytWindow`)
*Statut : Résolu & implémenté dans `picasa_py/ui/`.*

- [x] Identification de la classe de fenêtre principale :
  - Nom Win32 : `ytWindow` (`picasa3.exe @ 0x00C7F35C`).
  - Procédure de fenêtre : `picasa3.exe @ 0x00983940`.
  - Enregistrement : `0x009838D0` (Style `0x400B`, `cbWndExtra=4`).
  - Signature d'instance : `0x47506332` (`GPc2`) dans `GetWindowLong(hwnd, 0)`.
- [x] Choix du Toolkit : **PySide6** justifié dans `docs/ui/toolkit.md` (rendu `QPainter` custom pixel-exact, virtual scrolling 60 FPS).
- [x] Architecture modulaire implémentée dans `picasa_py/ui/` :
  - `style.py` : styles et métriques issus de `constants.ui`.
  - `resources.py` : gestionnaire d'icônes, curseurs et textes.
  - `menu.py` : constructeur des menus et raccourcis clavier.
  - `top_bar.py` : barre d'outils, bouton Import, filtres rapides et recherche.
  - `library_tree.py` : volet de navigation gauche connecté à `PicasaDatabase`.
  - `thumbnail_view.py` : grille de vignettes virtuelle optimisée (60 FPS, sélection bicolore, zoom slider).
  - `photo_tray.py` : bac inférieur caractéristique avec boutons d'action.
  - `right_drawer.py` : volet escamotable d'informations EXIF et balises.
  - `main_window.py` : fenêtre principale `PicasaMainWindow`.
  - `app.py` : point d'entrée exécutable.
- [x] Respect de l'isolation : aucune écriture directe de l'UI vers la base ; passage obligatoire par `picasa_py/db/` et `picasa_py/ini/`.

---

## 10. Mode Éditeur Plein Écran (« One-Up View »)
*Statut : Résolu & validé par tests unitaires.*

- [x] Identification des structures du visualiseur :
  - Identifiants binaire : `OneUp`, `AVOneUpUI`, `editoneup`.
  - Spécification : `ONEUPTEXT.XML`, `filterdesc.xml`.
- [x] Implémentation complète dans `picasa_py/ui/` :
  - `image_canvas.py` : Affichage haute résolution, zoom centré, panoramique fluide avec curseur main (`cursor_7.cur`), rotations 90°.
  - `edit_panel.py` : Volet latéral de retouche avec bouton « Revenir à la bibliothèque », Annuler/Rétablir et onglets (Retouches de base, Lumière et couleur, Effets).
  - `image_processor.py` : Moteur de filtres matriciels exécutant Contraste auto, Couleur auto, N&B, Sépia, Warmify, Lumière d'appoint, Netteté et Grain photo.
  - `one_up_view.py` : Orchestrateur assemblant panneau d'édition, canvas et barre de transport (navigation Précédente / Suivante, rotations, zoom).
  - Intégration dans `main_window.py` via `QStackedWidget` pour bascule transparente au double-clic et retour par `Échap` / bouton.

---

## 11. Phases Complémentaires Résolues
- [x] Phase 6 : Mesures de performances, profilage et benchmarks comparatifs (`docs/perf/targets.md`, `benchmarks/test_perf_benchmarks.py`, incluant le benchmark à l'échelle 100 000 entrées).
- [x] Phase 7 : Moteur de scan de dossiers incrémental (`directory_scanner.py`) & Gestionnaire de dossiers (`folder_manager.py`, `FOLDERMGR_TEXT.XML`).
- [x] Phase 8 : Implémentation des 84 filtres de `filterdesc.xml` dans `PicasaImageProcessor` et des 15 sous-systèmes clés audités par `tools/audit_picasa_code.py` (`make_movie.py`, `face_movie.py`, `xmp_tagger.py`, `preferences.py`, etc.).
- [x] Phase 9 : Désassemblage et implémentation exacte des checksums `CBlockFile` (`picasa_py/db/blockfile.py`, validés à 100 % sur l'ensemble des fichiers `db3/*_index.db` réels) :
  - `thumbs_index.db` / `thumbs2_index.db` (`picasa3.exe @ 0x006B99F0` `full_hash=1` / `0x004E3AB0`) : hash des 32 bits bas de `ft2`, `size`, `filters` (`imagedata_filters.pmp`) et `crop64` (`imagedata_crop64.pmp`), avec résolution vers le parent (`parent_idx`) pour les entrées visage (`type == 1001`, `0x004E3B87`).
  - `bigthumbs_index.db` / `previews_index.db` (`picasa3.exe @ 0x006B9B26` `full_hash=0` / `0x0042AD1E`) : hash de `ft2` arrondi à la paire de secondes (division entière 64 bits par `20 000 000` via multiplication magique `0xABCC77118461CEFD >> 47` à `0x006B9A6D`) combiné avec `(((flip * 4) ^ rotate_step) << 4)`.
  - `facetemplatesV2_index.db` (`picasa3.exe @ 0x0048050B`) : constante `checksum = 1`.
- [x] Phase 10 : Désassemblage de `plugins/Red.dll` + `plugins/red.cfg` et implémentation native 64 bits de `vqc_Cue` et `vqc_Relator` (`picasa_py/db/blockfile.py`, `picasa_py/db/database.py`, `picasa_py/faces/face_manager.py`) :
  - Format exact des enregistrements `facetemplatesV2_0.db` (1 044 octets = 261 `uint32` : `u[0]=1044`, `u[1]=0x00423002`, `u[3]=0x0044DD4D`, `u[4]=2000`, `u[5]=4`, `u[6]=8`, `u[7]=inv_norm`, `u[8]=image_stamp`, `u[9]=250`, `u[10]=checksum` tel que `sum(u[0..260]) & 0xFFFFFFFF == 0xFFFFFFFF`, `u[11..260]` = 2 000 nibbles 4 bits non signés `q` décodés en `2*q - 15`, `Red.dll @ 0x10102020`, `0x10102100`, `0x1003E510`). Validé à 100 % sur les 1 160 visages réels de `facetemplatesV2_0.db`.
  - Chargement des 2 000 poids `float32` et paramètres sigmoïdes (`13.5`, `0.45`) depuis `plugins/red.cfg` (`vqc_Relator` `0x00423003` à l'offset `0x2290A9`, `Red.dll @ 0x101005F0`, `0x10100A10`, `0x100FF050`).
- [x] Phase 11 : Implémentation exacte du critère de chevauchement des rectangles de visages (`picasa3.exe @ 0x0092C2F0` : `inter_area / min(area1, area2)`) et du filtrage de répertoires (`runtime/filters.txt` `DirectoryFilters` @ `0x00D0AD70`, `.picasaoriginals` @ `0x0085A0B0`, `frexclude=1` @ `0x00881690`).
- [x] Phase 12 : Suite complète de tests d'interopérabilité croisée automatisés (`tests/test_interop_db_ini.py`, `AGENTS.md` §7.2).

---

## 12. Points documentés `# TODO(unverified)` (`AGENTS.md` §8)

Conformément à la règle §8 de `AGENTS.md`, les points suivants disposent d'une implémentation fonctionnelle fidèle aux structures de données externes mais dont certains détails algorithmiques internes restent marqués `# TODO(unverified)` :

1. **Moteur de détection et d'extraction d'embedding pour les visages (`picasa_py/faces/detector.py`, `picasa_py/faces/red_engine_py.py`)** :
   - *Statut : Résolu à 100 %.*
   - Le moteur natif (`plugins/Red.dll` + `plugins/red.cfg` via `red_bridge_x86.exe`) ainsi que la réimplémentation Python/NumPy pure désassemblée (`PurePythonRedEngine` dans `picasa_py/faces/red_engine_py.py` lisant les 2,39 Mo de `plugins/red.cfg`) produisent tous deux exactement les mêmes boîtes englobantes, angles, confiances et descripteurs `vqc_Cue` de 1 044 octets (corrélation `1.000000`, `max_diff = 0`). Seul le chemin de repli OpenCV Haar (utilisé uniquement si `plugins/red.cfg` est absent de la machine) reste marqué `# TODO(unverified)`.
2. **Formules internes de certains filtres artistiques avancés (`picasa_py/ui/image_processor.py`)** :
   - *Adresse concernée* : `picasa3.exe @ 0x00760F40` et `runtime/filterdesc.xml`.
   - *État* : Les 84 identifiants de filtres, leurs paramètres et leur sérialisation dans `.picasa.ini` (`filters=...`) ainsi que les tables de correspondance (`Sixties`, `CrossProcess`, `Cinemascope`, `HeatMap`, `NightVision`, `Polaroid`, `QuantizePalette`) extraites de `filterdesc.xml` sont exacts. Les shaders internes de certains effets Picnik (`MuseumMatte`, `ReanimatedEyeColor`, `PicnikFocalPixelate`, etc.) sont reproduits par approximation matricielle NumPy et marqués `# TODO(unverified)`.



---

## 13. Écarts relevés par comparaison différentielle avec une base réelle `db3` (17 196 enregistrements)

Méthode : recalcul avec `picasa_py` des valeurs écrites par `picasa3.exe` pour des fichiers présents sur disque
(scripts de vérification en lecture seule). Points corrigés : `tagdate` (0 pour les images, heure locale de
modification pour les vidéos), `originfast` = 0 et pas de `thumbs2` pour les vidéos, `bigthumbs`/`previews` non
créés au scan, grand côté des vignettes forcé à 144 / 72 px avec petit côté arrondi au supérieur, `ft1`/`ft2`
FILETIME exacts (100 ns), type détecté par signature, jetons `wordhash` (nom de fichier + dimensions JPEG).

Points non résolus (`# TODO(unverified)`) :

1. **Arrondi du petit côté des vignettes** : `ceil` exact sur 97–98 % des cas ; les cas restants (valeur très
   proche d'un entier, ex. 96,009 → 96) suggèrent un calcul sur l'image intermédiaire décodée. Routine à localiser
   autour de `0x00424CA0`.
2. **`imagedata_avgcolor`** : écart > 2 niveaux sur ~70 % de l'échantillon. L'original ne moyenne pas comme
   `resize((1,1), BILINEAR)` sur la vignette 144 px (espace, gamma ou source différents). Routine non localisée.
3. **Jetons `wordhash` non reproduits** : `]album:<jeton du dossier>` (album de dossier, catégorie 2),
   `color:<teinte>` (10 teintes), mots EXIF/IPTC (`adobe`, `photoshop`, `iptc`…), étiquettes `]face`, `]star`,
   `]edited`, `]updated`, `]geo`, `]hidden`… Algorithmes à localiser (indexeur de mots, classification de couleur).
4. **Albums de dossier dans `albumdata_*`** : chaque dossier semble disposer d'une ligne `albumdata` de catégorie 2
   (ex. « Pictures » → `]album:3926…`). Création et maintien de ces lignes non reproduits.
5. **Dimensions des RAW** (`.PEF`…) : l'original stocke la taille capteur (ex. 4309×2868) ; `picasa_py` ne sait
   pas décoder ces fichiers et écrit 640×480.
6. **Détection par signature** : observée sur un seul enregistrement (WEBP nommé `.jpg` → type 31) ; routine de
   détection non localisée dans le désassemblage.

---

## 14. Bugs et anomalies découverts dans le binaire original (`picasa3.exe` & `Red.dll`)

Voir le rapport détaillé [`docs/analysis/original_bugs_and_quirks.md`](./analysis/original_bugs_and_quirks.md) qui documente :
- **Catégorie A (4 bugs corrigés dans `PyCasa`)** :
  1. Double calcul et double écriture disque de `backuphash` (`0x00429CA0` & `0x00429D57..0x00429D86`),
  2. `Fallthrough` écrasant `imagedata_crop64 = 0` lorsque `backuphash=` est présent sans `filters=` (`0x00459DE3 -> LAB_00459e21`),
  3. Clé `screensaver=` ignorant sa valeur à droite du `=` dans `SyncIniToDB` (`0x00458F9B`),
  4. Validation incomplète du type de parent dans `SaveThumbIndex` (`0x004F56BA`).
- **Catégorie B (3 bugs/anomalies conservés à l'identique pour garantir l'interopérabilité bit-à-bit et pixel-exact)** :
  5. Troncature `float32` (`12` groupes au lieu de `12.5`) et pointeur `edi` non incrémenté dans `dqc_Relator::init` de `Red.dll` (`0x101007F8..0x10100856`),
  6. Extension de signe `char` signé (`movsx ecx, cl`) sur les octets UTF-8 `>= 0x80` dans les checksums `CBlockFile` (`0x006B9A60`, `0x0042A96A`),
  7. Paramètre `sharpness` câblé en dur à `0.0f` dans le filtre `Soft Focus` / `radblur` (`0x008F8645`).

