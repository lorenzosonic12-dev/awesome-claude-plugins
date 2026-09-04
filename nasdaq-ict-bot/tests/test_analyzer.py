from __future__ import annotations

import pandas as pd
import pytest

from ict_bot.analysis.analyzer import DealingRange, MarketAnalyzer, SetupState
from ict_bot.core.structure import Direction
from ict_bot.analysis.display import render
from ict_bot.analysis.session import AnalysisSession, AnalysisSessionConfig
from ict_bot.strategy.ict_strategy import ICTStrategy, ICTStrategyConfig


from tests.conftest import FULL_SETUP_SIGNAL_BAR


def test_analyze_returns_a_populated_snapshot(full_setup):
    snap = MarketAnalyzer().analyze(full_setup)

    assert snap.bars == len(full_setup)
    assert snap.last_price == pytest.approx(full_setup["close"].iloc[-1])
    assert snap.timestamp == full_setup.index[-1]
    assert len(snap.gates) == 4
    assert isinstance(snap.setup_state, SetupState)
    assert 0 <= snap.gates_passed <= 4


def test_sweep_is_detected_as_the_first_gate(full_setup):
    # truncate to just after the sweep, before structure has flipped
    snap = MarketAnalyzer().analyze(full_setup.iloc[:42])

    passed, detail = snap.gates[0]
    assert passed is True
    assert "sell-side sweep" in detail
    assert snap.setup_state == SetupState.LIQUIDITY_SWEPT


def test_setup_walks_every_state_in_order(full_setup):
    """The whole point of live analysis: the read has to advance through the
    model's stages as bars arrive, not flip straight from idle to a signal."""
    analyzer = MarketAnalyzer()
    seen: list[SetupState] = []
    for i in range(30, len(full_setup) + 1):
        state = analyzer.analyze(full_setup.iloc[:i]).setup_state
        if not seen or seen[-1] != state:
            seen.append(state)

    assert SetupState.IDLE in seen
    assert SetupState.LIQUIDITY_SWEPT in seen
    assert SetupState.CHOCH_CONFIRMED in seen
    assert SetupState.AWAITING_RETRACE in seen
    assert SetupState.SIGNAL_READY in seen
    # and they arrive in that order
    order = [seen.index(s) for s in (
        SetupState.IDLE, SetupState.LIQUIDITY_SWEPT,
        SetupState.CHOCH_CONFIRMED, SetupState.AWAITING_RETRACE,
        SetupState.SIGNAL_READY,
    )]
    assert order == sorted(order)


def test_signal_fires_on_the_expected_bar_with_all_gates_passed(full_setup):
    analyzer = MarketAnalyzer()
    snap = analyzer.analyze(full_setup.iloc[: FULL_SETUP_SIGNAL_BAR + 1])

    assert snap.setup_state == SetupState.SIGNAL_READY
    assert snap.gates_passed == 4
    assert snap.signal is not None
    assert snap.signal.direction == Direction.BULLISH
    assert snap.signal.risk_reward >= 2.0
    # target is the buy-side pool left by the opening rally
    assert snap.signal.target == pytest.approx(106.01, abs=0.02)
    assert snap.signal.entry == pytest.approx(101.2, abs=0.02)


def test_flat_market_is_idle(bar_factory, df_factory):
    rows = [bar_factory(100, 100.1, 99.9, 100) for _ in range(60)]
    df = df_factory(rows)
    snap = MarketAnalyzer().analyze(df)

    assert snap.setup_state == SetupState.IDLE
    assert snap.gates_passed == 0
    assert snap.signal is None


def test_empty_frame_is_rejected():
    with pytest.raises(ValueError):
        MarketAnalyzer().analyze(pd.DataFrame())


def test_kill_zone_gate_blocks_outside_configured_windows(df_factory):
    from tests.conftest import full_setup_rows
    # 02:00 UTC is 21:00 the previous day in New York -- no configured zone
    df = df_factory(full_setup_rows(), start="2024-01-03 02:00")
    analyzer = MarketAnalyzer(ICTStrategy(ICTStrategyConfig(require_kill_zone=True)))
    snap = analyzer.analyze(df)

    assert snap.tradeable_zone is False
    assert snap.signal is None
    assert "outside configured kill zones" in snap.gates[3][1]


def test_dealing_range_positions_price():
    assert DealingRange(high=110, low=100, price=102).zone == "discount"
    assert DealingRange(high=110, low=100, price=108).zone == "premium"
    assert DealingRange(high=110, low=100, price=105).zone == "equilibrium"
    assert DealingRange(high=110, low=100, price=105).position == pytest.approx(0.5)
    # clamped, and a degenerate range doesn't divide by zero
    assert DealingRange(high=110, low=100, price=999).position == 1.0
    assert DealingRange(high=100, low=100, price=100).position == 0.5


def test_dealing_range_reports_breakouts_rather_than_pinning_at_100pct():
    above = DealingRange(high=110, low=100, price=115)
    below = DealingRange(high=110, low=100, price=95)
    inside = DealingRange(high=110, low=100, price=104)

    assert above.outside is True and above.zone == "above range"
    assert below.outside is True and below.zone == "below range"
    assert inside.outside is False and inside.zone == "discount"


def test_analysis_matches_the_strategy_it_wraps(full_setup):
    """The analyzer must not drift from the strategy: if it reports a signal,
    the strategy has to agree one fires on that bar."""
    df = full_setup
    strategy = ICTStrategy(ICTStrategyConfig(require_kill_zone=False, min_risk_reward=1.0))
    snap = MarketAnalyzer(strategy).analyze(df)

    signals = strategy.generate_signals(df)
    fires_on_last = bool(signals) and signals[-1].index == df.index[-1]
    assert (snap.signal is not None) == fires_on_last


def test_build_context_is_reused_not_recomputed(full_setup):
    """generate_signals must accept a prebuilt context and produce the same
    answer as computing one itself."""
    df = full_setup
    strategy = ICTStrategy(ICTStrategyConfig(require_kill_zone=False, min_risk_reward=1.0))

    ctx = strategy.build_context(df)
    with_ctx = strategy.generate_signals(df, context=ctx)
    without = strategy.generate_signals(df)

    assert [s.index for s in with_ctx] == [s.index for s in without]
    assert [s.entry for s in with_ctx] == [s.entry for s in without]


# --- session ---------------------------------------------------------------


def test_session_warms_up_before_reporting(bar_factory, df_factory):
    session = AnalysisSession(
        MarketAnalyzer(), config=AnalysisSessionConfig(min_bars=30)
    )
    df = df_factory([bar_factory(100, 100.1, 99.9, 100) for _ in range(10)])
    snapshots = session.replay(df)

    assert snapshots == []
    assert session.last_snapshot is None


def test_session_replay_emits_one_snapshot_per_bar_after_warmup(full_setup):
    df = full_setup
    session = AnalysisSession(
        MarketAnalyzer(ICTStrategy(ICTStrategyConfig(require_kill_zone=False))),
        config=AnalysisSessionConfig(min_bars=20),
    )
    snapshots = session.replay(df)

    assert len(snapshots) == len(df) - 20 + 1
    assert session.last_snapshot is not None
    assert session.last_snapshot.timestamp == df.index[-1]


def test_session_notifies_the_callback(full_setup):
    seen = []
    session = AnalysisSession(
        MarketAnalyzer(ICTStrategy(ICTStrategyConfig(require_kill_zone=False))),
        config=AnalysisSessionConfig(min_bars=20),
        on_snapshot=seen.append,
    )
    session.replay(full_setup)
    assert len(seen) > 0
    assert seen[-1] is session.last_snapshot


# --- display ---------------------------------------------------------------


def test_render_produces_a_bounded_panel(full_setup):
    snap = MarketAnalyzer().analyze(full_setup)

    plain = render(snap, color=False)
    body = [ln for ln in plain.splitlines() if ln.startswith(("│", "┌", "├", "└"))]

    assert body, "panel produced no framed rows"
    widths = {len(ln) for ln in body}
    assert len(widths) == 1, f"ragged panel edges: {sorted(widths)}"

    assert snap.symbol in plain
    assert f"{snap.last_price:.2f}" in plain
    assert "read-only, no orders placed" in plain


def test_render_with_color_stays_aligned(full_setup):
    """ANSI codes must not be counted when padding rows."""
    snap = MarketAnalyzer().analyze(full_setup)

    colored = render(snap, color=True)
    assert "\x1b[" in colored

    import re

    stripped = re.sub(r"\x1b\[[0-9;]*m", "", colored)
    body = [ln for ln in stripped.splitlines() if ln.startswith(("│", "┌", "├", "└"))]
    assert len({len(ln) for ln in body}) == 1
