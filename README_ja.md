# IoTxWeb3 Intelligence Platform (IW3IP)

## Home Assistant x SSI Data Publisher サンプル（Phase 1）

Language: [English](README.md) | **日本語**

このブランチは、ユーザー主権型データ共有の最小かつ拡張可能なプロトタイプです。

Home Assistant -> MQTT -> (任意 Node-RED) -> Data Publisher -> Data Sharing Platform API

Data Publisher は受信データを正規化し、Consent VC ポリシーを評価し、許可されたデータのみ送信し、監査ログを記録します。

## このサンプルで分かること

このサンプルは、Home Assistant データを SSI/DID/VC の考え方で共有するための最小実装です。

- Home Assistant の state/event データを MQTT で受信
- 共通スキーマへ正規化し、`dataset_id` を付与
- Consent VC の条件（`dataset_id` / `purpose` / 有効期間）を判定
- 許可データのみ Platform API へ送信
- `allow` / `deny` / `send_error` を SQLite 監査ログへ保存

対象データセット例:
- `home/env/temperature`
- `home/energy/power`
- `home/event/person_detected`
- `home/event/flood_risk_high`
- `home/event/possible_littering`

## 実行環境

### 必須

- Docker / Docker Compose（`docker compose` が利用可能）
- Python 3.11+（ローカル実行・テスト時）

### 採用技術（本実装）

- FastAPI + pydantic（Data Publisher）
- Eclipse Mosquitto（MQTT）
- SQLite（監査ログDB）
- pytest（テスト）
- uv（依存管理・ローカル実行例）

### このブランチでの確認項目

- `docker compose -f infra/docker-compose.yml up --build`
- `GET /health`
- `POST /consents`
- `POST /simulate/publish`
- `mosquitto_pub` による MQTT 取り込みと監査ログ記録

## はじめてガイド（初心者向け）

初めて触る場合は、このセクションを上から順に実行してください。

### 0. 事前チェック（そのまま実行）

```bash
docker --version
docker compose version
curl --version
```

期待結果:
- すべてバージョンが表示される
- `command not found` が出ない

### 1. システム起動

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

期待結果:
- `iw3ip-mosquitto` と `iw3ip-publisher` が `Up`

確認コマンド:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

### 2. API疎通確認

```bash
curl http://localhost:8080/health
```

期待結果:

```json
{"status":"ok","service":"publisher"}
```

### 3. サンプルConsentをすべて登録

```bash
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_temperature.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_power.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_person_detected.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_flood_risk_high.json
curl -X POST http://localhost:8080/consents -H 'Content-Type: application/json' -d @examples/consent_possible_littering.json
```

期待結果:
- 各レスポンスに `"status":"stored"` を含む

Phase 2 用のサンプルファイル:
- `examples/consent_flood_risk_high.json`
- `examples/consent_possible_littering.json`
- `examples/payload_flood_risk_high.json`
- `examples/payload_possible_littering.json`

### 4. 許可されるケースを試す（HTTP疑似投入）

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/state/sensor/temperature",
    "payload":{
      "entity_id":"sensor.living_room_temperature",
      "state":"24.1",
      "attributes":{"unit_of_measurement":"C"},
      "ts":"2026-02-28T10:00:00Z",
      "source":"home_assistant"
    },
    "purpose":"research"
  }'
```

期待結果:

```json
{"status":"allowed","dataset_id":"home/env/temperature"}
```

### 5. 拒否されるケースを試す（purpose不一致）

```bash
curl -X POST http://localhost:8080/simulate/publish \
  -H 'Content-Type: application/json' \
  -d '{
    "topic":"homeassistant/state/sensor/power",
    "payload":{
      "entity_id":"sensor.main_power",
      "state":"520",
      "attributes":{"unit_of_measurement":"W"},
      "ts":"2026-02-28T10:00:10Z",
      "source":"home_assistant"
    },
    "purpose":"marketing"
  }'
```

期待結果:

```json
{"status":"denied","dataset_id":"home/energy/power","reason":"no_matching_consent"}
```

### 6. 監査ログ確認

```bash
curl http://localhost:8080/audit/logs?limit=5
```

期待結果:
- `allow` と `deny` が記録される
- 各行に `message_hash`、`dataset_id`、`purpose` がある

### 7. MQTT経路を試す

```bash
docker exec -i iw3ip-mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t homeassistant/event/person_detected \
  -m '{"event_type":"person_detected","data":{"camera_id":"front_door","confidence":0.93},"ts":"2026-02-28T10:00:20Z","source":"edge_inference"}'
```

再度ログ確認:

```bash
curl http://localhost:8080/audit/logs?limit=5
```

### 8. 停止

```bash
docker compose -f infra/docker-compose.yml down
```

## スコープ

- Phase 1（実装済み）: データ交換パイプライン + 同意ベース判定 + 監査ログ
- Phase 2（設計フック）: イベント指向共有（推論結果など）
- Phase 3（設計フック）: SSI Gateway / PEP 前段配置

## Phase 3 地域安全アシスタントサンプル

このブランチでは、自然言語の要求を解釈し、タスク分解し、イベント評価を行い、ダミー機器操作まで実行する Phase 3 の最小プロトタイプも追加しています。

流れ:

`人間の要求 -> planner -> 実行計画 -> イベント評価 -> 機器操作コマンド`

実装済み API:
- `GET /health`
- `POST /assistant/plan`
- `POST /assistant/execute`
- `GET /assistant/executions`

最小の要求例:

```json
{
  "request_text": "公園北側でポイ捨てや危険行動が増えていたら教えて。必要なら照明をつけて管理者に通知して。"
}
```

主なサンプルファイル:
- `examples/phase3_request_park_safety.json`
- `examples/phase3_events_park_safety.json`
- `assistant/app/main.py`
- `assistant/app/planner.py`
- `assistant/app/planner_interface.py`
- `assistant/app/planner_factory.py`
- `assistant/app/rule_based_planner.py`
- `assistant/app/llm_planner.py`
- `assistant/app/llm_prompt.py`
- `assistant/app/llm_provider.py`
- `assistant/app/plan_validator.py`
- `assistant/app/evaluator.py`
- `assistant/app/actuator.py`

最小実行例:

```bash
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

計画生成の例:

```bash
curl -X POST http://localhost:8090/assistant/plan \
  -H 'Content-Type: application/json' \
  -d @examples/phase3_request_park_safety.json
```

このレスポンスには `planner_diagnostics` も含まれます。例:

```json
{
  "planner_diagnostics": {
    "status": "fallback",
    "severity": "warning",
    "label": "Fallback",
    "color_hint": "amber",
    "code": "llm_provider_error",
    "category": "provider",
    "user_message": "The LLM API could not be used, so the rule-based planner was used instead.",
    "planner_mode": "llm",
    "provider_name": "openai_compatible",
    "used_fallback": true,
    "error_type": "LLMProviderError",
    "error_message": "model response is not valid JSON"
  }
}
```

見やすくするための項目:

- `status`
  - `ok` または `fallback`
- `severity`
  - `info`, `warning`, `error`
- `label`
  - `OK` や `Fallback` のような短いバッジ表示用文字列
- `color_hint`
  - `green`, `amber`, `red` のような色分け用ヒント
- `code`
  - `llm_provider_error` のような機械判定しやすい固定コード
- `category`
  - `success`, `provider`, `validation`, `planner` のような大分類
- `user_message`
  - フロントにそのまま表示しやすい短い説明文
- `summary`
  - 人間向けの短い説明
- `suggestion`
  - 次に確認すべき内容

実行の例:

```bash
curl -X POST http://localhost:8090/assistant/execute \
  -H 'Content-Type: application/json' \
  -d @examples/phase3_request_park_safety.json
```

### Phase 3 planner モード

assistant は、planner の選択と planner 本体を分離した構成になりました。

- `ASSISTANT_PLANNER_MODE=rule_based`
  - `RuleBasedPlanner` を使う
- `ASSISTANT_PLANNER_MODE=llm`
  - `LLMPlanner` を使う
- `ASSISTANT_LLM_PROVIDER=stub`
  - 外部 API に依存しないローカル provider
- `ASSISTANT_LLM_PROVIDER=openai_compatible`
  - 実際の OpenAI 互換 `/chat/completions` API を呼び出す
- `ASSISTANT_LLM_API_BASE_URL`
- `ASSISTANT_LLM_API_KEY`
- `ASSISTANT_LLM_MODEL`

現在の `LLMPlanner` は、`ExecutionPlan` の出力契約を維持しつつ、`llm_prompt.py` で prompt を組み立て、許可イベント・許可アクション・許可エリアを validator で確認し、失敗時は rule-based planner にフォールバックします。

例:

```bash
ASSISTANT_PLANNER_MODE=llm \
ASSISTANT_PLANNER_NAME=llm-planner-stub-v1 \
ASSISTANT_LLM_PROVIDER=stub \
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

実 API の例:

```bash
ASSISTANT_PLANNER_MODE=llm \
ASSISTANT_PLANNER_NAME=llm-planner-openai-compatible-v1 \
ASSISTANT_LLM_PROVIDER=openai_compatible \
ASSISTANT_LLM_API_BASE_URL=https://api.openai.com/v1 \
ASSISTANT_LLM_API_KEY=REPLACE_WITH_YOUR_API_KEY \
ASSISTANT_LLM_MODEL=gpt-4.1-mini \
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

ローカル HTTP mock の例:

```bash
uvicorn examples.phase3_llm_mock_server:app --host 127.0.0.1 --port 18000
```

別ターミナルで:

```bash
source examples/phase3_llm_mock.env.example
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

対応する example:

- `.env.local.example`
- `examples/phase3_llm.env.example`
- `examples/phase3_llm_mock.env.example`
- `examples/phase3_llm_expected_plan.json`
- `examples/phase3_request_station_warning.json`
- `examples/phase3_llm_mock_server.py`

推奨するローカル設定:

```bash
cp .env.local.example .env.local
source .env.local
```

Docker Compose の例:

```bash
docker compose -f infra/docker-compose.yml --profile assistant-llm up --build -d assistant-llm
```

Docker Compose で local HTTP mock を使う例:

```bash
docker compose -f infra/docker-compose.yml --profile llm-mock up --build -d llm-mock
source examples/phase3_llm_mock.env.example
uvicorn assistant.app.main:app --host 0.0.0.0 --port 8090
```

`openai_compatible` のよくあるつまずき:

- `401 Unauthorized`
  - `ASSISTANT_LLM_API_KEY` を確認してください
- `404` または `405`
  - `ASSISTANT_LLM_API_BASE_URL` を確認してください
- いつも rule-based planner にフォールバックする
  - model が JSON を返しているか確認してください

演習用 pytest:

```bash
pytest -q tests/test_phase3_llm_hands_on_program.py
```

TODO を埋めた後に問題用プログラムへ向ける場合:

```bash
PHASE3_LLM_HANDS_ON_MODULE=examples.hands_on.phase3_llm_planner.problem_program \
pytest -q tests/test_phase3_llm_hands_on_program.py
```

実 LLM API の調査時は、次も確認してください。

```bash
curl http://localhost:8090/assistant/executions
```

`planner_diagnostics.error_type`, `planner_diagnostics.error_message`, `planner_diagnostics.used_fallback` を見ると原因を追いやすくなります。

## Phase 2 のサンプルファイル

ウェブサイト側の Phase 2 Hands-on と、ソースコードリポジトリ側のファイル名・JSON 内容が一致するように、Phase 2 用のサンプルファイルも追加しています。

- `examples/consent_flood_risk_high.json`
  - `home/event/flood_risk_high` を `disaster_response` と `research` で許可
- `examples/consent_possible_littering.json`
  - `home/event/possible_littering` を `community_cleaning` と `research` で許可
- `examples/payload_flood_risk_high.json`
  - 防災イベント共有用のサンプル payload
- `examples/payload_possible_littering.json`
  - ポイ捨てイベント共有用のサンプル payload

すぐに Phase 2 を試したい場合は、`examples/README.md` とウェブサイト側の Hands-on にある:
- 環境・防災イベント共有
- USBウェブカメライベント共有
を参照してください。

問題用プログラムと解答用プログラムを使うワークショップ形式にしたい場合は、次を参照してください。

- `examples/hands_on/README.md`
- `examples/hands_on/huskylens2_mock/`
- `examples/hands_on/webcam_littering_mock/`
- `examples/hands_on/mobile_viewer/`
- `examples/hands_on/phase1_ha_ssi_publisher/`
- `examples/hands_on/phase2_environment_disaster/`
- `examples/hands_on/phase2_webcam_event_sharing/`
- `examples/hands_on/phase3_llm_planner/`

## ディレクトリ構成

- `assistant/` : Phase 3 地域安全アシスタント（planner interface / factory / rule-based planner / 最小 LLM planner / evaluator / actuator / API）
- `publisher/` : FastAPI ベース Data Publisher
- `schemas/` : 正規化スキーマ
- `policy/` : Consent VC モデル、署名検証インタフェース、ポリシー判定
- `audit/` : 監査DBアクセス層（現状 SQLite、将来差し替え可能）
- `infra/` : docker compose、Mosquitto設定、任意 Node-RED
- `examples/` : サンプル payload / Consent VC / Phase 3 用 request / event / 動作確認コマンド
- `tests/` : pytest（policy / normalization / audit / assistant）

## クイックスタート（Docker）

### 1. サービス起動

```bash
docker compose -f infra/docker-compose.yml up --build
```

起動されるサービス:
- `mosquitto`（MQTT broker）
- `publisher`（FastAPI + MQTT subscriber）
- `nodered`（任意、profile: `nodered`）

### 2. ヘルスチェック

```bash
curl http://localhost:8080/health
```

期待結果:

```json
{"status":"ok","service":"publisher"}
```

### 3. Consent VC 登録

```bash
curl -X POST http://localhost:8080/consents \
  -H 'Content-Type: application/json' \
  -d @examples/consent_temperature.json
```

### 4. Home Assistant 形式 MQTT メッセージ送信

```bash
docker exec -i iw3ip-mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t homeassistant/state/sensor/temperature \
  -m '{"entity_id":"sensor.living_room_temperature","state":"24.1","attributes":{"unit_of_measurement":"C"},"ts":"2026-02-28T10:00:00Z","source":"home_assistant"}'
```

### 5. 監査ログ確認

```bash
curl http://localhost:8080/audit/logs
```

許可条件を満たす場合、`allow` が記録されます。

## ローカル実行（uv）

### 1. 依存インストール

```bash
uv sync
```

### 2. Publisher 起動

```bash
uv run uvicorn publisher.app.main:app --host 0.0.0.0 --port 8080
```

## 設定（環境変数）

- `PUBLISHER_ID`（既定: `publisher-001`）
- `DEFAULT_PURPOSE`（既定: `research`）
- `MQTT_BROKER_HOST`（既定: Docker は `mosquitto` / ローカルは `localhost`）
- `MQTT_BROKER_PORT`（既定: `1883`）
- `MQTT_TOPICS`（既定: `homeassistant/state/+/+,homeassistant/event/+`）
- `PLATFORM_API_URL`（既定: Docker で `http://publisher:8080/platform/ingest`）
- `AUDIT_DB_PATH`（既定: `./audit/audit.db`）
- `CONSENT_STORE_PATH`（任意、Consent 永続化先）

## Home Assistant -> MQTT 送信例

### Topic 1: temperature state

- Topic: `homeassistant/state/sensor/temperature`
- Payload:

```json
{
  "entity_id": "sensor.living_room_temperature",
  "state": "24.1",
  "attributes": {"unit_of_measurement": "C"},
  "ts": "2026-02-28T10:00:00Z",
  "source": "home_assistant"
}
```

### Topic 2: power state

- Topic: `homeassistant/state/sensor/power`
- Payload:

```json
{
  "entity_id": "sensor.main_power",
  "state": "520",
  "attributes": {"unit_of_measurement": "W"},
  "ts": "2026-02-28T10:00:10Z",
  "source": "home_assistant"
}
```

### Topic 3: person_detected event

- Topic: `homeassistant/event/person_detected`
- Payload:

```json
{
  "event_type": "person_detected",
  "data": {"camera_id": "front_door", "confidence": 0.93},
  "ts": "2026-02-28T10:00:20Z",
  "source": "edge_inference"
}
```

## API

- `GET /health`
- `GET /consents`
- `POST /consents`
- `DELETE /consents/{vc_id}`
- `POST /simulate/publish`（MQTTなし疑似投入）
- `GET /audit/logs`（確認用）
- `POST /platform/ingest`（ダミー受信エンドポイント）

## ポリシー判定（Phase 1）

以下をすべて満たす場合に送信許可:

1. `dataset_id` が一致する Consent が存在
2. `purpose` が `allowed_purposes` に含まれる
3. 現在時刻が `valid_from`〜`valid_to` の範囲内

不許可の場合、送信せずに監査ログへ `deny` を記録します。

## 監査ログ

SQLite テーブル `audit_log`:

- `id`
- `ts`
- `action`（`allow`, `deny`, `send_error`）
- `subject_did`
- `dataset_id`
- `purpose`
- `reason`
- `message_hash`（SHA-256）
- `raw_topic`

## テスト

```bash
uv run pytest -q
```

対象:
- policy 判定
- 正規化マッピング
- 監査ログ永続化

## 拡張ポイント

- 署名検証: `policy.verifier.verify_signature()` を差し替え
- DID解決: DID Resolver を追加して policy 判定へ接続
- 外部プラットフォーム連携: `PLATFORM_API_URL` を本番APIへ変更
- DB差し替え: PostgreSQL 実装を追加
- Phase 3 PEP: `process_message` 前段に VC 提示検証を追加

## 注意

- 研究用プロトタイプです。
- JSON-LD VC は未実装ですが、Consent VC キー設計は将来移行を想定しています。

## トラブルシュート（初心者向け）

- `port is already allocated` が出る:
  - `1883` または `8080` を他プロセスが使用中
  - 使用中プロセスを停止するか `infra/docker-compose.yml` のポートを変更
- `curl: (7) Failed to connect`:
  - Publisher 起動直後でまだ待受前
  - `docker ps` 確認後、数秒待って再試行
- いつも `denied` になる:
  - Consent未登録、期限切れ、dataset不一致、purpose不一致が原因
  - `/consents` で登録内容確認、`purpose=research` で再試行
- MQTTが処理されない:
  - topic が `homeassistant/state/...` か `homeassistant/event/...` になっているか確認
  - payload が JSON 形式か確認

## 用語ミニ解説

- `Consent VC`: どのデータを何目的で共有できるかを示す同意情報
- `dataset_id`: 正規化後の論理データ分類（ポリシー照合に使用）
- `purpose`: 共有目的（例: `research`）
- `PEP`: ポリシー適用ポイント（Phase 3 で導入予定）
