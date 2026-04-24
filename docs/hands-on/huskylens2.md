# HUSKYLENS2サンプル

## 目的

HUSKYLENS2（または中継入力）からイベントを作り、商品化までを確認します。

## 1. mockで最小確認

```bash
cd sensor-bridge
python3 huskylens_bridge.py \
  --mode mock \
  --camera-id 301 \
  --output-dir ../mediator-owner/raw_data/output \
  --flush-interval-sec 8
```

## 2. 実機（serial）

```bash
python3 huskylens_bridge.py \
  --mode serial \
  --serial-port /dev/ttyUSB0 \
  --baudrate 115200 \
  --camera-id 301 \
  --output-dir ../mediator-owner/raw_data/output
```

## 3. 確認ポイント

- `raw_data/output` に `301_huskylens_*.txt` が作成される
- `mediator-owner` ログに watcher event が出る
- フロントに商品が反映される

## 4. トラブル時

- `pyserial` 未導入: `pip install pyserial`
- ポート不明: `/dev/tty.usbserial-*` などを確認
