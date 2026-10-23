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
    def write_atomic(cls, path: str, doc: PicasaIniDocument) -> None:
        """
        FR: Écrit le fichier INI de manière atomique (fichier temporaire puis renommage).
        Gère les attributs Windows (FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_READONLY) uniquement
        sous sys.platform == 'win32' pour éviter PermissionError [Errno 13] / [WinError 5],
        et fonctionne nativement sur Linux et macOS (où le préfixe '.' rend déjà .picasa.ini caché).
        EN: Atomically writes the INI file (temporary file followed by rename).
        Handles Windows file attributes (FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_READONLY) only
        under sys.platform == 'win32' to prevent PermissionError [Errno 13] / [WinError 5],
        and works natively on Linux and macOS (where a leading '.' already hides .picasa.ini).
        Ref: FUN_0068ac80 (sauvegarde sécurisée évitant la corruption en cas d'interruption).
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
                    # FR: Si le fichier a le bit READONLY (0x01), le retirer temporairement
                    # EN: If the file has the READONLY bit (0x01), clear it temporarily
                    if attrs != -1 and (attrs & 0x01):
                        kernel32.SetFileAttributesW(abs_path, attrs & ~0x01)
            except Exception:
                kernel32 = None

        cls.mark_internal_write(dir_name)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".picasa_", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())

            # FR: Remplacement atomique / EN: Atomic replacement
            os.replace(tmp_path, abs_path)

            # FR: Rétablir ou appliquer l'attribut HIDDEN (0x02) sous Windows si le fichier commence par '.'
            # EN: Restore or apply the HIDDEN attribute (0x02) on Windows if the filename starts with '.'
            is_dot_ini = os.path.basename(abs_path).startswith(".")
            if kernel32 is not None and sys.platform == "win32" and is_dot_ini:
                attrs = kernel32.GetFileAttributesW(abs_path)
                if attrs != -1:
                    kernel32.SetFileAttributesW(abs_path, attrs | 0x02)
            cls.mark_internal_write(dir_name)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            # FR: Repli direct via r+b si os.replace échoue pour cause de verrouillage / attributs
            # EN: Direct r+b fallback if os.replace fails due to locking or file attributes
            try:
                if os.path.exists(abs_path):
                    with open(abs_path, "r+b") as f:
                        f.seek(0)
                        f.write(data)
                        f.truncate()
                    is_dot_ini = os.path.basename(abs_path).startswith(".")
                    if kernel32 is not None and sys.platform == "win32" and is_dot_ini:
                        attrs = kernel32.GetFileAttributesW(abs_path)
                        if attrs != -1:
                            kernel32.SetFileAttributesW(abs_path, attrs | 0x02)
                    cls.mark_internal_write(dir_name)
                    return
            except Exception:
                pass
            raise

    @classmethod
    def write_file(cls, path: str, doc: PicasaIniDocument) -> None:
        """
        FR: Alias de `write_atomic` pour l'écriture atomique d'un document `.picasa.ini`.
        EN: Alias for `write_atomic` to atomically write a `.picasa.ini` document.
        Ref: picasa3.exe @ 0x0068AC80
        """
        cls.write_atomic(path, doc)

