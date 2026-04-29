"""Stage T (case B) — minimal HTTP media gateway.

Lets the data-provider side stash a JPEG / MP4 blob and get back a
stable URL it can fold into the event payload as ``image_url`` /
``video_url``. The Phase 2 publisher then runs the same tier-aware
``/platform/data`` projection on those URL keys that it already runs on
``image_cid`` / ``video_cid``.

This is **not** a content-addressed store — the wallet just dereferences
the URL like any other static asset. Case C will replace it with a real
IPFS / Web3.Storage backend; the API surface here (POST /media/upload
returning a JSON ``{url, sha256, content_type, byte_size}``) is the same
shape, so callers shouldn't need to change.

Storage layout::

    <media_store_path>/<sha256>.<ext>

The sha256 doubles as the filename so duplicates dedupe automatically.

Security: ``/media/<sha256>.<ext>`` is unauthenticated **on purpose** —
the wallet running on the buyer's iPhone must be able to fetch it after
the tier-aware projection hands the URL out. Authorization is enforced
upstream at ``/platform/data`` (ViewerToken + ``allowed_views``).
"""
from __future__ import annotations

import hashlib
import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse


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


def build_router(*, store_path: str, public_base_url: str = "") -> APIRouter:
    """Return a router with /media/upload (POST) + /media/{name} (GET).

    ``public_base_url`` is prefixed onto the URL we hand back. When empty
    we hand back a relative ``/media/<name>`` so callers inherit the
    request's own origin (this is what the dockerised tests exercise).
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
        if public_base_url:
            url = f"{public_base_url.rstrip('/')}/media/{name}"
        else:
            origin = str(request.base_url).rstrip("/")
            url = f"{origin}/media/{name}"
        logger.info(
            "media_uploaded sha256=%s ext=%s bytes=%d url=%s",
            sha[:16] + "...",
            ext,
            len(body),
            url,
        )
        return JSONResponse(
            {
                "url": url,
                "sha256": sha,
                "content_type": _ALLOWED_EXT[ext],
                "byte_size": len(body),
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

    return router
