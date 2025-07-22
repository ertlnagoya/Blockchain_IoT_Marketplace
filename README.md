# Blockchain IoT Marketplace

![Solidity](https://img.shields.io/badge/Solidity-%23363636.svg?style=for-the-badge&logo=solidity&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)
![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![NPM](https://img.shields.io/badge/NPM-%23CB3837.svg?style=for-the-badge&logo=npm&logoColor=white)
![Vite](https://img.shields.io/badge/vite-%23646CFF.svg?style=for-the-badge&logo=vite&logoColor=white)
![Svelte](https://img.shields.io/badge/svelte-%23f1413d.svg?style=for-the-badge&logo=svelte&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)

## 引継ぎ情報

ブランチ`0704-batch-purchase`で、バッチ購入機能を実装しようとしましたが、失敗しました。  
バッチ購入機能は、複数の商品を一度のコントラクトで購入できる機能です。

## 概要

データ流通を支援する分散型需給マッチングシステムのPoC。ブロックチェーンを用いたIoT機器のデータ流通を追体験できる。
[Blockchain_IoT_Marketplace](https://github.com/ertlnagoya/Blockchain_IoT_Marketplace)に、デプロイされた商品の検索機能を加えたもの。

## requirements

- Docker
- VSCode (Extensions：Docker+DevContainers)

## データセットの準備

`metadata_generator/README.md`を参照してください。

## 起動

### 1. リポジトリをクローン

```bash
git clone git@github.com:ertlnagoya/Blockchain_IoT_Marketplace_enshu_2025.git
```

### 2. hardhat(ブロックチェーンの)セットアップ

```bash
cd iot-market
code .
```

VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行

```bash
npx hardhat node
```

これによって、ローカルネットワークが起動します。

別のターミナルを開いて、以下のコマンドを実行

```bash
npx hardhat run scripts/deployMerchandiseWithIoTMarket.ts --network localhost
```

これによってローカルネットワークに、IoT Marketといくつかのサンプルデータがデプロイされます。  
（注意）コントラクトのデプロイは不安定で、コントラクト名が`Unrecognized Contract`になる失敗がある（DevContainer作成直後は失敗する印象）。  
デプロイしたコントラクト名が正常に表示されていない場合、`npx hardhat node`からやり直す。

### 3. Metamaskのセットアップ

ブラウザの拡張機能である[MetaMask](https://chromewebstore.google.com/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn?hl=ja&utm_source=ext_sidebar)をインストールしてください。  
次にMetaMaskの新規ウォレットを作成してください（パスワードは簡易で覚えやすい`password`を推奨、ここで作成したウォレットは実験では使わないから。）。  
ウオレットの保護は`後で通知`でスキップしてください。  

ブロックチェーンのネットワークを追加してください。  
![How to add a network](./images/how_to_network.png)  

下記の4つの秘密鍵で、アカウントを追加してください。  

```txt
0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

```txt
0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
```

```txt
0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a
```

```txt
0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6
```

参考：[Ethereumのローカルノードを立ち上げて、MetaMaskも使ってみる (hardhat) #Ubuntu - Qiita](https://qiita.com/middle_aged_rookie_programmer/items/26c3d6667c7d6514c1de)

### 4. フロントエンドのセットアップ

```bash
cd iot-market-ui
code .
```

VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行

```bash
npm run dev
```

`localhost:5173`にアクセスすると、フロントエンドが表示されます。

### 5. ストレージサーバーのセットアップ

```bash
cd simple-storage
code .
```

VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行

```bash
cargo run
```

これによって、ストレージサーバーが起動します。ストレージサーバーはポート3000番で待ち受けます。

### 6. IPFS, PostgreSQLのセットアップ

`ipfs/README.md`を参照してください。

### 7. Mediator(owner)のセットアップ

```bash
cd mediator-owner
docker compose up -d
```

これで、Mediatorを複数起動させるためのコンテナを起動します。

```bash
docker exec owner cargo build
```

これで、Mediatorをビルドします。

```bash
docker exec owner python3 -u scripts/run.py
```

これで、Mediatorが複数起動します。
ownerは商品のデプロイとストレージサーバーへのファイルのアップロードを行います。

### 8. Mediator(buyer)のセットアップ

VSCodeを開いたら、`> DevContainer: Rebuild and Reopen in Container`を選択してコンテナに入る。

続いて、以下のコマンドを実行

```bash
cargo run --bin mediator-b
```

これで、Mediatorが起動します。
buyerはUIで購入した商品のダウンロードを行います。

### 9. 購入手続きを行う

`localhost:5173`にアクセスし、metamaskでアカウントをbuyerのもの（UUIDが`0x3c`で始まるもの）に切り替えてください。  
その後、mediator(owner)の実行によってデプロイされた商品を購入してください。  
UIで検索し、検索にヒットした商品をそれぞれ購入できます。
正しくセットアップされていれば、buyerはイベントをキャッチしてストレージサーバーから`downloads/`にファイルをダウンロードするはずです。

## Tips

- システムを再起動すると、ローカルネットワークのブロックとMetaMaskが持つブロックがずれることがある
  - 解決するときの手順
    1. MetaMaskの設定->高度な設定->アクティビティタブのデータを消去
    2. ブラウザを閉じる
    3. DevContainerを再起動し、各種コンポーネントを起動
    4. ブラウザでMetaMaskを開き、ログイン
    5. それぞれのアカウントのデポジットは回復しているはず
