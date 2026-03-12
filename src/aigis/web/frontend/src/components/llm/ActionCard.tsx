import { useEffect, useRef, useState } from "react";
import { Play, Check, X, Loader } from "lucide-react";
import type { SuggestedAction, ScanEvent } from "../../types";
import { streamAction } from "../../api/actions";

interface Props {
  action: SuggestedAction;
  runId?: string;
}

export function ActionCard({ action, runId }: Props) {
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<{ type: string; text: string }[]>([]);
  const [result, setResult] = useState<{ success: boolean; exitCode: number } | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  async function handleTrigger() {
    if (running) return;
    setRunning(true);
    setLines([]);
    setResult(null);

    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      const res = await streamAction(
        action.action_id,
        action.params,
        runId ?? "web",
        controller.signal,
      );

      if (!res.ok) {
        const text = await res.text();
        setLines([{ type: "error", text }]);
        setResult({ success: false, exitCode: -1 });
        setRunning(false);
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
            const event = JSON.parse(dataLine.slice(5).trim()) as ScanEvent & { success?: boolean };
            if (event.type === "stdout" || event.type === "stderr") {
              setLines((l) => [...l, { type: event.type, text: event.line ?? "" }]);
            } else if (event.type === "done") {
              setResult({ success: event.success ?? event.exit_code === 0, exitCode: event.exit_code ?? 0 });
              setRunning(false);
            } else if (event.type === "error") {
              setLines((l) => [...l, { type: "error", text: event.message ?? "Unknown error" }]);
              setResult({ success: false, exitCode: -1 });
              setRunning(false);
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setLines((l) => [...l, { type: "error", text: String(err) }]);
        setResult({ success: false, exitCode: -1 });
      }
      setRunning(false);
    }
  }

  return (
    <div className="border border-neutral-800 rounded bg-neutral-950 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <span className="font-mono text-xs font-medium text-neutral-200">{action.action_id}</span>
          {Object.keys(action.params).length > 0 && (
            <span className="ml-2 text-xs text-neutral-600 font-mono">
              {Object.entries(action.params).map(([k, v]) => `${k}=${v}`).join(", ")}
            </span>
          )}
          {action.description && (
            <p className="text-xs text-neutral-600 mt-0.5 leading-relaxed">{action.description}</p>
          )}
          {!action.description && action.reason && (
            <p className="text-xs text-neutral-600 mt-1 leading-relaxed">{action.reason}</p>
          )}
        </div>
        <button
          onClick={() => void handleTrigger()}
          disabled={running}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-neutral-800 hover:bg-neutral-700 disabled:opacity-40 text-neutral-300 rounded border border-neutral-700 transition-colors shrink-0"
        >
          {running ? (
            <Loader size={11} className="animate-spin" />
          ) : (
            <Play size={11} strokeWidth={2.5} />
          )}
          Run
        </button>
      </div>

      {(lines.length > 0 || running) && (
        <div className="mt-2 rounded border border-neutral-800 bg-black max-h-36 overflow-y-auto p-2 font-mono text-xs leading-5">
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
          {running && <span className="inline-block w-1.5 h-3 bg-red-500 animate-pulse" />}
          <div ref={bottomRef} />
        </div>
      )}

      {result && (
        <div
          className={`mt-2 flex items-center gap-1.5 text-xs px-2 py-1 rounded border ${
            result.success
              ? "bg-neutral-900 border-neutral-700 text-neutral-400"
              : "bg-red-950 border-red-900 text-red-400"
          }`}
        >
          {result.success ? <Check size={11} /> : <X size={11} />}
          {result.success ? "Executed successfully" : `Failed (exit ${result.exitCode})`}
        </div>
      )}
    </div>
  );
}
