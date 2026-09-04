from __future__ import annotations

from ict_bot.core.structure import Direction, StructureEventType, detect_structure_events, find_swing_points


def test_find_swing_points_detects_high_and_low(bar_factory, df_factory):
    rows = [bar_factory(1, 1.1, 0.9, 1) for _ in range(3)]
    rows += [bar_factory(2, 3.0, 1.9, 2)]  # swing high
    rows += [bar_factory(1, 1.1, 0.9, 1) for _ in range(3)]
    rows += [bar_factory(1, 1.1, 0.2, 0.5)]  # swing low
    rows += [bar_factory(1, 1.1, 0.9, 1) for _ in range(3)]
    df = df_factory(rows)

    swings = find_swing_points(df, lookback=3)
    kinds = {s.kind for s in swings}
    assert "high" in kinds
    assert "low" in kinds


def test_detect_structure_events_flags_bos_then_choch(bar_factory, df_factory):
    rows = [bar_factory(1, 1.1, 0.9, 1) for _ in range(4)]
    rows += [bar_factory(2, 3.0, 1.9, 2)]  # swing high ~3.0
    rows += [bar_factory(1, 1.1, 0.9, 1) for _ in range(4)]
    rows += [bar_factory(1, 1.1, 0.2, 0.5)]  # swing low ~0.2
    rows += [bar_factory(1, 1.1, 0.9, 1) for _ in range(4)]
    rows += [bar_factory(4, 5.0, 3.9, 4.5)]  # close (4.5) breaks above 3.0 -> BOS bullish
    rows += [bar_factory(1, 1.1, 0.9, 1) for _ in range(4)]
    rows += [bar_factory(0, 0.15, 0.0, 0.05)]  # close (0.05) breaks below 0.2 -> CHoCH bearish
    rows += [bar_factory(1, 1.1, 0.9, 1) for _ in range(4)]
    df = df_factory(rows)

    swings = find_swing_points(df, lookback=3)
    events = detect_structure_events(df, swings)

    assert any(e.event_type == StructureEventType.BOS and e.direction == Direction.BULLISH for e in events)
    assert any(e.event_type == StructureEventType.CHOCH and e.direction == Direction.BEARISH for e in events)
