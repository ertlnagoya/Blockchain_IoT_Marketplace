<script lang="ts">
  import { v4 as uuidv4 } from 'uuid';
  import { signPurchasePayloadJWS } from '$lib/purchase/sign';
  import { verifyProviderResponse } from '$lib/purchase/verifyPurchaseResponse';
  import { providerEndpoints, defaultProviderEndpoint, providerPortalUrl } from '$lib/config/providers';
   import { setPendingPurchase } from '$lib/purchase/pending';
  import { consumerDID, consumerSeedB64 } from '$lib/config/consumer';
  import { sendPurchaseRequest } from '$lib/purchase/send';
  import { providerVerification } from '$lib/stores/providerVerification';

  export let datasetCID: string;
  export let providerAddress: string;
  const MIN_LEVEL = 2;

  const endpoint = providerEndpoints[providerAddress?.toLowerCase?.()] ?? defaultProviderEndpoint;

  const redirectToProviderPortal = () => {
    if (typeof window !== 'undefined') {
      window.location.href = providerPortalUrl;
    }
  };

  const nowISO = () => new Date().toISOString();
  const genNonce = (n=32)=>Array.from(crypto.getRandomValues(new Uint8Array(n))).map(x=>x.toString(16).padStart(2,'0')).join('');

  async function onPurchaseClick(e: Event) {
    e.preventDefault();
    console.log('[PurchaseButton] endpoint=', endpoint); // 可见即说明组件已挂载
    const requestID = uuidv4();
    const level = Number($providerVerification.level ?? 0);
    if (level < MIN_LEVEL) {
      alert('请先在 /provider 页面完成 FULL ACCESS 验证');
        setPendingPurchase({ datasetCID: datasetCID, ipfsData: { address: providerAddress }, source: 'detail' });
      redirectToProviderPortal();
      return;
    }
    const payload = {
      requestID,
      nonce: genNonce(16),
      issuedAt: nowISO(),
      consumerDID,
      datasetID: datasetCID,
      accessType: 'ONE_TIME_PURCHASE',
      zkAccessLevelClaim: { level }
    };
  const proof = await signPurchasePayloadJWS(payload, consumerDID, consumerSeedB64);
    const body = { ...payload, proof };

    const resp = await sendPurchaseRequest(endpoint, body); // 这里会发 POST
    await verifyProviderResponse(resp, requestID);
    alert('ProviderResponse verified');
  }
</script>

<button type="button" class="btn btn-primary" on:click={onPurchaseClick}>
  Purchase
</button>