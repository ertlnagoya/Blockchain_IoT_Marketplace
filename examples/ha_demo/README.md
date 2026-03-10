# Home Assistant Demo Examples

This directory contains the sample payloads and consents used by the Home Assistant demo simulator.

## Files

- `consent_temperature.json`
- `consent_power.json`
- `consent_person_detected.json`
- `consent_flood_risk_high.json`
- `consent_possible_littering.json`
- `consent_suspicious_activity.json`
- `payload_temperature.json`
- `payload_power.json`
- `payload_person_detected.json`
- `payload_flood_risk_high.json`
- `payload_possible_littering.json`
- `payload_suspicious_activity.json`
- `phase3_request_park_safety.json`
- `run_phase3_from_ingest.py`
- `nodered_flows.json`

## Intended use

1. start `docker compose -f infra/docker-compose.yml --profile ha-demo up --build -d`
2. open Home Assistant at `http://localhost:8123`
3. add the MQTT integration with host `mosquitto` and port `1883`
4. register the consent files into the publisher
5. run Home Assistant scripts or use the payload files for direct testing

This directory now covers:

- Phase 1: state sharing (`temperature`, `power`)
- Phase 2: event sharing (`person_detected`, `flood_risk_high`, `possible_littering`, `suspicious_activity`)
- Phase 3: assistant execution from publisher ingest records

## Register sample consents

```bash
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_temperature.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_power.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_person_detected.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_flood_risk_high.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_possible_littering.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_suspicious_activity.json
```

## Direct MQTT testing example

```bash
docker exec -i iw3ip-mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t homeassistant/state/sensor/temperature \
  -m "$(cat examples/ha_demo/payload_temperature.json)"
```

## Optional Node-RED

Import `nodered_flows.json` into Node-RED if you want clickable inject nodes for the same MQTT topics.

## Phase 3 bridge

Start publisher, Home Assistant demo, and assistant together:

```bash
docker compose -f infra/docker-compose.yml --profile ha-demo-phase3 up --build -d
```

Run the Home Assistant script `script.iw3ip_publish_demo_phase3_safety_scenario`, then inspect the plan first:

```bash
python3 examples/ha_demo/run_phase3_from_ingest.py \
  --plan-only \
  --request-file examples/ha_demo/phase3_request_park_safety.json
```

Then execute with the same request:

```bash
python3 examples/ha_demo/run_phase3_from_ingest.py \
  --request-file examples/ha_demo/phase3_request_park_safety.json
```

This script:

1. reads `GET /platform/ingest` from the publisher
2. calls `POST /assistant/plan` when `--plan-only` is set
3. converts allowed Home Assistant events into `observed_events` and calls `POST /assistant/execute` otherwise

Use `--print-only` if you want to inspect the generated request body first.
