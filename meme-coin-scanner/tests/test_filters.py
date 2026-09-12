from __future__ import annotations

from meme_scanner.core.filters import ScanFilters, apply_filters
from meme_scanner.core.models import TokenPair


def test_matches_respects_chain_allowlist(sample_pair):
    assert ScanFilters(chains=["solana"]).matches(sample_pair)
    assert not ScanFilters(chains=["ethereum"]).matches(sample_pair)


def test_matches_respects_liquidity_and_volume_floors(sample_pair):
    assert ScanFilters(min_liquidity_usd=1000, min_volume_h24_usd=1000).matches(sample_pair)
    assert not ScanFilters(min_liquidity_usd=1_000_000).matches(sample_pair)
    assert not ScanFilters(min_volume_h24_usd=1_000_000).matches(sample_pair)


def test_matches_respects_max_age(sample_pair):
    assert ScanFilters(max_age_hours=24).matches(sample_pair)
    assert not ScanFilters(max_age_hours=1).matches(sample_pair)


def test_matches_respects_min_txns(sample_pair):
    assert ScanFilters(min_txns_h1=10).matches(sample_pair)
    assert not ScanFilters(min_txns_h1=1000).matches(sample_pair)


def test_apply_filters_filters_list(sample_pair, raw_pair_factory):
    other = TokenPair.from_dexscreener(raw_pair_factory(chainId="ethereum"))
    results = apply_filters([sample_pair, other], ScanFilters(chains=["solana"]))
    assert results == [sample_pair]
