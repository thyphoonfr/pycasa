# Bugs et anomalies découverts dans le binaire original (`picasa3.exe` & `Red.dll`)

Ce document recense les **7 bugs et anomalies d'implémentation** découverts lors du désassemblage pas-à-pas de `picasa3.exe` (v3.9.141.259) et de son moteur de reconnaissance faciale `plugins/Red.dll`.

Conformément aux règles d'interopérabilité stricte (`AGENTS.md` §1, §3, §4, §4 bis), ces 7 anomalies sont réparties en deux catégories :
1. **Catégorie A — Les 4 bugs corrigés dans `PyCasa`** : leur correction élimine des pertes de données ou des écritures disque redondantes **sans jamais compromettre la compatibilité**, et protège même `picasa3.exe` contre ses propres bugs lorsqu'il relit les fichiers écrits par `PyCasa`.
2. **Catégorie B — Les 3 bugs/anomalies conservés à l'identique dans `PyCasa`** : leur maintien bit-à-bit est **indispensable** car toute modification romprait la compatibilité binaire (`facetemplatesV2_0.db`, `thumbs_index.db`, `previews_index.db`) ou la fidélité au pixel près des filtres.

---

## Catégorie A — Bugs corrigés dans `PyCasa` (Bénéfiques & 100 % Compatibles)

### 1. Double calcul et double écriture disque de `backuphash`
- **Localisation dans `picasa3.exe`** :
  - Fonction : `FUN_00429ca0` (`0x00429CA0..0x00429D05`)
  - Appelant : `0x00429D57..0x00429D86`
- **Analyse du désassemblage** :
  1. Contrairement à ce que son nom suggère, `backuphash=` dans `.picasa.ini` (et `imagedata_backuphash.pmp`) **n'est pas un hash du fichier image**. La fonction `0x00429CA0` appelle `GetCurrentOleDate()` (`0x0098B6E0`, qui retourne l'horodatage courant sous forme d'un `double` IEEE-754 de 8 octets), découpe ces 8 octets en quatre mots de 16 bits (`w0, w1, w2, w3`) et calcule :
     $$\text{backuphash} = (w_0 \oplus w_1 \oplus w_2 \oplus w_3) \pmod{65536}$$
     puis écrit ce `uint16` dans `.picasa.ini` (`backuphash=%d`) et dans `imagedata_backuphash.pmp`.
  2. **Le bug à `0x00429D57`** : L'appelant exécute `call 0x00429CA0`, puis **immédiatement après le retour de la fonction (`0x00429D5C..0x00429D86`)**, exécute une seconde fois exactement les mêmes instructions en ligne (probablement une fonction `inline` ou macro C++ appelée deux fois par erreur) et réécrit une deuxième fois `backuphash` dans `.picasa.ini` et dans `imagedata_backuphash.pmp`.
- **Correction dans `PyCasa`** :
  - Dans [`OneUpView.save_current_photo`](../../picasa_py/ui/one_up_view.py), `PyCasa` calcule le `XOR` 16 bits exact de la date OLE Automation (`w0 ^ w1 ^ w2 ^ w3`) mais ne l'écrit **qu'une seule fois** dans `.picasa.ini` et `imagedata_backuphash.pmp`.
- **Pourquoi c'est 100 % compatible** :
  - La valeur 16 bits produite a exactement la même distribution et le même format que celle attendue par `picasa3.exe`, tout en divisant par deux les écritures disque lors de la sauvegarde d'une photo.

---

### 2. Écrasement du recadrage (`crop=rect64(...)`) lorsque `backuphash=` est présent sans `filters=`
- **Localisation dans `picasa3.exe`** :
  - Fonction : `SyncIniToDB` (`FUN_00456a15` @ `0x00456A15`)
  - Bloc fautif : `0x00459A10..0x0045A0A6` (voir [`docs/analysis/func_00456a15.c`](./func_00456a15.c))
- **Analyse du désassemblage** :
  - Lors de la lecture d'une section `[photo.jpg]` dans `.picasa.ini` :
    - Si `crop=rect64(...)` est présent, `cStack000000a4` (`has_crop`) passe à `1` et `imagedata_crop64` reçoit le `uint64` du rectangle.
    - Plus bas (`0x00459DC0`), le code vérifie si `filters=` a été vu (`param_18._1_1_`).
    - Si `filters=` est **absent** mais que `backuphash=` est **présent** (`(char)param_18 != '\0'`), le code emprunte la branche `0x00459DE3` pour vider `imagedata_filters`, puis **tombe directement (`fallthrough`) dans `LAB_00459e21` sans tester `has_crop` (`cStack000000a4`)** !
    - Or `LAB_00459e21` remet **`imagedata_crop64 = 0`**, détruisant le recadrage pourtant lu quelques lignes plus haut à partir de `crop=rect64(...)` !
- **Correction dans `PyCasa` (lecture + écriture protectrice)** :
  1. **En lecture** ([`PicasaDatabase.sync_photo_ini_to_db`](../../picasa_py/db/database.py)) : `PyCasa` ne contient pas ce `fallthrough` fautif ; il conserve toujours `imagedata_crop64` lorsque `crop=rect64(...)` est présent et synthétise automatiquement `crop64=1,<hex>;` dans `imagedata_filters` s'il manquait.
  2. **En écriture** ([`PicasaIniDocument.set_crop_rect64`](../../picasa_py/ini/parser.py) et [`PicasaIniDocument.set_crop`](../../picasa_py/ini/parser.py)) : Dès qu'une section possède `backuphash=` (ou `filters=`), l'écriture d'un recadrage par `PyCasa` ajoute systématiquement `filters=crop64=1,<hex>;` dans `.picasa.ini`.
- **Pourquoi c'est 100 % compatible (et protège `picasa3.exe`)** :
  - Non seulement `PyCasa` ne perd jamais un recadrage, mais en écrivant systématiquement `filters=crop64=1,<hex>;` dès que `backuphash=` est présent, `PyCasa` **empêche `picasa3.exe` de tomber dans son propre bug `0x00459DE3`** lorsqu'on ouvre ensuite le dossier dans `picasa3.exe`.

---

### 3. La clé `screensaver=` ignore sa valeur dans `SyncIniToDB`
- **Localisation dans `picasa3.exe`** :
  - Fonction : `SyncIniToDB` (`FUN_00456a15` @ `0x00458F9B..0x00459075`, [`docs/analysis/func_00456a15.c`](./func_00456a15.c))
- **Analyse du désassemblage** :
  - Alors que les branches `star=` (`0x00458D60`) et `hidden=` (`0x00458E80`) comparent explicitement la valeur à droite du `=` avec `"yes"`, la branche `screensaver=` (`0x00458F9B`) **ne lit jamais le pointeur de valeur** : dès que la clé `screensaver=` apparaît dans une section (même sous la forme `screensaver=no`, `screensaver=0` ou `screensaver=`), `picasa3.exe` ajoute inconditionnellement le jeton `]screensaver` dans `wordhash.dat`.
- **Correction dans `PyCasa`** :
  - Dans [`PicasaDatabase.sync_photo_ini_to_db`](../../picasa_py/db/database.py), `PyCasa` vérifie la valeur de `screensaver=` :
    - Si elle vaut `"yes"`, `"1"`, `"true"` (ou toute valeur affirmative écrite par `picasa3.exe`), `]screensaver` est ajouté à `wordhash.dat`.
    - Si la clé est supprimée ou vaut `"no"`, `"0"`, `"false"` ou `""`, `]screensaver` est retiré de `wordhash.dat`.
- **Pourquoi c'est 100 % compatible** :
  - `picasa3.exe` écrit toujours `screensaver=yes` lorsqu'une photo est ajoutée à l'économiseur d'écran et supprime la ligne lorsqu'elle en est retirée ; les deux applications restent donc 100 % synchronisées tout en évitant les entrées fantômes sur `screensaver=no` ou `screensaver=0`.

---

### 4. Validation incomplète des parents dans `SaveThumbIndex` (`thumbindex.db`)
- **Localisation dans `picasa3.exe`** :
  - Fonction : `SaveThumbIndex` (`FUN_004f54b0` @ `0x004F54B0`, bloc `0x004F56BA`, voir [`docs/analysis/thumbindex_004F54B0.c`](./thumbindex_004F54B0.c))
- **Analyse du désassemblage** :
  - Lors de la sérialisation de `thumbindex.db`, `0x004F56BA` vérifie que chaque entrée n'a pas de cycle de parenté (`depth <= 10`), mais ne vérifie que le parent est un dossier valide (`parent.type in (1, 0x19)`) **que lorsque l'enfant est de `type == 4`** (archive/film).
  - Si un dossier (`type == 1`) ou une photo (`type == 2`) est supprimé (`type = 0, flags = 0`) sans que ses enfants directs (photos `type == 2`, vidéos `type == 7`, ou sous-enregistrements de visages `type == 1001`) aient été purgés, `picasa3.exe` laisse ces enfants orphelins pointer vers une entrée `type == 0` dans `thumbindex.db`.
- **Correction dans `PyCasa`** :
  - Dans [`ThumbIndexFile.sanitize_records`](../../picasa_py/db/thumbindex.py) (appelé lors de l'écriture sur disque de `thumbindex.db`) :
    1. **Passe 1** : invalide (`mark_deleted()`) toute entrée `type == 0`, `flags_hi == 0`, ou présentant un cycle / parent hors bornes / parent supprimé sur une chaîne allant jusqu'à 10 niveaux (`0x004F56BA`).
    2. **Passe 2** : vérifie que tout média (`type in (2, 4, 7, 18, 32)`) ayant un parent pointe bien vers un dossier actif (`type in (1, 0x19)`), et que tout sous-enregistrement de visage (`type == 1001`) pointe bien vers un média actif (`type in (2, 7, 18, 32)`).
- **Pourquoi c'est 100 % compatible** :
  - Un enregistrement invalidé par `mark_deleted()` est sérialisé avec `path=""`, `type=0`, `flags=0`, `parent_idx=0xFFFFFFFF` — le format exact des slots libres de `thumbindex.db` dans `picasa3.exe` (`0x004F571B`). Cela évite les enregistrements fantômes dans les deux applications sans jamais décaler les index de lignes des tables `.pmp`.

---

## Catégorie B — Bugs et anomalies conservés à l'identique dans `PyCasa` (Indispensables à l'interopérabilité)

### 5. Double bug dans `dqc_Relator::init` de `Red.dll` (Troncature `float32` + Pointeur `edi` non incrémenté)
- **Localisation dans `Red.dll`** :
  - Fonction : `dqc_Relator::init` (`0x101007F8..0x10100856`)
- **Analyse du désassemblage** :
  1. **Bug de troncature `float32` (`0x101007F8..0x1010081A`)** :
     - Le modèle de reconnaissance faciale (`plugins/red.cfg`, bloc `0x00423003`) comporte `2000` poids répartis en `250` groupes de `8`.
     - Le code cherche à conserver tels quels les premiers `5 %` des groupes (`250 * (1.0 - 0.95) = 12.5`) et à moyenner par groupe de 8 les `95 %` restants.
     - Or `0.95f` est stocké en IEEE-754 `float32` (`0x3F733333` = `0.94999998807907104492`).
     - En FPU 80 bits : `1.0 - 0.949999988079071 = 0.05000001192092895508`, multiplié par `250` = `12.5000029802322387695`, puis tronqué en entier par `_ftol2_sse` à **`12` groupes (`96` poids)** au lieu de `100` !
  2. **Bug du pointeur `edi` figé dans la boucle interne (`0x10100838..0x10100845`)** :
     - Pour chacun des groupes `m = 12..249`, une boucle interne de 8 itérations est censée additionner les 8 poids du groupe (`w[m*8 + 0] .. w[m*8 + 7]`) puis diviser la somme par 8 :
       ```asm
       10100838: fldz                     ; sum = 0.0
       1010083a: mov eax, 8               ; compteur = 8
       1010083f: fadd dword ptr [edi]     ; sum += *edi  <-- BUG : edi n'est JAMAIS incrémenté !
       10100841: sub eax, 1
       10100844: jne 1010083f
       10100846: fmul dword ptr [...]     ; sum *= 0.125 (1/8)
       ```
     - Comme `edi` pointe sur `w[m*8 + 0]` et n'est **jamais incrémenté** dans la boucle `1010083f..10100844`, la boucle calcule `8 * w[m*8 + 0] * 0.125 = w[m*8 + 0]`, puis la boucle suivante (`1010084C..10100856`, où l'auteur a bien écrit `add ecx, 4`) écrase les 8 poids du groupe `m` avec la valeur du **1er poids `w[m*8 + 0]`** !
- **Pourquoi `PyCasa` DOIT conserver ce bug à l'identique** :
  - Les scores de similarité faciale (`vqc_Relator`) et le regroupement des visages entre `facetemplatesV2_0.db` et les albums personnes reposent directement sur ce tableau de 2 000 poids pondérés.
  - Si `PyCasa` calculait la « vraie » moyenne des 8 poids par groupe, tous les produits scalaires et distances sigmoïdes divergeraient de ceux calculés par `picasa3.exe`. C'est pourquoi [`picasa_py/faces/engine.py`](../../picasa_py/faces/engine.py) reproduit exactement `m_start = 12` et `w[m*8 : m*8+8] = w[m*8]`.

---

### 6. Extension de signe `char` signé (`movsx ecx, cl`) sur les octets UTF-8 dans les checksums `CBlockFile`
- **Localisation dans `picasa3.exe`** :
  - Fonctions : `ComputePathHash` (`0x006B9A60`), `GetThumbnailChecksum` (`0x0042A96A`, `0x0042ACAA`, `0x0042AD9A`)
- **Analyse du désassemblage** :
  - Toutes les boucles de hachage `seed = 0x12345678` de `picasa3.exe` lisent chaque octet de la chaîne UTF-8 dans un registre 8 bits `cl`, puis le convertissent en 32 bits avec **extension de signe** (`movsx ecx, cl`) avant de l'additionner :
    ```asm
    movsx ecx, cl        ; octet >= 0x80 devient négatif (0xFFFFFF80..0xFFFFFFFF) !
    mov edx, esi
    shl edx, 5
    shr esi, 2
    add edx, ecx
    add esi, edx
    ```
  - Ainsi, tout caractère non-ASCII (par exemple un caractère accentué UTF-8 `é` = `0xC3 0xA9`) est traité comme une séquence d'entiers **négatifs** (`-61`, `-87`) qui sont soustraits du hash au lieu d'y être ajoutés comme des octets non signés (`195`, `169`).
- **Pourquoi `PyCasa` DOIT conserver ce comportement à l'identique** :
  - Ce hash constitue la colonne `checksums` de `thumbs_index.db`, `thumbs2_index.db`, `bigthumbs_index.db` et `previews_index.db`.
  - Si `PyCasa` utilisait des octets non signés (`0..255`), le checksum de **toutes les photos situées dans un dossier contenant un accent** (`C:\Photos\Été\`, `Noël.jpg`, etc.) ou possédant une légende accentuée serait considéré comme **invalide** par `picasa3.exe`, provoquant la destruction et la régénération complète de toutes les miniatures à chaque ouverture !
  - Ce comportement est reproduit bit-à-bit dans [`hash_picasa_string`](../../picasa_py/db/blockfile.py) et [`hash_picasa_string_case_sensitive`](../../picasa_py/db/blockfile.py).

---

### 7. Paramètre `sharpness` câblé en dur à `0.0f` dans le filtre `Soft Focus` (`radblur`)
- **Localisation dans `picasa3.exe`** :
  - Fonction : `radblur` (`FUN_008f8520` @ `0x008F8520`, appel à `0x008F8645` vers `0x0090B050` -> `0x0090AEB0`)
- **Analyse du désassemblage** :
  - La routine de génération de masque radial `0x0090AEB0(size, sharpness)` (partagée entre `Focal B&W` / `radsat` et `Soft Focus` / `radblur`) accepte deux flottants : le rayon `size` et la netteté de transition `sharpness`.
  - Alors que `radsat` (`0x008F8680`) lui transmet bien ses deux curseurs, `radblur` (`0x008F8645`) empile `0.0f` (`xorps xmm0, xmm0`) pour `sharpness` et utilise son 2e curseur (`amount`) uniquement pour faire varier le rayon du flou gaussien (`r_blur = 0.01 * w * (1 + amount) + 0.001`).
- **Pourquoi `PyCasa` DOIT conserver ce comportement à l'identique** :
  - Pour qu'une photo retouchée avec `radblur=1,<size>,<amount>;` dans `.picasa.ini` ait un rendu **identique au pixel près** dans `picasa3.exe` et dans `PyCasa` ([`PicasaImageProcessor.soft_focus`](../../picasa_py/ui/image_processor.py)).

---

## Tableau récapitulatif

| # | Sous-système | Adresse Ghidra | Nature du bug original | Action dans `PyCasa` | Justification |
|---|---|---|---|---|---|
| **1** | `.picasa.ini` / `backuphash` | `0x00429CA0`, `0x00429D57` | `backuphash` (XOR de la date OLE) calculé et écrit **2 fois de suite** | **Corrigé** (écrit 1 seule fois) | Évite une double écriture disque inutile ; valeur 16 bits 100 % identique. |
| **2** | `SyncIniToDB` (`crop` + `backuphash`) | `0x00459DE3 -> 0x00459E21` | `fallthrough` écrasant `imagedata_crop64 = 0` si `backuphash=` est présent sans `filters=` | **Corrigé** (en lecture + injection de `filters=crop64=1,...;` en écriture) | Empêche toute perte de recadrage dans `PyCasa` **et** protège `picasa3.exe` contre son propre bug. |
| **3** | `SyncIniToDB` (`screensaver=`) | `0x00458F9B` | Ignore la valeur à droite de `=` (même `no`/`0` active `]screensaver`) | **Corrigé** (`no`/`0`/`false`/vide retire `]screensaver`) | Compatible avec `screensaver=yes` de `picasa3.exe` tout en permettant la désactivation propre. |
| **4** | `SaveThumbIndex` (`thumbindex.db`) | `0x004F56BA` | Vérifie le type du parent uniquement pour `type == 4` (oublie `2, 7, 1001`) | **Corrigé** (`sanitize_records` en 2 passes sur tous les types) | Purges propres des enfants et visages `1001` orphelins sans décaler les index `.pmp`. |
| **5** | `Red.dll` (`dqc_Relator::init`) | `0x101007F8..0x10100856` | Troncature `float32` (`12` au lieu de `12.5`) + pointeur `edi` non incrémenté dans la moyenne par 8 | **Conservé bit-à-bit** | Obligatoire pour que les embeddings `facetemplatesV2_0.db` et distances faciales soient identiques. |
| **6** | Checksums `CBlockFile` | `0x006B9A60`, `0x0042A96A` | Extension de signe `movsx ecx, cl` rendant négatifs les octets UTF-8 `>= 0x80` | **Conservé bit-à-bit** | Obligatoire pour que `picasa3.exe` ne rejette pas les miniatures des chemins accentués. |
| **7** | Filtre `Soft Focus` (`radblur`) | `0x008F8645` | `sharpness` câblé en dur à `0.0f` dans l'appel au masque radial `0x0090AEB0` | **Conservé au pixel près** | Obligatoire pour que le rendu de `radblur=1,...` soit identique au pixel près entre les deux apps. |
