"""Live market analysis: a point-in-time read of everything the ICT model
sees right now.

The backtester only ever asks "is there a signal on this bar?". Watching a
market in real time needs the question answered continuously and with its
reasoning exposed -- which pools are still unswept, where the unmitigated
arrays sit, whether we're inside a kill zone, and how far along a setup is.
That's what a snapshot carries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from ict_bot.core.fvg import FairValueGap
from ict_bot.core.liquidity import LiquidityPool, LiquiditySweep
from ict_bot.core.order_blocks import OrderBlock
from ict_bot.core.sessions import active_kill_zones, in_kill_zone
from ict_bot.core.structure import Direction, StructureEvent, StructureEventType
from ict_bot.strategy.ict_strategy import ICTStrategy, MarketContext, Signal


class SetupState(str, Enum):
    """How far the model has progressed toward a tradeable setup."""

    IDLE = "idle"                          # nothing doing
    LIQUIDITY_SWEPT = "liquidity swept"    # stops taken, waiting on structure
    CHOCH_CONFIRMED = "choch confirmed"    # structure flipped against the sweep
    AWAITING_RETRACE = "awaiting retrace"  # array formed, price hasn't tagged it
    ARMED = "armed"                        # array tagged; blocked only on time / R:R
    SIGNAL_READY = "signal ready"          # everything aligned on this bar


@dataclass
class LevelRead:
    """A price level with its distance from spot."""

    price: float
    distance: float          # signed: positive is above spot
    distance_pct: float
    label: str = ""

    @property
    def above(self) -> bool:
        return self.distance > 0


@dataclass
class DealingRange:
    """The swing high/low the model currently treats as the range, and where
    price sits inside it. ICT buys discount and sells premium."""

    high: float
    low: float
    price: float

    @property
    def equilibrium(self) -> float:
        return (self.high + self.low) / 2

    @property
    def position(self) -> float:
        """0.0 at the low, 1.0 at the high. Clamped."""
        span = self.high - self.low
        if span <= 0:
            return 0.5
        return max(0.0, min(1.0, (self.price - self.low) / span))

    @property
    def outside(self) -> bool:
        return self.price > self.high or self.price < self.low

    @property
    def zone(self) -> str:
        # After a displacement leg price often sits beyond the old range
        # entirely; saying "premium 100%" there hides what actually happened.
        if self.price > self.high:
            return "above range"
        if self.price < self.low:
            return "below range"
        pos = self.position
        if pos > 0.55:
            return "premium"
        if pos < 0.45:
            return "discount"
        return "equilibrium"


@dataclass
class AnalysisSnapshot:
    """What the model sees at one moment."""

    timestamp: pd.Timestamp
    symbol: str
    last_price: float
    bars: int

    trend: Direction | None = None
    last_event: StructureEvent | None = None

    active_zones: list[str] = field(default_factory=list)
    tradeable_zone: bool = False

    dealing_range: DealingRange | None = None

    buyside: list[LevelRead] = field(default_factory=list)
    sellside: list[LevelRead] = field(default_factory=list)

    unmitigated_fvgs: list[FairValueGap] = field(default_factory=list)
    unmitigated_obs: list[OrderBlock] = field(default_factory=list)

    recent_sweep: LiquiditySweep | None = None
    last_choch: StructureEvent | None = None

    setup_state: SetupState = SetupState.IDLE
    gates: list[tuple[bool, str]] = field(default_factory=list)
    signal: Signal | None = None

    @property
    def gates_passed(self) -> int:
        return sum(1 for ok, _ in self.gates if ok)


class MarketAnalyzer:
    """Turns a frame of bars into an AnalysisSnapshot. Read-only -- it never
    places or sizes an order, so it's safe to point at a live market."""

    def __init__(self, strategy: ICTStrategy | None = None, symbol: str = "QQQ") -> None:
        self.strategy = strategy or ICTStrategy()
        self.symbol = symbol

    def analyze(self, df: pd.DataFrame) -> AnalysisSnapshot:
        cfg = self.strategy.config
        if df is None or df.empty:
            raise ValueError("cannot analyze an empty frame")

        ts = df.index[-1]
        price = float(df["close"].iloc[-1])
        ctx = self.strategy.build_context(df)

        snap = AnalysisSnapshot(
            timestamp=ts, symbol=self.symbol, last_price=price, bars=len(df)
        )

        # --- structure -------------------------------------------------
        if ctx.events:
            snap.last_event = ctx.events[-1]
            snap.trend = ctx.events[-1].direction
        chochs = [e for e in ctx.events if e.event_type == StructureEventType.CHOCH]
        snap.last_choch = chochs[-1] if chochs else None

        # --- time ------------------------------------------------------
        snap.active_zones = active_kill_zones(ts)
        snap.tradeable_zone = (
            not cfg.require_kill_zone
            or any(in_kill_zone(ts, z) for z in cfg.kill_zones)
        )

        # --- dealing range (premium / discount) ------------------------
        highs = [s for s in ctx.swings if s.kind == "high"]
        lows = [s for s in ctx.swings if s.kind == "low"]
        if highs and lows:
            snap.dealing_range = DealingRange(
                high=highs[-1].price, low=lows[-1].price, price=price
            )

        # --- resting liquidity -----------------------------------------
        snap.buyside = self._levels(
            [p for p in ctx.pools if p.side == "buy" and not p.swept], price
        )
        snap.sellside = self._levels(
            [p for p in ctx.pools if p.side == "sell" and not p.swept], price
        )

        # --- unmitigated arrays ----------------------------------------
        snap.unmitigated_fvgs = sorted(
            (g for g in ctx.fvgs if not g.mitigated),
            key=lambda g: abs((g.top + g.bottom) / 2 - price),
        )[:4]
        snap.unmitigated_obs = sorted(
            (o for o in ctx.order_blocks if not o.mitigated),
            key=lambda o: abs((o.top + o.bottom) / 2 - price),
        )[:4]

        # --- setup progress --------------------------------------------
        snap.recent_sweep = self._recent_sweep(ctx, df, cfg.max_bars_after_choch)
        snap.signal = self._signal_on_last_bar(df, ctx, ts)
        snap.gates = self._gates(snap, ctx, df)
        snap.setup_state = self._state(snap)
        return snap

    # ------------------------------------------------------------------

    @staticmethod
    def _levels(pools: list[LiquidityPool], price: float) -> list[LevelRead]:
        reads = [
            LevelRead(
                price=p.price,
                distance=p.price - price,
                distance_pct=(p.price - price) / price * 100 if price else 0.0,
                label=f"{len(p.swing_indices)} pivots",
            )
            for p in pools
        ]
        reads.sort(key=lambda r: abs(r.distance))
        return reads[:3]

    @staticmethod
    def _recent_sweep(ctx: MarketContext, df: pd.DataFrame, max_bars: int) -> LiquiditySweep | None:
        """The most recent sweep, but only if it's still live context rather
        than something that happened hours ago."""
        if not ctx.sweeps:
            return None
        latest = max(ctx.sweeps, key=lambda s: s.index)
        pos = df.index.get_indexer([latest.index])[0]
        if pos < 0:
            return None
        if (len(df) - 1) - pos > max_bars:
            return None
        return latest

    def _signal_on_last_bar(
        self, df: pd.DataFrame, ctx: MarketContext, ts: pd.Timestamp
    ) -> Signal | None:
        signals = self.strategy.generate_signals(df, context=ctx)
        if signals and signals[-1].index == ts:
            return signals[-1]
        return None

    def _gates(
        self, snap: AnalysisSnapshot, ctx: MarketContext, df: pd.DataFrame
    ) -> list[tuple[bool, str]]:
        """The four strategy gates, each reported with what it's waiting on."""
        cfg = self.strategy.config
        sweep = snap.recent_sweep
        choch = snap.last_choch

        # gate 1 -- a pool was taken recently
        if sweep is not None:
            g1 = (True, f"{sweep.pool.side}-side sweep @ {sweep.price:.2f}")
        else:
            g1 = (False, "no recent liquidity sweep")

        # gate 2 -- structure flipped, and against the side that was swept
        g2 = (False, "no CHoCH since the sweep")
        aligned = False
        if sweep is not None and choch is not None and choch.index >= sweep.index:
            expected = "sell" if choch.direction == Direction.BULLISH else "buy"
            if sweep.pool.side == expected:
                aligned = True
                g2 = (True, f"CHoCH {choch.direction.value} @ {choch.price:.2f}")
            else:
                g2 = (False, f"CHoCH {choch.direction.value} contradicts the sweep side")

        # gate 3 -- an array formed in the new direction and has been tagged
        g3 = (False, "no PD array yet")
        if aligned and choch is not None:
            array = self.strategy._first_pd_array_after(
                ctx.fvgs, ctx.order_blocks, choch, cfg.max_bars_after_choch, df
            )
            if array is not None:
                _, top, bottom, source = array
                g3 = (True, f"{source} {bottom:.2f}-{top:.2f} tagged")
            else:
                pending = self._pending_array(ctx, choch, cfg.max_bars_after_choch, df)
                if pending is not None:
                    top, bottom, source = pending
                    g3 = (False, f"{source} {bottom:.2f}-{top:.2f} awaiting retrace")

        # gate 4 -- time and reward
        if snap.signal is not None:
            g4 = (True, f"{snap.signal.risk_reward:.2f}R in {'/'.join(snap.active_zones) or 'session'}")
        elif not snap.tradeable_zone:
            g4 = (False, "outside configured kill zones")
        else:
            g4 = (False, f"needs >= {cfg.min_risk_reward:.1f}R to a clear pool")

        return [g1, g2, g3, g4]

    @staticmethod
    def _pending_array(
        ctx: MarketContext, choch: StructureEvent, max_bars: int, df: pd.DataFrame
    ) -> tuple[float, float, str] | None:
        """An array formed in the CHoCH's direction that price hasn't tagged
        yet -- the thing the model is actively waiting on."""
        pos = df.index.get_indexer([choch.index])[0]
        if pos < 0:
            return None
        horizon = set(df.index[pos : min(len(df), pos + max_bars + 1)])

        best: tuple[pd.Timestamp, float, float, str] | None = None
        for gap in ctx.fvgs:
            if gap.index in horizon and gap.direction == choch.direction and not gap.mitigated:
                if best is None or gap.index < best[0]:
                    best = (gap.index, gap.top, gap.bottom, "FVG")
        for ob in ctx.order_blocks:
            if ob.index in horizon and ob.direction == choch.direction and not ob.mitigated:
                if best is None or ob.index < best[0]:
                    best = (ob.index, ob.top, ob.bottom, "order block")
        if best is None:
            return None
        return best[1], best[2], best[3]

    @staticmethod
    def _state(snap: AnalysisSnapshot) -> SetupState:
        """Which gate the setup is currently stalled at."""
        if snap.signal is not None:
            return SetupState.SIGNAL_READY

        ok = [passed for passed, _ in snap.gates]
        if not ok or not ok[0]:
            return SetupState.IDLE
        if not ok[1]:
            return SetupState.LIQUIDITY_SWEPT
        if ok[2]:
            # structure is complete; only the time window or reward is missing
            return SetupState.ARMED
        if "awaiting retrace" in snap.gates[2][1]:
            return SetupState.AWAITING_RETRACE
        return SetupState.CHOCH_CONFIRMED
