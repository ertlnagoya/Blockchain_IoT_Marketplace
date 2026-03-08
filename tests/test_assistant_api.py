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
    assert body["execution"]["planner_diagnostics"]["used_fallback"] is False


def test_assistant_plan_returns_planner_diagnostics() -> None:
    client = TestClient(app)

    response = client.post(
        "/assistant/plan",
        json={
            "request_text": "公園北側でポイ捨てが増えていたら教えて。必要なら照明をつけて管理者に通知して。"
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert "planner_diagnostics" in body
    assert body["planner_diagnostics"]["planner_mode"] in {"rule_based", "llm"}
    assert body["planner_diagnostics"]["status"] in {"ok", "fallback"}
    assert body["planner_diagnostics"]["severity"] in {"info", "warning", "error"}
    assert body["planner_diagnostics"]["label"] in {"OK", "Fallback", "Ready"}
    assert body["planner_diagnostics"]["color_hint"] in {"green", "amber", "red"}
    assert body["planner_diagnostics"]["category"] in {"planner", "provider", "validation", "success"}
    assert isinstance(body["planner_diagnostics"]["code"], str)
    assert isinstance(body["planner_diagnostics"]["user_message"], str)
    assert "summary" in body["planner_diagnostics"]
    assert "suggestion" in body["planner_diagnostics"]
