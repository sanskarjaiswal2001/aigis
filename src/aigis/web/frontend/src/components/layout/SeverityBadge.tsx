import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import type { Severity } from "../../types";
import { severityBg } from "../../utils/severity";

const icons: Record<Severity, React.ElementType> = {
  OK: CheckCircle2,
  WARN: AlertTriangle,
  CRITICAL: XCircle,
};

interface Props {
  severity: Severity;
  size?: "sm" | "md" | "lg";
}

export function SeverityBadge({ severity, size = "md" }: Props) {
  const Icon = icons[severity];
  const sizeClass =
    size === "sm"
      ? "text-xs px-2 py-0.5 gap-1"
      : size === "lg"
        ? "text-sm px-3 py-1.5 gap-1.5 font-semibold tracking-wide"
        : "text-xs px-2.5 py-1 gap-1.5";
  const iconSize = size === "lg" ? 15 : 12;

  return (
    <span
      className={`inline-flex items-center rounded font-medium uppercase tracking-widest ${sizeClass} ${severityBg[severity]}`}
    >
      <Icon size={iconSize} strokeWidth={2.5} />
      {severity}
    </span>
  );
}
