// Bridge skeleton smoke tests.
// M2 will replace these with real listener tests once the publisher
// /marketplace/claim endpoint is implemented.

import { describe, it, expect } from "vitest";
import { PublisherClient } from "../src/publisher_client.js";

describe("PublisherClient", () => {
  it("constructs with a base URL", () => {
    const c = new PublisherClient("http://publisher:8080");
    expect(c).toBeDefined();
  });
});
