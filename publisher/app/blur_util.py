"""Gaussian blur whose strength follows the size of the region.

A fixed kernel (the former 51x51) under-blurs large faces: in the
iw3ip-research detectability study (experiment C, 2026-11-24) a face
recogniser (SFace) still identified 37.8% of LFW probes at a face width
of 131 px and 80.6% at 192 px after a 51x51 blur, and the Haar cascade
re-detected the blurred face in 28% of WIDER FACE frames. With the
kernel at least as wide as the region, rank-1 identification fell to
about 1.5% at every width.

Kernels above ``_MAX_DIRECT_KSIZE`` are applied to a downscaled copy and
scaled back, which gives the same identification rate in that study
(1.4-1.7%) while keeping a 1000 px region at ~13 ms instead of ~8 s.
"""
from __future__ import annotations

DEFAULT_MIN_KSIZE = 51
_MAX_DIRECT_KSIZE = 101


def region_ksize(width: int, min_ksize: int = DEFAULT_MIN_KSIZE) -> int:
    """Odd kernel size, at least ``min_ksize`` and at least the region width."""
    k = max(int(min_ksize), int(width))
    return k if k % 2 == 1 else k + 1


def blur_region(roi, min_ksize: int = DEFAULT_MIN_KSIZE):
    """Return a blurred copy of ``roi`` (an OpenCV BGR array)."""
    import cv2  # type: ignore[import-not-found]

    h, w = roi.shape[:2]
    k = region_ksize(w, min_ksize)
    if k <= _MAX_DIRECT_KSIZE:
        return cv2.GaussianBlur(roi, (k, k), 0)
    f = _MAX_DIRECT_KSIZE / k
    small = cv2.resize(
        roi,
        (max(1, round(w * f)), max(1, round(h * f))),
        interpolation=cv2.INTER_AREA,
    )
    small = cv2.GaussianBlur(small, (_MAX_DIRECT_KSIZE, _MAX_DIRECT_KSIZE), 0)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
