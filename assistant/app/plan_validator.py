from __future__ import annotations

from assistant.app.models import ExecutionPlan


ALLOWED_EVENTS = {
    "possible_littering",
    "suspicious_activity",
    "person_detected",
}
ALLOWED_ACTIONS = {
    "light_on",
    "send_notification",
    "show_warning",
}
ALLOWED_AREAS = {
    "park-north",
    "park-south",
    "station-front",
    "unknown-area",
}


class PlanValidationError(ValueError):
    pass


def validate_plan(plan: ExecutionPlan) -> ExecutionPlan:
    if plan.target_area not in ALLOWED_AREAS:
        raise PlanValidationError(f"unsupported target_area: {plan.target_area}")

    invalid_events = [event for event in plan.watch_events if event not in ALLOWED_EVENTS]
    if invalid_events:
        raise PlanValidationError(f"unsupported watch_events: {invalid_events}")

    invalid_actions = [action.action_type for action in plan.actions if action.action_type not in ALLOWED_ACTIONS]
    if invalid_actions:
        raise PlanValidationError(f"unsupported actions: {invalid_actions}")

    return plan
