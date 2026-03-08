from __future__ import annotations

import json

from pydantic import ValidationError

from assistant.app.models import ActionCommand, ExecutionPlan
from assistant.app.plan_validator import PlanValidationError, validate_plan
from assistant.app.rule_based_planner import RuleBasedPlanner


class LLMPlanner:
    """
    Minimal LLM-style planner.

    The default implementation stays self-contained for local testing:
    it produces structured JSON via a stub backend, validates the result,
    and falls back to the rule-based planner when validation fails.
    """

    def __init__(
        self,
        planner_name: str,
        backend: str = "stub",
        fallback_planner: RuleBasedPlanner | None = None,
    ) -> None:
        self.planner_name = planner_name
        self.backend = backend
        self.fallback_planner = fallback_planner or RuleBasedPlanner("rule-based-fallback-v1")

    def plan(self, request_text: str) -> ExecutionPlan:
        try:
            payload = self._generate_structured_payload(request_text)
            plan = ExecutionPlan.model_validate(
                {
                    "planner_name": self.planner_name,
                    "original_request": request_text,
                    **payload,
                }
            )
            return validate_plan(plan)
        except (json.JSONDecodeError, ValidationError, PlanValidationError, ValueError):
            return self.fallback_planner.plan(request_text)

    def _generate_structured_payload(self, request_text: str) -> dict:
        if self.backend != "stub":
            raise ValueError(f"unsupported llm backend: {self.backend}")

        text = request_text.lower()
        target_area = "park-north" if ("公園北側" in request_text or "park north" in text or "north side of the park" in text) else "unknown-area"

        watch_events: list[str] = []
        thresholds: dict[str, int] = {}
        actions: list[dict] = []

        if "ポイ捨て" in request_text or "litter" in text:
            watch_events.append("possible_littering")
            thresholds["possible_littering"] = 3
        if "危険行動" in request_text or "suspicious" in text:
            watch_events.append("suspicious_activity")
            thresholds["suspicious_activity"] = 1
        if not watch_events:
            watch_events.append("possible_littering")
            thresholds["possible_littering"] = 3

        if "照明" in request_text or "light" in text:
            actions.append(
                ActionCommand(
                    action_type="light_on",
                    target=f"{target_area}-light-1",
                    parameters={"brightness": 80},
                ).model_dump(mode="json")
            )
        if "通知" in request_text or "notify" in text:
            actions.append(
                ActionCommand(
                    action_type="send_notification",
                    target=f"{target_area}-manager",
                    parameters={"channel": "mobile_push"},
                ).model_dump(mode="json")
            )
        if "表示" in request_text or "warning" in text or "signage" in text:
            actions.append(
                ActionCommand(
                    action_type="show_warning",
                    target=f"{target_area}-signage",
                    parameters={"message": "Safety alert"},
                ).model_dump(mode="json")
            )
        if not actions:
            actions.append(
                ActionCommand(
                    action_type="send_notification",
                    target=f"{target_area}-manager",
                    parameters={"channel": "mobile_push"},
                ).model_dump(mode="json")
            )

        response_text = json.dumps(
            {
                "intent": "monitor_public_safety",
                "target_area": target_area,
                "time_window_minutes": 30,
                "watch_events": watch_events,
                "thresholds": thresholds,
                "actions": actions,
            }
        )
        return json.loads(response_text)
