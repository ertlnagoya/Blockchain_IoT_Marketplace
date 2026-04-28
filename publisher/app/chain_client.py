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
