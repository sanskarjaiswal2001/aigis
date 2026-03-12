import { CheckCircle2, XCircle } from "lucide-react";
import { useAuditLog } from "../../api/audit";

export function AuditLog() {
  const { data: entries, isLoading } = useAuditLog(100);

  if (isLoading)
    return <div className="p-6 text-neutral-600 text-xs">Loading…</div>;

  if (!entries || entries.length === 0)
    return <div className="p-6 text-neutral-600 text-xs">No actions executed yet.</div>;

  const sorted = [...entries].reverse();

  return (
    <div className="p-6 max-w-3xl space-y-4">
      <h1 className="text-xs font-medium text-neutral-500 uppercase tracking-widest">
        Audit Log
      </h1>
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-800">
              {["Time", "Action", "Params", "Approved by", "Result", "Run ID"].map((h) => (
                <th
                  key={h}
                  className="px-4 py-2.5 text-left text-neutral-600 font-medium uppercase tracking-widest"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-900">
            {sorted.map((entry, i) => (
              <tr key={i} className="hover:bg-neutral-800/40 transition-colors">
                <td className="px-4 py-2.5 text-neutral-600 whitespace-nowrap">
                  {new Date(entry.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2.5 font-mono text-neutral-300">{entry.action_id}</td>
                <td className="px-4 py-2.5 font-mono text-neutral-600">
                  {Object.entries(entry.params ?? {})
                    .map(([k, v]) => `${k}=${String(v)}`)
                    .join(", ") || "—"}
                </td>
                <td className="px-4 py-2.5 text-neutral-500">{entry.approved_by}</td>
                <td className="px-4 py-2.5">
                  {entry.success ? (
                    <CheckCircle2 size={13} className="text-green-500" strokeWidth={2} />
                  ) : (
                    <XCircle size={13} className="text-red-400" strokeWidth={2} />
                  )}
                </td>
                <td className="px-4 py-2.5 font-mono text-neutral-700">{entry.run_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
