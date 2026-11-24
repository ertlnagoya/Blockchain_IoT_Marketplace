"""Face detection shared by the image redactor and the vision analyzer.

Backends (``settings.face_detector``):

* ``yunet`` (default) -- OpenCV's YuNet CNN detector
  (``cv2.FaceDetectorYN``, model ``face_detection_yunet_2023mar.onnx``,
  MIT, vendored under ``publisher/models``). Returns a real confidence
  per face.
* ``haar`` -- the former frontal-face Haar cascade. Kept for comparison
  and for OpenCV builds without ``FaceDetectorYN``; OpenCV 5 removed
  ``CascadeClassifier``.

Why YuNet: the redacted output should pass the check a receiver or
auditor runs on it, i.e. a face detector should find nothing left to
blur. On 200 WIDER FACE val frames resized to 640 px (iw3ip-research
detectability study, 2026-11-24), YuNet still found a face in 62 outputs
of the Haar-based redactor and in 2 outputs of the YuNet-based one.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path


DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent / "models" / "face_detection_yunet_2023mar.onnx"
)
# OpenCV's default score threshold for YuNet; the study used the same.
YUNET_SCORE_THRESHOLD = 0.9
YUNET_NMS_THRESHOLD = 0.3
YUNET_TOP_K = 5000
# Minimum size for the Haar path (unchanged). YuNet detections are kept at
# any size: a small face left unblurred is a leak, not a saving.
HAAR_MIN_SIZE = 30
# Haar has no probability; keep the constant the analyzer reported before.
HAAR_CONFIDENCE = 0.85

BACKENDS = ("yunet", "haar")


class FaceDetectorError(Exception):
    """The detector could not be built (unknown backend, missing model,
    or an OpenCV build without the required class)."""


class FaceDetector:
    """``detect(img)`` returns ``[(x, y, w, h, score), ...]`` in pixels,
    clipped to the image, for a BGR ``numpy`` image."""

    def __init__(self, backend: str = "yunet", model_path: str | os.PathLike | None = None) -> None:
        import cv2  # type: ignore[import-not-found]

        self.backend = backend or "yunet"
        self._lock = threading.Lock()  # FaceDetectorYN keeps per-call input size
        if self.backend == "yunet":
            path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
            if not path.exists():
                raise FaceDetectorError(f"YuNet model not found at {path}")
            if not hasattr(cv2, "FaceDetectorYN"):
                raise FaceDetectorError(
                    f"OpenCV {cv2.__version__} has no FaceDetectorYN; need >= 4.5.4"
                )
            self._det = cv2.FaceDetectorYN.create(
                str(path), "", (320, 320),
                YUNET_SCORE_THRESHOLD, YUNET_NMS_THRESHOLD, YUNET_TOP_K,
            )
        elif self.backend == "haar":
            if not hasattr(cv2, "CascadeClassifier"):
                raise FaceDetectorError(
                    f"OpenCV {cv2.__version__} has no CascadeClassifier; use face_detector=yunet"
                )
            cascade = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            if not cascade.exists():
                raise FaceDetectorError(f"haar cascade not found at {cascade}; reinstall opencv")
            self._det = cv2.CascadeClassifier(str(cascade))
        else:
            raise FaceDetectorError(
                f"unknown face_detector={self.backend!r}; expected one of {BACKENDS}"
            )

    @property
    def name(self) -> str:
        return "YuNet (face_detection_yunet_2023mar)" if self.backend == "yunet" else "Haar cascade frontal-face"

    def detect(self, img) -> list[tuple[int, int, int, int, float]]:
        import cv2  # type: ignore[import-not-found]

        H, W = img.shape[:2]
        if self.backend == "yunet":
            with self._lock:
                self._det.setInputSize((W, H))
                _, rows = self._det.detect(img)
            raw = [] if rows is None else [(r[0], r[1], r[2], r[3], float(r[14])) for r in rows]
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            rects = self._det.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(HAAR_MIN_SIZE, HAAR_MIN_SIZE)
            )
            raw = [(x, y, w, h, HAAR_CONFIDENCE) for (x, y, w, h) in rects]

        out = []
        for x, y, w, h, s in raw:
            # YuNet boxes can start outside the frame; clip so callers can slice.
            x0, y0 = max(0, int(round(x))), max(0, int(round(y)))
            x1, y1 = min(W, int(round(x + w))), min(H, int(round(y + h)))
            if x1 <= x0 or y1 <= y0:
                continue
            out.append((x0, y0, x1 - x0, y1 - y0, s))
        return out


_cache: dict[tuple[str, str], FaceDetector] = {}
_cache_lock = threading.Lock()


def get_face_detector(backend: str = "yunet", model_path: str | os.PathLike | None = None) -> FaceDetector:
    """Process-wide detector per (backend, model path); building YuNet
    loads the ONNX model, so do it once."""
    key = (backend or "yunet", str(model_path or ""))
    with _cache_lock:
        if key not in _cache:
            _cache[key] = FaceDetector(key[0], model_path=model_path or None)
        return _cache[key]
