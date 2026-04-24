# Mock Atlassian Server 使用指南

模拟 Jira 和 Confluence 服务器，用于性能测试，无需真实的 Atlassian 实例。

---

## 快速开始

### 1. 启动模拟服务器

```powershell
# 默认配置（10,000 个 Jira Issues + 5,000 个 Confluence Pages）
python scripts/mock_atlassian_server.py

# 自定义数据规模
python scripts/mock_atlassian_server.py --jira-issues 50000 --confluence-pages 20000

# 自定义端口
python scripts/mock_atlassian_server.py --port 9000
```

**输出示例：**
```
================================================================================
🚀 Mock Atlassian Server
================================================================================
📍 Jira API:       http://0.0.0.0:8888/rest/api/2/
📍 Confluence API: http://0.0.0.0:8888/wiki/rest/api/
📊 Mock Data:
   • Jira Issues:      10,000
   • Confluence Pages: 5,000

🔑 Authentication: Use any token (e.g., 'Bearer mock-token')

📖 Usage:
   1. Start this server
   2. Configure data source:
      Base URL: http://localhost:8888
      Token: mock-token (any value works)
   3. Run performance diagnosis
================================================================================
```

### 2. 配置数据源

在你的 Portal 或 CLI 中添加数据源：

**Jira 数据源：**
```powershell
python scripts/workspace_cli.py source add my_workspace mock_jira \
  --connector-type jira.atlassian_api \
  --base-url http://localhost:8888 \
  --credential-ref mock_token
```

**Confluence 数据源：**
```powershell
python scripts/workspace_cli.py source add my_workspace mock_confluence \
  --connector-type confluence.atlassian_api \
  --base-url http://localhost:8888/wiki \
  --credential-ref mock_token
```

**配置凭证：**
```yaml
# workspace/.local/credentials.yaml
version: 1
credentials:
  mock_token:
    type: bearer_inline
    value: mock-token  # 任意值都可以
```

### 3. 运行性能诊断

```powershell
# 测试 1000 条数据
python scripts/diagnose_performance.py my_workspace mock_jira --limit 1000

# 测试 10000 条数据
python scripts/diagnose_performance.py my_workspace mock_jira --limit 10000
```

---

## 功能特性

### ✅ 完整的 REST API 模拟

**Jira API：**
- ✅ `/rest/api/2/search` - 搜索 Issues（支持 JQL、分页）
- ✅ `/rest/api/2/issue/{key}` - 获取单个 Issue
- ✅ `/rest/api/2/serverInfo` - 服务器信息（连接测试）

**Confluence API：**
- ✅ `/wiki/rest/api/content` - 搜索 Pages（支持过滤、分页）
- ✅ `/wiki/rest/api/content/{id}` - 获取单个 Page

### ✅ 真实的数据结构

生成的数据包含：
- **Jira Issues:**
  - 完整的字段（summary, description, status, priority, etc.）
  - 评论（comments）
  - 附件（attachments）
  - 组件（components）
  - 标签（labels）
  - 时间戳（created, updated）

- **Confluence Pages:**
  - 标题和内容（HTML 格式）
  - 版本信息
  - 空间（space）
  - 标签（labels）
  - 时间戳

### ✅ 可配置的数据规模

```powershell
# 小规模测试（快速）
python scripts/mock_atlassian_server.py --jira-issues 1000 --confluence-pages 500

# 中等规模（5K-10K）
python scripts/mock_atlassian_server.py --jira-issues 10000 --confluence-pages 5000

# 大规模（50K+）
python scripts/mock_atlassian_server.py --jira-issues 50000 --confluence-pages 20000

# 超大规模（压力测试）
python scripts/mock_atlassian_server.py --jira-issues 100000 --confluence-pages 50000
```

### ✅ 支持分页

```bash
# Jira 分页
curl -H "Authorization: Bearer mock-token" \
  "http://localhost:8888/rest/api/2/search?jql=order+by+updated+asc&startAt=0&maxResults=50"

# Confluence 分页
curl -H "Authorization: Bearer mock-token" \
  "http://localhost:8888/wiki/rest/api/content?type=page&start=0&limit=25"
```

---

## 使用场景

### 场景 1: 性能基准测试

**目标：** 测试系统在不同数据规模下的性能

```powershell
# 1. 启动模拟服务器（50K issues）
python scripts/mock_atlassian_server.py --jira-issues 50000

# 2. 配置数据源
python scripts/workspace_cli.py source add test_workspace mock_jira \
  --connector-type jira.atlassian_api \
  --base-url http://localhost:8888

# 3. 运行诊断
python scripts/diagnose_performance.py test_workspace mock_jira --limit 1000
python scripts/diagnose_performance.py test_workspace mock_jira --limit 5000
python scripts/diagnose_performance.py test_workspace mock_jira --limit 10000
```

### 场景 2: 优化前后对比

**目标：** 验证优化效果

```powershell
# 1. 优化前测试
python scripts/diagnose_performance.py workspace1 mock_jira --limit 5000 \
  --output before_optimization.json

# 2. 实施优化（异步、并发等）

# 3. 优化后测试
python scripts/diagnose_performance.py workspace1 mock_jira --limit 5000 \
  --output after_optimization.json

# 4. 对比结果
python scripts/compare_performance.py before_optimization.json after_optimization.json
```

### 场景 3: 压力测试

**目标：** 测试系统极限

```powershell
# 1. 启动超大规模服务器
python scripts/mock_atlassian_server.py --jira-issues 100000

# 2. 逐步增加负载
python scripts/diagnose_performance.py workspace1 mock_jira --limit 10000
python scripts/diagnose_performance.py workspace1 mock_jira --limit 20000
python scripts/diagnose_performance.py workspace1 mock_jira --limit 50000
```

### 场景 4: 开发和调试

**目标：** 在没有真实 Jira 的情况下开发和测试

```powershell
# 1. 启动本地服务器
python scripts/mock_atlassian_server.py --port 8888

# 2. 开发新功能
# 3. 使用模拟数据测试
# 4. 无需担心影响生产数据
```

---

## API 示例

### Jira API

**搜索 Issues：**
```bash
curl -H "Authorization: Bearer mock-token" \
  "http://localhost:8888/rest/api/2/search?jql=project=SSD&startAt=0&maxResults=10"
```

**响应：**
```json
{
  "startAt": 0,
  "maxResults": 10,
  "total": 10000,
  "issues": [
    {
      "id": "10001",
      "key": "SSD-1",
      "fields": {
        "summary": "[Mock] Issue SSD-1: Fix NVMe",
        "description": "This is a mock issue...",
        "status": {"name": "Open"},
        "priority": {"name": "High"},
        ...
      }
    },
    ...
  ]
}
```

**获取单个 Issue：**
```bash
curl -H "Authorization: Bearer mock-token" \
  "http://localhost:8888/rest/api/2/issue/SSD-123"
```

### Confluence API

**搜索 Pages：**
```bash
curl -H "Authorization: Bearer mock-token" \
  "http://localhost:8888/wiki/rest/api/content?type=page&spaceKey=TECH&start=0&limit=10"
```

**响应：**
```json
{
  "results": [
    {
      "id": "300001",
      "type": "page",
      "title": "[Mock] Design - Page 1",
      "space": {"key": "TECH", "name": "TECH Space"},
      "body": {
        "storage": {
          "value": "<h1>Mock Page 1</h1>...",
          "representation": "storage"
        }
      },
      ...
    },
    ...
  ],
  "start": 0,
  "limit": 10,
  "size": 10
}
```

---

## 数据特征

### Jira Issues

- **Projects:** SSD, FW, HW, TEST, DOC
- **Issue Types:** Bug, Task, Story, Epic, Sub-task
- **Statuses:** Open, In Progress, In Review, Resolved, Closed
- **Priorities:** Highest, High, Medium, Low, Lowest
- **Components:** NVMe, SATA, PCIe, Firmware, Driver, Testing
- **Labels:** performance, security, bug-fix, feature, refactor, documentation

**时间分布：**
- Issue 编号越小，创建时间越早
- 模拟过去 365 天的数据
- 每个 Issue 有随机的更新时间

### Confluence Pages

- **Spaces:** TECH, DESIGN, SPEC, WIKI, TEAM
- **Page Types:** page, blogpost
- **内容:** HTML 格式，包含标题、段落、列表、宏

---

## 性能特征

### 响应时间

模拟服务器的响应时间非常快（< 10ms），因为：
- 数据在内存中动态生成
- 没有真实的数据库查询
- 没有网络延迟

**这意味着：**
- ✅ 可以快速测试大规模数据
- ✅ 瓶颈会集中在你的代码上（而非 API）
- ⚠️ 真实环境的网络延迟需要单独考虑

### 内存占用

- 小规模（1K-10K）: ~50-100 MB
- 中等规模（10K-50K）: ~100-200 MB
- 大规模（50K-100K）: ~200-500 MB

---

## 故障排查

### 问题 1: 连接失败

**症状：**
```
❌ 连接失败: Connection refused
```

**解决方案：**
1. 确认服务器已启动
2. 检查端口是否正确（默认 8888）
3. 检查防火墙设置

### 问题 2: 认证失败

**症状：**
```
❌ 401 Unauthorized
```

**解决方案：**
1. 确保请求包含 `Authorization` header
2. 使用任意 token（例如 `Bearer mock-token`）
3. 检查凭证配置

### 问题 3: 数据不一致

**症状：**
每次请求返回不同的数据

**解释：**
这是正常的！数据是动态生成的，每次请求都会生成新的随机数据。

**如果需要一致性：**
可以修改代码，使用固定的随机种子：
```python
random.seed(42)  # 固定种子
```

---

## 高级用法

### 自定义数据生成

修改 `MockDataGenerator` 类来自定义数据：

```python
# 修改项目列表
self.projects = ["MYPROJECT", "TEAM1", "TEAM2"]

# 修改 Issue 描述模板
def _generate_description(self, issue_key: str) -> str:
    return f"Custom description for {issue_key}"
```

### 添加延迟模拟

模拟真实的网络延迟：

```python
import time

@app.get("/rest/api/2/search")
async def jira_search(...):
    time.sleep(0.1)  # 模拟 100ms 延迟
    ...
```

### 模拟错误

测试错误处理：

```python
@app.get("/rest/api/2/search")
async def jira_search(...):
    if random.random() < 0.1:  # 10% 概率失败
        raise HTTPException(status_code=500, detail="Internal Server Error")
    ...
```

---

## 与真实 API 的差异

### 相同点

- ✅ REST API 端点路径
- ✅ 请求参数（JQL, startAt, maxResults, etc.）
- ✅ 响应数据结构
- ✅ 分页机制
- ✅ 认证方式

### 差异点

- ⚠️ 数据是动态生成的（不持久化）
- ⚠️ 不支持写操作（POST, PUT, DELETE）
- ⚠️ JQL 查询不会真正过滤（返回所有数据）
- ⚠️ 响应速度比真实 API 快得多
- ⚠️ 没有限流（rate limiting）

---

## 下一步

1. **启动服务器**
   ```powershell
   python scripts/mock_atlassian_server.py --jira-issues 10000
   ```

2. **配置数据源**
   ```powershell
   python scripts/workspace_cli.py source add workspace1 mock_jira \
     --connector-type jira.atlassian_api \
     --base-url http://localhost:8888
   ```

3. **运行性能诊断**
   ```powershell
   python scripts/diagnose_performance.py workspace1 mock_jira --limit 1000
   ```

4. **分析结果并优化**

---

## 相关文档

- [性能诊断指南](PERFORMANCE_DIAGNOSIS_GUIDE.md)
- [简化数据源配置](SIMPLIFIED_SOURCE_CONFIG.md)
- [架构概览](architecture-overview.md)
