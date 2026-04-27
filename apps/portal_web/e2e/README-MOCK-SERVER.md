# Mock Server for E2E Testing

## 概述

为 Jira 和 Confluence 集成测试提供模拟 API 服务器，避免依赖真实的外部服务。

## 功能

### Mock Jira Server (端口 8797)

提供以下 API 端点：

- `GET /rest/api/3/myself` - 获取当前用户信息
- `GET /rest/api/3/search` - 搜索 Jira issues (支持 JQL)
- `GET /rest/api/3/project` - 获取项目列表

### Mock Confluence Server (端口 8798)

提供以下 API 端点：

- `GET /rest/api/user/current` - 获取当前用户信息
- `GET /rest/api/content` - 获取页面内容 (支持 spaceKey 参数)
- `GET /rest/api/space` - 获取空间列表

## 使用方法

### 1. 安装依赖

```bash
cd apps/portal_web
npm install express cors @types/express @types/cors --save-dev
```

### 2. 启动模拟服务器

```bash
# 使用 ts-node 直接运行
npx ts-node e2e/mock-server.ts

# 或者添加到 package.json scripts
npm run mock-server
```

### 3. 在测试中使用

```typescript
// 测试配置
const mockJiraUrl = 'http://localhost:8797';
const mockConfluenceUrl = 'http://localhost:8798';
const testEmail = 'test@example.com';
const testToken = 'mock-api-token-12345';

// 在测试中使用这些 URL
await page.locator('input[placeholder*="Jira URL"]').fill(mockJiraUrl);
```

## 运行完整测试流程

### 方式 1: 手动启动

```bash
# Terminal 1: 启动模拟服务器
cd apps/portal_web
npx ts-node e2e/mock-server.ts

# Terminal 2: 启动前端
npm run dev

# Terminal 3: 运行测试
npx playwright test
```

### 方式 2: 使用 package.json scripts

在 `package.json` 中添加：

```json
{
  "scripts": {
    "mock-server": "ts-node e2e/mock-server.ts",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:full": "concurrently \"npm run mock-server\" \"npm run dev\" \"npm run test:e2e\""
  }
}
```

然后运行：

```bash
npm run test:e2e:full
```

## Mock 数据

### Jira Issues

返回 2 个模拟 issue：

- **TEST-1**: "Mock Jira Issue 1" (In Progress, High Priority)
- **TEST-2**: "Mock Jira Issue 2" (To Do, Medium Priority)

### Confluence Pages

返回 2 个模拟页面：

- **Page 1**: "Mock Confluence Page 1"
- **Page 2**: "Mock Confluence Page 2"

## 扩展 Mock 数据

编辑 `mock-server.ts` 文件，修改返回的 JSON 数据：

```typescript
// 添加更多 Jira issues
jiraApp.get('/rest/api/3/search', (req, res) => {
  res.json({
    issues: [
      // 添加更多 issues...
    ]
  });
});

// 添加更多 Confluence 页面
confluenceApp.get('/rest/api/content', (req, res) => {
  res.json({
    results: [
      // 添加更多页面...
    ]
  });
});
```

## 故障排除

### 端口已被占用

如果端口 8797 或 8798 已被占用，修改 `mock-server.ts` 中的端口号：

```typescript
const JIRA_PORT = 8797; // 改为其他端口
const CONFLUENCE_PORT = 8798; // 改为其他端口
```

### 服务器未响应

检查服务器是否正在运行：

```bash
# Windows
netstat -ano | findstr "8797"
netstat -ano | findstr "8798"

# Linux/Mac
lsof -i :8797
lsof -i :8798
```

### CORS 错误

模拟服务器已启用 CORS，如果仍有问题，检查浏览器控制台错误信息。

## 最佳实践

1. **测试前启动** - 确保在运行测试前启动模拟服务器
2. **独立进程** - 在单独的终端窗口运行模拟服务器
3. **清理资源** - 测试完成后使用 Ctrl+C 停止服务器
4. **版本控制** - 将 mock-server.ts 纳入版本控制，团队共享

## 与真实 API 的差异

Mock 服务器提供简化的响应，不包括：

- 认证验证（接受任何 token）
- 分页逻辑
- 错误场景模拟
- 完整的字段集

如需测试这些场景，需要扩展 mock 服务器或使用真实 API。
