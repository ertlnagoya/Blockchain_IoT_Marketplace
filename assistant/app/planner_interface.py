from __future__ import annotations

from typing import Protocol

from assistant.app.models import ExecutionPlan


class Planner(Protocol):
    planner_name: str

    def plan(self, request_text: str) -> ExecutionPlan:
        ...
