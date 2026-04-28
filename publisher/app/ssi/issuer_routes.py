from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from audit.models import AuditLogRecord
from audit.repository import SQLiteAuditRepository
from publisher.app.ssi.config import SSISettings
from publisher.app.ssi.did_jwk import did_jwk_from_public_jwk, public_jwk_from_did_jwk
from publisher.app.ssi.html import render_qr_page
from publisher.app.ssi.keys import IssuerKeyStore
from publisher.app.ssi.sdjwt import issue_sd_jwt_vc
from publisher.app.ssi.state import SSIStateStore
from publisher.app.ssi.url_utils import externally_reachable_base_url


CONSENT_VC_CONFIG_ID = "ConsentVC"
CONSENT_VCT = "https://iw3ip.example/credentials/ConsentVC/v1"
VIEWER_VC_CONFIG_ID = "ViewerVC"
VIEWER_VCT = "https://iw3ip.example/credentials/ViewerVC/v1"
SERVICE_VC_CONFIG_ID = "ServiceVC"
SERVICE_VCT = "https://iw3ip.example/credentials/ServiceVC/v1"
PURCHASE_VIEWER_VC_CONFIG_ID = "PurchaseViewerVC"
PURCHASE_VIEWER_VCT = "https://iw3ip.example/credentials/PurchaseViewerVC/v1"

# Backwards-compatible aliases for code/tests that imported the originals.
CREDENTIAL_CONFIG_ID = CONSENT_VC_CONFIG_ID
VCT = CONSENT_VCT

# ConsentVC         = single-use write authz       (Stage 1)
# ViewerVC          = multi-use read authz         (Stage 3)
# ServiceVC         = multi-use write authz, M2M   (Stage 4 prep)
# PurchaseViewerVC  = read authz tied to a Merchandise.Purchase tx
#                     (v2 / Stage 5, marketplace bridge)
VC_KIND_TO_VCT = {
    "ConsentVC": CONSENT_VCT,
    "ViewerVC": VIEWER_VCT,
    "ServiceVC": SERVICE_VCT,
    "PurchaseViewerVC": PURCHASE_VIEWER_VCT,
}
VC_KIND_TO_CONFIG_ID = {
    "ConsentVC": CONSENT_VC_CONFIG_ID,
    "ViewerVC": VIEWER_VC_CONFIG_ID,
    "ServiceVC": SERVICE_VC_CONFIG_ID,
    "PurchaseViewerVC": PURCHASE_VIEWER_VC_CONFIG_ID,
}

DEEPLINK_SCHEME = "openid-credential-offer://"

DEFAULT_ALLOWED_PURPOSES = {
    "home/env/temperature": ["research", "planning"],
    "home/env/person_detected": ["safety", "research"],
    "home/env/flood_risk_high": ["safety", "emergency_planning"],
    "home/env/possible_littering": ["community_awareness", "planning"],
    "home/energy/power": ["research", "planning"],
}


@dataclass
class IssuerDeps:
    settings: SSISettings
    keys: IssuerKeyStore
    state: SSIStateStore
    audit_repo: SQLiteAuditRepository | None = None  # M3: required for PurchaseViewerVC


def _issuer_did(keys: IssuerKeyStore) -> str:
    return did_jwk_from_public_jwk(keys.public_jwk)


def _credential_offer(base_url: str, pre_auth_code: str, config_id: str) -> dict:
    return {
        "credential_issuer": base_url,
        "credential_configuration_ids": [config_id],
        "grants": {
            "urn:ietf:params:oauth:grant-type:pre-authorized_code": {
                "pre-authorized_code": pre_auth_code,
            }
        },
    }


def _credential_issuer_metadata(base_url: str, keys: IssuerKeyStore) -> dict:
    issuer_did = _issuer_did(keys)
    common_alg = {
        "format": "dc+sd-jwt",
        "cryptographic_binding_methods_supported": ["jwk", "did:jwk"],
        "credential_signing_alg_values_supported": ["ES256"],
        "proof_types_supported": {
            "jwt": {"proof_signing_alg_values_supported": ["ES256"]}
        },
    }
    return {
        "credential_issuer": base_url,
        "token_endpoint": f"{base_url}/issuer/token",
        "credential_endpoint": f"{base_url}/issuer/credential",
        "authorization_servers": [base_url],
        "credential_configurations_supported": {
            CONSENT_VC_CONFIG_ID: {
                **common_alg,
                "vct": CONSENT_VCT,
                "scope": "ConsentVC",
                "display": [
                    {"name": "IW3IP Consent Credential", "locale": "en"},
                    {"name": "IW3IP 同意クレデンシャル", "locale": "ja"},
                ],
                "claims": {
                    "dataset_id": {"display": [{"name": "Dataset ID"}]},
                    "purpose": {"display": [{"name": "Purpose"}]},
                    "allowed_purposes": {"display": [{"name": "Allowed purposes"}]},
                    "subject_id": {"display": [{"name": "Subject"}], "mandatory": False},
                    "iw3ip_issuer": {"display": [{"name": "Issuer"}]},
                },
            },
            VIEWER_VC_CONFIG_ID: {
                **common_alg,
                "vct": VIEWER_VCT,
                "scope": "ViewerVC",
                "display": [
                    {"name": "IW3IP Viewer Credential", "locale": "en"},
                    {"name": "IW3IP 閲覧クレデンシャル", "locale": "ja"},
                ],
                "claims": {
                    "dataset_id": {"display": [{"name": "Dataset ID"}]},
                    "allowed_actions": {"display": [{"name": "Allowed actions"}]},
                    "subject_id": {"display": [{"name": "Subject"}], "mandatory": False},
                    "iw3ip_issuer": {"display": [{"name": "Issuer"}]},
                },
            },
            SERVICE_VC_CONFIG_ID: {
                **common_alg,
                "vct": SERVICE_VCT,
                "scope": "ServiceVC",
                "display": [
                    {"name": "IW3IP Service Credential", "locale": "en"},
                    {"name": "IW3IP サービスクレデンシャル", "locale": "ja"},
                ],
                "claims": {
                    "dataset_id": {"display": [{"name": "Dataset ID"}]},
                    "allowed_actions": {"display": [{"name": "Allowed actions"}]},
                    "subject_id": {"display": [{"name": "Subject"}], "mandatory": False},
                    "iw3ip_issuer": {"display": [{"name": "Issuer"}]},
                },
            },
            PURCHASE_VIEWER_VC_CONFIG_ID: {
                **common_alg,
                "vct": PURCHASE_VIEWER_VCT,
                "scope": "PurchaseViewerVC",
                "display": [
                    {"name": "IW3IP Purchase Viewer Credential", "locale": "en"},
                    {"name": "IW3IP 購入閲覧クレデンシャル", "locale": "ja"},
                ],
                "claims": {
                    "dataset_id": {"display": [{"name": "Dataset ID"}]},
                    "allowed_actions": {"display": [{"name": "Allowed actions"}]},
                    "merchandise_address": {"display": [{"name": "Merchandise contract"}]},
                    "buyer_eth_addr": {"display": [{"name": "Buyer ETH address"}]},
                    "tx_hash": {"display": [{"name": "Purchase tx hash"}]},
                    "subject_id": {"display": [{"name": "Subject"}], "mandatory": False},
                    "iw3ip_issuer": {"display": [{"name": "Issuer"}]},
                },
            },
        },
        "issuer": issuer_did,
        "jwks": {"keys": [keys.public_jwk]},
    }


def _parse_proof_jwt(proof_jwt: str, expected_nonce: str, expected_aud: str) -> dict:
    from publisher.app.ssi.sdjwt import _b64u_decode, _es256_verify

    try:
        h_b64, p_b64, s_b64 = proof_jwt.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"malformed proof JWT: {exc}")

    header = json.loads(_b64u_decode(h_b64))
    payload = json.loads(_b64u_decode(p_b64))
    signature = _b64u_decode(s_b64)

    if header.get("typ") != "openid4vci-proof+jwt":
        raise HTTPException(status_code=400, detail="proof typ must be openid4vci-proof+jwt")

    holder_jwk = header.get("jwk")
    holder_kid = header.get("kid")
    if not holder_jwk and holder_kid and holder_kid.startswith("did:jwk:"):
        holder_jwk = public_jwk_from_did_jwk(holder_kid.split("#")[0])
    if not holder_jwk:
        raise HTTPException(status_code=400, detail="proof header missing jwk/kid")

    signing_input = (h_b64 + "." + p_b64).encode("ascii")
    if not _es256_verify(holder_jwk, signing_input, signature):
        raise HTTPException(status_code=400, detail="proof signature invalid")

    if payload.get("nonce") != expected_nonce:
        raise HTTPException(status_code=400, detail="proof nonce mismatch")
    if payload.get("aud") not in (expected_aud, expected_aud.rstrip("/")):
        raise HTTPException(status_code=400, detail="proof aud mismatch")

    return holder_jwk


def build_router(deps: IssuerDeps) -> APIRouter:
    router = APIRouter()

    @router.get("/.well-known/openid-credential-issuer")
    def issuer_metadata(request: Request) -> dict:
        base = externally_reachable_base_url(request, deps.settings.issuer_base_url)
        return _credential_issuer_metadata(base, deps.keys)

    @router.get("/.well-known/oauth-authorization-server")
    def as_metadata(request: Request) -> dict:
        base = externally_reachable_base_url(request, deps.settings.issuer_base_url)
        return {
            "issuer": base,
            "token_endpoint": f"{base}/issuer/token",
            "grant_types_supported": [
                "urn:ietf:params:oauth:grant-type:pre-authorized_code"
            ],
            "token_endpoint_auth_methods_supported": ["none"],
            "response_types_supported": ["token"],
        }

    @router.get("/issuer/offer")
    def issuer_offer(
        request: Request,
        type: str = Query("ConsentVC", alias="type"),
        dataset_id: str = Query(...),
        purpose: str = Query("read"),
    ):
        if type not in VC_KIND_TO_CONFIG_ID:
            raise HTTPException(
                status_code=400,
                detail=f"unknown VC type: {type} (supported: {list(VC_KIND_TO_CONFIG_ID)})",
            )
        config_id = VC_KIND_TO_CONFIG_ID[type]

        if type == "ConsentVC":
            allowed = DEFAULT_ALLOWED_PURPOSES.get(dataset_id, [purpose])
            page_title = "IW3IP Consent VC を発行"
        elif type == "ViewerVC":
            allowed = ["read"]
            page_title = "IW3IP Viewer VC を発行"
        elif type == "ServiceVC":
            allowed = ["write_continuous"]
            page_title = "IW3IP Service VC を発行"
        else:  # PurchaseViewerVC: bridge issues these via /marketplace/claim,
            # not directly via /issuer/offer. We still support the manual path
            # for hands-on debugging.
            allowed = ["read"]
            page_title = "IW3IP Purchase Viewer VC を発行"

        offer = deps.state.create_offer(
            credential_config_id=config_id,
            dataset_id=dataset_id,
            purpose=purpose,
            allowed_purposes=allowed,
            vc_kind=type,
        )
        public_base = externally_reachable_base_url(request, deps.settings.issuer_base_url)
        co = _credential_offer(public_base, offer.pre_authorized_code, config_id)
        deeplink = (
            DEEPLINK_SCHEME
            + "?credential_offer="
            + urllib.parse.quote(json.dumps(co, separators=(",", ":")))
        )

        accept = request.headers.get("accept", "")
        if "application/json" in accept or request.query_params.get("format") == "json":
            return JSONResponse(
                {
                    "credential_offer": co,
                    "deeplink": deeplink,
                    "pre_authorized_code": offer.pre_authorized_code,
                    "dataset_id": dataset_id,
                    "purpose": purpose,
                    "allowed_purposes": allowed,
                    "vc_kind": type,
                }
            )

        html = render_qr_page(
            title=page_title,
            subtitle=f"dataset_id={dataset_id} / purpose={purpose}",
            deeplink=deeplink,
            deeplink_label="ウォレットで開く",
            payload_json=json.dumps(co, indent=2, ensure_ascii=False),
        )
        return HTMLResponse(html)

    @router.post("/issuer/token")
    def issuer_token(
        grant_type: str = Form(...),
        pre_authorized_code: str = Form(..., alias="pre-authorized_code"),
    ):
        if grant_type != "urn:ietf:params:oauth:grant-type:pre-authorized_code":
            raise HTTPException(status_code=400, detail="unsupported_grant_type")
        offer = deps.state.consume_offer(pre_authorized_code)
        if not offer:
            raise HTTPException(status_code=400, detail="invalid_grant")
        token = deps.state.issue_token(offer)
        return {
            "access_token": token.token,
            "token_type": "Bearer",
            "expires_in": deps.settings.offer_ttl_seconds,
            "c_nonce": token.c_nonce,
            "c_nonce_expires_in": deps.settings.offer_ttl_seconds,
        }

    @router.post("/issuer/credential")
    def issuer_credential(
        request: Request,
        body: dict,
        authorization: str | None = Header(default=None),
    ):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token_str = authorization.split(" ", 1)[1]
        token = deps.state.get_token(token_str)
        if not token:
            raise HTTPException(status_code=401, detail="invalid_token")
        offer = deps.state.get_offer_for_token(token)
        if not offer:
            raise HTTPException(status_code=400, detail="no_offer_for_token")

        cfg_id = body.get("credential_configuration_id") or body.get("credential_identifier")
        fmt = body.get("format")
        offer_vct = VC_KIND_TO_VCT[offer.vc_kind]
        offer_cfg_id = VC_KIND_TO_CONFIG_ID[offer.vc_kind]
        # Accept both the new (`dc+sd-jwt`) and legacy (`vc+sd-jwt`) SD-JWT VC media
        # type names so wallets that pin to either draft revision can still issue.
        if not (cfg_id == offer_cfg_id or fmt in ("dc+sd-jwt", "vc+sd-jwt")):
            raise HTTPException(status_code=400, detail=f"only sd-jwt vc supported (got format={fmt}, cfg_id={cfg_id})")
        if body.get("vct") and body["vct"] != offer_vct:
            raise HTTPException(status_code=400, detail=f"unknown vct: {body['vct']}")

        proof = body.get("proof") or {}
        proofs = body.get("proofs") or {}
        proof_jwt = None
        if isinstance(proof, dict) and proof.get("proof_type") == "jwt" and "jwt" in proof:
            proof_jwt = proof["jwt"]
        elif isinstance(proofs, dict) and isinstance(proofs.get("jwt"), list) and proofs["jwt"]:
            proof_jwt = proofs["jwt"][0]
        if not proof_jwt:
            raise HTTPException(status_code=400, detail="proof_type=jwt required")

        # Wallets sign the proof JWT with whatever issuer URL they fetched the
        # offer/metadata under. That's the externally-reachable URL we just
        # echoed back, not the docker-internal `settings.issuer_base_url`.
        public_base = externally_reachable_base_url(request, deps.settings.issuer_base_url)
        holder_jwk = _parse_proof_jwt(
            proof_jwt,
            expected_nonce=token.c_nonce,
            expected_aud=public_base,
        )

        now = int(time.time())
        exp = now + deps.settings.credential_ttl_days * 86400
        issuer_did = _issuer_did(deps.keys)
        holder_did = did_jwk_from_public_jwk(holder_jwk)

        if offer.vc_kind == "PurchaseViewerVC":
            # M3: fold marketplace context into the claims and link the
            # holder DID back to the bridge-recorded claim.
            claim = deps.state.find_marketplace_claim_by_code(
                offer.pre_authorized_code
            )
            plain_claims = {
                "dataset_id": offer.dataset_id,
                "allowed_actions": offer.allowed_purposes,
                "iw3ip_issuer": deps.settings.issuer_id,
            }
            if claim:
                plain_claims.update({
                    "merchandise_address": claim.merchandise_address,
                    "buyer_eth_addr": claim.buyer_eth_addr,
                    "tx_hash": claim.tx_hash,
                    "purchased_at": int(claim.created_at),
                })
                deps.state.attach_holder_to_claim(claim.claim_id, holder_did)
                # Audit the eth_addr <-> did:jwk binding now that we have both.
                if deps.audit_repo is not None:
                    deps.audit_repo.write(
                        AuditLogRecord(
                            ts=datetime.now(timezone.utc).isoformat(),
                            action="allow",
                            subject_did=holder_did,
                            dataset_id=claim.dataset_id,
                            purpose="purchase_link",
                            reason=(
                                f"eth_did_bound:claim={claim.claim_id}"
                                f":eth={claim.buyer_eth_addr}:tx={claim.tx_hash}"
                            ),
                            message_hash="",
                            raw_topic="marketplace/issued",
                            holder_did=holder_did,
                            vc_hash=None,
                            presentation_verified="allow",
                        )
                    )
        elif offer.vc_kind in ("ViewerVC", "ServiceVC"):
            plain_claims = {
                "dataset_id": offer.dataset_id,
                "allowed_actions": offer.allowed_purposes,
                "iw3ip_issuer": deps.settings.issuer_id,
            }
        else:
            plain_claims = {
                "dataset_id": offer.dataset_id,
                "allowed_purposes": offer.allowed_purposes,
                "iw3ip_issuer": deps.settings.issuer_id,
            }

        vc = issue_sd_jwt_vc(
            issuer_private_jwk=deps.keys.private_jwk,
            issuer_did=issuer_did,
            vct=offer_vct,
            plain_claims=plain_claims,
            sd_claims={
                "subject_id": holder_did,
            },
            holder_cnf_jwk=holder_jwk,
            iat=now,
            exp=exp,
        )
        return {"credential": vc.compact, "format": "dc+sd-jwt"}

    return router
