# stream-server モジュール

ブロックチェーンを用いたIoT機器のデータ流通フレームワークを利用した、カメラ映像をストリーミングするためのモジュールです

## 環境

カメラ側のデバイスにffmpegをインストールしてください

サーバ側はDocker Composeが使える環境が必要です、重いのでラズパイに載せるのは非推奨

購入者側はrtmpプロトコルのネットワークストリームが再生できるメディアプレイヤーが必要です（VLCなど）

## 実行方法

### サーバの起動
```bash
docker compose up
```
コンテナ起動後は自動でサーバーが起動、認証・配信待ちになります

テスト環境ではbridgeネットワークが動作しなかったので、サーバはhostネットワークで起動します（あまり望ましくない）。bridgeネットワークが動作する環境の場合`docker-compose.yaml`内、`network_mode: "host"`を削除してください

### ストリーミング
カメラ側デバイスに必要なのは`cam.sh`ファイルのみです

カメラ側デバイスに`cam.sh`ファイルをコピー、必要に応じて以下を変更してください

`cam.sh`ファイル内
```bash
stream_server='localhost'
mediator='../mediator-owner/raw_data'
```
ストリームサーバをカメラとは別デバイスに置く場合、`stream_server`をサーバのアドレスに変更

`mediator`には`mediator-owner`の生データの格納ディレクトリのパスを指定してください

`iot-market`,`iot-market-ui`,`simple-storage`,`mediator-buyer`,`mediator-owner`,`stream-server`をすべて起動してから、スクリプトを実行してください。指定したサーバにストリーミングを開始します
```bash
chmod +x ./cam.sh
./cam.sh
```
htmlファイルがデプロイされるので購入します。ダウンロードされたhtmlファイルは普通に開けばブラウザがメディアプレイヤーで開くようプロンプトしてくれます。されない場合、htmlの中にあるrtmp://から始まるリンクを開いてください