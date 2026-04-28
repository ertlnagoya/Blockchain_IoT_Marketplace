"""End-to-end /marketplace/claim → PurchaseViewerVC → ViewerToken (M3).

Exercises the v2 lane:
  bridge POSTs claim -> publisher mints offer -> wallet completes
  OID4VCI -> publisher records eth_addr <-> did:jwk binding -> wallet
  presents PurchaseViewerVC -> ViewerToken -> /platform/data.
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

    import importlib
    import publisher.app.main as pm
    importlib.reload(pm)

    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        from fastapi.testclient import TestClient
        with TestClient(pm.app) as tc:
            yield tc, pm


_BASE_BODY = {
    "merchandise_address": "0x0000000000000000000000000000000000000abc",
    "buyer_eth_addr": "0xdeadbeef00000000000000000000000000000000",
    "tx_hash": "0xfeedface" + "00" * 28,
    "dataset_id": "home/env/temperature",
    "purchase_amount_wei": "10000000000000000",
}


def _make_holder():
    pk = ec.generate_private_key(ec.SECP256R1())
    jwk = private_key_to_jwk(pk)
    pub = public_jwk_from_private_jwk(jwk)
    return jwk, pub, did_jwk_from_public_jwk(pub)


def _proof_jwt(priv, pub, nonce, aud):
    h = _b64u(_json_bytes({"alg": "ES256", "typ": "openid4vci-proof+jwt", "jwk": pub}))
    p = _b64u(_json_bytes({"nonce": nonce, "aud": aud, "iat": int(time.time())}))
    sig = _es256_sign(priv, (h + "." + p).encode("ascii"))
    return h + "." + p + "." + _b64u(sig)


def _submission(pd_id: str, input_desc_id: str) -> dict:
    return {
        "id": "sub-" + pd_id,
        "definition_id": pd_id,
        "descriptor_map": [{"id": input_desc_id, "format": "vc+sd-jwt", "path": "$"}],
    }


def _claim_to_pre_auth(deeplink: str) -> str:
    import urllib.parse as _u
    qs = deeplink.split("?", 1)[1]
    co = json.loads(_u.unquote(qs.split("=", 1)[1]))
    return co["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]


def _full_purchase_to_credential(tc) -> tuple[str, str, dict]:
    """Returns (sd_jwt_vc, holder_did, claim_response)."""
    claim_resp = tc.post("/marketplace/claim", json=_BASE_BODY).json()
    pre_auth = _claim_to_pre_auth(claim_resp["deeplink"])

    priv, pub, holder_did = _make_holder()
    token = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    ).json()
    proof = _proof_jwt(priv, pub, token["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    return cred["credential"], holder_did, claim_resp


def test_issuer_metadata_lists_purchase_viewer_vc(client):
    tc, _ = client
    cfgs = tc.get("/.well-known/openid-credential-issuer").json()["credential_configurations_supported"]
    assert "PurchaseViewerVC" in cfgs
    assert cfgs["PurchaseViewerVC"]["vct"].endswith("/PurchaseViewerVC/v1")


def test_claim_offer_now_targets_purchase_viewer_vc(client):
    tc, _ = client
    body = tc.post("/marketplace/claim", json=_BASE_BODY).json()
    assert "PurchaseViewerVC" in body["offer_url"]


def test_credential_issued_with_marketplace_claims(client):
    tc, _ = client
    sd_jwt, holder_did, claim = _full_purchase_to_credential(tc)
    # Decode the SD-JWT VC payload and verify the claims got injected.
    head, payload_b64, *_ = sd_jwt.split(".")
    import base64 as _b64
    pad = "=" * (-len(payload_b64) % 4)
    payload = json.loads(_b64.urlsafe_b64decode(payload_b64 + pad))
    assert payload["dataset_id"] == _BASE_BODY["dataset_id"]
    assert payload["merchandise_address"] == _BASE_BODY["merchandise_address"]
    assert payload["buyer_eth_addr"] == _BASE_BODY["buyer_eth_addr"]
    assert payload["tx_hash"] == _BASE_BODY["tx_hash"]
    assert "read" in payload["allowed_actions"]


def test_eth_did_binding_audited_on_credential_receipt(client):
    tc, pm = client
    _, holder_did, claim_resp = _full_purchase_to_credential(tc)

    # Audit log should now carry the eth_did_bound entry.
    logs = tc.get("/audit/logs?limit=20").json()
    bound = [
        log for log in logs
        if log["raw_topic"] == "marketplace/issued"
        and log["reason"].startswith("eth_did_bound:")
    ]
    assert len(bound) == 1
    log = bound[0]
    assert log["holder_did"] == holder_did
    assert _BASE_BODY["buyer_eth_addr"] in log["reason"]
    assert _BASE_BODY["tx_hash"] in log["reason"]

    # /marketplace/claim/{id} now reports delivered with the holder DID.
    status = tc.get(f"/marketplace/claim/{claim_resp['claim_id']}").json()
    assert status["status"] == "delivered"
    assert status["holder_did"] == holder_did


def test_presentation_yields_viewer_token_with_marketplace_context(client):
    tc, _ = client
    sd_jwt, _, _ = _full_purchase_to_credential(tc)

    req = tc.get(
        "/verifier/request",
        params={"dataset_id": _BASE_BODY["dataset_id"], "vc_kind": "PurchaseViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = _submission("purchase-viewer-temperature", "purchase_viewer_vc_temperature")
    body = tc.post(
        "/verifier/response",
        data={
            "vp_token": sd_jwt,
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    assert body["status"] == "allowed", body
    assert body["vc_kind"] == "PurchaseViewerVC"
    assert "viewer_token" in body
    assert body["merchandise_address"] == _BASE_BODY["merchandise_address"]
    assert body["tx_hash"] == _BASE_BODY["tx_hash"]
    assert body["buyer_eth_addr"] == _BASE_BODY["buyer_eth_addr"]


def test_viewer_token_from_purchase_unlocks_platform_data(client):
    tc, _ = client
    sd_jwt, _, _ = _full_purchase_to_credential(tc)

    req = tc.get(
        "/verifier/request",
        params={"dataset_id": _BASE_BODY["dataset_id"], "vc_kind": "PurchaseViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = _submission("purchase-viewer-temperature", "purchase_viewer_vc_temperature")
    body = tc.post(
        "/verifier/response",
        data={
            "vp_token": sd_jwt,
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    viewer_token = body["viewer_token"]

    r = tc.get(
        "/platform/data",
        params={"dataset_id": _BASE_BODY["dataset_id"]},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 200
    assert r.json()["read_count"] == 1


def test_existing_viewer_vc_flow_unaffected(client):
    """Stage 3 ViewerVC presentation must keep working alongside the v2 path."""
    tc, _ = client
    priv, pub, _ = _make_holder()
    offer = tc.get(
        "/issuer/offer",
        params={"type": "ViewerVC", "dataset_id": _BASE_BODY["dataset_id"], "purpose": "read"},
        headers={"accept": "application/json"},
    ).json()
    token = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": offer["pre_authorized_code"],
        },
    ).json()
    proof = _proof_jwt(priv, pub, token["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={"format": "vc+sd-jwt",
              "vct": "https://iw3ip.example/credentials/ViewerVC/v1",
              "proof": {"proof_type": "jwt", "jwt": proof}},
    ).json()
    req = tc.get(
        "/verifier/request",
        params={"dataset_id": _BASE_BODY["dataset_id"], "vc_kind": "ViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = _submission("viewer-temperature", "viewer_vc_temperature")
    body = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    assert body["status"] == "allowed"
    assert body["vc_kind"] == "ViewerVC"
    assert "merchandise_address" not in body  # only PurchaseViewerVC carries this
