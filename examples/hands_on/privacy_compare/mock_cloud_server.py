#!/usr/bin/env python3
"""Mock "cloud AI" server for the privacy-compare hands-on.

It speaks a minimal OpenAI-compatible ``POST /v1/chat/completions`` and,
above all, **records exactly what it received**: every request is saved
under ``received/`` (the text as JSON, any image as a .jpg file) so that
learners can open the folder and see what a real cloud service would
have been given.

Answers:
  * By default the server returns a canned answer that only states what
    it received (it does not look at the image).
  * With ``--ollama-url`` it forwards the request to a local Ollama model
    and returns that model's answer, so the "cloud" produces realistic
    descriptions while everything still stays on the PC.

Standard library only, so it runs without installing anything.

Usage:
  python3 mock_cloud_server.py --port 18080
  python3 mock_cloud_server.py --port 18080 \
      --ollama-url http://localhost:11434 --ollama-model moondream
"""
from __future__ import annotations

import argparse
import base64
import json
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


def split_messages(messages: list) -> tuple[str, list[bytes]]:
    """Return (all text, list of decoded images) from OpenAI-style messages."""
    texts: list[str] = []
    images: list[bytes] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            texts.append(content)
            continue
        for part in content or []:
            if part.get("type") == "text":
                texts.append(part.get("text", ""))
            elif part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url", "")
                if url.startswith("data:") and "," in url:
                    images.append(base64.b64decode(url.split(",", 1)[1]))
    return "\n".join(texts), images


def ollama_generate(ollama_url: str, model: str, prompt: str, images: list[bytes]) -> str:
    # cap the answer length so a CPU-only PC answers in a reasonable time
    body = {"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": 120}}
    if images:
        body["images"] = [base64.b64encode(img).decode() for img in images]
    req = urllib.request.Request(
        ollama_url.rstrip("/") + "/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp).get("response", "").strip()


def canned_answer(text: str, images: list[bytes]) -> str:
    if images:
        size_kb = sum(len(img) for img in images) / 1024
        return (
            f"(mock) Received {len(images)} image(s), {size_kb:.0f} KB in total, "
            f"and {len(text)} characters of text. A real cloud service could "
            "analyze everything visible in the image."
        )
    return (
        f"(mock) Received {len(text)} characters of text and no image. "
        "A real cloud service only sees this text."
    )


class Recorder:
    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._count = len(list(self.out_dir.glob("*.json")))

    def save(self, text: str, images: list[bytes], tag: str) -> dict:
        with self._lock:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            self._count += 1
            stem = f"{self._count:03d}"
        image_files = []
        for i, img in enumerate(images):
            name = f"{stem}_image{i + 1}.jpg"
            (self.out_dir / name).write_bytes(img)
            image_files.append(name)
        record = {
            "id": stem,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "tag": tag,
            "text": text,
            "text_chars": len(text),
            "image_files": image_files,
            "image_bytes": sum(len(img) for img in images),
        }
        (self.out_dir / f"{stem}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return record


def make_handler(recorder: Recorder, ollama_url: str | None, ollama_model: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):  # keep the console readable
            return

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok", "service": "mock-cloud-ai"})
            else:
                self._send(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self._send(404, {"error": "not_found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            text, images = split_messages(body.get("messages") or [])
            tag = self.headers.get("X-Exercise-Config", "")
            record = recorder.save(text, images, tag)
            print(
                f"[cloud] #{record['id']} {tag or '-'}: "
                f"image {record['image_bytes']} bytes, text {record['text_chars']} chars"
                f" -> saved to {recorder.out_dir.name}/",
                flush=True,
            )
            started = time.time()
            if ollama_url:
                try:
                    answer = ollama_generate(ollama_url, ollama_model, text, images)
                except Exception as exc:  # noqa: BLE001 - report and keep serving
                    self._send(502, {"error": f"ollama_failed: {exc}"})
                    return
            else:
                answer = canned_answer(text, images)
            self._send(
                200,
                {
                    "id": f"mock-{record['id']}",
                    "object": "chat.completion",
                    "model": body.get("model", "mock-cloud"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": answer},
                            "finish_reason": "stop",
                        }
                    ],
                    "x_mock": {
                        "received_id": record["id"],
                        "elapsed_sec": round(time.time() - started, 2),
                    },
                },
            )

    return Handler


def serve(port: int, out_dir: Path, ollama_url: str | None, ollama_model: str) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Recorder(out_dir), ollama_url, ollama_model))
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock cloud AI that records what it receives")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--out-dir", default=str(HERE / "received"))
    parser.add_argument("--ollama-url", default=None, help="forward requests to this Ollama (optional)")
    parser.add_argument("--ollama-model", default="moondream")
    args = parser.parse_args()
    server = serve(args.port, Path(args.out_dir), args.ollama_url, args.ollama_model)
    mode = f"forwarding to {args.ollama_url} ({args.ollama_model})" if args.ollama_url else "canned answers"
    print(f"[cloud] mock cloud AI on http://127.0.0.1:{args.port} ({mode})", flush=True)
    print(f"[cloud] received data is saved under {args.out_dir}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
