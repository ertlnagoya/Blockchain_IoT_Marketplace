# IPFSの使い方

IPFSを起動する．

```bash
docker compose up
```

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

## ストアしたデータを消す

volumeを確認する．

```bash
docker volume ls
```

消す．

```bash
docker volume rm ipfs_ipfs_data
docker volume rm ipfs_ipfs_staging
```

## PostgreSQLへのアクセス

```bash
docker exec -it postgres_db psql -U dev -d mydb
```

PostGISが有効に

```sql
-- PostGIS拡張を有効化
CREATE EXTENSION postgis;

-- バージョン確認
SELECT PostGIS_Full_Version();
```

テーブル作成

```sql
CREATE TABLE ipfs_records (
    cid TEXT PRIMARY KEY,                         -- IPFSのCID（文字列）
    start_timestamp TIMESTAMP NOT NULL,           -- 開始時刻
    end_timestamp TIMESTAMP NOT NULL,             -- 終了時刻
    location GEOGRAPHY(POINT, 4326) NOT NULL,     -- 緯度・経度 (PostGISで空間検索も可能)
    exist_people BOOL NOT NULL
);
```
