"""Composite opportunity/risk scoring for a candidate meme coin pair.

Each subscore is 0-100; the final score is a weighted blend. This is a
heuristic, not a prediction -- it surfaces pairs worth a human look and
flags obvious rug-pull red flags, nothing more.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from meme_scanner.core.models import TokenPair
from meme_scanner.data.goplus import SecurityReport


@dataclass
class ScoringWeights:
    liquidity_health: float = 0.25
    volume_turnover: float = 0.20
    buy_pressure: float = 0.20
    momentum: float = 0.15
    freshness: float = 0.10
    security: float = 0.10


@dataclass
class SecurityThresholds:
    max_buy_tax_pct: float = 10.0
    max_sell_tax_pct: float = 10.0
    max_top_holder_pct: float = 30.0


@dataclass
class ScoreResult:
    pair: TokenPair
    score: float
    subscores: dict[str, float]
    warnings: list[str] = field(default_factory=list)


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_liquidity_health(pair: TokenPair) -> float:
    """Liquidity relative to market cap/FDV. Thin liquidity under a big
    market cap is a classic rug setup: little capital is needed to move
    the price, and to pull the liquidity out from under holders."""
    basis = pair.market_cap or pair.fdv
    if pair.liquidity_usd <= 0:
        return 0.0
    if basis <= 0:
        return _clamp(pair.liquidity_usd / 200)  # no mcap data -- fall back to absolute liquidity
    ratio = pair.liquidity_usd / basis
    return _clamp(ratio * 500)  # 20% liquidity/mcap -> 100


def score_volume_turnover(pair: TokenPair) -> float:
    if pair.liquidity_usd <= 0:
        return 0.0
    turnover = pair.volume_h24 / pair.liquidity_usd
    return _clamp(turnover * 40)  # 2.5x liquidity traded per day -> 100


def score_buy_pressure(pair: TokenPair) -> float:
    ratio = pair.txns_h1.buy_ratio if pair.txns_h1.total >= 5 else pair.txns_h24.buy_ratio
    return _clamp(ratio * 100)


def score_momentum(pair: TokenPair) -> float:
    """Reward steady recent gains, but discount a pair that's already
    parabolic today -- more likely near the top than early."""
    score = _clamp(50 + pair.price_change_h1 * 2)
    if pair.price_change_h24 > 500:
        score *= 0.5
    return _clamp(score)


def score_freshness(pair: TokenPair) -> float:
    age = pair.age_hours
    if age <= 1:
        return 60.0  # brand new: interesting but unproven
    if age <= 24:
        return 100.0
    if age <= 72:
        return 70.0
    if age <= 24 * 7:
        return 40.0
    return 15.0


def score_security(
    report: SecurityReport | None,
    warnings: list[str],
    thresholds: SecurityThresholds | None = None,
) -> float:
    thresholds = thresholds or SecurityThresholds()
    if report is None:
        warnings.append("security: not checked")
        return 50.0  # unknown -- neutral, not zero

    if report.is_honeypot:
        warnings.append("security: HONEYPOT detected -- tokens likely can't be sold")
        return 0.0

    score = 100.0
    if report.is_mintable:
        warnings.append("security: mint authority is still active (supply can be inflated)")
        score -= 35
    if report.buy_tax_pct > thresholds.max_buy_tax_pct:
        warnings.append(f"security: high buy tax ({report.buy_tax_pct:.1f}%)")
        score -= 20
    if report.sell_tax_pct > thresholds.max_sell_tax_pct:
        warnings.append(f"security: high sell tax ({report.sell_tax_pct:.1f}%)")
        score -= 25
    if report.top_holder_pct > thresholds.max_top_holder_pct:
        warnings.append(f"security: top 10 holders own {report.top_holder_pct:.1f}% of supply")
        score -= 25
    if report.is_open_source is False:
        warnings.append("security: contract source is not verified")
        score -= 10
    return _clamp(score)


def score_pair(
    pair: TokenPair,
    security: SecurityReport | None = None,
    weights: ScoringWeights | None = None,
    security_thresholds: SecurityThresholds | None = None,
) -> ScoreResult:
    weights = weights or ScoringWeights()
    warnings: list[str] = []

    if 0 < pair.liquidity_usd < 1000:
        warnings.append("liquidity is under $1,000 -- extremely easy to manipulate")

    subscores = {
        "liquidity_health": score_liquidity_health(pair),
        "volume_turnover": score_volume_turnover(pair),
        "buy_pressure": score_buy_pressure(pair),
        "momentum": score_momentum(pair),
        "freshness": score_freshness(pair),
        "security": score_security(security, warnings, security_thresholds),
    }
    total = sum(subscores[name] * getattr(weights, name) for name in subscores)
    return ScoreResult(pair=pair, score=round(_clamp(total), 2), subscores=subscores, warnings=warnings)
