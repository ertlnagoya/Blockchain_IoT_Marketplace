from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from audit.models import AuditLogRecord
from audit.repository import SQLiteAuditRepository
from publisher.app.ssi.config import SSISettings
from publisher.app.ssi.html import render_qr_page
from publisher.app.ssi.keys import IssuerKeyStore
from publisher.app.ssi.pex_client import PEXSidecarClient
from publisher.app.ssi.presentation_defs import PresentationDefinitionStore
from publisher.app.ssi.sdjwt import parse_sd_jwt_vc, verify_sd_jwt_vc
from publisher.app.ssi.state import SSIStateStore
from publisher.app.ssi.url_utils import externally_reachable_base_url


logger = logging.getLogger(__name__)


@dataclass
class VerifierDeps:
    settings: SSISettings
    keys: IssuerKeyStore
    state: SSIStateStore
    definitions: PresentationDefinitionStore
    audit_repo: SQLiteAuditRepository
    pex_client: PEXSidecarClient


def _vc_hash(vp_token: str) -> str:
    compact = vp_token.split("~")[0]
    return "sha256:" + hashlib.sha256(compact.encode("utf-8")).hexdigest()


def _extract_sd_jwt_compact(raw_vp_token: str) -> str:
    """Pull the SD-JWT VC compact string out of whatever shape `vp_token` arrives in.

    PEX/SIOPv2 responses send `vp_token` as a single SD-JWT VC compact string.
    DCQL responses send it as a JSON object keyed by the credential query id
    (e.g. `{"consent_vc": "<sd-jwt>"}`) or by an array of strings. Newer wallets
    may also send a JSON array. Accept all three shapes.
    """
    s = (raw_vp_token or "").strip()
    if not s or s[0] not in "{[":
        return raw_vp_token
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return raw_vp_token
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, str) and v:
                return v
            if isinstance(v, list) and v and isinstance(v[0], str):
                return v[0]
    if isinstance(data, list) and data and isinstance(data[0], str):
        return data[0]
    return raw_vp_token


def _write_audit(
    audit_repo: SQLiteAuditRepository,
    *,
    action: str,
    reason: str,
    dataset_id: str,
    purpose: str,
    holder_did: str | None,
    vc_hash: str | None,
    verified: str,
) -> None:
    audit_repo.write(
        AuditLogRecord(
            ts=datetime.now(timezone.utc).isoformat(),
            action=action,
            subject_did=holder_did or "unknown",
            dataset_id=dataset_id,
            purpose=purpose,
            reason=reason,
            message_hash="",
            raw_topic="oid4vp/response",
            holder_did=holder_did,
            vc_hash=vc_hash,
            presentation_verified=verified,
        )
    )


def _local_pex_fallback(
    pd: dict,
    vp_token: str,
    issuer_public_jwk: dict,
    dataset_id: str,
    purpose: str,
) -> dict:
    """Fallback verification when the Node sidecar is unreachable.

    Only honors a minimal subset of PEX v2: for each input descriptor, each
    constraint field is treated as a JSONPath-like dotted path into the
    disclosed VC claims, with optional `filter.const` equality.
    """
    claims = verify_sd_jwt_vc(vp_token, issuer_public_jwk)
    for descriptor in pd.get("input_descriptors", []):
        for field in descriptor.get("constraints", {}).get("fields", []):
            paths = field.get("path", [])
            filt = field.get("filter") or {}
            const = filt.get("const")
            got = None
            for p in paths:
                if not p.startswith("$."):
                    continue
                parts = p[2:].split(".")
                cur = claims
                ok = True
                for part in parts:
                    if isinstance(cur, dict) and part in cur:
                        cur = cur[part]
                    else:
                        ok = False
                        break
                if ok:
                    got = cur
                    break
            if const is not None and got != const:
                return {
                    "verified": False,
                    "reason": f"field_mismatch:{paths[0] if paths else '?'}",
                    "claims": claims,
                    "holder_did": None,
                }
    # enforce request-time purpose/dataset
    if claims.get("dataset_id") != dataset_id:
        return {"verified": False, "reason": "dataset_mismatch", "claims": claims, "holder_did": None}
    allowed = claims.get("allowed_purposes", [])
    if purpose not in allowed:
        return {"verified": False, "reason": "purpose_mismatch", "claims": claims, "holder_did": None}
    cnf = claims.get("cnf", {}).get("jwk")
    holder_did = None
    if cnf:
        from publisher.app.ssi.did_jwk import did_jwk_from_public_jwk

        holder_did = did_jwk_from_public_jwk(cnf)
    return {"verified": True, "reason": "ok", "claims": claims, "holder_did": holder_did}


def _safe_local_pex_fallback(pd, sd_jwt, deps, req):
    try:
        return _local_pex_fallback(
            pd, sd_jwt, deps.keys.public_jwk, req.dataset_id, req.purpose
        )
    except Exception as fb_exc:  # noqa: BLE001
        return {"verified": False, "reason": f"verify_error:{fb_exc}", "claims": {}, "holder_did": None}


def build_router(deps: VerifierDeps) -> APIRouter:
    router = APIRouter()

    @router.get("/verifier/presentation-definitions/{pd_id}")
    def get_presentation_definition(pd_id: str) -> dict:
        pd = deps.definitions.get(pd_id)
        if not pd:
            raise HTTPException(status_code=404, detail="presentation_definition_not_found")
        return pd

    @router.get("/verifier/request")
    def verifier_request(
        request: Request,
        dataset_id: str = Query(...),
        purpose: str = Query(...),
    ):
        match = deps.definitions.find_for_dataset(dataset_id)
        if not match:
            raise HTTPException(status_code=404, detail="no_presentation_definition_for_dataset")
        pd_id, pd = match
        req = deps.state.create_verification_request(pd_id, dataset_id, purpose)

        public_base = externally_reachable_base_url(request, deps.settings.issuer_base_url)
        authz = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": deps.settings.issuer_base_url,
            "response_uri": f"{public_base}/verifier/response",
            "presentation_definition": pd,
            "nonce": req.nonce,
            "state": req.state,
        }
        request_uri = f"{public_base}/verifier/request_object?state={req.state}"
        deeplink = "openid4vp://?" + urllib.parse.urlencode(
            {
                "client_id": authz["client_id"],
                "request_uri": request_uri,
            }
        )

        accept = request.headers.get("accept", "")
        if "application/json" in accept or request.query_params.get("format") == "json":
            return JSONResponse({
                "authorization_request": authz,
                "deeplink": deeplink,
                "state": req.state,
                "nonce": req.nonce,
            })

        html = render_qr_page(
            title="IW3IP Consent VC を提示",
            subtitle=f"dataset_id={dataset_id} / purpose={purpose}",
            deeplink=deeplink,
            deeplink_label="ウォレットで開く",
            payload_json=json.dumps(authz, indent=2, ensure_ascii=False),
        )
        return HTMLResponse(html)

    @router.get("/verifier/request_object")
    def verifier_request_object(request: Request, state: str = Query(...)):
        from fastapi.responses import Response as _Response
        from publisher.app.ssi.sdjwt import _b64u, _es256_sign, _json_bytes
        from publisher.app.ssi.did_jwk import did_jwk_from_public_jwk
        req = deps.state.find_verification_request(state)
        if not req:
            raise HTTPException(status_code=404, detail="verification_request_not_found")
        pd = deps.definitions.get(req.presentation_definition_id)
        kid = did_jwk_from_public_jwk(deps.keys.public_jwk) + "#0"
        header = {"alg": "ES256", "typ": "oauth-authz-req+jwt", "kid": kid}
        dcql = {
            "credentials": [
                {
                    "id": "consent_vc",
                    "format": "dc+sd-jwt",
                    "meta": {"vct_values": ["https://iw3ip.example/credentials/ConsentVC/v1"]},
                    "claims": [
                        {"path": ["dataset_id"], "values": [req.dataset_id]},
                        {"path": ["allowed_purposes"]},
                        {"path": ["subject_id"]},
                    ],
                }
            ]
        }
        public_base = externally_reachable_base_url(request, deps.settings.issuer_base_url)
        payload = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": deps.settings.issuer_base_url,
            "response_uri": f"{public_base}/verifier/response",
            "dcql_query": dcql,
            "nonce": req.nonce,
            "state": req.state,
            "iss": deps.settings.issuer_base_url,
            "aud": "https://self-issued.me/v2",
        }
        h_b64 = _b64u(_json_bytes(header))
        p_b64 = _b64u(_json_bytes(payload))
        signing_input = (h_b64 + "." + p_b64).encode("ascii")
        sig = _es256_sign(deps.keys.private_jwk, signing_input)
        jwt = h_b64 + "." + p_b64 + "." + _b64u(sig)
        return _Response(content=jwt, media_type="application/oauth-authz-req+jwt")

    @router.post("/verifier/response")
    def verifier_response(
        vp_token: str = Form(...),
        state: str = Form(...),
        # Only sent for PEX (presentation_definition) responses. DCQL responses
        # have no equivalent — the wallet keys `vp_token` by credential query id
        # instead. Keep the field optional so both shapes are accepted.
        presentation_submission: str | None = Form(default=None),
    ):
        req = deps.state.find_verification_request(state)
        if not req:
            raise HTTPException(status_code=400, detail="unknown_or_expired_state")

        pd = deps.definitions.get(req.presentation_definition_id)
        if not pd:
            raise HTTPException(status_code=500, detail="presentation_definition_missing")

        sd_jwt = _extract_sd_jwt_compact(vp_token)
        vc_hash_value = _vc_hash(sd_jwt)

        if presentation_submission is not None:
            submission = json.loads(presentation_submission)
            try:
                result = deps.pex_client.verify(
                    presentation_definition=pd,
                    vp_token=sd_jwt,
                    presentation_submission=submission,
                    issuer_public_jwk=deps.keys.public_jwk,
                    expected_nonce=req.nonce,
                    expected_aud=deps.settings.issuer_base_url,
                )
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                logger.warning("PEX sidecar unreachable (%s); using local fallback", exc)
                result = _safe_local_pex_fallback(pd, sd_jwt, deps, req)
        else:
            # DCQL path: PEX sidecar speaks PEX, not DCQL, so go straight to the
            # local fallback that re-checks the disclosed claims directly.
            result = _safe_local_pex_fallback(pd, sd_jwt, deps, req)

        verified = bool(result.get("verified"))
        reason = result.get("reason") or ("ok" if verified else "verification_failed")
        holder_did = result.get("holder_did")

        # Phase 2 purpose check (belt-and-braces against PEX)
        claims = result.get("claims") or {}
        if verified:
            if claims.get("dataset_id") not in (None, req.dataset_id):
                verified = False
                reason = "dataset_mismatch"
            else:
                allowed = claims.get("allowed_purposes")
                if allowed is not None and req.purpose not in allowed:
                    verified = False
                    reason = "purpose_mismatch"

        deps.state.record_verification_result(
            state, {"verified": verified, "reason": reason}
        )
        _write_audit(
            deps.audit_repo,
            action="allow" if verified else "deny",
            reason=reason,
            dataset_id=req.dataset_id,
            purpose=req.purpose,
            holder_did=holder_did,
            vc_hash=vc_hash_value,
            verified="allow" if verified else "deny",
        )
        if verified:
            return {"status": "allowed", "dataset_id": req.dataset_id}
        return {"status": "denied", "dataset_id": req.dataset_id, "reason": reason}

    @router.get("/verifier/status")
    def verifier_status(state: str = Query(...)) -> dict:
        req = deps.state.find_verification_request(state)
        if not req:
            raise HTTPException(status_code=404, detail="unknown_or_expired_state")
        return {
            "state": state,
            "result": req.result,
            "dataset_id": req.dataset_id,
            "purpose": req.purpose,
        }

    return router
