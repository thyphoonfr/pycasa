"""
Writer dédié pour les fichiers .picasa.ini et Picasa.ini.

Traçabilité Ghidra :
- FUN_0068ac80 @ 0x0068AC80 - 0x0068C412 (Sérialisation canonique CRLF, UTF-8 sans BOM)
- Écriture atomique et renommage
"""

from __future__ import annotations
import os
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from picasa_py.ini.parser import PicasaIniDocument

# Ref: picasa3.exe @ 0x0068AC80
class PicasaIniWriter:
    """
    Sérialiseur fidèle pour les fichiers INI de Picasa.
    Assure un round-trip octet pour octet et une écriture atomique sur disque.
    """

    @staticmethod
    def to_bytes(doc: PicasaIniDocument) -> bytes:
        chunks: list[str] = []

        if doc.preamble:
            chunks.append(doc.preamble)

        for sec in doc.sections:
            if sec.raw_header:
                chunks.append(sec.raw_header)
            else:
                # Ref: picasa3.exe @ 0x0068B37F ("[%s]\r\n")
                chunks.append(f"[{sec.name}]\r\n")

            for entry in sec.entries:
                if entry.raw_line:
                    chunks.append(entry.raw_line)
                elif entry.key is not None:
                    # Ref: picasa3.exe @ 0x0068AC80 ("%s=%s\r\n")
                    val = entry.value if entry.value is not None else ""
                    chunks.append(f"{entry.key}={val}\r\n")

        full_str = "".join(chunks)
        data = full_str.encode("utf-8")

        if doc.has_bom:
            data = b"\xef\xbb\xbf" + data

        return data

    @classmethod
    def write_atomic(cls, path: str, doc: PicasaIniDocument) -> None:
        """
        Écrit le fichier INI de manière atomique (fichier temporaire puis renommage).
        Ref: FUN_0068ac80 (sauvegarde sécurisée évitant la corruption en cas d'interruption).
        """
        data = cls.to_bytes(doc)
        dir_name = os.path.dirname(os.path.abspath(path))
        os.makedirs(dir_name, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".picasa_", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            # Remplacement atomique
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
