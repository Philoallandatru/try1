# Jira/Confluence 集成测试 - 完成总结

## 📋 已创建的测试文件

### 1. `data-source-setup.integration.spec.ts`
**基础数据源设置测试套件**

包含 8 个测试用例：
- ✅ 导航到数据源页面
- ✅ 添加 Jira 数据源（带模拟服务器）
- ✅ 添加 Confluence 数据源（带模拟服务器）
- ✅ 显示 Jira 和 Confluence 数据源
- ✅ 验证数据源状态和文档数量
- ✅ 测试搜索功能
- ✅ 测试按类型过滤
- ✅ 测试删除功能

**特点**：
- 使用模拟服务器 URL（localhost:8797 和 8798）
- 完整的表单填写流程
- 详细的控制台日志输出
- 验证数据源状态和项目数

### 2. `jira-confluence-full-flow.integration.spec.ts`
**完整的端到端集成流程测试**

包含 8 个步骤测试：
- **Step 1**: 验证数据源页面 UI（标题、标签、按钮）
- **Step 2**: 添加 Jira 源（完整配置 + JQL 查询）
- **Step 3**: 添加 Confluence 源（完整配置 + 空间键）
- **Step 4**: 验证两个数据源并检查状态
- **Step 5**: 测试按类型过滤（全部/Jira/Confluence/文件）
- **Step 6**: 测试搜索功能
- **Step 7**: 验证卡片交互（hover、编辑、删除按钮）
- **Step 8**: 完整流程总结和截图

**特点**：
- 分步骤执行，便于调试
- 自动生成截图（配置填写、卡片、最终状态）
- 详细的日志输出（每个步骤的状态）
- 完整的验证流程

### 3. `README-JIRA-CONFLUENCE-TESTS.md`
**完整的测试文档**

包含：
- 📖 测试概述和文件说明
- 🔧 前置条件（后端、前端、模拟服务器）
- ▶️ 运行测试的各种方式
- 🔍 测试流程详解（8 个步骤）
- 📸 截图和报告说明
- 🐛 调试技巧（UI 模式、Debug 模式、慢速执行）
- ❓ 常见问题和解决方案
- 🚀 扩展测试示例
- 📝 最佳实践
- 🔄 持续集成配置示例

## 🎯 测试覆盖的功能

### UI 交互
- ✅ 页面导航
- ✅ 模态框打开/关闭
- ✅ 表单填写
- ✅ 按钮点击
- ✅ 标签页切换
- ✅ 搜索输入
- ✅ 卡片 hover 效果

### 数据源管理
- ✅ 添加 Jira 数据源
- ✅ 添加 Confluence 数据源
- ✅ 配置 URL 和凭据
- ✅ 设置 JQL 查询
- ✅ 设置空间键
- ✅ 查看数据源列表
- ✅ 过滤数据源
- ✅ 搜索数据源
- ✅ 删除数据源

### 验证检查
- ✅ UI 元素可见性
- ✅ 表单提交成功
- ✅ 数据源状态显示
- ✅ 项目数量显示
- ✅ 最后同步时间
- ✅ 类型标签
- ✅ 操作按钮

## 📝 测试配置

### 模拟服务器
```typescript
const mockJiraUrl = 'http://localhost:8797';
const mockConfluenceUrl = 'http://localhost:8798';
```

### 测试凭据
```typescript
const testEmail = 'test@example.com';
const testToken = 'mock-api-token-12345';
const runnerToken = 'test-token-123';
```

### 示例配置
```typescript
// JQL 查询
'project = SSD AND status != Done'

// Confluence 空间键
'SSDENG'
```

## 🚀 如何运行测试

### 基础运行
```bash
# 运行完整流程测试
npx playwright test jira-confluence-full-flow.integration.spec.ts

# 运行基础设置测试
npx playwright test data-source-setup.integration.spec.ts
```

### 运行特定步骤
```bash
# 只运行 Step 1（验证 UI）
npx playwright test jira-confluence-full-flow.integration.spec.ts -g "Step 1"

# 只运行 Step 2（添加 Jira）
npx playwright test jira-confluence-full-flow.integration.spec.ts -g "Step 2"

# 只运行 Step 3（添加 Confluence）
npx playwright test jira-confluence-full-flow.integration.spec.ts -g "Step 3"
```

### 调试模式
```bash
# UI 模式（推荐）
npx playwright test jira-confluence-full-flow.integration.spec.ts --ui

# Debug 模式
npx playwright test --debug

# 慢速执行
npx playwright test --slow-mo=1000

# 保持浏览器打开
npx playwright test --headed
```

### 生成报告
```bash
# HTML 报告
npx playwright test jira-confluence-full-flow.integration.spec.ts --reporter=html
npx playwright show-report

# 列表报告
npx playwright test --reporter=list
```

## 📸 自动生成的截图

测试会自动生成以下截图到 `test-results/` 目录：

1. **jira-config-filled.png** - Jira 配置表单填写完成
2. **confluence-config-filled.png** - Confluence 配置表单填写完成
3. **source-card.png** - 数据源卡片详情
4. **final-data-sources.png** - 最终数据源列表（全页面）

## 🔍 测试日志示例

```
=== Step 1: Navigate to Data Sources ===
✓ Tab "全部" found
✓ Tab "文件" found
✓ Tab "Jira" found
✓ Tab "Confluence" found
✓ Data Sources page UI verified

=== Step 2: Add Jira Source ===
✓ Add source modal opened
✓ Jira type selected
Filling Jira configuration...
  URL: http://localhost:8797
  Email: test@example.com
  Token: mock-api-t...
  JQL: project = SSD AND status != Done
✓ Form submitted
✓ Modal closed
✓ Jira source added successfully (1 source(s) found)
  Name: Jira Source
  Status: 活跃

=== Step 3: Add Confluence Source ===
✓ Confluence type selected
Filling Confluence configuration...
  URL: http://localhost:8798
  Email: test@example.com
  Token: mock-api-t...
  Space Key: SSDENG
✓ Form submitted
✓ Confluence source added successfully (1 source(s) found)
  Name: Confluence Source
  Status: 活跃

=== Step 8: Flow Summary ===
=== Integration Flow Complete ===
Total data sources: 2
  - Jira sources: 1
  - Confluence sources: 1
✓ All steps completed successfully
```

## 🎨 与样式改进的集成

这些测试完全兼容新的样式改进：

### 使用的选择器
- ✅ `h1:has-text("数据源管理")` - 中文标题
- ✅ `button:has-text("添加数据源")` - 中文按钮
- ✅ `.bg-white.rounded-xl.border` - 新的卡片样式
- ✅ `span.rounded-full` - 新的状态标签样式
- ✅ `button:has-text("编辑")` - 中文编辑按钮

### 验证的样式元素
- ✅ 圆角卡片 (`rounded-xl`)
- ✅ 边框和阴影
- ✅ 彩色图标背景
- ✅ 圆形状态标签
- ✅ Hover 效果
- ✅ 过渡动画

## 🔄 下一步建议

### 1. 添加模拟服务器
创建真实的模拟 Jira/Confluence API 服务器：
```bash
# 使用 json-server 或 express
npm install -D json-server
```

### 2. 测试数据同步
添加测试验证数据源同步功能：
```typescript
test('should sync Jira source', async ({ page }) => {
  // 触发同步
  // 验证同步状态
  // 检查文档数量更新
});
```

### 3. 测试文档解析
验证解析后的文档：
```typescript
test('should parse Jira issues', async ({ page }) => {
  // 导航到搜索页面
  // 搜索 Jira 问题
  // 验证结果
});
```

### 4. 添加错误场景测试
```typescript
test('should handle invalid credentials', async ({ page }) => {
  // 使用错误的凭据
  // 验证错误消息
});

test('should handle network errors', async ({ page }) => {
  // 模拟网络错误
  // 验证错误处理
});
```

### 5. 性能测试
```typescript
test('should load sources quickly', async ({ page }) => {
  const startTime = Date.now();
  await page.goto('http://localhost:5173/data-sources');
  const loadTime = Date.now() - startTime;
  expect(loadTime).toBeLessThan(3000);
});
```

## ✅ 完成清单

- [x] 创建基础数据源设置测试
- [x] 创建完整集成流程测试（8 步骤）
- [x] 添加详细的测试文档
- [x] 配置模拟服务器 URL
- [x] 添加表单填写测试
- [x] 添加 UI 验证测试
- [x] 添加过滤和搜索测试
- [x] 添加截图功能
- [x] 添加详细日志输出
- [x] 兼容新的样式改进
- [x] 提供调试指南
- [x] 提供扩展示例

## 📚 相关文件

```
apps/portal_web/e2e/
├── data-source-setup.integration.spec.ts          # 基础设置测试
├── jira-confluence-full-flow.integration.spec.ts  # 完整流程测试
└── README-JIRA-CONFLUENCE-TESTS.md                # 测试文档

apps/portal_web/src/
├── DataSourcesPage.tsx                            # 数据源页面（已优化样式）
├── StrategyComparisonPage.tsx                     # 策略对比页面（已优化样式）
└── RetrievalDebugPage.tsx                         # 检索调试页面（已优化样式）
```

## 🎉 总结

成功创建了完整的 Jira/Confluence 集成 E2E 测试套件，包括：

1. **2 个测试文件**，共 16 个测试用例
2. **完整的测试文档**，包含使用指南和最佳实践
3. **自动截图功能**，便于验证和调试
4. **详细的日志输出**，便于追踪测试执行
5. **与新样式完全兼容**，使用中文界面和新的 Tailwind 样式

测试覆盖了从零开始配置 Jira 和 Confluence 数据源的完整流程，可以作为回归测试和功能验证的基础。
