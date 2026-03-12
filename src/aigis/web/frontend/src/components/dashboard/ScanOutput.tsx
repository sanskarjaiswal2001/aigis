import { useEffect, useRef, useState } from "react";
import { X, Terminal, CheckCircle2, XCircle } from "lucide-react";
import type { ScanEvent } from "../../types";

interface Props {
  onClose: () => void;
  onDone: () => void;
  autoFix: boolean;
}

const PHASES: [string, string][] = [
  ["collection", "Collecting"],
  ["evaluation", "Evaluating"],
  ["analysis", "Analyzing"],
  ["reporting", "Reporting"],
  ["done", "Done"],
];

export function ScanOutput({ onClose, onDone, autoFix }: Props) {
  const [lines, setLines] = useState<{ type: string; text: string }[]>([]);
  const [done, setDone] = useState(false);
  const [exitCode, setExitCode] = useState<number | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
  const [completedPhases, setCompletedPhases] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function stream() {
      try {
        const res = await fetch("/api/scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ auto_fix: autoFix }),
          signal: controller.signal,
        });

        if (!res.ok) {
          let text = await res.text();
          try { const j = JSON.parse(text); if (j.detail) text = j.detail; } catch { /* raw */ }
          setLines((l) => [...l, { type: "error", text }]);
          setDone(true);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done: streamDone, value } = await reader.read();
          if (streamDone) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";
          for (const part of parts) {
            const dataLine = part.split("\n").find((l) => l.startsWith("data:"));
            if (!dataLine) continue;
            try {
              const event = JSON.parse(dataLine.slice(5).trim()) as ScanEvent;
              if (event.type === "stdout" || event.type === "stderr") {
                const text = event.line ?? "";
                // Parse phase markers — advance phase bar, don't show in terminal
                if (event.type === "stdout" && text.startsWith("AIGIS_PHASE:")) {
                  const phase = text.slice("AIGIS_PHASE:".length);
                  setCurrentPhase(phase);
                  setCompletedPhases((prev) => {
                    const next = new Set(prev);
                    // Mark all phases before this one as completed
                    const idx = PHASES.findIndex(([id]) => id === phase);
                    PHASES.slice(0, idx).forEach(([id]) => next.add(id));
                    return next;
                  });
                } else {
                  setLines((l) => [...l, { type: event.type, text }]);
                }
              } else if (event.type === "done") {
                setExitCode(event.exit_code ?? 0);
                setDone(true);
                setCurrentPhase("done");
                setCompletedPhases(new Set(PHASES.map(([id]) => id)));
                onDone();
              } else if (event.type === "error") {
                setLines((l) => [...l, { type: "error", text: event.message ?? "unknown error" }]);
                setDone(true);
              }
            } catch {
              // ignore parse errors
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setLines((l) => [...l, { type: "error", text: String(err) }]);
          setDone(true);
        }
      }
    }

    void stream();
    return () => controller.abort();
  }, [autoFix, onDone]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const success = exitCode === 0;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-neutral-950 border border-neutral-800 rounded-lg w-full max-w-3xl flex flex-col max-h-[80vh] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-800">
          <div className="flex items-center gap-2 text-xs text-neutral-400">
            <Terminal size={13} className="text-neutral-600" />
            {done ? (
              success ? (
                <span className="flex items-center gap-1.5 text-neutral-300">
                  <CheckCircle2 size={12} className="text-neutral-400" />
                  Scan complete
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-red-400">
                  <XCircle size={12} />
                  Exit {exitCode}
                </span>
              )
            ) : (
              <span className="text-neutral-500">Scanning…</span>
            )}
          </div>
          {done && (
            <button
              onClick={onClose}
              className="p-1 text-neutral-600 hover:text-neutral-300 rounded transition-colors"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Phase step bar */}
        <div className="flex items-center gap-0 px-4 py-2 border-b border-neutral-800 overflow-x-auto">
          {PHASES.map(([id, label], i) => {
            const isCompleted = completedPhases.has(id);
            const isCurrent = currentPhase === id && !isCompleted;
            return (
              <div key={id} className="flex items-center">
                <div className={`flex items-center gap-1 text-xs whitespace-nowrap ${
                  isCompleted
                    ? "text-neutral-500"
                    : isCurrent
                      ? "text-red-400"
                      : "text-neutral-700"
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    isCompleted
                      ? "bg-neutral-600"
                      : isCurrent
                        ? "bg-red-400 animate-pulse"
                        : "bg-neutral-800"
                  }`} />
                  {label}
                </div>
                {i < PHASES.length - 1 && (
                  <span className="mx-2 text-neutral-800">›</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Output */}
        <div className="overflow-y-auto flex-1 p-4 font-mono text-xs leading-5 bg-black rounded-b-lg">
          {lines.map((l, i) => (
            <div
              key={i}
              className={
                l.type === "stderr"
                  ? "text-neutral-500"
                  : l.type === "error"
                    ? "text-red-500"
                    : "text-neutral-300"
              }
            >
              {l.text || "\u00a0"}
            </div>
          ))}
          {!done && (
            <span className="inline-block w-1.5 h-3.5 bg-red-500 animate-pulse" />
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
