"""
FR: Fenêtre surgissante de notification Picasa (CNotifierPopup — "Picasa Notifier").
Affiche en bas à droite de la zone de travail de l'écran (SPI_GETWORKAREA) une petite
fenêtre flottante sans bordure (WS_EX_TOPMOST | WS_EX_TOOLWINDOW) lorsqu'un changement
est détecté dans les dossiers surveillés (nouvelle photo ajoutée, photo modifiée, capture
d'écran enregistrée, montage ou film créé). Permet de cliquer sur la notification pour
localiser et sélectionner directement la photo dans la photothèque (WM_USER + 0xFF = 0x4FF).

EN: Picasa floating notification popup window (CNotifierPopup — "Picasa Notifier").
Displays at the bottom-right corner of the primary screen work area (SPI_GETWORKAREA) a
frameless floating tool window (WS_EX_TOPMOST | WS_EX_TOOLWINDOW) whenever changes are
detected in watched folders (new photo indexed, modified photo updated, screenshot saved,
collage or movie created). Clicking a notification cell restores the main window and
scrolls to / selects the photo in the library (WM_USER + 0xFF = 0x4FF).

Ref: picasa3.exe @ 0x00656FE0 (CNotifierPopup::CNotifierPopup, vftable @ 0x00CA284C)
Ref: picasa3.exe @ 0x00657300 (CNotifierPopup::Create, "Picasa Notifier", SPI_GETWORKAREA=0x30)
Ref: picasa3.exe @ 0x00658400 (CNotifierPopup::OnPaint & Layout, max 3 visible cells @ 0x006584BF)
Ref: picasa3.exe @ 0x00659270 (CNotifierPopup::DrawThumbnailWithBorder, 38x29 px, border #7792A4)
Ref: picasa3.exe @ 0x00659340 (CNotifierPopup::AddOrUpdatePhotoNotification, timeout 5.0s @ 0x00CF4618)
Ref: picasa3.exe @ 0x0065804F (CNotifierPopup::OnLButtonDown -> PostMessage 0x4FF)
Ref: picasa3.exe @ 0x00571850 (CThumbUI::NotifyPhotoAddedOrUpdated)
Ref: picasa3.exe @ 0x005E4D30 (CThumbUI::OnNotifierItemClicked, handler for 0x4FF)
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QWidget

from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle


@dataclass
class NotifierCell:
    """
    FR: Cellule de notification individuelle dans CNotifierPopup (taille struct 0x38 octets dans le binaire).
    EN: Individual notification cell in CNotifierPopup (0x38-byte struct in the original binary).
    Ref: picasa3.exe @ 0x00659340 (offsets: +0x00 group_id, +0x04 item_id, +0x08 count,
         +0x0C title, +0x10 subtitle, +0x18 thumbnail, +0x24 progress, +0x28 timeout_sec)
    """

    group_key: str
    folder_path: str
    filename: str
    file_path: str
    title: str
    subtitle: str = ""
    count: int = 1
    db_idx: int = -1
    progress: float = -1.0
    timeout_ms: int = 5000
    thumbnail: Optional[QPixmap] = None


class PicasaNotifierPopup(QWidget):
    """
    FR: Fenêtre surgissante « Picasa Notifier » reproduisant CNotifierPopup (0x00656FE0).
    S'ancre en bas à droite de la zone de travail de l'écran principal sans voler le focus,
    empile jusqu'à 3 cellules de dossiers/événements simultanées, affiche un aperçu miniature
    encadré (#7792A4) de la dernière photo détectée et se referme automatiquement après 5,0 s.

    EN: "Picasa Notifier" popup window reproducing CNotifierPopup (0x00656FE0).
    Docks at the bottom-right of the primary screen work area without stealing focus,
    stacks up to 3 simultaneous folder/event cells, renders a bordered thumbnail preview (#7792A4)
    of the latest detected photo, and auto-dismisses after 5.0 seconds.

    Ref: picasa3.exe @ 0x00656FE0..0x0065A300
    """

    # FR: Émis lors d'un clic sur une cellule : (file_path, folder_path) -> WM_USER + 0xFF (0x4FF)
    # EN: Emitted when a notification cell is clicked: (file_path, folder_path) -> WM_USER + 0xFF (0x4FF)
    notification_clicked = Signal(str, str)

    MAX_VISIBLE_CELLS = 3        # Ref: 0x006584BF (cmp dword ptr [esp + 0x38], 3)
    POPUP_WIDTH = 280            # Ref: 0x00658400 (largeur de la fenêtre surgissante)
    HEADER_HEIGHT = 22           # Ref: 0x00658640 (barre supérieure avec gripper, collapse et close)
    CELL_HEIGHT = 50             # Ref: 0x00658840 (hauteur d'une cellule de notification)
    THUMB_WIDTH = 38             # Ref: 0x006592B3 (push 0x26 = 38 px)
    THUMB_HEIGHT = 29            # Ref: 0x006592AD (push 0x1d = 29 px)
    THUMB_BORDER_COLOR = "#7792A4"  # Ref: 0x00659307 (push 0xFF7792A4)
    DEFAULT_TIMEOUT_MS = 5000    # Ref: 0x005719E6 (double @ 0x00CF4618 = 5.0 s)

    def __init__(self, style: Optional[PicasaStyle] = None, parent: Optional[QWidget] = None):
        """
        FR: Initialise la fenêtre surgissante Picasa Notifier et ses minuteries.
        EN: Initializes the Picasa Notifier popup window and its timers.
        Ref: picasa3.exe @ 0x00656FE0, 0x00657300
        """
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        self.setWindowTitle("Picasa Notifier")  # Ref: 0x00CA2730 ("Picasa Notifier")

        self.style_cfg = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.cells: List[NotifierCell] = []
        self.is_collapsed: bool = False  # Ref: [ebp + 0x314]
        self._hovered_cell_idx: int = -1
        self._hovered_close: bool = False
        self._hovered_collapse: bool = False

        # FR: Rectangles d'interaction calculés lors de la mise en page (Ref: 0x0065869C, 0x0065874A)
        # EN: Hit-test rectangles computed during layout (Ref: 0x0065869C, 0x0065874A)
        self._close_rect = QRect()
        self._collapse_rect = QRect()
        self._cell_rects: List[QRect] = []

        # FR: Minuterie d'auto-fermeture de 5,0 secondes (Ref: 0x005719E6, 0x00CF4618 = 5.0)
        # EN: 5.0-second auto-dismiss timer (Ref: 0x005719E6, 0x00CF4618 = 5.0)
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.setInterval(self.DEFAULT_TIMEOUT_MS)
        self.dismiss_timer.timeout.connect(self._on_dismiss_timeout)

        self._header_title = "Mis à jour"
        self._click_to_view_label = "Cliquer pour afficher"
        self.retranslate_ui()
        self.apply_style(self.style_cfg)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR: Applique le thème de couleurs actif à la fenêtre de notification.
        EN: Applies the active color theme to the notification popup window.
        """
        if style is not None:
            self.style_cfg = style
        self.update()

    def retranslate_ui(self) -> None:
        """
        FR: Met à jour les chaînes localisées depuis STRINGRES_*.XML (IDS_LISTUPDATED, clickview).
        EN: Updates localized strings from STRINGRES_*.XML (IDS_LISTUPDATED, clickview).
        Ref: picasa3.exe @ 0x00C83068 (IDS_LISTUPDATED), 0x0057D12B (CThumbUI::clickview)
        """
        updated_str = ""
        if self.res_mgr:
            updated_str = (
                self.res_mgr.get_stringres("IDS_LISTUPDATED", "")
                or self.res_mgr.get_xml_string("STRINGRES", "IDS_LISTUPDATED", "")
            ).strip()
        lang = self.res_mgr.get_current_language() if self.res_mgr else "fr"
        if not updated_str:
            updated_str = "Mis à jour" if lang.startswith("fr") else "Updated"
        self._header_title = updated_str

        if lang.startswith("fr"):
            self._click_to_view_label = "Cliquer pour afficher"
        else:
            self._click_to_view_label = "Click to view"
        self.update()

    def _load_thumbnail_pixmap(self, file_path: str) -> Optional[QPixmap]:
        """
        FR: Charge et redimensionne la vignette de la photo aux dimensions 38x29 avec son orientation EXIF/INI.
        EN: Loads and scales the photo thumbnail to 38x29 with its EXIF/INI orientation.
        Ref: picasa3.exe @ 0x005718DF (get 256px thumb), 0x00659270 (scale to 38x29 / 0x26 x 0x1d)
        """
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            from picasa_py.ui.image_processor import PicasaImageProcessor

            pil_img = PicasaImageProcessor.load_transformed_image(file_path)
            if pil_img is not None:
                pil_rgb = pil_img.convert("RGB")
                pil_rgb.thumbnail((self.THUMB_WIDTH * 2, self.THUMB_HEIGHT * 2))
                data = pil_rgb.tobytes("raw", "RGB")
                qimg = QImage(
                    data,
                    pil_rgb.width,
                    pil_rgb.height,
                    pil_rgb.width * 3,
                    QImage.Format.Format_RGB888,
                ).copy()
                pix = QPixmap.fromImage(qimg)
                if not pix.isNull():
                    return pix.scaled(
                        self.THUMB_WIDTH,
                        self.THUMB_HEIGHT,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        except Exception:
            pass

        try:
            pix = QPixmap(file_path)
            if not pix.isNull():
                return pix.scaled(
                    self.THUMB_WIDTH,
                    self.THUMB_HEIGHT,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        except Exception:
            pass
        return None

    def _format_cell_subtitle(self, filename: str, count: int) -> str:
        """
        FR: Formate le sous-titre d'une cellule selon le nombre de fichiers détectés dans le dossier.
        EN: Formats a cell's subtitle according to the number of files detected in the folder.
        Ref: picasa3.exe @ 0x0049FF10, 0x00658F20 (il_PopupNotifierRec::1..3)
        """
        lang = self.res_mgr.get_current_language() if self.res_mgr else "fr"
        if count <= 1:
            return filename
        if lang.startswith("fr"):
            return f"{count} photos mises à jour ({filename})"
        return f"{count} photos updated ({filename})"

    def notify_photo_indexed(
        self,
        folder_path: str,
        filename: str,
        file_path: str = "",
        db_idx: int = -1,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        show_popup: bool = True,
    ) -> NotifierCell:
        """
        FR: Ajoute ou met à jour une notification pour une photo nouvellement indexée ou modifiée.
        Si le dossier possède déjà une cellule active, incrémente son compteur, remplace la miniature
        par celle de la dernière photo et réinitialise le délai d'auto-fermeture de 5,0 s.

        EN: Adds or updates a notification for a newly indexed or modified photo.
        If the folder already has an active cell, increments its counter, updates the thumbnail
        to the latest photo, and resets the 5.0s auto-dismiss timer.

        Ref: picasa3.exe @ 0x00571850 (CThumbUI::NotifyPhotoAddedOrUpdated)
        Ref: picasa3.exe @ 0x00659340 (CNotifierPopup::AddOrUpdatePhotoNotification, vftable + 0x68)
        """
        clean_folder = folder_path.rstrip("\\/")
        norm_key = os.path.normcase(os.path.normpath(clean_folder)) if clean_folder else "__default__"
        folder_title = os.path.basename(clean_folder) or clean_folder or self._header_title
        full_path = file_path or (os.path.join(clean_folder, filename) if clean_folder and filename else "")
        thumb = self._load_thumbnail_pixmap(full_path)

        existing_cell: Optional[NotifierCell] = None
        for cell in self.cells:
            if cell.group_key == norm_key:
                existing_cell = cell
                break

        if existing_cell is not None:
            # Ref: 0x0065949A (add dword ptr [eax + 8], 1 -> incrémente le compteur du dossier)
            existing_cell.count += 1
            existing_cell.filename = filename
            existing_cell.file_path = full_path
            existing_cell.db_idx = db_idx
            existing_cell.title = folder_title
            existing_cell.subtitle = self._format_cell_subtitle(filename, existing_cell.count)
            existing_cell.timeout_ms = timeout_ms
            if thumb is not None:
                existing_cell.thumbnail = thumb
            target_cell = existing_cell
        else:
            target_cell = NotifierCell(
                group_key=norm_key,
                folder_path=clean_folder,
                filename=filename,
                file_path=full_path,
                title=folder_title,
                subtitle=self._format_cell_subtitle(filename, 1),
                count=1,
                db_idx=db_idx,
                timeout_ms=timeout_ms,
                thumbnail=thumb,
            )
            self.cells.insert(0, target_cell)
            # Conserver au maximum MAX_VISIBLE_CELLS * 2 en mémoire, 3 affichées (Ref: 0x006584BF)
            if len(self.cells) > 6:
                self.cells = self.cells[:6]

        self._update_layout_and_position()
        if show_popup:
            if not self.isVisible():
                self.show()
            self.raise_()
        self.update()

        if timeout_ms > 0:
            self.dismiss_timer.start(timeout_ms)
        return target_cell

    def update_progress(self, folder_path: str, progress: float) -> None:
        """
        FR: Met à jour la barre de progression d'une cellule active (0.0 à 1.0, ou -1.0 pour masquer).
        EN: Updates the progress bar of an active cell (0.0 to 1.0, or -1.0 to hide).
        Ref: picasa3.exe @ 0x00659CA0 (CNotifierPopup::UpdateProgress, vftable + 0x7C)
        """
        clean_folder = folder_path.rstrip("\\/")
        norm_key = os.path.normcase(os.path.normpath(clean_folder)) if clean_folder else "__default__"
        for cell in self.cells:
            if cell.group_key == norm_key:
                cell.progress = progress
                self.update()
                break

    def clear_notifications(self) -> None:
        """
        FR: Efface toutes les notifications et masque la fenêtre surgissante.
        EN: Clears all notifications and hides the popup window.
        """
        self.dismiss_timer.stop()
        self.cells.clear()
        self._cell_rects.clear()
        self.hide()

    def _on_dismiss_timeout(self) -> None:
        """
        FR: Masque automatiquement la fenêtre après l'expiration du délai de 5,0 secondes.
        EN: Automatically hides the popup window after the 5.0-second timeout expires.
        Ref: picasa3.exe @ 0x00657D60 (CNotifierPopup::OnTimer)
        """
        self.clear_notifications()

    def _update_layout_and_position(self) -> None:
        """
        FR: Calcule les rectangles des boutons/cellules et positionne la fenêtre en bas à droite
        de la zone de travail de l'écran principal (SPI_GETWORKAREA).
        EN: Computes button/cell rectangles and positions the window at the bottom-right corner
        of the primary screen work area (SPI_GETWORKAREA).
        Ref: picasa3.exe @ 0x00657341 (SystemParametersInfoW SPI_GETWORKAREA=0x30), 0x00658400
        """
        visible_cells = [] if self.is_collapsed else self.cells[: self.MAX_VISIBLE_CELLS]
        total_h = self.HEADER_HEIGHT + len(visible_cells) * self.CELL_HEIGHT + 2
        total_w = self.POPUP_WIDTH

        # Ref: 0x0065869C..0x0065874A (close button at right=width-5, top=4; collapse button to its left)
        self._close_rect = QRect(total_w - 20, 3, 15, 15)
        self._collapse_rect = QRect(total_w - 38, 3, 15, 15)

        self._cell_rects = []
        y = self.HEADER_HEIGHT
        for _ in visible_cells:
            self._cell_rects.append(QRect(2, y, total_w - 4, self.CELL_HEIGHT))
            y += self.CELL_HEIGHT

        self.setFixedSize(total_w, total_h)

        # Positionner en bas à droite de la zone de travail (availableGeometry = SPI_GETWORKAREA)
        screen = QApplication.primaryScreen()
        if screen is not None:
            work_area = screen.availableGeometry()
            x_pos = work_area.right() - total_w - 8
            y_pos = work_area.bottom() - total_h - 8
            self.move(max(work_area.left(), x_pos), max(work_area.top(), y_pos))

    def paintEvent(self, event) -> None:
        """
        FR: Dessine l'en-tête (« Mis à jour », gripper, boutons réduire/fermer), les cellules
        de dossiers modifiés, la barre de progression éventuelle et la miniature 38x29 encadrée (#7792A4).
        EN: Paints the header ("Updated", gripper, collapse/close buttons), the modified folder
        cells, any active progress bar, and the 38x29 bordered thumbnail (#7792A4).
        Ref: picasa3.exe @ 0x00658400..0x0065933D
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainterPath.RenderHint.Antialiasing if hasattr(QPainterPath, "RenderHint") else QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()

        bg_col = self.style_cfg.window_bgcolor if self.style_cfg else QColor("#F2F5F8")
        hdr_start = self.style_cfg.topbar_grad_start if self.style_cfg else QColor("#DCE4EC")
        hdr_end = self.style_cfg.topbar_grad_end if self.style_cfg else QColor("#C6D2DF")
        border_col = QColor(self.THUMB_BORDER_COLOR)  # Ref: 0x00659307 (#7792A4)
        text_col = self.style_cfg.alist_textcolor if self.style_cfg else QColor("#1E293B")
        sub_col = QColor("#526578") if bg_col.lightness() > 128 else QColor("#A8B8C8")
        accent_col = self.style_cfg.accent_color if self.style_cfg else QColor("#4A90D9")

        # 1. Fond général et bordure extérieure (#7792A4)
        painter.fillRect(0, 0, w, h, bg_col)

        # 2. Barre d'en-tête avec dégradé et texture gripper ("notifier/gripper" @ 0x00655B2B)
        hdr_grad = QLinearGradient(0, 0, 0, self.HEADER_HEIGHT)
        hdr_grad.setColorAt(0.0, hdr_start)
        hdr_grad.setColorAt(1.0, hdr_end)
        painter.fillRect(1, 1, w - 2, self.HEADER_HEIGHT - 1, hdr_grad)

        # Gripper à gauche (points en relief de "notifier/gripper")
        grip_col = QColor("#7792A4")
        for row in range(3):
            for col in range(2):
                painter.fillRect(6 + col * 3, 6 + row * 3, 2, 2, grip_col)

        # Titre de l'en-tête (IDS_LISTUPDATED : "Mis à jour " @ 0x00C83068)
        hdr_font = QFont("Tahoma", 8)
        hdr_font.setBold(True)
        painter.setFont(hdr_font)
        painter.setPen(text_col)
        total_items = sum(c.count for c in self.cells)
        hdr_text = f"{self._header_title} ({total_items})" if total_items > 1 else self._header_title
        painter.drawText(
            QRect(16, 0, w - 58, self.HEADER_HEIGHT),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            hdr_text,
        )

        # Bouton Réduire/Déplier ("notifier/collapse" @ 0x0065874A)
        if self._hovered_collapse:
            painter.fillRect(self._collapse_rect, QColor(119, 146, 164, 70))
        painter.setPen(text_col)
        arrow_char = "▴" if self.is_collapsed else "▾"
        painter.drawText(self._collapse_rect, Qt.AlignmentFlag.AlignCenter, arrow_char)

        # Bouton Fermer ("notifier/close" @ 0x0065869C)
        if self._hovered_close:
            painter.fillRect(self._close_rect, QColor(210, 60, 60, 180))
            painter.setPen(Qt.GlobalColor.white)
        else:
            painter.setPen(text_col)
        painter.drawText(self._close_rect, Qt.AlignmentFlag.AlignCenter, "✕")

        # Ligne de séparation sous l'en-tête
        painter.setPen(QPen(border_col, 1))
        painter.drawLine(1, self.HEADER_HEIGHT, w - 2, self.HEADER_HEIGHT)

        # 3. Cellules de notification (jusqu'à 3 cellules visibles — Ref: 0x006584BF)
        visible_cells = [] if self.is_collapsed else self.cells[: self.MAX_VISIBLE_CELLS]
        title_font = QFont("Tahoma", 9)
        title_font.setBold(True)
        sub_font = QFont("Tahoma", 8)
        fm_title = QFontMetrics(title_font)
        fm_sub = QFontMetrics(sub_font)

        for idx, cell in enumerate(visible_cells):
            if idx >= len(self._cell_rects):
                break
            rect = self._cell_rects[idx]

            # Survol de la cellule (cliquable pour localiser dans Picasa)
            if idx == self._hovered_cell_idx:
                hover_bg = QColor(accent_col)
                hover_bg.setAlpha(35)
                painter.fillRect(rect, hover_bg)

            # Zone de miniature à droite : 38x29 px, marge droite 6 px, centrée verticalement
            # Ref: 0x00658AE5..0x00658AF2 & 0x00659270..0x00659307
            thumb_x = rect.right() - self.THUMB_WIDTH - 6
            thumb_y = rect.top() + (rect.height() - self.THUMB_HEIGHT) // 2
            thumb_box = QRect(thumb_x, thumb_y, self.THUMB_WIDTH, self.THUMB_HEIGHT)

            painter.fillRect(thumb_box, QColor("#FFFFFF"))
            if cell.thumbnail is not None and not cell.thumbnail.isNull():
                pw = cell.thumbnail.width()
                ph = cell.thumbnail.height()
                dx = thumb_x + (self.THUMB_WIDTH - pw) // 2
                dy = thumb_y + (self.THUMB_HEIGHT - ph) // 2
                painter.drawPixmap(dx, dy, cell.thumbnail)

            # Bordure de 1 px #7792A4 autour de la miniature (Ref: 0x00659307 -> push 0xFF7792A4)
            painter.setPen(QPen(border_col, 1))
            painter.drawRect(thumb_box.adjusted(-1, -1, 0, 0))

            # Zone de texte à gauche de la miniature
            text_max_w = thumb_x - rect.left() - 12

            # Titre du dossier (Ref: 0x004AE0F0, Praxis Semi Bold 14px)
            painter.setFont(title_font)
            painter.setPen(text_col)
            elided_title = fm_title.elidedText(cell.title, Qt.TextElideMode.ElideRight, text_max_w)
            painter.drawText(
                QRect(rect.left() + 8, rect.top() + 5, text_max_w, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                elided_title,
            )

            # Sous-titre : nom du fichier ou compteur (Ref: 0x0049FF10, 0x00658F20)
            painter.setFont(sub_font)
            painter.setPen(sub_col)
            sub_str = cell.subtitle or cell.filename
            elided_sub = fm_sub.elidedText(sub_str, Qt.TextElideMode.ElideRight, text_max_w)
            painter.drawText(
                QRect(rect.left() + 8, rect.top() + 23, text_max_w, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                elided_sub,
            )

            # Barre de progression optionnelle ("notifier/progressbase" & "notifier/progressfill" @ 0x00658C00)
            if 0.0 <= cell.progress < 1.0:
                prog_rect = QRect(rect.left() + 8, rect.bottom() - 7, text_max_w, 4)
                painter.fillRect(prog_rect, QColor("#CBD5E1"))
                fill_w = max(2, int(text_max_w * min(1.0, max(0.0, cell.progress))))
                painter.fillRect(QRect(prog_rect.left(), prog_rect.top(), fill_w, 4), accent_col)

            # Séparateur entre cellules
            if idx < len(visible_cells) - 1:
                sep_col = QColor(border_col)
                sep_col.setAlpha(90)
                painter.setPen(QPen(sep_col, 1))
                painter.drawLine(rect.left() + 6, rect.bottom(), rect.right() - 6, rect.bottom())

        # Cadre extérieur #7792A4 (Ref: 0x00659307)
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(0, 0, w - 1, h - 1)
        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        FR: Met à jour l'état de survol des boutons et des cellules, et suspend le timer tant que la souris survole.
        EN: Updates hover state for buttons and cells, and pauses the auto-dismiss timer while hovered.
        """
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        old_close = self._hovered_close
        old_collapse = self._hovered_collapse
        old_cell = self._hovered_cell_idx

        self._hovered_close = self._close_rect.contains(pos)
        self._hovered_collapse = self._collapse_rect.contains(pos)
        self._hovered_cell_idx = -1
        for i, r in enumerate(self._cell_rects):
            if r.contains(pos):
                self._hovered_cell_idx = i
                break

        if self._hovered_close or self._hovered_collapse or self._hovered_cell_idx >= 0:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if (
            old_close != self._hovered_close
            or old_collapse != self._hovered_collapse
            or old_cell != self._hovered_cell_idx
        ):
            self.update()

        super().mouseMoveEvent(event)

    def enterEvent(self, event) -> None:
        """
        FR: Suspend la fermeture automatique tant que le curseur survole la notification.
        EN: Pauses auto-dismiss while the cursor hovers over the notification popup.
        """
        if self.dismiss_timer.isActive():
            self.dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """
        FR: Réinitialise le survol et relance le délai d'auto-fermeture lorsque la souris quitte la fenêtre.
        EN: Resets hover state and restarts the auto-dismiss timer when the cursor leaves the popup.
        """
        self._hovered_close = False
        self._hovered_collapse = False
        self._hovered_cell_idx = -1
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.cells and self.isVisible():
            self.dismiss_timer.start(self.DEFAULT_TIMEOUT_MS)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        FR: Gère le clic sur le bouton Fermer, le bouton Réduire ou sur une cellule de notification.
        Un clic sur une cellule émet notification_clicked(file_path, folder_path) conformément à
        PostMessage(hMainWnd, 0x4FF, group_id, item_id) dans picasa3.exe @ 0x00658056.

        EN: Handles clicks on the Close button, Collapse button, or a notification cell.
        Clicking a cell emits notification_clicked(file_path, folder_path) matching
        PostMessage(hMainWnd, 0x4FF, group_id, item_id) in picasa3.exe @ 0x00658056.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if self._close_rect.contains(pos):
                self.clear_notifications()
                event.accept()
                return
            if self._collapse_rect.contains(pos):
                self.is_collapsed = not self.is_collapsed
                self._update_layout_and_position()
                self.update()
                event.accept()
                return
            for i, r in enumerate(self._cell_rects):
                if r.contains(pos) and i < len(self.cells):
                    clicked_cell = self.cells.pop(i)
                    self.notification_clicked.emit(clicked_cell.file_path, clicked_cell.folder_path)
                    if not self.cells:
                        self.clear_notifications()
                    else:
                        self._update_layout_and_position()
                        self.update()
                    event.accept()
                    return
        super().mousePressEvent(event)
