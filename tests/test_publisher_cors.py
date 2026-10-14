"""CORS: the marketplace UI (:5173) calls the publisher from the browser."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def _client(monkeypatch, tmp_path, origins: str | None):
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
    if origins is None:
        monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", origins)

    import importlib
    import publisher.app.main as pm
    importlib.reload(pm)
    from fastapi.testclient import TestClient
    return TestClient(pm.app)


PREFLIGHT = {
    "Origin": "http://192.168.1.20:5173",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}


@pytest.mark.parametrize("origins", [None, "*"])
def test_preflight_for_marketplace_claim_is_allowed(monkeypatch, tmp_path, origins):
    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        r = _client(monkeypatch, tmp_path, origins).options("/marketplace/claim", headers=PREFLIGHT)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] in ("*", PREFLIGHT["Origin"])


def test_cors_can_be_disabled(monkeypatch, tmp_path):
    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        r = _client(monkeypatch, tmp_path, "").options("/marketplace/claim", headers=PREFLIGHT)
    assert "access-control-allow-origin" not in r.headers
