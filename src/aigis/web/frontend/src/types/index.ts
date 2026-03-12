export type Severity = "OK" | "WARN" | "CRITICAL";

export interface CheckResult {
  check_id: string;
  name: string;
  severity: Severity;
  message: string;
  value?: string | number | null;
  raw_signal_ref?: string | null;
}

export interface SuggestedAction {
  action_id: string;
  params: Record<string, string | number | boolean>;
  reason: string;
  description?: string | null;
}

export interface ManualRecommendation {
  description: string;
  risk_level: string;
  steps?: string[];
}

export interface RunPhase {
  category: "collection" | "evaluation" | "reporting" | "analysis" | "healing";
  description: string;
  steps: string[];
  passes: "true" | "false";
  details?: Record<string, string | number | boolean> | null;
}

export interface RunHistoryEntry {
  run_id: string;
  timestamp: string;
  target: string;
  overall_severity: Severity;
  phases: RunPhase[];
  anomaly_explanation?: string | null;
}

export interface DetectedIssue {
  component: string;
  severity: string;
  explanation: string;
}

export interface HealthReport {
  run_id: string;
  timestamp: string;
  overall_severity: Severity;
  checks: CheckResult[];
  anomaly_explanation?: string | null;
  reasoning_trace?: string | null;
  detected_issues?: DetectedIssue[] | null;
  suggested_actions?: SuggestedAction[] | null;
  manual_recommendations?: ManualRecommendation[] | null;
  metadata: Record<string, string | number>;
}

export interface AuditEntry {
  timestamp: string;
  run_id: string;
  action_id: string;
  params: Record<string, unknown>;
  approved_by: string;
  success: boolean;
  exit_code: number;
}

export interface ActionInfo {
  script: string;
  params: string[];
  auto_approve: boolean;
}

export interface RunEvent {
  type: "connected" | "new_run" | "error";
  run_id?: string;
  overall_severity?: Severity;
  timestamp?: string;
  target?: string;
  message?: string;
}

export interface ScanEvent {
  type: "stdout" | "stderr" | "done" | "error";
  line?: string;
  exit_code?: number;
  message?: string;
}
