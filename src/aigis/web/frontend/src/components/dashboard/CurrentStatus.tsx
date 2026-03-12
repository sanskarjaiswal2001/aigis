import { useState } from "react";
import { CheckCircle2, AlertTriangle, XCircle, ChevronDown, ChevronRight } from "lucide-react";
import { useLatestReport, useLatestRun } from "../../api/runs";
import { severityColor } from "../../utils/severity";
import type { Severity } from "../../types";

const statusIcon = (severity: Severity) => {
  const cls = `shrink-0 ${severityColor[severity]}`;
  if (severity === "OK") return <CheckCircle2 size={14} className={cls} strokeWidth={2} />;
  if (severity === "WARN") return <AlertTriangle size={14} className={cls} strokeWidth={2} />;
  return <XCircle size={14} className={cls} strokeWidth={2} />;
};

const MESSAGE_TRUNCATE = 60;

export function CurrentStatus() {
  const { data: latest, isLoading: runLoading, error: runError } = useLatestRun();
  const { data: report, isLoading: reportLoading } = useLatestReport();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  if (runLoading)
    return <div className="h-36 bg-neutral-900 animate-pulse rounded-lg border border-neutral-800" />;

  if (runError || !latest)
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5 text-neutral-500 text-xs">
        No runs yet — start a scan or wait for the scheduled job.
      </div>
    );

  const checks = report?.checks ?? [];

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden h-full flex flex-col">
      <div className="px-4 py-2.5 border-b border-neutral-800">
        <h2 className="text-xs font-medium text-neutral-500 uppercase tracking-widest">Checks</h2>
      </div>

      {reportLoading ? (
        <div className="p-4 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-4 bg-neutral-800 animate-pulse rounded" />
          ))}
        </div>
      ) : checks.length > 0 ? (
        <div className="divide-y divide-neutral-800/60 flex-1 overflow-y-auto min-h-0">
          {checks.map((c) => {
            const isLong = c.message.length > MESSAGE_TRUNCATE;
            const isOpen = expanded.has(c.check_id);
            return (
              <div key={c.check_id} className="text-xs">
                <div
                  className={`flex items-center gap-3 px-4 py-2.5 ${isLong ? "cursor-pointer hover:bg-neutral-800/40" : ""}`}
                  onClick={() => isLong && toggle(c.check_id)}
                >
                  {statusIcon(c.severity)}
                  <span className="text-neutral-300 w-36 shrink-0 truncate">{c.name}</span>
                  <span className="text-neutral-500 flex-1 min-w-0 truncate">
                    {isLong && !isOpen ? c.message.slice(0, MESSAGE_TRUNCATE) + "…" : isOpen ? "" : c.message}
                  </span>
                  {isLong && (
                    <span className="ml-auto text-neutral-700 shrink-0 pl-2">
                      {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </span>
                  )}
                </div>
                {isLong && isOpen && (
                  <div className="px-4 pb-2.5 pl-11 text-neutral-500 leading-relaxed break-words">
                    {c.message}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="px-4 py-4 text-xs text-neutral-600">Run a scan to see check details.</p>
      )}
    </div>
  );
}
