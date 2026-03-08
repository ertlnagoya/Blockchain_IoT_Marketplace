# Examples

## Hands-on sample programs

- `examples/hands_on/README.md`
  - overview of all exercise programs
- `examples/hands_on/phase2_environment_disaster/problem_program.py`
  - exercise version with `TODO`
- `examples/hands_on/phase2_environment_disaster/answer_program.py`
  - reference solution
- `examples/hands_on/phase2_environment_disaster/README.md`
  - step-by-step instructions for the exercise

Other hands-on exercise directories:

- `examples/hands_on/huskylens2_mock/`
- `examples/hands_on/webcam_littering_mock/`
- `examples/hands_on/mobile_viewer/`
- `examples/hands_on/phase1_ha_ssi_publisher/`
- `examples/hands_on/phase2_webcam_event_sharing/`

## Phase 3 LLM planner examples

- `examples/phase3_request_park_safety.json`
  - base request used by both the rule-based and LLM planners
- `examples/phase3_request_station_warning.json`
  - English request example for area/action variation
- `examples/phase3_events_park_safety.json`
  - sample observed events
- `examples/phase3_llm.env.example`
  - environment variable template for an actual OpenAI-compatible LLM API
- `examples/phase3_llm_expected_plan.json`
  - example shape expected from `/assistant/plan`

### Phase 3 with stub LLM provider

```bash
ASSISTANT_PLANNER_MODE=llm \
ASSISTANT_PLANNER_NAME=llm-planner-stub-v1 \
ASSISTANT_LLM_PROVIDER=stub \
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

```bash
curl -X POST http://localhost:8090/assistant/plan \
  -H 'Content-Type: application/json' \
  -d @examples/phase3_request_park_safety.json
```

Expected:

```json
{"status":"planned","plan":{"planner_name":"llm-planner-stub-v1","target_area":"park-north"}}
```

### Phase 3 with an actual OpenAI-compatible API

```bash
set -a
source examples/phase3_llm.env.example
set +a
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

Before running this against a real API, replace:

- `ASSISTANT_LLM_API_KEY`
- `ASSISTANT_LLM_MODEL`
- `ASSISTANT_LLM_API_BASE_URL` if you are not using the default OpenAI-compatible endpoint

Then call:

```bash
curl -X POST http://localhost:8090/assistant/plan \
  -H 'Content-Type: application/json' \
  -d @examples/phase3_request_park_safety.json
```

The expected shape is documented in `examples/phase3_llm_expected_plan.json`.

## Consent VC registration

```bash
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_temperature.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_power.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_person_detected.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_flood_risk_high.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_possible_littering.json
```

Expected: each returns `{"status":"stored", ...}`.

## Simulate publish without MQTT

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/state/sensor/temperature",
    "payload": {
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

## Deny case (purpose not allowed)

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/state/sensor/power",
    "payload": {
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

## MQTT publish examples

```bash
docker exec -i iw3ip-mosquitto mosquitto_pub -h localhost -p 1883 -t homeassistant/state/sensor/temperature -m "$(cat examples/payload_temperature.json)"
docker exec -i iw3ip-mosquitto mosquitto_pub -h localhost -p 1883 -t homeassistant/state/sensor/power -m "$(cat examples/payload_power.json)"
docker exec -i iw3ip-mosquitto mosquitto_pub -h localhost -p 1883 -t homeassistant/event/person_detected -m "$(cat examples/payload_person_detected.json)"
docker exec -i iw3ip-mosquitto mosquitto_pub -h localhost -p 1883 -t homeassistant/event/flood_risk_high -m "$(cat examples/payload_flood_risk_high.json)"
docker exec -i iw3ip-mosquitto mosquitto_pub -h localhost -p 1883 -t homeassistant/event/possible_littering -m "$(cat examples/payload_possible_littering.json)"
```

## Phase 2 event sharing examples

### Flood risk event (allowed)

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/event/flood_risk_high",
    "payload": {
      "event_type":"flood_risk_high",
      "data":{
        "sensor_id":"river-west-01",
        "location":"west_river_area",
        "water_level_m":1.82,
        "severity":"high"
      },
      "ts":"2026-03-08T10:15:05Z",
      "source":"edge_inference"
    },
    "purpose":"disaster_response"
  }'
```

Expected:

```json
{"status":"allowed","dataset_id":"home/event/flood_risk_high"}
```

### Possible littering event (allowed)

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/event/possible_littering",
    "payload": {
      "event_type":"possible_littering",
      "data":{
        "camera_id":"webcam-401",
        "location":"park-north",
        "object_class":"bottle",
        "confidence":0.87
      },
      "ts":"2026-03-08T11:00:00Z",
      "source":"edge_inference"
    },
    "purpose":"community_cleaning"
  }'
```

Expected:

```json
{"status":"allowed","dataset_id":"home/event/possible_littering"}
```

### Example deny case for Phase 2

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/event/possible_littering",
    "payload": {
      "event_type":"possible_littering",
      "data":{
        "camera_id":"webcam-401",
        "location":"park-north",
        "object_class":"bottle",
        "confidence":0.87
      },
      "ts":"2026-03-08T11:01:00Z",
      "source":"edge_inference"
    },
    "purpose":"advertising"
  }'
```

Expected:

```json
{"status":"denied","dataset_id":"home/event/possible_littering","reason":"no_matching_consent"}
```

## Audit log check

```bash
curl http://localhost:8080/audit/logs
```

Expected: records with `action` in `allow`, `deny`, or `send_error`.
