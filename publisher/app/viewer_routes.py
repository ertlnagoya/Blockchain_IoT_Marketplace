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
    /* Stage T (VLM extension): semantic-tier styling. */
    .badge.tier-summary { background: rgba(96, 125, 139, 0.20); color: #455a64; }
    .description {
      background: #f5f5f5; padding: 0.75rem 1rem; border-radius: 6px;
      border-left: 3px solid #2e7d32; margin-block: 0.5rem;
    }
    .description.summary { border-left-color: #c77800; }
    .description-label {
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em;
      color: #666; margin-bottom: 0.3rem;
    }
    .warnings {
      padding: 0.75rem 1rem; background: #fff7e6; border-radius: 6px;
      border-left: 3px solid #f57c00; color: #8a6d3b; margin-block: 0.5rem;
      font-size: 0.85rem;
    }
    .warnings code {
      background: rgba(245, 124, 0, 0.15); padding: 1px 6px; border-radius: 4px;
      margin-inline: 2px; font-family: ui-monospace, Menlo, monospace; font-size: 0.78rem;
    }
    .redacted-badge {
      font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em;
      background: rgba(96, 125, 139, 0.20); color: #455a64;
      padding: 1px 6px; border-radius: 4px; margin-left: 6px;
      vertical-align: middle;
    }
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

  <div style="margin-block:0.5rem">
    <label style="font-size:0.85rem;color:#555;cursor:pointer">
      <input type="checkbox" id="semanticToggle" />
      🔬 意味的レンダリングを使う (実験) — /semantic/render_url 経由で信頼度別表示
    </label>
    <div class="meta" id="semanticInfo" style="margin-top:0.25rem"></div>
  </div>

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
        // Stage T (VLM extension): the badge picks up the new semantic
        // tiers. With raw video -> tier-3, with raw image -> tier-2,
        // with image_redacted (no raw image) -> tier-2 still (visual
        // tier 2 either way), with description_summary only and no
        // images -> the new "summary" tier; otherwise tier-1 (event-only).
        const v = body.allowed_views || [];
        const tierClass =
          v.includes("video") ? "tier-3" :
          v.includes("image") || v.includes("image_redacted") ? "tier-2" :
          v.includes("description_summary") ? "tier-summary" :
          "tier-1";
        document.getElementById("tier").classList.add(tierClass);
        document.getElementById("meta").textContent =
          `${DS} • ${body.count} row${body.count === 1 ? "" : "s"}` +
          (body.seller_did ? ` • seller=${body.seller_did}` : "");

        if (!body.rows?.length) {
          root.appendChild(el("div", { class: "empty",
            text: "このデータセットにはまだイベントが届いていません。" }));
          return;
        }
        // Stage T+ opt-in: when the toggle is on, derive a viewer
        // trust level from the body.allowed_views and replace each
        // row's render with /semantic/render_url output. Default
        // (toggle off) keeps the existing renderRow path.
        const useSemantic = document.getElementById("semanticToggle").checked;
        const semanticInfo = document.getElementById("semanticInfo");
        if (useSemantic) {
          const tl = deriveTrustLevel(body.allowed_views || []);
          semanticInfo.textContent = `derived trust level: ${tl}`;
          for (const row of body.rows) {
            const card = el("section");
            root.appendChild(card);
            renderRowSemantic(card, row, tl).catch(err => {
              card.innerHTML = "";
              card.appendChild(el("div", { class: "err",
                text: "semantic render failed: " + (err.message || err) }));
            });
          }
        } else {
          semanticInfo.textContent = "";
          for (const row of body.rows) {
            root.appendChild(renderRow(row));
          }
        }
      } catch (e) {
        root.innerHTML = "";
        root.appendChild(el("div", { class: "err",
          text: `network error: ${e.message || e}` }));
      }
    }

    // Map the existing Stage T allowed_views array to a
    // ViewerTrustLevel. The mapping is intentionally conservative:
    // empty / unknown -> anonymous, anything richer than text-only
    // becomes medium or higher. The semantic pipeline's own policy
    // engine then makes the final masking decisions, so a slightly
    // generous mapping here doesn't relax fail-closed.
    function deriveTrustLevel(allowedViews) {
      const v = new Set(allowedViews);
      if (v.has("video")) return "high";
      if (v.has("image") || v.has("image_redacted")) return "medium";
      if (v.has("description_summary") || v.has("description_full")) return "low";
      if (v.has("event")) return "anonymous";
      return "anonymous"; // fail-closed default
    }

    async function renderRowSemantic(card, row, trustLevel) {
      // Decide which URL to feed the semantic pipeline. Prefer the
      // raw image_url when present (HIGH viewers); fall back to
      // image_url_redacted (MEDIUM/Tier-2 VLM); otherwise text-only.
      const sourceUrl = row.image_url || row.image_url_redacted || null;
      const reqBody = { trust_level: trustLevel };
      if (sourceUrl) reqBody.image_url = sourceUrl;

      // No image at all (Tier 1 / event-only): skip the network call
      // and just render the row's existing payload as text.
      let out;
      if (!sourceUrl) {
        out = {
          trust_level: trustLevel,
          granted_kinds: ["eventList"],
          text_summary: row.payload?.event_type || row.event_type || "",
          event_list: [],
          rationale: "no source image; text-only path",
        };
      } else {
        const r = await fetch(`${ORIGIN}/semantic/render_url`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(reqBody),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0,200)}`);
        out = await r.json();
      }

      // Render the trust-aware result. Always show the granted_kinds
      // and rationale so the receiver knows why they're seeing
      // (or not seeing) image bytes.
      card.innerHTML = "";
      const head = el("div", { class: "meta" });
      head.textContent = `[${out.trust_level}] kinds: ${(out.granted_kinds || []).join(" + ") || "(none)"}`;
      card.appendChild(head);
      if (out.image_b64) {
        const img = el("img", {
          src: `data:${out.image_content_type || "image/jpeg"};base64,${out.image_b64}`,
          alt: "trust-aware rendered image",
        });
        img.style.maxWidth = "100%";
        img.style.maxHeight = "360px";
        img.style.borderRadius = "8px";
        img.style.background = "#f3f3f3";
        card.appendChild(img);
      }
      if (out.text_summary) {
        const p = el("p");
        p.textContent = out.text_summary;
        card.appendChild(p);
      }
      if ((out.event_list || []).length) {
        const ul = el("ul");
        for (const ev of out.event_list) {
          const li = el("li");
          li.textContent = `${ev.type}: ${ev.description}`;
          ul.appendChild(li);
        }
        card.appendChild(ul);
      }
      if (out.audit_required) {
        const audit = el("p", { class: "meta" });
        audit.style.color = "#b71c1c";
        audit.textContent = "🛡 audit_required=true (owner/admin access)";
        card.appendChild(audit);
      }
      if (out.rationale) {
        const det = el("details");
        det.appendChild(el("summary", { class: "meta", text: "policy rationale" }));
        det.appendChild(el("pre", { text: out.rationale }));
        card.appendChild(det);
      }
    }

    function renderRow(row) {
      const card = el("section");
      const media = el("div", { class: "media" });

      // Stage T media projection. Order of preference for the inline
      // <img> rendering:
      //   row.image_url          (Tier 3 raw, case B/C)
      //   row.image_url_redacted (Tier 2+ blurred, VLM extension)
      // We render whichever is present. Only one shows up at a time
      // because /platform/data drops keys per allowed_views.
      if (row.image_url) {
        media.appendChild(el("img", { src: row.image_url, alt: "image" }));
      } else if (row.image_url_redacted) {
        const wrap = el("div");
        const img = el("img", { src: row.image_url_redacted, alt: "redacted image" });
        wrap.appendChild(img);
        const tag = el("span", { class: "redacted-badge", text: "🔒 face/PII blurred" });
        wrap.appendChild(tag);
        media.appendChild(wrap);
      }
      if (row.video_url) {
        media.appendChild(el("video", { src: row.video_url, controls: "" }));
      }
      if (media.children.length) card.appendChild(media);

      // Stage T (VLM extension): description_full / description_summary
      // appear at Tier 2+ / Tier 1+ respectively. Show both when both
      // are visible (Tier 2/3) so the receiver sees the contrast
      // between named-entity detail and PII-scrubbed summary.
      if (row.description_full) {
        const box = el("div", { class: "description" });
        box.appendChild(el("div", { class: "description-label", text: "VLM detailed (full)" }));
        box.appendChild(el("p", { text: row.description_full }));
        card.appendChild(box);
      }
      if (row.description_summary) {
        const box = el("div", { class: "description summary" });
        box.appendChild(el("div", { class: "description-label", text: "VLM summary (PII-redacted)" }));
        box.appendChild(el("p", { text: row.description_summary }));
        card.appendChild(box);
      }

      // Stage T (VLM extension): processing_warnings tells the receiver
      // which derivative steps were degraded. The meaningful keys today
      // are vlm_unavailable + redaction_unavailable; we render any
      // future warnings transparently so the contract is forward-
      // compatible.
      if (Array.isArray(row.processing_warnings) && row.processing_warnings.length) {
        const w = el("div", { class: "warnings" });
        const intro = el("span", {
          text: "⚠ 一部の派生データが省略されました: ",
        });
        w.appendChild(intro);
        row.processing_warnings.forEach((name, i) => {
          if (i > 0) w.appendChild(document.createTextNode(" "));
          w.appendChild(el("code", { text: name }));
        });
        card.appendChild(w);
      }

      // Surface the IPFS CID if present so the viewer doubles as
      // proof-of-content-addressing. Show the redacted variant too
      // so receivers can audit which content-addressed bytes they
      // actually got.
      if (row.image_cid) {
        card.appendChild(el("p", { class: "meta" },
          "IPFS CID: ",
          el("a", { class: "cid", href: `${ORIGIN}/ipfs/${row.image_cid}` },
            row.image_cid)
        ));
      }
      if (row.image_cid_redacted) {
        card.appendChild(el("p", { class: "meta" },
          "IPFS CID (redacted): ",
          el("a", { class: "cid", href: `${ORIGIN}/ipfs/${row.image_cid_redacted}` },
            row.image_cid_redacted)
        ));
      }

      // Surface VLM model + generation time so the receiver knows
      // exactly which inference produced description_*.
      if (row.description_model) {
        const meta = el("p", { class: "meta" });
        meta.textContent = `VLM: ${row.description_model}`;
        if (row.description_generated_at) {
          meta.textContent += ` • generated ${row.description_generated_at}`;
        }
        card.appendChild(meta);
      }

      const ts = row.payload?.ts || row.ts || "";
      if (ts) card.appendChild(el("p", { class: "meta", text: `ts: ${ts}` }));

      const detail = el("details");
      detail.appendChild(el("summary", { text: "Payload (raw)" }));
      detail.appendChild(el("pre", { text: JSON.stringify(row, null, 2) }));
      card.appendChild(detail);
      return card;
    }

    // Re-run load() when the operator toggles the semantic switch
    // so they can flip between legacy projection and the
    // trust-aware semantic render without a hard reload. Persist
    // the choice in localStorage so refreshing the page keeps the
    // preference.
    const semanticToggleEl = document.getElementById("semanticToggle");
    semanticToggleEl.checked =
      localStorage.getItem("iw3ip_viewer_semantic_mode") === "1";
    semanticToggleEl.addEventListener("change", () => {
      localStorage.setItem(
        "iw3ip_viewer_semantic_mode",
        semanticToggleEl.checked ? "1" : "0"
      );
      load();
    });

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
