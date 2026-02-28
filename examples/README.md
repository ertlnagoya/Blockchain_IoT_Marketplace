# Examples

## Consent VC registration

```bash
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_temperature.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_power.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_person_detected.json
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
```

## Audit log check

```bash
curl http://localhost:8080/audit/logs
```

Expected: records with `action` in `allow`, `deny`, or `send_error`.
