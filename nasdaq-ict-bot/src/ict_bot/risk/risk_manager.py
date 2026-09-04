"""Position sizing and account-level risk guardrails."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 0.5   # % of equity risked per trade
    max_daily_loss_pct: float = 2.0   # circuit breaker for the trading day
    max_open_positions: int = 1
    max_trades_per_day: int = 5


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
        risk_amount = equity * (self.config.risk_per_trade_pct / 100)
        per_unit_risk = abs(entry - stop)
        quantity = risk_amount / per_unit_risk if per_unit_risk else 0.0
        return TradeRisk(quantity=quantity, risk_amount=risk_amount)

    def register_trade_open(self) -> None:
        self._trades_today += 1
        self._open_positions += 1

    def register_trade_close(self, pnl: float) -> None:
        self._open_positions = max(0, self._open_positions - 1)
        if pnl < 0:
            self._daily_loss += abs(pnl)
