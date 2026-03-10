from examples.ha_demo.run_phase3_from_ingest import (
    build_execute_request,
    build_plan_request,
    ingest_records_to_observed_events,
)


def test_ingest_records_to_observed_events_filters_states_and_maps_location() -> None:
    ingested = [
        {
            "dataset_id": "home/env/temperature",
            "payload": {
                "ts": "2026-03-10T10:00:00Z",
                "payload": {
                    "state": "24.5",
                },
            },
        },
        {
            "dataset_id": "home/event/possible_littering",
            "payload": {
                "ts": "2026-03-10T10:01:00Z",
                "payload": {
                    "event_type": "possible_littering",
                    "data": {
                        "location": "park-north",
                        "confidence": 0.88,
                    },
                },
            },
        },
        {
            "dataset_id": "home/event/suspicious_activity",
            "payload": {
                "ts": "2026-03-10T10:02:00Z",
                "payload": {
                    "event_type": "suspicious_activity",
                    "data": {
                        "location": "station-front",
                        "activity": "loitering",
                    },
                },
            },
        },
    ]

    observed = ingest_records_to_observed_events(ingested, target_area="park-north")

    assert len(observed) == 1
    assert observed[0]["event_type"] == "possible_littering"
    assert observed[0]["location"] == "park-north"


def test_build_execute_request_includes_observed_events() -> None:
    ingested = [
        {
            "dataset_id": "home/event/suspicious_activity",
            "payload": {
                "ts": "2026-03-10T10:02:00Z",
                "payload": {
                    "event_type": "suspicious_activity",
                    "data": {
                        "location": "park-north",
                        "activity": "loitering",
                    },
                },
            },
        },
    ]

    body = build_execute_request(ingested, request_text="test request", target_area="park-north")

    assert body["request_text"] == "test request"
    assert len(body["observed_events"]) == 1
    assert body["observed_events"][0]["event_type"] == "suspicious_activity"


def test_build_plan_request_contains_only_request_text() -> None:
    body = build_plan_request("plan only request")

    assert body == {"request_text": "plan only request"}
