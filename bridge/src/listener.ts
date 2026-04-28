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
          log(
            `bridge: Purchase event from ${ev.address} buyer=${buyer} tx=${ev.transactionHash}`,
          );
          try {
            const resp = await opts.publisher.claim({
              merchandise_address: ev.address,
              buyer_eth_addr: buyer,
              tx_hash: ev.transactionHash,
              dataset_id: opts.datasetDefault, // TODO M3+: read from Merchandise additionalInfo
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
