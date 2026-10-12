# Spécification du format PMP (`.pmp` - Picasa Property Map)

> **Source unique de vérité** : Désassemblage et décompilation de `Picasa3.exe` (PE 32-bit).  
> Conformité stricte : voir [AGENTS.md](../../AGENTS.md) §3.

---

## 1. Vue d'ensemble et localisation dans le binaire

Les fichiers `.pmp` (Property Map) constituent le moteur de stockage par colonne de la base de données Picasa (`db3/`).
Chaque table (`imagedata`, `albumdata`, `catdata`) est décomposée en colonnes indépendantes nommées selon le motif `%s_%s.pmp` (Table_Champ.pmp).

### Références désassemblage :
- **Classe C++** : `CPropertyMap` (`.\thumblab\CPropertyMap.cpp` @ `0x00CA8104`)
- **Format de nom de fichier** : `%s_%s.%s` @ `0x00CA80F8`
- **Extension** : `pmp` @ `0x00CA80F4`, `.pmp` @ `0x00CA80EC`
- **Méthode d'ouverture / lecture fichier** :  
  `FUN_006a2b60` @ `0x006A2B60` - `0x006A2CCD`
- **Méthode de dispatch et lecture de structure** :  
  `FUN_006d17f0` @ `0x006D17F0` - `0x006D18C0`
- **Lecteur de chaînes (Type 0x0000)** :  
  `FUN_009977a0` @ `0x009977A0` - `0x009978E0`
- **Lecteur d'entiers 32-bit (Type 0x0001 / 0x0007)** :  
  `FUN_00997f40` @ `0x00997F40`
- **Lecteur 64-bit / Double (Type 0x0002 / 0x0004)** :  
  `FUN_009981e0` @ `0x009981E0`
- **Lecteur d'octets 8-bit (Type 0x0003 / 0x0006)** :  
  `FUN_009975d0` @ `0x009975D0`, `FUN_00998090` @ `0x00998090`
- **Lecteur d'entiers 16-bit (Type 0x0005)** :  
  `FUN_00998330` @ `0x00998330`

---

## 2. Structure binaire de l'en-tête (20 octets)

L'en-tête est strictement composé de 5 entiers 32-bit little-endian :

| Offset | Champ | Type | Valeur / Description |
|---|---|---|---|
| `0x00` | `magic` | `uint32` | `0x3FCCCCCD` (Représentation binaire IEEE 754 de `1.6f`) |
| `0x04` | `type_id` | `uint32` | `0x13320000 | type_enum` (Identifiant du type de champ) |
| `0x08` | `subversion` | `uint32` | `0x00000002` (Version de schéma PMP) |
| `0x0C` | `type_id_repeat` | `uint32` | `type_id` (Répétition identique du champ `type_id`) |
| `0x10` | `record_count` | `uint32` | Nombre total d'enregistrements (lignes) dans la colonne |

---

## 3. Types de données supportés (`type_enum`)

Le type effectif est déterminé par `type_id & 0x0000FFFF` :

| `type_enum` | Format | Taille par élément | Description | Exemples de champs |
|---|---|---|---|---|
| `0x0000` | Chaîne UTF-8 | Variable | Chaînes terminées par `\0` écrites consécutivement. Chaîne vide = `\0` unique. | `imagedata_caption.pmp`, `catdata_name.pmp`, `albumdata_filename.pmp` |
| `0x0001` | `uint32` | 4 octets | Entier non signé 32-bit | `albumdata_category.pmp`, `imagedata_avgcolor.pmp` |
| `0x0002` | `double` | 8 octets | Flottant 64-bit IEEE 754 (dates OLE, coordonnées GPS) | `albumdata_date.pmp`, `imagedata_lat.pmp`, `imagedata_long.pmp` |
| `0x0003` | `uint8` | 1 octet | Entier non signé 8-bit (booléen / drapeaux / priorité) | `catdata_catpri.pmp`, `albumdata_hascollage.pmp` |
| `0x0004` | `uint64` | 8 octets | Entier non signé 64-bit | `imagedata_crop64.pmp`, `imagedata_facerect.pmp`, `albumdata_albumcontactids.pmp` |
| `0x0005` | `uint16` | 2 octets | Entier non signé 16-bit | `imagedata_backuphash.pmp`, `imagedata_rotate.pmp` |
| `0x0006` | Chaîne UTF-8 | Variable | Chaînes terminées par `\0` (accès par pointeur direct) | `imagedata_tags.pmp` |
| `0x0007` | `uint32` | 4 octets | Entier non signé 32-bit (variante d'index) | `albumdata_unread.pmp` |

---

## 4. Règle de round-trip

- Taille totale attendue pour les types fixes : `20 + (record_count * element_size)`.
- Taille totale pour les chaînes : `20 + sum(len(s.encode('utf-8')) + 1 for s in strings)`.
- Réécriture : les 20 octets d'en-tête et les enregistrements sont sérialisés octet pour octet à l'identique de l'original.
