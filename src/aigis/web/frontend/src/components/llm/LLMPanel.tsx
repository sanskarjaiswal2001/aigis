import { useState } from "react";
import { Bot, Zap, AlertCircle, GitBranch, BookOpen, ChevronDown, ChevronRight } from "lucide-react";
import type { HealthReport, ManualRecommendation } from "../../types";
import type { Severity } from "../../types";
import { ActionCard } from "./ActionCard";
import { SeverityBadge } from "../layout/SeverityBadge";

interface Props {
  report: HealthReport | undefined;
}

const riskColor: Record<string, string> = {
  low: "text-neutral-500",
  medium: "text-amber-500",
  high: "text-red-500",
};

function ManualStepCard({ rec }: { rec: ManualRecommendation }) {
  const [open, setOpen] = useState(false);
  const hasSteps = (rec.steps?.length ?? 0) > 0;

  return (
    <div className="border border-neutral-800 rounded bg-neutral-950 p-3">
      <div className="flex items-start gap-2">
        <BookOpen size={12} className="text-neutral-600 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-xs text-neutral-300 leading-relaxed">{rec.description}</p>
          <div className="flex items-center gap-3 mt-1">
            <span className={`text-xs ${riskColor[rec.risk_level] ?? "text-neutral-500"}`}>
              {rec.risk_level} risk
            </span>
            {hasSteps && (
              <button
                onClick={() => setOpen(!open)}
                className="flex items-center gap-0.5 text-xs text-neutral-600 hover:text-neutral-400 transition-colors"
              >
                {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                {open ? "hide steps" : "show steps"}
              </button>
            )}
          </div>
          {open && rec.steps && rec.steps.length > 0 && (
            <ol className="list-decimal pl-4 space-y-1 mt-2 text-neutral-500 text-xs leading-relaxed">
              {rec.steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}

export function LLMExplanation({ report }: Props) {
  if (!report?.anomaly_explanation) return null;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden h-full flex flex-col">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neutral-800">
        <Bot size={13} className="text-neutral-600" />
        <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest">
          Analysis
        </h2>
      </div>
      <div className="p-5 flex-1">
        <p className="text-xs text-neutral-400 leading-relaxed">
          {report.anomaly_explanation}
        </p>
      </div>
    </div>
  );
}

export function LLMIssues({ report }: Props) {
  if (!report?.detected_issues?.length) return null;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden h-full flex flex-col">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neutral-800">
        <AlertCircle size={13} className="text-neutral-600" />
        <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest">
          Detected Issues
        </h2>
        <span className="ml-auto text-xs text-neutral-700 font-mono">
          {report.detected_issues.length}
        </span>
      </div>
      <div className="divide-y divide-neutral-800 flex-1">
        {report.detected_issues.map((issue, i) => (
          <div key={i} className="flex items-start gap-3 px-5 py-2.5">
            <SeverityBadge severity={issue.severity as Severity} />
            <div className="flex-1 min-w-0">
              <span className="text-xs font-mono text-neutral-400">{issue.component}</span>
              <p className="text-xs text-neutral-500 mt-0.5">{issue.explanation}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LLMReasoning({ report }: Props) {
  if (!report?.reasoning_trace) return null;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden h-full flex flex-col">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neutral-800">
        <GitBranch size={13} className="text-neutral-600" />
        <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest">
          Reasoning
        </h2>
      </div>
      <div className="p-5 flex-1">
        <p className="text-xs text-neutral-400 leading-relaxed">{report.reasoning_trace}</p>
      </div>
    </div>
  );
}

export function LLMActions({ report }: Props) {
  const hasScripted = (report?.suggested_actions?.length ?? 0) > 0;
  const hasManual = (report?.manual_recommendations?.length ?? 0) > 0;

  if (!hasScripted && !hasManual) {
    // Show placeholder only when analysis ran but nothing suggested
    if (!report?.anomaly_explanation) return null;
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden h-full flex flex-col">
        <div className="flex items-center gap-2 px-5 py-3 border-b border-neutral-800">
          <Zap size={13} className="text-neutral-600" />
          <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest">
            Suggested Actions
          </h2>
        </div>
        <div className="p-5 flex-1">
          <p className="text-xs text-neutral-600 italic">
            No automated actions available — review logs and runbooks manually.
          </p>
        </div>
      </div>
    );
  }

  const total = (report?.suggested_actions?.length ?? 0) + (report?.manual_recommendations?.length ?? 0);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden h-full flex flex-col">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neutral-800">
        <Zap size={13} className="text-neutral-600" />
        <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest">
          Suggested Actions
        </h2>
        <span className="ml-auto text-xs text-neutral-700 font-mono">{total}</span>
      </div>
      <div className="p-5 space-y-2 flex-1">
        {report?.suggested_actions?.map((action) => (
          <ActionCard key={action.action_id} action={action} runId={report.run_id} />
        ))}
        {report?.manual_recommendations?.map((rec, i) => (
          <ManualStepCard key={i} rec={rec} />
        ))}
      </div>
    </div>
  );
}

/** @deprecated Use LLMExplanation + LLMActions separately */
export function LLMPanel({ report }: Props) {
  return (
    <>
      <LLMExplanation report={report} />
      <LLMActions report={report} />
    </>
  );
}
