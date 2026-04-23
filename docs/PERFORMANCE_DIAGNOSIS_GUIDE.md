# 性能诊断指南

本指南帮助你诊断数据同步卡顿问题，找到真正的瓶颈，并提供针对性的优化建议。

---

## 快速开始

### 1. 运行诊断工具

```powershell
# 基础诊断（拉取 100 条数据测试）
python scripts/diagnose_performance.py <workspace> <source_name> --limit 100

# 中等规模测试（1000 条）
python scripts/diagnose_performance.py <workspace> <source_name> --limit 1000

# 大规模测试（5000 条）
python scripts/diagnose_performance.py <workspace> <source_name> --limit 5000

# 保存报告到文件
python scripts/diagnose_performance.py <workspace> <source_name> --limit 1000 --output diagnosis_report.json
```

### 2. 示例

```powershell
# 诊断 jira_source
python scripts/diagnose_performance.py workspace1 jira_source --limit 500

# 使用特定的 selector
python scripts/diagnose_performance.py workspace1 jira_source --selector-profile my_selector --limit 1000
```

---

## 诊断报告解读

### 报告结构

```
🔍 性能诊断报告
================================================================================

📈 总体性能:
  • 总耗时: 45.23 秒
  • 峰值内存: 156.8 MB
  • 处理数据: 1000 条
  • 吞吐量: 22.1 items/秒

⏱️  详细计时:
  • build_fetch_request          :   0.12s ( 0.3%) |   2.1 MB
  • establish_connection         :   1.45s ( 3.2%) |   5.3 MB
  • fetch_data_from_api          :  35.67s (78.9%) | 120.5 MB | 28.0 items/s
  • parse_and_normalize          :   5.23s (11.6%) |  25.4 MB | 191.2 items/s
  • serialize_to_json            :   1.89s ( 4.2%) |  18.7 MB | 529.1 items/s
  • write_to_disk                :   0.87s ( 1.9%) |  12.3 MB | 1149.4 items/s

🚨 性能瓶颈:
  • fetch_data_from_api 占用 78.9% 的时间

💡 优化建议:
🔴 API 调用是主要瓶颈 (>60%)
  → 建议: 启用异步并发拉取 (asyncio + httpx)
  → 建议: 增加 page_size 减少请求次数
  → 建议: 实现增量同步，只拉取变更数据
  → 考虑: 迁移到 LlamaIndex 的 JiraReader（内置优化）

📊 大规模数据预估:
  • 1,000 items: ~0.8 分钟
  • 5,000 items: ~3.8 分钟
  • 10,000 items: ~7.5 分钟
  • 50,000 items: ~37.7 分钟
```

---

## 瓶颈类型和解决方案

### 🔴 瓶颈 1: API 调用慢 (>60%)

**症状:**
- `fetch_data_from_api` 占用超过 60% 的时间
- 吞吐量 < 20 items/秒
- CPU 空闲，大部分时间在等待网络响应

**原因:**
- 单线程同步调用 API
- 网络延迟高
- API 限流
- page_size 太小，请求次数过多

**解决方案（按优先级）:**

#### 方案 A: 优化当前系统（1-2 周）

1. **启用异步并发拉取**
   ```python
   import asyncio
   import httpx
   
   async def fetch_issues_async(base_url, jql, page_size=100):
       async with httpx.AsyncClient() as client:
           tasks = []
           # 并发拉取多页
           for start_at in range(0, total, page_size):
               task = client.get(f"{base_url}/rest/api/2/search", 
                                params={"jql": jql, "startAt": start_at, "maxResults": page_size})
               tasks.append(task)
           responses = await asyncio.gather(*tasks)
           return responses
   ```

2. **增加 page_size**
   - 当前默认: 50
   - 建议: 100-200（根据 API 限制）
   - 修改位置: `source.defaults.page_size`

3. **实现增量同步**
   ```python
   # 只拉取最近更新的数据
   jql = f"project = SSD AND updated >= '{last_sync_time}' ORDER BY updated ASC"
   ```

4. **连接池复用**
   ```python
   # 复用 HTTP 连接，减少握手开销
   session = requests.Session()
   adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
   session.mount('https://', adapter)
   ```

**预期提升:** 3-5x 速度提升

#### 方案 B: 迁移到 LlamaIndex（2-4 周）

```python
from llama_index.readers.jira import JiraReader

# LlamaIndex 内置优化
reader = JiraReader(
    server_url="https://jira.example.com",
    email="user@example.com",
    api_token="your-token",
)

# 自动处理分页、重试、限流
documents = reader.load_data(
    query="project = SSD AND updated >= '2024-01-01'",
    max_results=10000,  # 自动分页
)
```

**优势:**
- 内置异步并发
- 自动重试和错误处理
- 增量同步支持
- 社区维护

---

### 🟡 瓶颈 2: 数据解析慢 (>30%)

**症状:**
- `parse_and_normalize` 占用超过 30% 的时间
- CPU 占用高
- 内存占用高

**原因:**
- JSON 解析慢（使用标准 `json` 库）
- 数据规范化逻辑复杂
- 大量字符串操作

**解决方案:**

1. **使用 orjson 替代标准 json**
   ```python
   # 安装
   pip install orjson
   
   # 使用（比标准 json 快 2-3x）
   import orjson
   data = orjson.loads(response.text)
   ```

2. **优化数据规范化逻辑**
   - 避免深拷贝 (`dict(issue)` → 直接修改)
   - 减少不必要的字段处理
   - 使用生成器而非列表

3. **分批处理**
   ```python
   # 不要一次性处理所有数据
   for batch in chunks(issues, batch_size=100):
       process_batch(batch)
   ```

**预期提升:** 2-3x 速度提升

---

### 🟢 瓶颈 3: 文件 I/O 慢 (>20%)

**症状:**
- `write_to_disk` 占用超过 20% 的时间
- 磁盘 I/O 高

**原因:**
- 频繁的小文件写入
- 没有使用缓冲
- 磁盘性能差（机械硬盘）

**解决方案:**

1. **批量写入**
   ```python
   # 不要每个 issue 写一个文件
   # 而是批量写入
   with open(output_file, 'w') as f:
       json.dump({"issues": all_issues}, f)
   ```

2. **使用内存缓存**
   ```python
   # 先在内存中累积，最后一次性写入
   buffer = []
   for issue in issues:
       buffer.append(issue)
       if len(buffer) >= 1000:
           flush_to_disk(buffer)
           buffer.clear()
   ```

3. **使用 SSD**
   - 如果可能，将工作空间移到 SSD

**预期提升:** 2x 速度提升

---

## 内存优化

### 内存占用过高 (>500 MB)

**解决方案:**

1. **流式处理**
   ```python
   # 不要一次性加载所有数据到内存
   def process_stream(issues):
       for issue in issues:
           normalized = normalize_issue(issue)
           write_to_disk(normalized)
           # 立即释放内存
           del normalized
   ```

2. **分批处理**
   ```python
   # 每次只处理 1000 条
   for batch in fetch_in_batches(jql, batch_size=1000):
       process_batch(batch)
   ```

3. **使用生成器**
   ```python
   def fetch_issues_generator(jql):
       start_at = 0
       while True:
           batch = fetch_batch(jql, start_at)
           if not batch:
               break
           for issue in batch:
               yield issue
           start_at += len(batch)
   ```

---

## 决策树

根据诊断结果，选择合适的优化方案：

```
诊断报告
    ↓
API 调用 > 60%？
    ├─ 是 → 优先优化 API 调用
    │        ├─ 快速方案: 异步并发 + 增加 page_size (1 周)
    │        ├─ 中期方案: 增量同步 (1-2 周)
    │        └─ 长期方案: 迁移到 LlamaIndex (2-4 周)
    │
    └─ 否 → 数据解析 > 30%？
             ├─ 是 → 优化数据处理
             │        ├─ 使用 orjson (1 天)
             │        ├─ 优化规范化逻辑 (3-5 天)
             │        └─ 分批处理 (1 周)
             │
             └─ 否 → 文件 I/O > 20%？
                      ├─ 是 → 优化文件写入
                      │        ├─ 批量写入 (1 天)
                      │        └─ 使用 SSD (硬件)
                      │
                      └─ 否 → 性能已经很好，无需优化
```

---

## 测试计划

### 阶段 1: 基准测试（第 1 天）

1. 运行诊断工具，测试 3 个规模:
   - 100 条（快速测试）
   - 1000 条（中等规模）
   - 5000 条（大规模）

2. 记录基准数据:
   - 总耗时
   - 吞吐量
   - 内存占用
   - 各阶段耗时占比

### 阶段 2: 针对性优化（第 2-7 天）

根据诊断结果，选择 1-2 个优化方案实施。

### 阶段 3: 对比测试（第 8 天）

1. 使用相同的测试数据
2. 对比优化前后的性能
3. 计算提升比例

### 阶段 4: 决策（第 9-10 天）

- 如果性能提升 > 3x，且满足需求 → 保持当前系统
- 如果性能提升 < 2x，或仍然不够 → 考虑迁移到 LlamaIndex
- 如果代码维护负担太重 → 考虑迁移到 LlamaIndex

---

## 常见问题

### Q1: 诊断工具会影响生产数据吗？

**A:** 不会。诊断工具:
- 只读取数据，不修改
- 测试文件会自动清理
- 可以使用 `--limit` 限制数据量

### Q2: 需要多长时间完成诊断？

**A:** 取决于测试规模:
- 100 条: 1-2 分钟
- 1000 条: 5-10 分钟
- 5000 条: 20-30 分钟

### Q3: 诊断工具支持 Confluence 吗？

**A:** 当前版本主要支持 Jira。Confluence 支持即将推出。

### Q4: 如何解读"吞吐量"指标？

**A:** 吞吐量 = 每秒处理的 items 数量
- < 10 items/s: 🔴 较慢，需要优化
- 10-30 items/s: 🟡 中等，可以优化
- > 30 items/s: 🟢 良好

对于 50K 数据:
- 10 items/s → 83 分钟
- 30 items/s → 28 分钟
- 50 items/s → 17 分钟

---

## 下一步

1. **运行诊断工具**
   ```powershell
   python scripts/diagnose_performance.py <workspace> <source_name> --limit 1000
   ```

2. **分析报告**
   - 找到主要瓶颈
   - 查看优化建议

3. **选择优化方案**
   - 快速方案: 优化当前系统（1-2 周）
   - 长期方案: 迁移到 LlamaIndex（2-4 周）

4. **实施优化**
   - 按优先级逐步优化
   - 每次优化后重新测试

5. **评估结果**
   - 对比优化前后性能
   - 决定是否需要进一步优化或迁移

---

## 相关文档

- [简化数据源配置方案](SIMPLIFIED_SOURCE_CONFIG.md)
- [架构概览](architecture-overview.md)
- [开发者工作流](developer-workflow.md)
