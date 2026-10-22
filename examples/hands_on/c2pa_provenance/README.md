# c2pa_provenance — Stage P (C2PA provenance) P0 check

Check program for the design spec
[C2PA provenance pipeline (Stage P)](https://www.ertl.jp/iw3ip.github.io/design/c2pa-provenance-spec/).
There is no hands-on page yet; this directory is the starting point for P0.

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
`--with opencv-python`).

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
[PASS] one flipped byte makes the derivative Invalid  (Invalid)

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
| One flipped byte | §9.1 tamper detection |

## Pitfalls found while writing this

- The SDK rejects certificates signed with SHA-1, self-signed signing
  certificates, and signing certificates without an EKU. `make_test_certs.py`
  avoids all three (macOS `openssl` signs with SHA-1 unless `-sha256` is given).
- The ES256 signing callback must return raw `r||s` (64 bytes), not DER.
- A derivative manifest must start with `c2pa.opened`; `c2pa.edited` first is refused.
- Without redaction, the derivative carries the original camera ID, sensor
  readings, and an **unblurred thumbnail** of the original.
- Redaction URIs must start with `/c2pa/`. Other forms are silently ignored,
  which is why the script reads the derivative back and checks.
- The SDK does not add the `c2pa.redacted` action by itself.

## Not covered yet

- Content Credentials Verify (the page shows our test CA as untrusted)
- RTSP IP cameras, fragmented MP4, Raspberry Pi timing (P3–P4)
- `/media/upload` validation in the publisher (P1)
