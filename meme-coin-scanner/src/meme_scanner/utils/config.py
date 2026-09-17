"""Load YAML config into typed settings objects."""
from __future__ import annotations

from pathlib import Path

import yaml

from meme_scanner.core.filters import ScanFilters
from meme_scanner.core.scoring import ScoringWeights, SecurityThresholds
from meme_scanner.scanner import ScannerConfig


def load_config(path: str | Path) -> ScannerConfig:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    scan_raw = dict(raw.get("scan", {}))
    filters = ScanFilters(
        chains=list(scan_raw.get("chains", []) or []),
        min_liquidity_usd=scan_raw.get("min_liquidity_usd", 0.0),
        min_volume_h24_usd=scan_raw.get("min_volume_h24_usd", 0.0),
        max_age_hours=scan_raw.get("max_age_hours", float("inf")),
        min_txns_h1=scan_raw.get("min_txns_h1", 0),
    )

    weights = ScoringWeights(**dict(raw.get("scoring", {}).get("weights", {})))

    security_raw = dict(raw.get("security", {}))
    thresholds = SecurityThresholds(
        **{k: v for k, v in security_raw.items() if k in SecurityThresholds.__dataclass_fields__}
    )

    default_queries = ScannerConfig().queries
    return ScannerConfig(
        queries=list(scan_raw.get("queries") or default_queries),
        filters=filters,
        weights=weights,
        security_thresholds=thresholds,
        check_security=security_raw.get("enabled", True),
        top_n=scan_raw.get("top_n", 25),
    )
