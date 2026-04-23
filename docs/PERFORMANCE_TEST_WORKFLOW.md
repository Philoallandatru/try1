# 完整性能测试流程

从零开始，使用模拟服务器进行完整的性能诊断和优化。

---

## 📋 测试流程概览

```
1. 启动模拟服务器
   ↓
2. 配置测试工作空间
   ↓
3. 运行基准测试
   ↓
4. 分析瓶颈
   ↓
5. 实施优化
   ↓
6. 对比测试
   ↓
7. 决策：优化 vs 迁移
```

---

## 🚀 第一步：环境准备（5 分钟）

### 1.1 安装依赖

```powershell
# 确保已安装 FastAPI 和 uvicorn
pip install fastapi uvicorn

# 或者使用 uv
uv pip install fastapi uvicorn
```

### 1.2 创建测试工作空间

```powershell
# 初始化工作空间
python scripts/workspace_cli.py init test_workspace

# 创建凭证文件
mkdir test_workspace\.local
```

创建 `test_workspace/.local/credentials.yaml`:
```yaml
version: 1
credentials:
  mock_token:
    type: bearer_inline
    value: mock-token
```

---

## 🎯 第二步：启动模拟服务器（1 分钟）

### 2.1 启动服务器

**终端 1（保持运行）：**
```powershell
# 启动模拟服务器（10K Jira Issues）
python scripts/mock_atlassian_server.py --jira-issues 10000 --confluence-pages 5000
```

**预期输出：**
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
================================================================================

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8888 (Press CTRL+C to quit)
```

### 2.2 验证服务器

**终端 2：**
```powershell
# 测试连接
curl http://localhost:8888/health
```

**预期响应：**
```json
{
  "status": "healthy",
  "jira_issues": 10000,
  "confluence_pages": 5000
}
```

---

## 📊 第三步：配置数据源（2 分钟）

### 3.1 添加 Jira 数据源

```powershell
python scripts/workspace_cli.py source add test_workspace mock_jira \
  --connector-type jira.atlassian_api \
  --base-url http://localhost:8888 \
  --credential-ref mock_token
```

### 3.2 创建 Selector

```powershell
python scripts/workspace_cli.py selector add test_workspace default_selector \
  --source mock_jira \
  --type jql_query \
  --jql "order by updated asc"
```

### 3.3 测试连接

```powershell
python scripts/workspace_cli.py test-source test_workspace mock_jira
```

**预期输出：**
```json
{
  "status": "success",
  "message": "Connection successful",
  "server_info": {
    "version": "9.12.0",
    "serverTitle": "Mock Jira Server"
  }
}
```

---

## 🔍 第四步：运行基准测试（10-30 分钟）

### 4.1 小规模测试（快速验证）

```powershell
python scripts/diagnose_performance.py test_workspace mock_jira --limit 100
```

**预期时间：** 1-2 分钟

### 4.2 中等规模测试

```powershell
python scripts/diagnose_performance.py test_workspace mock_jira --limit 1000 \
  --output baseline_1k.json
```

**预期时间：** 5-10 分钟

### 4.3 大规模测试

```powershell
python scripts/diagnose_performance.py test_workspace mock_jira --limit 5000 \
  --output baseline_5k.json
```

**预期时间：** 20-30 分钟

---

## 📈 第五步：分析基准测试结果（5 分钟）

### 5.1 查看报告

打开 `baseline_1k.json` 或查看终端输出：

```
🔍 性能诊断报告
================================================================================

📈 总体性能:
  • 总耗时: 45.23 秒
  • 峰值内存: 156.8 MB
  • 处理数据: 1000 条
  • 吞吐量: 22.1 items/秒

⏱️  详细计时:
  • fetch_data_from_api          :  35.67s (78.9%) | 120.5 MB
  • parse_and_normalize          :   5.23s (11.6%) |  25.4 MB
  • serialize_to_json            :   1.89s ( 4.2%) |  18.7 MB
  • write_to_disk                :   0.87s ( 1.9%) |  12.3 MB

🚨 性能瓶颈:
  • fetch_data_from_api 占用 78.9% 的时间

💡 优化建议:
🔴 API 调用是主要瓶颈 (>60%)
  → 建议: 启用异步并发拉取 (asyncio + httpx)
  → 建议: 增加 page_size 减少请求次数
  → 建议: 实现增量同步，只拉取变更数据
```

### 5.2 识别瓶颈类型

根据报告中的 🔴 标记：

| 瓶颈类型 | 占比 | 优先级 | 预期提升 |
|---------|------|--------|---------|
| API 调用 | >60% | 🔴 高 | 3-5x |
| 数据解析 | >30% | 🟡 中 | 2-3x |
| 文件 I/O | >20% | 🟢 低 | 2x |

---

## 🛠️ 第六步：实施优化（根据瓶颈类型）

### 场景 A: API 调用是瓶颈（最常见）

#### 优化 1: 增加 page_size（5 分钟）

**修改数据源配置：**
```powershell
python scripts/workspace_cli.py source configure test_workspace mock_jira \
  --page-size 200
```

**重新测试：**
```powershell
python scripts/diagnose_performance.py test_workspace mock_jira --limit 1000 \
  --output after_pagesize.json
```

**预期提升：** 1.5-2x

#### 优化 2: 启用异步并发（1-2 天）

**修改 `services/connectors/jira/atlassian_api_fetch.py`：**

```python
import asyncio
import httpx

async def fetch_jira_issues_async(base_url, jql, token, page_size=100):
    """异步并发拉取 Jira Issues"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 第一次请求获取总数
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/rest/api/2/search",
            params={"jql": jql, "startAt": 0, "maxResults": 1},
            headers=headers,
        )
        data = response.json()
        total = data["total"]
    
    # 并发拉取所有页
    tasks = []
    async with httpx.AsyncClient() as client:
        for start_at in range(0, total, page_size):
            task = client.get(
                f"{base_url}/rest/api/2/search",
                params={"jql": jql, "startAt": start_at, "maxResults": page_size},
                headers=headers,
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
    
    # 合并结果
    all_issues = []
    for response in responses:
        data = response.json()
        all_issues.extend(data["issues"])
    
    return {"issues": all_issues, "total": total}
```

**重新测试：**
```powershell
python scripts/diagnose_performance.py test_workspace mock_jira --limit 1000 \
  --output after_async.json
```

**预期提升：** 3-5x

#### 优化 3: 实现增量同步（2-3 天）

**修改 JQL 查询，只拉取最近更新的数据：**

```python
# 记录上次同步时间
last_sync = "2024-01-01 00:00"

# 只拉取增量数据
jql = f"updated >= '{last_sync}' ORDER BY updated ASC"
```

**预期提升：** 10-100x（取决于增量数据量）

### 场景 B: 数据解析是瓶颈

#### 优化 1: 使用 orjson（10 分钟）

```powershell
# 安装 orjson
pip install orjson
```

**修改代码：**
```python
# 替换
import json
data = json.loads(response.text)

# 为
import orjson
data = orjson.loads(response.content)
```

**预期提升：** 2-3x

---

## 📊 第七步：对比测试（10 分钟）

### 7.1 运行对比测试

```powershell
# 优化后测试
python scripts/diagnose_performance.py test_workspace mock_jira --limit 1000 \
  --output after_optimization.json
```

### 7.2 对比结果

**手动对比：**

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 总耗时 | 45.23s | 12.34s | 3.7x ⬆️ |
| 吞吐量 | 22.1 items/s | 81.0 items/s | 3.7x ⬆️ |
| 内存占用 | 156.8 MB | 145.2 MB | 7% ⬇️ |
| API 调用占比 | 78.9% | 45.2% | 33.7% ⬇️ |

**预估大规模数据：**

| 数据量 | 优化前 | 优化后 | 节省时间 |
|--------|--------|--------|---------|
| 5,000 | 3.8 分钟 | 1.0 分钟 | 2.8 分钟 |
| 10,000 | 7.5 分钟 | 2.1 分钟 | 5.4 分钟 |
| 50,000 | 37.7 分钟 | 10.3 分钟 | 27.4 分钟 |

---

## 🎯 第八步：决策（5 分钟）

### 决策树

```
优化后性能提升 > 3x？
    ├─ 是 → 满足需求？
    │        ├─ 是 → ✅ 保持当前系统
    │        └─ 否 → 继续优化或考虑迁移
    │
    └─ 否 → 优化后性能提升 < 2x？
             ├─ 是 → 🔴 考虑迁移到 LlamaIndex
             └─ 否 → 🟡 继续优化或考虑迁移
```

### 决策标准

**保持当前系统（优化）：**
- ✅ 性能提升 > 3x
- ✅ 满足业务需求（50K 数据 < 15 分钟）
- ✅ 代码维护负担可接受
- ✅ 工作量 < 2 周

**迁移到 LlamaIndex：**
- ✅ 优化后性能仍不满足需求
- ✅ 代码维护负担重
- ✅ 需要更强的检索能力
- ✅ 愿意投入 2-4 周迁移时间
- ✅ 希望获得社区支持

---

## 📝 第九步：记录结果（5 分钟）

### 9.1 创建测试报告

创建 `test_workspace/performance_test_report.md`:

```markdown
# 性能测试报告

**测试日期:** 2024-04-23
**测试人员:** [你的名字]

## 测试环境
- 模拟服务器: 10,000 Jira Issues
- 测试规模: 1,000 / 5,000 / 10,000
- 硬件: [CPU/内存/磁盘]

## 基准测试结果
- 总耗时: 45.23s (1000 items)
- 吞吐量: 22.1 items/s
- 主要瓶颈: API 调用 (78.9%)

## 优化措施
1. 增加 page_size: 50 → 200
2. 启用异步并发
3. [其他优化]

## 优化后结果
- 总耗时: 12.34s (1000 items)
- 吞吐量: 81.0 items/s
- 性能提升: 3.7x

## 决策
✅ 保持当前系统，性能满足需求

## 下一步
- [ ] 部署优化到生产环境
- [ ] 监控生产性能
- [ ] 定期重新评估
```

### 9.2 保存测试数据

```powershell
# 创建测试结果目录
mkdir test_workspace\performance_tests

# 移动所有测试结果
move baseline_*.json test_workspace\performance_tests\
move after_*.json test_workspace\performance_tests\
```

---

## 🎓 常见问题

### Q1: 测试需要多长时间？

**A:** 完整流程约 1-2 小时：
- 环境准备: 5 分钟
- 启动服务器: 1 分钟
- 配置数据源: 2 分钟
- 基准测试: 30-60 分钟
- 分析结果: 5 分钟
- 实施优化: 根据优化类型（5 分钟 - 2 天）
- 对比测试: 10 分钟
- 决策和记录: 10 分钟

### Q2: 模拟服务器和真实环境的差异？

**A:** 主要差异：
- 模拟服务器响应极快（< 10ms）
- 真实环境有网络延迟（50-200ms）
- 真实环境可能有限流

**建议：**
- 使用模拟服务器找到代码瓶颈
- 在真实环境验证网络优化效果

### Q3: 如何模拟网络延迟？

**A:** 修改模拟服务器代码：

```python
import time

@app.get("/rest/api/2/search")
async def jira_search(...):
    time.sleep(0.1)  # 模拟 100ms 延迟
    ...
```

### Q4: 优化后仍然不够快怎么办？

**A:** 按优先级尝试：
1. 检查是否还有其他瓶颈
2. 考虑硬件升级（SSD、更多内存）
3. 实施更激进的优化（流式处理、分布式）
4. 考虑迁移到 LlamaIndex

---

## 📚 相关文档

- [性能诊断指南](PERFORMANCE_DIAGNOSIS_GUIDE.md)
- [Mock 服务器指南](MOCK_SERVER_GUIDE.md)
- [简化数据源配置](SIMPLIFIED_SOURCE_CONFIG.md)

---

## ✅ 检查清单

完成测试后，确认以下事项：

- [ ] 已运行至少 3 个规模的基准测试（100/1000/5000）
- [ ] 已识别主要瓶颈（API/解析/I/O）
- [ ] 已实施至少 1 个优化措施
- [ ] 已运行对比测试
- [ ] 性能提升 > 2x
- [ ] 已记录测试结果
- [ ] 已做出决策（优化 vs 迁移）
- [ ] 已制定下一步计划

---

**祝测试顺利！** 🎉
