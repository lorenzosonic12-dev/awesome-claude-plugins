from __future__ import annotations

from meme_scanner.data.goplus import GoPlusClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return FakeResponse(self.payload)


def test_check_evm_token_parses_flags():
    payload = {
        "result": {
            "0xabc": {
                "is_honeypot": "1",
                "is_open_source": "1",
                "is_mintable": "0",
                "transfer_pausable": "1",
                "buy_tax": "0.05",
                "sell_tax": "0.12",
                "holder_count": "4210",
                "holders": [{"percent": "0.15"}, {"percent": "0.10"}],
            }
        }
    }
    client = GoPlusClient(session=FakeSession(payload))
    report = client.check_evm_token("ethereum", "0xabc")
    assert report is not None
    assert report.is_honeypot is True
    assert report.is_freezable is True
    assert report.buy_tax_pct == 5.0
    assert report.sell_tax_pct == 12.0
    assert round(report.top_holder_pct, 1) == 25.0
    assert report.holder_count == 4210


def test_check_evm_token_counts_locked_and_burned_lp():
    payload = {
        "result": {
            "0xabc": {
                "lp_holders": [
                    {"address": "0xLocker", "is_locked": 1, "percent": "0.70"},
                    {"address": "0x000000000000000000000000000000000000dEaD", "is_locked": 0, "percent": "0.28"},
                    {"address": "0xDeployer", "is_locked": 0, "percent": "0.02"},
                ],
            }
        }
    }
    client = GoPlusClient(session=FakeSession(payload))
    report = client.check_evm_token("ethereum", "0xabc")
    assert round(report.lp_locked_pct, 1) == 98.0  # 70% locked + 28% burned, deployer's 2% excluded


def test_check_evm_token_unknown_chain_returns_none():
    client = GoPlusClient(session=FakeSession({}))
    assert client.check_evm_token("not-a-chain", "0xabc") is None


def test_check_evm_token_missing_result_returns_none():
    client = GoPlusClient(session=FakeSession({"result": {}}))
    assert client.check_evm_token("ethereum", "0xabc") is None


def test_check_solana_token_parses_mint_authority():
    payload = {
        "result": {
            "TOKEN123": {
                "mintable": {"status": "1"},
                "freezable": {"status": "1"},
                "holders": [{"percent": "0.4"}],
            }
        }
    }
    client = GoPlusClient(session=FakeSession(payload))
    report = client.check_solana_token("TOKEN123")
    assert report is not None
    assert report.is_mintable is True
    assert report.is_freezable is True
    assert round(report.top_holder_pct, 1) == 40.0


def test_check_solana_token_takes_best_pool_lp_burn():
    payload = {
        "result": {
            "TOKEN123": {
                "mintable": {"status": "0"},
                "dex": [
                    {"dex_name": "orca", "burn_percent": None},
                    {"dex_name": "raydium", "burn_percent": "100"},
                    {"dex_name": "meteora", "burn_percent": "12"},
                ],
            }
        }
    }
    client = GoPlusClient(session=FakeSession(payload))
    report = client.check_solana_token("TOKEN123")
    assert report.lp_locked_pct == 100.0


def test_solana_lp_burn_accepts_fractional_reporting():
    payload = {"result": {"TOKEN123": {"dex": [{"burn_percent": "0.85"}]}}}
    client = GoPlusClient(session=FakeSession(payload))
    report = client.check_solana_token("TOKEN123")
    assert report.lp_locked_pct == 85.0
