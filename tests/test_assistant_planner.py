from assistant.app.planner import RequestPlanner


def test_planner_extracts_area_events_and_actions() -> None:
    planner = RequestPlanner("rule-based-planner-v1")
    plan = planner.plan("公園北側でポイ捨てや危険行動が増えていたら教えて。必要なら照明をつけて管理者に通知して。")

    assert plan.target_area == "park-north"
    assert "possible_littering" in plan.watch_events
    assert "suspicious_activity" in plan.watch_events
    assert any(action.action_type == "light_on" for action in plan.actions)
    assert any(action.action_type == "send_notification" for action in plan.actions)
