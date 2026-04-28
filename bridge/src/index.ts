// Bridge service entrypoint. Skeleton only — M2 wires this into
// docker compose under the `mv-bridge` profile.

import { loadConfig } from "./config.js";
import { startListener } from "./listener.js";
import { PublisherClient } from "./publisher_client.js";

async function main() {
  const cfg = loadConfig();
  const publisher = new PublisherClient(cfg.publisherUrl, cfg.publicPublisherUrl);
  const stop = await startListener({
    rpcUrl: cfg.hardhatRpc,
    iotMarketAddress: cfg.iotMarketAddress,
    datasetDefault: cfg.datasetDefault,
    publisher,
  });
  console.log(
    `bridge: started rpc=${cfg.hardhatRpc} market=${cfg.iotMarketAddress} publisher=${cfg.publisherUrl}`,
  );

  const shutdown = () => {
    console.log("bridge: shutting down");
    stop();
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((e) => {
  console.error("bridge: fatal", e);
  process.exit(1);
});
