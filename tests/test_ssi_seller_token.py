"""SellerVC issuance + presentation + multi-use SellerToken (Stage 7 / C2).

Stage 7 introduces a 5th VC kind that gates marketplace registration.
This file covers the publisher-side basics:
  - issuer metadata advertises SellerVC
  - /issuer/offer accepts type=SellerVC + seller_id + licensed_datasets
  - presentation yields a SellerToken with the licensed_datasets list
  - SellerToken is multi-use within TTL
  - dataset not in licensed_datasets is rejected on use
  - SellerToken cannot be used as a write/read token (namespace isolation)

Stage 7 / C3 will add /marketplace/register on top.
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


def _issue_seller_token(client, *, seller_id="ertl-001",
                        licensed="home/env/temperature,home/env/humidity") -> tuple[str, list[str]]:
    priv, pub, _ = _holder()
    offer = client.get(
        "/issuer/offer",
        params={
            "type": "SellerVC",
            "seller_id": seller_id,
            "licensed_datasets": licensed,
        },
        headers={"accept": "application/json"},
    ).json()
    token = client.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": offer["pre_authorized_code"],
        },
    ).json()
    proof = _proof(priv, pub, token["c_nonce"], "http://testserver")
    cred = client.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/SellerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    req = client.get(
        "/verifier/request",
        params={"vc_kind": "SellerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-seller-vc",
        "definition_id": "seller-vc",
        "descriptor_map": [{"id": "seller_vc", "format": "vc+sd-jwt", "path": "$"}],
    }
    body = client.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    assert body["status"] == "allowed", body
    assert body["vc_kind"] == "SellerVC"
    assert body["seller_id"] == seller_id
    return body["seller_token"], body["licensed_datasets"]


def test_issuer_metadata_lists_seller_vc(client):
    tc, _ = client
    cfgs = tc.get("/.well-known/openid-credential-issuer").json()["credential_configurations_supported"]
    assert "SellerVC" in cfgs
    assert cfgs["SellerVC"]["vct"].endswith("/SellerVC/v1")


def test_issuer_offer_requires_seller_id(client):
    tc, _ = client
    r = tc.get(
        "/issuer/offer",
        params={"type": "SellerVC", "licensed_datasets": "x"},
        headers={"accept": "application/json"},
    )
    assert r.status_code == 400
    assert "seller_id" in r.json()["detail"]


def test_issuer_offer_requires_licensed_datasets(client):
    tc, _ = client
    r = tc.get(
        "/issuer/offer",
        params={"type": "SellerVC", "seller_id": "x"},
        headers={"accept": "application/json"},
    )
    assert r.status_code == 400
    assert "licensed_datasets" in r.json()["detail"]


def test_seller_response_returns_token_and_metadata(client):
    tc, _ = client
    token, licensed = _issue_seller_token(tc)
    assert isinstance(token, str) and len(token) > 20
    assert sorted(licensed) == ["home/env/humidity", "home/env/temperature"]


def test_seller_token_use_succeeds_for_licensed_dataset(client):
    tc, pm = client
    token, _ = _issue_seller_token(tc)
    st, reason = pm.ssi_state.use_seller_token(token, dataset_id="home/env/temperature")
    assert reason == "ok"
    assert st is not None
    assert st.register_count == 1


def test_seller_token_use_rejected_for_unlicensed_dataset(client):
    tc, pm = client
    token, _ = _issue_seller_token(tc, licensed="home/env/temperature")
    _, reason = pm.ssi_state.use_seller_token(token, dataset_id="home/env/humidity")
    assert reason == "dataset_not_licensed"


def test_seller_token_is_multi_use(client):
    tc, pm = client
    token, _ = _issue_seller_token(tc)
    for expected in (1, 2, 3, 4):
        st, reason = pm.ssi_state.use_seller_token(token, dataset_id="home/env/temperature")
        assert reason == "ok"
        assert st.register_count == expected


def test_seller_token_expired(client):
    tc, pm = client
    token, _ = _issue_seller_token(tc)
    pm.ssi_state.get_seller_token(token).expires_at = time.time() - 1
    _, reason = pm.ssi_state.use_seller_token(token, dataset_id="home/env/temperature")
    assert reason == "expired"


def test_seller_token_unknown(client):
    _, pm = client
    _, reason = pm.ssi_state.use_seller_token("bogus", dataset_id="home/env/temperature")
    assert reason == "unknown"


# ---- Stage T (PWA provider, c1): /provider/start + cross-device polling ----


def test_provider_start_page_renders_html(client):
    tc, _ = client
    r = tc.get("/provider/start", params={"ds": "home/env/temperature"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    body = r.text
    # Page should hard-code SellerVC as the vc_kind it asks for and
    # bootstrap /verifier/request itself.
    assert "SellerVC" in body
    assert "/verifier/request" in body
    assert "/verifier/status" in body
    # Dataset hint should land in the page (so audit logs see what the
    # provider intended even though SellerVC isn't dataset-bound).
    assert "home/env/temperature" in body
    # QR rendering is client-side via qrcode-svg CDN.
    assert "qrcode" in body.lower() or "QRCode" in body


def test_provider_start_accepts_optional_ds(client):
    """ds is optional -- SellerVC verification isn't dataset-scoped, the
    page just shows the hint when given."""
    tc, _ = client
    r = tc.get("/provider/start")
    assert r.status_code == 200
    assert "SellerVC" in r.text


def test_seller_vc_response_returns_redirect_uri_to_provider_start(client):
    """c1: a successful SellerVC presentation must echo a redirect_uri
    pointing back at /provider/start?state=... so same-device wallets
    can bounce the user back to the polling page."""
    tc, _ = client
    # _issue_seller_token already asserts status == "allowed".
    # Inspect the raw /verifier/response by mirroring its setup.
    priv, pub, _ = _holder()
    offer = tc.get(
        "/issuer/offer",
        params={"type": "SellerVC", "seller_id": "ertl-001",
                "licensed_datasets": "home/env/temperature"},
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
    state = req["authorization_request"]["state"]
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
            "state": state,
        },
    ).json()
    assert body["status"] == "allowed"
    assert body["vc_kind"] == "SellerVC"
    assert "redirect_uri" in body, body
    # Must point at /provider/start with the same state so the resume
    # branch in the page-side script picks it up.
    assert "/provider/start" in body["redirect_uri"]
    assert f"state={state}" in body["redirect_uri"]


def test_verifier_status_surfaces_seller_token_after_success(client):
    """c1: cross-device polling -- once SellerVC has been presented,
    /verifier/status must echo seller_token + licensed_datasets so the
    /provider/start page can render its inline success panel."""
    tc, pm = client
    seller_token, licensed = _issue_seller_token(tc)
    # Most recent verification request state corresponds to the SellerVC
    # presentation just issued by the helper.
    state = list(pm.ssi_state._requests.keys())[-1]
    r = tc.get("/verifier/status", params={"state": state})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["seller_token"] == seller_token
    assert sorted(body["licensed_datasets"]) == sorted(licensed)
    assert body["seller_id"] == "ertl-001"
    # Inner result must record the verified=True branch.
    assert body["result"]["verified"] is True
    assert body["result"]["vc_kind"] == "SellerVC"
