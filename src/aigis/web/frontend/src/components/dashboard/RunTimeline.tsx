import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity } from "lucide-react";
import { useRuns } from "../../api/runs";
import { severityHex, severityOrder } from "../../utils/severity";
import type { Severity } from "../../types";

export function RunTimeline() {
  const { data: runs, isLoading } = useRuns(20);

  if (isLoading)
    return <div className="h-44 bg-neutral-900 animate-pulse rounded-lg border border-neutral-800" />;

  if (!runs || runs.length === 0)
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5 text-neutral-600 text-xs">
        No run history yet.
      </div>
    );

  const chartData = runs.map((r) => ({
    time: new Date(r.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    severity: severityOrder[r.overall_severity],
    label: r.overall_severity as Severity,
  }));

  const labels = ["OK", "WARN", "CRIT"];

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5 h-full flex flex-col" style={{ minHeight: "200px" }}>
      <div className="flex items-center gap-2 mb-4">
        <Activity size={13} className="text-neutral-600" />
        <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest">
          Run History
        </h2>
        <span className="text-neutral-700 text-xs">{runs.length} runs</span>
      </div>
      <div className="flex-1 min-h-0" style={{ minHeight: "130px" }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
          <defs>
            <linearGradient id="sevGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: "#525252" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 2]}
            ticks={[0, 1, 2]}
            tickFormatter={(v) => labels[v as number] ?? ""}
            tick={{ fontSize: 10, fill: "#525252" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#0a0a0a",
              border: "1px solid #262626",
              borderRadius: 4,
              fontSize: 11,
              color: "#a3a3a3",
            }}
            formatter={(v) => [labels[(v as number)] ?? v, "Severity"]}
            labelStyle={{ color: "#525252" }}
          />
          <Area
            type="stepAfter"
            dataKey="severity"
            stroke="#ef4444"
            strokeWidth={1.5}
            fill="url(#sevGrad)"
            dot={(props) => {
              const { cx, cy, payload } = props as {
                cx: number;
                cy: number;
                payload: { label: Severity };
              };
              return (
                <circle
                  key={`dot-${cx}-${cy}`}
                  cx={cx}
                  cy={cy}
                  r={3}
                  fill={severityHex(payload.label)}
                  stroke="#000"
                  strokeWidth={1}
                />
              );
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}
