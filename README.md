# IoTxWeb3 Intelligence Platform (IW3IP)

## Home Assistant x SSI Data Publisher Sample (Phase 1)

Language: **English** | [日本語](README_ja.md)

This branch provides a minimal, extensible prototype for user-sovereign IoT data sharing:

Home Assistant -> MQTT -> (optional Node-RED) -> Data Publisher -> Data Sharing Platform API

The Data Publisher normalizes incoming data, evaluates Consent VC policy, sends only allowed data, and records audit logs.

## What This Sample Demonstrates

This sample is a minimum working prototype for sharing Home Assistant data with a user-sovereign model (SSI/DID/VC).

- Receives state/event data from Home Assistant via MQTT
- Normalizes input into a common schema and assigns `dataset_id`
- Evaluates Consent VC conditions (`dataset_id`, `purpose`, validity window)
- Sends only permitted data to Platform API
- Stores `allow` / `deny` / `send_error` in SQLite audit logs

Example datasets:
- `home/env/temperature`
- `home/energy/power`
- `home/event/person_detected`
- `home/event/flood_risk_high`
- `home/event/possible_littering`

## Runtime Environment

### Required

- Docker / Docker Compose (with `docker compose`)
- Python 3.11+ (for local run and tests)

### Tech Stack (implemented)

- FastAPI + pydantic (Data Publisher)
- Eclipse Mosquitto (MQTT)
- SQLite (audit log DB)
- pytest (tests)
- uv (dependency management / local run examples)

### Verified in this branch

- `docker compose -f infra/docker-compose.yml up --build`
- `GET /health`
- `POST /consents`
- `POST /simulate/publish`
- MQTT ingest via `mosquitto_pub` and audit log recording

## Beginner Quick Guide

If this is your first time, follow this section top to bottom.

### 0. Pre-check (copy and run)

```bash
docker --version
docker compose version
curl --version
```

Expected:
- each command prints a version
- no command-not-found errors

### 1. Start the system

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

Expected:
- `iw3ip-mosquitto` and `iw3ip-publisher` become `Up`

Optional check:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

### 2. Confirm API is alive

```bash
curl http://localhost:8080/health
```

Expected:

```json
{"status":"ok","service":"publisher"}
```

### 3. Register all sample consents

```bash
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_temperature.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_power.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_person_detected.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_flood_risk_high.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_possible_littering.json
```

Expected:
- each response includes `"status":"stored"`

Phase 2 example files:
- `examples/consent_flood_risk_high.json`
- `examples/consent_possible_littering.json`
- `examples/payload_flood_risk_high.json`
- `examples/payload_possible_littering.json`

### 4. Simulate an allowed message (HTTP path)

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/state/sensor/temperature",
    "payload":{
      "entity_id":"sensor.living_room_temperature",
      "state":"24.1",
      "attributes":{"unit_of_measurement":"C"},
      "ts":"2026-02-28T10:00:00Z",
      "source":"home_assistant"
    },
    "purpose":"research"
  }'
```

Expected:

```json
{"status":"allowed","dataset_id":"home/env/temperature"}
```

### 5. Simulate a denied message (purpose mismatch)

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/state/sensor/power",
    "payload":{
      "entity_id":"sensor.main_power",
      "state":"520",
      "attributes":{"unit_of_measurement":"W"},
      "ts":"2026-02-28T10:00:10Z",
      "source":"home_assistant"
    },
    "purpose":"marketing"
  }'
```

Expected:

```json
{"status":"denied","dataset_id":"home/energy/power","reason":"no_matching_consent"}
```

### 6. Verify audit logs

```bash
curl http://localhost:8080/audit/logs?limit=5
```

Expected:
- includes both `allow` and `deny` actions
- each row has `message_hash`, `dataset_id`, and `purpose`

### 7. Test MQTT ingestion path

```bash
docker exec -i iw3ip-mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t homeassistant/event/person_detected \
  -m '{"event_type":"person_detected","data":{"camera_id":"front_door","confidence":0.93},"ts":"2026-02-28T10:00:20Z","source":"edge_inference"}'
```

Then check logs again:

```bash
curl http://localhost:8080/audit/logs?limit=5
```

### 8. Stop services

```bash
docker compose -f infra/docker-compose.yml down
```

## Scope

- Phase 1 (implemented): data exchange pipeline + consent-based policy + audit logging
- Phase 2 (design hook): event-oriented sharing (inference/events)
- Phase 3 (design hook): SSI gateway / PEP before publisher

## Phase 3 Regional Safety Assistant Sample

This branch also adds a minimal Phase 3 prototype that interprets a human request, decomposes it into tasks, evaluates recent events, and triggers dummy device actions.

Flow:

`human request -> planner -> execution plan -> event evaluation -> action commands`

Implemented endpoints:
- `GET /health`
- `POST /assistant/plan`
- `POST /assistant/execute`
- `GET /assistant/executions`

Minimal demo request:

```json
{
  "request_text": "If littering or suspicious behavior increases near the north side of the park, let me know. Turn on the lights and notify the manager if needed."
}
```

Main sample files:
- `examples/phase3_request_park_safety.json`
- `examples/phase3_events_park_safety.json`
- `assistant/app/main.py`
- `assistant/app/planner.py`
- `assistant/app/planner_interface.py`
- `assistant/app/planner_factory.py`
- `assistant/app/rule_based_planner.py`
- `assistant/app/llm_planner.py`
- `assistant/app/llm_prompt.py`
- `assistant/app/llm_provider.py`
- `assistant/app/plan_validator.py`
- `assistant/app/evaluator.py`
- `assistant/app/actuator.py`

Quick run example:

```bash
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Example plan request:

```bash
curl -X POST http://localhost:8090/assistant/plan \
  -H 'Content-Type: application/json' \
  -d @examples/phase3_request_park_safety.json
```

The response now also includes `planner_diagnostics`, for example:

```json
{
  "planner_diagnostics": {
    "planner_mode": "llm",
    "provider_name": "openai_compatible",
    "used_fallback": true,
    "error_type": "LLMProviderError",
    "error_message": "model response is not valid JSON"
  }
}
```

Readable fields:

- `status`
  - `ok` or `fallback`
- `summary`
  - short human-readable explanation
- `suggestion`
  - next troubleshooting step

Example execute request:

```bash
curl -X POST http://localhost:8090/assistant/execute \
  -H 'Content-Type: application/json' \
  -d @examples/phase3_request_park_safety.json
```

### Phase 3 planner modes

The assistant now separates planner selection from planner implementation.

- `ASSISTANT_PLANNER_MODE=rule_based`
  - uses `RuleBasedPlanner`
- `ASSISTANT_PLANNER_MODE=llm`
  - uses `LLMPlanner`
- `ASSISTANT_LLM_PROVIDER=stub`
  - self-contained local provider for testing
- `ASSISTANT_LLM_PROVIDER=openai_compatible`
  - calls an actual OpenAI-compatible `/chat/completions` API
- `ASSISTANT_LLM_API_BASE_URL`
- `ASSISTANT_LLM_API_KEY`
- `ASSISTANT_LLM_MODEL`

The current `LLMPlanner` keeps the same `ExecutionPlan` output contract, builds prompts in `llm_prompt.py`, validates allowed events/actions/areas, and falls back to the rule-based planner if the LLM response is invalid.

Example:

```bash
ASSISTANT_PLANNER_MODE=llm \
ASSISTANT_PLANNER_NAME=llm-planner-stub-v1 \
ASSISTANT_LLM_PROVIDER=stub \
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Actual API example:

```bash
ASSISTANT_PLANNER_MODE=llm \
ASSISTANT_PLANNER_NAME=llm-planner-openai-compatible-v1 \
ASSISTANT_LLM_PROVIDER=openai_compatible \
ASSISTANT_LLM_API_BASE_URL=https://api.openai.com/v1 \
ASSISTANT_LLM_API_KEY=REPLACE_WITH_YOUR_API_KEY \
ASSISTANT_LLM_MODEL=gpt-4.1-mini \
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Local HTTP mock example:

```bash
uvicorn examples.phase3_llm_mock_server:app --host 127.0.0.1 --port 18000
```

Then, in another terminal:

```bash
source examples/phase3_llm_mock.env.example
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Matching files:

- `.env.local.example`
- `examples/phase3_llm.env.example`
- `examples/phase3_llm_mock.env.example`
- `examples/phase3_llm_expected_plan.json`
- `examples/phase3_request_station_warning.json`
- `examples/phase3_llm_mock_server.py`

Recommended local setup:

```bash
cp .env.local.example .env.local
source .env.local
```

Docker Compose example:

```bash
docker compose -f infra/docker-compose.yml --profile assistant-llm up --build -d assistant-llm
```

Common troubleshooting for `openai_compatible`:

- `401 Unauthorized`
  - check `ASSISTANT_LLM_API_KEY`
- `404` or `405`
  - check `ASSISTANT_LLM_API_BASE_URL`
- the response always falls back to the rule-based planner
  - check whether the model returned valid JSON content

Exercise pytest:

```bash
pytest -q tests/test_phase3_llm_hands_on_program.py
```

To run the same test against the exercise file after implementing the TODOs:

```bash
PHASE3_LLM_HANDS_ON_MODULE=examples.hands_on.phase3_llm_planner.problem_program \
pytest -q tests/test_phase3_llm_hands_on_program.py
```

If you are debugging a real LLM API issue, check:

```bash
curl http://localhost:8090/assistant/executions
```

Look for `planner_diagnostics.error_type`, `planner_diagnostics.error_message`, and `planner_diagnostics.used_fallback`.

## Phase 2 Example Files

The repository now also includes Phase 2 event-sharing example files so that the website hands-on pages and the source repository use the same names and payloads.

- `examples/consent_flood_risk_high.json`
  - allows `home/event/flood_risk_high` for `disaster_response` and `research`
- `examples/consent_possible_littering.json`
  - allows `home/event/possible_littering` for `community_cleaning` and `research`
- `examples/payload_flood_risk_high.json`
  - sample event payload for disaster-response sharing
- `examples/payload_possible_littering.json`
  - sample event payload for littering-event sharing

If you want a ready-made Phase 2 path, see `examples/README.md` and the website hands-on pages for:
- environment/disaster event sharing
- webcam event sharing

For workshop exercise versions with problem programs and reference solutions, see:
- `examples/hands_on/README.md`
- `examples/hands_on/huskylens2_mock/`
- `examples/hands_on/webcam_littering_mock/`
- `examples/hands_on/mobile_viewer/`
- `examples/hands_on/phase1_ha_ssi_publisher/`
- `examples/hands_on/phase2_environment_disaster/`
- `examples/hands_on/phase2_webcam_event_sharing/`
- `examples/hands_on/phase3_llm_planner/`

## Directory Structure

- `assistant/` : Phase 3 regional safety assistant (planner interface/factory, rule-based planner, minimal LLM planner, evaluator, actuator, API)
- `publisher/` : FastAPI-based Data Publisher
- `schemas/` : normalization and common schemas
- `policy/` : Consent VC model, signature verifier interface, policy engine
- `audit/` : audit DB access layer (SQLite now, replaceable later)
- `infra/` : docker compose, Mosquitto config, optional Node-RED
- `examples/` : sample payloads, sample consents, Phase 3 request/event fixtures, demo commands
- `tests/` : pytest tests (policy, normalization, audit, assistant)

## Quick Start (Docker)

### 1. Start services

```bash
docker compose -f infra/docker-compose.yml up --build
```

This starts:
- `mosquitto` (MQTT broker)
- `publisher` (FastAPI + MQTT subscriber)
- `nodered` (optional, profile: `nodered`)

### 2. Health check

```bash
curl http://localhost:8080/health
```

Expected:

```json
{"status":"ok","service":"publisher"}
```

### 3. Register Consent VC

```bash
curl -X POST http://localhost:8080/consents \
  -H 'Content-Type: application/json' \
  -d @examples/consent_temperature.json
```

### 4. Publish a Home Assistant-like MQTT message

```bash
docker exec -i iw3ip-mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t homeassistant/state/sensor/temperature \
  -m '{"entity_id":"sensor.living_room_temperature","state":"24.1","attributes":{"unit_of_measurement":"C"},"ts":"2026-02-28T10:00:00Z","source":"home_assistant"}'
```

### 5. Check audit logs

```bash
curl http://localhost:8080/audit/logs
```

You should see `allow` entries for permitted datasets/purposes.

## Local Run (uv)

### 1. Install dependencies

```bash
uv sync
```

### 2. Run publisher

```bash
uv run uvicorn publisher.app.main:app --host 0.0.0.0 --port 8080
```

## Configuration (Environment Variables)

- `PUBLISHER_ID` (default: `publisher-001`)
- `DEFAULT_PURPOSE` (default: `research`)
- `MQTT_BROKER_HOST` (default: `mosquitto` in docker / `localhost` locally)
- `MQTT_BROKER_PORT` (default: `1883`)
- `MQTT_TOPICS` (comma-separated, default: `homeassistant/state/+/+,homeassistant/event/+`)
- `PLATFORM_API_URL` (default: `http://publisher:8080/platform/ingest` in docker)
- `AUDIT_DB_PATH` (default: `./audit/audit.db`)
- `CONSENT_STORE_PATH` (optional file path for persisted consents)

## Home Assistant -> MQTT Example Topics and Payloads

### Topic 1: temperature state

- Topic: `homeassistant/state/sensor/temperature`
- Payload:

```json
{
  "entity_id": "sensor.living_room_temperature",
  "state": "24.1",
  "attributes": {"unit_of_measurement": "C"},
  "ts": "2026-02-28T10:00:00Z",
  "source": "home_assistant"
}
```

### Topic 2: power state

- Topic: `homeassistant/state/sensor/power`
- Payload:

```json
{
  "entity_id": "sensor.main_power",
  "state": "520",
  "attributes": {"unit_of_measurement": "W"},
  "ts": "2026-02-28T10:00:10Z",
  "source": "home_assistant"
}
```

### Topic 3: person_detected event

- Topic: `homeassistant/event/person_detected`
- Payload:

```json
{
  "event_type": "person_detected",
  "data": {"camera_id": "front_door", "confidence": 0.93},
  "ts": "2026-02-28T10:00:20Z",
  "source": "edge_inference"
}
```

## API

- `GET /health`
- `GET /consents`
- `POST /consents`
- `DELETE /consents/{vc_id}`
- `POST /simulate/publish` (HTTP-based injection without MQTT)
- `GET /audit/logs` (debug helper)
- `POST /platform/ingest` (dummy platform endpoint)

## Policy Rules (Phase 1)

A message is allowed only when:

1. Consent exists with matching `dataset_id`
2. `purpose` is in `allowed_purposes`
3. current time in `[valid_from, valid_to]`

If denied, no platform send occurs and audit action is `deny`.

## Audit Log

SQLite table `audit_log` columns:

- `id`
- `ts`
- `action` (`allow`, `deny`, `send_error`)
- `subject_did`
- `dataset_id`
- `purpose`
- `reason`
- `message_hash` (SHA-256)
- `raw_topic`

## Test

```bash
uv run pytest -q
```

Covers:
- policy decision
- normalization mapping
- audit repository persistence

## Extension Points

- Signature verification: replace `policy.verifier.verify_signature()`
- DID resolution: add a DID resolver module and connect it to policy check
- External platform integration: set `PLATFORM_API_URL` to real endpoint
- DB backend swap: add PostgreSQL repository implementing audit store interface
- PEP hook for Phase 3: insert VC presentation check before `process_message`

## Notes

- This is a research prototype for rapid validation.
- JSON-LD VC is not implemented yet, but Consent VC keys are designed to migrate.

## Troubleshooting (Beginner)

- `port is already allocated`:
  - another process uses `1883` or `8080`
  - stop it or change ports in `infra/docker-compose.yml`
- `curl: (7) Failed to connect`:
  - publisher is not ready yet
  - check `docker ps` and retry in a few seconds
- always `denied`:
  - consent missing, expired, wrong dataset, or wrong purpose
  - verify `/consents` response and test purpose `research`
- no MQTT processing:
  - verify topic prefix is `homeassistant/state/...` or `homeassistant/event/...`
  - verify JSON payload format

## Mini Glossary

- `Consent VC`: user consent record for what data can be shared and for which purpose
- `dataset_id`: normalized logical data category (for policy matching)
- `purpose`: reason of sharing (example: `research`)
- `PEP`: policy enforcement point (planned in Phase 3)
