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
