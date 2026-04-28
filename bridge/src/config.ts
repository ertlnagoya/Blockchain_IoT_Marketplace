// Bridge runtime config. M2 skeleton — values are env-driven so the
// service can be dropped into the existing docker compose without
// hard-coded URLs.

export interface BridgeConfig {
  hardhatRpc: string;
  iotMarketAddress: string;
  publisherUrl: string;
  // The host-LAN URL the wallet uses to reach publisher. We forward it
  // to /marketplace/claim via X-Forwarded-Host so the deeplink it bakes
  // into the OID4VCI offer stays reachable from the phone, not the
  // internal "publisher:8080" Docker hostname.
  publicPublisherUrl: string;
  datasetDefault: string;
}

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`missing env: ${name}`);
  return v;
}

export function loadConfig(): BridgeConfig {
  const publisherUrl =
    process.env.BRIDGE_PUBLISHER_URL ?? "http://publisher:8080";
  return {
    hardhatRpc: process.env.BRIDGE_HARDHAT_RPC ?? "http://hardhat:8545",
    iotMarketAddress: required("BRIDGE_IOT_MARKET_ADDRESS"),
    publisherUrl,
    publicPublisherUrl:
      process.env.BRIDGE_PUBLIC_PUBLISHER_URL ?? publisherUrl,
    datasetDefault: process.env.BRIDGE_DATASET_DEFAULT ?? "home/env/temperature",
  };
}
