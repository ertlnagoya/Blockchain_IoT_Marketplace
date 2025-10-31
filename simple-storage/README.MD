# simple-storage / シンプルストレージ

<p align="center">
  <a href="#english-readme">English README</a> ｜ <a href="#日本語-readme">日本語 README</a>
</p>

---

## English README

A minimal file storage server written in Rust (Axum). Supports upload, list, and download.

### Run

```bash
# Run locally
cargo run
# Server listens on http://localhost:3000
```

### API Examples

Health check
```bash
curl -X GET 'http://localhost:3000/'
```

Upload
```bash
curl -X POST -F file=@path/to/yourfile.ext 'http://localhost:3000/upload'
# => {"upload_path":"<UUID>"}  # Keep this UUID to download later
```

List uploaded files
```bash
curl -X GET 'http://localhost:3000/list'
```

Download
```bash
# Use the UUID returned by /upload as the key
curl -L -OJ 'http://localhost:3000/download?key=<UUID>'
# -O: write to file, -J: use server-provided filename
```

Notes
- Upload directory: uploads
- Max upload size: ~50MB (DefaultBodyLimit)

---

## 日本語 README

Rust（Axum）で実装したシンプルなファイル保存サーバーです。アップロード、一覧、ダウンロードを提供します。

### 起動

```bash
# ローカル実行
cargo run
# http://localhost:3000 で待ち受け
```

### コマンド例

ヘルスチェック
```bash
curl -X GET 'http://localhost:3000/'
```

アップロード
```bash
curl -X POST -F file=@path/to/yourfile.ext 'http://localhost:3000/upload'
# => {"upload_path":"<UUID>"}  # 後でダウンロードするため、このUUIDを控えておく
```

アップロード済み一覧
```bash
curl -X GET 'http://localhost:3000/list'
```

ダウンロード
```bash
# /upload の応答で得た UUID を key として使用
curl -L -OJ 'http://localhost:3000/download?key=<UUID>'
# -O: ファイルに保存, -J: サーバー指定のファイル名を使用
```

補足
- 保存先ディレクトリ: uploads
- 最大アップロードサイズ: 約50MB（DefaultBodyLimit）