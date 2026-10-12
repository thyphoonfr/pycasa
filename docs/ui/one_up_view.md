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
- **Molette de souris** : zoom progressif centré.
- **Clic gauche glissé** : déplacement libre de l'image (panoramique) avec curseur main.
- **Annuler / Rétablir** : pile d'historique complète permettant d'annuler les retouches successives.
