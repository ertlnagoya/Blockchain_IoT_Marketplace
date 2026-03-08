from __future__ import annotations

from fastapi.testclient import TestClient

from examples.phase3_llm_mock_server import app


def test_mock_server_health() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "llm-mock-server"}


def test_mock_server_returns_openai_compatible_response() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-model",
            "messages": [
                {"role": "system", "content": "Return JSON only."},
                {
                    "role": "user",
                    "content": "If suspicious activity increases near the station front, show a warning and notify the manager.",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"]
    assert "station-front" in body["choices"][0]["message"]["content"]
