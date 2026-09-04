"""Performance metrics for a completed backtest."""
from __future__ import annotations

from dataclasses import dataclass

from ict_bot.backtest.engine import BacktestResult


@dataclass
class Metrics:
    total_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    max_drawdown_pct: float
    avg_risk_reward: float


def compute_metrics(result: BacktestResult) -> Metrics:
    trades = [t for t in result.trades if t.pnl is not None]
    total = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]

    win_rate = len(wins) / total * 100 if total else 0.0
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    if gross_loss:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit else 0.0
    total_pnl = sum(t.pnl for t in trades)

    equity = result.equity_curve
    if not equity.empty:
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max * 100
        max_drawdown_pct = float(drawdown.min())
    else:
        max_drawdown_pct = 0.0

    rr_values = [abs(t.target - t.entry) / abs(t.entry - t.stop) for t in trades if t.entry != t.stop]
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0.0

    return Metrics(
        total_trades=total,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_pnl=total_pnl,
        max_drawdown_pct=max_drawdown_pct,
        avg_risk_reward=avg_rr,
    )
