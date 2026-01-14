<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { providerVerification } from '$lib/stores/providerVerification';
  import { flagAutoPurchase, hasPendingPurchase, setPendingPurchase } from '$lib/purchase/pending';

  let status = 'Processing verification payload...';

  type LightweightPendingPayload = {
    datasetCID: string;
    ipfsData?: Record<string, any> | null;
    source?: 'search' | 'detail' | 'unknown';
  };

  function decodePendingPayload(raw: string | null): LightweightPendingPayload | null {
    if (!raw) return null;
    try {
      const json = atob(raw);
      const parsed = JSON.parse(json);
      if (parsed && typeof parsed === 'object' && parsed.datasetCID) {
        return parsed as PendingPurchasePayload;
      }
    } catch (error) {
      console.warn('[provider bridge] Failed to decode pending payload', error);
    }
    return null;
  }

  onMount(() => {
    if (!browser) return;

    const params = new URLSearchParams(window.location.search);
    const level = Number(params.get('level') ?? '0');
    const providerDID = params.get('providerDID') ?? undefined;
    const issuerDID = params.get('issuerDID') ?? undefined;
    const vcID = params.get('vcID') ?? undefined;
    const autoParam = params.get('auto');
    const redirectTarget = params.get('redirect') ?? '/';
    const pendingPayload = decodePendingPayload(params.get('pending'));

    if (pendingPayload) {
      setPendingPurchase(pendingPayload);
    }

    if (Number.isFinite(level) && level >= 2) {
      providerVerification.markVerified({
        level,
        providerDID,
        issuerDID,
        vcID
      });
      status = 'Verification synced. Redirecting to marketplace...';
      const shouldAuto = autoParam === '1' || autoParam?.toLowerCase() === 'true';
      if (shouldAuto && (pendingPayload || hasPendingPurchase())) {
        flagAutoPurchase();
      }
      setTimeout(() => goto(redirectTarget), 600);
    } else {
      status = 'Verification payload invalid. Returning to provider page...';
      providerVerification.reset();
      setTimeout(() => goto('/provider'), 800);
    }
  });
</script>

<section class="min-h-screen flex items-center justify-center bg-slate-950 text-white">
  <div class="max-w-md text-center space-y-4">
    <div class="animate-pulse text-sm text-slate-300">{status}</div>
    <div class="rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-left text-xs text-slate-400">
      <p>Use this bridge endpoint when your SSI verification runs on a different origin.</p>
      <p class="mt-1">Query parameters:</p>
      <ul class="list-disc list-inside">
        <li><code>level</code> – Required, numeric access level</li>
        <li><code>providerDID</code>, <code>issuerDID</code>, <code>vcID</code> – Optional metadata</li>
        <li><code>auto</code> – Set to <code>1</code> to resume pending purchase automatically</li>
        <li><code>redirect</code> – Optional target after syncing, defaults to <code>/</code></li>
        <li><code>pending</code> – Optional base64(JSON) to store pending purchase</li>
      </ul>
    </div>
  </div>
</section>
