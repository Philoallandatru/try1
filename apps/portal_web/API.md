# API 文档

本文档描述了 SSD Knowledge Portal 前端与后端之间的 API 接口。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **认证方式**: Bearer Token (存储在 localStorage 的 `ssdPortalToken`)
- **内容类型**: `application/json`
- **字符编码**: UTF-8

## 认证

所有 API 请求都需要在 Header 中包含认证 Token：

```http
Authorization: Bearer <token>
```

## 通用响应格式

### 成功响应

```json
{
  "data": { ... },
  "message": "Success"
}
```

### 错误响应

```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## API 端点

### 工作空间管理

#### 获取工作空间列表

```http
GET /api/workspaces
```

**响应示例：**

```json
{
  "workspaces": [
    {
      "name": "default",
      "path": "/path/to/workspace",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 创建工作空间

```http
POST /api/workspaces
Content-Type: application/json

{
  "name": "workspace-name",
  "description": "Workspace description"
}
```

#### 获取工作空间配置文件

```http
GET /api/workspace/profiles?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "profiles": [
    {
      "name": "default",
      "llm_provider": "lmstudio",
      "model_name": "qwen2.5-14b",
      "is_default": true
    }
  ]
}
```

#### 创建配置文件

```http
POST /api/workspace/profiles
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "name": "profile-name",
  "llm_provider": "lmstudio",
  "model_name": "qwen2.5-14b",
  "base_url": "http://localhost:1234/v1",
  "api_key": "optional-api-key"
}
```

#### 验证配置文件

```http
POST /api/workspace/profiles/<profile_name>/validate
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace"
}
```

#### 设置默认配置文件

```http
POST /api/workspace/profiles/<profile_name>/default
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace"
}
```

#### 复制配置文件

```http
POST /api/workspace/profiles/<profile_name>/duplicate
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "new_name": "new-profile-name"
}
```

### 数据源管理

#### 获取数据源列表

```http
GET /api/workspace/sources?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "sources": [
    {
      "name": "jira-source",
      "type": "jira",
      "config": {
        "server_url": "https://jira.example.com",
        "project_key": "PROJ"
      },
      "status": "active",
      "last_sync": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 创建 Jira 数据源

```http
POST /api/workspace/sources
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "name": "jira-source",
  "type": "jira",
  "config": {
    "server_url": "https://jira.example.com",
    "username": "user@example.com",
    "api_token": "token",
    "project_key": "PROJ",
    "jql": "project = PROJ"
  }
}
```

#### 创建 Confluence 数据源

```http
POST /api/workspace/sources
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "name": "confluence-source",
  "type": "confluence",
  "config": {
    "server_url": "https://confluence.example.com",
    "username": "user@example.com",
    "api_token": "token",
    "space_key": "SPACE"
  }
}
```

#### 测试数据源连接

```http
POST /api/workspace/sources/<source_name>/test
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace"
}
```

**响应示例：**

```json
{
  "success": true,
  "message": "Connection successful",
  "details": {
    "server_version": "8.20.0",
    "accessible_projects": ["PROJ1", "PROJ2"]
  }
}
```

#### 刷新数据源

```http
POST /api/workspace/sources/<source_name>/refresh
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace"
}
```

### 文档管理

#### 获取文档类型列表

```http
GET /api/documents/types
```

**响应示例：**

```json
{
  "types": [
    "Specification",
    "Design",
    "Policy",
    "Reference",
    "Other"
  ]
}
```

#### 获取文档列表

```http
GET /api/documents/list?workspace=<workspace_name>[&document_type=<type>]
```

**查询参数：**
- `workspace` (必需): 工作空间名称
- `document_type` (可选): 文档类型过滤

**响应示例：**

```json
{
  "documents": [
    {
      "id": "doc-123",
      "name": "API Specification.pdf",
      "type": "Specification",
      "size": 1024000,
      "uploaded_at": "2024-01-01T00:00:00Z",
      "status": "indexed"
    }
  ]
}
```

#### 上传文档

```http
POST /api/documents/upload
Content-Type: multipart/form-data

file: <file>
workspace: <workspace_name>
document_type: <type>
```

**支持的文件格式：**
- PDF (.pdf)
- Word (.docx)
- Excel (.xlsx)
- PowerPoint (.pptx)

**响应示例：**

```json
{
  "task_id": "task-123",
  "message": "Document upload started"
}
```

#### 查询文档处理任务状态

```http
GET /api/documents/task/<task_id>
```

**响应示例：**

```json
{
  "task_id": "task-123",
  "status": "processing",
  "progress": 50,
  "message": "Extracting text from PDF..."
}
```

#### 删除文档

```http
DELETE /api/documents/delete?workspace=<workspace_name>&doc_id=<document_id>
```

### 分析功能

#### 深度分析 (WebSocket)

```
ws://localhost:8000/api/analysis/deep/<issue_id>/stream?workspace_dir=<workspace_path>
```

**WebSocket 消息格式：**

```json
{
  "type": "progress",
  "data": {
    "stage": "retrieving",
    "progress": 30,
    "message": "Searching knowledge base..."
  }
}
```

```json
{
  "type": "result",
  "data": {
    "analysis": "Analysis result in markdown format",
    "references": [
      {
        "doc_id": "doc-123",
        "title": "API Specification",
        "relevance": 0.95
      }
    ]
  }
}
```

#### 获取深度分析结果

```http
GET /api/analysis/deep/<issue_id>?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "issue_id": "PROJ-123",
  "analysis": "Analysis result in markdown format",
  "references": [...],
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### 生成每日报告

```http
POST /api/analysis/daily-report
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "date": "2024-01-01",
  "mode": "quick"
}
```

**参数说明：**
- `mode`: `"quick"` (5秒快速版) 或 `"full"` (5分钟完整版)

**响应示例：**

```json
{
  "report": "Daily report in markdown format",
  "issues_analyzed": 10,
  "generated_at": "2024-01-01T00:00:00Z"
}
```

#### 执行 Jira 分析

```http
POST /api/workspace/analyze-jira
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "source_name": "jira-source",
  "issue_keys": ["PROJ-123", "PROJ-124"]
}
```

### 批量分析

#### 获取批量分析列表

```http
GET /api/analysis/batches?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "batches": [
    {
      "batch_id": "batch-123",
      "created_at": "2024-01-01T00:00:00Z",
      "total_issues": 10,
      "completed": 8,
      "status": "processing"
    }
  ]
}
```

#### 创建批量分析

```http
POST /api/analysis/batch
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "issue_keys": ["PROJ-123", "PROJ-124", "PROJ-125"]
}
```

**响应示例：**

```json
{
  "batch_id": "batch-123",
  "message": "Batch analysis started"
}
```

#### 获取批量分析详情

```http
GET /api/analysis/batch/<batch_id>?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "batch_id": "batch-123",
  "status": "completed",
  "total_issues": 10,
  "completed": 10,
  "failed": 0,
  "results": [
    {
      "issue_key": "PROJ-123",
      "status": "completed",
      "analysis": "..."
    }
  ]
}
```

#### 导出批量分析结果

```http
GET /api/export/batch/<batch_id>/<format>?workspace_dir=<workspace_path>
```

**支持的格式：**
- `json`: JSON 格式
- `csv`: CSV 格式
- `markdown`: Markdown 格式

### 检索功能

#### 搜索知识库

```http
POST /api/retrieval/search
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "query": "search query",
  "method": "hybrid",
  "limit": 10
}
```

**参数说明：**
- `method`: `"bm25"` (关键词), `"semantic"` (语义), 或 `"hybrid"` (混合)
- `limit`: 返回结果数量 (默认 10)

**响应示例：**

```json
{
  "results": [
    {
      "doc_id": "doc-123",
      "title": "API Specification",
      "content": "Relevant content snippet...",
      "score": 0.95,
      "metadata": {
        "type": "Specification",
        "page": 5
      }
    }
  ]
}
```

#### 知识库搜索 (简化版)

```http
GET /api/analysis/knowledge/search?workspace_dir=<workspace_path>&query=<query>&limit=<limit>
```

### 索引管理

#### 获取索引统计

```http
GET /api/retrieval/index/stats?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "total_documents": 100,
  "total_chunks": 5000,
  "index_size_mb": 250,
  "last_updated": "2024-01-01T00:00:00Z",
  "methods": {
    "bm25": {
      "enabled": true,
      "documents": 100
    },
    "semantic": {
      "enabled": true,
      "documents": 100,
      "model": "bge-large-zh-v1.5"
    }
  }
}
```

#### 构建索引

```http
POST /api/retrieval/index/build
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "methods": ["bm25", "semantic"],
  "force_rebuild": false
}
```

**参数说明：**
- `methods`: 要构建的索引类型数组
- `force_rebuild`: 是否强制重建 (默认 false)

### 规范资产管理

#### 获取规范资产列表

```http
GET /api/workspace/spec-assets?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "assets": [
    {
      "id": "nvme-spec",
      "name": "NVMe Specification",
      "type": "pdf",
      "status": "indexed",
      "pages": 500
    }
  ]
}
```

#### 检查 MinerU 依赖

```http
GET /api/workspace/spec-assets/nvme-spec-mineru/require-mineru?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "required": true,
  "installed": false,
  "message": "MinerU is required for PDF processing"
}
```

#### 导入规范资产

```http
POST /api/workspace/spec-assets/ingest
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace",
  "asset_id": "nvme-spec",
  "use_mineru": true
}
```

### 运行历史

#### 获取运行列表

```http
GET /api/workspace/runs?workspace_dir=<workspace_path>
```

**响应示例：**

```json
{
  "runs": [
    {
      "run_id": "run-123",
      "issue_key": "PROJ-123",
      "status": "completed",
      "created_at": "2024-01-01T00:00:00Z",
      "duration_seconds": 45
    }
  ]
}
```

#### 获取运行详情

```http
GET /api/workspace/runs/<run_id>?workspace_dir=<workspace_path>
```

#### 获取运行产物 - 深度分析结果

```http
GET /api/workspace/runs/<run_id>/artifacts/deep_analysis_result?workspace_dir=<workspace_path>
```

#### 获取运行产物 - LLM 验证结果

```http
GET /api/workspace/runs/<run_id>/artifacts/llm_verification?workspace_dir=<workspace_path>
```

#### 获取运行产物 - LLM 验证历史

```http
GET /api/workspace/runs/<run_id>/artifacts/llm_verification_history?workspace_dir=<workspace_path>
```

#### 执行 LLM 验证

```http
POST /api/workspace/runs/<run_id>/verify-llm
Content-Type: application/json

{
  "workspace_dir": "/path/to/workspace"
}
```

## 错误代码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 (Token 无效或过期) |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 502 | 网关错误 |
| 503 | 服务不可用 |

## 前端 API 工具函数

### apiJson

用于发送 JSON 请求并验证响应：

```typescript
import { apiJson } from './apiUtils';
import { z } from 'zod';

const schema = z.object({
  data: z.array(z.string())
});

const result = await apiJson('/api/endpoint', schema, {
  method: 'POST',
  body: { key: 'value' }
});
```

### fetchWithRetry

带重试机制的 fetch 封装：

```typescript
import { fetchWithRetry } from './apiUtils';

const result = await fetchWithRetry(
  '/api/endpoint',
  schema,
  { method: 'GET' },
  {
    maxRetries: 3,
    initialDelay: 1000,
    backoffMultiplier: 2
  }
);
```

**重试配置：**
- `maxRetries`: 最大重试次数 (默认 3)
- `initialDelay`: 初始延迟毫秒数 (默认 1000)
- `backoffMultiplier`: 退避倍数 (默认 2)

**可重试的状态码：**
- 408 (Request Timeout)
- 429 (Too Many Requests)
- 500 (Internal Server Error)
- 502 (Bad Gateway)
- 503 (Service Unavailable)
- 504 (Gateway Timeout)

### getUserFriendlyError

将技术错误转换为用户友好的消息：

```typescript
import { getUserFriendlyError } from './errorMessages';

try {
  await apiCall();
} catch (error) {
  const friendly = getUserFriendlyError(error);
  console.log(friendly.title);    // "Connection Error"
  console.log(friendly.message);  // "Unable to connect to the server..."
  console.log(friendly.action);   // "Verify the backend server is running..."
}
```

## React Query 集成

### 查询示例

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiJson } from './apiUtils';

const { data, isLoading, error } = useQuery({
  queryKey: ['workspaces'],
  queryFn: () => apiJson('/api/workspaces', workspacesSchema),
  staleTime: 5 * 60 * 1000,  // 5 分钟
  retry: 3
});
```

### Mutation 示例

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';

const queryClient = useQueryClient();

const mutation = useMutation({
  mutationFn: (data) => apiJson('/api/workspaces', schema, {
    method: 'POST',
    body: data
  }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['workspaces'] });
  }
});
```

## WebSocket 集成

### useWebSocket Hook

```typescript
import { useWebSocket } from './useWebSocket';

const { isConnected, lastMessage, sendMessage } = useWebSocket(
  'ws://localhost:8000/api/analysis/deep/PROJ-123/stream',
  {
    onMessage: (message) => {
      console.log('Received:', message);
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
    reconnect: true,
    reconnectAttempts: 5,
    reconnectInterval: 3000
  }
);
```

## 最佳实践

### 1. 错误处理

始终使用 try-catch 包裹 API 调用：

```typescript
try {
  const result = await apiJson('/api/endpoint', schema);
  // 处理成功结果
} catch (error) {
  const friendly = getUserFriendlyError(error);
  // 显示友好错误消息
}
```

### 2. 加载状态

使用骨架屏提升用户体验：

```typescript
if (isLoading) {
  return <SkeletonPage />;
}
```

### 3. 缓存策略

合理设置 staleTime 和 gcTime：

```typescript
useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
  staleTime: 5 * 60 * 1000,   // 5 分钟内不重新请求
  gcTime: 10 * 60 * 1000,     // 10 分钟后清理缓存
});
```

### 4. 请求取消

使用 AbortController 取消请求：

```typescript
const controller = new AbortController();

fetch('/api/endpoint', {
  signal: controller.signal
});

// 取消请求
controller.abort();
```

### 5. 类型安全

使用 Zod schema 验证响应：

```typescript
const schema = z.object({
  data: z.array(z.string()),
  total: z.number()
});

type Response = z.infer<typeof schema>;
```

## 性能优化

### 1. 并行请求

使用 Promise.all 并行发送多个请求：

```typescript
const [workspaces, sources, documents] = await Promise.all([
  apiJson('/api/workspaces', workspacesSchema),
  apiJson('/api/workspace/sources', sourcesSchema),
  apiJson('/api/documents/list', documentsSchema)
]);
```

### 2. 请求去重

React Query 自动去重相同的请求：

```typescript
// 这两个查询会被合并为一个请求
useQuery({ queryKey: ['data'], queryFn: fetchData });
useQuery({ queryKey: ['data'], queryFn: fetchData });
```

### 3. 预取数据

提前加载可能需要的数据：

```typescript
queryClient.prefetchQuery({
  queryKey: ['data'],
  queryFn: fetchData
});
```

## 调试技巧

### 1. 查看网络请求

打开浏览器开发者工具 → Network 标签页

### 2. 查看 WebSocket 消息

打开浏览器开发者工具 → Network → WS 标签页

### 3. React Query DevTools

```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

<QueryClientProvider client={queryClient}>
  <App />
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

### 4. 日志记录

在 apiUtils.ts 中添加日志：

```typescript
console.log('Request:', url, options);
console.log('Response:', data);
```

## 更新日志

### 2024-01-01
- 初始版本
- 添加所有核心 API 端点
- 添加 WebSocket 支持
- 添加错误处理和重试机制
