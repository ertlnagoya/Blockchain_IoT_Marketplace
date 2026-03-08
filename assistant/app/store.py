from __future__ import annotations

from assistant.app.models import ExecutionRecord


class ExecutionStore:
    def __init__(self) -> None:
        self._records: list[ExecutionRecord] = []

    def add(self, record: ExecutionRecord) -> ExecutionRecord:
        self._records.append(record)
        return record

    def list(self) -> list[ExecutionRecord]:
        return list(self._records)
