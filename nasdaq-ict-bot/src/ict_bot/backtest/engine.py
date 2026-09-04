"""Bar-by-bar backtest engine for the ICT strategy."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ict_bot.core.structure import Direction
from ict_bot.risk.risk_manager import RiskManager
from ict_bot.strategy.ict_strategy import ICTStrategy


@dataclass
class Trade:
    entry_index: pd.Timestamp
    exit_index: pd.Timestamp | None
    direction: Direction
    entry: float
    stop: float
    target: float
    quantity: float
    exit_price: float | None = None
    pnl: float | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: pd.Series


class BacktestEngine:
    """Simulates the strategy's signals against subsequent price action:
    a signal opens a position at its planned entry on the bar it fires,
    which is then closed when price touches the stop or the target,
    whichever comes first (stop checked first as the conservative
    assumption when both are hit within the same bar).
    """

    def __init__(self, strategy: ICTStrategy, risk_manager: RiskManager, starting_equity: float = 100_000.0) -> None:
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.starting_equity = starting_equity

    def run(self, df: pd.DataFrame) -> BacktestResult:
        signals = {s.index: s for s in self.strategy.generate_signals(df)}
        equity = self.starting_equity
        equity_curve: list[tuple[pd.Timestamp, float]] = []
        trades: list[Trade] = []
        open_trade: Trade | None = None
        current_day = None

        for ts, row in df.iterrows():
            if current_day != ts.date():
                current_day = ts.date()
                self.risk_manager.reset_day()

            if open_trade is not None:
                exit_price = self._check_exit(open_trade, row)
                if exit_price is not None:
                    pnl = self._settle(open_trade, exit_price, ts)
                    equity += pnl
                    trades.append(open_trade)
                    open_trade = None

            signal = signals.get(ts)
            if signal is not None and open_trade is None and self.risk_manager.can_trade():
                sized = self.risk_manager.size_position(equity, signal.entry, signal.stop)
                if sized.quantity > 0:
                    open_trade = Trade(
                        entry_index=ts,
                        exit_index=None,
                        direction=signal.direction,
                        entry=signal.entry,
                        stop=signal.stop,
                        target=signal.target,
                        quantity=sized.quantity,
                        reasons=signal.reasons,
                    )
                    self.risk_manager.register_trade_open()

            equity_curve.append((ts, equity))

        series = pd.Series({t: e for t, e in equity_curve})
        return BacktestResult(trades=trades, equity_curve=series)

    @staticmethod
    def _check_exit(trade: Trade, row: pd.Series) -> float | None:
        if trade.direction == Direction.BULLISH:
            if row["low"] <= trade.stop:
                return trade.stop
            if row["high"] >= trade.target:
                return trade.target
        else:
            if row["high"] >= trade.stop:
                return trade.stop
            if row["low"] <= trade.target:
                return trade.target
        return None

    def _settle(self, trade: Trade, exit_price: float, ts: pd.Timestamp) -> float:
        direction_sign = 1 if trade.direction == Direction.BULLISH else -1
        pnl = direction_sign * (exit_price - trade.entry) * trade.quantity
        trade.exit_index = ts
        trade.exit_price = exit_price
        trade.pnl = pnl
        self.risk_manager.register_trade_close(pnl)
        return pnl
