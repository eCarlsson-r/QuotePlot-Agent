"""Small, read-only Ethereum JSON-RPC adapter."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

_ERC20_SELECTORS = {
    "name": "06fdde03",
    "symbol": "95d89b41",
    "decimals": "313ce567",
}


class EthereumRPCError(RuntimeError):
    """Raised when an Ethereum RPC request or response is invalid."""


def _decode_abi_string(value: str) -> str:
    """Decode a standard ABI string, with support for legacy bytes32 values."""
    if not isinstance(value, str) or not value.startswith("0x"):
        raise EthereumRPCError("eth_call returned a malformed hex value")
    try:
        data = bytes.fromhex(value[2:])
    except ValueError as exc:
        raise EthereumRPCError("eth_call returned invalid hex data") from exc

    # A few older ERC-20 contracts expose name/symbol as bytes32.
    if len(data) == 32:
        return data.rstrip(b"\0").decode("utf-8")
    if len(data) < 64 or len(data) % 32:
        raise EthereumRPCError("eth_call returned invalid ABI string data")

    offset = int.from_bytes(data[:32], "big")
    if offset + 32 > len(data):
        raise EthereumRPCError("ABI string offset is out of bounds")
    length = int.from_bytes(data[offset : offset + 32], "big")
    start = offset + 32
    end = start + length
    if end > len(data):
        raise EthereumRPCError("ABI string length is out of bounds")
    try:
        return data[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EthereumRPCError("ABI string is not valid UTF-8") from exc


def _decode_uint(value: str, bits: int = 256) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise EthereumRPCError("eth_call returned a malformed integer")
    try:
        data = bytes.fromhex(value[2:])
    except ValueError as exc:
        raise EthereumRPCError("eth_call returned invalid integer data") from exc
    if len(data) != 32:
        raise EthereumRPCError("eth_call returned an invalid ABI integer")
    result = int.from_bytes(data, "big")
    if result >= 1 << bits:
        raise EthereumRPCError("ABI integer is outside the expected range")
    return result


class EthereumAdapter:
    """Read-only access to a configured Ethereum JSON-RPC endpoint."""

    def __init__(
        self,
        rpc_url: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.rpc_url = rpc_url or os.getenv("ETH_RPC_URL")
        if not self.rpc_url:
            raise ValueError("ETH_RPC_URL is required for Ethereum RPC access")
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout
        self._request_id = 0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        self._request_id += 1
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        try:
            response = await (await self._get_client()).post(self.rpc_url, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise EthereumRPCError(f"Ethereum RPC transport failed for {method}") from exc
        except ValueError as exc:
            raise EthereumRPCError("Ethereum RPC returned invalid JSON") from exc

        if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
            raise EthereumRPCError("Ethereum RPC returned an invalid JSON-RPC response")
        if body.get("error"):
            error = body["error"]
            message = error.get("message", "unknown RPC error") if isinstance(error, dict) else "unknown RPC error"
            raise EthereumRPCError(f"Ethereum RPC {method} failed: {message}")
        if "result" not in body:
            raise EthereumRPCError("Ethereum RPC response is missing result")
        return body["result"]

    async def get_block_number(self) -> int:
        result = await self._rpc("eth_blockNumber", [])
        if not isinstance(result, str) or not result.startswith("0x"):
            raise EthereumRPCError("eth_blockNumber returned an invalid result")
        try:
            return int(result, 16)
        except ValueError as exc:
            raise EthereumRPCError("eth_blockNumber returned invalid hex") from exc

    async def get_balance(self, address: str, block: str = "latest") -> int:
        _validate_address(address)
        result = await self._rpc("eth_getBalance", [address, block])
        if not isinstance(result, str) or not result.startswith("0x"):
            raise EthereumRPCError("eth_getBalance returned an invalid result")
        try:
            return int(result, 16)
        except ValueError as exc:
            raise EthereumRPCError("eth_getBalance returned invalid hex") from exc

    async def eth_call(self, address: str, data: str, block: str = "latest") -> str:
        _validate_address(address)
        result = await self._rpc("eth_call", [{"to": address, "data": data}, block])
        if not isinstance(result, str):
            raise EthereumRPCError("eth_call returned an invalid result")
        return result

    async def get_erc20_metadata(self, address: str) -> dict[str, Any]:
        """Return block height and standard ERC-20 name, symbol, and decimals."""
        _validate_address(address)
        block_number = await self.get_block_number()
        name_data = await self.eth_call(address, "0x" + _ERC20_SELECTORS["name"])
        symbol_data = await self.eth_call(address, "0x" + _ERC20_SELECTORS["symbol"])
        decimals_data = await self.eth_call(address, "0x" + _ERC20_SELECTORS["decimals"])
        return {
            "chain": "ethereum",
            "address": address,
            "block_number": block_number,
            "token": {
                "name": _decode_abi_string(name_data),
                "symbol": _decode_abi_string(symbol_data),
                "decimals": _decode_uint(decimals_data, bits=8),
            },
        }


def _validate_address(address: str) -> None:
    if not isinstance(address, str) or len(address) != 42 or not address.startswith("0x"):
        raise ValueError("Ethereum address must be a 20-byte 0x-prefixed hex string")
    try:
        bytes.fromhex(address[2:])
    except ValueError as exc:
        raise ValueError("Ethereum address must be a 20-byte 0x-prefixed hex string") from exc


async def get_erc20_metadata(address: str) -> dict[str, Any]:
    """Convenience entry point for one-off metadata reads."""
    adapter = EthereumAdapter()
    try:
        return await adapter.get_erc20_metadata(address)
    finally:
        await adapter.close()
