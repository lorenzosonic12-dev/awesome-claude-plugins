from __future__ import annotations

from ict_bot.core.order_blocks import detect_order_blocks, update_mitigation
from ict_bot.core.structure import Direction, StructureEvent, StructureEventType, SwingPoint


def test_detect_bullish_order_block(bar_factory, df_factory):
    rows = [
        bar_factory(10, 10.2, 9.0, 9.2),   # down candle -> becomes the OB
        bar_factory(9.2, 12, 9.1, 11.8),   # displacement candle breaking structure
    ]
    df = df_factory(rows)
    swing = SwingPoint(df.index[0], 10.2, "high")
    event = StructureEvent(df.index[1], StructureEventType.BOS, Direction.BULLISH, 11.8, swing)

    obs = detect_order_blocks(df, [event])
    assert len(obs) == 1
    ob = obs[0]
    assert ob.direction == Direction.BULLISH
    assert ob.index == df.index[0]
    assert ob.top == 10.2
    assert ob.bottom == 9.0


def test_order_block_mitigation(bar_factory, df_factory):
    rows = [
        bar_factory(10, 10.2, 9.0, 9.2),
        bar_factory(9.2, 12, 9.1, 11.8),
        bar_factory(11, 11.5, 9.5, 9.8),  # low trades back into the OB range [9.0, 10.2]
    ]
    df = df_factory(rows)
    swing = SwingPoint(df.index[0], 10.2, "high")
    event = StructureEvent(df.index[1], StructureEventType.BOS, Direction.BULLISH, 11.8, swing)

    obs = detect_order_blocks(df, [event])
    update_mitigation(obs, df)
    assert obs[0].mitigated is True
