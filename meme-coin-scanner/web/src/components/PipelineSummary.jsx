import { Filter } from "lucide-react";
import { STATUS, THRESHOLDS } from "../lib/securityRules.js";

const RULE_LABELS = {
  liquidity: `LP ≥ ${THRESHOLDS.minLpLockedPct}%`,
  honeypot: "Sin honeypot",
  taxes: `Tax < ${THRESHOLDS.maxTaxPct}%`,
  mint: "Mint revocado",
  freeze: "Freeze revocado",
  holders: `Top 10 ≤ ${THRESHOLDS.maxTop10Pct}%`,
};

/**
 * Aggregate pass/fail/unknown rate per rule across everything currently
 * on screen, so the operator sees which filter is doing the rejecting.
 */
export default function PipelineSummary({ tokens }) {
  const ruleIds = Object.keys(RULE_LABELS);
  const totals = ruleIds.map((id) => {
    const counts = { pass: 0, fail: 0, unknown: 0 };
    for (const token of tokens) {
      const check = token.checks.find((c) => c.id === id);
      if (check) counts[check.status] += 1;
    }
    const total = counts.pass + counts.fail + counts.unknown || 1;
    return { id, counts, total };
  });

  return (
    <section className="rounded-lg border border-term-line bg-term-panel p-4">
      <h2 className="mb-3 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
        <Filter className="h-3.5 w-3.5" />
        Pipeline de filtrado ({tokens.length} tokens)
      </h2>

      <ul className="flex flex-col gap-2.5">
        {totals.map(({ id, counts, total }) => (
          <li key={id}>
            <div className="mb-1 flex items-baseline justify-between gap-2">
              <span className="font-mono text-[11px] text-slate-300">{RULE_LABELS[id]}</span>
              <span className="font-mono text-[10px] tnum text-slate-600">
                <span className="text-neon">{counts[STATUS.PASS]}</span>
                {" · "}
                <span className="text-danger">{counts[STATUS.FAIL]}</span>
                {" · "}
                <span className="text-slate-500">{counts[STATUS.UNKNOWN]}</span>
              </span>
            </div>
            <div className="flex h-1.5 overflow-hidden rounded-full bg-term-line">
              <div className="bg-neon transition-[width] duration-500" style={{ width: `${(counts.pass / total) * 100}%` }} />
              <div className="bg-danger transition-[width] duration-500" style={{ width: `${(counts.fail / total) * 100}%` }} />
              <div className="bg-slate-700 transition-[width] duration-500" style={{ width: `${(counts.unknown / total) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>

      <p className="mt-3 border-t border-term-line pt-2.5 font-mono text-[10px] leading-relaxed text-slate-600">
        Verde = aprobado · Rojo = fallo · Gris = sin datos. Un control sin datos
        nunca cuenta como aprobado.
      </p>
    </section>
  );
}
