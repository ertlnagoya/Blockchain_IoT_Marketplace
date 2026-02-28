# 最短起動

この章では、まず基盤を動かすことに集中します。

## 起動順

1. `iot-market`: ローカルチェーン + デプロイ
2. `iot-market-ui`: フロントエンド
3. `simple-storage`: ストレージサーバ
4. `ipfs`: IPFS + PostgreSQL
5. `mediator-owner`
6. `mediator-buyer`

## 例（抜粋）

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

詳しい注意点は、ルートの [README_ja.md](../../README_ja.md) を参照してください。
