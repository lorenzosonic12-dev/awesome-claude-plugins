"""ICT kill zones / trading session windows, defined in New York local
time -- the exchange timezone for NASDAQ instruments.
"""
from __future__ import annotations

from datetime import time

import pandas as pd

NY_TZ = "America/New_York"

# (start, end) in NY local time. A zone that wraps past midnight (start > end)
# is handled by in_kill_zone below.
KILL_ZONES: dict[str, tuple[time, time]] = {
    "asian": (time(20, 0), time(0, 0)),
    "london_open": (time(2, 0), time(5, 0)),
    "ny_am": (time(7, 0), time(10, 0)),
    "silver_bullet_am": (time(10, 0), time(11, 0)),
    "ny_lunch": (time(12, 0), time(13, 0)),
    "silver_bullet_pm": (time(14, 0), time(15, 0)),
    "london_close": (time(10, 0), time(12, 0)),
}


def _to_ny(ts: pd.Timestamp) -> pd.Timestamp:
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(NY_TZ)


def in_kill_zone(ts: pd.Timestamp, zone: str) -> bool:
    start, end = KILL_ZONES[zone]
    local = _to_ny(ts).time()
    if start <= end:
        return start <= local < end
    return local >= start or local < end


def active_kill_zones(ts: pd.Timestamp) -> list[str]:
    return [name for name in KILL_ZONES if in_kill_zone(ts, name)]
