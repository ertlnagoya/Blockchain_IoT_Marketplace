# HuskyLens2 Sensor Bridge (First-Learner Sample)

This sample turns HUSKYLENS2 detections into `.txt` files that are automatically productized by `mediator-owner`.

## Concept

- HUSKYLENS2 (or compatible relay) sends detection events.
- `huskylens_bridge.py` aggregates events every few seconds.
- The bridge writes `*.txt` files into `mediator-owner/raw_data/output`.
- `mediator-owner` watches the folder and deploys products automatically.

## Quick Start (No Device / Mock)

```bash
cd sensor-bridge
python3 huskylens_bridge.py \
  --mode mock \
  --camera-id 301 \
  --output-dir ../mediator-owner/raw_data/output \
  --flush-interval-sec 8
```

This is enough to learn the full pipeline for the first time.

## Run with HUSKYLENS2 on PC

1. Connect HUSKYLENS2 to your PC through a USB-UART adapter.
2. Start bridge in serial mode.

```bash
cd sensor-bridge
python3 huskylens_bridge.py \
  --mode serial \
  --serial-port /dev/ttyUSB0 \
  --baudrate 115200 \
  --camera-id 301 \
  --output-dir ../mediator-owner/raw_data/output
```

- If you are on macOS, serial ports are often `/dev/tty.usbserial-*` or `/dev/tty.usbmodem*`.
- `pyserial` is required for serial mode:

```bash
pip install pyserial
```

## Run with Wi-Fi Module (TCP Relay)

If your Wi-Fi module can forward line-by-line detection messages as TCP text:

```bash
cd sensor-bridge
python3 huskylens_bridge.py \
  --mode tcp \
  --tcp-host 0.0.0.0 \
  --tcp-port 8899 \
  --camera-id 301 \
  --output-dir ../mediator-owner/raw_data/output
```

Accepted input format (one line each):

- NDJSON (recommended)
```json
{"label":"person","confidence":0.93,"id":"7","x":120,"y":80,"w":44,"h":70}
```
- CSV fallback
```txt
person,7,0.93,120,80,44,70
```

## Raspberry Pi Variant

You can run exactly the same script on Raspberry Pi.

```bash
cd sensor-bridge
python3 huskylens_bridge.py \
  --mode serial \
  --serial-port /dev/ttyAMA0 \
  --baudrate 115200 \
  --camera-id 301 \
  --output-dir ../mediator-owner/raw_data/output
```

The rest of the marketplace components can still run on your main PC.

## Notes

- The generated filenames look like: `301_huskylens_<epoch>.txt`
- Current `mediator-owner/settings/process_rule.json` already accepts `*.txt`, so no rule change is required.
- Use `--max-batches 1` for a one-shot test.
