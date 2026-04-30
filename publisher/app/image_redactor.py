"""Image PII redactor for the Stage T semantic-tier extension.

Backends:

* ``stub`` -- returns the *same* URL marked with a `?redacted=stub`
  query string so tests / hands-on demos can exercise the pipeline
  without OpenCV. The marker makes it obvious in /platform/data that
  the receiver is looking at a placeholder, not a real blur.

* ``opencv`` -- placeholder. Will run Haar-cascade face detection +
  Gaussian blur and re-upload the result through the existing
  /media/upload path so the redacted image gets the same dedup +
  IPFS hooks the originals get. Wires up in Δ3.

Independent from VLM: face-blur doesn't need a multimodal model, so a
deployment can run blur alone without the description text. The
pipeline reads each backend separately and emits the corresponding
``processing_warnings`` entry on failure.

See ``docs/hands-on/data-user-vc-tiered-spec.md`` "Face / PII blur"
for the schema contract this module implements.
"""
from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


class RedactionError(Exception):
    """Base class for any redaction failure. Pipeline catches this and
    marks the row with `processing_warnings: ["redaction_unavailable"]`."""


class RedactionNotImplemented(RedactionError):
    """Backend recognised but not wired in yet."""


class RedactionUnknownBackend(RedactionError):
    """``settings.image_redaction_backend`` doesn't match a known name."""


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
            # Mark the URL so receivers can immediately tell this is a
            # placeholder, not a real blurred image. We don't host a
            # second media file; the test asserts the marker is present.
            sep = "&" if "?" in image_url else "?"
            return {
                "image_url_redacted": f"{image_url}{sep}redacted=stub",
                "image_cid_redacted": None,
            }
        if self.backend == "opencv":
            raise RedactionNotImplemented(
                "opencv backend is wired in Δ3; configure "
                "IMAGE_REDACTION_BACKEND=stub for now"
            )
        raise RedactionUnknownBackend(
            f"unknown image redactor backend {self.backend!r}; "
            f"expected one of: stub, opencv"
        )
