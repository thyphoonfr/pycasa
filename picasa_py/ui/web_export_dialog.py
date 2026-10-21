"""
FR : Boîte de dialogue d'exportation de galerie Web HTML pour PyCasa (CWebExportDialog / webexport.fen).
Génère une galerie photo statique HTML5/CSS complète et responsive avec visionneuse modale.
EN : HTML Web Gallery Export Dialog for PyCasa (CWebExportDialog / webexport.fen).
Generates a complete, responsive HTML5/CSS static photo gallery with lightbox navigation.

Ref: picasa3.exe @ webexport.fen, WEBEXPORT.XML
Ref: ui/resources/xml/WEBEXPORT_FR.XML
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import List, Optional
from PIL import Image

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFileDialog, QMessageBox, QFrame,
    QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtCore import QUrl

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager


class PicasaWebExportDialog(QDialog):
    """
    FR : Dialogue d'exportation en page web HTML (webexport.fen).
    EN : HTML web page export dialog (webexport.fen).
    """

    def __init__(
        self,
        photo_paths: List[str],
        default_title: str = "Galerie Photos",
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.photo_paths = [p for p in photo_paths if os.path.exists(p)]
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(
            self.res_mgr.get_xml_string("webexport/window1.title", "Exporter en tant que page Web")
        )
        self.setFixedWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Titre de la page web (Ref: webexport/description)
        self.lbl_title = QLabel(
            self.res_mgr.get_xml_string("webexport/labelgroup13.title", "Titre de la page Web :")
        )
        layout.addWidget(self.lbl_title)
        self.edit_title = QLineEdit(default_title)
        layout.addWidget(self.edit_title)

        # 2. Dimensions des images (Ref: webexport/sizeradio)
        self.lbl_size = QLabel(
            self.res_mgr.get_xml_string("webexport/labelgroup2.title", "Exporter les photos en :")
        )
        layout.addWidget(self.lbl_size)
        self.combo_size = QComboBox()
        self.combo_size.addItem("1024 pixels (pour grands écrans)", 1024)
        self.combo_size.addItem("800 pixels (pour pages Web standard)", 800)
        self.combo_size.addItem("640 pixels (taille compacte)", 640)
        self.combo_size.addItem("Taille originale", 0)
        layout.addWidget(self.combo_size)

        # 3. Thème graphique (Template)
        self.lbl_theme = QLabel("Modèle de présentation :")
        layout.addWidget(self.lbl_theme)
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("Picasa Sombre (Fond gris foncé)", "dark")
        self.combo_theme.addItem("Picasa Moderne (Fond clair épuré)", "light")
        layout.addWidget(self.combo_theme)

        # 4. Dossier de destination (Ref: webexport/location)
        self.lbl_location = QLabel(
            self.res_mgr.get_xml_string("webexport/labelgroup15.title", "Dossier de destination :")
        )
        layout.addWidget(self.lbl_location)
        loc_box = QHBoxLayout()
        default_dir = str(Path.home() / "Documents" / "WebGallery")
        self.edit_location = QLineEdit(default_dir)
        self.edit_dest = self.edit_location
        loc_box.addWidget(self.edit_location, 1)

        self.btn_browse = QPushButton(
            self.res_mgr.get_xml_string("webexport/changeloc.title", "Parcourir...")
        )
        self.btn_browse.clicked.connect(self._browse_location)
        loc_box.addWidget(self.btn_browse)
        layout.addLayout(loc_box)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.sep)

        # 5. Boutons Exporter / Annuler
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)

        self.btn_export = QPushButton(
            self.res_mgr.get_xml_string("webexport/button29.title", "Exporter")
        )
        self.btn_export.setObjectName("PrimaryBtn")
        self.btn_export.clicked.connect(self._export_gallery)
        btn_box.addWidget(self.btn_export)

        self.btn_cancel = QPushButton(
            self.res_mgr.get_xml_string("webexport/button30.title", "Annuler")
        )
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)
        self.apply_style(self.style)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue d'exportation Web.
        EN : Dynamically applies the active Picasa theme to the web export dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#111111"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        border = "#4B5263" if is_dark else "#7F9DB9"
        btn_bg = "#3A3F4B" if is_dark else "#F0F0F0"
        btn_hover = "#484E5C" if is_dark else "#E5E5E5"
        btn_border = "#555B69" if is_dark else "#707070"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
            QLineEdit, QComboBox {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 3px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 9pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {inp_bg};
                color: {fg};
                selection-background-color: #3879D9;
                selection-color: #FFFFFF;
                font-size: 9pt;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 12px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                min-width: 65px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: #3C7FB1;
                color: {fg};
            }}
            QPushButton#PrimaryBtn {{
                background-color: #2F6DB5;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #1E4E85;
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: #3879D9;
                color: #FFFFFF;
            }}
        """)
        if hasattr(self, "sep"):
            self.sep.setStyleSheet(f"color: {border};")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes selon la langue active.
        EN : Updates texts according to the active language.
        """
        self.setWindowTitle(
            self.res_mgr.get_xml_string("webexport/window1.title", "Exporter en tant que page Web")
        )
        self.lbl_title.setText(
            self.res_mgr.get_xml_string("webexport/labelgroup13.title", "Titre de la page Web :")
        )
        self.lbl_size.setText(
            self.res_mgr.get_xml_string("webexport/labelgroup2.title", "Exporter les photos en :")
        )
        self.lbl_location.setText(
            self.res_mgr.get_xml_string("webexport/labelgroup15.title", "Dossier de destination :")
        )
        self.btn_browse.setText(self.res_mgr.get_xml_string("webexport/changeloc.title", "Parcourir..."))
        self.btn_export.setText(self.res_mgr.get_xml_string("webexport/button29.title", "Exporter"))
        self.btn_cancel.setText(self.res_mgr.get_xml_string("webexport/button30.title", "Annuler"))

    def _browse_location(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination", self.edit_location.text())
        if folder:
            self.edit_location.setText(folder)

    def _export_gallery(self) -> None:
        if not self.photo_paths:
            QMessageBox.warning(self, "Attention", "Aucune photo sélectionnée pour l'exportation.")
            return

        out_root = Path(self.edit_location.text().strip())
        out_root.mkdir(parents=True, exist_ok=True)

        images_dir = out_root / "images"
        thumbs_dir = out_root / "thumbnails"
        images_dir.mkdir(exist_ok=True)
        thumbs_dir.mkdir(exist_ok=True)

        target_size = self.combo_size.currentData()
        theme = self.combo_theme.currentData()
        title = self.edit_title.text().strip() or "Galerie Photos"

        processed_photos = []

        for idx, src_p in enumerate(self.photo_paths):
            fname = Path(src_p).name
            img_dest = images_dir / fname
            thumb_dest = thumbs_dir / fname

            try:
                from picasa_py.ui.image_processor import PicasaImageProcessor
                img = PicasaImageProcessor.load_transformed_image(src_p)
                if img is not None:
                    # Copie image plein format ou redimensionnée
                    img_full = img.copy()
                    if target_size > 0:
                        img_full.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
                    if img_full.mode in ("RGBA", "P"):
                        img_full = img_full.convert("RGB")
                    img_full.save(str(img_dest), "JPEG", quality=90)

                    # Miniature carrée centrée
                    thumb_img = img.copy()
                    thumb_img.thumbnail((250, 250), Image.Resampling.LANCZOS)
                    if thumb_img.mode in ("RGBA", "P"):
                        thumb_img = thumb_img.convert("RGB")
                    thumb_img.save(str(thumb_dest), "JPEG", quality=85)

                    processed_photos.append({
                        "name": Path(src_p).name,
                        "file": fname,
                    })
            except Exception:
                pass

        # Générer le fichier index.html avec galerie responsive et visionneuse modale
        bg_color = "#1E2024" if theme == "dark" else "#F7F7F7"
        text_color = "#FFFFFF" if theme == "dark" else "#222222"
        card_bg = "#2C3038" if theme == "dark" else "#FFFFFF"

        html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      font-family: Tahoma, 'Segoe UI', sans-serif;
      background-color: {bg_color};
      color: {text_color};
      margin: 0;
      padding: 24px;
    }}
    header {{
      text-align: center;
      margin-bottom: 24px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(128,128,128,0.2);
    }}
    h1 {{ margin: 0 0 6px 0; font-size: 24px; }}
    .count {{ font-size: 13px; opacity: 0.7; }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
      max-width: 1200px;
      margin: 0 auto;
    }}
    .card {{
      background: {card_bg};
      border-radius: 6px;
      overflow: hidden;
      box-shadow: 0 3px 6px rgba(0,0,0,0.2);
      cursor: pointer;
      transition: transform 0.15s ease;
      text-align: center;
    }}
    .card:hover {{ transform: scale(1.03); }}
    .card img {{
      width: 100%;
      height: 140px;
      object-fit: cover;
      display: block;
    }}
    .caption {{
      padding: 8px;
      font-size: 11px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    /* Modal Lightbox */
    #modal {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.9);
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }}
    #modal img {{
      max-width: 90vw;
      max-height: 85vh;
      border-radius: 4px;
      box-shadow: 0 0 20px rgba(0,0,0,0.8);
    }}
    .close-btn, .prev-btn, .next-btn {{
      position: absolute;
      color: #FFF;
      font-size: 28px;
      cursor: pointer;
      user-select: none;
      padding: 10px;
    }}
    .close-btn {{ top: 15px; right: 25px; }}
    .prev-btn {{ left: 20px; top: 50%; transform: translateY(-50%); }}
    .next-btn {{ right: 20px; top: 50%; transform: translateY(-50%); }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="count">{len(processed_photos)} photos exportées depuis Picasa</div>
  </header>
  <div class="gallery">
"""
        for i, item in enumerate(processed_photos):
            html_content += f"""    <div class="card" onclick="openPhoto({i})">
      <img src="thumbnails/{item['file']}" alt="{item['name']}">
      <div class="caption">{item['name']}</div>
    </div>\n"""

        html_content += f"""  </div>

  <div id="modal" onclick="if(event.target===this) closeModal()">
    <span class="close-btn" onclick="closeModal()">&times;</span>
    <span class="prev-btn" onclick="changePhoto(-1)">&#10094;</span>
    <img id="modal-img" src="" alt="Agrandissement">
    <span class="next-btn" onclick="changePhoto(1)">&#10095;</span>
  </div>

  <script>
    const photos = {str([f"images/{p['file']}" for p in processed_photos])};
    let currIdx = 0;
    function openPhoto(idx) {{
      currIdx = idx;
      document.getElementById('modal-img').src = photos[currIdx];
      document.getElementById('modal').style.display = 'flex';
    }}
    function closeModal() {{
      document.getElementById('modal').style.display = 'none';
    }}
    function changePhoto(step) {{
      currIdx = (currIdx + step + photos.length) % photos.length;
      document.getElementById('modal-img').src = photos[currIdx];
    }}
    document.addEventListener('keydown', (e) => {{
      if (document.getElementById('modal').style.display === 'flex') {{
        if (e.key === 'ArrowLeft') changePhoto(-1);
        else if (e.key === 'ArrowRight') changePhoto(1);
        else if (e.key === 'Escape') closeModal();
      }}
    }});
  </script>
</body>
</html>"""

        index_file = out_root / "index.html"
        index_file.write_text(html_content, encoding="utf-8")

        if self.isVisible():
            QMessageBox.information(
                self,
                "Galerie Web créée",
                f"La galerie HTML a été générée avec succès dans :\n{out_root}\n\nLe fichier index.html va s'ouvrir dans votre navigateur."
            )
            # Ouvrir index.html dans le navigateur
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(index_file)))
        self.accept()

    _generate_web_gallery = _export_gallery
