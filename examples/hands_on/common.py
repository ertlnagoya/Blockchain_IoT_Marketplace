#!/usr/bin/env python3
"""Shared helpers for hands-on sample programs."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from urllib import request


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


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


def get_json(url: str) -> dict | list:
    with request.urlopen(url, timeout=10) as resp:  # noqa: S310 - local training endpoint
        return json.load(resp)


def write_text(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def detect_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()
