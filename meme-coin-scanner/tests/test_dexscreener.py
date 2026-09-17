from __future__ import annotations

from meme_scanner.data.dexscreener import DexScreenerClient


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


def test_search_pairs_parses_response(raw_pair_factory):
    session = FakeSession({"pairs": [raw_pair_factory()]})
    client = DexScreenerClient(session=session)
    results = client.search_pairs("doge")
    assert len(results) == 1
    assert results[0].base_symbol == "DOGEK"
    assert session.calls[0][1] == {"q": "doge"}


def test_search_pairs_handles_no_results():
    session = FakeSession({"pairs": None})
    client = DexScreenerClient(session=session)
    assert client.search_pairs("nonexistent") == []


def test_scan_queries_deduplicates_by_pair(raw_pair_factory):
    session = FakeSession({"pairs": [raw_pair_factory()]})
    client = DexScreenerClient(session=session)
    results = client.scan_queries(["doge", "pepe"])
    assert len(results) == 1


def test_get_pairs_by_token_accepts_list_payload(raw_pair_factory):
    session = FakeSession([raw_pair_factory()])
    client = DexScreenerClient(session=session)
    results = client.get_pairs_by_token("solana", "TOKEN123")
    assert len(results) == 1
