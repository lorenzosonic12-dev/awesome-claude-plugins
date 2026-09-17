import { STATUS, evaluateSecurity, verdictFor } from "./securityRules.js";

const BANDS = [
  { min: 70, id: "safe", label: "SEGURO", tone: "neon" },
  { min: 40, id: "caution", label: "PRECAUCIÓN", tone: "caution" },
  { min: 0, id: "danger", label: "PELIGRO", tone: "danger" },
];

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

/**
 * Market-side adjustment, applied after the security penalties.
 *
 * Thin liquidity under a large market cap is the classic rug setup: little
 * capital is needed to move the price, and to pull the floor out from
 * under holders. Real trading activity earns a small bonus back.
 */
function marketAdjustment(token) {
  let delta = 0;

  const liquidity = token.liquidityUsd ?? 0;
  const marketCap = token.marketCapUsd ?? 0;
  if (liquidity < 5000) delta -= 12;
  else if (liquidity < 15000) delta -= 6;

  if (marketCap > 0 && liquidity > 0) {
    const ratio = liquidity / marketCap;
    if (ratio < 0.02) delta -= 10;
    else if (ratio > 0.15) delta += 5;
  }

  const trades = (token.txnsM5?.buys ?? 0) + (token.txnsM5?.sells ?? 0);
  if (trades >= 25) delta += 4;
  else if (trades === 0) delta -= 4;

  return delta;
}

/**
 * DegenScore: 0-100, where 100 is "nothing in the checklist is wrong".
 * Security failures dominate; market conditions only nudge the result.
 */
export function degenScore(token) {
  const checks = token.checks ?? evaluateSecurity(token.security ?? {});

  if (checks.some((c) => c.id === "honeypot" && c.status === STATUS.FAIL)) {
    return { score: 0, checks, band: BANDS[2], verdict: verdictFor(checks) };
  }

  let score = 100;
  for (const check of checks) {
    if (check.status === STATUS.FAIL) score -= check.weight;
    // Uncertainty is cheaper than a confirmed failure, but never free.
    else if (check.status === STATUS.UNKNOWN) score -= check.weight / 4;
  }

  score = clamp(score + marketAdjustment(token));
  const band = BANDS.find((b) => score >= b.min) ?? BANDS[2];

  return { score: Math.round(score), checks, band, verdict: verdictFor(checks) };
}

/** Attach checks + score to a raw token, the shape the UI consumes. */
export function analyzeToken(token) {
  const checks = evaluateSecurity(token.security ?? {});
  const { score, band, verdict } = degenScore({ ...token, checks });
  return { ...token, checks, score, band, verdict };
}
