import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Search,
  Plus,
  RefreshCw,
  Trash2,
  Play,
  Database,
  FileText,
  Settings,
  BarChart3,
  Clock,
  ChevronRight,
  ExternalLink,
  Download,
  Upload,
  Loader2,
  Info,
  AlertTriangle,
  Check,
  X,
  Copy,
  FileCheck,
} from "lucide-react";
import "./styles.css";

const workspaceSchema = z.object({
  name: z.string().optional(),
  workspace_dir: z.string(),
});

const workspacesSchema = z.object({
  workspaces: z.array(workspaceSchema),
});

const profileSchema = z.object({
  name: z.string(),
  inputs: z.record(z.string(), z.unknown()).optional(),
  analysis: z.record(z.string(), z.unknown()).optional(),
});

const profilesSchema = z.object({
  profiles: z.array(profileSchema),
});

const specAssetSchema = z.object({
  asset_id: z.string(),
  display_name: z.string().optional(),
  version: z.string().optional(),
  parser_used: z.string().optional(),
  document_id: z.string().optional(),
});

const specAssetsSchema = z.object({
  assets: z.array(specAssetSchema),
});

const sourceSchema = z.object({
  name: z.string(),
  kind: z.string(),
  connector_type: z.string(),
  mode: z.string().optional(),
  enabled: z.boolean().optional(),
  status: z.string().optional(),
  status_reason: z.string().optional(),
  last_refresh: z.string().nullable().optional(),
  document_count: z.number().optional(),
  selector: z
    .object({
      name: z.string(),
      source: z.string(),
    })
    .nullable()
    .optional(),
});

const selectorSchema = z.object({
  name: z.string(),
  source: z.string(),
  selector: z.record(z.string(), z.unknown()).optional(),
});

const sourcesSchema = z.object({
  sources: z.array(sourceSchema),
  selectors: z.array(selectorSchema).default([]),
});

const analyzeSchema = z.object({
  run_id: z.string(),
  status: z.string(),
  issue_key: z.string(),
  profile: z.string(),
  summary: z.record(z.string(), z.unknown()),
  sections: z.record(z.string(), z.unknown()),
  citations: z.array(z.record(z.string(), z.unknown())),
  evidence_coverage: z
    .object({
      jira_found: z.boolean().optional(),
      confluence_count: z.number().optional(),
      spec_count: z.number().optional(),
      missing: z.array(z.string()).optional(),
    })
    .optional(),
  evidence_sources: z.array(z.string()),
  missing_evidence: z.array(z.unknown()),
  artifacts: z.record(z.string(), z.unknown()),
});

const runsSchema = z.object({
  runs: z.array(
    z.object({
      run_id: z.string(),
      status: z.string(),
      issue_key: z.string().nullable().optional(),
      updated_at: z.string().nullable().optional(),
      run_dir: z.string().optional(),
      artifact_count: z.number().optional(),
    }),
  ),
});

const runDetailSchema = z.object({
  manifest: z.object({
    input_config: z.record(z.string(), z.unknown()).optional(),
  }).passthrough(),
  artifact_inventory: z.array(
    z.object({
      artifact_type: z.string(),
      path: z.string().optional(),
      exists: z.boolean().optional(),
      status: z.string().optional(),
      stale: z.boolean().optional(),
      step_name: z.string().optional(),
    }).passthrough(),
  ).optional(),
}).passthrough();

const deepAnalysisArtifactSchema = z.object({
  payload: z.object({
    title: z.string().optional(),
    issue_id: z.string().optional(),
    answer: z.object({ text: z.string().optional() }).optional(),
    shared_retrieval_bundle: z
      .object({
        source_breakdown: z.record(z.string(), z.object({
          result_count: z.number().optional(),
        }).passthrough()).optional(),
      })
      .passthrough()
      .optional(),
    section_outputs: z.record(z.string(), z.unknown()).optional(),
    confluence_evidence: z.object({ citations: z.array(z.record(z.string(), z.unknown())).optional() }).optional(),
    spec_evidence: z.object({ citations: z.array(z.record(z.string(), z.unknown())).optional() }).optional(),
    knowledge_artifacts: z.record(z.string(), z.unknown()).optional(),
  }).passthrough(),
});

const llmVerificationSchema = z.object({
  payload: z.object({
    backend: z.string(),
    mode: z.string(),
    verification_text: z.string(),
    created_at: z.string().optional(),
  }).passthrough(),
});

const llmVerificationHistorySchema = z.object({
  payload: z.object({
    verifications: z.array(
      z.object({
        backend: z.string(),
        mode: z.string(),
        verification_text: z.string(),
        created_at: z.string().optional(),
      }).passthrough(),
    ),
  }).passthrough(),
});

const verifyRunSchema = z.object({
  verification: z.object({
    backend: z.string(),
    mode: z.string(),
    verification_text: z.string(),
    created_at: z.string().optional(),
  }).passthrough(),
});

type Workspace = z.infer<typeof workspaceSchema>;
type Profile = z.infer<typeof profileSchema>;
type Source = z.infer<typeof sourceSchema>;
type Selector = z.infer<typeof selectorSchema>;
type SpecAsset = z.infer<typeof specAssetSchema>;
type AnalyzeResult = z.infer<typeof analyzeSchema>;
type SetupItem = {
  label: string;
  ok: boolean;
  detail: string;
  target: Page;
};
type EvidenceCoverage = {
  jiraFound: boolean;
  confluenceCount: number;
  specCount: number;
  missing: string[];
};
type RunTab = "summary" | "rca" | "spec_impact" | "decision_brief" | "evidence" | "verification" | "artifacts";
type SourceWizardStep = 0 | 1 | 2 | 3 | 4;
type SourceFormValues = {
  kind: string;
  name: string;
  baseUrl: string;
  token: string;
  selectorName: string;
  selectorValue: string;
  filePath: string;
  fileType: string;
  parser: string;
  originalFilename: string;
};
type ProfileFormValues = {
  name: string;
  jiraSource: string;
  jiraSelector: string;
  evidenceSource: string;
  evidenceSelector: string;
  specAssetId: string;
  topK: number;
  promptMode: string;
  llmBackend: string;
  llmModel: string;
  llmBaseUrl: string;
};
type SpecIngestValues = {
  specPdf: string;
  assetId: string;
  displayName: string;
  mineruPythonExe: string;
};

type Page = "analyze" | "runs" | "sources" | "profiles" | "wiki" | "reports" | "spec";

const queryClient = new QueryClient();

function tokenHeaders(): HeadersInit {
  const token = localStorage.getItem("ssdPortalToken") || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiJson<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...tokenHeaders(),
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep HTTP status text.
    }
    throw new Error(message);
  }
  return schema.parse(await response.json());
}

function remember(key: string, value: string) {
  if (!value.trim()) {
    return;
  }
  const storageKey = `ssdPortalRecent:${key}`;
  const current = JSON.parse(localStorage.getItem(storageKey) || "[]") as string[];
  const next = [value, ...current.filter((item) => item !== value)].slice(0, 5);
  localStorage.setItem(storageKey, JSON.stringify(next));
}

function readRecent(key: string): string[] {
  return JSON.parse(localStorage.getItem(`ssdPortalRecent:${key}`) || "[]") as string[];
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("ssdPortalToken") || "");
  const [page, setPage] = useState<Page>("analyze");
  const [workspaceDir, setWorkspaceDir] = useState("");
  const [workspaceName, setWorkspaceName] = useState("real-workspace");
  const [latestResult, setLatestResult] = useState<AnalyzeResult | null>(null);
  const queryClient = useQueryClient();

  const workspaces = useQuery({
    queryKey: ["workspaces", token],
    queryFn: () => apiJson("/api/workspaces", workspacesSchema),
    enabled: Boolean(token),
  });

  const selectedWorkspace = workspaceDir || workspaces.data?.workspaces[0]?.workspace_dir || "";
  const profiles = useQuery({
    queryKey: ["profiles", selectedWorkspace],
    queryFn: () => apiJson(`/api/workspace/profiles?workspace_dir=${encodeURIComponent(selectedWorkspace)}`, profilesSchema),
    enabled: Boolean(token && selectedWorkspace),
  });
  const sources = useQuery({
    queryKey: ["sources", selectedWorkspace],
    queryFn: () => apiJson(`/api/workspace/sources?workspace_dir=${encodeURIComponent(selectedWorkspace)}`, sourcesSchema),
    enabled: Boolean(token && selectedWorkspace),
  });

  function saveToken() {
    localStorage.setItem("ssdPortalToken", token);
    queryClient.invalidateQueries();
  }

  const createWorkspace = useMutation({
    mutationFn: (name: string) =>
      apiJson("/api/workspaces", workspaceSchema, {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: (workspace) => {
      setWorkspaceDir(workspace.workspace_dir);
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });

  return (
    <div className="app-shell">
      <aside className="nav">
        <div className="nav-brand">
          <span className="brand-mark" aria-hidden="true">S</span>
          <div>
            <p className="eyebrow">SSD Platform</p>
            <h1>Codex Ops</h1>
          </div>
        </div>
        <div className="nav-group-label">Workspace</div>
        <nav>
          {[
            { id: "analyze", label: "Analyze", icon: Search },
            { id: "runs", label: "Runs", icon: Clock },
            { id: "sources", label: "Sources", icon: Database },
            { id: "profiles", label: "Profiles", icon: Settings },
            { id: "wiki", label: "Wiki", icon: FileText },
            { id: "reports", label: "Reports", icon: BarChart3 },
            { id: "spec", label: "Spec Lab", icon: FileText },
          ].map(({ id, label, icon: Icon }) => (
            <button className={page === id ? "active" : ""} key={id} onClick={() => setPage(id as Page)} type="button">
              <Icon size={18} /> {label}
            </button>
          ))}
          <a href="/admin/"><ExternalLink size={18} /> Admin</a>
        </nav>
        <div className="nav-footer">
          <span className="status-dot" aria-hidden="true" />
          <span>{token ? "Runner connected" : "Runner waiting"}</span>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="toolbar-title">
            <span className="toolbar-dot" aria-hidden="true" />
            <div>
              <p className="eyebrow">Local Runner</p>
              <strong>{selectedWorkspace ? "SSD Knowledge Workspace" : "Connect Runner"}</strong>
            </div>
          </div>
          <div className="toolbar-controls" aria-label="Runner controls">
            <label>
              Token
              <input value={token} onChange={(event) => setToken(event.target.value)} onBlur={saveToken} placeholder="change-me" />
            </label>
            <label>
              Workspace
              <select value={selectedWorkspace} onChange={(event) => setWorkspaceDir(event.target.value)}>
                {!selectedWorkspace && <option value="">No workspace</option>}
                {(workspaces.data?.workspaces || []).map((workspace: Workspace) => (
                  <option key={workspace.workspace_dir} value={workspace.workspace_dir}>
                    {workspace.name || workspace.workspace_dir}
                  </option>
                ))}
              </select>
            </label>
            <label>
              New
              <span className="inline-create">
                <input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} />
                <button type="button" onClick={() => createWorkspace.mutate(workspaceName)}>
                  Create
                </button>
              </span>
            </label>
          </div>
        </header>

        {!token ? (
          <EmptyState title="Connect the runner" body="Enter the local runner token to load workspaces, sources, profiles, and runs." />
        ) : page === "analyze" ? (
          <AnalyzePage
            workspaceDir={selectedWorkspace}
            profiles={profiles.data?.profiles || []}
            sources={sources.data?.sources || []}
            latestResult={latestResult}
            onResult={setLatestResult}
            onNavigate={setPage}
          />
        ) : page === "runs" ? (
          <RunsPage workspaceDir={selectedWorkspace} onRerun={(result) => setLatestResult(result)} />
        ) : page === "sources" ? (
          <SourcesPage workspaceDir={selectedWorkspace} />
        ) : page === "profiles" ? (
          <ProfilesPage
            workspaceDir={selectedWorkspace}
            profiles={profiles.data?.profiles || []}
            sources={sources.data?.sources || []}
            selectors={sources.data?.selectors || []}
          />
        ) : page === "spec" ? (
          <SpecLabPage workspaceDir={selectedWorkspace} />
        ) : (
          <ModulePlaceholder page={page} latestResult={latestResult} />
        )}
      </main>
    </div>
  );
}

function AnalyzePage({
  workspaceDir,
  profiles,
  sources,
  latestResult,
  onResult,
  onNavigate,
}: {
  workspaceDir: string;
  profiles: Profile[];
  sources: Source[];
  latestResult: AnalyzeResult | null;
  onResult: (result: AnalyzeResult) => void;
  onNavigate: (page: Page) => void;
}) {
  const [recentIssues] = useState(readRecent("issues"));
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const form = useForm({ defaultValues: { issueKey: recentIssues[0] || "", profile: profiles[0]?.name || "" } });
  const mutation = useMutation({
    mutationFn: (values: { issueKey: string; profile: string }) =>
      apiJson(
        "/api/workspace/analyze-jira",
        analyzeSchema,
        {
          method: "POST",
          body: JSON.stringify({
            workspace_dir: workspaceDir,
            issue_key: values.issueKey,
            profile: values.profile,
          }),
        },
      ),
    onSuccess: (result, values) => {
      remember("issues", values.issueKey);
      remember("profiles", values.profile);
      remember("runs", result.run_id);
      onResult(result);
    },
  });

  const specAssets = useQuery({
    queryKey: ["workspace-spec-assets", workspaceDir],
    queryFn: () => apiJson(`/api/workspace/spec-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`, specAssetsSchema),
    enabled: Boolean(workspaceDir),
  });
  const jiraReady = sources.some((source) => source.kind === "jira" && source.enabled !== false);
  const confluenceReady = sources.some((source) => source.kind === "confluence" && source.enabled !== false);
  const mineruReady = Boolean(specAssets.data?.assets.some((asset) => asset.asset_id === "nvme-spec-mineru" && asset.parser_used === "mineru"));
  const profileReady = profiles.some((profile) => {
    const text = JSON.stringify(profile);
    return text.includes("nvme-spec-mineru") && text.includes("llm_backend");
  });
  const setupItems: SetupItem[] = [
    { label: "Jira Source", ok: jiraReady, detail: jiraReady ? "Configured" : "Add a Jira source", target: "sources" },
    { label: "Confluence Source", ok: confluenceReady, detail: confluenceReady ? "Configured" : "Add a Confluence source", target: "sources" },
    { label: "NVMe Spec Asset", ok: mineruReady, detail: mineruReady ? "nvme-spec-mineru / MinerU" : "Parse or register nvme-spec-mineru", target: "spec" },
    { label: "Analysis Profile", ok: profileReady, detail: profileReady ? "Profile references spec + LLM settings" : "Create a profile with spec and LLM settings", target: "profiles" },
  ];
  const setupComplete = Boolean(workspaceDir && setupItems.every((item) => item.ok));

  return (
    <section className="page-grid analyze-grid">
      <div className="primary-surface transcript-surface">
        <div className="section-heading chat-heading">
          <p className="eyebrow">Analyze</p>
          <h2>Grounded Jira analysis</h2>
          <p>Run PageIndex-first analysis over Jira, Confluence, and spec evidence.</p>
        </div>

        <SetupChecklist items={setupItems} onNavigate={onNavigate} />

        <div className="message-stack">
          <article className="message system-message">
            <div className="message-meta">system</div>
            <p>PageIndex-first retrieval, ACL filtering before ranking, citation-bearing answer assembly.</p>
          </article>
          <article className="message assistant-message">
            <div className="message-meta">workspace</div>
            <p>
              {setupComplete
                ? "Sources and profiles are ready. Choose an issue key and run the analysis."
                : "Connect a source and create a profile before starting the next grounded run."}
            </p>
          </article>
          {latestResult && (
            <article className="message user-message">
              <div className="message-meta">latest run</div>
              <p>{latestResult.issue_key} completed as {latestResult.run_id}</p>
            </article>
          )}
        </div>

        <button className="plain-action" type="button" onClick={() => setAdvancedOpen((value) => !value)}>
          {advancedOpen ? "Hide Advanced" : "Advanced"}
        </button>
        {advancedOpen && (
          <div className="advanced-grid">
            <span>Source override: profile default</span>
            <span>Spec assets: profile default</span>
            <span>LLM: profile default</span>
            <span>Top K: profile default</span>
          </div>
        )}

        {mutation.error && <div className="error">{String(mutation.error.message)}</div>}

        <form className="run-form command-composer" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <label>
            Issue Key
            <input {...form.register("issueKey", { required: true })} placeholder="SSD-DEMO-A" list="recent-issues" />
            <datalist id="recent-issues">
              {recentIssues.map((issue) => (
                <option key={issue} value={issue} />
              ))}
            </datalist>
          </label>
          <label>
            Profile
            <select {...form.register("profile", { required: true })}>
              {profiles.map((profile) => (
                <option key={profile.name} value={profile.name}>
                  {profile.name}
                </option>
              ))}
            </select>
          </label>
          <button disabled={!setupComplete || mutation.isPending} type="submit">
            {mutation.isPending ? <><RefreshCw size={16} className="spin" /> Running...</> : <><Play size={16} /> Run Analysis</>}
          </button>
        </form>
      </div>

      <ResultView result={latestResult} />
    </section>
  );
}

function SetupChecklist({ items, onNavigate }: { items: SetupItem[]; onNavigate: (page: Page) => void }) {
  const complete = items.filter((item) => item.ok).length;
  return (
    <div className="setup-checklist">
      <div className="setup-header">
        <div>
          <p className="eyebrow">Setup Checklist</p>
          <strong>{complete} / {items.length} ready</strong>
        </div>
        <span className={complete === items.length ? "setup-badge ready" : "setup-badge"}>
          {complete === items.length ? <><CheckCircle2 size={14} /> Ready</> : <><AlertCircle size={14} /> Action needed</>}
        </span>
      </div>
      <div className="setup-items">
        {items.map((item) => (
          <button className={item.ok ? "setup-item ready" : "setup-item"} key={item.label} onClick={() => onNavigate(item.target)} type="button">
            <span>{item.ok ? <Check size={16} /> : <AlertTriangle size={16} />}</span>
            <strong>{item.label}</strong>
            <small>{item.detail}</small>
          </button>
        ))}
      </div>
    </div>
  );
}

function Stepper({ steps }: { steps: { label: string; ok: boolean }[] }) {
  return (
    <div className="stepper" aria-label="Setup steps">
      {steps.map((step, index) => (
        <div className={step.ok ? "step ready" : "step"} key={step.label}>
          <span>{step.ok ? <CheckCircle2 size={16} /> : index + 1}</span>
          <strong>{step.label}</strong>
        </div>
      ))}
    </div>
  );
}

function WizardActions({
  primaryLabel,
  primaryDisabled = false,
  onPrimary,
  backLabel,
  onBack,
  submit = false,
}: {
  primaryLabel: string;
  primaryDisabled?: boolean;
  onPrimary?: () => void;
  backLabel?: string;
  onBack?: () => void;
  submit?: boolean;
}) {
  return (
    <div className="wizard-actions">
      {backLabel && (
        <button className="secondary-action" onClick={onBack} type="button">
          {backLabel}
        </button>
      )}
      <button disabled={primaryDisabled} onClick={onPrimary} type={submit ? "submit" : "button"}>
        {primaryLabel}
      </button>
    </div>
  );
}

function SourcesPage({ workspaceDir }: { workspaceDir: string }) {
  const queryClient = useQueryClient();
  const [wizardStep, setWizardStep] = useState<SourceWizardStep>(0);
  const form = useForm<SourceFormValues>({
    defaultValues: {
      kind: "jira",
      name: "",
      baseUrl: "",
      token: "",
      selectorName: "",
      selectorValue: "",
      filePath: "",
      fileType: "pdf",
      parser: "auto",
      originalFilename: "",
    },
  });
  const sources = useQuery({
    queryKey: ["sources", workspaceDir],
    queryFn: () => apiJson(`/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`, sourcesSchema),
    enabled: Boolean(workspaceDir),
  });
  const watchedKind = form.watch("kind");
  const watchedName = form.watch("name");
  const watchedBaseUrl = form.watch("baseUrl");
  const watchedFilePath = form.watch("filePath");
  const watchedSelectorValue = form.watch("selectorValue");
  const isFileUpload = watchedKind === "file_upload";
  const sourceCreated = Boolean((sources.data?.sources || []).some((source) => source.name === watchedName));
  const selectedSource = (sources.data?.sources || []).find((source) => source.name === watchedName);
  const sourceTested = Boolean(selectedSource && selectedSource.status !== "stale");
  const sourceFetched = Boolean(selectedSource && (selectedSource.document_count || 0) > 0);
  const sourceSteps = isFileUpload
    ? [
        { label: "File Details", ok: Boolean(watchedKind && watchedName && watchedFilePath) },
        { label: "Test", ok: sourceTested },
        { label: "Parse", ok: sourceFetched },
      ]
    : [
        { label: "Source Details", ok: Boolean(watchedKind && watchedName && watchedBaseUrl) },
        { label: "Authentication", ok: true },
        { label: "Selector", ok: Boolean(watchedSelectorValue) },
        { label: "Test", ok: sourceTested },
        { label: "Fetch", ok: sourceFetched },
      ];
  const currentSelector = selectedSource?.selector || sources.data?.selectors.find((row) => row.source === watchedName);
  const canAdvanceDetails = isFileUpload
    ? Boolean(watchedKind && watchedName && watchedFilePath)
    : Boolean(watchedKind && watchedName && watchedBaseUrl);
  const canAdvanceSelector = Boolean(watchedSelectorValue);
  const resetSourceWizard = () => {
    form.reset({
      kind: "jira",
      name: "",
      baseUrl: "",
      token: "",
      selectorName: "",
      selectorValue: "",
      filePath: "",
      fileType: "pdf",
      parser: "auto",
      originalFilename: "",
    });
    setWizardStep(0);
  };
  const createSource = useMutation({
    mutationFn: (values: SourceFormValues) => {
      if (values.kind === "file_upload") {
        // File Upload source
        return apiJson(
          "/api/workspace/sources",
          z.unknown(),
          {
            method: "POST",
            body: JSON.stringify({
              workspace_dir: workspaceDir,
              name: values.name,
              connector_type: "file_upload.local",
              file_path: values.filePath,
              file_type: values.fileType,
              parser: values.parser,
              original_filename: values.originalFilename || values.filePath.split(/[/\\]/).pop(),
            }),
          },
        );
      } else {
        // Jira or Confluence source
        const isJira = values.kind === "jira";
        return apiJson(
          "/api/workspace/sources",
          z.unknown(),
          {
            method: "POST",
            body: JSON.stringify({
              workspace_dir: workspaceDir,
              name: values.name,
              connector_type: isJira ? "jira.atlassian_api" : "confluence.atlassian_api",
              base_url: values.baseUrl,
              token: values.token,
              defaults: { fetch_backend: "native", include_comments: true, include_attachments: true },
              selector: isJira
                ? { name: values.selectorName || `${values.name}_issue`, type: "issue", issue_key: values.selectorValue }
                : { name: values.selectorName || `${values.name}_space`, type: "space_slice", space_key: values.selectorValue },
            }),
          },
        );
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", workspaceDir] });
      setWizardStep(3);
    },
  });
  const refresh = useMutation({
    mutationFn: ({ name, selector }: { name: string; selector: string }) =>
      apiJson(
        `/api/workspace/sources/${name}/refresh`,
        z.unknown(),
        {
          method: "POST",
          body: JSON.stringify({ workspace_dir: workspaceDir, selector_profile: selector }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", workspaceDir] });
      setWizardStep(4);
    },
  });
  const testSource = useMutation({
    mutationFn: ({ name, selector }: { name: string; selector: string }) =>
      apiJson(
        `/api/workspace/sources/${name}/test`,
        z.unknown(),
        {
          method: "POST",
          body: JSON.stringify({ workspace_dir: workspaceDir, selector_profile: selector }),
        },
      ),
    onSuccess: () => setWizardStep(4),
  });

  return (
    <section className="page-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Sources</p>
          <h2>Connect Data Sources</h2>
          <p>Add Jira, Confluence, or File Upload sources, test them, then refresh data into the workspace.</p>
        </div>
        <Stepper steps={sourceSteps} />
        <form className="stack-form" onSubmit={form.handleSubmit((values) => createSource.mutate(values))}>
          {wizardStep === 0 && (
            <>
              <label>
                Source type
                <select {...form.register("kind")}>
                  <option value="jira">Jira</option>
                  <option value="confluence">Confluence</option>
                  <option value="file_upload">File Upload</option>
                </select>
              </label>
              <label>
                Source name
                <input {...form.register("name", { required: true })} placeholder={watchedKind === "file_upload" ? "nvme_spec" : "ssd_jira"} />
              </label>
              {watchedKind === "file_upload" ? (
                <>
                  <label>
                    File path
                    <input {...form.register("filePath", { required: true })} placeholder="D:\specs\nvme.pdf" />
                  </label>
                  <label>
                    File type
                    <select {...form.register("fileType")}>
                      <option value="pdf">PDF</option>
                      <option value="docx">DOCX</option>
                      <option value="xlsx">XLSX</option>
                      <option value="pptx">PPTX</option>
                      <option value="image">Image</option>
                    </select>
                  </label>
                  <label>
                    Parser
                    <select {...form.register("parser")}>
                      <option value="auto">Auto (MinerU + fallback)</option>
                      <option value="mineru">MinerU</option>
                      <option value="pypdf">PyPDF</option>
                    </select>
                  </label>
                </>
              ) : (
                <label>
                  Base URL
                  <input {...form.register("baseUrl", { required: true })} placeholder="https://jira.example.com" />
                </label>
              )}
              <WizardActions
                primaryLabel={watchedKind === "file_upload" ? "Next: Test File" : "Next: Authentication"}
                primaryDisabled={!canAdvanceDetails}
                onPrimary={() => setWizardStep(watchedKind === "file_upload" ? 3 : 1)}
              />
            </>
          )}
          {wizardStep === 1 && (
            <>
              <label>
                Token
                <input {...form.register("token")} type="password" placeholder="Stored locally and redacted" />
              </label>
              <p className="form-hint">Inline bearer tokens are stored only in the workspace `.local/credentials.yaml` and are redacted from API responses.</p>
              <WizardActions
                backLabel="Back"
                onBack={() => setWizardStep(0)}
                primaryLabel="Next: Selector"
                onPrimary={() => setWizardStep(2)}
              />
            </>
          )}
          {wizardStep === 2 && (
            <>
              <label>
                Selector name
                <input {...form.register("selectorName")} placeholder="ssd_issue_selector" />
              </label>
              <label>
                {watchedKind === "jira" ? "Issue key" : "Space key"}
                <input {...form.register("selectorValue", { required: true })} placeholder={watchedKind === "jira" ? "SSD-DEMO-A" : "SSDENG"} />
              </label>
              <WizardActions
                backLabel="Back"
                onBack={() => setWizardStep(1)}
                primaryLabel={createSource.isPending ? "Saving..." : "Save source and selector"}
                primaryDisabled={!canAdvanceSelector || createSource.isPending}
                submit
              />
            </>
          )}
          {wizardStep === 3 && (
            <>
              <div className="notice">
                {isFileUpload
                  ? "File source saved. Test file accessibility before parsing."
                  : "Source saved. Test the configured connector before fetching data."}
              </div>
              <WizardActions
                backLabel="Back"
                onBack={() => setWizardStep(isFileUpload ? 0 : 2)}
                primaryLabel={testSource.isPending ? "Testing..." : (isFileUpload ? "Test File" : "Test Connection")}
                primaryDisabled={isFileUpload ? testSource.isPending : (!currentSelector || testSource.isPending)}
                onPrimary={() => {
                  if (isFileUpload) {
                    testSource.mutate({ name: watchedName, selector: "" });
                  } else if (currentSelector) {
                    testSource.mutate({ name: watchedName, selector: currentSelector.name });
                  }
                }}
              />
            </>
          )}
          {wizardStep === 4 && (
            <>
              <div className={sourceFetched ? "notice" : "advanced-grid"}>
                {sourceFetched
                  ? `${selectedSource?.document_count || 0} documents ${isFileUpload ? "parsed" : "fetched"}.`
                  : isFileUpload
                  ? "File is accessible. Parse the file into the workspace."
                  : "Connection is ready. Fetch data into the workspace."}
              </div>
              <WizardActions
                backLabel="Back"
                onBack={() => setWizardStep(3)}
                primaryLabel={refresh.isPending ? (isFileUpload ? "Parsing..." : "Fetching...") : (isFileUpload ? "Parse File" : "Fetch Data")}
                primaryDisabled={isFileUpload ? refresh.isPending : (!currentSelector || refresh.isPending)}
                onPrimary={() => {
                  if (isFileUpload) {
                    refresh.mutate({ name: watchedName, selector: "" });
                  } else if (currentSelector) {
                    refresh.mutate({ name: watchedName, selector: currentSelector.name });
                  }
                }}
              />
              <button className="secondary-action" onClick={resetSourceWizard} type="button">
                <Plus size={16} /> Add another source
              </button>
            </>
          )}
        </form>
      </div>

      <ListPanel title="Configured Sources">
        {(sources.data?.sources || []).map((source) => {
          const selector = source.selector || sources.data?.selectors.find((row) => row.source === source.name);
          return (
          <div className="list-row" key={source.name}>
            <strong>{source.name}</strong>
            <span>{source.kind} / {source.connector_type}</span>
            <span>{source.status || "not refreshed"} / {source.document_count ?? 0} docs</span>
            <span>last refresh: {source.last_refresh || "-"}</span>
            <span>selector: {selector?.name || "not set"}</span>
            <span>{source.enabled === false ? "disabled" : "enabled"}</span>
            <div className="row-actions">
              <button disabled={!selector || testSource.isPending} type="button" onClick={() => selector && testSource.mutate({ name: source.name, selector: selector.name })}>
                {testSource.isPending ? <Loader2 size={14} className="spin" /> : <Play size={14} />} Test
              </button>
              <button disabled={!selector || refresh.isPending} type="button" onClick={() => selector && refresh.mutate({ name: source.name, selector: selector.name })}>
                {refresh.isPending ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />} Refresh
              </button>
            </div>
          </div>
          );
        })}
        {testSource.error && <div className="error">{String(testSource.error.message)}</div>}
        {refresh.error && <div className="error">{String(refresh.error.message)}</div>}
      </ListPanel>
    </section>
  );
}

function ProfilesPage({
  workspaceDir,
  profiles,
  sources,
  selectors,
}: {
  workspaceDir: string;
  profiles: Profile[];
  sources: Source[];
  selectors: Selector[];
}) {
  const queryClient = useQueryClient();
  const specAssets = useQuery({
    queryKey: ["workspace-spec-assets", workspaceDir],
    queryFn: () => apiJson(`/api/workspace/spec-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`, specAssetsSchema),
    enabled: Boolean(workspaceDir),
  });
  const form = useForm<ProfileFormValues>({
    defaultValues: {
      name: "",
      jiraSource: sources.find((source) => source.kind === "jira")?.name || "",
      jiraSelector: "",
      evidenceSource: sources.find((source) => source.kind === "confluence")?.name || "",
      evidenceSelector: "",
      specAssetId: "nvme-spec-mineru",
      topK: 5,
      promptMode: "strict",
      llmBackend: "openai-compatible",
      llmModel: "qwen-9b",
      llmBaseUrl: "http://127.0.0.1:1234/v1",
    },
  });
  const createProfile = useMutation({
    mutationFn: (values: ProfileFormValues) =>
      apiJson(
        "/api/workspace/profiles",
        z.unknown(),
        {
          method: "POST",
          body: JSON.stringify({
            workspace_dir: workspaceDir,
            name: values.name,
            inputs: {
              jira: { source: values.jiraSource, selector_profile: values.jiraSelector },
              evidence: { source: values.evidenceSource, selector_profile: values.evidenceSelector },
            },
            spec_asset_ids: values.specAssetId ? [values.specAssetId] : [],
            analysis: {
              top_k: Number(values.topK),
              llm_backend: values.llmBackend,
              llm_model: values.llmModel || undefined,
              llm_base_url: values.llmBaseUrl || undefined,
              llm_prompt_mode: values.promptMode,
              policies: ["team:ssd", "public"],
            },
          }),
        },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles", workspaceDir] }),
  });
  const validateProfile = useMutation({
    mutationFn: (name: string) =>
      apiJson(
        `/api/workspace/profiles/${name}/validate`,
        z.unknown(),
        {
          method: "POST",
          body: JSON.stringify({ workspace_dir: workspaceDir }),
        },
      ),
  });
  const setDefaultProfile = useMutation({
    mutationFn: (name: string) =>
      apiJson(
        `/api/workspace/profiles/${name}/default`,
        z.unknown(),
        {
          method: "POST",
          body: JSON.stringify({ workspace_dir: workspaceDir }),
        },
      ),
  });
  const duplicateProfile = useMutation({
    mutationFn: ({ sourceName, targetName }: { sourceName: string; targetName: string }) =>
      apiJson(
        `/api/workspace/profiles/${sourceName}/duplicate`,
        z.unknown(),
        {
          method: "POST",
          body: JSON.stringify({ workspace_dir: workspaceDir, name: targetName }),
        },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles", workspaceDir] }),
  });

  return (
    <section className="page-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Profiles</p>
          <h2>Analysis Settings</h2>
          <p>Name the Jira input, evidence source, and analysis behavior users can reuse.</p>
        </div>
        <form className="stack-form" onSubmit={form.handleSubmit((values) => createProfile.mutate(values))}>
          <label>
            Profile name
            <input {...form.register("name", { required: true })} placeholder="nvme_default" />
          </label>
          <label>
            Jira source
            <select {...form.register("jiraSource", { required: true })}>
              {sources.filter((source) => source.kind === "jira").map((source) => <option key={source.name}>{source.name}</option>)}
            </select>
          </label>
          <label>
            Jira selector
            <select {...form.register("jiraSelector", { required: true })}>
              {selectors.filter((selector) => selector.source === form.watch("jiraSource")).map((selector) => <option key={selector.name}>{selector.name}</option>)}
            </select>
          </label>
          <label>
            Evidence source
            <select {...form.register("evidenceSource", { required: true })}>
              {sources.filter((source) => source.kind === "confluence").map((source) => <option key={source.name}>{source.name}</option>)}
            </select>
          </label>
          <label>
            Evidence selector
            <select {...form.register("evidenceSelector", { required: true })}>
              {selectors.filter((selector) => selector.source === form.watch("evidenceSource")).map((selector) => <option key={selector.name}>{selector.name}</option>)}
            </select>
          </label>
          <label>
            Spec asset
            <select {...form.register("specAssetId")}>
              <option value="">No spec asset</option>
              {(specAssets.data?.assets || []).map((asset: SpecAsset) => (
                <option key={`${asset.asset_id}:${asset.version || ""}`} value={asset.asset_id}>
                  {asset.asset_id}{asset.parser_used ? ` / ${asset.parser_used}` : ""}
                </option>
              ))}
              {!specAssets.data?.assets.some((asset) => asset.asset_id === "nvme-spec-mineru") && (
                <option value="nvme-spec-mineru">nvme-spec-mineru / pending</option>
              )}
            </select>
          </label>
          <label>
            Top K
            <input {...form.register("topK")} type="number" min="1" max="20" />
          </label>
          <label>
            Prompt mode
            <select {...form.register("promptMode")}>
              <option value="strict">strict</option>
              <option value="balanced">balanced</option>
              <option value="exploratory">exploratory</option>
            </select>
          </label>
          <label>
            LLM backend
            <select {...form.register("llmBackend")}>
              <option value="ollama">ollama</option>
              <option value="none">none</option>
              <option value="openai-compatible">openai-compatible</option>
            </select>
          </label>
          <label>
            LLM model
            <input {...form.register("llmModel")} placeholder="qwen-9b" />
          </label>
          <label>
            LLM base URL
            <input {...form.register("llmBaseUrl")} placeholder="http://127.0.0.1:1234/v1" />
          </label>
          <button disabled={createProfile.isPending} type="submit">Create Profile</button>
        </form>
      </div>
      <ListPanel title="Profiles">
        {profiles.map((profile) => (
          <div className="list-row" key={profile.name}>
            <strong>{profile.name}</strong>
            <span>{String(profile.analysis?.llm_prompt_mode || "strict")}</span>
            <div className="row-actions">
              <button
                type="button"
                onClick={() => {
                  const targetName = window.prompt("Duplicate as", `${profile.name}_copy`);
                  if (targetName) {
                    duplicateProfile.mutate({ sourceName: profile.name, targetName });
                  }
                }}
              >
                <Copy size={14} /> Duplicate
              </button>
              <button type="button" onClick={() => validateProfile.mutate(profile.name)}>
                <FileCheck size={14} /> Validate
              </button>
              <button type="button" onClick={() => setDefaultProfile.mutate(profile.name)}>
                <CheckCircle2 size={14} /> Set default
              </button>
            </div>
          </div>
        ))}
        {validateProfile.error && <div className="error">{String(validateProfile.error.message)}</div>}
        {setDefaultProfile.error && <div className="error">{String(setDefaultProfile.error.message)}</div>}
        {duplicateProfile.error && <div className="error">{String(duplicateProfile.error.message)}</div>}
      </ListPanel>
    </section>
  );
}

function RunsPage({ workspaceDir, onRerun }: { workspaceDir: string; onRerun: (result: AnalyzeResult) => void }) {
  const queryClient = useQueryClient();
  const runs = useQuery({
    queryKey: ["workspace-runs", workspaceDir],
    queryFn: () => apiJson(`/api/workspace/runs?workspace_dir=${encodeURIComponent(workspaceDir)}`, runsSchema),
    enabled: Boolean(workspaceDir),
  });
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [activeTab, setActiveTab] = useState<RunTab>("summary");
  const selected = useMemo(() => runs.data?.runs.find((run) => run.run_id === selectedRun) || runs.data?.runs[0], [runs.data, selectedRun]);
  const runDetail = useQuery({
    queryKey: ["workspace-run-detail", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        runDetailSchema,
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
  });
  const analysisArtifact = useQuery({
    queryKey: ["workspace-run-artifact", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}/artifacts/deep_analysis_result?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        deepAnalysisArtifactSchema,
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
  });
  const verificationArtifact = useQuery({
    queryKey: ["workspace-run-llm-verification", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}/artifacts/llm_verification?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        llmVerificationSchema,
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
    retry: false,
  });
  const verificationHistoryArtifact = useQuery({
    queryKey: ["workspace-run-llm-verification-history", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}/artifacts/llm_verification_history?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        llmVerificationHistorySchema,
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
    retry: false,
  });
  const verifyRun = useMutation({
    mutationFn: (runId: string) =>
      apiJson(
        `/api/workspace/runs/${runId}/verify-llm`,
        verifyRunSchema,
        {
          method: "POST",
          body: JSON.stringify({
            workspace_dir: workspaceDir,
            llm_backend: "openai-compatible",
            llm_model: "qwen-9b",
            llm_base_url: "http://127.0.0.1:1234/v1",
            llm_timeout_seconds: 600,
          }),
        },
      ),
    onSuccess: (_result, runId) => {
      queryClient.invalidateQueries({ queryKey: ["workspace-run-llm-verification", workspaceDir, runId] });
      queryClient.invalidateQueries({ queryKey: ["workspace-run-llm-verification-history", workspaceDir, runId] });
      queryClient.invalidateQueries({ queryKey: ["workspace-runs", workspaceDir] });
    },
  });
  const rerun = useMutation({
    mutationFn: () => {
      const inputConfig = runDetail.data?.manifest.input_config || {};
      const issueKey = String(inputConfig.issue_key || "");
      const profile = String(inputConfig.profile || "");
      if (!issueKey || !profile) {
        throw new Error("This run does not include issue/profile metadata for rerun.");
      }
      return apiJson(
        "/api/workspace/analyze-jira",
        analyzeSchema,
        {
          method: "POST",
          body: JSON.stringify({
            workspace_dir: workspaceDir,
            issue_key: issueKey,
            profile,
          }),
        },
      );
    },
    onSuccess: (result) => {
      remember("runs", result.run_id);
      onRerun(result);
      queryClient.invalidateQueries({ queryKey: ["workspace-runs", workspaceDir] });
    },
  });
  const payload = analysisArtifact.data?.payload;
  const confluenceCitations = payload?.confluence_evidence?.citations || [];
  const specCitations = payload?.spec_evidence?.citations || [];
  const verification = verificationArtifact.data?.payload;
  const verificationHistory = verificationHistoryArtifact.data?.payload.verifications || [];
  const coverage = coverageFromDeepPayload(payload);
  const artifacts = runDetail.data?.artifact_inventory || [];
  const sectionOutputs = payload?.section_outputs || {};

  return (
    <section className="runs-layout">
      <ListPanel title="Run History">
        {(runs.data?.runs || []).map((run) => (
          <button className="run-row" key={run.run_id} onClick={() => setSelectedRun(run.run_id)} type="button">
            <strong>{run.issue_key || run.run_id}</strong>
            <span>{run.status}</span>
            <span>{run.updated_at || "-"}</span>
          </button>
        ))}
      </ListPanel>
      <div className="primary-surface">
        {selected ? (
          <>
            <div className="section-heading">
              <p className="eyebrow">Run Detail</p>
              <h2>{payload?.title || selected.issue_key || selected.run_id}</h2>
              <p>{selected.status} / {selected.artifact_count ?? 0} artifacts</p>
            </div>
            <div className="row-actions">
              <button disabled={rerun.isPending || !runDetail.data} type="button" onClick={() => rerun.mutate()}>
                {rerun.isPending ? <><Loader2 size={14} className="spin" /> Rerunning...</> : <><Play size={14} /> Rerun same issue/profile</>}
              </button>
              <button disabled={verifyRun.isPending || !selected.run_id} type="button" onClick={() => verifyRun.mutate(selected.run_id)}>
                {verifyRun.isPending ? <><Loader2 size={14} className="spin" /> Verifying...</> : <><CheckCircle2 size={14} /> Verify with LM Studio qwen-9b</>}
              </button>
            </div>
            {analysisArtifact.isLoading && <p>Loading run summary...</p>}
            {analysisArtifact.error && <div className="error">{String(analysisArtifact.error.message)}</div>}
            {rerun.error && <div className="error">{String(rerun.error.message)}</div>}
            {verifyRun.error && <div className="error">{String(verifyRun.error.message)}</div>}
            {payload && (
              <div className="run-detail-stack">
                <EvidenceCoveragePanel coverage={coverage} verificationText={verification?.verification_text} />
                <RunTabs activeTab={activeTab} onSelect={setActiveTab} />
                <RunTabPanel
                  activeTab={activeTab}
                  payload={payload}
                  sectionOutputs={sectionOutputs}
                  confluenceCitations={confluenceCitations}
                  specCitations={specCitations}
                  verification={verification}
                  verificationHistory={verificationHistory}
                  artifacts={artifacts}
                />
              </div>
            )}
          </>
        ) : (
          <EmptyState title="No runs yet" body="Run an analysis to see results here." />
        )}
      </div>
    </section>
  );
}

function RunTabs({ activeTab, onSelect }: { activeTab: RunTab; onSelect: (tab: RunTab) => void }) {
  const tabs: { id: RunTab; label: string }[] = [
    { id: "summary", label: "Summary" },
    { id: "rca", label: "RCA" },
    { id: "spec_impact", label: "Spec Impact" },
    { id: "decision_brief", label: "Decision Brief" },
    { id: "evidence", label: "Evidence" },
    { id: "verification", label: "Verification" },
    { id: "artifacts", label: "Artifacts" },
  ];
  return (
    <div className="run-tabs" role="tablist" aria-label="Run detail tabs">
      {tabs.map((tab) => (
        <button
          className={activeTab === tab.id ? "active" : ""}
          key={tab.id}
          onClick={() => onSelect(tab.id)}
          role="tab"
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function RunTabPanel({
  activeTab,
  payload,
  sectionOutputs,
  confluenceCitations,
  specCitations,
  verification,
  verificationHistory,
  artifacts,
}: {
  activeTab: RunTab;
  payload: z.infer<typeof deepAnalysisArtifactSchema>["payload"];
  sectionOutputs: Record<string, unknown>;
  confluenceCitations: Record<string, unknown>[];
  specCitations: Record<string, unknown>[];
  verification?: z.infer<typeof llmVerificationSchema>["payload"];
  verificationHistory: z.infer<typeof llmVerificationHistorySchema>["payload"]["verifications"];
  artifacts: z.infer<typeof runDetailSchema>["artifact_inventory"];
}) {
  if (activeTab === "summary") {
    return (
      <section className="tab-panel">
        <p className="eyebrow">Summary</p>
        <p>{payload.answer?.text || "No summary text available."}</p>
      </section>
    );
  }
  if (activeTab === "verification") {
    return (
      <section className="tab-panel">
        <p className="eyebrow">LLM Verification</p>
        {verification ? (
          <div className="verification-card">
            <strong>{verification.backend} / {verification.mode}</strong>
            <p>{verification.verification_text}</p>
          </div>
        ) : (
          <p>No LLM verification artifact yet.</p>
        )}
        {verificationHistory.length > 0 && (
          <div className="history-list">
            <p className="eyebrow">History</p>
            {verificationHistory.slice().reverse().map((item, index) => (
              <div className="history-row" key={`${item.created_at || "unknown"}-${index}`}>
                <strong>{item.backend} / {item.created_at || "unknown time"}</strong>
                <span>{firstLine(item.verification_text)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    );
  }
  if (activeTab === "evidence") {
    const citations = [...confluenceCitations, ...specCitations];
    return (
      <section className="tab-panel">
        <p className="eyebrow">Evidence</p>
        {citations.slice(0, 12).map((citation, index) => (
          <div className="citation" key={index}>
            <strong>{String(citation.title || citation.document || citation.document_id || "Evidence")}</strong>
            <span>page {String(citation.page ?? "-")} / {String(citation.section ?? citation.clause ?? "-")}</span>
          </div>
        ))}
        {!citations.length && <p>No evidence citations returned.</p>}
      </section>
    );
  }
  if (activeTab === "artifacts") {
    return (
      <section className="tab-panel">
        <p className="eyebrow">Artifacts</p>
        {(artifacts || []).map((artifact) => (
          <div className="artifact-row" key={artifact.artifact_type}>
            <strong>{artifact.artifact_type}</strong>
            <span>{artifact.status || "unknown"} / {artifact.exists ? "exists" : "missing"}{artifact.stale ? " / stale" : ""}</span>
            <small>{artifact.path || "-"}</small>
          </div>
        ))}
        {!artifacts?.length && <p>No artifact inventory available.</p>}
      </section>
    );
  }
  return (
    <section className="tab-panel">
      <p className="eyebrow">{activeTab.replace("_", " ")}</p>
      <p>{sectionText(sectionOutputs[activeTab])}</p>
    </section>
  );
}

function sectionText(section: unknown): string {
  if (!section || typeof section !== "object") {
    return "No section output available.";
  }
  const answer = (section as { answer?: { text?: string } }).answer;
  return answer?.text || "No section answer available.";
}

function SpecLabPage({ workspaceDir }: { workspaceDir: string }) {
  const form = useForm<SpecIngestValues>({
    defaultValues: {
      specPdf: "",
      assetId: "nvme-spec-mineru",
      displayName: "NVMe Spec",
      mineruPythonExe: "",
    },
  });
  const gate = useQuery({
    queryKey: ["mineru-spec", workspaceDir],
    queryFn: () =>
      apiJson(
        `/api/workspace/spec-assets/nvme-spec-mineru/require-mineru?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        z.unknown(),
      ),
    enabled: Boolean(workspaceDir),
    retry: false,
  });
  const assets = useQuery({
    queryKey: ["workspace-spec-assets", workspaceDir],
    queryFn: () => apiJson(`/api/workspace/spec-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`, specAssetsSchema),
    enabled: Boolean(workspaceDir),
  });
  const queryClient = useQueryClient();
  const ingest = useMutation({
    mutationFn: (values: SpecIngestValues) =>
      apiJson(
        "/api/workspace/spec-assets/ingest",
        z.unknown(),
        {
          method: "POST",
          body: JSON.stringify({
            workspace_dir: workspaceDir,
            spec_pdf: values.specPdf,
            asset_id: values.assetId,
            display_name: values.displayName,
            mineru_python_exe: values.mineruPythonExe || undefined,
          }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mineru-spec", workspaceDir] });
      queryClient.invalidateQueries({ queryKey: ["workspace-spec-assets", workspaceDir] });
    },
  });

  return (
    <section className="page-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Spec Lab</p>
          <h2>NVMe Spec Asset</h2>
          <p>Use a reusable MinerU-parsed spec asset for citation-grade evidence.</p>
        </div>
        {gate.isSuccess ? (
          <div className="notice">nvme-spec-mineru is ready and parsed with MinerU.</div>
        ) : (
          <div className="notice">Parse the NVMe PDF once with MinerU, then reuse the asset in profiles.</div>
        )}
        <form className="stack-form" onSubmit={form.handleSubmit((values) => ingest.mutate(values))}>
          <label>
            NVMe PDF path
            <input {...form.register("specPdf", { required: true })} placeholder="D:\\specs\\nvme.pdf" />
          </label>
          <label>
            Asset ID
            <input {...form.register("assetId", { required: true })} />
          </label>
          <label>
            Display name
            <input {...form.register("displayName", { required: true })} />
          </label>
          <label>
            MinerU Python executable
            <input {...form.register("mineruPythonExe")} placeholder="Optional if mineru is on PATH" />
          </label>
          <button disabled={ingest.isPending} type="submit">
            {ingest.isPending ? <><Loader2 size={16} className="spin" /> Parsing...</> : <><Upload size={16} /> Parse Once With MinerU</>}
          </button>
        </form>
        {gate.error && <div className="error">{String(gate.error.message)}</div>}
        {ingest.error && <div className="error">{String(ingest.error.message)}</div>}
      </div>
      <ListPanel title="Spec Assets">
        {(assets.data?.assets || []).map((asset: SpecAsset) => (
          <div className="list-row" key={`${asset.asset_id}:${asset.version || ""}`}>
            <strong>{asset.asset_id}</strong>
            <span>{asset.display_name || "Unnamed spec"}</span>
            <span>parser: {asset.parser_used || "unknown"}</span>
            <span>document: {asset.document_id || "-"}</span>
            <span>version: {asset.version || "-"}</span>
          </div>
        ))}
        {!assets.data?.assets.length && <p>No spec assets registered in this workspace.</p>}
      </ListPanel>
    </section>
  );
}

function ResultView({ result }: { result: AnalyzeResult | null }) {
  if (!result) {
    return <EmptyState title="Results" body="Summary, evidence, citations, and next actions appear after a run." />;
  }
  const coverage = coverageFromAnalyzeResult(result);
  return (
    <div className="result-surface">
      <EvidenceCoveragePanel coverage={coverage} />
      <section>
        <p className="eyebrow">Summary</p>
        <h3>{String(result.summary.title || result.issue_key)}</h3>
        <p>{String(result.summary.answer || "Analysis completed. Review sections and citations below.")}</p>
      </section>
      <section>
        <p className="eyebrow">Evidence</p>
        {result.evidence_sources.length ? result.evidence_sources.map((source) => <span className="pill" key={source}>{source}</span>) : <p>No evidence sources returned.</p>}
      </section>
      <section>
        <p className="eyebrow">Spec Citations</p>
        {result.citations.slice(0, 5).map((citation, index) => (
          <div className="citation" key={index}>
            <strong>{String(citation.title || citation.document || "Evidence")}</strong>
            <span>page {String(citation.page ?? "-")} / {String(citation.section ?? citation.clause ?? "-")}</span>
          </div>
        ))}
      </section>
      <section>
        <p className="eyebrow">Next Actions</p>
        <p>Use the RCA and Spec Impact tabs in Runs to review follow-up actions and knowledge artifacts.</p>
      </section>
    </div>
  );
}

function ModulePlaceholder({ page, latestResult }: { page: Page; latestResult: AnalyzeResult | null }) {
  const title = page === "wiki" ? "Wiki" : page === "reports" ? "Reports" : "Spec Lab";
  return (
    <div className="primary-surface">
      <div className="section-heading">
        <p className="eyebrow">{title}</p>
        <h2>{title}</h2>
        <p>{latestResult ? "Review generated artifacts from the latest run." : "Run an analysis first to populate this module."}</p>
      </div>
    </div>
  );
}

function EvidenceCoveragePanel({
  coverage,
  verificationText,
}: {
  coverage: EvidenceCoverage;
  verificationText?: string;
}) {
  const verdict = verificationText ? firstLine(verificationText) : (coverage.missing.length ? "Evidence gaps detected" : "Evidence coverage ready");
  return (
    <section className={coverage.missing.length ? "coverage-panel warning" : "coverage-panel"}>
      <div className="coverage-header">
        <div>
          <p className="eyebrow">Evidence Coverage</p>
          <h3>{verdict}</h3>
        </div>
        <span className={coverage.missing.length ? "setup-badge" : "setup-badge ready"}>
          {coverage.missing.length ? "Needs review" : "Ready"}
        </span>
      </div>
      <div className="coverage-grid">
        <MetricCard label="Jira issue" value={coverage.jiraFound ? "found" : "missing"} />
        <MetricCard label="Confluence" value={`${coverage.confluenceCount} hits`} warning={coverage.confluenceCount === 0} />
        <MetricCard label="Spec" value={`${coverage.specCount} hits`} warning={coverage.specCount === 0} />
      </div>
      {coverage.missing.length > 0 && (
        <p className="coverage-gap">
          Missing evidence: {coverage.missing.join(", ")}. Adjust source selectors or rerun after fetching more evidence.
        </p>
      )}
    </section>
  );
}

function MetricCard({ label, value, warning = false }: { label: string; value: string; warning?: boolean }) {
  return (
    <div className={warning ? "metric-card warning" : "metric-card"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function coverageFromAnalyzeResult(result: AnalyzeResult): EvidenceCoverage {
  const coverage = result.evidence_coverage;
  const confluenceCount = Number(coverage?.confluence_count || 0);
  const specCount = Number(coverage?.spec_count || result.citations.length || 0);
  return {
    jiraFound: Boolean(coverage?.jira_found ?? result.issue_key),
    confluenceCount,
    specCount,
    missing: coverage?.missing || [
      ...(confluenceCount ? [] : ["confluence"]),
      ...(specCount ? [] : ["spec"]),
    ],
  };
}

function coverageFromDeepPayload(payload: z.infer<typeof deepAnalysisArtifactSchema>["payload"] | undefined): EvidenceCoverage {
  const breakdown = payload?.shared_retrieval_bundle?.source_breakdown || {};
  const confluenceCount = Number(breakdown.confluence?.result_count || 0);
  const specCount = Object.entries(breakdown).reduce((total, [sourceType, source]) => {
    if (sourceType === "jira" || sourceType === "confluence") {
      return total;
    }
    return total + Number(source.result_count || 0);
  }, 0);
  return {
    jiraFound: Boolean(payload?.issue_id),
    confluenceCount,
    specCount,
    missing: [
      ...(confluenceCount ? [] : ["confluence"]),
      ...(specCount ? [] : ["spec"]),
    ],
  };
}

function firstLine(text: string): string {
  return text.split(/\r?\n/).find((line) => line.trim())?.trim() || "Verification complete";
}

function ListPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <aside className="side-panel">
      <h3>{title}</h3>
      <div className="list-stack">{children}</div>
    </aside>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
