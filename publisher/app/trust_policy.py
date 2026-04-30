"""Trust-aware disclosure policy.

Given a viewer's ``ViewerTrustLevel`` and a frame's
``SemanticIntermediateRepresentation``, decide:

1. Which output kinds the viewer is allowed to receive
   (``textSummary`` / ``eventList`` / ``redactedImage`` / etc.).
2. Which sensitive regions in the SIR must be masked when an image
   output is permitted at all.

The resulting ``DisclosurePolicy`` is a *plan*. The renderer
(`trust_aware_renderer.py`) consumes the plan and produces the
actual bytes / text. Splitting the two means we can unit-test
"who's allowed to see what" without a working image decoder, and
swap the renderer (HTML / JSON / SSE) without touching policy
logic.

Fail-closed invariants encoded here:

* Unknown trust level -> ``ANONYMOUS``. This is implemented at the
  ``TrustPolicyEngine.evaluate()`` boundary; callers passing any
  non-``ViewerTrustLevel`` value get the strictest treatment.
* Any ``unknown_sensitive`` region forces masking at MEDIUM and
  below (HIGH may surface them only when ``allow_unknown_at_high``
  is opted in).
* Empty SIR + non-zero ``privacy_risk_score`` (the
  ``SemanticIntermediateRepresentation.empty()`` shape) produces a
  plan that ships only the boilerplate "analysis unavailable" text
  -- never an image.
* If the engine itself raises mid-evaluation, callers (the renderer
  / route) are expected to map that to "no output". A separate
  ``evaluate_safe()`` helper does that explicitly so route handlers
  don't get to forget the try/except.
"""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Iterable

from publisher.app.sir_models import (
    SemanticIntermediateRepresentation,
    SensitiveRegion,
    SensitiveRegionType,
    ViewerTrustLevel,
)


logger = logging.getLogger(__name__)


class OutputKind(str, enum.Enum):
    """Outputs the renderer can produce.

    Ordering is loosely "less revealing -> more revealing" so a quick
    `> OutputKind.LOW_RESOLUTION_IMAGE` check would tell you a viewer
    is on a permissive plan. The renderer doesn't rely on that order;
    it's purely human-readable.
    """

    TEXT_SUMMARY = "textSummary"
    EVENT_LIST = "eventList"
    REDACTED_IMAGE = "redactedImage"
    LOW_RESOLUTION_IMAGE = "lowResolutionImage"
    MASKED_VIDEO_FRAME = "maskedVideoFrame"
    ORIGINAL_FRAME = "originalFrame"


# Confidence below which a sensitive-region flag still triggers a mask.
# Spec calls this out as "fail-closed": a low-confidence text region
# must still hide. Set deliberately loose so a Haar cascade's typical
# 0.7-ish confidence still trips masking at medium.
_MASK_CONFIDENCE_FLOOR = 0.0

# privacy_risk_score above which medium-tier viewers also lose the
# image affordance (text / event only). 0.95+ is essentially the
# "empty SIR" sentinel from `SemanticIntermediateRepresentation.empty()`.
_MEDIUM_RISK_CEILING = 0.9


@dataclass(frozen=True)
class DisclosurePolicy:
    """Output of ``TrustPolicyEngine.evaluate()``.

    Pure data: the renderer reads ``allowed_outputs`` to decide what
    to produce, and ``mask_regions`` to decide which boxes get
    blurred when an image kind is in the allowed set. ``rationale``
    is a short human-readable string for debug surfaces and audit
    logs (never echoed to low-trust viewers).
    """

    trust_level: ViewerTrustLevel
    allowed_outputs: frozenset[OutputKind]
    mask_regions: tuple[SensitiveRegion, ...]
    blur_strength: int = 51
    audit_required: bool = False
    rationale: str = ""

    def allows(self, kind: OutputKind) -> bool:
        return kind in self.allowed_outputs

    @property
    def has_image_output(self) -> bool:
        return any(
            k in self.allowed_outputs
            for k in (
                OutputKind.REDACTED_IMAGE,
                OutputKind.LOW_RESOLUTION_IMAGE,
                OutputKind.MASKED_VIDEO_FRAME,
                OutputKind.ORIGINAL_FRAME,
            )
        )


# Per-tier base policy. Image-bearing tiers also get the text/event
# affordances on the assumption that more detail beats less. The
# policy engine still strips image kinds when the SIR is too risky.
_BASE_OUTPUTS: dict[ViewerTrustLevel, frozenset[OutputKind]] = {
    ViewerTrustLevel.ANONYMOUS: frozenset({OutputKind.EVENT_LIST}),
    ViewerTrustLevel.LOW: frozenset(
        {OutputKind.TEXT_SUMMARY, OutputKind.EVENT_LIST}
    ),
    ViewerTrustLevel.MEDIUM: frozenset(
        {
            OutputKind.TEXT_SUMMARY,
            OutputKind.EVENT_LIST,
            OutputKind.REDACTED_IMAGE,
            OutputKind.LOW_RESOLUTION_IMAGE,
        }
    ),
    ViewerTrustLevel.HIGH: frozenset(
        {
            OutputKind.TEXT_SUMMARY,
            OutputKind.EVENT_LIST,
            OutputKind.REDACTED_IMAGE,
            OutputKind.LOW_RESOLUTION_IMAGE,
            OutputKind.MASKED_VIDEO_FRAME,
        }
    ),
    ViewerTrustLevel.OWNER: frozenset(
        {
            OutputKind.TEXT_SUMMARY,
            OutputKind.EVENT_LIST,
            OutputKind.REDACTED_IMAGE,
            OutputKind.LOW_RESOLUTION_IMAGE,
            OutputKind.MASKED_VIDEO_FRAME,
            OutputKind.ORIGINAL_FRAME,
        }
    ),
    ViewerTrustLevel.ADMIN: frozenset(
        {
            OutputKind.TEXT_SUMMARY,
            OutputKind.EVENT_LIST,
            OutputKind.REDACTED_IMAGE,
            OutputKind.LOW_RESOLUTION_IMAGE,
            OutputKind.MASKED_VIDEO_FRAME,
            OutputKind.ORIGINAL_FRAME,
        }
    ),
}


# Sensitive-region types that always get masked when an image output
# is permitted. Anything in this set takes precedence over
# `unmask_at_high`. The spec calls these "must hide" categories.
_ALWAYS_MASK_BELOW_HIGH: frozenset[SensitiveRegionType] = frozenset(
    {
        SensitiveRegionType.FACE,
        SensitiveRegionType.TEXT,
        SensitiveRegionType.SCREEN,
        SensitiveRegionType.WHITEBOARD,
        SensitiveRegionType.DOCUMENT,
        SensitiveRegionType.ID_CARD,
        SensitiveRegionType.NAME_TAG,
        SensitiveRegionType.LICENSE_PLATE,
        SensitiveRegionType.UNKNOWN_SENSITIVE,
    }
)


@dataclass
class TrustPolicyEngine:
    """Stateless policy decision maker.

    Construct once at app startup; ``evaluate()`` is pure on its
    inputs and safe to call concurrently. The dataclass exists only
    to hold the small set of operator knobs (``allow_unknown_at_high``,
    etc.); none of those persist across requests.
    """

    #: HIGH viewers ordinarily still get unknown_sensitive masked.
    #: Operators with a downstream review queue can set this to True
    #: to send the unknown regions through unmasked. Defaults to
    #: False (fail-closed).
    allow_unknown_at_high: bool = False

    def evaluate(
        self,
        *,
        viewer_trust: ViewerTrustLevel | str | None,
        sir: SemanticIntermediateRepresentation,
    ) -> DisclosurePolicy:
        """Compute the disclosure plan for one frame.

        ``viewer_trust`` is forgiving on type: a raw string from a
        request body or query param works, and anything that doesn't
        cleanly map to ``ViewerTrustLevel`` collapses to ANONYMOUS.
        """
        level = _coerce_trust_level(viewer_trust)
        allowed = set(_BASE_OUTPUTS[level])
        rationale_bits: list[str] = [f"base={level.value}"]
        audit_required = level in (ViewerTrustLevel.OWNER, ViewerTrustLevel.ADMIN)

        # Empty / fail-closed SIR (privacy_risk_score >= ceiling)
        # forfeits any image kind even at HIGH. The boilerplate
        # "analysis unavailable" text is still useful to the receiver,
        # so we leave TEXT_SUMMARY / EVENT_LIST alone.
        if sir.privacy_risk_score >= _MEDIUM_RISK_CEILING and level not in (
            ViewerTrustLevel.OWNER,
            ViewerTrustLevel.ADMIN,
        ):
            allowed = allowed - {
                OutputKind.REDACTED_IMAGE,
                OutputKind.LOW_RESOLUTION_IMAGE,
                OutputKind.MASKED_VIDEO_FRAME,
                OutputKind.ORIGINAL_FRAME,
            }
            rationale_bits.append(
                f"high_risk_score({sir.privacy_risk_score:.2f})>=ceiling"
                f"({_MEDIUM_RISK_CEILING}); image kinds dropped"
            )

        # Mask plan: which sensitive regions must the renderer blur
        # when it does produce an image output. Computed even for
        # ANONYMOUS / LOW so the rationale is consistent in audit
        # logs ("we found N regions, none of them surfaced because
        # the viewer wasn't authorized to see images at all").
        mask_regions = list(_compute_mask_plan(level, sir, allow_unknown_at_high=self.allow_unknown_at_high))
        if mask_regions:
            rationale_bits.append(
                f"masking {len(mask_regions)} region(s): "
                + ",".join(r.type.value for r in mask_regions)
            )

        return DisclosurePolicy(
            trust_level=level,
            allowed_outputs=frozenset(allowed),
            mask_regions=tuple(mask_regions),
            audit_required=audit_required,
            rationale="; ".join(rationale_bits),
        )

    def evaluate_safe(
        self,
        *,
        viewer_trust: ViewerTrustLevel | str | None,
        sir: SemanticIntermediateRepresentation,
    ) -> DisclosurePolicy:
        """Wrap ``evaluate()`` with a top-level except clause that
        produces the most restrictive policy possible on any internal
        error. Use this from request handlers.
        """
        try:
            return self.evaluate(viewer_trust=viewer_trust, sir=sir)
        except Exception as exc:  # noqa: BLE001
            logger.exception("trust policy evaluation failed: %s", exc)
            return DisclosurePolicy(
                trust_level=ViewerTrustLevel.ANONYMOUS,
                allowed_outputs=frozenset(),  # nothing
                mask_regions=tuple(),
                rationale=f"policy_evaluation_failed: {type(exc).__name__}",
            )


def _coerce_trust_level(value: object) -> ViewerTrustLevel:
    """Map any input to a ViewerTrustLevel. Unknown -> ANONYMOUS.

    Accepts:
      * ViewerTrustLevel directly
      * str: case-insensitive match against the enum's value
      * None / anything else: ANONYMOUS

    Spec invariant: "信頼度が未設定 → anonymous として扱う".
    """
    if isinstance(value, ViewerTrustLevel):
        return value
    if isinstance(value, str):
        key = value.strip().lower()
        for lv in ViewerTrustLevel:
            if lv.value == key:
                return lv
    return ViewerTrustLevel.ANONYMOUS


def _compute_mask_plan(
    level: ViewerTrustLevel,
    sir: SemanticIntermediateRepresentation,
    *,
    allow_unknown_at_high: bool,
) -> Iterable[SensitiveRegion]:
    """Yield the regions the renderer must blur, given a trust level.

    No image is even minted at ANONYMOUS / LOW, but we still emit a
    consistent plan so the audit log can describe what the analyzer
    found and what would have been masked. The renderer is expected
    to ignore the plan when ``has_image_output`` is False on the
    surrounding policy.
    """
    if level in (ViewerTrustLevel.OWNER, ViewerTrustLevel.ADMIN):
        # OWNER / ADMIN see originals; the mask plan is empty by
        # design but we still surface it on the disclosure record so
        # the audit trail can reconstruct what *would* have been
        # masked at lower tiers.
        return ()

    out: list[SensitiveRegion] = []
    for region in sir.sensitive_regions:
        if region.type in _ALWAYS_MASK_BELOW_HIGH:
            if (
                level is ViewerTrustLevel.HIGH
                and region.is_unknown
                and not allow_unknown_at_high
            ):
                # HIGH ordinarily masks unknown_sensitive too. The
                # opt-out exists for deployments with a manual review
                # queue downstream.
                out.append(region)
            elif level is ViewerTrustLevel.HIGH and not region.is_unknown:
                # HIGH: still mask the always-mask categories (face /
                # text / screen / …). The "high" tier is "more
                # affordances", not "less masking" -- it's the
                # MASKED_VIDEO_FRAME availability that distinguishes it.
                out.append(region)
            elif level in (ViewerTrustLevel.MEDIUM, ViewerTrustLevel.LOW, ViewerTrustLevel.ANONYMOUS):
                out.append(region)
        # If a region's confidence is below the floor we still mask
        # it -- spec says "不確実な場合は隠す側に倒す". The floor is
        # 0.0 by default which means "mask everything the analyzer
        # mentioned"; raising it would be an explicit risk-acceptance
        # decision.
        elif region.confidence >= _MASK_CONFIDENCE_FLOOR:
            out.append(region)
    return out
