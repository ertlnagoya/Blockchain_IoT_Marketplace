from __future__ import annotations

import json
import threading
from pathlib import Path

from policy.models import ConsentVC


class ConsentStore:
    def __init__(self, file_path: str | None = None) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, ConsentVC] = {}
        self._file_path = Path(file_path) if file_path else None
        self._load_if_exists()

    def _load_if_exists(self) -> None:
        if not self._file_path or not self._file_path.exists():
            return

        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        with self._lock:
            self._by_id = {
                item["vc_id"]: ConsentVC.model_validate(item)
                for item in raw
            }

    def _save(self) -> None:
        if not self._file_path:
            return

        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [c.model_dump(mode="json") for c in self._by_id.values()]
        self._file_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def upsert(self, consent: ConsentVC) -> ConsentVC:
        with self._lock:
            self._by_id[consent.vc_id] = consent
            self._save()
            return consent

    def list(self) -> list[ConsentVC]:
        with self._lock:
            return list(self._by_id.values())

    def delete(self, vc_id: str) -> bool:
        with self._lock:
            deleted = self._by_id.pop(vc_id, None) is not None
            if deleted:
                self._save()
            return deleted

    def find_by_dataset(self, dataset_id: str) -> list[ConsentVC]:
        with self._lock:
            return [c for c in self._by_id.values() if c.dataset_id == dataset_id]
