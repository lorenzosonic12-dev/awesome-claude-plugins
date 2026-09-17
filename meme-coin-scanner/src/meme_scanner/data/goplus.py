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
    """A check is `None` when GoPlus reported nothing for it.

    That is deliberately not the same as a passing value: GoPlus returns
    empty holder lists, empty LP data and empty tax strings for tokens it
    has not indexed, and reading those as "0% tax, 0% concentration"
    would turn missing data into a clean bill of health -- the most
    dangerous failure mode a rug scanner can have.
    """

    is_honeypot: bool | None = None
    is_open_source: bool | None = None
    is_mintable: bool | None = None
    is_freezable: bool | None = None
    buy_tax_pct: float | None = None
    sell_tax_pct: float | None = None
    top_holder_pct: float | None = None
    lp_locked_pct: float | None = None
    holder_count: int = 0
    raw: dict = field(default_factory=dict)


# Addresses that permanently destroy whatever LP tokens are sent to them.
BURN_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}


def _flag(value: object) -> bool | None:
    """GoPlus booleans arrive as "1"/"0" strings, or not at all."""
    if value in ("1", 1):
        return True
    if value in ("0", 0):
        return False
    return None


def _tax_pct(value: object) -> float | None:
    """Taxes arrive as a 0-1 fraction, or as "" when unreported."""
    if value in (None, ""):
        return None
    return float(value) * 100


def _top_holder_pct(holders: list[dict], n: int = 10) -> float | None:
    if not holders:
        return None
    return sum(float(h.get("percent") or 0) for h in holders[:n]) * 100


def _evm_lp_locked_pct(lp_holders: list[dict]) -> float | None:
    """Share of the LP supply that can never be pulled: locked in a locker
    contract, or burned by sending it to a null address."""
    if not lp_holders:
        return None
    total = 0.0
    for holder in lp_holders:
        address = str(holder.get("address") or "").lower()
        burned = address in BURN_ADDRESSES
        if holder.get("is_locked") == 1 or burned:
            total += float(holder.get("percent") or 0)
    return total * 100


def _solana_lp_burn_pct(dex_pools: list[dict]) -> float | None:
    """Highest LP burn across the token's pools. GoPlus reports this per
    pool and omits it (null) for pool types that have no burnable LP
    token, such as Orca's concentrated positions."""
    reported = [p.get("burn_percent") for p in dex_pools if p.get("burn_percent") is not None]
    if not reported:
        return None
    # Some pools report a 0-1 fraction, others an outright percentage.
    values = [float(v) * 100 if float(v) <= 1 else float(v) for v in reported]
    return min(max(values), 100.0)


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
            is_honeypot=_flag(result.get("is_honeypot")),
            is_open_source=_flag(result.get("is_open_source")),
            is_mintable=_flag(result.get("is_mintable")),
            is_freezable=_flag(result.get("transfer_pausable")),
            buy_tax_pct=_tax_pct(result.get("buy_tax")),
            sell_tax_pct=_tax_pct(result.get("sell_tax")),
            top_holder_pct=_top_holder_pct(result.get("holders") or []),
            lp_locked_pct=_evm_lp_locked_pct(result.get("lp_holders") or []),
            holder_count=int(result.get("holder_count") or 0),
            raw=result,
        )

    def check_solana_token(self, token_address: str) -> SecurityReport | None:
        data = self._get(GOPLUS_SOLANA_URL, {"contract_addresses": token_address})
        result = (data.get("result") or {}).get(token_address)
        if not result:
            return None
        return SecurityReport(
            is_mintable=_flag((result.get("mintable") or {}).get("status")),
            is_freezable=_flag((result.get("freezable") or {}).get("status")),
            top_holder_pct=_top_holder_pct(result.get("holders") or []),
            lp_locked_pct=_solana_lp_burn_pct(result.get("dex") or []),
            holder_count=int(result.get("holder_count") or 0),
            raw=result,
        )
