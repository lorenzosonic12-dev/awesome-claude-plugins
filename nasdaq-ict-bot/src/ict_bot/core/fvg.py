"""Fair Value Gap (imbalance) detection.

A three-candle pattern left behind by a displacement move: candle 1 and
candle 3 don't overlap, leaving a gap that ICT treats as an inefficiency
price is likely to return to and "fill" before continuing.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ict_bot.core.structure import Direction


@dataclass
class FairValueGap:
    index: pd.Timestamp  # timestamp of the middle (displacement) candle
    top: float
    bottom: float
    direction: Direction
    formed_at: pd.Timestamp | None = None  # timestamp of the 3rd candle that completes the gap
    mitigated: bool = False
    mitigated_at: pd.Timestamp | None = None


def detect_fvgs(df: pd.DataFrame) -> list[FairValueGap]:
    """Bullish FVG: candle[i-2].high < candle[i].low.
    Bearish FVG: candle[i-2].low > candle[i].high.
    """
    fvgs: list[FairValueGap] = []
    highs, lows = df["high"], df["low"]

    for i in range(2, len(df)):
        c1_high, c1_low = highs.iloc[i - 2], lows.iloc[i - 2]
        c3_high, c3_low = highs.iloc[i], lows.iloc[i]

        if c1_high < c3_low:
            fvgs.append(
                FairValueGap(
                    df.index[i - 1], top=float(c3_low), bottom=float(c1_high),
                    direction=Direction.BULLISH, formed_at=df.index[i],
                )
            )
        elif c1_low > c3_high:
            fvgs.append(
                FairValueGap(
                    df.index[i - 1], top=float(c1_low), bottom=float(c3_high),
                    direction=Direction.BEARISH, formed_at=df.index[i],
                )
            )

    return fvgs


def update_mitigation(fvgs: list[FairValueGap], df: pd.DataFrame) -> None:
    """Mark each gap mitigated the first time a *later* bar trades back into
    it. Bars up to and including the one that completes the gap are
    excluded, since candle 3 always sits exactly on the gap's own boundary.
    """
    for gap in fvgs:
        if gap.mitigated:
            continue
        future = df.loc[df.index > gap.formed_at]
        for ts, row in future.iterrows():
            if gap.direction == Direction.BULLISH and row["low"] <= gap.top:
                gap.mitigated = True
                gap.mitigated_at = ts
                break
            if gap.direction == Direction.BEARISH and row["high"] >= gap.bottom:
                gap.mitigated = True
                gap.mitigated_at = ts
                break
