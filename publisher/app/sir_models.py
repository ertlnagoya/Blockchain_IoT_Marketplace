"""Semantic Intermediate Representation (SIR) for the Stage T+ pipeline.

The pipeline this module backs:

  Camera / Video Source       (iPhone /provider page, getUserMedia)
       ↓
  Frame Sampler               (page-side throttle + server-side rate cap)
       ↓
  SemanticAnalyzer            (semantic_analyzer.py: Mock | Vision-OpenCV | …)
       ↓
  Semantic Intermediate       (this module: structured JSON, never raw pixels)
  Representation
       ↓
  TrustPolicyEngine           (trust_policy.py)
       ↓
  TrustAwareRenderer          (trust_aware_renderer.py)
       ↓
  Viewer Output               (textSummary / eventList / redactedImage / …)

Why a structured intermediate exists at all (research design):

* Raw frames are never the source of truth for the receiver. We pass
  the SIR into the policy engine and renderer, so a low-trust viewer
  can never receive bytes that the analyzer didn't first account for.
* Bounding boxes are normalised to [0, 1] so a single mask plan
  applies regardless of downstream resolution choices (low-res preview
  vs. full-resolution masked).
* An ``unknown_sensitive`` bucket exists so we can be explicit about
  "we suspect this region is risky but cannot classify it" -- the
  policy engine treats those as fail-closed at medium and below.

This module is purely Pydantic v2 type definitions. No I/O, no
analysis logic. Keep it that way -- the pipeline's value is that
every layer can be tested in isolation against these schemas.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ViewerTrustLevel(str, enum.Enum):
    """Discrete trust bands for receivers.

    Mapped to the existing Stage T access_level field where it makes
    sense:
        anonymous  -- caller has presented no VC; bare HTTP read
        low        -- summary tier (DataUserVC score 50-59 with VLM on)
        medium     -- access tier (DataUserVC score >= 60, non-gov)
        high       -- full tier (DataUserVC score >= 80 + gov/police)
        owner      -- the SellerVC holder for the dataset
        admin      -- platform operator (audit-logged)

    `unknown` does not exist on purpose. Any code that ends up unable
    to derive a level must fall through to ``ANONYMOUS`` (fail-closed).
    """

    ANONYMOUS = "anonymous"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    OWNER = "owner"
    ADMIN = "admin"


class SensitiveRegionType(str, enum.Enum):
    """Privacy-sensitive region categories the analyzer can emit.

    `unknown_sensitive` is intentionally part of the enum, not a
    fallback hidden in code: it lets the analyzer say "I think this
    region is risky but I can't tell you why". The policy engine
    treats it as fail-closed at medium and below, by spec.
    """

    FACE = "face"
    PERSON = "person"
    TEXT = "text"
    SCREEN = "screen"
    WHITEBOARD = "whiteboard"
    DOCUMENT = "document"
    ID_CARD = "id_card"
    NAME_TAG = "name_tag"
    LICENSE_PLATE = "license_plate"
    UNKNOWN_SENSITIVE = "unknown_sensitive"


# A normalized confidence in [0, 1]. We keep this typed so accidental
# percent-vs-fraction mistakes (84 vs 0.84) get caught at validation
# time rather than silently masking a real PII region.
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class BoundingBox(BaseModel):
    """Normalized bounding box, x/y/width/height all in [0, 1].

    Origin is top-left, x grows right, y grows down (matches OpenCV /
    HTML canvas / Apple Vision). Percent-style absolute pixel boxes
    are rejected by validation so a raw cv2 (x1,y1,x2,y2) can't sneak
    through unconverted.
    """

    model_config = ConfigDict(frozen=True)

    x: Annotated[float, Field(ge=0.0, le=1.0)]
    y: Annotated[float, Field(ge=0.0, le=1.0)]
    width: Annotated[float, Field(ge=0.0, le=1.0)]
    height: Annotated[float, Field(ge=0.0, le=1.0)]

    def clamped(self) -> "BoundingBox":
        """Return a copy with width/height clipped so the box stays
        inside the unit square. Useful when an analyzer reports a box
        that mathematically extends past the frame edge."""
        max_w = max(0.0, min(1.0 - self.x, self.width))
        max_h = max(0.0, min(1.0 - self.y, self.height))
        return BoundingBox(x=self.x, y=self.y, width=max_w, height=max_h)


class DetectedObject(BaseModel):
    """Generic object detection. Used for non-sensitive labels too
    (chair, table, etc.) so downstream renderers can describe scenes.
    Not all objects are privacy-sensitive; sensitive ones get a
    dedicated entry in `sensitive_regions` with the same bbox so
    masking has a single source of truth.
    """

    model_config = ConfigDict(frozen=True)

    label: str
    confidence: Confidence
    bbox: BoundingBox


class SensitiveRegion(BaseModel):
    """Spatial region the analyzer flags as privacy-sensitive."""

    model_config = ConfigDict(frozen=True)

    type: SensitiveRegionType
    confidence: Confidence
    bbox: BoundingBox
    reason: str = Field(default="")

    @property
    def is_unknown(self) -> bool:
        """Used by the policy engine: unknown_sensitive must hide at
        medium and below by spec."""
        return self.type is SensitiveRegionType.UNKNOWN_SENSITIVE


class DetectedEvent(BaseModel):
    """High-level scene event the analyzer derives. Examples:
    `person_detected`, `motion_in_entryway`, `screen_visible`. Events
    are how the renderer constructs `eventList` for low-trust viewers."""

    model_config = ConfigDict(frozen=True)

    type: str
    description: str
    confidence: Confidence


class PeopleSummary(BaseModel):
    """Aggregated people info. `count` is non-PII; `identities` is
    deliberately a placeholder for future face-matching backends and
    the MVP must always leave it empty."""

    model_config = ConfigDict(frozen=True)

    count: int = Field(ge=0)
    identities: list[str] = Field(default_factory=list)


class SemanticIntermediateRepresentation(BaseModel):
    """The single artefact every layer downstream of the analyzer
    operates on. Once an SIR exists, the renderer never goes back to
    the raw frame for low-trust viewers.

    The schema mirrors the example in the spec. Renames vs the
    JS-style spec example:
        capturedAt        -> captured_at
        sceneSummary      -> scene_summary
        sensitiveRegions  -> sensitive_regions
        privacyRiskScore  -> privacy_risk_score
        analyzerVersion   -> analyzer_version
    These follow the existing publisher Pydantic style (snake_case);
    the JSON serialiser emits them as-is, which is fine for the
    server-internal contract. If a JS client needs the camelCase
    spelling later, add `populate_by_name` + aliases here.
    """

    model_config = ConfigDict(frozen=True)

    frame_id: str
    source_device_id: str
    captured_at: datetime
    scene_summary: str = Field(default="")
    objects: list[DetectedObject] = Field(default_factory=list)
    people: PeopleSummary = Field(default_factory=lambda: PeopleSummary(count=0))
    sensitive_regions: list[SensitiveRegion] = Field(default_factory=list)
    events: list[DetectedEvent] = Field(default_factory=list)
    privacy_risk_score: Confidence = 0.0
    analyzer_version: str = "unknown"

    @classmethod
    def empty(
        cls,
        *,
        frame_id: str,
        source_device_id: str,
        analyzer_version: str = "unknown",
    ) -> "SemanticIntermediateRepresentation":
        """Construct an SIR with no detections but the audit fields
        set. Used by the analyzer layer when a frame is unanalysable
        (corrupted bytes, decoder error). Combined with a non-trivial
        `privacy_risk_score`, this makes the policy engine treat the
        frame as fail-closed: nothing is known about it, so nothing
        beyond a generic event is shown."""
        return cls(
            frame_id=frame_id,
            source_device_id=source_device_id,
            captured_at=datetime.now(timezone.utc),
            scene_summary="(analysis unavailable; treat as private)",
            privacy_risk_score=1.0,
            analyzer_version=analyzer_version,
        )
