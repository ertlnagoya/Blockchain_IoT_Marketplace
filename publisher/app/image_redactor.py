"""Image PII redactor for the Stage T semantic-tier extension.

Backends:

* ``stub`` -- returns the *same* URL marked with a `?redacted=stub`
  query string so tests / hands-on demos can exercise the pipeline
  without OpenCV. The marker makes it obvious in /platform/data that
  the receiver is looking at a placeholder, not a real blur.

* ``opencv`` -- runs face detection (YuNet by default, see
  face_detector.py) + Gaussian blur on the source image bytes. The
  blurred result is POSTed back to /media/upload (which dedups on sha256 and optionally pushes to
  IPFS), so the redacted image gets the same delivery surface as the
  originals: receivers fetch via /media/<sha>.<ext> regardless of
  which tier they're on.

Independent from VLM: face-blur doesn't need a multimodal model, so a
deployment can run blur alone without the description text. The
pipeline reads each backend separately and emits the corresponding
``processing_warnings`` entry on failure.

See ``docs/hands-on/data-user-vc-tiered-spec.md`` "Face / PII blur"
for the schema contract this module implements.

Stage P (P2): when a ``C2paProvenance`` that can sign is injected and
the source image carries a C2PA manifest, the opencv backend signs the
blurred bytes with a Tier 2 derivative manifest (capture as ingredient,
capture thumbnail / camera / sensor assertions redacted) before the
upload. The result then carries ``image_redacted_c2pa`` (the upload's
verification result) or ``provenance_derivation_failed`` when signing
failed and the blurred image went out unsigned.
"""
from __future__ import annotations

import logging
import os

import httpx

from publisher.app.blur_util import DEFAULT_MIN_KSIZE, blur_region
from publisher.app.face_detector import FaceDetectorError, get_face_detector


logger = logging.getLogger(__name__)


# Minimum Gaussian kernel size for the blur. The kernel grows with the
# face width (see blur_util): a fixed 51x51 kernel left faces wider than
# ~100 px recognisable (SFace rank-1 37.8% at 131 px, 80.6% at 192 px).
_BLUR_MIN_KSIZE = DEFAULT_MIN_KSIZE


class RedactionError(Exception):
    """Base class for any redaction failure. Pipeline catches this and
    marks the row with `processing_warnings: ["redaction_unavailable"]`."""


class RedactionNotImplemented(RedactionError):
    """Backend recognised but not wired in yet."""


class RedactionUnknownBackend(RedactionError):
    """``settings.image_redaction_backend`` doesn't match a known name."""


class RedactionDependencyMissing(RedactionError):
    """The opencv backend was selected but cv2 / numpy aren't installed.
    Surfaces as a clear message instead of a raw ImportError so the
    operator knows to add `opencv-python-headless` to the publisher
    image (or fall back to the stub backend in tests)."""


def _media_upload_endpoint(image_url: str) -> str:
    """Derive the publisher's /media/upload URL from a /media/<sha>.<ext>
    URL by stripping the trailing path segment. Lets the redactor reuse
    the same publisher instance that served the source image without
    needing a separate config flag."""
    return image_url.rsplit("/media/", 1)[0] + "/media/upload"


def _opencv_blur_faces(
    image_bytes: bytes,
    *,
    ext: str,
    detector: str = "yunet",
    model_path: str | None = None,
) -> bytes:
    """Detect faces (``detector``: ``yunet`` or ``haar``) and
    Gaussian-blur each face region, returning the re-encoded image bytes.

    `ext` is the original file extension (e.g. `.jpg`, `.png`); we
    re-encode to the same format so downstream callers don't have to
    rewrite content_type. Faces the detector misses pass through; see
    face_detector.py for how often that happens with each backend.
    """
    try:
        import cv2  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RedactionDependencyMissing(
            "opencv backend requires cv2 + numpy. Install "
            "`opencv-python-headless` in the publisher image, or set "
            "IMAGE_REDACTION_BACKEND=stub to skip blur for now."
        ) from exc

    # Decode the image into an OpenCV BGR array. cv2.imdecode handles
    # JPEG/PNG/WebP without a temp file.
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise RedactionError(
            f"opencv could not decode image (ext={ext}, bytes={len(image_bytes)})"
        )

    try:
        faces = get_face_detector(detector, model_path).detect(img)
    except FaceDetectorError as exc:
        raise RedactionError(str(exc)) from exc
    logger.info(
        "opencv_blur_faces detector=%s detected=%d shape=%s",
        detector, len(faces), img.shape,
    )
    for (x, y, w, h, _score) in faces:
        roi = img[y : y + h, x : x + w]
        img[y : y + h, x : x + w] = blur_region(roi, _BLUR_MIN_KSIZE)

    # Re-encode with the original extension. JPEG quality 90 keeps
    # the file small without obvious artefacts.
    encode_ext = ext if ext.startswith(".") else f".{ext}"
    encode_params = []
    if encode_ext.lower() in (".jpg", ".jpeg"):
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    ok, out = cv2.imencode(encode_ext, img, encode_params)
    if not ok:
        raise RedactionError(f"opencv re-encode failed for ext={encode_ext}")
    return out.tobytes()


def _post_to_media_upload(
    *, upload_endpoint: str, body: bytes, filename: str, content_type: str
) -> dict:
    """Send the redacted bytes to the publisher's /media/upload and
    return the response JSON ({url, sha256, cid, ipfs_gateway_url, ...}).

    Reuses the publisher's existing dedup + IPFS path so receivers
    fetch redacted images the same way they fetch originals."""
    files = {"file": (filename, body, content_type)}
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(upload_endpoint, files=files)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as exc:
        raise RedactionError(
            f"redacted upload to {upload_endpoint} failed: {exc}"
        ) from exc


class ImageRedactor:
    """Produce ``{image_url_redacted, image_cid_redacted}`` from a
    source image URL.

    Construct via ``ImageRedactor.from_settings(settings)``; pass
    through ``None`` when the backend is empty so callers can branch
    on ``if image_redactor is not None``.
    """

    def __init__(
        self,
        *,
        backend: str,
        provenance=None,
        face_detector: str = "yunet",
        face_detector_model_path: str | None = None,
    ) -> None:
        self.backend = backend
        self.provenance = provenance
        self.face_detector = face_detector
        self.face_detector_model_path = face_detector_model_path

    @classmethod
    def from_settings(cls, settings, provenance=None) -> "ImageRedactor | None":
        if not settings.image_redaction_backend:
            return None
        return cls(
            backend=settings.image_redaction_backend,
            provenance=provenance,
            face_detector=getattr(settings, "face_detector", "yunet"),
            face_detector_model_path=getattr(settings, "face_detector_model_path", "") or None,
        )

    def blur_pii(self, *, image_url: str, content_type: str) -> dict:
        """Return ``{image_url_redacted, image_cid_redacted}`` (the
        cid is None when the source wasn't IPFS-backed or the redactor
        backend doesn't run IPFS uploads).

        Raises ``RedactionError`` on failure -- the pipeline catches
        and emits ``processing_warnings: ["redaction_unavailable"]``.
        """
        # Video sources are not handled by the MVP redactor (frame
        # extraction + per-frame blur is future work). The Stage T spec
        # explicitly says Tier 2 video falls back to text-only.
        if content_type.startswith("video/"):
            raise RedactionNotImplemented(
                f"video redaction is future work; got content_type={content_type}"
            )

        if self.backend == "stub":
            sep = "&" if "?" in image_url else "?"
            return {
                "image_url_redacted": f"{image_url}{sep}redacted=stub",
                "image_cid_redacted": None,
            }
        if self.backend == "opencv":
            return self._blur_opencv(image_url=image_url, content_type=content_type)
        raise RedactionUnknownBackend(
            f"unknown image redactor backend {self.backend!r}; "
            f"expected one of: stub, opencv"
        )

    def _blur_opencv(self, *, image_url: str, content_type: str) -> dict:
        # Fetch the source image bytes.
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(image_url)
                r.raise_for_status()
                source_bytes = r.content
        except httpx.HTTPError as exc:
            raise RedactionError(f"failed to fetch {image_url}: {exc}") from exc

        # Pull the extension out of the URL so the OpenCV encoder
        # produces matching bytes (jpg -> JPEG, png -> PNG, etc).
        path = image_url.split("?", 1)[0]
        ext = os.path.splitext(path)[1] or ".jpg"

        blurred = _opencv_blur_faces(
            source_bytes,
            ext=ext,
            detector=self.face_detector,
            model_path=self.face_detector_model_path,
        )
        derivation_failed = False
        if self.provenance is not None and self.provenance.can_sign:
            source_c2pa = self.provenance.verify(source_bytes, content_type)
            if source_c2pa.present:
                try:
                    blurred = self.provenance.sign_tier2(
                        source=source_bytes,
                        derived=blurred,
                        content_type=content_type,
                        title=f"tier2{ext}",
                    )
                except Exception as exc:  # noqa: BLE001 - ship the unsigned blur
                    logger.warning("tier2 c2pa signing failed: %s", exc)
                    derivation_failed = True

        # POST back to the publisher's /media/upload to land the
        # redacted bytes under /media/<sha>.<ext> with dedup + IPFS.
        upload_endpoint = _media_upload_endpoint(image_url)
        meta = _post_to_media_upload(
            upload_endpoint=upload_endpoint,
            body=blurred,
            filename=f"redacted{ext}",
            content_type=content_type,
        )
        out = {
            "image_url_redacted": meta.get("url"),
            "image_cid_redacted": meta.get("cid"),
        }
        if meta.get("c2pa") is not None:
            out["image_redacted_c2pa"] = meta["c2pa"]
        if derivation_failed:
            out["provenance_derivation_failed"] = True
        return out
