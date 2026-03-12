import { useQueryClient } from "@tanstack/react-query";
import { Server, Clock, Hash, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { useLatestReport, useLatestRun } from "../../api/runs";
import { useSSE } from "../../hooks/useSSE";
import type { RunEvent } from "../../types";
import { SeverityBadge } from "../layout/SeverityBadge";
import { CurrentStatus } from "./CurrentStatus";
import { RunTimeline } from "./RunTimeline";
import { ScanButton } from "./ScanButton";
import { LLMExplanation, LLMActions, LLMIssues, LLMReasoning } from "../llm/LLMPanel";

function StatTile({
  label,
  value,
  icon,
  valueClass = "text-neutral-300",
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  valueClass?: string;
}) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3 flex flex-col gap-1">
      <span className="text-neutral-600 text-xs uppercase tracking-widest">{label}</span>
      <div className={`flex items-center gap-1.5 font-mono text-lg font-semibold ${valueClass}`}>
        {icon}
        {value}
      </div>
    </div>
  );
}

export function Dashboard() {
  const queryClient = useQueryClient();
  const { data: latest } = useLatestRun();
  const { data: report } = useLatestReport();

  useSSE<RunEvent>({
    url: "/api/events",
    onMessage: (event) => {
      if (event.type === "new_run") {
        void queryClient.invalidateQueries({ queryKey: ["runs"] });
      }
    },
  });

  const checks = report?.checks ?? [];
  const okCount = checks.filter((c) => c.severity === "OK").length;
  const warnCount = checks.filter((c) => c.severity === "WARN").length;
  const critCount = checks.filter((c) => c.severity === "CRITICAL").length;

  const hasAnalysis =
    !!report?.anomaly_explanation ||
    !!report?.detected_issues?.length ||
    !!report?.reasoning_trace ||
    !!report?.suggested_actions?.length ||
    !!report?.manual_recommendations?.length;

  return (
    <div className="p-6 w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xs font-medium text-neutral-500 uppercase tracking-widest">
          Dashboard
        </h1>
        <ScanButton />
      </div>

      {/* Stats strip */}
      {latest && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3 flex flex-col gap-1.5">
            <span className="text-neutral-600 text-xs uppercase tracking-widest">Status</span>
            <div className="flex items-center gap-2">
              <SeverityBadge severity={latest.overall_severity} size="lg" />
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5">
              <div className="flex items-center gap-1 text-neutral-500 text-xs">
                <Server size={10} />
                <span className="text-neutral-400">{latest.target}</span>
              </div>
              <div className="flex items-center gap-1 text-neutral-600 text-xs">
                <Clock size={10} />
                <span>{new Date(latest.timestamp).toLocaleString()}</span>
              </div>
              <Link
                to={`/runs/${latest.run_id}`}
                className="flex items-center gap-1 text-red-600 hover:text-red-400 text-xs font-mono transition-colors"
              >
                <Hash size={10} />
                {latest.run_id}
              </Link>
            </div>
          </div>

          <StatTile
            label="OK"
            value={okCount}
            icon={<CheckCircle2 size={16} className="text-green-500" strokeWidth={2} />}
            valueClass="text-green-500"
          />
          <StatTile
            label="Warnings"
            value={warnCount}
            icon={<AlertTriangle size={16} className={warnCount > 0 ? "text-amber-400" : "text-neutral-700"} strokeWidth={2} />}
            valueClass={warnCount > 0 ? "text-amber-400" : "text-neutral-600"}
          />
          <StatTile
            label="Critical"
            value={critCount}
            icon={<XCircle size={16} className={critCount > 0 ? "text-red-400" : "text-neutral-700"} strokeWidth={2} />}
            valueClass={critCount > 0 ? "text-red-400" : "text-neutral-600"}
          />
        </div>
      )}

      {/* Checks + Run History — equal halves */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CurrentStatus />
        <RunTimeline />
      </div>

      {/* Last Run Analysis — full-width bento row */}
      {hasAnalysis && (
        <div className="space-y-3">
          <p className="text-xs text-neutral-600 uppercase tracking-widest">Last Run Analysis</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <LLMExplanation report={report} />
            <LLMIssues report={report} />
            <LLMReasoning report={report} />
            <LLMActions report={report} />
          </div>
        </div>
      )}
    </div>
  );
}
