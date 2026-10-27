"""
FR : Détection et reconnaissance faciale fidèle à Picasa 3.9 (`Red.dll` + `red.cfg` / `PurePythonRedEngine`).
EN: Face detection and recognition faithful to Picasa 3.9 (`Red.dll` + `red.cfg` / `PurePythonRedEngine`).

# Ref: picasa3.exe @ 0x00478D50 (Chargement de plugins\\Red.dll et résolution de RED_CreateInterface)
# Ref: picasa3.exe @ 0x00478EE0 (Initialisation du détecteur avec plugins\\red.cfg)
# Ref: picasa3.exe @ 0x0047A0C0 (Détection multi-angles via table de rotation @ 0x00ABDFA8)
# Ref: picasa3.exe @ 0x0047ADE0 (Calcul de la boîte englobante à partir des coordonnées d'yeux)
# Ref: picasa3.exe @ 0x008568C0 (Sérialisation et comparaison des signatures faciales vqc_Cue 1044 octets)
# Ref: Red.dll @ 0x100253A0 (Export RED_CreateInterface, version d'interface 2)

FR : Architecture :
`Red.dll` étant un binaire Windows PE 32 bits (i386) et l'interpréteur Python hôte étant 64 bits
(ou exécuté sous Linux / macOS), `PicasaFaceDetector` orchestre :
1. Sur Windows (`sys.platform == "win32"`) lorsque `Red.dll` et un compilateur 32 bits sont présents :
   un micro-processus pont 32 bits persistant (`red_bridge_x86.exe`) qui charge nativement
   `plugins\\Red.dll` et `plugins\\red.cfg` et communique par tube binaire (`stdin`/`stdout`).
2. Sur Linux / macOS (`sys.platform != "win32"`) ou lorsque `Red.dll` / `red_bridge_x86.exe` n'est pas
   disponible, ou lorsque l'utilisateur sélectionne le moteur `'python'` : basculement automatique et
   transparent vers `PurePythonRedEngine` (`picasa_py/faces/red_engine_py.py`) qui lit directement
   `ui/resources/plugins/red.cfg` (ou depuis le bundle PyInstaller `sys._MEIPASS`).

EN: Architecture:
Because `Red.dll` is a 32-bit Windows PE binary (i386) while the host Python interpreter is 64-bit
(or running on Linux / macOS), `PicasaFaceDetector` orchestrates:
1. On Windows (`sys.platform == "win32"`) when `Red.dll` and a 32-bit compiler are available:
   a persistent 32-bit bridge micro-process (`red_bridge_x86.exe`) that natively loads
   `plugins\\Red.dll` and `plugins\\red.cfg` and communicates over binary pipes (`stdin`/`stdout`).
2. On Linux / macOS (`sys.platform != "win32"`) or whenever `Red.dll` / `red_bridge_x86.exe` is
   unavailable, or when the `'python'` engine is selected: automatic and transparent fallback to
   `PurePythonRedEngine` (`picasa_py/faces/red_engine_py.py`) reading `ui/resources/plugins/red.cfg`
   (including from a frozen PyInstaller bundle via `sys._MEIPASS`).
"""

from __future__ import annotations

import math
import os
import struct
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageOps

from picasa_py.faces.facerect import FaceRect

if TYPE_CHECKING:
    from picasa_py.faces.red_engine_py import PurePythonRedEngine


# Ref: picasa3.exe @ 0x00478D50 ("plugins\\Red.dll", "plugins\\red.cfg")
def _get_candidate_plugin_dirs() -> list[Path]:
    """
    FR : Retourne la liste ordonnée des répertoires candidats contenant `red.cfg` et/ou `Red.dll`
    (variable d'environnement, bundle PyInstaller `_MEIPASS`, dépôt local `ui/resources/plugins`,
    et installation standard Windows de Picasa 3).
    EN: Return the ordered list of candidate directories containing `red.cfg` and/or `Red.dll`
    (environment variable, PyInstaller `_MEIPASS` bundle, local repository `ui/resources/plugins`,
    and standard Windows Picasa 3 installation paths).

    # Ref: picasa3.exe @ 0x00478D50 (Résolution du répertoire plugins\\Red.dll et plugins\\red.cfg)
    """
    candidates: list[Path] = []
    env_dir = os.environ.get("PICASA3_PLUGINS_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    # FR : Support des exécutables figés PyInstaller (sys._MEIPASS) multi-OS
    # EN: Multi-OS PyInstaller frozen executable bundle support (sys._MEIPASS)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_path = Path(meipass)
        candidates.extend(
            [
                meipass_path / "ui" / "resources" / "plugins",
                meipass_path / "resources" / "plugins",
                meipass_path / "plugins",
            ]
        )

    # FR : Ressources embarquées dans le dépôt (`ui/resources/plugins`)
    # EN: Embedded repository resources (`ui/resources/plugins`)
    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            repo_root / "ui" / "resources" / "plugins",
            Path("ui/resources/plugins"),
            Path("bin/plugins"),
            Path(r"C:\Program Files (x86)\Google\Picasa3\plugins"),
            Path(r"C:\Program Files\Google\Picasa3\plugins"),
        ]
    )
    return candidates


def _find_red_plugin_paths() -> tuple[Path | None, Path | None]:
    """
    FR : Localise `Red.dll` et `red.cfg` de manière indépendante à travers les répertoires candidats
    (y compris `ui/resources/plugins/red.cfg` et `sys._MEIPASS`), afin que `red.cfg` soit toujours
    trouvé sous Windows, Linux et macOS même si Picasa 3 n'est pas installé dans `C:\\Program Files (x86)`.
    EN: Independently locate `Red.dll` and `red.cfg` across candidate directories (including
    `ui/resources/plugins/red.cfg` and `sys._MEIPASS`), ensuring `red.cfg` is always found on
    Windows, Linux, and macOS even if Picasa 3 is not installed in `C:\\Program Files (x86)`.

    # Ref: picasa3.exe @ 0x00478D50 (Localisation de plugins\\Red.dll et plugins\\red.cfg)
    """
    dll_found: Path | None = None
    cfg_found: Path | None = None

    for base in _get_candidate_plugin_dirs():
        try:
            if dll_found is None:
                for dll_name in ("Red.dll", "red.dll"):
                    candidate_dll = base / dll_name
                    if candidate_dll.is_file():
                        dll_found = candidate_dll.resolve()
                        break
            if cfg_found is None:
                for cfg_name in ("red.cfg", "Red.cfg"):
                    candidate_cfg = base / cfg_name
                    if candidate_cfg.is_file():
                        cfg_found = candidate_cfg.resolve()
                        break
        except OSError:
            continue
        if dll_found is not None and cfg_found is not None:
            break

    return dll_found, cfg_found


def _ensure_bridge_executable() -> Path | None:
    """
    FR : Vérifie la présence de `red_bridge_x86.exe` (uniquement sous Windows `sys.platform == "win32"`)
    et le compile à la volée avec `i686-w64-mingw32-g++` si le binaire n'est pas encore compilé.
    Retourne `None` immédiatement sur Linux / macOS.
    EN: Check for `red_bridge_x86.exe` (only on Windows `sys.platform == "win32"`) and compile it
    on-the-fly with `i686-w64-mingw32-g++` if not yet built. Immediately returns `None` on Linux / macOS.

    # Ref: picasa3.exe @ 0x00478D50 (Chargement PE 32 bits de Red.dll via RED_CreateInterface)
    """
    if sys.platform != "win32":
        return None

    faces_dir = Path(__file__).resolve().parent
    exe_path = faces_dir / "red_bridge_x86.exe"
    cpp_path = faces_dir / "red_bridge_x86.cpp"

    if exe_path.is_file():
        return exe_path

    if not cpp_path.is_file():
        return None

    # FR : Tentative de compilation avec MinGW-w64 32 bits (WinLibs / MSYS2)
    # EN: Attempt compilation using 32-bit MinGW-w64 (WinLibs / MSYS2)
    compiler_candidates = [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / r"Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw32\bin\i686-w64-mingw32-g++.exe",
        Path(r"C:\msys64\mingw32\bin\i686-w64-mingw32-g++.exe"),
    ]
    compiler = next((c for c in compiler_candidates if c.is_file()), None)
    if compiler is None:
        return None

    env = os.environ.copy()
    env["PATH"] = str(compiler.parent) + os.pathsep + env.get("PATH", "")
    try:
        subprocess.run(
            [
                str(compiler),
                "-O2",
                "-static",
                "-static-libgcc",
                "-static-libstdc++",
                str(cpp_path),
                "-o",
                str(exe_path),
            ],
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        if exe_path.is_file():
            return exe_path
    except Exception:
        return None
    return None


# Ref: picasa3.exe @ 0x0048AABC..0x0048AE60 (FRSuggestionThreshold = 0x55/100 = 0.85, FRSuggestionSingleThreshold = 0x5A/100 = 0.90)
# Ref: picasa3.exe @ 0x0078A220, 0x00881CC2 (FRSortThreshold default = 0x55 = 85 -> 0.85)
FR_SUGGESTION_THRESHOLD: float = 0.85
FR_SUGGESTION_SINGLE_THRESHOLD: float = 0.90
FR_SORT_THRESHOLD: float = 0.85
FR_RECOMMEND_INCLUDE_LIMIT: float = 0.50
FR_RECOMMEND_SHOW_LIMIT: float = 0.70


class PicasaFaceDetector:
    """
    FR : Détecteur et extracteur d'empreintes faciales Picasa 3.9 supportant deux moteurs :
    1. `'native'` : pilote nativement `Red.dll` + `red.cfg` via le pont 32 bits `red_bridge_x86.exe`
       (disponible sous Windows 32/64 bits).
    2. `'python'` : exécute le moteur Python/NumPy pur `PurePythonRedEngine` (`red_engine_py.py`)
       qui désérialise directement les 2 281 657 octets de `red.cfg` (portable Windows / Linux / macOS).
    Si `sys.platform != "win32"` ou si le pont 32 bits `red_bridge_x86.exe` / `Red.dll` n'est pas
    disponible sur l'OS hôte, bascule automatiquement et de manière transparente sur `PurePythonRedEngine`.

    EN: Picasa 3.9 face detector and feature extractor supporting two execution engines:
    1. `'native'`: natively drives `Red.dll` + `red.cfg` via the 32-bit `red_bridge_x86.exe` bridge
       (available on 32/64-bit Windows).
    2. `'python'`: runs the pure Python/NumPy engine `PurePythonRedEngine` (`red_engine_py.py`)
       deserializing all 2,281,657 bytes of `red.cfg` directly (cross-platform Windows / Linux / macOS).
    If `sys.platform != "win32"` or if the 32-bit bridge `red_bridge_x86.exe` / `Red.dll` is unavailable
    on the host OS, automatically and transparently falls back to `PurePythonRedEngine`.

    # Ref: picasa3.exe @ 0x00478D50 (Wrapper C++ autour de RED_CreateInterface)
    # Ref: picasa3.exe @ 0x0047A0C0 (Pipeline complet de détection et filtrage de confiance)
    # Ref: picasa3.exe @ 0x008568C0 (Calcul de distance L2 et seuil de regroupement des visages)
    """

    # Ref: picasa3.exe @ 0x0047A4E0 (Seuil de confiance minimal par défaut = 0.25)
    DEFAULT_CONFIDENCE_THRESHOLD = 0.25
    _singleton_instance: PicasaFaceDetector | None = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get(cls) -> PicasaFaceDetector:
        """
        FR : Retourne l'instance singleton partagée de `PicasaFaceDetector`.
        EN: Return the shared singleton instance of `PicasaFaceDetector`.
        """
        if cls._singleton_instance is None:
            with cls._singleton_lock:
                if cls._singleton_instance is None:
                    cls._singleton_instance = cls()
        return cls._singleton_instance

    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD, engine: str | None = None) -> None:
        self.confidence_threshold = confidence_threshold
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._dll_path, self._cfg_path = _find_red_plugin_paths()
        self._exe_path = (
            _ensure_bridge_executable()
            if (sys.platform == "win32" and self._dll_path is not None and self._cfg_path is not None)
            else None
        )
        self._red_available = bool(
            sys.platform == "win32" and self._dll_path is not None and self._cfg_path is not None and self._exe_path is not None
        )
        self._py_engine: PurePythonRedEngine | None = None

        # FR : Lecture du moteur préféré depuis les préférences si non forcé explicitement
        # EN: Read preferred engine from preferences when not explicitly specified
        if engine is None:
            try:
                from picasa_py.db.preferences import PicasaPreferences

                engine = PicasaPreferences.get_face_engine()
            except Exception:
                engine = "native"
        self._engine = "python" if engine == "python" else "native"

    def get_engine(self) -> str:
        """
        FR : Retourne le moteur actuellement sélectionné (`'native'` ou `'python'`).
        EN: Return the currently configured engine (`'native'` or `'python'`).
        """
        return self._engine

    def get_effective_engine(self) -> str:
        """
        FR : Retourne le moteur effectivement utilisé sur l'OS hôte (`'python'` si `sys.platform != "win32"`
        ou si `Red.dll` / `red_bridge_x86.exe` est indisponible).
        EN: Return the effective engine used on the host OS (`'python'` when `sys.platform != "win32"`
        or when `Red.dll` / `red_bridge_x86.exe` is unavailable).
        """
        if self._engine == "python" or sys.platform != "win32" or not self._red_available:
            return "python"
        return "native"

    def set_engine(self, engine: str) -> None:
        """
        FR : Bascule dynamiquement entre le moteur natif (`'native'`, `Red.dll`) et le moteur
        Python pur (`'python'`, `PurePythonRedEngine`).
        EN: Dynamically switch between the native engine (`'native'`, `Red.dll`) and the pure
        Python engine (`'python'`, `PurePythonRedEngine`).
        """
        with self._lock:
            self._engine = "python" if engine == "python" else "native"

    def _ensure_py_engine_locked(self) -> PurePythonRedEngine | None:
        """
        FR : Initialise paresseusement `PurePythonRedEngine` à partir de `red.cfg` (verrou `_lock` acquis).
        EN: Lazily initialize `PurePythonRedEngine` from `red.cfg` (with `_lock` held).
        """
        if self._py_engine is not None:
            return self._py_engine
        try:
            from picasa_py.faces.red_engine_py import PurePythonRedEngine

            self._py_engine = PurePythonRedEngine(self._cfg_path)
            return self._py_engine
        except Exception:
            return None

    def _ensure_process_locked(self) -> bool:
        """
        FR : Démarre le processus 32 bits `red_bridge_x86.exe` s'il n'est pas déjà actif
        (uniquement sous Windows `sys.platform == "win32"`).
        EN: Start the 32-bit `red_bridge_x86.exe` bridge process if not already running
        (only on Windows `sys.platform == "win32"`).
        """
        if sys.platform != "win32" or not self._red_available:
            return False
        if self._proc is not None and self._proc.poll() is None:
            return True

        try:
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | 0x00004000
                if os.name == "nt"
                else 0
            )
            self._proc = subprocess.Popen(
                [str(self._exe_path), str(self._dll_path), str(self._cfg_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            assert self._proc.stdout is not None
            magic = self._proc.stdout.read(4)
            # Ref: red_bridge_x86.exe @ RedBridge.Main il_offset 610..626 (écrit int32(1) = b"\x01\x00\x00\x00" au démarrage)
            if magic not in (b"\x01\x00\x00\x00", b"RED2"):
                self.close()
                return False
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        """
        FR : Ferme proprement le processus pont 32 bits `red_bridge_x86.exe`.
        EN: Cleanly terminate the 32-bit `red_bridge_x86.exe` bridge process.
        """
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    # Ref: red_bridge_x86.exe @ RedBridge.Main il_offset 707..728 (width <= 0 -> arrêt propre vt[1])
                    self._proc.stdin.write(struct.pack("<iif", 0, 0, 0.0))
                    self._proc.stdin.flush()
                    self._proc.stdin.close()
            except Exception:
                pass
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                pass
            self._proc = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    @staticmethod
    def _read_exact(stream, n: int) -> bytes:
        """
        FR : Lit exactement `n` octets depuis le flux binaire du pont IPC.
        EN: Read exactly `n` bytes from the IPC bridge binary stream.
        """
        buf = bytearray()
        while len(buf) < n:
            chunk = stream.read(n - len(buf))
            if not chunk:
                raise EOFError("Pont Red.dll interrompu / Red.dll bridge stream closed")
            buf.extend(chunk)
        return bytes(buf)

    # ------------------------------------------------------------------
    # FR : 1. Détection de visages + extraction simultanée des gabarits 1044 octets
    # EN: 1. Face detection + simultaneous extraction of 1044-byte templates
    # ------------------------------------------------------------------
    # Ref: picasa3.exe @ 0x0047A0C0 (Détection multi-échelles + calcul rect64 + extraction vqc_Cue)
    def detect_faces_in_image(
        self,
        img_or_path: str | Path | Image.Image,
    ) -> list[FaceRect]:
        """
        FR : Détecte tous les visages présents dans l'image en utilisant :
        - soit `Red.dll` + `red.cfg` natif (`engine == 'native'` sous Windows),
        - soit `PurePythonRedEngine` (`engine == 'python'`, ou basculement automatique sur Linux/macOS
          ou si le pont 32 bits `red_bridge_x86.exe` est indisponible).
        Retourne une liste de `FaceRect` avec coordonnées normalisées `[0.0, 1.0]`
        et le vecteur caractéristique déquantifié + gabarit 1 044 octets `vqc_Cue`.

        EN: Detect all faces in the image using:
        - either native `Red.dll` + `red.cfg` (`engine == 'native'` on Windows),
        - or `PurePythonRedEngine` (`engine == 'python'`, or automatic fallback on Linux/macOS
          or when the 32-bit `red_bridge_x86.exe` bridge is unavailable).
        Returns a list of `FaceRect` instances with normalized `[0.0, 1.0]` coordinates,
        dequantized feature vector, and 1,044-byte `vqc_Cue` template blob.
        """
        try:
            if isinstance(img_or_path, (str, Path)):
                with Image.open(img_or_path) as raw_img:
                    try:
                        exif_orient = raw_img.getexif().get(0x0112, 1)
                    except Exception:
                        exif_orient = 1
                    if raw_img.format == "JPEG" and max(raw_img.size) > 1024:
                        try:
                            raw_img.draft("L" if exif_orient == 1 else "RGB", (1024, 1024))
                        except Exception:
                            pass
                    if exif_orient and exif_orient != 1:
                        pil_img = ImageOps.exif_transpose(raw_img).convert("L")
                    else:
                        pil_img = raw_img.convert("L")
            else:
                pil_img = img_or_path.convert("L")
        except Exception:
            return []

        orig_w, orig_h = pil_img.size
        if orig_w < 24 or orig_h < 24:
            return []

        # Ref: picasa3.exe @ 0x00479F40 (Redimensionnement proportionnel max 1024 px avant passe Red.dll)
        max_dim = 1024
        if max(orig_w, orig_h) > max_dim:
            scale = max_dim / float(max(orig_w, orig_h))
            det_w = max(24, int(round(orig_w * scale)))
            det_h = max(24, int(round(orig_h * scale)))
            det_img = pil_img.resize((det_w, det_h), Image.Resampling.BILINEAR)
        else:
            det_w, det_h = orig_w, orig_h
            det_img = pil_img

        gray = np.asarray(det_img, dtype=np.uint8)
        gray = np.ascontiguousarray(gray)

        with self._lock:
            # FR : Si le moteur Python pur est sélectionné, ou sur Linux/macOS, ou si le pont natif 32 bits est absent
            # EN: When the pure Python engine is selected, on Linux/macOS, or when the 32-bit native bridge is unavailable
            use_python_engine = (self._engine == "python") or (sys.platform != "win32") or (not self._ensure_process_locked())
            if use_python_engine:
                py_eng = self._ensure_py_engine_locked()
                if py_eng is None:
                    return []
                dets = py_eng.detect_and_extract_all(
                    gray,
                    min_size=24,
                    confidence_threshold=self.confidence_threshold,
                )
                results_py: list[FaceRect] = []
                for det in dets:
                    fr = FaceRect(
                        left=det.left_norm,
                        top=det.top_norm,
                        right=det.right_norm,
                        bottom=det.bottom_norm,
                        contact_id="",
                        contact_name="",
                        feature_vector=det.feature_vec_2000,
                    )
                    fr.template_blob = det.cue_blob_1044  # type: ignore[attr-defined]
                    bw_py = max(0.0, float(det.right_norm) - float(det.left_norm))
                    bh_py = max(0.0, float(det.bottom_norm) - float(det.top_norm))
                    fr.confidence = float(det.confidence)  # type: ignore[attr-defined]
                    fr.pan = float(det.pan)  # type: ignore[attr-defined]
                    fr.leye = (float(det.left_norm) + 0.3625 * bw_py, float(det.top_norm) + 0.4790 * bh_py)  # type: ignore[attr-defined]
                    fr.reye = (float(det.left_norm) + 0.6375 * bw_py, float(det.top_norm) + 0.4790 * bh_py)  # type: ignore[attr-defined]
                    fr.mouth = (float(det.left_norm) + 0.5000 * bw_py, float(det.top_norm) + 0.7500 * bh_py)  # type: ignore[attr-defined]
                    results_py.append(fr)
                return results_py

            try:
                assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
                # Ref: red_bridge_x86.exe @ RedBridge.Main il_offset 668..706 (12 octets : int32 w, int32 h, float32 min_conf)
                header = struct.pack("<iif", int(det_w), int(det_h), float(self.confidence_threshold))
                self._proc.stdin.write(header)
                self._proc.stdin.write(gray.tobytes())
                self._proc.stdin.flush()

                count_bytes = self._read_exact(self._proc.stdout, 4)
                (num_faces,) = struct.unpack("<i", count_bytes)

                results: list[FaceRect] = []
                for _ in range(max(0, num_faces)):
                    # Ref: red_bridge_x86.exe @ RedBridge.Main il_offset 2082..2224
                    # 7 floats (left_norm, top_norm, right_norm, bottom_norm, conf, pan, roll) + int32 blob_len = 32 octets
                    meta = self._read_exact(self._proc.stdout, 32)
                    l_f, t_f, r_f, b_f, conf, _pan, _roll, blob_len = struct.unpack("<7fi", meta)
                    blob = self._read_exact(self._proc.stdout, blob_len) if blob_len > 0 else b""

                    if conf < self.confidence_threshold:
                        continue
                    if (r_f - l_f) <= 0.01 or (b_f - t_f) <= 0.01:
                        continue

                    feat_vec = self.cue_blob_to_feature_vector(blob) if len(blob) == 1044 else None
                    fr = FaceRect(
                        left=float(l_f),
                        top=float(t_f),
                        right=float(r_f),
                        bottom=float(b_f),
                        contact_id="",
                        contact_name="",
                        feature_vector=feat_vec,
                    )
                    # FR : Conserver aussi le blob brut 1044 octets pour l'écriture dans thumbs_index.db
                    # EN: Also retain the raw 1044-byte blob for writing into thumbs_index.db
                    fr.template_blob = blob  # type: ignore[attr-defined]
                    bw_n = max(0.0, float(r_f) - float(l_f))
                    bh_n = max(0.0, float(b_f) - float(t_f))
                    fr.confidence = float(conf)  # type: ignore[attr-defined]
                    fr.pan = float(_pan)  # type: ignore[attr-defined]
                    fr.roll = float(_roll)  # type: ignore[attr-defined]
                    fr.leye = (float(l_f) + 0.3625 * bw_n, float(t_f) + 0.4790 * bh_n)  # type: ignore[attr-defined]
                    fr.reye = (float(l_f) + 0.6375 * bw_n, float(t_f) + 0.4790 * bh_n)  # type: ignore[attr-defined]
                    fr.mouth = (float(l_f) + 0.5000 * bw_n, float(t_f) + 0.7500 * bh_n)  # type: ignore[attr-defined]
                    results.append(fr)
                return results
            except Exception:
                self.close()
                # FR : Repli automatique sur PurePythonRedEngine en cas d'erreur du processus 32 bits
                # EN: Automatic fallback to PurePythonRedEngine if the 32-bit bridge process fails
                py_eng = self._ensure_py_engine_locked()
                if py_eng is not None:
                    dets = py_eng.detect_and_extract_all(
                        gray,
                        min_size=24,
                        confidence_threshold=self.confidence_threshold,
                    )
                    fallback_results: list[FaceRect] = []
                    for det in dets:
                        fr = FaceRect(
                            left=det.left_norm,
                            top=det.top_norm,
                            right=det.right_norm,
                            bottom=det.bottom_norm,
                            contact_id="",
                            contact_name="",
                            feature_vector=det.feature_vec_2000,
                        )
                        fr.template_blob = det.cue_blob_1044  # type: ignore[attr-defined]
                        bw_fb = max(0.0, float(det.right_norm) - float(det.left_norm))
                        bh_fb = max(0.0, float(det.bottom_norm) - float(det.top_norm))
                        fr.confidence = float(det.confidence)  # type: ignore[attr-defined]
                        fr.pan = float(det.pan)  # type: ignore[attr-defined]
                        fr.leye = (float(det.left_norm) + 0.3625 * bw_fb, float(det.top_norm) + 0.4790 * bh_fb)  # type: ignore[attr-defined]
                        fr.reye = (float(det.left_norm) + 0.6375 * bw_fb, float(det.top_norm) + 0.4790 * bh_fb)  # type: ignore[attr-defined]
                        fr.mouth = (float(det.left_norm) + 0.5000 * bw_fb, float(det.top_norm) + 0.7500 * bh_fb)  # type: ignore[attr-defined]
                        fallback_results.append(fr)
                    return fallback_results
                return []

    def detect_faces_in_file(self, file_path: str | Path) -> list[FaceRect]:
        """
        FR : Alias de `detect_faces_in_image` acceptant un chemin de fichier sur disque.
        EN: Alias for `detect_faces_in_image` accepting an on-disk file path.

        # Ref: picasa3.exe @ 0x0087ECD6 (BgFaceDetectThread -> detect_faces_in_file)
        """
        return self.detect_faces_in_image(file_path)

    # ------------------------------------------------------------------
    # FR : 2. Extraction d'empreinte faciale 1044 octets (vqc_Cue) sur un crop existant
    # EN: 2. 1044-byte face template (vqc_Cue) extraction on an existing crop
    # ------------------------------------------------------------------
    # Ref: picasa3.exe @ 0x0047AD70 (Extraction vqc_Cue à partir des coordonnées d'yeux dans la boîte)
    # Ref: Red.dll @ 0x100237B0 (vqc_LinearQuantizer::quantize -> 2000 nibbles 4-bit = 1000 octets)
    @staticmethod
    def cue_blob_to_feature_vector(blob: bytes) -> list[float] | None:
        """
        FR : Décode un blob `vqc_Cue` de 1 044 octets (en-tête 44 octets + 1 000 octets = 2 000 nibbles 4-bit)
        en un vecteur pondéré de 2 000 composantes :
        `v_i = (2 * n_i - 15) * inv_norm * 0.5 * sqrt(w_i)`
        compatible avec le produit scalaire et la sigmoïde `vqc_Relator::sim` (`Red.dll @ 0x10100A10`).
        EN: Decode a 1,044-byte `vqc_Cue` blob (44-byte header + 1,000 bytes = 2,000 4-bit nibbles)
        into a 2,000-element weighted vector:
        `v_i = (2 * n_i - 15) * inv_norm * 0.5 * sqrt(w_i)`
        compatible with dot product and `vqc_Relator::sim` sigmoid scoring (`Red.dll @ 0x10100A10`).

        # Ref: Red.dll @ 0x100237B0, 0x100FF050 (vqc_Relator::rawSim), 0x10100A10 (vqc_Relator::sim)
        """
        if not blob or len(blob) != 1044:
            return None
        from picasa_py.db.database import PicasaDatabase

        vec = PicasaDatabase.decode_vqc_cue_vector(blob)
        if vec is not None:
            return vec.tolist()

        # Fallback pour un blob 1044 octets dont le checksum d'en-tête n'est pas finalisé
        inv_norm = struct.unpack_from("<f", blob, 28)[0]
        packed_1000 = blob[44:1044]
        if not math.isfinite(inv_norm) or inv_norm <= 1e-6:
            inv_norm = PicasaDatabase.compute_vqc_cue_inv_norm(packed_1000)
        sqrt_w, _ = PicasaDatabase._get_vqc_relator_weights()
        payload = np.frombuffer(packed_1000, dtype=np.uint8)
        vals = np.empty(2000, dtype=np.float32)
        vals[0::2] = (payload & 0x0F).astype(np.float32) * 2.0 - 15.0
        vals[1::2] = ((payload >> 4) & 0x0F).astype(np.float32) * 2.0 - 15.0
        weighted = vals * (float(inv_norm) * sqrt_w)
        return weighted.tolist()

    def extract_cue_blob_from_crop(self, face_crop: Image.Image) -> bytes | None:
        """
        FR : Extrait le blob binaire `vqc_Cue` de 1 044 octets à partir d'une vignette de visage
        déjà découpée suivant le rectangle Picasa (`rect64`).
        Dans le système de coordonnées de la boîte Picasa (`[-1.60, +1.60]` en X et `[-1.84, +2.00]` en Y
        autour du centre des yeux, d'où largeur = `3.20 * d_eyes` et hauteur = `3.84 * d_eyes`),
        l'œil gauche se trouve à `(1.10 / 3.20, 1.84 / 3.84)` et l'œil droit à `(2.10 / 3.20, 1.84 / 3.84)`.

        EN: Extract the 1,044-byte binary `vqc_Cue` blob from a face thumbnail already cropped
        according to a Picasa face rectangle (`rect64`).
        In the Picasa eye-box coordinate system (`[-1.60, +1.60]` in X and `[-1.84, +2.00]` in Y
        around the eye midpoint, so width = `3.20 * d_eyes` and height = `3.84 * d_eyes`),
        the left eye is at `(1.10 / 3.20, 1.84 / 3.84)` and the right eye at `(2.10 / 3.20, 1.84 / 3.84)`.

        # Ref: picasa3.exe @ 0x0047ADE0 (Géométrie [-1.60, +1.60] x [-1.84, +2.00] autour des yeux)
        """
        gray_img = face_crop.convert("L").resize((160, 192), Image.Resampling.BILINEAR)
        gray = np.ascontiguousarray(np.asarray(gray_img, dtype=np.uint8))
        w, h = 160, 192
        lx = w * (1.10 / 3.20)
        rx = w * (2.10 / 3.20)
        ly = h * (1.84 / 3.84)
        ry = ly

        with self._lock:
            py_eng = self._ensure_py_engine_locked()
            if py_eng is None:
                return None
            blob, _vec = py_eng.extract_vqc_cue_from_eyes(gray, lx, ly, rx, ry)
            return blob

    def compute_face_feature(self, face_crop: Image.Image) -> list[float] | None:
        """
        FR : Calcule le vecteur caractéristique de 2 000 dimensions issu de `vqc_Cue` (1 044 octets)
        pour un visage découpé.
        EN: Compute the 2,000-dimensional feature vector derived from `vqc_Cue` (1,044 bytes)
        for a cropped face image.
        """
        blob = self.extract_cue_blob_from_crop(face_crop)
        if blob is not None:
            return self.cue_blob_to_feature_vector(blob)
        return None

    # ------------------------------------------------------------------
    # FR : 3. Comparaison de deux signatures faciales (vqc_Relator::relate / cosinus)
    # EN: 3. Face signature comparison (vqc_Relator::relate / cosine similarity)
    # ------------------------------------------------------------------
    # Ref: Red.dll @ 0x10023950 (vqc_Relator::relate)
    # Ref: picasa3.exe @ 0x008568C0 (Comparaison de gabarits faciaux)
    def compare_cue_blobs(self, blob_a: bytes, blob_b: bytes) -> float:
        """
        FR : Compare deux blobs `vqc_Cue` de 1 044 octets via `vqc_Relator::relate` de `Red.dll`
        (`PurePythonRedEngine.relate_cues`, équivalent bit-à-bit à `Red.dll @ 0x10100A10`).
        EN: Compare two 1,044-byte `vqc_Cue` blobs via `Red.dll`'s `vqc_Relator::relate`
        (`PurePythonRedEngine.relate_cues`, bit-exact equivalent of `Red.dll @ 0x10100A10`).
        """
        if len(blob_a) != 1044 or len(blob_b) != 1044:
            return 0.0
        with self._lock:
            py_eng = self._ensure_py_engine_locked()
            if py_eng is not None:
                return py_eng.relate_cues(blob_a, blob_b)
            return 0.0

    @staticmethod
    def compare_face_features(feat_a: list[float] | np.ndarray | None, feat_b: list[float] | np.ndarray | None) -> float:
        """
        FR : Calcule la similarité `vqc_Relator::sim` (`1.0 / (1.0 + exp(-(13.5 * dot - 0.45)))`)
        entre deux vecteurs d'empreintes `vqc_Cue` de 2 000 dimensions (ou la similarité cosinus
        pour les vecteurs d'autre dimension). Retourne un score dans `[0.0, 1.0]`.
        EN: Compute `vqc_Relator::sim` similarity (`1.0 / (1.0 + exp(-(13.5 * dot - 0.45)))`)
        between two 2,000-dimensional `vqc_Cue` feature vectors (or cosine similarity
        for vectors of other dimensions). Returns a score in `[0.0, 1.0]`.

        # Ref: Red.dll @ 0x10100A10 (vqc_Relator::sim), picasa3.exe @ 0x008568C0
        """
        if feat_a is None or feat_b is None or len(feat_a) == 0 or len(feat_a) != len(feat_b):
            return 0.0
        va = np.asarray(feat_a, dtype=np.float32).ravel()
        vb = np.asarray(feat_b, dtype=np.float32).ravel()
        dot = float(np.dot(va, vb))
        if va.size == 2000 and vb.size == 2000:
            lin = max(-30.0, min(30.0, 13.5 * dot - 0.45))
            return float(1.0 / (1.0 + math.exp(-lin)))
        na = float(np.linalg.norm(va))
        nb = float(np.linalg.norm(vb))
        if na <= 1e-12 or nb <= 1e-12:
            return 0.0
        return max(0.0, min(1.0, float(dot / (na * nb))))
