from __future__ import annotations

import json
from typing import Protocol

import httpx


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(Protocol):
    provider_name: str

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        ...


class StubLLMProvider:
    provider_name = "stub"

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        request_text = user_prompt.lower()
        if "公園北側" in user_prompt or "park north" in request_text or "north side of the park" in request_text:
            target_area = "park-north"
        elif "公園南側" in user_prompt or "park south" in request_text or "south side of the park" in request_text:
            target_area = "park-south"
        elif "駅前" in user_prompt or "station front" in request_text:
            target_area = "station-front"
        else:
            target_area = "unknown-area"

        watch_events: list[str] = []
        thresholds: dict[str, int] = {}
        actions: list[dict] = []

        if "ポイ捨て" in user_prompt or "litter" in request_text:
            watch_events.append("possible_littering")
            thresholds["possible_littering"] = 3
        if "危険行動" in user_prompt or "suspicious" in request_text:
            watch_events.append("suspicious_activity")
            thresholds["suspicious_activity"] = 1
        if not watch_events:
            watch_events.append("possible_littering")
            thresholds["possible_littering"] = 3

        if "照明" in user_prompt or "light" in request_text:
            actions.append(
                {
                    "action_type": "light_on",
                    "target": f"{target_area}-light-1",
                    "parameters": {"brightness": 80},
                }
            )
        if "通知" in user_prompt or "notify" in request_text:
            actions.append(
                {
                    "action_type": "send_notification",
                    "target": f"{target_area}-manager",
                    "parameters": {"channel": "mobile_push"},
                }
            )
        if "表示" in user_prompt or "warning" in request_text or "signage" in request_text:
            actions.append(
                {
                    "action_type": "show_warning",
                    "target": f"{target_area}-signage",
                    "parameters": {"message": "Safety alert"},
                }
            )
        if not actions:
            actions.append(
                {
                    "action_type": "send_notification",
                    "target": f"{target_area}-manager",
                    "parameters": {"channel": "mobile_push"},
                }
            )

        response_text = json.dumps(
            {
                "intent": "monitor_public_safety",
                "target_area": target_area,
                "time_window_minutes": 30,
                "watch_events": watch_events,
                "thresholds": thresholds,
                "actions": actions,
            }
        )
        return json.loads(response_text)


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.provider_name = "openai_compatible"
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        if not self.api_base_url:
            raise LLMProviderError("missing api_base_url")
        if not self.api_key:
            raise LLMProviderError("missing api_key")
        if not self.model:
            raise LLMProviderError("missing model")

        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if self.http_client is not None:
            response = self.http_client.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
        else:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

        response.raise_for_status()
        body = response.json()

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("invalid chat completion response format") from exc

        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )
        if not isinstance(content, str):
            raise LLMProviderError("chat completion content is not a string")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMProviderError("model response is not valid JSON") from exc


def create_llm_provider(
    provider_name: str,
    *,
    api_base_url: str,
    api_key: str,
    model: str,
    timeout_seconds: float,
) -> LLMProvider:
    if provider_name == "stub":
        return StubLLMProvider()
    if provider_name == "openai_compatible":
        return OpenAICompatibleLLMProvider(
            api_base_url=api_base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    raise LLMProviderError(f"unsupported llm provider: {provider_name}")
