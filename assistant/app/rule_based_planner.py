from __future__ import annotations

from assistant.app.models import ActionCommand, ExecutionPlan, PlannerDiagnostics
from assistant.app.plan_validator import validate_plan


class RuleBasedPlanner:
    def __init__(self, planner_name: str) -> None:
        self.planner_name = planner_name
        self._last_diagnostics = PlannerDiagnostics(
            status="ok",
            planner_mode="rule_based",
            planner_name=self.planner_name,
            provider_name="rule_based",
            summary="Rule-based planner generated the execution plan.",
            suggestion="Use the generated plan as-is, or switch to llm mode to compare planner behavior.",
        )

    def plan(self, request_text: str) -> ExecutionPlan:
        self._last_diagnostics = PlannerDiagnostics(
            status="ok",
            planner_mode="rule_based",
            planner_name=self.planner_name,
            provider_name="rule_based",
            summary="Rule-based planner generated the execution plan.",
            suggestion="Use the generated plan as-is, or switch to llm mode to compare planner behavior.",
        )
        text = request_text.lower()

        if "公園北側" in request_text or "park north" in text or "north side of the park" in text:
            target_area = "park-north"
        elif "公園南側" in request_text or "park south" in text or "south side of the park" in text:
            target_area = "park-south"
        elif "駅前" in request_text or "station front" in text:
            target_area = "station-front"
        else:
            target_area = "unknown-area"

        watch_events: list[str] = []
        thresholds: dict[str, int] = {}

        if "ポイ捨て" in request_text or "litter" in text:
            watch_events.append("possible_littering")
            thresholds["possible_littering"] = 3

        if "危険行動" in request_text or "suspicious" in text:
            watch_events.append("suspicious_activity")
            thresholds["suspicious_activity"] = 1

        actions: list[ActionCommand] = []
        if "照明" in request_text or "light" in text:
            actions.append(
                ActionCommand(
                    action_type="light_on",
                    target=f"{target_area}-light-1",
                    parameters={"brightness": 80},
                )
            )
        if "通知" in request_text or "notify" in text:
            actions.append(
                ActionCommand(
                    action_type="send_notification",
                    target=f"{target_area}-manager",
                    parameters={"channel": "mobile_push"},
                )
            )
        if "表示" in request_text or "warning" in text or "signage" in text:
            actions.append(
                ActionCommand(
                    action_type="show_warning",
                    target=f"{target_area}-signage",
                    parameters={"message": "Safety alert"},
                )
            )

        if not watch_events:
            watch_events = ["possible_littering"]
            thresholds["possible_littering"] = 3

        if not actions:
            actions.append(
                ActionCommand(
                    action_type="send_notification",
                    target=f"{target_area}-manager",
                    parameters={"channel": "mobile_push"},
                )
            )

        return validate_plan(
            ExecutionPlan(
                planner_name=self.planner_name,
                intent="monitor_public_safety",
                target_area=target_area,
                time_window_minutes=30,
                watch_events=watch_events,
                thresholds=thresholds,
                actions=actions,
                original_request=request_text,
            )
        )

    def get_last_diagnostics(self) -> PlannerDiagnostics:
        return self._last_diagnostics
