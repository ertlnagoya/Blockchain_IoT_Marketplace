"""Face detector shared by the opencv redactor and the vision analyzer.

Runs only where OpenCV is installed (the publisher image has it); the
drawn face is the one the C2PA hands-on uses for its Tier 2 blur.
"""
import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from publisher.app import face_detector as fd  # noqa: E402
from publisher.app.image_redactor import RedactionError, _opencv_blur_faces  # noqa: E402


def _drawn_face(w=640, h=480):
    """Sky, a skin-coloured oval with hair, eyes, nose and mouth: the
    same layout as examples/hands_on/c2pa_provenance dummy_scene()."""
    img = np.full((h, w, 3), (235, 205, 170), np.uint8)
    cx, cy, r = 290, 190, 100
    cv2.ellipse(img, (cx, int(cy + r * 0.025)), (int(r * 0.8), int(r * 1.025)), 0, 0, 360, (150, 182, 224), -1)
    cv2.rectangle(img, (int(cx - r * 0.85), int(cy - r * 1.15)), (int(cx + r * 0.85), int(cy - r * 0.55)), (35, 45, 60), -1)
    for sx in (-1, 1):
        ex, ey = int(cx + sx * r * 0.33), int(cy - r * 0.12)
        cv2.ellipse(img, (ex, ey - 6), (20, 11), 0, 0, 360, (90, 110, 150), -1)
        cv2.ellipse(img, (ex, ey - 4), (12, 6), 0, 0, 360, (30, 30, 40), -1)
        cv2.rectangle(img, (ex - 22, ey - 32), (ex + 22, ey - 25), (35, 45, 60), -1)
    nose = np.array([(cx, cy - 5), (cx - 12, cy + 30), (cx + 12, cy + 30)], np.int32)
    cv2.fillPoly(img, [nose], (115, 140, 190))
    cv2.ellipse(img, (cx, cy + 55), (30, 7), 0, 0, 360, (70, 70, 150), -1)
    return cv2.GaussianBlur(img, (5, 5), 1)


def _jpeg(img):
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    assert ok
    return buf.tobytes()


def test_vendored_yunet_model_is_the_upstream_file():
    import hashlib

    digest = hashlib.sha256(fd.DEFAULT_MODEL_PATH.read_bytes()).hexdigest()
    # opencv_zoo models/face_detection_yunet/face_detection_yunet_2023mar.onnx (LFS oid)
    assert digest == "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


def test_unknown_backend_and_missing_model_raise():
    with pytest.raises(fd.FaceDetectorError):
        fd.FaceDetector("dlib")
    with pytest.raises(fd.FaceDetectorError):
        fd.FaceDetector("yunet", model_path="/nonexistent/yunet.onnx")


def test_yunet_finds_the_drawn_face_and_nothing_on_a_blank_frame():
    det = fd.get_face_detector("yunet")
    assert det is fd.get_face_detector("yunet")  # built once per process
    faces = det.detect(_drawn_face())
    assert len(faces) == 1
    x, y, w, h, score = faces[0]
    assert 180 < x + w / 2 < 400 and 0.9 <= score <= 1.0
    assert det.detect(np.zeros((480, 640, 3), np.uint8)) == []


def test_boxes_are_clipped_to_the_frame():
    img = _drawn_face()[:, 200:]  # face cut by the left edge
    for x, y, w, h, _ in fd.get_face_detector("yunet").detect(img):
        assert x >= 0 and y >= 0 and x + w <= img.shape[1] and y + h <= img.shape[0]


def test_redactor_blur_hides_the_face_from_the_same_detector():
    """The check a receiver or auditor runs: the detector that chose the
    regions finds no face in the redacted output."""
    out = _opencv_blur_faces(_jpeg(_drawn_face()), ext=".jpg", detector="yunet")
    img = cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_COLOR)
    assert fd.get_face_detector("yunet").detect(img) == []


def test_redactor_reports_a_detector_error_as_redaction_error():
    with pytest.raises(RedactionError):
        _opencv_blur_faces(_jpeg(_drawn_face()), ext=".jpg", detector="dlib")


@pytest.mark.skipif(not hasattr(cv2, "CascadeClassifier"), reason="OpenCV 5 has no Haar cascade")
def test_haar_backend_still_available():
    faces = fd.get_face_detector("haar").detect(_drawn_face())
    assert all(s == fd.HAAR_CONFIDENCE for *_, s in faces)


def test_vision_analyzer_uses_the_configured_detector():
    from publisher.app.semantic_analyzer import SemanticAnalyzer

    class _S:
        semantic_analyzer_backend = "vision"
        face_detector = "yunet"
        face_detector_model_path = ""

    a = SemanticAnalyzer.from_settings(_S())
    sir = a.analyze(image_bytes=_jpeg(_drawn_face()), source_device_id="cam-1")
    faces = [r for r in sir.sensitive_regions if r.type.value == "face"]
    assert sir.analyzer_version == "vision-opencv/v2-yunet"
    assert len(faces) == 1 and faces[0].confidence >= 0.9
    assert sir.people.count == 1
