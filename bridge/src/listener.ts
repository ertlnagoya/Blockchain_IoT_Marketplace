// Hardhat Purchase event listener.
//
// ethers v6's filter-based subscription (`contract.on("Purchase", ...)`)
// triggers a "results is not iterable" crash on Hardhat because
// eth_getFilterChanges returns `null` rather than `[]` when no new
// events. We sidestep that path by polling `getLogs` ourselves over
// explicit block ranges. This is also easier to reason about.

import { Contract, Interface, JsonRpcProvider, type Log } from "ethers";
import type { PublisherClient } from "./publisher_client.js";

const IOT_MARKET_ABI = [
  "function getMerchandises() view returns (address[])",
];

// We only need the read function to fetch dataset_id from additionalInfo;
// the Purchase event is parsed via topic0 + the logs interface below.
const MERCHANDISE_READ_ABI = [
  "function getAllAdditionalInfo() view returns (tuple(string key, string value)[])",
];

const PURCHASE_FRAGMENT =
  "event Purchase(address indexed owner, address indexed buyer, string pubkey)";
const MERCHANDISE_IFACE = new Interface([PURCHASE_FRAGMENT]);
const PURCHASE_TOPIC0 = MERCHANDISE_IFACE.getEvent("Purchase")!.topicHash;

export interface ListenerOptions {
  rpcUrl: string;
  iotMarketAddress: string;
  datasetDefault: string;
  publisher: PublisherClient;
  pollIntervalMs?: number;
  log?: (msg: string) => void;
}

export async function startListener(opts: ListenerOptions): Promise<() => void> {
  const log = opts.log ?? ((m) => console.log(m));
  const pollMs = opts.pollIntervalMs ?? 2000;
  const provider = new JsonRpcProvider(opts.rpcUrl);
  const market = new Contract(opts.iotMarketAddress, IOT_MARKET_ABI, provider);
  const merchandises: string[] = await market.getMerchandises();
  const watched = new Set(merchandises.map((a) => a.toLowerCase()));
  log(`bridge: listening to ${merchandises.length} merchandise(s)`);

  let cursor = await provider.getBlockNumber();
  log(`bridge: starting poll from block ${cursor}`);

  let stopped = false;
  const seenTx = new Set<string>();
  // merchandise_address (lowercased) -> dataset_id resolved from
  // its additionalInfo. Cached on first lookup so we don't re-query
  // chain on every event from the same merchandise.
  const datasetCache = new Map<string, string>();

  const resolveDatasetId = async (merchandiseAddr: string): Promise<string> => {
    const key = merchandiseAddr.toLowerCase();
    const hit = datasetCache.get(key);
    if (hit) return hit;
    try {
      const m = new Contract(merchandiseAddr, MERCHANDISE_READ_ABI, provider);
      const pairs: Array<{ key: string; value: string }> =
        await m.getAllAdditionalInfo();
      for (const p of pairs) {
        if (p.key === "dataset_id" && p.value) {
          datasetCache.set(key, p.value);
          return p.value;
        }
      }
    } catch (e) {
      log(`bridge: getAllAdditionalInfo(${merchandiseAddr}) failed: ${(e as Error).message}`);
    }
    datasetCache.set(key, opts.datasetDefault);
    return opts.datasetDefault;
  };

  const tick = async () => {
    if (stopped) return;
    try {
      const head = await provider.getBlockNumber();
      if (head > cursor) {
        const logs: Log[] = await provider.getLogs({
          fromBlock: cursor + 1,
          toBlock: head,
          topics: [PURCHASE_TOPIC0],
        });
        for (const ev of logs) {
          if (!watched.has(ev.address.toLowerCase())) continue;
          if (seenTx.has(ev.transactionHash)) continue;
          seenTx.add(ev.transactionHash);
          const parsed = MERCHANDISE_IFACE.parseLog({
            topics: [...ev.topics],
            data: ev.data,
          });
          if (!parsed) continue;
          const buyer = parsed.args.buyer as string;
          const datasetId = await resolveDatasetId(ev.address);
          log(
            `bridge: Purchase event from ${ev.address} buyer=${buyer} dataset=${datasetId} tx=${ev.transactionHash}`,
          );
          try {
            const resp = await opts.publisher.claim({
              merchandise_address: ev.address,
              buyer_eth_addr: buyer,
              tx_hash: ev.transactionHash,
              dataset_id: datasetId,
              purchase_amount_wei: "0", // TODO: read from tx
            });
            log(`bridge: claim ok jti=${resp.claim_id} deeplink=${resp.deeplink}`);
          } catch (e) {
            log(`bridge: claim failed: ${(e as Error).message}`);
          }
        }
        cursor = head;
      }
    } catch (e) {
      log(`bridge: poll error: ${(e as Error).message}`);
    } finally {
      if (!stopped) setTimeout(tick, pollMs);
    }
  };

  setTimeout(tick, pollMs);

  return () => {
    stopped = true;
  };
}
