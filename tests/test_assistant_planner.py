from assistant.app.planner import RequestPlanner
from assistant.app.planner_factory import create_planner


def test_planner_extracts_area_events_and_actions() -> None:
    planner = RequestPlanner("rule-based-planner-v1")
    plan = planner.plan("公園北側でポイ捨てや危険行動が増えていたら教えて。必要なら照明をつけて管理者に通知して。")

    assert plan.target_area == "park-north"
    assert "possible_littering" in plan.watch_events
    assert "suspicious_activity" in plan.watch_events
    assert any(action.action_type == "light_on" for action in plan.actions)
    assert any(action.action_type == "send_notification" for action in plan.actions)


def test_llm_planner_mode_returns_structured_plan() -> None:
    planner = create_planner(
        planner_mode="llm",
        planner_name="llm-planner-stub-v1",
        llm_backend="stub",
    )
    plan = planner.plan("公園北側でポイ捨てが増えていたら照明をつけて管理者に通知して。")

    assert plan.planner_name == "llm-planner-stub-v1"
    assert plan.target_area == "park-north"
    assert "possible_littering" in plan.watch_events
    assert any(action.action_type == "light_on" for action in plan.actions)


def test_unknown_planner_mode_is_rejected() -> None:
    try:
        create_planner(planner_mode="unknown", planner_name="broken")
    except ValueError as exc:
        assert "unsupported planner_mode" in str(exc)
    else:
        raise AssertionError("expected ValueError")
