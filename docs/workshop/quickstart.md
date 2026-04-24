# 最短起動

この章は「まず全体を動かす」ための最短手順です。

## 起動順

1. `iot-market`（ローカルチェーン + デプロイ）
2. `iot-market-ui`（フロントエンド）
3. `simple-storage`（データ保存）
4. `ipfs`（IPFS + PostgreSQL）
5. `mediator-owner`
6. `mediator-buyer`

## 主要コマンド

```bash
cd iot-market
npx hardhat node
```

別ターミナル:

```bash
cd iot-market
npx hardhat run scripts/deployMerchandiseWithIoTMarket.ts --network localhost
```

```bash
cd iot-market-ui
npm run dev
```

```bash
cd simple-storage
cargo run
```

```bash
cd ipfs
docker compose up -d
```

```bash
cd mediator-owner
cargo run -- settings/owner_1.yaml
```

```bash
cd mediator-buyer
cargo run --bin mediator-b
```

## 成功判定

- フロントが開く: `http://localhost:5173`
- 商品一覧が取得できる
- エラーで停止しているプロセスがない

## メタマスク設定イメージ

![MetaMask Network 設定例](../assets/how_to_network.png)
