from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConsentVC(BaseModel):
    vc_id: str
    subject_did: str
    dataset_id: str
    allowed_purposes: list[str]
    retention_days: int
    reshare_allowed: bool
    valid_from: datetime
    valid_to: datetime
    signature: str
