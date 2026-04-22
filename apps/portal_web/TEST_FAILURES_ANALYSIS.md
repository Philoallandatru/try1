# E2E 测试失败分析

**测试运行时间：** 2026-04-22  
**总测试数：** 65  
**通过：** 51 (78.5%)  
**失败：** 14 (21.5%)

## 失败分类

### 类别 1: 后端服务未运行 (3 个测试)

**根本原因：** 测试尝试连接 `http://localhost:8000`，但后端服务未启动

**失败测试：**
1. `analyze-real-backend.spec.ts:243` - should test analyze-jira endpoint with mock data
2. `diagnose-frontend.spec.ts:93` - manually check API responses
3. `test-api-direct.spec.ts:4` - should fetch workspaces via API

**错误信息：**
```
apiRequestContext.get: connect ECONNREFUSED ::1:8000
```

**修复策略：**
- **选项 A（推荐）：** 将这些测试标记为 `@integration`，需要后端运行时才执行
- **选项 B：** 使用 Playwright 的 `route.fulfill()` mock API 响应
- **选项 C：** 使用 MSW (Mock Service Worker) 提供 mock 数据

---

### 类别 2: Workspace 选择器超时 (10 个测试)

**根本原因：** `selectOption({ label: 'demo' })` 超时，无法找到 demo workspace 选项

**失败测试：**
1. `analyze-demo-workspace.spec.ts:19` - should show 4/4 ready with demo workspace
2. `analyze-demo-workspace.spec.ts:37` - should have profiles available
3. `analyze-demo-workspace.spec.ts:54` - should enable Run Analysis button
4. `analyze-demo-workspace.spec.ts:69` - should successfully run analysis on demo data
5. `analyze-demo-workspace.spec.ts:153` - should display error when LLM is not available
6. `analyze-demo-workspace.spec.ts:191` - should navigate to Runs page and see the run
7. `test-markdown-rendering.spec.ts:18` - should render markdown in Runs page
8. `test-markdown-rendering.spec.ts:75` - should check all section tabs for markdown rendering
9. `test-chinese-output.spec.ts:4` - should generate Chinese analysis with qwen-9b model
10. `verify-chinese-output.spec.ts:4` - should display Chinese analysis with proper markdown rendering

**错误信息：**
```
Error: locator.selectOption: Test timeout of 1860000ms exceeded.
- did not find some options
```

**可能原因：**
1. Demo workspace 未正确加载到 localStorage 或 API
2. 选择器定位不准确（`page.locator('select').first()`）
3. 页面加载时机问题（React 组件未完全渲染）
4. Demo 数据初始化失败

**修复策略：**
1. 检查 demo workspace 是否正确初始化
2. 改进选择器（使用 `data-testid` 或更具体的选择器）
3. 添加显式等待（`waitForLoadState`, `waitForSelector`）
4. 检查 workspace 下拉框的数据来源

---

### 类别 3: 元素可见性问题 (1 个测试)

**失败测试：**
1. `analyze-page.spec.ts:153` - should display result view after successful analysis

**错误信息：**
```
expect(locator).toBeVisible() failed
Locator: locator('.result-surface')
Timeout: 5000ms
Error: element(s) not found
```

**可能原因：**
1. 分析未成功完成，结果视图未渲染
2. CSS 类名不匹配
3. 异步加载未完成

**修复策略：**
1. 增加等待时间或使用更智能的等待
2. 检查分析流程是否正常完成
3. 验证 `.result-surface` 类名是否正确

---

## 优先级修复顺序

### 🔴 高优先级（影响 10 个测试）
**修复 Workspace 选择器问题**
- 影响最大（10/14 失败测试）
- 阻塞所有 demo workspace 相关测试
- 需要检查 demo 数据初始化逻辑

### 🟡 中优先级（影响 3 个测试）
**处理后端依赖测试**
- 添加集成测试标记
- 或实现 API mock

### 🟢 低优先级（影响 1 个测试）
**修复结果视图可见性**
- 单个测试问题
- 可能是测试编写问题

---

## 下一步行动

1. **立即执行：** 调查 workspace 选择器问题
   - 检查 `apps/portal_web/e2e/analyze-demo-workspace.spec.ts:14`
   - 查看 demo workspace 初始化代码
   - 改进选择器策略

2. **短期：** 标记集成测试
   - 为需要后端的测试添加 `@integration` 标签
   - 更新 CI 配置分离单元测试和集成测试

3. **中期：** 添加 API mock
   - 使用 Playwright route mock 或 MSW
   - 让测试可以独立运行

---

## 测试改进建议

1. **使用 data-testid**
   ```tsx
   <select data-testid="workspace-selector">
   ```
   ```ts
   await page.locator('[data-testid="workspace-selector"]').selectOption('demo');
   ```

2. **添加显式等待**
   ```ts
   await page.waitForLoadState('networkidle');
   await page.waitForSelector('[data-testid="workspace-selector"]');
   ```

3. **改进错误信息**
   ```ts
   const options = await workspaceSelect.locator('option').allTextContents();
   console.log('Available workspaces:', options);
   ```

4. **分离测试类型**
   - Unit tests: 不依赖外部服务
   - Integration tests: 需要后端运行
   - E2E tests: 完整用户流程
