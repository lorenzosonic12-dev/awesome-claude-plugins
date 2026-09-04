from __future__ import annotations

import pytest

from ict_bot.risk.risk_manager import RiskConfig, RiskManager


def test_size_position_scales_with_risk_pct():
    rm = RiskManager(RiskConfig(risk_per_trade_pct=1.0))
    sized = rm.size_position(equity=100_000, entry=100, stop=98)
    assert sized.risk_amount == 1_000
    assert sized.quantity == 500  # 1000 / 2


def test_size_position_caps_notional_at_equity():
    # A $1.91 stop on a $511 instrument would otherwise buy 261 shares --
    # $133k of stock against a $100k account.
    rm = RiskManager(RiskConfig(risk_per_trade_pct=0.5, max_position_notional_pct=100.0))
    sized = rm.size_position(equity=100_000, entry=511.20, stop=509.29)

    assert sized.quantity * 511.20 <= 100_000 + 1e-6
    assert sized.quantity == pytest.approx(100_000 / 511.20, rel=1e-9)
    # risk_amount reports what's actually at stake after the cap, not the budget
    assert sized.risk_amount == pytest.approx(sized.quantity * (511.20 - 509.29), rel=1e-9)
    assert sized.risk_amount < 500


def test_size_position_zero_stop_distance_is_flat():
    rm = RiskManager()
    sized = rm.size_position(equity=100_000, entry=100, stop=100)
    assert sized.quantity == 0.0
    assert sized.risk_amount == 0.0


def test_sync_open_positions_unlatches_can_trade():
    # Regression: the live loop has no fill callbacks, so without syncing the
    # counter only ever increments and blocks every trade after the first.
    rm = RiskManager(RiskConfig(max_open_positions=1, max_trades_per_day=5))
    rm.register_trade_open()
    assert rm.can_trade() is False

    rm.sync_open_positions(0)  # broker reports the position has closed
    assert rm.can_trade() is True


def test_can_trade_respects_caps():
    rm = RiskManager(RiskConfig(max_open_positions=1, max_trades_per_day=1))
    assert rm.can_trade() is True
    rm.register_trade_open()
    assert rm.can_trade() is False


def test_daily_loss_limit():
    rm = RiskManager(RiskConfig(max_daily_loss_pct=1.0))
    rm.register_trade_open()
    rm.register_trade_close(pnl=-1500)
    assert rm.is_daily_loss_limit_hit(equity=100_000) is True


def test_reset_day_clears_counters():
    rm = RiskManager(RiskConfig(max_trades_per_day=1))
    rm.register_trade_open()
    rm.register_trade_close(pnl=-100)
    assert rm.can_trade() is False
    rm.reset_day()
    assert rm.can_trade() is True
