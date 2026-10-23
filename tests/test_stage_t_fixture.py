"""The Stage T provider fixture must be a decodable JPEG.

Face blur (OpenCV) and the VLM both decode ``image_url``; a JPEG without
image data makes them fail with ``redaction_unavailable`` /
``vlm_unavailable`` on the hands-on's default run.
"""
from examples.hands_on.data_user_vc_tiered.provider_with_media import (
    _TINY_JPEG,
    _ensure_fixture,
)


def test_fixture_has_jpeg_segments() -> None:
    assert _TINY_JPEG.startswith(b"\xff\xd8")  # SOI
    assert b"\xff\xc0" in _TINY_JPEG  # baseline SOF
    assert b"\xff\xda" in _TINY_JPEG  # SOS: the image data
    assert _TINY_JPEG.endswith(b"\xff\xd9")  # EOI


def test_fixture_decodes_with_pillow_when_available() -> None:
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - optional dependency
        return
    import io

    with Image.open(io.BytesIO(_TINY_JPEG)) as im:
        im.load()
        assert im.size == (16, 16)


def test_ensure_fixture_replaces_stale_file(tmp_path) -> None:
    path = tmp_path / "stage_t_demo.jpg"
    path.write_bytes(b"old undecodable bytes")
    _ensure_fixture(path, _TINY_JPEG)
    assert path.read_bytes() == _TINY_JPEG
