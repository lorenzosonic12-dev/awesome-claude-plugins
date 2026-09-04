from __future__ import annotations

import pandas as pd

from ict_bot.core.sessions import in_kill_zone


def test_ny_am_kill_zone():
    ts = pd.Timestamp("2024-01-02 08:00", tz="America/New_York")
    assert in_kill_zone(ts, "ny_am") is True
    ts_outside = pd.Timestamp("2024-01-02 13:00", tz="America/New_York")
    assert in_kill_zone(ts_outside, "ny_am") is False


def test_wrapping_zone_crosses_midnight():
    late = pd.Timestamp("2024-01-02 22:00", tz="America/New_York")
    early = pd.Timestamp("2024-01-02 23:59", tz="America/New_York")
    assert in_kill_zone(late, "asian") is True
    assert in_kill_zone(early, "asian") is True
    daytime = pd.Timestamp("2024-01-02 12:00", tz="America/New_York")
    assert in_kill_zone(daytime, "asian") is False


def test_naive_timestamp_treated_as_utc():
    ts = pd.Timestamp("2024-01-02 12:00")  # 12:00 UTC = 07:00 NY (winter)
    assert in_kill_zone(ts, "ny_am") is True
