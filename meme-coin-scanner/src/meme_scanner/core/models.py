"""Typed representation of a DexScreener trading pair."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Txns:
    buys: int = 0
    sells: int = 0

    @property
    def total(self) -> int:
        return self.buys + self.sells

    @property
    def buy_ratio(self) -> float:
        """Fraction of transactions that were buys; 0.5 (neutral) when there's no data."""
        return self.buys / self.total if self.total else 0.5


@dataclass
class TokenPair:
    chain_id: str
    dex_id: str
    pair_address: str
    base_symbol: str
    base_name: str
    base_address: str
    quote_symbol: str
    price_usd: float
    liquidity_usd: float
    fdv: float
    market_cap: float
    volume_h24: float
    volume_h6: float
    volume_h1: float
    price_change_h1: float
    price_change_h24: float
    txns_h1: Txns
    txns_h24: Txns
    pair_created_at_ms: int | None
    url: str

    @property
    def age_hours(self) -> float:
        if not self.pair_created_at_ms:
            return float("inf")
        return (time.time() * 1000 - self.pair_created_at_ms) / 3_600_000

    @classmethod
    def from_dexscreener(cls, raw: dict) -> "TokenPair":
        """Build a TokenPair from one entry of DexScreener's `pairs` array."""
        base = raw.get("baseToken") or {}
        quote = raw.get("quoteToken") or {}
        liquidity = raw.get("liquidity") or {}
        volume = raw.get("volume") or {}
        price_change = raw.get("priceChange") or {}
        txns = raw.get("txns") or {}

        def _txns(period: str) -> Txns:
            d = txns.get(period) or {}
            return Txns(buys=int(d.get("buys") or 0), sells=int(d.get("sells") or 0))

        return cls(
            chain_id=raw.get("chainId", ""),
            dex_id=raw.get("dexId", ""),
            pair_address=raw.get("pairAddress", ""),
            base_symbol=base.get("symbol", "?"),
            base_name=base.get("name", "?"),
            base_address=base.get("address", ""),
            quote_symbol=quote.get("symbol", "?"),
            price_usd=float(raw.get("priceUsd") or 0.0),
            liquidity_usd=float(liquidity.get("usd") or 0.0),
            fdv=float(raw.get("fdv") or 0.0),
            market_cap=float(raw.get("marketCap") or 0.0),
            volume_h24=float(volume.get("h24") or 0.0),
            volume_h6=float(volume.get("h6") or 0.0),
            volume_h1=float(volume.get("h1") or 0.0),
            price_change_h1=float(price_change.get("h1") or 0.0),
            price_change_h24=float(price_change.get("h24") or 0.0),
            txns_h1=_txns("h1"),
            txns_h24=_txns("h24"),
            pair_created_at_ms=raw.get("pairCreatedAt"),
            url=raw.get("url", ""),
        )
