import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Play, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import { SetupChecklist, SetupItem } from "../components/workspace/SetupChecklist";
import { apiJson } from "../apiUtils";

// Schemas
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

const specAssetsSchema = z.object({
  assets: z.array(
    z.object({
      asset_id: z.string(),
      parser_used: z.string().optional(),
    })
  ),
});

type AnalyzeResult = z.infer<typeof analyzeSchema>;

interface Profile {
  name: string;
  [key: string]: unknown;
}

interface Source {
  kind: string;
  enabled?: boolean;
  [key: string]: unknown;
}

interface AnalyzePageProps {
  workspaceDir: string;
  profiles: Profile[];
  sources: Source[];
  latestResult: AnalyzeResult | null;
  onResult: (result: AnalyzeResult) => void;
}

function readRecent(key: string): string[] {
  try {
    const stored = localStorage.getItem(`recent-${key}`);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function remember(key: string, value: string) {
  try {
    const recent = readRecent(key);
    const updated = [value, ...recent.filter((v) => v !== value)].slice(0, 10);
    localStorage.setItem(`recent-${key}`, JSON.stringify(updated));
  } catch {
    // Ignore storage errors
  }
}

export function AnalyzePage({
  workspaceDir,
  profiles,
  sources,
  latestResult,
  onResult,
}: AnalyzePageProps) {
  const navigate = useNavigate();
  const [recentIssues] = useState(readRecent("issues"));
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const form = useForm({
    defaultValues: {
      issueKey: recentIssues[0] || "",
      profile: profiles[0]?.name || "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: { issueKey: string; profile: string }) =>
      apiJson("/api/workspace/analyze-jira", analyzeSchema, {
        method: "POST",
        body: JSON.stringify({
          workspace_dir: workspaceDir,
          issue_key: values.issueKey,
          profile: values.profile,
        }),
      }),
    onSuccess: (result, values) => {
      remember("issues", values.issueKey);
      remember("profiles", values.profile);
      remember("runs", result.run_id);
      onResult(result);
    },
  });

  const specAssets = useQuery({
    queryKey: ["workspace-spec-assets", workspaceDir],
    queryFn: () =>
      apiJson(
        `/api/workspace/spec-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        specAssetsSchema
      ),
    enabled: Boolean(workspaceDir),
  });

  const jiraReady = sources.some((source) => source.kind === "jira" && source.enabled !== false);
  const confluenceReady = sources.some(
    (source) => source.kind === "confluence" && source.enabled !== false
  );
  const mineruReady = Boolean(
    specAssets.data?.assets.some(
      (asset) => asset.asset_id === "nvme-spec-mineru" && asset.parser_used === "mineru"
    )
  );
  const profileReady = profiles.some((profile) => {
    const text = JSON.stringify(profile);
    return text.includes("nvme-spec-mineru") && text.includes("llm_backend");
  });

  const setupItems: SetupItem[] = [
    {
      label: "Jira Source",
      ok: jiraReady,
      detail: jiraReady ? "Configured" : "Add a Jira source",
      target: "sources",
    },
    {
      label: "Confluence Source",
      ok: confluenceReady,
      detail: confluenceReady ? "Configured" : "Add a Confluence source",
      target: "sources",
    },
    {
      label: "File Asset",
      ok: mineruReady,
      detail: mineruReady
        ? "File assets parsed with MinerU"
        : "Parse or register file assets (specs, policies, etc.)",
      target: "spec",
    },
    {
      label: "Analysis Profile",
      ok: profileReady,
      detail: profileReady
        ? "Profile references spec + LLM settings"
        : "Create a profile with spec and LLM settings",
      target: "profiles",
    },
  ];

  const setupComplete = Boolean(workspaceDir && setupItems.every((item) => item.ok));

  return (
    <section className="page-grid analyze-grid">
      <div className="primary-surface transcript-surface">
        <div className="section-heading chat-heading">
          <p className="eyebrow">Analyze</p>
          <h2>Deep Jira Analysis</h2>
          <p>
            Run deep analysis on Jira issues with cross-source evidence from Confluence and file
            assets.
          </p>
        </div>

        <SetupChecklist items={setupItems} onNavigate={(page) => navigate(`/${page}`)} />

        <div className="message-stack">
          <article className="message system-message">
            <div className="message-meta">system</div>
            <p>
              PageIndex-first retrieval, ACL filtering before ranking, citation-bearing answer
              assembly.
            </p>
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
              <p>
                {latestResult.issue_key} completed as {latestResult.run_id}
              </p>
            </article>
          )}
        </div>

        <button
          className="plain-action"
          type="button"
          onClick={() => setAdvancedOpen((value) => !value)}
        >
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

        <form
          className="run-form command-composer"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
        >
          <label>
            Issue Key
            <input
              {...form.register("issueKey", { required: true })}
              placeholder="SSD-DEMO-A"
              list="recent-issues"
            />
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
            {mutation.isPending ? (
              <>
                <RefreshCw size={16} className="spin" /> Running...
              </>
            ) : (
              <>
                <Play size={16} /> Run Analysis
              </>
            )}
          </button>
        </form>
      </div>
    </section>
  );
}
