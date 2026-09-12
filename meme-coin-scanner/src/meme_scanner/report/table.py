"""Plain-text table and CSV export for scan results."""
from __future__ import annotations

import csv

from meme_scanner.core.scoring import ScoreResult


def format_table(results: list[ScoreResult]) -> str:
    headers = ["#", "Chain", "Symbol", "Score", "Price$", "Liq$", "Vol24h$", "1h%", "24h%", "Age(h)", "Warnings"]
    rows = []
    for i, r in enumerate(results, 1):
        p = r.pair
        age = "inf" if p.age_hours == float("inf") else f"{p.age_hours:.1f}"
        rows.append(
            [
                str(i),
                p.chain_id,
                p.base_symbol,
                f"{r.score:.1f}",
                f"{p.price_usd:.6g}",
                f"{p.liquidity_usd:,.0f}",
                f"{p.volume_h24:,.0f}",
                f"{p.price_change_h1:+.1f}",
                f"{p.price_change_h24:+.1f}",
                age,
                "; ".join(r.warnings) or "-",
            ]
        )

    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
        for i in range(len(headers))
    ]
    lines = [" | ".join(h.ljust(w) for h, w in zip(headers, widths))]
    lines.append("-+-".join("-" * w for w in widths))
    for row in rows:
        lines.append(" | ".join(c.ljust(w) for c, w in zip(row, widths)))
    return "\n".join(lines)


def write_csv(results: list[ScoreResult], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "chain", "symbol", "name", "pair_address", "score", "price_usd",
                "liquidity_usd", "volume_h24", "price_change_h1", "price_change_h24",
                "age_hours", "url", "warnings",
            ]
        )
        for r in results:
            p = r.pair
            writer.writerow(
                [
                    p.chain_id, p.base_symbol, p.base_name, p.pair_address, r.score, p.price_usd,
                    p.liquidity_usd, p.volume_h24, p.price_change_h1, p.price_change_h24,
                    p.age_hours, p.url, "; ".join(r.warnings),
                ]
            )
