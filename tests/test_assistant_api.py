from fastapi.testclient import TestClient

from assistant.app.main import app


def test_assistant_execute_runs_actions() -> None:
    client = TestClient(app)

    response = client.post(
        "/assistant/execute",
        json={
            "request_text": "公園北側でポイ捨てが増えていたら教えて。必要なら照明をつけて管理者に通知して。"
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "executed"
    assert body["execution"]["evaluation"]["triggered"] is True
    assert len(body["execution"]["actions_executed"]) >= 1
