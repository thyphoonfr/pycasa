# Spécification du format `wordhash.dat` (Index de recherche textuelle)

## 1. Vue d'ensemble

Le fichier `wordhash.dat` est situé dans `%LOCALAPPDATA%\Google\Picasa2\db3\wordhash.dat`.
Il sert d'index inversé de recherche rapide par mot-clé pour toute la photothèque de Picasa (mots des noms de fichiers, dossiers, métadonnées, dates, tags, etc.).

## 2. Références Ghidra (binaire source de vérité)

- **Fonction d'écriture globale** : `picasa3.exe @ 0x004DB4F0` (`FUN_004db4f0`)
- **Fonction de lecture globale** : `picasa3.exe @ 0x004DB720` (`FUN_004db720`)
- **Sérialisation du pool de chaînes** : `picasa3.exe @ 0x00A61700` (`FUN_00a61700`)
- **Désérialisation du pool de chaînes** : `picasa3.exe @ 0x00A617B0` (`FUN_00a617b0`)
- **Sérialisation de la table de mots** : `picasa3.exe @ 0x00704500` (`FUN_00704500`)
- **Désérialisation de la table de mots** : `picasa3.exe @ 0x007046E0` (`FUN_007046e0`)
- **Écriture de vecteur colonne** : `picasa3.exe @ 0x0099C1E0` (`FUN_0099c1e0`)
- **Calcul d'offset dans le pool** : `picasa3.exe @ 0x00A61A70` (`FUN_00a61a70`)
- **Magic number** : `0x3FCCCCCD` (flottant IEEE 754 float32 `1.6f`)

## 3. Structure binaire

### 3.1 En-tête principal (8 octets)

| Offset | Type | Nom | Description |
|---|---|---|---|
| `0x00` | `uint32` | `magic` | `0x3FCCCCCD` (float32 `1.6f`) |
| `0x04` | `uint32` | `max_doc_id` | Identifiant/index maximum de document indexé (+1) |

### 3.2 Pool de chaînes (taille variable)

Écrit par `FUN_00a61700` :

| Offset | Type | Nom | Description |
|---|---|---|---|
| `0x08` | `uint32` | `chunk_count` | Nombre de blocs alloués pour le pool (ex. 1) |
| `0x0C` | `uint32` | `chunk_size` | Taille en octets d'un bloc (ex. `65536` = 64 Ko) |
| `0x10` | `uint32` | `used_bytes` | Nombre d'octets réellement occupés par des chaînes |
| `0x14` | `bytes` | `pool_data` | `chunk_count * chunk_size` octets de données brutes contenant toutes les chaînes terminées par `\0` |

### 3.3 Table d'index inversé

Écrit par `FUN_00704500` :

| Offset relatif | Type | Nom | Description |
|---|---|---|---|
| `+0x00` | `uint32` | `word_count` | Nombre total d'entrées de mots dans l'index |

Suivi de `word_count` enregistrements :

Pour chaque mot :
1. `str_offset: uint32` : Déplacement en octets du mot dans `pool_data` (début de la chaîne terminée par `\0`).
2. `count: uint32` : Nombre d'identifiants d'images contenant ce mot.
3. `items: count * uint32` : Liste des identifiants (row indices) des images correspondantes.
