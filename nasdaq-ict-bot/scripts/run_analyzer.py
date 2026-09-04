#!/usr/bin/env python
"""CLI: watch a market through the ICT model in real time.

Read-only. No broker is constructed and no order can be placed from this
script -- it exists to show you what the model sees.

    # live stream from Alpaca (needs .env keys; free IEX feed by default)
    python scripts/run_analyzer.py --source alpaca --symbol QQQ

    # delayed polling via yfinance, no account needed
    python scripts/run_analyzer.py --source yfinance --symbol QQQ

    # replay the last few days bar by bar, any time of day
    python scripts/run_analyzer.py --source replay --period 5d
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ict_bot.analysis.analyzer import MarketAnalyzer  # noqa: E402
from ict_bot.analysis.display import render  # noqa: E402
from ict_bot.analysis.session import AnalysisSession, AnalysisSessionConfig  # noqa: E402
from ict_bot.strategy.ict_strategy import ICTStrategy  # noqa: E402
from ict_bot.utils.config import load_config  # noqa: E402


def _clear() -> None:
    if sys.stdout.isatty():
        print("\x1b[2J\x1b[H", end="")


def main() -> None:
    ap = argparse.ArgumentParser(description="Live ICT market analysis (read-only)")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--symbol", default=None)
    ap.add_argument("--interval", default=None)
    ap.add_argument("--source", choices=["alpaca", "yfinance", "replay"], default="yfinance")
    ap.add_argument("--period", default="5d", help="history to seed/replay (yfinance syntax)")
    ap.add_argument("--feed", default="iex", choices=["iex", "sip"], help="Alpaca data feed")
    ap.add_argument("--poll", type=int, default=None, help="seconds between yfinance polls")
    ap.add_argument("--replay-delay", type=float, default=0.15, help="seconds between replayed bars")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config) if Path(args.config).exists() else None
    symbol = args.symbol or (cfg.runner.symbol if cfg else "QQQ")
    interval = args.interval or (cfg.runner.interval if cfg else "5m")
    poll = args.poll or (cfg.runner.poll_seconds if cfg else 60)
    color = not args.no_color

    strategy = ICTStrategy(cfg.strategy if cfg else None)
    analyzer = MarketAnalyzer(strategy, symbol=symbol)
    session_cfg = AnalysisSessionConfig(symbol=symbol, interval=interval)

    def show(snap) -> None:
        _clear()
        print(render(snap, color=color))

    if args.source == "alpaca":
        _run_alpaca(analyzer, session_cfg, args, symbol, interval, show)
    elif args.source == "replay":
        _run_replay(analyzer, session_cfg, args, symbol, interval, show)
    else:
        _run_polling(analyzer, session_cfg, args, symbol, interval, poll, show)


def _run_alpaca(analyzer, session_cfg, args, symbol, interval, show) -> None:
    from ict_bot.analysis.session import AnalysisSession
    from ict_bot.data.alpaca_data import fetch_alpaca_bars
    from ict_bot.data.stream import AlpacaBarStream

    if not os.environ.get("ALPACA_API_KEY"):
        print("ALPACA_API_KEY is not set. Copy .env.example to .env and fill it in,")
        print("or run with --source yfinance for delayed data without an account.")
        raise SystemExit(1)

    print(f"Seeding {symbol} history from Alpaca ({args.feed} feed)...")
    seed = fetch_alpaca_bars(symbol, interval=interval, lookback_days=5, feed=args.feed)
    session = AnalysisSession(analyzer, seed=seed, config=session_cfg, on_snapshot=show)
    session.refresh()

    print(f"Streaming live {interval} bars for {symbol}. Ctrl-C to stop.")
    stream = AlpacaBarStream(symbol, interval=interval, feed=args.feed)
    try:
        stream.run(session.handle_bar)
    except KeyboardInterrupt:
        stream.stop()
        print("\nStopped.")


def _run_polling(analyzer, session_cfg, args, symbol, interval, poll, show) -> None:
    from ict_bot.data.fetcher import fetch_ohlcv

    print(f"Polling {symbol} every {poll}s via yfinance (delayed data). Ctrl-C to stop.")
    session = AnalysisSession(analyzer, config=session_cfg, on_snapshot=show)
    last_seen = None
    try:
        while True:
            try:
                df = fetch_ohlcv(symbol, period=args.period, interval=interval)
                if last_seen is None or df.index[-1] > last_seen:
                    last_seen = df.index[-1]
                    # Re-seed wholesale: polling gives us the frame, not deltas.
                    session.frame = _reseed(session, df)
                    session.refresh()
            except Exception as exc:  # noqa: BLE001 - keep the watch alive
                print(f"fetch failed: {exc}")
            time.sleep(poll)
    except KeyboardInterrupt:
        print("\nStopped.")


def _reseed(session, df):
    from ict_bot.data.stream import RollingFrame

    return RollingFrame(df, max_bars=session.config.max_bars)


def _run_replay(analyzer, session_cfg, args, symbol, interval, show) -> None:
    from ict_bot.data.fetcher import fetch_ohlcv

    print(f"Replaying {symbol} {args.period} of {interval} bars...")
    df = fetch_ohlcv(symbol, period=args.period, interval=interval)
    session = AnalysisSession(analyzer, config=session_cfg)

    try:
        for ts, row in df.iterrows():
            from ict_bot.data.stream import Bar

            snap = session.handle_bar(
                Bar(ts, float(row["open"]), float(row["high"]),
                    float(row["low"]), float(row["close"]), float(row.get("volume", 0.0)))
            )
            if snap is not None:
                show(snap)
                time.sleep(args.replay_delay)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
