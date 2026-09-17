const TONES = {
  neon: "border-neon/40 bg-neon/10 text-neon",
  caution: "border-caution/40 bg-caution/10 text-caution",
  danger: "border-danger/40 bg-danger/10 text-danger",
  info: "border-info/40 bg-info/10 text-info",
};

const BAR_TONES = {
  neon: "bg-neon",
  caution: "bg-caution",
  danger: "bg-danger",
  info: "bg-info",
};

/** The 0-100 DegenScore with its colour band. */
export default function DegenBadge({ score, band, showBar = true }) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={`flex h-9 w-11 shrink-0 items-center justify-center rounded-md border font-mono text-sm font-bold tnum ${TONES[band.tone]}`}
        title={`DegenScore ${score}/100 — ${band.label}`}
      >
        {score}
      </div>
      <div className="min-w-0">
        <div className={`font-mono text-[10px] font-bold uppercase tracking-widest ${TONES[band.tone].split(" ").pop()}`}>
          {band.label}
        </div>
        {showBar && (
          <div className="mt-1 h-1 w-16 overflow-hidden rounded-full bg-term-line">
            <div
              className={`h-full rounded-full transition-[width] duration-500 ${BAR_TONES[band.tone]}`}
              style={{ width: `${Math.max(score, 3)}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
