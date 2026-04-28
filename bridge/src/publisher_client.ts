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
  /**
   * @param baseUrl Internal publisher URL (e.g. http://publisher:8080)
   * @param publicUrl Externally-reachable publisher URL (e.g.
   *   http://192.168.68.53:8080). Forwarded via X-Forwarded-Host so the
   *   OID4VCI offer baked into the response uses an URL reachable from
   *   the buyer's phone rather than the internal Docker hostname.
   */
  constructor(
    private readonly baseUrl: string,
    private readonly publicUrl: string = baseUrl,
  ) {}

  async claim(req: ClaimRequest): Promise<ClaimResponse> {
    const url = `${this.baseUrl}/marketplace/claim`;
    const pub = new URL(this.publicUrl);
    const { statusCode, body } = await request(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-forwarded-host": pub.host,
        "x-forwarded-proto": pub.protocol.replace(":", ""),
      },
      body: JSON.stringify(req),
    });
    const text = await body.text();
    if (statusCode !== 200) {
      throw new Error(`publisher /marketplace/claim ${statusCode}: ${text}`);
    }
    return JSON.parse(text) as ClaimResponse;
  }
}
