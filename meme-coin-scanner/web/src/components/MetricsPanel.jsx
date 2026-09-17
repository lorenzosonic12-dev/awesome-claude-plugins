import { Activity, ShieldAlert, ShieldCheck, Waves } from "lucide-react";
import { formatNumber, formatUsd } from "../lib/format.js";

const TONES = {
  slate: { text: "text-slate-200", icon: "text-slate-400", ring: "border-term-line" },
  danger: { text: "text-danger", icon: "text-danger", ring: "border-danger/30" },
  neon: { text: "text-neon", icon: "text-neon", ring: "border-neon/30" },
  info: { text: "text-info", icon: "text-info", ring: "border-info/30" },
};

function Metric({ icon: Icon, label, value, sub, tone }) {
  const styles = TONES[tone];
  return (
    <div className={`rounded-lg border bg-term-panel px-4 py-3.5 ${styles.ring}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</span>
        <Icon className={`h-4 w-4 ${styles.icon}`} strokeWidth={1.75} />
      </div>
      <div className={`mt-2 font-mono text-2xl font-bold tnum ${styles.text}`}>{value}</div>
      <div className="mt-0.5 font-mono text-[10.5px] text-slate-500">{sub}</div>
    </div>
  );
}

export default function MetricsPanel({ stats }) {
  return (
    <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Métricas globales">
      <Metric
        icon={Activity}
        tone="slate"
        label="Tokens escaneados"
        value={formatNumber(stats.scanned)}
        sub="Pares procesados en esta sesión"
      />
      <Metric
        icon={ShieldAlert}
        tone="danger"
        label="Alertas de rugpull"
        value={formatNumber(stats.rugAlerts)}
        sub="Rechazados por el pipeline"
      />
      <Metric
        icon={ShieldCheck}
        tone="neon"
        label="Tokens sin fallos"
        value={formatNumber(stats.noFailures)}
        sub={`${formatNumber(stats.fullyVerified)} con checklist 100% verificado`}
      />
      <Metric
        icon={Waves}
        tone="info"
        label="Volumen monitoreado"
        value={formatUsd(stats.volumeMonitored)}
        sub={`${formatUsd(stats.liquidityMonitored)} en liquidez`}
      />
    </section>
  );
}
