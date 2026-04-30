"""Stage T (PWA viewer) — minimal browser UI for buyers.

Two pages, both shippable as plain HTML + a few lines of JS so a wallet
or PC browser can render data right after the OID4VP presentation
succeeds:

* ``GET /viewer?vt=<viewer_token>&ds=<dataset_id>``
    Reads ``/platform/data`` with the viewer_token (Bearer) and renders
    image / video / event JSON inline. Works on iPhone Safari and PC
    Chrome / Edge / Firefox identically.

* ``GET /buyer/start?ds=<dataset_id>``
    Single page that adapts to device:

    * **Mobile UA** -- auto-redirects to the OID4VP deeplink so the
      iw3ip-wallet picks up the request, presents, and (thanks to the
      ``redirect_uri`` we hand back at /verifier/response) lands the
      buyer back on /viewer?vt=...
    * **Desktop UA** -- renders a QR for the same deeplink and starts
      polling /verifier/status?state=...; once the wallet on the user's
      phone completes the presentation, the page navigates to the
      ``viewer_url`` returned by /verifier/status.

The whole thing is dependency-free server-side; we just emit HTML + JS.
The QR rendering happens client-side via ``qrcode-svg`` (CDN-pinned)
so the publisher doesn't have to install browser-side JS deps.
"""
from __future__ import annotations

import html
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse


logger = logging.getLogger(__name__)


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/viewer", response_class=HTMLResponse)
    def viewer_page(
        request: Request,
        vt: str = Query(..., description="ViewerToken"),
        ds: str = Query(..., description="dataset_id"),
    ) -> HTMLResponse:
        """HTML viewer that reads /platform/data and renders the row."""
        # Sanitise the values we splice into the page; we'll only echo
        # them back as JSON literals (json.dumps is HTML-safe enough for
        # data-* attributes here).
        safe_vt = json.dumps(vt)
        safe_ds = json.dumps(ds)
        page_origin = str(request.base_url).rstrip("/")
        safe_origin = json.dumps(page_origin)

        body = _VIEWER_HTML.replace("__VT__", safe_vt) \
                           .replace("__DS__", safe_ds) \
                           .replace("__ORIGIN__", safe_origin)
        return HTMLResponse(body)

    @router.get("/buyer/start", response_class=HTMLResponse)
    def buyer_start_page(
        request: Request,
        ds: str = Query(..., description="dataset_id"),
        purpose: str = Query("read"),
        vc_kind: str = Query("PurchaseViewerVC"),
    ) -> HTMLResponse:
        """Single page that bootstraps the OID4VP request + UA-aware UX."""
        if not ds:
            raise HTTPException(status_code=400, detail="ds_required")
        # Build the same-device deeplink and give the page enough info
        # to long-poll /verifier/status. We hand the actual /verifier/request
        # call to the client-side script so the page mints a fresh
        # state per page-load (avoiding stale sessions on hot-reload).
        page_origin = str(request.base_url).rstrip("/")
        safe = lambda v: json.dumps(v)  # noqa: E731
        body = (
            _BUYER_START_HTML
            .replace("__ORIGIN__", safe(page_origin))
            .replace("__DS__", safe(ds))
            .replace("__PURPOSE__", safe(purpose))
            .replace("__VC_KIND__", safe(vc_kind))
        )
        return HTMLResponse(body)

    return router


# ----------------------------------------------------------------------
# /viewer page template
# ----------------------------------------------------------------------
_VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IW3IP Viewer</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      margin: 0;
      padding: 1rem;
      max-width: 760px;
      margin-inline: auto;
      line-height: 1.5;
    }
    header { display: flex; align-items: baseline; gap: 0.75rem; margin-bottom: 1rem; }
    h1 { font-size: 1.25rem; margin: 0; }
    .badge {
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(33, 150, 243, 0.15);
      color: #1565c0;
    }
    .badge.tier-3 { background: rgba(76, 175, 80, 0.18); color: #2e7d32; }
    .badge.tier-2 { background: rgba(255, 152, 0, 0.20); color: #c77800; }
    .badge.tier-1 { background: rgba(158, 158, 158, 0.25); color: #555; }
    section { margin-block: 1rem; }
    .media { display: grid; gap: 0.75rem; }
    .media img, .media video {
      width: 100%; max-height: 360px; object-fit: contain;
      border-radius: 8px; background: #f3f3f3;
    }
    pre {
      background: #1e1e1e; color: #eaeaea; padding: 0.75rem; border-radius: 6px;
      overflow-x: auto; font-size: 0.78rem;
    }
    .empty { padding: 1rem; background: #fff7e6; border-radius: 6px; color: #8a6d3b; }
    .err { padding: 1rem; background: #fdecea; border-radius: 6px; color: #b71c1c; }
    .meta { font-size: 0.85rem; color: #666; }
    a.cid {
      font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
      word-break: break-all;
    }
  </style>
</head>
<body>
  <header>
    <h1 id="title">IW3IP Viewer</h1>
    <span id="tier" class="badge">…</span>
  </header>
  <p class="meta" id="meta"></p>

  <div id="root">
    <p>Loading…</p>
  </div>

  <script>
    const VT = __VT__;
    const DS = __DS__;
    const ORIGIN = __ORIGIN__;

    function el(tag, attrs, ...children) {
      const e = document.createElement(tag);
      for (const [k, v] of Object.entries(attrs || {})) {
        if (v == null) continue;
        if (k === "class") e.className = v;
        else if (k === "text") e.textContent = v;
        else e.setAttribute(k, v);
      }
      for (const c of children) {
        if (c == null) continue;
        e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
      }
      return e;
    }

    async function load() {
      const root = document.getElementById("root");
      root.innerHTML = "";
      try {
        const r = await fetch(
          `${ORIGIN}/platform/data?dataset_id=${encodeURIComponent(DS)}`,
          { headers: { Authorization: `Bearer ${VT}` } }
        );
        if (!r.ok) {
          let detail = "";
          try { detail = JSON.stringify(await r.json()); }
          catch { detail = await r.text(); }
          const banner = el("div", { class: "err" });
          if (r.status === 401) {
            banner.innerHTML = `<strong>ViewerToken の有効期限が切れています</strong><br />` +
              `読み取り権限を再取得するため、購入画面 (<a href="${ORIGIN}/buyer/start?ds=${encodeURIComponent(DS)}">/buyer/start</a>) からウォレットで再提示してください。`;
          } else if (r.status === 403) {
            banner.innerHTML = `<strong>このデータを閲覧する権限がありません</strong><br />` +
              `提示された VC ではこのデータセットへのアクセスが許可されていません。`;
          } else if (r.status === 404) {
            banner.innerHTML = `<strong>データセットが見つかりません</strong><br />` +
              `dataset_id=${DS} は publisher に登録されていない可能性があります。`;
          } else {
            banner.textContent = `HTTP ${r.status}: ${detail.slice(0, 240)}`;
          }
          root.appendChild(banner);
          return;
        }
        const body = await r.json();
        const tier = (body.allowed_views || []).join("+") || "—";
        document.getElementById("tier").textContent = `tier: ${tier}`;
        document.getElementById("tier").classList.add(
          body.allowed_views?.includes("video") ? "tier-3" :
          body.allowed_views?.includes("image") ? "tier-2" : "tier-1"
        );
        document.getElementById("meta").textContent =
          `${DS} • ${body.count} row${body.count === 1 ? "" : "s"}` +
          (body.seller_did ? ` • seller=${body.seller_did}` : "");

        if (!body.rows?.length) {
          root.appendChild(el("div", { class: "empty",
            text: "このデータセットにはまだイベントが届いていません。" }));
          return;
        }
        for (const row of body.rows) {
          root.appendChild(renderRow(row));
        }
      } catch (e) {
        root.innerHTML = "";
        root.appendChild(el("div", { class: "err",
          text: `network error: ${e.message || e}` }));
      }
    }

    function renderRow(row) {
      const card = el("section");
      const media = el("div", { class: "media" });

      // image_url is the publisher-hosted URL (Stage T case B). When
      // the producer used IPFS too (case C) image_cid + ipfs_gateway_url
      // also exist; we just prefer image_url for the inline render
      // because it's guaranteed-reachable on the buyer's network.
      if (row.image_url) {
        media.appendChild(el("img", { src: row.image_url, alt: "image" }));
      }
      if (row.video_url) {
        media.appendChild(el("video", { src: row.video_url, controls: "" }));
      }
      if (media.children.length) card.appendChild(media);

      // Surface the IPFS CID if present so the viewer doubles as
      // proof-of-content-addressing.
      if (row.image_cid) {
        card.appendChild(el("p", { class: "meta" },
          "IPFS CID: ",
          el("a", { class: "cid", href: `${ORIGIN}/ipfs/${row.image_cid}` },
            row.image_cid)
        ));
      }

      const ts = row.payload?.ts || row.ts || "";
      if (ts) card.appendChild(el("p", { class: "meta", text: `ts: ${ts}` }));

      const detail = el("details");
      detail.appendChild(el("summary", { text: "Payload (raw)" }));
      detail.appendChild(el("pre", { text: JSON.stringify(row, null, 2) }));
      card.appendChild(detail);
      return card;
    }

    load();
  </script>
</body>
</html>
"""


# ----------------------------------------------------------------------
# /buyer/start page template
# ----------------------------------------------------------------------
_BUYER_START_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IW3IP Purchase</title>
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
    .deeplink {
      display: inline-block; padding: 0.6rem 1rem;
      background: #2196f3; color: #fff; border-radius: 6px;
      text-decoration: none; margin-block: 0.5rem;
    }
    .pulse { animation: pulse 1.4s ease-in-out infinite; }
    @keyframes pulse {
      0%, 100% { opacity: 0.55; }
      50% { opacity: 1; }
    }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/qrcode-svg@1.1.0/dist/qrcode.min.js"></script>
</head>
<body>
  <h1>IW3IP Purchase</h1>
  <p class="meta" id="meta"></p>
  <div id="root"><p class="pulse">Bootstrapping verifier session…</p></div>

  <script>
    const ORIGIN = __ORIGIN__;
    const DS = __DS__;
    const PURPOSE = __PURPOSE__;
    const VC_KIND = __VC_KIND__;

    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    document.getElementById("meta").textContent =
      `dataset_id=${DS} • purpose=${PURPOSE} • ${isMobile ? "📱 same-device" : "🖥 cross-device"}`;

    async function bootstrap() {
      const root = document.getElementById("root");
      try {
        const url = new URL(`${ORIGIN}/verifier/request`);
        url.searchParams.set("dataset_id", DS);
        url.searchParams.set("purpose", PURPOSE);
        url.searchParams.set("vc_kind", VC_KIND);
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
          // Same-device: jump straight to the wallet. The wallet will
          // bounce back to /viewer via redirect_uri once it presents.
          root.innerHTML = `
            <p>📱 ウォレットを起動しています…</p>
            <a class="deeplink" href="${deeplink}">ウォレットで開く</a>
            <p class="meta">起動しない場合は上のボタンをタップしてください。</p>
          `;
          window.location.href = deeplink;
        } else {
          // Desktop: show QR + start polling for completion.
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
        <p>🖥 PC からの購入は、<strong>iPhone のウォレットで下の QR を読み取る</strong>と進みます。</p>
        <div class="qr" id="qr"></div>
        <p class="pulse meta">ウォレットでの提示を待っています…（state=${state.slice(0, 10)}…）</p>
        <details>
          <summary>deeplink (debug)</summary>
          <p style="word-break:break-all;font-family:ui-monospace,Menlo,monospace;font-size:0.78rem">${deeplink}</p>
        </details>
      `;
      // QRCode is provided by qrcode-svg.
      const qr = new QRCode({ content: deeplink, width: 280, height: 280, padding: 0 });
      document.getElementById("qr").innerHTML = qr.svg();
      pollUntilDone(state);
    }

    let lastShown = 0;
    async function pollUntilDone(state) {
      while (true) {
        try {
          const r = await fetch(
            `${ORIGIN}/verifier/status?state=${encodeURIComponent(state)}`,
            { headers: { Accept: "application/json" } }
          );
          if (r.ok) {
            const body = await r.json();
            // Success: navigate to the data viewer.
            if (body.viewer_url) {
              window.location.href = body.viewer_url;
              return;
            }
            // Stage T (PWA viewer): the verifier denied the
            // presentation. Show the human-readable reason instead of
            // looping forever.
            const result = body.result;
            if (result && result.verified === false) {
              const root = document.getElementById("root");
              const msg = result.human_message_ja
                       || result.human_message_en
                       || `Presentation denied (${result.reason || "unknown"}).`;
              root.innerHTML = `
                <div class="err">
                  <strong>データを閲覧する権限がありません</strong><br />
                  ${msg}
                </div>
                <p class="meta">
                  reason code: <code>${result.reason || ""}</code>
                </p>
                <p>
                  別の VC で試す場合は<a href="" onclick="location.reload();return false;">このページをリロード</a>してください。
                </p>
              `;
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

    bootstrap();
  </script>
</body>
</html>
"""
