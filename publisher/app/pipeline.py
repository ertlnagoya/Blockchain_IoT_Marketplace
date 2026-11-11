from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
import logging
from pathlib import Path

from audit.models import AuditLogRecord
from audit.repository import SQLiteAuditRepository
from policy.engine import PolicyEngine
from policy.store import ConsentStore
from schemas.models import normalize
from publisher.app.c2pa_provenance import (
    C2paProvenance,
    media_file_for_url,
    read_sidecar_for_url,
    sniff_type,
    store_summary_card,
    write_sidecar,
)
from publisher.app.chain_client import ProvenanceMintError, ProvenanceTokenClient
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
        media_store_path: str | None = None,
        provenance_token: ProvenanceTokenClient | None = None,
        c2pa_provenance: C2paProvenance | None = None,
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
        # Stage P (C2PA provenance): /media/upload leaves the verification
        # result of each signed image under media_store_path; when it is
        # set, rows whose image_url has one gain a `provenance` object.
        self.media_store = Path(media_store_path) if media_store_path else None
        self.provenance_token = provenance_token
        # P3: signs the Tier 1 summary card when it can sign
        self.c2pa = c2pa_provenance

    def process_message(
        self,
        topic: str,
        payload: dict,
        purpose: str | None = None,
        seller_did: str | None = None,
    ) -> dict:
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
        provenance = self._provenance(
            envelope, warnings, dataset_id=normalized.dataset_id,
            purpose=used_purpose, seller_did=seller_did or "",
        )
        if provenance:
            envelope["provenance"] = provenance
        if warnings:
            envelope["processing_warnings"] = warnings

        try:
            self.platform_client.send(envelope)
            self._audit_provenance(
                provenance, dataset_id=normalized.dataset_id, purpose=used_purpose,
                message_hash=message_hash,
            )
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

    # ---- Stage P (C2PA provenance) ----

    def _provenance(
        self, envelope: dict, warnings: list[str], *, dataset_id: str,
        purpose: str, seller_did: str,
    ) -> dict | None:
        """Build the row's ``provenance`` object (spec §7.2).

        ``manifest_label`` / ``validation_state`` / ``signer`` come from
        the verification /media/upload stored for ``image_url``;
        ``redacted_manifest_label`` from the signed Tier 2 image;
        ``derived_sha256`` is the sha256 of the Tier 1 summary text and
        ``summary_card_url`` / ``summary_manifest_label`` the signed SVG
        card that binds that hash to the capture (spec §5.5); ``token_id`` from the
        ProvenanceToken of the image (spec §8), minted before the row is
        sent because the row carries it; a retry reuses the token. /platform/data
        decides which of these each tier sees.
        """
        # Always drop the redactor's internal keys: /platform/data passes
        # unknown row keys through to every tier.
        redacted = envelope.pop("image_redacted_c2pa", None)
        derivation_failed = envelope.pop("provenance_derivation_failed", False)
        if self.media_store is None:
            return None
        source = read_sidecar_for_url(self.media_store, envelope.get("image_url"))
        out: dict = {}
        if source:
            out.update(
                manifest_label=source.get("manifest_label"),
                validation_state=source.get("validation_state"),
                signer=source.get("signer"),
            )
        if redacted and redacted.get("present"):
            out["redacted_manifest_label"] = redacted.get("manifest_label")
        if derivation_failed:
            warnings.append("provenance_derivation_unavailable")
        summary = envelope.get("description_summary")
        if out and isinstance(summary, str):
            out["derived_sha256"] = hashlib.sha256(summary.encode("utf-8")).hexdigest()
            if self.c2pa is not None and self.c2pa.can_sign and source and source.get("present"):
                card = self._summary_card(envelope, summary)
                if card is None:
                    warnings.append("provenance_summary_unavailable")
                else:
                    out.update(card)
        if source and self.provenance_token is not None:
            sha = envelope["image_url"].split("?", 1)[0].rsplit("/", 1)[1].split(".", 1)[0]
            try:
                minted = self.provenance_token.mint(
                    manifest_label=source.get("manifest_label") or "",
                    asset_sha256=sha,
                    cid=envelope.get("image_cid") or "",
                    seller_did=seller_did,
                )
            except ProvenanceMintError as exc:
                logger.warning("provenance mint failed: %s", exc)
                warnings.append("provenance_anchor_unavailable")
            else:
                out["token_id"] = minted["token_id"]
                out["token_contract"] = minted["contract"]
                if minted.get("tx_hash"):
                    out["anchor_tx"] = minted["tx_hash"]
                if minted.get("reused"):
                    out["token_reused"] = True
        return out or None

    def _summary_card(self, envelope: dict, summary: str) -> dict | None:
        """Sign the Tier 1 summary card (spec §5.5) and store it beside the
        media. Returns ``{summary_card_url, summary_manifest_label}`` or
        None when signing failed (the row still goes out, with a warning)."""
        source_url = envelope["image_url"]
        path = media_file_for_url(self.media_store, source_url)
        if path is None:
            return None
        body = path.read_bytes()
        content_type = sniff_type(body)
        if content_type is None:
            return None
        try:
            card = self.c2pa.sign_summary(
                source=body,
                content_type=content_type,
                summary=summary,
                model=envelope.get("description_model") or "",
                prompt_sha256=(
                    self.vlm_client.summary_prompt_sha256()
                    if self.vlm_client is not None else ""
                ),
            )
            checked = self.c2pa.verify(card)
        except Exception as exc:  # noqa: BLE001 - SDK and IO errors alike
            logger.warning("summary card signing failed: %s", exc)
            return None
        if checked.validation_state == "Invalid":
            logger.warning("summary card did not verify: %s", checked.failure_codes)
            return None
        sha, url = store_summary_card(self.media_store, card, source_url)
        write_sidecar(self.media_store, sha, checked)
        return {
            "summary_card_url": url,
            "summary_manifest_label": checked.manifest_label,
        }

    def _audit_provenance(
        self, provenance: dict | None, *, dataset_id: str, purpose: str,
        message_hash: str,
    ) -> None:
        if not provenance:
            return
        now = datetime.now(timezone.utc).isoformat()
        if provenance.get("redacted_manifest_label"):
            self.audit_repo.write(
                AuditLogRecord(
                    ts=now, action="allow", subject_did="publisher",
                    dataset_id=dataset_id, purpose=purpose,
                    reason=(
                        f"tier2:{provenance['redacted_manifest_label']}"
                        f":ingredient={provenance.get('manifest_label')}"
                    ),
                    message_hash=message_hash, raw_topic="provenance/derived",
                )
            )
        if provenance.get("summary_manifest_label"):
            self.audit_repo.write(
                AuditLogRecord(
                    ts=now, action="allow", subject_did="publisher",
                    dataset_id=dataset_id, purpose=purpose,
                    reason=(
                        f"tier1:{provenance['summary_manifest_label']}"
                        f":ingredient={provenance.get('manifest_label')}"
                    ),
                    message_hash=message_hash, raw_topic="provenance/derived",
                )
            )
        if provenance.get("token_id") is not None and not provenance.get("token_reused"):
            self.audit_repo.write(
                AuditLogRecord(
                    ts=now, action="allow", subject_did="publisher",
                    dataset_id=dataset_id, purpose=purpose,
                    reason=(
                        f"token:{provenance['token_id']}:tx={provenance['anchor_tx']}"
                        f":manifest={provenance.get('manifest_label')}"
                    ),
                    message_hash=message_hash, raw_topic="provenance/anchored",
                )
            )
