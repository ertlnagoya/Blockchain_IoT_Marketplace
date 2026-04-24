"""Minimal SD-JWT VC issuance and verification.

Implements a subset of draft-ietf-oauth-sd-jwt-vc / draft-ietf-oauth-selective-disclosure-jwt
sufficient for the IW3IP hands-on: ES256 signing, salted disclosures, `_sd` array,
`cnf` holder binding, optional KB-JWT.

This is NOT a full spec implementation: it only supports flat SD claims (no nested
SD, no decoy digests, no array SD), and always uses SHA-256. It is intended for
educational and interop-sanity use against the Sphereon wallet, not production.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

from publisher.app.ssi.keys import jwk_to_private_key, jwk_to_public_key


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=False).encode("utf-8")


def _sha256_b64u(data: bytes) -> str:
    return _b64u(hashlib.sha256(data).digest())


def _es256_sign(private_jwk: dict, signing_input: bytes) -> bytes:
    pk = jwk_to_private_key(private_jwk)
    der = pk.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _es256_verify(public_jwk: dict, signing_input: bytes, signature: bytes) -> bool:
    if len(signature) != 64:
        return False
    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    der = utils.encode_dss_signature(r, s)
    pub = jwk_to_public_key(public_jwk)
    try:
        pub.verify(der, signing_input, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


@dataclass
class SDJWTCredential:
    compact: str
    disclosures: list[str]
    issuer_jwt: str


def make_disclosure(name: str, value) -> tuple[str, str]:
    """Return (disclosure_b64u, sd_digest)."""
    salt = _b64u(secrets.token_bytes(16))
    arr = [salt, name, value]
    encoded = _b64u(_json_bytes(arr))
    digest = _sha256_b64u(encoded.encode("ascii"))
    return encoded, digest


def issue_sd_jwt_vc(
    *,
    issuer_private_jwk: dict,
    issuer_did: str,
    vct: str,
    plain_claims: dict,
    sd_claims: dict,
    holder_cnf_jwk: dict,
    iat: int,
    exp: int,
) -> SDJWTCredential:
    disclosures: list[str] = []
    sd_digests: list[str] = []
    for name, value in sd_claims.items():
        enc, digest = make_disclosure(name, value)
        disclosures.append(enc)
        sd_digests.append(digest)

    body = {
        "iss": issuer_did,
        "vct": vct,
        "iat": iat,
        "exp": exp,
        "cnf": {"jwk": holder_cnf_jwk},
        "_sd_alg": "sha-256",
        **plain_claims,
    }
    if sd_digests:
        body["_sd"] = sd_digests

    header = {"alg": "ES256", "typ": "vc+sd-jwt", "kid": issuer_did + "#0"}
    signing_input = _b64u(_json_bytes(header)).encode("ascii") + b"." + _b64u(_json_bytes(body)).encode("ascii")
    sig = _es256_sign(issuer_private_jwk, signing_input)
    jwt = signing_input.decode("ascii") + "." + _b64u(sig)
    compact = jwt + "~" + "~".join(disclosures) + ("~" if disclosures else "")
    return SDJWTCredential(compact=compact, disclosures=disclosures, issuer_jwt=jwt)


def parse_sd_jwt_vc(compact: str) -> tuple[dict, dict, bytes, list[str], str | None]:
    """Return (header, payload, signature, disclosures, kb_jwt_or_none)."""
    parts = compact.split("~")
    jwt = parts[0]
    rest = parts[1:]
    kb = rest[-1] if rest and rest[-1] else None
    disclosures = [d for d in rest[:-1] if d]

    h_b64, p_b64, s_b64 = jwt.split(".")
    header = json.loads(_b64u_decode(h_b64))
    payload = json.loads(_b64u_decode(p_b64))
    signature = _b64u_decode(s_b64)
    return header, payload, signature, disclosures, kb


def verify_sd_jwt_vc(compact: str, issuer_public_jwk: dict) -> dict:
    header, payload, sig, disclosures, _kb = parse_sd_jwt_vc(compact)
    jwt = compact.split("~")[0]
    signing_input = ".".join(jwt.split(".")[:2]).encode("ascii")
    if not _es256_verify(issuer_public_jwk, signing_input, sig):
        raise ValueError("issuer signature invalid")

    disclosed: dict = {}
    sd_set = set(payload.get("_sd", []))
    for d in disclosures:
        digest = _sha256_b64u(d.encode("ascii"))
        if digest not in sd_set:
            raise ValueError(f"disclosure not referenced by _sd: {digest}")
        salt, name, value = json.loads(_b64u_decode(d))
        disclosed[name] = value

    merged = {k: v for k, v in payload.items() if k not in {"_sd", "_sd_alg"}}
    merged.update(disclosed)
    return merged
