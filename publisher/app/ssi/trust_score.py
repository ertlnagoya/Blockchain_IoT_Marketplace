"""Pure-function port of Li-san's `DataUserVerifier.sol` from `/ssi/contracts/`.

The Solidity contract scores 5 attributes from a buyer's DataUserVC into
a trust score (0-100) and maps it to one of three access levels:
`full` / `access` / `denied`. This module reproduces that logic in Python
so the publisher can drive the same evaluation off-chain (and stay in
sync with the on-chain verifier when Stage 8d / ZK gets wired in).

Stage T (case α) maps the access level to `allowed_views`:
    full   -> ["event", "image", "video"]
    access -> ["event", "image"]
    denied -> []

Keep the scoring constants in lock-step with `DataUserVerifier.sol`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrustEvaluation:
    trust_score: int
    access_level: str  # "full" | "access" | "denied"
    allowed_views: list[str]


# Buckets for entityType (case-insensitive)
_HIGH_TRUST_ENTITIES = {"GOVERNMENTORGANIZATION", "POLICE"}
_ENTITY_SCORES = {
    "GOVERNMENTORGANIZATION": 35,
    "POLICE": 35,
    "ENTERPRISE": 20,
    "RESEARCH ORGANIZATION": 15,
}

# Buckets for purpose (case-insensitive)
_PURPOSE_SCORES = {
    "CRIME SEARCH": 25,
    "TRAFFIC MANAGEMENT": 20,
    "RESEARCH": 15,
}


def _entity_score(entity_type: str) -> int:
    return _ENTITY_SCORES.get(entity_type.upper(), 5)


def _purpose_score(purpose: str) -> int:
    return _PURPOSE_SCORES.get(purpose.upper(), 5)


def _level_to_views(access_level: str) -> list[str]:
    if access_level == "full":
        return ["event", "image", "video"]
    if access_level == "access":
        return ["event", "image"]
    return []


def evaluate(
    *,
    entity_type: str,
    purpose: str,
    legal_compliance: bool,
    data_handling_policy: str,
    misuse_record: bool,
) -> TrustEvaluation:
    """Mirror of DataUserVerifier.sol: verifyUserAccess()."""
    score = _entity_score(entity_type) + _purpose_score(purpose)
    if legal_compliance:
        score += 15
    if data_handling_policy.upper() == "ISO27001":
        score += 15
    if misuse_record:
        score -= 10
    else:
        score += 10

    if score >= 80 and entity_type.upper() in _HIGH_TRUST_ENTITIES:
        access = "full"
    elif score >= 60:
        access = "access"
    else:
        access = "denied"

    return TrustEvaluation(
        trust_score=score,
        access_level=access,
        allowed_views=_level_to_views(access),
    )


def evaluate_from_claims(claims: dict) -> TrustEvaluation:
    """Convenience: read the 5 attributes straight from a DataUserVC's
    decoded claims dict (the publisher applies this when a DataUserVC
    is presented as part of a marketplace claim)."""
    return evaluate(
        entity_type=str(claims.get("entityType") or ""),
        purpose=str(claims.get("purpose") or ""),
        legal_compliance=bool(claims.get("legalCompliance", False)),
        data_handling_policy=str(claims.get("dataHandlingPolicy") or ""),
        misuse_record=bool(claims.get("misuseRecord", False)),
    )
