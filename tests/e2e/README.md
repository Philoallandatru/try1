# E2E 测试文档

## 概述

本目录包含完整的端到端测试套件，覆盖以下功能模块：

1. **文件数据源管理** - 文档上传、解析和管理
2. **Jira 数据源配置** - Jira 连接、JQL 查询、字段映射
3. **Confluence 数据源配置** - Confluence 连接、空间选择、CQL 查询
4. **Profile 配置管理** - LLM 配置、检索设置、提示词模板
5. **Jira 深度分析** - 问题分析、关联分析、AI 洞察

## 测试文件

### test_full_workflow.spec.ts
基础工作流测试，包括：
- 模型配置
- 文档上传
- 聊天功能
- API 健康检查

### test_data_sources.spec.ts
数据源和分析功能的完整测试套件，包括：
- 文件数据源的上传和解析
- Jira/Confluence 数据源配置
- Profile 配置和管理
- Jira 深度分析工作流

## 前置条件

### 1. 安装依赖

```bash
# 安装 Playwright
npm install --save-dev @playwright/test

# 安装浏览器
npx playwright install
```

### 2. 启动服务

```bash
# 终端 1: 启动后端服务
cd apps/portal_runner
python -m apps.portal_runner.server --host 0.0.0.0 --port 8787

# 终端 2: 启动前端开发服务器
cd apps/portal_web
npm run dev
```

### 3. 准备测试数据

确保以下测试文件存在：
- `tests/fixtures/test_document.pdf` - 测试 PDF 文档

### 4. 配置测试环境变量（可选）

创建 `.env.test` 文件：

```env
# Jira 配置
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=test@example.com
JIRA_API_TOKEN=your-test-token

# Confluence 配置
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_EMAIL=test@example.com
CONFLUENCE_API_TOKEN=your-test-token

# LLM 配置
OPENAI_API_KEY=sk-test-key
LM_STUDIO_URL=http://localhost:1234
```

## 运行测试

### 运行所有测试

```bash
npx playwright test
```

### 运行特定测试文件

```bash
# 运行基础工作流测试
npx playwright test test_full_workflow.spec.ts

# 运行数据源测试
npx playwright test test_data_sources.spec.ts
```

### 运行特定测试套件

```bash
# 只运行文件数据源测试
npx playwright test --grep "File Data Source"

# 只运行 Jira 配置测试
npx playwright test --grep "Jira Data Source Configuration"

# 只运行 Profile 配置测试
npx playwright test --grep "Profile Configuration"

# 只运行深度分析测试
npx playwright test --grep "Jira Deep Analysis"
```

### 调试模式

```bash
# 以调试模式运行（打开浏览器）
npx playwright test --debug

# 以 headed 模式运行（看到浏览器操作）
npx playwright test --headed

# 运行特定测试并调试
npx playwright test --grep "should perform deep analysis" --debug
```

### UI 模式

```bash
# 使用 Playwright UI 模式
npx playwright test --ui
```

## 测试覆盖范围

### 文件数据源测试

- ✅ PDF 文档上传
- ✅ 文档解析结果展示
- ✅ 按类型筛选文档
- ✅ 文档内容块展示（文本、表格、图片）

### Jira 数据源测试

- ✅ Jira 连接配置
- ✅ 连接测试
- ✅ JQL 查询配置和验证
- ✅ JQL 结果预览
- ✅ 自定义字段映射

### Confluence 数据源测试

- ✅ Confluence 连接配置
- ✅ 空间选择
- ✅ 页面选择（特定页面、标签、整个空间）
- ✅ CQL 查询配置和验证
- ✅ CQL 结果预览

### Profile 配置测试

- ✅ 创建新 Profile
- ✅ 编辑现有 Profile
- ✅ LLM 设置配置（提供商、模型、温度、token 限制）
- ✅ 检索设置配置（策略、top_k、相似度阈值、重排序）
- ✅ 提示词模板配置（分析、总结、建议）
- ✅ 设置默认 Profile
- ✅ 复制 Profile
- ✅ 验证 Profile 配置
- ✅ 删除 Profile
- ✅ 导出/导入 Profile

### Jira 深度分析测试

- ✅ 基础问题分析
- ✅ 关联问题分析（子任务、链接问题）
- ✅ 多层级深度分析
- ✅ AI 洞察生成（摘要、建议、风险评估）
- ✅ 分析结果导出（PDF）
- ✅ 错误处理和重试

### 完整工作流测试

- ✅ 端到端工作流：配置 → 上传 → 分析 → 导出
- ✅ 多数据源集成分析
- ✅ API 健康检查

## 测试数据

### 测试 Jira Issue

测试使用以下 Jira issue key：
- `TEST-123` - 标准测试问题
- `INVALID-999999` - 用于错误处理测试

### 测试文档

- `tests/fixtures/test_document.pdf` - 包含文本、表格和图片的测试 PDF

### 测试 Profile

测试会创建以下 profile：
- `test-profile` - 基础测试配置
- `test-profile-copy` - 复制的配置

## 预期结果

### 成功场景

所有测试应该通过，除非：
1. Jira/Confluence 未配置（会显示配置错误）
2. LM Studio 未运行（AI 分析测试会跳过）
3. 网络连接问题

### 失败场景测试

以下测试专门测试错误处理：
- 无效的 Jira issue key
- 无效的 JQL/CQL 查询
- API 连接失败
- 文件上传失败

## 测试报告

测试完成后，报告会生成在：
- `playwright-report/` - HTML 报告
- `test-results/` - 测试结果和截图

查看报告：

```bash
npx playwright show-report
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Start backend
        run: |
          python -m apps.portal_runner.server &
          sleep 5
      - name: Start frontend
        run: |
          cd apps/portal_web
          npm run dev &
          sleep 5
      - name: Run tests
        run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## 故障排查

### 常见问题

1. **测试超时**
   - 增加超时时间：`timeout: 60000`
   - 检查服务是否正常运行

2. **元素未找到**
   - 检查选择器是否正确
   - 使用 `--debug` 模式查看页面状态

3. **API 调用失败**
   - 检查后端服务是否运行
   - 查看 `backend.log` 日志

4. **文件上传失败**
   - 确认测试文件存在
   - 检查文件路径是否正确

### 调试技巧

```bash
# 生成测试代码
npx playwright codegen http://localhost:5173

# 查看测试追踪
npx playwright show-trace trace.zip

# 截图调试
await page.screenshot({ path: 'debug.png' });

# 打印页面内容
console.log(await page.content());
```

## 最佳实践

1. **使用语义化选择器**
   - 优先使用 `text=` 和 `role=` 选择器
   - 避免使用脆弱的 CSS 选择器

2. **等待策略**
   - 使用 `waitForSelector` 等待元素出现
   - 使用 `waitForLoadState` 等待页面加载

3. **测试隔离**
   - 每个测试应该独立运行
   - 使用 `beforeEach` 重置状态

4. **错误处理**
   - 测试应该包含正面和负面场景
   - 验证错误消息是否正确显示

5. **性能考虑**
   - 使用并行执行加速测试
   - 避免不必要的等待时间

## 维护指南

### 更新测试

当 UI 或 API 变化时：
1. 更新选择器
2. 更新预期结果
3. 更新测试数据
4. 运行测试验证

### 添加新测试

1. 在相应的 `test.describe` 块中添加
2. 遵循现有的命名约定
3. 添加清晰的注释
4. 更新本文档

## 参考资源

- [Playwright 文档](https://playwright.dev/)
- [Playwright 最佳实践](https://playwright.dev/docs/best-practices)
- [测试选择器](https://playwright.dev/docs/selectors)
- [调试测试](https://playwright.dev/docs/debug)
