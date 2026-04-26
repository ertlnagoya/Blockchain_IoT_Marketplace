"""Helpers for picking URLs the wallet can actually reach.

The publisher runs inside Docker and binds the configured `SSI_ISSUER_BASE_URL`
(default `http://publisher:8080`) into every protocol message. That hostname
only resolves inside the Compose network, so any URL the wallet has to fetch
or post to (issuer metadata, credential offer's `credential_issuer`, token
and credential endpoints, OID4VP `request_uri` / `response_uri`) is unusable
when the wallet sits on the host LAN or a phone.

When the configured base points at a known-internal host
(publisher/localhost/127.*/0.0.0.0), fall back to the scheme+host of the
inbound HTTP request: by definition that's how the caller reached us, so
echoing it back gives them a URL that round-trips. `client_id`, `iss`, `aud`
keep the configured value because they are stable identifiers, not fetch
targets.
"""

from __future__ import annotations

import urllib.parse

from fastapi import Request


_INTERNAL_HOST_PREFIXES = ("publisher", "localhost", "127.", "0.0.0.0")


def externally_reachable_base_url(request: Request, configured: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(configured)
    except ValueError:
        parsed = None
    host = (parsed.hostname or "") if parsed else ""
    if host and not any(host == p.rstrip(".") or host.startswith(p) for p in _INTERNAL_HOST_PREFIXES):
        return configured.rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    scheme = forwarded_proto or request.url.scheme
    host_header = forwarded_host or request.url.netloc
    return f"{scheme}://{host_header}".rstrip("/")
