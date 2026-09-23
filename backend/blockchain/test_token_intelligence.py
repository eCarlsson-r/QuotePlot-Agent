"""Tests for resolving TokenMap entries into Ethereum metadata reads."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.blockchain.token_intelligence import (
    TokenOnChainLookupError,
    get_token_on_chain_intelligence,
)
from backend.models import TokenMap


class FakeEthereumAdapter:
    def __init__(self):
        self.addresses = []
        self.closed = False

    async def get_erc20_metadata(self, address):
        self.addresses.append(address)
        return {
            "chain": "ethereum",
            "address": address,
            "block_number": 20_000_000,
            "token": {"name": "Dai Stablecoin", "symbol": "DAI", "decimals": 18},
        }

    async def close(self):
        self.closed = True


class TokenIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        TokenMap.__table__.create(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    async def test_resolves_active_erc20_mapping_to_structured_metadata(self):
        dai_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
        self.db.add(TokenMap(
            symbol="DAI",
            coingecko_id="dai",
            pyth_id="pyth-dai-id",
            address=dai_address,
            chain="ethereum",
            is_active=True,
        ))
        self.db.commit()
        adapter = FakeEthereumAdapter()

        result = await get_token_on_chain_intelligence(self.db, " dai ", adapter=adapter)

        self.assertEqual(adapter.addresses, [dai_address])
        self.assertFalse(adapter.closed)  # injected adapters remain caller-owned
        self.assertEqual(result, {
            "symbol": "DAI",
            "coingecko_id": "dai",
            "pyth_id": "pyth-dai-id",
            "chain": "ethereum",
            "address": dai_address,
            "block_number": 20_000_000,
            "token": {"name": "Dai Stablecoin", "symbol": "DAI", "decimals": 18},
        })

    async def test_native_eth_without_contract_address_is_reported_explicitly(self):
        self.db.add(TokenMap(
            symbol="ETH",
            coingecko_id="ethereum",
            pyth_id="pyth-eth-id",
            address=None,
            chain="ethereum",
            is_active=True,
        ))
        self.db.commit()

        with self.assertRaises(TokenOnChainLookupError) as caught:
            await get_token_on_chain_intelligence(self.db, "ETH", adapter=FakeEthereumAdapter())

        self.assertEqual(caught.exception.code, "missing_contract_address")
        self.assertIn("ETH is native", str(caught.exception))
        self.assertIn("no ERC-20 contract address", str(caught.exception))

    async def test_eth_mapping_to_another_chain_is_rejected_without_rpc(self):
        self.db.add(TokenMap(
            symbol="ETH",
            coingecko_id="ticker-eth",
            address="So11111111111111111111111111111111111111112",
            chain="solana",
            is_active=True,
        ))
        self.db.commit()
        adapter = FakeEthereumAdapter()

        with self.assertRaises(TokenOnChainLookupError) as caught:
            await get_token_on_chain_intelligence(self.db, "ETH", adapter=adapter)

        self.assertEqual(caught.exception.code, "unsupported_chain")
        self.assertIn("on solana", str(caught.exception))
        self.assertEqual(adapter.addresses, [])

    async def test_rejects_non_ethereum_mapping_before_rpc(self):
        self.db.add(TokenMap(
            symbol="SOL",
            coingecko_id="solana",
            address="So11111111111111111111111111111111111111112",
            chain="solana",
            is_active=True,
        ))
        self.db.commit()
        adapter = FakeEthereumAdapter()

        with self.assertRaises(TokenOnChainLookupError) as caught:
            await get_token_on_chain_intelligence(self.db, "SOL", adapter=adapter)

        self.assertEqual(caught.exception.code, "unsupported_chain")
        self.assertEqual(adapter.addresses, [])

    async def test_rejects_missing_and_inactive_token_entries(self):
        self.db.add(TokenMap(
            symbol="OLD",
            address="0x" + "11" * 20,
            chain="ethereum",
            is_active=False,
        ))
        self.db.commit()

        for symbol, expected_code in (("UNKNOWN", "token_not_found"), ("OLD", "token_inactive")):
            with self.subTest(symbol=symbol):
                with self.assertRaises(TokenOnChainLookupError) as caught:
                    await get_token_on_chain_intelligence(self.db, symbol, adapter=FakeEthereumAdapter())
                self.assertEqual(caught.exception.code, expected_code)


if __name__ == "__main__":
    unittest.main()
