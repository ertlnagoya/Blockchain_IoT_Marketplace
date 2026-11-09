"""Stage P (C2PA provenance) P1 + P2: run the provenance flow through the publisher.

Needs the publisher started with the C2PA overlay
(infra/docker-compose.c2pa.yml) and, for the token check, a Hardhat node
with ProvenanceToken deployed. Steps:

1. The gateway (this script) signs a capture with the gateway key.
2. P1: /media/upload verifies uploads -- an unsigned image passes with
   ``present: false``, the signed capture is ``Trusted``, a tampered copy
   is refused with ``400 c2pa_invalid`` even when renamed to ``.webp``.
3. P2: the event is published with the capture's image_url. The
   publisher blurs it, signs the blur with its own key (capture as
   ingredient, camera and sensor assertions redacted) and mints a
   ProvenanceToken.
4. The script downloads the Tier 2 image and checks its manifest itself.
5. A software wallet obtains a ViewerToken for each tier (full, access,
   summary) and shows which provenance fields /platform/data returns.
6. The token on chain and the provenance/* audit records are read back.

Usage:
    uv run --no-project --with c2pa-python --with pillow --with cryptography \
        python examples/hands_on/c2pa_provenance/p1p2_publisher_flow.py

Exit code is 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import c2pa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p0_sign_verify as p0  # noqa: E402  (signer, image capture, Checks)

REPO_ROOT = HERE.parents[2]
DATASET = "home/event/possible_littering"
TOPIC = "homeassistant/event/possible_littering"
# DataUserVC attributes that land in each tier with the VLM profile on
# (publisher/app/ssi/trust_score.py): 90 -> full, 75 -> access, 55 -> summary
TIERS = {
    "full": {"entityType": "GovernmentOrganization", "purpose": "research",
             "legalCompliance": True, "dataHandlingPolicy": "ISO27001", "misuseRecord": False},
    "access": {"entityType": "Enterprise", "purpose": "research",
               "legalCompliance": True, "dataHandlingPolicy": "ISO27001", "misuseRecord": False},
    "summary": {"entityType": "Research Organization", "purpose": "research",
                "legalCompliance": True, "dataHandlingPolicy": "", "misuseRecord": False},
}
# keccak256("tokenURI(uint256)")[:4]
TOKEN_URI_SELECTOR = "c87b56dd"


# ---- default image ----

def dummy_scene():
    """A park scene with a drawn person and a bottle on the grass.

    The face is drawn so that the publisher's face detector (OpenCV Haar
    cascade) finds it, which makes the Tier 2 blur visible. Unlike the P0
    dummy it carries no camera ID in its pixels.
    """
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", (640, 480), (170, 205, 235))  # sky
    d = ImageDraw.Draw(img)
    d.rectangle((0, 330, 640, 480), fill=(110, 160, 90))  # grass
    d.rectangle((40, 250, 140, 330), fill=(120, 90, 60))  # bench
    d.rectangle((210, 300, 370, 480), fill=(70, 90, 140))  # body
    cx, cy, r = 290, 190, 100
    d.ellipse((cx - r * 0.8, cy - r, cx + r * 0.8, cy + r * 1.05), fill=(224, 182, 150))
    d.rectangle((cx - r * 0.85, cy - r * 1.15, cx + r * 0.85, cy - r * 0.55), fill=(60, 45, 35))
    for sx in (-1, 1):
        ex, ey = cx + sx * r * 0.33, cy - r * 0.12
        d.ellipse((ex - r * 0.2, ey - r * 0.17, ex + r * 0.2, ey + r * 0.05), fill=(150, 110, 90))
        d.ellipse((ex - r * 0.12, ey - r * 0.1, ex + r * 0.12, ey + r * 0.02), fill=(40, 30, 30))
        d.rectangle((ex - r * 0.22, ey - r * 0.32, ex + r * 0.22, ey - r * 0.25), fill=(60, 45, 35))
    d.polygon([(cx, cy - r * 0.05), (cx - r * 0.12, cy + r * 0.3), (cx + r * 0.12, cy + r * 0.3)],
              fill=(190, 140, 115))
    d.ellipse((cx - r * 0.3, cy + r * 0.48, cx + r * 0.3, cy + r * 0.62), fill=(150, 70, 70))
    d.rounded_rectangle((470, 400, 540, 425), radius=8, fill=(90, 160, 110))  # bottle
    d.rectangle((540, 405, 555, 420), fill=(230, 230, 230))  # cap
    return img.filter(ImageFilter.GaussianBlur(1))


# ---- HTTP helpers (standard library only) ----

def http(method: str, url: str, *, body: bytes | None = None, headers: dict | None = None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - local hands-on
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def post_json(url: str, obj: dict):
    status, raw = http("POST", url, body=json.dumps(obj).encode(),
                       headers={"Content-Type": "application/json"})
    return status, json.loads(raw or b"null")


def post_form(url: str, fields: dict, headers: dict | None = None):
    body = urllib.parse.urlencode(fields).encode()
    status, raw = http("POST", url, body=body, headers={
        "Content-Type": "application/x-www-form-urlencoded", **(headers or {})})
    return status, json.loads(raw or b"null")


def upload(base: str, blob: bytes, name: str):
    boundary = "----iw3ip-" + uuid.uuid4().hex
    body = b"\r\n".join([
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{name}"'.encode(),
        b"Content-Type: image/jpeg", b"", blob, f"--{boundary}--".encode(), b"",
    ])
    status, raw = http("POST", base + "/media/upload", body=body,
                       headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return status, json.loads(raw)


# ---- software wallet: PurchaseViewerVC -> ViewerToken ----

def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def viewer_token(base: str, attrs: dict, tx_seed: str) -> tuple[str, list[str]]:
    """Claim -> issue PurchaseViewerVC -> present it, as the phone wallet does."""
    status, claim = post_json(base + "/marketplace/claim", {
        "merchandise_address": "0x" + "44" * 20,
        "buyer_eth_addr": "0x" + "55" * 20,
        "tx_hash": "0x" + hashlib.sha256(tx_seed.encode()).hexdigest(),
        "dataset_id": DATASET,
        "data_user_attrs": attrs,
    })
    if status != 200:
        raise RuntimeError(f"/marketplace/claim {status}: {claim}")
    offer = json.loads(urllib.parse.unquote(claim["deeplink"].split("=", 1)[1]))
    pre_auth = offer["grants"]["urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]
    _, tok = post_form(base + "/issuer/token", {
        "grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
        "pre-authorized_code": pre_auth,
    })
    key = ec.generate_private_key(ec.SECP256R1())
    nums = key.public_key().public_numbers()
    jwk = {"kty": "EC", "crv": "P-256",
           "x": _b64u(nums.x.to_bytes(32, "big")), "y": _b64u(nums.y.to_bytes(32, "big"))}
    head = _b64u(json.dumps({"alg": "ES256", "typ": "openid4vci-proof+jwt", "jwk": jwk}).encode())
    payload = _b64u(json.dumps({"nonce": tok["c_nonce"], "aud": offer["credential_issuer"],
                                "iat": int(time.time())}).encode())
    r, s = decode_dss_signature(key.sign(f"{head}.{payload}".encode(), ec.ECDSA(hashes.SHA256())))
    proof = f"{head}.{payload}." + _b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    status, raw = http("POST", base + "/issuer/credential", body=json.dumps({
        "format": "vc+sd-jwt",
        "vct": "https://iw3ip.example/credentials/PurchaseViewerVC/v1",
        "proof": {"proof_type": "jwt", "jwt": proof},
    }).encode(), headers={"Content-Type": "application/json",
                          "Authorization": f"Bearer {tok['access_token']}"})
    cred = json.loads(raw)
    if status != 200:
        raise RuntimeError(f"/issuer/credential {status}: {cred}")
    _, raw = http("GET", base + "/verifier/request?" + urllib.parse.urlencode(
        {"dataset_id": DATASET, "vc_kind": "PurchaseViewerVC"}), headers={"accept": "application/json"})
    req = json.loads(raw)
    _, presented = post_form(base + "/verifier/response", {
        "vp_token": cred["credential"],
        "presentation_submission": json.dumps({
            "id": "sub", "definition_id": "purchase-viewer-possible-littering",
            "descriptor_map": [{"id": "purchase_viewer_vc_possible_littering",
                                "format": "vc+sd-jwt", "path": "$"}],
        }),
        "state": req["state"],
    })
    if presented.get("status") != "allowed":
        raise RuntimeError(f"presentation refused: {presented}")
    return presented["viewer_token"], presented["allowed_views"]


# ---- chain ----

def token_uri(rpc: str, contract: str, token_id: int) -> dict:
    data = "0x" + TOKEN_URI_SELECTOR + token_id.to_bytes(32, "big").hex()
    _, out = post_json(rpc, {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                             "params": [{"to": contract, "data": data}, "latest"]})
    raw = bytes.fromhex(out["result"][2:])
    length = int.from_bytes(raw[32:64], "big")
    uri = raw[64:64 + length].decode()
    return json.loads(base64.b64decode(uri.split(",", 1)[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--image", type=Path, help="sign this JPEG/PNG instead of a dummy image")
    src.add_argument("--webcam", action="store_true", help="capture one frame with OpenCV")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--publisher", default="http://localhost:8080")
    parser.add_argument("--rpc", default="http://localhost:8545", help="Hardhat node for the token check")
    parser.add_argument("--certs", type=Path, default=HERE / "certs")
    parser.add_argument("--out", type=Path, default=HERE / "out")
    parser.add_argument("--camera-id", default="cam01")
    args = parser.parse_args()
    base = args.publisher.rstrip("/")
    if not (args.certs / "publisher_chain.pem").exists():
        sys.exit(f"{args.certs}/publisher_chain.pem not found; run make_test_certs.py first")
    args.out.mkdir(parents=True, exist_ok=True)
    checks = p0.Checks()
    trusted_ctx = c2pa.Context(c2pa.Settings.from_dict({
        "verify": {"verify_trust": True},
        "trust": {"user_anchors": (args.certs / "ca.pem").read_text()},
    }))

    # 1. gateway signs the capture (same manifest as p0_sign_verify.py)
    print(f"c2pa-python {p0.version('c2pa-python')} / c2pa-rs {c2pa.sdk_version()}")
    img = p0.capture_image(args) if (args.image or args.webcam) else dummy_scene()
    capture_def = {
        "claim_generator_info": [{"name": "iw3ip-gateway", "version": "0.1.0"}],
        "title": "capture.jpg",
        "assertions": [
            {"label": "c2pa.actions", "data": {"actions": [
                {"action": "c2pa.created", "digitalSourceType": p0.DIGITAL_CAPTURE}]}},
            {"label": "jp.ertl.iw3ip.capture", "data": {
                "camera_id": args.camera_id,
                "captured_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "gateway_did": "did:jwk:<gateway>"}},
            {"label": "jp.ertl.iw3ip.sensor", "data": {"readings": [
                {"topic": "home/env/temperature", "value": 22.4, "unit": "Cel"}]}},
        ],
    }
    out = io.BytesIO()
    with c2pa.Builder(capture_def) as builder:
        builder.sign(p0.make_signer(args.certs), "image/jpeg", p0.jpeg_bytes(img), out)
    capture = out.getvalue()
    (args.out / "p1_capture.jpg").write_bytes(capture)

    # 2. P1: the publisher verifies uploads
    status, j = upload(base, p0.jpeg_bytes(img).getvalue(), "unsigned.jpg")
    checks.expect(status == 200 and j["c2pa"] is not None and j["c2pa"]["present"] is False,
                  "P1 unsigned image is accepted without provenance",
                  f"{status} c2pa={j.get('c2pa')}")
    status, up = upload(base, capture, "capture.jpg")
    c = up.get("c2pa") or {}
    checks.expect(status == 200 and c.get("validation_state") == "Trusted",
                  "P1 signed capture is Trusted at the publisher",
                  f"{status} {c.get('validation_state')} signer={c.get('signer')}")
    tampered = bytearray(capture)
    tampered[-10] ^= 0xFF
    status, j = upload(base, bytes(tampered), "tampered.jpg")
    detail = j.get("detail") if isinstance(j, dict) else None
    checks.expect(status == 400 and isinstance(detail, dict) and detail.get("error") == "c2pa_invalid",
                  "P1 tampered capture is refused", f"{status} {detail and detail.get('error')}")
    # the publisher reads the type from the bytes, so a new extension does not help
    status, j = upload(base, bytes(tampered), "tampered.webp")
    detail = j.get("detail") if isinstance(j, dict) else None
    checks.expect(status == 400 and isinstance(detail, dict) and detail.get("error") == "c2pa_invalid",
                  "P1 tampered capture renamed to .webp is refused", f"{status} {detail and detail.get('error')}")

    # 3. P2: publish the event with the capture's image_url
    consent = json.loads((REPO_ROOT / "examples" / "consent_possible_littering.json").read_text())
    post_json(base + "/consents", consent)
    payload = json.loads((REPO_ROOT / "examples" / "payload_possible_littering.json").read_text())
    payload["image_url"] = up["url"]
    payload["ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
    status, pub = post_json(base + "/simulate/publish", {
        "topic": TOPIC, "payload": payload, "purpose": "community_cleaning"})
    checks.expect(pub.get("status") == "allowed", "P2 event is published", str(pub))
    _, raw = http("GET", base + "/platform/ingest")
    rows = [r for r in json.loads(raw) if r.get("image_url") == up["url"]]
    row = rows[-1] if rows else {}
    prov = row.get("provenance") or {}
    checks.expect(prov.get("manifest_label") == c.get("manifest_label"),
                  "P2 row carries the capture's manifest label", str(prov.get("manifest_label")))
    checks.expect(bool(prov.get("redacted_manifest_label")),
                  "P2 Tier 2 image has its own manifest", str(prov.get("redacted_manifest_label")))

    # 4. check the Tier 2 image ourselves
    redacted_url = row.get("image_url_redacted") or ""
    _, tier2 = http("GET", redacted_url) if redacted_url else (0, b"")
    (args.out / "p2_tier2.jpg").write_bytes(tier2)
    state, store = p0.read(tier2, trusted_ctx) if tier2 else ("-", {})
    active = store.get("manifests", {}).get(store.get("active_manifest"), {})
    checks.expect(state == "Trusted" and active.get("signature_info", {}).get("common_name") == "iw3ip-publisher",
                  "P2 Tier 2 image is Trusted and signed by the publisher", state)
    cap_m = store.get("manifests", {}).get(c.get("manifest_label"), {})
    remaining = [a["label"] for a in cap_m.get("assertions", [])]
    leaked = [lab for lab in p0.REDACT_LABELS if lab in remaining or (lab == "c2pa.thumbnail.claim" and "thumbnail" in cap_m)]
    checks.expect(bool(cap_m) and not leaked, "P2 capture thumbnail / camera / sensor are redacted", f"leaked={leaked}")
    hits = tier2.count(args.camera_id.encode())
    checks.expect(bool(tier2) and hits == 0, "P2 camera ID appears nowhere in the Tier 2 bytes", f"{hits} hit(s)")

    # 5. what each tier sees
    seen = {}
    for i, (tier, attrs) in enumerate(TIERS.items()):
        token, views = viewer_token(base, attrs, f"{up['sha256']}-{tier}-{time.time()}-{i}")
        _, raw = http("GET", base + "/platform/data?" + urllib.parse.urlencode({"dataset_id": DATASET}),
                      headers={"Authorization": f"Bearer {token}"})
        data_rows = [r for r in json.loads(raw)["rows"]
                     if (r.get("provenance") or {}).get("manifest_label") == c.get("manifest_label")]
        r = data_rows[-1] if data_rows else {}
        seen[tier] = r
        print(f"  {tier:8s} views={views}")
        print(f"           image_url={'yes' if 'image_url' in r else 'no'}"
              f" image_url_redacted={'yes' if 'image_url_redacted' in r else 'no'}"
              f" provenance={sorted((r.get('provenance') or {}).keys())}")
    full_p, access_p, summary_p = (seen[t].get("provenance") or {} for t in ("full", "access", "summary"))
    checks.expect("signer" in full_p and "redacted_manifest_label" in full_p,
                  "tier full sees signer and the Tier 2 manifest")
    checks.expect("signer" in access_p and "redacted_manifest_label" in access_p and "image_url" not in seen["access"],
                  "tier access sees the Tier 2 manifest but not the raw image")
    checks.expect(bool(summary_p) and "signer" not in summary_p and "redacted_manifest_label" not in summary_p
                  and "derived_sha256" in summary_p,
                  "tier summary sees only label, state, token and the summary hash")
    summary_text = seen["summary"].get("description_summary", "")
    checks.expect(hashlib.sha256(summary_text.encode()).hexdigest() == summary_p.get("derived_sha256"),
                  "summary text matches provenance.derived_sha256")

    # 6. chain and audit log
    if prov.get("token_id") is not None:
        meta = token_uri(args.rpc, prov["token_contract"], prov["token_id"])
        checks.expect(meta.get("manifestLabel") == c.get("manifest_label")
                      and meta.get("assetSha256") == "0x" + up["sha256"],
                      "P2 ProvenanceToken anchors the manifest label and image sha256",
                      f"token #{prov['token_id']}")
    else:
        checks.expect(False, "P2 ProvenanceToken was minted",
                      "no token_id; set PROVENANCE_TOKEN_ADDRESS and start the Hardhat node")
    _, raw = http("GET", base + "/audit/logs?limit=200")
    topics = {r["raw_topic"] for r in json.loads(raw)}
    for topic in ("provenance/verified", "provenance/derived", "provenance/anchored"):
        checks.expect(topic in topics, f"audit log has {topic}")

    print(f"\noutputs: {args.out}/p1_capture.jpg, {args.out}/p2_tier2.jpg")
    print("all checks passed" if not checks.failed else f"{checks.failed} check(s) failed")
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(main())
