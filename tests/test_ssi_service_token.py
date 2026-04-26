"""ServiceVC issuance + presentation + multi-use ServiceToken on /platform/ingest.

Stage-4-prep counterpart that lets an M2M publisher write many events
under one presentation, complementing single-use PolicyToken.
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


def _issue_service_token(client, *, dataset_id="home/env/temperature") -> str:
    priv, pub, _ = _make_holder_key()

    offer = client.get(
        "/issuer/offer",
        params={"type": "ServiceVC", "dataset_id": dataset_id, "purpose": "write_continuous"},
        headers={"accept": "application/json"},
    ).json()
    assert offer["vc_kind"] == "ServiceVC"
    assert offer["allowed_purposes"] == ["write_continuous"]

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
            "vct": "https://iw3ip.example/credentials/ServiceVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()

    req = client.get(
        "/verifier/request",
        params={"dataset_id": dataset_id, "vc_kind": "ServiceVC"},
        headers={"accept": "application/json"},
    ).json()

    sub = _submission("service-temperature", "service_vc_temperature")
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
    assert body["vc_kind"] == "ServiceVC"
    assert "service_token" in body
    return body["service_token"]


def test_issuer_metadata_lists_service_vc(client):
    tc, _ = client
    cfgs = tc.get("/.well-known/openid-credential-issuer").json()["credential_configurations_supported"]
    assert "ServiceVC" in cfgs
    assert cfgs["ServiceVC"]["vct"].endswith("/ServiceVC/v1")


def test_service_response_returns_service_token(client):
    tc, _ = client
    token = _issue_service_token(tc)
    assert isinstance(token, str) and len(token) > 20


def test_ingest_with_service_token_succeeds(client):
    tc, _ = client
    token = _issue_service_token(tc)
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": "home/env/temperature", "purpose": "write_continuous", "value": 21.4},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "received"


def test_service_token_is_multi_use(client):
    tc, _ = client
    token = _issue_service_token(tc)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"dataset_id": "home/env/temperature", "value": 1}
    for _ in range(5):
        r = tc.post("/platform/ingest", headers=headers, json=body)
        assert r.status_code == 200, r.text


def test_service_token_dataset_mismatch_rejected(client):
    tc, _ = client
    token = _issue_service_token(tc, dataset_id="home/env/temperature")
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": "home/env/humidity", "value": 1},
    )
    assert r.status_code == 403
    assert "dataset_mismatch" in r.json()["detail"]


def test_service_token_expired_rejected(client):
    tc, pm = client
    token = _issue_service_token(tc)
    st = pm.ssi_state.get_service_token(token)
    assert st is not None
    st.expires_at = time.time() - 1
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": "home/env/temperature", "value": 1},
    )
    assert r.status_code == 401
    assert "service_token_expired" in r.json()["detail"]


def test_service_audit_records_write_count(client):
    tc, _ = client
    token = _issue_service_token(tc)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"dataset_id": "home/env/temperature", "value": 1}
    for _ in range(3):
        tc.post("/platform/ingest", headers=headers, json=body)
    logs = tc.get("/audit/logs?limit=10").json()
    used_logs = [
        log for log in logs
        if log["raw_topic"] == "platform/ingest"
        and log["reason"].startswith("service_token_used:")
    ]
    assert len(used_logs) >= 3
    # write_count appended at end of reason
    counts = sorted(int(log["reason"].rsplit(":", 1)[1]) for log in used_logs[:3])
    assert counts == [1, 2, 3]


def test_policy_token_still_works_alongside(client):
    """Stage 1 PolicyToken path is unaffected by ServiceToken addition."""
    tc, _ = client
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

    # First use OK
    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {policy_token}"},
        json={"dataset_id": "home/env/temperature", "purpose": "research", "value": 1},
    )
    assert r.status_code == 200

    # Second use rejected with already_consumed (PolicyToken single-use)
    r2 = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {policy_token}"},
        json={"dataset_id": "home/env/temperature", "purpose": "research", "value": 1},
    )
    assert r2.status_code == 403
    assert "already_consumed" in r2.json()["detail"]


def test_viewer_token_does_not_unlock_ingest(client):
    """A ViewerToken (read authz) must NOT be accepted by /platform/ingest."""
    tc, _ = client
    # Issue a ViewerVC
    priv, pub, _ = _make_holder_key()
    offer = tc.get(
        "/issuer/offer",
        params={"type": "ViewerVC", "dataset_id": "home/env/temperature", "purpose": "read"},
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
        json={"format": "vc+sd-jwt", "vct": "https://iw3ip.example/credentials/ViewerVC/v1",
              "proof": {"proof_type": "jwt", "jwt": proof}},
    ).json()
    req = tc.get(
        "/verifier/request",
        params={"dataset_id": "home/env/temperature", "vc_kind": "ViewerVC"},
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
    viewer_token = body["viewer_token"]

    r = tc.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"dataset_id": "home/env/temperature", "value": 1},
    )
    # Both PolicyToken (unknown) and ServiceToken (unknown) reject → 401
    assert r.status_code == 401
