# ログフォルダ

このフォルダは、Hardhat のテストを実行した際に Gas の推定量を出力するための Hardhat Gas Reporter の出力先です。

## 使用方法

1. テストを実行する前に、Hardhat Gas Reporter をインストールしてください。

   ```shell
   npm install --save-dev hardhat-gas-reporter
   ```

2. Hardhat の設定ファイル（`hardhat.config.js`）に、Gas Reporter の設定を追加してください。

   ```typescript
   // hardhat.config.js
   // toolboxはgas-reporterを含む
   import "@nomicfoundation/hardhat-toolbox";

   module.exports = {
     // ...他の設定...
     gasReporter: {
       enabled: true,
     },
   };
   ```

3. テストを実行すると、Gas Reporter がログフォルダに推定量の出力を生成します。

## 注意事項

- Gas Reporter は、テストネットワークやメインネットワークでの使用に適しています。
- ログフォルダは、テストごとに新しいファイルが作成されます。
