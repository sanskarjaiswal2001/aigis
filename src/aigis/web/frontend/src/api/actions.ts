import { useMutation, useQuery } from "@tanstack/react-query";
import type { ActionInfo } from "../types";
import { apiFetch } from "./client";

export function useActions() {
  return useQuery<Record<string, ActionInfo>>({
    queryKey: ["actions"],
    queryFn: () => apiFetch<Record<string, ActionInfo>>("/actions"),
    staleTime: Infinity,
  });
}

interface TriggerActionVars {
  actionId: string;
  params?: Record<string, string | number | boolean>;
  runId?: string;
}

export function useTriggerAction() {
  return useMutation({
    mutationFn: ({ actionId, params = {}, runId = "web" }: TriggerActionVars) =>
      apiFetch<{ success: boolean; stdout: string; stderr: string; exit_code: number }>(
        `/actions/${actionId}`,
        {
          method: "POST",
          body: JSON.stringify({ params, run_id: runId }),
        },
      ),
  });
}

export function streamAction(
  actionId: string,
  params: Record<string, string | number | boolean>,
  runId: string,
  signal: AbortSignal,
): Promise<Response> {
  return fetch(`/api/actions/${actionId}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ params, run_id: runId }),
    signal,
  });
}
