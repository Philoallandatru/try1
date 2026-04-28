import { z } from "zod";
import { apiJson } from "../apiUtils";
import {
  workspacesSchema,
  workspaceSchema,
  profilesSchema,
  sourcesResponseSchema,
  specAssetsSchema,
  runsSchema,
  indexStatsSchema,
  datasetsResponseSchema,
  evaluationResultsResponseSchema,
  configResponseSchema,
} from "./schemas";

/**
 * Centralized API client for all backend endpoints.
 * Eliminates duplication and provides consistent error handling.
 */
export const api = {
  // Workspace endpoints
  workspaces: {
    list: () => apiJson("/api/workspaces", workspacesSchema),

    get: (workspaceDir: string) =>
      apiJson(
        `/api/workspaces/${encodeURIComponent(workspaceDir)}`,
        workspaceSchema,
        { method: "GET" }
      ),

    create: (data: { name: string }) =>
      apiJson("/api/workspaces", workspaceSchema, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (workspaceDir: string, data: { name: string }) =>
      apiJson(
        `/api/workspaces/${encodeURIComponent(workspaceDir)}`,
        workspaceSchema,
        {
          method: "PATCH",
          body: JSON.stringify(data),
        }
      ),

    delete: (workspaceDir: string) =>
      apiJson(
        `/api/workspaces/${encodeURIComponent(workspaceDir)}`,
        z.unknown(),
        { method: "DELETE" }
      ),
  },

  // Profile endpoints
  profiles: {
    list: (workspaceDir: string) =>
      apiJson(
        `/api/workspace/profiles?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        profilesSchema
      ),

    delete: (name: string, workspaceDir: string) =>
      apiJson(
        `/api/workspace/profiles/${name}`,
        z.unknown(),
        {
          method: "DELETE",
          body: JSON.stringify({ workspace_dir: workspaceDir }),
        }
      ),
  },

  // Source endpoints
  sources: {
    list: (workspaceDir: string) =>
      apiJson(
        `/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        sourcesResponseSchema
      ),

    create: (data: unknown) =>
      apiJson("/api/workspace/sources", z.unknown(), {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (name: string, data: unknown) =>
      apiJson(`/api/workspace/sources/${name}`, z.unknown(), {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    delete: (name: string, workspaceDir: string) =>
      apiJson(
        `/api/workspace/sources/${name}`,
        z.unknown(),
        {
          method: "DELETE",
          body: JSON.stringify({ workspace_dir: workspaceDir }),
        }
      ),
  },

  // Selector endpoints
  selectors: {
    create: (data: unknown) =>
      apiJson("/api/workspace/selectors", z.unknown(), {
        method: "POST",
        body: JSON.stringify(data),
      }),

    delete: (name: string, workspaceDir: string) =>
      apiJson(
        `/api/workspace/selectors/${name}`,
        z.unknown(),
        {
          method: "DELETE",
          body: JSON.stringify({ workspace_dir: workspaceDir }),
        }
      ),
  },

  // Asset endpoints
  assets: {
    listSpec: (workspaceDir: string) =>
      apiJson(
        `/api/workspace/spec-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        specAssetsSchema
      ),

    listDocument: (workspaceDir: string) =>
      apiJson(
        `/api/workspace/document-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        specAssetsSchema
      ),
  },

  // Run endpoints
  runs: {
    list: (workspaceDir: string) =>
      apiJson(
        `/api/workspace/runs?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        runsSchema
      ),
  },

  // Retrieval endpoints
  retrieval: {
    indexStats: (workspaceDir: string) =>
      apiJson(
        `/api/retrieval/index/stats?workspace_dir=${encodeURIComponent(workspaceDir)}`,
        indexStatsSchema
      ),

    datasets: () =>
      apiJson("/api/retrieval/datasets", datasetsResponseSchema),

    results: () =>
      apiJson("/api/retrieval/results", evaluationResultsResponseSchema),
  },

  // Model config endpoints
  modelConfig: {
    get: () => apiJson("/api/model-config", configResponseSchema),
  },
};
