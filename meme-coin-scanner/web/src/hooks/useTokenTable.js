import { useEffect, useMemo, useState } from "react";

const PAGE_SIZE = 10;

const ACCESSORS = {
  token: (t) => t.symbol.toLowerCase(),
  age: (t) => t.ageMinutes ?? Number.MAX_SAFE_INTEGER,
  marketCap: (t) => t.marketCapUsd ?? 0,
  liquidity: (t) => t.liquidityUsd ?? 0,
  volume: (t) => t.volumeH24 ?? 0,
  txns: (t) => (t.txnsM5?.buys ?? 0) + (t.txnsM5?.sells ?? 0),
  score: (t) => t.score,
};

function matchesQuery(token, query) {
  if (!query) return true;
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return (
    token.symbol.toLowerCase().includes(needle) ||
    token.name.toLowerCase().includes(needle) ||
    (token.address ?? "").toLowerCase().includes(needle) ||
    (token.pairAddress ?? "").toLowerCase().includes(needle)
  );
}

/**
 * Filtering, sorting and pagination for the monitoring table.
 * Sorting is stable within a page render because the comparator always
 * falls back to the token id.
 */
export function useTokenTable(tokens, { query, chain, onlyApproved }) {
  const [sort, setSort] = useState({ key: "age", dir: "asc" });
  const [page, setPage] = useState(0);

  const filtered = useMemo(
    () =>
      tokens.filter(
        (token) =>
          matchesQuery(token, query) &&
          (chain === "all" || token.chain === chain) &&
          (!onlyApproved || token.verdict.id === "approved")
      ),
    [tokens, query, chain, onlyApproved]
  );

  const sorted = useMemo(() => {
    const accessor = ACCESSORS[sort.key] ?? ACCESSORS.score;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const left = accessor(a);
      const right = accessor(b);
      if (left < right) return -1 * factor;
      if (left > right) return 1 * factor;
      return a.id < b.id ? -1 : 1;
    });
  }, [filtered, sort]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));

  // A shrinking result set must never strand the view on an empty page.
  useEffect(() => {
    setPage((current) => Math.min(current, pageCount - 1));
  }, [pageCount]);

  useEffect(() => {
    setPage(0);
  }, [query, chain, onlyApproved]);

  const pageRows = useMemo(
    () => sorted.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE),
    [sorted, page]
  );

  function toggleSort(key) {
    setSort((current) =>
      current.key === key
        ? { key, dir: current.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "token" || key === "age" ? "asc" : "desc" }
    );
  }

  return {
    rows: pageRows,
    totalRows: sorted.length,
    sort,
    toggleSort,
    page,
    pageCount,
    setPage,
    pageSize: PAGE_SIZE,
  };
}
