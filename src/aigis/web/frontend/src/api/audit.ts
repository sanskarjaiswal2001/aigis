import { useQuery } from "@tanstack/react-query";
import type { AuditEntry } from "../types";
import { apiFetch } from "./client";

export function useAuditLog(limit = 100) {
  return useQuery<AuditEntry[]>({
    queryKey: ["audit", limit],
    queryFn: () => apiFetch<AuditEntry[]>(`/audit?limit=${limit}`),
    staleTime: 60_000,
  });
}
