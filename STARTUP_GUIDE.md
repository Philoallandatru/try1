# 启动指南

本文档说明如何在本地启动前端和后端服务。

## 前提条件

1. Python 3.12+
2. Node.js 18+
3. 已安装项目依赖

## 安装依赖

### 后端依赖

```powershell
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 安装后端依赖（如果还没安装）
pip install -e ".[portal-runner]"
```

### 前端依赖

```powershell
# 进入前端目录
cd apps/portal_web

# 安装依赖
npm install
```

## 启动方式

### 方式 1：分别启动（推荐用于开发）

**启动后端 API：**

```powershell
# 在项目根目录
.\.venv\Scripts\Activate.ps1

# 启动 FastAPI 后端（默认端口 8787）
python -m apps.portal_runner.server --host 127.0.0.1 --port 8787
```

后端将在 `http://localhost:8787` 启动。

**注意**：默认端口是 8787，前端已配置代理到此端口。如果需要使用其他端口，需要同时修改 `apps/portal_web/vite.config.ts` 中的代理配置。

**启动前端开发服务器：**

```powershell
# 在另一个终端，进入前端目录
cd apps/portal_web

# 启动 Vite 开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动，并自动打开浏览器。

**注意**：前端默认端口是 5173（Vite 默认），会自动代理 `/api` 请求到后端的 8787 端口。

### 方式 2：使用 uvicorn 直接启动后端

```powershell
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 使用 uvicorn 启动（注意：需要指定 app 对象）
uvicorn apps.portal_runner.server:app --host 127.0.0.1 --port 8787 --reload
```

`--reload` 参数会在代码修改时自动重启服务器（开发模式）。

**注意**：使用 uvicorn 直接启动时，需要确保 `server.py` 中导出了 `app` 对象。推荐使用方式 1（`python -m apps.portal_runner.server`）。

## 验证服务

### 检查后端

访问 `http://localhost:8787/docs` 查看 API 文档（Swagger UI）。

### 检查前端

访问 `http://localhost:5173` 应该能看到应用界面。

## 配置

### 后端配置

后端配置文件位于 `.local/portal_runner_config.yaml`（如果不存在会使用默认配置）。

主要配置项：
- `bind_host`: 绑定地址（默认 127.0.0.1）
- `bind_port`: 绑定端口（默认 8787）
- `auth_token`: 认证 token（默认 "change-me"）
- `workspace_root`: 工作空间根目录

### 前端配置

前端通过 Vite 的 proxy 配置连接后端，配置在 `apps/portal_web/vite.config.ts`：

```typescript
server: {
  proxy: {
    '/api': 'http://127.0.0.1:8787',
  }
}
```

**重要**：前端代理配置必须与后端端口一致。如果修改后端端口，需要同步修改此配置。

## 常见问题

### Q: 后端启动失败，提示模块找不到

**A:** 确保已安装 portal-runner 依赖：

```powershell
pip install -e ".[portal-runner]"
```

### Q: 前端无法连接后端

**A:** 检查：
1. 后端是否在 8787 端口运行
2. 前端 proxy 配置是否正确（应该指向 http://127.0.0.1:8787）
3. 浏览器控制台是否有 CORS 错误

### Q: 如何修改端口？

**A:** 
- 后端：使用 `--port` 参数或修改配置文件
- 前端：修改 `vite.config.ts` 中的 `server.port`

### Q: 如何启用热重载？

**A:** 
- 后端：使用 `uvicorn` 的 `--reload` 参数
- 前端：`npm run dev` 默认启用热重载

## 生产部署

### 构建前端

```powershell
cd apps/portal_web
npm run build
```

构建产物在 `apps/portal_web/dist/` 目录。

### 启动生产服务器

```powershell
# 后端（不使用 --reload）
python -m apps.portal_runner.server --host 0.0.0.0 --port 8787

# 或使用 uvicorn
uvicorn apps.portal_runner.server:app --host 0.0.0.0 --port 8787 --workers 4
```

前端静态文件可以通过 nginx 或其他 web 服务器提供。

## 开发工作流

1. 启动后端（终端 1）
2. 启动前端（终端 2）
3. 修改代码，保存后自动重载
4. 在浏览器中测试
5. 运行测试验证功能

## 测试

### 后端测试

```powershell
# 运行所有测试
pytest

# 运行特定测试
pytest apps/portal_runner/test_analysis_api.py
```

### 前端测试

```powershell
cd apps/portal_web

# 单元测试
npm run test

# E2E 测试（需要后端运行）
npm run test:e2e:integration
```

## 相关文档

- [前端 README](apps/portal_web/README.md)
- [API 文档](apps/portal_web/API.md)
- [性能监控](apps/portal_web/PERFORMANCE.md)
- [工作空间管理](apps/portal_web/WORKSPACE_MANAGER.md)
