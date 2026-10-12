# Spécification et Cartographie du Mode Édition (« One-Up View »)

Ce document décrit le fonctionnement et l'architecture du mode visualiseur/éditeur plein écran de Picasa 3, découvert par désassemblage dans Ghidra, conformément à `AGENTS.md` §4 bis et §5.

---

## 1. Identification dans le Binaire

- **Identifiants C++ dans le binaire** :
  - `OneUp` (`picasa3.exe`)
  - `OneUpUI` / `AVOneUpUI`
  - `editoneup` (volet de retouche)
- **Fichiers de spécification associés** :
  - `ONEUPTEXT.XML` (infobulles et actions)
  - `filterdesc.xml` (description des 100+ filtres, curseurs et formules mathématiques)
- **Enregistrement des modifications** :
  - Non-destructif dans `.picasa.ini` (`crop=rect64(...)`, `rot=%d`, `filters=%s`, `star=yes`).

---

## 2. Disposition de l'Écran One-Up

```
+--------------------------+----------------------------------------------------+
| [◀ Revenir bibliothèque] | Canvas d'image haute résolution (PicasaImageCanvas)|
| [↶ Annuler] [↷ Rétablir] |                                                    |
+--------------------------+  - Rendu temps réel sans perte                     |
| Onglet 1: Retouches      |  - Zoom fluide à la molette                        |
|   - Recadrer (Crop)      |  - Déplacement Pan (curseur main cursor_7.cur)     |
|   - Redresser            |  - Double-clic : bascule 100% / Ajuster            |
|   - Yeux rouges          |                                                    |
|   - J'ai de la chance    |                                                    |
|   - Contraste auto       |                                                    |
|   - Couleur auto         |                                                    |
|   - Retoucher            |                                                    |
|   - Texte                |                                                    |
| Onglet 2: Lumière        |                                                    |
|   - Lumière d'appoint    |                                                    |
|   - Hautes lumières      |                                                    |
|   - Ombres / Température |                                                    |
| Onglet 3: Effets         |                                                    |
|   - Sépia, N&B, Netteté  |                                                    |
|   - Warmify, Grain photo |                                                    |
+--------------------------+----------------------------------------------------+
| Barre de Transport : [◀ Précédente] [Suivante ▶] [↶ 90°] [↷ 90°]  Zoom [—o—]    |
+-------------------------------------------------------------------------------+
```

---

## 3. Architecture des Composants (`picasa_py/ui/`)

| Composant | Fichier source | Rôle |
| :--- | :--- | :--- |
| **Image Canvas** | `image_canvas.py` | Affiche l'image haute définition, gère le zoom, le pan et les rotations |
| **Edit Panel** | `edit_panel.py` | Panneau de gauche avec bouton « Revenir à la bibliothèque », Annuler/Rétablir et onglets de retouche |
| **Image Processor** | `image_processor.py` | Moteur matriciel (Pillow / NumPy) exécutant les filtres de `filterdesc.xml` |
| **One-Up View** | `one_up_view.py` | Orchestrateur de la vue complète avec historique Annuler/Rétablir et transport |
| **Main Window** | `main_window.py` | Gère la bascule transparente entre la grille et l'éditeur via `QStackedWidget` |

---

## 4. Interactions & Raccourcis Clavier

- **Double-clic sur vignette** : ouverture instantanée dans l'éditeur One-Up.
- **Touche Échap ou Entrée** : retour immédiat à la grille de la bibliothèque avec la photo toujours sélectionnée.
- **Flèche Gauche / Droite** : passage à la photo précédente / suivante dans le dossier en cours.
- **Molette de souris** : zoom continu ancré au curseur (le point sous la souris reste stationnaire).
- **Double-clic sur l'image** : bascule entre le mode Ajuster (Fit) et le zoom 100% (1:1) ancré au curseur.
- **Clic gauche glissé** : déplacement libre de l'image (panoramique) avec curseur main (`cursor_7.cur`).
- **Annuler / Rétablir** : pile d'historique complète permettant d'annuler les retouches successives.

---

## 5. Résolution des Fichiers Haute Définition (`db.get_media_full_path`)

- **Problème résolu** : Dans `thumbindex.db`, le champ `entry.path` des médias (type 2) contient uniquement le nom de fichier (ex: `IMG_0001.JPG`), tandis que le chemin absolu du dossier parent est stocké dans l'entrée de type 1 pointée par `entry.parent_idx`.
- **Implémentation** : `PicasaDatabase.get_media_full_path(index)` reconstitue le chemin complet `os.path.join(parent.path, entry.path)`.
- **Repli transparent** : Si le disque externe est déconnecté, la chaîne de repli consulte successivement le cache `preview` (1024px), `large` (bigthumbs), `medium` et `small`.
- **Ref Ghidra** : `picasa3.exe @ 0x0045C0A0`.

---

## 6. Navigateur de Cadrage (« Loupe Navigator »)

- **Identification dans le binaire** :
  - `CLoupeNode` (`0x00942AE4`) : composant d'affichage de la vignette d'ensemble et du cadre de visée.
  - `CLoupeMaker` (`0x00942AC8`) : constructeur et coordinateur du zoom.
  - `PanHandler` (`0x0093F3A8`) : calcul du décalage panoramique et contraintes de bornes.
  - `thumbui/loupe` (`0x0088F9C4`) : ressource et style visuel.
- **Apparence visuelle** :
  - Carte flottante ancrée en bas à droite (marge 18px), dimensions max 160×120 adaptées au ratio d'aspect.
  - Fond anthracite translucide `QColor(22, 24, 28, 230)` avec bordure 1px et coins arrondis.
  - Miniature précalculée haute performance (60 FPS constants sans redimensionner l'original).
  - Cadre de visée Picasa Orange :
    - Remplissage translucide `QColor(255, 145, 0, 50)`.
    - Liseré net 1.8px `QColor(255, 155, 0, 240)`.
    - Accents d'angle (L-brackets) aux 4 coins en `QColor(255, 220, 130)`.
- **Interactions dynamiques** :
  - **Glisser le cadre** : fait défiler l'image principale en temps réel de façon proportionnelle (`ratio = draw_dim / nav_dim`).
  - **Clic n'importe où dans la miniature** : recentre immédiatement la caméra sur le point sélectionné.
  - **Survol adaptatif** : curseur flèches multidirectionnelles (`SizeAllCursor`) sur le cadre, main pointée (`PointingHandCursor`) sur la miniature, main ouverte (`cursor_7.cur`) sur le canvas.
  - **Visibilité intelligente** : s'affiche automatiquement dès que le zoom dépasse la taille de la fenêtre (`is_zoomed_in()`), et s'estompe en mode Ajuster.

