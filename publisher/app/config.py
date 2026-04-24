from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    publisher_id: str = "publisher-001"
    default_purpose: str = "research"

    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_topics: str = "homeassistant/state/+/+,homeassistant/event/+"

    platform_api_url: str = "http://localhost:8080/platform/ingest"

    audit_db_path: str = "audit/audit.db"
    consent_store_path: str | None = None

    @property
    def topic_list(self) -> list[str]:
        return [t.strip() for t in self.mqtt_topics.split(",") if t.strip()]
