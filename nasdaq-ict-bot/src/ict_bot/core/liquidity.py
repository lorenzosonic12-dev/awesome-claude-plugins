"""Liquidity pool (equal highs / equal lows) detection and sweep events.

ICT treats clusters of resting stops above equal highs (buy-side liquidity)
or below equal lows (sell-side liquidity) as magnets price is drawn to
before reversing -- the classic "stop hunt" / "liquidity grab".
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ict_bot.core.structure import SwingPoint


@dataclass
class LiquidityPool:
    price: float
    side: str  # "buy" (resting above equal highs) or "sell" (below equal lows)
    swing_indices: list[pd.Timestamp]
    swept: bool = False
    swept_at: pd.Timestamp | None = None


@dataclass
class LiquiditySweep:
    index: pd.Timestamp
    pool: LiquidityPool
    price: float


def detect_liquidity_pools(swings: list[SwingPoint], tolerance_pct: float = 0.05) -> list[LiquidityPool]:
    """Group swing highs/lows sitting within `tolerance_pct` percent of one
    another into resting liquidity pools."""
    pools: list[LiquidityPool] = []

    def _group(points: list[SwingPoint], side: str) -> None:
        used: set[int] = set()
        for i, p in enumerate(points):
            if i in used:
                continue
            cluster = [p]
            used.add(i)
            for j in range(i + 1, len(points)):
                if j in used:
                    continue
                q = points[j]
                if abs(q.price - p.price) / p.price * 100 <= tolerance_pct:
                    cluster.append(q)
                    used.add(j)
            if len(cluster) >= 2:
                avg_price = sum(c.price for c in cluster) / len(cluster)
                pools.append(LiquidityPool(avg_price, side, [c.index for c in cluster]))

    _group([s for s in swings if s.kind == "high"], "buy")
    _group([s for s in swings if s.kind == "low"], "sell")
    return pools


def detect_sweeps(df: pd.DataFrame, pools: list[LiquidityPool]) -> list[LiquiditySweep]:
    """A sweep is a wick through a pool that closes back on the other side."""
    sweeps: list[LiquiditySweep] = []

    for pool in pools:
        if pool.swept:
            continue
        start = max(pool.swing_indices)
        future = df.loc[df.index > start]
        for ts, row in future.iterrows():
            if pool.side == "buy" and row["high"] > pool.price and row["close"] < pool.price:
                pool.swept = True
                pool.swept_at = ts
                sweeps.append(LiquiditySweep(ts, pool, float(row["high"])))
                break
            if pool.side == "sell" and row["low"] < pool.price and row["close"] > pool.price:
                pool.swept = True
                pool.swept_at = ts
                sweeps.append(LiquiditySweep(ts, pool, float(row["low"])))
                break

    return sweeps
