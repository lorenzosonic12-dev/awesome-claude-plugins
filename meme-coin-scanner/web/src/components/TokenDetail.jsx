import { Copy, ExternalLink, Users } from "lucide-react";
import { useState } from "react";
import ChainTag from "./ChainTag.jsx";
import DegenBadge from "./DegenBadge.jsx";
import SecurityChecklist from "./SecurityChecklist.jsx";
import { formatAge, formatNumber, formatPct, formatPrice, formatUsd, shortAddress } from "../lib/format.js";

const VERDICT_TONES = {
  approved: "border-neon/40 bg-neon/10 text-neon",
  partial: "border-info/40 bg-info/10 text-info",
  review: "border-caution/40 bg-caution/10 text-caution",
  rejected: "border-danger/40 bg-danger/10 text-danger",
};

function Stat({ label, value, accent }) {
  return (
    <div className="rounded-md border border-term-line bg-term-bg px-2.5 py-2">
      <div className="font-mono text-[9.5px] uppercase tracking-wider text-slate-600">{label}</div>
      <div className={`mt-0.5 font-mono text-[12.5px] font-semibold tnum ${accent ?? "text-slate-200"}`}>{value}</div>
    </div>
  );
}

export default function TokenDetail({ token }) {
  const [copied, setCopied] = useState(false);

  if (!token) {
    return (
      <div className="flex h-full min-h-[280px] items-center justify-center rounded-lg border border-dashed border-term-line bg-term-panel p-6 text-center">
        <p className="text-[12.5px] text-slate-500">
          Selecciona un token de la tabla para ver su auditoría completa.
        </p>
      </div>
    );
  }

  function copyAddress() {
    if (!token.address || !navigator.clipboard) return;
    navigator.clipboard.writeText(token.address).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1600);
      },
      () => setCopied(false)
    );
  }

  const change = token.priceChangeH1 ?? 0;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-term-line bg-term-panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate font-mono text-base font-bold text-slate-100">${token.symbol}</h2>
            <ChainTag chain={token.chain} />
            <span className="rounded border border-term-line px-1.5 py-0.5 font-mono text-[9.5px] uppercase text-slate-500">
              {token.dex}
            </span>
          </div>
          <p className="mt-0.5 truncate text-[12px] text-slate-400">{token.name}</p>
          <p className="mt-0.5 font-mono text-[11px] text-slate-600">{formatAge(token.ageMinutes)}</p>
        </div>
        <DegenBadge score={token.score} band={token.band} />
      </div>

      <div
        className={`rounded-md border px-3 py-2 font-mono text-[11px] font-bold uppercase tracking-[0.14em] ${VERDICT_TONES[token.verdict.id]}`}
      >
        Veredicto del pipeline: {token.verdict.label}
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Stat label="Precio" value={formatPrice(token.priceUsd)} />
        <Stat
          label="Cambio 1h"
          value={formatPct(change)}
          accent={change >= 0 ? "text-neon" : "text-danger"}
        />
        <Stat label="Market cap" value={formatUsd(token.marketCapUsd)} />
        <Stat label="Liquidez" value={formatUsd(token.liquidityUsd)} />
        <Stat label="Volumen 24h" value={formatUsd(token.volumeH24)} />
        <Stat
          label="Txns 5m"
          value={`${formatNumber(token.txnsM5.buys)} / ${formatNumber(token.txnsM5.sells)}`}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-md border border-term-line bg-term-bg px-2.5 py-2">
        <span className="font-mono text-[9.5px] uppercase tracking-wider text-slate-600">Contrato</span>
        <code className="font-mono text-[11px] text-slate-300">{shortAddress(token.address)}</code>
        <button
          type="button"
          onClick={copyAddress}
          className="ml-auto flex items-center gap-1 rounded px-1.5 py-1 font-mono text-[10px] uppercase text-slate-500 transition-colors hover:text-neon"
        >
          <Copy className="h-3 w-3" />
          {copied ? "Copiado" : "Copiar"}
        </button>
        {token.url && (
          <a
            href={token.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded px-1.5 py-1 font-mono text-[10px] uppercase text-slate-500 transition-colors hover:text-info"
          >
            <ExternalLink className="h-3 w-3" />
            DexScreener
          </a>
        )}
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
            Pipeline de seguridad
          </h3>
          {token.security?.holderCount ? (
            <span className="flex items-center gap-1 font-mono text-[10px] text-slate-600">
              <Users className="h-3 w-3" />
              {formatNumber(token.security.holderCount)} holders
            </span>
          ) : null}
        </div>
        <SecurityChecklist checks={token.checks} />
      </div>
    </div>
  );
}
