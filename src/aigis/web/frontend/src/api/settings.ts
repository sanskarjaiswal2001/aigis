import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface Settings {
  active_target: string;
  available_targets: string[];
  target_host: string;
  target_auth: string;
  llm_enabled: boolean;
  llm_model: string;
  llm_max_tokens: number;
  llm_api_key_configured: boolean;
  collectors_enabled: string[];
  restic_repo_path: string;
  restic_warn_hours: number;
  restic_critical_hours: number;
  restic_integrity_check_enabled: boolean;
  disk_mounts: string[];
  disk_warn_pct: number;
  disk_critical_pct: number;
  load_warn_per_cpu: number;
  load_critical_per_cpu: number;
  auto_fix_min_confidence: string;
  actions_timeout_sec: number;
  run_history_last_n_runs: number;
  kb_enabled: boolean;
}

export type SettingsUpdate = Partial<Omit<Settings, "llm_api_key_configured" | "available_targets" | "target_host" | "target_auth">>;

export function useSettings() {
  return useQuery<Settings>({
    queryKey: ["settings"],
    queryFn: () => apiFetch<Settings>("/settings"),
    staleTime: 30_000,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (update: SettingsUpdate) =>
      apiFetch<Settings>("/settings", {
        method: "PATCH",
        body: JSON.stringify(update),
      }),
    onSuccess: (data) => {
      qc.setQueryData(["settings"], data);
    },
  });
}
