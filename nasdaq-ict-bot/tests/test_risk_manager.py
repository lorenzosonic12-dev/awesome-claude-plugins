from __future__ import annotations

from ict_bot.risk.risk_manager import RiskConfig, RiskManager


def test_size_position_scales_with_risk_pct():
    rm = RiskManager(RiskConfig(risk_per_trade_pct=1.0))
    sized = rm.size_position(equity=100_000, entry=100, stop=98)
    assert sized.risk_amount == 1_000
    assert sized.quantity == 500  # 1000 / 2


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
