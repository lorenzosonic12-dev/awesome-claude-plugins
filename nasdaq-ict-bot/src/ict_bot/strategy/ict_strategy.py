"""ICT confluence strategy ("2022 model" style): a liquidity sweep, followed
by a change of character, followed by a retracement into an unmitigated
Fair Value Gap or Order Block aligned with the new direction -- optionally
filtered to specific kill zones.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ict_bot.core.fvg import FairValueGap, detect_fvgs
from ict_bot.core.fvg import update_mitigation as mitigate_fvgs
from ict_bot.core.liquidity import LiquiditySweep, detect_liquidity_pools, detect_sweeps
from ict_bot.core.order_blocks import OrderBlock, detect_order_blocks
from ict_bot.core.order_blocks import update_mitigation as mitigate_obs
from ict_bot.core.sessions import in_kill_zone
from ict_bot.core.structure import (
    Direction,
    StructureEvent,
    StructureEventType,
    SwingPoint,
    detect_structure_events,
    find_swing_points,
)
from ict_bot.core.liquidity import LiquidityPool


@dataclass
class MarketContext:
    """Everything the detectors found in one pass over a frame."""

    swings: list[SwingPoint]
    events: list[StructureEvent]
    pools: list[LiquidityPool]
    sweeps: list[LiquiditySweep]
    fvgs: list[FairValueGap]
    order_blocks: list[OrderBlock]


@dataclass
class Signal:
    index: pd.Timestamp
    direction: Direction
    entry: float
    stop: float
    target: float
    reasons: list[str] = field(default_factory=list)

    @property
    def risk_reward(self) -> float:
        risk = abs(self.entry - self.stop)
        reward = abs(self.target - self.entry)
        return reward / risk if risk else 0.0


@dataclass
class ICTStrategyConfig:
    swing_lookback: int = 3
    liquidity_tolerance_pct: float = 0.05
    min_risk_reward: float = 2.0
    kill_zones: tuple[str, ...] = ("ny_am", "london_open", "silver_bullet_am", "silver_bullet_pm")
    require_kill_zone: bool = True
    max_bars_after_choch: int = 20


class ICTStrategy:
    """Detects: sell/buy-side liquidity sweep -> CHoCH -> retrace into an
    unmitigated FVG/order block aligned with the reversal -> (optionally)
    inside a kill zone. Emits a Signal with entry/stop/target and the
    confluence reasons behind it.
    """

    def __init__(self, config: ICTStrategyConfig | None = None) -> None:
        self.config = config or ICTStrategyConfig()

    def build_context(self, df: pd.DataFrame) -> MarketContext:
        """Run every detector once over the frame. Signal generation and live
        analysis both read from this, so the two can never drift apart."""
        cfg = self.config
        swings = find_swing_points(df, lookback=cfg.swing_lookback)
        events = detect_structure_events(df, swings)
        pools = detect_liquidity_pools(swings, tolerance_pct=cfg.liquidity_tolerance_pct)
        sweeps = detect_sweeps(df, pools)
        fvgs = detect_fvgs(df)
        mitigate_fvgs(fvgs, df)
        obs = detect_order_blocks(df, events)
        mitigate_obs(obs, df)
        return MarketContext(
            swings=swings, events=events, pools=pools,
            sweeps=sweeps, fvgs=fvgs, order_blocks=obs,
        )

    def generate_signals(self, df: pd.DataFrame, context: MarketContext | None = None) -> list[Signal]:
        cfg = self.config
        ctx = context if context is not None else self.build_context(df)
        events, pools, sweeps = ctx.events, ctx.pools, ctx.sweeps
        fvgs, obs = ctx.fvgs, ctx.order_blocks

        chochs = [e for e in events if e.event_type == StructureEventType.CHOCH]
        signals: list[Signal] = []

        for choch in chochs:
            sweep = self._preceding_sweep(sweeps, choch)
            if sweep is None:
                continue

            pd_array = self._first_pd_array_after(fvgs, obs, choch, cfg.max_bars_after_choch, df)
            if pd_array is None:
                continue
            array_index, top, bottom, source = pd_array

            if cfg.require_kill_zone and not any(in_kill_zone(array_index, z) for z in cfg.kill_zones):
                continue

            gap_size = top - bottom
            if choch.direction == Direction.BULLISH:
                entry = bottom
                stop = min(sweep.price, bottom) - gap_size * 0.1
                target = self._next_target(pools, entry, Direction.BULLISH, as_of=array_index)
            else:
                entry = top
                stop = max(sweep.price, top) + gap_size * 0.1
                target = self._next_target(pools, entry, Direction.BEARISH, as_of=array_index)

            if target is None:
                continue

            signal = Signal(
                index=array_index,
                direction=choch.direction,
                entry=entry,
                stop=stop,
                target=target,
                reasons=[
                    f"{sweep.pool.side}-side liquidity sweep at {sweep.index}",
                    f"CHoCH ({choch.direction.value}) at {choch.index}",
                    f"{source} retrace at {array_index}",
                ],
            )
            if signal.risk_reward >= cfg.min_risk_reward:
                signals.append(signal)

        signals.sort(key=lambda s: s.index)
        return signals

    @staticmethod
    def _preceding_sweep(sweeps: list[LiquiditySweep], choch: StructureEvent) -> LiquiditySweep | None:
        candidates = [s for s in sweeps if s.index <= choch.index]
        if not candidates:
            return None
        candidates.sort(key=lambda s: s.index)
        best = candidates[-1]
        expected_side = "sell" if choch.direction == Direction.BULLISH else "buy"
        return best if best.pool.side == expected_side else None

    @staticmethod
    def _first_pd_array_after(
        fvgs: list[FairValueGap],
        obs: list[OrderBlock],
        choch: StructureEvent,
        max_bars: int,
        df: pd.DataFrame,
    ) -> tuple[pd.Timestamp, float, float, str] | None:
        """Find a PD array (FVG or order block) that forms in the direction
        of the CHoCH within `max_bars` of it, and has since been retraced
        into (mitigated). The mitigation timestamp is the entry trigger --
        the moment price actually returned to tag the array -- not merely
        the moment the array was left behind.
        """
        pos = df.index.get_indexer([choch.index])[0]
        formation_horizon = set(df.index[pos : min(len(df), pos + max_bars + 1)])

        candidates: list[tuple[pd.Timestamp, float, float, str]] = []
        for gap in fvgs:
            if (
                gap.index in formation_horizon
                and gap.index >= choch.index
                and gap.direction == choch.direction
                and gap.mitigated_at is not None
            ):
                candidates.append((gap.mitigated_at, gap.top, gap.bottom, "FVG"))
        for ob in obs:
            if (
                ob.index in formation_horizon
                and ob.index >= choch.index
                and ob.direction == choch.direction
                and ob.mitigated_at is not None
            ):
                candidates.append((ob.mitigated_at, ob.top, ob.bottom, "order block"))

        if not candidates:
            return None
        candidates.sort(key=lambda c: c[0])
        return candidates[0]

    @staticmethod
    def _next_target(
        pools: list[LiquidityPool],
        entry: float,
        direction: Direction,
        as_of: pd.Timestamp | None = None,
    ) -> float | None:
        """Nearest untouched pool beyond the entry.

        `as_of` restricts the search to pools that already existed and were
        still unswept at that bar. Without it the target could be a pool that
        only formed later in the frame -- invisible at entry time, and pure
        lookahead in a backtest.
        """

        def visible(pool: LiquidityPool) -> bool:
            if as_of is None:
                return not pool.swept
            if max(pool.swing_indices) > as_of:
                return False  # pool hadn't formed yet
            return pool.swept_at is None or pool.swept_at > as_of

        if direction == Direction.BULLISH:
            above = [p.price for p in pools if p.side == "buy" and p.price > entry and visible(p)]
            return min(above) if above else None
        below = [p.price for p in pools if p.side == "sell" and p.price < entry and visible(p)]
        return max(below) if below else None
