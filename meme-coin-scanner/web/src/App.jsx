import { useEffect, useMemo, useRef, useState } from "react";
import { TriangleAlert } from "lucide-react";
import FeedTicker from "./components/FeedTicker.jsx";
import Header from "./components/Header.jsx";
import MetricsPanel from "./components/MetricsPanel.jsx";
import PipelineSummary from "./components/PipelineSummary.jsx";
import TokenDetail from "./components/TokenDetail.jsx";
import TokenTable from "./components/TokenTable.jsx";
import Toolbar from "./components/Toolbar.jsx";
import { useTokenFeed } from "./hooks/useTokenFeed.js";
import { useTokenTable } from "./hooks/useTokenTable.js";
import { seedScan } from "./data/seedTokens.js";

/** How long a freshly arrived row keeps its entrance animation. */
const NEW_ROW_MS = 4000;

export default function App() {
  const [intervalMs, setIntervalMs] = useState(2600);
  const [query, setQuery] = useState("");
  const [chain, setChain] = useState("all");
  const [onlyApproved, setOnlyApproved] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [newIds, setNewIds] = useState(() => new Set());

  const { tokens, feed, stats, running, setRunning, scanOnce, lastEventAt } = useTokenFeed({ intervalMs });
  const table = useTokenTable(tokens, { query, chain, onlyApproved });

  // Track which rows arrived recently so they animate in exactly once.
  const knownIds = useRef(new Set(tokens.map((t) => t.id)));
  useEffect(() => {
    const arrived = tokens.filter((t) => !knownIds.current.has(t.id)).map((t) => t.id);
    if (arrived.length === 0) return undefined;

    arrived.forEach((id) => knownIds.current.add(id));
    setNewIds((current) => new Set([...current, ...arrived]));

    const timer = setTimeout(() => {
      setNewIds((current) => {
        const next = new Set(current);
        arrived.forEach((id) => next.delete(id));
        return next;
      });
    }, NEW_ROW_MS);

    return () => clearTimeout(timer);
  }, [tokens]);

  const selected = useMemo(
    () => tokens.find((token) => token.id === selectedId) ?? tokens[0] ?? null,
    [tokens, selectedId]
  );

  const liveCount = tokens.filter((t) => t.source === "live").length;

  return (
    <div className="relative z-10 mx-auto flex max-w-[1400px] flex-col gap-4 px-4 py-5 sm:px-6">
      <Header
        running={running}
        onToggleRunning={() => setRunning((value) => !value)}
        intervalMs={intervalMs}
        onIntervalChange={setIntervalMs}
        onScanOnce={scanOnce}
        lastEventAt={lastEventAt}
      />

      <MetricsPanel stats={stats} />

      <Toolbar
        query={query}
        onQueryChange={setQuery}
        chain={chain}
        onChainChange={setChain}
        onlyApproved={onlyApproved}
        onOnlyApprovedChange={setOnlyApproved}
        resultCount={table.totalRows}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex flex-col gap-4">
          <TokenTable
            table={table}
            selectedId={selected?.id ?? null}
            onSelect={(token) => setSelectedId(token.id)}
            newIds={newIds}
          />
          <PipelineSummary tokens={tokens} />
        </div>

        <div className="flex flex-col gap-4">
          <FeedTicker feed={feed} running={running} />
          <TokenDetail token={selected} />
        </div>
      </div>

      <footer className="flex flex-col gap-2 border-t border-term-line pt-4 font-mono text-[10.5px] leading-relaxed text-slate-600">
        <p className="flex items-start gap-2">
          <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-caution" />
          <span>
            <strong className="text-slate-400">Esto no es asesoramiento financiero.</strong> Las meme coins
            son de riesgo extremo. Un DegenScore alto no es una recomendación de compra y la ausencia de
            alertas no prueba que un token sea seguro.
          </span>
        </p>
        <p>
          <span className="text-slate-400">Origen de los datos:</span> {liveCount} tokens provienen de un
          escaneo real (DexScreener + GoPlus Security) capturado el{" "}
          {new Date(seedScan.capturedAt).toLocaleString("es-ES")}. Las filas marcadas{" "}
          <span className="text-info">sim</span> las genera el simulador de feed, que sustituye al websocket
          de pares nuevos porque ese proveedor exige llave privada.
        </p>
      </footer>
    </div>
  );
}
