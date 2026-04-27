/**
 * Centralized API module
 *
 * Exports:
 * - api: Direct API client for imperative calls
 * - queries: React Query query factories
 * - queryKeys: Query key factory for cache management
 * - All Zod schemas and TypeScript types
 */

export { api } from "./client";
export { queries, queryKeys } from "./queries";
export * from "./schemas";
