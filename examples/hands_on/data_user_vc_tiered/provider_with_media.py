#!/usr/bin/env python3
"""Stage T (case B) — provider-side script that drives the full
"event + image + video → tier-aware /platform/data" loop.

Steps it runs end-to-end:

  1. Generate a small JPEG and a small MP4 fixture (or take user-supplied
     paths) and POST them to ``/media/upload``. The publisher dedupes on
     sha256, so repeat runs are cheap.
  2. Build a `possible_littering` event payload that carries
     ``image_url`` / ``video_url`` / ``video_duration_sec`` at the top
     level **and** under ``data:`` (the pipeline hoists either form,
     this just shows both work).
  3. POST the payload to ``/simulate/publish`` so it runs through the
     same Consent VC pipeline the Phase 2 hands-on use.

The receiver side (Tier 3 / 2 / 1 wallets) is unchanged — they simply
get ``image_url`` / ``video_url`` keys at ``/platform/data`` according
to their tier projection, and can dereference the URL directly with the
buyer's browser / wallet.
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

from examples.hands_on.common import post_json, upload_media


# Smallest legal JPEG (1×1 white pixel, 125 bytes).
_TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605"
    "08070707090908090a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a"
    "0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0affc0000b08"
    "00010001010100ffc4001500010100000000000000000000000000000007ff"
    "c4001f10000103030301010100000000000000010002030405060708ffd900"
)


def _ensure_fixture(path: Path, blob: bytes) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--purpose", default="community_cleaning")
    parser.add_argument(
        "--image",
        type=Path,
        help="JPEG/PNG to upload as the `image_url`. Defaults to a 1×1 fixture.",
    )
    parser.add_argument(
        "--video",
        type=Path,
        help="MP4 to upload as the `video_url`. Defaults to the 1×1 JPEG bytes "
        "tagged as video/mp4 — fine for tier-projection demos, replace with a "
        "real clip for a production-flavoured run.",
    )
    parser.add_argument("--video-duration-sec", type=int, default=12)
    parser.add_argument("--camera-id", default="webcam-401")
    args = parser.parse_args()

    # 1) Resolve / generate fixtures.
    image_path = args.image or _ensure_fixture(
        REPO_ROOT
        / "examples"
        / "hands_on"
        / "data_user_vc_tiered"
        / "fixtures"
        / "stage_t_demo.jpg",
        _TINY_JPEG,
    )
    # For demos that don't have a real video clip, reuse the JPEG bytes
    # behind a video/* extension so the upload codepath exercises both
    # branches. The Tier projection only cares about the URL keys.
    video_path = args.video or _ensure_fixture(
        REPO_ROOT
        / "examples"
        / "hands_on"
        / "data_user_vc_tiered"
        / "fixtures"
        / "stage_t_demo.mp4",
        _TINY_JPEG,
    )

    # 2) Upload both blobs to /media/upload.
    img_resp = upload_media(args.base_url, image_path, content_type="image/jpeg")
    vid_resp = upload_media(args.base_url, video_path, content_type="video/mp4")
    print("[upload]", json.dumps({"image": img_resp, "video": vid_resp}, indent=2))

    # 3) Build the event payload. The pipeline hoists either form.
    payload = {
        "event_type": "possible_littering",
        "data": {
            "camera_id": args.camera_id,
            "object_class": "bottle",
            "confidence": 0.87,
        },
        "image_url": img_resp["url"],
        "video_url": vid_resp["url"],
        "video_duration_sec": args.video_duration_sec,
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": "edge_inference",
    }

    body = {
        "topic": "homeassistant/event/possible_littering",
        "payload": payload,
        "purpose": args.purpose,
    }
    result = post_json(args.base_url, "/simulate/publish", body)
    print("[publish]", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
