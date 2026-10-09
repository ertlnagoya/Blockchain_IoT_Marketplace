"""Pure-function port of Li-san's `DataUserVerifier.sol` from `/ssi/contracts/`.

The Solidity contract scores 5 attributes from a buyer's DataUserVC into
a trust score (0-100) and maps it to one of three access levels:
`full` / `access` / `denied`. This module reproduces that logic in Python
so the publisher can drive the same evaluation off-chain (and stay in
sync with the on-chain verifier when Stage 8d / ZK gets wired in).

Stage T (case α, legacy 3-tier projection):
    full   -> ["event", "image", "video"]
    access -> ["event", "image"]
    denied -> []

Stage T (VLM extension, 4-tier projection — opt-in via `vlm_profile=True`):
    full    -> ["event", "image", "video",
                "image_redacted",
                "description_full", "description_summary"]
    access  -> ["event",
                "image_redacted",
                "description_full", "description_summary"]
    summary -> ["event", "description_summary"]
    denied  -> []

The legacy 3-tier projection is kept verbatim when `vlm_profile=False`
so flipping the publisher's `--profile vlm` switch is the only thing
that changes behaviour. Tests for the legacy path keep passing
unchanged.

Keep the scoring constants in lock-step with `DataUserVerifier.sol`.
See ``docs/hands-on/data-user-vc-tiered-spec.md`` "Tier extension:
semantic-level redaction (VLM)" for the schema contract.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrustEvaluation:
    trust_score: int
    access_level: str  # "full" | "access" | "summary" | "denied"
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

# Score band that triggers the new `summary` tier when the VLM
# profile is on. Below this band the claim is still rejected outright;
# above this band the legacy `access` tier kicks in unchanged.
_SUMMARY_TIER_FLOOR = 50


def _entity_score(entity_type: str) -> int:
    return _ENTITY_SCORES.get(entity_type.upper(), 5)


def _purpose_score(purpose: str) -> int:
    return _PURPOSE_SCORES.get(purpose.upper(), 5)


def _level_to_views_legacy(access_level: str) -> list[str]:
    if access_level == "full":
        return ["event", "image", "video"]
    if access_level == "access":
        return ["event", "image"]
    return []


def _level_to_views_vlm(access_level: str) -> list[str]:
    """Updated mapping when `--profile vlm` is on. Raw image/video keys
    narrow to Tier 3 only; Tier 2 swaps `image` for `image_redacted`
    and gains both description keys; Tier 1 (the new `summary` tier)
    only ships the redacted summary text."""
    if access_level == "full":
        return [
            "event",
            "image",
            "video",
            "image_redacted",
            "description_full",
            "description_summary",
        ]
    if access_level == "access":
        return [
            "event",
            "image_redacted",
            "description_full",
            "description_summary",
        ]
    if access_level == "summary":
        return ["event", "description_summary"]
    return []


def evaluate(
    *,
    entity_type: str,
    purpose: str,
    legal_compliance: bool,
    data_handling_policy: str,
    misuse_record: bool,
    vlm_profile: bool = False,
) -> TrustEvaluation:
    """Mirror of DataUserVerifier.sol: verifyUserAccess().

    The trust score is profile-independent (the 5-attribute weight
    table is shared with the on-chain verifier, so flipping the
    publisher flag must not move the number).

    `vlm_profile` only changes the `score -> access_level` cutoff (a
    new `summary` band appears between `access` and `denied`) and the
    `access_level -> allowed_views` mapping (new keys appear). When
    `vlm_profile=False` the function returns exactly what the original
    Stage T (case α) version did.
    """
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
    elif vlm_profile and score >= _SUMMARY_TIER_FLOOR:
        access = "summary"
    else:
        access = "denied"

    views = _level_to_views_vlm(access) if vlm_profile else _level_to_views_legacy(access)
    return TrustEvaluation(
        trust_score=score,
        access_level=access,
        allowed_views=views,
    )


def evaluate_from_claims(claims: dict, *, vlm_profile: bool = False) -> TrustEvaluation:
    """Convenience: read the 5 attributes straight from a DataUserVC's
    decoded claims dict (the publisher applies this when a DataUserVC
    is presented as part of a marketplace claim)."""
    return evaluate(
        entity_type=str(claims.get("entityType") or ""),
        purpose=str(claims.get("purpose") or ""),
        legal_compliance=bool(claims.get("legalCompliance", False)),
        data_handling_policy=str(claims.get("dataHandlingPolicy") or ""),
        misuse_record=bool(claims.get("misuseRecord", False)),
        vlm_profile=vlm_profile,
    )
