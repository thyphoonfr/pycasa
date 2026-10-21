# AGENTS.md — Portage de picasa3.exe vers Python (via Ghidra)

Ce fichier définit les règles de travail pour tout agent (humain ou IA) intervenant sur ce projet.
Il est prioritaire sur toute habitude ou supposition personnelle.

---

## 1. Objectif du projet

Produire une implémentation Python de `picasa3.exe` dont le comportement est **fonctionnellement équivalent** à l'original, avec deux exigences non négociables :

1. **Compatibilité totale de la base de données** : la version Python lit et écrit les fichiers de base de données de Picasa 3 (index, miniatures, métadonnées, contacts, etc.) dans un format **binaire identique**, de sorte que `picasa3.exe` et la version Python puissent travailler **alternativement sur les mêmes données** sans corruption, perte ou ré-indexation forcée.
2. **Compatibilité totale des fichiers `.ini`** : lecture, interprétation, écriture, ordre des sections/clés, encodage, fins de ligne, casse, espaces et valeurs par défaut doivent être strictement identiques à ceux de l'original.

3. **Fidélité de l'interface** : l'interface Python reproduit **au plus près** celle de `picasa3.exe`, à la fois dans sa **disposition** (fenêtres, panneaux, barres, menus, boîtes de dialogue, dimensions, espacements, couleurs, icônes, textes) et dans son **fonctionnement** (interactions, raccourcis, états, enchaînements, réactions aux erreurs).

4. **Performances comparables à l'original** : la version Python doit offrir une **réactivité et un débit proches de `picasa3.exe`** (démarrage, indexation, navigation, affichage des vignettes, défilement, ouverture d'images, recherche, consommation mémoire). Une version fidèle mais lente est considérée comme **non conforme**.

Ces quatre exigences sont prioritaires. Le reste (architecture interne, choix de bibliothèques) est secondaire tant qu'il ne les compromet pas. En cas de conflit, la compatibilité des données (points 1 et 2) prime toujours : on n'optimise jamais en sacrifiant la fidélité des fichiers.

---

## 2. Règle d'or : le désassemblage est la seule source de vérité

> **Le comportement de `picasa3.exe` est établi exclusivement par l'analyse du binaire dans Ghidra.**

### 2.1 Ce qui est autorisé comme source
- Le désassemblage et la décompilation Ghidra de `picasa3.exe` et de ses DLL embarquées/chargées.
- L'observation **statique** des chaînes, tables, ressources, constantes et structures présentes dans le binaire.
- Les **ressources PE** du binaire (menus, boîtes de dialogue, accélérateurs, tables de chaînes, bitmaps, icônes, curseurs, versions) extraites telles quelles.
- Les **captures d'écran de `picasa3.exe` en cours d'exécution**, uniquement pour *vérifier* une disposition ou un comportement déjà compris par le désassemblage (jamais comme source de spécification à elles seules).
- Les **fichiers réels produits par `picasa3.exe`** (bases, `.ini`) utilisés comme jeux de test de référence pour *vérifier* une hypothèse issue du désassemblage.
- L'analyse dynamique (débogueur, traces) uniquement pour **confirmer** ce que le désassemblage indique.

### 2.2 Ce qui est interdit comme source
- Documentation, blogs, forums, wikis, dépôts tiers ou code existant décrivant le format Picasa.
- Souvenirs ou connaissances « générales » sur le format des fichiers Picasa.
- Devinettes, extrapolations ou « ça doit être comme ça ».
- Rétro-ingénierie d'autres versions de Picasa non fournies explicitement dans le projet.

### 2.3 Conséquence pratique
Toute connaissance préalable (y compris celle de l'agent) est au mieux une **hypothèse de travail**. Elle ne peut entrer dans le code que **après confirmation dans le désassemblage**, avec la référence correspondante (voir §5).

Si le désassemblage ne permet pas de conclure : **on ne devine pas**. On documente le point comme « non résolu » (§8) et on continue l'analyse.

---

## 3. Compatibilité base de données

### 3.1 Exigences
- Format binaire reproduit **octet pour octet** : en-têtes, magic numbers, versions, endianness, alignements, padding, tailles de champs, tables d'index, checksums/CRC, compression éventuelle.
- Un fichier écrit par Python doit être relu sans erreur ni réparation par `picasa3.exe`, et inversement.
- Les opérations d'écriture doivent reproduire les mêmes effets de bord que l'original : ordre d'écriture, fichiers temporaires, verrous, renommages atomiques, mises à jour d'index.
- Le comportement face aux données **invalides, tronquées ou de version inconnue** doit être celui de l'original (rejet, réparation, reconstruction), tel qu'établi dans le code désassemblé.
- Aucune « amélioration » du format, aucune migration, aucun nouveau champ.

### 3.2 Méthode
1. Localiser dans Ghidra les fonctions d'ouverture, lecture, écriture et fermeture de chaque fichier de base (via les appels `CreateFile`, `ReadFile`, `WriteFile`, `SetFilePointer`, `MapViewOfFile`, etc., et leurs références croisées).
2. Reconstruire les structures (types Ghidra `struct`) champ par champ, puis les transcrire en Python (`struct`, `dataclasses`).
3. Documenter chaque format dans `docs/formats/` (spécification dérivée **uniquement** du binaire, voir §5).
4. Écrire un **test aller-retour** : `lire(fichier_original) -> écrire` doit redonner un fichier **identique au bit près** (sauf champs volatils explicitement identifiés, comme horodatages, avec justification).

---

## 4. Compatibilité fichiers `.ini`

### 4.1 Exigences
- Reproduire le **parseur exact** de l'original : gestion des commentaires, lignes vides, espaces autour de `=`, guillemets, séquences d'échappement, doublons de clés/sections, sensibilité à la casse, limites de longueur.
- Reproduire le **writer exact** : ordre des sections et des clés, séparateurs, fins de ligne (`\r\n` vs `\n`), BOM éventuel, encodage (ANSI / UTF-8 / UTF-16, code page), format des nombres, des flottants, des dates et des listes.
- Reproduire les **valeurs par défaut** et le comportement lorsque une clé est absente, vide ou malformée.
- **Ne pas utiliser `configparser`** ni une bibliothèque INI générique, sauf si un test prouve une équivalence stricte avec le comportement désassemblé. Par défaut, écrire un parseur/writer dédié.
- Les clés/sections **inconnues** doivent être préservées à l'identique (round-trip sans perte), sauf si l'original les supprime — ce qui doit alors être reproduit.

### 4.2 Méthode
1. Identifier dans Ghidra les routines de lecture/écriture INI (ex. appels à `GetPrivateProfile*` / `WritePrivateProfile*` ou parseurs maison), ainsi que toutes les chaînes de noms de sections/clés.
2. Dresser l'inventaire exhaustif des sections/clés avec : type, valeur par défaut, adresse de la fonction qui les lit et celle qui les écrit.
3. Tester par **diff binaire** sur des corpus de `.ini` réels produits par `picasa3.exe`.

---

## 4 bis. Fidélité de l'interface (disposition et fonctionnement)

### 4 bis.1 Exigences
- **Disposition identique** : hiérarchie des fenêtres, position et taille de chaque panneau, barre d'outils, barre d'état, menus (ordre, séparateurs, libellés, mnémoniques), boîtes de dialogue (position et taille de chaque contrôle, ordre de tabulation), polices, couleurs, icônes, marges, comportement au redimensionnement (ancrages, minimums, séparateurs).
- **Fonctionnement identique** : clic simple/double/droit, glisser-déposer, sélection multiple, survol, info-bulles, menus contextuels, raccourcis clavier, molette, défilement, zoom, animations et transitions, états activé/désactivé des commandes, enchaînement des écrans, messages d'erreur et confirmations.
- **Textes identiques** : libellés, messages et formats (dates, nombres, pluriels) repris des tables de chaînes du binaire, avec gestion des langues telle que l'original la fait.
- **Rendu personnalisé** : si l'original dessine lui-même ses contrôles (rendu GDI/GDI+ ou autre), la version Python doit reproduire ce dessin (tracé, dégradés, ombres, anticrénelage raisonnablement équivalent) plutôt que d'utiliser des contrôles natifs « proches ».
- **Persistance de l'état de l'interface** (positions de fenêtres, préférences, dernier dossier, vues) lue et écrite dans les mêmes emplacements et formats que l'original, conformément à §3 et §4.
- Aucune « amélioration » ergonomique, aucun nouveau menu, aucun changement de style : ce qui est perçu comme un défaut dans l'original est reproduit.

### 4 bis.2 Méthode
1. **Extraire les ressources PE** (menus, dialogues, chaînes, bitmaps, icônes) et les versionner sous `ui/resources/` sans modification. Documenter l'identifiant de chaque ressource et l'adresse du code qui la charge.
2. **Retrouver la logique d'interface dans Ghidra** : fenêtre principale, procédures de fenêtre (`WndProc`, `DialogProc`), tables de messages `WM_*`, gestion de `WM_COMMAND`, `WM_PAINT`, `WM_SIZE`, `WM_LBUTTONDOWN`, `WM_KEYDOWN`, minuteries, etc. Chaque commande d'interface est reliée à la fonction qui l'exécute.
3. **Reconstruire le modèle de mise en page** : constantes de dimensions, calculs de layout au redimensionnement, tailles de vignettes, espacements, règles de défilement, tels qu'ils apparaissent dans le code désassemblé.
4. **Cartographier le fonctionnement** : machine à états de chaque écran/mode, conditions d'activation des commandes, effets de chaque action. Documenter dans `docs/ui/` (un fichier par fenêtre/dialogue/mode).
5. **Comparer visuellement** : captures de l'original et de la version Python à résolution et état identiques, puis comparaison (diff d'images avec tolérance documentée).

### 4 bis.3 Choix de la bibliothèque graphique
- Le toolkit (Qt/PySide6, wxPython, Tkinter, rendu maison, etc.) est choisi **uniquement** sur sa capacité à reproduire la disposition et le dessin de l'original au pixel près ; le choix est justifié dans `docs/ui/toolkit.md`.
- Si le toolkit impose des différences (polices, rendu, DPI), elles sont listées comme écarts connus avec leur ampleur.
- L'interface est séparée de la logique : la couche UI n'écrit jamais directement dans la base ou les `.ini`, elle passe par les modules `db/` et `ini/` validés (§3 et §4).

---

## 4 ter. Performances

### 4 ter.1 Exigences
- **Objectifs mesurables** : pour chaque scénario clé, on définit une référence mesurée sur `picasa3.exe` (même machine, mêmes données), puis un seuil acceptable pour la version Python (par défaut : pas plus de 1,5× le temps de l'original, à affiner par scénario dans `docs/perf/targets.md`).
- **Scénarios à couvrir au minimum** :
  - démarrage à froid et à chaud ;
  - indexation / scan initial d'une photothèque (petite, moyenne, très grande : 100 000+ images) ;
  - ouverture d'un dossier et affichage des vignettes ;
  - défilement fluide dans une grande grille de vignettes ;
  - ouverture d'une image, zoom, passage à l'image suivante ;
  - recherche, tri, filtrage ;
  - lecture/écriture de la base et des `.ini` (débit, latence) ;
  - consommation mémoire et utilisation CPU/disque au repos et en charge.
- **Fluidité de l'interface** : le thread d'interface ne doit jamais être bloqué par des opérations longues (I/O, décodage, indexation). Les temps de réponse perçus doivent rester équivalents à l'original.
- **Comportement I/O fidèle et efficace** : reproduire les stratégies de l'original constatées dans le désassemblage (lecture par blocs, mapping mémoire, cache, écritures différées, verrouillage) lorsqu'elles expliquent ses performances, sans jamais changer ce qui est écrit sur disque.

### 4 ter.2 Méthode
1. **Comprendre pourquoi l'original est rapide** : repérer dans Ghidra les caches, tables d'index, structures en mémoire, pools de threads, files de travail, chargements différés et optimisations (précalcul de miniatures, lecture séquentielle de l'index, etc.). Documenter dans `docs/perf/`.
2. **Mesurer avant d'optimiser** : profilage (`cProfile`, `py-spy`, `tracemalloc`, profileurs de mémoire) sur des jeux de données de référence ; aucune optimisation sans mesure avant/après.
3. **Optimiser par ordre d'impact** : algorithmes et structures de données d'abord, puis parallélisme (threads/processus pour l'I/O et le décodage d'images), puis accélération native des chemins chauds (`numpy`, `Cython`, `cffi`, extensions en C/Rust, bibliothèques d'imagerie rapides).
4. **Chemins chauds natifs si nécessaire** : si Python pur ne tient pas les objectifs, les parties critiques (décodage/redimensionnement d'images, parsing binaire en masse, indexation) peuvent être implémentées en extension native, à condition de rester **strictement équivalentes** (mêmes tests round-trip, §7) et de conserver la référence au désassemblage (§5).
5. **Surveiller les régressions** : benchmarks automatisés en CI (`pytest-benchmark` ou équivalent) avec seuils ; toute régression au-delà du seuil fait échouer la CI.

### 4 ter.3 Garde-fous
- Une optimisation ne doit **jamais** modifier le format ni le contenu des fichiers produits (§3, §4) ni le comportement visible (§4 bis).
- Pas de cache persistant ni de fichier supplémentaire qui ne serait pas présent dans l'original, sauf s'il est invisible pour `picasa3.exe` et explicitement approuvé et documenté (risque d'incompatibilité : à éviter par défaut).
- Les gains de performance sont consignés avec leur mesure (avant/après, machine, jeu de données) dans `docs/perf/`.

---

## 5. Traçabilité obligatoire

Chaque comportement implémenté en Python doit pouvoir être relié au binaire.

- Chaque fonction/classe issue de l'analyse porte un commentaire de référence :
  ```python
  # Ref: picasa3.exe @ 0x004A1F30 (FUN_004a1f30 -> read_folder_ini)
  # Ghidra project: ghidra/picasa3.gpr, revision: <hash ou date>
  ```
- Chaque spécification dans `docs/` indique : adresses, noms Ghidra attribués, niveau de confiance (confirmé / probable / hypothèse).
- Le projet Ghidra (`.gpr` / export `.gzf`) est versionné ou archivé : renommages, types, commentaires et structures font partie du livrable.
- Les noms de fonctions Ghidra sont renommés de façon explicite dès qu'elles sont comprises (`FUN_xxx` -> nom parlant), avec commentaire.

---

## 6. Organisation recommandée

```
.
├── AGENTS.md
├── ghidra/                 # projet Ghidra, exports, scripts d'analyse
│   └── scripts/            # scripts Ghidra (Python/Java) d'extraction
├── docs/
│   ├── formats/            # spécifications dérivées du binaire (DB, INI)
│   ├── analysis/           # notes d'analyse par fonction/module
│   ├── ui/                 # spécification de l'interface (fenêtres, dialogues, modes)
│   ├── perf/               # objectifs, mesures et analyses de performance
│   └── open-questions.md   # points non résolus (§8)
├── benchmarks/             # scénarios et jeux de données de performance
├── ui/
│   └── resources/          # ressources PE extraites, non modifiées
├── picasa_py/              # code Python du portage
│   ├── db/                 # lecture/écriture bases
│   ├── ini/                # parseur/writer INI dédié
│   ├── ui/                 # interface (séparée de la logique)
│   └── ...
├── tests/
│   ├── fixtures/           # fichiers réels de référence (non modifiés)
│   ├── test_roundtrip_*.py # aller-retour octet pour octet
│   └── test_interop_*.py   # cohérence avec picasa3.exe
└── tools/                  # outils de comparaison (diff binaire, dump)
```

---

## 7. Stratégie de validation

Aucune fonctionnalité n'est considérée « terminée » sans ces preuves :

1. **Round-trip** : lecture puis réécriture identique au bit près sur tous les fichiers de référence.
2. **Interopérabilité croisée** :
   - fichiers créés par Python -> ouverts et modifiés par `picasa3.exe` sans erreur ;
   - fichiers créés par `picasa3.exe` -> ouverts et modifiés par Python sans erreur ;
   - alternance répétée Python / Picasa sur les mêmes données sans dérive.
3. **Tests différentiels** : mêmes entrées, comparaison des sorties (octets) entre l'original et la version Python.
4. **Cas limites** : fichiers vides, tronqués, corrompus, versions inconnues, chemins Unicode/longs, très gros volumes — comportement conforme à l'original.
5. **Interface** : pour chaque fenêtre/dialogue/mode, comparaison de captures (original vs Python) à même résolution, DPI et état, avec écart documenté et tolérance explicite ; scénarios d'interaction rejoués sur les deux versions (menus, raccourcis, glisser-déposer, redimensionnement) avec résultats identiques.
6. **Performances** : benchmarks exécutés sur chaque scénario de §4 ter, comparés à la mesure de référence de `picasa3.exe` ; résultats (temps, mémoire, CPU) archivés ; tout dépassement des seuils est un défaut bloquant au même titre qu'un test fonctionnel qui échoue. Toute optimisation repasse l'intégralité des tests round-trip et d'interopérabilité.
7. Les fixtures de référence sont **en lecture seule** ; ne jamais les écraser ni les « corriger ».

Tout écart (même un octet) est un **bug** jusqu'à preuve, dans le désassemblage, qu'il s'agit d'un champ volatil légitime.

---

## 8. Gestion de l'incertitude

- Tout point non confirmé par le désassemblage est consigné dans `docs/open-questions.md` avec : l'hypothèse, les adresses concernées, ce qui manque pour conclure.
- Dans le code, un comportement non confirmé est marqué `# TODO(unverified)` et **ne doit pas** être présenté comme fiable.
- En cas de doute, privilégier la **préservation à l'identique** des données (ne rien modifier, ne rien supprimer) plutôt qu'une interprétation risquée.
- Ne jamais « combler les trous » par du code plausible.

---

## 9. Règles de contribution pour les agents

1. **Analyser avant de coder** : pas de code sans référence Ghidra correspondante.
2. **Petits incréments** : un format ou une fonction à la fois, avec son test round-trip.
3. **Ne jamais modifier** le binaire d'origine ni les fixtures.
4. **Ne pas réécrire pour « moderniser »** : reproduire fidèlement, y compris les quirks et bugs de l'original lorsqu'ils influencent les fichiers produits.
5. **Pas de dépendance** qui changerait le comportement bas niveau (sérialisation, parsing, arrondis, encodage) sans test d'équivalence.
6. **Documenter** chaque découverte (adresses, structures, constantes) au moment où elle est faite.
7. Signaler explicitement toute divergence connue entre la version Python et l'original, y compris les écarts de performance.
8. **Mesurer, ne pas supposer** : aucune affirmation « c'est assez rapide » ou « c'est plus rapide » sans benchmark ; ne pas optimiser prématurément, mais ne pas livrer de chemin chaud non mesuré.
9. Données personnelles : les fichiers de test issus de vraies photothèques doivent être anonymisés ou non versionnés publiquement.
10. **Gestion stricte du numéro de version (`z.y.x.w` dans `picasa_py/version.py`)** :
    - Le numéro de version de PyCasa suit le format **`z.y.x.w`** (défini dans `picasa_py/version.py` et synchronisé dans `pyproject.toml`) :
      - **`z` et `y`** (ex. `3.9`) : **réservés exclusivement à l'utilisateur**. Aucun agent ne doit jamais modifier `z` ou `y` sans demande explicite de l'utilisateur.
      - **`x`** (initialisé à `145`) : incrémenté à chaque **demande d'ajout de fonctionnalité**.
      - **`w`** : incrémenté à **chaque changement dans le code** (correction, ajustement, refactoring ou modification quelconque du code).

---

## 10. Stack technique

- **Analyse** : Ghidra (décompileur + désassembleur), scripts Ghidra pour l'export de structures, chaînes et références croisées. Optionnel : débogueur (x64dbg/WinDbg) pour confirmer dynamiquement.
- **Implémentation** : Python 3.11+, typage statique (`mypy`), `struct`/`dataclasses` pour les formats binaires, `pytest` pour les tests.
- **Performance** : profilage (`cProfile`, `py-spy`, `tracemalloc`), benchmarks (`pytest-benchmark`), concurrence (`concurrent.futures`, `multiprocessing`, `asyncio` si pertinent), accélération native au besoin (`numpy`, `Cython`, `cffi`, extensions C/Rust, bibliothèques d'imagerie rapides).
- **Qualité** : formatage (`ruff`/`black`), CI exécutant tous les tests round-trip, différentiels et benchmarks.

---

## 11. Critères de réussite

Le projet est réussi lorsque :
- toute donnée (base + `.ini`) produite par l'une des deux versions est utilisable à l'identique par l'autre ;
- l'interface Python est indiscernable de l'original en disposition et en fonctionnement, hors écarts documentés ;
- les performances respectent les seuils définis par rapport à `picasa3.exe` sur tous les scénarios clés ;
- chaque comportement du code Python est justifié par une référence au désassemblage ;
- aucun test round-trip ou différentiel n'échoue ;
- les points non résolus sont explicitement documentés, jamais masqués.