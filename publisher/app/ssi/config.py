from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class SSISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SSI_", extra="ignore")

    enabled: bool = False
    issuer_base_url: str = "http://localhost:8080"
    issuer_key_path: str = "/data/issuer_key.jwk.json"
    issuer_id: str = "iw3ip-publisher-issuer"
    credential_ttl_days: int = 365
    offer_ttl_seconds: int = 1800
    pex_sidecar_url: str = "http://verifier-sidecar:7000"
    presentation_defs_dir: str = "/app/examples/ssi_wallet"
    response_ttl_seconds: int = 600
