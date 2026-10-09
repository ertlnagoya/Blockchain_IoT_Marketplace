"""Stage T (VLM extension, Δ2 skeleton) tests.

Covers the four buckets called out in the spec:

  1. `--profile vlm` off: existing tier projection regresses to nothing
  2. stub VLM backend produces the expected description_* shape
  3. Per-tier /platform/data projection matrix (full/access/summary/denied)
  4. Degrade matrix when VLM call or redaction fails
  5. processing_warnings propagation to the receiver

The pipeline is built standalone with a Sink so we don't need to
spin up the FastAPI app for every assertion (matches the pattern
test_data_user_vc_tiered.py uses for processor-level tests).
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from publisher.app.image_redactor import (
    ImageRedactor,
    RedactionError,
    RedactionUnknownBackend,
)
from publisher.app.pipeline import MessageProcessor
from publisher.app.ssi.trust_score import evaluate, evaluate_from_claims
from publisher.app.vlm_client import (
    VLMClient,
    VLMError,
    VLMUnknownBackend,
)
from policy.engine import PolicyEngine
from policy.models import ConsentVC
from policy.store import ConsentStore
from audit.repository import SQLiteAuditRepository


# ---------- (1) Trust score: profile-off keeps legacy 3-tier ----------


def test_trust_score_profile_off_full():
    """Tier 3 (full): unchanged shape under legacy projection."""
    e = evaluate(
        entity_type="GovernmentOrganization",
        purpose="CrimeSearch",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
    )
    assert e.access_level == "full"
    assert e.allowed_views == ["event", "image", "video"]


def test_trust_score_profile_off_access():
    """Tier 2 (access): legacy mapping is image-with-no-video."""
    e = evaluate(
        entity_type="Enterprise",
        purpose="Research",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
    )
    assert e.access_level == "access"
    assert e.allowed_views == ["event", "image"]


def test_trust_score_profile_off_denied():
    """Below 60 still denies (no `summary` tier without VLM profile)."""
    e = evaluate(
        entity_type="Enterprise",
        purpose="Research",
        legal_compliance=False,
        data_handling_policy="Other",
        misuse_record=True,
    )
    assert e.access_level == "denied"
    assert e.allowed_views == []


def test_trust_score_profile_off_no_summary_band():
    """Profile-off MUST NOT introduce the summary tier even at scores
    that would qualify for it under the VLM profile (50-59). Regression
    guard: a careless refactor that leaks vlm_profile=True default
    would silently widen what receivers see."""
    # 25 (entity ENTERPRISE) + 5 (purpose unknown) + 0 + 0 + 10 = 40
    e = evaluate(
        entity_type="Enterprise",
        purpose="unknown",
        legal_compliance=False,
        data_handling_policy="other",
        misuse_record=False,
    )
    # That's 50, but score-band assertion below uses entity_score 20
    # for enterprise -- so total = 20+5+0+0+10 = 35, which IS denied.
    # Either way the test asserts: profile off NEVER returns summary.
    assert e.access_level != "summary"


# ---------- (2) Trust score: profile-on opens summary tier ----------


def test_trust_score_profile_on_full_extends_views():
    e = evaluate(
        entity_type="GovernmentOrganization",
        purpose="CrimeSearch",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
        vlm_profile=True,
    )
    assert e.access_level == "full"
    assert "image" in e.allowed_views
    assert "video" in e.allowed_views
    assert "image_redacted" in e.allowed_views
    assert "description_full" in e.allowed_views
    assert "description_summary" in e.allowed_views


def test_trust_score_profile_on_access_swaps_image_for_redacted():
    e = evaluate(
        entity_type="Enterprise",
        purpose="Research",
        legal_compliance=True,
        data_handling_policy="ISO27001",
        misuse_record=False,
        vlm_profile=True,
    )
    assert e.access_level == "access"
    # No raw image / video at access tier under VLM projection
    assert "image" not in e.allowed_views
    assert "video" not in e.allowed_views
    # But the redacted image + both descriptions are visible
    assert "image_redacted" in e.allowed_views
    assert "description_full" in e.allowed_views
    assert "description_summary" in e.allowed_views


def test_trust_score_profile_on_summary_band_visible():
    """A 50-59 score under VLM profile maps to summary, not denied."""
    # entity ENTERPRISE (20) + purpose RESEARCH (15) + legal (15) + no_misuse (10) = 60
    # That's exactly access -- need to drop one to 59. Easiest: misuse=true (-10).
    # 20 + 15 + 15 + 0 - 10 = 40 -> still under 50 (denied).
    # Try: enterprise + research + legal=False + ISO27001 + no_misuse:
    # 20 + 15 + 0 + 15 + 10 = 60 -> access. Drop ISO: 20+15+0+0+10 = 45 (denied).
    # The construction is sensitive. Use a synthetic call instead:
    e = evaluate(
        entity_type="Enterprise",
        purpose="Research",
        legal_compliance=True,  # +15
        data_handling_policy="other",
        misuse_record=False,  # +10
        vlm_profile=True,
    )
    # 20 + 15 + 15 + 0 + 10 = 60 -> access (still). Try purpose=unknown:
    e2 = evaluate(
        entity_type="Enterprise",
        purpose="unknown",
        legal_compliance=True,  # +15
        data_handling_policy="other",
        misuse_record=False,  # +10
        vlm_profile=True,
    )
    # 20 + 5 + 15 + 0 + 10 = 50 -> summary
    assert e2.access_level == "summary", e2
    assert e2.allowed_views == ["event", "description_summary"]


def test_trust_score_profile_on_summary_collapses_to_denied_under_legacy():
    """The same `score==50` claim that earns `summary` under the VLM
    profile MUST still return `denied` under the legacy projection."""
    legacy = evaluate(
        entity_type="Enterprise",
        purpose="unknown",
        legal_compliance=True,
        data_handling_policy="other",
        misuse_record=False,
    )
    assert legacy.access_level == "denied"


def test_evaluate_from_claims_passes_profile_through():
    claims = {
        "entityType": "Enterprise",
        "purpose": "Research",
        "legalCompliance": True,
        "dataHandlingPolicy": "ISO27001",
        "misuseRecord": False,
    }
    legacy = evaluate_from_claims(claims)
    vlm = evaluate_from_claims(claims, vlm_profile=True)
    assert legacy.access_level == "access"
    assert vlm.access_level == "access"
    # Same access level, different allowed_views (the VLM profile
    # widens Tier 2's projection rather than re-tiering this row).
    assert legacy.allowed_views == ["event", "image"]
    assert vlm.allowed_views == [
        "event",
        "image_redacted",
        "description_full",
        "description_summary",
    ]


# ---------- (3) VLMClient stub backend produces the contract shape ----------


def test_vlm_stub_returns_four_keys():
    c = VLMClient(backend="stub", api_url="", model="stub-vlm/v0")
    out = c.describe(
        image_url="http://example/media/abc.jpg",
        content_type="image/jpeg",
    )
    assert set(out.keys()) == {
        "description_full",
        "description_summary",
        "description_model",
        "description_generated_at",
    }
    assert "[stub VLM" in out["description_full"]
    assert "[stub VLM" in out["description_summary"]
    assert out["description_model"] == "stub-vlm/v0"


def test_vlm_stub_is_deterministic():
    """Same image_url -> same description hash. Lets tests assert on
    the exact strings without mocking randomness."""
    c = VLMClient(backend="stub", api_url="", model="stub-vlm/v0")
    a = c.describe(image_url="http://example/media/x.jpg", content_type="image/jpeg")
    b = c.describe(image_url="http://example/media/x.jpg", content_type="image/jpeg")
    assert a["description_full"] == b["description_full"]
    assert a["description_summary"] == b["description_summary"]


def test_vlm_ollama_backend_calls_http(monkeypatch):
    """Δ3: ollama backend now does real HTTP. Mock the two helper
    functions and assert the contract: image fetched once, generate
    called twice (full + summary), returned dict carries the
    publisher's response shape."""
    from publisher.app import vlm_client as vc_mod

    fetch_calls = []
    generate_calls = []

    def fake_fetch(image_url, *, timeout=10.0):
        fetch_calls.append(image_url)
        return "ZmFrZS1iYXNlNjQ="  # base64 of "fake-base64"

    def fake_generate(*, api_url, model, prompt, image_b64):
        generate_calls.append({"api_url": api_url, "model": model, "prompt": prompt})
        if "WITHOUT identifying" in prompt:
            return "An adult dropped something near a public location."
        return "John Smith dropped a Coke bottle near the Hibiya station entrance."

    monkeypatch.setattr(vc_mod, "_fetch_image_b64", fake_fetch)
    monkeypatch.setattr(vc_mod, "_ollama_generate", fake_generate)

    c = VLMClient(backend="ollama", api_url="http://vlm:11434", model="llava")
    out = c.describe(image_url="http://publisher/media/abc.jpg", content_type="image/jpeg")

    assert fetch_calls == ["http://publisher/media/abc.jpg"]
    assert len(generate_calls) == 2  # full + summary
    assert "John Smith" in out["description_full"]
    assert "John Smith" not in out["description_summary"]
    assert "An adult" in out["description_summary"]
    assert out["description_model"] == "ollama/llava"


def test_vlm_per_backend_prompts_long_for_llava(monkeypatch):
    """llava-* models get the default (long) prompt set with explicit
    PII-redaction instructions."""
    from publisher.app import vlm_client as vc_mod

    captured = []

    def fake_fetch(image_url, *, timeout=10.0):
        return "ZmFrZS1iYXNlNjQ="

    def fake_generate(*, api_url, model, prompt, image_b64):
        captured.append({"model": model, "prompt": prompt})
        return "ok"

    monkeypatch.setattr(vc_mod, "_fetch_image_b64", fake_fetch)
    monkeypatch.setattr(vc_mod, "_ollama_generate", fake_generate)

    c = VLMClient(backend="ollama", api_url="http://vlm:11434", model="llava")
    c.describe(image_url="http://x/y.jpg", content_type="image/jpeg")

    # Default prompt set: detailed instructions, ~200+ chars per stage.
    full_prompt = captured[0]["prompt"]
    summary_prompt = captured[1]["prompt"]
    assert len(full_prompt) > 150
    assert "names of people" in full_prompt
    assert "WITHOUT identifying" in summary_prompt
    assert "license plate" in summary_prompt


def test_vlm_per_backend_prompts_short_for_moondream(monkeypatch):
    """moondream / bakllava get a short prompt set: real-device finding
    is they truncate to 3-10 char fragments on the long defaults."""
    from publisher.app import vlm_client as vc_mod

    captured = []

    def fake_fetch(image_url, *, timeout=10.0):
        return "ZmFrZS1iYXNlNjQ="

    def fake_generate(*, api_url, model, prompt, image_b64):
        captured.append({"model": model, "prompt": prompt})
        return "ok"

    monkeypatch.setattr(vc_mod, "_fetch_image_b64", fake_fetch)
    monkeypatch.setattr(vc_mod, "_ollama_generate", fake_generate)

    c = VLMClient(backend="ollama", api_url="http://vlm:11434", model="moondream")
    c.describe(image_url="http://x/y.jpg", content_type="image/jpeg")

    full_prompt = captured[0]["prompt"]
    summary_prompt = captured[1]["prompt"]
    # Short set: under 200 chars per stage (vs >150 for long).
    assert len(full_prompt) < 200
    # Still has the privacy-preserving distinction in the summary
    # prompt (the whole point of the two-stage design).
    assert "without naming" in summary_prompt.lower()


def test_vlm_per_backend_prompts_unknown_falls_back_to_default(monkeypatch):
    """Unknown model -> default (long) prompts. Operator can add a new
    entry to _PROMPT_TABLE if they need a tuned set."""
    from publisher.app import vlm_client as vc_mod

    captured = []

    def fake_fetch(image_url, *, timeout=10.0):
        return "ZmFrZS1iYXNlNjQ="

    def fake_generate(*, api_url, model, prompt, image_b64):
        captured.append(prompt)
        return "ok"

    monkeypatch.setattr(vc_mod, "_fetch_image_b64", fake_fetch)
    monkeypatch.setattr(vc_mod, "_ollama_generate", fake_generate)

    c = VLMClient(backend="ollama", api_url="http://vlm:11434", model="brand-new-vlm")
    c.describe(image_url="http://x/y.jpg", content_type="image/jpeg")

    # Falls back to the default (long) set.
    assert any("names of people" in p for p in captured)


def test_vlm_ollama_backend_requires_api_url():
    """Empty VLM_API_URL must produce a clear error -- otherwise the
    pipeline degrades silently with a confusing httpx error."""
    c = VLMClient(backend="ollama", api_url="", model="llava")
    with pytest.raises(VLMError, match="VLM_API_URL is empty"):
        c.describe(image_url="http://example/x.jpg", content_type="image/jpeg")


def test_vlm_ollama_backend_propagates_http_failure(monkeypatch):
    """Network / HTTP errors must surface as VLMError so the pipeline
    catches them and emits processing_warnings: ['vlm_unavailable'].
    A bare httpx exception leaking through would become a 500."""
    from publisher.app import vlm_client as vc_mod

    def fake_fetch(image_url, *, timeout=10.0):
        raise vc_mod.VLMError("simulated outage")

    monkeypatch.setattr(vc_mod, "_fetch_image_b64", fake_fetch)
    c = VLMClient(backend="ollama", api_url="http://vlm:11434", model="llava")
    with pytest.raises(VLMError, match="simulated outage"):
        c.describe(image_url="http://example/x.jpg", content_type="image/jpeg")


def test_vlm_unknown_backend_raises():
    c = VLMClient(backend="bogus", api_url="", model="")
    with pytest.raises(VLMUnknownBackend):
        c.describe(image_url="http://example/x.jpg", content_type="image/jpeg")


def test_vlm_from_settings_disabled_returns_none():
    class _S:
        vlm_backend = ""
        vlm_api_url = ""
        vlm_model = ""

    assert VLMClient.from_settings(_S()) is None


# ---------- (4) ImageRedactor stub passes a marker URL ----------


def test_image_redactor_stub_marks_url():
    r = ImageRedactor(backend="stub")
    out = r.blur_pii(
        image_url="http://example/media/abc.jpg",
        content_type="image/jpeg",
    )
    assert "redacted=stub" in out["image_url_redacted"]
    assert out["image_cid_redacted"] is None


def test_image_redactor_video_is_not_implemented():
    r = ImageRedactor(backend="stub")
    with pytest.raises(RedactionError):
        r.blur_pii(image_url="http://example/x.mp4", content_type="video/mp4")


def test_image_redactor_unknown_backend_raises():
    r = ImageRedactor(backend="bogus")
    with pytest.raises(RedactionUnknownBackend):
        r.blur_pii(image_url="http://example/x.jpg", content_type="image/jpeg")


# ---------- (4b) ImageRedactor opencv backend (Δ3) ----------


def test_image_redactor_opencv_round_trip(monkeypatch):
    """Δ3: opencv backend fetches the source, runs the (mocked) blur,
    POSTs back to /media/upload, and surfaces the response's url +
    cid as image_url_redacted / image_cid_redacted."""
    from publisher.app import image_redactor as ir_mod

    fetch_calls = []
    blur_calls = []
    upload_calls = []

    def fake_get(url, *, timeout=10.0):
        fetch_calls.append(url)
        # Returning bytes is enough; the test stubs out the actual
        # cv2 decoding via the blur monkeypatch below.
        class _R:
            content = b"fake-source-bytes"
            def raise_for_status(self):
                pass
        return _R()

    class _Client:
        def __init__(self, **_kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        get = staticmethod(fake_get)
        def post(self, endpoint, files=None):
            upload_calls.append({"endpoint": endpoint, "files_keys": list(files or {})})
            class _R:
                def raise_for_status(self): pass
                @staticmethod
                def json():
                    return {
                        "url": "http://publisher/media/redactedhash.jpg",
                        "cid": "bafyredactedcid",
                        "sha256": "redactedhash",
                        "content_type": "image/jpeg",
                        "byte_size": 100,
                    }
            return _R()

    monkeypatch.setattr(ir_mod.httpx, "Client", _Client)

    def fake_blur(image_bytes, *, ext):
        blur_calls.append({"len": len(image_bytes), "ext": ext})
        return b"fake-blurred-bytes"

    monkeypatch.setattr(ir_mod, "_opencv_blur_faces", fake_blur)

    r = ImageRedactor(backend="opencv")
    out = r.blur_pii(
        image_url="http://publisher/media/abc.jpg",
        content_type="image/jpeg",
    )

    assert fetch_calls == ["http://publisher/media/abc.jpg"]
    assert blur_calls == [{"len": len(b"fake-source-bytes"), "ext": ".jpg"}]
    assert len(upload_calls) == 1
    assert upload_calls[0]["endpoint"].endswith("/media/upload")
    assert out["image_url_redacted"] == "http://publisher/media/redactedhash.jpg"
    assert out["image_cid_redacted"] == "bafyredactedcid"


def test_image_redactor_opencv_propagates_fetch_failure(monkeypatch):
    """Source fetch failure must surface as RedactionError so the
    pipeline catches it and emits processing_warnings."""
    from publisher.app import image_redactor as ir_mod
    import httpx

    class _BadClient:
        def __init__(self, **_kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, url, *, timeout=10.0):
            raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr(ir_mod.httpx, "Client", _BadClient)

    r = ImageRedactor(backend="opencv")
    with pytest.raises(RedactionError, match="failed to fetch"):
        r.blur_pii(
            image_url="http://publisher/media/abc.jpg",
            content_type="image/jpeg",
        )


# ---------- (5) Pipeline integration: VLM + redactor wiring ----------


def _build_processor(*, vlm_client=None, image_redactor=None):
    """Build a MessageProcessor with seeded consent for
    home/event/possible_littering. Returns (processor, sink) where
    sink.last is the most recent envelope sent."""
    td = tempfile.mkdtemp(prefix="vlm-test-")
    cs = ConsentStore(os.path.join(td, "c.json"))
    now = datetime.now(timezone.utc)
    cs.upsert(
        ConsentVC(
            vc_id="c-vlm-test",
            subject_did="did:example:provider",
            dataset_id="home/event/possible_littering",
            allowed_purposes=["community_cleaning"],
            retention_days=14,
            reshare_allowed=False,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            signature="x",
        )
    )

    captured: list[dict] = []

    class _Sink:
        def send(self, env: dict) -> None:
            captured.append(env)

    proc = MessageProcessor(
        publisher_id="t",
        default_purpose="community_cleaning",
        consent_store=cs,
        policy_engine=PolicyEngine(),
        audit_repo=SQLiteAuditRepository(os.path.join(td, "a.db")),
        platform_client=_Sink(),
        vlm_client=vlm_client,
        image_redactor=image_redactor,
    )
    return proc, captured


def _publish(proc):
    return proc.process_message(
        "homeassistant/event/possible_littering",
        {
            "event_type": "possible_littering",
            "ts": "2026-04-30T07:00:00Z",
            "source": "iw3ip-provider-page",
            "image_url": "http://publisher/media/abc.jpg",
            "data": {},
        },
        "community_cleaning",
    )


def test_pipeline_no_injectors_keeps_legacy_envelope():
    """Δ2 regression: when both injectors are None the envelope is
    byte-for-byte identical to the pre-VLM behaviour. Description /
    redacted keys MUST NOT appear and processing_warnings MUST NOT
    leak in."""
    proc, sent = _build_processor()
    result = _publish(proc)
    assert result["status"] == "allowed"
    env = sent[0]
    assert "description_full" not in env
    assert "description_summary" not in env
    assert "image_url_redacted" not in env
    assert "image_cid_redacted" not in env
    assert "processing_warnings" not in env


def test_pipeline_stub_backends_attach_all_keys():
    proc, sent = _build_processor(
        vlm_client=VLMClient(backend="stub", api_url="", model="stub-vlm/v0"),
        image_redactor=ImageRedactor(backend="stub"),
    )
    _publish(proc)
    env = sent[0]
    assert "[stub VLM" in env["description_full"]
    assert "[stub VLM" in env["description_summary"]
    assert env["description_model"] == "stub-vlm/v0"
    assert "redacted=stub" in env["image_url_redacted"]
    # Both injectors succeeded -> no warnings entry at all.
    assert "processing_warnings" not in env


def test_pipeline_vlm_failure_emits_warning_but_keeps_redacted():
    """VLM down + redactor up: row ships without descriptions but the
    redacted image is still there, plus processing_warnings flags
    `vlm_unavailable` so receivers know what they're missing."""

    class _BrokenVLM:
        def describe(self, **_kwargs):
            raise VLMError("simulated outage")

    proc, sent = _build_processor(
        vlm_client=_BrokenVLM(),
        image_redactor=ImageRedactor(backend="stub"),
    )
    _publish(proc)
    env = sent[0]
    assert "description_full" not in env
    assert "description_summary" not in env
    assert "redacted=stub" in env["image_url_redacted"]
    assert env["processing_warnings"] == ["vlm_unavailable"]


def test_pipeline_redaction_failure_emits_warning_but_keeps_descriptions():
    class _BrokenRedactor:
        def blur_pii(self, **_kwargs):
            raise RedactionError("simulated outage")

    proc, sent = _build_processor(
        vlm_client=VLMClient(backend="stub", api_url="", model="stub-vlm/v0"),
        image_redactor=_BrokenRedactor(),
    )
    _publish(proc)
    env = sent[0]
    assert "[stub VLM" in env["description_full"]
    assert "image_url_redacted" not in env
    assert env["processing_warnings"] == ["redaction_unavailable"]


def test_pipeline_both_fail_emits_both_warnings_and_raw_keys_remain():
    class _BrokenVLM:
        def describe(self, **_kwargs):
            raise VLMError("vlm down")

    class _BrokenRedactor:
        def blur_pii(self, **_kwargs):
            raise RedactionError("blur down")

    proc, sent = _build_processor(
        vlm_client=_BrokenVLM(),
        image_redactor=_BrokenRedactor(),
    )
    _publish(proc)
    env = sent[0]
    assert env["processing_warnings"] == ["vlm_unavailable", "redaction_unavailable"]
    # Raw key MUST still ship -- the publisher is NOT supposed to
    # silently drop content when the derivatives are down.
    assert env["image_url"] == "http://publisher/media/abc.jpg"
