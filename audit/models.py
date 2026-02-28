from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AuditLogRecord:
    ts: str
    action: str
    subject_did: str
    dataset_id: str
    purpose: str
    reason: str
    message_hash: str
    raw_topic: str
