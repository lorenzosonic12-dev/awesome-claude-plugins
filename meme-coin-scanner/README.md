# Meme Coin Scanner

A Python CLI that scans DEX-traded meme coins (Solana, Ethereum, Base, BSC,
Arbitrum, Polygon) and ranks them with a composite score blending
liquidity health, volume, buy pressure, momentum, freshness, and
automated rug-pull risk checks. Market data comes from
[DexScreener](https://docs.dexscreener.com/api/reference) and security
checks from [GoPlus Security](https://docs.gopluslabs.io/reference/token-security-api)
-- both free, no API key required.

> **Not financial advice.** Meme coins are extremely high risk: most have
> no fundamentals, many are deliberately designed rug pulls or
> honeypots, and a high score here is not a recommendation to buy. This
> tool surfaces candidates and known red flags faster than checking each
> token by hand -- it does not replace your own research, and it cannot
> catch every scam. Never invest more than you can afford to lose
> completely.

## What it checks

| Signal | Module | What it measures |
|---|---|---|
| Liquidity health | `core/scoring.py` | Liquidity vs. market cap -- thin liquidity under a big market cap is a classic rug-pull setup |
| Volume turnover | `core/scoring.py` | 24h volume vs. liquidity -- how actively the pair is trading |
| Buy pressure | `core/scoring.py` | Buys vs. sells in the last hour (falls back to 24h if activity is too thin) |
| Momentum | `core/scoring.py` | Recent price action, discounted if the token is already parabolic (likely near the top) |
| Freshness | `core/scoring.py` | Peaks in the first 24h of a pair's life, decays afterward |
| Security | `data/goplus.py` | Honeypot detection, active mint authority, buy/sell tax, and top-10-holder concentration |

Every result also carries a list of plain-English warnings (e.g. `security:
top 10 holders own 61% of supply`) so a high score is never a black box.

## Project layout

```
meme-coin-scanner/
├── config.yaml              # search queries, filters, scoring weights, security thresholds
├── src/meme_scanner/
│   ├── core/                # TokenPair model, hard filters, composite scoring
│   ├── data/                # DexScreener client, GoPlus Security client
│   ├── report/              # plain-text table + CSV export
│   ├── utils/                # config loading
│   └── scanner.py           # ties data -> filters -> security -> scoring together
├── scripts/scan.py          # CLI entrypoint
└── tests/                   # unit tests for every module (HTTP calls are mocked)
```

## Setup

```bash
cd meme-coin-scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Use the defaults in config.yaml (multiple chains, moderate filters, security checks on)
python scripts/scan.py

# Narrow the search and skip the (slower) GoPlus security calls
python scripts/scan.py --query "pump.fun" --chain solana --no-security-check --top 10

# Only very fresh, reasonably liquid pairs, exported to CSV for further review
python scripts/scan.py --max-age-hours 24 --min-liquidity 20000 --csv fresh.csv
```

Example output:

```
# | Chain  | Symbol | Score | Price$    | Liq$    | Vol24h$ | 1h%  | 24h%   | Age(h) | Warnings
--+--------+--------+-------+-----------+---------+---------+------+--------+--------+---------------------------------------------
1 | solana | PEPE   | 72.8  | 0.0001055 | 29,996  | 45,745  | +4.8 | +154.0 | 388.6  | security: top 10 holders own 60.8% of supply
2 | bsc    | PEPE   | 56.6  | 3.307e-06 | 268,696 | 770,618 | -0.1 | +1.3   | 29088  | security: mint authority is still active
```

CLI flags override `config.yaml` for that run; nothing is written back to
the file. `--query`/`--chain` are repeatable (`--chain solana --chain
base`).

### Configuration

`config.yaml` controls:

- **`scan`** -- search queries, chain allowlist, minimum liquidity/volume,
  maximum pair age, minimum hourly transaction count, and how many
  results to keep.
- **`scoring.weights`** -- how much each subscore (0-100) contributes to
  the final score; should sum to roughly 1.0.
- **`security`** -- whether to run GoPlus checks at all, and the tax/holder
  thresholds that trigger a warning and score penalty.

## Testing

```bash
pytest
```

All tests mock the DexScreener and GoPlus HTTP calls, so the suite runs
fully offline and covers: pair parsing, filters, every scoring
subfunction, both API clients, the end-to-end scan pipeline (including a
failed security check not sinking the scan), and config loading.

## Disclaimer

This scanner applies a heuristic, rules-based score to public on-chain
data -- it is not a prediction of future price movement and does not
guarantee a token is safe even when no warnings are shown (GoPlus doesn't
catch every scam pattern, and a token can turn malicious after being
checked, e.g. via a delayed-trigger contract). Always verify liquidity
locks, contract source, and team reputation independently, and treat any
score here as a starting point for research, not a signal to trade on.
