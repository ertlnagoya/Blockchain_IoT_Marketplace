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
  </style>
</head>
<body>
  <h1>IW3IP Provider — Upload &amp; Publish</h1>
  <p class="meta" id="meta"></p>

  <fieldset>
    <legend>1. メディアをアップロード <span class="pill">/media/upload</span></legend>
    <p class="meta">画像 (JPEG / PNG / WebP) または動画 (MP4 / WebM) を選んでください。SHA-256 で重複排除されるので同じファイルの再アップロードは無料です。</p>
    <input type="file" id="file" accept="image/*,video/*" />
    <div class="preview" id="preview"></div>
    <div id="uploadResult"></div>
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
    const fileInput = document.getElementById("file");
    const preview = document.getElementById("preview");
    const uploadResult = document.getElementById("uploadResult");
    const publishBtn = document.getElementById("publishBtn");
    const publishHint = document.getElementById("publishHint");

    fileInput.addEventListener("change", async () => {
      const f = fileInput.files?.[0];
      preview.innerHTML = "";
      uploadResult.innerHTML = "";
      if (!f) {
        publishBtn.disabled = true;
        publishHint.textContent = "先にメディアをアップロードしてください";
        return;
      }

      // local preview
      const url = URL.createObjectURL(f);
      const isImg = f.type.startsWith("image/");
      const tag = document.createElement(isImg ? "img" : "video");
      tag.src = url;
      if (!isImg) tag.controls = true;
      preview.appendChild(tag);

      // upload to /media/upload (open by design)
      uploadResult.innerHTML = `<p class="meta">アップロード中…</p>`;
      const fd = new FormData();
      fd.append("file", f);
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
            <strong>アップロード完了</strong><br />
            URL: <a href="${lastUpload.url}" target="_blank" rel="noopener noreferrer">${lastUpload.url}</a>
            ${cidLine}
            <br /><span class="meta">${lastUpload.content_type} • ${lastUpload.byte_size} bytes • sha256=${lastUpload.sha256.slice(0, 12)}…</span>
          </div>
        `;
        publishBtn.disabled = false;
        publishHint.textContent = "発行する内容を確認して Publish を押してください";
      } catch (e) {
        uploadResult.innerHTML = `<div class="err">network error: ${e.message || e}</div>`;
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
