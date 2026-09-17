import { CheckCircle2, HelpCircle, XCircle } from "lucide-react";
import { STATUS } from "../lib/securityRules.js";

const PRESENTATION = {
  [STATUS.PASS]: { icon: CheckCircle2, color: "text-neon", ring: "border-neon/25 bg-neon/5", tag: "OK" },
  [STATUS.FAIL]: { icon: XCircle, color: "text-danger", ring: "border-danger/30 bg-danger/5", tag: "FALLO" },
  [STATUS.UNKNOWN]: { icon: HelpCircle, color: "text-slate-500", ring: "border-term-line bg-term-raised/40", tag: "S/D" },
};

/**
 * The implacable checklist. Unknown checks render in their own grey state
 * so nobody reads "no data" as "passed".
 */
export default function SecurityChecklist({ checks, dense = false }) {
  return (
    <ul className={`flex flex-col ${dense ? "gap-1.5" : "gap-2"}`}>
      {checks.map((check) => {
        const style = PRESENTATION[check.status];
        const Icon = style.icon;
        return (
          <li key={check.id} className={`rounded-md border px-3 py-2 ${style.ring}`}>
            <div className="flex items-start gap-2.5">
              <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${style.color}`} strokeWidth={2} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12.5px] font-medium text-slate-200">{check.label}</span>
                  <span className={`font-mono text-[9.5px] font-bold uppercase tracking-wider ${style.color}`}>
                    {style.tag}
                  </span>
                </div>
                <div className="font-mono text-[11px] text-slate-400">{check.detail}</div>
                {!dense && <p className="mt-1 text-[11px] leading-snug text-slate-500">{check.hint}</p>}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
