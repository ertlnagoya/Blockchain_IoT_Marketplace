from __future__ import annotations

import importlib
import os


DEFAULT_MODULE = "examples.hands_on.phase3_llm_planner.answer_program"


def _load_module():
    module_name = os.environ.get("PHASE3_LLM_HANDS_ON_MODULE", DEFAULT_MODULE)
    return importlib.import_module(module_name)


def test_build_plan_request_shape() -> None:
    module = _load_module()
    body = module.build_plan_request({"request_text": "test request"})

    assert body == {"request_text": "test request"}


def test_summarize_plan_shape() -> None:
    module = _load_module()
    summary = module.summarize_plan(
        {
            "plan": {
                "planner_name": "llm-planner-stub-v1",
                "target_area": "station-front",
                "watch_events": ["suspicious_activity"],
                "actions": [
                    {"action_type": "send_notification"},
                    {"action_type": "show_warning"},
                ],
            },
            "planner_diagnostics": {
                "label": "OK",
                "color_hint": "green",
                "code": "llm_plan_generated",
                "category": "success",
                "user_message": "LLM planner generated a plan successfully.",
            },
        }
    )

    assert summary == {
        "planner_name": "llm-planner-stub-v1",
        "target_area": "station-front",
        "watch_events": ["suspicious_activity"],
        "actions": ["send_notification", "show_warning"],
        "planner_diagnostics": {
            "label": "OK",
            "color_hint": "green",
            "code": "llm_plan_generated",
            "category": "success",
            "user_message": "LLM planner generated a plan successfully.",
        },
    }
