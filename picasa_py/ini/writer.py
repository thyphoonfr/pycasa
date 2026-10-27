"""
FR: Writer dédié pour les fichiers .picasa.ini et Picasa.ini.
EN: Dedicated writer for .picasa.ini and Picasa.ini files.

Traçabilité Ghidra / Ghidra Traceability:
- FUN_0068ac80 @ 0x0068AC80 - 0x0068C412 (Sérialisation canonique CRLF, UTF-8 sans BOM / Canonical CRLF, UTF-8 without BOM serialization)
- Écriture atomique et renommage / Atomic write and rename
"""

from __future__ import annotations
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from picasa_py.ini.parser import PicasaIniDocument


# Ref: picasa3.exe @ 0x0068AC80, 0x00456A15, 0x0068BABA
class PicasaIniWriter:
    """
    FR: Sérialiseur fidèle pour les fichiers INI de Picasa 3.
    Assure un round-trip octet pour octet et une écriture atomique multi-plateforme sur disque.
    EN: Faithful serializer for Picasa 3 INI files.
    Guarantees byte-for-byte round-trip fidelity and cross-platform atomic disk writes.
    """

    _recent_internal_writes: Dict[str, float] = {}
    _write_lock: threading.Lock = threading.Lock()

    @classmethod
    def _normalize_folder_key(cls, file_or_dir_path: Union[str, Path]) -> str:
        """
        FR: Normalise un chemin de fichier `.picasa.ini` ou de dossier en clé canonique de répertoire.
        EN: Normalizes a `.picasa.ini` file path or folder path into a canonical directory key.
        """
        raw_str = str(file_or_dir_path)
        abs_path = os.path.abspath(raw_str)
        bname = os.path.basename(abs_path).lower()
        if (
            bname in (".picasa.ini", "picasa.ini")
            or bname.endswith((".ini", ".tmp"))
            or (os.path.exists(abs_path) and os.path.isfile(abs_path))
        ):
            folder = os.path.dirname(abs_path)
        else:
            folder = abs_path
        return os.path.normcase(os.path.normpath(str(folder)))

    @classmethod
    def mark_internal_write(cls, file_or_dir_path: Union[str, Path]) -> None:
        """
        FR: Enregistre l'horodatage monotone d'une écriture INI interne pour inhiber la boucle
        d'auto-déclenchement de `PicasaFolderWatcher`.
        EN: Records the monotonic timestamp of an internal INI write to suppress the
        self-triggering loop in `PicasaFolderWatcher`.
        Ref: picasa3.exe @ 0x00456A15, 0x0068BABA
        """
        if not file_or_dir_path:
            return
        now = time.monotonic()
        folder_key = cls._normalize_folder_key(file_or_dir_path)
        raw_str = str(file_or_dir_path)
        bname = os.path.basename(raw_str).lower()
        raw_folder = os.path.dirname(raw_str) if (bname.endswith((".ini", ".tmp")) and os.path.dirname(raw_str)) else raw_str
        raw_key = os.path.normcase(os.path.normpath(str(raw_folder)))
        with cls._write_lock:
            if len(cls._recent_internal_writes) > 512:
                cutoff = now - 60.0
                cls._recent_internal_writes = {
                    k: ts for k, ts in cls._recent_internal_writes.items() if ts >= cutoff
                }
            cls._recent_internal_writes[folder_key] = now
            cls._recent_internal_writes[raw_key] = now

    @classmethod
    def is_recent_internal_write(cls, folder_path: Union[str, Path], window_s: float = 2.0) -> bool:
        """
        FR: Indique si le dossier spécifié a fait l'objet d'une écriture `.picasa.ini` interne
        au cours des `window_s` dernières secondes.
        EN: Returns whether the specified folder had an internal `.picasa.ini` write
        within the last `window_s` seconds.
        Ref: picasa3.exe @ 0x00456A15, 0x0068BABA
        """
        if not folder_path:
            return False
        now = time.monotonic()
        folder_key = cls._normalize_folder_key(folder_path)
        raw_key = os.path.normcase(os.path.normpath(str(folder_path)))
        with cls._write_lock:
            ts = cls._recent_internal_writes.get(folder_key)
            if ts is not None and (now - ts) <= window_s:
                return True
            ts_raw = cls._recent_internal_writes.get(raw_key)
            if ts_raw is not None and (now - ts_raw) <= window_s:
                return True
        return False

    @staticmethod
    def to_bytes(doc: PicasaIniDocument) -> bytes:
        """
        FR: Sérialise un PicasaIniDocument en octets UTF-8 (avec ou sans BOM selon l'original).
        Injecte `[encoding]\\r\\nutf8=1\\r\\n` en tête lorsque le contenu comporte des caractères
        non-ASCII (ou que l'encodage UTF-8 est explicitement requis) et qu'aucune section `[encoding]`
        n'est présente, conformément à `FUN_0068ac80` (`0x0068ad5a`).
        EN: Serializes a PicasaIniDocument into UTF-8 bytes (preserving original BOM state).
        Prepends `[encoding]\\r\\nutf8=1\\r\\n` when the content contains non-ASCII characters
        (or UTF-8 encoding is explicitly requested) and no `[encoding]` section is present,
        matching `FUN_0068ac80` (`0x0068ad5a`).
        """
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
        has_non_ascii = any(ord(c) > 127 for c in full_str)
        has_encoding_sec = doc.get_section("encoding") is not None
        preserve_untagged = getattr(doc, "_untagged_utf8_preserved", False) and not doc.is_modified()
        explicit_utf8 = getattr(doc, "_encoding_explicit", False) and getattr(doc, "encoding", "utf-8").lower() in ("utf-8", "utf8")

        # Ref: picasa3.exe @ 0x0068AD5A ("[encoding]\r\nutf8=1\r\n")
        if not has_encoding_sec and not doc.has_bom and not preserve_untagged and (has_non_ascii or explicit_utf8):
            full_str = "[encoding]\r\nutf8=1\r\n" + full_str

        data = full_str.encode("utf-8")

        if doc.has_bom:
            data = b"\xef\xbb\xbf" + data

        return data

    @classmethod
    def write_atomic(cls, path: str, doc: PicasaIniDocument) -> bool:
        """
        FR: Écrit le fichier `.picasa.ini` directement sur place (`OPEN_ALWAYS`, `SetFilePointer(0)`,
        `WriteFile`, `SetEndOfFile`) sans fichier temporaire `.tmp`, puis applique `attrs | 0x02`
        (`FILE_ATTRIBUTE_HIDDEN`) si le bit 0x02 n'est pas déjà positionné.
        Si le fichier existant possède `FILE_ATTRIBUTE_READONLY` (0x01), l'écriture est abandonnée
        sans modifier le fichier (retourne False), exactement comme `picasa3.exe`.
        EN: Writes the `.picasa.ini` file directly in-place (`OPEN_ALWAYS`, `SetFilePointer(0)`,
        `WriteFile`, `SetEndOfFile`) without a `.tmp` file, then sets `attrs | 0x02`
        (`FILE_ATTRIBUTE_HIDDEN`) if bit 0x02 is not already set.
        If the existing file has `FILE_ATTRIBUTE_READONLY` (0x01), writing is aborted without
        modifying the file (returns False), matching `picasa3.exe`.
        Ref: picasa3.exe @ 0x0099B440..0x0099B58C, 0x0099DB60, 0x009BD390, 0x009BD640, 0x009BED3F..0x009BEDB3
        """
        data = cls.to_bytes(doc)
        abs_path = os.path.abspath(path)
        dir_name = os.path.dirname(abs_path)
        os.makedirs(dir_name, exist_ok=True)

        kernel32 = None
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                if os.path.exists(abs_path):
                    attrs = kernel32.GetFileAttributesW(abs_path)
                    # Ref: picasa3.exe @ 0x0099DB60 / 0x009BD706 — ne jamais supprimer FILE_ATTRIBUTE_READONLY (0x01).
                    if attrs != -1 and (attrs & 0x01):
                        return False
            except Exception:
                kernel32 = None
        else:
            if os.path.exists(abs_path) and not os.access(abs_path, os.W_OK):
                return False

        cls.mark_internal_write(dir_name)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
        try:
            fd = os.open(abs_path, flags, 0o666)
        except PermissionError:
            return False

        try:
            with os.fdopen(fd, "r+b") as f:
                # Ref: picasa3.exe @ 0x009BED3F (SetFilePointer(0)), 0x009BED63 (WriteFile), 0x009BEDB3 (SetEndOfFile)
                f.seek(0)
                f.write(data)
                f.truncate()
                f.flush()
        finally:
            cls.mark_internal_write(dir_name)

        # Ref: picasa3.exe @ 0x0099B578..0x0099B58C :
        # GetFileAttributesW -> test bl, 2 -> jnz -> or eax, 2 -> SetFileAttributesW
        is_dot_ini = os.path.basename(abs_path).startswith(".")
        if kernel32 is not None and sys.platform == "win32" and is_dot_ini:
            try:
                attrs = kernel32.GetFileAttributesW(abs_path)
                if attrs != -1 and (attrs & 0x02) == 0:
                    kernel32.SetFileAttributesW(abs_path, attrs | 0x02)
            except Exception:
                pass
        return True

    @classmethod
    def write_file(cls, path: str, doc: PicasaIniDocument) -> bool:
        """
        FR: Écrit un document `.picasa.ini` sur place conformément à `picasa3.exe`.
        EN: Writes a `.picasa.ini` document in-place matching `picasa3.exe`.
        Ref: picasa3.exe @ 0x0099B440, 0x009BD390
        """
        return cls.write_atomic(path, doc)

