from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sample_events_path: str = "examples/phase3_events_park_safety.json"
    planner_mode: str = "rule_based"
    planner_name: str = "rule-based-planner-v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    llm_provider: str = "stub"
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(env_prefix="ASSISTANT_", extra="ignore")
