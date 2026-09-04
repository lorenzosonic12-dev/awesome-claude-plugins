from __future__ import annotations

import pandas as pd
import pytest


def bar(o: float, h: float, l: float, c: float, v: float = 1000.0) -> dict:
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def make_df(rows: list[dict], start: str = "2024-01-02 07:00", freq: str = "5min") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    return pd.DataFrame(rows, index=idx)


@pytest.fixture
def bar_factory():
    return bar


@pytest.fixture
def df_factory():
    return make_df


def full_setup_rows() -> list[dict]:
    """A complete ICT sequence, in the order the model expects to read it.

    Price rallies and leaves equal highs (buy-side liquidity), sells off and
    breaks structure down, prints equal lows, sweeps them with a wick that
    closes back above, then displaces up through the last lower high (CHoCH)
    leaving a gap it retraces into. The target is the old high from the
    opening rally -- liquidity that existed well before the entry.
    """
    rows: list[dict] = []
    rows += [bar(105.5, 105.9, 105.1, 105.5) for _ in range(4)]   # 0-3
    rows += [bar(105.6, 106.00, 105.4, 105.7)]                     # 4   swing high 106.00
    rows += [bar(105.5, 105.9, 105.1, 105.5) for _ in range(4)]   # 5-8
    rows += [bar(105.6, 106.02, 105.4, 105.7)]                     # 9   equal high -> buy pool
    rows += [bar(105.4, 105.8, 105.0, 105.3) for _ in range(4)]   # 10-13
    rows += [bar(105.0, 105.2, 104.00, 104.2)]                     # 14  swing low 104.00
    rows += [bar(104.4, 104.8, 104.2, 104.6) for _ in range(4)]   # 15-18
    rows += [bar(104.4, 104.6, 103.5, 103.6)]                      # 19  BOS bearish
    rows += [bar(103.0, 103.4, 102.6, 103.0) for _ in range(4)]   # 20-23
    rows += [bar(102.6, 103.0, 102.0, 102.2) for _ in range(4)]   # 24-27
    rows += [bar(101.6, 102.0, 101.2, 101.4)]                      # 28
    rows += [bar(100.6, 100.9, 100.00, 100.3)]                     # 29  swing low 100.00
    rows += [bar(100.8, 101.2, 100.4, 100.9) for _ in range(4)]   # 30-33
    rows += [bar(100.6, 100.9, 100.02, 100.3)]                     # 34  equal low -> sell pool
    rows += [bar(100.8, 101.2, 100.5, 100.9) for _ in range(2)]   # 35-36
    rows += [bar(101.0, 102.00, 100.8, 101.6)]                     # 37  lower high 102.00
    rows += [bar(100.9, 101.3, 100.6, 101.0) for _ in range(2)]   # 38-39
    rows += [bar(100.8, 101.0, 99.40, 100.5)]                      # 40  SWEEP
    rows += [bar(100.6, 101.0, 100.4, 100.8) for _ in range(2)]   # 41-42
    rows += [bar(100.9, 101.2, 100.7, 101.1)]                      # 43  FVG c1
    rows += [bar(101.1, 104.2, 101.0, 104.0)]                      # 44  displacement -> CHoCH
    rows += [bar(104.0, 104.6, 102.5, 104.2)]                      # 45  FVG c3
    rows += [bar(104.2, 104.4, 102.2, 102.6)]                      # 46  retrace tags the gap
    rows += [bar(102.8, 104.0, 102.6, 103.8)]                      # 47
    rows += [bar(104.0, 105.0, 103.8, 104.8) for _ in range(3)]   # 48-50
    return rows


# Index of the bar the signal fires on, for tests that assert timing.
FULL_SETUP_SIGNAL_BAR = 46


@pytest.fixture
def full_setup():
    """The frame above, started so the signal bar lands at 07:50 New York --
    inside the ny_am kill zone the default config enables."""
    return make_df(full_setup_rows(), start="2024-01-02 09:00")
