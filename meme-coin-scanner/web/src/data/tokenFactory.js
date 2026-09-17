/**
 * Synthetic new-pair generator for the live feed.
 *
 * The seeded rows in the table come from a real scan; this factory stands
 * in for the websocket of newly created DEX pairs, which needs a paid
 * provider key. Everything it emits is tagged `source: "sim"` so the UI
 * can label it and never pass it off as scanned data.
 *
 * The distributions are deliberately pessimistic: most brand-new meme
 * pairs fail at least one security check, which is what makes watching
 * the pipeline reject them interesting.
 */

import { CHAINS } from "../lib/chains.js";

const PREFIXES = [
  "Turbo", "Baby", "Mega", "Giga", "Hyper", "Based", "Quantum", "Cosmic",
  "Golden", "Silent", "Neon", "Feral", "Rogue", "Astro", "Retro",
];
const CORES = [
  "Doge", "Pepe", "Shiba", "Cat", "Wojak", "Chad", "Frog", "Monke", "Bonk",
  "Wif", "Floki", "Hamster", "Penguin", "Capybara", "Llama", "Axolotl",
];
const SUFFIXES = ["Inu", "Coin", "Protocol", "Finance", "Labs", "AI", "2.0", "Classic", "X"];

const B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
const HEX = "0123456789abcdef";

// Weighted so Solana dominates, roughly matching where new meme pairs launch.
const CHAIN_WEIGHTS = [
  ["solana", 0.55],
  ["base", 0.24],
  ["ethereum", 0.12],
  ["bsc", 0.09],
];

let sequence = 0;

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

/** Log-uniform draw: meme pair sizes span orders of magnitude. */
function logUniform(min, max) {
  return Math.exp(randomBetween(Math.log(min), Math.log(max)));
}

function chance(probability) {
  return Math.random() < probability;
}

function weightedChain() {
  const roll = Math.random();
  let cumulative = 0;
  for (const [chain, weight] of CHAIN_WEIGHTS) {
    cumulative += weight;
    if (roll <= cumulative) return chain;
  }
  return "solana";
}

function randomAddress(chain) {
  if (chain === "solana") {
    let out = "";
    for (let i = 0; i < 44; i += 1) out += pick(B58.split(""));
    return out;
  }
  let out = "0x";
  for (let i = 0; i < 40; i += 1) out += pick(HEX.split(""));
  return out;
}

function randomName() {
  const roll = Math.random();
  if (roll < 0.35) return `${pick(PREFIXES)} ${pick(CORES)}`;
  if (roll < 0.75) return `${pick(CORES)} ${pick(SUFFIXES)}`;
  return `${pick(PREFIXES)} ${pick(CORES)} ${pick(SUFFIXES)}`;
}

function tickerFor(name) {
  const letters = name.replace(/[^A-Za-z]/g, "").toUpperCase();
  return letters.slice(0, Math.random() < 0.5 ? 4 : 5) || "MEME";
}

/**
 * Security profile of a freshly deployed pair. Four archetypes, weighted
 * toward the outcomes that actually dominate new launches.
 */
function randomSecurity(chain) {
  const isSolana = chain === "solana";
  const roll = Math.random();

  // Not yet indexed by the security API — common in the first minutes.
  if (roll < 0.14) {
    return {
      checked: false,
      lpLockedPct: null,
      buyTaxPct: null,
      sellTaxPct: null,
      isHoneypot: null,
      mintRevoked: null,
      freezeRevoked: null,
      top10HoldersPct: null,
      holderCount: null,
      isOpenSource: null,
    };
  }

  const base = {
    checked: true,
    holderCount: Math.round(logUniform(8, 900)),
    isOpenSource: isSolana ? null : chance(0.82),
    buyTaxPct: isSolana ? null : 0,
    sellTaxPct: isSolana ? null : 0,
    isHoneypot: isSolana ? null : false,
  };

  // Outright scam: honeypot or a punitive sell tax.
  if (roll < 0.32) {
    return {
      ...base,
      lpLockedPct: randomBetween(0, 40),
      buyTaxPct: isSolana ? null : randomBetween(0, 12),
      sellTaxPct: isSolana ? null : randomBetween(15, 99),
      isHoneypot: isSolana ? null : chance(0.55),
      mintRevoked: chance(0.25),
      freezeRevoked: chance(0.4),
      top10HoldersPct: randomBetween(45, 96),
    };
  }

  // Sloppy launch: liquidity unlocked or supply concentrated.
  if (roll < 0.72) {
    return {
      ...base,
      lpLockedPct: chance(0.45) ? randomBetween(0, 94) : 100,
      buyTaxPct: isSolana ? null : randomBetween(0, 4),
      sellTaxPct: isSolana ? null : randomBetween(0, 6),
      mintRevoked: chance(0.7),
      freezeRevoked: chance(0.75),
      top10HoldersPct: randomBetween(18, 70),
    };
  }

  // Clean launch: everything the checklist asks for.
  return {
    ...base,
    lpLockedPct: chance(0.6) ? 100 : randomBetween(95, 100),
    buyTaxPct: isSolana ? null : randomBetween(0, 3),
    sellTaxPct: isSolana ? null : randomBetween(0, 3),
    mintRevoked: true,
    freezeRevoked: true,
    top10HoldersPct: randomBetween(4, 19),
  };
}

/** One freshly created pair, as the feed would deliver it. */
export function generateToken() {
  sequence += 1;
  const chain = weightedChain();
  const name = randomName();
  const liquidityUsd = logUniform(1800, 140000);
  const marketCapUsd = liquidityUsd * randomBetween(1.8, 38);
  const buys = Math.round(logUniform(2, 140));
  const sells = Math.round(buys * randomBetween(0.2, 1.6));

  return {
    id: `sim-${sequence}-${Date.now()}`,
    chain,
    dex: CHAINS[chain].dexes[Math.floor(Math.random() * CHAINS[chain].dexes.length)],
    symbol: tickerFor(name),
    name,
    address: randomAddress(chain),
    pairAddress: randomAddress(chain),
    url: null,
    priceUsd: marketCapUsd / logUniform(1e8, 1e12),
    liquidityUsd,
    marketCapUsd,
    volumeH24: liquidityUsd * randomBetween(0.2, 6),
    volumeM5: liquidityUsd * randomBetween(0.01, 0.4),
    txnsM5: { buys, sells },
    txnsH1: { buys: buys * 9, sells: sells * 9 },
    priceChangeM5: randomBetween(-35, 90),
    priceChangeH1: randomBetween(-60, 220),
    priceChangeH24: randomBetween(-80, 400),
    ageMinutes: randomBetween(0, 4),
    source: "sim",
    detectedAt: Date.now(),
    security: randomSecurity(chain),
  };
}

/**
 * Nudge a token's live counters, so trade counts and prices tick between
 * feed events instead of sitting frozen.
 */
export function tickToken(token, elapsedMinutes) {
  const heat = token.source === "sim" ? 1 : 0.35;
  const newBuys = Math.round(Math.random() * 4 * heat);
  const newSells = Math.round(Math.random() * 3 * heat);
  if (!newBuys && !newSells) {
    return { ...token, ageMinutes: (token.ageMinutes ?? 0) + elapsedMinutes };
  }

  const drift = randomBetween(-1.4, 1.8) * heat;
  return {
    ...token,
    ageMinutes: (token.ageMinutes ?? 0) + elapsedMinutes,
    txnsM5: { buys: token.txnsM5.buys + newBuys, sells: token.txnsM5.sells + newSells },
    priceUsd: Math.max(token.priceUsd * (1 + drift / 100), 1e-12),
    priceChangeM5: (token.priceChangeM5 ?? 0) + drift,
    volumeM5: token.volumeM5 + (newBuys + newSells) * randomBetween(20, 900),
  };
}
