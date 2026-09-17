import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";
import TokenRow from "./TokenRow.jsx";

const COLUMNS = [
  { key: "token", label: "Token", align: "left" },
  { key: "age", label: "Edad", align: "left" },
  { key: "marketCap", label: "Market cap", align: "left" },
  { key: "liquidity", label: "Liquidez", align: "left" },
  { key: "volume", label: "Volumen / Txns", align: "left" },
  { key: "txns", label: "Cambio 5m", align: "left" },
  { key: "score", label: "DegenScore", align: "left" },
];

function SortIcon({ active, dir }) {
  if (!active) return <ChevronDown className="h-3 w-3 opacity-25" />;
  return dir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />;
}

export default function TokenTable({ table, selectedId, onSelect, newIds }) {
  const { rows, sort, toggleSort, page, pageCount, setPage, totalRows, pageSize } = table;
  const firstRow = totalRows === 0 ? 0 : page * pageSize + 1;
  const lastRow = Math.min(totalRows, (page + 1) * pageSize);

  return (
    <section className="overflow-hidden rounded-lg border border-term-line bg-term-panel">
      <div className="flex items-center justify-between border-b border-term-line px-4 py-2.5">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
          Monitoreo en vivo
        </h2>
        <span className="font-mono text-[10.5px] tnum text-slate-600">
          {firstRow}–{lastRow} de {totalRows}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] border-collapse text-left">
          <thead>
            <tr className="border-b border-term-line bg-term-bg/60">
              {COLUMNS.map((column) => {
                const active = sort.key === column.key;
                return (
                  <th key={column.key} scope="col" className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => toggleSort(column.key)}
                      className={`flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                        active ? "text-neon" : "text-slate-500 hover:text-slate-300"
                      }`}
                      aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                    >
                      {column.label}
                      <SortIcon active={active} dir={sort.dir} />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((token) => (
              <TokenRow
                key={token.id}
                token={token}
                selected={token.id === selectedId}
                onSelect={onSelect}
                isNew={newIds.has(token.id)}
              />
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-[12.5px] text-slate-500">
                  Ningún token coincide con los filtros actuales.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-term-line px-4 py-2.5">
        <button
          type="button"
          onClick={() => setPage(Math.max(0, page - 1))}
          disabled={page === 0}
          className="flex items-center gap-1 rounded-md border border-term-line px-2.5 py-1.5 font-mono text-[10.5px] uppercase tracking-wider text-slate-400 transition-colors hover:border-term-edge hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Anterior
        </button>

        <span className="font-mono text-[10.5px] tnum text-slate-600">
          Página {page + 1} / {pageCount}
        </span>

        <button
          type="button"
          onClick={() => setPage(Math.min(pageCount - 1, page + 1))}
          disabled={page >= pageCount - 1}
          className="flex items-center gap-1 rounded-md border border-term-line px-2.5 py-1.5 font-mono text-[10.5px] uppercase tracking-wider text-slate-400 transition-colors hover:border-term-edge hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-30"
        >
          Siguiente
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </section>
  );
}
