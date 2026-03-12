import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle } from "lucide-react";
import type { RunPhase } from "../../types";

interface Props {
  phases: RunPhase[];
}

const categoryLabel: Record<string, string> = {
  collection: "Collection",
  evaluation: "Evaluation",
  reporting: "Reporting",
  analysis: "Analysis",
  healing: "Healing",
};

export function PhaseAccordion({ phases }: Props) {
  const [open, setOpen] = useState<string | null>(null);

  if (phases.length === 0)
    return <p className="text-neutral-600 text-xs">No phase data available.</p>;

  return (
    <div className="space-y-px">
      {phases.map((phase) => {
        const isOpen = open === phase.category;
        const passed = phase.passes === "true";
        return (
          <div key={phase.category} className="overflow-hidden">
            <button
              onClick={() => setOpen(isOpen ? null : phase.category)}
              className="w-full flex items-center justify-between px-4 py-2.5 bg-neutral-900 hover:bg-neutral-800 text-left transition-colors"
            >
              <div className="flex items-center gap-2.5">
                {isOpen ? (
                  <ChevronDown size={13} className="text-neutral-600" />
                ) : (
                  <ChevronRight size={13} className="text-neutral-600" />
                )}
                <span className="text-xs text-neutral-300 font-medium">
                  {categoryLabel[phase.category] ?? phase.category}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                {passed ? (
                  <CheckCircle2 size={12} className="text-neutral-500" />
                ) : (
                  <XCircle size={12} className="text-red-500" />
                )}
                <span className={`text-xs ${passed ? "text-neutral-600" : "text-red-500"}`}>
                  {passed ? "passed" : "failed"}
                </span>
              </div>
            </button>
            {isOpen && (
              <div className="bg-black px-4 py-3 border-t border-neutral-900">
                <p className="text-xs text-neutral-600 mb-2">{phase.description}</p>
                <div className="space-y-0.5">
                  {phase.steps.map((step, i) => (
                    <div key={i} className="font-mono text-xs text-neutral-500 leading-5">
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
