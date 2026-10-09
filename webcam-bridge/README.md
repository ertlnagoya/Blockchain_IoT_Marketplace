# Webcam Littering Bridge (No HUSKYLENS2 Required)

This sample is for learners who do not have HUSKYLENS2.
It uses a USB webcam and detects:

- `person_detected`
- `possible_littering`

Detected events are exported as `.txt` files, then auto-productized by `mediator-owner`.

## Startup Order (Checklist)

1. Start blockchain and deploy contracts (`iot-market`)
2. Start storage server (`simple-storage`)
3. Start IPFS/PostgreSQL (`ipfs`)
4. Start owner mediator (`mediator-owner`)
5. Start buyer mediator (`mediator-buyer`)
6. Start frontend (`iot-market-ui`)
7. Start this bridge (`webcam-bridge`)

## Install (PC or Raspberry Pi)

```bash
cd webcam-bridge
pip install ultralytics opencv-python
```

For Raspberry Pi, `opencv-python` installation depends on environment.
If pip wheels are unavailable, use OS packages or prebuilt images.

## Quick Start (No Camera / Mock)

```bash
cd webcam-bridge
python3 webcam_litter_bridge.py \
  --mode mock \
  --camera-id 401 \
  --output-dir ../mediator-owner/raw_data/output \
  --flush-seconds 5
```

Expected log example:

```txt
[webcam-bridge] mock mode start
[webcam-bridge] wrote ../mediator-owner/raw_data/output/401_webcam_event_*.txt
```

## USB Webcam Start

```bash
cd webcam-bridge
python3 webcam_litter_bridge.py \
  --mode webcam \
  --camera-index 0 \
  --camera-id 401 \
  --output-dir ../mediator-owner/raw_data/output \
  --litter-classes bottle,cup \
  --linger-seconds 8 \
  --person-away-seconds 5
```

Optional debug preview window:

```bash
python3 webcam_litter_bridge.py --mode webcam --show
```

## Detection Logic (Simple Heuristic)

- Person event:
  - If one or more persons are detected, emits `person_detected` periodically.
- Littering event:
  - If an object in `--litter-classes` stays visible for `--linger-seconds` or more,
  - and no person is near that object for `--person-away-seconds` or more,
  - emits `possible_littering`.

This is a beginner-friendly heuristic, not a legal/forensic classifier.

## End-to-End Success Criteria

1. `*_webcam_event_*.txt` files appear in `mediator-owner/raw_data/output`.
2. `mediator-owner` detects files and deploys products.
3. Products appear in frontend.
4. Buyer can purchase and receive data via existing flow.

## Common Issues

1. Webcam open error
- Change `--camera-index` (`0`, `1`, ...).
- Ensure no other app is using the camera.

2. No products appear
- Verify owner mediator command:
  `cargo run -- settings/owner_1.yaml`
- Verify output path points to `mediator-owner/raw_data/output`.

3. Performance is slow
- Use a lighter model (`yolov8n.pt` default).
- Lower input resolution at OS/camera layer.

4. Too many/too few littering events
- Tune:
  - `--linger-seconds`
  - `--person-away-seconds`
  - `--person-near-px`
  - `--conf`
