from assistant.app.llm_planner import LLMPlanner
from assistant.app.plan_validator import PlanValidationError, validate_plan


def test_llm_planner_falls_back_when_backend_is_unsupported() -> None:
    planner = LLMPlanner(
        planner_name="llm-planner-stub-v1",
        backend="unsupported",
    )

    plan = planner.plan("公園北側でポイ捨てが増えていたら照明をつけて通知して。")

    assert plan.planner_name == "rule-based-fallback-v1"
    assert plan.target_area == "park-north"


def test_validator_rejects_unsupported_event() -> None:
    plan = LLMPlanner("llm-planner-stub-v1").plan("公園北側でポイ捨てを監視して。")
    broken = plan.model_copy(update={"watch_events": ["made_up_event"]})

    try:
        validate_plan(broken)
    except PlanValidationError as exc:
        assert "unsupported watch_events" in str(exc)
    else:
        raise AssertionError("expected PlanValidationError")
