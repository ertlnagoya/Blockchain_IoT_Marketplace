# Data Generator / 格納用データ生成

<p align="center">
  <a href="#english-readme">English README</a> ｜ <a href="#日本語-readme">日本語 README</a>
</p>

---

## English README

Generate videos and JSON metadata from raw frames (with bounding boxes). This tool only reads local images and does not upload anything.

### Preparation

```bash
# (Optional) System packages for OpenCV
sudo apt -y update && sudo apt -y upgrade
sudo apt -y install libopencv-dev
```

```bash
# Create venv and install Python deps
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Dataset

```bash
# Download and extract the source frames (MeVID test annotations)
curl -L -o mevid-v1-bbox-test.tgz \
  https://mevadata-public-01.s3.amazonaws.com/mevid-annotations/mevid-v1-bbox-test.tgz
tar xzf mevid-v1-bbox-test.tgz
```

### Generate videos and metadata

```bash
python3 movie_generator.py \
  --frames_dir <path-to-mevid-v1-bbox-test> \
  --output_dir outputs/output
```

### Move outputs for next steps

```bash
mv outputs/output mediator-owner/raw_data/
```

### Notes

- Heavy processing. If it’s too slow or crashes, reduce max_workers in movie_generator.py.

---

## 日本語 README

生フレーム（バウンディングボックス付き）から動画と JSON メタデータを生成します。本ツールはローカル画像のみを読み込み、アップロードは行いません。

### 準備

```bash
# （任意）OpenCV 用のシステムパッケージ
sudo apt -y update && sudo apt -y upgrade
sudo apt -y install libopencv-dev
```

```bash
# 仮想環境の作成と依存関係のインストール
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### データセット

```bash
# 元フレーム（MeVID test annotations）のダウンロードと展開
curl -L -o mevid-v1-bbox-test.tgz \
  https://mevadata-public-01.s3.amazonaws.com/mevid-annotations/mevid-v1-bbox-test.tgz
tar xzf mevid-v1-bbox-test.tgz
```

### 動画・メタデータ生成

```bash
python3 movie_generator.py \
  --frames_dir <path-to-mevid-v1-bbox-test> \
  --output_dir outputs/output
```

### 次工程用に移動

```bash
mv outputs/output mediator-owner/raw_data/
```

### 注意事項

- 処理が重いです。負荷が高い場合は movie_generator.py の max_workers を下げてください。
