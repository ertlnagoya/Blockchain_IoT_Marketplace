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
- **Custom analyzer**: implement a new `SemanticAnalyzer` backend (see section 4).
- **Natural-language layer**: send the accumulated summaries to a local LLM and
  answer a free-text query (connects to the LLM Planner hands-on).

## 4. Deep dive: write a custom SemanticAnalyzer backend

`/semantic/analyze` runs whatever analyzer `SEMANTIC_ANALYZER_BACKEND` selects.
Shipped backends live in `publisher/app/semantic_analyzer.py`:

- `mock` / `stub` — deterministic SIR, no dependencies (the default)
- `vision` / `opencv` — OpenCV Haar-cascade faces + simple heuristics

Adding your own (a different detector, a real VLM, an Apple Vision bridge, …) is
the intended extension point. You implement one method and register one branch.

### 4.1 The interface

```python
from datetime import datetime, timezone

from publisher.app.semantic_analyzer import SemanticAnalyzer, SemanticAnalyzerError
from publisher.app.sir_models import (
    SemanticIntermediateRepresentation,
    PeopleSummary,
    SensitiveRegion,
    SensitiveRegionType,
    BoundingBox,
)


class MyAnalyzer(SemanticAnalyzer):
    # Embedded into the SIR's `analyzer_version` (survives in audit logs).
    name = "my-analyzer/v1"

    def analyze(
        self, *, image_bytes: bytes, source_device_id: str
    ) -> SemanticIntermediateRepresentation:
        try:
            # ... run your model on image_bytes ...
            people = PeopleSummary(count=1)          # identities stays empty
            regions = [
                SensitiveRegion(
                    type=SensitiveRegionType.FACE,
                    confidence=0.9,
                    bbox=BoundingBox(x=0.4, y=0.3, width=0.2, height=0.2),
                    reason="detected face",
                )
            ]
            return SemanticIntermediateRepresentation(
                frame_id="frame-001",
                source_device_id=source_device_id,
                captured_at=datetime.now(timezone.utc),
                scene_summary="one person, indoors",
                people=people,
                sensitive_regions=regions,
                privacy_risk_score=0.4,
                analyzer_version=self.name,
            )
        except Exception as exc:  # never let a raw error escape
            raise SemanticAnalyzerError(str(exc)) from exc
```

### 4.2 Rules that keep it fail-closed

- **Return an SIR, never raw pixels.** The whole point is that the image stays
  in; only the structured meaning leaves.
- **Wrap every failure in `SemanticAnalyzerError`.** A bare `cv2` / decode error
  must not bubble up — the pipeline treats any `SemanticAnalyzerError` as
  "decode failed → treat as private". When unsure, prefer
  `SemanticIntermediateRepresentation.empty(frame_id=..., source_device_id=...,
  analyzer_version=self.name)`.
- **Leave `people.identities` empty.** Identifying individuals is a separate,
  audit-logged concern; an analyzer never fills it in.
- **`analyze()` must be re-entrant.** One instance is shared across requests, so
  don't stash per-request state on `self`.

### 4.3 Register and select it

Add a branch to `SemanticAnalyzer.from_settings` in `semantic_analyzer.py`:

```python
backend = (getattr(settings, "semantic_analyzer_backend", "") or "").lower()
if backend == "myanalyzer":
    return MyAnalyzer()
if backend in ("vision", "opencv"):
    return VisionSemanticAnalyzer()
return MockSemanticAnalyzer()
```

Then start the publisher with your backend selected:

```bash
export SEMANTIC_ANALYZER_BACKEND=myanalyzer
docker compose -f infra/docker-compose.yml up -d publisher
```

Re-run `analyze_frame()` (step 2) and confirm `analyzer_version` in the SIR now
reads `my-analyzer/v1`.

### 4.4 SIR schema quick reference

`SemanticIntermediateRepresentation` (see `publisher/app/sir_models.py`):

| field | type | note |
|---|---|---|
| `frame_id` | str | your identifier for the frame |
| `source_device_id` | str | pass through from the request |
| `captured_at` | datetime | when the frame was captured (required) |
| `scene_summary` | str | short free-text summary |
| `objects` | list[DetectedObject] | `{label, confidence, bbox}` |
| `people` | PeopleSummary | `{count, identities}` — keep `identities` empty |
| `sensitive_regions` | list[SensitiveRegion] | `{type, confidence, bbox, reason}` |
| `events` | list[DetectedEvent] | `{type, description}` |
| `privacy_risk_score` | float 0–1 | drives fail-closed rendering |
| `analyzer_version` | str | set to `self.name` |
