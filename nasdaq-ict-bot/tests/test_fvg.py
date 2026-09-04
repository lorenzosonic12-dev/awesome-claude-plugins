from __future__ import annotations

from ict_bot.core.fvg import detect_fvgs, update_mitigation
from ict_bot.core.structure import Direction


def test_detect_bullish_fvg(bar_factory, df_factory):
    rows = [
        bar_factory(10, 10.5, 9.5, 10.2),   # c1: high 10.5
        bar_factory(11, 12, 10.8, 11.8),    # displacement candle
        bar_factory(12, 13, 11.5, 12.5),    # c3: low 11.5 > c1 high 10.5 -> bullish gap
    ]
    df = df_factory(rows)
    fvgs = detect_fvgs(df)

    assert len(fvgs) == 1
    gap = fvgs[0]
    assert gap.direction == Direction.BULLISH
    assert gap.bottom == 10.5
    assert gap.top == 11.5


def test_detect_bearish_fvg(bar_factory, df_factory):
    rows = [
        bar_factory(10, 10.5, 9.5, 9.8),
        bar_factory(9, 9.2, 8, 8.2),
        bar_factory(8, 8.8, 7, 7.5),  # c3 high 8.8 < c1 low 9.5 -> bearish gap
    ]
    df = df_factory(rows)
    fvgs = detect_fvgs(df)

    assert len(fvgs) == 1
    gap = fvgs[0]
    assert gap.direction == Direction.BEARISH
    assert gap.top == 9.5
    assert gap.bottom == 8.8


def test_mitigation_marks_gap_filled(bar_factory, df_factory):
    rows = [
        bar_factory(10, 10.5, 9.5, 10.2),
        bar_factory(11, 12, 10.8, 11.8),
        bar_factory(12, 13, 11.5, 12.5),
        bar_factory(12, 12.1, 11.0, 11.2),  # low 11.0 trades back into the gap (bottom 10.5)
    ]
    df = df_factory(rows)
    fvgs = detect_fvgs(df)
    update_mitigation(fvgs, df)

    assert fvgs[0].mitigated is True
    assert fvgs[0].mitigated_at == df.index[3]
    assert fvgs[0].formed_at == df.index[2]
