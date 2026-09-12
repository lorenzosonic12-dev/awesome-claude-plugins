from __future__ import annotations

import time

import pytest

from meme_scanner.core.models import TokenPair


def make_raw_pair(**overrides) -> dict:
    now_ms = int(time.time() * 1000)
    raw = {
        "chainId": "solana",
        "dexId": "raydium",
        "pairAddress": "PAIR123",
        "url": "https://dexscreener.com/solana/pair123",
        "baseToken": {"address": "TOKEN123", "name": "Doge Killer", "symbol": "DOGEK"},
        "quoteToken": {"address": "So11111111111111111111111111111111111111112", "symbol": "SOL"},
        "priceUsd": "0.00042",
        "liquidity": {"usd": 50000},
        "fdv": 500000,
        "marketCap": 400000,
        "volume": {"h24": 120000, "h6": 40000, "h1": 8000},
        "priceChange": {"h1": 5.2, "h24": 34.1},
        "txns": {
            "h1": {"buys": 40, "sells": 20},
            "h24": {"buys": 500, "sells": 300},
        },
        "pairCreatedAt": now_ms - 6 * 3_600_000,  # 6h old
    }
    raw.update(overrides)
    return raw


@pytest.fixture
def raw_pair_factory():
    return make_raw_pair


@pytest.fixture
def sample_pair() -> TokenPair:
    return TokenPair.from_dexscreener(make_raw_pair())
