import { CheckCheck, CircleSlash, Eye, ScanLine } from "lucide-react";
import ChainTag from "./ChainTag.jsx";
import { formatClock } from "../lib/format.js";

const VERDICT_STYLE = {
  approved: { icon: CheckCheck, color: "text-neon", text: "APROBADO" },
  partial: { icon: Eye, color: "text-info", text: "PARCIAL" },
  review: { icon: Eye, color: "text-caution", text: "REVISAR" },
  rejected: { icon: CircleSlash, color: "text-danger", text: "DESCARTADO" },
};

export default function FeedTicker({ feed, running }) {
  return (
    <section className="flex h-full flex-col overflow-hidden rounded-lg border border-term-line bg-term-panel">
      <div className="flex items-center justify-between border-b border-term-line px-4 py-2.5">
        <h2 className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
          <ScanLine className="h-3.5 w-3.5" />
          Feed de pares nuevos
        </h2>
        {running && (
          <span className="relative h-1 w-10 overflow-hidden rounded-full bg-term-line" aria-hidden="true">
            <span className="absolute inset-y-0 w-1/4 rounded-full bg-neon animate-sweep" />
          </span>
        )}
      </div>

      <ul className="flex-1 divide-y divide-term-line/60 overflow-y-auto" style={{ maxHeight: "320px" }}>
        {feed.map((event) => {
          const style = VERDICT_STYLE[event.verdict.id];
          const Icon = style.icon;
          return (
            <li key={event.id} className="flex items-center gap-2 px-3 py-2 animate-slide-in">
              <Icon className={`h-3.5 w-3.5 shrink-0 ${style.color}`} />
              <ChainTag chain={event.chain} showLabel={false} />
              <span className="min-w-0 flex-1 truncate font-mono text-[11.5px] text-slate-300">
                ${event.symbol}
              </span>
              <span className={`font-mono text-[9.5px] font-bold uppercase tracking-wider ${style.color}`}>
                {style.text}
              </span>
              <span className="w-7 text-right font-mono text-[11px] tnum text-slate-500">{event.score}</span>
              <span className="w-14 text-right font-mono text-[9.5px] tnum text-slate-700">
                {formatClock(new Date(event.at))}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
