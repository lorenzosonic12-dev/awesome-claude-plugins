from __future__ import annotations

import pandas as pd

from ict_bot.broker.base import Broker, OrderResult
from ict_bot.core.structure import Direction
from ict_bot.live import runner as runner_module
from ict_bot.live.runner import LiveRunner, LiveRunnerConfig
from ict_bot.risk.risk_manager import RiskConfig, RiskManager
from ict_bot.strategy.ict_strategy import ICTStrategy


class StubBroker(Broker):
    """Broker whose open-position count the test drives directly."""

    def __init__(self, open_positions: int = 0) -> None:
        self.open_positions = open_positions
        self.submitted: list[dict] = []

    def get_equity(self) -> float:
        return 100_000.0

    def get_open_position_count(self, symbol: str) -> int:
        return self.open_positions

    def submit_bracket_order(self, symbol, direction, quantity, entry, stop, target) -> OrderResult:
        self.submitted.append({"symbol": symbol, "quantity": quantity})
        return OrderResult(order_id="stub", status="accepted")


def _flat_frame(bars: int = 40, start: str = "2024-01-02 14:30") -> pd.DataFrame:
    idx = pd.date_range(start, periods=bars, freq="5min", tz="UTC")
    rows = [{"open": 100, "high": 100.1, "low": 99.9, "close": 100, "volume": 1000} for _ in range(bars)]
    return pd.DataFrame(rows, index=idx)


def test_poll_reconciles_position_count_with_broker(monkeypatch):
    """Regression: the counter used to only ever increment, so `can_trade`
    latched off permanently after the first live trade."""
    monkeypatch.setattr(runner_module, "fetch_ohlcv", lambda *a, **k: _flat_frame())

    broker = StubBroker(open_positions=0)
    rm = RiskManager(RiskConfig(max_open_positions=1, max_trades_per_day=5))
    rm.register_trade_open()  # simulate a trade opened on an earlier bar
    assert rm.can_trade() is False

    runner = LiveRunner(broker, ICTStrategy(), rm, LiveRunnerConfig())
    runner.poll_once()

    # Broker reports flat, so the runner should have released the latch.
    assert rm.can_trade() is True


def test_poll_respects_broker_reporting_an_open_position(monkeypatch):
    monkeypatch.setattr(runner_module, "fetch_ohlcv", lambda *a, **k: _flat_frame())

    broker = StubBroker(open_positions=1)
    rm = RiskManager()
    runner = LiveRunner(broker, ICTStrategy(), rm, LiveRunnerConfig())
    runner.poll_once()

    assert broker.submitted == []
    assert rm.can_trade() is False


def test_poll_ignores_a_bar_it_has_already_seen(monkeypatch):
    monkeypatch.setattr(runner_module, "fetch_ohlcv", lambda *a, **k: _flat_frame())

    broker = StubBroker()
    runner = LiveRunner(broker, ICTStrategy(), RiskManager(), LiveRunnerConfig())

    runner.poll_once()
    seen = runner._last_seen
    runner.poll_once()  # same frame, no newly closed bar

    assert runner._last_seen == seen
    assert broker.submitted == []


def test_flat_market_produces_no_orders(monkeypatch):
    monkeypatch.setattr(runner_module, "fetch_ohlcv", lambda *a, **k: _flat_frame())

    broker = StubBroker()
    runner = LiveRunner(broker, ICTStrategy(), RiskManager(), LiveRunnerConfig())
    runner.poll_once()

    assert broker.submitted == []


def test_stub_broker_satisfies_the_broker_interface():
    broker = StubBroker()
    result = broker.submit_bracket_order("QQQ", Direction.BULLISH, 10, 100, 98, 106)
    assert result.status == "accepted"
