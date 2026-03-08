from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI

from assistant.app.actuator import ActionActuator
from assistant.app.config import Settings
from assistant.app.evaluator import EventEvaluator
from assistant.app.models import EventRecord, ExecuteRequest, ExecutionRecord, PlanRequest
from assistant.app.planner_factory import create_planner
from assistant.app.store import ExecutionStore


settings = Settings()
planner = create_planner(
    planner_mode=settings.planner_mode,
    planner_name=settings.planner_name,
    llm_backend=settings.llm_backend,
)
evaluator = EventEvaluator()
actuator = ActionActuator()
store = ExecutionStore()

app = FastAPI(title="IW3IP Regional Safety Assistant", version="0.1.0")


def _load_sample_events() -> list[EventRecord]:
    path = Path(settings.sample_events_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [EventRecord.model_validate(item) for item in raw]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "assistant"}


@app.post("/assistant/plan")
def create_plan(req: PlanRequest) -> dict:
    plan = planner.plan(req.request_text)
    return {"status": "planned", "plan": plan.model_dump(mode="json")}


@app.post("/assistant/execute")
def execute(req: ExecuteRequest) -> dict:
    plan = planner.plan(req.request_text)
    events = req.observed_events or _load_sample_events()
    evaluation = evaluator.evaluate(plan, events)
    actions_executed = actuator.execute(plan.actions) if evaluation.triggered else []

    record = ExecutionRecord(
        execution_id=f"exec-{uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
        request_text=req.request_text,
        plan=plan,
        observed_events=events,
        evaluation=evaluation,
        actions_executed=actions_executed,
    )
    store.add(record)

    return {
        "status": "executed",
        "execution": record.model_dump(mode="json"),
    }


@app.get("/assistant/executions")
def list_executions() -> list[dict]:
    return [record.model_dump(mode="json") for record in store.list()]
