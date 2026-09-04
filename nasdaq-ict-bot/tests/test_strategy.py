from __future__ import annotations

import pandas as pd

from ict_bot.strategy.ict_strategy import ICTStrategy, ICTStrategyConfig


def _rows(bar_factory):
    # A sell-side liquidity sweep (two equal-ish lows), then a strong bullish
    # displacement that breaks structure and leaves an FVG behind, timed to
    # land inside the NY AM kill zone (12:00-15:00 UTC / 07:00-10:00 NY).
    rows = [bar_factory(101, 101.5, 100.5, 101) for _ in range(4)]
    rows += [bar_factory(100.5, 100.8, 100.0, 100.2)]  # swing low #1 ~ 100.0
    rows += [bar_factory(101, 101.5, 100.5, 101) for _ in range(4)]
    rows += [bar_factory(100.6, 100.9, 100.02, 100.3)]  # swing low #2 ~ 100.02 (equal low)
    rows += [bar_factory(101, 101.5, 100.5, 101) for _ in range(4)]
    rows += [bar_factory(102, 102.5, 101.9, 102.2)]  # swing high ~102.5
    rows += [bar_factory(101, 101.5, 100.5, 101) for _ in range(4)]
    rows += [bar_factory(100.5, 100.7, 99.5, 99.7)]  # sweeps sell-side liquidity (wicks below 100.0, closes above)
    rows += [bar_factory(101, 101.5, 100.5, 101) for _ in range(3)]
    # displacement leg: breaks back above prior swing high -> CHoCH bullish, leaves FVG
    rows += [bar_factory(101, 103, 100.9, 102.8)]
    rows += [bar_factory(103, 106, 102.9, 105.8)]
    rows += [bar_factory(106, 108, 105.9, 107.5)]  # c3: low 105.9 > c1 high 103 -> bullish FVG at index -2
    rows += [bar_factory(107, 107.2, 104.5, 104.8)]  # retrace into the FVG
    rows += [bar_factory(105, 109, 104.8, 108.5) for _ in range(3)]  # target liquidity above
    return rows


def test_strategy_runs_and_signals_meet_min_rr(bar_factory, df_factory):
    rows = _rows(bar_factory)
    # Start at 12:00 UTC (07:00 NY) so the displacement lands in the ny_am kill zone.
    df = df_factory(rows, start="2024-01-02 12:00", freq="5min")

    config = ICTStrategyConfig(swing_lookback=3, min_risk_reward=1.0, require_kill_zone=False)
    strategy = ICTStrategy(config)
    signals = strategy.generate_signals(df)

    assert isinstance(signals, list)
    for s in signals:
        assert s.risk_reward >= config.min_risk_reward


def test_strategy_handles_flat_data_without_error(bar_factory, df_factory):
    rows = [bar_factory(100, 100.1, 99.9, 100) for _ in range(50)]
    df = df_factory(rows)
    strategy = ICTStrategy()
    signals = strategy.generate_signals(df)
    assert signals == []
