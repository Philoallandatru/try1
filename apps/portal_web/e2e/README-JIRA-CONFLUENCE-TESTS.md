# Jira/Confluence Integration E2E Tests

## 概述

这些测试模拟从零开始配置和使用 Jira 和 Confluence 数据源的完整流程。

## 测试文件

### 1. `data-source-setup.integration.spec.ts`
基础数据源设置测试，包括：
- 导航到数据源页面
- 添加 Jira 数据源
- 添加 Confluence 数据源
- 验证数据源状态
- 测试搜索和过滤功能
- 测试删除功能

### 2. `jira-confluence-full-flow.integration.spec.ts`
完整的集成流程测试，包括 8 个步骤：
- Step 1: 验证数据源页面 UI
- Step 2: 添加 Jira 源（完整配置）
- Step 3: 添加 Confluence 源（完整配置）
- Step 4: 验证两个数据源
- Step 5: 测试按类型过滤
- Step 6: 测试搜索功能
- Step 7: 验证卡片交互
- Step 8: 完整流程总结

## 前置条件

### 1. 启动后端服务
```bash
# 在项目根目录
cd apps/portal_runner
python -m uvicorn server:app --reload --port 8000
```

### 2. 启动前端开发服务器
```bash
# 在 portal_web 目录
cd apps/portal_web
npm run dev
```

### 3. （可选）启动模拟 Jira/Confluence 服务器
如果需要真实的 API 交互，可以启动模拟服务器：

```bash
# 模拟 Jira 服务器 (端口 8797)
# 模拟 Confluence 服务器 (端口 8798)
```

## 运行测试

### 运行所有集成测试
```bash
npx playwright test jira-confluence-full-flow.integration.spec.ts
```

### 运行特定步骤
```bash
# 只运行 Step 1
npx playwright test jira-confluence-full-flow.integration.spec.ts -g "Step 1"

# 只运行 Step 2 (添加 Jira)
npx playwright test jira-confluence-full-flow.integration.spec.ts -g "Step 2"

# 只运行 Step 3 (添加 Confluence)
npx playwright test jira-confluence-full-flow.integration.spec.ts -g "Step 3"
```

### 运行基础设置测试
```bash
npx playwright test data-source-setup.integration.spec.ts
```

### 使用 UI 模式运行（推荐用于调试）
```bash
npx playwright test jira-confluence-full-flow.integration.spec.ts --ui
```

### 生成详细报告
```bash
npx playwright test jira-confluence-full-flow.integration.spec.ts --reporter=html
npx playwright show-report
```

## 测试配置

### 模拟服务器 URL
测试使用以下默认 URL：
- Jira: `http://localhost:8797`
- Confluence: `http://localhost:8798`

### 测试凭据
- Email: `test@example.com`
- API Token: `mock-api-token-12345`
- Runner Token: `test-token-123`

### JQL 查询示例
```
project = SSD AND status != Done
```

### Confluence 空间键示例
```
SSDENG
```

## 测试流程详解

### Step 1: 验证 UI
- 检查页面标题"数据源管理"
- 验证所有标签页（全部、文件、Jira、Confluence）
- 确认"添加数据源"按钮存在

### Step 2: 添加 Jira 源
1. 点击"添加数据源"按钮
2. 选择 Jira 类型
3. 填写配置：
   - Jira URL
   - 邮箱
   - API Token
   - JQL 查询（可选）
4. 提交表单
5. 验证 Jira 源出现在列表中

### Step 3: 添加 Confluence 源
1. 点击"添加数据源"按钮
2. 选择 Confluence 类型
3. 填写配置：
   - Confluence URL
   - 邮箱
   - API Token
   - 空间键（可选）
4. 提交表单
5. 验证 Confluence 源出现在列表中

### Step 4-8: 验证和测试
- 检查数据源状态
- 测试过滤功能
- 测试搜索功能
- 验证交互元素
- 生成测试报告

## 截图和报告

测试会自动生成以下截图：
- `test-results/jira-config-filled.png` - Jira 配置填写完成
- `test-results/confluence-config-filled.png` - Confluence 配置填写完成
- `test-results/source-card.png` - 数据源卡片
- `test-results/final-data-sources.png` - 最终状态（全页面）

## 调试技巧

### 1. 使用 UI 模式
```bash
npx playwright test --ui
```
可以逐步执行测试，查看每一步的状态。

### 2. 使用 Debug 模式
```bash
npx playwright test --debug
```
会打开浏览器开发者工具，可以设置断点。

### 3. 查看测试日志
测试会输出详细的控制台日志，包括：
- 每个步骤的执行状态
- 找到的数据源数量
- 数据源的详细信息（名称、类型、状态、项目数）

### 4. 慢速执行
```bash
npx playwright test --slow-mo=1000
```
每个操作之间延迟 1 秒，便于观察。

### 5. 保持浏览器打开
```bash
npx playwright test --headed
```
测试完成后不关闭浏览器。

## 常见问题

### Q: 测试找不到元素
A: 检查以下几点：
1. 前端服务器是否正常运行（http://localhost:5173）
2. 后端服务器是否正常运行（http://localhost:8000）
3. 元素选择器是否与最新的 UI 匹配

### Q: 模态框没有打开
A: 增加等待时间：
```typescript
await page.waitForTimeout(1000);
```

### Q: 数据源没有出现在列表中
A: 检查：
1. 后端 API 是否正常响应
2. 数据源是否成功创建
3. 页面是否需要刷新

### Q: 测试超时
A: 增加超时时间：
```typescript
await expect(element).toBeVisible({ timeout: 10000 });
```

## 扩展测试

### 添加新的测试场景
1. 复制现有测试文件
2. 修改测试名称和描述
3. 添加新的测试步骤
4. 运行并验证

### 测试数据源同步
```typescript
test('should trigger source sync', async ({ page }) => {
  // 找到数据源卡片
  const sourceCard = page.locator('.bg-white.rounded-xl').first();
  
  // 点击同步按钮（如果有）
  const syncButton = sourceCard.locator('button:has-text("同步")');
  if (await syncButton.isVisible()) {
    await syncButton.click();
    await page.waitForTimeout(2000);
    
    // 验证同步状态
    const status = await sourceCard.locator('span.rounded-full').textContent();
    console.log('Sync status:', status);
  }
});
```

### 测试文档解析
```typescript
test('should verify parsed documents', async ({ page }) => {
  // 导航到搜索页面
  await page.goto('http://localhost:5173/search');
  
  // 执行搜索
  const searchInput = page.locator('input[type="search"]');
  await searchInput.fill('test query');
  await searchInput.press('Enter');
  
  // 验证结果
  await page.waitForTimeout(2000);
  const results = page.locator('.search-result');
  const count = await results.count();
  console.log(`Found ${count} search results`);
});
```

## 最佳实践

1. **使用有意义的测试名称**
   ```typescript
   test('Step 2: Add Jira source with complete configuration', ...)
   ```

2. **添加详细的日志**
   ```typescript
   console.log('✓ Jira source added successfully');
   ```

3. **使用合适的等待策略**
   ```typescript
   await page.waitForLoadState('networkidle');
   await expect(element).toBeVisible({ timeout: 5000 });
   ```

4. **截图关键步骤**
   ```typescript
   await page.screenshot({ path: 'test-results/step-name.png' });
   ```

5. **验证多个方面**
   ```typescript
   // 不仅检查元素存在，还要验证内容
   const name = await element.textContent();
   expect(name).toContain('expected text');
   ```

## 持续集成

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
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Run tests
        run: npx playwright test jira-confluence-full-flow.integration.spec.ts
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## 贡献指南

欢迎贡献新的测试场景！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支
3. 添加测试
4. 确保所有测试通过
5. 提交 Pull Request

## 许可证

与主项目相同
