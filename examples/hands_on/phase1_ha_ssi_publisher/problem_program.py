#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.hands_on.common import load_json, post_json


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_EVENT_FILE = BASE_DIR / "payload_temperature.json"


def build_publish_request(payload: dict, purpose: str) -> dict:
    # TODO 1:
    # Return the body for /simulate/publish with:
    # - topic: "homeassistant/state/sensor/temperature"
    # - payload: loaded JSON
    # - purpose: function argument
    raise NotImplementedError("TODO: implement build_publish_request()")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--purpose", default="research")
    parser.add_argument("--event-file", type=Path, default=DEFAULT_EVENT_FILE)
    args = parser.parse_args()

    payload = load_json(args.event_file)
    body = build_publish_request(payload, args.purpose)
    result = post_json(args.base_url, "/simulate/publish", body)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
