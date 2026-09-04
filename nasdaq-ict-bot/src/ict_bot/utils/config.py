"""Load YAML config into typed settings objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ict_bot.live.runner import LiveRunnerConfig
from ict_bot.risk.risk_manager import RiskConfig
from ict_bot.strategy.ict_strategy import ICTStrategyConfig


@dataclass
class AppConfig:
    strategy: ICTStrategyConfig = field(default_factory=ICTStrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    runner: LiveRunnerConfig = field(default_factory=LiveRunnerConfig)
    starting_equity: float = 100_000.0
    broker: str = "paper"
    paper: bool = True


def load_config(path: str | Path) -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    strategy_raw = dict(raw.get("strategy", {}))
    if "kill_zones" in strategy_raw:
        strategy_raw["kill_zones"] = tuple(strategy_raw["kill_zones"])

    return AppConfig(
        strategy=ICTStrategyConfig(**strategy_raw),
        risk=RiskConfig(**raw.get("risk", {})),
        runner=LiveRunnerConfig(**raw.get("runner", {})),
        starting_equity=raw.get("starting_equity", 100_000.0),
        broker=raw.get("broker", "paper"),
        paper=raw.get("paper", True),
    )
