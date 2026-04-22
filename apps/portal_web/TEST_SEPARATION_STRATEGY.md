# 测试分离策略

**实施日期：** 2026-04-22  
**影响测试数：** 3 个集成测试

## 问题描述

3 个测试失败因为依赖后端服务：
- `diagnose-frontend.spec.ts` - 手动检查 API 响应
- `test-api-direct.spec.ts` - 直接测试 API 端点
- `analyze-real-backend.spec.ts` - 测试后端集成

**错误信息：**
```
apiRequestContext.get: connect ECONNREFUSED ::1:8000
```

## 解决方案

### 1. 测试分类

将测试分为两类：

#### E2E 测试（默认运行）
- 不依赖后端服务
- 使用 mock 数据或前端状态
- 快速执行
- 适合 CI/CD

#### 集成测试（需要后端）
- 依赖后端 API 运行
- 测试真实的前后端交互
- 较慢执行
- 需要手动运行

### 2. 文件命名约定

**E2E 测试：** `*.spec.ts`
```
e2e/analyze-page.spec.ts
e2e/analysis.spec.ts
e2e/analyze-demo-workspace.spec.ts
```

**集成测试：** `*.integration.spec.ts`
```
e2e/diagnose-frontend.integration.spec.ts
e2e/test-api-direct.integration.spec.ts
e2e/analyze-real-backend.integration.spec.ts
```

### 3. Playwright 配置

**文件：** `playwright.config.ts`

```typescript
projects: [
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'] },
    testIgnore: '**/e2e/*integration*.spec.ts', // 跳过集成测试
  },
  {
    name: 'integration',
    use: { ...devices['Desktop Chrome'] },
    testMatch: '**/e2e/*integration*.spec.ts', // 只运行集成测试
  },
]
```

### 4. NPM 脚本

**文件：** `package.json`

```json
{
  "scripts": {
    "test:e2e": "playwright test",                    // 运行所有测试
    "test:e2e:ui": "playwright test --ui",            // UI 模式
    "test:e2e:unit": "playwright test --project=chromium",      // 只运行 E2E 测试
    "test:e2e:integration": "playwright test --project=integration"  // 只运行集成测试
  }
}
```

## 使用方法

### 开发时（默认）

```bash
npm run test:e2e:unit
```

**运行：** 所有 E2E 测试（不需要后端）  
**跳过：** 集成测试

### 集成测试（需要后端运行）

```bash
# 1. 启动后端服务
cd ../../apps/runner
python -m uvicorn main:app --reload --port 8000

# 2. 运行集成测试
cd ../portal_web
npm run test:e2e:integration
```

**运行：** 只有集成测试  
**要求：** 后端服务在 localhost:8000 运行

### 运行所有测试

```bash
npm run test:e2e
```

**运行：** E2E + 集成测试  
**注意：** 集成测试会失败如果后端未运行

### UI 模式

```bash
npm run test:e2e:ui
```

**功能：** 交互式测试界面  
**可以：** 选择运行哪些测试

## 重命名的文件

| 原文件名 | 新文件名 | 原因 |
|---------|---------|------|
| `diagnose-frontend.spec.ts` | `diagnose-frontend.integration.spec.ts` | 直接调用后端 API |
| `test-api-direct.spec.ts` | `test-api-direct.integration.spec.ts` | 测试 API 端点 |
| `analyze-real-backend.spec.ts` | `analyze-real-backend.integration.spec.ts` | 测试后端集成 |

## 优点

### 1. 更快的反馈循环
- E2E 测试不等待后端
- 开发时快速验证前端功能

### 2. 清晰的测试边界
- 明确哪些测试需要后端
- 易于理解测试依赖

### 3. 灵活的 CI/CD
- CI 可以只运行 E2E 测试
- 集成测试可以在专门的环境运行

### 4. 更好的错误诊断
- 测试失败时，清楚是前端还是集成问题

## 未来改进

### 选项 A: API Mock
使用 Playwright 的 `route.fulfill()` mock API 响应：

```typescript
await page.route('**/api/workspaces', route => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({
      workspaces: [
        { name: 'demo', workspace_dir: '/path/to/demo' }
      ]
    })
  });
});
```

**优点：**
- 所有测试都可以离线运行
- 更快的测试执行
- 可控的测试数据

### 选项 B: MSW (Mock Service Worker)
使用 MSW 提供统一的 API mock：

```typescript
import { setupServer } from 'msw/node';
import { rest } from 'msw';

const server = setupServer(
  rest.get('/api/workspaces', (req, res, ctx) => {
    return res(ctx.json({ workspaces: [...] }));
  })
);
```

**优点：**
- 更真实的网络行为
- 可以在测试和开发中共享
- 支持复杂的场景

### 选项 C: 测试容器
使用 Docker 容器运行后端：

```yaml
# docker-compose.test.yml
services:
  backend:
    build: ../../apps/runner
    ports:
      - "8000:8000"
```

**优点：**
- 真实的后端环境
- 可以在 CI 中运行
- 测试完整的集成

## 测试统计

**修复前：**
- 总测试：65
- 通过：51 (78.5%)
- 失败：14 (21.5%)

**修复后（预期）：**
- E2E 测试：62
- 通过：59+ (95%+)
- 失败：3- (5%-)
- 集成测试：3（需要后端时运行）

## 相关文件

- `playwright.config.ts` - 添加项目分离
- `package.json` - 添加测试脚本
- `e2e/diagnose-frontend.integration.spec.ts` - 重命名
- `e2e/test-api-direct.integration.spec.ts` - 重命名
- `e2e/analyze-real-backend.integration.spec.ts` - 重命名
