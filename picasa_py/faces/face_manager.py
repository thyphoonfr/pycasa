"""
Gestionnaire des visages et personnes de Picasa (PeoplePanel / FaceCluster / CFaceManager).

Regroupe les visages détectés par contact, gère l'extraction des avatars,
la correspondance entre la base PMP (imagedata_facerect, personalbumid)
et les fichiers .picasa.ini, et permet le filtrage dans la bibliothèque.

Ref: picasa3.exe @ 0x008AAD76, 0x008C1F34 (FaceSyncer)
Ref: picasa3.exe @ 0x009B9190 (rect64 decoder)
Ref: albumdata_category.pmp (cat=8 Person Album)
Ref: imagedata_facerect.pmp / imagedata_personalbumid.pmp
Ref: contacts/contacts.xml
"""

from __future__ import annotations
import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image
from PySide6.QtGui import QPixmap, QIcon

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import FaceRect, decode_rect64_string, encode_rect64_string
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.ini.model import IniSection, IniEntry


@dataclass
class PersonCluster:
    """
    Regroupement d'une personne identifiée dans Picasa avec ses clichés et son avatar.
    """
    contact_id: str
    name: str
    photo_indices: List[int] = field(default_factory=list)
    photo_paths: List[str] = field(default_factory=list)
    face_rects_by_photo: Dict[int, List[FaceRect]] = field(default_factory=dict)
    primary_face_rect: Optional[FaceRect] = None
    avatar_pixmap: Optional[QPixmap] = None

    @property
    def photo_count(self) -> int:
        return len(self.photo_indices)


class PicasaFaceManager:
    """
    Moteur unifié de détection, regroupement et affichage des visages Picasa.
    """

    def __init__(self, db: PicasaDatabase):
        self.db = db
        self.people: Dict[str, PersonCluster] = {}  # contact_id -> PersonCluster
        self.photo_to_faces: Dict[int, List[FaceRect]] = {}  # db_idx -> List[FaceRect]
        self._load_all_faces()

    def _load_all_faces(self) -> None:
        """Charge l'ensemble des personnes et visages depuis la base et les .ini."""
        contact_id_to_name: Dict[str, str] = {}
        album_idx_to_contact_id: Dict[int, str] = {}

        # 1. Lecture de contacts.xml
        if self.db.contacts:
            for c in self.db.contacts.contacts:
                contact_id_to_name[c.id.lower()] = c.name

        # 2. Lecture de albumdata (cat == 8 pour les albums de personnes)
        ad_names = self.db.pmps.get("albumdata_name")
        ad_cats = self.db.pmps.get("albumdata_category")
        ad_cids = self.db.pmps.get("albumdata_albumcontactids")

        if ad_names and ad_cats:
            for i in range(len(ad_names.records)):
                if ad_cats.records[i] == 8:
                    pname = ad_names.records[i]
                    cid_hex = ""
                    if ad_cids and i < len(ad_cids.records) and ad_cids.records[i]:
                        cid_num = ad_cids.records[i]
                        cid_hex = f"{cid_num:016x}"
                        album_idx_to_contact_id[i] = cid_hex

                    if not cid_hex:
                        cid_hex = f"pers_{i:04d}"
                        album_idx_to_contact_id[i] = cid_hex

                    if cid_hex not in contact_id_to_name:
                        contact_id_to_name[cid_hex] = pname

        # Initialiser les clusters de personnes
        for cid, name in contact_id_to_name.items():
            self.people[cid] = PersonCluster(contact_id=cid, name=name)

        # 3. Association depuis imagedata_personalbumid & imagedata_facerect
        pmp_personalbum = self.db.pmps.get("imagedata_personalbumid")
        pmp_facerect = self.db.pmps.get("imagedata_facerect")

        if pmp_personalbum:
            for db_idx, alb_idx in enumerate(pmp_personalbum.records):
                if alb_idx and alb_idx in album_idx_to_contact_id:
                    cid = album_idx_to_contact_id[alb_idx]
                    cluster = self.people.get(cid)
                    if cluster:
                        if db_idx not in cluster.photo_indices:
                            cluster.photo_indices.append(db_idx)

                        # Récupérer les coordonnées rect64 si disponibles
                        if pmp_facerect and db_idx < len(pmp_facerect.records):
                            rect_val = pmp_facerect.records[db_idx]
                            if rect_val:
                                fr = FaceRect.from_uint64(rect_val, contact_id=cid, contact_name=cluster.name)
                                self.photo_to_faces.setdefault(db_idx, []).append(fr)
                                cluster.face_rects_by_photo.setdefault(db_idx, []).append(fr)
                                if cluster.primary_face_rect is None:
                                    cluster.primary_face_rect = fr

        # 4. Association depuis les fichiers .picasa.ini sur disque
        self._scan_ini_faces(contact_id_to_name)

        # 5. Génération des avatars
        self._generate_avatars()

    def _scan_ini_faces(self, contact_id_to_name: Dict[str, str]) -> None:
        """Parcourt les fichiers .picasa.ini pour extraire les balises faces=."""
        # Indexer les photos de la base par (dossier_norm, filename_lower)
        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
        path_to_idx: Dict[Tuple[str, str], int] = {}

        for i, r in enumerate(self.db.index):
            if r.type != 1:
                fpath = folders_map.get(r.parent_idx, "")
                norm_d = fpath.replace("/", "\\").rstrip("\\").lower()
                path_to_idx[(norm_d, r.path.lower())] = i

        # Trouver tous les dossiers de photos indexés
        indexed_dirs = set(norm_d for norm_d, _ in path_to_idx.keys())
        for dpath in indexed_dirs:
            ini_file = os.path.join(dpath, ".picasa.ini")
            alt_ini = os.path.join(dpath, "Picasa.ini")
            target_ini = ini_file if os.path.exists(ini_file) else (alt_ini if os.path.exists(alt_ini) else None)
            if not target_ini:
                continue

            try:
                doc = PicasaIniParser.parse_file(target_ini)
                # Lire d'éventuels contacts locaux dans [Contacts2]
                sec_c2 = doc.get_section("Contacts2")
                if sec_c2:
                    for entry in sec_c2.entries:
                        if entry.key and entry.value:
                            k = entry.key
                            val = entry.value
                            cname = val.split(";")[0].strip() if ";" in val else val.strip()
                            if cname and k.lower() not in contact_id_to_name:
                                contact_id_to_name[k.lower()] = cname
                                self.people[k.lower()] = PersonCluster(contact_id=k.lower(), name=cname)

                # Lire les faces de chaque image
                for sec in doc.sections:
                    sec_name = sec.name
                    if sec_name.lower() in ("contacts2", "picasa", "encoding"):
                        continue
                    faces_entry = sec.get("faces")
                    if not faces_entry:
                        continue

                    db_idx = path_to_idx.get((dpath.lower(), sec_name.lower()))
                    full_file_path = os.path.join(dpath, sec_name)

                    # Parser "rect64(xxx),cid;rect64(yyy),cid2"
                    parts = faces_entry.split(";")
                    for p in parts:
                        p = p.strip()
                        if not p or "," not in p:
                            continue
                        r64_part, cid_part = p.split(",", 1)
                        cid_clean = cid_part.strip().lower()

                        cname = contact_id_to_name.get(cid_clean, cid_clean)
                        cluster = self.people.get(cid_clean)
                        if not cluster:
                            cluster = PersonCluster(contact_id=cid_clean, name=cname)
                            self.people[cid_clean] = cluster

                        fr = FaceRect.from_rect64(r64_part, contact_id=cid_clean, contact_name=cname)

                        if db_idx is not None:
                            if db_idx not in cluster.photo_indices:
                                cluster.photo_indices.append(db_idx)
                            self.photo_to_faces.setdefault(db_idx, []).append(fr)
                            cluster.face_rects_by_photo.setdefault(db_idx, []).append(fr)
                            if cluster.primary_face_rect is None:
                                cluster.primary_face_rect = fr

                        if full_file_path not in cluster.photo_paths:
                            cluster.photo_paths.append(full_file_path)
            except Exception:
                pass

    def _generate_avatars(self) -> None:
        """Génère l'avatar circulaire pour chaque personne."""
        for cid, cluster in self.people.items():
            if not cluster.photo_indices and not cluster.photo_paths:
                continue

            fr = cluster.primary_face_rect
            if not fr:
                continue

            # Tentative de découpe depuis la miniature thumbs_0.db (très rapide)
            avatar_created = False
            if cluster.photo_indices:
                first_idx = cluster.photo_indices[0]
                thumb_jpeg = self.db.get_thumbnail(first_idx)
                if thumb_jpeg:
                    try:
                        with Image.open(io.BytesIO(thumb_jpeg)) as img:
                            cluster.avatar_pixmap = fr.crop_avatar(img, avatar_size=64, circular=True)
                            avatar_created = True
                    except Exception:
                        pass

            # Si miniature non disponible, tenter depuis le fichier original sur disque
            if not avatar_created and cluster.photo_paths:
                first_path = cluster.photo_paths[0]
                if os.path.exists(first_path):
                    try:
                        with Image.open(first_path) as img:
                            cluster.avatar_pixmap = fr.crop_avatar(img, avatar_size=64, circular=True)
                            avatar_created = True
                    except Exception:
                        pass

    def get_people(self) -> List[PersonCluster]:
        """Renvoie la liste des personnes triées par nombre de photos décroissant."""
        return sorted(self.people.values(), key=lambda p: (p.photo_count, p.name), reverse=True)

    def get_person(self, contact_id: str) -> Optional[PersonCluster]:
        return self.people.get(contact_id.lower())

    def get_faces_for_photo(self, db_idx: int) -> List[FaceRect]:
        return self.photo_to_faces.get(db_idx, [])

    def save_face_tag(self, file_path: str, face_rect: FaceRect, contact_id: str, contact_name: str) -> None:
        """
        Enregistre une nouvelle balise de visage dans le .picasa.ini correspondant.
        """
        parent_dir = os.path.dirname(file_path)
        fname = os.path.basename(file_path)
        ini_path = os.path.join(parent_dir, ".picasa.ini")

        doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()

        # 1. Enregistrement dans [Contacts2]
        sec_c2 = doc.get_or_create_section("Contacts2")
        sec_c2.set(contact_id, f"{contact_name};;")

        # 2. Enregistrement sous [filename]
        sec_img = doc.get_or_create_section(fname)
        curr_faces = sec_img.get("faces", "")
        new_face_str = f"{face_rect.to_rect64()},{contact_id}"

        if curr_faces:
            # Remplacer ou ajouter
            faces_list = [f.strip() for f in curr_faces.split(";") if f.strip()]
            faces_list.append(new_face_str)
            sec_img.set("faces", ";".join(faces_list))
        else:
            sec_img.set("faces", new_face_str)

        # Sauvegarder .picasa.ini bit-exact
        with open(ini_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(doc.to_ini_string())
