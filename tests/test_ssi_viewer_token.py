"""ViewerVC issuance + OID4VP presentation + ViewerToken-gated /platform/data.

Stage 3 read-side counterpart to test_ssi_policy_token.py.
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


def _issue_viewer_token(client, *, dataset_id="home/env/temperature") -> tuple[str, str]:
    priv, pub, _ = _make_holder_key()

    offer = client.get(
        "/issuer/offer",
        params={"type": "ViewerVC", "dataset_id": dataset_id, "purpose": "read"},
        headers={"accept": "application/json"},
    ).json()
    assert offer["vc_kind"] == "ViewerVC"
    assert offer["allowed_purposes"] == ["read"]

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
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/ViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()
    assert cred["credential"].count("~") >= 1

    req = client.get(
        "/verifier/request",
        params={"dataset_id": dataset_id, "vc_kind": "ViewerVC"},
        headers={"accept": "application/json"},
    ).json()

    sub = _submission("viewer-temperature", "viewer_vc_temperature")
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
    assert body["vc_kind"] == "ViewerVC"
    assert "viewer_token" in body
    return body["viewer_token"], dataset_id


def _seed_ingested(client, pm, dataset_id, values):
    """Inject rows directly into in-memory ingested list (write path is tested elsewhere)."""
    for v in values:
        pm.app.state.ingested.append({"dataset_id": dataset_id, "value": v})


def test_issuer_metadata_lists_both_vc_kinds(client):
    tc, _ = client
    meta = tc.get("/.well-known/openid-credential-issuer").json()
    cfgs = meta["credential_configurations_supported"]
    assert "ConsentVC" in cfgs
    assert "ViewerVC" in cfgs
    assert cfgs["ViewerVC"]["vct"].endswith("/ViewerVC/v1")


def test_viewer_response_returns_viewer_token(client):
    tc, _ = client
    token, dataset_id = _issue_viewer_token(tc)
    assert isinstance(token, str) and len(token) > 20


def test_data_with_valid_viewer_token_succeeds(client):
    tc, pm = client
    token, dataset_id = _issue_viewer_token(tc)
    _seed_ingested(tc, pm, dataset_id, [21.4, 22.0, 22.7])
    r = tc.get(
        f"/platform/data?dataset_id={dataset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 3
    assert len(body["rows"]) == 3
    assert body["read_count"] == 1


def test_viewer_token_is_multi_use_within_ttl(client):
    tc, pm = client
    token, dataset_id = _issue_viewer_token(tc)
    _seed_ingested(tc, pm, dataset_id, [1.0])
    headers = {"Authorization": f"Bearer {token}"}
    url = f"/platform/data?dataset_id={dataset_id}"
    assert tc.get(url, headers=headers).json()["read_count"] == 1
    assert tc.get(url, headers=headers).json()["read_count"] == 2
    assert tc.get(url, headers=headers).json()["read_count"] == 3


def test_data_unknown_token_rejected(client):
    tc, _ = client
    r = tc.get(
        "/platform/data?dataset_id=home/env/temperature",
        headers={"Authorization": "Bearer bogus"},
    )
    assert r.status_code == 401
    assert "viewer_token_unknown" in r.json()["detail"]


def test_data_dataset_mismatch_rejected(client):
    tc, _ = client
    token, _ = _issue_viewer_token(tc)
    r = tc.get(
        "/platform/data?dataset_id=home/env/humidity",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert "dataset_mismatch" in r.json()["detail"]


def test_data_expired_token_rejected(client):
    tc, pm = client
    token, dataset_id = _issue_viewer_token(tc)
    vt = pm.ssi_state.get_viewer_token(token)
    assert vt is not None
    vt.expires_at = time.time() - 1
    r = tc.get(
        f"/platform/data?dataset_id={dataset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert "viewer_token_expired" in r.json()["detail"]


def test_data_missing_header_rejected(client):
    tc, _ = client
    r = tc.get("/platform/data?dataset_id=home/env/temperature")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_authorization_header"


def test_consent_vc_token_does_not_unlock_read(client):
    """A PolicyToken (write authz) must NOT be accepted as a ViewerToken."""
    tc, pm = client
    # Reuse the Stage 1 issuance path
    priv, pub, _ = _make_holder_key()
    offer = tc.get(
        "/issuer/offer",
        params={"type": "ConsentVC", "dataset_id": "home/env/temperature", "purpose": "research"},
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
        json={"format": "vc+sd-jwt", "proof": {"proof_type": "jwt", "jwt": proof}},
    ).json()
    req = tc.get(
        "/verifier/request",
        params={"dataset_id": "home/env/temperature", "purpose": "research"},
        headers={"accept": "application/json"},
    ).json()
    sub = _submission("consent-temperature", "consent_vc_temperature")
    body = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    policy_token = body["policy_token"]

    # PolicyToken should be rejected by /platform/data (it's a write token)
    r = tc.get(
        "/platform/data?dataset_id=home/env/temperature",
        headers={"Authorization": f"Bearer {policy_token}"},
    )
    assert r.status_code == 401
    assert "viewer_token_unknown" in r.json()["detail"]


def test_audit_log_records_read(client):
    tc, pm = client
    token, dataset_id = _issue_viewer_token(tc)
    _seed_ingested(tc, pm, dataset_id, [9.9])
    tc.get(
        f"/platform/data?dataset_id={dataset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    logs = tc.get("/audit/logs?limit=5").json()
    assert any(
        log["raw_topic"] == "platform/data"
        and log["action"] == "allow"
        and log["purpose"] == "read"
        and log["reason"].startswith("viewer_token_used:")
        for log in logs
    )
