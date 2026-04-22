# SSD Knowledge Portal - Web Frontend

React + TypeScript 前端应用，提供直观的 Web 界面用于管理数据源、执行分析和查看结果。

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **TanStack Query** - 数据获取和缓存
- **React Router** - 路由管理
- **Lucide React** - 图标库
- **React Markdown** - Markdown 渲染
- **Playwright** - E2E 测试

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动。

### 构建生产版本

```bash
npm run build
```

构建产物输出到 `dist/` 目录。

### 运行测试

```bash
# 单元测试
npm run test

# 单元测试（UI 模式）
npm run test:ui

# 单元测试（覆盖率）
npm run test:coverage

# E2E 测试（单元测试，不需要后端）
npm run test:e2e:unit

# E2E 测试（集成测试，需要后端运行）
npm run test:e2e:integration

# E2E 测试（UI 模式）
npm run test:e2e:ui

# E2E 测试（调试模式）
npm run test:e2e:debug
```

## 项目结构

```
apps/portal_web/
├── src/
│   ├── main.tsx                    # 应用入口
│   ├── styles.css                  # 全局样式
│   ├── ErrorBoundary.tsx           # 错误边界组件
│   ├── SkeletonLoader.tsx          # 骨架屏组件
│   ├── useWebSocket.ts             # WebSocket Hook
│   ├── apiUtils.ts                 # API 工具函数
│   ├── errorMessages.ts            # 错误消息映射
│   ├── AnalysisResultsPage.tsx    # 分析结果页面
│   ├── DailyReportPage.tsx         # 每日报告页面
│   ├── BatchAnalysisPage.tsx      # 批量分析页面
│   └── DocumentManagementPage.tsx  # 文档管理页面
├── e2e/                            # E2E 测试
│   ├── document-management.spec.ts
│   ├── analysis.spec.ts
│   └── index-management.spec.ts
├── public/                         # 静态资源
├── playwright.config.ts            # Playwright 配置
├── vite.config.ts                  # Vite 配置
└── package.json
```

## 核心功能

### 1. 数据源管理

**支持的数据源类型：**
- Jira - 连接 Jira 实例，同步 Issues
- Confluence - 连接 Confluence 实例，同步 Pages
- 文件上传 - 上传 PDF、DOCX、XLSX、PPTX 文档

**功能：**
- 配置向导（3 步完成）
- 连接测试
- 增量同步
- 状态监控

### 2. 文档管理

**文档类型：**
- Specification（规范）
- Design（设计文档）
- Policy（策略文档）
- Reference（参考文档）
- Other（其他）

**功能：**
- 拖拽上传
- 类型分类
- 自动索引
- 搜索过滤
- 批量操作

### 3. 分析功能

**深度分析：**
- 单 Issue 综合分析
- 自动检索相关文档
- LLM 生成分析报告
- 引用追踪

**每日报告：**
- 渐进式生成
- 快速版（5 秒）
- 完整版（5 分钟）
- 实时更新（WebSocket）

**批量分析：**
- 多 Issue 并行分析
- 进度跟踪
- 结果汇总

### 4. 检索功能

**检索策略：**
- BM25 - 关键词匹配
- 语义检索 - 向量相似度
- 混合检索 - 加权组合

**索引管理：**
- 构建索引
- 查看统计
- 重建索引

## 性能优化

### 性能监控

应用内置了完整的性能监控系统，自动收集和报告关键性能指标。

**开发环境：**
- 点击右下角的图表图标 📊 打开性能监控面板
- 实时查看 Web Vitals、API 性能和自定义指标
- 导出性能数据用于分析

**编程接口：**

```typescript
import { performanceMonitor } from './performanceMonitor';

// 记录自定义指标
performanceMonitor.recordMetric('operation', 150);

// 测量 API 调用
await performanceMonitor.measureApiCall('fetch-data', async () => {
  return await fetch('/api/data').then(r => r.json());
});

// 获取性能报告
const report = performanceMonitor.getReport();
```

详细文档请参考 [PERFORMANCE.md](./PERFORMANCE.md)

### 代码分割

使用 React.lazy() 懒加载页面组件：

```typescript
const AnalysisResultsPage = lazy(() => 
  import("./AnalysisResultsPage").then(m => ({ default: m.AnalysisResultsPage }))
);
```

### 缓存策略

React Query 配置：
- `staleTime: 5 分钟` - 数据新鲜度
- `gcTime: 10 分钟` - 垃圾回收时间
- `retry: 3` - 自动重试次数
- `refetchOnWindowFocus: false` - 禁用窗口焦点刷新

### 加载状态

**骨架屏：**
- SkeletonBox - 基础占位符
- SkeletonCard - 卡片占位符
- SkeletonList - 列表占位符
- SkeletonTable - 表格占位符
- SkeletonPage - 页面占位符

**进度指示器：**
- 进度条（带动画）
- 加载旋转器
- 连接状态指示

### WebSocket 实时更新

```typescript
const { isConnected, lastMessage } = useWebSocket(wsUrl, {
  onMessage: (message) => {
    // 处理消息
  },
  reconnect: true,
  reconnectAttempts: 5,
});
```

## 错误处理

### 全局错误边界

捕获 React 组件树中的错误：

```typescript
<ErrorBoundary>
  <App />
</ErrorBoundary>
```

### API 重试机制

自动重试失败的 API 请求：

```typescript
const data = await fetchWithRetry(url, schema, {
  maxRetries: 3,
  retryDelay: 1000,
});
```

### 用户友好错误消息

将技术错误转换为用户可理解的消息：

```typescript
const friendlyMessage = getUserFriendlyErrorMessage(error);
```

## API 集成

### 后端 API

默认连接到 `http://localhost:8000`

**主要端点：**
- `GET /api/workspaces` - 获取工作空间列表
- `GET /api/workspace/sources` - 获取数据源
- `POST /api/workspace/sources` - 创建数据源
- `GET /api/workspace/documents` - 获取文档列表
- `POST /api/workspace/documents/upload` - 上传文档
- `POST /api/analysis/deep` - 执行深度分析
- `GET /api/retrieval/search` - 执行检索

### 认证

使用 Bearer Token 认证：

```typescript
headers: {
  'Authorization': `Bearer ${token}`
}
```

Token 存储在 localStorage 中：`ssdPortalToken`

## 样式系统

### CSS 变量

使用 CSS 变量实现主题：

```css
:root {
  --page: #fafafa;
  --panel: #ffffff;
  --panel-soft: #f5f5f5;
  --line: #e0e0e0;
  --text: #1a1a1a;
  --muted: #666666;
  --faint: #999999;
  --accent: #2563eb;
  --accent-bright: #3b82f6;
  --success: #10b981;
  --error: #ef4444;
  --warning: #f59e0b;
}
```

### 响应式设计

使用媒体查询适配不同屏幕：

```css
@media (max-width: 768px) {
  /* 移动端样式 */
}
```

## 测试

### 单元测试

使用 Vitest 和 React Testing Library 进行单元测试。

**已测试组件：**
- ErrorBoundary - 错误边界组件
- SkeletonLoader - 骨架屏组件
- apiUtils - API 工具函数

**运行测试：**

```bash
npm run test              # 运行所有单元测试
npm run test:ui           # UI 模式
npm run test:coverage     # 生成覆盖率报告
```

### E2E 测试覆盖

**单元测试（不需要后端）：**
- 文档管理 UI 交互
- Markdown 渲染
- 中文输出支持

**集成测试（需要后端）：**
- 完整的文档上传流程
- 分析功能
- 索引管理
- 数据源配置

**运行 E2E 测试：**

```bash
npm run test:e2e:unit         # 单元测试
npm run test:e2e:integration  # 集成测试（需要后端）
npm run test:e2e:ui           # UI 模式
```

### 测试最佳实践

1. 使用稳定的选择器（id、data-testid）
2. 等待元素可见后再交互
3. 模拟真实用户行为
4. 验证 UI 反馈
5. 测试错误场景
6. 分离单元测试和集成测试
7. 使用 React Testing Library 测试组件
8. 使用 Vitest 进行快速单元测试

## 开发指南

### 添加新页面

1. 创建页面组件：`src/NewPage.tsx`
2. 在 `main.tsx` 中添加懒加载：
   ```typescript
   const NewPage = lazy(() => import("./NewPage").then(m => ({ default: m.NewPage })));
   ```
3. 添加路由：
   ```typescript
   <Route path="/new" element={<NewPage />} />
   ```
4. 在侧边栏添加导航链接

### 添加新 API 调用

1. 定义 Zod schema：
   ```typescript
   const responseSchema = z.object({
     data: z.array(z.string()),
   });
   ```
2. 使用 React Query：
   ```typescript
   const { data } = useQuery({
     queryKey: ["key"],
     queryFn: () => apiJson("/api/endpoint", responseSchema),
   });
   ```

### 添加新组件

1. 创建组件文件
2. 使用 TypeScript 定义 Props
3. 添加必要的样式
4. 编写 E2E 测试

## 常见问题

### Q: 如何调试 WebSocket 连接？

**A:** 打开浏览器开发者工具 → Network → WS，查看 WebSocket 消息。

### Q: 如何修改 API 地址？

**A:** 修改 Vite 配置中的 proxy 设置：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://your-backend:8000'
    }
  }
});
```

### Q: 如何添加新的骨架屏？

**A:** 使用 `SkeletonLoader.tsx` 中的基础组件组合：

```typescript
<div className="custom-skeleton">
  <SkeletonBox width="200px" height="32px" />
  <SkeletonText lines={3} />
</div>
```

### Q: 如何处理大文件上传？

**A:** 使用分块上传和进度跟踪：

```typescript
const formData = new FormData();
formData.append('file', file);

const response = await fetch('/api/upload', {
  method: 'POST',
  body: formData,
  onUploadProgress: (e) => {
    setProgress((e.loaded / e.total) * 100);
  }
});
```

## 贡献

欢迎贡献！请遵循以下规范：

1. 使用 TypeScript
2. 遵循现有代码风格
3. 添加必要的类型定义
4. 编写 E2E 测试
5. 更新文档

## 许可证

内部项目，仅供 SSD 团队使用。
