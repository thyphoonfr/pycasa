# Spécification du format Key-Value Table (`repository.dat`, `usernames.dat`)

## 1. Vue d'ensemble

Les fichiers `repository.dat` et `usernames.dat` sont situés dans `%LOCALAPPDATA%\Google\Picasa2\db3\`.
Ils stockent des paires clé-valeur textuelles pour :
- `repository.dat` : les métadonnées globales du référentiel (DBID, versions des modules, dossiers surveillés).
- `usernames.dat` : les associations d'utilisateurs.

## 2. Références Ghidra (binaire source de vérité)

- **Référencé dans** : `picasa3.exe @ 0x0041415A` (`repository.dat`), `0x00416652` (`usernames.dat`)
- **Vtable associée** : `0x00C827F8`
- **Méthodes I/O CFile** : `picasa3.exe @ 0x009BD220` / `0x009BD390`
- **Magic number** : `0x3FCCCCCD` (flottant IEEE 754 float32 `1.6f`)

## 3. Structure binaire

### 3.1 En-tête (8 octets)

| Offset | Type | Nom | Description |
|---|---|---|---|
| `0x00` | `uint32` | `magic` | `0x3FCCCCCD` (float32 `1.6f`) |
| `0x04` | `uint32` | `pair_count` | Nombre de paires clé-valeur |

### 3.2 Données (paires clé-valeur)

Immédiatement après l'en-tête se trouvent `pair_count` paires de chaînes terminées par un octet null (`\0`) :
1. `key` : chaîne UTF-8 terminée par `\0`
2. `value` : chaîne UTF-8 terminée par `\0`

Taille totale du fichier :
`8 + sum(len(key.encode('utf-8')) + 1 + len(val.encode('utf-8')) + 1 for key, val in pairs)`
