# 数据源管理页面重新设计

## 问题分析

原始页面存在以下问题：

### 1. 设计风格不一致
- ❌ 使用黑色按钮，与其他页面的蓝色主题不符
- ❌ 布局混乱，文件上传、搜索、标签页混在一起
- ❌ 缺少统一的卡片样式和间距

### 2. 功能问题
- ❌ 没有显示已有数据源列表
- ❌ 缺少加载状态和错误提示
- ❌ 表单验证不完整
- ❌ 没有删除确认机制

### 3. 用户体验问题
- ❌ 添加后看不到结果
- ❌ 没有成功/失败反馈
- ❌ 表单字段缺少帮助文本

## 重新设计方案

### 1. 统一视觉风格

**颜色系统**：
- 主色：`#2563eb` (蓝色) - 与其他页面一致
- 成功：`#065f46` (绿色)
- 危险：`#dc2626` (红色)
- 中性：`#6b7280` (灰色)

**组件样式**：
- 使用 `.config-item` 卡片布局
- 统一的 `.primary-button` 样式
- 一致的 `.modal-overlay` 和 `.modal-content`

### 2. 改进的布局结构

```
┌─────────────────────────────────────────┐
│ 数据源管理                               │
│ 管理 Jira、Confluence 和文件数据源        │
├─────────────────────────────────────────┤
│ [+ 添加数据源] [刷新]                    │
├─────────────────────────────────────────┤
│ Jira 数据源 (2)                          │
│ ┌─────────────────────────────────────┐ │
│ │ my_jira  [jira] [Enabled]           │ │
│ │ Mode: live | Connector: jira.api    │ │
│ │                          [删除]      │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ Confluence 数据源 (1)                    │
│ ┌─────────────────────────────────────┐ │
│ │ my_confluence  [confluence] [Enabled]│ │
│ │                          [删除]      │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 3. 新增功能

#### 数据源列表
- ✅ 按类型分组显示（Jira / Confluence / Files）
- ✅ 显示状态（Enabled / Disabled）
- ✅ 显示文档数量和最后刷新时间
- ✅ 空状态提示和快速添加按钮

#### 添加数据源模态框
- ✅ 清晰的表单布局
- ✅ 实时验证和错误提示
- ✅ 帮助文本（Mock Server 地址提示）
- ✅ 加载状态和禁用按钮

#### 删除确认
- ✅ 两步确认机制
- ✅ 防止误删除

#### 状态反馈
- ✅ 加载动画（Loader2 spin）
- ✅ 错误提示（AlertCircle + 错误消息）
- ✅ 成功提示（通过 React Query 自动刷新）

## 测试步骤

### 前置条件
1. Mock Server 运行在 `http://localhost:8888`
2. 前端运行在 `http://127.0.0.1:5183`

### 测试用例

#### 1. 添加 Jira 数据源
```
访问: http://127.0.0.1:5183/data-sources

步骤:
1. 点击 "添加数据源" 按钮
2. 填写表单:
   - 名称: test_jira
   - Base URL: http://localhost:8888
   - Email: test@example.com
   - Token: mock-token
   - Project Key: SSD
3. 点击 "创建数据源"

预期结果:
- 模态框关闭
- 列表中显示新的 Jira 数据源
- 显示 "Enabled" 状态
```

#### 2. 添加 Confluence 数据源
```
步骤:
1. 点击 "添加数据源" 按钮
2. 选择 Confluence 类型
3. 填写表单:
   - 名称: test_confluence
   - Base URL: http://localhost:8888
   - Token: mock-token
   - Space Key: TECH
4. 点击 "创建数据源"

预期结果:
- Confluence 数据源添加成功
- 显示在 "Confluence 数据源" 分组中
```

#### 3. 删除数据源
```
步骤:
1. 找到要删除的数据源
2. 点击 "删除" 按钮
3. 点击 "确认删除"

预期结果:
- 数据源从列表中移除
- 显示加载动画
- 删除成功后列表自动刷新
```

#### 4. 表单验证
```
步骤:
1. 点击 "添加数据源"
2. 不填写任何字段
3. 点击 "创建数据源"

预期结果:
- 显示验证错误
- "名称不能为空"
- "URL 不能为空"
- "Token 不能为空"
```

#### 5. 空状态
```
步骤:
1. 删除所有数据源
2. 查看页面

预期结果:
- 显示空状态提示
- "暂无 Jira 数据源"
- 显示 "添加 Jira" 快速按钮
```

## 技术实现

### 使用的技术栈
- **React Query** - 数据获取和缓存
- **Zod** - 类型验证
- **Lucide React** - 图标库
- **CSS Modules** - 样式隔离

### 关键代码片段

#### 数据获取
```typescript
const sources = useQuery({
  queryKey: ['sources', workspaceDir],
  queryFn: () => apiJson(`/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`, sourcesResponseSchema),
  enabled: Boolean(workspaceDir),
});
```

#### 删除操作
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

#### 表单验证
```typescript
const newErrors: Record<string, string> = {};

if (!formData.name.trim()) {
  newErrors.name = '名称不能为空';
}
if (!formData.base_url.trim()) {
  newErrors.base_url = 'URL 不能为空';
}
if (!formData.token.trim()) {
  newErrors.token = 'Token 不能为空';
}
```

## 改进对比

| 方面 | 原设计 | 新设计 |
|------|--------|--------|
| 视觉风格 | 黑色按钮，不一致 | 蓝色主题，统一 |
| 数据展示 | 无列表 | 分组卡片列表 |
| 状态反馈 | 无 | 加载/错误/成功 |
| 表单验证 | 基础 | 完整验证+帮助文本 |
| 删除确认 | 无 | 两步确认 |
| 空状态 | 无 | 友好提示+快速操作 |
| 响应式 | 未优化 | 完全响应式 |

## 文件清单

修改的文件：
- `apps/portal_web/src/DataSourcesPage.tsx` - 完全重写
- `apps/portal_web/src/configuration.css` - 添加样式

相关文件：
- `apps/portal_web/src/main.tsx` - 路由配置
- `apps/portal_runner/server.py` - DELETE 端点
- `apps/portal_runner/product_api.py` - 删除函数

## 访问地址

- **数据源页面**: http://127.0.0.1:5183/data-sources
- **配置页面**: http://127.0.0.1:5183/configuration
- **Mock Server**: http://localhost:8888

## 总结

新设计完全解决了原页面的所有问题：

✅ **视觉一致性** - 与其他页面风格统一
✅ **功能完整性** - 列表、添加、删除、验证全部实现
✅ **用户体验** - 清晰的反馈和友好的交互
✅ **可测试性** - 使用 Mock Server 可以完整测试所有功能

页面现在可以投入使用了！
