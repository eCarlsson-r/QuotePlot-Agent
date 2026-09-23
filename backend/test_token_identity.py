"""Regression tests for canonical CoinGecko token identity mapping."""

import unittest

from backend.seed_data import _update_existing_token_mapping
from backend.utils import _select_coingecko_coin, _token_chain_and_address
from backend.models import TokenMap


class TokenIdentityTests(unittest.TestCase):
    def test_eth_selects_canonical_ethereum_over_same_ticker_collision(self):
        collision = {
            "id": "the-ticker-is-eth",
            "symbol": "eth",
            "platforms": {"solana": "So11111111111111111111111111111111111111112"},
        }
        ethereum = {"id": "ethereum", "symbol": "eth", "platforms": {}}

        for candidates in ([collision, ethereum], [ethereum, collision]):
            with self.subTest(candidate_order=[item["id"] for item in candidates]):
                selected = _select_coingecko_coin("ETH", candidates)
                self.assertIs(selected, ethereum)
                self.assertEqual(_token_chain_and_address("ETH", selected), ("ethereum", None))

    def test_eth_without_canonical_coingecko_entry_never_uses_collision(self):
        collision = {"id": "the-ticker-is-eth", "symbol": "eth", "platforms": {}}
        self.assertIsNone(_select_coingecko_coin("ETH", [collision]))

    def test_other_ticker_selection_keeps_existing_preference(self):
        first = {"id": "wrapped-bitcoin", "symbol": "btc"}
        preferred = {"id": "btc", "symbol": "btc"}
        self.assertIs(_select_coingecko_coin("BTC", [first, preferred]), preferred)

    def test_seeding_repairs_stale_eth_collision_to_native_ethereum(self):
        existing = TokenMap(
            symbol="ETH",
            coingecko_id="the-ticker-is-eth",
            pyth_id="old-feed",
            address="So11111111111111111111111111111111111111112",
            chain="solana",
            is_active=True,
        )

        changed = _update_existing_token_mapping(existing, {
            "symbol": "ETH",
            "coingecko_id": "ethereum",
            "pyth_id": "canonical-eth-feed",
            "address": None,
            "chain": "ethereum",
        })

        self.assertTrue(changed)
        self.assertEqual(existing.coingecko_id, "ethereum")
        self.assertEqual(existing.pyth_id, "canonical-eth-feed")
        self.assertIsNone(existing.address)
        self.assertEqual(existing.chain, "ethereum")

    def test_other_token_rows_do_not_clear_missing_feed_values(self):
        existing = TokenMap(
            symbol="DAI",
            coingecko_id="dai",
            address="0x" + "11" * 20,
            chain="ethereum",
            is_active=True,
        )

        changed = _update_existing_token_mapping(existing, {
            "symbol": "DAI",
            "coingecko_id": "dai",
            "pyth_id": None,
            "address": None,
            "chain": None,
        })

        self.assertFalse(changed)
        self.assertEqual(existing.address, "0x" + "11" * 20)
        self.assertEqual(existing.chain, "ethereum")


if __name__ == "__main__":
    unittest.main()
