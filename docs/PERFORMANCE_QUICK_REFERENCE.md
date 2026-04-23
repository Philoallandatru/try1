# 性能诊断快速参考

一页纸快速参考，帮助你快速开始性能诊断。

---

## 🚀 三步快速开始

### 1️⃣ 启动模拟服务器（终端 1）
```powershell
python scripts/mock_atlassian_server.py --jira-issues 10000
```

### 2️⃣ 配置数据源（终端 2）
```powershell
# 初始化工作空间
python scripts/workspace_cli.py init test_workspace

# 创建凭证文件
echo "version: 1
credentials:
  mock_token:
    type: bearer_inline
    value: mock-token" > test_workspace\.local\credentials.yaml

# 添加数据源
python scripts/workspace_cli.py source add test_workspace mock_jira \
  --connector-type jira.atlassian_api \
  --base-url http://localhost:8888 \
  --credential-ref mock_token
```

### 3️⃣ 运行诊断
```powershell
python scripts/diagnose_performance.py test_workspace mock_jira --limit 1000
```

---

## 📊 解读报告

### 瓶颈类型

| 指标 | 阈值 | 优先级 | 解决方案 |
|------|------|--------|---------|
| **API 调用** | >60% | 🔴 高 | 异步并发 + 增量同步 |
| **数据解析** | >30% | 🟡 中 | orjson + 优化逻辑 |
| **文件 I/O** | >20% | 🟢 低 | 批量写入 + SSD |

### 吞吐量标准

| 吞吐量 | 评级 | 50K 数据耗时 |
|--------|------|-------------|
| < 10 items/s | 🔴 慢 | 83 分钟 |
| 10-30 items/s | 🟡 中等 | 28-83 分钟 |
| > 30 items/s | 🟢 快 | < 28 分钟 |

---

## 🛠️ 快速优化

### 优化 1: 增加 page_size（5 分钟）
```powershell
python scripts/workspace_cli.py source configure test_workspace mock_jira \
  --page-size 200
```
**预期提升:** 1.5-2x

### 优化 2: 使用 orjson（10 分钟）
```powershell
pip install orjson
```
```python
# 替换 import json 为
import orjson
data = orjson.loads(response.content)
```
**预期提升:** 2-3x

### 优化 3: 异步并发（1-2 天）
```python
import asyncio
import httpx

async def fetch_async(urls):
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        return await asyncio.gather(*tasks)
```
**预期提升:** 3-5x

---

## 🎯 决策矩阵

| 性能提升 | 满足需求 | 决策 |
|---------|---------|------|
| > 3x | ✅ 是 | ✅ 保持当前系统 |
| > 3x | ❌ 否 | 🟡 继续优化 |
| 2-3x | ✅ 是 | ✅ 保持当前系统 |
| 2-3x | ❌ 否 | 🟡 考虑迁移 |
| < 2x | - | 🔴 迁移到 LlamaIndex |

---

## 📁 文件清单

### 已创建的文件

```
scripts/
├── diagnose_performance.py          # 性能诊断工具
└── mock_atlassian_server.py         # 模拟服务器

docs/
├── PERFORMANCE_DIAGNOSIS_GUIDE.md   # 详细诊断指南
├── MOCK_SERVER_GUIDE.md             # 模拟服务器指南
├── PERFORMANCE_TEST_WORKFLOW.md     # 完整测试流程
└── PERFORMANCE_QUICK_REFERENCE.md   # 本文件
```

### 测试输出文件

```
test_workspace/
├── .local/
│   └── credentials.yaml             # 凭证配置
├── sources/
│   └── mock_jira.yaml               # 数据源配置
├── performance_tests/
│   ├── baseline_1k.json             # 基准测试结果
│   ├── after_optimization.json      # 优化后结果
│   └── performance_test_report.md   # 测试报告
```

---

## 🔗 命令速查

### 模拟服务器
```powershell
# 启动（默认 10K issues）
python scripts/mock_atlassian_server.py

# 自定义规模
python scripts/mock_atlassian_server.py --jira-issues 50000

# 自定义端口
python scripts/mock_atlassian_server.py --port 9000

# 健康检查
curl http://localhost:8888/health
```

### 性能诊断
```powershell
# 快速测试（100 条）
python scripts/diagnose_performance.py <workspace> <source> --limit 100

# 标准测试（1000 条）
python scripts/diagnose_performance.py <workspace> <source> --limit 1000

# 大规模测试（5000 条）
python scripts/diagnose_performance.py <workspace> <source> --limit 5000

# 保存报告
python scripts/diagnose_performance.py <workspace> <source> --limit 1000 \
  --output report.json
```

### 数据源管理
```powershell
# 添加数据源
python scripts/workspace_cli.py source add <workspace> <name> \
  --connector-type jira.atlassian_api \
  --base-url http://localhost:8888 \
  --credential-ref mock_token

# 配置数据源
python scripts/workspace_cli.py source configure <workspace> <name> \
  --page-size 200

# 测试连接
python scripts/workspace_cli.py test-source <workspace> <name>

# 列出数据源
python scripts/workspace_cli.py source list <workspace>
```

---

## 💡 最佳实践

### ✅ 推荐做法

1. **先小规模测试**（100 条）验证配置
2. **逐步增加规模**（100 → 1000 → 5000）
3. **记录每次测试结果**
4. **一次只优化一个点**
5. **优化后立即测试**
6. **保存所有测试数据**

### ❌ 避免做法

1. ❌ 直接测试超大规模（50K+）
2. ❌ 同时实施多个优化
3. ❌ 不记录基准数据
4. ❌ 不验证优化效果
5. ❌ 盲目迁移到新框架

---

## 🆘 故障排查

### 问题：连接失败
```
❌ Connection refused
```
**解决：** 确认模拟服务器已启动，检查端口

### 问题：认证失败
```
❌ 401 Unauthorized
```
**解决：** 检查 credentials.yaml 配置

### 问题：诊断工具报错
```
❌ Generator not initialized
```
**解决：** 重启模拟服务器

### 问题：性能没有提升
**检查：**
1. 是否优化了正确的瓶颈？
2. 优化代码是否生效？
3. 是否有其他隐藏瓶颈？

---

## 📞 获取帮助

### 文档
- [详细诊断指南](PERFORMANCE_DIAGNOSIS_GUIDE.md)
- [完整测试流程](PERFORMANCE_TEST_WORKFLOW.md)
- [模拟服务器指南](MOCK_SERVER_GUIDE.md)

### 下一步
1. 运行诊断工具
2. 分析报告
3. 实施优化
4. 对比测试
5. 做出决策

---

**开始诊断：**
```powershell
python scripts/mock_atlassian_server.py --jira-issues 10000
python scripts/diagnose_performance.py test_workspace mock_jira --limit 1000
```

**祝你好运！** 🎯
