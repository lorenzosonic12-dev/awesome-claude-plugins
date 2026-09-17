import { Pause, Play, Radar, Zap } from "lucide-react";
import { formatClock } from "../lib/format.js";

const SPEEDS = [
  { ms: 5200, label: "LENTO" },
  { ms: 2600, label: "NORMAL" },
  { ms: 1100, label: "TURBO" },
];

export default function Header({ running, onToggleRunning, intervalMs, onIntervalChange, onScanOnce, lastEventAt }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-term-line pb-4">
      <div className="flex items-center gap-3">
        <div className="relative flex h-11 w-11 items-center justify-center rounded-lg border border-neon/30 bg-neon/5">
          <Radar className="h-6 w-6 text-neon" strokeWidth={1.75} />
          {running && (
            <span className="absolute inset-0 rounded-lg border border-neon/40 animate-pulse-ring" aria-hidden="true" />
          )}
        </div>
        <div>
          <h1 className="font-mono text-lg font-bold tracking-tight text-slate-100">
            RUGSENSE<span className="text-neon">_</span>SCANNER
          </h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-slate-500">
            Pipeline de seguridad on-chain · Solana · Base · Ethereum
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 rounded-md border border-term-line bg-term-panel px-3 py-2">
          <span
            className={`h-2 w-2 rounded-full ${running ? "bg-neon animate-pulse-ring" : "bg-slate-600"}`}
            aria-hidden="true"
          />
          <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">
            {running ? "En vivo" : "Pausado"}
          </span>
          <span className="font-mono text-[11px] text-slate-600">·</span>
          <span className="font-mono text-[11px] tnum text-slate-500">{formatClock(new Date(lastEventAt))}</span>
        </div>

        <div className="flex overflow-hidden rounded-md border border-term-line bg-term-panel" role="group" aria-label="Velocidad del feed">
          {SPEEDS.map((speed) => (
            <button
              key={speed.ms}
              type="button"
              onClick={() => onIntervalChange(speed.ms)}
              aria-pressed={intervalMs === speed.ms}
              className={`px-2.5 py-2 font-mono text-[10px] font-bold uppercase tracking-wider transition-colors ${
                intervalMs === speed.ms
                  ? "bg-neon/15 text-neon"
                  : "text-slate-500 hover:bg-term-raised hover:text-slate-300"
              }`}
            >
              {speed.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onScanOnce}
          className="flex items-center gap-1.5 rounded-md border border-term-line bg-term-panel px-3 py-2 font-mono text-[11px] font-bold uppercase tracking-wider text-slate-300 transition-colors hover:border-info/40 hover:text-info"
        >
          <Zap className="h-3.5 w-3.5" />
          Escanear
        </button>

        <button
          type="button"
          onClick={onToggleRunning}
          className={`flex items-center gap-1.5 rounded-md border px-3 py-2 font-mono text-[11px] font-bold uppercase tracking-wider transition-colors ${
            running
              ? "border-caution/40 bg-caution/10 text-caution hover:bg-caution/20"
              : "border-neon/40 bg-neon/10 text-neon hover:bg-neon/20"
          }`}
        >
          {running ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          {running ? "Pausar" : "Reanudar"}
        </button>
      </div>
    </header>
  );
}
