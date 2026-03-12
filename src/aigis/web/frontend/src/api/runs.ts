import { useQuery } from "@tanstack/react-query";
import type { HealthReport, RunHistoryEntry } from "../types";
import { apiFetch } from "./client";

export function useRuns(limit = 50) {
  return useQuery<RunHistoryEntry[]>({
    queryKey: ["runs", limit],
    queryFn: () => apiFetch<RunHistoryEntry[]>(`/runs?limit=${limit}`),
    staleTime: 60_000,
  });
}

export function useLatestRun() {
  return useQuery<RunHistoryEntry>({
    queryKey: ["runs", "latest"],
    queryFn: () => apiFetch<RunHistoryEntry>("/runs/latest"),
    staleTime: 30_000,
    retry: false,
  });
}

export function useRunReport(runId: string | undefined) {
  return useQuery<HealthReport>({
    queryKey: ["runs", runId, "report"],
    queryFn: () => apiFetch<HealthReport>(`/runs/${runId}/report`),
    enabled: !!runId,
    staleTime: Infinity,
  });
}

export function useLatestReport() {
  const { data: latest } = useLatestRun();
  return useRunReport(latest?.run_id);
}
