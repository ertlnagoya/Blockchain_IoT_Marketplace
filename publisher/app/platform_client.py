from __future__ import annotations

import httpx


class PlatformClient:
    def __init__(self, ingest_url: str) -> None:
        self._ingest_url = ingest_url

    def send(self, body: dict) -> None:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(self._ingest_url, json=body)
            response.raise_for_status()
