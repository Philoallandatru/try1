import { z } from "zod";

// Workspace schemas
export const workspaceSchema = z.object({
  name: z.string().optional(),
  workspace_dir: z.string(),
});

export const workspacesSchema = z.object({
  workspaces: z.array(workspaceSchema),
});

// Profile schemas
export const profileSchema = z.object({
  name: z.string(),
  inputs: z.record(z.string(), z.unknown()).optional(),
  analysis: z.record(z.string(), z.unknown()).optional(),
});

export const profilesSchema = z.object({
  profiles: z.array(profileSchema),
});

// Asset schemas
export const specAssetSchema = z.object({
  asset_id: z.string(),
  display_name: z.string().optional(),
  version: z.string().optional(),
  parser_used: z.string().optional(),
  document_id: z.string().optional(),
});

export const specAssetsSchema = z.object({
  assets: z.array(specAssetSchema),
});

// Source schemas
export const sourceSchema = z.object({
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

export const selectorSchema = z.object({
  name: z.string(),
  source: z.string(),
  selector: z.record(z.string(), z.unknown()).optional(),
});

export const sourcesResponseSchema = z.object({
  sources: z.array(sourceSchema),
  selectors: z.array(selectorSchema).default([]),
});

// Analysis schemas
export const analyzeSchema = z.object({
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

export const runsSchema = z.object({
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

// Retrieval schemas
export const indexStatsSchema = z.object({
  total_documents: z.number(),
  total_pages: z.number(),
  index_size_mb: z.number().optional(),
  last_updated: z.string().optional(),
});

export const datasetsResponseSchema = z.object({
  datasets: z.array(
    z.object({
      name: z.string(),
      description: z.string().optional(),
      query_count: z.number(),
    }),
  ),
});

export const evaluationResultsResponseSchema = z.object({
  results: z.array(
    z.object({
      run_id: z.string(),
      dataset: z.string(),
      strategy: z.string(),
      metrics: z.record(z.string(), z.number()),
      timestamp: z.string(),
    }),
  ),
});

// Model config schemas
export const configResponseSchema = z.object({
  model: z.string().optional(),
  temperature: z.number().optional(),
  max_tokens: z.number().optional(),
});

// Type exports
export type Workspace = z.infer<typeof workspaceSchema>;
export type Profile = z.infer<typeof profileSchema>;
export type SpecAsset = z.infer<typeof specAssetSchema>;
export type Source = z.infer<typeof sourceSchema>;
export type Selector = z.infer<typeof selectorSchema>;
export type AnalyzeResult = z.infer<typeof analyzeSchema>;
export type Run = z.infer<typeof runsSchema>["runs"][number];
export type IndexStats = z.infer<typeof indexStatsSchema>;
export type ModelConfig = z.infer<typeof configResponseSchema>;
