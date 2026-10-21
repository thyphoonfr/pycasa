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
    QMessageBox, QInputDialog, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap

from picasa_py.ui.style import PicasaStyle
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.db.database import PicasaDatabase
from picasa_py.db.contacts import Contact, ContactsFile
from picasa_py.faces.face_manager import PersonCluster


class PicasaContactManagerDialog(QDialog):
    """
    FR : Gestionnaire de contacts et de personnes (contactmgr.fen).
    EN : Contact and people manager dialog (contactmgr.fen).
    """

    def __init__(
        self,
        db: PicasaDatabase,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QDialog] = None
    ):
        super().__init__(parent)
        self.db = db
        self.style = style or PicasaStyle.instance()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(self.res_mgr.get_xml_string("contactmgr/window1.title", "Personnes"))
        self.resize(600, 420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Corps avec 2 colonnes (Liste gauche, Détails droite)
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
        self.list_contacts.setIconSize(QSize(32, 32))
        self.list_contacts.currentRowChanged.connect(self._on_contact_selected)
        left_box.addWidget(self.list_contacts, 1)

        btns_left = QHBoxLayout()
        self.btn_new = QPushButton("Nouveau...")
        self.btn_new.setToolTip(self.res_mgr.get_xml_string("contactmgr/create.title", "Créer une nouvelle personne"))
        self.btn_new.clicked.connect(self._create_person)
        btns_left.addWidget(self.btn_new)

        self.btn_delete = QPushButton("Supprimer")
        self.btn_delete.setToolTip(
            self.res_mgr.get_xml_string("contactmgr/delete.title", "Supprimer cette personne de Picasa")
        )
        self.btn_delete.clicked.connect(self._delete_person)
        btns_left.addWidget(self.btn_delete)

        self.btn_merge = QPushButton("Fusionner...")
        self.btn_merge.setToolTip("Fusionner avec une autre personne existante")
        self.btn_merge.clicked.connect(self._merge_person)
        btns_left.addWidget(self.btn_merge)

        left_box.addLayout(btns_left)
        content_box.addLayout(left_box, 1)

        # --- Colonne Droite (Détails) ---
        right_box = QVBoxLayout()
        right_box.setSpacing(10)

        # Avatar et compteur
        avatar_box = QHBoxLayout()
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(64, 64)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_box.addWidget(self.lbl_avatar)

        meta_box = QVBoxLayout()
        self.lbl_person_title = QLabel("Sélectionnez une personne")
        meta_box.addWidget(self.lbl_person_title)

        self.lbl_photo_count = QLabel("0 photos associées")
        meta_box.addWidget(self.lbl_photo_count)
        meta_box.addStretch(1)

        avatar_box.addLayout(meta_box, 1)
        right_box.addLayout(avatar_box)

        # Champs éditables
        self.lbl_name_field = QLabel(self.res_mgr.get_xml_string("contactmgr/labelgroup22.title", "Nom :"))
        right_box.addWidget(self.lbl_name_field)
        self.edit_name = QLineEdit()
        right_box.addWidget(self.edit_name)

        self.lbl_email_field = QLabel(
            self.res_mgr.get_xml_string("contactmgr/labelgroup24.title", "Adresse(s) e-mail :")
        )
        right_box.addWidget(self.lbl_email_field)
        self.edit_email = QLineEdit()
        self.edit_email.setPlaceholderText("adresse@example.com")
        right_box.addWidget(self.edit_email)

        # Bouton Appliquer modifications
        self.btn_save_person = QPushButton("Enregistrer les modifications")
        self.btn_save_person.clicked.connect(self._save_current_person)
        right_box.addWidget(self.btn_save_person)

        right_box.addStretch(1)
        content_box.addLayout(right_box, 1)

        main_layout.addLayout(content_box, 1)

        # Séparateur
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(self.sep)

        # Boutons OK / Annuler
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        self.btn_ok = QPushButton("Fermer")
        self.btn_ok.setObjectName("PrimaryBtn")
        self.btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_ok)
        main_layout.addLayout(btn_box)

        self.all_people: List[PersonCluster] = []
        self.current_person: Optional[PersonCluster] = None
        self.apply_style(self.style)
        self._load_people()

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
            QLineEdit {{
                background-color: {inp_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 4px;
                font-family: Tahoma, "Segoe UI", sans-serif;
                font-size: 11px;
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

    def _load_people(self) -> None:
        self.list_contacts.clear()
        if not self.db:
            return

        people: List[PersonCluster] = []
        known_ids = set()
        if getattr(self.db, "face_manager", None):
            people.extend(self.db.face_manager.get_people())
            known_ids = {p.contact_id.lower() for p in people}

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
                    known_ids.add(cid)

        self.all_people = sorted(people, key=lambda p: p.name.lower())
        search_txt = self.edit_search.text().strip().lower()

        for p in self.all_people:
            if search_txt and search_txt not in p.name.lower():
                continue
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, p.contact_id)
            if p.avatar_pixmap and not p.avatar_pixmap.isNull():
                item.setIcon(QIcon(p.avatar_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatioByExpanding)))
            self.list_contacts.addItem(item)

        if self.list_contacts.count() > 0:
            self.list_contacts.setCurrentRow(0)
        else:
            self._on_contact_selected(-1)

    def _filter_list(self, text: Optional[str] = None) -> None:
        if text is not None and isinstance(text, str):
            self.edit_search.setText(text)
        self._load_people()

    def _on_contact_selected(self, row: int) -> None:
        if row < 0 or row >= self.list_contacts.count():
            self.current_person = None
            self.lbl_person_title.setText("Sélectionnez une personne")
            self.lbl_photo_count.setText("")
            self.lbl_avatar.setPixmap(QPixmap())
            self.edit_name.clear()
            self.edit_name.setEnabled(False)
            self.edit_email.clear()
            self.edit_email.setEnabled(False)
            self.btn_save_person.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_merge.setEnabled(False)
            return

        item = self.list_contacts.item(row)
        contact_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_person = None
        if getattr(self.db, "face_manager", None):
            self.current_person = self.db.face_manager.get_person(contact_id)
        if not self.current_person:
            for p in self.all_people:
                if p.contact_id.lower() == str(contact_id).lower():
                    self.current_person = p
                    break

        if self.current_person:
            self.lbl_person_title.setText(self.current_person.name)
            count = len(self.current_person.photo_indices)
            self.lbl_photo_count.setText(f"{count} photos associées")
            if self.current_person.avatar_pixmap and not self.current_person.avatar_pixmap.isNull():
                self.lbl_avatar.setPixmap(
                    self.current_person.avatar_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                )
            else:
                self.lbl_avatar.setText("👤")

            self.edit_name.setEnabled(True)
            self.edit_name.setText(self.current_person.name)
            self.edit_email.setEnabled(True)
            email_val = ""
            if getattr(self.db, "contacts", None) and hasattr(self.db.contacts, "contacts"):
                for c in self.db.contacts.contacts:
                    if c.id.lower() == self.current_person.contact_id.lower():
                        email_val = getattr(c, "email", "") or ""
                        break
            self.edit_email.setText(email_val)
            self.btn_save_person.setEnabled(True)
            self.btn_delete.setEnabled(True)
            self.btn_merge.setEnabled(len(self.all_people) > 1)

    def _save_current_person(self) -> None:
        if not self.current_person:
            return
        new_name = self.edit_name.text().strip()
        if not new_name:
            return
        new_email = self.edit_email.text().strip()

        old_name = self.current_person.name
        self.current_person.name = new_name
        self.lbl_person_title.setText(new_name)

        # Mettre à jour contacts.xml via self.db
        self._update_contact_in_xml(self.current_person.contact_id, new_name, new_email)

        # Mettre à jour l'élément de la liste
        curr_item = self.list_contacts.currentItem()
        if curr_item:
            curr_item.setText(new_name)

        if getattr(self.db, "face_manager", None):
            self.db.face_manager.notify_people_changed()

        QMessageBox.information(self, "Personne modifiée", f"« {old_name} » a été renommé en « {new_name} ».")

    def _update_contact_in_xml(self, contact_id: str, new_name: str, new_email: Optional[str] = None) -> None:
        if not self.db:
            return
        if getattr(self.db, "contacts", None) is None:
            self.db.contacts = ContactsFile()
        found = False
        for c in self.db.contacts.contacts:
            if c.id.lower() == contact_id.lower():
                c.name = new_name
                if new_email is not None:
                    c.email = new_email
                found = True
                break
        if not found:
            self.db.contacts.contacts.append(Contact(id=contact_id, name=new_name, email=new_email or ""))
        if hasattr(self.db, "save_contacts"):
            self.db.save_contacts()

    def _create_person(self) -> None:
        name, ok = QInputDialog.getText(self, "Nouveau contact", "Nom de la nouvelle personne :")
        if ok and name.strip():
            cid = uuid.uuid4().hex[:16]
            self._update_contact_in_xml(cid, name.strip())
            new_cluster = PersonCluster(contact_id=cid, name=name.strip())
            if getattr(self.db, "face_manager", None):
                self.db.face_manager.people[cid] = new_cluster
                self.db.face_manager.notify_people_changed()
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
            if getattr(self.db, "face_manager", None) and cid in self.db.face_manager.people:
                del self.db.face_manager.people[cid]
                self.db.face_manager.notify_people_changed()

            if getattr(self.db, "contacts", None) and hasattr(self.db.contacts, "contacts"):
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
            new_cid = target_person.contact_id

            # Mettre à jour les entrées faces= dans .picasa.ini pour les photos de l'ancienne personne
            if self.db and hasattr(self.db, "get_media_full_path") and hasattr(self.db, "update_photo_ini"):
                for idx in list(self.current_person.photo_indices):
                    full_path = self.db.get_media_full_path(idx)
                    if full_path and os.path.exists(full_path):
                        from pathlib import Path
                        ini_p = Path(full_path).parent / ".picasa.ini"
                        if ini_p.exists():
                            doc = self.db.get_parsed_ini(str(ini_p))
                            if doc:
                                sec = doc.get_section(Path(full_path).name)
                                if sec:
                                    faces_val = sec.get("faces", "")
                                    if old_cid in faces_val:
                                        self.db.update_photo_ini(
                                            full_path,
                                            {"faces": faces_val.replace(old_cid, new_cid)},
                                        )

            # Fusionner les listes de photos
            for idx in self.current_person.photo_indices:
                if idx not in target_person.photo_indices:
                    target_person.photo_indices.append(idx)

            # Supprimer l'ancienne personne
            if getattr(self.db, "face_manager", None) and old_cid in self.db.face_manager.people:
                del self.db.face_manager.people[old_cid]
                self.db.face_manager.notify_people_changed()

            if getattr(self.db, "contacts", None) and hasattr(self.db.contacts, "contacts"):
                self.db.contacts.contacts = [c for c in self.db.contacts.contacts if c.id.lower() != old_cid.lower()]
                if hasattr(self.db, "save_contacts"):
                    self.db.save_contacts()

            self._load_people()
            QMessageBox.information(
                self,
                "Fusion réussie",
                f"Toutes les photos ont été rattachées à « {target_person.name} »."
            )
