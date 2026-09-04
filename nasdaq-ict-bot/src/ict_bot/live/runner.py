"""Live/paper trading loop: polls fresh bars, evaluates the ICT strategy on
each newly closed candle, and routes qualifying signals through the risk
manager to a broker.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd

from ict_bot.broker.base import Broker
from ict_bot.data.fetcher import fetch_ohlcv
from ict_bot.risk.risk_manager import RiskManager
from ict_bot.strategy.ict_strategy import ICTStrategy
from ict_bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LiveRunnerConfig:
    symbol: str = "QQQ"
    interval: str = "5m"
    lookback_period: str = "5d"
    poll_seconds: int = 60


class LiveRunner:
    def __init__(
        self,
        broker: Broker,
        strategy: ICTStrategy,
        risk_manager: RiskManager,
        config: LiveRunnerConfig | None = None,
    ) -> None:
        self.broker = broker
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.config = config or LiveRunnerConfig()
        self._last_seen: pd.Timestamp | None = None
        self._current_day = None

    def poll_once(self) -> None:
        cfg = self.config
        df = fetch_ohlcv(cfg.symbol, period=cfg.lookback_period, interval=cfg.interval)
        if df.empty:
            return

        latest_ts = df.index[-1]
        if self._current_day != latest_ts.date():
            self._current_day = latest_ts.date()
            self.risk_manager.reset_day()

        if self._last_seen is not None and latest_ts <= self._last_seen:
            return  # no new closed bar yet
        self._last_seen = latest_ts

        equity = self.broker.get_equity()
        if self.risk_manager.is_daily_loss_limit_hit(equity):
            logger.warning("Daily loss limit hit; standing down for %s", self._current_day)
            return
        if not self.risk_manager.can_trade():
            logger.info("Risk manager blocked new trades (open positions / daily cap)")
            return
        if self.broker.get_open_position_count(cfg.symbol) > 0:
            return

        signals = self.strategy.generate_signals(df)
        if not signals or signals[-1].index != latest_ts:
            return

        signal = signals[-1]
        sized = self.risk_manager.size_position(equity, signal.entry, signal.stop)
        if sized.quantity <= 0:
            return

        logger.info(
            "Signal %s %s entry=%.2f stop=%.2f target=%.2f qty=%.2f | %s",
            cfg.symbol,
            signal.direction.value,
            signal.entry,
            signal.stop,
            signal.target,
            sized.quantity,
            "; ".join(signal.reasons),
        )
        result = self.broker.submit_bracket_order(
            cfg.symbol, signal.direction, sized.quantity, signal.entry, signal.stop, signal.target
        )
        self.risk_manager.register_trade_open()
        logger.info("Order submitted: %s (%s)", result.order_id, result.status)

    def run_forever(self) -> None:
        logger.info("Starting live runner for %s @ %s", self.config.symbol, self.config.interval)
        while True:
            try:
                self.poll_once()
            except Exception:
                logger.exception("Error during poll cycle")
            time.sleep(self.config.poll_seconds)
