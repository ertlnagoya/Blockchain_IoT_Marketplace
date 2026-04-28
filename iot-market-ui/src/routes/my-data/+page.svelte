<script lang="ts">
  // Buyer's purchase history + on-tap data viewing.
  //
  // We store a lightweight history in localStorage when /purchased/[txHash]
  // succeeds, so this page can list past purchases without round-trips
  // to the chain. "View data" performs:
  //   1. open verifier deeplink for PurchaseViewerVC presentation
  //   2. user presents in iw3ip-wallet
  //   3. wallet redirects back to /my-data (universal link)
  //   4. we poll /platform/data?merchandise= with the most recent
  //      ViewerToken from publisher logs
  //
  // For MVP we surface the merchandise + tx + dataset and let the user
  // run the publisher curl manually; the full automatic loop lands later.

  import { onMount } from 'svelte';

  type HistoryEntry = {
    txHash: string;
    merchandise: string;
    dataset: string;
    buyer: string;
    purchasedAt: string;
  };

  const PUBLISHER_BASE =
    import.meta.env.VITE_PUBLISHER_URL ?? 'http://localhost:8080';

  let history: HistoryEntry[] = [];
  let lastViewedRows: any = null;
  let lastViewError = '';

  onMount(() => {
    try {
      const raw = localStorage.getItem('iw3ip:purchase_history');
      history = raw ? JSON.parse(raw) : [];
    } catch {
      history = [];
    }
  });

  async function viewData(entry: HistoryEntry) {
    lastViewError = '';
    lastViewedRows = null;
    try {
      // Hands-on path: user presents PurchaseViewerVC manually via the
      // verifier link, then pastes the ViewerToken below. Once we move
      // to integrated wallet (Stage 9), this becomes one tap.
      const presentUrl =
        `${PUBLISHER_BASE}/verifier/request?dataset_id=${encodeURIComponent(entry.dataset)}&vc_kind=PurchaseViewerVC`;
      window.open(presentUrl, '_blank', 'noopener');
    } catch (e) {
      lastViewError = (e as Error).message;
    }
  }

  let token = '';
  let activeMerchandise = '';
  async function fetchData(merchandise: string) {
    activeMerchandise = merchandise;
    lastViewedRows = null;
    lastViewError = '';
    if (!token) {
      lastViewError = '閲覧チケット (ViewerToken) を貼り付けてください';
      return;
    }
    try {
      const res = await fetch(
        `${PUBLISHER_BASE}/platform/data?merchandise=${encodeURIComponent(merchandise)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const body = await res.json();
      if (!res.ok) {
        lastViewError = `${res.status}: ${JSON.stringify(body)}`;
        return;
      }
      lastViewedRows = body;
    } catch (e) {
      lastViewError = (e as Error).message;
    }
  }
</script>

<style>
  .wrap { max-width: 720px; margin: 0 auto; padding: 16px; }
  h1 { font-size: 22px; }
  .empty { padding: 40px 16px; text-align: center; color: #6b7280; }
  .item {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px;
    margin: 10px 0;
  }
  .meta { font-size: 12px; color: #6b7280; word-break: break-all; }
  .btn {
    display: inline-block;
    padding: 10px 14px;
    background: #2563eb;
    color: white;
    border-radius: 6px;
    text-decoration: none;
    border: none;
    cursor: pointer;
    font-weight: bold;
    margin: 4px 4px 0 0;
  }
  .btn.secondary { background: #6b7280; }
  pre {
    background: #f3f4f6;
    padding: 10px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 12px;
  }
  .err { color: #dc2626; }
  input.token {
    width: 100%;
    padding: 8px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    margin-top: 6px;
  }
  .small { font-size: 12px; color: #6b7280; }
</style>

<div class="wrap">
  <h1>購入履歴</h1>

  {#if history.length === 0}
    <div class="empty">
      まだ購入したデータはありません。
      <br />
      <a class="btn" href="/" style="margin-top: 16px;">マーケットへ</a>
    </div>
  {:else}
    {#each history as entry}
      <div class="item">
        <div><strong>{entry.dataset}</strong></div>
        <div class="meta">
          merchandise: {entry.merchandise}<br />
          tx: {entry.txHash}<br />
          purchased: {entry.purchasedAt}
        </div>
        <button class="btn" on:click={() => viewData(entry)}>
          閲覧チケットを取得
        </button>
        <button class="btn secondary" on:click={() => (activeMerchandise = entry.merchandise)}>
          このデータを見る
        </button>
      </div>
    {/each}

    {#if activeMerchandise}
      <div class="item">
        <strong>データを取得</strong>
        <p class="small">
          チケットアプリで提示が完了すると <code>seller_token_issued</code>
          相当の token がサーバログに出ます。それを以下に貼って取得:
        </p>
        <input class="token" bind:value={token} placeholder="ViewerToken (Bearer)" />
        <button class="btn" on:click={() => fetchData(activeMerchandise)}>
          取得実行
        </button>

        {#if lastViewError}
          <p class="err">エラー: {lastViewError}</p>
        {/if}
        {#if lastViewedRows}
          <pre>{JSON.stringify(lastViewedRows, null, 2)}</pre>
        {/if}
      </div>
    {/if}
  {/if}

  <p class="small" style="margin-top: 24px;">
    閲覧チケットの自動取得・自動表示は将来の Stage 9 で対応予定です。
    現在は手動でトークンを貼る形になっています。
  </p>
</div>
