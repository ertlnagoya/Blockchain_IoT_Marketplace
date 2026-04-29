"""Smoke test: home/event/* dataset_ids work across the same flows
that home/env/* did, so Phase 2 hands-on can use Stage-0-shaped
camera / environment events end-to-end without breaking the wallet
authz layer.
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
            yield tc


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


def test_consent_vc_for_event_namespace_can_be_issued_and_presented(client):
    """ConsentVC issuance + presentation + ingest works for
    home/event/possible_littering — the dataset Phase 2 Stage 0 already
    uses, so Stage 1+ hands-on can reuse the same data shape."""
    priv, pub, _ = _holder()

    offer = client.get(
        "/issuer/offer",
        params={
            "type": "ConsentVC",
            "dataset_id": "home/event/possible_littering",
            "purpose": "community_cleaning",
        },
        headers={"accept": "application/json"},
    ).json()
    assert "community_cleaning" in offer["allowed_purposes"]

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
            "vct": "https://iw3ip.example/credentials/ConsentVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()

    req = client.get(
        "/verifier/request",
        params={"dataset_id": "home/event/possible_littering", "purpose": "community_cleaning"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-consent-possible-littering",
        "definition_id": "consent-possible-littering",
        "descriptor_map": [{"id": "consent_vc_possible_littering", "format": "vc+sd-jwt", "path": "$"}],
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
    assert body["vc_kind"] == "ConsentVC"
    policy_token = body["policy_token"]

    # And the policy token actually unlocks an ingest payload that looks
    # like the Stage 0 webcam-event-sharing payload (rich event data,
    # not just {"value": 21.4}).
    r = client.post(
        "/platform/ingest",
        headers={"Authorization": f"Bearer {policy_token}"},
        json={
            "dataset_id": "home/event/possible_littering",
            "purpose": "community_cleaning",
            "event_type": "possible_littering",
            "data": {
                "camera_id": "webcam-401",
                "location": "park-north",
                "object_class": "bottle",
                "confidence": 0.87,
            },
            "ts": "2026-04-28T11:02:00Z",
            "source": "edge_inference",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "received"


def test_viewer_vc_for_event_namespace(client):
    """Same dataset_id is gated for read via ViewerVC + ViewerToken."""
    priv, pub, _ = _holder()

    offer = client.get(
        "/issuer/offer",
        params={"type": "ViewerVC", "dataset_id": "home/event/possible_littering", "purpose": "read"},
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
            "vct": "https://iw3ip.example/credentials/ViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()

    req = client.get(
        "/verifier/request",
        params={"dataset_id": "home/event/possible_littering", "vc_kind": "ViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-viewer-possible-littering",
        "definition_id": "viewer-possible-littering",
        "descriptor_map": [{"id": "viewer_vc_possible_littering", "format": "vc+sd-jwt", "path": "$"}],
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
    assert body["vc_kind"] == "ViewerVC"
    assert "viewer_token" in body


def test_default_allowed_purposes_includes_event_datasets(client):
    """The DEFAULT_ALLOWED_PURPOSES table must answer for the event
    datasets we just added; otherwise issuer_offer falls back to a
    single-element list with whatever purpose the caller passed."""
    # community_cleaning isn't in any home/env/* default, so if the
    # offer comes back with that allowed list size > 1, we know the
    # event-namespace entry was honoured.
    offer = client.get(
        "/issuer/offer",
        params={
            "type": "ConsentVC",
            "dataset_id": "home/event/possible_littering",
            "purpose": "community_cleaning",
        },
        headers={"accept": "application/json"},
    ).json()
    assert "community_cleaning" in offer["allowed_purposes"]
    assert "research" in offer["allowed_purposes"]


def test_existing_env_namespace_unchanged(client):
    """Regression: the Stage 1-7 home/env/temperature path keeps working."""
    offer = client.get(
        "/issuer/offer",
        params={"type": "ConsentVC", "dataset_id": "home/env/temperature", "purpose": "research"},
        headers={"accept": "application/json"},
    ).json()
    assert "research" in offer["allowed_purposes"]
