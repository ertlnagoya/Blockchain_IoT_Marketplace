"""Minimal Ethereum JSON-RPC client used by /marketplace/register.

We only need one read: Merchandise.getOwner(). Rather than pulling in
web3.py, we craft the eth_call ourselves — getOwner() returns a
single 20-byte address, which is straightforward to encode/decode.

Selector keccak256("getOwner()")[:4] = 0x893d20e8
(verified against the Merchandise contract used by the iot-market
deploy scripts).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

GET_OWNER_SELECTOR = "0x893d20e8"


@dataclass
class ChainClientSettings:
    rpc_url: str | None
    request_timeout_seconds: float = 5.0

    @property
    def enabled(self) -> bool:
        return bool(self.rpc_url)


class ChainClient:
    def __init__(self, settings: ChainClientSettings) -> None:
        self._settings = settings

    def _post_rpc(self, method: str, params: list) -> dict:
        if not self._settings.rpc_url:
            raise RuntimeError("chain client disabled (no rpc_url)")
        body = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        with httpx.Client(timeout=self._settings.request_timeout_seconds) as c:
            r = c.post(self._settings.rpc_url, json=body)
            r.raise_for_status()
            return r.json()

    def merchandise_owner(self, merchandise_address: str) -> str | None:
        """Return the Merchandise.getOwner() result as a checksum-less
        lowercase 0x-prefixed address. Returns None on any error so the
        caller can fail-closed without a stack trace.
        """
        if not self._settings.enabled:
            return None
        try:
            payload = self._post_rpc(
                "eth_call",
                [
                    {
                        "to": merchandise_address,
                        "data": GET_OWNER_SELECTOR,
                    },
                    "latest",
                ],
            )
        except (httpx.HTTPError, httpx.InvalidURL, RuntimeError) as exc:
            logger.warning("chain RPC eth_call(getOwner) failed: %s", exc)
            return None

        result = payload.get("result")
        if not isinstance(result, str) or len(result) < 66:
            logger.warning("chain RPC eth_call(getOwner) bad result: %r", payload)
            return None
        # 32-byte returndata, address right-padded in last 20 bytes.
        owner_hex = result[-40:]
        return ("0x" + owner_hex).lower()


# ---- Stage P (C2PA provenance) P2: ProvenanceToken.mint ----
# mint(address,string,bytes32,string,string); selector checked by
# iot-market/test/unit/ProvenanceToken.test.ts. We send it with
# eth_sendTransaction from an unlocked Hardhat account, so no signing
# key lives in the publisher (local hands-on only).
PROVENANCE_MINT_SELECTOR = "04bcdede"
# tokenOfAsset(bytes32)
PROVENANCE_TOKEN_OF_ASSET_SELECTOR = "160e475d"
# keccak256("Transfer(address,address,uint256)")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _word(n: int) -> bytes:
    return n.to_bytes(32, "big")


def _encode_string(s: str) -> bytes:
    raw = s.encode("utf-8")
    pad = (-len(raw)) % 32
    return _word(len(raw)) + raw + b"\0" * pad


def encode_provenance_mint(
    to: str, manifest_label: str, asset_sha256: str, cid: str, seller_did: str
) -> str:
    """ABI-encode ``mint(to, manifestLabel, assetSha256, cid, sellerDid)``
    as 0x-prefixed calldata."""
    to_bytes = bytes.fromhex(to.removeprefix("0x"))
    sha_bytes = bytes.fromhex(asset_sha256.removeprefix("0x"))
    if len(to_bytes) != 20 or len(sha_bytes) != 32:
        raise ValueError("bad address or sha256")
    tails = [_encode_string(manifest_label), _encode_string(cid), _encode_string(seller_did)]
    head_size = 5 * 32
    offsets = [head_size]
    for t in tails[:-1]:
        offsets.append(offsets[-1] + len(t))
    head = (
        b"\0" * 12 + to_bytes
        + _word(offsets[0])
        + sha_bytes
        + _word(offsets[1])
        + _word(offsets[2])
    )
    return "0x" + PROVENANCE_MINT_SELECTOR + (head + b"".join(tails)).hex()


class ProvenanceMintError(Exception):
    pass


class ProvenanceTokenClient:
    """Mint one ProvenanceToken per event through a Hardhat node."""

    def __init__(
        self, *, rpc_url: str, token_address: str, minter: str = "", timeout: float = 10.0
    ) -> None:
        self._chain = ChainClient(ChainClientSettings(rpc_url, timeout))
        self.token_address = token_address
        self._minter = minter

    @classmethod
    def from_settings(cls, settings) -> "ProvenanceTokenClient | None":
        if not (settings.provenance_token_address and settings.provenance_rpc_url):
            return None
        return cls(
            rpc_url=settings.provenance_rpc_url,
            token_address=settings.provenance_token_address,
            minter=settings.provenance_minter_address,
        )

    def _rpc(self, method: str, params: list):
        try:
            payload = self._chain._post_rpc(method, params)
        except (httpx.HTTPError, httpx.InvalidURL, RuntimeError) as exc:
            raise ProvenanceMintError(f"{method} failed: {exc}") from exc
        if "error" in payload:
            raise ProvenanceMintError(f"{method} error: {payload['error']}")
        return payload.get("result")

    def minter(self) -> str:
        if not self._minter:
            accounts = self._rpc("eth_accounts", [])
            if not accounts:
                raise ProvenanceMintError("node has no unlocked accounts")
            self._minter = accounts[0]
        return self._minter

    def token_of_asset(self, asset_sha256: str) -> int:
        """Return the token already anchoring ``asset_sha256``, or 0."""
        data = "0x" + PROVENANCE_TOKEN_OF_ASSET_SELECTOR + asset_sha256.removeprefix("0x")
        result = self._rpc("eth_call", [{"to": self.token_address, "data": data}, "latest"])
        return int(result, 16) if result and result != "0x" else 0

    def mint(
        self, *, manifest_label: str, asset_sha256: str, cid: str, seller_did: str
    ) -> dict:
        """Send the mint and return ``{token_id, tx_hash, contract, reused}``.

        An image is anchored once (the contract refuses a second mint of
        the same sha256), so an image that already has a token -- a
        second event with the same image_url, or a retry after a failed
        send -- gets that token back with ``reused: True`` and
        ``tx_hash: None``. Hardhat mines each transaction at once, so
        the receipt is read right after sending; the token ID comes from
        the ERC-721 Transfer log (topic 3).
        """
        existing = self.token_of_asset(asset_sha256)
        if existing:
            return {"token_id": existing, "tx_hash": None, "contract": self.token_address,
                    "reused": True}
        minter = self.minter()
        data = encode_provenance_mint(minter, manifest_label, asset_sha256, cid, seller_did)
        tx_hash = self._rpc(
            "eth_sendTransaction",
            [{"from": minter, "to": self.token_address, "data": data}],
        )
        receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
        if not receipt or receipt.get("status") != "0x1":
            raise ProvenanceMintError(f"mint reverted tx={tx_hash}")
        for log in receipt.get("logs", []):
            topics = log.get("topics") or []
            if (
                log.get("address", "").lower() == self.token_address.lower()
                and topics
                and topics[0] == TRANSFER_TOPIC
                and len(topics) == 4
            ):
                return {
                    "token_id": int(topics[3], 16),
                    "tx_hash": tx_hash,
                    "contract": self.token_address,
                    "reused": False,
                }
        raise ProvenanceMintError(f"no Transfer log in tx={tx_hash}")
