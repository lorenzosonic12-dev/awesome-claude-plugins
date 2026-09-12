from __future__ import annotations

from meme_scanner.core.filters import ScanFilters
from meme_scanner.core.models import TokenPair
from meme_scanner.data.goplus import SecurityReport
from meme_scanner.scanner import MemeCoinScanner, ScannerConfig


class StubDexClient:
    def __init__(self, pairs):
        self.pairs = pairs

    def scan_queries(self, queries):
        return self.pairs


class StubSecurityClient:
    def __init__(self, report=None):
        self.report = report

    def check_solana_token(self, address):
        return self.report

    def check_evm_token(self, chain, address):
        return self.report


def test_scan_filters_out_thin_liquidity(raw_pair_factory):
    good = TokenPair.from_dexscreener(raw_pair_factory(pairAddress="GOOD"))
    thin = TokenPair.from_dexscreener(raw_pair_factory(pairAddress="THIN", liquidity={"usd": 10}))

    config = ScannerConfig(filters=ScanFilters(min_liquidity_usd=1000), top_n=10)
    scanner = MemeCoinScanner(
        config,
        dex_client=StubDexClient([good, thin]),
        security_client=StubSecurityClient(SecurityReport()),
    )

    results = scanner.scan()

    assert len(results) == 1
    assert results[0].pair.pair_address == "GOOD"


def test_scan_ranks_by_score_descending(raw_pair_factory):
    strong = TokenPair.from_dexscreener(raw_pair_factory(pairAddress="STRONG"))
    weak = TokenPair.from_dexscreener(
        raw_pair_factory(pairAddress="WEAK", liquidity={"usd": 1500}, marketCap=2_000_000)
    )

    config = ScannerConfig(filters=ScanFilters(min_liquidity_usd=1000))
    scanner = MemeCoinScanner(
        config,
        dex_client=StubDexClient([weak, strong]),
        security_client=StubSecurityClient(SecurityReport()),
    )

    results = scanner.scan()

    assert [r.pair.pair_address for r in results] == ["STRONG", "WEAK"]


def test_scan_skips_security_check_when_disabled(raw_pair_factory):
    pair = TokenPair.from_dexscreener(raw_pair_factory())
    config = ScannerConfig(check_security=False)

    class ExplodingSecurityClient:
        def check_solana_token(self, address):
            raise AssertionError("should not be called")

    scanner = MemeCoinScanner(config, dex_client=StubDexClient([pair]), security_client=ExplodingSecurityClient())
    results = scanner.scan()
    assert len(results) == 1


def test_scan_tolerates_security_check_failures(raw_pair_factory):
    pair = TokenPair.from_dexscreener(raw_pair_factory())
    config = ScannerConfig()

    class FailingSecurityClient:
        def check_solana_token(self, address):
            raise ConnectionError("network down")

    scanner = MemeCoinScanner(config, dex_client=StubDexClient([pair]), security_client=FailingSecurityClient())
    results = scanner.scan()
    assert len(results) == 1
    assert any("not checked" in w for w in results[0].warnings)
