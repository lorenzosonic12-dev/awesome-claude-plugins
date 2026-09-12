"""GoPlus Security API client -- honeypot, tax, and holder-concentration checks.

Free, no API key required. Docs: https://docs.gopluslabs.io/reference/token-security-api
"""
from __future__ import annotations

from dataclasses import dataclass, field

import requests

GOPLUS_EVM_URL = "https://api.gopluslabs.io/api/v1/token_security/{chain_id}"
GOPLUS_SOLANA_URL = "https://api.gopluslabs.io/api/v1/solana/token_security"
DEFAULT_TIMEOUT = 10

# GoPlus's numeric chain IDs for the EVM chains this scanner targets.
EVM_CHAIN_IDS = {
    "ethereum": "1",
    "bsc": "56",
    "base": "8453",
    "arbitrum": "42161",
    "polygon": "137",
}


@dataclass
class SecurityReport:
    is_honeypot: bool = False
    is_open_source: bool | None = None
    is_mintable: bool = False
    buy_tax_pct: float = 0.0
    sell_tax_pct: float = 0.0
    top_holder_pct: float = 0.0
    raw: dict = field(default_factory=dict)


def _top_holder_pct(holders: list[dict], n: int = 10) -> float:
    return sum(float(h.get("percent") or 0) for h in holders[:n]) * 100


class GoPlusClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, session: requests.Session | None = None):
        self.timeout = timeout
        self.session = session or requests.Session()

    def _get(self, url: str, params: dict) -> dict:
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def check_evm_token(self, chain: str, token_address: str) -> SecurityReport | None:
        chain_id = EVM_CHAIN_IDS.get(chain)
        if not chain_id:
            return None
        data = self._get(GOPLUS_EVM_URL.format(chain_id=chain_id), {"contract_addresses": token_address})
        result = (data.get("result") or {}).get(token_address.lower())
        if not result:
            return None
        return SecurityReport(
            is_honeypot=result.get("is_honeypot") == "1",
            is_open_source=result.get("is_open_source") == "1",
            is_mintable=result.get("is_mintable") == "1",
            buy_tax_pct=float(result.get("buy_tax") or 0) * 100,
            sell_tax_pct=float(result.get("sell_tax") or 0) * 100,
            top_holder_pct=_top_holder_pct(result.get("holders") or []),
            raw=result,
        )

    def check_solana_token(self, token_address: str) -> SecurityReport | None:
        data = self._get(GOPLUS_SOLANA_URL, {"contract_addresses": token_address})
        result = (data.get("result") or {}).get(token_address)
        if not result:
            return None
        return SecurityReport(
            is_mintable=(result.get("mintable") or {}).get("status") == "1",
            top_holder_pct=_top_holder_pct(result.get("holders") or []),
            raw=result,
        )
