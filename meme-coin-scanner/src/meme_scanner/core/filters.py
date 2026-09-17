"""Hard cutoffs applied before scoring -- cheap ways to discard obvious noise/scams."""
from __future__ import annotations

from dataclasses import dataclass, field

from meme_scanner.core.models import TokenPair


@dataclass
class ScanFilters:
    chains: list[str] = field(default_factory=list)  # empty = allow every chain
    min_liquidity_usd: float = 0.0
    min_volume_h24_usd: float = 0.0
    max_age_hours: float = float("inf")
    min_txns_h1: int = 0

    def matches(self, pair: TokenPair) -> bool:
        if self.chains and pair.chain_id not in self.chains:
            return False
        if pair.liquidity_usd < self.min_liquidity_usd:
            return False
        if pair.volume_h24 < self.min_volume_h24_usd:
            return False
        if pair.age_hours > self.max_age_hours:
            return False
        if pair.txns_h1.total < self.min_txns_h1:
            return False
        return True


def apply_filters(pairs: list[TokenPair], filters: ScanFilters) -> list[TokenPair]:
    return [p for p in pairs if filters.matches(p)]
