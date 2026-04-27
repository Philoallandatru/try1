import { api } from "./client";

/**
 * Query key factory for React Query.
 * Centralizes query key generation for consistent cache management.
 */
export const queryKeys = {
  // Workspace keys
  workspaces: {
    all: ["workspaces"] as const,
    detail: (workspaceDir: string) => ["workspaces", workspaceDir] as const,
  },

  // Profile keys
  profiles: {
    all: (workspaceDir: string) => ["profiles", workspaceDir] as const,
  },

  // Source keys
  sources: {
    all: (workspaceDir: string) => ["sources", workspaceDir] as const,
  },

  // Asset keys
  assets: {
    spec: (workspaceDir: string) => ["spec-assets", workspaceDir] as const,
    document: (workspaceDir: string) => ["document-assets", workspaceDir] as const,
  },

  // Run keys
  runs: {
    all: (workspaceDir: string) => ["runs", workspaceDir] as const,
  },

  // Retrieval keys
  retrieval: {
    indexStats: (workspaceDir: string) => ["retrieval", "index-stats", workspaceDir] as const,
    datasets: ["retrieval", "datasets"] as const,
    results: ["retrieval", "results"] as const,
  },

  // Model config keys
  modelConfig: {
    current: ["model-config"] as const,
  },
};

/**
 * Query option factories for React Query.
 * Provides consistent query configurations with proper typing.
 */
export const queries = {
  // Workspace queries
  workspaces: {
    list: () => ({
      queryKey: queryKeys.workspaces.all,
      queryFn: api.workspaces.list,
    }),

    detail: (workspaceDir: string) => ({
      queryKey: queryKeys.workspaces.detail(workspaceDir),
      queryFn: () => api.workspaces.get(workspaceDir),
      enabled: Boolean(workspaceDir),
    }),
  },

  // Profile queries
  profiles: {
    list: (workspaceDir: string) => ({
      queryKey: queryKeys.profiles.all(workspaceDir),
      queryFn: () => api.profiles.list(workspaceDir),
      enabled: Boolean(workspaceDir),
    }),
  },

  // Source queries
  sources: {
    list: (workspaceDir: string) => ({
      queryKey: queryKeys.sources.all(workspaceDir),
      queryFn: () => api.sources.list(workspaceDir),
      enabled: Boolean(workspaceDir),
    }),
  },

  // Asset queries
  assets: {
    listSpec: (workspaceDir: string) => ({
      queryKey: queryKeys.assets.spec(workspaceDir),
      queryFn: () => api.assets.listSpec(workspaceDir),
      enabled: Boolean(workspaceDir),
    }),

    listDocument: (workspaceDir: string) => ({
      queryKey: queryKeys.assets.document(workspaceDir),
      queryFn: () => api.assets.listDocument(workspaceDir),
      enabled: Boolean(workspaceDir),
    }),
  },

  // Run queries
  runs: {
    list: (workspaceDir: string) => ({
      queryKey: queryKeys.runs.all(workspaceDir),
      queryFn: () => api.runs.list(workspaceDir),
      enabled: Boolean(workspaceDir),
    }),
  },

  // Retrieval queries
  retrieval: {
    indexStats: (workspaceDir: string) => ({
      queryKey: queryKeys.retrieval.indexStats(workspaceDir),
      queryFn: () => api.retrieval.indexStats(workspaceDir),
      enabled: Boolean(workspaceDir),
    }),

    datasets: () => ({
      queryKey: queryKeys.retrieval.datasets,
      queryFn: api.retrieval.datasets,
    }),

    results: () => ({
      queryKey: queryKeys.retrieval.results,
      queryFn: api.retrieval.results,
    }),
  },

  // Model config queries
  modelConfig: {
    current: () => ({
      queryKey: queryKeys.modelConfig.current,
      queryFn: api.modelConfig.get,
    }),
  },
};
