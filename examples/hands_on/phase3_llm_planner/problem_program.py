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
DEFAULT_REQUEST_FILE = BASE_DIR / "phase3_request_park_safety.json"


def build_plan_request(request_body: dict) -> dict:
    # TODO 1:
    # Return the request body for POST /assistant/plan.
    #
    # Required:
    # {
    #   "request_text": request_body["request_text"]
    # }
    raise NotImplementedError("TODO: implement build_plan_request()")


def summarize_plan(response: dict) -> dict:
    # TODO 2:
    # Return a short summary dictionary with:
    # - planner_name
    # - target_area
    # - watch_events
    # - actions (list of action_type)
    # - planner_diagnostics:
    #   - label
    #   - color_hint
    raise NotImplementedError("TODO: implement summarize_plan()")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8090")
    parser.add_argument("--request-file", type=Path, default=DEFAULT_REQUEST_FILE)
    args = parser.parse_args()

    request_body = load_json(args.request_file)
    result = post_json(args.base_url, "/assistant/plan", build_plan_request(request_body))
    print(json.dumps(summarize_plan(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
