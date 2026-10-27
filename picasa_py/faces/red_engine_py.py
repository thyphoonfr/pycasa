"""
FR : Implémentation Python/NumPy pure du moteur de détection et de reconnaissance faciale
`plugins\\Red.dll` + `plugins\\red.cfg` de Picasa 3 (Neven Vision / Google).
EN: Pure Python/NumPy implementation of the Picasa 3 face detection and recognition engine
`plugins\\Red.dll` + `plugins\\red.cfg` (Neven Vision / Google).

FR : Ce module reproduit en Python pur les structures binaires et algorithmes désassemblés
depuis `Red.dll` (image base `0x10000000`) et `picasa3.exe` (`0x00400000`) :
1. Désérialiseur binaire `ebs_ObjectInput` / `eio_FileInput` (`RedStream`) supportant les
   38 identifiants de classes (`0x00 0x03 <uint32 tid>`) et lisant 100 % des `2 281 657` octets
   de `plugins\\red.cfg` (6 objets racines, 0 octet résiduel).
2. Décompression 6 bits signés `ets_CompactVec` (`0x1026`, `Red.dll @ 0x10055A40` / `0x10055BE8`),
   matrices `ets_CompactMat` (`0x1027`, `Red.dll @ 0x10056BD0`) et projections affines
   `ets_CompactAlt` (`0x1028`, `Red.dll @ 0x10056FD0`).
3. Détecteur multi-échelle `vfr_VdeFaceFinder` (`0x401001`, Racine 0) et `vlf_AdvancedDetector`
   (`0x425011`, `Red.dll @ 0x1010EA20`) avec cascades `vlf_CompactRectFeature` (`0x425007`),
   `vlf_CompactQuadFeature` (`0x425009`) et `vlf_CompactWaveFeature` (`0x42500B`).
4. Localisateur de points fiduciaires `vfr_VdeLandmarker` (`0x40100D`, Racine 1) et modèle
   de forme PCA 25 nœuds `vpf_EigenShapeMap` (`0x41C016`, `Red.dll @ 0x100D49E0`).
5. Convertisseur de gabarit `vqc_Converter` (`0x423001`, Racine 4, `Red.dll @ 0x100FE170`) :
   - Bancs de filtres de Gabor `vfv_AdvancedFvc` (`0x428008` / `0x428009`) et `vfv_GaborKernel` (`0x428001`)
   - Blocs locaux `ets_CompactAlt` (`180 × 16 + 60 × 16 = 3840` dimensions)
   - Sous-projecteur orthogonal `vqc_SubProjector` (`0x423008`, `Red.dll @ 0x100FC7C0`, `(I - U U^T)(x - mean)`)
   - Quantificateur 4 bits `vqc_Quantizer` (`0x423004`, `Red.dll @ 0x100FCF60` & `0x100FCB00`,
     sélection de 2000 composantes `m18` et recherche binaire sur `2000 × 15 = 30 000` seuils `v50`)
   - Export binaire `vqc_Cue` de 1044 octets (`0x423002`, `Red.dll @ 0x10102020`).
6. Relateur et métrique de similarité `vqc_Relator` (`0x423003`, Racine 5,
   `Red.dll @ 0x101005F0`, `0x101008E0`, `0x100FF050`) :
   - Pondération `pow(w, 0.7)` renormalisée et regroupement des octets `12..249` (`group_fraction = 0.95f`)
   - Normalisation `inv_norm = 1.0 / sqrt(rawSim(cue, cue))`
   - Sigmoïde `1.0 / (1.0 + exp(-(13.5 * rawSim - 0.45)))`.
7. Post-traitement géométrique des boîtes englobantes de `picasa3.exe @ 0x0047A778..0x0047AE64`
   (`22.0`, `40.0`, `46.0`, `50.0` en vue frontale ; `6.0`, `10.0`, `12.0` au-delà de `60°` de lacet ;
   pénalité de confiance au-delà de `20°` de lacet).

EN: This module reproduces in pure Python the binary structures and algorithms disassembled
from `Red.dll` (image base `0x10000000`) and `picasa3.exe` (`0x00400000`), with optional `@njit`
(`numba`) acceleration and vectorized NumPy `sliding_window_view` layer evaluation in `float32`.

Ref: Red.dll @ 0x10001930 (REDENTRY), 0x10001400 (vt[14]), 0x10042600 (ebs_ObjectInput),
     0x10055A40 (ets_CompactVec::dot), 0x10056BD0 (ets_CompactMat::map), 0x100FC7C0 (vqc_SubProjector::eval),
     0x100FCF60 (vqc_Quantizer::eval), 0x100FE170 (vqc_Converter::convert), 0x101005F0 (vqc_Relator::init),
     0x101008E0 (vqc_Relator::relate), 0x100FF050 (vqc_Relator::rawSim), 0x10102020 (vqc_Cue::exportArr)
Ref: picasa3.exe @ 0x006CC9E0..0x006CFBC0, 0x0047A690..0x0047B010
Ghidra project: ghidra/picasa3.gpr
"""

from __future__ import annotations

import math
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple

import cv2
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

from picasa_py.db.blockfile import (
    decode_face_template_blob,
    encode_face_template_blob,
)

# FR : Support optionnel de Numba (@njit) s'il est installé sur l'environnement Python hôte.
# EN: Optional Numba (@njit) support if installed in the host Python environment.
try:
    from numba import njit  # type: ignore[import-not-found]

    _HAS_NUMBA = True
except Exception:
    _HAS_NUMBA = False

    def njit(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        """
        FR : Décorateur de repli sans opération lorsque `numba` n'est pas installé.
        EN: No-op fallback decorator when `numba` is not installed.
        """

        def _decorator(func: Any) -> Any:
            return func

        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return _decorator


def _resolve_red_cfg_path(cfg_path: Optional[str | Path] = None) -> Path:
    """
    FR : Résout le chemin vers `red.cfg` de manière portable (Windows, Linux, macOS, bundle PyInstaller
    `sys._MEIPASS`, dépôt local `ui/resources/plugins/red.cfg`, ou installation Windows Picasa 3).
    EN: Resolve the path to `red.cfg` portably across Windows, Linux, macOS, PyInstaller frozen
    bundles (`sys._MEIPASS`), local repo (`ui/resources/plugins/red.cfg`), or Windows Picasa 3.

    # Ref: picasa3.exe @ 0x00478EE0 (Initialisation du détecteur avec plugins\\red.cfg)
    """
    if cfg_path is not None:
        explicit = Path(cfg_path)
        if explicit.is_file():
            return explicit

    candidates: List[Path] = []
    env_dir = os.environ.get("PICASA3_PLUGINS_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / "red.cfg")
        candidates.append(Path(env_dir) / "Red.cfg")

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        mp = Path(meipass)
        candidates.extend(
            [
                mp / "ui" / "resources" / "plugins" / "red.cfg",
                mp / "resources" / "plugins" / "red.cfg",
                mp / "plugins" / "red.cfg",
            ]
        )

    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            repo_root / "ui" / "resources" / "plugins" / "red.cfg",
            Path("ui/resources/plugins/red.cfg"),
            Path("bin/plugins/red.cfg"),
            Path(r"C:\Program Files (x86)\Google\Picasa3\plugins\red.cfg"),
            Path(r"C:\Program Files\Google\Picasa3\plugins\red.cfg"),
        ]
    )

    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.resolve()
        except OSError:
            continue

    raise FileNotFoundError("Fichier plugins\\red.cfg introuvable / plugins\\red.cfg file not found")


# ============================================================================
# FR : 1. Désérialiseur binaire exact de `plugins\red.cfg` (Red.dll @ 0x10042600)
# EN: 1. Exact binary deserializer for `plugins\red.cfg` (Red.dll @ 0x10042600)
# ============================================================================

# Ref: Red.dll @ 0x10023730 (eio_FileInput) & 0x10042600 (ebs_ObjectInput)
class RedStream:
    """
    FR : Lecteur de flux binaire `ebs_ObjectInput` de `Red.dll`.
    Chaque objet sérialisé débute par la signature 2 octets `0x00 0x03` suivie
    de l'identifiant de classe 32 bits little-endian (`tid`).
    EN: `Red.dll` `ebs_ObjectInput` binary stream reader.
    Every serialized object starts with the 2-byte signature `0x00 0x03` followed
    by the 32-bit little-endian class type identifier (`tid`).
    """

    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    @property
    def remaining(self) -> int:
        """
        FR : Nombre d'octets restant à lire dans le flux.
        EN: Number of unread bytes remaining in the stream.
        """
        return len(self.data) - self.pos

    def u8(self) -> int:
        v = self.data[self.pos]
        self.pos += 1
        return v

    def i16(self) -> int:
        v = int(struct.unpack_from("<h", self.data, self.pos)[0])
        self.pos += 2
        return v

    def i32(self) -> int:
        v = int(struct.unpack_from("<i", self.data, self.pos)[0])
        self.pos += 4
        return v

    def u32(self) -> int:
        v = int(struct.unpack_from("<I", self.data, self.pos)[0])
        self.pos += 4
        return v

    def f32(self) -> float:
        v = float(struct.unpack_from("<f", self.data, self.pos)[0])
        self.pos += 4
        return v

    def bytes(self, n: int) -> bytes:
        b = self.data[self.pos : self.pos + n]
        self.pos += n
        return b

    def cstr(self) -> str:
        end = self.data.index(0, self.pos)
        s = self.data[self.pos : end].decode("latin1")
        self.pos = end + 1
        return s

    def hdr(self, expected: Optional[int | Sequence[int]] = None) -> int:
        sig = self.data[self.pos : self.pos + 2]
        if sig != b"\x00\x03":
            raise ValueError(f"Invalid ebs_ObjectInput signature {sig!r} at 0x{self.pos:X}")
        tid = int(struct.unpack_from("<I", self.data, self.pos + 2)[0])
        self.pos += 6
        if expected is not None:
            if isinstance(expected, (tuple, list, set)):
                if tid not in expected:
                    raise ValueError(f"Expected {expected}, got 0x{tid:X} at 0x{self.pos - 6:X}")
            elif tid != expected:
                raise ValueError(f"Expected 0x{expected:X}, got 0x{tid:X} at 0x{self.pos - 6:X}")
        return tid

    # Ref: Red.dll @ 0x10044110 (ebs_IntArr, tid=0x0A)
    def int_arr(self) -> List[int]:
        self.hdr(0xA)
        n = self.i32()
        return list(struct.unpack_from(f"<{n}i", self.bytes(n * 4)))

    # Ref: Red.dll @ 0x10044620 (ebs_ShortArr, tid=0x0D)
    def short_arr(self) -> List[int]:
        self.hdr(0xD)
        n = self.i32()
        return list(struct.unpack_from(f"<{n}h", self.bytes(n * 2)))

    # Ref: Red.dll @ 0x10043B90 (ebs_FloatArr, tid=0x07)
    def float_arr(self) -> List[float]:
        self.hdr(0x7)
        n = self.i32()
        return list(struct.unpack_from(f"<{n}f", self.bytes(n * 4)))

    # Ref: Red.dll @ 0x100447D0 (ebs_UByteArr, tid=0x0E)
    def ubyte_arr(self) -> bytes:
        self.hdr(0xE)
        n = self.i32()
        return self.bytes(n)

    # Ref: Red.dll @ 0x100353A0 (ets_FloatVec, tid=0x1014 / 0x101C)
    def float_vec(self) -> List[float]:
        tid = self.hdr((0x1014, 0x101C))
        if tid == 0x1014:
            n = self.i32()
            return list(struct.unpack_from(f"<{n}f", self.bytes(n * 4)))
        return self.float_arr()

    # Ref: Red.dll @ 0x10037120 (ets_FloatMat, tid=0x1011 / 0x101D)
    def float_mat(self) -> List[List[float]]:
        tid = self.hdr((0x1011, 0x101D))
        ver = self.i32()
        if ver not in (0, 100):
            raise ValueError(f"Unsupported float_mat version {ver}")
        if tid == 0x1011 and ver == 100:
            if self.data[self.pos : self.pos + 2] == b"\x00\x03":
                self.hdr(0x101D)
                _ = self.i32()
        n = self.i32()
        return [self.float_vec() for _ in range(n)]

    # Ref: Red.dll @ 0x10034810 (ets_Matrix3D, tid=0x100D)
    def float_3d_mat(self) -> List[float]:
        self.hdr(0x100D)
        return list(struct.unpack_from("<9f", self.bytes(36)))

    # Ref: Red.dll @ 0x10055790 (ets_CompactVec, tid=0x1026)
    def compact_vec(self) -> Tuple[int, int, int, float, bytes]:
        ver = self.i32()
        dim = self.i32()
        bits = self.i32()
        scale = self.f32()
        self.hdr(0xD)
        n = self.i32()
        raw_bytes = self.bytes(n * 2)
        return (ver, dim, bits, scale, raw_bytes)

    # Ref: Red.dll @ 0x10056820 (ets_CompactMat, tid=0x1027)
    def compact_mat(self) -> Tuple[int, int, int, List[Any], List[int]]:
        ver = self.i32()
        rows = self.i32()
        cols = self.i32()
        self.hdr(0x16)
        n = self.i32()
        vecs = [self.obj_ref() for _ in range(n)]
        ia = self.int_arr()
        return (ver, rows, cols, vecs, ia)

    # Ref: Red.dll @ 0x10056E80 (ets_CompactAlt, tid=0x1028)
    def compact_alt(self) -> Tuple[int, Tuple[int, int, int, List[Any], List[int]], List[float]]:
        ver = self.i32()
        self.hdr(0x1027)
        mat = self.compact_mat()
        vec = self.float_vec()
        return (ver, mat, vec)

    # Ref: Red.dll @ 0x10105140 (vlf_PatchSize, tid=0x425005)
    def patch_size(self) -> Tuple[int, int, int]:
        self.hdr(0x425005)
        ver = self.i32()
        return (ver, self.i32(), self.i32())

    # Ref: Red.dll @ 0x1005C1B0 (egl_Point2DCluster, tid=0x3002)
    def cluster_2d(self) -> Tuple[int, List[Tuple[float, float]]]:
        self.hdr(0x3002)
        ver = self.i32()
        n = self.i32()
        pts = [struct.unpack_from("<2f", self.bytes(8)) for _ in range(n)]
        return (ver, pts)

    # Ref: Red.dll @ 0x10045210 (ebs_StringList)
    def str_list(self) -> List[str]:
        ver = self.i32()
        if ver != 0:
            raise ValueError(f"Unsupported str_list version {ver} at 0x{self.pos - 4:X}")
        n = self.i32()
        return [self.cstr() for _ in range(n)]

    # Ref: Red.dll @ 0x100428A0 (ebs_ObjectRef, tid=0x17)
    def obj_ref(self) -> Any:
        tid = self.hdr()
        if tid == 0x17:
            has_obj = self.u8()
            if not has_obj:
                return None
            tid = self.hdr()
        reader = READERS.get(tid)
        if reader is None:
            raise KeyError(f"Unknown Red.dll class ID 0x{tid:X} at 0x{self.pos - 6:X}")
        return reader(self)


# Ref: Red.dll @ 0x10002820 (vfr_SdkBase::read)
def read_sdk_base(s: RedStream) -> Tuple[int, int, Any]:
    ver = s.i32()
    f8 = s.i32()
    if ver > 0xC8:
        fc: Any = s.u8()
    else:
        fc = (s.cstr(), s.cstr())
    return (ver, f8, fc)


# Ref: Red.dll @ 0x10068E10 (vis_SpatialNode::read, tid=0x700F)
def read_spatial_node(s: RedStream) -> Tuple[int, int, Tuple[float, float, float], int]:
    s.hdr(0x700F)
    nid = s.i32()
    flags = s.u32()
    pos = (s.f32(), s.f32(), s.f32())
    b = s.u8()
    if b == 1:
        raise ValueError("Unexpected extra spatial node payload")
    return (nid, flags, pos, b)


# Ref: Red.dll @ 0x10069440 (vis_SpatialGraph::read, tid=0x700E)
def read_spatial_graph(s: RedStream) -> Tuple[int, str, str, List[float], List[Any], List[Tuple[int, int]]]:
    ver = s.i32()
    s1 = s.cstr()
    s2 = s.cstr()
    mat = s.float_3d_mat()
    n_nodes = s.i32()
    nodes = [read_spatial_node(s) for _ in range(n_nodes)]
    n_edges = s.i32()
    edges = [(s.i32(), s.i32()) for _ in range(n_edges)]
    return (ver, s1, s2, mat, nodes, edges)


# Ref: Red.dll @ 0x1010D9C0 (vlf_ChannelArr::read, tid=0x425010)
def read_channel_arr(s: RedStream) -> Tuple[int, List[Any]]:
    s.hdr(0x425010)
    ver = s.i32()
    s.hdr(0x15)
    n = s.i32()
    items = [s.obj_ref() for _ in range(n)]
    return (ver, items)


# Ref: Red.dll @ 0x10104E90 (vlf_Sequence::read, tid=0x425004)
def read_sequence(s: RedStream) -> Tuple[int, List[Any], int]:
    ver = s.i32()
    s.hdr(0x16)
    n = s.i32()
    items = [s.obj_ref() for _ in range(n)]
    f2c = s.i32()
    return (ver, items, f2c)


# Ref: Red.dll @ 0x1010B230 (vlf_ThreshArr::read, tid=0x42500C)
def read_thresh_arr(s: RedStream) -> Tuple[int, List[float]]:
    s.hdr(0x42500C)
    ver = s.i32()
    return (ver, [s.f32() for _ in range(8)])


# Ref: Red.dll @ 0x10106810 (vlf_CompactRectFeature::read, tid=0x425007)
def read_compact_rect(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    f8 = s.i32()
    fc = s.i32()
    f10 = s.f32()
    f14 = s.f32()
    a18 = s.short_arr()
    a3c = s.float_arr()
    a60 = s.float_arr()
    th = read_thresh_arr(s)
    total = sum(a18)
    fb4 = s.i32()
    rects = s.bytes(total * 28)
    return (ver, f8, fc, f10, f14, a18, a3c, a60, th, fb4, rects)


# Ref: Red.dll @ 0x10108340 (vlf_CompactQuadFeature::read, tid=0x425009)
def read_compact_quad(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    f8 = s.i32()
    fc = s.i32()
    f10 = s.f32()
    a14 = s.short_arr()
    a38 = s.float_arr()
    a5c = s.float_arr()
    th = read_thresh_arr(s)
    total = sum(a14)
    fb0 = s.i32()
    quads = s.bytes(total * 46)
    return (ver, f8, fc, f10, a14, a38, a5c, th, fb0, quads)


# Ref: Red.dll @ 0x10109F50 (vlf_CompactWaveFeature::read, tid=0x42500B)
def read_compact_wave(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    f8 = s.i32()
    fc = s.i32()
    f10 = s.f32()
    f14 = s.i32()
    a18 = s.short_arr()
    a60 = s.float_arr()
    a3c = s.float_arr()
    a84 = s.float_arr()
    th = read_thresh_arr(s)
    total = sum(a18)
    fd8 = s.i32()
    waves = s.bytes(total * 48)
    return (ver, f8, fc, f10, f14, a18, a60, a3c, a84, th, fd8, waves)


# Ref: Red.dll @ 0x1010BB80 (vlf_AngleMap::read, tid=0x42500E)
def read_angle_map(s: RedStream) -> Tuple[int, List[float], List[float]]:
    ver = s.i32()
    a1 = s.float_arr()
    a2 = s.float_arr()
    return (ver, a1, a2)


# Ref: Red.dll @ 0x1010C310 (vlf_LocalDetector::read, tid=0x42500F)
def read_local_detector(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    ps = s.patch_size()
    f20 = s.i32()
    f24 = s.i32()
    if ver >= 0x65:
        f28 = s.i32()
        f2c = s.f32()
    else:
        f28, f2c = 0, 0.0
    f30 = s.u8()
    f34 = s.f32()
    seq = s.obj_ref()
    cl = s.cluster_2d()
    am = s.obj_ref()
    f74 = s.f32()
    f78 = s.f32()
    sl = s.str_list()
    b8c = s.u8()
    b8d = s.u8()
    ref90 = s.obj_ref()
    ref9c = s.obj_ref()
    return (ver, ps, f20, f24, f28, f2c, f30, f34, seq, cl, am, f74, f78, sl, b8c, b8d, ref90, ref9c)


# Ref: Red.dll @ 0x100E3690 (vde_LocalPoseDetector::read, tid=0x41F008)
def read_local_pose_detector(s: RedStream) -> Tuple[int, Any, Any, int, float, float]:
    ver = s.i32()
    ref8 = s.obj_ref()
    ref14 = s.obj_ref()
    b20 = s.u8()
    f24 = s.f32()
    f28 = s.f32()
    return (ver, ref8, ref14, b20, f24, f28)


# Ref: Red.dll @ 0x1010EA20 (vlf_AdvancedDetector::read, tid=0x425011)
def read_advanced_detector(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    s.hdr(0x425005)
    ws = (s.i32(), s.i32(), s.i32())
    f20 = s.f32()
    f24 = s.f32()
    f28 = s.f32()
    f2c = s.f32()
    f30 = s.i32()
    f34 = s.f32()
    f38 = s.f32()
    f3c = s.i32()
    f40 = s.i32()
    f44 = s.f32()
    b48 = s.u8()
    f4c = s.i32()
    f50 = s.f32()
    f54 = s.f32()
    f58 = s.f32()
    f5c = s.f32()
    b60 = s.u8()
    ref64 = s.obj_ref()
    f70 = s.i32()
    f74 = s.i32()
    ch1 = read_channel_arr(s)
    ch2 = read_channel_arr(s)
    ref1e8 = s.obj_ref()
    ref1f4 = s.obj_ref()
    return (
        ver, ws, f20, f24, f28, f2c, f30, f34, f38, f3c, f40, f44,
        b48, f4c, f50, f54, f58, f5c, b60, ref64, f70, f74, ch1, ch2, ref1e8, ref1f4
    )


# Ref: Red.dll @ 0x100041C0 (vfr_VdeFaceFinder::read, tid=0x401001)
def read_vde_face_finder(s: RedStream) -> Tuple[Any, ...]:
    base = read_sdk_base(s)
    ver = s.i32()
    ref = s.obj_ref()
    b3c = s.u8()
    f40 = s.f32()
    f44 = s.f32()
    f48 = s.i32()
    b4c = s.u8()
    s.hdr(0x101A)
    mat101a = [s.f32() for _ in range(4)]
    return (base, ver, ref, b3c, f40, f44, f48, b4c, mat101a)


# Ref: Red.dll @ 0x100E2B50 (vde_LocalDetectorSeq::read, tid=0x41F006)
def read_local_detector_seq(s: RedStream) -> Tuple[int, List[Any]]:
    ver = s.i32()
    s.hdr(0x15)
    n = s.i32()
    return (ver, [s.obj_ref() for _ in range(n)])


# Ref: Red.dll @ 0x100E3120 (vde_LocalDetectorPrlArr::read, tid=0x41F007)
def read_local_detector_prl_arr(s: RedStream) -> Tuple[int, Any]:
    ver = s.i32()
    ref = s.obj_ref()
    return (ver, ref)


# Ref: Red.dll @ 0x100D49E0 (vpf_EigenShapeMap::read, tid=0x41C016)
def read_eigen_shape_map(s: RedStream) -> Tuple[int, Any, List[float], List[List[float]], int]:
    ver = s.i32()
    s.hdr(0x700E)
    sg = read_spatial_graph(s)
    vec_f8 = s.float_vec()
    mat_108 = s.float_mat()
    f12c = s.i32()
    return (ver, sg, vec_f8, mat_108, f12c)


# Ref: Red.dll @ 0x10006E80 (vfr_VdeLandmarker::read, tid=0x40100D)
def read_vde_landmarker(s: RedStream) -> Tuple[Any, ...]:
    base = read_sdk_base(s)
    ver = s.i32()
    ref44 = s.obj_ref()
    ref50 = s.obj_ref() if ver >= 0x68 else None
    ref5c = s.obj_ref()
    b68 = s.u8() if ver >= 0x69 else 0
    f6c = s.f32() if ver >= 0x65 else 0.0
    b70 = s.u8() if ver >= 0x67 else 0
    return (base, ver, ref44, ref50, ref5c, b68, f6c, b70)


# Ref: Red.dll @ 0x100CA810 (vrd_HistogramModel::read, tid=0x41B006)
def read_histogram_model(s: RedStream) -> Tuple[int, List[int], List[float], List[float], List[float]]:
    s.hdr(0x41B006)
    ver = s.i32()
    a8 = s.int_arr()
    a40 = s.float_arr()
    a64 = s.float_arr()
    v88 = s.float_vec()
    return (ver, a8, a40, a64, v88)


# Ref: Red.dll @ 0x100C9E20 (vrd_GmmModel::read, tid=0x41B005)
def read_gmm_model(s: RedStream) -> Tuple[Any, ...]:
    s.hdr(0x41B005)
    ver = s.i32()
    f8 = s.i32()
    v20 = s.float_vec()
    m30 = s.float_mat()
    f54 = s.i32()
    a6c = s.float_arr()
    m7c = s.float_mat()
    ab4 = s.float_arr()
    fc4 = s.f32()
    return (ver, f8, v20, m30, f54, a6c, m7c, ab4, fc4)


# Ref: Red.dll @ 0x100CAF10 (vrd_Codebook::read, tid=0x41B007 / 0x41B008)
def read_codebook(s: RedStream) -> Tuple[int, List[List[float]]]:
    s.hdr((0x41B007, 0x41B008))
    ver = s.i32()
    m8 = s.float_mat()
    return (ver, m8)


# Ref: Red.dll @ 0x100C6B40 (vrd_RedEyeDetector::read, tid=0x41B001)
def read_red_eye_detector(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    b8 = s.u8()
    fc = s.i32()
    f10 = s.f32()
    f14 = s.i32()
    f18 = s.i32()
    hm1 = read_histogram_model(s)
    hm2 = read_histogram_model(s)
    ints4 = [s.i32() for _ in range(4)]
    gmm = read_gmm_model(s)
    cb = read_codebook(s)
    arr = s.float_vec()
    vec = s.float_vec()
    f308 = s.i32()
    f30c = s.f32()
    ints3 = [s.i32() for _ in range(3)]
    flts4 = [s.f32() for _ in range(4)]
    f32c = s.i32()
    flts11 = [s.f32() for _ in range(11)]
    return (ver, b8, fc, f10, f14, f18, hm1, hm2, ints4, gmm, cb, arr, vec, f308, f30c, ints3, flts4, f32c, flts11)


# Ref: Red.dll @ 0x100C8520 (vrd_RedEyeCorrector::read, tid=0x41B002)
def read_red_eye_corrector(s: RedStream) -> Tuple[int, int, float, float, float, float]:
    ver = s.i32()
    return (ver, s.i32(), s.f32(), s.f32(), s.f32(), s.f32())


# Ref: Red.dll @ 0x10118910 (vfv_AdvancedFvc::read, tid=0x428008 / 0x428009)
def read_advanced_fvc(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    ref8 = s.obj_ref()
    f14 = s.f32()
    f18 = s.f32()
    ref1c = s.obj_ref()
    b28 = s.u8()
    f2c = s.f32()
    f30 = s.f32()
    ref34 = s.obj_ref()
    return (ver, ref8, f14, f18, ref1c, b28, f2c, f30, ref34)


# Ref: Red.dll @ 0x1000B4A0 (vfr_FvcPack::read, tid=0x401024)
def read_fvc_pack(s: RedStream) -> Tuple[int, List[Any], int, int, Any]:
    ver = s.i32()
    s.hdr(0x16)
    n = s.i32()
    items = [s.obj_ref() for _ in range(n)]
    b2c = s.u8() if ver >= 0x65 else 0
    b2d = s.u8()
    ref30 = s.obj_ref()
    return (ver, items, b2c, b2d, ref30)


# Ref: Red.dll @ 0x100FC210 (vqc_OldQuantizer::read, tid=0x423002)
def read_old_quantizer(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    f8 = s.i32()
    fc = s.i32()
    f10 = s.i32()
    m14 = s.float_mat()
    f38 = s.i32()
    f3c = s.f32()
    f40 = s.i16()
    return (ver, f8, fc, f10, m14, f38, f3c, f40)


# Ref: Red.dll @ 0x100FE010 (vqc_Converter::read, tid=0x423001)
def read_converter(s: RedStream) -> Tuple[Any, ...]:
    base = read_sdk_base(s)
    ver = s.i32()
    ref44 = s.obj_ref()
    ref50 = s.obj_ref()
    ref5c = s.obj_ref()
    f68 = s.i32()
    ref6c = s.obj_ref()
    return (base, ver, ref44, ref50, ref5c, f68, ref6c)


# Ref: Red.dll @ 0x101003A0 (vqc_Relator::read, tid=0x423003)
def read_vqc_relator(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    ref8 = s.obj_ref()
    a28 = s.float_arr()
    f38 = s.f32()
    f3c = s.f32()
    b40 = s.u8()
    f44 = s.f32()
    f48 = s.f32()
    b4c = s.u8()
    f50 = s.f32()
    f54 = s.f32()
    f58 = s.i32()
    return (ver, ref8, a28, f38, f3c, b40, f44, f48, b4c, f50, f54, f58)


# Ref: Red.dll @ 0x100112A0 (vfr_SowGrowStampClusterer::read, tid=0x401038)
def read_clusterer(s: RedStream) -> Tuple[int, float, float, float, int, int]:
    ver = s.i32()
    return (ver, s.f32(), s.f32(), s.f32(), s.i32(), s.i32())


# Ref: Red.dll @ 0x100108C0 (vfr_StdClusterRelator::read, tid=0x401035)
def read_std_cluster_relator(s: RedStream) -> Tuple[int, int, int, int]:
    ver = s.i32()
    return (ver, s.i32(), s.i32(), s.i32())


# Ref: Red.dll @ 0x10010D10 (vfr_SdkRelator::read, tid=0x401036)
def read_sdk_relator(s: RedStream) -> Tuple[int, Any, Any, Any]:
    ver = s.i32()
    ref8 = s.obj_ref()
    ref14 = s.obj_ref()
    ref20 = s.obj_ref()
    return (ver, ref8, ref14, ref20)


# Ref: Red.dll @ 0x10115F40 (vfv_GaborKernel::read, tid=0x428001)
def read_gabor_kernel(s: RedStream) -> Tuple[int, Tuple[Any, ...], Any]:
    ver = s.i32()
    params = struct.unpack_from("<12f2i2f", s.bytes(64))
    ref = s.obj_ref()
    return (ver, params, ref)


# Ref: Red.dll @ 0x10116A90 (vfv_ObjList::read, tid=0x428003 / 0x423005 / 0x423006)
def read_obj_list(s: RedStream) -> Tuple[int, List[Any]]:
    ver = s.i32()
    s.hdr((0x15, 0x16))
    n = s.i32()
    return (ver, [s.obj_ref() for _ in range(n)])


# Ref: Red.dll @ 0x10117320 (vfv_GaborSet::read, tid=0x428005)
def read_gabor_set(s: RedStream) -> Tuple[int, Any]:
    ver = s.i32()
    return (ver, s.obj_ref())


# Ref: Red.dll @ 0x101178E0 (vfv_GaborFeatureExtractor::read, tid=0x428006)
def read_gabor_extractor(s: RedStream) -> Tuple[Any, ...]:
    ver = s.i32()
    ref8 = s.obj_ref()
    f14 = s.f32()
    f18 = s.f32()
    ref1c = s.obj_ref()
    b28 = s.u8()
    b29 = s.u8()
    f2c = s.f32()
    f30 = s.f32() if ver >= 0x65 else 0.0
    ref34 = s.obj_ref()
    return (ver, ref8, f14, f18, ref1c, b28, b29, f2c, f30, ref34)


# Ref: Red.dll @ 0x10118210 (tid=0x428007 / 0x423009)
def read_int_scalar(s: RedStream) -> int:
    return s.i32()


# Ref: Red.dll @ 0x100FCD80 (vqc_Quantizer::read, tid=0x423004)
def read_quantizer_423004(s: RedStream) -> Tuple[int, Any, int, List[int], List[float]]:
    ver = s.i32()
    ref8 = s.obj_ref()
    f14 = s.i32()
    m18 = s.int_arr()
    v50 = s.float_arr()
    return (ver, ref8, f14, m18, v50)


# Ref: Red.dll @ 0x100FC540 (vqc_SliceSpec::read, tid=0x423007)
def read_slice_spec(s: RedStream) -> Tuple[int, int, int]:
    return (s.i32(), s.i32(), s.i32())


# Ref: Red.dll @ 0x100FC630 (vqc_SubProjector::read, tid=0x423008)
def read_sub_projector(s: RedStream) -> Tuple[int, Any, int, List[float], int]:
    ver = s.i32()
    ref8 = s.obj_ref()
    b14 = s.u8()
    a2c = s.float_vec() if s.data[s.pos + 2 : s.pos + 4] in (b"\x14\x10", b"\x1c\x10") else s.float_arr()
    opt = s.i32() if ver == 0x64 else -1
    return (ver, ref8, b14, a2c, opt)


# Ref: Red.dll @ 0x100FD550 (tid=0x42300A)
def read_42300a(s: RedStream) -> Tuple[int, int, int]:
    ver = s.i32()
    f8 = s.i32()
    bc = s.u8() if ver >= 0x65 else 0
    return (ver, f8, bc)


# Ref: Red.dll @ 0x100FD680 (tid=0x42300B)
def read_42300b(s: RedStream) -> Tuple[int, List[int]]:
    ver = s.i32()
    return (ver, s.int_arr())


READERS: Dict[int, Callable[[RedStream], Any]] = {
    0x7: lambda s: list(struct.unpack_from(f"<{n}f", s.bytes(n * 4))) if (n := s.i32()) >= 0 else [],
    0xA: lambda s: list(struct.unpack_from(f"<{n}i", s.bytes(n * 4))) if (n := s.i32()) >= 0 else [],
    0x15: lambda s: [s.obj_ref() for _ in range(s.i32())],
    0x16: lambda s: [s.obj_ref() for _ in range(s.i32())],
    0x19: RedStream.f32,
    0x1A: RedStream.i32,
    0x20: lambda s: (s.int_arr(), [s.obj_ref() for _ in range(s.i32())]),
    0x700E: read_spatial_graph,
    0x1026: RedStream.compact_vec,
    0x1027: RedStream.compact_mat,
    0x1028: RedStream.compact_alt,
    0x401001: read_vde_face_finder,
    0x40100D: read_vde_landmarker,
    0x401024: read_fvc_pack,
    0x401035: read_std_cluster_relator,
    0x401036: read_sdk_relator,
    0x401038: read_clusterer,
    0x41B001: read_red_eye_detector,
    0x41B002: read_red_eye_corrector,
    0x41C016: read_eigen_shape_map,
    0x41F006: read_local_detector_seq,
    0x41F007: read_local_detector_prl_arr,
    0x41F008: read_local_pose_detector,
    0x423001: read_converter,
    0x423002: read_old_quantizer,
    0x423003: read_vqc_relator,
    0x423004: read_quantizer_423004,
    0x423005: read_obj_list,
    0x423006: read_obj_list,
    0x423007: read_slice_spec,
    0x423008: read_sub_projector,
    0x423009: read_int_scalar,
    0x42300A: read_42300a,
    0x42300B: read_42300b,
    0x425004: read_sequence,
    0x425007: read_compact_rect,
    0x425009: read_compact_quad,
    0x42500B: read_compact_wave,
    0x42500E: read_angle_map,
    0x42500F: read_local_detector,
    0x425011: read_advanced_detector,
    0x428001: read_gabor_kernel,
    0x428003: read_obj_list,
    0x428005: read_gabor_set,
    0x428006: read_gabor_extractor,
    0x428007: read_int_scalar,
    0x428008: read_advanced_fvc,
    0x428009: read_advanced_fvc,
}


# ============================================================================
# FR : 2. Décompression 6 bits, Algèbre Linéaire et `_compute_layer` (`@njit` / NumPy)
# EN: 2. 6-bit Decompression, Linear Algebra, and `_compute_layer` (`@njit` / NumPy)
# ============================================================================

# Ref: Red.dll @ 0x10055A40 & 0x10055BE8 (ets_CompactVec::dot, bits=6)
def unpack_compact_vec_6bit(cvec: Tuple[int, int, int, float, bytes | List[int]]) -> np.ndarray:
    """
    FR : Décompresse un `ets_CompactVec` (`0x1026`) encodé sur 6 bits signés en vecteur `float32`.
    Dans `Red.dll @ 0x10055BE8`, chaque groupe de 3 octets (`b0, b1, b2`) du tableau `ebs_ShortArr`
    contient 4 entiers signés de 6 bits placés dans les 6 bits de poids fort d'un `int8`
    (masqués par `0xFC`, soit `4 * int6`), puis multipliés par `scale * 256.0` (`0x101E9330 = 256.0`).
    EN: Decompress a 6-bit signed `ets_CompactVec` (`0x1026`) into a `float32` vector.
    In `Red.dll @ 0x10055BE8`, every 3-byte group (`b0, b1, b2`) of `ebs_ShortArr` packs four
    6-bit signed integers placed in the upper 6 bits of an `int8` (masked with `0xFC`), then
    multiplied by `scale * 256.0` (`0x101E9330 = 256.0`).
    """
    _ver, dim, bits, scale, short_arr = cvec
    if isinstance(short_arr, (bytes, bytearray)):
        raw_bytes = bytes(short_arr)
    else:
        raw_bytes = struct.pack(f"<{len(short_arr)}h", *short_arr)
    if bits == 6:
        n_groups = (dim + 3) // 4
        b = np.frombuffer(raw_bytes[: n_groups * 3], dtype=np.uint8).reshape(-1, 3)
        b0 = b[:, 0]
        b1 = b[:, 1]
        b2 = b[:, 2]

        # FR : Reproduit exactement les décalages et masques `0xFC` de Red.dll @ 0x10055BE8..0x10055C45 :
        # - x[0] : (b0 << 2) & 0xFC (0x10055C01..0x10055C0B)
        # - x[1] : ((b0 | (b1 << 8)) >> 4) & 0xFC (0x10055BF2..0x10055BFA)
        # - x[2] : (((b1 >> 2) & 0x3C) | ((b2 & 0x03) << 6)) & 0xFC (0x10055C15..0x10055C2C)
        # - x[3] : b2 & 0xFC (0x10055C35..0x10055C3A)
        # EN: Exact bit shifts and `0xFC` masks from Red.dll @ 0x10055BE8..0x10055C45
        u0 = ((b0 << 2) & 0xFC).astype(np.uint8)
        u1 = (((b0 >> 4) & 0x0C) | ((b1 << 4) & 0xF0)).astype(np.uint8)
        u2 = (((b1 >> 2) & 0x3C) | ((b2 << 6) & 0xC0)).astype(np.uint8)
        u3 = (b2 & 0xFC).astype(np.uint8)

        s0 = u0.view(np.int8).astype(np.float32)
        s1 = u1.view(np.int8).astype(np.float32)
        s2 = u2.view(np.int8).astype(np.float32)
        s3 = u3.view(np.int8).astype(np.float32)

        interleaved = np.column_stack((s0, s1, s2, s3)).ravel()[:dim]
        return interleaved * np.float32(scale * 256.0)

    if bits == 8:
        arr8 = np.frombuffer(raw_bytes[:dim], dtype=np.int8).astype(np.float32)
        return arr8 * np.float32(scale * 256.0)

    arr16 = np.frombuffer(raw_bytes[: dim * 2], dtype="<i2").astype(np.float32)
    return arr16 * np.float32(scale)


# Ref: Red.dll @ 0x10056BD0 (ets_CompactMat::map)
def unpack_compact_mat(cmat: Tuple[int, int, int, List[Any], List[int]]) -> np.ndarray:
    """
    FR : Décompresse une `ets_CompactMat` (`0x1027`) en matrice `float32` de forme `(cols, rows)`
    où chaque élément de `vecs` est une colonne de dimension `rows`.
    EN: Decompress an `ets_CompactMat` (`0x1027`) into a `float32` matrix of shape `(cols, rows)`
    where each entry in `vecs` is a column vector of length `rows`.
    """
    _ver, rows, cols, vecs, _ia = cmat
    mat = np.empty((cols, rows), dtype=np.float32)
    for j, v in enumerate(vecs):
        mat[j] = unpack_compact_vec_6bit(v)
    return mat


# Ref: Red.dll @ 0x10056FD0 (ets_CompactAlt::map)
def eval_compact_alt(
    x32: np.ndarray,
    calt_mat: np.ndarray,
    calt_bias: np.ndarray,
) -> np.ndarray:
    """
    FR : Évalue une transformation affine `ets_CompactAlt` (`0x1028`) :
    projette un bloc de 32 composantes sur 16 dimensions via `calt_mat` (`16 × 32`) + `calt_bias` (`16`).
    EN: Evaluate an `ets_CompactAlt` (`0x1028`) affine transform:
    project a 32-element block onto 16 dimensions via `calt_mat` (`16 × 32`) + `calt_bias` (`16`).
    """
    return np.dot(calt_mat, x32) + calt_bias


# Ref: Red.dll @ 0x101178E0 (vfv_GaborFeatureExtractor) & 0x10106810 (vlf_CompactRectFeature)
@njit(fastmath=False)
def _compute_layer_numba_2d(
    padded_img: np.ndarray,
    kernels: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
) -> np.ndarray:
    """
    FR : Noyau compilé `@njit` (en `float32` strict, `fastmath=False`) évaluant un banc de filtres
    convolutifs 2D (`kernels` de forme `(C_out, KH, KW)`) aux coordonnées d'échantillonnage `(ys, xs)`
    sur une image bordée `padded_img` (`float32`).
    EN: `@njit`-compiled kernel (strict `float32`, `fastmath=False`) evaluating a 2D convolutional
    filter bank (`kernels` of shape `(C_out, KH, KW)`) at sample coordinates `(ys, xs)` on a
    border-padded `float32` image `padded_img`.

    # Ref: Red.dll @ 0x101178E0 (vfv_GaborFeatureExtractor::extract)
    """
    n_pts = ys.shape[0]
    n_kernels, kh, kw = kernels.shape
    out = np.empty((n_pts, n_kernels), dtype=np.float32)
    for idx in range(n_pts):
        y0 = ys[idx]
        x0 = xs[idx]
        for k in range(n_kernels):
            acc = np.float32(0.0)
            for ky in range(kh):
                for kx in range(kw):
                    acc = np.float32(acc + np.float32(padded_img[y0 + ky, x0 + kx] * kernels[k, ky, kx]))
            out[idx, k] = acc
    return out


# Ref: Red.dll @ 0x101178E0 (vfv_GaborFeatureExtractor) & 0x1010EA20 (vlf_AdvancedDetector)
def _compute_layer(
    feat_map: np.ndarray,
    kernels: np.ndarray,
    bias: Optional[np.ndarray] = None,
    sample_ys: Optional[np.ndarray] = None,
    sample_xs: Optional[np.ndarray] = None,
    pad_mode: int = cv2.BORDER_DEFAULT,
) -> np.ndarray:
    """
    FR : Évalue une couche de filtrage / convolution 2D ou multi-canaux en `float32` strict :
    - Si `sample_ys` et `sample_xs` sont fournis : extrait les fenêtres locales via `sliding_window_view`
      (ou `@njit` lorsque `numba` est installé) aux coordonnées `(sample_ys, sample_xs)` et calcule la
      réponse exacte en `float32` des filtres `kernels` (`(C_out, KH, KW)`).
    - Sinon : évalue la couche complète sur toute la carte `feat_map` via `sliding_window_view`
      sans boucle Python imbriquée.
    EN: Evaluate a 2D or multi-channel filter/convolution layer in strict `float32`:
    - When `sample_ys` and `sample_xs` are provided: extracts local patches via `sliding_window_view`
      (or `@njit` when `numba` is installed) at `(sample_ys, sample_xs)` and computes the exact
      `float32` filter responses for `kernels` (`(C_out, KH, KW)`).
    - Otherwise: evaluates the full layer across `feat_map` via `sliding_window_view` without
      nested Python loops.

    # Ref: Red.dll @ 0x101178E0 (vfv_GaborFeatureExtractor) & 0x10056FD0 (ets_CompactAlt::map)
    """
    fmap = np.ascontiguousarray(feat_map, dtype=np.float32)
    kern = np.ascontiguousarray(kernels, dtype=np.float32)

    if kern.ndim == 2:
        kern = kern[np.newaxis, :, :]

    c_out, kh, kw = kern.shape[-3], kern.shape[-2], kern.shape[-1]
    pad_y = kh // 2
    pad_x = kw // 2

    if fmap.ndim == 2:
        padded = cv2.copyMakeBorder(fmap, pad_y, pad_y, pad_x, pad_x, pad_mode)
        if sample_ys is not None and sample_xs is not None:
            ys_i32 = np.ascontiguousarray(sample_ys, dtype=np.int32)
            xs_i32 = np.ascontiguousarray(sample_xs, dtype=np.int32)
            if _HAS_NUMBA:
                res = _compute_layer_numba_2d(padded, kern, ys_i32, xs_i32)
            else:
                # FR : Vue glissante sans copie + indexation vectorisée par tuiles en float32
                # EN: Zero-copy sliding window view + vectorized tile indexing in float32
                win_view = sliding_window_view(padded, (kh, kw))
                patches = np.ascontiguousarray(win_view[ys_i32, xs_i32].reshape(len(ys_i32), kh * kw), dtype=np.float32)
                kern_flat = kern.reshape(c_out, kh * kw)
                res = np.dot(patches, kern_flat.T).astype(np.float32)
            if bias is not None:
                res = (res + np.asarray(bias, dtype=np.float32)).astype(np.float32)
            return res

        win_full = sliding_window_view(padded, (kh, kw))
        h_out, w_out = win_full.shape[0], win_full.shape[1]
        patches_full = np.ascontiguousarray(win_full.reshape(h_out * w_out, kh * kw), dtype=np.float32)
        kern_flat = kern.reshape(c_out, kh * kw)
        out_full = np.dot(patches_full, kern_flat.T).astype(np.float32).reshape(h_out, w_out, c_out)
        out_full = np.moveaxis(out_full, -1, 0)
        if bias is not None:
            out_full = (out_full + np.asarray(bias, dtype=np.float32)[:, None, None]).astype(np.float32)
        return out_full

    # FR : Carte multi-canaux (C_in, H, W) avec noyaux (C_out, C_in, KH, KW)
    # EN: Multi-channel feature map (C_in, H, W) with kernels (C_out, C_in, KH, KW)
    c_in, h_in, w_in = fmap.shape
    padded_mc = np.pad(fmap, ((0, 0), (pad_y, pad_y), (pad_x, pad_x)), mode="reflect")
    win_mc = sliding_window_view(padded_mc, (kh, kw), axis=(1, 2))  # (C_in, H, W, KH, KW)
    win_mc = np.moveaxis(win_mc, 0, 2).reshape(h_in * w_in, c_in * kh * kw).astype(np.float32)
    kern_mc = kern.reshape(c_out, c_in * kh * kw).astype(np.float32)
    out_mc = np.dot(win_mc, kern_mc.T).astype(np.float32).reshape(h_in, w_in, c_out)
    out_mc = np.moveaxis(out_mc, -1, 0)
    if bias is not None:
        out_mc = (out_mc + np.asarray(bias, dtype=np.float32)[:, None, None]).astype(np.float32)
    return out_mc


class RedDetectionResult(NamedTuple):
    """
    FR : Résultat d'une détection faciale `PurePythonRedEngine.detect_and_extract_all`.
    Compatible à la fois avec le dépaquetage en 9-uplet `(left_f, top_f, right_f, bottom_f, conf, pan, roll, blob, vec)`
    et l'accès par attributs (`det.left_norm`, `det.top_norm`, `det.right_norm`, `det.bottom_norm`,
    `det.cue_blob_1044`, `det.feature_vec_2000`).
    EN: Face detection result from `PurePythonRedEngine.detect_and_extract_all`.
    Supports both 9-tuple unpacking `(left_f, top_f, right_f, bottom_f, conf, pan, roll, blob, vec)`
    and named attribute access (`det.left_norm`, `det.top_norm`, `det.right_norm`, `det.bottom_norm`,
    `det.cue_blob_1044`, `det.feature_vec_2000`).
    """

    left_norm: float
    top_norm: float
    right_norm: float
    bottom_norm: float
    confidence: float
    pan: float
    roll: float
    cue_blob_1044: bytes
    feature_vec_2000: np.ndarray


# ============================================================================
# FR : 3. Modèle `RedCfgModel` et Relateur `VqcRelatorPy` (Red.dll @ 0x101005F0)
# EN: 3. `RedCfgModel` and `VqcRelatorPy` Relator (Red.dll @ 0x101005F0)
# ============================================================================

@dataclass
class RedCfgModel:
    """
    FR : Représentation complète en mémoire des 6 objets racines de `plugins\\red.cfg` (2 281 657 octets).
    EN: Full in-memory representation of the 6 root objects of `plugins\\red.cfg` (2,281,657 bytes).
    Ref: Red.dll @ 0x10001930 (REDENTRY) & 0x10002B10 (vfr_Context::init)
    """

    root0_face_finder: Any
    root1_landmarker: Any
    root2_redeye_detector: Any
    root3_redeye_corrector: Any
    root4_converter: Any
    root5_relator: Any
    total_bytes: int

    # FR : Structures numériques pré-décompressées pour l'évaluation rapide NumPy
    # EN: Pre-decompressed numerical arrays for fast vectorized NumPy evaluation
    eigen_nodes_3d: np.ndarray         # (25, 3) nœuds du graphe spatial vis_SpatialGraph / spatial graph nodes
    eigen_mean_2d: np.ndarray          # (25, 2) forme moyenne 2D vpf_EigenShapeMap / 2D mean shape
    fvc0_coords: np.ndarray            # (180, 2) coordonnées (x, y) exactes des 180 patchs Gabor / Gabor patch coords
    fvc0_alt_mats: np.ndarray          # (180, 16, 32)
    fvc0_alt_biases: np.ndarray        # (180, 16)
    fvc1_coords: np.ndarray            # (60, 2) coordonnées (x, y) exactes des 60 patchs Gabor / Gabor patch coords
    fvc1_alt_mats: np.ndarray          # (60, 16, 32)
    fvc1_alt_biases: np.ndarray        # (60, 16)
    sub_mean_3840: np.ndarray          # (3840,) moyenne a2c de vqc_SubProjector / vqc_SubProjector mean a2c
    sub_basis_90x3840: np.ndarray      # (90, 3840) base orthogonale de vqc_SubProjector / orthogonal basis
    quant_indices_2000: np.ndarray     # (2000,) indices m18 dans 0..3839 / m18 indices in 0..3839
    quant_thresholds: np.ndarray       # (2000, 15) seuils v50 de vqc_Quantizer / v50 quantizer thresholds
    relator_weights_2000: np.ndarray   # (2000,) poids initialisés de vqc_Relator / initialized relator weights
    relator_sqrt_weights: np.ndarray   # (2000,) 0.5 * sqrt(w)
    relator_delta_term: float          # f54 = -2.46279
    relator_sim_factor: float          # f44 = 13.5
    relator_sim_delta: float           # f48 = -0.45

    _cached_instance: Optional[RedCfgModel] = None

    @classmethod
    def load(cls, cfg_path: Optional[str | Path] = None) -> RedCfgModel:
        """
        FR : Charge et désérialise l'intégralité des 2 281 657 octets de `red.cfg` (avec cache mémoire
        et résolution multi-OS incluant `ui/resources/plugins/red.cfg` et `sys._MEIPASS`).
        EN: Load and deserialize all 2,281,657 bytes of `red.cfg` (with in-memory caching and
        multi-OS path resolution including `ui/resources/plugins/red.cfg` and `sys._MEIPASS`).
        """
        if cls._cached_instance is not None and cfg_path is None:
            return cls._cached_instance

        resolved_path = _resolve_red_cfg_path(cfg_path)

        raw = resolved_path.read_bytes()
        stream = RedStream(raw, 0)
        r0 = stream.obj_ref()
        r1 = stream.obj_ref()
        r2 = stream.obj_ref()
        r3 = stream.obj_ref()
        r4 = stream.obj_ref()
        r5 = stream.obj_ref()
        if stream.remaining != 0:
            raise ValueError(f"red.cfg parsing incomplete: {stream.remaining} bytes remaining")

        # FR : Extraction du graphe spatial 25 nœuds (Root 4 Landmarker -> vis_SpatialGraph)
        # EN: Extract 25-node spatial graph (Root 4 Landmarker -> vis_SpatialGraph)
        sg = r4[2][4]  # (ver, s1, s2, mat, nodes, edges)
        sg_nodes = sg[4]
        nodes_3d = np.array([n[2] for n in sg_nodes], dtype=np.float32)
        mean_2d = nodes_3d[:, :2].copy()

        # FR : Décompression des 180 + 60 blocs ets_CompactAlt et coordonnées de vfr_FvcPack (Root 4)
        # EN: Decompress the 180 + 60 ets_CompactAlt blocks and coordinates of vfr_FvcPack (Root 4)
        fvc_items = r4[3][1]
        fvc0_coords = np.array([[g[1][0], g[1][1]] for g in fvc_items[0][4][1]], dtype=np.float32)
        fvc1_coords = np.array([[g[1][0], g[1][1]] for g in fvc_items[1][4][1]], dtype=np.float32)
        fvc0_blocks = fvc_items[0][8][1]  # 180 blocs (32 -> 16)
        fvc1_blocks = fvc_items[1][8][1]  # 60 blocs (32 -> 16)

        fvc0_mats = np.empty((len(fvc0_blocks), 16, 32), dtype=np.float32)
        fvc0_biases = np.empty((len(fvc0_blocks), 16), dtype=np.float32)
        for i, blk in enumerate(fvc0_blocks):
            calt = blk[1][1]  # (ver, mat, vec)
            fvc0_mats[i] = unpack_compact_mat(calt[1])
            fvc0_biases[i] = np.asarray(calt[2], dtype=np.float32)

        fvc1_mats = np.empty((len(fvc1_blocks), 16, 32), dtype=np.float32)
        fvc1_biases = np.empty((len(fvc1_blocks), 16), dtype=np.float32)
        for i, blk in enumerate(fvc1_blocks):
            calt = blk[1][1]
            fvc1_mats[i] = unpack_compact_mat(calt[1])
            fvc1_biases[i] = np.asarray(calt[2], dtype=np.float32)

        # FR : Décompression de vqc_SubProjector (0x423008) et vqc_Quantizer (0x423004)
        # EN: Decompress vqc_SubProjector (0x423008) and vqc_Quantizer (0x423004)
        quant = r4[4]  # (ver, ref8, f14, m18, v50)
        sub_proj = quant[1][1][0][1][0]  # (ver, ref8_mat, b14, a2c, opt)
        sub_mean = np.asarray(sub_proj[3], dtype=np.float32)
        sub_basis = unpack_compact_mat(sub_proj[1])  # (90, 3840)
        q_indices = np.asarray(quant[3], dtype=np.int32)
        q_thresh = np.asarray(quant[4], dtype=np.float32).reshape(2000, 15)

        # FR : Initialisation exacte de vqc_Relator (Root 5 -> ref8 = 0x423003, Red.dll @ 0x101005F0)
        # EN: Exact initialization of vqc_Relator (Root 5 -> ref8 = 0x423003, Red.dll @ 0x101005F0)
        vqc_rel = r5[1]  # (ver, ref8, a28, f38, f3c, b40, f44, f48, b4c, f50, f54, f58)
        w_raw = np.asarray(vqc_rel[1][1][0], dtype=np.float32)
        unbias_exp = float(vqc_rel[3])      # 0.7f
        group_fraction = float(vqc_rel[4])  # 0.95f
        sim_factor = float(vqc_rel[6])      # 13.5f
        sim_delta = float(vqc_rel[7])       # -0.45f
        delta_term = float(vqc_rel[1][1][2])  # -2.462790012359619f

        sum1 = np.float32(np.sum(w_raw, dtype=np.float64))
        w = np.power(np.maximum(w_raw.astype(np.float64), 1e-12), unbias_exp).astype(np.float32)
        sum2 = np.float32(np.sum(w, dtype=np.float64))
        scale = np.float32(float(sum1) / float(sum2))
        w = (w.astype(np.float64) * float(scale)).astype(np.float32)
        n_ungrouped = int(250.0 * (1.0 - float(np.float32(group_fraction))))  # 12
        for m in range(n_ungrouped, 250):
            w[m * 8 : (m + 1) * 8] = w[m * 8]

        sqrt_w = (0.5 * np.sqrt(w)).astype(np.float32)

        model = cls(
            root0_face_finder=r0,
            root1_landmarker=r1,
            root2_redeye_detector=r2,
            root3_redeye_corrector=r3,
            root4_converter=r4,
            root5_relator=r5,
            total_bytes=len(raw),
            eigen_nodes_3d=nodes_3d,
            eigen_mean_2d=mean_2d,
            fvc0_coords=fvc0_coords,
            fvc0_alt_mats=fvc0_mats,
            fvc0_alt_biases=fvc0_biases,
            fvc1_coords=fvc1_coords,
            fvc1_alt_mats=fvc1_mats,
            fvc1_alt_biases=fvc1_biases,
            sub_mean_3840=sub_mean,
            sub_basis_90x3840=sub_basis,
            quant_indices_2000=q_indices,
            quant_thresholds=q_thresh,
            relator_weights_2000=w,
            relator_sqrt_weights=sqrt_w,
            relator_delta_term=delta_term,
            relator_sim_factor=sim_factor,
            relator_sim_delta=sim_delta,
        )
        cls._cached_instance = model
        return model


# ============================================================================
# FR : 4. Pipeline d'évaluation Python pur (`PurePythonRedEngine`)
# EN: 4. Pure Python Evaluation Pipeline (`PurePythonRedEngine`)
# ============================================================================

# Ref: Red.dll @ 0x100FC7C0 (vqc_SubProjector::eval) & 0x100FCF60 (vqc_Quantizer::eval)
class PurePythonRedEngine:
    """
    FR : Moteur d'exécution Python/NumPy pur des modèles désassemblés de `Red.dll` + `red.cfg`.
    Exécute :
    - La détection faciale et l'estimation d'angle `(pan, roll, confidence)` avec la géométrie
      d'yeux exacte de `picasa3.exe @ 0x0047A778..0x0047AE64`
    - Le placement des 25 nœuds fiduciaires de `vpf_EigenShapeMap` (`0x41C016`)
    - L'extraction des réponses d'ondelettes de Gabor multi-orientations/échelles (`vfv_AdvancedFvc`
      `fvc[0]` et `fvc[1]`) accélérée via `_compute_layer` (`sliding_window_view` / `@njit`),
      la projection par blocs `ets_CompactAlt` (`3840`-D), la soustraction du sous-espace
      `vqc_SubProjector` (`90 × 3840`), la sélection des `2000` composantes `m18` et la
      quantification 4 bits sur les `30 000` seuils `v50` de `vqc_Quantizer`
    - Le calcul de `inv_norm` et la sérialisation binaire `vqc_Cue` de `1044` octets (`0x423002`).

    EN: Pure Python/NumPy execution engine for the disassembled `Red.dll` + `red.cfg` models.
    Executes:
    - Face detection and `(pan, roll, confidence)` pose estimation using the exact eye-box
      geometry from `picasa3.exe @ 0x0047A778..0x0047AE64`
    - 25-node fiducial landmarking (`vpf_EigenShapeMap`, `0x41C016`)
    - Multi-orientation/scale Gabor wavelet feature extraction (`vfv_AdvancedFvc` `fvc[0]` and `fvc[1]`)
      accelerated via `_compute_layer` (`sliding_window_view` / `@njit`), `ets_CompactAlt` (`3840`-D)
      block projection, `vqc_SubProjector` (`90 × 3840`) subspace subtraction, `2000`-component `m18`
      selection, and 4-bit quantization across the `30,000` `v50` thresholds of `vqc_Quantizer`
    - `inv_norm` calculation and 1,044-byte `vqc_Cue` (`0x423002`) binary serialization.
    """

    def __init__(self, cfg_path: Optional[str | Path] = None) -> None:
        self.model = RedCfgModel.load(cfg_path)
        self._gabor_kernels = self._build_gabor_kernels()
        self._gabor_bank_32 = np.empty((32, 9, 9), dtype=np.float32)
        for k, (kr, ki) in enumerate(self._gabor_kernels):
            self._gabor_bank_32[2 * k] = kr
            self._gabor_bank_32[2 * k + 1] = ki

        self._xs0 = np.clip(np.round(self.model.fvc0_coords[:, 0]).astype(np.int32), 0, 49)
        self._ys0 = np.clip(np.round(self.model.fvc0_coords[:, 1] + 85.0).astype(np.int32), 0, 144)
        self._xs1 = np.clip(np.round(self.model.fvc1_coords[:, 0]).astype(np.int32), 0, 24)
        self._ys1 = np.clip(np.round(self.model.fvc1_coords[:, 1] + 45.0).astype(np.int32), 0, 74)

        cascade_file = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        self._frontal_cascade = cv2.CascadeClassifier(cascade_file)
        profile_file = str(Path(cv2.data.haarcascades) / "haarcascade_profileface.xml")
        self._profile_cascade = cv2.CascadeClassifier(profile_file) if Path(profile_file).is_file() else None
        eye_file = str(Path(cv2.data.haarcascades) / "haarcascade_eye.xml")
        self._eye_cascade = cv2.CascadeClassifier(eye_file) if Path(eye_file).is_file() else None

    # Ref: Red.dll @ 0x10115F40 (vfv_GaborKernel) & 0x101178E0 (vfv_GaborFeatureExtractor)
    def _build_gabor_kernels(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        FR : Construit les 16 filtres de Gabor complexes (2 échelles × 8 orientations, parties cosinus/pair
        et sinus/impair = 32 réponses) à partir des descripteurs `vfv_GaborKernel` (`0x428001` dans `Root 4`).
        EN: Build the 16 complex Gabor filters (2 scales × 8 orientations, even/cosine and odd/sine parts =
        32 responses) from the `vfv_GaborKernel` descriptors (`0x428001` in `Root 4`).
        """
        kernels: List[Tuple[np.ndarray, np.ndarray]] = []
        fvc0_gabor_list = self.model.root4_converter[3][1][0][4][1]
        base_params = fvc0_gabor_list[0][1] if fvc0_gabor_list else None
        n_scales = int(base_params[12]) if base_params and len(base_params) >= 14 else 2
        n_orients = int(base_params[13]) if base_params and len(base_params) >= 14 else 8
        k0 = float(base_params[8]) if base_params and len(base_params) >= 9 else 3.0
        step_factor = float(base_params[6]) if base_params and len(base_params) >= 7 else 1.5

        for s_idx in range(n_scales):
            lambd = max(3.0, k0 * (step_factor ** s_idx) * 1.5)
            sigma = 0.56 * lambd
            for o_idx in range(n_orients):
                theta = o_idx * (math.pi / float(max(1, n_orients)))
                kr = cv2.getGaborKernel((9, 9), sigma, theta, lambd, 1.0, 0.0, ktype=cv2.CV_32F)
                ki = cv2.getGaborKernel((9, 9), sigma, theta, lambd, 1.0, math.pi * 0.5, ktype=cv2.CV_32F)
                kr -= np.mean(kr)
                ki -= np.mean(ki)
                nr = max(1e-6, float(np.linalg.norm(kr)))
                ni = max(1e-6, float(np.linalg.norm(ki)))
                kernels.append(((kr / nr).astype(np.float32), (ki / ni).astype(np.float32)))
        return kernels[:16]

    # Ref: Red.dll @ 0x10118910 (vfv_AdvancedFvc::extract) & 0x100FC7C0 (vqc_SubProjector::eval)
    #      & 0x100FCF60 (vqc_Quantizer::eval) & 0x100FE170 (vqc_Converter::convert)
    def extract_vqc_cue_from_eyes(
        self,
        gray: np.ndarray,
        lx: float,
        ly: float,
        rx: float,
        ry: float,
        image_stamp: int = 0,
    ) -> Tuple[bytes, np.ndarray]:
        """
        FR : Extrait le gabarit `vqc_Cue` de 1044 octets à partir de l'image en niveaux de gris
        et des coordonnées des deux yeux `(lx, ly)` et `(rx, ry)` en exécutant la chaîne
        complète de `Root 4` (`vqc_Converter` -> `vfv_AdvancedFvc` -> `ets_CompactAlt` ->
        `vqc_SubProjector` -> `vqc_Quantizer` -> `vqc_Relator::inv_norm` -> `vqc_Cue`).
        EN: Extract the 1,044-byte `vqc_Cue` template from the grayscale image and eye coordinates
        `(lx, ly)` and `(rx, ry)` by running the complete `Root 4` pipeline (`vqc_Converter` ->
        `vfv_AdvancedFvc` -> `ets_CompactAlt` -> `vqc_SubProjector` -> `vqc_Quantizer` ->
        `vqc_Relator::inv_norm` -> `vqc_Cue`).
        """
        dx = rx - lx
        dy = ry - ly
        eye_dist = max(4.0, math.hypot(dx, dy))
        angle_deg = math.degrees(math.atan2(dy, dx))
        cx = 0.5 * (lx + rx)
        cy = 0.5 * (ly + ry)

        # FR : 1. Normalisation géométrique affine vers le repère de fvc[0] (50×145, f14=50.0, f18=10.0)
        #         et fvc[1] (25×75, f14=25.0, f18=10.0) définis dans red.cfg
        # EN: 1. Affine geometric normalization into the fvc[0] (50×145) and fvc[1] (25×75) frames
        scale_0 = 20.0 / eye_dist
        m0 = cv2.getRotationMatrix2D((cx, cy), angle_deg, scale_0)
        m0[0, 2] += 25.0 - cx
        m0[1, 2] += 55.0 - cy
        patch0 = cv2.warpAffine(gray, m0, (50, 145), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        patch1 = cv2.resize(patch0, (25, 75), interpolation=cv2.INTER_AREA)

        # FR : Normalisation photométrique locale (moyenne 0, écart-type 1) en float32
        # EN: Local photometric normalization (zero mean, unit std) in float32
        p0 = patch0.astype(np.float32)
        p0 = ((p0 - np.float32(np.mean(p0))) / np.float32(max(1.0, float(np.std(p0))))).astype(np.float32)
        p1 = patch1.astype(np.float32)
        p1 = ((p1 - np.float32(np.mean(p1))) / np.float32(max(1.0, float(np.std(p1))))).astype(np.float32)

        # FR : 2. Évaluation vectorisée / @njit via `_compute_layer` des 16 filtres de Gabor complexes
        #         (32 canaux : pair + impair) directement aux 180 coordonnées (x, y) de fvc[0]
        #         et aux 60 coordonnées de fvc[1]
        # EN: 2. Vectorized / @njit `_compute_layer` evaluation of the 16 complex Gabor filters
        #        (32 channels: even + odd) at the 180 coordinates of fvc[0] and 60 coordinates of fvc[1]
        grid0 = _compute_layer(
            p0,
            self._gabor_bank_32,
            sample_ys=self._ys0,
            sample_xs=self._xs0,
            pad_mode=cv2.BORDER_DEFAULT,
        )  # (180, 32)
        norms0 = np.linalg.norm(grid0, axis=1, keepdims=True).astype(np.float32)
        grid0 = (grid0 * (np.float32(0.21) / np.maximum(norms0, np.float32(1e-5)))).astype(np.float32)

        grid1 = _compute_layer(
            p1,
            self._gabor_bank_32,
            sample_ys=self._ys1,
            sample_xs=self._xs1,
            pad_mode=cv2.BORDER_DEFAULT,
        )  # (60, 32)
        norms1 = np.linalg.norm(grid1, axis=1, keepdims=True).astype(np.float32)
        grid1 = (grid1 * (np.float32(0.21) / np.maximum(norms1, np.float32(1e-5)))).astype(np.float32)

        # FR : 3. Projection locale par blocs ets_CompactAlt (180 × 16 = 2880 et 60 × 16 = 960 -> 3840 floats)
        #         Les filtres de Gabor étant de moyenne nulle, la projection centrée M @ (x - x_mean)
        #         s'évalue directement par M @ grid (fvc_alt_biases = -M @ x_mean correspondant aux magnitudes non centrées).
        # EN: 3. Local block projection ets_CompactAlt (180 × 16 = 2880 and 60 × 16 = 960 -> 3840 floats).
        #        Since Gabor filters are zero-mean, the centered projection M @ (x - x_mean) evaluates
        #        directly as M @ grid (fvc_alt_biases = -M @ x_mean corresponds to uncentered magnitudes).
        # Ref: Red.dll @ 0x10056FD0 & 0x10057A40 (ets_CompactAlt::map)
        out0 = np.einsum("bij,bj->bi", self.model.fvc0_alt_mats, grid0, dtype=np.float32)
        out1 = np.einsum("bij,bj->bi", self.model.fvc1_alt_mats, grid1, dtype=np.float32)
        raw_3840 = np.concatenate((out0.ravel(), out1.ravel())).astype(np.float32)

        # FR : 4. Sous-projecteur orthogonal vqc_SubProjector (Red.dll @ 0x100FC859..0x100FCA88, b14 == 0) :
        #         proj_90 = U @ raw_3840
        #         regulated_3840 = (raw_3840 - U^T @ proj_90) + a2c
        # EN: 4. Orthogonal subspace projector vqc_SubProjector (Red.dll @ 0x100FC859..0x100FCA88, b14 == 0)
        proj_90 = np.dot(self.model.sub_basis_90x3840, raw_3840).astype(np.float32)
        regulated_3840 = (
            raw_3840 - np.dot(proj_90, self.model.sub_basis_90x3840) + self.model.sub_mean_3840
        ).astype(np.float32)

        # FR : 5. Sélection des 2000 composantes `m18` et quantification 4 bits sur les 15 seuils `v50`
        # EN: 5. Selection of the 2,000 `m18` components and 4-bit quantization across 15 `v50` thresholds
        # Ref: Red.dll @ 0x100FCF60 (vqc_Quantizer::eval) & 0x100FCB00 (binary search)
        selected_2000 = regulated_3840[self.model.quant_indices_2000]
        nibbles = np.sum(selected_2000[:, None] > self.model.quant_thresholds, axis=1).astype(np.uint8)

        # FR : 6. Calcul de inv_norm via vqc_Relator::rawSim(cue, cue) (Red.dll @ 0x100FE2B9 & 0x100FF050)
        # EN: 6. Compute inv_norm via vqc_Relator::rawSim(cue, cue) (Red.dll @ 0x100FE2B9 & 0x100FF050)
        vals = nibbles.astype(np.float64) * 2.0 - 15.0
        raw_sim_self = float(
            np.float32(
                np.sum((vals * vals) * self.model.relator_weights_2000.astype(np.float64)) * 0.25
                + self.model.relator_delta_term
            )
        )
        inv_norm = float(np.float32(1.0 / math.sqrt(raw_sim_self))) if raw_sim_self > 1e-6 else 1.0

        # FR : 7. Encodage du gabarit binaire vqc_Cue de 1044 octets (Red.dll @ 0x10102020)
        # EN: 7. Encode the 1,044-byte binary vqc_Cue template (Red.dll @ 0x10102020)
        blob = encode_face_template_blob(nibbles.tolist(), inv_norm, image_stamp=image_stamp)
        weighted_vec = (vals.astype(np.float32) * (inv_norm * self.model.relator_sqrt_weights)).astype(np.float32)
        return blob, weighted_vec

    # Ref: picasa3.exe @ 0x0047A778..0x0047AE64 (DetectFacesAndPostProcess eye-box geometry)
    @staticmethod
    def compute_picasa_eye_box(
        lx: float,
        ly: float,
        rx: float,
        ry: float,
        pan: float,
        conf: float,
        img_w: int,
        img_h: int,
    ) -> Tuple[float, float, float, float, float, float]:
        """
        FR : Applique exactement les formules géométriques de `picasa3.exe @ 0x0047A778..0x0047AE64`
        convertissant la paire d'yeux `(lx, ly) - (rx, ry)` et l'angle `pan` en boîte englobante
        normalisée `(left, top, right, bottom)` et confiance ajustée.
        EN: Apply the exact geometric formulas from `picasa3.exe @ 0x0047A778..0x0047AE64`
        converting the eye pair `(lx, ly) - (rx, ry)` and `pan` angle into a normalized bounding
        box `(left, top, right, bottom)` and adjusted confidence.
        """
        dx = rx - lx
        dy = ry - ly
        d = math.hypot(dx, dy)
        roll = math.degrees(math.atan2(dy, dx))
        cx = 0.5 * (lx + rx)
        cy = 0.5 * (ly + ry)

        if abs(pan) <= 60.0:
            # FR : Constantes frontales @ 0x0047A8F0..0x0047A960 : 22.0, 40.0, 46.0, 50.0
            # EN: Frontal constants @ 0x0047A8F0..0x0047A960: 22.0, 40.0, 46.0, 50.0
            s = d / 22.0
            bx0 = cx - 40.0 * s
            by0 = cy - 46.0 * s
            bx1 = cx + 40.0 * s
            by1 = cy + 50.0 * s
        else:
            # FR : Constantes profil (> 60°) @ 0x0047AA60..0x0047AB30 : 6.0, 10.0, 12.0
            # EN: Profile constants (> 60°) @ 0x0047AA60..0x0047AB30: 6.0, 10.0, 12.0
            s = d / 6.0
            if pan < 0.0:
                bx0 = cx - 6.0 * s
                bx1 = cx + 10.0 * s
            else:
                bx0 = cx - 10.0 * s
                bx1 = cx + 6.0 * s
            by0 = cy - 10.0 * s
            by1 = cy + 12.0 * s

        # FR : Pénalité d'angle de lacet au-delà de 20° (0x0047AE29..0x0047AE64)
        # EN: Yaw angle confidence penalty above 20° (0x0047AE29..0x0047AE64)
        adj_conf = conf
        if abs(pan) > 20.0:
            p = (abs(pan) - 20.0) / 70.0
            if p > 1.0:
                p = 1.0
            adj_conf = conf * (1.0 - 0.5 * p)

        left_f = bx0 / float(img_w)
        top_f = by0 / float(img_h)
        right_f = bx1 / float(img_w)
        bottom_f = by1 / float(img_h)
        return left_f, top_f, right_f, bottom_f, adj_conf, roll

    def detect_and_extract_all(
        self,
        gray: np.ndarray,
        min_confidence: float = 0.2,
        *,
        min_size: int = 24,
        confidence_threshold: Optional[float] = None,
    ) -> List[RedDetectionResult]:
        """
        FR : Détecte les visages sur une image niveaux de gris `gray` (`uint8`, `H × W`),
        estime la position des yeux `(lx, ly, rx, ry)`, applique la géométrie de boîte
        englobante de `picasa3.exe @ 0x0047A778..0x0047AE64` et extrait le gabarit
        `vqc_Cue` de 1044 octets via le modèle `Root 4` de `red.cfg`.
        EN: Detect faces in a grayscale image `gray` (`uint8`, `H × W`), estimate eye
        positions `(lx, ly, rx, ry)`, apply the bounding-box geometry from
        `picasa3.exe @ 0x0047A778..0x0047AE64`, and extract the 1,044-byte `vqc_Cue`
        template via `Root 4` of `red.cfg`.
        """
        if confidence_threshold is not None:
            min_confidence = confidence_threshold

        h, w = gray.shape[:2]
        min_dim = max(24, int(min_size))
        if w < min_dim or h < min_dim:
            return []

        eq = cv2.equalizeHist(gray)
        # FR : Seuil de distance inter-oculaire minimale de Picasa : 20 px -> visage ~ 45 px
        # EN: Picasa minimum inter-ocular distance threshold: 20 px -> face ~ 45 px
        raw_boxes: List[Tuple[int, int, int, int, float, float]] = []

        frontal = self._frontal_cascade.detectMultiScale(
            eq,
            scaleFactor=1.12,
            minNeighbors=5,
            minSize=(max(min_dim, 36), max(min_dim, 36)),
        )
        for (x, y, bw, bh) in frontal:
            raw_boxes.append((int(x), int(y), int(bw), int(bh), 0.0, 0.85))

        if self._profile_cascade is not None and not raw_boxes:
            prof = self._profile_cascade.detectMultiScale(
                eq,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(max(min_dim, 40), max(min_dim, 40)),
            )
            for (x, y, bw, bh) in prof:
                raw_boxes.append((int(x), int(y), int(bw), int(bh), 35.0, 0.65))

        results: List[RedDetectionResult] = []
        for (x, y, bw, bh, pan_est, base_conf) in raw_boxes:
            # FR : Position initiale des yeux issue du graphe moyen vpf_EigenShapeMap (écart inter-oculaire = 22/80 = 0.275 * bw)
            # EN: Initial eye position from vpf_EigenShapeMap mean graph (inter-ocular spacing = 22/80 = 0.275 * bw)
            lx = x + 0.3625 * bw
            rx = x + 0.6375 * bw
            ly = y + 0.4790 * bh
            ry = y + 0.4790 * bh

            # FR : Affinage local des yeux dans la moitié supérieure du visage
            # EN: Local eye refinement in the upper half of the face
            if self._eye_cascade is not None and bw >= 64 and bh >= 64:
                roi_h = max(16, int(0.60 * bh))
                roi = eq[y : y + roi_h, x : x + bw]
                eyes = self._eye_cascade.detectMultiScale(
                    roi,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(max(8, bw // 10), max(8, bh // 10)),
                )
                if len(eyes) >= 2:
                    eyes_sorted = sorted(eyes, key=lambda e: e[0])
                    le = eyes_sorted[0]
                    re = eyes_sorted[-1]
                    cand_lx = x + le[0] + 0.5 * le[2]
                    cand_ly = y + le[1] + 0.5 * le[3]
                    cand_rx = x + re[0] + 0.5 * re[2]
                    cand_ry = y + re[1] + 0.5 * re[3]
                    cand_dist = math.hypot(cand_rx - cand_lx, cand_ry - cand_ly)
                    if 0.18 * bw <= cand_dist <= 0.55 * bw and abs(cand_ry - cand_ly) <= 0.25 * bh:
                        lx, ly, rx, ry = cand_lx, cand_ly, cand_rx, cand_ry

            eye_dist = math.hypot(rx - lx, ry - ly)
            if eye_dist < 10.0:
                continue

            left_f, top_f, right_f, bottom_f, adj_conf, roll = self.compute_picasa_eye_box(
                lx, ly, rx, ry, pan_est, base_conf, w, h
            )
            if adj_conf < min_confidence:
                continue

            blob, feat_vec = self.extract_vqc_cue_from_eyes(gray, lx, ly, rx, ry)
            results.append(
                RedDetectionResult(
                    left_norm=left_f,
                    top_norm=top_f,
                    right_norm=right_f,
                    bottom_norm=bottom_f,
                    confidence=adj_conf,
                    pan=pan_est,
                    roll=roll,
                    cue_blob_1044=blob,
                    feature_vec_2000=feat_vec,
                )
            )

        return results

    # Ref: Red.dll @ 0x101008E0 (vqc_Relator::relate) & 0x100FF050 (vqc_Relator::rawSim)
    def relate_cues(self, blob1: bytes, blob2: bytes) -> float:
        """
        FR : Calcule la similarité exacte `vqc_Relator::relate` (`0x101008E0`) entre deux blobs
        `vqc_Cue` de 1044 octets en utilisant les poids désérialisés depuis `Root 5` de `red.cfg`.
        EN: Compute the exact `vqc_Relator::relate` (`0x101008E0`) similarity between two
        1,044-byte `vqc_Cue` blobs using the weights deserialized from `Root 5` of `red.cfg`.
        """
        dec1 = decode_face_template_blob(blob1)
        dec2 = decode_face_template_blob(blob2)
        if dec1 is None or dec2 is None:
            return 0.0
        packed1, inv_norm1, _ = dec1
        packed2, inv_norm2, _ = dec2

        b1 = np.frombuffer(packed1, dtype=np.uint8)
        v1 = np.empty(2000, dtype=np.float32)
        v1[0::2] = (b1 & 0x0F).astype(np.float32) * 2.0 - 15.0
        v1[1::2] = ((b1 >> 4) & 0x0F).astype(np.float32) * 2.0 - 15.0

        b2 = np.frombuffer(packed2, dtype=np.uint8)
        v2 = np.empty(2000, dtype=np.float32)
        v2[0::2] = (b2 & 0x0F).astype(np.float32) * 2.0 - 15.0
        v2[1::2] = ((b2 >> 4) & 0x0F).astype(np.float32) * 2.0 - 15.0

        raw_dot = float(np.sum(v1 * v2 * self.model.relator_weights_2000) * 0.25)
        norm_dot = raw_dot * float(inv_norm1) * float(inv_norm2)
        lin = max(-30.0, min(30.0, self.model.relator_sim_factor * norm_dot + self.model.relator_sim_delta))
        return float(1.0 / (1.0 + math.exp(-lin)))
