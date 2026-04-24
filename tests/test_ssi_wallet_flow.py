"""End-to-end OID4VCI issuance + OID4VP presentation using the local
PEX fallback (no Node sidecar running).

Simulates a Sphereon-style wallet: generate a P-256 holder key, do the
pre-authorized_code flow against /issuer/token + /issuer/credential, then
post the resulting SD-JWT VC back to /verifier/response for the challenge
created by /verifier/request.
"""
from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from publisher.app.ssi.did_jwk import did_jwk_from_public_jwk
from publisher.app.ssi.keys import private_key_to_jwk, public_jwk_from_private_jwk
from publisher.app.ssi.sdjwt import _es256_sign, _b64u, _json_bytes


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

    # Force the sidecar to be unreachable so we exercise the local fallback.
    monkeypatch.setenv("SSI_PEX_SIDECAR_URL", "http://127.0.0.1:1")

    import importlib
    import publisher.app.main as pm
    importlib.reload(pm)

    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        from fastapi.testclient import TestClient
        with TestClient(pm.app) as tc:
            yield tc


def _make_holder_key():
    pk = ec.generate_private_key(ec.SECP256R1())
    jwk = private_key_to_jwk(pk)
    pub = public_jwk_from_private_jwk(jwk)
    did = did_jwk_from_public_jwk(pub)
    return jwk, pub, did


def _make_proof_jwt(holder_jwk_private, holder_jwk_public, nonce, aud):
    header = {"alg": "ES256", "typ": "openid4vci-proof+jwt", "jwk": holder_jwk_public}
    payload = {"nonce": nonce, "aud": aud, "iat": int(time.time())}
    h = _b64u(_json_bytes(header))
    p = _b64u(_json_bytes(payload))
    sig = _es256_sign(holder_jwk_private, (h + "." + p).encode("ascii"))
    return h + "." + p + "." + _b64u(sig)


def _make_presentation_submission(pd_id: str, input_desc_id: str) -> dict:
    return {
        "id": "sub-" + pd_id,
        "definition_id": pd_id,
        "descriptor_map": [
            {"id": input_desc_id, "format": "vc+sd-jwt", "path": "$"}
        ],
    }


def test_health_and_well_known(client):
    assert client.get("/health").json()["status"] == "ok"
    meta = client.get("/.well-known/openid-credential-issuer").json()
    assert meta["credential_endpoint"].endswith("/issuer/credential")
    assert "ConsentVC" in meta["credential_configurations_supported"]


def test_presentation_definition_lookup(client):
    pd = client.get("/verifier/presentation-definitions/consent-temperature").json()
    assert pd["iw3ip_dataset_id"] == "home/env/temperature"
    assert client.get("/verifier/presentation-definitions/unknown").status_code == 404


def test_full_issuance_and_verification_allow(client):
    holder_priv, holder_pub, holder_did = _make_holder_key()

    # 1. offer (JSON form)
    offer = client.get(
        "/issuer/offer",
        params={"type": "ConsentVC", "dataset_id": "home/env/temperature", "purpose": "research"},
        headers={"accept": "application/json"},
    ).json()
    pre_auth = offer["pre_authorized_code"]

    # 2. token
    token = client.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    ).json()
    assert "access_token" in token
    assert "c_nonce" in token

    # 3. credential (with proof JWT)
    proof = _make_proof_jwt(holder_priv, holder_pub, token["c_nonce"], "http://testserver")
    cred = client.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/ConsentVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    vp_token = cred["credential"]
    assert vp_token.count("~") >= 1

    # 4. verifier request
    req = client.get(
        "/verifier/request",
        params={"dataset_id": "home/env/temperature", "purpose": "research"},
        headers={"accept": "application/json"},
    ).json()
    state = req["state"]

    # 5. verifier response (ALLOW path)
    submission = _make_presentation_submission("consent-temperature", "consent_vc_temperature")
    r = client.post(
        "/verifier/response",
        data={
            "vp_token": vp_token,
            "presentation_submission": json.dumps(submission),
            "state": state,
        },
    )
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "allowed", body
    assert body["dataset_id"] == "home/env/temperature"

    logs = client.get("/audit/logs?limit=5").json()
    latest = logs[0]
    assert latest["action"] == "allow"
    assert latest["presentation_verified"] == "allow"
    assert latest["holder_did"] == holder_did
    assert latest["dataset_id"] == "home/env/temperature"
    assert latest["vc_hash"].startswith("sha256:")


def test_purpose_mismatch_denied(client):
    holder_priv, holder_pub, _ = _make_holder_key()
    offer = client.get(
        "/issuer/offer",
        params={"type": "ConsentVC", "dataset_id": "home/env/temperature", "purpose": "research"},
        headers={"accept": "application/json"},
    ).json()
    token = client.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": offer["pre_authorized_code"],
        },
    ).json()
    proof = _make_proof_jwt(holder_priv, holder_pub, token["c_nonce"], "http://testserver")
    cred = client.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()

    # Request verification with a purpose that is NOT in allowed_purposes
    req = client.get(
        "/verifier/request",
        params={"dataset_id": "home/env/temperature", "purpose": "marketing"},
        headers={"accept": "application/json"},
    ).json()
    submission = _make_presentation_submission("consent-temperature", "consent_vc_temperature")
    r = client.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(submission),
            "state": req["state"],
        },
    )
    body = r.json()
    assert body["status"] == "denied"
    assert body["reason"] == "purpose_mismatch"

    logs = client.get("/audit/logs?limit=5").json()
    assert logs[0]["action"] == "deny"
    assert logs[0]["presentation_verified"] == "deny"
    assert logs[0]["reason"] == "purpose_mismatch"


def test_phase1_consents_still_work(client):
    """Ensure Phase 1 /consents + /simulate/publish remain non-breaking."""
    consent = {
        "vc_id": "consent-test-1",
        "subject_did": "did:example:alice",
        "dataset_id": "home/env/temperature",
        "allowed_purposes": ["research"],
        "retention_days": 30,
        "reshare_allowed": False,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": "2099-01-01T00:00:00Z",
        "signature": "stub",
    }
    r = client.post("/consents", json=consent)
    assert r.status_code == 200, r.text
    listed = client.get("/consents").json()
    assert any(c["vc_id"] == "consent-test-1" for c in listed)
