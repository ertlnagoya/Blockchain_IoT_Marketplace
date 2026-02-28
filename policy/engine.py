from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from policy.models import ConsentVC
from policy.verifier import verify_signature


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    consent: ConsentVC | None = None


class PolicyEngine:
    def evaluate(
        self,
        dataset_id: str,
        purpose: str,
        consents: list[ConsentVC],
        now: datetime | None = None,
    ) -> PolicyDecision:
        clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

        for consent in consents:
            if consent.dataset_id != dataset_id:
                continue
            if not verify_signature(consent):
                continue
            if purpose not in consent.allowed_purposes:
                continue
            if clock < consent.valid_from.astimezone(timezone.utc):
                continue
            if clock > consent.valid_to.astimezone(timezone.utc):
                continue
            return PolicyDecision(True, "allowed", consent)

        return PolicyDecision(False, "no_matching_consent")
