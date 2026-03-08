from __future__ import annotations

from assistant.app.llm_planner import LLMPlanner
from assistant.app.planner_interface import Planner
from assistant.app.rule_based_planner import RuleBasedPlanner


def create_planner(
    planner_mode: str,
    planner_name: str,
    llm_backend: str = "stub",
) -> Planner:
    if planner_mode == "rule_based":
        return RuleBasedPlanner(planner_name)
    if planner_mode == "llm":
        return LLMPlanner(planner_name=planner_name, backend=llm_backend)
    raise ValueError(f"unsupported planner_mode: {planner_mode}")
