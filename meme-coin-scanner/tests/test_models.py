from __future__ import annotations

from meme_scanner.core.models import TokenPair, Txns


def test_from_dexscreener_parses_core_fields(raw_pair_factory):
    pair = TokenPair.from_dexscreener(raw_pair_factory())
    assert pair.chain_id == "solana"
    assert pair.base_symbol == "DOGEK"
    assert pair.liquidity_usd == 50000
    assert pair.volume_h24 == 120000
    assert pair.txns_h1.buys == 40
    assert pair.txns_h1.sells == 20


def test_age_hours_uses_pair_created_at(raw_pair_factory):
    pair = TokenPair.from_dexscreener(raw_pair_factory())
    assert 5.9 < pair.age_hours < 6.1


def test_age_hours_infinite_when_missing():
    pair = TokenPair.from_dexscreener({"baseToken": {}, "quoteToken": {}})
    assert pair.age_hours == float("inf")


def test_buy_ratio_handles_zero_txns():
    assert Txns(0, 0).buy_ratio == 0.5
    assert Txns(3, 1).buy_ratio == 0.75
