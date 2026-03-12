import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Play, Zap } from "lucide-react";
import { ScanOutput } from "./ScanOutput";

export function ScanButton() {
  const [scanning, setScanning] = useState(false);
  const [autoFix, setAutoFix] = useState(false);
  const queryClient = useQueryClient();

  function handleDone() {
    void queryClient.invalidateQueries({ queryKey: ["runs"] });
  }

  return (
    <>
      <div className="flex items-center gap-3">
        <button
          onClick={() => setScanning(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded text-xs font-medium tracking-wide transition-colors"
        >
          <Play size={12} strokeWidth={2.5} />
          Run Scan
        </button>
        <label className="flex items-center gap-1.5 text-xs text-neutral-500 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={autoFix}
            onChange={(e) => setAutoFix(e.target.checked)}
            className="accent-red-500 w-3 h-3"
          />
          <Zap size={11} className="text-neutral-600" />
          Auto-fix
        </label>
      </div>

      {scanning && (
        <ScanOutput
          autoFix={autoFix}
          onDone={handleDone}
          onClose={() => setScanning(false)}
        />
      )}
    </>
  );
}
