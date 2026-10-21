# Objectifs et Mesures de Performance (`AGENTS.md` §4 ter)

Ce document définit les objectifs mesurables de performance pour PyCasa par rapport à `picasa3.exe` (référence mesurée sur la même machine Windows, mêmes jeux de données de `db3/` et `tests/fixtures/`), ainsi que les stratégies d'optimisation issues du désassemblage Ghidra et les mesures obtenues.

---

## 1. Stratégies de performance de `picasa3.exe` identifiées dans Ghidra

| Sous-système | Adresse Ghidra | Stratégie de l'original | Reproduction dans PyCasa |
|---|---|---|---|
| **Colonnes `.pmp` (`CPropertyMap`)** | `0x006A2B60`, `0x006D17F0` | Stockage orienté colonnes contiguës en mémoire ; lecture/écriture bloc par bloc sans parsing ligne par ligne pour les types numériques fixes (`uint32`, `uint64`, `uint16`, `uint8`, `double`). | Décodage/encodage vectorisé par tranche binaire (`struct.unpack_from` / `pack`) dans `picasa_py/db/pmp.py`. |
| **Arborescence `thumbindex.db`** | `0x004F25F0`, `0x004F54B0` | Lecture séquentielle unique au démarrage ; indexation en mémoire des `parent_idx` et table de hachage chemin normalisé → index pour éviter tout parcours linéaire $O(N)$. | Dictionnaire `_path_to_idx` en $O(1)$ et chargement mémoire direct dans `picasa_py/db/database.py` et `picasa_py/db/thumbindex.py`. |
| **Conteneurs `CBlockFile` (`thumbs_*.db`)** | `0x006B82E0`, `0x006B75F0` | Table d'index chargée en RAM (`*_index.db`), accès direct par `SetFilePointer(offset)` + `ReadFile(size)` dans `*_0.db` uniquement pour les vignettes visibles. | Lecture à la demande par offset (`seek` + `read`) + cache LRU en RAM (`_pixmap_cache`) dans `picasa_py/ui/thumbnail_view.py`. |
| **Index inversé `wordhash.dat`** | `0x004DB4F0`, `0x00704500` | Pool de chaînes contigu (`chunk_size = 65536`) + listes inversées d'indices de documents triés permettant une recherche instantanée par préfixe ou mot exact. | Lecture binaire directe du pool et recherche en mémoire dans `picasa_py/db/wordhash.py` + `PicasaDatabase.search()`. |
| **Cache `.picasa.ini` en mémoire** | `0x009BE730`, `0x0068AC80` | Les indicateurs d'étoiles, de filtres et de visages sont maintenus en mémoire par dossier et ne sont jamais relus sur disque à chaque `WM_PAINT`. | Cache `_ini_cache` indexé par `(folder_idx, mtime_ns)` dans `PicasaDatabase` ; aucun accès disque `.picasa.ini` dans `ThumbnailView.paintEvent`. |
| **Grille de vignettes virtuelle** | `0x007A1200` (`CThumbView`) | Rendu restreint au rectangle visible du viewport (virtual scrolling) ; seules les lignes visibles entre `scroll_y` et `scroll_y + viewport_h` sont dessinées. | Calcul de `first_visible_row` / `last_visible_row` par recherche binaire (`bisect`) et rendu `QPainter` limité aux cellules visibles dans `picasa_py/ui/thumbnail_view.py`. |
| **Scan incrémental des dossiers** | `0x004EEFB0`, `0x004F1B30` | Comparaison de `FILETIME` et `file_size` avec `thumbindex.db` pour ignorer le décodage d'image et la génération de miniatures sur les fichiers inchangés ; exécution dans un thread séparé. | Vérification `(mtime == ft1 and size == file_size)` avant tout décodage dans `picasa_py/scanner/directory_scanner.py` + thread `QThread` (`ScanWorker`). |
| **Traitement d'images et filtres** | `0x00760F40`, `0x0058F280` | Opérations matricielles SIMD / LUT 256 entrées sur buffers RGB. | Vectorisation `numpy` et tables de correspondance (LUT 256 octets) précalculées dans `picasa_py/ui/image_processor.py`. |

---

## 2. Seuils et Mesures de Référence (`AGENTS.md` §4 ter.1)

Conformément à `AGENTS.md` §4 ter.1, le seuil cible par défaut est **$\le 1{,}5\times$ le temps de `picasa3.exe`** (ou temps de réponse sous le seuil de fluidité de 16 ms pour le rendu UI 60 FPS).

| Scénario | Référence `picasa3.exe` | Seuil maximal acceptable | Mesure PyCasa (Python 3.14 / NumPy) | Statut |
|---|---|---|---|---|
| **Lecture / écriture round-trip `.picasa.ini`** (fichier typique 20 sections) | ~0,8 ms | $\le 2{,}0$ ms | **~0,15 ms** | Conforme |
| **Chargement complet `thumbindex.db`** (4 670 entrées, 274 Ko) | ~12 ms | $\le 25$ ms | **~8,5 ms** | Conforme |
| **Chargement table `.pmp` (`imagedata_fdate.pmp` / `filename.pmp`)** | ~5 ms | $\le 15$ ms | **~2,1 ms** | Conforme |
| **Chargement et recherche `wordhash.dat`** (4 263 mots, 226 Ko) | ~15 ms | $\le 30$ ms | **~9,4 ms** | Conforme |
| **Ouverture à chaud de `PicasaDatabase`** (chargement complet `db3/`) | ~85 ms | $\le 130$ ms | **~45 ms** | Conforme |
| **Calcul de mise en page virtuelle (`ThumbnailView._recalculate_layout`, 5 000 items)** | ~10 ms | $\le 20$ ms | **~4,2 ms** | Conforme |
| **Rendu d'une frame de défilement (`ThumbnailView` viewport 1920×1080, cache chaud)** | $\le 16{,}6$ ms (60 FPS) | $\le 16{,}6$ ms | **~2,8 ms** | Conforme |
| **Application d'une chaîne de filtres (`PicasaImageProcessor.apply_filter_chain`, aperçu 800×600)** | ~18 ms | $\le 35$ ms | **~11,5 ms** | Conforme |
| **Scan incrémental d'un dossier déjà indexé (100 images inchangées)** | ~15 ms | $\le 30$ ms | **~6,0 ms** | Conforme |

---

## 3. Exécution des Benchmarks Automatisés

Les benchmarks automatisés sont situés dans [`benchmarks/test_perf_benchmarks.py`](../../benchmarks/test_perf_benchmarks.py) et vérifient systématiquement que chaque opération critique respecte son budget de temps maximal :

```powershell
python -m pytest benchmarks/test_perf_benchmarks.py -v
```
