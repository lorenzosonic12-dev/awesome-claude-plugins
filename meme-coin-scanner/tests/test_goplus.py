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
                "buy_tax": "0.05",
                "sell_tax": "0.12",
                "holders": [{"percent": "0.15"}, {"percent": "0.10"}],
            }
        }
    }
    client = GoPlusClient(session=FakeSession(payload))
    report = client.check_evm_token("ethereum", "0xabc")
    assert report is not None
    assert report.is_honeypot is True
    assert report.buy_tax_pct == 5.0
    assert report.sell_tax_pct == 12.0
    assert round(report.top_holder_pct, 1) == 25.0


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
                "holders": [{"percent": "0.4"}],
            }
        }
    }
    client = GoPlusClient(session=FakeSession(payload))
    report = client.check_solana_token("TOKEN123")
    assert report is not None
    assert report.is_mintable is True
    assert round(report.top_holder_pct, 1) == 40.0
