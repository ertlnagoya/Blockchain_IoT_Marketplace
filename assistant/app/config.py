from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sample_events_path: str = "examples/phase3_events_park_safety.json"
    planner_name: str = "rule-based-planner-v1"

    model_config = SettingsConfigDict(env_prefix="ASSISTANT_", extra="ignore")
