from __future__ import annotations

from meme_scanner.utils.config import load_config


def test_load_config_reads_yaml(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
scan:
  queries: [foo, bar]
  chains: [solana]
  min_liquidity_usd: 2500
  top_n: 5
scoring:
  weights:
    liquidity_health: 0.5
    volume_turnover: 0.1
    buy_pressure: 0.1
    momentum: 0.1
    freshness: 0.1
    security: 0.1
security:
  enabled: false
  max_buy_tax_pct: 5
"""
    )
    config = load_config(config_path)
    assert config.queries == ["foo", "bar"]
    assert config.filters.chains == ["solana"]
    assert config.filters.min_liquidity_usd == 2500
    assert config.top_n == 5
    assert config.check_security is False
    assert config.weights.liquidity_health == 0.5
    assert config.security_thresholds.max_buy_tax_pct == 5


def test_load_config_defaults_when_sections_missing(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("scan:\n  min_liquidity_usd: 100\n")
    config = load_config(config_path)
    assert config.filters.min_liquidity_usd == 100
    assert config.check_security is True
    assert config.queries  # falls back to the built-in defaults
