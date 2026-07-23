#!/usr/bin/env python3
"""Reference solution for the "local VLM / semantic distribution" hands-on.

Flow (see README.md for the walkthrough):

  1. analyze  : POST the frame to /semantic/analyze and read back the
                Semantic Intermediate Representation (SIR) -- the local
                model's structured "meaning" for the image. No wallet,
                no VC: this is the dev/integration affordance.
  2. summarize: turn the SIR JSON into a one-line human summary.
  3. distribute (optional, --distribute): register a consent, upload the
                image to /media/upload, and publish an event carrying the
                image_url through /simulate/publish, so the AI-derived
                data enters the platform's distribution pipeline. With
                the publisher started under `--profile vlm`, the VLM also
                attaches description_full / description_summary to the row
                (retrieved per trust tier in the DataUserVC hands-on).
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
    """One-line human summary of a Semantic Intermediate Representation."""
    people = (sir.get("people") or {}).get("count", 0)
    objects = len(sir.get("objects") or [])
    sensitive = len(sir.get("sensitive_regions") or [])
    risk = sir.get("privacy_risk_score", 0.0)
    scene = sir.get("scene_summary") or "(no scene summary)"
    return (
        f"people={people}, objects={objects}, sensitive_regions={sensitive}, "
        f"privacy_risk={risk} | {scene}"
    )


def build_event(image_url: str, camera_id: str) -> dict:
    """Build the event payload that carries the frame into the platform."""
    return {
        "event_type": "possible_littering",
        "data": {
            "camera_id": camera_id,
            "object_class": "unknown",
            "confidence": 0.5,
        },
        "image_url": image_url,
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": "local_vlm_distribution",
    }


def distribute_frame(
    base_url: str, image_path: Path, camera_id: str, purpose: str
) -> dict:
    """Register a consent, upload the image, and publish the event."""
    # Register a consent so /simulate/publish is allowed (idempotent).
    consent = load_json(HERE / "fixtures" / "consent_webcam.json")
    post_json(base_url, "/consents", consent)

    # Upload the frame; the publisher's media gateway dedupes on sha256.
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
    parser.add_argument(
        "--distribute",
        action="store_true",
        help="Also publish the frame into the platform (needs a running stack).",
    )
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
