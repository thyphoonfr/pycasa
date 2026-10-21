# Spécification du format `CBlockFile` (Containers et Index de Miniatures)

## 1. Vue d'ensemble

Les images de miniatures, prévisualisations et visages de Picasa sont stockées dans des conteneurs binaires gérés par la classe C++ `CBlockFile` (`.\thumblab\CBlockFile.cpp`).

Chaque type de miniature est composé de :
1. Un fichier d'index nommé `<prefix>_index.db` (ex. `thumbs_index.db`, `thumbs2_index.db`, `bigthumbs_index.db`, `previews_index.db`, `albums_index.db`, `facetemplatesV2_index.db`).
2. Un ou plusieurs fichiers de blocs nommés `<prefix>_%d.db` (ex. `thumbs_0.db`, `thumbs_1.db`...).

## 2. Références Ghidra (binaire source de vérité)

- **Fichier source original** : `.\thumblab\CBlockFile.cpp` référencé aux adresses `0x00CA847C`, `0x00CA8487`.
- **Constructeur** : `picasa3.exe @ 0x006B5D40` (`FUN_006b5d40`)
- **Écriture de l'index (`SaveIndex`)** : `picasa3.exe @ 0x006B7FC0` (`FUN_006b7fc0`)
- **Lecture de l'index (`ReadIndex`)** : `picasa3.exe @ 0x006B82E0` (`FUN_006b82e0`)
- **Écriture d'un élément (`WriteEntry`)** : `picasa3.exe @ 0x006B75F0` (`FUN_006b75f0`)
- **Initialisation/validation des tables** : `picasa3.exe @ 0x006B8AC0` (`FUN_006b8ac0`)
- **Fermeture/vidage (`Close`/`Flush`)** : `picasa3.exe @ 0x006B9470` (`FUN_006b9470`)
- **Écriture d'un vecteur colonne** : `picasa3.exe @ 0x0099C1E0` (`FUN_0099c1e0`)
- **Écriture d'un entier 32-bit** : `picasa3.exe @ 0x00996D50` (`FUN_00996d50`)
- **Export CSV de diagnostic** : `picasa3.exe @ 0x006B5E00` (`FUN_006b5e00`, en-tête `"Size,Offset,Checksum\n"`, format `"%d,%d,%d\n"`)
- **Magic number** : `0x3FCCCCCD` (flottant IEEE 754 float32 `1.6f` stocké à l'adresse globale `_DAT_00d678e0`)

---

## 3. Structure du fichier d'index (`*_index.db`)

L'index n'est pas un fichier d'enregistrements entrelacés, mais une structure de **trois vecteurs colonnes successifs**.

### 3.1 En-tête (8 octets)

| Offset | Type | Nom | Description |
|---|---|---|---|
| `0x00` | `uint32` | `magic` | `0x3FCCCCCD` (float32 `1.6f`) |
| `0x04` | `uint32` | `active_block` | Numéro du bloc actif actuel (généralement 0) |

### 3.2 Vecteurs de données

L'en-tête est immédiatement suivi de trois vecteurs écrits par `FUN_0099c1e0` :

Chaque vecteur se compose de :
- `count: uint32` (nombre d'éléments)
- `count * uint32` (les valeurs 32-bit little-endian)

#### Vecteur 1 : Sommes de contrôle (`Checksums`)
- `count1: uint32`
- `count1` entiers `uint32` : CRC / Checksum / Hash de chaque élément (0 si l'entrée est vide).

#### Vecteur 2 : Déplacements (`Offsets`)
- `count2: uint32` (égal à `count1`)
- `count2` entiers `uint32` : Déplacement en octets du début de l'élément dans le fichier bloc correspondant.

#### Vecteur 3 : Tailles et numéros de bloc (`Sizes & Blocks`)
- `count3: uint32` (égal à `count1`)
- `count3` entiers `uint32` :
  - Bits 0..23 (`val & 0x00FFFFFF`) : Taille de l'élément en octets.
  - Bits 24..31 (`(val >> 24) & 0xFF`) : Numéro du fichier bloc contenant l'élément (ex. 0 pour `thumbs_0.db`, 1 pour `thumbs_1.db`).

Taille totale du fichier `*_index.db` :
`8 + (4 + count * 4) * 3 = 20 + count * 12` octets.

---

## 4. Structure des fichiers blocs (`*_0.db`, `*_1.db`...)

### 4.1 En-tête (4 octets)

| Offset | Type | Nom | Description |
|---|---|---|---|
| `0x00` | `uint32` | `magic` | `0x3FCCCCCD` (float32 `1.6f`) |

### 4.2 Données (à partir de l'offset 4)

Les données des images (miniatures JPEG, modèles de visages, prévisualisations) sont concaténées séquentiellement à partir de l'offset `4`.
Chaque élément est adressé par son triplet `(block, offset, size)` présent dans l'index :
- `block` indique le fichier `<prefix>_%d.db`
- `offset` indique la position exacte de départ dans ce fichier (doit être $\ge 4$)
- `size` indique le nombre d'octets exacts du blob (ex. image JPEG débutant par `0xFF 0xD8` et se terminant par `0xFF 0xD9`).

---

## 5. Formules exactes de calcul des `Checksums` (Vecteur 1)

| Fichier d'index | Adresse Ghidra | Niveau de confiance | Formule exacte |
|---|---|---|---|
| `thumbs_index.db`, `thumbs2_index.db`, `bigthumbs_index.db` | `picasa3.exe @ 0x006B99F0` (`FUN_006b99f0` -> `0x004E3AB0`) | **Confirmé** (100 % sur 753 entrées réelles) | `full_path` (chemin du dossier parent avec `\` final + nom du fichier, converti en minuscules `tolower` octet par octet, terminé par `\0`), haché avec `hash = 0` puis `hash = (hash * 5 + byte) & 0xFFFFFFFF`, puis `checksum = (hash + ft_low + size) & 0xFFFFFFFF` (`ft_low = ft2 & 0xFFFFFFFF`). |
| `previews_index.db` | `picasa3.exe @ 0x0042A800` (`FUN_0042a800`) | **Confirmé** (100 % sur les entrées réelles) | `checksum = ((ft2 & 0xFFFFFFFF) + (rotate_step & 3) + (4 if flip else 0)) & 0xFFFFFFFF`. |
| `facetemplatesV2_index.db` | `picasa3.exe @ 0x0048050B` (`FUN_004804a0`) | **Confirmé** (100 % sur 1 160 entrées réelles) | Constante `1` (`0x00000001`). |

---

## 6. Format binaire des blobs `facetemplatesV2_0.db` (`vqc_Cue`, 1 044 octets)

Les empreintes faciales de `facetemplatesV2_0.db` sont sérialisées par le moteur Neven Vision / PittPatt (`Red.dll` + modèle `plugins/red.cfg`, classe C++ `vqc_Cue`, ID `0x00423002`, format `0x0044DD4D`).

### 6.1 Références Ghidra (`Red.dll` & `picasa3.exe`)
- `picasa3.exe @ 0x00881480` : lecture de `facetemplatesV2` via `CBlockFile::GetBlock` (`checksum == 1`) et désérialisation via `Red.dll`.
- `Red.dll @ 0x10102020` : sérialisation / désérialisation de `vqc_Cue`.
- `Red.dll @ 0x1014A340` : calcul du checksum interne sur les `1 032` premiers octets (`sum(bytes[0:1032]) * 0x00041AE5 & 0xFFFFFFFF`).
- `Red.dll @ 0x100FE262..0x100FE320` : calcul de `inv_norm = float32(1.0 / sqrt(vqc_Relator::rawSim(cue, cue)))`.
- `Red.dll @ 0x100FF050..0x100FFF45` & `0x101007D7..0x10100865` : `vqc_Relator::rawSim` et `dqc_Relator::init` (table de poids `float32[2000]` à l'offset `0x1F5C1C` dans `plugins/red.cfg`, `delta_term = -2.46279f` à `0x1F7B7A`, facteur `0.25`).
- `Red.dll @ 0x100FCF60` & `0x100FCB00` : `vqc_Quantizer::map` (classe `0x00423004`, 30 000 seuils `float32[2000, 15]` à l'offset `0x20BBDC` dans `plugins/red.cfg`).

### 6.2 Disposition d'un enregistrement `vqc_Cue` (1 044 octets)

| Offset | Taille | Type | Nom | Description |
|---|---|---|---|---|
| `0x000` (0) | 4 | `uint32` | `class_id` | `0x00423002` (`vqc_Cue`) |
| `0x004` (4) | 4 | `uint32` | `format_id` | `0x0044DD4D` |
| `0x008` (8) | 4 | `uint32` | `reserved_0` | `0` |
| `0x00C` (12) | 4 | `uint32` | `n_dims` | `2000` (`0x000007D0`) |
| `0x010` (16) | 1000 | `uint8[1000]` | `packed_nibbles` | 2 000 valeurs quantifiées sur 4 bits (`0..15`) : `q[2*i] = byte & 0x0F`, `q[2*i+1] = (byte >> 4) & 0x0F` |
| `0x3F8` (1016) | 4 | `float32` | `inv_norm` | `1.0 / sqrt(vqc_Relator::rawSim(cue, cue))` |
| `0x3FC` (1020) | 12 | `float32[3]` | `pose_meta` | Métadonnées d'orientation/pose du visage |
| `0x408` (1032) | 4 | `uint32` | `cue_checksum` | `(sum(blob[0:1032]) * 0x00041AE5) & 0xFFFFFFFF` |
| `0x40C` (1036) | 4 | `uint32` | `tail_size` | `8` (`0x00000008`) |
| `0x410` (1040) | 4 | `uint32` | `tail_flags` | `0` (`0x00000000`) |

