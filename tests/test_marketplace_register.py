"""POST /marketplace/register + seller_did in /platform/data (Stage 7 / C3).

Builds on the SellerVC + SellerToken machinery from C2 and binds a
seller_did to a merchandise so buyers can see who sold the data.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from publisher.app.ssi.did_jwk import did_jwk_from_public_jwk
from publisher.app.ssi.keys import private_key_to_jwk, public_jwk_from_private_jwk
from publisher.app.ssi.sdjwt import _b64u, _es256_sign, _json_bytes


@pytest.fixture
def client(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SSI_ISSUER_KEY_PATH", str(tmp_path / "issuer_key.jwk.json"))
    monkeypatch.setenv("SSI_PRESENTATION_DEFS_DIR", str(repo_root / "examples" / "ssi_wallet"))
    monkeypatch.setenv("SSI_ISSUER_BASE_URL", "http://testserver")
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("CONSENT_STORE_PATH", str(tmp_path / "consents.json"))
    monkeypatch.setenv("PLATFORM_API_URL", "http://testserver/platform/ingest")
    monkeypatch.setenv("MQTT_BROKER_HOST", "localhost")
    monkeypatch.setenv("MQTT_TOPICS", "")
    monkeypatch.setenv("SSI_PEX_SIDECAR_URL", "http://127.0.0.1:1")
    # Default: no on-chain owner verification (skip the chain RPC).
    # Individual tests that need to exercise that path patch
    # _chain_client.merchandise_owner directly.

    import importlib
    import publisher.app.main as pm
    importlib.reload(pm)

    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        from fastapi.testclient import TestClient
        with TestClient(pm.app) as tc:
            yield tc, pm


_MERCHANDISE = "0x1111111111111111111111111111111111111111"
_SELLER_ETH = "0x2222222222222222222222222222222222222222"
_TX_HASH = "0x" + "a" * 64
_DATASET = "home/env/temperature"


def _holder():
    pk = ec.generate_private_key(ec.SECP256R1())
    jwk = private_key_to_jwk(pk)
    pub = public_jwk_from_private_jwk(jwk)
    return jwk, pub, did_jwk_from_public_jwk(pub)


def _proof(priv, pub, nonce, aud):
    h = _b64u(_json_bytes({"alg": "ES256", "typ": "openid4vci-proof+jwt", "jwk": pub}))
    p = _b64u(_json_bytes({"nonce": nonce, "aud": aud, "iat": int(time.time())}))
    sig = _es256_sign(priv, (h + "." + p).encode("ascii"))
    return h + "." + p + "." + _b64u(sig)


def _issue_seller_token(tc, *, licensed=_DATASET) -> tuple[str, str]:
    """Returns (seller_token, seller_did)."""
    priv, pub, holder_did = _holder()
    offer = tc.get(
        "/issuer/offer",
        params={
            "type": "SellerVC",
            "seller_id": "ertl-test",
            "licensed_datasets": licensed,
        },
        headers={"accept": "application/json"},
    ).json()
    token = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": offer["pre_authorized_code"],
        },
    ).json()
    proof = _proof(priv, pub, token["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/SellerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    req = tc.get(
        "/verifier/request",
        params={"vc_kind": "SellerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-seller-vc",
        "definition_id": "seller-vc",
        "descriptor_map": [{"id": "seller_vc", "format": "vc+sd-jwt", "path": "$"}],
    }
    body = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    return body["seller_token"], holder_did


_BASE_BODY = {
    "merchandise_address": _MERCHANDISE,
    "seller_eth_addr": _SELLER_ETH,
    "tx_hash": _TX_HASH,
    "dataset_id": _DATASET,
}


def test_register_succeeds_with_licensed_dataset(client):
    tc, _ = client
    token, seller_did = _issue_seller_token(tc)
    r = tc.post(
        "/marketplace/register",
        headers={"Authorization": f"Bearer {token}"},
        json=_BASE_BODY,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["registered"] is True
    assert body["seller_did"] == seller_did
    assert body["owner_verify"] == "skipped"  # rpc not configured in tests


def test_register_audit_records_seller_register(client):
    tc, _ = client
    token, seller_did = _issue_seller_token(tc)
    tc.post(
        "/marketplace/register",
        headers={"Authorization": f"Bearer {token}"},
        json=_BASE_BODY,
    )
    logs = tc.get("/audit/logs?limit=5").json()
    matches = [
        log for log in logs
        if log["raw_topic"] == "marketplace/seller_registered"
        and log["reason"].startswith("seller_register:")
    ]
    assert len(matches) == 1
    log = matches[0]
    assert log["holder_did"] == seller_did
    assert _TX_HASH in log["reason"]
    assert _MERCHANDISE in log["reason"]
    assert "owner_verify=skipped" in log["reason"]


def test_register_rejects_unlicensed_dataset(client):
    tc, _ = client
    token, _ = _issue_seller_token(tc, licensed="home/env/humidity")
    r = tc.post(
        "/marketplace/register",
        headers={"Authorization": f"Bearer {token}"},
        json=_BASE_BODY,
    )
    assert r.status_code == 403
    assert "dataset_not_licensed" in r.json()["detail"]


def test_register_rejects_unknown_token(client):
    tc, _ = client
    r = tc.post(
        "/marketplace/register",
        headers={"Authorization": "Bearer bogus"},
        json=_BASE_BODY,
    )
    assert r.status_code == 401
    assert "seller_token_unknown" in r.json()["detail"]


def test_register_rejects_missing_field(client):
    tc, _ = client
    token, _ = _issue_seller_token(tc)
    incomplete = {k: v for k, v in _BASE_BODY.items() if k != "tx_hash"}
    r = tc.post(
        "/marketplace/register",
        headers={"Authorization": f"Bearer {token}"},
        json=incomplete,
    )
    assert r.status_code == 400
    assert "missing_field:tx_hash" in r.json()["detail"]


def test_register_rejects_missing_authorization(client):
    tc, _ = client
    r = tc.post("/marketplace/register", json=_BASE_BODY)
    assert r.status_code == 401


def test_owner_verify_when_rpc_configured_and_matches(client, monkeypatch):
    tc, pm = client
    # Re-enable the chain client by overriding settings; force the
    # eth_call to return our seller eth address.
    pm._chain_client._settings.rpc_url = "http://hardhat:8545"  # noqa: SLF001
    monkeypatch.setattr(
        pm._chain_client,
        "merchandise_owner",
        lambda addr: _SELLER_ETH,
    )

    token, _ = _issue_seller_token(tc)
    r = tc.post(
        "/marketplace/register",
        headers={"Authorization": f"Bearer {token}"},
        json=_BASE_BODY,
    )
    assert r.status_code == 200
    assert r.json()["owner_verify"] == "verified"


def test_owner_verify_rejects_mismatch(client, monkeypatch):
    tc, pm = client
    pm._chain_client._settings.rpc_url = "http://hardhat:8545"  # noqa: SLF001
    monkeypatch.setattr(
        pm._chain_client,
        "merchandise_owner",
        lambda addr: "0x" + "ff" * 20,
    )

    token, _ = _issue_seller_token(tc)
    r = tc.post(
        "/marketplace/register",
        headers={"Authorization": f"Bearer {token}"},
        json=_BASE_BODY,
    )
    assert r.status_code == 403
    assert "owner_mismatch" in r.json()["detail"]


def test_platform_data_includes_seller_did_for_registered_merchandise(client):
    """After /marketplace/register binds a Merchandise to a seller_did,
    the buyer's GET /platform/data?merchandise=... shows that seller_did
    in the response."""
    tc, _ = client

    # 1) Seller registers
    seller_token, seller_did = _issue_seller_token(tc)
    tc.post(
        "/marketplace/register",
        headers={"Authorization": f"Bearer {seller_token}"},
        json=_BASE_BODY,
    )

    # 2) Bridge claim flow to get a ViewerToken bound to the merchandise
    claim = tc.post(
        "/marketplace/claim",
        json={
            "merchandise_address": _MERCHANDISE,
            "buyer_eth_addr": "0x" + "33" * 20,
            "tx_hash": "0x" + "44" * 32,
            "dataset_id": _DATASET,
            "purchase_amount_wei": "0",
        },
    ).json()
    pre_auth = json.loads(
        __import__("urllib.parse").parse.unquote(
            claim["deeplink"].split("=", 1)[1]
        )
    )["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]
    priv, pub, _ = _holder()
    tok = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    ).json()
    proof = _proof(priv, pub, tok["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {tok['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    req = tc.get(
        "/verifier/request",
        params={"dataset_id": _DATASET, "vc_kind": "PurchaseViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-purchase-viewer-temperature",
        "definition_id": "purchase-viewer-temperature",
        "descriptor_map": [{"id": "purchase_viewer_vc_temperature", "format": "vc+sd-jwt", "path": "$"}],
    }
    presented = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    viewer_token = presented["viewer_token"]

    r = tc.get(
        "/platform/data",
        params={"merchandise": _MERCHANDISE},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["seller_did"] == seller_did


def test_platform_data_seller_did_unknown_when_not_registered(client):
    """If a Merchandise is fetched but never went through /marketplace/register,
    seller_did should report 'unknown' rather than crash."""
    tc, _ = client

    claim = tc.post(
        "/marketplace/claim",
        json={
            "merchandise_address": "0x" + "55" * 20,
            "buyer_eth_addr": "0x" + "33" * 20,
            "tx_hash": "0x" + "66" * 32,
            "dataset_id": _DATASET,
            "purchase_amount_wei": "0",
        },
    ).json()
    pre_auth = json.loads(
        __import__("urllib.parse").parse.unquote(
            claim["deeplink"].split("=", 1)[1]
        )
    )["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]
    priv, pub, _ = _holder()
    tok = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    ).json()
    proof = _proof(priv, pub, tok["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {tok['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    req = tc.get(
        "/verifier/request",
        params={"dataset_id": _DATASET, "vc_kind": "PurchaseViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-purchase-viewer-temperature",
        "definition_id": "purchase-viewer-temperature",
        "descriptor_map": [{"id": "purchase_viewer_vc_temperature", "format": "vc+sd-jwt", "path": "$"}],
    }
    presented = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    viewer_token = presented["viewer_token"]

    r = tc.get(
        "/platform/data",
        params={"merchandise": "0x" + "55" * 20},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["seller_did"] == "unknown"
