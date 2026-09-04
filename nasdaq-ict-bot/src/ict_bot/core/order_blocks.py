"""Order block detection: the last opposite-colored candle before a
displacement move that produces a break of structure -- the footprint of
the institutional order flow that fueled the move.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ict_bot.core.structure import Direction, StructureEvent


@dataclass
class OrderBlock:
    index: pd.Timestamp
    top: float
    bottom: float
    direction: Direction
    structure_event_index: pd.Timestamp
    mitigated: bool = False
    mitigated_at: pd.Timestamp | None = None


def detect_order_blocks(df: pd.DataFrame, events: list[StructureEvent], search_window: int = 20) -> list[OrderBlock]:
    """For every structure event, walk back up to `search_window` bars and
    take the last candle of the opposite color as the order block."""
    obs: list[OrderBlock] = []

    for event in events:
        pos = df.index.get_indexer([event.index])[0]
        if pos <= 0:
            continue
        window = df.iloc[max(0, pos - search_window) : pos]

        if event.direction == Direction.BULLISH:
            down_candles = window[window["close"] < window["open"]]
            if down_candles.empty:
                continue
            ob_idx = down_candles.index[-1]
            row = df.loc[ob_idx]
            obs.append(
                OrderBlock(ob_idx, top=float(row["high"]), bottom=float(row["low"]),
                           direction=Direction.BULLISH, structure_event_index=event.index)
            )
        else:
            up_candles = window[window["close"] > window["open"]]
            if up_candles.empty:
                continue
            ob_idx = up_candles.index[-1]
            row = df.loc[ob_idx]
            obs.append(
                OrderBlock(ob_idx, top=float(row["high"]), bottom=float(row["low"]),
                           direction=Direction.BEARISH, structure_event_index=event.index)
            )

    return obs


def update_mitigation(order_blocks: list[OrderBlock], df: pd.DataFrame) -> None:
    for ob in order_blocks:
        if ob.mitigated:
            continue
        future = df.loc[df.index > ob.structure_event_index]
        for ts, row in future.iterrows():
            if ob.direction == Direction.BULLISH and row["low"] <= ob.top:
                ob.mitigated = True
                ob.mitigated_at = ts
                break
            if ob.direction == Direction.BEARISH and row["high"] >= ob.bottom:
                ob.mitigated = True
                ob.mitigated_at = ts
                break
