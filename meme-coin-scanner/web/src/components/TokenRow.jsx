import { ArrowDownRight, ArrowUpRight, CircleAlert } from "lucide-react";
import ChainTag from "./ChainTag.jsx";
import DegenBadge from "./DegenBadge.jsx";
import { STATUS } from "../lib/securityRules.js";
import { formatAgeShort, formatNumber, formatPct, formatUsd } from "../lib/format.js";

export default function TokenRow({ token, selected, onSelect, isNew }) {
  const failures = token.checks.filter((c) => c.status === STATUS.FAIL).length;
  const change = token.priceChangeM5 ?? 0;
  const trades = token.txnsM5.buys + token.txnsM5.sells;

  return (
    <tr
      onClick={() => onSelect(token)}
      className={`cursor-pointer border-b border-term-line/70 transition-colors ${
        selected ? "bg-neon/[0.06]" : "hover:bg-term-raised/60"
      } ${isNew ? "animate-slide-in" : ""}`}
    >
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          <ChainTag chain={token.chain} showLabel={false} size="md" />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[13px] font-bold text-slate-100">${token.symbol}</span>
              {token.source === "sim" && (
                <span
                  className="rounded border border-info/30 px-1 font-mono text-[8.5px] uppercase tracking-wider text-info/80"
                  title="Par simulado por el feed en vivo"
                >
                  sim
                </span>
              )}
              {failures > 0 && (
                <span className="flex items-center gap-0.5 font-mono text-[9.5px] text-danger" title={`${failures} controles fallidos`}>
                  <CircleAlert className="h-3 w-3" />
                  {failures}
                </span>
              )}
            </div>
            <div className="truncate text-[11px] text-slate-500" style={{ maxWidth: "15ch" }}>
              {token.name}
            </div>
          </div>
        </div>
      </td>

      <td className="px-3 py-2.5 font-mono text-[12px] tnum text-slate-400">
        {formatAgeShort(token.ageMinutes)}
      </td>

      <td className="px-3 py-2.5 font-mono text-[12px] tnum text-slate-300">
        {formatUsd(token.marketCapUsd)}
      </td>

      <td className="px-3 py-2.5 font-mono text-[12px] tnum text-slate-300">
        {formatUsd(token.liquidityUsd)}
      </td>

      <td className="px-3 py-2.5">
        <div className="font-mono text-[12px] tnum text-slate-300">{formatUsd(token.volumeH24)}</div>
        <div className="font-mono text-[10px] tnum text-slate-600">
          <span className="text-neon/70">{formatNumber(token.txnsM5.buys)}</span>
          {" / "}
          <span className="text-danger/70">{formatNumber(token.txnsM5.sells)}</span>
          <span className="text-slate-700"> · {trades} tx 5m</span>
        </div>
      </td>

      <td className="px-3 py-2.5">
        <span
          className={`flex items-center gap-0.5 font-mono text-[12px] tnum ${
            change >= 0 ? "text-neon" : "text-danger"
          }`}
        >
          {change >= 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
          {formatPct(change, { sign: false })}
        </span>
      </td>

      <td className="px-3 py-2.5">
        <DegenBadge score={token.score} band={token.band} />
      </td>
    </tr>
  );
}
