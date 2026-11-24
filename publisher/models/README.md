# Vendored models

| File | Source | License |
|---|---|---|
| `face_detection_yunet_2023mar.onnx` | [opencv_zoo `models/face_detection_yunet`](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) (sha256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`) | MIT, see `LICENSE.yunet` |

Used by `publisher/app/face_detector.py` (`FACE_DETECTOR=yunet`, the default).
`FACE_DETECTOR_MODEL_PATH` points the publisher at another copy.
