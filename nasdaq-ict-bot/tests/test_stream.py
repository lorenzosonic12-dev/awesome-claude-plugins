from __future__ import annotations

import pandas as pd
import pytest

from ict_bot.data.stream import Bar, BarAggregator, RollingFrame, to_pandas_freq


def test_interval_conversion():
    assert to_pandas_freq("5m") == "5min"
    assert to_pandas_freq("15min") == "15min"
    assert to_pandas_freq("1h") == "1h"
    with pytest.raises(ValueError):
        to_pandas_freq("banana")


def test_aggregator_emits_only_on_window_close():
    agg = BarAggregator("5m")
    base = pd.Timestamp("2024-01-02 14:30", tz="UTC")

    # four 1-minute bars inside the same 5-minute window
    assert agg.add(base, 100, 101, 99, 100.5, 10) is None
    assert agg.add(base + pd.Timedelta(minutes=1), 100.5, 103, 100, 102, 10) is None
    assert agg.add(base + pd.Timedelta(minutes=2), 102, 102.5, 98, 99, 10) is None
    assert agg.add(base + pd.Timedelta(minutes=3), 99, 100, 98.5, 99.5, 10) is None

    # the bar that opens the next window closes the previous one
    closed = agg.add(base + pd.Timedelta(minutes=5), 99.5, 100, 99, 99.8, 5)
    assert closed is not None
    assert closed.timestamp == base
    assert closed.open == 100        # first print
    assert closed.high == 103        # highest across the window
    assert closed.low == 98          # lowest across the window
    assert closed.close == 99.5      # last print of the window
    assert closed.volume == 40


def test_aggregator_never_hands_out_an_open_bar():
    agg = BarAggregator("5m")
    base = pd.Timestamp("2024-01-02 14:30", tz="UTC")
    agg.add(base, 100, 101, 99, 100, 1)
    assert agg.pending is not None
    assert agg.pending.close == 100

    flushed = agg.flush()
    assert flushed is not None
    assert agg.pending is None


def test_aggregator_localizes_naive_timestamps():
    agg = BarAggregator("5m")
    agg.add(pd.Timestamp("2024-01-02 14:30"), 100, 100, 100, 100, 1)
    closed = agg.add(pd.Timestamp("2024-01-02 14:35"), 100, 100, 100, 100, 1)
    assert closed is not None
    assert closed.timestamp.tzinfo is not None


def test_rolling_frame_evicts_oldest():
    frame = RollingFrame(max_bars=3)
    base = pd.Timestamp("2024-01-02 14:30", tz="UTC")
    for i in range(5):
        frame.append(Bar(base + pd.Timedelta(minutes=5 * i), 100, 101, 99, 100 + i, 10))

    assert len(frame) == 3
    assert frame.frame["close"].iloc[0] == 102  # bars 0 and 1 evicted
    assert frame.frame["close"].iloc[-1] == 104
    assert frame.frame.index.is_monotonic_increasing


def test_rolling_frame_seeds_from_history():
    idx = pd.date_range("2024-01-02 14:30", periods=4, freq="5min", tz="UTC")
    seed = pd.DataFrame(
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 5.0},
        index=idx,
    )
    frame = RollingFrame(seed, max_bars=10)
    assert len(frame) == 4

    frame.append(Bar(idx[-1] + pd.Timedelta(minutes=5), 100, 102, 100, 101.5, 7))
    assert len(frame) == 5
    assert frame.frame["close"].iloc[-1] == 101.5
