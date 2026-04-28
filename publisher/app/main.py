from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException

from audit.models import AuditLogRecord
from audit.repository import SQLiteAuditRepository
from policy.engine import PolicyEngine
from policy.models import ConsentVC
from policy.store import ConsentStore
from publisher.app.config import Settings
from publisher.app.logging_utils import configure_logging
from publisher.app.models import SimulatePublishRequest
from publisher.app.mqtt_subscriber import MQTTSubscriber
from publisher.app.pipeline import MessageProcessor
from publisher.app.platform_client import PlatformClient
from publisher.app.ssi import issuer_routes, verifier_routes
from publisher.app.ssi.config import SSISettings
from publisher.app.ssi.keys import IssuerKeyStore
from publisher.app.ssi.pex_client import PEXSidecarClient
from publisher.app.ssi.presentation_defs import PresentationDefinitionStore
from publisher.app.ssi.state import SSIStateStore


configure_logging()
settings = Settings()
ssi_settings = SSISettings()

consent_store = ConsentStore(settings.consent_store_path)
audit_repo = SQLiteAuditRepository(settings.audit_db_path)
policy_engine = PolicyEngine()
platform_client = PlatformClient(settings.platform_api_url)

processor = MessageProcessor(
    publisher_id=settings.publisher_id,
    default_purpose=settings.default_purpose,
    consent_store=consent_store,
    policy_engine=policy_engine,
    audit_repo=audit_repo,
    platform_client=platform_client,
)

mqtt_subscriber = MQTTSubscriber(
    host=settings.mqtt_broker_host,
    port=settings.mqtt_broker_port,
    topics=settings.topic_list,
    processor=processor,
)

app = FastAPI(title="IW3IP Data Publisher", version="0.1.0")
app.state.ingested = []

import logging
from starlette.requests import Request as _StarletteRequest
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_ssi_error_log = logging.getLogger("ssi.error")


@app.exception_handler(HTTPException)
async def _log_http_exception(request: _StarletteRequest, exc: HTTPException):
    if exc.status_code >= 400:
        _ssi_error_log.error("HTTP %s on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def _log_validation_exception(request: _StarletteRequest, exc: RequestValidationError):
    _ssi_error_log.error("422 on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

ssi_keys = IssuerKeyStore(ssi_settings.issuer_key_path)
ssi_state = SSIStateStore(
    offer_ttl=ssi_settings.offer_ttl_seconds,
    response_ttl=ssi_settings.response_ttl_seconds,
)
ssi_definitions = PresentationDefinitionStore(ssi_settings.presentation_defs_dir)
ssi_pex_client = PEXSidecarClient(ssi_settings.pex_sidecar_url)

app.include_router(
    issuer_routes.build_router(
        issuer_routes.IssuerDeps(
            settings=ssi_settings, keys=ssi_keys, state=ssi_state
        )
    )
)
app.include_router(
    verifier_routes.build_router(
        verifier_routes.VerifierDeps(
            settings=ssi_settings,
            keys=ssi_keys,
            state=ssi_state,
            definitions=ssi_definitions,
            audit_repo=audit_repo,
            pex_client=ssi_pex_client,
        )
    )
)


@app.on_event("startup")
def on_startup() -> None:
    mqtt_subscriber.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    mqtt_subscriber.stop()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "publisher"}


@app.get("/consents")
def list_consents() -> list[dict]:
    return [c.model_dump(mode="json") for c in consent_store.list()]


@app.post("/consents")
def create_or_update_consent(consent: ConsentVC) -> dict:
    stored = consent_store.upsert(consent)
    return {"status": "stored", "consent": stored.model_dump(mode="json")}


@app.delete("/consents/{vc_id}")
def delete_consent(vc_id: str) -> dict:
    deleted = consent_store.delete(vc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Consent not found")
    return {"status": "deleted", "vc_id": vc_id}


@app.post("/simulate/publish")
def simulate_publish(req: SimulatePublishRequest) -> dict:
    return processor.process_message(req.topic, req.payload, req.purpose)


@app.get("/audit/logs")
def list_audit_logs(limit: int = 100) -> list[dict]:
    return audit_repo.list_recent(limit)


@app.post("/platform/ingest")
def platform_ingest(
    body: dict,
    authorization: str | None = Header(default=None),
) -> dict:
    # Bearer header is the wallet/PolicyToken path. No header = legacy
    # Phase 2 consent_store path (see /consents JSON), kept for the existing
    # webcam-event-sharing / environment-disaster hands-on flows.
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="invalid_authorization_header")
        dataset_id = body.get("dataset_id")
        if not dataset_id:
            raise HTTPException(status_code=400, detail="dataset_id_required")
        # Try PolicyToken first (single-use, Stage 1).
        # Fall through to ServiceToken (multi-use, M2M) if not recognized.
        pt, p_reason = ssi_state.consume_policy_token(token, dataset_id=dataset_id)
        st = None
        s_reason = None
        if not pt and p_reason == "unknown":
            st, s_reason = ssi_state.use_service_token(token, dataset_id=dataset_id)
        if not pt and not st:
            # Prefer the more informative error: if ServiceToken matched but
            # had a non-trivial issue (expired/dataset_mismatch), surface that;
            # otherwise default to the PolicyToken error space (which Stage 1
            # users expect and which is also right for "really unknown token").
            if s_reason and s_reason != "unknown":
                reason = s_reason
                kind = "service"
            else:
                reason = p_reason
                kind = "policy"
            audit_repo.write(
                AuditLogRecord(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action="deny",
                    subject_did="unknown",
                    dataset_id=str(dataset_id),
                    purpose=str(body.get("purpose") or "unknown"),
                    reason=f"{kind}_token_{reason}",
                    message_hash="",
                    raw_topic="platform/ingest",
                    holder_did=None,
                    vc_hash=None,
                    presentation_verified="deny",
                )
            )
            status = 401 if reason in ("unknown", "expired") else 403
            raise HTTPException(status_code=status, detail=f"{kind}_token_{reason}")
        if pt:
            audit_repo.write(
                AuditLogRecord(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action="allow",
                    subject_did=pt.holder_did or "unknown",
                    dataset_id=pt.dataset_id,
                    purpose=pt.purpose,
                    reason=f"policy_token_consumed:{pt.jti}",
                    message_hash="",
                    raw_topic="platform/ingest",
                    holder_did=pt.holder_did,
                    vc_hash=None,
                    presentation_verified="allow",
                )
            )
        else:
            audit_repo.write(
                AuditLogRecord(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action="allow",
                    subject_did=st.holder_did or "unknown",
                    dataset_id=st.dataset_id,
                    purpose=str(body.get("purpose") or "write_continuous"),
                    reason=f"service_token_used:{st.jti}:{st.write_count}",
                    message_hash="",
                    raw_topic="platform/ingest",
                    holder_did=st.holder_did,
                    vc_hash=None,
                    presentation_verified="allow",
                )
            )
    app.state.ingested.append(body)
    return {"status": "received", "count": len(app.state.ingested)}


@app.get("/platform/data")
def platform_data(
    dataset_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    """Read ingested rows for a dataset, gated by ViewerToken (Stage 3)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization_header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid_authorization_header")
    vt, reason = ssi_state.use_viewer_token(token, dataset_id=dataset_id)
    if not vt:
        audit_repo.write(
            AuditLogRecord(
                ts=datetime.now(timezone.utc).isoformat(),
                action="deny",
                subject_did="unknown",
                dataset_id=dataset_id,
                purpose="read",
                reason=f"viewer_token_{reason}",
                message_hash="",
                raw_topic="platform/data",
                holder_did=None,
                vc_hash=None,
                presentation_verified="deny",
            )
        )
        status = 401 if reason in ("unknown", "expired") else 403
        raise HTTPException(status_code=status, detail=f"viewer_token_{reason}")
    rows = [r for r in app.state.ingested if r.get("dataset_id") == dataset_id]
    audit_repo.write(
        AuditLogRecord(
            ts=datetime.now(timezone.utc).isoformat(),
            action="allow",
            subject_did=vt.holder_did or "unknown",
            dataset_id=vt.dataset_id,
            purpose="read",
            reason=f"viewer_token_used:{vt.jti}:{vt.read_count}",
            message_hash="",
            raw_topic="platform/data",
            holder_did=vt.holder_did,
            vc_hash=None,
            presentation_verified="allow",
        )
    )
    return {
        "dataset_id": vt.dataset_id,
        "count": len(rows),
        "read_count": vt.read_count,
        "rows": rows,
    }


# ---- Marketplace VC Bridge (v2 / M2) ----
# The bridge service POSTs here when a Merchandise.Purchase event fires.
# We record the (eth_addr, tx_hash, merchandise) context and return an
# OID4VCI offer URL bound to that context. The actual PurchaseViewerVC
# type (with merchandise/tx claims) lands in M3; for M2 we return an
# offer that issues a regular ViewerVC scoped to the dataset.

import json as _json
import urllib.parse as _urllib
from publisher.app.ssi.url_utils import externally_reachable_base_url
from starlette.requests import Request as _Request


@app.post("/marketplace/claim")
def marketplace_claim(body: dict, request: _Request) -> dict:
    required_fields = (
        "merchandise_address",
        "buyer_eth_addr",
        "tx_hash",
        "dataset_id",
    )
    for f in required_fields:
        if not body.get(f):
            raise HTTPException(status_code=400, detail=f"missing_field:{f}")

    claim, created = ssi_state.create_marketplace_claim(
        merchandise_address=body["merchandise_address"],
        buyer_eth_addr=body["buyer_eth_addr"],
        tx_hash=body["tx_hash"],
        dataset_id=body["dataset_id"],
        purchase_amount_wei=str(body.get("purchase_amount_wei", "0")),
    )

    # Stitch the claim's pre_authorized_code into a credential offer that
    # the publisher's existing /issuer/* path knows how to redeem. M3 will
    # extend offer creation to fold merchandise context into the issued
    # PurchaseViewerVC; for now we register the claim's code as a regular
    # ViewerVC offer for the dataset.
    if created:
        # Reserve an Offer entry so /issuer/token can find the
        # pre_authorized_code we just minted.
        ssi_state._offers[claim.pre_authorized_code] = (  # noqa: SLF001
            __import__("publisher.app.ssi.state", fromlist=["Offer"]).Offer(
                pre_authorized_code=claim.pre_authorized_code,
                credential_config_id="ViewerVC",  # M3: switch to PurchaseViewerVC
                dataset_id=claim.dataset_id,
                purpose="read",
                allowed_purposes=["read"],
                created_at=claim.created_at,
                vc_kind="ViewerVC",  # M3: PurchaseViewerVC
            )
        )
        audit_repo.write(
            AuditLogRecord(
                ts=datetime.now(timezone.utc).isoformat(),
                action="allow",
                subject_did=f"eth:{claim.buyer_eth_addr}",
                dataset_id=claim.dataset_id,
                purpose="purchase",
                reason=f"claim_received:{claim.claim_id}:tx={claim.tx_hash}",
                message_hash="",
                raw_topic="marketplace/claim",
                holder_did=None,  # M3 fills this in once wallet completes
                vc_hash=None,
                presentation_verified="allow",
            )
        )

    public_base = externally_reachable_base_url(request, ssi_settings.issuer_base_url)
    co = {
        "credential_issuer": public_base,
        "credential_configuration_ids": ["ViewerVC"],
        "grants": {
            "urn:ietf:params:oauth:grant-type:pre-authorized_code": {
                "pre-authorized_code": claim.pre_authorized_code,
            }
        },
    }
    deeplink = (
        "openid-credential-offer://?credential_offer="
        + _urllib.quote(_json.dumps(co, separators=(",", ":")))
    )
    offer_url = (
        f"{public_base}/issuer/offer?type=ViewerVC"
        f"&dataset_id={_urllib.quote(claim.dataset_id)}&purpose=read"
        f"&claim_id={claim.claim_id}"
    )
    return {
        "claim_id": claim.claim_id,
        "offer_url": offer_url,
        "deeplink": deeplink,
        "merchandise_address": claim.merchandise_address,
        "buyer_eth_addr": claim.buyer_eth_addr,
        "tx_hash": claim.tx_hash,
        "created": created,
    }


@app.get("/marketplace/claim/{claim_id}")
def marketplace_claim_status(claim_id: str) -> dict:
    c = ssi_state.get_marketplace_claim(claim_id)
    if not c:
        raise HTTPException(status_code=404, detail="claim_not_found")
    return {
        "claim_id": c.claim_id,
        "merchandise_address": c.merchandise_address,
        "buyer_eth_addr": c.buyer_eth_addr,
        "tx_hash": c.tx_hash,
        "dataset_id": c.dataset_id,
        "status": "delivered" if c.holder_did else "pending",
        "holder_did": c.holder_did,
    }
