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

## 11. Prochaines étapes
- [ ] Phase 6 : Mesures de performances initiales, profilage et benchmarks comparatifs (`docs/perf/targets.md`).
- [ ] Phase 7 : Moteur de scan de dossiers & Gestionnaire de dossiers (`FOLDERMGR_TEXT.XML`).
