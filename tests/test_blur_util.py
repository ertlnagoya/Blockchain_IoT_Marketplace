"""Kernel scaling of the face / region blur (publisher/app/blur_util.py)."""
import pytest

from publisher.app.blur_util import blur_region, region_ksize

np = pytest.importorskip("numpy")
cv2 = pytest.importorskip("cv2")


def test_region_ksize_is_odd_and_grows_with_width():
    assert region_ksize(20) == 51          # never below the former fixed kernel
    assert region_ksize(131) == 131
    assert region_ksize(132) == 133
    assert region_ksize(40, min_ksize=60) == 61


def _texture(n):
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, (n, n, 3), dtype=np.uint8)


def _sharpness(img):
    return float(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def test_large_region_is_blurred_harder_than_fixed_51():
    roi = _texture(192)
    fixed = cv2.GaussianBlur(roi, (51, 51), 0)
    scaled = blur_region(roi)
    assert scaled.shape == roi.shape
    assert _sharpness(scaled) < _sharpness(fixed) / 4


def test_downscaled_path_matches_direct_blur():
    roi = _texture(301)                    # kernel 301 > 101 -> downscaled path
    fast = blur_region(roi).astype(np.int16)
    direct = cv2.GaussianBlur(roi, (301, 301), 0).astype(np.int16)
    assert fast.shape == direct.shape
    assert float(np.abs(fast - direct).mean()) < 2.0


def test_small_region_keeps_former_behaviour():
    roi = _texture(40)
    assert np.array_equal(blur_region(roi), cv2.GaussianBlur(roi, (51, 51), 0))
