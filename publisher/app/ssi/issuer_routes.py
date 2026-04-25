from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import dataclass

from fastapi import APIRouter, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from publisher.app.ssi.config import SSISettings
from publisher.app.ssi.did_jwk import did_jwk_from_public_jwk, public_jwk_from_did_jwk
from publisher.app.ssi.html import render_qr_page
from publisher.app.ssi.keys import IssuerKeyStore
from publisher.app.ssi.sdjwt import issue_sd_jwt_vc
from publisher.app.ssi.state import SSIStateStore


CREDENTIAL_CONFIG_ID = "ConsentVC"
VCT = "https://iw3ip.example/credentials/ConsentVC/v1"
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


def _issuer_did(keys: IssuerKeyStore) -> str:
    return did_jwk_from_public_jwk(keys.public_jwk)


def _credential_offer(settings: SSISettings, pre_auth_code: str) -> dict:
    return {
        "credential_issuer": settings.issuer_base_url,
        "credential_configuration_ids": [CREDENTIAL_CONFIG_ID],
        "grants": {
            "urn:ietf:params:oauth:grant-type:pre-authorized_code": {
                "pre-authorized_code": pre_auth_code,
            }
        },
    }


def _credential_issuer_metadata(settings: SSISettings, keys: IssuerKeyStore) -> dict:
    issuer_did = _issuer_did(keys)
    return {
        "credential_issuer": settings.issuer_base_url,
        "token_endpoint": f"{settings.issuer_base_url}/issuer/token",
        "credential_endpoint": f"{settings.issuer_base_url}/issuer/credential",
        "authorization_servers": [settings.issuer_base_url],
        "credential_configurations_supported": {
            CREDENTIAL_CONFIG_ID: {
                "format": "dc+sd-jwt",
                "vct": VCT,
                "scope": "ConsentVC",
                "cryptographic_binding_methods_supported": ["jwk", "did:jwk"],
                "credential_signing_alg_values_supported": ["ES256"],
                "proof_types_supported": {
                    "jwt": {"proof_signing_alg_values_supported": ["ES256"]}
                },
                "display": [
                    {"name": "IW3IP Consent Credential", "locale": "en"},
                    {"name": "IW3IP 同意クレデンシャル", "locale": "ja"},
                ],
                "claims": {
                    "dataset_id": {"display": [{"name": "Dataset ID"}]},
                    "purpose": {"display": [{"name": "Purpose"}]},
                    "subject_id": {
                        "display": [{"name": "Subject"}],
                        "mandatory": False,
                    },
                    "iw3ip_issuer": {"display": [{"name": "Issuer"}]},
                },
            }
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
    def issuer_metadata() -> dict:
        return _credential_issuer_metadata(deps.settings, deps.keys)

    @router.get("/.well-known/oauth-authorization-server")
    def as_metadata() -> dict:
        base = deps.settings.issuer_base_url
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
        purpose: str = Query(...),
    ):
        if type != "ConsentVC":
            raise HTTPException(status_code=400, detail="only ConsentVC is supported")

        allowed = DEFAULT_ALLOWED_PURPOSES.get(dataset_id, [purpose])
        offer = deps.state.create_offer(
            credential_config_id=CREDENTIAL_CONFIG_ID,
            dataset_id=dataset_id,
            purpose=purpose,
            allowed_purposes=allowed,
        )
        co = _credential_offer(deps.settings, offer.pre_authorized_code)
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
                }
            )

        html = render_qr_page(
            title="IW3IP Consent VC を発行",
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
        # Accept both the new (`dc+sd-jwt`) and legacy (`vc+sd-jwt`) SD-JWT VC media
        # type names so wallets that pin to either draft revision can still issue.
        if not (cfg_id == CREDENTIAL_CONFIG_ID or fmt in ("dc+sd-jwt", "vc+sd-jwt")):
            raise HTTPException(status_code=400, detail=f"only sd-jwt vc supported (got format={fmt}, cfg_id={cfg_id})")
        if body.get("vct") and body["vct"] != VCT:
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

        holder_jwk = _parse_proof_jwt(
            proof_jwt,
            expected_nonce=token.c_nonce,
            expected_aud=deps.settings.issuer_base_url,
        )

        now = int(time.time())
        exp = now + deps.settings.credential_ttl_days * 86400
        issuer_did = _issuer_did(deps.keys)
        holder_did = did_jwk_from_public_jwk(holder_jwk)

        vc = issue_sd_jwt_vc(
            issuer_private_jwk=deps.keys.private_jwk,
            issuer_did=issuer_did,
            vct=VCT,
            plain_claims={
                "dataset_id": offer.dataset_id,
                "allowed_purposes": offer.allowed_purposes,
                "iw3ip_issuer": deps.settings.issuer_id,
            },
            sd_claims={
                "subject_id": holder_did,
            },
            holder_cnf_jwk=holder_jwk,
            iat=now,
            exp=exp,
        )
        return {"credential": vc.compact, "format": "dc+sd-jwt"}

    return router
