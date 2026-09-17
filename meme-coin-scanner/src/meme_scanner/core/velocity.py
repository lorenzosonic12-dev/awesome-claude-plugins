"""Liquidity-velocity detection: how fast a pair's on-chain liquidity is moving.

Rapid liquidity *inflow* often precedes a pump (fresh capital locking in);
rapid *outflow* is the signature of a liquidity pull / rug in progress.
Both require two snapshots of the same pair taken minutes apart -- a
single DexScreener response has no history.
"""
from __future__ import annotations

from dataclasses import dataclass

from meme_scanner.core.models import TokenPair


@dataclass
class LiquiditySnapshot:
    liquidity_usd: float
    timestamp: float  # unix seconds


@dataclass
class VelocityResult:
    pair: TokenPair
    prev_liquidity_usd: float
    curr_liquidity_usd: float
    elapsed_minutes: float
    delta_usd: float
    delta_pct: float
    usd_per_minute: float
    direction: str  # "inflow" | "outflow" | "flat"
    is_rapid: bool


def key_for(pair: TokenPair) -> str:
    return f"{pair.chain_id}:{pair.pair_address}"


def snapshot_map(pairs: list[TokenPair], timestamp: float) -> dict[str, LiquiditySnapshot]:
    return {key_for(p): LiquiditySnapshot(liquidity_usd=p.liquidity_usd, timestamp=timestamp) for p in pairs}


def compute_velocity(
    pair: TokenPair,
    previous: LiquiditySnapshot,
    now_ts: float,
    rapid_pct_per_min: float = 1.5,
    min_elapsed_minutes: float = 0.5,
) -> VelocityResult | None:
    """Compare `pair`'s current liquidity to a `previous` snapshot.

    Returns None when the two readings are too close together in time to
    give a meaningful rate (avoids divide-by-near-zero noise).
    """
    elapsed_minutes = (now_ts - previous.timestamp) / 60
    if elapsed_minutes < min_elapsed_minutes:
        return None

    delta_usd = pair.liquidity_usd - previous.liquidity_usd
    delta_pct = (delta_usd / previous.liquidity_usd * 100) if previous.liquidity_usd > 0 else 0.0
    usd_per_minute = delta_usd / elapsed_minutes
    pct_per_min = abs(delta_pct) / elapsed_minutes

    direction = "inflow" if delta_usd > 0 else "outflow" if delta_usd < 0 else "flat"
    is_rapid = direction != "flat" and pct_per_min >= rapid_pct_per_min

    return VelocityResult(
        pair=pair,
        prev_liquidity_usd=previous.liquidity_usd,
        curr_liquidity_usd=pair.liquidity_usd,
        elapsed_minutes=round(elapsed_minutes, 2),
        delta_usd=round(delta_usd, 2),
        delta_pct=round(delta_pct, 2),
        usd_per_minute=round(usd_per_minute, 2),
        direction=direction,
        is_rapid=is_rapid,
    )


def compute_all_velocities(
    pairs: list[TokenPair],
    previous_snapshots: dict[str, LiquiditySnapshot],
    now_ts: float,
    rapid_pct_per_min: float = 1.5,
) -> list[VelocityResult]:
    results = []
    for pair in pairs:
        previous = previous_snapshots.get(key_for(pair))
        if previous is None:
            continue  # no baseline for this pair yet -- can't measure a rate
        result = compute_velocity(pair, previous, now_ts, rapid_pct_per_min=rapid_pct_per_min)
        if result is not None:
            results.append(result)
    return results
