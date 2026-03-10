from __future__ import annotations

import json
from pathlib import Path


EXAMPLES_DIR = Path("examples/ha_demo")
CONSENT_FILES = [
    "consent_temperature.json",
    "consent_power.json",
    "consent_person_detected.json",
    "consent_flood_risk_high.json",
    "consent_possible_littering.json",
    "consent_suspicious_activity.json",
]
PAYLOAD_FILES = [
    "payload_temperature.json",
    "payload_power.json",
    "payload_person_detected.json",
    "payload_flood_risk_high.json",
    "payload_possible_littering.json",
    "payload_suspicious_activity.json",
]


def test_ha_demo_example_files_exist_and_are_valid_json() -> None:
    for filename in CONSENT_FILES + PAYLOAD_FILES:
        data = json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))
        assert isinstance(data, dict)


def test_ha_demo_nodered_flow_exists() -> None:
    data = json.loads((EXAMPLES_DIR / "nodered_flows.json").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 2
