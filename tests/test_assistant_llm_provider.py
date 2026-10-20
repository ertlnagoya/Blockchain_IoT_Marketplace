import json

import httpx
import pytest

from assistant.app.llm_prompt import build_system_prompt, build_user_prompt
from assistant.app.llm_planner import LLMPlanner
from assistant.app.llm_provider import (
    LLMProviderError,
    OpenAICompatibleLLMProvider,
    StubLLMProvider,
)


def test_stub_provider_returns_expected_shape() -> None:
    provider = StubLLMProvider()

    plan = provider.generate_json(
        build_system_prompt(),
        build_user_prompt("公園北側でポイ捨てが増えていたら照明をつけて管理者に通知して。"),
    )

    assert plan["target_area"] == "park-north"
    assert "possible_littering" in plan["watch_events"]
    assert any(action["action_type"] == "light_on" for action in plan["actions"])


def test_stub_provider_understands_station_front() -> None:
    provider = StubLLMProvider()

    plan = provider.generate_json(
        build_system_prompt(),
        build_user_prompt("If suspicious activity increases near the station front, show a warning and notify the manager."),
    )

    assert plan["target_area"] == "station-front"
    assert "suspicious_activity" in plan["watch_events"]
    assert any(action["action_type"] == "show_warning" for action in plan["actions"])


def test_openai_compatible_provider_parses_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "test-model"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "intent": "monitor_public_safety",
                                    "target_area": "park-north",
                                    "time_window_minutes": 30,
                                    "watch_events": ["possible_littering"],
                                    "thresholds": {"possible_littering": 3},
                                    "actions": [
                                        {
                                            "action_type": "send_notification",
                                            "target": "park-north-manager",
                                            "parameters": {"channel": "mobile_push"},
                                        }
                                    ],
                                }
                            )
                        }
                    }
                ]
            },
        )

    provider = OpenAICompatibleLLMProvider(
        api_base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    plan = provider.generate_json(
        build_system_prompt(),
        build_user_prompt("Notify me if littering increases in park north."),
    )

    assert plan["target_area"] == "park-north"
    assert plan["watch_events"] == ["possible_littering"]


def _provider_with(handler) -> OpenAICompatibleLLMProvider:
    return OpenAICompatibleLLMProvider(
        api_base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_openai_compatible_provider_wraps_http_status_error() -> None:
    provider = _provider_with(lambda request: httpx.Response(401, json={"error": "bad key"}))

    with pytest.raises(LLMProviderError, match="HTTP 401"):
        provider.generate_json(build_system_prompt(), build_user_prompt("park north"))


def test_openai_compatible_provider_wraps_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _provider_with(handler)

    with pytest.raises(LLMProviderError, match="could not reach LLM API"):
        provider.generate_json(build_system_prompt(), build_user_prompt("park north"))


def test_llm_planner_falls_back_on_http_error() -> None:
    planner = LLMPlanner(
        planner_name="llm-planner-openai-compatible-v1",
        provider=_provider_with(lambda request: httpx.Response(404, text="not found")),
    )

    plan = planner.plan("公園北側でポイ捨てが増えていたら照明をつけて通知して。")
    diagnostics = planner.get_last_diagnostics()

    assert plan.planner_name == "rule-based-fallback-v1"
    assert diagnostics.used_fallback is True
    assert diagnostics.code == "llm_provider_error"
    assert diagnostics.error_type == "LLMProviderError"
    assert diagnostics.error_message == "LLM API returned HTTP 404"
