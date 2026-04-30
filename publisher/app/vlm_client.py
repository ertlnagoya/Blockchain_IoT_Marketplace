"""VLM client for the Stage T semantic-tier extension.

Backends:

* ``stub`` -- returns deterministic dummy strings keyed off the source
  URL's sha256. Used by tests and by `--profile vlm` smoke tests when
  no real model is connected. Never makes a network call.

* ``ollama`` -- POST to OLLAMA_API_URL with the configured multimodal
  model (e.g. ``llava``). Two-stage prompting: one prompt produces the
  named-entities-included `description_full`, a second prompt produces
  the PII-redacted `description_summary`. Both share the same image
  base64 payload (one fetch, two inferences). Network / model errors
  raise ``VLMError`` so the pipeline can emit
  ``processing_warnings: ["vlm_unavailable"]`` and keep publishing.

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

import base64
import hashlib
import logging
from datetime import datetime, timezone

import httpx


logger = logging.getLogger(__name__)


# Two-stage prompts. The full prompt keeps named entities, the summary
# prompt actively scrubs them. ASCII-only so they round-trip through
# Ollama's JSON API without escaping surprises.
_PROMPT_FULL = (
    "Describe what is happening in this image as factually as possible. "
    "Include any visible text, names of people if you can read name tags, "
    "specific objects, brands, license plates, and locations. "
    "Reply in 2-3 sentences."
)
_PROMPT_SUMMARY = (
    "Summarize what is happening in this image WITHOUT identifying any "
    "individual person, organization, named place, license plate, "
    "vehicle make/model, or readable text. Use only generic terms like "
    "'an adult', 'a vehicle', 'a public location'. Reply in 1-2 sentences."
)

# Network budget. Ollama's first request after cold start can take a
# while as the model warms; subsequent calls are fast. We keep the
# timeout generous so the first-publish UX isn't a misleading
# `vlm_unavailable` warning. The pipeline catches the timeout and
# degrades gracefully if it does fire.
_OLLAMA_TIMEOUT_SEC = 60.0


class VLMError(Exception):
    """Base class for any VLM call failure. Pipeline catches this and
    marks the row with `processing_warnings: ["vlm_unavailable"]`."""


class VLMNotImplemented(VLMError):
    """Backend recognised but not wired in yet."""


class VLMUnknownBackend(VLMError):
    """``settings.vlm_backend`` doesn't match a known backend name."""


def _stub_descriptions(image_url: str, content_type: str) -> tuple[str, str]:
    """Deterministic dummy strings keyed off the source URL's sha256.

    Tests rely on this being stable: the same input always produces the
    same output, so projection assertions don't need to mock anything.
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


def _fetch_image_b64(image_url: str, *, timeout: float = 10.0) -> str:
    """Download the image and return its base64-encoded bytes (no
    data: prefix -- Ollama's `images` field wants the raw base64).

    Network errors propagate as VLMError so the pipeline degrades
    rather than 500-ing.
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(image_url)
            r.raise_for_status()
            return base64.b64encode(r.content).decode("ascii")
    except httpx.HTTPError as exc:
        raise VLMError(f"failed to fetch image {image_url}: {exc}") from exc


def _ollama_generate(
    *, api_url: str, model: str, prompt: str, image_b64: str
) -> str:
    """Call Ollama's /api/generate with stream=False. Returns the
    plain-text completion. Raises VLMError on any HTTP / shape problem."""
    endpoint = api_url.rstrip("/") + "/api/generate"
    body = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
    }
    try:
        with httpx.Client(timeout=_OLLAMA_TIMEOUT_SEC) as client:
            r = client.post(endpoint, json=body)
            r.raise_for_status()
            payload = r.json()
    except httpx.HTTPError as exc:
        raise VLMError(f"ollama call failed: {exc}") from exc
    except ValueError as exc:  # JSON decode
        raise VLMError(f"ollama returned non-JSON: {exc}") from exc
    text = payload.get("response")
    if not isinstance(text, str) or not text.strip():
        raise VLMError(f"ollama returned empty/invalid response: {payload!r}")
    return text.strip()


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
            return self._describe_ollama(image_url=image_url)
        raise VLMUnknownBackend(
            f"unknown vlm backend {self.backend!r}; expected one of: stub, ollama"
        )

    def _describe_ollama(self, *, image_url: str) -> dict:
        if not self.api_url:
            raise VLMError(
                "ollama backend selected but VLM_API_URL is empty; "
                "set e.g. VLM_API_URL=http://vlm:11434"
            )
        # Fetch once, infer twice. The full + summary share the same
        # bytes so we don't pay double bandwidth or risk getting two
        # different frames if the source URL is volatile.
        image_b64 = _fetch_image_b64(image_url)
        logger.info(
            "vlm_describe_start backend=ollama model=%s url=%s bytes_b64=%d",
            self.model, image_url, len(image_b64),
        )
        full = _ollama_generate(
            api_url=self.api_url,
            model=self.model,
            prompt=_PROMPT_FULL,
            image_b64=image_b64,
        )
        summary = _ollama_generate(
            api_url=self.api_url,
            model=self.model,
            prompt=_PROMPT_SUMMARY,
            image_b64=image_b64,
        )
        logger.info(
            "vlm_describe_done full_len=%d summary_len=%d",
            len(full), len(summary),
        )
        return {
            "description_full": full,
            "description_summary": summary,
            "description_model": f"ollama/{self.model}",
            "description_generated_at": datetime.now(timezone.utc).isoformat(),
        }
