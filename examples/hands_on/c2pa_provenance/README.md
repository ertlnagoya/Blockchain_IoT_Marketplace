# c2pa_provenance — Stage P (C2PA provenance) P0, P1, P2

Check program for the design spec
[C2PA provenance pipeline (Stage P)](https://www.ertl.jp/iw3ip.github.io/design/c2pa-provenance-spec/).
The hands-on page is [Prove where an image came from (C2PA / Stage P)](https://www.ertl.jp/iw3ip.github.io/hands-on/c2pa-provenance/)
(Japanese, with an English version on the same site).

The goal of P0: sign a camera capture with a C2PA manifest, derive a Tier 2
face-blurred image that keeps a verifiable link to the original without
leaking it, and confirm the result with the C2PA SDK — all on one PC, with
no publisher, chain, or camera required.

P1 and P2 run the same flow through the publisher: `/media/upload` verifies
the manifest, the publisher signs the Tier 2 blur itself, mints a
ProvenanceToken on a Hardhat node, and `/platform/data` shows each tier only
part of the provenance. The second hands-on page is
[Connect provenance to the publisher and the chain (C2PA / Stage P, P1-P2)](https://www.ertl.jp/iw3ip.github.io/hands-on/c2pa-provenance-publisher/).

## Files

- `make_test_certs.py` — creates a private test CA, an ES256 gateway certificate and the publisher's signing certificate under `certs/`
- `p0_sign_verify.py` — P0: signs a capture, makes the Tier 2 derivative, and runs the checks
- `p1p2_publisher_flow.py` — P1 + P2: sends the signed capture through the publisher and checks verification, the signed Tier 2 image, the per-tier provenance, the token and the audit log
- `certs/`, `out/` — generated; ignored by git (the keys are for local tests only)

## Run

`c2pa-python` and `pillow` are not project dependencies, so pass them with
`--with`. Use `--no-project` because `uv run` would otherwise try to build
this repository as a package.

```bash
uv run --no-project --with c2pa-python --with pillow --with cryptography \
  python examples/hands_on/c2pa_provenance/make_test_certs.py
```

```bash
uv run --no-project --with c2pa-python --with pillow --with cryptography \
  python examples/hands_on/c2pa_provenance/p0_sign_verify.py
```

By default the script signs a generated dummy image. Use `--image PATH` to
sign your own JPEG/PNG, or `--webcam` to capture one frame (needs
`--with opencv-python`; on macOS, allow camera access for your terminal app
first, or the script stops with `webcam capture failed`).

## Expected output

```
c2pa-python 0.38.1 / c2pa-rs 0.91.3
[PASS] capture without trust anchor is Valid + untrusted  (Valid)
[PASS] capture with test CA is Trusted  (Trusted)
[PASS] custom assertions are in the capture manifest  (...)
[PASS] Tier 2 derivative is Trusted  (Trusted)
[PASS] capture/sensor assertions are redacted  (leaked=[])
[PASS] no unblurred thumbnail via the ingredient
[PASS] capture manifest thumbnail is redacted
[PASS] capture title has no camera ID  (capture.jpg)
[PASS] signer certificate name has no camera ID  (iw3ip-gateway)
[PASS] camera ID appears nowhere in the Tier 2 bytes  (0 hit(s))
[PASS] one flipped byte makes the derivative Invalid  (Invalid)

outputs: .../examples/hands_on/c2pa_provenance/out/capture.jpg, .../examples/hands_on/c2pa_provenance/out/tier2.jpg
all checks passed
```

The exit code is 0 only when every check passes. `out/capture.jpg` and
`out/tier2.jpg` are the signed files.

## What each check corresponds to in the spec

| Check | Spec section |
| --- | --- |
| Valid + untrusted / Trusted | §6.1 certificates, §7.1 validation states |
| Custom assertions | §5.1 labels, §5.2 capture manifest |
| Tier 2 derivative, redaction, thumbnails | §5.3 derivative manifests (the privacy pitfall) |
| Capture title, signer certificate name, camera ID in the bytes | §5.2 capture manifest title, §5.3 what redaction cannot remove, §6.1 certificate name |
| One flipped byte | §9.1 tamper detection |

## Pitfalls found while writing this

- The SDK rejects certificates signed with SHA-1, self-signed signing
  certificates, and signing certificates without an EKU. A chain without key
  identifiers (SKI/AKI) and a CA key usage was also rejected. `make_test_certs.py`
  covers all of these (macOS `openssl` signs with SHA-1 unless `-sha256` is given).
- A derivative manifest must start with `c2pa.opened`; `c2pa.edited` first is refused.
- Without redaction, the derivative carries the original camera ID, sensor
  readings, and an **unblurred thumbnail** of the original. The script reads
  the derivative back to confirm the redaction instead of trusting the definition.
- The SDK does not add the `c2pa.redacted` action by itself.
- Redaction cannot remove the capture manifest's title or the signer
  certificate: the derivative imports the capture claim and signature as they
  are, and the title stays even when the ingredient title is omitted. Keep the
  camera ID and capture time out of both (the camera ID goes in
  `jp.ertl.iw3ip.capture`, which can be redacted). Certificates made before
  this change have CN `iw3ip-gateway-cam01`; rerun `make_test_certs.py`.
- The certificate serial number still stays in every derivative, so Tier 2
  recipients can tell which files came from the same gateway (spec §11).

## P1 + P2: through the publisher

Start a Hardhat node and deploy the ProvenanceToken (in `iot-market/`):

```bash
npx hardhat node --hostname 0.0.0.0
```

```bash
npx hardhat run scripts/deployProvenanceToken.ts --network localhost
```

Start the publisher with the C2PA overlay, passing the printed address. The
overlay mounts `certs/` read-only, turns on `C2PA_ENABLED`, the opencv face
blur and the VLM stub, and points `PROVENANCE_RPC_URL` at the host's node.

```bash
PROVENANCE_TOKEN_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3 \
  docker compose -f infra/docker-compose.yml -f infra/docker-compose.c2pa.yml up -d --build publisher
```

Then run the flow (from the repository root):

```bash
uv run --no-project --with c2pa-python --with pillow --with cryptography \
  python examples/hands_on/c2pa_provenance/p1p2_publisher_flow.py
```

Expected output (manifest labels differ per run):

```
[PASS] P1 unsigned image is accepted without provenance  (...)
[PASS] P1 signed capture is Trusted at the publisher  (200 Trusted signer=iw3ip-gateway)
[PASS] P1 tampered capture is refused  (400 c2pa_invalid)
[PASS] P1 tampered capture renamed to .webp is refused  (400 c2pa_invalid)
[PASS] P2 event is published  (...)
[PASS] P2 row carries the capture's manifest label  (urn:c2pa:...)
[PASS] P2 Tier 2 image has its own manifest  (urn:c2pa:...)
[PASS] P2 Tier 2 image is Trusted and signed by the publisher  (Trusted)
[PASS] P2 capture thumbnail / camera / sensor are redacted  (leaked=[])
[PASS] P2 camera ID appears nowhere in the Tier 2 bytes  (0 hit(s))
  full     views=['event', 'image', 'video', 'image_redacted', 'description_full', 'description_summary']
           image_url=yes image_url_redacted=yes provenance=['anchor_tx', 'derived_sha256', 'manifest_label', 'redacted_manifest_label', 'signer', 'token_contract', 'token_id', 'validation_state']
  access   views=['event', 'image_redacted', 'description_full', 'description_summary']
           image_url=no image_url_redacted=yes provenance=['anchor_tx', 'derived_sha256', 'manifest_label', 'redacted_manifest_label', 'signer', 'token_contract', 'token_id', 'validation_state']
  summary  views=['event', 'description_summary']
           image_url=no image_url_redacted=no provenance=['anchor_tx', 'derived_sha256', 'manifest_label', 'token_contract', 'token_id', 'validation_state']
[PASS] tier full sees signer and the Tier 2 manifest
[PASS] tier access sees the Tier 2 manifest but not the raw image
[PASS] tier summary sees only label, state, token and the summary hash
[PASS] summary text matches provenance.derived_sha256
[PASS] P2 ProvenanceToken anchors the manifest label and image sha256  (token #1)
[PASS] audit log has provenance/verified
[PASS] audit log has provenance/derived
[PASS] audit log has provenance/anchored

outputs: .../out/p1_capture.jpg, .../out/p2_tier2.jpg
all checks passed
```

The script plays both ends: the gateway that signs the capture, and a
software wallet that obtains a ViewerToken for each tier (full, access,
summary) through `/marketplace/claim`, `/issuer/*` and `/verifier/*`, the
same endpoints the phone wallet uses.

| Check | Spec section |
| --- | --- |
| Unsigned / Trusted / tampered upload | §7.1 `/media/upload` response and validation states |
| Tier 2 image signed by the publisher, redaction | §5.3 derivative manifests |
| Per-tier provenance fields, summary hash | §7.2 `/platform/data` rows, §5.5 text derivatives |
| Token | §8 ProvenanceToken |
| Audit log | §7.3 `provenance/verified`, `provenance/derived`, `provenance/anchored` |

Every tier, including summary, sees the capture's `manifest_label` and the
`token_id`, so two recipients of different tiers can tell that their rows
come from the same capture. This follows spec §7.2 and is a known limit.

## Not covered yet

- Content Credentials Verify (the page shows our test CA as untrusted)
- RTSP IP cameras, fragmented MP4, Raspberry Pi timing (P3–P4)
- A signing key in a TPM or secure element (P4)
