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

### 2.1 Manette des gaz / Jog-Shuttle (`AVCScrollThrottle` dans `picasa_py/ui/album_scroll.py`)
1. **Curseur centré au repos (Point mort central)** :
   - Le curseur (capsule métallique de 14x28 px) reste calé au centre vertical de la piste au repos (`rest_thumb_y`), face à un repère neutre horizontal.
2. **Accélération proportionnelle et non-linéaire** :
   - **Glisser vers le bas** : défilement avant dans le temps (vitesse positive).
   - **Glisser vers le haut** : défilement arrière dans le temps (vitesse négative).
   - Plus on écarte le curseur du centre, plus la vitesse croît rapidement (combinaison linéaire, quadratique et cubique : contrôle très fin à faible écartement, balayage à haute vitesse à pleine déviation).
   - Zone morte centrale de 3 px pour éviter toute dérive involontaire.
   - Ruban indicateur de tension lumineux bleu reliant le point mort au curseur pour matérialiser visuellement la puissance du défilement.
3. **Retour élastique automatique (Spring-back)** :
   - Dès le relâchement du bouton de la souris, une animation 60 FPS ramène immédiatement et avec souplesse le curseur à sa position centrale neutre, stoppant le défilement.
4. **Badge flottant chronologique (PicasaScrollTooltip)** :
   - Suit en temps réel le curseur pendant le throttle, affichant le dossier en cours de survol et sa date.
   - S'estompe avec une temporisation d'inactivité après relâchement.
5. **Commandes de pas et de saut** :
   - Clic flèches simples : défilement pas à pas (60 px).
   - Clic doubles chevrons (`prevalbum`, `nextalbum`) : saut direct à l'en-tête de l'album précédent / suivant.

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
