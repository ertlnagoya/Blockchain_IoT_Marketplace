#!/usr/bin/env python3
"""HUSKYLENS2 sensor bridge for Blockchain IoT Marketplace.

This script receives detections from HUSKYLENS2 (or a compatible relay)
and periodically writes summary .txt files into mediator-owner raw_data.
Those .txt files are automatically productized by mediator-owner.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import random
import socket
import sys
import time
from pathlib import Path
from typing import Iterable, Optional


@dataclasses.dataclass
class Detection:
    ts: dt.datetime
    label: str
    confidence: float
    source: str
    object_id: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    w: Optional[float] = None
    h: Optional[float] = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge HUSKYLENS2 detections into marketplace-ready .txt products"
    )
    parser.add_argument("--mode", choices=["serial", "tcp", "mock"], default="mock")
    parser.add_argument("--serial-port", default="/dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--tcp-host", default="0.0.0.0")
    parser.add_argument("--tcp-port", type=int, default=8899)
    parser.add_argument(
        "--output-dir",
        default="mediator-owner/raw_data/output",
        help="Directory watched by mediator-owner",
    )
    parser.add_argument("--camera-id", default="301")
    parser.add_argument("--flush-interval-sec", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=0.5)
    parser.add_argument("--mock-labels", default="person,car,bike")
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_line_to_detection(line: str, source: str) -> Optional[Detection]:
    line = line.strip()
    if not line:
        return None

    # Preferred format (NDJSON)
    # {"label":"person","confidence":0.92,"id":"12","x":120,"y":80,"w":48,"h":60,"timestamp":"..."}
    if line.startswith("{"):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None

        label = str(obj.get("label", "unknown")).strip() or "unknown"
        confidence = float(obj.get("confidence", 0.0))
        ts_val = obj.get("timestamp")
        if isinstance(ts_val, str):
            try:
                ts = dt.datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            except ValueError:
                ts = now_utc()
        else:
            ts = now_utc()

        return Detection(
            ts=ts,
            label=label,
            confidence=confidence,
            source=source,
            object_id=_to_optional_str(obj.get("id")),
            x=_to_optional_float(obj.get("x")),
            y=_to_optional_float(obj.get("y")),
            w=_to_optional_float(obj.get("w")),
            h=_to_optional_float(obj.get("h")),
        )

    # Fallback format (CSV)
    # label,id,confidence,x,y,w,h
    parts = [p.strip() for p in line.split(",")]
    if len(parts) >= 3:
        label = parts[0] or "unknown"
        return Detection(
            ts=now_utc(),
            label=label,
            confidence=_safe_float(parts[2], default=0.0),
            source=source,
            object_id=parts[1] or None,
            x=_safe_float(parts[3], default=None) if len(parts) > 3 else None,
            y=_safe_float(parts[4], default=None) if len(parts) > 4 else None,
            w=_safe_float(parts[5], default=None) if len(parts) > 5 else None,
            h=_safe_float(parts[6], default=None) if len(parts) > 6 else None,
        )
    return None


def _safe_float(value: str, default: Optional[float]) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_optional_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_optional_str(value: object) -> Optional[str]:
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str or None


def serial_lines(port: str, baudrate: int) -> Iterable[str]:
    try:
        import serial  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pyserial is required for --mode serial. Install with: pip install pyserial"
        ) from exc

    with serial.Serial(port=port, baudrate=baudrate, timeout=1) as ser:
        print(f"[bridge] serial connected: {port} @ {baudrate}")
        while True:
            raw = ser.readline()
            if not raw:
                continue
            try:
                yield raw.decode("utf-8", errors="replace")
            except UnicodeDecodeError:
                continue


def tcp_lines(host: str, port: int) -> Iterable[str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        print(f"[bridge] tcp listening: {host}:{port}")
        while True:
            conn, addr = server.accept()
            print(f"[bridge] tcp client connected: {addr[0]}:{addr[1]}")
            with conn:
                fileobj = conn.makefile("r", encoding="utf-8", newline="\n")
                for line in fileobj:
                    yield line
            print("[bridge] tcp client disconnected")


def mock_detections(labels: list[str]) -> Iterable[Detection]:
    while True:
        time.sleep(1)
        count = random.randint(0, 4)
        for _ in range(count):
            label = random.choice(labels)
            confidence = random.uniform(0.45, 0.99)
            yield Detection(
                ts=now_utc(),
                label=label,
                confidence=confidence,
                source="mock",
                object_id=str(random.randint(1, 20)),
                x=random.uniform(0, 640),
                y=random.uniform(0, 480),
                w=random.uniform(20, 200),
                h=random.uniform(20, 200),
            )


def build_product_text(
    camera_id: str,
    started_at: dt.datetime,
    ended_at: dt.datetime,
    detections: list[Detection],
) -> str:
    by_label: dict[str, int] = {}
    max_conf = 0.0
    for det in detections:
        by_label[det.label] = by_label.get(det.label, 0) + 1
        max_conf = max(max_conf, det.confidence)

    sorted_labels = sorted(by_label.items(), key=lambda kv: (-kv[1], kv[0]))
    top_label = sorted_labels[0][0] if sorted_labels else "none"

    lines = [
        "# HuskyLens2 Detection Snapshot",
        f"camera_id: {camera_id}",
        f"window_start_utc: {started_at.isoformat()}",
        f"window_end_utc: {ended_at.isoformat()}",
        f"total_detections: {len(detections)}",
        f"unique_labels: {len(by_label)}",
        f"top_label: {top_label}",
        f"max_confidence: {max_conf:.3f}",
        "labels:",
    ]
    for label, cnt in sorted_labels:
        lines.append(f"  - {label}: {cnt}")

    lines.append("samples:")
    for det in detections[:30]:
        lines.append(
            "  - "
            + json.dumps(
                {
                    "timestamp": det.ts.isoformat(),
                    "label": det.label,
                    "confidence": round(det.confidence, 4),
                    "id": det.object_id,
                    "x": _round_or_none(det.x),
                    "y": _round_or_none(det.y),
                    "w": _round_or_none(det.w),
                    "h": _round_or_none(det.h),
                    "source": det.source,
                },
                ensure_ascii=True,
            )
        )

    return "\n".join(lines) + "\n"


def _round_or_none(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 2)


def write_product_file(output_dir: Path, camera_id: str, content: str, dry_run: bool) -> Optional[Path]:
    ts = int(time.time())
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{camera_id}_huskylens_{ts}.txt"
    final_path = output_dir / filename
    tmp_path = output_dir / f".{filename}.tmp"

    if dry_run:
        print(f"[bridge][dry-run] would write: {final_path}")
        return None

    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, final_path)
    return final_path


def run_bridge(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    min_conf = float(args.min_confidence)
    camera_id = str(args.camera_id)
    flush_interval = max(1, int(args.flush_interval_sec))

    print("[bridge] starting HuskyLens2 bridge")
    print(f"[bridge] mode={args.mode} camera_id={camera_id} output_dir={output_dir}")
    print(f"[bridge] flush_interval_sec={flush_interval} min_confidence={min_conf:.2f}")

    batches_written = 0
    started_at = now_utc()
    last_flush = time.time()
    buffer: list[Detection] = []

    if args.mode == "mock":
        labels = [x.strip() for x in args.mock_labels.split(",") if x.strip()]
        if not labels:
            labels = ["person"]
        source_iter: Iterable[Detection] = mock_detections(labels)
        for det in source_iter:
            if det.confidence >= min_conf:
                buffer.append(det)
            now = time.time()
            if now - last_flush >= flush_interval:
                ended_at = now_utc()
                content = build_product_text(camera_id, started_at, ended_at, buffer)
                written = write_product_file(output_dir, camera_id, content, args.dry_run)
                print(
                    f"[bridge] batch detections={len(buffer)} "
                    + (f"file={written}" if written else "file=<dry-run>")
                )
                buffer = []
                started_at = ended_at
                last_flush = now
                batches_written += 1
                if args.max_batches and batches_written >= args.max_batches:
                    break
        return 0

    if args.mode == "serial":
        line_iter = serial_lines(args.serial_port, args.baudrate)
        source_name = f"serial:{args.serial_port}"
    else:
        line_iter = tcp_lines(args.tcp_host, args.tcp_port)
        source_name = f"tcp:{args.tcp_host}:{args.tcp_port}"

    for line in line_iter:
        det = parse_line_to_detection(line, source=source_name)
        if det and det.confidence >= min_conf:
            buffer.append(det)

        now = time.time()
        if now - last_flush < flush_interval:
            continue

        ended_at = now_utc()
        content = build_product_text(camera_id, started_at, ended_at, buffer)
        written = write_product_file(output_dir, camera_id, content, args.dry_run)
        print(
            f"[bridge] batch detections={len(buffer)} "
            + (f"file={written}" if written else "file=<dry-run>")
        )
        buffer = []
        started_at = ended_at
        last_flush = now
        batches_written += 1
        if args.max_batches and batches_written >= args.max_batches:
            break

    return 0


def main() -> int:
    args = parse_args()
    try:
        return run_bridge(args)
    except KeyboardInterrupt:
        print("\n[bridge] stopped by user")
        return 130
    except Exception as exc:  # keep message concise for first learners
        print(f"[bridge] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
