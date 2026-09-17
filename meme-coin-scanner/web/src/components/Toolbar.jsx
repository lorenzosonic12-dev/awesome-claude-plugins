import { Search, ShieldCheck, X } from "lucide-react";
import { FILTERABLE_CHAINS, chainInfo } from "../lib/chains.js";

export default function Toolbar({ query, onQueryChange, chain, onChainChange, onlyApproved, onOnlyApprovedChange, resultCount }) {
  return (
    <section className="flex flex-wrap items-center gap-3 rounded-lg border border-term-line bg-term-panel p-3">
      <div className="relative min-w-[240px] flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" />
        <input
          id="token-search"
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Buscar por contrato (CA / mint), ticker o nombre…"
          className="w-full rounded-md border border-term-line bg-term-bg py-2 pl-9 pr-9 font-mono text-[12.5px] text-slate-200 placeholder:text-slate-600 focus:border-neon/50 focus:outline-none"
        />
        {query && (
          <button
            type="button"
            onClick={() => onQueryChange("")}
            aria-label="Limpiar búsqueda"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-600 hover:text-slate-300"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="flex items-center gap-1.5" role="group" aria-label="Filtrar por red">
        <button
          type="button"
          onClick={() => onChainChange("all")}
          aria-pressed={chain === "all"}
          className={`rounded-md border px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
            chain === "all"
              ? "border-neon/40 bg-neon/10 text-neon"
              : "border-term-line text-slate-500 hover:border-term-edge hover:text-slate-300"
          }`}
        >
          Todas
        </button>
        {FILTERABLE_CHAINS.map((id) => {
          const info = chainInfo(id);
          const active = chain === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onChainChange(id)}
              aria-pressed={active}
              className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                active
                  ? "border-neon/40 bg-neon/10 text-neon"
                  : "border-term-line text-slate-500 hover:border-term-edge hover:text-slate-300"
              }`}
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: info.color }}
                aria-hidden="true"
              />
              {info.label}
            </button>
          );
        })}
      </div>

      <label
        htmlFor="only-approved"
        className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
          onlyApproved ? "border-neon/40 bg-neon/10 text-neon" : "border-term-line text-slate-500 hover:text-slate-300"
        }`}
      >
        <input
          id="only-approved"
          type="checkbox"
          checked={onlyApproved}
          onChange={(event) => onOnlyApprovedChange(event.target.checked)}
          className="sr-only"
        />
        <ShieldCheck className="h-3.5 w-3.5" />
        Solo aprobados
      </label>

      <span className="font-mono text-[11px] tnum text-slate-600">{resultCount} resultados</span>
    </section>
  );
}
