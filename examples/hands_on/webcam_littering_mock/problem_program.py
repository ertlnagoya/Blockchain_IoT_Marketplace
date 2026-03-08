#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.hands_on.common import write_text


def build_event(camera_id: int) -> dict:
    # TODO 1:
    # Return a mock webcam event with:
    # - source: "usb_webcam"
    # - camera_id: function argument
    # - event_type: "possible_littering"
    # - object_class: "bottle"
    # - confidence: 0.87
    # - ts: current UTC ISO8601 string
    raise NotImplementedError("TODO: implement build_event()")


def build_output_path(output_dir: Path, camera_id: int) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return output_dir / f"{camera_id}_webcam_event_{timestamp}.txt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-id", type=int, default=401)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    event = build_event(args.camera_id)
    out = build_output_path(args.output_dir, args.camera_id)
    write_text(out, json.dumps(event, ensure_ascii=False, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
