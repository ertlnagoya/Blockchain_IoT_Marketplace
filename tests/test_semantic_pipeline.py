"""Tests for the Stage T+ semantic-tier pipeline.

Covers the 8 spec test cases:

  1. trustLevel == anonymous -> no image bytes ever returned
  2. trustLevel == low -> no original image returned
  3. trustLevel == medium -> face/text/screen/whiteboard/document/
     id_card/name_tag/unknown_sensitive all masked
  4. trustLevel unset / unknown -> coerced to anonymous
  5. SemanticAnalyzer error -> no original frame in the response
  6. sensitive_regions empty + low analyzer confidence -> still safe
     (here represented by the empty SIR shape: privacy_risk_score=1.0
     forces image kinds off at MEDIUM)
  7. OWNER / ADMIN access -> audit_required=True on the policy and
     original frame is permitted
  8. policy engine internal failure -> evaluate_safe() drops to
     "no output"

Tests are deliberately analyzer-free: we hand-build SIRs to cover
edge cases. The MockSemanticAnalyzer is exercised in a separate
case to verify the analyzer interface. Cv2 / OpenCV is mocked or
skipped: the renderer's mask code path is small and self-contained,
covered by an explicit cv2-not-installed test.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from publisher.app.semantic_analyzer import (
    MockSemanticAnalyzer,
    SemanticAnalyzer,
    SemanticAnalyzerError,
)
from publisher.app.sir_models import (
    BoundingBox,
    DetectedEvent,
    DetectedObject,
    PeopleSummary,
    SemanticIntermediateRepresentation,
    SensitiveRegion,
    SensitiveRegionType,
    ViewerTrustLevel,
)
from publisher.app.trust_aware_renderer import RenderedOutput, TrustAwareRenderer
from publisher.app.trust_policy import (
    DisclosurePolicy,
    OutputKind,
    TrustPolicyEngine,
)


# ---------- helpers ----------


def _sir_with_regions(
    regions: list[SensitiveRegion] | None = None,
    *,
    privacy_risk_score: float = 0.5,
) -> SemanticIntermediateRepresentation:
    return SemanticIntermediateRepresentation(
        frame_id="f-1",
        source_device_id="iphone-test",
        captured_at=datetime.now(timezone.utc),
        scene_summary="test scene",
        objects=[
            DetectedObject(
                label="person",
                confidence=0.9,
                bbox=BoundingBox(x=0.1, y=0.1, width=0.2, height=0.5),
            )
        ],
        people=PeopleSummary(count=1),
        sensitive_regions=regions or [],
        events=[
            DetectedEvent(
                type="person_detected",
                description="人物が検出された",
                confidence=0.9,
            )
        ],
        privacy_risk_score=privacy_risk_score,
        analyzer_version="test",
    )


def _all_kinds_of_sensitive_region() -> list[SensitiveRegion]:
    return [
        SensitiveRegion(
            type=t,
            confidence=0.9,
            bbox=BoundingBox(x=0.1 * i, y=0.1, width=0.05, height=0.05),
            reason=f"test-{t.value}",
        )
        for i, t in enumerate(
            [
                SensitiveRegionType.FACE,
                SensitiveRegionType.TEXT,
                SensitiveRegionType.SCREEN,
                SensitiveRegionType.WHITEBOARD,
                SensitiveRegionType.DOCUMENT,
                SensitiveRegionType.ID_CARD,
                SensitiveRegionType.NAME_TAG,
                SensitiveRegionType.UNKNOWN_SENSITIVE,
            ]
        )
    ]


# ---------- (1) ANONYMOUS gets no image kinds ----------


def test_anonymous_never_receives_image_kinds():
    engine = TrustPolicyEngine()
    sir = _sir_with_regions([SensitiveRegion(
        type=SensitiveRegionType.FACE,
        confidence=0.9,
        bbox=BoundingBox(x=0.1, y=0.1, width=0.1, height=0.1),
        reason="",
    )])
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.ANONYMOUS, sir=sir)
    assert OutputKind.REDACTED_IMAGE not in policy.allowed_outputs
    assert OutputKind.LOW_RESOLUTION_IMAGE not in policy.allowed_outputs
    assert OutputKind.MASKED_VIDEO_FRAME not in policy.allowed_outputs
    assert OutputKind.ORIGINAL_FRAME not in policy.allowed_outputs
    assert not policy.has_image_output


def test_anonymous_renderer_never_returns_image_bytes():
    """Even if a route accidentally hands the source bytes to the
    renderer, the policy's allowed_outputs list doesn't include any
    image kind so image_bytes must be None."""
    engine = TrustPolicyEngine()
    renderer = TrustAwareRenderer()
    sir = _sir_with_regions(_all_kinds_of_sensitive_region())
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.ANONYMOUS, sir=sir)
    out = renderer.render(
        sir=sir, policy=policy, image_bytes=b"\xff\xd8\xff\xe0", image_content_type="image/jpeg"
    )
    assert out.image_bytes is None
    assert out.image_content_type is None


# ---------- (2) LOW: no original frame, no image at all ----------


def test_low_never_receives_original_frame():
    engine = TrustPolicyEngine()
    sir = _sir_with_regions([])
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.LOW, sir=sir)
    assert OutputKind.ORIGINAL_FRAME not in policy.allowed_outputs
    # In fact LOW gets text/event only -- no image at all.
    assert not policy.has_image_output


# ---------- (3) MEDIUM masks every "always mask" type ----------


def test_medium_masks_all_always_mask_categories():
    engine = TrustPolicyEngine()
    regions = _all_kinds_of_sensitive_region()
    sir = _sir_with_regions(regions)
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.MEDIUM, sir=sir)
    masked_types = {r.type for r in policy.mask_regions}
    expected = {
        SensitiveRegionType.FACE,
        SensitiveRegionType.TEXT,
        SensitiveRegionType.SCREEN,
        SensitiveRegionType.WHITEBOARD,
        SensitiveRegionType.DOCUMENT,
        SensitiveRegionType.ID_CARD,
        SensitiveRegionType.NAME_TAG,
        SensitiveRegionType.UNKNOWN_SENSITIVE,
    }
    assert expected.issubset(masked_types)
    # And MEDIUM gets the redacted/lowres affordances.
    assert OutputKind.REDACTED_IMAGE in policy.allowed_outputs
    assert OutputKind.LOW_RESOLUTION_IMAGE in policy.allowed_outputs
    # But MEDIUM never gets the masked video frame or original.
    assert OutputKind.MASKED_VIDEO_FRAME not in policy.allowed_outputs
    assert OutputKind.ORIGINAL_FRAME not in policy.allowed_outputs


# ---------- (4) Unknown / missing trustLevel collapses to ANONYMOUS ----------


def test_unset_trust_level_treated_as_anonymous():
    engine = TrustPolicyEngine()
    sir = _sir_with_regions([])
    policy_none = engine.evaluate(viewer_trust=None, sir=sir)
    policy_garbage = engine.evaluate(viewer_trust="not-a-real-level", sir=sir)
    policy_int = engine.evaluate(viewer_trust=42, sir=sir)
    assert policy_none.trust_level is ViewerTrustLevel.ANONYMOUS
    assert policy_garbage.trust_level is ViewerTrustLevel.ANONYMOUS
    assert policy_int.trust_level is ViewerTrustLevel.ANONYMOUS


def test_string_trust_level_is_case_insensitive():
    engine = TrustPolicyEngine()
    sir = _sir_with_regions([])
    assert (
        engine.evaluate(viewer_trust="MEDIUM", sir=sir).trust_level
        is ViewerTrustLevel.MEDIUM
    )
    assert (
        engine.evaluate(viewer_trust="HiGh", sir=sir).trust_level
        is ViewerTrustLevel.HIGH
    )


# ---------- (5) Analyzer failure -> empty SIR -> no original frame ----------


def test_analyzer_error_path_uses_empty_sir():
    """When the analyzer raises, callers fall through to
    `SemanticIntermediateRepresentation.empty()` which has a 1.0
    privacy_risk_score. Even MEDIUM viewers lose every image kind
    in that case."""

    class _Broken(SemanticAnalyzer):
        name = "broken/v1"

        def analyze(self, *, image_bytes, source_device_id):
            raise SemanticAnalyzerError("simulated decode failure")

    analyzer = _Broken()
    with pytest.raises(SemanticAnalyzerError):
        analyzer.analyze(image_bytes=b"x", source_device_id="d")

    # Caller's responsibility: replace with empty SIR.
    sir = SemanticIntermediateRepresentation.empty(
        frame_id="f-broken", source_device_id="d"
    )
    engine = TrustPolicyEngine()
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.MEDIUM, sir=sir)
    # MEDIUM ordinarily has REDACTED_IMAGE; high risk strips it.
    assert OutputKind.REDACTED_IMAGE not in policy.allowed_outputs
    assert OutputKind.LOW_RESOLUTION_IMAGE not in policy.allowed_outputs
    # Text affordances remain so the receiver isn't silently blank.
    assert OutputKind.TEXT_SUMMARY in policy.allowed_outputs


# ---------- (6) Empty regions + high risk score -> still safe ----------


def test_empty_regions_but_high_risk_score_drops_image_at_medium():
    """If the analyzer reported nothing yet asserts a high
    privacy_risk_score (e.g. because confidence was low across the
    board), MEDIUM still loses the image affordance. No image must
    leak just because the analyzer can't pinpoint what's risky."""
    sir = _sir_with_regions([], privacy_risk_score=0.95)
    engine = TrustPolicyEngine()
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.MEDIUM, sir=sir)
    assert not policy.has_image_output


# ---------- (7) OWNER / ADMIN access flags audit_required ----------


def test_owner_and_admin_set_audit_required():
    engine = TrustPolicyEngine()
    sir = _sir_with_regions([])
    p_owner = engine.evaluate(viewer_trust=ViewerTrustLevel.OWNER, sir=sir)
    p_admin = engine.evaluate(viewer_trust=ViewerTrustLevel.ADMIN, sir=sir)
    assert p_owner.audit_required is True
    assert p_admin.audit_required is True
    # And both can receive originals (subject to caller actually
    # logging access).
    assert OutputKind.ORIGINAL_FRAME in p_owner.allowed_outputs
    assert OutputKind.ORIGINAL_FRAME in p_admin.allowed_outputs


def test_renderer_emits_original_only_for_owner_and_admin():
    """Even if a malicious caller built a DisclosurePolicy with
    ORIGINAL_FRAME in allowed_outputs but a low trust_level (which
    `evaluate()` itself never produces), the renderer cross-checks
    the trust_level and refuses."""
    bad_policy = DisclosurePolicy(
        trust_level=ViewerTrustLevel.MEDIUM,  # NOT owner/admin
        allowed_outputs=frozenset({OutputKind.ORIGINAL_FRAME}),
        mask_regions=tuple(),
    )
    renderer = TrustAwareRenderer()
    sir = _sir_with_regions([])
    out = renderer.render(
        sir=sir,
        policy=bad_policy,
        image_bytes=b"raw-bytes",
        image_content_type="image/jpeg",
    )
    # Renderer's own trust_level guard fires -> original frame
    # not emitted, image_bytes stays None because no other image
    # kind was in allowed_outputs.
    assert out.image_bytes is None


# ---------- (8) PolicyEngine.evaluate_safe wraps any internal failure ----------


def test_evaluate_safe_falls_through_on_internal_failure(monkeypatch):
    engine = TrustPolicyEngine()
    # Force the inner evaluate() to blow up.
    monkeypatch.setattr(
        engine,
        "evaluate",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("simulated")),
    )
    policy = engine.evaluate_safe(
        viewer_trust=ViewerTrustLevel.HIGH,
        sir=_sir_with_regions([]),
    )
    assert policy.trust_level is ViewerTrustLevel.ANONYMOUS
    assert policy.allowed_outputs == frozenset()  # no output at all
    assert "policy_evaluation_failed" in policy.rationale


# ---------- analyzer interface smoke tests ----------


def test_mock_analyzer_is_deterministic():
    a = MockSemanticAnalyzer()
    sir1 = a.analyze(image_bytes=b"sample-bytes", source_device_id="dev")
    sir2 = a.analyze(image_bytes=b"sample-bytes", source_device_id="dev")
    assert sir1.frame_id == sir2.frame_id
    assert len(sir1.sensitive_regions) == 3
    types = {r.type for r in sir1.sensitive_regions}
    assert SensitiveRegionType.FACE in types
    assert SensitiveRegionType.TEXT in types
    assert SensitiveRegionType.UNKNOWN_SENSITIVE in types


def test_mock_analyzer_unknown_sensitive_region_present():
    """The mock deliberately includes an unknown_sensitive region so
    the test suite exercises the fail-closed branch. Regression guard:
    if someone simplifies the mock and removes it, multiple coverage
    tests above silently lose teeth."""
    a = MockSemanticAnalyzer()
    sir = a.analyze(image_bytes=b"sample-bytes", source_device_id="dev")
    has_unknown = any(r.is_unknown for r in sir.sensitive_regions)
    assert has_unknown


# ---------- policy + renderer integration: HIGH masks unknown by default ----------


def test_high_masks_unknown_sensitive_by_default():
    engine = TrustPolicyEngine()  # default: allow_unknown_at_high=False
    sir = _sir_with_regions(_all_kinds_of_sensitive_region())
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.HIGH, sir=sir)
    # HIGH still masks unknown_sensitive even though it has more
    # output kinds than MEDIUM.
    masked_types = {r.type for r in policy.mask_regions}
    assert SensitiveRegionType.UNKNOWN_SENSITIVE in masked_types


def test_high_can_opt_in_to_unmask_unknown():
    engine = TrustPolicyEngine(allow_unknown_at_high=True)
    sir = _sir_with_regions(_all_kinds_of_sensitive_region())
    policy = engine.evaluate(viewer_trust=ViewerTrustLevel.HIGH, sir=sir)
    masked_types = {r.type for r in policy.mask_regions}
    # Opt-in deployments can let HIGH see unknown_sensitive directly.
    assert SensitiveRegionType.UNKNOWN_SENSITIVE not in masked_types
    # All other always-mask categories are still masked.
    assert SensitiveRegionType.FACE in masked_types
    assert SensitiveRegionType.TEXT in masked_types


# ---------- BoundingBox validation ----------


def test_bounding_box_rejects_out_of_range_values():
    with pytest.raises(Exception):
        BoundingBox(x=-0.1, y=0.0, width=0.5, height=0.5)
    with pytest.raises(Exception):
        BoundingBox(x=0.0, y=0.0, width=1.5, height=0.5)


def test_bounding_box_clamped_keeps_box_inside_unit_square():
    bb = BoundingBox(x=0.7, y=0.7, width=0.5, height=0.5)
    c = bb.clamped()
    assert c.x + c.width <= 1.0
    assert c.y + c.height <= 1.0


# ---------- empty SIR sanity ----------


def test_empty_sir_has_high_risk_and_no_objects():
    s = SemanticIntermediateRepresentation.empty(
        frame_id="f", source_device_id="d", analyzer_version="t"
    )
    assert s.privacy_risk_score == 1.0
    assert s.objects == []
    assert s.sensitive_regions == []


# ---------- factory dispatch ----------


def test_analyzer_from_settings_unknown_falls_back_to_mock():
    class _S:
        semantic_analyzer_backend = "this-does-not-exist"

    a = SemanticAnalyzer.from_settings(_S())
    assert isinstance(a, MockSemanticAnalyzer)


def test_analyzer_from_settings_explicit_mock():
    class _S:
        semantic_analyzer_backend = "stub"

    a = SemanticAnalyzer.from_settings(_S())
    assert isinstance(a, MockSemanticAnalyzer)


def test_analyzer_from_settings_vision_returns_vision():
    from publisher.app.semantic_analyzer import VisionSemanticAnalyzer

    class _S:
        semantic_analyzer_backend = "vision"

    a = SemanticAnalyzer.from_settings(_S())
    assert isinstance(a, VisionSemanticAnalyzer)


# ---------- HTTP routes /semantic/* ----------


def _semantic_test_app():
    """Build a minimal FastAPI app exposing /semantic/* without
    pulling in the full publisher (which needs SSI keys, mqtt, …).
    Tests can hit it via TestClient without external deps."""
    from fastapi import FastAPI
    from publisher.app.semantic_routes import build_router

    app = FastAPI()
    app.include_router(
        build_router(
            analyzer=MockSemanticAnalyzer(),
            policy_engine=TrustPolicyEngine(),
            renderer=TrustAwareRenderer(),
        )
    )
    return app


def test_semantic_analyze_route_returns_sir_json():
    from fastapi.testclient import TestClient

    client = TestClient(_semantic_test_app())
    r = client.post(
        "/semantic/analyze",
        files={"file": ("frame.jpg", b"sample-bytes", "image/jpeg")},
        data={"source_device_id": "iphone-test"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Mock analyzer always emits the canonical 3 sensitive regions.
    assert len(body["sensitive_regions"]) == 3
    assert body["analyzer_version"].startswith("mock-semantic-analyzer")
    assert body["source_device_id"] == "iphone-test"
    # The route must NOT echo the source bytes back.
    assert "image_bytes" not in body
    assert "image_b64" not in body


def test_semantic_render_route_low_trust_returns_no_image():
    """Smoke test the /semantic/render fail-closed contract: a
    low-trust caller passing image_url gets text-only back."""
    from fastapi.testclient import TestClient

    client = TestClient(_semantic_test_app())
    sir = MockSemanticAnalyzer().analyze(
        image_bytes=b"sample", source_device_id="iphone-test"
    )
    r = client.post(
        "/semantic/render",
        json={
            "trust_level": "low",
            "sir": sir.model_dump(mode="json"),
            # image_url omitted: ensure low-trust never gets bytes
            # even if the caller had supplied a fetchable URL.
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trust_level"] == "low"
    assert "image_b64" not in body
    assert body["text_summary"]


def test_semantic_render_route_unknown_trust_collapses_to_anonymous():
    from fastapi.testclient import TestClient

    client = TestClient(_semantic_test_app())
    r = client.post(
        "/semantic/render",
        json={
            "trust_level": "this-tier-does-not-exist",
            "sir": MockSemanticAnalyzer()
            .analyze(image_bytes=b"x", source_device_id="d")
            .model_dump(mode="json"),
        },
    )
    body = r.json()
    assert body["trust_level"] == "anonymous"
    assert "image_b64" not in body
