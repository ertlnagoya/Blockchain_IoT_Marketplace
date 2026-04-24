from __future__ import annotations

import base64
import json


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def did_jwk_from_public_jwk(public_jwk: dict) -> str:
    """Encode a did:jwk identifier from a public JWK.

    Per https://github.com/quartzjer/did-jwk/blob/main/spec.md — the method-specific
    id is base64url(JSON(public_jwk)) with canonical key order.
    """
    canonical = json.dumps(public_jwk, sort_keys=True, separators=(",", ":"))
    return "did:jwk:" + _b64u(canonical.encode("utf-8"))


def public_jwk_from_did_jwk(did: str) -> dict:
    if not did.startswith("did:jwk:"):
        raise ValueError("not a did:jwk")
    encoded = did[len("did:jwk:") :]
    padded = encoded + "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
