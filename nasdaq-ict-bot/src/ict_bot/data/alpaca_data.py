"""Historical bars from Alpaca, used to seed the live analyzer.

Swing detection needs history before it can say anything, so the stream is
primed with recent bars from the same venue it's about to stream from --
mixing a yfinance seed with an Alpaca stream would splice two differently
consolidated series together at the join.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from ict_bot.data.stream import to_pandas_freq

COLUMNS = ["open", "high", "low", "close", "volume"]


def fetch_alpaca_bars(
    symbol: str,
    interval: str = "5m",
    lookback_days: int = 5,
    api_key: str | None = None,
    secret_key: str | None = None,
    feed: str = "iex",
) -> pd.DataFrame:
    """Recent OHLCV bars, normalized to the same shape fetch_ohlcv returns."""
    try:
        from alpaca.data.enums import DataFeed
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    except ImportError as exc:
        raise ImportError(
            "Alpaca history requires 'alpaca-py': pip install alpaca-py"
        ) from exc

    api_key = api_key or os.environ.get("ALPACA_API_KEY")
    secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise ValueError("Alpaca credentials not found (ALPACA_API_KEY / ALPACA_SECRET_KEY)")

    client = StockHistoricalDataClient(api_key, secret_key)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=_timeframe(interval, TimeFrame, TimeFrameUnit),
        start=datetime.now(timezone.utc) - timedelta(days=lookback_days),
        feed=DataFeed(feed.lower()),
    )
    bars = client.get_stock_bars(request)
    df = bars.df
    if df is None or df.empty:
        raise ValueError(f"Alpaca returned no bars for {symbol}")

    # get_stock_bars returns a (symbol, timestamp) MultiIndex for one or many
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level=0)

    df = df.rename(columns=str.lower)[COLUMNS].copy()
    df.index = pd.DatetimeIndex(df.index)
    df.index = df.index.tz_convert("UTC") if df.index.tz else df.index.tz_localize("UTC")
    df.index.name = "timestamp"
    return df.sort_index()


def _timeframe(interval: str, TimeFrame, TimeFrameUnit):
    """Map '5m' onto an Alpaca TimeFrame."""
    freq = to_pandas_freq(interval)
    if freq.endswith("min"):
        return TimeFrame(int(freq[:-3]), TimeFrameUnit.Minute)
    if freq.endswith("h"):
        return TimeFrame(int(freq[:-1]), TimeFrameUnit.Hour)
    return TimeFrame(int(freq[:-1]), TimeFrameUnit.Day)
