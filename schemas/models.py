from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


SCHEMA_VERSION = "1.0"


class StateInput(BaseModel):
    entity_id: str
    state: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    ts: datetime
    source: str = "home_assistant"


class EventInput(BaseModel):
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    ts: datetime
    source: str = "edge_inference"


class NormalizedMessage(BaseModel):
    dataset_id: str
    schema_version: str = SCHEMA_VERSION
    message_type: Literal["state", "event"]
    source: str
    ts: datetime
    payload: dict[str, Any]


def _dataset_from_state(topic: str, state: StateInput) -> str:
    tail = topic.split("/")[-1]
    if tail == "temperature":
        return "home/env/temperature"
    if tail == "power":
        return "home/energy/power"

    entity = state.entity_id.lower()
    if "temperature" in entity:
        return "home/env/temperature"
    if "power" in entity:
        return "home/energy/power"

    return f"home/state/{tail}"


def _dataset_from_event(event: EventInput) -> str:
    name = event.event_type.strip().lower().replace(" ", "_")
    if name == "person_detected":
        return "home/event/person_detected"
    return f"home/event/{name}"


def normalize(topic: str, payload: dict[str, Any]) -> NormalizedMessage:
    if topic.startswith("homeassistant/state/"):
        state = StateInput.model_validate(payload)
        return NormalizedMessage(
            dataset_id=_dataset_from_state(topic, state),
            message_type="state",
            source=state.source,
            ts=state.ts.astimezone(timezone.utc),
            payload=state.model_dump(mode="json"),
        )

    if topic.startswith("homeassistant/event/"):
        event = EventInput.model_validate(payload)
        return NormalizedMessage(
            dataset_id=_dataset_from_event(event),
            message_type="event",
            source=event.source,
            ts=event.ts.astimezone(timezone.utc),
            payload=event.model_dump(mode="json"),
        )

    raise ValueError(f"Unsupported topic: {topic}")
