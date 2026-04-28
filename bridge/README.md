# bridge — Marketplace VC Bridge service (v2)

Listens to `Merchandise.Purchase` events on the Hardhat chain and
forwards each purchase to the SSI publisher so the buyer can claim a
**PurchaseViewerVC**.

## Status

**M2 skeleton.** Not yet wired end-to-end. See the design spec at
[`iw3ip.github.io/docs/design/marketplace-vc-bridge-spec.md`](https://iw3ip.github.io/design/marketplace-vc-bridge-spec/)
for the full v1/v2 architecture and milestones.

## Role in v2

```
Merchandise.Purchase event
        │
        ▼
   bridge (this service)
        │  POST /marketplace/claim
        ▼
   publisher (FastAPI, ssi/)
        │  OID4VCI offer
        ▼
   iw3ip-wallet (PurchaseViewerVC)
```

v1 (encryptURI → decrypt) keeps running in parallel; bridge does **not**
modify any on-chain state.

## Layout (planned for M2)

```
bridge/
├── README.md              ← this file
├── package.json           ← Node dependencies (M2)
├── tsconfig.json
├── Dockerfile             ← compose-friendly image (M2)
├── src/
│   ├── index.ts           ← entrypoint, env loading
│   ├── listener.ts        ← ethers.js Purchase event subscription
│   ├── publisher_client.ts ← HTTP client for /marketplace/claim
│   └── config.ts
└── test/
    └── listener.test.ts   ← vitest unit tests with mock Hardhat
```

## Environment variables

| Var | Default | Meaning |
| --- | --- | --- |
| `BRIDGE_HARDHAT_RPC` | `http://hardhat:8545` | RPC endpoint for the local chain |
| `BRIDGE_IOT_MARKET_ADDRESS` | (required) | `IoTMarket` contract address; bridge enumerates Merchandise from it |
| `BRIDGE_PUBLISHER_URL` | `http://publisher:8080` | publisher base URL |
| `BRIDGE_DATASET_DEFAULT` | `home/env/temperature` | fallback `dataset_id` if Merchandise has none |

## Milestones

| ID | Status |
| --- | --- |
| M1: design spec | in review |
| M2: this skeleton + Purchase event → claim API | **here** |
| M3: PurchaseViewerVC + eth↔did binding | not started |
| M4: `/platform/data?merchandise=<addr>` + tests | not started |
| M5: iot-market-ui post-purchase delivery | not started |
| M6: hands-on docs | not started |

## Running (once M2 lands)

```bash
docker compose -f infra/docker-compose.yml --profile mv-bridge up --build
```

## Out of scope for v2 MVP

- EIP-712 signed eth_addr ↔ did:jwk binding (production hardening)
- KYC / identity-proofing VCs
- Multi-chain / production RPC
- Auction / price negotiation
