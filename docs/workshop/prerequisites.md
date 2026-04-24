# 事前準備

## 必須ソフト

- Docker
- VSCode + Dev Containers
- Node.js / npm
- Rust / Cargo
- Git

## 推奨

- Docker Desktop（`host.docker.internal` を使うため）
- MetaMask

## 受講者向けチェック

```bash
docker --version
npm -v
cargo --version
```

```bash
git clone --recursive https://github.com/ertlnagoya/Blockchain_IoT_Marketplace.git
cd Blockchain_IoT_Marketplace
```

## 講師向けチェック

1. デモ用アカウント（MetaMask）を事前用意
2. `iot-market` デプロイ済みログを確認
3. `ipfs` / PostgreSQL のテーブル作成完了を確認
4. サンプル入力（HUSKYLENS2またはWebcam）の動作確認
