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
