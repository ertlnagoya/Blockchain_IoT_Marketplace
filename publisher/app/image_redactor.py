"""Image PII redactor for the Stage T semantic-tier extension.

Backends:

* ``stub`` -- returns the *same* URL marked with a `?redacted=stub`
  query string so tests / hands-on demos can exercise the pipeline
  without OpenCV. The marker makes it obvious in /platform/data that
  the receiver is looking at a placeholder, not a real blur.

* ``opencv`` -- runs Haar-cascade face detection + Gaussian blur on
  the source image bytes. The blurred result is POSTed back to
  /media/upload (which dedups on sha256 and optionally pushes to
  IPFS), so the redacted image gets the same delivery surface as the
  originals: receivers fetch via /media/<sha>.<ext> regardless of
  which tier they're on.

Independent from VLM: face-blur doesn't need a multimodal model, so a
deployment can run blur alone without the description text. The
pipeline reads each backend separately and emits the corresponding
``processing_warnings`` entry on failure.

See ``docs/hands-on/data-user-vc-tiered-spec.md`` "Face / PII blur"
for the schema contract this module implements.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx


logger = logging.getLogger(__name__)


# Default Gaussian kernel size for the blur. Odd numbers only
# (OpenCV requirement). 51 is empirically heavy enough that a
# downstream face detector won't re-identify the subject from the
# blurred output.
_BLUR_KSIZE = (51, 51)


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


def _opencv_blur_faces(image_bytes: bytes, *, ext: str) -> bytes:
    """Detect faces with a Haar cascade and Gaussian-blur each face
    region, returning the re-encoded image bytes.

    `ext` is the original file extension (e.g. `.jpg`, `.png`); we
    re-encode to the same format so downstream callers don't have to
    rewrite content_type. The MVP cascade only catches frontal faces
    -- profile / occluded / low-resolution faces will pass through.
    Documented as a future-work item in the spec.
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

    cascade_path = (
        Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    )
    if not cascade_path.exists():
        raise RedactionError(
            f"haar cascade not found at {cascade_path}; reinstall opencv"
        )
    cascade = cv2.CascadeClassifier(str(cascade_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    logger.info(
        "opencv_blur_faces detected=%d shape=%s",
        len(faces), img.shape,
    )
    for (x, y, w, h) in faces:
        roi = img[y : y + h, x : x + w]
        img[y : y + h, x : x + w] = cv2.GaussianBlur(roi, _BLUR_KSIZE, 0)

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

    def __init__(self, *, backend: str) -> None:
        self.backend = backend

    @classmethod
    def from_settings(cls, settings) -> "ImageRedactor | None":
        if not settings.image_redaction_backend:
            return None
        return cls(backend=settings.image_redaction_backend)

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

        blurred = _opencv_blur_faces(source_bytes, ext=ext)

        # POST back to the publisher's /media/upload to land the
        # redacted bytes under /media/<sha>.<ext> with dedup + IPFS.
        upload_endpoint = _media_upload_endpoint(image_url)
        meta = _post_to_media_upload(
            upload_endpoint=upload_endpoint,
            body=blurred,
            filename=f"redacted{ext}",
            content_type=content_type,
        )
        return {
            "image_url_redacted": meta.get("url"),
            "image_cid_redacted": meta.get("cid"),
        }
