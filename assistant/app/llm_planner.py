from __future__ import annotations

from pydantic import ValidationError

from assistant.app.llm_prompt import build_system_prompt, build_user_prompt
from assistant.app.llm_provider import LLMProvider, LLMProviderError
from assistant.app.models import ExecutionPlan, PlannerDiagnostics
from assistant.app.plan_validator import PlanValidationError, validate_plan
from assistant.app.rule_based_planner import RuleBasedPlanner


class LLMPlanner:
    """
    Minimal LLM-style planner.

    The default implementation stays self-contained for local testing:
    it produces structured JSON via a stub backend, validates the result,
    and falls back to the rule-based planner when validation fails.
    """

    def __init__(
        self,
        planner_name: str,
        provider: LLMProvider,
        fallback_planner: RuleBasedPlanner | None = None,
    ) -> None:
        self.planner_name = planner_name
        self.provider = provider
        self.fallback_planner = fallback_planner or RuleBasedPlanner("rule-based-fallback-v1")
        self.system_prompt = build_system_prompt()
        self._last_diagnostics = PlannerDiagnostics(
            status="ok",
            severity="info",
            planner_mode="llm",
            planner_name=self.planner_name,
            provider_name=self.provider.provider_name,
            summary="LLM planner is ready.",
            suggestion="Call /assistant/plan with a request to generate a structured plan.",
        )

    def plan(self, request_text: str) -> ExecutionPlan:
        provider_name = getattr(self.provider, "provider_name", "unknown")
        try:
            self._last_diagnostics = PlannerDiagnostics(
                status="ok",
                severity="info",
                planner_mode="llm",
                planner_name=self.planner_name,
                provider_name=provider_name,
                used_fallback=False,
                summary="LLM response was accepted and converted into an execution plan.",
                suggestion="Continue with /assistant/execute or inspect the generated plan.",
            )
            payload = self.provider.generate_json(
                system_prompt=self.system_prompt,
                user_prompt=build_user_prompt(request_text),
            )
            plan = ExecutionPlan.model_validate(
                {
                    "planner_name": self.planner_name,
                    "original_request": request_text,
                    **payload,
                }
            )
            return validate_plan(plan)
        except (ValidationError, PlanValidationError, LLMProviderError, ValueError) as exc:
            self._last_diagnostics = PlannerDiagnostics(
                status="fallback",
                severity="warning",
                planner_mode="llm",
                planner_name=self.planner_name,
                provider_name=provider_name,
                used_fallback=True,
                summary="LLM response could not be used, so the rule-based fallback planner generated the plan.",
                suggestion="Check error_type, error_message, API credentials, and whether the model returned valid JSON.",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return self.fallback_planner.plan(request_text)

    def get_last_diagnostics(self) -> PlannerDiagnostics:
        return self._last_diagnostics
