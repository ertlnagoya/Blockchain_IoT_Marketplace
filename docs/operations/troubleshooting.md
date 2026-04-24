# トラブルシュート

## 1. `host.docker.internal` の接続エラー

- DevContainer / Docker Desktop 前提を確認
- 直接ホスト実行している場合はネットワーク設定を見直す

## 2. IPFSコンテナが再起動ループ

- `ipfs/docker-compose.yaml` の image を `ipfs/kubo:latest` にする

## 3. スマホから `/mobile` が開けない

- `npm run dev -- --host 0.0.0.0 --port 5173` で起動したか
- PCとスマホが同一ネットワークか
- PCのFWで5173が遮断されていないか

## 4. 商品が表示されない

- `mediator-owner` の実行引数を確認: `cargo run -- settings/owner_1.yaml`
- `raw_data/output` にファイルが作成されているか確認

## 5. 購入できない

- MetaMaskの接続アカウントを確認
- ローカルチェーン再起動後はMetaMaskのキャッシュをクリア
