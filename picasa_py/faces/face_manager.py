"""
FR : Gestionnaire des visages et personnes de Picasa (`PeoplePanel` / `FaceCluster` / `CFaceManager`).
Regroupe les visages détectés par contact, gère l'extraction des avatars,
la correspondance entre la base PMP (`imagedata_facerect`, `personalbumid`)
et les fichiers `.picasa.ini`, et permet le filtrage dans la bibliothèque.
EN: Picasa Face and People Manager (`PeoplePanel` / `FaceCluster` / `CFaceManager`).
Groups detected faces by contact, manages avatar extraction, synchronizes
PMP database tables (`imagedata_facerect`, `personalbumid`) with `.picasa.ini`
files, and provides people filtering in the photo library.

Ref: picasa3.exe @ 0x008AAD76, 0x008C1F34 (FaceSyncer)
Ref: picasa3.exe @ 0x009B9190 (rect64 decoder)
Ref: albumdata_category.pmp (cat=8 Person Album)
Ref: imagedata_facerect.pmp / imagedata_personalbumid.pmp
Ref: contacts/contacts.xml
"""

from __future__ import annotations
import io
import math
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QPixmap, QIcon


from picasa_py.db.database import PicasaDatabase
from picasa_py.db.contacts import Contact, ContactsFile
from picasa_py.faces.detector import (
    PicasaFaceDetector,
    FR_SUGGESTION_THRESHOLD,
    FR_SUGGESTION_SINGLE_THRESHOLD,
    FR_SORT_THRESHOLD,
)
from picasa_py.faces.facerect import FaceRect, decode_rect64_string, encode_rect64_string
from picasa_py.ini.parser import PicasaIniParser, PicasaIniDocument
from picasa_py.ini.model import IniSection, IniEntry, FaceItem


# Ref: picasa3.exe @ 0x0092C2F0 (FUN_0092c2f0 -> FaceRectOverlap)
# Ghidra project: ghidra/picasa3.gpr
def _face_overlap(f1: FaceRect, f2: FaceRect) -> float:
    """
    FR : Calcule le recouvrement géométrique entre deux rectangles de visages.
    EN: Compute geometric overlap ratio between two face bounding rectangles.
    """
    ix1 = max(f1.left, f2.left)
    iy1 = max(f1.top, f2.top)
    ix2 = min(f1.right, f2.right)
    iy2 = min(f1.bottom, f2.bottom)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    a1 = f1.width * f1.height
    a2 = f2.width * f2.height
    denom = min(a1, a2)
    return (intersection / denom) if denom > 0 else 0.0


@dataclass
class FaceSuggestion:
    """
    FR : Proposition de visage détecté mais non confirmé pour une personne donnée.
    EN: Suggested (unconfirmed) detected face for a given person/contact.
    Ref: picasa3.exe @ 0x0048AA80 (FRSuggestionThreshold), 0x00880B94 (suggestionpersonalbumid)
    """
    contact_id: str
    contact_name: str
    photo_path: str
    face_rect: FaceRect
    similarity: float
    db_idx: Optional[int] = None


@dataclass
class PersonCluster:
    """
    FR : Regroupement d'une personne identifiée dans Picasa avec ses clichés, son avatar et ses gabarits `vqc_Cue`.
    EN: Cluster representing an identified person in Picasa with their photos, avatar, and `vqc_Cue` templates.
    """
    contact_id: str
    name: str
    photo_indices: List[int] = field(default_factory=list)
    photo_paths: List[str] = field(default_factory=list)
    face_rects_by_photo: Dict[int, List[FaceRect]] = field(default_factory=dict)
    primary_face_rect: Optional[FaceRect] = None
    avatar_pixmap: Optional[QPixmap] = None
    feature_vector: Optional[np.ndarray] = None  # FR : Gabarit vqc_Cue 2000-D principal / EN: Primary 2000-D vqc_Cue template
    feature_vectors: List[np.ndarray] = field(default_factory=list)  # FR : Tous les gabarits 2000-D / EN: All 2000-D templates
    cover_photo_path: Optional[str] = None
    _avatar_pixmap: Optional[QPixmap] = field(default=None, init=False, repr=False, compare=False)
    _manager: Optional[Any] = field(default=None, init=False, repr=False, compare=False)
    _generating_avatar: bool = field(default=False, init=False, repr=False, compare=False)

    @property  # type: ignore[no-redef]
    def avatar_pixmap(self) -> Optional[QPixmap]:
        if self._avatar_pixmap is None and self._manager is not None and not self._generating_avatar:
            self._generating_avatar = True
            try:
                self._manager.get_person_avatar(self.contact_id, size=64, circular=True)
            except Exception:
                pass
            finally:
                self._generating_avatar = False
        return self._avatar_pixmap

    @avatar_pixmap.setter
    def avatar_pixmap(self, value: Optional[QPixmap]) -> None:
        if isinstance(value, property):
            value = None
        self._avatar_pixmap = value

    @property
    def photo_count(self) -> int:
        """
        FR : Nombre total de photos/visages confirmés associés à cette personne.
        Utilise en priorité `len(self.photo_indices)` (chaque entrée correspond à un enregistrement
        confirmé dans `imagedata_personalbumid`), ou le nombre de chemins normalisés uniques.
        EN: Total number of confirmed photos/faces associated with this person.
        Ref: picasa3.exe @ 0x0048AA80 (FRSuggestionSingleThreshold = 0.90 when photo_count <= 1)
        """
        if self.photo_indices:
            return len(self.photo_indices)
        if not self.photo_paths:
            return 0
        return len({os.path.normcase(os.path.normpath(p)) for p in self.photo_paths if p})


class PicasaFaceManager:
    """
    FR : Moteur unifié de détection, regroupement et affichage des visages Picasa.
    EN: Unified engine for Picasa face detection, clustering, and people management.
    """

    def __init__(self, db: PicasaDatabase):
        self.db = db
        self.detector = PicasaFaceDetector.get()
        self.people: Dict[str, PersonCluster] = {}  # contact_id -> PersonCluster
        self.photo_to_faces: Dict[int, List[FaceRect]] = {}  # db_idx -> List[FaceRect]
        self.suggestions: Dict[str, List[FaceSuggestion]] = {}  # contact_id -> List[FaceSuggestion]
        self.unnamed_faces: List[Tuple[Optional[int], str, FaceRect]] = []  # (db_idx, photo_path, FaceRect)
        self.on_people_changed_callbacks: List[Callable[[], None]] = []
        self._face_feature_cache: Dict[Tuple[Optional[int], float, float], np.ndarray] = {}
        self._avatar_cache: Dict[Tuple[Any, ...], QPixmap] = {}
        self._scanned_photo_indices: Set[int] = set()
        self._rejected_suggestions: Set[Tuple[int, str]] = set()
        self._suggestions_rebuilt: bool = False
        self._load_all_faces()


    def notify_people_changed(self) -> None:
        """
        FR : Notifie l'ensemble des composants d'interface (`CAlbumListUI`, grille, tiroirs)
        qu'une personne ou un visage a été ajouté, renommé, réassigné ou supprimé.
        EN: Notify all UI components (`CAlbumListUI`, thumbnail grid, drawers) that a person
        or face has been added, renamed, reassigned, or removed.
        Ref: picasa3.exe @ 0x008AAD76 (NOTIFY_PEOPLE_CHANGED)
        """
        if self.db and hasattr(self.db, "invalidate_search_cache"):
            self.db.invalidate_search_cache()
        for cb in list(self.on_people_changed_callbacks):
            try:
                cb()
            except Exception:
                pass

    def reload(self) -> None:
        """
        FR : Recharge l'ensemble des personnes et visages depuis la base PMP et les fichiers `.picasa.ini`.
        EN: Reload all people and face rectangles from the PMP database and `.picasa.ini` files.
        """
        if self.db and hasattr(self.db, "invalidate_search_cache"):
            self.db.invalidate_search_cache()
        self.people.clear()
        self.photo_to_faces.clear()
        self.suggestions.clear()
        self.unnamed_faces.clear()
        self._avatar_cache.clear()
        self._scanned_photo_indices.clear()
        self._person_vectors_loaded = False
        self._suggestions_rebuilt = False
        self._load_all_faces()

    def _load_all_faces(self) -> None:
        """
        FR : Charge l'ensemble des personnes et visages depuis la base PMP et les fichiers `.picasa.ini`.
        EN: Load all people and face rectangles from the PMP database and `.picasa.ini` files.
        """
        contact_id_to_name: Dict[str, str] = {}
        album_idx_to_contact_id: Dict[int, str] = {}

        # FR : 1. Lecture de contacts.xml
        # EN: 1. Read contacts.xml
        if self.db.contacts:
            for c in self.db.contacts.contacts:
                cname_clean = (c.name or "").strip()
                if not cname_clean or cname_clean.lower() in ("sans nom", "unnamed", "<personne inconnue>", "<unknown person>"):
                    continue
                contact_id_to_name[c.id.lower()] = cname_clean

        # FR : 2. Lecture de albumdata (cat == 8 pour les albums de personnes)
        # EN: 2. Read albumdata (cat == 8 for Person albums)
        ad_names = self.db.pmps.get("albumdata_name")
        ad_cats = self.db.pmps.get("albumdata_category")
        ad_cids = self.db.pmps.get("albumdata_albumcontactids")

        if ad_names and ad_cats:
            for i in range(len(ad_names.records)):
                if ad_cats.records[i] == 8:
                    pname = (ad_names.records[i] or "").strip()
                    # FR : Album 0 dans Picasa 3 est réservé aux visages sans nom (Ref: CThumbDB::unknownfacealbum @ 0x008AAD76)
                    # Ignorer également les albums factices "<Personne inconnue>" créés à partir d'IDs orphelins.
                    # EN: Album 0 in Picasa 3 is reserved for unnamed faces (Ref: CThumbDB::unknownfacealbum @ 0x008AAD76)
                    if i == 0 or not pname or pname.lower() in ("sans nom", "unnamed", "<personne inconnue>", "<unknown person>"):
                        continue
                    cid_hex = ""
                    if ad_cids and i < len(ad_cids.records) and ad_cids.records[i]:
                        cid_num = ad_cids.records[i]
                        cid_unpadded = f"{cid_num:x}"
                        cid_padded = f"{cid_num:016x}"
                        if cid_unpadded in contact_id_to_name:
                            cid_hex = cid_unpadded
                        elif cid_padded in contact_id_to_name:
                            cid_hex = cid_padded
                        else:
                            cid_hex = cid_unpadded
                        album_idx_to_contact_id[i] = cid_hex

                    if not cid_hex:
                        # FR : Chercher aussi par nom dans contact_id_to_name avant d'utiliser un ID synthétique
                        # EN: Also search by name in contact_id_to_name before falling back to a synthetic ID
                        for existing_cid, existing_name in contact_id_to_name.items():
                            if existing_name.strip().lower() == pname.strip().lower():
                                cid_hex = existing_cid
                                break
                        if not cid_hex:
                            cid_hex = f"{i:016x}"
                        album_idx_to_contact_id[i] = cid_hex

                    if cid_hex not in contact_id_to_name:
                        contact_id_to_name[cid_hex] = pname

        # FR : Initialiser les clusters de personnes
        # EN: Initialize person clusters
        for cid, name in contact_id_to_name.items():
            self.people[cid] = PersonCluster(contact_id=cid, name=name)

        # FR : 3. Association depuis imagedata_facerect, imagedata_personalbumid, imagedata_suggestionpersonalbumid
        # EN: 3. Link from imagedata_facerect, imagedata_personalbumid, imagedata_suggestionpersonalbumid
        pmp_facerect = self.db.pmps.get("imagedata_facerect")
        pmp_personalbum = self.db.pmps.get("imagedata_personalbumid")
        pmp_suggestion = self.db.pmps.get("imagedata_suggestionpersonalbumid")
        pmp_parecs = self.db.pmps.get("imagedata_personalbumrecs")

        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}

        # FR : Construire la table parent_photo_idx -> [child_1001_indices]
        # Dans picasa3.exe, lorsqu'une photo possède des sous-enregistrements de visages (type == 1001),
        # imagedata_facerect[parent_idx] stocke la boîte englobante d'union de tous les visages de la photo
        # et non un visage individuel. Chaque visage individuel est porté par son enregistrement 1001.
        # EN: Build parent_photo_idx -> [child_1001_indices] map.
        # In picasa3.exe, when a photo has child face records (type == 1001),
        # imagedata_facerect[parent_idx] stores the union bounding box of all faces on that photo
        # rather than an individual face. Each individual face is represented by its type 1001 record.
        # Ref: picasa3.exe @ 0x008AAD76, 0x009B93F0
        self._parent_to_1001: Dict[int, List[int]] = {}
        for i, r in enumerate(self.db.index):
            if r.type == 1001 and 0 <= r.parent_idx < len(self.db.index):
                pr = self.db.index[r.parent_idx]
                if pr.type not in (0, 1, 1001) and pr.path:
                    self._parent_to_1001.setdefault(r.parent_idx, []).append(i)

        def _get_photo_path(idx: int) -> str:
            if idx < len(self.db.index):
                r = self.db.index[idx]
                if r.type == 1001:
                    if 0 <= r.parent_idx < len(self.db.index):
                        pr = self.db.index[r.parent_idx]
                        if pr.type in (0, 1, 1001) or not pr.path:
                            return ""
                        fdir = folders_map.get(pr.parent_idx, "")
                        return os.path.normpath(os.path.join(fdir, pr.path)) if fdir else pr.path
                    return ""
                if r.type in (0, 1) or not r.path:
                    return ""
                fdir = folders_map.get(r.parent_idx, "")
                return os.path.normpath(os.path.join(fdir, r.path)) if fdir else r.path
            return ""

        ignored_rec_ids = (
            set(self.db.wordhash.search("]ignoreface"))
            if (self.db and getattr(self.db, "wordhash", None) is not None and hasattr(self.db.wordhash, "search"))
            else set()
        )
        self._ignored_rec_ids: Set[int] = ignored_rec_ids
        if pmp_facerect:
            for db_idx, rect_val in enumerate(pmp_facerect.records):
                if db_idx < len(self.db.index):
                    rec_obj = self.db.index[db_idx]
                    if rec_obj.type == 0:
                        continue
                    is_face_rec = bool(rec_obj.type == 1001)
                    if is_face_rec:
                        if not (0 <= rec_obj.parent_idx < len(self.db.index)):
                            continue
                        parent_rec = self.db.index[rec_obj.parent_idx]
                        if parent_rec.type == 0:
                            continue
                else:
                    is_face_rec = False
                if rect_val:
                    self._scanned_photo_indices.add(db_idx)
                    if is_face_rec:
                        parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
                        if parent_photo_idx is not None and parent_photo_idx >= 0:
                            self._scanned_photo_indices.add(parent_photo_idx)
                if not rect_val or rect_val <= 1:
                    continue

                # FR : Ignorer la boîte englobante d'union sur l'enregistrement photo parent s'il a des enfants 1001
                # EN: Skip the union bounding box on the parent photo record when it has type 1001 face children
                if not is_face_rec and db_idx in self._parent_to_1001:
                    continue

                # FR : Ignorer les visages explicitement marqués ]ignoreface dans wordhash.dat
                # EN: Skip faces explicitly marked ]ignoreface in wordhash.dat
                # Ref: picasa3.exe @ 0x00896FA8 (]ignoreface)
                if db_idx in ignored_rec_ids:
                    continue

                alb_idx = pmp_personalbum.records[db_idx] if pmp_personalbum and db_idx < len(pmp_personalbum.records) else 0
                sug_idx = pmp_suggestion.records[db_idx] if pmp_suggestion and db_idx < len(pmp_suggestion.records) else 0

                photo_path = _get_photo_path(db_idx)

                # FR : Priorité 1 : Visage attribué à une personne confirmée uniquement via imagedata_personalbumid
                # (imagedata_personalbumrecs stocke le plus proche voisin sur tous les visages 1001, même sans nom ou ignorés)
                # EN: Priority 1: Face assigned to a confirmed person strictly via imagedata_personalbumid
                # (imagedata_personalbumrecs stores the nearest neighbor on all 1001 faces, including unnamed or ignored ones)
                # Ref: picasa3.exe @ 0x00880B5C (personalbumid), 0x00880BBC (personalbumrecs)
                assigned_alb_idx = alb_idx if alb_idx in album_idx_to_contact_id else 0
                if assigned_alb_idx and assigned_alb_idx in album_idx_to_contact_id:
                    cid = album_idx_to_contact_id[assigned_alb_idx]
                    cluster = self.people.get(cid)
                    if cluster:
                        fr = FaceRect.from_uint64(rect_val, contact_id=cid, contact_name=cluster.name)
                        if db_idx not in cluster.photo_indices:
                            cluster.photo_indices.append(db_idx)
                        if photo_path and photo_path not in cluster.photo_paths:
                            cluster.photo_paths.append(photo_path)
                        self.photo_to_faces.setdefault(db_idx, []).append(fr)
                        cluster.face_rects_by_photo.setdefault(db_idx, []).append(fr)
                        if is_face_rec:
                            parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
                            if parent_photo_idx is not None and parent_photo_idx >= 0:
                                self.photo_to_faces.setdefault(parent_photo_idx, []).append(fr)
                                cluster.face_rects_by_photo.setdefault(parent_photo_idx, []).append(fr)
                        if cluster.primary_face_rect is None:
                            cluster.primary_face_rect = fr
                elif sug_idx and sug_idx in album_idx_to_contact_id:
                    # FR : Priorité 2 : Suggestion de visage pour une personne (Ref: 0x00880B94 suggestionpersonalbumid)
                    # EN: Priority 2: Face suggestion for a person (Ref: 0x00880B94 suggestionpersonalbumid)
                    cid = album_idx_to_contact_id[sug_idx]
                    cluster = self.people.get(cid)
                    cname = cluster.name if cluster else cid
                    fr = FaceRect.from_uint64(rect_val, contact_id="", contact_name=f"? {cname}")
                    sug = FaceSuggestion(
                        contact_id=cid,
                        contact_name=cname,
                        photo_path=photo_path,
                        face_rect=fr,
                        similarity=0.85,
                        db_idx=db_idx,
                    )
                    self.suggestions.setdefault(cid, []).append(sug)
                    self.photo_to_faces.setdefault(db_idx, []).append(fr)
                    if is_face_rec:
                        parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
                        if parent_photo_idx is not None and parent_photo_idx >= 0:
                            self.photo_to_faces.setdefault(parent_photo_idx, []).append(fr)
                else:
                    # FR : Priorité 3 : Visage sans nom (Ref: CThumbDB::unknownfacealbum @ 0x008AAD76)
                    # EN: Priority 3: Unnamed face (Ref: CThumbDB::unknownfacealbum @ 0x008AAD76)
                    fr_unnamed = FaceRect.from_uint64(rect_val, contact_id="", contact_name=None)
                    self.unnamed_faces.append((db_idx, photo_path, fr_unnamed))
                    self.photo_to_faces.setdefault(db_idx, []).append(fr_unnamed)
                    if is_face_rec:
                        parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
                        if parent_photo_idx is not None and parent_photo_idx >= 0:
                            self.photo_to_faces.setdefault(parent_photo_idx, []).append(fr_unnamed)

        elif pmp_personalbum:
            # FR : Fallback si imagedata_facerect est absent
            # EN: Fallback if imagedata_facerect is missing
            for db_idx, alb_idx in enumerate(pmp_personalbum.records):
                if alb_idx and alb_idx in album_idx_to_contact_id:
                    cid = album_idx_to_contact_id[alb_idx]
                    cluster = self.people.get(cid)
                    if cluster and db_idx not in cluster.photo_indices:
                        cluster.photo_indices.append(db_idx)

        # FR : 4. Association depuis les fichiers .picasa.ini sur disque
        # EN: 4. Link from on-disk .picasa.ini files
        self._scan_ini_faces(contact_id_to_name)

        # FR : 5. Génération des avatars
        # EN: 5. Avatar generation
        self._generate_avatars()

        # FR : 6. Restauration des couvertures personnalisées (Ref: ID_SETPEOPLEALBUMCOVER @ 0x008AF20B)
        # EN: 6. Restore custom person album covers (Ref: ID_SETPEOPLEALBUMCOVER @ 0x008AF20B)
        try:
            for cid, cluster in self.people.items():
                saved_path = None
                saved_rect64 = None
                if self.db and getattr(self.db, "contacts", None):
                    c_obj = self.db.contacts.get(cid)
                    if c_obj and c_obj.extra_attrs:
                        saved_path = c_obj.extra_attrs.get("cover_photo_path")
                        saved_rect64 = c_obj.extra_attrs.get("cover_rect64")
                if (not saved_path or not saved_rect64) and self.db and getattr(self.db, "repository", None):
                    saved_path = self.db.repository.get(f"PeopleCovers/{cid}/photo_path")
                    saved_rect64 = self.db.repository.get(f"PeopleCovers/{cid}/rect64")
                if saved_path and saved_rect64:
                    fr = FaceRect.from_rect64(str(saved_rect64), contact_id=cid, contact_name=cluster.name)
                    cluster.primary_face_rect = fr
                    cluster.cover_photo_path = str(saved_path)
        except Exception:
            pass

    def _find_matching_1001_child(self, parent_db_idx: Optional[int], target_fr: FaceRect) -> Optional[int]:
        """
        FR : Cherche parmi les sous-enregistrements de visages (`type == 1001`) d'une photo parente
        celui dont le rectangle `facerect` correspond à `target_fr`.
        EN: Search among a parent photo's face sub-records (`type == 1001`) for the one whose
        `facerect` matches `target_fr`.
        Ref: picasa3.exe @ 0x008AAD76, 0x009B93F0
        """
        if parent_db_idx is None or parent_db_idx < 0 or not self.db:
            return None
        parent_map = getattr(self, "_parent_to_1001", None)
        if parent_map is None:
            parent_map = {}
            for i, r in enumerate(self.db.index):
                if r.type == 1001 and 0 <= r.parent_idx < len(self.db.index):
                    parent_map.setdefault(r.parent_idx, []).append(i)
            self._parent_to_1001 = parent_map

        children = parent_map.get(parent_db_idx)
        if not children:
            return None

        pmp_facerect = self.db.pmps.get("imagedata_facerect")
        best_child: Optional[int] = None
        best_ov = 0.45
        for c_idx in children:
            c_faces = self.photo_to_faces.get(c_idx)
            if c_faces:
                ov = _face_overlap(c_faces[0], target_fr)
                if ov >= best_ov:
                    best_ov = ov
                    best_child = c_idx
            elif pmp_facerect and c_idx < len(pmp_facerect.records):
                rval = pmp_facerect.records[c_idx]
                if rval and rval > 1:
                    c_fr = FaceRect.from_uint64(rval)
                    ov = _face_overlap(c_fr, target_fr)
                    if ov >= best_ov:
                        best_ov = ov
                        best_child = c_idx
        return best_child

    def _get_or_create_1001_child(
        self,
        parent_db_idx: Optional[int],
        face_rect: FaceRect,
        source_img: Optional[Image.Image] = None,
    ) -> Optional[int]:
        """
        FR : Trouve ou crée un sous-enregistrement de visage (`type == 1001`) dans `thumbindex.db`
        et aligne les tables `imagedata_*` en enregistrant le `rect64` uint64 dans `imagedata_facerect.pmp`.
        EN: Find or create a child face record (`type == 1001`) in `thumbindex.db` and align
        `imagedata_*` tables, storing the uint64 `rect64` in `imagedata_facerect.pmp`.
        Ref: picasa3.exe @ 0x0072BA00, 0x008AAD76, 0x009B93F0
        """
        if parent_db_idx is None or parent_db_idx < 0 or not self.db:
            return None
        existing_child = self._find_matching_1001_child(parent_db_idx, face_rect)
        if existing_child is not None:
            pmp_fr = self.db.pmps.get("imagedata_facerect")
            if pmp_fr is not None:
                while len(pmp_fr.records) <= existing_child:
                    pmp_fr.records.append(0)
                pmp_fr.records[existing_child] = face_rect.to_uint64()
            return existing_child

        if getattr(self.db, "thumbindex", None) is None or parent_db_idx >= len(self.db.index):
            return None

        from picasa_py.db.thumbindex import ThumbIndexRecord

        with self.db._lock:
            existing_child = self._find_matching_1001_child(parent_db_idx, face_rect)
            if existing_child is not None:
                pmp_fr = self.db.pmps.get("imagedata_facerect")
                if pmp_fr is not None:
                    while len(pmp_fr.records) <= existing_child:
                        pmp_fr.records.append(0)
                    pmp_fr.records[existing_child] = face_rect.to_uint64()
                    pmp_fr.dirty = True
                return existing_child

            child_idx = len(self.db.index)
            # Ref: picasa3.exe @ 0x00414584 — sous-enregistrement visage : ft1=0, ft2=0, size=1, flags=0x0100
            # (vérifié sur db3 : 1458/1458 enregistrements type=1001)
            self.db.index.append(
                ThumbIndexRecord(
                    path="",
                    ft1=0,
                    ft2=0,
                    size=1,
                    parent_idx=parent_db_idx,
                    type=1001,
                    flags_hi=1,
                    flags_lo=0,
                )
            )
            if self.db.thumbindex is not None:
                self.db.thumbindex.dirty = True
            if hasattr(self.db, "_align_imagedata_tables"):
                self.db._align_imagedata_tables(child_idx)
            rect_u64 = face_rect.to_uint64()
            pmps = self.db.pmps

            def _setc(col: str, idx: int, val: Any) -> None:
                """
                FR : Écrit une valeur PMP en étendant la colonne si nécessaire et marque la table modifiée.
                EN: Writes a PMP value, extending the column if needed, and marks the table dirty.
                """
                p = pmps.get(col)
                if p is None:
                    return
                while len(p.records) <= idx:
                    p.records.append(p.default_value())
                if p.records[idx] != val:
                    p.records[idx] = val
                    p.dirty = True

            def _getc(col: str, idx: int, default: Any) -> Any:
                """
                FR : Lit une valeur PMP avec repli.
                EN: Reads a PMP value with fallback.
                """
                p = pmps.get(col)
                if p is None or idx >= len(p.records):
                    return default
                return p.records[idx]

            # FR : Colonnes du sous-enregistrement (db3 : filetype=1001, width/height/rotate du parent, crop64=facerect)
            # EN: Child record columns (db3: filetype=1001, parent width/height/rotate, crop64=facerect)
            _setc("imagedata_facerect", child_idx, rect_u64)
            _setc("imagedata_crop64", child_idx, rect_u64)
            _setc("imagedata_filetype", child_idx, 1001)
            _setc("imagedata_width", child_idx, _getc("imagedata_width", parent_db_idx, 0))
            _setc("imagedata_height", child_idx, _getc("imagedata_height", parent_db_idx, 0))
            _setc("imagedata_rotate", child_idx, _getc("imagedata_rotate", parent_db_idx, ""))
            conf = getattr(face_rect, "confidence", None)
            if conf is not None:
                try:
                    pan = float(getattr(face_rect, "pan", 0.0) or 0.0)
                    lx, ly = getattr(face_rect, "left_eye", (0.0, 0.0)) or (0.0, 0.0)
                    rx, ry = getattr(face_rect, "right_eye", (0.0, 0.0)) or (0.0, 0.0)
                    mx, my = getattr(face_rect, "mouth", (0.0, 0.0)) or (0.0, 0.0)
                    # Ref: picasa3.exe @ 0x00414584, formats @ 0x00C80C90
                    _setc(
                        "imagedata_facerectdata",
                        child_idx,
                        f"conf({float(conf):.3f}),pan({pan:.3f}),leye({lx:.3f},{ly:.3f}),"
                        f"reye({rx:.3f},{ry:.3f}),mouth({mx:.3f},{my:.3f})",
                    )
                    _setc("imagedata_facequality", child_idx, int(round(float(conf) * 100000)))
                except Exception:
                    pass

            # FR : Photo parente : facerect = boîte englobante union de tous ses visages, facerectdata = "1"
            # EN: Parent photo: facerect = union bounding box of all its faces, facerectdata = "1"
            # (db3 : 515/515 photos parentes)
            parent_map = getattr(self, "_parent_to_1001", None)
            if parent_map is not None:
                parent_map.setdefault(parent_db_idx, []).append(child_idx)
                sibling_idxs = parent_map.get(parent_db_idx, [child_idx])
            else:
                sibling_idxs = [child_idx]
            child_rects = [
                int(_getc("imagedata_facerect", k, 0)) for k in sibling_idxs
                if 0 <= k < len(self.db.index) and self.db.index[k].type == 1001
            ]
            child_rects = [v for v in child_rects if v > 1]
            if child_rects:
                u_l = min(v >> 48 for v in child_rects)
                u_t = min((v >> 32) & 0xFFFF for v in child_rects)
                u_r = max((v >> 16) & 0xFFFF for v in child_rects)
                u_b = max(v & 0xFFFF for v in child_rects)
                _setc("imagedata_facerect", parent_db_idx, (u_l << 48) | (u_t << 32) | (u_r << 16) | u_b)
                _setc("imagedata_facerectdata", parent_db_idx, "1")
                _setc("imagedata_deferredface", parent_db_idx, "")
            if getattr(self.db, "wordhash", None) is not None:
                self.db.wordhash.add_word("]face", parent_db_idx)
                self.db.wordhash.add_word("]unknownface", child_idx)
        try:
            parent_path = self.db.get_media_full_path(parent_db_idx) or ""
            if source_img is not None or (parent_path and os.path.exists(parent_path)):
                self._write_face_record_thumbnails(
                    child_idx, face_rect, photo_path=parent_path, source_img=source_img
                )
        except Exception:
            pass
        return child_idx

    _create_face_db_record = _get_or_create_1001_child

    def _scan_ini_faces(self, contact_id_to_name: Dict[str, str]) -> None:
        """
        FR : Parcourt les fichiers `.picasa.ini` pour extraire les balises `faces=` en complexité $O(N)$.
        EN: Scan `.picasa.ini` files to extract `faces=` tags in $O(N)$ complexity.
        """
        # FR : Indexer les photos de la base par (dossier_norm, filename_lower) en conservant la casse canonique
        # EN: Index database photos by (normalized_folder, filename_lower) while preserving canonical casing
        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
        path_to_idx: Dict[Tuple[str, str], int] = {}
        canonical_dirs: Dict[str, str] = {}

        for i, r in enumerate(self.db.index):
            if r.type not in (0, 1, 1001) and r.path:
                fpath = folders_map.get(r.parent_idx, "")
                orig_d = fpath.replace("/", "\\").rstrip("\\")
                norm_d = orig_d.lower()
                if norm_d and norm_d not in canonical_dirs:
                    canonical_dirs[norm_d] = orig_d
                path_to_idx[(norm_d, r.path.lower())] = i

        pmp_personalbum = self.db.pmps.get("imagedata_personalbumid") if self.db else None
        pmp_suggestion = self.db.pmps.get("imagedata_suggestionpersonalbumid") if self.db else None
        unknown_rec_ids = (
            set(self.db.wordhash.search("]unknownface"))
            if (self.db and getattr(self.db, "wordhash", None) is not None and hasattr(self.db.wordhash, "search"))
            else set()
        )
        ignored_set = getattr(self, "_ignored_rec_ids", set())

        # FR : Indexation O(1) de unnamed_faces et suggestions par db_idx et par chemin normalisé
        # pour éviter le filtrage quadratique O(N * U) à chaque visage nommé.
        # EN: O(1) indexing of unnamed_faces and suggestions by db_idx and normalized path
        # to avoid quadratic O(N * U) filtering on every named face.
        unnamed_by_idx: Dict[int, List[int]] = {}
        unnamed_by_path: Dict[str, List[int]] = {}
        unnamed_removed: Set[int] = set()
        for pos, (u_idx, u_path, _) in enumerate(self.unnamed_faces):
            if u_idx is not None:
                unnamed_by_idx.setdefault(u_idx, []).append(pos)
            if u_path:
                norm_u = os.path.normpath(u_path).lower()
                unnamed_by_path.setdefault(norm_u, []).append(pos)

        sug_by_idx: Dict[int, List[Tuple[str, FaceSuggestion]]] = {}
        sug_by_path: Dict[str, List[Tuple[str, FaceSuggestion]]] = {}
        sug_removed_ids: Set[int] = set()
        for s_cid, s_list in self.suggestions.items():
            for s in s_list:
                if s.db_idx is not None:
                    sug_by_idx.setdefault(s.db_idx, []).append((s_cid, s))
                if s.photo_path:
                    norm_s = os.path.normpath(s.photo_path).lower()
                    sug_by_path.setdefault(norm_s, []).append((s_cid, s))

        # FR : Trouver tous les dossiers de photos indexés
        # EN: Collect all indexed photo directories
        indexed_dirs = set(norm_d for norm_d, _ in path_to_idx.keys())
        is_bg_thread = threading.current_thread() is not threading.main_thread()
        for dir_idx, dpath in enumerate(indexed_dirs):
            if is_bg_thread and dir_idx > 0 and (dir_idx % 8) == 0:
                try:
                    from picasa_py.scanner.scanner import BackgroundScanWorker
                    BackgroundScanWorker.yield_for_gui(0.001)
                except Exception:
                    pass
            ini_file = os.path.join(dpath, ".picasa.ini")
            alt_ini = os.path.join(dpath, "Picasa.ini")

            try:
                if self.db and hasattr(self.db, "get_parsed_ini"):
                    doc = self.db.get_parsed_ini(ini_file)
                    if doc is None:
                        doc = self.db.get_parsed_ini(alt_ini)
                else:
                    target_ini = ini_file if os.path.exists(ini_file) else (alt_ini if os.path.exists(alt_ini) else None)
                    doc = PicasaIniParser.parse_file(target_ini) if target_ini else None
                if not doc:
                    continue
                # FR : Lire d'éventuels contacts locaux dans [Contacts2]
                # EN: Read local contacts from [Contacts2] if present
                sec_c2 = doc.get_section("Contacts2")
                if sec_c2:
                    for entry in sec_c2.entries:
                        if entry.key and entry.value:
                            k = entry.key.strip().lower()
                            k_unpadded = k.lstrip("0") or "0"
                            k_padded = k.zfill(16)
                            val = entry.value
                            cname = val.split(";")[0].strip() if ";" in val else val.strip()
                            if cname and cname.lower() not in ("sans nom", "unnamed", "<personne inconnue>", "<unknown person>"):
                                if k in contact_id_to_name or k_unpadded in contact_id_to_name or k_padded in contact_id_to_name:
                                    continue
                                contact_id_to_name[k] = cname
                                self.people[k] = PersonCluster(contact_id=k, name=cname)

                # FR : Lire les faces de chaque image
                # EN: Read face rectangles for each image section
                orig_dir = canonical_dirs.get(dpath, dpath)
                for sec in doc.sections:
                    sec_name = sec.name
                    if sec_name.lower() in ("contacts2", "picasa", "encoding"):
                        continue
                    faces_entry = sec.get("faces")
                    if not faces_entry:
                        continue

                    photo_db_idx = path_to_idx.get((dpath.lower(), sec_name.lower()))
                    if photo_db_idx is not None and 0 <= photo_db_idx < len(self.db.index):
                        canon_fname = self.db.index[photo_db_idx].path or sec_name
                        full_file_path = os.path.normpath(os.path.join(orig_dir, canon_fname))
                        self._scanned_photo_indices.add(photo_db_idx)
                    else:
                        full_file_path = os.path.normpath(os.path.join(orig_dir, sec_name))
                        if not os.path.exists(full_file_path):
                            continue

                    norm_full = os.path.normpath(full_file_path).lower() if full_file_path else ""

                    # FR : Parser "rect64(xxx),cid;rect64(yyy),cid2"
                    # EN: Parse "rect64(xxx),cid;rect64(yyy),cid2"
                    parts = faces_entry.split(";")
                    for p in parts:
                        p = p.strip()
                        if not p or "," not in p:
                            continue
                        r64_part, cid_part = p.split(",", 1)
                        cid_clean = cid_part.strip().lower()

                        # FR : Dans picasa3.exe @ 0x00484AE5..0x00484BE3 (WriteFacesToIni) :
                        # - Si personalbumid == 0 et IsFaceIgnored(rec) != 0 (]ignoreface), picasa3.exe écrit
                        #   `push -1; push -1; call 0x00413630` -> `rect64(...),ffffffffffffffff` dans .picasa.ini.
                        # - Si personalbumid == 0 et IsFaceIgnored(rec) == 0 (visage sans nom), picasa3.exe NE l'écrit PAS
                        #   dans .picasa.ini (`je 0x00484be3`).
                        # EN: In picasa3.exe @ 0x00484AE5..0x00484BE3 (WriteFacesToIni):
                        # - When personalbumid == 0 and IsFaceIgnored(rec) != 0 (]ignoreface), picasa3.exe writes
                        #   `rect64(...),ffffffffffffffff` (-1) to .picasa.ini.
                        # - When personalbumid == 0 and IsFaceIgnored(rec) == 0 (unnamed face), it is NOT written to .picasa.ini.
                        if cid_clean == "ffffffffffffffff":
                            fr_ignored = FaceRect.from_rect64(r64_part, contact_id="", contact_name=None)
                            child_1001 = self._find_matching_1001_child(photo_db_idx, fr_ignored)
                            eff_idx = child_1001 if child_1001 is not None else photo_db_idx
                            u_cands_ign: List[int] = []
                            if eff_idx is not None and eff_idx in unnamed_by_idx:
                                u_cands_ign.extend(unnamed_by_idx[eff_idx])
                            if photo_db_idx is not None and photo_db_idx != eff_idx and photo_db_idx in unnamed_by_idx:
                                u_cands_ign.extend(unnamed_by_idx[photo_db_idx])
                            if norm_full and norm_full in unnamed_by_path:
                                u_cands_ign.extend(unnamed_by_path[norm_full])
                            for pos in u_cands_ign:
                                if pos not in unnamed_removed and _face_overlap(self.unnamed_faces[pos][2], fr_ignored) >= 0.45:
                                    unnamed_removed.add(pos)
                            s_cands_ign: List[Tuple[str, FaceSuggestion]] = []
                            if eff_idx is not None and eff_idx in sug_by_idx:
                                s_cands_ign.extend(sug_by_idx[eff_idx])
                            if photo_db_idx is not None and photo_db_idx != eff_idx and photo_db_idx in sug_by_idx:
                                s_cands_ign.extend(sug_by_idx[photo_db_idx])
                            if norm_full and norm_full in sug_by_path:
                                s_cands_ign.extend(sug_by_path[norm_full])
                            for _, s_obj in s_cands_ign:
                                if id(s_obj) not in sug_removed_ids and _face_overlap(s_obj.face_rect, fr_ignored) >= 0.45:
                                    sug_removed_ids.add(id(s_obj))
                            continue

                        # FR : Visage sans nom ou non assigné explicite (ex. base de test synthétique sans enregistrements 1001)
                        # Dans picasa3.exe (@ 0x00484B10..0x00484BE3), les visages sans nom sont portés exclusivement
                        # par les enregistrements `type == 1001` dans `thumbindex.db` / `imagedata_facerect.pmp` et ne
                        # sont jamais écrits avec `,0` dans `.picasa.ini`. Si la base possède des enregistrements 1001
                        # (`self._parent_to_1001` non vide), ignorer toute entrée `,0` orpheline sans enfant `1001`.
                        # EN: Explicit unnamed or unassigned face (e.g. synthetic test DB without 1001 records).
                        # In picasa3.exe (@ 0x00484B10..0x00484BE3), unnamed faces live exclusively on `type == 1001`
                        # records in `thumbindex.db` / `imagedata_facerect.pmp`. When the DB has 1001 records
                        # (`self._parent_to_1001` non-empty), skip any orphan `,0` entry that has no matching 1001 child.
                        if not cid_clean or cid_clean in ("unknown", "unnamed", "0"):
                            fr_unnamed = FaceRect.from_rect64(r64_part, contact_id="", contact_name=None)
                            child_1001 = self._find_matching_1001_child(photo_db_idx, fr_unnamed)
                            if self._parent_to_1001 and child_1001 is None:
                                continue
                            eff_idx = child_1001 if child_1001 is not None else photo_db_idx
                            ignored_set = getattr(self, "_ignored_rec_ids", set())
                            if eff_idx is not None and eff_idx in ignored_set:
                                continue
                            # FR : Si ce visage est déjà nommé ou suggéré dans la base PMP (via son 1001), ne pas le ré-ajouter en sans-nom
                            # EN: If this face is already named or suggested in the PMP DB (via its 1001 record), do not re-add as unnamed
                            if eff_idx is not None and any(
                                ef.contact_id or (ef.contact_name and ef.contact_name.startswith("? "))
                                for ef in self.photo_to_faces.get(eff_idx, [])
                                if _face_overlap(ef, fr_unnamed) >= 0.45
                            ):
                                continue
                            cand_positions: List[int] = []
                            if eff_idx is not None and eff_idx in unnamed_by_idx:
                                cand_positions.extend(unnamed_by_idx[eff_idx])
                            if norm_full and norm_full in unnamed_by_path:
                                cand_positions.extend(unnamed_by_path[norm_full])
                            already_present = any(
                                pos not in unnamed_removed and _face_overlap(self.unnamed_faces[pos][2], fr_unnamed) >= 0.45
                                for pos in cand_positions
                            )
                            if not already_present:
                                new_pos = len(self.unnamed_faces)
                                self.unnamed_faces.append((eff_idx, full_file_path, fr_unnamed))
                                if eff_idx is not None:
                                    unnamed_by_idx.setdefault(eff_idx, []).append(new_pos)
                                if norm_full:
                                    unnamed_by_path.setdefault(norm_full, []).append(new_pos)
                            if eff_idx is not None:
                                existing_eff = self.photo_to_faces.setdefault(eff_idx, [])
                                if not any(_face_overlap(ef, fr_unnamed) >= 0.45 for ef in existing_eff):
                                    existing_eff.append(fr_unnamed)
                            if photo_db_idx is not None and photo_db_idx != eff_idx:
                                existing_parent = self.photo_to_faces.setdefault(photo_db_idx, [])
                                if not any(_face_overlap(ef, fr_unnamed) >= 0.45 for ef in existing_parent):
                                    existing_parent.append(fr_unnamed)
                            continue

                        if cid_clean not in contact_id_to_name:
                            cid_unpadded = cid_clean.lstrip("0") or "0"
                            cid_padded = cid_clean.zfill(16)
                            if cid_unpadded in contact_id_to_name:
                                cid_clean = cid_unpadded
                            elif cid_padded in contact_id_to_name:
                                cid_clean = cid_padded

                        fr = FaceRect.from_rect64(r64_part, contact_id=cid_clean, contact_name=contact_id_to_name.get(cid_clean, cid_clean))
                        child_1001 = self._find_matching_1001_child(photo_db_idx, fr)
                        eff_idx = child_1001 if child_1001 is not None else photo_db_idx

                        # FR : Si l'enregistrement 1001 existe déjà dans la base PMP (thumbindex.db) :
                        # - s'il est marqué ]ignoreface, ne jamais le promouvoir en visage confirmé ;
                        # - s'il a imagedata_personalbumid == 0 et qu'il s'agit d'une suggestion en attente
                        #   (imagedata_suggestionpersonalbumid != 0) ou d'un visage sans nom (]unknownface),
                        #   la base PMP fait foi (Ref: picasa3.exe @ 0x0041A8B0..0x0041AF20) : une ancienne
                        #   ligne faces= dans .picasa.ini ne doit jamais valider automatiquement une suggestion !
                        # EN: When the 1001 child record already exists in the PMP database:
                        # - if marked ]ignoreface, never promote it to a confirmed face;
                        # - if imagedata_personalbumid == 0 and it is a pending suggestion or ]unknownface,
                        #   the PMP database is authoritative (Ref: picasa3.exe @ 0x0041A8B0..0x0041AF20):
                        #   a stale faces= entry in .picasa.ini must never auto-confirm a suggestion!
                        if child_1001 is not None:
                            if child_1001 in ignored_set:
                                continue
                            pa_val = (
                                pmp_personalbum.records[child_1001]
                                if (pmp_personalbum is not None and 0 <= child_1001 < len(pmp_personalbum.records))
                                else 0
                            )
                            sug_val = (
                                pmp_suggestion.records[child_1001]
                                if (pmp_suggestion is not None and 0 <= child_1001 < len(pmp_suggestion.records))
                                else 0
                            )
                            if pa_val == 0 and (sug_val != 0 or child_1001 in unknown_rec_ids):
                                continue

                        # FR : Si l'identifiant de contact est orphelin (absent de contacts.xml, albumdata et [Contacts2])
                        # et que la base possède des enregistrements 1001, ne pas créer de personne factice "<Personne inconnue>"
                        # EN: If the contact ID is orphaned (missing from contacts.xml, albumdata, and [Contacts2])
                        # and the DB has 1001 records, do not create a dummy "<Personne inconnue>" person
                        if cid_clean not in contact_id_to_name and cid_clean not in self.people:
                            if self._parent_to_1001:
                                continue

                        cname = contact_id_to_name.get(cid_clean, cid_clean)
                        if cname.strip().lower() in ("sans nom", "unnamed", "<personne inconnue>", "<unknown person>"):
                            continue
                        cluster = self.people.get(cid_clean)
                        if not cluster:
                            cluster = PersonCluster(contact_id=cid_clean, name=cname)
                            self.people[cid_clean] = cluster
                        fr.contact_name = cname

                        if eff_idx is not None:
                            if eff_idx not in cluster.photo_indices:
                                cluster.photo_indices.append(eff_idx)
                            existing_eff = self.photo_to_faces.setdefault(eff_idx, [])
                            matched_ef = False
                            for ef in existing_eff:
                                if _face_overlap(ef, fr) >= 0.45:
                                    ef.contact_id = cid_clean
                                    ef.contact_name = cname
                                    matched_ef = True
                            if not matched_ef:
                                existing_eff.append(fr)
                            c_eff = cluster.face_rects_by_photo.setdefault(eff_idx, [])
                            if not any(_face_overlap(ef, fr) >= 0.45 for ef in c_eff):
                                c_eff.append(fr)

                        if photo_db_idx is not None and photo_db_idx != eff_idx:
                            existing_parent = self.photo_to_faces.setdefault(photo_db_idx, [])
                            matched_parent_ef = False
                            for ef in existing_parent:
                                if _face_overlap(ef, fr) >= 0.45:
                                    ef.contact_id = cid_clean
                                    ef.contact_name = cname
                                    matched_parent_ef = True
                            if not matched_parent_ef:
                                existing_parent.append(fr)
                            c_parent = cluster.face_rects_by_photo.setdefault(photo_db_idx, [])
                            if not any(_face_overlap(ef, fr) >= 0.45 for ef in c_parent):
                                c_parent.append(fr)

                        # FR : Marquage en O(1) des visages correspondants dans unnamed_faces et suggestions
                        # EN: O(1) marking of matching faces in unnamed_faces and suggestions
                        u_cands: List[int] = []
                        if eff_idx is not None and eff_idx in unnamed_by_idx:
                            u_cands.extend(unnamed_by_idx[eff_idx])
                        if photo_db_idx is not None and photo_db_idx != eff_idx and photo_db_idx in unnamed_by_idx:
                            u_cands.extend(unnamed_by_idx[photo_db_idx])
                        if norm_full and norm_full in unnamed_by_path:
                            u_cands.extend(unnamed_by_path[norm_full])
                        for pos in u_cands:
                            if pos not in unnamed_removed and _face_overlap(self.unnamed_faces[pos][2], fr) >= 0.45:
                                unnamed_removed.add(pos)

                        s_cands: List[Tuple[str, FaceSuggestion]] = []
                        if eff_idx is not None and eff_idx in sug_by_idx:
                            s_cands.extend(sug_by_idx[eff_idx])
                        if photo_db_idx is not None and photo_db_idx != eff_idx and photo_db_idx in sug_by_idx:
                            s_cands.extend(sug_by_idx[photo_db_idx])
                        if norm_full and norm_full in sug_by_path:
                            s_cands.extend(sug_by_path[norm_full])
                        for _, s_obj in s_cands:
                            if id(s_obj) not in sug_removed_ids and _face_overlap(s_obj.face_rect, fr) >= 0.45:
                                sug_removed_ids.add(id(s_obj))

                        if cluster.primary_face_rect is None:
                            cluster.primary_face_rect = fr

                        norm_target_p = os.path.normcase(os.path.normpath(full_file_path))
                        if not any(os.path.normcase(os.path.normpath(p)) == norm_target_p for p in cluster.photo_paths):
                            cluster.photo_paths.append(full_file_path)
            except Exception:
                pass

        # FR : Filtrage unique en O(U) à la fin de _scan_ini_faces
        # EN: Single O(U) filtering pass at the end of _scan_ini_faces
        if unnamed_removed:
            self.unnamed_faces = [
                uf for pos, uf in enumerate(self.unnamed_faces) if pos not in unnamed_removed
            ]
        if sug_removed_ids:
            for s_cid in list(self.suggestions.keys()):
                self.suggestions[s_cid] = [
                    s for s in self.suggestions[s_cid] if id(s) not in sug_removed_ids
                ]

    @staticmethod
    def _open_photo_for_face_crop(
        photo_path: str,
        face_rect: FaceRect,
        target_size: int = 64,
    ) -> Optional[Image.Image]:
        """
        FR : Ouvre une photo sur disque pour en extraire un visage avec une résolution optimale.
        Calcule le facteur `draft()` proportionnellement à la taille relative du visage afin que
        le visage découpé possède toujours au moins `2 * max(target_size, 256)` pixels de côté,
        tout en appliquant l'orientation EXIF et les transformations `.picasa.ini`.
        EN: Open an on-disk photo to crop a face at optimal resolution.
        Scales the `draft()` target inversely by the normalized face size so the cropped face
        always retains at least `2 * max(target_size, 256)` pixels per side, while applying
        EXIF orientation and `.picasa.ini` non-destructive transformations.
        Ref: picasa3.exe @ 0x009B93F0, 0x00896F74
        """
        if not photo_path or not os.path.exists(photo_path):
            return None
        try:
            with Image.open(photo_path) as raw_img:
                # FR : Lire l'orientation EXIF avant draft() car draft() peut réinitialiser les métadonnées
                # EN: Read EXIF orientation before draft() since draft() may strip metadata
                exif_orient = 1
                try:
                    exif = raw_img.getexif()
                    if exif:
                        exif_orient = int(exif.get(0x0112, 1) or 1)
                except Exception:
                    exif_orient = 1

                min_frac = max(0.02, min(face_rect.width, face_rect.height))
                req_full = int(max(target_size * 2, 256) / min_frac)
                if req_full < min(raw_img.size) and exif_orient <= 1:
                    raw_img.draft("RGB", (req_full, req_full))

                if raw_img.mode in ("P", "PA") or "transparency" in raw_img.info:
                    raw_img = raw_img.convert("RGBA")
                try:
                    pil_img = ImageOps.exif_transpose(raw_img)
                except Exception:
                    pil_img = raw_img
                if pil_img.mode not in ("RGB", "RGBA"):
                    pil_img = pil_img.convert("RGB")
                else:
                    pil_img = pil_img.copy()

                # FR : Appliquer les transformations géométriques .picasa.ini (crop, rotate, tilt)
                # EN: Apply .picasa.ini geometric transformations (crop, rotate, tilt)
                parent_dir = os.path.dirname(photo_path)
                ini_path = os.path.join(parent_dir, ".picasa.ini")
                if not os.path.exists(ini_path):
                    ini_path = os.path.join(parent_dir, "Picasa.ini")
                if os.path.exists(ini_path):
                    try:
                        doc = PicasaIniParser.parse_file(ini_path)
                        base_name = os.path.basename(photo_path)
                        crop_hex = doc.get_crop(base_name)
                        if crop_hex:
                            cl, ct, cr, cb = decode_rect64_string(crop_hex)
                            w, h = pil_img.size
                            crop_box = (
                                max(0, min(w - 1, int(round(cl * w)))),
                                max(0, min(h - 1, int(round(ct * h)))),
                                max(1, min(w, int(round(cr * w)))),
                                max(1, min(h, int(round(cb * h)))),
                            )
                            if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                                pil_img = pil_img.crop(crop_box)
                        rot = (doc.get_rotate(base_name) or 0) % 4
                        if rot == 1:
                            pil_img = pil_img.rotate(270, expand=True)
                        elif rot == 2:
                            pil_img = pil_img.rotate(180, expand=True)
                        elif rot == 3:
                            pil_img = pil_img.rotate(90, expand=True)
                        tilt = doc.get_tilt(base_name) or 0.0
                        if abs(tilt) >= 0.01:
                            from picasa_py.ui.image_processor import PicasaImageProcessor
                            pil_img = PicasaImageProcessor.straighten(pil_img, tilt)
                    except Exception:
                        pass
                return pil_img
        except Exception:
            return None

    def _write_face_record_thumbnails(
        self,
        face_rec_idx: int,
        face_rect: FaceRect,
        photo_path: str = "",
        source_img: Optional[Image.Image] = None,
    ) -> bool:
        """
        FR : Génère et écrit dans les conteneurs `CBlockFile` les vignettes portrait 5:6 d'un sous-enregistrement
        de visage (`type == 1001`) conformément à `FUN_00424CA0` / `FUN_00425210` (`0x004258D1..0x00425B6C`) :
        - `thumbs` (`small`) : `120x144` (`0x78 x 0x90`), qualité JPEG `90`
        - `thumbs2` (`medium`) : `60x72` (`0x3C x 0x48`), qualité JPEG `90`
        - `bigthumbs` (`large`) : `240x288` (`0xF0 x 0x120`), qualité JPEG `90`
        EN: Generate and write into `CBlockFile` containers the 5:6 portrait thumbnails for a face sub-record
        (`type == 1001`) matching `FUN_00424CA0` / `FUN_00425210` (`0x004258D1..0x00425B6C`):
        - `thumbs` (`small`): `120x144` (`0x78 x 0x90`), JPEG quality `90`
        - `thumbs2` (`medium`): `60x72` (`0x3C x 0x48`), JPEG quality `90`
        - `bigthumbs` (`large`): `240x288` (`0xF0 x 0x120`), JPEG quality `90`
        Ref: picasa3.exe @ 0x00424CA0, 0x00425210 (0x004258D1..0x00425B6C), 0x009B93F0
        """
        if not self.db or face_rec_idx is None or face_rec_idx < 0:
            return False
        if not photo_path:
            try:
                photo_path = self.db.get_media_full_path(face_rec_idx) or ""
            except Exception:
                photo_path = ""
        pil_img = source_img
        if pil_img is None and photo_path and os.path.exists(photo_path):
            pil_img = self._open_photo_for_face_crop(photo_path, face_rect, target_size=288)
        if pil_img is None or pil_img.width <= 0 or pil_img.height <= 0:
            return False
        try:
            aspect_img = pil_img.width / float(pil_img.height)
            disp_fr = face_rect.project_for_photo_ini(photo_path, aspect_ratio=aspect_img, db=self.db)
            cbox = disp_fr.to_pixel_bbox(pil_img.width, pil_img.height)
            face_crop = pil_img.crop(cbox)
            if face_crop.mode != "RGB":
                face_crop = face_crop.convert("RGB")

            def _enc(tw: int, th: int) -> bytes:
                sub = face_crop.resize((tw, th), Image.Resampling.BILINEAR)
                buf = io.BytesIO()
                sub.save(buf, format="JPEG", quality=90)
                return buf.getvalue()

            b_idx = getattr(self.db, "block_indices", {})
            if "thumbs" in b_idx:
                self.db.add_thumbnail(face_rec_idx, _enc(120, 144), size="small")
            if "thumbs2" in b_idx:
                self.db.add_thumbnail(face_rec_idx, _enc(60, 72), size="medium")
            if "bigthumbs" in b_idx:
                self.db.add_thumbnail(face_rec_idx, _enc(240, 288), size="large")
            return True
        except Exception:
            return False

    def _generate_avatars(self) -> None:
        """
        FR : Prépare paresseusement les clusters au démarrage sans décoder d'images ni désérialiser
        des milliers de gabarits `vqc_Cue` sur le thread GUI. Les vecteurs de caractéristiques
        sont chargés à la demande par `_ensure_person_feature_vectors()`, et les `cluster.avatar_pixmap`
        sont générés paresseusement dans `get_person_avatar`.
        EN: Lazily prepares clusters at startup without decoding images or unpacking thousands of
        `vqc_Cue` templates on the GUI thread. Feature vectors are loaded on demand by
        `_ensure_person_feature_vectors()`, and `cluster.avatar_pixmap` objects are generated
        lazily in `get_person_avatar`.
        Ref: picasa3.exe @ 0x009B93F0, 0x008AAD76
        """
        for cluster in self.people.values():
            cluster._manager = self

    def _rebuild_suggestions_from_templates(self) -> None:
        """
        FR : Reconstruit paresseusement les vecteurs et suggestions à partir de `facetemplatesV2_0.db`
        à la première demande (`get_suggestions()`, `get_all_suggestions()`) ou depuis
        `BackgroundFaceDetectionWorker`, sans bloquer `reload()` sur le thread principal.
        EN: Lazily rebuilds template vectors and suggestions from `facetemplatesV2_0.db`
        on first request (`get_suggestions()`, `get_all_suggestions()`) or from
        `BackgroundFaceDetectionWorker`, without blocking `reload()` on the main thread.
        Ref: picasa3.exe @ 0x0048AA80, 0x00880B94
        """
        if self._suggestions_rebuilt:
            return
        self._suggestions_rebuilt = True
        self._ensure_person_feature_vectors()

    def _ensure_person_feature_vectors(self) -> None:
        """
        FR : Charge à la demande les gabarits `vqc_Cue` depuis `facetemplatesV2_0.db` pour les
        clusters de personnes connus lorsque l'identification automatique (`detect_faces_for_photo`)
        en a besoin.
        EN: Lazily loads `vqc_Cue` templates from `facetemplatesV2_0.db` for known person clusters
        when automatic recognition (`detect_faces_for_photo`) needs them.
        Ref: picasa3.exe @ 0x0048AA80, 0x008AAD76
        """
        if getattr(self, "_person_vectors_loaded", False):
            return
        self._person_vectors_loaded = True
        has_templates_db = bool(self.db and hasattr(self.db, "get_face_template"))
        if not has_templates_db:
            return
        for cid, cluster in list(self.people.items()):
            if not cluster.photo_indices or cluster.feature_vectors:
                continue
            for p_idx in cluster.photo_indices[:32]:
                tpl_vec = self.db.get_face_template(p_idx)
                if tpl_vec is not None:
                    cluster.feature_vectors.append(tpl_vec)
            if cluster.feature_vectors and cluster.feature_vector is None:
                cluster.feature_vector = cluster.feature_vectors[0]

    def get_person_avatar(
        self,
        contact_id: str,
        size: int = 64,
        circular: bool = True,
        allow_disk_fallback: bool = True,
    ) -> Optional[QPixmap]:
        """
        FR : Récupère ou génère à la volée l'avatar pour un contact à la résolution demandée.
        Réutilise et redimensionne `cluster.avatar_pixmap` (64x64) pour les tailles inférieures
        ou différentes afin d'éviter toute relecture de la base ou du disque.
        Si `allow_disk_fallback=False`, utilise uniquement les miniatures précalculées en base
        sans jamais décoder un fichier photo haute résolution sur disque depuis le thread GUI.
        EN: Retrieve or generate on-the-fly the avatar for a contact at the requested resolution.
        Reuses and scales `cluster.avatar_pixmap` (64x64) for other requested sizes to avoid
        redundant database or disk reads.
        When `allow_disk_fallback=False`, only uses precomputed database thumbnails without ever
        decoding a full-resolution photo file from disk on the GUI thread.
        Ref: picasa3.exe @ 0x009B93F0, 0x008AAD76
        """
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.instance() is None:
            return None
        cid = contact_id.lower()
        cluster = self.people.get(cid)
        if not cluster:
            return None

        cache_key = ("person_avatar", cid, size, circular)
        if cache_key in self._avatar_cache:
            return self._avatar_cache[cache_key]

        cached_avatar = cluster._avatar_pixmap
        if circular and cached_avatar and not cached_avatar.isNull():
            if size == 64:
                self._avatar_cache[cache_key] = cached_avatar
                return cached_avatar
            if size < 64:
                scaled = cached_avatar.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._avatar_cache[cache_key] = scaled
                return scaled

        fr = cluster.primary_face_rect
        if not fr:
            for flist in cluster.face_rects_by_photo.values():
                if flist:
                    fr = flist[0]
                    cluster.primary_face_rect = fr
                    break

        if not fr and cluster.photo_paths:
            for ppath in cluster.photo_paths:
                ini_path = os.path.join(os.path.dirname(ppath), ".picasa.ini")
                doc = self.db.get_parsed_ini(ini_path) if (self.db and hasattr(self.db, "get_parsed_ini")) else None
                if not doc and allow_disk_fallback and os.path.exists(ini_path):
                    try:
                        doc = PicasaIniParser.parse_file(ini_path)
                    except Exception:
                        pass
                if doc:
                    faces = doc.get_faces(os.path.basename(ppath))
                    for item in faces:
                        if item.contact_id.lower() == cid:
                            fr = FaceRect.from_rect64(f"rect64({item.rect64})", contact_id=contact_id, contact_name=cluster.name)
                            cluster.primary_face_rect = fr
                            break
                if fr:
                    break

        if not fr:
            return None

        target_gen_size = 64 if (circular and size <= 64) else size
        gen_pix: Optional[QPixmap] = None

        # FR : 1. Tenter depuis la couverture personnalisée si définie (en privilégiant la miniature 1001 en base)
        # EN: 1. Try from custom cover photo if set (preferring the type 1001 DB thumbnail if available)
        if cluster.cover_photo_path:
            cover_db_idx = (
                self.db.find_photo_index(cluster.cover_photo_path)
                if (self.db and hasattr(self.db, "find_photo_index"))
                else None
            )
            if cover_db_idx is not None:
                gen_pix = self.get_face_avatar(
                    cluster.cover_photo_path,
                    fr,
                    db_idx=cover_db_idx,
                    size=target_gen_size,
                    circular=circular,
                    allow_disk_fallback=allow_disk_fallback,
                )
            if allow_disk_fallback and (gen_pix is None or gen_pix.isNull()) and os.path.exists(cluster.cover_photo_path):
                pil_img = self._open_photo_for_face_crop(cluster.cover_photo_path, fr, target_gen_size)
                if pil_img is not None:
                    try:
                        aspect_img = (pil_img.width / float(pil_img.height)) if pil_img.height > 0 else 1.0
                        disp_fr = fr.project_for_photo_ini(cluster.cover_photo_path, aspect_ratio=aspect_img, db=self.db)
                        gen_pix = disp_fr.crop_avatar(pil_img, avatar_size=target_gen_size, circular=circular)
                    except Exception:
                        gen_pix = None

        # FR : 2. Tenter via get_face_avatar sur le premier enregistrement du cluster (1001 haute résolution ou photo originale)
        # EN: 2. Try via get_face_avatar on the first cluster record (high-res 1001 thumbnail or original photo)
        if (gen_pix is None or gen_pix.isNull()) and cluster.photo_indices and self.db:
            first_idx = cluster.photo_indices[0]
            first_path = cluster.photo_paths[0] if cluster.photo_paths else ""
            gen_pix = self.get_face_avatar(
                first_path,
                fr,
                db_idx=first_idx,
                size=target_gen_size,
                circular=circular,
                allow_disk_fallback=allow_disk_fallback,
            )

        # FR : 3. Tenter depuis le fichier original sur disque (uniquement si allow_disk_fallback=True)
        # EN: 3. Try from original file on disk (only when allow_disk_fallback=True)
        if allow_disk_fallback and (gen_pix is None or gen_pix.isNull()):
            for ppath in cluster.photo_paths:
                if os.path.exists(ppath):
                    pil_img = self._open_photo_for_face_crop(ppath, fr, target_gen_size)
                    if pil_img is not None:
                        try:
                            aspect_img = (pil_img.width / float(pil_img.height)) if pil_img.height > 0 else 1.0
                            disp_fr = fr.project_for_photo_ini(ppath, aspect_ratio=aspect_img, db=self.db)
                            gen_pix = disp_fr.crop_avatar(pil_img, avatar_size=target_gen_size, circular=circular)
                            if gen_pix and not gen_pix.isNull():
                                break
                        except Exception:
                            pass

        if gen_pix and not gen_pix.isNull():
            if circular:
                if target_gen_size == 64:
                    cluster.avatar_pixmap = gen_pix
                    self._avatar_cache[("person_avatar", cid, 64, True)] = gen_pix
                elif cluster._avatar_pixmap is None or cluster._avatar_pixmap.isNull():
                    cluster.avatar_pixmap = gen_pix.scaled(
                        64,
                        64,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self._avatar_cache[("person_avatar", cid, 64, True)] = cluster._avatar_pixmap
                if size != target_gen_size:
                    scaled = gen_pix.scaled(
                        size,
                        size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self._avatar_cache[cache_key] = scaled
                    return scaled
            self._avatar_cache[cache_key] = gen_pix
            return gen_pix

        return None

    def set_person_album_cover(self, contact_id: str, photo_path: str, face_rect: FaceRect) -> bool:
        """
        FR : Définit explicitement le visage choisi comme couverture / miniature de l'album de personne (`ID_SETPEOPLEALBUMCOVER`).
        EN: Explicitly set the selected face as the cover / thumbnail of the person album (`ID_SETPEOPLEALBUMCOVER`).
        Ref: picasa3.exe @ PplAlbumPhoto::ID_SETPEOPLEALBUMCOVER (0x008AF20B), CThumbUI::UpdateAlbumCover (0x0088F08C)
        """
        cid = contact_id.lower()
        cluster = self.people.get(cid)
        if not cluster:
            return False

        cluster.primary_face_rect = face_rect
        cluster.cover_photo_path = photo_path
        cluster.avatar_pixmap = None
        for k in list(self._avatar_cache.keys()):
            if isinstance(k, tuple) and len(k) >= 2 and k[0] == "person_avatar" and k[1] == cid:
                self._avatar_cache.pop(k, None)

        # FR : Recréer immédiatement l'avatar circulaire
        # EN: Immediately recreate the circular avatar
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.instance() is not None:
            from picasa_py.ui.image_processor import PicasaImageProcessor
            img = None
            if photo_path and os.path.exists(photo_path):
                try:
                    img = PicasaImageProcessor.load_transformed_image(photo_path)
                except Exception:
                    pass
            if img is not None:
                aspect_img = (img.width / float(img.height)) if img.height > 0 else 1.0
                disp_fr = face_rect.project_for_photo_ini(photo_path, aspect_ratio=aspect_img, db=self.db)
                cluster.avatar_pixmap = disp_fr.crop_avatar(img, avatar_size=64, circular=True)
                crop_box = disp_fr.to_pixel_bbox(img.width, img.height)
                sub = img.crop(crop_box)
                cluster.feature_vector = PicasaFaceDetector.get().compute_face_feature(sub)

        # FR : Sauvegarde persistante dans contacts.xml / repository.dat (sans QSettings tiers)
        # EN: Persistent storage in contacts.xml / repository.dat (without third-party QSettings)
        try:
            r64_str = face_rect.to_rect64()
            if self.db and getattr(self.db, "contacts", None):
                c_obj = self.db.contacts.get(cid)
                if c_obj:
                    c_obj.extra_attrs["cover_photo_path"] = photo_path
                    c_obj.extra_attrs["cover_rect64"] = r64_str
                if getattr(self.db, "contacts_dir", None):
                    self.db.contacts.save(str(self.db.contacts_dir / "contacts.xml"))
            if self.db and getattr(self.db, "repository", None):
                self.db.repository.set(f"PeopleCovers/{cid}/photo_path", photo_path)
                self.db.repository.set(f"PeopleCovers/{cid}/rect64", r64_str)
        except Exception:
            pass

        self.notify_people_changed()
        return True

    def get_face_avatar(
        self,
        photo_path: str,
        face_rect: FaceRect,
        db_idx: Optional[int] = None,
        size: int = 64,
        circular: bool = True,
        allow_disk_fallback: bool = True,
    ) -> Optional[QPixmap]:
        """
        FR : Génère ou découpe un avatar haute résolution pour un visage donné :
        - Si l'enregistrement est un visage `type == 1001` (ou possède un enfant `1001` correspondant),
          utilise en priorité la vignette de visage haute résolution `bigthumbs_0.db` (`240x288`, `size="large"`)
          puis `thumbs_0.db` (`120x144`, `size="small"`), ou découpe depuis l'original sur disque si `size > 288`.
        - Si l'enregistrement est une photo entière (`type != 1001`), découpe le visage depuis la photo originale
          haute résolution sur disque (et non depuis la miniature `144x108` de la photo entière !).
        - Si `allow_disk_fallback=False` (utilisé pendant un `paintEvent`), ne fait jamais `_open_photo_for_face_crop`
          sur le fichier haute résolution du disque si la miniature `thumbs_0.db` est absente.
        EN: Generate or crop a high-resolution avatar for a given face:
        - When the record is a `type == 1001` face sub-record (or has a matching `1001` child),
          uses the high-resolution `bigthumbs_0.db` (`240x288`, `size="large"`) face thumbnail first,
          then `thumbs_0.db` (`120x144`, `size="small"`), or crops from the on-disk original if `size > 288`.
        - When the record is a full photo (`type != 1001`), crops the face from the high-resolution
          original photo on disk (never from the tiny `144x108` whole-photo thumbnail unless the file is missing).
        - When `allow_disk_fallback=False` (used during `paintEvent`), never opens the high-resolution
          disk file via `_open_photo_for_face_crop` if the `thumbs_0.db` thumbnail is absent.
        Ref: picasa3.exe @ 0x009B93F0, 0x00896F74, 0x0057A4F0
        """
        from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPainterPath
        if QGuiApplication.instance() is None:
            return None

        face_rec_idx: Optional[int] = None
        parent_photo_idx: Optional[int] = None
        is_direct_1001 = False
        if db_idx is not None and db_idx >= 0 and self.db:
            if 0 <= db_idx < len(self.db.index) and getattr(self.db, "is_face_record", lambda i: False)(db_idx):
                parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
                # Ref: picasa3.exe @ 0x0064CE70 - 0x0064D250 (PeoplePanel::BuildFaceCards) :
                # Lorsque db_idx pointe sur un enregistrement visage enfant 1001 mais que face_rect
                # désigne une AUTRE personne présente sur la même photo parente, ne jamais réutiliser
                # la miniature 1001 de db_idx (qui afficherait le même visage plusieurs fois).
                own_faces = self.photo_to_faces.get(db_idx, [])
                if face_rect is None or not own_faces or any(
                    _face_overlap(face_rect, of) >= 0.45 for of in own_faces
                ):
                    is_direct_1001 = True
                    face_rec_idx = db_idx
                elif parent_photo_idx is not None and parent_photo_idx >= 0:
                    face_rec_idx = self._find_matching_1001_child(parent_photo_idx, face_rect)
                    is_direct_1001 = face_rec_idx is not None
            else:
                parent_photo_idx = db_idx
                face_rec_idx = self._find_matching_1001_child(db_idx, face_rect)
                is_direct_1001 = face_rec_idx is not None

        # FR : Chemin ultra-rapide O(1) lorsque db_idx est un enregistrement 1001 :
        # lit directement la miniature pré-découpée dans thumbs_0.db / bigthumbs_0.db via QImage.fromData
        # AVANT d'interroger .picasa.ini ou de décoder previews_0.db avec PIL.
        # EN: Ultra-fast O(1) path when db_idx is a 1001 face record:
        # reads the pre-cropped face thumbnail directly from thumbs_0.db / bigthumbs_0.db via QImage.fromData
        # BEFORE querying .picasa.ini or decoding previews_0.db with PIL.
        if is_direct_1001 and face_rec_idx is not None and self.db and size <= 288:
            fast_cache_key = ("face_1001", face_rec_idx, size, circular)
            if fast_cache_key in self._avatar_cache:
                return self._avatar_cache[fast_cache_key]
            raw_face = (
                self.db.get_thumbnail(face_rec_idx, size="large" if size > 144 else "small")
                or self.db.get_thumbnail(face_rec_idx, size="small")
            )
            if raw_face:
                qimg = QImage.fromData(raw_face)
                if not qimg.isNull():
                    w_q, h_q = qimg.width(), qimg.height()
                    side = min(w_q, h_q)
                    if side > 0:
                        if w_q != h_q:
                            qimg = qimg.copy((w_q - side) // 2, (h_q - side) // 2, side, side)
                        if qimg.width() != size or qimg.height() != size:
                            qimg = qimg.scaled(
                                size,
                                size,
                                Qt.AspectRatioMode.IgnoreAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        if circular:
                            out_img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
                            out_img.fill(Qt.GlobalColor.transparent)
                            painter = QPainter(out_img)
                            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                            clip_path = QPainterPath()
                            clip_path.addEllipse(0.0, 0.0, float(size), float(size))
                            painter.setClipPath(clip_path)
                            painter.drawImage(0, 0, qimg)
                            painter.end()
                            pix = QPixmap.fromImage(out_img)
                        else:
                            pix = QPixmap.fromImage(qimg)
                        if not pix.isNull():
                            self._avatar_cache[fast_cache_key] = pix
                            return pix

        if not photo_path and parent_photo_idx is not None and parent_photo_idx >= 0 and self.db:
            try:
                photo_path = self.db.get_media_full_path(parent_photo_idx) or ""
            except Exception:
                photo_path = ""

        has_geo_edits = False
        geo_sig = (0, "", 0.0)
        if photo_path:
            parent_dir = os.path.dirname(photo_path)
            if self.db and hasattr(self.db, "get_parsed_ini"):
                doc = self.db.get_parsed_ini(os.path.join(parent_dir, ".picasa.ini"))
                if doc is None:
                    doc = self.db.get_parsed_ini(os.path.join(parent_dir, "Picasa.ini"))
            else:
                ini_p = os.path.join(parent_dir, ".picasa.ini")
                if not os.path.exists(ini_p):
                    ini_p = os.path.join(parent_dir, "Picasa.ini")
                doc = PicasaIniParser.parse_file(ini_p) if os.path.exists(ini_p) else None
            if doc is not None:
                try:
                    bname = os.path.basename(photo_path)
                    rot_v = (doc.get_rotate(bname) or 0) % 4
                    crop_v = doc.get_crop(bname) or ""
                    tilt_v = round(float(doc.get_tilt(bname) or 0.0), 3)
                    geo_sig = (rot_v, crop_v, tilt_v)
                    has_geo_edits = bool(rot_v != 0 or crop_v or abs(tilt_v) >= 0.01)
                except Exception:
                    pass

        cache_key = (db_idx, photo_path, round(face_rect.left, 4), round(face_rect.top, 4), size, circular, geo_sig)
        if cache_key in self._avatar_cache:
            return self._avatar_cache[cache_key]

        # FR : 1. Si l'on dispose d'un sous-enregistrement de visage (type == 1001) et que la photo n'a pas
        # de transformation géométrique non répercutée, utiliser bigthumbs_0.db (240x288) ou thumbs_0.db (120x144).
        # EN: 1. When a face sub-record (type == 1001) is available and no unapplied geometric edit is active,
        # use bigthumbs_0.db (240x288) or thumbs_0.db (120x144).
        if face_rec_idx is not None and self.db and (not has_geo_edits or not allow_disk_fallback or not (photo_path and os.path.exists(photo_path))):
            raw_face = (
                self.db.get_thumbnail(face_rec_idx, size="large" if size > 144 else "small")
                or self.db.get_thumbnail(face_rec_idx, size="small")
            )
            if raw_face:
                qimg = QImage.fromData(raw_face)
                if not qimg.isNull() and (size <= max(qimg.width(), qimg.height()) or not allow_disk_fallback or not (photo_path and os.path.exists(photo_path))):
                    w_q, h_q = qimg.width(), qimg.height()
                    side = min(w_q, h_q)
                    if side > 0:
                        if w_q != h_q:
                            qimg = qimg.copy((w_q - side) // 2, (h_q - side) // 2, side, side)
                        if qimg.width() != size or qimg.height() != size:
                            qimg = qimg.scaled(
                                size,
                                size,
                                Qt.AspectRatioMode.IgnoreAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        if circular:
                            out_img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
                            out_img.fill(Qt.GlobalColor.transparent)
                            painter = QPainter(out_img)
                            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                            clip_path = QPainterPath()
                            clip_path.addEllipse(0.0, 0.0, float(size), float(size))
                            painter.setClipPath(clip_path)
                            painter.drawImage(0, 0, qimg)
                            painter.end()
                            pix = QPixmap.fromImage(out_img)
                        else:
                            pix = QPixmap.fromImage(qimg)
                        if not pix.isNull():
                            self._avatar_cache[cache_key] = pix
                            return pix

        # FR : 2. Découpage haute résolution depuis le fichier photo original sur disque (avec projection .picasa.ini)
        # EN: 2. High-resolution crop from the original photo file on disk (with .picasa.ini projection)
        if allow_disk_fallback and photo_path and os.path.exists(photo_path):
            pil_img = self._open_photo_for_face_crop(photo_path, face_rect, size)
            if pil_img is not None:
                try:
                    aspect_img = (pil_img.width / float(pil_img.height)) if pil_img.height > 0 else 1.0
                    disp_fr = face_rect.project_for_photo_ini(photo_path, aspect_ratio=aspect_img, db=self.db)
                    pix = disp_fr.crop_avatar(pil_img, avatar_size=size, circular=circular)
                    if pix and not pix.isNull():
                        self._avatar_cache[cache_key] = pix
                        return pix
                except Exception:
                    pass

        # FR : 3. Repli (uniquement si le fichier original sur disque est introuvable ou allow_disk_fallback=False) :
        # essayer previews_0.db puis bigthumbs_0.db puis thumbs_0.db de la photo parente
        # EN: 3. Fallback (when the original on-disk file is missing or allow_disk_fallback=False):
        # try previews_0.db, then bigthumbs_0.db, then thumbs_0.db of the parent photo
        if parent_photo_idx is not None and parent_photo_idx >= 0 and self.db:
            for sz in ("preview", "large", "small"):
                raw_parent = (
                    self.db.load_thumbnail(parent_photo_idx, size=sz)
                    if hasattr(self.db, "load_thumbnail")
                    else self.db.get_thumbnail(parent_photo_idx, size=sz)
                )
                if raw_parent:
                    try:
                        with Image.open(io.BytesIO(raw_parent)) as img:
                            aspect_img = (img.width / float(img.height)) if img.height > 0 else 1.0
                            disp_fr = face_rect.project_for_photo_ini(photo_path, aspect_ratio=aspect_img, db=self.db)
                            pix = disp_fr.crop_avatar(img, avatar_size=size, circular=circular)
                            if pix and not pix.isNull():
                                self._avatar_cache[cache_key] = pix
                                return pix
                    except Exception:
                        pass

        return None

    def cluster_unnamed_faces(
        self,
        threshold: float = 0.85,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        unnamed_subset: Optional[List[Tuple[Optional[int], str, FaceRect]]] = None
    ) -> List[List[Tuple[Optional[int], str, FaceRect]]]:
        """
        FR : Regroupe les visages sans nom similaires en grappes (`clusters`) selon l'algorithme
        désassemblé exact `vfr_SowGrowStampClusterer::createClusters` de `Red.dll` + `picasa3.exe` :
        1. Seuil par défaut `FRSortThreshold = 0x55 = 85` (`0.85`, `picasa3.exe @ 0x0078A220`).
        2. Découpage par lots de `max_batch = 5000` visages (`int(sqrt(25_000_000))`, `Red.dll @ 0x100A09F0`).
        3. Contrainte de tampon photo (`image_stamp` à `+0x0C` de `vqc_Cue`, `f_0c = 0.98`, `Red.dll @ 0x1009F180`) :
           deux visages issus de la même photo ne peuvent pas appartenir à la même grappe (sauf doublon `sim > 0.98`).
        4. Étape Sow (`Red.dll @ 0x100A6420`) : sélection gloutonne des graines par poids de voisinage
           `w = max(0, min(sim, 0.98) - thr) / (1 - thr)` avec soustraction à 2 sauts et masquage des voisins directs.
        5. Étape Grow (`Red.dll @ 0x1009F500`) : croissance par file de priorité (`best_sim >= thr`) sous contrainte
           de non-collision de `image_stamp` dans chaque grappe.
        6. Étape d'élagage des graines isolées (`Red.dll @ 0x1009FF50`) : dissolution des graines de taille 1
           et rattachement éventuel au meilleur groupe voisin valide.
        7. Tri des grappes multi-visages (`len >= 2`) par taille décroissante (`picasa3.exe @ 0x006C8400`, `0x006C8820`),
           suivies des visages isolés (`cluster_id == -1`).

        EN: Group similar unnamed faces into clusters using the exact disassembled
        `vfr_SowGrowStampClusterer::createClusters` algorithm from `Red.dll` + `picasa3.exe`.
        Ref: picasa3.exe @ 0x006C4A30, 0x006C8400, 0x006C8820, 0x00789C00, 0x0078A220 (FRSortThreshold = 85)
        Ref: Red.dll @ 0x1009F180, 0x1009F470, 0x1009F500, 0x1009FF50, 0x100A0190, 0x100A09F0, 0x100A6420
        """
        import zlib

        target_unnamed = list(unnamed_subset if unnamed_subset is not None else self.unnamed_faces)
        if not target_unnamed:
            return []

        total = len(target_unnamed)

        # FR : Cache intelligent des grappes (Ref: picasa3.exe @ 0x007898B0 SetGrouped, 0x0078A360 RemoveCluster)
        # Si les grappes ont déjà été calculées et que seuls quelques visages ont été nommés/ignorés,
        # filtrer les grappes existantes en O(N) au lieu de recalculer la matrice.
        if unnamed_subset is None:
            cached_clusters = getattr(self, "_cached_unnamed_clusters", None)
            cached_th = getattr(self, "_cached_unnamed_threshold", None)
            cached_total = getattr(self, "_cached_unnamed_total", 0)
            if (
                cached_clusters is not None
                and cached_th == threshold
                and cached_total >= total
                and (cached_total - total) <= max(500, cached_total // 5)
            ):
                current_keys = {
                    (db_idx, ppath, round(fr.left, 4), round(fr.top, 4)): (db_idx, ppath, fr)
                    for db_idx, ppath, fr in target_unnamed
                }
                filtered_clusters: List[List[Tuple[Optional[int], str, FaceRect]]] = []
                matched_count = 0
                for c in cached_clusters:
                    new_c = []
                    for db_idx, ppath, fr in c:
                        k = (db_idx, ppath, round(fr.left, 4), round(fr.top, 4))
                        item = current_keys.pop(k, None)
                        if item is not None:
                            new_c.append(item)
                            matched_count += 1
                    if new_c:
                        filtered_clusters.append(new_c)
                if not current_keys and matched_count == total:
                    multi_c = [c for c in filtered_clusters if len(c) > 1]
                    single_c = [c for c in filtered_clusters if len(c) == 1]
                    multi_c.sort(key=lambda c: len(c), reverse=True)
                    res = multi_c + single_c
                    self._cached_unnamed_clusters = res
                    self._cached_unnamed_total = total
                    if progress_callback:
                        try:
                            progress_callback(total, total)
                        except Exception:
                            pass
                    return res

        features: List[Optional[np.ndarray]] = []
        stamps: List[int] = []
        has_templates_db = bool(self.db and hasattr(self.db, "get_face_template"))
        has_cue_db = bool(self.db and hasattr(self.db, "get_face_template_cue"))

        for i, (db_idx, ppath, fr) in enumerate(target_unnamed):
            cache_key = (db_idx, round(fr.left, 4), round(fr.top, 4))
            feat = self._face_feature_cache.get(cache_key)
            img_stamp = 0

            if db_idx is not None and has_cue_db:
                cue_res = self.db.get_face_template_cue(db_idx)
                if cue_res is not None:
                    c_vec, _c_inv, c_stamp = cue_res
                    img_stamp = int(c_stamp)
                    if feat is None:
                        # Note: get_face_template_cue retourne déjà `vals * (inv_norm * sqrt_w)`
                        feat = c_vec
                        self._face_feature_cache[cache_key] = feat

            if feat is None:
                if db_idx is not None and has_templates_db:
                    feat = self.db.get_face_template(db_idx)
                if feat is None and not has_templates_db:
                    if db_idx is not None and self.db:
                        raw_thumb = self.db.get_thumbnail(db_idx, size="small")
                        if raw_thumb:
                            try:
                                with Image.open(io.BytesIO(raw_thumb)) as t_img:
                                    box = fr.to_pixel_bbox(t_img.width, t_img.height)
                                    feat = PicasaFaceDetector.get().compute_face_feature(t_img.crop(box))
                            except Exception:
                                pass
                if feat is not None:
                    self._face_feature_cache[cache_key] = feat

            # FR : Si le tampon image_stamp de vqc_Cue vaut 0 (ex. gabarit PurePythonRedEngine ou test),
            # dériver un identifiant de photo parente non nul pour garantir que deux visages d'une même photo
            # partagent le même tampon (Ref: picasa3.exe @ 0x0047B040, Red.dll @ 0x1009F180).
            if img_stamp == 0:
                parent_idx: Optional[int] = None
                if db_idx is not None and self.db and hasattr(self.db, "get_face_parent_photo_idx"):
                    parent_idx = self.db.get_face_parent_photo_idx(db_idx)
                if parent_idx is not None and parent_idx >= 0:
                    img_stamp = int(parent_idx) + 1
                elif ppath:
                    img_stamp = (zlib.crc32(os.path.normpath(ppath).lower().encode("utf-8")) & 0x7FFFFFFF) | 1
                elif db_idx is not None and db_idx >= 0:
                    img_stamp = int(db_idx) + 1

            features.append(feat)
            stamps.append(img_stamp)
            if progress_callback and (i % 1000 == 0 or i == total - 1):
                try:
                    progress_callback(max(1, int((i + 1) * 0.20)), total)
                except Exception:
                    pass

        valid_indices = [idx for idx, f in enumerate(features) if f is not None]
        if not valid_indices:
            return [[f] for f in target_unnamed]

        n_valid = len(valid_indices)
        mat = np.array([features[idx] for idx in valid_indices], dtype=np.float32)
        valid_stamps = np.array([stamps[idx] for idx in valid_indices], dtype=np.int64)

        # FR : Préparation des vecteurs pour vqc_Relator::sim (sim_factor=13.5, sim_delta=-0.45, logistic_map=1)
        # Ref: Red.dll @ 0x10100A10 (vqc_Relator::sim), 0x1009F470 (vfr_SowGrowStampClusterer)
        is_2000d = (mat.shape[1] == 2000)
        centered_scale = 1.0
        if is_2000d:
            col_mean = mat.mean(axis=0, keepdims=True)
            cm_norm2 = float(np.dot(col_mean.ravel(), col_mean.ravel()))
            if cm_norm2 > 0.05 and n_valid >= 64:
                # FR : Gabarits 2000-D issus de PurePythonRedEngine possédant une moyenne de population non nulle :
                # centrer par colonne uniquement lorsque l'échantillon est statistiquement significatif (n_valid >= 64),
                # normaliser L2 et appliquer le facteur d'échelle 0.62 qui aligne la distribution
                # des produits scalaires centrés sur la courbe logistique de vqc_Relator::sim (seuil 0.85 -> cos >= 0.261).
                mat_c = mat - col_mean
                norms_c = np.linalg.norm(mat_c, axis=1, keepdims=True)
                norms_c[norms_c == 0] = 1.0
                mat_work = (mat_c / norms_c).astype(np.float32, copy=False)
                centered_scale = 0.62
            else:
                mat_work = mat
            clamped_t = min(max(float(threshold), 1e-6), 1.0 - 1e-6)
            dot_thr = float((math.log(clamped_t / (1.0 - clamped_t)) + 0.45) / 13.5)
        else:
            mat_c = mat - mat.mean(axis=1, keepdims=True)
            norms_c = np.linalg.norm(mat_c, axis=1, keepdims=True)
            norms_c[norms_c == 0] = 1.0
            mat_work = (mat_c / norms_c).astype(np.float32, copy=False)
            clamped_t = min(max(float(threshold), 1e-6), 1.0 - 1e-6)
            dot_thr = float(0.28 if mat.shape[1] >= 512 else clamped_t)

        # FR :Constantes exactes de vfr_SowGrowStampClusterer dans red.cfg Root 5 :
        # - f_0c = 0.98 (plafond de similarité pour le poids Sow et seuil de fusion même-photo)
        # - ref14 = 25_000_000 -> max_batch = int(sqrt(25_000_000)) = 5000 (Red.dll @ 0x100A09F0..0x100A0C5C)
        f_0c = 0.98
        inv_one_minus_thr = 1.0 / max(1e-6, 1.0 - clamped_t)
        dot_98 = float((math.log(0.98 / 0.02) + 0.45) / 13.5)
        max_batch = 5000

        multi_clusters: List[List[Tuple[Optional[int], str, FaceRect]]] = []
        single_clusters: List[List[Tuple[Optional[int], str, FaceRect]]] = []

        for b_start in range(0, n_valid, max_batch):
            b_end = min(b_start + max_batch, n_valid)
            B = b_end - b_start
            b_mat = mat_work[b_start:b_end]
            b_stamps = valid_stamps[b_start:b_end]

            # FR : Étape 1 — Matrice de similarité du lot B x B et graphe clairsemé (Red.dll @ 0x1009F470)
            dots = np.dot(b_mat, b_mat.T)
            if centered_scale != 1.0:
                dots *= centered_scale

            adj_nb: List[np.ndarray] = []
            adj_sim: List[np.ndarray] = []
            adj_w: List[np.ndarray] = []
            node_w = np.zeros(B, dtype=np.float64)

            for i in range(B):
                row_dots = dots[i]
                mask = row_dots >= dot_thr
                mask[i] = False
                st_i = int(b_stamps[i])
                if st_i != 0:
                    # Ref: Red.dll @ 0x1009F180 (canJoinCluster : exclure les visages de la même photo si sim <= f_0c)
                    same_st = (b_stamps == st_i)
                    if is_2000d:
                        same_st &= (row_dots <= dot_98)
                    mask &= ~same_st
                nb = np.flatnonzero(mask).astype(np.int32)
                if nb.size == 0:
                    adj_nb.append(nb)
                    adj_sim.append(np.empty(0, dtype=np.float32))
                    adj_w.append(np.empty(0, dtype=np.float32))
                else:
                    d_nb = row_dots[nb].astype(np.float64)
                    if is_2000d:
                        s_nb = 1.0 / (1.0 + np.exp(-(13.5 * d_nb - 0.45)))
                    else:
                        s_nb = np.clip(d_nb, 0.0, 1.0)
                    w_nb = np.maximum(0.0, np.minimum(s_nb, f_0c) - clamped_t) * inv_one_minus_thr
                    adj_nb.append(nb)
                    adj_sim.append(s_nb.astype(np.float32))
                    adj_w.append(w_nb.astype(np.float32))
                    node_w[i] = float(np.sum(w_nb))

            del dots

            # FR : Étape 2 — Sow : sélection des graines et soustraction des poids à 2 sauts (Red.dll @ 0x100A6420)
            rem_w = node_w.copy()
            avail = rem_w > 0.0
            seeds: List[int] = []
            cluster_of = np.full(B, -1, dtype=np.int32)
            cluster_stamps: List[Set[int]] = []
            cluster_members: List[List[int]] = []

            while True:
                masked_w = np.where(avail, rem_w, -1.0)
                best_u = int(np.argmax(masked_w))
                if masked_w[best_u] <= 0.0:
                    break
                cid = len(seeds)
                seeds.append(best_u)
                cluster_of[best_u] = cid
                st_u = int(b_stamps[best_u])
                cluster_stamps.append({st_u} if st_u != 0 else set())
                cluster_members.append([best_u])

                avail[best_u] = False
                u_nbs = adj_nb[best_u]
                u_ws = adj_w[best_u]
                avail[u_nbs] = False

                for k_idx in range(u_nbs.size):
                    v = int(u_nbs[k_idx])
                    rem_w[best_u] -= float(u_ws[k_idx])
                    v_nbs = adj_nb[v]
                    v_ws = adj_w[v]
                    rem_w[v_nbs] -= v_ws

            # FR : Étape 3 — Grow : croissance par meilleur voisin sous contrainte de tampon photo (Red.dll @ 0x1009F500)
            best_sim_to_seed = np.full(B, -1.0, dtype=np.float32)
            best_cid_for_node = np.full(B, -1, dtype=np.int32)

            for cid, s in enumerate(seeds):
                s_nbs = adj_nb[s]
                s_sims = adj_sim[s]
                c_stamps = cluster_stamps[cid]
                for k_idx in range(s_nbs.size):
                    v = int(s_nbs[k_idx])
                    if cluster_of[v] != -1:
                        continue
                    st_v = int(b_stamps[v])
                    if st_v != 0 and st_v in c_stamps:
                        continue
                    sim_val = float(s_sims[k_idx])
                    if sim_val > best_sim_to_seed[v]:
                        best_sim_to_seed[v] = sim_val
                        best_cid_for_node[v] = cid

            while True:
                u = int(np.argmax(best_sim_to_seed))
                best_s = float(best_sim_to_seed[u])
                if best_s < clamped_t:
                    break
                cid = int(best_cid_for_node[u])
                best_sim_to_seed[u] = -1.0
                if cluster_of[u] != -1 or cid < 0:
                    continue

                st_u = int(b_stamps[u])
                if st_u != 0 and st_u in cluster_stamps[cid]:
                    # FR : Le tampon de la photo est déjà présent dans la grappe cid -> chercher le meilleur autre groupe valide
                    u_nbs = adj_nb[u]
                    u_sims = adj_sim[u]
                    alt_sim = -1.0
                    alt_cid = -1
                    for k_idx in range(u_nbs.size):
                        nb_node = int(u_nbs[k_idx])
                        nb_cid = int(cluster_of[nb_node])
                        if nb_cid >= 0 and nb_cid != cid:
                            if st_u == 0 or st_u not in cluster_stamps[nb_cid]:
                                s_val = float(u_sims[k_idx])
                                if s_val > alt_sim:
                                    alt_sim = s_val
                                    alt_cid = nb_cid
                    if alt_cid >= 0 and alt_sim >= clamped_t:
                        best_sim_to_seed[u] = alt_sim
                        best_cid_for_node[u] = alt_cid
                    continue

                cluster_of[u] = cid
                cluster_members[cid].append(u)
                if st_u != 0:
                    cluster_stamps[cid].add(st_u)

                # FR : Propager depuis u vers ses voisins non encore assignés
                u_nbs = adj_nb[u]
                u_sims = adj_sim[u]
                c_stamps = cluster_stamps[cid]
                for k_idx in range(u_nbs.size):
                    v = int(u_nbs[k_idx])
                    if cluster_of[v] != -1:
                        continue
                    st_v = int(b_stamps[v])
                    if st_v != 0 and st_v in c_stamps:
                        continue
                    sim_val = float(u_sims[k_idx])
                    if sim_val > best_sim_to_seed[v]:
                        best_sim_to_seed[v] = sim_val
                        best_cid_for_node[v] = cid

            # FR : Étape 4 — Élagage des graines restées seules (taille 1) et rattachement éventuel (Red.dll @ 0x1009FF50)
            singleton_seeds: List[int] = []
            for cid, members in enumerate(cluster_members):
                if len(members) == 1:
                    s = members[0]
                    cluster_of[s] = -1
                    members.clear()
                    cluster_stamps[cid].clear()
                    singleton_seeds.append(s)

            for s in singleton_seeds:
                s_nbs = adj_nb[s]
                s_sims = adj_sim[s]
                st_s = int(b_stamps[s])
                best_c = -1
                best_sim_val = clamped_t
                for k_idx in range(s_nbs.size):
                    v = int(s_nbs[k_idx])
                    c_v = int(cluster_of[v])
                    if c_v >= 0 and len(cluster_members[c_v]) >= 2:
                        if st_s == 0 or st_s not in cluster_stamps[c_v]:
                            sv = float(s_sims[k_idx])
                            if sv >= best_sim_val:
                                best_sim_val = sv
                                best_c = c_v
                if best_c >= 0:
                    cluster_of[s] = best_c
                    cluster_members[best_c].append(s)
                    if st_s != 0:
                        cluster_stamps[best_c].add(st_s)

            for members in cluster_members:
                if len(members) >= 2:
                    multi_clusters.append([target_unnamed[valid_indices[b_start + m]] for m in members])

            for i in range(B):
                if cluster_of[i] == -1:
                    single_clusters.append([target_unnamed[valid_indices[b_start + i]]])

            if progress_callback:
                try:
                    prog_val = int(total * 0.20 + (b_end / max(1, n_valid)) * (total * 0.80))
                    progress_callback(min(total, max(1, prog_val)), total)
                except Exception:
                    pass

        # FR : Ajouter les visages sans signature calculable comme visages isolés
        # EN: Append faces without a computable feature vector as singleton clusters
        for idx, f in enumerate(features):
            if f is None:
                single_clusters.append([target_unnamed[idx]])

        # Ref: picasa3.exe @ 0x006C8400, 0x006C8820 : les groupes multi-visages d'abord (triés par taille décroissante),
        # suivis des visages isolés (cluster_id == -1) dans leur ordre d'origine.
        multi_clusters.sort(key=lambda c: len(c), reverse=True)
        result = multi_clusters + single_clusters

        if unnamed_subset is None:
            self._cached_unnamed_clusters = result
            self._cached_unnamed_threshold = threshold
            self._cached_unnamed_total = total

        return result

    def ignore_unnamed_faces(self, items: List[Tuple[Optional[int], str, FaceRect]]) -> None:
        """
        FR : Marque un ou plusieurs visages sans nom comme ignorés (`]ignoreface`), les retire de
        `unnamed_faces` et persiste `rect64(...),ffffffffffffffff` dans `.picasa.ini` ainsi que
        `]ignoreface` dans `wordhash.dat`.
        EN: Mark one or more unnamed faces as ignored (`]ignoreface`), remove them from
        `unnamed_faces`, and persist `rect64(...),ffffffffffffffff` in `.picasa.ini` as well as
        `]ignoreface` in `wordhash.dat`.
        Ref: picasa3.exe @ 0x00484BD0 (WriteFacesToIni -1), 0x006470D0 (SetFaceIgnored), 0x00786C28 (faceclusterpanel ignore)
        """
        if not items:
            return
        to_ignore_keys: Set[Tuple[str, float, float]] = set()
        by_photo: Dict[str, List[FaceRect]] = {}
        ignored_set = getattr(self, "_ignored_rec_ids", None)
        if ignored_set is None:
            ignored_set = set()
            self._ignored_rec_ids = ignored_set

        for db_idx, ppath, fr in items:
            if fr is None:
                continue
            to_ignore_keys.add((ppath, round(fr.left, 4), round(fr.top, 4)))
            if ppath:
                by_photo.setdefault(ppath, []).append(fr)

            eff_idx = db_idx
            if eff_idx is not None and self.db and not getattr(self.db, "is_face_record", lambda i: False)(eff_idx):
                child_1001 = self._find_matching_1001_child(eff_idx, fr)
                if child_1001 is not None:
                    eff_idx = child_1001
            if eff_idx is not None and eff_idx >= 0:
                ignored_set.add(eff_idx)
                if self.db and getattr(self.db, "wordhash", None) is not None:
                    with self.db._lock:
                        if hasattr(self.db.wordhash, "remove_word"):
                            self.db.wordhash.remove_word("]unknownface", eff_idx)
                        if hasattr(self.db.wordhash, "add_word"):
                            self.db.wordhash.add_word("]ignoreface", eff_idx)

        if to_ignore_keys:
            self.unnamed_faces = [
                (i, p, f)
                for (i, p, f) in self.unnamed_faces
                if (p, round(f.left, 4), round(f.top, 4)) not in to_ignore_keys
            ]
            cached = getattr(self, "_cached_unnamed_clusters", None)
            if cached is not None:
                new_cached = []
                for c in cached:
                    nc = [
                        (i, p, f)
                        for (i, p, f) in c
                        if (p, round(f.left, 4), round(f.top, 4)) not in to_ignore_keys
                    ]
                    if nc:
                        new_cached.append(nc)
                self._cached_unnamed_clusters = new_cached
                self._cached_unnamed_total = len(self.unnamed_faces)

        # FR : Persister `rect64(...),ffffffffffffffff` dans .picasa.ini (Ref: picasa3.exe @ 0x00484BD0)
        if self.db and hasattr(self.db, "update_photo_ini"):
            for ppath, fr_list in by_photo.items():
                if not ppath or not os.path.exists(ppath):
                    continue
                def _persist_ignored(doc: PicasaIniDocument, section_name: str, rects: List[FaceRect] = fr_list) -> None:
                    sec = doc.get_or_create_section(section_name)
                    curr = sec.get("faces") or ""
                    tokens = [t.strip() for t in curr.split(";") if t.strip()]
                    for r_ign in rects:
                        r64 = r_ign.to_rect64()
                        new_tok = f"{r64},ffffffffffffffff"
                        replaced = False
                        for t_idx, tok in enumerate(tokens):
                            if tok.startswith(r64 + ","):
                                tokens[t_idx] = new_tok
                                replaced = True
                                break
                        if not replaced:
                            tokens.append(new_tok)
                    if tokens:
                        sec.set("faces", ";".join(tokens))
                try:
                    self.db.update_photo_ini(ppath, _persist_ignored, invalidate_albums_starred=False)
                except TypeError:
                    self.db.update_photo_ini(ppath, _persist_ignored)
                except Exception:
                    pass

    def name_cluster(self, cluster: List[Tuple[Optional[int], str, FaceRect]], name: str) -> None:
        """
        FR : Attribue un nom à tous les visages d'un cluster d'un seul coup.
        EN: Assign a name to all faces in a cluster at once.
        Ref: picasa3.exe @ unknownfaceheaderpanel/addname
        """
        for db_idx, ppath, fr in cluster:
            self.add_face(ppath, fr, name, db_idx=db_idx)

    def get_people(self) -> List[PersonCluster]:
        """
        FR : Renvoie la liste des personnes triées par nombre de photos décroissant.
        EN: Return the list of people sorted by descending photo count.
        """
        return sorted(self.people.values(), key=lambda p: (p.photo_count, p.name), reverse=True)

    def get_person(self, contact_id: str) -> Optional[PersonCluster]:
        """
        FR : Récupère le `PersonCluster` correspondant à `contact_id`.
        EN: Return the `PersonCluster` matching `contact_id`.
        """
        return self.people.get(contact_id.lower())

    def get_faces_for_photo(self, db_idx: int, photo_path: Optional[str] = None) -> List[FaceRect]:
        """
        FR : Renvoie l'ensemble des rectangles de visages associés à la photo `db_idx` (ou `photo_path`).
             Si `db_idx` est un sous-enregistrement de visage (`type == 1001`), remonte à la photo parente
             afin de renvoyer tous les visages présents sur cette photo (`PeoplePanel::InThisPhoto`).
        EN: Return all face rectangles associated with photo `db_idx` (or `photo_path`).
            If `db_idx` is a face sub-record (`type == 1001`), resolves to the parent photo
            so all faces on that photo are returned (`PeoplePanel::InThisPhoto`).
        Ref: picasa3.exe @ 0x008AAD76 (PeoplePanel::InThisPhoto)
        """
        target_idx = db_idx
        if self.db and target_idx is not None and target_idx >= 0 and getattr(self.db, "is_face_record", lambda i: False)(target_idx):
            parent_idx = self.db.get_face_parent_photo_idx(target_idx)
            if parent_idx is not None and parent_idx >= 0:
                target_idx = parent_idx

        if target_idx is not None and target_idx >= 0:
            if target_idx in self.photo_to_faces and self.photo_to_faces[target_idx]:
                return self.photo_to_faces[target_idx]
            children = getattr(self, "_parent_to_1001", {}).get(target_idx, [])
            if children:
                collected: List[FaceRect] = []
                for c_idx in children:
                    for fr in self.photo_to_faces.get(c_idx, []):
                        if not any(_face_overlap(ef, fr) >= 0.45 for ef in collected):
                            collected.append(fr)
                if collected:
                    self.photo_to_faces[target_idx] = collected
                    return collected

        if db_idx is not None and db_idx in self.photo_to_faces and self.photo_to_faces[db_idx]:
            return self.photo_to_faces[db_idx]

        if photo_path and self.db and hasattr(self.db, "find_media_index_by_path"):
            found_idx = self.db.find_media_index_by_path(photo_path)
            if found_idx is not None and found_idx >= 0 and found_idx in self.photo_to_faces and self.photo_to_faces[found_idx]:
                return self.photo_to_faces[found_idx]

        if photo_path:
            norm_target = os.path.normpath(photo_path).lower()
            matched_unnamed = [
                fr for (_, u_path, fr) in self.unnamed_faces
                if u_path and os.path.normpath(u_path).lower() == norm_target
            ]
            if matched_unnamed:
                return matched_unnamed

        return []

    def detect_faces_for_photo(
        self,
        photo_path: str | int | Path,
        db_idx: Optional[int | str | Path] = None,
        auto_suggest: bool = True,
        persist_ini: bool = False,
    ) -> List[FaceRect]:
        """
        FR : Détecte automatiquement les visages sur une photo via `CFaceDetector` / `BgFaceDetectThread`.
        Si de nouveaux visages sont détectés, crée les enregistrements enfants `type == 1001`
        dans `thumbindex.db`, stocke les coordonnées dans `imagedata_facerect.pmp`, enregistre
        les signatures `vqc_Cue` dans `facetemplatesV2` et recherche des correspondances
        avec les contacts existants pour générer des suggestions.
        Si 0 visage n'est détecté, marque l'image parente avec `imagedata_facerect = 1`.
        EN: Automatically detect faces in a photo via `CFaceDetector` / `BgFaceDetectThread`.
        When new faces are detected, creates child `type == 1001` records in `thumbindex.db`,
        stores rects in `imagedata_facerect.pmp`, writes `vqc_Cue` templates into `facetemplatesV2`,
        and matches them against existing contacts to generate suggestions.
        If 0 faces are detected, marks the parent photo with `imagedata_facerect = 1`.
        Ref: picasa3.exe @ 0x0072BA00, 0x0087ECD6 (BgFaceDetectThread), 0x00881CC0 (FRSuggestionThreshold)
        """
        if isinstance(photo_path, int):
            if isinstance(db_idx, (str, Path)):
                photo_path, db_idx = str(db_idx), photo_path
            else:
                db_idx = photo_path
                photo_path = (self.db.get_media_full_path(db_idx) or "") if self.db else ""
        else:
            photo_path = str(photo_path or "")
            if isinstance(db_idx, (str, Path)):
                db_idx = None

        if (db_idx is None or db_idx < 0) and self.db and photo_path:
            if hasattr(self.db, "find_photo_index"):
                db_idx = self.db.find_photo_index(photo_path)
            else:
                folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
                norm_dir = os.path.dirname(photo_path).replace("/", "\\").rstrip("\\").lower()
                fname_lower = os.path.basename(photo_path).lower()
                for i, r in enumerate(self.db.index):
                    if r.type not in (0, 1, 1001) and r.path.lower() == fname_lower:
                        fpath = folders_map.get(r.parent_idx, "")
                        if fpath.replace("/", "\\").rstrip("\\").lower() == norm_dir:
                            db_idx = i
                            break

        if db_idx is not None:
            self._scanned_photo_indices.add(db_idx)

        if not photo_path or not os.path.exists(photo_path):
            return self.get_faces_for_photo(db_idx) if db_idx is not None else []

        existing: List[FaceRect] = list(self.get_faces_for_photo(db_idx)) if db_idx is not None else []

        # Ref: picasa3.exe @ 0x00881690 (frexclude=1 dans [Picasa] de .picasa.ini)
        parent_dir = os.path.dirname(photo_path)
        for ini_name in (".picasa.ini", "Picasa.ini"):
            ini_p = os.path.join(parent_dir, ini_name)
            doc = self.db.get_parsed_ini(ini_p) if (self.db and hasattr(self.db, "get_parsed_ini")) else None
            if doc is None and not (self.db and hasattr(self.db, "get_parsed_ini")) and os.path.exists(ini_p):
                try:
                    doc = PicasaIniParser.parse_file(ini_p)
                except Exception:
                    doc = None
            if doc is not None:
                sec_p = doc.get_section("Picasa")
                if sec_p and (sec_p.get("frexclude") or "").strip().lower() in ("1", "yes", "true"):
                    return existing

        detector = getattr(self, "detector", None) or PicasaFaceDetector.get()
        detected: list[Any] = []
        if hasattr(detector, "detect_faces_in_file"):
            res = detector.detect_faces_in_file(photo_path)
            if isinstance(res, list):
                detected = res
            elif hasattr(detector, "detect_faces_in_image"):
                res2 = detector.detect_faces_in_image(photo_path)
                if isinstance(res2, list):
                    detected = res2
        elif hasattr(detector, "detect_faces_in_image"):
            res = detector.detect_faces_in_image(photo_path)
            if isinstance(res, list):
                detected = res
        elif hasattr(detector, "detect_faces"):
            res = detector.detect_faces(photo_path)
            if isinstance(res, list):
                detected = res

        if not detected:
            # Ref: picasa3.exe @ 0x0072BA00 (imagedata_facerect = 1 pour photo analysée avec 0 visage)
            if db_idx is not None and db_idx >= 0 and self.db:
                with self.db._lock:
                    pmp_fr = self.db.pmps.get("imagedata_facerect")
                    if pmp_fr is not None:
                        while len(pmp_fr.records) <= db_idx:
                            pmp_fr.records.append(0)
                            pmp_fr.dirty = True
                        if pmp_fr.records[db_idx] == 0:
                            pmp_fr.records[db_idx] = 1
                            pmp_fr.dirty = True
            return existing

        # FR : Ouvrir l'image uniquement si un gabarit n'a pas déjà été extrait par Red.dll / PurePythonRedEngine
        # EN: Open the image only if a template was not already extracted by Red.dll / PurePythonRedEngine
        pil_img: Optional[Image.Image] = None

        new_faces_added = False
        newly_detected_rects: List[FaceRect] = []
        for df_raw in detected:
            if isinstance(df_raw, FaceRect):
                df = df_raw
            elif hasattr(df_raw, "rect") and isinstance(getattr(df_raw, "rect"), FaceRect):
                df = getattr(df_raw, "rect")
            elif hasattr(df_raw, "face_rect") and isinstance(getattr(df_raw, "face_rect"), FaceRect):
                df = getattr(df_raw, "face_rect")
            else:
                df = FaceRect(
                    left=float(getattr(df_raw, "left", getattr(df_raw, "left_norm", 0.2))),
                    top=float(getattr(df_raw, "top", getattr(df_raw, "top_norm", 0.2))),
                    right=float(getattr(df_raw, "right", getattr(df_raw, "right_norm", 0.8))),
                    bottom=float(getattr(df_raw, "bottom", getattr(df_raw, "bottom_norm", 0.8))),
                )
            template_blob = (
                getattr(df, "template_blob", None)
                or getattr(df_raw, "template_blob", None)
                or getattr(df_raw, "cue_blob_1044", None)
                or getattr(df_raw, "template", None)
            )
            if template_blob is not None:
                df.template_blob = template_blob  # type: ignore[attr-defined]
            if getattr(df, "feature_vector", None) is None and getattr(df_raw, "feature_vector", None) is not None:
                df.feature_vector = getattr(df_raw, "feature_vector")

            # FR : Vérifier si ce visage correspond déjà à un visage existant (recouvrement >= 0.35)
            # EN: Check whether this face already overlaps an existing face (overlap >= 0.35)
            if any(_face_overlap(df, ef) >= 0.35 for ef in existing):
                continue

            child_idx: Optional[int] = None
            if db_idx is not None and db_idx >= 0 and self.db:
                if pil_img is None and photo_path and os.path.exists(photo_path):
                    if self._find_matching_1001_child(db_idx, df) is None:
                        pil_img = self._open_photo_for_face_crop(photo_path, df, target_size=288)
                child_idx = self._get_or_create_1001_child(db_idx, df, source_img=pil_img)
                if child_idx is not None:
                    self.photo_to_faces.setdefault(child_idx, [df])
                    if isinstance(template_blob, (bytes, bytearray)) and len(template_blob) > 0 and hasattr(self.db, "add_face_template"):
                        self.db.add_face_template(child_idx, bytes(template_blob))

            # FR : Récupérer le gabarit vqc_Cue 2000-D extrait par Red.dll (vt[14]) / PurePythonRedEngine
            # EN: Retrieve the 2000-D vqc_Cue template extracted by Red.dll (vt[14]) / PurePythonRedEngine
            feat: Optional[Any] = getattr(df, "feature_vector", None)
            if feat is None and isinstance(template_blob, (bytes, bytearray)) and len(template_blob) == 1044:
                feat = PicasaFaceDetector.cue_blob_to_feature_vector(bytes(template_blob))
                if feat is not None:
                    df.feature_vector = feat
            if feat is None and child_idx is not None and self.db and hasattr(self.db, "get_face_template"):
                feat = self.db.get_face_template(child_idx)
            if feat is None and db_idx is not None and self.db and hasattr(self.db, "get_face_template"):
                feat = self.db.get_face_template(db_idx)

            if feat is None and auto_suggest and self.people:
                try:
                    if pil_img is None:
                        from picasa_py.ui.image_processor import PicasaImageProcessor
                        pil_img = PicasaImageProcessor.load_transformed_image(photo_path)
                    if pil_img is not None:
                        cbox = df.to_pixel_bbox(pil_img.width, pil_img.height)
                        sub = pil_img.crop(cbox)
                        feat = PicasaFaceDetector.get().compute_face_feature(sub)
                except Exception:
                    pass

            if feat is not None:
                cache_key = (db_idx, round(df.left, 4), round(df.top, 4))
                self._face_feature_cache[cache_key] = feat

            # FR : Visage non répertorié : tentative d'identification / suggestion via vqc_Relator::sim
            # EN: Unlisted face: attempt identification / suggestion via vqc_Relator::sim
            # Ref: picasa3.exe @ 0x0048AA80..0x0048AE80 :
            # - FRSuggestionSingleThreshold = 0.90 (90%) si le contact n'a qu'1 seule photo confirmée / if 1 confirmed photo
            # - FRSuggestionThreshold = 0.65 (65%) si le contact a >= 2 photos confirmées / if >= 2 confirmed photos
            matched_cluster: Optional[PersonCluster] = None
            best_similarity: float = -1.0

            if feat is not None and auto_suggest and self.people:
                self._ensure_person_feature_vectors()
                detector = PicasaFaceDetector.get()
                sug_cand_idx = child_idx if child_idx is not None else db_idx
                rejected_set = getattr(self, "_rejected_suggestions", set())
                for cluster in self.people.values():
                    if sug_cand_idx is not None and (sug_cand_idx, cluster.contact_id.lower()) in rejected_set:
                        continue
                    ref_vecs = cluster.feature_vectors if cluster.feature_vectors else (
                        [cluster.feature_vector] if cluster.feature_vector is not None else []
                    )
                    if not ref_vecs:
                        continue
                    cluster_best = max(detector.compare_face_features(feat, rv) for rv in ref_vecs)
                    req_thresh = (
                        FR_SUGGESTION_SINGLE_THRESHOLD
                        if cluster.photo_count <= 1
                        else FR_SUGGESTION_THRESHOLD
                    )
                    if cluster_best >= req_thresh and cluster_best > best_similarity:
                        best_similarity = cluster_best
                        matched_cluster = cluster

            if matched_cluster is not None:
                df.contact_id = ""
                df.contact_name = f"? {matched_cluster.name}"
                sug_target_idx = child_idx if child_idx is not None else db_idx
                sug = FaceSuggestion(
                    contact_id=matched_cluster.contact_id,
                    contact_name=matched_cluster.name,
                    photo_path=photo_path,
                    face_rect=df,
                    similarity=best_similarity,
                    db_idx=sug_target_idx
                )
                self.suggestions.setdefault(matched_cluster.contact_id, []).append(sug)
                # FR : Persister la suggestion dans imagedata_suggestionpersonalbumid, personalbumrecs et wordhash.dat
                # Dans picasa3.exe @ 0x0044CD60, tant que personalbumid == 0 (suggestion non confirmée),
                # l'enregistrement 1001 conserve ]unknownface et reçoit ]facealbum:%d.
                # EN: Persist suggestion in imagedata_suggestionpersonalbumid, personalbumrecs, and wordhash.dat
                # Ref: picasa3.exe @ 0x0044CD60, 0x00880B94 (suggestionpersonalbumid), 0x00880BBC (personalbumrecs), 0x008AAD76 (]facealbum:%d)
                if sug_target_idx is not None and sug_target_idx >= 0 and self.db:
                    with self.db._lock:
                        sug_alb_idx = self._get_or_create_person_album_id(matched_cluster.contact_id, matched_cluster.name)
                        if sug_alb_idx is not None and sug_alb_idx > 0:
                            pmp_sug = self.db.pmps.get("imagedata_suggestionpersonalbumid")
                            if pmp_sug is not None:
                                while len(pmp_sug.records) <= sug_target_idx:
                                    pmp_sug.records.append(0)
                                pmp_sug.records[sug_target_idx] = sug_alb_idx
                                pmp_sug.dirty = True
                            pmp_parecs = self.db.pmps.get("imagedata_personalbumrecs")
                            if pmp_parecs is not None:
                                while len(pmp_parecs.records) <= sug_target_idx:
                                    pmp_parecs.records.append(0)
                                pmp_parecs.records[sug_target_idx] = sug_alb_idx
                                pmp_parecs.dirty = True
                            pmp_parecvals = self.db.pmps.get("imagedata_personalbumrecvalues")
                            if pmp_parecvals is not None:
                                while len(pmp_parecvals.records) <= sug_target_idx:
                                    pmp_parecvals.records.append(0)
                                pmp_parecvals.records[sug_target_idx] = int(round(max(0.0, min(1.0, best_similarity)) * 10000.0)) & 0xFFFF
                                pmp_parecvals.dirty = True
                            if getattr(self.db, "wordhash", None) is not None:
                                if hasattr(self.db.wordhash, "remove_word"):
                                    self.db.wordhash.remove_word("]ignoreface", sug_target_idx)
                                self.db.wordhash.add_word("]unknownface", sug_target_idx)
                                self.db.wordhash.add_word(f"]facealbum:{sug_alb_idx}", sug_target_idx)
            else:
                df.contact_id = ""
                df.contact_name = None  # FR : Visage sans nom / EN: Unnamed face (Ref: CThumbDB::unknownfacealbum)
                self.unnamed_faces.append((child_idx if child_idx is not None else db_idx, photo_path, df))

            existing.append(df)
            newly_detected_rects.append(df)
            new_faces_added = True

        if pil_img:
            try:
                pil_img.close()
            except Exception:
                pass

        if db_idx is not None and new_faces_added:
            self.photo_to_faces[db_idx] = existing

        if persist_ini and new_faces_added:
            try:
                fname = os.path.basename(photo_path)
                def _persist_detected_faces(doc: PicasaIniDocument, section_name: str) -> None:
                    sec = doc.get_or_create_section(section_name)
                    curr = sec.get("faces") or ""
                    items = [p.strip() for p in curr.split(";") if p.strip()]
                    for ndf in newly_detected_rects:
                        r64 = ndf.to_rect64()
                        tok = f"{r64},0"
                        if not any(r64 in it for it in items):
                            items.append(tok)
                    if items:
                        sec.set("faces", ";".join(items))
                if self.db and hasattr(self.db, "update_photo_ini"):
                    try:
                        self.db.update_photo_ini(
                            photo_path,
                            _persist_detected_faces,
                            invalidate_albums_starred=False,
                        )
                    except TypeError:
                        self.db.update_photo_ini(photo_path, _persist_detected_faces)
            except Exception:
                pass

        return existing

    def _save_contacts_xml(self) -> None:
        """
        FR : Sauvegarde `contacts.xml` sur disque via `self.db.contacts`.
        EN: Save `contacts.xml` to disk via `self.db.contacts`.
        Ref: picasa3.exe @ 0x008AAD76, contactmgr.fen
        """
        if not self.db or getattr(self.db, "contacts", None) is None or not getattr(self.db, "contacts_dir", None):
            return
        try:
            self.db.contacts_dir.mkdir(parents=True, exist_ok=True)
            (self.db.contacts_dir / "contacts.xml").write_text(self.db.contacts.to_xml(), encoding="utf-8")
        except Exception:
            pass

    def _sync_contacts_from_xml(self) -> None:
        """
        FR : Synchronise les contacts entre `contacts.xml` et `self.people`.
        N'appelle `self._save_contacts_xml()` à la fin de `_sync_contacts_from_xml`
        que si un contact présent dans `self.people` n'était pas déjà présent avec
        le même nom dans `contacts.xml` (`dirty == True`), pour ne pas réécrire
        `contacts.xml` sur disque à chaque ouverture en lecture seule.
        EN: Synchronize contacts between `contacts.xml` and `self.people`.
        Only calls `self._save_contacts_xml()` at the end of `_sync_contacts_from_xml`
        when a contact in `self.people` was not already present with the same name
        in `contacts.xml` (`dirty == True`), avoiding redundant `contacts.xml` disk
        writes on read-only opens.
        Ref: picasa3.exe @ 0x008AAD76, contactmgr.fen
        """
        if not self.db:
            return
        if getattr(self.db, "contacts", None) is None:
            self.db.contacts = ContactsFile()
        existing_by_id: Dict[str, Contact] = {
            c.id.lower(): c for c in self.db.contacts.contacts if c.id
        }
        for cid, c_obj in existing_by_id.items():
            if cid not in self.people and c_obj.name:
                self.people[cid] = PersonCluster(contact_id=cid, name=c_obj.name)
                self.people[cid]._manager = self
        dirty = False
        for cid, cluster in self.people.items():
            if not cid or not cluster.name:
                continue
            c_low = cid.lower()
            existing = existing_by_id.get(c_low)
            if existing is None:
                new_c = Contact(id=cid, name=cluster.name)
                self.db.contacts.contacts.append(new_c)
                existing_by_id[c_low] = new_c
                dirty = True
            elif existing.name != cluster.name:
                existing.name = cluster.name
                dirty = True
        if dirty:
            self._save_contacts_xml()


    def _get_or_create_person_album_id(self, contact_id: str, contact_name: str) -> Optional[int]:
        """
        FR : Trouve ou crée l'album de personne (category == 8) dans les tables albumdata_*
        en préservant l'alignement strict de toutes les colonnes albumdata_*.
        EN: Find or create the person album (category == 8) in albumdata_* tables
        while strictly preserving row alignment across all albumdata_* columns.
        Ref: picasa3.exe @ 0x008AAD76 (albumdata_category == 8, albumdata_albumcontactids)
        """
        if not self.db:
            return None
        ad_names = self.db.pmps.get("albumdata_name")
        ad_cats = self.db.pmps.get("albumdata_category")
        if ad_names is None or ad_cats is None:
            return None

        ad_cids = self.db.pmps.get("albumdata_albumcontactids")
        cid_int: Optional[int] = None
        try:
            cid_int = int(contact_id.strip(), 16) & 0xFFFFFFFFFFFFFFFF
        except Exception:
            cid_int = None

        clean_lower = contact_name.strip().lower()
        for i in range(len(ad_names.records)):
            if i < len(ad_cats.records) and ad_cats.records[i] == 8:
                if i == 0:
                    continue
                if ad_cids is not None and i < len(ad_cids.records) and cid_int is not None and ad_cids.records[i] == cid_int:
                    return i
                if str(ad_names.records[i] or "").strip().lower() == clean_lower:
                    return i

        albumdata_tables = {
            stem: pmp
            for stem, pmp in self.db.pmps.items()
            if stem.startswith("albumdata_")
        }
        base_len = len(ad_names.records)
        for pmp in albumdata_tables.values():
            def_val = pmp.default_value()
            while len(pmp.records) < base_len:
                pmp.records.append(def_val)
                pmp.dirty = True

        if len(ad_names.records) == 0:
            import hashlib
            u_uid = hashlib.md5(b"]unknownface").hexdigest()
            for stem, pmp in albumdata_tables.items():
                if stem == "albumdata_name":
                    pmp.records.append("Sans nom")
                elif stem == "albumdata_token":
                    pmp.records.append("]unknownface")
                elif stem == "albumdata_uid":
                    pmp.records.append(u_uid)
                elif stem == "albumdata_category":
                    pmp.records.append(8)
                else:
                    pmp.records.append(pmp.default_value())
                pmp.dirty = True

        new_alb_idx = len(ad_names.records)
        import hashlib
        from datetime import datetime
        from picasa_py.scanner.scanner import datetime_to_ole
        p_tok = f"]facealbum:{new_alb_idx}"
        p_uid = hashlib.md5(f"{contact_id}:{new_alb_idx}".encode("utf-8", errors="surrogateescape")).hexdigest()
        p_date = datetime_to_ole(datetime.now())
        for stem, pmp in albumdata_tables.items():
            if stem == "albumdata_name":
                pmp.records.append(contact_name.strip())
            elif stem == "albumdata_token":
                pmp.records.append(p_tok)
            elif stem == "albumdata_uid":
                pmp.records.append(p_uid)
            elif stem == "albumdata_date":
                pmp.records.append(p_date)
            elif stem == "albumdata_category":
                pmp.records.append(8)
            elif stem == "albumdata_albumcontactids":
                pmp.records.append(cid_int if cid_int is not None else 0)
            else:
                pmp.records.append(pmp.default_value())
            pmp.dirty = True
        return new_alb_idx

    def add_face(
        self,
        photo_path: str | int,
        face_rect: FaceRect,
        contact_name: str | PersonCluster = "",
        contact_id: Optional[str | PersonCluster] = None,
        db_idx: Optional[int] = None,
        source_image: Optional[Image.Image] = None,
    ) -> FaceRect:
        """
        FR : Associe un visage à une personne, crée ou met à jour le contact,
        synchronise les tables PMP (`imagedata_personalbumid`, `imagedata_suggestionpersonalbumid`, `albumdata_*`)
        et enregistre les modifications de manière bit-exacte dans le fichier `.picasa.ini`.
        EN: Associate a face with a person, create or update the contact,
        synchronize PMP tables (`imagedata_personalbumid`, `imagedata_suggestionpersonalbumid`, `albumdata_*`),
        and save changes bit-exactly into the `.picasa.ini` file.
        Ref: picasa3.exe @ 0x008A1034 (peoplepanel/manual_add_editbox), 0x0068BABA
        """
        if isinstance(photo_path, int):
            if db_idx is None:
                db_idx = photo_path
            photo_path = ""
        else:
            photo_path = str(photo_path or "")

        if isinstance(face_rect, (tuple, list)) and len(face_rect) >= 4:
            face_rect = FaceRect(
                left=float(face_rect[0]),
                top=float(face_rect[1]),
                right=float(face_rect[2]),
                bottom=float(face_rect[3]),
            )

        if isinstance(contact_name, PersonCluster):
            if not contact_id:
                contact_id = contact_name.contact_id
            contact_name = contact_name.name
        if isinstance(contact_id, PersonCluster):
            if not contact_name:
                contact_name = contact_id.name
            contact_id = contact_id.contact_id

        if not contact_id and getattr(face_rect, "contact_id", None):
            raw_cid = face_rect.contact_id
            if isinstance(raw_cid, PersonCluster):
                if not contact_name:
                    contact_name = raw_cid.name
                contact_id = raw_cid.contact_id
            elif str(raw_cid).strip().lower() not in ("", "0", "ffffffffffffffff", "unknown", "unnamed"):
                contact_id = str(raw_cid).strip().lower()

        clean_name = str(contact_name or "").strip()
        if not clean_name and getattr(face_rect, "contact_name", None):
            clean_name = str(face_rect.contact_name).lstrip("? ").strip()
        if not clean_name and contact_id and str(contact_id).lower() in self.people:
            clean_name = self.people[str(contact_id).lower()].name
        if not clean_name:
            clean_name = "Sans nom"

        # FR : Résoudre ou créer le contact_id (format hex 16 caractères de Picasa)
        # EN: Resolve or generate the contact_id (Picasa 16-char hex format)
        if not contact_id:
            for c in self.people.values():
                if c.name.strip().lower() == clean_name.lower():
                    contact_id = c.contact_id
                    break
            if not contact_id:
                contact_id = secrets.token_hex(8)
        else:
            contact_id = str(contact_id).strip().lower()

        face_rect.contact_id = contact_id
        face_rect.contact_name = clean_name

        # FR : Mettre à jour le cluster en mémoire
        # EN: Update in-memory person cluster
        cluster = self.people.get(contact_id)
        if not cluster:
            cluster = PersonCluster(contact_id=contact_id, name=clean_name)
            cluster._manager = self
            self.people[contact_id] = cluster
        else:
            cluster._manager = self

        if (db_idx is None or db_idx < 0) and self.db and photo_path:
            if hasattr(self.db, "find_photo_index"):
                db_idx = self.db.find_photo_index(photo_path)
            else:
                folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
                norm_dir = os.path.dirname(photo_path).replace("/", "\\").rstrip("\\").lower()
                fname_lower = os.path.basename(photo_path).lower()
                for i, r in enumerate(self.db.index):
                    if r.type not in (0, 1, 1001) and r.path.lower() == fname_lower:
                        fpath = folders_map.get(r.parent_idx, "")
                        if fpath.replace("/", "\\").rstrip("\\").lower() == norm_dir:
                            db_idx = i
                            break

        parent_photo_idx: Optional[int] = None
        face_rec_idx: Optional[int] = None
        is_input_1001 = False
        if db_idx is not None and db_idx >= 0 and self.db:
            if getattr(self.db, "is_face_record", lambda i: False)(db_idx):
                is_input_1001 = True
                face_rec_idx = db_idx
                parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
            else:
                parent_photo_idx = db_idx
                face_rec_idx = self._get_or_create_1001_child(
                    parent_photo_idx, face_rect, source_img=source_image
                )
        elif db_idx is not None and db_idx >= 0:
            parent_photo_idx = db_idx

        if not photo_path and parent_photo_idx is not None and parent_photo_idx >= 0 and self.db:
            try:
                photo_path = self.db.get_media_full_path(parent_photo_idx) or ""
            except Exception:
                photo_path = ""

        eff_idx = face_rec_idx if face_rec_idx is not None else parent_photo_idx
        face_rect.record_index = face_rec_idx
        cluster_idx = face_rec_idx if is_input_1001 else (parent_photo_idx if parent_photo_idx is not None else face_rec_idx)
        if cluster_idx is not None and cluster_idx not in cluster.photo_indices:
            cluster.photo_indices.append(cluster_idx)
        if photo_path and photo_path not in cluster.photo_paths:
            cluster.photo_paths.append(photo_path)

        for target_idx in (face_rec_idx, parent_photo_idx):
            if target_idx is None:
                continue
            flist = cluster.face_rects_by_photo.setdefault(target_idx, [])
            replaced_c = False
            for i, f in enumerate(flist):
                if _face_overlap(f, face_rect) >= 0.45:
                    f.contact_id = contact_id
                    f.contact_name = clean_name
                    flist[i] = face_rect
                    replaced_c = True
                    break
            if not replaced_c:
                flist.append(face_rect)

            pflist = self.photo_to_faces.setdefault(target_idx, [])
            replaced_p = False
            for i, f in enumerate(pflist):
                if _face_overlap(f, face_rect) >= 0.45:
                    f.contact_id = contact_id
                    f.contact_name = clean_name
                    pflist[i] = face_rect
                    replaced_p = True
                    break
            if not replaced_p:
                pflist.append(face_rect)

        # FR : Ajouter le gabarit vqc_Cue 2000-D au cluster s'il est disponible
        # EN: Append the 2000-D vqc_Cue template to the cluster if available
        fv = getattr(face_rect, "feature_vector", None)
        if fv is None:
            fv = self._face_feature_cache.get((eff_idx, round(face_rect.left, 4), round(face_rect.top, 4)))
        if fv is None and eff_idx is not None and self.db and hasattr(self.db, "get_face_template"):
            fv = self.db.get_face_template(eff_idx)
        if fv is not None:
            cluster.feature_vectors.append(fv)
            if cluster.feature_vector is None:
                cluster.feature_vector = fv

        # FR : Générer l'avatar si manquant ou mis à jour
        # EN: Generate avatar if missing or updated
        if cluster.primary_face_rect is None or cluster._avatar_pixmap is None:
            cluster.primary_face_rect = face_rect
            from PySide6.QtGui import QGuiApplication
            if QGuiApplication.instance() is not None:
                pimg = source_image
                if pimg is None and photo_path and os.path.exists(photo_path):
                    from picasa_py.ui.image_processor import PicasaImageProcessor
                    pimg = PicasaImageProcessor.load_transformed_image(photo_path)
                if pimg is not None:
                    try:
                        aspect_p = (pimg.width / float(pimg.height)) if pimg.height > 0 else 1.0
                        disp_fr = face_rect.project_for_photo_ini(photo_path, aspect_ratio=aspect_p, db=self.db)
                        cluster.avatar_pixmap = disp_fr.crop_avatar(pimg, avatar_size=64, circular=True)
                        if cluster.feature_vector is None:
                            cbox = disp_fr.to_pixel_bbox(pimg.width, pimg.height)
                            fv_crop = PicasaFaceDetector.get().compute_face_feature(pimg.crop(cbox))
                            if fv_crop is not None:
                                cluster.feature_vector = fv_crop
                                cluster.feature_vectors.append(fv_crop)
                    except Exception:
                        pass

        # FR : Retirer des visages sans nom et des suggestions
        # EN: Remove from unnamed faces and pending suggestions
        norm_photo = os.path.normpath(photo_path).lower() if photo_path else ""
        target_indices = {idx for idx in (face_rec_idx, parent_photo_idx, db_idx) if idx is not None}
        self.unnamed_faces = [
            (i, p, f) for (i, p, f) in self.unnamed_faces
            if not (
                (
                    (i is not None and i in target_indices)
                    or (p and norm_photo and os.path.normpath(p).lower() == norm_photo)
                )
                and _face_overlap(f, face_rect) >= 0.45
            )
        ]
        for cid in list(self.suggestions.keys()):
            self.suggestions[cid] = [
                s for s in self.suggestions[cid]
                if not (
                    (
                        (s.db_idx is not None and s.db_idx in target_indices)
                        or (s.photo_path and norm_photo and os.path.normpath(s.photo_path).lower() == norm_photo)
                    )
                    and _face_overlap(s.face_rect, face_rect) >= 0.45
                )
            ]

        # FR : Synchroniser imagedata_personalbumid et imagedata_suggestionpersonalbumid
        # EN: Synchronize imagedata_personalbumid and imagedata_suggestionpersonalbumid
        if self.db:
            with self.db._lock:
                pmp_pa = self.db.pmps.get("imagedata_personalbumid")
                pmp_sug = self.db.pmps.get("imagedata_suggestionpersonalbumid")
                pa_target_idx = face_rec_idx if face_rec_idx is not None else parent_photo_idx
                alb_idx = None
                if pa_target_idx is not None and pmp_pa is not None and contact_id not in ("", "0", "ffffffffffffffff", "unknown", "unnamed"):
                    alb_idx = self._get_or_create_person_album_id(contact_id, clean_name)
                    if alb_idx is not None:
                        while len(pmp_pa.records) <= pa_target_idx:
                            pmp_pa.records.append(0)
                        old_pa = pmp_pa.records[pa_target_idx]
                        pmp_pa.records[pa_target_idx] = alb_idx
                        pmp_pa.dirty = True
                        # Ref: picasa3.exe @ 0x0044B112, 0x0044BC83, 0x0044C84A (imagedata_tagdate = VariantTime now)
                        pmp_td = self.db.pmps.get("imagedata_tagdate")
                        if pmp_td is not None:
                            import time
                            while len(pmp_td.records) <= pa_target_idx:
                                pmp_td.records.append(0.0)
                            pmp_td.records[pa_target_idx] = 25569.0 + (time.time() / 86400.0)
                            pmp_td.dirty = True
                        if getattr(self.db, "wordhash", None) is not None:
                            if hasattr(self.db.wordhash, "remove_word"):
                                self.db.wordhash.remove_word("]unknownface", pa_target_idx)
                                self.db.wordhash.remove_word("]ignoreface", pa_target_idx)
                                if old_pa and old_pa != alb_idx:
                                    self.db.wordhash.remove_word(f"]facealbum:{old_pa}", pa_target_idx)
                            self.db.wordhash.add_word(f"]facealbum:{alb_idx}", pa_target_idx)
                            if parent_photo_idx is not None and parent_photo_idx >= 0:
                                self.db.wordhash.add_word("]face", parent_photo_idx)
                if pmp_sug is not None:
                    for t_idx in target_indices:
                        if 0 <= t_idx < len(pmp_sug.records):
                            old_sug = pmp_sug.records[t_idx]
                            pmp_sug.records[t_idx] = 0
                            pmp_sug.dirty = True
                            if old_sug and old_sug != alb_idx and getattr(self.db, "wordhash", None) is not None and hasattr(self.db.wordhash, "remove_word"):
                                self.db.wordhash.remove_word(f"]facealbum:{old_sug}", t_idx)

        # FR : Écriture bit-exacte dans le .picasa.ini
        # EN: Bit-exact write to .picasa.ini
        if photo_path:
            parent_dir = os.path.dirname(photo_path)
            fname = os.path.basename(photo_path)
            ini_path = os.path.join(parent_dir, ".picasa.ini")

            doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()

            sec_c2 = doc.get_or_create_section("Contacts2")
            sec_c2.set(contact_id, f"{clean_name};;")

            r64_clean = face_rect.to_rect64()[7:-1]
            faces = doc.get_faces(fname)
            found = False
            for idx, item in enumerate(faces):
                try:
                    item_fr = FaceRect.from_rect64(f"rect64({item.rect64})")
                    if _face_overlap(item_fr, face_rect) >= 0.45 or item.rect64.lower() == r64_clean.lower():
                        faces[idx] = FaceItem(rect64=r64_clean, contact_id=contact_id)
                        found = True
                        break
                except Exception:
                    pass
            if not found:
                faces.append(FaceItem(rect64=r64_clean, contact_id=contact_id))
            faces = [
                f_it for f_it in faces
                if (f_it.contact_id or "").strip().lower() not in ("", "0", "unknown", "unnamed")
            ]

            doc.set_faces(fname, faces)
            doc.write_file(ini_path)
            if self.db and hasattr(self.db, "invalidate_ini_cache"):
                try:
                    self.db.invalidate_ini_cache(ini_path, invalidate_albums_starred=False)
                except TypeError:
                    self.db.invalidate_ini_cache(ini_path)
            if self.db and hasattr(self.db, "sync_photo_ini_to_db"):
                try:
                    self.db.sync_photo_ini_to_db(photo_path, doc)
                except Exception:
                    pass

        # FR : Synchroniser contacts.xml pour la base globale Picasa
        # EN: Synchronize contacts.xml for the global Picasa database
        if self.db:
            if getattr(self.db, "contacts", None) is None:
                self.db.contacts = ContactsFile()
            found_c = False
            for c in self.db.contacts.contacts:
                if c.id.lower() == contact_id.lower():
                    found_c = True
                    break
            if not found_c:
                self.db.contacts.contacts.append(Contact(id=contact_id, name=clean_name))
                if getattr(self.db, "contacts_dir", None):
                    try:
                        self.db.contacts_dir.mkdir(parents=True, exist_ok=True)
                        (self.db.contacts_dir / "contacts.xml").write_text(self.db.contacts.to_xml(), encoding="utf-8")
                    except Exception:
                        pass

        self.notify_people_changed()
        return face_rect

    def reassign_face(
        self,
        photo_path: str,
        old_face_rect: FaceRect,
        new_contact_name: str,
        new_contact_id: Optional[str] = None,
        db_idx: Optional[int] = None,
        source_image: Optional[Image.Image] = None,
        source_contact_id: Optional[str] = None,
    ) -> FaceRect:
        """
        FR : Réassigne un visage existant à une autre personne ou renomme la personne.
        EN: Reassign an existing face to another person or rename the person.
        Ref: picasa3.exe @ peoplepanel/addname, peopleautocomplete (0x008A15D0)
        """
        if (db_idx is None or db_idx < 0) and self.db and photo_path:
            if hasattr(self.db, "find_photo_index"):
                db_idx = self.db.find_photo_index(photo_path)
            else:
                folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
                norm_dir = os.path.dirname(photo_path).replace("/", "\\").rstrip("\\").lower()
                fname_lower = os.path.basename(photo_path).lower()
                for i, r in enumerate(self.db.index):
                    if r.type not in (0, 1, 1001) and r.path.lower() == fname_lower:
                        fpath = folders_map.get(r.parent_idx, "")
                        if fpath.replace("/", "\\").rstrip("\\").lower() == norm_dir:
                            db_idx = i
                            break

        old_cid = old_face_rect.contact_id or source_contact_id
        old_cluster = self.get_person(old_cid) if old_cid else None

        if old_cluster:
            # FR : 1. Retirer le visage de old_cluster.face_rects_by_photo
            # EN: 1. Remove face from old_cluster.face_rects_by_photo
            matching_keys = []
            for k, flist in list(old_cluster.face_rects_by_photo.items()):
                new_flist = [f for f in flist if _face_overlap(f, old_face_rect) < 0.45]
                if len(new_flist) != len(flist):
                    if new_flist:
                        old_cluster.face_rects_by_photo[k] = new_flist
                    else:
                        del old_cluster.face_rects_by_photo[k]
                        matching_keys.append(k)

            for k in matching_keys:
                if isinstance(k, int) and k in old_cluster.photo_indices:
                    old_cluster.photo_indices.remove(k)
            if db_idx is not None and db_idx not in old_cluster.face_rects_by_photo:
                if db_idx in old_cluster.photo_indices:
                    old_cluster.photo_indices.remove(db_idx)

            # FR : 2. Vérifier s'il reste d'autres visages appartenant à old_cluster pour CETTE photo
            # EN: 2. Check if any other faces belonging to old_cluster remain on THIS photo
            has_other_for_this_photo = False
            if db_idx is not None and db_idx in old_cluster.face_rects_by_photo:
                has_other_for_this_photo = True

            norm_p = os.path.normpath(photo_path).lower() if photo_path else ""
            if not has_other_for_this_photo and norm_p:
                old_cluster.photo_paths = [
                    p for p in old_cluster.photo_paths
                    if os.path.normpath(p).lower() != norm_p
                ]
                if db_idx is not None and db_idx in old_cluster.photo_indices:
                    old_cluster.photo_indices = [idx for idx in old_cluster.photo_indices if idx != db_idx]

            # FR : 3. Avatar de l'ancien cluster si c'était ce visage
            # EN: 3. Update old cluster's primary avatar if it used this face
            if old_cluster.primary_face_rect and _face_overlap(old_cluster.primary_face_rect, old_face_rect) >= 0.45:
                all_remaining = []
                for fl in old_cluster.face_rects_by_photo.values():
                    all_remaining.extend(fl)
                if all_remaining:
                    old_cluster.primary_face_rect = all_remaining[0]
                else:
                    old_cluster.primary_face_rect = None
                    old_cluster.avatar_pixmap = None

        new_fr = FaceRect(
            left=old_face_rect.left,
            top=old_face_rect.top,
            right=old_face_rect.right,
            bottom=old_face_rect.bottom
        )
        return self.add_face(
            photo_path, new_fr, new_contact_name, new_contact_id, db_idx, source_image=source_image
        )

    def remove_face(
        self,
        photo_path: str,
        face_rect: FaceRect,
        db_idx: Optional[int] = None
    ) -> None:
        """
        FR : Supprime / ignore un visage d'une photo et synchronise le fichier `.picasa.ini` et les tables PMP.
        EN: Remove / ignore a face from a photo and synchronize the `.picasa.ini` file and PMP tables.
        Ref: picasa3.exe @ peoplepanel::ignore, removesel (0x00896FA8)
        """
        if (db_idx is None or db_idx < 0) and self.db and photo_path:
            if hasattr(self.db, "find_photo_index"):
                db_idx = self.db.find_photo_index(photo_path)
            else:
                folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
                norm_dir = os.path.dirname(photo_path).replace("/", "\\").rstrip("\\").lower()
                fname_lower = os.path.basename(photo_path).lower()
                for i, r in enumerate(self.db.index):
                    if r.type not in (0, 1, 1001) and r.path.lower() == fname_lower:
                        fpath = folders_map.get(r.parent_idx, "")
                        if fpath.replace("/", "\\").rstrip("\\").lower() == norm_dir:
                            db_idx = i
                            break

        parent_photo_idx: Optional[int] = None
        face_rec_idx: Optional[int] = None
        if db_idx is not None and db_idx >= 0 and self.db:
            if getattr(self.db, "is_face_record", lambda i: False)(db_idx):
                face_rec_idx = db_idx
                parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
            else:
                parent_photo_idx = db_idx
                face_rec_idx = self._find_matching_1001_child(parent_photo_idx, face_rect)
        elif db_idx is not None and db_idx >= 0:
            parent_photo_idx = db_idx

        if not photo_path and parent_photo_idx is not None and parent_photo_idx >= 0 and self.db:
            try:
                photo_path = self.db.get_media_full_path(parent_photo_idx) or ""
            except Exception:
                photo_path = ""

        target_indices = {idx for idx in (face_rec_idx, parent_photo_idx, db_idx) if idx is not None}
        for t_idx in target_indices:
            if t_idx in self.photo_to_faces:
                self.photo_to_faces[t_idx] = [
                    f for f in self.photo_to_faces[t_idx]
                    if _face_overlap(f, face_rect) < 0.45
                ]

        norm_photo = os.path.normpath(photo_path).lower() if photo_path else ""
        cid = (face_rect.contact_id or "").lower()
        clusters_to_check = [self.people[cid]] if (cid and cid in self.people) else list(self.people.values())
        for c in clusters_to_check:
            removed_any = False
            for t_idx in target_indices:
                if t_idx in c.face_rects_by_photo:
                    prev_len = len(c.face_rects_by_photo[t_idx])
                    c.face_rects_by_photo[t_idx] = [
                        f for f in c.face_rects_by_photo[t_idx]
                        if _face_overlap(f, face_rect) < 0.45
                    ]
                    if len(c.face_rects_by_photo[t_idx]) != prev_len:
                        removed_any = True
                    if not c.face_rects_by_photo[t_idx]:
                        del c.face_rects_by_photo[t_idx]
                        if t_idx in c.photo_indices:
                            c.photo_indices.remove(t_idx)

            if removed_any or c.contact_id == cid:
                # FR : Ne retirer photo_path de c.photo_paths que s'il ne reste plus aucun visage de cette personne sur cette photo
                # EN: Only remove photo_path from c.photo_paths if no other faces of this person remain on this photo
                sibling_1001 = set(getattr(self, "_parent_to_1001", {}).get(parent_photo_idx, [])) if parent_photo_idx is not None else set()
                all_photo_keys = target_indices | sibling_1001
                still_has_face_on_photo = any(
                    bool(c.face_rects_by_photo.get(k)) for k in all_photo_keys
                )
                if not still_has_face_on_photo and norm_photo:
                    c.photo_paths = [
                        p for p in c.photo_paths
                        if os.path.normpath(p).lower() != norm_photo
                    ]

        self.unnamed_faces = [
            (i, p, f) for (i, p, f) in self.unnamed_faces
            if not (
                (
                    (i is not None and i in target_indices)
                    or (p and norm_photo and os.path.normpath(p).lower() == norm_photo)
                )
                and _face_overlap(f, face_rect) >= 0.45
            )
        ]
        for scid in list(self.suggestions.keys()):
            self.suggestions[scid] = [
                s for s in self.suggestions[scid]
                if not (
                    (
                        (s.db_idx is not None and s.db_idx in target_indices)
                        or (s.photo_path and norm_photo and os.path.normpath(s.photo_path).lower() == norm_photo)
                    )
                    and _face_overlap(s.face_rect, face_rect) >= 0.45
                )
            ]

        if self.db and face_rec_idx is not None:
            for col_name in ("imagedata_personalbumid", "imagedata_suggestionpersonalbumid"):
                pmp = self.db.pmps.get(col_name)
                if pmp is not None and 0 <= face_rec_idx < len(pmp.records):
                    old_alb = pmp.records[face_rec_idx]
                    pmp.records[face_rec_idx] = 0
                    pmp.dirty = True
                    if old_alb and getattr(self.db, "wordhash", None) is not None:
                        if hasattr(self.db.wordhash, "remove_word"):
                            self.db.wordhash.remove_word(f"]facealbum:{old_alb}", face_rec_idx)
            # Ref: picasa3.exe @ 0x0044B963..0x0044BC83 (imagedata_tagdate = 0.0 when personalbumid cleared)
            pmp_td = self.db.pmps.get("imagedata_tagdate")
            if pmp_td is not None and 0 <= face_rec_idx < len(pmp_td.records) and pmp_td.records[face_rec_idx] != 0.0:
                pmp_td.records[face_rec_idx] = 0.0
                pmp_td.dirty = True
            if getattr(self.db, "wordhash", None) is not None:
                if hasattr(self.db.wordhash, "remove_word"):
                    self.db.wordhash.remove_word("]unknownface", face_rec_idx)
                self.db.wordhash.add_word("]ignoreface", face_rec_idx)

        # FR : Mise à jour du .picasa.ini
        # EN: Update .picasa.ini
        if photo_path:
            parent_dir = os.path.dirname(photo_path)
            fname = os.path.basename(photo_path)
            ini_path = os.path.join(parent_dir, ".picasa.ini")

            if os.path.exists(ini_path):
                doc = PicasaIniParser.parse_file(ini_path)
                faces = doc.get_faces(fname)
                rem_hex = face_rect.to_rect64()[7:-1].lower()
                new_faces: List[FaceItem] = []
                for item in faces:
                    if item.rect64.lower() == rem_hex:
                        continue
                    try:
                        item_fr = FaceRect.from_rect64(f"rect64({item.rect64})")
                        if _face_overlap(item_fr, face_rect) >= 0.45:
                            continue
                    except Exception:
                        pass
                    new_faces.append(item)

                doc.set_faces(fname, new_faces)
                doc.write_file(ini_path)
                if self.db and hasattr(self.db, "invalidate_ini_cache"):
                    self.db.invalidate_ini_cache(ini_path, invalidate_albums_starred=False)
                if self.db and hasattr(self.db, "sync_photo_ini_to_db"):
                    try:
                        self.db.sync_photo_ini_to_db(photo_path, doc)
                    except Exception:
                        pass
        self.notify_people_changed()

    def create_person(self, name: str) -> PersonCluster:
        """
        FR : Crée une nouvelle personne/contact dans Picasa.
        EN: Create a new person/contact in Picasa.
        Ref: picasa3.exe @ 0x008AAD76, contactmgr.fen
        """
        cid = secrets.token_hex(8)
        clean_name = name.strip()
        cluster = PersonCluster(contact_id=cid, name=clean_name)
        cluster._manager = self
        self.people[cid] = cluster

        if self.db:
            if getattr(self.db, "contacts", None) is None:
                self.db.contacts = ContactsFile()
            self.db.contacts.contacts.append(Contact(id=cid, name=clean_name))
            if getattr(self.db, "contacts_dir", None):
                try:
                    self.db.contacts_dir.mkdir(parents=True, exist_ok=True)
                    (self.db.contacts_dir / "contacts.xml").write_text(self.db.contacts.to_xml(), encoding="utf-8")
                except Exception:
                    pass

        self.notify_people_changed()
        return cluster

    def add_person(self, name: str, email: str = "", display: str = "") -> str:
        """
        FR : Crée une personne et retourne son identifiant hexadécimal `contact_id`.
        EN: Creates a person and returns their hexadecimal `contact_id`.
        Ref: picasa3.exe @ 0x008AAD76, contactmgr.fen
        """
        cluster = self.create_person(name)
        return cluster.contact_id

    def rename_person(self, contact_id: str | PersonCluster, new_name: str) -> bool:
        """
        FR : Renomme une personne existante (ou la fusionne si une autre personne porte déjà ce nom)
        et synchronise les `FaceRect`, `albumdata_name.pmp`, `contacts.xml` et `.picasa.ini`.
        EN: Rename an existing person (or merge if another person already has that name)
        and synchronize `FaceRect` objects, `albumdata_name.pmp`, `contacts.xml`, and `.picasa.ini`.
        Ref: picasa3.exe @ 0x008AAD76, contactmgr.fen
        """
        cid = (contact_id.contact_id if isinstance(contact_id, PersonCluster) else str(contact_id)).lower()
        cluster = self.people.get(cid)
        clean_new = new_name.strip()
        if not cluster or not clean_new:
            return False

        old_name = cluster.name
        existing_target: Optional[PersonCluster] = None
        for other in self.people.values():
            if other.contact_id != cid and other.name.strip().lower() == clean_new.lower():
                existing_target = other
                break

        if existing_target is not None:
            target_cid = existing_target.contact_id
            for p_idx in cluster.photo_indices:
                if p_idx not in existing_target.photo_indices:
                    existing_target.photo_indices.append(p_idx)
            for ppath in cluster.photo_paths:
                if ppath not in existing_target.photo_paths:
                    existing_target.photo_paths.append(ppath)
            for k, flist in cluster.face_rects_by_photo.items():
                t_flist = existing_target.face_rects_by_photo.setdefault(k, [])
                for fr in flist:
                    fr.contact_id = target_cid
                    fr.contact_name = existing_target.name
                    if not any(_face_overlap(ef, fr) >= 0.45 for ef in t_flist):
                        t_flist.append(fr)
            for flist in self.photo_to_faces.values():
                for fr in flist:
                    if (fr.contact_id or "").lower() == cid:
                        fr.contact_id = target_cid
                        fr.contact_name = existing_target.name
            for fv in cluster.feature_vectors:
                existing_target.feature_vectors.append(fv)
            if existing_target.feature_vector is None and cluster.feature_vector is not None:
                existing_target.feature_vector = cluster.feature_vector
            if existing_target.primary_face_rect is None and cluster.primary_face_rect is not None:
                existing_target.primary_face_rect = cluster.primary_face_rect
                existing_target.avatar_pixmap = cluster._avatar_pixmap

            old_sugs = self.suggestions.pop(cid, [])
            if old_sugs:
                t_sugs = self.suggestions.setdefault(target_cid, [])
                for s in old_sugs:
                    s.contact_id = target_cid
                    s.contact_name = existing_target.name
                    s.face_rect.contact_name = f"? {existing_target.name}"
                    t_sugs.append(s)

            for ppath in list(cluster.photo_paths):
                if not ppath:
                    continue
                ini_path = os.path.join(os.path.dirname(ppath), ".picasa.ini")
                if os.path.exists(ini_path):
                    try:
                        doc = PicasaIniParser.parse_file(ini_path)
                        sec_c2 = doc.get_or_create_section("Contacts2")
                        sec_c2.remove(cid)
                        sec_c2.set(target_cid, f"{existing_target.name};;")
                        fname = os.path.basename(ppath)
                        faces = doc.get_faces(fname)
                        changed_f = False
                        for item in faces:
                            if item.contact_id.lower() == cid:
                                item.contact_id = target_cid
                                changed_f = True
                        if changed_f:
                            doc.set_faces(fname, faces)
                        doc.write_file(ini_path)
                        if self.db and hasattr(self.db, "invalidate_ini_cache"):
                            self.db.invalidate_ini_cache(ini_path, invalidate_albums_starred=False)
                        if self.db and hasattr(self.db, "sync_photo_ini_to_db"):
                            try:
                                self.db.sync_photo_ini_to_db(ppath, doc)
                            except Exception:
                                pass
                    except Exception:
                        pass

            # FR : Fusionner aussi les colonnes PMP (imagedata_personalbumid, suggestionpersonalbumid, personalbumrecs),
            # wordhash.dat (]facealbum:<id>) et albumdata_* pour que Picasa3.exe voie la fusion
            # EN: Also merge PMP columns (imagedata_personalbumid, suggestionpersonalbumid, personalbumrecs),
            # wordhash.dat (]facealbum:<id>), and albumdata_* so Picasa3.exe sees the merge
            if self.db:
                with self.db._lock:
                    target_alb_idx = self._get_or_create_person_album_id(target_cid, existing_target.name)
                    ad_names = self.db.pmps.get("albumdata_name")
                    ad_cats = self.db.pmps.get("albumdata_category")
                    ad_cids = self.db.pmps.get("albumdata_albumcontactids")
                    ad_toks = self.db.pmps.get("albumdata_token")
                    ad_uids = self.db.pmps.get("albumdata_uid")
                    old_alb_ids: Set[int] = set()
                    cid_int_m: Optional[int] = None
                    try:
                        cid_int_m = int(cid, 16) & 0xFFFFFFFFFFFFFFFF
                    except Exception:
                        cid_int_m = None
                    if ad_names is not None and ad_cats is not None:
                        for i in range(1, len(ad_names.records)):
                            if i != target_alb_idx and i < len(ad_cats.records) and ad_cats.records[i] == 8:
                                if (ad_cids is not None and i < len(ad_cids.records) and cid_int_m is not None and ad_cids.records[i] == cid_int_m) or (
                                    str(ad_names.records[i] or "").strip().lower() == old_name.strip().lower()
                                ):
                                    old_alb_ids.add(i)
                    if old_alb_ids and target_alb_idx is not None and target_alb_idx > 0:
                        for col_name in ("imagedata_personalbumid", "imagedata_suggestionpersonalbumid", "imagedata_personalbumrecs"):
                            pmp_col = self.db.pmps.get(col_name)
                            if pmp_col is not None:
                                for r_idx, val in enumerate(pmp_col.records):
                                    if val in old_alb_ids:
                                        pmp_col.records[r_idx] = target_alb_idx
                                        pmp_col.dirty = True
                                        if col_name in ("imagedata_personalbumid", "imagedata_suggestionpersonalbumid") and getattr(self.db, "wordhash", None) is not None:
                                            if hasattr(self.db.wordhash, "remove_word"):
                                                self.db.wordhash.remove_word(f"]facealbum:{val}", r_idx)
                                            self.db.wordhash.add_word(f"]facealbum:{target_alb_idx}", r_idx)
                        for old_id in old_alb_ids:
                            if ad_cats is not None and old_id < len(ad_cats.records):
                                ad_cats.records[old_id] = 0
                                ad_cats.dirty = True
                            if ad_names is not None and old_id < len(ad_names.records):
                                ad_names.records[old_id] = ""
                                ad_names.dirty = True
                            if ad_cids is not None and old_id < len(ad_cids.records):
                                ad_cids.records[old_id] = 0
                                ad_cids.dirty = True
                            if ad_toks is not None and old_id < len(ad_toks.records):
                                ad_toks.records[old_id] = ""
                                ad_toks.dirty = True
                            if ad_uids is not None and old_id < len(ad_uids.records):
                                ad_uids.records[old_id] = ""
                                ad_uids.dirty = True

            del self.people[cid]
            if self.db and getattr(self.db, "contacts", None):
                self.db.contacts.contacts = [c for c in self.db.contacts.contacts if c.id.lower() != cid]
                if getattr(self.db, "contacts_dir", None):
                    try:
                        (self.db.contacts_dir / "contacts.xml").write_text(self.db.contacts.to_xml(), encoding="utf-8")
                    except Exception:
                        pass
            self.notify_people_changed()
            return True

        cluster.name = clean_new
        for flist in cluster.face_rects_by_photo.values():
            for fr in flist:
                fr.contact_name = clean_new
        for flist in self.photo_to_faces.values():
            for fr in flist:
                if (fr.contact_id or "").lower() == cid:
                    fr.contact_name = clean_new
        for s in self.suggestions.get(cid, []):
            s.contact_name = clean_new
            s.face_rect.contact_name = f"? {clean_new}"

        if self.db:
            ad_names = self.db.pmps.get("albumdata_name")
            ad_cats = self.db.pmps.get("albumdata_category")
            ad_cids = self.db.pmps.get("albumdata_albumcontactids")
            cid_int: Optional[int] = None
            try:
                cid_int = int(cid, 16) & 0xFFFFFFFFFFFFFFFF
            except Exception:
                cid_int = None
            if ad_names is not None and ad_cats is not None:
                for i in range(len(ad_names.records)):
                    if i < len(ad_cats.records) and ad_cats.records[i] == 8 and i > 0:
                        if (ad_cids is not None and i < len(ad_cids.records) and cid_int is not None and ad_cids.records[i] == cid_int) or (
                            str(ad_names.records[i] or "").strip().lower() == old_name.strip().lower()
                        ):
                            ad_names.records[i] = clean_new
                            ad_names.dirty = True

        updated_inis: Set[str] = set()
        for ppath in cluster.photo_paths:
            if not ppath:
                continue
            ini_path = os.path.join(os.path.dirname(ppath), ".picasa.ini")
            if ini_path in updated_inis or not os.path.exists(ini_path):
                continue
            updated_inis.add(ini_path)
            try:
                doc = PicasaIniParser.parse_file(ini_path)
                sec_c2 = doc.get_or_create_section("Contacts2")
                sec_c2.set(cid, f"{clean_new};;")
                doc.write_file(ini_path)
                if self.db and hasattr(self.db, "invalidate_ini_cache"):
                    self.db.invalidate_ini_cache(ini_path, invalidate_albums_starred=False)
            except Exception:
                pass

        if self.db and getattr(self.db, "contacts", None):
            for c in self.db.contacts.contacts:
                if c.id.lower() == cid:
                    c.name = clean_new
                    break
            if getattr(self.db, "contacts_dir", None):
                try:
                    (self.db.contacts_dir / "contacts.xml").write_text(self.db.contacts.to_xml(), encoding="utf-8")
                except Exception:
                    pass

        self.notify_people_changed()
        return True

    def delete_person(self, contact_id: str | PersonCluster) -> bool:
        """
        FR : Supprime une personne et ses associations, remet ses visages en sans-nom (`unnamed_faces`),
        et nettoie `suggestions`, `.picasa.ini`, `imagedata_personalbumid` et `contacts.xml`.
        EN: Delete a person and their associations, return their faces to `unnamed_faces`,
        and clean up `suggestions`, `.picasa.ini`, `imagedata_personalbumid`, and `contacts.xml`.
        Ref: picasa3.exe @ 0x008AAD76, contactmgr.fen
        """
        cid = (contact_id.contact_id if isinstance(contact_id, PersonCluster) else str(contact_id)).lower()
        cluster = self.people.pop(cid, None)
        popped_sugs = self.suggestions.pop(cid, [])

        for s in popped_sugs:
            s.face_rect.contact_id = ""
            s.face_rect.contact_name = None
            already_u = any(
                ((u_idx is not None and s.db_idx is not None and u_idx == s.db_idx) or (u_path and s.photo_path and os.path.normpath(u_path).lower() == os.path.normpath(s.photo_path).lower()))
                and _face_overlap(u_fr, s.face_rect) >= 0.45
                for u_idx, u_path, u_fr in self.unnamed_faces
            )
            if not already_u:
                self.unnamed_faces.append((s.db_idx, s.photo_path, s.face_rect))

        parent_to_1001 = getattr(self, "_parent_to_1001", {})
        for p_idx, flist in list(self.photo_to_faces.items()):
            for fr in flist:
                if (fr.contact_id or "").lower() == cid:
                    fr.contact_id = ""
                    fr.contact_name = None
                    is_parent_with_children = (
                        self.db is not None
                        and not getattr(self.db, "is_face_record", lambda i: False)(p_idx)
                        and p_idx in parent_to_1001
                    )
                    if not is_parent_with_children:
                        ppath = ""
                        if self.db:
                            try:
                                ppath = self.db.get_media_full_path(p_idx) or ""
                            except Exception:
                                ppath = ""
                        if not ppath and cluster and cluster.photo_paths:
                            ppath = cluster.photo_paths[0]
                        already_u = any(
                            ((u_idx is not None and u_idx == p_idx) or (u_path and ppath and os.path.normpath(u_path).lower() == os.path.normpath(ppath).lower()))
                            and _face_overlap(u_fr, fr) >= 0.45
                            for u_idx, u_path, u_fr in self.unnamed_faces
                        )
                        if not already_u:
                            self.unnamed_faces.append((p_idx, ppath, fr))

        if cluster:
            for ppath in list(cluster.photo_paths):
                if not ppath:
                    continue
                ini_path = os.path.join(os.path.dirname(ppath), ".picasa.ini")
                if not os.path.exists(ini_path):
                    continue
                try:
                    doc = PicasaIniParser.parse_file(ini_path)
                    sec_c2 = doc.get_section("Contacts2")
                    if sec_c2:
                        sec_c2.remove(cid)
                    fname = os.path.basename(ppath)
                    faces = doc.get_faces(fname)
                    remaining = [item for item in faces if item.contact_id.lower() != cid]
                    if len(remaining) != len(faces):
                        doc.set_faces(fname, remaining)
                    doc.write_file(ini_path)
                    if self.db and hasattr(self.db, "invalidate_ini_cache"):
                        self.db.invalidate_ini_cache(ini_path, invalidate_albums_starred=False)
                    if self.db and hasattr(self.db, "sync_photo_ini_to_db"):
                        try:
                            self.db.sync_photo_ini_to_db(ppath, doc)
                        except Exception:
                            pass
                except Exception:
                    pass

        if self.db:
            with self.db._lock:
                ad_names = self.db.pmps.get("albumdata_name")
                ad_cats = self.db.pmps.get("albumdata_category")
                ad_cids = self.db.pmps.get("albumdata_albumcontactids")
                ad_toks = self.db.pmps.get("albumdata_token")
                ad_uids = self.db.pmps.get("albumdata_uid")
                matching_alb_ids: Set[int] = set()
                cid_int: Optional[int] = None
                try:
                    cid_int = int(cid, 16) & 0xFFFFFFFFFFFFFFFF
                except Exception:
                    cid_int = None
                if ad_names is not None and ad_cats is not None:
                    for i in range(len(ad_names.records)):
                        if i < len(ad_cats.records) and ad_cats.records[i] == 8 and i > 0:
                            if (ad_cids is not None and i < len(ad_cids.records) and cid_int is not None and ad_cids.records[i] == cid_int) or (
                                cluster and str(ad_names.records[i] or "").strip().lower() == cluster.name.strip().lower()
                            ):
                                matching_alb_ids.add(i)

                reset_face_indices: Set[int] = set()
                for col_name in ("imagedata_personalbumid", "imagedata_suggestionpersonalbumid"):
                    pmp = self.db.pmps.get(col_name)
                    if pmp is not None:
                        if cluster:
                            for p_idx in cluster.photo_indices:
                                if 0 <= p_idx < len(pmp.records) and pmp.records[p_idx] != 0:
                                    old_v = pmp.records[p_idx]
                                    pmp.records[p_idx] = 0
                                    pmp.dirty = True
                                    reset_face_indices.add(p_idx)
                                    if getattr(self.db, "wordhash", None) is not None and hasattr(self.db.wordhash, "remove_word"):
                                        self.db.wordhash.remove_word(f"]facealbum:{old_v}", p_idx)
                        if matching_alb_ids:
                            for r_idx, val in enumerate(pmp.records):
                                if val in matching_alb_ids:
                                    pmp.records[r_idx] = 0
                                    pmp.dirty = True
                                    reset_face_indices.add(r_idx)
                                    if getattr(self.db, "wordhash", None) is not None and hasattr(self.db.wordhash, "remove_word"):
                                        self.db.wordhash.remove_word(f"]facealbum:{val}", r_idx)

                # Ref: picasa3.exe @ 0x0044C623..0x0044C84A (imagedata_tagdate = 0.0 when personalbumid cleared)
                pmp_td = self.db.pmps.get("imagedata_tagdate")
                if pmp_td is not None:
                    for r_idx in reset_face_indices:
                        if 0 <= r_idx < len(pmp_td.records) and pmp_td.records[r_idx] != 0.0:
                            pmp_td.records[r_idx] = 0.0
                            pmp_td.dirty = True

                if getattr(self.db, "wordhash", None) is not None:
                    for r_idx in reset_face_indices:
                        if getattr(self.db, "is_face_record", lambda i: False)(r_idx):
                            self.db.wordhash.add_word("]unknownface", r_idx)

                for old_id in matching_alb_ids:
                    if ad_cats is not None and old_id < len(ad_cats.records):
                        ad_cats.records[old_id] = 0
                        ad_cats.dirty = True
                    if ad_names is not None and old_id < len(ad_names.records):
                        ad_names.records[old_id] = ""
                        ad_names.dirty = True
                    if ad_cids is not None and old_id < len(ad_cids.records):
                        ad_cids.records[old_id] = 0
                        ad_cids.dirty = True
                    if ad_toks is not None and old_id < len(ad_toks.records):
                        ad_toks.records[old_id] = ""
                        ad_toks.dirty = True
                    if ad_uids is not None and old_id < len(ad_uids.records):
                        ad_uids.records[old_id] = ""
                        ad_uids.dirty = True

        if self.db and getattr(self.db, "contacts", None):
            self.db.contacts.contacts = [c for c in self.db.contacts.contacts if c.id.lower() != cid]
            if getattr(self.db, "contacts_dir", None):
                try:
                    (self.db.contacts_dir / "contacts.xml").write_text(self.db.contacts.to_xml(), encoding="utf-8")
                except Exception:
                    pass

        self.notify_people_changed()
        return True

    def get_suggestions(self, contact_id: str | PersonCluster) -> List[FaceSuggestion]:
        """
        FR : Renvoie la liste des visages suggérés pour un contact.
        EN: Return the list of suggested faces for a contact.
        """
        if not self._suggestions_rebuilt:
            self._rebuild_suggestions_from_templates()
        cid = (contact_id.contact_id if isinstance(contact_id, PersonCluster) else str(contact_id)).lower()
        return self.suggestions.get(cid, [])

    def get_all_suggestions(self) -> List[FaceSuggestion]:
        """
        FR : Renvoie l'ensemble des suggestions en attente de validation.
        EN: Return all pending face suggestions awaiting confirmation.
        """
        if not self._suggestions_rebuilt:
            self._rebuild_suggestions_from_templates()
        res: List[FaceSuggestion] = []
        for sugs in self.suggestions.values():
            res.extend(sugs)
        return res

    def confirm_suggestion(self, suggestion: FaceSuggestion) -> FaceRect:
        """
        FR : Valide une suggestion de visage et l'assigne définitivement au contact.
        EN: Confirm a face suggestion and permanently assign it to the contact.
        Ref: picasa3.exe @ peoplepanel/suggestion_yes, confirmsug (0x00896F74)
        """
        fr = self.add_face(
            suggestion.photo_path,
            suggestion.face_rect,
            suggestion.contact_name,
            contact_id=suggestion.contact_id,
            db_idx=suggestion.db_idx
        )
        cid = suggestion.contact_id.lower()
        if cid in self.suggestions:
            self.suggestions[cid] = [s for s in self.suggestions[cid] if s is not suggestion]
        return fr

    def reject_suggestion(self, suggestion: FaceSuggestion) -> None:
        """
        FR : Rejette une suggestion de visage (le visage redevient sans nom dans `unnamed_faces`
        et `imagedata_suggestionpersonalbumid` est remis à `0`).
        EN: Reject a face suggestion (the face returns to `unnamed_faces` as unnamed
        and `imagedata_suggestionpersonalbumid` is reset to `0`).
        Ref: picasa3.exe @ peoplepanel/suggestion_no (0x008A13D8)
        """
        cid = suggestion.contact_id.lower()
        if cid in self.suggestions:
            self.suggestions[cid] = [s for s in self.suggestions[cid] if s is not suggestion]

        db_idx = suggestion.db_idx
        parent_photo_idx: Optional[int] = None
        face_rec_idx: Optional[int] = None
        if db_idx is not None and db_idx >= 0 and self.db:
            if getattr(self.db, "is_face_record", lambda i: False)(db_idx):
                face_rec_idx = db_idx
                parent_photo_idx = self.db.get_face_parent_photo_idx(db_idx)
            else:
                parent_photo_idx = db_idx
                face_rec_idx = self._find_matching_1001_child(parent_photo_idx, suggestion.face_rect)
        elif db_idx is not None and db_idx >= 0:
            parent_photo_idx = db_idx

        suggestion.face_rect.contact_id = ""
        suggestion.face_rect.contact_name = None

        for t_idx in {idx for idx in (db_idx, face_rec_idx, parent_photo_idx) if idx is not None}:
            for ef in self.photo_to_faces.get(t_idx, []):
                if _face_overlap(ef, suggestion.face_rect) >= 0.45:
                    ef.contact_id = ""
                    ef.contact_name = None

        eff_idx = face_rec_idx if face_rec_idx is not None else parent_photo_idx
        if eff_idx is not None and cid:
            if not hasattr(self, "_rejected_suggestions"):
                self._rejected_suggestions = set()
            self._rejected_suggestions.add((eff_idx, cid))
        norm_p = os.path.normpath(suggestion.photo_path).lower() if suggestion.photo_path else ""
        already_unnamed = any(
            (
                (u_idx is not None and eff_idx is not None and u_idx == eff_idx)
                or (u_path and norm_p and os.path.normpath(u_path).lower() == norm_p)
            )
            and _face_overlap(u_fr, suggestion.face_rect) >= 0.45
            for u_idx, u_path, u_fr in self.unnamed_faces
        )
        if not already_unnamed:
            self.unnamed_faces.append((eff_idx, suggestion.photo_path, suggestion.face_rect))

        if self.db:
            with self.db._lock:
                pmp_sug = self.db.pmps.get("imagedata_suggestionpersonalbumid")
                if pmp_sug is not None:
                    for t_idx in {idx for idx in (face_rec_idx, db_idx) if idx is not None}:
                        if 0 <= t_idx < len(pmp_sug.records):
                            old_sug = pmp_sug.records[t_idx]
                            pmp_sug.records[t_idx] = 0
                            pmp_sug.dirty = True
                            if getattr(self.db, "wordhash", None) is not None:
                                if old_sug and hasattr(self.db.wordhash, "remove_word"):
                                    self.db.wordhash.remove_word(f"]facealbum:{old_sug}", t_idx)
                                if getattr(self.db, "is_face_record", lambda i: False)(t_idx):
                                    self.db.wordhash.add_word("]unknownface", t_idx)

        # FR : Si .picasa.ini contenait une entrée obsolète faces=rect64(...),cid pour ce visage rejeté, la nettoyer
        # EN: If .picasa.ini had a stale faces=rect64(...),cid entry for this rejected face, clean it up
        if suggestion.photo_path and os.path.exists(os.path.dirname(suggestion.photo_path)):
            try:
                pdir = os.path.dirname(suggestion.photo_path)
                pfname = os.path.basename(suggestion.photo_path)
                ini_p = os.path.join(pdir, ".picasa.ini")
                if os.path.exists(ini_p):
                    doc = PicasaIniParser.parse_file(ini_p)
                    sec = doc.get_section(pfname)
                    if sec is not None:
                        faces_str = sec.get("faces")
                        if faces_str:
                            kept_parts: List[str] = []
                            changed_ini = False
                            for part in faces_str.split(";"):
                                part_s = part.strip()
                                if not part_s or "," not in part_s:
                                    continue
                                r_part, c_part = part_s.split(",", 1)
                                try:
                                    fr_ini = FaceRect.from_rect64(r_part)
                                    if _face_overlap(fr_ini, suggestion.face_rect) >= 0.45 and c_part.strip().lower() != "ffffffffffffffff":
                                        changed_ini = True
                                        continue
                                except Exception:
                                    pass
                                kept_parts.append(part_s)
                            if changed_ini:
                                if kept_parts:
                                    sec.set("faces", ";".join(kept_parts))
                                else:
                                    sec.remove("faces")
                                doc.write_file(ini_p)
                                if self.db and hasattr(self.db, "invalidate_ini_cache"):
                                    self.db.invalidate_ini_cache(ini_p)
            except Exception:
                pass

        self.notify_people_changed()

    def confirm_all_suggestions(self, contact_id: str | PersonCluster) -> int:
        """
        FR : Valide d'un seul clic toutes les suggestions en attente pour un contact.
        EN: Confirm all pending suggestions for a contact in a single action.
        Ref: picasa3.exe @ confirmsug (0x00896F74 - 'Tout confirmer')
        """
        cid = (contact_id.contact_id if isinstance(contact_id, PersonCluster) else str(contact_id)).lower()
        sugs = list(self.suggestions.get(cid, []))
        count = 0
        for s in sugs:
            self.confirm_suggestion(s)
            count += 1
        return count

    def save_face_tag(self, file_path: str, face_rect: FaceRect, contact_id: str, contact_name: str) -> None:
        """
        FR : Méthode de compatibilité descendante pour l'enregistrement d'un tag de visage.
        EN: Backward-compatibility helper to save a face tag.
        """
        self.add_face(file_path, face_rect, contact_name, contact_id=contact_id)

    def get_unscanned_photos(
        self,
        folder_paths: Optional[List[str]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> List[Tuple[int, str]]:
        """
        FR : Renvoie la liste des photos `(db_idx, photo_path)` qui n'ont pas encore été analysées
        par le moteur de détection des visages (`BgFaceDetectThread`), en excluant :
        - les dossiers (`type == 1`),
        - les vidéos (`type == 0x20`),
        - les enregistrements enfants de visages (`type == 1001`),
        - les dossiers marqués `frexclude=1` dans `[Picasa]` de `.picasa.ini`.
        EN: Return the list of photos `(db_idx, photo_path)` not yet scanned by the face
        detection engine (`BgFaceDetectThread`), excluding:
        - folders (`type == 1`),
        - videos (`type == 0x20`),
        - child face records (`type == 1001`),
        - folders marked `frexclude=1` in `[Picasa]` of `.picasa.ini`.

        Ref: picasa3.exe @ 0x0087ECD6 (BgFaceDetectThread), 0x00881690 (frexclude=1)
        """
        if not self.db:
            return []

        folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
        allowed_folders_norm: Optional[Set[str]] = None
        if folder_paths:
            allowed_folders_norm = {
                os.path.abspath(p).replace("/", "\\").rstrip("\\").lower()
                for p in folder_paths if p
            }

        excluded_dirs_cache: Dict[str, bool] = {}

        def _is_folder_frexcluded(dpath: str) -> bool:
            norm_d = dpath.replace("/", "\\").rstrip("\\").lower()
            if norm_d in excluded_dirs_cache:
                return excluded_dirs_cache[norm_d]
            res = False
            for ini_name in (".picasa.ini", "Picasa.ini"):
                ini_p = os.path.join(dpath, ini_name)
                doc = self.db.get_parsed_ini(ini_p) if hasattr(self.db, "get_parsed_ini") else None
                if doc is None and not hasattr(self.db, "get_parsed_ini") and os.path.exists(ini_p):
                    try:
                        doc = PicasaIniParser.parse_file(ini_p)
                    except Exception:
                        doc = None
                if doc is not None:
                    sec_p = doc.get_section("Picasa")
                    if sec_p and (sec_p.get("frexclude") or "").strip().lower() in ("1", "yes", "true"):
                        res = True
                        break
            excluded_dirs_cache[norm_d] = res
            return res

        candidates: List[Tuple[int, str]] = []
        for idx, rec in enumerate(self.db.index):
            if is_cancelled and is_cancelled():
                break
            if rec.type in (1, 0x20, 1001):
                continue
            if idx in self._scanned_photo_indices or idx in self.photo_to_faces:
                continue

            fdir = folders_map.get(rec.parent_idx, "")
            if not fdir:
                continue

            norm_fdir = os.path.abspath(fdir).replace("/", "\\").rstrip("\\").lower()
            if allowed_folders_norm is not None:
                if not any(norm_fdir == af or norm_fdir.startswith(af + "\\") for af in allowed_folders_norm):
                    continue

            if _is_folder_frexcluded(fdir):
                self._scanned_photo_indices.add(idx)
                continue

            full_path = os.path.join(fdir, rec.path)
            if os.path.exists(full_path):
                candidates.append((idx, full_path))

        return candidates

    def _sync_faces_to_ini(self, photo_idx_or_path: int | str | Path) -> None:
        """
        FR : Synchronise les visages d'une photo (et les contacts associés dans `[Contacts2]`)
        vers le fichier `.picasa.ini` du dossier parent.
        EN: Synchronize a photo's faces (and associated contacts in `[Contacts2]`)
        into the parent folder's `.picasa.ini` file.
        Ref: picasa3.exe @ 0x008C1F34 (FaceSyncer), 0x0068BABA
        """
        db_idx: Optional[int] = None
        photo_path: str = ""
        if isinstance(photo_idx_or_path, int):
            db_idx = photo_idx_or_path
            if self.db:
                photo_path = self.db.get_media_full_path(db_idx) or ""
        else:
            photo_path = str(photo_idx_or_path or "")
            if self.db and photo_path:
                if hasattr(self.db, "find_photo_index"):
                    db_idx = self.db.find_photo_index(photo_path)
                else:
                    folders_map = {i: r.path for i, r in enumerate(self.db.index) if r.type == 1}
                    norm_dir = os.path.dirname(photo_path).replace("/", "\\").rstrip("\\").lower()
                    fname_lower = os.path.basename(photo_path).lower()
                    for i, r in enumerate(self.db.index):
                        if r.type not in (0, 1, 1001) and r.path.lower() == fname_lower:
                            fpath = folders_map.get(r.parent_idx, "")
                            if fpath.replace("/", "\\").rstrip("\\").lower() == norm_dir:
                                db_idx = i
                                break
        if not photo_path:
            return
        parent_dir = os.path.dirname(photo_path)
        fname = os.path.basename(photo_path)
        ini_path = os.path.join(parent_dir, ".picasa.ini")
        doc = PicasaIniParser.parse_file(ini_path) if os.path.exists(ini_path) else PicasaIniDocument()
        faces_list = self.get_faces_for_photo(db_idx) if db_idx is not None else []
        sec_c2 = doc.get_or_create_section("Contacts2")
        items: List[FaceItem] = []
        for fr in faces_list:
            raw_cid = (fr.contact_id or "").strip().lower()
            if raw_cid in ("", "0", "unknown", "unnamed"):
                continue
            cid = raw_cid
            if cid != "ffffffffffffffff":
                cname = (fr.contact_name or "").lstrip("? ").strip()
                if not cname and cid in self.people:
                    cname = self.people[cid].name
                if cname:
                    sec_c2.set(cid, f"{cname};;")
            r64_clean = fr.to_rect64()[7:-1]
            items.append(FaceItem(rect64=r64_clean, contact_id=cid))
        doc.set_faces(fname, items)
        doc.write_file(ini_path)
        if self.db and hasattr(self.db, "invalidate_ini_cache"):
            self.db.invalidate_ini_cache(ini_path, invalidate_albums_starred=False)


# Ref: picasa3.exe @ 0x0087ECD6 (BgFaceDetectThread), 0x0093B9CE (CFaceDetector), 0x008C1F34 (FaceSyncer)
# Ghidra project: ghidra/picasa3.gpr
class BackgroundFaceDetectionWorker(QThread):
    """
    FR : Worker thread d'arrière-plan (`BgFaceDetectThread`) exécutant la détection automatique
    des visages (`CFaceDetector`) et le rapprochement/suggestion de contacts (`FaceSyncer`)
    sur les photos indexées non encore analysées, sans jamais bloquer le thread UI.
    EN: Background worker thread (`BgFaceDetectThread`) running automatic face detection
    (`CFaceDetector`) and contact matching/suggestion (`FaceSyncer`) on unscanned indexed
    photos without blocking the UI thread.

    Ref: picasa3.exe @ 0x0087ECD6 (BgFaceDetectThread)
    Ref: picasa3.exe @ 0x0093B9CE (CFaceDetector)
    Ref: picasa3.exe @ 0x008C1F34 (FaceSyncer)
    Ref: picasa3.exe @ 0x00881CC0 (FRSuggestionThreshold)
    Ref: picasa3.exe @ 0x008AAD76 (NOTIFY_PEOPLE_CHANGED)
    """

    progress = Signal(int, int, str)        # (current, total, filename)
    faces_detected = Signal(int, str, int)  # (db_idx, photo_path, new_face_count)
    people_updated = Signal()               # FR : Émis périodiquement / EN: Emitted periodically when new faces are found
    finished = Signal(int)                  # (total_new_faces_detected)

    def __init__(
        self,
        db: PicasaDatabase,
        folder_paths: Optional[List[str]] = None,
        persist_ini: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.db = db
        self.folder_paths = folder_paths
        self.persist_ini = persist_ini
        self._is_cancelled = False

    def start(self, priority: QThread.Priority = QThread.Priority.LowestPriority) -> None:
        """
        FR : Démarre le thread de détection des visages avec la priorité OS la plus basse
        (`LowestPriority`) afin de ne jamais concurrencer le thread GUI ni le scan de dossiers.
        EN: Starts the face detection thread with `LowestPriority` OS scheduling so it never
        competes with the GUI thread or folder scanning.
        """
        super().start(priority)

    def cancel(self) -> None:
        """
        FR : Demande l'arrêt du thread de détection en arrière-plan.
        EN: Request termination of the background detection thread.
        """
        self._is_cancelled = True

    def __del__(self) -> None:
        try:
            self._is_cancelled = True
            if self.isRunning():
                self.wait(2000)
        except Exception:
            pass


    def run(self) -> None:
        """
        FR : Boucle principale d'analyse faciale en arrière-plan (`BgFaceDetectThread`).
        EN: Main background face detection loop (`BgFaceDetectThread`).
        Ref: picasa3.exe @ 0x0087ECD6 (BgFaceDetectThread -> THREAD_PRIORITY_LOWEST)
        """
        from picasa_py.scanner.scanner import BackgroundScanWorker, set_current_thread_background_priority
        if self.isRunning():
            set_current_thread_background_priority(lowest=True)
        if not self.db or not getattr(self.db, "face_manager", None):
            self.finished.emit(0)
            return

        fm: PicasaFaceManager = self.db.face_manager
        if not fm._suggestions_rebuilt:
            fm._rebuild_suggestions_from_templates()
        candidates = fm.get_unscanned_photos(
            folder_paths=self.folder_paths,
            is_cancelled=lambda: self._is_cancelled,
        )

        total = len(candidates)
        if total == 0:
            self.finished.emit(0)
            return

        total_detected = 0
        pending_ui_notify = 0
        last_emit_time = time.monotonic()
        last_progress_emit = 0.0
        is_running_thread = self.isRunning()
        throttle_signals = is_running_thread and total > 15

        for i, (db_idx, photo_path) in enumerate(candidates):
            if self._is_cancelled:
                break

            if is_running_thread:
                # FR: En cas d'interaction GUI récente, mettre en pause la détection des visages
                # pour laisser 100 % du CPU/GIL à l'interface utilisateur.
                # EN: On recent GUI interaction, pause face detection to give 100% of CPU/GIL to the UI.
                while not self._is_cancelled and (time.monotonic() - BackgroundScanWorker._last_gui_activity_ts) < 0.60:
                    time.sleep(0.050)
                BackgroundScanWorker.yield_for_gui(0.012)

            fname = os.path.basename(photo_path)
            now = time.monotonic()
            if not throttle_signals or i == 0 or (i + 1) == total or (now - last_progress_emit) >= 0.20:
                last_progress_emit = now
                self.progress.emit(i + 1, total, fname)

            before_count = len(fm.get_faces_for_photo(db_idx))
            try:
                after_faces = fm.detect_faces_for_photo(
                    photo_path,
                    db_idx=db_idx,
                    auto_suggest=True,
                    persist_ini=self.persist_ini,
                )
                added = max(0, len(after_faces) - before_count)
                if added > 0:
                    total_detected += added
                    pending_ui_notify += added
                    if not throttle_signals or (now - last_emit_time) >= 1.0:
                        self.faces_detected.emit(db_idx, photo_path, added)
                    now = time.monotonic()
                    if now - last_emit_time >= 3.0:
                        pending_ui_notify = 0
                        last_emit_time = now
                        self.people_updated.emit()
            except Exception:
                pass

        if total_detected > 0:
            if self.db is not None and hasattr(self.db, "save_database"):
                # FR : Attendre une pause de l'utilisateur avant la sauvegarde (CSlowTaskManager @ 0x005E4F6E)
                # EN: Wait for a user pause before saving (CSlowTaskManager @ 0x005E4F6E)
                if is_running_thread:
                    waited = 0.0
                    while not self._is_cancelled and BackgroundScanWorker.is_gui_active(0.5) and waited < 10.0:
                        time.sleep(0.05)
                        waited += 0.05
                try:
                    self.db.save_database()
                except Exception:
                    pass
            self.people_updated.emit()

        self.finished.emit(total_detected)


FaceManager = PicasaFaceManager


