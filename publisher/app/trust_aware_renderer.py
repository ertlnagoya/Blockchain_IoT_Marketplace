"""Trust-aware renderer: SIR + DisclosurePolicy -> ViewerOutput.

This module is the only place where the source frame bytes get
combined with the policy decision. Keep it that way -- if any other
module reads `image_bytes` and the policy together, that's a bypass
of the fail-closed guarantees.

Outputs the renderer can produce, parameterised by the policy's
``allowed_outputs``:

* ``textSummary``        -- the SIR's scene_summary, plus a list of
                            event descriptions. Always safe; works
                            even when the analyzer returned an empty
                            SIR.
* ``eventList``          -- structured events from the SIR. Mirror of
                            textSummary as JSON instead of prose.
* ``redactedImage``      -- bytes of the source frame with the policy's
                            mask_regions Gaussian-blurred at the
                            policy's blur_strength. Returns None if
                            cv2 isn't available -- the route should
                            then fall back to textSummary.
* ``lowResolutionImage`` -- like redactedImage but downsampled to a
                            small width and JPEG-recompressed. Hides
                            sub-mask details a low-res preview can't
                            convey.
* ``maskedVideoFrame``   -- alias of redactedImage at full resolution
                            (the kind exists separately so the policy
                            engine can grant it to HIGH but not to
                            MEDIUM).
* ``originalFrame``      -- the source bytes verbatim. Only emitted at
                            OWNER / ADMIN; the renderer refuses for any
                            other policy.

Every render method takes an explicit ``allow=...`` policy check at
the top. There is no path through this file that emits image bytes
without first asserting the policy permits the corresponding kind.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional

from publisher.app.sir_models import (
    SemanticIntermediateRepresentation,
    SensitiveRegion,
    ViewerTrustLevel,
)
from publisher.app.trust_policy import DisclosurePolicy, OutputKind


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderedOutput:
    """The complete envelope a route handler ships to a viewer.

    ``image_bytes`` and ``image_content_type`` are paired -- if
    bytes are present the content type must be too. The renderer
    leaves ``image_bytes`` None whenever the policy didn't grant any
    image kind, so a caller can do a single ``if image_bytes`` check
    to decide whether to send a multipart response.
    """

    trust_level: ViewerTrustLevel
    granted_kinds: frozenset[OutputKind]
    text_summary: str = ""
    event_list: tuple[dict, ...] = ()
    image_bytes: Optional[bytes] = None
    image_content_type: Optional[str] = None
    rationale: str = ""
    audit_required: bool = False


class TrustAwareRenderer:
    """Stateless. Construct once at startup, call ``render()`` per
    request. The renderer doesn't make network calls and doesn't
    persist anything."""

    #: Width to which lowResolutionImage downsamples. Keeps the
    #: preview small enough that masked-but-leaked details (a single
    #: pixel of unblurred face, a tiny corner of a screen) don't
    #: convey identifying info on their own.
    low_resolution_max_width: int = 256

    #: JPEG quality for the lowResolutionImage. Slightly lossy on
    #: purpose -- compression smooths the boundaries of mask blocks.
    low_resolution_jpeg_quality: int = 70

    def render(
        self,
        *,
        sir: SemanticIntermediateRepresentation,
        policy: DisclosurePolicy,
        image_bytes: Optional[bytes] = None,
        image_content_type: Optional[str] = None,
    ) -> RenderedOutput:
        """Compute the viewer-bound payload.

        ``image_bytes`` may be None even when the policy permits image
        kinds (e.g. the analyzer ran but the source frame wasn't
        retained for privacy reasons). In that case the image kinds
        are silently demoted; the caller sees ``image_bytes is None``
        on the result.
        """
        text_summary = self._render_text_summary(sir, policy)
        event_list = self._render_event_list(sir, policy)

        out_bytes: Optional[bytes] = None
        out_ct: Optional[str] = None

        # Original frame: only at OWNER / ADMIN, only when policy says
        # so, only when image bytes are actually present. Audit log
        # is the caller's responsibility (route handler).
        if (
            policy.allows(OutputKind.ORIGINAL_FRAME)
            and image_bytes is not None
            and policy.trust_level
            in (ViewerTrustLevel.OWNER, ViewerTrustLevel.ADMIN)
        ):
            out_bytes = image_bytes
            out_ct = image_content_type or "application/octet-stream"

        # Masked video frame (HIGH and above): full-resolution blur.
        elif policy.allows(OutputKind.MASKED_VIDEO_FRAME) and image_bytes is not None:
            out_bytes, out_ct = self._render_masked(
                image_bytes,
                image_content_type=image_content_type,
                regions=policy.mask_regions,
                blur_kernel=policy.blur_strength,
                downsample_to=None,
            )

        # Plain redacted image (MEDIUM): same blur, full resolution.
        elif policy.allows(OutputKind.REDACTED_IMAGE) and image_bytes is not None:
            out_bytes, out_ct = self._render_masked(
                image_bytes,
                image_content_type=image_content_type,
                regions=policy.mask_regions,
                blur_kernel=policy.blur_strength,
                downsample_to=None,
            )

        # Low-resolution image (MEDIUM): downsample first, then blur,
        # so the blur kernel covers proportionally more of the small
        # frame and stragglers near mask edges still get smoothed.
        elif (
            policy.allows(OutputKind.LOW_RESOLUTION_IMAGE)
            and image_bytes is not None
        ):
            out_bytes, out_ct = self._render_masked(
                image_bytes,
                image_content_type=image_content_type,
                regions=policy.mask_regions,
                blur_kernel=policy.blur_strength,
                downsample_to=self.low_resolution_max_width,
            )

        # If the policy permits image kinds but we couldn't actually
        # render an image (no bytes / cv2 unavailable / decode failed),
        # the result is text-only. The granted_kinds field still says
        # we'd have served images, so the caller can log the demotion.
        return RenderedOutput(
            trust_level=policy.trust_level,
            granted_kinds=policy.allowed_outputs,
            text_summary=text_summary,
            event_list=event_list,
            image_bytes=out_bytes,
            image_content_type=out_ct,
            rationale=policy.rationale,
            audit_required=policy.audit_required,
        )

    # ---------------------- internals ----------------------

    def _render_text_summary(
        self,
        sir: SemanticIntermediateRepresentation,
        policy: DisclosurePolicy,
    ) -> str:
        if not (
            policy.allows(OutputKind.TEXT_SUMMARY)
            or policy.allows(OutputKind.EVENT_LIST)
        ):
            return ""
        if sir.privacy_risk_score >= 0.95 and not sir.objects:
            # `SemanticIntermediateRepresentation.empty()` shape: no
            # detections, max risk. Don't make up a summary.
            return sir.scene_summary or "(分析できないため非表示)"

        # ANONYMOUS: avoid even the people-count phrasing the SIR
        # may have produced; condense to "movement detected" style.
        if policy.trust_level is ViewerTrustLevel.ANONYMOUS:
            if sir.events:
                return "; ".join(e.description for e in sir.events)
            return "イベントが検出されました" if sir.objects else "新しい情報はありません"

        return sir.scene_summary or "(scene_summary なし)"

    def _render_event_list(
        self,
        sir: SemanticIntermediateRepresentation,
        policy: DisclosurePolicy,
    ) -> tuple[dict, ...]:
        if not policy.allows(OutputKind.EVENT_LIST):
            return ()
        return tuple(
            {
                "type": e.type,
                "description": e.description,
                "confidence": e.confidence,
            }
            for e in sir.events
        )

    def _render_masked(
        self,
        image_bytes: bytes,
        *,
        image_content_type: Optional[str],
        regions: tuple[SensitiveRegion, ...],
        blur_kernel: int,
        downsample_to: Optional[int],
    ) -> tuple[Optional[bytes], Optional[str]]:
        """Apply mask regions and optionally downsample. Returns
        (bytes, content_type) or (None, None) when the operation
        cannot complete -- e.g. cv2 isn't installed, the source
        bytes don't decode, the encoder rejects the format. Callers
        treat (None, None) as "image kind silently demoted to text"."""
        try:
            import cv2  # type: ignore[import-not-found]
            import numpy as np  # type: ignore[import-not-found]
        except ImportError:
            logger.warning(
                "trust_aware_renderer: cv2/numpy unavailable; "
                "image render demoted to text"
            )
            return None, None

        try:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("trust_aware_renderer: cv2 could not decode source")
                return None, None
            h, w = img.shape[:2]

            # Apply a Gaussian blur to each masked region. We round
            # the kernel size up to the nearest odd number because cv2
            # rejects even kernels.
            ksize = blur_kernel if blur_kernel % 2 == 1 else blur_kernel + 1
            for r in regions:
                bbox = r.bbox.clamped()
                x = int(bbox.x * w)
                y = int(bbox.y * h)
                rw = int(bbox.width * w)
                rh = int(bbox.height * h)
                if rw <= 0 or rh <= 0:
                    continue
                roi = img[y : y + rh, x : x + rw]
                if roi.size == 0:
                    continue
                img[y : y + rh, x : x + rw] = cv2.GaussianBlur(roi, (ksize, ksize), 0)

            if downsample_to and w > downsample_to:
                scale = downsample_to / w
                new_w = downsample_to
                new_h = max(1, int(h * scale))
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Pick output format: always JPEG for low-res to benefit
            # from compression-induced edge smoothing; otherwise mirror
            # the source content_type when possible.
            if downsample_to is not None or (image_content_type or "").startswith(
                "image/jpeg"
            ):
                ok, buf = cv2.imencode(
                    ".jpg",
                    img,
                    [int(cv2.IMWRITE_JPEG_QUALITY), self.low_resolution_jpeg_quality],
                )
                ct = "image/jpeg"
            elif (image_content_type or "").startswith("image/png"):
                ok, buf = cv2.imencode(".png", img)
                ct = "image/png"
            else:
                ok, buf = cv2.imencode(".jpg", img)
                ct = "image/jpeg"

            if not ok:
                logger.warning("trust_aware_renderer: cv2 imencode failed")
                return None, None
            return buf.tobytes(), ct
        except Exception as exc:  # noqa: BLE001
            # Anything below cv2 is wrapped so the route doesn't 500.
            logger.warning("trust_aware_renderer mask error: %s", exc)
            return None, None
