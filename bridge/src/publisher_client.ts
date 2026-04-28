// HTTP client for the publisher's marketplace endpoints.
// Skeleton only — wire to real publisher in M2.

import { request } from "undici";

export interface ClaimRequest {
  merchandise_address: string;
  buyer_eth_addr: string;
  tx_hash: string;
  dataset_id: string;
  purchase_amount_wei: string;
}

export interface ClaimResponse {
  offer_url: string;
  deeplink: string;
  claim_id: string;
}

export class PublisherClient {
  constructor(private readonly baseUrl: string) {}

  async claim(req: ClaimRequest): Promise<ClaimResponse> {
    const url = `${this.baseUrl}/marketplace/claim`;
    const { statusCode, body } = await request(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req),
    });
    const text = await body.text();
    if (statusCode !== 200) {
      throw new Error(`publisher /marketplace/claim ${statusCode}: ${text}`);
    }
    return JSON.parse(text) as ClaimResponse;
  }
}
