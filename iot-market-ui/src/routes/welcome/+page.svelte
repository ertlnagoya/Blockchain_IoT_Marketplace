<script lang="ts">
  // PWA onboarding: guide laypeople through the two prerequisite apps
  // (MetaMask Mobile for ETH payments, IW3IP Wallet for credentials),
  // then send them to the marketplace.
  //
  // Designed for first-time launch from "Add to Home Screen" — no
  // jargon (お財布 / 閲覧チケット), big tap targets, two scrollable steps.

  let step = 1;
</script>

<style>
  .wrap { max-width: 480px; margin: 0 auto; padding: 24px 16px; }
  h1 { font-size: 22px; margin-bottom: 8px; }
  p { color: #374151; line-height: 1.6; }
  .card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 18px;
    margin: 16px 0;
  }
  .step-tag {
    display: inline-block;
    background: #2563eb;
    color: white;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 8px;
  }
  .btn {
    display: inline-block;
    width: 100%;
    text-align: center;
    padding: 14px;
    margin: 6px 0;
    background: #2563eb;
    color: white;
    border-radius: 8px;
    text-decoration: none;
    font-weight: bold;
    font-size: 16px;
    border: none;
    cursor: pointer;
  }
  .btn.secondary { background: #6b7280; }
  .stepper { display: flex; gap: 4px; margin: 12px 0; }
  .dot { flex: 1; height: 4px; background: #d1d5db; border-radius: 2px; }
  .dot.active { background: #2563eb; }
  .small { font-size: 13px; color: #6b7280; }
</style>

<div class="wrap">
  <h1>IW3IP データマーケットへようこそ</h1>
  <p class="small">
    あなたの IoT データを安全に売買するアプリです。最初に 2 つの準備が必要です。
  </p>

  <div class="stepper">
    <div class="dot" class:active={step >= 1}></div>
    <div class="dot" class:active={step >= 2}></div>
    <div class="dot" class:active={step >= 3}></div>
  </div>

  {#if step === 1}
    <div class="card">
      <div class="step-tag">STEP 1 / 3</div>
      <h2>お財布アプリ (MetaMask)</h2>
      <p>
        購入の支払いに使う「お財布アプリ」を入れます。MetaMask は世界で
        いちばん使われているお財布です。
      </p>
      <a class="btn" href="https://metamask.io/" target="_blank" rel="noreferrer">
        MetaMask を入手する
      </a>
      <button class="btn secondary" on:click={() => (step = 2)}>
        もう入っています →
      </button>
    </div>

  {:else if step === 2}
    <div class="card">
      <div class="step-tag">STEP 2 / 3</div>
      <h2>閲覧チケット用アプリ (IW3IP Wallet)</h2>
      <p>
        購入したデータを見るための「閲覧チケット」を保管するアプリです。
        商品を買うとアプリが自動で起動して、チケットを受け取ります。
      </p>
      <p class="small">
        ※ 開発中のため、アプリ配布は別途案内されたリンクから取得してください。
      </p>
      <button class="btn secondary" on:click={() => (step = 3)}>
        もう入っています →
      </button>
    </div>

  {:else}
    <div class="card">
      <div class="step-tag">STEP 3 / 3</div>
      <h2>準備完了</h2>
      <p>
        マーケットへ移動して商品を見てみましょう。お試しなら無料に近い
        ものから選べます。
      </p>
      <a class="btn" href="/">マーケットへ進む</a>
      <a class="btn secondary" href="/my-data">購入履歴を見る</a>
    </div>
  {/if}

  <p class="small" style="margin-top: 24px;">
    上のステップ表示は単なる進捗ガイドです。アプリを終了しても情報は失われません。
  </p>
</div>
