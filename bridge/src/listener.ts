// Hardhat Purchase event listener. Skeleton only — minimal ABI, no
// retry/backoff yet. M2 lands the full integration.

import { Contract, JsonRpcProvider, type EventLog } from "ethers";
import type { PublisherClient } from "./publisher_client.js";

const IOT_MARKET_ABI = [
  "function getMerchandises() view returns (address[])",
];

const MERCHANDISE_ABI = [
  "event Purchase(address indexed owner, address indexed buyer, string pubkey)",
];

export interface ListenerOptions {
  rpcUrl: string;
  iotMarketAddress: string;
  datasetDefault: string;
  publisher: PublisherClient;
  log?: (msg: string) => void;
}

export async function startListener(opts: ListenerOptions): Promise<() => void> {
  const log = opts.log ?? ((m) => console.log(m));
  const provider = new JsonRpcProvider(opts.rpcUrl);
  const market = new Contract(opts.iotMarketAddress, IOT_MARKET_ABI, provider);
  const merchandises: string[] = await market.getMerchandises();
  log(`bridge: listening to ${merchandises.length} merchandise(s)`);

  const subs: Array<{ contract: Contract; off: () => void }> = [];

  for (const addr of merchandises) {
    const contract = new Contract(addr, MERCHANDISE_ABI, provider);
    const handler = async (
      _owner: string,
      buyer: string,
      _pubkey: string,
      raw: EventLog,
    ) => {
      log(`bridge: Purchase event from ${addr} buyer=${buyer} tx=${raw.transactionHash}`);
      try {
        const resp = await opts.publisher.claim({
          merchandise_address: addr,
          buyer_eth_addr: buyer,
          tx_hash: raw.transactionHash,
          dataset_id: opts.datasetDefault, // TODO M3: read from Merchandise additionalInfo
          purchase_amount_wei: "0", // TODO M3: read from tx
        });
        log(`bridge: claim ok jti=${resp.claim_id} deeplink=${resp.deeplink}`);
      } catch (e) {
        log(`bridge: claim failed: ${(e as Error).message}`);
      }
    };
    await contract.on("Purchase", handler);
    subs.push({
      contract,
      off: () => {
        void contract.off("Purchase", handler);
      },
    });
  }

  return () => {
    for (const s of subs) s.off();
  };
}
