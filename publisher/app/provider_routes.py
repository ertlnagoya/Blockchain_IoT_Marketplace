"""Stage T (PWA provider, c1) -- minimal browser UI for data providers.

Mirror of /buyer/start but for SellerVC presentation. The page bootstraps
a /verifier/request?vc_kind=SellerVC, shows a QR for cross-device flow
(or jumps to the wallet for same-device), and on success renders an
inline panel showing the SellerToken + licensed_datasets.

The actual upload + /simulate/publish UI ships in c2; for c1 the page
only proves that the OID4VP plumbing for the provider side works
end-to-end (QR -> wallet -> SellerVC presentation -> SellerToken issued
and surfaced back to the page).

Same-device flow uses redirect_uri=/provider/start?state=... which the
client-side script picks up to skip the bootstrap step and just resume
polling.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse


logger = logging.getLogger(__name__)


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/provider/start", response_class=HTMLResponse)
    def provider_start_page(
        request: Request,
        ds: str | None = Query(
            default=None,
            description=(
                "Optional dataset hint -- shown in the page header so the "
                "provider knows which dataset they're about to publish to. "
                "SellerVC verification itself is not dataset-bound; the "
                "licensed_datasets check happens server-side at upload time."
            ),
        ),
        state: str | None = Query(
            default=None,
            description=(
                "Existing verifier state to resume polling against. Set by "
                "the wallet's redirect_uri after a same-device presentation "
                "so the page skips the bootstrap step."
            ),
        ),
    ) -> HTMLResponse:
        page_origin = str(request.base_url).rstrip("/")
        safe = lambda v: json.dumps(v if v is not None else "")  # noqa: E731
        body = (
            _PROVIDER_START_HTML
            .replace("__ORIGIN__", safe(page_origin))
            .replace("__DS__", safe(ds))
            .replace("__RESUME_STATE__", safe(state))
        )
        return HTMLResponse(body)

    return router


# ----------------------------------------------------------------------
# /provider/start page template
# ----------------------------------------------------------------------
_PROVIDER_START_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IW3IP Provider</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      margin: 0; padding: 1rem; max-width: 720px; margin-inline: auto;
      line-height: 1.5;
    }
    h1 { font-size: 1.2rem; margin-block-start: 0; }
    .qr {
      display: grid; place-items: center; padding: 1rem; background: #fff;
      border: 1px solid #ddd; border-radius: 8px; margin-block: 1rem;
    }
    .qr svg { max-width: 100%; height: auto; }
    .meta { font-size: 0.85rem; color: #666; }
    .err { padding: 1rem; background: #fdecea; border-radius: 6px; color: #b71c1c; }
    .ok  { padding: 1rem; background: #e8f5e9; border-radius: 6px; color: #1b5e20; }
    .deeplink {
      display: inline-block; padding: 0.6rem 1rem;
      background: #2e7d32; color: #fff; border-radius: 6px;
      text-decoration: none; margin-block: 0.5rem;
    }
    .pulse { animation: pulse 1.4s ease-in-out infinite; }
    @keyframes pulse {
      0%, 100% { opacity: 0.55; }
      50% { opacity: 1; }
    }
    code, .mono {
      font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
      font-size: 0.85rem; word-break: break-all;
    }
    ul.licensed { padding-inline-start: 1.2rem; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/qrcode-svg@1.1.0/dist/qrcode.min.js"></script>
</head>
<body>
  <h1>IW3IP Provider</h1>
  <p class="meta" id="meta"></p>
  <div id="root"><p class="pulse">Bootstrapping verifier session…</p></div>

  <script>
    const ORIGIN = __ORIGIN__;
    const DS_HINT = __DS__;
    const RESUME_STATE = __RESUME_STATE__;
    const VC_KIND = "SellerVC";

    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    document.getElementById("meta").textContent =
      (DS_HINT ? `dataset_hint=${DS_HINT} • ` : "")
      + `vc_kind=${VC_KIND} • ${isMobile ? "📱 same-device" : "🖥 cross-device"}`;

    async function bootstrap() {
      const root = document.getElementById("root");

      // Same-device return path: the wallet's redirect_uri brought us
      // back with ?state=... already set. Skip /verifier/request and
      // resume polling immediately.
      if (RESUME_STATE) {
        root.innerHTML = `<p class="pulse">ウォレットからの戻りを処理中…</p>`;
        pollUntilDone(RESUME_STATE);
        return;
      }

      try {
        const url = new URL(`${ORIGIN}/verifier/request`);
        url.searchParams.set("vc_kind", VC_KIND);
        // SellerVC isn't dataset-scoped at verify time; verifier_routes
        // accepts "*" as a sentinel. Pass the hint along anyway so audit
        // logs see what the provider intended.
        url.searchParams.set("dataset_id", DS_HINT || "*");
        url.searchParams.set("purpose", "publish");
        const r = await fetch(url, { headers: { Accept: "application/json" } });
        if (!r.ok) {
          root.innerHTML = "";
          root.append(Object.assign(document.createElement("div"),
            { className: "err", textContent: `HTTP ${r.status}: ${await r.text()}` }));
          return;
        }
        const body = await r.json();
        const deeplink = body.deeplink;
        const state = body.authorization_request?.state;
        if (!deeplink || !state) {
          root.textContent = "Unexpected /verifier/request response";
          return;
        }
        if (isMobile) {
          // Same-device: jump to the wallet. Wallet's redirect_uri
          // returns the user to /provider/start?state=... which the
          // RESUME_STATE branch above picks up.
          root.innerHTML = `
            <p>📱 ウォレットを起動しています…</p>
            <a class="deeplink" href="${deeplink}">ウォレットで開く</a>
            <p class="meta">起動しない場合は上のボタンをタップしてください。</p>
          `;
          window.location.href = deeplink;
        } else {
          renderQrAndPoll(deeplink, state);
        }
      } catch (e) {
        root.innerHTML = "";
        root.append(Object.assign(document.createElement("div"),
          { className: "err", textContent: `network error: ${e.message || e}` }));
      }
    }

    function renderQrAndPoll(deeplink, state) {
      const root = document.getElementById("root");
      root.innerHTML = `
        <p>🖥 PC からのデータ提供は、<strong>iPhone のウォレットで下の QR を読み取り SellerVC を提示</strong>すると進みます。</p>
        <div class="qr" id="qr"></div>
        <p class="pulse meta">ウォレットでの提示を待っています…（state=${state.slice(0, 10)}…）</p>
        <details>
          <summary>deeplink (debug)</summary>
          <p class="mono">${deeplink}</p>
        </details>
      `;
      const qr = new QRCode({ content: deeplink, width: 280, height: 280, padding: 0 });
      document.getElementById("qr").innerHTML = qr.svg();
      pollUntilDone(state);
    }

    async function pollUntilDone(state) {
      while (true) {
        try {
          const r = await fetch(
            `${ORIGIN}/verifier/status?state=${encodeURIComponent(state)}`,
            { headers: { Accept: "application/json" } }
          );
          if (r.ok) {
            const body = await r.json();
            // Success: SellerToken minted. /verifier/status surfaces
            // seller_token + licensed_datasets directly.
            if (body.seller_token) {
              renderSuccess(body);
              return;
            }
            const result = body.result;
            if (result && result.verified === false) {
              renderDeny(result);
              return;
            }
          } else if (r.status === 404) {
            const root = document.getElementById("root");
            root.innerHTML = `<div class="err">verifier session expired. リロードしてやり直してください。</div>`;
            return;
          }
        } catch (e) {
          // transient error, keep polling
        }
        await new Promise(r => setTimeout(r, 2000));
      }
    }

    function renderSuccess(body) {
      const root = document.getElementById("root");
      const licensed = body.licensed_datasets || [];
      const items = licensed.map(d => `<li><code>${d}</code></li>`).join("") || "<li><em>(none)</em></li>";
      const expIn = body.expires_in ? `${Math.round(body.expires_in / 60)} 分` : "—";
      root.innerHTML = `
        <div class="ok">
          <strong>SellerVC 提示が承認されました</strong><br />
          ProviderToken (= SellerToken) を発行しました。
        </div>
        <h2 style="font-size:1rem;margin-top:1.5rem">出品許可データセット</h2>
        <ul class="licensed">${items}</ul>
        <p class="meta">seller_id: <code>${body.seller_id || "—"}</code></p>
        <p class="meta">有効期限: ${expIn}</p>
        <details style="margin-top:1rem">
          <summary>SellerToken (debug)</summary>
          <p class="mono">${body.seller_token}</p>
        </details>
        <hr style="margin-block:1.5rem" />
        <p class="meta">
          このトークンを使ったメディアアップロード + イベント発行 UI は次の PR (c2) でこの場所に追加されます。
          現状ではこのページは「OID4VP のプロバイダ側ループが動く」ことの確認用です。
        </p>
      `;
    }

    function renderDeny(result) {
      const root = document.getElementById("root");
      const msg = result.human_message_ja
               || result.human_message_en
               || `Presentation denied (${result.reason || "unknown"}).`;
      root.innerHTML = `
        <div class="err">
          <strong>提示が拒否されました</strong><br />
          ${msg}
        </div>
        <p class="meta">
          reason code: <code>${result.reason || ""}</code>
        </p>
        <p>
          別の VC で試す場合は<a href="" onclick="location.reload();return false;">このページをリロード</a>してください。
        </p>
      `;
    }

    bootstrap();
  </script>
</body>
</html>
"""
