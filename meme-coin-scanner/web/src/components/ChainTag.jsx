import { chainInfo } from "../lib/chains.js";

/** Network identity dot + label, the same shape everywhere it appears. */
export default function ChainTag({ chain, showLabel = true, size = "sm" }) {
  const info = chainInfo(chain);
  const dot = size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5";

  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        className={`${dot} shrink-0 rounded-full`}
        style={{ backgroundColor: info.color, boxShadow: `0 0 8px ${info.color}66` }}
        aria-hidden="true"
      />
      {showLabel && (
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">
          {info.short}
        </span>
      )}
    </span>
  );
}
