"""POST /marketplace/claim contract: bridge -> publisher hand-off.

M2 covers:
  - new claim creates an Offer reachable via /issuer/token
  - replaying the same tx_hash is idempotent
  - missing fields rejected
  - GET /marketplace/claim/{id} reflects status

PurchaseViewerVC issuance with merchandise/tx claims and the
eth_addr <-> did:jwk binding land in M3.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


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


def test_claim_creates_offer_and_returns_deeplink(client):
    tc, _ = client
    r = tc.post("/marketplace/claim", json=_BASE_BODY)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["claim_id"]
    assert body["created"] is True
    assert body["deeplink"].startswith("openid-credential-offer://")
    assert body["offer_url"].startswith("http://testserver/issuer/offer")
    assert body["merchandise_address"] == _BASE_BODY["merchandise_address"]
    assert body["tx_hash"] == _BASE_BODY["tx_hash"]


def test_claim_is_idempotent_on_tx_hash(client):
    tc, _ = client
    r1 = tc.post("/marketplace/claim", json=_BASE_BODY).json()
    r2 = tc.post("/marketplace/claim", json=_BASE_BODY).json()
    assert r1["claim_id"] == r2["claim_id"]
    assert r1["deeplink"] == r2["deeplink"]
    assert r2["created"] is False


def test_claim_status_endpoint_reports_pending_until_holder_attaches(client):
    tc, pm = client
    body = tc.post("/marketplace/claim", json=_BASE_BODY).json()
    s1 = tc.get(f"/marketplace/claim/{body['claim_id']}").json()
    assert s1["status"] == "pending"
    assert s1["holder_did"] is None

    # Simulate M3 attaching a wallet holder DID
    pm.ssi_state.attach_holder_to_claim(body["claim_id"], "did:jwk:test-holder")
    s2 = tc.get(f"/marketplace/claim/{body['claim_id']}").json()
    assert s2["status"] == "delivered"
    assert s2["holder_did"] == "did:jwk:test-holder"


def test_claim_missing_field_rejected(client):
    tc, _ = client
    incomplete = {k: v for k, v in _BASE_BODY.items() if k != "buyer_eth_addr"}
    r = tc.post("/marketplace/claim", json=incomplete)
    assert r.status_code == 400
    assert "missing_field:buyer_eth_addr" in r.json()["detail"]


def test_claim_unknown_id_returns_404(client):
    tc, _ = client
    r = tc.get("/marketplace/claim/does-not-exist")
    assert r.status_code == 404


def test_claim_audit_log_records_eth_addr_and_tx(client):
    tc, _ = client
    body = tc.post("/marketplace/claim", json=_BASE_BODY).json()
    logs = tc.get("/audit/logs?limit=5").json()
    matching = [
        log for log in logs
        if log["raw_topic"] == "marketplace/claim"
        and body["claim_id"] in log["reason"]
    ]
    assert len(matching) == 1
    log = matching[0]
    assert log["action"] == "allow"
    assert _BASE_BODY["tx_hash"] in log["reason"]
    assert log["subject_did"] == f"eth:{_BASE_BODY['buyer_eth_addr']}"
    assert log["dataset_id"] == _BASE_BODY["dataset_id"]


def test_claim_offer_redeemable_via_issuer_token(client):
    """The pre_authorized_code embedded in the deeplink should be
    accepted by /issuer/token, proving the bridge -> issuer hand-off
    is wired correctly. Full credential issuance with M3 PurchaseViewerVC
    claims is exercised separately."""
    import json as _json
    import urllib.parse as _urllib

    tc, _ = client
    body = tc.post("/marketplace/claim", json=_BASE_BODY).json()
    # Decode the credential_offer query param to extract pre-auth code
    deeplink = body["deeplink"]
    qs = deeplink.split("?", 1)[1]
    co = _json.loads(_urllib.unquote(qs.split("=", 1)[1]))
    pre_auth = co["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]

    r = tc.post(
        "/issuer/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
            "pre-authorized_code": pre_auth,
        },
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()
