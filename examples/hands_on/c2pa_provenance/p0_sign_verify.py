"""Stage P (C2PA provenance) P0: sign a capture, derive a Tier 2 image, verify both.

Checks the design spec (docs/design/c2pa-provenance-spec, §5.2 / §5.3 / §7.1)
end to end on one machine:

1. Sign a capture (dummy JPEG, a file, or one webcam frame) with a capture
   manifest carrying the ``jp.ertl.iw3ip.*`` custom assertions.
2. Validate it without and with the test CA as a trust anchor
   (expected: ``Valid`` with ``signingCredential.untrusted``, then ``Trusted``).
3. Make a Tier 2 face-blurred derivative that references the capture as a
   ``parentOf`` ingredient and redacts the capture's thumbnail, camera and
   sensor assertions.
4. Confirm the redacted assertions are really gone and the derivative is
   still ``Trusted``, and that the camera ID does not reach Tier 2 through
   the capture title or the signer certificate, which cannot be redacted.
5. Flip one byte of the derivative and confirm it becomes ``Invalid``.

Usage:
    uv run --with c2pa-python --with pillow \
        python examples/hands_on/c2pa_provenance/make_test_certs.py
    uv run --with c2pa-python --with pillow \
        python examples/hands_on/c2pa_provenance/p0_sign_verify.py [--image PATH | --webcam]

Exit code is 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
from importlib.metadata import version
from pathlib import Path

import c2pa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from PIL import Image, ImageDraw, ImageFilter


HERE = Path(__file__).resolve().parent
DIGITAL_CAPTURE = "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"
# Capture assertions that must not reach Tier 2 recipients (spec §5.3)
REDACT_LABELS = ["c2pa.thumbnail.claim", "jp.ertl.iw3ip.capture", "jp.ertl.iw3ip.sensor"]


def make_signer(certs: Path) -> c2pa.Signer:
    key = serialization.load_pem_private_key((certs / "gw.key").read_bytes(), None)

    def sign(data: bytes) -> bytes:
        # COSE ES256 signatures are raw r||s (64 bytes); the SDK also accepted DER in our tests
        r, s = decode_dss_signature(key.sign(data, ec.ECDSA(hashes.SHA256())))
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    return c2pa.Signer.from_callback(
        sign, c2pa.C2paSigningAlg.ES256, (certs / "chain.pem").read_text(), None
    )


def capture_image(args: argparse.Namespace) -> Image.Image:
    if args.image:
        return Image.open(args.image).convert("RGB")
    if args.webcam:
        import cv2  # optional; only needed for --webcam

        cam = cv2.VideoCapture(args.camera_index)
        ok, frame = cam.read()
        cam.release()
        if not ok:
            sys.exit("webcam capture failed")
        return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    img = Image.new("RGB", (640, 480), (90, 120, 160))
    draw = ImageDraw.Draw(img)
    draw.ellipse((280, 120, 360, 200), fill=(230, 190, 160))  # stand-in "face"
    draw.text((10, 10), "cam01 (dummy)", fill=(255, 255, 255))
    return img


def jpeg_bytes(img: Image.Image) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    buf.seek(0)
    return buf


def read(data: bytes, ctx: c2pa.Context | None = None) -> tuple[str, dict]:
    stream = io.BytesIO(data)
    reader = c2pa.Reader("image/jpeg", stream, context=ctx) if ctx else c2pa.Reader("image/jpeg", stream)
    return reader.get_validation_state(), json.loads(reader.json())


def status_codes(store: dict) -> list[str]:
    return [s.get("code") for s in store.get("validation_status") or []]


class Checks:
    def __init__(self) -> None:
        self.failed = 0

    def expect(self, ok: bool, label: str, detail: str = "") -> None:
        self.failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--image", type=Path, help="sign this JPEG/PNG instead of a dummy image")
    src.add_argument("--webcam", action="store_true", help="capture one frame with OpenCV")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--certs", type=Path, default=HERE / "certs")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--camera-id", default="cam01")
    args = parser.parse_args()

    if not (args.certs / "chain.pem").exists():
        sys.exit(f"{args.certs}/chain.pem not found; run make_test_certs.py first")
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"c2pa-python {version('c2pa-python')} / c2pa-rs {c2pa.sdk_version()}")
    signer = make_signer(args.certs)
    trusted_ctx = c2pa.Context(c2pa.Settings.from_dict({
        "verify": {"verify_trust": True},
        "trust": {"user_anchors": (args.certs / "ca.pem").read_text()},
    }))
    checks = Checks()

    # 1. capture manifest (spec §5.2)
    img = capture_image(args)
    captured_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    capture_def = {
        "claim_generator_info": [{"name": "iw3ip-gateway", "version": "0.1.0"}],
        # the capture title cannot be redacted from derivatives (spec §5.2), so it carries no camera ID or time
        "title": "capture.jpg",
        "assertions": [
            {"label": "c2pa.actions", "data": {"actions": [
                {"action": "c2pa.created", "digitalSourceType": DIGITAL_CAPTURE}]}},
            {"label": "jp.ertl.iw3ip.capture", "data": {
                "camera_id": args.camera_id, "captured_at": captured_at,
                "gateway_did": "did:jwk:<gateway>"}},
            {"label": "jp.ertl.iw3ip.sensor", "data": {"readings": [
                {"topic": "home/env/temperature", "value": 22.4, "unit": "Cel"}]}},
        ],
    }
    out = io.BytesIO()
    with c2pa.Builder(capture_def) as builder:
        builder.sign(signer, "image/jpeg", jpeg_bytes(img), out)
    capture = out.getvalue()
    (args.out / "capture.jpg").write_bytes(capture)

    # 2. validation without / with the test CA (spec §7.1)
    state, store = read(capture)
    checks.expect(state == "Valid" and "signingCredential.untrusted" in status_codes(store),
                  "capture without trust anchor is Valid + untrusted", state)
    state, store = read(capture, trusted_ctx)
    checks.expect(state == "Trusted", "capture with test CA is Trusted", state)
    cap_label = store["active_manifest"]
    cap_labels = [a["label"] for a in store["manifests"][cap_label]["assertions"]]
    checks.expect({"jp.ertl.iw3ip.capture", "jp.ertl.iw3ip.sensor"} <= set(cap_labels),
                  "custom assertions are in the capture manifest", ", ".join(cap_labels))

    # 3. Tier 2 derivative (spec §5.3)
    blurred = Image.open(io.BytesIO(capture)).convert("RGB").filter(ImageFilter.GaussianBlur(12))
    redactions = [f"self#jumbf=/c2pa/{cap_label}/c2pa.assertions/{lab}" for lab in REDACT_LABELS]
    derived_def = {
        "claim_generator_info": [{"name": "iw3ip-publisher", "version": "0.1.0"}],
        "title": "tier2.jpg",
        "assertions": [
            {"label": "c2pa.actions", "data": {"actions": [
                # the SDK refuses a first action other than created / opened
                {"action": "c2pa.opened", "parameters": {"ingredientIds": ["capture"]}},
                {"action": "c2pa.edited", "parameters": {"description": "face_blur"}},
                # the SDK does not add c2pa.redacted by itself
                *({"action": "c2pa.redacted", "reason": "c2pa.PII.present",
                   "parameters": {"redacted": uri}} for uri in redactions),
            ]}},
            {"label": "jp.ertl.iw3ip.derivation", "data": {"tier": 2, "kind": "face_blur"}},
        ],
        # removes these assertions from the ingredient's manifest; checked below
        "redactions": redactions,
    }
    out = io.BytesIO()
    # the derivative's own thumbnail shows the blurred image, so it can stay
    with c2pa.Builder(derived_def) as builder:
        builder.add_ingredient(
            {"title": "capture.jpg", "relationship": "parentOf", "label": "capture"},
            "image/jpeg", io.BytesIO(capture),
        )
        builder.sign(signer, "image/jpeg", jpeg_bytes(blurred), out)
    derived = out.getvalue()
    (args.out / "tier2.jpg").write_bytes(derived)

    # 4. redaction really happened, derivative still trusted
    state, store = read(derived, trusted_ctx)
    checks.expect(state == "Trusted", "Tier 2 derivative is Trusted", state)
    remaining = [a["label"] for a in store["manifests"].get(cap_label, {}).get("assertions", [])]
    leaked = [lab for lab in REDACT_LABELS if lab in remaining]
    checks.expect(not leaked, "capture/sensor assertions are redacted", f"leaked={leaked}")
    ingredients = store["manifests"][store["active_manifest"]].get("ingredients", [])
    checks.expect(all("thumbnail" not in i for i in ingredients),
                  "no unblurred thumbnail via the ingredient")
    checks.expect("thumbnail" not in store["manifests"][cap_label],
                  "capture manifest thumbnail is redacted")
    # the capture title and signer certificate come in with the capture claim and cannot be redacted (spec §5.3)
    cap_m = store["manifests"][cap_label]
    cap_title, signer_cn = cap_m.get("title") or "", cap_m["signature_info"].get("common_name") or ""
    checks.expect(args.camera_id not in cap_title, "capture title has no camera ID", cap_title)
    checks.expect(args.camera_id not in signer_cn, "signer certificate name has no camera ID",
                  signer_cn + ("" if args.camera_id not in signer_cn else "; rerun make_test_certs.py"))
    hits = derived.count(args.camera_id.encode())
    checks.expect(hits == 0, "camera ID appears nowhere in the Tier 2 bytes", f"{hits} hit(s)")

    # 5. tamper detection (spec §9.1)
    tampered = bytearray(derived)
    tampered[-10] ^= 0xFF  # image data just before EOI (the manifest sits in APP11 near the start)
    state, store = read(bytes(tampered), trusted_ctx)
    checks.expect(state == "Invalid" and "assertion.dataHash.mismatch" in status_codes(store),
                  "one flipped byte makes the derivative Invalid", state)

    print(f"\noutputs: {args.out}/capture.jpg, {args.out}/tier2.jpg")
    print("all checks passed" if not checks.failed else f"{checks.failed} check(s) failed")
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(main())
