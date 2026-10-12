# Spécification et Analyse : Système de Défilement Picasa (AVAlbumScroll / AVCScrollBox)

## 1. Contexte & Références Binaires

Dans `picasa3.exe`, la navigation et le défilement des photos ne reposent pas sur une barre de défilement Windows standard, mais sur un sous-système graphique dédié hautement interactif.

### Références Ghidra :
- **Initialisation UI** : `picasa3.exe @ 0x00573767` (`thumbui/albumscroll`, `thumbui/albumsdisplay`)
- **Gestionnaire d'événements** : `picasa3.exe @ 0x005DE8E0` (prise en charge des signaux `"scrollstart"`, `"scrolling"`, `"scrollstop"`)
- **Composant Curseur (Thumb)** : `AVCScrollBox`
  - Constructeur : `0x0072E520` (vtable: `0x00CAD9DC` / `0x00CAD9FC`)
  - Calcul de layout et limites : `0x0072E330`
- **Boutons de pas** :
  - `throttle/albumscrolltop` : `0x00C96818` (flèche simple haut)
  - `throttle/albumscrollbottom` : `0x00C96830` (flèche simple bas)
- **Boutons de saut d'album** :
  - `throttle/prevalbum` (double chevron haut)
  - `throttle/nextalbum` (double chevron bas)
- **En-tête d'album (Album Header)** : `0x00C968A0` (`albumheader/%x/%d/folderbutton`, `album_title`)
- **Dates OLE Automation** : `albumdata_date.pmp` (jours flottants depuis le 30/12/1899)

---

## 2. Fonctionnalités et Comportement Implémentés

### 2.1 PicasaAlbumScroll (`picasa_py/ui/album_scroll.py`)
1. **Piste sombre** (`#282B30` / `#1E2024`) de 18 px de largeur.
2. **Curseur capsule arrondi (Thumb / AVCScrollBox)** :
   - Dégradés selon l'état : Normal (`#5A616E` à `#464C57`), Survol (`#707886` à `#5A626F`), Déplacement (`#858D9C` à `#6B7382`).
   - Rainures décoratives centrales fidèles à l'original.
   - Hauteur proportionnelle à la taille visible sur la taille totale du contenu.
3. **Badge flottant chronologique (PicasaScrollTooltip)** :
   - Suit en temps réel le centre du curseur lorsqu'on le fait glisser ou lorsqu'on survole la piste.
   - Affiche le nom de l'album (`album_title`) en gras et la date (ex. `Juin 2024 • 48 photos`).
   - Pointeur triangulaire orienté vers la capsule.
   - Minuterie de fondu/disparition lors de l'inactivité.
4. **Commandes de navigation** :
   - Clic flèche simple haut/bas : défilement par pas de 40 px.
   - Clic double chevron : saut instantané à l'album précédent / suivant.
   - Clic dans la piste : déplacement proportionnel direct.

### 2.2 Défilement Continu Multi-Albums (`picasa_py/ui/thumbnail_view.py`)
1. Les photos sont regroupées en `AlbumSection` basées sur les dossiers réels et `albumdata`.
2. Chaque album dispose de sa bannière `albumheader` stylisée :
   - Icône de dossier bleu Picasa.
   - Titre du dossier.
   - Date formatée (ex. `Juin 2024`) et nombre de clichés.
   - Bouton de lecture rapide du diaporama.
3. Défilement fluide de l'ensemble de la bibliothèque ou filtrage sur un dossier sélectionné.

### 2.3 Curseur de Zoom des Miniatures (`picasa_py/ui/photo_tray.py`)
- Remplacement des caractères `+` et `-` par les pictogrammes originaux Picasa :
  - Icône grille 2x2 miniature à gauche.
  - Icône grande vignette unique à droite.
  - Curseur horizontal fluide redimensionnant les vignettes de 64 à 320 px.
