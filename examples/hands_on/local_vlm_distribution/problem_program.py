#!/usr/bin/env python3
"""Exercise version of the "local VLM / semantic distribution" hands-on.

Fill in the two TODOs, then run it against a running publisher. See
README.md for the walkthrough and the expected output. The reference
solution is answer_program.py in the same directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.hands_on.common import (  # noqa: E402
    load_json,
    post_json,
    post_multipart,
    upload_media,
)

HERE = Path(__file__).resolve().parent


def analyze_frame(base_url: str, image_path: Path, source_device_id: str) -> dict:
    """Send one frame to /semantic/analyze and return the SIR JSON."""
    return post_multipart(
        base_url,
        "/semantic/analyze",
        image_path,
        fields={"source_device_id": source_device_id},
    )


def summarize_sir(sir: dict) -> str:
    # TODO 1:
    # Turn the SIR dict into a one-line human summary string. Read at
    # least: people count (sir["people"]["count"]), number of objects
    # (len(sir["objects"])), number of sensitive_regions, and the
    # scene_summary. Use .get(...) so a missing key does not crash.
    raise NotImplementedError("TODO 1: implement summarize_sir()")


def build_event(image_url: str, camera_id: str) -> dict:
    # TODO 2:
    # Return the event payload that carries the frame into the platform:
    # - event_type: "possible_littering"
    # - data: {"camera_id": camera_id, "object_class": "unknown",
    #          "confidence": 0.5}
    # - image_url: the argument (this links the uploaded media to the event)
    # - ts: current UTC ISO8601 string
    # - source: "local_vlm_distribution"
    raise NotImplementedError("TODO 2: implement build_event()")


def distribute_frame(
    base_url: str, image_path: Path, camera_id: str, purpose: str
) -> dict:
    consent = load_json(HERE / "fixtures" / "consent_webcam.json")
    post_json(base_url, "/consents", consent)
    upload = upload_media(base_url, image_path, content_type="image/jpeg")
    payload = build_event(upload["url"], camera_id)
    body = {
        "topic": "homeassistant/event/possible_littering",
        "payload": payload,
        "purpose": purpose,
    }
    return post_json(base_url, "/simulate/publish", body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--image", type=Path, required=True, help="JPEG/PNG frame")
    parser.add_argument("--source-device-id", default="laptop-webcam-01")
    parser.add_argument("--camera-id", default="webcam-401")
    parser.add_argument("--purpose", default="community_cleaning")
    parser.add_argument("--distribute", action="store_true")
    args = parser.parse_args()

    sir = analyze_frame(args.base_url, args.image, args.source_device_id)
    print("[analyze] SIR:")
    print(json.dumps(sir, ensure_ascii=False, indent=2))
    print("[summary]", summarize_sir(sir))

    if args.distribute:
        result = distribute_frame(
            args.base_url, args.image, args.camera_id, args.purpose
        )
        print("[distribute]", json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
