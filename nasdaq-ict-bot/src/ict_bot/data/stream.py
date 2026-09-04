"""Real-time bar plumbing.

Brokers stream fine-grained bars (Alpaca sends one a minute); the strategy
wants a coarser interval. BarAggregator rolls them up and emits a bar only
once its window has actually closed, so the model never analyzes a partial
candle. RollingFrame keeps a bounded history for the detectors to run over.

Both are pure in-memory objects with no network dependency.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import pandas as pd

_INTERVAL = re.compile(r"^(\d+)\s*(m|min|h|hour|d)$", re.IGNORECASE)


def to_pandas_freq(interval: str) -> str:
    """'5m' -> '5min'. Accepts the same shorthand the config and yfinance use."""
    match = _INTERVAL.match(interval.strip())
    if not match:
        raise ValueError(f"unrecognized interval: {interval!r}")
    count, unit = match.group(1), match.group(2).lower()
    if unit in ("m", "min"):
        return f"{count}min"
    if unit in ("h", "hour"):
        return f"{count}h"
    return f"{count}D"


@dataclass
class Bar:
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float

    def as_row(self) -> dict:
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class BarAggregator:
    """Rolls finer bars up into `interval`, emitting each window once closed.

    A bar is returned from `add` only when a later window opens -- the bar
    being built is never handed out, because acting on a candle that hasn't
    closed is how a backtest and a live bot quietly disagree.
    """

    def __init__(self, interval: str = "5m") -> None:
        self.freq = to_pandas_freq(interval)
        self._start: pd.Timestamp | None = None
        self._bar: Bar | None = None

    @property
    def pending(self) -> Bar | None:
        """The in-progress bar. Useful for display, never for signals."""
        return self._bar

    def add(self, timestamp: pd.Timestamp, o: float, h: float, l: float, c: float, v: float = 0.0) -> Bar | None:
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        window = ts.floor(self.freq)

        if self._start is None:
            self._start = window
            self._bar = Bar(window, o, h, l, c, v)
            return None

        if window > self._start:
            completed = self._bar
            self._start = window
            self._bar = Bar(window, o, h, l, c, v)
            return completed

        # same window -- extend the bar being built
        assert self._bar is not None
        self._bar.high = max(self._bar.high, h)
        self._bar.low = min(self._bar.low, l)
        self._bar.close = c
        self._bar.volume += v
        return None

    def flush(self) -> Bar | None:
        """Close out the in-progress bar (end of session, shutdown)."""
        done, self._bar, self._start = self._bar, None, None
        return done


class RollingFrame:
    """A bounded OHLCV frame the live loop appends closed bars to."""

    def __init__(self, seed: pd.DataFrame | None = None, max_bars: int = 500) -> None:
        self.max_bars = max_bars
        columns = ["open", "high", "low", "close", "volume"]
        if seed is not None and not seed.empty:
            self._df = seed[columns].tail(max_bars).copy()
        else:
            idx = pd.DatetimeIndex([], tz="UTC", name="timestamp")
            self._df = pd.DataFrame(columns=columns, index=idx, dtype=float)

    def append(self, bar: Bar) -> None:
        self._df.loc[bar.timestamp] = bar.as_row()
        if not self._df.index.is_monotonic_increasing:
            self._df.sort_index(inplace=True)
        if len(self._df) > self.max_bars:
            self._df = self._df.iloc[-self.max_bars :]

    @property
    def frame(self) -> pd.DataFrame:
        return self._df

    def __len__(self) -> int:
        return len(self._df)


class AlpacaBarStream:
    """Alpaca's real-time bar WebSocket, rolled up to the target interval.

    The free IEX feed carries a subset of consolidated volume; `feed="sip"`
    needs a paid market-data subscription. Either way this is live data, not
    the delayed snapshots the polling fetcher returns.
    """

    def __init__(
        self,
        symbol: str,
        interval: str = "5m",
        api_key: str | None = None,
        secret_key: str | None = None,
        feed: str = "iex",
    ) -> None:
        import os

        try:
            from alpaca.data.live import StockDataStream
        except ImportError as exc:
            raise ImportError(
                "Real-time streaming requires 'alpaca-py': pip install alpaca-py"
            ) from exc

        api_key = api_key or os.environ.get("ALPACA_API_KEY")
        secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            raise ValueError(
                "Alpaca credentials not found (ALPACA_API_KEY / ALPACA_SECRET_KEY)"
            )

        from alpaca.data.enums import DataFeed

        self.symbol = symbol
        self.aggregator = BarAggregator(interval)
        self._stream = StockDataStream(
            api_key, secret_key, feed=DataFeed(feed.lower())
        )

    def run(self, on_bar: Callable[[Bar], None]) -> None:
        """Block, feeding each *closed* interval bar to `on_bar`."""

        async def handler(bar) -> None:
            completed = self.aggregator.add(
                pd.Timestamp(bar.timestamp),
                float(bar.open), float(bar.high), float(bar.low),
                float(bar.close), float(bar.volume or 0.0),
            )
            if completed is not None:
                on_bar(completed)

        self._stream.subscribe_bars(handler, self.symbol)
        self._stream.run()

    def stop(self) -> None:
        self._stream.stop()
