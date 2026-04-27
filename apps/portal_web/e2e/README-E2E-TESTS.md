# E2E 测试运行指南

## 📋 测试文件概览

### 1. `sidebar-navigation.spec.ts` - 侧边栏导航测试
测试所有侧边栏入口的导航功能，验证每个页面是否正确加载。

**测试用例**：
- ✅ 显示所有侧边栏链接
- ✅ 导航到 Analyze 页面
- ✅ 导航到 Search 页面
- ✅ 导航到 Chat 页面
- ✅ 导航到 Data Sources 页面
- ✅ 导航到 Retrieval Debug 页面
- ✅ 导航到 Strategy Comparison 页面
- ✅ 导航到 Profiles 页面
- ✅ 导航到 Runs 页面
- ✅ 高亮显示当前激活的链接
- ✅ 顺序导航多个页面
- ✅ 跨页面保持 Workspace 选择

### 2. `complete-flow.spec.ts` - 完整业务流程测试
测试从数据源添加到检索的完整端到端流程。

**主要流程**：
1. 添加 Jira 数据源
2. 添加 Confluence 数据源
3. 验证数据源状态
4. 构建检索索引
5. 执行搜索查询
6. 验证搜索结果
7. 测试搜索过滤器
8. 验证导航

**额外流程测试**：
- Data Sources → Retrieval Debug
- Data Sources → Strategy Comparison
- Search → Analyze → Runs

### 3. `data-source-setup.integration.spec.ts` - 数据源设置测试
基础数据源设置和管理功能测试。

### 4. `jira-confluence-full-flow.integration.spec.ts` - Jira/Confluence 集成测试
完整的 Jira 和 Confluence 数据源集成流程测试。

---

## 🚀 运行测试

### 前置条件

1. **启动 Mock Server**（必需）
```bash
# Terminal 1: 启动 Mock Server
cd apps/portal_web
npm run mock-server
```

2. **启动前端应用**（必需）
```bash
# Terminal 2: 启动前端
npm run dev
```

3. **确保后端服务运行**（如果需要真实 API）

---

## 📝 运行命令

### 运行所有测试
```bash
# Terminal 3: 运行所有 E2E 测试
npm run test:e2e
```

### 运行特定测试文件

```bash
# 侧边栏导航测试
npx playwright test sidebar-navigation.spec.ts

# 完整流程测试
npx playwright test complete-flow.spec.ts

# 数据源设置测试
npx playwright test data-source-setup.integration.spec.ts

# Jira/Confluence 集成测试
npx playwright test jira-confluence-full-flow.integration.spec.ts
```

### 运行特定测试用例

```bash
# 只运行侧边栏链接显示测试
npx playwright test sidebar-navigation.spec.ts -g "should display all sidebar navigation links"

# 只运行完整 E2E 流程
npx playwright test complete-flow.spec.ts -g "Complete Flow: Add Data Sources"

# 只运行导航到 Data Sources 的测试
npx playwright test sidebar-navigation.spec.ts -g "should navigate to Data Sources page"
```

---

## 🎯 调试模式

### UI 模式（推荐）
```bash
# 可视化测试执行，逐步调试
npx playwright test sidebar-navigation.spec.ts --ui
npx playwright test complete-flow.spec.ts --ui
```

### Debug 模式
```bash
# 打开 Playwright Inspector
npx playwright test --debug

# Debug 特定测试
npx playwright test sidebar-navigation.spec.ts --debug
```

### 慢速执行
```bash
# 减慢执行速度，便于观察
npx playwright test --slow-mo=1000
```

### 保持浏览器打开
```bash
# 测试完成后不关闭浏览器
npx playwright test --headed
```

---

## 📊 生成测试报告

### HTML 报告
```bash
# 生成并查看 HTML 报告
npx playwright test --reporter=html
npx playwright show-report
```

### 列表报告
```bash
# 在终端显示详细列表
npx playwright test --reporter=list
```

### JSON 报告
```bash
# 生成 JSON 格式报告
npx playwright test --reporter=json
```

---

## 🔍 测试覆盖的功能

### 侧边栏导航
- ✅ 所有 15 个侧边栏入口
- ✅ 页面加载验证
- ✅ 激活状态高亮
- ✅ Workspace 持久化
- ✅ 顺序导航

### 数据源管理
- ✅ 添加 Jira 数据源
- ✅ 添加 Confluence 数据源
- ✅ 表单验证
- ✅ Toast 通知
- ✅ 数据源列表显示
- ✅ 搜索和过滤
- ✅ 删除确认

### 检索功能
- ✅ 构建索引
- ✅ 执行搜索
- ✅ 搜索结果显示
- ✅ 文档类型过滤
- ✅ 结果详情查看

### UI/UX
- ✅ 加载状态
- ✅ 错误处理
- ✅ 成功提示
- ✅ 空状态显示
- ✅ 响应式布局

---

## 🐛 故障排除

### Mock Server 未运行
**错误**: 连接被拒绝或超时

**解决方案**:
```bash
# 检查 Mock Server 是否运行
netstat -ano | findstr "8797"
netstat -ano | findstr "8798"

# 重新启动 Mock Server
npm run mock-server
```

### 前端未启动
**错误**: `ERR_CONNECTION_REFUSED` 或 `net::ERR_CONNECTION_REFUSED`

**解决方案**:
```bash
# 检查前端是否运行在 5173 端口
netstat -ano | findstr "5173"

# 启动前端
npm run dev
```

### 测试超时
**错误**: `Test timeout of 30000ms exceeded`

**解决方案**:
```bash
# 增加超时时间
npx playwright test --timeout=60000

# 或在测试文件中设置
test.setTimeout(60000);
```

### 元素未找到
**错误**: `locator.click: Target closed` 或 `Element not found`

**解决方案**:
- 使用 `--headed` 模式查看实际页面
- 检查选择器是否正确
- 增加等待时间

### 端口冲突
**错误**: `EADDRINUSE: address already in use`

**解决方案**:
```bash
# Windows: 查找并终止占用端口的进程
netstat -ano | findstr "8797"
taskkill /PID <PID> /F

# 或修改 mock-server.ts 中的端口号
```

---

## 📸 截图和视频

### 自动截图
测试失败时自动生成截图，保存在 `test-results/` 目录。

### 手动截图
```typescript
// 在测试中添加
await page.screenshot({ path: 'screenshot.png' });
await page.screenshot({ path: 'fullpage.png', fullPage: true });
```

### 录制视频
```bash
# 启用视频录制
npx playwright test --video=on

# 只在失败时录制
npx playwright test --video=retain-on-failure
```

---

## 🎨 测试最佳实践

### 1. 使用 data-testid
```typescript
// 推荐
await page.locator('[data-testid="search-input"]').fill('test');

// 避免
await page.locator('input').nth(3).fill('test');
```

### 2. 等待网络空闲
```typescript
await page.waitForLoadState('networkidle');
```

### 3. 使用明确的断言
```typescript
// 推荐
await expect(heading).toBeVisible({ timeout: 5000 });

// 避免
await page.waitForTimeout(5000);
```

### 4. 清理测试数据
```typescript
test.afterEach(async ({ page }) => {
  // 清理创建的数据源
});
```

---

## 📈 持续集成

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
      
      - name: Start Mock Server
        run: npm run mock-server &
      
      - name: Start Frontend
        run: npm run dev &
      
      - name: Wait for services
        run: npx wait-on http://localhost:5173 http://localhost:8797
      
      - name: Run E2E tests
        run: npm run test:e2e
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

---

## 📚 相关文档

- [Playwright 官方文档](https://playwright.dev/)
- [Mock Server 使用指南](./README-MOCK-SERVER.md)
- [Jira/Confluence 测试文档](./README-JIRA-CONFLUENCE-TESTS.md)
- [问题分析和解决方案](./ISSUES-AND-SOLUTIONS.md)

---

## ✅ 测试检查清单

运行测试前确认：

- [ ] Mock Server 正在运行（端口 8797, 8798）
- [ ] 前端应用正在运行（端口 5173）
- [ ] 后端服务正在运行（如需要）
- [ ] 已安装所有依赖 (`npm install`)
- [ ] 已安装 Playwright 浏览器 (`npx playwright install`)

---

## 🎯 快速开始

```bash
# 1. 安装依赖
npm install

# 2. 启动 Mock Server（Terminal 1）
npm run mock-server

# 3. 启动前端（Terminal 2）
npm run dev

# 4. 运行测试（Terminal 3）
npm run test:e2e

# 或使用 UI 模式
npm run test:e2e:ui
```

---

## 📞 获取帮助

如果遇到问题：

1. 查看 [故障排除](#-故障排除) 部分
2. 检查 [相关文档](#-相关文档)
3. 使用 `--debug` 模式运行测试
4. 查看测试日志和截图

祝测试顺利！🚀
