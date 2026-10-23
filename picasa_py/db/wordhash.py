"""
FR: Module de lecture et d'écriture du fichier wordhash.dat (Index de recherche inversé par mot-clé).
EN: Module for reading and writing the wordhash.dat file (Inverted keyword search index).

Traçabilité Ghidra / Ghidra Traceability:
- Magic number : 0x3FCCCCCD (1.6f float32 à l'adresse globale _DAT_00d678e0)
- Écriture globale / Global write : picasa3.exe @ 0x004DB4F0 (FUN_004db4f0)
- Lecture globale / Global read : picasa3.exe @ 0x004DB720 (FUN_004db720)
- Écriture du pool de chaînes / String pool write : picasa3.exe @ 0x00A61700 (FUN_00a61700)
- Lecture du pool de chaînes / String pool read : picasa3.exe @ 0x00A617B0 (FUN_00a617b0)
- Écriture de la table d'index / Index table write : picasa3.exe @ 0x00704500 (FUN_00704500)
- Lecture de la table d'index / Index table read : picasa3.exe @ 0x007046E0 (FUN_007046e0)
- Écriture de vecteur colonne / Column vector write : picasa3.exe @ 0x0099C1E0 (FUN_0099c1e0)
"""

from __future__ import annotations
import bisect
import os
from pathlib import Path
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union


WORDHASH_MAGIC = 0x3FCCCCCD  # 1.6f en IEEE 754 float32 / 1.6f in IEEE 754 float32
HEADER_STRUCT = struct.Struct("<II")
POOL_HEADER_STRUCT = struct.Struct("<III")


def picasa_word_hash(word: str) -> int:
    """
    FR: Calcule le hachage polynomial 32 bits insensible à la casse d'un mot Picasa (`h = h * 0x101 + tolower(c)`).
    EN: Computes Picasa's case-insensitive 32-bit polynomial word hash (`h = h * 0x101 + tolower(c)`).
    Ref: picasa3.exe @ 0x00A43E20, 0x004D9AA0
    """
    h = 0
    for ch in word.lower().encode("utf-8", errors="surrogateescape"):
        h = (h * 0x101 + ch) & 0xFFFFFFFF
    return h


hash_word = picasa_word_hash


@dataclass
class WordEntry:
    """
    FR: Entrée d'index inversé associant un mot du pool de chaînes à la liste des IDs d'images.
    EN: Inverted index entry mapping a word from the string pool to a list of image IDs.
    """
    word: str
    str_offset: int
    image_ids: List[int]


WordHashEntry = WordEntry


class WordHashFile:
    """
    FR: Représente le fichier wordhash.dat complet.
    Permet la lecture, la recherche et la ré-écriture bit-exacte.
    EN: Represents the complete wordhash.dat file.
    Supports reading, prefix search, and bit-exact rewriting.
    """

    hash_word = staticmethod(picasa_word_hash)

    def __init__(
        self,
        magic: int = WORDHASH_MAGIC,
        max_doc_id: int = 0,
        chunk_size: int = 65536,
        used_bytes: int | None = None,
        pool_bytes: bytes | None = None,
        entries: List[WordEntry] | None = None,
        version: int | None = None,
        dirty: bool = False,
    ):
        """
        FR: Initialise l'index inversé wordhash.dat en mémoire avec son flag d'état modifié (`dirty`)
        et son dictionnaire interne `_word_map` en O(1).
        EN: Initializes the in-memory wordhash.dat inverted index with its modified state flag (`dirty`)
        and its O(1) internal `_word_map` dictionary.
        Ref: picasa3.exe @ 0x004DB4F0 (FUN_004db4f0), 0x004DB720, 0x004DC110
        """
        self.magic = magic
        self.max_doc_id = version if version is not None else max_doc_id
        self.chunk_size = chunk_size
        self.used_bytes = used_bytes
        self._raw_pool_bytes: bytes = pool_bytes if pool_bytes is not None else b""
        self._pool_buf: Optional[bytearray] = None
        self.entries: List[WordEntry] = entries if entries is not None else []
        self._word_map: Dict[str, WordEntry] = {}
        for e in self.entries:
            self._word_map[e.word] = e
            self._word_map.setdefault(e.word.lower(), e)
        self.words: Dict[str, List[int]] = {e.word: e.image_ids for e in self.entries}
        self.dirty: bool = dirty

    @property
    def pool_bytes(self) -> bytes:
        """
        FR: Retourne les octets bruts du pool de chaînes (matérialise `_pool_buf` à la demande).
        EN: Returns the raw string pool bytes (lazily materializing `_pool_buf` on demand).
        """
        if self._pool_buf is not None:
            self._raw_pool_bytes = bytes(self._pool_buf)
            self._pool_buf = None
        return self._raw_pool_bytes

    @pool_bytes.setter
    def pool_bytes(self, val: bytes) -> None:
        self._raw_pool_bytes = bytes(val)
        self._pool_buf = None

    def _ensure_pool_buf(self) -> bytearray:
        """
        FR: Initialise le buffer de chaînes mutable `_pool_buf` une seule fois pour des ajouts en O(1) amorti.
        EN: Initializes the mutable string buffer `_pool_buf` once for amortized O(1) appends.
        """
        if self._pool_buf is None:
            raw = self._raw_pool_bytes
            if self.used_bytes is not None:
                self._pool_buf = bytearray(raw[: self.used_bytes])
            elif self.entries:
                max_end = 0
                for e in self.entries:
                    end_pos = raw.find(b"\x00", e.str_offset)
                    if end_pos != -1:
                        max_end = max(max_end, end_pos + 1)
                self._pool_buf = bytearray(raw[:max_end])
            else:
                self._pool_buf = bytearray(raw)
        return self._pool_buf

    @property
    def version(self) -> int:
        """
        FR: Borne supérieure des identifiants d'enregistrements (`max(record_id) + 1`, offset `0x04`).
        EN: Upper bound of record identifiers (`max(record_id) + 1`, offset `0x04`).
        Ref: picasa3.exe @ 0x004DB4F0 (FUN_004db4f0)
        """
        return self.max_doc_id

    @version.setter
    def version(self, val: int) -> None:
        """
        FR: Définit la borne supérieure `max_doc_id` (`version`) dans l'en-tête.
        EN: Sets the upper bound `max_doc_id` (`version`) in the header.
        """
        self.max_doc_id = int(val)
        self.dirty = True

    def _sync_words_to_entries(self) -> None:
        """
        FR: Synchronise le dictionnaire `self.words` vers `self.entries`, `self._word_map` et `self.pool_bytes`
        si `self.words` a été modifié directement.
        EN: Synchronizes the `self.words` dictionary into `self.entries`, `self._word_map`, and `self.pool_bytes`
        if `self.words` was mutated directly.
        """
        if len(self.words) == len(self.entries):
            in_sync = True
            for w, ids in self.words.items():
                ent = self._word_map.get(w)
                if ent is None or ent.word != w or (ids is not ent.image_ids and ids != ent.image_ids):
                    in_sync = False
                    break
            if in_sync:
                return

        existing_by_word = {e.word: e for e in self.entries}
        raw_pool = self._ensure_pool_buf()

        new_entries: List[WordEntry] = []
        new_word_map: Dict[str, WordEntry] = {}
        for w, ids in self.words.items():
            clean_ids = sorted(list(set(int(x) for x in ids)))
            if clean_ids:
                self.max_doc_id = max(self.max_doc_id, max(clean_ids) + 1)
            if w in existing_by_word:
                ent = existing_by_word[w]
                ent.image_ids = clean_ids
                self.words[w] = ent.image_ids
                new_entries.append(ent)
            else:
                str_off = len(raw_pool)
                b_word = w.encode("utf-8", errors="surrogateescape") + b"\x00"
                raw_pool.extend(b_word)
                ent = WordEntry(word=w, str_offset=str_off, image_ids=clean_ids)
                self.words[w] = ent.image_ids
                new_entries.append(ent)
            new_word_map[ent.word] = ent
            new_word_map.setdefault(ent.word.lower(), ent)

        self.entries = new_entries
        self._word_map = new_word_map
        self.used_bytes = len(raw_pool)
        self.dirty = True

    def search(self, query: str) -> List[int]:
        """
        FR: Recherche des identifiants d'images par mot-clé (intersection multi-termes avec support des préfixes).
        EN: Searches image IDs by keyword (multi-term intersection with prefix matching support).
        Ref: picasa3.exe @ 0x007046E0 (FUN_007046e0 / wordhash index search)
        """
        self._sync_words_to_entries()
        tokens = [t.strip().lower() for t in query.split() if t.strip()]
        if not tokens:
            return []

        token_matches: List[set[int]] = []
        for token in tokens:
            matched_ids: set[int] = set()
            for entry in self.entries:
                if entry.word.lower().startswith(token):
                    matched_ids.update(entry.image_ids)
            token_matches.append(matched_ids)

        if not token_matches:
            return []

        common_ids = token_matches[0]
        for s in token_matches[1:]:
            common_ids = common_ids.intersection(s)

        return sorted(list(common_ids))

    @classmethod
    def create_from_dict(
        cls,
        index_dict: Dict[str, List[int]],
        max_doc_id: int = 0,
        chunk_size: int = 65536,
    ) -> WordHashFile:
        """
        FR: Construit une instance WordHashFile à partir d'un dictionnaire {mot: [id_images]}.
        EN: Builds a WordHashFile instance from a {word: [image_ids]} dictionary.
        Ref: picasa3.exe @ 0x004DB4F0 / 0x00A61700 / 0x00704500
        """
        pool_parts: List[bytes] = []
        entries: List[WordEntry] = []
        current_offset = 0

        calculated_max_id = max_doc_id
        for word, img_ids in index_dict.items():
            b_word = word.encode("utf-8") + b"\x00"
            unique_ids = sorted(list(set(img_ids)))
            if unique_ids:
                calculated_max_id = max(calculated_max_id, max(unique_ids) + 1)
            entries.append(WordEntry(word=word, str_offset=current_offset, image_ids=unique_ids))
            pool_parts.append(b_word)
            current_offset += len(b_word)

        pool_bytes = b"".join(pool_parts)
        return cls(
            magic=WORDHASH_MAGIC,
            max_doc_id=calculated_max_id,
            chunk_size=chunk_size,
            used_bytes=len(pool_bytes),
            pool_bytes=pool_bytes,
            entries=entries,
        )

    @classmethod
    # Ref: picasa3.exe @ 0x004DB720 / 0x007046E0
    def from_bytes(cls, data: bytes) -> WordHashFile:
        """
        FR: Désérialise wordhash.dat depuis un buffer d'octets.
        EN: Deserializes wordhash.dat from a byte buffer.
        """
        if len(data) < 20:
            raise ValueError(f"Fichier wordhash.dat trop court : {len(data)} octets (min 20)")

        magic, max_doc_id = HEADER_STRUCT.unpack_from(data, 0)
        if magic != WORDHASH_MAGIC:
            raise ValueError(f"Magic wordhash invalide : 0x{magic:08X} (attendu 0x{WORDHASH_MAGIC:08X})")

        pos = 8
        chunk_count, chunk_size, used_bytes = POOL_HEADER_STRUCT.unpack_from(data, pos)
        pos += 12

        pool_len = chunk_count * chunk_size
        if pos + pool_len > len(data):
            raise ValueError(f"Pool de chaînes wordhash tronqué : {pool_len} octets attendus")

        pool_bytes = data[pos : pos + pool_len]
        pos += pool_len

        if pos + 4 > len(data):
            raise ValueError("Nombre d'entrées wordhash manquant")

        word_count = struct.unpack_from("<I", data, pos)[0]
        pos += 4

        entries: List[WordEntry] = []
        for i in range(word_count):
            if pos + 8 > len(data):
                raise ValueError(f"Entrée wordhash {i} tronquée")
            str_off = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            count = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            if pos + count * 4 > len(data):
                raise ValueError(f"Vecteur d'images de l'entrée {i} tronqué : {count} IDs attendus")
            items = list(struct.unpack_from(f"<{count}I", data, pos))
            pos += count * 4

            null_idx = pool_bytes.find(b"\x00", str_off)
            word = pool_bytes[str_off:null_idx].decode("utf-8", errors="surrogateescape")
            entries.append(WordEntry(word=word, str_offset=str_off, image_ids=items))

        if pos != len(data):
            raise ValueError(f"Octets excédentaires à la fin de wordhash.dat : {len(data) - pos} octets")

        return cls(
            magic=magic,
            max_doc_id=max_doc_id,
            chunk_size=chunk_size,
            used_bytes=used_bytes,
            pool_bytes=pool_bytes,
            entries=entries,
        )

    # Ref: picasa3.exe @ 0x004DB4F0 / 0x00704500
    def to_bytes(self) -> bytes:
        """
        FR: Sérialise wordhash.dat au format binaire exact de Picasa 3.
        Calcule la borne supérieure `max(record_id) + 1` (`version_to_write`) conformément à `FUN_004db4f0`.
        EN: Serializes wordhash.dat into the exact Picasa 3 binary format.
        Computes the upper bound `max(record_id) + 1` (`version_to_write`) in accordance with `FUN_004db4f0`.
        """
        self._sync_words_to_entries()
        chunk_size = self.chunk_size if self.chunk_size > 0 else 65536
        # FR: Si pool_bytes est fourni, on calcule le nombre de chunks / EN: Compute chunk count from pool_bytes length
        pool_len = len(self.pool_bytes)
        chunk_count = (pool_len + chunk_size - 1) // chunk_size if pool_len > 0 else 1
        total_pool_alloc = chunk_count * chunk_size
        padded_pool = self.pool_bytes.ljust(total_pool_alloc, b"\x00")

        # Calcul des used_bytes (Ref: picasa3.exe @ 0x00A61700 : taille effective du pool de chaînes)
        if self.used_bytes is not None:
            used_bytes = self.used_bytes
        else:
            used_bytes = len(self.pool_bytes)

        max_rec_plus_1 = 0
        for entry in self.entries:
            if entry.image_ids:
                max_rec_plus_1 = max(max_rec_plus_1, max(entry.image_ids) + 1)
        version_to_write = max(self.max_doc_id, max_rec_plus_1)
        self.max_doc_id = version_to_write

        parts: List[bytes] = [
            HEADER_STRUCT.pack(self.magic, version_to_write),
            POOL_HEADER_STRUCT.pack(chunk_count, chunk_size, used_bytes),
            padded_pool,
            struct.pack("<I", len(self.entries)),
        ]

        for entry in self.entries:
            count = len(entry.image_ids)
            parts.append(struct.pack(f"<II{count}I", entry.str_offset, count, *entry.image_ids))

        return b"".join(parts)

    def add_word(self, word: str, record_id: int) -> None:
        """
        FR: Ajoute en O(1) un mot associé à un `record_id` via `self._word_map` et met à jour
        la borne `version` (`max_doc_id = max(version, record_id + 1)`).
        EN: Adds in O(1) a word associated with a `record_id` via `self._word_map` and updates
        the `version` bound (`max_doc_id = max(version, record_id + 1)`).
        Ref: picasa3.exe @ 0x004D9AA0 / 0x004DB4F0 / 0x004DB720 / 0x004DC110
        """
        if record_id < 0:
            return
        if record_id + 1 > self.max_doc_id:
            self.max_doc_id = record_id + 1
            self.dirty = True
        self.add_document_words(record_id, [word])

    def add_document_words(self, doc_id: int, words: List[str]) -> None:
        """
        FR: Ajoute ou met à jour en O(1) par mot les mots associés à un `doc_id` dans l'index inversé.
        EN: Adds or updates in O(1) per word the words associated with a `doc_id` in the inverted index.
        Ref: picasa3.exe @ 0x004D9AA0 / 0x00704500 / 0x004DB720 / 0x004DC110
        """
        if doc_id < 0:
            return
        if len(self.words) != len(self.entries):
            self._sync_words_to_entries()
        if doc_id + 1 > self.max_doc_id:
            self.max_doc_id = doc_id + 1
            self.dirty = True

        for w in words:
            clean_w = w.strip().lower()
            if not clean_w:
                continue
            existing = self._word_map.get(clean_w)
            if existing is not None:
                ids = existing.image_ids
                if not ids or ids[-1] < doc_id:
                    ids.append(doc_id)
                    self.dirty = True
                else:
                    pos = bisect.bisect_left(ids, doc_id)
                    if pos >= len(ids) or ids[pos] != doc_id:
                        ids.insert(pos, doc_id)
                        self.dirty = True
                self.words[existing.word] = ids
            else:
                raw_pool = self._ensure_pool_buf()
                str_off = len(raw_pool)
                b_word = clean_w.encode("utf-8", errors="surrogateescape") + b"\x00"
                raw_pool.extend(b_word)
                self.used_bytes = len(raw_pool)
                new_entry = WordEntry(word=clean_w, str_offset=str_off, image_ids=[doc_id])
                self.entries.append(new_entry)
                self._word_map[clean_w] = new_entry
                self.words[clean_w] = new_entry.image_ids
                self.dirty = True

    def write(self, path: Union[str, Path]) -> None:
        """
        FR: Écrit `wordhash.dat` sur disque au format binaire exact de Picasa 3.
        EN: Writes `wordhash.dat` to disk in the exact Picasa 3 binary format.
        Ref: picasa3.exe @ 0x004DB4F0 (FUN_004db4f0)
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.to_bytes())
        self.dirty = False

    @classmethod
    def read(cls, path: Union[str, Path]) -> WordHashFile:
        """
        FR: Lit et désérialise un fichier `wordhash.dat` depuis le disque.
        EN: Reads and deserializes a `wordhash.dat` file from disk.
        Ref: picasa3.exe @ 0x004DB720 (FUN_004db720)
        """
        return cls.from_bytes(Path(path).read_bytes())


WordHash = WordHashFile

