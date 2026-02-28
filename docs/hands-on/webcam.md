# USBウェブカメラサンプル（ポイ捨て検知）

このサンプルは `webcam-bridge` を使います。

## 入口（mock）

```bash
cd webcam-bridge
python3 webcam_litter_bridge.py --mode mock --output-dir ../mediator-owner/raw_data/output
```

## 実機（USB webcam）

```bash
python3 webcam_litter_bridge.py --mode webcam --camera-index 0 --output-dir ../mediator-owner/raw_data/output
```

## イベント

- `person_detected`
- `possible_littering`

## 期待結果

- `*_webcam_event_*.txt` が出力される
- 商品化され、購入可能になる
