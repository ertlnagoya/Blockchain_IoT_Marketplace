#!/usr/bin/env python3
"""USB webcam bridge: person/litter event detection for marketplace demo.

- Captures frames from a USB webcam (or runs in mock mode)
- Detects persons and litter candidates with YOLO (Ultralytics)
- Applies a simple lingering heuristic for possible littering
- Writes marketplace-ready .txt events into mediator-owner/raw_data/output
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclasses.dataclass
class Detection:
    label: str
    conf: float
    cx: float
    cy: float
    w: float
    h: float


@dataclasses.dataclass
class Track:
    track_id: int
    label: str
    first_seen: float
    last_seen: float
    cx: float
    cy: float
    conf: float
    near_person_last_seen: float
    litter_event_emitted: bool = False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="USB webcam littering-event bridge for Blockchain IoT Marketplace"
    )
    p.add_argument("--mode", choices=["webcam", "mock"], default="webcam")
    p.add_argument("--camera-index", type=int, default=0)
    p.add_argument("--camera-id", default="401")
    p.add_argument("--output-dir", default="mediator-owner/raw_data/output")
    p.add_argument("--model", default="yolov8n.pt")
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--flush-seconds", type=int, default=10)
    p.add_argument("--litter-classes", default="bottle,cup")
    p.add_argument("--linger-seconds", type=float, default=8.0)
    p.add_argument("--person-near-px", type=float, default=180.0)
    p.add_argument("--person-away-seconds", type=float, default=5.0)
    p.add_argument("--person-event-interval", type=float, default=12.0)
    p.add_argument("--max-seconds", type=int, default=0)
    p.add_argument("--show", action="store_true")
    return p.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_event_txt(output_dir: Path, camera_id: str, payload: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    path = output_dir / f"{camera_id}_webcam_event_{ts}.txt"
    tmp = output_dir / f".{path.name}.tmp"
    lines = [
        "# Webcam Event Snapshot",
        f"camera_id: {camera_id}",
        f"event_type: {payload.get('event_type', 'unknown')}",
        f"event_time_utc: {payload.get('event_time_utc', now_iso())}",
        f"event_score: {payload.get('event_score', 0.0)}",
        f"summary: {payload.get('summary', '')}",
        "details:",
        json.dumps(payload, ensure_ascii=True),
    ]
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def iou_like_close(det: Detection, tr: Track, max_dist: float = 80.0) -> bool:
    return distance((det.cx, det.cy), (tr.cx, tr.cy)) <= max_dist


def update_tracks(
    tracks: Dict[int, Track],
    detections: List[Detection],
    now_ts: float,
    next_track_id: int,
) -> int:
    for det in detections:
        candidates = [
            tr
            for tr in tracks.values()
            if tr.label == det.label and iou_like_close(det, tr)
        ]
        if candidates:
            tr = min(candidates, key=lambda t: distance((det.cx, det.cy), (t.cx, t.cy)))
            tr.last_seen = now_ts
            tr.cx = det.cx
            tr.cy = det.cy
            tr.conf = det.conf
        else:
            tracks[next_track_id] = Track(
                track_id=next_track_id,
                label=det.label,
                first_seen=now_ts,
                last_seen=now_ts,
                cx=det.cx,
                cy=det.cy,
                conf=det.conf,
                near_person_last_seen=0.0,
            )
            next_track_id += 1

    # prune stale tracks
    stale = [tid for tid, tr in tracks.items() if now_ts - tr.last_seen > 3.0]
    for tid in stale:
        del tracks[tid]

    return next_track_id


def mark_person_proximity(
    tracks: Dict[int, Track],
    person_dets: List[Detection],
    litter_labels: set[str],
    now_ts: float,
    person_near_px: float,
) -> None:
    for tr in tracks.values():
        if tr.label not in litter_labels:
            continue
        for pd in person_dets:
            if distance((tr.cx, tr.cy), (pd.cx, pd.cy)) <= person_near_px:
                tr.near_person_last_seen = now_ts
                break


def build_person_event(person_count: int) -> dict:
    return {
        "event_type": "person_detected",
        "event_time_utc": now_iso(),
        "event_score": float(person_count),
        "summary": f"Detected {person_count} person(s) near camera",
        "person_count": person_count,
    }


def build_litter_event(track: Track, dwell_s: float, away_s: float) -> dict:
    return {
        "event_type": "possible_littering",
        "event_time_utc": now_iso(),
        "event_score": round(min(1.0, track.conf + min(0.4, dwell_s / 30.0)), 3),
        "summary": (
            f"{track.label} has remained for {dwell_s:.1f}s "
            f"with no nearby person for {away_s:.1f}s"
        ),
        "object": {
            "track_id": track.track_id,
            "label": track.label,
            "confidence": round(track.conf, 3),
            "cx": round(track.cx, 1),
            "cy": round(track.cy, 1),
        },
        "heuristic": {
            "dwell_seconds": round(dwell_s, 2),
            "away_seconds": round(away_s, 2),
        },
    }


def run_mock(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    start = time.time()
    print("[webcam-bridge] mock mode start")
    while True:
        payload = random.choice(
            [
                build_person_event(random.randint(1, 4)),
                {
                    "event_type": "possible_littering",
                    "event_time_utc": now_iso(),
                    "event_score": round(random.uniform(0.65, 0.95), 3),
                    "summary": "Bottle remained on ground area for long duration",
                    "object": {"track_id": random.randint(10, 30), "label": "bottle"},
                },
            ]
        )
        path = write_event_txt(output_dir, args.camera_id, payload)
        print(f"[webcam-bridge] wrote {path}")
        time.sleep(max(3, args.flush_seconds))
        if args.max_seconds and time.time() - start >= args.max_seconds:
            return 0


def load_yolo(model_name: str):
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "ultralytics is required. Install: pip install ultralytics opencv-python"
        ) from exc
    return YOLO(model_name)


def extract_detections(result, conf_th: float) -> List[Detection]:
    out: List[Detection] = []
    names = result.names
    boxes = result.boxes
    if boxes is None:
        return out
    for b in boxes:
        conf = float(b.conf[0])
        if conf < conf_th:
            continue
        cls_id = int(b.cls[0])
        label = str(names.get(cls_id, cls_id))
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        out.append(
            Detection(
                label=label,
                conf=conf,
                cx=cx,
                cy=cy,
                w=(x2 - x1),
                h=(y2 - y1),
            )
        )
    return out


def run_webcam(args: argparse.Namespace) -> int:
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("opencv-python is required. Install: pip install opencv-python") from exc

    model = load_yolo(args.model)
    litter_labels = {x.strip() for x in args.litter_classes.split(",") if x.strip()}
    if not litter_labels:
        litter_labels = {"bottle", "cup"}

    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"failed to open webcam index={args.camera_index}")

    print("[webcam-bridge] webcam mode start")
    print(
        f"[webcam-bridge] camera={args.camera_index} conf={args.conf} litter={sorted(litter_labels)}"
    )

    tracks: Dict[int, Track] = {}
    next_track_id = 1
    last_person_event_ts = 0.0
    last_flush = time.time()
    start = time.time()
    output_dir = Path(args.output_dir)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            result = model(frame, verbose=False)[0]
            dets = extract_detections(result, args.conf)
            person_dets = [d for d in dets if d.label == "person"]
            litter_dets = [d for d in dets if d.label in litter_labels]

            now_ts = time.time()
            next_track_id = update_tracks(tracks, litter_dets, now_ts, next_track_id)
            mark_person_proximity(
                tracks,
                person_dets,
                litter_labels,
                now_ts,
                person_near_px=args.person_near_px,
            )

            if person_dets and (now_ts - last_person_event_ts >= args.person_event_interval):
                payload = build_person_event(len(person_dets))
                path = write_event_txt(output_dir, args.camera_id, payload)
                print(f"[webcam-bridge] person event -> {path}")
                last_person_event_ts = now_ts

            if now_ts - last_flush >= max(1, args.flush_seconds):
                for tr in list(tracks.values()):
                    dwell_s = now_ts - tr.first_seen
                    away_s = now_ts - tr.near_person_last_seen if tr.near_person_last_seen > 0 else dwell_s
                    if (
                        not tr.litter_event_emitted
                        and dwell_s >= args.linger_seconds
                        and away_s >= args.person_away_seconds
                    ):
                        payload = build_litter_event(tr, dwell_s=dwell_s, away_s=away_s)
                        path = write_event_txt(output_dir, args.camera_id, payload)
                        print(f"[webcam-bridge] litter event -> {path}")
                        tr.litter_event_emitted = True
                last_flush = now_ts

            if args.show:
                cv2.imshow("webcam-litter-bridge", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if args.max_seconds and (now_ts - start >= args.max_seconds):
                break

    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()

    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.mode == "mock":
            return run_mock(args)
        return run_webcam(args)
    except KeyboardInterrupt:
        print("\n[webcam-bridge] stopped by user")
        return 130
    except Exception as exc:
        print(f"[webcam-bridge] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
