"""Semantic analyzer interface + concrete implementations.

Every analyzer takes raw image bytes and returns an SIR
(``sir_models.SemanticIntermediateRepresentation``). No analyzer
is allowed to leak the raw bytes back through the SIR; if it cannot
analyze the frame, it must return ``SemanticIntermediateRepresentation.empty()``
which signals "treat as private" downstream.

Backends shipped here:

* ``MockSemanticAnalyzer`` -- deterministic SIR. Used by tests and by
  the dev path where the operator just wants to exercise the policy
  engine + renderer without an actual model. Produces a person + a
  face + an unknown-sensitive region so the fail-closed branches all
  get exercised.

* ``VisionSemanticAnalyzer`` -- OpenCV Haar cascade for faces, plus
  some lightweight heuristics for text-heavy regions (rectangular
  high-contrast blobs become ``unknown_sensitive`` -- we cannot tell
  whiteboard from screen from poster from this signal alone, and the
  spec says "unsure -> unknown_sensitive -> hide"). Apple Vision /
  CoreML / a real VLM would slot in by implementing ``SemanticAnalyzer``
  and registering with the same ``from_settings`` factory.

What this module deliberately does NOT do:

* Send images to any external service. The function signatures take
  bytes in and emit JSON-shaped Pydantic objects out. There's no
  network call seam in this file by design.
* Persist images to disk (other than what OpenCV needs to decode).
* Identify individuals. ``PeopleSummary.identities`` stays empty in
  every backend until a separate, audit-logged identification module
  is added.

See `sir_models.py` for the data contract and `trust_policy.py` for
how SIRs flow into per-tier disclosure decisions.
"""
from __future__ import annotations

import abc
import hashlib
import logging
import uuid
from datetime import datetime, timezone

from publisher.app.sir_models import (
    BoundingBox,
    DetectedEvent,
    DetectedObject,
    PeopleSummary,
    SemanticIntermediateRepresentation,
    SensitiveRegion,
    SensitiveRegionType,
)


logger = logging.getLogger(__name__)


class SemanticAnalyzerError(Exception):
    """Anything raised from an analyzer's ``analyze()`` MUST be a
    subclass of this so the call site has a single except clause for
    fail-closed handling. Don't let a bare ImportError or cv2 error
    bubble up: the pipeline assumes any exception here means
    "decoder failed -> treat as private".
    """


class SemanticAnalyzer(abc.ABC):
    """Strategy interface every analyzer implementation backs.

    Implementations should be cheap to construct and safe to call
    concurrently from request-handling threads -- one analyzer
    instance is shared across requests (FastAPI default), and frame
    sampling on the page side is the throttle. If a backend keeps
    expensive state (model weights), that's fine, but
    ``analyze()`` itself must be re-entrant.
    """

    #: Name embedded into the SIR's `analyzer_version` field. Important
    #: for audit logs: a per-analyzer identifier survives logs even
    #: when the SIR is otherwise discarded for privacy.
    name: str

    @abc.abstractmethod
    def analyze(
        self, *, image_bytes: bytes, source_device_id: str
    ) -> SemanticIntermediateRepresentation:
        """Return an SIR for the input frame.

        Raises ``SemanticAnalyzerError`` on any unrecoverable failure.
        Callers should catch and fall through to
        ``SemanticIntermediateRepresentation.empty()`` so the policy
        engine sees a "high risk, no data" SIR rather than a missing
        SIR (which is harder to express fail-closed).
        """

    @classmethod
    def from_settings(cls, settings) -> "SemanticAnalyzer":
        """Factory dispatching on `settings.semantic_analyzer_backend`.

        Backends recognised: ``stub`` (alias ``mock``), ``vision``
        (alias ``opencv``). Anything else -- including the empty
        string -- returns the mock backend. We intentionally do NOT
        make this raise on unknown values: a misconfigured operator
        getting deterministic stub output is safer than the pipeline
        failing closed and surfacing nothing.
        """
        backend = (getattr(settings, "semantic_analyzer_backend", "") or "").lower()
        if backend in ("vision", "opencv"):
            return VisionSemanticAnalyzer()
        # default for empty / "stub" / "mock" / unrecognised
        return MockSemanticAnalyzer()


class MockSemanticAnalyzer(SemanticAnalyzer):
    """Deterministic stub. Same input bytes always produce the same
    SIR -- tests rely on this. The output deliberately exercises the
    full schema so policy / renderer tests have real material to mask.
    """

    name = "mock-semantic-analyzer/v1"

    def analyze(
        self, *, image_bytes: bytes, source_device_id: str
    ) -> SemanticIntermediateRepresentation:
        sha = hashlib.sha256(image_bytes).hexdigest()
        # Stable but content-derived UUID so tests can compare runs
        # without worrying about clock-based id collisions.
        frame_id = str(uuid.UUID(sha[:32]))

        face = SensitiveRegion(
            type=SensitiveRegionType.FACE,
            confidence=0.94,
            bbox=BoundingBox(x=0.18, y=0.20, width=0.08, height=0.10),
            reason="顔が写っているため",
        )
        text = SensitiveRegion(
            type=SensitiveRegionType.TEXT,
            confidence=0.72,
            bbox=BoundingBox(x=0.52, y=0.21, width=0.30, height=0.16),
            reason="画面または白板上の文字情報の可能性があるため",
        )
        unknown = SensitiveRegion(
            type=SensitiveRegionType.UNKNOWN_SENSITIVE,
            confidence=0.45,
            bbox=BoundingBox(x=0.75, y=0.65, width=0.15, height=0.20),
            reason="高コントラストな矩形領域。種別を断定できないため安全側で隠す",
        )

        return SemanticIntermediateRepresentation(
            frame_id=frame_id,
            source_device_id=source_device_id,
            captured_at=datetime.now(timezone.utc),
            scene_summary="研究室の入口付近に1人の人物がいる（mock出力）",
            objects=[
                DetectedObject(
                    label="person",
                    confidence=0.91,
                    bbox=BoundingBox(x=0.12, y=0.18, width=0.22, height=0.51),
                ),
            ],
            people=PeopleSummary(count=1),
            sensitive_regions=[face, text, unknown],
            events=[
                DetectedEvent(
                    type="person_detected",
                    description="人物が検出された",
                    confidence=0.91,
                ),
            ],
            privacy_risk_score=0.78,
            analyzer_version=self.name,
        )


class VisionSemanticAnalyzer(SemanticAnalyzer):
    """OpenCV Haar-cascade face detector + a coarse text-region
    heuristic. The MVP stand-in for an Apple Vision / Core ML / VLM
    backend. Always conservative: any high-contrast rectangular blob
    becomes ``unknown_sensitive`` rather than ``screen``/``whiteboard``,
    because the policy engine treats unknown as fail-closed at medium
    and below.
    """

    name = "vision-opencv/v1"

    def analyze(
        self, *, image_bytes: bytes, source_device_id: str
    ) -> SemanticIntermediateRepresentation:
        sha = hashlib.sha256(image_bytes).hexdigest()
        frame_id = str(uuid.UUID(sha[:32]))
        captured_at = datetime.now(timezone.utc)

        try:
            import cv2  # type: ignore[import-not-found]
            import numpy as np  # type: ignore[import-not-found]
        except ImportError as exc:
            raise SemanticAnalyzerError(
                "vision backend requires cv2 + numpy; install "
                "opencv-python-headless or fall back to MockSemanticAnalyzer"
            ) from exc

        try:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise SemanticAnalyzerError("opencv could not decode frame")
            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # ------------- face detection ----------------
            from pathlib import Path

            cascade_path = (
                Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            )
            cascade = cv2.CascadeClassifier(str(cascade_path))
            face_rects = cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            sensitive_regions: list[SensitiveRegion] = []
            objects: list[DetectedObject] = []
            for (x, y, fw, fh) in face_rects:
                bbox = BoundingBox(
                    x=x / w, y=y / h, width=fw / w, height=fh / h
                ).clamped()
                sensitive_regions.append(
                    SensitiveRegion(
                        type=SensitiveRegionType.FACE,
                        confidence=0.85,  # Haar cascades don't return a real prob
                        bbox=bbox,
                        reason="OpenCV Haar cascade frontal-face detection",
                    )
                )
                # Each detected face implies a person; emit a person bbox
                # spanning ~3x the face area as a coarse approximation.
                person_bbox = BoundingBox(
                    x=max(0.0, (x - fw) / w),
                    y=max(0.0, (y - fh / 2) / h),
                    width=min(1.0, (3 * fw) / w),
                    height=min(1.0, (4 * fh) / h),
                ).clamped()
                objects.append(
                    DetectedObject(label="person", confidence=0.7, bbox=person_bbox)
                )

            # ------------- text-likely region heuristic ----------------
            # MSER finds maximally stable regions which over-fire on
            # text. We bucket them as `unknown_sensitive` (not `text`)
            # because we can't tell text from logos from random
            # high-contrast geometry, and the spec wants us to fail
            # closed when uncertain.
            try:
                mser = cv2.MSER_create()
                regions, _ = mser.detectRegions(gray)
                # group into a single coarse hull so we don't emit
                # hundreds of micro-regions; the policy engine cares
                # about whether risky pixels exist, not where each char is
                if regions:
                    pts = np.concatenate([r for r in regions], axis=0)
                    rx, ry, rw, rh = cv2.boundingRect(pts)
                    if rw > 0.05 * w and rh > 0.05 * h:
                        text_bbox = BoundingBox(
                            x=rx / w, y=ry / h, width=rw / w, height=rh / h
                        ).clamped()
                        sensitive_regions.append(
                            SensitiveRegion(
                                type=SensitiveRegionType.UNKNOWN_SENSITIVE,
                                confidence=0.5,
                                bbox=text_bbox,
                                reason=(
                                    "MSER 高コントラスト領域: "
                                    "テキスト/画面/ロゴの可能性。種別不明のため隠す"
                                ),
                            )
                        )
            except Exception as inner:  # noqa: BLE001
                # MSER is optional; missing it shouldn't fail the whole
                # analyzer. Log at debug only -- we never log the
                # frame contents.
                logger.debug("MSER skipped: %s", inner)

            # ------------- people summary + events ----------------
            people_count = len(face_rects)
            events: list[DetectedEvent] = []
            if people_count:
                events.append(
                    DetectedEvent(
                        type="person_detected",
                        description=f"{people_count} 人の人物が検出された",
                        confidence=0.85,
                    )
                )

            # ------------- privacy risk score ----------------
            # Combination heuristic: more sensitive regions -> higher
            # risk. unknown_sensitive contributes the most because we
            # can't tell what it actually is.
            risk = 0.0
            for r in sensitive_regions:
                if r.is_unknown:
                    risk += 0.5
                elif r.type is SensitiveRegionType.FACE:
                    risk += 0.4
                else:
                    risk += 0.3
            risk = min(1.0, risk)

            scene_summary = (
                f"{people_count} 人の人物 + {len(sensitive_regions)} 件のセンシティブ領域"
                if people_count or sensitive_regions
                else "人物・センシティブ領域は検出されませんでした"
            )

            return SemanticIntermediateRepresentation(
                frame_id=frame_id,
                source_device_id=source_device_id,
                captured_at=captured_at,
                scene_summary=scene_summary,
                objects=objects,
                people=PeopleSummary(count=people_count),
                sensitive_regions=sensitive_regions,
                events=events,
                privacy_risk_score=risk,
                analyzer_version=self.name,
            )
        except SemanticAnalyzerError:
            raise
        except Exception as exc:  # noqa: BLE001
            # Anything below cv2 (memory, decode quirks, …) is wrapped
            # so the call site has one exception type to catch.
            raise SemanticAnalyzerError(
                f"vision analyzer failed: {type(exc).__name__}: {exc}"
            ) from exc
