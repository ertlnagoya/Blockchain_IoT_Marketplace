<script lang="ts">
  // M5: post-purchase VC delivery page (Marketplace VC Bridge v2).
  //
  // After a successful Merchandise.purchase() the buyer lands here.
  // We POST to the publisher's /marketplace/claim endpoint (idempotent
  // on tx_hash so the bridge can race us harmlessly) and surface the
  // resulting OID4VCI deeplink as a clickable button + QR code.
  //
  // The wallet receives the PurchaseViewerVC, which carries the
  // merchandise_address / tx_hash / buyer_eth_addr claims. After
  // presentation the buyer can fetch data via
  // /platform/data?merchandise=<addr> (covered in M6 hands-on).

  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  // URL: /purchased/[txHash]?merchandise=0x...&dataset=home/env/temperature&buyer=0x...
  $: txHash = $page.params.txHash;
  $: merchandiseAddr = $page.url.searchParams.get('merchandise') ?? '';
  $: datasetId = $page.url.searchParams.get('dataset') ?? 'home/env/temperature';
  $: buyerAddr = $page.url.searchParams.get('buyer') ?? '';

  const PUBLISHER_BASE =
    import.meta.env.VITE_PUBLISHER_URL ?? 'http://localhost:8080';

  let status: 'idle' | 'claiming' | 'ready' | 'error' = 'idle';
  let errorMsg = '';
  let deeplink = '';
  let offerUrl = '';
  let claimId = '';

  async function postClaim() {
    status = 'claiming';
    errorMsg = '';
    try {
      const res = await fetch(`${PUBLISHER_BASE}/marketplace/claim`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          merchandise_address: merchandiseAddr,
          buyer_eth_addr: buyerAddr,
          tx_hash: txHash,
          dataset_id: datasetId,
          purchase_amount_wei: '0',
        }),
      });
      if (!res.ok) {
        throw new Error(`publisher returned ${res.status}: ${await res.text()}`);
      }
      const body = await res.json();
      deeplink = body.deeplink;
      offerUrl = body.offer_url;
      claimId = body.claim_id;
      status = 'ready';
      // Persist purchase history so /my-data can list past purchases
      // without contract round-trips. Idempotent on tx_hash.
      try {
        const raw = localStorage.getItem('iw3ip:purchase_history');
        const list: any[] = raw ? JSON.parse(raw) : [];
        if (!list.some((e) => e.txHash === txHash)) {
          list.unshift({
            txHash,
            merchandise: merchandiseAddr,
            dataset: datasetId,
            buyer: buyerAddr,
            purchasedAt: new Date().toISOString(),
          });
          localStorage.setItem(
            'iw3ip:purchase_history',
            JSON.stringify(list.slice(0, 50)),
          );
        }
      } catch {
        // ignore localStorage failures
      }
    } catch (e) {
      errorMsg = (e as Error).message;
      status = 'error';
    }
  }

  // QR via the same external service used elsewhere in the project;
  // the wallet scans this to receive the PurchaseViewerVC.
  $: qrSrc = deeplink
    ? `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(deeplink)}`
    : '';

  onMount(postClaim);
</script>

<style>
  .wrap { max-width: 640px; margin: 0 auto; padding: 24px; text-align: center; }
  .qr { margin: 16px auto; }
  .meta { font-size: 13px; color: #444; word-break: break-all; }
  .btn {
    display: inline-block; padding: 10px 18px; margin: 8px;
    background: #2563eb; color: white; border-radius: 6px; text-decoration: none;
  }
  .btn.secondary { background: #6b7280; }
  pre { text-align: left; background: #f3f4f6; padding: 12px; border-radius: 4px; }
  .err { color: #dc2626; }
</style>

<div class="wrap">
  <h2>購入完了 — VC を受け取る</h2>

  {#if status === 'claiming'}
    <p>publisher にクレームを登録中…</p>
  {:else if status === 'error'}
    <p class="err">エラー: {errorMsg}</p>
    <button class="btn" on:click={postClaim}>再試行</button>
  {:else if status === 'ready'}
    <p>
      購入トランザクションを <strong>PurchaseViewerVC</strong> として
      ウォレットに発行する準備ができました。
    </p>

    <p>スマホウォレットで以下の QR を読み取るか、ボタンを押してください。</p>

    <img class="qr" src={qrSrc} alt="OID4VCI offer deeplink QR" />
    <div>
      <a class="btn" href={deeplink}>ウォレットで開く</a>
      <a class="btn secondary" href={offerUrl} target="_blank" rel="noreferrer">
        ブラウザで JSON を見る
      </a>
    </div>

    <h3>このクレームの情報</h3>
    <pre class="meta">{JSON.stringify(
      {
        claim_id: claimId,
        tx_hash: txHash,
        merchandise: merchandiseAddr,
        dataset_id: datasetId,
        buyer_eth_addr: buyerAddr,
      },
      null,
      2
    )}</pre>

    <p>
      VC を受領したあとは、ウォレットから OID4VP で提示すれば
      <code>/platform/data?merchandise=&lt;addr&gt;</code> でデータを
      取得できます。詳しくは
      <a
        href="https://iw3ip.github.io/hands-on/marketplace-vc-bridge/"
        target="_blank"
        rel="noreferrer"
      >ハンズオン</a>を参照。
    </p>
  {/if}
</div>
