#!/usr/bin/env python3
"""Reference solution for the privacy-compare hands-on.

The same webcam frame is handed to AI in four ways, and the program
records what left the PC each time:

  A  raw image  -> cloud VLM          (baseline: everything leaves)
  B  raw image  -> local VLM (Ollama) (nothing leaves the PC)
  C  faces blurred on the PC -> cloud VLM
  D  meaning extracted on the PC (SIR) -> cloud LLM, text only

"Cloud" is the mock server (mock_cloud_server.py). It saves everything
it receives under received/, so you can check what a real service
would have been given.

Results go to --out-dir: frame.jpg, frame_blurred.jpg, outbound.jsonl
(one line per request that left the PC) and report.md (comparison
table).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

PROMPT = "Describe this image in detail."
TEXT_PROMPT = (
    "The following JSON is a privacy-preserving summary of one camera "
    "frame (counts and region types only, no pixels). In two sentences, "
    "describe the situation and say whether anyone may need attention.\n\n"
)


# ---------------------------------------------------------------- capture
def get_frame(image: str | None, camera_index: int, out_dir: Path) -> bytes:
    """Return JPEG bytes from --image, or capture one frame from the webcam."""
    if image:
        data = Path(image).read_bytes()
    else:
        import cv2  # imported here so the rest works without OpenCV

        cap = cv2.VideoCapture(camera_index)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            raise SystemExit("Could not read from the camera (check --camera-index or use --image).")
        ok, buf = cv2.imencode(".jpg", frame)
        data = buf.tobytes()
    (out_dir / "frame.jpg").write_bytes(data)
    return data


# ------------------------------------------------------------ C: redaction
def redact_faces(jpeg: bytes) -> tuple[bytes, int]:
    """Blur every face found by OpenCV's Haar cascade. Returns (jpeg, faces)."""
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    for (x, y, w, h) in faces:
        # widen the box a little so hair line and chin are covered too
        x0, y0 = max(0, x - w // 8), max(0, y - h // 8)
        x1, y1 = min(img.shape[1], x + w + w // 8), min(img.shape[0], y + h + h // 8)
        img[y0:y1, x0:x1] = cv2.GaussianBlur(img[y0:y1, x0:x1], (99, 99), 30)
    ok, buf = cv2.imencode(".jpg", img)
    return buf.tobytes(), len(faces)


# ---------------------------------------------------- D: meaning extraction
def analyze_locally(publisher_url: str, jpeg: bytes) -> dict:
    """Ask the publisher's local analyzer for the SIR (no pixels returned)."""
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"source_device_id\"\r\n\r\n"
        "laptop-webcam-01\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"frame.jpg\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode() + jpeg + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        publisher_url.rstrip("/") + "/semantic/analyze",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def sir_to_text(sir: dict) -> str:
    """Keep only counts and region types; drop identities, positions, ids."""
    summary = {
        "people_count": (sir.get("people") or {}).get("count", 0),
        "objects": sorted({o.get("label") or o.get("type", "object") for o in sir.get("objects") or []}),
        "sensitive_region_types": sorted({r.get("type", "unknown") for r in sir.get("sensitive_regions") or []}),
        "privacy_risk_score": sir.get("privacy_risk_score"),
    }
    return json.dumps(summary, ensure_ascii=False)


# ----------------------------------------------------------- AI endpoints
def ask_cloud(cloud_url: str, config: str, text: str, image: bytes | None) -> str:
    """Send an OpenAI-style chat request to the (mock) cloud. Returns the answer."""
    content: list[dict] = [{"type": "text", "text": text}]
    if image is not None:
        b64 = base64.b64encode(image).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    body = {"model": "mock-cloud-vlm", "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request(
        cloud_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Exercise-Config": config},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)["choices"][0]["message"]["content"].strip()


def ask_local_vlm(ollama_url: str, model: str, image: bytes) -> str:
    body = {
        "model": model,
        "prompt": PROMPT,
        "images": [base64.b64encode(image).decode()],
        "stream": False,
        # cap the answer length so a CPU-only PC answers in a reasonable time
        "options": {"num_predict": 120},
    }
    req = urllib.request.Request(
        ollama_url.rstrip("/") + "/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp).get("response", "").strip()


# ------------------------------------------------------------------ main
def record(log: list[dict], config: str, destination: str, text: str, image: bytes | None,
           answer: str, seconds: float) -> None:
    log.append({
        "config": config,
        "destination": destination,
        "sent_text_chars": len(text) if destination != "local" else 0,
        "sent_image_bytes": len(image) if (image is not None and destination != "local") else 0,
        "sent_image_sha256": hashlib.sha256(image).hexdigest()[:16] if (image is not None and destination != "local") else "",
        "answer": answer,
        "seconds": round(seconds, 1),
    })


def run(args: argparse.Namespace) -> list[dict]:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame = get_frame(args.image, args.camera_index, out_dir)
    log: list[dict] = []

    # A: raw image to the cloud
    t = time.time()
    answer = ask_cloud(args.cloud_url, "A", PROMPT, frame)
    record(log, "A raw image -> cloud VLM", args.cloud_url, PROMPT, frame, answer, time.time() - t)

    # B: raw image to the local VLM
    t = time.time()
    try:
        answer = ask_local_vlm(args.ollama_url, args.ollama_model, frame)
    except (urllib.error.URLError, OSError) as exc:
        answer = f"(skipped: local VLM not reachable at {args.ollama_url}: {exc})"
    record(log, "B raw image -> local VLM", "local", PROMPT, frame, answer, time.time() - t)

    # C: blur faces on the PC, then send to the cloud
    blurred, faces = redact_faces(frame)
    (out_dir / "frame_blurred.jpg").write_bytes(blurred)
    t = time.time()
    answer = ask_cloud(args.cloud_url, "C", PROMPT, blurred)
    record(log, f"C faces blurred ({faces}) -> cloud VLM", args.cloud_url, PROMPT, blurred, answer, time.time() - t)

    # D: extract meaning on the PC, send text only
    try:
        sir = analyze_locally(args.publisher_url, frame)
    except (urllib.error.URLError, OSError) as exc:
        raise SystemExit(f"publisher not reachable at {args.publisher_url}: {exc}")
    text = TEXT_PROMPT + sir_to_text(sir)
    t = time.time()
    answer = ask_cloud(args.cloud_url, "D", text, None)
    record(log, "D meaning (text only) -> cloud LLM", args.cloud_url, text, None, answer, time.time() - t)

    with open(out_dir / "outbound.jsonl", "w", encoding="utf-8") as f:
        for row in log:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    lines = [
        "| config | left the PC | image bytes sent | text chars sent | seconds | answer |",
        "|---|---|---|---|---|---|",
    ]
    for row in log:
        left = "nothing" if row["destination"] == "local" else ("image + text" if row["sent_image_bytes"] else "text only")
        lines.append(
            f"| {row['config']} | {left} | {row['sent_image_bytes']} | {row['sent_text_chars']} | "
            f"{row['seconds']} | {row['answer'][:120].replace('|', '/')} |"
        )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return log


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare four ways of handing a camera frame to AI")
    parser.add_argument("--image", help="use this JPEG instead of the webcam")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--cloud-url", default="http://localhost:18080")
    parser.add_argument("--publisher-url", default="http://localhost:8080")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--ollama-model", default="moondream")
    parser.add_argument("--out-dir", default="results")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
