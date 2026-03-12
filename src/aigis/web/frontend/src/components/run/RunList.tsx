import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useRuns } from "../../api/runs";
import { SeverityBadge } from "../layout/SeverityBadge";

export function RunList() {
  const { data: runs, isLoading } = useRuns(50);

  if (isLoading)
    return <div className="p-6 text-neutral-600 text-xs">Loading…</div>;

  if (!runs || runs.length === 0)
    return <div className="p-6 text-neutral-600 text-xs">No runs yet.</div>;

  const sorted = [...runs].reverse();

  return (
    <div className="p-6 max-w-3xl space-y-4">
      <h1 className="text-xs font-medium text-neutral-500 uppercase tracking-widest">
        Run History
      </h1>
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-800">
              <th className="px-4 py-2.5 text-left text-neutral-600 font-medium uppercase tracking-widest">
                Status
              </th>
              <th className="px-4 py-2.5 text-left text-neutral-600 font-medium uppercase tracking-widest">
                Run ID
              </th>
              <th className="px-4 py-2.5 text-left text-neutral-600 font-medium uppercase tracking-widest">
                Target
              </th>
              <th className="px-4 py-2.5 text-left text-neutral-600 font-medium uppercase tracking-widest">
                Time
              </th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-900">
            {sorted.map((run) => (
              <tr key={run.run_id} className="hover:bg-neutral-800/40 transition-colors">
                <td className="px-4 py-2.5">
                  <SeverityBadge severity={run.overall_severity} size="sm" />
                </td>
                <td className="px-4 py-2.5 font-mono text-neutral-600">{run.run_id}</td>
                <td className="px-4 py-2.5 text-neutral-400">{run.target}</td>
                <td className="px-4 py-2.5 text-neutral-600 whitespace-nowrap">
                  {new Date(run.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <Link
                    to={`/runs/${run.run_id}`}
                    className="inline-flex items-center gap-1 text-neutral-600 hover:text-red-500 transition-colors"
                  >
                    <ArrowRight size={12} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
