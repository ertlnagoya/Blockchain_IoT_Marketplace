from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    request_text: str


class EventRecord(BaseModel):
    event_type: str
    location: str
    ts: datetime
    severity: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ActionCommand(BaseModel):
    action_type: Literal["light_on", "send_notification", "show_warning"]
    target: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    planner_name: str
    intent: str
    target_area: str
    time_window_minutes: int
    watch_events: list[str]
    thresholds: dict[str, int]
    actions: list[ActionCommand]
    original_request: str


class ExecuteRequest(BaseModel):
    request_text: str
    observed_events: list[EventRecord] | None = None


class EvaluationResult(BaseModel):
    triggered: bool
    matched_counts: dict[str, int]
    reason: str


class ExecutionRecord(BaseModel):
    execution_id: str
    created_at: datetime
    request_text: str
    plan: ExecutionPlan
    observed_events: list[EventRecord]
    evaluation: EvaluationResult
    actions_executed: list[ActionCommand]
