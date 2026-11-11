"""Stage P (C2PA provenance) P3: follow a VLM summary back to the signed capture.

A Tier 1 (summary) recipient gets only the VLM's summary text. P3 lets
that recipient check where the text came from:

1. The gateway (this script) signs a capture and uploads it; the
   publisher verifies it (P1).
2. The event is published. The publisher runs the VLM on the capture,
   blurs it for Tier 2 (P2) and renders the summary text into an SVG
   "summary card" that it signs: the capture is an ``inputTo``
   ingredient (camera and sensor assertions redacted), the action is
   ``c2pa.created`` of AI-generated media, and
   ``jp.ertl.iw3ip.derivation`` holds the sha256 of the exact text, the
   model and the prompt hash.
3. A software wallet obtains a ViewerToken for the summary tier and
   reads /platform/data: the summary text and ``provenance`` only.
4. The script, as that recipient, downloads the card, validates it,
   compares the text hash, and follows the ingredient to the manifest
   label the ProvenanceToken anchors on chain.
5. It changes one word of the text and one byte of the card, and checks
   that both are caught.

Usage (publisher started with infra/docker-compose.c2pa.yml):
    uv run --no-project --with c2pa-python --with pillow --with cryptography \\
        python examples/hands_on/c2pa_provenance/p3_vlm_summary.py

With a real VLM (VLM_BACKEND=ollama) the publish call waits for the
model; raise --timeout if the CPU is slow. Exit code is 0 only when
every check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import urllib.parse
from pathlib import Path

import c2pa

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p0_sign_verify as p0  # noqa: E402
import p1p2_publisher_flow as flow  # noqa: E402

AI_MEDIA = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"


def read_card(data: bytes, ctx: c2pa.Context) -> tuple[str, dict]:
    """Validation state and manifest store of an SVG card."""
    with c2pa.Reader("image/svg+xml", io.BytesIO(data), context=ctx) as reader:
        return reader.get_validation_state(), json.loads(reader.json())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--image", type=Path, help="sign this JPEG/PNG instead of the drawn scene")
    src.add_argument("--webcam", action="store_true", help="capture one frame with OpenCV")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--publisher", default="http://localhost:8080")
    parser.add_argument("--rpc", default="http://localhost:8545", help="Hardhat node for the token check")
    parser.add_argument("--certs", type=Path, default=HERE / "certs")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--camera-id", default="cam01")
    parser.add_argument("--timeout", type=float, default=900,
                        help="seconds to wait for the publish call (the VLM runs inside it)")
    args = parser.parse_args()
    base = args.publisher.rstrip("/")
    if not (args.certs / "publisher_chain.pem").exists():
        sys.exit(f"{args.certs}/publisher_chain.pem not found; run make_test_certs.py first")
    args.out.mkdir(parents=True, exist_ok=True)
    checks = p0.Checks()
    ctx = c2pa.Context(c2pa.Settings.from_dict({
        "verify": {"verify_trust": True},
        "trust": {"user_anchors": (args.certs / "ca.pem").read_text()},
    }))

    # 1. capture, signed by the gateway and verified by the publisher
    print(f"c2pa-python {p0.version('c2pa-python')} / c2pa-rs {c2pa.sdk_version()}")
    capture = flow.sign_capture(p0.capture_image(args), certs=args.certs, camera_id=args.camera_id)
    (args.out / "p3_capture.jpg").write_bytes(capture)
    status, up = flow.upload(base, capture, "capture.jpg")
    cap = up.get("c2pa") or {}
    checks.expect(status == 200 and cap.get("validation_state") == "Trusted",
                  "capture is Trusted at the publisher", f"{status} {cap.get('validation_state')}")

    # 2. publish; the VLM, the blur and the summary card run inside this call
    started = time.monotonic()
    pub, row = flow.publish_event(base, up["url"], timeout=args.timeout)
    took = time.monotonic() - started
    warnings = row.get("processing_warnings") or []
    checks.expect(pub.get("status") == "allowed", "event is published", f"{took:.1f}s")
    checks.expect(bool(row.get("description_summary")) and "vlm_unavailable" not in warnings,
                  "VLM wrote a summary", f"model={row.get('description_model')}")
    checks.expect("provenance_summary_unavailable" not in warnings
                  and bool((row.get("provenance") or {}).get("summary_card_url")),
                  "publisher signed the summary card", f"warnings={warnings}")

    # 3. what the summary tier receives
    token, views = flow.viewer_token(base, flow.TIERS["summary"],
                                     f"{up['sha256']}-p3-{time.time()}")
    _, raw = flow.http("GET", base + "/platform/data?" + urllib.parse.urlencode(
        {"dataset_id": flow.DATASET}), headers={"Authorization": f"Bearer {token}"})
    rows = [r for r in json.loads(raw)["rows"]
            if (r.get("provenance") or {}).get("manifest_label") == cap.get("manifest_label")]
    got = rows[-1] if rows else {}
    prov = got.get("provenance") or {}
    text = got.get("description_summary") or ""
    print(f"  summary tier views={views}")
    print(f"  keys={sorted(got.keys())}")
    print(f"  provenance={sorted(prov.keys())}")
    print(f"  text: {text}")
    checks.expect(bool(text) and not ({"image_url", "image_url_redacted", "description_full"} & got.keys()),
                  "summary tier gets the text but no image and no full description")
    checks.expect(bool(prov.get("summary_card_url")) and "signer" not in prov,
                  "summary tier gets the card URL but not the gateway signer")

    # 4. check the card as the recipient
    _, card = flow.http("GET", prov.get("summary_card_url", "")) if prov.get("summary_card_url") else (0, b"")
    (args.out / "p3_summary_card.svg").write_bytes(card)
    state, store = read_card(card, ctx) if card else ("-", {})
    active = store.get("manifests", {}).get(store.get("active_manifest"), {})
    checks.expect(state == "Trusted" and active.get("signature_info", {}).get("common_name") == "iw3ip-publisher",
                  "card is Trusted and signed by the publisher", state)
    checks.expect(bool(store.get("active_manifest"))
                  and store.get("active_manifest") == prov.get("summary_manifest_label"),
                  "card manifest matches provenance.summary_manifest_label")
    derivation = next((a["data"] for a in active.get("assertions", [])
                       if a["label"] == "jp.ertl.iw3ip.derivation"), {})
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    checks.expect(derivation.get("text_sha256") == text_sha == prov.get("derived_sha256"),
                  "sha256 of the received text matches the signed text_sha256",
                  f"model={derivation.get('model')} prompt={str(derivation.get('prompt_sha256'))[:12]}...")
    actions = next((a["data"]["actions"] for a in active.get("assertions", [])
                    if a["label"].startswith("c2pa.actions")), [])
    first = actions[0] if actions else {}
    checks.expect(first.get("action") == "c2pa.created" and first.get("digitalSourceType") == AI_MEDIA,
                  "card says the text is AI-generated", (first.get("softwareAgent") or {}).get("name", ""))
    ingredients = active.get("ingredients", [])
    ing_label = (ingredients[0].get("active_manifest") if ingredients else None)
    checks.expect(len(ingredients) == 1 and ingredients[0].get("relationship") == "inputTo"
                  and ing_label == cap.get("manifest_label"),
                  "card's input is the signed capture", str(ing_label))
    cap_m = store.get("manifests", {}).get(cap.get("manifest_label"), {})
    remaining = [a["label"] for a in cap_m.get("assertions", [])]
    leaked = [lab for lab in p0.REDACT_LABELS
              if lab in remaining or (lab == "c2pa.thumbnail.claim" and "thumbnail" in cap_m)]
    hits = card.count(args.camera_id.encode())
    checks.expect(bool(cap_m) and not leaked and hits == 0,
                  "capture thumbnail / camera / sensor are redacted from the card", f"leaked={leaked} hits={hits}")

    # the ingredient is the manifest the ProvenanceToken anchors
    if prov.get("token_id") is not None:
        meta = flow.token_uri(args.rpc, prov["token_contract"], prov["token_id"])
        checks.expect(meta.get("manifestLabel") == ing_label,
                      "ProvenanceToken anchors the card's input manifest", f"token #{prov['token_id']}")
    else:
        checks.expect(False, "ProvenanceToken was minted",
                      "no token_id; set PROVENANCE_TOKEN_ADDRESS and start the Hardhat node")

    # 5. tampering
    words = text.split()
    if words:
        words[-1] = "elsewhere."
    altered = " ".join(words)
    checks.expect(bool(derivation.get("text_sha256"))
                  and hashlib.sha256(altered.encode()).hexdigest() != derivation.get("text_sha256"),
                  "a changed word in the text no longer matches the card", altered[-40:])
    i = card.find(b"<text x=\"16\" y=\"56\">")
    bad = bytearray(card)
    if i >= 0:
        bad[i + 20] ^= 0x20  # flip the case of the first letter of the summary
    state_bad, _ = read_card(bytes(bad), ctx) if i >= 0 else ("-", {})
    checks.expect(state_bad == "Invalid", "a changed letter in the card is Invalid", state_bad)

    _, raw = flow.http("GET", base + "/audit/logs?limit=200")
    reasons = [r["reason"] for r in json.loads(raw) if r["raw_topic"] == "provenance/derived"]
    checks.expect(any(x.startswith(f"tier1:{prov.get('summary_manifest_label')}") for x in reasons),
                  "audit log records the summary card under provenance/derived")

    print(f"\noutputs: {args.out}/p3_capture.jpg, {args.out}/p3_summary_card.svg")
    print("all checks passed" if not checks.failed else f"{checks.failed} check(s) failed")
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(main())
