import React, { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { Play, Loader2, CheckCircle2 } from "lucide-react";
import { ListPanel } from "../components/common/ListPanel";
import { EmptyState } from "../components/common/EmptyState";
import { EvidenceCoveragePanel, EvidenceCoverage } from "../components/evidence/EvidenceCoveragePanel";
import { RunTabs, RunTab } from "../components/runs/RunTabs";
import { RunTabPanel } from "../components/runs/RunTabPanel";
import { apiJson } from "../apiUtils";

// Schemas
const runsSchema = z.object({
  runs: z.array(
    z.object({
      run_id: z.string(),
      status: z.string(),
      issue_key: z.string().nullable().optional(),
      updated_at: z.string().nullable().optional(),
      run_dir: z.string().optional(),
      artifact_count: z.number().optional(),
    })
  ),
});

const runDetailSchema = z.object({
  manifest: z
    .object({
      input_config: z.record(z.string(), z.unknown()).optional(),
    })
    .passthrough(),
  artifact_inventory: z
    .array(
      z
        .object({
          artifact_type: z.string(),
          path: z.string().optional(),
          exists: z.boolean().optional(),
          status: z.string().optional(),
          stale: z.boolean().optional(),
          step_name: z.string().optional(),
        })
        .passthrough()
    )
    .optional(),
}).passthrough();

const deepAnalysisArtifactSchema = z.object({
  payload: z
    .object({
      title: z.string().optional(),
      issue_id: z.string().optional(),
      issue_summary: z.string().optional(),
      answer: z.object({ text: z.string().optional() }).optional(),
      shared_retrieval_bundle: z
        .object({
          source_breakdown: z
            .record(
              z.string(),
              z
                .object({
                  result_count: z.number().optional(),
                })
                .passthrough()
            )
            .optional(),
        })
        .passthrough()
        .optional(),
      section_outputs: z.record(z.string(), z.unknown()).optional(),
      confluence_evidence: z
        .object({ citations: z.array(z.record(z.string(), z.unknown())).optional() })
        .optional(),
      spec_evidence: z
        .object({ citations: z.array(z.record(z.string(), z.unknown())).optional() })
        .optional(),
      knowledge_artifacts: z.record(z.string(), z.unknown()).optional(),
    })
    .passthrough(),
});

const llmVerificationSchema = z.object({
  payload: z
    .object({
      backend: z.string(),
      mode: z.string(),
      verification_text: z.string(),
      created_at: z.string().optional(),
    })
    .passthrough(),
});

const llmVerificationHistorySchema = z.object({
  payload: z
    .object({
      verifications: z.array(
        z
          .object({
            backend: z.string(),
            mode: z.string(),
            verification_text: z.string(),
            created_at: z.string().optional(),
          })
          .passthrough()
      ),
    })
    .passthrough(),
});

const verifyRunSchema = z.object({
  verification: z
    .object({
      backend: z.string(),
      mode: z.string(),
      verification_text: z.string(),
      created_at: z.string().optional(),
    })
    .passthrough(),
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

type AnalyzeResult = z.infer<typeof analyzeSchema>;

interface RunsPageProps {
  workspaceDir: string;
  onRerun: (result: AnalyzeResult) => void;
}

function remember(key: string, value: string) {
  try {
    const stored = localStorage.getItem(`recent-${key}`);
    const recent = stored ? JSON.parse(stored) : [];
    const updated = [value, ...recent.filter((v: string) => v !== value)].slice(0, 10);
    localStorage.setItem(`recent-${key}`, JSON.stringify(updated));
  } catch {
    // Ignore storage errors
  }
}

function coverageFromDeepPayload(
  payload: z.infer<typeof deepAnalysisArtifactSchema>["payload"] | undefined
): EvidenceCoverage {
  const breakdown = payload?.shared_retrieval_bundle?.source_breakdown || {};
  const confluenceCount = Number(breakdown.confluence?.result_count || 0);
  const specCount = Object.entries(breakdown).reduce((total, [sourceType, source]) => {
    if (sourceType === "jira" || sourceType === "confluence") {
      return total;
    }
    return total + Number(source.result_count || 0);
  }, 0);
  return {
    jira_found: Boolean(payload?.issue_id),
    confluence_count: confluenceCount,
    spec_count: specCount,
    missing: [...(confluenceCount ? [] : ["confluence"]), ...(specCount ? [] : ["spec"])],
  };
}

export function RunsPage({ workspaceDir, onRerun }: RunsPageProps) {
  const queryClient = useQueryClient();

  const runs = useQuery({
    queryKey: ["workspace-runs", workspaceDir],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        runsSchema
      ),
    enabled: Boolean(workspaceDir),
  });

  const [selectedRun, setSelectedRun] = useState<string>("");
  const [activeTab, setActiveTab] = useState<RunTab>("summary");

  const selected = useMemo(
    () => runs.data?.runs.find((run) => run.run_id === selectedRun) || runs.data?.runs[0],
    [runs.data, selectedRun]
  );

  const runDetail = useQuery({
    queryKey: ["workspace-run-detail", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        runDetailSchema
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
  });

  const analysisArtifact = useQuery({
    queryKey: ["workspace-run-artifact", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}/artifacts/deep_analysis_result?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        deepAnalysisArtifactSchema
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
  });

  const verificationArtifact = useQuery({
    queryKey: ["workspace-run-llm-verification", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}/artifacts/llm_verification?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        llmVerificationSchema
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
    retry: false,
  });

  const verificationHistoryArtifact = useQuery({
    queryKey: ["workspace-run-llm-verification-history", workspaceDir, selected?.run_id],
    queryFn: () =>
      apiJson(
        `/api/workspace/runs/${selected!.run_id}/artifacts/llm_verification_history?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        llmVerificationHistorySchema
      ),
    enabled: Boolean(workspaceDir && selected?.run_id),
    retry: false,
  });

  const verifyRun = useMutation({
    mutationFn: (runId: string) =>
      apiJson(`/api/workspace/runs/${runId}/verify-llm`, verifyRunSchema, {
        method: "POST",
        body: JSON.stringify({
          workspace_dir: workspaceDir,
          llm_backend: "openai-compatible",
          llm_model: "qwen-9b",
          llm_base_url: "http://127.0.0.1:1234/v1",
          llm_timeout_seconds: 600,
        }),
      }),
    onSuccess: (_result, runId) => {
      queryClient.invalidateQueries({
        queryKey: ["workspace-run-llm-verification", workspaceDir, runId],
      });
      queryClient.invalidateQueries({
        queryKey: ["workspace-run-llm-verification-history", workspaceDir, runId],
      });
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
      return apiJson("/api/workspace/analyze-jira", analyzeSchema, {
        method: "POST",
        body: JSON.stringify({
          workspace_dir: workspaceDir,
          issue_key: issueKey,
          profile,
        }),
      });
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
          <button
            className="run-row"
            key={run.run_id}
            onClick={() => setSelectedRun(run.run_id)}
            type="button"
          >
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
              <p>
                {selected.status} / {selected.artifact_count ?? 0} artifacts
              </p>
            </div>
            <div className="row-actions">
              <button
                disabled={rerun.isPending || !runDetail.data}
                type="button"
                onClick={() => rerun.mutate()}
              >
                {rerun.isPending ? (
                  <>
                    <Loader2 size={14} className="spin" /> Rerunning...
                  </>
                ) : (
                  <>
                    <Play size={14} /> Rerun same issue/profile
                  </>
                )}
              </button>
              <button
                disabled={verifyRun.isPending || !selected.run_id}
                type="button"
                onClick={() => verifyRun.mutate(selected.run_id)}
              >
                {verifyRun.isPending ? (
                  <>
                    <Loader2 size={14} className="spin" /> Verifying...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={14} /> Verify with LM Studio qwen-9b
                  </>
                )}
              </button>
            </div>
            {analysisArtifact.isLoading && <p>Loading run summary...</p>}
            {analysisArtifact.error && (
              <div className="error">{String(analysisArtifact.error.message)}</div>
            )}
            {rerun.error && <div className="error">{String(rerun.error.message)}</div>}
            {verifyRun.error && <div className="error">{String(verifyRun.error.message)}</div>}
            {payload && (
              <div className="run-detail-stack">
                <EvidenceCoveragePanel
                  coverage={coverage}
                  verificationText={verification?.verification_text}
                />
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
