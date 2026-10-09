"""GET /platform/ingest is a demo-only, unauthenticated read path.

It must stay off by default (the read path is the ViewerToken-gated
/platform/data) and only return rows when explicitly enabled.
"""
from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest


def _client(monkeypatch, tmp_path, enabled: str | None):
    monkeypatch.setenv("SSI_ISSUER_KEY_PATH", str(tmp_path / "issuer_key.jwk.json"))
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("CONSENT_STORE_PATH", str(tmp_path / "consents.json"))
    monkeypatch.setenv("PLATFORM_API_URL", "http://testserver/platform/ingest")
    monkeypatch.setenv("MQTT_TOPICS", "")
    if enabled is None:
        monkeypatch.delenv("PLATFORM_INGEST_READ_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PLATFORM_INGEST_READ_ENABLED", enabled)

    import publisher.app.main as pm

    importlib.reload(pm)
    return pm


@pytest.mark.parametrize("enabled", [None, "false"])
def test_get_platform_ingest_is_disabled_by_default(monkeypatch, tmp_path, enabled):
    pm = _client(monkeypatch, tmp_path, enabled)
    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        from fastapi.testclient import TestClient

        with TestClient(pm.app) as tc:
            tc.post("/platform/ingest", json={"dataset_id": "home/env/temperature", "value": 1})
            res = tc.get("/platform/ingest")
    assert res.status_code == 404
    assert res.json()["detail"] == "platform_ingest_read_disabled"


def test_get_platform_ingest_returns_rows_when_enabled(monkeypatch, tmp_path):
    pm = _client(monkeypatch, tmp_path, "true")
    with patch("publisher.app.mqtt_subscriber.MQTTSubscriber.start", lambda self: None), \
         patch("publisher.app.mqtt_subscriber.MQTTSubscriber.stop", lambda self: None):
        from fastapi.testclient import TestClient

        with TestClient(pm.app) as tc:
            tc.post("/platform/ingest", json={"dataset_id": "home/env/temperature", "value": 1})
            res = tc.get("/platform/ingest")
    assert res.status_code == 200
    assert res.json() == [{"dataset_id": "home/env/temperature", "value": 1}]
