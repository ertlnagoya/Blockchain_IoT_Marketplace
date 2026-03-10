# Home Assistant Demo Examples

This directory contains the sample payloads and consents used by the Home Assistant demo simulator.

## Files

- `consent_temperature.json`
- `consent_power.json`
- `consent_person_detected.json`
- `consent_flood_risk_high.json`
- `consent_possible_littering.json`
- `payload_temperature.json`
- `payload_power.json`
- `payload_person_detected.json`
- `payload_flood_risk_high.json`
- `payload_possible_littering.json`
- `nodered_flows.json`

## Intended use

1. start `docker compose -f infra/docker-compose.yml --profile ha-demo up --build -d`
2. open Home Assistant at `http://localhost:8123`
3. add the MQTT integration with host `mosquitto` and port `1883`
4. register the consent files into the publisher
5. run Home Assistant scripts or use the payload files for direct testing

## Register sample consents

```bash
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_temperature.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_power.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_person_detected.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_flood_risk_high.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/ha_demo/consent_possible_littering.json
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
