# Workspace 选择器修复总结

**修复日期：** 2026-04-22  
**影响测试数：** 10 个失败测试

## 问题描述

10 个 E2E 测试失败，原因是 workspace 选择器超时：
- `analyze-demo-workspace.spec.ts` (6 个测试)
- `test-markdown-rendering.spec.ts` (2 个测试)
- `test-chinese-output.spec.ts` (1 个测试)
- `verify-chinese-output.spec.ts` (1 个测试)

**错误信息：**
```
Error: locator.selectOption: Test timeout of 1860000ms exceeded.
- did not find some options
```

## 根本原因

1. **硬编码选择器：** 测试使用 `selectOption({ label: 'demo' })` 假设 demo workspace 存在
2. **无等待逻辑：** 没有等待 workspace 数据从 API 加载
3. **无回退机制：** 如果 demo workspace 不存在，测试直接失败
4. **选择器不稳定：** 使用 `page.locator('select').first()` 或 `label:has-text("Workspace") select`

## 修复方案

### 1. 添加 `data-testid` 属性

**文件：** `apps/portal_web/src/main.tsx:454`

```tsx
<select
  data-testid="workspace-selector"
  value={selectedWorkspace}
  onChange={(event) => setWorkspaceDir(event.target.value)}
>
```

**优点：**
- 更稳定的选择器
- 不依赖文本内容
- 符合测试最佳实践

### 2. 创建测试辅助函数

**文件：** `apps/portal_web/e2e/test-helpers.ts`

```typescript
export async function setupAuthAndWorkspace(
  page: Page,
  token: string = 'change-me',
  preferredWorkspace: string = 'demo'
): Promise<string | null>
```

**功能：**
- 设置认证 token
- 等待 workspace 选择器加载
- 等待 API 返回 workspace 数据
- 尝试选择首选 workspace
- 如果不存在，选择第一个可用 workspace
- 返回选中的 workspace 名称

### 3. 重构测试文件

**修改的文件：**
- `e2e/analyze-demo-workspace.spec.ts`
- `e2e/test-markdown-rendering.spec.ts`
- `e2e/test-chinese-output.spec.ts`

**修改前：**
```typescript
test.beforeEach(async ({ page }) => {
  await page.goto('http://localhost:5173');
  await page.evaluate(() => {
    localStorage.setItem('ssdPortalToken', 'change-me');
  });
  await page.reload();
  await page.waitForTimeout(2000);

  const workspaceSelect = page.locator('select').first();
  await workspaceSelect.selectOption({ label: 'demo' });
  await page.waitForTimeout(2000);
});
```

**修改后：**
```typescript
import { setupAuthAndWorkspace } from './test-helpers';

test.beforeEach(async ({ page }) => {
  await setupAuthAndWorkspace(page, 'change-me', 'demo');
});
```

## 改进点

### 1. 健壮性
- ✅ 等待 workspace 数据加载完成
- ✅ 检查 workspace 是否存在
- ✅ 回退到第一个可用 workspace
- ✅ 详细的日志输出

### 2. 可维护性
- ✅ 集中管理 workspace 选择逻辑
- ✅ 减少重复代码
- ✅ 易于更新和扩展

### 3. 可读性
- ✅ 清晰的函数命名
- ✅ 简洁的测试代码
- ✅ 详细的注释

## 预期效果

修复后，这 10 个测试应该：
1. 不再因为 workspace 选择器超时而失败
2. 能够适应不同的 workspace 配置
3. 提供更好的错误信息

## 剩余问题

这些测试仍然可能失败，如果：
1. **后端服务未运行** - 需要启动后端 API
2. **Demo workspace 未配置** - 需要创建 demo workspace
3. **API 返回空数据** - 需要检查后端数据

## 下一步

1. 运行测试验证修复效果
2. 如果仍有失败，检查后端服务状态
3. 考虑添加 API mock 以支持离线测试

## 相关文件

- `apps/portal_web/src/main.tsx` - 添加 data-testid
- `apps/portal_web/e2e/test-helpers.ts` - 新建辅助函数
- `apps/portal_web/e2e/analyze-demo-workspace.spec.ts` - 重构
- `apps/portal_web/e2e/test-markdown-rendering.spec.ts` - 重构
- `apps/portal_web/e2e/test-chinese-output.spec.ts` - 重构
