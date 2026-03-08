import json

import httpx

from assistant.app.llm_prompt import build_system_prompt, build_user_prompt
from assistant.app.llm_provider import OpenAICompatibleLLMProvider, StubLLMProvider


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
