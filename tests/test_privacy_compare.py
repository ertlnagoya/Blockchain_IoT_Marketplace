"""privacy_compare hands-on: the mock cloud records what it receives, and the
text-only configuration (D) sends no pixels."""
from __future__ import annotations

import importlib.util
import json
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "examples" / "hands_on" / "privacy_compare"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _start_mock(tmp_path):
    mock = _load("mock_cloud_server")
    server = mock.serve(0, tmp_path / "received", None, "moondream")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_mock_cloud_records_image_and_text(tmp_path):
    answer = _load("answer_program")
    server, url = _start_mock(tmp_path)
    try:
        reply = answer.ask_cloud(url, "A", "describe", b"\xff\xd8fake-jpeg\xff\xd9")
    finally:
        server.shutdown()
    record = json.loads((tmp_path / "received" / "001.json").read_text())
    assert record["tag"] == "A"
    assert record["image_bytes"] == len(b"\xff\xd8fake-jpeg\xff\xd9")
    assert (tmp_path / "received" / record["image_files"][0]).read_bytes().startswith(b"\xff\xd8")
    assert "image" in reply


def test_text_only_config_sends_no_image(tmp_path):
    answer = _load("answer_program")
    server, url = _start_mock(tmp_path)
    sir = {
        "frame_id": "f-1",
        "people": {"count": 1, "identities": ["alice"]},
        "objects": [{"label": "person", "bbox": [1, 2, 3, 4]}],
        "sensitive_regions": [{"type": "face", "bbox": [1, 2, 3, 4], "confidence": 0.9}],
        "privacy_risk_score": 0.9,
    }
    text = answer.sir_to_text(sir)
    try:
        answer.ask_cloud(url, "D", text, None)
    finally:
        server.shutdown()
    record = json.loads((tmp_path / "received" / "001.json").read_text())
    assert record["image_bytes"] == 0 and record["image_files"] == []
    assert json.loads(text) == {
        "people_count": 1,
        "objects": ["person"],
        "sensitive_region_types": ["face"],
        "privacy_risk_score": 0.9,
    }
    for leaked in ("alice", "bbox", "f-1"):
        assert leaked not in record["text"]


def test_redact_faces_blurs_the_face_found_by_yunet():
    """Config C: the reference redact_faces() finds the drawn face with YuNet
    and blurs it so the detector no longer finds it."""
    import pytest

    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    from test_face_detector import _drawn_face

    answer = _load("answer_program")
    ok, buf = cv2.imencode(".jpg", _drawn_face())
    blurred, faces = answer.redact_faces(buf.tobytes())
    assert faces == 1
    again, faces_after = answer.redact_faces(blurred)
    assert faces_after == 0
