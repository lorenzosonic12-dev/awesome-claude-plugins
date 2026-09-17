"""DexScreener API client -- free, no API key required.

Docs: https://docs.dexscreener.com/api/reference
"""
from __future__ import annotations

from typing import Iterable

import requests

from meme_scanner.core.models import TokenPair

BASE_URL = "https://api.dexscreener.com"
DEFAULT_TIMEOUT = 10


class DexScreenerClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = DEFAULT_TIMEOUT, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def search_pairs(self, query: str) -> list[TokenPair]:
        """Free-text search across all indexed DEXs/chains (ticker, name, or address)."""
        data = self._get("/latest/dex/search", params={"q": query})
        pairs = (data.get("pairs") if isinstance(data, dict) else None) or []
        return [TokenPair.from_dexscreener(p) for p in pairs]

    def get_pairs_by_token(self, chain_id: str, token_address: str) -> list[TokenPair]:
        """All pools trading a specific token on a specific chain."""
        data = self._get(f"/token-pairs/v1/{chain_id}/{token_address}")
        pairs = data if isinstance(data, list) else (data.get("pairs") or [])
        return [TokenPair.from_dexscreener(p) for p in pairs]

    def scan_queries(self, queries: Iterable[str]) -> list[TokenPair]:
        """Run several searches and merge results, de-duplicated by (chain, pair address)."""
        seen: dict[str, TokenPair] = {}
        for query in queries:
            for pair in self.search_pairs(query):
                seen[f"{pair.chain_id}:{pair.pair_address}"] = pair
        return list(seen.values())
