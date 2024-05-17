# Blockchain IoT Marketplace
![Solidity](https://img.shields.io/badge/Solidity-%23363636.svg?style=for-the-badge&logo=solidity&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)
![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![NPM](https://img.shields.io/badge/NPM-%23CB3837.svg?style=for-the-badge&logo=npm&logoColor=white)
![Vite](https://img.shields.io/badge/vite-%23646CFF.svg?style=for-the-badge&logo=vite&logoColor=white)
![Svelte](https://img.shields.io/badge/svelte-%23f1413d.svg?style=for-the-badge&logo=svelte&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)


## 概要
データ流通を支援する分散型需給マッチングシステム
のPoC。ブロックチェーンを用いたIoT機器のデータ流通を追体験できる。

データ流通までのワークフロー
```mermaid
sequenceDiagram
    autonumber
    participant Mediator(IoTOwner)
    actor iotOwner as IoTオーナー
    participant Merchandise
    participant IoTMarketplace as マーケットプレイス
    participant Frontend as UIアプリケーション
    actor buyer as データ購入者
    participant Mediator(buyer)
    Mediator(IoTOwner)->>IoTMarketplace: Deploy
    Note right of Mediator(IoTOwner): Hash値などメタデータ
    IoTMarketplace->>Merchandise: コンストラクタ
    buyer->>Frontend: データ購入リクエスト
    Note left of buyer: ウォレットによる署名
    Frontend->>Merchandise: purchase
    Mediator(buyer)->>Mediator(IoTOwner): 実データの要求
    Mediator(buyer)->>Mediator(buyer):Hash()
    Mediator(buyer)->>Merchandise: verify()
    Mediator(IoTOwner)->>Merchandise: withdraw()
```

## requirements
- Docker
- VSCode (Extensions：Docker+DevContainers)

## セットアップ
### 1. リポジトリをクローン
```
git clone --recursive https://github.com/ertlnagoya/Blockchain_IoT_Marketplace.git
```

### 2. hardhat(ブロックチェーンの)セットアップ
```
$ cd iot-market
$ code .
```
VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行
```
$ npx hardhat node
```
これによって、ローカルネットワークが起動します。

別のターミナルを開いて、以下のコマンドを実行
```
$ npx hardhat run scripts/deployMerchandiseWithIoTMarket.ts --network localhost
```
これによってローカルネットワークに、IoT Marketといくつかのサンプルデータがデプロイされます。

### 3. Metamaskのセットアップ
ブラウザの拡張機能であるMetamaskをインストールしてください。
以下のサイトを参考にローカルネットワークのアカウント0~3をMetamaskに追加してください

参考：[Ethereumのローカルノードを立ち上げて、MetaMaskも使ってみる (hardhat) #Ubuntu - Qiita](https://qiita.com/middle_aged_rookie_programmer/items/26c3d6667c7d6514c1de)


### 4. フロントエンドのセットアップ
```
$ cd iot-market-ui
$ code .
```
VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行
```
$ npm run dev
```
`localhost:5173`にアクセスすると、フロントエンドが表示されます。

### 5. ストレージサーバーのセットアップ
```
$ cd simple-storage
$ code .
```
VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行
```
$ cargo run
```
これによって、ストレージサーバーが起動します。ストレージサーバーはポート3000番で待ち受けます。

### 6. Mediator(owner)のセットアップ
```
$ cd mediator-owner
$ code .
```
VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行
```
$ cargo run
```
これによって、Mediatorが起動します。
ownerは商品のデプロイとストレージサーバーへのファイルのアップロードを行います。

### 7. Mediator(buyer)のセットアップ
```
$ cd mediator-buyer
$ code .
```
以降、手順6と同様にMediator(buyer)をセットアップしてください。

### 8. 購入手続きを行う
`localhost:5173`にアクセスし、metamaskでアカウントをbuyerのものに切り替えてください。その後、mediator(owner)の実行によってデプロイされた商品を購入してください。正しくセットアップされていれば、buyerはイベントをキャッチしてストレージサーバーからファイルをダウンロードするはずです。

![How it works](./images/how_it_works.png)