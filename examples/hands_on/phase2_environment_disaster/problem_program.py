#!/usr/bin/env python3
"""Exercise program for the Phase 2 environment/disaster event-sharing hands-on."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import request


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_EVENT_FILE = BASE_DIR / "payload_flood_risk_high.json"
SIMULATE_PUBLISH_PATH = "/simulate/publish"


def load_event_payload(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_publish_request(payload: dict, purpose: str) -> dict:
    # TODO 1:
    # Return the request body expected by POST /simulate/publish.
    #
    # It must include:
    # - topic: "homeassistant/event/flood_risk_high"
    # - payload: the loaded JSON event
    # - purpose: the function argument
    #
    # Example output:
    # {
    #   "topic": "homeassistant/event/flood_risk_high",
    #   "payload": {...},
    #   "purpose": "disaster_response"
    # }
    raise NotImplementedError("TODO: implement build_publish_request()")


def post_json(base_url: str, path: str, body: dict) -> dict:
    payload = json.dumps(body).encode("utf-8")
    req = request.Request(
        base_url.rstrip("/") + path,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as resp:  # noqa: S310 - local training endpoint
        return json.load(resp)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 2 hands-on exercise: send flood_risk_high to the Publisher."
    )
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--purpose", default="disaster_response")
    parser.add_argument("--event-file", type=Path, default=DEFAULT_EVENT_FILE)
    args = parser.parse_args()

    event_payload = load_event_payload(args.event_file)
    request_body = build_publish_request(event_payload, args.purpose)
    result = post_json(args.base_url, SIMULATE_PUBLISH_PATH, request_body)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
