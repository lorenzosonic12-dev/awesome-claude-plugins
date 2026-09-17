/** The networks the scanner monitors, with their display identity. */
export const CHAINS = {
  solana: { id: "solana", label: "Solana", short: "SOL", color: "#14f195", dexes: ["raydium", "pumpswap", "meteora", "orca"] },
  base: { id: "base", label: "Base", short: "BASE", color: "#0052ff", dexes: ["uniswap", "aerodrome"] },
  ethereum: { id: "ethereum", label: "Ethereum", short: "ETH", color: "#8a92b2", dexes: ["uniswap", "pancakeswap"] },
  bsc: { id: "bsc", label: "BNB Chain", short: "BSC", color: "#f0b90b", dexes: ["pancakeswap"] },
};

/** Networks offered as quick filters, in the order the spec lists them. */
export const FILTERABLE_CHAINS = ["solana", "base", "ethereum"];

export function chainInfo(id) {
  return (
    CHAINS[id] ?? {
      id,
      label: id ? id.charAt(0).toUpperCase() + id.slice(1) : "Desconocida",
      short: (id ?? "???").slice(0, 4).toUpperCase(),
      color: "#64748b",
      dexes: ["dex"],
    }
  );
}
