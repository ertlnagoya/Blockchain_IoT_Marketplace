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


def upload_media(
    base_url: str,
    file_path: Path,
    *,
    content_type: str | None = None,
) -> dict:
    """POST a binary blob to /media/upload and return the JSON response.

    Used by the Stage T (case B) hands-on flow so a data provider can
    bake an ``image_url`` / ``video_url`` into the event payload before
    sending it to the publisher. The publisher's media gateway dedupes
    on sha256 so repeated uploads of the same fixture are cheap.
    """
    import mimetypes
    import uuid

    body_bytes = file_path.read_bytes()
    if content_type is None:
        content_type = (
            mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        )
    boundary = "----iw3ip-" + uuid.uuid4().hex
    crlf = b"\r\n"
    parts: list[bytes] = []
    parts.append(f"--{boundary}".encode())
    parts.append(
        (
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{file_path.name}"'
        ).encode()
    )
    parts.append(f"Content-Type: {content_type}".encode())
    parts.append(b"")
    parts.append(body_bytes)
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    body = crlf.join(parts)

    req = request.Request(
        base_url.rstrip("/") + "/media/upload",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    with request.urlopen(req, timeout=30) as resp:  # noqa: S310 - local training endpoint
        return json.load(resp)
