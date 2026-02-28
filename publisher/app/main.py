from __future__ import annotations

from fastapi import FastAPI, HTTPException

from audit.repository import SQLiteAuditRepository
from policy.engine import PolicyEngine
from policy.models import ConsentVC
from policy.store import ConsentStore
from publisher.app.config import Settings
from publisher.app.logging_utils import configure_logging
from publisher.app.models import SimulatePublishRequest
from publisher.app.mqtt_subscriber import MQTTSubscriber
from publisher.app.pipeline import MessageProcessor
from publisher.app.platform_client import PlatformClient


configure_logging()
settings = Settings()

consent_store = ConsentStore(settings.consent_store_path)
audit_repo = SQLiteAuditRepository(settings.audit_db_path)
policy_engine = PolicyEngine()
platform_client = PlatformClient(settings.platform_api_url)

processor = MessageProcessor(
    publisher_id=settings.publisher_id,
    default_purpose=settings.default_purpose,
    consent_store=consent_store,
    policy_engine=policy_engine,
    audit_repo=audit_repo,
    platform_client=platform_client,
)

mqtt_subscriber = MQTTSubscriber(
    host=settings.mqtt_broker_host,
    port=settings.mqtt_broker_port,
    topics=settings.topic_list,
    processor=processor,
)

app = FastAPI(title="IW3IP Data Publisher", version="0.1.0")
app.state.ingested = []


@app.on_event("startup")
def on_startup() -> None:
    mqtt_subscriber.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    mqtt_subscriber.stop()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "publisher"}


@app.get("/consents")
def list_consents() -> list[dict]:
    return [c.model_dump(mode="json") for c in consent_store.list()]


@app.post("/consents")
def create_or_update_consent(consent: ConsentVC) -> dict:
    stored = consent_store.upsert(consent)
    return {"status": "stored", "consent": stored.model_dump(mode="json")}


@app.delete("/consents/{vc_id}")
def delete_consent(vc_id: str) -> dict:
    deleted = consent_store.delete(vc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Consent not found")
    return {"status": "deleted", "vc_id": vc_id}


@app.post("/simulate/publish")
def simulate_publish(req: SimulatePublishRequest) -> dict:
    return processor.process_message(req.topic, req.payload, req.purpose)


@app.get("/audit/logs")
def list_audit_logs(limit: int = 100) -> list[dict]:
    return audit_repo.list_recent(limit)


@app.post("/platform/ingest")
def platform_ingest(body: dict) -> dict:
    app.state.ingested.append(body)
    return {"status": "received", "count": len(app.state.ingested)}


@app.get("/platform/ingest")
def platform_ingest_list() -> list[dict]:
    return app.state.ingested
