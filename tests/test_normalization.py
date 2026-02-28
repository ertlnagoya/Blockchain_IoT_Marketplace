from schemas.models import normalize


def test_normalize_temperature_state() -> None:
    payload = {
        "entity_id": "sensor.living_room_temperature",
        "state": "24.1",
        "attributes": {"unit_of_measurement": "C"},
        "ts": "2026-02-28T10:00:00Z",
        "source": "home_assistant",
    }
    normalized = normalize("homeassistant/state/sensor/temperature", payload)
    assert normalized.dataset_id == "home/env/temperature"
    assert normalized.message_type == "state"


def test_normalize_person_detected_event() -> None:
    payload = {
        "event_type": "person_detected",
        "data": {"camera_id": "front_door", "confidence": 0.9},
        "ts": "2026-02-28T10:00:20Z",
        "source": "edge_inference",
    }
    normalized = normalize("homeassistant/event/person_detected", payload)
    assert normalized.dataset_id == "home/event/person_detected"
    assert normalized.message_type == "event"
