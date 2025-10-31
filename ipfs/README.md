# IPFS / DB

<p align="center">
  <a href="#日本語-readme">日本語 README</a> | <a href="#english-readme">English README</a>
</p>

---

## 日本語 README

IPFS ノードと PostgreSQL（PostGIS）を docker compose で起動し、IPFS の CID とメタデータを DB に保存するための環境です。

### セットアップ

#### コンテナの起動

```bash
docker compose up -d
```

これで IPFS は起動します。  
PostgreSQL は、テーブルを自分で作成する必要があります（後述）。

#### PostgreSQL でテーブルを作成

PostgreSQL にログイン：

```bash
docker exec -it postgres_db psql -U dev -d mydb
```

必要に応じて PostGIS を有効化（コンテナイメージに同梱されている場合）：

```sql
-- 必要なら
-- CREATE EXTENSION IF NOT EXISTS postgis;
```

テーブルを作成：

```sql
CREATE TABLE ipfs_records (
    cid TEXT PRIMARY KEY,                         -- IPFS の CID（文字列）
    start_timestamp TIMESTAMP NOT NULL,           -- 開始時刻
    end_timestamp TIMESTAMP NOT NULL,             -- 終了時刻
    location GEOGRAPHY(POINT, 4326) NOT NULL,     -- 緯度・経度（PostGIS で空間検索も可能）
    exist_people BOOL NOT NULL
);
```

### ストアしたデータを消す

#### 全部消したいとき（ボリュームごと削除）

ボリュームを確認：

```bash
docker volume ls
```

削除：

```bash
docker volume rm ipfs_ipfs_data
docker volume rm ipfs_pg_data
```

#### テーブル内のデータのみ消したいとき

psql で以下を実行：

```sql
TRUNCATE ipfs_records;
```

### 困ったときの動作検証方法

#### IPFS

JSON ファイルを作成し、IPFS に格納：

```bash
curl -X POST http://localhost:5001/api/v0/add -F file=@test.json
```

戻りの Hash（CID）でコンテンツを取得：

```bash
curl -L http://localhost:8080/ipfs/<YOUR_CID>
```

別の Dev Container からアクセスする場合：

```bash
curl -X POST http://host.docker.internal:5001/api/v0/version
curl -L http://host.docker.internal:8080/ipfs/<YOUR_CID>
```

---

## English README

This directory provides a docker compose setup for running an IPFS node and PostgreSQL (with PostGIS), so that you can store IPFS CIDs alongside metadata in the database.

### Setup

#### Start containers

```bash
docker compose up -d
```

This starts IPFS.  
For PostgreSQL, you need to create the table manually (see below).

#### Create table in PostgreSQL

Log into PostgreSQL:

```bash
docker exec -it postgres_db psql -U dev -d mydb
```

Enable PostGIS if needed (depending on the image):

```sql
-- If needed:
-- CREATE EXTENSION IF NOT EXISTS postgis;
```

Create the table:

```sql
CREATE TABLE ipfs_records (
    cid TEXT PRIMARY KEY,                         -- IPFS CID (string)
    start_timestamp TIMESTAMP NOT NULL,           -- Start time
    end_timestamp TIMESTAMP NOT NULL,             -- End time
    location GEOGRAPHY(POINT, 4326) NOT NULL,     -- Latitude/Longitude (supports spatial queries via PostGIS)
    exist_people BOOL NOT NULL
);
```

### How to clear stored data

#### Remove everything (volumes)

List volumes:

```bash
docker volume ls
```

Remove:

```bash
docker volume rm ipfs_ipfs_data
docker volume rm ipfs_pg_data
```

#### Only clear table rows

Run in psql:

```sql
TRUNCATE ipfs_records;
```

### Troubleshooting / Verification

#### IPFS

Add a JSON file to IPFS:

```bash
curl -X POST http://localhost:5001/api/v0/add -F file=@test.json
```

Fetch by the returned Hash (CID):

```bash
curl -L http://localhost:8080/ipfs/<YOUR_CID>
```

Access from another Dev Container:

```bash
curl -X POST http://host.docker.internal:5001/api/v0/version
curl -L http://host.docker.internal:8080/ipfs/<YOUR_CID>
```
