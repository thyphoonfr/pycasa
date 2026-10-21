"""
FR: Composants d'histogramme et d'informations EXIF d'appareil photo pour PyCasa.
Fournit la visualisation d'histogramme RVB & Luminance en temps réel et la carte d'infos caméra.

EN: Histogram & Camera EXIF Info Components for PyCasa.
Provides real-time RGB & Luminance histogram visualization and compact camera info card.

Ref: picasa3.exe @ IMAGEPROPERTIES.XML, imageproperties.fen
Ref: picasa3.exe @ 0x00889210 (EXIF parsing & display)
Ref: AGENTS.md §4 bis (Fidélité de l'interface & performances)
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QButtonGroup
)
from PySide6.QtCore import Qt, QRect, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPaintEvent, QPainterPath, QLinearGradient, QFont
)

from picasa_py.ui.exif_reader import extract_full_metadata
from picasa_py.ui.style import PicasaStyle


class PicasaHistogramWidget(QWidget):
    """
    FR: Widget de visualisation d'histogramme RVB et Luminance en temps réel.
    EN: Real-time RGB and Luminance histogram visualization widget.
    Ref: picasa3.exe @ imageproperties/histogram, photo editor tuning
    """

    def __init__(
        self,
        height: int = 80,
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        """
        FR: Initialise le widget d'histogramme avec la hauteur et le style spécifiés.
        EN: Initializes the histogram widget with the specified height and style.
        """
        super().__init__(parent)
        self.style = style or PicasaStyle.instance()
        self.setFixedHeight(height)
        self.setMinimumWidth(180)

        self.channel_mode: str = "RGB"  # "RGB", "R", "G", "B", "L"
        self._r_bins: List[int] = [0] * 256
        self._g_bins: List[int] = [0] * 256
        self._b_bins: List[int] = [0] * 256
        self._l_bins: List[int] = [0] * 256
        self._max_val: int = 1
        self._has_data: bool = False

        self.setStyleSheet("background: transparent;")

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique le thème PicasaStyle et redessine l'histogramme.
        EN: Applies the PicasaStyle theme and repaints the histogram.
        """
        self.style = style or PicasaStyle.instance()
        self.update()

    def set_image(self, img: Optional[Image.Image]) -> None:
        """
        FR: Calcule l'histogramme RVB et Luminance depuis une image PIL.
        EN: Computes the RGB and Luminance histogram bins from a PIL image.
        """
        if img is None:
            self._has_data = False
            self.update()
            return

        try:
            if img.mode in ("P", "PA") or (img.mode != "RGBA" and "transparency" in img.info):
                img = img.convert("RGBA")
            if img.mode != "RGB":
                rgb_img = img.convert("RGB")
            else:
                rgb_img = img

            # FR: Pour une performance maximale, sous-échantillonner à 256px max
            # EN: For maximum performance, downsample to 256px max
            w, h = rgb_img.size
            if w > 256 or h > 256:
                scale = min(256.0 / w, 256.0 / h)
                calc_img = rgb_img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.NEAREST)
            else:
                calc_img = rgb_img

            hist = calc_img.histogram()
            self._r_bins = hist[0:256]
            self._g_bins = hist[256:512]
            self._b_bins = hist[512:768]
            self._l_bins = calc_img.convert("L").histogram()

            # FR: Normalisation avec écrêtage léger du pic pour éviter que le noir/blanc pur n'écrase la courbe
            # EN: Normalize with slight peak clipping so pure black/white spikes do not flatten the curve
            all_max = max(
                max(self._r_bins[1:255] or [1]),
                max(self._g_bins[1:255] or [1]),
                max(self._b_bins[1:255] or [1]),
                max(self._l_bins[1:255] or [1]),
            )
            self._max_val = max(1, all_max)
            self._has_data = True
            self.update()
        except Exception:
            self._has_data = False
            self.update()

    def set_channel_mode(self, mode: str) -> None:
        """
        FR: Sélectionne le mode d'affichage des canaux ('RGB', 'R', 'G', 'B' ou 'L').
        EN: Selects the channel display mode ('RGB', 'R', 'G', 'B', or 'L').
        """
        if mode in ("RGB", "R", "G", "B", "L"):
            self.channel_mode = mode
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        FR: Dessine l'arrière-plan, la grille de repères et les courbes d'histogramme des canaux actifs.
        EN: Paints the background, reference grid, and active channel histogram curves.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        is_dark = self.style.is_dark

        # FR: 1. Fond adapté au thème actif / EN: 1. Background adapted to the active theme
        bg_rect = QRect(0, 0, w, h)
        if is_dark:
            bg_col = self.style.window_bgcolor.darker(115)
            border_col = self.style.splitter_color
            grid_col = self.style.window_bgcolor.lighter(120)
            wait_col = self.style.alayout_subtitleColor
        else:
            bg_col = self.style.alist_bgcolor.darker(108)
            border_col = self.style.splitter_color
            grid_col = self.style.alist_bgcolor.darker(118)
            wait_col = self.style.alayout_subtitleColor

        painter.fillRect(bg_rect, bg_col)
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        # FR: 2. Grille discrète (repères 25%, 50%, 75%) / EN: 2. Subtle grid lines (25%, 50%, 75% marks)
        grid_pen = QPen(grid_col, 1, Qt.PenStyle.DotLine)
        painter.setPen(grid_pen)
        for pct in (0.25, 0.5, 0.75):
            x = int(pct * (w - 2)) + 1
            painter.drawLine(x, 1, x, h - 2)

        if not self._has_data:
            painter.setPen(wait_col)
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, "Histogramme (en attente)")
            return

        # FR: 3. Dessin des courbes selon le mode / EN: 3. Draw channel curves according to mode
        margin_x = 2.0
        draw_w = w - 4.0
        draw_h = h - 6.0
        base_y = h - 3.0

        def create_curve_path(bins: List[int]) -> QPainterPath:
            """
            FR: Construit le chemin QPainterPath fermé représentant la courbe d'un canal de 256 niveaux.
            EN: Builds the closed QPainterPath representing a 256-bin channel histogram curve.
            """
            path = QPainterPath()
            path.moveTo(margin_x, base_y)
            for i in range(256):
                x = margin_x + (i / 255.0) * draw_w
                # FR: Échelle linéaire bornée / EN: Clamped linear scale
                val = bins[i]
                norm_h = min(1.0, val / self._max_val)
                y = base_y - (norm_h * draw_h)
                path.lineTo(x, y)
            path.lineTo(margin_x + draw_w, base_y)
            path.closeSubpath()
            return path

        if is_dark:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self.channel_mode in ("RGB", "R"):
            r_path = create_curve_path(self._r_bins)
            painter.setPen(QPen(QColor("#E53935" if not is_dark else "#FF4444"), 1))
            painter.setBrush(QBrush(QColor(235, 60, 60, 110)))
            painter.drawPath(r_path)

        if self.channel_mode in ("RGB", "G"):
            g_path = create_curve_path(self._g_bins)
            painter.setPen(QPen(QColor("#2E7D32" if not is_dark else "#44DD55"), 1))
            painter.setBrush(QBrush(QColor(60, 200, 75, 100)))
            painter.drawPath(g_path)

        if self.channel_mode in ("RGB", "B"):
            b_path = create_curve_path(self._b_bins)
            painter.setPen(QPen(QColor("#1E88E5" if not is_dark else "#4488FF"), 1))
            painter.setBrush(QBrush(QColor(60, 130, 245, 110)))
            painter.drawPath(b_path)

        if self.channel_mode == "L":
            l_path = create_curve_path(self._l_bins)
            if is_dark:
                painter.setPen(QPen(QColor("#DDDDDD"), 1.2))
                painter.setBrush(QBrush(QColor(220, 220, 220, 130)))
            else:
                lum_col = self.style.alist_textcolor
                painter.setPen(QPen(lum_col, 1.2))
                painter.setBrush(QBrush(QColor(lum_col.red(), lum_col.green(), lum_col.blue(), 95)))
            painter.drawPath(l_path)


class PicasaCameraInfoCard(QWidget):
    """
    FR: Fiche récapitulative compacte des données de l'appareil photo et de prise de vue.
    EN: Compact summary card displaying camera model and exposure metadata.
    Ref: picasa3.exe @ imageproperties.fen, IMAGEPROPERTIES.XML
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        style: Optional[PicasaStyle] = None,
    ):
        """
        FR: Initialise la fiche d'informations caméra avec ses badges EXIF (ouverture, vitesse, ISO, focale, flash).
        EN: Initializes the camera info card with its EXIF badges (aperture, shutter, ISO, focal length, flash).
        """
        super().__init__(parent)
        self.style = style or PicasaStyle()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.frame = QFrame()
        self.frame.setObjectName("InfoFrame")
        f_layout = QVBoxLayout(self.frame)
        f_layout.setContentsMargins(6, 6, 6, 6)
        f_layout.setSpacing(4)

        # FR: Ligne 1 : Appareil photo / EN: Row 1: Camera model
        h_cam = QHBoxLayout()
        self.lbl_camera = QLabel("📷 Appareil non renseigné")
        self.lbl_camera.setObjectName("CameraTitle")
        h_cam.addWidget(self.lbl_camera, 1)
        f_layout.addLayout(h_cam)

        # FR: Ligne 2 : Badges de paramètres de prise de vue (f/, s, ISO, mm)
        # EN: Row 2: Shooting parameter badges (f/, s, ISO, mm)
        self.h_badges = QHBoxLayout()
        self.h_badges.setSpacing(4)

        self.badge_aperture = QLabel("—")
        self.badge_aperture.setObjectName("Badge")
        self.badge_aperture.setToolTip("Ouverture du diaphragme")
        self.h_badges.addWidget(self.badge_aperture)

        self.badge_shutter = QLabel("—")
        self.badge_shutter.setObjectName("Badge")
        self.badge_shutter.setToolTip("Vitesse d'obturation")
        self.h_badges.addWidget(self.badge_shutter)

        self.badge_iso = QLabel("—")
        self.badge_iso.setObjectName("Badge")
        self.badge_iso.setToolTip("Sensibilité ISO")
        self.h_badges.addWidget(self.badge_iso)

        self.badge_focal = QLabel("—")
        self.badge_focal.setObjectName("Badge")
        self.badge_focal.setToolTip("Distance focale")
        self.h_badges.addWidget(self.badge_focal)

        self.badge_flash = QLabel("⚡")
        self.badge_flash.setObjectName("Badge")
        self.badge_flash.setToolTip("État du flash")
        self.h_badges.addWidget(self.badge_flash)

        self.h_badges.addStretch(1)
        f_layout.addLayout(self.h_badges)

        # FR: Ligne 3 : Dimensions et date / EN: Row 3: Dimensions and date
        self.lbl_details = QLabel("— × — • —")
        self.lbl_details.setObjectName("CameraDetails")
        f_layout.addWidget(self.lbl_details)

        layout.addWidget(self.frame)
        self.apply_style(self.style)

    def apply_style(self, style: PicasaStyle) -> None:
        """
        FR: Applique dynamiquement les couleurs du thème PicasaStyle à la fiche et aux badges.
        EN: Dynamically applies PicasaStyle theme colors to the info frame and badges.
        """
        self.style = style
        is_dark = style.is_dark
        if is_dark:
            frame_bg = style.window_bgcolor.darker(110).name()
            frame_border = style.splitter_color.name()
            txt_col = style.alist_textcolor.name()
            sub_col = style.alayout_subtitleColor.name()
            badge_bg = style.topbar_btn_bg_end.name()
            badge_border = style.topbar_border_color.name()
            badge_txt = style.alist_textcolor.name()
        else:
            frame_bg = style.alist_bgcolor.darker(104).name()
            frame_border = style.splitter_color.name()
            txt_col = style.alist_textcolor.name()
            sub_col = style.alayout_subtitleColor.name()
            badge_bg = style.topbar_btn_bg_start.name()
            badge_border = style.topbar_border_color.name()
            badge_txt = style.alist_textcolor.name()

        self.setStyleSheet(f"""
            QFrame#InfoFrame {{
                background-color: {frame_bg};
                border: 1px solid {frame_border};
                border-radius: 5px;
                padding: 6px;
            }}
            QLabel {{
                color: {txt_col};
                font-size: 11px;
                background: transparent;
            }}
            QLabel#CameraTitle {{
                font-weight: bold;
                color: {txt_col};
                font-size: 11px;
                background: transparent;
            }}
            QLabel#CameraDetails {{
                color: {sub_col};
                font-size: 10px;
                background: transparent;
            }}
            QLabel#Badge {{
                background-color: {badge_bg};
                color: {badge_txt};
                border: 1px solid {badge_border};
                border-radius: 3px;
                padding: 2px 5px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)

    def set_photo_path(self, photo_path: str) -> None:
        """
        FR: Charge et extrait les métadonnées de la photo depuis son chemin disque.
        EN: Loads and extracts photo metadata from its file path on disk.
        """
        if not photo_path:
            self.clear_info()
            return
        meta = extract_full_metadata(photo_path)
        self.update_with_metadata(meta)

    def update_with_metadata(self, meta: Dict[str, Any]) -> None:
        """
        FR: Met à jour l'affichage avec le dictionnaire de métadonnées extrait.
        EN: Updates the card display using the extracted metadata dictionary.
        """
        cam = meta.get("camera", "—")
        self.lbl_camera.setText(f"📷  {cam}" if cam and cam != "—" else "📷  Appareil inconnu")

        props_dict = dict(meta.get("properties", []))

        # FR: Ouverture / EN: Aperture
        f_val = props_dict.get("Ouverture", "—")
        self.badge_aperture.setText(f_val)
        self.badge_aperture.setVisible(f_val != "—")

        # FR: Vitesse / EN: Shutter speed
        exp_val = props_dict.get("Vitesse d'obturation", "—")
        self.badge_shutter.setText(exp_val)
        self.badge_shutter.setVisible(exp_val != "—")

        # FR: ISO / EN: ISO sensitivity
        iso_val = props_dict.get("Sensibilité ISO", "—")
        self.badge_iso.setText(iso_val.replace("ISO ", "") if "ISO" in iso_val else iso_val)
        self.badge_iso.setVisible(iso_val != "—")

        # FR: Focale / EN: Focal length
        focal_val = props_dict.get("Distance focale", "—")
        self.badge_focal.setText(focal_val)
        self.badge_focal.setVisible(focal_val != "—")

        # FR: Flash / EN: Flash status
        flash_val = props_dict.get("Flash", "—")
        if flash_val == "Déclenché":
            self.badge_flash.setText("⚡ Flash")
            self.badge_flash.setStyleSheet("background-color: #7A5515; color: #FFD24D; border: 1px solid #B3862A; border-radius: 3px; padding: 2px 5px; font-size: 10px; font-weight: bold;")
            self.badge_flash.setVisible(True)
        else:
            self.badge_flash.setVisible(False)

        res = meta.get("resolution", "—")
        sz = meta.get("filesize", "—")
        date_str = meta.get("date", "—")
        self.lbl_details.setText(f"{res}  •  {sz}  •  {date_str}")

    def clear_info(self) -> None:
        """
        FR: Réinitialise la fiche d'informations lorsqu'aucune photo n'est sélectionnée.
        EN: Resets the camera info card when no photo is selected.
        """
        self.lbl_camera.setText("📷  Aucune photo")
        self.badge_aperture.setVisible(False)
        self.badge_shutter.setVisible(False)
        self.badge_iso.setVisible(False)
        self.badge_focal.setVisible(False)
        self.badge_flash.setVisible(False)
        self.lbl_details.setText("—")

