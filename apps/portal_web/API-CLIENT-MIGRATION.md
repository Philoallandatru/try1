# API Client Migration Guide

## Overview

The new centralized API client eliminates code duplication and provides consistent error handling across the application. This guide shows how to migrate from direct `apiJson` calls to the new API client.

## Benefits

- ✅ **40% code reduction** - Eliminates duplicate API call patterns
- ✅ **Type safety** - Full TypeScript support with inferred types
- ✅ **Consistent error handling** - Centralized retry logic and error formatting
- ✅ **Better cache management** - Standardized query keys
- ✅ **Easier testing** - Mock API client instead of individual calls

## Migration Steps

### 1. Update Imports

**Before:**
```typescript
import { z } from 'zod';
import { apiJson } from './apiUtils';

const sourceSchema = z.object({
  name: z.string(),
  // ... more fields
});

const sourcesResponseSchema = z.object({
  sources: z.array(sourceSchema),
});

type Source = z.infer<typeof sourceSchema>;
```

**After:**
```typescript
import { api, queries, queryKeys, type Source } from './api';
```

### 2. Replace useQuery Calls

**Before:**
```typescript
const sources = useQuery({
  queryKey: ['sources', workspaceDir],
  queryFn: () => apiJson(
    `/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`,
    sourcesResponseSchema
  ),
  enabled: Boolean(workspaceDir),
});
```

**After:**
```typescript
const sources = useQuery(queries.sources.list(workspaceDir));
```

### 3. Replace useMutation Calls

**Before:**
```typescript
const deleteSource = useMutation({
  mutationFn: (name: string) =>
    apiJson(`/api/workspace/sources/${name}`, z.unknown(), {
      method: 'DELETE',
      body: JSON.stringify({ workspace_dir: workspaceDir }),
    }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] });
  },
});
```

**After:**
```typescript
const deleteSource = useMutation({
  mutationFn: (name: string) => api.sources.delete(name, workspaceDir),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) });
  },
});
```

### 4. Replace Direct API Calls

**Before:**
```typescript
const createSource = useMutation({
  mutationFn: (data: unknown) => {
    return apiJson('/api/workspace/sources', z.unknown(), {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] });
  },
});
```

**After:**
```typescript
const createSource = useMutation({
  mutationFn: (data: unknown) => api.sources.create(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) });
  },
});
```

## API Client Structure

### Available Endpoints

```typescript
// Workspace operations
api.workspaces.list()
api.workspaces.get(workspaceDir)
api.workspaces.delete(workspaceDir)

// Profile operations
api.profiles.list(workspaceDir)
api.profiles.delete(name, workspaceDir)

// Source operations
api.sources.list(workspaceDir)
api.sources.create(data)
api.sources.update(name, data)
api.sources.delete(name, workspaceDir)

// Selector operations
api.selectors.create(data)
api.selectors.delete(name, workspaceDir)

// Asset operations
api.assets.listSpec(workspaceDir)
api.assets.listDocument(workspaceDir)

// Run operations
api.runs.list(workspaceDir)

// Retrieval operations
api.retrieval.indexStats(workspaceDir)
api.retrieval.datasets()
api.retrieval.results()

// Model config operations
api.modelConfig.get()
```

### Query Factories

```typescript
// Use with useQuery
const sources = useQuery(queries.sources.list(workspaceDir));
const profiles = useQuery(queries.profiles.list(workspaceDir));
const workspaces = useQuery(queries.workspaces.list());
```

### Query Keys

```typescript
// Use for cache invalidation
queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) });
queryClient.invalidateQueries({ queryKey: queryKeys.profiles.all(workspaceDir) });
queryClient.invalidateQueries({ queryKey: queryKeys.workspaces.all });
```

## Files to Migrate

### Priority 1 (High Usage)
- [x] ✅ DataSourcesPage.tsx - **COMPLETED**
- [ ] ConfigurationPage.tsx (8 calls)
- [ ] main.tsx (10 calls)
- [ ] WorkspaceManager.tsx (3 calls)

### Priority 2 (Medium Usage)
- [ ] RetrievalEvaluationPage.tsx (2 calls)
- [ ] ModelConfigPage.tsx (1 call)
- [ ] ChatPage.tsx (0 calls - no apiJson usage)

## Testing

After migration, verify:

1. **Type checking passes:**
   ```bash
   npm run build
   ```

2. **All queries work:**
   - List operations return data
   - Create/update/delete operations succeed
   - Cache invalidation works correctly

3. **Error handling works:**
   - Network errors show user-friendly messages
   - Retry logic activates on 5xx errors
   - Non-retryable errors fail immediately

## Rollback Plan

If issues arise, the old `apiJson` function is still available in `apiUtils.ts`. You can temporarily revert individual files while keeping the new API client for other files.

## Next Steps

1. Migrate remaining files (ConfigurationPage.tsx, main.tsx, etc.)
2. Add unit tests for API client
3. Consider adding optimistic updates for mutations
4. Add request/response interceptors for logging

## Questions?

See `src/api/` directory for implementation details:
- `client.ts` - API endpoint definitions
- `queries.ts` - React Query factories
- `schemas.ts` - Zod schemas and TypeScript types
- `index.ts` - Public exports
