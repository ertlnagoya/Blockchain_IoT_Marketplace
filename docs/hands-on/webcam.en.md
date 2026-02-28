# USB Webcam Sample (Littering)

## Mock first

```bash
cd webcam-bridge
python3 webcam_litter_bridge.py --mode mock --output-dir ../mediator-owner/raw_data/output
```

## USB webcam

```bash
python3 webcam_litter_bridge.py --mode webcam --camera-index 0 --output-dir ../mediator-owner/raw_data/output
```

## Event types

- `person_detected`
- `possible_littering`
