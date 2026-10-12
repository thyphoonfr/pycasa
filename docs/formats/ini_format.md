# Spécification du format INI Picasa (`.picasa.ini` / `Picasa.ini`)

> **Source unique de vérité** : Désassemblage et décompilation de `Picasa3.exe` (PE 32-bit).  
> Conformité stricte : voir [AGENTS.md](../../AGENTS.md) §4.

---

## 1. Vue d'ensemble et localisation dans le binaire

Picasa 3 n'utilise **aucune** fonction de l'API standard Win32 (`GetPrivateProfileString`, `WritePrivateProfileString`). Il implémente son propre parseur et son propre writer en C++.

### Références désassemblage :
- **Writer principal (.picasa.ini)** :
  `FUN_0068ac80` @ `0x0068AC80` - `0x0068C412`  
  Formatage direct dans des buffers mémoire avant écriture atomique sur disque.
- **Moteur de parsing INI (Recherche section/clé)** :
  `FUN_009be730` @ `0x009BE730` - `0x009BE9AE`  
  Lecture en mémoire, parcours par délimiteurs `\n`, `[`, `]`, `=`, `\r\n`.
- **Lecture du fichier sur disque** :
  `FUN_009bd390` / `FUN_009bd490` @ `0x009BD390` - `0x009BD5A0`  
  Appels directs à `CreateFileA` (`0x00C40424`), `GetFileSize` (`0x00C40420`), `ReadFile` (`0x00C4042C`).
- **Gestionnaire / Fallback de nom de fichier** :
  `FUN_0045c0a0` @ `0x0045C0A0` et `FUN_005ab320` @ `0x005AB320`  
  Recherche de `.picasa.ini`, repli sur `Picasa.ini`.

---

## 2. Règles syntaxiques et encodage

1. **Encodage** :
   - UTF-8 pur, **sans BOM** (`EF BB BF`).
   - L'en-tête explicite `[encoding]\r\nutf8=1\r\n` est émis par `0x0068AE31` lorsque des métadonnées globales de dossier/album sont présentes.
2. **Fin de ligne** :
   - Strictement CRLF (`\r\n` : `0x0D 0x0A`).
3. **Sensibilité à la casse** :
   - La recherche de section et de clé dans `FUN_009be730` convertit les caractères ASCII `A-Z` en `a-z` (`+ 0x20`), rendant les clés et sections insensibles à la casse en lecture.
   - En écriture (`FUN_0068ac80`), la casse canonique exacte du binaire doit être reproduite (ex. `[Contacts2]`, `backuphash=`, `faces=`, `star=yes`).
4. **Espaces et séparateurs** :
   - Aucun espace autour du signe `=` (`clé=valeur\r\n`).
   - Aucun guillemet d'encadrement des chaînes (les valeurs sont écrites brutes).
   - Les listes utilisent la virgule `,` ou le point-virgule `;` selon la clé.

---

## 3. Inventaire exhaustif des sections et clés

### 3.1 Section `[encoding]`
Écrite par `FUN_0068ac80` @ `0x0068AE31` :
- `utf8=1` : Indique que les chaînes sont encodées en UTF-8.

### 3.2 Section `[Picasa]` (Métadonnées de collection / dossier)
Écrite par `FUN_0068ac80` @ `0x0068AE9D` - `0x0068AF8E` :
- `name=%s` : Nom du dossier ou de la collection.
- `description=%s` : Description textuelle.
- `location=%s` : Lieu géographique ou dossier.
- `category=%s` : Catégorie.
- `date=%f` : Date numérique (flottant).
- `%s=%s` : Paires de propriétés supplémentaires `_lh`.

### 3.3 Section `[Contacts2]`
Stocke la table des personnes identifiées dans le dossier :
- Format : `<contact_id_hex>=<Nom>;<email>;<extra>`
- Exemple : `aa28c3a53f34c2f8=Jean Dupont;;`

### 3.4 Sections d'album `[.album:<uid32>]`
Stocke les métadonnées d'un album virtuel lié :
- `name=%s` : Titre de l'album.
- `token=%s` : Jeton d'album (identique au hash hexadécimal de l'UID).
- `date=%s` : Date ISO 8601 (ex. `2026-08-26T15:41:38+02:00`).

### 3.5 Sections de fichier image `[<nom_fichier>]` (ex. `[IMG_0001.JPG]`)
Écrites par `FUN_0068ac80` @ `0x0068B37F` - `0x0068BABF` :
- `crop=rect64(%s)` (Ref: `0x0068B63D`) :  
  Valeur hexadécimale 64-bit (`%I64x`, ex. `rect64(1d3a0e46ffffe75e)`).
- `filters=%s` :  
  Liste de filtres et retouches séparés par des points-virgules (ex. `redeye=1;retouch=1;picnik=1;`).
- `caption=%s` (Ref: `0x0068B870`) :  
  Légende textuelle de la photo.
- `star=yes` (Ref: `0x0068B800`) :  
  Présent si la photo est marquée comme favorite ("star"). Absent sinon.
- `keywords=%s` (Ref: `0x0068B8BD`) :  
  Liste de mots-clés séparés par des virgules (Ref: `0x0068B9A6` `push 0x2c`).
- `faces=%s` (Ref: `0x0068BABA`) :  
  Liste de visages reconnus : `rect64(<coords_hex64>),<contact_id_hex>;...`
- `backuphash=%d` :  
  Entier de synchronisation du fichier de sauvegarde.
- `albums=%s` :  
  Liste d'UIDs d'albums séparés par des virgules (éventuellement préfixés de `]album:`).
- `IIDLIST_%s=%s` (Ref: `0x0068B9F7`) :  
  Identifiants internes d'éléments.
- `rotate=rotate(%d)` :  
  Angle de rotation (0, 1, 2, 3 pour 0°, 90°, 180°, 270°).

---

## 4. Préservation des données inconnues (Round-Trip)

Conformément à [AGENTS.md](../../AGENTS.md) §4.1 :
- Toute section ou clé inconnue rencontrée lors de la lecture doit être **conservée à l'identique**, à sa position relative, et réécrite telle quelle.
- L'ordre relatif des sections et des clés doit être rigoureusement préservé.
