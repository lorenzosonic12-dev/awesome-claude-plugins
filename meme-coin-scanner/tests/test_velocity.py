from __future__ import annotations

from meme_scanner.core.velocity import (
    LiquiditySnapshot,
    compute_all_velocities,
    compute_velocity,
    key_for,
    snapshot_map,
)


def test_compute_velocity_detects_inflow(sample_pair):
    previous = LiquiditySnapshot(liquidity_usd=40000, timestamp=1000.0)
    sample_pair.liquidity_usd = 50000  # +25% since baseline
    result = compute_velocity(sample_pair, previous, now_ts=1000.0 + 60, rapid_pct_per_min=1.0)
    assert result is not None
    assert result.direction == "inflow"
    assert result.delta_usd == 10000
    assert result.delta_pct == 25.0
    assert result.is_rapid is True


def test_compute_velocity_detects_outflow(sample_pair):
    previous = LiquiditySnapshot(liquidity_usd=50000, timestamp=1000.0)
    sample_pair.liquidity_usd = 20000  # a 60% drain -- classic rug signature
    result = compute_velocity(sample_pair, previous, now_ts=1000.0 + 120, rapid_pct_per_min=1.0)
    assert result is not None
    assert result.direction == "outflow"
    assert result.delta_pct == -60.0
    assert result.is_rapid is True


def test_compute_velocity_not_rapid_below_threshold(sample_pair):
    previous = LiquiditySnapshot(liquidity_usd=50000, timestamp=1000.0)
    sample_pair.liquidity_usd = 50100  # +0.2% over a minute
    result = compute_velocity(sample_pair, previous, now_ts=1000.0 + 60, rapid_pct_per_min=1.5)
    assert result is not None
    assert result.direction == "inflow"
    assert result.is_rapid is False


def test_compute_velocity_flat_is_never_rapid(sample_pair):
    previous = LiquiditySnapshot(liquidity_usd=sample_pair.liquidity_usd, timestamp=1000.0)
    result = compute_velocity(sample_pair, previous, now_ts=1000.0 + 60, rapid_pct_per_min=0.0)
    assert result is not None
    assert result.direction == "flat"
    assert result.is_rapid is False


def test_compute_velocity_returns_none_when_too_close_in_time(sample_pair):
    previous = LiquiditySnapshot(liquidity_usd=1000, timestamp=1000.0)
    sample_pair.liquidity_usd = 5000
    result = compute_velocity(sample_pair, previous, now_ts=1000.5, min_elapsed_minutes=0.5)
    assert result is None


def test_key_for_combines_chain_and_pair_address(sample_pair):
    assert key_for(sample_pair) == f"{sample_pair.chain_id}:{sample_pair.pair_address}"


def test_snapshot_map_indexes_by_key(sample_pair):
    snapshots = snapshot_map([sample_pair], timestamp=42.0)
    assert snapshots[key_for(sample_pair)].liquidity_usd == sample_pair.liquidity_usd
    assert snapshots[key_for(sample_pair)].timestamp == 42.0


def test_compute_all_velocities_skips_pairs_without_baseline(sample_pair, raw_pair_factory):
    from meme_scanner.core.models import TokenPair

    unseen = TokenPair.from_dexscreener(raw_pair_factory(pairAddress="UNSEEN"))
    baseline = snapshot_map([sample_pair], timestamp=1000.0)

    results = compute_all_velocities([sample_pair, unseen], baseline, now_ts=1000.0 + 60)

    assert len(results) == 1
    assert results[0].pair.pair_address == sample_pair.pair_address
