from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib import request


DEFAULT_REQUEST_TEXT = "公園北側でポイ捨てや危険行動が増えていたら教えて。必要なら照明をつけて管理者に通知して。"


def fetch_json(url: str) -> Any:
    with request.urlopen(url, timeout=10) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, body: dict[str, Any]) -> Any:
    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=15) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def ingest_records_to_observed_events(ingested: list[dict[str, Any]], target_area: str | None = None) -> list[dict[str, Any]]:
    observed_events: list[dict[str, Any]] = []
    for envelope in ingested:
        dataset_id = envelope.get("dataset_id", "")
        if not dataset_id.startswith("home/event/"):
            continue

        normalized = envelope.get("payload", {})
        event_payload = normalized.get("payload", {})
        event_type = event_payload.get("event_type")
        event_data = event_payload.get("data", {})
        location = event_data.get("location", "unknown")
        if target_area and location != target_area:
            continue

        observed_events.append(
            {
                "event_type": event_type,
                "location": location,
                "ts": normalized.get("ts"),
                "severity": event_data.get("severity", "medium"),
                "data": event_data,
            }
        )
    return observed_events


def build_execute_request(
    ingested: list[dict[str, Any]],
    request_text: str,
    target_area: str | None = None,
) -> dict[str, Any]:
    return {
        "request_text": request_text,
        "observed_events": ingest_records_to_observed_events(ingested, target_area=target_area),
    }


def build_plan_request(request_text: str) -> dict[str, Any]:
    return {"request_text": request_text}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and optionally send Phase 3 plan/execute requests from publisher ingest records.")
    parser.add_argument("--publisher-url", default="http://localhost:8080", help="Base URL of the publisher service.")
    parser.add_argument("--assistant-url", default="http://localhost:8090", help="Base URL of the assistant service.")
    parser.add_argument("--request-file", default="", help="Optional JSON file containing request_text.")
    parser.add_argument("--request-text", default=DEFAULT_REQUEST_TEXT, help="Fallback request text.")
    parser.add_argument("--target-area", default="park-north", help="Only include events from this area. Use empty string to disable.")
    parser.add_argument("--print-only", action="store_true", help="Print the request JSON without posting it to the assistant.")
    parser.add_argument("--plan-only", action="store_true", help="Send POST /assistant/plan instead of POST /assistant/execute.")
    args = parser.parse_args()

    request_text = args.request_text
    if args.request_file:
        payload = json.loads(Path(args.request_file).read_text(encoding="utf-8"))
        request_text = payload["request_text"]

    ingested = fetch_json(f"{args.publisher_url.rstrip('/')}/platform/ingest")
    execute_request = build_execute_request(
        ingested,
        request_text=request_text,
        target_area=args.target_area or None,
    )
    plan_request = build_plan_request(request_text)

    if args.print_only:
        body = plan_request if args.plan_only else execute_request
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return

    endpoint = "/assistant/plan" if args.plan_only else "/assistant/execute"
    body = plan_request if args.plan_only else execute_request
    result = post_json(f"{args.assistant_url.rstrip('/')}{endpoint}", body)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
