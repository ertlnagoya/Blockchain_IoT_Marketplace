from __future__ import annotations

from assistant.app.llm_provider import create_llm_provider
from assistant.app.llm_planner import LLMPlanner
from assistant.app.planner_interface import Planner
from assistant.app.rule_based_planner import RuleBasedPlanner


def create_planner(
    planner_mode: str,
    planner_name: str,
    llm_provider: str = "stub",
    llm_api_base_url: str = "",
    llm_api_key: str = "",
    llm_model: str = "",
    llm_timeout_seconds: float = 20.0,
) -> Planner:
    if planner_mode == "rule_based":
        return RuleBasedPlanner(planner_name)
    if planner_mode == "llm":
        provider = create_llm_provider(
            provider_name=llm_provider,
            api_base_url=llm_api_base_url,
            api_key=llm_api_key,
            model=llm_model,
            timeout_seconds=llm_timeout_seconds,
        )
        return LLMPlanner(planner_name=planner_name, provider=provider)
    raise ValueError(f"unsupported planner_mode: {planner_mode}")
