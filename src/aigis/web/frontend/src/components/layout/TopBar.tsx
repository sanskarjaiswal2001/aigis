import { Shield, Server, Clock } from "lucide-react";
import { useLatestRun } from "../../api/runs";
import { SeverityBadge } from "./SeverityBadge";

export function TopBar() {
  const { data: latest } = useLatestRun();

  return (
    <header className="bg-neutral-950 border-b border-neutral-800 px-5 py-3 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <Shield size={18} className="text-red-500" strokeWidth={2} />
        <span className="font-bold text-sm tracking-widest uppercase text-neutral-100">
          AIgis
        </span>
        {latest && (
          <div className="flex items-center gap-1.5 text-neutral-500 text-xs ml-2">
            <Server size={12} />
            <span className="text-neutral-400">{latest.target}</span>
          </div>
        )}
      </div>

      {latest && (
        <div className="flex items-center gap-4">
          <SeverityBadge severity={latest.overall_severity} size="sm" />
          <div className="flex items-center gap-1.5 text-neutral-600 text-xs">
            <Clock size={11} />
            <span>{new Date(latest.timestamp).toLocaleString()}</span>
          </div>
        </div>
      )}
    </header>
  );
}
