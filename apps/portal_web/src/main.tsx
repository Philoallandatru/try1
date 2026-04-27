import React, { useMemo, useState, Suspense, lazy, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import ReactMarkdown from "react-markdown";
import { ErrorBoundary } from "./ErrorBoundary";
import { apiJson } from "./apiUtils";
import { SkeletonPage } from "./SkeletonLoader";
import { performanceMonitor } from "./performanceMonitor";
import { PerformancePanel } from "./PerformancePanel";
import { PermissionProvider } from "./PermissionContext";
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
  Calendar,
  Layers,
  MessageSquare,
  Sliders,
} from "lucide-react";
import "./styles.css";
import "./workspace-manager.css";
import "./permissions.css";
import "./share.css";
import "./comment.css";
import "./annotation.css";
import "./configuration.css";

// Lazy load page components for code splitting
const AnalysisResultsPage = lazy(() => import("./AnalysisResultsPage").then(m => ({ default: m.AnalysisResultsPage })));
const DailyReportPage = lazy(() => import("./DailyReportPage").then(m => ({ default: m.DailyReportPage })));
const BatchAnalysisPage = lazy(() => import("./BatchAnalysisPage").then(m => ({ default: m.BatchAnalysisPage })));
const DataSourcesPage = lazy(() => import("./DataSourcesPage"));
const ConfigurationPage = lazy(() => import("./ConfigurationPage"));
const RetrievalEvaluationPage = lazy(() => import("./RetrievalEvaluationPage").then(m => ({ default: m.RetrievalEvaluationPage })));
const RetrievalDebugPage = lazy(() => import("./RetrievalDebugPage"));
const StrategyComparisonPage = lazy(() => import("./StrategyComparisonPage"));
const ModelConfigPage = lazy(() => import("./ModelConfigPage").then(m => ({ default: m.ModelConfigPage })));
const ChatPage = lazy(() => import("./ChatPage").then(m => ({ default: m.ChatPage })));
const DocumentManagementPage = lazy(() => import("./DocumentManagementPage").then(m => ({ default: m.DocumentManagementPage })));

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

const searchResultSchema = z.object({
  doc_id: z.string(),
  score: z.number(),
  document: z.object({
    id: z.string(),
    title: z.string().optional(),
    content: z.string().optional(),
    source: z.string().optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
  }),
});

const searchResponseSchema = z.object({
  status: z.string(),
  query: z.string(),
  results: z.array(searchResultSchema),
  total: z.number(),
});

const indexStatsSchema = z.object({
  status: z.string(),
  stats: z.object({
    total_documents: z.number(),
    index_size_bytes: z.number().optional(),
    last_updated: z.string().optional(),
  }),
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
  target: string;
};
type EvidenceCoverage = {
  jiraFound: boolean;
  confluenceCount: number;
  specCount: number;
  missing: string[];
};
type RunTab = "summary" | "rca" | "spec_impact" | "decision_brief" | "evidence" | "verification" | "artifacts";
type ProfileFormValues = {
  name: string;
  jiraSource: string;
  jiraSelector: string;
  evidenceSource: string;
  evidenceSelector: string;
  specAssetId: string;
  documentAssetIds: string[];
  topK: number;
  promptMode: string;
  llmBackend: string;
  llmModel: string;
  llmBaseUrl: string;
};

type Page = "analyze" | "runs" | "sources" | "profiles" | "wiki" | "reports" | "spec" | "search";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      refetchOnMount: true,
    },
    mutations: {
      retry: 1,
      retryDelay: 1000,
      onError: (error) => {
        console.error("Mutation error:", error);
      },
    },
  },
});

function tokenHeaders(): HeadersInit {
  const token = localStorage.getItem("ssdPortalToken") || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiJsonLegacy<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<T> {
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
  const [workspaceDir, setWorkspaceDir] = useState("");
  const [workspaceName, setWorkspaceName] = useState("real-workspace");
  const [latestResult, setLatestResult] = useState<AnalyzeResult | null>(null);
  const queryClient = useQueryClient();
  const location = useLocation();

  // Initialize performance monitoring
  useEffect(() => {
    performanceMonitor.init();

    // Log performance report every 5 minutes in development
    if (import.meta.env.DEV) {
      const interval = setInterval(() => {
        const report = performanceMonitor.getReport();
        console.log('Performance Report:', report);
      }, 5 * 60 * 1000);

      return () => clearInterval(interval);
    }
  }, []);

  const workspaces = useQuery({
    queryKey: ["workspaces"],
    queryFn: () => apiJson("/api/workspaces", workspacesSchema),
  });

  const selectedWorkspace = workspaceDir || workspaces.data?.workspaces[0]?.workspace_dir || "";
  const profiles = useQuery({
    queryKey: ["profiles", selectedWorkspace],
    queryFn: () => apiJson(`/api/workspace/profiles?workspace_dir=${encodeURIComponent(selectedWorkspace)}`, profilesSchema),
    enabled: Boolean(selectedWorkspace),
  });
  const sources = useQuery({
    queryKey: ["sources", selectedWorkspace],
    queryFn: () => apiJson(`/api/workspace/sources?workspace_dir=${encodeURIComponent(selectedWorkspace)}`, sourcesSchema),
    enabled: Boolean(selectedWorkspace),
  });

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
            <h1>SSD Quality Wiki</h1>
          </div>
        </div>
        <div className="nav-group-label">Workspace</div>
        <nav>
          {[
            { id: "/", label: "Analyze", icon: Search },
            { id: "/search", label: "Search", icon: FileText },
            { id: "/chat", label: "Chat", icon: MessageSquare },
            { id: "/runs", label: "Runs", icon: Clock },
            { id: "/analysis", label: "Analysis", icon: BarChart3 },
            { id: "/daily-report", label: "Daily Report", icon: Calendar },
            { id: "/batch-analysis", label: "Batch Analysis", icon: Layers },
            { id: "/configuration", label: "Configuration", icon: Settings },
            { id: "/data-sources", label: "Data Sources", icon: Database },
            { id: "/documents", label: "Documents", icon: Upload },
            { id: "/retrieval-eval", label: "Retrieval Eval", icon: BarChart3 },
            { id: "/retrieval-debug", label: "Retrieval Debug", icon: Settings },
            { id: "/strategy-comparison", label: "Strategy Compare", icon: BarChart3 },
            { id: "/profiles", label: "Profiles", icon: Settings },
            { id: "/model-config", label: "Model Config", icon: Sliders },
            { id: "/wiki", label: "Wiki", icon: FileText },
            { id: "/reports", label: "Reports", icon: BarChart3 },
          ].map(({ id, label, icon: Icon }) => (
            <Link
              to={id}
              key={id}
              className={location.pathname === id ? "active" : ""}
            >
              <Icon size={18} /> {label}
            </Link>
          ))}
          <a href="/admin/"><ExternalLink size={18} /> Admin</a>
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="toolbar-title">
            <span className="toolbar-dot" aria-hidden="true" />
            <div>
              <p className="eyebrow">SSD Platform</p>
              <strong>SSD Knowledge Workspace</strong>
            </div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label htmlFor="workspace-selector" style={{ fontSize: '14px', color: '#666' }}>Workspace:</label>
            <select
              id="workspace-selector"
              data-testid="workspace-selector"
              value={selectedWorkspace}
              onChange={(e) => setWorkspaceDir(e.target.value)}
              style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              {workspaces.data?.workspaces.map((ws) => (
                <option key={ws.workspace_dir} value={ws.workspace_dir}>
                  {ws.name || ws.workspace_dir}
                </option>
              ))}
            </select>
          </div>
        </header>

        <Suspense fallback={<SkeletonPage />}>
          <Routes>
            <Route path="/" element={
              <AnalyzePage
                workspaceDir={selectedWorkspace}
                profiles={profiles.data?.profiles || []}
                sources={sources.data?.sources || []}
                latestResult={latestResult}
                onResult={setLatestResult}
              />
            } />
            <Route path="/search" element={<SearchPage workspaceDir={selectedWorkspace} />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/runs" element={<RunsPage workspaceDir={selectedWorkspace} onRerun={(result) => setLatestResult(result)} />} />
            <Route path="/analysis" element={<AnalysisResultsPage workspaceDir={selectedWorkspace} />} />
            <Route path="/daily-report" element={<DailyReportPage workspaceDir={selectedWorkspace} />} />
            <Route path="/batch-analysis" element={<BatchAnalysisPage />} />
            <Route path="/configuration" element={<ConfigurationPage workspaceDir={selectedWorkspace} />} />
            <Route path="/data-sources" element={<DataSourcesPage workspaceDir={selectedWorkspace} />} />
            <Route path="/documents" element={<DocumentManagementPage workspaceDir={selectedWorkspace} />} />
            <Route path="/retrieval-eval" element={<RetrievalEvaluationPage workspaceDir={selectedWorkspace} />} />
            <Route path="/retrieval-debug" element={<RetrievalDebugPage />} />
            <Route path="/strategy-comparison" element={<StrategyComparisonPage />} />
            <Route path="/profiles" element={
              <ProfilesPage
                workspaceDir={selectedWorkspace}
                profiles={profiles.data?.profiles || []}
                sources={sources.data?.sources || []}
                selectors={sources.data?.selectors || []}
              />
            } />
            <Route path="/model-config" element={<ModelConfigPage />} />
            <Route path="/wiki" element={<ModulePlaceholder page="wiki" latestResult={latestResult} />} />
            <Route path="/reports" element={<ModulePlaceholder page="reports" latestResult={latestResult} />} />
          </Routes>
        </Suspense>
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
}: {
  workspaceDir: string;
  profiles: Profile[];
  sources: Source[];
  latestResult: AnalyzeResult | null;
  onResult: (result: AnalyzeResult) => void;
}) {
  const navigate = useNavigate();
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
    { label: "File Asset", ok: mineruReady, detail: mineruReady ? "File assets parsed with MinerU" : "Parse or register file assets (specs, policies, etc.)", target: "spec" },
    { label: "Analysis Profile", ok: profileReady, detail: profileReady ? "Profile references spec + LLM settings" : "Create a profile with spec and LLM settings", target: "profiles" },
  ];
  const setupComplete = Boolean(workspaceDir && setupItems.every((item) => item.ok));

  return (
    <section className="page-grid analyze-grid">
      <div className="primary-surface transcript-surface">
        <div className="section-heading chat-heading">
          <p className="eyebrow">Analyze</p>
          <h2>Deep Jira Analysis</h2>
          <p>Run deep analysis on Jira issues with cross-source evidence from Confluence and file assets.</p>
        </div>

        <SetupChecklist items={setupItems} onNavigate={(page) => navigate(`/${page}`)} />

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

function SetupChecklist({ items, onNavigate }: { items: SetupItem[]; onNavigate: (page: string) => void }) {
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
  const documentAssets = useQuery({
    queryKey: ["workspace-document-assets", workspaceDir],
    queryFn: () => apiJson(`/api/workspace/document-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`, specAssetsSchema),
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
      documentAssetIds: [],
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
            document_asset_ids: values.documentAssetIds || [],
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
            Document assets (uploaded files)
            <div style={{ maxHeight: "150px", overflowY: "auto", border: "1px solid var(--border)", borderRadius: "4px", padding: "8px" }}>
              {(documentAssets.data?.assets || []).length === 0 ? (
                <p style={{ margin: 0, color: "var(--text-secondary)" }}>No uploaded documents available</p>
              ) : (
                (documentAssets.data?.assets || []).map((asset: SpecAsset) => (
                  <label key={asset.asset_id} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "4px 0" }}>
                    <input
                      type="checkbox"
                      value={asset.asset_id}
                      {...form.register("documentAssetIds")}
                    />
                    <span>{asset.asset_id}</span>
                  </label>
                ))
              )}
            </div>
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
    const issueDataText = payload.issue_summary ? String(payload.issue_summary) : null;
    return (
      <section className="tab-panel">
        {issueDataText && (
          <>
            <p className="eyebrow">Jira Issue</p>
            <div className="document-content markdown-content">
              <ReactMarkdown>{issueDataText}</ReactMarkdown>
            </div>
          </>
        )}
        <p className="eyebrow">Analysis Summary</p>
        <div className="markdown-content">
          <ReactMarkdown>{payload.answer?.text || "No summary text available."}</ReactMarkdown>
        </div>
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
      <div className="markdown-content">
        <ReactMarkdown>{sectionText(sectionOutputs[activeTab])}</ReactMarkdown>
      </div>
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

// Highlight matching text in search results
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  const terms = query.trim().split(/\s+/);
  let result: React.ReactNode = text;

  terms.forEach((term) => {
    if (term.length < 2) return;
    const regex = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts: React.ReactNode[] = [];

    if (typeof result === 'string') {
      const matches = result.split(regex);
      matches.forEach((part, i) => {
        if (regex.test(part)) {
          parts.push(<mark key={i}>{part}</mark>);
        } else {
          parts.push(part);
        }
      });
      result = parts;
    }
  });

  return result;
}

function SearchPage({ workspaceDir }: { workspaceDir: string }) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<z.infer<typeof searchResultSchema>[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<z.infer<typeof searchResultSchema> | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);

  const indexStats = useQuery({
    queryKey: ["index-stats", workspaceDir],
    queryFn: () => apiJson(`/api/retrieval/index/stats?workspace_dir=${encodeURIComponent(workspaceDir)}`, indexStatsSchema),
    enabled: Boolean(workspaceDir),
  });

  const queryClient = useQueryClient();

  const buildIndex = useMutation({
    mutationFn: () =>
      apiJson(
        "/api/retrieval/index/build",
        z.object({ status: z.string(), indexed_documents: z.number() }),
        {
          method: "POST",
          body: JSON.stringify({ workspace_dir: workspaceDir }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["index-stats", workspaceDir] });
    },
  });

  const toggleDocumentType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    try {
      const response = await apiJson(
        "/api/retrieval/search",
        searchResponseSchema,
        {
          method: "POST",
          body: JSON.stringify({
            workspace_dir: workspaceDir,
            query: query.trim(),
            top_k: 10,
            document_types: selectedTypes.length > 0 ? selectedTypes : undefined,
          }),
        },
      );
      setSearchResults(response.results);
    } catch (error) {
      setSearchError(String(error));
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const totalDocs = indexStats.data?.stats.total_documents ?? 0;
  const indexReady = totalDocs > 0;

  return (
    <section className="page-grid search-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Search</p>
          <h2>Knowledge Retrieval</h2>
          <p>Search across all indexed documents using BM25 retrieval with Chinese/English support.</p>
        </div>

        <div className="index-status-card" data-testid="index-status-card">
          <div className="index-status-header">
            <div>
              <p className="eyebrow">Index Status</p>
              <strong data-testid="document-count">{totalDocs} documents indexed</strong>
            </div>
            <button
              data-testid="rebuild-index-button"
              disabled={buildIndex.isPending}
              type="button"
              onClick={() => buildIndex.mutate()}
              aria-busy={buildIndex.isPending}
              aria-label={buildIndex.isPending ? "Building index" : "Rebuild index"}
            >
              {buildIndex.isPending ? (
                <><Loader2 size={16} className="spin" /> Building...</>
              ) : (
                <><RefreshCw size={16} /> Rebuild Index</>
              )}
            </button>
          </div>
          {indexStats.data?.stats.last_updated && (
            <p className="index-status-detail">
              Last updated: {indexStats.data.stats.last_updated}
            </p>
          )}
          {buildIndex.error && (
            <div className="error" role="alert">
              <XCircle size={16} /> {String(buildIndex.error.message)}
            </div>
          )}
        </div>

        <div className="search-box">
          <input
            data-testid="search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Enter your search query (支持中英文)..."
            disabled={!indexReady || isSearching}
            aria-label="Search documents"
            aria-describedby={!indexReady ? "search-help" : undefined}
            aria-invalid={!!searchError}
          />
          <button
            data-testid="search-button"
            type="button"
            onClick={handleSearch}
            disabled={!indexReady || !query.trim() || isSearching}
            aria-busy={isSearching}
            aria-label={isSearching ? "Searching" : "Search"}
          >
            {isSearching ? (
              <><Loader2 size={16} className="spin" /> Searching...</>
            ) : (
              <><Search size={16} /> Search</>
            )}
          </button>
        </div>

        <div className="document-type-filters">
          <p className="eyebrow">Filter by Document Type</p>
          <div className="filter-buttons">
            <button
              type="button"
              className={selectedTypes.includes("spec") ? "filter-button active" : "filter-button"}
              onClick={() => toggleDocumentType("spec")}
            >
              <FileText size={14} /> Specification {selectedTypes.includes("spec") && <Check size={14} />}
            </button>
            <button
              type="button"
              className={selectedTypes.includes("policy") ? "filter-button active" : "filter-button"}
              onClick={() => toggleDocumentType("policy")}
            >
              <FileCheck size={14} /> Policy {selectedTypes.includes("policy") && <Check size={14} />}
            </button>
            <button
              type="button"
              className={selectedTypes.includes("other") ? "filter-button active" : "filter-button"}
              onClick={() => toggleDocumentType("other")}
            >
              <FileText size={14} /> Other {selectedTypes.includes("other") && <Check size={14} />}
            </button>
            {selectedTypes.length > 0 && (
              <button
                type="button"
                className="filter-button clear"
                onClick={() => setSelectedTypes([])}
              >
                <X size={14} /> Clear filters
              </button>
            )}
          </div>
        </div>

        {!indexReady && (
          <div className="notice" id="search-help" role="status">
            No documents indexed yet. Build the index first by clicking "Rebuild Index" above.
          </div>
        )}

        {isSearching && (
          <div role="status" aria-live="polite" className="sr-only">
            Searching for {query}...
          </div>
        )}

        {searchError && (
          <div className="error" role="alert" aria-live="assertive">
            <XCircle size={16} /> Search failed: {searchError}
          </div>
        )}

        {searchResults.length > 0 && (
          <div className="search-results" data-testid="search-results">
            <p className="eyebrow">{searchResults.length} results</p>
            {searchResults.map((result, index) => {
              const docType = result.document.metadata?.document_type as string | undefined;
              const priority = result.document.metadata?.priority as number | undefined;

              return (
                <button
                  key={result.doc_id}
                  data-testid={`search-result-${index}`}
                  className={selectedDoc?.doc_id === result.doc_id ? "search-result-card active" : "search-result-card"}
                  onClick={() => setSelectedDoc(result)}
                  type="button"
                  aria-label={`Result ${index + 1}: ${result.document.title || result.doc_id}`}
                >
                  <div className="search-result-header">
                    <div className="search-result-title">
                      <strong>#{index + 1} {highlightText(result.document.title || result.doc_id, query)}</strong>
                      {docType && (
                        <span className={`doc-type-badge ${docType}`}>
                          {docType === "spec" && <FileText size={12} />}
                          {docType === "policy" && <FileCheck size={12} />}
                          {docType === "other" && <FileText size={12} />}
                          {docType.toUpperCase()}
                        </span>
                      )}
                      {priority !== undefined && (
                        <span className="priority-badge" title={`Priority: ${priority}`}>
                          P{priority}
                        </span>
                      )}
                    </div>
                    <span className="search-score">Score: {result.score.toFixed(3)}</span>
                  </div>
                  <p className="search-result-snippet">
                    {highlightText(result.document.content?.substring(0, 200) || "No content preview", query)}
                    {(result.document.content?.length ?? 0) > 200 && "..."}
                  </p>
                  <div className="search-result-meta">
                    <span><Database size={14} /> {result.document.source || "unknown"}</span>
                    <span><FileText size={14} /> {result.doc_id}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {searchResults.length === 0 && query && !isSearching && !searchError && (
          <div className="empty-state">
            <Search size={48} />
            <p>No results found for "{query}"</p>
            <p className="empty-state-hint">Try different keywords or rebuild the index</p>
          </div>
        )}
      </div>

      {selectedDoc ? (
        <div className="result-surface document-detail">
          <div className="section-heading">
            <p className="eyebrow">Document Detail</p>
            <h3>{selectedDoc.document.title || selectedDoc.doc_id}</h3>
          </div>
          <div className="document-meta-grid">
            <MetricCard label="Score" value={selectedDoc.score.toFixed(3)} />
            <MetricCard label="Source" value={selectedDoc.document.source || "unknown"} />
            <MetricCard label="Doc ID" value={selectedDoc.doc_id} />
          </div>
          <section>
            <p className="eyebrow">Content</p>
            <div className="document-content">
              {selectedDoc.document.content || "No content available"}
            </div>
          </section>
          {selectedDoc.document.metadata && Object.keys(selectedDoc.document.metadata).length > 0 && (
            <section>
              <p className="eyebrow">Metadata</p>
              <div className="metadata-grid">
                {Object.entries(selectedDoc.document.metadata).map(([key, value]) => (
                  <div key={key} className="metadata-row">
                    <strong>{key}</strong>
                    <span>{String(value)}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      ) : (
        <EmptyState
          title="Select a result"
          body="Click on a search result to view full document details."
        />
      )}
    </section>
  );
}

function ResultView({ result }: { result: AnalyzeResult | null }) {
  if (!result) {
    return <EmptyState title="Results" body="Summary, evidence, citations, and next actions appear after a run." />;
  }
  const coverage = coverageFromAnalyzeResult(result);
  const issueData = result.sections?.issue_summary || result.summary?.issue_summary;
  const issueDataText = issueData ? String(issueData) : null;

  return (
    <div className="result-surface">
      <EvidenceCoveragePanel coverage={coverage} />
      {issueDataText && (
        <section>
          <p className="eyebrow">Jira Issue</p>
          <div className="document-content markdown-content">
            <ReactMarkdown>{issueDataText}</ReactMarkdown>
          </div>
        </section>
      )}
      <section>
        <p className="eyebrow">Analysis Summary</p>
        <h3>{String(result.summary.title || result.issue_key)}</h3>
        <div className="markdown-content">
          <ReactMarkdown>{String(result.summary.answer || "Analysis completed. Review sections and citations below.")}</ReactMarkdown>
        </div>
      </section>
      <section>
        <p className="eyebrow">Evidence Sources</p>
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
    <ErrorBoundary>
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <PermissionProvider>
            <App />
            <PerformancePanel />
          </PermissionProvider>
        </QueryClientProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
);
