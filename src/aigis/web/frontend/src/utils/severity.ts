import type { Severity } from "../types";

// Text color classes
export const severityColor: Record<Severity, string> = {
  OK: "text-green-500",
  WARN: "text-amber-400",
  CRITICAL: "text-red-500",
};

// Badge background + text
export const severityBg: Record<Severity, string> = {
  OK: "bg-green-950 text-green-400 border border-green-900",
  WARN: "bg-amber-950 text-amber-400 border border-amber-800",
  CRITICAL: "bg-red-950 text-red-400 border border-red-800",
};

// Left border accent for cards
export const severityBorder: Record<Severity, string> = {
  OK: "border-l-green-700",
  WARN: "border-l-amber-500",
  CRITICAL: "border-l-red-500",
};

export const severityOrder: Record<Severity, number> = {
  OK: 0,
  WARN: 1,
  CRITICAL: 2,
};

// Raw hex for Recharts (can't use Tailwind classes there)
export function severityHex(severity: Severity): string {
  return { OK: "#22c55e", WARN: "#f59e0b", CRITICAL: "#ef4444" }[severity];
}
