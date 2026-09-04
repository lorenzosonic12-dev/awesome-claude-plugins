#!/usr/bin/env python
"""CLI: backtest the ICT strategy over historical data.

Example:
    python scripts/run_backtest.py --symbol QQQ --period 60d --interval 5m
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ict_bot.backtest.engine import BacktestEngine  # noqa: E402
from ict_bot.backtest.metrics import compute_metrics  # noqa: E402
from ict_bot.data.fetcher import fetch_ohlcv  # noqa: E402
from ict_bot.risk.risk_manager import RiskManager  # noqa: E402
from ict_bot.strategy.ict_strategy import ICTStrategy  # noqa: E402
from ict_bot.utils.config import load_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest the ICT NASDAQ strategy")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--symbol", default="QQQ")
    parser.add_argument("--period", default="60d")
    parser.add_argument("--interval", default="5m")
    args = parser.parse_args()

    config = load_config(args.config) if Path(args.config).exists() else None
    strategy = ICTStrategy(config.strategy if config else None)
    risk_manager = RiskManager(config.risk if config else None)
    starting_equity = config.starting_equity if config else 100_000.0

    df = fetch_ohlcv(args.symbol, period=args.period, interval=args.interval)
    engine = BacktestEngine(strategy, risk_manager, starting_equity=starting_equity)
    result = engine.run(df)
    metrics = compute_metrics(result)

    print(f"Symbol:          {args.symbol}")
    print(f"Bars:            {len(df)}")
    print(f"Trades:          {metrics.total_trades}")
    print(f"Win rate:        {metrics.win_rate:.1f}%")
    print(f"Profit factor:   {metrics.profit_factor:.2f}")
    print(f"Total PnL:       {metrics.total_pnl:,.2f}")
    print(f"Max drawdown:    {metrics.max_drawdown_pct:.2f}%")
    print(f"Avg planned RR:  {metrics.avg_risk_reward:.2f}")


if __name__ == "__main__":
    main()
