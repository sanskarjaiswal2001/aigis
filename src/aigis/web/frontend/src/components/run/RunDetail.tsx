import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Hash } from "lucide-react";
import { useRunReport } from "../../api/runs";
import { SeverityBadge } from "../layout/SeverityBadge";
import { CheckTable } from "./CheckTable";
import { LLMExplanation, LLMActions, LLMIssues, LLMReasoning } from "../llm/LLMPanel";

export function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const { data: report, isLoading, error } = useRunReport(runId);

  if (isLoading)
    return <div className="p-6 text-neutral-600 text-xs">Loading…</div>;

  if (error || !report)
    return (
      <div className="p-6 text-neutral-600 text-xs space-y-1">
        <p>No report file found for this run.</p>
        <p className="text-neutral-700">
          Per-run reports are written starting from the first scan after the dashboard was set up.
        </p>
      </div>
    );

  return (
    <div className="p-6 space-y-4 w-full">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/runs"
          className="flex items-center gap-1 text-neutral-600 hover:text-neutral-400 text-xs transition-colors"
        >
          <ArrowLeft size={12} />
          Runs
        </Link>
        <span className="text-neutral-800">|</span>
        <SeverityBadge severity={report.overall_severity} />
        <div className="flex items-center gap-1.5 text-neutral-600 text-xs font-mono ml-auto">
          <Hash size={11} />
          {report.run_id}
        </div>
        <span className="text-neutral-700 text-xs">
          {new Date(report.timestamp).toLocaleString()}
        </span>
      </div>

      {/* Row 1: Checks | Analysis | Reasoning */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
        <section className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden h-full flex flex-col">
          <div className="px-4 py-2.5 border-b border-neutral-800">
            <h2 className="text-xs font-medium text-neutral-500 uppercase tracking-widest">
              Checks
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            <CheckTable checks={report.checks} />
          </div>
        </section>
        <LLMExplanation report={report} />
        <LLMReasoning report={report} />
      </div>

      {/* Row 2: Detected Issues | Suggested Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
        <LLMIssues report={report} />
        <LLMActions report={report} />
      </div>
    </div>
  );
}
