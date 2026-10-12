# Choix du Toolkit Graphique pour PyCasa

Conformément à la section **4 bis.3** de `AGENTS.md` :
> « Le toolkit (Qt/PySide6, wxPython, Tkinter, rendu maison, etc.) est choisi uniquement sur sa capacité à reproduire la disposition et le dessin de l'original au pixel près ; le choix est justifié dans `docs/ui/toolkit.md`. »

---

## 1. Analyse des besoins de reproduction de `Picasa3.exe`

L'interface de Picasa 3 présente les spécificités suivantes, identifiées dans le binaire désassemblé et ses ressources (`constants.ui`, `respack.yt`, `SHORTCUTS.XML`) :

1. **Rendu sur-mesure (Custom Owner-Drawn controls)** :
   - Picasa 3 ne se repose pas sur les contrôles Win32 standard (boutons ronds avec dégradés métalliques, barre de recherche biseautée avec loupe, curseur de zoom rotatif/glissant, badges d'albums, en-têtes de dossiers stylisés avec boutons d'actions inline).
   - Les vignettes dans la grille comportent des ombres portées, bordures blanches de sélection (`thumbsel_color1=#009EFF`, `thumbsel_color2=#FFFFFF`), étoiles de favoris superposées, icônes de détection faciale.

2. **Grille de vignettes haute performance (Fluidité de défilement)** :
   - Capacité à faire défiler plusieurs dizaines de milliers de vignettes à 60 images par seconde sans à-coups ni blocage du fil d'interface (`AGENTS.md` §4 ter).
   - Chargement différé et asynchrone des vignettes depuis `thumbs_0.db` via `PicasaDatabase`.

3. **Disposition géométrique stricte** :
   - Volet latéral gauche (`alist` : hauteur de ligne 22px, indentation 17px, police 14px, couleur `#FFF3F3F3`).
   - Panneau central de grille de vignettes (gouttière 24px, espacement X 12px, espacement Y 22px, titre en Georgia 20px `#634B45`).
   - Barre de sélection inférieure (« Photo Tray ») avec boutons d'action (Hold, Clear, Upload, Export, Print, Email).
   - Volet latéral droit escamotable (« Right Drawer » : Informations/EXIF, Balises/Tags, Personnes/Faces, Lieux/Geotag).
   - Barre d'outils supérieure et barre de menus complète (`eMenu*`).

4. **Compatibilité multiplateforme et intégration Python** :
   - Python 3.11+ sous Windows avec typage strict.

---

## 2. Comparatif des solutions candidates

| Critère | Tkinter | wxPython | PySide6 (Qt 6) | Moteur Direct2D / Curses |
| :--- | :--- | :--- | :--- | :--- |
| **Rendu pixel-exact personnalisé** | Faible (contrôles natifs rigides, dessin lent) | Moyen (DC GDI lourd, limitations multi-écran) | **Excellent** (`QPainter`, QSS, double-buffering matériel) | Élevé mais demande réécriture totale des primitives |
| **Performance grille 100k images** | Inexploitable | Médiocre avec Canvas | **Optimale** (Viewport virtuel, `QAbstractItemView` / `QGraphicsView` / `QPainter` direct) | Optimale |
| **Gestion des polices et DPI** | Rendu flou / DPI instable | Rendu Win32 natif | **Exacte** (Support High-DPI, formats de police, métriques sous-pixel) | Complexe |
| **Raccourcis clavier & Menus** | Basique | Standard | **Complet** (`QKeySequence`, gestion fine des événements clavier) | Faible |
| **Disponibilité dans l'environnement** | Standard | Non installé | **Déjà installé** (`PySide6 6.12.0`) | Non installé |

---

## 3. Décision technique : **PySide6**

**PySide6** est retenu comme toolkit principal pour les raisons suivantes :

1. **Rendu Custom haute fidélité** :
   Grâce à `QPainter`, PySide6 permet de reproduire fidèlement chaque élément graphique propriétaire de Picasa (bordures arrondies, dégradés d'en-tête, boutons d'action du tray, bordures de sélection bleue/blanche).

2. **Architecture Vue Virtuelle (Virtual Canvas)** :
   Une implémentation avec calcul de disposition virtuel permet d'afficher des photothèques de plus de 100 000 photos en ne dessinant que les éléments visibles dans le viewport, garantissant un défilement immédiat à 60 FPS conformément à `AGENTS.md` §4 ter.

3. **Séparation nette Modèle / Vue** :
   La couche d'interface `picasa_py/ui/` communique avec `picasa_py/db/` sans jamais effectuer d'écritures directes non contrôlées, garantissant la règle absolue de compatibilité de la base de données.

---

## 4. Écarts connus et tolérances

1. **Rendu des polices de caractères** :
   - Picasa 3 intègre dans son binaire et dans `runtime/` des polices propriétaires (`Praxis`, `HelveticaNeue`). Sur les systèmes où ces polices ne sont pas installées au niveau de l'OS, PySide6 utilisera les métriques et correspondances exactes (police Segoe UI / Arial / Georgia selon `constants.ui`).
2. **DPI Scaling** :
   - Picasa 3 date de l'ère du 96 DPI fixe (Windows XP/7). PySide6 gère le 96 DPI par défaut avec mode adaptatif optionnel tout en préservant les dimensions d'origine en pixels logiques.
