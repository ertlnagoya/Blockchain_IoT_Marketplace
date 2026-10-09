from __future__ import annotations

import json

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="IW3IP LLM Mock Server", version="0.1.0")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    temperature: float | int | None = None
    response_format: dict | None = None
    messages: list[ChatMessage]


def _extract_request_text(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def _build_plan(request_text: str) -> dict:
    text = request_text.lower()

    if "公園北側" in request_text or "park north" in text or "north side of the park" in text:
        target_area = "park-north"
    elif "公園南側" in request_text or "park south" in text or "south side of the park" in text:
        target_area = "park-south"
    elif "駅前" in request_text or "station front" in text:
        target_area = "station-front"
    else:
        target_area = "unknown-area"

    watch_events: list[str] = []
    thresholds: dict[str, int] = {}
    actions: list[dict] = []

    if "ポイ捨て" in request_text or "litter" in text:
        watch_events.append("possible_littering")
        thresholds["possible_littering"] = 3
    if "危険行動" in request_text or "suspicious" in text:
        watch_events.append("suspicious_activity")
        thresholds["suspicious_activity"] = 1
    if not watch_events:
        watch_events.append("possible_littering")
        thresholds["possible_littering"] = 3

    if "照明" in request_text or "light" in text:
        actions.append(
            {
                "action_type": "light_on",
                "target": f"{target_area}-light-1",
                "parameters": {"brightness": 80},
            }
        )
    if "通知" in request_text or "notify" in text:
        actions.append(
            {
                "action_type": "send_notification",
                "target": f"{target_area}-manager",
                "parameters": {"channel": "mobile_push"},
            }
        )
    if "表示" in request_text or "warning" in text or "signage" in text:
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

    return {
        "intent": "monitor_public_safety",
        "target_area": target_area,
        "time_window_minutes": 30,
        "watch_events": watch_events,
        "thresholds": thresholds,
        "actions": actions,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-mock-server"}


@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest) -> dict:
    request_text = _extract_request_text(req.messages)
    plan = _build_plan(request_text)
    return {
        "id": "chatcmpl-mock-001",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(plan),
                },
                "finish_reason": "stop",
            }
        ],
    }
