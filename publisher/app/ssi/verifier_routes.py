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


# Stage T (PWA viewer): map verifier `reason` codes to human-readable
# messages so /buyer/start, /viewer and the wallet can surface what
# actually went wrong. Keep the JA strings short enough to render on a
# phone in one or two lines; English mirrors the same idea.
_DENY_HUMAN_MESSAGES: dict[str, dict[str, str]] = {
    "dataset_mismatch": {
        "ja": "提示された VC のデータセットが、要求されたデータセットと一致しません。",
        "en": "The presented VC is bound to a different dataset.",
    },
    "action_not_allowed": {
        "ja": "提示された VC では、このデータの読み取り権限がありません。",
        "en": "The presented VC does not include the required action (read).",
    },
    "purpose_mismatch": {
        "ja": "提示された VC の許可目的に、今回の用途が含まれていません。",
        "en": "The presented VC's allowed_purposes does not cover this purpose.",
    },
    "missing_seller_id": {
        "ja": "SellerVC に seller_id が含まれていません。",
        "en": "SellerVC is missing seller_id.",
    },
    "missing_licensed_datasets": {
        "ja": "SellerVC に出品許可データセットが含まれていません。",
        "en": "SellerVC is missing licensed_datasets.",
    },
    "missing_entityType": {
        "ja": "DataUserVC に entityType が含まれていません。",
        "en": "DataUserVC is missing entityType.",
    },
    "missing_purpose": {
        "ja": "DataUserVC に purpose が含まれていません。",
        "en": "DataUserVC is missing purpose.",
    },
    "missing_dataHandlingPolicy": {
        "ja": "DataUserVC に dataHandlingPolicy が含まれていません。",
        "en": "DataUserVC is missing dataHandlingPolicy.",
    },
    "verification_failed": {
        "ja": "VC の署名検証に失敗しました。",
        "en": "VC verification failed.",
    },
}


def _humanize_reason(reason: str) -> dict[str, str]:
    """Turn a verifier-internal reason code into a JA/EN message pair.
    Falls back to the raw code when we don't have a curated string yet
    -- callers can still display it; the codes are user-readable enough
    to be useful as a fallback."""
    msg = _DENY_HUMAN_MESSAGES.get(reason)
    if msg:
        return {"reason": reason, "human_message_ja": msg["ja"], "human_message_en": msg["en"]}
    return {
        "reason": reason,
        "human_message_ja": f"提示が拒否されました ({reason})。",
        "human_message_en": f"Presentation denied ({reason}).",
    }


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
    vc_kind: str = "ConsentVC",
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
    # SellerVC / DataUserVC aren't dataset-scoped; the dataset check
    # happens at /marketplace/register time (SellerVC) or never
    # (DataUserVC, which only feeds trust evaluation).
    if vc_kind not in ("SellerVC", "DataUserVC"):
        if claims.get("dataset_id") != dataset_id:
            return {"verified": False, "reason": "dataset_mismatch", "claims": claims, "holder_did": None}
    if vc_kind in ("ViewerVC", "PurchaseViewerVC"):
        actions = claims.get("allowed_actions", [])
        if "read" not in actions:
            return {"verified": False, "reason": "action_not_allowed", "claims": claims, "holder_did": None}
    elif vc_kind == "ServiceVC":
        actions = claims.get("allowed_actions", [])
        if "write_continuous" not in actions:
            return {"verified": False, "reason": "action_not_allowed", "claims": claims, "holder_did": None}
    elif vc_kind == "SellerVC":
        if not claims.get("seller_id"):
            return {"verified": False, "reason": "missing_seller_id", "claims": claims, "holder_did": None}
        if not claims.get("licensed_datasets"):
            return {"verified": False, "reason": "missing_licensed_datasets", "claims": claims, "holder_did": None}
    elif vc_kind == "DataUserVC":
        # All five trust attributes must be present so trust_score can be
        # computed deterministically. legalCompliance / misuseRecord are
        # booleans; entityType / purpose / dataHandlingPolicy are strings.
        for k in ("entityType", "purpose", "dataHandlingPolicy"):
            if not claims.get(k):
                return {"verified": False, "reason": f"missing_{k}", "claims": claims, "holder_did": None}
        if "legalCompliance" not in claims:
            return {"verified": False, "reason": "missing_legalCompliance", "claims": claims, "holder_did": None}
        if "misuseRecord" not in claims:
            return {"verified": False, "reason": "missing_misuseRecord", "claims": claims, "holder_did": None}
    else:
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
            pd, sd_jwt, deps.keys.public_jwk, req.dataset_id, req.purpose,
            vc_kind=getattr(req, "vc_kind", "ConsentVC"),
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
        # SellerVC isn't dataset-scoped; the registration step checks
        # licensed_datasets later. Accept "*" as a sentinel here.
        dataset_id: str = Query("*"),
        purpose: str = Query("read"),
        vc_kind: str = Query("ConsentVC"),
    ):
        if vc_kind not in ("ConsentVC", "ViewerVC", "ServiceVC", "PurchaseViewerVC", "SellerVC", "DataUserVC"):
            raise HTTPException(status_code=400, detail=f"unknown vc_kind: {vc_kind}")
        if vc_kind not in ("SellerVC", "DataUserVC") and dataset_id == "*":
            raise HTTPException(status_code=400, detail="dataset_id required for this vc_kind")
        match = deps.definitions.find_for_dataset(dataset_id, vc_kind=vc_kind)
        if not match:
            raise HTTPException(status_code=404, detail="no_presentation_definition_for_dataset")
        pd_id, pd = match
        req = deps.state.create_verification_request(pd_id, dataset_id, purpose, vc_kind=vc_kind)

        public_base = externally_reachable_base_url(request, deps.settings.issuer_base_url)
        # Stage T (PWA viewer + cross-device fix): client_id MUST match a
        # URL the wallet can actually reach. The Docker-internal
        # `issuer_base_url` (e.g. http://publisher:8080) trips up
        # Sphereon mobile-wallet during cross-device flow because the
        # wallet attempts to fetch client_metadata from the URL and
        # times out -- the user then sees a generic "Network request
        # failed". Use the externally-reachable base everywhere.
        authz = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": public_base,
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

        title = {
            "ViewerVC": "IW3IP Viewer VC を提示",
            "ServiceVC": "IW3IP Service VC を提示",
            "PurchaseViewerVC": "IW3IP Purchase Viewer VC を提示",
            "SellerVC": "IW3IP Seller VC を提示",
            "DataUserVC": "IW3IP Data User VC を提示",
        }.get(vc_kind, "IW3IP Consent VC を提示")
        html = render_qr_page(
            title=title,
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
        if req.vc_kind == "ViewerVC":
            dcql = {
                "credentials": [
                    {
                        "id": "viewer_vc",
                        "format": "dc+sd-jwt",
                        "meta": {"vct_values": ["https://iw3ip.example/credentials/ViewerVC/v1"]},
                        "claims": [
                            {"path": ["dataset_id"], "values": [req.dataset_id]},
                            {"path": ["allowed_actions"]},
                            {"path": ["subject_id"]},
                        ],
                    }
                ]
            }
        elif req.vc_kind == "ServiceVC":
            dcql = {
                "credentials": [
                    {
                        "id": "service_vc",
                        "format": "dc+sd-jwt",
                        "meta": {"vct_values": ["https://iw3ip.example/credentials/ServiceVC/v1"]},
                        "claims": [
                            {"path": ["dataset_id"], "values": [req.dataset_id]},
                            {"path": ["allowed_actions"]},
                            {"path": ["subject_id"]},
                        ],
                    }
                ]
            }
        elif req.vc_kind == "SellerVC":
            dcql = {
                "credentials": [
                    {
                        "id": "seller_vc",
                        "format": "dc+sd-jwt",
                        "meta": {"vct_values": ["https://iw3ip.example/credentials/SellerVC/v1"]},
                        "claims": [
                            {"path": ["seller_id"]},
                            {"path": ["licensed_datasets"]},
                            {"path": ["subject_id"]},
                        ],
                    }
                ]
            }
        elif req.vc_kind == "DataUserVC":
            dcql = {
                "credentials": [
                    {
                        "id": "data_user_vc",
                        "format": "dc+sd-jwt",
                        "meta": {"vct_values": ["https://iw3ip.example/credentials/DataUserVC/v1"]},
                        "claims": [
                            {"path": ["entityType"]},
                            {"path": ["purpose"]},
                            {"path": ["legalCompliance"]},
                            {"path": ["dataHandlingPolicy"]},
                            {"path": ["misuseRecord"]},
                            {"path": ["subject_id"]},
                        ],
                    }
                ]
            }
        elif req.vc_kind == "PurchaseViewerVC":
            dcql = {
                "credentials": [
                    {
                        "id": "purchase_viewer_vc",
                        "format": "dc+sd-jwt",
                        "meta": {"vct_values": ["https://iw3ip.example/credentials/PurchaseViewerVC/v1"]},
                        "claims": [
                            {"path": ["dataset_id"], "values": [req.dataset_id]},
                            {"path": ["allowed_actions"]},
                            {"path": ["merchandise_address"]},
                            {"path": ["buyer_eth_addr"]},
                            {"path": ["tx_hash"]},
                            {"path": ["subject_id"]},
                        ],
                    }
                ]
            }
        else:
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
        # See note above /verifier/request — client_id + iss must match
        # the URL the wallet can reach, not the Docker-internal one.
        payload = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": public_base,
            "response_uri": f"{public_base}/verifier/response",
            "dcql_query": dcql,
            "nonce": req.nonce,
            "state": req.state,
            "iss": public_base,
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
        request: Request,
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

        # Phase 2/3 belt-and-braces purpose/action check after PEX
        claims = result.get("claims") or {}
        if verified:
            # SellerVC / DataUserVC aren't dataset-bound; skip dataset_id check
            if (
                req.vc_kind not in ("SellerVC", "DataUserVC")
                and claims.get("dataset_id") not in (None, req.dataset_id)
            ):
                verified = False
                reason = "dataset_mismatch"
            elif req.vc_kind in ("ViewerVC", "PurchaseViewerVC"):
                actions = claims.get("allowed_actions")
                if actions is not None and "read" not in actions:
                    verified = False
                    reason = "action_not_allowed"
            elif req.vc_kind == "ServiceVC":
                actions = claims.get("allowed_actions")
                if actions is not None and "write_continuous" not in actions:
                    verified = False
                    reason = "action_not_allowed"
            elif req.vc_kind == "SellerVC":
                if not claims.get("seller_id"):
                    verified = False
                    reason = "missing_seller_id"
                elif not claims.get("licensed_datasets"):
                    verified = False
                    reason = "missing_licensed_datasets"
            elif req.vc_kind == "DataUserVC":
                # Only check that the 5 attributes are present here.
                # Trust score is computed at the marketplace claim step.
                for k in ("entityType", "purpose", "dataHandlingPolicy"):
                    if not claims.get(k):
                        verified = False
                        reason = f"missing_{k}"
                        break
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
            if req.vc_kind in ("ViewerVC", "PurchaseViewerVC"):
                # Stage T (case alpha): pull allowed_views from the VC's
                # claims when present (PurchaseViewerVC) and propagate it
                # to the ViewerToken; this gates the response projection
                # at /platform/data. Defaults to ["event"] for VCs
                # without the claim (back-compat).
                allowed_views_claim = claims.get("allowed_views")
                token_views = (
                    list(allowed_views_claim)
                    if isinstance(allowed_views_claim, list) and allowed_views_claim
                    else ["event"]
                )
                vt = deps.state.create_viewer_token(
                    dataset_id=req.dataset_id,
                    holder_did=holder_did,
                    allowed_views=token_views,
                )
                logger.info(
                    "viewer_token_issued vc_kind=%s jti=%s token=%s dataset=%s ttl=%ss views=%s",
                    req.vc_kind, vt.jti, vt.token, vt.dataset_id,
                    int(vt.expires_at - vt.issued_at),
                    "+".join(vt.allowed_views),
                )
                resp: dict = {
                    "status": "allowed",
                    "dataset_id": req.dataset_id,
                    "vc_kind": req.vc_kind,
                    "viewer_token": vt.token,
                    "viewer_token_jti": vt.jti,
                    "expires_in": int(vt.expires_at - vt.issued_at),
                    "allowed_views": vt.allowed_views,
                }
                # Surface marketplace context in the response so the
                # iot-market-ui flow (M5) can correlate without re-decoding
                # the VC.
                if req.vc_kind == "PurchaseViewerVC":
                    for k in ("merchandise_address", "buyer_eth_addr", "tx_hash"):
                        if claims.get(k) is not None:
                            resp[k] = claims[k]

                # Stage T (PWA viewer):
                # 1. stash viewer_token onto VerificationRequest.result so
                #    /verifier/status (long-poll) can return it for the
                #    PC cross-device flow.
                # 2. add an OID4VP `redirect_uri` so OS-level deeplink
                #    handlers (Sphereon mobile-wallet) bounce the user
                #    straight into the publisher's /viewer page after a
                #    successful same-device presentation.
                deps.state.record_verification_result(
                    state,
                    {
                        "verified": True,
                        "reason": reason,
                        "viewer_token": vt.token,
                        "viewer_token_jti": vt.jti,
                        "expires_in": int(vt.expires_at - vt.issued_at),
                        "allowed_views": list(vt.allowed_views),
                        "dataset_id": req.dataset_id,
                        "vc_kind": req.vc_kind,
                    },
                )
                public_base = externally_reachable_base_url(
                    request, deps.settings.issuer_base_url
                )
                resp["redirect_uri"] = (
                    f"{public_base.rstrip('/')}/viewer"
                    f"?vt={vt.token}&ds={urllib.parse.quote(req.dataset_id)}"
                )
                return resp
            if req.vc_kind == "SellerVC":
                seller_st = deps.state.create_seller_token(
                    seller_did=holder_did,
                    licensed_datasets=list(claims.get("licensed_datasets") or []),
                )
                logger.info(
                    "seller_token_issued jti=%s token=%s seller_id=%s licensed=%s ttl=%ss",
                    seller_st.jti,
                    seller_st.token,
                    claims.get("seller_id"),
                    seller_st.licensed_datasets,
                    int(seller_st.expires_at - seller_st.issued_at),
                )
                resp = {
                    "status": "allowed",
                    "vc_kind": "SellerVC",
                    "seller_token": seller_st.token,
                    "seller_token_jti": seller_st.jti,
                    "seller_id": claims.get("seller_id"),
                    "licensed_datasets": seller_st.licensed_datasets,
                    "expires_in": int(seller_st.expires_at - seller_st.issued_at),
                }
                # Stage T (PWA provider, c1):
                # mirror what PurchaseViewerVC does -- stash the seller_token
                # onto VerificationRequest.result so /verifier/status
                # (long-poll) can echo it for the cross-device flow, and
                # add an OID4VP redirect_uri pointing back at /provider/start
                # with the same `state` so same-device flow can resume the
                # poll after the wallet bounces back.
                deps.state.record_verification_result(
                    state,
                    {
                        "verified": True,
                        "reason": reason,
                        "seller_token": seller_st.token,
                        "seller_token_jti": seller_st.jti,
                        "seller_id": claims.get("seller_id"),
                        "licensed_datasets": list(seller_st.licensed_datasets),
                        "expires_in": int(seller_st.expires_at - seller_st.issued_at),
                        "vc_kind": "SellerVC",
                    },
                )
                public_base = externally_reachable_base_url(
                    request, deps.settings.issuer_base_url
                )
                resp["redirect_uri"] = (
                    f"{public_base.rstrip('/')}/provider/start"
                    f"?state={urllib.parse.quote(state)}"
                )
                return resp
            if req.vc_kind == "DataUserVC":
                # No token minted: DataUserVC presentation is informational
                # (the publisher just confirms it can compute the trust score
                # and reports the result). Subsequent ViewerToken / Purchase
                # flows pick up the trust evaluation via /marketplace/claim.
                from publisher.app.ssi.trust_score import evaluate_from_claims
                trust = evaluate_from_claims(claims)
                logger.info(
                    "data_user_vc_verified holder=%s entity=%s purpose=%s trust=%s level=%s",
                    holder_did,
                    claims.get("entityType"),
                    claims.get("purpose"),
                    trust.trust_score,
                    trust.access_level,
                )
                return {
                    "status": "allowed",
                    "vc_kind": "DataUserVC",
                    "trust_score": trust.trust_score,
                    "access_level": trust.access_level,
                    "allowed_views": trust.allowed_views,
                    "holder_did": holder_did,
                }
            if req.vc_kind == "ServiceVC":
                st = deps.state.create_service_token(
                    dataset_id=req.dataset_id,
                    holder_did=holder_did,
                )
                logger.info(
                    "service_token_issued jti=%s token=%s dataset=%s ttl=%ss",
                    st.jti, st.token, st.dataset_id,
                    int(st.expires_at - st.issued_at),
                )
                return {
                    "status": "allowed",
                    "dataset_id": req.dataset_id,
                    "vc_kind": "ServiceVC",
                    "service_token": st.token,
                    "service_token_jti": st.jti,
                    "expires_in": int(st.expires_at - st.issued_at),
                }
            pt = deps.state.create_policy_token(
                dataset_id=req.dataset_id,
                purpose=req.purpose,
                holder_did=holder_did,
            )
            logger.info(
                "policy_token_issued jti=%s token=%s dataset=%s ttl=%ss",
                pt.jti, pt.token, pt.dataset_id,
                int(pt.expires_at - pt.issued_at),
            )
            return {
                "status": "allowed",
                "dataset_id": req.dataset_id,
                "vc_kind": "ConsentVC",
                "policy_token": pt.token,
                "policy_token_jti": pt.jti,
                "expires_in": int(pt.expires_at - pt.issued_at),
            }
        # Stage T (PWA viewer): record the deny on the verification
        # request so /verifier/status can echo a human-readable message
        # back to the long-polling /buyer/start page.
        deny_human = _humanize_reason(reason)
        deps.state.record_verification_result(
            state,
            {
                "verified": False,
                "reason": reason,
                "human_message_ja": deny_human["human_message_ja"],
                "human_message_en": deny_human["human_message_en"],
                "dataset_id": req.dataset_id,
                "vc_kind": req.vc_kind,
            },
        )
        return {
            "status": "denied",
            "dataset_id": req.dataset_id,
            "reason": reason,
            "human_message_ja": deny_human["human_message_ja"],
            "human_message_en": deny_human["human_message_en"],
        }

    @router.get("/verifier/status")
    def verifier_status(request: Request, state: str = Query(...)) -> dict:
        """Verifier-state poll endpoint.

        The PWA Buyer-Start page polls this every ~2 s while the user is
        scanning a QR on a separate device. Once /verifier/response has
        stashed a viewer_token onto the request's `result`, this echoes
        it back along with a ready-to-redirect ``viewer_url`` so the
        polling page can navigate to the data viewer.
        """
        req = deps.state.find_verification_request(state)
        if not req:
            raise HTTPException(status_code=404, detail="unknown_or_expired_state")

        result = req.result or {}
        out: dict = {
            "state": state,
            "result": result,
            "dataset_id": req.dataset_id,
            "purpose": req.purpose,
            "vc_kind": req.vc_kind,
        }
        # When the verification has succeeded and minted a ViewerToken,
        # surface a fully-formed `viewer_url` the polling page can redirect to.
        if isinstance(result, dict) and result.get("verified") and result.get("viewer_token"):
            public_base = externally_reachable_base_url(
                request, deps.settings.issuer_base_url
            )
            out["viewer_token"] = result["viewer_token"]
            out["allowed_views"] = result.get("allowed_views") or []
            out["expires_in"] = result.get("expires_in")
            out["viewer_url"] = (
                f"{public_base.rstrip('/')}/viewer"
                f"?vt={result['viewer_token']}"
                f"&ds={urllib.parse.quote(req.dataset_id)}"
            )
        # Stage T (PWA provider, c1): same idea for SellerVC. The polling
        # /provider/start page only needs the seller_token + licensed_datasets
        # to render its inline success panel; it does not navigate away.
        if isinstance(result, dict) and result.get("verified") and result.get("seller_token"):
            out["seller_token"] = result["seller_token"]
            out["licensed_datasets"] = result.get("licensed_datasets") or []
            out["expires_in"] = result.get("expires_in")
            out["seller_id"] = result.get("seller_id")
        return out

    return router
