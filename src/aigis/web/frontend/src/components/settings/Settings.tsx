import { useState } from "react";
import { Check, X, Bot, Database, Gauge, Zap, Clock, Key, Server } from "lucide-react";
import { useSettings, useUpdateSettings } from "../../api/settings";
import type { SettingsUpdate } from "../../api/settings";

const ALL_COLLECTORS = ["restic", "disk", "load", "network", "docker"] as const;

function SectionCard({
  icon,
  title,
  children,
  onSave,
  saving,
  saveResult,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  onSave: () => void;
  saving: boolean;
  saveResult: "success" | "error" | null;
}) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-neutral-800">
        <span className="text-neutral-600">{icon}</span>
        <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest flex-1">
          {title}
        </h2>
      </div>
      <div className="p-5 space-y-3">
        {children}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={onSave}
            disabled={saving}
            className="px-3 py-1.5 text-xs bg-red-700 hover:bg-red-600 disabled:opacity-40 text-white rounded transition-colors"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          {saveResult === "success" && (
            <span className="flex items-center gap-1 text-xs text-neutral-400">
              <Check size={11} /> Saved
            </span>
          )}
          {saveResult === "error" && (
            <span className="flex items-center gap-1 text-xs text-red-400">
              <X size={11} /> Save failed
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-neutral-500 w-44 shrink-0">{label}</span>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-neutral-800 border border-neutral-700 rounded px-2.5 py-1 text-xs text-neutral-300 placeholder-neutral-600 focus:outline-none focus:border-neutral-500"
    />
  );
}

function NumberInput({
  value,
  onChange,
  min,
  step,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  step?: number;
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      step={step ?? 1}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-32 bg-neutral-800 border border-neutral-700 rounded px-2.5 py-1 text-xs text-neutral-300 focus:outline-none focus:border-neutral-500"
    />
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative w-9 h-5 rounded-full transition-colors ${
        checked ? "bg-red-600" : "bg-neutral-700"
      }`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
          checked ? "translate-x-4" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function TagsInput({
  values,
  onChange,
  placeholder,
}: {
  values: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  function add() {
    const v = draft.trim();
    if (v && !values.includes(v)) onChange([...values, v]);
    setDraft("");
  }
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span
            key={v}
            className="flex items-center gap-1 px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-xs text-neutral-300 font-mono"
          >
            {v}
            <button
              onClick={() => onChange(values.filter((x) => x !== v))}
              className="text-neutral-600 hover:text-neutral-400"
            >
              <X size={10} />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
          placeholder={placeholder ?? "Type and press Enter"}
          className="flex-1 bg-neutral-800 border border-neutral-700 rounded px-2.5 py-1 text-xs text-neutral-300 placeholder-neutral-600 focus:outline-none focus:border-neutral-500"
        />
        <button
          onClick={add}
          className="px-2.5 py-1 text-xs bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 text-neutral-300 rounded transition-colors"
        >
          Add
        </button>
      </div>
    </div>
  );
}

function useSectionSave(fields: SettingsUpdate) {
  const update = useUpdateSettings();
  const [result, setResult] = useState<"success" | "error" | null>(null);
  async function save() {
    setResult(null);
    try {
      await update.mutateAsync(fields);
      setResult("success");
      setTimeout(() => setResult(null), 3000);
    } catch {
      setResult("error");
    }
  }
  return { save, saving: update.isPending, result };
}

export function Settings() {
  const { data: s, isLoading, error } = useSettings();

  // Target section state
  const [activeTarget, setActiveTarget] = useState<string | null>(null);
  const target = useSectionSave({
    ...(activeTarget !== null && { active_target: activeTarget }),
  });

  // LLM section state
  const [llmEnabled, setLlmEnabled] = useState<boolean | null>(null);
  const [llmModel, setLlmModel] = useState<string | null>(null);
  const [llmMaxTokens, setLlmMaxTokens] = useState<number | null>(null);
  const llm = useSectionSave({
    ...(llmEnabled !== null && { llm_enabled: llmEnabled }),
    ...(llmModel !== null && { llm_model: llmModel }),
    ...(llmMaxTokens !== null && { llm_max_tokens: llmMaxTokens }),
  });

  // Collectors section state
  const [collectorsEnabled, setCollectorsEnabled] = useState<string[] | null>(null);
  const [resticRepo, setResticRepo] = useState<string | null>(null);
  const [resticWarnH, setResticWarnH] = useState<number | null>(null);
  const [resticCritH, setResticCritH] = useState<number | null>(null);
  const [resticIntegrity, setResticIntegrity] = useState<boolean | null>(null);
  const [diskMounts, setDiskMounts] = useState<string[] | null>(null);
  const collectors = useSectionSave({
    ...(collectorsEnabled !== null && { collectors_enabled: collectorsEnabled }),
    ...(resticRepo !== null && { restic_repo_path: resticRepo }),
    ...(resticWarnH !== null && { restic_warn_hours: resticWarnH }),
    ...(resticCritH !== null && { restic_critical_hours: resticCritH }),
    ...(resticIntegrity !== null && { restic_integrity_check_enabled: resticIntegrity }),
    ...(diskMounts !== null && { disk_mounts: diskMounts }),
  });

  // Rules section state
  const [diskWarn, setDiskWarn] = useState<number | null>(null);
  const [diskCrit, setDiskCrit] = useState<number | null>(null);
  const [loadWarn, setLoadWarn] = useState<number | null>(null);
  const [loadCrit, setLoadCrit] = useState<number | null>(null);
  const rules = useSectionSave({
    ...(diskWarn !== null && { disk_warn_pct: diskWarn }),
    ...(diskCrit !== null && { disk_critical_pct: diskCrit }),
    ...(loadWarn !== null && { load_warn_per_cpu: loadWarn }),
    ...(loadCrit !== null && { load_critical_per_cpu: loadCrit }),
  });

  // Advanced section state
  const [confidence, setConfidence] = useState<string | null>(null);
  const [historyRuns, setHistoryRuns] = useState<number | null>(null);
  const [actionsTimeout, setActionsTimeout] = useState<number | null>(null);
  const [kbEnabled, setKbEnabled] = useState<boolean | null>(null);
  const advanced = useSectionSave({
    ...(confidence !== null && { auto_fix_min_confidence: confidence }),
    ...(historyRuns !== null && { run_history_last_n_runs: historyRuns }),
    ...(actionsTimeout !== null && { actions_timeout_sec: actionsTimeout }),
    ...(kbEnabled !== null && { kb_enabled: kbEnabled }),
  });

  if (isLoading)
    return <div className="p-6 text-neutral-600 text-xs">Loading settings…</div>;
  if (error || !s)
    return <div className="p-6 text-red-500 text-xs">Failed to load settings.</div>;

  return (
    <div className="p-6 w-full space-y-4 max-w-2xl">
      <h1 className="text-xs font-medium text-neutral-500 uppercase tracking-widest">Settings</h1>

      {/* Target */}
      <SectionCard
        icon={<Server size={13} />}
        title="Target"
        onSave={target.save}
        saving={target.saving}
        saveResult={target.result}
      >
        <Field label="Active target">
          <select
            value={activeTarget ?? s.active_target}
            onChange={(e) => setActiveTarget(e.target.value)}
            className="bg-neutral-800 border border-neutral-700 rounded px-2.5 py-1 text-xs text-neutral-300 focus:outline-none focus:border-neutral-500"
          >
            {s.available_targets.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </Field>
        <Field label="Host">
          <code className="text-xs text-neutral-400 font-mono">
            {s.target_host || "localhost"}
          </code>
        </Field>
        <Field label="Auth">
          <span className="text-xs text-neutral-500">{s.target_auth}</span>
        </Field>
        <p className="text-xs text-neutral-700">
          To add or edit targets, modify config/default.yaml directly.
        </p>
      </SectionCard>

      {/* LLM Analysis */}
      <SectionCard
        icon={<Bot size={13} />}
        title="LLM Analysis"
        onSave={llm.save}
        saving={llm.saving}
        saveResult={llm.result}
      >
        <Field label="Enabled">
          <Toggle
            checked={llmEnabled ?? s.llm_enabled}
            onChange={setLlmEnabled}
          />
        </Field>
        <Field label="Model">
          <TextInput
            value={llmModel ?? s.llm_model}
            onChange={setLlmModel}
            placeholder="claude-sonnet-4-6"
          />
        </Field>
        <Field label="Max tokens">
          <NumberInput
            value={llmMaxTokens ?? s.llm_max_tokens}
            onChange={setLlmMaxTokens}
            min={256}
            step={256}
          />
        </Field>
        <Field label="API key">
          <span
            className={`flex items-center gap-1.5 text-xs ${
              s.llm_api_key_configured ? "text-neutral-400" : "text-red-400"
            }`}
          >
            <Key size={11} />
            {s.llm_api_key_configured
              ? "Configured (set in .env)"
              : "Not configured — add ANTHROPIC_API_KEY to .env"}
          </span>
        </Field>
      </SectionCard>

      {/* Collectors */}
      <SectionCard
        icon={<Database size={13} />}
        title="Collectors"
        onSave={collectors.save}
        saving={collectors.saving}
        saveResult={collectors.result}
      >
        <Field label="Enabled collectors">
          <div className="flex flex-wrap gap-2">
            {ALL_COLLECTORS.map((c) => {
              const enabled = (collectorsEnabled ?? s.collectors_enabled).includes(c);
              return (
                <label key={c} className="flex items-center gap-1.5 text-xs text-neutral-400 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={enabled}
                    className="accent-red-500 w-3 h-3"
                    onChange={() => {
                      const cur = collectorsEnabled ?? s.collectors_enabled;
                      setCollectorsEnabled(
                        enabled ? cur.filter((x) => x !== c) : [...cur, c]
                      );
                    }}
                  />
                  {c}
                </label>
              );
            })}
          </div>
        </Field>
        <Field label="Restic repo path">
          <TextInput
            value={resticRepo ?? s.restic_repo_path}
            onChange={setResticRepo}
            placeholder="/mnt/data/restic"
          />
        </Field>
        <Field label="Restic warn (hours)">
          <NumberInput
            value={resticWarnH ?? s.restic_warn_hours}
            onChange={setResticWarnH}
            min={1}
          />
        </Field>
        <Field label="Restic critical (hours)">
          <NumberInput
            value={resticCritH ?? s.restic_critical_hours}
            onChange={setResticCritH}
            min={1}
          />
        </Field>
        <Field label="Integrity check">
          <Toggle
            checked={resticIntegrity ?? s.restic_integrity_check_enabled}
            onChange={setResticIntegrity}
          />
        </Field>
        <Field label="Disk mounts">
          <TagsInput
            values={diskMounts ?? s.disk_mounts}
            onChange={setDiskMounts}
            placeholder="e.g. /mnt/data (Enter to add)"
          />
        </Field>
      </SectionCard>

      {/* Rules */}
      <SectionCard
        icon={<Gauge size={13} />}
        title="Rules & Thresholds"
        onSave={rules.save}
        saving={rules.saving}
        saveResult={rules.result}
      >
        <Field label="Disk warn (%)">
          <NumberInput value={diskWarn ?? s.disk_warn_pct} onChange={setDiskWarn} min={1} step={1} />
        </Field>
        <Field label="Disk critical (%)">
          <NumberInput value={diskCrit ?? s.disk_critical_pct} onChange={setDiskCrit} min={1} step={1} />
        </Field>
        <Field label="Load warn (per CPU)">
          <NumberInput value={loadWarn ?? s.load_warn_per_cpu} onChange={setLoadWarn} min={0.1} step={0.5} />
        </Field>
        <Field label="Load critical (per CPU)">
          <NumberInput value={loadCrit ?? s.load_critical_per_cpu} onChange={setLoadCrit} min={0.1} step={0.5} />
        </Field>
      </SectionCard>

      {/* Scheduled Runs */}
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
        <div className="flex items-center gap-2 px-5 py-3 border-b border-neutral-800">
          <Clock size={13} className="text-neutral-600" />
          <h2 className="text-xs font-medium text-neutral-400 uppercase tracking-widest">
            Scheduled Runs
          </h2>
        </div>
        <div className="p-5 space-y-3 text-xs text-neutral-500">
          <p>Aigis ships with a systemd timer that runs every 15 minutes with <code className="font-mono text-neutral-400">--auto-fix</code>.</p>
          <p className="text-neutral-600">Copy the unit files, then enable:</p>
          <div className="space-y-1.5">
            {[
              "sudo cp scripts/systemd/aigis.service /etc/systemd/system/",
              "sudo cp scripts/systemd/aigis.timer  /etc/systemd/system/",
              "sudo systemctl daemon-reload",
              "sudo systemctl enable --now aigis.timer",
            ].map((cmd) => (
              <code key={cmd} className="block bg-neutral-950 border border-neutral-800 rounded px-3 py-1.5 font-mono text-neutral-400 text-xs select-all">
                {cmd}
              </code>
            ))}
          </div>
          <p className="text-neutral-700">
            Check status: <code className="font-mono text-neutral-600">journalctl -u aigis.service -f</code>
          </p>
        </div>
      </div>

      {/* Advanced */}
      <SectionCard
        icon={<Zap size={13} />}
        title="Advanced"
        onSave={advanced.save}
        saving={advanced.saving}
        saveResult={advanced.result}
      >
        <Field label="Auto-fix confidence">
          <select
            value={confidence ?? s.auto_fix_min_confidence}
            onChange={(e) => setConfidence(e.target.value)}
            className="bg-neutral-800 border border-neutral-700 rounded px-2.5 py-1 text-xs text-neutral-300 focus:outline-none focus:border-neutral-500"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </Field>
        <Field label="History depth (runs)">
          <NumberInput
            value={historyRuns ?? s.run_history_last_n_runs}
            onChange={setHistoryRuns}
            min={1}
          />
        </Field>
        <Field label="Action timeout (sec)">
          <NumberInput
            value={actionsTimeout ?? s.actions_timeout_sec}
            onChange={setActionsTimeout}
            min={30}
            step={30}
          />
        </Field>
        <Field label="Knowledge base">
          <Toggle
            checked={kbEnabled ?? s.kb_enabled}
            onChange={setKbEnabled}
          />
        </Field>
      </SectionCard>
    </div>
  );
}
