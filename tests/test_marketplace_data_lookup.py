"""GET /platform/data?merchandise=<addr> reverse lookup (M4 / v2).

The bridge records merchandise_address -> dataset_id during /marketplace/claim;
M4 lets the buyer fetch data without typing the dataset_id, using the
merchandise contract address as the index.
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


_BASE = {
    "merchandise_address": "0x0000000000000000000000000000000000000abc",
    "buyer_eth_addr": "0xdeadbeef00000000000000000000000000000000",
    "tx_hash": "0xfeedface" + "00" * 28,
    "dataset_id": "home/env/temperature",
    "purchase_amount_wei": "1",
}


def _proof(priv, pub, nonce, aud):
    h = _b64u(_json_bytes({"alg": "ES256", "typ": "openid4vci-proof+jwt", "jwk": pub}))
    p = _b64u(_json_bytes({"nonce": nonce, "aud": aud, "iat": int(time.time())}))
    sig = _es256_sign(priv, (h + "." + p).encode("ascii"))
    return h + "." + p + "." + _b64u(sig)


def _viewer_token_after_purchase(tc) -> tuple[str, dict]:
    claim = tc.post("/marketplace/claim", json=_BASE).json()
    pre_auth = json.loads(__import__("urllib.parse").parse.unquote(
        claim["deeplink"].split("=", 1)[1]
    ))["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]
    pk = ec.generate_private_key(ec.SECP256R1())
    priv = private_key_to_jwk(pk)
    pub = public_jwk_from_private_jwk(priv)

    token = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    ).json()
    proof = _proof(priv, pub, token["c_nonce"], "http://testserver")
    cred = tc.post(
        "/issuer/credential",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "format": "vc+sd-jwt",
            "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
            "proof": {"proof_type": "jwt", "jwt": proof},
        },
    ).json()

    req = tc.get(
        "/verifier/request",
        params={"dataset_id": _BASE["dataset_id"], "vc_kind": "PurchaseViewerVC"},
        headers={"accept": "application/json"},
    ).json()
    sub = {
        "id": "sub-purchase-viewer-temperature",
        "definition_id": "purchase-viewer-temperature",
        "descriptor_map": [{"id": "purchase_viewer_vc_temperature", "format": "vc+sd-jwt", "path": "$"}],
    }
    body = tc.post(
        "/verifier/response",
        data={
            "vp_token": cred["credential"],
            "presentation_submission": json.dumps(sub),
            "state": req["state"],
        },
    ).json()
    return body["viewer_token"], claim


def test_merchandise_lookup_returns_data(client):
    tok, claim = _viewer_token_after_purchase(client)
    r = client.get(
        "/platform/data",
        params={"merchandise": _BASE["merchandise_address"]},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dataset_id"] == _BASE["dataset_id"]
    assert body["read_count"] == 1


def test_merchandise_lookup_is_case_insensitive(client):
    tok, _ = _viewer_token_after_purchase(client)
    upper = _BASE["merchandise_address"].upper().replace("0X", "0x")
    r = client.get(
        "/platform/data",
        params={"merchandise": upper},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text


def test_unknown_merchandise_returns_404(client):
    r = client.get(
        "/platform/data",
        params={"merchandise": "0x" + "ff" * 20},
        headers={"Authorization": "Bearer any"},
    )
    assert r.status_code == 404
    assert "unknown_merchandise" in r.json()["detail"]


def test_both_or_neither_dataset_id_and_merchandise_rejected(client):
    # Both
    r1 = client.get(
        "/platform/data",
        params={"dataset_id": "x", "merchandise": "0xabc"},
        headers={"Authorization": "Bearer any"},
    )
    assert r1.status_code == 400
    # Neither
    r2 = client.get(
        "/platform/data",
        headers={"Authorization": "Bearer any"},
    )
    # FastAPI surfaces "missing query" for both being None? Actually
    # both Optional now, so it goes to our validation:
    assert r2.status_code in (400, 422)


def test_merchandise_lookup_token_dataset_mismatch_rejected(client):
    """A ViewerToken bound to dataset A must not unlock data via a
    merchandise that maps to dataset B."""
    tok, _ = _viewer_token_after_purchase(client)
    # Register a different merchandise under a different dataset
    other = {
        **_BASE,
        "merchandise_address": "0x" + "11" * 20,
        "tx_hash": "0x" + "22" * 32,
        "dataset_id": "home/env/humidity",
    }
    client.post("/marketplace/claim", json=other)
    r = client.get(
        "/platform/data",
        params={"merchandise": other["merchandise_address"]},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 403
    assert "dataset_mismatch" in r.json()["detail"]
