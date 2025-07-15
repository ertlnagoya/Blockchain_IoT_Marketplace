# DB

## セットアップ

### コンテナの起動

```bash
docker compose up -d
```

これで、IPFSは起動する。
PostgreSQLは、自分でテーブルを作成する必要がある（後述）。

### PostgreSQLでテーブルを作成

PostgreSQLにログイン。

```bash
docker exec -it postgres_db psql -U dev -d mydb
```

テーブルを作成する。

```sql
CREATE TABLE ipfs_records (
    cid TEXT PRIMARY KEY,                         -- IPFSのCID（文字列）
    start_timestamp TIMESTAMP NOT NULL,           -- 開始時刻
    end_timestamp TIMESTAMP NOT NULL,             -- 終了時刻
    location GEOGRAPHY(POINT, 4326) NOT NULL,     -- 緯度・経度 (PostGISで空間検索も可能)
    exist_people BOOL NOT NULL
);
```

## ストアしたデータを消す

### 全部消したいとき

volumeを確認する．

```bash
docker volume ls
```

消す．

```bash
docker volume rm ipfs_ipfs_data
docker volume rm ipfs_pg_data
```

### テーブル内のデータのみ消したいとき

psqlに入った後、下記を実行

```sql
TRUNCATE ipfs_records;
```

## 困ったときの動作検証方法

### IPFS

JSONファイルを作成し，IPFSに格納する．

```bash
curl -X POST http://localhost:5001/api/v0/add -F file=@test.json
```

この際に，Hashが返ってくる（CID）．  
このCIDで，格納したコンテンツを得る．

```bash
curl -L http://localhost:8080/ipfs/QmXrejoiiPLztK98sXm2ytHBLyyRJkZbxR8wX2mf5skj2j
```

他のdevcontainerからアクセスするときは，下記のようにアクセス．

```bash
curl -X POST http://host.docker.internal:5001/api/v0/version
curl -L http://host.docker.internal:8080/ipfs/QmXrejoiiPLztK98sXm2ytHBLyyRJkZbxR8wX2mf5skj2j
```
