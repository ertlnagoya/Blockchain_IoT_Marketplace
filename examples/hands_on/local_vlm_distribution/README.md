# local_vlm_distribution — Enrich camera data with a local model and distribute it

Exercise programs for the Part 3 hands-on
[Enrich camera data with a local VLM](https://www.ertl.jp/iw3ip.github.io/hands-on/local-vlm-distribution/).

The goal: take a webcam frame, let a **local model** on the PC turn it into
structured "meaning" (never leaking the raw pixels), and push that AI-derived
data into the platform's distribution pipeline.

## Files

- `answer_program.py` — reference solution
- `problem_program.py` — exercise version with two `TODO`s
- `fixtures/consent_webcam.json` — a consent used by the optional `--distribute` step

## 0. Big picture — how the program maps to the platform

```
 webcam frame (snapshot.jpg)
        │
        │  analyze_frame()  ── POST /semantic/analyze ─────────────▶ SIR (JSON)
        │                     (local model: people / faces / regions)
        │
        │  summarize_sir()  ── read the SIR, print a one-line summary
        │
        └─ distribute_frame() (optional, --distribute)
               ├─ POST /consents           (allow the dataset)
               ├─ upload_media()  ── POST /media/upload ── image_url
               └─ post /simulate/publish   (event carries image_url)
                     │
                     └─ with `--profile vlm`, the publisher runs the local VLM
                        and attaches description_full / description_summary to
                        the row (retrieved per trust tier in the DataUserVC
                        hands-on).
```

The three functions you should read first, in order:

1. `analyze_frame(base_url, image_path, source_device_id)` — sends the frame to
   `POST /semantic/analyze` (multipart) and returns the **Semantic Intermediate
   Representation (SIR)**: a structured JSON describing what the local model saw
   (`people.count`, `objects`, `sensitive_regions`, `scene_summary`,
   `privacy_risk_score`). The endpoint **never echoes the raw pixels** — that is
   the whole point: the meaning leaves, the image does not.
2. `summarize_sir(sir)` — reads that JSON and prints a one-line human summary.
3. `distribute_frame(...)` — registers a consent, uploads the frame, and
   publishes an event that carries the `image_url` into the platform.

`/semantic/analyze` needs no wallet and no VC, so step 1 works out of the box.
The default analyzer is a deterministic stub; set `SEMANTIC_ANALYZER_BACKEND=vision`
on the publisher for real OpenCV face/region detection.

## 1. Prepare a frame

Capture one frame from a USB webcam (or use any JPEG as `snapshot.jpg`):

```python
import cv2
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
cap.release()
if ok:
    cv2.imwrite("snapshot.jpg", frame)
```

## 2. Exercise: fill in the two TODOs

Start the stack (see the hands-on page; add `--profile vlm` for the VLM step),
then run the exercise version:

```bash
python examples/hands_on/local_vlm_distribution/problem_program.py \
  --base-url http://localhost:8080 \
  --image snapshot.jpg
```

You implement:

- **TODO 1 `summarize_sir()`** — read the SIR and return a one-line summary.
- **TODO 2 `build_event()`** — build the event payload that carries the frame
  (`image_url`) into the platform.

Compare with `answer_program.py`. Expected output (SIR values depend on the
image and analyzer):

```text
[analyze] SIR:
{
  "frame_id": "...",
  "people": {"count": 1, "identities": []},
  "objects": [...],
  "sensitive_regions": [...],
  "scene_summary": "...",
  "privacy_risk_score": 0.4,
  "analyzer_version": "..."
}
[summary] people=1, objects=2, sensitive_regions=1, privacy_risk=0.4 | ...
```

Then distribute the frame (needs a running stack; `--profile vlm` optional):

```bash
python examples/hands_on/local_vlm_distribution/answer_program.py \
  --base-url http://localhost:8080 \
  --image snapshot.jpg \
  --distribute
```

`[distribute]` should report the publish result (an `allow` outcome). Per-tier
retrieval of `description_full` / `description_summary` is covered in the
DataUserVC tiered-access hands-on.

## 3. Advanced: add a feature from scratch

Pick one and implement it yourself (no template):

- **Richer summary**: extend `summarize_sir()` to list each
  `sensitive_regions[].type` and warn when `privacy_risk_score` is high.
- **Frame sampling**: capture N frames on a timer, analyze each, and only
  distribute the one with the highest `privacy_risk_score` (or a chosen object).
- **New derived field**: add a field to the event `data` computed from the SIR
  (e.g. `people_count`) and confirm it survives publish.
- **Custom analyzer**: implement a new `SemanticAnalyzer` backend in
  `publisher/app/semantic_analyzer.py` (register it in `from_settings`) and point
  `SEMANTIC_ANALYZER_BACKEND` at it.
- **Natural-language layer**: send the accumulated summaries to a local LLM and
  answer a free-text query (connects to the LLM Planner hands-on).
