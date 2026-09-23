"""Resolve a TokenMap identity to read-only Ethereum contract metadata."""

from __future__ import annotations

from backend.blockchain.ethereum import EthereumAdapter
from backend.models import TokenMap


class TokenOnChainLookupError(ValueError):
    """A TokenMap row cannot be used for an Ethereum contract read."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


async def get_token_on_chain_intelligence(
    db,
    symbol: str,
    *,
    adapter: EthereumAdapter | None = None,
) -> dict:
    """Resolve an active TokenMap symbol and return its Ethereum ERC-20 data.

    An adapter may be injected by callers that manage its lifecycle. When
    omitted, this function creates and closes a short-lived adapter.
    """
    normalized_symbol = symbol.strip().upper() if isinstance(symbol, str) else ""
    if not normalized_symbol:
        raise TokenOnChainLookupError("invalid_symbol", "A token symbol is required.")

    mapping = (
        db.query(TokenMap)
        .filter(TokenMap.symbol == normalized_symbol)
        .first()
    )
    if mapping is None:
        raise TokenOnChainLookupError(
            "token_not_found", f"No TokenMap entry exists for {normalized_symbol}."
        )
    if not mapping.is_active:
        raise TokenOnChainLookupError(
            "token_inactive", f"TokenMap entry {normalized_symbol} is inactive."
        )

    chain = (mapping.chain or "").strip().lower()
    if chain and chain != "ethereum":
        raise TokenOnChainLookupError(
            "unsupported_chain",
            f"TokenMap entry {normalized_symbol} is on {chain}, not Ethereum.",
        )

    address = (mapping.address or "").strip()
    if not address:
        if normalized_symbol == "ETH":
            message = "ETH is native on Ethereum and has no ERC-20 contract address in TokenMap."
        else:
            message = f"TokenMap entry {normalized_symbol} has no contract address."
        raise TokenOnChainLookupError("missing_contract_address", message)

    if not chain:
        raise TokenOnChainLookupError(
            "unsupported_chain",
            f"TokenMap entry {normalized_symbol} has no chain mapping, so Ethereum cannot be verified.",
        )

    owned_adapter = adapter is None
    rpc = adapter or EthereumAdapter()
    try:
        on_chain = await rpc.get_erc20_metadata(address)
    finally:
        if owned_adapter:
            await rpc.close()

    return {
        "symbol": normalized_symbol,
        "coingecko_id": mapping.coingecko_id,
        "pyth_id": mapping.pyth_id,
        "chain": on_chain["chain"],
        "address": on_chain["address"],
        "block_number": on_chain["block_number"],
        "token": on_chain["token"],
    }
