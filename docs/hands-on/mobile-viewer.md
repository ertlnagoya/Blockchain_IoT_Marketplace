# スマホ閲覧アプリ

## 目的

スマホからイベントフィードを閲覧し、必要なデータを購入できることを確認します。

## 1. PC側をLAN公開で起動

```bash
cd iot-market-ui
npm run dev -- --host 0.0.0.0 --port 5173
```

## 2. PCのLAN IPを確認

```bash
ipconfig getifaddr en0
```

## 3. スマホでアクセス

```txt
http://<PCのLAN_IP>:5173/mobile
```

## 4. 購入時の注意

- スマホで購入する場合は MetaMaskモバイル内ブラウザを推奨

## 5. 確認ポイント

- イベントフィードが表示される
- フィルタが使える
- 購入後、履歴タブに記録される
