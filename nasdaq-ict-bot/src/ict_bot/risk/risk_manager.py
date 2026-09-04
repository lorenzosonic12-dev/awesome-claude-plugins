"""Position sizing and account-level risk guardrails."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 0.5        # % of equity risked per trade
    max_daily_loss_pct: float = 2.0        # circuit breaker for the trading day
    max_open_positions: int = 1
    max_trades_per_day: int = 5
    max_position_notional_pct: float = 100.0  # cap position value at this % of equity


@dataclass
class TradeRisk:
    quantity: float
    risk_amount: float


class RiskManager:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        self._daily_loss = 0.0
        self._trades_today = 0
        self._open_positions = 0

    def reset_day(self) -> None:
        self._daily_loss = 0.0
        self._trades_today = 0

    def can_trade(self) -> bool:
        cfg = self.config
        if self._open_positions >= cfg.max_open_positions:
            return False
        if self._trades_today >= cfg.max_trades_per_day:
            return False
        return True

    def is_daily_loss_limit_hit(self, equity: float) -> bool:
        return self._daily_loss >= equity * (self.config.max_daily_loss_pct / 100)

    def size_position(self, equity: float, entry: float, stop: float) -> TradeRisk:
        """Size by stop distance, then cap the position's notional value so a
        tight stop can't lever the account up. `risk_amount` reflects the
        risk actually taken after any cap is applied, not the budget."""
        risk_budget = equity * (self.config.risk_per_trade_pct / 100)
        per_unit_risk = abs(entry - stop)
        if not per_unit_risk:
            return TradeRisk(quantity=0.0, risk_amount=0.0)

        quantity = risk_budget / per_unit_risk

        max_notional = equity * (self.config.max_position_notional_pct / 100)
        if entry > 0 and quantity * entry > max_notional:
            quantity = max_notional / entry

        return TradeRisk(quantity=quantity, risk_amount=quantity * per_unit_risk)

    def sync_open_positions(self, count: int) -> None:
        """Reconcile the internal position counter against the broker's real
        open position count. The live loop has no fill callbacks, so without
        this the counter only ever increments and `can_trade` latches off
        after the first trade."""
        self._open_positions = max(0, count)

    def register_trade_open(self) -> None:
        self._trades_today += 1
        self._open_positions += 1

    def register_trade_close(self, pnl: float) -> None:
        self._open_positions = max(0, self._open_positions - 1)
        if pnl < 0:
            self._daily_loss += abs(pnl)
