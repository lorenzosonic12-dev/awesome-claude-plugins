#!/usr/bin/env python
"""CLI: scan DEXs for meme coins and rank them by an opportunity/risk score.

Example:
    python scripts/scan.py --chain solana --query pump --min-liquidity 10000 --top 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from meme_scanner.report.table import format_table, write_csv  # noqa: E402
from meme_scanner.scanner import MemeCoinScanner, ScannerConfig  # noqa: E402
from meme_scanner.utils.config import load_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan DEXs for meme coin opportunities")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--query", action="append", dest="queries", help="Search term, repeatable (default: from config.yaml)")
    parser.add_argument("--chain", action="append", dest="chains", help="Restrict to chain(s), e.g. solana, ethereum, base")
    parser.add_argument("--min-liquidity", type=float, default=None)
    parser.add_argument("--min-volume", type=float, default=None)
    parser.add_argument("--max-age-hours", type=float, default=None)
    parser.add_argument("--min-txns-h1", type=int, default=None)
    parser.add_argument("--top", type=int, default=None)
    parser.add_argument(
        "--no-security-check",
        action="store_true",
        help="Skip GoPlus honeypot/tax/holder checks (faster, less safe)",
    )
    parser.add_argument("--csv", default=None, help="Also write full results to this CSV path")
    args = parser.parse_args()

    config = load_config(args.config) if Path(args.config).exists() else ScannerConfig()

    if args.queries:
        config.queries = args.queries
    if args.chains:
        config.filters.chains = args.chains
    if args.min_liquidity is not None:
        config.filters.min_liquidity_usd = args.min_liquidity
    if args.min_volume is not None:
        config.filters.min_volume_h24_usd = args.min_volume
    if args.max_age_hours is not None:
        config.filters.max_age_hours = args.max_age_hours
    if args.min_txns_h1 is not None:
        config.filters.min_txns_h1 = args.min_txns_h1
    if args.top is not None:
        config.top_n = args.top
    if args.no_security_check:
        config.check_security = False

    results = MemeCoinScanner(config).scan()

    if not results:
        print("No pairs matched the current filters.")
        return

    print(format_table(results))
    print(f"\n{len(results)} pair(s) shown, ranked by liquidity health, volume, buy pressure,")
    print("momentum, freshness, and (when enabled) GoPlus security checks. Not financial advice --")
    print("meme coins are extremely high risk; always verify independently before trading.")

    if args.csv:
        write_csv(results, args.csv)
        print(f"\nFull results written to {args.csv}")


if __name__ == "__main__":
    main()
