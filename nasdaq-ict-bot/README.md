# NASDAQ ICT Trading Bot

A Python trading bot for NASDAQ instruments (QQQ / NQ futures / ^NDX) built
around **ICT (Inner Circle Trader)** price-action concepts: market
structure, liquidity, imbalances, and time-of-day. It includes a
backtester and a paper/live trading loop.

> **Not financial advice.** This is an educational implementation of a
> discretionary trading methodology, translated into rules a computer can
> evaluate. Markets are not guaranteed to behave the way any model
> predicts. Backtest thoroughly, paper trade extensively, and never risk
> money you can't afford to lose. Trading equities/futures carries
> substantial risk of loss.

## ICT concepts implemented

| Concept | Module | What it detects |
|---|---|---|
| Market structure | `core/structure.py` | Swing highs/lows, **BOS** (break of structure — trend continuation) and **CHoCH** (change of character — first break against the trend) |
| Fair Value Gaps | `core/fvg.py` | Three-candle imbalances left behind by a displacement move, and when price later "mitigates" (fills) them |
| Order Blocks | `core/order_blocks.py` | The last opposite-colored candle before a structure-breaking displacement |
| Liquidity | `core/liquidity.py` | Equal highs/lows (resting liquidity pools) and **sweeps** (a wick through the pool that closes back — the "stop hunt") |
| Kill zones | `core/sessions.py` | London open, NY AM, NY lunch, London close, and the AM/PM "Silver Bullet" windows, in NY local time |

## Strategy

`strategy/ict_strategy.py` combines the above into one confluence model,
similar to ICT's "2022 model":

1. **Liquidity sweep** — price takes out sell-side (or buy-side) resting
   liquidity.
2. **CHoCH** — structure breaks in the opposite direction, suggesting the
   sweep was a stop hunt ahead of a reversal.
3. **Retracement into a PD array** — a Fair Value Gap or Order Block forms
   in the new direction, and price actually returns to tag it (the entry
   trigger).
4. **Kill zone filter** (optional) — the entry must fall inside a
   configured session window.

Each signal carries an entry, a stop beyond the sweep/array, a target at
the next untouched liquidity pool, and is only emitted if it clears a
minimum risk:reward (default 2R).

## Project layout

```
nasdaq-ict-bot/
├── config.yaml              # strategy / risk / runner configuration
├── .env.example             # Alpaca API key template
├── src/ict_bot/
│   ├── core/                # structure, FVG, order blocks, liquidity, sessions
│   ├── strategy/            # ICT confluence strategy -> Signal objects
│   ├── analysis/            # live read: analyzer, setup states, terminal panel
│   ├── risk/                # position sizing, daily loss limit, trade caps
│   ├── backtest/            # bar-by-bar simulation + performance metrics
│   ├── data/                # yfinance polling, Alpaca history, live bar stream
│   ├── broker/              # Broker interface: PaperBroker, AlpacaBroker
│   ├── live/                # polling loop that ties strategy -> risk -> broker
│   └── utils/                # config loading, logging
├── scripts/
│   ├── run_analyzer.py      # watch a live market (read-only)
│   ├── run_backtest.py
│   └── run_live.py
└── tests/                    # unit tests for every core module
```

## Real-time analysis

The analyzer watches a live market and shows you the model's read as it
changes, bar by bar. It is **read-only** — it constructs no broker and can
place no order.

```bash
# live streaming bars from Alpaca (free IEX feed; needs .env keys)
python scripts/run_analyzer.py --source alpaca --symbol QQQ

# delayed polling via yfinance, no account required
python scripts/run_analyzer.py --source yfinance --symbol QQQ

# replay recent history bar by bar — works outside market hours
python scripts/run_analyzer.py --source replay --period 5d
```

```
┌─ QQQ ──────────────────────────────────────────────2024-01-02 07:50 ET ┐
│ LAST         102.60     TREND        ▲ bullish                         │
│ RANGE        99.40 – 102.00         above range                        │
│ SESSION      ny_am                  ● tradeable                        │
├─ SETUP ────────────────────────────────────────────────────────────────┤
│ ▸ SIGNAL READY   4/4 gates                                             │
│   ✓ sweep          sell-side sweep @ 99.40                             │
│   ✓ CHoCH          CHoCH bullish @ 104.00                              │
│   ✓ PD array       FVG 101.20-102.50 tagged                            │
│   ✓ time + R:R     2.49R in ny_am                                      │
├─ SIGNAL ───────────────────────────────────────────────────────────────┤
│   LONG  entry 101.20   stop 99.27   target 106.01                      │
└────────────────────────────────────────────────────────────────────────┘
```

The setup state machine is the point: rather than only reporting a
finished signal, it tells you which gate the market is currently stalled
at, so you can see a setup building.

| State | Meaning |
|---|---|
| `idle` | no recent liquidity sweep |
| `liquidity swept` | stops taken, waiting on structure to flip |
| `choch confirmed` | structure flipped against the sweep, no array yet |
| `awaiting retrace` | array formed, price hasn't come back to tag it |
| `armed` | array tagged; blocked only on kill zone or R:R |
| `signal ready` | all four gates pass on this bar |

### Where the data comes from

`--source alpaca` opens a WebSocket to Alpaca, receives 1-minute bars and
rolls them up locally into the configured interval, emitting a bar only
once its window has closed — the model never analyzes a partial candle.
History is seeded from Alpaca's own bars so the stream and the seed come
from one venue.

`--source yfinance` needs no account but returns delayed snapshots. It's
fine for watching mechanics, not for acting on.

## Setup

```bash
cd nasdaq-ict-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # only needed for --broker alpaca
```

## Backtesting

```bash
python scripts/run_backtest.py --symbol QQQ --period 60d --interval 5m
```

Prints trade count, win rate, profit factor, total PnL, max drawdown, and
average planned risk:reward. `--period`/`--interval` follow yfinance's
conventions (intraday intervals like `5m` are limited to the last ~60 days
by Yahoo Finance).

Tune the strategy/risk parameters in `config.yaml` (kill zones, minimum
RR, liquidity tolerance, risk per trade, daily loss cap, etc.) — the
backtest script picks it up automatically if present.

## Paper / live trading

```bash
# Dry run against an in-memory paper broker (default, no external account)
python scripts/run_live.py --broker paper

# Paper trade for real against Alpaca's paper endpoint (needs .env keys)
python scripts/run_live.py --broker alpaca

# Live trading with real money -- requires an explicit typed confirmation
python scripts/run_live.py --broker alpaca --live
```

Alpaca doesn't offer CME NASDAQ futures, so the Alpaca backend trades an
equity/ETF proxy (QQQ by default, configurable in `config.yaml` under
`runner.symbol`). To trade the actual NQ futures contract you'd implement
a new `Broker` subclass against a futures-capable API (e.g. Interactive
Brokers) using the same `Broker` interface in `broker/base.py`.

The live runner polls for newly closed bars, re-runs the strategy, and
only acts on a signal that fires on the bar that just closed — it never
places an order to fix duplicate signals it's already seen. Risk
guardrails (max open positions, max trades/day, daily loss circuit
breaker) are enforced the same way in both backtest and live modes since
both go through the same `RiskManager`.

## Testing

```bash
pytest
```

Unit tests cover swing/structure detection, FVGs, order blocks, liquidity
pools/sweeps, kill zone timing, risk sizing, and an end-to-end strategy
smoke test.

## Disclaimer

ICT concepts are a discretionary, pattern-based trading methodology, not
a mathematically proven edge. This implementation is a best-effort,
rules-based approximation for research and educational purposes. Past
backtest performance does not guarantee future results. Use paper trading
to validate any configuration extensively before risking real capital,
and never disable the risk guardrails in `risk/risk_manager.py`.
