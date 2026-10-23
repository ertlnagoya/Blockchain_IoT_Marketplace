# c2pa_provenance — Stage P (C2PA provenance) P0 check

Check program for the design spec
[C2PA provenance pipeline (Stage P)](https://www.ertl.jp/iw3ip.github.io/design/c2pa-provenance-spec/).
The hands-on page is [Prove where an image came from (C2PA / Stage P)](https://www.ertl.jp/iw3ip.github.io/hands-on/c2pa-provenance/)
(Japanese, with an English version on the same site).

The goal: sign a camera capture with a C2PA manifest, derive a Tier 2
face-blurred image that keeps a verifiable link to the original without
leaking it, and confirm the result with the C2PA SDK — all on one PC, with
no publisher, chain, or camera required.

## Files

- `make_test_certs.py` — creates a private test CA and an ES256 gateway certificate under `certs/`
- `p0_sign_verify.py` — signs a capture, makes the Tier 2 derivative, and runs the checks
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

## Not covered yet

- Content Credentials Verify (the page shows our test CA as untrusted)
- RTSP IP cameras, fragmented MP4, Raspberry Pi timing (P3–P4)
- `/media/upload` validation in the publisher (P1)
