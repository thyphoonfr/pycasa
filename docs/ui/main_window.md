# Spécification et Cartographie de la Fenêtre Principale (`ytWindow`)

Ce document décrit l'architecture de la fenêtre principale de Picasa 3 (`ytWindow`), découverte par désassemblage et rétro-ingénierie dans Ghidra, conformément à `AGENTS.md` §4 bis et §5.

---

## 1. Identification dans le Binaire

- **Nom de classe Win32** : `ytWindow`
  - Chaîne : `picasa3.exe @ 0x00C7F35C`
- **Procédure de fenêtre (`lpfnWndProc`)** : `picasa3.exe @ 0x00983940`
- **Enregistrement de la classe (`RegisterClass`)** : `picasa3.exe @ 0x009838D0` - `0x00983937`
  - Style : `0x400B` (`CS_DBLCLKS | CS_HREDRAW | CS_VREDRAW`)
  - `cbWndExtra` : `4`
- **Signature magique de l'instance** : `picasa3.exe @ 0x0070494B`
  - Valeur stockée dans `GetWindowLong(hwnd, 0)` : `0x47506332` (`GPc2` = Google Picasa 2/3)
  - Pointeur C++ vers l'objet `ytWindow` stocké dans `GWL_USERDATA` (`-21`)
- **Distribution des messages (`WndProc`)** :
  - Appel virtuel : `(*(pThis->vtable + 0x1C))(uMsg, wParam, lParam)`
  - Code de retour `0xF4241` (1,000,001) : renvoi vers `DefWindowProcW`
  - Code de retour `0xF4240` (1,000,000) : message traité avec succès (`return 1`)

---

## 2. Disposition de la Fenêtre Principale

La disposition est articulée en 4 bandes horizontales et verticales :

```
+-------------------------------------------------------------------------+
| Barre de Menus (File, Edit, View, Folder, Picture, Create, Tools, Help) |
+-------------------------------------------------------------------------+
| Barre d'outils (Import, Diaporama, Filtres Star/Face/Movie, Recherche)  |
+---------------------+-----------------------------------+---------------+
| Volet Bibliothèque  | Grille de Vignettes Virtuelle     | Tiroir Droit  |
| (Albums, People,    | (Rendu custom QPainter 60 FPS,    | (Métadonnées, |
|  Folders, Projects) |  titre album Georgia 20px,        |  EXIF,        |
|                     |  sélection bleu/blanc, lazy-load) |  Tags, Faces) |
| alist_bgcolor=#F3F3 |                                   |               |
| alist_height=22     | alayout_gutter=24                 |               |
| alist_indent=17     | alayout_thumbGutterX=12 / Y=22    |               |
+---------------------+-----------------------------------+---------------+
| Bac à photos (Picture Tray) : Hold, Clear, Zoom Slider, Upload, Export  |
+-------------------------------------------------------------------------+
| Barre d'état (StatusBar)                                                |
+-------------------------------------------------------------------------+
```

---

## 3. Composants et Modules Python (`picasa_py/ui/`)

| Composant | Fichier source | Classe | Rôle |
| :--- | :--- | :--- | :--- |
| **Style & Métriques** | `style.py` | `PicasaStyle` | Charge `constants.ui` (couleurs, polices, marges) |
| **Ressources PE** | `resources.py` | `PicasaResourceManager` | Charge icônes `.ico`, curseurs `.cur`, textes `strings.json` |
| **Barre de Menus** | `menu.py` | `PicasaMenuBuilder` | Reconstruit l'arborescence des 167 entrées `eMenu*` |
| **Barre d'Outils** | `top_bar.py` | `PicasaTopBar` | Bouton Import, Diaporama, Filtres rapides, Recherche |
| **Arborescence** | `library_tree.py` | `PicasaLibraryTree` | Volet gauche (`alist_*`) connecté à `PicasaDatabase` |
| **Grille de Vignettes** | `thumbnail_view.py` | `PicasaThumbnailView` | Moteur de rendu virtuel haute performance (60 FPS) |
| **Bac à Photos** | `photo_tray.py` | `PicasaPhotoTray` | Plateau inférieur de sélection, actions et zoom |
| **Tiroir Droit** | `right_drawer.py` | `PicasaRightDrawer` | Métadonnées EXIF et balises de l'élément sélectionné |
| **Fenêtre Principale** | `main_window.py` | `PicasaMainWindow` | Fenêtre racine assemblant tous les composants |
| **Lanceur** | `app.py` | `run_picasa()` | Point d'entrée de l'application graphique |

---

## 4. Isolation stricte UI / Données

Conformément à `AGENTS.md` §4 bis.3 :
- La couche d'interface utilisateur `picasa_py/ui/` n'effectue **aucune écriture directe** sur les fichiers de base de données ni sur les fichiers `.ini`.
- Toutes les opérations de lecture et d'écriture transitent exclusivement par les modules `picasa_py/db/` et `picasa_py/ini/` validés par des tests unitaires round-trip à 100%.
