# USBウェブカメラサンプル（ポイ捨て検知）

## 目的

HUSKYLENS2がなくても、USBウェブカメラだけで
`person_detected` / `possible_littering` イベントを生成します。

## 1. mockで最小確認

```bash
cd webcam-bridge
python3 webcam_litter_bridge.py \
  --mode mock \
  --camera-id 401 \
  --output-dir ../mediator-owner/raw_data/output \
  --flush-seconds 5
```

## 2. 実機（USB webcam）

```bash
python3 webcam_litter_bridge.py \
  --mode webcam \
  --camera-index 0 \
  --camera-id 401 \
  --output-dir ../mediator-owner/raw_data/output \
  --litter-classes bottle,cup \
  --linger-seconds 8 \
  --person-away-seconds 5
```

## 3. 判定ロジック（簡易）

- 人を検出 → `person_detected`
- `bottle/cup` が一定時間残留し、人が近くにいない → `possible_littering`

## 4. 確認ポイント

- `*_webcam_event_*.txt` が生成される
- 商品化されて購入可能になる

## 5. 注意

この検知は学習用のヒューリスティックであり、厳密な判定ではありません。
