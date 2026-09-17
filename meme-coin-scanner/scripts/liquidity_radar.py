#!/usr/bin/env python
"""CLI: measure meme coin liquidity velocity by sampling DexScreener twice.

Takes two live readings `--interval-seconds` apart (default 90s) and
reports which pairs' liquidity is moving fastest. Rapid inflow can
precede a pump (fresh capital locking in); rapid outflow is the
signature of a liquidity pull / rug in progress.

Example:
    python scripts/liquidity_radar.py --chain solana --interval-seconds 90 --top 25 --out snapshot.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from meme_scanner.core.filters import ScanFilters, apply_filters  # noqa: E402
from meme_scanner.core.models import TokenPair  # noqa: E402
from meme_scanner.core.velocity import VelocityResult, compute_all_velocities, snapshot_map  # noqa: E402
from meme_scanner.data.dexscreener import DexScreenerClient  # noqa: E402

DEFAULT_QUERIES = ["solana meme", "pepe", "dog", "pump.fun", "base meme"]


def result_to_json(result: VelocityResult) -> dict:
    p = result.pair
    return {
        "chain": p.chain_id,
        "dex": p.dex_id,
        "symbol": p.base_symbol,
        "name": p.base_name,
        "pair_address": p.pair_address,
        "url": p.url,
        "price_usd": p.price_usd,
        "liquidity_usd": result.curr_liquidity_usd,
        "prev_liquidity_usd": result.prev_liquidity_usd,
        "delta_usd": result.delta_usd,
        "delta_pct": result.delta_pct,
        "usd_per_minute": result.usd_per_minute,
        "elapsed_minutes": result.elapsed_minutes,
        "direction": result.direction,
        "is_rapid": result.is_rapid,
        "volume_h24": p.volume_h24,
        "price_change_h1": p.price_change_h1,
        "age_hours": None if p.age_hours == float("inf") else round(p.age_hours, 1),
    }


def sample(client: DexScreenerClient, queries: list[str], filters: ScanFilters) -> list[TokenPair]:
    return apply_filters(client.scan_queries(queries), filters)


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure meme coin liquidity velocity")
    parser.add_argument("--query", action="append", dest="queries", default=None)
    parser.add_argument("--chain", action="append", dest="chains", default=None)
    parser.add_argument("--min-liquidity", type=float, default=5000)
    parser.add_argument("--min-volume", type=float, default=1000)
    parser.add_argument("--max-age-hours", type=float, default=24 * 14)
    parser.add_argument("--interval-seconds", type=float, default=90)
    parser.add_argument("--rapid-pct-per-min", type=float, default=1.5)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--out", default=None, help="Also write the JSON payload to this path")
    args = parser.parse_args()

    queries = args.queries or DEFAULT_QUERIES
    filters = ScanFilters(
        chains=args.chains or [],
        min_liquidity_usd=args.min_liquidity,
        min_volume_h24_usd=args.min_volume,
        max_age_hours=args.max_age_hours,
    )
    client = DexScreenerClient()

    baseline_pairs = sample(client, queries, filters)
    baseline_ts = time.time()
    baseline_snapshots = snapshot_map(baseline_pairs, baseline_ts)

    print(
        f"Sampled {len(baseline_pairs)} pairs, waiting {args.interval_seconds:.0f}s for a second reading...",
        file=sys.stderr,
    )
    time.sleep(args.interval_seconds)

    current_pairs = sample(client, queries, filters)
    now_ts = time.time()

    velocities = compute_all_velocities(current_pairs, baseline_snapshots, now_ts, rapid_pct_per_min=args.rapid_pct_per_min)
    velocities.sort(key=lambda v: abs(v.delta_pct) / max(v.elapsed_minutes, 0.01), reverse=True)
    top = velocities[: args.top]

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts)),
        "interval_seconds": args.interval_seconds,
        "rapid_pct_per_min_threshold": args.rapid_pct_per_min,
        "queries": queries,
        "chains": filters.chains,
        "pairs_sampled": len(current_pairs),
        "results": [result_to_json(v) for v in top],
    }

    output = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(output)
        print(f"Wrote {len(top)} result(s) to {args.out}", file=sys.stderr)
    print(output)


if __name__ == "__main__":
    main()
