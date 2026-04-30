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

    # Stage T (case B): static directory the media gateway writes uploaded
    # image/video blobs into and serves them from at /media/<sha256>.<ext>.
    # Production callers (docker compose) should override this to a real
    # volume mount such as /data/media; the relative default is so the
    # publisher boots fine in the test environment without sudo.
    media_store_path: str = "publisher/data/media"
    # Public base URL the wallet / browser uses to GET /media/<name>. When
    # left empty we mint a relative path so the wallet/browser inherits the
    # same origin it fetched the platform data from.
    media_public_base_url: str = ""

    # Stage T (case C): IPFS daemon HTTP API base URL (e.g.
    # http://ipfs:5001). When set, /media/upload also pushes the blob
    # into IPFS via `POST /api/v0/add` and the response carries a real
    # content-addressed `cid`. When empty, the gateway runs in case B
    # mode (publisher-hosted URL only).
    ipfs_api_url: str = ""
    # IPFS HTTP gateway (the publisher reverse-proxies /ipfs/<cid> to
    # this). Production: http://ipfs:8080 inside the docker network;
    # leave empty to disable the proxy and rely on public gateways.
    ipfs_gateway_url: str = ""

    # Stage 7 (case C): when set, /marketplace/register verifies that
    # Merchandise.getOwner() == seller_eth_addr against this RPC. Leave
    # unset in tests/dev to skip the check (and in audit log we'll mark
    # the registration as "owner_verify=skipped").
    marketplace_hardhat_rpc: str | None = None

    # Stage T (VLM extension): semantic-level tier projection.
    # Empty string ("") = legacy 3-tier behaviour (drop image/video keys
    # per access_level). When set, the pipeline produces VLM-derived
    # keys (description_full / description_summary) and a redacted
    # image alongside the raw upload, and `allowed_views` gains the
    # `image_redacted` / `description_full` / `description_summary`
    # labels. See docs/hands-on/data-user-vc-tiered-spec.md
    # "Tier extension: semantic-level redaction (VLM)".
    #
    # Backends:
    #   ""        -> disabled (legacy tier projection)
    #   "stub"    -> deterministic dummy strings (test mode)
    #   "ollama"  -> POST to OLLAMA_API_URL with VLM_MODEL (Δ3+)
    vlm_backend: str = ""
    vlm_api_url: str = ""
    vlm_model: str = "llava"

    # Image redaction: independent of VLM (face blur doesn't need a
    # multimodal model). Empty string = disabled. "stub" = passthrough
    # marker for tests. "opencv" = real Haar-cascade face blur (Δ3).
    image_redaction_backend: str = ""

    # Stage T+ (semantic-tier pipeline). Selects which
    # SemanticAnalyzer backend services /semantic/analyze. The
    # analyzer turns a frame into a SIR
    # (Semantic Intermediate Representation) that the trust-aware
    # renderer consumes. Backends:
    #   ""       -> mock (deterministic stub; test/dev default)
    #   "stub"   -> alias of mock
    #   "vision" -> OpenCV Haar cascade + MSER heuristic
    #               (requires opencv-python-headless)
    # Apple Vision / Core ML / external VLM backends would slot in
    # here without changes to /semantic/* call sites.
    semantic_analyzer_backend: str = ""

    # Allow HIGH-tier viewers to receive `unknown_sensitive` regions
    # un-masked. Default: False (fail-closed). Operators with a manual
    # review queue downstream can flip this to True.
    semantic_allow_unknown_at_high: bool = False

    @property
    def vlm_enabled(self) -> bool:
        """True when any VLM-tier feature is active.

        Used by trust_score / pipeline / platform_data to switch between
        legacy 3-tier projection and the 4-tier (full/access/summary/
        denied) projection. We tie it to vlm_backend (text derivatives)
        rather than image_redaction_backend so a config that turns on
        only blur without VLM still falls back to legacy tiering --
        receivers without `description_summary` shouldn't see a
        `summary` tier with nothing in it.
        """
        return bool(self.vlm_backend)

    @property
    def topic_list(self) -> list[str]:
        return [t.strip() for t in self.mqtt_topics.split(",") if t.strip()]
