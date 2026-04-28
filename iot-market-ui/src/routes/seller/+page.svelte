<script lang="ts">
  // C5: minimal seller registration UI (Stage 7).
  //
  // Scope per spec Q3: form only. Merchandise is deployed via the
  // existing Hardhat console flow; this page handles only the
  // SellerVC -> SellerToken -> /marketplace/register step.
  //
  // Flow:
  //   1. Seller obtains a SellerVC by visiting /issuer/offer with
  //      type=SellerVC + seller_id + licensed_datasets, receives it
  //      in their wallet.
  //   2. Seller presents the SellerVC at /verifier/request?vc_kind=SellerVC.
  //      The publisher log emits `seller_token_issued ... token=...`.
  //   3. Seller pastes the token + merchandise context into the form
  //      below; we POST to publisher /marketplace/register.
  //   4. The merchandise is now bound to seller_did inside the publisher,
  //      and buyers see the seller in /platform/data?merchandise= responses.

  const PUBLISHER_BASE =
    import.meta.env.VITE_PUBLISHER_URL ?? 'http://localhost:8080';

  let sellerId = 'ertl-seller-001';
  let licensedDatasets = 'home/env/temperature,home/env/humidity';
  let sellerToken = '';
  let merchandiseAddress = '';
  let sellerEthAddr = '';
  let txHash = '';
  let datasetId = 'home/env/temperature';

  let status: 'idle' | 'submitting' | 'ok' | 'error' = 'idle';
  let response: any = null;
  let errorMsg = '';

  $: offerHref =
    `${PUBLISHER_BASE}/issuer/offer?type=SellerVC` +
    `&seller_id=${encodeURIComponent(sellerId)}` +
    `&licensed_datasets=${encodeURIComponent(licensedDatasets)}`;

  $: presentHref = `${PUBLISHER_BASE}/verifier/request?vc_kind=SellerVC`;

  async function register() {
    status = 'submitting';
    errorMsg = '';
    response = null;
    try {
      const r = await fetch(`${PUBLISHER_BASE}/marketplace/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sellerToken}`,
        },
        body: JSON.stringify({
          merchandise_address: merchandiseAddress,
          seller_eth_addr: sellerEthAddr,
          tx_hash: txHash,
          dataset_id: datasetId,
        }),
      });
      if (!r.ok) {
        throw new Error(`publisher returned ${r.status}: ${await r.text()}`);
      }
      response = await r.json();
      status = 'ok';
    } catch (e) {
      errorMsg = (e as Error).message;
      status = 'error';
    }
  }
</script>

<style>
  .wrap { max-width: 720px; margin: 0 auto; padding: 24px; }
  .step { padding: 16px; margin: 12px 0; border: 1px solid #d1d5db; border-radius: 8px; }
  .step h3 { margin-top: 0; }
  label { display: block; margin: 8px 0 4px; font-size: 14px; color: #374151; }
  input { width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px; }
  .btn {
    display: inline-block; padding: 10px 16px; margin: 8px 8px 0 0;
    background: #2563eb; color: white; border-radius: 6px; text-decoration: none;
    border: none; cursor: pointer;
  }
  .btn.secondary { background: #6b7280; }
  pre { background: #f3f4f6; padding: 12px; border-radius: 4px; overflow-x: auto; }
  .err { color: #dc2626; }
  .ok { color: #16a34a; }
</style>

<div class="wrap">
  <h2>Seller registration (Stage 7)</h2>

  <p>
    Bind a freshly-deployed Merchandise contract to your seller identity
    by presenting a SellerVC and posting the registration to the publisher.
    Backend spec: <a
      href="https://iw3ip.github.io/design/seller-vc-spec/"
      target="_blank"
      rel="noreferrer">SellerVC design doc</a>.
  </p>

  <div class="step">
    <h3>1. SellerVC を発行する</h3>
    <p>seller_id と licensed_datasets を埋めてリンクを開く。
      QR が出るのでスマホ wallet で読み取り、VC を受領。</p>
    <label>seller_id</label>
    <input type="text" bind:value={sellerId} />
    <label>licensed_datasets (カンマ区切り)</label>
    <input type="text" bind:value={licensedDatasets} />
    <a class="btn" href={offerHref} target="_blank" rel="noreferrer">
      /issuer/offer を開く
    </a>
  </div>

  <div class="step">
    <h3>2. SellerVC を提示して SellerToken を取り出す</h3>
    <p>下のリンクで提示画面を開き、wallet で SellerVC を選択して提示する。
      提示後、publisher のログ <code>seller_token_issued ... token=...</code>
      の <code>token=</code> を以下に貼り付ける。</p>
    <a class="btn" href={presentHref} target="_blank" rel="noreferrer">
      /verifier/request を開く
    </a>
    <pre>docker logs $PUB 2&gt;&amp;1 | grep seller_token_issued | tail -1</pre>
  </div>

  <div class="step">
    <h3>3. Merchandise を登録</h3>
    <p>事前に Hardhat console で <code>Merchandise</code> を deploy し、
      <code>IoTMarket.registerMerchandise()</code> を呼んでおく
      (<a href="https://iw3ip.github.io/hands-on/marketplace-seller-vc/"
          target="_blank" rel="noreferrer">手順</a>)。
      その出力からアドレスと tx hash を以下に貼る。</p>
    <label>SellerToken</label>
    <input type="text" bind:value={sellerToken} placeholder="LuW_UmOLNeXJjdeKlQbKUnmcmqAg..." />
    <label>merchandise_address</label>
    <input type="text" bind:value={merchandiseAddress} placeholder="0x..." />
    <label>seller_eth_addr</label>
    <input type="text" bind:value={sellerEthAddr} placeholder="0x..." />
    <label>tx_hash (deploy か register tx)</label>
    <input type="text" bind:value={txHash} placeholder="0x..." />
    <label>dataset_id (Merchandise.additionalInfo の値と一致)</label>
    <input type="text" bind:value={datasetId} />
    <button
      class="btn"
      on:click={register}
      disabled={status === 'submitting' || !sellerToken || !merchandiseAddress}
    >
      Register
    </button>
  </div>

  {#if status === 'submitting'}
    <p>送信中…</p>
  {:else if status === 'error'}
    <p class="err">エラー: {errorMsg}</p>
  {:else if status === 'ok'}
    <p class="ok">登録成功</p>
    <pre>{JSON.stringify(response, null, 2)}</pre>
  {/if}
</div>
