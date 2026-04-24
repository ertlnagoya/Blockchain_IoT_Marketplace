from datetime import datetime, timezone

from policy.engine import PolicyEngine
from policy.models import ConsentVC


def _consent() -> ConsentVC:
    return ConsentVC.model_validate(
        {
            "vc_id": "consent-1",
            "subject_did": "did:example:alice",
            "dataset_id": "home/env/temperature",
            "allowed_purposes": ["research"],
            "retention_days": 30,
            "reshare_allowed": False,
            "valid_from": "2026-02-01T00:00:00Z",
            "valid_to": "2026-05-01T00:00:00Z",
            "signature": "PLACEHOLDER",
        }
    )


def test_policy_allow() -> None:
    engine = PolicyEngine()
    decision = engine.evaluate(
        dataset_id="home/env/temperature",
        purpose="research",
        consents=[_consent()],
        now=datetime(2026, 2, 28, tzinfo=timezone.utc),
    )
    assert decision.allowed is True


def test_policy_deny_invalid_purpose() -> None:
    engine = PolicyEngine()
    decision = engine.evaluate(
        dataset_id="home/env/temperature",
        purpose="marketing",
        consents=[_consent()],
        now=datetime(2026, 2, 28, tzinfo=timezone.utc),
    )
    assert decision.allowed is False
    assert decision.reason == "no_matching_consent"
