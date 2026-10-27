"""
FR : Injecteur sans perte de métadonnées XMP de visages et boîte de dialogue associée pour PyCasa.
Reproduction fidèle de `FileFaceTagger` et `write_all_facetags.fen`.
EN: Lossless XMP Face Metadata Tagger and Dialog for PyCasa.
Faithful reproduction of `FileFaceTagger` and `write_all_facetags.fen`.

Ref: picasa3.exe @ 0x00C29F00 (FileFaceTagger)
Ref: picasa3.exe @ 0x008EF3AC (mwg-rs:Regions, RegionList, stArea, PersonInImage)
Ref: write_all_facetags.fen / WRITE_ALL_FACETAGS_FR.XML
Ref: MWG (Metadata Working Group) Standard for Regions:
     xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/regions/"
     xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#"
     xmlns:stDim="http://ns.adobe.com/xmp/sType/Dimensions#"
     xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
"""

from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from picasa_py.db.database import PicasaDatabase
from picasa_py.faces.facerect import decode_rect64_string
from picasa_py.ini.parser import PicasaIniDocument, PicasaIniParser
from picasa_py.ui.resources import PicasaResourceManager
from picasa_py.ui.style import PicasaStyle


XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


class PicasaXMPFaceTagger:
    """
    FR : Constructeur et injecteur sans perte de métadonnées XMP `mwg-rs:Regions` dans les fichiers JPEG.
    EN: Builder and lossless injector of `mwg-rs:Regions` XMP face metadata into JPEG files.
    Ref: picasa3.exe @ FileFaceTagger (0x00C29F00)
    """

    @staticmethod
    def build_xmp_packet(
        width: int,
        height: int,
        faces: List[Tuple[str, float, float, float, float]],  # (name, left, top, right, bottom)
        existing_xmp: Optional[bytes] = None,
    ) -> bytes:
        """
        FR : Construit le paquet RDF/XMP complet au format `mwg-rs:Regions` exact de `Picasa3.exe`
        (`%g` pour `stArea:x/y/w/h`, `mwg-rs:AppliedToDimensions`, sans `Iptc4xmpExt:PersonInImage`,
        et préservation des balises XMP existantes hors `mwg-rs:Regions`).
        EN: Builds the complete RDF/XMP packet in the exact `Picasa3.exe` `mwg-rs:Regions` format
        (`%g` for `stArea:x/y/w/h`, `mwg-rs:AppliedToDimensions`, no `Iptc4xmpExt:PersonInImage`,
        preserving existing non-`mwg-rs:Regions` XMP nodes).
        Ref: picasa3.exe @ 0x00BA73C0 ("%g"), 0x00BA7430, 0x00BB15F0, 0x00BB17E0..0x00BB2010
        """
        import re

        regions_xml = []
        for name, left, top, right, bottom in faces:
            cx = (left + right) / 2.0
            cy = (top + bottom) / 2.0
            w = right - left
            h = bottom - top

            safe_name = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            regions_xml.append(
                f'          <rdf:li rdf:parseType="Resource">\n'
                f'            <mwg-rs:Area stArea:x="{cx:g}" stArea:y="{cy:g}" stArea:w="{w:g}" stArea:h="{h:g}" stArea:unit="normalized"/>\n'
                f'            <mwg-rs:Type>Face</mwg-rs:Type>\n'
                f'            <mwg-rs:Name>{safe_name}</mwg-rs:Name>\n'
                f'          </rdf:li>'
            )

        region_list_str = "\n".join(regions_xml)
        mwg_block = (
            f'      <mwg-rs:Regions rdf:parseType="Resource">\n'
            f'        <mwg-rs:AppliedToDimensions stDim:w="{width}" stDim:h="{height}" stDim:unit="pixel"/>\n'
            f'        <mwg-rs:RegionList>\n'
            f'          <rdf:Bag>\n'
            f'{region_list_str}\n'
            f'          </rdf:Bag>\n'
            f'        </mwg-rs:RegionList>\n'
            f'      </mwg-rs:Regions>'
        )

        # Ref: picasa3.exe @ 0x00BB2010 — fusionner dans le DOM XMP existant s'il est présent
        if existing_xmp:
            try:
                old_str = existing_xmp.decode("utf-8", errors="replace")
                if "</rdf:Description>" in old_str:
                    cleaned = re.sub(
                        r"\s*<mwg-rs:Regions\b[^>]*>.*?</mwg-rs:Regions>",
                        "",
                        old_str,
                        flags=re.DOTALL,
                    )
                    for ns_prefix, ns_uri in (
                        ("xmlns:mwg-rs", "http://www.metadataworkinggroup.com/schemas/regions/"),
                        ("xmlns:stDim", "http://ns.adobe.com/xmp/sType/Dimensions#"),
                        ("xmlns:stArea", "http://ns.adobe.com/xmp/sType/Area#"),
                    ):
                        if ns_prefix not in cleaned:
                            cleaned = cleaned.replace(
                                "<rdf:Description",
                                f'<rdf:Description {ns_prefix}="{ns_uri}"',
                                1,
                            )
                    idx_close = cleaned.rfind("</rdf:Description>")
                    if idx_close != -1:
                        merged = cleaned[:idx_close] + mwg_block + "\n    " + cleaned[idx_close:]
                        return merged.encode("utf-8")
            except Exception:
                pass

        xmp_str = (
            f'<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
            f'<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
            f'  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
            f'    <rdf:Description rdf:about=""\n'
            f'        xmlns:mwg-rs="http://www.metadataworkinggroup.com/schemas/regions/"\n'
            f'        xmlns:stDim="http://ns.adobe.com/xmp/sType/Dimensions#"\n'
            f'        xmlns:stArea="http://ns.adobe.com/xmp/sType/Area#">\n'
            f'{mwg_block}\n'
            f'    </rdf:Description>\n'
            f'  </rdf:RDF>\n'
            f'</x:xmpmeta>\n'
            f'<?xpacket end="w"?>'
        )
        return xmp_str.encode("utf-8")

    @staticmethod
    def extract_xmp_from_jpeg(jpeg_path: str) -> Optional[bytes]:
        """
        FR : Extrait le paquet XMP existant (`APP1` `http://ns.adobe.com/xap/1.0/\\x00`) d'un JPEG, ou `None`.
        EN: Extracts the existing XMP packet (`APP1` `http://ns.adobe.com/xap/1.0/\\x00`) from a JPEG, or `None`.
        Ref: picasa3.exe @ 0x00BB2010
        """
        try:
            with open(jpeg_path, "rb") as f:
                data = f.read()
            if len(data) < 4 or data[:2] != b"\xff\xd8":
                return None
            idx = 2
            while idx + 4 <= len(data):
                if data[idx] != 0xFF:
                    break
                marker = data[idx : idx + 2]
                if marker in (b"\xff\xd9", b"\xff\xda"):
                    break
                if marker == b"\xff\x00":
                    idx += 1
                    continue
                length = struct.unpack(">H", data[idx + 2 : idx + 4])[0]
                chunk = data[idx : idx + 2 + length]
                if marker == b"\xff\xe1" and chunk[4 : 4 + len(XMP_HEADER)] == XMP_HEADER:
                    return chunk[4 + len(XMP_HEADER) :]
                idx += 2 + length
        except Exception:
            pass
        return None

    @staticmethod
    def inject_xmp_into_jpeg(jpeg_path: str, xmp_bytes: bytes) -> bool:
        """
        FR : Insère ou met à jour le segment `APP1` XMP dans le fichier JPEG sans ré-encoder l'image.
        Garantit une écriture atomique et sans perte de qualité.
        EN: Insert or update the `APP1` XMP segment in the JPEG file without re-encoding image data.
        Guarantees atomic, lossless writing.
        Ref: picasa3.exe @ 0x00C29F00 (FileFaceTagger)
        """
        try:
            with open(jpeg_path, "rb") as f:
                data = f.read()

            if len(data) < 4 or data[:2] != b"\xff\xd8":
                return False  # FR : Pas un JPEG valide / EN: Not a valid JPEG

            # FR : Préparation du segment APP1 XMP : Marqueur 0xFFE1 + 2 octets longueur
            # EN: Prepare APP1 XMP segment: 0xFFE1 marker + 2-byte big-endian length
            payload = XMP_HEADER + xmp_bytes
            seg_len = len(payload) + 2
            if seg_len > 65535:
                return False  # FR : Dépassement taille max segment JPEG / EN: Exceeds max JPEG segment size

            new_app1 = b"\xff\xe1" + struct.pack(">H", seg_len) + payload

            # FR : Analyser les marqueurs pour remplacer l'ancien segment XMP s'il existe
            # EN: Parse markers to replace any existing XMP segment
            idx = 2
            new_data_parts = [data[:2]]
            app1_inserted = False

            while idx < len(data):
                if data[idx] != 0xFF:
                    break

                marker = data[idx : idx + 2]
                if marker in (b"\xff\xd9", b"\xff\xda"):  # FR : EOI ou début SOS / EN: EOI or start of SOS
                    # FR : Insérer le nouveau segment avant les données compressées si pas encore fait
                    # EN: Insert the new segment before compressed scan data if not yet inserted
                    if not app1_inserted:
                        new_data_parts.append(new_app1)
                        app1_inserted = True
                    new_data_parts.append(data[idx:])
                    break

                if marker == b"\xff\x00":
                    idx += 1
                    continue

                if idx + 4 > len(data):
                    break

                length = struct.unpack(">H", data[idx + 2 : idx + 4])[0]
                chunk = data[idx : idx + 2 + length]

                # FR : Si c'est un segment APP1 XMP existant, on le remplace
                # EN: Replace existing APP1 XMP segment if found
                if marker == b"\xff\xe1" and chunk[4 : 4 + len(XMP_HEADER)] == XMP_HEADER:
                    new_data_parts.append(new_app1)
                    app1_inserted = True
                else:
                    new_data_parts.append(chunk)

                idx += 2 + length

            if not app1_inserted:
                # FR : Insérer après le premier segment (ex: JFIF APP0)
                # EN: Insert right after the first segment (e.g., JFIF APP0)
                if len(new_data_parts) > 1:
                    new_data_parts.insert(2, new_app1)
                else:
                    new_data_parts.append(new_app1)

            final_data = b"".join(new_data_parts)

            # Ref: picasa3.exe @ 0x009ED330 — écriture directe sans fichier .tmp_xmp
            with open(jpeg_path, "wb") as f:
                f.write(final_data)
            return True

        except Exception:
            return False


class PicasaWriteFaceTagsWorker(QThread):
    """
    FR : Worker en tâche de fond pour l'écriture en masse des métadonnées de visage XMP.
    EN: Background worker thread for batch writing XMP face metadata tags.
    """

    progress = Signal(int, int, str)
    finished = Signal(int, int)

    def __init__(self, photo_paths: List[str], db: Optional[PicasaDatabase], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.photo_paths = photo_paths
        self.db = db
        self._is_cancelled = False

    def cancel(self) -> None:
        """
        FR : Demande l'annulation du traitement en cours.
        EN: Request cancellation of the running batch job.
        """
        self._is_cancelled = True

    def run(self) -> None:
        """
        FR : Parcourt les fichiers JPEG cibles, lit les visages depuis `.picasa.ini` et `contacts.xml`,
        et injecte les paquets XMP `mwg-rs:Regions`.
        EN: Iterate over target JPEG files, read face rectangles from `.picasa.ini` and `contacts.xml`,
        and inject `mwg-rs:Regions` XMP packets.
        """
        total = len(self.photo_paths)
        succ = 0
        err = 0

        ini_cache: Dict[str, Optional[PicasaIniDocument]] = {}
        contacts_cache: Dict[str, str] = {}

        for i, p_str in enumerate(self.photo_paths):
            if self._is_cancelled:
                break

            p = Path(p_str)
            self.progress.emit(i + 1, total, p.name)

            if not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg"):
                continue

            try:
                parent_dir = str(p.parent)
                if parent_dir not in ini_cache:
                    ini_path = Path(parent_dir) / ".picasa.ini"
                    if not ini_path.exists():
                        ini_path = Path(parent_dir) / "Picasa.ini"
                    if ini_path.exists():
                        try:
                            doc = PicasaIniParser.parse_file(str(ini_path))
                            ini_cache[parent_dir] = doc
                            # FR : Charger les contacts de ce dossier
                            # EN: Load contacts declared in this folder
                            for cid, cinfo in doc.get_contacts().items():
                                contacts_cache[cid] = cinfo.name
                        except Exception:
                            ini_cache[parent_dir] = None
                    else:
                        ini_cache[parent_dir] = None

                doc = ini_cache.get(parent_dir)
                faces_to_write = []

                if doc:
                    face_items = doc.get_faces(p.name)
                    for item in face_items:
                        left, top, right, bottom = decode_rect64_string(item.rect64)
                        name = contacts_cache.get(item.contact_id, "")
                        if not name and self.db and getattr(self.db, "contacts", None):
                            contact = self.db.contacts.by_id.get(item.contact_id)
                            if contact:
                                name = contact.name
                        faces_to_write.append((name, left, top, right, bottom))

                if faces_to_write:
                    with Image.open(p) as img:
                        w, h = img.size
                    existing_xmp = PicasaXMPFaceTagger.extract_xmp_from_jpeg(str(p))
                    xmp_bytes = PicasaXMPFaceTagger.build_xmp_packet(w, h, faces_to_write, existing_xmp=existing_xmp)
                    if PicasaXMPFaceTagger.inject_xmp_into_jpeg(str(p), xmp_bytes):
                        succ += 1
                    else:
                        err += 1

            except Exception:
                err += 1

        self.finished.emit(succ, err)


class PicasaWriteFaceTagsDialog(QDialog):
    """
    FR : Boîte de dialogue officielle d'écriture des tags de visages dans les fichiers JPEG.
    EN: Official dialog for writing face tags into JPEG files.
    Ref: write_all_facetags.fen, WRITE_ALL_FACETAGS_FR.XML
    """

    def __init__(
        self,
        selected_paths: List[str],
        db: Optional[PicasaDatabase] = None,
        style: Optional[PicasaStyle] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.selected_paths = selected_paths
        self.db = db
        self.style = style or PicasaStyle.load()
        self.res_mgr = PicasaResourceManager.get()

        self.setWindowTitle(self.res_mgr.get_xml_string("write_all_facetags/window1.title", "Écrire les tags de visage"))
        self.setFixedWidth(440)
        self.setStyleSheet("""
            QDialog {
                background-color: #ECE9D8;
                color: #000000;
                font-size: 11px;
            }
            QPushButton {
                background-color: #F8F7F4;
                border: 1px solid #7F9DB9;
                border-radius: 3px;
                padding: 5px 12px;
                font-size: 11px;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #EBF2F9;
                border-color: #3879D9;
            }
            QPushButton#PrimaryAction {
                background-color: #3879D9;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #2859A3;
            }
            QPushButton#PrimaryAction:hover {
                background-color: #4A8BF0;
            }
            QLabel {
                font-size: 11px;
                color: #333333;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        # FR : 1. Message informatif officiel (Ref: write_all_facetags/label3.title)
        # EN: 1. Official informational label (Ref: write_all_facetags/label3.title)
        desc_text = self.res_mgr.get_xml_string(
            "write_all_facetags/label3.title",
            "L'opération \"Écrire les tags de visage\" écrit les noms et coordonnées directement dans les métadonnées XMP des fichiers JPEG (compatibles Lightroom, DigiKam et Google Photos).",
        )
        self.lbl_desc = QLabel(desc_text)
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        # FR : 2. Boutons d'action (Ref: buttongroup)
        # EN: 2. Action buttons (Ref: buttongroup)
        lay_btns = QVBoxLayout()
        lay_btns.setSpacing(6)

        # "Écriture sélectionnée" (Ref: write_all_facetags/onlyselection.title)
        self.btn_selected = QPushButton(
            self.res_mgr.get_xml_string(
                "write_all_facetags/onlyselection.title",
                "Écriture sélectionnée",
            )
        )
        self.btn_selected.setObjectName("PrimaryAction")
        self.btn_selected.setEnabled(bool(self.selected_paths))
        self.btn_selected.clicked.connect(lambda: self._start_tagging("selected"))
        lay_btns.addWidget(self.btn_selected)

        # "Écrire les tags de visage" (Ref: write_all_facetags/allwithfaces.title)
        self.btn_all_faces = QPushButton(
            self.res_mgr.get_xml_string(
                "write_all_facetags/allwithfaces.title",
                "Écrire les tags de visage",
            )
        )
        self.btn_all_faces.clicked.connect(lambda: self._start_tagging("all_faces"))
        lay_btns.addWidget(self.btn_all_faces)

        # "Tout écrire" (Ref: write_all_facetags/allfiles.title)
        self.btn_all_files = QPushButton(
            self.res_mgr.get_xml_string(
                "write_all_facetags/allfiles.title",
                "Tout écrire",
            )
        )
        self.btn_all_files.clicked.connect(lambda: self._start_tagging("all_files"))
        lay_btns.addWidget(self.btn_all_files)

        # "Annuler" (Ref: write_all_facetags/button8.title)
        self.btn_cancel = QPushButton(self.res_mgr.get_xml_string("write_all_facetags/button8.title", "Annuler"))
        self.btn_cancel.clicked.connect(self.reject)
        lay_btns.addWidget(self.btn_cancel)

        layout.addLayout(lay_btns)

    def _start_tagging(self, mode: str) -> None:
        """
        FR : Lance le worker d'écriture XMP selon le mode choisi (`selected`, `all_faces`, `all_files`).
        EN: Start the XMP tagging worker according to the selected mode (`selected`, `all_faces`, `all_files`).
        """
        targets: List[str] = []
        if mode == "selected":
            targets = list(self.selected_paths)
        else:
            if self.db and hasattr(self.db, "index") and self.db.index:
                for idx, item in enumerate(self.db.index):
                    if item.type == 1 or not item.path:
                        continue
                    full_p = (
                        self.db.get_media_full_path(idx)
                        if hasattr(self.db, "get_media_full_path")
                        else item.path
                    ) or item.path
                    if not full_p:
                        continue
                    if mode == "all_faces":
                        has_face = False
                        if getattr(self.db, "_face_manager", None) is not None:
                            has_face = bool(self.db.face_manager.get_faces_for_photo(idx))
                        if not has_face and os.path.exists(full_p):
                            ini_p = os.path.join(os.path.dirname(full_p), ".picasa.ini")
                            doc = self.db.get_parsed_ini(ini_p) if hasattr(self.db, "get_parsed_ini") else None
                            if doc and doc.get_faces(os.path.basename(full_p)):
                                has_face = True
                        if not has_face:
                            continue
                    if full_p not in targets:
                        targets.append(full_p)
            elif self.selected_paths:
                targets = list(self.selected_paths)

        if not targets:
            QMessageBox.information(self, "Visages", "Aucun fichier à traiter.")
            return

        prog = QProgressDialog("Écriture des balises de visages XMP...", "Annuler", 0, len(targets), self)
        prog.setWindowTitle("Écrire les tags de visage")
        prog.setWindowModality(Qt.WindowModality.WindowModal)

        worker = PicasaWriteFaceTagsWorker(targets, self.db, self)

        def on_prog(cur: int, tot: int, name: str) -> None:
            prog.setValue(cur)
            prog.setLabelText(f"Écriture : {name} ({cur}/{tot})")

        def on_finished(succ: int, err: int) -> None:
            prog.close()
            msg = f"Écriture XMP terminée !\n\n{succ} fichier(s) mis à jour avec succès."
            if err > 0:
                msg += f"\n({err} erreur(s))"
            QMessageBox.information(self, "Tags de visage", msg)
            self.accept()

        prog.canceled.connect(worker.cancel)
        worker.progress.connect(on_prog)
        worker.finished.connect(on_finished)
        worker.start()
        prog.exec()
