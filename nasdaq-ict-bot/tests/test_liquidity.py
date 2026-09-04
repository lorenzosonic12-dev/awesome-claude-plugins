from __future__ import annotations

from ict_bot.core.liquidity import detect_liquidity_pools, detect_sweeps
from ict_bot.core.structure import SwingPoint


def test_detect_liquidity_pool_groups_equal_highs(df_factory, bar_factory):
    rows = [bar_factory(1, 1, 1, 1) for _ in range(2)]
    df = df_factory(rows)
    swings = [
        SwingPoint(df.index[0], 100.0, "high"),
        SwingPoint(df.index[1], 100.02, "high"),  # within 0.05% tolerance
    ]
    pools = detect_liquidity_pools(swings, tolerance_pct=0.05)
    assert len(pools) == 1
    assert pools[0].side == "buy"


def test_detect_sweep_marks_pool_swept(bar_factory, df_factory):
    rows = [
        bar_factory(99, 100.0, 98, 99.5),
        bar_factory(99.5, 100.02, 98.5, 99.8),
        bar_factory(99.8, 100.5, 99.0, 99.2),  # wicks above pool (~100.0) then closes back below
    ]
    df = df_factory(rows)
    swings = [
        SwingPoint(df.index[0], 100.0, "high"),
        SwingPoint(df.index[1], 100.02, "high"),
    ]
    pools = detect_liquidity_pools(swings, tolerance_pct=0.05)
    sweeps = detect_sweeps(df, pools)

    assert len(sweeps) == 1
    assert pools[0].swept is True
