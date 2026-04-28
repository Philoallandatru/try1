import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Copy, FileCheck, CheckCircle2 } from "lucide-react";
import { ListPanel } from "../components/common/ListPanel";
import { apiJson } from "../apiUtils";

const specAssetsSchema = z.object({
  assets: z.array(
    z.object({
      asset_id: z.string(),
      version: z.string().optional(),
      parser_used: z.string().optional(),
    })
  ),
});

type SpecAsset = z.infer<typeof specAssetsSchema>["assets"][number];

interface Profile {
  name: string;
  analysis?: {
    llm_prompt_mode?: string;
  };
  [key: string]: unknown;
}

interface Source {
  name: string;
  kind: string;
  [key: string]: unknown;
}

interface Selector {
  name: string;
  source: string;
  [key: string]: unknown;
}

interface ProfileFormValues {
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
}

interface ProfilesPageProps {
  workspaceDir: string;
  profiles: Profile[];
  sources: Source[];
  selectors: Selector[];
}

export function ProfilesPage({
  workspaceDir,
  profiles,
  sources,
  selectors,
}: ProfilesPageProps) {
  const queryClient = useQueryClient();

  const specAssets = useQuery({
    queryKey: ["workspace-spec-assets", workspaceDir],
    queryFn: () =>
      apiJson(
        `/api/workspace/spec-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        specAssetsSchema
      ),
    enabled: Boolean(workspaceDir),
  });

  const documentAssets = useQuery({
    queryKey: ["workspace-document-assets", workspaceDir],
    queryFn: () =>
      apiJson(
        `/api/workspace/document-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        specAssetsSchema
      ),
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
      apiJson("/api/workspace/profiles", z.unknown(), {
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
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles", workspaceDir] }),
  });

  const validateProfile = useMutation({
    mutationFn: (name: string) =>
      apiJson(`/api/workspace/profiles/${name}/validate`, z.unknown(), {
        method: "POST",
        body: JSON.stringify({ workspace_dir: workspaceDir }),
      }),
  });

  const setDefaultProfile = useMutation({
    mutationFn: (name: string) =>
      apiJson(`/api/workspace/profiles/${name}/default`, z.unknown(), {
        method: "POST",
        body: JSON.stringify({ workspace_dir: workspaceDir }),
      }),
  });

  const duplicateProfile = useMutation({
    mutationFn: ({ sourceName, targetName }: { sourceName: string; targetName: string }) =>
      apiJson(`/api/workspace/profiles/${sourceName}/duplicate`, z.unknown(), {
        method: "POST",
        body: JSON.stringify({ workspace_dir: workspaceDir, name: targetName }),
      }),
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
        <form
          className="stack-form"
          onSubmit={form.handleSubmit((values) => createProfile.mutate(values))}
        >
          <label>
            Profile name
            <input {...form.register("name", { required: true })} placeholder="nvme_default" />
          </label>
          <label>
            Jira source
            <select {...form.register("jiraSource", { required: true })}>
              {sources
                .filter((source) => source.kind === "jira")
                .map((source) => (
                  <option key={source.name}>{source.name}</option>
                ))}
            </select>
          </label>
          <label>
            Jira selector
            <select {...form.register("jiraSelector", { required: true })}>
              {selectors
                .filter((selector) => selector.source === form.watch("jiraSource"))
                .map((selector) => (
                  <option key={selector.name}>{selector.name}</option>
                ))}
            </select>
          </label>
          <label>
            Evidence source
            <select {...form.register("evidenceSource", { required: true })}>
              {sources
                .filter((source) => source.kind === "confluence")
                .map((source) => (
                  <option key={source.name}>{source.name}</option>
                ))}
            </select>
          </label>
          <label>
            Evidence selector
            <select {...form.register("evidenceSelector", { required: true })}>
              {selectors
                .filter((selector) => selector.source === form.watch("evidenceSource"))
                .map((selector) => (
                  <option key={selector.name}>{selector.name}</option>
                ))}
            </select>
          </label>
          <label>
            Spec asset
            <select {...form.register("specAssetId")}>
              <option value="">No spec asset</option>
              {(specAssets.data?.assets || []).map((asset: SpecAsset) => (
                <option
                  key={`${asset.asset_id}:${asset.version || ""}`}
                  value={asset.asset_id}
                >
                  {asset.asset_id}
                  {asset.parser_used ? ` / ${asset.parser_used}` : ""}
                </option>
              ))}
              {!specAssets.data?.assets.some((asset) => asset.asset_id === "nvme-spec-mineru") && (
                <option value="nvme-spec-mineru">nvme-spec-mineru / pending</option>
              )}
            </select>
          </label>
          <label>
            Document assets (uploaded files)
            <div
              style={{
                maxHeight: "150px",
                overflowY: "auto",
                border: "1px solid var(--border)",
                borderRadius: "4px",
                padding: "8px",
              }}
            >
              {(documentAssets.data?.assets || []).length === 0 ? (
                <p style={{ margin: 0, color: "var(--text-secondary)" }}>
                  No uploaded documents available
                </p>
              ) : (
                (documentAssets.data?.assets || []).map((asset: SpecAsset) => (
                  <label
                    key={asset.asset_id}
                    style={{ display: "flex", alignItems: "center", gap: "8px", padding: "4px 0" }}
                  >
                    <input type="checkbox" value={asset.asset_id} {...form.register("documentAssetIds")} />
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
          <button disabled={createProfile.isPending} type="submit">
            Create Profile
          </button>
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
        {validateProfile.error && (
          <div className="error">{String(validateProfile.error.message)}</div>
        )}
        {setDefaultProfile.error && (
          <div className="error">{String(setDefaultProfile.error.message)}</div>
        )}
        {duplicateProfile.error && (
          <div className="error">{String(duplicateProfile.error.message)}</div>
        )}
      </ListPanel>
    </section>
  );
}
