# 格納用データ生成

本システムに格納するための、動画データ・メタデータを生成する。

## requirements

- Python 3.12
  - venvをインストールする
（requirements.txtのものが動けばよいから、他バージョンでも大丈夫かも）

## 環境構築

Pythonの環境を構築する。

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

生成する動画の元データを[mevid-v1-bbox-test](https://mevadata-public-01.s3.amazonaws.com/mevid-annotations/mevid-v1-bbox-test.tgz)からダウンロードする。

そして、これを展開しておく。

## 動画・メタデータ生成

下記コマンドで生成する。  
時間がかかるので並列処理を入れている。  
PCの性能によっては、`movie_generator.py`の`max_workers`を減らさないと、重くてクラッシュするかも。

```bash
python3 movie_generator.py --frames_dir <path-to-mevid-v1-bbox-test> --output_dir outputs/output
```

生成した`outputs/output`は`mediator-owner/raw_data/`に移動する。
