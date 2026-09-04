"""Renders an AnalysisSnapshot as a terminal panel.

Pure string building -- no I/O, no cursor tricks -- so it can be tested and
so the caller decides whether to stream it, clear the screen, or log it.
"""
from __future__ import annotations

import re

from ict_bot.analysis.analyzer import AnalysisSnapshot, SetupState
from ict_bot.core.sessions import NY_TZ
from ict_bot.core.structure import Direction

WIDTH = 74

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class Palette:
    def __init__(self, color: bool = True) -> None:
        self.on = color

    def _w(self, code: str, text: str) -> str:
        return f"\x1b[{code}m{text}\x1b[0m" if self.on else text

    def dim(self, t: str) -> str:
        return self._w("2", t)

    def bold(self, t: str) -> str:
        return self._w("1", t)

    def amber(self, t: str) -> str:
        return self._w("33", t)

    def green(self, t: str) -> str:
        return self._w("32", t)

    def red(self, t: str) -> str:
        return self._w("31", t)

    def cyan(self, t: str) -> str:
        return self._w("36", t)


def _visible(text: str) -> int:
    return len(_ANSI.sub("", text))


def _pad(text: str, width: int) -> str:
    gap = width - _visible(text)
    return text + " " * max(0, gap)


def render(snap: AnalysisSnapshot, color: bool = True) -> str:
    """Build the full panel for one snapshot."""
    p = Palette(color)
    inner = WIDTH - 2
    lines: list[str] = []

    def row(text: str = "") -> None:
        lines.append("│ " + _pad(text, inner - 2) + " │")

    def rule(label: str = "") -> None:
        if label:
            bar = "─" * max(0, inner - _visible(label) - 1)
            lines.append("├─" + label + bar + "┤")
        else:
            lines.append("├" + "─" * inner + "┤")

    local = snap.timestamp.tz_convert(NY_TZ) if snap.timestamp.tzinfo else snap.timestamp
    stamp = local.strftime("%Y-%m-%d %H:%M ET")
    head = f" {snap.symbol} "
    lines.append("┌─" + head + "─" * max(0, inner - len(head) - len(stamp) - 2) + stamp + " ┐")

    # --- price / trend -------------------------------------------------
    if snap.trend == Direction.BULLISH:
        trend = p.green("▲ bullish")
    elif snap.trend == Direction.BEARISH:
        trend = p.red("▼ bearish")
    else:
        trend = p.dim("— none")
    # Pad the plain text *before* coloring -- f-string width counts the ANSI
    # bytes otherwise, and the columns drift apart only in color mode.
    def label(text: str, width: int = 12) -> str:
        return p.dim(f"{text:<{width}}")

    row(f"{label('LAST')} {p.bold(f'{snap.last_price:<10.2f}')} {label('TREND')} {trend}")

    if snap.dealing_range:
        dr = snap.dealing_range
        span = f"{dr.low:.2f} – {dr.high:.2f}"
        pct = "" if dr.outside else f" {dr.position * 100:.0f}%"
        row(f"{label('RANGE')} {span:<22} {_zone_color(p, dr.zone)}{pct}")
        row(f"{'':<13}{_meter(dr.position, p)}")

    zones = ", ".join(snap.active_zones) if snap.active_zones else "—"
    flag = p.green("● tradeable") if snap.tradeable_zone else p.dim("○ stand down")
    row(f"{label('SESSION')} {zones:<22} {flag}")

    # --- setup ----------------------------------------------------------
    rule(p.dim(" SETUP "))
    state = _state_text(p, snap.setup_state)
    row(f"{state}   {p.dim(f'{snap.gates_passed}/4 gates')}")
    row()
    names = ["sweep", "CHoCH", "PD array", "time + R:R"]
    for (ok, detail), name in zip(snap.gates, names):
        mark = p.green("✓") if ok else p.dim("·")
        label = name if ok else p.dim(name)
        row(f"  {mark} {_pad(label, 14)} {p.dim(detail) if not ok else detail}")

    if snap.signal is not None:
        s = snap.signal
        rule(p.amber(" SIGNAL "))
        arrow = "LONG" if s.direction == Direction.BULLISH else "SHORT"
        row(p.amber(p.bold(f"  {arrow}  entry {s.entry:.2f}   stop {s.stop:.2f}   target {s.target:.2f}")))
        row(p.amber(f"        {s.risk_reward:.2f}R"))

    # --- liquidity -------------------------------------------------------
    rule(p.dim(" RESTING LIQUIDITY "))
    if not snap.buyside and not snap.sellside:
        row(p.dim("  none unswept in range"))
    for lv in snap.buyside:
        row(f"  {p.dim('above'):<12} {lv.price:>9.2f}  {_signed(p, lv.distance_pct):<16} {p.dim(lv.label)}")
    for lv in snap.sellside:
        row(f"  {p.dim('below'):<12} {lv.price:>9.2f}  {_signed(p, lv.distance_pct):<16} {p.dim(lv.label)}")

    # --- arrays ----------------------------------------------------------
    arrays = [(g.direction, g.bottom, g.top, "FVG") for g in snap.unmitigated_fvgs]
    arrays += [(o.direction, o.bottom, o.top, "OB") for o in snap.unmitigated_obs]
    if arrays:
        rule(p.dim(" UNMITIGATED ARRAYS "))
        for direction, bottom, top, kind in arrays[:5]:
            tint = p.green if direction == Direction.BULLISH else p.red
            side = tint("bull" if direction == Direction.BULLISH else "bear")
            row(f"  {p.dim(kind):<10} {side:<14} {bottom:>9.2f} – {top:<9.2f}")

    lines.append("└" + "─" * inner + "┘")
    lines.append(p.dim(f"  {snap.bars} bars analyzed · read-only, no orders placed"))
    return "\n".join(lines)


def _meter(position: float, p: Palette, width: int = 24) -> str:
    """A discount/premium meter with equilibrium marked at the midpoint."""
    filled = int(round(position * (width - 1)))
    cells = []
    for i in range(width):
        if i == filled:
            cells.append(p.bold("●"))
        elif i == width // 2:
            cells.append(p.dim("┊"))
        else:
            cells.append(p.dim("─"))
    return "".join(cells) + p.dim("  premium →")


def _zone_color(p: Palette, zone: str) -> str:
    if zone == "discount":
        return p.green(zone)
    if zone == "premium":
        return p.red(zone)
    return p.dim(zone)


def _signed(p: Palette, pct: float) -> str:
    text = f"{pct:+.2f}%"
    return p.dim(text)


def _state_text(p: Palette, state: SetupState) -> str:
    if state == SetupState.SIGNAL_READY:
        return p.amber(p.bold(f"▸ {state.value.upper()}"))
    if state == SetupState.IDLE:
        return p.dim(f"▸ {state.value}")
    return p.cyan(f"▸ {state.value}")
