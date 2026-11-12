"""
FR : Dialogue de gestion des contacts et personnes pour PyCasa (CContactMgrDialog / contactmgr.fen).
Gère toutes les personnes reconnues dans Picasa (contacts.xml), avatars, renommage, suppression et fusion.
EN : Contact & People Manager Dialog for PyCasa (CContactMgrDialog / contactmgr.fen).
Manages all recognized people in Picasa (contacts.xml), avatars, renaming, deletion, and merging.

Ref: picasa3.exe @ contactmgr.fen
Ref: ui/resources/xml/CONTACTMGR_FR.XML / CONTACTMGR.XML
Ref: picasa_py/db/contacts.py
"""

from __future__ import annotations
import os
import uuid
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QInputDialog, QFrame, QSplitter, QPlainTextEdit,
    QCheckBox
)
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QFont, QIcon, QPixmap, QDesktopServices

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.database import PicasaDatabase
from picasa_py.db.contacts import Contact, ContactsFile
from picasa_py.faces.face_manager import PersonCluster


class _MultiEmailEdit(QPlainTextEdit):
    """
    FR : Zone de saisie d'adresses e-mail multi-lignes (`height="3li" scroll="v"` dans `contactmgr.fen`)
    exposant également `.text()` et `.setText()` pour compatibilité avec l'API `QLineEdit`.
    EN : Multi-line email input box (`height="3li" scroll="v"` in `contactmgr.fen`)
    also exposing `.text()` and `.setText()` for `QLineEdit` API compatibility.
    Ref: picasa3.exe @ contactmgr.fen line 39, 0x007B7B97, 0x007B8E54
    """

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str) -> None:
        self.setPlainText(text or "")


class PicasaContactManagerDialog(QDialog):
    """
    FR : Gestionnaire de contacts et de personnes (contactmgr.fen / ContactManagerDlg).
    Ref: picasa3.exe @ 0x007B8F80 (ContactManagerDlg), 0x007B9240 (SelectContact), 0x006DB730 (PplAlbum::ID_ALBUM_EDITCAPTIONS)
    EN : Contact and people manager dialog (contactmgr.fen / ContactManagerDlg).
    """

    def __init__(
        self,
        db: PicasaDatabase,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None,
        initial_contact_id: Optional[str] = None,
        initial_person_name: Optional[str] = None,
    ):
        super().__init__(parent)
        self.db = db
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()
        self.initial_contact_id = (initial_contact_id or "").strip()
        self.initial_person_name = (initial_person_name or "").strip()

        self.setWindowTitle(self.res_mgr.get_xml_string("contactmgr/window1.title", "Personnes"))
        self.resize(620, 440)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Corps avec 2 colonnes (Liste gauche, Détails droite) — Ref: contactmgr.fen
        content_box = QHBoxLayout()
        content_box.setSpacing(14)

        # --- Colonne Gauche ---
        left_box = QVBoxLayout()
        left_box.setSpacing(6)

        self.lbl_search = QLabel(self.res_mgr.get_xml_string("contactmgr/labelgroup4.title", "Rechercher :"))
        left_box.addWidget(self.lbl_search)
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Filtrer les personnes...")
        self.search_edit = self.edit_search
        self._filter_contacts = self._filter_list
        self.edit_search.textChanged.connect(self._filter_list)
        left_box.addWidget(self.edit_search)

        self.list_contacts = QListWidget()
        self.list_contacts.setMinimumWidth(250)
        self.list_contacts.setIconSize(QSize(32, 32))
        self.list_contacts.currentRowChanged.connect(self._on_contact_selected)
        left_box.addWidget(self.list_contacts, 1)

        btns_left = QHBoxLayout()
        self.btn_delete = QPushButton(self.res_mgr.get_xml_string("contactmgr/delete.title", "Supprimer cette personne"))
        self.btn_delete.setToolTip(
            self.res_mgr.get_xml_string("contactmgr/delete.title", "Supprimer cette personne de Picasa")
        )
        self.btn_delete.clicked.connect(self._delete_person)
        btns_left.addWidget(self.btn_delete)

        self.btn_new = QPushButton(self.res_mgr.get_xml_string("contactmgr/create.title", "Nouveau contact"))
        self.btn_new.setToolTip(self.res_mgr.get_xml_string("contactmgr/create.title", "Créer une nouvelle personne"))
        self.btn_new.clicked.connect(self._create_person)
        btns_left.addWidget(self.btn_new)

        self.btn_merge = QPushButton("Fusionner...")
        self.btn_merge.setToolTip("Fusionner avec une autre personne existante")
        self.btn_merge.clicked.connect(self._merge_person)
        btns_left.addWidget(self.btn_merge)

        left_box.addLayout(btns_left)
        content_box.addLayout(left_box, 1)

        # --- Colonne Droite (Détails : thumb, count, online_contact, fullname, emails, sync, status, revert) ---
        right_box = QVBoxLayout()
        right_box.setSpacing(8)

        # Avatar, compteur "%d photo(s) dans Picasa" et statut "Contact en ligne" (Ref: contactmgr.fen lines 26-34, 0x007B8C11)
        avatar_box = QHBoxLayout()
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(64, 64)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_box.addWidget(self.lbl_avatar)

        meta_box = QVBoxLayout()
        meta_box.setSpacing(2)
        self.lbl_person_title = QLabel("Sélectionnez une personne")
        meta_box.addWidget(self.lbl_person_title)

        self.lbl_photo_count = QLabel(
            self.res_mgr.get_stringres("ContactManagerDlg::PhotosInPicasa", "%d photos dans Picasa") % 0
        )
        meta_box.addWidget(self.lbl_photo_count)

        self.lbl_online_contact = QLabel(
            self.res_mgr.get_xml_string("contactmgr/online_contact.title", "Contact en ligne")
        )
        meta_box.addWidget(self.lbl_online_contact)
        meta_box.addStretch(1)

        avatar_box.addLayout(meta_box, 1)
        right_box.addLayout(avatar_box)

        # Champ Nom (fullname) — Ref: contactmgr.fen line 35-37
        self.lbl_name_field = QLabel(self.res_mgr.get_xml_string("contactmgr/labelgroup22.title", "Nom :"))
        right_box.addWidget(self.lbl_name_field)
        self.edit_name = QLineEdit()
        self.edit_name.setMinimumWidth(250)
        right_box.addWidget(self.edit_name)

        # Champ Adresse(s) e-mail (emails, 3 lignes avec défilement vertical) — Ref: contactmgr.fen line 38-42
        self.lbl_email_field = QLabel(
            self.res_mgr.get_xml_string("contactmgr/labelgroup24.title", "Adresse(s) e-mail :")
        )
        right_box.addWidget(self.lbl_email_field)
        self.edit_email = _MultiEmailEdit()
        self.edit_email.setFixedHeight(62)
        self.edit_email.setPlaceholderText("adresse1@example.com\nadresse2@example.com")
        right_box.addWidget(self.edit_email)

        self.chk_sync = QCheckBox(
            self.res_mgr.get_xml_string("contactmgr/sync.title", "Synchroniser les tags de visage avec les albums Web")
        )
        right_box.addWidget(self.chk_sync)

        # Ligne Status + Rétablir (revert) + Enregistrer — Ref: contactmgr.fen line 63-66
        revert_row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        revert_row.addWidget(self.lbl_status, 1)

        self.btn_revert = QPushButton(self.res_mgr.get_xml_string("contactmgr/revert.title", "Rétablir"))
        self.btn_revert.clicked.connect(self._revert_current_person)
        revert_row.addWidget(self.btn_revert)

        self.btn_save_person = QPushButton("Appliquer")
        self.btn_save_person.clicked.connect(self._save_current_person)
        revert_row.addWidget(self.btn_save_person)
        right_box.addLayout(revert_row)

        right_box.addStretch(1)
        content_box.addLayout(right_box, 1)

        main_layout.addLayout(content_box, 1)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(self.sep)

        # Barre inférieure (Gérer les contacts en ligne, Actualiser les contacts, OK, Annuler) — Ref: contactmgr.fen lines 72-79
        btn_box = QHBoxLayout()
        self.btn_online = QPushButton(
            self.res_mgr.get_xml_string("contactmgr/online.title", "Gérer les contacts en ligne")
        )
        self.btn_online.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.google.com/contacts"))
        )
        btn_box.addWidget(self.btn_online)

        self.btn_refresh_contacts = QPushButton(
            self.res_mgr.get_xml_string("contactmgr/refresh_contacts.title", "Actualiser les contacts")
        )
        self.btn_refresh_contacts.clicked.connect(self._load_people)
        btn_box.addWidget(self.btn_refresh_contacts)

        btn_box.addStretch(1)
        self.btn_ok = QPushButton(self.res_mgr.get_xml_string("contactmgr/ok.title", "OK"))
        self.btn_ok.setObjectName("PrimaryBtn")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        btn_box.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("contactmgr/cancel.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_box)

        self.all_people: List[PersonCluster] = []
        self.current_person: Optional[PersonCluster] = None
        self.apply_style(self.style)
        self._load_people()
        if self.initial_contact_id or self.initial_person_name:
            self.select_person(self.initial_contact_id, self.initial_person_name)

    def apply_style(self, style: Optional[PicasaStyle] = None) -> None:
        """
        FR : Applique dynamiquement le thème Picasa actif au dialogue des contacts.
        EN : Dynamically applies the active Picasa theme to the contact manager dialog.
        """
        if style is not None:
            self.style = style
        s = self.style or PicasaStyle.instance()
        is_dark = getattr(s, "is_dark", False)
        bg = "#24272E" if is_dark else "#ECE9D8"
        fg = "#F0F2F5" if is_dark else "#111111"
        sub_fg = "#AEB6C2" if is_dark else "#222222"
        inp_bg = "#1E2127" if is_dark else "#FFFFFF"
        border = "#4B5263" if is_dark else "#7F9DB9"
        btn_bg = "#3A3F4B" if is_dark else "#F0F0F0"
        btn_hover = "#484E5C" if is_dark else "#E5E5E5"
        btn_border = "#555B69" if is_dark else "#707070"
        avatar_bg = "#1E2127" if is_dark else "#E0E0E0"

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
            QLineEdit, QPlainTextEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 4px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QCheckBox {{
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
                color: {fg};
            }}
            QListWidget {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
            }}
            QListWidget::item {{
                color: {fg};
                padding: 3px 6px;
            }}
            QListWidget::item:selected {{
                background-color: #316AC5;
                color: #FFFFFF;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {fg};
                border: 1px solid {btn_border};
                border-radius: 3px;
                padding: 4px 10px;
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
        self.lbl_avatar.setStyleSheet(f"border: 1px solid {border}; background-color: {avatar_bg}; color: {fg};")
        self.lbl_person_title.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {fg};")
        self.lbl_photo_count.setStyleSheet(f"color: {sub_fg}; font-size: 11px;")
        if hasattr(self, "lbl_online_contact"):
            self.lbl_online_contact.setStyleSheet(f"color: {sub_fg}; font-size: 11px;")
        if hasattr(self, "lbl_status"):
            self.lbl_status.setStyleSheet("color: #C0392B; font-size: 11px;")
        if hasattr(self, "sep"):
            self.sep.setStyleSheet(f"color: {border};")

    def retranslate_ui(self) -> None:
        """
        FR : Met à jour les textes de l'interface selon la langue active.
        EN : Updates the UI texts according to the active language.
        """
        self.setWindowTitle(self.res_mgr.get_xml_string("contactmgr/window1.title", "Personnes"))
        self.lbl_search.setText(self.res_mgr.get_xml_string("contactmgr/labelgroup4.title", "Rechercher :"))
        self.lbl_name_field.setText(self.res_mgr.get_xml_string("contactmgr/labelgroup22.title", "Nom :"))
        self.lbl_email_field.setText(
            self.res_mgr.get_xml_string("contactmgr/labelgroup24.title", "Adresse(s) e-mail :")
        )
        if hasattr(self, "lbl_online_contact"):
            self.lbl_online_contact.setText(
                self.res_mgr.get_xml_string("contactmgr/online_contact.title", "Contact en ligne")
            )
        if hasattr(self, "chk_sync"):
            self.chk_sync.setText(
                self.res_mgr.get_xml_string("contactmgr/sync.title", "Synchroniser les tags de visage avec les albums Web")
            )
        if hasattr(self, "btn_revert"):
            self.btn_revert.setText(self.res_mgr.get_xml_string("contactmgr/revert.title", "Rétablir"))
        if hasattr(self, "btn_online"):
            self.btn_online.setText(
                self.res_mgr.get_xml_string("contactmgr/online.title", "Gérer les contacts en ligne")
            )
        if hasattr(self, "btn_refresh_contacts"):
            self.btn_refresh_contacts.setText(
                self.res_mgr.get_xml_string("contactmgr/refresh_contacts.title", "Actualiser les contacts")
            )
        if hasattr(self, "btn_ok"):
            self.btn_ok.setText(self.res_mgr.get_xml_string("contactmgr/ok.title", "OK"))
        if hasattr(self, "btn_cancel"):
            self.btn_cancel.setText(self.res_mgr.get_xml_string("contactmgr/cancel.title", "Annuler"))

    def _format_photo_count(self, count: int) -> str:
        """
        FR : Formate le nombre de photos de la personne selon `ContactManagerDlg::PhotoInPicasa` /
        `ContactManagerDlg::PhotosInPicasa` (`0x007B8C11..0x007B8CAC`).
        EN : Formats the person's photo count according to `ContactManagerDlg::PhotoInPicasa` /
        `ContactManagerDlg::PhotosInPicasa` (`0x007B8C11..0x007B8CAC`).
        """
        if count == 1:
            tmpl = self.res_mgr.get_stringres("ContactManagerDlg::PhotoInPicasa", "%d photo dans Picasa")
        else:
            tmpl = self.res_mgr.get_stringres("ContactManagerDlg::PhotosInPicasa", "%d photos dans Picasa")
        try:
            return tmpl % count
        except Exception:
            return f"{count} photo(s) dans Picasa"

    def _get_person_photo_count(self, person: Optional[PersonCluster]) -> int:
        """
        FR : Calcule le nombre exact de photos associées à une personne dans Picasa.
        EN : Computes the exact number of photos associated with a person in Picasa.
        """
        if person is None:
            return 0
        cnt = getattr(person, "photo_count", 0) or len(getattr(person, "photo_indices", []) or [])
        if cnt == 0:
            fm = getattr(self.db, "face_manager", None)
            if fm is not None and hasattr(fm, "get_photos_for_person"):
                try:
                    paths = fm.get_photos_for_person(person.contact_id)
                    if paths:
                        cnt = len(paths)
                except Exception:
                    pass
        return cnt

    def select_person(self, contact_id: str, person_name: str = "") -> bool:
        """
        FR : Sélectionne une personne spécifique dans la liste (`ContactManagerDlg::SelectContact` @ `0x007B9240`).
        EN : Selects a specific person in the list (`ContactManagerDlg::SelectContact` @ `0x007B9240`).
        """
        cid_variants = set(ContactsFile._cid_variants(contact_id)) if contact_id else set()
        norm_name = (person_name or "").strip().lower()
        for r in range(self.list_contacts.count()):
            item = self.list_contacts.item(r)
            item_cid = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
            item_variants = set(ContactsFile._cid_variants(item_cid)) if item_cid else set()
            if (cid_variants and (item_cid.lower() in cid_variants or (item_variants & cid_variants))) or (
                norm_name and item.text().strip().lower() == norm_name
            ):
                self.list_contacts.setCurrentRow(r)
                self.edit_name.setFocus()
                self.edit_name.selectAll()
                return True
        return False

    def _load_people(self) -> None:
        self.list_contacts.clear()
        if not self.db:
            return

        people: List[PersonCluster] = []
        known_ids = set()
        fm = getattr(self.db, "face_manager", None)
        if fm is not None:
            people.extend(fm.get_people())
            for p in people:
                for v in fm._cid_variants(p.contact_id):
                    known_ids.add(v)

        # Inclure également les contacts du fichier contacts.xml si présents
        if getattr(self.db, "contacts", None) and hasattr(self.db.contacts, "contacts"):
            from picasa_py.faces.face_manager import PersonCluster
            contacts_data = self.db.contacts.contacts
            contacts_list = contacts_data.values() if isinstance(contacts_data, dict) else contacts_data
            for contact in contacts_list:
                cid = (getattr(contact, "id", None) or "").strip().lower()
                if cid and cid not in known_ids:
                    cluster = PersonCluster(contact_id=cid, name=getattr(contact, "name", "") or cid)
                    people.append(cluster)
                    if fm is not None:
                        for v in fm._cid_variants(cid):
                            known_ids.add(v)
                    else:
                        known_ids.add(cid)

        # Si le dialogue a été ouvert pour une personne précise pas encore dans la liste, l'inclure
        if self.initial_contact_id:
            init_variants = set(ContactsFile._cid_variants(self.initial_contact_id))
            if not (init_variants & known_ids):
                cluster = PersonCluster(
                    contact_id=self.initial_contact_id,
                    name=self.initial_person_name or self.initial_contact_id,
                )
                people.append(cluster)
                known_ids.update(init_variants)

        self.all_people = sorted(
            people,
            key=lambda p: (1 if getattr(p, "is_unknown", False) or not p.name else 0, (p.name or p.display_name or p.contact_id).lower()),
        )
        search_txt = self.edit_search.text().strip().lower()

        for p in self.all_people:
            label_text = p.name or getattr(p, "display_name", "") or p.contact_id
            if search_txt and search_txt not in label_text.lower():
                continue
            item = QListWidgetItem(label_text)
            item.setData(Qt.ItemDataRole.UserRole, p.contact_id)
            if (p.avatar_pixmap is None or p.avatar_pixmap.isNull()) and fm is not None:
                try:
                    fm.get_person_avatar(p.contact_id, size=32)
                except Exception:
                    pass
            if p.avatar_pixmap and not p.avatar_pixmap.isNull():
                item.setIcon(QIcon(p.avatar_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatioByExpanding)))
            self.list_contacts.addItem(item)

        if self.list_contacts.count() > 0:
            if not (self.initial_contact_id and self.select_person(self.initial_contact_id, self.initial_person_name)):
                self.list_contacts.setCurrentRow(0)
        else:
            self._on_contact_selected(-1)

    def _filter_list(self, text: Optional[str] = None) -> None:
        if text is not None and isinstance(text, str):
            self.edit_search.setText(text)
        self._load_people()

    def _on_contact_selected(self, row: int) -> None:
        if hasattr(self, "lbl_status"):
            self.lbl_status.setText("")
        if row < 0 or row >= self.list_contacts.count():
            self.current_person = None
            self.lbl_person_title.setText("Sélectionnez une personne")
            self.lbl_photo_count.setText("")
            if hasattr(self, "lbl_online_contact"):
                self.lbl_online_contact.setVisible(False)
            self.lbl_avatar.setPixmap(QPixmap())
            self.edit_name.clear()
            self.edit_name.setEnabled(False)
            self.edit_email.clear()
            self.edit_email.setEnabled(False)
            if hasattr(self, "chk_sync"):
                self.chk_sync.setChecked(False)
                self.chk_sync.setEnabled(False)
            if hasattr(self, "btn_revert"):
                self.btn_revert.setEnabled(False)
            self.btn_save_person.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_merge.setEnabled(False)
            return

        item = self.list_contacts.item(row)
        contact_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_person = None
        fm = getattr(self.db, "face_manager", None)
        if fm is not None:
            self.current_person = fm.get_person(contact_id)
        if not self.current_person:
            for p in self.all_people:
                if p.contact_id.lower() == str(contact_id).lower():
                    self.current_person = p
                    break

        if self.current_person:
            title_str = self.current_person.name or getattr(self.current_person, "display_name", "") or self.current_person.contact_id
            self.lbl_person_title.setText(title_str)
            count = self._get_person_photo_count(self.current_person)
            self.lbl_photo_count.setText(self._format_photo_count(count))
            if (self.current_person.avatar_pixmap is None or self.current_person.avatar_pixmap.isNull()) and fm is not None:
                try:
                    fm.get_person_avatar(self.current_person.contact_id, size=64)
                except Exception:
                    pass
            if self.current_person.avatar_pixmap and not self.current_person.avatar_pixmap.isNull():
                self.lbl_avatar.setPixmap(
                    self.current_person.avatar_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                )
            else:
                self.lbl_avatar.setPixmap(QPixmap())
                self.lbl_avatar.setText("👤")

            self.edit_name.setEnabled(True)
            self.edit_name.setText(self.current_person.name)
            self.edit_email.setEnabled(True)
            email_val = ""
            is_online = False
            sync_enabled = False
            if getattr(self.db, "contacts", None):
                c = self.db.contacts.get(self.current_person.contact_id)
                if c is not None:
                    c_emails = getattr(c, "emails", None)
                    if c_emails:
                        email_val = "\n".join(c_emails)
                    else:
                        email_val = getattr(c, "email", "") or ""
                    is_online = getattr(c, "local_contact", "1") == "0" or bool(email_val)
                    sync_enabled = c.extra_attrs.get("sync_enabled", "0") in ("1", "true", "yes")
            self.edit_email.setText(email_val)
            if hasattr(self, "lbl_online_contact"):
                self.lbl_online_contact.setVisible(is_online)
            if hasattr(self, "chk_sync"):
                self.chk_sync.setEnabled(True)
                self.chk_sync.setChecked(sync_enabled)
            if hasattr(self, "btn_revert"):
                self.btn_revert.setEnabled(True)
            self.btn_save_person.setEnabled(True)
            self.btn_delete.setEnabled(True)
            self.btn_merge.setEnabled(len(self.all_people) > 1)

    def _revert_current_person(self) -> None:
        """
        FR : Rétablit les champs Nom et Adresse(s) e-mail de la personne sélectionnée (`0x007B7B10`).
        EN : Reverts the Name and Email(s) fields for the selected person (`0x007B7B10`).
        """
        row = self.list_contacts.currentRow()
        if row >= 0:
            self._on_contact_selected(row)

    def _on_ok_clicked(self) -> None:
        """
        FR : Valide et enregistre automatiquement les modifications en cours avant de fermer (`0x007B99D3`).
        EN : Validates and automatically saves pending edits before closing (`0x007B99D3`).
        """
        if self.current_person is not None:
            new_name = self.edit_name.text().strip()
            if not new_name:
                msg = self.res_mgr.get_stringres("ContactManagerDlg::InvalidFullName", "Nom manquant")
                if hasattr(self, "lbl_status"):
                    self.lbl_status.setText(msg)
                return
            self._save_current_person(silent=True)
        self.accept()

    def _save_current_person(self, silent: bool = False) -> None:
        if not self.current_person:
            return
        new_name = self.edit_name.text().strip()
        if not new_name:
            if hasattr(self, "lbl_status"):
                self.lbl_status.setText(
                    self.res_mgr.get_stringres("ContactManagerDlg::InvalidFullName", "Nom manquant")
                )
            return
        new_email = self.edit_email.text().strip()

        old_name = self.current_person.name or getattr(self.current_person, "display_name", "") or self.current_person.contact_id
        cid = self.current_person.contact_id

        # Mettre à jour contacts.xml via self.db (notamment pour les adresses e-mail) avant rename_person
        self._update_contact_in_xml(cid, new_name, new_email)

        fm = getattr(self.db, "face_manager", None)
        if fm is not None and new_name != self.current_person.name:
            # FR : Déléguer à face_manager.rename_person pour synchroniser albumdata_name.pmp, .picasa.ini, contacts.xml et wordhash.dat
            # EN: Delegate to face_manager.rename_person to synchronize albumdata_name.pmp, .picasa.ini, contacts.xml and wordhash.dat
            fm.rename_person(cid, new_name)
            updated = fm.get_person(cid) or fm.get_person(new_name)
            if updated is not None:
                self.current_person = updated
                if self.current_person.contact_id != cid and new_email:
                    self._update_contact_in_xml(self.current_person.contact_id, self.current_person.name, new_email)
            else:
                self.current_person.name = new_name
        else:
            self.current_person.name = new_name

        self.lbl_person_title.setText(new_name)
        if hasattr(self, "lbl_status"):
            self.lbl_status.setText("")

        # Mettre à jour l'élément de la liste
        curr_item = self.list_contacts.currentItem()
        if curr_item:
            curr_item.setText(new_name)

        if fm is not None:
            fm.notify_people_changed()

        if not silent:
            if old_name != new_name:
                QMessageBox.information(self, "Personne modifiée", f"« {old_name} » a été renommé en « {new_name} ».")
            else:
                QMessageBox.information(self, "Personne modifiée", f"Les informations de « {new_name} » ont été enregistrées.")

    def _update_contact_in_xml(self, contact_id: str, new_name: str, new_email: Optional[str] = None) -> None:
        if not self.db:
            return
        if getattr(self.db, "contacts", None) is None:
            self.db.contacts = ContactsFile()
        existing = self.db.contacts.get(contact_id)
        sync_checked = bool(getattr(self, "chk_sync", None) and self.chk_sync.isChecked())
        if existing is not None:
            existing.name = new_name
            if new_email is not None:
                existing.email = new_email
            if sync_checked:
                existing.extra_attrs["sync_enabled"] = "1"
            else:
                existing.extra_attrs.pop("sync_enabled", None)
        else:
            c_obj = Contact(id=contact_id, name=new_name, email=new_email or "")
            if sync_checked:
                c_obj.extra_attrs["sync_enabled"] = "1"
            self.db.contacts.contacts.append(c_obj)
            existing = c_obj
        if hasattr(self.db, "save_contacts"):
            self.db.save_contacts()
        # Synchroniser également [Contacts2] (<cid>=<name>;<email>;) dans les fichiers .picasa.ini du contact
        # Ref: picasa3.exe @ 0x0068AD1C (WriteContacts2Section "%s=%s;%s;\r\n")
        if self.current_person and getattr(self.current_person, "photo_paths", None):
            from picasa_py.ini.parser import PicasaIniParser
            from picasa_py.ini.writer import PicasaIniWriter
            primary_email = (existing.email if existing is not None else (new_email or "")) or ""
            seen_dirs = set()
            for pp in self.current_person.photo_paths:
                if not pp:
                    continue
                d = os.path.dirname(pp)
                if not d or d in seen_dirs:
                    continue
                seen_dirs.add(d)
                for ini_name in (".picasa.ini", "Picasa.ini"):
                    ini_p = os.path.join(d, ini_name)
                    if os.path.exists(ini_p):
                        try:
                            doc = PicasaIniParser.parse_file(ini_p)
                            csec = doc.get_section("Contacts2")
                            if csec is not None and csec.get(contact_id) is not None:
                                csec.set(contact_id, f"{new_name};{primary_email};")
                                PicasaIniWriter.mark_internal_write(d)
                                doc.write_file(ini_p)
                                if hasattr(self.db, "invalidate_ini_cache"):
                                    self.db.invalidate_ini_cache(ini_p)
                        except Exception:
                            pass
                        break

    def _create_person(self) -> None:
        name, ok = QInputDialog.getText(self, "Nouveau contact", "Nom de la nouvelle personne :")
        if ok and name.strip():
            clean_name = name.strip()
            fm = getattr(self.db, "face_manager", None)
            if fm is not None:
                new_cluster = fm.create_person(clean_name)
                cid = new_cluster.contact_id
                self._update_contact_in_xml(cid, clean_name)
            else:
                cid = uuid.uuid4().hex[:16]
                self._update_contact_in_xml(cid, clean_name)
            self._load_people()
            # Sélectionner le nouvel élément
            for r in range(self.list_contacts.count()):
                if self.list_contacts.item(r).data(Qt.ItemDataRole.UserRole) == cid:
                    self.list_contacts.setCurrentRow(r)
                    break

    def _delete_person(self) -> None:
        if not self.current_person:
            return

        res = QMessageBox.question(
            self,
            "Supprimer la personne",
            f"Êtes-vous sûr de vouloir supprimer « {self.current_person.name} » de Picasa ?\n"
            "Cette action retire l'association de visage pour cette personne.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            cid = self.current_person.contact_id
            if getattr(self.db, "face_manager", None):
                self.db.face_manager.delete_person(cid)
            elif getattr(self.db, "contacts", None) and hasattr(self.db.contacts, "contacts"):
                self.db.contacts.contacts = [c for c in self.db.contacts.contacts if c.id.lower() != cid.lower()]
                if hasattr(self.db, "save_contacts"):
                    self.db.save_contacts()

            self._load_people()

    def _merge_person(self) -> None:
        if not self.current_person or len(self.all_people) <= 1:
            return

        other_people = [p for p in self.all_people if p.contact_id != self.current_person.contact_id]
        names = [p.name for p in other_people]

        target_name, ok = QInputDialog.getItem(
            self,
            "Fusionner des personnes",
            f"Fusionner « {self.current_person.name} » avec :",
            names,
            0,
            False
        )
        if ok and target_name:
            target_person = next((p for p in other_people if p.name == target_name), None)
            if not target_person:
                return

            old_cid = self.current_person.contact_id
            if getattr(self.db, "face_manager", None):
                # FR : Déléguer à face_manager.rename_person qui gère la fusion complète (.picasa.ini, PMP, wordhash.dat, contacts.xml)
                # EN: Delegate to face_manager.rename_person which handles full merge (.picasa.ini, PMP, wordhash.dat, contacts.xml)
                self.db.face_manager.rename_person(old_cid, target_person.name)

            self._load_people()
            QMessageBox.information(
                self,
                "Fusion réussie",
                f"Toutes les photos ont été rattachées à « {target_person.name} »."
            )
