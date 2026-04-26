"""PolicyToken gate on /platform/ingest.

Covers issuance via /verifier/response, single-use consumption, expiry,
dataset mismatch, and that the legacy header-less path still works.
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


def _make_holder_key():
    pk = ec.generate_private_key(ec.SECP256R1())
    jwk = private_key_to_jwk(pk)
    pub = public_jwk_from_private_jwk(jwk)
    did = did_jwk_from_public_jwk(pub)
    return jwk, pub, did


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


def _issue_policy_token(client, *, dataset_id="home/env/temperature", purpose="research") -> tuple[str, str]:
    priv, pub, _ = _make_holder_key()
    offer = client.get(
        "/issuer/offer",
        params={"type": "ConsentVC", "dataset_id": dataset_id, "purpose": purpose},
        headers={"accept": "application/json"},
    ).json()
    token = client.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": offer["pre_authorized_code"],
        },
    ).json()
    proof = _proof_jwt(priv, pub, token["c_nonce"], "http://testserver")
    cred = client.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={"format": "vc+sd-jwt", "proof": {"proof_type": "jwt", "jwt": proof}},
    ).json()
    req = client.get(
        "/verifier/request",
        params={"dataset_id": dataset_id, "purpose": purpose},
        headers={"accept": "application/json"},
    ).json()
    sub = _submission("consent-temperature", "consent_vc_temperature")
    r = client.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    )
    body = r.json()
    assert body["status"] == "allowed", body
    assert "policy_token" in body
    return body["policy_token"], dataset_id


def test_verifier_response_returns_policy_token(client):
    tc, _ = client
    token, dataset_id = _issue_policy_token(tc)
    assert isinstance(token, str) and len(token) > 20


def test_ingest_with_valid_token_succeeds(client):
    tc, _ = client
    token, dataset_id = _issue_policy_token(tc)
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": dataset_id, "purpose": "research", "value": 21.4},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "received"

    logs = tc.get("/audit/logs?limit=5").json()
    assert any(
        log["raw_topic"] == "platform/ingest" and log["action"] == "allow"
        for log in logs
    )


def test_ingest_token_is_single_use(client):
    tc, _ = client
    token, dataset_id = _issue_policy_token(tc)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"dataset_id": dataset_id, "purpose": "research", "value": 1}

    assert tc.post("/platform/ingest", headers=headers, json=body).status_code == 200
    r2 = tc.post("/platform/ingest", headers=headers, json=body)
    assert r2.status_code == 403
    assert "already_consumed" in r2.json()["detail"]


def test_ingest_unknown_token_rejected(client):
    tc, _ = client
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": "Bearer bogus"},
        json={"dataset_id": "home/env/temperature", "purpose": "research"},
    )
    assert r.status_code == 401
    assert "policy_token_unknown" in r.json()["detail"]


def test_ingest_dataset_mismatch_rejected(client):
    tc, _ = client
    token, _ = _issue_policy_token(tc, dataset_id="home/env/temperature")
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": "home/env/humidity", "purpose": "research"},
    )
    assert r.status_code == 403
    assert "dataset_mismatch" in r.json()["detail"]


def test_ingest_expired_token_rejected(client):
    tc, pm = client
    token, dataset_id = _issue_policy_token(tc)
    pt = pm.ssi_state.get_policy_token(token)
    assert pt is not None
    pt.expires_at = time.time() - 1
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": dataset_id, "purpose": "research"},
    )
    assert r.status_code == 401
    assert "policy_token_expired" in r.json()["detail"]


def test_ingest_without_header_still_works(client):
    """Legacy Phase 2 webcam/environment hands-on uses /consents + plain ingest."""
    tc, _ = client
    r = tc.post(
        "/platform/ingest",
        json={"dataset_id": "home/env/temperature", "value": 1},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "received"


def test_ingest_invalid_auth_scheme_rejected(client):
    tc, _ = client
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": "Basic abc"},
        json={"dataset_id": "home/env/temperature"},
    )
    assert r.status_code == 401
