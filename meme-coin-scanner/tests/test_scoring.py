from __future__ import annotations

import time

from meme_scanner.core.models import TokenPair
from meme_scanner.core.scoring import (
    ScoringWeights,
    SecurityThresholds,
    score_buy_pressure,
    score_freshness,
    score_liquidity_health,
    score_pair,
    score_security,
    score_volume_turnover,
)
from meme_scanner.data.goplus import SecurityReport


def test_score_liquidity_health_rewards_liquidity_relative_to_mcap(sample_pair):
    healthy_score = score_liquidity_health(sample_pair)
    sample_pair.liquidity_usd = 500
    thin_score = score_liquidity_health(sample_pair)
    assert thin_score < healthy_score


def test_score_volume_turnover_scales_with_ratio(sample_pair):
    sample_pair.volume_h24 = sample_pair.liquidity_usd
    low = score_volume_turnover(sample_pair)
    sample_pair.volume_h24 = sample_pair.liquidity_usd * 5
    high = score_volume_turnover(sample_pair)
    assert high > low


def test_score_buy_pressure_favors_more_buys(sample_pair):
    sample_pair.txns_h1.buys, sample_pair.txns_h1.sells = 90, 10
    assert score_buy_pressure(sample_pair) == 90.0


def test_score_freshness_peaks_in_first_day():
    now_ms = int(time.time() * 1000)
    fresh = TokenPair.from_dexscreener(
        {"baseToken": {}, "quoteToken": {}, "pairCreatedAt": now_ms - 3_600_000 * 12}
    )
    week_old = TokenPair.from_dexscreener(
        {"baseToken": {}, "quoteToken": {}, "pairCreatedAt": now_ms - 3_600_000 * 24 * 10}
    )
    assert score_freshness(fresh) > score_freshness(week_old)


def test_score_security_zeroes_out_honeypots():
    warnings: list[str] = []
    score = score_security(SecurityReport(is_honeypot=True), warnings, SecurityThresholds())
    assert score == 0.0
    assert any("HONEYPOT" in w for w in warnings)


def test_score_security_penalizes_high_taxes():
    warnings: list[str] = []
    score = score_security(SecurityReport(sell_tax_pct=50.0), warnings, SecurityThresholds())
    assert score < 100
    assert any("sell tax" in w for w in warnings)


def test_score_security_neutral_when_unchecked():
    warnings: list[str] = []
    assert score_security(None, warnings, SecurityThresholds()) == 50.0
    assert any("not checked" in w for w in warnings)


def test_score_pair_combines_subscores_within_bounds(sample_pair):
    result = score_pair(sample_pair, security=None, weights=ScoringWeights())
    assert 0 <= result.score <= 100
    assert set(result.subscores) == {
        "liquidity_health",
        "volume_turnover",
        "buy_pressure",
        "momentum",
        "freshness",
        "security",
    }


def test_score_pair_flags_dust_liquidity(sample_pair):
    sample_pair.liquidity_usd = 200
    result = score_pair(sample_pair)
    assert any("under $1,000" in w for w in result.warnings)
