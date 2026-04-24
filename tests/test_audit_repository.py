from audit.models import AuditLogRecord
from audit.repository import SQLiteAuditRepository


def test_audit_write_and_list(tmp_path) -> None:
    repo = SQLiteAuditRepository(str(tmp_path / "audit.db"))
    repo.write(
        AuditLogRecord(
            ts="2026-02-28T10:00:00Z",
            action="allow",
            subject_did="did:example:alice",
            dataset_id="home/env/temperature",
            purpose="research",
            reason="sent",
            message_hash="abc",
            raw_topic="homeassistant/state/sensor/temperature",
        )
    )
    rows = repo.list_recent()
    assert len(rows) == 1
    assert rows[0]["action"] == "allow"
