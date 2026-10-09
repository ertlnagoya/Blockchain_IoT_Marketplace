from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
import logging

from audit.models import AuditLogRecord
from audit.repository import SQLiteAuditRepository
from policy.engine import PolicyEngine
from policy.store import ConsentStore
from schemas.models import normalize
from publisher.app.image_redactor import ImageRedactor, RedactionError
from publisher.app.platform_client import PlatformClient
from publisher.app.vlm_client import VLMClient, VLMError


logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(
        self,
        publisher_id: str,
        default_purpose: str,
        consent_store: ConsentStore,
        policy_engine: PolicyEngine,
        audit_repo: SQLiteAuditRepository,
        platform_client: PlatformClient,
        vlm_client: VLMClient | None = None,
        image_redactor: ImageRedactor | None = None,
    ) -> None:
        self.publisher_id = publisher_id
        self.default_purpose = default_purpose
        self.consent_store = consent_store
        self.policy_engine = policy_engine
        self.audit_repo = audit_repo
        self.platform_client = platform_client
        # Stage T (VLM extension): optional injectors. When both are
        # None the pipeline runs exactly the legacy path -- existing
        # tier projection / pipeline tests must not regress.
        self.vlm_client = vlm_client
        self.image_redactor = image_redactor

    def process_message(self, topic: str, payload: dict, purpose: str | None = None) -> dict:
        normalized = normalize(topic, payload)
        used_purpose = purpose or self.default_purpose

        payload_canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        message_hash = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()

        matched_consents = self.consent_store.find_by_dataset(normalized.dataset_id)
        decision = self.policy_engine.evaluate(
            dataset_id=normalized.dataset_id,
            purpose=used_purpose,
            consents=matched_consents,
            now=datetime.now(timezone.utc),
        )

        if not decision.allowed or decision.consent is None:
            self.audit_repo.write(
                AuditLogRecord(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action="deny",
                    subject_did="unknown",
                    dataset_id=normalized.dataset_id,
                    purpose=used_purpose,
                    reason=decision.reason,
                    message_hash=message_hash,
                    raw_topic=topic,
                )
            )
            return {
                "status": "denied",
                "dataset_id": normalized.dataset_id,
                "reason": decision.reason,
            }

        envelope = {
            "dataset_id": normalized.dataset_id,
            "schema_version": normalized.schema_version,
            "subject_did": decision.consent.subject_did,
            "purpose": used_purpose,
            "payload": normalized.model_dump(mode="json"),
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "publisher_id": self.publisher_id,
        }

        # Stage T (case alpha + B) — hoist trust-tier-relevant media
        # fields to the envelope's top level. /platform/data's
        # allowed_views projection filters these keys per tier; without
        # this hoist /simulate/publish would bury them inside
        # `payload.payload.data` and the projection never bites.
        # `image_url` / `video_url` are case B (publisher-hosted media
        # gateway); `image_cid` / `video_cid` are case alpha + the
        # forthcoming case C (real IPFS).
        for _media_key in (
            "image_cid",
            "image_url",
            "video_cid",
            "video_url",
            "video_duration_sec",
        ):
            if not isinstance(payload, dict):
                break
            if _media_key in payload:
                envelope.setdefault(_media_key, payload[_media_key])
                continue
            inner = payload.get("data")
            if isinstance(inner, dict) and _media_key in inner:
                envelope.setdefault(_media_key, inner[_media_key])

        # Stage T (VLM extension): when injectors are configured, derive
        # description_full / description_summary / image_url_redacted
        # from the raw image and attach them to the envelope. Both
        # injectors fail-soft: a failure produces a row that's still
        # publishable (legacy keys remain), with a processing_warnings
        # entry letting receivers know what was skipped. The
        # /platform/data tier projector decides which derived keys are
        # visible per tier.
        warnings: list[str] = []
        source_image_url = envelope.get("image_url")
        source_video_url = envelope.get("video_url")
        # Pick the source the VLM operates on. MVP: image only -- video
        # frame extraction is future work, see spec "Future work".
        vlm_source_url = source_image_url
        vlm_source_ct = (
            "image/jpeg" if source_image_url else
            ("video/mp4" if source_video_url else "")
        )
        if self.vlm_client is not None and vlm_source_url:
            try:
                derived = self.vlm_client.describe(
                    image_url=vlm_source_url,
                    content_type=vlm_source_ct,
                )
            except VLMError as exc:
                logger.warning("vlm describe failed: %s", exc)
                warnings.append("vlm_unavailable")
            else:
                envelope.update(derived)
        if self.image_redactor is not None and source_image_url:
            try:
                redacted = self.image_redactor.blur_pii(
                    image_url=source_image_url,
                    content_type=vlm_source_ct or "image/jpeg",
                )
            except RedactionError as exc:
                logger.warning("image redaction failed: %s", exc)
                warnings.append("redaction_unavailable")
            else:
                envelope.update(redacted)
        if warnings:
            envelope["processing_warnings"] = warnings

        try:
            self.platform_client.send(envelope)
            self.audit_repo.write(
                AuditLogRecord(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action="allow",
                    subject_did=decision.consent.subject_did,
                    dataset_id=normalized.dataset_id,
                    purpose=used_purpose,
                    reason="sent",
                    message_hash=message_hash,
                    raw_topic=topic,
                )
            )
            return {"status": "allowed", "dataset_id": normalized.dataset_id}
        except Exception as exc:  # noqa: BLE001
            logger.exception("send failed")
            self.audit_repo.write(
                AuditLogRecord(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action="send_error",
                    subject_did=decision.consent.subject_did,
                    dataset_id=normalized.dataset_id,
                    purpose=used_purpose,
                    reason=str(exc),
                    message_hash=message_hash,
                    raw_topic=topic,
                )
            )
            return {
                "status": "send_error",
                "dataset_id": normalized.dataset_id,
                "reason": str(exc),
            }
