# HUSKYLENS2サンプル

このサンプルは `sensor-bridge` を使います。

## 入口

```bash
cd sensor-bridge
python3 huskylens_bridge.py --mode mock --output-dir ../mediator-owner/raw_data/output
```

## 実機（serial）

```bash
python3 huskylens_bridge.py --mode serial --serial-port /dev/ttyUSB0 --output-dir ../mediator-owner/raw_data/output
```

## 期待結果

- `mediator-owner/raw_data/output` に `*.txt` 生成
- Frontendに商品が表示
