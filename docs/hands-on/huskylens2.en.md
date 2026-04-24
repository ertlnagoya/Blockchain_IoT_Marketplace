# HUSKYLENS2 Sample

## Mock first

```bash
cd sensor-bridge
python3 huskylens_bridge.py --mode mock --output-dir ../mediator-owner/raw_data/output
```

## Real device (serial)

```bash
python3 huskylens_bridge.py --mode serial --serial-port /dev/ttyUSB0 --output-dir ../mediator-owner/raw_data/output
```

## Expected

- `301_huskylens_*.txt` appears under `raw_data/output`
- Owner mediator detects and productizes
