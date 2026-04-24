from __future__ import annotations

from policy.models import ConsentVC


def verify_signature(consent: ConsentVC) -> bool:
    """Signature verification hook (placeholder for Phase 3 SSI integration)."""
    return bool(consent.signature)
