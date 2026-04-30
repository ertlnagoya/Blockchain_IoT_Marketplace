"""HTTP surface for the Stage T+ semantic-tier pipeline.

Two endpoints:

* ``POST /semantic/analyze``
    Multipart upload of a single frame. Returns the SIR JSON. Never
    echoes the frame bytes; the response is purely structured. The
    caller (typically the /provider page on iPhone Safari) is
    responsible for sampling -- this route does not throttle, but it
    does cap the request body size at the publisher's existing
    multipart limit.

* ``POST /semantic/render``
    Body: ``{ "trust_level": "anonymous|...", "sir": {...},
              "image_url": "..." }``. The publisher fetches
    ``image_url`` from its own /media/<sha>.<ext> store, runs the
    trust-aware renderer, and ships the resulting payload (text +
    optional masked image bytes inline as base64). For low-trust
    viewers no image bytes are attached at all -- the renderer
    enforces fail-closed regardless of what the caller asked for.

Both endpoints stay deliberately minimal: in production the actual
viewer route (`/viewer`) calls into the same renderer directly with
the ViewerToken context, so /semantic/* is mostly a dev affordance
to exercise the pipeline without round-tripping through the wallet
flow. Audit logging is the caller's responsibility -- when used
from a production code path, wrap with the existing audit_repo.write().

This module deliberately doesn't expose any way to short-circuit
the SemanticAnalyzer or to send raw frames to a low-trust viewer.
The entire point of the pipeline is that those guarantees are
unsidesteppable.
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from publisher.app.semantic_analyzer import (
    SemanticAnalyzer,
    SemanticAnalyzerError,
)
from publisher.app.sir_models import (
    SemanticIntermediateRepresentation,
    ViewerTrustLevel,
)
from publisher.app.trust_aware_renderer import TrustAwareRenderer
from publisher.app.trust_policy import OutputKind, TrustPolicyEngine


logger = logging.getLogger(__name__)


class _RenderRequest(BaseModel):
    """Body of POST /semantic/render."""

    trust_level: Optional[str] = Field(
        default=None,
        description=(
            "Viewer trust level. Unknown / missing values collapse to "
            "anonymous (fail-closed)."
        ),
    )
    sir: dict[str, Any] = Field(
        default_factory=dict,
        description="Semantic intermediate representation as JSON.",
    )
    image_url: Optional[str] = Field(
        default=None,
        description=(
            "Optional /media/<sha>.<ext> URL the publisher can fetch as "
            "the source frame. Omit when the caller wants text-only "
            "output. The renderer never returns image bytes for "
            "low-trust viewers, regardless of this field."
        ),
    )


class _RenderUrlRequest(BaseModel):
    """Body of POST /semantic/render_url. One-shot variant used by
    /viewer: instead of supplying an SIR, ask the publisher to fetch
    the URL, analyze it, and render in one call."""

    trust_level: Optional[str] = None
    image_url: str
    source_device_id: Optional[str] = None


def _serialize_rendered(out) -> dict[str, Any]:
    """Common JSON shape for /semantic/render and /semantic/render_url.
    Image bytes ride along as base64 only when actually produced; we
    never include the input source URL in the response so a leaked
    log line can't be replayed to fetch the original."""
    body: dict[str, Any] = {
        "trust_level": out.trust_level.value,
        "granted_kinds": [k.value for k in out.granted_kinds],
        "text_summary": out.text_summary,
        "event_list": list(out.event_list),
        "rationale": out.rationale,
        "audit_required": out.audit_required,
    }
    if out.image_bytes is not None:
        import base64
        body["image_b64"] = base64.b64encode(out.image_bytes).decode("ascii")
        body["image_content_type"] = out.image_content_type
    return body


def build_router(
    *,
    analyzer: SemanticAnalyzer,
    policy_engine: TrustPolicyEngine,
    renderer: TrustAwareRenderer,
) -> APIRouter:
    router = APIRouter()

    @router.post("/semantic/analyze")
    async def analyze(
        file: UploadFile = File(...),
        source_device_id: str = Form(default="unknown-device"),
    ) -> dict[str, Any]:
        """Run the configured analyzer on the uploaded frame, return the
        SIR. Never echoes the frame bytes."""
        body = await file.read()
        if not body:
            raise HTTPException(status_code=400, detail="empty_frame")
        try:
            sir = analyzer.analyze(image_bytes=body, source_device_id=source_device_id)
        except SemanticAnalyzerError as exc:
            logger.warning("semantic analyze failed: %s", exc)
            sir = SemanticIntermediateRepresentation.empty(
                frame_id="unanalysable",
                source_device_id=source_device_id,
                analyzer_version=getattr(analyzer, "name", "unknown"),
            )
        return sir.model_dump(mode="json")

    @router.post("/semantic/render_url")
    def render_url(req: _RenderUrlRequest) -> dict[str, Any]:
        """One-shot helper: fetch ``image_url``, analyze, render. Used
        by /viewer when it has a row's image_url and a trust level
        and just wants the trust-aware payload back. Saves the client
        a round trip vs calling /semantic/analyze + /semantic/render
        sequentially. Failures fall through to text-only output --
        the caller never gets raw frame bytes back."""
        if not req.image_url:
            raise HTTPException(status_code=400, detail="image_url_required")
        # Fetch source bytes. Same publisher-internal-only assumption
        # as /semantic/render: we don't follow arbitrary external URLs.
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(req.image_url)
                r.raise_for_status()
            image_bytes = r.content
            image_content_type = r.headers.get("content-type")
        except httpx.HTTPError as exc:
            logger.warning("/semantic/render_url fetch %s: %s", req.image_url, exc)
            # Fall through with empty bytes so the renderer demotes to
            # text using an empty SIR; receiver sees "analysis unavailable".
            sir = SemanticIntermediateRepresentation.empty(
                frame_id="fetch-failed",
                source_device_id="render-url",
                analyzer_version=getattr(analyzer, "name", "unknown"),
            )
            policy = policy_engine.evaluate_safe(viewer_trust=req.trust_level, sir=sir)
            out = renderer.render(sir=sir, policy=policy)
            return _serialize_rendered(out)

        # Analyze locally; analyzer failure becomes the empty-SIR
        # fail-closed shape, same as /semantic/analyze.
        try:
            sir = analyzer.analyze(
                image_bytes=image_bytes,
                source_device_id=req.source_device_id or "render-url",
            )
        except SemanticAnalyzerError as exc:
            logger.warning("/semantic/render_url analyze: %s", exc)
            sir = SemanticIntermediateRepresentation.empty(
                frame_id="analyze-failed",
                source_device_id=req.source_device_id or "render-url",
                analyzer_version=getattr(analyzer, "name", "unknown"),
            )

        policy = policy_engine.evaluate_safe(viewer_trust=req.trust_level, sir=sir)
        out = renderer.render(
            sir=sir,
            policy=policy,
            image_bytes=image_bytes,
            image_content_type=image_content_type,
        )
        return _serialize_rendered(out)

    @router.post("/semantic/render")
    def render(req: _RenderRequest) -> dict[str, Any]:
        """Apply the trust-aware policy + renderer to a SIR + optional
        source frame. Returns text/event/optional-base64 image. Image
        bytes are only attached when the policy permits an image kind
        AND the source bytes successfully fetched."""
        try:
            sir = SemanticIntermediateRepresentation.model_validate(req.sir or {})
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400, detail=f"invalid_sir: {type(exc).__name__}: {exc}"
            )

        # Optionally fetch the source bytes. Fetch failures are
        # treated as "no image available" -- the renderer demotes to
        # text. The fetcher hits *only* the publisher's own /media
        # path; we don't follow arbitrary external URLs here.
        image_bytes: Optional[bytes] = None
        image_content_type: Optional[str] = None
        if req.image_url:
            try:
                with httpx.Client(timeout=10.0) as client:
                    r = client.get(req.image_url)
                    r.raise_for_status()
                image_bytes = r.content
                image_content_type = r.headers.get("content-type")
            except httpx.HTTPError as exc:
                logger.warning("/semantic/render failed to fetch %s: %s", req.image_url, exc)

        policy = policy_engine.evaluate_safe(viewer_trust=req.trust_level, sir=sir)
        out = renderer.render(
            sir=sir,
            policy=policy,
            image_bytes=image_bytes,
            image_content_type=image_content_type,
        )
        return _serialize_rendered(out)

    return router
