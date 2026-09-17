"""Ties data fetching, filtering, security checks, and scoring into one scan."""
from __future__ import annotations

from dataclasses import dataclass, field

from meme_scanner.core.filters import ScanFilters, apply_filters
from meme_scanner.core.models import TokenPair
from meme_scanner.core.scoring import ScoreResult, ScoringWeights, SecurityThresholds, score_pair
from meme_scanner.data.dexscreener import DexScreenerClient
from meme_scanner.data.goplus import GoPlusClient, SecurityReport

DEFAULT_QUERIES = ["solana meme", "pepe", "dog", "pump.fun", "base meme"]
EVM_CHAINS = {"ethereum", "bsc", "base", "arbitrum", "polygon"}


@dataclass
class ScannerConfig:
    queries: list[str] = field(default_factory=lambda: list(DEFAULT_QUERIES))
    filters: ScanFilters = field(default_factory=ScanFilters)
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    security_thresholds: SecurityThresholds = field(default_factory=SecurityThresholds)
    check_security: bool = True
    top_n: int = 25


class MemeCoinScanner:
    def __init__(
        self,
        config: ScannerConfig | None = None,
        dex_client: DexScreenerClient | None = None,
        security_client: GoPlusClient | None = None,
    ):
        self.config = config or ScannerConfig()
        self.dex_client = dex_client or DexScreenerClient()
        self.security_client = security_client or GoPlusClient()

    def _check_security(self, pair: TokenPair) -> SecurityReport | None:
        if not self.config.check_security or not pair.base_address:
            return None
        try:
            if pair.chain_id == "solana":
                return self.security_client.check_solana_token(pair.base_address)
            if pair.chain_id in EVM_CHAINS:
                return self.security_client.check_evm_token(pair.chain_id, pair.base_address)
        except Exception:
            return None  # a failed security check shouldn't sink the whole scan
        return None

    def scan(self) -> list[ScoreResult]:
        pairs = self.dex_client.scan_queries(self.config.queries)
        candidates = apply_filters(pairs, self.config.filters)

        results = [
            score_pair(
                pair,
                security=self._check_security(pair),
                weights=self.config.weights,
                security_thresholds=self.config.security_thresholds,
            )
            for pair in candidates
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: self.config.top_n]
