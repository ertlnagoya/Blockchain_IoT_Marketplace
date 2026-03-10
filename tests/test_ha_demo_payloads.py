from __future__ import annotations

import json
from pathlib import Path

from schemas.models import normalize


EXAMPLES_DIR = Path("examples/ha_demo")


CASES = [
    (
        "homeassistant/state/sensor/temperature",
        "payload_temperature.json",
        "home/env/temperature",
        "state",
    ),
    (
        "homeassistant/state/sensor/power",
        "payload_power.json",
        "home/energy/power",
        "state",
    ),
    (
        "homeassistant/event/person_detected",
        "payload_person_detected.json",
        "home/event/person_detected",
        "event",
    ),
    (
        "homeassistant/event/flood_risk_high",
        "payload_flood_risk_high.json",
        "home/event/flood_risk_high",
        "event",
    ),
    (
        "homeassistant/event/possible_littering",
        "payload_possible_littering.json",
        "home/event/possible_littering",
        "event",
    ),
]


def _load_json(name: str) -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def test_ha_demo_payloads_normalize_to_expected_dataset_ids() -> None:
    for topic, filename, dataset_id, message_type in CASES:
        normalized = normalize(topic, _load_json(filename))
        assert normalized.dataset_id == dataset_id
        assert normalized.message_type == message_type
        assert normalized.source == "home_assistant_demo"
