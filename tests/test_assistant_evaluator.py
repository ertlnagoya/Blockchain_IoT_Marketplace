from datetime import datetime

from assistant.app.evaluator import EventEvaluator
from assistant.app.models import EventRecord
from assistant.app.planner import RequestPlanner


def test_evaluator_triggers_when_threshold_is_met() -> None:
    planner = RequestPlanner("rule-based-planner-v1")
    plan = planner.plan("公園北側でポイ捨てが増えていたら照明をつけて通知して。")

    events = [
        EventRecord(
            event_type="possible_littering",
            location="park-north",
            ts=datetime.fromisoformat("2026-03-08T11:00:00+00:00"),
            severity="medium",
            data={},
        ),
        EventRecord(
            event_type="possible_littering",
            location="park-north",
            ts=datetime.fromisoformat("2026-03-08T11:05:00+00:00"),
            severity="medium",
            data={},
        ),
        EventRecord(
            event_type="possible_littering",
            location="park-north",
            ts=datetime.fromisoformat("2026-03-08T11:10:00+00:00"),
            severity="high",
            data={},
        ),
    ]

    evaluator = EventEvaluator()
    result = evaluator.evaluate(plan, events, now=datetime.fromisoformat("2026-03-08T11:20:00+00:00"))

    assert result.triggered is True
    assert result.matched_counts["possible_littering"] == 3
