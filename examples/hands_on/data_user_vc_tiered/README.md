# Stage T case B — provider-with-media demo

Drives the full **"event + image + video → tier-aware `/platform/data`"**
loop. The receiver side is unchanged — Tier 3 sees `image_url` and
`video_url`, Tier 2 sees only `image_url`, Tier 1 sees neither.

```bash
# Provider side
python examples/hands_on/data_user_vc_tiered/provider_with_media.py \
  --base-url http://192.168.68.53:8080
```

The script:

1. Generates a 1×1 JPEG / MP4 fixture under `fixtures/` (or uses
   `--image` / `--video` paths you supply).
2. Uploads both via `POST /media/upload` (the publisher's media gateway
   dedupes on sha256, so re-runs are cheap).
3. Builds a `possible_littering` event with `image_url` / `video_url` /
   `video_duration_sec` at the envelope top level.
4. Posts it to `/simulate/publish` so it runs through the same Consent
   VC pipeline as the Phase 2 hands-on.

## Receiver (unchanged)

Use the existing Stage T walkthrough at
`docs/hands-on/data-user-vc-tiered.md` — issue a DataUserVC at the
desired tier, claim, present a PurchaseViewerVC, fetch
`/platform/data`, and watch `image_url` / `video_url` appear or
disappear per tier. Tap the URL on the receiver's browser / wallet to
see the actual blob.

## Limitations (intentional, lifted in case C)

- Publisher-hosted, not content-addressed.
- No auth on the GET path: the URL itself is the only access control
  (sha256 makes it unguessable, but URL-leakage = blob-leakage).
- Single replica: no resilience / pinning.

Case C will replace the gateway with IPFS / Web3.Storage while keeping
the same `/media/upload` shape so this script doesn't change.
