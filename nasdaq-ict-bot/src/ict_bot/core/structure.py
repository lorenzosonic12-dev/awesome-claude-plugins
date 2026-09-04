"""Market structure detection: swing points, Break of Structure (BOS), and
Change of Character (CHoCH).

ICT reads price action as a sequence of swing highs/lows. While the market
keeps breaking structure in the direction of the prevailing trend, that's a
BOS (trend continuation). The first break in the *opposite* direction is a
CHoCH -- the earliest structural signal that a reversal may be underway.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class StructureEventType(str, Enum):
    BOS = "BOS"
    CHOCH = "CHoCH"


@dataclass(frozen=True)
class SwingPoint:
    index: pd.Timestamp
    price: float
    kind: str  # "high" or "low"


@dataclass(frozen=True)
class StructureEvent:
    index: pd.Timestamp
    event_type: StructureEventType
    direction: Direction
    price: float
    swing: SwingPoint


def find_swing_points(df: pd.DataFrame, lookback: int = 3) -> list[SwingPoint]:
    """Locate fractal swing highs/lows: a bar whose high (low) is the unique
    extreme within `lookback` bars on either side."""
    highs = df["high"]
    lows = df["low"]
    swings: list[SwingPoint] = []
    n = len(df)

    for i in range(lookback, n - lookback):
        window_high = highs.iloc[i - lookback : i + lookback + 1]
        if highs.iloc[i] == window_high.max() and (window_high == highs.iloc[i]).sum() == 1:
            swings.append(SwingPoint(df.index[i], float(highs.iloc[i]), "high"))

        window_low = lows.iloc[i - lookback : i + lookback + 1]
        if lows.iloc[i] == window_low.min() and (window_low == lows.iloc[i]).sum() == 1:
            swings.append(SwingPoint(df.index[i], float(lows.iloc[i]), "low"))

    swings.sort(key=lambda s: s.index)
    return swings


def detect_structure_events(df: pd.DataFrame, swings: list[SwingPoint]) -> list[StructureEvent]:
    """Walk forward through candle closes, tracking the most recent unbroken
    swing high/low, and flag BOS/CHoCH the first time a close trades beyond
    one of them.

    The reference is the *most recent* pivot, not the most extreme one. In a
    downtrend the level that matters is the latest lower high -- breaking it
    is the change of character. Tracking the highest high instead would keep
    pointing at some stale level from before the trend began.
    """
    events: list[StructureEvent] = []
    trend: Direction | None = None

    last_high: SwingPoint | None = None
    last_low: SwingPoint | None = None
    swing_iter = iter(swings)
    next_swing = next(swing_iter, None)

    for ts, row in df.iterrows():
        # Absorb swings confirmed strictly before this bar. A swing point
        # formed *by* this bar's own high/low must not be used to judge this
        # same bar's breakout -- it only becomes relevant for future bars.
        while next_swing is not None and next_swing.index < ts:
            if next_swing.kind == "high":
                last_high = next_swing
            else:
                last_low = next_swing
            next_swing = next(swing_iter, None)

        close = row["close"]

        if last_high is not None and close > last_high.price:
            event_type = (
                StructureEventType.BOS
                if trend in (None, Direction.BULLISH)
                else StructureEventType.CHOCH
            )
            events.append(StructureEvent(ts, event_type, Direction.BULLISH, float(close), last_high))
            trend = Direction.BULLISH
            last_high = None
        elif last_low is not None and close < last_low.price:
            event_type = (
                StructureEventType.BOS
                if trend in (None, Direction.BEARISH)
                else StructureEventType.CHOCH
            )
            events.append(StructureEvent(ts, event_type, Direction.BEARISH, float(close), last_low))
            trend = Direction.BEARISH
            last_low = None

        # Now absorb any swing point formed by this bar itself, so it's
        # available to judge breakouts on subsequent bars.
        while next_swing is not None and next_swing.index == ts:
            if next_swing.kind == "high":
                last_high = next_swing
            else:
                last_low = next_swing
            next_swing = next(swing_iter, None)

    return events
