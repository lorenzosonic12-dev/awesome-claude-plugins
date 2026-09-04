"""Historical + recent OHLCV data retrieval via yfinance."""
from __future__ import annotations

import pandas as pd

DEFAULT_COLUMNS = ["open", "high", "low", "close", "volume"]


def fetch_ohlcv(symbol: str, period: str = "60d", interval: str = "5m") -> pd.DataFrame:
    """Fetch OHLCV bars for `symbol` (e.g. 'QQQ', 'NQ=F', '^NDX') and
    normalize to lowercase columns with a tz-aware UTC index."""
    import yfinance as yf

    raw = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    if raw is None or raw.empty:
        raise ValueError(f"No data returned for {symbol} ({period}, {interval})")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw.rename(columns=str.lower)[DEFAULT_COLUMNS].copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index.name = "timestamp"
    return df
