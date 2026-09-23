"""Deterministic tests for the read-only Ethereum RPC adapter."""

import json
import os
import unittest
from unittest.mock import patch

import httpx

from backend.blockchain.ethereum import (
    EthereumAdapter,
    EthereumRPCError,
    _decode_abi_string,
)


def _abi_string(text: str) -> str:
    encoded = text.encode("utf-8")
    padded = encoded + bytes((-len(encoded)) % 32)
    return "0x" + (32).to_bytes(32, "big").hex() + len(encoded).to_bytes(32, "big").hex() + padded.hex()


class EthereumAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_rpc_url_from_environment_or_argument(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "ETH_RPC_URL is required"):
                EthereumAdapter()
        adapter = EthereumAdapter("https://rpc.example.invalid")
        self.assertEqual(adapter.rpc_url, "https://rpc.example.invalid")

    async def test_metadata_calls_parse_json_rpc_and_abi(self):
        address = "0x" + "12" * 20
        calls = []

        async def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            calls.append(payload)
            result_by_method = {
                "eth_blockNumber": "0x1234",
                "eth_call": None,
            }
            if payload["method"] == "eth_blockNumber":
                result = result_by_method["eth_blockNumber"]
            else:
                selector = payload["params"][0]["data"]
                result = {
                    "0x06fdde03": _abi_string("Example Token"),
                    "0x95d89b41": _abi_string("EXT"),
                    "0x313ce567": "0x" + (6).to_bytes(32, "big").hex(),
                }[selector]
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        adapter = EthereumAdapter("https://rpc.example.invalid", client=client)
        try:
            result = await adapter.get_erc20_metadata(address)
        finally:
            await client.aclose()

        self.assertEqual(result, {
            "chain": "ethereum",
            "address": address,
            "block_number": 0x1234,
            "token": {"name": "Example Token", "symbol": "EXT", "decimals": 6},
        })
        self.assertEqual([call["method"] for call in calls], [
            "eth_blockNumber", "eth_call", "eth_call", "eth_call",
        ])
        self.assertEqual(calls[1]["params"], [{"to": address, "data": "0x06fdde03"}, "latest"])

    async def test_balance_and_rpc_errors(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            if payload["method"] == "eth_getBalance":
                result = "0xde0b6b3a7640000"
                body = {"jsonrpc": "2.0", "id": payload["id"], "result": result}
            else:
                body = {"jsonrpc": "2.0", "id": payload["id"], "error": {"message": "unavailable"}}
            return httpx.Response(200, json=body)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = EthereumAdapter("https://rpc.example.invalid", client=client)
            self.assertEqual(await adapter.get_balance("0x" + "ab" * 20), 10**18)
            with self.assertRaisesRegex(EthereumRPCError, "unavailable"):
                await adapter.get_block_number()

    async def test_abi_string_decode_rejects_malformed_data(self):
        self.assertEqual(_decode_abi_string(_abi_string("Token 🪙")), "Token 🪙")
        with self.assertRaises(EthereumRPCError):
            _decode_abi_string("0x1234")


if __name__ == "__main__":
    unittest.main()
