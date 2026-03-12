import { useState } from "react";
import { CheckCircle2, AlertTriangle, XCircle, ChevronDown, ChevronRight } from "lucide-react";
import type { CheckResult, Severity } from "../../types";
import { severityColor } from "../../utils/severity";

const StatusIcon = ({ severity }: { severity: Severity }) => {
  const cls = `shrink-0 ${severityColor[severity]}`;
  if (severity === "OK") return <CheckCircle2 size={13} className={cls} strokeWidth={2} />;
  if (severity === "WARN") return <AlertTriangle size={13} className={cls} strokeWidth={2} />;
  return <XCircle size={13} className={cls} strokeWidth={2} />;
};

const MESSAGE_TRUNCATE = 60;

interface Props {
  checks: CheckResult[];
}

export function CheckTable({ checks }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  if (checks.length === 0)
    return <p className="text-neutral-600 text-xs p-4">No checks.</p>;

  return (
    <div className="divide-y divide-neutral-900">
      {checks.map((c) => {
        const isLong = c.message.length > MESSAGE_TRUNCATE;
        const isOpen = expanded.has(c.check_id);
        return (
          <div key={c.check_id} className="text-xs">
            <div
              className={`flex items-center gap-3 px-4 py-2.5 ${isLong ? "cursor-pointer hover:bg-neutral-900/50" : ""}`}
              onClick={() => isLong && toggle(c.check_id)}
            >
              <StatusIcon severity={c.severity} />
              <span className="text-neutral-300 font-medium w-36 shrink-0 truncate">{c.name}</span>
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
  );
}
