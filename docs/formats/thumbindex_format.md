# Spécification du format `thumbindex.db` (Picasa File & Folder Index)

## 1. Vue d'ensemble

Le fichier `thumbindex.db` est situé dans le répertoire de base de données de Picasa (généralement `%LOCALAPPDATA%\Google\Picasa2\db3\thumbindex.db`).
Il contient l'arborescence complète des dossiers surveillés et des fichiers multimédias indexés par Picasa.

Chaque entrée de `thumbindex.db` possède un index de ligne (0-based) qui correspond directement à la même ligne dans :
- `thumbs_index.db` / `thumbs_0.db` (miniatures petites)
- `thumbs2_index.db` / `thumbs2_0.db` (miniatures moyennes)
- `facetemplatesV2_index.db` / `facetemplatesV2_0.db` (modèles de visages)

## 2. Références Ghidra (binaire source de vérité)

- **Fonction d'écriture** : `picasa3.exe @ 0x004F54B0` (`FUN_004f54b0`)
- **Fonction de lecture** : `picasa3.exe @ 0x004F25F0` (`FUN_004f25f0`)
- **Magic number** : `0x40466666` (flottant IEEE 754 float32 `3.1f` stocké à l'adresse `0x00CF4F4C`)
- **Écriture de chaîne terminée par null** : `picasa3.exe @ 0x00996DB0` (`FUN_00996db0`)
- **Écriture bloc métadonnées** : appel `fwrite(&iStack_28, 0x1e, 1, file)` à `0x004F571B` (30 octets fixes)

## 3. Structure binaire

### 3.1 En-tête (8 octets)

| Offset | Type | Nom | Description |
|---|---|---|---|
| `0x00` | `uint32` | `magic` | `0x40466666` (représentation float32 de `3.1f`) |
| `0x04` | `uint32` | `record_count` | Nombre total d'enregistrements |

### 3.2 Enregistrements (répétés `record_count` fois)

Chaque enregistrement est constitué d'une partie de taille variable (chemin) suivie d'une structure de métadonnées de 30 octets (`0x1E`).

#### 3.2.1 Chemin (taille variable)
- Chaîne de caractères terminée par un octet null (`\0`).
- Encodage : UTF-8 ou ANSI selon le système hôte.
- Pour les dossiers : se termine par un antislash `\` (ex. `C:\Users\foo\Pictures\`).
- Pour les fichiers : chemin absolu complet ou nom relatif.

#### 3.2.2 Métadonnées (30 octets fixes, little-endian)

| Offset relatif | Taille | Type | Nom | Description |
|---|---|---|---|---|
| `+0x00` | 8 octets | `uint64` | `ft1` | Horodatage FILETIME Windows 1 (création / modification) |
| `+0x08` | 8 octets | `uint64` | `ft2` | Horodatage FILETIME Windows 2 (dernière écriture) |
| `+0x10` | 4 octets | `uint32` | `size` | Taille du fichier en octets (0 pour les dossiers) |
| `+0x14` | 4 octets | `uint32` | `type` | Type d'élément (1 = Dossier, 2 = Image, 5 = Racine de lecteur) |
| `+0x18` | 2 octets | `uint16` | `flags` | Drapeaux d'attributs (ex. 0x0100 = 256, 0x0102 = 258) |
| `+0x1A` | 4 octets | `uint32` | `parent_idx` | Index du dossier parent (`0xFFFFFFFF` pour les racines) |

Taille totale d'un enregistrement : `len(path_bytes) + 1 + 30` octets.
Taille totale du fichier : `8 + sum(len(rec.path) + 31 for rec in records)`.
