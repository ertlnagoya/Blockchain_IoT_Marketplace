# privacy_compare — What leaves the PC when you hand a camera frame to AI?

Exercise programs for the Part 3 hands-on
[Protect camera images before handing them to AI](https://www.ertl.jp/iw3ip.github.io/hands-on/privacy-compare/).

The same webcam frame is handed to AI in four ways, and the program records
what left the PC each time.

| Config | What leaves the PC | Where it goes |
|---|---|---|
| A | the raw image | cloud VLM |
| B | nothing | local VLM (Ollama) |
| C | the image with faces blurred on the PC | cloud VLM |
| D | text only: counts and region types extracted on the PC | cloud LLM |

The "cloud" is `mock_cloud_server.py`, a stand-in that speaks a minimal
OpenAI-compatible `POST /v1/chat/completions`. It saves **everything it
receives** under `received/` (text as JSON, images as .jpg), so you can open the
folder and see exactly what a real cloud service would have been given. With
`--ollama-url` it forwards each request to a local Ollama model to produce
realistic answers; without it, it returns a canned answer.

## Files

- `mock_cloud_server.py` — mock cloud AI (standard library only)
- `answer_program.py` — reference solution
- `problem_program.py` — exercise version with two `TODO`s
  (`redact_faces()` and `sir_to_text()`)

## Requirements

- Python 3 with `opencv-python<5` (`pip install "opencv-python<5"`).
  OpenCV 5 removed the Haar-cascade face detector used here.
- A local Ollama with a vision model (default `moondream`), reachable at
  `http://localhost:11434`, for config B and for realistic mock answers.
  For example:

  ```bash
  docker run -d --name iw3ip-ollama -p 11434:11434 -v iw3ip_ollama:/root/.ollama ollama/ollama
  docker exec iw3ip-ollama ollama pull moondream
  ```

- The publisher running on `http://localhost:8080` (for config D's
  `/semantic/analyze`). Start it with `SEMANTIC_ANALYZER_BACKEND=vision` to use
  the OpenCV analyzer; the default analyzer returns a fixed mock result.

## Run

```bash
# terminal 1: the mock cloud
python3 mock_cloud_server.py --port 18080 \
  --ollama-url http://localhost:11434 --ollama-model moondream

# terminal 2: the comparison (webcam, or --image <jpeg>)
python3 answer_program.py --out-dir results
```

Outputs:

- `results/frame.jpg`, `results/frame_blurred.jpg` — the frame and its blurred copy
- `results/outbound.jsonl` — one line per request: what was sent and the answer
- `results/report.md` — the comparison table
- `received/` (next to the mock server) — what the "cloud" actually received

With a CPU-only PC the local model takes from several seconds to a few minutes
per request. Answers are capped at 120 tokens.

## Safety

Only photograph people who agreed to it (yourself, or a printed / synthetic
face). Do not point the camera at other people, ID cards, or screens with
personal data. The mock server keeps everything on the PC; delete `received/`
and `results/` when you are done.
