from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


logger = logging.getLogger(__name__)


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _int_to_b64u(value: int, length: int) -> str:
    return _b64u(value.to_bytes(length, "big"))


def private_key_to_jwk(pk: ec.EllipticCurvePrivateKey) -> dict:
    numbers = pk.private_numbers()
    pub = numbers.public_numbers
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _int_to_b64u(pub.x, 32),
        "y": _int_to_b64u(pub.y, 32),
        "d": _int_to_b64u(numbers.private_value, 32),
    }


def public_jwk_from_private_jwk(jwk: dict) -> dict:
    return {k: v for k, v in jwk.items() if k in {"kty", "crv", "x", "y"}}


def jwk_to_private_key(jwk: dict) -> ec.EllipticCurvePrivateKey:
    d = int.from_bytes(base64.urlsafe_b64decode(jwk["d"] + "=="), "big")
    return ec.derive_private_key(d, ec.SECP256R1(), default_backend())


def jwk_to_public_key(jwk: dict) -> ec.EllipticCurvePublicKey:
    x = int.from_bytes(base64.urlsafe_b64decode(jwk["x"] + "=="), "big")
    y = int.from_bytes(base64.urlsafe_b64decode(jwk["y"] + "=="), "big")
    return ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(),
        b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big"),
    )


class IssuerKeyStore:
    def __init__(self, key_path: str) -> None:
        self._path = Path(key_path)
        self._jwk: dict | None = None

    def load_or_create(self) -> dict:
        if self._jwk is not None:
            return self._jwk
        if self._path.exists():
            self._jwk = json.loads(self._path.read_text(encoding="utf-8"))
            return self._jwk

        logger.info("issuer key not found; generating new P-256 key at %s", self._path)
        pk = ec.generate_private_key(ec.SECP256R1(), default_backend())
        jwk = private_key_to_jwk(pk)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(jwk, indent=2), encoding="utf-8")
        self._path.chmod(0o600)
        self._jwk = jwk
        return jwk

    @property
    def private_jwk(self) -> dict:
        return self.load_or_create()

    @property
    def public_jwk(self) -> dict:
        return public_jwk_from_private_jwk(self.load_or_create())
