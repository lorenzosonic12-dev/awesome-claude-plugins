import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { analyzeToken } from "../lib/degenScore.js";
import { generateToken, tickToken } from "../data/tokenFactory.js";
import { seedScan } from "../data/seedTokens.js";

const MAX_TOKENS = 120;
const MAX_FEED_EVENTS = 40;

const seedTokens = seedScan.tokens.map(analyzeToken);

function feedEventFor(token) {
  return {
    id: token.id,
    symbol: token.symbol,
    chain: token.chain,
    score: token.score,
    verdict: token.verdict,
    at: Date.now(),
  };
}

/**
 * Drives the live feed: seeds the table with the real scan, then streams
 * newly created pairs through the security pipeline on an interval.
 *
 * The interval callback only uses functional state updates, so it never
 * closes over stale token arrays.
 */
export function useTokenFeed({ intervalMs = 2600 } = {}) {
  const [tokens, setTokens] = useState(seedTokens);
  const [feed, setFeed] = useState(() => seedTokens.slice(0, 6).map(feedEventFor));
  const [running, setRunning] = useState(true);
  const [scannedCount, setScannedCount] = useState(seedTokens.length);
  const [lastEventAt, setLastEventAt] = useState(Date.now());

  const tickMs = useRef(intervalMs);
  tickMs.current = intervalMs;

  const pushTokens = useCallback((incoming) => {
    setTokens((current) => {
      const aged = current.map((token) => tickToken(token, tickMs.current / 60000));
      return [...incoming, ...aged].slice(0, MAX_TOKENS);
    });
    setFeed((current) => [...incoming.map(feedEventFor), ...current].slice(0, MAX_FEED_EVENTS));
    setScannedCount((count) => count + incoming.length);
    setLastEventAt(Date.now());
  }, []);

  useEffect(() => {
    if (!running) return undefined;

    const id = setInterval(() => {
      // One or two pairs per tick, so the stream feels irregular like a
      // real mempool rather than a metronome.
      const batch = Math.random() < 0.25 ? 2 : 1;
      const incoming = Array.from({ length: batch }, () => analyzeToken(generateToken()));
      pushTokens(incoming);
    }, intervalMs);

    return () => clearInterval(id);
  }, [running, intervalMs, pushTokens]);

  const scanOnce = useCallback(() => {
    pushTokens([analyzeToken(generateToken())]);
  }, [pushTokens]);

  const stats = useMemo(() => {
    const rugAlerts = tokens.filter((t) => t.verdict.id === "rejected").length;
    // "No failures" and "every check verified" are different claims, and
    // conflating them would let a token nobody has indexed read as safe.
    const noFailures = tokens.filter((t) => !t.checks.some((c) => c.status === "fail")).length;
    const fullyVerified = tokens.filter((t) => t.verdict.id === "approved").length;
    const volumeMonitored = tokens.reduce((sum, t) => sum + (t.volumeH24 ?? 0), 0);
    const liquidityMonitored = tokens.reduce((sum, t) => sum + (t.liquidityUsd ?? 0), 0);
    return {
      scanned: scannedCount,
      rugAlerts,
      noFailures,
      fullyVerified,
      volumeMonitored,
      liquidityMonitored,
    };
  }, [tokens, scannedCount]);

  return { tokens, feed, stats, running, setRunning, scanOnce, lastEventAt };
}

export { seedScan };
