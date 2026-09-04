#!/usr/bin/env python
"""CLI: run the ICT strategy live/paper against a broker.

Defaults to the in-memory PaperBroker, so nothing touches a real account
until you explicitly pass --broker alpaca, and nothing touches a *live*
account until you also pass --live and type the confirmation phrase.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ict_bot.live.runner import LiveRunner  # noqa: E402
from ict_bot.risk.risk_manager import RiskManager  # noqa: E402
from ict_bot.strategy.ict_strategy import ICTStrategy  # noqa: E402
from ict_bot.utils.config import load_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ICT NASDAQ bot live/paper")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--broker", choices=["paper", "alpaca"], default="paper")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use Alpaca's LIVE endpoint instead of paper (requires --broker alpaca)",
    )
    args = parser.parse_args()

    config = load_config(args.config) if Path(args.config).exists() else None
    strategy = ICTStrategy(config.strategy if config else None)
    risk_manager = RiskManager(config.risk if config else None)
    runner_config = config.runner if config else None

    if args.broker == "alpaca":
        from ict_bot.broker.alpaca_broker import AlpacaBroker

        if args.live:
            confirm = input("Type 'CONFIRM LIVE TRADING' to proceed with a real Alpaca account: ")
            if confirm.strip() != "CONFIRM LIVE TRADING":
                print("Aborted.")
                return
        broker = AlpacaBroker(paper=not args.live)
    else:
        from ict_bot.broker.paper_broker import PaperBroker

        starting_equity = config.starting_equity if config else 100_000.0
        broker = PaperBroker(starting_equity=starting_equity)

    runner = LiveRunner(broker, strategy, risk_manager, runner_config)
    runner.run_forever()


if __name__ == "__main__":
    main()
