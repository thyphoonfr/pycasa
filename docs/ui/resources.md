# Spécification et Cartographie des Ressources Graphiques de Picasa 3

Ce document référence l'ensemble des ressources extraites de `Picasa3.exe`, `Picasa3i18n.dll` et du répertoire `runtime/` conformément à la section **4 bis.2** et **5** de `AGENTS.md`.

---

## 1. Icônes d'application (`RT_GROUP_ICON` & `RT_ICON`)

Localisation : `ui/resources/icons/`
Source : `Picasa3.exe` @ Section des ressources PE

| ID Groupe | Fichier extrait | Résolutions incluses | Usage / Rôle dans Picasa |
| :--- | :--- | :--- | :--- |
| **105** | `group_icon_105.ico` | 16x16, 32x32, 48x48, 256x256 (32bpp & 8bpp) | **Icône principale de l'application Picasa 3** |
| **106** | `group_icon_106.ico` | 32x32 (32bpp) | Icône document / fichier Picasa |
| **150** | `group_icon_150.ico` | 16x16 | Icône dossier d'images surveillé |
| **151** | `group_icon_151.ico` | 16x16, 32x32 | Icône de notification système (System Tray) |
| **152** | `group_icon_152.ico` | 16x16 | Icône d'album virtuel |
| **153** | `group_icon_153.ico` | 16x16 | Icône de dossier externe |
| **157** | `group_icon_157.ico` | 16x16 | Icône d'album web Picasa |
| **158** | `group_icon_158.ico` | 16x16 | Icône film / vidéo |
| **159** | `group_icon_159.ico` | 16x16 | Icône de groupe de personnes |
| **161** | `group_icon_161.ico` | 16x16 | Icône de projet (collage, poster, film) |
| **320** | `group_icon_320.ico` | 16x16, 32x32, 48x48, 256x256 | Icône alternative d'export / visionneuse |

---

## 2. Curseurs personnalisés (`RT_GROUP_CURSOR` & `RT_CURSOR`)

Localisation : `ui/resources/cursors/`
Source : `Picasa3.exe` @ Section des ressources PE

| ID Curseur | Fichier extrait | Point chaud (Hotspot) | Usage dans l'interface |
| :--- | :--- | :--- | :--- |
| **1** | `cursor_1.cur` | (9, 8) | Loupe / Zoom avant |
| **2** | `cursor_2.cur` | (0, 19) | Pinceau / Outil de retouche |
| **3** | `cursor_3.cur` | (7, 9) | Pipette de balance des blancs |
| **4** | `cursor_4.cur` | (7, 9) | Sélecteur de couleur / Échantillonnage |
| **5** | `cursor_5.cur` | (14, 15) | Réticule de recadrage (Crop tool crosshair) |
| **6** | `cursor_6.cur` | (0, 0) | Flèche de redimensionnement horizontale |
| **7** | `cursor_7.cur` | (2, 2) | Main de déplacement d'image (Pan / Hand tool) |
| **8** | `cursor_8.cur` | (12, 9) | Outil yeux rouges |
| **9** | `cursor_9.cur` | (14, 15) | Curseur de rotation d'image / Straighten |
| **10** | `cursor_10.cur` | (0, 0) | Curseur de texte |
| **11** | `cursor_11.cur` | (7, 9) | Curseur de tag / identification de visage |
| **12** | `cursor_12.cur` | (15, 14) | Curseur de glisser-déposer d'images |

---

## 3. Définitions d'écrans et boîtes de dialogue (`runtime/*.fen`)

Localisation : `ui/resources/fen/`
Picasa utilise son propre moteur de fenêtrage XML (`.fen`) pour composer ses boîtes de dialogue et panneaux :

- `about.fen` : Boîte de dialogue « À propos de Picasa »
- `album.fen` : Création et modification d'album
- `confirm.fen` : Dialogue de confirmation de suppression / déplacement
- `contactmgr.fen` : Gestionnaire de contacts et visages
- `customaspectratio.fen` : Dialogue de format de recadrage personnalisé
- `export.fen` : Assistant d'exportation d'images (redimensionnement, qualité JPEG)
- `imageproperties.fen` : Panneau des propriétés et métadonnées EXIF/IPTC
- `options.fen` : Préférences globales de l'application (types de fichiers, affichage, etc.)
- `rename.fen` : Outil de renommage en masse
- `reviewprint.fen` : Aperçu avant impression
- `webexport.fen` : Exportation en page web HTML
- `youtube.fen` : Assistant de publication vidéo sur YouTube

---

## 4. Métriques et feuille de style de l'interface (`constants.ui`)

Localisation : `ui/resources/style/constants.ui`
Définition originale des couleurs, marges et polices de Picasa :

```ini
[Picasa2]
; Volet gauche (Album / Folder List)
alist_height=22
alist_fontsize_win=14
alist_indent=17
alist_bgcolor=0xFFF3F3F3
alist_hicolor_win=0xFF83A7BD
alist_hicolor2_win=0xFFE5E2DA
alist_selcolor_win=0xFF25648B
alist_catcolor=0xFFEDEAE4
alist_scatcolor=0xFF25648B
alist_dotcolor=0xFFBEBEBE
alist_stickycolor=0xFFEAE7DC

; En-tête des dossiers / albums
alabel_fldrcol=#e2e2e2
alabel_fldrhicol=#f2f2f2
alabel_albumcol=#e2e2e2
alabel_albumhicol=#f2f2f2
alabel_buttfont_win=Praxis Semi Bold/Heavy
alabel_buttfontSize_win=12
alabel_lighttext=#FFFFFF
alabel_darktext=#000000

; Grille de vignettes
alayout_gutter=24
alayout_thumbGutterX=12
alayout_thumbGutterY=22
alayout_titleFont=Georgia
alayout_titleSize=20
alayout_titleColor=#634B45
alayout_titleOffsetX=28
alayout_bodyFont=Georgia
alayout_bodySize=14

; Sélection de vignettes
thumbsel_color1=#009EFF
thumbsel_color2=#FFFFFF
```

---

## 5. Menus et Raccourcis Clavier

Localisation : `ui/resources/menus/` et `ui/resources/xml/SHORTCUTS.XML`
167 entrées de menu structurées avec identifiants symboliques `eMenuFile`, `eMenuEdit`, `eMenuView`, `eMenuLabelFolder`, `eMenuPicture`, `eMenuCreate`, `eMenuTools`, `eMenuHelp`.
