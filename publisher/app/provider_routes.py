"""Stage T (PWA provider) -- browser UI for data providers.

Three routes ship together:

* ``GET /provider/start`` (c1) -- bootstraps the SellerVC OID4VP loop
  (UA-aware: phone deeplink vs. PC QR + long-poll). On success the
  page navigates to ``/provider`` with the freshly-minted SellerToken.

* ``GET /provider`` (c2) -- the actual upload + publish UI. Accepts
  ``?pt=<seller_token>&ds=<dataset_id>``, lets the provider pick an
  image / video / event JSON, calls /media/upload, and POSTs the
  resulting payload to /provider/publish.

* ``POST /provider/publish`` (c2) -- Bearer-SellerToken-gated wrapper
  around ``processor.process_message``. The dataset (derived from the
  topic, same as /simulate/publish) must be in the SellerToken's
  ``licensed_datasets`` -- enforced via the multi-use ``use_seller_token``
  helper. ``/media/upload`` itself stays open: the URL it returns is
  the access token (same model the buyer side uses for /platform/data).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from audit.models import AuditLogRecord
from audit.repository import SQLiteAuditRepository
from publisher.app.models import SimulatePublishRequest
from publisher.app.pipeline import MessageProcessor
from publisher.app.ssi.state import SSIStateStore


logger = logging.getLogger(__name__)


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization_header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid_authorization_header")
    return token


def build_router(
    *,
    ssi_state: SSIStateStore,
    processor: MessageProcessor,
    audit_repo: SQLiteAuditRepository,
) -> APIRouter:
    router = APIRouter()

    @router.get("/provider/start", response_class=HTMLResponse)
    def provider_start_page(
        request: Request,
        ds: str | None = Query(default=None),
        state: str | None = Query(default=None),
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

    @router.get("/provider", response_class=HTMLResponse)
    def provider_page(
        request: Request,
        pt: str = Query(..., description="SellerToken (Bearer for /provider/publish)"),
        ds: str = Query(..., description="dataset_id to publish to"),
    ) -> HTMLResponse:
        page_origin = str(request.base_url).rstrip("/")
        safe = lambda v: json.dumps(v)  # noqa: E731
        body = (
            _PROVIDER_HTML
            .replace("__ORIGIN__", safe(page_origin))
            .replace("__PT__", safe(pt))
            .replace("__DS__", safe(ds))
        )
        return HTMLResponse(body)

    @router.post("/provider/publish")
    def provider_publish(
        req: SimulatePublishRequest,
        authorization: str | None = Header(default=None),
    ) -> dict:
        """Bearer-SellerToken wrapper around processor.process_message.

        Dataset is derived from the topic via the same normalize() pipeline
        /simulate/publish uses; we then check the resolved dataset_id
        against the SellerToken's licensed_datasets list.
        """
        token = _bearer_token(authorization)

        # Resolve dataset_id from the topic+payload before we look up the
        # SellerToken so the licensed_datasets check is meaningful even
        # when the topic itself is well-formed but the dataset isn't
        # licensed.
        from schemas.models import normalize  # local import: schemas is heavy

        try:
            normalized = normalize(req.topic, req.payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"unsupported_topic:{exc}")
        dataset_id = normalized.dataset_id

        seller_token, reason = ssi_state.use_seller_token(token, dataset_id=dataset_id)
        if not seller_token:
            audit_repo.write(
                AuditLogRecord(
                    ts=datetime.now(timezone.utc).isoformat(),
                    action="deny",
                    subject_did="unknown",
                    dataset_id=dataset_id,
                    purpose=req.purpose or "publish",
                    reason=f"seller_token_{reason}",
                    message_hash="",
                    raw_topic=req.topic,
                    holder_did=None,
                    vc_hash=None,
                    presentation_verified="deny",
                )
            )
            status = 401 if reason in ("unknown", "expired") else 403
            raise HTTPException(status_code=status, detail=f"seller_token_{reason}")

        result: dict[str, Any] = processor.process_message(
            req.topic, req.payload, req.purpose
        )
        # Keep the SellerToken-derived identity in the response so the
        # /provider page can show the provider who authored what.
        result["seller_did"] = seller_token.seller_did
        result["seller_token_jti"] = seller_token.jti
        result["register_count"] = seller_token.register_count
        return result

    return router


# ----------------------------------------------------------------------
# /provider/start page template (c1)
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
    @keyframes pulse { 0%, 100% { opacity: 0.55; } 50% { opacity: 1; } }
    code, .mono {
      font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
      font-size: 0.85rem; word-break: break-all;
    }
    ul.licensed { padding-inline-start: 1.2rem; }
    .ds-pick {
      display: flex; gap: 0.5rem; align-items: center;
      margin-top: 1rem; flex-wrap: wrap;
    }
    .ds-pick input { flex: 1 1 240px; padding: 0.4rem; }
    .btn {
      display: inline-block; padding: 0.5rem 1rem; border-radius: 6px;
      background: #2e7d32; color: #fff; text-decoration: none;
      border: 0; cursor: pointer; font-size: 0.95rem;
    }
    .btn[disabled] { background: #aaa; cursor: not-allowed; }
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
      if (RESUME_STATE) {
        root.innerHTML = `<p class="pulse">ウォレットからの戻りを処理中…</p>`;
        pollUntilDone(RESUME_STATE);
        return;
      }
      try {
        const url = new URL(`${ORIGIN}/verifier/request`);
        url.searchParams.set("vc_kind", VC_KIND);
        // SellerVC isn't dataset-scoped at verify time; verifier_routes
        // looks up presentation definitions per (vc_kind, dataset_id)
        // and only registers SellerVC under the "*" sentinel. Passing
        // the actual dataset hint here returns 404
        // no_presentation_definition_for_dataset. The DS_HINT is purely
        // a display label in the page header above.
        url.searchParams.set("dataset_id", "*");
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
          // transient
        }
        await new Promise(r => setTimeout(r, 2000));
      }
    }

    function renderSuccess(body) {
      const root = document.getElementById("root");
      const licensed = body.licensed_datasets || [];
      // c2: when DS_HINT is one of the licensed datasets, we can offer
      // a "go straight to /provider" button. Otherwise we let the user
      // pick from licensed_datasets.
      const preselected = licensed.includes(DS_HINT) ? DS_HINT : (licensed[0] || "");
      const items = licensed.map(d =>
        `<li><label><input type="radio" name="ds" value="${d}" ${d === preselected ? "checked" : ""} /> <code>${d}</code></label></li>`
      ).join("") || "<li><em>(none)</em> — このウォレットにはまだデータセットが付与されていません</li>";
      const expIn = body.expires_in ? `${Math.round(body.expires_in / 60)} 分` : "—";
      root.innerHTML = `
        <div class="ok">
          <strong>SellerVC 提示が承認されました</strong><br />
          ProviderToken (= SellerToken) を発行しました。
        </div>
        <h2 style="font-size:1rem;margin-top:1.5rem">出品許可データセット — 1 つ選んでください</h2>
        <ul class="licensed" id="dsList">${items}</ul>
        <p class="meta">seller_id: <code>${body.seller_id || "—"}</code></p>
        <p class="meta">有効期限: ${expIn}</p>
        <div class="ds-pick">
          <button class="btn" id="goProvider" ${licensed.length ? "" : "disabled"}>
            選んだデータセットでアップロードへ進む →
          </button>
        </div>
        <details style="margin-top:1rem">
          <summary>SellerToken (debug)</summary>
          <p class="mono">${body.seller_token}</p>
        </details>
      `;
      document.getElementById("goProvider").addEventListener("click", () => {
        const sel = document.querySelector('input[name="ds"]:checked');
        if (!sel) return;
        const u = new URL(`${ORIGIN}/provider`);
        u.searchParams.set("pt", body.seller_token);
        u.searchParams.set("ds", sel.value);
        window.location.href = u.toString();
      });
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
        <p class="meta">reason code: <code>${result.reason || ""}</code></p>
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


# ----------------------------------------------------------------------
# /provider page template (c2)
# ----------------------------------------------------------------------
_PROVIDER_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IW3IP Provider — Upload &amp; Publish</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      margin: 0; padding: 1rem; max-width: 760px; margin-inline: auto;
      line-height: 1.5;
    }
    h1 { font-size: 1.2rem; margin-block-start: 0; }
    fieldset { border: 1px solid #ccc; border-radius: 8px; margin-block: 1rem; padding: 1rem; }
    legend { font-weight: 600; padding: 0 0.5rem; }
    label { display: block; margin-block: 0.4rem 0.2rem; font-size: 0.9rem; color: #555; }
    input[type=text], input[type=number], textarea, select {
      width: 100%; padding: 0.4rem; box-sizing: border-box; font-size: 0.95rem;
    }
    textarea { min-height: 6em; font-family: ui-monospace, Menlo, monospace; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }
    .meta { font-size: 0.85rem; color: #666; }
    .err { padding: 0.75rem; background: #fdecea; border-radius: 6px; color: #b71c1c; margin-block: 0.5rem; }
    .ok  { padding: 0.75rem; background: #e8f5e9; border-radius: 6px; color: #1b5e20; margin-block: 0.5rem; }
    pre { background: #1e1e1e; color: #eaeaea; padding: 0.75rem; border-radius: 6px; overflow: auto; font-size: 0.78rem; }
    .btn {
      display: inline-block; padding: 0.55rem 1rem; border-radius: 6px;
      background: #2e7d32; color: #fff; text-decoration: none;
      border: 0; cursor: pointer; font-size: 0.95rem;
    }
    .btn.secondary { background: #455a64; }
    .btn[disabled] { background: #aaa; cursor: not-allowed; }
    .preview img, .preview video {
      max-width: 100%; max-height: 240px; border-radius: 6px; background: #f3f3f3;
    }
    .row-fields { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
    .pill {
      background: rgba(46,125,50,0.12); color: #1b5e20;
      padding: 2px 8px; border-radius: 999px; font-size: 0.75rem;
    }
    .modes {
      display: grid; gap: 0.75rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .mode {
      border: 1px solid #ddd; border-radius: 6px; padding: 0.75rem;
      background: rgba(0,0,0,0.02);
    }
    .mode-title { font-weight: 600; color: #2e7d32; margin-bottom: 0.4rem; display:block; }
    .mode input[type=file] { width: 100%; }
    .rec-on { background: #c62828 !important; }
    /* SIR analysis affordances */
    .sir-bbox-overlay { position: relative; display: inline-block; max-width: 100%; }
    .sir-bbox-overlay img { display: block; max-width: 100%; max-height: 320px; }
    .sir-bbox-overlay .sir-bbox {
      position: absolute; box-sizing: border-box;
      border: 2px solid #d32f2f; background: rgba(211, 47, 47, 0.18);
      pointer-events: none;
    }
    .sir-bbox-overlay .sir-bbox-label {
      position: absolute; top: 0; left: 0; transform: translateY(-100%);
      background: #d32f2f; color: #fff; font-size: 0.65rem;
      padding: 1px 4px; border-radius: 3px; font-family: ui-monospace, Menlo, monospace;
    }
    .sir-tier-grid {
      display: grid; gap: 0.6rem;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      margin-top: 0.5rem;
    }
    .sir-tier-card {
      border: 1px solid #ddd; border-radius: 6px; padding: 0.6rem;
      background: rgba(0,0,0,0.02); font-size: 0.85rem;
    }
    .sir-tier-card .tier-name {
      font-weight: 600; font-size: 0.75rem; text-transform: uppercase;
      letter-spacing: 0.05em; color: #455a64; margin-bottom: 0.4rem;
    }
    .sir-tier-card .tier-kinds {
      font-family: ui-monospace, Menlo, monospace; font-size: 0.7rem;
      color: #666; margin-bottom: 0.3rem;
    }
    .sir-summary-row {
      display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;
      margin-block: 0.4rem; font-size: 0.85rem;
    }
    .sir-risk-pill {
      padding: 2px 8px; border-radius: 999px; font-size: 0.75rem;
      background: rgba(211, 47, 47, 0.15); color: #b71c1c;
    }
    .sir-risk-pill.low { background: rgba(76,175,80,0.15); color: #2e7d32; }
    .sir-risk-pill.mid { background: rgba(255,152,0,0.18); color: #c77800; }
  </style>
</head>
<body>
  <h1>IW3IP Provider — Upload &amp; Publish</h1>
  <p class="meta" id="meta"></p>

  <fieldset>
    <legend>1. メディアをアップロード <span class="pill">/media/upload</span></legend>
    <p class="meta">提供方法を 3 つから選べます。どのソースでも SHA-256 で重複排除されます。</p>

    <div class="modes">
      <div class="mode">
        <label class="mode-title">📁 ファイルから選ぶ</label>
        <input type="file" id="filePick" accept="image/*,video/*" />
        <p class="meta">PC / スマホ共通。既存のファイルを選択。</p>
      </div>
      <div class="mode">
        <label class="mode-title">📷 カメラで撮影 (iPhone 推奨)</label>
        <input type="file" id="fileCapture" accept="image/*,video/*" capture="environment" />
        <p class="meta">iPhone Safari ではカメラが直接起動します。PC では通常のファイル選択にフォールバック。</p>
      </div>
      <div class="mode">
        <label class="mode-title">🔴 ブラウザで録画 (PC 推奨)</label>
        <div class="row-fields">
          <button class="btn secondary" id="recStart" type="button">録画開始</button>
          <button class="btn" id="recStop" type="button" disabled>停止 &amp; アップロード</button>
          <span class="meta" id="recStatus">待機中</span>
        </div>
        <video id="recPreview" muted playsinline style="display:none;width:100%;max-height:200px;background:#000;border-radius:6px;margin-top:0.5rem"></video>
        <p class="meta">PC のウェブカメラ + マイクから録画 (WebM / VP9)。停止すると自動アップロードします。</p>
      </div>
    </div>

    <div class="preview" id="preview"></div>
    <div id="uploadResult"></div>
  </fieldset>

  <fieldset>
    <legend>1.5 意味的中間表現を確認 <span class="pill">POST /semantic/analyze</span></legend>
    <p class="meta">
      アップロードしたフレームに含まれるセンシティブ領域（顔・テキスト・画面など）と、
      閲覧者の信頼度別に何が見えるかを事前確認できます。サーバ側は分析結果を JSON
      で返すだけで、フレームのバイト列は応答に含まれません。
    </p>
    <div class="row-fields" style="margin-top: 0.5rem">
      <button class="btn secondary" id="analyzeBtn" type="button" disabled>分析を実行</button>
      <span class="meta" id="analyzeStatus">アップロード後に有効になります</span>
    </div>
    <div id="sirResult" style="margin-top: 0.7rem"></div>
    <div id="sirOverlay" style="margin-top: 0.7rem"></div>
    <div id="sirTrustPreview" style="margin-top: 0.7rem"></div>
  </fieldset>

  <fieldset>
    <legend>2. イベントを発行 <span class="pill">POST /provider/publish</span></legend>
    <div class="row">
      <div>
        <label>topic</label>
        <input type="text" id="topic" />
      </div>
      <div>
        <label>purpose</label>
        <input type="text" id="purpose" value="community_cleaning" />
      </div>
    </div>
    <div class="row">
      <div>
        <label>camera_id (event payload)</label>
        <input type="text" id="cameraId" value="webcam-401" />
      </div>
      <div>
        <label>video_duration_sec</label>
        <input type="number" id="videoDuration" value="12" min="0" />
      </div>
    </div>
    <label>extra payload keys (JSON, merged into event payload — optional)</label>
    <textarea id="extraJson" placeholder='{"weather":"clear"}'></textarea>
    <div class="row-fields" style="margin-top: 0.7rem">
      <button class="btn" id="publishBtn" disabled>Publish event</button>
      <span class="meta" id="publishHint">先にメディアをアップロードしてください</span>
    </div>
    <div id="publishResult"></div>
  </fieldset>

  <fieldset>
    <legend>3. 受信側で確認</legend>
    <p class="meta">
      この dataset の受信側 PWA は
      <a id="buyerLink" target="_blank" rel="noopener noreferrer">/buyer/start</a>
      から開けます（Tier 3 の PurchaseViewerVC を提示してください）。
    </p>
  </fieldset>

  <script>
    const ORIGIN = __ORIGIN__;
    const PT = __PT__;
    const DS = __DS__;

    document.getElementById("meta").textContent = `dataset_id=${DS}`;
    // event topic defaults to "homeassistant/event/<last-segment-of-ds>"
    const lastSeg = DS.split("/").pop();
    document.getElementById("topic").value = `homeassistant/event/${lastSeg}`;
    const buyerLink = document.getElementById("buyerLink");
    const buyerUrl = new URL(`${ORIGIN}/buyer/start`);
    buyerUrl.searchParams.set("ds", DS);
    buyerLink.href = buyerUrl.toString();
    buyerLink.textContent = buyerUrl.toString();

    let lastUpload = null; // { url, cid, ipfs_gateway_url, content_type, byte_size }
    let lastSourceBlob = null; // raw bytes for /semantic/analyze
    const preview = document.getElementById("preview");
    const uploadResult = document.getElementById("uploadResult");
    const publishBtn = document.getElementById("publishBtn");
    const publishHint = document.getElementById("publishHint");
    // Stage T+ semantic pipeline UI handles
    const analyzeBtn = document.getElementById("analyzeBtn");
    const analyzeStatus = document.getElementById("analyzeStatus");
    const sirResult = document.getElementById("sirResult");
    const sirOverlay = document.getElementById("sirOverlay");
    const sirTrustPreview = document.getElementById("sirTrustPreview");

    // ---- shared upload pipeline ----
    // All three input modes (file / capture / recorder) end up calling
    // this with a Blob-or-File. We render a local preview, POST to
    // /media/upload, and update lastUpload + the publish button state.
    async function uploadBlob(blob, sourceLabel) {
      preview.innerHTML = "";
      uploadResult.innerHTML = `<p class="meta">アップロード中… (${sourceLabel})</p>`;

      // local preview
      const objectUrl = URL.createObjectURL(blob);
      const isImg = (blob.type || "").startsWith("image/");
      const tag = document.createElement(isImg ? "img" : "video");
      tag.src = objectUrl;
      if (!isImg) tag.controls = true;
      preview.appendChild(tag);

      // /media/upload expects a multipart `file` field. For File objects
      // FormData uses File.name; for raw Blobs (from MediaRecorder) we
      // pass an explicit filename so the server's _resolve_ext picks the
      // right extension.
      const fd = new FormData();
      const filename = blob.name || (blob.type.startsWith("video/") ? "recorded.webm" : "recorded.bin");
      fd.append("file", blob, filename);
      try {
        const r = await fetch(`${ORIGIN}/media/upload`, { method: "POST", body: fd });
        const text = await r.text();
        if (!r.ok) {
          uploadResult.innerHTML = `<div class="err">HTTP ${r.status}: ${text}</div>`;
          return;
        }
        lastUpload = JSON.parse(text);
        const cidLine = lastUpload.cid
          ? `<br /><span class="meta">CID: <code>${lastUpload.cid}</code></span>`
          : "";
        uploadResult.innerHTML = `
          <div class="ok">
            <strong>アップロード完了</strong> (${sourceLabel})<br />
            URL: <a href="${lastUpload.url}" target="_blank" rel="noopener noreferrer">${lastUpload.url}</a>
            ${cidLine}
            <br /><span class="meta">${lastUpload.content_type} • ${lastUpload.byte_size} bytes • sha256=${lastUpload.sha256.slice(0, 12)}…</span>
          </div>
        `;
        publishBtn.disabled = false;
        publishHint.textContent = "発行する内容を確認して Publish を押してください";
        // Stage T+ semantic pipeline: enable the analyze button and
        // remember the source blob so we can re-POST it without
        // re-fetching the (possibly /media-deduped) URL.
        analyzeBtn.disabled = false;
        analyzeStatus.textContent = "「分析を実行」を押すと SIR を確認できます";
        analyzeBtn.dataset.sourceBlob = sourceLabel;  // for status only
        lastSourceBlob = blob;
      } catch (e) {
        uploadResult.innerHTML = `<div class="err">network error: ${e.message || e}</div>`;
      }
    }

    function bindFileInput(id, label) {
      const el = document.getElementById(id);
      el.addEventListener("change", () => {
        const f = el.files?.[0];
        if (f) uploadBlob(f, label);
      });
    }
    bindFileInput("filePick", "ファイル選択");
    bindFileInput("fileCapture", "カメラ撮影");

    // Stage T+ semantic analysis. POSTs the same blob the upload
    // pipeline used to /semantic/analyze, renders the resulting SIR
    // (sensitive regions, scene summary, privacy_risk_score), and
    // shows what 4 trust levels (anonymous/low/medium/high) would
    // see for this frame. Only the analysis runs here -- nothing is
    // published, sent externally, or written to /viewer state.
    analyzeBtn.addEventListener("click", async () => {
      if (!lastSourceBlob) {
        analyzeStatus.textContent = "アップロードがまだです";
        return;
      }
      analyzeBtn.disabled = true;
      analyzeStatus.textContent = "サーバ側で分析中…";
      sirResult.innerHTML = "";
      sirOverlay.innerHTML = "";
      sirTrustPreview.innerHTML = "";

      let sir = null;
      try {
        const fd = new FormData();
        const fname = (lastSourceBlob && lastSourceBlob.name) || "frame.jpg";
        fd.append("file", lastSourceBlob, fname);
        fd.append("source_device_id", "provider-page-" + (navigator.userAgent.match(/iPhone|iPad/) ? "iphone" : "browser"));
        const r = await fetch(`${ORIGIN}/semantic/analyze`, { method: "POST", body: fd });
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 200)}`);
        sir = await r.json();
      } catch (e) {
        sirResult.innerHTML = `<div class="err">analyze failed: ${e.message || e}</div>`;
        analyzeBtn.disabled = false;
        analyzeStatus.textContent = "もう一度試せます";
        return;
      }

      // ---- summary line + risk pill ----
      const risk = Number(sir.privacy_risk_score || 0);
      const riskClass = risk < 0.3 ? "low" : (risk < 0.7 ? "mid" : "");
      sirResult.innerHTML = `
        <div class="ok">
          <strong>分析完了</strong> (analyzer: <code>${escapeHtml(sir.analyzer_version)}</code>)
        </div>
        <div class="sir-summary-row">
          <span class="sir-risk-pill ${riskClass}">privacy_risk_score: ${risk.toFixed(2)}</span>
          <span>${escapeHtml(sir.scene_summary || "(scene_summary なし)")}</span>
        </div>
        <details>
          <summary class="meta">SIR (raw JSON)</summary>
          <pre style="background:#1e1e1e;color:#eaeaea;padding:0.6rem;border-radius:6px;overflow:auto;font-size:0.7rem">${escapeHtml(JSON.stringify(sir, null, 2))}</pre>
        </details>
      `;

      // ---- bbox overlay on the preview image ----
      if (lastUpload && lastUpload.url && (sir.sensitive_regions || []).length) {
        renderBboxOverlay(sir, lastUpload.url);
      }

      // ---- per-tier disclosure preview ----
      await renderTrustPreview(sir);

      analyzeBtn.disabled = false;
      analyzeStatus.textContent = "再分析もできます";
    });

    function renderBboxOverlay(sir, sourceUrl) {
      const wrap = document.createElement("div");
      wrap.className = "sir-bbox-overlay";
      const img = document.createElement("img");
      img.src = sourceUrl;
      img.alt = "source frame with bbox overlay";
      wrap.appendChild(img);

      img.addEventListener("load", () => {
        for (const region of sir.sensitive_regions || []) {
          const bb = region.bbox || {};
          const box = document.createElement("div");
          box.className = "sir-bbox";
          box.style.left = (bb.x * 100) + "%";
          box.style.top = (bb.y * 100) + "%";
          box.style.width = (bb.width * 100) + "%";
          box.style.height = (bb.height * 100) + "%";
          const lbl = document.createElement("span");
          lbl.className = "sir-bbox-label";
          lbl.textContent = `${region.type} ${(region.confidence || 0).toFixed(2)}`;
          box.appendChild(lbl);
          wrap.appendChild(box);
        }
      });
      sirOverlay.innerHTML = "";
      const title = document.createElement("p");
      title.className = "meta";
      title.textContent = "検出されたセンシティブ領域 (赤枠):";
      sirOverlay.appendChild(title);
      sirOverlay.appendChild(wrap);
    }

    async function renderTrustPreview(sir) {
      const tiers = ["anonymous", "low", "medium", "high"];
      const grid = document.createElement("div");
      grid.className = "sir-tier-grid";
      sirTrustPreview.innerHTML = "";
      const title = document.createElement("p");
      title.className = "meta";
      title.textContent = "信頼度別の見え方プレビュー:";
      sirTrustPreview.appendChild(title);
      sirTrustPreview.appendChild(grid);

      for (const t of tiers) {
        const card = document.createElement("div");
        card.className = "sir-tier-card";
        card.innerHTML = `<div class="tier-name">${t}</div><div class="tier-kinds meta">…</div><div class="tier-text meta">…</div>`;
        grid.appendChild(card);
        // Fire-and-walk: each tier renders independently. Errors
        // surface inline and don't block the others.
        renderOneTier(t, sir, card).catch(err => {
          card.querySelector(".tier-text").textContent = "render failed: " + (err.message || err);
        });
      }
    }

    async function renderOneTier(trust, sir, cardEl) {
      const body = { trust_level: trust, sir };
      // Only attach image_url when we have an upload URL AND the tier
      // could actually consume it. anonymous / low never see images,
      // so skip the fetch entirely there to save a /media GET.
      if (lastUpload && lastUpload.url && trust !== "anonymous" && trust !== "low") {
        body.image_url = lastUpload.url;
      }
      const r = await fetch(`${ORIGIN}/semantic/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        cardEl.querySelector(".tier-text").textContent = `HTTP ${r.status}`;
        return;
      }
      const out = await r.json();
      cardEl.querySelector(".tier-kinds").textContent = (out.granted_kinds || []).join(" + ") || "(none)";
      cardEl.querySelector(".tier-text").textContent = out.text_summary || "(no summary)";
      if (out.image_b64) {
        const img = document.createElement("img");
        img.src = `data:${out.image_content_type || "image/jpeg"};base64,${out.image_b64}`;
        img.style.maxWidth = "100%";
        img.style.maxHeight = "120px";
        img.style.borderRadius = "4px";
        img.style.marginTop = "0.4rem";
        cardEl.appendChild(img);
      }
    }

    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, c => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c]
      ));
    }

    // ---- MediaRecorder mode (PC ブラウザ録画) ----
    let mediaStream = null;
    let mediaRecorder = null;
    let recChunks = [];
    const recStart = document.getElementById("recStart");
    const recStop = document.getElementById("recStop");
    const recPreview = document.getElementById("recPreview");
    const recStatus = document.getElementById("recStatus");

    function pickRecorderMime() {
      // Prefer VP9 then VP8. Real-device matrix on macOS (verified
      // 2026-04-30 in iw3ip.github.io PR #29 §11.8 B/C/D):
      //   Chrome 147:    all 4 supported -> picks VP9
      //   Safari 17+:    all 4 supported -> picks VP9 (modern Safari
      //                  has WebM/VP9 native support; the long-standing
      //                  "Safari falls back to MP4" assumption only
      //                  applies to Safari 16 and earlier)
      //   Firefox 139:   only VP8 / webm -> picks VP8
      // The MP4 entry stays for Safari 14.1-16 backwards compat.
      const candidates = [
        "video/webm;codecs=vp9,opus",
        "video/webm;codecs=vp8,opus",
        "video/webm",
        "video/mp4",
      ];
      for (const m of candidates) {
        if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
      }
      return "";
    }

    recStart.addEventListener("click", async () => {
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        recStatus.textContent = "このブラウザは録画に対応していません";
        recStatus.style.color = "#b71c1c";
        return;
      }
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: true,
        });
        recPreview.srcObject = mediaStream;
        recPreview.style.display = "block";
        await recPreview.play().catch(() => { /* autoplay may be blocked, ignore */ });

        const mime = pickRecorderMime();
        const opts = mime ? { mimeType: mime } : {};
        mediaRecorder = new MediaRecorder(mediaStream, opts);
        recChunks = [];
        mediaRecorder.ondataavailable = (ev) => {
          if (ev.data && ev.data.size > 0) recChunks.push(ev.data);
        };
        mediaRecorder.onstop = async () => {
          const startedAt = mediaRecorder._startedAt || Date.now();
          const durationSec = Math.max(1, Math.round((Date.now() - startedAt) / 1000));
          // Auto-fill the video_duration_sec field with the actual length.
          document.getElementById("videoDuration").value = String(durationSec);

          const type = (mime || "video/webm").split(";")[0];
          const ext = type.endsWith("mp4") ? "mp4" : "webm";
          const blob = new Blob(recChunks, { type });
          const filename = `recorded-${Date.now()}.${ext}`;
          // Wrap as File so the upload pipeline shows a friendly name.
          const file = new File([blob], filename, { type });

          // Tear down the camera stream now that we have the blob.
          mediaStream.getTracks().forEach(t => t.stop());
          recPreview.srcObject = null;
          recPreview.style.display = "none";

          recStart.disabled = false;
          recStart.classList.remove("rec-on");
          recStop.disabled = true;
          recStatus.textContent = `録画完了 (${durationSec}s) — アップロード中…`;
          recStatus.style.color = "";

          await uploadBlob(file, "ブラウザ録画");
          recStatus.textContent = `録画完了 (${durationSec}s)`;
        };
        mediaRecorder._startedAt = Date.now();
        mediaRecorder.start(1000); // gather a chunk every 1 s

        recStart.disabled = true;
        recStart.classList.add("rec-on");
        recStop.disabled = false;
        recStatus.textContent = "🔴 録画中…";
      } catch (e) {
        recStatus.textContent = `カメラの取得に失敗: ${e.message || e}`;
        recStatus.style.color = "#b71c1c";
      }
    });

    recStop.addEventListener("click", () => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    });

    publishBtn.addEventListener("click", async () => {
      const topic = document.getElementById("topic").value.trim();
      const purpose = document.getElementById("purpose").value.trim();
      const cameraId = document.getElementById("cameraId").value.trim();
      const videoDuration = parseInt(document.getElementById("videoDuration").value, 10) || 0;
      let extra = {};
      const extraText = document.getElementById("extraJson").value.trim();
      if (extraText) {
        try {
          extra = JSON.parse(extraText);
        } catch (e) {
          document.getElementById("publishResult").innerHTML =
            `<div class="err">extra JSON のパースに失敗: ${e.message}</div>`;
          return;
        }
      }

      const isImage = (lastUpload?.content_type || "").startsWith("image/");
      const payload = {
        ts: new Date().toISOString(),
        source: "iw3ip-provider-page",
        event_type: "possible_littering",
        camera_id: cameraId,
        ...(isImage
          ? { image_url: lastUpload.url }
          : { video_url: lastUpload.url, video_duration_sec: videoDuration }),
        ...(lastUpload?.cid ? { image_cid: lastUpload.cid } : {}),
        data: {
          purpose,
          dataset_id: DS,
        },
        ...extra,
      };

      const out = document.getElementById("publishResult");
      out.innerHTML = `<p class="meta">Publish 中…</p>`;
      try {
        const r = await fetch(`${ORIGIN}/provider/publish`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${PT}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ topic, payload, purpose }),
        });
        const text = await r.text();
        if (!r.ok) {
          out.innerHTML = `<div class="err">HTTP ${r.status}: ${text}</div>`;
          return;
        }
        const body = JSON.parse(text);
        out.innerHTML = `
          <div class="ok">
            <strong>Published</strong>
            <br /><span class="meta">status=${body.status} • dataset=${body.dataset_id || DS}</span>
          </div>
          <details><summary>response (raw)</summary><pre>${JSON.stringify(body, null, 2)}</pre></details>
        `;
      } catch (e) {
        out.innerHTML = `<div class="err">network error: ${e.message || e}</div>`;
      }
    });
  </script>
</body>
</html>
"""
