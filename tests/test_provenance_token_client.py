"""Stage P (C2PA provenance) P2: ProvenanceToken.mint from the publisher.

Verifies the calldata matches the Solidity ABI (vector from ethers) and
that the token ID is read from the ERC-721 Transfer log. No chain or
C2PA SDK is needed.
"""
from __future__ import annotations

from unittest.mock import patch

from publisher.app.chain_client import ProvenanceTokenClient, encode_provenance_mint


def test_mint_calldata_matches_solidity_abi():
    # Vector from ethers: AbiCoder.encode(["address","string","bytes32",
    # "string","string"], [0x11..11, "urn:c2pa:abc", 0xab..ab, "bafyCID", ""])
    expected = (
        "0x04bcdede"
        "0000000000000000000000001111111111111111111111111111111111111111"
        "00000000000000000000000000000000000000000000000000000000000000a0"
        "abababababababababababababababababababababababababababababababab"
        "00000000000000000000000000000000000000000000000000000000000000e0"
        "0000000000000000000000000000000000000000000000000000000000000120"
        "000000000000000000000000000000000000000000000000000000000000000c"
        "75726e3a633270613a6162630000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000007"
        "6261667943494400000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    got = encode_provenance_mint("0x" + "11" * 20, "urn:c2pa:abc", "ab" * 32, "bafyCID", "")
    assert got == expected


def test_mint_reads_token_id_from_transfer_log():
    token = "0x" + "cc" * 20
    client = ProvenanceTokenClient(rpc_url="http://node:8545", token_address=token)
    calls = []

    def fake_rpc(method, params):
        calls.append(method)
        if method == "eth_call":  # tokenOfAsset: not anchored yet
            assert params[0]["data"] == "0x160e475d" + "ab" * 32
            return {"result": "0x" + "00" * 32}
        if method == "eth_accounts":
            return {"result": ["0x" + "aa" * 20]}
        if method == "eth_sendTransaction":
            assert params[0]["data"].startswith("0x04bcdede")
            return {"result": "0x" + "77" * 32}
        return {"result": {"status": "0x1", "logs": [{
            "address": token,
            "topics": [
                "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                "0x" + "00" * 32, "0x" + "00" * 12 + "aa" * 20,
                "0x" + "00" * 31 + "07",
            ],
        }]}}

    with patch.object(client._chain, "_post_rpc", side_effect=fake_rpc):
        out = client.mint(manifest_label="urn:c2pa:x", asset_sha256="ab" * 32, cid="", seller_did="")
    assert out == {"token_id": 7, "tx_hash": "0x" + "77" * 32, "contract": token, "reused": False}
    assert calls == ["eth_call", "eth_accounts", "eth_sendTransaction", "eth_getTransactionReceipt"]


def test_mint_reuses_the_token_of_an_anchored_image():
    """A second event with the same image (or a retry) must not try to mint
    again -- the contract would refuse -- but get the existing token."""
    token = "0x" + "cc" * 20
    client = ProvenanceTokenClient(rpc_url="http://node:8545", token_address=token)
    calls = []

    def fake_rpc(method, params):
        calls.append(method)
        return {"result": "0x" + "00" * 31 + "05"}

    with patch.object(client._chain, "_post_rpc", side_effect=fake_rpc):
        out = client.mint(manifest_label="urn:c2pa:x", asset_sha256="ab" * 32, cid="", seller_did="")
    assert out == {"token_id": 5, "tx_hash": None, "contract": token, "reused": True}
    assert calls == ["eth_call"]
