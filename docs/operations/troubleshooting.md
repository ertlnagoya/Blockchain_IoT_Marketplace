# トラブルシュート

## 1. `host.docker.internal` で接続失敗

- DevContainer / Docker Desktop 前提を確認
- ホスト名が解決できない場合はコンテナ設定を見直す

## 2. IPFSコンテナが再起動ループ

- `ipfs/docker-compose.yaml` のイメージを確認（`ipfs/kubo:latest`）

## 3. スマホから `/mobile` が開けない

- `--host 0.0.0.0` で起動したか
- PCとスマホが同一ネットワークか
- FWで5173が遮断されていないか

## 4. 商品が増えない

- `mediator-owner` の `rawdata_dir` を確認
- `raw_data/output` にイベントファイルができているか確認
