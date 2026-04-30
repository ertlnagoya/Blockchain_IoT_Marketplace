"""VLM client for the Stage T semantic-tier extension.

Backends:

* ``stub`` -- returns deterministic dummy strings keyed off the source
  URL's sha256. Used by tests and by `--profile vlm` smoke tests when
  no real model is connected. Never makes a network call.

* ``ollama`` -- placeholder. Will POST to OLLAMA_API_URL with the
  configured model (e.g. ``llava``). The actual HTTP wiring lands in
  the next PR (Δ3) so this skeleton can ship without dragging Ollama
  into the test environment. Today it raises ``VLMNotImplemented``.

The pipeline calls ``VLMClient.describe(image_url, content_type)`` and
expects either a dict with the four contract keys or a ``VLMError``
subclass. Anything else is a programming bug; never silently fall back
to a placeholder description because that bypasses the
``processing_warnings`` channel that lets receivers know they're
seeing a degraded result.

See ``docs/hands-on/data-user-vc-tiered-spec.md`` "Tier extension:
semantic-level redaction (VLM)" for the schema contract this module
implements.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class VLMError(Exception):
    """Base class for any VLM call failure. Pipeline catches this and
    marks the row with `processing_warnings: ["vlm_unavailable"]`."""


class VLMNotImplemented(VLMError):
    """Backend recognised but not wired in yet (e.g. ollama in Δ2)."""


class VLMUnknownBackend(VLMError):
    """``settings.vlm_backend`` doesn't match a known backend name."""


def _stub_descriptions(image_url: str, content_type: str) -> tuple[str, str]:
    """Deterministic dummy strings keyed off the source URL's sha256.

    Tests rely on this being stable: the same input always produces the
    same output, so projection assertions don't need to mock anything.

    The strings are obviously synthetic ("[stub] ..." prefix) so a
    receiver who somehow gets them in production immediately knows the
    publisher is mis-configured.
    """
    sha = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:8]
    full = (
        f"[stub VLM:{sha}] A person in a blue jacket is dropping a plastic "
        f"bottle near the park entrance. Source content-type: {content_type}."
    )
    summary = (
        f"[stub VLM:{sha}] An adult dropped a piece of litter near a public "
        f"location. Source content-type: {content_type}."
    )
    return full, summary


class VLMClient:
    """Thin client that turns an image URL into description_full +
    description_summary plus audit metadata.

    Construct via ``VLMClient.from_settings(settings)``; pass through
    `None` when the backend is empty so callers can branch on
    ``if vlm_client is not None`` without sprinkling settings checks.
    """

    def __init__(self, *, backend: str, api_url: str, model: str) -> None:
        self.backend = backend
        self.api_url = api_url
        self.model = model

    @classmethod
    def from_settings(cls, settings) -> "VLMClient | None":
        if not settings.vlm_backend:
            return None
        return cls(
            backend=settings.vlm_backend,
            api_url=settings.vlm_api_url,
            model=settings.vlm_model,
        )

    def describe(self, *, image_url: str, content_type: str) -> dict:
        """Return ``{description_full, description_summary,
        description_model, description_generated_at}``.

        Raises ``VLMError`` on any backend failure -- callers catch and
        emit ``processing_warnings: ["vlm_unavailable"]``.
        """
        if self.backend == "stub":
            full, summary = _stub_descriptions(image_url, content_type)
            return {
                "description_full": full,
                "description_summary": summary,
                "description_model": "stub-vlm/v0",
                "description_generated_at": datetime.now(timezone.utc).isoformat(),
            }
        if self.backend == "ollama":
            raise VLMNotImplemented(
                "ollama backend is wired in Δ3; configure VLM_BACKEND=stub for now"
            )
        raise VLMUnknownBackend(
            f"unknown vlm backend {self.backend!r}; expected one of: stub, ollama"
        )
