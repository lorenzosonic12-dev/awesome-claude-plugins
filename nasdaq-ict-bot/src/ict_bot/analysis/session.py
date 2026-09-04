"""The live analysis session: seed history, consume bars, re-analyze on every
close, and hand the snapshot to whatever wants to render or act on it.

Deliberately independent of the broker. Analysis is read-only; the trading
loop in live/runner.py is a separate thing you have to opt into.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from ict_bot.analysis.analyzer import AnalysisSnapshot, MarketAnalyzer, SetupState
from ict_bot.data.stream import Bar, RollingFrame
from ict_bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AnalysisSessionConfig:
    symbol: str = "QQQ"
    interval: str = "5m"
    max_bars: int = 500
    min_bars: int = 30  # detectors need history before they say anything


class AnalysisSession:
    """Holds the rolling frame and re-runs the model on each closed bar."""

    def __init__(
        self,
        analyzer: MarketAnalyzer,
        seed: pd.DataFrame | None = None,
        config: AnalysisSessionConfig | None = None,
        on_snapshot: Callable[[AnalysisSnapshot], None] | None = None,
    ) -> None:
        self.config = config or AnalysisSessionConfig()
        self.analyzer = analyzer
        self.frame = RollingFrame(seed, max_bars=self.config.max_bars)
        self.on_snapshot = on_snapshot
        self.last_snapshot: AnalysisSnapshot | None = None
        self._last_state: SetupState | None = None

    def handle_bar(self, bar: Bar) -> AnalysisSnapshot | None:
        """Append a closed bar and re-analyze. Returns None while the frame is
        still too short for the detectors to mean anything."""
        self.frame.append(bar)
        return self.refresh()

    def refresh(self) -> AnalysisSnapshot | None:
        if len(self.frame) < self.config.min_bars:
            logger.debug(
                "warming up: %d/%d bars", len(self.frame), self.config.min_bars
            )
            return None

        snapshot = self.analyzer.analyze(self.frame.frame)
        self.last_snapshot = snapshot

        if snapshot.setup_state != self._last_state:
            logger.info(
                "%s setup: %s -> %s (%d/4 gates)",
                snapshot.symbol,
                self._last_state.value if self._last_state else "—",
                snapshot.setup_state.value,
                snapshot.gates_passed,
            )
            self._last_state = snapshot.setup_state

        if snapshot.signal is not None:
            s = snapshot.signal
            logger.info(
                "SIGNAL %s %s entry=%.2f stop=%.2f target=%.2f (%.2fR)",
                snapshot.symbol, s.direction.value, s.entry, s.stop, s.target, s.risk_reward,
            )

        if self.on_snapshot is not None:
            self.on_snapshot(snapshot)
        return snapshot

    def replay(self, df: pd.DataFrame) -> list[AnalysisSnapshot]:
        """Feed a historical frame through bar by bar, as if it were live.

        Lets you watch how the read evolved across a past session, and is the
        way to sanity-check the analyzer without waiting on market hours.
        """
        snapshots: list[AnalysisSnapshot] = []
        for ts, row in df.iterrows():
            bar = Bar(
                timestamp=ts,
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]),
                volume=float(row.get("volume", 0.0)),
            )
            snap = self.handle_bar(bar)
            if snap is not None:
                snapshots.append(snap)
        return snapshots
