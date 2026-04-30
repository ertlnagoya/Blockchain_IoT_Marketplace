"""Stage T (case B + C) — HTTP + IPFS media gateway.

Lets the data-provider side stash a JPEG / MP4 blob and get back the
URL + (optionally) the IPFS CID it can fold into the event payload as
``image_url`` / ``image_cid`` (and the video equivalents). The Phase 2
publisher then runs the same tier-aware ``/platform/data`` projection
on those URL/CID keys.

Two backends, both addressable from one ``POST /media/upload`` call:

- **case B (local)** — always on. The blob lives under
  ``<media_store_path>/<sha256>.<ext>`` and the publisher serves it at
  ``GET /media/<sha256>.<ext>``. Deduped on sha256.

- **case C (IPFS)** — turned on when ``IPFS_API_URL`` is set. The same
  blob is added to a local kubo daemon via ``POST /api/v0/add``, the
  daemon hands back a content-addressed CID, and the response also
  carries an ``ipfs_gateway_url`` that points at
  ``GET /ipfs/<cid>`` on the publisher (which reverse-proxies the
  daemon's HTTP gateway). External callers can dereference the same
  CID through any public gateway (``https://ipfs.io/ipfs/<cid>``,
  ``https://w3s.link/ipfs/<cid>``, ...).

Response shape (stable across both modes; case-C-only fields default
to ``null`` in case B mode):

    {
      "url":              "http://publisher/media/<sha>.<ext>",
      "sha256":           "<hex>",
      "content_type":     "image/jpeg",
      "byte_size":        7645,
      "cid":              "bafy..." | null,
      "ipfs_gateway_url": "http://publisher/ipfs/bafy..." | null
    }

Security: ``/media/<name>`` and ``/ipfs/<cid>`` are unauthenticated on
purpose — the wallet running on the buyer's iPhone must be able to
fetch the blob after the tier-aware projection hands it out.
Authorization is enforced upstream at ``/platform/data`` (ViewerToken
+ ``allowed_views``); the URL / CID is the access token.
"""
from __future__ import annotations

import hashlib
import logging
import mimetypes
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse


logger = logging.getLogger(__name__)


_ALLOWED_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".m4v": "video/mp4",
    # iPhone Safari `<input capture="environment">` saves recorded clips
    # as QuickTime .mov; without this the /provider page hits 415 right
    # after the user finishes recording on a phone.
    ".mov": "video/quicktime",
}


def _resolve_ext(filename: str | None, content_type: str | None) -> str:
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in _ALLOWED_EXT:
            return ext
    if content_type:
        ext = mimetypes.guess_extension(content_type) or ""
        if ext.lower() in _ALLOWED_EXT:
            return ext.lower()
    raise HTTPException(
        status_code=415,
        detail=(
            "unsupported media type; expected one of "
            + ", ".join(sorted(_ALLOWED_EXT))
        ),
    )


def _ipfs_add(api_url: str, body: bytes, filename: str) -> str:
    """Push ``body`` into an IPFS daemon at ``api_url`` and return its CID.

    Uses the ``/api/v0/add`` HTTP API. We pin the result so the daemon
    keeps it alive across restarts, and request CIDv1 so the resulting
    string is the same shape readers see from public gateways.
    """
    boundary = "----iw3ip-ipfs-add"
    crlf = b"\r\n"
    parts = [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode(),
        b"Content-Type: application/octet-stream",
        b"",
        body,
        f"--{boundary}--".encode(),
        b"",
    ]
    payload = crlf.join(parts)
    resp = httpx.post(
        api_url.rstrip("/") + "/api/v0/add",
        params={"cid-version": "1", "pin": "true"},
        content=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    # kubo's /api/v0/add streams ndjson when adding multiple files; for a
    # single file we get one JSON object (or one line). Parse defensively.
    text = resp.text.strip()
    last_line = text.splitlines()[-1] if text else "{}"
    import json as _json

    obj = _json.loads(last_line)
    cid = obj.get("Hash")
    if not cid:
        raise HTTPException(
            status_code=502,
            detail=f"ipfs_add_no_cid response={text[:200]}",
        )
    return cid


def build_router(
    *,
    store_path: str,
    public_base_url: str = "",
    ipfs_api_url: str = "",
    ipfs_gateway_url: str = "",
) -> APIRouter:
    """Return a router with /media/upload + /media/{name} + /ipfs/{cid}.

    ``public_base_url`` is prefixed onto the URLs we hand back. When
    empty we use the request origin so the wallet inherits the same
    hostname it fetched from.

    ``ipfs_api_url`` (e.g. ``http://ipfs:5001``) flips on the case C
    backend: every ``POST /media/upload`` also pushes into IPFS and the
    response gains a ``cid`` field. When empty, only case B (local
    file) runs.

    ``ipfs_gateway_url`` (e.g. ``http://ipfs:8080``) is the URL the
    publisher reverse-proxies ``/ipfs/<cid>`` to. When empty we leave
    the proxy off — callers can dereference the CID through any public
    gateway.
    """
    base = Path(store_path)
    base.mkdir(parents=True, exist_ok=True)

    router = APIRouter()

    @router.post("/media/upload")
    async def media_upload(
        request: Request,
        file: UploadFile = File(...),
    ) -> JSONResponse:
        ext = _resolve_ext(file.filename, file.content_type)
        body = await file.read()
        if not body:
            raise HTTPException(status_code=400, detail="empty_body")
        sha = hashlib.sha256(body).hexdigest()
        name = f"{sha}{ext}"
        path = base / name
        if not path.exists():
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(body)
            tmp.replace(path)
        # Mint URL. When media_public_base_url is set we use it verbatim;
        # otherwise we fall back to the request origin so the wallet on
        # the buyer's phone reaches us at the same hostname.
        origin = (
            public_base_url.rstrip("/")
            if public_base_url
            else str(request.base_url).rstrip("/")
        )
        url = f"{origin}/media/{name}"

        cid: str | None = None
        gateway_url: str | None = None
        if ipfs_api_url:
            try:
                cid = _ipfs_add(ipfs_api_url, body, name)
                gateway_url = f"{origin}/ipfs/{cid}"
            except (httpx.HTTPError, HTTPException) as exc:
                # Don't fail the upload — the case-B URL is still valid.
                logger.warning("ipfs_add failed sha256=%s err=%s", sha[:16], exc)

        logger.info(
            "media_uploaded sha256=%s ext=%s bytes=%d url=%s cid=%s",
            sha[:16] + "...",
            ext,
            len(body),
            url,
            cid or "-",
        )
        return JSONResponse(
            {
                "url": url,
                "sha256": sha,
                "content_type": _ALLOWED_EXT[ext],
                "byte_size": len(body),
                "cid": cid,
                "ipfs_gateway_url": gateway_url,
            }
        )

    @router.get("/media/{name}")
    def media_get(name: str) -> FileResponse:
        # Reject directory traversal / dotted segments.
        if "/" in name or "\\" in name or name.startswith("."):
            raise HTTPException(status_code=400, detail="bad_name")
        path = base / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="not_found")
        return FileResponse(path)

    @router.get("/ipfs/{cid_path:path}")
    def ipfs_get(cid_path: str):
        """Reverse-proxy GET requests to the local kubo HTTP gateway.

        Lets a wallet running on the LAN dereference an IPFS CID without
        needing internet access or a public gateway. ``cid_path`` is
        passed through verbatim so directory listings and subpaths
        (``bafy.../foo/bar.jpg``) still work. The route is **disabled**
        (404) if no gateway URL is configured — callers can then use
        any public gateway directly.
        """
        if not ipfs_gateway_url:
            raise HTTPException(status_code=404, detail="ipfs_proxy_disabled")
        # Block obvious traversal attempts.
        if cid_path.startswith("..") or cid_path.startswith("/"):
            raise HTTPException(status_code=400, detail="bad_cid_path")
        upstream = f"{ipfs_gateway_url.rstrip('/')}/ipfs/{cid_path}"
        # Stream the body so large files don't bloat publisher RAM.
        try:
            resp = httpx.get(upstream, follow_redirects=True, timeout=30.0)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"ipfs_gateway_unreachable: {exc}"
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"ipfs_gateway_error: {resp.text[:200]}",
            )
        # Forward content-type so JPEG / MP4 render correctly in the wallet.
        return StreamingResponse(
            iter([resp.content]),
            media_type=resp.headers.get(
                "content-type", "application/octet-stream"
            ),
        )

    return router
