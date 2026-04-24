# Docs Site (MkDocs, ja/en)

このディレクトリは、Workshop/Hands-on向けの多言語ドキュメントサイトです。

## 構成

- 既定言語: 日本語（`*.md`）
- 英語版: `*.en.md`
- ルーティング: `mkdocs-static-i18n` の `suffix` 構成

例:
- `docs/workshop/quickstart.md`（日本語）
- `docs/workshop/quickstart.en.md`（英語）

## ローカル起動

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

- URL: `http://127.0.0.1:8000`

## ビルド

```bash
mkdocs build --strict
```

- 出力: `site/`

## GitHub Pages 公開テンプレート

このリポジトリには Pages 公開用ワークフローを同梱しています。

- Workflow: `.github/workflows/docs-pages.yml`
- トリガー: `main` への push（`docs/**`, `mkdocs.yml` 変更時）

### 必要な設定（GitHub Repository）

1. `Settings` → `Pages`
2. `Build and deployment` の Source を `GitHub Actions` に設定
3. `mkdocs.yml` の `site_url` を実リポジトリURLに合わせる
   - 例: `https://<user>.github.io/<repo>/`
