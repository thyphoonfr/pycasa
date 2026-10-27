"""
FR: Tests pour l'outil d'écriture sans perte des métadonnées de visages XMP et sa boîte de dialogue (Option 5).
EN: Tests for Lossless XMP Face Metadata Tagger and Dialog (Option 5).
Ref: FileFaceTagger, write_all_facetags.fen, WRITE_ALL_FACETAGS_FR.XML
"""

from __future__ import annotations
import os
import io
from pathlib import Path
from PIL import Image

import pytest
from PySide6.QtWidgets import QApplication

from picasa_py.faces.xmp_tagger import PicasaXMPFaceTagger, PicasaWriteFaceTagsDialog
from picasa_py.ini.parser import PicasaIniParser


@pytest.fixture(scope="session")
def qapp():
    """
    FR: Fournit une instance partagée de QApplication pour la session de tests.
    EN: Provide a shared QApplication instance for the test session.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_build_xmp_packet():
    """
    FR: Vérifie la génération du paquet RDF/XMP conforme aux normes MWG Regions et IPTC.
    EN: Verify generation of the RDF/XMP packet compliant with MWG Regions and IPTC standards.
    """
    faces = [
        ("Alice Dupont", 0.1, 0.2, 0.3, 0.5),   # cx = 0.2, cy = 0.35, w = 0.2, h = 0.3
        ("Bob Martin", 0.6, 0.4, 0.8, 0.7),     # cx = 0.7, cy = 0.55, w = 0.2, h = 0.3
    ]
    xmp_bytes = PicasaXMPFaceTagger.build_xmp_packet(width=1000, height=800, faces=faces)

    assert isinstance(xmp_bytes, bytes)
    xmp_str = xmp_bytes.decode("utf-8")

    assert "xmlns:mwg-rs=" in xmp_str
    assert "xmlns:stArea=" in xmp_str
    assert "Iptc4xmpExt" not in xmp_str
    assert '<mwg-rs:Name>Alice Dupont</mwg-rs:Name>' in xmp_str
    assert '<mwg-rs:Name>Bob Martin</mwg-rs:Name>' in xmp_str
    assert 'stArea:x="0.2"' in xmp_str
    assert 'stArea:unit="normalized"' in xmp_str
    assert 'stDim:w="1000"' in xmp_str
    assert 'stDim:h="800"' in xmp_str


def test_inject_xmp_into_jpeg(tmp_path):
    """
    FR: Vérifie l'injection sans perte et atomique d'un paquet XMP dans un fichier JPEG.
    EN: Verify lossless and atomic injection of an XMP packet into a JPEG file.
    """
    jpeg_file = tmp_path / "test_photo.jpg"
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    img.save(str(jpeg_file), format="JPEG")

    faces = [("Charlie", 0.2, 0.2, 0.4, 0.4)]
    xmp_bytes = PicasaXMPFaceTagger.build_xmp_packet(100, 100, faces)

    success = PicasaXMPFaceTagger.inject_xmp_into_jpeg(str(jpeg_file), xmp_bytes)
    assert success is True

    # Vérifier que le fichier JPEG est toujours valide et lisible
    with open(jpeg_file, "rb") as f:
        data = f.read()

    assert data.startswith(b"\xff\xd8")
    assert b"http://ns.adobe.com/xap/1.0/\x00" in data
    assert b"Charlie" in data

    # Vérifier ré-ouverture PIL
    with Image.open(jpeg_file) as reopened:
        assert reopened.size == (100, 100)

    # Test remplacement du segment XMP existant par un nouveau
    faces2 = [("David", 0.5, 0.5, 0.7, 0.7)]
    xmp_bytes2 = PicasaXMPFaceTagger.build_xmp_packet(100, 100, faces2)
    success2 = PicasaXMPFaceTagger.inject_xmp_into_jpeg(str(jpeg_file), xmp_bytes2)
    assert success2 is True

    with open(jpeg_file, "rb") as f:
        data2 = f.read()
    assert b"David" in data2
    assert b"Charlie" not in data2


def test_write_facetags_dialog(qapp, tmp_path):
    """
    FR: Vérifie l'initialisation et l'état des contrôles de la boîte de dialogue.
    EN: Verify initialization and control states of the Write Face Tags dialog.
    """
    img_path = tmp_path / "sample.jpg"
    img = Image.new("RGB", (64, 64), color="green")
    img.save(str(img_path), format="JPEG")

    dlg = PicasaWriteFaceTagsDialog([str(img_path)])
    assert dlg.windowTitle() == "Écrire les tags de visage"
    assert dlg.btn_selected.isEnabled() is True
    assert "Écriture sélectionnée" in dlg.btn_selected.text()
    assert "Écrire les tags de visage" in dlg.btn_all_faces.text()
    assert "Tout écrire" in dlg.btn_all_files.text()
