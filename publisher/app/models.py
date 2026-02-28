from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SimulatePublishRequest(BaseModel):
    topic: str
    payload: dict[str, Any]
    purpose: str | None = None
